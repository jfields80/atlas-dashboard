"""Content-binding tests (AES-WEB-002J.8; AES-WEB-001 §5.7).

Covers: exact (route, slot_id) content resolution, missing required content
fails, optional content omission, ONE_TO_N multi-value binding
(navigation/discovery link collections), and the "no invented copy"
invariant (a component with unresolved optional content never fabricates
placeholder text).
"""

from __future__ import annotations

import pytest

from engines.website_generation.contracts.artifacts import ComponentInstance, ContentBlock
from engines.website_generation.contracts.errors import RenderError

from . import real_brand_package, real_registry, render_page, render_single_component


class TestExactSlotBinding:
    def test_content_resolved_by_exact_route_and_slot_id(self):
        registry = real_registry()
        brand = real_brand_package()
        result = render_single_component(
            registry,
            brand,
            "atom.button.action",
            content_overrides={"label": "Book Now"},
        )
        assert "Book Now" in result.page_details[0].html

    def test_content_bound_to_a_different_route_is_not_leaked(self):
        registry = real_registry()
        brand = real_brand_package()
        definition = registry.get("atom.button.action")
        instance = ComponentInstance(
            component_id="atom.button.action",
            component_version="1.0.0",
            props={"weight": "primary"},
            content_refs=("label",),
        )
        # The only ContentBlock is bound to a *different* route than the
        # page being rendered -- this must fail as missing content, not
        # silently resolve to empty or to the wrong page's text.
        with pytest.raises(RenderError) as exc_info:
            render_page(
                registry,
                brand,
                "/real-route",
                (instance,),
                (ContentBlock(page_route="/other-route", slot_id="label", text="Wrong page"),),
            )
        assert "missing_required_content" in exc_info.value.diagnostics


class TestMissingRequiredContentFails:
    def test_required_slot_absent_from_content_refs_fails(self):
        registry = real_registry()
        brand = real_brand_package()
        instance = ComponentInstance(
            component_id="atom.button.action",
            component_version="1.0.0",
            props={"weight": "primary"},
            # "label" not listed in content_refs at all
        )
        with pytest.raises(RenderError) as exc_info:
            render_page(registry, brand, "/", (instance,), ())
        diag = exc_info.value.diagnostics["missing_required_content"]
        assert diag[0]["slots"] == ["label"]

    def test_required_slot_in_content_refs_but_unresolvable_fails(self):
        registry = real_registry()
        brand = real_brand_package()
        instance = ComponentInstance(
            component_id="atom.button.action",
            component_version="1.0.0",
            props={"weight": "primary"},
            content_refs=("label",),
        )
        # content_refs names "label" but no matching ContentBlock exists.
        with pytest.raises(RenderError) as exc_info:
            render_page(registry, brand, "/", (instance,), ())
        assert "missing_required_content" in exc_info.value.diagnostics


class TestOptionalContentOmission:
    def test_optional_slot_absent_renders_without_it(self):
        registry = real_registry()
        brand = real_brand_package()
        # layout.section.container's "heading" slot is optional.
        result = render_single_component(registry, brand, "layout.section.container")
        assert "<h2>" not in result.page_details[0].html

    def test_optional_slot_present_renders_with_it(self):
        registry = real_registry()
        brand = real_brand_package()
        result = render_single_component(
            registry,
            brand,
            "layout.section.container",
            content_overrides={"heading": "Featured"},
            include_optional=True,
        )
        assert "<h2>Featured</h2>" in result.page_details[0].html

    def test_no_content_is_ever_invented_for_missing_optional(self):
        registry = real_registry()
        brand = real_brand_package()
        result = render_single_component(registry, brand, "layout.section.container")
        html = result.page_details[0].html
        for placeholder in ("Lorem", "TODO", "placeholder", "Featured"):
            assert placeholder not in html


class TestOneToNBinding:
    def test_multiple_blocks_sharing_one_slot_all_render(self):
        registry = real_registry()
        brand = real_brand_package()
        definition = registry.get("directory.categories.grid")
        instance = ComponentInstance(
            component_id="directory.categories.grid",
            component_version="1.0.0",
            props={"category_source_ref": "cat-source", "columns": "3"},
            content_refs=("category_tiles",),
        )
        blocks = (
            ContentBlock(page_route="/", slot_id="cat-source", text="Category taxonomy"),
            ContentBlock(page_route="/", slot_id="category_tiles", text="/cat/dogs"),
            ContentBlock(page_route="/", slot_id="category_tiles", text="/cat/cats"),
            ContentBlock(page_route="/", slot_id="category_tiles", text="/cat/birds"),
        )
        result = render_page(registry, brand, "/", (instance,), blocks)
        html = result.page_details[0].html
        assert html.count('href="/cat/') == 3
        # ContentPackage's own block order is preserved, never re-sorted.
        assert html.index("/cat/dogs") < html.index("/cat/cats") < html.index("/cat/birds")

    def test_zero_bound_values_for_required_one_to_n_slot_fails(self):
        registry = real_registry()
        brand = real_brand_package()
        instance = ComponentInstance(
            component_id="directory.categories.grid",
            component_version="1.0.0",
            props={"category_source_ref": "cat-source", "columns": "3"},
            content_refs=("category_tiles",),
        )
        with pytest.raises(RenderError) as exc_info:
            render_page(registry, brand, "/", (instance,), ())
        assert "missing_required_content" in exc_info.value.diagnostics


class TestContentBlockRefPropResolution:
    def test_content_block_ref_prop_resolves_like_a_slot(self):
        registry = real_registry()
        brand = real_brand_package()
        instance = ComponentInstance(
            component_id="atom.link.standard",
            component_version="1.0.0",
            props={"link": "my-link-ref"},
        )
        blocks = (ContentBlock(page_route="/", slot_id="my-link-ref", text="/destination"),)
        result = render_page(registry, brand, "/", (instance,), blocks)
        assert 'href="/destination"' in result.page_details[0].html
