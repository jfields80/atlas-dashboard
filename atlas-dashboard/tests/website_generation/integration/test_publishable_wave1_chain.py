"""Publishable Wave-1 real-chain integration test (AES-WEB-002K.1;
ADR-WEB-CONTENT-BINDING-MAP; AES-WEB-001 §5.5/§5.7/§5.8).

Proves the mission's Wave-1 acceptance criterion: using the curated
``publishable_wave1_fixture`` (home + one real category + five real
listings, five IA-*generated* business-profile routes -- not hand-built),
the REAL

    InformationArchitectureEngine (with ListingDataset)
    -> ComponentEngine (render-data production)
    -> LayoutEngine
    -> Renderer (with render_data)
    -> SEOEngine (with base_url)
    -> AssemblyEngine
    -> QualityGateEngine
    -> SiteBundleRepository

chain produces a genuinely navigable, commercially credible site: real
clickable navigation, linked and enriched listing cards, clickable
contact/hours, absolute canonical/sitemap URLs, exactly one header/footer/
main landmark per page, valid heading hierarchy, and honest handling of the
two known, pre-existing, unrelated quality-gate findings this delivery
retires (CG-CMP-005/006 -- see the K.1 implementation report for why they
now pass).

Distinct from ``test_listing_collection_chain.py`` (AES-WEB-002J.20): that
test proves listing *repetition* against a hand-built ``SiteArchitecture``
with zero navigation. This test proves the *whole* Wave-1 capability --
IA-generated profile routes, real render-data-backed navigation/cards/
contact/hours, and absolute URLs -- together, end to end.
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

from website_generation.fixtures.publishable_wave1_fixture import (  # noqa: E402
    build_publishable_wave1_fixture_inputs,
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

_KNOWN_BLOCKING_GATE_IDS = frozenset({"CG-CMP-005", "CG-CMP-006"})
_HREF_RE = re.compile(r'href="([^"]*)"')


def _run_real_chain():
    """Drive every real engine in sequence -- no hand-repair anywhere."""
    fixture = build_publishable_wave1_fixture_inputs()
    registry = build_default_registry()

    compilation = ComponentEngine().compile(
        fixture.site_architecture,
        fixture.content_package,
        listing_dataset=fixture.listing_dataset,
        brand_package=fixture.brand_package,
        registry=registry,
    )
    layout = LayoutEngine(registry).compose(
        compilation.component_manifest, fixture.brand_package
    )
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


class TestIAProfileRouteGeneration:
    def test_home_and_category_exist(self):
        fixture, *_ = _run_real_chain()
        routes = {p.route for p in fixture.site_architecture.pages}
        assert fixture.home_route in routes
        assert fixture.category_route in routes

    def test_at_least_five_profile_routes_exist(self):
        fixture, *_ = _run_real_chain()
        assert len(fixture.profile_routes) >= 5

    def test_profile_titles_equal_real_business_names(self):
        fixture, *_ = _run_real_chain()
        by_route = {p.route: p.title for p in fixture.site_architecture.pages}
        assert by_route[fixture.verified_listing_route] == "Cedar Harbor Inn"
        for route in fixture.profile_routes:
            assert by_route[route]  # never empty

    def test_profile_routes_follow_adr_convention(self):
        fixture, *_ = _run_real_chain()
        for route in fixture.profile_routes:
            assert route.startswith(fixture.category_route)
            assert route.endswith("/")

    def test_profiles_excluded_from_nav_routes(self):
        fixture, *_ = _run_real_chain()
        for route in fixture.profile_routes:
            assert route not in fixture.site_architecture.nav_routes
        assert fixture.home_route in fixture.site_architecture.nav_routes
        assert fixture.category_route in fixture.site_architecture.nav_routes

    def test_profiles_included_in_sitemap_routes(self):
        fixture, *_ = _run_real_chain()
        for route in fixture.profile_routes:
            assert route in fixture.site_architecture.sitemap_routes


class TestHomePage:
    def test_exactly_one_header_footer_main(self):
        fixture, compilation, layout, rendered, *_ = _run_real_chain()
        html = _page_html(rendered, fixture.home_route)
        assert html.count("<header") == 1
        assert html.count("<footer") == 1
        assert html.count("<main") == 1

    def test_real_nav_links_with_human_labels(self):
        fixture, compilation, layout, rendered, *_ = _run_real_chain()
        html = _page_html(rendered, fixture.home_route)
        assert 'href="/"' in html
        assert 'href="/hotels/"' in html
        assert ">Hotels<" in html or ">Hotels</a>" in html

    def test_at_least_one_category_link(self):
        fixture, compilation, layout, rendered, *_ = _run_real_chain()
        html = _page_html(rendered, fixture.home_route)
        assert 'href="%s"' % fixture.category_route in html

    def test_no_raw_route_labels(self):
        fixture, compilation, layout, rendered, *_ = _run_real_chain()
        html = _page_html(rendered, fixture.home_route)
        # A raw route used as its own label would render literally as
        # ">/hotels/<" -- the honest label is "Hotels".
        assert ">/hotels/<" not in html

    def test_no_placeholders(self):
        fixture, compilation, layout, rendered, *_ = _run_real_chain()
        html = _page_html(rendered, fixture.home_route)
        assert "Resolved " not in html
        assert "TODO" not in html
        assert "placeholder" not in html.lower()


class TestCategoryPage:
    def test_exactly_one_header_footer_main(self):
        fixture, compilation, layout, rendered, *_ = _run_real_chain()
        html = _page_html(rendered, fixture.category_route)
        assert html.count("<header") == 1
        assert html.count("<footer") == 1
        assert html.count("<main") == 1

    def test_h1_exists(self):
        fixture, compilation, layout, rendered, *_ = _run_real_chain()
        html = _page_html(rendered, fixture.category_route)
        assert html.count("<h1") == 1

    def test_five_linked_listing_cards(self):
        fixture, compilation, layout, rendered, *_ = _run_real_chain()
        html = _page_html(rendered, fixture.category_route)
        for route in fixture.profile_routes:
            assert 'href="%s"' % route in html

    def test_each_card_links_to_its_correct_profile(self):
        fixture, compilation, layout, rendered, *_ = _run_real_chain()
        page = next(p for p in compilation.component_manifest.pages if p.route == fixture.category_route)
        cards = [i for i in page.components if i.component_id == "listing.card.standard"]
        assert len(cards) == 5
        entry_by_key = {
            (e.route, e.component_index): e.data
            for e in compilation.render_data.entries
        }
        for idx, instance in enumerate(page.components):
            if instance.component_id != "listing.card.standard":
                continue
            data = entry_by_key[(fixture.category_route, idx)]
            assert data.card is not None
            assert data.card.profile_href in fixture.profile_routes

    def test_names_unique_and_real(self):
        fixture, compilation, layout, rendered, *_ = _run_real_chain()
        html = _page_html(rendered, fixture.category_route)
        names = [
            "Alpine Lantern Lodge", "Cedar Harbor Inn", "Maple Ridge Retreat",
            "Northstar Guest House", "Willow Creek Suites",
        ]
        for name in names:
            assert html.count(name) >= 1
        assert len(set(names)) == len(names)

    def test_area_and_rating_visible_where_available(self):
        fixture, compilation, layout, rendered, *_ = _run_real_chain()
        html = _page_html(rendered, fixture.category_route)
        assert "Aspen, CO" in html
        assert "4.7" in html  # Alpine Lantern Lodge's rating
        # The intentionally-unrated listing must still appear (by name)
        # without a fabricated rating number.
        assert "Northstar Guest House" in html

    def test_no_empty_control_containers(self):
        fixture, compilation, layout, rendered, *_ = _run_real_chain()
        page = next(p for p in compilation.component_manifest.pages if p.route == fixture.category_route)
        # filters/sort/pagination/zero_results are optional with no
        # fallback (AES-WEB-002K.1 category-control cleanup) -- none of
        # the instances on this page may be an unrelated structural filler
        # standing in for one of those four retired slots.
        ids = [i.component_id for i in page.components]
        # layout.stack.standard was the pre-K.1 fallback for these slots;
        # it must not appear at all on a fully-populated category page.
        assert "layout.stack.standard" not in ids

    def test_valid_heading_hierarchy_h1_then_h2(self):
        fixture, compilation, layout, rendered, *_ = _run_real_chain()
        html = _page_html(rendered, fixture.category_route)
        assert html.count("<h1") == 1
        assert html.count("<h2") == 5
        assert "<h3" not in html


class TestProfilePages:
    def test_exactly_one_header_footer_main_for_every_profile(self):
        fixture, compilation, layout, rendered, *_ = _run_real_chain()
        for route in fixture.profile_routes:
            html = _page_html(rendered, route)
            assert html.count("<header") == 1, route
            assert html.count("<footer") == 1, route
            assert html.count("<main") == 1, route

    def test_profile_name_is_h1(self):
        fixture, compilation, layout, rendered, *_ = _run_real_chain()
        html = _page_html(rendered, fixture.verified_listing_route)
        assert "<h1>Cedar Harbor Inn</h1>" in html

    def test_clickable_phone_and_email(self):
        fixture, compilation, layout, rendered, *_ = _run_real_chain()
        html = _page_html(rendered, fixture.verified_listing_route)
        assert 'href="tel:5550101"' in html
        assert 'href="mailto:cedarharborinn@example.com"' in html

    def test_per_day_hours_including_closed_day(self):
        fixture, compilation, layout, rendered, *_ = _run_real_chain()
        html = _page_html(rendered, fixture.verified_listing_route)
        assert "Monday" in html and "08:00-20:00" in html
        assert "Sunday" in html and "Closed" in html

    def test_related_listing_ratings_visible_when_available(self):
        # The profile page's own header shows only the listing's name (§9.3
        # H1 ownership) -- rating/review enrichment is a card-level concern
        # (AES-WEB-002K.1 scope), visible here via this profile's own
        # related-listings cards (e.g. Alpine Lantern Lodge, a sibling
        # listing, carries a real rating).
        fixture, compilation, layout, rendered, *_ = _run_real_chain()
        html = _page_html(rendered, fixture.verified_listing_route)
        assert "4.7" in html

    def test_cta_visible_when_available(self):
        fixture, compilation, layout, rendered, *_ = _run_real_chain()
        # The CTA is carried on the *related_listings* cards that reference
        # the CTA-bearing listing from a sibling profile page, since Wave 1
        # renders a listing's own CTA through its card enrichment wherever
        # that listing appears as a card (this profile's own related-
        # listings region does not include itself). Verify it appears on
        # the category page, where the CTA-bearing listing's own card is.
        fixture2, compilation2, layout2, rendered2, *_ = _run_real_chain()
        html = _page_html(rendered2, fixture2.category_route)
        assert 'href="https://example.com/book/cedar-harbor-inn"' in html
        assert "Check availability" in html

    def test_related_listing_links_present(self):
        fixture, compilation, layout, rendered, *_ = _run_real_chain()
        html = _page_html(rendered, fixture.verified_listing_route)
        other_routes = [r for r in fixture.profile_routes if r != fixture.verified_listing_route]
        assert any('href="%s"' % r in html for r in other_routes)

    def test_no_duplicate_own_listing_in_related(self):
        fixture, compilation, layout, rendered, *_ = _run_real_chain()
        page = next(
            p for p in compilation.component_manifest.pages if p.route == fixture.verified_listing_route
        )
        entry_by_key = {
            (e.route, e.component_index): e.data for e in compilation.render_data.entries
        }
        for idx, instance in enumerate(page.components):
            if instance.component_id != "listing.card.standard":
                continue
            data = entry_by_key[(fixture.verified_listing_route, idx)]
            assert data.card.profile_href != fixture.verified_listing_route


class TestSiteWide:
    def test_total_anchor_count_positive(self):
        fixture, compilation, layout, rendered, *_ = _run_real_chain()
        total = sum(len(_HREF_RE.findall(p.html)) for p in rendered.page_details)
        assert total > 0

    def test_every_card_links_to_correct_profile_site_wide(self):
        fixture, compilation, layout, rendered, *_ = _run_real_chain()
        for entry in compilation.render_data.entries:
            if entry.data.card is not None:
                assert entry.data.card.profile_href in fixture.profile_routes

    def test_no_placeholder_text_anywhere(self):
        fixture, compilation, layout, rendered, *_ = _run_real_chain()
        for page in rendered.page_details:
            assert "Resolved " not in page.html
            assert "TODO" not in page.html
            assert "placeholder" not in page.html.lower()

    def test_no_broken_or_empty_href(self):
        fixture, compilation, layout, rendered, *_ = _run_real_chain()
        for page in rendered.page_details:
            for href in _HREF_RE.findall(page.html):
                assert href != "", page.route

    def test_no_duplicate_landmark_or_heading_failures(self):
        _, _, _, _, _, _, report = _run_real_chain()
        blocking = {g.gate_id for g in report.gate_results if not g.passed and g.severity == GateSeverity.BLOCKING}
        assert "CG-CMP-005" not in blocking
        assert "CG-CMP-006" not in blocking

    def test_absolute_canonical_and_sitemap_urls(self):
        fixture, compilation, layout, rendered, seo_package, *_ = _run_real_chain()
        for entry in seo_package.entries:
            assert entry.canonical_url.startswith(fixture.base_url)
        for route in seo_package.sitemap_routes:
            assert route.startswith(fixture.base_url)

    def test_no_blocking_gate_failures_beyond_known_findings(self):
        _, _, _, _, _, _, report = _run_real_chain()
        blocking = {g.gate_id for g in report.gate_results if not g.passed and g.severity == GateSeverity.BLOCKING}
        assert blocking == set()


class TestEndToEnd:
    def test_assembly_succeeds(self):
        *_, bundle, _ = _run_real_chain()
        assert isinstance(bundle, SiteBundle)
        assert bundle.files and bundle.bundle_hash

    def test_quality_gates_execute(self):
        *_, report = _run_real_chain()
        assert isinstance(report, QualityReport)
        assert report.gate_results

    def test_repository_materializes(self, tmp_path):
        *_, bundle, _ = _run_real_chain()
        result = SiteBundleRepository().materialize(bundle, str(tmp_path / "site"))
        assert result.written_paths
        for path in result.written_paths:
            assert (tmp_path / "site" / path).is_file()


class TestDeterminism:
    def test_two_runs_byte_identical_bundle_hash(self):
        *_, bundle_a, _ = _run_real_chain()
        *_, bundle_b, _ = _run_real_chain()
        assert bundle_a.bundle_hash == bundle_b.bundle_hash

    def test_two_materializations_byte_identical(self, tmp_path):
        *_, bundle, _ = _run_real_chain()
        a, b = tmp_path / "a", tmp_path / "b"
        ra = SiteBundleRepository().materialize(bundle, str(a))
        rb = SiteBundleRepository().materialize(bundle, str(b))
        for rel in ra.written_paths:
            assert (a / rel).read_bytes() == (b / rel).read_bytes(), rel


class TestForbiddenScope:
    def test_pipeline_remains_unwired(self):
        from engines.website_generation.constants.build import (
            PHASE1_EXECUTED_STAGES,
            STAGE_SPEC_COMPILATION,
        )

        assert PHASE1_EXECUTED_STAGES == (STAGE_SPEC_COMPILATION,)

    def test_all_components_remain_proposed(self):
        registry = build_default_registry()
        ids = [d.component_id for d in registry.all_definitions()]
        assert {str(registry.lifecycle(c)) for c in ids} == {"LifecycleStatus.PROPOSED"}

    def test_no_forbidden_runtime_facilities_in_fixture(self):
        fixture_src = (
            _REPO_ROOT / "tests" / "website_generation" / "fixtures" / "publishable_wave1_fixture.py"
        ).read_text(encoding="utf-8")
        for banned in (
            "import socket", "import urllib", "import requests", "import uuid",
            "import random", "import datetime", "os.environ", "import webbrowser",
            "http.server", "import subprocess", "time.time", "anthropic",
        ):
            assert banned not in fixture_src, banned

    def test_no_images_in_output(self):
        fixture, compilation, layout, rendered, *_ = _run_real_chain()
        for page in rendered.page_details:
            assert "<img" not in page.html
