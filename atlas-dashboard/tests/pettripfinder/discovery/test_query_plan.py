"""AES-DATA-004A discovery -- query planning tests (Task 6)."""

from __future__ import annotations

import pytest

from scripts.pettripfinder.discovery import constants as C
from scripts.pettripfinder.discovery.market_config import load_market_config
from scripts.pettripfinder.discovery.query_plan import (
    RequestBudget,
    build_planner_report,
    plan_queries,
)


def _market():
    return load_market_config("columbus-oh")


def test_plan_is_deterministic():
    m = _market()
    q1 = plan_queries(m, [C.PROVIDER_GOOGLE_PLACES], [C.CATEGORY_VETERINARY])
    q2 = plan_queries(m, [C.PROVIDER_GOOGLE_PLACES], [C.CATEGORY_VETERINARY])
    assert q1 == q2


def test_plan_makes_no_side_effects_multiple_variants_per_category():
    m = _market()
    queries = plan_queries(m, [C.PROVIDER_GOOGLE_PLACES], [C.CATEGORY_VETERINARY])
    # more than one query per cell for veterinary (never a single-keyword category)
    per_cell = [q for q in queries if q.cell_id == m.cells[0].cell_id]
    assert len(per_cell) >= 2


def test_foursquare_queries_always_disabled():
    m = _market()
    queries = plan_queries(m, [C.PROVIDER_FOURSQUARE], [C.CATEGORY_VETERINARY])
    assert len(queries) > 0
    assert all(q.enabled is False for q in queries)


def test_overpass_unsupported_category_skipped_not_invented():
    m = _market()
    queries = plan_queries(m, [C.PROVIDER_OPENSTREETMAP], [C.CATEGORY_EMERGENCY_VETERINARY])
    assert queries == ()   # no invented OSM tag for this category


def test_unknown_category_raises():
    m = _market()
    with pytest.raises(ValueError):
        plan_queries(m, [C.PROVIDER_GOOGLE_PLACES], ["not_a_real_category"])


def test_unknown_provider_raises():
    m = _market()
    with pytest.raises(ValueError):
        plan_queries(m, ["NOT_A_PROVIDER"], [C.CATEGORY_VETERINARY])


def test_planner_report_no_network_pure():
    m = _market()
    queries = plan_queries(m, [C.PROVIDER_GOOGLE_PLACES, C.PROVIDER_OPENSTREETMAP],
                           [C.CATEGORY_VETERINARY, C.CATEGORY_DOG_PARK])
    report = build_planner_report(queries, market_id=m.market_id,
                                  google_key_present=True, foursquare_key_present=False)
    assert report.total_planned_queries == len(queries)
    assert report.max_possible_paginated_requests > 0


def test_planner_report_blocks_google_when_key_missing():
    m = _market()
    queries = plan_queries(m, [C.PROVIDER_GOOGLE_PLACES], [C.CATEGORY_VETERINARY])
    report = build_planner_report(queries, market_id=m.market_id,
                                  google_key_present=False, foursquare_key_present=False)
    assert len(report.blocked_queries_missing_credential) == len(queries)
    assert report.estimated_upper_bound_google_billable_calls == 0


def test_request_budget_enforces_cap():
    b = RequestBudget(max_requests=2)
    assert b.can_spend(1) is True
    b.spend(1)
    b.spend(1)
    assert b.can_spend(1) is False
    assert b.remaining() == 0


def test_request_budget_zero_default_blocks_everything():
    b = RequestBudget(max_requests=0)
    assert b.can_spend(1) is False
