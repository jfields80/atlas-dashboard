"""PTF-INVENTORY-001 -- regression tests for the narrow tiered-fee approval.

The business policy: a valid tiered or capped pet fee is not a contradiction,
and the renderer's inability to show two numbers must not suppress credible
pet-friendly inventory. The safety policy: that allowance must waive EXACTLY
one reason code, for EXACTLY one hotel, bound to EXACTLY one frozen result
hash -- and must never become a general-purpose bypass.

Every test here defends the second half of that sentence.
"""

from __future__ import annotations

import shutil

import pytest

from scripts.pettripfinder import prod003_approvals as PA
from scripts.pettripfinder import promote_worker_candidates as PWC

@pytest.fixture(autouse=True)
def isolated_promotion_root(request, monkeypatch):
    """Point the destination at a scratch dir for every test in this file.

    Without this the suite reads the REAL promotion root, so once an operator
    has run --apply every test here fails with destination_would_overwrite --
    gate logic must not depend on whether a promotion has happened.

    The scratch dir lives UNDER the app root (in gitignored data/) rather than
    in pytest's tmp_path, because the adapter reports destinations as paths
    relative to the app root and a path outside it raises ValueError.
    """
    root = (PWC._APP_ROOT / "data" / "worker_runs" / "_pytest_promotion"
            / request.node.name[:60])
    monkeypatch.setattr(PWC, "PROMOTION_ROOT", root)
    yield
    shutil.rmtree(root, ignore_errors=True)


KEY = "red roof plus columbus downtown convention center"
NAME = "Red Roof PLUS+ Columbus Downtown Convention Center"
HASH = "sha256:" + "a" * 64
OTHER_KEY = "red roof plus columbus worthington"


def g1_record(**over):
    rec = {
        "listing_key": KEY,
        "listing_name": NAME,
        "candidate_identity": HASH,
        "final_route": "REVIEW",
        "reason_codes": ["STRUCTURED_FEE_REQUIRED"],
        "multi_amount_detected": True,
        "multi_amount_values": ["105.00", "15.00"],
        "manual_review_reason": "Evidence states multiple distinct pet-fee amounts",
        "source_urls": ["https://www.redroof.com/why-red-roof/pet-policy"],
        "model_id": "gpt-5.4-nano-2026-03-17",
        "supported_facts": [
            {"field_name": "pets_allowed", "value": "true",
             "evidence_quote": "Up to two well-behaved domestic pets",
             "source_url": "https://www.redroof.com/why-red-roof/pet-policy",
             "source_type": "OFFICIAL_BRAND"},
            {"field_name": "weight_limit", "value": "80 pounds each",
             "evidence_quote": "up to 80 pounds each",
             "source_url": "https://www.redroof.com/why-red-roof/pet-policy",
             "source_type": "OFFICIAL_BRAND"},
        ],
    }
    rec.update(over)
    return rec


def approval(**over):
    a = {
        "listing_key": KEY, "listing_name": NAME, "result_hash": HASH,
        "source_url": "https://www.redroof.com/why-red-roof/pet-policy",
        "verification_date": "2026-07-15", "gate1_route": "REVIEW",
        "decision": PA.DECISION_TIERED_FEE_OMITTED,
        "operator": "jfields80", "approval_date": "2026-07-28",
        "waived_reason_codes": ["STRUCTURED_FEE_REQUIRED"],
        "preserved_fee_amounts": ["105.00", "15.00"],
    }
    a.update(over)
    return a


def ctx(**over):
    c = {
        "g1_safe": {}, "g1_manual": {KEY: g1_record()},
        "committed_keys": set(), "corpus_ready": set(),
        "prod_display": {KEY: NAME}, "approvals": {"approvals": []},
    }
    c.update(over)
    return c


def run(a=None, c=None, batch=None):
    a = a or approval()
    c = c or ctx()
    return PWC.evaluate(a, c, batch if batch is not None else [a["listing_key"]])


# --------------------------------------------------------------------------- #
# 1 / 2 -- blocked without approval, allowed with it.
# --------------------------------------------------------------------------- #

def test_1_structured_fee_required_stays_blocked_without_the_approval(monkeypatch):
    """The ordinary decision must still fail on a manual-review record."""
    res = run(approval(decision=PA.DECISION_APPROVED, gate1_route="READY",
                       waived_reason_codes=None, preserved_fee_amounts=None))
    assert res["excluded"] is True
    assert "manual_review_record" in res["failures"]


def test_1b_a_hold_or_reject_decision_is_never_selected():
    for d in (PA.DECISION_HOLD, PA.DECISION_REJECTED, PA.DECISION_SUPERSEDED):
        res = run(approval(decision=d))
        assert res["selected"] is False and res["excluded"] is True


def test_2_matching_approval_allows_promotion():
    res = run()
    assert res["excluded"] is False, res["failures"]
    assert res["failures"] == []
    assert res["mapped_corpus_candidate"] is not None


def test_2b_scalar_fee_is_omitted_from_the_promoted_record():
    res = run()
    pet_facts = dict(res["mapped_corpus_candidate"]["pet_facts"])
    assert "pet_fee" not in pet_facts
    assert "fee_basis" not in pet_facts


# --------------------------------------------------------------------------- #
# 3 -- tier values and conditions preserved.
# --------------------------------------------------------------------------- #

def test_3_tier_values_and_conditions_survive_in_provenance():
    tf = run()["mapped_corpus_candidate"]["worker_provenance"]["tiered_fee"]
    assert sorted(tf["amounts"]) == ["105.00", "15.00"]
    assert tf["scalar_fee_omitted"] is True
    assert "cannot represent" in tf["omission_reason"]
    assert tf["waived_reason_codes"] == ["STRUCTURED_FEE_REQUIRED"]
    assert "multiple distinct pet-fee amounts" in tf["evidence_statement"]


def test_3b_consumer_note_is_honest_about_the_uncertainty():
    note = run()["mapped_corpus_candidate"]["worker_provenance"]["tiered_fee"]["consumer_note"]
    assert note == PWC.TIERED_FEE_CONSUMER_NOTE
    assert "vary by stay length" in note
    assert "Confirm the current fee directly with the hotel" in note


def test_3c_preserved_amounts_must_match_the_evidence():
    res = run(approval(preserved_fee_amounts=["99.00", "1.00"]))
    assert "preserved_fee_amounts_do_not_match_evidence" in res["failures"]


# --------------------------------------------------------------------------- #
# 4 / 5 -- hash and hotel binding.
# --------------------------------------------------------------------------- #

def test_4_mismatched_result_hash_fails_closed():
    res = run(approval(result_hash="sha256:" + "b" * 64))
    assert res["excluded"] is True
    assert "stale_result_hash" in res["failures"]


def test_5_approval_for_one_hotel_cannot_authorize_another():
    res = run(approval(listing_key=OTHER_KEY, listing_name="Red Roof PLUS+ Columbus Worthington"))
    assert res["excluded"] is True
    assert "unknown_in_gate1_manifest" in res["failures"]


def test_5b_a_launch_safe_record_cannot_use_the_tiered_decision():
    c = ctx(g1_safe={KEY: g1_record(final_route="READY")}, g1_manual={})
    res = run(c=c)
    assert res["excluded"] is True
    assert "launch_safe_record_needs_standard_approval" in res["failures"]


# --------------------------------------------------------------------------- #
# 6 / 7 -- the waiver clears nothing else.
# --------------------------------------------------------------------------- #

def test_6_approval_cannot_clear_a_contradiction():
    c = ctx(g1_manual={KEY: g1_record(
        reason_codes=["STRUCTURED_FEE_REQUIRED", "CONTRADICTORY_OFFICIAL_SOURCES"])})
    res = run(c=c)
    assert res["excluded"] is True
    assert "contradiction" in res["failures"]


def test_7_approval_cannot_clear_source_authority_ambiguity():
    """Exactly the Red Roof West Hilliard case."""
    c = ctx(g1_manual={KEY: g1_record(
        reason_codes=["STRUCTURED_FEE_REQUIRED", "SOURCE_AUTHORITY_AMBIGUITY"])})
    res = run(c=c)
    assert res["excluded"] is True
    assert "source_authority_ambiguity" in res["failures"]


def test_7b_approval_cannot_clear_incomplete_extraction():
    c = ctx(g1_manual={KEY: g1_record(
        reason_codes=["STRUCTURED_FEE_REQUIRED", "INCOMPLETE_EXTRACTION"])})
    res = run(c=c)
    assert res["excluded"] is True
    assert "incomplete_extraction" in res["failures"]


def test_7c_an_unknown_reason_code_blocks_rather_than_slipping_through():
    c = ctx(g1_manual={KEY: g1_record(
        reason_codes=["STRUCTURED_FEE_REQUIRED", "SOME_FUTURE_REASON"])})
    res = run(c=c)
    assert res["excluded"] is True
    assert any(f.startswith("unwaived_reason_codes") for f in res["failures"])


def test_7d_the_manifest_validator_refuses_a_non_waivable_waiver():
    m = {"schema": PA.SCHEMA_ID, "market": "columbus-oh", "pending_candidates": [],
         "approvals": [approval(waived_reason_codes=["SOURCE_AUTHORITY_AMBIGUITY"])]}
    errs = PA.validate_manifest(m)
    assert any("non_waivable_reason_codes" in e for e in errs)


def test_7e_never_waivable_set_is_disjoint_from_waivable():
    assert PA.WAIVABLE_REASON_CODES.isdisjoint(PA.NEVER_WAIVABLE_REASON_CODES)
    assert PA.WAIVABLE_REASON_CODES == {"STRUCTURED_FEE_REQUIRED"}


# --------------------------------------------------------------------------- #
# 8 -- changed evidence invalidates the approval.
# --------------------------------------------------------------------------- #

def test_8_changed_evidence_invalidates_the_approval():
    """A different candidate_identity means the evidence moved underneath us."""
    c = ctx(g1_manual={KEY: g1_record(candidate_identity="sha256:" + "c" * 64)})
    res = run(c=c)
    assert res["excluded"] is True
    assert "stale_result_hash" in res["failures"]


def test_8b_waiver_requires_real_multi_amount_evidence():
    c = ctx(g1_manual={KEY: g1_record(multi_amount_detected=False, multi_amount_values=[])})
    res = run(c=c)
    assert res["excluded"] is True
    assert "tiered_fee_waiver_without_multi_amount_evidence" in res["failures"]


def test_8c_waiver_does_not_apply_when_a_scalar_fee_exists():
    facts = g1_record()["supported_facts"] + [
        {"field_name": "pet_fee", "value": "$15", "evidence_quote": "$15 per night",
         "source_url": "https://www.redroof.com/why-red-roof/pet-policy",
         "source_type": "OFFICIAL_BRAND"}]
    res = run(c=ctx(g1_manual={KEY: g1_record(supported_facts=facts)}))
    assert "scalar_pet_fee_present_waiver_not_applicable" in res["failures"]


# --------------------------------------------------------------------------- #
# 9 -- the consumer-facing record never carries a flattened fee.
# --------------------------------------------------------------------------- #

def test_9_published_projection_has_no_misleading_scalar_fee():
    proj = run()["package_projection"]
    assert "pet_fee" not in proj["facts"]
    assert "fee_basis" not in proj["facts"]
    assert proj["facts"].get("pets_allowed") == "true"
    # neither tier amount leaks in as if it were the whole policy
    blob = repr(proj["facts"])
    assert "15.00" not in blob and "105.00" not in blob


def test_9b_supported_non_fee_facts_are_preserved():
    proj = run()["package_projection"]
    assert proj["facts"]["weight_limit"] == "80 pounds each"
    assert proj["evidence_quote"]


# --------------------------------------------------------------------------- #
# 10 -- existing behaviour is unchanged for unapproved properties.
# --------------------------------------------------------------------------- #

def test_10_standard_approvals_behave_exactly_as_before():
    safe = g1_record(final_route="READY", reason_codes=["PUBLICATION_ELIGIBLE"],
                     multi_amount_detected=False, multi_amount_values=[])
    a = approval(decision=PA.DECISION_APPROVED, gate1_route="READY")
    for f in PA.TIERED_FEE_FIELDS:
        a.pop(f, None)
    res = PWC.evaluate(a, ctx(g1_safe={KEY: safe}, g1_manual={}), [KEY])
    assert res["excluded"] is False, res["failures"]
    assert "tiered_fee" not in res["mapped_corpus_candidate"]["worker_provenance"]


def test_10b_manual_review_records_without_approval_still_blocked():
    a = approval(decision=PA.DECISION_APPROVED, gate1_route="READY")
    for f in PA.TIERED_FEE_FIELDS:
        a.pop(f, None)
    res = run(a)
    assert res["excluded"] is True


def test_10c_collision_gates_still_apply_to_a_tiered_approval():
    res = run(c=ctx(committed_keys={KEY}))
    assert "collision_committed_package" in res["failures"]
    res = run(c=ctx(corpus_ready={KEY}))
    assert "collision_existing_corpus_record" in res["failures"]


def test_10d_evidence_and_source_gates_still_apply():
    res = run(c=ctx(g1_manual={KEY: g1_record(source_urls=[])}))
    assert "no_source_url" in res["failures"]
    res = run(c=ctx(g1_manual={KEY: g1_record(supported_facts=[])}))
    assert "no_supported_facts" in res["failures"]


def test_10f_idempotency_failures_are_distinguished_from_unsafe_ones():
    """An already-promoted record must not veto a later, valid promotion --
    but any real gate failure still refuses the whole batch."""
    assert PWC.IDEMPOTENCY_FAILURES == {
        "collision_committed_package", "collision_existing_corpus_record",
        "destination_would_overwrite"}
    # none of the safety gates may ever be treated as idempotent
    for unsafe in ("contradiction", "source_authority_ambiguity", "stale_result_hash",
                   "incomplete_extraction", "no_supported_facts", "source_not_official",
                   "structured_fee_required", "multi_term_fee_signal"):
        assert unsafe not in PWC.IDEMPOTENCY_FAILURES


def test_10e_manifest_schema_rules_for_the_new_decision():
    base = {"schema": PA.SCHEMA_ID, "market": "columbus-oh", "pending_candidates": []}
    # a READY route has nothing to waive
    m = dict(base, approvals=[approval(gate1_route="READY")])
    assert any("tiered_fee_requires_review_route" in e for e in PA.validate_manifest(m))
    # one amount is not a tier
    m = dict(base, approvals=[approval(preserved_fee_amounts=["15.00"])])
    assert any("two_or_more_amounts" in e for e in PA.validate_manifest(m))
    # the extra fields are rejected on an ordinary approval
    a = approval(decision=PA.DECISION_APPROVED, gate1_route="READY")
    m = dict(base, approvals=[a])
    assert any("unexpected_fields" in e for e in PA.validate_manifest(m))
    # a well-formed record validates
    assert PA.validate_manifest(dict(base, approvals=[approval()])) == []
