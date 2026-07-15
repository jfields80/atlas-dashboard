"""Media asset plumbing tests -- assembly half (AES-WEB-002M.1).

Covers the contract additions (ListingAssetRef metadata, BundleAssetRef,
SiteBundle.assets), the deterministic path derivation
(``media_asset_path``), fail-closed asset collection
(``collect_media_assets``), and the Assembly Engine's optional
``listing_dataset`` input -- including the M.1 preservation invariant:
omitting the input, or supplying a dataset with no bundle-authorized
assets, produces a ``file_map``/``bundle_hash`` byte-identical to pre-M.1
output. The repository half (CAS raw bytes + materialization) lives in
``tests/website_generation/repositories/test_media_materialization.py``.
"""

from __future__ import annotations

import pytest

from engines.website_generation.assembly.assembly_builders import (
    MEDIA_ASSET_DIR,
    MEDIA_MIME_EXTENSIONS,
    collect_media_assets,
    media_asset_path,
)
from engines.website_generation.assembly.assembly_engine import AssemblyEngine
from engines.website_generation.contracts.artifacts import (
    BundleAssetRef,
    ListingAssetRef,
    ListingCategory,
    ListingDataset,
    ListingRecord,
    SiteBundle,
    artifact_sha256,
    canonical_artifact_json,
    sha256_of_bytes,
)
from engines.website_generation.contracts.enums import ArtifactKind, AssetRole
from engines.website_generation.contracts.errors import AssemblyError
from engines.website_generation.contracts.versions import SCHEMA_VERSIONS

from . import assemble, brand_package, rendered_page_set, seo_package

# Deterministic fixture bytes: a syntactically minimal PNG header + fixed
# payload. Content is irrelevant to M.1 (no decoding happens anywhere);
# what matters is that the hash is real and stable.
FIXTURE_BYTES = b"\x89PNG\r\n\x1a\n" + bytes(range(48))
FIXTURE_HASH = sha256_of_bytes(FIXTURE_BYTES)

SECOND_BYTES = b"\x89PNG\r\n\x1a\n" + bytes(range(48, 96))
SECOND_HASH = sha256_of_bytes(SECOND_BYTES)


def asset_ref(**overrides) -> ListingAssetRef:
    fields = dict(
        role=AssetRole.HERO_IMAGE,
        asset_hash=FIXTURE_HASH,
        alt_text="Lakeview Lodge exterior",
        width=1200,
        height=800,
        mime_type="image/png",
        source_kind="OPERATOR_UPLOAD",
        bundle_allowed=True,
        attribution_text="",
    )
    fields.update(overrides)
    return ListingAssetRef(**fields)


def listing(listing_id: str = "lst-1", assets=()) -> ListingRecord:
    return ListingRecord(
        listing_id=listing_id,
        business_name=listing_id.replace("-", " ").title(),
        slug=listing_id,
        category_id="cat-1",
        assets=tuple(assets),
    )


def dataset(listings=()) -> ListingDataset:
    return ListingDataset(
        schema_version=SCHEMA_VERSIONS[ArtifactKind.LISTING_DATASET],
        artifact_kind=ArtifactKind.LISTING_DATASET,
        source_hashes={},
        listings=tuple(listings),
        categories=(ListingCategory(category_id="cat-1", label="Cat", slug="cat"),),
        locations=(),
    )


def assemble_with(listing_dataset) -> SiteBundle:
    return AssemblyEngine().assemble(
        rendered_page_set(), seo_package(), brand_package(),
        listing_dataset=listing_dataset,
    )


# --------------------------------------------------------------------------- #
# A. ListingAssetRef metadata contract (ListingDataset 1.1.0)
# --------------------------------------------------------------------------- #

class TestListingAssetRefContract:
    def test_two_field_construction_still_valid(self):
        # The 1.0.0 construction shape (role + hash) remains valid -- every
        # new field is additive with a default.
        ref = ListingAssetRef(role=AssetRole.HERO_IMAGE, asset_hash=FIXTURE_HASH)
        assert ref.alt_text == ""
        assert ref.width == 0 and ref.height == 0
        assert ref.mime_type == ""
        assert ref.source_kind == ""
        assert ref.attribution_text == ""

    def test_bundle_allowed_defaults_to_refusal(self):
        # Licensing fail-closed (operator decision 3): an asset without an
        # explicit grant is never bundle-authorized.
        ref = ListingAssetRef(role=AssetRole.HERO_IMAGE, asset_hash=FIXTURE_HASH)
        assert ref.bundle_allowed is False

    def test_v1_replay_preserves_1_0_0_serialization(self):
        # A 1.0.0 payload replayed through the registered 1.0.0 model chain
        # re-serializes byte-identically -- no additive-field leakage.
        import json

        from engines.website_generation.contracts.artifacts import ListingDatasetV1
        from engines.website_generation.contracts.versions import (
            registered_artifact_model,
        )

        assert registered_artifact_model(
            ArtifactKind.LISTING_DATASET, "1.0.0"
        ) is ListingDatasetV1
        legacy = ListingDatasetV1(
            schema_version="1.0.0",
            artifact_kind=ArtifactKind.LISTING_DATASET,
            source_hashes={},
            listings=(),
            categories=(),
            locations=(),
        )
        text = canonical_artifact_json(legacy)
        replayed = ListingDatasetV1(**json.loads(text))
        assert canonical_artifact_json(replayed) == text
        for field in ("alt_text", "bundle_allowed", "mime_type"):
            assert field not in text

    def test_v1_nested_asset_ref_has_no_metadata_fields(self):
        from engines.website_generation.contracts.artifacts import ListingAssetRefV1

        v1_fields = set(ListingAssetRefV1.__fields__)
        assert v1_fields == {"role", "asset_hash"}


# --------------------------------------------------------------------------- #
# B. Deterministic asset path derivation
# --------------------------------------------------------------------------- #

class TestMediaAssetPath:
    def test_png_path_shape(self):
        path, error = media_asset_path(FIXTURE_HASH, "image/png")
        assert error is None
        assert path == "%s/%s.png" % (MEDIA_ASSET_DIR, FIXTURE_HASH)

    @pytest.mark.parametrize("mime,ext", sorted(MEDIA_MIME_EXTENSIONS.items()))
    def test_every_supported_mime_maps(self, mime, ext):
        path, error = media_asset_path(FIXTURE_HASH, mime)
        assert error is None
        assert path.endswith("." + ext)

    def test_unknown_mime_rejected(self):
        path, error = media_asset_path(FIXTURE_HASH, "image/tiff")
        assert path is None and error == "unsupported_mime_type"

    def test_uppercase_hash_rejected_not_normalized(self):
        path, error = media_asset_path(FIXTURE_HASH.upper(), "image/png")
        assert path is None and error == "invalid_asset_hash"

    def test_truncated_hash_rejected(self):
        path, error = media_asset_path(FIXTURE_HASH[:40], "image/png")
        assert path is None and error == "invalid_asset_hash"

    def test_path_traversal_impossible_by_construction(self):
        # A valid input can only ever produce assets/media/<hex>.<ext>;
        # adversarial hash strings are rejected before path assembly.
        path, error = media_asset_path("../" + FIXTURE_HASH[3:], "image/png")
        assert path is None and error == "invalid_asset_hash"

    def test_derivation_is_deterministic(self):
        assert media_asset_path(FIXTURE_HASH, "image/png") == media_asset_path(
            FIXTURE_HASH, "image/png"
        )


# --------------------------------------------------------------------------- #
# C. Asset collection (fail-closed licensing, dedupe, determinism)
# --------------------------------------------------------------------------- #

class TestCollectMediaAssets:
    def test_authorized_asset_collected(self):
        pairs, issues = collect_media_assets(dataset([listing(assets=[asset_ref()])]))
        assert pairs == ((FIXTURE_HASH, "image/png"),)
        assert issues == ()

    def test_unauthorized_asset_skipped_silently(self):
        pairs, issues = collect_media_assets(
            dataset([listing(assets=[asset_ref(bundle_allowed=False)])])
        )
        assert pairs == () and issues == ()

    def test_duplicate_asset_across_listings_deduplicates(self):
        pairs, _ = collect_media_assets(
            dataset([
                listing("lst-1", assets=[asset_ref()]),
                listing("lst-2", assets=[asset_ref()]),
            ])
        )
        assert pairs == ((FIXTURE_HASH, "image/png"),)

    def test_conflicting_mime_declarations_reported(self):
        _, issues = collect_media_assets(
            dataset([
                listing("lst-1", assets=[asset_ref()]),
                listing("lst-2", assets=[asset_ref(mime_type="image/jpeg")]),
            ])
        )
        assert len(issues) == 1
        assert "conflicting mime types" in issues[0]

    def test_output_sorted_by_hash(self):
        pairs, _ = collect_media_assets(
            dataset([
                listing(assets=[
                    asset_ref(asset_hash=max(FIXTURE_HASH, SECOND_HASH)),
                    asset_ref(asset_hash=min(FIXTURE_HASH, SECOND_HASH)),
                ]),
            ])
        )
        assert list(pairs) == sorted(pairs)


# --------------------------------------------------------------------------- #
# D. Assembly integration
# --------------------------------------------------------------------------- #

class TestAssemblyMediaMapping:
    def test_omitted_dataset_is_byte_identical_to_pre_m1(self):
        # The M.1 preservation invariant (operator decision 14): the default
        # call path's file_map and bundle_hash never move.
        default_bundle = assemble()
        explicit_none = AssemblyEngine().assemble(
            rendered_page_set(), seo_package(), brand_package(), listing_dataset=None,
        )
        assert default_bundle.file_map == explicit_none.file_map
        assert default_bundle.bundle_hash == explicit_none.bundle_hash
        assert default_bundle.assets == () == explicit_none.assets

    def test_assetless_dataset_changes_nothing_but_provenance(self):
        without = assemble()
        with_dataset = assemble_with(dataset([listing()]))
        assert with_dataset.file_map == without.file_map
        assert with_dataset.bundle_hash == without.bundle_hash
        assert with_dataset.assets == ()
        assert "listing_dataset" in with_dataset.source_hashes

    def test_authorized_asset_enters_file_map_and_assets(self):
        bundle = assemble_with(dataset([listing(assets=[asset_ref()])]))
        expected_path = "%s/%s.png" % (MEDIA_ASSET_DIR, FIXTURE_HASH)
        assert bundle.file_map[expected_path] == FIXTURE_HASH
        assert bundle.assets == (
            BundleAssetRef(
                path=expected_path, asset_hash=FIXTURE_HASH, mime_type="image/png",
            ),
        )
        # References only: no BundleFile carries the asset path.
        assert expected_path not in {bf.path for bf in bundle.files}

    def test_bundle_hash_covers_assets(self):
        without = assemble()
        with_asset = assemble_with(dataset([listing(assets=[asset_ref()])]))
        assert with_asset.bundle_hash != without.bundle_hash

    def test_unauthorized_asset_not_bundled(self):
        bundle = assemble_with(
            dataset([listing(assets=[asset_ref(bundle_allowed=False)])])
        )
        assert bundle.assets == ()
        assert not any(p.startswith(MEDIA_ASSET_DIR) for p in bundle.file_map)

    def test_authorized_asset_with_unknown_mime_batch_fails(self):
        with pytest.raises(AssemblyError) as exc:
            assemble_with(dataset([listing(assets=[asset_ref(mime_type="image/tiff")])]))
        entries = exc.value.diagnostics["invalid_media_assets"]
        assert entries[0]["reason"] == "unsupported_mime_type"
        assert entries[0]["asset_hash"] == FIXTURE_HASH

    def test_authorized_asset_with_malformed_hash_batch_fails(self):
        with pytest.raises(AssemblyError) as exc:
            assemble_with(dataset([listing(assets=[asset_ref(asset_hash="nothex")])]))
        assert exc.value.diagnostics["invalid_media_assets"][0]["reason"] == "invalid_asset_hash"

    def test_conflicting_mime_declarations_batch_fail(self):
        with pytest.raises(AssemblyError) as exc:
            assemble_with(
                dataset([
                    listing("lst-1", assets=[asset_ref()]),
                    listing("lst-2", assets=[asset_ref(mime_type="image/jpeg")]),
                ])
            )
        reasons = [e["reason"] for e in exc.value.diagnostics["invalid_media_assets"]]
        assert any("conflicting mime types" in r for r in reasons)

    def test_repeated_assembly_is_deterministic(self):
        ds = dataset([listing(assets=[asset_ref()])])
        a = assemble_with(ds)
        b = assemble_with(ds)
        assert artifact_sha256(a) == artifact_sha256(b)

    def test_schema_version_is_1_2_0(self):
        bundle = assemble_with(dataset([listing(assets=[asset_ref()])]))
        assert bundle.schema_version == "1.2.0"
