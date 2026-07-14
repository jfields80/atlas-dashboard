"""Render-data contracts (AES-WEB-002K.1; ADR-WEB-CONTENT-BINDING-MAP).

A small, typed, **non-artifact** value model produced by the Component
Engine's Phase B (``components/component_engine.py``) and consumed only by
the Renderer/emitters, carrying exactly the structured data flat
``ContentBlock.text`` cannot honestly represent: real hyperlinks (label +
href), enriched listing cards, and structured contact/hours. Bundled onto
:class:`~engines.website_generation.contracts.artifacts.ComponentCompilationResult`
as an additive ``render_data`` field -- never a registered artifact, never
an :class:`ArtifactKind`, never hashed/replayed independently of the
rendered HTML it produces.

Layering (AES-WEB-002 §29.2 import matrix): ``rendering/`` may import only
``contracts/`` and ``constants/`` -- it has no legal import path to
``components/``, so these types live here, not under ``components/``. This
module intentionally does **not** import
:class:`engines.website_generation.contracts.artifacts.FrozenModel` --
``artifacts.py`` is the module that imports *this* one (to type
``ComponentCompilationResult.render_data``), and a reverse import would be
circular. Per the established ``is_safe_url`` precedent
(``contracts/listing_dataset_validator.py``'s module docstring: "``contracts/``
has no legal import path to ``rendering/``, so URL/route safety is
re-derived here rather than imported... documented in parallel, not shared
code"), this module embeds its own tiny frozen-model isolation point rather
than create a fifth cross-layer import edge.

Pydantic-compat + no-validator doctrine (mirrors ``contracts/artifacts.py``'s
own documented decision): models derive from :class:`FrozenModel`, frozen
under v1 and v2, ``extra="forbid"``. No ``@validator``/``@field_validator``
-- validation beyond type coercion (href safety, non-empty labels, unique
``(route, component_index)`` entries) lives in the producer
(``ComponentEngine``, "the compiler"), which raises the existing
``ComponentResolutionError`` batch-diagnostic model on a genuine defect,
exactly like every other Phase-B binding failure. A contract-level
``@validator`` here would duplicate that responsibility in a second place
and risk disagreeing with it.
"""

from __future__ import annotations

from typing import FrozenSet, Optional, Tuple

import pydantic
from pydantic import BaseModel

PYDANTIC_V2: bool = str(getattr(pydantic, "VERSION", "1.0")).startswith("2")

if PYDANTIC_V2:
    from pydantic import ConfigDict

    class FrozenModel(BaseModel):
        """Immutable base model (Pydantic v2) -- local to this module; see
        the module docstring for why this isn't imported from
        ``contracts/artifacts.py``."""

        model_config = ConfigDict(frozen=True, extra="forbid")

else:

    class FrozenModel(BaseModel):
        """Immutable base model (Pydantic v1) -- local to this module; see
        the module docstring for why this isn't imported from
        ``contracts/artifacts.py``."""

        class Config:
            frozen = True
            allow_mutation = False
            extra = "forbid"


# AES-WEB-002K.1: this module's own version, independent of any engine
# version. Recorded in ComponentManifest.source_hashes (the
# BINDING_MAP_VERSION/COMPOSITION_RULES_VERSION precedent) so a manifest is
# replay-verifiable against the exact render-data model revision that
# produced it.
RENDER_DATA_VERSION: str = "1.0.0"


class LinkSpec(FrozenModel):
    """One real hyperlink: a human label plus its href -- the one reusable
    shape for header/footer navigation, listing-card profile links, CTAs,
    and clickable contact fields. ``rel`` is a single space-separated
    string (the HTML ``rel`` attribute's own grammar -- e.g.
    ``"noopener sponsored"``), not a tuple. ``external`` is supplied
    explicitly by the producer (it knows whether a link is internal/route
    or an outbound URL); it is never derived by guessing at the href."""

    label: str
    href: str
    rel: str = ""
    aria_label: str = ""
    external: bool = False


class NavigationData(FrozenModel):
    """One nav landmark's ordered links (header OR footer -- two separate
    instances, not one shared list)."""

    links: Tuple[LinkSpec, ...] = ()


class TileLinks(FrozenModel):
    """Category/location discovery tiles. Defined per the approved
    render-data model for contract completeness; AES-WEB-002K.1 wires no
    producer for it (the home page's "at least one category link"
    requirement is satisfied by header navigation alone --
    ``directory.categories.grid``/location tiles remain out of Wave 1
    scope, unchanged)."""

    tiles: Tuple[LinkSpec, ...] = ()


class ListingCardData(FrozenModel):
    """One repeated listing card/row instance's enrichment (AES-WEB-002K.1)
    -- additive to the already-bindable ``listing_ref``/``density`` props
    (§14.18 J.19/J.20), never a replacement for them. ``review_count`` is
    ``None`` when absent (distinct from a real, honest zero)."""

    listing_id: str
    name: str
    profile_href: str
    area_label: str = ""
    rating_text: str = ""
    review_count: Optional[int] = None
    badge_kind: str = ""
    badge_label: str = ""
    cta: Optional[LinkSpec] = None


class ContactData(FrozenModel):
    """A profile's structured, clickable contact block. ``disclosure_text``
    (PILOT-PTF-1) is the listing's own ``ListingSponsorship.disclosure_text``
    when present -- rendered visibly alongside contact information so a
    sponsored listing's profile page carries the same honesty a sponsored
    card already does, never a fabricated default when the listing carries
    no sponsorship disclosure."""

    address_text: str = ""
    phone: Optional[LinkSpec] = None
    email: Optional[LinkSpec] = None
    website: Optional[LinkSpec] = None
    disclosure_text: str = ""


class HoursRow(FrozenModel):
    """One day's schedule -- never collapsed into an opaque joined string
    when structured ``ListingHoursEntry`` data exists."""

    day: str
    opens: str = ""
    closes: str = ""
    closed: bool = False


class HoursData(FrozenModel):
    rows: Tuple[HoursRow, ...] = ()


class ComponentRenderData(FrozenModel):
    """The render-data slice for exactly one ``ComponentInstance``. Every
    member is optional and independent -- a given instance carries only the
    member(s) its own emitter actually consumes (a nav component carries
    ``nav``; a listing card carries ``card``; never more than one component
    "kind" of data on one instance in Wave 1)."""

    nav: Optional[NavigationData] = None
    tiles: Optional[TileLinks] = None
    card: Optional[ListingCardData] = None
    contact: Optional[ContactData] = None
    hours: Optional[HoursData] = None


class RenderDataEntry(FrozenModel):
    """One ``(route, component_index)``-keyed render-data record -- the
    same positional identity ``LayoutContext``/``ComponentManifest`` already
    use (no new identity concept)."""

    route: str
    component_index: int
    data: ComponentRenderData


class RenderDataBundle(FrozenModel):
    """The whole build's render data: a flat, deterministically ordered
    tuple of entries. The Renderer builds its own ``(route,
    component_index) -> ComponentRenderData`` lookup from this at render
    time (the same pattern it already uses for ``ContentPackage.blocks`` ->
    ``content_index``) -- this bundle itself is not a lookup structure."""

    entries: Tuple[RenderDataEntry, ...] = ()


# ---------------------------------------------------------------------------
# Render-data-backed prop values (AES-WEB-002K.1)
# ---------------------------------------------------------------------------
#
# A required CONTENT_BLOCK_REF/LISTING_REF prop whose BindingState is
# RENDER_DATA (components/binding_rules.py) is bound to one of these
# generated keys instead of a ContentPackage-resolvable slot id
# (content_projection.generated_slot_id's "bind." form). The value is never
# looked up against ContentPackage -- the real data lives in this bundle,
# keyed by (route, component_index) -- so the "render:" prefix lets the
# Renderer recognize and skip the ContentPackage-lookup/missing-content
# check for exactly these props (renderer.py's _resolve_content), without
# teaching the Renderer any BindingState semantics.
_RENDER_DATA_PROP_PREFIX = "render:"


def generated_render_data_key(semantic_slot: str, component_index: int) -> str:
    """Deterministic, stable, positional key for a render-data-backed prop
    value -- mirrors ``content_projection.generated_slot_id``'s shape
    exactly, with the distinguishing ``"render:"`` prefix."""
    return "%s%s.%d" % (_RENDER_DATA_PROP_PREFIX, semantic_slot, component_index)


def is_render_data_prop_value(value: str) -> bool:
    """True iff ``value`` is a generated render-data key (as opposed to a
    real ContentPackage-resolvable generated slot id)."""
    return value.startswith(_RENDER_DATA_PROP_PREFIX)


# ---------------------------------------------------------------------------
# URL safety (documented duplication -- see module docstring)
# ---------------------------------------------------------------------------

_SAFE_URL_SCHEMES: FrozenSet[str] = frozenset({"http", "https", "mailto", "tel"})


def is_safe_url(url: str) -> bool:
    """Same grammar as ``rendering.html_emitter.is_safe_url`` /
    ``contracts.listing_dataset_validator._is_safe_url`` (documented
    duplication -- see module docstring): a same-origin-relative path, a
    bare fragment, or an explicitly whitelisted scheme. Rejects
    ``javascript:``, ``data:``, ``vbscript:``, protocol-relative
    ``//host/...``, and any other scheme. Called by the Component Engine's
    render-data producer before constructing a :class:`LinkSpec` --
    "the compiler," per the no-``@validator`` doctrine, not this module."""
    stripped = url.strip()
    if not stripped:
        return False
    if stripped.startswith("//"):
        return False
    if stripped.startswith("#") or stripped.startswith("/"):
        return True
    if ":" not in stripped:
        return True
    scheme = stripped.split(":", 1)[0].strip().lower()
    return scheme in _SAFE_URL_SCHEMES
