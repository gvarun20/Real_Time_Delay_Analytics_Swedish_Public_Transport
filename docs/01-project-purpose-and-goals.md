# Project Purpose & Goals

## Why this project exists

Public transport in Sweden publishes two kinds of open data:

1. **Static schedules** — when a bus, metro, or train is *planned* to arrive (GTFS static files).
2. **Realtime updates** — when it *actually* arrives, including delays (GTFS-RT TripUpdates).

These feeds are rarely combined in a **production-style data pipeline**: scheduled ingestion, fault-tolerant orchestration, dimensional modeling, and a dashboard for analysis. This project builds that pipeline end-to-end, using Swedish transit data from [Trafiklab](https://www.trafiklab.se/).

### Personal motivation (portfolio & skills)

This project directly demonstrates skills commonly expected for data engineering roles:

| Skill area | How this project proves it |
|---|---|
| Workflow orchestration | Apache Airflow DAGs with retries, scheduling, failure callbacks |
| Large-scale processing | PySpark transforms on real GTFS volumes |
| Dimensional modeling | Kimball star schema (`dim_*` + `fact_trip_delay`) — explained in [03-star-schema-explained.md](03-star-schema-explained.md) |
| Data quality mindset | Validation gates before downstream consumers |
| DevOps | Docker Compose, CI, reproducible local environment |
| Storytelling | Clear docs, architecture diagrams, demo-ready artifacts |

The target outcome is a **portfolio-ready GitHub repository** that a recruiter or interviewer can clone, run locally at **$0 cost**, and understand in under 10 minutes.

---

## Problem statement

Transit operators and analysts need answers to questions like:

- Which routes are consistently late?
- Which stops have the worst delays at rush hour?
- Does delay vary by day of week or time of day?

Raw GTFS files alone do not answer these questions. You must:

1. **Ingest** static and realtime feeds reliably over time.
2. **Join** scheduled stop times with live TripUpdates on `trip_id` + `stop_id`.
3. **Model** the result into an analytical schema (star schema).
4. **Serve** metrics through a dashboard backed by tested infrastructure.

Without a pipeline, analysis stays ad-hoc — manual downloads, one-off scripts, no audit trail.

---

## Project goals

### Primary goals (must-have)

| # | Goal | Success indicator |
|---|---|---|
| G1 | Ingest GTFS static + realtime on a schedule | Airflow DAGs land files under `data/raw/` without manual steps |
| G2 | Transform raw feeds into delay facts | `fact_trip_delay` populated in PostgreSQL |
| G3 | Model data using Kimball star schema | Documented grain: one row per trip × stop × service date |
| G4 | Surface insights in a dashboard | Streamlit shows delay trends by route, stop, and time |
| G5 | Operate like a production pipeline | Retries, logging, data quality checks, CI tests |

### Secondary goals (nice-to-have)

| # | Goal | When |
|---|---|---|
| G6 | Idempotent incremental loads | Week 2–3 |
| G7 | ML delay prediction or weather join | Optional stretch |
| G8 | Live demo link (Streamlit Cloud sample data) | Week 4 |

### Non-goals (explicitly out of scope for v1)

- Full national Sweden coverage in the dashboard (we filter to **SL / Stockholm** for clarity)
- Sub-second streaming (Kafka) — batch snapshots every 15 minutes is sufficient
- Paid cloud hosting — everything runs in local Docker
- Mobile app or public production deployment

---

## Target users (personas)

### 1. Data analyst
Wants delay trends by route, hour, and day of week to support service planning conversations.

### 2. Transit operator (hypothetical)
Wants to identify chronically late stops and routes for operational review.

### 3. You (job seeker / builder)
Needs a concrete artifact proving orchestration, Spark, modeling, and CI/CD — with honest documentation of tradeoffs.

---

## Analytical questions the pipeline will answer

Once Weeks 2–3 are complete, the dashboard should support:

1. What is the **average delay by route** for a chosen date range?
2. Which **stops** have the highest median delay?
3. How do delays vary by **hour-of-day × day-of-week** (heatmap)?
4. What **percentage of trips** are on-time (delay ≤ 0 seconds)?
5. Where are stops on a **map**, colored by average delay?

---

## Technical design principles

1. **Reproducibility** — `git clone` + `docker compose up` + `.env` should be enough to run ingestion.
2. **Honesty** — If realtime coverage is sparse, report coverage %; label simulated data clearly.
3. **Separation of concerns** — Ingest (Week 1) → Transform (Week 2) → Serve (Week 3) → Polish (Week 4).
4. **Immutable raw layer** — Never overwrite the same raw partition; each pull gets its own folder/timestamp.
5. **Fail fast on bad data** — Quality checks block downstream tasks, not just log warnings.

---

## 4-week delivery plan (summary)

| Week | Focus | Phase gate |
|---|---|---|
| **1** | Data access + Airflow ingestion | Raw static + realtime land on schedule |
| **2** | PySpark + star schema load | `fact_trip_delay` has rows in Postgres |
| **3** | Streamlit + data quality + tests | Dashboard live; DQ task fails on bad data |
| **4** | CI/CD + docs + demo video | CI green; portfolio-ready README |

Detailed task breakdown: [transit_delay_pipeline_4week_plan.md](../transit_delay_pipeline_4week_plan.md)

---

## Definition of done (full project)

- [ ] Airflow DAG runs end-to-end without manual intervention
- [ ] Reproducible from fresh clone + Docker
- [ ] Star schema populated with ≥7 days of delay facts
- [ ] Streamlit dashboard with 4+ views from live Postgres
- [ ] ≥12 pytest tests passing in CI
- [ ] README with architecture, setup, design decisions, demo link
- [ ] `.env.example` documents all secrets (no keys committed)

---

## Resume narrative (when complete)

> Built an end-to-end, Airflow-orchestrated pipeline processing Swedish public transit (GTFS) data with PySpark, modeling delay patterns into a Kimball-style star schema in PostgreSQL; surfaced insights via Streamlit, with automated testing and CI/CD — fully containerized at zero cost.

---

*Related docs: [02-architecture.md](02-architecture.md) · [week1-runbook.md](week1-runbook.md) · [WEEK1_CHECKLIST.md](WEEK1_CHECKLIST.md)*
