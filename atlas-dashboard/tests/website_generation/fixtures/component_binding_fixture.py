"""Curated deterministic fixture for the AES-WEB-002J.19 real-component-chain
integration test.

    HONESTLY-BINDABLE SUBSET ONLY -- NOT THE FULL CATALOG
    Distinct from the J.13 local demo fixture (which hand-binds every
    component) -- this fixture supplies only the *inputs* (SiteArchitecture,
    ContentPackage, ListingDataset, BrandPackage); the real Component Engine
    performs selection AND Phase-B binding.

Two routes, chosen because the J.19 architectural preflight established they
are the only page roles the current 72-component catalog can fully bind end
to end (AES-WEB-002 §26 "category"/"city"/"city-category"/"search-results"
all require a "pagination" or "zero_results" slot with no declared fallback,
whose only real candidates are categorically SOURCE_UNAVAILABLE/
STRUCTURED_DEFERRED -- an architectural gap, not a data gap):

* ``/`` (home) -- editorial content only.
* ``/hotels/lakeview-lodge/`` (business-profile) -- one real listing's data,
  bound by Phase B via ``ListingDataset``.

The Information Architecture Engine does not yet produce a
``business-profile`` page (it emits only ``home``/``category``), so
``SiteArchitecture`` is constructed directly here (an authorized fixture
technique -- ADR-WEB-LISTING-DATASET/ADR-WEB-CONTENT-BINDING-MAP precedent)
rather than via ``InformationArchitectureEngine.plan``.

Determinism: no clock, no UUID, no randomness, no environment variables, no
filesystem, no network, no runtime AI. ``BrandPackage`` is derived from the
pure, deterministic ``BrandEngine`` (the same J.13 precedent); every other
artifact is a hand-authored literal.
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

FIXTURE_SITE_NAME = "Atlas Binding Fixture"

HOME_ROUTE = "/"
PROFILE_ROUTE = "/hotels/lakeview-lodge/"
ROUTES: Tuple[str, ...] = (HOME_ROUTE, PROFILE_ROUTE)


@dataclass(frozen=True)
class BindingFixtureInputs:
    """The four ``ComponentEngine.compile()`` inputs plus the SEOPackage the
    Assembly/Quality-Gate stages need. Fixture-local value type -- not a WGE
    artifact bundle and not a registered schema."""

    site_architecture: SiteArchitecture
    content_package: ContentPackage
    listing_dataset: ListingDataset
    brand_package: BrandPackage
    seo_package: SEOPackage
    routes: Tuple[str, ...]


def _brand_package() -> BrandPackage:
    spec = BusinessSpec(
        schema_version=SCHEMA_VERSIONS[ArtifactKind.BUSINESS_SPEC],
        artifact_kind=ArtifactKind.BUSINESS_SPEC,
        source_hashes={},
        business_name=FIXTURE_SITE_NAME,
        niche="pet travel",
        audience="pet owners",
        value_proposition="find pet-friendly places",
    )
    return BrandEngine().resolve(spec)


def _site_architecture() -> SiteArchitecture:
    pages = (
        PagePlan(route=HOME_ROUTE, page_type="home", title="Home"),
        PagePlan(route=PROFILE_ROUTE, page_type="business-profile", title="Lakeview Lodge"),
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
    # Only the home route's editorial hero content -- everything the
    # business-profile route's bindable components need comes from
    # ListingDataset via Phase B projection, per design. footer_legal/
    # disclosures (AES-WEB-002K.1, D5) are needed on both routes: with
    # nav.header.standard/legal.footer.directory now categorically
    # bindable (RENDER_DATA), the site shell recipe slots select them
    # whenever the pilot registry offers them, and Phase B then requires
    # real content for legal.footer.directory's required content slots
    # regardless of the shell slot's own optional/required status.
    blocks = (
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
            page_route=HOME_ROUTE, slot_id="footer_legal",
            text="(c) 2026 Atlas Binding Fixture. All rights reserved.",
        ),
        ContentBlock(
            page_route=HOME_ROUTE, slot_id="disclosures",
            text="Some listings may be sponsored placements, clearly labeled.",
        ),
        ContentBlock(
            page_route=PROFILE_ROUTE, slot_id="footer_legal",
            text="(c) 2026 Atlas Binding Fixture. All rights reserved.",
        ),
        ContentBlock(
            page_route=PROFILE_ROUTE, slot_id="disclosures",
            text="Some listings may be sponsored placements, clearly labeled.",
        ),
    )
    return ContentPackage(
        schema_version=SCHEMA_VERSIONS[ArtifactKind.CONTENT_PACKAGE],
        artifact_kind=ArtifactKind.CONTENT_PACKAGE,
        source_hashes={},
        blocks=blocks,
    )


def _listing_dataset() -> ListingDataset:
    category = ListingCategory(category_id="cat-hotels", label="Hotels", slug="hotels")
    listing = ListingRecord(
        listing_id="lakeview-lodge",
        business_name="Lakeview Lodge",
        slug="lakeview-lodge",
        category_id="cat-hotels",
        description="A lakeside lodge with fenced runs and on-site pet-sitting.",
        listing_kind=ListingKind.ORGANIC,
        contact=ListingContact(phone="555-0100", email="stay@lakeview.example"),
        address=ListingAddress(city="Austin", state="TX", country="US"),
        hours=(
            ListingHoursEntry(day=Weekday.MONDAY, opens="08:00", closes="20:00"),
            ListingHoursEntry(day=Weekday.TUESDAY, opens="08:00", closes="20:00"),
            ListingHoursEntry(day=Weekday.WEDNESDAY, opens="08:00", closes="20:00"),
            ListingHoursEntry(day=Weekday.THURSDAY, opens="08:00", closes="20:00"),
            ListingHoursEntry(day=Weekday.FRIDAY, opens="08:00", closes="20:00"),
            ListingHoursEntry(day=Weekday.SATURDAY, opens="09:00", closes="18:00"),
            ListingHoursEntry(day=Weekday.SUNDAY, closed=True),
        ),
        rating=ListingRating(rating_hundredths=460, review_count=132),
        credentials=("Licensed pet boarding operator", "Insured and bonded"),
        sponsorship=ListingSponsorship(kind=ListingKind.ORGANIC, disclosure_text=""),
    )
    return ListingDataset(
        schema_version=SCHEMA_VERSIONS[ArtifactKind.LISTING_DATASET],
        artifact_kind=ArtifactKind.LISTING_DATASET,
        source_hashes={},
        listings=(listing,),
        categories=(category,),
        locations=(),
    )


def _seo_package() -> SEOPackage:
    entries = tuple(
        SEOEntry(
            route=route,
            title="%s - %s" % (FIXTURE_SITE_NAME, route),
            meta_description="Binding-fixture demo page for %s" % route,
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


def build_binding_fixture_inputs() -> BindingFixtureInputs:
    """Build the deterministic Phase-B input set. Pure: same output on every
    call, no I/O."""
    return BindingFixtureInputs(
        site_architecture=_site_architecture(),
        content_package=_content_package(),
        listing_dataset=_listing_dataset(),
        brand_package=_brand_package(),
        seo_package=_seo_package(),
        routes=ROUTES,
    )
