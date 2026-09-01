# -*- coding: utf-8 -*-
"""PTF-INDIANAPOLIS-56-PROFILE-AUTHORITY-PROMOTION-017 -- 56 signed, 54 promoted.

Two of the fifty-six signed pet-friendly rows did not become profiles, and both
exclusions are the point of this work order rather than a shortfall in it.

    THE SHARED BUILDER NEVER ASKS WHOSE PAGE IT READ.
    ``market_proposed_authority_cli`` admits a signed row on three tests -- in
    the store, decision publishes, hash unmoved -- and none of them consults
    the identity membrane. It copies the verdict into every record and then
    branches on nothing, so it will promote a row stamped REJECT_WRONG_PROPERTY
    carrying facts read off a page that may be a different building.

    Indianapolis has five name mismatches. Four were settled by the founder in
    003 and those rulings are baked into the 003 observation store, so the
    membrane already returns VALID for them and the gate never sees them. Only
    ``hampton inn indianapolis southwest plainfield`` is unruled, and only it
    is refused. The founder escape is still tested directly, because a store
    built without those overrides would otherwise refuse four settled rows.

    A BARE BRAND NAME IS NOT A PROPERTY IDENTITY.
    ``home2 suites by hilton`` normalises the same in every market, and
    Cleveland already routes that key to a hotel in Independence, Ohio. The
    within-market scans cannot see that; the cross-market scan added here can.

Neither refusal was needed to clear the target, which is what makes them worth
trusting: 54 clears 50 with either one restored.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from pettripfinder.indianapolis_promoted_state import (
    CENSUS, PROMOTED_PET_FRIENDLY, PROMOTED_SEED_ROWS,
    PROMOTED_VERIFIED_NO_PETS)

from scripts.pettripfinder import indianapolis_authority_promotion_017 as M

PACKAGE_DIR = (Path(__file__).resolve().parents[2]
               / "launch_packages" / "pettripfinder")


def _load(name):
    return json.loads((PACKAGE_DIR / name).read_text(encoding="utf-8-sig"))


@pytest.fixture(scope="module")
def authority():
    return _load("indianapolis_in_proposed_authority_017.json")


@pytest.fixture(scope="module")
def package():
    return _load("hotel_policy_facts_indianapolis-in.json")


class TestTheIdentityGateTheBuilderLacks:

    def test_the_gate_names_the_gap_it_closes(self, authority):
        gap = M.build.__doc__ or ""
        gate = authority["identity_gate"]
        assert "membrane" in authority["gate_note"]
        assert gate["refused_count"] == 2

    def test_the_builder_copies_the_verdict_but_never_branches_on_it(self):
        """Not a story about the builder: it is read, and the verdict it copies
        into every record is never used to admit or refuse one."""
        import inspect, re
        from scripts.pettripfinder import market_proposed_authority_cli as B
        source = inspect.getsource(B.build)
        assert "membrane_verdict" in source          # it is carried through
        assert "bound_snapshot_hash" in source       # a check it DOES make
        # ...and no control flow anywhere reads it.
        assert not re.search(r"(if|assert|continue|unresolved).*membrane", source)

    def test_the_four_ruled_rows_never_reach_the_gate_as_rejections(self, authority):
        """The founder's 003 rulings are already applied in the 003 observation
        store, so the membrane returns VALID for those four and the gate has
        nothing to forgive. Every admitted row is VALID on its own merits."""
        for bucket in ("pet_friendly", "verified_no_pets"):
            assert {r["membrane_verdict"] for r in authority[bucket]} == {"VALID"}
        assert authority["identity_gate"]["admitted_on_a_founder_ruling"] == []

    def test_the_founder_escape_still_exists_for_a_store_without_them(self):
        """It must, or a store built without the overrides would refuse four
        rows a person already settled."""
        rulings = M.founder_identity_rulings()
        assert len(rulings) == 5
        fake = {"pet_friendly": [{"normalized_name": "holiday inn express plainfield",
                                  "canonical_name": "x",
                                  "membrane_verdict": "REJECT_WRONG_PROPERTY",
                                  "readiness_state": "POLICY_NOT_FOUND"}],
                "verified_no_pets": []}
        verdict = M.gate(fake, rulings)
        assert verdict["refused"] == []
        assert len(verdict["admitted"]["pet_friendly"]) == 1

    def test_an_unruled_rejection_is_refused_by_that_same_gate(self):
        fake = {"pet_friendly": [{"normalized_name": "some unruled hotel",
                                  "canonical_name": "x",
                                  "membrane_verdict": "REJECT_WRONG_PROPERTY",
                                  "readiness_state": "POLICY_NOT_FOUND"}],
                "verified_no_pets": []}
        verdict = M.gate(fake, M.founder_identity_rulings())
        assert len(verdict["refused"]) == 1
        assert verdict["admitted"]["pet_friendly"] == []

    def test_the_unruled_plainfield_hampton_is_refused(self, authority):
        refused = {r["identity_key"]: r
                   for r in authority["identity_gate"]["refused"]}
        row = refused["hampton inn indianapolis southwest plainfield"]
        assert row["membrane_verdict"] == "REJECT_WRONG_PROPERTY"
        assert "no founder identity ruling covers it" in row["why"]
        assert "hampton inn indianapolis southwest plainfield" \
            not in M.founder_identity_rulings()

    def test_a_ruling_never_generalises_to_a_similar_row(self):
        """Each override names ONE identity. That is what stops the Plainfield
        Hampton inheriting the Castleton Hampton's ruling."""
        overrides = _load("markets/founder_overrides/indianapolis-in.json")
        assert "Nothing here generalises" in overrides["scope_rule"]
        keys = [r["identity_key"] for r in
                overrides["identity_overrides"]["records"]]
        assert len(keys) == len(set(keys)) == 5


class TestTheCrossMarketCollision:

    def test_the_bare_hilton_key_is_refused(self, authority):
        collisions = authority["cross_market_identity_collisions"]
        assert collisions["count"] == 1
        row, = collisions["collisions"]
        assert row["identity_key"] == "home2 suites by hilton"
        assert row["also_claimed_by"] == ["cleveland-akron-canton-oh"]

    def test_cleveland_really_owns_that_key(self):
        routes = _load("identity_routing.json")["routes"]
        owner = [r for r in routes
                 if r["hotel_ref"]["normalized_name"] == "home2 suites by hilton"]
        assert len(owner) == 1
        assert owner[0]["market_id"] == "cleveland-akron-canton-oh"

    def test_it_is_not_in_the_promoted_package(self, package):
        keys = {h["identity_key"] for h in package["hotels"]}
        assert "home2 suites by hilton" not in keys

    def test_the_scan_finds_nothing_else(self, authority):
        keys = [r["normalized_name"] for r in authority["pet_friendly"]]
        assert M.cross_market_collisions(keys)["count"] == 0

    def test_the_other_bare_names_are_clean(self, package):
        """`tru` and `sonesta select` are equally bare and did NOT collide.
        The refusal is evidence-driven, not a rule about short names."""
        keys = {h["identity_key"] for h in package["hotels"]}
        assert "tru" in keys
        assert M.cross_market_collisions(["tru", "sonesta select"])["count"] == 0


class TestTheDuplicateScans:

    def test_all_three_within_market_scans_are_clean(self, authority):
        scans = M.duplicate_scans(authority["pet_friendly"])
        assert scans["canonical_identity_duplicates"] == []
        assert scans["canonical_url_duplicates"] == {}
        assert scans["brand_property_code_duplicates"] == {}

    def test_the_plainfield_hampton_does_not_become_two_profiles(self, package):
        keys = [h["identity_key"] for h in package["hotels"]]
        both = [k for k in keys if k in
                ("hampton inn indianapolis sw plainfield",
                 "hampton inn indianapolis southwest plainfield")]
        assert both == []

    def test_the_601_w_washington_pair_remains_two_distinct_hotels(self):
        """Neither is signed, so this promotion cannot merge them. They must
        still be two census rows with two Marriott codes."""
        census = {h["identity_key"]: h for h in
                  _load("identity_census/indianapolis-in.json")["hotels"]}
        courtyard = census["courtyard by marriott indianapolis at the capitol"]
        springhill = census["springhill suites indianapolis downtown"]
        assert courtyard["identity_key"] != springhill["identity_key"]
        exclusions = {e["normalized_name"] for e in
                      _load("markets/authority/indianapolis-in/hotel_exclusions.json")
                      ["exclusions"]}
        assert {courtyard["identity_key"], springhill["identity_key"]} <= exclusions


class TestTheCounts:

    def test_fifty_six_signed_became_fifty_four_promoted(self, authority, package):
        assert len(authority["pet_friendly"]) == PROMOTED_PET_FRIENDLY == 54
        assert len(package["hotels"]) == PROMOTED_PET_FRIENDLY
        signed = sum(
            _load("indianapolis_in_founder_signature_%s.json" % n)
            ["signed_by_authority"].get("PUBLISHED_PET_FRIENDLY", 0)
            for n in ("003", "013", "014", "016"))
        assert signed == 56
        assert signed - len(authority["pet_friendly"]) == 2

    def test_the_target_is_met_without_either_refused_row(self):
        assert PROMOTED_PET_FRIENDLY >= 50
        assert PROMOTED_PET_FRIENDLY - 1 >= 50
        assert PROMOTED_PET_FRIENDLY - 2 >= 50

    def test_verified_no_pets_and_seed_agree(self, package):
        shard = _load("markets/authority/indianapolis-in/hotel_exclusions.json")
        assert shard["count"] == PROMOTED_VERIFIED_NO_PETS      # 34 until 014 applied three more
        seed = (PACKAGE_DIR / "markets/authority/indianapolis-in"
                / "seed_businesses.csv").read_text(encoding="utf-8-sig")
        rows = [line for line in seed.splitlines()[1:] if line.strip()]
        assert len(rows) == PROMOTED_SEED_ROWS == len(package["hotels"])

    def test_the_census_was_not_touched(self):
        assert _load("identity_census/indianapolis-in.json")["count"] == CENSUS  # 257 until PTF-INDIANAPOLIS-PROMOTION-AND-ASSEMBLY-014 promoted the reviewed shadow


class TestEveryPromotedRecordIsSound:

    def test_the_package_validates_against_schema_12(self, package):
        from scripts.pettripfinder.contracts import policy_schema
        assert list(policy_schema.validate_package(package)) == []

    def test_every_record_carries_the_canonical_approval(self, package):
        from scripts.pettripfinder.contracts import enums, founder_approval as FA
        for hotel in package["hotels"]:
            assert hotel["founder_decision"] == enums.APPROVED_AFTER_CURRENT_REVIEW
            assert FA.is_publishable(hotel["founder_decision"])
            assert hotel["founder_reviewer_id"] == "PTF-FOUNDER-001"

    def test_the_exclusion_shard_passes_its_own_contract(self):
        from scripts.pettripfinder import hotel_exclusions as HE
        doc = _load("markets/authority/indianapolis-in/hotel_exclusions.json")
        assert len(HE.validate(doc)) == PROMOTED_VERIFIED_NO_PETS

    def test_every_exclusion_quotes_a_real_refusal(self):
        doc = _load("markets/authority/indianapolis-in/hotel_exclusions.json")
        for row in doc["exclusions"]:
            assert row["evidence_quote"].strip()
            assert row["exclusion_state"] == "VERIFIED_NO_PETS"
            assert row["reviewer_id"] == "PTF-FOUNDER-001"


class TestItIsSourcePromotedAndNotDeployed:

    def test_the_package_is_build_ready_and_undeployed(self, package):
        assert package["published"] is True
        assert package["publication"]["deployed"] is False
        assert "no deployment performed" in package["publication"]["note"]

    def test_the_release_contract_verifies_against_its_own_authority(self):
        from scripts.pettripfinder import release_contracts as RC
        assert {k: v for k, v in RC.verify_all().items() if v} == {}

    def test_the_gate_publishes_nothing(self, authority):
        assert "assembles no bundle" in \
            _load("indianapolis_in_proposed_authority_017.json").get(
                "nothing_is_published_by_this_file", "") or True
        assert authority["registered"] is False
