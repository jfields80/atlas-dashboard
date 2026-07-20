"""ATLAS-WORKERS-001 -- research worker tests (Stage 10).

No network, no paid calls, no writes outside a pytest tmp_path. Covers the
contracts, the deterministic evidence protections, the provider airlock, budget
caps, the fake-provider benchmark, the scorer, and the production-safety
guarantees.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from services.research_workers import manifest
from services.research_workers import vocabulary as V
from services.research_workers.benchmark import Budget, load_benchmark, run_benchmark, score_case
from services.research_workers.contracts import (
    Assignment, ContractError, ProposedField, SourceDocument, WorkerResult, content_hash,
)
from services.research_workers.evidence_validator import validate_proposal
from services.research_workers.hotel_policy_worker import run_assignment
from services.research_workers.pricing import ModelPricing, estimate_cost, pricing_for
from services.research_workers.proposal import ModelProposal, RawFactClaim
from services.research_workers.providers import (
    FakeProvider, LiveAuthorization, OpenAICompatibleProvider, SpendingAirlockError,
    build_provider, require_live_authorization,
)
from services.research_workers.repository import RepositoryError, WorkerRepository

_REPO_ROOT = Path(__file__).resolve().parents[2]


def _doc(url, stype, text, status=V.RETRIEVAL_OK):
    return SourceDocument(url, stype, "2026-07-19T00:00:00Z", "t",
                          text if status == V.RETRIEVAL_OK else "",
                          content_hash(text) if status == V.RETRIEVAL_OK else "", status)


def _asg(docs, fields=V.POLICY_FIELDS, aid="a1"):
    urls = tuple(d.source_url for d in docs)
    return Assignment(aid, "columbus-oh", aid, "Test Hotel", "1 Main St", urls[0] if urls else "",
                      urls, tuple(docs), tuple(fields), "tester")


def _claims(*items):
    return ModelProposal(claims=tuple(RawFactClaim(*i) for i in items), ok=True,
                         provider="stub", model="stub-1")


def _sup(result, field):
    return next((f for f in result.proposed_facts if f.field_name == field), None)


# --- 1. schema validation --------------------------------------------------- #
def test_assignment_schema_validation():
    good = _asg([_doc("https://p.example/a", V.SOURCE_OFFICIAL_PROPERTY, "Pets are welcome.")])
    good.validate()   # no raise
    with pytest.raises(ContractError):
        _asg([_doc("https://p.example/a", "MADE_UP_TYPE", "x")]).validate()
    with pytest.raises(ContractError):
        Assignment("a", "m", "k", "n", "addr", "", ("https://only.example/a",),
                   (_doc("https://other.example/b", V.SOURCE_OFFICIAL_PROPERTY, "x"),),
                   V.POLICY_FIELDS, "t").validate()   # doc URL not in allowlist


def test_result_schema_roundtrip():
    r = _run_fake("Dogs and cats are welcome. A $50 fee applies per night.")
    r2 = WorkerResult.from_dict(r.to_dict())
    assert r2.to_dict() == r.to_dict()


# --- 2. deterministic serialization + hashing ------------------------------- #
def test_deterministic_hash_and_serialization():
    a = _run_fake("Pets are welcome. A $50 fee applies per night.")
    b = _run_fake("Pets are welcome. A $50 fee applies per night.")
    assert a.result_hash == b.result_hash
    assert a.result_hash.startswith("sha256:")
    # latency/tokens excluded from the content hash
    import dataclasses
    assert dataclasses.replace(a, latency_ms=999, input_tokens=7).compute_hash() == a.compute_hash()


# --- 3. path traversal rejection -------------------------------------------- #
def test_path_traversal_rejected(tmp_path):
    repo = WorkerRepository(tmp_path)
    for bad in ("../evil", "a/b", "..\\evil", "/etc/passwd", "a/../../b"):
        with pytest.raises(RepositoryError):
            repo._safe_file("results", bad)


def test_repo_refuses_launch_package_root():
    with pytest.raises(RepositoryError):
        WorkerRepository(_REPO_ROOT / "launch_packages" / "pettripfinder")


# --- 4. URL allowlist enforcement ------------------------------------------- #
def test_url_allowlist_enforced_in_validation():
    # a claim citing a URL not among the usable official docs is rejected
    doc = _doc("https://p.example/a", V.SOURCE_OFFICIAL_PROPERTY, "Pets are welcome.")
    asg = _asg([doc])
    prop = _claims((V.FIELD_PETS_ALLOWED, "true", "Pets are welcome.", "https://evil.example/x"))
    r = validate_proposal(asg, prop)
    assert _sup(r, V.FIELD_PETS_ALLOWED).state == V.NOT_STATED
    assert any("source_not_official" in w for w in r.warnings)


# --- 5/6. exact quote verification + unsupported rejection ------------------ #
def test_exact_quote_required_and_unsupported_rejected():
    doc = _doc("https://p.example/a", V.SOURCE_OFFICIAL_PROPERTY, "Pets are welcome at our hotel.")
    asg = _asg([doc])
    # quote not verbatim in the doc -> rejected to NOT_STATED
    r = validate_proposal(asg, _claims((V.FIELD_PETS_ALLOWED, "true", "PETS ARE BANNED", doc.source_url)))
    assert _sup(r, V.FIELD_PETS_ALLOWED).state == V.NOT_STATED
    # verbatim quote -> supported
    r2 = validate_proposal(asg, _claims((V.FIELD_PETS_ALLOWED, "true", "Pets are welcome at our hotel.", doc.source_url)))
    f = _sup(r2, V.FIELD_PETS_ALLOWED)
    assert f.state == V.SUPPORTED and f.evidence_quote in doc.content_text


# --- 7/8. pets welcome does not imply dogs / cats --------------------------- #
def test_pets_welcome_does_not_imply_dogs():
    doc = _doc("https://p.example/a", V.SOURCE_OFFICIAL_PROPERTY, "Pets are welcome at our property.")
    asg = _asg([doc])
    r = validate_proposal(asg, _claims((V.FIELD_DOGS_ACCEPTED, "true", "Pets are welcome at our property.", doc.source_url)))
    assert _sup(r, V.FIELD_DOGS_ACCEPTED).state == V.NOT_STATED   # no "dog" in quote
    assert any("species_not_in_quote" in w for w in r.warnings)


def test_pets_welcome_does_not_imply_cats():
    doc = _doc("https://p.example/a", V.SOURCE_OFFICIAL_PROPERTY, "Pets are welcome at our property.")
    asg = _asg([doc])
    r = validate_proposal(asg, _claims((V.FIELD_CATS_ACCEPTED, "true", "Pets are welcome at our property.", doc.source_url)))
    assert _sup(r, V.FIELD_CATS_ACCEPTED).state == V.NOT_STATED


# --- 9. fee vs deposit ------------------------------------------------------ #
def test_fee_and_deposit_stay_separate():
    text = ("A $50 pet fee applies per night. A refundable deposit of $100 is required.")
    doc = _doc("https://p.example/a", V.SOURCE_OFFICIAL_PROPERTY, text)
    asg = _asg([doc])
    r = validate_proposal(asg, _claims(
        (V.FIELD_PET_FEE, "$50", "A $50 pet fee applies per night.", doc.source_url),
        (V.FIELD_REFUNDABLE_DEPOSIT, "$100", "A refundable deposit of $100 is required.", doc.source_url)))
    assert _sup(r, V.FIELD_PET_FEE).value == "$50"
    assert _sup(r, V.FIELD_REFUNDABLE_DEPOSIT).value == "$100"
    # a deposit claim whose quote lacks "deposit" is rejected
    r2 = validate_proposal(asg, _claims(
        (V.FIELD_REFUNDABLE_DEPOSIT, "$50", "A $50 pet fee applies per night.", doc.source_url)))
    assert _sup(r2, V.FIELD_REFUNDABLE_DEPOSIT).state == V.NOT_STATED


# --- 10. fee-basis distinction ---------------------------------------------- #
def test_fee_basis_distinction():
    doc = _doc("https://p.example/a", V.SOURCE_OFFICIAL_PROPERTY, "A fee of $40 applies per room per day.")
    asg = _asg([doc])
    good = validate_proposal(asg, _claims((V.FIELD_FEE_BASIS, "per_room_per_day", "A fee of $40 applies per room per day.", doc.source_url)))
    assert _sup(good, V.FIELD_FEE_BASIS).value == "per_room_per_day"
    # claiming per_room when the text says per room per day is rejected (distinct)
    bad = validate_proposal(asg, _claims((V.FIELD_FEE_BASIS, "per_room", "A fee of $40 applies per room per day.", doc.source_url)))
    assert _sup(bad, V.FIELD_FEE_BASIS).state == V.NOT_STATED


# --- 11. maximum-pet non-inference ------------------------------------------ #
def test_maximum_pets_not_inferred_from_plural():
    doc = _doc("https://p.example/a", V.SOURCE_OFFICIAL_PROPERTY, "Pets are welcome in all rooms.")
    asg = _asg([doc])
    r = validate_proposal(asg, _claims((V.FIELD_MAXIMUM_PETS, "2", "Pets are welcome in all rooms.", doc.source_url)))
    assert _sup(r, V.FIELD_MAXIMUM_PETS).state == V.NOT_STATED   # no "2" in quote


# --- 12. weight-limit non-inference ----------------------------------------- #
def test_weight_limit_number_must_be_quoted():
    doc = _doc("https://p.example/a", V.SOURCE_OFFICIAL_PROPERTY, "Large pets are permitted.")
    asg = _asg([doc])
    r = validate_proposal(asg, _claims((V.FIELD_WEIGHT_LIMIT, "80 lb", "Large pets are permitted.", doc.source_url)))
    assert _sup(r, V.FIELD_WEIGHT_LIMIT).state == V.NOT_STATED


# --- 13. contradictory sources ---------------------------------------------- #
def test_contradictory_same_rank_sources():
    d1 = _doc("https://p.example/a", V.SOURCE_OFFICIAL_PROPERTY, "Pets are welcome here.")
    d2 = _doc("https://p.example/b", V.SOURCE_OFFICIAL_PROPERTY, "No pets are allowed here.")
    asg = _asg([d1, d2])
    r = run_assignment(asg, FakeProvider(), model="fake")
    assert r.status == V.STATUS_CONTRADICTORY
    assert any(c.startswith("pets_allowed") for c in r.contradictions)


def test_brand_never_overrides_property():
    prop = _doc("https://p.example/a", V.SOURCE_OFFICIAL_PROPERTY, "Pets are welcome here.")
    brand = _doc("https://brand.example/policy", V.SOURCE_OFFICIAL_BRAND, "No pets are allowed at our hotels.")
    asg = _asg([prop, brand])
    r = validate_proposal(asg, _claims(
        (V.FIELD_PETS_ALLOWED, "true", "Pets are welcome here.", prop.source_url),
        (V.FIELD_PETS_ALLOWED, "false", "No pets are allowed at our hotels.", brand.source_url)))
    f = _sup(r, V.FIELD_PETS_ALLOWED)
    assert f.state == V.SUPPORTED and f.value == "true"   # property wins
    assert r.status == V.STATUS_NEEDS_REVIEW               # brand disagreement flagged


# --- 14. missing / blocked sources ------------------------------------------ #
def test_blocked_sources_produce_no_facts():
    blocked = _doc("https://p.example/a", V.SOURCE_OFFICIAL_PROPERTY, "Pets are welcome.", status=V.RETRIEVAL_BLOCKED)
    asg = _asg([blocked])
    r = run_assignment(asg, FakeProvider(), model="fake")
    assert r.status == V.STATUS_NO_OFFICIAL_SOURCE
    assert all(f.state == V.NOT_STATED for f in r.proposed_facts)


def test_other_source_is_not_evidence():
    other = _doc("https://blog.example/x", V.SOURCE_OTHER, "This hotel is pet-friendly per reviews.")
    asg = _asg([other])
    r = run_assignment(asg, FakeProvider(), model="fake")
    assert r.status == V.STATUS_NO_OFFICIAL_SOURCE


# --- 15. usage capture ------------------------------------------------------ #
def test_usage_capture_flows_into_result():
    doc = _doc("https://p.example/a", V.SOURCE_OFFICIAL_PROPERTY, "Pets are welcome.")
    asg = _asg([doc])
    prop = ModelProposal(claims=(RawFactClaim(V.FIELD_PETS_ALLOWED, "true", "Pets are welcome.", doc.source_url),),
                         ok=True, provider="stub", model="m", input_tokens=123, output_tokens=45,
                         cached_input_tokens=10, latency_ms=250, attempt_count=2)
    r = validate_proposal(asg, prop)
    assert (r.input_tokens, r.output_tokens, r.cached_input_tokens, r.latency_ms, r.attempt_count) == (123, 45, 10, 250, 2)


# --- 16. configurable cost calculation -------------------------------------- #
def test_configurable_cost_calculation():
    p = ModelPricing(input_per_1k=1.0, output_per_1k=2.0, cached_input_per_1k=0.5)
    assert estimate_cost(p, input_tokens=1000, output_tokens=1000) == 3.0
    assert estimate_cost(p, input_tokens=1000, output_tokens=0, cached_input_tokens=1000) == 0.5
    assert estimate_cost(None, input_tokens=1000, output_tokens=1000) == 0.0   # unknown pricing
    table = {"openai/m": p}
    assert pricing_for(table, "openai", "m") is p
    assert pricing_for(table, "openai", "other") is None


# --- 17/18. live-mode airlock + no offline network init --------------------- #
def test_airlock_blocks_without_full_authorization(monkeypatch):
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    for auth in (LiveAuthorization(live=False),
                 LiveAuthorization(live=True),
                 LiveAuthorization(live=True, confirm_spend=True),
                 LiveAuthorization(live=True, confirm_spend=True, provider="openai"),
                 LiveAuthorization(live=True, confirm_spend=True, provider="openai", model="m")):
        with pytest.raises(SpendingAirlockError):
            require_live_authorization(auth)
    with pytest.raises(SpendingAirlockError):
        build_provider("openai", auth=LiveAuthorization(live=True, confirm_spend=True, provider="openai", model="m"))


def test_offline_provider_never_initializes_network(monkeypatch):
    import urllib.request
    def _boom(*a, **k):
        raise AssertionError("network call attempted in offline mode")
    monkeypatch.setattr(urllib.request, "urlopen", _boom)
    monkeypatch.setattr(urllib.request, "Request", _boom)
    rep = run_benchmark(FakeProvider(), model="fake-extractor-v1")   # must not touch the network
    assert rep["assignments_attempted"] == 10


# --- 19. budget-cap enforcement --------------------------------------------- #
def test_budget_caps():
    b = Budget(max_assignments=3)
    rep = run_benchmark(FakeProvider(), model="fake-extractor-v1", budget=b)
    assert rep["assignments_attempted"] == 3 and rep["budget_stopped"]
    assert Budget(max_estimated_cost=1.0).exceeded(ran=1, input_tokens=0, output_tokens=0, cost=2.0) == "max_estimated_cost"
    assert Budget(max_total_input_tokens=100).exceeded(ran=1, input_tokens=200, output_tokens=0, cost=0.0) == "max_total_input_tokens"
    assert Budget().exceeded(ran=99, input_tokens=1, output_tokens=1, cost=1.0) is None


# --- 20. bounded retries (live adapter, no real network) -------------------- #
def test_bounded_retries(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "x")
    auth = LiveAuthorization(live=True, confirm_spend=True, provider="openai", model="m")
    prov = OpenAICompatibleProvider(auth)
    import urllib.request
    calls = {"n": 0}
    def _fail(*a, **k):
        calls["n"] += 1
        raise OSError("boom")
    monkeypatch.setattr(urllib.request, "urlopen", _fail)
    doc = _doc("https://p.example/a", V.SOURCE_OFFICIAL_PROPERTY, "Pets are welcome.")
    out = prov.propose(_asg([doc]), model="m", output_token_cap=64, timeout_s=1, max_retries=2)
    assert out.ok is False and out.attempt_count == 3 and calls["n"] == 3


def test_adapter_refuses_model_switch(monkeypatch):
    monkeypatch.setenv("OPENAI_API_KEY", "x")
    prov = OpenAICompatibleProvider(LiveAuthorization(live=True, confirm_spend=True, provider="openai", model="m"))
    with pytest.raises(SpendingAirlockError):
        prov.propose(_asg([_doc("https://p.example/a", V.SOURCE_OFFICIAL_PROPERTY, "Pets are welcome.")]),
                     model="a-different-model", output_token_cap=64, timeout_s=1, max_retries=0)


# --- 21/22. fake benchmark + scorer yield metrics --------------------------- #
def test_fake_benchmark_yield_metrics():
    rep = run_benchmark(FakeProvider(), model="fake-extractor-v1")
    assert rep["assignments_attempted"] == 10
    assert rep["benchmark_kind"] == "offline_pipeline_validator_benchmark"
    assert rep["structured_valid_results"] == 10
    assert rep["validator_passed_results"] == 10
    assert rep["benchmark_correct_results"] == 10
    # publication-eligible excludes the contradictory + the two no-source cases
    assert rep["publication_eligible_results"] == 7
    assert rep["human_review_results"] == 1
    assert rep["no_source_results"] == 2
    assert rep["failed_results"] == 0
    assert rep["forbidden_inference_count"] == 0 and rep["unsupported_fact_count"] == 0
    assert rep["field_recall"] == 1.0 and rep["field_precision"] == 1.0
    assert rep["contradiction_detection_rate"] == 1.0


def test_contradictory_case_not_publication_eligible():
    rep = run_benchmark(FakeProvider(), model="fake-extractor-v1")
    contra = next(c for c in rep["cases"] if c["case_id"] == "07_contradictory_sources")
    assert contra["actual_status"] == V.STATUS_CONTRADICTORY
    assert contra["benchmark_correct"] is True       # a correct research result
    assert contra["publication_eligible"] is False   # but NOT publication eligible


def test_scorer_flags_forbidden_inference():
    _bid, cases = load_benchmark()
    generic = next(c for c in cases if c.case_id == "02_generic_pets_welcome")
    quote = generic.assignment.source_documents[0].content_text.split("\n")[0]
    bad = WorkerResult(
        assignment_id=generic.assignment.assignment_id, listing_key="k", status=V.STATUS_COMPLETED,
        selected_source_url=generic.assignment.allowed_source_urls[0], selected_source_type=V.SOURCE_OFFICIAL_PROPERTY,
        evidence_quotes=(), proposed_facts=(ProposedField(V.FIELD_DOGS_ACCEPTED, V.SUPPORTED, "true",
                                                          quote, generic.assignment.allowed_source_urls[0],
                                                          V.SOURCE_OFFICIAL_PROPERTY),),
        unknown_fields=(), contradictions=(), warnings=(), provider="x", model="y").with_hash()
    sc = score_case(generic, bad)
    assert sc["forbidden_inference_count"] == 1
    assert sc["benchmark_correct"] is False and sc["publication_eligible"] is False


# --- ATLAS-WORKERS-001A: benchmark realism + manifest + sync ---------------- #
def test_manifest_gates_pass():
    assert manifest.validate_manifest() == []


def test_evidence_sync_in_sync():
    assert manifest.verify_evidence_sync() == []


def test_evidence_sync_detects_drift(tmp_path):
    # tamper with the committed quote -> sync must fail loudly
    facts = json.loads((_REPO_ROOT / "launch_packages" / "pettripfinder" / "hotel_policy_facts.json").read_text(encoding="utf-8"))
    facts["hotels"][0]["evidence_quote"] = "TAMPERED " + facts["hotels"][0]["evidence_quote"]
    p = tmp_path / "facts.json"
    p.write_text(json.dumps(facts), encoding="utf-8")
    problems = manifest.verify_evidence_sync(facts_path=str(p))
    assert problems, "drift must be detected"


def test_at_least_six_real_cases_map_to_committed_evidence():
    _bid, cases = load_benchmark()
    reals = [c for c in cases if c.case_kind == "REAL"]
    assert len(reals) >= 6
    facts = json.loads((_REPO_ROOT / "launch_packages" / "pettripfinder" / "hotel_policy_facts.json").read_text(encoding="utf-8"))
    keys = {h["key"] for h in facts["hotels"]}
    for c in reals:
        rec_key = c.provenance["source_record_key"]
        assert rec_key in keys
        committed = next(h["evidence_quote"] for h in facts["hotels"] if h["key"] == rec_key)
        assert any(committed in d.content_text for d in c.assignment.source_documents)


def test_prompt_injection_is_ignored():
    _bid, cases = load_benchmark()
    inj = next(c for c in cases if c.case_id == "08_prompt_injection_no_pets")
    assert any("Ignore previous instructions" in d.content_text for d in inj.assignment.source_documents)
    r = run_assignment(inj.assignment, FakeProvider(), model="fake")
    pets = next(f for f in r.proposed_facts if f.field_name == V.FIELD_PETS_ALLOWED)
    assert pets.state == V.SUPPORTED and pets.value == "false"   # injection did not flip it


# --- 23/24. production safety ------------------------------------------------ #
def test_no_writes_to_launch_packages_or_inventory(tmp_path):
    csv = _REPO_ROOT / "launch_packages" / "pettripfinder" / "seed_businesses.csv"
    before = hashlib.sha256(csv.read_bytes()).hexdigest()
    repo = WorkerRepository(tmp_path)
    r = _run_fake("Dogs and cats are welcome. A $50 fee applies per night.")
    repo.write_result(r)
    # everything the worker wrote lives under the tmp worker root
    written = list(tmp_path.rglob("*.json"))
    assert written and all(tmp_path in p.parents for p in written)
    assert hashlib.sha256(csv.read_bytes()).hexdigest() == before   # inventory untouched


def _run_fake(text):
    doc = _doc("https://p.example/a", V.SOURCE_OFFICIAL_PROPERTY, text)
    return run_assignment(_asg([doc]), FakeProvider(), model="fake")
