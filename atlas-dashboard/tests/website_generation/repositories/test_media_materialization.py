"""Media asset plumbing tests -- repository half (AES-WEB-002M.1).

Covers the CAS raw-bytes object class (``ArtifactStoreRepository.put_bytes``
/``get_bytes``/``exists_bytes``: §9.1 "canonical JSON or raw bytes"; §4.3),
``SiteBundleRepository``'s binary asset materialization (byte writing from
the caller-supplied mapping, fail-closed availability/identity checks,
post-write re-hash verification), and the full M.1 plumbing proof:

    ListingDataset (asset ref) -> CAS (raw bytes) -> AssemblyEngine
    (asset map) -> SiteBundleRepository (materialization) -> on-disk
    hash-verified file, deterministic across repeated builds.

The assembly half (contracts, path derivation, collection, asset mapping)
lives in ``tests/website_generation/assembly/test_media_assets.py``.
"""

from __future__ import annotations

import pytest

from engines.website_generation.assembly.assembly_engine import AssemblyEngine
from engines.website_generation.contracts.artifacts import (
    ListingAssetRef,
    ListingCategory,
    ListingDataset,
    ListingRecord,
    sha256_of_bytes,
)
from engines.website_generation.contracts.enums import ArtifactKind, AssetRole
from engines.website_generation.contracts.errors import (
    ArtifactIntegrityError,
    ArtifactNotFoundError,
    ArtifactValidationError,
    SiteBundleRepositoryError,
)
from engines.website_generation.contracts.versions import SCHEMA_VERSIONS
from repositories.artifact_store_repository import ArtifactStoreRepository
from repositories.site_bundle_repository import SiteBundleRepository

from ..assembly import brand_package, rendered_page_set, seo_package

FIXTURE_BYTES = b"\x89PNG\r\n\x1a\n" + bytes(range(64))
FIXTURE_HASH = sha256_of_bytes(FIXTURE_BYTES)


def _dataset_with_asset(**asset_overrides) -> ListingDataset:
    fields = dict(
        role=AssetRole.HERO_IMAGE,
        asset_hash=FIXTURE_HASH,
        alt_text="Lakeview Lodge exterior",
        width=1200,
        height=800,
        mime_type="image/png",
        source_kind="OPERATOR_UPLOAD",
        bundle_allowed=True,
    )
    fields.update(asset_overrides)
    return ListingDataset(
        schema_version=SCHEMA_VERSIONS[ArtifactKind.LISTING_DATASET],
        artifact_kind=ArtifactKind.LISTING_DATASET,
        source_hashes={},
        listings=(
            ListingRecord(
                listing_id="lst-1",
                business_name="Lakeview Lodge",
                slug="lakeview-lodge",
                category_id="cat-1",
                assets=(ListingAssetRef(**fields),),
            ),
        ),
        categories=(ListingCategory(category_id="cat-1", label="Hotels", slug="hotels"),),
        locations=(),
    )


def _assemble_with_asset():
    return AssemblyEngine().assemble(
        rendered_page_set(), seo_package(), brand_package(),
        listing_dataset=_dataset_with_asset(),
    )


# --------------------------------------------------------------------------- #
# A. CAS raw-bytes object class
# --------------------------------------------------------------------------- #

class TestCasRawBytes:
    def test_put_get_roundtrip(self, tmp_path):
        store = ArtifactStoreRepository(tmp_path)
        content_hash = store.put_bytes(FIXTURE_BYTES)
        assert content_hash == FIXTURE_HASH
        assert store.get_bytes(content_hash) == FIXTURE_BYTES

    def test_put_is_idempotent(self, tmp_path):
        store = ArtifactStoreRepository(tmp_path)
        assert store.put_bytes(FIXTURE_BYTES) == store.put_bytes(FIXTURE_BYTES)

    def test_exists_bytes(self, tmp_path):
        store = ArtifactStoreRepository(tmp_path)
        assert not store.exists_bytes(FIXTURE_HASH)
        store.put_bytes(FIXTURE_BYTES)
        assert store.exists_bytes(FIXTURE_HASH)

    def test_bytes_objects_invisible_to_artifact_class(self, tmp_path):
        # Distinct object classes: a bytes hash never resolves as an
        # artifact and vice versa (.bin vs .json suffixes).
        store = ArtifactStoreRepository(tmp_path)
        store.put_bytes(FIXTURE_BYTES)
        assert not store.exists(FIXTURE_HASH)

    def test_get_missing_raises_not_found(self, tmp_path):
        store = ArtifactStoreRepository(tmp_path)
        with pytest.raises(ArtifactNotFoundError):
            store.get_bytes(FIXTURE_HASH)

    def test_tampered_object_raises_integrity_error(self, tmp_path):
        store = ArtifactStoreRepository(tmp_path)
        content_hash = store.put_bytes(FIXTURE_BYTES)
        store._bytes_path(content_hash).write_bytes(b"tampered")
        with pytest.raises(ArtifactIntegrityError):
            store.get_bytes(content_hash)

    def test_str_payload_rejected(self, tmp_path):
        # Text belongs in artifacts; the binary class refuses str payloads
        # rather than silently picking an encoding.
        store = ArtifactStoreRepository(tmp_path)
        with pytest.raises(ArtifactValidationError):
            store.put_bytes("not bytes")  # type: ignore[arg-type]


# --------------------------------------------------------------------------- #
# B. Repository asset materialization
# --------------------------------------------------------------------------- #

class TestAssetMaterialization:
    def test_asset_written_and_hash_verified(self, tmp_path):
        bundle = _assemble_with_asset()
        destination = tmp_path / "site"
        SiteBundleRepository().materialize(
            bundle, destination, asset_bytes={FIXTURE_HASH: FIXTURE_BYTES},
        )
        asset_file = destination / "assets" / "media" / (FIXTURE_HASH + ".png")
        assert asset_file.is_file()
        assert sha256_of_bytes(asset_file.read_bytes()) == FIXTURE_HASH

    def test_manifest_file_map_includes_asset(self, tmp_path):
        import json

        bundle = _assemble_with_asset()
        destination = tmp_path / "site"
        SiteBundleRepository().materialize(
            bundle, destination, asset_bytes={FIXTURE_HASH: FIXTURE_BYTES},
        )
        manifest = json.loads((destination / "bundle_manifest.json").read_text(encoding="utf-8"))
        assert manifest["file_map"]["assets/media/%s.png" % FIXTURE_HASH] == FIXTURE_HASH

    def test_missing_asset_bytes_fails_closed_before_any_write(self, tmp_path):
        bundle = _assemble_with_asset()
        destination = tmp_path / "site"
        with pytest.raises(SiteBundleRepositoryError) as exc:
            SiteBundleRepository().materialize(bundle, destination, asset_bytes=None)
        assert exc.value.category == "asset_bytes_failure"
        assert not destination.exists()

    def test_wrong_asset_bytes_fail_closed(self, tmp_path):
        bundle = _assemble_with_asset()
        with pytest.raises(SiteBundleRepositoryError) as exc:
            SiteBundleRepository().materialize(
                bundle, tmp_path / "site", asset_bytes={FIXTURE_HASH: b"wrong bytes"},
            )
        assert exc.value.category == "asset_bytes_failure"

    def test_partial_mapping_fails_closed(self, tmp_path):
        bundle = _assemble_with_asset()
        with pytest.raises(SiteBundleRepositoryError) as exc:
            SiteBundleRepository().materialize(
                bundle, tmp_path / "site", asset_bytes={},
            )
        assert exc.value.category == "asset_bytes_failure"

    def test_assetless_bundle_needs_no_mapping(self, tmp_path):
        # Pre-M.1 call shape, byte-identical behavior.
        bundle = AssemblyEngine().assemble(
            rendered_page_set(), seo_package(), brand_package(),
        )
        destination = tmp_path / "site"
        result = SiteBundleRepository().materialize(bundle, destination)
        assert (destination / "index.html").is_file()
        assert not (destination / "assets").exists()
        assert result.bundle_hash == bundle.bundle_hash

    def test_repeated_materialization_is_deterministic(self, tmp_path):
        bundle = _assemble_with_asset()
        mapping = {FIXTURE_HASH: FIXTURE_BYTES}
        SiteBundleRepository().materialize(bundle, tmp_path / "a", asset_bytes=mapping)
        SiteBundleRepository().materialize(bundle, tmp_path / "b", asset_bytes=mapping)
        rel = "assets/media/%s.png" % FIXTURE_HASH
        assert (tmp_path / "a" / rel).read_bytes() == (tmp_path / "b" / rel).read_bytes()

    def test_written_paths_include_asset(self, tmp_path):
        bundle = _assemble_with_asset()
        result = SiteBundleRepository().materialize(
            bundle, tmp_path / "site", asset_bytes={FIXTURE_HASH: FIXTURE_BYTES},
        )
        assert "assets/media/%s.png" % FIXTURE_HASH in result.written_paths


# --------------------------------------------------------------------------- #
# C. End-to-end plumbing proof (dataset -> CAS -> assemble -> materialize)
# --------------------------------------------------------------------------- #

class TestEndToEndPlumbing:
    def test_full_chain_through_real_cas(self, tmp_path):
        # 1. The operator-authorized bytes enter the CAS.
        store = ArtifactStoreRepository(tmp_path / "cas")
        content_hash = store.put_bytes(FIXTURE_BYTES)
        assert content_hash == FIXTURE_HASH

        # 2. The dataset references them by hash + role (never a path/URL).
        listing_dataset = _dataset_with_asset()

        # 3. Assembly maps the authorized asset -- pure, no CAS access.
        bundle = AssemblyEngine().assemble(
            rendered_page_set(), seo_package(), brand_package(),
            listing_dataset=listing_dataset,
        )
        (asset,) = bundle.assets

        # 4. The repository materializes from CAS-fetched bytes, fail-closed.
        destination = tmp_path / "site"
        SiteBundleRepository().materialize(
            bundle, destination,
            asset_bytes={asset.asset_hash: store.get_bytes(asset.asset_hash)},
        )
        written = destination.joinpath(*asset.path.split("/"))
        assert sha256_of_bytes(written.read_bytes()) == asset.asset_hash

    def test_repeated_full_chain_is_byte_stable(self, tmp_path):
        store = ArtifactStoreRepository(tmp_path / "cas")
        store.put_bytes(FIXTURE_BYTES)
        bundles = [_assemble_with_asset() for _ in range(2)]
        assert bundles[0].bundle_hash == bundles[1].bundle_hash
        assert bundles[0].assets == bundles[1].assets
