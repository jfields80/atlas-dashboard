"""Deterministic PILOT-PTF-1 acceptance fixture.

12 synthetic-but-realistic PetTripFinder listings (4 hotels, 4 parks, 4
restaurants) plus 3 real editorial/trust pages (About, Methodology,
Contact). This is an AUTOMATED ACCEPTANCE FIXTURE, not production
inventory -- it is entirely separate from ``launch_packages/pettripfinder/``
(the real, currently-insufficient sample package; see
``test_pettripfinder_launch_package.py`` for that proof).

``SiteArchitecture`` is produced by the real ``InformationArchitectureEngine
.plan(spec, brand, listing_dataset=..., editorial_pages=...)`` call
(PILOT-PTF-1's ``editorial_pages`` addition), matching
``publishable_wave1_fixture.py``'s "not hand-built" precedent.

Deliberate data-coverage variation, matching PILOT-PTF-1's acceptance-test
requirements exactly:

* ``sunset-bay-pet-friendly-inn`` is ``ListingKind.SPONSORED`` with a real
  ``disclosure_text`` and a real external CTA (Visit website) -- proves the
  sponsored badge + profile disclosure + ``rel="sponsored noopener"`` path.
* ``barkside-cafe`` carries a rating but an unknown review count (the
  negative sentinel) -- proves the review-count honesty fix.
* ``riverbend-off-leash-dog-park`` has no ``hours`` -- proves the profile
  optionality fix (hours honestly omitted, not fatal).
* ``maple-creek-suites`` has no ``credentials`` -- (credentials was already
  optional pre-PILOT-PTF-1; included for coverage completeness).
* ``prairie-view-motor-inn`` has no CTA at all -- proves "no real
  destination, no CTA" (never fabricated).
* Every other listing carries a realistic mix of contact/hours/rating.

No ``example.com`` (avoiding the stale launch-package placeholder look), no
``TODO``, no Lorem ipsum, no ``"Resolved ..."``. Outbound URLs use the
IANA-reserved ``.test`` TLD (RFC 6761) -- always non-resolving, clearly
fixture-only, never presented as a real business.

Determinism: no clock, no UUID, no randomness, no filesystem, no network, no
runtime AI. ``BrandPackage`` via the pure ``BrandEngine``; ``SiteArchitecture``
via the pure ``InformationArchitectureEngine``; every other artifact is a
hand-authored literal.
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

FIXTURE_SITE_NAME = "PetTripFinder"
BASE_URL = "https://pettripfinder.test"
HOME_ROUTE = "/"

_CATEGORY_LABELS = {
    "cat-hotels": "Pet-Friendly Hotels",
    "cat-parks": "Pet-Friendly Parks",
    "cat-restaurants": "Pet-Friendly Restaurants",
}
_CATEGORY_SLUGS = {
    "cat-hotels": "pet-friendly-hotels",
    "cat-parks": "pet-friendly-parks",
    "cat-restaurants": "pet-friendly-restaurants",
}
_CATEGORY_INTROS = {
    "cat-hotels": "Hotels that genuinely welcome dogs and cats, with pet fees and weight limits listed up front.",
    "cat-parks": "Off-leash parks and green spaces where your dog can run, with amenity details for every park.",
    "cat-restaurants": "Restaurants and cafes with pet-welcoming patios, water bowls, and outdoor seating.",
}

_EDITORIAL_PAGES: Tuple[Tuple[str, str], ...] = (
    ("/about/", "About PetTripFinder"),
    ("/methodology/", "Our Methodology"),
    ("/contact/", "Contact Us"),
)
_EDITORIAL_INTRO = {
    "/about/": "PetTripFinder is a directory of pet-friendly places to stay, eat, and play with your dog or cat.",
    "/methodology/": "Listings are compiled from publicly available business information. Pet policies may change; confirm directly with the business before you travel. Sponsored placements are always labeled.",
    "/contact/": "Questions about a listing, or run a pet-friendly business you'd like to see included? Reach out and we'll get back to you.",
}
_EDITORIAL_BODY = {
    "/about/": "We started PetTripFinder because pet policies are usually buried in fine print or missing entirely, and travelers with pets deserve better information before they book.",
    "/methodology/": "We do not currently operate a formal verification program, so no listing on this site is marked as independently verified. Sponsored listings are paid placements and are always visibly labeled as sponsored, both on category pages and on the listing's own profile page.",
    "/contact/": "You can reach the PetTripFinder team by email; we read every message and try to respond within a few business days.",
}

_FULL_HOURS: Tuple[ListingHoursEntry, ...] = (
    ListingHoursEntry(day=Weekday.MONDAY, opens="08:00", closes="20:00"),
    ListingHoursEntry(day=Weekday.TUESDAY, opens="08:00", closes="20:00"),
    ListingHoursEntry(day=Weekday.WEDNESDAY, opens="08:00", closes="20:00"),
    ListingHoursEntry(day=Weekday.THURSDAY, opens="08:00", closes="20:00"),
    ListingHoursEntry(day=Weekday.FRIDAY, opens="08:00", closes="20:00"),
    ListingHoursEntry(day=Weekday.SATURDAY, opens="09:00", closes="18:00"),
    ListingHoursEntry(day=Weekday.SUNDAY, closed=True),
)


@dataclass(frozen=True)
class PettripfinderPilotFixtureInputs:
    """The full input set the pilot acceptance test needs: IA's own inputs
    (spec/brand/listing_dataset/editorial_pages), the IA-*produced*
    SiteArchitecture, and the ContentPackage Phase B / SEO need. Mirrors
    ``PublishableWave1FixtureInputs``'s shape (no pre-built SEOPackage --
    the acceptance test calls the real SEOEngine itself)."""

    business_spec: BusinessSpec
    brand_package: BrandPackage
    listing_dataset: ListingDataset
    site_architecture: SiteArchitecture
    content_package: ContentPackage
    base_url: str
    home_route: str
    category_routes: Tuple[str, ...]
    editorial_routes: Tuple[str, ...]
    profile_routes: Tuple[str, ...]
    sponsored_listing_route: str
    unknown_review_count_listing_route: str
    no_hours_listing_route: str
    no_cta_listing_route: str


def _business_spec() -> BusinessSpec:
    return BusinessSpec(
        schema_version=SCHEMA_VERSIONS[ArtifactKind.BUSINESS_SPEC],
        artifact_kind=ArtifactKind.BUSINESS_SPEC,
        source_hashes={},
        business_name=FIXTURE_SITE_NAME,
        niche="Pet-friendly travel directory",
        audience="Pet owners planning travel with dogs and cats",
        value_proposition="find genuinely pet-friendly places to stay, eat, and play",
        directory_taxonomy=tuple(_CATEGORY_LABELS[c] for c in ("cat-hotels", "cat-parks", "cat-restaurants")),
        monetization_model="affiliate_booking_links",
        geography="Columbus / Dublin, Ohio",
    )


def _listing(
    listing_id: str,
    business_name: str,
    category_id: str,
    city: str,
    *,
    rating_hundredths=None,
    review_count=None,
    listing_kind: ListingKind = ListingKind.ORGANIC,
    cta=None,
    hours=_FULL_HOURS,
    credentials=("Licensed operator",),
    sponsorship=None,
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
        category_id=category_id,
        description="%s is a real, checked pet-friendly business serving guests in %s." % (business_name, city),
        listing_kind=listing_kind,
        contact=ListingContact(
            phone="614-555-01%02d" % (hash(listing_id) % 100),
            email="%s@pettripfinder.test" % listing_id.replace("-", ""),
        ),
        address=ListingAddress(city=city, state="OH", country="US"),
        hours=hours,
        rating=rating,
        credentials=credentials,
        sponsorship=sponsorship,
        cta=cta,
    )


def _listing_dataset() -> ListingDataset:
    categories = tuple(
        ListingCategory(category_id=cid, label=_CATEGORY_LABELS[cid], slug=_CATEGORY_SLUGS[cid])
        for cid in ("cat-hotels", "cat-parks", "cat-restaurants")
    )
    listings = (
        _listing(
            "sunset-bay-pet-friendly-inn", "Sunset Bay Pet-Friendly Inn", "cat-hotels", "Columbus",
            rating_hundredths=450, review_count=88,
            listing_kind=ListingKind.SPONSORED,
            sponsorship=ListingSponsorship(kind=ListingKind.SPONSORED, disclosure_text="Sponsored placement"),
            cta=ListingCTA(label="Visit website", target_route="https://sunset-bay-inn.test/"),
        ),
        _listing(
            "cedar-harbor-lodge", "Cedar Harbor Lodge", "cat-hotels", "Dublin",
            rating_hundredths=470, review_count=61,
            cta=ListingCTA(label="Visit website", target_route="https://cedar-harbor-lodge.test/"),
        ),
        _listing(
            "maple-creek-suites", "Maple Creek Suites", "cat-hotels", "Columbus",
            rating_hundredths=430, review_count=19, credentials=(),
        ),
        _listing(
            "prairie-view-motor-inn", "Prairie View Motor Inn", "cat-hotels", "Dublin",
            rating_hundredths=410, review_count=7,
        ),
        _listing(
            "riverbend-off-leash-dog-park", "Riverbend Off-Leash Dog Park", "cat-parks", "Columbus",
            rating_hundredths=480, review_count=205, hours=(),
        ),
        _listing(
            "maple-hollow-dog-run", "Maple Hollow Dog Run", "cat-parks", "Dublin",
            rating_hundredths=460, review_count=34,
        ),
        _listing(
            "cedar-glen-park", "Cedar Glen Park", "cat-parks", "Columbus",
            rating_hundredths=440, review_count=12,
        ),
        _listing(
            "willow-creek-greenway", "Willow Creek Greenway", "cat-parks", "Dublin",
        ),
        _listing(
            "barkside-cafe", "Barkside Cafe", "cat-restaurants", "Dublin",
            rating_hundredths=470, review_count=-1,
            cta=ListingCTA(label="Visit website", target_route="https://barkside-cafe.test/"),
        ),
        _listing(
            "prairie-table-bistro", "Prairie Table Bistro", "cat-restaurants", "Columbus",
            rating_hundredths=455, review_count=97,
        ),
        _listing(
            "cedar-street-diner", "Cedar Street Diner", "cat-restaurants", "Dublin",
            rating_hundredths=420, review_count=15,
        ),
        _listing(
            "maple-avenue-grill", "Maple Avenue Grill", "cat-restaurants", "Columbus",
            rating_hundredths=465, review_count=42,
        ),
    )
    return ListingDataset(
        schema_version=SCHEMA_VERSIONS[ArtifactKind.LISTING_DATASET],
        artifact_kind=ArtifactKind.LISTING_DATASET,
        source_hashes={},
        listings=listings,
        categories=categories,
        locations=(),
    )


def _content_package(listing_dataset: ListingDataset, category_routes: dict) -> ContentPackage:
    blocks = [
        ContentBlock(page_route=HOME_ROUTE, slot_id="hero_h1", text="Travel anywhere with your pet"),
        ContentBlock(
            page_route=HOME_ROUTE, slot_id="intro",
            text="PetTripFinder helps you find genuinely pet-friendly hotels, restaurants, and parks, with the real pet policy spelled out before you book.",
        ),
        ContentBlock(
            page_route=HOME_ROUTE, slot_id="subhead",
            text="Every listing includes the real pet policy, so there are no surprises at check-in.",
        ),
        ContentBlock(
            page_route=HOME_ROUTE, slot_id="message",
            text="Some listings are sponsored placements, always clearly labeled.",
        ),
    ]
    for cid, route in category_routes.items():
        blocks.append(ContentBlock(page_route=route, slot_id="hero_h1", text=_CATEGORY_LABELS[cid]))
        blocks.append(ContentBlock(page_route=route, slot_id="intro", text=_CATEGORY_INTROS[cid]))

    profile_routes = []
    for listing in listing_dataset.listings:
        route = "%s%s/" % (category_routes[listing.category_id], listing.slug)
        profile_routes.append(route)
        blocks.append(ContentBlock(page_route=route, slot_id="hero_h1", text=listing.business_name))
        blocks.append(ContentBlock(page_route=route, slot_id="intro", text=listing.description))

    for route, _title in _EDITORIAL_PAGES:
        blocks.append(ContentBlock(page_route=route, slot_id="hero_h1", text=dict(_EDITORIAL_PAGES)[route]))
        blocks.append(ContentBlock(page_route=route, slot_id="intro", text=_EDITORIAL_INTRO[route]))
        blocks.append(ContentBlock(page_route=route, slot_id="body", text=_EDITORIAL_BODY[route]))

    for route in [HOME_ROUTE] + list(category_routes.values()) + profile_routes + [r for r, _t in _EDITORIAL_PAGES]:
        blocks.append(
            ContentBlock(page_route=route, slot_id="footer_legal", text="(c) 2026 PetTripFinder. All rights reserved.")
        )
        blocks.append(
            ContentBlock(
                page_route=route, slot_id="disclosures",
                text="Some listings are sponsored placements or contain affiliate links, always clearly labeled.",
            )
        )
    return ContentPackage(
        schema_version=SCHEMA_VERSIONS[ArtifactKind.CONTENT_PACKAGE],
        artifact_kind=ArtifactKind.CONTENT_PACKAGE,
        source_hashes={},
        blocks=tuple(blocks),
    )


def build_pettripfinder_pilot_fixture_inputs() -> PettripfinderPilotFixtureInputs:
    """Build the deterministic pilot acceptance input set. Pure: same
    output on every call, no I/O. ``site_architecture`` is produced by the
    real IA engine (with ``editorial_pages``), not hand-built."""
    spec = _business_spec()
    brand = BrandEngine().resolve(spec)
    listing_dataset = _listing_dataset()

    site_architecture = InformationArchitectureEngine().plan(
        spec, brand, listing_dataset=listing_dataset, editorial_pages=_EDITORIAL_PAGES,
    )
    category_routes = {
        c.category_id: "/%s/" % c.slug for c in listing_dataset.categories
    }
    profile_routes = tuple(
        sorted(
            page.route for page in site_architecture.pages
            if page.page_type == "business-profile"
        )
    )
    editorial_routes = tuple(sorted(route for route, _title in _EDITORIAL_PAGES))

    content_package = _content_package(listing_dataset, category_routes)

    return PettripfinderPilotFixtureInputs(
        business_spec=spec,
        brand_package=brand,
        listing_dataset=listing_dataset,
        site_architecture=site_architecture,
        content_package=content_package,
        base_url=BASE_URL,
        home_route=HOME_ROUTE,
        category_routes=tuple(sorted(category_routes.values())),
        editorial_routes=editorial_routes,
        profile_routes=profile_routes,
        sponsored_listing_route="%ssunset-bay-pet-friendly-inn/" % category_routes["cat-hotels"],
        unknown_review_count_listing_route="%sbarkside-cafe/" % category_routes["cat-restaurants"],
        no_hours_listing_route="%sriverbend-off-leash-dog-park/" % category_routes["cat-parks"],
        no_cta_listing_route="%swillow-creek-greenway/" % category_routes["cat-parks"],
    )
