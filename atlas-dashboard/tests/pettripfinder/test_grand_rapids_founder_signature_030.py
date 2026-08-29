# -*- coding: utf-8 -*-
"""PTF-GRAND-RAPIDS-FOUNDER-SIGNATURE-PASS-030 -- fourteen signed, eleven promoted.

THE HEADLINE IS A SHORTFALL AND THE TESTS PIN IT. Fourteen records were signed
cleanly and the market promotes to 40 pet-friendly, not 43. Three
founder-approved rows are held out of PUBLICATION because the schema requires
``fee_cap.qualifier_stated`` and never infers it. Their signatures stand. A
later pass that reports 43 without a ruling on those caps would be claiming
something this promotion does not say.

THE RECONCILED ROW IS THE INTERESTING ONE. Its capture was declined at the
identity gate, which runs BEFORE the locator, so no block was ever cut. 029
settled the identity; this pass RE-LOCATED the block from the same bytes into a
NEW directory and fed it through the COMMITTED store builder with the ruling
supplied as a founder identity override. The declined capture is untouched, and
a test proves it -- it is the record of what the gate saw.

TWO RULINGS, NOT ONE. That row carries an explicit SAME_PROPERTY_CONFIRMED
identity ruling AND a record-level approval, in separate fields, because
identity confirmation is not policy approval.

AND PUBLISHING WITHDRAWS THE ROUTES IT ANSWERS. The first version of this
promotion did not, and left a stale pointer beside every newly published seed
row; the committed invariant caught it. Both halves are tested: the routes fell
79 -> 75, and no route survives for a hotel this market now publishes.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.pettripfinder import grand_rapids_holland_founder_signature_030 as S  # noqa: E402

LP = REPO_ROOT / "launch_packages" / "pettripfinder"
LEDGER = LP / "grand_rapids_holland_mi_founder_decision_ledger_030.json"
AUTHORITY = LP / "grand_rapids_holland_mi_proposed_authority_030.json"
HOLDS = LP / "grand_rapids_holland_mi_publication_holds_030.json"
PROMOTION = LP / "grand_rapids_holland_mi_source_promotion_030.json"
PACKAGE = LP / "hotel_policy_facts_grand-rapids-holland-mi.json"
STORE_030 = LP / "grand_rapids_holland_mi_observation_store_030.json"
OVERRIDES = LP / "grand_rapids_holland_mi_founder_overrides_030.json"


def _load(path):
    assert path.is_file(), "%s is missing" % path.name
    return json.loads(path.read_text(encoding="utf-8-sig"))


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
def package():
    return _load(PACKAGE)


# --------------------------------------------------------------------------- #
# The signature pass
# --------------------------------------------------------------------------- #

def test_fourteen_presented_fourteen_signed_none_stale(ledger):
    counts = ledger["counts"]
    assert counts["candidates_presented"] == 14
    assert counts["signatures_written"] == 14
    assert counts["signatures_refused"] == 0
    assert counts["signed_pet_friendly"] == 8
    assert counts["signed_verified_no_pets"] == 6


def test_every_signature_binds_a_semantic_hash(ledger):
    assert ledger["every_signature_binds_a_hash"] is True
    assert ledger["binding_contract"] == "semantic-approval/1.0"
    for row in ledger["signed"]:
        assert row["bound_semantic_hash"]
        assert row["bound_snapshot_hash"]
        assert row["founder_decision"] == "APPROVED_AFTER_CURRENT_REVIEW"
        assert row["founder_reviewer_id"] == "PTF-FOUNDER-001"
        assert row["founder_reviewed_at"] == "2026-08-29"


def test_no_unresolved_row_entered_the_approved_set(ledger):
    assert ledger["no_unresolved_row_signed"] is True
    for row in ledger["signed"]:
        assert row["readiness"] in S.SIGNABLE_STATES
        assert row["membrane"] == "VALID"
        assert row["publication_grade"] == "PUBLICATION_GRADE_CONFIRMED"
        assert row["classification"] in ("PET_FRIENDLY", "VERIFIED_NO_PETS")


def test_a_row_that_defers_to_a_person_is_refused_not_signed():
    """POLICY_NOT_FOUND and POLICY_PARTIAL never route themselves, so they can
    never be signed as records however the rest of the row looks."""
    census = {"x": {"corridor": ""}}
    for state in ("POLICY_NOT_FOUND", "POLICY_PARTIAL"):
        rows = S.sign(
            [{"identity_key": "x", "canonical_name": "X",
              "classification": "PET_FRIENDLY"}],
            {"x": {"readiness": {"state": state}, "membrane": {"verdict": "VALID"}}},
            census, {}, {})
        assert rows[0]["outcome"] == S.REFUSED_READINESS
        assert rows[0]["founder_decision"] == ""
        assert rows[0]["founder_reviewer_id"] == ""


def test_a_row_with_no_record_cannot_be_signed():
    rows = S.sign([{"identity_key": "ghost", "canonical_name": "Ghost",
                    "classification": "PET_FRIENDLY"}],
                  {}, {"ghost": {}}, {}, {})
    assert rows[0]["outcome"] == S.REFUSED_HASH_UNREPRODUCIBLE
    assert rows[0]["founder_decision"] == ""


def test_the_reconciled_row_carries_two_rulings(ledger):
    """Identity confirmation is not policy approval and one field cannot say
    both, so they are recorded separately."""
    assert ledger["identity_rulings_recorded"] == ["comfort inn airport"]
    row = next(r for r in ledger["signed"]
               if r["identity_key"] == "comfort inn airport")
    ruling = row["identity_ruling"]
    assert ruling["verdict"] == "SAME_PROPERTY_CONFIRMED"
    assert ruling["ruled_by"] == "PTF-FOUNDER-001"
    assert ruling["non_telephone_signals"] >= 1
    assert "does not agree with expected" in ruling["gate_declined_because"]
    assert "would publish a record on evidence the gate refused" in \
        ruling["why_it_needs_its_own_ruling"]
    # And the record-level approval is its own, separate field.
    assert row["founder_decision"] == "APPROVED_AFTER_CURRENT_REVIEW"


# --------------------------------------------------------------------------- #
# The re-located capture
# --------------------------------------------------------------------------- #

def test_the_declined_capture_was_not_touched():
    """It is the record of what the gate saw. The re-located capture is a new
    directory and both stay on disk so the two can be compared."""
    declined = REPO_ROOT / "data" / "acquisition" / "gr_028" / \
        "comfort-inn-airport" / "declined-01"
    relocated = REPO_ROOT / "data" / "acquisition" / "gr_030_relocated" / \
        "comfort-inn-airport" / "attempt-01"
    assert (declined / "declined.json").is_file()
    assert (declined / "rendered.html").is_file()
    assert not (declined / "policy-block.txt").exists(), (
        "the gate declined before the locator ran; a block here would mean the "
        "declined capture had been edited")
    assert (relocated / "policy-block.txt").is_file()
    assert (relocated / "locator.json").is_file()


def test_the_relocated_block_says_where_it_came_from():
    locator = _load(REPO_ROOT / "data" / "acquisition" / "gr_030_relocated" /
                    "comfort-inn-airport" / "attempt-01" / "locator.json")
    assert locator["relocated_by"] == S.WORK_ORDER
    assert "gr_028" in locator["relocated_from"]
    assert "before the locator" in locator["why"]
    assert locator["block_sha256"]


def test_the_reconciled_record_went_through_the_committed_builder():
    store = _load(STORE_030)
    record = (store.get("records") or store.get("observations"))[0]
    assert record["identity_key"] == "comfort inn airport"
    assert record["readiness"]["state"] == "POLICY_CONFIRMED"
    assert record["membrane"]["verdict"] == "VALID"
    assert record["publication_grade"]["verdict"] == "PUBLICATION_GRADE_CONFIRMED"
    assert record["observation"]["extraction"]["pets_allowed"] is True


def test_the_identity_ruling_reached_the_builder_as_an_override():
    overrides = _load(OVERRIDES)
    assert overrides["decided_by"] == "PTF-FOUNDER-001"
    block = overrides["identity_overrides"]
    assert "SAME_PROPERTY_CONFIRMED" in block["founder_ruling"]
    assert block["records"][0]["identity_key"] == "comfort inn airport"


# --------------------------------------------------------------------------- #
# What publication would not take
# --------------------------------------------------------------------------- #

def test_three_signed_rows_are_held_out_of_publication():
    holds = _load(HOLDS)
    assert holds["count"] == 3
    assert {r["identity_key"] for r in holds["held"]} == {
        "holiday inn grand rapids downtown",
        "red roof inn grand rapids airport",
        "wyndham garden grand rapids airport"}
    for row in holds["held"]:
        assert row["signature_still_stands"] is True
        assert any("qualifier_stated" in issue for issue in row["issues"])
        assert row["source_quotes_for_the_cap"], (
            "the quotes are carried because they settle the ruling quickly")
        assert "decision 3" in row["what_would_settle_it"]
        assert "--cap-qualifier-stated" in row["what_would_settle_it"]


def test_a_hold_is_not_a_failed_signature(ledger):
    holds = {r["identity_key"] for r in _load(HOLDS)["held"]}
    signed = {r["identity_key"] for r in ledger["signed"]}
    assert holds <= signed, (
        "these rows ARE signed; what waits is their publication")


def test_the_refusal_parser_cannot_report_zero_by_accident():
    """It scanned for the first "[" and hit one in the traceback, swallowed the
    parse error and reported ZERO refusals -- which looked exactly like a clean
    projection and would have promoted three rows the schema refuses."""
    traceback = ('Traceback (most recent call last):\n  File "x.py", '
                 'line 1, in <module>\n    parents[2]\nPolicyPackageError: '
                 'boom')
    with pytest.raises(SystemExit):
        S.schema_refusals(traceback)
    good = ('PolicyPackageError: 1 record(s) failed schema 1.2 validation and '
            'the package was NOT written: [{"identity_key": "a", '
            '"issues": ["x"]}]')
    assert S.schema_refusals(good) == [{"identity_key": "a", "issues": ["x"]}]
    assert S.schema_refusals("everything was fine") == []


# --------------------------------------------------------------------------- #
# The promotion
# --------------------------------------------------------------------------- #

def test_the_market_promotes_to_forty_not_forty_three(authority, package,
                                                      promotion):
    assert authority["pet_friendly_count"] == 40
    assert authority["verified_no_pets_count"] == 20
    assert authority["authority_total"] == 60
    assert package["count"] == 40
    assert promotion["signed_authority"] == {"pet_friendly": 43,
                                             "verified_no_pets": 20,
                                             "total": 63}
    assert promotion["promoted"]["pet_friendly"] == 40


def test_every_published_row_carries_a_founder_signature(package):
    for row in package["hotels"]:
        assert row["founder_decision"] == "APPROVED_AFTER_CURRENT_REVIEW"
        assert row["founder_reviewer_id"] == "PTF-FOUNDER-001"
        assert row["founder_reviewed_at"]


def test_no_duplicate_identity_or_display_key(package):
    from collections import Counter
    keys = [row["identity_key"] for row in package["hotels"]]
    assert [k for k, c in Counter(keys).items() if c > 1] == []
    display = [row["key"] for row in package["hotels"]]
    assert [k for k, c in Counter(display).items() if c > 1] == []


def test_publishing_withdrew_the_routes_it_answered(promotion):
    """The first version of this promotion did not, and left a stale pointer
    beside every newly published seed row."""
    withdrawal = promotion["routes_withdrawn_by_publication"]
    assert withdrawal["routes_before"] == 79
    assert withdrawal["routes_after"] == 75
    assert withdrawal["withdrawn"] == 4
    assert withdrawal["routes_for_a_published_identity_in_the_end_state"] == 0
    assert "ROUTING_RETIRED" in withdrawal["not_retired_because"]


def test_the_promotion_preserved_what_it_must(promotion):
    preserved = promotion["preserved"]
    assert preserved["pinned_census"] == 163
    assert preserved["other_market_shards_changed"] == []
    assert "check mode" in preserved["build_market_authorities"]
    assert "--write" in preserved["build_market_authorities"]


def test_the_release_contract_agrees_with_the_authority():
    from scripts.pettripfinder import release_contracts as RC
    assert RC.verify_contract("grand-rapids-holland-mi") == []
    derived = RC.derive_authority("grand-rapids-holland-mi")
    assert derived.published_hotel_profiles == 40
    assert derived.verified_no_pets == 20
    assert derived.resolved == 60
    assert derived.confirmed_identities == 163


def test_nothing_was_spent(ledger, promotion):
    assert ledger["provider_calls"] == 0 and ledger["usd_spent"] == 0.0
    assert promotion["provider_calls"] == 0 and promotion["usd_spent"] == 0.0
    discovery = _load(LP / "ptf_discovery_attempt_ledger_001.json")
    assert len([a for a in discovery["attempts"]
                if a["market_id"] == "grand-rapids-holland-mi"]) == 40
    paid = _load(LP / "ptf_paid_attempt_ledger_001.json")
    assert len([a for a in paid["attempts"]
                if a["market_id"] == "grand-rapids-holland-mi"]) == 89
