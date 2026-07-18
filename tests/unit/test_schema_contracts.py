"""Unit tests: star schema DDL contracts (no live Postgres required)."""

from __future__ import annotations

from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]
SCHEMA_SQL = (PROJECT_ROOT / "sql" / "schema.sql").read_text(encoding="utf-8")

REQUIRED_TABLES = {
    "dim_date",
    "dim_route",
    "dim_stop",
    "dim_vehicle_type",
    "fact_trip_delay",
    "pipeline_runs",
}

FACT_REQUIRED_COLUMNS = {
    "delay_key",
    "date_key",
    "route_key",
    "stop_key",
    "vehicle_type_key",
    "trip_id",
    "stop_sequence",
    "scheduled_arrival",
    "actual_arrival",
    "delay_seconds",
    "data_source",
}


def test_schema_sql_defines_all_star_tables():
    for table in REQUIRED_TABLES:
        assert f"CREATE TABLE IF NOT EXISTS {table}" in SCHEMA_SQL, f"missing {table}"


def test_fact_trip_delay_has_required_columns():
    start = SCHEMA_SQL.index("CREATE TABLE IF NOT EXISTS fact_trip_delay")
    end = SCHEMA_SQL.index(");", start)
    fact_block = SCHEMA_SQL[start:end]
    for column in FACT_REQUIRED_COLUMNS:
        assert column in fact_block, f"fact_trip_delay missing column {column}"


def test_fact_grain_unique_constraint_exists():
    assert "UNIQUE (trip_id, stop_key, date_key, stop_sequence)" in SCHEMA_SQL


def test_fact_foreign_keys_reference_dimensions():
    assert "REFERENCES dim_date(date_key)" in SCHEMA_SQL
    assert "REFERENCES dim_route(route_key)" in SCHEMA_SQL
    assert "REFERENCES dim_stop(stop_key)" in SCHEMA_SQL
    assert "REFERENCES dim_vehicle_type(vehicle_type_key)" in SCHEMA_SQL


def test_pipeline_runs_has_dq_status_column():
    start = SCHEMA_SQL.index("CREATE TABLE IF NOT EXISTS pipeline_runs")
    end = SCHEMA_SQL.index(");", start)
    assert "dq_status" in SCHEMA_SQL[start:end]
