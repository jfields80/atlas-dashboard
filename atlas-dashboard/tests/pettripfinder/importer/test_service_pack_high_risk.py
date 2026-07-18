"""AES-DATA-003C -- shared projection-helper unit tests (Task 8) and
high-risk / non-inference doctrine proofs (Task 16) across boarding,
grooming, and pet_store. Static fixtures only -- no network, no live
provider calls."""

from __future__ import annotations

import json
import tempfile
from pathlib import Path

import pytest

from repositories.artifact_store_repository import ArtifactStoreRepository
from scripts.import_official_url import _build_static
from scripts.pettripfinder.importer import constants as C
from scripts.pettripfinder.importer.candidate import candidate_from_dict, dumps_candidate, run_import
from scripts.pettripfinder.importer.domain_packs.base import CapabilityState
from scripts.pettripfinder.importer.domain_packs.projection import (
    CapabilityProjectionRule,
    high_risk_capability_conflict,
    project_capabilities,
    service_evidence_present,
)
from scripts.pettripfinder.importer.models import Conflict, ExtractedEvidence, ImportContext

_BOARDING_FIXTURES = Path(__file__).resolve().parent / "fixtures" / "boarding"
_GROOMING_FIXTURES = Path(__file__).resolve().parent / "fixtures" / "grooming"
_PET_STORE_FIXTURES = Path(__file__).resolve().parent / "fixtures" / "pet_store"


def _run(fixtures_dir, name, tmp_path, created_at="1970-01-01T00:00:00"):
    obj = json.loads((fixtures_dir / (name + ".json")).read_text(encoding="utf-8"))
    url = obj["url"]
    fetcher, extractor = _build_static(url, str(fixtures_dir / (name + ".json")))
    ctx = ImportContext(**obj.get("context", {}))
    cas = ArtifactStoreRepository(tmp_path / "cas")
    return run_import(url, ctx, fetcher=fetcher, extractor=extractor, cas=cas,
                      observed_at="2026-07-18", created_at=created_at)


def _ev(field, value, url="https://x.test"):
    return ExtractedEvidence(
        field_name=field, proposed_value=value, source_wording=value, source_url=url,
        snapshot_quote=value, char_start=0, char_end=len(value),
        extraction_method=C.METHOD_LLM_TEXT, support_state=C.SUPPORT_SUPPORTED, warnings=())


_RULES = (
    CapabilityProjectionRule("boarding_offered", "boarding_offered", "bool", high_risk=False),
    CapabilityProjectionRule("cat_boarding", "cat_boarding", "bool", high_risk=True),
    CapabilityProjectionRule("vaccination_requirements", "vaccination_requirements", "text"),
)


# --------------------------------------------------------------------------- #
# Shared projection-helper unit tests (Task 8; parity with veterinary's
# proven 003B behavior, now generalized).
# --------------------------------------------------------------------------- #

def test_missing_fact_is_omitted_not_unknown():
    assert project_capabilities({}, (), _RULES) == ()


def test_boolean_true_is_supported():
    caps = project_capabilities(
        {"boarding_offered": "true"}, (_ev("boarding_offered", "true"),), _RULES)
    assert caps[0].state == CapabilityState.SUPPORTED.value


def test_boolean_false_is_explicitly_absent():
    caps = project_capabilities(
        {"cat_boarding": "false"}, (_ev("cat_boarding", "false"),), _RULES)
    assert caps[0].state == CapabilityState.EXPLICITLY_ABSENT.value
    assert caps[0].high_risk is True


def test_text_field_supported_with_value():
    caps = project_capabilities(
        {"vaccination_requirements": "rabies required"},
        (_ev("vaccination_requirements", "rabies required"),), _RULES)
    assert caps[0].value == "rabies required"


def test_empty_text_omitted():
    assert project_capabilities({"vaccination_requirements": ""}, (), _RULES) == ()


def test_56_evidence_index_points_at_final_evidence_tuple():
    ev = (_ev("boarding_offered", "true"), _ev("cat_boarding", "true"))
    caps = project_capabilities(
        {"boarding_offered": "true", "cat_boarding": "true"}, ev, _RULES)
    by_id = {c.capability_id: c for c in caps}
    assert by_id["boarding_offered"].evidence_index == 0
    assert by_id["cat_boarding"].evidence_index == 1


def test_57_deterministic_capability_ordering():
    facts = {"cat_boarding": "true", "boarding_offered": "true"}
    ev = tuple(_ev(f, "true") for f in facts)
    caps = project_capabilities(facts, ev, _RULES)
    assert [c.capability_id for c in caps] == ["boarding_offered", "cat_boarding"]


def test_58_no_duplicate_capability_ids():
    facts = {"boarding_offered": "true", "cat_boarding": "true"}
    ev = tuple(_ev(f, "true") for f in facts)
    caps = project_capabilities(facts, ev, _RULES)
    ids = [c.capability_id for c in caps]
    assert len(ids) == len(set(ids))


def test_conflicted_field_emits_conflicted_high_risk():
    ev = (_ev("cat_boarding", "true", "https://a.test"),
         _ev("cat_boarding", "false", "https://b.test"))
    conflicts = (Conflict(field_name="cat_boarding", competing_values=("true", "false"),
                          evidence=ev, precedence_note="aggregate_policy_conflict",
                          resolution_status="UNRESOLVED"),)
    caps = project_capabilities({}, ev, _RULES, conflicts)
    assert caps[0].state == CapabilityState.CONFLICTED.value
    assert caps[0].high_risk is True


def test_service_evidence_present_true_for_any_real_state():
    caps = project_capabilities(
        {"boarding_offered": "true"}, (_ev("boarding_offered", "true"),), _RULES)
    assert service_evidence_present(caps) is True
    assert service_evidence_present(()) is False


def test_high_risk_capability_conflict_scoped_to_high_risk_only():
    ev = (_ev("boarding_offered", "true"), _ev("boarding_offered", "false"))
    conflicts = (Conflict(field_name="boarding_offered", competing_values=("true", "false"),
                          evidence=ev, precedence_note="aggregate_policy_conflict",
                          resolution_status="UNRESOLVED"),)
    caps = project_capabilities({}, ev, _RULES, conflicts)
    assert caps[0].high_risk is False
    assert high_risk_capability_conflict(caps) is False


def test_unknown_value_kind_raises():
    bad_rule = (CapabilityProjectionRule("x", "x", "number"),)
    with pytest.raises(ValueError):
        project_capabilities({"x": "1"}, (_ev("x", "1"),), bad_rule)


# --------------------------------------------------------------------------- #
# 62-65. Evidence-validity gating (shared across all three packs).
# --------------------------------------------------------------------------- #

def _run_hostile(category, prompt_facts, page_text, tmp_path):
    url = "https://www.hostile%s.test/" % category
    fixture = {
        "url": url,
        "context": {"category": category, "expected_city": "Columbus", "expected_state": "OH"},
        "html": (
            "<!doctype html><html><head><meta charset='utf-8'>"
            "<script type=\"application/ld+json\">{\"@context\": \"https://schema.org\", "
            "\"@type\": \"LocalBusiness\", \"name\": \"Hostile Test Business\", "
            "\"telephone\": \"614-555-0999\", \"url\": \"%s\", "
            "\"address\": {\"@type\": \"PostalAddress\", \"streetAddress\": \"1 Test St\", "
            "\"addressLocality\": \"Columbus\", \"addressRegion\": \"OH\", "
            "\"postalCode\": \"43215\"}}</script></head>"
            "<body><h1>Hostile Test Business</h1><p>%s</p></body></html>"
        ) % (url, page_text),
        "extraction": {"facts": prompt_facts},
    }
    fp = Path(tempfile.mkdtemp()) / "fixture.json"
    fp.write_text(json.dumps(fixture), encoding="utf-8")
    fetcher, extractor = _build_static(fixture["url"], str(fp))
    ctx = ImportContext(**fixture["context"])
    cas = ArtifactStoreRepository(tmp_path / "cas")
    return run_import(fixture["url"], ctx, fetcher=fetcher, extractor=extractor, cas=cas,
                      observed_at="2026-07-18", created_at="1970-01-01T00:00:00")


def test_62_invalid_evidence_blocks_boarding_capability(tmp_path):
    c = _run_hostile(
        "boarding",
        [{"field": "boarding_offered", "value": "true", "quote": "We offer boarding"},
         {"field": "cat_boarding", "value": "true", "quote": "we board every kind of cat imaginable"}],
        "We offer boarding for dogs.",
        tmp_path)
    assert c.recommendation == C.RECOMMEND_READY
    assert "cat_boarding" not in {cap.capability_id for cap in c.capabilities}
    mismatches = [e for e in c.evidence if e.field_name == "cat_boarding"
                 and e.support_state == C.SUPPORT_UNSUPPORTED]
    assert len(mismatches) == 1


def test_63_missing_evidence_blocks_grooming_capability(tmp_path):
    c = _run_hostile(
        "grooming",
        [{"field": "grooming_offered", "value": "true", "quote": "We groom dogs"},
         {"field": "cat_grooming", "value": "true", "quote": "we lovingly groom every cat breed"}],
        "We groom dogs.",
        tmp_path)
    assert c.recommendation == C.RECOMMEND_READY
    assert "cat_grooming" not in {cap.capability_id for cap in c.capabilities}


def test_64_high_risk_conflict_never_reaches_ready(tmp_path):
    caps = project_capabilities(
        {}, (_ev("cat_boarding", "true", "https://a.test"),
             _ev("cat_boarding", "false", "https://b.test")),
        _RULES,
        (Conflict(field_name="cat_boarding", competing_values=("true", "false"),
                 evidence=(_ev("cat_boarding", "true"), _ev("cat_boarding", "false")),
                 precedence_note="aggregate_policy_conflict", resolution_status="UNRESOLVED"),))
    assert high_risk_capability_conflict(caps) is True
    # end-to-end proof lives in test_service_pack_aggregate.py scenarios M/W


def test_65_explicit_negative_requires_its_own_evidence(tmp_path):
    c = _run_hostile(
        "pet_store",
        [{"field": "retail_products", "value": "true", "quote": "We sell pet food"},
         {"field": "live_animals", "value": "false", "quote": "we do not sell live animals here"}],
        "We sell pet food.",
        tmp_path)
    assert c.recommendation == C.RECOMMEND_READY
    assert "live_animals" not in {cap.capability_id for cap in c.capabilities}


# --------------------------------------------------------------------------- #
# 59-61. CategoryDetail / round-trip / provenance (shared pattern, proven
# once per new category is sufficient -- the mechanism is category-agnostic).
# --------------------------------------------------------------------------- #

def test_59_category_detail_deterministic(tmp_path):
    fixture = {
        "url": "https://www.hoursboarding.test/",
        "context": {"category": "boarding", "expected_city": "Columbus", "expected_state": "OH"},
        "html": ("<!doctype html><html><body><h1>Hours Boarding</h1><p>We offer boarding. "
                 "Open Monday-Friday 7am-7pm.</p></body></html>"),
        "extraction": {"facts": [
            {"field": "boarding_offered", "value": "true", "quote": "We offer boarding"},
            {"field": "hours", "value": "Monday-Friday 7am-7pm", "quote": "Open Monday-Friday 7am-7pm"},
        ]},
    }
    fp = Path(tempfile.mkdtemp()) / "fixture.json"
    fp.write_text(json.dumps(fixture), encoding="utf-8")
    fetcher, extractor = _build_static(fixture["url"], str(fp))
    ctx = ImportContext(**fixture["context"])
    cas = ArtifactStoreRepository(tmp_path / "cas")
    c = run_import(fixture["url"], ctx, fetcher=fetcher, extractor=extractor, cas=cas,
                   observed_at="2026-07-18", created_at="1970-01-01T00:00:00")
    assert c.category_detail is not None
    assert c.category_detail.detail_type == "boarding"
    assert dict(c.category_detail.fields)["hours"] == "Monday-Friday 7am-7pm"
    assert "hours" not in {cap.capability_id for cap in c.capabilities}


def test_60_populated_candidate_round_trip(tmp_path):
    c = _run(_BOARDING_FIXTURES, "board_b_cat_and_dog_boarding", tmp_path)
    blob = dumps_candidate(c)
    restored = candidate_from_dict(json.loads(blob))
    assert len(restored.capabilities) == len(c.capabilities)
    assert restored.pack_id == c.pack_id
    assert dumps_candidate(restored) == blob


def test_61_pack_provenance_serialized(tmp_path):
    for fixtures_dir, name, pack_id in (
        (_BOARDING_FIXTURES, "board_a_dog_boarding_daycare", "pettripfinder-boarding"),
        (_GROOMING_FIXTURES, "groom_h_dog_grooming_appointment", "pettripfinder-grooming"),
        (_PET_STORE_FIXTURES, "store_n_food_and_supplies", "pettripfinder-pet-store"),
    ):
        c = _run(fixtures_dir, name, tmp_path)
        assert c.pack_id == pack_id
        assert c.pack_version == "1.0.0"
        assert c.capability_schema_version
        d = json.loads(dumps_candidate(c))
        assert d["pack_id"] == pack_id


# --------------------------------------------------------------------------- #
# Task 16 non-inference doctrine (boarding/grooming/pet-store).
# --------------------------------------------------------------------------- #

def test_boarding_does_not_imply_dog_boarding(tmp_path):
    c = _run(_BOARDING_FIXTURES, "board_d_generic_pet_boarding_only", tmp_path)
    assert "dog_boarding" not in {cap.capability_id for cap in c.capabilities}


def test_boarding_does_not_imply_cat_boarding(tmp_path):
    c = _run(_BOARDING_FIXTURES, "board_d_generic_pet_boarding_only", tmp_path)
    assert "cat_boarding" not in {cap.capability_id for cap in c.capabilities}


def test_online_booking_does_not_imply_same_day_availability(tmp_path):
    c = _run(_BOARDING_FIXTURES, "board_e_booking_no_availability", tmp_path)
    assert "same_day_availability" not in {cap.capability_id for cap in c.capabilities}


def test_daycare_does_not_imply_walk_ins(tmp_path):
    c = _run(_BOARDING_FIXTURES, "board_a_dog_boarding_daycare", tmp_path)
    assert "walk_ins_accepted" not in {cap.capability_id for cap in c.capabilities}


def test_generic_special_care_does_not_imply_medication_administration(tmp_path):
    c = _run(_BOARDING_FIXTURES, "board_a_dog_boarding_daycare", tmp_path)
    assert "medication_administration" not in {cap.capability_id for cap in c.capabilities}


def test_pet_boarding_does_not_imply_other_species(tmp_path):
    c = _run(_BOARDING_FIXTURES, "board_d_generic_pet_boarding_only", tmp_path)
    assert "other_species_boarding" not in {cap.capability_id for cap in c.capabilities}


def test_grooming_does_not_imply_dog_grooming(tmp_path):
    c = _run(_GROOMING_FIXTURES, "groom_k_generic_grooming_only", tmp_path)
    assert "dog_grooming" not in {cap.capability_id for cap in c.capabilities}


def test_grooming_does_not_imply_cat_grooming(tmp_path):
    c = _run(_GROOMING_FIXTURES, "groom_k_generic_grooming_only", tmp_path)
    assert "cat_grooming" not in {cap.capability_id for cap in c.capabilities}


def test_appointments_do_not_imply_walk_ins(tmp_path):
    c = _run(_GROOMING_FIXTURES, "groom_h_dog_grooming_appointment", tmp_path)
    assert "walk_ins_accepted" not in {cap.capability_id for cap in c.capabilities}


def test_mobile_service_not_inferred_from_delivery_like_wording(tmp_path):
    c = _run(_GROOMING_FIXTURES, "groom_k_generic_grooming_only", tmp_path)
    assert "mobile_service" not in {cap.capability_id for cap in c.capabilities}


def test_no_restriction_inferred_from_silence(tmp_path):
    c = _run(_GROOMING_FIXTURES, "groom_j_mobile_service_area", tmp_path)
    ids = {cap.capability_id for cap in c.capabilities}
    assert "breed_restrictions" not in ids
    assert "size_restrictions" not in ids


def test_pharmacy_does_not_imply_prescription_fulfillment_2(tmp_path):
    c = _run(_PET_STORE_FIXTURES, "store_o_pharmacy_no_prescription_fulfillment", tmp_path)
    assert "prescription_fulfillment" not in {cap.capability_id for cap in c.capabilities}


def test_pet_food_does_not_imply_prescription_food(tmp_path):
    c = _run(_PET_STORE_FIXTURES, "store_n_food_and_supplies", tmp_path)
    assert "prescription_food" not in {cap.capability_id for cap in c.capabilities}


def test_curbside_does_not_imply_delivery_2(tmp_path):
    c = _run(_PET_STORE_FIXTURES, "store_r_curbside_no_delivery", tmp_path)
    assert "delivery" not in {cap.capability_id for cap in c.capabilities}


def test_website_does_not_imply_online_ordering(tmp_path):
    c = _run(_PET_STORE_FIXTURES, "store_n_food_and_supplies", tmp_path)
    assert "online_ordering" not in {cap.capability_id for cap in c.capabilities}


def test_health_products_do_not_imply_vaccination_clinic(tmp_path):
    c = _run(_PET_STORE_FIXTURES, "store_p_prescription_food_and_fulfillment", tmp_path)
    assert "vaccination_clinic" not in {cap.capability_id for cap in c.capabilities}


def test_animal_imagery_does_not_imply_live_animal_sales(tmp_path):
    c = _run(_PET_STORE_FIXTURES, "store_t_live_animal_ambiguity", tmp_path)
    assert "live_animals" not in {cap.capability_id for cap in c.capabilities}


def test_live_animals_explicit_only_positive_case(tmp_path):
    c = _run_hostile(
        "pet_store",
        [{"field": "retail_products", "value": "true", "quote": "We sell pet food"},
         {"field": "live_animals", "value": "true",
          "quote": "Live fish and reptiles are available for adoption at this location"}],
        "We sell pet food. Live fish and reptiles are available for adoption at this location.",
        tmp_path)
    by_id = {cap.capability_id: cap for cap in c.capabilities}
    assert by_id["live_animals"].state == "SUPPORTED"
    assert by_id["live_animals"].high_risk is True


def test_chain_wide_service_not_automatically_location_specific(tmp_path):
    c = _run(_PET_STORE_FIXTURES, "store_u_chain_wide_multi_location", tmp_path)
    ids = {cap.capability_id for cap in c.capabilities}
    assert "grooming_offered" not in ids
    assert "pharmacy" not in ids
