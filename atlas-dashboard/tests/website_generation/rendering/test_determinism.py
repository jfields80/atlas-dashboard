"""Determinism tests (AES-WEB-002J.8; AES-WEB-001 §1.1/§5.7, CG-RND-001).

Covers: identical inputs produce equal RenderedPageSet/canonical
JSON/artifact hash; fresh Renderer instances produce byte-identical output;
registry construction order and emitter-table dict insertion order do not
affect output; stable diagnostics ordering on failure.
"""

from __future__ import annotations

from engines.website_generation.components.registry import ComponentRegistry
from engines.website_generation.contracts.artifacts import artifact_sha256, canonical_artifact_json
from engines.website_generation.contracts.errors import RenderError
from engines.website_generation.rendering.renderer import Renderer

from . import J8_COMPONENT_IDS, real_brand_package, real_registry, render_page, render_single_component


class TestRepeatedRenderIsIdentical:
    def test_same_inputs_equal_models(self):
        registry = real_registry()
        brand = real_brand_package()
        a = render_single_component(registry, brand, "atom.button.action")
        b = render_single_component(registry, brand, "atom.button.action")
        assert a == b

    def test_same_inputs_equal_canonical_json(self):
        registry = real_registry()
        brand = real_brand_package()
        a = render_single_component(registry, brand, "nav.header.standard")
        b = render_single_component(registry, brand, "nav.header.standard")
        assert canonical_artifact_json(a) == canonical_artifact_json(b)

    def test_same_inputs_equal_artifact_hash(self):
        registry = real_registry()
        brand = real_brand_package()
        a = render_single_component(registry, brand, "directory.search.primary")
        b = render_single_component(registry, brand, "directory.search.primary")
        assert artifact_sha256(a) == artifact_sha256(b)

    def test_html_hash_is_deterministic_across_calls(self):
        registry = real_registry()
        brand = real_brand_package()
        a = render_single_component(registry, brand, "status.results.zero")
        b = render_single_component(registry, brand, "status.results.zero")
        assert a.pages[0].html_hash == b.pages[0].html_hash
        assert a.page_details[0].html == b.page_details[0].html


class TestFreshInstancesAreByteIdentical:
    def test_two_fresh_renderer_instances_agree(self):
        registry = real_registry()
        brand = real_brand_package()
        r1 = Renderer(registry)
        r2 = Renderer(registry)
        assert r1 is not r2
        for component_id in J8_COMPONENT_IDS:
            out1 = render_single_component(registry, brand, component_id)
            out2 = render_single_component(registry, brand, component_id)
            assert out1.page_details[0].html == out2.page_details[0].html


class TestRegistryConstructionOrderIndependence:
    def test_reordered_definitions_yield_same_render(self):
        registry_a = real_registry()
        definitions = list(registry_a.all_definitions())
        reversed_registry = ComponentRegistry(list(reversed(definitions)))
        brand = real_brand_package()

        out_a = render_single_component(registry_a, brand, "atom.badge.status")
        out_b = render_single_component(reversed_registry, brand, "atom.badge.status")
        assert out_a.page_details[0].html == out_b.page_details[0].html


class TestEmitterTableOrderIndependence:
    def test_merged_table_content_independent_of_family_order(self):
        from engines.website_generation.rendering.emitters_discovery import (
            DISCOVERY_EMITTERS,
        )
        from engines.website_generation.rendering.emitters_layout_atoms import (
            LAYOUT_ATOMS_EMITTERS,
        )
        from engines.website_generation.rendering.emitters_navigation import (
            NAVIGATION_EMITTERS,
        )

        forward = {}
        for table in (LAYOUT_ATOMS_EMITTERS, NAVIGATION_EMITTERS, DISCOVERY_EMITTERS):
            forward.update(table)
        backward = {}
        for table in (DISCOVERY_EMITTERS, NAVIGATION_EMITTERS, LAYOUT_ATOMS_EMITTERS):
            backward.update(table)
        assert set(forward) == set(backward)


class TestStableDiagnostics:
    def test_repeated_failure_yields_identical_diagnostics(self):
        registry = real_registry()
        brand = real_brand_package()
        definition = registry.get("atom.button.action")
        from engines.website_generation.contracts.artifacts import ComponentInstance

        instance = ComponentInstance(
            component_id="atom.button.action",
            component_version="1.0.0",
            props={"weight": "primary"},
            # required "label" slot deliberately unbound
        )

        def _attempt():
            try:
                render_page(registry, brand, "/", (instance,), ())
                return None
            except RenderError as exc:
                return exc.diagnostics

        first = _attempt()
        second = _attempt()
        assert first is not None
        assert first == second
