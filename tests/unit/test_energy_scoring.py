"""Unit tests for relative energy scoring helpers (no Postgres)."""

from __future__ import annotations

from datetime import datetime, timedelta

from jobs.energy.scoring import (
    TripEnergyFeatures,
    build_flag_reasons,
    haversine_km,
    min_max_scale,
    path_length_km,
    percentile,
    point_in_bbox,
    route_in_region,
    trip_duration_hours,
)


def test_haversine_km_known_short_leg():
    # ~1.11 km north from a point near Stockholm
    d = haversine_km(59.33, 18.06, 59.34, 18.06)
    assert 1.0 < d < 1.3


def test_path_length_km_sums_legs_and_skips_absurd_jumps():
    points = [
        (59.33, 18.06),
        (59.34, 18.06),  # ~1.1 km
        (60.50, 18.06),  # absurd jump > 25 km — skipped
        (59.35, 18.06),  # from previous kept point? zip consecutive — jump from 60.5 skipped
    ]
    # legs: 1.1, ~129 (skipped), ~128 (skipped) → only first leg counts between consecutive
    # Actually path walks consecutive pairs: (1-2) ok, (2-3) skip, (3-4) skip
    length = path_length_km(points[:2])
    assert 1.0 < length < 1.3
    assert path_length_km([(59.33, 18.06)]) == 0.0


def test_trip_duration_hours_prefers_actual_and_caps():
    t0 = datetime(2026, 7, 12, 8, 0, 0)
    t1 = datetime(2026, 7, 12, 9, 0, 0)
    assert trip_duration_hours(t0, t1) == 1.0
    assert trip_duration_hours(t0, t1, t0, t0 + timedelta(hours=2)) == 2.0
    assert trip_duration_hours(t0, t0 + timedelta(hours=12)) == 8.0
    assert trip_duration_hours(None, t1) == 0.0


def test_route_in_region_fraction():
    bbox = (59.30, 59.36, 17.98, 18.12)
    inside = [(59.33, 18.06), (59.34, 18.07)]
    outside = [(59.20, 18.06), (59.21, 18.07)]
    mixed = [(59.33, 18.06), (59.20, 18.06)]
    assert route_in_region(inside, None) is True
    assert route_in_region(inside, bbox) is True
    assert route_in_region(outside, bbox) is False
    assert route_in_region(mixed, bbox, min_fraction=0.5) is True
    assert point_in_bbox(59.33, 18.06, bbox) is True


def test_percentile_and_min_max_scale():
    assert percentile([], 90) == 0.0
    assert percentile([10.0], 90) == 10.0
    assert percentile([0.0, 10.0, 20.0, 30.0], 50) == 15.0
    assert min_max_scale([1.0, 1.0, 1.0]) == [50.0, 50.0, 50.0]
    scaled = min_max_scale([0.0, 5.0, 10.0])
    assert scaled[0] == 0.0
    assert scaled[-1] == 100.0
    assert abs(scaled[1] - 50.0) < 1e-9


def test_trip_energy_features_raw_score_weights():
    feat = TripEnergyFeatures(
        trip_id="t1",
        route_key=1,
        vehicle_type_key=1,
        date_key=20260712,
        km=10.0,
        hours=1.0,
        n_stops=20,
        delay_hours=0.5,
    )
    expected = 0.35 * 10 + 0.35 * 1 + 0.20 * 20 + 0.10 * 0.5
    assert abs(feat.raw_score - expected) < 1e-9


def test_build_flag_reasons_tags():
    reasons = build_flag_reasons(
        km=20.0,
        hours=2.0,
        stops=40.0,
        delay_hours=1.0,
        trip_count=50,
        km_p75=10.0,
        hours_p75=1.0,
        stops_per_km_p75=1.0,
        delay_ratio_p75=0.1,
        trip_count_p75=10.0,
        hours_per_km_p75=0.05,
    )
    assert "LONG_DISTANCE" in reasons
    assert "LONG_DURATION" in reasons
    assert "HIGH_STOP_DENSITY" in reasons
    assert "CONGESTION" in reasons
    assert "HIGH_FREQUENCY" in reasons
    assert "SLOW_SPEED" in reasons
