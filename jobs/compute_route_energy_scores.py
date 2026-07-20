"""Compute relative route energy scores from fact_trip_delay (Strategy C).

Usage:
    py jobs/compute_route_energy_scores.py --service-date 2026-07-12
    py jobs/compute_route_energy_scores.py --service-date 2026-07-12 --region inner_stockholm

Produces unitless 0-100 energy_score values — NOT measured kWh.
"""

from __future__ import annotations

import argparse
import logging
import sys
from collections import defaultdict
from datetime import date
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from jobs.energy.scoring import (  # noqa: E402
    REGION_PRESETS,
    TripEnergyFeatures,
    build_flag_reasons,
    min_max_scale,
    path_length_km,
    percentile,
    route_in_region,
    trip_duration_hours,
)
from jobs.transform.loaders import (  # noqa: E402
    delete_energy_scores_for_date,
    ensure_energy_score_table,
    get_connection,
    upsert_route_energy_scores,
)
from jobs.transform.time_utils import date_to_date_key  # noqa: E402

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger(__name__)

FETCH_SQL = """
SELECT
    f.date_key,
    f.route_key,
    f.vehicle_type_key,
    f.trip_id,
    f.stop_sequence,
    f.scheduled_arrival,
    f.actual_arrival,
    f.delay_seconds,
    s.stop_lat,
    s.stop_lon,
    vt.type_name
FROM fact_trip_delay f
JOIN dim_stop s ON f.stop_key = s.stop_key
JOIN dim_vehicle_type vt ON f.vehicle_type_key = vt.vehicle_type_key
WHERE f.date_key = %s
  AND vt.type_name = 'Bus'
ORDER BY f.trip_id, f.stop_sequence
"""


def _fetch_bus_rows(date_key: int) -> list[tuple]:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(FETCH_SQL, (date_key,))
            return cur.fetchall()


def build_trip_features(
    rows: list[tuple],
    region_id: str,
) -> list[TripEnergyFeatures]:
    preset = REGION_PRESETS.get(region_id) or REGION_PRESETS["all"]
    bbox = preset["bbox"]

    trips: dict[str, list[tuple]] = defaultdict(list)
    for row in rows:
        trips[row[3]].append(row)  # trip_id

    features: list[TripEnergyFeatures] = []
    for trip_id, stop_rows in trips.items():
        stop_rows = sorted(stop_rows, key=lambda r: int(r[4]))
        points: list[tuple[float, float]] = []
        for r in stop_rows:
            lat, lon = r[8], r[9]
            if lat is None or lon is None:
                continue
            points.append((float(lat), float(lon)))

        if len(points) < 2:
            continue
        if not route_in_region(points, bbox):
            continue

        first, last = stop_rows[0], stop_rows[-1]
        hours = trip_duration_hours(
            first[5],
            last[5],
            first[6],
            last[6],
        )
        if hours <= 0:
            continue

        delay_seconds = sum(max(0, int(r[7])) for r in stop_rows if r[7] is not None)
        features.append(
            TripEnergyFeatures(
                trip_id=trip_id,
                route_key=int(first[1]),
                vehicle_type_key=int(first[2]),
                date_key=int(first[0]),
                km=path_length_km(points),
                hours=hours,
                n_stops=len(points),
                delay_hours=delay_seconds / 3600.0,
            )
        )
    return features


def aggregate_routes(
    features: list[TripEnergyFeatures],
    region_id: str,
) -> list[dict]:
    if not features:
        return []

    preset = REGION_PRESETS.get(region_id) or REGION_PRESETS["all"]
    region_name = preset["name"]

    by_route: dict[int, list[TripEnergyFeatures]] = defaultdict(list)
    for feat in features:
        by_route[feat.route_key].append(feat)

    # Trip-level raw scores for route averages, then min-max across routes
    route_rows: list[dict] = []
    for route_key, trips in by_route.items():
        kms = [t.km for t in trips]
        hours = [t.hours for t in trips]
        stops = [float(t.n_stops) for t in trips]
        delays = [t.delay_hours for t in trips]
        raws = [t.raw_score for t in trips]
        vt_key = trips[0].vehicle_type_key
        date_key = trips[0].date_key

        total_km = sum(kms)
        total_hours = sum(hours)
        trip_count = len(trips)
        avg_km = total_km / trip_count
        avg_stops = sum(stops) / trip_count
        delay_hours = sum(delays)
        p90_hours = percentile(hours, 90)
        raw_score = sum(raws) / trip_count

        route_rows.append(
            {
                "date_key": date_key,
                "route_key": route_key,
                "vehicle_type_key": vt_key,
                "region_id": region_id,
                "region_name": region_name,
                "trip_count": trip_count,
                "total_km": total_km,
                "avg_km": avg_km,
                "total_hours": total_hours,
                "p90_hours": p90_hours,
                "avg_stops": avg_stops,
                "delay_hours": delay_hours,
                "raw_score": raw_score,
            }
        )

    scaled = min_max_scale([r["raw_score"] for r in route_rows])
    for row, score in zip(route_rows, scaled, strict=True):
        row["energy_score"] = score

    # Quartile thresholds for reason tags (p75 within this region/date set)
    km_vals = [r["avg_km"] for r in route_rows]
    hour_vals = [r["p90_hours"] for r in route_rows]
    spk_vals = [
        (r["avg_stops"] / r["avg_km"]) if r["avg_km"] > 0.05 else 0.0 for r in route_rows
    ]
    dr_vals = [
        (r["delay_hours"] / r["total_hours"]) if r["total_hours"] > 0.05 else 0.0
        for r in route_rows
    ]
    tc_vals = [float(r["trip_count"]) for r in route_rows]
    hpk_vals = [
        (r["p90_hours"] / r["avg_km"]) if r["avg_km"] > 0.05 else 0.0 for r in route_rows
    ]

    km_p75 = percentile(km_vals, 75)
    hours_p75 = percentile(hour_vals, 75)
    spk_p75 = percentile(spk_vals, 75)
    dr_p75 = percentile(dr_vals, 75)
    tc_p75 = percentile(tc_vals, 75)
    hpk_p75 = percentile(hpk_vals, 75)

    score_cutoff = percentile([r["energy_score"] for r in route_rows], 90)
    hours_cutoff = percentile(hour_vals, 75)

    for row in route_rows:
        reasons = build_flag_reasons(
            km=row["avg_km"],
            hours=row["p90_hours"],
            stops=row["avg_stops"],
            delay_hours=row["delay_hours"],
            trip_count=row["trip_count"],
            km_p75=km_p75,
            hours_p75=hours_p75,
            stops_per_km_p75=spk_p75,
            delay_ratio_p75=dr_p75,
            trip_count_p75=tc_p75,
            hours_per_km_p75=hpk_p75,
        )
        flagged = row["energy_score"] >= score_cutoff and row["p90_hours"] >= hours_cutoff
        row["is_flagged"] = bool(flagged)
        row["flag_reasons"] = ",".join(reasons) if reasons else ""
        row["data_source"] = "estimate_v1"

    return route_rows


def run_compute(service_date: str | date, region_id: str = "all") -> int:
    if isinstance(service_date, date):
        service_date = service_date.isoformat()
    if region_id not in REGION_PRESETS:
        raise ValueError(f"Unknown region_id={region_id!r}. Choose from {list(REGION_PRESETS)}")

    date_key = date_to_date_key(service_date)
    ensure_energy_score_table()
    rows = _fetch_bus_rows(date_key)
    logger.info("Fetched %d bus stop-level fact rows for %s", len(rows), service_date)
    if not rows:
        logger.warning("No bus facts for %s — nothing to score", service_date)
        return 0

    features = build_trip_features(rows, region_id)
    logger.info("Built features for %d trips in region=%s", len(features), region_id)
    aggregates = aggregate_routes(features, region_id)
    delete_energy_scores_for_date(date_key, region_id)
    inserted = upsert_route_energy_scores(aggregates)
    flagged = sum(1 for r in aggregates if r["is_flagged"])
    logger.info(
        "Wrote %d route energy scores for %s / %s (%d flagged)",
        inserted,
        service_date,
        region_id,
        flagged,
    )
    return inserted


def main() -> int:
    parser = argparse.ArgumentParser(description="Compute relative route energy scores")
    parser.add_argument("--service-date", required=True, help="YYYY-MM-DD")
    parser.add_argument(
        "--region",
        default="all",
        choices=sorted(REGION_PRESETS.keys()),
        help="Region preset id",
    )
    args = parser.parse_args()
    try:
        run_compute(args.service_date, region_id=args.region)
    except Exception:
        logger.exception("Energy score compute failed")
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
