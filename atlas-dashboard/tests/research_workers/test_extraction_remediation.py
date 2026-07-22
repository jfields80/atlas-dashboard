"""ATLAS-WORKERS-005 -- Columbus extraction-quality remediation tests.

Proves the safe, NON-WEAKENING remediation of the systemic Columbus pilot
findings: explicit number WORDS are recognized (bare plurals still rejected),
the fee-basis vocabulary gains per_room_per_night (broader values still cannot
claim it), a generic pet-friendliness statement supports pets_allowed (no
species), and legitimate tiered-fee ambiguity still routes to REVIEW. All
offline; exact quotes and strict publication gates are preserved.
"""

from __future__ import annotations

from services.research_workers import routing as RT
from services.research_workers import vocabulary as V
from services.research_workers.benchmark import load_benchmark, run_benchmark
from services.research_workers.contracts import Assignment, SourceDocument, content_hash
from services.research_workers.evidence_validator import (
    _fee_basis_supported, _numeric_supported, validate_proposal,
)
from services.research_workers.model_eval import VALIDATOR_VERSION
from services.research_workers.prompt import PROMPT_VERSION, build_worker_prompt
from services.research_workers.proposal import ModelProposal, RawFactClaim
from services.research_workers.providers import FakeProvider


def _asg(text, url="https://ex.example/pets", stype=V.SOURCE_OFFICIAL_PROPERTY, aid="rem-1"):
    doc = SourceDocument(url, stype, "2026-07-21T00:00:00Z", "t", text, content_hash(text), V.RETRIEVAL_OK)
    return Assignment(aid, "columbus-oh", aid, "Test Hotel", "1 Main St", url, (url,), (doc,),
                      V.POLICY_FIELDS, "tester")


def _claims(*items):
    return ModelProposal(claims=tuple(RawFactClaim(*i) for i in items), ok=True,
                         structured_output_valid=True, provider="openai", model="m")


def _supported(result):
    return {f.field_name: f for f in result.proposed_facts if f.state == V.SUPPORTED}


# --------------------------------------------------------------------------- #
# 1. Word-number recognition (unit) + the non-weakening boundary.
# --------------------------------------------------------------------------- #

def test_explicit_number_word_supports_count():
    assert _numeric_supported("2", "limit two pets per room") is True
    assert _numeric_supported("2", "A maximum of 2 pets is allowed") is True     # digit still works
    assert _numeric_supported("3", "up to three dogs permitted") is True


def test_bare_plural_or_wrong_number_still_unsupported():
    # NON-WEAKENING: a plural with no number, or the WRONG number word, or empty,
    # is still unsupported -- inference from plural wording is not allowed.
    assert _numeric_supported("2", "pets are welcome") is False
    assert _numeric_supported("2", "several pets allowed") is False
    assert _numeric_supported("2", "three pets permitted") is False
    assert _numeric_supported("2", "") is False


def test_number_word_end_to_end_preserves_verbatim_quote():
    asg = _asg("Pet Policy: guests may bring up to two pets per room.")
    u = asg.source_documents[0].source_url
    r = validate_proposal(asg, _claims(("maximum_pets", "2", "up to two pets per room", u)))
    sup = _supported(r)
    assert sup["maximum_pets"].value == "2"
    assert sup["maximum_pets"].evidence_quote == "up to two pets per room"        # verbatim, unchanged
    assert sup["maximum_pets"].evidence_quote in asg.source_documents[0].content_text
    assert r.status == V.STATUS_COMPLETED


def test_bare_plural_count_rejected_end_to_end():
    asg = _asg("Pet Policy: pets are welcome at our hotel.")
    u = asg.source_documents[0].source_url
    r = validate_proposal(asg, _claims(("maximum_pets", "2", "pets are welcome at our hotel", u)))
    assert "maximum_pets" not in _supported(r)
    assert "rejected_maximum_pets:number_not_in_quote" in r.warnings


# --------------------------------------------------------------------------- #
# 2. per_room_per_night fee-basis (unit) + broader-value guards.
# --------------------------------------------------------------------------- #

def test_per_room_per_night_supported():
    assert _fee_basis_supported(V.FEE_BASIS_PER_ROOM_PER_NIGHT, "$50 per room per night fee plus tax") is True


def test_broader_values_cannot_claim_per_room_per_night():
    # per_night and per_room must NOT match "per room per night" (forbidden guards).
    assert _fee_basis_supported(V.FEE_BASIS_PER_NIGHT, "$50 per room per night fee") is False
    assert _fee_basis_supported(V.FEE_BASIS_PER_ROOM, "$50 per room per night fee") is False


def test_per_room_per_day_and_night_stay_distinct():
    assert _fee_basis_supported(V.FEE_BASIS_PER_ROOM_PER_DAY, "A $50 fee applies per room per day") is True
    # the new value must not match per-day phrasing, and per_day must not match per-night
    assert _fee_basis_supported(V.FEE_BASIS_PER_ROOM_PER_NIGHT, "A $50 fee applies per room per day") is False
    assert _fee_basis_supported(V.FEE_BASIS_PER_ROOM_PER_DAY, "$50 per room per night") is False
    # a plain per_night still works where there is no per-room wording
    assert _fee_basis_supported(V.FEE_BASIS_PER_NIGHT, "A $75 fee applies per night") is True


# --------------------------------------------------------------------------- #
# 3. Drury-style end-to-end: the two fixes together lift it to READY.
# --------------------------------------------------------------------------- #

def test_drury_style_routes_ready():
    text = ("Dogs and cats accepted; $50 per room per night fee plus tax; "
            "limit two pets per room with a combined weight of 80 pounds; service animals free of charge")
    asg = _asg(text)
    u = asg.source_documents[0].source_url
    prop = _claims(
        ("pets_allowed", "true", "Dogs and cats accepted", u),
        ("dogs_accepted", "true", "Dogs and cats accepted", u),
        ("cats_accepted", "true", "Dogs and cats accepted", u),
        ("pet_fee", "$50", "$50 per room per night fee plus tax", u),
        ("fee_currency", "USD", "$50 per room per night fee plus tax", u),
        ("fee_basis", "per_room_per_night", "$50 per room per night fee plus tax", u),
        ("maximum_pets", "2", "limit two pets per room with a combined weight of 80 pounds", u),
        ("weight_limit", "80 pounds", "combined weight of 80 pounds", u))
    r = validate_proposal(asg, prop, provider="openai", model="gpt-5.4-nano-2026-03-17")
    assert r.status == V.STATUS_COMPLETED and r.warnings == ()
    env = RT.route_result(asg, r, prop, prompt_version=PROMPT_VERSION, validator_version=VALIDATOR_VERSION)
    assert env.route == RT.ROUTE_READY and env.publication_eligible is True
    facts = {f["field_name"]: f["value"] for f in env.supported_facts}
    assert facts["fee_basis"] == "per_room_per_night" and facts["maximum_pets"] == "2"


# --------------------------------------------------------------------------- #
# 4. Legitimate tiered-fee ambiguity stays REVIEW (never forced READY).
# --------------------------------------------------------------------------- #

def test_tiered_fee_conflict_still_withheld_to_review():
    text = ("Pet Policy: a cleaning fee of up to $25 per day per pet for the first six nights, "
            "then up to $15 per day.")
    asg = _asg(text)
    u = asg.source_documents[0].source_url
    prop = _claims(("pet_fee", "$25", "up to $25 per day per pet", u),
                   ("pet_fee", "$15", "then up to $15 per day", u))
    r = validate_proposal(asg, prop)
    assert r.status == V.STATUS_CONTRADICTORY                     # source states two amounts
    env = RT.route_result(asg, r, prop, prompt_version=PROMPT_VERSION, validator_version=VALIDATOR_VERSION)
    assert env.route == RT.ROUTE_REVIEW and env.publication_eligible is False
    assert RT.CONTRADICTORY_OFFICIAL_SOURCES in env.reason_codes


# --------------------------------------------------------------------------- #
# 5. Generic pet-friendliness supports pets_allowed (no species inference).
# --------------------------------------------------------------------------- #

def test_generic_pet_friendly_supports_pets_allowed_only():
    asg = _asg("Pet Policy: The property identifies itself as pet-friendly. Confirm current fees directly.")
    u = asg.source_documents[0].source_url
    r = validate_proposal(asg, _claims(
        ("pets_allowed", "true", "The property identifies itself as pet-friendly", u)))
    sup = _supported(r)
    assert sup["pets_allowed"].value == "true"
    assert "dogs_accepted" not in sup and "cats_accepted" not in sup   # rule 4 still holds
    assert r.status == V.STATUS_COMPLETED


# --------------------------------------------------------------------------- #
# 6. No regression: the deterministic oracle still passes the committed benchmark.
# --------------------------------------------------------------------------- #

def test_benchmark_oracle_unchanged_by_remediation():
    rep = run_benchmark(FakeProvider(), model="fake-extractor-v1")
    assert rep["benchmark_correct_results"] == 10
    assert rep["validator_passed_results"] == 10
    assert rep["forbidden_inference_count"] == 0 and rep["unsupported_fact_count"] == 0
    assert rep["exact_evidence_match_rate"] == 1.0


# --------------------------------------------------------------------------- #
# 7. Contract versions + prompt content.
# --------------------------------------------------------------------------- #

def test_contract_versions_and_prompt_content():
    assert PROMPT_VERSION == "1.4.0" and VALIDATOR_VERSION == "1.3.0"
    assert V.FEE_BASIS_PER_ROOM_PER_NIGHT in V.FEE_BASIS_VALUES
    _id, cases = load_benchmark()
    system, _user = build_worker_prompt(cases[0].assignment)
    assert "per_room_per_night" in system                     # new fee-basis mapping
    assert "two pets" in system                               # number-word instruction
    assert "identifies itself as pet-friendly" in system      # generic completeness clause
    assert "Emit fee_basis ONLY" in system                    # only-when-explicit-basis rule
