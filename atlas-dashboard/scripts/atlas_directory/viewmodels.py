"""Atlas Directory — typed view models (niche-agnostic).

Every reusable renderer takes one of these VMs plus a ``DirectoryConfig``. Plain
string fields are escaped by the renderer; fields documented as ``*_html`` carry
pre-rendered, pre-escaped HTML fragments produced by the niche adapter (e.g. a
listing's attribute chips, an evidence block, editorial prose), so the reusable
components compose rich pages without knowing any domain field.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Sequence, Tuple

from scripts.atlas_directory.config import FAMILY_PRIMARY


# --------------------------------------------------------------------------- #
# Atoms.
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class Crumb:
    label: str
    href: str = ""          # "" => current page


@dataclass(frozen=True)
class Badge:
    text: str
    state: str = "ok"       # ok | neutral | stop


@dataclass(frozen=True)
class FactChip:
    html: str               # pre-escaped fragment (may contain <b>)
    dim: bool = False


@dataclass(frozen=True)
class Action:
    label: str
    href: str
    style: str = "accent"   # accent | ever | ghost | onhero
    rel: str = ""
    external: bool = False


@dataclass(frozen=True)
class MediaSpec:
    """Placeholder-first media view model. ``family`` selects the visual; the
    remaining fields are shaped for a later real-media provider and never trigger
    a network call in this phase."""
    family: str = FAMILY_PRIMARY
    label: str = ""
    sublabel: str = ""
    initials: str = ""
    glyph: str = ""                     # media glyph key; defaults to family
    alt: str = ""
    # future media object (unused for rendering in this phase)
    source_type: str = "placeholder"    # placeholder | local | <provider>
    source_id: str = ""
    url: str = ""
    width: int = 0
    height: int = 0
    author_attribution: str = ""
    provider_attribution: str = ""
    loading_state: str = "idle"         # idle | loading | ready | error | missing


# --------------------------------------------------------------------------- #
# Shared section head.
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class SectionVM:
    eyebrow: str = ""
    heading: str = ""
    lead: str = ""                       # lead may contain inline markup (niche-supplied, trusted)
    center: bool = False


@dataclass(frozen=True)
class PageHeadVM:
    crumbs: Tuple[Crumb, ...]
    title: str
    lead: str = ""                       # trusted inline markup allowed


# --------------------------------------------------------------------------- #
# Cards.
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class CardVM:
    title: str
    route: str
    media: MediaSpec
    area_label: str = ""
    badge: Optional[Badge] = None
    chips: Tuple[FactChip, ...] = ()
    body_html: str = ""                  # optional pre-escaped body (e.g. a policy sentence)
    footnote: str = ""                   # e.g. verified date (plain text)
    link_label: str = "View details"


@dataclass(frozen=True)
class CategoryCardVM:
    title: str
    desc: str
    href: str
    media: MediaSpec
    cta_label: str = "Explore"


# --------------------------------------------------------------------------- #
# Home.
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class StatVM:
    value: str
    label: str


@dataclass(frozen=True)
class HeroVM:
    location_label: str
    headline: str
    subcopy: str
    primary: Action
    secondary: Action
    trust_points: Tuple[str, ...]
    media: MediaSpec
    badge_value: str = ""
    badge_label: str = ""


@dataclass(frozen=True)
class SearchFieldVM:
    label: str
    kind: str                            # "static" | "chips"
    static_html: str = ""                # for kind=static (pre-escaped)
    chips: Tuple[Action, ...] = ()       # for kind=chips


@dataclass(frozen=True)
class SearchVM:
    fields: Tuple[SearchFieldVM, ...]
    cta: Action
    note: str = ""


@dataclass(frozen=True)
class VsColumnVM:
    tag: str
    items: Tuple[str, ...]               # trusted inline markup allowed
    positive: bool                        # True => check icon (brand), False => x icon (muted)


@dataclass(frozen=True)
class VerifyVM:
    head: SectionVM
    generic: VsColumnVM
    ours: VsColumnVM
    cta: Optional[Action] = None


@dataclass(frozen=True)
class ExploreItemVM:
    title: str
    subtitle: str
    href: str


@dataclass(frozen=True)
class ExploreVM:
    head: SectionVM
    media: MediaSpec
    items: Tuple[ExploreItemVM, ...]


@dataclass(frozen=True)
class CtaBandVM:
    headline: str
    sub: str
    actions: Tuple[Action, ...]
    media: MediaSpec


@dataclass(frozen=True)
class HomeVM:
    hero: HeroVM
    search: SearchVM
    stats: Tuple[StatVM, ...]
    featured_head: SectionVM
    featured_cards: Tuple[CardVM, ...]
    featured_cta: Action
    categories_head: SectionVM
    categories: Tuple[CategoryCardVM, ...]
    verify: VerifyVM
    explore: ExploreVM
    cta_band: CtaBandVM


# --------------------------------------------------------------------------- #
# Listing / profile / comparison / editorial.
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class ListingVM:
    head: PageHeadVM
    cards: Tuple[CardVM, ...]
    note_html: str = ""                  # optional pre-escaped note above the grid


@dataclass(frozen=True)
class NearbyGroupVM:
    title: str
    items: Tuple[ExploreItemVM, ...]     # reuse (title, subtitle, href)


@dataclass(frozen=True)
class ProfileVM:
    crumbs: Tuple[Crumb, ...]
    area_label: str
    kind_label: str
    title: str
    media: MediaSpec
    intro_html: str = ""
    evidence_html: str = ""
    detail_html: str = ""                # e.g. address line (pre-escaped)
    actions: Tuple[Action, ...] = ()
    nearby: Tuple[NearbyGroupVM, ...] = ()
    # SEO
    meta_description: str = ""
    route: str = "/"
    active_nav: str = ""
    title_tag: str = ""


@dataclass(frozen=True)
class ComparisonVM:
    head: PageHeadVM
    identity_label: str                  # first column header (e.g. "Hotel")
    columns: Tuple[Tuple[str, str], ...] # (key, label) for remaining columns
    rows: Tuple[dict, ...]               # each: {"name","route", <col keys>...}
    caption: str
    not_stated_label: str = "Not stated"


@dataclass(frozen=True)
class EditorialVM:
    head: PageHeadVM
    prose_html: str                      # pre-escaped editorial HTML
