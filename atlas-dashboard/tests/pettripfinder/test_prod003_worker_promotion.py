"""PETTRIPFINDER-PROD-003 Gate 2 (Stage D) -- Option-A promotion-adapter tests.

The gate and mapping tests are self-contained (synthetic approvals/Gate-1 records),
so they pass in a clean clone. The end-to-end dry-run tests use the committed
approval manifest + the gitignored Gate-1 manifest and skip when it is absent.
No test performs an operational write; --apply is never invoked.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.pettripfinder import prod003_approvals as PA
from scripts.pettripfinder import promote_worker_candidates as PROM

_HASH_A = "sha256:" + "a" * 64
_URL = "https://official.example/policies"


def _fact(field, value, quote, stype="OFFICIAL_PROPERTY"):
    return {"field_name": field, "value": value, "evidence_quote": quote,
            "source_url": _URL, "source_type": stype}


def _g1(key, **over):
    base = dict(listing_key=key, listing_name=key.title(), candidate_identity=_HASH_A,
                final_route="READY", reason_codes=["PUBLICATION_ELIGIBLE"],
                multi_amount_detected=False, source_urls=[_URL], verification_date="2026-07-15",
                model_id="gpt-5.4-nano-2026-03-17", extraction_prompt_version="1.4.0",
                rederivation_validator_version="1.5.0", rederivation_routing_version="1.2.0",
                supported_facts=[_fact("pets_allowed", "true", "Pets welcome")])
    base.update(over)
    return base


def _approval(key, **over):
    base = dict(listing_key=key, listing_name=key.title(), result_hash=_HASH_A, source_url=_URL,
                verification_date="2026-07-15", gate1_route="READY",
                decision=PA.DECISION_APPROVED, operator="Jonathan Fields", approval_date="2026-07-23")
    base.update(over)
    return base


def _ctx(key, g1rec, *, committed=(), corpus=(), display=None, manual=None):
    return {"approvals": {"approvals": []}, "g1_safe": {key: g1rec} if g1rec else {},
            "g1_manual": manual or {}, "committed_keys": set(committed),
            "corpus_ready": set(corpus), "prod_display": display or {key: g1rec["listing_name"]}
            if g1rec else {}, "committed_count": len(committed)}


def _eval(key, g1rec, approval=None, **ctx_over):
    ctx = _ctx(key, g1rec, **ctx_over)
    return PROM.evaluate(approval or _approval(key), ctx, [key])


# --------------------------------------------------------------------------- #
# Gate rejections (self-contained).
# --------------------------------------------------------------------------- #

def test_clean_record_passes_all_gates():
    key = "clean hotel"
    r = _eval(key, _g1(key))
    assert r["excluded"] is False and r["failures"] == []
    assert r["mapped_corpus_candidate"] is not None


def test_stale_result_hash_rejected():
    key = "h"
    r = _eval(key, _g1(key, candidate_identity="sha256:" + "b" * 64))
    assert "stale_result_hash" in r["failures"] and r["excluded"]


def test_non_approved_decision_not_selected():
    r = PROM.evaluate(_approval("h", decision=PA.DECISION_HOLD), _ctx("h", _g1("h")), ["h"])
    assert r["excluded"] and any(f.startswith("decision:") for f in r["failures"])


def test_manual_review_record_rejected():
    key = "held hotel"
    ctx = {"approvals": {"approvals": []}, "g1_safe": {}, "g1_manual": {key: _g1(key)},
           "committed_keys": set(), "corpus_ready": set(), "prod_display": {}, "committed_count": 0}
    r = PROM.evaluate(_approval(key), ctx, [key])
    assert "manual_review_record" in r["failures"]


def test_non_ready_route_rejected():
    key = "h"
    r = _eval(key, _g1(key, final_route="REVIEW"))
    assert "gate1_route_not_ready" in r["failures"]


def test_multi_term_fee_signal_rejected():
    key = "h"
    r = _eval(key, _g1(key, multi_amount_detected=True))
    assert "multi_term_fee_signal" in r["failures"]


def test_contradiction_rejected():
    key = "h"
    r = _eval(key, _g1(key, reason_codes=["CONTRADICTORY_OFFICIAL_SOURCES"]))
    assert "contradiction" in r["failures"]


def test_incomplete_extraction_rejected():
    key = "h"
    r = _eval(key, _g1(key, reason_codes=["INCOMPLETE_EXTRACTION"]))
    assert "incomplete_extraction" in r["failures"]


def test_source_authority_ambiguity_rejected():
    key = "h"
    r = _eval(key, _g1(key, reason_codes=["SOURCE_AUTHORITY_AMBIGUITY"]))
    assert "source_authority_ambiguity" in r["failures"]


def test_collision_with_committed_package_rejected():
    key = "h"
    r = _eval(key, _g1(key), committed=[key])
    assert "collision_committed_package" in r["failures"]


def test_collision_with_existing_corpus_rejected():
    key = "h"
    r = _eval(key, _g1(key), corpus=[key])
    assert "collision_existing_corpus_record" in r["failures"]


def test_duplicate_listing_identity_rejected():
    key = "h"
    ctx = _ctx(key, _g1(key))
    r = PROM.evaluate(_approval(key), ctx, [key, key])          # appears twice in the batch
    assert "duplicate_listing_identity" in r["failures"]


def test_missing_production_row_rejected():
    key = "h"
    ctx = _ctx(key, _g1(key), display={})                       # no display row
    ctx["prod_display"] = {}
    r = PROM.evaluate(_approval(key), ctx, [key])
    assert "no_production_display_row" in r["failures"]


# --------------------------------------------------------------------------- #
# Mapping (self-contained).
# --------------------------------------------------------------------------- #

def test_every_approved_field_mapping():
    key = "rich hotel"
    g1 = _g1(key, supported_facts=[
        _fact("pets_allowed", "true", "Dogs and cats accepted"),
        _fact("dogs_accepted", "true", "Dogs and cats accepted"),
        _fact("cats_accepted", "true", "Dogs and cats accepted"),
        _fact("pet_fee", "$50", "$50 per room per night fee"),
        _fact("fee_basis", "per_room_per_night", "$50 per room per night fee"),
        _fact("maximum_pets", "2", "limit two pets per room"),
        _fact("weight_limit", "80 pounds", "combined weight of 80 pounds"),
        _fact("breed_restrictions", "No breed restrictions", "No breed restrictions"),
        _fact("unattended_pet_rule", "Pets may not be left unattended", "pets may not be left unattended")])
    cand, transforms, unmapped, fail = PROM.build_mapping(_approval(key), g1, "Rich Hotel")
    assert fail is None
    pf = dict(cand["pet_facts"])
    assert pf["pets_allowed"] == "true"
    assert pf["species_allowed"] == "dogs, cats"
    assert pf["pet_fee"] == "$50"
    assert pf["fee_basis"] == "per room per night"
    assert pf["pet_count_limit"] == "2"
    assert pf["weight_limit"] == "80 pounds"
    assert pf["breed_restrictions"] == "No breed restrictions"
    assert pf["unattended_policy"] == "Pets may not be left unattended"
    assert "general_restrictions" not in pf                     # never invented


def test_species_mapping_without_inference():
    key = "dogs only"
    g1 = _g1(key, supported_facts=[_fact("dogs_accepted", "true", "Dogs only")])
    cand, _, _, fail = PROM.build_mapping(_approval(key), g1, "Dogs Only")
    assert fail is None and dict(cand["pet_facts"]).get("species_allowed") == "dogs"
    # generic pets welcome -> no species field at all
    g2 = _g1(key, supported_facts=[_fact("pets_allowed", "true", "Pets welcome")])
    cand2, _, _, _ = PROM.build_mapping(_approval(key), g2, "Generic")
    assert "species_allowed" not in dict(cand2["pet_facts"])


def test_fee_basis_value_mapping():
    for token, phrase in PROM.FEE_BASIS_MAP.items():
        key = "h"
        g1 = _g1(key, supported_facts=[_fact("pet_fee", "$50", "$50 fee " + phrase),
                                       _fact("fee_basis", token, "$50 fee " + phrase)])
        cand, _, _, fail = PROM.build_mapping(_approval(key), g1, "H")
        assert fail is None and dict(cand["pet_facts"])["fee_basis"] == phrase


def test_unknown_fee_basis_fails_closed():
    key = "h"
    g1 = _g1(key, supported_facts=[_fact("pet_fee", "$50", "$50 fee"),
                                   _fact("fee_basis", "per_pet_per_stay", "$50 fee")])
    cand, _, _, fail = PROM.build_mapping(_approval(key), g1, "H")
    assert cand is None and fail.startswith("unknown_fee_basis_value:")
    # and the record is excluded end-to-end
    r = _eval(key, g1)
    assert any(f.startswith("unknown_fee_basis_value") for f in r["failures"])


def test_unmapped_facts_retained_in_provenance_never_forcefit():
    key = "h"
    g1 = _g1(key, supported_facts=[
        _fact("pets_allowed", "true", "Pets welcome"),
        _fact("fee_currency", "USD", "$50 fee"),
        _fact("refundable_deposit", "$100", "$100 refundable deposit"),
        _fact("service_animal_note", "free of charge", "service animals free of charge")])
    cand, _, unmapped, fail = PROM.build_mapping(_approval(key), g1, "H")
    assert fail is None
    pf = dict(cand["pet_facts"])
    assert "general_restrictions" not in pf                     # service_animal_note NOT force-fit
    fields = {u["field"] for u in unmapped}
    assert fields == {"fee_currency", "refundable_deposit", "service_animal_note"}
    san = [u for u in unmapped if u["field"] == "service_animal_note"][0]
    assert san["reason"] == "must_not_map_to_general_restrictions"
    assert cand["worker_provenance"]["unmapped_facts"] == unmapped


def test_exact_evidence_result_hash_and_approval_metadata_preserved():
    key = "h"
    g1 = _g1(key, supported_facts=[_fact("pets_allowed", "true", "Pets welcome"),
                                   _fact("pet_fee", "$50", "$50 per night fee")])
    cand, _, _, _ = PROM.build_mapping(_approval(key), g1, "H")
    quotes = [e["quote"] for e in cand["evidence"]]
    assert quotes == ["Pets welcome", "$50 per night fee"]      # verbatim, preserved
    prov = cand["worker_provenance"]
    assert prov["result_hash"] == _HASH_A
    assert prov["prompt_version"] == "1.4.0" and prov["validator_version"] == "1.5.0"
    assert prov["routing_version"] == "1.2.0" and prov["model_id"] == "gpt-5.4-nano-2026-03-17"
    assert prov["approval"] == {"decision": PA.DECISION_APPROVED,
                                "operator": "Jonathan Fields", "approval_date": "2026-07-23"}


def test_report_carries_no_credentials():
    key = "h"
    ctx = {"approvals": {"approvals": [_approval(key)]}, "g1_safe": {key: _g1(key)},
           "g1_manual": {}, "committed_keys": set(), "corpus_ready": set(),
           "prod_display": {key: "H"}, "committed_count": 0}
    report = PROM.build_report(ctx, PROM.evaluate_all(ctx))
    blob = json.dumps(report).lower()
    for secret in ("sk-", "api_key", "apikey", "bearer ", "password", "authorization"):
        assert secret not in blob


# --------------------------------------------------------------------------- #
# End-to-end dry run over the committed manifest (skips without Gate-1 data).
# --------------------------------------------------------------------------- #

def _gate1_present():
    return PROM.GATE1_MANIFEST_PATH.exists()


def test_committed_dry_run_selects_nine_and_excludes_held(tmp_path):
    if not _gate1_present():
        pytest.skip("Gate-1 manifest absent (gitignored); end-to-end dry run skipped")
    report = PROM.run_dry_run(tmp_path / "dry")
    c = report["counts"]
    assert c["approved_selected"] == 9 and c["passed_all_gates"] == 9 and c["excluded_by_gate"] == 1
    held = [r for r in report["records"] if r["excluded"]]
    assert len(held) == 1 and held[0]["listing_key"] == "drury plaza hotel columbus downtown"
    assert report["future_package"] == {
        "current_record_count": 5, "proposed_added": 9, "expected_total": 14,
        "would_change": True, "contingent_on": report["future_package"]["contingent_on"]}


def test_dry_run_is_deterministic_and_idempotent(tmp_path):
    if not _gate1_present():
        pytest.skip("Gate-1 manifest absent (gitignored); determinism check skipped")
    PROM.run_dry_run(tmp_path / "a")
    PROM.run_dry_run(tmp_path / "b")
    assert ((tmp_path / "a" / "promotion_report.json").read_bytes()
            == (tmp_path / "b" / "promotion_report.json").read_bytes())


def test_dry_run_writes_only_under_out_dir_and_no_operational_data(tmp_path):
    if not _gate1_present():
        pytest.skip("Gate-1 manifest absent (gitignored); zero-write check skipped")
    committed = PROM.COMMITTED_PACKAGE_PATH.read_bytes()
    out = tmp_path / "dry"
    PROM.run_dry_run(out)
    # committed launch package byte-identical; dedicated promotion root never created
    assert PROM.COMMITTED_PACKAGE_PATH.read_bytes() == committed
    assert not PROM.PROMOTION_ROOT.exists()
    # only the two report files exist under out_dir
    assert sorted(p.name for p in out.iterdir()) == ["promotion_diff.md", "promotion_report.json"]
