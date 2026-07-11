"""Content-addressable artifact store tests (AES-WEB-001 §9.1, §4.4).

Covers: put/get round-trip, content deduplication, hash verification,
tamper detection, missing-source-hash rejection, unsupported schema
rejection, and temp-directory isolation.
"""

from __future__ import annotations

import json

import pytest

from engines.website_generation import (
    ArtifactKind,
    ArtifactIntegrityError,
    ArtifactNotFoundError,
    ArtifactValidationError,
    BrandPackage,
    BusinessSpec,
    artifact_sha256,
)
from repositories.artifact_store_repository import ArtifactStoreRepository


def _spec(**overrides) -> BusinessSpec:
    fields = dict(
        schema_version="1.0.0",
        artifact_kind=ArtifactKind.BUSINESS_SPEC,
        source_hashes={"external:project": "a" * 64},
        business_name="Pet Trip Finder",
        niche="pet travel",
        audience="pet owners",
        value_proposition="verified stays",
    )
    fields.update(overrides)
    return BusinessSpec(**fields)


@pytest.fixture
def store(tmp_path) -> ArtifactStoreRepository:
    return ArtifactStoreRepository(tmp_path / "cas")


class TestRoundTrip:
    def test_put_get_round_trip(self, store):
        spec = _spec()
        digest = store.put(spec)
        loaded = store.get(digest, ArtifactKind.BUSINESS_SPEC)
        assert isinstance(loaded, BusinessSpec)
        assert artifact_sha256(loaded) == digest
        assert loaded.business_name == "Pet Trip Finder"

    def test_put_returns_content_hash(self, store):
        spec = _spec()
        assert store.put(spec) == artifact_sha256(spec)

    def test_exists(self, store):
        spec = _spec()
        assert store.exists(artifact_sha256(spec)) is False
        store.put(spec)
        assert store.exists(artifact_sha256(spec)) is True

    def test_get_missing_hash_raises_not_found(self, store):
        with pytest.raises(ArtifactNotFoundError):
            store.get("f" * 64, ArtifactKind.BUSINESS_SPEC)

    def test_kind_mismatch_on_get_rejected(self, store):
        digest = store.put(_spec())
        with pytest.raises(ArtifactValidationError):
            store.get(digest, ArtifactKind.BRAND_PACKAGE)

    def test_list_by_kind(self, store):
        h1 = store.put(_spec())
        h2 = store.put(_spec(niche="dog travel"))
        assert store.list_by_kind(ArtifactKind.BUSINESS_SPEC) == sorted(
            [h1, h2]
        )
        assert store.list_by_kind(ArtifactKind.SITE_BUNDLE) == []


class TestDeduplication:
    def test_duplicate_content_deduplicates(self, store, tmp_path):
        h1 = store.put(_spec())
        h2 = store.put(_spec())
        assert h1 == h2
        objects = list((tmp_path / "cas" / "objects").rglob("*.json"))
        assert len(objects) == 1

    def test_layout_is_derived_from_hash(self, store, tmp_path):
        digest = store.put(_spec())
        expected = (
            tmp_path / "cas" / "objects" / digest[:2] / (digest + ".json")
        )
        assert expected.exists()


class TestIntegrity:
    def test_tamper_detection(self, store, tmp_path):
        digest = store.put(_spec())
        path = tmp_path / "cas" / "objects" / digest[:2] / (digest + ".json")
        payload = json.loads(path.read_text(encoding="utf-8"))
        payload["business_name"] = "Tampered"
        path.write_text(json.dumps(payload), encoding="utf-8")
        with pytest.raises(ArtifactIntegrityError):
            store.get(digest, ArtifactKind.BUSINESS_SPEC)

    def test_stored_bytes_are_canonical(self, store, tmp_path):
        spec = _spec()
        digest = store.put(spec)
        path = tmp_path / "cas" / "objects" / digest[:2] / (digest + ".json")
        raw = path.read_text(encoding="utf-8")
        import hashlib

        assert hashlib.sha256(raw.encode("utf-8")).hexdigest() == digest


class TestSourceHashVerification:
    def test_missing_source_hash_rejected(self, store):
        orphan = BrandPackage(
            schema_version="1.0.0",
            artifact_kind=ArtifactKind.BRAND_PACKAGE,
            source_hashes={"business_spec": "c" * 64},  # not in store
        )
        with pytest.raises(ArtifactValidationError) as excinfo:
            store.put(orphan)
        assert "business_spec" in excinfo.value.diagnostics[
            "missing_source_keys"
        ]

    def test_resolvable_source_hash_accepted(self, store):
        spec_hash = store.put(_spec())
        brand = BrandPackage(
            schema_version="1.0.0",
            artifact_kind=ArtifactKind.BRAND_PACKAGE,
            source_hashes={"business_spec": spec_hash},
        )
        assert store.exists(store.put(brand))

    def test_external_prefixed_sources_are_exempt(self, store):
        # BusinessSpec provenance points at upstream Atlas records that
        # live outside the CAS (documented Phase 1 policy).
        assert store.exists(store.put(_spec()))


class TestSchemaValidation:
    def test_unsupported_schema_version_rejected_on_put(self, store):
        from engines.website_generation import UnsupportedSchemaVersionError

        bad = _spec(schema_version="9.9.9")
        with pytest.raises(UnsupportedSchemaVersionError):
            store.put(bad)

    def test_non_artifact_rejected(self, store):
        with pytest.raises(ArtifactValidationError):
            store.put({"artifact_kind": "BUSINESS_SPEC"})


class TestIsolation:
    def test_temp_directory_isolation(self, tmp_path):
        store_a = ArtifactStoreRepository(tmp_path / "a")
        store_b = ArtifactStoreRepository(tmp_path / "b")
        digest = store_a.put(_spec())
        assert store_a.exists(digest) is True
        assert store_b.exists(digest) is False

    def test_persistence_across_repository_reload(self, tmp_path):
        digest = ArtifactStoreRepository(tmp_path / "cas").put(_spec())
        reloaded = ArtifactStoreRepository(tmp_path / "cas")
        assert reloaded.exists(digest)
        loaded = reloaded.get(digest, ArtifactKind.BUSINESS_SPEC)
        assert artifact_sha256(loaded) == digest
