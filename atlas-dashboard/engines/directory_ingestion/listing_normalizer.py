"""
Module 2 — Listing Normalizer
=============================

Converts RawListing payloads into canonical NormalizedListing records via a
reusable, declarative field-mapping system.

Deterministic. No I/O, no SQL, no external APIs.
"""

from __future__ import annotations

import hashlib
import re
from dataclasses import dataclass
from typing import Callable, Optional

from engines.directory_ingestion.ingestion_models import (
    NormalizedListing,
    Provenance,
    RawListing,
    SourceType,
    TaggedValue,
)

# ---------------------------------------------------------------------------
# Named constants
# ---------------------------------------------------------------------------

# Sources whose data is treated as verified at ingestion time.
_VERIFIED_SOURCES = frozenset(
    {SourceType.GOVERNMENT_OPEN_DATA, SourceType.ASSOCIATION_WEBSITE}
)

# Confidence contribution per populated core field (sums with base).
_CONFIDENCE_BASE = 0.20
_CONFIDENCE_PER_CORE_FIELD = 0.10
_CORE_FIELDS = ("address", "city", "state", "phone", "website")
_CONFIDENCE_VERIFIED_BONUS = 0.15
_CONFIDENCE_MAX = 1.0

_US_STATE_CODES = frozenset(
    "AL AK AZ AR CA CO CT DE FL GA HI ID IL IN IA KS KY LA ME MD MA MI MN MS "
    "MO MT NE NV NH NJ NM NY NC ND OH OK OR PA RI SC SD TN TX UT VT VA WA WV "
    "WI WY DC".split()
)

_US_STATE_NAMES = {
    "alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR",
    "california": "CA", "colorado": "CO", "connecticut": "CT", "delaware": "DE",
    "florida": "FL", "georgia": "GA", "hawaii": "HI", "idaho": "ID",
    "illinois": "IL", "indiana": "IN", "iowa": "IA", "kansas": "KS",
    "kentucky": "KY", "louisiana": "LA", "maine": "ME", "maryland": "MD",
    "massachusetts": "MA", "michigan": "MI", "minnesota": "MN",
    "mississippi": "MS", "missouri": "MO", "montana": "MT", "nebraska": "NE",
    "nevada": "NV", "new hampshire": "NH", "new jersey": "NJ",
    "new mexico": "NM", "new york": "NY", "north carolina": "NC",
    "north dakota": "ND", "ohio": "OH", "oklahoma": "OK", "oregon": "OR",
    "pennsylvania": "PA", "rhode island": "RI", "south carolina": "SC",
    "south dakota": "SD", "tennessee": "TN", "texas": "TX", "utah": "UT",
    "vermont": "VT", "virginia": "VA", "washington": "WA",
    "west virginia": "WV", "wisconsin": "WI", "wyoming": "WY",
    "district of columbia": "DC",
}

_PHONE_DIGITS_US = 10
_PHONE_DIGITS_US_WITH_COUNTRY = 11
_ZIP_RE = re.compile(r"^(\d{5})(?:-\d{4})?$")
_EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
_LAT_MIN, _LAT_MAX = -90.0, 90.0
_LNG_MIN, _LNG_MAX = -180.0, 180.0

_LOWERCASE_NAME_WORDS = frozenset({"and", "of", "the", "for", "at", "on", "in"})


# ---------------------------------------------------------------------------
# Reusable mapping system
# ---------------------------------------------------------------------------

@dataclass(frozen=True)
class FieldMapping:
    """
    Declarative mapping from a canonical Atlas field to candidate source keys.

    ``source_keys`` are checked in order; first non-empty value wins.
    """
    atlas_field: str
    source_keys: tuple[str, ...]


# Default mapping profile covering the most common source vocabularies
# (Google Places exports, government CSVs, association rosters).
DEFAULT_MAPPING_PROFILE: tuple[FieldMapping, ...] = (
    FieldMapping("business_name", ("business_name", "name", "company", "listing_name", "dba")),
    FieldMapping("address", ("address", "street_address", "address1", "addr", "street")),
    FieldMapping("city", ("city", "town", "locality")),
    FieldMapping("state", ("state", "region", "province", "state_code")),
    FieldMapping("zip_code", ("zip", "zip_code", "postal_code", "zipcode")),
    FieldMapping("country", ("country", "country_code")),
    FieldMapping("phone", ("phone", "phone_number", "telephone", "tel")),
    FieldMapping("website", ("website", "url", "web", "homepage", "site")),
    FieldMapping("email", ("email", "email_address", "contact_email")),
    FieldMapping("categories", ("categories", "category", "type", "business_type")),
    FieldMapping("subcategories", ("subcategories", "subcategory")),
    FieldMapping("hours", ("hours", "opening_hours", "business_hours")),
    FieldMapping("latitude", ("latitude", "lat")),
    FieldMapping("longitude", ("longitude", "lng", "lon", "long")),
    FieldMapping("amenities", ("amenities",)),
    FieldMapping("services", ("services", "services_offered")),
    FieldMapping("pricing_notes", ("pricing_notes", "pricing", "price_range")),
    FieldMapping("description", ("description", "about", "summary", "bio")),
    FieldMapping("seo_summary", ("seo_summary", "meta_description")),
)


class ListingNormalizer:
    """
    Stateless normalizer.

    A custom mapping profile may be supplied per source; the default profile
    covers common vocabularies. Field values are cleaned by dedicated,
    deterministic normalizer functions.
    """

    def __init__(
        self,
        mapping_profile: tuple[FieldMapping, ...] = DEFAULT_MAPPING_PROFILE,
    ) -> None:
        self._profile = mapping_profile
        self._index: dict[str, tuple[str, ...]] = {
            m.atlas_field: m.source_keys for m in mapping_profile
        }

    # -- public API ----------------------------------------------------------

    def normalize(self, raw: RawListing) -> Optional[NormalizedListing]:
        """
        Normalize one raw listing. Returns None if the record has no usable
        business name (unrecoverable — an enrichment task cannot name a
        business that was never named).
        """
        payload = {k.strip().lower(): v for k, v in raw.payload_dict().items()}

        name_raw = self._pick(payload, "business_name")
        business_name = self._normalize_name(name_raw)
        if not business_name:
            return None

        verified = raw.source_type in _VERIFIED_SOURCES
        tag = Provenance.VERIFIED if verified else Provenance.ESTIMATED

        phone = self._normalize_phone(self._pick(payload, "phone"))
        website = self._normalize_website(self._pick(payload, "website"))
        email = self._normalize_email(self._pick(payload, "email"))
        state = self._normalize_state(self._pick(payload, "state"))
        zip_code = self._normalize_zip(self._pick(payload, "zip_code"))
        city = self._clean_text(self._pick(payload, "city"))
        address = self._clean_text(self._pick(payload, "address"))
        country = self._clean_text(self._pick(payload, "country")) or "US"

        latitude = self._normalize_coord(self._pick(payload, "latitude"), _LAT_MIN, _LAT_MAX)
        longitude = self._normalize_coord(self._pick(payload, "longitude"), _LNG_MIN, _LNG_MAX)

        listing = NormalizedListing(
            listing_id=self._listing_id(raw.raw_id, business_name),
            raw_id=raw.raw_id,
            business_name=business_name,
            address=self._tag(address, tag),
            city=self._tag(city, tag),
            state=self._tag(state, tag),
            zip_code=self._tag(zip_code, tag),
            country=self._tag(country, Provenance.ESTIMATED if country == "US" and not self._pick(payload, "country") else tag),
            phone=self._tag(phone, tag),
            website=self._tag(website, tag),
            email=self._tag(email, tag),
            categories=self._split_list(self._pick(payload, "categories")),
            subcategories=self._split_list(self._pick(payload, "subcategories")),
            hours=self._tag(self._clean_text(self._pick(payload, "hours")), tag),
            latitude=latitude,
            longitude=longitude,
            amenities=self._split_list(self._pick(payload, "amenities")),
            services=self._split_list(self._pick(payload, "services")),
            pricing_notes=self._tag(self._clean_text(self._pick(payload, "pricing_notes")), tag),
            description=self._tag(self._clean_text(self._pick(payload, "description")), tag),
            seo_summary=self._tag(self._clean_text(self._pick(payload, "seo_summary")), tag),
            source_type=raw.source_type,
            source_url=raw.source_url,
            confidence=0.0,  # replaced below
            verified=verified,
        )
        return self._with_confidence(listing)

    def normalize_batch(self, raws: list[RawListing]) -> tuple[list[NormalizedListing], list[str]]:
        """Returns (normalized, rejected_raw_ids)."""
        out: list[NormalizedListing] = []
        rejected: list[str] = []
        for raw in raws:
            n = self.normalize(raw)
            if n is None:
                rejected.append(raw.raw_id)
            else:
                out.append(n)
        return out, rejected

    # -- field normalizers -----------------------------------------------------

    def _pick(self, payload: dict[str, str], atlas_field: str) -> Optional[str]:
        for key in self._index.get(atlas_field, ()):
            value = payload.get(key)
            if value is not None and value.strip():
                return value.strip()
        return None

    @staticmethod
    def _clean_text(value: Optional[str]) -> Optional[str]:
        if not value:
            return None
        cleaned = re.sub(r"\s+", " ", value).strip()
        return cleaned or None

    @classmethod
    def _normalize_name(cls, value: Optional[str]) -> Optional[str]:
        cleaned = cls._clean_text(value)
        if not cleaned:
            return None
        # Title-case ALL-CAPS / all-lower names; preserve mixed-case as-is.
        if cleaned.isupper() or cleaned.islower():
            words = cleaned.lower().split()
            titled = [
                w if (i > 0 and w in _LOWERCASE_NAME_WORDS) else w.capitalize()
                for i, w in enumerate(words)
            ]
            cleaned = " ".join(titled)
        return cleaned

    @staticmethod
    def _normalize_phone(value: Optional[str]) -> Optional[str]:
        if not value:
            return None
        digits = re.sub(r"\D", "", value)
        if len(digits) == _PHONE_DIGITS_US_WITH_COUNTRY and digits.startswith("1"):
            digits = digits[1:]
        if len(digits) != _PHONE_DIGITS_US:
            return None
        return f"({digits[0:3]}) {digits[3:6]}-{digits[6:]}"

    @staticmethod
    def _normalize_website(value: Optional[str]) -> Optional[str]:
        if not value:
            return None
        url = value.strip().lower()
        if url in {"n/a", "none", "-"}:
            return None
        if not url.startswith(("http://", "https://")):
            url = "https://" + url
        url = url.rstrip("/")
        if "." not in url.split("//", 1)[-1]:
            return None
        return url

    @staticmethod
    def _normalize_email(value: Optional[str]) -> Optional[str]:
        if not value:
            return None
        email = value.strip().lower()
        return email if _EMAIL_RE.match(email) else None

    @staticmethod
    def _normalize_state(value: Optional[str]) -> Optional[str]:
        if not value:
            return None
        candidate = value.strip()
        if candidate.upper() in _US_STATE_CODES:
            return candidate.upper()
        return _US_STATE_NAMES.get(candidate.lower())

    @staticmethod
    def _normalize_zip(value: Optional[str]) -> Optional[str]:
        if not value:
            return None
        match = _ZIP_RE.match(value.strip())
        return match.group(0) if match else None

    @staticmethod
    def _normalize_coord(value: Optional[str], low: float, high: float) -> Optional[float]:
        if not value:
            return None
        try:
            coord = float(value)
        except ValueError:
            return None
        return coord if low <= coord <= high else None

    @staticmethod
    def _split_list(value: Optional[str]) -> tuple[str, ...]:
        if not value:
            return ()
        parts = re.split(r"[;,|]", value)
        seen: list[str] = []
        for p in parts:
            item = p.strip()
            if item and item.lower() not in {s.lower() for s in seen}:
                seen.append(item)
        return tuple(seen)

    # -- helpers -----------------------------------------------------------------

    @staticmethod
    def _tag(value: Optional[str], provenance: Provenance) -> TaggedValue:
        if value is None:
            return TaggedValue.unknown()
        return TaggedValue(value=value, provenance=provenance)

    @staticmethod
    def _listing_id(raw_id: str, business_name: str) -> str:
        digest = hashlib.sha256(f"{raw_id}::{business_name}".encode()).hexdigest()
        return f"lst_{digest[:16]}"

    @staticmethod
    def _with_confidence(listing: NormalizedListing) -> NormalizedListing:
        populated = 0
        for field_name in _CORE_FIELDS:
            tv: TaggedValue = getattr(listing, field_name)
            if tv.value:
                populated += 1
        confidence = _CONFIDENCE_BASE + populated * _CONFIDENCE_PER_CORE_FIELD
        if listing.verified:
            confidence += _CONFIDENCE_VERIFIED_BONUS
        confidence = min(_CONFIDENCE_MAX, round(confidence, 2))
        # frozen dataclass → rebuild with confidence
        from dataclasses import replace
        return replace(listing, confidence=confidence)
