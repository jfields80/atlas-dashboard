"""PTF-MILWAUKEE-IDENTITY-RESOLUTION-AND-FULL-CLOSURE-038 -- closure invariants.

These are not tests of a report's contents. They are the arithmetic and the
governance rules the closure rests on, pinned so a later work order that breaks
one fails here rather than in a market that quietly stops adding up.
"""

from __future__ import annotations

import json
import sys
from collections import Counter
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts.pettripfinder import market_authority as MA
from scripts.pettripfinder.acquisition import authority_build_036 as A36
from scripts.pettripfinder.acquisition import closure_038 as C38
from scripts.pettripfinder.acquisition import founder_decisions_036 as D36
from scripts.pettripfinder.acquisition import identity_resolution_038 as I38


@pytest.fixture(autouse=True)
def _fresh_derivation():
    """The derivation is memoised for speed, and sibling suites write authority
    files to disk while they run. A cached row set outlives that, so every test
    here re-derives from whatever is on disk right now."""
    for cached in (C38.capture_attempts, C38.best_replay, C38.active_rows,
                   C38.non_active_rows):
        cached.cache_clear()
    yield
    for cached in (C38.capture_attempts, C38.best_replay, C38.active_rows,
                   C38.non_active_rows):
        cached.cache_clear()


@pytest.fixture
def rows():
    return C38.active_rows()


@pytest.fixture
def ledger():
    return json.loads(C38.LEDGER.read_text(encoding="utf-8"))


# --- A. every property, exactly once ---------------------------------------- #

def test_every_active_eligible_property_has_exactly_one_disposition(rows):
    keys = [row["identity_key"] for row in rows]
    assert len(keys) == 133
    assert len(set(keys)) == 133


def test_no_row_carries_a_disposition_outside_the_contract(rows):
    assert {row["disposition"] for row in rows} <= set(C38.DISPOSITIONS)


def test_the_dispositions_sum_to_the_active_universe(rows):
    assert sum(Counter(row["disposition"] for row in rows).values()) == 133


# --- B. the whole census reconciles ----------------------------------------- #

def test_the_census_reconciles_with_no_unnamed_remainder():
    recon = C38.reconciliation()
    assert recon["problems"] == []
    assert recon["active_eligible"] + recon["non_active_eligible"] == 147
    assert recon["census_total"] == 147


def test_no_identity_is_both_active_and_not(rows):
    assert not ({row["identity_key"] for row in rows}
                & {row["identity_key"] for row in C38.non_active_rows()})


# --- C. authority is frozen -------------------------------------------------- #

def test_authority_counts_are_exactly_what_the_founders_approved(rows):
    """Derived from the decisions across every sitting, not pinned to 038's
    moment: a later founder is entitled to approve more, and what must hold is
    that the closure's authority buckets equal what was actually approved."""
    from scripts.pettripfinder.acquisition import publication_037 as P37
    counts = Counter(row["disposition"] for row in rows)
    assert counts[C38.AUTHORITY_PET_FRIENDLY] == len(P37.approved_identities())
    assert counts[C38.AUTHORITY_VERIFIED_NO_PETS] == len(
        P37.approved_refusals())


def test_every_authority_row_names_a_founder_approval(rows):
    for row in rows:
        if row["disposition"].startswith("AUTHORITY_"):
            assert row["founder_review_status"] == "APPROVED_BY_FOUNDER"


def test_the_closure_admitted_nobody_to_authority():
    """038 classified; it approved nothing. Asserted by name rather than by
    count, so a later founder's approvals do not read as 038's."""
    doc = json.loads(A36.AUTHORITY.read_text(encoding="utf-8"))
    for record in doc["hotels"]:
        assert record["approval"]["decision_source"]["work_order"] !=             C38.WORK_ORDER
    for row in MA.load_market_exclusions(C38.MARKET):
        assert (row.get("decision_source") or {}).get(
            "work_order") != C38.WORK_ORDER


def test_every_currently_held_property_is_outside_authority(rows):
    """A hold is only a hold until the founder lifts it. 036 held Saint Kate
    and 040 approved it, so the durable claim is about whatever is held NOW --
    pinning 036's pair would have failed the moment a founder answered."""
    from scripts.pettripfinder.acquisition import publication_037 as P37
    held = set(P37.held_identities())
    assert held
    for row in rows:
        if row["identity_key"] in held:
            assert row["authority_status"] == "NONE"
            assert row["disposition"] == C38.HELD_REVIEW


# --- D. nothing recovered here became authority ------------------------------ #

def test_every_new_candidate_is_awaiting_a_decision():
    for row in C38.new_candidates():
        assert row["status"] == "AWAITING_FOUNDER_DECISION"
        assert row["founder_approved"] is False


def test_no_new_candidate_is_in_authority():
    doc = json.loads(A36.AUTHORITY.read_text(encoding="utf-8"))
    published = {record["identity_key"] for record in doc["hotels"]}
    assert not ({row["identity_key"] for row in C38.new_candidates()}
                & published)


def test_a_candidate_from_a_non_production_run_says_so():
    """025 excludes decision-test captures from the store on purpose. Evidence
    taken from one may be shown to a founder; it may never be shown as though
    a production run had produced it."""
    for row in C38.new_candidates():
        if row["run_kind"] != C38.S25.CURRENT_PRODUCTION:
            assert row["run_kind"] in row["acquisition_lineage"]


# --- E. the reader may not turn a price into a permission -------------------- #

def test_a_candidate_reading_states_whether_pets_are_allowed():
    """A page that prices a pet policy without granting one is exactly what the
    founder held two rows over. Re-offering it would ask the same question
    twice and invite an inference nobody made."""
    for row in C38.new_candidates():
        if row["reader_reading_trustworthy"]:
            assert "pets_allowed" in row["proposed_facts"]


def test_hyatt_regency_remains_held_on_the_same_ground(rows):
    row = next(r for r in rows if r["identity_key"] == "hyatt regency milwaukee")
    assert row["disposition"] == C38.HELD_REVIEW
    assert row["founder_review_status"] == "HELD_BY_FOUNDER"
    assert row["identity_key"] not in {c["identity_key"]
                                       for c in C38.new_candidates()}


# --- F. a self-contradictory source settles nothing -------------------------- #

def test_a_source_that_contradicts_itself_is_not_a_candidate(rows):
    conflicted = [r for r in rows if r["disposition"] == C38.SOURCE_CONFLICT]
    assert conflicted
    for row in conflicted:
        assert "038 candidate" not in row["founder_review_status"]
        assert row["authority_status"] == "NONE"


# --- G. a declined capture stays declined ------------------------------------ #

def test_a_declined_capture_carries_no_proposed_facts():
    """The router refused to bind the page to the property. A founder may still
    read the quote; nothing downstream may read a parse of it as facts."""
    from scripts.pettripfinder.acquisition import founder_review_039 as V39
    # Read from the committed review package: live state no longer offers
    # these as candidates because 040 decided them, and what 038 produced is
    # what this test is about.
    declined = [row for row in V39.rows()
                if row["identity_status"] != "CONFIRMED"]
    assert declined
    for row in declined:
        assert row["proposed_publication_facts"] == {}
        assert row["parse_is_trustworthy"] is False
        assert row["evidence_quote"]


def test_the_identity_gate_was_not_weakened():
    for row in C38.new_candidates():
        if not row["identity_confirmed"]:
            assert row["identity_key"] not in {
                r["identity_key"] for r in C38.active_rows()
                if r["disposition"].startswith("AUTHORITY_")}


# --- H. every row explains itself -------------------------------------------- #

def test_every_row_states_a_reason(rows):
    for row in rows:
        assert row["reason"].strip(), row["identity_key"]


def test_other_requires_explanation_is_never_used_bare(rows):
    for row in rows:
        if row["disposition"] == C38.OTHER:
            assert len(row["reason"]) > 40


def test_every_non_authority_row_carries_a_recovery_class(rows):
    for row in rows:
        if not row["disposition"].startswith("AUTHORITY_"):
            assert row["recovery_class"], row["identity_key"]


# --- I. the market is not published ------------------------------------------ #

def test_the_closure_publishes_nothing(ledger):
    assert ledger["published"] == 0
    assert ledger["deployed"] == 0


def test_the_market_policy_package_is_still_unpublished():
    doc = json.loads(A36.AUTHORITY.read_text(encoding="utf-8"))
    assert doc["published"] is False


# --- J. the identity resolution the founder signed --------------------------- #

def test_the_shared_address_pair_is_resolved_as_two_properties():
    doc = json.loads(I38.RESOLUTIONS.read_text(encoding="utf-8"))
    match = [row for row in doc["resolutions"]
             if row["resolution_id"] == I38.RESOLUTION_ID]
    assert len(match) == 1
    assert match[0]["reviewer_id"] == I38.FOUNDER
    assert match[0]["distinct_reason"].strip()


def test_both_hilton_identities_survive_deduplication():
    """The blocker 037 hit: two hotels at 515 N Jefferson St collapsing into
    one listing. Both must reach the site, or neither claim is true."""
    for key in I38.PAIR:
        assert key in {row["identity_key"] for row in C38.active_rows()}


# --- the ledger on disk is the one this module derives ----------------------- #

def test_the_committed_ledger_matches_the_derivation(ledger):
    assert ledger["reconciliation"] == C38.reconciliation()
    assert (len(ledger["active_eligible"]) ==
            ledger["reconciliation"]["active_eligible"])
