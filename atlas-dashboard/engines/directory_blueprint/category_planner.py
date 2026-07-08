"""Category / location / navigation architecture planner.

Deterministic engine. No database access, no Flask, no side effects.
All heuristics are expressed as named constants so every output is
explainable and reproducible for a given input.
"""

from __future__ import annotations

import re
from typing import List, Tuple

from engines.directory_blueprint.blueprint_models import (
    CategoryNode,
    DirectoryArchitecture,
    DirectoryType,
    GeographicScope,
    LocationHierarchy,
    NavigationNode,
    OpportunityInput,
)

# ---------------------------------------------------------------------------
# Named constants
# ---------------------------------------------------------------------------

DIRECTORY_TYPE_KEYWORDS: List[Tuple[DirectoryType, Tuple[str, ...]]] = [
    (DirectoryType.TRAVEL, ("travel", "hotel", "trip", "vacation", "tourism", "destination")),
    (DirectoryType.EDUCATION, ("school", "training", "course", "class", "academy", "education", "martial")),
    (DirectoryType.B2B, ("b2b", "wholesale", "supplier", "manufacturer", "agency", "vendor")),
    (DirectoryType.MARKETPLACE, ("marketplace", "buy", "sell", "farm", "beef", "shop")),
    (DirectoryType.LOCAL_SERVICES, ("service", "repair", "contractor", "plumber", "groomer", "clinic", "vet", "trades")),
]
DEFAULT_DIRECTORY_TYPE = DirectoryType.NICHE_INTEREST

BASE_SUBCATEGORIES: Tuple[str, ...] = (
    "Top Rated",
    "Budget Friendly",
    "Premium",
    "New Listings",
)

DIRECTORY_TYPE_CATEGORY_TEMPLATES = {
    DirectoryType.TRAVEL: ("Destinations", "Accommodations", "Activities", "Dining", "Travel Guides"),
    DirectoryType.EDUCATION: ("Programs", "Providers", "Age Groups", "Skill Levels", "Resources"),
    DirectoryType.B2B: ("Providers", "Industries", "Services", "Certifications", "Resources"),
    DirectoryType.MARKETPLACE: ("Sellers", "Products", "Regions", "Deals", "Guides"),
    DirectoryType.LOCAL_SERVICES: ("Services", "Providers", "Specialties", "Emergency", "Resources"),
    DirectoryType.NICHE_INTEREST: ("Listings", "Categories", "Regions", "Featured", "Guides"),
}

SCOPE_LOCATION_LEVELS = {
    GeographicScope.NATIONAL: ["Country", "State", "County", "City", "Neighborhood"],
    GeographicScope.REGIONAL: ["Region", "State", "County", "City", "Neighborhood"],
    GeographicScope.STATE: ["State", "County", "City", "Neighborhood"],
    GeographicScope.METRO: ["Metro", "City", "Neighborhood"],
    GeographicScope.CITY: ["City", "Neighborhood"],
}

STANDARD_TAGS: Tuple[str, ...] = (
    "verified",
    "featured",
    "premium",
    "new",
    "popular",
    "editor-pick",
)

STANDARD_AMENITIES: Tuple[str, ...] = (
    "parking",
    "wheelchair-accessible",
    "online-booking",
    "open-weekends",
    "free-consultation",
)

STANDARD_ATTRIBUTES: Tuple[str, ...] = (
    "price-range",
    "years-in-business",
    "rating",
    "review-count",
    "response-time",
)

CANONICAL_STRATEGY_RULES: Tuple[str, ...] = (
    "Every listing has exactly one canonical URL: /{state}/{city}/{category}/{listing-slug}/",
    "Category x location pages canonicalize to themselves; filtered/sorted variants canonicalize to the unfiltered page",
    "Pagination uses rel=next/prev semantics with self-referencing canonicals per page",
    "Tag and amenity facet pages are noindex,follow until they earn distinct search demand",
    "www vs non-www and trailing-slash policy enforced via 301 at the edge",
)

PARENT_CHILD_RULES: Tuple[str, ...] = (
    "Category -> Subcategory: one parent per subcategory, max depth 2",
    "Location: strict containment chain (State > County > City > Neighborhood)",
    "Listing -> Category: one primary category, unlimited secondary categories",
    "Listing -> Location: one physical location node; service-area listings map to multiple cities",
)

RELATIONSHIP_DIAGRAM = (
    "Business (1) --< Reviews (N)\n"
    "Business (1) --< Images (N)\n"
    "Business (N) >--< Categories (N) via business_categories\n"
    "Business (N) >-- Location (1)\n"
    "Business (1) --< Claims (N) >-- Owner (1)\n"
    "Owner (1) --< Subscriptions (N)\n"
    "Business (1) --< PremiumListings / Coupons / Events / Jobs (N)\n"
    "Category (1) --< Subcategory (N)\n"
    "Location (1) --< ChildLocation (N)"
)

_SLUG_STRIP_RE = re.compile(r"[^a-z0-9]+")


def slugify(text: str) -> str:
    """Deterministic slug: lowercase, alphanumerics joined by hyphens."""
    return _SLUG_STRIP_RE.sub("-", text.lower()).strip("-")


def infer_directory_type(opportunity: OpportunityInput) -> DirectoryType:
    """Keyword-driven, first-match-wins classification of the directory type."""
    haystack = " ".join([opportunity.niche, opportunity.name, opportunity.description]).lower()
    for directory_type, keywords in DIRECTORY_TYPE_KEYWORDS:
        if any(keyword in haystack for keyword in keywords):
            return directory_type
    return DEFAULT_DIRECTORY_TYPE


def build_category_tree(opportunity: OpportunityInput, directory_type: DirectoryType) -> List[CategoryNode]:
    """Top-level categories from the type template, each with standard subcategories."""
    tree: List[CategoryNode] = []
    for top_name in DIRECTORY_TYPE_CATEGORY_TEMPLATES[directory_type]:
        subs = [CategoryNode(name=s, slug=slugify(s)) for s in BASE_SUBCATEGORIES]
        tree.append(CategoryNode(name=top_name, slug=slugify(top_name), subcategories=subs))
    return tree


def build_location_hierarchy(scope: GeographicScope, primary_market: str) -> LocationHierarchy:
    levels = list(SCOPE_LOCATION_LEVELS[scope])
    market_slug = slugify(primary_market) or "market"
    example_paths = [
        "/" + "/".join(slugify(level) for level in levels[: i + 1]) + "/"
        for i in range(len(levels))
    ]
    example_paths.append("/%s/ (primary market root)" % market_slug)
    return LocationHierarchy(levels=levels, example_paths=example_paths)


def build_navigation_tree(category_tree: List[CategoryNode]) -> List[NavigationNode]:
    nav: List[NavigationNode] = [
        NavigationNode(label="Home", url_pattern="/"),
        NavigationNode(
            label="Browse",
            url_pattern="/browse/",
            children=[
                NavigationNode(label=c.name, url_pattern="/%s/" % c.slug) for c in category_tree
            ],
        ),
        NavigationNode(label="Locations", url_pattern="/locations/"),
        NavigationNode(label="Search", url_pattern="/search/"),
        NavigationNode(label="Add Your Business", url_pattern="/claim/"),
        NavigationNode(label="Guides", url_pattern="/guides/"),
    ]
    return nav


def build_url_hierarchy(category_tree: List[CategoryNode]) -> List[str]:
    urls = [
        "/",
        "/search/",
        "/locations/",
        "/{state}/",
        "/{state}/{city}/",
        "/{state}/{city}/{category}/",
        "/{state}/{city}/{category}/{listing-slug}/",
        "/guides/{guide-slug}/",
        "/faq/",
    ]
    urls.extend("/%s/" % c.slug for c in category_tree)
    return urls


def plan_directory_architecture(opportunity: OpportunityInput) -> DirectoryArchitecture:
    """Assemble the full Section 2 architecture. Pure function of its input."""
    directory_type = infer_directory_type(opportunity)
    category_tree = build_category_tree(opportunity, directory_type)
    return DirectoryArchitecture(
        category_tree=category_tree,
        location_hierarchy=build_location_hierarchy(
            opportunity.geographic_scope, opportunity.primary_market
        ),
        tags=list(STANDARD_TAGS),
        amenities=list(STANDARD_AMENITIES),
        attributes=list(STANDARD_ATTRIBUTES),
        relationship_diagram=RELATIONSHIP_DIAGRAM,
        parent_child_rules=list(PARENT_CHILD_RULES),
        navigation_tree=build_navigation_tree(category_tree),
        url_hierarchy=build_url_hierarchy(category_tree),
        canonical_strategy=list(CANONICAL_STRATEGY_RULES),
    )
