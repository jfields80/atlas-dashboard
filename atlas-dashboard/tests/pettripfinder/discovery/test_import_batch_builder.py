"""AES-DATA-004C Task 11 -- import batch generation tests. Validates
generated manifests against the REAL importer schema validator, not just
this package's own assumptions."""

from __future__ import annotations

import tempfile
from pathlib import Path

from scripts.pettripfinder.discovery import constants as C
from scripts.pettripfinder.discovery.import_batch_builder import (
    build_batch_index,
    build_batches,
    build_import_job,
    dumps_batch_manifest,
)
from scripts.pettripfinder.discovery.models import DiscoveryCandidate
from scripts.pettripfinder.importer.batch import load_manifest, validate_manifest


def _candidate(candidate_id, name, city="Columbus", state="OH", category=C.CATEGORY_HOTEL):
    return DiscoveryCandidate(candidate_id=candidate_id, source_records=(), name=name,
                              city=city, state=state, category_candidates=(category,))


def test_job_maps_motel_category_to_importer_hotels():
    c = _candidate("dc_1", "Test Motel", category=C.CATEGORY_MOTEL)
    job = build_import_job(c, resolved_url="https://example.com/x", is_confirmed=True)
    assert job.category == C.IMPORTER_CATEGORY_HOTELS


def test_job_confirmed_gets_relationship_hint():
    c = _candidate("dc_1", "Test Hotel")
    job = build_import_job(c, resolved_url="https://example.com/x", is_confirmed=True)
    assert job.source_relationship_hint == "EXACT_ENTITY_DOMAIN"


def test_job_probable_gets_no_hint():
    c = _candidate("dc_1", "Test Hotel")
    job = build_import_job(c, resolved_url="https://example.com/x", is_confirmed=False)
    assert job.source_relationship_hint == ""


def test_generated_manifest_validates_against_real_importer_schema():
    jobs = [build_import_job(_candidate("dc_%02d" % i, "Hotel %d" % i),
                             resolved_url="https://example.com/hotel-%d" % i, is_confirmed=True)
           for i in range(3)]
    manifests = build_batches(jobs, batch_id_prefix="columbus-wave1-hotel",
                              batch_name_prefix="Columbus Wave 1 Hotel")
    assert len(manifests) == 1
    with tempfile.TemporaryDirectory() as tmp:
        path = Path(tmp) / "m.json"
        path.write_text(dumps_batch_manifest(manifests[0]), encoding="utf-8")
        manifest = load_manifest(str(path))
        errors = validate_manifest(manifest, extractor="anthropic", repo_root=".")
        assert errors == ()


def test_max_20_jobs_per_batch():
    jobs = [build_import_job(_candidate("dc_%03d" % i, "Hotel %d" % i),
                             resolved_url="https://example.com/hotel-%d" % i, is_confirmed=True)
           for i in range(45)]
    manifests = build_batches(jobs, batch_id_prefix="columbus-wave1-hotel",
                              batch_name_prefix="Columbus Wave 1 Hotel")
    assert len(manifests) == 3
    assert [len(m["jobs"]) for m in manifests] == [20, 20, 5]


def test_stable_ordering_deterministic():
    jobs = [build_import_job(_candidate("dc_%02d" % i, "Hotel %d" % i),
                             resolved_url="https://example.com/hotel-%d" % i, is_confirmed=True)
           for i in (3, 1, 2)]
    manifests1 = build_batches(jobs, batch_id_prefix="p", batch_name_prefix="P")
    manifests2 = build_batches(list(reversed(jobs)), batch_id_prefix="p", batch_name_prefix="P")
    assert dumps_batch_manifest(manifests1[0]) == dumps_batch_manifest(manifests2[0])


def test_no_duplicate_locations_across_batch():
    jobs = [build_import_job(_candidate("dc_1", "Hotel A"), resolved_url="https://a.com", is_confirmed=True),
           build_import_job(_candidate("dc_1", "Hotel A"), resolved_url="https://a.com", is_confirmed=True)]
    manifests = build_batches(jobs, batch_id_prefix="p", batch_name_prefix="P")
    assert sum(len(m["jobs"]) for m in manifests) == 1


def test_deterministic_batch_ids():
    jobs = [build_import_job(_candidate("dc_1", "Hotel A"), resolved_url="https://a.com", is_confirmed=True)]
    manifests = build_batches(jobs, batch_id_prefix="columbus-wave1-hotel", batch_name_prefix="X")
    assert manifests[0]["batch_id"] == "columbus-wave1-hotel-001"


def test_no_pet_policy_or_ratings_fields_in_job():
    c = _candidate("dc_1", "Test Hotel")
    job = build_import_job(c, resolved_url="https://example.com/x", is_confirmed=True)
    manifests = build_batches([job], batch_id_prefix="p", batch_name_prefix="P")
    job_keys = set(manifests[0]["jobs"][0].keys())
    forbidden = {"pet_policy", "rating", "reviews", "expected_status", "amenities"}
    assert not (job_keys & forbidden)


def test_batch_index_shape():
    hotel_job = build_import_job(_candidate("dc_h1", "Hotel A"), resolved_url="https://a.com", is_confirmed=True)
    motel_job = build_import_job(_candidate("dc_m1", "Motel A", category=C.CATEGORY_MOTEL),
                                 resolved_url="https://b.com", is_confirmed=True)
    hotel_manifests = build_batches([hotel_job], batch_id_prefix="columbus-wave1-hotel", batch_name_prefix="H")
    motel_manifests = build_batches([motel_job], batch_id_prefix="columbus-wave1-motel", batch_name_prefix="M")
    index = build_batch_index(hotel_manifests, motel_manifests,
                              hotel_paths=["hotel_batch_001.json"], motel_paths=["motel_batch_001.json"])
    assert index["total_batches"] == 2
    assert index["total_jobs"] == 2


def test_no_batches_from_empty_job_list():
    assert build_batches([], batch_id_prefix="p", batch_name_prefix="P") == ()
