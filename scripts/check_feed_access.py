"""Probe every Trafiklab static/realtime feed combo to see which products your keys unlock.

This is a one-off diagnostic for the "GTFS Sweden 3 static + GTFS Regional realtime"
ID-namespace mismatch (see docs/decisions/003-ingest-feed-types.md). It does NOT change
any config — it just reports HTTP status codes so you know which REALTIME_FEED / STATIC_FEED
combination is actually usable with your current Trafiklab keys before editing .env.

Usage (inside the airflow-scheduler container, which has the deps + .env mounted):
    docker compose exec -T airflow-scheduler python /opt/airflow/project/scripts/check_feed_access.py
"""
from __future__ import annotations

import sys
from pathlib import Path

import requests

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from config.settings import (  # noqa: E402
    OPERATOR,
    TRAFIKLAB_REALTIME_API_KEY,
    TRAFIKLAB_STATIC_API_KEY,
)
from jobs.ingest.common import GTFS_HEADERS, REALTIME_HEADERS  # noqa: E402

BASE = "https://opendata.samtrafiken.se"

STATIC_URLS = {
    "gtfs_sweden_3 (national static)": f"{BASE}/gtfs-sweden/sweden.zip",
    "gtfs_regional (per-operator static)": f"{BASE}/gtfs/{OPERATOR}/{OPERATOR}.zip",
}

REALTIME_URLS = {
    "gtfs_regional (SL realtime)": f"{BASE}/gtfs-rt/{OPERATOR}/TripUpdates.pb",
    "gtfs_sweden (national realtime)": f"{BASE}/gtfs-rt-sweden/{OPERATOR}/TripUpdatesSweden.pb",
}

KEYS = {
    "TRAFIKLAB_STATIC_API_KEY": TRAFIKLAB_STATIC_API_KEY,
    "TRAFIKLAB_REALTIME_API_KEY": TRAFIKLAB_REALTIME_API_KEY,
}


def probe(url: str, key: str, headers: dict) -> str:
    if not key:
        return "NO KEY SET"
    try:
        resp = requests.head(f"{url}?key={key}", headers=headers, timeout=20, allow_redirects=True)
        if resp.status_code in (200, 304):
            return f"OK ({resp.status_code})"
        if resp.status_code == 403:
            return "403 Forbidden (key lacks this product)"
        return f"HTTP {resp.status_code}"
    except requests.RequestException as exc:
        return f"ERROR: {exc}"


def main() -> int:
    print(f"Operator: {OPERATOR}\n")

    print("=== STATIC feeds ===")
    for label, url in STATIC_URLS.items():
        for key_name, key in KEYS.items():
            result = probe(url, key, GTFS_HEADERS)
            print(f"  {label:38s} + {key_name:26s} -> {result}")
    print()

    print("=== REALTIME feeds ===")
    for label, url in REALTIME_URLS.items():
        for key_name, key in KEYS.items():
            result = probe(url, key, REALTIME_HEADERS)
            print(f"  {label:38s} + {key_name:26s} -> {result}")

    print(
        "\nLook for 'OK' on a STATIC feed and a REALTIME feed from the SAME family "
        "(both 'gtfs_sweden_3'/'gtfs_sweden' OR both 'gtfs_regional') — that pairing "
        "shares one ID namespace and will actually join in transform_gtfs.py."
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
