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


def test_indianapolis_config_loads():
    m = load_market_config("indianapolis-in")
    assert m.market_id == "indianapolis-in"
    assert m.state == "IN"
    required = {
        "Indianapolis", "Speedway", "Carmel", "Fishers", "Noblesville",
        "Westfield", "Plainfield", "Avon", "Brownsburg", "Greenwood",
    }
    assert required.issubset(set(m.included_municipalities))
    assert len(m.cells) > 1
    for cell in m.cells:
        assert cell.radius_meters <= 10_000
    assert m.bounds.contains(m.center_lat, m.center_lng)


def test_pittsburgh_config_loads():
    m = load_market_config("pittsburgh-pa")
    assert m.market_id == "pittsburgh-pa"
    assert m.state == "PA"
    assert m.bounds.contains(m.center_lat, m.center_lng)
    assert len(m.cells) > 1
    for cell in m.cells:
        assert cell.radius_meters <= 10_000


def test_unknown_market_raises():
    with pytest.raises(KeyError):
        load_market_config("nonexistent-market")


def test_cell_lookup_by_id():
    m = load_market_config("columbus-oh")
    first = m.cells[0]
    assert m.cell_by_id(first.cell_id) == first
    assert m.cell_by_id("not-a-real-cell") is None


def test_louisville_config_loads():
    m = load_market_config("louisville-ky")
    assert m.market_id == "louisville-ky"
    assert m.state == "KY"
    assert m.bounds.contains(m.center_lat, m.center_lng)
    required = {"Louisville", "Jeffersonville", "Clarksville", "New Albany",
                "Sellersburg", "Middletown"}
    assert required.issubset(set(m.included_municipalities))
    assert len(m.cells) > 1
    for cell in m.cells:
        assert cell.radius_meters <= 10_000


# --------------------------------------------------------------------------- #
# PTF-GRAND-RAPIDS-HOLLAND-GEOGRAPHY-HARDENING-002
# --------------------------------------------------------------------------- #

GRAND_RAPIDS = "grand-rapids-holland-mi"
GRAND_RAPIDS_CORRIDOR_CELLS = {
    GRAND_RAPIDS + "__downtown-grand-rapids",
    GRAND_RAPIDS + "__grr-airport-kentwood",
    GRAND_RAPIDS + "__walker-northwest-grand-rapids",
    GRAND_RAPIDS + "__wyoming-grandville",
    GRAND_RAPIDS + "__east-grand-rapids-ada",
    GRAND_RAPIDS + "__holland-zeeland",
}
GRAND_RAPIDS_HARDENING_CELLS = {
    GRAND_RAPIDS + "__comstock-park-alpine",
    GRAND_RAPIDS + "__ada-cascade-east",
    GRAND_RAPIDS + "__northeast-grand-rapids-plainfield",
    GRAND_RAPIDS + "__south-wyoming-cutlerville",
}


def _grand_rapids_raw():
    import json
    from scripts.pettripfinder.discovery.market_config import _resolve_config_path
    return json.loads(_resolve_config_path(GRAND_RAPIDS, None)
                      .read_text(encoding="utf-8"))


def test_grand_rapids_holland_config_loads():
    m = load_market_config(GRAND_RAPIDS)
    assert m.market_id == GRAND_RAPIDS
    assert m.state == "MI"
    assert m.bounds.contains(m.center_lat, m.center_lng)
    required = {"Grand Rapids", "Kentwood", "Walker", "Comstock Park",
                "Wyoming", "Grandville", "Ada", "Holland", "Zeeland"}
    assert required == set(m.included_municipalities)
    assert len(m.cells) > 1
    for cell in m.cells:
        assert cell.radius_meters <= 10_000
        # Cells seed queries inside the enclosure; a centre outside it would
        # be a query whose every result the bounds filter then discards.
        assert m.bounds.contains(cell.center_lat, cell.center_lng), cell.cell_id


def test_grand_rapids_holland_keeps_every_corridor_cell_and_names_the_added_ones():
    """No cell was removed by the geography hardening: the six corridor
    cells are all still there, and the four additions are exactly the
    places the coverage audit found outside every radius."""
    cell_ids = {cell.cell_id for cell in load_market_config(GRAND_RAPIDS).cells}
    assert GRAND_RAPIDS_CORRIDOR_CELLS <= cell_ids
    assert cell_ids - GRAND_RAPIDS_CORRIDOR_CELLS == GRAND_RAPIDS_HARDENING_CELLS
    assert len(cell_ids) == 10
    # Every cell municipality is one the market includes -- the hardening
    # did not pull unrelated Michigan territory in under a new name.
    m = load_market_config(GRAND_RAPIDS)
    assert {cell.municipality for cell in m.cells} <= set(m.included_municipalities)


def test_grand_rapids_holland_every_included_municipality_is_inside_a_cell():
    """The finding that motivated the hardening, asserted mechanically:
    each included municipality's disclosed reference point lies within at
    least one cell's query radius. Comstock Park and Ada were ~2 km outside
    every cell before; they are not allowed to drift out again."""
    from scripts.pettripfinder.discovery.census_projection import haversine_meters
    m = load_market_config(GRAND_RAPIDS)
    points = _grand_rapids_raw()["municipality_reference_points"]
    for municipality in m.included_municipalities:
        point = points[municipality]              # every municipality has one
        assert m.bounds.contains(point["lat"], point["lng"]), municipality
        inside = [
            cell.cell_id for cell in m.cells
            if haversine_meters(point["lat"], point["lng"],
                                cell.center_lat, cell.center_lng)
            <= cell.radius_meters
        ]
        assert inside, "%s is outside every discovery cell" % municipality
