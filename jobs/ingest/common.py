"""Shared helpers for GTFS ingestion jobs."""

from __future__ import annotations

import json
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from config.settings import DATA_RAW_DIR

GTFS_HEADERS = {
    "Accept-Encoding": "gzip, deflate",
    "User-Agent": "transit-delay-pipeline/0.1",
}

REALTIME_HEADERS = {
    "Accept-Encoding": "gzip, deflate",
    "User-Agent": "transit-delay-pipeline/0.1",
}


def static_landing_dir(service_date: str | date) -> Path:
    if isinstance(service_date, date):
        service_date = service_date.isoformat()
    path = DATA_RAW_DIR / "static" / service_date
    path.mkdir(parents=True, exist_ok=True)
    return path


def realtime_landing_dir(service_date: str | date, timestamp: datetime | None = None) -> Path:
    if isinstance(service_date, date):
        service_date = service_date.isoformat()
    ts = timestamp or datetime.now(timezone.utc)
    stamp = ts.strftime("%H-%M-%S")
    path = DATA_RAW_DIR / "realtime" / service_date / stamp
    path.mkdir(parents=True, exist_ok=True)
    return path


def write_metadata(
    landing_dir: Path,
    *,
    operator: str,
    feed_type: str,
    record_count: int | None,
    api_status: int,
    extra: dict[str, Any] | None = None,
) -> Path:
    payload: dict[str, Any] = {
        "operator": operator,
        "feed_type": feed_type,
        "pulled_at_utc": datetime.now(timezone.utc).isoformat(),
        "record_count": record_count,
        "api_status": api_status,
    }
    if extra:
        payload.update(extra)

    metadata_path = landing_dir / "metadata.json"
    metadata_path.write_text(json.dumps(payload, indent=2), encoding="utf-8")
    return metadata_path


def count_trip_update_entities(pb_bytes: bytes) -> int:
    from google.transit import gtfs_realtime_pb2

    feed = gtfs_realtime_pb2.FeedMessage()
    feed.ParseFromString(pb_bytes)
    return len(feed.entity)
