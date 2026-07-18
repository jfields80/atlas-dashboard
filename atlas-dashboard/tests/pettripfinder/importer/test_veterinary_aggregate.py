"""AES-DATA-003B -- veterinary multi-source aggregation (Task 12), fingerprint
provenance (Task 17), review-report rendering (Task 14), and the remaining
single-source doctrine scenarios E/F/K from the static fixture set. Static
fixtures only -- no network, no live provider calls."""

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

_FIXTURES = Path(__file__).resolve().parent / "fixtures" / "veterinary"
_REPO_ROOT = Path(__file__).resolve().parents[3]
_SEED_CSV = _REPO_ROOT / "launch_packages" / "pettripfinder" / "seed_businesses.csv"


def _run_single(name, tmp_path, created_at="1970-01-01T00:00:00"):
    obj = json.loads((_FIXTURES / (name + ".json")).read_text(encoding="utf-8"))
    url = obj["url"]
    fetcher, extractor = _build_static(url, str(_FIXTURES / (name + ".json")))
    ctx = ImportContext(**obj.get("context", {}))
    cas = ArtifactStoreRepository(tmp_path / "cas")
    return run_import(url, ctx, fetcher=fetcher, extractor=extractor, cas=cas,
                      observed_at="2026-07-18", created_at=created_at)


def _run_multi(names, ctx_overrides, tmp_path, created_at="1970-01-01T00:00:00"):
    paths = [_FIXTURES / (n + ".json") for n in names]
    objs = [json.loads(p.read_text(encoding="utf-8")) for p in paths]
    urls = [o["url"] for o in objs]
    fetcher, extractor = _build_static_multi(urls, [str(p) for p in paths])
    ctx = ImportContext(**ctx_overrides)
    cas = ArtifactStoreRepository(tmp_path / "cas")
    return run_multi_import(urls, ctx, fetcher=fetcher, extractor=extractor, cas=cas,
                            observed_at="2026-07-18", created_at=created_at)


_VET_CTX = {"category": "veterinary", "expected_city": "Columbus", "expected_state": "OH"}


# --------------------------------------------------------------------------- #
# 1-2. Remaining single-source doctrine scenarios E/F.
# --------------------------------------------------------------------------- #

def test_1_scenario_e_after_hours_phone_only_ready(tmp_path):
    c = _run_single("vet_e_after_hours_phone_only", tmp_path)
    assert c.recommendation == C.RECOMMEND_READY
    by_id = {cap.capability_id: cap for cap in c.capabilities}
    assert by_id["after_hours_instructions"].state == "SUPPORTED"
    assert by_id["after_hours_instructions"].high_risk is False
    assert "open_24h" not in by_id
    assert "emergency_service" not in by_id


def test_2_scenario_f_existing_clients_only_ready(tmp_path):
    c = _run_single("vet_f_existing_clients_only", tmp_path)
    assert c.recommendation == C.RECOMMEND_READY
    by_id = {cap.capability_id: cap for cap in c.capabilities}
    assert by_id["existing_clients_only"].state == "SUPPORTED"
    assert by_id["existing_clients_only"].high_risk is True


# --------------------------------------------------------------------------- #
# 3. Scenario K: a third-party discovery host is rejected even for
#    veterinary -- universal gates apply unchanged to the new category.
# --------------------------------------------------------------------------- #

def test_3_scenario_k_third_party_source_rejected(tmp_path):
    c = _run_single("vet_k_third_party_source", tmp_path)
    assert c.recommendation == C.RECOMMEND_REJECT
    assert c.recommendation_reasons == (C.REASON_UNCERTAIN_SOURCE_RELATIONSHIP,)
    # A REJECTed candidate is never promoted regardless of what evidence it
    # carries -- capabilities/pet_facts/evidence stay populated for audit
    # visibility (the exact existing precedent: hotel_08_hostile keeps its
    # fabricated-fee evidence entry visible too), but review_status stays
    # PENDING and the recommendation itself is the actual publish gate.
    assert c.review_status == C.REVIEW_PENDING


# --------------------------------------------------------------------------- #
# 4. Scenario I: multi-source hospital -- location facts and emergency facts
#    from two different pages merge into one candidate, each capability
#    correctly attributed to its own contributing source.
# --------------------------------------------------------------------------- #

def test_4_scenario_i_multi_source_hospital_ready_with_attribution(tmp_path):
    c = _run_multi(
        ["vet_i_multi_source_hospital_s1_location", "vet_i_multi_source_hospital_s2_emergency"],
        _VET_CTX, tmp_path)
    assert c.recommendation == C.RECOMMEND_READY
    assert c.recommendation_reasons == ()
    by_id = {cap.capability_id: cap for cap in c.capabilities}
    assert set(by_id) == {"general_practice", "species_served", "emergency_service", "open_24h"}
    assert by_id["general_practice"].source_url == "https://www.northsidevethospital.test/"
    assert by_id["emergency_service"].source_url == "https://www.northsidevethospital.test/emergency"
    assert by_id["open_24h"].source_url == "https://www.northsidevethospital.test/emergency"
    assert by_id["emergency_service"].high_risk is True
    assert len(c.sources) == 2


# --------------------------------------------------------------------------- #
# 5. Scenario J: multi-source contradiction -- conflicting emergency_service
#    claims force REVIEW via the dedicated high-risk-conflict reason (never
#    a silent pick-one resolution).
# --------------------------------------------------------------------------- #

def test_5_scenario_j_multi_source_contradiction_review(tmp_path):
    c = _run_multi(
        ["vet_j_multi_source_contradiction_s1", "vet_j_multi_source_contradiction_s2"],
        _VET_CTX, tmp_path)
    assert c.recommendation == C.RECOMMEND_REVIEW
    assert C.REASON_VETERINARY_CAPABILITY_CONFLICT in c.recommendation_reasons
    assert C.REASON_POLICY_CONFLICT in c.recommendation_reasons
    by_id = {cap.capability_id: cap for cap in c.capabilities}
    assert by_id["emergency_service"].state == "CONFLICTED"
    assert by_id["emergency_service"].high_risk is True
    # general_practice is uncontested on both sources -- still SUPPORTED.
    assert by_id["general_practice"].state == "SUPPORTED"


# --------------------------------------------------------------------------- #
# 6. An excluded source (different registrable domain) contributes no
#    capability at all -- no cross-business merge.
# --------------------------------------------------------------------------- #

def test_6_excluded_source_contributes_no_capability(tmp_path):
    import tempfile
    primary = json.loads(
        (_FIXTURES / "vet_i_multi_source_hospital_s1_location.json").read_text(encoding="utf-8"))
    foreign = {
        "url": "https://www.totallydifferentclinic.test/",
        "html": ("<!doctype html><html><body><h1>Totally Different Clinic</h1>"
                 "<p>Totally Different Clinic provides emergency veterinary care "
                 "24 hours a day.</p></body></html>"),
        "extraction": {"facts": [
            {"field": "emergency_service", "value": "true",
             "quote": "Totally Different Clinic provides emergency veterinary care"},
            {"field": "open_24h", "value": "true", "quote": "24 hours a day"},
        ]},
    }
    tmp = Path(tempfile.mkdtemp())
    primary_fp = tmp / "primary.json"
    foreign_fp = tmp / "foreign.json"
    primary_fp.write_text(json.dumps(primary), encoding="utf-8")
    foreign_fp.write_text(json.dumps(foreign), encoding="utf-8")

    urls = [primary["url"], foreign["url"]]
    fetcher, extractor = _build_static_multi(urls, [str(primary_fp), str(foreign_fp)])
    ctx = ImportContext(**_VET_CTX)
    cas = ArtifactStoreRepository(tmp_path / "cas")
    c = run_multi_import(urls, ctx, fetcher=fetcher, extractor=extractor, cas=cas,
                         observed_at="2026-07-18", created_at="1970-01-01T00:00:00")

    ids = {cap.capability_id for cap in c.capabilities}
    assert "emergency_service" not in ids
    assert "open_24h" not in ids
    assert any(s.excluded_reason == C.REASON_DIFFERENT_REGISTRABLE_DOMAIN for s in c.sources)


# --------------------------------------------------------------------------- #
# 7-9. Pack-aware job fingerprinting extends correctly to veterinary
#    (Task 17), reusing the exact AES-DATA-003A mechanism unmodified.
# --------------------------------------------------------------------------- #

def _vet_job(job_id: str = "v1") -> BatchJob:
    return BatchJob(
        job_id=job_id, candidate_name="X", category=C.CATEGORY_VETERINARY,
        expected_city="c", expected_state="OH", urls=("https://a.test",))


def _kwargs():
    return dict(extractor="static", model="m", observed_at="2026-01-01", repo_root=_REPO_ROOT)


def test_7_veterinary_fingerprint_deterministic():
    job = _vet_job()
    fp1 = compute_job_fingerprint(job, **_kwargs())
    fp2 = compute_job_fingerprint(job, **_kwargs())
    assert fp1 == fp2


def test_8_veterinary_pack_version_change_scoped_to_veterinary(monkeypatch):
    vet_job = _vet_job()
    hotel_job = BatchJob(
        job_id="h1", candidate_name="X", category=C.CATEGORY_HOTELS,
        expected_city="c", expected_state="OH", urls=("https://a.test",))
    fp_vet_before = compute_job_fingerprint(vet_job, **_kwargs())
    fp_hotel_before = compute_job_fingerprint(hotel_job, **_kwargs())

    original_pack = default_registry.for_category(C.CATEGORY_VETERINARY)
    bumped_pack = dataclasses.replace(original_pack, pack_version="9.9.9")
    monkeypatch.setitem(default_registry._by_category, C.CATEGORY_VETERINARY, bumped_pack)

    fp_vet_after = compute_job_fingerprint(vet_job, **_kwargs())
    fp_hotel_after = compute_job_fingerprint(hotel_job, **_kwargs())

    assert fp_vet_after != fp_vet_before
    assert fp_hotel_after == fp_hotel_before


def test_9_batch_id_and_manifest_hash_unaffected_by_veterinary_pack_version(monkeypatch):
    manifest = BatchManifest(
        manifest_schema_version=C.BATCH_MANIFEST_SCHEMA_VERSION, batch_id="stable-vet-batch",
        batch_name="t", defaults={}, jobs=(_vet_job(),))
    assert get_batch_id(manifest) == "stable-vet-batch"
    hash_before = compute_manifest_hash(manifest)

    original_pack = default_registry.for_category(C.CATEGORY_VETERINARY)
    bumped_pack = dataclasses.replace(original_pack, pack_version="9.9.9")
    monkeypatch.setitem(default_registry._by_category, C.CATEGORY_VETERINARY, bumped_pack)

    hash_after = compute_manifest_hash(manifest)
    assert hash_after == hash_before


# --------------------------------------------------------------------------- #
# 10-11. Review report rendering (Task 14): capabilities, category detail,
# pack provenance, HTML escaping, and legacy byte-identity when there is no
# pack data.
# --------------------------------------------------------------------------- #

def test_10_review_report_shows_high_risk_marker_and_capabilities(tmp_path):
    c = _run_single("vet_b_emergency_hospital_24_7", tmp_path)
    html = render_report_html(c, "candidate.json")
    assert "emergency_service" in html
    assert "HIGH-RISK" in html
    assert "pettripfinder-veterinary" in html
    assert "<script" not in html
    assert "24 hours a day, seven days a week" in html   # evidence quote visible


def test_11_review_report_legacy_candidate_has_no_capability_card(tmp_path):
    fixture_path = Path(__file__).resolve().parent / "fixtures" / "hotel_01_strong.json"
    obj = json.loads(fixture_path.read_text(encoding="utf-8"))
    fetcher, extractor = _build_static(obj["url"], str(fixture_path))
    ctx = ImportContext(**obj["context"])
    cas = ArtifactStoreRepository(tmp_path / "cas")
    c = run_import(obj["url"], ctx, fetcher=fetcher, extractor=extractor, cas=cas,
                   observed_at="2026-07-16", created_at="1970-01-01T00:00:00")
    html = render_report_html(c, "candidate.json")
    assert "Capabilities" not in html
    assert "Category detail" not in html
    assert "domain pack:" not in html


# --------------------------------------------------------------------------- #
# 12. No production inventory mutation: running veterinary imports never
#    touches the real seed CSV.
# --------------------------------------------------------------------------- #

def test_12_no_production_csv_mutation(tmp_path):
    before = _SEED_CSV.read_bytes() if _SEED_CSV.exists() else None
    _run_single("vet_a_general_practice", tmp_path)
    _run_multi(
        ["vet_i_multi_source_hospital_s1_location", "vet_i_multi_source_hospital_s2_emergency"],
        _VET_CTX, tmp_path)
    after = _SEED_CSV.read_bytes() if _SEED_CSV.exists() else None
    assert before == after
