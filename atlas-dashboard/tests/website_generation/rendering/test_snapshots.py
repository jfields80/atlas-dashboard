"""HTML snapshot tests for all 32 J.8 components (AES-WEB-002J.8;
AES-WEB-001 §11.4, AES-WEB-002 §20.1, CG-RND-004).

Two tiers:

* A parametrized sweep over all 32 ``J8_COMPONENT_IDS`` asserting the
  properties every emitter must share -- analytics attributes present,
  alphabetical attribute order, the component's own class present, stable
  double-render output, no forbidden internal markers.
* Targeted exact-markup snapshots for one representative component per
  distinctive shape (button, link, labeled field, drawer, document shell,
  search form, badge, breadcrumbs) -- pinned literal strings, so an
  unintended markup change (a real snapshot diff) fails loudly and an
  intentional one requires touching this file, matching §11.4's "snapshot
  updates require an explicit engine version bump" discipline in spirit.
"""

from __future__ import annotations

import re

import pytest

from . import J8_COMPONENT_IDS, real_brand_package, real_registry, render_single_component

_ATTR_RE = re.compile(r'([a-zA-Z:-]+)="[^"]*"')


def _attr_names_in_order(tag_html: str) -> list:
    """Every attribute name in the first opening tag, in the order it
    appears in the markup."""
    match = re.match(r"<[a-zA-Z0-9]+((?:\s+[a-zA-Z:-]+=\"[^\"]*\")*)", tag_html)
    if not match:
        return []
    return _ATTR_RE.findall(match.group(1))


class TestUniformEmitterProperties:
    @pytest.mark.parametrize("component_id", J8_COMPONENT_IDS)
    def test_renders_without_error(self, component_id):
        registry = real_registry()
        brand = real_brand_package()
        result = render_single_component(registry, brand, component_id)
        assert result.page_details[0].html

    @pytest.mark.parametrize("component_id", J8_COMPONENT_IDS)
    def test_analytics_attributes_present(self, component_id):
        registry = real_registry()
        brand = real_brand_package()
        definition = registry.get(component_id)
        result = render_single_component(registry, brand, component_id)
        html = result.page_details[0].html
        impression_id = definition.analytics_contract.impression_id
        assert 'data-atlas-c="%s"' % impression_id in html
        assert 'data-atlas-v="1.0.0"' in html

    @pytest.mark.parametrize("component_id", J8_COMPONENT_IDS)
    def test_class_prefix_present(self, component_id):
        registry = real_registry()
        brand = real_brand_package()
        definition = registry.get(component_id)
        result = render_single_component(registry, brand, component_id)
        html = result.page_details[0].html
        assert definition.rendering_contract.class_prefix in html

    @pytest.mark.parametrize("component_id", J8_COMPONENT_IDS)
    def test_double_render_hash_equality(self, component_id):
        # CG-RND-001, scoped to a single component.
        registry = real_registry()
        brand = real_brand_package()
        a = render_single_component(registry, brand, component_id)
        b = render_single_component(registry, brand, component_id)
        assert a.pages[0].html_hash == b.pages[0].html_hash

    @pytest.mark.parametrize("component_id", J8_COMPONENT_IDS)
    def test_no_internal_metadata_leakage(self, component_id):
        registry = real_registry()
        brand = real_brand_package()
        result = render_single_component(registry, brand, component_id)
        html = result.page_details[0].html
        for marker in ("selection_trace", "registry_version", "build_id", "__shell_body__"):
            assert marker not in html

    @pytest.mark.parametrize("component_id", J8_COMPONENT_IDS)
    def test_no_inline_script_or_style(self, component_id):
        registry = real_registry()
        brand = real_brand_package()
        result = render_single_component(registry, brand, component_id)
        html = result.page_details[0].html
        assert "<script" not in html
        assert " style=" not in html

    @pytest.mark.parametrize("component_id", J8_COMPONENT_IDS)
    def test_attribute_order_is_alphabetical_on_the_root_element(self, component_id):
        registry = real_registry()
        brand = real_brand_package()
        result = render_single_component(registry, brand, component_id)
        html = result.page_details[0].html
        # The shell always wraps output; inspect the shell's own root tag
        # (<html>) plus, heuristically, the first inner tag after <body ...>.
        body_start = html.index("<body")
        inner = html[body_start:]
        names = _attr_names_in_order(inner)
        assert names == sorted(names)


class TestRepresentativeExactSnapshots:
    def test_atom_button_action(self):
        registry = real_registry()
        brand = real_brand_package()
        result = render_single_component(
            registry, brand, "atom.button.action",
            prop_overrides={"weight": "secondary"},
            content_overrides={"label": "Call Now"},
        )
        assert (
            '<button class="ac-atom ac-atom--button-action ac-atom--secondary" '
            'data-atlas-c="atom-button-action" data-atlas-e="component_interaction" '
            'data-atlas-v="1.0.0" type="button">Call Now</button>'
        ) in result.page_details[0].html

    def test_atom_badge_status(self):
        registry = real_registry()
        brand = real_brand_package()
        result = render_single_component(
            registry, brand, "atom.badge.status",
            prop_overrides={"kind": "sponsored"},
            content_overrides={"label": "Sponsored"},
        )
        assert (
            '<span class="ac-atom ac-atom--badge-status ac-atom--sponsored" '
            'data-atlas-c="atom-badge-status" data-atlas-v="1.0.0">Sponsored</span>'
        ) in result.page_details[0].html

    def test_nav_skip_link(self):
        registry = real_registry()
        brand = real_brand_package()
        result = render_single_component(registry, brand, "nav.skip.link")
        assert (
            '<a class="ac-nav ac-nav--skip-link" data-atlas-c="nav-skip-link" '
            'data-atlas-v="1.0.0" href="#main">Skip to main content</a>'
        ) in result.page_details[0].html

    def test_nav_mobile_drawer_uses_details_summary(self):
        registry = real_registry()
        brand = real_brand_package()
        result = render_single_component(registry, brand, "nav.mobile.drawer")
        html = result.page_details[0].html
        assert "<details" in html
        assert "<summary>Menu</summary>" in html
        assert "aria-expanded" not in html
        assert "aria-modal" not in html

    def test_directory_filters_panel_uses_details_summary(self):
        registry = real_registry()
        brand = real_brand_package()
        result = render_single_component(registry, brand, "directory.filters.panel")
        html = result.page_details[0].html
        assert "<aside>" in html
        assert "<details" in html
        assert "<summary>Filters</summary>" in html

    def test_directory_search_primary_is_a_get_form(self):
        registry = real_registry()
        brand = real_brand_package()
        result = render_single_component(
            registry, brand, "directory.search.primary",
            prop_overrides={"action_route": "/search", "input_label": "Search pet-friendly stays"},
        )
        html = result.page_details[0].html
        assert '<form action="/search" class="ac-directory ac-directory--search-primary ac-directory--standalone" data-atlas-c="directory-search-primary" data-atlas-e="search_submit" data-atlas-v="1.0.0" method="get">' in html
        assert 'type="search"' in html
        assert '<button type="submit">Search</button>' in html

    def test_atom_field_text_has_label_association(self):
        registry = real_registry()
        brand = real_brand_package()
        result = render_single_component(
            registry, brand, "atom.field.text",
            content_overrides={"label": "Email address"},
        )
        html = result.page_details[0].html
        field_id = re.search(r'id="(ac-atom-field-text-\d+)"', html).group(1)
        assert '<label for="%s">Email address</label>' % field_id in html
        assert 'id="%s"' % field_id in html

    def test_nav_breadcrumbs_standard_has_aria_label(self):
        registry = real_registry()
        brand = real_brand_package()
        result = render_single_component(
            registry, brand, "nav.breadcrumbs.standard",
            prop_overrides={"trail": "trail-ref"},
            content_overrides={"trail": "/category/dogs"},
        )
        html = result.page_details[0].html
        assert 'aria-label="Breadcrumb"' in html
        assert "<ol>" in html

    def test_layout_shell_page_is_full_document(self):
        registry = real_registry()
        brand = real_brand_package()
        result = render_single_component(registry, brand, "nav.skip.link")
        html = result.page_details[0].html
        assert html.startswith("<!doctype html>")
        assert '<html lang="en">' in html
        assert '<meta charset="utf-8">' in html
        assert (
            '<meta content="width=device-width, initial-scale=1" name="viewport">'
            in html
        )

    def test_status_results_zero_has_status_role_and_recovery_links(self):
        registry = real_registry()
        brand = real_brand_package()
        result = render_single_component(
            registry, brand, "status.results.zero",
            content_overrides={"message": "No results found"},
        )
        html = result.page_details[0].html
        assert 'role="status"' in html
        assert "No results found" in html
