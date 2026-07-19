# Start here — documentation map (beginner friendly)

Welcome. If you are new to data engineering, read in this order.

## 1) Understand the project (15 minutes)

| # | Document | What you will learn |
|---|---|---|
| 1 | [01-project-purpose-and-goals.md](01-project-purpose-and-goals.md) | Problem, goals, what “done” means |
| 2 | [03-star-schema-explained.md](03-star-schema-explained.md) | **Why Kimball star schema** — facts, dimensions, grain |
| 3 | [02-architecture.md](02-architecture.md) | How data moves: Trafiklab → Airflow → Spark → Postgres → dashboard |
| 4 | [04-glossary.md](04-glossary.md) | Simple definitions of ETL, DAG, GTFS, CI, … |

## 2) See how we planned and delivered

| Document | What you will learn |
|---|---|
| [../transit_delay_pipeline_4week_plan.md](../transit_delay_pipeline_4week_plan.md) | Full 4-week plan |
| [WEEK1_CHECKLIST.md](WEEK1_CHECKLIST.md) | Week 1 gate (ingest) |
| [WEEK2_CHECKLIST.md](WEEK2_CHECKLIST.md) | Week 2 gate (transform + warehouse) |
| [WEEK3_CHECKLIST.md](WEEK3_CHECKLIST.md) | Week 3 gate (dashboard + DQ + tests) |

## 3) Operate the system (commands)

| Document | When to use it |
|---|---|
| [week1-runbook.md](week1-runbook.md) | Download / ingest |
| [week2-runbook.md](week2-runbook.md) | Transform into Postgres |
| [week3-runbook.md](week3-runbook.md) | Dashboard + data quality |
| [public-dashboard-deploy.md](public-dashboard-deploy.md) | Public Streamlit Cloud |
| [github-pages.md](github-pages.md) | This project website |

## 4) Important decisions (ADRs)

| Document | Topic |
|---|---|
| [decisions/001-operator-choice.md](decisions/001-operator-choice.md) | Why SL Stockholm |
| [decisions/002-dual-api-keys.md](decisions/002-dual-api-keys.md) | Why two Trafiklab keys |
| [decisions/003-ingest-feed-types.md](decisions/003-ingest-feed-types.md) | Same feed family for IDs |
| [decisions/004-week2-transform-debugging.md](decisions/004-week2-transform-debugging.md) | Real bugs we fixed |

## 5) Public links

| What | URL |
|---|---|
| Landing page | https://gvarun20.github.io/Real_Time_Delay_Analytics_Swedish_Public_Transport/ |
| Live dashboard | https://realtime--delay--analytics--swedish--publictransport.streamlit.app/ |
| Source code | https://github.com/gvarun20/Real_Time_Delay_Analytics_Swedish_Public_Transport |
| CI runs | https://github.com/gvarun20/Real_Time_Delay_Analytics_Swedish_Public_Transport/actions |

## One-sentence project summary

We download Swedish transit schedules and live delays, join them with PySpark, store results in a Kimball star schema in PostgreSQL, check quality, and show filters + charts in Streamlit — orchestrated by Airflow, tested in GitHub Actions.
