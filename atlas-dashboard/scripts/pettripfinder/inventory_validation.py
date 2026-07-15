"""Publish-grade inventory validation for the PetTripFinder pilot
(AES-WEB-002N.1 -- launch inventory contract and validation).

Pure, deterministic assessment of a built ``ListingDataset`` against the
operator-approved required-to-publish standard (AES-WEB-002N operator
decisions 3/8/15, readiness semantics remediated pre-commit). Three
states per listing:

* ``READY`` -- every required publish field present and valid, and the
  observation is not stale. Recommended-field gaps (phone, postal code,
  authorized image, rating) are **advisories**: visible in the readiness
  report, never demoting -- optional enrichment must never become a de
  facto launch gate (images are recommended-not-required, ratings are
  never fabricated, phone may legitimately not exist).
* ``READY_WITH_WARNINGS`` -- required fields present but a genuinely
  significant, still-publishable condition applies. For N.1 exactly one
  warning class exists: a **stale observation** per the category
  staleness thresholds. Publishable, but does not count toward the
  strict launch threshold until refreshed.
* ``NOT_READY`` -- one or more required publish fields missing/invalid.
  Blocks production launch outright.

Required to publish (decision 3): name, category, city, state, street
address, source URL, source type, observed date, pet-policy statement
(carried as the listing ``description``, which the builder synthesizes
from the seed's ``pet_policy``), and a website URL (hotels/restaurants:
the business site; parks: the official parks-department page -- one
uniform field, category-appropriate content).

Staleness (decision 15): hotels/restaurants 180 days, parks 365; stale
listings stay publishable with a warning.

Determinism: no clock. Staleness is evaluated only against an explicitly
supplied ``reference_date`` (ISO ``YYYY-MM-DD``); the *runner* passes a
real calendar date (script-layer, console-report-only -- no durable
artifact carries it), tests pass fixed dates, and an empty reference date
skips staleness entirely. Validation lives here in the ingestion/readiness
layer by operator decision 18 -- never in HTML quality gates.
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Dict, Optional, Tuple

READY = "READY"
READY_WITH_WARNINGS = "READY_WITH_WARNINGS"
NOT_READY = "NOT_READY"

# Staleness thresholds in days, keyed by category slug (operator decision 15).
STALENESS_DAYS_BY_CATEGORY_SLUG: Dict[str, int] = {
    "pet-friendly-hotels": 180,
    "pet-friendly-restaurants": 180,
    "pet-friendly-parks": 365,
}
_DEFAULT_STALENESS_DAYS = 180


@dataclass(frozen=True)
class ListingReadiness:
    """One listing's deterministic publish assessment.

    ``warnings`` are state-demoting significant conditions (N.1: staleness
    only); ``advisories`` are non-demoting recommended-field gaps -- kept
    visible for the operator, never a launch gate."""

    listing_id: str
    business_name: str
    category_slug: str
    state: str  # READY | READY_WITH_WARNINGS | NOT_READY
    missing_required: Tuple[str, ...] = ()
    warnings: Tuple[str, ...] = ()
    advisories: Tuple[str, ...] = ()


def _parse_iso_date(value: str) -> Optional[date]:
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        return None


def assess_listing(
    listing,
    category_slug: str,
    *,
    reference_date: str = "",
) -> ListingReadiness:
    """Assess one built ``ListingRecord`` against the publish standard."""
    missing = []

    if not listing.business_name.strip():
        missing.append("name")
    if not category_slug:
        missing.append("category")
    address = listing.address
    if address is None or not address.city.strip():
        missing.append("city")
    if address is None or not address.state.strip():
        missing.append("state")
    if address is None or not address.street.strip():
        missing.append("street_address")

    provenance = listing.provenance
    if provenance is None or not provenance.source_url.strip():
        missing.append("source_url")
    if provenance is None or not provenance.source_type.strip():
        missing.append("source_type")
    observed = None
    if provenance is None or not provenance.observed_at.strip():
        missing.append("observed_at")
    else:
        observed = _parse_iso_date(provenance.observed_at.strip())
        if observed is None:
            missing.append("observed_at")  # present but not a valid ISO date

    # The pet-policy statement travels as the synthesized description --
    # a pet-category listing with no policy fact is filler, not inventory.
    if not listing.description.strip():
        missing.append("pet_policy")

    if listing.contact is None or not listing.contact.website_url.strip():
        missing.append("website_url")

    # Advisories: recommended-field gaps -- operator-visible, never
    # state-demoting (optional enrichment must not become a de facto
    # launch requirement; remediated pre-commit doctrine).
    advisories = []
    if listing.contact is None or not listing.contact.phone.strip():
        advisories.append("no_phone")
    if address is None or not address.postal_code.strip():
        advisories.append("no_postal_code")
    if not listing.assets:
        advisories.append("no_authorized_image")
    if listing.rating is None:
        advisories.append("no_rating")

    # Warnings: genuinely significant, still-publishable conditions.
    # N.1's single warning class is staleness (decision 15).
    warnings = []
    if reference_date and observed is not None:
        reference = _parse_iso_date(reference_date)
        if reference is not None:
            limit = STALENESS_DAYS_BY_CATEGORY_SLUG.get(
                category_slug, _DEFAULT_STALENESS_DAYS
            )
            age_days = (reference - observed).days
            if age_days > limit:
                warnings.append(
                    "stale_observation:%dd_old_limit_%dd" % (age_days, limit)
                )

    if missing:
        state = NOT_READY
    elif warnings:
        state = READY_WITH_WARNINGS
    else:
        state = READY
    return ListingReadiness(
        listing_id=listing.listing_id,
        business_name=listing.business_name,
        category_slug=category_slug,
        state=state,
        missing_required=tuple(missing),
        warnings=tuple(warnings),
        advisories=tuple(advisories),
    )


def assess_inventory(dataset, *, reference_date: str = "") -> Tuple[ListingReadiness, ...]:
    """Assess every listing, in the dataset's own deterministic order."""
    slug_by_id = {c.category_id: c.slug for c in dataset.categories}
    return tuple(
        assess_listing(
            listing,
            slug_by_id.get(listing.category_id, ""),
            reference_date=reference_date,
        )
        for listing in dataset.listings
    )


def compute_launch_readiness(
    assessments: Tuple[ListingReadiness, ...],
    thresholds: Dict[str, object],
) -> Dict[str, object]:
    """The strict launch-readiness verdict (operator decisions 1/2/9,
    readiness semantics remediated pre-commit).

    Chosen rule, exactly: only ``READY`` listings count toward the 30-total
    and 10-per-category thresholds. Advisory recommended-field gaps never
    demote a listing below READY, so an otherwise-complete listing with no
    image, no rating, no phone, or no postal code still counts.
    ``READY_WITH_WARNINGS`` (N.1: stale observations only) listings remain
    publishable but never satisfy the strict threshold until refreshed.
    Any ``NOT_READY`` listing blocks production launch outright (a corpus
    carrying unpublishable records is not launch-ready, even if 30 other
    records are).
    """
    ready_by_category: Dict[str, int] = {}
    counts_by_state: Dict[str, int] = {READY: 0, READY_WITH_WARNINGS: 0, NOT_READY: 0}
    for assessment in assessments:
        counts_by_state[assessment.state] += 1
        if assessment.state == READY:
            ready_by_category[assessment.category_slug] = (
                ready_by_category.get(assessment.category_slug, 0) + 1
            )

    minimum_total = int(thresholds["minimum_total_listings"])
    minimum_per_category = int(thresholds["minimum_per_category"])
    required_categories = list(thresholds["required_categories"])

    categories_below_target = sorted(
        category for category in required_categories
        if ready_by_category.get(category, 0) < minimum_per_category
    )
    ready_total = counts_by_state[READY]
    launch_ready = (
        ready_total >= minimum_total
        and not categories_below_target
        and counts_by_state[NOT_READY] == 0
    )
    return {
        "ready_total": ready_total,
        "ready_by_category": {k: ready_by_category[k] for k in sorted(ready_by_category)},
        "counts_by_state": dict(counts_by_state),
        "minimum_total_listings": minimum_total,
        "minimum_per_category": minimum_per_category,
        "categories_below_target": categories_below_target,
        "launch_inventory_ready": launch_ready,
    }


def format_readiness_report(
    assessments: Tuple[ListingReadiness, ...],
    readiness: Dict[str, object],
    rejected_duplicates: Tuple[str, ...] = (),
) -> str:
    """The deterministic operator-facing readiness report (plain ASCII)."""
    lines = ["Inventory readiness report:"]
    for a in sorted(assessments, key=lambda x: (x.category_slug, x.listing_id)):
        lines.append("  [%s] %s (%s)" % (a.state, a.business_name, a.category_slug))
        for field in a.missing_required:
            lines.append("      missing required: %s" % field)
        for warning in a.warnings:
            lines.append("      warning: %s" % warning)
        for advisory in a.advisories:
            lines.append("      advisory: %s" % advisory)
    if rejected_duplicates:
        lines.append("  Rejected duplicates:")
        for entry in rejected_duplicates:
            lines.append("    - %s" % entry)
    lines.append("  READY: %d | READY_WITH_WARNINGS: %d | NOT_READY: %d" % (
        readiness["counts_by_state"][READY],
        readiness["counts_by_state"][READY_WITH_WARNINGS],
        readiness["counts_by_state"][NOT_READY],
    ))
    lines.append("  READY by category: %s (need %d each, %d total)" % (
        readiness["ready_by_category"],
        readiness["minimum_per_category"],
        readiness["minimum_total_listings"],
    ))
    lines.append("  launch_inventory_ready: %s" % readiness["launch_inventory_ready"])
    return "\n".join(lines)
