"""Unit tests for sample energy CSV helpers (no Postgres)."""

from __future__ import annotations

from datetime import date
from pathlib import Path

import pandas as pd

from dashboard import sample_data


def test_energy_sample_path_constant():
    assert sample_data.ENERGY_SAMPLE_PATH.name == "energy_scores.csv.gz"


def test_get_energy_scores_filters_region_and_dates(tmp_path, monkeypatch):
    path = tmp_path / "energy_scores.csv.gz"
    df = pd.DataFrame(
        [
            {
                "full_date": "2026-07-12",
                "region_id": "all",
                "region_name": "All stops",
                "route_id": "1",
                "route_short_name": "27",
                "route_long_name": "Demo",
                "trip_count": 10,
                "avg_km": 8.0,
                "total_km": 80.0,
                "p90_hours": 0.7,
                "total_hours": 5.0,
                "avg_stops": 20.0,
                "delay_hours": 0.2,
                "energy_score": 40.0,
                "is_flagged": True,
                "flag_reasons": "LONG_DURATION",
            },
            {
                "full_date": "2026-07-12",
                "region_id": "inner_stockholm",
                "region_name": "Inner Stockholm",
                "route_id": "2",
                "route_short_name": "4",
                "route_long_name": "Other",
                "trip_count": 5,
                "avg_km": 3.0,
                "total_km": 15.0,
                "p90_hours": 0.3,
                "total_hours": 1.0,
                "avg_stops": 10.0,
                "delay_hours": 0.1,
                "energy_score": 10.0,
                "is_flagged": False,
                "flag_reasons": "",
            },
        ]
    )
    df.to_csv(path, index=False, compression="gzip")
    monkeypatch.setattr(sample_data, "ENERGY_SAMPLE_PATH", path)
    sample_data.load_energy_scores.cache_clear()

    out = sample_data.get_energy_scores(date(2026, 7, 12), date(2026, 7, 12), "all")
    assert len(out) == 1
    assert str(out.iloc[0]["route_short_name"]) == "27"
    assert bool(out.iloc[0]["is_flagged"]) is True

    sample_data.load_energy_scores.cache_clear()
    assert sample_data.energy_sample_file_exists() or Path(path).exists()
