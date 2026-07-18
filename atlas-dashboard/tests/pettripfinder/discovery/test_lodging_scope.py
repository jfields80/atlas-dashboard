"""AES-DATA-004C Task 1 -- lodging scope classification tests."""

from __future__ import annotations

from scripts.pettripfinder.discovery import constants as C
from scripts.pettripfinder.discovery.lodging_scope import classify_lodging_scope
from scripts.pettripfinder.discovery.market_config import load_market_config
from scripts.pettripfinder.discovery.models import DiscoveryCandidate


def _market():
    return load_market_config("columbus-oh")


def cand(**kw):
    base = dict(candidate_id="dc_1", source_records=(), city="", state="",
               latitude=None, longitude=None)
    base.update(kw)
    return DiscoveryCandidate(**base)


def test_central_columbus_in_scope():
    m = _market()
    assert classify_lodging_scope(cand(city="Columbus", state="OH"), m) == C.SCOPE_IN_SCOPE


def test_included_suburbs_in_scope():
    m = _market()
    for city in ("Dublin", "Hilliard", "Worthington", "Westerville", "Gahanna",
                 "Reynoldsburg", "Grove City", "Powell", "New Albany", "Upper Arlington"):
        assert classify_lodging_scope(cand(city=city, state="OH"), m) == C.SCOPE_IN_SCOPE, city


def test_just_outside_bounds_is_borderline():
    m = _market()
    # Just beyond the strict bounding box but within the 25% buffer.
    result = classify_lodging_scope(cand(latitude=40.25, longitude=-82.99), m)
    assert result == C.SCOPE_BORDERLINE


def test_clearly_distant_ohio_property_out_of_scope():
    m = _market()
    # Cincinnati, OH -- same state, clearly outside Columbus market.
    result = classify_lodging_scope(cand(city="Cincinnati", state="OH",
                                         latitude=39.10, longitude=-84.51), m)
    assert result == C.SCOPE_OUT_OF_SCOPE


def test_conflicting_city_and_coordinates_is_borderline():
    m = _market()
    # City says in-scope, coordinates say clearly elsewhere.
    result = classify_lodging_scope(cand(city="Columbus", state="OH",
                                         latitude=39.10, longitude=-84.51), m)
    assert result == C.SCOPE_BORDERLINE


def test_coords_say_in_but_city_says_unfamiliar_is_borderline():
    m = _market()
    result = classify_lodging_scope(cand(city="Somewhere Else", state="OH",
                                         latitude=39.96, longitude=-82.99), m)
    assert result == C.SCOPE_BORDERLINE


def test_missing_coordinates_but_valid_municipality_in_scope():
    m = _market()
    result = classify_lodging_scope(cand(city="Worthington", state="OH"), m)
    assert result == C.SCOPE_IN_SCOPE


def test_missing_geography_is_unknown_not_excluded():
    m = _market()
    result = classify_lodging_scope(cand(), m)
    assert result == C.SCOPE_UNKNOWN


def test_out_of_state_without_coords_is_out_of_scope():
    m = _market()
    result = classify_lodging_scope(cand(city="Indianapolis", state="IN"), m)
    assert result == C.SCOPE_OUT_OF_SCOPE


def test_same_state_unfamiliar_municipality_no_coords_is_borderline_not_out():
    m = _market()
    # A real adjacent suburb simply not yet in the configured list --
    # doctrine: never invent exact legal metro boundaries, never guess exclude.
    result = classify_lodging_scope(cand(city="Pickerington", state="OH"), m)
    assert result == C.SCOPE_BORDERLINE


def test_coords_deep_inside_bounds_with_no_city_in_scope():
    m = _market()
    result = classify_lodging_scope(cand(latitude=39.96, longitude=-82.99), m)
    assert result == C.SCOPE_IN_SCOPE


def test_coords_far_outside_even_buffer_out_of_scope():
    m = _market()
    # Cleveland, OH -- same state, far north, well beyond any reasonable buffer.
    result = classify_lodging_scope(cand(latitude=41.4993, longitude=-81.6944), m)
    assert result == C.SCOPE_OUT_OF_SCOPE
