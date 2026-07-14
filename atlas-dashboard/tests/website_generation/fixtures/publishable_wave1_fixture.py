"""Curated deterministic fixture for the AES-WEB-002K.1 publishable Wave-1
integration test.

    HONESTLY-BINDABLE, GENUINELY NAVIGABLE SUBSET
    Distinct from every earlier fixture in this test tree
    (``component_binding_fixture.py`` J.19, ``listing_collection_fixture.py``
    J.20): this fixture's ``SiteArchitecture`` is not hand-built. It is
    produced by the real ``InformationArchitectureEngine.plan(spec, brand,
    listing_dataset=...)`` call (AES-WEB-002K.1) -- the actual proof that IA
    now emits real, human-titled home/category pages plus one
    business-profile ``PagePlan`` per ``ListingRecord``, exactly the way a
    production caller would build it.

Five listings, deterministic, collision-free business names: Alpine Lantern
Lodge, Cedar Harbor Inn, Maple Ridge Retreat, Northstar Guest House, Willow
Creek Suites -- all under one category ("Hotels", matching
``BusinessSpec.directory_taxonomy`` exactly, so the ListingDataset's own
category and IA's taxonomy-derived category route land on the identical
``/hotels/`` route). Deliberately varied data coverage, not uniform:

* four of five listings carry a rating/review count; one does not (proves
  optional enrichment is omitted, never fabricated, never a compile
  failure).
* one listing (Cedar Harbor Inn) is ``ListingKind.VERIFIED`` (a real badge)
  and carries a real outbound ``ListingCTA`` (an external booking link) --
  proving badge/CTA production without ever selecting a
  sponsored/featured card *variant* (AES-WEB-002J.20 decision #11: v1
  repeats one recipe-selected definition uniformly).
* every listing carries full contact (phone/email) and a full 7-day
  ``hours`` schedule, including one closed day (Sunday) -- proving the
  structured hours table's "Closed" row, not just open hours.
* no listing carries an image/asset reference -- Wave 1 explicitly ships
  no images (no asset store exists yet).

Generic directory content throughout -- never PetTripFinder-specific
copy, names, or domain (AES-WEB-002K.1 is the generic engine capability;
PetTripFinder productization is explicitly out of scope, Wave 2).

Determinism: no clock, no UUID, no randomness, no environment variables, no
filesystem, no network, no runtime AI. ``BrandPackage`` is derived from the
pure, deterministic ``BrandEngine``; ``SiteArchitecture`` is derived from
the pure, deterministic ``InformationArchitectureEngine``; every other
artifact is a hand-authored literal.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Tuple

from engines.website_generation.brand.brand_engine import BrandEngine
from engines.website_generation.ia.information_architecture_engine import (
    InformationArchitectureEngine,
)
from engines.website_generation.contracts.artifacts import (
    BrandPackage,
    BusinessSpec,
    ContentBlock,
    ContentPackage,
    ListingAddress,
    ListingCategory,
    ListingContact,
    ListingCTA,
    ListingDataset,
    ListingHoursEntry,
    ListingRating,
    ListingRecord,
    ListingSponsorship,
    SiteArchitecture,
)
from engines.website_generation.contracts.enums import ArtifactKind, ListingKind, Weekday
from engines.website_generation.contracts.versions import SCHEMA_VERSIONS

FIXTURE_SITE_NAME = "Atlas Publishable Directory"
CATEGORY_TAXONOMY_ENTRY = "Hotels"
CATEGORY_SLUG = "hotels"
CATEGORY_ROUTE = "/hotels/"
HOME_ROUTE = "/"
BASE_URL = "https://example.com"

# The listing whose CTA/badge proves those two enrichment paths.
_VERIFIED_LISTING_SLUG = "cedar-harbor-inn"
# The listing intentionally left without a rating (proves honest omission).
_UNRATED_LISTING_SLUG = "northstar-guest-house"


@dataclass(frozen=True)
class PublishableWave1FixtureInputs:
    """The inputs a real publishable-pilot acceptance run needs: IA's own
    inputs (spec/brand/listing_dataset), the IA-*produced* SiteArchitecture,
    and the ContentPackage the Component Engine's Phase B (and the SEO
    Engine's D1/D2 title/meta composition) need. Deliberately excludes a
    pre-built SEOPackage -- the integration test calls the real, K.1-upgraded
    ``SEOEngine().compile(..., base_url=base_url)`` itself, proving that
    engine's ``base_url``/business-profile-role additions rather than
    bypassing them with a hand-built artifact. Fixture-local value type --
    not a WGE artifact bundle and not a registered schema."""

    business_spec: BusinessSpec
    brand_package: BrandPackage
    listing_dataset: ListingDataset
    site_architecture: SiteArchitecture
    content_package: ContentPackage
    base_url: str
    home_route: str
    category_route: str
    profile_routes: Tuple[str, ...]
    verified_listing_route: str


def _business_spec() -> BusinessSpec:
    return BusinessSpec(
        schema_version=SCHEMA_VERSIONS[ArtifactKind.BUSINESS_SPEC],
        artifact_kind=ArtifactKind.BUSINESS_SPEC,
        source_hashes={},
        business_name=FIXTURE_SITE_NAME,
        niche="local business directory",
        audience="people looking for a place to stay",
        value_proposition="find trustworthy, well-reviewed hotels",
        directory_taxonomy=(CATEGORY_TAXONOMY_ENTRY,),
    )


def _listing(
    listing_id: str,
    business_name: str,
    city: str,
    phone_suffix: str,
    *,
    rating_hundredths=None,
    review_count=None,
    listing_kind: ListingKind = ListingKind.ORGANIC,
    cta=None,
) -> ListingRecord:
    rating = (
        ListingRating(rating_hundredths=rating_hundredths, review_count=review_count)
        if rating_hundredths is not None
        else None
    )
    return ListingRecord(
        listing_id=listing_id,
        business_name=business_name,
        slug=listing_id,
        category_id="cat-hotels",
        description="%s is a well-reviewed local business serving guests year round." % business_name,
        listing_kind=listing_kind,
        contact=ListingContact(
            phone="555-01%s" % phone_suffix, email="%s@example.com" % listing_id.replace("-", ""),
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
        rating=rating,
        credentials=("Licensed operator", "Insured and bonded"),
        sponsorship=ListingSponsorship(kind=listing_kind, disclosure_text=""),
        cta=cta,
    )


def _listing_dataset() -> ListingDataset:
    category = ListingCategory(category_id="cat-hotels", label=CATEGORY_TAXONOMY_ENTRY, slug=CATEGORY_SLUG)
    listings = (
        _listing(
            "alpine-lantern-lodge", "Alpine Lantern Lodge", "Aspen", "00",
            rating_hundredths=470, review_count=88,
        ),
        _listing(
            _VERIFIED_LISTING_SLUG, "Cedar Harbor Inn", "Breckenridge", "01",
            rating_hundredths=440, review_count=61,
            listing_kind=ListingKind.VERIFIED,
            cta=ListingCTA(
                label="Check availability",
                target_route="https://example.com/book/cedar-harbor-inn",
            ),
        ),
        _listing(
            "maple-ridge-retreat", "Maple Ridge Retreat", "Vail", "02",
            rating_hundredths=490, review_count=205,
        ),
        _listing(
            _UNRATED_LISTING_SLUG, "Northstar Guest House", "Telluride", "03",
        ),
        _listing(
            "willow-creek-suites", "Willow Creek Suites", "Estes Park", "04",
            rating_hundredths=455, review_count=97,
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


def _content_package(listing_dataset: ListingDataset) -> ContentPackage:
    # Home/category need real editorial hero content (no ListingDataset
    # source exists for either slot). Every route hosting the site footer
    # (home, category, every profile) needs the explicit footer_legal/
    # disclosures ContentBlocks the D5 operator decision requires --
    # legal.footer.directory's legal_facts field is CONTENT_PACKAGE-sourced,
    # never BusinessSpec-sourced, this delivery. Business-profile pages also
    # need their own hero_h1/intro (the SEO Engine's D1/D2 title/meta
    # source slots, now extended to business-profile, AES-WEB-002K.1) --
    # real, distinct per-listing text derived from the listing's own name/
    # description, never a copy-pasted duplicate.
    profile_routes = tuple(
        "%s%s/" % (CATEGORY_ROUTE, listing.slug) for listing in listing_dataset.listings
    )
    blocks = [
        ContentBlock(page_route=HOME_ROUTE, slot_id="hero_h1", text="Find a great place to stay"),
        ContentBlock(
            page_route=HOME_ROUTE, slot_id="intro",
            text="Browse trusted, well-reviewed hotels verified by our editorial team.",
        ),
        ContentBlock(
            page_route=HOME_ROUTE, slot_id="subhead",
            text="Verified hotels, checked and reviewed by real guests.",
        ),
        ContentBlock(
            page_route=HOME_ROUTE, slot_id="message",
            text="Some listings are sponsored placements, always clearly labeled.",
        ),
        ContentBlock(page_route=CATEGORY_ROUTE, slot_id="hero_h1", text="Hotels"),
        ContentBlock(
            page_route=CATEGORY_ROUTE, slot_id="intro",
            text="Well-reviewed hotels, each one checked by our editorial team before listing.",
        ),
    ]
    for listing in listing_dataset.listings:
        route = "%s%s/" % (CATEGORY_ROUTE, listing.slug)
        blocks.append(ContentBlock(page_route=route, slot_id="hero_h1", text=listing.business_name))
        blocks.append(ContentBlock(page_route=route, slot_id="intro", text=listing.description))
    for route in (HOME_ROUTE, CATEGORY_ROUTE) + profile_routes:
        blocks.append(
            ContentBlock(
                page_route=route, slot_id="footer_legal",
                text="(c) 2026 Atlas Publishable Directory. All rights reserved.",
            )
        )
        blocks.append(
            ContentBlock(
                page_route=route, slot_id="disclosures",
                text="Some listings may be sponsored placements, always clearly labeled.",
            )
        )
    return ContentPackage(
        schema_version=SCHEMA_VERSIONS[ArtifactKind.CONTENT_PACKAGE],
        artifact_kind=ArtifactKind.CONTENT_PACKAGE,
        source_hashes={},
        blocks=tuple(blocks),
    )


def build_publishable_wave1_fixture_inputs() -> PublishableWave1FixtureInputs:
    """Build the deterministic Wave-1 input set. Pure: same output on every
    call, no I/O. ``site_architecture`` is produced by the real IA engine,
    not hand-built -- see module docstring."""
    spec = _business_spec()
    brand = BrandEngine().resolve(spec)
    listing_dataset = _listing_dataset()

    site_architecture = InformationArchitectureEngine().plan(
        spec, brand, listing_dataset=listing_dataset
    )
    profile_routes = tuple(
        sorted(
            page.route
            for page in site_architecture.pages
            if page.page_type == "business-profile"
        )
    )
    verified_listing_route = "%s%s/" % (CATEGORY_ROUTE, _VERIFIED_LISTING_SLUG)

    content_package = _content_package(listing_dataset)

    return PublishableWave1FixtureInputs(
        business_spec=spec,
        brand_package=brand,
        listing_dataset=listing_dataset,
        site_architecture=site_architecture,
        content_package=content_package,
        base_url=BASE_URL,
        home_route=HOME_ROUTE,
        category_route=CATEGORY_ROUTE,
        profile_routes=profile_routes,
        verified_listing_route=verified_listing_route,
    )
