# -*- coding: utf-8 -*-
"""PTF-GRAND-RAPIDS-FOUNDER-RULINGS-020.

The counts are pinned, and so are the two rules that stop this pass doing
damage rather than merely being wrong.

THE FIRST is the founder's own constraint on identity: a shared telephone alone
may never confirm it. It is asserted as arithmetic -- two agreeing signals, one
of them not the telephone -- and there are tests that a confirmation the
evidence cannot carry RAISES, because a rule a run cannot fail is not a rule.

THE SECOND is the inversion this build actually hit and had to fix. ``baymont``
carries ``pets_allowed: None`` in the observation store; the founder's
price-implies-allowance doctrine rules it TRUE, and the store is not edited.
Reading the class straight off the untouched record turned a hotel that charges
25.00 USD per pet per night into a VERIFIED NO-PETS entry -- the founder's
silence doctrine violated from the other direction. ``every_no_pets_row_states_a_refusal``
is the guard, and the test below drives the defect to make sure it still bites.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.pettripfinder import grand_rapids_holland_founder_rulings_020 as R  # noqa: E402

LP = REPO_ROOT / "launch_packages" / "pettripfinder"
LEDGER = LP / "grand_rapids_holland_mi_founder_decision_ledger_020.json"
CLASSIFICATION = LP / "grand_rapids_holland_mi_founder_review_classification_020.json"
READINESS = LP / "grand_rapids_holland_mi_proposed_authority_readiness_020.json"


def _load(path):
    assert path.is_file(), "%s is missing" % path.name
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def ledger():
    return _load(LEDGER)


@pytest.fixture(scope="module")
def classification():
    return _load(CLASSIFICATION)


@pytest.fixture(scope="module")
def readiness():
    return _load(READINESS)


# --------------------------------------------------------------------------- #
# Authorship
# --------------------------------------------------------------------------- #

def test_the_ledger_separates_what_the_founder_decided_from_what_was_delegated(ledger):
    """A doctrine and a correction are the founder's. A per-row identity
    verdict is the operator's, decided under the founder's constraint. Blurring
    them is how an operator's opinion acquires a founder's authority."""
    for entry in ledger["allowance_rulings"] + ledger["corrections"]:
        assert entry["ruling_authority"] == R.BY_FOUNDER
        assert entry["ruled_by"] == R.FOUNDER
    for entry in ledger["identity_rulings"]:
        assert entry["ruling_authority"] == R.BY_OPERATOR_UNDER_DELEGATION
        assert entry["ruled_by"] == R.OPERATOR
        assert entry["founder_constraint"]


def test_only_the_rows_this_order_names_are_signed(ledger, classification):
    """45 rows were called clean by a MACHINE review in 019. None of them
    acquires a signature here."""
    assert ledger["rows_ruled"] == 16
    assert ledger["rows_left_unsigned"] == 45
    ruled = R.ruled_keys(ledger)
    for row in classification["rows"]:
        if row["signed_in_this_order"]:
            assert row["identity_key"] in ruled


# --------------------------------------------------------------------------- #
# Doctrine 1 -- a stated pet price implies an allowance
# --------------------------------------------------------------------------- #

def test_both_allowance_rulings_cite_an_explicit_pet_specific_price(ledger):
    assert len(ledger["allowance_rulings"]) == 2
    keys = {e["identity_key"] for e in ledger["allowance_rulings"]}
    assert keys == {"baymont", "travelodge by wyndham grand rapids north"}
    for entry in ledger["allowance_rulings"]:
        assert entry["ruling"] == "PETS_ALLOWED_TRUE"
        assert entry["pet_specific_price_quote"]
        assert entry["membrane_verdict"] == "VALID"
        # Both sources also say it in words, so neither ruling rests on the
        # inference the doctrine authorises.
        assert entry["source_also_states_the_allowance_in_words"]


def test_the_doctrine_refuses_a_row_that_states_no_pet_specific_price():
    """Its bound. A record whose fee is generic, or absent, is not reached."""
    record = {
        "canonical_name": "X",
        "membrane": {"verdict": "VALID"},
        "withheld_fields": {"pets_allowed": "SOURCE_SILENT"},
        "observation": {"extraction": {"pet_fee": None}, "evidence": []},
    }
    assert R.pet_specific_price(record, "A resort fee of 25.00 USD applies.") == ""
    assert R.pet_specific_price(record, "") == ""


def test_the_doctrine_refuses_a_row_whose_allowance_is_not_withheld():
    record = {
        "canonical_name": "X", "membrane": {"verdict": "VALID"},
        "withheld_fields": {},
        "observation": {"extraction": {"pets_allowed": True}, "evidence": []},
    }
    with pytest.raises(R.RulingError):
        R.build_allowance_entries({"baymont": record})


def test_a_pet_price_is_recognised_and_a_generic_one_is_not():
    assert R.pet_specific_price(
        {"observation": {"extraction": {}, "evidence": []}},
        "Up to 2 pets are welcome for 10.00 USD per pet per night.")
    assert not R.pet_specific_price(
        {"observation": {"extraction": {}, "evidence": []}},
        "A destination fee of 30.00 USD is charged nightly.")


# --------------------------------------------------------------------------- #
# Doctrine 2 -- source silence
# --------------------------------------------------------------------------- #

def test_the_three_silent_rows_stay_unresolved(ledger, classification):
    keys = {e["identity_key"] for e in ledger["silence_rulings"]}
    assert keys == {"doubletree by hilton hotel grand rapids airport",
                    "drury inn and suites grand rapids", "tulyp"}
    for entry in ledger["silence_rulings"]:
        assert entry["ruling"] == "POLICY_NOT_FOUND_UNRESOLVED"
        assert entry["becomes_verified_no_pets"] is False
    for row in classification["rows"]:
        if row["identity_key"] in keys:
            assert row["now"] == R.POLICY_NOT_FOUND
            assert row["pets_allowed_after_rulings"] is None


def test_an_amenity_token_is_not_a_policy(ledger):
    """Two of the three pages DO carry the word 'Pets' -- as an amenity list
    item and as a policy heading whose body never rendered. The founder's
    doctrine rules out inferring from either, and the ledger records that the
    tokens were seen rather than pretending the pages were blank."""
    seen = [e for e in ledger["silence_rulings"]
            if e["saved_page_mentions_a_pet_token"]]
    assert len(seen) == 2
    for entry in seen:
        assert entry["becomes_verified_no_pets"] is False
        assert "amenity" in entry["why"]


# --------------------------------------------------------------------------- #
# The inversion guard
# --------------------------------------------------------------------------- #

def test_an_unresolved_allowance_can_never_be_called_verified_no_pets():
    """The defect this build hit: pets_allowed None read as falsy."""
    with pytest.raises(R.RulingError):
        R.class_of("x", {"x": {"pets_allowed": None}})
    assert R.class_of("x", {"x": {"pets_allowed": False}}) == R.CLEAN_VERIFIED_NO_PETS
    assert R.class_of("x", {"x": {"pets_allowed": True}}) == R.CLEAN_PET_FRIENDLY


def test_the_ruled_facts_override_the_untouched_store(ledger, classification):
    """The store is not edited -- an observation records what a page said, and
    a ruling is a different kind of statement -- so baymont's class has to come
    from the ruling."""
    baymont = [r for r in classification["rows"]
               if r["identity_key"] == "baymont"][0]
    assert baymont["pets_allowed_after_rulings"] is True
    assert baymont["now"] == R.CLEAN_PET_FRIENDLY
    store = json.loads((LP / "grand_rapids_holland_mi_observation_store_001.json")
                       .read_text(encoding="utf-8"))
    on_disk = [r for r in store["records"] if r["identity_key"] == "baymont"][0]
    assert on_disk["observation"]["extraction"].get("pets_allowed") is None, (
        "the observation store must stay exactly as the reader wrote it")


def test_every_no_pets_row_states_a_refusal(readiness, classification):
    check = readiness["validation"]["every_no_pets_row_states_a_refusal"]
    assert check["ok"] is True
    for row in classification["rows"]:
        if row["now"] == R.CLEAN_VERIFIED_NO_PETS:
            assert row["pets_allowed_after_rulings"] is False


# --------------------------------------------------------------------------- #
# Identity
# --------------------------------------------------------------------------- #

def test_seven_confirmed_one_held(ledger):
    verdicts = {e["identity_key"]: e["ruling"] for e in ledger["identity_rulings"]}
    assert len(verdicts) == 8
    assert sum(1 for v in verdicts.values()
               if v == R.SAME_PROPERTY_CONFIRMED) == 7
    assert verdicts["budgetel grand rapids"] == R.HOLD_IDENTITY
    assert R.DISTINCT_PROPERTY not in verdicts.values()


def test_no_confirmation_rests_on_the_telephone(ledger):
    """The founder's constraint, as arithmetic."""
    for entry in ledger["identity_rulings"]:
        if entry["ruling"] != R.SAME_PROPERTY_CONFIRMED:
            continue
        assert entry["signals_agreed_count"] >= 2
        assert entry["non_telephone_signals"], entry["identity_key"]


def test_a_confirmation_the_evidence_cannot_carry_raises():
    """Not a comment: the ledger refuses to record it."""
    census = {"x": {"canonical_name": "X Hotel", "phone": "6165550100",
                    "address": "1 Main St", "postal_code": "49503"}}
    signals = {"phone_on_page": "616-555-0100", "phones_on_page": [],
               "name_on_page": "", "address_on_page": "", "postal_code": "",
               "property_code_on_page": "", "canonical_url": ""}
    derived = R.identity_signals(census["x"], signals)
    assert list(derived["agreed"]) == [R.SIGNAL_TELEPHONE]
    assert derived["satisfies_confirmation_rule"] is False


def test_the_ada_hotels_generic_words_are_not_a_name_signal():
    """The membrane's own complaint: 'ada, hotel, the' are words this market
    shares. What carries that row is its own domain and its telephone."""
    assert R._distinctive("The Ada Hotel") == frozenset({"ada"})
    assert R._distinctive("Grand Rapids Downtown Hotel") == frozenset()


def test_two_spellings_of_one_street_agree():
    """5970 Metro Way S.W. and 5970 Metro Way SouthW. are one address."""
    census = {"canonical_name": "Fairfield Inn & Suites Grand Rapids Wyoming",
              "address": "5970 Metro Way SouthW.", "postal_code": "49519",
              "phone": "", "official_url": "https://www.marriott.com/grrfw"}
    signals = {"address_on_page": "5970 Metro Way S.W.", "postal_code": "49519",
               "name_on_page": "Fairfield by Marriott Inn & Suites Grand Rapids Wyoming",
               "property_code_on_page": "grrfw", "phone_on_page": "",
               "phones_on_page": [], "canonical_url": ""}
    derived = R.identity_signals(census, signals)
    assert R.SIGNAL_STREET in derived["agreed"]
    assert R.SIGNAL_PROPERTY_CODE in derived["agreed"]
    assert derived["satisfies_confirmation_rule"] is True


def test_a_country_code_does_not_hide_a_telephone_agreement():
    assert R._digits("1-616-9533900") == R._digits("6169533900")
    assert R._digits("+16167763200") == "6167763200"
    assert R._digits("6169533900") == "6169533900"


def test_only_avid_zeeland_becomes_a_candidate_today(ledger):
    """Six rows were declined at the IDENTITY gate, before the policy locator
    ever ran, so their captures carry no policy block. Confirming identity says
    who the page is about; it does not read what the page says."""
    yields = [e for e in ledger["identity_rulings"]
              if e["yields_a_policy_observation_today"]]
    assert [e["identity_key"] for e in yields] == ["avid hotel zeeland"]
    quiet = [e for e in ledger["identity_rulings"]
             if e["ruling"] == R.SAME_PROPERTY_CONFIRMED
             and e["saved_page_mentions_pets"] is False]
    assert len(quiet) == 4, (
        "four of the confirmed pages never mention a pet, so a free re-locate "
        "over them should be expected to return POLICY_NOT_FOUND")


# --------------------------------------------------------------------------- #
# The pairs
# --------------------------------------------------------------------------- #

def test_nothing_is_merged_and_no_pair_is_decided_on_a_shared_phone(ledger):
    assert len(ledger["pair_rulings"]) == 5
    for pair in ledger["pair_rulings"]:
        assert pair["merged"] is False
        assert pair["decided_on_shared_telephone_alone"] is False


def test_the_three_named_pairs_stay_independent(ledger):
    preserved = {tuple(p["identity_keys"]) for p in ledger["pair_rulings"]
                 if p["ruling"] == R.PRESERVE_INDEPENDENT}
    assert ("comfort inn", "comfort suites grandville grand rapids sw") in preserved
    assert ("sleep inn and suites", "spark by hilton grand rapids") in preserved
    assert ("budgetel grand rapids", "budgetel inn and suites hotel") in preserved
    for pair in ledger["pair_rulings"]:
        if pair["ruling"] == R.PRESERVE_INDEPENDENT:
            assert pair["shares_a_telephone"] is True


def test_two_rebrands_are_recorded_rather_than_merged(ledger):
    """The founder asked for this explicitly: evidence of a successor
    relationship is written down, not acted on."""
    recorded = [p for p in ledger["pair_rulings"]
                if p["ruling"] == R.REBRAND_RECORDED]
    assert len(recorded) == 2
    assert {tuple(p["identity_keys"]) for p in recorded} == {
        ("baymont inn and suites grand rapids airport",
         "baymont by wyndham grand rapids airport"),
        ("the bluejay hotel", "the blue jay hotel and events")}
    for pair in recorded:
        assert pair["merged"] is False


# --------------------------------------------------------------------------- #
# The classification and the gate
# --------------------------------------------------------------------------- #

def test_the_rebuilt_classification(classification):
    counts = classification["counts"]
    assert counts[R.CLEAN_PET_FRIENDLY] == 36
    assert counts[R.CLEAN_VERIFIED_NO_PETS] == 15
    assert counts[R.POLICY_NOT_FOUND] == 3
    assert sum(counts.values()) == 54
    assert len(classification["changed"]) == 9


def test_the_authority_is_not_built_and_the_gate_is_named(readiness):
    """The order's conditional is not met, and saying so is the answer."""
    assert readiness["ready_to_build"] is False
    assert "no Grand Rapids record carries a founder approval" in readiness["blocked_by"]
    assert readiness["would_contain"] == 50
    assert readiness["pet_friendly"] == 36
    assert readiness["verified_no_pets"] == 14
    assert readiness["exact_next_step"]


def test_a_fact_ruling_is_not_counted_as_a_record_approval(readiness):
    """The count that matters is 50 awaiting, not 44. This order settled facts
    inside five records and confirmed one more record's identity; none of that
    is a founder decision from the approval vocabulary over a whole record.
    Reporting six rows as signed would let a reader believe six records were
    approved when none was -- the same error as signing them, reached by
    rounding."""
    assert readiness["rows_with_a_record_level_founder_approval"] == 0
    assert readiness["awaiting_a_record_level_approval"] == 50
    assert sorted(readiness["rows_with_a_founder_fact_ruling"]) == [
        "baymont", "baymont by wyndham holland", "doubletree by hilton",
        "travelodge by wyndham grand rapids north", "tru"]
    assert readiness["rows_admitted_by_a_delegated_identity_verdict"] == [
        "avid hotel zeeland"]
    for row in readiness["candidates"]:
        assert row["founder_record_approval"] == ""
        assert row["semantic_approval_hash"]


def test_the_held_identity_is_still_withheld(readiness):
    assert readiness["withheld_on_an_open_identity"] == [
        "comfort suites grandville grand rapids sw"]
    keys = {c["identity_key"] for c in readiness["candidates"]}
    assert "comfort suites grandville grand rapids sw" not in keys
    assert "budgetel grand rapids" not in keys


def test_every_validation_check_passes(readiness):
    validation = readiness["validation"]
    for name, check in validation.items():
        if name == "all_pass":
            continue
        assert check["ok"] is True, "%s: %r" % (name, check)
    assert validation["all_pass"] is True


def test_no_cross_market_collision(readiness):
    check = readiness["validation"]["no_cross_market_collision"]
    assert check["ok"] is True
    assert check["markets_scanned"] >= 10
    assert check["collisions"] == []


def test_nothing_was_spent(ledger, classification, readiness):
    for document in (ledger, classification, readiness):
        assert document["provider_calls"] == 0
        assert document["usd_spent"] == 0.0
        assert document["plan_credits_spent"] == 0.0


def test_no_market_authority_or_census_is_written_by_this_pass():
    import subprocess
    result = subprocess.run(
        ["git", "status", "--porcelain", "--",
         "launch_packages/pettripfinder/markets",
         "launch_packages/pettripfinder/identity_census"],
        cwd=str(REPO_ROOT.parent), capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "", (
        "a market contract, authority shard or census changed: %r"
        % result.stdout)
