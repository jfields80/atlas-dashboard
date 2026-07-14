"""Phase-B content-slot and content-reference-prop projection
(AES-WEB-002J.19; ADR-WEB-CONTENT-BINDING-MAP; AES-WEB-001 §5.5).

Two distinct binding shapes, matching the Renderer's own content-resolution
convention (``rendering/renderer.py._resolve_content``) exactly -- this
module produces exactly what that convention already expects, nothing new:

* **content slots** (``required_content_slots``/``optional_content_slots``):
  the created/reused ``ContentBlock.slot_id`` MUST equal the component's own
  declared field name (e.g. ``"h1"``), because the Renderer looks up
  ``content_index[(route, slot_id)]`` using that exact literal. Resolving a
  ``FULLY_BINDABLE`` editorial rule therefore *copies* the source text into a
  new block keyed by the component's own field name when the source key
  differs (e.g. IA's ``hero_h1`` -> component field ``h1``), or reuses the
  block directly when the names already match (e.g. ``intro`` -> ``intro``).
* **``CONTENT_BLOCK_REF``/``LISTING_REF`` props**: the Renderer looks up
  ``content_index[(route, instance.props[prop_name])]`` -- the prop's own
  *value* is the lookup key, so Phase B is free to choose it. For a
  ``LISTING_DATASET``-sourced semantic slot whose listing is actually known
  (an explicit AES-WEB-002J.20 repetition assignment, or the J.19
  route-scope fallback), the generated id is the listing-aware
  ``bind.<semantic_slot>.<listing_id>`` -- stable under listing reordering
  and safely idempotent when the same listing is referenced by more than one
  component on a route (identical text at an identical key, never a
  collision). Every other projection (no listing resolved, or a
  non-``LISTING_DATASET`` source) keeps the J.19 positional
  ``bind.<semantic_slot>.<component_index>`` form.

Route scope (category/listing identity) is resolved by an **exact,
deterministic route-string convention** documented in
ADR-WEB-LISTING-DATASET §6 (category route ``/<category-slug>/``, listing
route ``/<category-slug>/<listing-slug>/``) -- never fuzzy/substring
matching. Listing projections (name, description, contact, hours, rating,
credentials, disclosure) are flat, honest, deterministic single strings
(``FLAT_PROJECTION_ONLY`` per the J.18 map) -- never a claim of structured
support. No AI, no clock, no randomness, no network.
"""

from __future__ import annotations

from typing import Dict, List, NamedTuple, Optional, Tuple

from engines.website_generation.constants.content_slots import Availability, SourceOwner
from engines.website_generation.contracts.artifacts import (
    ContentBlock,
    ListingCategory,
    ListingDataset,
    ListingLocation,
    ListingRecord,
)
from engines.website_generation.components.binding_rules import BindingRule, SEMANTIC_SLOTS

_WEEKDAY_ORDER: Tuple[str, ...] = (
    "MONDAY", "TUESDAY", "WEDNESDAY", "THURSDAY", "FRIDAY", "SATURDAY", "SUNDAY",
)
_WEEKDAY_LABEL: Dict[str, str] = {
    "MONDAY": "Mon", "TUESDAY": "Tue", "WEDNESDAY": "Wed", "THURSDAY": "Thu",
    "FRIDAY": "Fri", "SATURDAY": "Sat", "SUNDAY": "Sun",
}


class UnboundContentField(Exception):
    """Internal: a content-slot or ref-prop rule could not be projected.
    Never escapes the Component Engine's batch collector uncaught."""

    def __init__(self, field_name: str, reason: str) -> None:
        super().__init__(field_name, reason)
        self.field_name = field_name
        self.reason = reason


class ProjectedSlotCollision(Exception):
    """Internal: two different texts were projected to the same
    ``(route, slot_id)`` key -- a hard error (ADR: never silently overwrite)."""

    def __init__(self, route: str, slot_id: str) -> None:
        super().__init__(route, slot_id)
        self.route = route
        self.slot_id = slot_id


# --------------------------------------------------------------------------- #
# Route scope resolution (deterministic, exact-match only)
# --------------------------------------------------------------------------- #

class RouteScope(NamedTuple):
    """The listing-data identity a route resolves to, or none of it."""

    category: Optional[ListingCategory]
    location: Optional[ListingLocation]
    listing: Optional[ListingRecord]


def _category_route(category: ListingCategory) -> str:
    return "/%s/" % category.slug


def _listing_route(category: ListingCategory, listing: ListingRecord) -> str:
    return "/%s/%s/" % (category.slug, listing.slug)


def resolve_route_scope(
    route: str, listing_dataset: Optional[ListingDataset]
) -> RouteScope:
    """Resolve ``route`` against ``listing_dataset`` by exact string match
    against the ADR-WEB-LISTING-DATASET §6 derivation convention. Listing
    routes are checked first (more specific), then category routes. No
    match (home/static/status routes, or no dataset supplied) yields an
    all-``None`` scope -- never a guess."""
    if listing_dataset is None:
        return RouteScope(None, None, None)
    categories_by_id = {c.category_id: c for c in listing_dataset.categories}
    locations_by_id = {l.location_id: l for l in listing_dataset.locations}

    for listing in listing_dataset.listings:
        category = categories_by_id.get(listing.category_id)
        if category is None:
            continue
        if route == _listing_route(category, listing):
            location = locations_by_id.get(listing.location_id) if listing.location_id else None
            return RouteScope(category, location, listing)

    for category in listing_dataset.categories:
        if route == _category_route(category):
            return RouteScope(category, None, None)

    return RouteScope(None, None, None)


def assign_listing(route_scope: RouteScope, listing_dataset: Optional[ListingDataset]) -> Optional[ListingRecord]:
    """The single ``ListingRecord`` a component instance on this route binds
    to (§10 -- no repetition in J.19: one generic listing component receives
    the *first* matching listing only).

    * Listing/profile route -> the resolved listing itself.
    * Category route -> the first listing (dataset tuple order) whose
      ``category_id`` matches, or ``None`` if the category has no listings.
    * No scope -> ``None``.
    """
    if route_scope.listing is not None:
        return route_scope.listing
    if route_scope.category is not None and listing_dataset is not None:
        for listing in listing_dataset.listings:
            if listing.category_id == route_scope.category.category_id:
                return listing
    return None


# --------------------------------------------------------------------------- #
# Generated slot-id strategy
# --------------------------------------------------------------------------- #

def generated_slot_id(semantic_slot: str, component_index: int) -> str:
    """``bind.<semantic_slot>.<component_index>`` (deterministic, route-
    scoped-by-construction since ``component_index`` is unique per page;
    no UUID/clock/random/address)."""
    return "bind.%s.%d" % (semantic_slot, component_index)


def generated_listing_slot_id(semantic_slot: str, listing_id: str) -> str:
    """``bind.<semantic_slot>.<listing_id>`` (AES-WEB-002J.20). Deterministic
    and stable under listing reordering -- ``listing_id``'s grammar
    (``^[a-z0-9]+(-[a-z0-9]+)*$``, ADR-WEB-LISTING-DATASET) contains no dots,
    so the three-segment id remains unambiguous to parse. The same
    ``(semantic_slot, listing_id)`` pair always yields the same id
    regardless of which component instance or page position references it,
    which is what makes cross-component reuse of one listing's projected
    block an idempotent no-op (:class:`ProjectionAccumulator`) rather than a
    collision."""
    return "bind.%s.%s" % (semantic_slot, listing_id)


# --------------------------------------------------------------------------- #
# Listing / derived flat projections (FULLY_BINDABLE / FLAT_PROJECTION_ONLY
# rules whose source_owner is LISTING_DATASET or DERIVED)
# --------------------------------------------------------------------------- #

def _format_rating(rating_hundredths: int, review_count: int) -> str:
    # Integer-only formatting -- no float arithmetic (ADR/mission directive).
    whole, frac = divmod(rating_hundredths, 100)
    return "%d.%02d (%d review%s)" % (
        whole, frac, review_count, "" if review_count == 1 else "s"
    )


def _format_contact(listing: ListingRecord) -> str:
    parts: List[str] = []
    if listing.address is not None:
        addr = listing.address
        line = ", ".join(p for p in (addr.street, addr.city, addr.state, addr.postal_code) if p)
        if line:
            parts.append(line)
    if listing.contact is not None:
        c = listing.contact
        if c.phone:
            parts.append(c.phone)
        if c.email:
            parts.append(c.email)
        if c.website_url:
            parts.append(c.website_url)
    return "; ".join(parts)


def _format_hours(listing: ListingRecord) -> str:
    by_day = {entry.day.value: entry for entry in listing.hours}
    parts: List[str] = []
    for day in _WEEKDAY_ORDER:
        entry = by_day.get(day)
        if entry is None:
            continue
        label = _WEEKDAY_LABEL[day]
        if entry.closed:
            parts.append("%s Closed" % label)
        else:
            parts.append("%s %s-%s" % (label, entry.opens, entry.closes))
    return "; ".join(parts)


def project_listing_value(semantic_slot: str, listing: ListingRecord) -> Optional[str]:
    """Deterministic flat text for a listing-sourced semantic slot, or
    ``None`` when the listing has no data for it (caller decides whether
    that is an honest failure or an omittable optional field)."""
    if semantic_slot == "listing_name":
        return listing.business_name or None
    if semantic_slot == "listing_description":
        return listing.description or None
    if semantic_slot in ("listing_contact",):
        text = _format_contact(listing)
        return text or None
    if semantic_slot == "listing_hours":
        text = _format_hours(listing)
        return text or None
    if semantic_slot == "listing_rating":
        if listing.rating is None:
            return None
        return _format_rating(listing.rating.rating_hundredths, listing.rating.review_count)
    if semantic_slot == "listing_credentials":
        return "; ".join(listing.credentials) or None
    if semantic_slot in ("listing_disclosure", "sponsorship_disclosure"):
        if listing.sponsorship is None or not listing.sponsorship.disclosure_text:
            return None
        return listing.sponsorship.disclosure_text
    return None


def project_derived_value(
    semantic_slot: str, route_scope: RouteScope, listing_dataset: Optional[ListingDataset]
) -> Optional[str]:
    """Deterministic text for a ``DERIVED``-owned semantic slot (currently
    only ``result_summary`` -- a real count, never a fabricated one)."""
    if semantic_slot != "result_summary":
        return None
    if listing_dataset is None or route_scope.category is None:
        return None
    count = sum(
        1 for l in listing_dataset.listings if l.category_id == route_scope.category.category_id
    )
    if count == 0:
        return "No listings found"
    return "Showing %d listing%s" % (count, "" if count == 1 else "s")


# --------------------------------------------------------------------------- #
# Existing-ContentPackage resolution (editorial rules; BUSINESS_SPEC-sourced
# rules are honestly unbindable this delivery -- compile() takes no
# BusinessSpec input, per the J.19 operator decision)
# --------------------------------------------------------------------------- #

_CONTENT_PACKAGE_PREFIX = "ContentPackage:"


def resolve_existing_content(
    rule: BindingRule,
    route: str,
    content_index: Dict[Tuple[str, str], Tuple[str, ...]],
) -> str:
    """Resolve a ``FULLY_BINDABLE`` rule whose source is an existing
    ``ContentPackage`` block. Exact ``(route, key)`` lookup only -- the key
    is the rule's own declared ``source_rule`` (already the correct J.18
    alias target, e.g. ``hero_h1`` for component field ``h1``). Raises on
    zero or ambiguous (>1, for a single-value field) matches."""
    if not rule.source_rule.startswith(_CONTENT_PACKAGE_PREFIX):
        raise UnboundContentField(rule.field_name, "invalid_source_field: not a ContentPackage rule")
    key = rule.source_rule[len(_CONTENT_PACKAGE_PREFIX):]
    values = content_index.get((route, key), ())
    if not values:
        raise UnboundContentField(
            rule.field_name, "missing_source_artifact: no ContentPackage block at (%r, %r)" % (route, key)
        )
    if len(values) > 1 and len(set(values)) > 1:
        raise UnboundContentField(
            rule.field_name,
            "content_alias_ambiguity: %d conflicting blocks at (%r, %r)" % (len(values), route, key),
        )
    return values[0]


# --------------------------------------------------------------------------- #
# Per-compile projected-block accumulator (collision-safe, immutable output)
# --------------------------------------------------------------------------- #

class ProjectionAccumulator:
    """Collects deterministic projected ``ContentBlock``s across one
    ``compile()`` call. Idempotent re-projection of the identical
    ``(route, slot_id)`` -> text is a no-op; conflicting text at the same
    key raises :class:`ProjectedSlotCollision` (ADR: never silently
    overwrite)."""

    def __init__(self) -> None:
        self._by_key: Dict[Tuple[str, str], str] = {}
        self._order: List[Tuple[str, str]] = []

    def add(self, route: str, slot_id: str, text: str) -> None:
        key = (route, slot_id)
        existing = self._by_key.get(key)
        if existing is not None:
            if existing != text:
                raise ProjectedSlotCollision(route, slot_id)
            return
        self._by_key[key] = text
        self._order.append(key)

    def blocks(self) -> Tuple[ContentBlock, ...]:
        return tuple(
            ContentBlock(page_route=route, slot_id=slot_id, text=self._by_key[(route, slot_id)])
            for route, slot_id in self._order
        )


# --------------------------------------------------------------------------- #
# Orchestration: one content-slot / one ref-prop, source-owner dispatch
# --------------------------------------------------------------------------- #

def _resolve_semantic_text(
    rule: BindingRule,
    field_name: str,
    route: str,
    *,
    content_index: Dict[Tuple[str, str], Tuple[str, ...]],
    listing_dataset: Optional[ListingDataset],
    route_scope: RouteScope,
    assigned_listing: Optional[ListingRecord] = None,
) -> Tuple[str, Optional[str]]:
    """Resolve the text a rule's semantic slot projects to, dispatching on
    the slot's declared ``source_owner`` -- the one place binding failures
    for content/ref fields converge, per §14.2's centralized-failure
    discipline.

    Returns ``(text, listing_id)`` -- ``listing_id`` is the resolved
    listing's id when ``source_owner`` is ``LISTING_DATASET`` (AES-WEB-002J.20:
    the caller uses it for a listing-aware generated slot id), or ``None``
    for every other source. ``assigned_listing`` (J.20 repetition) takes
    precedence over the J.19 single-listing route-scope fallback
    (:func:`assign_listing`) when supplied -- this is what lets each
    repeated instance bind to its own record rather than all sharing the
    route's one implicit listing.
    """
    semantic = SEMANTIC_SLOTS.get(rule.semantic_slot)
    if semantic is None:
        raise UnboundContentField(
            field_name, "missing_semantic_source: unknown semantic slot %r" % rule.semantic_slot
        )

    if semantic.source_owner is SourceOwner.CONTENT_PACKAGE:
        return resolve_existing_content(rule, route, content_index), None

    if semantic.source_owner is SourceOwner.LISTING_DATASET:
        listing = assigned_listing if assigned_listing is not None else assign_listing(
            route_scope, listing_dataset
        )
        if listing is None:
            raise UnboundContentField(
                field_name, "missing_listing: no listing resolved for route %r" % route
            )
        text = project_listing_value(rule.semantic_slot, listing)
        if text is None:
            raise UnboundContentField(
                field_name,
                "missing_source_artifact: listing has no value for %r" % rule.semantic_slot,
            )
        return text, listing.listing_id

    if semantic.source_owner is SourceOwner.DERIVED:
        text = project_derived_value(rule.semantic_slot, route_scope, listing_dataset)
        if text is None:
            raise UnboundContentField(
                field_name, "missing_source_artifact: cannot derive %r" % rule.semantic_slot
            )
        return text, None

    if semantic.source_owner is SourceOwner.BUSINESS_SPEC:
        # compile() takes no BusinessSpec input in J.19 (operator decision) --
        # honestly unbindable this delivery, never fabricated.
        raise UnboundContentField(
            field_name, "missing_source_artifact: BusinessSpec is not a Phase-B input"
        )

    # BRAND_PACKAGE / UNAVAILABLE semantic slots have no content projection
    # path; a required rule of this shape should already have been excluded
    # at Phase A by is_categorically_bindable -- reaching here (a fallback or
    # an externally-injected component slipping through) is a defensive
    # double-check, not the expected path.
    raise UnboundContentField(
        field_name, "unavailable_source: %r has no content projection path" % rule.semantic_slot
    )


def bind_content_slot(
    rule: BindingRule,
    field_name: str,
    route: str,
    *,
    content_index: Dict[Tuple[str, str], Tuple[str, ...]],
    listing_dataset: Optional[ListingDataset],
    route_scope: RouteScope,
    projection: ProjectionAccumulator,
) -> str:
    """Resolve and project one content-slot field. Returns ``field_name``
    itself (the ``content_refs`` membership token the Renderer checks) after
    ensuring a ``ContentBlock`` exists at ``(route, field_name)`` -- reusing
    an identical pre-existing block verbatim, projecting a new one when
    none exists, or raising :class:`ProjectedSlotCollision` when a
    pre-existing block at that exact key carries different text."""
    text, _listing_id = _resolve_semantic_text(
        rule, field_name, route,
        content_index=content_index, listing_dataset=listing_dataset, route_scope=route_scope,
    )
    existing = content_index.get((route, field_name), ())
    if existing:
        if len(set(existing)) > 1 or existing[0] != text:
            raise ProjectedSlotCollision(route, field_name)
        # Identical block already present under this exact key -- no new
        # projection needed (e.g. "intro" component slot <- "intro" IA slot).
    else:
        projection.add(route, field_name, text)
    return field_name


def bind_ref_prop(
    rule: BindingRule,
    field_name: str,
    route: str,
    component_index: int,
    *,
    content_index: Dict[Tuple[str, str], Tuple[str, ...]],
    listing_dataset: Optional[ListingDataset],
    route_scope: RouteScope,
    projection: ProjectionAccumulator,
    assigned_listing: Optional[ListingRecord] = None,
) -> str:
    """Resolve and project one ``CONTENT_BLOCK_REF``/``LISTING_REF`` prop.
    Returns the generated slot id -- the prop's own bound *value* -- after
    ensuring a ``ContentBlock`` exists at that id.

    ``assigned_listing`` (AES-WEB-002J.20 repetition) takes precedence over
    the J.19 route-scope fallback; when a listing is actually resolved for a
    ``LISTING_DATASET``-sourced slot, the generated id is the listing-aware
    ``bind.<semantic_slot>.<listing_id>`` rather than the positional
    ``bind.<semantic_slot>.<component_index>`` -- stable under reordering
    and safely shareable across components referencing the same listing.
    """
    text, listing_id = _resolve_semantic_text(
        rule, field_name, route,
        content_index=content_index, listing_dataset=listing_dataset, route_scope=route_scope,
        assigned_listing=assigned_listing,
    )
    slot_id = (
        generated_listing_slot_id(rule.semantic_slot, listing_id)
        if listing_id is not None
        else generated_slot_id(rule.semantic_slot, component_index)
    )
    projection.add(route, slot_id, text)
    return slot_id
