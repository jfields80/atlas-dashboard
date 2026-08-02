"""PTF-WORKERS -- approving a record whose only remaining reason is a diagnostic.

MODEL_OVERCLAIM records that an unsupported model claim was CAUGHT, rejected and
removed. There is no bad fact left in the record to waive -- the record is sound
BECAUSE the claim is gone. Filing it under WAIVABLE_REASON_CODES would say the
opposite; filing it under NEVER_WAIVABLE would hold a clean record forever over
a note about a claim that never reached it.

So it lives in a third category, and its approval is called an acknowledgement
rather than a waiver. The tests below care far more about what the decision
CANNOT do than about what it can.

Offline: no network, no model call, no production write.
"""

from __future__ import annotations

import pytest

from scripts.pettripfinder import prod003_approvals as PA

_BASE = {
    "listing_key": "sonesta simply suites dublin columbus",
    "listing_name": "Sonesta Simply Suites Dublin Columbus",
    "result_hash": "sha256:" + "a" * 64,
    "source_url": "https://ex.example/property",
    "verification_date": "2026-08-02",
    "gate1_route": "REVIEW",
    "decision": PA.DECISION_DIAGNOSTIC_ACKNOWLEDGED,
    "operator": "jfields80",
    "approval_date": "2026-08-02",
    "acknowledged_reason_codes": ["MODEL_OVERCLAIM"],
    "acknowledged_warnings": ["rejected_fee_basis:unsupported_model_claim"],
}


def _manifest(approval):
    return {"schema": PA.SCHEMA_ID, "market": "columbus-oh",
            "approvals": [approval], "pending_candidates": [],
            "bound_to": {"frozen_worker_commit": "c" * 40,
                         "gate1_commit": "g" * 40,
                         "gate1_manifest_sha256": "h" * 64}}


def _errors(approval, **kw):
    return list(PA.validate_manifest(_manifest(approval), **kw))


def _with(**kw):
    a = dict(_BASE)
    a.update(kw)
    return a


# --------------------------------------------------------------------------- #
# The category itself.
# --------------------------------------------------------------------------- #

class TestTheThirdCategory:
    def test_model_overclaim_is_approval_eligible_not_waivable(self):
        assert "MODEL_OVERCLAIM" in PA.APPROVAL_ELIGIBLE_WARNING_CODES
        assert "MODEL_OVERCLAIM" not in PA.WAIVABLE_REASON_CODES
        assert "MODEL_OVERCLAIM" not in PA.NEVER_WAIVABLE_REASON_CODES

    def test_e_existing_waivable_and_never_waivable_sets_are_unchanged(self):
        assert PA.WAIVABLE_REASON_CODES == frozenset({"STRUCTURED_FEE_REQUIRED"})
        assert PA.PAIRED_WAIVABLE_REASON_CODES == frozenset(
            {"PAIRED_OFFICIAL_SOURCE_REQUIRES_REVIEW"})
        assert PA.NEVER_WAIVABLE_REASON_CODES == frozenset({
            "CONTRADICTORY_OFFICIAL_SOURCES", "INCOMPLETE_EXTRACTION",
            "SOURCE_AUTHORITY_AMBIGUITY", "MODEL_RESEARCH_NOT_OFFICIAL_EVIDENCE",
            "INHERITED_IDENTITY_REQUIRES_REVIEW", "UNSAFE_RESULT"})

    def test_the_three_categories_do_not_overlap(self):
        assert not (PA.WAIVABLE_REASON_CODES & PA.NEVER_WAIVABLE_REASON_CODES)
        assert not (PA.APPROVAL_ELIGIBLE_WARNING_CODES & PA.WAIVABLE_REASON_CODES)
        assert not (PA.APPROVAL_ELIGIBLE_WARNING_CODES & PA.NEVER_WAIVABLE_REASON_CODES)

    def test_the_decision_is_not_named_a_waiver(self):
        assert PA.DECISION_DIAGNOSTIC_ACKNOWLEDGED == "APPROVE_WITH_DIAGNOSTIC_ACKNOWLEDGEMENT"
        assert "WAIV" not in PA.DECISION_DIAGNOSTIC_ACKNOWLEDGED.upper()
        assert PA.DECISION_DIAGNOSTIC_ACKNOWLEDGED in PA.ALLOWED_DECISIONS


# --------------------------------------------------------------------------- #
# A. A well-formed acknowledgement.
# --------------------------------------------------------------------------- #

class TestWellFormedAcknowledgement:
    def test_a_a_valid_acknowledgement_passes_the_contract(self):
        assert _errors(_BASE) == []

    def test_a_the_warning_must_be_carried_verbatim(self):
        """The point of the decision is that the diagnostic SURVIVES approval."""
        assert any("diagnostic_ack_requires_warnings" in e
                   for e in _errors(_with(acknowledged_warnings=[])))

    def test_a_the_reason_codes_must_be_named(self):
        assert any("diagnostic_ack_requires_reason_codes" in e
                   for e in _errors(_with(acknowledged_reason_codes=[])))

    def test_a_the_operator_and_date_are_still_human_supplied(self):
        for field in ("operator", "approval_date"):
            assert any(("missing_%s" % field) in e for e in _errors(_with(**{field: ""})))


# --------------------------------------------------------------------------- #
# B-D. What the acknowledgement CANNOT do.
# --------------------------------------------------------------------------- #

class TestItCannotClearAnythingElse:
    @pytest.mark.parametrize("code", [
        "INCOMPLETE_EXTRACTION",                  # B
        "CONTRADICTORY_OFFICIAL_SOURCES",         # C
        "INHERITED_IDENTITY_REQUIRES_REVIEW",     # D (identity)
        "SOURCE_AUTHORITY_AMBIGUITY",             # D (source authority)
        "UNSAFE_RESULT",
        "STRUCTURED_FEE_REQUIRED",                # a real waiver's code
    ])
    def test_it_may_not_acknowledge_a_blocking_code(self, code):
        errs = _errors(_with(acknowledged_reason_codes=["MODEL_OVERCLAIM", code]))
        assert any("not_approval_eligible_reason_codes" in e for e in errs), code

    def test_it_may_not_be_used_on_a_ready_record(self):
        """A READY record has no diagnostic to acknowledge; allowing it would
        turn the decision into a general-purpose rubber stamp."""
        errs = _errors(_with(gate1_route="READY"))
        assert any("diagnostic_ack_requires_review_route" in e for e in errs)

    def test_it_may_not_carry_waiver_fields(self):
        errs = _errors(_with(waived_reason_codes=["STRUCTURED_FEE_REQUIRED"]))
        assert any("unexpected_fields" in e for e in errs)

    def test_other_decisions_may_not_carry_acknowledgement_fields(self):
        a = _with(decision=PA.DECISION_APPROVED, gate1_route="READY")
        assert any("unexpected_fields" in e for e in _errors(a))
