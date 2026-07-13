"""Deterministic demo-site fixture for the Local Demo Website Harness.

    LOCAL DEVELOPMENT / VISUAL DEMO HARNESS FIXTURE
    NOT THE PRODUCTION WEBSITE GENERATION PIPELINE

Internal sequencing label: AES-WEB-002J.13.

This module hand-assembles the five *rendering-ready* artifacts
(``BrandPackage``, ``ContentPackage``, ``SEOPackage``, ``ComponentManifest``,
``LayoutPlan`` -- plus a minimal ``SiteArchitecture`` the Quality Gate reads
for provenance) that the real Renderer -> Assembly -> Quality Gate ->
SiteBundleRepository chain consumes. It is a **Level B** harness input:

* Component **selection** is handcrafted here -- the real Component Engine is
  *not* invoked. Its output is not yet Renderer-consumable because value-layer
  binding is deferred (AES-WEB-001 §5.5; the Renderer requires content/prop
  bindings the Component Engine leaves empty this wave). This harness therefore
  *begins* at fully-bound rendering inputs.
* Content **binding** is handcrafted here -- every required prop and every
  required content slot of every instance is bound to a deterministic value
  derived from the component's own registered contract (the same mechanism the
  Renderer test-suite's ``minimal_fixture_for`` uses, reimplemented locally so
  this module is self-contained and importable by a plain script as well as by
  pytest).
* Certification is **not** granted and blocking gates remain deferred; the
  generated output is for local visual inspection only.

Determinism: no clock, no UUID, no randomness, no environment variables, no
filesystem, no network, no runtime AI. The one artifact derived via a pure
deterministic engine is the ``BrandPackage`` (``BrandEngine().resolve`` of a
fixed inline ``BusinessSpec``): a render-complete design-token set is required
for the Renderer, and hand-enumerating every token the 72-component catalog
references would be fragile and no more honest than deriving them from the
pure, deterministic Brand Engine. Every other artifact is a hand-authored
literal.

Honest known limitations deliberately left visible (not papered over):

* The three ``listing.card.*`` components emit an ``<h3>`` with no
  ``<h2>``-emitting component anywhere in the catalog to bridge the hero's
  ``<h1>``, so a card on any page produces an ``H1 -> H3`` skip that fails the
  evaluated heading-hierarchy gate (CG-CMP-005). To keep the default demo
  gate-clean, listings are shown with ``listing.row.compact`` (which emits no
  heading) plus a ``monetization.ribbon.sponsor`` label for the sponsored one.
  This is a real limitation of the current emitter set, surfaced here rather
  than hidden.
* ``ContentBlock.text`` is opaque, so listing rows / grids / tables show
  resolved placeholder text; forms render a disclosure + submit affordance but
  no field children (no nesting data exists); images emit ``alt=""``; listing
  cards/rows carry no outbound link. These are carried Renderer/Component gaps.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from engines.website_generation.brand.brand_engine import BrandEngine
from engines.website_generation.components.registry import (
    ComponentRegistry,
    build_default_registry,
)
from engines.website_generation.contracts.artifacts import (
    BrandPackage,
    BusinessSpec,
    ComponentInstance,
    ComponentManifest,
    ComponentPlacement,
    ContentBlock,
    ContentPackage,
    GridPlacement,
    LayoutPlan,
    LayoutRegion,
    PageComponents,
    PageLayout,
    RegionLayoutDetail,
    ResponsiveSelection,
    SEOEntry,
    SEOPackage,
    SiteArchitecture,
)
from engines.website_generation.contracts.components import ComponentDefinition
from engines.website_generation.contracts.enums import ArtifactKind, PropType, RegionKind
from engines.website_generation.contracts.versions import SCHEMA_VERSIONS

DEMO_SITE_NAME = "Atlas Local Demo"


@dataclass(frozen=True)
class LocalDemoInputs:
    """The rendering-ready artifacts for one deterministic demo build.

    Repository/harness-local value type -- not a WGE artifact and not a
    registered schema. ``site_architecture`` is a minimal header-only artifact
    the Quality Gate Engine reads only for provenance hashing.
    """

    brand: BrandPackage
    content: ContentPackage
    seo: SEOPackage
    manifest: ComponentManifest
    layout: LayoutPlan
    site_architecture: SiteArchitecture
    routes: Tuple[str, ...]


# --------------------------------------------------------------------------- #
# Deterministic per-contract binding (local reimplementation of the Renderer
# suite's ``minimal_fixture_for`` -- kept here so this module has no test-only
# import and can be loaded by a plain script via file path).
# --------------------------------------------------------------------------- #

def _sample_prop_value(prop_spec, name: str) -> str:
    """A deterministic, contract-valid sample for any ``PropSpec`` (the same
    per-``PropType`` rule the Renderer suite's ``sample_prop_value`` uses)."""
    pt = prop_spec.prop_type
    if pt is PropType.STR_ENUM:
        return prop_spec.enum_values[0] if prop_spec.enum_values else name
    if pt is PropType.BOOL:
        return "false"
    if pt is PropType.INT_BOUNDED:
        return str(prop_spec.int_min if prop_spec.int_min is not None else 1)
    if pt is PropType.CONTENT_BLOCK_REF:
        return "ref-" + name
    if pt is PropType.ROUTE_REF:
        return "/target"
    if pt is PropType.ASSET_REF:
        return "/assets/x.png"
    if pt is PropType.A11Y_LABEL:
        return "Accessible label"
    return name


def _bind(
    definition: ComponentDefinition,
    route: str,
    content_overrides: Optional[Dict[str, str]] = None,
) -> Tuple[ComponentInstance, Tuple[ContentBlock, ...]]:
    """A contract-valid ``(ComponentInstance, content blocks)`` pair: every
    required prop bound to a deterministic sample, every required content slot
    (and every ``CONTENT_BLOCK_REF``/``LISTING_REF`` prop) bound to a resolvable
    ``ContentBlock``. ``content_overrides`` (keyed by prop or slot name) supply
    human-meaningful demo copy in place of the generated placeholder."""
    overrides = content_overrides or {}
    props: Dict[str, str] = {}
    blocks: List[ContentBlock] = []
    for name, spec in definition.required_props.items():
        value = _sample_prop_value(spec, name)
        props[name] = value
        if spec.prop_type in (PropType.CONTENT_BLOCK_REF, PropType.LISTING_REF):
            blocks.append(
                ContentBlock(
                    page_route=route,
                    slot_id=value,
                    text=overrides.get(name, "Resolved %s" % name),
                )
            )
    content_refs: List[str] = []
    for slot_id in definition.required_content_slots:
        content_refs.append(slot_id)
        blocks.append(
            ContentBlock(
                page_route=route,
                slot_id=slot_id,
                text=overrides.get(slot_id, "Resolved %s" % slot_id),
            )
        )
    instance = ComponentInstance(
        component_id=definition.component_id,
        component_version=definition.component_version,
        props=props,
        content_refs=tuple(content_refs),
    )
    return instance, tuple(blocks)


# --------------------------------------------------------------------------- #
# The demo site: (component_id, region, content overrides) per route.
# Every component is a registered, PROPOSED catalog component. Listings use
# ``listing.row.compact`` (no heading) rather than ``listing.card.*`` (H3, see
# module docstring) so the default build is heading-hierarchy clean.
# --------------------------------------------------------------------------- #

_R = RegionKind
_FOOTER = (
    "legal.footer.directory",
    _R.FOOTER,
    {"legal_facts": "(c) 2026 Atlas Local Demo", "disclosures": "Affiliate disclosures apply."},
)
_SPONSOR_DISCLOSURE = (
    "monetization.disclosure.advertising",
    _R.ANNOUNCEMENT,
    {"disclosure": "Some listings are sponsored. Sponsored placements are labeled."},
)

# Canonical region emission order (skip link first, footer last).
_REGION_ORDER: Tuple[RegionKind, ...] = (
    _R.SKIP,
    _R.ANNOUNCEMENT,
    _R.HEADER,
    _R.BREADCRUMB,
    _R.HERO,
    _R.BODY,
    _R.STICKY_MOBILE,
    _R.FOOTER,
)

_PAGES: "Dict[str, List[Tuple[str, RegionKind, Dict[str, str]]]]" = {
    "/": [
        ("nav.skip.link", _R.SKIP, {}),
        ("nav.header.standard", _R.HEADER, {}),
        _SPONSOR_DISCLOSURE,
        ("hero.search.directory", _R.HERO, {
            "h1": "Find pet-friendly places to stay",
            "subhead": "Verified hotels, parks, and restaurants that welcome pets.",
        }),
        ("content.intro.contextual", _R.BODY, {
            "intro": "Browse trusted, pet-welcoming businesses across the country.",
        }),
        ("directory.categories.grid", _R.BODY, {"category_tiles": "Hotels, Parks, Restaurants"}),
        ("monetization.ribbon.sponsor", _R.BODY, {"label": "Sponsored"}),
        ("listing.row.compact", _R.BODY, {}),
        ("listing.row.compact", _R.BODY, {}),
        ("trust.statistics.strip", _R.BODY, {"statistics": "1,200 verified listings across 48 states"}),
        ("cta.claim.listing", _R.BODY, {"label": "Own a business? Claim your listing"}),
        _FOOTER,
    ],
    "/hotels/": [
        ("nav.skip.link", _R.SKIP, {}),
        ("nav.header.standard", _R.HEADER, {}),
        _SPONSOR_DISCLOSURE,
        ("hero.local.standard", _R.HERO, {
            "h1": "Pet-friendly hotels",
            "intro": "Stays that welcome dogs and cats.",
        }),
        ("directory.results.summary", _R.BODY, {"summary_text": "Showing 24 pet-friendly hotels"}),
        ("monetization.ribbon.sponsor", _R.BODY, {"label": "Sponsored"}),
        ("listing.row.compact", _R.BODY, {}),
        ("listing.row.compact", _R.BODY, {}),
        ("listing.row.compact", _R.BODY, {}),
        ("trust.reviews.summary", _R.BODY, {"rating_summary": "4.6 average from 900 reviews"}),
        _FOOTER,
    ],
    "/hotels/lakeview-lodge/": [
        ("nav.skip.link", _R.SKIP, {}),
        ("nav.header.standard", _R.HEADER, {}),
        ("hero.local.standard", _R.HERO, {
            "h1": "Lakeview Lodge",
            "intro": "A lakeside lodge that welcomes pets.",
        }),
        ("content.description.business", _R.BODY, {
            "description": "A lakeside lodge with fenced runs and on-site pet-sitting.",
        }),
        ("profile.hours.table", _R.BODY, {"hours": "Mon-Sun, 8am to 8pm"}),
        ("profile.contact.panel", _R.BODY, {"contact_info": "(555) 0100 - stay@lakeview.example"}),
        ("cta.claim.listing", _R.BODY, {"label": "Is this your business? Claim it"}),
        _FOOTER,
    ],
    "/about/": [
        ("nav.skip.link", _R.SKIP, {}),
        ("nav.header.standard", _R.HEADER, {}),
        ("hero.local.standard", _R.HERO, {
            "h1": "About Atlas Local Demo",
            "intro": "How we verify pet-friendly businesses.",
        }),
        ("content.section.editorial", _R.BODY, {
            "body": "We independently check pet policies before listing a business.",
        }),
        ("content.faq.standard", _R.BODY, {
            "qa_pairs": "Is this a real directory? No - it is a local demonstration site.",
        }),
        ("trust.statistics.strip", _R.BODY, {"statistics": "1,200 listings, 48 states, 900 reviews"}),
        _FOOTER,
    ],
    "/contact/": [
        ("nav.skip.link", _R.SKIP, {}),
        ("nav.header.standard", _R.HEADER, {}),
        ("hero.local.standard", _R.HERO, {
            "h1": "Contact us",
            "intro": "Questions about a listing? Get in touch.",
        }),
        ("form.lead.quote", _R.BODY, {"disclosure": "By submitting you agree to be contacted."}),
        ("form.capture.newsletter", _R.BODY, {"label": "Subscribe to pet-travel tips"}),
        ("profile.contact.panel", _R.BODY, {"contact_info": "hello@atlas-local-demo.example"}),
        _FOOTER,
    ],
}


def _brand_package() -> BrandPackage:
    """A render-complete ``BrandPackage`` from the pure, deterministic Brand
    Engine (fixed inline spec; see module docstring for why this one artifact
    is engine-derived rather than a hand-enumerated token literal)."""
    spec = BusinessSpec(
        schema_version=SCHEMA_VERSIONS[ArtifactKind.BUSINESS_SPEC],
        artifact_kind=ArtifactKind.BUSINESS_SPEC,
        source_hashes={},
        business_name="Atlas Local Demo",
        niche="pet travel",
        audience="pet owners",
        value_proposition="find pet-friendly places",
    )
    return BrandEngine().resolve(spec)


def demo_registry() -> ComponentRegistry:
    """The real 72-component MVP catalog the harness renders against (the same
    instance is used by both the Renderer and any layout composition)."""
    return build_default_registry()


def build_local_demo_inputs() -> LocalDemoInputs:
    """Build the deterministic five (+1) rendering/gate artifacts for the
    ``Atlas Local Demo`` site. Pure: same output on every call, no I/O."""
    registry = demo_registry()
    manifest_pages: List[PageComponents] = []
    layout_pages: List[PageLayout] = []
    region_details: List[RegionLayoutDetail] = []
    blocks: List[ContentBlock] = []
    seo_entries: List[SEOEntry] = []
    routes = tuple(_PAGES.keys())

    for route, components in _PAGES.items():
        instances: List[ComponentInstance] = []
        region_indexes: Dict[RegionKind, List[int]] = {}
        for index, (component_id, region, overrides) in enumerate(components):
            definition = registry.get(component_id)
            instance, instance_blocks = _bind(definition, route, overrides or None)
            instances.append(instance)
            blocks.extend(instance_blocks)
            region_indexes.setdefault(region, []).append(index)

        regions: List[LayoutRegion] = []
        details: List[RegionLayoutDetail] = []
        for region_kind in _REGION_ORDER:
            if region_kind not in region_indexes:
                continue
            indexes = tuple(region_indexes[region_kind])
            regions.append(
                LayoutRegion(region_id=region_kind.value, component_indexes=indexes)
            )
            details.append(
                RegionLayoutDetail(
                    route=route,
                    region_id=region_kind.value,
                    region_kind=region_kind,
                    placements=tuple(
                        ComponentPlacement(
                            component_index=i,
                            grid=GridPlacement(),
                            responsive=ResponsiveSelection(),
                        )
                        for i in indexes
                    ),
                )
            )

        manifest_pages.append(PageComponents(route=route, components=tuple(instances)))
        layout_pages.append(PageLayout(route=route, regions=tuple(regions)))
        region_details.extend(details)
        seo_entries.append(
            SEOEntry(
                route=route,
                title="%s - %s" % (DEMO_SITE_NAME, route),
                meta_description="Pet-friendly directory demo page for %s" % route,
                canonical_url=route,
            )
        )

    brand = _brand_package()
    content = ContentPackage(
        schema_version=SCHEMA_VERSIONS[ArtifactKind.CONTENT_PACKAGE],
        artifact_kind=ArtifactKind.CONTENT_PACKAGE,
        source_hashes={},
        blocks=tuple(blocks),
    )
    seo = SEOPackage(
        schema_version=SCHEMA_VERSIONS[ArtifactKind.SEO_PACKAGE],
        artifact_kind=ArtifactKind.SEO_PACKAGE,
        source_hashes={},
        entries=tuple(seo_entries),
        sitemap_routes=routes,
        robots_directives=("User-agent: *", "Allow: /"),
    )
    manifest = ComponentManifest(
        schema_version=SCHEMA_VERSIONS[ArtifactKind.COMPONENT_MANIFEST],
        artifact_kind=ArtifactKind.COMPONENT_MANIFEST,
        source_hashes={},
        pages=tuple(manifest_pages),
    )
    layout = LayoutPlan(
        schema_version=SCHEMA_VERSIONS[ArtifactKind.LAYOUT_PLAN],
        artifact_kind=ArtifactKind.LAYOUT_PLAN,
        source_hashes={},
        pages=tuple(layout_pages),
        region_details=tuple(region_details),
    )
    site_architecture = SiteArchitecture(
        schema_version=SCHEMA_VERSIONS[ArtifactKind.SITE_ARCHITECTURE],
        artifact_kind=ArtifactKind.SITE_ARCHITECTURE,
        source_hashes={},
    )
    return LocalDemoInputs(
        brand=brand,
        content=content,
        seo=seo,
        manifest=manifest,
        layout=layout,
        site_architecture=site_architecture,
        routes=routes,
    )
