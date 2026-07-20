"""Queries for the relative route energy score dashboard page."""

from __future__ import annotations

from datetime import date

import pandas as pd
from sqlalchemy import text

from dashboard.queries import get_engine, using_sample_data
from jobs.energy.scoring import REGION_PRESETS
from jobs.transform.time_utils import date_to_date_key


def list_regions() -> list[tuple[str, str]]:
    return [(rid, meta["name"]) for rid, meta in REGION_PRESETS.items()]


def get_energy_scores(
    start_date: date,
    end_date: date,
    region_id: str = "all",
) -> pd.DataFrame:
    """Return route energy scores for the date range + region.

    Empty when using sample/public mode without energy CSV (local Postgres only for v1).
    """
    if using_sample_data():
        return pd.DataFrame()

    start_key = date_to_date_key(start_date)
    end_key = date_to_date_key(end_date)
    sql = text(
        """
        SELECT
            d.full_date,
            e.region_id,
            e.region_name,
            r.route_id,
            r.route_short_name,
            r.route_long_name,
            e.trip_count,
            e.avg_km,
            e.total_km,
            e.p90_hours,
            e.total_hours,
            e.avg_stops,
            e.delay_hours,
            e.energy_score,
            e.is_flagged,
            e.flag_reasons
        FROM fact_route_energy_score e
        JOIN dim_route r ON e.route_key = r.route_key
        JOIN dim_date d ON e.date_key = d.date_key
        WHERE e.date_key BETWEEN :start_key AND :end_key
          AND e.region_id = :region_id
        ORDER BY e.energy_score DESC, e.p90_hours DESC
        """
    )
    with get_engine().connect() as conn:
        return pd.read_sql(
            sql,
            conn,
            params={
                "start_key": start_key,
                "end_key": end_key,
                "region_id": region_id,
            },
        )


def aggregate_energy_for_view(df: pd.DataFrame) -> pd.DataFrame:
    """Collapse multi-day rows to one row per route (mean score, max p90 hours)."""
    if df.empty:
        return df
    grouped = (
        df.groupby(["route_id", "route_short_name", "route_long_name"], as_index=False)
        .agg(
            trip_count=("trip_count", "sum"),
            avg_km=("avg_km", "mean"),
            total_km=("total_km", "sum"),
            p90_hours=("p90_hours", "max"),
            total_hours=("total_hours", "sum"),
            avg_stops=("avg_stops", "mean"),
            delay_hours=("delay_hours", "sum"),
            energy_score=("energy_score", "mean"),
            is_flagged=("is_flagged", "max"),
            flag_reasons=("flag_reasons", "first"),
        )
        .sort_values("energy_score", ascending=False)
    )
    return grouped.reset_index(drop=True)
