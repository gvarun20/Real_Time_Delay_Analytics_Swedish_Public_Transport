# Week 3 — Dashboard + Data Quality + Tests

## Goal

Serve the star schema through a read-only Streamlit dashboard, gate the pipeline on automated
data quality checks, and expand pytest coverage (unit + integration).

```
Postgres (star schema)  →  jobs/validate_data_quality.py  →  pipeline_runs.dq_status
Postgres (star schema)  →  dashboard/queries.py  →  dashboard/app.py (Streamlit)
```

## Run the dashboard (host-side)

```powershell
pip install -r requirements.txt   # picks up streamlit, plotly, pandas
streamlit run dashboard/app.py
```

Opens at `http://localhost:8501`. Reads directly from `postgres-analytics` (uses the same
`.env` / `config/settings.py` as everything else — make sure `POSTGRES_HOST=localhost` and
`POSTGRES_PORT=5433` are set for host-side access, per `.env.example`).

The dashboard is entirely **read-only** — no writes ever go through `dashboard/queries.py`.

## Run data quality checks manually

```powershell
docker compose exec -T airflow-scheduler python /opt/airflow/project/jobs/validate_data_quality.py --service-date 2026-07-12
```

Exits non-zero (and logs `ERROR`) if any ERROR-severity check fails (see check catalog below).
WARN-severity checks are logged but do not fail the run.

## Data quality check catalog

| Check ID | Rule | Severity | Notes |
|---|---|---|---|
| DQ-001 | `fact_trip_delay` row count > 0 for service_date | ERROR | Fails the DAG if a date has zero facts |
| DQ-002 | No NULL `trip_id` in facts | ERROR | Also enforced by `NOT NULL` at the DB level |
| DQ-003 | `delay_seconds` within [-3600, 10800]s | WARN | Logs count of outliers, does not fail |
| DQ-004 | `delay_seconds` NULL rate < 80% | WARN | Logs realtime coverage |
| DQ-006 | No duplicate `(trip_id, stop_key, date_key, stop_sequence)` rows | ERROR | Also enforced by the `UNIQUE` constraint |
| DQ-007 | Static GTFS file age < 7 days | WARN | Reads `data/raw/static/{date}/metadata.json` |

(DQ-005 — "all `route_key` exist in `dim_route`" — is enforced unconditionally by the `FOREIGN KEY`
constraint on `fact_trip_delay.route_key`, so it's not implemented as a separate app-level check.)

## Airflow DAG

`gtfs_transform` now chains: `[wait_for_static_gtfs, check_realtime_snapshot] >> transform_with_pyspark
>> validate_data_quality`. The new `validate_data_quality` task raises `DataQualityError` (failing
the task/DAG run) only on ERROR-severity failures, and always writes the resulting status
(`passed` / `warn` / `failed`) to `pipeline_runs.dq_status`.

## Tests

```powershell
py -m ruff check .
py -m pytest -q                                    # unit + integration
py -m pytest tests/unit -q                          # unit only, no DB needed
py -m pytest tests/integration -q                   # needs postgres-analytics running (else auto-skips)
py -m pytest --cov=jobs --cov=config --cov=dashboard --cov-report=term-missing -q
```

Integration tests in `tests/integration/` auto-skip (not fail) if Postgres isn't reachable, so
`pytest` stays green with no Docker running. In CI, `.github/workflows/ci.yml` spins up a real
`postgres:15` service container and loads `sql/schema.sql` first, so integration tests run for
real on every push.

## Troubleshooting

For Week 1/2 issues (feed mismatches, `POSTGRES_DB` misconfig, `execute_values` pagination,
missing `fs_default` connection, `CardinalityViolation`), see
`docs/decisions/004-week2-transform-debugging.md`.

## Progress tracking

See `docs/WEEK3_CHECKLIST.md` for the full Week 3 completion checklist.

**Week 3 status: complete.** Phase gate met (dashboard on Postgres, DQ fails on bad data,
tests green). Public hosting / demo video / README polish belong to Week 4.
