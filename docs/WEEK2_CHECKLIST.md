# Week 2 Completion Checklist

Use this to confirm Week 2 is **fully done** before starting the dashboard + tests (Week 3).
Mirrors `docs/WEEK1_CHECKLIST.md`. Cross-reference `transit_delay_pipeline_4week_plan.md` →
"WEEK 2 — Transformation" for full task descriptions.

## Star schema design (Day 8–9)

- [x] ER diagram documented (`transit_delay_pipeline_4week_plan.md` → Star Schema Specification)
- [x] `sql/schema.sql` — `dim_date`, `dim_route`, `dim_stop`, `dim_vehicle_type`,
      `fact_trip_delay`, `pipeline_runs`
- [x] `sql/seed_dim_date.sql` populates date dimension
- [x] `dim_vehicle_type` seeded from GTFS `route_type` mapping (Tram/Metro/Rail/Bus/Ferry/
      Funicular/Trolleybus/Monorail)
- [x] `sql/indexes.sql` present
- [x] Init scripts mounted via `docker-compose.yml` postgres-analytics volumes
- [x] ADR written — grain of fact table + feed pairing decisions in `docs/decisions/003-*.md`,
      `docs/decisions/004-*.md`

## PySpark transform job (Day 10–12)

- [x] `jobs/transform_gtfs.py` — CLI entrypoint (`--service-date`, `--operator`,
      `--raw-base-path`, `--sample-fraction`)
- [x] `jobs/transform/time_utils.py` — `gtfs_time_to_datetime()` handles GTFS times ≥ 24:00
- [x] `jobs/transform/gtfs_realtime.py` — protobuf TripUpdates → flat records
- [x] `jobs/transform/ids.py` — cross-feed ID normalization helper (now mostly redundant since
      static+realtime are same-family, kept for resilience/tests)
- [x] `jobs/transform/loaders.py` — dimension upserts + fact insert, Postgres JDBC via psycopg2
- [x] Join logic: primary `trip_id`+`stop_id`, fallback `route_id`+`stop_id`+`stop_sequence`+
      time-window
- [x] Row counts logged at each stage (parsed, matched, upserted, inserted)
- [x] **Manual run loads real data:** `638` fact rows loaded for `2026-07-12`
      (`SELECT COUNT(*) FROM fact_trip_delay` confirmed non-zero in Postgres)

## Wire into Airflow (Day 13–14)

- [x] `dags/dag_gtfs_transform.py` — `gtfs_transform` DAG with `FileSensor` (wait for static) +
      realtime-availability check → `transform_with_pyspark` task
- [x] Execution date passed via Airflow's `{{ ds }}` macro (`context["ds"]`)
- [x] JDBC/Java version documented (`docker/airflow/Dockerfile` — OpenJDK 17 for PySpark)
- [ ] End-to-end **DAG run** (not just manual script) verified green in Airflow UI for a full
      (non-sampled) service date — manual script run is confirmed working; DAG trigger not yet
      re-verified since the fixes below

## Bugs found and fixed this week (see `docs/decisions/004-week2-transform-debugging.md`)

- [x] Feed-family ID mismatch (`gtfs_sweden_3` static + `gtfs_regional` realtime → 0 join matches)
- [x] `docker-compose.yml` `POSTGRES_DB` typo (`transit` vs actual `transit_dw`)
- [x] `execute_values(..., fetch=True)` missing → dimension key maps silently incomplete

## Week 2 deliverables checklist (from master plan)

- [x] Star schema DDL in repo
- [x] PySpark job runs standalone (`docker compose exec airflow-scheduler python
      jobs/transform_gtfs.py ...`)
- [ ] PySpark job runs **via Airflow** (DAG trigger) — confirm next
- [x] At least 1 service date loaded end-to-end (`2026-07-12`, 638 rows)

## Week 2 phase gate (from master plan)

> `fact_trip_delay` has rows in Postgres; dimensions are populated; one manual DAG run succeeds.

- [x] `fact_trip_delay` has rows (638)
- [x] Dimensions populated (573 routes, 10,234 stops, 8 vehicle types, `dim_date` seeded)
- [ ] "One manual **DAG** run succeeds" — only the underlying script has been re-verified since
      the fixes; trigger `gtfs_transform` in the Airflow UI (or `airflow dags trigger
      gtfs_transform`) to close this out

## Remaining before moving to Week 3

- [ ] Trigger `gtfs_transform` from the Airflow UI (not just the manual script) to confirm the
      DAG itself succeeds end-to-end post-fix
- [ ] Run a **full, non-sampled** transform (drop `--sample-fraction`) for at least one date
- [ ] Consider re-running for a few more consecutive dates to get closer to the project-level
      "≥7 days of delay facts" success criterion (currently only 1 date loaded)
- [ ] Review and commit outstanding changes (`.env.example`, docs, code fixes)

---

**Once the "Remaining before moving to Week 3" items are done → proceed to Week 3: Dashboard +
Data Quality + Tests.**
