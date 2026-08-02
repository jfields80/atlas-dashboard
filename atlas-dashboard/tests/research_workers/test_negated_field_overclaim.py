"""PTF-WORKERS -- a model overclaim against an explicitly negated field is a
model-quality fault, not missing evidence.

"No breed or weight restrictions" is not a gap in the evidence. It IS the
evidence: the property is telling a guest there is no ceiling. When a model then
proposes a weight limit anyway, the validator rightly rejects it -- but that
rejection was mapped to INCOMPLETE_EXTRACTION, which reads "we failed to extract
a fact that exists" and is never waivable. A property that stated its policy
MORE completely than most was blocked for having done so.

These tests pin the narrowness far more than the exception. The claim is still
rejected, the positive value is still never published, and every neighbouring
failure mode -- silence, a wrong number against a real stated one, a genuine
contradiction -- must be completely unaffected.

Offline: no network, no model call, no production write.
"""

from __future__ import annotations

import pytest

from services.research_workers import routing as RT
from services.research_workers import vocabulary as V
from services.research_workers.contracts import (
    Assignment, SourceDocument, content_hash,
)
from services.research_workers.evidence_validator import (
    OVERCLAIM_AGAINST_NEGATION, explicitly_negated_fields, validate_proposal,
)
from services.research_workers.proposal import ModelProposal, RawFactClaim

URL = "https://ex.example/pets"

SONESTA_NO_LIMITS = (
    "Up to two well-mannered dogs per suite with no breed or weight restrictions; "
    "cats are not allowed; $75 fee per pet for stays up to 7 nights, $150 for longer stays")
SILENT_ON_WEIGHT = ("Pets are welcome at this property. Up to two pets per room. "
                    "A $50 fee applies per night.")
REAL_WEIGHT_LIMIT = ("Pets welcome. Maximum Pet Weight: 50 lbs. "
                     "Maximum Number of Pets in Room: 2. A $50 fee applies per night.")
NO_FEE = ("Pets are welcome at this property. Up to two pets per room. "
          "There is no pet fee.")


def _asg(text, url=URL, stype=V.SOURCE_OFFICIAL_PROPERTY):
    doc = SourceDocument(url, stype, "2026-08-02T00:00:00Z", "t", text,
                         content_hash(text), V.RETRIEVAL_OK)
    return Assignment("neg-1", "columbus-oh", "neg-1", "H", "1 St", url,
                      (url,), (doc,), V.POLICY_FIELDS, "t")


def _run(text, facts):
    asg = _asg(text)
    prop = ModelProposal(claims=tuple(RawFactClaim(*f) for f in facts), fee_terms=(),
                         ok=True, structured_output_valid=True, provider="openai", model="m")
    res = validate_proposal(asg, prop)
    env = RT.route_result(asg, res, run_id="r", observed_at="2026-08-02")
    return res, env


def _supported(res, field):
    return next((f.value for f in res.proposed_facts
                 if f.field_name == field and f.state == V.SUPPORTED), None)


def _rejections(res):
    return [w for w in res.warnings if w.startswith("rejected_")]


# --------------------------------------------------------------------------- #
# The detector itself.
# --------------------------------------------------------------------------- #

class TestNegationDetector:
    @pytest.mark.parametrize("text,field", [
        ("with no breed or weight restrictions", V.FIELD_WEIGHT_LIMIT),
        ("with no breed or weight restrictions", V.FIELD_BREED_RESTRICTIONS),
        ("There are no weight restrictions.", V.FIELD_WEIGHT_LIMIT),
        ("all breeds are welcome", V.FIELD_BREED_RESTRICTIONS),
        ("There is no pet fee.", V.FIELD_PET_FEE),
        ("Pets stay free.", V.FIELD_PET_FEE),
        ("no limit on the number of pets", V.FIELD_MAXIMUM_PETS),
    ])
    def test_explicit_negations_are_detected(self, text, field):
        assert field in explicitly_negated_fields(text)

    @pytest.mark.parametrize("text", [
        "Pets are welcome. Up to two pets per room.",          # silent on weight
        "Maximum Pet Weight: 50 lbs.",                          # a real limit
        "No smoking in guest rooms.",                           # a different negation
        "Pets are not allowed.",                                # negates PETS, not a field
        "",
    ])
    def test_silence_and_unrelated_negations_are_not_negation(self, text):
        assert V.FIELD_WEIGHT_LIMIT not in explicitly_negated_fields(text)

    def test_a_bare_no_never_negates(self):
        assert explicitly_negated_fields("no") == frozenset()
        assert explicitly_negated_fields("No.") == frozenset()


# --------------------------------------------------------------------------- #
# A-D. The required regression cases.
# --------------------------------------------------------------------------- #

class TestOverclaimClassification:
    def test_a_negated_weight_overclaim_is_a_model_quality_warning(self):
        """Sonesta: source says no weight restrictions, model proposes 50 lbs."""
        res, env = _run(SONESTA_NO_LIMITS, (
            (V.FIELD_PETS_ALLOWED, "true", "Up to two well-mannered dogs per suite", URL),
            (V.FIELD_WEIGHT_LIMIT, "50", "with no breed or weight restrictions", URL),
        ))
        assert ("rejected_%s:%s" % (V.FIELD_WEIGHT_LIMIT, OVERCLAIM_AGAINST_NEGATION)
                in res.warnings)                                   # rejected, and labelled
        assert RT.INCOMPLETE_EXTRACTION not in env.reason_codes    # not missing evidence
        assert RT.MODEL_OVERCLAIM in env.reason_codes              # still a recorded fault
        assert _supported(res, V.FIELD_WEIGHT_LIMIT) is None       # never published

    def test_a_the_source_supported_negative_fact_survives(self):
        res, _env = _run(SONESTA_NO_LIMITS, (
            (V.FIELD_PETS_ALLOWED, "true", "Up to two well-mannered dogs per suite", URL),
            (V.FIELD_BREED_RESTRICTIONS, "false", "with no breed or weight restrictions", URL),
            (V.FIELD_WEIGHT_LIMIT, "50", "with no breed or weight restrictions", URL),
        ))
        assert _supported(res, V.FIELD_BREED_RESTRICTIONS) == "false"
        assert _supported(res, V.FIELD_PETS_ALLOWED) == "true"

    def test_b_silence_is_not_negation_and_the_claim_is_still_rejected(self):
        """The source never mentions weight. That is unknown, not unlimited, so
        the NEGATION exception must not fire.

        Superseded in part: this claim is now an UNSUPPORTED_MODEL_CLAIM rather
        than an INCOMPLETE_EXTRACTION, because the source states nothing to
        extract. The claim is still rejected and the value still never
        publishes -- only the name of the fault changed.
        """
        res, env = _run(SILENT_ON_WEIGHT, (
            (V.FIELD_PETS_ALLOWED, "true", "Pets are welcome at this property", URL),
            (V.FIELD_WEIGHT_LIMIT, "50", "Pets are welcome at this property", URL),
        ))
        assert any(w.startswith("rejected_%s" % V.FIELD_WEIGHT_LIMIT) for w in res.warnings)
        assert OVERCLAIM_AGAINST_NEGATION not in " ".join(res.warnings)
        assert RT.MODEL_OVERCLAIM in env.reason_codes
        assert _supported(res, V.FIELD_WEIGHT_LIMIT) is None

    def test_c_a_wrong_number_against_a_real_limit_is_not_downgraded(self):
        """The source states 50 lbs; the model says 80. Catching it must not
        make it a lesser fault -- that is exactly the flattening-class error the
        never-waivable gate exists for."""
        res, env = _run(REAL_WEIGHT_LIMIT, (
            (V.FIELD_PETS_ALLOWED, "true", "Pets welcome", URL),
            (V.FIELD_WEIGHT_LIMIT, "80", "Maximum Pet Weight: 50 lbs", URL),
        ))
        assert ("rejected_%s:number_not_in_quote" % V.FIELD_WEIGHT_LIMIT) in res.warnings
        assert RT.INCOMPLETE_EXTRACTION in env.reason_codes
        assert _supported(res, V.FIELD_WEIGHT_LIMIT) is None

    def test_d_a_negated_fee_overclaim_is_handled_the_same_way(self):
        res, env = _run(NO_FEE, (
            (V.FIELD_PETS_ALLOWED, "true", "Pets are welcome at this property", URL),
            (V.FIELD_PET_FEE, "75", "There is no pet fee.", URL),
        ))
        assert ("rejected_%s:%s" % (V.FIELD_PET_FEE, OVERCLAIM_AGAINST_NEGATION)
                in res.warnings)
        assert RT.INCOMPLETE_EXTRACTION not in env.reason_codes
        assert _supported(res, V.FIELD_PET_FEE) is None


# --------------------------------------------------------------------------- #
# Narrowness. These matter more than the exception.
# --------------------------------------------------------------------------- #

class TestTheExceptionStaysNarrow:
    def test_it_never_clears_a_contradiction(self):
        text = SONESTA_NO_LIMITS + " Elsewhere the page states a maximum of 3 pets per suite."
        res, env = _run(text, (
            (V.FIELD_MAXIMUM_PETS, "2", "Up to two well-mannered dogs per suite", URL),
            (V.FIELD_MAXIMUM_PETS, "3", "a maximum of 3 pets per suite", URL),
        ))
        assert res.contradictions
        assert RT.CONTRADICTORY_OFFICIAL_SOURCES in env.reason_codes

    def test_it_never_fires_on_a_negative_claim(self):
        """A model AGREEING with the source is not overclaiming, so nothing is
        reclassified -- and the claim is accepted, not rejected."""
        res, _env = _run(SONESTA_NO_LIMITS, (
            (V.FIELD_BREED_RESTRICTIONS, "false", "with no breed or weight restrictions", URL),
        ))
        assert not any(OVERCLAIM_AGAINST_NEGATION in w for w in res.warnings)
        assert _supported(res, V.FIELD_BREED_RESTRICTIONS) == "false"

    def test_it_never_fires_for_a_field_the_source_did_not_negate(self):
        """The source negates WEIGHT; the model overclaims a COUNT. Only the
        negated field may be reclassified."""
        res, _env = _run(SONESTA_NO_LIMITS, (
            (V.FIELD_PETS_ALLOWED, "true", "Up to two well-mannered dogs per suite", URL),
            (V.FIELD_MAXIMUM_PETS, "9", "with no breed or weight restrictions", URL),
        ))
        # Rejected, and NOT under the negation exception -- the source negates
        # weight and breed, never the pet count.
        assert any(w.startswith("rejected_%s" % V.FIELD_MAXIMUM_PETS) for w in res.warnings)
        assert ("rejected_%s:%s" % (V.FIELD_MAXIMUM_PETS, OVERCLAIM_AGAINST_NEGATION)
                not in res.warnings)

    def test_a_record_with_nothing_supported_is_still_incomplete(self):
        """The exception reclassifies ONE rejected overclaim. It cannot make a
        record with no publishable fact look complete."""
        res, env = _run(SONESTA_NO_LIMITS, (
            (V.FIELD_WEIGHT_LIMIT, "50", "with no breed or weight restrictions", URL),
        ))
        assert not any(f.state == V.SUPPORTED for f in res.proposed_facts)
        assert env.route != RT.ROUTE_READY

    def test_never_waivable_codes_are_untouched(self):
        from scripts.pettripfinder.prod003_approvals import (
            NEVER_WAIVABLE_REASON_CODES, WAIVABLE_REASON_CODES,
        )
        assert WAIVABLE_REASON_CODES == frozenset({"STRUCTURED_FEE_REQUIRED"})
        for code in ("CONTRADICTORY_OFFICIAL_SOURCES", "INCOMPLETE_EXTRACTION",
                     "SOURCE_AUTHORITY_AMBIGUITY", "UNSAFE_RESULT",
                     "MODEL_RESEARCH_NOT_OFFICIAL_EVIDENCE",
                     "INHERITED_IDENTITY_REQUIRES_REVIEW"):
            assert code in NEVER_WAIVABLE_REASON_CODES

    def test_the_detector_names_no_brand(self):
        import inspect
        from services.research_workers import evidence_validator as EV
        src = (inspect.getsource(EV.explicitly_negated_fields)
               + inspect.getsource(EV._is_positive_restriction)).lower()
        for token in ("sonesta", "hyatt", "hilton", "marriott", "wyndham", ".com"):
            assert token not in src


class TestPromptHardening:
    def test_prompt_version_bumped(self):
        from services.research_workers.prompt import PROMPT_VERSION
        assert PROMPT_VERSION == "1.7.0"

    @pytest.mark.parametrize("phrase", [
        "NO RESTRICTION\" IS NOT \"NOT STATED",
        "NEVER propose a positive restriction",
        "Do not report silence as",
        "NEVER convert a COMBINED limit into a per-pet limit",
        "MUST be supported by a quote containing that exact number",
    ])
    def test_the_new_instructions_are_present(self, phrase):
        from services.research_workers.prompt import _SYSTEM_PROMPT
        assert phrase in _SYSTEM_PROMPT
