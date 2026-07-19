"""Shared dashboard filter model (used by Postgres and sample-data backends)."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import date

from jobs.transform.time_utils import date_to_date_key


@dataclass
class Filters:
    start_date: date
    end_date: date
    route_ids: list[str] = field(default_factory=list)
    vehicle_types: list[str] = field(default_factory=list)

    @property
    def start_date_key(self) -> int:
        return date_to_date_key(self.start_date)

    @property
    def end_date_key(self) -> int:
        return date_to_date_key(self.end_date)
