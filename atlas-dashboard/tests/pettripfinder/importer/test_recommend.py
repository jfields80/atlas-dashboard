"""AES-DATA-001 -- recommendation logic unit tests (mission section 15)."""

from __future__ import annotations

from scripts.pettripfinder.importer import constants as C
from scripts.pettripfinder.importer.recommend import RecommendationInput, recommend


def _base(**kw):
    d = dict(
        fetch_ok=True, fetch_reason="", source_relationship=C.REL_EXACT_ENTITY_DOMAIN,
        entity_identified=True, category_resolved=True, missing_required=(),
        pet_policy_present=True, pets_allowed_state="true", has_material_conflict=False,
        multi_entity=False, required_evidence_mismatch=False, ambiguous_present=False,
        extraction_ok=True, text_truncated=False)
    d.update(kw)
    return RecommendationInput(**d)


def test_ready():
    rec, reasons = recommend(_base())
    assert rec == C.RECOMMEND_READY and reasons == ()


def test_blocked_review():
    rec, reasons = recommend(_base(fetch_ok=False, fetch_reason=C.REASON_BLOCKED_SOURCE))
    assert rec == C.RECOMMEND_REVIEW and reasons == (C.REASON_BLOCKED_SOURCE,)


def test_fetch_reject():
    rec, _ = recommend(_base(fetch_ok=False, fetch_reason=C.REASON_UNSAFE_HOST))
    assert rec == C.RECOMMEND_REJECT


def test_no_pets_reject():
    rec, reasons = recommend(_base(pets_allowed_state="false"))
    assert rec == C.RECOMMEND_REJECT and C.REASON_NO_PETS in reasons


def test_third_party_reject():
    rec, _ = recommend(_base(source_relationship=C.REL_THIRD_PARTY))
    assert rec == C.RECOMMEND_REJECT


def test_no_entity_reject():
    rec, _ = recommend(_base(entity_identified=False))
    assert rec == C.RECOMMEND_REJECT


def test_no_pet_evidence_reject():
    rec, reasons = recommend(_base(pet_policy_present=False, pets_allowed_state=""))
    assert rec == C.RECOMMEND_REJECT and C.REASON_NO_PET_EVIDENCE in reasons


def test_evidence_mismatch_reject():
    rec, _ = recommend(_base(required_evidence_mismatch=True))
    assert rec == C.RECOMMEND_REJECT


def test_conflict_review():
    rec, reasons = recommend(_base(has_material_conflict=True))
    assert rec == C.RECOMMEND_REVIEW and C.REASON_CONFLICTING_EVIDENCE in reasons


def test_multi_entity_review():
    rec, reasons = recommend(_base(multi_entity=True))
    assert rec == C.RECOMMEND_REVIEW and C.REASON_MULTI_ENTITY in reasons


def test_missing_required_review():
    rec, reasons = recommend(_base(missing_required=("address",)))
    assert rec == C.RECOMMEND_REVIEW
    assert any("address" in r for r in reasons)


def test_unknown_relationship_review():
    rec, reasons = recommend(_base(source_relationship=C.REL_UNKNOWN))
    assert rec == C.RECOMMEND_REVIEW and C.REASON_UNCERTAIN_SOURCE_RELATIONSHIP in reasons
