"""ATLAS-WORKERS-006 -- structured tiered/conditional/capped pet-fee tests.

All OFFLINE. Proves faithful non-lossy representation, evidence-safe per-term
validation, same-source reconciliation (rules A-F), additive backward
compatibility, and fail-closed routing (DOWNSTREAM_FEE_SCHEMA_UNSUPPORTED) while
the production chain remains single-value. Exact quotes and strict gates are
preserved; no genuine contradiction is let through and no fee is flattened.
"""

from __future__ import annotations

import json

from services.research_workers import fee_terms as FT
from services.research_workers import routing as RT
from services.research_workers import vocabulary as V
from services.research_workers.benchmark import run_benchmark
from services.research_workers.contracts import (
    Assignment, PetFeePolicy, PetFeeTerm, SourceDocument, WorkerResult, canonical_json, content_hash,
)
from services.research_workers.evidence_validator import validate_proposal
from services.research_workers.model_eval import VALIDATOR_VERSION
from services.research_workers.prompt import PROMPT_VERSION, parse_fee_terms
from services.research_workers.proposal import ModelProposal, RawFactClaim, RawFeeTerm
from services.research_workers.providers import FakeProvider


def _asg(text, url="https://ex.example/pets", stype=V.SOURCE_OFFICIAL_PROPERTY, aid="fee-1"):
    doc = SourceDocument(url, stype, "2026-07-22T00:00:00Z", "t", text, content_hash(text), V.RETRIEVAL_OK)
    return Assignment(aid, "columbus-oh", aid, "H", "1 St", url, (url,), (doc,), V.POLICY_FIELDS, "t")


def _prop(asg, fee_terms, facts=()):
    return ModelProposal(claims=tuple(RawFactClaim(*f) for f in facts), fee_terms=tuple(fee_terms),
                         ok=True, structured_output_valid=True, provider="openai", model="m")


def _docmap(asg):
    return {d.source_url: d for d in asg.source_documents}


# --------------------------------------------------------------------------- #
# 1. Canonical amount (Decimal, never float, never raw fragment).
# --------------------------------------------------------------------------- #

def test_canonical_amount():
    assert FT.canonical_amount("$50") == "50.00"
    assert FT.canonical_amount("up to $150") == "150.00"
    assert FT.canonical_amount("$25.50 plus tax") == "25.50"
    assert FT.canonical_amount("1,250") == "1250.00"
    assert FT.canonical_amount("no number here") is None
    assert FT.canonical_amount("") is None


# --------------------------------------------------------------------------- #
# 2. Backward compatibility: simple policy + additive contract.
# --------------------------------------------------------------------------- #

def test_simple_policy_backward_compatible():
    asg = _asg("Pet Policy: A $75 fee applies per stay.")
    u = asg.source_documents[0].source_url
    r = validate_proposal(asg, _prop(asg, (), facts=[
        ("pets_allowed", "true", "A $75 fee applies per stay", u),
        ("pet_fee", "$75", "A $75 fee applies per stay", u),
        ("fee_currency", "USD", "A $75 fee applies per stay", u),
        ("fee_basis", "per_stay", "A $75 fee applies per stay", u)]))
    assert r.fee_policy is None                                   # no structured policy
    sup = {f.field_name: f.value for f in r.proposed_facts if f.state == V.SUPPORTED}
    assert sup["pet_fee"] == "$75" and sup["fee_basis"] == "per_stay"   # scalar intact


def test_worker_result_additive_field_backward_readable():
    # An old serialized result with NO fee_policy round-trips to None, and its
    # result_hash is byte-stable (fee_policy omitted from the content when None).
    r = WorkerResult(assignment_id="a", listing_key="a", status=V.STATUS_COMPLETED,
                     selected_source_url="", selected_source_type="", evidence_quotes=(),
                     proposed_facts=(), unknown_fields=(), contradictions=(), warnings=(),
                     provider="fake", model="m").with_hash()
    d = r.to_dict()
    assert "fee_policy" not in d                                  # omitted when None
    back = WorkerResult.from_dict(d)
    assert back.fee_policy is None and back.result_hash == r.result_hash


# --------------------------------------------------------------------------- #
# 3. Per-term validation: accept + every rejection reason.
# --------------------------------------------------------------------------- #

def test_valid_recurring_charge_accepted():
    asg = _asg("non-refundable pet fee of $50 per night")
    term, why = FT.validate_fee_term(
        RawFeeTerm(role="RECURRING_CHARGE", amount="$50", currency="USD", basis="per_night",
                   scope="unstated", condition_type="unconditional",
                   evidence_quote="non-refundable pet fee of $50 per night",
                   source_url=asg.source_documents[0].source_url), _docmap(asg))
    assert why == "" and term.amount == "50.00" and term.basis == "per_night"


def test_term_rejections():
    asg = _asg("A cleaning fee of up to $25 per day per pet for the first six nights. "
               "A flat fee of $75 per stay applies. "
               "A refundable deposit of $200 per stay is required.")
    u = asg.source_documents[0].source_url
    dm = _docmap(asg)

    def why(**kw):
        base = dict(role="RECURRING_CHARGE", amount="$25", currency="USD", basis="per_day",
                    scope="unstated", condition_type="unconditional", source_url=u,
                    evidence_quote="up to $25 per day per pet for the first six nights")
        base.update(kw)
        return FT.validate_fee_term(RawFeeTerm(**base), dm)[1]

    assert why(role="NOPE") == "invalid_role"
    assert why(amount="free") == "amount_unparseable"
    assert why(basis="weekly") == "invalid_basis"
    assert why(scope="per_guest") == "invalid_scope"
    assert why(amount="$999") == "amount_not_in_quote"           # 999 not in the quote
    assert why(currency="") == "currency_missing"
    assert why(basis="per_stay", role="ONE_TIME_CHARGE",
               evidence_quote="up to $25 per day per pet") == "basis_not_in_quote"     # no "stay"
    assert why(scope="per_room") == "scope_not_in_quote"          # quote says pet, not room
    assert why(role="CAP", basis="per_stay", scope="policy_total", amount="$75",
               evidence_quote="A flat fee of $75 per stay applies") == "cap_language_absent"
    assert why(role="DEPOSIT", basis="one_time") == "deposit_language_absent"
    assert why(role="ONE_TIME_CHARGE", basis="per_stay", amount="$200",
               evidence_quote="A refundable deposit of $200 per stay is required") == "fee_deposit_confusion"
    assert why(condition_type="stay_length_range", condition_min=None, condition_max=99,
               boundary_unit="nights") == "condition_boundary_not_in_quote"   # 99 absent


def test_number_word_boundary_supported():
    asg = _asg("up to $25 per day per pet for the first six nights")
    term, why = FT.validate_fee_term(
        RawFeeTerm(role="RECURRING_CHARGE", amount="$25", currency="USD", basis="per_day",
                   scope="per_pet", condition_type="stay_length_range", condition_min=None,
                   condition_max=6, boundary_unit="nights",
                   evidence_quote="up to $25 per day per pet for the first six nights",
                   source_url=asg.source_documents[0].source_url), _docmap(asg))
    assert why == "" and term.condition_max == 6                 # "six" -> 6 (word boundary)


# --------------------------------------------------------------------------- #
# 4. Reconciliation rules A-F.
# --------------------------------------------------------------------------- #

def _t(role, amount, basis, scope="unstated", ct="unconditional", cmin=None, cmax=None, unit="", q="q"):
    return PetFeeTerm(role=role, amount=amount, currency="USD", basis=basis, scope=scope,
                      condition_type=ct, condition_min=cmin, condition_max=cmax, boundary_unit=unit,
                      evidence_quote=q, source_url="u", source_type=V.SOURCE_OFFICIAL_PROPERTY)


def test_rule_a_exact_duplicate_dedup():
    p, contra = FT.reconcile_fee_terms([_t("ONE_TIME_CHARGE", "75.00", "per_stay"),
                                        _t("ONE_TIME_CHARGE", "75.00", "per_stay")])
    assert len(p.terms) == 1 and contra == []


def test_semantic_duplicate_dedup_ignores_quote():
    p, contra = FT.reconcile_fee_terms([_t("ONE_TIME_CHARGE", "75.00", "per_stay", q="A"),
                                        _t("ONE_TIME_CHARGE", "75.00", "per_stay", q="B differently worded")])
    assert len(p.terms) == 1 and contra == []                    # identity ignores wording


def test_rule_b_mutually_exclusive_tiers_not_contradictory():
    p, contra = FT.reconcile_fee_terms([
        _t("ONE_TIME_CHARGE", "75.00", "per_stay", ct="stay_length_range", cmin=1, cmax=7, unit="nights"),
        _t("ONE_TIME_CHARGE", "150.00", "per_stay", ct="stay_length_range", cmin=8, cmax=None, unit="nights")])
    assert contra == [] and len(p.terms) == 2                    # non-overlapping ranges kept


def test_rule_c_recurring_plus_cap_not_contradictory():
    p, contra = FT.reconcile_fee_terms([_t("RECURRING_CHARGE", "50.00", "per_night"),
                                        _t("CAP", "150.00", "per_stay", scope="policy_total")])
    assert contra == [] and len(p.terms) == 2                    # different roles preserved


def test_rule_d_overlapping_amounts_contradictory():
    p, contra = FT.reconcile_fee_terms([_t("RECURRING_CHARGE", "50.00", "per_night"),
                                        _t("RECURRING_CHARGE", "75.00", "per_night")])
    assert contra and "50.00 vs 75.00" in contra[0]              # unconditional overlap -> conflict


def test_rule_f_fee_and_deposit_separate():
    p, contra = FT.reconcile_fee_terms([_t("ONE_TIME_CHARGE", "75.00", "per_stay"),
                                        _t("DEPOSIT", "200.00", "one_time")])
    assert contra == [] and len(p.terms) == 2


# --------------------------------------------------------------------------- #
# 5. End-to-end representative patterns (validate + reconcile + route).
# --------------------------------------------------------------------------- #

def _route(asg, prop):
    r = validate_proposal(asg, prop, provider="openai", model="gpt-5.4-nano-2026-03-17")
    env = RT.route_result(asg, r, prop, prompt_version=PROMPT_VERSION, validator_version=VALIDATOR_VERSION)
    return r, env


def test_recurring_plus_cap_pattern_routes_review_downstream():
    asg = _asg("non-refundable pet fee of $50 per night, up to $150 per stay")
    u = asg.source_documents[0].source_url
    r, env = _route(asg, _prop(asg, [
        RawFeeTerm(role="RECURRING_CHARGE", amount="$50", currency="USD", basis="per_night",
                   condition_type="unconditional", evidence_quote="pet fee of $50 per night", source_url=u),
        RawFeeTerm(role="CAP", amount="up to $150", currency="USD", basis="per_stay", scope="policy_total",
                   condition_type="unconditional", evidence_quote="up to $150 per stay", source_url=u)],
        facts=[("pets_allowed", "true", "pet fee of $50 per night", u)]))
    assert r.status == V.STATUS_COMPLETED and r.contradictions == ()
    assert r.fee_policy is not None and len(r.fee_policy.terms) == 2
    assert not any(f.field_name == "pet_fee" and f.state == V.SUPPORTED for f in r.proposed_facts)  # no flattening
    assert env.route == RT.ROUTE_REVIEW and env.reason_codes == (RT.DOWNSTREAM_FEE_SCHEMA_UNSUPPORTED,)
    assert env.publication_eligible is False and env.fee_policy is not None


def test_first_n_after_n_tiers_route_review():
    asg = _asg("up to $25 plus tax per day per pet for the first six nights, then up to $15 per day")
    u = asg.source_documents[0].source_url
    r, env = _route(asg, _prop(asg, [
        RawFeeTerm(role="RECURRING_CHARGE", amount="$25", currency="USD", basis="per_day", scope="per_pet",
                   condition_type="stay_length_range", condition_min=None, condition_max=6, boundary_unit="nights",
                   evidence_quote="up to $25 plus tax per day per pet for the first six nights", source_url=u),
        RawFeeTerm(role="RECURRING_CHARGE", amount="$15", currency="USD", basis="per_day", scope="per_pet",
                   condition_type="stay_length_range", condition_min=6, condition_max=None, boundary_unit="nights",
                   evidence_quote="per day per pet for the first six nights, then up to $15 per day", source_url=u)],
        facts=[("pets_allowed", "true", "per day per pet", u)]))
    assert r.status == V.STATUS_COMPLETED and r.contradictions == ()   # sequential tiers, not contradictory
    assert len(r.fee_policy.terms) == 2
    assert env.route == RT.ROUTE_REVIEW and RT.DOWNSTREAM_FEE_SCHEMA_UNSUPPORTED in env.reason_codes


def test_overlapping_terms_route_contradictory():
    asg = _asg("a pet fee of $50 per night and a pet fee of $75 per night")
    u = asg.source_documents[0].source_url
    r, env = _route(asg, _prop(asg, [
        RawFeeTerm(role="RECURRING_CHARGE", amount="$50", currency="USD", basis="per_night",
                   condition_type="unconditional", evidence_quote="a pet fee of $50 per night", source_url=u),
        RawFeeTerm(role="RECURRING_CHARGE", amount="$75", currency="USD", basis="per_night",
                   condition_type="unconditional", evidence_quote="a pet fee of $75 per night", source_url=u)]))
    assert r.status == V.STATUS_CONTRADICTORY                     # genuine overlap -> withheld
    assert env.route == RT.ROUTE_REVIEW and RT.CONTRADICTORY_OFFICIAL_SOURCES in env.reason_codes


def test_per_room_vs_per_pet_scope_distinct():
    asg = _asg("$50 per night per room; a separate $10 per night per pet surcharge")
    u = asg.source_documents[0].source_url
    r, _env = _route(asg, _prop(asg, [
        RawFeeTerm(role="RECURRING_CHARGE", amount="$50", currency="USD", basis="per_night", scope="per_room",
                   condition_type="unconditional", evidence_quote="$50 per night per room", source_url=u),
        RawFeeTerm(role="RECURRING_CHARGE", amount="$10", currency="USD", basis="per_night", scope="per_pet",
                   condition_type="unconditional", evidence_quote="$10 per night per pet surcharge", source_url=u)]))
    scopes = {t.scope for t in r.fee_policy.terms}
    assert scopes == {"per_room", "per_pet"} and r.contradictions == ()   # different scope -> not contradictory


# --------------------------------------------------------------------------- #
# 6. Serialization / identity / envelope + export preservation.
# --------------------------------------------------------------------------- #

def test_policy_deterministic_serialization_and_identity():
    a = PetFeePolicy(terms=(_t("CAP", "150.00", "per_stay"), _t("RECURRING_CHARGE", "50.00", "per_night")),
                     fee_policy_version=V.FEE_POLICY_VERSION)
    b = PetFeePolicy(terms=(_t("RECURRING_CHARGE", "50.00", "per_night"), _t("CAP", "150.00", "per_stay")),
                     fee_policy_version=V.FEE_POLICY_VERSION)
    assert canonical_json(a.to_dict()) == canonical_json(b.to_dict())     # order-independent
    assert a.content_hash() == b.content_hash()
    assert PetFeePolicy.from_dict(a.to_dict()).content_hash() == a.content_hash()   # round-trip
    # A materially different term changes the identity.
    c = PetFeePolicy(terms=(_t("RECURRING_CHARGE", "60.00", "per_night"),), fee_policy_version=V.FEE_POLICY_VERSION)
    assert c.content_hash() != a.content_hash()


def test_envelope_and_parser_roundtrip():
    asg = _asg("pet fee of $50 per night, up to $150 per stay")
    u = asg.source_documents[0].source_url
    payload = json.dumps({"facts": [], "fee_terms": [
        {"role": "RECURRING_CHARGE", "amount": "$50", "currency": "USD", "basis": "per_night",
         "condition_type": "unconditional", "quote": "pet fee of $50 per night", "source_url": u},
        {"role": "CAP", "amount": "$150", "currency": "USD", "basis": "per_stay", "scope": "policy_total",
         "condition_type": "unconditional", "quote": "up to $150 per stay", "source_url": u}]})
    raws = parse_fee_terms(payload, asg)
    assert len(raws) == 2 and raws[0].role in V.FEE_TERM_ROLES
    r, env = _route(asg, _prop(asg, raws, facts=[("pets_allowed", "true", "pet fee of $50 per night", u)]))
    assert env.fee_policy is not None
    back = RT.RoutingEnvelope.from_dict(env.to_dict())            # envelope round-trips with fee_policy
    assert back.fee_policy == env.fee_policy


# --------------------------------------------------------------------------- #
# 7. No regression: benchmark oracle + cross-source contradiction intact.
# --------------------------------------------------------------------------- #

def test_benchmark_oracle_unaffected():
    rep = run_benchmark(FakeProvider(), model="fake-extractor-v1")
    assert rep["benchmark_correct_results"] == 10 and rep["validator_passed_results"] == 10
    assert rep["exact_evidence_match_rate"] == 1.0


# --------------------------------------------------------------------------- #
# 6b. Stage-D fail-closed backstop: scalar-only flattening cannot reach READY.
# --------------------------------------------------------------------------- #

def _scalar(asg, *facts):
    return _prop(asg, (), facts=facts)


def test_backstop_recurring_plus_cap_scalar_only_cannot_route_ready():
    asg = _asg("non-refundable pet fee of $50 per night, up to $150 per stay")
    u = asg.source_documents[0].source_url
    r, env = _route(asg, _scalar(asg, ("pets_allowed", "true", "pet fee of $50 per night", u),
                                 ("pet_fee", "$50", "non-refundable pet fee of $50 per night", u),
                                 ("fee_currency", "USD", "pet fee of $50 per night", u),
                                 ("fee_basis", "per_night", "pet fee of $50 per night", u)))
    assert not any(f.field_name == "pet_fee" and f.state == V.SUPPORTED for f in r.proposed_facts)  # withheld
    assert "rejected_pet_fee:multi_term_fee_unrepresented" in r.warnings
    assert any(w.startswith("multi_term_fee_amounts:") for w in r.warnings)   # diagnostic preserved
    assert env.route == RT.ROUTE_REVIEW and RT.STRUCTURED_FEE_REQUIRED in env.reason_codes
    assert env.publication_eligible is False


def test_backstop_first_n_after_n_scalar_only_cannot_route_ready():
    asg = _asg("up to $25 per day per pet for the first six nights, then up to $15 per day")
    u = asg.source_documents[0].source_url
    r, env = _route(asg, _scalar(asg, ("pets_allowed", "true", "per day per pet", u),
                                 ("pet_fee", "$25", "up to $25 per day per pet for the first six nights", u)))
    assert not any(f.field_name == "pet_fee" and f.state == V.SUPPORTED for f in r.proposed_facts)
    assert env.route == RT.ROUTE_REVIEW and RT.STRUCTURED_FEE_REQUIRED in env.reason_codes


def test_backstop_short_long_tier_scalar_only_cannot_route_ready():
    asg = _asg("a non-refundable fee of $75 for stays of 1 to 7 nights or $150 for 8 or more nights")
    u = asg.source_documents[0].source_url
    r, env = _route(asg, _scalar(asg, ("pets_allowed", "true", "a non-refundable fee of $75", u),
                                 ("pet_fee", "$75", "a non-refundable fee of $75 for stays of 1 to 7 nights", u)))
    assert env.route == RT.ROUTE_REVIEW and RT.STRUCTURED_FEE_REQUIRED in env.reason_codes


# --------------------------------------------------------------------------- #
# 6c. Backstop false-positive protections.
# --------------------------------------------------------------------------- #

def test_repeated_identical_amount_not_multi_term():
    asg = _asg("A $50 pet fee applies. The $50 pet fee is non-refundable.")
    u = asg.source_documents[0].source_url
    r, env = _route(asg, _scalar(asg, ("pets_allowed", "true", "A $50 pet fee applies", u),
                                 ("pet_fee", "$50", "A $50 pet fee applies", u),
                                 ("fee_currency", "USD", "A $50 pet fee applies", u)))
    assert any(f.field_name == "pet_fee" and f.state == V.SUPPORTED for f in r.proposed_facts)  # not withheld
    assert env.route == RT.ROUTE_READY


def test_unrelated_room_rate_not_triggered():
    asg = _asg("Room rates start at $159 per night. A $50 pet fee applies per stay.")
    u = asg.source_documents[0].source_url
    r, _env = _route(asg, _scalar(asg, ("pets_allowed", "true", "A $50 pet fee applies per stay", u),
                                  ("pet_fee", "$50", "A $50 pet fee applies per stay", u)))
    assert any(f.field_name == "pet_fee" and f.state == V.SUPPORTED for f in r.proposed_facts)  # $159 ignored


def test_fee_and_deposit_not_multi_term():
    asg = _asg("A $50 pet fee applies per stay. A refundable deposit of $200 is required.")
    u = asg.source_documents[0].source_url
    r, _env = _route(asg, _scalar(asg, ("pets_allowed", "true", "A $50 pet fee applies per stay", u),
                                  ("pet_fee", "$50", "A $50 pet fee applies per stay", u),
                                  ("refundable_deposit", "$200", "A refundable deposit of $200 is required", u)))
    sup = {f.field_name for f in r.proposed_facts if f.state == V.SUPPORTED}
    assert "pet_fee" in sup and "refundable_deposit" in sup    # distinct scalar fields, not a fee tier


def test_simple_single_fee_still_routes_ready():
    # Representative of the genuinely-simple V2 READY records -- unaffected.
    asg = _asg("Pet Policy: A $75 fee applies per stay.")
    u = asg.source_documents[0].source_url
    r, env = _route(asg, _scalar(asg, ("pets_allowed", "true", "A $75 fee applies per stay", u),
                                 ("pet_fee", "$75", "A $75 fee applies per stay", u),
                                 ("fee_currency", "USD", "A $75 fee applies per stay", u),
                                 ("fee_basis", "per_stay", "A $75 fee applies per stay", u)))
    assert env.route == RT.ROUTE_READY and r.fee_policy is None


def test_offline_replay_zero_network_and_classification(tmp_path):
    from services.research_workers import fee_replay as FR
    export = {"ready_candidates": [], "retry_candidates": [], "rejected_candidates": [],
              "review_candidates": [
                  {"listing_name": "Aloft Columbus University District", "route": "REVIEW",
                   "reason_codes": ["CONTRADICTORY_OFFICIAL_SOURCES"],
                   "contradictions": ["pet_fee: $150 vs $50"], "fee_policy": None},
                  {"listing_name": "Staybridge Suites Columbus Dublin", "route": "REVIEW",
                   "reason_codes": ["DOWNSTREAM_FEE_SCHEMA_UNSUPPORTED"], "contradictions": [],
                   "fee_policy": {"terms": [{"role": "ONE_TIME_CHARGE"}]}}]}
    p = tmp_path / "candidate_export.json"
    p.write_text(json.dumps(export), encoding="utf-8")
    rep = FR.replay_tiered_fee_records(str(p), hotels=("Aloft Columbus University District",
                                                       "Staybridge Suites Columbus Dublin"))
    assert rep["network_calls"] == 0
    by = {r["hotel"]: r["classification"] for r in rep["records"]}
    assert by["Aloft Columbus University District"] == FR.REPLAY_NEEDS_NEW_MODEL   # stored data insufficient
    assert by["Staybridge Suites Columbus Dublin"] == FR.REPLAY_RESEARCH_COMPLETE_DOWNSTREAM
    # Read-only: the source is unchanged and nothing else is written (no baseline touched).
    assert p.read_text(encoding="utf-8") == json.dumps(export)
    assert list(tmp_path.iterdir()) == [p]


def test_contract_versions():
    assert PROMPT_VERSION == "1.6.0" and VALIDATOR_VERSION == "1.5.0"
    assert V.FEE_POLICY_VERSION == "1.0.0"
    assert RT.ROUTING_VERSION == "1.2.0"
    assert RT.DOWNSTREAM_FEE_SCHEMA_UNSUPPORTED in RT.REVIEW_REASONS
    assert RT.STRUCTURED_FEE_REQUIRED in RT.REVIEW_REASONS
