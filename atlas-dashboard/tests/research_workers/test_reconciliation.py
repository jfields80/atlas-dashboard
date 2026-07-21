"""ATLAS-WORKERS-002 -- deterministic cross-source contradiction detection.

Proves that a genuine conflict between two eligible authoritative sources is
caught by Atlas's own deterministic reconciliation (services.research_workers.
reconciliation) regardless of what the model returned -- an empty response, or
one that silently picked a side, can no longer hide it. All offline: no network,
no paid call, no production write.
"""

from __future__ import annotations

import pytest

from services.research_workers import vocabulary as V
from services.research_workers.benchmark import load_benchmark, run_benchmark, score_case
from services.research_workers.contracts import Assignment, SourceDocument, content_hash
from services.research_workers.eval_config import DEFAULT_MODELS
from services.research_workers.evidence_validator import validate_proposal
from services.research_workers.model_eval import EvalCaps, run_live_evaluation
from services.research_workers.proposal import ModelProposal, RawFactClaim
from services.research_workers.providers import FakeProvider
from services.research_workers.reconciliation import (
    detect_field_contradictions, extract_source_claims,
)

_WELCOME = "Pet Policy: Pets are welcome at our hotel."
_NO_PETS = "Pet Policy: No pets are allowed at this location."
_BENCH07 = "07_contradictory_sources"
_BENCH07_PET_URL = "https://ex-ambig.example/pet-policy"


def _doc(url, stype, text, status=V.RETRIEVAL_OK):
    return SourceDocument(url, stype, "2026-07-21T00:00:00Z", "t",
                          text if status == V.RETRIEVAL_OK else "",
                          content_hash(text) if status == V.RETRIEVAL_OK else "", status)


def _asg(docs, fields=V.POLICY_FIELDS, aid="rec1"):
    urls = tuple(d.source_url for d in docs)
    return Assignment(aid, "columbus-oh", aid, "Test Hotel", "1 Main St",
                      urls[0] if urls else "", urls, tuple(docs), tuple(fields), "tester")


def _conflict_asg(text_a=_WELCOME, text_b=_NO_PETS,
                  stype_a=V.SOURCE_OFFICIAL_PROPERTY, stype_b=V.SOURCE_OFFICIAL_PROPERTY):
    a = _doc("https://ex.example/pet-policy", stype_a, text_a)
    b = _doc("https://ex.example/faq-policy", stype_b, text_b)
    return _asg([a, b]), a, b


def _claims(*items):
    return ModelProposal(claims=tuple(RawFactClaim(*i) for i in items), ok=True,
                         provider="openai", model="gpt-5.4-nano-2026-03-17")


def _empty():
    return ModelProposal(claims=(), ok=True, provider="openai", model="gpt-5.4-nano-2026-03-17")


def _pf(result, field):
    return next(f for f in result.proposed_facts if f.field_name == field)


def _bench07():
    _id, cases = load_benchmark()
    return next(c for c in cases if c.case_id == _BENCH07)


# --- 1. conflicting values for the same field produce CONTRADICTORY --------- #
def test_conflicting_values_produce_contradictory():
    asg, a, b = _conflict_asg()
    contra = detect_field_contradictions(asg.source_documents)
    assert V.FIELD_PETS_ALLOWED in contra
    assert {s.normalized_value for s in contra[V.FIELD_PETS_ALLOWED].sides} == {"true", "false"}
    # And through the validator, whether the model surfaced both sides or not.
    r = validate_proposal(asg, _claims(
        (V.FIELD_PETS_ALLOWED, "true", _WELCOME, a.source_url),
        (V.FIELD_PETS_ALLOWED, "false", _NO_PETS, b.source_url)))
    assert r.status == V.STATUS_CONTRADICTORY
    assert _pf(r, V.FIELD_PETS_ALLOWED).state == V.CONTRADICTORY


# --- 2. both sources and quotes are preserved ------------------------------- #
def test_both_sources_and_quotes_preserved():
    asg, a, b = _conflict_asg()
    r = validate_proposal(asg, _empty())          # model returned nothing
    blob = " ".join(r.contradictions)
    assert a.source_url in blob and b.source_url in blob          # both citations
    assert _WELCOME in blob and _NO_PETS in blob                  # both verbatim quotes
    assert "true" in blob and "false" in blob                     # both normalized values
    # the per-source SourceClaim records themselves retain full identity
    claims = extract_source_claims(asg.source_documents)
    by_url = {c.source_url: c for c in claims}
    assert by_url[a.source_url].normalized_value == "true"
    assert by_url[a.source_url].evidence_quote == _WELCOME
    assert by_url[a.source_url].source_type == V.SOURCE_OFFICIAL_PROPERTY
    assert by_url[b.source_url].normalized_value == "false"
    assert by_url[b.source_url].evidence_quote == _NO_PETS


# --- 3. one-source omission does not hide a known cross-source contradiction - #
def test_one_source_omission_does_not_hide_contradiction():
    asg, a, _b = _conflict_asg()
    # The model surfaced ONLY the pet-policy side (pets_allowed=true), omitting
    # the conflicting faq-policy source entirely.
    r = validate_proposal(asg, _claims((V.FIELD_PETS_ALLOWED, "true", _WELCOME, a.source_url)))
    assert r.status == V.STATUS_CONTRADICTORY
    assert _pf(r, V.FIELD_PETS_ALLOWED).state == V.CONTRADICTORY
    assert not [f for f in r.proposed_facts
                if f.field_name == V.FIELD_PETS_ALLOWED and f.state == V.SUPPORTED]


# --- 4. an empty model response cannot turn conflicting evidence into COMPLETED #
def test_empty_response_with_conflict_never_completed():
    asg, _a, _b = _conflict_asg()
    r = validate_proposal(asg, _empty())
    assert r.status == V.STATUS_CONTRADICTORY
    assert r.status != V.STATUS_COMPLETED


# --- 5. identical normalized values are not contradictory ------------------- #
def test_identical_normalized_values_not_contradictory():
    # Two differently-worded official sources that both normalize to true.
    asg, _a, _b = _conflict_asg(text_a=_WELCOME, text_b="Pet Policy: This property is pet-friendly.")
    assert detect_field_contradictions(asg.source_documents) == {}
    r = validate_proposal(asg, _empty())
    assert r.status != V.STATUS_CONTRADICTORY
    assert not r.contradictions


# --- 6. missing values are not contradictory -------------------------------- #
def test_missing_value_not_contradictory():
    # One source states the policy; the other is silent about pets entirely.
    a = _doc("https://ex.example/pet-policy", V.SOURCE_OFFICIAL_PROPERTY, _WELCOME)
    b = _doc("https://ex.example/rooms", V.SOURCE_OFFICIAL_PROPERTY,
             "Rooms and Rates. Check-in is at 3:00 PM. Free WiFi in every room.")
    asg = _asg([a, b])
    assert detect_field_contradictions(asg.source_documents) == {}
    r = validate_proposal(asg, _empty())
    assert r.status != V.STATUS_CONTRADICTORY


# --- 7. explicit existing source-priority rules are honored ----------------- #
def test_source_priority_rule_resolves_property_over_brand():
    # Property (rank 3) says pets welcome; the brand-wide page (rank 1) says no
    # pets. Atlas's existing rank rule resolves it -> property wins, NOT a
    # contradiction (rules 5/6). No new priority assumption is invented.
    asg, prop, _brand = _conflict_asg(text_a=_WELCOME, text_b="Pet Policy: No pets are allowed at our hotels.",
                                      stype_a=V.SOURCE_OFFICIAL_PROPERTY, stype_b=V.SOURCE_OFFICIAL_BRAND)
    assert detect_field_contradictions(asg.source_documents) == {}
    # A model that surfaced both sides: property wins, brand disagreement flagged.
    r = validate_proposal(asg, _claims(
        (V.FIELD_PETS_ALLOWED, "true", _WELCOME, prop.source_url),
        (V.FIELD_PETS_ALLOWED, "false", "Pet Policy: No pets are allowed at our hotels.", asg.source_documents[1].source_url)))
    pf = _pf(r, V.FIELD_PETS_ALLOWED)
    assert pf.state == V.SUPPORTED and pf.value == "true"
    assert r.status == V.STATUS_NEEDS_REVIEW      # rank-resolved, never CONTRADICTORY
    # Even with an empty model response, a rank-resolved disagreement is not a
    # deterministic contradiction.
    assert validate_proposal(asg, _empty()).status != V.STATUS_CONTRADICTORY


# --- 8. disputed fields cannot become publication eligible ------------------ #
def test_disputed_field_cannot_be_publication_eligible():
    case = _bench07()
    prop = _claims((V.FIELD_PETS_ALLOWED, "true", _WELCOME, _BENCH07_PET_URL))
    r = validate_proposal(case.assignment, prop)
    sc = score_case(case, r, prop)
    assert r.status == V.STATUS_CONTRADICTORY
    assert sc["publication_eligible"] is False
    assert V.FIELD_PETS_ALLOWED not in {
        f.field_name for f in r.proposed_facts if f.state == V.SUPPORTED}


# --- 9. normal single-source extraction remains unchanged ------------------- #
def test_single_source_extraction_unchanged():
    doc = _doc("https://p.example/a", V.SOURCE_OFFICIAL_PROPERTY, _WELCOME)
    asg = _asg([doc])
    assert detect_field_contradictions(asg.source_documents) == {}
    r = validate_proposal(asg, _claims((V.FIELD_PETS_ALLOWED, "true", _WELCOME, doc.source_url)))
    pf = _pf(r, V.FIELD_PETS_ALLOWED)
    assert pf.state == V.SUPPORTED and pf.value == "true"
    assert r.status == V.STATUS_COMPLETED and not r.contradictions


def test_full_fake_benchmark_metrics_unchanged():
    """The deterministic FakeProvider oracle still passes every case with the
    same yield split -- the reconciliation stage adds nothing to single-source
    or already-flagged cases."""
    rep = run_benchmark(FakeProvider(), model="fake-extractor-v1")
    assert rep["benchmark_correct_results"] == 10
    assert rep["validator_passed_results"] == 10
    assert rep["publication_eligible_results"] == 7
    assert rep["human_review_results"] == 1 and rep["no_source_results"] == 2
    assert rep["contradiction_detection_rate"] == 1.0
    assert rep["forbidden_inference_count"] == 0 and rep["unsupported_fact_count"] == 0


# --- 10. bench-07 passes deterministically even when the model picks one side- #
def _one_sided_factory():
    """A model that returns exactly one side of the bench-07 conflict
    (pets_allowed=true), never surfacing the contradicting source."""

    class _P:
        name = "openai"

        def propose(self, assignment, *, model, output_token_cap, timeout_s, max_retries):
            return ModelProposal(
                claims=(RawFactClaim(V.FIELD_PETS_ALLOWED, "true", _WELCOME, _BENCH07_PET_URL),),
                ok=True, structured_output_valid=True, provider="openai", model=model,
                input_tokens=700, output_tokens=40, latency_ms=100)

    return lambda name, **_: _P()


def test_bench07_deterministic_when_model_picks_one_side(monkeypatch):
    monkeypatch.setenv("ATLAS_BENCHMARK_SPEND_AUTHORIZATION", "YES_MAX_1_USD")
    monkeypatch.setenv("OPENAI_API_KEY", "SECRET")
    rep = run_live_evaluation([DEFAULT_MODELS[0]], EvalCaps(repetitions=3),
                              case_id=_BENCH07, provider_factory=_one_sided_factory())
    m = rep["models"][0]
    assert m["results"] == 3
    assert m["contradiction_detection_rate"] == 1.0     # detected in all three reps
    assert m["benchmark_correct"] == 3                  # every rep now correct
    assert m["publication_eligible"] == 0               # never publication eligible
    # Every repetition is a genuine cross-source contradiction, not a provider
    # failure or a validator failure.
    assert m["provider_failures"] == 0 and m["validator_failures"] == 0


def test_bench07_deterministic_when_model_returns_nothing(monkeypatch):
    """The empty-response repetition (bench-07 rep 0): no claims, available
    conflicting authoritative evidence, no provider failure -> CONTRADICTORY,
    never an empty COMPLETED."""
    monkeypatch.setenv("ATLAS_BENCHMARK_SPEND_AUTHORIZATION", "YES_MAX_1_USD")
    monkeypatch.setenv("OPENAI_API_KEY", "SECRET")

    class _P:
        name = "openai"

        def propose(self, assignment, *, model, output_token_cap, timeout_s, max_retries):
            return ModelProposal(claims=(), ok=True, structured_output_valid=True,
                                 provider="openai", model=model, input_tokens=700,
                                 output_tokens=5, latency_ms=90)

    rep = run_live_evaluation([DEFAULT_MODELS[0]], EvalCaps(repetitions=1),
                              case_id=_BENCH07, provider_factory=lambda name, **_: _P())
    m = rep["models"][0]
    assert m["benchmark_correct"] == 1 and m["contradiction_detection_rate"] == 1.0
    assert m["human_review"] == 1 and m["publication_eligible"] == 0
