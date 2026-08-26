"""PTF-ST-LOUIS-MARKET-001 -- the discovery-to-census projection.

Three of these tests exist because the first draft of the module got them
wrong, and the wrongness was silent both times:

* ``category_candidates`` is our QUERY vocabulary, not the provider's, so
  reading it made the non-lodging veto unreachable -- 565 candidates, 0
  classified NOT_LODGING, RV parks and wedding barns admitted;
* membership was tested before absorption, so an OpenStreetMap row with
  coordinates and no postal code was excluded as out-of-market instead of
  being reconciled with the addressed row it duplicated;
* an unqualified brand name ("Comfort Inn") is a VALID identity key, so
  deduplicating a census by key deleted real hotels at real addresses.
"""

from __future__ import annotations

import pytest

from scripts.pettripfinder.contracts import enums
from scripts.pettripfinder.discovery import census_projection as CP
from scripts.pettripfinder.markets.contract import parse_market


def _market(zips=("63101", "63102")):
    return parse_market({
        "schema": "ptf-market/1.1",
        "market_id": "test-mo", "market_name": "Test", "market_slug": "test-mo",
        "state_name": "Missouri", "state_code": "MO", "primary_state_code": "MO",
        "states": ["MO"], "primary_city": "Test", "country_code": "US",
        "title": "t", "meta_description": "m", "introductory_copy": "",
        "navigation_label": "Test", "show_in_navigation": False,
        "show_in_sitemap": False, "minimum_published_hotels": 1,
        "route_mode": "market_prefixed",
        "corridors": [{
            "corridor_id": "test-mo__core", "market_id": "test-mo",
            "name": "Core", "slug": "core", "title": "t",
            "meta_description": "m", "description": "",
            "included_cities": [], "included_postal_codes": list(zips),
            "explicit_hotel_ids": [], "excluded_hotel_ids": [],
            "minimum_hotel_count": 1, "show_in_navigation": False,
            "show_in_sitemap": False, "allow_multi_corridor": False,
            "display_order": 1, "display_area": "Core", "state_code": "MO",
        }],
    }, source="test")


def candidate(cid, name, *, lat=38.63, lng=-90.19, address="1 Main St",
              zip5="63101", categories=("hotel", "lodging"), provider="G",
              status="OPERATIONAL", website=""):
    return {
        "candidate_id": cid, "name": name, "address_line": address,
        "city": "St. Louis", "state": "MO", "postal_code": zip5,
        "latitude": lat, "longitude": lng,
        "category_candidates": ["hotel", "motel"],
        "website_state": ("OFFICIAL_WEBSITE_PRESENT" if website else "WEBSITE_MISSING"),
        "website_url": website, "review_state": "SINGLE_SOURCE",
        "source_records": [{
            "provider": provider, "provider_categories": list(categories),
            "business_status": status, "phone": "", "provenance": [],
        }],
    }


class TestCategory:
    def test_query_categories_do_not_defeat_the_non_lodging_veto(self):
        """The defect: every lodging-run candidate carries hotel+motel in
        ``category_candidates``, so reading it made the veto unreachable."""
        row = candidate("c1", "Some KOA", categories=("campground", "rv_park"))
        state, why = CP.classify_category(row)
        assert state == enums.NOT_LODGING
        assert "campground" in why

    def test_a_bed_and_breakfast_is_not_in_current_category(self):
        row = candidate("c2", "Tiffany Inn B&B", categories=("bed_and_breakfast",))
        assert CP.classify_category(row)[0] == enums.NOT_LODGING

    def test_a_hotel_that_is_also_a_wedding_venue_is_still_a_hotel(self):
        row = candidate("c3", "Grand Hotel",
                        categories=("hotel", "lodging", "wedding_venue"))
        assert CP.classify_category(row)[0] == enums.LODGING_CONFIRMED

    def test_no_provider_category_falls_back_to_the_name(self):
        row = candidate("c4", "Riverfront Apartments", categories=())
        assert CP.classify_category(row)[0] == enums.NOT_LODGING
        row = candidate("c5", "Riverfront Lodge", categories=())
        assert CP.classify_category(row)[0] == enums.LODGING_BY_NAME


class TestAbsorption:
    def test_an_unqualified_name_absorbs_into_its_qualified_twin(self):
        rows = [
            candidate("a", "Red Roof Inn", address="", zip5="", provider="O"),
            candidate("b", "Red Roof Inn St Louis Westport",
                      lat=38.6301, lng=-90.1901, provider="G"),
        ]
        admitted, ledger = CP.project(rows, _market(), observed_at="2026-08-23",
                                      work_order="T")
        assert len(admitted) == 1
        assert admitted[0]["identity_key"] == "red roof inn st louis westport"
        absorbed = [e for e in ledger if e["disposition"] == CP.ABSORBED]
        assert len(absorbed) == 1
        assert absorbed[0]["absorbed_into_candidate_id"] == "b"
        assert absorbed[0]["distance_meters"] < CP.ABSORB_RADIUS_METERS

    def test_absorption_runs_before_membership(self):
        """A row with no postal code cannot be tested for membership. Ordering
        membership first threw it away and called it out-of-market."""
        rows = [
            candidate("a", "Quality Inn", address="", zip5="", provider="O"),
            candidate("b", "Quality Inn Airport", provider="G"),
        ]
        _admitted, ledger = CP.project(rows, _market(), observed_at="x",
                                       work_order="T")
        dispositions = {e["candidate_id"]: e["disposition"] for e in ledger}
        assert dispositions["a"] == CP.ABSORBED

    def test_distance_beats_a_matching_name(self):
        """Same brand, 4km apart: two hotels, not one."""
        rows = [
            candidate("a", "Hampton Inn", address="", zip5="",
                      lat=38.63, lng=-90.19, provider="O"),
            candidate("b", "Hampton Inn Downtown",
                      lat=38.67, lng=-90.19, provider="G"),
        ]
        admitted, _ledger = CP.project(rows, _market(), observed_at="x",
                                       work_order="T")
        assert len(admitted) == 2

    def test_a_one_word_name_never_absorbs(self):
        assert CP.absorption_direction("Motel", "Motel 6 Fenton") == 0


class TestIdentityKeyCollisions:
    def test_two_buildings_under_one_key_are_held_not_collapsed(self):
        """Both are real. A census cannot hold two rows with one key, so the
        second is HELD with its address intact -- never deleted."""
        rows = [
            candidate("a", "Comfort Inn", address="8 Commerce Dr",
                      lat=38.63, lng=-90.19),
            candidate("b", "Comfort Inn", address="12031 Lackland Rd",
                      lat=38.70, lng=-90.44),
        ]
        admitted, _ledger = CP.project(rows, _market(), observed_at="x",
                                       work_order="T")
        unique, collisions = CP.resolve_identity_key_collisions(admitted)
        assert len(unique) == 1
        assert len(collisions) == 1
        held = collisions[0]["held_for_review"]
        assert len(held) == 1
        assert held[0]["address_line"] in ("8 Commerce Dr", "12031 Lackland Rd")
        assert held[0]["address_line"] != collisions[0]["kept_address"]


class TestMembership:
    def test_an_unclaimed_postal_code_is_a_boundary_decision(self):
        rows = [candidate("a", "Waterloo Inn", zip5="62298",
                          lat=38.36, lng=-90.15)]
        _admitted, ledger = CP.project(
            rows, _market(), observed_at="x", work_order="T",
            in_bounds={"a": True})
        assert ledger[0]["disposition"] == CP.OUT_OF_MARKET_BOUNDARY_DECISION

    def test_coordinates_outside_the_box_are_geography_not_a_decision(self):
        rows = [candidate("a", "Belleville Inn", zip5="66935",
                          lat=39.8, lng=-97.6)]
        _admitted, ledger = CP.project(
            rows, _market(), observed_at="x", work_order="T",
            in_bounds={"a": False})
        assert ledger[0]["disposition"] == CP.OUT_OF_MARKET_GEOGRAPHY


class TestLedgerCompleteness:
    def test_every_candidate_gets_exactly_one_disposition(self):
        rows = [
            candidate("a", "Good Hotel"),
            candidate("b", "Some KOA", categories=("campground",)),
            candidate("c", "", address="", zip5=""),
            candidate("d", "Closed Hotel", status="CLOSED_PERMANENTLY"),
        ]
        admitted, ledger = CP.project(rows, _market(), observed_at="x",
                                      work_order="T")
        assert len(ledger) == len(rows)
        assert {e["candidate_id"] for e in ledger} == {"a", "b", "c", "d"}
        assert all(e["disposition"] in CP.LEDGER_DISPOSITIONS for e in ledger)
        assert len(admitted) == 1


class TestLocality:
    """The census contract requires a city and a state on every row. A row that
    cannot say where it is cannot be assigned, joined or published -- so it is
    held in the ledger with its coordinates, never admitted and never dropped."""

    def test_a_row_with_no_city_is_held_not_admitted(self):
        rows = [candidate("a", "Some Motel", zip5="63101")]
        rows[0]["city"] = ""
        admitted, ledger = CP.project(rows, _market(), observed_at="x",
                                      work_order="T")
        assert admitted == []
        assert ledger[0]["disposition"] == CP.NO_LOCALITY
        assert ledger[0]["latitude"] is not None, "coordinates are kept"

    def test_a_row_with_no_postal_code_city_or_state_is_held(self):
        rows = [candidate("a", "Grand Motel", address="", zip5="")]
        rows[0]["city"] = ""
        rows[0]["state"] = ""
        admitted, ledger = CP.project(rows, _market(), observed_at="x",
                                      work_order="T", in_bounds={"a": True})
        assert admitted == []
        assert ledger[0]["disposition"] == CP.NO_LOCALITY

    def test_a_row_with_a_city_and_a_postal_code_is_admitted(self):
        rows = [candidate("a", "Real Hotel", zip5="63101")]
        rows[0]["state"] = ""
        admitted, _ledger = CP.project(rows, _market(), observed_at="x",
                                       work_order="T")
        assert len(admitted) == 1, "a missing STATE is derivable; a missing city is not"


class TestDistinctiveTokens:
    def test_the_market_own_words_are_not_identity_signals(self):
        rows = [{"canonical_name": "%s Inn St. Louis" % brand}
                for brand in ("Alpha", "Bravo", "Charlie", "Delta", "Echo",
                              "Foxtrot", "Golf", "Hotel", "India", "Juliet",
                              "Kilo", "Lima", "Mike", "November", "Oscar",
                              "Papa", "Quebec", "Romeo", "Sierra", "Tango")]
        distinctive = CP.distinctive_tokens(rows)
        for common in ("inn", "st", "louis"):
            assert common not in distinctive
        assert "alpha" in distinctive

    def test_two_rows_sharing_only_market_words_are_not_suspected(self):
        rows = [{"identity_key": "a inn st louis", "canonical_name": "A Inn St Louis",
                 "latitude": 38.63, "longitude": -90.19},
                {"identity_key": "b inn st louis", "canonical_name": "B Inn St Louis",
                 "latitude": 38.6301, "longitude": -90.1901}]
        assert CP.suspected_duplicates(rows) == []

    def test_two_names_for_one_building_are_suspected(self):
        """Distinctiveness is measured against the CORPUS, so the pair has to
        sit in one. Two rows alone is a degenerate corpus in which every token
        is carried by half the market."""
        # 40 filler rows, because the distinctiveness ceiling is a SHARE of the
        # corpus: below 40 rows it rounds to 1, and a token carried by exactly
        # the pair we are looking for is then excluded by its own duplication.
        corpus = [{"identity_key": "filler%02d inn st louis" % index,
                   "canonical_name": "Filler%02d Inn St. Louis" % index,
                   "latitude": 38.70 + index / 1000.0, "longitude": -90.30}
                  for index in range(40)]
        corpus += [{"identity_key": "ritz carlton hotel st louis",
                    "canonical_name": "Ritz-Carlton Hotel St. Louis",
                    "latitude": 38.63, "longitude": -90.19},
                   {"identity_key": "the ritz carlton st louis",
                    "canonical_name": "The Ritz-Carlton, St. Louis",
                    "latitude": 38.6300, "longitude": -90.1900}]
        suspects = CP.suspected_duplicates(corpus)
        pairs = [s for s in suspects if "ritz" in s["shared_distinctive_tokens"]]
        assert len(pairs) == 1
        assert set(pairs[0]["shared_distinctive_tokens"]) >= {"ritz", "carlton"}
