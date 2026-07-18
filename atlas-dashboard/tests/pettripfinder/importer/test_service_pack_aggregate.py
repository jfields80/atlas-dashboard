"""AES-DATA-003C -- multi-source aggregation (Task 12), fingerprint
provenance (Task 17), review-report rendering (Task 14), no-production-
mutation, and legacy/veterinary regression re-proof for boarding/grooming/
pet_store. Static fixtures only -- no network, no live provider calls."""

from __future__ import annotations

import dataclasses
import json
from pathlib import Path

from repositories.artifact_store_repository import ArtifactStoreRepository
from scripts.import_official_url import _build_static
from scripts.import_official_urls import _build_static_multi
from scripts.pettripfinder.importer import constants as C
from scripts.pettripfinder.importer.aggregate import run_multi_import
from scripts.pettripfinder.importer.batch import (
    BatchJob,
    BatchManifest,
    compute_job_fingerprint,
    compute_manifest_hash,
    get_batch_id,
)
from scripts.pettripfinder.importer.candidate import run_import
from scripts.pettripfinder.importer.domain_packs.registry import default_registry
from scripts.pettripfinder.importer.models import ImportContext
from scripts.pettripfinder.importer.review_report import render_report_html

_REPO_ROOT = Path(__file__).resolve().parents[3]
_FIXTURES = Path(__file__).resolve().parent / "fixtures"
_SEED_CSV = _REPO_ROOT / "launch_packages" / "pettripfinder" / "seed_businesses.csv"
_GOLDEN_DIR = Path(__file__).resolve().parent / "fixtures" / "golden"


def _run_multi(names, ctx_overrides, tmp_path, created_at="1970-01-01T00:00:00"):
    paths = [_FIXTURES / (n + ".json") for n in names]
    objs = [json.loads(p.read_text(encoding="utf-8")) for p in paths]
    urls = [o["url"] for o in objs]
    fetcher, extractor = _build_static_multi(urls, [str(p) for p in paths])
    ctx = ImportContext(**ctx_overrides)
    cas = ArtifactStoreRepository(tmp_path / "cas")
    return run_multi_import(urls, ctx, fetcher=fetcher, extractor=extractor, cas=cas,
                            observed_at="2026-07-18", created_at=created_at)


def _run_single(fixture_rel_path, tmp_path, created_at="1970-01-01T00:00:00"):
    obj = json.loads((_FIXTURES / (fixture_rel_path + ".json")).read_text(encoding="utf-8"))
    url = obj["url"]
    fetcher, extractor = _build_static(url, str(_FIXTURES / (fixture_rel_path + ".json")))
    ctx = ImportContext(**obj.get("context", {}))
    cas = ArtifactStoreRepository(tmp_path / "cas")
    return run_import(url, ctx, fetcher=fetcher, extractor=extractor, cas=cas,
                      observed_at="2026-07-18", created_at=created_at)


_BOARD_CTX = {"category": "boarding", "expected_city": "Columbus", "expected_state": "OH"}
_GROOM_CTX = {"category": "grooming", "expected_city": "Columbus", "expected_state": "OH"}
_STORE_CTX = {"category": "pet_store", "expected_city": "Columbus", "expected_state": "OH"}


# --------------------------------------------------------------------------- #
# 23-25/39/54-55. Multi-source scenarios F, M, V, W.
# --------------------------------------------------------------------------- #

def test_23_boarding_multi_source_merge(tmp_path):
    c = _run_multi(
        ["boarding/board_a_dog_boarding_daycare", "boarding/board_a_dog_boarding_daycare"],
        _BOARD_CTX, tmp_path)
    assert len(c.sources) == 1   # exact duplicate URL dedupes before fetch
    assert c.recommendation == C.RECOMMEND_READY


def test_24_25_scenario_f_requirements_conflict_review(tmp_path):
    c = _run_multi(
        ["boarding/board_f_vaccination_conflict_s1", "boarding/board_f_vaccination_conflict_s2"],
        _BOARD_CTX, tmp_path)
    assert c.recommendation == C.RECOMMEND_REVIEW
    assert C.REASON_POLICY_CONFLICT in c.recommendation_reasons
    by_id = {cap.capability_id: cap for cap in c.capabilities}
    assert by_id["dog_boarding"].state == "CONFLICTED"
    # cat_boarding was only claimed by S2, uncontested -- still SUPPORTED,
    # proving one source's exclusion-relevant fact never poisons another's.
    assert by_id["cat_boarding"].state == "SUPPORTED"
    assert len(c.sources) == 2


def test_39_scenario_m_service_area_conflict_review(tmp_path):
    c = _run_multi(
        ["grooming/groom_m_service_area_conflict_s1", "grooming/groom_m_service_area_conflict_s2"],
        _GROOM_CTX, tmp_path)
    assert c.recommendation == C.RECOMMEND_REVIEW
    assert C.REASON_GROOMING_CAPABILITY_CONFLICT in c.recommendation_reasons
    assert C.REASON_POLICY_CONFLICT in c.recommendation_reasons
    by_id = {cap.capability_id: cap for cap in c.capabilities}
    assert by_id["mobile_service"].state == "CONFLICTED"
    assert by_id["mobile_service"].high_risk is True


def test_54_pet_store_multi_source_merge_with_attribution(tmp_path):
    c = _run_multi(
        ["pet_store/store_v_multi_source_s1_location", "pet_store/store_v_multi_source_s2_services"],
        _STORE_CTX, tmp_path)
    assert c.recommendation == C.RECOMMEND_READY
    assert c.recommendation_reasons == ()
    by_id = {cap.capability_id: cap for cap in c.capabilities}
    assert by_id["retail_products"].source_url == "https://www.twopagepets.test/"
    assert by_id["delivery"].source_url == "https://www.twopagepets.test/services"
    assert by_id["online_ordering"].source_url == "https://www.twopagepets.test/services"
    assert len(c.sources) == 2


def test_55_scenario_w_conflicting_service_claim_review(tmp_path):
    c = _run_multi(
        ["pet_store/store_w_multi_source_conflict_s1", "pet_store/store_w_multi_source_conflict_s2"],
        _STORE_CTX, tmp_path)
    assert c.recommendation == C.RECOMMEND_REVIEW
    assert C.REASON_PET_STORE_CAPABILITY_CONFLICT in c.recommendation_reasons
    by_id = {cap.capability_id: cap for cap in c.capabilities}
    assert by_id["vaccination_clinic"].state == "CONFLICTED"
    assert by_id["vaccination_clinic"].high_risk is True
    assert by_id["retail_products"].state == "SUPPORTED"


def test_excluded_source_contributes_no_capability(tmp_path):
    import tempfile
    primary = json.loads((_FIXTURES / "pet_store" / "store_v_multi_source_s1_location.json")
                         .read_text(encoding="utf-8"))
    foreign = {
        "url": "https://www.totallydifferentstore.test/",
        "html": ("<!doctype html><html><body><h1>Totally Different Store</h1>"
                 "<p>Totally Different Store offers a full-service vaccination clinic.</p>"
                 "</body></html>"),
        "extraction": {"facts": [
            {"field": "vaccination_clinic", "value": "true",
             "quote": "Totally Different Store offers a full-service vaccination clinic"},
        ]},
    }
    tmp = Path(tempfile.mkdtemp())
    primary_fp = tmp / "primary.json"
    foreign_fp = tmp / "foreign.json"
    primary_fp.write_text(json.dumps(primary), encoding="utf-8")
    foreign_fp.write_text(json.dumps(foreign), encoding="utf-8")
    urls = [primary["url"], foreign["url"]]
    fetcher, extractor = _build_static_multi(urls, [str(primary_fp), str(foreign_fp)])
    ctx = ImportContext(**_STORE_CTX)
    cas = ArtifactStoreRepository(tmp_path / "cas")
    c = run_multi_import(urls, ctx, fetcher=fetcher, extractor=extractor, cas=cas,
                         observed_at="2026-07-18", created_at="1970-01-01T00:00:00")
    ids = {cap.capability_id for cap in c.capabilities}
    assert "vaccination_clinic" not in ids
    assert any(s.excluded_reason == C.REASON_DIFFERENT_REGISTRABLE_DOMAIN for s in c.sources)


def test_no_cross_business_merge_and_deterministic_source_order(tmp_path):
    c = _run_multi(
        ["pet_store/store_v_multi_source_s1_location", "pet_store/store_v_multi_source_s2_services"],
        _STORE_CTX, tmp_path)
    assert [s.source_id for s in c.sources] == ["S1", "S2"]
    assert c.sources[0].role == C.SOURCE_ROLE_PRIMARY
    assert c.sources[1].role == C.SOURCE_ROLE_SUPPLEMENTAL


# --------------------------------------------------------------------------- #
# 69. Category-scoped fingerprint invalidation (Task 17) -- boarding,
# grooming, pet_store each verified independently.
# --------------------------------------------------------------------------- #

def _job(category, job_id="j1"):
    return BatchJob(job_id=job_id, candidate_name="X", category=category,
                    expected_city="c", expected_state="OH", urls=("https://a.test",))


def _kwargs():
    return dict(extractor="static", model="m", observed_at="2026-01-01", repo_root=_REPO_ROOT)


def test_boarding_fingerprint_deterministic_and_scoped(monkeypatch):
    boarding_job = _job(C.CATEGORY_BOARDING)
    hotel_job = _job(C.CATEGORY_HOTELS, "h1")
    fp1 = compute_job_fingerprint(boarding_job, **_kwargs())
    fp2 = compute_job_fingerprint(boarding_job, **_kwargs())
    assert fp1 == fp2
    fp_hotel_before = compute_job_fingerprint(hotel_job, **_kwargs())

    original = default_registry.for_category(C.CATEGORY_BOARDING)
    bumped = dataclasses.replace(original, pack_version="9.9.9")
    monkeypatch.setitem(default_registry._by_category, C.CATEGORY_BOARDING, bumped)

    fp_boarding_after = compute_job_fingerprint(boarding_job, **_kwargs())
    fp_hotel_after = compute_job_fingerprint(hotel_job, **_kwargs())
    assert fp_boarding_after != fp1
    assert fp_hotel_after == fp_hotel_before


def test_grooming_fingerprint_deterministic_and_scoped(monkeypatch):
    grooming_job = _job(C.CATEGORY_GROOMING)
    boarding_job = _job(C.CATEGORY_BOARDING, "b1")
    fp1 = compute_job_fingerprint(grooming_job, **_kwargs())
    fp_boarding_before = compute_job_fingerprint(boarding_job, **_kwargs())

    original = default_registry.for_category(C.CATEGORY_GROOMING)
    bumped = dataclasses.replace(original, pack_version="9.9.9")
    monkeypatch.setitem(default_registry._by_category, C.CATEGORY_GROOMING, bumped)

    fp_grooming_after = compute_job_fingerprint(grooming_job, **_kwargs())
    fp_boarding_after = compute_job_fingerprint(boarding_job, **_kwargs())
    assert fp_grooming_after != fp1
    assert fp_boarding_after == fp_boarding_before


def test_pet_store_fingerprint_deterministic_and_scoped(monkeypatch):
    store_job = _job(C.CATEGORY_PET_STORE)
    vet_job = _job(C.CATEGORY_VETERINARY, "v1")
    fp1 = compute_job_fingerprint(store_job, **_kwargs())
    fp_vet_before = compute_job_fingerprint(vet_job, **_kwargs())

    original = default_registry.for_category(C.CATEGORY_PET_STORE)
    bumped = dataclasses.replace(original, pack_version="9.9.9")
    monkeypatch.setitem(default_registry._by_category, C.CATEGORY_PET_STORE, bumped)

    fp_store_after = compute_job_fingerprint(store_job, **_kwargs())
    fp_vet_after = compute_job_fingerprint(vet_job, **_kwargs())
    assert fp_store_after != fp1
    assert fp_vet_after == fp_vet_before


def test_batch_id_and_manifest_hash_unaffected_by_service_pack_versions(monkeypatch):
    manifest = BatchManifest(
        manifest_schema_version=C.BATCH_MANIFEST_SCHEMA_VERSION, batch_id="stable-service-batch",
        batch_name="t", defaults={}, jobs=(_job(C.CATEGORY_PET_STORE),))
    assert get_batch_id(manifest) == "stable-service-batch"
    hash_before = compute_manifest_hash(manifest)

    original = default_registry.for_category(C.CATEGORY_PET_STORE)
    bumped = dataclasses.replace(original, pack_version="9.9.9")
    monkeypatch.setitem(default_registry._by_category, C.CATEGORY_PET_STORE, bumped)

    hash_after = compute_manifest_hash(manifest)
    assert hash_after == hash_before


def test_no_time_randomness_or_output_root_dependency():
    job = _job(C.CATEGORY_BOARDING)
    fp_a = compute_job_fingerprint(job, **_kwargs())
    fp_b = compute_job_fingerprint(job, extractor="static", model="m",
                                   observed_at="2026-01-01", repo_root=_REPO_ROOT)
    assert fp_a == fp_b


# --------------------------------------------------------------------------- #
# 66. Review report rendering + HTML escaping.
# --------------------------------------------------------------------------- #

def test_66_review_report_shows_capabilities_and_escapes_html(tmp_path):
    c = _run_single("boarding/board_b_cat_and_dog_boarding", tmp_path)
    html = render_report_html(c, "candidate.json")
    assert "cat_boarding" in html
    assert "HIGH-RISK" in html
    assert "pettripfinder-boarding" in html
    assert "<script" not in html
    assert "we board both dogs and cats overnight" in html.lower()


def test_review_report_grooming_conflict_shows_conflicted_state(tmp_path):
    c = _run_multi(
        ["grooming/groom_m_service_area_conflict_s1", "grooming/groom_m_service_area_conflict_s2"],
        _GROOM_CTX, tmp_path)
    html = render_report_html(c, "candidate.json")
    assert "CONFLICTED" in html
    assert "mobile_service" in html


# --------------------------------------------------------------------------- #
# 67. Compatibility summary contains only validated facts.
# --------------------------------------------------------------------------- #

def test_67_compatibility_summary_never_invents_facts(tmp_path):
    c = _run_single("pet_store/store_n_food_and_supplies", tmp_path)
    policy = dict(c.proposed_fields)["pet_policy"]
    # Only facts actually evidenced on the page appear; pharmacy/delivery/
    # vaccination_clinic were never stated and must never leak into the text.
    assert "pharmacy" not in policy.lower()
    assert "delivery" not in policy.lower()
    assert "vaccination" not in policy.lower()


# --------------------------------------------------------------------------- #
# 68. No production CSV mutation.
# --------------------------------------------------------------------------- #

def test_68_no_production_csv_mutation(tmp_path):
    before = _SEED_CSV.read_bytes() if _SEED_CSV.exists() else None
    _run_single("boarding/board_a_dog_boarding_daycare", tmp_path)
    _run_single("grooming/groom_h_dog_grooming_appointment", tmp_path)
    _run_single("pet_store/store_n_food_and_supplies", tmp_path)
    _run_multi(
        ["pet_store/store_v_multi_source_s1_location", "pet_store/store_v_multi_source_s2_services"],
        _STORE_CTX, tmp_path)
    after = _SEED_CSV.read_bytes() if _SEED_CSV.exists() else None
    assert before == after


# --------------------------------------------------------------------------- #
# 70-73. Legacy and veterinary regression re-proof (this phase touched
# candidate.py/aggregate.py/recommend.py/policy_compose.py again).
# --------------------------------------------------------------------------- #

def test_70_71_72_legacy_golden_bytes_unchanged():
    from scripts.pettripfinder.importer.candidate import candidate_from_dict, dumps_candidate
    for name in ("golden_drury", "golden_scioto", "golden_landgrant"):
        text = (_GOLDEN_DIR / (name + ".json")).read_text(encoding="utf-8")
        candidate = candidate_from_dict(json.loads(text))
        assert dumps_candidate(candidate) + "\n" == text


def test_73_veterinary_scenario_a_and_b_unchanged(tmp_path):
    c_a = _run_single("veterinary/vet_a_general_practice", tmp_path)
    assert c_a.recommendation == C.RECOMMEND_READY
    assert {cap.capability_id for cap in c_a.capabilities} == {
        "general_practice", "species_served", "wellness_exams", "vaccinations"}

    c_b = _run_single("veterinary/vet_b_emergency_hospital_24_7", tmp_path)
    assert c_b.recommendation == C.RECOMMEND_READY
    by_id = {cap.capability_id: cap for cap in c_b.capabilities}
    assert by_id["emergency_service"].high_risk is True
    assert by_id["open_24h"].high_risk is True


def test_73b_veterinary_multi_source_contradiction_unchanged(tmp_path):
    vet_ctx = {"category": "veterinary", "expected_city": "Columbus", "expected_state": "OH"}
    c = _run_multi(
        ["veterinary/vet_j_multi_source_contradiction_s1",
         "veterinary/vet_j_multi_source_contradiction_s2"],
        vet_ctx, tmp_path)
    assert c.recommendation == C.RECOMMEND_REVIEW
    assert C.REASON_VETERINARY_CAPABILITY_CONFLICT in c.recommendation_reasons
