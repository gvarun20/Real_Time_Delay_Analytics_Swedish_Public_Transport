# Kimball star schema — explained simply

This project stores delay analytics in a **Kimball star schema**.  
If you are new to data engineering, this page is the plain-language guide.

---

## The problem star schema solves

Raw GTFS data is spread across many files (`trips.txt`, `stop_times.txt`, `routes.txt`, …).  
That shape is good for **transit systems**, but bad for **business questions** like:

- What was the average delay on route 17 last week?
- Which stops are worst on Monday mornings?
- Are buses later than the metro?

If every answer means joining 6 messy files again, analysis is slow and error-prone.  
A **star schema** reorganizes the data once into tables that are easy to filter and aggregate.

---

## What “Kimball” means (one sentence)

**Ralph Kimball’s approach:** build an analytical database around **facts** (measurements) and **dimensions** (the labels you filter by), shaped like a star.

```text
              dim_date
                 |
   dim_route ----+---- dim_stop
                 |
          fact_trip_delay
                 |
          dim_vehicle_type
```

The **fact** is in the middle. **Dimensions** sit around it. That picture is why it is called a **star**.

---

## Two kinds of tables

### 1) Fact table = the numbers (the “what happened”)

In this project: `fact_trip_delay`

One row means:

> “On this date, this trip arrived at this stop (in this order), with this scheduled time, this actual time, and this delay.”

Important columns:

| Column | Simple meaning |
|---|---|
| `delay_seconds` | How late (+) or early (−) in seconds |
| `scheduled_arrival` | When it was planned |
| `actual_arrival` | When it actually arrived (if known) |
| `trip_id` | Which trip |
| `stop_sequence` | Order of the stop on that trip |
| `date_key`, `route_key`, `stop_key`, `vehicle_type_key` | Links to dimension tables |

**Grain (very important):**  
We decided one fact row = one `(trip, stop, date, stop_sequence)` observation.  
“Grain” = *what one row represents*. If the grain is unclear, numbers get double-counted.

### 2) Dimension tables = the labels (the “who / where / when”)

| Table | Answers questions like… |
|---|---|
| `dim_date` | Which day? Weekend? |
| `dim_route` | Which line / route name? |
| `dim_stop` | Which stop name? Where on the map? |
| `dim_vehicle_type` | Bus, metro, rail…? |

Dimensions are usually smaller and reused. Facts can grow to millions of rows.

---

## Why we use a star schema (reasons)

| Reason | In simple words |
|---|---|
| **Easy questions** | “Delay by route and hour” is a few joins, not a GTFS puzzle |
| **Consistent meaning** | Everyone uses the same `dim_route` and `dim_date` |
| **Dashboard-friendly** | Streamlit filters map cleanly to dimension columns |
| **Performance** | Indexes on keys (`date_key`, `route_key`, …) make aggregates faster |
| **Industry standard** | Interviewers recognize Kimball / dimensional modeling |
| **Separates measure from description** | Delay is a fact; “Route 17” is a dimension attribute |

### Why not keep one giant flat table?

You *can* dump everything into one wide CSV. That works for a tiny demo, then becomes painful when:

- route names change (you must rewrite history everywhere)
- you add weather or holidays later (table explodes with columns)
- multiple dashboards need the same “route” definition

Star schema keeps **descriptions** in dimensions and **events** in facts.

### Why not a fully normalized OLTP model?

Transit source systems are normalized for **writing** transactions.  
Analytics warehouses are shaped for **reading** and aggregating.  
Kimball star is the common warehouse compromise: simple for analysts, still structured.

---

## Surrogate keys (the `*_key` columns)

Dimensions use integer keys like `route_key`, `stop_key`.

- **Natural key** = the ID from GTFS (`route_id`, `stop_id`) — can be long/stringy and tied to the source
- **Surrogate key** = our warehouse integer ID — stable inside Postgres

Facts store surrogate keys. That makes joins fast and lets us update dimension attributes (SCD Type 1 overwrite) without rewriting fact text fields.

---

## How a dashboard query uses the star

Example question: *“Average delay by route for 12–13 July.”*

```text
fact_trip_delay
   JOIN dim_date   ON date_key
   JOIN dim_route  ON route_key
WHERE full_date BETWEEN '2026-07-12' AND '2026-07-13'
GROUP BY route_short_name
AVG(delay_seconds)
```

That is exactly what `dashboard/queries.py` does (with safe parameters).

---

## How data gets into the star in *this* project

1. Airflow downloads GTFS files → `data/raw/`
2. PySpark joins schedule + realtime → computes `delay_seconds`
3. Loaders upsert `dim_route` / `dim_stop`
4. Facts insert/upsert into `fact_trip_delay`
5. Data quality checks confirm the day looks sane
6. Streamlit reads the star (or a sample export on the public site)

---

## Mini glossary for this page

| Term | Meaning |
|---|---|
| Fact | A measurable event (here: a delay observation) |
| Dimension | Descriptive context (date, route, stop, vehicle type) |
| Grain | What one fact row represents |
| Surrogate key | Warehouse-generated integer ID |
| Natural key | Source system ID (`route_id`, …) |
| SCD Type 1 | Overwrite dimension attributes when they change (our choice for names) |
| Star schema | Fact in the center, dimensions around it |

---

## Where to look in the repo

| File | What it is |
|---|---|
| [`sql/schema.sql`](../sql/schema.sql) | Table definitions |
| [`sql/seed_dim_date.sql`](../sql/seed_dim_date.sql) | Pre-filled calendar |
| [`jobs/transform/loaders.py`](../jobs/transform/loaders.py) | Upserts + fact inserts |
| [`docs/02-architecture.md`](02-architecture.md) | System picture |
| [`docs/04-glossary.md`](04-glossary.md) | More beginner terms |

If you remember only one sentence:

> **Facts store delays; dimensions store the labels we filter by; together they form a star that makes analytics easy.**
