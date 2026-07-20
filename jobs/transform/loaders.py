"""Load dimension and fact tables into PostgreSQL."""

from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import psycopg2
from psycopg2.extras import execute_values

from config.settings import (
    POSTGRES_DB,
    POSTGRES_HOST,
    POSTGRES_PASSWORD,
    POSTGRES_PORT,
    POSTGRES_USER,
)

logger = logging.getLogger(__name__)


def get_connection():
    return psycopg2.connect(
        host=POSTGRES_HOST,
        port=POSTGRES_PORT,
        dbname=POSTGRES_DB,
        user=POSTGRES_USER,
        password=POSTGRES_PASSWORD,
    )


def upsert_routes(rows: list[dict[str, Any]], operator: str) -> dict[str, int]:
    """Upsert dim_route and return route_id -> route_key map."""
    if not rows:
        return {}

    sql = """
        INSERT INTO dim_route (route_id, route_short_name, route_long_name, operator)
        VALUES %s
        ON CONFLICT (route_id, operator) DO UPDATE SET
            route_short_name = EXCLUDED.route_short_name,
            route_long_name = EXCLUDED.route_long_name
        RETURNING route_id, route_key
    """
    values = [
        (r["route_id"], r.get("route_short_name"), r.get("route_long_name"), operator)
        for r in rows
    ]

    mapping: dict[str, int] = {}
    with get_connection() as conn:
        with conn.cursor() as cur:
            # fetch=True is required so RETURNING rows from EVERY page are kept — without it,
            # execute_values() silently discards RETURNING output from all but the last
            # internal page (default page_size=100), so this map would be missing most rows.
            returned = execute_values(cur, sql, values, fetch=True)
            for route_id, route_key in returned:
                mapping[route_id] = route_key
        conn.commit()
    logger.info("Upserted %d routes", len(mapping))
    return mapping


def upsert_stops(rows: list[dict[str, Any]], operator: str) -> dict[str, int]:
    """Upsert dim_stop and return stop_id -> stop_key map."""
    if not rows:
        return {}

    sql = """
        INSERT INTO dim_stop (stop_id, stop_name, stop_lat, stop_lon, operator)
        VALUES %s
        ON CONFLICT (stop_id, operator) DO UPDATE SET
            stop_name = EXCLUDED.stop_name,
            stop_lat = EXCLUDED.stop_lat,
            stop_lon = EXCLUDED.stop_lon
        RETURNING stop_id, stop_key
    """
    values = [
        (r["stop_id"], r.get("stop_name"), r.get("stop_lat"), r.get("stop_lon"), operator)
        for r in rows
    ]

    mapping: dict[str, int] = {}
    with get_connection() as conn:
        with conn.cursor() as cur:
            # See comment in upsert_routes() — fetch=True is required to get RETURNING rows
            # from every page, not just the last one.
            returned = execute_values(cur, sql, values, fetch=True)
            for stop_id, stop_key in returned:
                mapping[stop_id] = stop_key
        conn.commit()
    logger.info("Upserted %d stops", len(mapping))
    return mapping


def get_vehicle_type_keys() -> dict[int, int]:
    """Return gtfs_route_type -> vehicle_type_key from dim_vehicle_type."""
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                "SELECT gtfs_route_type, vehicle_type_key FROM dim_vehicle_type"
            )
            return {int(gtfs_type): int(key) for gtfs_type, key in cur.fetchall()}


def delete_facts_for_date(date_key: int) -> int:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute("DELETE FROM fact_trip_delay WHERE date_key = %s", (date_key,))
            deleted = cur.rowcount
        conn.commit()
    logger.info("Deleted %d existing fact rows for date_key=%s", deleted, date_key)
    return deleted


def insert_facts(rows: list[dict[str, Any]], batch_size: int = 5000) -> int:
    if not rows:
        return 0

    sql = """
        INSERT INTO fact_trip_delay (
            date_key, route_key, stop_key, vehicle_type_key,
            trip_id, stop_sequence, scheduled_arrival, actual_arrival,
            delay_seconds, data_source
        ) VALUES %s
        ON CONFLICT (trip_id, stop_key, date_key, stop_sequence) DO UPDATE SET
            scheduled_arrival = EXCLUDED.scheduled_arrival,
            actual_arrival = EXCLUDED.actual_arrival,
            delay_seconds = EXCLUDED.delay_seconds,
            data_source = EXCLUDED.data_source
    """
    values = [
        (
            r["date_key"],
            r["route_key"],
            r["stop_key"],
            r["vehicle_type_key"],
            r["trip_id"],
            r["stop_sequence"],
            r["scheduled_arrival"],
            r.get("actual_arrival"),
            r.get("delay_seconds"),
            r.get("data_source", "gtfs_rt"),
        )
        for r in rows
    ]

    inserted = 0
    with get_connection() as conn:
        with conn.cursor() as cur:
            for i in range(0, len(values), batch_size):
                batch = values[i : i + batch_size]
                execute_values(cur, sql, batch)
                inserted += len(batch)
        conn.commit()
    logger.info("Inserted/updated %d fact rows", inserted)
    return inserted


def record_pipeline_run(
    service_date: str,
    status: str,
    rows_fact: int,
    dag_run_id: str | None = None,
) -> None:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                INSERT INTO pipeline_runs (dag_run_id, service_date, finished_at, status, rows_fact)
                VALUES (%s, %s, NOW(), %s, %s)
                """,
                (dag_run_id, service_date, status, rows_fact),
            )
        conn.commit()


def update_dq_status(
    service_date: str,
    dq_status: str,
    dag_run_id: str | None = None,
) -> None:
    """Set dq_status on the pipeline_runs row for this service_date.

    Prefers matching by dag_run_id (unambiguous); falls back to the most
    recently finished run for that service_date if no dag_run_id is given.
    """
    with get_connection() as conn:
        with conn.cursor() as cur:
            if dag_run_id:
                cur.execute(
                    """
                    UPDATE pipeline_runs SET dq_status = %s
                    WHERE service_date = %s AND dag_run_id = %s
                    """,
                    (dq_status, service_date, dag_run_id),
                )
            if not dag_run_id or cur.rowcount == 0:
                cur.execute(
                    """
                    UPDATE pipeline_runs SET dq_status = %s
                    WHERE run_id = (
                        SELECT run_id FROM pipeline_runs
                        WHERE service_date = %s
                        ORDER BY finished_at DESC NULLS LAST
                        LIMIT 1
                    )
                    """,
                    (dq_status, service_date),
                )
        conn.commit()


def ensure_energy_score_table() -> None:
    """Create fact_route_energy_score if missing (safe on existing Docker volumes)."""
    ddl_path = Path(__file__).resolve().parents[2] / "sql" / "energy_score.sql"
    ddl = ddl_path.read_text(encoding="utf-8")
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(ddl)
        conn.commit()
    logger.info("Ensured fact_route_energy_score exists")


def delete_energy_scores_for_date(date_key: int, region_id: str) -> int:
    with get_connection() as conn:
        with conn.cursor() as cur:
            cur.execute(
                """
                DELETE FROM fact_route_energy_score
                WHERE date_key = %s AND region_id = %s
                """,
                (date_key, region_id),
            )
            deleted = cur.rowcount
        conn.commit()
    logger.info(
        "Deleted %d energy score rows for date_key=%s region=%s",
        deleted,
        date_key,
        region_id,
    )
    return deleted


def upsert_route_energy_scores(rows: list[dict[str, Any]]) -> int:
    if not rows:
        return 0

    sql = """
        INSERT INTO fact_route_energy_score (
            date_key, route_key, vehicle_type_key, region_id, region_name,
            trip_count, total_km, avg_km, total_hours, p90_hours, avg_stops,
            delay_hours, raw_score, energy_score, is_flagged, flag_reasons, data_source
        ) VALUES %s
        ON CONFLICT (date_key, route_key, region_id) DO UPDATE SET
            vehicle_type_key = EXCLUDED.vehicle_type_key,
            region_name = EXCLUDED.region_name,
            trip_count = EXCLUDED.trip_count,
            total_km = EXCLUDED.total_km,
            avg_km = EXCLUDED.avg_km,
            total_hours = EXCLUDED.total_hours,
            p90_hours = EXCLUDED.p90_hours,
            avg_stops = EXCLUDED.avg_stops,
            delay_hours = EXCLUDED.delay_hours,
            raw_score = EXCLUDED.raw_score,
            energy_score = EXCLUDED.energy_score,
            is_flagged = EXCLUDED.is_flagged,
            flag_reasons = EXCLUDED.flag_reasons,
            data_source = EXCLUDED.data_source,
            computed_at = NOW()
    """
    values = [
        (
            r["date_key"],
            r["route_key"],
            r["vehicle_type_key"],
            r["region_id"],
            r["region_name"],
            r["trip_count"],
            r["total_km"],
            r["avg_km"],
            r["total_hours"],
            r["p90_hours"],
            r["avg_stops"],
            r["delay_hours"],
            r["raw_score"],
            r["energy_score"],
            r["is_flagged"],
            r["flag_reasons"],
            r.get("data_source", "estimate_v1"),
        )
        for r in rows
    ]
    with get_connection() as conn:
        with conn.cursor() as cur:
            execute_values(cur, sql, values)
        conn.commit()
    logger.info("Upserted %d route energy score rows", len(values))
    return len(values)
