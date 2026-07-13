"""Quick Trafiklab API key check — does not download full GTFS files."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

import requests

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import (  # noqa: E402
    REALTIME_FEED,
    STATIC_FEED,
    TRAFIKLAB_REALTIME_API_KEY,
    TRAFIKLAB_STATIC_API_KEY,
    static_gtfs_url,
    trip_updates_url,
)
from jobs.ingest.common import GTFS_HEADERS, REALTIME_HEADERS  # noqa: E402

PLACEHOLDERS = {
    "",
    "your_api_key_here",
    "your_static_key_here",
    "your_realtime_key_here",
}


def check_key(operator: str) -> int:
    ok = True

    if TRAFIKLAB_STATIC_API_KEY in PLACEHOLDERS:
        print("FAIL: TRAFIKLAB_STATIC_API_KEY missing in .env")
        print("  → Paste key from 'GTFS Sweden 3 Static data' on developer.trafiklab.se")
        ok = False
    else:
        print(
            f"Static key OK (length={len(TRAFIKLAB_STATIC_API_KEY)}, feed={STATIC_FEED})"
        )

    if TRAFIKLAB_REALTIME_API_KEY in PLACEHOLDERS:
        print("FAIL: TRAFIKLAB_REALTIME_API_KEY missing in .env")
        print(
            f"  → Paste key whose project has the product matching REALTIME_FEED="
            f"{REALTIME_FEED} on developer.trafiklab.se"
        )
        ok = False
    else:
        print(f"Realtime key OK (length={len(TRAFIKLAB_REALTIME_API_KEY)}, feed={REALTIME_FEED})")

    if not ok:
        return 1

    print(f"\nChecking operator '{operator}'...")
    static_url = static_gtfs_url(operator, TRAFIKLAB_STATIC_API_KEY)
    rt_url = trip_updates_url(operator, TRAFIKLAB_REALTIME_API_KEY)

    static_resp = requests.head(static_url, headers=GTFS_HEADERS, timeout=30, allow_redirects=True)
    rt_resp = requests.head(rt_url, headers=REALTIME_HEADERS, timeout=30, allow_redirects=True)

    print(f"  Static GTFS:  HTTP {static_resp.status_code}")
    print(f"  TripUpdates:  HTTP {rt_resp.status_code}")

    if static_resp.status_code == 403 or rt_resp.status_code == 403:
        print(
            "\n403 — wrong key matched to wrong API product, or STATIC_FEED/REALTIME_FEED "
            "are from different feed families (run scripts/check_feed_access.py to see "
            "which combos your keys actually authorize)."
        )
        return 1

    if static_resp.status_code in (200, 304) and rt_resp.status_code in (200, 304):
        print("\nOK: Both keys work.")
        return 0

    print("\nUnexpected response — check Trafiklab status.")
    return 1


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--operator", default="sl")
    raise SystemExit(check_key(parser.parse_args().operator))
