"""GTFS ID normalization across static/realtime feed families."""

from __future__ import annotations

# GTFS Sweden 3 national feed — SL operator agency IDs
SL_AGENCY_IDS_SWEDEN3 = {
    "500000000000000782",
    "500000000000000833",
    "505000000000000001",
    "505000000000000607",
}

# Legacy GTFS Regional static feed
SL_AGENCY_IDS_REGIONAL = {"275", "1:275"}


def normalize_rt_stop_id(
    stop_id: str | None,
    *,
    static_feed: str,
    realtime_feed: str,
) -> str | None:
    """Map GTFS Regional RT stop IDs to GTFS Sweden 3 IDs when feeds are mixed."""
    if not stop_id:
        return None
    if static_feed == "gtfs_sweden_3" and realtime_feed == "gtfs_regional":
        if stop_id.startswith("9022"):
            return "9011" + stop_id[4:]
    return stop_id
