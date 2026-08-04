"""Export delay + energy sample CSVs for public Streamlit Cloud demos.

Usage (Docker Postgres must be up and have fact rows):

    py scripts/export_dashboard_sample.py

Writes:
  dashboard/sample_data/delay_facts.csv.gz
  dashboard/sample_data/energy_scores.csv.gz
"""

from __future__ import annotations

import sys
from pathlib import Path

import pandas as pd
from sqlalchemy import create_engine, text

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import postgres_url  # noqa: E402

DELAY_OUT = PROJECT_ROOT / "dashboard" / "sample_data" / "delay_facts.csv.gz"
ENERGY_OUT = PROJECT_ROOT / "dashboard" / "sample_data" / "energy_scores.csv.gz"

DELAY_SQL = """
SELECT
    f.date_key,
    d.full_date,
    d.day_name,
    d.day_of_week,
    f.trip_id,
    f.stop_sequence,
    f.scheduled_arrival,
    f.actual_arrival,
    f.delay_seconds,
    f.data_source,
    r.route_id,
    r.route_short_name,
    r.route_long_name,
    s.stop_id,
    s.stop_name,
    s.stop_lat,
    s.stop_lon,
    vt.type_name,
    EXTRACT(HOUR FROM f.scheduled_arrival)::int AS hour_of_day
FROM fact_trip_delay f
JOIN dim_date d ON f.date_key = d.date_key
JOIN dim_route r ON f.route_key = r.route_key
JOIN dim_stop s ON f.stop_key = s.stop_key
JOIN dim_vehicle_type vt ON f.vehicle_type_key = vt.vehicle_type_key
ORDER BY f.date_key, f.trip_id, f.stop_sequence
"""

ENERGY_SQL = """
SELECT
    e.date_key,
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
JOIN dim_date d ON e.date_key = d.date_key
JOIN dim_route r ON e.route_key = r.route_key
ORDER BY e.date_key, e.region_id, e.energy_score DESC
"""


def _write_gz(df: pd.DataFrame, path: Path, label: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(path, index=False, compression="gzip")
    size_mb = path.stat().st_size / (1024 * 1024)
    print(f"Wrote {len(df):,} {label} rows -> {path} ({size_mb:.2f} MB)")


def main() -> int:
    engine = create_engine(postgres_url(), pool_pre_ping=True)
    with engine.connect() as conn:
        delays = pd.read_sql(text(DELAY_SQL), conn)
        energy = pd.read_sql(text(ENERGY_SQL), conn)

    if delays.empty:
        print("ERROR: No rows in fact_trip_delay. Run gtfs_transform first.")
        return 1

    _write_gz(delays, DELAY_OUT, "delay")

    if energy.empty:
        print(
            "WARN: No energy scores yet. Run:\n"
            "  py jobs/compute_route_energy_scores.py --service-date YYYY-MM-DD --region all"
        )
    else:
        _write_gz(energy, ENERGY_OUT, "energy")

    print("Commit the sample_data files, then Streamlit Cloud will pick them up on next deploy.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
