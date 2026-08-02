"""PTF-WORKERS -- an invented fact is not a missing one.

INCOMPLETE_EXTRACTION conflated two opposite failures:

    "a fact exists in the source and we failed to carry it through"
    "the model asserted a fact the source never states"

Only the first is a gap in our pipeline, and only the first deserves a
never-waivable gate. The second is the airlock WORKING -- it caught an
invention -- and a record was being held for its own defence.

The two are told apart by asking the SOURCE, never the model: does the
authoritative text speak to this field at all? Silence means there was nothing
to extract, so a rejection there is an overclaim. A source that quantifies the
field means a real stated fact was missed or mangled, and that keeps its
original weight.

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
    UNSUPPORTED_MODEL_CLAIM, validate_proposal,
)
from services.research_workers.providers import fields_stated_by_source
from services.research_workers.proposal import ModelProposal, RawFactClaim

URL = "https://ex.example/pets"

#: Silent on weight and on fee basis; states a fee ladder, species and breed.
SONESTA = ("Up to two well-mannered dogs per suite with no breed or weight restrictions; "
           "cats are not allowed; $75 fee per pet for stays up to 7 nights, $150 for longer stays")
#: States a basis explicitly.
PER_STAY = ("Pets welcome. A pet fee of $50 applies per stay. "
            "Maximum Number of Pets in Room: 2.")
#: States a real numeric weight limit.
REAL_WEIGHT = "Pets welcome. Maximum Pet Weight: 50 lbs. A $50 fee applies per night."
#: Says nothing about weight at all.
SILENT_WEIGHT = "Pets are welcome at this property. Up to two pets per room."


def _asg(text):
    d = SourceDocument(URL, V.SOURCE_OFFICIAL_PROPERTY, "2026-08-02T00:00:00Z", "t",
                       text, content_hash(text), V.RETRIEVAL_OK)
    return Assignment("oc-1", "columbus-oh", "oc-1", "H", "1 St", URL, (URL,), (d,),
                      V.POLICY_FIELDS, "t")


def _run(text, claims):
    a = _asg(text)
    res = validate_proposal(a, ModelProposal(
        claims=tuple(RawFactClaim(*c) for c in claims), fee_terms=(), ok=True,
        structured_output_valid=True, provider="openai", model="m"))
    return res, RT.route_result(a, res, run_id="r", observed_at="2026-08-02")


def _supported(res, field):
    return next((f.value for f in res.proposed_facts
                 if f.field_name == field and f.state == V.SUPPORTED), None)


class TestSourceStatedFieldsReader:
    def test_silence_is_reported_as_silence(self):
        assert V.FIELD_WEIGHT_LIMIT not in fields_stated_by_source(
            _asg(SILENT_WEIGHT).source_documents)

    def test_a_stated_numeric_limit_is_seen(self):
        assert V.FIELD_WEIGHT_LIMIT in fields_stated_by_source(
            _asg(REAL_WEIGHT).source_documents)

    def test_a_stated_basis_is_seen(self):
        assert V.FIELD_FEE_BASIS in fields_stated_by_source(
            _asg(PER_STAY).source_documents)

    def test_an_unusable_source_is_never_read(self):
        d = SourceDocument(URL, V.SOURCE_OFFICIAL_PROPERTY, "t", "t", REAL_WEIGHT,
                           content_hash(REAL_WEIGHT), "ERROR")
        assert fields_stated_by_source((d,)) == frozenset()


class TestRequiredCases:
    def test_a_invented_fee_basis_is_an_overclaim_not_incomplete(self):
        res, env = _run(SONESTA, (
            (V.FIELD_PETS_ALLOWED, "true", "Up to two well-mannered dogs per suite", URL),
            (V.FIELD_FEE_BASIS, "per_night", "$75 fee per pet for stays up to 7 nights", URL),
        ))
        assert ("rejected_%s:%s" % (V.FIELD_FEE_BASIS, UNSUPPORTED_MODEL_CLAIM)
                in res.warnings)
        assert RT.MODEL_OVERCLAIM in env.reason_codes
        assert RT.INCOMPLETE_EXTRACTION not in env.reason_codes
        assert _supported(res, V.FIELD_FEE_BASIS) is None       # never published

    def test_a_the_fee_ladder_survives_and_is_the_only_reason(self):
        """The clean state: source-supported facts preserved, the invention
        removed, and MODEL_OVERCLAIM the sole remaining issue."""
        res, env = _run(SONESTA, (
            (V.FIELD_PETS_ALLOWED, "true", "Up to two well-mannered dogs per suite", URL),
            (V.FIELD_FEE_BASIS, "per_night", "$75 fee per pet for stays up to 7 nights", URL),
        ))
        assert res.fee_policy is not None
        assert [(t.amount, t.condition_min, t.condition_max) for t in res.fee_policy.terms] == [
            ("75.00", 1, 7), ("150.00", 8, None)]
        assert set(env.reason_codes) == {RT.MODEL_OVERCLAIM}
        assert res.contradictions == ()

    def test_b_a_stated_basis_the_model_omits_stays_incomplete(self):
        """Nothing rejected, but a source-stated fact never reaches the output."""
        res, _env = _run(PER_STAY, (
            (V.FIELD_PETS_ALLOWED, "true", "Pets welcome", URL),
        ))
        assert V.FIELD_FEE_BASIS in fields_stated_by_source(_asg(PER_STAY).source_documents)
        assert _supported(res, V.FIELD_FEE_BASIS) is None

    def test_c_a_wrong_basis_against_a_stated_one_stays_incomplete(self):
        """The source says per stay. Proposing per_night is a MANGLED real fact,
        not an invention, and must not be downgraded."""
        res, env = _run(PER_STAY, (
            (V.FIELD_PETS_ALLOWED, "true", "Pets welcome", URL),
            (V.FIELD_FEE_BASIS, "per_night", "A pet fee of $50 applies per stay", URL),
        ))
        assert ("rejected_%s:fee_basis_phrase_absent" % V.FIELD_FEE_BASIS) in res.warnings
        assert RT.INCOMPLETE_EXTRACTION in env.reason_codes
        assert RT.MODEL_OVERCLAIM not in env.reason_codes

    def test_d_an_invented_weight_is_an_overclaim(self):
        res, env = _run(SILENT_WEIGHT, (
            (V.FIELD_PETS_ALLOWED, "true", "Pets are welcome at this property", URL),
            (V.FIELD_WEIGHT_LIMIT, "50", "Pets are welcome at this property", URL),
        ))
        assert ("rejected_%s:%s" % (V.FIELD_WEIGHT_LIMIT, UNSUPPORTED_MODEL_CLAIM)
                in res.warnings)
        assert RT.MODEL_OVERCLAIM in env.reason_codes
        assert RT.INCOMPLETE_EXTRACTION not in env.reason_codes
        assert _supported(res, V.FIELD_WEIGHT_LIMIT) is None

    def test_e_a_wrong_number_against_a_real_limit_stays_incomplete(self):
        res, env = _run(REAL_WEIGHT, (
            (V.FIELD_PETS_ALLOWED, "true", "Pets welcome", URL),
            (V.FIELD_WEIGHT_LIMIT, "80", "Maximum Pet Weight: 50 lbs", URL),
        ))
        assert ("rejected_%s:number_not_in_quote" % V.FIELD_WEIGHT_LIMIT) in res.warnings
        assert RT.INCOMPLETE_EXTRACTION in env.reason_codes
        assert RT.MODEL_OVERCLAIM not in env.reason_codes


class TestNegationBeatsMention:
    def test_a_negated_field_is_not_a_stated_one(self):
        """"no weight restrictions" MENTIONS weight and states that there is no
        value. Counting the mention would make every rejected weight claim look
        like a real fact we mangled."""
        from services.research_workers.evidence_validator import explicitly_negated_fields
        docs = _asg(SONESTA).source_documents
        assert V.FIELD_WEIGHT_LIMIT in fields_stated_by_source(docs)      # mentioned
        assert V.FIELD_WEIGHT_LIMIT in explicitly_negated_fields(SONESTA)  # and negated

    @pytest.mark.parametrize("value", ["50", "no weight limit", "none"])
    def test_no_weight_claim_on_a_negating_source_is_ever_incomplete(self, value):
        """Positive, unparseable, or sentinel -- none of them can be a MISSED
        fact, because the source says there is no fact to miss. In every case
        the claim is discarded, nothing is published, and the never-waivable
        INCOMPLETE_EXTRACTION never appears."""
        res, env = _run(SONESTA, (
            (V.FIELD_PETS_ALLOWED, "true", "Up to two well-mannered dogs per suite", URL),
            (V.FIELD_WEIGHT_LIMIT, value, "with no breed or weight restrictions", URL),
        ))
        assert RT.INCOMPLETE_EXTRACTION not in env.reason_codes
        assert _supported(res, V.FIELD_WEIGHT_LIMIT) is None
        # The discard is always recorded, whether as a rejection or a
        # normalization -- never silently dropped.
        assert any(V.FIELD_WEIGHT_LIMIT in w for w in res.warnings)

    @pytest.mark.parametrize("value", ["50", "no weight limit"])
    def test_a_rejected_weight_claim_reports_as_an_overclaim(self, value):
        """A value the validator REJECTS reports MODEL_OVERCLAIM. A recognised
        absence sentinel is normalized away instead, so it produces no
        rejection at all and the record is not held for one."""
        _res, env = _run(SONESTA, (
            (V.FIELD_PETS_ALLOWED, "true", "Up to two well-mannered dogs per suite", URL),
            (V.FIELD_WEIGHT_LIMIT, value, "with no breed or weight restrictions", URL),
        ))
        assert RT.MODEL_OVERCLAIM in env.reason_codes


class TestNothingElseWeakened:
    def test_model_overclaim_never_clears_a_contradiction(self):
        text = SONESTA + " Elsewhere the page states a maximum of 3 pets per suite."
        res, env = _run(text, (
            (V.FIELD_MAXIMUM_PETS, "2", "Up to two well-mannered dogs per suite", URL),
            (V.FIELD_MAXIMUM_PETS, "3", "a maximum of 3 pets per suite", URL),
        ))
        assert res.contradictions
        assert RT.CONTRADICTORY_OFFICIAL_SOURCES in env.reason_codes

    def test_a_record_with_nothing_supported_is_still_incomplete(self):
        _res, env = _run(SILENT_WEIGHT, (
            (V.FIELD_WEIGHT_LIMIT, "50", "Pets are welcome at this property", URL),
        ))
        assert RT.INCOMPLETE_EXTRACTION in env.reason_codes
        assert env.route != RT.ROUTE_READY

    def test_a_fabricated_quote_is_still_an_evidence_mismatch(self):
        """A quote that is not in the document at all is a different and more
        serious fault; it must not be softened into an overclaim."""
        res, env = _run(SILENT_WEIGHT, (
            (V.FIELD_PETS_ALLOWED, "true", "Pets are welcome at this property", URL),
            (V.FIELD_WEIGHT_LIMIT, "50", "Maximum Pet Weight: 50 lbs", URL),
        ))
        assert any("quote_not_verbatim" in w for w in res.warnings)
        assert RT.EXACT_EVIDENCE_MISMATCH in env.reason_codes

    def test_model_overclaim_is_a_review_reason_and_never_ready(self):
        assert RT.MODEL_OVERCLAIM in RT.REVIEW_REASONS
        assert RT.MODEL_OVERCLAIM not in RT.READY_REASONS

    def test_never_waivable_set_is_unchanged(self):
        from scripts.pettripfinder.prod003_approvals import (
            NEVER_WAIVABLE_REASON_CODES, WAIVABLE_REASON_CODES,
        )
        assert WAIVABLE_REASON_CODES == frozenset({"STRUCTURED_FEE_REQUIRED"})
        assert "INCOMPLETE_EXTRACTION" in NEVER_WAIVABLE_REASON_CODES
        assert "CONTRADICTORY_OFFICIAL_SOURCES" in NEVER_WAIVABLE_REASON_CODES
        # MODEL_OVERCLAIM is deliberately in NEITHER set until an operator
        # decides how it may be disposed of.
        assert "MODEL_OVERCLAIM" not in NEVER_WAIVABLE_REASON_CODES
        assert "MODEL_OVERCLAIM" not in WAIVABLE_REASON_CODES


class TestDiagnosticsAreNotFaults:
    def test_ladder_diagnostics_do_not_become_reason_codes(self):
        """Writing down HOW we read the evidence must not hold the record."""
        res, env = _run(SONESTA, (
            (V.FIELD_PETS_ALLOWED, "true", "Up to two well-mannered dogs per suite", URL),
        ))
        assert any(w.startswith("stay_length_ladder_read_from_source") for w in res.warnings)
        assert RT.VALIDATOR_WARNING not in env.reason_codes

    @pytest.mark.parametrize("prefix", [
        "multi_term_fee_amounts",
        "stay_length_ladder_read_from_source",
        "stay_length_ladder_supersedes_scalar",
    ])
    def test_declared_diagnostic_prefixes(self, prefix):
        assert prefix in RT._DIAGNOSTIC_WARNING_PREFIXES
