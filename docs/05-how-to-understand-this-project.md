# How to understand this project (simple guide)

Read this in **10 minutes**. No data-engineering background required.

## What problem are we solving?

Buses and trains publish:

1. a **schedule** (“should arrive at 08:15”), and  
2. **live updates** (“actually arrived at 08:22 → 7 minutes late”).

Those two files sit in different formats. This project **joins them every day**, stores clean results, and shows charts so you can ask:

- Which routes are late?
- Which stops are worst?
- Is rush hour worse?
- Which bus routes look like a heavier relative workload? (energy score tab)

## The factory line (one picture)

```
Internet (Trafiklab)
        ↓
   Airflow downloads files on a schedule
        ↓
   Folders: data/raw/…  (keep originals)
        ↓
   PySpark joins schedule + live updates → delay in seconds
        ↓
   PostgreSQL tables (star schema)
        ↓
   Quality checks + energy scores
        ↓
   Streamlit dashboard (charts you can click)
```

## What each big word means here

| Word | Simple meaning |
|---|---|
| **GTFS** | Standard file format for transit schedules |
| **GTFS-RT** | Live delay/arrival messages |
| **Airflow** | The timer + supervisor that runs jobs |
| **PySpark** | The engine that processes large files |
| **Star schema** | Easy analytics tables: facts + dimensions |
| **Fact** | A measurement row (e.g. one delay observation) |
| **Dimension** | Labels (route name, stop name, date) |
| **DQ** | Automatic “is this data sane?” checks |
| **Energy score** | Relative 0–100 bus workload index — **not** electricity (kWh) |

More terms: [04-glossary.md](04-glossary.md)

## How we built it (4 weeks)

| Week | We built… |
|---|---|
| 1 | Download jobs + Docker |
| 2 | Join + warehouse tables |
| 3 | Dashboard + tests + quality gates |
| 4 | Public website, CI polish, energy scores, clearer docs |

Full plan: [../transit_delay_pipeline_4week_plan.md](../transit_delay_pipeline_4week_plan.md)

## How to explore the repo

1. Open the [README](../README.md) — links and story.  
2. Click the **live dashboard** (may take a minute to wake up).  
3. Skim [03-star-schema-explained.md](03-star-schema-explained.md).  
4. If you want to run locally: README → Quick start.

## Two dashboards modes

| Mode | Data source |
|---|---|
| **Local** | Your Docker PostgreSQL (full pipeline) |
| **Public Cloud** | Sample CSV files in `dashboard/sample_data/` (no home PC needed) |

## Success looks like

- Airflow DAGs can land files and transform a day  
- Postgres has delay rows  
- Dashboard shows KPIs and charts  
- CI is green on GitHub  

That is the whole project story.
