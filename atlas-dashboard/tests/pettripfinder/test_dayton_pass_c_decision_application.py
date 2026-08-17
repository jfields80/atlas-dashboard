"""PTF-DAYTON-RECERTIFICATION-001 Pass C -- tests for the PREPARED applier.

Pass C has not been run. These tests therefore prove two different things: that
nothing has been applied, and that the applier -- when it is authorised -- would
do exactly what the founder approved and refuse anything else.

The second half matters most. An applier is the one module in this work order
that writes a human's name onto a record, so the behaviour worth testing is not
the happy path but the refusals: a record that moved between decision and
application, a cohort record that stopped qualifying, a decision that was not an
approval. Each must stop that record rather than sweep it in.
"""

from __future__ import annotations

import copy
import json
from pathlib import Path

import pytest

from scripts.pettripfinder.contracts import enums
from scripts.pettripfinder.dayton_pass_c_decision_application import (
    COHORT, FOUNDER, POLICY, _founder_prior, approve, run,
)
from scripts.pettripfinder.policy_migration import evidence_hash, record_hash

REPO_ROOT = Path(__file__).resolve().parents[2]
LP = REPO_ROOT / "launch_packages" / "pettripfinder"
FACTS_PATH = LP / "hotel_policy_facts_dayton-oh.json"
LEDGER_PATH = LP / "dayton_passB_founder_decisions.json"
REPORT_PATH = LP / "dayton_passC_application_report.json"
BASELINE = "d14cdc4"


@pytest.fixture(scope="module")
def facts():
    return json.loads(FACTS_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def ledger():
    return json.loads(LEDGER_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def dry_run():
    return run(BASELINE, apply=False)


# --------------------------------------------------------------------------- #
# Nothing has been applied.
# --------------------------------------------------------------------------- #

def test_pass_c_has_not_been_run(facts):
    assert not REPORT_PATH.exists()
    for hotel in facts["hotels"]:
        approval = hotel["approval"]
        assert approval["decision"] == enums.MACHINE_REVIEWED_PENDING_OPERATOR
        assert approval["operator"] != FOUNDER


def test_the_dry_run_writes_nothing(facts):
    before = FACTS_PATH.read_bytes()
    report = run(BASELINE, apply=False)
    assert report["status"] == "PREPARED_NOT_APPLIED"
    assert report["release_contract"]["repinned"] is False
    assert FACTS_PATH.read_bytes() == before
    assert not REPORT_PATH.exists()


# --------------------------------------------------------------------------- #
# What it would do.
# --------------------------------------------------------------------------- #

def test_it_would_apply_exactly_the_two_lanes(dry_run):
    counts = dry_run["counts"]
    assert counts["policy_decisions_applied"] == 13
    assert counts["cohort_reattestations_applied"] == 34
    assert counts["total_applied"] == 47
    assert counts["refused"] == 0


def test_it_would_reach_the_end_state_the_work_order_names(dry_run):
    assert dry_run["post_conditions"] == {
        "all_47_founder_approved": True,
        "zero_machine_reviewed_pending": True,
        "every_approval_binds_its_record": True,
        "supersedes_is_always_the_founders": True,
    }
    assert dry_run["counts"]["founder_bound_after_application"] == 47
    assert dry_run["counts"]["still_pending_operator"] == 0


def test_it_would_repin_the_release_contract(dry_run):
    contract = dry_run["release_contract"]
    assert contract["current_sha256"] != contract["projected_sha256"]
    assert len(contract["projected_sha256"]) == 64


def test_the_two_lanes_partition_the_market(dry_run, ledger):
    policy = {r["identity_key"] for r in dry_run["applied_records"]
              if r["lane"] == POLICY}
    cohort = {r["identity_key"] for r in dry_run["applied_records"]
              if r["lane"] == COHORT}
    assert len(policy) == 13 and len(cohort) == 34
    assert policy & cohort == set()
    assert policy == {r["identity_key"] for r in ledger["decisions"]}
    assert cohort == {r["identity_key"] for r in
                      ledger["artifact_only_cohort_decision"]["records"]}


# --------------------------------------------------------------------------- #
# Refusals -- the half that matters.
# --------------------------------------------------------------------------- #

def _tamper(monkeypatch, mutate):
    """Run the applier over a mutated in-memory package."""
    import scripts.pettripfinder.dayton_pass_c_decision_application as module
    original = module.load_json

    def patched(path):
        loaded = original(path)
        if "hotel_policy_facts" in str(path):
            mutate(loaded)
        return loaded

    monkeypatch.setattr(module, "load_json", patched)
    return module.run(BASELINE, apply=False)


def test_a_cohort_record_that_stopped_qualifying_is_refused(monkeypatch):
    """The founder's explicit condition: STOP for that record, never sweep it
    into a cohort it no longer belongs to."""
    def mutate(package):
        for hotel in package["hotels"]:
            if hotel["identity_key"] == "ac hotel dayton":
                hotel["facts"]["breed_restrictions"] = "SNUCK IN"

    report = _tamper(monkeypatch, mutate)
    refused = {r["identity_key"]: r for r in report["refused_records"]}
    assert "ac hotel dayton" in refused
    assert refused["ac hotel dayton"]["lane"] == COHORT
    assert "facts changed" in refused["ac hotel dayton"]["failures"]
    # Refused individually, not fatally -- the other 46 still apply.
    assert report["counts"]["total_applied"] == 46
    assert report["counts"]["refused"] == 1
    # ...and the end state is reported honestly rather than claimed.
    assert report["post_conditions"]["all_47_founder_approved"] is False
    assert report["post_conditions"]["zero_machine_reviewed_pending"] is False


def test_a_record_that_moved_since_the_decision_stops_the_run(monkeypatch):
    """A policy decision names hashes. If the record no longer matches them,
    the approval would be about something the founder never saw."""
    def mutate(package):
        for hotel in package["hotels"]:
            if hotel["identity_key"] == "staybridge suites miamisburg":
                hotel["facts"]["pet_count_limit"] = 9

    with pytest.raises(AssertionError, match="moved between decision and"):
        _tamper(monkeypatch, mutate)


def test_a_non_approval_decision_is_never_applied(facts, ledger):
    """Only APPROVE_CORRECTED_RECORD writes an approval; a HOLD must not."""
    import scripts.pettripfinder.dayton_pass_c_decision_application as module
    held = copy.deepcopy(ledger)
    held["decisions"][0]["founder_decision"] = "HOLD"
    original = module.load_json

    def patched(path):
        return copy.deepcopy(held) if "founder_decisions" in str(path) \
            else original(path)

    module.load_json = patched
    try:
        report = module.run(BASELINE, apply=False)
    finally:
        module.load_json = original
    refused = {r["identity_key"]: r for r in report["refused_records"]}
    assert ledger["decisions"][0]["identity_key"] in refused
    assert report["counts"]["total_applied"] == 46


# --------------------------------------------------------------------------- #
# The supersedes chain.
# --------------------------------------------------------------------------- #

def test_the_preserved_prior_is_always_the_founders(facts, ledger):
    """Applying replaces the agent's machine block, never the human approval
    beneath it -- so the chain reads founder -> founder and no agent name is
    left where a reader checks provenance first."""
    rows = {r["identity_key"]: r for r in ledger["decisions"]}
    for hotel in facts["hotels"]:
        if hotel["identity_key"] not in rows:
            continue
        record = copy.deepcopy(hotel)
        approval = approve(record, POLICY, rows[hotel["identity_key"]])
        assert approval["decision"] == enums.APPROVED_AFTER_CURRENT_REVIEW
        assert approval["operator"] == FOUNDER
        assert approval["supersedes"]["operator"] == FOUNDER
        assert "claude" not in json.dumps(approval["supersedes"]).lower()
        # The approval binds the record it signs.
        assert approval["record_hash"] == record_hash(record)
        assert approval["evidence_hash"] == evidence_hash(record["evidence"])


def test_founder_prior_walks_past_the_machine_block(facts):
    hotel = facts["hotels"][0]
    prior = _founder_prior(hotel["approval"])
    assert prior["operator"] == FOUNDER
    assert prior["decision"] == enums.APPROVED_AFTER_CURRENT_REVIEW


def test_founder_prior_refuses_a_chain_with_no_human_in_it():
    with pytest.raises(AssertionError, match="no founder approval"):
        _founder_prior({"operator": "claude-opus-5 (agent)",
                        "supersedes": {"operator": "claude-opus-5 (agent)"}})
