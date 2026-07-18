# Week 3 Completion Checklist

Use this to confirm Week 3 is **fully done** before starting CI/CD + polish (Week 4). Mirrors
`docs/WEEK1_CHECKLIST.md` / `docs/WEEK2_CHECKLIST.md`. Cross-reference
`transit_delay_pipeline_4week_plan.md` → "WEEK 3 — Serving Layer" for full task descriptions.

Order taken this week: **Data Quality → Dashboard → Tests** (checked data was trustworthy before
building visuals on top of it, rather than the plan's original Dashboard-first ordering).

## Data quality checks (Day 18–19)

- [x] `jobs/validate_data_quality.py` implements the check catalog — DQ-001, DQ-002, DQ-003,
      DQ-004, DQ-006, DQ-007 (DQ-005 is enforced by the `FOREIGN KEY` constraint instead of an
      app-level check — see `docs/week3-runbook.md`)
- [x] Each check is split into a pure `evaluate_*()` function (unit-testable, no DB) + a thin SQL
      query wrapper — see `jobs/validate_data_quality.py`
- [x] Airflow task `validate_data_quality` added to `dags/dag_gtfs_transform.py`, chained after
      `transform_with_pyspark`; raises `DataQualityError` (fails the task/DAG) only on
      ERROR-severity failures
- [x] Results written to `pipeline_runs.dq_status` (`passed` / `warn` / `failed`) via
      `jobs/transform/loaders.py::update_dq_status()`
- [x] Quarantine table `fact_trip_delay_rejects` — **skipped by design** (optional in the plan;
      out-of-range rows are logged via DQ-003 WARN instead of physically quarantined)

## Streamlit dashboard (Day 15–17)

- [x] `dashboard/app.py` — single-page layout, run host-side (`streamlit run dashboard/app.py`)
- [x] `dashboard/queries.py` — all SQL parameterized via SQLAlchemy `text()` + bound params
      (no f-string interpolation of filter values)
- [x] Sidebar filters: date range, route, vehicle type (operator filter omitted — single-operator
      project, SL only, for now)
- [x] **View 1:** Average delay by route (horizontal bar, top 20)
- [x] **View 2:** Delay heatmap — hour-of-day × day-of-week
- [x] **View 3:** Top 10 worst stops by avg delay (table)
- [x] **View 4:** Map — stops colored by avg delay (Plotly `scatter_map`, MapLibre/OSM tiles,
      **no API token required**)
- [x] **View 5 (bonus):** Distribution histogram of `delay_seconds`
- [x] **View 6 (bonus):** KPI cards — median delay, % on-time, trips observed, worst route
- [x] Caching: `@st.cache_data(ttl=300)` on every query wrapper
- [x] Empty state: friendly message when no data for the current filter selection

## pytest suite (Day 20–21)

- [x] Unit: `tests/unit/test_gtfs_time_parsing.py` — post-midnight `25:30:00` + helpers
- [x] Unit: `tests/unit/test_delay_calculation.py` — early, late, on-time, missing RT
- [x] Unit: `tests/unit/test_schema_contracts.py` — required tables/columns/grain/FKs in DDL
- [x] Unit: `tests/unit/test_data_quality.py` — DQ `evaluate_*()` decision logic
- [x] Unit: `tests/unit/test_dashboard_queries.py` — `Filters` + `_where_clause()`
- [x] Unit: `tests/unit/test_dag_structure.py` — DAG files + `validate_data_quality` wiring
- [x] Integration: `tests/integration/test_postgres_load.py` — schema + referential integrity
- [x] Integration: `tests/integration/test_data_quality_checks.py` — DQ fails on empty date
- [x] Integration tests auto-skip when Postgres unreachable — `tests/integration/conftest.py`
- [x] `.github/workflows/ci.yml` — Postgres service container + schema load for CI
- [x] ≥12 meaningful tests — suite has **60+** tests (target was ≥12)

## Week 3 deliverables checklist (from master plan)

- [x] Dashboard runs locally against Postgres
- [x] DQ task fails on injected/absent bad data (proved with
      `test_validate_raises_dataqualityerror_for_empty_date`)
- [x] `pytest` green locally

## Week 3 phase gate (from master plan)

> Dashboard connects to Postgres; data quality task fails intentionally on bad data; tests green
> locally.

- [x] Dashboard connects to Postgres — `dashboard/queries.py` via `config.settings.postgres_url()`
- [x] Data quality task fails intentionally on bad data — proved via integration test
- [x] Tests green locally

## Known follow-ups (Week 4 — not Week 3 blockers)

- [ ] Investigate unusually large/skewed average delays on real data
- [ ] Keep running DAGs daily toward ≥7 days of delay facts
- [ ] Public demo / Streamlit Cloud (optional) + README polish — **Week 4**

---

**Week 3 is complete — all phase gate items are met. Proceed to Week 4: CI/CD polish, docs, demo.**
