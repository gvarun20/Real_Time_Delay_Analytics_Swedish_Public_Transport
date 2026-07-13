# ADR 003: Static and Realtime Feed URL Types

**Status:** Superseded (see Update 2026-07-13)
**Date:** 2026-07-11

## Context

Trafiklab has multiple GTFS API families with **different URL paths** and **different API key products**:

| API family | Static URL | Realtime URL |
|---|---|---|
| GTFS Sweden 3 / Sweden Realtime | `/gtfs-sweden/sweden.zip` | `/gtfs-rt-sweden/{op}/TripUpdatesSweden.pb` |
| GTFS Regional | `/gtfs/{op}/{op}.zip` | `/gtfs-rt/{op}/TripUpdates.pb` |

Our keys map to **Sweden 3 Static** + **Regional Realtime**, so we need a hybrid configuration.

## Decision (original, 2026-07-11)

Environment variables control feed type:

```env
STATIC_FEED=gtfs_sweden_3      # uses /gtfs-sweden/sweden.zip
REALTIME_FEED=gtfs_regional    # uses /gtfs-rt/sl/TripUpdates.pb
```

Implemented in `config/settings.py` → `static_gtfs_url()` and `trip_updates_url()`.

## Consequences (original)

- Week 2 PySpark must **filter Sweden-wide static zip to SL operator** (agency_id 275 / operator SL)
- If user later adds GTFS Regional Static key, they can set `STATIC_FEED=gtfs_regional` for smaller per-operator zips
- Documentation and test scripts must reference feed types, not a single generic "GTFS API"

## Update 2026-07-13: hybrid pairing was wrong — feeds don't share an ID namespace

The **Sweden 3 Static** + **Regional Realtime** hybrid pairing above seemed fine at ingest
time (both feeds landed data successfully), but it silently broke the Week 2 transform join:
`gtfs_sweden_3` static uses Samtrafiken's national aggregated `trip_id`/`route_id`/`stop_id`
values, while `gtfs_regional` realtime uses SL's own regional IDs. These are two independent
ID namespaces — Trafiklab's own docs confirm GTFS Sweden Realtime "must be matched with the
GTFS Sweden static dataset," i.e. regional realtime was never meant to join against Sweden-3
static. Result: `jobs/transform_gtfs.py` matched **0 rows** on both the primary `trip_id` join
and the `route_id`+`stop_id`+`stop_sequence`+time-window fallback.

**Corrected decision:** keep both feeds in the same family. We added the "GTFS Sweden 3
Realtime" product to our Trafiklab key and switched:

```env
STATIC_FEED=gtfs_sweden_3      # uses /gtfs-sweden/sweden.zip
REALTIME_FEED=gtfs_sweden      # uses /gtfs-rt-sweden/sl/TripUpdatesSweden.pb
```

`TRAFIKLAB_REALTIME_API_KEY` now holds the "GTFS Sweden 3 Realtime" key rather than the
"GTFS Regional Realtime" key. The alternative path (not taken) would have been requesting a
"GTFS Regional Static data" key and using `STATIC_FEED=gtfs_regional` +
`REALTIME_FEED=gtfs_regional` instead.

### Consequences (update)

- Both static and realtime IDs now come from the same Samtrafiken national namespace, so the
  primary `trip_id`+`stop_id` join in `run_transform()` should match directly without the
  fallback path or the `normalize_rt_stop_id` cross-feed stop-id hack.
- `scripts/check_feed_access.py` was added to probe which static/realtime/key combos are
  actually authorized before changing `.env` — run it after any Trafiklab key change.
- The old "GTFS Regional Realtime" key is no longer used by the pipeline; kept in `.env` as
  `TRAFIKLAB_REGIONAL_REALTIME_API_KEY` for reference/rollback only.
