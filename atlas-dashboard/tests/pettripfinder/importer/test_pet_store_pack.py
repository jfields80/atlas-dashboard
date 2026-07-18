"""AES-DATA-003C -- pet supply store Domain Pack: category registration,
pack contract shape, prompt-fragment scoping, and end-to-end recommendation
scenarios N/O/P/Q/R/S/T/U. Static fixtures only -- no network, no live
provider calls."""

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
from scripts.pettripfinder.importer.domain_packs.pet_store import PET_STORE_PACK
from scripts.pettripfinder.importer.domain_packs.registry import default_registry
from scripts.pettripfinder.importer.models import ImportContext

_FIXTURES = Path(__file__).resolve().parent / "fixtures" / "pet_store"


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

def test_3_pet_store_category_registered():
    assert C.CATEGORY_PET_STORE == "pet_store"
    assert C.CATEGORY_PET_STORE in C.IMPORTER_CATEGORIES
    pack = default_registry.for_category(C.CATEGORY_PET_STORE)
    assert pack is PET_STORE_PACK


def test_pet_store_slug_is_service_specific():
    assert C.CATEGORY_SLUG_BY_IMPORTER[C.CATEGORY_PET_STORE] == "pet-stores"


def test_6_pet_pharmacy_not_registered_as_primary_category():
    assert "pet_pharmacy" not in C.IMPORTER_CATEGORIES
    assert "pet_pharmacy" not in default_registry.category_ids()
    # The hyphenated public-slug spelling is never a category id either.
    assert "pet-store" not in default_registry.category_ids()


# --------------------------------------------------------------------------- #
# Pack contract shape.
# --------------------------------------------------------------------------- #

def test_pack_id_and_version():
    assert PET_STORE_PACK.pack_id == "pettripfinder-pet-store"
    assert PET_STORE_PACK.pack_version == "1.0.0"
    assert PET_STORE_PACK.detail_schema_version == "1.0.0"


def test_pack_category_ids_is_exactly_pet_store():
    assert PET_STORE_PACK.category_ids == (C.CATEGORY_PET_STORE,)


def test_7_allowed_fields_exact():
    expected = {
        "name", "address", "phone",
        "retail_products", "pet_food", "pet_supplies", "pharmacy",
        "prescription_fulfillment", "prescription_food", "grooming_offered",
        "self_wash", "vaccination_clinic", "live_animals", "curbside_pickup",
        "delivery", "online_ordering", "booking_url",
        "hours",
    }
    assert PET_STORE_PACK.allowed_fields == expected
    assert allowed_fields(C.CATEGORY_PET_STORE) == expected


def test_8_field_order_deterministic_and_matches_allowed():
    assert len(PET_STORE_PACK.field_order) == len(set(PET_STORE_PACK.field_order))
    assert set(PET_STORE_PACK.field_order) == PET_STORE_PACK.allowed_fields
    assert allowed_field_order(C.CATEGORY_PET_STORE) == PET_STORE_PACK.field_order


def test_high_risk_capabilities_exact():
    assert set(PET_STORE_PACK.high_risk_capabilities) == {
        "prescription_fulfillment", "vaccination_clinic", "live_animals"}
    assert "pharmacy" not in PET_STORE_PACK.high_risk_capabilities
    assert "self_wash" not in PET_STORE_PACK.high_risk_capabilities
    assert "grooming_offered" not in PET_STORE_PACK.high_risk_capabilities


def test_source_roles_cover_expected_ids():
    role_ids = {r.role_id for r in PET_STORE_PACK.source_roles}
    assert role_ids == {"location", "products", "services", "pharmacy",
                        "ordering", "delivery", "hours", "contact"}


def test_pack_is_frozen():
    with pytest.raises(FrozenInstanceError):
        PET_STORE_PACK.pack_version = "9.9.9"


# --------------------------------------------------------------------------- #
# 9-10. Prompt fragment.
# --------------------------------------------------------------------------- #

def test_9_prompt_fragment_non_empty_and_scoped():
    assert PET_STORE_PACK.prompt_fragment
    assert "PET-STORE" in PET_STORE_PACK.prompt_fragment.upper()


@pytest.mark.parametrize("phrase", [
    "prescription_fulfillment=true ONLY", "prescription_food=true ONLY",
    "self-wash", "vaccination_clinic=true ONLY", "delivery=true ONLY when",
    "live_animals=true ONLY", "online_ordering", "chain-wide or company-level",
])
def test_prompt_fragment_covers_doctrine_phrase(phrase):
    assert phrase.lower() in PET_STORE_PACK.prompt_fragment.lower()


# --------------------------------------------------------------------------- #
# 40-53. End-to-end scenarios via the real pipeline.
# --------------------------------------------------------------------------- #

def test_40_scenario_n_food_and_supplies_ready(tmp_path):
    c = _run("store_n_food_and_supplies", tmp_path)
    assert c.recommendation == C.RECOMMEND_READY
    assert c.recommendation_reasons == ()
    ids = {cap.capability_id for cap in c.capabilities}
    assert ids == {"retail_products", "pet_food", "pet_supplies"}
    assert c.pack_id == "pettripfinder-pet-store"


def test_41_pharmacy_explicit(tmp_path):
    c = _run("store_o_pharmacy_no_prescription_fulfillment", tmp_path)
    assert c.recommendation == C.RECOMMEND_READY
    by_id = {cap.capability_id: cap for cap in c.capabilities}
    assert by_id["pharmacy"].state == "SUPPORTED"


def test_42_pharmacy_does_not_imply_prescription_fulfillment(tmp_path):
    c = _run("store_o_pharmacy_no_prescription_fulfillment", tmp_path)
    ids = {cap.capability_id for cap in c.capabilities}
    assert "prescription_fulfillment" not in ids


def test_43_prescription_food_explicit(tmp_path):
    c = _run("store_p_prescription_food_and_fulfillment", tmp_path)
    assert c.recommendation == C.RECOMMEND_READY
    by_id = {cap.capability_id: cap for cap in c.capabilities}
    assert by_id["prescription_food"].state == "SUPPORTED"
    assert by_id["prescription_fulfillment"].state == "SUPPORTED"
    assert by_id["prescription_fulfillment"].high_risk is True


def test_44_self_wash_does_not_imply_grooming(tmp_path):
    c = _run("store_q_self_wash_no_grooming", tmp_path)
    assert c.recommendation == C.RECOMMEND_READY
    by_id = {cap.capability_id: cap for cap in c.capabilities}
    assert by_id["self_wash"].state == "SUPPORTED"
    assert "grooming_offered" not in by_id


def test_45_grooming_explicit(tmp_path):
    c = _run("store_p_prescription_food_and_fulfillment", tmp_path)
    assert "grooming_offered" not in {cap.capability_id for cap in c.capabilities}


def test_46_vaccination_clinic_explicit(tmp_path):
    c = _run("store_s_vaccination_clinic", tmp_path)
    assert c.recommendation == C.RECOMMEND_READY
    by_id = {cap.capability_id: cap for cap in c.capabilities}
    assert by_id["vaccination_clinic"].state == "SUPPORTED"
    assert by_id["vaccination_clinic"].high_risk is True


def test_48_imagery_does_not_prove_live_animals(tmp_path):
    c = _run("store_t_live_animal_ambiguity", tmp_path)
    assert c.recommendation == C.RECOMMEND_READY
    assert "live_animals" not in {cap.capability_id for cap in c.capabilities}


def test_49_curbside_does_not_imply_delivery(tmp_path):
    c = _run("store_r_curbside_no_delivery", tmp_path)
    assert c.recommendation == C.RECOMMEND_READY
    by_id = {cap.capability_id: cap for cap in c.capabilities}
    assert by_id["curbside_pickup"].state == "SUPPORTED"
    assert "delivery" not in by_id


def test_52_generic_website_does_not_imply_ordering(tmp_path):
    for name in ("store_n_food_and_supplies", "store_o_pharmacy_no_prescription_fulfillment",
                "store_q_self_wash_no_grooming"):
        c = _run(name, tmp_path)
        assert "online_ordering" not in {cap.capability_id for cap in c.capabilities}


def test_53_scenario_u_chain_location_ambiguity_review(tmp_path):
    c = _run("store_u_chain_wide_multi_location", tmp_path)
    assert c.recommendation == C.RECOMMEND_REVIEW
    assert C.REASON_MULTI_ENTITY in c.recommendation_reasons
    # The chain-wide grooming/pharmacy marketing text never becomes a
    # capability -- only the location-neutral retail_products fact does.
    ids = {cap.capability_id for cap in c.capabilities}
    assert ids == {"retail_products"}
    assert "grooming_offered" not in ids
    assert "pharmacy" not in ids


def test_compatibility_summary_pet_store(tmp_path):
    c = _run("store_n_food_and_supplies", tmp_path)
    policy = dict(c.proposed_fields)["pet_policy"]
    assert policy
    assert "pet" in policy.lower()
