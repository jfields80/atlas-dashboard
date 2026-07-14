"""Component-field -> semantic-slot binding map (AES-WEB-002J.18;
ADR-WEB-CONTENT-BINDING-MAP).

The explicit, deterministic table telling the future Component Engine Phase-B
binder (AES-WEB-001 §5.5) how each component's *own* declared field names map
onto the canonical semantic vocabulary (``constants/content_slots.py``) and
which source rule fills them. This module is declarative data only: it
performs no binding, imports no Renderer/emitter, and mutates nothing.

Coverage (validated by ``binding_map_validator``): every required content
slot, every required ``CONTENT_BLOCK_REF`` prop, every required
``LISTING_REF`` prop, and every required literal prop
(``STR_ENUM``/``INT_BOUNDED``/``BOOL``/``ROUTE_REF``/``ASSET_REF``/
``TOKEN_REF``/``A11Y_LABEL``) across all 72 catalog components is mapped -- so
the map is total and cannot silently drift from the registry.

Honesty rules (ADR): a field whose declared block type flat
``ContentBlock.text`` cannot represent is ``STRUCTURED_DEFERRED``; a field
with a real source but only an honest one-string projection is
``FLAT_PROJECTION_ONLY``; a field with no producing artifact is
``SOURCE_UNAVAILABLE``. No placeholder or ``"Resolved ..."`` source ever
appears here.
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Tuple

from engines.website_generation.constants.content_slots import SEMANTIC_SLOTS


class FieldKind(str, Enum):
    """Which kind of component field a rule binds."""

    CONTENT_SLOT = "CONTENT_SLOT"          # required/optional content slot
    PROP_REF = "PROP_REF"                  # CONTENT_BLOCK_REF / LISTING_REF prop
    PROP_LITERAL = "PROP_LITERAL"          # STR_ENUM/INT/BOOL/ROUTE/ASSET/TOKEN/A11Y prop


class BindingState(str, Enum):
    """How completely a field can be bound today (ADR "four binding states",
    extended to five by AES-WEB-002K.1)."""

    FULLY_BINDABLE = "FULLY_BINDABLE"
    FLAT_PROJECTION_ONLY = "FLAT_PROJECTION_ONLY"
    # AES-WEB-002K.1: a field whose real, honest representation requires a
    # link (label + href) or other structure flat ContentBlock.text cannot
    # carry, but which the render-data producer (component_engine.py's
    # Phase B, via contracts/render_data.py) now genuinely supplies --
    # distinct from FULLY_BINDABLE (never a flat-text projection) and from
    # STRUCTURED_DEFERRED (never a fabricated string; a real structured
    # producer exists).
    RENDER_DATA = "RENDER_DATA"
    STRUCTURED_DEFERRED = "STRUCTURED_DEFERRED"
    SOURCE_UNAVAILABLE = "SOURCE_UNAVAILABLE"


# The "semantic slot" for a literal prop is the empty string: a literal prop
# resolves to a value string (an enum member, an int, a route, a token id),
# never to a ContentPackage content slot. ``source_rule`` documents where the
# literal comes from.
_LITERAL = ""


@dataclass(frozen=True)
class BindingRule:
    """One component field's mapping to a source.

    ``semantic_slot`` names an entry in ``SEMANTIC_SLOTS`` for content slots
    and prop-refs, or ``""`` for literal props. ``expected_type`` is the
    component field's declared ``block_type`` (content slots) or ``PropType``
    value (props). ``source_rule`` is a stable human-readable derivation id
    (documentation/test anchor, never parsed at runtime).
    """

    component_id: str
    field_kind: FieldKind
    field_name: str
    semantic_slot: str
    expected_type: str
    required: bool
    binding_state: BindingState
    source_rule: str
    note: str = ""


def _cs(cid, field, semantic, block_type, state, source_rule, note="", required=True) -> BindingRule:
    return BindingRule(cid, FieldKind.CONTENT_SLOT, field, semantic, block_type,
                       required, state, source_rule, note)


def _ref(cid, field, semantic, prop_type, state, source_rule, note="", required=True) -> BindingRule:
    return BindingRule(cid, FieldKind.PROP_REF, field, semantic, prop_type,
                       required, state, source_rule, note)


def _lit(cid, field, prop_type, source_rule, state=BindingState.FULLY_BINDABLE, required=True) -> BindingRule:
    return BindingRule(cid, FieldKind.PROP_LITERAL, field, _LITERAL, prop_type,
                       required, state, source_rule)


_FULL = BindingState.FULLY_BINDABLE
_FLAT = BindingState.FLAT_PROJECTION_ONLY
_RENDER = BindingState.RENDER_DATA
_DEFER = BindingState.STRUCTURED_DEFERRED
_UNAVAIL = BindingState.SOURCE_UNAVAILABLE

# Source rules for the literal-prop families (Phase-B binding responsibility).
_R_ENUM = "prop:str_enum_default_or_role"     # enum_values[0], or hosting role for *_role
_R_INT = "prop:int_bounded_min"               # int_min (or default)
_R_BOOL = "prop:bool_default"                 # default
_R_ROUTE = "SiteArchitecture:route"           # a route that must exist in SiteArchitecture (§8.1)
_R_TOKEN = "BrandPackage:token_id"            # a semantic token id present in BrandPackage
_R_A11Y = "derive:accessible_label"           # deterministic literal accessible label
_R_ASSET_UNAVAIL = "unavailable:asset_store"  # no asset artifact wired yet


_RULES: Tuple[BindingRule, ...] = (
    # ===================== atoms =====================
    _cs("atom.alert.notice", "body", "inline_body", "RichTextBlock", _FULL, "ContentPackage:body"),
    _lit("atom.alert.notice", "severity", "STR_ENUM", _R_ENUM),
    _cs("atom.badge.status", "label", "inline_label", "RichTextBlock", _FULL, "ContentPackage:label"),
    _lit("atom.badge.status", "kind", "STR_ENUM", _R_ENUM),
    _cs("atom.button.action", "label", "inline_label", "RichTextBlock", _FULL, "ContentPackage:label"),
    _lit("atom.button.action", "weight", "STR_ENUM", _R_ENUM),
    _cs("atom.field.choice", "legend", "field_legend", "RichTextBlock", _FULL, "ContentPackage:legend"),
    _cs("atom.field.choice", "error", "field_error", "RichTextBlock", _FULL, "ContentPackage:error"),
    _ref("atom.field.choice", "options", "field_options", "CONTENT_BLOCK_REF", _UNAVAIL,
         "unavailable:field_options", "no choice-option source artifact exists yet"),
    _lit("atom.field.choice", "mode", "STR_ENUM", _R_ENUM),
    _cs("atom.field.select", "label", "inline_label", "RichTextBlock", _FULL, "ContentPackage:label"),
    _cs("atom.field.select", "error", "field_error", "RichTextBlock", _FULL, "ContentPackage:error"),
    _ref("atom.field.select", "options", "field_options", "CONTENT_BLOCK_REF", _UNAVAIL,
         "unavailable:field_options", "no select-option source artifact exists yet"),
    _lit("atom.field.select", "required", "BOOL", _R_BOOL),
    _cs("atom.field.text", "label", "inline_label", "RichTextBlock", _FULL, "ContentPackage:label"),
    _cs("atom.field.text", "error", "field_error", "RichTextBlock", _FULL, "ContentPackage:error"),
    _lit("atom.field.text", "input_kind", "STR_ENUM", _R_ENUM),
    _lit("atom.field.text", "autocomplete", "STR_ENUM", _R_ENUM),
    _lit("atom.field.text", "required", "BOOL", _R_BOOL),
    _lit("atom.icon.standard", "asset", "ASSET_REF", _R_ASSET_UNAVAIL, _UNAVAIL),
    _lit("atom.icon.standard", "size", "TOKEN_REF", _R_TOKEN),
    _lit("atom.image.responsive", "asset", "ASSET_REF", _R_ASSET_UNAVAIL, _UNAVAIL),
    _lit("atom.image.responsive", "aspect", "TOKEN_REF", _R_TOKEN),
    _lit("atom.image.responsive", "loading", "STR_ENUM", _R_ENUM),
    _ref("atom.link.standard", "link", "inline_link", "CONTENT_BLOCK_REF", _DEFER,
         "SiteArchitecture:route+title", "LinkSpec label+href not representable by flat ContentBlock"),
    # ===================== commerce =====================
    _cs("commerce.pricing.sponsorship", "pricing", "pricing_disclaimer", "PriceSpec", _UNAVAIL,
        "unavailable:pricing", "PriceSpec is structured and has no source artifact yet"),
    _cs("commerce.pricing.sponsorship", "disclaimer", "disclaimer_text", "RichTextBlock", _FULL,
        "ContentPackage:disclaimer"),
    # ===================== content =====================
    _cs("content.description.business", "description", "listing_description", "RichTextBlock", _FULL,
        "ListingRecord.description"),
    _cs("content.faq.standard", "qa_pairs", "qa_pairs", "QAPair", _UNAVAIL,
        "unavailable:qa_pairs", "QAPair is structured (Q/A) and has no source artifact yet"),
    _cs("content.intro.contextual", "intro", "page_intro", "RichTextBlock", _FULL, "ContentPackage:intro"),
    _lit("content.intro.contextual", "context_role", "STR_ENUM", _R_ENUM),
    _cs("content.resources.grid", "resources", "resource_links", "LinkSpec", _DEFER,
        "SiteArchitecture:routes+titles", "LinkSpec label+href not representable by flat ContentBlock"),
    _cs("content.section.editorial", "body", "page_body", "RichTextBlock", _FULL, "ContentPackage:body"),
    _cs("content.table.comparison", "table", "comparison_table", "ComparisonTableBlock", _UNAVAIL,
        "unavailable:comparison_table", "ComparisonTableBlock is structured and has no source artifact yet"),
    _ref("content.toc.standard", "heading_refs", "heading_refs", "CONTENT_BLOCK_REF", _DEFER,
         "derive:page_headings+anchors", "TOC anchors are LinkSpec-shaped, not flat text"),
    # ===================== cta =====================
    _cs("cta.claim.listing", "label", "inline_label", "RichTextBlock", _FULL, "ContentPackage:label"),
    _lit("cta.claim.listing", "target_route", "ROUTE_REF", _R_ROUTE),
    _cs("cta.sponsor.inquiry", "label", "inline_label", "RichTextBlock", _FULL, "ContentPackage:label"),
    _lit("cta.sponsor.inquiry", "target_route", "ROUTE_REF", _R_ROUTE),
    _lit("cta.sticky.mobile", "goal", "STR_ENUM", _R_ENUM),
    _lit("cta.sticky.mobile", "target_route", "ROUTE_REF", _R_ROUTE),
    _cs("cta.submit.listing", "label", "inline_label", "RichTextBlock", _FULL, "ContentPackage:label"),
    _lit("cta.submit.listing", "target_route", "ROUTE_REF", _R_ROUTE),
    # ===================== directory =====================
    # AES-WEB-002K.1/PILOT-PTF-1: real tile links (label+href per launched
    # category) now flow through the render-data producer
    # (component_engine._build_category_tiles), the same TileLinks contract
    # K.1 declared but left unwired -- the home page's category-discovery
    # grid was the only remaining always-empty required slot.
    _cs("directory.categories.grid", "category_tiles", "category_tiles", "LinkSpec", _RENDER,
        "SiteArchitecture.pages (category routes+titles)", "real tile label+href via render-data"),
    _ref("directory.categories.grid", "category_source_ref", "category_tiles", "CONTENT_BLOCK_REF", _RENDER,
         "SiteArchitecture.pages (category routes+titles)", "resolves the category tile source (render-data)"),
    _lit("directory.categories.grid", "columns", "INT_BOUNDED", _R_INT),
    _ref("directory.filters.panel", "facet_set_ref", "facet_options", "CONTENT_BLOCK_REF", _UNAVAIL,
         "unavailable:facets", "no facet source artifact exists yet"),
    _cs("directory.locations.grid", "location_tiles", "location_tiles", "LinkSpec", _DEFER,
        "ListingDataset.locations+routes", "tile label+href not representable by flat ContentBlock"),
    _ref("directory.locations.grid", "location_source_ref", "location_tiles", "CONTENT_BLOCK_REF", _DEFER,
         "ListingDataset.locations+routes", "resolves the location tile source (structured)"),
    _cs("directory.results.summary", "summary_text", "result_summary", "RichTextBlock", _FULL,
        "derive:result_count", "deterministic count string from ListingDataset filtered by route"),
    _lit("directory.search.primary", "action_route", "ROUTE_REF", _R_ROUTE),
    _lit("directory.search.primary", "scope", "STR_ENUM", _R_ENUM),
    _lit("directory.search.primary", "input_label", "A11Y_LABEL", _R_A11Y),
    _ref("directory.sort.control", "sort_options_ref", "sort_options", "CONTENT_BLOCK_REF", _UNAVAIL,
         "unavailable:sort_options", "no sort-option source artifact exists yet"),
    # ===================== forms =====================
    _cs("form.capture.newsletter", "label", "inline_label", "RichTextBlock", _FULL, "ContentPackage:label"),
    _lit("form.capture.newsletter", "action_route", "ROUTE_REF", _R_ROUTE),
    _ref("form.claim.standard", "listing_ref", "listing_name", "LISTING_REF", _FLAT,
         "ListingRecord.business_name", "binds one listing; full record is structured"),
    _lit("form.claim.standard", "action_route", "ROUTE_REF", _R_ROUTE),
    _ref("form.correction.standard", "listing_ref", "listing_name", "LISTING_REF", _FLAT,
         "ListingRecord.business_name", "binds one listing; full record is structured"),
    _lit("form.correction.standard", "action_route", "ROUTE_REF", _R_ROUTE),
    _cs("form.lead.quote", "disclosure", "form_disclosure", "DisclosureBlock", _FULL,
        "ContentPackage:disclosure"),
    _lit("form.lead.quote", "action_route", "ROUTE_REF", _R_ROUTE),
    _cs("form.submission.listing", "standards_link", "standards_link", "LinkSpec", _DEFER,
        "SiteArchitecture:route+title", "LinkSpec label+href not representable by flat ContentBlock"),
    _lit("form.submission.listing", "action_route", "ROUTE_REF", _R_ROUTE),
    # ===================== hero =====================
    _cs("hero.local.standard", "h1", "page_h1", "RichTextBlock", _FULL, "ContentPackage:hero_h1"),
    _cs("hero.local.standard", "intro", "page_intro", "RichTextBlock", _FULL, "ContentPackage:intro"),
    _lit("hero.local.standard", "context_role", "STR_ENUM", _R_ENUM),
    _cs("hero.search.directory", "h1", "page_h1", "RichTextBlock", _FULL, "ContentPackage:hero_h1"),
    _cs("hero.search.directory", "subhead", "page_subhead", "RichTextBlock", _FULL, "ContentPackage:subhead"),
    # ===================== layout =====================
    _lit("layout.card.shell", "surface", "TOKEN_REF", _R_TOKEN),
    _lit("layout.card.shell", "radius", "TOKEN_REF", _R_TOKEN),
    _lit("layout.grid.standard", "columns", "STR_ENUM", _R_ENUM),
    _lit("layout.grid.standard", "gap", "TOKEN_REF", _R_TOKEN),
    _lit("layout.section.container", "width", "TOKEN_REF", _R_TOKEN),
    _lit("layout.section.container", "section_spacing", "TOKEN_REF", _R_TOKEN),
    _lit("layout.shell.page", "page_role", "STR_ENUM", _R_ENUM),
    _lit("layout.split.standard", "ratio", "STR_ENUM", _R_ENUM),
    _lit("layout.split.standard", "mobile_order", "STR_ENUM", _R_ENUM),
    _lit("layout.stack.standard", "gap", "TOKEN_REF", _R_TOKEN),
    # ===================== legal =====================
    _cs("legal.footer.directory", "legal_facts", "footer_legal_text", "RichTextBlock", _FULL,
        "ContentPackage:footer_legal", "AES-WEB-002K.1: repointed from the BUSINESS_SPEC-sourced "
        "legal_text slot (unreachable -- compile() takes no BusinessSpec input, D5) to an "
        "explicit ContentPackage block"),
    _cs("legal.footer.directory", "disclosures", "footer_disclosures", "DisclosureBlock", _FULL,
        "ContentPackage:disclosures"),
    _ref("legal.footer.directory", "nav_tree", "footer_navigation", "CONTENT_BLOCK_REF", _RENDER,
         "RenderData:footer_navigation", "AES-WEB-002K.1: footer nav label+href now produced by "
         "the render-data producer (component_engine.py Phase B)"),
    _cs("legal.statement.standard", "body", "inline_body", "RichTextBlock", _FULL, "ContentPackage:body"),
    _lit("legal.statement.standard", "kind", "STR_ENUM", _R_ENUM),
    # ===================== listing =====================
    _cs("listing.card.featured", "disclosure", "listing_disclosure", "DisclosureBlock", _FULL,
        "ListingRecord.sponsorship.disclosure_text"),
    _ref("listing.card.featured", "listing_ref", "listing_name", "LISTING_REF", _FLAT,
         "ListingRecord.business_name", "card renders one heading; full record is structured"),
    _cs("listing.card.sponsored", "disclosure", "listing_disclosure", "DisclosureBlock", _FULL,
        "ListingRecord.sponsorship.disclosure_text"),
    _ref("listing.card.sponsored", "listing_ref", "listing_name", "LISTING_REF", _FLAT,
         "ListingRecord.business_name", "card renders one heading; full record is structured"),
    _ref("listing.card.standard", "listing_ref", "listing_name", "LISTING_REF", _FLAT,
         "ListingRecord.business_name", "card renders one heading; full record is structured"),
    _lit("listing.card.standard", "density", "STR_ENUM", _R_ENUM),
    _ref("listing.row.compact", "listing_ref", "listing_name", "LISTING_REF", _FLAT,
         "ListingRecord.business_name", "row renders one label; full record is structured"),
    # ===================== monetization =====================
    _cs("monetization.disclosure.advertising", "disclosure", "sponsorship_disclosure", "DisclosureBlock", _FULL,
        "ListingRecord.sponsorship.disclosure_text or constants default"),
    _lit("monetization.disclosure.advertising", "disclosure_kind", "STR_ENUM", _R_ENUM),
    _cs("monetization.prompt.upgrade", "offer", "offer_text", "RichTextBlock", _FULL, "ContentPackage:offer"),
    _cs("monetization.prompt.upgrade", "disclosure", "sponsorship_disclosure", "DisclosureBlock", _FULL,
        "ListingRecord.sponsorship.disclosure_text or constants default"),
    _cs("monetization.ribbon.sponsor", "label", "inline_label", "RichTextBlock", _FULL, "ContentPackage:label"),
    _cs("monetization.section.premium-profile", "premium_blocks", "premium_blocks", "RichTextBlock", _FULL,
        "ContentPackage:premium_blocks"),
    # ===================== nav =====================
    _ref("nav.breadcrumbs.standard", "trail", "breadcrumb_trail", "CONTENT_BLOCK_REF", _DEFER,
         "SiteArchitecture:breadcrumb_routes+titles", "breadcrumb label+href not representable by flat ContentBlock"),
    _ref("nav.header.standard", "nav_tree", "primary_navigation", "CONTENT_BLOCK_REF", _RENDER,
         "RenderData:primary_navigation", "AES-WEB-002K.1: header nav label+href now produced by "
         "the render-data producer (component_engine.py Phase B)"),
    _ref("nav.mobile.drawer", "nav_tree", "primary_navigation", "CONTENT_BLOCK_REF", _DEFER,
         "SiteArchitecture:nav_routes+titles", "drawer nav label+href not representable by flat ContentBlock"),
    _ref("nav.pagination.standard", "page_context", "pagination_context", "CONTENT_BLOCK_REF", _UNAVAIL,
         "unavailable:pagination", "no pagination-context source artifact exists yet"),
    _cs("nav.utility.bar", "message", "status_message", "RichTextBlock", _FULL, "ContentPackage:message"),
    # ===================== profile =====================
    _cs("profile.areas.served", "area_links", "service_area_links", "LinkSpec", _DEFER,
        "SiteArchitecture:service_area_routes+titles", "area label+href not representable by flat ContentBlock"),
    _cs("profile.contact.panel", "contact_info", "listing_contact", "ContactSpec", _FLAT,
        "ListingRecord.contact+address", "one NAP string; tel:/mailto: links deferred"),
    _cs("profile.credentials.list", "credentials", "listing_credentials", "CredentialBlock", _FLAT,
        "ListingRecord.credentials", "flat credential lines; structured issuer/evidence deferred"),
    _cs("profile.gallery.standard", "images", "listing_gallery", "AssetRef", _DEFER,
        "ListingRecord.assets", "AssetRef media is structured and needs an asset store to resolve"),
    _cs("profile.header.business", "name", "listing_name", "RichTextBlock", _FULL,
        "ListingRecord.business_name"),
    _ref("profile.header.business", "listing_ref", "listing_name", "LISTING_REF", _FLAT,
         "ListingRecord.business_name", "identifies the listing; full record is structured"),
    _cs("profile.hours.table", "hours", "listing_hours", "HoursSpec", _FLAT,
        "ListingRecord.hours", "one schedule string; per-day rows deferred"),
    _cs("profile.map.directions", "location", "listing_location", "GeoSpec", _DEFER,
        "ListingRecord.geo+address", "GeoSpec coordinates not representable by flat text"),
    _cs("profile.map.directions", "directions_text", "directions_text", "RichTextBlock", _FULL,
        "ContentPackage:directions_text"),
    _ref("profile.map.directions", "listing_ref", "listing_name", "LISTING_REF", _FLAT,
         "ListingRecord.business_name", "identifies the listing; full record is structured"),
    # ===================== seo =====================
    _cs("seo.local-links.categories", "category_links", "category_tiles", "LinkSpec", _DEFER,
        "ListingDataset.categories+routes", "SEO category links label+href not representable by flat ContentBlock"),
    _ref("seo.local-links.categories", "category_source_ref", "category_tiles", "CONTENT_BLOCK_REF", _DEFER,
         "ListingDataset.categories+routes", "resolves the SEO category-link source (structured)"),
    _cs("seo.local-links.cities", "city_links", "location_tiles", "LinkSpec", _DEFER,
        "ListingDataset.locations+routes", "SEO city links label+href not representable by flat ContentBlock"),
    _ref("seo.local-links.cities", "city_source_ref", "location_tiles", "CONTENT_BLOCK_REF", _DEFER,
         "ListingDataset.locations+routes", "resolves the SEO city-link source (structured)"),
    # ===================== status =====================
    _cs("status.banner.notification", "body", "inline_body", "RichTextBlock", _FULL, "ContentPackage:body"),
    _lit("status.banner.notification", "severity", "STR_ENUM", _R_ENUM),
    _cs("status.listing.pending", "message", "status_message", "RichTextBlock", _FULL, "ContentPackage:message"),
    _cs("status.listing.pending", "expectation_text", "expectation_text", "RichTextBlock", _FULL,
        "ContentPackage:expectation_text"),
    _cs("status.listing.unavailable", "message", "status_message", "RichTextBlock", _FULL, "ContentPackage:message"),
    _cs("status.listing.unavailable", "recovery_links", "recovery_links", "LinkSpec", _DEFER,
        "SiteArchitecture:recovery_routes+titles", "recovery label+href not representable by flat ContentBlock"),
    _lit("status.listing.unavailable", "reason", "STR_ENUM", _R_ENUM),
    _cs("status.results.zero", "message", "status_message", "RichTextBlock", _FULL, "ContentPackage:message"),
    _cs("status.results.zero", "recovery_links", "recovery_links", "LinkSpec", _DEFER,
        "SiteArchitecture:recovery_routes+titles", "recovery label+href not representable by flat ContentBlock"),
    # ===================== trust =====================
    _cs("trust.reviews.list", "reviews", "reviews", "ReviewBlock", _UNAVAIL,
        "unavailable:reviews", "ReviewBlock corpus has no source artifact yet"),
    _lit("trust.reviews.list", "density", "STR_ENUM", _R_ENUM),
    _cs("trust.reviews.summary", "rating_summary", "listing_rating", "RatingSummary", _FLAT,
        "ListingRecord.rating", "one formatted aggregate string; structured stars deferred"),
    _cs("trust.statistics.strip", "statistics", "statistics", "StatBlock", _UNAVAIL,
        "unavailable:statistics", "StatBlock evidence has no source artifact yet"),
)

# AES-WEB-002J.19: the binding map's own version, independent of
# component_engine's ENGINE_VERSIONS entry. Recorded in Phase-B provenance
# (ComponentManifest.source_hashes) so a manifest is replay-verifiable
# against the exact map revision that produced it. Bumped whenever
# BINDING_RULES/SEMANTIC_SLOTS change in a way that could change binding
# output for identical artifact inputs -- never a timestamp.
#
# AES-WEB-002K.1 bumps 1.0.0 -> 1.1.0: nav.header.standard/legal.footer
# .directory's nav_tree fields move from STRUCTURED_DEFERRED to the new
# RENDER_DATA state (a real render-data producer now exists), and
# legal.footer.directory's legal_facts field is repointed from the
# unreachable BUSINESS_SPEC-sourced "legal_text" semantic slot to the new
# CONTENT_PACKAGE-sourced "footer_legal_text" slot (compile() takes no
# BusinessSpec input this delivery, per the J.19 operator decision,
# unchanged by K.1 -- see D5).
BINDING_MAP_VERSION: str = "1.2.0"

BINDING_RULES: Tuple[BindingRule, ...] = _RULES

# Index by (component_id, field_kind, field_name) -- the natural key. Built at
# import for O(1) lookup; duplicate keys are a validation concern (the
# validator reports them), so this index keeps the first occurrence.
BINDING_RULES_BY_KEY: Dict[Tuple[str, str, str], BindingRule] = {}
for _rule in BINDING_RULES:
    BINDING_RULES_BY_KEY.setdefault(
        (_rule.component_id, _rule.field_kind.value, _rule.field_name), _rule
    )


def rules_for_component(component_id: str) -> Tuple[BindingRule, ...]:
    """Every binding rule declared for ``component_id`` (declared order)."""
    return tuple(r for r in BINDING_RULES if r.component_id == component_id)


# Cross-check helper: every semantic slot a content-slot/prop-ref rule names
# must exist in the vocabulary. (The validator enforces this; exposed here so
# tests can assert it without re-deriving the set.)
def referenced_semantic_slots() -> Tuple[str, ...]:
    names = {
        r.semantic_slot
        for r in BINDING_RULES
        if r.field_kind is not FieldKind.PROP_LITERAL
    }
    return tuple(sorted(names))


def unknown_semantic_slots() -> Tuple[str, ...]:
    return tuple(
        sorted(n for n in referenced_semantic_slots() if n not in SEMANTIC_SLOTS)
    )


# ---------------------------------------------------------------------------
# Categorical bindability (AES-WEB-002J.19; ADR-WEB-CONTENT-BINDING-MAP)
# ---------------------------------------------------------------------------
#
# A component is "categorically bindable" when none of its REQUIRED fields
# carries a rule whose ``binding_state`` is STRUCTURED_DEFERRED or
# SOURCE_UNAVAILABLE -- i.e. when nothing about it is *architecturally*
# unbindable, regardless of which concrete inputs a given ``compile()`` call
# supplies. This is a static, pure classification over ``BINDING_RULES``
# alone (no artifact/runtime data needed), computed once and cached.
#
# A component with no declared rules at all (never registered in
# BINDING_RULES -- true of every synthetic/test-only definition outside the
# 72-component catalog) is treated as categorically bindable: the map has no
# basis to disqualify what it has never classified, so selection-only tests
# built on synthetic fixtures are unaffected by this filter (per ADR rule 7,
# "no placeholder source values" cuts the other way too -- silence is not
# evidence of unbindability).

_CATEGORICALLY_UNBINDABLE_STATES = frozenset(
    {BindingState.STRUCTURED_DEFERRED, BindingState.SOURCE_UNAVAILABLE}
)


def unbindable_required_fields(component_id: str) -> Tuple[BindingRule, ...]:
    """Every required rule for ``component_id`` whose ``binding_state`` is
    categorically unbindable (structured-deferred or source-unavailable),
    in declared order. Empty when the component is categorically bindable."""
    return tuple(
        r
        for r in rules_for_component(component_id)
        if r.required and r.binding_state in _CATEGORICALLY_UNBINDABLE_STATES
    )


def is_categorically_bindable(component_id: str) -> bool:
    """True unless ``component_id`` has at least one required field that can
    never be honestly bound under the current architecture (§14 doctrine:
    never fake structured support, never bind an unavailable source)."""
    return not unbindable_required_fields(component_id)
