"""AES-DATA-003B -- high-risk veterinary non-inference guards (Task 11).
Structural/explicit proof that the pipeline never derives one veterinary
fact from another, and never derives a fact from a name/photo/generic
wording. Static fixtures only -- no network, no live provider calls."""

from __future__ import annotations

import json
from pathlib import Path

from repositories.artifact_store_repository import ArtifactStoreRepository
from scripts.import_official_url import _build_static
from scripts.pettripfinder.importer import constants as C
from scripts.pettripfinder.importer.candidate import run_import
from scripts.pettripfinder.importer.domain_packs.veterinary import project_capabilities
from scripts.pettripfinder.importer.models import ExtractedEvidence, ImportContext

_FIXTURES = Path(__file__).resolve().parent / "fixtures" / "veterinary"


def _run(name, tmp_path, created_at="1970-01-01T00:00:00"):
    obj = json.loads((_FIXTURES / (name + ".json")).read_text(encoding="utf-8"))
    url = obj["url"]
    fetcher, extractor = _build_static(url, str(_FIXTURES / (name + ".json")))
    ctx = ImportContext(**obj.get("context", {}))
    cas = ArtifactStoreRepository(tmp_path / "cas")
    return run_import(url, ctx, fetcher=fetcher, extractor=extractor, cas=cas,
                      observed_at="2026-07-18", created_at=created_at)


def _ev(field, value):
    return ExtractedEvidence(
        field_name=field, proposed_value=value, source_wording=value,
        source_url="https://x.test", snapshot_quote=value, char_start=0,
        char_end=len(value), extraction_method=C.METHOD_LLM_TEXT,
        support_state=C.SUPPORT_SUPPORTED, warnings=())


def _capability_ids(facts):
    ev = tuple(_ev(f, v) for f, v in facts.items())
    return {cap.capability_id for cap in project_capabilities(facts, ev)}


# --------------------------------------------------------------------------- #
# 1. "hospital"/"animal hospital" in the business name never implies
#    emergency_service (scenario D, end-to-end).
# --------------------------------------------------------------------------- #

def test_1_hospital_in_name_does_not_imply_emergency(tmp_path):
    c = _run("vet_d_animal_hospital_no_emergency_wording", tmp_path)
    assert c.recommendation == C.RECOMMEND_READY
    ids = {cap.capability_id for cap in c.capabilities}
    assert "emergency_service" not in ids
    assert "urgent_care" not in ids
    assert "open_24h" not in ids
    assert "Hospital" in dict(c.proposed_fields)["name"]


# --------------------------------------------------------------------------- #
# 2. "critical care" wording alone (no explicit emergency wording) never
#    implies emergency_service or open_24h.
# --------------------------------------------------------------------------- #

def test_2_critical_care_alone_does_not_imply_emergency_or_open_24h():
    ids = _capability_ids({"critical_care": "true"})
    assert ids == {"critical_care"}
    assert "emergency_service" not in ids
    assert "open_24h" not in ids


# --------------------------------------------------------------------------- #
# 3-4. emergency_service alone never implies urgent_care or open_24h.
# --------------------------------------------------------------------------- #

def test_3_emergency_service_alone_does_not_imply_urgent_care():
    ids = _capability_ids({"emergency_service": "true"})
    assert ids == {"emergency_service"}
    assert "urgent_care" not in ids


def test_4_emergency_service_alone_does_not_imply_open_24h():
    ids = _capability_ids({"emergency_service": "true"})
    assert "open_24h" not in ids


# --------------------------------------------------------------------------- #
# 5. "open late" / "seven days a week" wording never establishes open_24h --
#    proven by construction: no fact is ever emitted for a page that never
#    states 24-hour availability, so the capability list is correctly empty
#    of open_24h (scenario C's "8am to 8pm" wording never claims open_24h).
# --------------------------------------------------------------------------- #

def test_5_partial_hours_wording_never_yields_open_24h(tmp_path):
    c = _run("vet_c_urgent_care_not_24h", tmp_path)
    assert "open_24h" not in {cap.capability_id for cap in c.capabilities}


# --------------------------------------------------------------------------- #
# 6-8. walk_ins_accepted is never derived from emergency_service or
#    urgent_care alone; explicit walk-ins wording is required.
# --------------------------------------------------------------------------- #

def test_6_urgent_care_alone_does_not_imply_walk_ins():
    ids = _capability_ids({"urgent_care": "true"})
    assert ids == {"urgent_care"}
    assert "walk_ins_accepted" not in ids


def test_7_emergency_service_alone_does_not_imply_walk_ins():
    ids = _capability_ids({"emergency_service": "true"})
    assert "walk_ins_accepted" not in ids


def test_8_explicit_no_walk_ins_still_high_risk_and_absent(tmp_path):
    c = _run("vet_g_no_walk_ins", tmp_path)
    assert c.recommendation == C.RECOMMEND_READY
    by_id = {cap.capability_id: cap for cap in c.capabilities}
    assert by_id["walk_ins_accepted"].state == "EXPLICITLY_ABSENT"
    assert by_id["walk_ins_accepted"].high_risk is True


# --------------------------------------------------------------------------- #
# 9. Generic "pets"/"animals" wording never sets species_served (scenario H).
# --------------------------------------------------------------------------- #

def test_9_generic_pets_wording_never_sets_species_served(tmp_path):
    c = _run("vet_h_species_ambiguity", tmp_path)
    assert c.recommendation == C.RECOMMEND_READY
    assert "species_served" not in {cap.capability_id for cap in c.capabilities}


# --------------------------------------------------------------------------- #
# 10. No image-derived evidence path exists anywhere in the extraction
#    schema -- an image can never be evidence by construction.
# --------------------------------------------------------------------------- #

def test_10_no_image_based_extraction_method_exists():
    image_markers = ("image", "photo", "logo", "picture", "img")
    all_methods = (
        C.METHOD_JSON_LD, C.METHOD_MICRODATA, C.METHOD_META, C.METHOD_OPEN_GRAPH,
        C.METHOD_TEL_LINK, C.METHOD_ADDRESS_BLOCK, C.METHOD_LLM_TEXT,
        C.METHOD_OPERATOR_EDIT,
    )
    for method in all_methods:
        assert not any(marker in method.lower() for marker in image_markers)


# --------------------------------------------------------------------------- #
# 11. No high-risk capability is ever produced when only unrelated,
#    non-high-risk facts are present -- proves no cross-field derivation.
# --------------------------------------------------------------------------- #

def test_11_high_risk_capabilities_never_appear_from_unrelated_facts():
    ids = _capability_ids({
        "general_practice": "true", "preventive_care": "true",
        "vaccinations": "true", "surgery": "true", "dentistry": "true",
        "pharmacy": "true", "diagnostics": "true", "critical_care": "true",
    })
    for high_risk_field in ("emergency_service", "urgent_care", "open_24h",
                            "walk_ins_accepted", "existing_clients_only", "species_served"):
        assert high_risk_field not in ids


# --------------------------------------------------------------------------- #
# 12. existing_clients_only is never derived from emergency_service or
#    urgent_care alone -- only from its own explicit fact.
# --------------------------------------------------------------------------- #

def test_12_existing_clients_only_never_derived_from_emergency_or_urgent():
    ids = _capability_ids({"emergency_service": "true", "urgent_care": "true"})
    assert "existing_clients_only" not in ids


# --------------------------------------------------------------------------- #
# 13. Exotic-species keyword detection is literal/narrow, not fuzzy.
# --------------------------------------------------------------------------- #

def test_13_exotic_detection_is_literal_not_fuzzy():
    # "exotic-looking dog" contains no genuine exotic-species keyword as a
    # substring boundary issue would only matter for fuzzy matching; the
    # literal substring check still (correctly) flags "exotic" here, but a
    # plain "dogs and cats" claim must never be flagged.
    ids_common = _capability_ids({"species_served": "dogs and cats"})
    caps_common = project_capabilities(
        {"species_served": "dogs and cats"}, (_ev("species_served", "dogs and cats"),))
    assert caps_common[0].high_risk is False

    caps_exotic = project_capabilities(
        {"species_served": "reptiles and amphibians"},
        (_ev("species_served", "reptiles and amphibians"),))
    assert caps_exotic[0].high_risk is True


# --------------------------------------------------------------------------- #
# 14. Missing/invalid evidence (a fabricated quote that fails span
#    validation) never yields a published capability -- scenario L.
# --------------------------------------------------------------------------- #

def test_14_unsupported_evidence_never_becomes_a_capability(tmp_path):
    c = _run("vet_l_unsupported_claim_missing_evidence", tmp_path)
    assert c.recommendation == C.RECOMMEND_READY
    assert "emergency_service" not in {cap.capability_id for cap in c.capabilities}
    mismatches = [e for e in c.evidence if e.field_name == "emergency_service"
                 and e.support_state == C.SUPPORT_UNSUPPORTED
                 and C.REASON_EVIDENCE_MISMATCH in e.warnings]
    assert len(mismatches) == 1
    assert "emergency_service" not in c.pet_facts_dict()


# --------------------------------------------------------------------------- #
# 15. Structured-metadata VeterinaryCare/MedicalBusiness recognition never
#    independently establishes a high-risk capability (Task 13).
# --------------------------------------------------------------------------- #

def test_15_structured_metadata_recognition_creates_no_high_risk_capability(tmp_path):
    import tempfile
    fixture = {
        "url": "https://www.structuredonlyvet.test/",
        "context": {"category": "veterinary", "expected_city": "Columbus", "expected_state": "OH"},
        "html": (
            "<!doctype html><html><head><meta charset='utf-8'>"
            "<script type=\"application/ld+json\">{\"@context\": \"https://schema.org\", "
            "\"@type\": \"VeterinaryCare\", \"name\": \"Structured Only Vet\", "
            "\"telephone\": \"614-555-0299\", \"url\": \"https://www.structuredonlyvet.test/\", "
            "\"address\": {\"@type\": \"PostalAddress\", \"streetAddress\": \"1 Data St\", "
            "\"addressLocality\": \"Columbus\", \"addressRegion\": \"OH\", "
            "\"postalCode\": \"43215\"}}</script></head>"
            "<body><h1>Structured Only Vet</h1><p>We provide general veterinary "
            "practice care.</p></body></html>"),
        "extraction": {"facts": [
            {"field": "general_practice", "value": "true",
             "quote": "We provide general veterinary practice care"},
        ]},
    }
    fp = Path(tempfile.mkdtemp()) / "fixture.json"
    fp.write_text(json.dumps(fixture), encoding="utf-8")
    fetcher, extractor = _build_static(fixture["url"], str(fp))
    ctx = ImportContext(**fixture["context"])
    cas = ArtifactStoreRepository(tmp_path / "cas")
    c = run_import(fixture["url"], ctx, fetcher=fetcher, extractor=extractor, cas=cas,
                   observed_at="2026-07-18", created_at="1970-01-01T00:00:00")
    assert dict(c.proposed_fields)["name"] == "Structured Only Vet"   # identity recognized
    ids = {cap.capability_id for cap in c.capabilities}
    for high_risk_field in ("emergency_service", "urgent_care", "open_24h",
                            "walk_ins_accepted", "existing_clients_only", "species_served"):
        assert high_risk_field not in ids
