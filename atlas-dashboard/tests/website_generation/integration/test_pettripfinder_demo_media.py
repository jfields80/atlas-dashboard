"""PetTripFinder real demo-media activation tests (AES-WEB-002M.3).

Drives the *real* launch package (``launch_packages/pettripfinder/`` --
its committed ``demo_media.json`` manifest and repository-owned
deterministic demo PNGs) through the real M.2 ingestion path and the full
engine chain, proving the mission matrix:

A. manifest/config validation
B. real pilot ingestion (HERO_IMAGE refs on configured listings only)
C. generated HTML (card + profile images; image-less listing untouched)
D. bundle (asset tuple, content-addressed paths, materialized bytes)
E. request safety (no remote/data/protocol-relative srcs)
F. determinism (repeated build identity)
G. zero-image fallback (no manifest -> zero <img>, generation succeeds)
"""

from __future__ import annotations

import pathlib
import re
import sys

import pytest

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from engines.website_generation.assembly.assembly_engine import AssemblyEngine  # noqa: E402
from engines.website_generation.brand.brand_engine import BrandEngine  # noqa: E402
from engines.website_generation.components.component_engine import ComponentEngine  # noqa: E402
from engines.website_generation.components.registry import build_default_registry  # noqa: E402
from engines.website_generation.contracts.artifacts import (  # noqa: E402
    ArtifactKind,
    BusinessSpec,
    sha256_of_bytes,
)
from engines.website_generation.contracts.enums import AssetRole  # noqa: E402
from engines.website_generation.contracts.versions import SCHEMA_VERSIONS  # noqa: E402
from engines.website_generation.ia.information_architecture_engine import (  # noqa: E402
    InformationArchitectureEngine,
)
from engines.website_generation.layouts.layout_engine import LayoutEngine  # noqa: E402
from engines.website_generation.rendering.renderer import Renderer  # noqa: E402
from engines.website_generation.seo.seo_engine import SEOEngine  # noqa: E402
from repositories.artifact_store_repository import ArtifactStoreRepository  # noqa: E402
from repositories.site_bundle_repository import SiteBundleRepository  # noqa: E402
from scripts.generate_pettripfinder_pilot import (  # noqa: E402
    LAUNCH_PACKAGE_DIR,
    build_content_package,
    load_launch_package,
)
from scripts.pettripfinder.listing_dataset_builder import build_listing_dataset  # noqa: E402
from scripts.pettripfinder.media_ingestion import (  # noqa: E402
    MediaIngestionError,
    ingest_demo_media,
    load_demo_media_manifest,
)

_IMG_TAG_RE = re.compile(r"<img [^>]*>")
_SRC_RE = re.compile(r'src="([^"]*)"')

# The committed manifest's intent (kept in sync with demo_media.json --
# these tests fail loudly if the manifest and this expectation diverge).
IMAGED_SLUGS = {"riverbend-off-leash-dog-park", "barkside-cafe"}
# AES-WEB-002N.1: the launch package's "Duplicate Sunset Bay Inn" noise row
# was removed, so the real hotel record (and its slug) is now canonical.
IMAGELESS_SLUG = "sunset-bay-pet-friendly-inn"


def _real_chain(tmp_path, *, with_media: bool):
    """The runner's exact chain (load -> optional ingest -> build -> IA ->
    compile -> render -> assemble), media-optional."""
    package = load_launch_package()
    media_by_key = {}
    cas = None
    if with_media:
        entries = load_demo_media_manifest(LAUNCH_PACKAGE_DIR)
        cas = ArtifactStoreRepository(tmp_path / "cas")
        media_by_key = ingest_demo_media(entries, LAUNCH_PACKAGE_DIR, cas)
    result = build_listing_dataset(
        seed_businesses=package["seed_businesses"],
        categories=package["categories"],
        locations=package["locations"],
        media_by_key=media_by_key,
    )
    assert result.ok
    dataset = result.dataset

    pilot_config = package["pilot_config"]
    spec = BusinessSpec(
        schema_version=SCHEMA_VERSIONS[ArtifactKind.BUSINESS_SPEC],
        artifact_kind=ArtifactKind.BUSINESS_SPEC,
        source_hashes={},
        business_name=pilot_config["project_name"],
        niche=pilot_config["niche"],
        audience=pilot_config["audience"],
        value_proposition=pilot_config["value_proposition"],
        directory_taxonomy=tuple(c["name"] for c in pilot_config["launch_categories"]),
        monetization_model=pilot_config["monetization_model"],
        geography=pilot_config["geography"],
    )
    brand = BrandEngine().resolve(spec)
    editorial_pages = tuple((p["route"], p["title"]) for p in pilot_config["editorial_pages"])
    site = InformationArchitectureEngine().plan(
        spec, brand, listing_dataset=dataset, editorial_pages=editorial_pages,
    )
    category_routes = {c.slug: "/%s/" % c.slug for c in dataset.categories}
    content = build_content_package(
        package["pilot_content"], category_routes, dataset, dict(editorial_pages),
    )
    registry = build_default_registry()
    compilation = ComponentEngine().compile(
        site, content, listing_dataset=dataset, brand_package=brand, registry=registry,
    )
    layout = LayoutEngine(registry).compose(compilation.component_manifest, brand)
    rendered = Renderer(registry).render(
        layout, compilation.component_manifest, compilation.content_package, brand,
        render_data=compilation.render_data,
    )
    seo = SEOEngine().compile(site, compilation.content_package, spec, base_url=pilot_config["base_url"])
    bundle = AssemblyEngine().assemble(rendered, seo, brand, listing_dataset=dataset)
    return dataset, rendered, bundle, cas


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
    def test_configured_listings_gain_hero_refs(self, tmp_path):
        dataset, _, _, _ = _real_chain(tmp_path, with_media=True)
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

    def test_asset_hashes_match_committed_bytes(self, tmp_path):
        dataset, _, _, _ = _real_chain(tmp_path, with_media=True)
        by_slug = {l.slug: l for l in dataset.listings}
        park = (LAUNCH_PACKAGE_DIR / "media" / "park-demo.png").read_bytes()
        dining = (LAUNCH_PACKAGE_DIR / "media" / "dining-demo.png").read_bytes()
        assert by_slug["riverbend-off-leash-dog-park"].assets[0].asset_hash == sha256_of_bytes(park)
        assert by_slug["barkside-cafe"].assets[0].asset_hash == sha256_of_bytes(dining)

    def test_no_filesystem_path_in_dataset(self, tmp_path):
        from engines.website_generation.contracts.artifacts import canonical_artifact_json

        dataset, _, _, _ = _real_chain(tmp_path, with_media=True)
        text = canonical_artifact_json(dataset)
        assert "media/park-demo.png" not in text
        assert "launch_packages" not in text
        assert "\\\\" not in text


# --------------------------------------------------------------------------- #
# C. Generated HTML
# --------------------------------------------------------------------------- #

class TestGeneratedHtml:
    def _html(self, rendered, route):
        return next(p for p in rendered.page_details if p.route == route).html

    def test_configured_card_and_profile_render_img(self, tmp_path):
        dataset, rendered, _, _ = _real_chain(tmp_path, with_media=True)
        park_hash = next(
            l.assets[0].asset_hash for l in dataset.listings
            if l.slug == "riverbend-off-leash-dog-park"
        )
        expected_src = "/assets/media/%s.png" % park_hash
        category = self._html(rendered, "/pet-friendly-parks/")
        profile = self._html(rendered, "/pet-friendly-parks/riverbend-off-leash-dog-park/")
        assert 'src="%s"' % expected_src in category
        assert "ac-listing--card-image" in category
        assert 'src="%s"' % expected_src in profile
        assert "ac-profile--primary-image" in profile
        assert 'alt="Pet-friendly park travel illustration"' in category

    def test_imageless_listing_stays_text_only(self, tmp_path):
        _, rendered, _, _ = _real_chain(tmp_path, with_media=True)
        for route in ("/pet-friendly-hotels/", "/pet-friendly-hotels/%s/" % IMAGELESS_SLUG):
            html = self._html(rendered, route)
            assert "<img" not in html
            assert "card-image" not in html and "primary-image" not in html

    def test_exactly_four_img_tags_sitewide(self, tmp_path):
        # 2 imaged listings x (1 card + 1 profile) = 4; single-listing
        # categories have no related-listing repetition here.
        _, rendered, _, _ = _real_chain(tmp_path, with_media=True)
        total = sum(len(_IMG_TAG_RE.findall(p.html)) for p in rendered.page_details)
        assert total == 4


# --------------------------------------------------------------------------- #
# D. Bundle + materialization
# --------------------------------------------------------------------------- #

class TestBundle:
    def test_two_content_addressed_assets_materialized(self, tmp_path):
        _, _, bundle, cas = _real_chain(tmp_path, with_media=True)
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

    def test_no_duplicated_bytes(self, tmp_path):
        _, _, bundle, _ = _real_chain(tmp_path, with_media=True)
        hashes = [a.asset_hash for a in bundle.assets]
        assert len(hashes) == len(set(hashes))


# --------------------------------------------------------------------------- #
# E. Request safety
# --------------------------------------------------------------------------- #

class TestRequestSafety:
    def test_every_img_src_is_bundled_local(self, tmp_path):
        _, rendered, bundle, _ = _real_chain(tmp_path, with_media=True)
        for page in rendered.page_details:
            for img in _IMG_TAG_RE.findall(page.html):
                src = _SRC_RE.search(img).group(1)
                assert src.startswith("/assets/media/")
                assert not src.startswith(("http://", "https://", "//", "data:"))
                assert src.lstrip("/") in bundle.file_map


# --------------------------------------------------------------------------- #
# F. Determinism
# --------------------------------------------------------------------------- #

class TestDeterminism:
    def test_repeated_real_build_identical(self, tmp_path):
        _, rendered_a, bundle_a, _ = _real_chain(tmp_path / "a", with_media=True)
        _, rendered_b, bundle_b, _ = _real_chain(tmp_path / "b", with_media=True)
        assert bundle_a.bundle_hash == bundle_b.bundle_hash
        assert bundle_a.assets == bundle_b.assets
        for pa, pb in zip(rendered_a.page_details, rendered_b.page_details):
            assert pa.html == pb.html


# --------------------------------------------------------------------------- #
# G. Zero-image fallback
# --------------------------------------------------------------------------- #

class TestZeroImageFallback:
    def test_no_media_mapping_yields_zero_img(self, tmp_path):
        dataset, rendered, bundle, _ = _real_chain(tmp_path, with_media=False)
        assert all(l.assets == () for l in dataset.listings)
        assert bundle.assets == ()
        for page in rendered.page_details:
            assert "<img" not in page.html
