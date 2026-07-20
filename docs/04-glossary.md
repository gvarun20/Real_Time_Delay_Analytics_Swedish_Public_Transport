# Beginner glossary (data engineering terms in this project)

Read this anytime a word feels unclear.

| Term | Simple meaning | In this project |
|---|---|---|
| **ETL / pipeline** | Steps that move and clean data automatically | Airflow DAGs + jobs |
| **Ingest** | Download / collect raw data | `gtfs_static_ingest`, `gtfs_realtime_ingest` |
| **Landing zone** | Folder where raw files are saved unchanged | `data/raw/` |
| **Transform** | Clean, join, calculate new fields | `jobs/transform_gtfs.py` (PySpark) |
| **Orchestration** | Scheduling and watching jobs | Apache Airflow |
| **DAG** | Workflow graph: tasks + order | files in `dags/` |
| **GTFS** | Standard for transit schedules | static zip from Trafiklab |
| **GTFS-RT** | Live updates (delays, arrivals) | `tripupdates.pb` |
| **Protobuf (.pb)** | Compact binary message format | realtime feed file |
| **Kimball / star schema** | Analytics model: facts + dimensions | see `03-star-schema-explained.md` |
| **Fact** | Measurable event row | `fact_trip_delay`, `fact_route_energy_score` |
| **Energy score** | Relative 0–100 index (not kWh) | distance + duration + stops + delay |
| **Dimension** | Label / context table | `dim_route`, `dim_stop`, … |
| **Grain** | What one fact row means | trip × stop × date × sequence |
| **Surrogate key** | Integer ID created in the warehouse | `route_key`, `stop_key` |
| **Natural key** | ID from the source system | `route_id`, `stop_id` |
| **Upsert** | Insert or update if already exists | dimension loaders |
| **Data quality (DQ)** | Automatic checks that data looks sane | `validate_data_quality.py` |
| **CI** | Tests that run on every push | GitHub Actions `.github/workflows/ci.yml` |
| **CD (in our sense)** | Auto publish of docs/site on push | GitHub Pages from `/docs` |
| **Docker Compose** | Runs many services together locally | Airflow + Postgres |
| **Streamlit** | Python tool for interactive dashboards | `dashboard/app.py` |
| **Sample data** | Fixed CSV for public demo (no secrets) | `dashboard/sample_data/` |
| **ADR** | Architecture Decision Record | `docs/decisions/` |
| **Idempotent** | Safe to re-run without messing data up | upserts / delete-then-load per date |

## Delay sign convention

| `delay_seconds` | Meaning |
|---|---|
| `> 0` | Late |
| `= 0` | On time |
| `< 0` | Early |
| `NULL` | No realtime match (unknown) — **not** the same as 0 |
