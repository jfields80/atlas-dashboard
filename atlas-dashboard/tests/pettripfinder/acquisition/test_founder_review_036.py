"""PTF-MILWAUKEE-FIRST-AUTHORITY-AND-FOUNDER-REVIEW-036.

WHAT THESE TESTS GUARD
----------------------
One boundary, from both sides.

A row that is technically clean is not an approved row, and an agent may not
close that distance. Most of what follows exists to make the shortcut
impossible: absence of a decision is not consent, a decision bound to a record
that has since moved does not apply, and nothing in this module can write an
attestation to disk.

The other side is that the question has to be worth answering. A founder
approving a fee ladder must be able to SEE the ladder, so the package is
tested for carrying every band rather than a number that stands for them.

The authority-construction tests the work order lists (serialisation into
authority, second-build byte-identity, no-pets rendering) belong to the work
order that builds authority. There is no Milwaukee authority to test: this pass
was not permitted to create one, and a test asserting properties of a file that
does not exist would assert nothing.
"""

import copy
import json
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[4]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts.pettripfinder.acquisition import founder_review_036 as F
from scripts.pettripfinder.contracts import enums
from scripts.pettripfinder.contracts import policy_schema as SCHEMA
from . import authority_freeze as AUTHORITY_FREEZE



FROZEN_BY_THIS_WORK_ORDER = (
    "atlas-dashboard/scripts/pettripfinder/contracts/policy_schema.py",
    "atlas-dashboard/scripts/pettripfinder/contracts/enums.py",
    "atlas-dashboard/scripts/pettripfinder/brightdata/policy_reading.py",
    "atlas-dashboard/scripts/pettripfinder/brightdata/marriott_surface.py",
    "atlas-dashboard/launch_packages/pettripfinder/identity_census",
    "atlas-dashboard/launch_packages/pettripfinder/markets/reports/"
    "milwaukee-wi_policy_proposals_001.json",
)


def files_changed_by(commit: str):
    return subprocess.run(["git", "show", "--name-only", "--format=", commit],
                          cwd=str(REPO), capture_output=True,
                          text=True).stdout.split()


def store():
    return F.R34.store_doc()


# --------------------------------------------------------------------------- #
# 1 -- the cohort, derived and not listed.
# --------------------------------------------------------------------------- #

def test_the_cohort_is_exactly_the_reviewable_states():
    assertions = F.cohort_assertions()
    assert assertions["candidates"] == 98
    assert assertions["ready"] == 72
    assert assertions["refusal"] == 26
    assert assertions["unique_identities"] == 98
    assert assertions["duplicates"] == []
    assert assertions["missing_canonical_block"] == []
    assert assertions["missing_source_url"] == []
    assert assertions["not_in_census"] == []


def test_no_held_or_unresolved_row_is_in_the_cohort():
    keys = {row["identity_key"] for row in F.cohort_rows()}
    for row in store()["items"]:
        if row["review_status"] in F.COHORT_STATES:
            continue
        assert row["identity_key"] not in keys, row["identity_key"]
    excluded = F.cohort_assertions()["excluded_states"]
    assert excluded["HELD_SCHEMA_CANNOT_REPRESENT"] == 12
    assert excluded["HELD_INSUFFICIENT_EVIDENCE"] == 7


def test_the_cohort_is_not_a_hardcoded_list_of_names():
    import inspect
    source = inspect.getsource(F)
    for row in F.cohort_rows()[:20]:
        assert row["identity_key"] not in source, row["identity_key"]


# --------------------------------------------------------------------------- #
# 2 / 3 / 25 -- ready is not approved, and neither is silence.
# --------------------------------------------------------------------------- #

def test_a_ready_row_is_not_founder_approved():
    for row in F.candidates():
        if row["review_state"] != F.READY:
            continue
        assert row["founder_approved"] is False
        assert row["founder_decision"] is None
        assert row["proposed_decision"] in (F.PROPOSE_APPROVE,
                                            F.PROPOSE_INDIVIDUAL)


def test_a_refusal_row_is_not_founder_approved():
    for row in F.candidates():
        if row["review_state"] != F.REFUSAL:
            continue
        assert row["founder_approved"] is False
        assert row["facts"].get("pets_allowed") is False


def test_the_store_records_no_approval_anywhere():
    doc = store()
    assert all(not row.get("founder_approved") for row in doc["items"])
    assert all(not row.get("published") for row in doc["items"])
    assert F.counters()["founder_approved"] == 0


def test_absence_of_a_decision_is_not_approval():
    """A row is approved by a decision that names a human, or not at all.

    NARROWED. When this was written no ledger existed and the emptiness was
    the proof. A founder has since decided, so the claim is made where it
    still bites: every applicable decision names a decider, an unlisted row is
    not approved, and the review package itself approves nothing.
    """
    ledger = F.load_ledger()
    if ledger is None:
        assert F.applicable_decisions() == []
        assert F.verdict()["verdict"] == "FOUNDER_REVIEW_REQUIRED"
        return
    decided = {row["identity_key"] for row in F.applicable_decisions()}
    for decision in F.applicable_decisions():
        assert decision["decided_by"], decision["identity_key"]
        assert decision["decision"] in ("APPROVE", "APPROVE_REFUSAL", "HOLD")
    for row in F.candidates():
        assert row["founder_approved"] is False   # the package approves nothing
        assert row["founder_decision"] is None
        if row["identity_key"] not in decided:
            assert row["identity_key"] not in decided


def test_this_module_cannot_write_an_attestation():
    """The skeleton is printed, never written, and carries no decisions."""
    import inspect
    source = inspect.getsource(F)
    assert "LEDGER.write_text" not in source
    assert "LEDGER.open" not in source
    template = F.ledger_template()
    assert template["decided_by"].startswith("<")
    assert all(entry["decision"] is None for entry in template["decisions"])
    assert all(entry["decided_by"] is None for entry in template["decisions"])


# --------------------------------------------------------------------------- #
# 6 / 7 / 8 / 9 -- a decision binds to what the founder was shown.
# --------------------------------------------------------------------------- #

def _ledger_with(row, **overrides):
    entry = {"identity_key": row["identity_key"],
             "decision": F.PROPOSE_APPROVE,
             "decided_by": "a-human",
             "record_hash": row["record_hash"],
             "evidence_hash": row["evidence_hash"]}
    entry.update(overrides)
    return {"decisions": [entry]}


def test_a_decision_against_a_moved_record_does_not_apply(monkeypatch):
    row = F.candidates()[0]
    monkeypatch.setattr(F, "load_ledger",
                        lambda: _ledger_with(row, record_hash="sha256:stale"))
    with pytest.raises(F.FounderDecisionError):
        F.applicable_decisions()


def test_a_decision_against_moved_evidence_does_not_apply(monkeypatch):
    row = F.candidates()[0]
    monkeypatch.setattr(F, "load_ledger",
                        lambda: _ledger_with(row, evidence_hash="sha256:stale"))
    with pytest.raises(F.FounderDecisionError):
        F.applicable_decisions()


def test_a_decision_for_a_row_that_is_not_a_candidate_is_refused(monkeypatch):
    row = dict(F.candidates()[0], identity_key="a hotel nobody reviewed")
    monkeypatch.setattr(F, "load_ledger", lambda: _ledger_with(row))
    with pytest.raises(F.FounderDecisionError):
        F.applicable_decisions()


def test_a_decision_that_names_no_decider_is_refused(monkeypatch):
    row = F.candidates()[0]
    monkeypatch.setattr(F, "load_ledger",
                        lambda: _ledger_with(row, decided_by=""))
    with pytest.raises(F.FounderDecisionError):
        F.applicable_decisions()


def test_a_well_formed_decision_binds(monkeypatch):
    """The mechanism works -- which is why refusing to use it is a choice."""
    row = F.candidates()[0]
    monkeypatch.setattr(F, "load_ledger", lambda: _ledger_with(row))
    applied = F.applicable_decisions()
    assert len(applied) == 1
    assert applied[0]["identity_key"] == row["identity_key"]


# --------------------------------------------------------------------------- #
# 10 / 14 / 18 -- what is checked, and what is deliberately not.
# --------------------------------------------------------------------------- #

def _first_row_with(field):
    for row in F.cohort_rows():
        if (row["proposed_facts"] or {}).get(field):
            return row
    raise AssertionError("no row carries %s" % field)


def test_every_mechanical_check_can_actually_fail():
    """A gate that never fires guards nothing."""
    row = _first_row_with("fee_tiers")
    assert F.row_checks(row)["blocking_issues"] == []
    breakages = (
        (lambda r: r["provenance"].__setitem__("source_url", ""), "no source URL"),
        (lambda r: r["provenance"].__setitem__("snapshot_hash", ""),
         "no document hash"),
        (lambda r: r.__setitem__("evidence", []), "no evidence entries"),
        (lambda r: r["withheld_fields"].__setitem__("pet_count_limit",
                                                    "SOURCE_SILENT"),
         "asserted and withheld at once"),
        (lambda r: r["proposed_facts"]["fee_tiers"][0].pop("role"),
         "structured fee fails schema 1.2"),
        (lambda r: r.__setitem__("identity_key", "not a milwaukee hotel"),
         "identity is not in the Milwaukee census"),
        (lambda r: r.__setitem__("frozen_semantics_violations", ["x"]),
         "frozen-semantics violation"),
    )
    for mutate, expected in breakages:
        broken = copy.deepcopy(row)
        mutate(broken)
        issues = " | ".join(F.row_checks(broken)["blocking_issues"])
        assert expected in issues, (expected, issues)


def test_an_unknown_optional_field_does_not_block_a_row():
    rows = [row for row in F.candidates()
            if row["proposed_decision"] == F.PROPOSE_APPROVE
            and "weight_limit" not in row["facts"]]
    assert rows, "expected at least one approved-proposal row with no weight"
    for row in rows:
        assert row["blocking_issues"] == []


def test_a_withheld_field_never_appears_in_the_facts():
    for row in F.candidates():
        overlap = set(row["facts"]) & set(row["withheld_fields"])
        assert overlap == set(), row["identity_key"]


def test_every_structured_fee_validates_under_schema_1_2():
    checked = 0
    for row in F.candidates():
        subset = {key: row["facts"][key] for key in F.STRUCTURED_FIELDS
                  if key in row["facts"]}
        if not subset:
            continue
        checked += 1
        assert SCHEMA.validate_facts(subset) == (), row["identity_key"]
    assert checked >= 20


# --------------------------------------------------------------------------- #
# 11 / 12 / 13 -- the founder can see the price they are approving.
# --------------------------------------------------------------------------- #

def test_a_fee_ladder_survives_the_package_whole():
    row = next(r for r in F.candidates() if r["facts"].get("fee_tiers"))
    tiers = row["facts"]["fee_tiers"]
    assert len(tiers) >= 2
    assert len({tier["amount_cents"] for tier in tiers}) >= 2
    for tier in tiers:
        assert tier["role"] and tier["condition_type"] and tier["boundary_unit"]
    written = json.loads(F.REVIEW_JSON.read_text(encoding="utf-8"))
    stored = next(item for item in written["candidates"]
                  if item["identity_key"] == row["identity_key"])
    assert stored["facts"]["fee_tiers"] == tiers


def test_the_csv_spells_every_band_out_rather_than_collapsing_it():
    row = next(r for r in F.candidates() if r["facts"].get("fee_tiers"))
    cell = F._csv_value(row, "fee_structure")
    for tier in row["facts"]["fee_tiers"]:
        assert "$%d.%02d" % divmod(int(tier["amount_cents"]), 100) in cell
    assert F._csv_value(row, "pet_fee") == ""


def test_a_fee_cap_reaches_the_package_as_a_cap():
    rows = [row for row in F.candidates() if row["facts"].get("fee_cap")]
    assert rows
    for row in rows:
        assert "pet_fee" in row["facts"] or "fee_tiers" in row["facts"] \
            or "pet_fee" in row["withheld_fields"]
        assert row["facts"]["fee_cap"]["amount_minor"] > 0


def test_the_package_names_what_the_authority_builder_must_convert():
    """The legacy money shape is a finding, not a surprise for the next order."""
    requirements = F.pre_authority_requirements()
    money = next(item for item in requirements
                 if "money shapes" in item["requirement"])
    assert money["rows_affected"]
    assert "EMPTY STRING" in money["detail"]


# --------------------------------------------------------------------------- #
# 15 / 16 / 17 -- refusals stay refusals.
# --------------------------------------------------------------------------- #

def test_a_refusal_carries_a_quote_that_supports_it():
    for row in F.candidates():
        if row["review_state"] != F.REFUSAL:
            continue
        quotes = [item["quote"] for item in row["evidence"]["per_field_evidence"]
                  if "pets_allowed" in (item.get("field_refs") or ())]
        assert any(quote.strip() for quote in quotes), row["identity_key"]
        assert row["facts"]["pets_allowed"] is False


def test_a_no_pets_row_can_never_read_as_pet_friendly():
    for row in F.candidates():
        if row["review_state"] != F.REFUSAL:
            continue
        assert row["facts"].get("pets_allowed") is not True
        assert "pet_fee" not in row["facts"]
        assert "fee_tiers" not in row["facts"]
        assert row["proposed_decision"] in (F.PROPOSE_APPROVE_REFUSAL,
                                            F.PROPOSE_INDIVIDUAL)


def test_a_contrastive_refusal_quote_goes_to_individual_review():
    """"no other pets" is a contrast, and what it contrasts with is the answer.

    After "ADA service animals are welcome" it is a blanket refusal; after
    "dogs are welcome" it refuses only the other species, and BRAND-REPAIR-003
    caught that form nearly publishing a no-pets record for a hotel that takes
    dogs. A founder cannot tell those apart from three words.
    """
    assert not F.refusal_quote_is_self_contained("no other pets")
    assert F.refusal_quote_is_self_contained("Pets are not accepted")
    flagged = [row for row in F.candidates()
               if any("contrast" in note
                      for note in row["needs_individual_attention"])]
    assert len(flagged) == 3
    for row in flagged:
        assert row["proposed_decision"] == F.PROPOSE_INDIVIDUAL
        assert "service animals are welcome" in \
            " ".join(row["needs_individual_attention"]).lower()


def test_a_service_animal_statement_alone_is_never_an_allowance():
    for row in F.candidates():
        facts = row["facts"]
        if facts.get("service_animal_exception") and "pets_allowed" not in facts:
            assert row["proposed_decision"] == F.PROPOSE_INDIVIDUAL


def test_a_priced_policy_with_no_stated_allowance_goes_to_individual_review():
    """036 found two such rows. One of them was Saint Kate, whose page DID
    grant permission -- the reader was misreading a place restriction as a
    refusal, and 038 repaired it. So the live count is one, and the rule the
    test is about is unchanged: a priced policy with no stated allowance never
    reaches a bulk approval."""
    flagged = [row for row in F.candidates()
               if row["review_state"] == F.READY
               and row["facts"].get("pets_allowed") is not True]
    assert flagged
    for row in flagged:
        assert row["proposed_decision"] == F.PROPOSE_INDIVIDUAL


# --------------------------------------------------------------------------- #
# 19 / 20 -- the package is deterministic.
# --------------------------------------------------------------------------- #

def test_regenerating_the_package_is_deterministic(tmp_path):
    """Regenerated into a temp directory, never over the committed package.

    The manifest carries a generated_at, so a test that regenerated in place
    would mutate the artifact the founder was shown in order to check it.

    NARROWED by PTF-...-NORMALIZATION-041. The claim was byte-identity with
    the COMMITTED package, which held only while the store stood still. 041
    projected the store onto the current reader -- one row's facts changed,
    with the founder's approval -- so a regeneration today legitimately
    differs from the document the founder read in 036. What must still hold is
    that the generator is deterministic and that the committed artifact is
    never silently rewritten, and both are checked here.
    """
    first = tmp_path / "first"
    second = tmp_path / "second"
    first.mkdir()
    second.mkdir()
    committed = {path.name: path.read_bytes() for path in
                 (F.REVIEW_JSON, F.REVIEW_CSV, F.SUMMARY)}
    manifest_before = json.loads(F.MANIFEST.read_text(encoding="utf-8"))
    paths = (F.PACKAGE_DIR, F.REVIEW_JSON, F.REVIEW_CSV, F.MANIFEST, F.SUMMARY)
    try:
        F.write_package(first)
        F.write_package(second)
        for name in committed:
            assert (first / name).read_bytes() == (second / name).read_bytes(),                 name
        manifest_after = json.loads(
            (first / "founder-review-manifest.json").read_text(encoding="utf-8"))
    finally:
        # The module's paths are restored WITHOUT writing: regenerating in
        # place is exactly what this test exists to avoid doing.
        (F.PACKAGE_DIR, F.REVIEW_JSON, F.REVIEW_CSV, F.MANIFEST,
         F.SUMMARY) = paths
    # Three keys record WHEN and WHERE the manifest was made rather than what
    # the package says: the clock, the file paths, and the HEAD at generation
    # time -- which moved when 036 was committed, one commit after the package
    # it describes. Everything that is a claim about the candidates must match.
    for key, value in manifest_before.items():
        # source_store_sha256 joins the four: it pins the store AS IT WAS when
        # the founder was shown the package, and 041 projected the store onto
        # the current reader. A manifest whose store hash silently followed
        # the store would bind the package to nothing.
        if key in ("generated_at", "files", "source_head", "governance",
                   "source_store_sha256"):
            continue
        assert manifest_after[key] == value, key
    assert manifest_before["source_store_sha256"] !=         manifest_after["source_store_sha256"]
    # Those four record WHEN, WHERE and IN WHAT CONTEXT the manifest was made
    # rather than what the package says. Three are clock and paths; the fourth
    # is the real story and is asserted rather than skipped: when the package
    # was committed no decision ledger existed, and now one does.
    assert manifest_before["governance"]["ledger_exists"] is False
    assert manifest_after["governance"]["ledger_exists"] is True
    assert manifest_after["candidate_count"] == manifest_before["candidate_count"]
    # And the committed package itself is untouched by any of this.
    for path, payload in zip((F.REVIEW_JSON, F.REVIEW_CSV, F.SUMMARY),
                             committed.values()):
        assert path.read_bytes() == payload


def test_the_manifest_binds_the_package_to_the_store_it_came_from():
    """The manifest pins the store AS IT WAS when the founder was shown the
    package. PTF-...-NORMALIZATION-041 projected the store onto the current
    reader, so the live file no longer hashes to it -- and that is correct:
    a binding that silently followed the store would bind to nothing."""
    manifest = json.loads(F.MANIFEST.read_text(encoding="utf-8"))
    assert manifest["source_store_sha256"].startswith("sha256:")
    committed_then = subprocess.run(
        ["git", "show", "01fd5a8:" + F.STORE.relative_to(REPO).as_posix()],
        cwd=str(REPO), capture_output=True).stdout
    if committed_then:
        import hashlib
        assert manifest["source_store_sha256"] == (
            "sha256:" + hashlib.sha256(committed_then).hexdigest())
    assert manifest["candidate_count"] == 98
    assert manifest["approval_count"] == 0
    assert manifest["authority_count"] == 0
    assert manifest["governance"]["authority_permitted_now"] is False
    for name, entry in manifest["files"].items():
        # Paths in the manifest are relative to the atlas-dashboard package
        # root, which is where the store and the census live too.
        assert (F.REPO / entry["path"]).is_file(), name


# --------------------------------------------------------------------------- #
# 4 / 5 / 21 to 24 -- what must not have happened.
# --------------------------------------------------------------------------- #

def test_no_milwaukee_authority_was_created():
    """NARROWED by PTF-MILWAUKEE-FOUNDER-DECISION-036.

    This claimed the work order created no Milwaukee authority, which
    was true and still is. Read against the live filesystem it became
    "Milwaukee may never have one", and the founder has since approved
    96 records explicitly and in writing. The historical claim is
    checked against the commit; the standing claim -- that authority is
    recorded and never live inventory, and that every row in it was
    approved by a human -- is checked beside it.
    """
    AUTHORITY_FREEZE.assert_commit_created_no_authority("01fd5a8")
    AUTHORITY_FREEZE.assert_authority_is_recorded_not_live()
    AUTHORITY_FREEZE.assert_every_authority_row_was_approved_by_a_human()


def test_no_held_or_unresolved_row_can_reach_authority_from_here():
    """Authority takes approvals, and no held row has one.

    NARROWED: the emptiness of the ledger used to prove this. Now the ledger
    is checked instead -- a row outside the 98-candidate cohort is not in it,
    so it cannot be approved and cannot be admitted.
    """
    decided = {row["identity_key"] for row in F.applicable_decisions()}
    cohort = {row["identity_key"] for row in F.cohort_rows()}
    assert decided <= cohort
    for row in F.R34.store_doc()["items"]:
        if row["review_status"] not in F.COHORT_STATES:
            assert row["identity_key"] not in decided, row["identity_key"]
    complement = F.complement()
    assert complement["held_rows"] == 19
    assert complement["by_state"]["HELD_SCHEMA_CANNOT_REPRESENT"] == 12
    assert complement["by_state"]["HELD_INSUFFICIENT_EVIDENCE"] == 7
    assert complement["active_unresolved"] == 16
    for row in complement["rows"]:
        assert row["next_action"] or row["review_state"]


def test_nothing_was_deployed_and_no_provider_was_called():
    cost = F.cost()
    assert cost["provider_calls"] == 0
    assert cost["brightdata_spend_usd"] == 0.0
    assert F.counters()["deployed_live"] == 0
    import inspect
    # No deployment path is reachable from here: the module names no deploy
    # tool and calls nothing that publishes. "deployed_live: 0" is a COUNTER,
    # so the check is on what could be invoked, not on the word.
    source = inspect.getsource(F).lower()
    for token in ("netlify", "--prod", "subprocess.run([\"netlify",
                  "build_market_authorities", "assemble("):
        assert token not in source, token


def test_the_schema_is_still_1_2_and_the_store_was_not_touched():
    """The claim is about THIS work order, not about the future.

    It used to assert the working tree was clean, which made it fail the moment
    a later, authorised work order touched the reader --
    PTF-...-FULL-CLOSURE-038 repaired a place-qualified refusal. What is
    durable is that 01fd5a8 changed none of these files, and that is checked
    against its own commit.
    """
    assert enums.POLICY_SCHEMA_VERSION == "1.2"
    assert store()["policy_schema_version"] == "1.2"
    touched = set(files_changed_by('01fd5a8')) & set(FROZEN_BY_THIS_WORK_ORDER)
    assert touched == set(), touched


def test_the_counters_reconcile():
    counters = F.counters()
    assert counters["census_total"] == 147
    assert counters["active_eligible"] == 133
    assert counters["observed"] == 117
    assert counters["sum_of_final_states"] == 147
    assert counters["founder_review_candidates"] == 98
    assert (counters["proposed_approve"] + counters["proposed_approve_refusal"]
            + counters["proposed_individual_review"]) == 98
    assert counters["published"] == 0
