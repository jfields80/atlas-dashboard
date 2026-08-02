"""PTF-WORKERS -- a species the source never names is an invention, not a gap.

Rule 11 forbids generic-to-specific species inference in both directions:
"pets welcome" never establishes DOGS, and "no pets" never establishes that
dogs are refused. That rule is untouched here and the claim is always rejected.

What changes is what the rejection MEANS, and the source decides:

  the source never names the species -> the model invented it and the airlock
      caught it. The sanitized record says "not stated", which is precisely
      what the page says. MODEL_OVERCLAIM.
  the source DOES name the species -> the model contradicted or mangled a real
      statement. Far more serious, and it keeps UNSUPPORTED_INFERENCE.

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

#: Sonesta, verbatim. Names pets and cats; never says "dog".
PETS_AND_NO_CATS = (
    "Sonesta Simply Suites Dublin Columbus is pet-friendly and welcomes well-mannered "
    "pets, with no breed or weight restrictions. Up to two pets are permitted per suite. "
    "We apologize as cats are not permitted. $75 fee, per pet, applies for stays up to "
    "7 nights; $150 for all longer stays.")
PETS_ONLY = "Pets are welcome at this property. Up to two pets are permitted per room."
DOGS_WELCOME = ("Dogs are welcome at this property. Up to two dogs are permitted per room. "
                "A $50 fee applies per night.")
DOGS_PROHIBITED = ("Pets are welcome at this property, but dogs are not permitted. "
                   "Up to two pets are permitted per room.")


def _asg(text):
    d = SourceDocument(URL, V.SOURCE_OFFICIAL_PROPERTY, "2026-08-02T00:00:00Z", "t",
                       text, content_hash(text), V.RETRIEVAL_OK)
    return Assignment("sp-1", "columbus-oh", "sp-1", "H", "1 St", URL, (URL,), (d,),
                      V.POLICY_FIELDS, "t")


def _run(text, claims):
    a = _asg(text)
    res = validate_proposal(a, ModelProposal(
        claims=tuple(RawFactClaim(*c) for c in claims), fee_terms=(), ok=True,
        structured_output_valid=True, provider="openai", model="m"))
    return res, RT.route_result(a, res, run_id="r", observed_at="2026-08-02")


def _state(res, field):
    return next((f.state for f in res.proposed_facts if f.field_name == field), None)


def _value(res, field):
    return next((f.value for f in res.proposed_facts
                 if f.field_name == field and f.state == V.SUPPORTED), None)


# --------------------------------------------------------------------------- #
# A. The Sonesta case.
# --------------------------------------------------------------------------- #

class TestSilentSpeciesIsAnOverclaim:
    def _sonesta(self):
        return _run(PETS_AND_NO_CATS, (
            (V.FIELD_PETS_ALLOWED, "true", "welcomes well-mannered pets", URL),
            (V.FIELD_CATS_ACCEPTED, "false", "cats are not permitted", URL),
            (V.FIELD_MAXIMUM_PETS, "2", "Up to two pets are permitted per suite.", URL),
            (V.FIELD_BREED_RESTRICTIONS, "false", "with no breed or weight restrictions", URL),
            (V.FIELD_DOGS_ACCEPTED, "true", "Up to two pets are permitted per suite.", URL),
        ))

    def test_the_source_never_names_dogs(self):
        assert V.FIELD_DOGS_ACCEPTED not in fields_stated_by_source(
            _asg(PETS_AND_NO_CATS).source_documents)
        assert V.FIELD_CATS_ACCEPTED in fields_stated_by_source(
            _asg(PETS_AND_NO_CATS).source_documents)

    def test_a_the_dogs_claim_is_removed_and_reported_as_an_overclaim(self):
        res, env = self._sonesta()
        w = next(w for w in res.warnings if w.startswith("rejected_dogs_accepted:"))
        assert w.split(":")[1] == UNSUPPORTED_MODEL_CLAIM
        assert RT.MODEL_OVERCLAIM in env.reason_codes
        assert RT.UNSUPPORTED_INFERENCE not in env.reason_codes

    def test_a_the_sanitized_output_says_what_the_page_says(self):
        res, _env = self._sonesta()
        assert _value(res, V.FIELD_PETS_ALLOWED) == "true"
        assert _value(res, V.FIELD_CATS_ACCEPTED) == "false"
        assert _value(res, V.FIELD_DOGS_ACCEPTED) is None          # never published
        assert _state(res, V.FIELD_DOGS_ACCEPTED) == V.NOT_STATED
        assert _value(res, V.FIELD_MAXIMUM_PETS) == "2"
        assert _value(res, V.FIELD_BREED_RESTRICTIONS) == "false"

    def test_a_the_diagnostic_is_the_only_reason(self):
        _res, env = self._sonesta()
        assert set(env.reason_codes) == {RT.MODEL_OVERCLAIM}

    def test_a_the_fee_ladder_survives_with_its_stated_scope(self):
        res, _env = self._sonesta()
        assert [(t.amount, t.condition_min, t.condition_max, t.scope)
                for t in res.fee_policy.terms] == [
            ("75.00", 1, 7, V.FEE_SCOPE_PER_PET),
            ("150.00", 8, None, V.FEE_SCOPE_UNSTATED)]

    def test_a_the_provenance_records_field_value_and_reason(self):
        """An approver acknowledging this diagnostic must be able to see WHAT
        was claimed and WHICH gate refused it -- not merely that something was
        discarded."""
        res, _env = self._sonesta()
        w = next(w for w in res.warnings if w.startswith("rejected_dogs_accepted:"))
        parts = w.split(":")
        assert parts[0] == "rejected_dogs_accepted"          # the field
        assert parts[1] == UNSUPPORTED_MODEL_CLAIM           # the classification
        assert parts[2] == "species_not_in_quote"            # the rule that fired
        assert parts[3] == "value=true"                      # the value refused
        assert res.contradictions == ()


# --------------------------------------------------------------------------- #
# B-D. Everything else is unchanged.
# --------------------------------------------------------------------------- #

class TestTheRuleItselfIsUnchanged:
    def test_b_a_stated_species_the_model_omits_is_never_credited(self):
        """The source names dogs; the model says nothing about them. That is not
        an overclaim -- nothing was claimed -- so no diagnostic is produced and
        the field simply does not publish."""
        res, env = _run(DOGS_WELCOME, (
            (V.FIELD_PETS_ALLOWED, "true", "Dogs are welcome at this property", URL),
        ))
        assert V.FIELD_DOGS_ACCEPTED in fields_stated_by_source(
            _asg(DOGS_WELCOME).source_documents)
        assert RT.MODEL_OVERCLAIM not in env.reason_codes
        assert _value(res, V.FIELD_DOGS_ACCEPTED) is None

    def test_c_a_species_the_source_names_is_not_downgraded(self):
        """"dogs are not permitted" is a real statement. A dogs claim against it
        is a contradiction or a mangled fact -- never a silent-source invention,
        and never MODEL_OVERCLAIM-only approval."""
        assert V.FIELD_DOGS_ACCEPTED in fields_stated_by_source(
            _asg(DOGS_PROHIBITED).source_documents)
        res, env = _run(DOGS_PROHIBITED, (
            (V.FIELD_PETS_ALLOWED, "true", "Pets are welcome at this property", URL),
            (V.FIELD_DOGS_ACCEPTED, "true", "Up to two pets are permitted per room.", URL),
        ))
        assert ("rejected_%s:species_not_in_quote" % V.FIELD_DOGS_ACCEPTED) in res.warnings
        assert RT.UNSUPPORTED_INFERENCE in env.reason_codes
        assert set(env.reason_codes) != {RT.MODEL_OVERCLAIM}
        assert _value(res, V.FIELD_DOGS_ACCEPTED) is None

    def test_d_both_invented_species_are_removed_and_both_reported(self):
        res, env = _run(PETS_ONLY, (
            (V.FIELD_PETS_ALLOWED, "true", "Pets are welcome at this property", URL),
            (V.FIELD_DOGS_ACCEPTED, "true", "Pets are welcome at this property", URL),
            (V.FIELD_CATS_ACCEPTED, "true", "Pets are welcome at this property", URL),
        ))
        for field in (V.FIELD_DOGS_ACCEPTED, V.FIELD_CATS_ACCEPTED):
            w = next(w for w in res.warnings if w.startswith("rejected_%s:" % field))
            assert w.split(":")[1] == UNSUPPORTED_MODEL_CLAIM
            assert "species_not_in_quote" in w                # the rule is preserved
            assert _value(res, field) is None
            assert _state(res, field) == V.NOT_STATED
        assert RT.MODEL_OVERCLAIM in env.reason_codes
        assert _value(res, V.FIELD_PETS_ALLOWED) == "true"

    @pytest.mark.parametrize("text,claim_field,claim_value", [
        # pets allowed -> dogs allowed
        (PETS_ONLY, V.FIELD_DOGS_ACCEPTED, "true"),
        # pets allowed -> cats allowed
        (PETS_ONLY, V.FIELD_CATS_ACCEPTED, "true"),
        # no pets -> a specific species stance
        ("Pets are not allowed at this property.", V.FIELD_DOGS_ACCEPTED, "false"),
    ])
    def test_no_generic_to_specific_inference_ever_publishes(self, text, claim_field, claim_value):
        res, _env = _run(text, (
            (claim_field, claim_value, text.split(".")[0], URL),
        ))
        assert _value(res, claim_field) is None

    def test_e_other_rejection_gates_are_untouched(self):
        # A fabricated quote is an evidence mismatch, never an overclaim.
        res, env = _run(PETS_ONLY, (
            (V.FIELD_PETS_ALLOWED, "true", "Pets are welcome at this property", URL),
            (V.FIELD_DOGS_ACCEPTED, "true", "Dogs are welcome at this property", URL),
        ))
        assert any("quote_not_verbatim" in w for w in res.warnings)
        assert RT.EXACT_EVIDENCE_MISMATCH in env.reason_codes

    def test_e_a_contradiction_still_dominates(self):
        text = PETS_AND_NO_CATS + " Elsewhere the page states a maximum of 3 pets per suite."
        res, env = _run(text, (
            (V.FIELD_MAXIMUM_PETS, "2", "Up to two pets are permitted per suite.", URL),
            (V.FIELD_MAXIMUM_PETS, "3", "a maximum of 3 pets per suite", URL),
        ))
        assert res.contradictions
        assert RT.CONTRADICTORY_OFFICIAL_SOURCES in env.reason_codes

    def test_e_an_empty_record_is_still_incomplete(self):
        _res, env = _run(PETS_ONLY, (
            (V.FIELD_DOGS_ACCEPTED, "true", "Pets are welcome at this property", URL),
        ))
        assert RT.INCOMPLETE_EXTRACTION in env.reason_codes
