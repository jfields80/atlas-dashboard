"""No-JS baseline tests (AES-WEB-002J.8; AES-WEB-002 §20.3/§24, CG-RND-006,
D-5).

Covers: ``nav.mobile.drawer`` and ``directory.filters.panel`` remain usable
and accessible with zero JavaScript (native ``<details>``/``<summary>``
disclosure); no component in this delivery emits a ``<script>`` tag, an
external script reference, or any hidden runtime-JS dependency anywhere in
its output.
"""

from __future__ import annotations

import re

from . import J8_COMPONENT_IDS, real_brand_package, real_registry, render_single_component


class TestNavMobileDrawerNoJs:
    def test_uses_native_details_disclosure(self):
        registry = real_registry()
        brand = real_brand_package()
        result = render_single_component(registry, brand, "nav.mobile.drawer")
        html = result.page_details[0].html
        assert "<details" in html
        assert "</details>" in html
        assert "<summary>" in html

    def test_no_script_tag_anywhere(self):
        registry = real_registry()
        brand = real_brand_package()
        result = render_single_component(registry, brand, "nav.mobile.drawer")
        assert "<script" not in result.page_details[0].html

    def test_nav_links_reachable_without_js(self):
        registry = real_registry()
        brand = real_brand_package()
        result = render_single_component(
            registry, brand, "nav.mobile.drawer",
            prop_overrides={"nav_tree": "navref"},
            content_overrides={"nav_tree": "/about"},
        )
        html = result.page_details[0].html
        assert 'href="/about"' in html
        # The link sits inside the <details> element, not gated behind any
        # runtime toggle -- a screen reader/keyboard/no-JS user can always
        # reach it via the native <summary> disclosure control.
        details_start = html.index("<details")
        details_end = html.index("</details>") + len("</details>")
        assert "/about" in html[details_start:details_end]


class TestDirectoryFiltersPanelNoJs:
    def test_uses_native_details_disclosure_regardless_of_variant(self):
        registry = real_registry()
        brand = real_brand_package()
        result = render_single_component(registry, brand, "directory.filters.panel")
        html = result.page_details[0].html
        assert "<details" in html
        assert "<summary>Filters</summary>" in html

    def test_no_script_tag_anywhere(self):
        registry = real_registry()
        brand = real_brand_package()
        result = render_single_component(registry, brand, "directory.filters.panel")
        assert "<script" not in result.page_details[0].html


class TestNoJavaScriptAssetsAnywhere:
    def test_no_component_emits_a_script_tag(self):
        registry = real_registry()
        brand = real_brand_package()
        for component_id in J8_COMPONENT_IDS:
            result = render_single_component(registry, brand, component_id)
            html = result.page_details[0].html
            assert "<script" not in html, component_id

    def test_no_component_references_a_js_asset_url(self):
        registry = real_registry()
        brand = real_brand_package()
        for component_id in J8_COMPONENT_IDS:
            result = render_single_component(registry, brand, component_id)
            html = result.page_details[0].html
            assert not re.search(r'\.js["\'\s>]', html), component_id

    def test_no_component_emits_an_event_handler_attribute(self):
        registry = real_registry()
        brand = real_brand_package()
        for component_id in J8_COMPONENT_IDS:
            result = render_single_component(registry, brand, component_id)
            html = result.page_details[0].html
            assert not re.search(r'\son[a-z]+=', html), component_id

    def test_shared_css_never_references_javascript(self):
        registry = real_registry()
        brand = real_brand_package()
        result = render_single_component(registry, brand, "nav.mobile.drawer")
        assert "javascript" not in result.shared_css.lower()
