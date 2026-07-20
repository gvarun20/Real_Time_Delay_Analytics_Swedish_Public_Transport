# Relative energy scores (Strategy C)

## What this is

A **unitless 0–100 energy score** per bus route and region for a service date. It blends
distance (haversine path), trip duration, stop count, and delay — then min-max scales across
routes. It is **not** measured kWh or fuel.

Flagged routes: `energy_score ≥ p90` **and** `p90_hours ≥ p75`, with reason tags such as
`LONG_DISTANCE`, `LONG_DURATION`, `CONGESTION`, `HIGH_STOP_DENSITY`, `HIGH_FREQUENCY`,
`SLOW_SPEED`.

## Table

- DDL: `sql/energy_score.sql` (also appended in `sql/schema.sql` for fresh Docker volumes)
- Table: `fact_route_energy_score`
- Existing DBs: the compute job calls `ensure_energy_score_table()` automatically

## Compute (host)

Postgres must be up and `fact_trip_delay` must already have bus facts for the date.

```powershell
# Optional explicit migrate (also auto-created by the job):
Get-Content sql/energy_score.sql | docker compose exec -T postgres-analytics psql -U transit -d transit_dw

py jobs/compute_route_energy_scores.py --service-date 2026-07-12 --region all
py jobs/compute_route_energy_scores.py --service-date 2026-07-12 --region inner_stockholm
py jobs/compute_route_energy_scores.py --service-date 2026-07-12 --region south_stockholm
```

## Dashboard

```powershell
py -m streamlit run dashboard/app.py
```

Open the **Energy scores** tab. The page includes plain-language explanations under each
chart (what the metric means, how to read colours/axes, and what flagged reason tags mean).
Charts: score leaders, duration leaders, scatter, flagged routes with reason tags.

Public Streamlit Cloud sample mode only has delay CSV — energy scores need local Postgres.

## Airflow

`gtfs_transform` chains:

`… >> transform_with_pyspark >> validate_data_quality >> compute_route_energy_scores`

The energy task scores regions `all`, `inner_stockholm`, and `south_stockholm` for `ds`.
