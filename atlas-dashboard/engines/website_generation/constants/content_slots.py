"""Canonical semantic content-slot vocabulary (AES-WEB-002J.18;
ADR-WEB-CONTENT-BINDING-MAP).

The declarative source-of-truth vocabulary the future Component Engine
Phase-B binder (AES-WEB-001 §5.5) consumes: one entry per *semantic* slot
recording which artifact/derivation owns it, the block type it expects, its
scope and cardinality, and -- honestly -- whether flat ``ContentBlock.text``
can represent it. This module declares *what content means and where it
comes from*; ``components/binding_rules.py`` maps each component's own
declared field names onto these semantic slots.

Import matrix (§3.2): ``constants/`` may import only stdlib and other
``constants/`` modules -- never ``contracts/``. The enums below are therefore
plain ``enum.Enum`` classes (not the ``contracts/enums.py`` types), and block
types / cardinalities are the same bare strings ``SlotSpec`` already uses.

This is data only (no computation, no I/O, no binding). Structured content
that a single flat string cannot honestly carry is marked
``structured_deferred=True`` and left ``DEFERRED``; content with no producing
artifact is ``UNAVAILABLE``. No placeholder or ``"Resolved ..."`` value ever
appears here (ADR rule 7).
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Dict, Tuple


class SourceOwner(str, Enum):
    """Which artifact (or deterministic derivation) owns a semantic slot's
    value. Mirrors the AES-WEB-001 §4.1 artifact names plus ``DERIVED`` (a
    pure function of other artifacts) and ``UNAVAILABLE`` (no producer yet)."""

    BUSINESS_SPEC = "BUSINESS_SPEC"
    SITE_ARCHITECTURE = "SITE_ARCHITECTURE"
    CONTENT_PACKAGE = "CONTENT_PACKAGE"
    LISTING_DATASET = "LISTING_DATASET"
    BRAND_PACKAGE = "BRAND_PACKAGE"
    DERIVED = "DERIVED"
    UNAVAILABLE = "UNAVAILABLE"


class SlotScope(str, Enum):
    """The identity scope a slot's value is resolved within."""

    SITE = "SITE"
    ROUTE = "ROUTE"
    CATEGORY = "CATEGORY"
    LOCATION = "LOCATION"
    LISTING = "LISTING"


class Availability(str, Enum):
    """Whether a semantic slot's source can be bound today.

    * ``AVAILABLE``   -- a concrete artifact field exists and is honestly
      representable now.
    * ``DERIVABLE``   -- no stored field, but a deterministic pure derivation
      from existing artifacts yields it now (e.g. a result count).
    * ``DEFERRED``    -- a source may exist, but flat ``ContentBlock.text``
      cannot honestly represent the declared block type (structured content),
      so real binding waits for a ContentBlock/emitter sprint.
    * ``UNAVAILABLE`` -- no producing artifact exists yet.
    """

    AVAILABLE = "AVAILABLE"
    DERIVABLE = "DERIVABLE"
    DEFERRED = "DEFERRED"
    UNAVAILABLE = "UNAVAILABLE"


# Cardinality strings mirror contracts.enums.SlotCardinality values verbatim
# (constants/ may not import that enum). Kept as a module constant so the
# validator can check membership without a contracts import.
CARD_EXACTLY_ONE = "exactly_one"
CARD_ZERO_OR_ONE = "zero_or_one"
CARD_ONE_TO_N = "one_to_n"
VALID_CARDINALITIES: Tuple[str, ...] = (
    CARD_EXACTLY_ONE,
    CARD_ZERO_OR_ONE,
    CARD_ONE_TO_N,
)


@dataclass(frozen=True)
class SemanticSlot:
    """One canonical semantic content slot.

    ``source_key`` is a stable, human-readable path/derivation identifier
    (e.g. ``"ListingRecord.business_name"``, ``"ContentPackage:hero_h1"``,
    ``"derive:result_count"``) -- documentation and test anchor, never parsed
    at runtime. ``block_type`` is the same bare string a ``SlotSpec`` declares.
    ``flat_ok`` is True when a single ``ContentBlock.text`` honestly carries
    the value; ``structured_deferred`` is True when the declared block type
    needs structure flat text cannot represent.
    """

    name: str
    source_owner: SourceOwner
    source_key: str
    block_type: str
    scope: SlotScope
    cardinality: str
    flat_ok: bool
    structured_deferred: bool
    availability: Availability


def _slot(
    name, owner, source_key, block_type, scope, cardinality,
    flat_ok, structured_deferred, availability,
) -> SemanticSlot:
    return SemanticSlot(
        name=name,
        source_owner=owner,
        source_key=source_key,
        block_type=block_type,
        scope=scope,
        cardinality=cardinality,
        flat_ok=flat_ok,
        structured_deferred=structured_deferred,
        availability=availability,
    )


_O = SourceOwner
_S = SlotScope
_A = Availability

# The canonical vocabulary. Every entry is consumed by at least one current
# component (via binding_rules.py); no speculative slots. Ordered by group for
# readability -- the SEMANTIC_SLOTS dict preserves this insertion order, and
# the validator sorts by name where determinism matters.
_ALL: Tuple[SemanticSlot, ...] = (
    # -- Site -----------------------------------------------------------
    _slot("site_name", _O.BUSINESS_SPEC, "BusinessSpec.business_name",
          "RichTextBlock", _S.SITE, CARD_EXACTLY_ONE, True, False, _A.AVAILABLE),
    _slot("logo", _O.BRAND_PACKAGE, "BrandPackage.asset_hashes[logo]",
          "AssetRef", _S.SITE, CARD_ZERO_OR_ONE, False, True, _A.DEFERRED),
    _slot("primary_navigation", _O.SITE_ARCHITECTURE, "derive:nav_routes+titles",
          "LinkSpec", _S.SITE, CARD_ONE_TO_N, False, True, _A.DEFERRED),
    _slot("footer_navigation", _O.SITE_ARCHITECTURE, "derive:footer_routes+titles",
          "LinkSpec", _S.SITE, CARD_ONE_TO_N, False, True, _A.DEFERRED),
    _slot("legal_text", _O.BUSINESS_SPEC, "BusinessSpec.legal_footer_facts",
          "RichTextBlock", _S.SITE, CARD_ONE_TO_N, True, False, _A.AVAILABLE),
    # AES-WEB-002K.1: legal.footer.directory's legal_facts field is
    # repointed here (D5) rather than to "legal_text" above -- compile()
    # takes no BusinessSpec input this delivery (unchanged J.19 operator
    # decision), so "legal_text" stays permanently unreachable in practice;
    # this slot is the same shape (flat, always-available site copy) but
    # sourced from an explicit ContentPackage block instead, mirroring
    # footer_disclosures' identical CONTENT_PACKAGE/SITE-scope pattern below.
    _slot("footer_legal_text", _O.CONTENT_PACKAGE, "ContentPackage:footer_legal",
          "RichTextBlock", _S.SITE, CARD_EXACTLY_ONE, True, False, _A.AVAILABLE),
    # -- Page -----------------------------------------------------------
    _slot("page_h1", _O.CONTENT_PACKAGE, "ContentPackage:hero_h1",
          "RichTextBlock", _S.ROUTE, CARD_EXACTLY_ONE, True, False, _A.AVAILABLE),
    _slot("page_subhead", _O.CONTENT_PACKAGE, "ContentPackage:subhead",
          "RichTextBlock", _S.ROUTE, CARD_EXACTLY_ONE, True, False, _A.AVAILABLE),
    _slot("page_intro", _O.CONTENT_PACKAGE, "ContentPackage:intro",
          "RichTextBlock", _S.ROUTE, CARD_EXACTLY_ONE, True, False, _A.AVAILABLE),
    _slot("page_body", _O.CONTENT_PACKAGE, "ContentPackage:body",
          "RichTextBlock", _S.ROUTE, CARD_EXACTLY_ONE, True, False, _A.AVAILABLE),
    _slot("page_summary", _O.CONTENT_PACKAGE, "ContentPackage:summary",
          "RichTextBlock", _S.ROUTE, CARD_EXACTLY_ONE, True, False, _A.AVAILABLE),
    _slot("page_message", _O.CONTENT_PACKAGE, "ContentPackage:message",
          "RichTextBlock", _S.ROUTE, CARD_EXACTLY_ONE, True, False, _A.AVAILABLE),
    _slot("recovery_links", _O.SITE_ARCHITECTURE, "derive:recovery_routes+titles",
          "LinkSpec", _S.ROUTE, CARD_ONE_TO_N, False, True, _A.DEFERRED),
    # -- Directory ------------------------------------------------------
    _slot("category_tiles", _O.LISTING_DATASET, "derive:categories+routes",
          "LinkSpec", _S.CATEGORY, CARD_ONE_TO_N, False, True, _A.DEFERRED),
    _slot("location_tiles", _O.LISTING_DATASET, "derive:locations+routes",
          "LinkSpec", _S.LOCATION, CARD_ONE_TO_N, False, True, _A.DEFERRED),
    _slot("result_summary", _O.DERIVED, "derive:result_count",
          "RichTextBlock", _S.ROUTE, CARD_EXACTLY_ONE, True, False, _A.DERIVABLE),
    _slot("facet_options", _O.UNAVAILABLE, "unavailable:facets",
          "LinkSpec", _S.ROUTE, CARD_ONE_TO_N, False, True, _A.UNAVAILABLE),
    _slot("sort_options", _O.UNAVAILABLE, "unavailable:sort_options",
          "LinkSpec", _S.ROUTE, CARD_ONE_TO_N, False, True, _A.UNAVAILABLE),
    _slot("pagination_context", _O.UNAVAILABLE, "unavailable:pagination",
          "LinkSpec", _S.ROUTE, CARD_ONE_TO_N, False, True, _A.UNAVAILABLE),
    # -- Listing / profile ----------------------------------------------
    _slot("listing_name", _O.LISTING_DATASET, "ListingRecord.business_name",
          "RichTextBlock", _S.LISTING, CARD_EXACTLY_ONE, True, False, _A.AVAILABLE),
    _slot("listing_description", _O.LISTING_DATASET, "ListingRecord.description",
          "RichTextBlock", _S.LISTING, CARD_EXACTLY_ONE, True, False, _A.AVAILABLE),
    _slot("listing_contact", _O.LISTING_DATASET, "ListingRecord.contact+address",
          "ContactSpec", _S.LISTING, CARD_EXACTLY_ONE, False, True, _A.DEFERRED),
    _slot("listing_hours", _O.LISTING_DATASET, "ListingRecord.hours",
          "HoursSpec", _S.LISTING, CARD_EXACTLY_ONE, False, True, _A.DEFERRED),
    _slot("listing_rating", _O.LISTING_DATASET, "ListingRecord.rating",
          "RatingSummary", _S.LISTING, CARD_ZERO_OR_ONE, False, True, _A.DEFERRED),
    _slot("listing_credentials", _O.LISTING_DATASET, "ListingRecord.credentials",
          "CredentialBlock", _S.LISTING, CARD_ONE_TO_N, False, True, _A.DEFERRED),
    _slot("listing_location", _O.LISTING_DATASET, "ListingRecord.geo+address",
          "GeoSpec", _S.LISTING, CARD_EXACTLY_ONE, False, True, _A.DEFERRED),
    _slot("listing_disclosure", _O.LISTING_DATASET, "ListingRecord.sponsorship.disclosure_text",
          "DisclosureBlock", _S.LISTING, CARD_EXACTLY_ONE, True, False, _A.AVAILABLE),
    _slot("listing_cta", _O.LISTING_DATASET, "ListingRecord.cta",
          "LinkSpec", _S.LISTING, CARD_ZERO_OR_ONE, False, True, _A.DEFERRED),
    _slot("listing_gallery", _O.LISTING_DATASET, "ListingRecord.assets",
          "AssetRef", _S.LISTING, CARD_ONE_TO_N, False, True, _A.DEFERRED),
    # -- Trust / commercial ---------------------------------------------
    _slot("sponsorship_disclosure", _O.LISTING_DATASET, "ListingRecord.sponsorship.disclosure_text",
          "DisclosureBlock", _S.LISTING, CARD_EXACTLY_ONE, True, False, _A.AVAILABLE),
    _slot("statistics", _O.UNAVAILABLE, "unavailable:statistics",
          "StatBlock", _S.SITE, CARD_ONE_TO_N, False, True, _A.UNAVAILABLE),
    _slot("pricing_disclaimer", _O.UNAVAILABLE, "unavailable:pricing",
          "PriceSpec", _S.SITE, CARD_EXACTLY_ONE, False, True, _A.UNAVAILABLE),
    _slot("qa_pairs", _O.UNAVAILABLE, "unavailable:qa_pairs",
          "QAPair", _S.ROUTE, CARD_ONE_TO_N, False, True, _A.UNAVAILABLE),
    _slot("reviews", _O.UNAVAILABLE, "unavailable:reviews",
          "ReviewBlock", _S.LISTING, CARD_ONE_TO_N, False, True, _A.UNAVAILABLE),
    _slot("comparison_table", _O.UNAVAILABLE, "unavailable:comparison_table",
          "ComparisonTableBlock", _S.ROUTE, CARD_EXACTLY_ONE, False, True, _A.UNAVAILABLE),
    # -- Forms ----------------------------------------------------------
    _slot("form_disclosure", _O.CONTENT_PACKAGE, "ContentPackage:disclosure",
          "DisclosureBlock", _S.ROUTE, CARD_EXACTLY_ONE, True, False, _A.AVAILABLE),
    _slot("form_label", _O.CONTENT_PACKAGE, "ContentPackage:label",
          "RichTextBlock", _S.ROUTE, CARD_EXACTLY_ONE, True, False, _A.AVAILABLE),
    _slot("resource_links", _O.SITE_ARCHITECTURE, "derive:resource_routes+titles",
          "LinkSpec", _S.ROUTE, CARD_ONE_TO_N, False, True, _A.DEFERRED),
    _slot("standards_link", _O.SITE_ARCHITECTURE, "derive:standards_route+title",
          "LinkSpec", _S.ROUTE, CARD_EXACTLY_ONE, False, True, _A.DEFERRED),
    # -- Generic editorial (atoms/status/legal that carry inline copy) --
    _slot("inline_label", _O.CONTENT_PACKAGE, "ContentPackage:label",
          "RichTextBlock", _S.ROUTE, CARD_EXACTLY_ONE, True, False, _A.AVAILABLE),
    _slot("inline_body", _O.CONTENT_PACKAGE, "ContentPackage:body",
          "RichTextBlock", _S.ROUTE, CARD_EXACTLY_ONE, True, False, _A.AVAILABLE),
    _slot("field_error", _O.CONTENT_PACKAGE, "ContentPackage:error",
          "RichTextBlock", _S.ROUTE, CARD_EXACTLY_ONE, True, False, _A.AVAILABLE),
    _slot("field_legend", _O.CONTENT_PACKAGE, "ContentPackage:legend",
          "RichTextBlock", _S.ROUTE, CARD_EXACTLY_ONE, True, False, _A.AVAILABLE),
    _slot("field_options", _O.UNAVAILABLE, "unavailable:field_options",
          "LinkSpec", _S.ROUTE, CARD_ONE_TO_N, False, True, _A.UNAVAILABLE),
    _slot("heading_refs", _O.SITE_ARCHITECTURE, "derive:page_headings+anchors",
          "LinkSpec", _S.ROUTE, CARD_ONE_TO_N, False, True, _A.DEFERRED),
    _slot("breadcrumb_trail", _O.SITE_ARCHITECTURE, "derive:breadcrumb_routes+titles",
          "LinkSpec", _S.ROUTE, CARD_ONE_TO_N, False, True, _A.DEFERRED),
    _slot("status_message", _O.CONTENT_PACKAGE, "ContentPackage:message",
          "RichTextBlock", _S.ROUTE, CARD_EXACTLY_ONE, True, False, _A.AVAILABLE),
    _slot("expectation_text", _O.CONTENT_PACKAGE, "ContentPackage:expectation_text",
          "RichTextBlock", _S.ROUTE, CARD_EXACTLY_ONE, True, False, _A.AVAILABLE),
    _slot("premium_blocks", _O.CONTENT_PACKAGE, "ContentPackage:premium_blocks",
          "RichTextBlock", _S.ROUTE, CARD_EXACTLY_ONE, True, False, _A.AVAILABLE),
    _slot("offer_text", _O.CONTENT_PACKAGE, "ContentPackage:offer",
          "RichTextBlock", _S.ROUTE, CARD_EXACTLY_ONE, True, False, _A.AVAILABLE),
    _slot("disclaimer_text", _O.CONTENT_PACKAGE, "ContentPackage:disclaimer",
          "RichTextBlock", _S.ROUTE, CARD_EXACTLY_ONE, True, False, _A.AVAILABLE),
    _slot("directions_text", _O.CONTENT_PACKAGE, "ContentPackage:directions_text",
          "RichTextBlock", _S.ROUTE, CARD_EXACTLY_ONE, True, False, _A.AVAILABLE),
    _slot("footer_disclosures", _O.CONTENT_PACKAGE, "ContentPackage:disclosures",
          "DisclosureBlock", _S.SITE, CARD_EXACTLY_ONE, True, False, _A.AVAILABLE),
    _slot("service_area_links", _O.SITE_ARCHITECTURE, "derive:service_area_routes+titles",
          "LinkSpec", _S.LISTING, CARD_ONE_TO_N, False, True, _A.DEFERRED),
    _slot("inline_link", _O.SITE_ARCHITECTURE, "derive:route+title",
          "LinkSpec", _S.ROUTE, CARD_EXACTLY_ONE, False, True, _A.DEFERRED),
)

SEMANTIC_SLOTS: Dict[str, SemanticSlot] = {slot.name: slot for slot in _ALL}


def semantic_slot(name: str) -> SemanticSlot:
    """Return the :class:`SemanticSlot` for ``name`` (KeyError if unknown)."""
    return SEMANTIC_SLOTS[name]


def is_flat_bindable(slot: SemanticSlot) -> bool:
    """True when a single flat ``ContentBlock.text`` honestly binds this slot
    today (AVAILABLE or DERIVABLE and ``flat_ok``)."""
    return (
        slot.flat_ok
        and not slot.structured_deferred
        and slot.availability in (Availability.AVAILABLE, Availability.DERIVABLE)
    )
