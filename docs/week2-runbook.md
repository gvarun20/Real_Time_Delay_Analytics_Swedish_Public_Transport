# Week 2 — PySpark Transform

## Goal

Join static GTFS schedules with realtime TripUpdates, compute `delay_seconds`, load star schema.

```
data/raw/  →  jobs/transform_gtfs.py  →  Postgres (fact_trip_delay + dims)
```

## Manual run (VS Code)

```powershell
# Rebuild Airflow image after Week 2 changes (Java + PySpark)
docker compose build airflow-scheduler airflow-webserver
docker compose up -d --force-recreate airflow-scheduler airflow-webserver

# Quick test with 5% of SL trips (~faster)
.\scripts\run_transform.ps1 -ServiceDate 2026-07-12 -SampleFraction 0.05

# Full run for a date
.\scripts\run_transform.ps1 -ServiceDate 2026-07-12
```

## Verify Postgres

```powershell
docker compose exec postgres-analytics psql -U transit -d transit_dw -c "SELECT COUNT(*) FROM fact_trip_delay;"
docker compose exec postgres-analytics psql -U transit -d transit_dw -c "SELECT COUNT(*) FROM dim_route;"
docker compose exec postgres-analytics psql -U transit -d transit_dw -c "SELECT AVG(delay_seconds), COUNT(*) FROM fact_trip_delay;"
```

## Airflow DAG

Trigger **`gtfs_transform`** at http://localhost:8081 (requires static + realtime for that date).

## SL filtering

Static zip is all of Sweden (GTFS Sweden 3). Transform filters to **SL (Stockholm)** via `agency_id = 275` / agency name.

## Troubleshooting

If the transform matches 0 rows, loads 0 fact rows despite a successful join, or can't connect
to Postgres, see `docs/decisions/004-week2-transform-debugging.md` for the three bugs we hit
(feed-family ID mismatch, `POSTGRES_DB` misconfiguration, `execute_values` pagination) and their
fixes. Run `python scripts/check_feed_access.py` first if you suspect an API key/feed mismatch.

## Progress tracking

See `docs/WEEK2_CHECKLIST.md` for the full Week 2 completion checklist and current status.
