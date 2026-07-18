"""Unit tests for delay_seconds calculation (early / late / missing RT)."""

from __future__ import annotations

from datetime import datetime

from jobs.transform.time_utils import compute_delay_seconds


def test_late_arrival_from_timestamps():
    scheduled = datetime(2026, 7, 12, 8, 0, 0)
    actual = datetime(2026, 7, 12, 8, 5, 30)
    assert compute_delay_seconds(scheduled, actual) == 330


def test_early_arrival_is_negative():
    scheduled = datetime(2026, 7, 12, 8, 0, 0)
    actual = datetime(2026, 7, 12, 7, 58, 0)
    assert compute_delay_seconds(scheduled, actual) == -120


def test_on_time_is_zero():
    scheduled = datetime(2026, 7, 12, 8, 0, 0)
    assert compute_delay_seconds(scheduled, scheduled) == 0


def test_missing_realtime_returns_null():
    scheduled = datetime(2026, 7, 12, 8, 0, 0)
    assert compute_delay_seconds(scheduled, None) is None
    assert compute_delay_seconds(None, None) is None


def test_rt_delay_field_preferred_over_timestamps():
    scheduled = datetime(2026, 7, 12, 8, 0, 0)
    actual = datetime(2026, 7, 12, 8, 10, 0)
    # RT says 90s late even if timestamp math would say 600s
    assert compute_delay_seconds(scheduled, actual, delay_from_rt=90) == 90


def test_rt_delay_field_alone_is_enough():
    assert compute_delay_seconds(None, None, delay_from_rt=-45) == -45
