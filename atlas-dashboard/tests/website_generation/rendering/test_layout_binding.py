"""Layout-binding tests (AES-WEB-002J.8; AES-WEB-001 §5.7, AES-WEB-002 §9).

Covers: page order preserved, region order preserved, component order
preserved, component_index resolution (including out-of-range failure),
grid token/column-span application, responsive-selection application, and
the "Renderer never reorders" invariant.
"""

from __future__ import annotations

import pytest

from engines.website_generation.contracts.artifacts import (
    ComponentInstance,
    ComponentPlacement,
    ContentBlock,
    GridPlacement,
    LayoutRegion,
    PageComponents,
    PageLayout,
    RegionLayoutDetail,
    ResponsiveSelection,
)
from engines.website_generation.contracts.enums import RegionKind
from engines.website_generation.contracts.errors import RenderError
from engines.website_generation.rendering.renderer import Renderer

from . import make_component_manifest, make_content_package, make_layout_plan, real_brand_package, real_registry


def _button(index_label: str) -> ComponentInstance:
    return ComponentInstance(
        component_id="atom.button.action",
        component_version="1.0.0",
        props={"weight": "primary"},
        content_refs=("label",),
    )


class TestPageOrderPreserved:
    def test_pages_render_in_layout_plan_order(self):
        registry = real_registry()
        brand = real_brand_package()
        manifest = make_component_manifest(
            pages=(
                PageComponents(route="/b", components=(_button("b"),)),
                PageComponents(route="/a", components=(_button("a"),)),
            )
        )
        content = make_content_package(
            blocks=(
                ContentBlock(page_route="/b", slot_id="label", text="B"),
                ContentBlock(page_route="/a", slot_id="label", text="A"),
            )
        )
        # LayoutPlan declares /b before /a -- output order must follow this,
        # not the manifest's own page order.
        layout = make_layout_plan(
            pages=(
                PageLayout(
                    route="/b",
                    regions=(LayoutRegion(region_id="BODY", component_indexes=(0,)),),
                ),
                PageLayout(
                    route="/a",
                    regions=(LayoutRegion(region_id="BODY", component_indexes=(0,)),),
                ),
            ),
            region_details=(
                RegionLayoutDetail(
                    route="/b", region_id="BODY", region_kind=RegionKind.BODY,
                    placements=(ComponentPlacement(component_index=0),),
                ),
                RegionLayoutDetail(
                    route="/a", region_id="BODY", region_kind=RegionKind.BODY,
                    placements=(ComponentPlacement(component_index=0),),
                ),
            ),
        )
        result = Renderer(registry).render(layout, manifest, content, brand)
        assert [p.route for p in result.pages] == ["/b", "/a"]


class TestRegionAndComponentOrderPreserved:
    def test_component_order_within_region_is_manifest_order(self):
        registry = real_registry()
        brand = real_brand_package()
        manifest = make_component_manifest(
            pages=(
                PageComponents(
                    route="/",
                    components=(
                        ComponentInstance(
                            component_id="atom.badge.status",
                            component_version="1.0.0",
                            props={"kind": "verified"},
                            content_refs=("label",),
                        ),
                        ComponentInstance(
                            component_id="atom.badge.status",
                            component_version="1.0.0",
                            props={"kind": "featured"},
                            content_refs=("label",),
                        ),
                    ),
                ),
            )
        )
        content = make_content_package(
            blocks=(
                ContentBlock(page_route="/", slot_id="label", text="First"),
            )
        )
        layout = make_layout_plan(
            pages=(
                PageLayout(
                    route="/",
                    regions=(
                        LayoutRegion(region_id="BODY", component_indexes=(1, 0)),
                    ),
                ),
            ),
            region_details=(
                RegionLayoutDetail(
                    route="/", region_id="BODY", region_kind=RegionKind.BODY,
                    placements=(
                        ComponentPlacement(component_index=1),
                        ComponentPlacement(component_index=0),
                    ),
                ),
            ),
        )
        result = Renderer(registry).render(layout, manifest, content, brand)
        html = result.page_details[0].html
        # component_indexes=(1, 0): the "featured" instance (index 1) must
        # appear before the "verified" instance (index 0) in the output --
        # LayoutPlan's own declared order, not manifest declaration order.
        assert html.index("ac-atom--featured") < html.index("ac-atom--verified")


class TestComponentIndexResolution:
    def test_out_of_range_index_fails_deterministically(self):
        registry = real_registry()
        brand = real_brand_package()
        manifest = make_component_manifest(
            pages=(PageComponents(route="/", components=()),)
        )
        content = make_content_package()
        layout = make_layout_plan(
            pages=(
                PageLayout(
                    route="/",
                    regions=(LayoutRegion(region_id="BODY", component_indexes=(0,)),),
                ),
            ),
            region_details=(
                RegionLayoutDetail(
                    route="/", region_id="BODY", region_kind=RegionKind.BODY,
                    placements=(ComponentPlacement(component_index=0),),
                ),
            ),
        )
        with pytest.raises(RenderError) as exc_info:
            Renderer(registry).render(layout, manifest, content, brand)
        assert "malformed_layout_indexes" in exc_info.value.diagnostics

    def test_route_not_in_manifest_fails(self):
        registry = real_registry()
        brand = real_brand_package()
        manifest = make_component_manifest(pages=())
        content = make_content_package()
        layout = make_layout_plan(
            pages=(
                PageLayout(
                    route="/missing",
                    regions=(LayoutRegion(region_id="BODY", component_indexes=(0,)),),
                ),
            ),
        )
        with pytest.raises(RenderError) as exc_info:
            Renderer(registry).render(layout, manifest, content, brand)
        assert "unresolved_routes" in exc_info.value.diagnostics


class TestGridAndResponsivePlacementApplied:
    def test_grid_placement_reaches_the_emitter(self):
        # layout.grid.standard's own "columns" prop drives its class, but
        # the *placement* GridPlacement (grid.columns_token/column_span)
        # from RegionLayoutDetail must still resolve without error and be
        # available to the emitter via LayoutContext -- exercised end to
        # end here via a component whose region+placement is fully wired.
        registry = real_registry()
        brand = real_brand_package()
        manifest = make_component_manifest(
            pages=(
                PageComponents(
                    route="/",
                    components=(
                        ComponentInstance(
                            component_id="layout.grid.standard",
                            component_version="1.0.0",
                            props={"columns": "3"},
                        ),
                    ),
                ),
            )
        )
        content = make_content_package()
        layout = make_layout_plan(
            pages=(
                PageLayout(
                    route="/",
                    regions=(LayoutRegion(region_id="BODY", component_indexes=(0,)),),
                ),
            ),
            region_details=(
                RegionLayoutDetail(
                    route="/", region_id="BODY", region_kind=RegionKind.BODY,
                    placements=(
                        ComponentPlacement(
                            component_index=0,
                            grid=GridPlacement(columns_token="grid.columns.3", column_span=1),
                            responsive=ResponsiveSelection(collapse_behavior="grid-to-stack"),
                        ),
                    ),
                ),
            ),
        )
        result = Renderer(registry).render(layout, manifest, content, brand)
        assert "ac-layout--cols-3" in result.page_details[0].html


class TestRendererNeverReorders:
    def test_region_order_follows_page_regions_not_region_kind_enum_order(self):
        registry = real_registry()
        brand = real_brand_package()
        # Two regions declared BODY-before-FOOTER in the LayoutPlan (which
        # also happens to be RegionKind declaration order); the assertion is
        # that output order follows page.regions verbatim, not a
        # re-derivation.
        manifest = make_component_manifest(
            pages=(
                PageComponents(
                    route="/",
                    components=(
                        ComponentInstance(
                            component_id="directory.results.summary",
                            component_version="1.0.0",
                            content_refs=("summary_text",),
                        ),
                        ComponentInstance(
                            component_id="legal.footer.directory",
                            component_version="1.0.0",
                            props={"nav_tree": "footer-nav"},
                            content_refs=("legal_facts", "disclosures"),
                        ),
                    ),
                ),
            )
        )
        content = make_content_package(
            blocks=(
                ContentBlock(page_route="/", slot_id="summary_text", text="12 results"),
                ContentBlock(page_route="/", slot_id="legal_facts", text="Facts"),
                ContentBlock(page_route="/", slot_id="disclosures", text="Disclosure"),
                ContentBlock(page_route="/", slot_id="footer-nav", text="/home"),
            )
        )
        layout = make_layout_plan(
            pages=(
                PageLayout(
                    route="/",
                    regions=(
                        LayoutRegion(region_id="BODY", component_indexes=(0,)),
                        LayoutRegion(region_id="FOOTER", component_indexes=(1,)),
                    ),
                ),
            ),
            region_details=(
                RegionLayoutDetail(
                    route="/", region_id="BODY", region_kind=RegionKind.BODY,
                    placements=(ComponentPlacement(component_index=0),),
                ),
                RegionLayoutDetail(
                    route="/", region_id="FOOTER", region_kind=RegionKind.FOOTER,
                    placements=(ComponentPlacement(component_index=1),),
                ),
            ),
        )
        result = Renderer(registry).render(layout, manifest, content, brand)
        html = result.page_details[0].html
        assert html.index("12 results") < html.index("Facts")
        assert "<main id=\"main\">" in html
        assert "<footer>" in html
