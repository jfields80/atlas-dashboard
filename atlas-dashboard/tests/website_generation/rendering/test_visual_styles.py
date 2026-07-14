"""Applied-visual-CSS tests (AES-WEB-002J.15; AES-WEB-001 §8.3;
ADR-WEB-VISUAL-TOKEN-APPLICATION).

Asserts the Renderer now emits real, token-driven, deterministic visual
declarations -- not only a token dump -- by inspecting the shared CSS of a
build that exercises the commercial families, and enforces the ADR's token
discipline (every applied value references a semantic custom property; no raw
literals, external assets, or dangling var references).
"""

from __future__ import annotations

import re

import pytest

from engines.website_generation.rendering.css_emitter import compile_shared_css
from engines.website_generation.rendering.visual_styles import (
    _COMPONENT_RULES,
    _GLOBAL_RULES,
    _RESPONSIVE_RULES,
    compile_visual_styles,
)

from . import (
    make_component_manifest,
    make_content_package,
    make_layout_plan,
    minimal_fixture_for,
    real_brand_package,
    real_registry,
)
from engines.website_generation.contracts.artifacts import (
    ComponentPlacement,
    GridPlacement,
    LayoutRegion,
    PageComponents,
    PageLayout,
    RegionLayoutDetail,
    ResponsiveSelection,
)
from engines.website_generation.contracts.enums import RegionKind
from engines.website_generation.rendering.renderer import Renderer

# A build exercising every commercial family/variant the visual layer styles.
_DEMO_COMPONENTS = (
    ("nav.skip.link", RegionKind.SKIP),
    ("nav.header.standard", RegionKind.HEADER),
    ("monetization.disclosure.advertising", RegionKind.ANNOUNCEMENT),
    ("hero.search.directory", RegionKind.HERO),
    ("directory.categories.grid", RegionKind.BODY),
    ("directory.results.summary", RegionKind.BODY),
    ("monetization.ribbon.sponsor", RegionKind.BODY),
    ("listing.row.compact", RegionKind.BODY),
    ("trust.statistics.strip", RegionKind.BODY),
    ("trust.reviews.summary", RegionKind.BODY),
    ("cta.claim.listing", RegionKind.BODY),
    ("form.lead.quote", RegionKind.BODY),
    ("form.capture.newsletter", RegionKind.BODY),
    ("profile.contact.panel", RegionKind.BODY),
    ("legal.footer.directory", RegionKind.FOOTER),
)


def _rule_bodies(css: str, selector: str) -> str:
    """All rule bodies for an exact selector, joined -- the applied visual
    rule and the (harmless) token-alias rule share a selector, so tests scan
    both."""
    return " ".join(re.findall(re.escape(selector) + r"\{([^}]*)\}", css))


def _demo_css() -> str:
    registry = real_registry()
    brand = real_brand_package()
    instances, blocks, region_map = [], [], {}
    for idx, (cid, region) in enumerate(_DEMO_COMPONENTS):
        inst, cblocks = minimal_fixture_for(registry.get(cid), "/")
        instances.append(inst)
        blocks.extend(cblocks)
        region_map.setdefault(region, []).append(idx)
    regions, details = [], []
    for region, idxs in region_map.items():
        regions.append(LayoutRegion(region_id=region.value, component_indexes=tuple(idxs)))
        details.append(
            RegionLayoutDetail(
                route="/",
                region_id=region.value,
                region_kind=region,
                placements=tuple(
                    ComponentPlacement(component_index=i, grid=GridPlacement(), responsive=ResponsiveSelection())
                    for i in idxs
                ),
            )
        )
    manifest = make_component_manifest(pages=(PageComponents(route="/", components=tuple(instances)),))
    content = make_content_package(blocks=tuple(blocks))
    layout = make_layout_plan(
        pages=(PageLayout(route="/", regions=tuple(regions)),), region_details=tuple(details)
    )
    return Renderer(registry).render(layout, manifest, content, brand).shared_css


@pytest.fixture(scope="module")
def demo_css() -> str:
    return _demo_css()


# --------------------------------------------------------------------------- #
# A. Applied CSS
# --------------------------------------------------------------------------- #

class TestAppliedCss:
    def test_body_has_applied_background_typography_color(self, demo_css):
        body = re.search(r"body\{([^}]*)\}", demo_css).group(1)
        assert "background:var(--color-surface-page)" in body
        assert "color:var(--color-text-default)" in body
        assert "font:var(--typography-body-default)" in body

    def test_links_styled(self, demo_css):
        assert re.search(r"(^|\})a\{[^}]*color:var\(--color-text-link\)", demo_css)

    def test_focus_visible_rule_exists(self, demo_css):
        assert ":focus-visible{" in demo_css
        assert "outline:var(--focus-ring-default) var(--color-focus-ring)" in demo_css

    def test_header_nav_layout_and_surface(self, demo_css):
        rule = _rule_bodies(demo_css, ".ac-nav--header-standard")
        assert "display:flex" in rule
        assert "background:var(--color-surface-raised)" in rule
        assert "border-bottom:var(--border-default) var(--color-border-default)" in rule

    def test_hero_surface_and_spacing(self, demo_css):
        rule = re.search(r"\.ac-hero\{([^}]*)\}", demo_css).group(1)
        assert "background:var(--color-surface-featured)" in rule
        assert "padding:var(--spacing-section-large) var(--spacing-section-small)" in rule

    def test_directory_uses_real_grid_with_tokens(self, demo_css):
        rule = re.search(r"\.ac-directory--categories-grid ul\{([^}]*)\}", demo_css).group(1)
        assert "display:grid" in rule
        assert "grid-template-columns:var(--grid-columns-3)" in rule
        assert "gap:var(--grid-gap-default)" in rule

    def test_listing_row_card_surface(self, demo_css):
        rule = _rule_bodies(demo_css, ".ac-listing--row-compact")
        assert "border:var(--border-default) var(--color-border-default)" in rule
        assert "border-radius:var(--radius-card)" in rule
        assert "box-shadow:var(--shadow-raised)" in rule

    def test_cta_button_treatment_with_states(self, demo_css):
        rule = re.search(r"\.ac-cta--action\{([^}]*)\}", demo_css).group(1)
        assert "background:var(--color-action-primary)" in rule
        assert "color:var(--color-text-inverse)" in rule
        assert "border-radius:var(--radius-control)" in rule
        assert ".ac-cta--action:hover{background:var(--color-action-primary-hover)}" in demo_css
        assert ".ac-cta--action:focus-visible{" in demo_css

    def test_forms_styled(self, demo_css):
        assert re.search(r"\.ac-form--lead-quote[^{]*\{[^}]*border-radius:var\(--radius-card\)", demo_css)
        assert re.search(r"\.ac-form button\{[^}]*background:var\(--color-action-primary\)", demo_css)

    def test_footer_surface(self, demo_css):
        rule = _rule_bodies(demo_css, ".ac-legal--footer-directory")
        assert "background:var(--color-surface-inverse)" in rule
        assert "color:var(--color-text-inverse)" in rule

    def test_skip_link_hidden_until_focus(self, demo_css):
        rule = _rule_bodies(demo_css, ".ac-nav--skip-link")
        assert "left:-9999px" in rule
        assert ".ac-nav--skip-link:focus{left:0}" in demo_css

    def test_sponsor_ribbon_distinct_surface(self, demo_css):
        rule = _rule_bodies(demo_css, ".ac-monetization--ribbon-sponsor")
        assert "background:var(--color-surface-sponsored)" in rule
        assert "border-radius:var(--radius-badge)" in rule


# --------------------------------------------------------------------------- #
# B. Token discipline
# --------------------------------------------------------------------------- #

class TestTokenDiscipline:
    def test_no_raw_hex_outside_root_block(self, demo_css):
        root = re.search(r":root\{[^}]*\}", demo_css).group(0)
        assert not re.findall(r"#[0-9a-fA-F]{3,8}", demo_css.replace(root, ""))

    def test_no_external_assets_or_imports(self, demo_css):
        for banned in ("url(", "http://", "https://", "@import", "@font-face"):
            assert banned not in demo_css

    def test_no_dangling_var_references(self, demo_css):
        # Every var(--x) must have a backing --x: declaration in :root.
        root = re.search(r":root\{([^}]*)\}", demo_css).group(1)
        declared = set(re.findall(r"(--[a-z0-9-]+):", root))
        referenced = set(re.findall(r"var\((--[a-z0-9-]+)\)", demo_css))
        assert referenced <= declared, referenced - declared

    def test_empty_tokens_emit_no_var_references(self):
        # With no tokens, only structural (token-free) declarations may remain
        # -- never a dangling var() reference.
        registry = real_registry()
        definitions = [registry.get(cid) for cid, _ in _DEMO_COMPONENTS]
        assert "var(" not in compile_visual_styles(definitions, {})

    def test_authored_rules_reference_only_real_tokens(self):
        brand = real_brand_package()
        tokens = {}
        for field in ("palette", "type_scale", "spacing_scale", "radius_scale", "extended_tokens"):
            tokens.update(getattr(brand, field))
        all_rules = list(_GLOBAL_RULES) + [(s, d) for _f, s, d in _COMPONENT_RULES] + [
            (s, d) for _f, s, d in _RESPONSIVE_RULES
        ]
        for _selector, declarations in all_rules:
            for _prop, _template, token_ids in declarations:
                for token_id in token_ids:
                    assert token_id in tokens, token_id


# --------------------------------------------------------------------------- #
# C. Responsive
# --------------------------------------------------------------------------- #

class TestResponsive:
    def test_media_query_uses_resolved_breakpoint_value(self, demo_css):
        assert "@media (max-width: 1024px){" in demo_css
        # var() is invalid in a media condition -- must be the resolved value.
        assert "@media (max-width: var(" not in demo_css

    def test_grid_collapses_to_single_column_on_mobile(self, demo_css):
        media = re.search(r"@media \(max-width: 1024px\)\{(.*)\}", demo_css).group(1)
        assert ".ac-directory--categories-grid ul{grid-template-columns:1fr}" in media

    def test_nav_stacks_on_mobile(self, demo_css):
        media = re.search(r"@media \(max-width: 1024px\)\{(.*)\}", demo_css).group(1)
        assert "flex-direction:column" in media

    def test_no_javascript(self, demo_css):
        for banned in ("<script", "javascript:", "onclick", "addEventListener"):
            assert banned not in demo_css


# --------------------------------------------------------------------------- #
# D. Determinism & selector coverage
# --------------------------------------------------------------------------- #

class TestDeterminismAndCoverage:
    def test_visual_styles_deterministic_across_definition_order(self):
        registry = real_registry()
        brand = real_brand_package()
        tokens = {}
        for field in ("palette", "type_scale", "spacing_scale", "radius_scale", "extended_tokens"):
            tokens.update(getattr(brand, field))
        defs = list(registry.all_definitions())
        a = compile_visual_styles(defs, tokens)
        b = compile_visual_styles(list(reversed(defs)), tokens)
        assert a == b

    def test_tree_shaken_absent_family_gets_no_visual_rule(self):
        # A build with only an atom present must not carry hero/cta/etc rules.
        registry = real_registry()
        brand = real_brand_package()
        tokens = {}
        for field in ("palette", "type_scale", "spacing_scale", "radius_scale", "extended_tokens"):
            tokens.update(getattr(brand, field))
        css = compile_visual_styles([registry.get("atom.button.action")], tokens)
        assert ".ac-hero{" not in css
        assert ".ac-cta--action{" not in css

    def test_styled_selectors_match_emitted_markup_classes(self, demo_css):
        # Every component-variant selector the visual layer emits must be a
        # class that appears in the rendered markup for this build.
        registry = real_registry()
        brand = real_brand_package()
        # Render markup and collect emitted classes.
        html_classes = set()
        instances, blocks, region_map = [], [], {}
        for idx, (cid, region) in enumerate(_DEMO_COMPONENTS):
            inst, cblocks = minimal_fixture_for(registry.get(cid), "/")
            instances.append(inst); blocks.extend(cblocks)
            region_map.setdefault(region, []).append(idx)
        regions = [LayoutRegion(region_id=r.value, component_indexes=tuple(i)) for r, i in region_map.items()]
        details = [
            RegionLayoutDetail(route="/", region_id=r.value, region_kind=r,
                placements=tuple(ComponentPlacement(component_index=i, grid=GridPlacement(), responsive=ResponsiveSelection()) for i in idxs))
            for r, idxs in region_map.items()
        ]
        manifest = make_component_manifest(pages=(PageComponents(route="/", components=tuple(instances)),))
        content = make_content_package(blocks=tuple(blocks))
        layout = make_layout_plan(pages=(PageLayout(route="/", regions=tuple(regions)),), region_details=tuple(details))
        rendered = Renderer(registry).render(layout, manifest, content, brand)
        for pd in rendered.page_details:
            for cls in re.findall(r'class="([^"]*)"', pd.html):
                html_classes.update(cls.split())
        # Extract the leading component class from each authored variant selector.
        for _family, selector, _decls in _COMPONENT_RULES:
            head = re.match(r"\.([A-Za-z0-9-]+)", selector).group(1)
            if "--" in head:  # a variant/component class (skip element-only)
                assert head in html_classes, "%s not in emitted markup" % head
