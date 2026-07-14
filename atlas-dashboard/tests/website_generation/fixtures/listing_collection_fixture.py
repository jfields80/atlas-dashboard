"""Curated deterministic fixture for the AES-WEB-002J.20 listing-repetition
real-chain integration test.

    HONESTLY-BINDABLE SUBSET ONLY -- NOT THE FULL CATALOG
    Distinct from the J.13 local demo fixture (hand-binds every component)
    and the J.19 ``component_binding_fixture`` (one listing, no repetition)
    -- this fixture supplies inputs for THREE routes so both v1 repetition
    rules (``composition_rules.COMPOSITION_RULES``) get a real, non-trivial
    match set:

* ``/`` (home) -- editorial content only, unchanged pattern from J.19.
* ``/hotels/`` (category) -- the amended category recipe (structural
  ``layout.stack.standard`` fallback on ``pagination``/``zero_results``,
  AES-WEB-002J.20) plus five real listings, proving P2: ``listing_cards``
  expands to five ``listing.card.standard`` instances.
* ``/hotels/alpine-lantern-lodge/`` (business-profile) -- one of the five
  listings as the page's own; proving P1: ``related_listings`` expands to
  the other four (``exclude_self=True`` drops the page's own listing).

Five listings, deterministic, collision-free business names (no shared
prefixes/substrings that could mask an ordering or slot-id bug): Alpine
Lantern Lodge, Cedar Harbor Inn, Maple Ridge Retreat, Northstar Guest House,
Willow Creek Suites. Every listing carries full contact/hours/credentials
data (not just the hosting page's own) so P1's related-listing cards and
P2's listing cards both bind real, non-placeholder content -- not only the
minimum ``listing.card.standard`` structurally requires (``listing_ref``,
``density``).

The Information Architecture Engine does not yet produce a
``business-profile`` page and its ``category`` output uses a different route
convention than ADR-WEB-LISTING-DATASET's exact-match derivation, so
``SiteArchitecture`` is constructed directly here (the same authorized
fixture technique the J.19 fixture already established) rather than via
``InformationArchitectureEngine.plan``.

Determinism: no clock, no UUID, no randomness, no environment variables, no
filesystem, no network, no runtime AI. ``BrandPackage`` is derived from the
pure, deterministic ``BrandEngine``; every other artifact is a hand-authored
literal.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

from engines.website_generation.brand.brand_engine import BrandEngine
from engines.website_generation.contracts.artifacts import (
    BrandPackage,
    BusinessSpec,
    ContentBlock,
    ContentPackage,
    ListingAddress,
    ListingCategory,
    ListingContact,
    ListingDataset,
    ListingHoursEntry,
    ListingRating,
    ListingRecord,
    ListingSponsorship,
    PagePlan,
    SEOEntry,
    SEOPackage,
    SiteArchitecture,
)
from engines.website_generation.contracts.enums import ArtifactKind, ListingKind, Weekday
from engines.website_generation.contracts.versions import SCHEMA_VERSIONS

FIXTURE_SITE_NAME = "Atlas Listing Collection Fixture"

HOME_ROUTE = "/"
CATEGORY_ROUTE = "/hotels/"
PROFILE_ROUTE = "/hotels/alpine-lantern-lodge/"
ROUTES: Tuple[str, ...] = (HOME_ROUTE, CATEGORY_ROUTE, PROFILE_ROUTE)

# The page's own listing for PROFILE_ROUTE -- excluded from its own
# related_listings collection (exclude_self=True). The other four are the
# P1 proof's expected related-listing set, in ListingDataset tuple order.
_HOSTING_LISTING_SLUG = "alpine-lantern-lodge"


@dataclass(frozen=True)
class ListingCollectionFixtureInputs:
    """The four ``ComponentEngine.compile()`` inputs plus the SEOPackage the
    Assembly/Quality-Gate stages need. Fixture-local value type -- not a WGE
    artifact bundle and not a registered schema."""

    site_architecture: SiteArchitecture
    content_package: ContentPackage
    listing_dataset: ListingDataset
    brand_package: BrandPackage
    seo_package: SEOPackage
    routes: Tuple[str, ...]
    category_route: str
    profile_route: str
    hosting_listing_slug: str


def _brand_package() -> BrandPackage:
    spec = BusinessSpec(
        schema_version=SCHEMA_VERSIONS[ArtifactKind.BUSINESS_SPEC],
        artifact_kind=ArtifactKind.BUSINESS_SPEC,
        source_hashes={},
        business_name=FIXTURE_SITE_NAME,
        niche="pet travel",
        audience="pet owners",
        value_proposition="find pet-friendly places to stay",
    )
    return BrandEngine().resolve(spec)


def _site_architecture() -> SiteArchitecture:
    pages = (
        PagePlan(route=HOME_ROUTE, page_type="home", title="Home"),
        PagePlan(route=CATEGORY_ROUTE, page_type="category", title="Hotels"),
        PagePlan(
            route=PROFILE_ROUTE, page_type="business-profile", title="Alpine Lantern Lodge"
        ),
    )
    return SiteArchitecture(
        schema_version=SCHEMA_VERSIONS[ArtifactKind.SITE_ARCHITECTURE],
        artifact_kind=ArtifactKind.SITE_ARCHITECTURE,
        source_hashes={},
        pages=pages,
        nav_routes=ROUTES,
        sitemap_routes=ROUTES,
    )


def _content_package() -> ContentPackage:
    # Home and category routes need editorial hero content (no ListingDataset
    # source exists for either slot); business-profile needs none for its
    # own listing fields -- every bindable field there comes from
    # ListingDataset via Phase B projection. footer_legal/disclosures
    # (AES-WEB-002K.1, D5) are needed on every route: with
    # nav.header.standard/legal.footer.directory now categorically bindable
    # (RENDER_DATA), the site shell recipe slots select them whenever the
    # pilot registry offers them, and Phase B then requires real content for
    # legal.footer.directory's required content slots regardless of the
    # shell slot's own optional/required status.
    blocks = [
        ContentBlock(
            page_route=HOME_ROUTE, slot_id="hero_h1",
            text="Find pet-friendly places to stay",
        ),
        ContentBlock(
            page_route=HOME_ROUTE, slot_id="intro",
            text="Browse trusted, pet-welcoming businesses across the country.",
        ),
        ContentBlock(
            page_route=HOME_ROUTE, slot_id="subhead",
            text="Verified hotels, parks, and restaurants that welcome pets.",
        ),
        ContentBlock(
            page_route=HOME_ROUTE, slot_id="message",
            text="Some listings are sponsored placements, clearly labeled.",
        ),
        ContentBlock(
            page_route=CATEGORY_ROUTE, slot_id="hero_h1",
            text="Pet-friendly hotels",
        ),
        ContentBlock(
            page_route=CATEGORY_ROUTE, slot_id="intro",
            text="Hotels that welcome your pets, verified by our team.",
        ),
    ]
    for route in ROUTES:
        blocks.append(ContentBlock(
            page_route=route, slot_id="footer_legal",
            text="(c) 2026 Atlas Listing Collection Fixture. All rights reserved.",
        ))
        blocks.append(ContentBlock(
            page_route=route, slot_id="disclosures",
            text="Some listings may be sponsored placements, clearly labeled.",
        ))
    return ContentPackage(
        schema_version=SCHEMA_VERSIONS[ArtifactKind.CONTENT_PACKAGE],
        artifact_kind=ArtifactKind.CONTENT_PACKAGE,
        source_hashes={},
        blocks=tuple(blocks),
    )


def _listing(listing_id, slug, business_name, city, phone_suffix, rating_hundredths, review_count):
    return ListingRecord(
        listing_id=listing_id,
        business_name=business_name,
        slug=slug,
        category_id="cat-hotels",
        description="%s welcomes pets with open arms and fenced play areas." % business_name,
        listing_kind=ListingKind.ORGANIC,
        contact=ListingContact(
            phone="555-01%s" % phone_suffix, email="%s@example.com" % slug.replace("-", "")
        ),
        address=ListingAddress(city=city, state="CO", country="US"),
        hours=(
            ListingHoursEntry(day=Weekday.MONDAY, opens="08:00", closes="20:00"),
            ListingHoursEntry(day=Weekday.TUESDAY, opens="08:00", closes="20:00"),
            ListingHoursEntry(day=Weekday.WEDNESDAY, opens="08:00", closes="20:00"),
            ListingHoursEntry(day=Weekday.THURSDAY, opens="08:00", closes="20:00"),
            ListingHoursEntry(day=Weekday.FRIDAY, opens="08:00", closes="20:00"),
            ListingHoursEntry(day=Weekday.SATURDAY, opens="09:00", closes="18:00"),
            ListingHoursEntry(day=Weekday.SUNDAY, closed=True),
        ),
        rating=ListingRating(rating_hundredths=rating_hundredths, review_count=review_count),
        credentials=("Licensed pet boarding operator", "Insured and bonded"),
        sponsorship=ListingSponsorship(kind=ListingKind.ORGANIC, disclosure_text=""),
    )


def _listing_dataset() -> ListingDataset:
    category = ListingCategory(category_id="cat-hotels", label="Hotels", slug="hotels")
    listings = (
        _listing(
            "alpine-lantern-lodge", "alpine-lantern-lodge", "Alpine Lantern Lodge",
            "Aspen", "00", 470, 88,
        ),
        _listing(
            "cedar-harbor-inn", "cedar-harbor-inn", "Cedar Harbor Inn",
            "Breckenridge", "01", 440, 61,
        ),
        _listing(
            "maple-ridge-retreat", "maple-ridge-retreat", "Maple Ridge Retreat",
            "Vail", "02", 490, 205,
        ),
        _listing(
            "northstar-guest-house", "northstar-guest-house", "Northstar Guest House",
            "Telluride", "03", 420, 34,
        ),
        _listing(
            "willow-creek-suites", "willow-creek-suites", "Willow Creek Suites",
            "Estes Park", "04", 455, 97,
        ),
    )
    return ListingDataset(
        schema_version=SCHEMA_VERSIONS[ArtifactKind.LISTING_DATASET],
        artifact_kind=ArtifactKind.LISTING_DATASET,
        source_hashes={},
        listings=listings,
        categories=(category,),
        locations=(),
    )


def _seo_package() -> SEOPackage:
    entries = tuple(
        SEOEntry(
            route=route,
            title="%s - %s" % (FIXTURE_SITE_NAME, route),
            meta_description="Listing-collection fixture demo page for %s" % route,
            canonical_url=route,
        )
        for route in ROUTES
    )
    return SEOPackage(
        schema_version=SCHEMA_VERSIONS[ArtifactKind.SEO_PACKAGE],
        artifact_kind=ArtifactKind.SEO_PACKAGE,
        source_hashes={},
        entries=entries,
        sitemap_routes=ROUTES,
        robots_directives=("User-agent: *", "Allow: /"),
    )


def build_listing_collection_fixture_inputs() -> ListingCollectionFixtureInputs:
    """Build the deterministic Phase-B input set. Pure: same output on every
    call, no I/O."""
    return ListingCollectionFixtureInputs(
        site_architecture=_site_architecture(),
        content_package=_content_package(),
        listing_dataset=_listing_dataset(),
        brand_package=_brand_package(),
        seo_package=_seo_package(),
        routes=ROUTES,
        category_route=CATEGORY_ROUTE,
        profile_route=PROFILE_ROUTE,
        hosting_listing_slug=_HOSTING_LISTING_SLUG,
    )
