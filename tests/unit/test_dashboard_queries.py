"""Unit tests for dashboard/queries.py's pure filter-building logic.

No database connection is made here — `get_engine()` is lazy, so importing
the module and exercising `Filters` / `_where_clause` is safe without Postgres.
"""

from __future__ import annotations

from datetime import date

from dashboard.filters import Filters
from dashboard.queries import _where_clause


def test_filters_computes_date_keys():
    filters = Filters(start_date=date(2026, 7, 12), end_date=date(2026, 7, 13))
    assert filters.start_date_key == 20260712
    assert filters.end_date_key == 20260713


def test_where_clause_base_case_has_only_date_range():
    filters = Filters(start_date=date(2026, 7, 12), end_date=date(2026, 7, 13))
    where, params = _where_clause(filters)
    assert "date_key BETWEEN" in where
    assert "route_id" not in where
    assert "type_name" not in where
    assert params == {"start_date_key": 20260712, "end_date_key": 20260713}


def test_where_clause_adds_route_filter():
    filters = Filters(
        start_date=date(2026, 7, 12),
        end_date=date(2026, 7, 13),
        route_ids=["1", "2"],
    )
    where, params = _where_clause(filters)
    assert "r.route_id IN :route_ids" in where
    assert params["route_ids"] == ("1", "2")


def test_where_clause_adds_vehicle_type_filter():
    filters = Filters(
        start_date=date(2026, 7, 12),
        end_date=date(2026, 7, 13),
        vehicle_types=["Bus", "Metro"],
    )
    where, params = _where_clause(filters)
    assert "vt.type_name IN :vehicle_types" in where
    assert params["vehicle_types"] == ("Bus", "Metro")


def test_where_clause_combines_all_filters():
    filters = Filters(
        start_date=date(2026, 7, 12),
        end_date=date(2026, 7, 13),
        route_ids=["1"],
        vehicle_types=["Bus"],
    )
    where, params = _where_clause(filters)
    # BETWEEN ... AND ... contributes one " AND ", plus two filter joins = 3 total
    assert where.count(" AND ") == 3
    assert "r.route_id IN :route_ids" in where
    assert "vt.type_name IN :vehicle_types" in where
    assert set(params) == {"start_date_key", "end_date_key", "route_ids", "vehicle_types"}
