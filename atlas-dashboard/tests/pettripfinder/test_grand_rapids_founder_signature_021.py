# -*- coding: utf-8 -*-
"""PTF-GRAND-RAPIDS-FOUNDER-SIGNATURE-PASS-021.

The counts are pinned. Beyond that, three things get their own tests because
they are where a signature pass can go quietly wrong.

THE BINDING. A signature is bound to a semantic hash so it lapses when a fact
moves. Five of the fifty hashes DIFFER from the one 019 recorded -- they moved
because 020 ruled on them -- and the rebinding is only legitimate because it is
PROVEN rather than assumed: each hash must first reproduce exactly from the
untouched store, and may then move only for a field 020 names. A hash that
moves for any other reason is refused, and there is a test that it is.

THE FACTS THE AUTHORITY PUBLISHES. The builder reads facts from the observation
store, so a market signed on 020's rulings but built from the untouched store
would publish baymont as pet-friendly with no ``pets_allowed`` at all. A derived
store carries the ruled values; the original stays byte-for-byte as the reader
wrote it, and both are asserted.

THE ROWS THE CONTRACT DEFERS. ``publishable_subject_to_existing_gates`` is False
for every confirmed REFUSAL too, because a no-pets row publishes no profile --
it becomes an exclusion. Keying the gate on that flag would have held back all
14 exclusions for a reason the contract never gave, so the deferral is read off
the readiness STATE instead, and the test pins which states route themselves.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.pettripfinder import grand_rapids_holland_founder_signature_021 as S  # noqa: E402
from scripts.pettripfinder.contracts import enums                                  # noqa: E402
from scripts.pettripfinder.contracts import founder_approval as FA                 # noqa: E402

LP = REPO_ROOT / "launch_packages" / "pettripfinder"
ORIGINAL_STORE = LP / "grand_rapids_holland_mi_observation_store_001.json"
DERIVED_STORE = LP / "grand_rapids_holland_mi_observation_store_021.json"
LEDGER = LP / "grand_rapids_holland_mi_founder_decision_ledger_021.json"
CONFIRMATIONS = LP / "grand_rapids_holland_mi_identity_confirmations_021.json"
AUTHORITY = LP / "grand_rapids_holland_mi_proposed_authority_021.json"
PROMOTION = LP / "grand_rapids_holland_mi_source_promotion_readiness_021.json"

RULED = {"baymont", "baymont by wyndham holland", "doubletree by hilton",
         "travelodge by wyndham grand rapids north", "tru"}


def _load(path):
    assert path.is_file(), "%s is missing" % path.name
    return json.loads(path.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def ledger():
    return _load(LEDGER)


@pytest.fixture(scope="module")
def authority():
    return _load(AUTHORITY)


@pytest.fixture(scope="module")
def promotion():
    return _load(PROMOTION)


@pytest.fixture(scope="module")
def derived():
    return {r["identity_key"]: r for r in _load(DERIVED_STORE)["records"]}


# --------------------------------------------------------------------------- #
# The signatures
# --------------------------------------------------------------------------- #

def test_fifty_presented_fifty_signed_none_refused(ledger):
    assert ledger["candidates_presented"] == 50
    assert ledger["signatures_written"] == 50
    assert ledger["refused"] == 0
    assert ledger["refused_rows"] == []
    assert len(ledger["signed"]) == 50
    assert len({r["identity_key"] for r in ledger["signed"]}) == 50


def test_forty_five_hashes_were_unchanged_and_five_were_rebound(ledger):
    assert ledger["by_outcome"] == {
        S.SIGNED_HASH_UNCHANGED: 45, S.SIGNED_HASH_REBOUND: 5}
    rebound = {r["identity_key"] for r in ledger["all_signatures"]
               if r["outcome"] == S.SIGNED_HASH_REBOUND}
    assert rebound == RULED


def test_every_rebinding_is_explained_by_a_field_020_ruled_on(ledger):
    """Not "the hash moved and we allowed it" -- the moved FIELD is named."""
    for row in ledger["all_signatures"]:
        if row["outcome"] == S.SIGNED_HASH_REBOUND:
            assert row["hash_moved_by"], row["identity_key"]
            assert row["reviewed_semantic_hash"] != row["bound_semantic_hash"]
        if row["outcome"] == S.SIGNED_HASH_UNCHANGED:
            assert row["hash_moved_by"] == []
            assert row["reviewed_semantic_hash"] == row["bound_semantic_hash"]


def test_every_hash_reproduces_from_the_untouched_store(ledger):
    """Step one of the binding proof. If a row's hash did not reproduce, the
    store drifted after review and the row would be refused rather than
    rebound."""
    for row in ledger["all_signatures"]:
        assert (row["semantic_hash_from_the_untouched_store"]
                == row["reviewed_semantic_hash"]), row["identity_key"]


def test_a_hash_that_moved_for_an_unruled_reason_is_refused():
    """The check that makes the rebinding safe rather than convenient."""
    census = {"x": {"corridor": "c"}}
    original = {"x": {"identity_key": "x", "canonical_name": "X",
                      "observation": {"snapshot_hash": "s"}}}
    derived = dict(original)

    calls = {"n": 0}

    def fake_hash(record, row):
        calls["n"] += 1
        return "H1" if calls["n"] == 1 else "H2"

    saved = S.semantic_hash_of
    S.semantic_hash_of = fake_hash
    try:
        rows = S.sign([{"identity_key": "x", "class": S.CLEAN_PET_FRIENDLY}],
                      {"x": "H1"}, original, derived, census, {})
    finally:
        S.semantic_hash_of = saved
    assert rows[0]["outcome"] == S.REFUSED_UNEXPLAINED
    assert rows[0]["founder_decision"] == ""
    assert rows[0]["founder_reviewer_id"] == ""


def test_a_store_that_drifted_since_review_is_refused():
    census = {"x": {"corridor": "c"}}
    original = {"x": {"identity_key": "x", "canonical_name": "X",
                      "observation": {"snapshot_hash": "s"}}}
    saved = S.semantic_hash_of
    S.semantic_hash_of = lambda record, row: "MOVED"
    try:
        rows = S.sign([{"identity_key": "x", "class": S.CLEAN_PET_FRIENDLY}],
                      {"x": "REVIEWED"}, original, dict(original), census,
                      {"x": [{"field": "pets_allowed"}]})
    finally:
        S.semantic_hash_of = saved
    assert rows[0]["outcome"] == S.REFUSED_STORE_DRIFTED
    assert rows[0]["founder_decision"] == ""


def test_the_decision_is_the_canonical_vocabulary_value(ledger):
    assert ledger["approval_vocabulary"] == FA.VOCABULARY_VERSION
    assert ledger["decided_by"] == S.FOUNDER
    for row in ledger["signed"]:
        assert row["founder_decision"] == FA.CANONICAL_APPROVED
        assert FA.is_publishable(row["founder_decision"])
        assert row["founder_reviewer_id"] == "PTF-FOUNDER-001"
        assert row["founder_reviewed_at"] == S.REVIEWED_AT
        assert row["founder_authorization"]


# --------------------------------------------------------------------------- #
# The derived store
# --------------------------------------------------------------------------- #

def test_the_original_store_is_untouched():
    """An observation records what a page said. A founder ruling is a different
    kind of statement and must not be disguised as one."""
    original = {r["identity_key"]: r for r in _load(ORIGINAL_STORE)["records"]}
    assert original["baymont"]["observation"]["extraction"].get(
        "pets_allowed") is None
    assert original["baymont"]["canonical_name"] == "Baymont"
    assert original["baymont"]["withheld_fields"] == {
        "pets_allowed": "SOURCE_SILENT"}


def test_the_derived_store_carries_the_ruled_values_with_provenance(derived):
    document = _load(DERIVED_STORE)
    assert document["records_changed"] == 5
    assert set(document["rulings_applied"]) == RULED
    for key, changes in document["rulings_applied"].items():
        for change in changes:
            assert change["ruling"]
            assert change["why"]
            assert change["from"] != change["to"]

    assert derived["baymont"]["observation"]["extraction"]["pets_allowed"] is True
    assert derived["baymont"]["canonical_name"] == (
        "Baymont by Wyndham Grand Rapids Near Downtown")
    assert derived["baymont"]["withheld_fields"] == {}
    assert derived["baymont by wyndham holland"]["observation"]["extraction"][
        "weight_limit"] == {"value": 100.0, "unit": "lb"}


def test_a_ruled_allowance_does_not_release_an_unrelated_withholding(derived):
    """The doctrine settles the allowance and says nothing about a fee the
    schema could not represent, so those withholdings survive."""
    travelodge = derived["travelodge by wyndham grand rapids north"]
    assert travelodge["observation"]["extraction"]["pets_allowed"] is True
    assert travelodge["withheld_fields"] == {
        "pet_fee": "SCHEMA_CANNOT_REPRESENT",
        "fee_basis": "SCHEMA_CANNOT_REPRESENT"}


def test_no_membrane_verdict_is_rewritten(derived):
    """A ruling that erased the refusal would leave nothing to disagree with."""
    avid = derived["avid hotel zeeland"]
    assert avid["membrane"]["verdict"] == "REJECT_WRONG_PROPERTY"
    assert avid["founder_identity_ruling"]["ruling"] == "SAME_PROPERTY_CONFIRMED"
    assert avid["founder_identity_ruling"][
        "membrane_verdict_left_as_recorded"] == "REJECT_WRONG_PROPERTY"


# --------------------------------------------------------------------------- #
# The authority
# --------------------------------------------------------------------------- #

def test_the_authority_was_built_by_the_sanctioned_builder(authority):
    from scripts.pettripfinder import market_proposed_authority_cli as PA
    assert authority["schema"] == PA.SCHEMA == "ptf-market-proposed-authority/1.0"
    assert authority["registered"] is False
    assert authority["published"] is False
    assert authority["deployed"] is False
    assert authority["signed_rows_in"] == 50
    assert authority["unresolved"] == []


def test_the_authority_counts(authority):
    assert authority["pet_friendly_count"] == 36
    assert authority["verified_no_pets_count"] == 14
    assert authority["authority_total"] == 50


def test_the_ruled_facts_reached_the_published_facts(authority):
    """The reason a derived store exists at all."""
    rows = {r["normalized_name"]: r for r in authority["pet_friendly"]}
    assert rows["baymont"]["facts"]["pets_allowed"] is True
    assert rows["baymont"]["canonical_name"] == (
        "Baymont by Wyndham Grand Rapids Near Downtown")
    assert rows["travelodge by wyndham grand rapids north"]["facts"][
        "pets_allowed"] is True
    assert rows["tru"]["canonical_name"] == "Tru by Hilton Grand Rapids Airport"
    exclusions = {r["normalized_name"] for r in authority["verified_no_pets"]}
    assert "doubletree by hilton" in exclusions


def test_every_exclusion_carries_a_refusal_quote_and_a_false_allowance(
        authority, derived):
    for row in authority["verified_no_pets"]:
        assert row["exclusion_state"] == enums.VERIFIED_NO_PETS
        assert row["evidence_quote"].strip()
        assert derived[row["normalized_name"]]["observation"]["extraction"][
            "pets_allowed"] is False


def test_the_membrane_refusal_travels_with_avid_rather_than_being_smoothed(
        authority):
    row = next(r for r in authority["pet_friendly"]
               if r["normalized_name"] == "avid hotel zeeland")
    assert row["membrane_verdict"] == "REJECT_WRONG_PROPERTY"
    assert row["readiness_state"] == "POLICY_NOT_FOUND"
    confirmations = {c["identity_key"]
                     for c in authority["identity_confirmations"]}
    assert "avid hotel zeeland" in confirmations
    assert _load(CONFIRMATIONS)["withdrawals"] == [], (
        "nothing is withdrawn here; the channel is borrowed for the ruling")


def test_only_the_three_deferred_rows_needed_a_ruling(promotion):
    """POLICY_NEGATIVE_CONFIRMED routes itself to hotel_exclusions. Reading the
    gate off publishable_subject_to_existing_gates would have held back all 14
    exclusions for a reason the contract never gave."""
    check = promotion["validation"][
        "every_row_the_contract_defers_to_a_person_carries_a_020_ruling"]
    assert check["ok"] is True
    assert [d["identity_key"] for d in check["deferred_rows"]] == [
        "avid hotel zeeland", "baymont",
        "travelodge by wyndham grand rapids north"]
    for row in check["deferred_rows"]:
        assert row["covered_by_a_020_ruling"] is True
    assert check["uncovered"] == []
    assert set(check["routed_states_needing_no_ruling"]) == {
        "POLICY_CONFIRMED", "POLICY_CONFIRMED_WITH_AMBIGUITY",
        "POLICY_NEGATIVE_CONFIRMED"}


def test_the_holds_and_the_silent_rows_stayed_out(authority):
    keys = {r["normalized_name"] for r in
            authority["pet_friendly"] + authority["verified_no_pets"]}
    for key in ("budgetel grand rapids", "comfort inn",
                "comfort suites grandville grand rapids sw",
                "sleep inn and suites", "spark by hilton grand rapids",
                "doubletree by hilton hotel grand rapids airport",
                "drury inn and suites grand rapids", "tulyp"):
        assert key not in keys, key


def test_every_validation_check_passes(promotion):
    validation = promotion["validation"]
    for name, check in validation.items():
        if name == "all_pass":
            continue
        assert check["ok"] is True, "%s: %r" % (name, check)
    assert validation["all_pass"] is True


# --------------------------------------------------------------------------- #
# Promotion readiness
# --------------------------------------------------------------------------- #

def test_source_promotion_is_ready_and_is_not_a_registration(promotion):
    assert promotion["source_promotion_ready"] is True
    assert promotion["blockers"] == []
    assert promotion["market_is_already_registered"] is True
    assert promotion["promotion_is_a_registration"] is False
    assert promotion["clears_the_minimum"] is True
    assert promotion["authority_total"] == 50
    assert promotion["minimum_published_hotels"] == 5


def test_promotion_names_its_steps_and_what_it_did_not_do(promotion):
    steps = promotion["steps_promotion_would_take"]
    assert len(steps) == 4
    assert any("hotel_exclusions" in s["target"] for s in steps)
    assert any("build_market_authorities --check" in s["step"] for s in steps)
    check_step = next(s for s in steps
                      if "build_market_authorities" in s["step"])
    assert "--write wipes corridor assignments" in check_step["note"]
    assert promotion["not_done_here"]


def test_what_is_still_outside_the_authority(promotion):
    outside = promotion["still_outside_the_authority"]
    assert outside["policy_not_found"] == 3
    assert outside["identity_holds"] == 2
    assert outside["identity_hold_rows"] == 1
    assert outside["routing_unresolved"] == 11


def test_nothing_was_spent(ledger, promotion):
    for document in (ledger, promotion, _load(DERIVED_STORE),
                     _load(CONFIRMATIONS)):
        if "provider_calls" in document:
            assert document["provider_calls"] == 0
            assert document["usd_spent"] == 0.0


def test_no_market_authority_shard_or_census_is_written():
    import subprocess
    result = subprocess.run(
        ["git", "status", "--porcelain", "--",
         "launch_packages/pettripfinder/markets",
         "launch_packages/pettripfinder/identity_census",
         "launch_packages/pettripfinder/grand_rapids_holland_mi_observation_store_001.json"],
        cwd=str(REPO_ROOT.parent), capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "", (
        "a shard, a census or the original store changed: %r" % result.stdout)
