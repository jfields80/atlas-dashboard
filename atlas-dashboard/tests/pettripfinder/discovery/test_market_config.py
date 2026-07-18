"""AES-DATA-004A discovery -- market geography config tests (Task 2)."""

from __future__ import annotations

import pytest

from scripts.pettripfinder.discovery.market_config import load_market_config


def test_columbus_config_loads():
    m = load_market_config("columbus-oh")
    assert m.market_id == "columbus-oh"
    assert m.state == "OH"


def test_required_municipalities_present():
    m = load_market_config("columbus-oh")
    required = {
        "Columbus", "Dublin", "Hilliard", "Worthington", "Westerville",
        "Upper Arlington", "Gahanna", "Reynoldsburg", "Grove City", "Powell",
        "New Albany",
    }
    assert required.issubset(set(m.included_municipalities))


def test_cells_are_bounded_not_one_giant_radius():
    m = load_market_config("columbus-oh")
    assert len(m.cells) > 1
    for cell in m.cells:
        assert cell.radius_meters <= 10_000   # no enormous single-radius query


def test_bounds_contains_market_center():
    m = load_market_config("columbus-oh")
    assert m.bounds.contains(m.center_lat, m.center_lng)


def test_unknown_market_raises():
    with pytest.raises(KeyError):
        load_market_config("nonexistent-market")


def test_cell_lookup_by_id():
    m = load_market_config("columbus-oh")
    first = m.cells[0]
    assert m.cell_by_id(first.cell_id) == first
    assert m.cell_by_id("not-a-real-cell") is None
