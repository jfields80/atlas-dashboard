"""Seed-package -> ``ListingDataset`` converter (PILOT-PTF-1).

A small, pure conversion function: parsed launch-package seed records
(``launch_packages/<slug>/seed_businesses.{csv,json}``-shaped dicts) in,
a valid :class:`~engines.website_generation.contracts.artifacts.ListingDataset`
(current schema, 1.1.0 as of AES-WEB-002M.1) or a deterministic, typed
rejection report out -- never a partially-valid dataset.

Pure: no file I/O, no network, no clock, no randomness. File reading
(CSV/JSON parsing) is the caller's job (the pilot runner), and media
ingestion (file reads, signature validation, CAS writes) is
``media_ingestion.py``'s job (AES-WEB-002M.2); this module only ever sees
already-parsed Python data structures and already-ingested asset refs.

Lives under ``scripts/`` (not ``engines/website_generation/``) deliberately:
``tests/website_generation/architecture/test_import_audit.py`` and
``test_public_surface.py`` enforce that only ``engines/website_generation/
pipeline/`` composes sibling engine subpackages and that no unauthorized
top-level package appears under ``engines/website_generation/`` -- both
correctly reject a new pilot-only adapter package there. This module only
imports ``contracts/`` (never a sibling engine subpackage, e.g. ``ia/``),
matching the same layering discipline those tests enforce, and its
``slugify`` below is a small, documented duplicate of
``ia.information_architecture_engine.slugify`` for that same reason (the
"``is_safe_url`` duplicated across ``rendering/``/``contracts/``" precedent,
extended to a pilot-adapter/engine boundary).

Doctrine (PILOT-PTF-1 mission, "no fake inventory"):

* Deduplication key is case-insensitive ``(name, city, state)``; the winner
  is deterministic (first in the record set's own sorted order, mirroring
  ``engines/directory_builder/import_package_engine.py``'s established
  policy) -- duplicates are reported, never silently dropped or silently
  kept.
* An unknown category reference is a hard, batch-reported rejection --
  never a fabricated or default category.
* An unresolved location reference simply leaves ``location_id`` empty
  (``ListingRecord.location_id`` is optional, zero-or-one, per its own
  docstring) -- it is not an error, since a pilot's location list normally
  covers only some of its listings' cities.
* ``review_count`` is a required int on ``ListingRecord.rating``
  (``ListingRating``, a registered artifact -- no schema change is
  permitted here), so "unknown" is carried by convention: a negative
  sentinel (``-1``), the same convention
  ``component_engine._build_card_data``/``content_projection._format_rating``
  already use to omit an unknown review count from rendered output. A
  source that explicitly supplies zero reviews yields ``0``, never ``-1``.
* ``source_url`` is provenance only -- it never becomes a CTA. A CTA is
  created only when the enrichment overlay supplies a real business
  destination URL, always labeled "Visit website" (the approved v1 CTA
  label).
* ``rating_hundredths`` is derived via ``decimal.Decimal`` on the
  input's own string form, never ``float`` arithmetic -- ``"4.5"`` (or the
  float ``4.5``, converted via ``str()`` first) always yields exactly
  ``450``.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from decimal import Decimal, InvalidOperation
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from urllib.parse import urlsplit

from engines.website_generation.contracts.artifacts import (
    ArtifactKind,
    ListingAddress,
    ListingAssetRef,
    ListingCategory,
    ListingContact,
    ListingCTA,
    ListingDataset,
    ListingLocation,
    ListingProvenance,
    ListingRating,
    ListingRecord,
)
from engines.website_generation.contracts.render_data import is_safe_url
from engines.website_generation.contracts.versions import SCHEMA_VERSIONS

_SLUG_DISALLOWED_RUN = re.compile(r"[^a-z0-9]+")


def slugify(text: str) -> str:
    """Deterministic route-slug derivation -- byte-identical duplicate of
    ``ia.information_architecture_engine.slugify`` (module docstring)."""
    lowered = text.strip().lower()
    return _SLUG_DISALLOWED_RUN.sub("-", lowered).strip("-")


# The approved v1 CTA label (PILOT-PTF-1 §10 operator decision) -- never a
# different label, never inferred from source data.
_CTA_LABEL = "Visit website"

# The "unknown review count" sentinel (see module docstring).
_UNKNOWN_REVIEW_COUNT = -1


@dataclass(frozen=True)
class ListingDatasetBuildResult:
    """The converter's total output: either a valid ``dataset`` (``errors``
    empty) or ``dataset is None`` with a non-empty, deterministic ``errors``
    tuple -- never a partially-valid dataset. ``rejected_duplicates`` is
    populated independently of success/failure (a duplicate is reported,
    not an error, since the deterministic winner still produces a valid
    listing)."""

    dataset: Optional[ListingDataset]
    rejected_duplicates: Tuple[str, ...] = ()
    errors: Tuple[str, ...] = ()

    @property
    def ok(self) -> bool:
        return self.dataset is not None


def _normalize_key(value: Any) -> str:
    return str(value or "").strip().lower()


def _source_host(source_url: str) -> str:
    """The source's host identity (AES-WEB-002N.1 ``ListingProvenance.
    source_id``), deterministically derived from the URL -- falls back to
    the full URL when no host parses (never empty for a non-empty URL,
    since ``source_id`` is the one required provenance field)."""
    host = urlsplit(source_url).netloc.strip().lower()
    return host or source_url


def _strip_trailing_locality(street: str, city: str, state: str) -> str:
    """AES-WEB-002K.2 address-duplication fix. A seed record's ``address``
    field sometimes carries the full postal string, redundantly repeating
    the record's own ``city``/``state`` as a trailing locality (e.g. "123
    Sunset Bay Road, Columbus, OH" alongside separate ``city="Columbus"``,
    ``state="OH"`` fields). Left as-is, ``ListingAddress.street`` and
    ``ListingAddress.city``/``state`` get joined downstream into a visibly
    duplicated "123 Sunset Bay Road, Columbus, OH, Columbus, OH". This
    strips an exact, case-insensitive trailing ", City, State" match only
    -- a normal street-only value (no repeated locality) is returned
    unchanged, never altered speculatively."""
    street = street.strip()
    city = city.strip()
    state = state.strip()
    if not street or not city or not state:
        return street
    suffix = ", %s, %s" % (city, state)
    if street.lower().endswith(suffix.lower()):
        return street[: -len(suffix)].rstrip(", ").strip()
    return street


# Common street-suffix abbreviation variants (PILOT-PTF-1: two seed records
# for the same physical address but a slightly different business-name
# string -- e.g. "123 Sunset Bay Rd" vs "123 Sunset Bay Road" -- must still
# collapse to the same dedup key; a pure name-based key alone would let a
# re-submitted or typo'd listing through as if it were a distinct business).
_STREET_SUFFIX_VARIANTS: Tuple[Tuple[str, str], ...] = (
    ("road", "rd"), ("street", "st"), ("avenue", "ave"), ("drive", "dr"),
)


def _normalize_address(street: Any) -> str:
    # Strip punctuation to plain space-separated words first (the raw
    # address commonly carries commas: "123 Sunset Bay Road, Columbus,
    # OH") so a suffix word adjacent to a comma still matches.
    raw = _normalize_key(street)
    words = "".join(ch if ch.isalnum() else " " for ch in raw).split()
    variants = dict(_STREET_SUFFIX_VARIANTS)
    normalized_words = [variants.get(word, word) for word in words]
    return " ".join(normalized_words)


# AES-WEB-002N.1: the closed canonical-quality field set (operator decision
# 10). Canonical selection compares populated-field counts over exactly
# these raw-record fields -- arbitrary future optional fields never change
# canonical selection, and there is no fuzzy matching and no opaque
# scoring. "media" is populated when the record's (name, city, state)
# enrichment key has an authorized entry in the caller's media overlay.
_CANONICAL_QUALITY_FIELDS: Tuple[str, ...] = (
    "source_url",
    "website_url",
    "address",
    "pet_policy",
    "phone",
    "hours",
    "postal_code",
)


def _media_key(record: Mapping[str, Any]) -> Tuple[str, str, str]:
    return (
        _normalize_key(record.get("name")),
        _normalize_key(record.get("city")),
        _normalize_key(record.get("state")),
    )


def _canonical_quality_count(
    record: Mapping[str, Any],
    media_by_key: Mapping[Tuple[str, str, str], Tuple[Any, ...]],
) -> int:
    count = sum(
        1 for field in _CANONICAL_QUALITY_FIELDS
        if str(record.get(field, "") or "").strip()
    )
    if media_by_key.get(_media_key(record)):
        count += 1
    return count


def _is_truthy_marker(value: Any) -> bool:
    return str(value or "").strip().lower() in ("true", "yes", "1", "x")


def _select_canonical_record(
    group: List[Mapping[str, Any]],
    media_by_key: Mapping[Tuple[str, str, str], Tuple[Any, ...]],
) -> Mapping[str, Any]:
    """The canonical record among duplicates (AES-WEB-002N.1, operator
    decision 10), in strict priority order:

    1. Explicit operator override: exactly one record marked
       ``canonical`` wins outright. (Multiple markers cancel each other --
       contradictory operator input falls through to the deterministic
       rules rather than silently trusting either marker.)
    2. Most populated fields from the closed canonical-quality set
       (``_CANONICAL_QUALITY_FIELDS`` + authorized media).
    3. Longer non-empty ``pet_policy`` statement.
    4. Stable lexical name tie-break (ascending).
    """
    marked = [raw for raw in group if _is_truthy_marker(raw.get("canonical"))]
    if len(marked) == 1:
        return marked[0]
    return min(
        group,
        key=lambda raw: (
            -_canonical_quality_count(raw, media_by_key),
            -len(str(raw.get("pet_policy", "") or "").strip()),
            _normalize_key(raw.get("name")),
        ),
    )


def _dedup_key(record: Mapping[str, Any]) -> Tuple[str, str, str]:
    """Two records with the same normalized street address in the same
    city/state are the same physical business regardless of a differing
    name string; absent a usable address, dedup falls back to
    case-insensitive ``(name, city, state)`` (mission §1.A)."""
    city = _normalize_key(record.get("city"))
    state = _normalize_key(record.get("state"))
    address = _normalize_address(record.get("address"))
    if address:
        return (address, city, state)
    return (_normalize_key(record.get("name")), city, state)


def _parse_rating_hundredths(raw_rating: Any) -> Optional[int]:
    """``None`` when no rating was supplied at all (a listing may honestly
    carry no rating); raises :class:`InvalidOperation`/``ValueError`` on a
    genuinely malformed value -- the caller turns that into a batch error,
    never a silently-dropped rating."""
    if raw_rating in (None, ""):
        return None
    hundredths = Decimal(str(raw_rating)) * 100
    return int(hundredths)


def _resolve_category(
    raw_category: str, categories_by_key: Mapping[str, ListingCategory]
) -> Optional[ListingCategory]:
    key = _normalize_key(raw_category)
    return categories_by_key.get(key)


def _resolve_location(
    city: str, state: str, locations_by_key: Mapping[Tuple[str, str], ListingLocation]
) -> Optional[ListingLocation]:
    return locations_by_key.get((_normalize_key(city), _normalize_key(state)))


def _build_description(pet_policy: str, amenities: Sequence[str]) -> str:
    """Deterministic, factual-only description text (mission §1.H: "do not
    invent qualitative claims") -- a plain restatement of the pet policy and
    amenity list a source record already supplied, nothing more."""
    parts: List[str] = []
    pet_policy = (pet_policy or "").strip()
    if pet_policy:
        parts.append("Pet policy: %s." % pet_policy)
    cleaned_amenities = [a.strip() for a in amenities if str(a).strip()]
    if cleaned_amenities:
        parts.append("Amenities: %s." % ", ".join(cleaned_amenities))
    return " ".join(parts)


def build_categories(raw_categories: Sequence[Mapping[str, Any]]) -> Tuple[ListingCategory, ...]:
    """Pure ``categories.json``-shaped records -> ``ListingCategory`` tuple,
    deterministically ordered by slug. Each record needs ``name``/``slug``
    (``derived_from`` and any other launch-package bookkeeping field is
    ignored -- not part of the ``ListingCategory`` shape)."""
    categories = [
        ListingCategory(
            category_id="cat-%s" % raw["slug"],
            label=str(raw["name"]).strip(),
            slug=str(raw["slug"]).strip(),
        )
        for raw in raw_categories
    ]
    return tuple(sorted(categories, key=lambda c: c.slug))


def build_locations(raw_locations: Sequence[Mapping[str, Any]]) -> Tuple[ListingLocation, ...]:
    """Pure ``locations.json``-shaped records -> ``ListingLocation`` tuple,
    deterministically ordered by slug."""
    locations = [
        ListingLocation(
            location_id="loc-%s" % raw["slug"],
            city=str(raw["name"]).strip(),
            state=str(raw.get("state", "")).strip(),
            slug=str(raw["slug"]).strip(),
        )
        for raw in raw_locations
    ]
    return tuple(sorted(locations, key=lambda l: l.slug))


def build_listing_dataset(
    *,
    seed_businesses: Sequence[Mapping[str, Any]],
    categories: Sequence[Mapping[str, Any]],
    locations: Sequence[Mapping[str, Any]] = (),
    enrichment_by_key: Optional[Mapping[Tuple[str, str, str], Mapping[str, Any]]] = None,
    media_by_key: Optional[Mapping[Tuple[str, str, str], Tuple[ListingAssetRef, ...]]] = None,
) -> ListingDatasetBuildResult:
    """Convert parsed seed-package records into a ``ListingDataset``.

    ``enrichment_by_key`` is an optional overlay keyed by the same
    case-insensitive ``(name, city, state)`` dedup key, supplying real,
    operator-verified fields no launch-package seed file carries: a real
    CTA destination URL, phone, email, website, and per-day hours. Absent
    entirely, every listing simply carries no CTA/contact/hours (an honest,
    valid, less-enriched ``ListingRecord`` -- never fabricated).

    ``media_by_key`` (AES-WEB-002M.2) is the analogous optional media
    overlay, same ``(name, city, state)`` key shape: already-ingested
    ``ListingAssetRef`` tuples. The file-read/validate/CAS half lives in
    ``scripts/pettripfinder/media_ingestion.py`` -- this builder stays pure
    and I/O-free, receiving only durable hash-referenced metadata (no
    filesystem path ever reaches this function). Absent entirely, every
    listing simply carries no assets: the honest, valid, image-less record
    the current sample package produces.
    """
    enrichment_by_key = enrichment_by_key or {}
    media_by_key = media_by_key or {}
    resolved_categories = build_categories(categories)
    resolved_locations = build_locations(locations)
    categories_by_key = {_normalize_key(c.label): c for c in resolved_categories}
    categories_by_key.update({_normalize_key(c.slug): c for c in resolved_categories})
    locations_by_key = {(_normalize_key(l.city), _normalize_key(l.state)): l for l in resolved_locations}

    # Deterministic dedup: sort by the dedup key itself first, so the
    # "winner" never depends on the caller's file-read order (mirrors
    # engines/directory_builder/import_package_engine.py's established
    # policy).
    ordered = sorted(
        seed_businesses,
        key=lambda r: (_dedup_key(r), str(r.get("name", "")), str(r.get("source_url", ""))),
    )

    # AES-WEB-002N.1 canonical-record selection: group all records sharing a
    # dedup key, then choose the canonical one deterministically -- never
    # "whichever sorted first" (the rule that let a junk-named, less-complete
    # duplicate beat the real record). Rejected duplicates are always
    # reported with the winner's name, never silently discarded.
    groups: Dict[Tuple[str, str, str], List[Mapping[str, Any]]] = {}
    for raw in ordered:
        groups.setdefault(_dedup_key(raw), []).append(raw)

    seen_keys: Dict[Tuple[str, str, str], Mapping[str, Any]] = {}
    rejected_duplicates: List[str] = []
    for key in sorted(groups):
        group = groups[key]
        winner = _select_canonical_record(group, media_by_key)
        seen_keys[key] = winner
        for raw in group:
            if raw is winner:
                continue
            rejected_duplicates.append(
                "%s (%s, %s) -- duplicate of %s" % (
                    raw.get("name", ""), raw.get("city", ""), raw.get("state", ""),
                    winner.get("name", ""),
                )
            )

    errors: List[str] = []
    listings: List[ListingRecord] = []
    seen_slugs: Dict[str, str] = {}

    for key, raw in sorted(seen_keys.items()):
        name = str(raw.get("name", "")).strip()
        if not name:
            errors.append("malformed_record: seed record with key %r has no name" % (key,))
            continue

        category = _resolve_category(str(raw.get("category", "")), categories_by_key)
        if category is None:
            errors.append(
                "unresolved_category: listing %r names category %r, not present in categories"
                % (name, raw.get("category", ""))
            )
            continue

        slug = slugify(name)
        if not slug:
            errors.append("unsluggable_name: listing %r yields no derivable slug" % name)
            continue
        if slug in seen_slugs and seen_slugs[slug] != name:
            errors.append(
                "slug_collision: %r and %r both slugify to %r" % (seen_slugs[slug], name, slug)
            )
            continue
        seen_slugs[slug] = name

        try:
            rating_hundredths = _parse_rating_hundredths(raw.get("rating"))
        except (InvalidOperation, ValueError, ArithmeticError):
            errors.append("malformed_rating: listing %r rating %r is not decimal" % (name, raw.get("rating")))
            continue

        location = _resolve_location(str(raw.get("city", "")), str(raw.get("state", "")), locations_by_key)

        # Enrichment is looked up by the record's own (name, city, state) --
        # never by the dedup key, which may be address-based (see
        # _dedup_key) and so would be an unpredictable lookup shape for a
        # caller supplying enrichment by business name.
        enrichment_key = (
            _normalize_key(name), _normalize_key(raw.get("city")), _normalize_key(raw.get("state")),
        )
        enrichment = enrichment_by_key.get(enrichment_key, {})
        rating = None
        if rating_hundredths is not None:
            raw_review_count = enrichment.get("review_count")
            review_count = (
                int(raw_review_count) if raw_review_count is not None else _UNKNOWN_REVIEW_COUNT
            )
            rating = ListingRating(rating_hundredths=rating_hundredths, review_count=review_count)

        # AES-WEB-002N.1: contact facts may now arrive on the seed row
        # itself (the operator CSV); the enrichment overlay -- operator-
        # verified data -- still overrides seed values field-by-field.
        contact = None
        phone = str(enrichment.get("phone", raw.get("phone", "")) or "").strip()
        email = str(enrichment.get("email", "") or "").strip()
        website_url = str(enrichment.get("website_url", raw.get("website_url", "")) or "").strip()
        if website_url and not is_safe_url(website_url):
            errors.append("unsafe_website_url: listing %r website_url %r is unsafe" % (name, website_url))
            continue
        if phone or email or website_url:
            contact = ListingContact(phone=phone, email=email, website_url=website_url)

        raw_city = str(raw.get("city", "")).strip()
        raw_state = str(raw.get("state", "")).strip()
        address = ListingAddress(
            street=_strip_trailing_locality(str(raw.get("address", "")), raw_city, raw_state),
            city=raw_city,
            state=raw_state,
            postal_code=str(raw.get("postal_code", "") or "").strip(),
            country="US",
        )

        # AES-WEB-002N.1 provenance wiring: the seed's source facts finally
        # survive into the dataset (pre-N.1 the builder silently dropped
        # source_url despite its own "provenance only" doctrine).
        # observed_at is a preserved external input from the seed row --
        # never generated at build time (ListingProvenance's own doctrine;
        # deterministic builds stay deterministic). source_id is the
        # source's host identity, deterministically derived.
        provenance = None
        source_url = str(raw.get("source_url", "") or "").strip()
        if source_url:
            if not is_safe_url(source_url):
                errors.append("unsafe_source_url: listing %r source_url %r is unsafe" % (name, source_url))
                continue
            provenance = ListingProvenance(
                source_id=_source_host(source_url),
                source_type=str(raw.get("source_type", "") or "").strip(),
                source_url=source_url,
                observed_at=str(raw.get("observed_at", "") or "").strip(),
            )

        cta = None
        cta_url = str(enrichment.get("cta_url", "")).strip()
        if cta_url:
            if not is_safe_url(cta_url):
                errors.append("unsafe_cta_url: listing %r cta_url %r is unsafe" % (name, cta_url))
                continue
            cta = ListingCTA(label=_CTA_LABEL, target_route=cta_url)

        amenities = raw.get("amenities") or ()
        description = _build_description(str(raw.get("pet_policy", "")), amenities)

        listings.append(
            ListingRecord(
                listing_id=slug,
                business_name=name,
                slug=slug,
                category_id=category.category_id,
                location_id=location.location_id if location is not None else "",
                description=description,
                contact=contact,
                address=address,
                rating=rating,
                assets=tuple(media_by_key.get(enrichment_key, ())),
                cta=cta,
                provenance=provenance,
            )
        )

    if errors:
        return ListingDatasetBuildResult(
            dataset=None,
            rejected_duplicates=tuple(sorted(rejected_duplicates)),
            errors=tuple(sorted(errors)),
        )

    dataset = ListingDataset(
        schema_version=SCHEMA_VERSIONS[ArtifactKind.LISTING_DATASET],
        artifact_kind=ArtifactKind.LISTING_DATASET,
        source_hashes={},
        listings=tuple(sorted(listings, key=lambda l: (l.category_id, l.slug))),
        categories=resolved_categories,
        locations=resolved_locations,
    )
    return ListingDatasetBuildResult(dataset=dataset, rejected_duplicates=tuple(sorted(rejected_duplicates)))
