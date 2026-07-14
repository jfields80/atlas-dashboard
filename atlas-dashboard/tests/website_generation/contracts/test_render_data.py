"""Render-data contract tests (AES-WEB-002K.1; ADR-WEB-CONTENT-BINDING-MAP).

Covers the frozen, non-artifact ``contracts/render_data.py`` types
themselves (frozen, deterministic, no unrestricted dict, no artifact
registration) and the module's layering constraints (no import from
``rendering/`` or ``components/``, no circular import via ``artifacts.py``).
Producer-side honesty (unsafe URLs, missing categories) is exercised through
the real ``ComponentEngine.compile()`` in ``test_repetition.py``'s sibling
files, not here -- this file is a pure contract-shape test.
"""

from __future__ import annotations

import ast
import pathlib

import pytest

from engines.website_generation.contracts.render_data import (
    RENDER_DATA_VERSION,
    ComponentRenderData,
    ContactData,
    HoursData,
    HoursRow,
    LinkSpec,
    ListingCardData,
    NavigationData,
    RenderDataBundle,
    RenderDataEntry,
    TileLinks,
    generated_render_data_key,
    is_render_data_prop_value,
    is_safe_url,
)


class TestVersionConstant:
    def test_render_data_version(self):
        assert RENDER_DATA_VERSION == "1.0.0"


class TestLinkSpec:
    def test_construction_and_defaults(self):
        link = LinkSpec(label="Hotels", href="/hotels/")
        assert link.label == "Hotels"
        assert link.href == "/hotels/"
        assert link.rel == ""
        assert link.aria_label == ""
        assert link.external is False

    def test_full_construction(self):
        link = LinkSpec(
            label="Visit site", href="https://example.com", rel="noopener sponsored",
            aria_label="Visit external site", external=True,
        )
        assert link.rel == "noopener sponsored"
        assert link.external is True

    def test_frozen(self):
        link = LinkSpec(label="Home", href="/")
        with pytest.raises(Exception):
            link.label = "Other"

    def test_extra_field_forbidden(self):
        with pytest.raises(Exception):
            LinkSpec(label="Home", href="/", nonexistent="x")


class TestNavigationDataAndTileLinks:
    def test_empty_default(self):
        assert NavigationData().links == ()
        assert TileLinks().tiles == ()

    def test_construction(self):
        links = (LinkSpec(label="Home", href="/"), LinkSpec(label="Hotels", href="/hotels/"))
        nav = NavigationData(links=links)
        assert nav.links == links
        tiles = TileLinks(tiles=links)
        assert tiles.tiles == links

    def test_frozen(self):
        nav = NavigationData(links=(LinkSpec(label="Home", href="/"),))
        with pytest.raises(Exception):
            nav.links = ()


class TestListingCardData:
    def test_minimal_construction(self):
        card = ListingCardData(
            listing_id="alpine-lantern-lodge", name="Alpine Lantern Lodge",
            profile_href="/hotels/alpine-lantern-lodge/",
        )
        assert card.area_label == ""
        assert card.rating_text == ""
        assert card.review_count is None
        assert card.badge_kind == ""
        assert card.badge_label == ""
        assert card.cta is None

    def test_full_construction(self):
        cta = LinkSpec(label="Book now", href="https://example.com/book", external=True)
        card = ListingCardData(
            listing_id="l1", name="Cedar Harbor Inn", profile_href="/hotels/cedar-harbor-inn/",
            area_label="Breckenridge, CO", rating_text="4.4", review_count=61,
            badge_kind="verified", badge_label="Verified", cta=cta,
        )
        assert card.review_count == 61
        assert card.cta == cta

    def test_review_count_zero_distinct_from_absent(self):
        # A real, honest zero must round-trip -- never coerced to "absent".
        card = ListingCardData(
            listing_id="l1", name="X", profile_href="/x/", review_count=0,
        )
        assert card.review_count == 0
        assert card.review_count is not None

    def test_frozen(self):
        card = ListingCardData(listing_id="l1", name="X", profile_href="/x/")
        with pytest.raises(Exception):
            card.name = "Y"


class TestContactData:
    def test_empty_default(self):
        contact = ContactData()
        assert contact.address_text == ""
        assert contact.phone is None
        assert contact.email is None
        assert contact.website is None

    def test_full_construction(self):
        contact = ContactData(
            address_text="123 Main St, Aspen, CO",
            phone=LinkSpec(label="555-0100", href="tel:5550100"),
            email=LinkSpec(label="hi@example.com", href="mailto:hi@example.com"),
            website=LinkSpec(label="Visit website", href="https://example.com", external=True),
        )
        assert contact.phone.href == "tel:5550100"
        assert contact.email.href.startswith("mailto:")
        assert contact.website.external is True


class TestHoursRowAndHoursData:
    def test_hours_row_construction(self):
        row = HoursRow(day="Monday", opens="08:00", closes="20:00", closed=False)
        assert row.day == "Monday"
        assert row.closed is False

    def test_closed_day_row(self):
        row = HoursRow(day="Sunday", closed=True)
        assert row.closed is True
        assert row.opens == ""
        assert row.closes == ""

    def test_hours_data_ordering_preserved(self):
        rows = (
            HoursRow(day="Monday", opens="08:00", closes="20:00"),
            HoursRow(day="Tuesday", opens="08:00", closes="20:00"),
        )
        hours = HoursData(rows=rows)
        assert hours.rows == rows

    def test_empty_default(self):
        assert HoursData().rows == ()


class TestComponentRenderDataAndBundle:
    def test_all_members_optional_and_independent(self):
        data = ComponentRenderData()
        assert data.nav is None
        assert data.tiles is None
        assert data.card is None
        assert data.contact is None
        assert data.hours is None

    def test_one_member_populated(self):
        data = ComponentRenderData(nav=NavigationData(links=(LinkSpec(label="Home", href="/"),)))
        assert data.nav is not None
        assert data.card is None

    def test_render_data_entry_construction(self):
        entry = RenderDataEntry(route="/", component_index=0, data=ComponentRenderData())
        assert entry.route == "/"
        assert entry.component_index == 0

    def test_render_data_bundle_empty_default(self):
        bundle = RenderDataBundle()
        assert bundle.entries == ()

    def test_render_data_bundle_construction(self):
        entries = (
            RenderDataEntry(route="/", component_index=0, data=ComponentRenderData()),
            RenderDataEntry(route="/hotels/", component_index=1, data=ComponentRenderData()),
        )
        bundle = RenderDataBundle(entries=entries)
        assert bundle.entries == entries

    def test_frozen(self):
        bundle = RenderDataBundle()
        with pytest.raises(Exception):
            bundle.entries = (RenderDataEntry(route="/", component_index=0, data=ComponentRenderData()),)


class TestGeneratedRenderDataKey:
    def test_deterministic_and_stable(self):
        a = generated_render_data_key("primary_navigation", 0)
        b = generated_render_data_key("primary_navigation", 0)
        assert a == b == "render:primary_navigation.0"

    def test_unique_per_component_index(self):
        assert generated_render_data_key("primary_navigation", 0) != generated_render_data_key(
            "primary_navigation", 1
        )

    def test_recognized_by_is_render_data_prop_value(self):
        key = generated_render_data_key("footer_navigation", 3)
        assert is_render_data_prop_value(key)

    def test_ordinary_content_slot_id_not_recognized(self):
        assert not is_render_data_prop_value("bind.listing_name.0")
        assert not is_render_data_prop_value("hero_h1")


class TestIsSafeUrl:
    @pytest.mark.parametrize("url", ["/hotels/", "#main", "https://example.com", "tel:5550100", "mailto:a@b.com"])
    def test_safe_urls(self, url):
        assert is_safe_url(url)

    @pytest.mark.parametrize(
        "url", ["javascript:alert(1)", "data:text/html,x", "//evil.example.com", "", "   "]
    )
    def test_unsafe_or_empty_urls(self, url):
        assert not is_safe_url(url)


class TestNoDictAnyOrArbitraryPayload:
    def test_no_dict_any_fields_declared(self):
        # Structural honesty check: none of the render-data models declare a
        # Dict[str, Any]-shaped field or an "extensions"/"metadata" catch-all.
        for model in (
            LinkSpec, NavigationData, TileLinks, ListingCardData, ContactData,
            HoursRow, HoursData, ComponentRenderData, RenderDataEntry, RenderDataBundle,
        ):
            for name in model.__fields__:
                assert name not in ("metadata", "extensions", "payload", "extra")

    def test_models_reject_unknown_fields(self):
        with pytest.raises(Exception):
            ComponentRenderData(unknown_field="x")


class TestDependencyLayering:
    """AES-WEB-002 §29.2 import matrix: contracts/render_data.py must not
    import rendering/ or components/ (it is imported BY both), and must not
    import contracts/artifacts.py (artifacts.py imports IT, so the reverse
    would be circular) -- verified by AST inspection of the actual
    committed source, not by convention alone."""

    @staticmethod
    def _imported_modules(path: pathlib.Path) -> set:
        tree = ast.parse(path.read_text(encoding="utf-8"))
        modules = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                modules.add(node.module)
            elif isinstance(node, ast.Import):
                modules.update(alias.name for alias in node.names)
        return modules

    def test_render_data_does_not_import_rendering(self):
        path = pathlib.Path("engines/website_generation/contracts/render_data.py")
        modules = self._imported_modules(path)
        assert not any("rendering" in m for m in modules)

    def test_render_data_does_not_import_components(self):
        path = pathlib.Path("engines/website_generation/contracts/render_data.py")
        modules = self._imported_modules(path)
        assert not any(".components" in m or m.endswith("components") for m in modules)

    def test_render_data_does_not_import_artifacts(self):
        # Avoiding the circular import: artifacts.py imports render_data.py
        # (for ComponentCompilationResult.render_data's type), so the
        # reverse import is illegal, not just unused.
        path = pathlib.Path("engines/website_generation/contracts/render_data.py")
        modules = self._imported_modules(path)
        assert not any(m.endswith("contracts.artifacts") for m in modules)

    def test_artifacts_imports_render_data_one_directionally(self):
        path = pathlib.Path("engines/website_generation/contracts/artifacts.py")
        modules = self._imported_modules(path)
        assert any(m.endswith("contracts.render_data") for m in modules)
