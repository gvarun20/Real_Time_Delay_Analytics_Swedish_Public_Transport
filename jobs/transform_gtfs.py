"""PySpark transform: raw GTFS + TripUpdates -> PostgreSQL star schema."""

from __future__ import annotations

import argparse
import logging
import shutil
import sys
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path

from pyspark.sql import SparkSession
from pyspark.sql import functions as F
from pyspark.sql.types import IntegerType, TimestampType
from pyspark.sql.window import Window

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import DATA_RAW_DIR, OPERATOR, OPERATOR_NAME, REALTIME_FEED, STATIC_FEED  # noqa: E402
from jobs.transform.ids import SL_AGENCY_IDS_REGIONAL, SL_AGENCY_IDS_SWEDEN3, normalize_rt_stop_id  # noqa: E402
from jobs.transform.gtfs_realtime import parse_trip_updates  # noqa: E402
from jobs.transform.loaders import (  # noqa: E402
    delete_facts_for_date,
    get_vehicle_type_keys,
    insert_facts,
    record_pipeline_run,
    upsert_routes,
    upsert_stops,
)
from jobs.transform.paths import latest_realtime_pb, static_zip_path  # noqa: E402
from jobs.transform.time_utils import date_to_date_key, gtfs_time_to_datetime  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# Legacy alias kept for tests/docs
SL_AGENCY_IDS = SL_AGENCY_IDS_REGIONAL


def _gtfs_time_udf():
    from pyspark.sql.functions import udf

    @udf(TimestampType())
    def to_timestamp(service_date: str, gtfs_time: str):
        if not gtfs_time:
            return None
        return gtfs_time_to_datetime(service_date, gtfs_time)

    return to_timestamp


def _extract_gtfs_zip(zip_path: Path) -> Path:
    tmp = Path(tempfile.mkdtemp(prefix="gtfs_extract_"))
    with zipfile.ZipFile(zip_path) as zf:
        zf.extractall(tmp)
    return tmp


def _sl_agency_filter(agency_df, static_feed: str = STATIC_FEED):
    """Filter agency rows to SL operator."""
    if static_feed == "gtfs_regional":
        return agency_df
    sl_ids = list(SL_AGENCY_IDS_SWEDEN3 | SL_AGENCY_IDS_REGIONAL)
    return agency_df.filter(
        F.col("agency_id").isin(sl_ids)
        | (F.lower(F.col("agency_name")) == "sl")
        | F.lower(F.col("agency_name")).contains("ab sl")
    )


def run_transform(
    service_date: str,
    operator: str = OPERATOR,
    operator_name: str = OPERATOR_NAME,
    raw_base: Path | None = None,
    dag_run_id: str | None = None,
    sample_fraction: float | None = None,
) -> int:
    raw_base = raw_base or DATA_RAW_DIR
    date_key = date_to_date_key(service_date)
    zip_path = static_zip_path(service_date, raw_base)
    rt_path = latest_realtime_pb(service_date, raw_base)

    logger.info("Transform service_date=%s operator=%s", service_date, operator)
    logger.info("Static: %s", zip_path)
    logger.info("Realtime: %s", rt_path)

    extract_dir = _extract_gtfs_zip(zip_path)
    try:
        spark = (
            SparkSession.builder.appName("gtfs-delay-transform")
            .master("local[2]")
            .config("spark.driver.memory", "4g")
            .config("spark.sql.shuffle.partitions", "8")
            .config("spark.sql.session.timeZone", "Europe/Stockholm")
            .getOrCreate()
        )
        spark.sparkContext.setLogLevel("WARN")

        gtfs_time_to_ts = _gtfs_time_udf()

        agency = spark.read.option("header", True).csv(str(extract_dir / "agency.txt"))
        sl_agency = _sl_agency_filter(agency).select("agency_id").distinct()

        routes = spark.read.option("header", True).csv(str(extract_dir / "routes.txt"))
        sl_routes = routes.join(sl_agency, on="agency_id", how="inner")

        trips = spark.read.option("header", True).csv(str(extract_dir / "trips.txt"))
        sl_trips = trips.join(sl_routes.select("route_id"), on="route_id", how="inner")

        stops = spark.read.option("header", True).csv(str(extract_dir / "stops.txt"))
        stop_times = spark.read.option("header", True).csv(str(extract_dir / "stop_times.txt"))
        sl_stop_times = stop_times.join(
            sl_trips.select("trip_id", "route_id"), on="trip_id", how="inner"
        )
        for col_name in ("route_id", "stop_id", "trip_id", "stop_sequence"):
            if col_name in sl_stop_times.columns:
                sl_stop_times = sl_stop_times.withColumn(col_name, F.col(col_name).cast("string"))

        if sample_fraction and 0 < sample_fraction < 1:
            sl_trips = sl_trips.sample(fraction=sample_fraction, seed=42)
            trip_ids = sl_trips.select("trip_id")
            sl_stop_times = sl_stop_times.join(trip_ids, on="trip_id", how="inner")
            logger.info("Sampled %.0f%% of SL trips for faster dev run", sample_fraction * 100)

        # Cache + materialize now: sl_stop_times feeds trip_starts, scheduled, AND stop_rows
        # below. Without caching, each Spark action recomputes the full lineage from scratch —
        # including re-running .sample() after the upstream shuffle join — which can silently
        # draw a DIFFERENT random subset of trips each time, causing stop_rows/route_rows to
        # disagree with the rows actually seen in `joined` later.
        sl_stop_times = sl_stop_times.cache()
        sl_stop_times.count()

        rt_rows = parse_trip_updates(rt_path)
        if not rt_rows:
            raise ValueError(f"No TripUpdates parsed from {rt_path}")

        for row in rt_rows:
            row["stop_id"] = normalize_rt_stop_id(
                row.get("stop_id"),
                static_feed=STATIC_FEED,
                realtime_feed=REALTIME_FEED,
            )

        rt_df = spark.createDataFrame(rt_rows)
        for col_name in ("route_id", "stop_id", "trip_id", "stop_sequence"):
            if col_name in rt_df.columns:
                rt_df = rt_df.withColumn(col_name, F.col(col_name).cast("string"))
        logger.info("Parsed %d realtime stop updates", len(rt_rows))

        # First stop departure per trip (for matching regional RT to national static)
        trip_window = Window.partitionBy("trip_id").orderBy(F.col("stop_sequence").cast("int"))
        trip_starts = (
            sl_stop_times.withColumn("rn", F.row_number().over(trip_window))
            .filter(F.col("rn") == 1)
            .select(
                "trip_id",
                gtfs_time_to_ts(F.lit(service_date), F.col("departure_time")).alias("trip_start_ts"),
            )
            .withColumn("trip_start_epoch", F.unix_timestamp(F.col("trip_start_ts")))
        )

        scheduled = (
            sl_stop_times.join(
                stops.select("stop_id", "stop_name", "stop_lat", "stop_lon"), on="stop_id"
            )
            .join(
                sl_routes.select("route_id", "route_short_name", "route_long_name", "route_type"),
                on="route_id",
            )
            .join(trip_starts, on="trip_id", how="left")
            .withColumn(
                "scheduled_arrival",
                gtfs_time_to_ts(F.lit(service_date), F.col("arrival_time")),
            )
            .select(
                "trip_id",
                "stop_id",
                "stop_sequence",
                "route_id",
                "route_short_name",
                "route_long_name",
                "route_type",
                "stop_name",
                "stop_lat",
                "stop_lon",
                "scheduled_arrival",
                "trip_start_epoch",
            )
        )

        rt_cols = [
            "trip_id",
            "route_id",
            "trip_start_epoch",
            "stop_id",
            "stop_sequence",
            "delay_seconds",
            "actual_epoch",
        ]
        rt_sel = rt_df.select(*[c for c in rt_cols if c in rt_df.columns])

        # Primary: trip_id + stop_id (same feed family)
        # .cache() BEFORE the materializing .count() call so this exact result is reused by
        # every later action (the withColumn calls below and the toLocalIterator() loop),
        # instead of Spark recomputing — and potentially re-sampling — the whole lineage again.
        joined = scheduled.join(
            rt_sel.select("trip_id", "stop_id", "delay_seconds", "actual_epoch"),
            on=["trip_id", "stop_id"],
            how="inner",
        ).cache()
        match_count = joined.count()

        if match_count == 0:
            logger.warning(
                "trip_id join matched 0 rows (STATIC_FEED=%s, REALTIME_FEED=%s) — falling "
                "back to route_id + stop_id + stop_sequence + trip_start_epoch. If this "
                "fallback also matches 0 rows, STATIC_FEED/REALTIME_FEED are likely from "
                "different feed families — see docs/decisions/003-ingest-feed-types.md",
                STATIC_FEED,
                REALTIME_FEED,
            )
            joined.unpersist()
            rt_fallback = rt_sel.withColumnRenamed("trip_start_epoch", "rt_trip_start_epoch")
            joined = scheduled.join(
                rt_fallback.drop("trip_id"),
                on=["route_id", "stop_id", "stop_sequence"],
                how="inner",
            )
            joined = joined.filter(
                F.col("rt_trip_start_epoch").isNull()
                | F.col("trip_start_epoch").isNull()
                | (F.abs(F.col("rt_trip_start_epoch") - F.col("trip_start_epoch")) <= 300)
            ).cache()
            match_count = joined.count()

        joined = joined.withColumn(
            "actual_arrival",
            F.when(
                F.col("actual_epoch").isNotNull(),
                F.to_timestamp(F.from_unixtime(F.col("actual_epoch"))),
            ).when(
                F.col("delay_seconds").isNotNull(),
                F.to_timestamp(
                    F.from_unixtime(
                        F.unix_timestamp(F.col("scheduled_arrival"))
                        + F.col("delay_seconds").cast("int")
                    )
                ),
            ),
        )

        joined = joined.withColumn(
            "delay_seconds",
            F.when(
                F.col("delay_seconds").isNotNull(),
                F.col("delay_seconds").cast(IntegerType()),
            ).otherwise(
                F.unix_timestamp(F.col("actual_arrival"))
                - F.unix_timestamp(F.col("scheduled_arrival"))
            ),
        )

        fact_count = match_count
        logger.info("Matched %d trip-stop rows with realtime data", fact_count)
        if fact_count == 0:
            raise ValueError("No rows after joining static schedule with realtime updates")

        route_rows = [
            {
                "route_id": row.route_id,
                "route_short_name": row.route_short_name,
                "route_long_name": row.route_long_name,
            }
            for row in sl_routes.select("route_id", "route_short_name", "route_long_name")
            .distinct()
            .collect()
        ]
        stop_rows = [
            {
                "stop_id": row.stop_id,
                "stop_name": row.stop_name,
                "stop_lat": float(row.stop_lat) if row.stop_lat else None,
                "stop_lon": float(row.stop_lon) if row.stop_lon else None,
            }
            for row in stops.join(
                sl_stop_times.select("stop_id").distinct(), on="stop_id", how="inner"
            )
            .select("stop_id", "stop_name", "stop_lat", "stop_lon")
            .distinct()
            .collect()
        ]

        route_keys = upsert_routes(route_rows, operator_name)
        stop_keys = upsert_stops(stop_rows, operator_name)
        vehicle_type_keys = get_vehicle_type_keys()
        default_vt_key = vehicle_type_keys.get(3, 1)

        delete_facts_for_date(date_key)

        fact_batch: list[dict] = []
        total_inserted = 0
        rows_seen = 0
        skipped_no_dim = 0
        for row in joined.toLocalIterator():
            rows_seen += 1
            route_key = route_keys.get(row.route_id)
            stop_key = stop_keys.get(row.stop_id)
            if route_key is None or stop_key is None:
                skipped_no_dim += 1
                continue
            try:
                route_type = int(row.route_type) if row.route_type else 3
            except (TypeError, ValueError):
                route_type = 3
            vt_key = vehicle_type_keys.get(route_type, default_vt_key)

            delay_val = int(row.delay_seconds) if row.delay_seconds is not None else None
            fact_batch.append(
                {
                    "date_key": date_key,
                    "route_key": route_key,
                    "stop_key": stop_key,
                    "vehicle_type_key": vt_key,
                    "trip_id": row.trip_id,
                    "stop_sequence": int(row.stop_sequence),
                    "scheduled_arrival": row.scheduled_arrival,
                    "actual_arrival": row.actual_arrival,
                    "delay_seconds": delay_val,
                    "data_source": "gtfs_rt",
                }
            )
            if len(fact_batch) >= 5000:
                total_inserted += insert_facts(fact_batch)
                fact_batch = []

        if fact_batch:
            total_inserted += insert_facts(fact_batch)

        if skipped_no_dim:
            logger.warning(
                "Fact loop: skipped %d/%d rows missing a dim_route/dim_stop key "
                "(route_keys=%d, stop_keys=%d)",
                skipped_no_dim,
                rows_seen,
                len(route_keys),
                len(stop_keys),
            )

        record_pipeline_run(service_date, "success", total_inserted, dag_run_id)
        logger.info("Transform complete: %d fact rows loaded for %s", total_inserted, service_date)
        spark.stop()
        return total_inserted

    finally:
        shutil.rmtree(extract_dir, ignore_errors=True)


def main() -> int:
    parser = argparse.ArgumentParser(
        description="Transform GTFS raw data into Postgres star schema"
    )
    parser.add_argument("--service-date", required=True, help="Service date YYYY-MM-DD")
    parser.add_argument("--operator", default=OPERATOR)
    parser.add_argument("--operator-name", default=OPERATOR_NAME)
    parser.add_argument("--raw-base-path", default=str(DATA_RAW_DIR))
    parser.add_argument(
        "--sample-fraction",
        type=float,
        default=None,
        help="Optional fraction of trips to process (e.g. 0.05 for 5%% dev run)",
    )
    args = parser.parse_args()

    try:
        rows = run_transform(
            service_date=args.service_date,
            operator=args.operator,
            operator_name=args.operator_name,
            raw_base=Path(args.raw_base_path),
            sample_fraction=args.sample_fraction,
        )
        logger.info("Done at %s — %d fact rows", datetime.now(timezone.utc).isoformat(), rows)
    except Exception:
        logger.exception("Transform failed")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
