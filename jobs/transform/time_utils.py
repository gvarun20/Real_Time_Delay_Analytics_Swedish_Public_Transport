"""GTFS time parsing utilities."""

from __future__ import annotations

from datetime import date, datetime, timedelta
from zoneinfo import ZoneInfo

STOCKHOLM_TZ = ZoneInfo("Europe/Stockholm")


def gtfs_time_to_seconds(time_str: str) -> int:
    """Convert GTFS HH:MM:SS (may exceed 24:00) to seconds from midnight."""
    parts = time_str.strip().split(":")
    if len(parts) != 3:
        raise ValueError(f"Invalid GTFS time: {time_str!r}")
    hours, minutes, seconds = (int(parts[0]), int(parts[1]), int(parts[2]))
    return hours * 3600 + minutes * 60 + seconds


def gtfs_time_to_datetime(service_date: str | date, time_str: str) -> datetime:
    """Convert GTFS time + service date to a timezone-naive datetime."""
    if isinstance(service_date, date):
        service_date = service_date.isoformat()
    total_seconds = gtfs_time_to_seconds(time_str)
    day_offset = total_seconds // 86400
    remainder = total_seconds % 86400
    base = datetime.strptime(service_date, "%Y-%m-%d") + timedelta(days=day_offset)
    return base + timedelta(
        hours=remainder // 3600,
        minutes=(remainder % 3600) // 60,
        seconds=remainder % 60,
    )


def date_to_date_key(service_date: str | date) -> int:
    if isinstance(service_date, date):
        service_date = service_date.isoformat()
    return int(service_date.replace("-", ""))


def gtfs_rt_start_to_epoch(start_date: str | None, start_time: str | None) -> int | None:
    """Convert GTFS-RT trip start_date (YYYYMMDD) + start_time to Unix epoch."""
    if not start_date or not start_time:
        return None
    if ":" in start_time:
        service_date = f"{start_date[:4]}-{start_date[4:6]}-{start_date[6:8]}"
        dt = gtfs_time_to_datetime(service_date, start_time)
        return int(dt.replace(tzinfo=STOCKHOLM_TZ).timestamp())
    return int(start_time)
