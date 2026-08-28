# -*- coding: utf-8 -*-
"""PTF-INDIANAPOLIS-FINAL-ZERO-COST-CLEANUP-018 -- six items, no money, 54 -> 56.

Two rows became profiles and two deliberately did not, and the tests worth
having are the ones on the second pair.

    ESA IS HANDED BACK, NOT REACHED. Its capture really does contain "a
    maximum of two pets are allowed in each suite", and the committed rules
    really would approve that sentence. It stays held anyway, because the
    block the locator bounded is not empty -- it states a fee schedule -- and
    014's own rule is that an EMPTY block may be re-located off and an
    ASSERTING one may not. Reaching it needs a re-locate and a fact override,
    and both are the founder's.

    HOME2 IS RENAMED, NOT PROMOTED. The overlay was verified NOT to rekey the
    census identity, so the key Cleveland already owns is still the key this
    row carries.

    THE 14 MISMATCHES RECOVERED NOTHING. A refused capture kept no artifact,
    so "repaired" means the rule stops refusing wrongly -- not that a policy
    came back. Exactly one repairs, and sixteen controls hold the other
    thirteen apart.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from pettripfinder.indianapolis_promoted_state import (
    CENSUS, PROMOTED_PET_FRIENDLY, PROMOTED_SEED_ROWS, PROMOTED_VERIFIED_NO_PETS)

from scripts.pettripfinder import indianapolis_final_cleanup_018 as M
from scripts.pettripfinder import indianapolis_founder_review_013 as R
from scripts.pettripfinder.brightdata.policy_surface import streets_agree

PACKAGE_DIR = (Path(__file__).resolve().parents[2]
               / "launch_packages" / "pettripfinder")


def _load(name):
    return json.loads((PACKAGE_DIR / name).read_text(encoding="utf-8-sig"))


@pytest.fixture(scope="module")
def cleanup():
    return _load("indianapolis_in_final_cleanup_018.json")


@pytest.fixture(scope="module")
def package():
    return _load("hotel_policy_facts_indianapolis-in.json")


class TestNothingWasBought:

    def test_no_provider_call_and_no_spend(self, cleanup):
        assert cleanup["provider_calls"] == 0
        assert cleanup["usd_spent"] == 0.0
        assert cleanup["nothing_was_fetched"] is True

    def test_the_paid_ledger_gained_no_run(self):
        ledger = _load("ptf_paid_attempt_ledger_001.json")
        runs = {a.get("run_id") for a in ledger["attempts"]
                if a.get("market_id") == "indianapolis-in"}
        assert runs == {"indianapolis-in-002-pass1", "indianapolis-in-002-pass2",
                        "indianapolis-in-012", "indianapolis-in-016"}


class TestItem1PlainfieldHampton:

    def test_it_is_promoted(self, cleanup, package):
        assert cleanup["item_1_plainfield_hampton_identity_ruling"]["rule_satisfied"]
        assert M.PLAINFIELD in {h["identity_key"] for h in package["hotels"]}

    def test_the_phone_is_what_carries_it(self, cleanup):
        signals = cleanup["item_1_plainfield_hampton_identity_ruling"]["signals"]
        assert signals["exact_telephone"]["agrees"] is True
        assert signals["brand_property_code"]["agrees"] is True
        assert signals["street_identity"]["agrees"] is False

    def test_the_street_conflict_is_not_pretended_away(self, cleanup):
        ruling = cleanup["item_1_plainfield_hampton_identity_ruling"]
        assert "does NOT decide which is right" in \
            ruling["street_disagreement_is_not_reconciled"]
        assert streets_agree("2244 East Perry Road", "2244 East Main Street")[0] is False

    def test_the_rule_applied_is_the_founders_own(self, cleanup):
        ruling = cleanup["item_1_plainfield_hampton_identity_ruling"]
        overrides = _load("markets/founder_overrides/indianapolis-in.json")
        assert ruling["founder_rule_applied"] == \
            overrides["identity_overrides"]["founder_ruling"]
        assert "an exact telephone" in ruling["founder_rule_applied"]

    def test_the_ruling_is_recorded_where_rulings_live(self):
        overrides = _load("markets/founder_overrides/indianapolis-in.json")
        row = next(r for r in overrides["identity_overrides"]["records"]
                   if r["identity_key"] == M.PLAINFIELD)
        assert row["telephone"]["agrees"] is True
        assert row["street"]["agrees"] is False
        assert "the operator" in row["decided_by"]

    def test_it_was_not_signed_twice(self):
        """It was already signed by 013. An attestation is a dated act."""
        eighteen = {r["identity_key"]
                    for r in _load("indianapolis_in_founder_signature_018.json")["signed"]}
        thirteen = {r["identity_key"]
                    for r in _load("indianapolis_in_founder_signature_013.json")["signed"]}
        assert M.PLAINFIELD in thirteen
        assert M.PLAINFIELD not in eighteen


class TestItem4OmniSeverin:

    def test_it_is_promoted(self, cleanup, package):
        assert cleanup["item_4_omni_severin"]["disposition"] == R.APPROVE_PET_FRIENDLY
        assert M.OMNI in {h["identity_key"] for h in package["hotels"]}

    def test_nothing_was_re_located_for_it(self, cleanup):
        """The block is the one the locator already bounded."""
        omni = cleanup["item_4_omni_severin"]
        assert "no re-located" in omni["what_changed"] or \
            "re-located or re-acquired" in omni["what_changed"]
        run = _load("indianapolis_in_market_acquisition_016.json")
        row = next(r for r in run["results"] if r["identity_key"] == M.OMNI)
        assert omni["content_hash"] == row["content_hash"]

    def test_the_widening_is_anchored(self):
        """It must catch the permission and miss the marketing phrase."""
        assert R.read_block("is a pet friendly hotel")["allowing_language"]
        assert R.read_block("Pet friendly rooms available.")["allowing_language"] == []
        assert R.read_block("/services-programs/pet-friendly-hotels")["allowing_language"] == []

    def test_a_refusal_still_outranks_it(self):
        block = "This is not a pet friendly hotel; pets are not allowed."
        assert R.rule({"policy_block": block}, R.read_block(block))[0] == R.APPROVE_NO_PETS


class TestItem5EsaIsHandedBackNotReached:

    def test_the_permission_really_is_in_the_capture(self, cleanup):
        esa = cleanup["item_5_esa_fee_only_hold"]
        assert esa["the_permission_is_in_the_capture"] is True
        assert "two pets are allowed in each suite" in esa["quote"]
        assert esa["committed_rules_would_approve_that_sentence"] == R.APPROVE_PET_FRIENDLY

    def test_and_it_is_still_held(self, cleanup, package):
        esa = cleanup["item_5_esa_fee_only_hold"]
        assert esa["state"].startswith("STILL HELD")
        assert M.ESA not in {h["identity_key"] for h in package["hotels"]}

    def test_because_the_block_asserts_something(self, cleanup):
        """014's rule, applied to 014's own author."""
        why = cleanup["item_5_esa_fee_only_hold"]["why_it_is_not_resolved_here"]
        assert "not empty" in why["the_block_asserts_something"]
        assert "fee schedule" in why["the_block_asserts_something"]
        held = cleanup["item_5_esa_fee_only_hold"]["held_block"]
        assert held.strip()
        assert R.rule({"policy_block": held}, R.read_block(held))[0] == R.HOLD

    def test_the_capture_contains_no_refusal(self, cleanup):
        esa = cleanup["item_5_esa_fee_only_hold"]
        assert esa["contradicting_refusals_in_the_whole_capture"] == "none"

    def test_the_ruling_it_needs_is_spelled_out(self, cleanup):
        esa = cleanup["item_5_esa_fee_only_hold"]
        assert "pet permission" in esa["what_a_ruling_would_need_to_say"]


class TestItems2And3NameCorrections:

    def test_both_names_come_from_the_property_page(self, cleanup):
        doc = _load("markets/name_corrections/indianapolis-in.json")
        assert doc["count"] == 2
        for row in doc["records"]:
            assert row["evidence_field"] == "identity_check.name_on_page"
            assert row["source_url"].startswith("https://www.hilton.com/")

    def test_tru_publishes_a_building_now(self, package):
        tru = next(h for h in package["hotels"] if h["identity_key"] == "tru")
        assert tru["name"] == "Tru by Hilton Indianapolis Downtown"
        assert tru["key"] == "tru by hilton indianapolis downtown"

    def test_the_correction_does_not_rekey_the_identity(self, cleanup, package):
        """Verified empirically, and it is why Home2 is still refused."""
        for row in cleanup["item_2_and_3_canonical_name_corrections"]["records"]:
            assert row["rekeys_the_identity"] is False
        assert "tru" in {h["identity_key"] for h in package["hotels"]}

    def test_key_diverging_from_identity_key_is_the_normal_shape(self, package):
        """Louisville carries eight such rows and St. Louis four."""
        diverged = [h for h in package["hotels"] if h["key"] != h["identity_key"]]
        assert len(diverged) == 1
        other = _load("hotel_policy_facts_louisville-ky.json")["hotels"]
        assert len([h for h in other if h["key"] != h["identity_key"]]) == 8

    def test_home2_is_renamed_and_still_refused(self, cleanup, package):
        home2 = cleanup["home2_is_still_refused"]
        assert home2["name_corrected"] is True and home2["promoted"] is False
        assert "Cleveland" in home2["why"]
        assert "home2 suites by hilton" not in {h["identity_key"] for h in package["hotels"]}


class TestItem6RoutingRepair:

    def test_all_fourteen_examined_one_repaired(self, cleanup):
        routing = cleanup["item_6_routing_repair"]
        assert routing["examined"] == 14
        assert routing["repaired"] == 1
        assert routing["still_unresolved"] == 13
        assert routing["repaired_keys"] == [
            "extended stay america indianapolis west 86th st"]

    def test_no_policy_came_back_and_the_report_says_so(self, cleanup):
        routing = cleanup["item_6_routing_repair"]
        assert all(r["policy_recovered"] is False for r in routing["rows"])
        assert all(r["saved_artifact"] is False for r in routing["rows"])
        assert "does not recover a policy" in routing["no_policy_was_recovered"]

    def test_the_split_directional_rule_repairs_the_one(self):
        agree, why = streets_agree("8520 N.W. Blvd.", "8520 Northwest Boulevard")
        assert agree is True
        assert "split by full stops" in why

    @pytest.mark.parametrize("page,census", [
        ("2245 E Perry Rd", "2245 W Perry Rd"),          # opposite directionals
        ("2245 N.E. Perry Rd", "2245 N.W. Perry Rd"),    # opposite split pairs
        ("17070 Dragonfly Lane", "17070 Dragonfly Drive"),
        ("8301 Bash Street", "8255 Bash Street"),
        ("6300 Gateway Drive", "6010 Gateway Drive"),
        ("31 Maplehurst Drive", "31 Brownsburg Place"),
        ("100 N W", "100 Northwest"),                    # the pair names no street
    ])
    def test_the_widening_merges_no_two_buildings(self, page, census):
        assert streets_agree(page, census)[0] is False

    def test_the_earlier_widenings_still_work(self):
        assert streets_agree("7226 Woodland Drive at 71st Street",
                             "7226 Woodland Drive")[0] is True
        assert streets_agree("2245 East Perry Road", "2245 Perry Road")[0] is True

    def test_every_unresolved_row_says_why(self, cleanup):
        for row in cleanup["item_6_routing_repair"]["rows"]:
            if not row["repaired"]:
                assert row["still_unresolved_because"].strip()


class TestTheResultingState:

    def test_fifty_four_became_fifty_six(self, cleanup, package):
        counts = cleanup["counts"]
        assert counts["starting_pet_friendly"] == 54
        assert counts["ending_pet_friendly"] == PROMOTED_PET_FRIENDLY == 56
        assert len(package["hotels"]) == 56

    def test_the_other_totals(self, package):
        assert _load("markets/authority/indianapolis-in/hotel_exclusions.json")["count"] \
            == PROMOTED_VERIFIED_NO_PETS == 34
        assert _load("identity_census/indianapolis-in.json")["count"] == CENSUS == 257
        seed = (PACKAGE_DIR / "markets/authority/indianapolis-in"
                / "seed_businesses.csv").read_text(encoding="utf-8-sig")
        rows = [line for line in seed.splitlines()[1:] if line.strip()]
        assert len(rows) == PROMOTED_SEED_ROWS == 56

    def test_the_fifty_four_that_were_already_there_are_untouched(self, package):
        """Only Tru's NAME may have moved, and only because it was corrected."""
        import subprocess
        prior = json.loads(subprocess.run(
            ["git", "show", "6ee99f7:atlas-dashboard/launch_packages/pettripfinder/"
             "hotel_policy_facts_indianapolis-in.json"],
            capture_output=True).stdout.decode("utf-8"))
        old = {h["identity_key"]: h for h in prior["hotels"]}
        new = {h["identity_key"]: h for h in package["hotels"]}
        changed = [k for k, v in old.items()
                   if json.dumps(v, sort_keys=True) != json.dumps(new[k], sort_keys=True)]
        assert changed == ["tru"]
        assert set(new) - set(old) == {M.PLAINFIELD, M.OMNI}

    def test_every_contract_still_verifies(self):
        from scripts.pettripfinder import release_contracts as RC
        assert {k: v for k, v in RC.verify_all().items() if v} == {}

    def test_still_source_promoted_and_not_deployed(self, package):
        assert package["published"] is True
        assert package["publication"]["deployed"] is False
