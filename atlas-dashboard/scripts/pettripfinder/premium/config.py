"""PetTripFinder — the directory CONFIGURATION for the reusable Atlas Directory
system (scripts/atlas_directory/). Every PetTripFinder/Columbus-specific string,
navigation label, category, geographic term, and copy block lives here (or in
``adapter.py``) — the reusable renderers hold none of it. A second Atlas
directory replaces this module (and the adapters) and reuses the same components.
"""

from __future__ import annotations

from scripts.atlas_directory.config import (
    Cta, CategoryDef, DirectoryConfig, FooterColumn, GeoTerm, NavItem,
    FAMILY_NATURE, FAMILY_PRIMARY, FAMILY_WARM,
)

BASE_URL = "https://pettripfinder.com"

# Category set for this directory (niche categories -> reusable visual families).
CAT_HOTELS = CategoryDef("hotels", "pet-friendly-hotels", "Hotels", FAMILY_PRIMARY, "home")
CAT_PARKS = CategoryDef("parks", "pet-friendly-parks", "Parks", FAMILY_NATURE, "leaf")
CAT_RESTAURANTS = CategoryDef("restaurants", "pet-friendly-restaurants", "Restaurants", FAMILY_WARM, "fork")
CATEGORIES = (CAT_HOTELS, CAT_PARKS, CAT_RESTAURANTS)

CONFIG = DirectoryConfig(
    brand_name="PetTripFinder",
    brand_qualifier="Columbus",
    base_url=BASE_URL,
    nav=(
        NavItem("hotels", "Hotels", "/pet-friendly-hotels/"),
        NavItem("parks", "Parks", "/pet-friendly-parks/"),
        NavItem("restaurants", "Restaurants", "/pet-friendly-restaurants/"),
        NavItem("compare", "Compare", "/pet-friendly-hotels/policy-comparison/"),
        NavItem("verify", "How verification works", "/methodology/"),
    ),
    header_cta=Cta("Browse verified hotels", "/pet-friendly-hotels/", "accent"),
    footer_columns=(
        FooterColumn("Explore", (
            ("Pet-friendly hotels", "/pet-friendly-hotels/"),
            ("Dog parks & green space", "/pet-friendly-parks/"),
            ("Pet-friendly restaurants", "/pet-friendly-restaurants/"),
            ("Compare hotel policies", "/pet-friendly-hotels/policy-comparison/"),
        )),
        FooterColumn("Trust", (
            ("How we verify", "/methodology/"),
            ("What we verify", "/methodology/"),
            ("Photo policy", "/methodology/#photos"),
        )),
        FooterColumn("PetTripFinder", (
            ("About PetTripFinder", "/about/"),
            ("Contact", "/contact/"),
        )),
    ),
    footer_tagline=("Real pet policies, read straight from each business’s own official website "
                    "— so there are no surprises at check-in."),
    footer_copyright="© 2026 PetTripFinder · Your verified Columbus pet-travel guide.",
    footer_disclosure=("Some booking links are affiliate links; using them may earn PetTripFinder a "
                       "commission and never changes a property’s placement or its verified policy. "
                       "Pet policies can change — always confirm with the business before you travel."),
    geo_term=GeoTerm(singular="corridor", plural="corridors"),
    categories=CATEGORIES,
    home_route="/",
)


def category_by_slug(slug: str) -> CategoryDef:
    for c in CATEGORIES:
        if c.slug == slug:
            return c
    return CAT_HOTELS
