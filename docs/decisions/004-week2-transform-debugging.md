# ADR 004: Week 2 Transform Debugging — Three Stacked Bugs from "0 rows" to "638 rows"

**Status:** Resolved
**Date:** 2026-07-13

## Context

After building the PySpark transform (`jobs/transform_gtfs.py`) and wiring it into
`dags/dag_gtfs_transform.py`, the Week 2 phase gate ("`fact_trip_delay` has rows in Postgres")
would not pass. Running the job manually failed, then "succeeded" with 0 rows, three separate
times, for three unrelated reasons. This ADR documents each bug, how it was diagnosed, and the
fix, so future contributors don't have to re-discover the same failure modes.

Each bug was hidden behind the previous one — fixing bug 1 revealed bug 2; fixing bug 2 revealed
bug 3. All three had to be fixed before the pipeline produced correct output.

---

## Bug 1: Static and realtime feeds were from different Trafiklab ID namespaces

**Symptom:**

```
2026-07-13 16:27:18 WARNING trip_id join matched 0 rows — falling back to route_id + stop_id +
  stop_sequence + trip_start_epoch (GTFS Sweden 3 static + Regional RT)
2026-07-13 16:27:50 INFO Matched 0 trip-stop rows with realtime data
ValueError: No rows after joining static schedule with realtime updates
```

Both the primary join (`trip_id` + `stop_id`) **and** the fallback join
(`route_id` + `stop_id` + `stop_sequence` + time window) matched zero rows — a strong signal the
problem wasn't a join-condition bug but a data-identity mismatch.

**Root cause:**

`.env` paired `STATIC_FEED=gtfs_sweden_3` (Trafiklab's national aggregated static feed) with
`REALTIME_FEED=gtfs_regional` (SL's own regional realtime feed). These are two independent
Trafiklab products with **unrelated `trip_id`/`route_id`/`stop_id` value spaces** — Trafiklab's
own docs state GTFS Sweden Realtime "must be matched with the GTFS Sweden static dataset."
Regional realtime IDs were never meant to be joined against Sweden-3 static IDs. This pairing
was a deliberate but consequential choice from `docs/decisions/003-ingest-feed-types.md`
(2026-07-11), made because the project's Trafiklab keys only had access to "Sweden 3 Static" +
"Regional Realtime" at the time.

**Diagnosis approach:**

1. Wrote `scripts/check_feed_access.py` to probe all 4 static × realtime × key combinations
   against Trafiklab directly (HEAD requests), independent of the transform job.
2. Confirmed neither key had access to a *same-family* static+realtime pair.
3. Added the "GTFS Sweden 3 Realtime" product to the Trafiklab project holding the static key.

**Fix:**

- `.env`: `REALTIME_FEED=gtfs_regional` → `REALTIME_FEED=gtfs_sweden`
- `.env`: `TRAFIKLAB_REALTIME_API_KEY` → new "GTFS Sweden 3 Realtime" key
- Old key preserved as `TRAFIKLAB_REGIONAL_REALTIME_API_KEY` for rollback reference
- Updated `docs/decisions/003-ingest-feed-types.md` with a superseding "Update 2026-07-13" section
- `jobs/transform_gtfs.py`'s fallback-join warning now logs the actual configured feed values and
  points at this ADR, instead of hardcoding the old (wrong) pairing in the log message

**Result:** primary `trip_id` join matched 638/638 rows — no fallback needed.

---

## Bug 2: `docker-compose.yml` pointed Airflow at the wrong database name

**Symptom:**

```
psycopg2.OperationalError: connection to server at "postgres-analytics" (172.25.0.3), port 5432
  failed: FATAL:  database "transit" does not exist
```

This only surfaced *after* Bug 1 was fixed, once the transform had real rows to write.

**Root cause:**

`docker-compose.yml`'s `x-airflow-common` environment block hardcoded `POSTGRES_DB: transit`,
but the `postgres-analytics` service itself is configured with `POSTGRES_DB: transit_dw`. The
Airflow containers were simply pointed at a database name that was never created.

**Fix:** Changed `POSTGRES_DB: transit` → `POSTGRES_DB: transit_dw` in `docker-compose.yml`
(the `x-airflow-common-env` block). Required `docker compose up -d --force-recreate
airflow-scheduler airflow-webserver` to pick up the corrected env var.

---

## Bug 3: `psycopg2.extras.execute_values()` silently drops paginated `RETURNING` rows

**Symptom:** The join now matched hundreds of rows, dimension upserts logged success
(`Upserted 73 routes`, `Upserted 34 stops`), yet the fact-loading loop skipped nearly every row
and `fact_trip_delay` stayed empty:

```
Matched 638 trip-stop rows with realtime data
Upserted 73 routes
Upserted 34 stops
Transform complete: 0 fact rows loaded for 2026-07-12
```

**Root cause:**

`upsert_routes()` / `upsert_stops()` in `jobs/transform/loaders.py` called:

```python
execute_values(cur, sql, values)  # sql has a RETURNING clause
for route_id, route_key in cur.fetchall():
    mapping[route_id] = route_key
```

`execute_values()` batches large `VALUES` lists into pages (default `page_size=100`) and issues
one `INSERT` per page. **When the query has a `RETURNING` clause and `fetch` is left at its
default of `False`, psycopg2 only keeps the `RETURNING` output of the *last* executed page** —
results from every earlier page are discarded. The rows themselves were correctly
inserted/updated in Postgres (hence "Upserted 73 routes" being non-zero); only the
`route_id → route_key` / `stop_id → stop_key` mapping dictionaries used by the fact-loading loop
were incomplete. Any `route_id`/`stop_id` that happened to land on an earlier page produced a
`None` lookup and got silently skipped via the loop's `continue`.

**Diagnosis approach:**

1. Added counters (`skipped_no_route`, `skipped_no_stop`) and sampled the specific
   `(route_id, stop_id)` pairs that failed lookup.
2. Ran a direct Spark-side existence check (`sl_routes.filter(F.col("route_id") ==
   miss_route_id).count()`) for one of the sampled misses — it returned `1`, proving the route
   genuinely existed in the SL-filtered static data and had been inserted, but wasn't in the
   in-memory `route_keys` dict. This ruled out a join/filtering bug and pointed at the
   dict-building step itself.
3. Recognized the ~73/~34 counts as suspiciously close to psycopg2's default page boundary
   behavior and checked `execute_values()`'s `fetch` parameter.

**Fix:** Pass `fetch=True` to both `execute_values()` calls:

```python
returned = execute_values(cur, sql, values, fetch=True)
for route_id, route_key in returned:
    mapping[route_id] = route_key
```

**Result:** `Upserted 573 routes`, `Upserted 10234 stops`, `Inserted/updated 638 fact rows` —
matching the 638 rows from the join exactly, with zero skips.

---

## Consequences

- `scripts/check_feed_access.py` is now a permanent diagnostic tool — run it after any Trafiklab
  key/project change, before touching `STATIC_FEED`/`REALTIME_FEED`.
- Any future code that calls `execute_values()` with a `RETURNING` clause **must** pass
  `fetch=True`. Consider a lint/code-review checklist note for this, since it fails silently
  (no exception, just missing data) and only manifests once row counts exceed the page size.
- The Week 2 phase gate ("`fact_trip_delay` has rows in Postgres") is now met — see
  `docs/WEEK2_CHECKLIST.md` for full status.
