"""Atlas Directory — configuration contracts (niche-agnostic).

A directory product supplies one ``DirectoryConfig`` describing its brand, base
URL, navigation, footer, geographic-grouping terminology, and category set. The
reusable renderers read only from this config (plus per-page view models) — they
never hardcode a market, category, geography term, or navigation label.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional, Tuple

# Visual media families (niche-agnostic). A niche maps each of its categories to
# one family; the media renderer only knows families, never "hotel"/"park"/etc.
FAMILY_PRIMARY = "primary"    # deep brand tone (e.g. lodging)
FAMILY_NATURE = "nature"      # green (e.g. parks / outdoors)
FAMILY_WARM = "warm"          # accent tone (e.g. dining)
FAMILY_CITY = "city"          # place / map
FAMILY_BRAND = "brand"        # generic brand tile
VALID_FAMILIES = (FAMILY_PRIMARY, FAMILY_NATURE, FAMILY_WARM, FAMILY_CITY, FAMILY_BRAND)


@dataclass(frozen=True)
class NavItem:
    key: str
    label: str
    route: str


@dataclass(frozen=True)
class Cta:
    label: str
    href: str
    style: str = "accent"   # accent | ever | ghost | onhero


@dataclass(frozen=True)
class FooterColumn:
    title: str
    links: Tuple[Tuple[str, str], ...]   # (label, route)


@dataclass(frozen=True)
class GeoTerm:
    """Configurable geographic-grouping terminology. A grouping may present as a
    corridor, neighborhood, district, service area, region, etc."""
    singular: str = "area"
    plural: str = "areas"
    # e.g. "Explore the city" eyebrow / "Plan a … trip" — supplied by the niche.


@dataclass(frozen=True)
class CategoryDef:
    """One directory category. ``media_family`` selects the placeholder visual;
    ``glyph`` is one of the media glyph keys. All labels are niche-supplied."""
    key: str
    slug: str
    label: str
    media_family: str = FAMILY_PRIMARY
    glyph: str = FAMILY_BRAND


@dataclass(frozen=True)
class DirectoryConfig:
    brand_name: str
    brand_qualifier: str            # e.g. a market/region qualifier shown after the brand
    base_url: str
    nav: Tuple[NavItem, ...]
    header_cta: Cta
    footer_columns: Tuple[FooterColumn, ...]
    footer_tagline: str             # short brand line in the footer
    footer_copyright: str
    footer_disclosure: str
    geo_term: GeoTerm = field(default_factory=GeoTerm)
    categories: Tuple[CategoryDef, ...] = ()
    home_route: str = "/"

    def category(self, key: str) -> Optional[CategoryDef]:
        for c in self.categories:
            if c.key == key:
                return c
        return None
