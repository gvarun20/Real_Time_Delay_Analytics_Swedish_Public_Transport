"""Pure helpers for relative route energy scores (Strategy C hybrid).

Score is a unitless 0-100 index. It is NOT measured kWh or fuel.
"""

from __future__ import annotations

import math
from dataclasses import dataclass

# Weights for the hybrid raw score (sum = 1.0)
W_KM = 0.35
W_HOURS = 0.35
W_STOPS = 0.20
W_DELAY = 0.10

# Region presets: (min_lat, max_lat, min_lon, max_lon)
REGION_PRESETS: dict[str, dict] = {
    "all": {
        "name": "All stops",
        "bbox": None,
    },
    "inner_stockholm": {
        "name": "Inner Stockholm",
        "bbox": (59.30, 59.36, 17.98, 18.12),
    },
    "south_stockholm": {
        "name": "South Stockholm",
        "bbox": (59.24, 59.31, 17.95, 18.15),
    },
}


@dataclass
class TripEnergyFeatures:
    trip_id: str
    route_key: int
    vehicle_type_key: int
    date_key: int
    km: float
    hours: float
    n_stops: int
    delay_hours: float

    @property
    def raw_score(self) -> float:
        return (
            W_KM * self.km
            + W_HOURS * self.hours
            + W_STOPS * float(self.n_stops)
            + W_DELAY * self.delay_hours
        )


def haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    """Great-circle distance between two WGS84 points in kilometres."""
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlmb = math.radians(lon2 - lon1)
    a = math.sin(dphi / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dlmb / 2) ** 2
    return 2 * r * math.asin(min(1.0, math.sqrt(a)))


def path_length_km(points: list[tuple[float, float]]) -> float:
    """Sum haversine lengths along an ordered stop path. Caps absurd jumps at 25 km."""
    if len(points) < 2:
        return 0.0
    total = 0.0
    for (lat1, lon1), (lat2, lon2) in zip(points, points[1:], strict=False):
        leg = haversine_km(lat1, lon1, lat2, lon2)
        if leg <= 25.0:
            total += leg
    return total


def trip_duration_hours(
    first_scheduled,
    last_scheduled,
    first_actual=None,
    last_actual=None,
) -> float:
    """Prefer actual endpoints when both exist; else scheduled. Returns hours >= 0."""
    start = first_actual if first_actual is not None else first_scheduled
    end = last_actual if last_actual is not None else last_scheduled
    if start is None or end is None:
        return 0.0
    seconds = (end - start).total_seconds()
    if seconds < 0:
        return 0.0
    # Cap at 8 hours to avoid broken GTFS day-spill artefacts dominating the score
    return min(seconds / 3600.0, 8.0)


def point_in_bbox(lat: float, lon: float, bbox: tuple[float, float, float, float]) -> bool:
    min_lat, max_lat, min_lon, max_lon = bbox
    return min_lat <= lat <= max_lat and min_lon <= lon <= max_lon


def route_in_region(
    stop_points: list[tuple[float, float]],
    bbox: tuple[float, float, float, float] | None,
    min_fraction: float = 0.5,
) -> bool:
    """True if bbox is None, or >= min_fraction of stops fall inside bbox."""
    if bbox is None:
        return True
    if not stop_points:
        return False
    inside = sum(1 for lat, lon in stop_points if point_in_bbox(lat, lon, bbox))
    return (inside / len(stop_points)) >= min_fraction


def percentile(values: list[float], p: float) -> float:
    if not values:
        return 0.0
    ordered = sorted(values)
    if len(ordered) == 1:
        return float(ordered[0])
    p = min(100.0, max(0.0, p))
    k = (len(ordered) - 1) * (p / 100.0)
    f = math.floor(k)
    c = math.ceil(k)
    if f == c:
        return float(ordered[int(k)])
    return float(ordered[f] * (c - k) + ordered[c] * (k - f))


def min_max_scale(values: list[float]) -> list[float]:
    """Scale to 0-100. If all equal, return 50 for each."""
    if not values:
        return []
    lo, hi = min(values), max(values)
    if hi - lo < 1e-12:
        return [50.0 for _ in values]
    return [100.0 * (v - lo) / (hi - lo) for v in values]


def build_flag_reasons(
    *,
    km: float,
    hours: float,
    stops: float,
    delay_hours: float,
    trip_count: int,
    km_p75: float,
    hours_p75: float,
    stops_per_km_p75: float,
    delay_ratio_p75: float,
    trip_count_p75: float,
    hours_per_km_p75: float,
) -> list[str]:
    reasons: list[str] = []
    stops_per_km = (stops / km) if km > 0.05 else 0.0
    delay_ratio = (delay_hours / hours) if hours > 0.05 else 0.0
    hours_per_km = (hours / km) if km > 0.05 else 0.0

    if km >= km_p75 and km_p75 > 0:
        reasons.append("LONG_DISTANCE")
    if hours >= hours_p75 and hours_p75 > 0:
        reasons.append("LONG_DURATION")
    if stops_per_km >= stops_per_km_p75 and stops_per_km_p75 > 0:
        reasons.append("HIGH_STOP_DENSITY")
    if delay_ratio >= delay_ratio_p75 and delay_ratio_p75 > 0:
        reasons.append("CONGESTION")
    if trip_count >= trip_count_p75 and trip_count_p75 > 0:
        reasons.append("HIGH_FREQUENCY")
    if hours_per_km >= hours_per_km_p75 and hours_per_km_p75 > 0:
        reasons.append("SLOW_SPEED")
    return reasons
