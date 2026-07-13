"""Resolve raw landing zone paths for transform jobs."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from config.settings import DATA_RAW_DIR


def static_zip_path(service_date: str | date, raw_base: Path | None = None) -> Path:
    if isinstance(service_date, date):
        service_date = service_date.isoformat()
    base = raw_base or DATA_RAW_DIR
    path = base / "static" / service_date / "gtfs.zip"
    if not path.exists():
        raise FileNotFoundError(f"Static GTFS not found: {path}")
    return path


def latest_realtime_pb(service_date: str | date, raw_base: Path | None = None) -> Path:
    """Return the latest TripUpdates snapshot for a service date."""
    if isinstance(service_date, date):
        service_date = service_date.isoformat()
    base = raw_base or DATA_RAW_DIR
    day_dir = base / "realtime" / service_date
    if not day_dir.exists():
        raise FileNotFoundError(f"No realtime folder for {service_date}: {day_dir}")

    snapshots = sorted(d for d in day_dir.iterdir() if d.is_dir())
    if not snapshots:
        raise FileNotFoundError(f"No realtime snapshots under {day_dir}")

    latest = snapshots[-1]
    pb_path = latest / "tripupdates.pb"
    if not pb_path.exists():
        raise FileNotFoundError(f"Missing tripupdates.pb in {latest}")
    return pb_path
