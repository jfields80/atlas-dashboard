"""PTF-CLEVELAND-OVERNIGHT-AUTHORITY-001 -- Cleveland authority and isolation.

These run against the committed Cleveland authority, not fixtures. What they
defend is mostly what could go wrong QUIETLY:

  * a fact published without the property's own words behind it
  * a withheld field reappearing as a claim
  * a Columbus exclusion counted as Cleveland's, because ownership was implicit
  * the "Pets Welcome | Dogs & service animals only" page being read as a refusal
  * Cleveland hotels appearing in a Columbus package, or the reverse
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from scripts.pettripfinder.hotel_exclusions import load_exclusions
from scripts.pettripfinder.market_ownership import owned_by
from scripts.pettripfinder.site_data import (
    load_published_hotel_policy_facts, normalize_name, published_facts_path,
    read_production_rows, verified_public_hotels,
)

CLEVELAND = "cleveland-akron-canton-oh"
COLUMBUS = "columbus-oh"
_ROOT = Path(__file__).resolve().parents[2]


@pytest.fixture(scope="module")
def facts():
    return json.loads(published_facts_path(CLEVELAND).read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def proposal():
    p = (_ROOT / "data" / "worker_runs" / "pettripfinder" / "discovery"
         / "review_batches" / "cleveland-factory-001"
         / "proposed_cleveland_authority.json")
    if not p.exists():
        pytest.skip("Cleveland capture package is gitignored and absent here")
    return json.loads(p.read_text(encoding="utf-8"))


class TestClevelandAuthority:

    def test_twenty_one_hotels_are_published(self, facts):
        """19 from PTF-CLEVELAND-OVERNIGHT-AUTHORITY-001, plus the two Drury
        properties PTF-CLEVELAND-POLICY-CAPTURE-INTEGRATION-003 published."""
        assert facts["market"] == CLEVELAND
        assert len(facts["hotels"]) == 21
        assert {h["verification_state"] for h in facts["hotels"]} == {"VERIFIED_PET_FRIENDLY"}

    def test_eight_verified_no_pets_are_cleveland_owned(self):
        cle = [e for e in load_exclusions()
               if e.get("market_id") == CLEVELAND
               and e["exclusion_state"] == "VERIFIED_NO_PETS"]
        assert len(cle) == 8

    def test_every_exclusion_states_its_market(self):
        """Implicit ownership defaulted Columbus's 14 exclusions into whichever
        market asked, and reported 22 verified-no-pets for a market with 8."""
        assert all((e.get("market_id") or "").strip() for e in load_exclusions())

    def test_columbus_still_has_exactly_fourteen(self):
        cbus = [e for e in load_exclusions()
                if e.get("market_id") == COLUMBUS
                and e["exclusion_state"] == "VERIFIED_NO_PETS"]
        assert len(cbus) == 14

    def test_out_of_current_category_is_kept_distinct(self):
        states = {e["exclusion_state"] for e in load_exclusions()}
        assert "OUT_OF_CURRENT_CATEGORY" in states and "VERIFIED_NO_PETS" in states

    def test_every_published_fact_carries_a_quote_from_the_page(self, facts):
        """The whole standard in one assertion: a fact with no supporting words
        in the captured evidence is not publishable."""
        for hotel in facts["hotels"]:
            evidence = {e["field"]: e["quote"] for e in hotel["evidence"]}
            page = " ".join(hotel["evidence_quote"].split()).lower()
            for field in hotel["facts"]:
                assert field in evidence, "%s: %s has no evidence" % (hotel["name"], field)
                assert " ".join(evidence[field].split()).lower() in page, (
                    "%s: %s quote is not in the captured page text"
                    % (hotel["name"], field))

    def test_withheld_fields_are_recorded_and_absent_from_facts(self, facts):
        withheld_total = 0
        for hotel in facts["hotels"]:
            for field, reason in hotel["withheld_fields"].items():
                withheld_total += 1
                assert field not in hotel["facts"], (
                    "%s: %s is both withheld and published" % (hotel["name"], field))
                assert len(reason) > 20, "a withheld field needs a real reason"
        # 21 from the overnight authority + 2 each for the two Drury records
        # (service_animal_exception, which no renderer reads, and fee_scope,
        # whose room scope is carried inside fee_basis).
        assert withheld_total == 25

    def test_no_invented_money_or_weight_units(self, facts):
        for hotel in facts["hotels"]:
            f = hotel["facts"]
            if "pet_fee" in f:
                assert re.fullmatch(r"\$\d+\.\d{2}", f["pet_fee"]), hotel["name"]
            if "weight_limit" in f:
                assert f["weight_limit"].endswith(" pounds"), hotel["name"]
            # {lt, lte, combined} is the closed operator set; "per pet" is not a
            # member and rendered as nothing at all when it was briefly used.
            assert f.get("weight_limit_operator") in (None, "lt", "lte", "combined")


class TestTheServiceAnimalNearMiss:

    def test_cleveland_marriott_downtown_is_published_as_pet_friendly(self, facts):
        """Its page reads 'Pets Welcome | Dogs & service animals only'. A
        substring test for 'service animals only' would have suppressed the
        market's flagship hotel."""
        hotel = next(h for h in facts["hotels"]
                     if h["key"] == "cleveland marriott downtown at key tower")
        assert hotel["verification_state"] == "VERIFIED_PET_FRIENDLY"
        assert hotel["facts"]["pets_allowed"] == "true"
        assert hotel["facts"]["species_allowed"] == "dogs"
        assert "service animals only" in hotel["evidence_quote"].lower()

    def test_it_is_not_in_the_exclusion_authority(self):
        names = {normalize_name(e["canonical_name"]) for e in load_exclusions()}
        assert "cleveland marriott downtown at key tower" not in names

    def test_species_is_never_established_by_service_animal_language_alone(self, facts):
        """A species quote must NAME a species.

        "Dogs & service animals only" legitimately supports species=dogs -- the
        sentence names dogs. What must never happen is a species published from
        a sentence whose only animal reference is the legal service-animal
        category, so the test requires a real species word rather than the
        absence of the phrase.
        """
        for hotel in facts["hotels"]:
            if "species_allowed" not in hotel["facts"]:
                continue
            quote = next(e["quote"].lower() for e in hotel["evidence"]
                         if e["field"] == "species_allowed")
            named = [w for w in ("dog", "cat", "pet") if w in quote]
            assert named, "%s: species rests on no named species (%r)" % (
                hotel["name"], quote)
            stripped = quote.replace("service animal", "")
            assert any(w in stripped for w in ("dog", "cat")), (
                "%s: the only animal named is a service animal" % hotel["name"])


class TestMarketIsolation:

    def test_cleveland_inventory_is_owned_and_scoped(self):
        rows = read_production_rows()
        cle = owned_by(rows, CLEVELAND)
        assert len(cle) == 21
        assert all(r["category"] == "pet-friendly-hotels" for r in cle)

    def test_columbus_inventory_is_unchanged_at_116(self):
        assert len(owned_by(read_production_rows(), COLUMBUS)) == 116

    def test_no_cleveland_hotel_can_reach_a_columbus_package(self):
        cle_keys = {normalize_name(r["name"])
                    for r in owned_by(read_production_rows(), CLEVELAND)}
        cbus = owned_by(read_production_rows(), COLUMBUS)
        assert {normalize_name(r["name"]) for r in cbus} & cle_keys == set()

    def test_each_market_selects_only_its_own_facts(self):
        cbus = load_published_hotel_policy_facts(COLUMBUS)
        cle = load_published_hotel_policy_facts(CLEVELAND)
        assert len(cbus) == 88 and len(cle) == 21
        assert set(cbus) & set(cle) == set()

    def test_the_columbus_join_still_yields_88(self):
        rows = [r for r in owned_by(read_production_rows(), COLUMBUS)
                if r["category"] == "pet-friendly-hotels"]
        assert len(verified_public_hotels(
            rows, load_published_hotel_policy_facts(COLUMBUS))) == 88

    def test_the_cleveland_join_yields_21(self):
        rows = [r for r in owned_by(read_production_rows(), CLEVELAND)
                if r["category"] == "pet-friendly-hotels"]
        assert len(verified_public_hotels(
            rows, load_published_hotel_policy_facts(CLEVELAND))) == 21

    def test_reconciliation_is_188_21_8_29_159(self):
        from scripts.pettripfinder.build_market_manifest import build_package

        pkg = build_package(CLEVELAND)
        assert pkg.reconciliation() == (188, 21, 8, 29, 159)
        assert pkg.published_pet_friendly_count + pkg.verified_no_pets_count == 29
        assert 29 + pkg.unresolved_count == 188

    def test_columbus_reconciliation_is_untouched(self):
        from scripts.pettripfinder.build_market_manifest import build_package

        assert build_package(
            COLUMBUS, confirmed_identity_count=114).reconciliation() == (114, 88, 14, 102, 12)


class TestEveryProposalIsAccountedFor:

    def test_all_27_resolved_proposals_reached_authority(self, proposal, facts):
        published = {h["key"] for h in facts["hotels"]}
        excluded = {normalize_name(e["canonical_name"]) for e in load_exclusions()
                    if e.get("market_id") == CLEVELAND}
        for entry in proposal["captured_pet_friendly"]:
            assert entry["listing_key"] in published, entry["canonical_name"]
        for entry in proposal["verified_no_pets"]:
            assert normalize_name(entry["canonical_name"]) in excluded, entry["canonical_name"]

    def test_the_out_of_market_capture_never_entered_cleveland(self, proposal, facts):
        """One of the 28 captures is a Columbus hotel. It stays evidence and
        never becomes Cleveland authority."""
        assert proposal["counts"]["out_of_market_excluded"] == 1
        stray = proposal["out_of_market_excluded"][0]["listing_key"]
        assert stray not in {h["key"] for h in facts["hotels"]}
        assert stray not in {normalize_name(r["name"])
                             for r in owned_by(read_production_rows(), CLEVELAND)}
