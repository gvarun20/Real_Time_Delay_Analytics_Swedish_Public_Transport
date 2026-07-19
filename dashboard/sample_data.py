"""Load and filter the public demo dataset (CSV) for Streamlit Cloud.

The live pipeline still uses PostgreSQL locally. Public hosting cannot reach
your Docker Postgres, so we ship a denormalized sample export under
`dashboard/sample_data/delay_facts.csv.gz`.
"""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

import pandas as pd

from dashboard.filters import Filters

SAMPLE_PATH = Path(__file__).resolve().parent / "sample_data" / "delay_facts.csv.gz"

DAY_ORDER = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]


def sample_file_exists() -> bool:
    return SAMPLE_PATH.exists()


@lru_cache(maxsize=1)
def load_facts() -> pd.DataFrame:
    if not SAMPLE_PATH.exists():
        return pd.DataFrame()
    df = pd.read_csv(SAMPLE_PATH, compression="gzip")
    df["full_date"] = pd.to_datetime(df["full_date"]).dt.date
    if "scheduled_arrival" in df.columns:
        df["scheduled_arrival"] = pd.to_datetime(df["scheduled_arrival"], errors="coerce")
        if "hour_of_day" not in df.columns:
            df["hour_of_day"] = df["scheduled_arrival"].dt.hour
    return df


def _apply_filters(df: pd.DataFrame, filters: Filters) -> pd.DataFrame:
    if df.empty:
        return df
    out = df[
        (df["full_date"] >= filters.start_date) & (df["full_date"] <= filters.end_date)
    ]
    if filters.route_ids:
        out = out[out["route_id"].isin(filters.route_ids)]
    if filters.vehicle_types:
        out = out[out["type_name"].isin(filters.vehicle_types)]
    return out


def get_available_date_range() -> tuple:
    df = load_facts()
    if df.empty:
        return None, None
    return df["full_date"].min(), df["full_date"].max()


def get_available_routes() -> pd.DataFrame:
    df = load_facts()
    if df.empty:
        return pd.DataFrame(columns=["route_id", "route_short_name"])
    return (
        df[["route_id", "route_short_name"]]
        .drop_duplicates()
        .sort_values("route_short_name")
        .reset_index(drop=True)
    )


def get_available_vehicle_types() -> pd.DataFrame:
    df = load_facts()
    if df.empty:
        return pd.DataFrame(columns=["type_name"])
    return (
        df[["type_name"]]
        .drop_duplicates()
        .sort_values("type_name")
        .reset_index(drop=True)
    )


def get_kpis(filters: Filters) -> dict:
    df = _apply_filters(load_facts(), filters)
    if df.empty:
        return {
            "total_facts": 0,
            "trips_observed": 0,
            "median_delay_sec": None,
            "on_time_rate": None,
            "observed_delay_count": 0,
            "worst_route": "N/A",
        }
    delays = df["delay_seconds"].dropna()
    on_time_rate = float((delays <= 0).mean()) if len(delays) else None
    worst = "N/A"
    if len(delays):
        by_route = (
            df.dropna(subset=["delay_seconds"])
            .groupby("route_short_name")["delay_seconds"]
            .mean()
            .sort_values(ascending=False)
        )
        if not by_route.empty:
            worst = str(by_route.index[0])
    return {
        "total_facts": int(len(df)),
        "trips_observed": int(df["trip_id"].nunique()),
        "median_delay_sec": float(delays.median()) if len(delays) else None,
        "on_time_rate": on_time_rate,
        "observed_delay_count": int(len(delays)),
        "worst_route": worst,
    }


def get_avg_delay_by_route(filters: Filters, limit: int = 20) -> pd.DataFrame:
    df = _apply_filters(load_facts(), filters).dropna(subset=["delay_seconds"])
    if df.empty:
        return pd.DataFrame(columns=["route_short_name", "avg_delay_sec", "n_observations"])
    out = (
        df.groupby("route_short_name", as_index=False)
        .agg(avg_delay_sec=("delay_seconds", "mean"), n_observations=("delay_seconds", "size"))
        .sort_values("avg_delay_sec", ascending=False)
        .head(limit)
    )
    return out.reset_index(drop=True)


def get_delay_heatmap(filters: Filters) -> pd.DataFrame:
    df = _apply_filters(load_facts(), filters).dropna(subset=["delay_seconds"])
    if df.empty:
        return pd.DataFrame(columns=["day_name", "day_of_week", "hour_of_day", "avg_delay_sec"])
    out = (
        df.groupby(["day_name", "day_of_week", "hour_of_day"], as_index=False)
        .agg(avg_delay_sec=("delay_seconds", "mean"))
        .sort_values(["day_of_week", "hour_of_day"])
    )
    return out.reset_index(drop=True)


def get_worst_stops(filters: Filters, limit: int = 10) -> pd.DataFrame:
    df = _apply_filters(load_facts(), filters).dropna(subset=["delay_seconds"])
    if df.empty:
        return pd.DataFrame(columns=["stop_name", "stop_id", "avg_delay_sec", "n_observations"])
    out = (
        df.groupby(["stop_name", "stop_id"], as_index=False)
        .agg(avg_delay_sec=("delay_seconds", "mean"), n_observations=("delay_seconds", "size"))
    )
    out = out[out["n_observations"] >= 3].sort_values("avg_delay_sec", ascending=False).head(limit)
    return out.reset_index(drop=True)


def get_stops_map_data(filters: Filters) -> pd.DataFrame:
    df = _apply_filters(load_facts(), filters).dropna(
        subset=["delay_seconds", "stop_lat", "stop_lon"]
    )
    if df.empty:
        return pd.DataFrame(
            columns=["stop_name", "stop_lat", "stop_lon", "avg_delay_sec", "n_observations"]
        )
    out = (
        df.groupby(["stop_name", "stop_lat", "stop_lon"], as_index=False)
        .agg(avg_delay_sec=("delay_seconds", "mean"), n_observations=("delay_seconds", "size"))
    )
    return out.reset_index(drop=True)


def get_delay_distribution(filters: Filters, sample_limit: int = 20000) -> pd.DataFrame:
    df = _apply_filters(load_facts(), filters).dropna(subset=["delay_seconds"])
    if df.empty:
        return pd.DataFrame(columns=["delay_seconds"])
    return df[["delay_seconds"]].head(sample_limit).reset_index(drop=True)
