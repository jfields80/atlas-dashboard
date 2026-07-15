"""Operator media ingestion tests (AES-WEB-002M.2; mission matrix §I).

Covers ``scripts/pettripfinder/media_ingestion.py`` (signature validation,
stdlib dimension extraction, MIME-from-bytes derivation, CAS storage, and
the durable ``ListingAssetRef`` shape -- no filesystem path leakage) and
the builder's ``media_by_key`` overlay (the pure converter receives only
already-ingested refs; ``media_ingestion`` owns all I/O).
"""

from __future__ import annotations

import pathlib
import sys

import pytest

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(_REPO_ROOT / "tests") not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT / "tests"))

from website_generation.fixtures.media_fixtures import make_test_jpeg, make_test_png  # noqa: E402

from engines.website_generation.contracts.artifacts import (  # noqa: E402
    ListingAssetRef,
    sha256_of_bytes,
)
from engines.website_generation.contracts.enums import AssetRole  # noqa: E402
from repositories.artifact_store_repository import ArtifactStoreRepository  # noqa: E402
from scripts.pettripfinder.listing_dataset_builder import build_listing_dataset  # noqa: E402
from scripts.pettripfinder.media_ingestion import (  # noqa: E402
    MediaIngestionError,
    ingest_operator_image,
    validate_image_bytes,
)

_CATEGORIES = [{"name": "Hotels", "slug": "hotels"}]


def _biz(name="Acme Inn"):
    return {"name": name, "category": "Hotels", "city": "Columbus", "state": "OH"}


# --------------------------------------------------------------------------- #
# Byte validation + dimension extraction
# --------------------------------------------------------------------------- #

class TestValidateImageBytes:
    def test_valid_png_dimensions(self):
        validated = validate_image_bytes(make_test_png(width=32, height=20))
        assert validated.mime_type == "image/png"
        assert (validated.width, validated.height) == (32, 20)

    def test_valid_jpeg_dimensions(self):
        validated = validate_image_bytes(make_test_jpeg(width=48, height=36))
        assert validated.mime_type == "image/jpeg"
        assert (validated.width, validated.height) == (48, 36)

    def test_dimensions_never_zero_on_success(self):
        for data in (make_test_png(1, 1), make_test_jpeg(1, 1)):
            validated = validate_image_bytes(data)
            assert validated.width > 0 and validated.height > 0

    def test_malformed_png_rejected(self):
        truncated = make_test_png()[:12]
        with pytest.raises(MediaIngestionError) as exc:
            validate_image_bytes(truncated)
        assert exc.value.reason == "malformed_png"

    def test_png_without_ihdr_rejected(self):
        bad = b"\x89PNG\r\n\x1a\n" + b"\x00" * 16
        with pytest.raises(MediaIngestionError) as exc:
            validate_image_bytes(bad)
        assert exc.value.reason == "malformed_png"

    def test_malformed_jpeg_rejected(self):
        # SOI then garbage where a marker must be.
        bad = b"\xff\xd8" + b"no markers here"
        with pytest.raises(MediaIngestionError) as exc:
            validate_image_bytes(bad)
        assert exc.value.reason == "malformed_jpeg"

    def test_jpeg_without_frame_header_rejected(self):
        # SOI + EOI, no SOF -- structurally empty.
        with pytest.raises(MediaIngestionError) as exc:
            validate_image_bytes(b"\xff\xd8\xff\xd9")
        assert exc.value.reason == "malformed_jpeg"

    def test_unsupported_format_rejected(self):
        # A GIF signature: real image format, deliberately not V1-ingestible.
        with pytest.raises(MediaIngestionError) as exc:
            validate_image_bytes(b"GIF89a" + b"\x00" * 32)
        assert exc.value.reason == "unsupported_format"

    def test_svg_and_webp_not_operator_ingestible(self):
        # Bundle-capable from M.1, but ingestion is narrower (mission §11/§12
        # fail-closed): SVG security is unresolved, WebP dimensions are not
        # honestly parsed in V1.
        with pytest.raises(MediaIngestionError):
            validate_image_bytes(b"<svg xmlns='http://www.w3.org/2000/svg'/>")
        with pytest.raises(MediaIngestionError):
            validate_image_bytes(b"RIFF\x00\x00\x00\x00WEBPVP8 ")

    def test_mime_derived_from_bytes_never_extension(self, tmp_path):
        # A PNG payload behind a .jpg name still ingests as image/png --
        # the signature is the truth; extensions are never consulted.
        lying_path = tmp_path / "photo.jpg"
        lying_path.write_bytes(make_test_png(width=10, height=8))
        store = ArtifactStoreRepository(tmp_path / "cas")
        ref = ingest_operator_image(lying_path, store)
        assert ref.mime_type == "image/png"
        assert (ref.width, ref.height) == (10, 8)


# --------------------------------------------------------------------------- #
# CAS ingestion + durable ref shape
# --------------------------------------------------------------------------- #

class TestIngestOperatorImage:
    def test_full_ingestion_shape(self, tmp_path):
        data = make_test_png(width=24, height=16)
        image_path = tmp_path / "lodge.png"
        image_path.write_bytes(data)
        store = ArtifactStoreRepository(tmp_path / "cas")

        ref = ingest_operator_image(image_path, store, alt_text="Lodge exterior")

        assert ref.role is AssetRole.HERO_IMAGE
        assert ref.asset_hash == sha256_of_bytes(data)
        assert store.get_bytes(ref.asset_hash) == data
        assert ref.alt_text == "Lodge exterior"
        assert (ref.width, ref.height) == (24, 16)
        assert ref.mime_type == "image/png"
        assert ref.source_kind == "OPERATOR_UPLOAD"
        assert ref.bundle_allowed is True
        assert ref.attribution_text == ""

    def test_no_path_leaks_into_the_ref(self, tmp_path):
        # The local path is ingestion-only input: nothing derived from it
        # (directory name, filename, extension, separators) survives into
        # the durable ref (mission §9).
        image_path = tmp_path / "SECRET-DIRNAME" / "photo.png"
        image_path.parent.mkdir()
        image_path.write_bytes(make_test_png())
        store = ArtifactStoreRepository(tmp_path / "cas")
        ref = ingest_operator_image(image_path, store)
        text = str(ref.dict())
        assert "SECRET-DIRNAME" not in text
        assert "photo.png" not in text
        assert "\\" not in text

    def test_missing_file_fails_closed(self, tmp_path):
        store = ArtifactStoreRepository(tmp_path / "cas")
        with pytest.raises(MediaIngestionError) as exc:
            ingest_operator_image(tmp_path / "nope.png", store)
        assert exc.value.reason == "unreadable_file"

    def test_ingestion_is_deterministic(self, tmp_path):
        image_path = tmp_path / "a.png"
        image_path.write_bytes(make_test_png())
        store = ArtifactStoreRepository(tmp_path / "cas")
        first = ingest_operator_image(image_path, store, alt_text="x")
        second = ingest_operator_image(image_path, store, alt_text="x")
        assert first == second


# --------------------------------------------------------------------------- #
# Builder media overlay (pure -- refs in, records out)
# --------------------------------------------------------------------------- #

class TestBuilderMediaOverlay:
    def _ref(self):
        data = make_test_png()
        return ListingAssetRef(
            role=AssetRole.HERO_IMAGE,
            asset_hash=sha256_of_bytes(data),
            alt_text="Front",
            width=6,
            height=4,
            mime_type="image/png",
            source_kind="OPERATOR_UPLOAD",
            bundle_allowed=True,
        )

    def test_media_by_key_attaches_assets(self):
        ref = self._ref()
        result = build_listing_dataset(
            seed_businesses=[_biz()],
            categories=_CATEGORIES,
            media_by_key={("acme inn", "columbus", "oh"): (ref,)},
        )
        assert result.ok
        (record,) = result.dataset.listings
        assert record.assets == (ref,)

    def test_omitted_media_by_key_yields_assetless_records(self):
        result = build_listing_dataset(seed_businesses=[_biz()], categories=_CATEGORIES)
        assert result.ok
        assert result.dataset.listings[0].assets == ()

    def test_unmatched_key_yields_assetless_record(self):
        result = build_listing_dataset(
            seed_businesses=[_biz()],
            categories=_CATEGORIES,
            media_by_key={("someone else", "columbus", "oh"): (self._ref(),)},
        )
        assert result.ok
        assert result.dataset.listings[0].assets == ()
