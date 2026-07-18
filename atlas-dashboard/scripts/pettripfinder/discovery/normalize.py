"""AES-DATA-004A discovery -- provider-record normalization (Task 8).

Self-contained: does NOT import ``scripts.pettripfinder.importer.normalize``.
Generic formatting (phone/state/ZIP/URL) mirrors that module's well-
established algorithms (10-digit US phone, state name/code table, 5-digit
ZIP, registrable-domain-as-last-two-labels) by independent reimplementation
here, not by cross-package import -- discovery and the importer are
deliberately kept decoupled (mission: "do not modify the importer unless a
truly shared contract requires it"). Identity/title-suffix reconciliation
(``names_compatible`` in the importer) is deliberately NOT mirrored:
provider ``name`` fields (Google ``displayName``, OSM ``name`` tag) do not
carry the marketing-tagline-in-a-page-title artifact that motivated that
logic, so discovery's name normalization stays a plain, conservative
formatting pass -- never brand/tagline stripping, and never fuzzy/prefix
matching, so chain-location qualifiers ("Petco Columbus #864" vs. a
different address's "Petco", "MedVet Columbus" vs. "MedVet Hilliard",
"Hilton Downtown" vs. "Hilton Easton") are preserved by construction
(Task 8's required examples).

Never discards the raw provider value -- every function here returns a
*new* value; callers keep the original on the record alongside it.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import replace
from typing import Optional, Tuple

from scripts.pettripfinder.discovery.models import DiscoveryRecord

_WS_RE = re.compile(r"\s+")
_PUNCT_STRIP_RE = re.compile(r"[^\w\s&]", re.UNICODE)

_US_STATES = {
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
_US_STATE_CODES = frozenset(_US_STATES.values())


def normalize_unicode(value: str) -> str:
    return unicodedata.normalize("NFKC", value or "")


def normalize_whitespace(value: str) -> str:
    return _WS_RE.sub(" ", (value or "")).strip()


def normalize_business_name(value: str) -> str:
    """Plain, conservative canonical form for equality comparison: unicode-
    normalize, lowercase, collapse whitespace, strip punctuation except
    ``&`` and word characters. Deliberately no brand/tagline stripping."""
    v = normalize_whitespace(normalize_unicode(value)).lower()
    v = _PUNCT_STRIP_RE.sub("", v)
    return normalize_whitespace(v)


def normalize_phone(value: str) -> str:
    if not value:
        return ""
    digits = re.sub(r"\D", "", value)
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    if len(digits) != 10:
        return ""
    return "%s-%s-%s" % (digits[0:3], digits[3:6], digits[6:10])


def normalize_state(value: str) -> str:
    if not value:
        return ""
    v = normalize_whitespace(value)
    up = v.upper()
    if up in _US_STATE_CODES:
        return up
    return _US_STATES.get(v.lower(), "")


def normalize_postal(value: str) -> str:
    if not value:
        return ""
    m = re.match(r"^\s*(\d{5})(?:-\d{4})?\s*$", value)
    return m.group(1) if m else ""


def normalize_address_line(value: str) -> str:
    return normalize_whitespace(normalize_unicode(value))


def normalize_url(value: str) -> str:
    if not value:
        return ""
    v = value.strip()
    m = re.match(r"^(https?)://([^/?#]+)(.*)$", v, re.I)
    if not m:
        return ""
    scheme = m.group(1).lower()
    host = m.group(2).lower()
    if host.endswith(":80") and scheme == "http":
        host = host[:-3]
    if host.endswith(":443") and scheme == "https":
        host = host[:-4]
    rest = m.group(3).rstrip("/")
    return "%s://%s%s" % (scheme, host, rest)


def registrable_domain(url_or_host: str) -> str:
    """Last two dot-separated labels -- the same simplification already
    established in scripts.pettripfinder.importer.candidate._registrable
    (does not special-case multi-part public suffixes like ``.co.uk``;
    disclosed, not fixed here, per "do not modify the importer")."""
    value = url_or_host or ""
    m = re.match(r"^https?://([^/?#]+)", value, re.I)
    host = (m.group(1) if m else value).lower().strip(".")
    host = host.split(":")[0]
    labels = host.split(".")
    return ".".join(labels[-2:]) if len(labels) >= 2 else host


def names_loosely_compatible(a: str, b: str) -> bool:
    """Conservative equality after formatting normalization only -- exact
    match required, no fuzzy/prefix/substring logic. This is intentionally
    weaker than the importer's ``names_compatible``: it is one ingredient in
    dedup scoring, never sufficient alone (Task 9)."""
    na, nb = normalize_business_name(a), normalize_business_name(b)
    return bool(na) and na == nb


def validate_coordinate(lat: Optional[float], lng: Optional[float]) -> bool:
    if lat is None or lng is None:
        return False
    if not (-90.0 <= lat <= 90.0 and -180.0 <= lng <= 180.0):
        return False
    if lat == 0.0 and lng == 0.0:          # "null island" sentinel-bug signal
        return False
    return True


def normalize_record(record: DiscoveryRecord) -> DiscoveryRecord:
    """Returns a new ``DiscoveryRecord`` with derived normalized fields
    filled in. Raw provider fields (``name``, ``address_line``, ``phone``,
    ``website_url``, ...) are left exactly as the adapter produced them --
    only ``normalized_name`` is newly populated, plus in-place format
    tightening of phone/state/postal/address/url (still the same
    information, not a different value)."""
    warnings = list(record.warnings)
    lat, lng = record.latitude, record.longitude
    if not validate_coordinate(lat, lng):
        if lat is not None or lng is not None:
            warnings.append("invalid_coordinates_dropped")
        lat, lng = None, None
    return replace(
        record,
        normalized_name=normalize_business_name(record.name),
        phone=normalize_phone(record.phone),
        website_url=normalize_url(record.website_url),
        state=normalize_state(record.state) or record.state,
        postal_code=normalize_postal(record.postal_code) or record.postal_code,
        address_line=normalize_address_line(record.address_line),
        latitude=lat, longitude=lng,
        warnings=tuple(warnings),
    )


def normalize_records(records: Tuple[DiscoveryRecord, ...]) -> Tuple[DiscoveryRecord, ...]:
    return tuple(normalize_record(r) for r in records)
