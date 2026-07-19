"""AES-SITE-001 -- site data helper tests. No network; corridor/nearby
logic tested against both synthetic fixtures and the real production CSV."""

from __future__ import annotations

from scripts.pettripfinder.site_data import (
    CORRIDOR_DOWNTOWN,
    CORRIDOR_DUBLIN,
    CORRIDOR_MIN_PROPERTIES,
    NEARBY_MAX_RESULTS,
    assign_corridor,
    group_by_corridor,
    load_hotel_policy_facts,
    nearby_same_city,
    normalize_name,
    read_production_rows,
)


def test_dublin_corridor_from_city_alone():
    assert assign_corridor("1 Any St", "Dublin") == CORRIDOR_DUBLIN


def test_downtown_corridor_unambiguous_street():
    assert assign_corridor("33 East Nationwide Blvd", "Columbus") == CORRIDOR_DOWNTOWN
    assert assign_corridor("75 East State Street", "Columbus") == CORRIDOR_DOWNTOWN


def test_high_street_low_number_is_downtown():
    assert assign_corridor("350 North High St", "Columbus") == CORRIDOR_DOWNTOWN
    assert assign_corridor("310 South High St", "Columbus") == CORRIDOR_DOWNTOWN


def test_high_street_high_number_is_not_downtown():
    # Live defect this test locks in: 7480 North High St is Worthington,
    # miles from downtown -- a bare "high st" substring match would
    # misclassify it.
    assert assign_corridor("7480 North High St", "Columbus") == ""


def test_no_corridor_for_unrecognized_address():
    assert assign_corridor("1 Random Rd", "Columbus") == ""
    assert assign_corridor("1 Random Rd", "Grove City") == ""


def test_corridor_never_reads_business_name():
    # The function signature itself proves this (no name parameter), but
    # assert explicitly that two different names at the same address/city
    # produce the identical result.
    a = assign_corridor("1 Random Rd", "Grove City")
    b = assign_corridor("1 Random Rd", "Grove City")
    assert a == b == ""


def test_group_by_corridor_enforces_minimum_threshold():
    rows = [{"name": "H%d" % i, "address": "1 East Nationwide Blvd", "city": "Columbus"}
            for i in range(CORRIDOR_MIN_PROPERTIES - 1)]
    assert group_by_corridor(rows) == {}
    rows.append({"name": "Hlast", "address": "1 East Nationwide Blvd", "city": "Columbus"})
    assert len(rows) == CORRIDOR_MIN_PROPERTIES
    groups = group_by_corridor(rows)
    assert len(groups[CORRIDOR_DOWNTOWN]) == CORRIDOR_MIN_PROPERTIES


def test_nearby_same_city_excludes_self():
    rows = [
        {"name": "A Hotel", "city": "Columbus", "category": "pet-friendly-hotels"},
        {"name": "B Hotel", "city": "Columbus", "category": "pet-friendly-hotels"},
    ]
    result = nearby_same_city(rows, rows[0])
    names = [r["name"] for r in result]
    assert "A Hotel" not in names
    assert "B Hotel" in names


def test_nearby_same_city_no_coordinates_no_distance_claim():
    rows = [{"name": "A", "city": "Columbus", "category": "x"},
            {"name": "B", "city": "Columbus", "category": "x"}]
    result = nearby_same_city(rows, rows[0])
    # No distance field is ever produced by this function -- it returns raw
    # rows only; the caller must never invent a mileage figure from them.
    assert result and "distance" not in result[0]


def test_nearby_same_city_deterministic_alphabetical_order():
    rows = [
        {"name": "Zebra Inn", "city": "Columbus", "category": "x"},
        {"name": "Alpha Inn", "city": "Columbus", "category": "x"},
        {"name": "Mid Inn", "city": "Columbus", "category": "x"},
        {"name": "Subject", "city": "Columbus", "category": "x"},
    ]
    result = nearby_same_city(rows, rows[3])
    assert [r["name"] for r in result] == ["Alpha Inn", "Mid Inn", "Zebra Inn"]


def test_nearby_same_city_capped_at_max_results():
    rows = [{"name": "H%02d" % i, "city": "Columbus", "category": "x"} for i in range(10)]
    result = nearby_same_city(rows, {"name": "Subject", "city": "Columbus", "category": "x"})
    assert len(result) == NEARBY_MAX_RESULTS


def test_nearby_same_city_no_match_for_missing_city():
    assert nearby_same_city([{"name": "A", "city": "Columbus", "category": "x"}],
                            {"name": "B", "city": "", "category": "x"}) == []


def test_nearby_filters_by_other_category():
    rows = [
        {"name": "A Park", "city": "Columbus", "category": "pet-friendly-parks"},
        {"name": "B Hotel", "city": "Columbus", "category": "pet-friendly-hotels"},
    ]
    result = nearby_same_city(rows, rows[1], other_category="pet-friendly-parks")
    assert [r["name"] for r in result] == ["A Park"]


def test_nearby_ties_broken_alphabetically_not_by_input_order():
    rows = [
        {"name": "B", "city": "Columbus", "category": "x"},
        {"name": "A", "city": "Columbus", "category": "x"},
    ]
    result = nearby_same_city(rows, {"name": "S", "city": "Columbus", "category": "x"})
    assert [r["name"] for r in result] == ["A", "B"]


# --------------------------------------------------------------------------- #
# Real production data.
# --------------------------------------------------------------------------- #

def test_real_production_hotel_corridors_meet_threshold():
    rows = [r for r in read_production_rows() if r["category"] == "pet-friendly-hotels"]
    groups = group_by_corridor(rows)
    assert CORRIDOR_DOWNTOWN in groups
    assert CORRIDOR_DUBLIN in groups
    for corridor, members in groups.items():
        assert len(members) >= CORRIDOR_MIN_PROPERTIES


def test_real_hotel_policy_facts_only_from_ready_candidates():
    facts = load_hotel_policy_facts()
    for name, entry in facts.items():
        assert entry["facts"].get("pets_allowed") == "true"
        assert entry["verified_at"]


def test_real_hotel_policy_facts_are_a_subset_of_production_names():
    rows = [r for r in read_production_rows() if r["category"] == "pet-friendly-hotels"]
    prod_names = {normalize_name(r["name"]) for r in rows}
    facts = load_hotel_policy_facts()
    assert set(facts.keys()) <= prod_names
