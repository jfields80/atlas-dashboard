"""PTF-...-FOUNDER-REVIEW-AND-APPROVAL-BINDING-039 -- what an approval is about.

The corrected binding is only worth having if it is strictly narrower in one
direction and not at all in the other: implementation provenance must stop
withdrawing approvals, and every approved fact must still withdraw one. Both
halves are asserted here, field by field, because "we made the hash smaller"
is exactly the change that quietly becomes "we made tampering undetectable".
"""

from __future__ import annotations

import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts.pettripfinder import approval_binding as AB
from scripts.pettripfinder.acquisition import approval_rebinding_039 as R39
from scripts.pettripfinder.acquisition import authority_build_036 as A36
from scripts.pettripfinder.acquisition import founder_decisions_036 as D36
from scripts.pettripfinder.acquisition import founder_review_036 as F36
from scripts.pettripfinder.acquisition import founder_review_039 as V39
from scripts.pettripfinder.policy_migration import record_hash


#: The files 039 changed, located from the repository rather than pinned to a
#: sha nobody can know while writing the test. Before the work order is
#: committed this is the working set, which answers the same question; after,
#: it is the commit that introduced the binding contract. Either way it is
#: "what did 039 touch", and never "whatever HEAD happens to be".
def files_changed_by_this_work_order():
    contract = ("atlas-dashboard/scripts/pettripfinder/approval_binding.py")
    commit = subprocess.run(
        ["git", "log", "--diff-filter=A", "--format=%H", "--", contract],
        cwd=str(REPO.parent), capture_output=True, text=True).stdout.split()
    if commit:
        return subprocess.run(
            ["git", "show", "--name-only", "--format=", commit[-1]],
            cwd=str(REPO.parent), capture_output=True, text=True).stdout.split()
    porcelain = subprocess.run(
        ["git", "status", "--porcelain"],
        cwd=str(REPO.parent), capture_output=True, text=True).stdout.splitlines()
    return [line[3:].strip().strip('"') for line in porcelain if line[3:].strip()]


@pytest.fixture(scope="module")
def store():
    return R39.store_rows()


@pytest.fixture(scope="module")
def row(store):
    return copy.deepcopy(store["avid hotels milwaukee west waukesha"])


@pytest.fixture(scope="module")
def rebinding():
    return json.loads(R39.REBINDING.read_text(encoding="utf-8"))


# --------------------------------------------------------------------------- #
# The six.
# --------------------------------------------------------------------------- #

EXPECTED_SIX = [
    "Country Inn & Suites by Radisson, Brown Deer - Milwaukee North",
    "Country Inn & Suites by Radisson, Milwaukee West (Brookfield), WI",
    "Econo Lodge Milwaukee Airport",
    "Knickerbocker on the Lake",
    "Saint Kate - The Arts Hotel",
    "The Iron Horse Hotel",
]


def test_exactly_the_six_038_candidates_are_surfaced():
    rows = V39.assert_cohort()
    assert [row["property_name"] for row in rows] == EXPECTED_SIX


def test_no_already_decided_row_is_in_the_package():
    decided = {d["identity_key"] for d in F36.load_ledger()["decisions"]
               if d["decision"] != D36.HOLD}
    assert not {row["identity_key"] for row in V39.rows()} & decided


def test_every_candidate_is_unanswered_and_advisory():
    for row in V39.rows():
        assert row["status"] == "AWAITING_FOUNDER_DECISION"
        assert row["founder_decision"] == "<UNANSWERED>"
        assert row["verdict_is_advisory_only"] is True
        assert row["recommended_machine_verdict"] in (
            V39.APPROVE, V39.APPROVE_REFUSAL, V39.HOLD)


def test_every_candidate_shows_its_quote_and_its_lineage():
    for row in V39.rows():
        assert row["evidence_quote"].strip(), row["property_name"]
        assert row["provider_lineage"].strip()
        assert row["evidence_origin"] in (V39.FROM_PERSISTED,
                                          V39.FROM_REACQUISITION)
        assert row["source_url"].startswith("http")


def test_039_put_nothing_from_the_package_into_authority():
    """039 asked; it did not answer. Where a candidate is in authority today
    it is because PTF-MILWAUKEE-FOUNDER-DECISION-040 approved it, and the
    record says so -- which is the check, rather than "no candidate is ever
    admitted"."""
    authority = json.loads(A36.AUTHORITY.read_text(encoding="utf-8"))
    keys = {row["identity_key"] for row in V39.rows()}
    for record in authority["hotels"]:
        if record["identity_key"] in keys:
            source = record["approval"]["decision_source"]
            assert source["work_order"] != V39.WORK_ORDER
            assert source["review_work_order"] == V39.WORK_ORDER


def test_the_package_cost_nothing():
    assert V39.document()["provider_calls_in_039"] == 0


# --------------------------------------------------------------------------- #
# Provenance must not invalidate.
# --------------------------------------------------------------------------- #

PROVENANCE_EDITS = [
    ("rederivation.reader_commit", "deadbeef" * 5),
    ("rederivation.derivation", "a different explanation of the same thing"),
    ("rederivation.evidence_block_path", "data/somewhere/else/policy-block.txt"),
    ("rederivation.superseded_by", "PTF-SOMETHING-LATER"),
    ("provenance.retrieved_at", "2030-01-01T00:00:00+00:00"),
    ("provenance.capture_method", "carrier_pigeon"),
    ("provenance.provider", "some_other_provider"),
    ("provenance.reader", "some_other_reader"),
    ("provenance.raw_pointer", "D:/elsewhere"),
    ("provenance.obs_id", "run::slug::attempt-99"),
    ("source_run", "a-different-run"),
    ("published", True),
    ("founder_approved", True),
]


def _edit(record, path, value):
    out = copy.deepcopy(record)
    target = out
    parts = path.split(".")
    for part in parts[:-1]:
        target = target[part]
    target[parts[-1]] = value
    return out


@pytest.mark.parametrize("path,value", PROVENANCE_EDITS)
def test_provenance_changes_do_not_invalidate_an_approval(row, path, value):
    changed = _edit(row, path, value)
    assert AB.semantic_hash(changed) == AB.semantic_hash(row), path
    # And the old binding really would have broken on the same edit, which is
    # the whole reason this contract exists.
    assert record_hash(changed) != record_hash(row), path


def test_reordering_the_evidence_array_is_not_a_change(row):
    shuffled = copy.deepcopy(row)
    shuffled["evidence"] = list(reversed(shuffled["evidence"]))
    assert AB.semantic_hash(shuffled) == AB.semantic_hash(row)


# --------------------------------------------------------------------------- #
# Semantics must invalidate. Every field the work order names.
# --------------------------------------------------------------------------- #

SEMANTIC_EDITS = [
    ("pets_allowed", {"pets_allowed": False}),
    ("pet_fee", {"pet_fee": 4500}),
    ("fee_basis", {"fee_basis": "per_stay"}),
    ("fee_cap", {"fee_cap": {"amount_minor": 15000, "currency": "USD",
                             "qualifier_stated": "per stay"}}),
    ("pet_count", {"pet_count_limit": 9}),
    ("weight_value", {"weight_limit": {"value": 999.0, "unit": "lb"}}),
    ("weight_operator", {"weight_limit": {"value": 50.0, "unit": "lb",
                                          "operator": "lte"}}),
    ("weight_scope", {"weight_limit": {"value": 50.0, "unit": "lb",
                                       "scope": "per_pet"}}),
    ("species", {"species": {"dogs": "accepted", "cats": "accepted"}}),
    ("deposit", {"deposit": {"amount_minor": 20000, "currency": "USD",
                             "refundable": True}}),
    ("substantive_restriction", {"other_charges": [
        {"kind": "cleaning", "amount_minor": 5000, "currency": "USD",
         "refundable": False}]}),
]


@pytest.mark.parametrize("label,patch", SEMANTIC_EDITS)
def test_a_change_to_an_approved_fact_invalidates_the_approval(row, label,
                                                               patch):
    changed = copy.deepcopy(row)
    changed["proposed_facts"] = dict(changed["proposed_facts"], **patch)
    assert AB.semantic_hash(changed) != AB.semantic_hash(row), label


def test_changing_the_canonical_supporting_evidence_invalidates(row):
    changed = copy.deepcopy(row)
    changed["evidence"][0] = dict(changed["evidence"][0],
                                  quote="a quote the page never made")
    assert AB.semantic_hash(changed) != AB.semantic_hash(row)


def test_dropping_a_citation_invalidates(row):
    changed = copy.deepcopy(row)
    changed["evidence"] = changed["evidence"][:-1]
    assert AB.semantic_hash(changed) != AB.semantic_hash(row)


def test_changing_the_evidence_block_hash_invalidates(row):
    changed = _edit(row, "rederivation.evidence_block_sha256", "0" * 64)
    assert AB.semantic_hash(changed) != AB.semantic_hash(row)


def test_changing_the_source_page_or_its_snapshot_invalidates(row):
    for path in ("provenance.source_url", "provenance.final_url",
                 "provenance.snapshot_hash", "provenance.authority_tier",
                 "provenance.source_type"):
        assert AB.semantic_hash(_edit(row, path, "changed")) \
            != AB.semantic_hash(row), path


def test_lifting_a_withholding_invalidates(row):
    """A withholding is a claim: that nothing is being asserted here."""
    changed = copy.deepcopy(row)
    changed["withheld_fields"] = {}
    assert AB.semantic_hash(changed) != AB.semantic_hash(row)


def test_identity_and_schema_are_part_of_the_claim(row):
    for field, value in (("identity_key", "some other hotel"),
                         ("canonical_name", "Some Other Hotel"),
                         ("market_id", "elsewhere-xx"),
                         ("policy_schema_version", "9.9"),
                         ("is_refusal", True),
                         ("publication_grade", "SOMETHING_ELSE"),
                         ("review_status", "SOMETHING_ELSE"),
                         ("service_animal_statement", "changed")):
        assert AB.semantic_hash(_edit(row, field, value)) \
            != AB.semantic_hash(row), field


def test_an_unclassified_field_refuses_to_hash(row):
    changed = copy.deepcopy(row)
    changed["some_field_nobody_classified"] = 1
    assert AB.unclassified_fields(changed)
    with pytest.raises(ValueError):
        AB.semantic_hash(changed)


def test_every_field_in_every_committed_row_is_classified(store):
    for key, record in store.items():
        assert AB.unclassified_fields(record) == {}, key


# --------------------------------------------------------------------------- #
# The migration.
# --------------------------------------------------------------------------- #

def test_the_migration_reproduces_038s_finding(rebinding):
    assert rebinding["decisions_total"] == 98
    assert rebinding["affected_by_reprojection"] == 16
    assert rebinding["rebound_without_founder_action"] == 15
    assert rebinding["requires_founder_re_review"] == 1


def test_the_only_substantive_change_is_a_hold_not_an_approval(rebinding):
    rows = rebinding["requires_founder_re_review_rows"]
    assert [row["canonical_name"] for row in rows] == [
        "Saint Kate - The Arts Hotel"]
    assert rows[0]["founder_decision"] == D36.HOLD


def test_every_rebound_row_proves_its_meaning_is_unchanged(rebinding):
    for row in rebinding["decisions"]:
        if row["classification"] == R39.PROVENANCE_ONLY:
            assert row["semantic_difference"] == {}
            assert row["new_binding"]["semantic_hash"] == \
                row["semantic_hash_after_reprojection"]
            assert row["provenance_that_moved"]


def test_old_approval_lineage_is_preserved(rebinding):
    ledger = {d["identity_key"]: d for d in F36.load_ledger()["decisions"]}
    for row in rebinding["decisions"]:
        old = row["old_binding"]
        assert old["record_hash"] == ledger[row["identity_key"]]["record_hash"]
        assert old["evidence_hash"] == \
            ledger[row["identity_key"]]["evidence_hash"]
        assert old["contract"] == "record_hash+evidence_hash (036)"
    assert rebinding["source_ledger"] == F36.LEDGER.name
    assert rebinding["migration_reason"].strip()


def test_the_founders_own_ledger_was_not_rewritten():
    """036 is history. A migration may sit beside it; it may not edit it."""
    changed = files_changed_by_this_work_order()
    assert not [path for path in changed
                if path.endswith("milwaukee_founder_decisions_036.json")]


def test_the_migration_is_deterministic():
    first = R39.rebinding_document()
    second = R39.rebinding_document()
    assert json.dumps(first, sort_keys=True, default=str) == \
        json.dumps(second, sort_keys=True, default=str)


def test_the_contract_is_versioned(rebinding):
    assert rebinding["binding_contract"] == AB.BINDING_CONTRACT_VERSION
    assert AB.BINDING_CONTRACT_VERSION == "semantic-approval/1.0"
    assert rebinding["supersedes_contract"] == "record_hash+evidence_hash (036)"


# --------------------------------------------------------------------------- #
# The binding, in use.
# --------------------------------------------------------------------------- #

def test_every_decision_still_applies_or_is_superseded():
    """Nothing is refused. A decision a later founder sitting answered again
    is superseded, not pending -- 040 re-decided Saint Kate."""
    applicable, refused = A36.bound_decisions()
    ledger_keys = {row["identity_key"] for row in F36.load_ledger()["decisions"]}
    superseded = ledger_keys & set(A36.superseded_decisions())
    assert refused == []
    assert len(applicable) + len(superseded) == 98


def test_a_row_that_needs_re_review_is_not_in_the_rebound_index():
    assert "saint kate the arts hotel" not in R39.rebound_index()


def test_the_semantic_route_only_admits_rows_the_migration_examined(row):
    """The rebinding is by NAME, not by rule: a row nobody looked at cannot
    slip through on the strength of a matching hash shape."""
    ledger = {d["identity_key"]: d for d in F36.load_ledger()["decisions"]}
    index = R39.rebound_index()
    assert index
    for key, (semantic, old_record, old_evidence) in index.items():
        assert semantic.startswith("sha256:")
        # The entry carries the decision's OWN hashes, so the semantic route
        # can refuse a decision that has been edited since 039 examined it.
        assert old_record == ledger[key]["record_hash"]
        assert old_evidence == ledger[key]["evidence_hash"]
    assert set(index) <= set(ledger)


def test_a_tampered_decision_is_refused_by_both_bindings(monkeypatch):
    """Editing a decision's record_hash is tampering with the founder's own
    statement about which record they saw. The semantic route must not forgive
    it just because the live row still means what it meant."""
    ledger = copy.deepcopy(F36.load_ledger())
    target = next(d for d in ledger["decisions"]
                  if d["identity_key"] in R39.rebound_index())
    target["record_hash"] = "sha256:moved"
    monkeypatch.setattr(F36, "load_ledger", lambda: ledger)
    applicable, refused = A36.bound_decisions()
    assert [row["identity_key"] for row in refused] == [target["identity_key"]]
    assert len(applicable) == 96


# --------------------------------------------------------------------------- #
# The rules 039 must not have loosened.
# --------------------------------------------------------------------------- #

def test_hyatt_regency_is_still_held_and_still_not_a_candidate():
    from scripts.pettripfinder.acquisition import closure_038 as C38
    assert "hyatt regency milwaukee" not in {row["identity_key"]
                                             for row in V39.rows()}
    ledger = {d["identity_key"]: d for d in F36.load_ledger()["decisions"]}
    assert ledger["hyatt regency milwaukee"]["decision"] == D36.HOLD
    authority = json.loads(A36.AUTHORITY.read_text(encoding="utf-8"))
    assert "hyatt regency milwaukee" not in {r["identity_key"]
                                             for r in authority["hotels"]}


def test_saint_kate_was_presented_and_not_approved_by_039():
    """The package asked the question and left it open. A founder answered it
    later, in their own work order, which is the point of the separation."""
    row = next(r for r in V39.rows()
               if r["identity_key"] == "saint kate the arts hotel")
    assert row["status"] == "AWAITING_FOUNDER_DECISION"
    assert row["founder_decision"] == "<UNANSWERED>"
    assert row["proposed_publication_facts"].get("pets_allowed") is True
    authority = json.loads(A36.AUTHORITY.read_text(encoding="utf-8"))
    record = next((r for r in authority["hotels"]
                   if r["identity_key"] == "saint kate the arts hotel"), None)
    if record is not None:
        assert record["approval"]["decision_source"]["work_order"] !=             V39.WORK_ORDER


def test_a_declined_page_is_presented_with_the_decline_and_no_facts():
    declined = [row for row in V39.rows()
                if row["identity_status"] == "DECLINED_BY_ROUTER_IDENTITY_GATE"]
    assert [row["property_name"] for row in declined] == [
        "Knickerbocker on the Lake", "The Iron Horse Hotel"]
    for row in declined:
        assert row["proposed_publication_facts"] == {}
        assert row["parse_is_trustworthy"] is False
        assert row["recommended_machine_verdict"] == V39.HOLD
        assert any("DECLINED" in item for item in row["ambiguity"])


def test_the_identity_gate_itself_was_not_touched_by_039():
    for path in files_changed_by_this_work_order():
        assert "policy_surface.py" not in path, path
        assert "identity_binding" not in path, path
        assert "publication_guard" not in path, path
        assert "identity_resolutions.json" not in path, path


def test_039_admitted_nobody_to_authority():
    """039 reviewed and rebound; it approved nothing.

    Asserted as "no record names 039" rather than "the file still holds 70",
    which stopped being 039's claim the moment PTF-MILWAUKEE-FOUNDER-DECISION
    -040 admitted four rows a founder approved.
    """
    from scripts.pettripfinder import market_authority as MA
    authority = json.loads(A36.AUTHORITY.read_text(encoding="utf-8"))
    for record in authority["hotels"]:
        source = record["approval"]["decision_source"]
        assert source["work_order"] != V39.WORK_ORDER
        assert source["ledger"] != V39.REVIEW_JSON.name
    for row in MA.load_market_exclusions("milwaukee-wi"):
        assert (row.get("decision_source") or {}).get(
            "work_order") != V39.WORK_ORDER
    # SUCCEEDED by PTF-MILWAUKEE-PUBLICATION-042: the market is published now,
    # and 039's claim was never "nobody may ever publish" -- it was that 039
    # itself neither approved nor published anything.
    if authority["published"]:
        assert authority["publication"]["work_order"] != V39.WORK_ORDER


def test_the_closure_arithmetic_is_unchanged():
    from scripts.pettripfinder.acquisition import closure_038 as C38
    recon = C38.reconciliation()
    assert recon["active_eligible"] == 133
    assert recon["census_total"] == 147
    assert recon["problems"] == []


def test_milwaukee_is_not_published():
    from scripts.pettripfinder.acquisition import closure_038 as C38
    ledger = json.loads(C38.LEDGER.read_text(encoding="utf-8"))
    assert ledger["published"] == 0
    assert ledger["deployed"] == 0
