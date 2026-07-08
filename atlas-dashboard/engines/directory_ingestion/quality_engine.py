"""
Module 4 — Data Quality Engine
==============================

Scores every normalized listing across seven dimensions plus a weighted
overall score. Deterministic, explainable, named constants only.
"""

from __future__ import annotations

from engines.directory_ingestion.ingestion_models import (
    NormalizedListing,
    Provenance,
    QualityReport,
    QualityScore,
    SourceType,
)

# ---------------------------------------------------------------------------
# Overall weighting — sums to 100
# ---------------------------------------------------------------------------

_W_COMPLETENESS = 25
_W_CONTACT = 20
_W_LOCATION = 15
_W_SEO = 10
_W_MONETIZATION = 10
_W_VERIFICATION = 15
_W_FRESHNESS = 5

_MAX = 100

# Completeness field weights (sum 100)
_COMPLETENESS_FIELDS: tuple[tuple[str, int], ...] = (
    ("address", 15),
    ("city", 10),
    ("state", 10),
    ("zip_code", 5),
    ("phone", 15),
    ("website", 15),
    ("email", 10),
    ("hours", 5),
    ("description", 10),
    ("categories", 5),      # tuple field
)

# Contact quality points
_CONTACT_PHONE = 40
_CONTACT_WEBSITE = 35
_CONTACT_EMAIL = 25

# Location accuracy points
_LOCATION_FULL_ADDRESS = 40     # address + city + state + zip
_LOCATION_PARTIAL_ADDRESS = 20  # city + state only
_LOCATION_COORDS = 40
_LOCATION_VERIFIED_BONUS = 20

# SEO readiness points
_SEO_DESCRIPTION = 40
_SEO_DESCRIPTION_MIN_CHARS = 80
_SEO_SHORT_DESCRIPTION = 20
_SEO_SUMMARY = 30
_SEO_CATEGORY = 30

# Monetization readiness points
_MONETIZATION_CONTACTABLE = 40   # phone or email (a business we can sell to)
_MONETIZATION_WEBSITE = 30       # upgrade candidate signal
_MONETIZATION_PRICING = 15
_MONETIZATION_SERVICES = 15

# Verification quality points
_VERIFICATION_VERIFIED_SOURCE = 60
_VERIFICATION_TAGGED_VERIFIED_FIELD = 8   # per verified core field, capped
_VERIFICATION_TAGGED_CAP = 40

# Freshness by source type (Phase 3B has no crawl timestamps yet;
# freshness is a source-derived prior and is honestly documented as such)
_FRESHNESS_BY_SOURCE: dict[SourceType, int] = {
    SourceType.USER_SUBMITTED: 95,
    SourceType.GOOGLE_PLACES: 90,
    SourceType.FUTURE_API: 85,
    SourceType.FUTURE_SCRAPER: 75,
    SourceType.ASSOCIATION_WEBSITE: 65,
    SourceType.GOVERNMENT_OPEN_DATA: 60,
    SourceType.PUBLIC_DIRECTORY: 55,
    SourceType.CSV_IMPORT: 50,
}

# Report threshold: listings at or above this overall score are import-grade.
QUALITY_THRESHOLD = 60


class QualityEngine:
    """Stateless quality scorer."""

    def score(self, listing: NormalizedListing) -> QualityScore:
        explanations: list[str] = []

        completeness = self._completeness(listing, explanations)
        contact = self._contact(listing, explanations)
        location = self._location(listing, explanations)
        seo = self._seo(listing, explanations)
        monetization = self._monetization(listing, explanations)
        verification = self._verification(listing, explanations)
        freshness = _FRESHNESS_BY_SOURCE[listing.source_type]
        explanations.append(
            f"freshness={freshness} (source-type prior: {listing.source_type.value})"
        )

        overall = round(
            (
                completeness * _W_COMPLETENESS
                + contact * _W_CONTACT
                + location * _W_LOCATION
                + seo * _W_SEO
                + monetization * _W_MONETIZATION
                + verification * _W_VERIFICATION
                + freshness * _W_FRESHNESS
            )
            / 100
        )
        return QualityScore(
            listing_id=listing.listing_id,
            completeness=completeness,
            contact_quality=contact,
            location_accuracy=location,
            seo_readiness=seo,
            monetization_readiness=monetization,
            verification_quality=verification,
            freshness=freshness,
            overall=overall,
            explanations=tuple(explanations),
        )

    def score_batch(self, listings: list[NormalizedListing]) -> QualityReport:
        scores = tuple(self.score(l) for l in listings)
        average = round(sum(s.overall for s in scores) / len(scores)) if scores else 0
        above = sum(1 for s in scores if s.overall >= QUALITY_THRESHOLD)
        return QualityReport(
            scores=scores,
            average_overall=average,
            listings_above_threshold=above,
            threshold=QUALITY_THRESHOLD,
        )

    # -- dimensions -----------------------------------------------------------

    @staticmethod
    def _completeness(l: NormalizedListing, notes: list[str]) -> int:
        earned = 0
        missing: list[str] = []
        for field_name, weight in _COMPLETENESS_FIELDS:
            value = getattr(l, field_name)
            populated = bool(value.value) if hasattr(value, "value") else bool(value)
            if populated:
                earned += weight
            else:
                missing.append(field_name)
        if missing:
            notes.append(f"completeness={earned}: missing {', '.join(missing)}")
        else:
            notes.append("completeness=100: all tracked fields populated")
        return min(_MAX, earned)

    @staticmethod
    def _contact(l: NormalizedListing, notes: list[str]) -> int:
        earned = 0
        if l.phone.value:
            earned += _CONTACT_PHONE
        if l.website.value:
            earned += _CONTACT_WEBSITE
        if l.email.value:
            earned += _CONTACT_EMAIL
        notes.append(f"contact_quality={earned}")
        return min(_MAX, earned)

    @staticmethod
    def _location(l: NormalizedListing, notes: list[str]) -> int:
        earned = 0
        if l.address.value and l.city.value and l.state.value and l.zip_code.value:
            earned += _LOCATION_FULL_ADDRESS
        elif l.city.value and l.state.value:
            earned += _LOCATION_PARTIAL_ADDRESS
        if l.latitude is not None and l.longitude is not None:
            earned += _LOCATION_COORDS
        if l.address.provenance is Provenance.VERIFIED and l.address.value:
            earned += _LOCATION_VERIFIED_BONUS
        notes.append(f"location_accuracy={min(_MAX, earned)}")
        return min(_MAX, earned)

    @staticmethod
    def _seo(l: NormalizedListing, notes: list[str]) -> int:
        earned = 0
        if l.description.value:
            if len(l.description.value) >= _SEO_DESCRIPTION_MIN_CHARS:
                earned += _SEO_DESCRIPTION
            else:
                earned += _SEO_SHORT_DESCRIPTION
        if l.seo_summary.value:
            earned += _SEO_SUMMARY
        if l.categories:
            earned += _SEO_CATEGORY
        notes.append(f"seo_readiness={min(_MAX, earned)}")
        return min(_MAX, earned)

    @staticmethod
    def _monetization(l: NormalizedListing, notes: list[str]) -> int:
        earned = 0
        if l.phone.value or l.email.value:
            earned += _MONETIZATION_CONTACTABLE
        if l.website.value:
            earned += _MONETIZATION_WEBSITE
        if l.pricing_notes.value:
            earned += _MONETIZATION_PRICING
        if l.services:
            earned += _MONETIZATION_SERVICES
        notes.append(f"monetization_readiness={min(_MAX, earned)}")
        return min(_MAX, earned)

    @staticmethod
    def _verification(l: NormalizedListing, notes: list[str]) -> int:
        earned = _VERIFICATION_VERIFIED_SOURCE if l.verified else 0
        tagged = 0
        for tv in (l.address, l.city, l.state, l.phone, l.website):
            if tv.value and tv.provenance is Provenance.VERIFIED:
                tagged += _VERIFICATION_TAGGED_VERIFIED_FIELD
        earned += min(_VERIFICATION_TAGGED_CAP, tagged)
        notes.append(f"verification_quality={min(_MAX, earned)}")
        return min(_MAX, earned)
