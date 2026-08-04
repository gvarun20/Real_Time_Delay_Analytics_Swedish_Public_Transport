"""Tests for route lateness ranking helpers (sample path, no Postgres)."""

from __future__ import annotations

from datetime import date

import pandas as pd

from dashboard import sample_data
from dashboard.filters import Filters


def test_get_route_lateness_ranks_by_pct_late(monkeypatch):
    facts = pd.DataFrame(
        {
            "full_date": [date(2026, 7, 12)] * 12,
            "route_id": ["a"] * 6 + ["b"] * 6,
            "route_short_name": ["10"] * 6 + ["20"] * 6,
            "type_name": ["Bus"] * 12,
            "delay_seconds": [120, 120, 120, 0, 0, 0, 30, 30, 30, 30, 30, 30],
            "trip_id": [f"t{i}" for i in range(12)],
        }
    )
    monkeypatch.setattr(sample_data, "load_facts", lambda: facts)

    out = sample_data.get_route_lateness(
        Filters(date(2026, 7, 12), date(2026, 7, 12)),
        min_observations=5,
        limit=10,
    )
    assert list(out["route_short_name"]) == ["10", "20"]
    assert out.iloc[0]["pct_late"] == 0.5
    assert out.iloc[1]["pct_late"] == 0.0


def test_get_route_lateness_filters_small_samples(monkeypatch):
    facts = pd.DataFrame(
        {
            "full_date": [date(2026, 7, 12)] * 4,
            "route_id": ["a"] * 3 + ["b"],
            "route_short_name": ["10"] * 3 + ["99"],
            "type_name": ["Bus"] * 4,
            "delay_seconds": [200, 200, 200, 9999],
            "trip_id": ["t1", "t2", "t3", "t4"],
        }
    )
    monkeypatch.setattr(sample_data, "load_facts", lambda: facts)
    out = sample_data.get_route_lateness(
        Filters(date(2026, 7, 12), date(2026, 7, 12)),
        min_observations=3,
        limit=10,
    )
    assert list(out["route_short_name"]) == ["10"]
