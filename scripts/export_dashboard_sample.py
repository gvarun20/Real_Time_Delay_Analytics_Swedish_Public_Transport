"""Export a denormalized delay-facts CSV for public Streamlit Cloud demos.

Usage (Docker Postgres must be up and have fact rows):

    py scripts/export_dashboard_sample.py

Writes: dashboard/sample_data/delay_facts.csv.gz
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

OUT_PATH = PROJECT_ROOT / "dashboard" / "sample_data" / "delay_facts.csv.gz"

SQL = """
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


def main() -> int:
    engine = create_engine(postgres_url(), pool_pre_ping=True)
    with engine.connect() as conn:
        df = pd.read_sql(text(SQL), conn)

    if df.empty:
        print("ERROR: No rows in fact_trip_delay. Run gtfs_transform first.")
        return 1

    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    df.to_csv(OUT_PATH, index=False, compression="gzip")
    size_mb = OUT_PATH.stat().st_size / (1024 * 1024)
    print(f"Wrote {len(df):,} rows → {OUT_PATH} ({size_mb:.2f} MB)")
    print("Commit this file, then deploy dashboard/app.py on Streamlit Community Cloud.")
    return 0


if __name__ == "__main__":
    sys.exit(main())
