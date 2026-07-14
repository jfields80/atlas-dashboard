"""Cross-record validation for ``ListingDataset`` (AES-WEB-002J.17;
ADR-WEB-LISTING-DATASET).

Structural field types/shapes are already enforced by Pydantic on
``ListingRecord``/``ListingDataset`` construction (``FrozenModel``,
``extra="forbid"``). This module validates the *cross-record* invariants
Pydantic cannot express on its own -- identity uniqueness, category/location
reference integrity, numeric ranges, and safe-URL/route grammar -- exactly
mirroring the batch-reporting discipline every other WGE validator/error
uses (``content_validators.py``, ``SpecCompilationError``,
``ContentValidationError``): every violation is collected, none is repaired
silently, and no partial/patched dataset is ever accepted.

Pure: no I/O, no clock, no randomness, no AI, no mutation of the (frozen)
input. Per the contracts/ import matrix (§3.1: stdlib + pydantic +
intra-contracts only), URL/route safety is re-derived here rather than
imported from ``rendering/html_emitter.is_safe_url`` -- the same scheme
whitelist (``http``, ``https``, ``mailto``, ``tel``) and rejection rules
(no ``javascript:``/``data:``/protocol-relative), documented in parallel,
not shared code, because ``contracts/`` has no legal import path to
``rendering/``.
"""

from __future__ import annotations

import re
from typing import Dict, List

from engines.website_generation.contracts.artifacts import ListingDataset
from engines.website_generation.contracts.errors import ArtifactValidationError

_ID_SLUG_RE = re.compile(r"^[a-z0-9]+(-[a-z0-9]+)*$")
_HOURS_RE = re.compile(r"^([01]\d|2[0-3]):[0-5]\d$")
_SAFE_URL_SCHEMES = frozenset({"http", "https", "mailto", "tel"})

_MIN_RATING_HUNDREDTHS = 0
_MAX_RATING_HUNDREDTHS = 500
_MIN_LAT_MICRO = -90_000_000
_MAX_LAT_MICRO = 90_000_000
_MIN_LONG_MICRO = -180_000_000
_MAX_LONG_MICRO = 180_000_000

# Fixed diagnostics key order (readability/debugging only; mirrors
# component_engine._DIAGNOSTIC_BUCKET_ORDER / seo_engine's precedent).
_DIAGNOSTIC_BUCKET_ORDER = (
    "duplicate_listing_ids",
    "duplicate_category_ids",
    "duplicate_location_ids",
    "duplicate_category_slugs",
    "invalid_ids",
    "unresolved_category_refs",
    "unresolved_location_refs",
    "duplicate_routes",
    "empty_business_names",
    "empty_category_labels",
    "empty_cta_labels",
    "empty_provenance_source_ids",
    "invalid_ratings",
    "invalid_review_counts",
    "invalid_coordinates",
    "invalid_hours",
    "unsafe_urls",
    "unsafe_asset_refs",
)


def _is_safe_url(value: str) -> bool:
    """Same grammar as ``rendering.html_emitter.is_safe_url`` (documented
    duplication -- see module docstring)."""
    stripped = value.strip()
    if not stripped:
        return True  # empty is optional-and-absent, not unsafe
    if stripped.startswith("//"):
        return False
    if stripped.startswith("#") or stripped.startswith("/"):
        return True
    if ":" not in stripped:
        return True
    scheme = stripped.split(":", 1)[0].strip().lower()
    return scheme in _SAFE_URL_SCHEMES


def _derived_route(category_slug: str, listing_slug: str) -> str:
    """The deterministic route-derivation rule this validator checks
    collisions against (ADR §6: route is never *stored*, only checked for
    prospective collision here as a dataset-integrity signal)."""
    return "/%s/%s/" % (category_slug, listing_slug)


def validate_listing_dataset(dataset: ListingDataset) -> None:
    """Validate every cross-record invariant; raise one batched
    :class:`ArtifactValidationError` naming every violation, or return
    ``None`` when the dataset is valid (including the empty dataset).

    Deterministic ordering: every diagnostics list is sorted by a stable
    key so the result never depends on tuple input order.
    """
    diagnostics: Dict[str, List[Dict[str, str]]] = {}

    categories_by_id = {c.category_id: c for c in dataset.categories}
    locations_by_id = {l.location_id: l for l in dataset.locations}

    # -- identity uniqueness -------------------------------------------
    _check_duplicates(
        diagnostics, "duplicate_listing_ids",
        [l.listing_id for l in dataset.listings],
    )
    _check_duplicates(
        diagnostics, "duplicate_category_ids",
        [c.category_id for c in dataset.categories],
    )
    _check_duplicates(
        diagnostics, "duplicate_location_ids",
        [l.location_id for l in dataset.locations],
    )
    _check_duplicates(
        diagnostics, "duplicate_category_slugs",
        ["%s/%s" % (l.category_id, l.slug) for l in dataset.listings],
    )

    # -- grammar ----------------------------------------------------------
    invalid_ids: List[Dict[str, str]] = []
    for listing in dataset.listings:
        for field_name, value in (
            ("listing_id", listing.listing_id),
            ("slug", listing.slug),
        ):
            if not _ID_SLUG_RE.match(value):
                invalid_ids.append(
                    {"listing_id": listing.listing_id, "field": field_name, "value": value}
                )
    for category in dataset.categories:
        for field_name, value in (
            ("category_id", category.category_id),
            ("slug", category.slug),
        ):
            if not _ID_SLUG_RE.match(value):
                invalid_ids.append(
                    {"category_id": category.category_id, "field": field_name, "value": value}
                )
    for location in dataset.locations:
        for field_name, value in (
            ("location_id", location.location_id),
            ("slug", location.slug),
        ):
            if not _ID_SLUG_RE.match(value):
                invalid_ids.append(
                    {"location_id": location.location_id, "field": field_name, "value": value}
                )
    if invalid_ids:
        diagnostics["invalid_ids"] = sorted(
            invalid_ids, key=lambda e: (e.get("field", ""), str(sorted(e.items())))
        )

    # -- reference integrity ------------------------------------------
    unresolved_category: List[Dict[str, str]] = []
    unresolved_location: List[Dict[str, str]] = []
    for listing in dataset.listings:
        if listing.category_id not in categories_by_id:
            unresolved_category.append(
                {"listing_id": listing.listing_id, "category_id": listing.category_id}
            )
        if listing.location_id and listing.location_id not in locations_by_id:
            unresolved_location.append(
                {"listing_id": listing.listing_id, "location_id": listing.location_id}
            )
    if unresolved_category:
        diagnostics["unresolved_category_refs"] = sorted(
            unresolved_category, key=lambda e: e["listing_id"]
        )
    if unresolved_location:
        diagnostics["unresolved_location_refs"] = sorted(
            unresolved_location, key=lambda e: e["listing_id"]
        )

    # -- derived-route collisions (checked, never stored; ADR §6) ---------
    routes_seen: Dict[str, List[str]] = {}
    for listing in dataset.listings:
        category = categories_by_id.get(listing.category_id)
        if category is None:
            continue  # already reported as unresolved_category_refs
        route = _derived_route(category.slug, listing.slug)
        routes_seen.setdefault(route, []).append(listing.listing_id)
    duplicate_routes = [
        {"route": route, "listing_ids": ",".join(sorted(ids))}
        for route, ids in routes_seen.items()
        if len(ids) > 1
    ]
    if duplicate_routes:
        diagnostics["duplicate_routes"] = sorted(
            duplicate_routes, key=lambda e: e["route"]
        )

    # -- required-value non-emptiness --------------------------------
    empty_names = [
        {"listing_id": l.listing_id}
        for l in dataset.listings
        if not l.business_name.strip()
    ]
    if empty_names:
        diagnostics["empty_business_names"] = sorted(
            empty_names, key=lambda e: e["listing_id"]
        )

    empty_category_labels = [
        {"category_id": c.category_id}
        for c in dataset.categories
        if not c.label.strip()
    ]
    if empty_category_labels:
        diagnostics["empty_category_labels"] = sorted(
            empty_category_labels, key=lambda e: e["category_id"]
        )

    empty_cta_labels = [
        {"listing_id": l.listing_id}
        for l in dataset.listings
        if l.cta is not None and not l.cta.label.strip()
    ]
    if empty_cta_labels:
        diagnostics["empty_cta_labels"] = sorted(
            empty_cta_labels, key=lambda e: e["listing_id"]
        )

    empty_provenance_ids = [
        {"listing_id": l.listing_id}
        for l in dataset.listings
        if l.provenance is not None and not l.provenance.source_id.strip()
    ]
    if empty_provenance_ids:
        diagnostics["empty_provenance_source_ids"] = sorted(
            empty_provenance_ids, key=lambda e: e["listing_id"]
        )

    # -- numeric ranges -------------------------------------------------
    invalid_ratings: List[Dict[str, str]] = []
    invalid_review_counts: List[Dict[str, str]] = []
    invalid_coords: List[Dict[str, str]] = []
    for listing in dataset.listings:
        if listing.rating is not None:
            r = listing.rating.rating_hundredths
            if not (_MIN_RATING_HUNDREDTHS <= r <= _MAX_RATING_HUNDREDTHS):
                invalid_ratings.append(
                    {"listing_id": listing.listing_id, "rating_hundredths": str(r)}
                )
            if listing.rating.review_count < 0:
                invalid_review_counts.append(
                    {
                        "listing_id": listing.listing_id,
                        "review_count": str(listing.rating.review_count),
                    }
                )
        if listing.geo is not None:
            lat, lng = listing.geo.lat_micro, listing.geo.long_micro
            if not (_MIN_LAT_MICRO <= lat <= _MAX_LAT_MICRO):
                invalid_coords.append(
                    {"listing_id": listing.listing_id, "axis": "lat_micro", "value": str(lat)}
                )
            if not (_MIN_LONG_MICRO <= lng <= _MAX_LONG_MICRO):
                invalid_coords.append(
                    {"listing_id": listing.listing_id, "axis": "long_micro", "value": str(lng)}
                )
    if invalid_ratings:
        diagnostics["invalid_ratings"] = sorted(
            invalid_ratings, key=lambda e: e["listing_id"]
        )
    if invalid_review_counts:
        diagnostics["invalid_review_counts"] = sorted(
            invalid_review_counts, key=lambda e: e["listing_id"]
        )
    if invalid_coords:
        diagnostics["invalid_coordinates"] = sorted(
            invalid_coords, key=lambda e: (e["listing_id"], e["axis"])
        )

    # -- hours ------------------------------------------------------------
    invalid_hours: List[Dict[str, str]] = []
    for listing in dataset.listings:
        seen_days: set = set()
        for entry in listing.hours:
            if entry.day in seen_days:
                invalid_hours.append(
                    {
                        "listing_id": listing.listing_id,
                        "day": entry.day.value,
                        "reason": "duplicate_weekday",
                    }
                )
            seen_days.add(entry.day)
            if entry.closed:
                continue
            has_opens, has_closes = bool(entry.opens), bool(entry.closes)
            if has_opens != has_closes:
                invalid_hours.append(
                    {
                        "listing_id": listing.listing_id,
                        "day": entry.day.value,
                        "reason": "incomplete_open_close_pair",
                    }
                )
                continue
            if has_opens and not (_HOURS_RE.match(entry.opens) and _HOURS_RE.match(entry.closes)):
                invalid_hours.append(
                    {
                        "listing_id": listing.listing_id,
                        "day": entry.day.value,
                        "reason": "malformed_time",
                    }
                )
    if invalid_hours:
        diagnostics["invalid_hours"] = sorted(
            invalid_hours, key=lambda e: (e["listing_id"], e["day"])
        )

    # -- URL/route safety ---------------------------------------------
    unsafe_urls: List[Dict[str, str]] = []
    for listing in dataset.listings:
        if listing.contact is not None and not _is_safe_url(listing.contact.website_url):
            unsafe_urls.append(
                {"listing_id": listing.listing_id, "field": "contact.website_url"}
            )
        if listing.cta is not None and not _is_safe_url(listing.cta.target_route):
            unsafe_urls.append(
                {"listing_id": listing.listing_id, "field": "cta.target_route"}
            )
        if listing.provenance is not None and not _is_safe_url(listing.provenance.source_url):
            unsafe_urls.append(
                {"listing_id": listing.listing_id, "field": "provenance.source_url"}
            )
    if unsafe_urls:
        diagnostics["unsafe_urls"] = sorted(
            unsafe_urls, key=lambda e: (e["listing_id"], e["field"])
        )

    # -- asset references: hash-shaped, never a path or URL ------------
    unsafe_assets: List[Dict[str, str]] = []
    for listing in dataset.listings:
        for asset in listing.assets:
            value = asset.asset_hash.strip()
            if not value or "/" in value or "\\" in value or ":" in value:
                unsafe_assets.append(
                    {"listing_id": listing.listing_id, "asset_hash": value}
                )
    if unsafe_assets:
        diagnostics["unsafe_asset_refs"] = sorted(
            unsafe_assets, key=lambda e: e["listing_id"]
        )

    if not diagnostics:
        return

    ordered = {
        key: diagnostics[key] for key in _DIAGNOSTIC_BUCKET_ORDER if key in diagnostics
    }
    raise ArtifactValidationError(
        "ListingDataset validation failed; see diagnostics",
        stage="listing_dataset_validation",
        diagnostics=ordered,
    )


def _check_duplicates(
    diagnostics: Dict[str, List[Dict[str, str]]], bucket: str, values: List[str]
) -> None:
    seen: set = set()
    duplicates: set = set()
    for value in values:
        if value in seen:
            duplicates.add(value)
        seen.add(value)
    if duplicates:
        diagnostics[bucket] = [{"value": v} for v in sorted(duplicates)]
