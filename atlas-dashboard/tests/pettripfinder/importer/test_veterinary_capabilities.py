"""AES-DATA-003B -- veterinary capability projection (Task 7), CategoryDetail
(Task 8), provenance/serialization (Task 9), and end-to-end READY scenarios
(A/B/C from the static fixture set). Static fixtures only -- no network, no
live provider calls."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from repositories.artifact_store_repository import ArtifactStoreRepository
from scripts.import_official_url import _build_static
from scripts.pettripfinder.importer import constants as C
from scripts.pettripfinder.importer.candidate import (
    candidate_from_dict,
    dumps_candidate,
    run_import,
)
from scripts.pettripfinder.importer.domain_packs.base import CapabilityState
from scripts.pettripfinder.importer.domain_packs.capabilities import (
    CAPABILITY_SCHEMA_VERSION,
)
from scripts.pettripfinder.importer.domain_packs.veterinary import (
    VETERINARY_PACK,
    high_risk_capability_conflict,
    project_capabilities,
    service_evidence_present,
)
from scripts.pettripfinder.importer.models import Conflict, ExtractedEvidence, ImportContext

_FIXTURES = Path(__file__).resolve().parent / "fixtures" / "veterinary"


def _run(name, tmp_path, created_at="1970-01-01T00:00:00"):
    obj = json.loads((_FIXTURES / (name + ".json")).read_text(encoding="utf-8"))
    url = obj["url"]
    fetcher, extractor = _build_static(url, str(_FIXTURES / (name + ".json")))
    ctx = ImportContext(**obj.get("context", {}))
    cas = ArtifactStoreRepository(tmp_path / "cas")
    return run_import(url, ctx, fetcher=fetcher, extractor=extractor, cas=cas,
                      observed_at="2026-07-18", created_at=created_at)


def _ev(field, value, url="https://x.test", state=C.SUPPORT_SUPPORTED, idx_hint=0):
    return ExtractedEvidence(
        field_name=field, proposed_value=value, source_wording=value, source_url=url,
        snapshot_quote=value, char_start=idx_hint, char_end=idx_hint + len(value),
        extraction_method=C.METHOD_LLM_TEXT, support_state=state, warnings=())


# --------------------------------------------------------------------------- #
# 1-10. Pure ``project_capabilities`` unit tests (Task 7).
# --------------------------------------------------------------------------- #

def test_1_missing_fact_is_omitted_not_unknown():
    caps = project_capabilities({}, ())
    assert caps == ()


def test_2_boolean_true_is_supported():
    facts = {"general_practice": "true"}
    ev = (_ev("general_practice", "true"),)
    caps = project_capabilities(facts, ev)
    assert len(caps) == 1
    assert caps[0].capability_id == "general_practice"
    assert caps[0].state == CapabilityState.SUPPORTED.value


def test_3_boolean_false_is_explicitly_absent():
    facts = {"walk_ins_accepted": "false"}
    ev = (_ev("walk_ins_accepted", "false"),)
    caps = project_capabilities(facts, ev)
    assert caps[0].state == CapabilityState.EXPLICITLY_ABSENT.value


def test_4_text_field_with_value_is_supported_with_value():
    facts = {"species_served": "dogs and cats"}
    ev = (_ev("species_served", "dogs and cats"),)
    caps = project_capabilities(facts, ev)
    assert caps[0].state == CapabilityState.SUPPORTED.value
    assert caps[0].value == "dogs and cats"


def test_5_empty_text_value_is_omitted():
    facts = {"species_served": ""}
    caps = project_capabilities(facts, ())
    assert caps == ()


def test_6_boolean_field_with_non_bool_string_is_omitted():
    facts = {"general_practice": "maybe"}
    caps = project_capabilities(facts, (_ev("general_practice", "maybe"),))
    assert caps == ()


def test_7_evidence_index_points_at_final_evidence_tuple_position():
    ev = (
        _ev("name", "Clinic"),                    # index 0 -- not a capability field
        _ev("general_practice", "true"),          # index 1
    )
    caps = project_capabilities({"general_practice": "true"}, ev)
    assert caps[0].evidence_index == 1


def test_8_deterministic_ordering_matches_pack_field_order():
    facts = {"urgent_care": "true", "general_practice": "true", "surgery": "true"}
    ev = tuple(_ev(f, "true") for f in facts)
    caps = project_capabilities(facts, ev)
    ids = [c.capability_id for c in caps]
    pack_order = [f for f in VETERINARY_PACK.field_order if f in facts]
    assert ids == pack_order


def test_9_no_duplicate_capability_ids():
    facts = {f: "true" for f in ("general_practice", "surgery", "dentistry")}
    ev = tuple(_ev(f, "true") for f in facts)
    caps = project_capabilities(facts, ev)
    ids = [c.capability_id for c in caps]
    assert len(ids) == len(set(ids))


def test_10_conflicted_field_emits_conflicted_state():
    ev = (
        _ev("emergency_service", "true", url="https://a.test"),
        _ev("emergency_service", "false", url="https://b.test"),
    )
    conflicts = (Conflict(
        field_name="emergency_service", competing_values=("true", "false"),
        evidence=ev, precedence_note="aggregate_policy_conflict",
        resolution_status="UNRESOLVED"),)
    caps = project_capabilities({}, ev, conflicts)
    assert len(caps) == 1
    assert caps[0].capability_id == "emergency_service"
    assert caps[0].state == CapabilityState.CONFLICTED.value
    assert caps[0].high_risk is True


# --------------------------------------------------------------------------- #
# 11-14. Exotic-species high-risk detection.
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("value", [
    "reptiles", "birds and exotics", "rabbits and ferrets", "snakes",
])
def test_11_exotic_species_marked_high_risk(value):
    facts = {"species_served": value}
    caps = project_capabilities(facts, (_ev("species_served", value),))
    assert caps[0].high_risk is True


@pytest.mark.parametrize("value", ["dogs and cats", "dogs", "cats"])
def test_12_common_species_not_high_risk(value):
    facts = {"species_served": value}
    caps = project_capabilities(facts, (_ev("species_served", value),))
    assert caps[0].high_risk is False


def test_13_declared_high_risk_fields_flagged_regardless_of_state():
    for field, val in (("emergency_service", "true"), ("walk_ins_accepted", "false"),
                      ("existing_clients_only", "true"), ("open_24h", "true"),
                      ("urgent_care", "true")):
        caps = project_capabilities({field: val}, (_ev(field, val),))
        assert caps[0].high_risk is True, field


def test_14_non_high_risk_fields_never_flagged():
    for field in ("general_practice", "preventive_care", "vaccinations", "surgery",
                 "dentistry", "pharmacy", "diagnostics", "critical_care"):
        caps = project_capabilities({field: "true"}, (_ev(field, "true"),))
        assert caps[0].high_risk is False, field


# --------------------------------------------------------------------------- #
# 15-18. service_evidence_present / high_risk_capability_conflict helpers.
# --------------------------------------------------------------------------- #

def test_15_service_evidence_present_true_when_supported_capability_exists():
    caps = project_capabilities({"general_practice": "true"}, (_ev("general_practice", "true"),))
    assert service_evidence_present(caps) is True


def test_16_service_evidence_present_false_when_no_capabilities():
    assert service_evidence_present(()) is False


def test_17_high_risk_conflict_true_only_for_high_risk_conflicted():
    ev = (_ev("emergency_service", "true"), _ev("emergency_service", "false"))
    conflicts = (Conflict(
        field_name="emergency_service", competing_values=("true", "false"), evidence=ev,
        precedence_note="aggregate_policy_conflict", resolution_status="UNRESOLVED"),)
    caps = project_capabilities({}, ev, conflicts)
    assert high_risk_capability_conflict(caps) is True


def test_18_high_risk_conflict_false_for_non_high_risk_conflict():
    ev = (_ev("general_practice", "true"), _ev("general_practice", "false"))
    conflicts = (Conflict(
        field_name="general_practice", competing_values=("true", "false"), evidence=ev,
        precedence_note="aggregate_policy_conflict", resolution_status="UNRESOLVED"),)
    caps = project_capabilities({}, ev, conflicts)
    assert high_risk_capability_conflict(caps) is False


# --------------------------------------------------------------------------- #
# 19-24. End-to-end scenarios A/B/C via the real pipeline (Tasks 6/10).
# --------------------------------------------------------------------------- #

def test_19_scenario_a_general_practice_ready(tmp_path):
    c = _run("vet_a_general_practice", tmp_path)
    assert c.recommendation == C.RECOMMEND_READY
    assert c.recommendation_reasons == ()
    ids = {cap.capability_id for cap in c.capabilities}
    assert ids == {"general_practice", "species_served", "wellness_exams", "vaccinations"}
    assert all(not cap.high_risk for cap in c.capabilities if cap.capability_id != "species_served")
    assert c.pack_id == "pettripfinder-veterinary"
    assert c.pack_version == "1.0.0"
    assert c.capability_schema_version == CAPABILITY_SCHEMA_VERSION


def test_20_scenario_b_emergency_hospital_24h_ready(tmp_path):
    c = _run("vet_b_emergency_hospital_24_7", tmp_path)
    assert c.recommendation == C.RECOMMEND_READY
    by_id = {cap.capability_id: cap for cap in c.capabilities}
    assert by_id["emergency_service"].state == CapabilityState.SUPPORTED.value
    assert by_id["emergency_service"].high_risk is True
    assert by_id["open_24h"].state == CapabilityState.SUPPORTED.value
    assert by_id["open_24h"].high_risk is True
    assert by_id["general_practice"].high_risk is False


def test_21_scenario_c_urgent_care_not_24h_ready(tmp_path):
    c = _run("vet_c_urgent_care_not_24h", tmp_path)
    assert c.recommendation == C.RECOMMEND_READY
    ids = {cap.capability_id for cap in c.capabilities}
    assert "urgent_care" in ids
    assert "walk_ins_accepted" in ids
    # Non-inference: urgent_care never implies emergency_service or open_24h.
    assert "emergency_service" not in ids
    assert "open_24h" not in ids


def test_22_category_detail_built_from_hours_fact(tmp_path):
    # Build a minimal fixture-equivalent inline: reuse scenario A's fetcher
    # but with an added "hours" fact via a fresh fixture file is unnecessary
    # -- exercise the projection contract directly through run_import using
    # the existing static-fixture seam with an extra fact.
    import tempfile
    from scripts.pettripfinder.importer.models import ImportContext as _Ctx

    fixture = {
        "url": "https://www.hoursvet.test/",
        "context": {"category": "veterinary", "expected_city": "Columbus", "expected_state": "OH"},
        "html": ("<!doctype html><html><body><h1>Hours Vet</h1><p>We provide general "
                 "veterinary practice care. Open Monday-Friday 8am-6pm.</p></body></html>"),
        "extraction": {"facts": [
            {"field": "general_practice", "value": "true",
             "quote": "We provide general veterinary practice care"},
            {"field": "hours", "value": "Monday-Friday 8am-6pm",
             "quote": "Open Monday-Friday 8am-6pm"},
        ]},
    }
    fp = Path(tempfile.mkdtemp()) / "fixture.json"
    fp.write_text(json.dumps(fixture), encoding="utf-8")
    fetcher, extractor = _build_static(fixture["url"], str(fp))
    ctx = _Ctx(**fixture["context"])
    cas = ArtifactStoreRepository(tmp_path / "cas")
    c = run_import(fixture["url"], ctx, fetcher=fetcher, extractor=extractor, cas=cas,
                   observed_at="2026-07-18", created_at="1970-01-01T00:00:00")
    assert c.category_detail is not None
    assert c.category_detail.detail_type == "veterinary"
    assert c.category_detail.detail_schema_version == "1.0.0"
    assert dict(c.category_detail.fields)["hours"] == "Monday-Friday 8am-6pm"
    # "hours" itself is never duplicated as a capability.
    assert "hours" not in {cap.capability_id for cap in c.capabilities}


def test_23_serialization_round_trip_preserves_veterinary_fields(tmp_path):
    c = _run("vet_b_emergency_hospital_24_7", tmp_path)
    blob = dumps_candidate(c)
    restored = candidate_from_dict(json.loads(blob))
    assert restored.pack_id == c.pack_id
    assert restored.pack_version == c.pack_version
    assert restored.capability_schema_version == c.capability_schema_version
    assert len(restored.capabilities) == len(c.capabilities)
    for a, b in zip(sorted(restored.capabilities, key=lambda x: x.capability_id),
                    sorted(c.capabilities, key=lambda x: x.capability_id)):
        assert a.capability_id == b.capability_id
        assert a.state == b.state
        assert a.high_risk == b.high_risk
        assert a.evidence_index == b.evidence_index
    assert dumps_candidate(restored) == blob


def test_24_legacy_hotel_candidate_still_omits_pack_keys(tmp_path):
    fixture_path = Path(__file__).resolve().parent / "fixtures" / "hotel_01_strong.json"
    obj = json.loads(fixture_path.read_text(encoding="utf-8"))
    fetcher, extractor = _build_static(obj["url"], str(fixture_path))
    ctx = ImportContext(**obj["context"])
    cas = ArtifactStoreRepository(tmp_path / "cas")
    c = run_import(obj["url"], ctx, fetcher=fetcher, extractor=extractor, cas=cas,
                   observed_at="2026-07-16", created_at="1970-01-01T00:00:00")
    assert c.capabilities == ()
    assert c.category_detail is None
    assert c.pack_id == "" and c.pack_version == "" and c.capability_schema_version == ""
    d = json.loads(dumps_candidate(c))
    for key in ("capabilities", "category_detail", "pack_id", "pack_version",
               "capability_schema_version"):
        assert key not in d
