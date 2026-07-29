"""PTF-WORKERS-007 -- APPROVED_PAIRED_OFFICIAL_SOURCE.

The narrow, hash-bound decision that lets validated paired Marriott evidence
move from REVIEW to publication. It waives exactly one reason code, requires
all four binding signals, and is bound to three hashes: the identity capture,
the policy capture, and the attestation that joined them.

Offline: no network, no model call, no production write.
"""

from __future__ import annotations

import pytest

from scripts.pettripfinder import prod003_approvals as PA

H_ID = "a" * 64
H_POL = "b" * 64
H_ATT = "sha256:" + "c" * 64
PROPERTY_URL = "https://www.marriott.com/en-us/hotels/cmhea-aloft-columbus-easton/overview/"
SEARCH_URL = "https://www.marriott.com/search/findHotels.mi?propertyCode=cmhea"


def _approval(**over):
    base = {
        "listing_key": "aloft columbus easton",
        "listing_name": "Aloft Columbus Easton",
        "result_hash": "sha256:" + "d" * 64,
        "source_url": PROPERTY_URL,
        "verification_date": "2026-07-29",
        "gate1_route": "REVIEW",
        "decision": PA.DECISION_PAIRED_OFFICIAL_SOURCE,
        "operator": "jfields80",
        "approval_date": "2026-07-29",
        "waived_reason_codes": ["PAIRED_OFFICIAL_SOURCE_REQUIRES_REVIEW"],
        "identity_capture_url": PROPERTY_URL,
        "identity_text_hash": H_ID,
        "policy_capture_url": SEARCH_URL,
        "policy_text_hash": H_POL,
        "matched_signals": ["address_exact", "name_exact", "phone_exact",
                            "property_code"],
        "attestation_hash": H_ATT,
    }
    base.update(over)
    return base


def _manifest(**over):
    return {"schema": PA.SCHEMA_ID, "market": "columbus-oh",
            "pending_candidates": [], "approvals": [_approval(**over)]}


def _errors(**over):
    """Approval-level errors only -- manifest-level slugs are covered by the
    existing prod003 tests and would just add noise here."""
    return [e for e in PA.validate_manifest(_manifest(**over))
            if e.startswith("approval[")]


class TestDecisionVocabulary:
    def test_decision_is_allowed(self):
        assert PA.DECISION_PAIRED_OFFICIAL_SOURCE in PA.ALLOWED_DECISIONS

    def test_waives_exactly_one_reason_code(self):
        assert PA.PAIRED_WAIVABLE_REASON_CODES == frozenset(
            {"PAIRED_OFFICIAL_SOURCE_REQUIRES_REVIEW"})

    def test_the_two_waiver_sets_are_disjoint(self):
        """Neither decision may ever clear the other's blocker."""
        assert not (PA.WAIVABLE_REASON_CODES & PA.PAIRED_WAIVABLE_REASON_CODES)

    def test_never_waivable_set_is_untouched(self):
        for code in ("CONTRADICTORY_OFFICIAL_SOURCES", "INCOMPLETE_EXTRACTION",
                     "SOURCE_AUTHORITY_AMBIGUITY", "UNSAFE_RESULT",
                     "MODEL_RESEARCH_NOT_OFFICIAL_EVIDENCE",
                     "INHERITED_IDENTITY_REQUIRES_REVIEW"):
            assert code in PA.NEVER_WAIVABLE_REASON_CODES
            assert code not in PA.PAIRED_WAIVABLE_REASON_CODES

    def test_all_four_signals_are_required_by_contract(self):
        assert set(PA.REQUIRED_BINDING_SIGNALS) == {
            "address_exact", "name_exact", "phone_exact", "property_code"}


class TestValidApproval:
    def test_well_formed_approval_validates(self):
        assert _errors() == []

    def test_paired_fields_are_permitted_only_on_this_decision(self):
        errs = _errors(decision=PA.DECISION_APPROVED, gate1_route="READY")
        assert any("unexpected_fields" in e for e in errs)


class TestFailsClosed:
    def test_ready_route_has_nothing_to_waive(self):
        assert any("paired_source_requires_review_route" in e
                   for e in _errors(gate1_route="READY"))

    def test_missing_one_signal_is_refused(self):
        errs = _errors(matched_signals=["address_exact", "name_exact", "phone_exact"])
        assert any("missing_binding_signals:property_code" in e for e in errs)

    def test_no_signals_is_refused(self):
        assert any("missing_binding_signals" in e for e in _errors(matched_signals=[]))

    def test_cannot_waive_an_unrelated_code(self):
        errs = _errors(waived_reason_codes=["CONTRADICTORY_OFFICIAL_SOURCES"])
        assert any("non_waivable_reason_codes:CONTRADICTORY_OFFICIAL_SOURCES" in e
                   for e in errs)

    def test_cannot_waive_the_fee_code(self):
        errs = _errors(waived_reason_codes=["STRUCTURED_FEE_REQUIRED"])
        assert any("non_waivable_reason_codes:STRUCTURED_FEE_REQUIRED" in e for e in errs)

    def test_empty_waiver_list_is_refused(self):
        assert any("requires_waived_reason_codes" in e for e in _errors(waived_reason_codes=[]))

    @pytest.mark.parametrize("field", ["identity_text_hash", "policy_text_hash",
                                       "attestation_hash"])
    def test_every_hash_must_be_a_sha256(self, field):
        assert any("invalid_%s" % field in e for e in _errors(**{field: "not-a-hash"}))

    def test_identical_capture_hashes_refused(self):
        """One capture cited twice would be its own corroboration."""
        assert any("identity_and_policy_captures_identical" in e
                   for e in _errors(identity_text_hash=H_POL))

    def test_source_url_must_be_the_property_page(self):
        errs = _errors(source_url=SEARCH_URL)
        assert any("source_url_must_be_the_identity_capture" in e for e in errs)

    def test_both_capture_urls_required(self):
        assert any("requires_both_capture_urls" in e for e in _errors(policy_capture_url=""))

    def test_launch_safe_record_cannot_take_a_paired_waiver(self):
        """The waiver exists for a manual-review record; on a launch-safe one
        it would be a rubber stamp."""
        idx = {"aloft columbus easton": {"result_hash": _approval()["result_hash"],
                                         "launch_safe": True}}
        errs = PA.validate_manifest(_manifest(), gate1_idx=idx)
        assert any("paired_source_requires_manual_review_record" in e for e in errs)

    def test_stale_result_hash_is_refused(self):
        """Hash-bound: the approval must name the exact Gate-1 record it was
        granted against."""
        idx = {"aloft columbus easton": {"result_hash": "sha256:" + "9" * 64,
                                         "launch_safe": False}}
        errs = PA.validate_manifest(_manifest(), gate1_idx=idx)
        assert any("stale_result_hash" in e for e in errs)

    def test_manual_review_record_accepts_the_waiver(self):
        idx = {"aloft columbus easton": {"result_hash": _approval()["result_hash"],
                                         "launch_safe": False}}
        errs = [e for e in PA.validate_manifest(_manifest(), gate1_idx=idx)
                if e.startswith("approval[")]
        assert errs == []
