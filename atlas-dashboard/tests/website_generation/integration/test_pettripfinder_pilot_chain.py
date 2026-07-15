"""PILOT-PTF-1 end-to-end acceptance test.

Drives the full real engine chain (BrandEngine -> IA -> Component Engine ->
LayoutEngine -> Renderer -> SEOEngine -> AssemblyEngine -> QualityGateEngine
-> SiteBundleRepository) against the dedicated 12-listing + 3-editorial-page
PetTripFinder pilot fixture (``fixtures/pettripfinder_pilot_fixture.py``).

Distinct from ``test_publishable_wave1_chain.py`` (AES-WEB-002K.1's generic
directory proof): this test proves PetTripFinder-specific real content
(brand name, category taxonomy, trust pages) plus every PILOT-PTF-1
completion fix (hours/credentials optionality, home category tiles,
editorial/trust pages, review-count honesty, sponsored rel policy, sponsored
profile disclosure, claimed-class honesty).
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

from website_generation.fixtures.pettripfinder_pilot_fixture import (  # noqa: E402
    build_pettripfinder_pilot_fixture_inputs,
)

from engines.website_generation.assembly.assembly_engine import AssemblyEngine  # noqa: E402
from engines.website_generation.components.component_engine import ComponentEngine  # noqa: E402
from engines.website_generation.components.registry import build_default_registry  # noqa: E402
from engines.website_generation.contracts.artifacts import QualityReport, SiteBundle  # noqa: E402
from engines.website_generation.contracts.enums import GateSeverity  # noqa: E402
from engines.website_generation.gates.quality_gate_engine import QualityGateEngine  # noqa: E402
from engines.website_generation.layouts.layout_engine import LayoutEngine  # noqa: E402
from engines.website_generation.rendering.renderer import Renderer  # noqa: E402
from engines.website_generation.seo.seo_engine import SEOEngine  # noqa: E402
from repositories.site_bundle_repository import SiteBundleRepository  # noqa: E402

_HREF_RE = re.compile(r'href="([^"]*)"')


def _run_real_chain():
    fixture = build_pettripfinder_pilot_fixture_inputs()
    registry = build_default_registry()

    compilation = ComponentEngine().compile(
        fixture.site_architecture, fixture.content_package,
        listing_dataset=fixture.listing_dataset, brand_package=fixture.brand_package,
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
    bundle = AssemblyEngine().assemble(rendered, seo_package, fixture.brand_package)
    report = QualityGateEngine().evaluate(
        bundle, seo_package, compilation.content_package, fixture.site_architecture
    )
    return fixture, compilation, layout, rendered, seo_package, bundle, report


def _page_html(rendered, route):
    return next(p for p in rendered.page_details if p.route == route).html


def _body(html):
    return html.split("<body", 1)[-1]


class TestRouteGraph:
    def test_expected_total_route_count_is_19(self):
        fixture, *_ = _run_real_chain()
        assert len(fixture.site_architecture.pages) == 19

    def test_home_and_categories_exist(self):
        fixture, *_ = _run_real_chain()
        routes = {p.route for p in fixture.site_architecture.pages}
        assert "/" in routes
        for route in fixture.category_routes:
            assert route in routes

    def test_twelve_profile_routes_exist(self):
        fixture, *_ = _run_real_chain()
        assert len(fixture.profile_routes) == 12

    def test_editorial_routes_exist(self):
        fixture, *_ = _run_real_chain()
        routes = {p.route for p in fixture.site_architecture.pages}
        assert "/about/" in routes
        assert "/methodology/" in routes
        assert "/contact/" in routes


class TestBrand:
    def test_pettripfinder_visible_in_home_title(self):
        _, _, _, _, seo_package, *_ = _run_real_chain()
        home_entry = next(e for e in seo_package.entries if e.route == "/")
        assert "PetTripFinder" in home_entry.title


class TestHomePage:
    def test_non_empty_main(self):
        _, _, _, rendered, *_ = _run_real_chain()
        html = _page_html(rendered, "/")
        main_body = html.split("<main", 1)[1]
        assert "<a href=" in main_body

    def test_three_linked_category_tiles(self):
        fixture, _, _, rendered, *_ = _run_real_chain()
        html = _page_html(rendered, "/")
        main_body = html.split("<main", 1)[1].split("</main>", 1)[0]
        for route in fixture.category_routes:
            assert 'href="%s"' % route in main_body

    def test_hero_and_trust_content_present(self):
        _, _, _, rendered, *_ = _run_real_chain()
        html = _page_html(rendered, "/")
        assert "Travel anywhere with your pet" in html
        assert "sponsored placements" in html

    def test_header_excludes_editorial_footer_includes_it(self):
        _, _, _, rendered, *_ = _run_real_chain()
        html = _page_html(rendered, "/")
        header = html.split("<header", 1)[1].split("</header>", 1)[0]
        footer = html.split("<footer", 1)[1].split("</footer>", 1)[0]
        assert "/about/" not in header
        assert "/about/" in footer


class TestCategoryPages:
    def test_each_category_has_four_linked_cards(self):
        fixture, _, _, rendered, *_ = _run_real_chain()
        for route in fixture.category_routes:
            html = _page_html(rendered, route)
            main_body = html.split("<main", 1)[1]
            assert main_body.count('class="ac-listing') >= 4


class TestProfilePagesOptionality:
    def test_no_hours_listing_compiles_and_omits_hours_table(self):
        fixture, _, _, rendered, *_ = _run_real_chain()
        html = _page_html(rendered, fixture.no_hours_listing_route)
        assert "profile-hours-table" not in html

    def test_listing_with_hours_renders_hours_table(self):
        fixture, _, _, rendered, *_ = _run_real_chain()
        route = fixture.sponsored_listing_route
        html = _page_html(rendered, route)
        assert "profile-hours-table" in html
        assert "Monday" in html

    def test_no_cta_listing_has_no_cta_link(self):
        fixture, _, _, rendered, *_ = _run_real_chain()
        html = _page_html(rendered, fixture.no_cta_listing_route)
        assert "Visit website" not in html


class TestReviewCountHonesty:
    def test_unknown_review_count_not_rendered_as_zero(self):
        fixture, _, _, rendered, *_ = _run_real_chain()
        category_route = [r for r in fixture.category_routes if "restaurant" in r][0]
        html = _page_html(rendered, category_route)
        assert "(0 reviews)" not in html

    def test_barkside_cafe_rating_shown_without_review_count(self):
        fixture, _, _, rendered, *_ = _run_real_chain()
        category_route = [r for r in fixture.category_routes if "restaurant" in r][0]
        html = _page_html(rendered, category_route)
        assert "4.7" in html
        assert "4.7 (" not in html


class TestSponsorship:
    def test_sponsored_badge_only_on_sponsored_listing(self):
        fixture, _, _, rendered, *_ = _run_real_chain()
        category_route = [r for r in fixture.category_routes if "hotel" in r][0]
        html = _page_html(rendered, category_route)
        assert html.count("ac-listing--badge") == 1
        assert "Sponsored" in html

    def test_sponsored_cta_rel_is_sponsored_noopener(self):
        fixture, _, _, rendered, *_ = _run_real_chain()
        category_route = [r for r in fixture.category_routes if "hotel" in r][0]
        html = _page_html(rendered, category_route)
        assert 'rel="sponsored noopener"' in html

    def test_ordinary_external_cta_is_plain_noopener(self):
        fixture, _, _, rendered, *_ = _run_real_chain()
        category_route = [r for r in fixture.category_routes if "restaurant" in r][0]
        html = _page_html(rendered, category_route)
        # barkside-cafe is ORGANIC with a real CTA.
        assert 'rel="noopener"' in html

    def test_sponsored_profile_page_shows_disclosure(self):
        fixture, _, _, rendered, *_ = _run_real_chain()
        html = _page_html(rendered, fixture.sponsored_listing_route)
        assert "Sponsored placement" in html

    def test_organic_profile_page_has_no_disclosure(self):
        fixture, _, _, rendered, *_ = _run_real_chain()
        html = _page_html(rendered, fixture.no_hours_listing_route)
        assert "ac-profile ac-profile--disclosure" not in html

    def test_no_paid_reordering_dataset_order_preserved(self):
        fixture, _, _, rendered, *_ = _run_real_chain()
        category_route = [r for r in fixture.category_routes if "hotel" in r][0]
        html = _page_html(rendered, category_route)
        # sunset-bay-pet-friendly-inn (SPONSORED) is first in dataset order
        # for cat-hotels -- its badge/card must not be moved later.
        first_card_pos = html.find("ac-listing--card-standard")
        sponsored_pos = html.find("Sunset Bay Pet-Friendly Inn")
        assert 0 < sponsored_pos < html.find("Cedar Harbor Lodge")


class TestClaimHonesty:
    def test_no_profile_header_asserts_claimed(self):
        fixture, _, _, rendered, *_ = _run_real_chain()
        for route in fixture.profile_routes:
            html = _page_html(rendered, route)
            assert "header-business--claimed" not in html


class TestEditorialTrustPages:
    def test_about_page_renders_real_content(self):
        _, _, _, rendered, *_ = _run_real_chain()
        html = _page_html(rendered, "/about/")
        assert "About PetTripFinder" in html
        assert "directory of pet-friendly places" in html

    def test_methodology_page_renders_real_content(self):
        _, _, _, rendered, *_ = _run_real_chain()
        html = _page_html(rendered, "/methodology/")
        assert "Our Methodology" in html
        assert "sponsored" in html.lower()

    def test_contact_page_renders_real_content(self):
        _, _, _, rendered, *_ = _run_real_chain()
        html = _page_html(rendered, "/contact/")
        assert "Contact Us" in html

    def test_every_editorial_page_has_shell_and_main(self):
        _, _, _, rendered, *_ = _run_real_chain()
        for route in ("/about/", "/methodology/", "/contact/"):
            html = _page_html(rendered, route)
            assert html.count("<header") == 1
            assert html.count("<footer") == 1
            assert "<main" in html
            main_body = html.split("<main", 1)[1].split("</main>", 1)[0]
            assert "<p>" in main_body

    def test_editorial_pages_in_sitemap(self):
        _, _, _, _, seo_package, *_ = _run_real_chain()
        sitemap = set(seo_package.sitemap_routes)
        for route in ("/about/", "/methodology/", "/contact/"):
            assert any(route in s for s in sitemap)


class TestSEO:
    def test_base_url_used_for_canonicals(self):
        fixture, _, _, _, seo_package, *_ = _run_real_chain()
        home_entry = next(e for e in seo_package.entries if e.route == "/")
        assert home_entry.canonical_url == fixture.base_url + "/"

    def test_absolute_sitemap_urls(self):
        fixture, _, _, _, seo_package, *_ = _run_real_chain()
        assert all(url.startswith(fixture.base_url) for url in seo_package.sitemap_routes)


class TestQuality:
    def test_zero_blocking_gate_failures(self):
        *_, report = _run_real_chain()
        blocking = [g for g in report.gate_results if g.severity == GateSeverity.BLOCKING and not g.passed]
        assert blocking == [], blocking

    def test_no_placeholder_text_anywhere(self):
        _, _, _, rendered, *_ = _run_real_chain()
        for page in rendered.page_details:
            lowered = page.html.lower()
            for marker in ("lorem ipsum", "todo", "resolved ", "tbd", "fixme"):
                assert marker not in lowered, (page.route, marker)

    def test_no_broken_or_empty_href(self):
        _, _, _, rendered, *_ = _run_real_chain()
        for page in rendered.page_details:
            for href in _HREF_RE.findall(page.html):
                assert href.strip() != "", page.route

    def test_no_unsafe_urls(self):
        _, _, _, rendered, *_ = _run_real_chain()
        for page in rendered.page_details:
            for href in _HREF_RE.findall(page.html):
                assert not href.lower().startswith("javascript:"), page.route


class TestEndToEnd:
    def test_assembly_succeeds(self):
        *_, bundle, report = _run_real_chain()
        assert isinstance(bundle, SiteBundle)

    def test_quality_gates_execute(self):
        *_, report = _run_real_chain()
        assert isinstance(report, QualityReport)

    def test_repository_materializes(self, tmp_path):
        *_, bundle, _ = _run_real_chain()
        materialization = SiteBundleRepository().materialize(bundle, str(tmp_path / "out"))
        assert materialization.bundle_hash


class TestDeterminism:
    def test_two_runs_byte_identical_bundle_hash(self, tmp_path):
        *_, bundle_a, _ = _run_real_chain()
        *_, bundle_b, _ = _run_real_chain()
        mat_a = SiteBundleRepository().materialize(bundle_a, str(tmp_path / "a"))
        mat_b = SiteBundleRepository().materialize(bundle_b, str(tmp_path / "b"))
        assert mat_a.bundle_hash == mat_b.bundle_hash

    def test_two_materializations_byte_identical(self, tmp_path):
        *_, bundle, _ = _run_real_chain()
        mat_a = SiteBundleRepository().materialize(bundle, str(tmp_path / "a"))
        mat_b = SiteBundleRepository().materialize(bundle, str(tmp_path / "b"))
        assert mat_a.written_paths == mat_b.written_paths
        for rel in mat_a.written_paths:
            content_a = (tmp_path / "a" / rel).read_bytes()
            content_b = (tmp_path / "b" / rel).read_bytes()
            assert content_a == content_b, rel


class TestVisualSystemV2:
    """AES-WEB-002K.2 visual acceptance assertions -- the real generated
    CSS/HTML surfaces the masterplan identified as unstyled/underdesigned,
    proven against the real chain output rather than a synthetic fixture."""

    def test_listing_card_has_real_applied_styling(self):
        _, _, _, rendered, *_ = _run_real_chain()
        css = rendered.shared_css
        assert ".ac-listing--card-standard" in css
        rule = re.search(
            r"\.ac-listing--card-standard[^{]*\{([^}]*)\}", css
        )
        assert rule is not None
        body = rule.group(1)
        assert "border:" in body
        assert "border-radius:" in body
        assert "box-shadow:" in body

    def test_utility_bar_has_real_applied_styling(self):
        _, _, _, rendered, *_ = _run_real_chain()
        assert ".ac-nav--utility-bar{" in rendered.shared_css

    def test_meaningful_hover_rules_exist(self):
        _, _, _, rendered, *_ = _run_real_chain()
        hover_count = rendered.shared_css.count(":hover")
        assert hover_count >= 5, hover_count

    def test_hero_no_longer_uses_section_large_padding(self):
        _, _, _, rendered, *_ = _run_real_chain()
        rule = re.search(r"\.ac-hero\{([^}]*)\}", rendered.shared_css)
        assert rule is not None
        assert "--spacing-section-large" not in rule.group(1)

    def test_editorial_content_has_readable_max_width(self):
        _, _, _, rendered, *_ = _run_real_chain()
        assert "max-width:70ch" in rendered.shared_css

    def test_two_responsive_breakpoint_tiers_exist(self):
        _, _, _, rendered, *_ = _run_real_chain()
        css = rendered.shared_css
        assert "@media (max-width: 1024px){" in css
        assert "@media (max-width: 640px){" in css

    def test_cta_action_rules_exist(self):
        _, _, _, rendered, *_ = _run_real_chain()
        css = rendered.shared_css
        assert ".ac-cta--action{" in css
        assert ".ac-cta--action:hover{" in css
        assert ".ac-cta--action:focus-visible{" in css

    def test_sponsored_badge_rules_exist(self):
        _, _, _, rendered, *_ = _run_real_chain()
        assert ".ac-listing--badge{" in rendered.shared_css

    def test_hero_cta_exists_and_points_to_main(self):
        _, _, _, rendered, *_ = _run_real_chain()
        html = _page_html(rendered, "/")
        assert 'href="#main"' in html
        assert 'class="ac-cta ac-cta--action" href="#main"' in html

    def test_cta_anchors_carry_shared_action_class(self):
        fixture, _, _, rendered, *_ = _run_real_chain()
        html = _page_html(rendered, fixture.sponsored_listing_route)
        assert 'class="ac-cta ac-cta--action"' in html

    def test_no_empty_map_directions_section(self):
        fixture, _, _, rendered, *_ = _run_real_chain()
        for route in fixture.profile_routes:
            html = _page_html(rendered, route)
            assert "<section></section>" not in html
            assert "profile-map-directions" not in html

    def test_no_broken_class_hooks(self):
        _, _, _, rendered, *_ = _run_real_chain()
        for page in rendered.page_details:
            assert 'class=""' not in page.html


class TestCommercialStrategyRegression:
    """AES-WEB-002L.1 §H: proves the real PetTripFinder BusinessSpec
    classifies DIRECTORY (never LEAD_GENERATION merely because
    ``monetization_model="affiliate_booking_links"`` involves money), and
    that the default (omitted) ``commercial_strategy`` argument the real
    chain's own ``_run_real_chain()`` already uses (unchanged by this
    delivery) reproduces exactly that classification end-to-end -- the
    same real PetTripFinder pilot fixture this whole file already proves
    K.2's visible output against, now also proven commercial-strategy-
    correct."""

    def test_pettripfinder_spec_classifies_directory(self):
        from engines.website_generation.components.commercial_strategy import (
            classify_commercial_strategy,
        )
        from engines.website_generation.constants.commercial_strategy import (
            STRATEGY_DIRECTORY,
        )
        fixture = build_pettripfinder_pilot_fixture_inputs()
        assert classify_commercial_strategy(fixture.business_spec) == STRATEGY_DIRECTORY

    def test_default_compile_records_directory_strategy_provenance(self):
        _, compilation, *_ = _run_real_chain()
        source_hashes = compilation.component_manifest.source_hashes
        assert source_hashes["commercial_strategy"] == "directory"
        assert source_hashes["commercial_strategy_version"] == "1.0.0"

    def test_hero_cta_still_present_and_unchanged_under_real_chain(self):
        # The K.2 hero CTA byte-equivalence tests above
        # (test_hero_cta_exists_and_points_to_main) already prove the
        # visible markup; this test names *why* it still holds under
        # AES-WEB-002L.1: the real chain's DIRECTORY classification
        # resolves PAGE_COMMERCIAL_DEFAULTS[("directory", "home")], the
        # exact table entry K.2's former hardcoded module constants were
        # migrated into verbatim.
        from engines.website_generation.constants.commercial_strategy import (
            PAGE_COMMERCIAL_DEFAULTS,
            STRATEGY_DIRECTORY,
        )
        defaults = PAGE_COMMERCIAL_DEFAULTS[(STRATEGY_DIRECTORY, "home")]
        assert defaults["primary_cta_label"] == "Browse the directory"
        assert defaults["primary_cta_href"] == "#main"
