"""PTF-DAYTON-RECERTIFICATION-001 Pass C -- tests for the APPLIED closeout.

Pass C has been run under founder authorisation. These tests prove the applied
state is the one the founder approved, and that the applier still refuses
anything else.

The refusals matter most. This is the one module in the work order that writes a
human's name onto a record, so the behaviour worth testing is not the happy path
but what it declines: a record that moved between decision and application, a
cohort record that stopped qualifying, a decision that was not an approval. Each
must stop that record rather than sweep it in.
"""

from __future__ import annotations

import copy
import json
from collections import OrderedDict
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
#: The policy-package sha Pass C produced and its release contract pinned when
#: the market held exactly its 47 records.
PASS_C_EPOCH_SHA256 = "7cd4cf025bf371dfa89bc0d25b90527c4a75aa9b3e4bae2f95925055224d8c53"


@pytest.fixture(scope="module")
def facts():
    return json.loads(FACTS_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def ledger():
    return json.loads(LEDGER_PATH.read_text(encoding="utf-8"))


@pytest.fixture
def dry_run(monkeypatch):
    return _run_at_epoch(monkeypatch)


@pytest.fixture(scope="module")
def pass_c_records(facts):
    """The 47 records Pass C applied, identified by the ledger that authorised
    them.

    Pass C was a one-shot closeout over the market as it stood on 2026-08-16.
    PTF-DAYTON-OH-HARDENED-APPLICATION-002 has since published seven more
    records under a different authorisation, so "every record in the package"
    is no longer the same set as "every record Pass C applied". Scoping to the
    ledger keeps these assertions pointed at the work they were written to
    verify, and makes the count of 47 an assertion about the COHORT rather than
    an accident of the package's size.
    """
    return [h for h in facts["hotels"]
            if (h["approval"].get("decision_source") or {}).get("ledger")
            == "dayton_passB_founder_decisions.json"]


# --------------------------------------------------------------------------- #
# Nothing has been applied.
# --------------------------------------------------------------------------- #

def test_every_record_is_now_founder_approved(facts, pass_c_records):
    """The end state the work order named: 47 founder approvals, 0 pending."""
    assert len(pass_c_records) == 47
    for hotel in pass_c_records:
        approval = hotel["approval"]
        assert approval["decision"] == enums.APPROVED_AFTER_CURRENT_REVIEW
        assert approval["operator"] == FOUNDER
        assert approval["approval_date"] == "2026-08-16"
    # No record in the package, of any epoch, may sit pending an operator.
    pending = [h for h in facts["hotels"] if h["approval"]["decision"]
               == enums.MACHINE_REVIEWED_PENDING_OPERATOR]
    assert pending == []


def test_the_application_report_records_what_was_applied():
    report = json.loads(REPORT_PATH.read_text(encoding="utf-8"))
    assert report["status"] == "APPLIED"
    assert report["counts"]["policy_decisions_applied"] == 13
    assert report["counts"]["cohort_reattestations_applied"] == 34
    assert report["counts"]["total_applied"] == 47
    assert report["counts"]["refused"] == 0
    assert report["refused_records"] == []
    assert report["post_conditions"] == {
        "all_47_founder_approved": True,
        "zero_machine_reviewed_pending": True,
        "every_approval_binds_its_record": True,
        "supersedes_is_always_the_founders": True,
    }


def test_a_rerun_is_idempotent(facts, monkeypatch):
    """Applying twice must not double-supersede or move a hash.

    The failure this guards against is the one that has already happened twice
    in this work order: a second run burying the human approval under the
    machine block it replaced.
    """
    before = FACTS_PATH.read_bytes()
    report = _run_at_epoch(monkeypatch)
    assert report["counts"]["total_applied"] == 47
    assert report["counts"]["refused"] == 0
    assert FACTS_PATH.read_bytes() == before


# --------------------------------------------------------------------------- #
# What it would do.
# --------------------------------------------------------------------------- #

def test_each_approval_names_the_decision_that_authorised_it(pass_c_records):
    """An approval binding only hashes says a record was approved; one naming
    its decision says WHICH ruling, given when, in which ledger."""
    kinds = {POLICY: 0, COHORT: 0}
    for hotel in pass_c_records:
        source = hotel["approval"]["decision_source"]
        assert source["decided_by"] == FOUNDER
        assert source["decided_at"] == "2026-08-16"
        assert source["ledger"] == "dayton_passB_founder_decisions.json"
        kinds[source["kind"]] += 1
        if source["kind"] == POLICY:
            assert source["decision_id"].startswith("DAY-B")
        else:
            assert source["decision_id"] == \
                "APPROVE_ARTIFACT_BINDING_ONLY_REATTESTATION"
    assert kinds == {POLICY: 13, COHORT: 34}


def test_no_approval_is_stale_or_drifted(facts, pass_c_records):
    # Every record in the package must bind its own bytes, whatever applied it.
    for hotel in facts["hotels"]:
        assert hotel["approval"]["record_hash"] == record_hash(hotel)
        assert hotel["approval"]["evidence_hash"] == evidence_hash(hotel["evidence"])
    # Only Pass C's cohort carries a superseded approval to compare against.
    for hotel in pass_c_records:
        approval = hotel["approval"]
        assert approval["record_hash"] == record_hash(hotel)
        assert approval["evidence_hash"] == evidence_hash(hotel["evidence"])
        # The superseded approval described a DIFFERENT record; if it still
        # bound this one, nothing would have been re-attested.
        assert approval["supersedes"]["record_hash"] != approval["record_hash"]


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


def test_the_release_contract_pins_the_applied_bytes(dry_run):
    """Verified against the file on disk, never against the prediction."""
    import hashlib
    actual = hashlib.sha256(FACTS_PATH.read_bytes()).hexdigest()
    contract = json.loads(
        (REPO_ROOT / "deploy" / "netlify" / "release_contracts"
         / "dayton-oh.json").read_text(encoding="utf-8"))
    assert contract["policy_package"]["expected_sha256"] == actual
    # Applied and stable: re-running Pass C over its OWN epoch reproduces that
    # epoch's bytes EXACTLY -- the sha the contract pinned when Pass C closed.
    # It is not compared against current_sha256, which simply reads whatever is
    # on disk now, and the package has since grown by the seven records
    # PTF-DAYTON-OH-HARDENED-APPLICATION-002 published. The line above is what
    # holds today's contract to today's bytes; this one proves the historical
    # applier is still byte-for-byte idempotent over the market it was
    # authorised for.
    assert dry_run["release_contract"]["projected_sha256"] == PASS_C_EPOCH_SHA256
    assert b"\r\n" not in FACTS_PATH.read_bytes()


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

PASS_C_LEDGER = "dayton_passB_founder_decisions.json"


def _epoch_package(loaded):
    """The package as Pass C saw it: its own 47 records, nothing later.

    Pass C's own guard refuses to run unless its two decision lanes cover the
    market EXACTLY. That guard is correct and is deliberately left in place --
    a one-shot applier must not run against a market that has moved past the
    epoch it was authorised for, and since
    PTF-DAYTON-OH-HARDENED-APPLICATION-002 published seven more records the
    live package is no longer that market.

    So the applier is given its own epoch rather than the guard being relaxed.
    Every assertion below then tests what it was written to test: the refusal
    behaviour of a real applier over the real records it was authorised for.
    """
    loaded["hotels"] = [h for h in loaded["hotels"]
                        if (h.get("approval", {}).get("decision_source") or {})
                        .get("ledger") == PASS_C_LEDGER]
    return loaded


def _run_at_epoch(monkeypatch, mutate=None):
    import scripts.pettripfinder.dayton_pass_c_decision_application as module
    original = module.load_json

    def patched(path):
        loaded = original(path)
        if "hotel_policy_facts" in str(path):
            loaded = _epoch_package(loaded)
            if mutate is not None:
                mutate(loaded)
        return loaded

    monkeypatch.setattr(module, "load_json", patched)
    return module.run(BASELINE, apply=False)


def _tamper(monkeypatch, mutate):
    """Run the applier over a mutated in-memory package at its own epoch."""
    return _run_at_epoch(monkeypatch, mutate)


def test_the_applier_refuses_a_market_that_moved_past_its_epoch():
    """The one-shot guard, asserted directly rather than worked around.

    Run against the LIVE package -- which now carries seven records Pass C was
    never authorised over -- the applier must refuse outright.
    """
    with pytest.raises(AssertionError, match="do not cover the market exactly"):
        run(BASELINE, apply=False)


def test_a_cohort_record_that_stopped_qualifying_is_refused(monkeypatch):
    """The founder's explicit condition: STOP for that record.

    Exercised in the PRE-application posture, which is when it governs: the
    record is put back to pending, as it was before Pass C ran, and then
    tampered with. It must be refused individually and left pending -- never
    folded into a cohort it no longer belongs to.
    """
    def mutate(package):
        for hotel in package["hotels"]:
            if hotel["identity_key"] != "ac hotel dayton":
                continue
            # Put the record back to the posture Pass C runs against: the
            # agent's machine block over the founder's own prior approval.
            hotel["approval"] = OrderedDict([
                ("decision", enums.MACHINE_REVIEWED_PENDING_OPERATOR),
                ("operator", "claude-opus-5 (agent)"),
                ("approval_date", "2026-08-16"),
                ("supersedes", copy.deepcopy(
                    hotel["approval"]["supersedes"])),
                ("record_hash", hotel["approval"]["record_hash"]),
                ("evidence_hash", hotel["approval"]["evidence_hash"]),
            ])
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


def test_a_drifted_record_can_never_be_certified(monkeypatch):
    """Post-application, a record that drifts already carries an approval.

    Refusing it would leave that stale approval standing, so the run raises
    instead: there is no state in which this module reports success over a
    record whose approval no longer binds it.
    """
    def mutate(package):
        for hotel in package["hotels"]:
            if hotel["identity_key"] == "ac hotel dayton":
                hotel["facts"]["breed_restrictions"] = "SNUCK IN"

    with pytest.raises(AssertionError, match="does not bind its record"):
        _tamper(monkeypatch, mutate)


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
        if "founder_decisions" in str(path):
            return copy.deepcopy(held)
        loaded = original(path)
        # Pass C is a one-shot over its own 47 records; see _epoch_package.
        return _epoch_package(loaded) if "hotel_policy_facts" in str(path) else loaded

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

def test_no_agent_name_survives_anywhere_in_a_supersedes_chain(facts, pass_c_records):
    """Applying replaced the agent's machine block, never the human approval
    beneath it -- so every chain reads founder -> founder and no agent name is
    left where a reader checks provenance first.

    Scoped to Pass C's cohort because only those records HAVE a supersedes
    chain; a record published later never carried a machine block to replace.
    The wider invariant -- no agent name in any approval anywhere -- is asserted
    over the whole package immediately after."""
    for hotel in pass_c_records:
        approval = hotel["approval"]
        assert approval["supersedes"]["operator"] == FOUNDER
        assert "claude" not in json.dumps(approval["supersedes"]).lower()
    for hotel in facts["hotels"]:
        assert hotel["approval"]["operator"] == FOUNDER, hotel["key"]
        assert "claude" not in json.dumps(
            hotel["approval"].get("supersedes") or {}).lower(), hotel["key"]


def test_founder_prior_finds_the_last_human_approval(facts):
    hotel = facts["hotels"][0]
    prior = _founder_prior(hotel["approval"])
    assert prior["operator"] == FOUNDER
    assert prior["decision"] == enums.APPROVED_AFTER_CURRENT_REVIEW


def test_founder_prior_refuses_a_chain_with_no_human_in_it():
    with pytest.raises(AssertionError, match="no founder approval"):
        _founder_prior({"operator": "claude-opus-5 (agent)",
                        "supersedes": {"operator": "claude-opus-5 (agent)"}})
