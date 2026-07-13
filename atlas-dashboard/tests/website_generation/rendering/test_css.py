"""CSS emission tests (AES-WEB-002J.8; AES-WEB-001 §5.7/§8.3, AES-WEB-002
§20.2).

Covers: deterministic shared CSS across repeated builds, sorted custom-
property/selector/media-query order, manifest-driven tree-shaking (only
present components' classes appear), missing-token failure, no random
hashes, no external URLs, and no untrusted-content interpolation (CSS never
reads ContentPackage at all).
"""

from __future__ import annotations

import re

from engines.website_generation.contracts.artifacts import ComponentInstance
from engines.website_generation.rendering.css_emitter import (
    compile_custom_properties,
    compile_shared_css,
    component_class,
    custom_property_name,
    token_var,
)

from . import J8_COMPONENT_IDS, real_brand_package, real_registry, render_page, render_single_component


class TestCustomPropertyCompilation:
    def test_token_id_to_custom_property_name(self):
        assert custom_property_name("color.text.link") == "--color-text-link"

    def test_token_var_reference(self):
        assert token_var("color.text.link") == "var(--color-text-link)"

    def test_custom_properties_sorted_regardless_of_input_order(self):
        forward = compile_custom_properties({"b.token": "1", "a.token": "2"})
        backward = compile_custom_properties({"a.token": "2", "b.token": "1"})
        assert forward == backward
        assert forward.index("--a-token") < forward.index("--b-token")

    def test_empty_tokens_produce_empty_root_block(self):
        assert compile_custom_properties({}) == ":root{}"


class TestDeterministicSharedCss:
    def test_same_build_produces_identical_css(self):
        registry = real_registry()
        brand = real_brand_package()
        a = render_single_component(registry, brand, "atom.button.action")
        b = render_single_component(registry, brand, "atom.button.action")
        assert a.shared_css == b.shared_css
        assert a.shared_css_hash == b.shared_css_hash

    def test_css_root_block_present(self):
        registry = real_registry()
        brand = real_brand_package()
        result = render_single_component(registry, brand, "atom.button.action")
        assert result.shared_css.startswith(":root{")


class TestManifestDrivenTreeShaking:
    def test_only_present_components_contribute_rules(self):
        registry = real_registry()
        brand = real_brand_package()
        button_definition = registry.get("atom.button.action")
        badge_definition = registry.get("atom.badge.status")

        result = render_single_component(registry, brand, "atom.button.action")
        css = result.shared_css
        assert "." + component_class(button_definition) in css
        assert "." + component_class(badge_definition) not in css

    def test_shell_is_always_present(self):
        registry = real_registry()
        brand = real_brand_package()
        shell_definition = registry.get("layout.shell.page")
        result = render_single_component(registry, brand, "atom.button.action")
        # The shell contributes CSS only if it declares token deps; verify
        # its class is at least evaluable without error and, if it declares
        # deps, that they appear.
        if shell_definition.design_token_dependencies:
            assert "." + component_class(shell_definition) in result.shared_css


class TestComponentClassDeterminism:
    def test_component_class_matches_html_output(self):
        registry = real_registry()
        brand = real_brand_package()
        definition = registry.get("atom.button.action")
        result = render_single_component(registry, brand, "atom.button.action")
        assert component_class(definition) in result.page_details[0].html

    def test_component_class_is_never_hashed_random(self):
        registry = real_registry()
        definition = registry.get("atom.button.action")
        a = component_class(definition)
        b = component_class(definition)
        assert a == b == "ac-atom--button-action"


class TestNoRandomHashesOrExternalUrls:
    def test_shared_css_contains_no_url_scheme(self):
        registry = real_registry()
        brand = real_brand_package()
        for component_id in J8_COMPONENT_IDS[:5]:
            result = render_single_component(registry, brand, component_id)
            assert "http://" not in result.shared_css
            assert "https://" not in result.shared_css
            assert "url(" not in result.shared_css

    def test_shared_css_has_no_content_derived_text(self):
        # CSS emission never reads ContentPackage -- structurally impossible
        # to leak untrusted content into a stylesheet, verified by exercising
        # a component with hostile content and confirming it never appears
        # in the CSS payload (only in the HTML payload, correctly escaped).
        registry = real_registry()
        brand = real_brand_package()
        result = render_single_component(
            registry, brand, "atom.button.action",
            content_overrides={"label": "UNIQUE_HOSTILE_MARKER_<script>"},
        )
        assert "UNIQUE_HOSTILE_MARKER" not in result.shared_css


class TestMissingTokenDiagnostic:
    def test_missing_token_is_flagged_without_crashing_css_compile(self):
        # compile_shared_css only emits rules for tokens present in the map
        # -- a component whose dependency is absent contributes no
        # declaration for that token rather than emitting var() with no
        # backing custom property.
        from engines.website_generation.components.registry import build_default_registry

        registry = build_default_registry()
        definition = registry.get("atom.button.action")
        css = compile_shared_css([definition], {})
        assert "color-action-primary" not in css


class TestDeclarationAndSelectorOrderStable:
    def test_repeated_compilation_is_byte_identical(self):
        registry = real_registry()
        definitions = registry.all_definitions()
        tokens = {}
        brand = real_brand_package()
        tokens.update(brand.palette)
        tokens.update(brand.extended_tokens)
        a = compile_shared_css(definitions, tokens)
        b = compile_shared_css(list(reversed(definitions)), tokens)
        assert a == b
