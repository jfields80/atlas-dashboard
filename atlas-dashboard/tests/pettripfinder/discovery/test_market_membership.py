"""PTF-GENERIC-CENSUS-MEMBERSHIP-HARDENING-001 -- market membership is not the
corridor registry.

What went wrong, and what these tests pin
-----------------------------------------
``census_projection`` decided market membership with the corridor ZIP registry
and nothing else. A market whose corridors classify by ``explicit_hotel_ids``
claims no postal code, so the registry could only ever answer "no": a
re-census of Grand Rapids-Holland turned 120 committed identities plus 113
fresh discovery candidates into FOUR census rows, and stamped 103 of the
market's own census rows OUT_OF_MARKET_GEOGRAPHY with the reason "the
candidate own coordinates fall outside the market geographic bounds" -- for
rows that carry no coordinates at all.

Two separate rules come out of that, and both are pinned below:

* membership is decided on the basis the market CONTRACT declares, never
  inferred from whether ``included_postal_codes`` happens to be empty; and
* missing evidence is never contrary evidence. A candidate that states no
  coordinates has not been shown to be outside anything.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.pettripfinder.discovery import census_projection as CP
from scripts.pettripfinder.discovery import market_membership as MM
from scripts.pettripfinder.discovery.market_config import GeoBounds
from scripts.pettripfinder.discovery.market_config import MarketConfig as GeoConfig
from scripts.pettripfinder.markets import contract as MC

REPO_ROOT = Path(__file__).resolve().parents[3]
MARKETS = REPO_ROOT / "launch_packages" / "pettripfinder" / "markets"
CENSUS = REPO_ROOT / "launch_packages" / "pettripfinder" / "identity_census"


# --------------------------------------------------------------------------- #
# Fixtures: two markets that differ ONLY in how they declare membership.
# --------------------------------------------------------------------------- #

def _corridor(corridor_id, *, zips=(), cities=(), explicit=()):
    return {
        "corridor_id": corridor_id, "market_id": "fixture-market",
        "name": corridor_id, "slug": corridor_id.split("__")[-1],
        "title": "t", "meta_description": "m", "description": "d",
        "included_cities": list(cities), "included_postal_codes": list(zips),
        "explicit_hotel_ids": list(explicit), "excluded_hotel_ids": [],
        "minimum_hotel_count": 5, "show_in_navigation": False,
        "show_in_sitemap": False, "allow_multi_corridor": False,
        "display_order": 1, "display_area": "A", "state_code": "MI",
    }


def _market(basis=None, corridors=()):
    doc = {
        "schema": MC.SCHEMA_VERSION, "market_id": "fixture-market",
        "market_name": "Fixture", "market_slug": "fixture",
        "state_name": "Michigan", "state_code": "MI",
        "primary_state_code": "MI", "states": ["MI"], "primary_city": "Testville",
        "country_code": "US", "title": "t", "meta_description": "m",
        "introductory_copy": "", "navigation_label": "n",
        "show_in_navigation": False, "show_in_sitemap": False,
        "minimum_published_hotels": 1, "route_mode": "market_prefixed",
        "corridors": [dict(c, market_id="fixture-market") for c in corridors],
    }
    if basis is not None:
        doc["census_membership_basis"] = basis
    return MC.parse_market(doc, source="fixture")


def _geography():
    """Bounds around Testville, with two included municipalities."""
    return GeoConfig(
        market_id="fixture-market", market_name="Fixture", state="MI",
        country="US", center_lat=42.96, center_lng=-85.67,
        bounds=GeoBounds(min_lat=42.75, max_lat=43.15,
                         min_lng=-86.25, max_lng=-85.45),
        included_municipalities=("Testville", "Nearby"),
        cells=(),
    )


def _candidate(cid="c1", **fields):
    row = {
        "candidate_id": cid, "name": "Test Hotel", "address_line": "1 Main St",
        "city": "", "state": "", "postal_code": "",
        "latitude": None, "longitude": None,
        "provider_categories": ["hotel"], "source_records": [],
    }
    row.update(fields)
    return row


# --------------------------------------------------------------------------- #
# The contract mechanism itself.
# --------------------------------------------------------------------------- #

class TestTheBasisIsDeclaredNeverInferred:

    def test_a_market_that_says_nothing_keeps_the_corridor_registry(self):
        """Every market committed before this field existed must be unchanged."""
        assert _market().census_membership_basis == MC.MEMBERSHIP_CORRIDOR_REGISTRY

    def test_an_empty_zip_list_does_not_silently_change_the_basis(self):
        """The whole point of a declared field: a corridor may legitimately
        claim no ZIP and still be a corridor-registry market."""
        market = _market(corridors=[_corridor("fixture-market__a", explicit=["x"])])
        assert market.census_membership_basis == MC.MEMBERSHIP_CORRIDOR_REGISTRY

    def test_an_unknown_basis_is_refused(self):
        """A typo here would re-decide every row in a census."""
        with pytest.raises(MC.MarketContractError):
            _market(basis="GEOGRAPHY")

    def test_market_geography_without_geography_fails_closed(self):
        """Never quietly fall back to the registry the contract just refused."""
        with pytest.raises(ValueError):
            MM.decide(_candidate(), basis=MC.MEMBERSHIP_MARKET_GEOGRAPHY,
                      corridor_of_zip={}, coords_in_bounds=None, geography=None)


# --------------------------------------------------------------------------- #
# 1. Identity-corridor market.
# --------------------------------------------------------------------------- #

class TestIdentityCorridorMarket:
    """Corridors carry explicit_hotel_ids and no postal codes at all."""

    def _project(self, candidates):
        market = _market(
            basis=MC.MEMBERSHIP_MARKET_GEOGRAPHY,
            corridors=[_corridor("fixture-market__downtown",
                                 explicit=["test hotel"])])
        return CP.project(candidates, market, observed_at="2026-08-26",
                          work_order="WO", geography=_geography(),
                          in_bounds={"c1": True})

    def test_a_candidate_inside_the_bounds_is_admitted(self):
        admitted, ledger = self._project([_candidate(
            city="Testville", state="MI", postal_code="49503",
            latitude=42.96, longitude=-85.67)])
        assert [r["identity_key"] for r in admitted] == ["test hotel"]
        assert [e["disposition"] for e in ledger] == [CP.ADMITTED]

    def test_membership_does_not_require_a_corridor_to_claim_the_zip(self):
        """The regression itself: no corridor claims 49503, and the row is
        still in the market."""
        admitted, ledger = self._project([_candidate(
            city="Testville", state="MI", postal_code="49503",
            latitude=42.96, longitude=-85.67)])
        assert admitted, "an identity-corridor market admitted nothing"
        assert CP.OUT_OF_MARKET_BOUNDARY_DECISION not in {
            e["disposition"] for e in ledger}

    def test_corridor_assignment_is_independent_of_membership(self):
        """An admitted row may carry no corridor and remain a census identity."""
        admitted, _ = self._project([_candidate(
            city="Testville", state="MI", postal_code="49503",
            latitude=42.96, longitude=-85.67)])
        assert admitted[0]["corridor"] == ""


# --------------------------------------------------------------------------- #
# 2-5. The evidence ladder.
# --------------------------------------------------------------------------- #

class TestTheEvidenceLadder:

    def _decide(self, candidate, *, prior=False):
        return MM.decide(candidate, basis=MC.MEMBERSHIP_MARKET_GEOGRAPHY,
                         corridor_of_zip={}, coords_in_bounds=None,
                         geography=_geography(), is_prior_identity=prior)

    def test_prior_row_without_coordinates_is_not_out_of_geography(self):
        """2. The 103. A committed identity with city/state/address and no
        lat/lon must never be evicted for lacking a coordinate."""
        outcome, why, _ = self._decide(
            _candidate(city="Grand Rapids", state="MI", postal_code="49503",
                       address_line="187 Monroe Ave NW"), prior=True)
        assert outcome != MM.OUT_OF_GEOGRAPHY
        assert outcome == MM.IN_MARKET
        assert "carried forward" in why

    def test_a_true_out_of_bounds_row_is_still_rejected(self):
        """3. The fix must not become a rubber stamp."""
        outcome, _, _ = self._decide(_candidate(
            city="Miami", state="FL", latitude=25.76, longitude=-80.19))
        assert outcome == MM.OUT_OF_GEOGRAPHY

    def test_a_true_out_of_bounds_row_is_rejected_even_when_prior(self):
        """Prior continuity yields to AFFIRMATIVE contrary evidence."""
        outcome, _, _ = self._decide(_candidate(
            city="Miami", state="FL", latitude=25.76, longitude=-80.19),
            prior=True)
        assert outcome == MM.OUT_OF_GEOGRAPHY

    def test_a_locality_outside_the_market_is_rejected(self):
        """4. Another state, no coordinates: out on the candidate's own words."""
        outcome, _, _ = self._decide(
            _candidate(city="Toledo", state="OH"))
        assert outcome == MM.OUT_OF_GEOGRAPHY

    def test_unresolvable_geography_is_held_not_rejected(self):
        """5. No coordinates and nothing to place it by -- an honest hold."""
        outcome, why, _ = self._decide(_candidate())
        assert outcome == MM.UNRESOLVED
        assert "never measured against" in why

    def test_an_unfamiliar_same_state_municipality_is_held_not_rejected(self):
        """A real adjacent suburb missing from the configured list must not be
        asserted out of the market."""
        outcome, _, _ = self._decide(_candidate(city="Rockford", state="MI"))
        assert outcome == MM.UNRESOLVED

    def test_the_unresolved_ledger_entry_keeps_the_geography_it_did_state(self):
        admitted, ledger = CP.project(
            [_candidate(city="Rockford", state="MI", postal_code="49341")],
            _market(basis=MC.MEMBERSHIP_MARKET_GEOGRAPHY),
            observed_at="2026-08-26", work_order="WO",
            geography=_geography(), in_bounds={"c1": None})
        assert admitted == []
        entry, = ledger
        assert entry["disposition"] == CP.MEMBERSHIP_UNRESOLVED
        assert entry["city_seen"] == "Rockford"
        assert entry["postal_code_seen"] == "49341"


# --------------------------------------------------------------------------- #
# 6. ZIP-ownership markets keep their behaviour.
# --------------------------------------------------------------------------- #

class TestZipOwnershipMarketsAreUnchanged:

    def _market(self):
        return _market(corridors=[_corridor(
            "fixture-market__claimed", zips=["49503"])])

    def test_a_claimed_zip_is_admitted_into_its_corridor(self):
        admitted, _ = CP.project(
            [_candidate(city="Testville", state="MI", postal_code="49503",
                        latitude=42.96, longitude=-85.67)],
            self._market(), observed_at="2026-08-26", work_order="WO",
            in_bounds={"c1": True})
        assert admitted[0]["corridor"] == "fixture-market__claimed"

    def test_an_unclaimed_zip_inside_the_box_is_still_a_boundary_decision(self):
        _, ledger = CP.project(
            [_candidate(city="Testville", state="MI", postal_code="49999",
                        latitude=42.96, longitude=-85.67)],
            self._market(), observed_at="2026-08-26", work_order="WO",
            in_bounds={"c1": True})
        assert [e["disposition"] for e in ledger] == [
            CP.OUT_OF_MARKET_BOUNDARY_DECISION]

    def test_coordinates_outside_the_box_are_still_out_of_geography(self):
        _, ledger = CP.project(
            [_candidate(city="Miami", state="FL", postal_code="33101",
                        latitude=25.76, longitude=-80.19)],
            self._market(), observed_at="2026-08-26", work_order="WO",
            in_bounds={"c1": False})
        assert [e["disposition"] for e in ledger] == [CP.OUT_OF_MARKET_GEOGRAPHY]

    def test_a_zip_market_no_longer_asserts_bounds_it_never_measured(self):
        """The one correction that applies to EVERY basis. Previously a
        candidate with no coordinates read as in_bounds False and was stamped
        OUT_OF_MARKET_GEOGRAPHY; it is now a boundary decision, which is what
        an unclaimed ZIP actually is. No row is admitted that was not admitted
        before -- only the recorded reason becomes true."""
        _, ledger = CP.project(
            [_candidate(city="Testville", state="MI", postal_code="49999")],
            self._market(), observed_at="2026-08-26", work_order="WO",
            in_bounds={"c1": None})
        assert [e["disposition"] for e in ledger] == [
            CP.OUT_OF_MARKET_BOUNDARY_DECISION]


# --------------------------------------------------------------------------- #
# PTF-DETROIT-ANN-ARBOR-HARDENED-MEMBERSHIP-AND-SHADOW-RECENSUS-002.
#
# The Grand Rapids fixture that shipped with this module lives on the branch
# that owns that market. Detroit-Ann Arbor is the SAME defect with a different
# corridor style -- 11 corridors classifying by ``included_cities``, ZERO
# postal codes between them -- so the regression is pinned here against the
# market this branch actually owns, on its live committed census.
#
# Detroit is the more dangerous case of the two. Grand Rapids kept 4 of 120
# rows under the broken gate because those 4 carried no postal code. Every one
# of Detroit's 170 postal-code-bearing rows is rejected outright, so the
# CORRIDOR_REGISTRY default projects the market to ZERO.
# --------------------------------------------------------------------------- #

class TestDetroitFixture:
    """The committed Detroit census, through the membership engine.

    182 rows until PTF-DETROIT-ANN-ARBOR-EVIDENCE-VOCABULARY-AND-PROMOTION-004
    applied founder ruling DTW-ID-003-NOVI-11-MILE, retiring one stale identity
    into its successor at the same address.
    """

    MARKET_ID = "detroit-ann-arbor-mi"

    def _contract(self):
        return MC.parse_market(
            json.loads((MARKETS / "detroit-ann-arbor-mi.json").read_text(
                encoding="utf-8")),
            source="detroit-ann-arbor-mi.json")

    def _census_rows(self):
        return json.loads(
            (CENSUS / "detroit-ann-arbor-mi.json").read_text(
                encoding="utf-8"))["hotels"]

    def _geography(self):
        from scripts.pettripfinder.discovery.market_config import load_market_config
        return load_market_config(self.MARKET_ID)

    def _corridor_of_zip(self):
        return {zip5: c.corridor_id
                for c in self._contract().corridors
                for zip5 in c.included_postal_codes}

    def _decide_all(self, basis, *, is_prior_identity):
        geo = self._geography() if basis == MC.MEMBERSHIP_MARKET_GEOGRAPHY else None
        counts = {}
        for row in self._census_rows():
            outcome, _, _ = MM.decide(
                row, basis=basis, corridor_of_zip=self._corridor_of_zip(),
                coords_in_bounds=None, geography=geo,
                is_prior_identity=is_prior_identity)
            counts[outcome] = counts.get(outcome, 0) + 1
        return counts

    # -- the declaration ---------------------------------------------------- #

    def test_the_market_declares_geography_membership(self):
        """No recensus may proceed on the inherited default. The market must
        SAY which basis decides membership, and for Detroit it is its own
        geography."""
        assert (self._contract().census_membership_basis
                == MC.MEMBERSHIP_MARKET_GEOGRAPHY)

    def test_its_corridors_still_claim_no_postal_code(self):
        """The condition that makes the ZIP gate unanswerable is unchanged --
        the fix is in the engine and in the declaration, not in the corridors.
        Detroit classifies by city, so a ZIP-keyed test has nothing to read."""
        contract = self._contract()
        assert len(contract.corridors) == 11
        assert sum(len(c.included_postal_codes) for c in contract.corridors) == 0
        assert sum(len(c.included_cities) for c in contract.corridors) > 0

    def test_no_committed_census_row_carries_a_coordinate(self):
        """The precondition for the missing-evidence rule, pinned so it cannot
        silently change underneath the continuity guarantee."""
        rows = self._census_rows()
        assert len(rows) == 181
        assert not any(r.get("latitude") or r.get("longitude") for r in rows)

    # -- the regression ----------------------------------------------------- #

    def test_every_committed_identity_survives_under_market_geography(self):
        """The whole census, end to end: all 181 committed rows stay in the
        market. This is the number the shadow recensus reconciles against."""
        counts = self._decide_all(MC.MEMBERSHIP_MARKET_GEOGRAPHY,
                                  is_prior_identity=True)
        assert counts == {MM.IN_MARKET: 181}

    def test_the_corridor_registry_default_would_be_catastrophic(self):
        """Why the declaration is a prerequisite and not an improvement.

        Under the basis Detroit would inherit by default, NOT ONE of its 181
        committed identities is admitted: the 170 rows that state a postal code
        are rejected outright, because no corridor claims any postal code, and
        the 11 that state none are held UNRESOLVED. This assertion exists so
        that anyone who removes the declaration sees exactly what it was
        holding back."""
        counts = self._decide_all(MC.MEMBERSHIP_CORRIDOR_REGISTRY,
                                  is_prior_identity=True)
        assert counts.get(MM.IN_MARKET, 0) == 0
        assert counts[MM.BOUNDARY_DECISION] == 170
        assert counts[MM.UNRESOLVED] == 11
        assert sum(counts.values()) == 181

    def test_a_fresh_candidate_is_held_not_evicted_where_geography_is_thin(self):
        """Prior-census continuity is doing real work here, and only for one
        row: Best Western Greenfield Inn states Allen Park, a municipality the
        market admits by explicit corridor id but does not list in its
        discovery geography. As a prior identity it carries forward; as a fresh
        candidate it is BORDERLINE, so it is held for review rather than
        asserted to be outside bounds it was never measured against. That row
        is Phase 4's boundary packet, not a silent drop."""
        fresh = self._decide_all(MC.MEMBERSHIP_MARKET_GEOGRAPHY,
                                 is_prior_identity=False)
        assert fresh[MM.IN_MARKET] == 180
        assert fresh[MM.UNRESOLVED] == 1
        assert MM.OUT_OF_GEOGRAPHY not in fresh

    def test_membership_fails_closed_without_geography(self):
        """A MARKET_GEOGRAPHY market whose geography was not supplied must
        raise, never quietly fall back to the corridor registry -- that
        fallback is the census-to-zero path."""
        with pytest.raises(ValueError):
            MM.decide({"city": "Detroit", "state": "MI", "postal_code": "48226"},
                      basis=MC.MEMBERSHIP_MARKET_GEOGRAPHY,
                      corridor_of_zip={}, coords_in_bounds=None, geography=None)
