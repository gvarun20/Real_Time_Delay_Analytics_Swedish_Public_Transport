"""Project configuration loaded from environment variables."""

from __future__ import annotations

import os
from pathlib import Path

from dotenv import load_dotenv

PROJECT_ROOT = Path(os.getenv("PROJECT_ROOT", Path(__file__).resolve().parents[1])).resolve()
load_dotenv(PROJECT_ROOT / ".env")
load_dotenv()

DATA_RAW_DIR = Path(os.getenv("DATA_RAW_DIR", PROJECT_ROOT / "data" / "raw")).resolve()


def _clean_key(value: str) -> str:
    return value.strip().strip('"').strip("'")


# Fallback single key (optional)
TRAFIKLAB_API_KEY = _clean_key(os.getenv("TRAFIKLAB_API_KEY", ""))

# Trafiklab issues separate keys per API product — use both:
#   GTFS Sweden 3 Static data  → TRAFIKLAB_STATIC_API_KEY
#   GTFS Regional Realtime     → TRAFIKLAB_REALTIME_API_KEY
TRAFIKLAB_STATIC_API_KEY = (
    _clean_key(os.getenv("TRAFIKLAB_STATIC_API_KEY", "")) or TRAFIKLAB_API_KEY
)
TRAFIKLAB_REALTIME_API_KEY = (
    _clean_key(os.getenv("TRAFIKLAB_REALTIME_API_KEY", "")) or TRAFIKLAB_API_KEY
)

OPERATOR = os.getenv("OPERATOR", "sl").lower()
OPERATOR_NAME = os.getenv("OPERATOR_NAME", OPERATOR.upper())

# gtfs_sweden_3 = /gtfs-sweden/sweden.zip (matches "GTFS Sweden 3 Static data" key)
# gtfs_regional = /gtfs/{operator}/{operator}.zip (needs "GTFS Regional Static data" key)
STATIC_FEED = os.getenv("STATIC_FEED", "gtfs_sweden_3").lower()

# gtfs_sweden   = /gtfs-rt-sweden/{operator}/TripUpdatesSweden.pb (matches "GTFS Sweden 3
#                 Realtime" key; pairs with the STATIC_FEED=gtfs_sweden_3 default — see ADR-003)
# gtfs_regional = /gtfs-rt/{operator}/TripUpdates.pb (needs "GTFS Regional Realtime" key; only
#                 use with STATIC_FEED=gtfs_regional, same-family)
REALTIME_FEED = os.getenv("REALTIME_FEED", "gtfs_sweden").lower()

POSTGRES_HOST = os.getenv("POSTGRES_HOST", "localhost")
POSTGRES_PORT = int(os.getenv("POSTGRES_PORT", "5432"))
POSTGRES_DB = os.getenv("POSTGRES_DB", "transit_dw")
POSTGRES_USER = os.getenv("POSTGRES_USER", "transit")
POSTGRES_PASSWORD = os.getenv("POSTGRES_PASSWORD", "transit")


def static_gtfs_url(operator: str | None = None, api_key: str | None = None) -> str:
    key = api_key or TRAFIKLAB_STATIC_API_KEY
    if STATIC_FEED == "gtfs_regional":
        op = (operator or OPERATOR).lower()
        return f"https://opendata.samtrafiken.se/gtfs/{op}/{op}.zip?key={key}"
    return f"https://opendata.samtrafiken.se/gtfs-sweden/sweden.zip?key={key}"


def trip_updates_url(operator: str | None = None, api_key: str | None = None) -> str:
    op = (operator or OPERATOR).lower()
    key = api_key or TRAFIKLAB_REALTIME_API_KEY
    if REALTIME_FEED == "gtfs_sweden":
        path = f"gtfs-rt-sweden/{op}/TripUpdatesSweden.pb"
    else:
        path = f"gtfs-rt/{op}/TripUpdates.pb"
    return f"https://opendata.samtrafiken.se/{path}?key={key}"


def postgres_url() -> str:
    return (
        f"postgresql+psycopg2://{POSTGRES_USER}:{POSTGRES_PASSWORD}"
        f"@{POSTGRES_HOST}:{POSTGRES_PORT}/{POSTGRES_DB}"
    )
