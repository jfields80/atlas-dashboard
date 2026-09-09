"""PetTripFinder real demo-media activation tests (AES-WEB-002M.3).

Drives the *real* launch package (``launch_packages/pettripfinder/`` -- its
committed ``demo_media.json`` manifest and repository-owned deterministic demo
PNGs) through the real M.2 ingestion path and the full engine chain, proving
the mission matrix:

A. manifest/config validation
B. real pilot ingestion (HERO_IMAGE refs on configured listings only)
C. generated HTML (card + profile images; image-less listing untouched)
D. bundle (asset tuple, content-addressed paths, materialized bytes)
E. request safety (no remote/data/protocol-relative srcs)

Claims F (determinism) and G (zero-image fallback) live in their own modules --
``test_pettripfinder_demo_media_determinism.py`` and
``..._fallback.py`` -- because each needs a DIFFERENT execution of the chain
rather than a different assertion about this one.

**Why the split, and why this module now builds once.**
ATLAS-THROUGHPUT-001 found each of these tests rebuilding the same committed
launch package at 280-425 s a time. 002 introduced the module fixture below and
cut nine builds to five. 006 then measured what remained: 1,375.7 s, 38% of the
entire broad suite, and the floor under every sharded remote run, because no
split into jobs can finish faster than its slowest indivisible module.

007 removed the last redundant build here. Every claim in this module is about
the RESULT of one with-media chain, so there is exactly one, and the claim that
used to build a second identical chain (``no filesystem path in the dataset``)
now reads the shared one -- and checks more than it used to, because it can now
also assert that the fixture's own temp root never leaked in.
"""

from __future__ import annotations

import pathlib
import sys

import pytest

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from engines.website_generation.contracts.artifacts import sha256_of_bytes  # noqa: E402
from engines.website_generation.contracts.enums import AssetRole  # noqa: E402
from repositories.artifact_store_repository import ArtifactStoreRepository  # noqa: E402
from repositories.site_bundle_repository import SiteBundleRepository  # noqa: E402
from scripts.generate_pettripfinder_pilot import LAUNCH_PACKAGE_DIR  # noqa: E402
from scripts.pettripfinder.media_ingestion import (  # noqa: E402
    MediaIngestionError,
    ingest_demo_media,
    load_demo_media_manifest,
)
_HERE = pathlib.Path(__file__).resolve().parent
if str(_HERE) not in sys.path:
    sys.path.insert(0, str(_HERE))

from pettripfinder_demo_chain import (  # noqa: E402
    IMAGED_SLUGS,
    IMAGELESS_SLUG,
    IMG_TAG_RE,
    SRC_RE,
    expected_by_category,
    real_chain,
)


@pytest.fixture(scope="module")
def with_media_chain(tmp_path_factory):
    """ATLAS-THROUGHPUT-002 -- the CONSUMER-REUSE claim, completed in 007.

    One real with-media chain, built once per module and read by every test
    below, because every one of them asserts about the RESULT of the chain
    (ingestion refs, HTML, bundle contents, request safety) rather than about
    the act of building it. The claims that need their own execution -- two
    independent builds for determinism, a no-media build for the fallback --
    live in their own modules and keep their own builds.

    Yields ``(dataset, rendered, bundle, cas, root)``.
    """
    root = tmp_path_factory.mktemp("with_media_chain")
    dataset, rendered, bundle, cas = real_chain(root, with_media=True)
    return dataset, rendered, bundle, cas, root


# --------------------------------------------------------------------------- #
# A. Manifest / config
# --------------------------------------------------------------------------- #

class TestDemoMediaManifest:
    def test_committed_manifest_loads_with_two_entries(self):
        entries = load_demo_media_manifest(LAUNCH_PACKAGE_DIR)
        assert len(entries) == 2
        assert [e["image"] for e in entries] == [
            "media/park-demo.png", "media/dining-demo.png",
        ]

    def test_paths_are_relative_and_forward_slash(self):
        for entry in load_demo_media_manifest(LAUNCH_PACKAGE_DIR):
            image = entry["image"]
            assert not image.startswith("/")
            assert "\\" not in image and ":" not in image
            assert (LAUNCH_PACKAGE_DIR / image).is_file()

    def test_missing_manifest_is_valid_zero_media(self, tmp_path):
        assert load_demo_media_manifest(tmp_path) == ()

    def test_absolute_path_rejected(self, tmp_path):
        (tmp_path / "demo_media.json").write_text(
            '{"demo_media": [{"name": "X", "city": "C", "state": "OH", '
            '"image": "/etc/evil.png", "alt_text": "x"}]}',
            encoding="utf-8",
        )
        with pytest.raises(MediaIngestionError) as exc:
            load_demo_media_manifest(tmp_path)
        assert exc.value.reason == "invalid_manifest_path"

    def test_traversal_and_backslash_and_drive_rejected(self, tmp_path):
        for bad in ("../outside.png", "media\\x.png", "C:/x.png"):
            (tmp_path / "demo_media.json").write_text(
                '{"demo_media": [{"name": "X", "city": "C", "state": "OH", '
                '"image": "%s", "alt_text": "x"}]}' % bad.replace("\\", "\\\\"),
                encoding="utf-8",
            )
            with pytest.raises(MediaIngestionError):
                load_demo_media_manifest(tmp_path)

    def test_missing_field_rejected(self, tmp_path):
        (tmp_path / "demo_media.json").write_text(
            '{"demo_media": [{"name": "X", "city": "C", "state": "OH", '
            '"image": "media/x.png", "alt_text": "  "}]}',
            encoding="utf-8",
        )
        with pytest.raises(MediaIngestionError) as exc:
            load_demo_media_manifest(tmp_path)
        assert exc.value.reason == "invalid_manifest_entry"

    def test_manifest_image_file_missing_fails_clearly(self, tmp_path):
        (tmp_path / "demo_media.json").write_text(
            '{"demo_media": [{"name": "X", "city": "C", "state": "OH", '
            '"image": "media/missing.png", "alt_text": "x"}]}',
            encoding="utf-8",
        )
        entries = load_demo_media_manifest(tmp_path)
        cas = ArtifactStoreRepository(tmp_path / "cas")
        with pytest.raises(MediaIngestionError) as exc:
            ingest_demo_media(entries, tmp_path, cas)
        assert exc.value.reason == "unreadable_file"


# --------------------------------------------------------------------------- #
# B. Real pilot ingestion
# --------------------------------------------------------------------------- #

class TestRealPilotIngestion:
    def test_configured_listings_gain_hero_refs(self, with_media_chain):
        dataset, _, _, _, _ = with_media_chain
        by_slug = {l.slug: l for l in dataset.listings}
        for slug in IMAGED_SLUGS:
            (ref,) = by_slug[slug].assets
            assert ref.role is AssetRole.HERO_IMAGE
            assert ref.source_kind == "OPERATOR_UPLOAD"
            assert ref.bundle_allowed is True
            assert ref.alt_text.strip()
            assert "illustration" in ref.alt_text  # honest demo wording
            assert (ref.width, ref.height) == (1200, 800)
        assert by_slug[IMAGELESS_SLUG].assets == ()

    def test_asset_hashes_match_committed_bytes(self, with_media_chain):
        dataset, _, _, _, _ = with_media_chain
        by_slug = {l.slug: l for l in dataset.listings}
        park = (LAUNCH_PACKAGE_DIR / "media" / "park-demo.png").read_bytes()
        dining = (LAUNCH_PACKAGE_DIR / "media" / "dining-demo.png").read_bytes()
        assert by_slug["scioto-audubon-metro-park"].assets[0].asset_hash == sha256_of_bytes(park)
        assert by_slug["land-grant-brewing-company"].assets[0].asset_hash == sha256_of_bytes(dining)

    def test_no_filesystem_path_in_dataset(self, with_media_chain):
        """ATLAS-THROUGHPUT-007: this used to build a SECOND identical chain
        (262 s measured) to assert about a dataset the module had already
        built. It now reads the shared one and checks strictly more -- the
        fixture's own temp root is a filesystem path that must not have leaked
        in either, which the private build could never have caught, because it
        was checking a tree it had just created for itself."""
        from engines.website_generation.contracts.artifacts import canonical_artifact_json

        dataset, _, _, _, root = with_media_chain
        text = canonical_artifact_json(dataset)
        assert "media/park-demo.png" not in text
        assert "launch_packages" not in text
        assert "\\\\" not in text
        assert str(root) not in text
        assert root.name not in text


# --------------------------------------------------------------------------- #
# C. Generated HTML
# --------------------------------------------------------------------------- #

class TestGeneratedHtml:
    def _html(self, rendered, route):
        return next(p for p in rendered.page_details if p.route == route).html

    def test_configured_card_and_profile_render_img(self, with_media_chain):
        dataset, rendered, _, _, _ = with_media_chain
        park_hash = next(
            l.assets[0].asset_hash for l in dataset.listings
            if l.slug == "scioto-audubon-metro-park"
        )
        expected_src = "/assets/media/%s.png" % park_hash
        category = self._html(rendered, "/pet-friendly-parks/")
        profile = self._html(rendered, "/pet-friendly-parks/scioto-audubon-metro-park/")
        assert 'src="%s"' % expected_src in category
        assert "ac-listing--card-image" in category
        assert 'src="%s"' % expected_src in profile
        assert "ac-profile--primary-image" in profile
        assert 'alt="Pet-friendly park travel illustration"' in category

    def test_imageless_listing_stays_text_only(self, with_media_chain):
        _, rendered, _, _, _ = with_media_chain
        for route in ("/pet-friendly-hotels/", "/pet-friendly-hotels/%s/" % IMAGELESS_SLUG):
            html = self._html(rendered, route)
            assert "<img" not in html
            assert "card-image" not in html and "primary-image" not in html

    def test_img_tags_sitewide_are_exactly_the_two_demo_illustrations(self, with_media_chain):
        # 2 imaged listings x (1 category card + 1 profile primary) = 4, plus
        # J.20 related-listing repetition: the Scioto Audubon card appears on
        # every OTHER park profile and the Land-Grant card on every OTHER
        # restaurant profile. Every img is one of the two repository-owned demo
        # illustrations; all other listings stay text-only.
        #
        # PTF-MARKET-AUTHORITY-SHARDING-001: the repetition terms are counted
        # from the seed shards rather than pinned at 13 and 12. The formula is
        # the behaviour under test; the sibling counts are just how many
        # listings the markets happen to seed, and a market adding one park
        # should not make this test wrong.
        by_category = expected_by_category()
        expected = (4 + (by_category["pet-friendly-parks"] - 1)
                    + (by_category["pet-friendly-restaurants"] - 1))
        _, rendered, _, _, _ = with_media_chain
        total = sum(len(IMG_TAG_RE.findall(p.html)) for p in rendered.page_details)
        assert total == expected


# --------------------------------------------------------------------------- #
# D. Bundle + materialization
# --------------------------------------------------------------------------- #

class TestBundle:
    def test_two_content_addressed_assets_materialized(self, with_media_chain, tmp_path):
        _, _, bundle, cas, _ = with_media_chain
        assert len(bundle.assets) == 2
        for asset in bundle.assets:
            assert asset.path == "assets/media/%s.png" % asset.asset_hash
            assert bundle.file_map[asset.path] == asset.asset_hash

        destination = tmp_path / "site"
        SiteBundleRepository().materialize(
            bundle, destination,
            asset_bytes={a.asset_hash: cas.get_bytes(a.asset_hash) for a in bundle.assets},
        )
        media_dir = destination / "assets" / "media"
        files = sorted(media_dir.iterdir())
        assert len(files) == 2
        for f in files:
            assert sha256_of_bytes(f.read_bytes()) == f.name.split(".")[0]

    def test_no_duplicated_bytes(self, with_media_chain):
        _, _, bundle, _, _ = with_media_chain
        hashes = [a.asset_hash for a in bundle.assets]
        assert len(hashes) == len(set(hashes))


# --------------------------------------------------------------------------- #
# E. Request safety
# --------------------------------------------------------------------------- #

class TestRequestSafety:
    def test_every_img_src_is_bundled_local(self, with_media_chain):
        _, rendered, bundle, _, _ = with_media_chain
        for page in rendered.page_details:
            for img in IMG_TAG_RE.findall(page.html):
                src = SRC_RE.search(img).group(1)
                assert src.startswith("/assets/media/")
                assert not src.startswith(("http://", "https://", "//", "data:"))
                assert src.lstrip("/") in bundle.file_map
