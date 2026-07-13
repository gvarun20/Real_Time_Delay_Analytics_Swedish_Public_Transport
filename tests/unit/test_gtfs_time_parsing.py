from datetime import datetime
from zoneinfo import ZoneInfo

from jobs.transform.time_utils import (
    date_to_date_key,
    gtfs_rt_start_to_epoch,
    gtfs_time_to_datetime,
    gtfs_time_to_seconds,
)


def test_gtfs_time_post_midnight():
    assert gtfs_time_to_seconds("25:30:00") == 91800
    dt = gtfs_time_to_datetime("2026-07-11", "25:30:00")
    assert dt == datetime(2026, 7, 12, 1, 30, 0)


def test_gtfs_time_normal():
    assert gtfs_time_to_seconds("08:15:30") == 29730
    dt = gtfs_time_to_datetime("2026-07-11", "08:15:30")
    assert dt == datetime(2026, 7, 11, 8, 15, 30)


def test_date_to_date_key():
    assert date_to_date_key("2026-07-11") == 20260711


def test_gtfs_rt_start_to_epoch():
    epoch = gtfs_rt_start_to_epoch("20260712", "15:54:00")
    assert epoch is not None
    assert gtfs_time_to_datetime("2026-07-12", "15:54:00").replace(
        tzinfo=ZoneInfo("Europe/Stockholm")
    ).timestamp() == epoch
    assert gtfs_rt_start_to_epoch("20260712", None) is None
    assert gtfs_rt_start_to_epoch(None, "15:54:00") is None
