"""Visible listing media end-to-end tests (AES-WEB-002M.2).

Drives the real engine chain (ComponentEngine -> LayoutEngine -> Renderer
-> SEOEngine -> AssemblyEngine -> SiteBundleRepository, with real CAS
bytes) over the real PetTripFinder pilot fixture with deterministic
synthetic images injected into chosen listings -- proving the full mission
flow:

    image bytes -> CAS -> ListingRecord.assets (HERO_IMAGE)
      -> Component Engine render-data resolution
      -> listing-card <img> + profile primary <img>
      -> Assembly asset map -> materialized, hash-verified file
      -> every HTML src resolves to a bundled local asset

Mission matrix sections: A (ImageData), B (selection), C (alt text),
D (card), E (profile), F (mixed collection), G (deduplication), H (route
depth), J (external-request ban), M (end-to-end), N (determinism).
Ingestion (§I) lives in ``tests/pettripfinder/test_media_ingestion.py``;
the zero-image PetTripFinder regression (§L) stays in
``test_pettripfinder_pilot_chain.py``.
"""

from __future__ import annotations

import pathlib
import re
import sys

import pytest

_REPO_ROOT = pathlib.Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))
_TESTS_ROOT = _REPO_ROOT / "tests"
if str(_TESTS_ROOT) not in sys.path:
    sys.path.insert(0, str(_TESTS_ROOT))

from website_generation.fixtures.media_fixtures import make_test_jpeg, make_test_png  # noqa: E402
from website_generation.fixtures.pettripfinder_pilot_fixture import (  # noqa: E402
    build_pettripfinder_pilot_fixture_inputs,
)

from engines.website_generation.assembly.assembly_engine import AssemblyEngine  # noqa: E402
from engines.website_generation.components.component_engine import ComponentEngine  # noqa: E402
from engines.website_generation.components.registry import build_default_registry  # noqa: E402
from engines.website_generation.contracts.artifacts import (  # noqa: E402
    ListingAssetRef,
    sha256_of_bytes,
)
from engines.website_generation.contracts.enums import AssetRole  # noqa: E402
from engines.website_generation.contracts.render_data import ImageData  # noqa: E402
from engines.website_generation.layouts.layout_engine import LayoutEngine  # noqa: E402
from engines.website_generation.rendering.renderer import Renderer  # noqa: E402
from engines.website_generation.seo.seo_engine import SEOEngine  # noqa: E402
from repositories.site_bundle_repository import SiteBundleRepository  # noqa: E402

# Deterministic fixture images (see fixtures/media_fixtures.py).
PNG_BYTES = make_test_png(width=30, height=20)
PNG_HASH = sha256_of_bytes(PNG_BYTES)
JPEG_BYTES = make_test_jpeg(width=40, height=30)
JPEG_HASH = sha256_of_bytes(JPEG_BYTES)

ASSET_BYTES = {PNG_HASH: PNG_BYTES, JPEG_HASH: JPEG_BYTES}

_IMG_TAG_RE = re.compile(r"<img [^>]*>")
_SRC_RE = re.compile(r'src="([^"]*)"')


def _hero_ref(asset_hash=PNG_HASH, mime="image/png", **overrides) -> ListingAssetRef:
    fields = dict(
        role=AssetRole.HERO_IMAGE,
        asset_hash=asset_hash,
        alt_text="",
        width=30,
        height=20,
        mime_type=mime,
        source_kind="OPERATOR_UPLOAD",
        bundle_allowed=True,
    )
    fields.update(overrides)
    return ListingAssetRef(**fields)


def _with_assets(dataset, assets_by_listing_id):
    """A copy of the pilot dataset with assets injected into the named
    listings -- slugs/routes untouched, so the fixture's SiteArchitecture
    and ContentPackage stay valid for the modified dataset."""
    listings = tuple(
        record.copy(update={"assets": tuple(assets_by_listing_id[record.listing_id])})
        if record.listing_id in assets_by_listing_id
        else record
        for record in dataset.listings
    )
    return dataset.copy(update={"listings": listings})


def _run_chain(assets_by_listing_id):
    """The real chain over the pilot fixture with injected media."""
    fixture = build_pettripfinder_pilot_fixture_inputs()
    dataset = _with_assets(fixture.listing_dataset, assets_by_listing_id)
    registry = build_default_registry()
    compilation = ComponentEngine().compile(
        fixture.site_architecture, fixture.content_package,
        listing_dataset=dataset, brand_package=fixture.brand_package,
        registry=registry,
    )
    layout = LayoutEngine(registry).compose(compilation.component_manifest, fixture.brand_package)
    rendered = Renderer(registry).render(
        layout, compilation.component_manifest, compilation.content_package,
        fixture.brand_package, render_data=compilation.render_data,
    )
    seo_package = SEOEngine().compile(
        fixture.site_architecture, compilation.content_package, fixture.business_spec,
        base_url=fixture.base_url,
    )
    bundle = AssemblyEngine().assemble(
        rendered, seo_package, fixture.brand_package, listing_dataset=dataset,
    )
    return fixture, compilation, rendered, bundle


def _page_html(rendered, route):
    return next(p for p in rendered.page_details if p.route == route).html


def _first_hotel_ids(fixture, count):
    """The first N hotel-category listing ids in profile-route order --
    deterministic targets for asset injection."""
    ids = []
    for route in fixture.profile_routes:
        if route.startswith("/pet-friendly-hotels/"):
            ids.append(route.rstrip("/").rsplit("/", 1)[-1])
    return ids[:count]


# --------------------------------------------------------------------------- #
# A. ImageData contract
# --------------------------------------------------------------------------- #

class TestImageDataContract:
    def test_required_fields_and_defaults(self):
        image = ImageData(src="/assets/media/a.png", alt="A")
        assert image.width == 0 and image.height == 0

    def test_immutable(self):
        image = ImageData(src="/assets/media/a.png", alt="A")
        with pytest.raises(TypeError):
            image.src = "/other"  # type: ignore[misc]

    def test_optional_on_render_data(self):
        from engines.website_generation.contracts.render_data import (
            ComponentRenderData,
            ListingCardData,
        )

        assert ComponentRenderData().image is None
        assert ListingCardData(listing_id="x", name="X", profile_href="/x/").image is None


# --------------------------------------------------------------------------- #
# B. Asset selection (resolver unit tests through the public class)
# --------------------------------------------------------------------------- #

class TestAssetSelection:
    def _listing(self, assets):
        from engines.website_generation.contracts.artifacts import ListingRecord

        return ListingRecord(
            listing_id="lst", business_name="Lodge", slug="lst",
            category_id="c", assets=tuple(assets),
        )

    def test_first_hero_image_in_tuple_order_wins(self):
        first = _hero_ref(asset_hash=JPEG_HASH, mime="image/jpeg", alt_text="first")
        second = _hero_ref(alt_text="second")
        image = ComponentEngine._resolve_primary_image(self._listing([first, second]))
        assert image.alt == "first"
        assert image.src.endswith(".jpg")

    def test_declared_order_not_hash_order(self):
        # Reverse the hash ordering to prove no sorting happens: whichever
        # ref is declared first wins, regardless of hash comparison.
        low, high = sorted([PNG_HASH, JPEG_HASH])
        first = _hero_ref(asset_hash=high, mime="image/png", alt_text="declared-first")
        second = _hero_ref(asset_hash=low, mime="image/png", alt_text="declared-second")
        image = ComponentEngine._resolve_primary_image(self._listing([first, second]))
        assert image.alt == "declared-first"

    def test_unauthorized_first_authorized_second(self):
        blocked = _hero_ref(bundle_allowed=False, alt_text="blocked")
        allowed = _hero_ref(asset_hash=JPEG_HASH, mime="image/jpeg", alt_text="allowed")
        image = ComponentEngine._resolve_primary_image(self._listing([blocked, allowed]))
        assert image.alt == "allowed"

    def test_gallery_role_never_selected(self):
        gallery = _hero_ref(role=AssetRole.GALLERY_IMAGE)
        assert ComponentEngine._resolve_primary_image(self._listing([gallery])) is None

    def test_unsupported_mime_omitted(self):
        tiff = _hero_ref(mime="image/tiff")
        assert ComponentEngine._resolve_primary_image(self._listing([tiff])) is None

    def test_malformed_hash_omitted(self):
        bad = _hero_ref(asset_hash="NOT-A-HASH")
        assert ComponentEngine._resolve_primary_image(self._listing([bad])) is None

    def test_no_assets_is_none(self):
        assert ComponentEngine._resolve_primary_image(self._listing([])) is None


# --------------------------------------------------------------------------- #
# C. Alt text
# --------------------------------------------------------------------------- #

class TestAltText:
    def _resolve(self, alt_text):
        from engines.website_generation.contracts.artifacts import ListingRecord

        listing = ListingRecord(
            listing_id="lst", business_name="Lakeview Lodge & Suites", slug="lst",
            category_id="c", assets=(_hero_ref(alt_text=alt_text),),
        )
        return ComponentEngine._resolve_primary_image(listing)

    def test_supplied_alt_wins(self):
        assert self._resolve("Front porch at dusk").alt == "Front porch at dusk"

    def test_blank_alt_falls_back_to_business_name(self):
        assert self._resolve("").alt == "Lakeview Lodge & Suites"

    def test_whitespace_only_alt_falls_back(self):
        assert self._resolve("   \t ").alt == "Lakeview Lodge & Suites"

    def test_special_characters_escaped_in_html(self):
        fixture = build_pettripfinder_pilot_fixture_inputs()
        target = _first_hotel_ids(fixture, 1)[0]
        _, _, rendered, _ = _run_chain(
            {target: [_hero_ref(alt_text='B&B "Best" <Lodge>')]}
        )
        route = next(r for r in fixture.profile_routes if r.endswith("/%s/" % target))
        html = _page_html(rendered, route)
        assert 'alt="B&amp;B &quot;Best&quot; &lt;Lodge&gt;"' in html
        assert '<Lodge>' not in html


# --------------------------------------------------------------------------- #
# D/E. Card + profile rendering (real chain)
# --------------------------------------------------------------------------- #

class TestCardAndProfileRendering:
    def test_card_renders_real_img(self):
        fixture = build_pettripfinder_pilot_fixture_inputs()
        target = _first_hotel_ids(fixture, 1)[0]
        _, _, rendered, _ = _run_chain({target: [_hero_ref(alt_text="Lodge front")]})
        category_html = _page_html(rendered, "/pet-friendly-hotels/")
        (img,) = _IMG_TAG_RE.findall(category_html)
        assert 'class="ac-listing ac-listing--card-image"' in img
        assert 'src="/assets/media/%s.png"' % PNG_HASH in img
        assert 'alt="Lodge front"' in img
        assert 'loading="lazy"' in img
        assert 'decoding="async"' in img
        assert 'width="30"' in img and 'height="20"' in img

    def test_unknown_dimensions_omit_attributes(self):
        fixture = build_pettripfinder_pilot_fixture_inputs()
        target = _first_hotel_ids(fixture, 1)[0]
        _, _, rendered, _ = _run_chain(
            {target: [_hero_ref(width=0, height=0, alt_text="No dims")]}
        )
        category_html = _page_html(rendered, "/pet-friendly-hotels/")
        (img,) = _IMG_TAG_RE.findall(category_html)
        assert "width=" not in img and "height=" not in img

    def test_profile_renders_same_asset(self):
        fixture = build_pettripfinder_pilot_fixture_inputs()
        target = _first_hotel_ids(fixture, 1)[0]
        _, _, rendered, _ = _run_chain({target: [_hero_ref()]})
        route = next(r for r in fixture.profile_routes if r.endswith("/%s/" % target))
        profile_html = _page_html(rendered, route)
        imgs = _IMG_TAG_RE.findall(profile_html)
        (img,) = imgs
        assert 'class="ac-profile ac-profile--primary-image"' in img
        assert 'src="/assets/media/%s.png"' % PNG_HASH in img
        # h1 (the section's first content) still precedes the image.
        header = profile_html.split('data-atlas-c="profile-header-business"', 1)[1]
        assert header.index("<h1>") < header.index("<img ")

    def test_no_image_listing_has_no_img_and_no_frame(self):
        _, _, rendered, _ = _run_chain({})
        for page in rendered.page_details:
            assert "<img" not in page.html
            assert "ac-listing--card-image" not in page.html
            assert "ac-profile--primary-image" not in page.html


# --------------------------------------------------------------------------- #
# F. Mixed collection
# --------------------------------------------------------------------------- #

class TestMixedCollection:
    def test_mixed_image_and_text_cards_preserve_order(self):
        fixture = build_pettripfinder_pilot_fixture_inputs()
        hotels = _first_hotel_ids(fixture, 4)
        assert len(hotels) == 4
        # Give images to hotels 0 and 2 -- interleaved with text-only cards.
        _, _, rendered, _ = _run_chain({
            hotels[0]: [_hero_ref()],
            hotels[2]: [_hero_ref(asset_hash=JPEG_HASH, mime="image/jpeg")],
        })
        html = _page_html(rendered, "/pet-friendly-hotels/")
        # Exactly two image cards among the four.
        assert len(_IMG_TAG_RE.findall(html)) == 2

        # Card order is the J.20 repetition ordering (sponsored-first, then
        # dataset order) and must be identical to a zero-image run: images
        # never reorder, duplicate, or drop cards.
        _, _, rendered_plain, _ = _run_chain({})
        href_pattern = r'<h2><a href="(/pet-friendly-hotels/[^"]+)"'
        hrefs = re.findall(href_pattern, html)
        assert hrefs == re.findall(href_pattern, _page_html(rendered_plain, "/pet-friendly-hotels/"))
        assert len(hrefs) == 4
        assert {h.rstrip("/").rsplit("/", 1)[-1] for h in hrefs} == set(hotels)

        # The image sits inside exactly the two targeted listings' cards.
        with_images = {hotels[0], hotels[2]}
        for article in html.split("<article")[1:]:
            (href,) = re.findall(href_pattern, article) or [None]
            if href is None:
                continue
            listing_id = href.rstrip("/").rsplit("/", 1)[-1]
            assert ("<img " in article) == (listing_id in with_images), listing_id


# --------------------------------------------------------------------------- #
# G. Same-asset deduplication
# --------------------------------------------------------------------------- #

class TestDeduplication:
    def test_one_hash_many_references_one_bundle_asset_one_file(self, tmp_path):
        fixture = build_pettripfinder_pilot_fixture_inputs()
        hotels = _first_hotel_ids(fixture, 2)
        # The same PNG on two listings. It renders on the category page (2
        # cards), on each listing's own profile (2 primary images), and --
        # because the business-profile recipe's related_listings slot
        # repeats sibling-category cards (J.20) -- on the hotel profiles'
        # related-listing cards too (the 2 image listings appear as related
        # cards on the other hotels' profiles: 3+3 minus their own pages'
        # self-exclusions = 6). Many references, one binary.
        _, _, rendered, bundle = _run_chain({
            hotels[0]: [_hero_ref()], hotels[1]: [_hero_ref()],
        })
        (asset,) = bundle.assets
        assert asset.asset_hash == PNG_HASH

        references = sum(
            page.html.count('src="/assets/media/%s.png"' % PNG_HASH)
            for page in rendered.page_details
        )
        assert references == 10  # 2 category cards + 2 profile primaries + 6 related cards

        destination = tmp_path / "site"
        SiteBundleRepository().materialize(bundle, destination, asset_bytes=ASSET_BYTES)
        media_files = list((destination / "assets" / "media").iterdir())
        assert len(media_files) == 1


# --------------------------------------------------------------------------- #
# H/J. Route depth + external-request ban
# --------------------------------------------------------------------------- #

class TestSrcSafety:
    def test_src_identical_and_resolvable_from_every_route_depth(self):
        fixture = build_pettripfinder_pilot_fixture_inputs()
        target = _first_hotel_ids(fixture, 1)[0]
        _, _, rendered, bundle = _run_chain({target: [_hero_ref()]})
        srcs = set()
        for page in rendered.page_details:
            for img in _IMG_TAG_RE.findall(page.html):
                srcs.add(_SRC_RE.search(img).group(1))
        (src,) = srcs  # category page (depth 1) and profile page (depth 2)
        assert src == "/assets/media/%s.png" % PNG_HASH
        # Root-relative: resolves to the bundled file from any page depth.
        assert src.lstrip("/") in bundle.file_map
        assert "\\" not in src
        assert not re.match(r"^[A-Za-z]:", src)

    def test_no_external_or_data_srcs_anywhere(self):
        fixture = build_pettripfinder_pilot_fixture_inputs()
        target = _first_hotel_ids(fixture, 1)[0]
        _, _, rendered, _ = _run_chain({target: [_hero_ref()]})
        for page in rendered.page_details:
            for img in _IMG_TAG_RE.findall(page.html):
                src = _SRC_RE.search(img).group(1)
                assert not src.startswith("http://")
                assert not src.startswith("https://")
                assert not src.startswith("//")
                assert not src.startswith("data:")
                assert src.startswith("/assets/media/")


# --------------------------------------------------------------------------- #
# M/N. End-to-end proof + determinism
# --------------------------------------------------------------------------- #

class TestEndToEnd:
    def test_full_flow_image_reaches_browser_visible_file(self, tmp_path):
        from repositories.artifact_store_repository import ArtifactStoreRepository

        # 1. Operator bytes enter the CAS (the M.1 raw-bytes object class).
        store = ArtifactStoreRepository(tmp_path / "cas")
        assert store.put_bytes(PNG_BYTES) == PNG_HASH

        # 2-5. Dataset ref -> render data -> HTML -> bundle asset map.
        fixture = build_pettripfinder_pilot_fixture_inputs()
        target = _first_hotel_ids(fixture, 1)[0]
        _, _, rendered, bundle = _run_chain({target: [_hero_ref()]})
        (asset,) = bundle.assets

        # 6. Materialize with CAS-composed bytes (the M.1 mapping seam).
        destination = tmp_path / "site"
        SiteBundleRepository().materialize(
            bundle, destination,
            asset_bytes={asset.asset_hash: store.get_bytes(asset.asset_hash)},
        )

        # 7. The browser-visible file exists, hash-verified, and every HTML
        # src reference corresponds to it.
        written = destination.joinpath(*asset.path.split("/"))
        assert sha256_of_bytes(written.read_bytes()) == PNG_HASH
        category_html = (destination / "pet-friendly-hotels" / "index.html").read_text(encoding="utf-8")
        assert 'src="/%s"' % asset.path in category_html

    def test_repeated_build_is_deterministic(self):
        fixture = build_pettripfinder_pilot_fixture_inputs()
        target = _first_hotel_ids(fixture, 1)[0]
        assets = {target: [_hero_ref(alt_text="Stable")]}
        _, _, rendered_a, bundle_a = _run_chain(assets)
        _, _, rendered_b, bundle_b = _run_chain(assets)
        assert bundle_a.bundle_hash == bundle_b.bundle_hash
        assert bundle_a.assets == bundle_b.assets
        for pa, pb in zip(rendered_a.page_details, rendered_b.page_details):
            assert pa.html == pb.html
