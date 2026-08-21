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
    """No ledger exists, so no decision applies. Not one, not by default."""
    assert F.load_ledger() is None
    assert F.applicable_decisions() == []
    assert F.verdict()["verdict"] == "FOUNDER_REVIEW_REQUIRED"
    assert F.verdict()["authority_created"] is False


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
    flagged = [row for row in F.candidates()
               if row["review_state"] == F.READY
               and row["facts"].get("pets_allowed") is not True]
    assert len(flagged) == 2
    for row in flagged:
        assert row["proposed_decision"] == F.PROPOSE_INDIVIDUAL


# --------------------------------------------------------------------------- #
# 19 / 20 -- the package is deterministic.
# --------------------------------------------------------------------------- #

def test_regenerating_the_package_is_byte_identical():
    before = {path: path.read_bytes() for path in
              (F.REVIEW_JSON, F.REVIEW_CSV, F.SUMMARY)}
    manifest_before = json.loads(F.MANIFEST.read_text(encoding="utf-8"))
    F.write_package()
    for path, payload in before.items():
        assert path.read_bytes() == payload, path.name
    manifest_after = json.loads(F.MANIFEST.read_text(encoding="utf-8"))
    for key, value in manifest_before.items():
        if key == "generated_at":
            continue
        assert manifest_after[key] == value, key


def test_the_manifest_binds_the_package_to_the_store_it_came_from():
    manifest = json.loads(F.MANIFEST.read_text(encoding="utf-8"))
    assert manifest["source_store_sha256"] == F._sha256_file(F.STORE)
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
    assert F.counters()["authority_rows"] == 0
    assert not list((REPO / "atlas-dashboard" / "launch_packages"
                     / "pettripfinder").rglob("*hotel_policy_facts*milwaukee*"))
    assert not store().get("authority_written")


def test_no_held_or_unresolved_row_can_reach_authority_from_here():
    """There is no path: authority takes approvals, and there are none."""
    assert F.applicable_decisions() == []
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
    assert enums.POLICY_SCHEMA_VERSION == "1.2"
    assert store()["policy_schema_version"] == "1.2"
    changed = subprocess.run(
        ["git", "status", "--porcelain", "--",
         "atlas-dashboard/launch_packages/pettripfinder/markets/reports/"
         "milwaukee-wi_policy_proposals_001.json",
         "atlas-dashboard/scripts/pettripfinder/brightdata/policy_reading.py",
         "atlas-dashboard/scripts/pettripfinder/brightdata/marriott_surface.py",
         "atlas-dashboard/launch_packages/pettripfinder/identity_census"],
        cwd=str(REPO), capture_output=True, text=True).stdout.strip()
    assert changed == "", changed


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
