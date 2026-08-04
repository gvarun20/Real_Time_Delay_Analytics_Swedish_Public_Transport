# Week 1 Completion Checklist

Use this to confirm Week 1 is **fully done** before starting PySpark (Week 2).

> **Feed pairing (important):** static and realtime must be the **same ID family**, or Week 2 joins return 0 rows.  
> Use `STATIC_FEED=gtfs_sweden_3` and `REALTIME_FEED=gtfs_sweden` (not `gtfs_regional`).  
> See [decisions/003-ingest-feed-types.md](decisions/003-ingest-feed-types.md).

## Environment

- [x] Docker Desktop running
- [x] `docker compose ps` shows healthy `transit-delay-pipeline-*` containers
- [x] Airflow UI opens at http://localhost:8081 (`admin` / `admin`)
- [x] `.env` has both API keys (not placeholders)
- [x] `STATIC_FEED=gtfs_sweden_3` and `REALTIME_FEED=gtfs_sweden`

## API access

- [x] `scripts/test_api_key.py` returns **OK: Both keys work**
- [x] Static test: HTTP 200
- [x] Realtime test: HTTP 200

## Raw data landing

- [x] `data/raw/static/YYYY-MM-DD/gtfs.zip` exists (large file, ~800MB+)
- [x] `data/raw/static/YYYY-MM-DD/metadata.json` exists
- [x] `data/raw/realtime/YYYY-MM-DD/HH-mm-ss/tripupdates.pb` exists
- [x] `data/raw/realtime/.../metadata.json` exists with `record_count` > 0

## Airflow

- [x] `airflow dags list` shows `gtfs_static_ingest` and `gtfs_realtime_ingest`
- [x] Both DAGs are **unpaused**
- [x] Manual trigger of `gtfs_static_ingest` succeeds (green)
- [x] Manual trigger of `gtfs_realtime_ingest` succeeds (green)
- [x] Task logs show file paths under `data/raw/`

## Database (schema only — Week 1)

- [x] Postgres on `localhost:5433` accepts connection (`transit` / `transit`)
- [x] Tables exist: `dim_date`, `dim_route`, `dim_stop`, `dim_vehicle_type`, `fact_trip_delay`, `pipeline_runs`
- [x] `dim_date` has rows (2024–2027 seeded)
- [x] `fact_trip_delay` is empty at end of Week 1 (filled in Week 2)

## Tests & docs

- [x] `pytest` passes locally
- [x] `scripts/verify_week1.ps1` passes
- [x] Read [01-project-purpose-and-goals.md](01-project-purpose-and-goals.md)

## Quick verify command

```powershell
.\scripts\verify_week1.ps1
```

---

**Week 1 phase gate (from master plan):**  
> Two Airflow tasks land raw static + realtime files on schedule; folder structure is deterministic.

When all boxes above are checked → proceed to **Week 2: PySpark transform**.
