"""AES-DATA-003C -- pet grooming Domain Pack: category registration, pack
contract shape, prompt-fragment scoping, and end-to-end recommendation
scenarios H/I/J/K/L. Static fixtures only -- no network, no live provider
calls."""

from __future__ import annotations

import json
from dataclasses import FrozenInstanceError
from pathlib import Path

import pytest

from repositories.artifact_store_repository import ArtifactStoreRepository
from scripts.import_official_url import _build_static
from scripts.pettripfinder.importer import constants as C
from scripts.pettripfinder.importer.candidate import run_import
from scripts.pettripfinder.importer.category_templates import (
    allowed_field_order,
    allowed_fields,
)
from scripts.pettripfinder.importer.domain_packs.grooming import GROOMING_PACK
from scripts.pettripfinder.importer.domain_packs.registry import default_registry
from scripts.pettripfinder.importer.models import ImportContext

_FIXTURES = Path(__file__).resolve().parent / "fixtures" / "grooming"


def _run(name, tmp_path, created_at="1970-01-01T00:00:00"):
    obj = json.loads((_FIXTURES / (name + ".json")).read_text(encoding="utf-8"))
    url = obj["url"]
    fetcher, extractor = _build_static(url, str(_FIXTURES / (name + ".json")))
    ctx = ImportContext(**obj.get("context", {}))
    cas = ArtifactStoreRepository(tmp_path / "cas")
    return run_import(url, ctx, fetcher=fetcher, extractor=extractor, cas=cas,
                      observed_at="2026-07-18", created_at=created_at)


# --------------------------------------------------------------------------- #
# Category registration.
# --------------------------------------------------------------------------- #

def test_2_grooming_category_registered():
    assert C.CATEGORY_GROOMING == "grooming"
    assert C.CATEGORY_GROOMING in C.IMPORTER_CATEGORIES
    pack = default_registry.for_category(C.CATEGORY_GROOMING)
    assert pack is GROOMING_PACK


def test_grooming_slug_is_service_specific():
    assert C.CATEGORY_SLUG_BY_IMPORTER[C.CATEGORY_GROOMING] == "pet-grooming"


def test_5_mobile_grooming_not_registered_as_primary_category():
    assert "mobile_grooming" not in C.IMPORTER_CATEGORIES
    assert "mobile_grooming" not in default_registry.category_ids()


# --------------------------------------------------------------------------- #
# Pack contract shape.
# --------------------------------------------------------------------------- #

def test_pack_id_and_version():
    assert GROOMING_PACK.pack_id == "pettripfinder-grooming"
    assert GROOMING_PACK.pack_version == "1.0.0"
    assert GROOMING_PACK.detail_schema_version == "1.0.0"


def test_pack_category_ids_is_exactly_grooming():
    assert GROOMING_PACK.category_ids == (C.CATEGORY_GROOMING,)


def test_7_allowed_fields_exact():
    expected = {
        "name", "address", "phone",
        "grooming_offered", "dog_grooming", "cat_grooming", "bathing",
        "nail_trimming", "deshedding", "mobile_service", "appointment_required",
        "walk_ins_accepted", "pricing_available",
        "breed_restrictions", "size_restrictions", "service_area", "booking_url",
        "hours",
    }
    assert GROOMING_PACK.allowed_fields == expected
    assert allowed_fields(C.CATEGORY_GROOMING) == expected


def test_8_field_order_deterministic_and_matches_allowed():
    assert len(GROOMING_PACK.field_order) == len(set(GROOMING_PACK.field_order))
    assert set(GROOMING_PACK.field_order) == GROOMING_PACK.allowed_fields
    assert allowed_field_order(C.CATEGORY_GROOMING) == GROOMING_PACK.field_order


def test_high_risk_capabilities_exact():
    assert set(GROOMING_PACK.high_risk_capabilities) == {
        "walk_ins_accepted", "mobile_service", "service_area"}
    assert "cat_grooming" not in GROOMING_PACK.high_risk_capabilities
    assert "dog_grooming" not in GROOMING_PACK.high_risk_capabilities


def test_source_roles_cover_expected_ids():
    role_ids = {r.role_id for r in GROOMING_PACK.source_roles}
    assert role_ids == {"location", "services", "restrictions", "pricing",
                        "service_area", "booking", "hours", "contact"}


def test_pack_is_frozen():
    with pytest.raises(FrozenInstanceError):
        GROOMING_PACK.pack_version = "9.9.9"


# --------------------------------------------------------------------------- #
# 9-10. Prompt fragment.
# --------------------------------------------------------------------------- #

def test_9_prompt_fragment_non_empty_and_scoped():
    assert GROOMING_PACK.prompt_fragment
    assert "GROOMING" in GROOMING_PACK.prompt_fragment.upper()


@pytest.mark.parametrize("phrase", [
    "dog_grooming or cat_grooming", "walk_ins_accepted=true ONLY",
    "same-day appointments", "mobile_service=true ONLY",
    "never inferred from the business's own street address",
    "never infer",
])
def test_prompt_fragment_covers_doctrine_phrase(phrase):
    assert phrase.lower() in GROOMING_PACK.prompt_fragment.lower()


# --------------------------------------------------------------------------- #
# 26-39. End-to-end scenarios via the real pipeline.
# --------------------------------------------------------------------------- #

def test_26_scenario_h_dog_grooming_ready(tmp_path):
    c = _run("groom_h_dog_grooming_appointment", tmp_path)
    assert c.recommendation == C.RECOMMEND_READY
    assert c.recommendation_reasons == ()
    ids = {cap.capability_id for cap in c.capabilities}
    assert ids == {"grooming_offered", "dog_grooming", "bathing", "nail_trimming",
                   "appointment_required"}
    assert "cat_grooming" not in ids
    assert c.pack_id == "pettripfinder-grooming"


def test_27_cat_grooming_explicit_only(tmp_path):
    c = _run("groom_i_cat_grooming_explicit", tmp_path)
    assert c.recommendation == C.RECOMMEND_READY
    by_id = {cap.capability_id: cap for cap in c.capabilities}
    assert by_id["cat_grooming"].state == "SUPPORTED"
    c2 = _run("groom_h_dog_grooming_appointment", tmp_path)
    assert "cat_grooming" not in {cap.capability_id for cap in c2.capabilities}


def test_28_grooming_does_not_infer_dog_or_cat(tmp_path):
    c = _run("groom_k_generic_grooming_only", tmp_path)
    assert c.recommendation == C.RECOMMEND_READY
    ids = {cap.capability_id for cap in c.capabilities}
    assert ids == {"grooming_offered"}
    assert "dog_grooming" not in ids
    assert "cat_grooming" not in ids


def test_29_bathing_explicit(tmp_path):
    c = _run("groom_h_dog_grooming_appointment", tmp_path)
    by_id = {cap.capability_id: cap for cap in c.capabilities}
    assert by_id["bathing"].state == "SUPPORTED"


def test_30_nail_trimming_explicit(tmp_path):
    c = _run("groom_h_dog_grooming_appointment", tmp_path)
    by_id = {cap.capability_id: cap for cap in c.capabilities}
    assert by_id["nail_trimming"].state == "SUPPORTED"


def test_31_deshedding_explicit(tmp_path):
    c = _run("groom_i_cat_grooming_explicit", tmp_path)
    by_id = {cap.capability_id: cap for cap in c.capabilities}
    assert by_id["deshedding"].state == "SUPPORTED"


def test_32_appointment_required(tmp_path):
    c = _run("groom_h_dog_grooming_appointment", tmp_path)
    by_id = {cap.capability_id: cap for cap in c.capabilities}
    assert by_id["appointment_required"].state == "SUPPORTED"


def test_33_walk_ins_supported_only_explicitly(tmp_path):
    for name in ("groom_h_dog_grooming_appointment", "groom_k_generic_grooming_only"):
        c = _run(name, tmp_path)
        assert "walk_ins_accepted" not in {cap.capability_id for cap in c.capabilities}


def test_34_no_walk_ins_explicitly_absent(tmp_path):
    c = _run("groom_l_no_walk_ins", tmp_path)
    assert c.recommendation == C.RECOMMEND_READY
    by_id = {cap.capability_id: cap for cap in c.capabilities}
    assert by_id["walk_ins_accepted"].state == "EXPLICITLY_ABSENT"
    assert by_id["walk_ins_accepted"].high_risk is True


def test_35_mobile_service_explicit(tmp_path):
    c = _run("groom_j_mobile_service_area", tmp_path)
    assert c.recommendation == C.RECOMMEND_READY
    by_id = {cap.capability_id: cap for cap in c.capabilities}
    assert by_id["mobile_service"].state == "SUPPORTED"
    assert by_id["mobile_service"].high_risk is True


def test_36_service_area_text_retained(tmp_path):
    c = _run("groom_j_mobile_service_area", tmp_path)
    by_id = {cap.capability_id: cap for cap in c.capabilities}
    assert by_id["service_area"].value == "Columbus and surrounding suburbs"
    assert by_id["service_area"].high_risk is True


def test_37_address_does_not_infer_service_area(tmp_path):
    # Scenario H has a full street address but no service-area statement.
    c = _run("groom_h_dog_grooming_appointment", tmp_path)
    assert "service_area" not in {cap.capability_id for cap in c.capabilities}


def test_38_restriction_omitted_not_defaulted(tmp_path):
    # No fixture states a restriction; prove the field is simply absent
    # rather than defaulted to "none" (doctrine: never infer "no
    # restrictions" from silence).
    c = _run("groom_h_dog_grooming_appointment", tmp_path)
    ids = {cap.capability_id for cap in c.capabilities}
    assert "breed_restrictions" not in ids
    assert "size_restrictions" not in ids


def test_compatibility_summary_grooming(tmp_path):
    c = _run("groom_h_dog_grooming_appointment", tmp_path)
    policy = dict(c.proposed_fields)["pet_policy"]
    assert policy
    assert "groom" in policy.lower()
