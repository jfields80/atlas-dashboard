"""SEO blueprint planner.

Deterministic engine producing Section 7 (SEO Blueprint). Pure functions of
the opportunity input and the already-planned directory architecture.
"""

from __future__ import annotations

from typing import List

from engines.directory_blueprint.blueprint_models import (
    DirectoryArchitecture,
    KeywordCluster,
    OpportunityInput,
    SEOBlueprint,
)
from engines.directory_blueprint.category_planner import slugify

# ---------------------------------------------------------------------------
# Named constants
# ---------------------------------------------------------------------------

SCHEMA_MARKUP_TYPES = (
    "LocalBusiness (per listing)",
    "AggregateRating (per listing with reviews)",
    "BreadcrumbList (all hierarchy pages)",
    "FAQPage (FAQ hubs and listing FAQs)",
    "ItemList (category and location index pages)",
    "Organization + WebSite with SearchAction (sitewide)",
)

INTERNAL_LINKING_RULES = (
    "Every listing links up to its city page, category page, and category-in-city page",
    "Category pages cross-link sibling categories and top 10 listings",
    "Location pages link parent and child locations plus top categories in that location",
    "Guides link to the 3-5 most relevant category-in-city pages, never to raw search URLs",
    "Homepage links only to top-level categories, top locations, and newest guides",
)

FAQ_TOPIC_TEMPLATES = (
    "How to choose a {niche} provider",
    "Average cost of {niche}",
    "Questions to ask before hiring in {niche}",
    "{niche} licensing and certification basics",
    "How reviews and verification work on this site",
)

BLOG_TEMPLATES = (
    "Best {niche} options in {market}",
    "{niche} pricing guide for {market}",
    "Seasonal {niche} checklist",
    "How we verify {niche} listings",
    "{niche} trends this year",
)

PROGRAMMATIC_TEMPLATES = (
    "'best {category} in {city}' pages generated from listing density thresholds",
    "'{category} near {neighborhood}' pages for metros with >= 20 listings",
    "'{category} open now in {city}' powered by hours data",
    "comparison pages: '{listing A} vs {listing B}' for top-2 listings per category-city",
    "cost pages: '{category} cost in {state}' from aggregated pricing attributes",
)


def _fill(template: str, niche: str, market: str) -> str:
    return template.replace("{niche}", niche).replace("{market}", market)


def build_keyword_clusters(opportunity: OpportunityInput) -> List[KeywordCluster]:
    niche = opportunity.niche.lower()
    return [
        KeywordCluster(
            theme="Category + location intent",
            example_keywords=[
                "%s near me" % niche,
                "best %s in {city}" % niche,
                "%s {city} {state}" % niche,
            ],
            target_page_type="category-in-location pages",
        ),
        KeywordCluster(
            theme="Cost and pricing intent",
            example_keywords=[
                "%s cost" % niche,
                "how much does %s cost" % niche,
                "%s pricing" % niche,
            ],
            target_page_type="cost guide pages",
        ),
        KeywordCluster(
            theme="Comparison and evaluation intent",
            example_keywords=[
                "best %s" % niche,
                "%s reviews" % niche,
                "top rated %s" % niche,
            ],
            target_page_type="ranked list and comparison pages",
        ),
        KeywordCluster(
            theme="Informational intent",
            example_keywords=[
                "how to choose %s" % niche,
                "%s guide" % niche,
                "what to look for in %s" % niche,
            ],
            target_page_type="guides and FAQ hub",
        ),
    ]


def plan_seo(opportunity: OpportunityInput, architecture: DirectoryArchitecture) -> SEOBlueprint:
    niche = opportunity.niche
    market = opportunity.primary_market
    niche_slug = slugify(niche)

    category_pages = ["/%s/" % node.slug for node in architecture.category_tree]
    location_pages = [
        "/{state}/",
        "/{state}/{city}/",
        "/{state}/{city}/%s/" % (category_pages[0].strip("/") if category_pages else niche_slug),
    ]

    return SEOBlueprint(
        url_structure=list(architecture.url_hierarchy),
        content_silos=[
            "Directory silo: category -> category-in-location -> listing",
            "Guides silo: /guides/ hub -> topic guides -> linked category pages",
            "FAQ silo: /faq/ hub -> question pages -> linked guides",
            "Cost silo: /costs/ hub -> per-category cost pages",
        ],
        landing_pages=[
            "/ (primary market home)",
            "/best-%s/" % niche_slug,
            "/claim/ (business owner acquisition)",
            "/costs/%s/" % niche_slug,
        ],
        category_pages=category_pages,
        location_pages=location_pages,
        faq_topics=[_fill(t, niche, market) for t in FAQ_TOPIC_TEMPLATES],
        blog_opportunities=[_fill(t, niche, market) for t in BLOG_TEMPLATES],
        schema_markup=list(SCHEMA_MARKUP_TYPES),
        internal_linking_strategy=list(INTERNAL_LINKING_RULES),
        keyword_clusters=build_keyword_clusters(opportunity),
        programmatic_seo_opportunities=list(PROGRAMMATIC_TEMPLATES),
    )
