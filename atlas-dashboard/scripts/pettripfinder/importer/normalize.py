"""AES-DATA-001 importer -- pure deterministic normalizers (mission section
12). Three layers stay distinct: original source wording (kept in evidence),
normalized structured value (here), and publication prose (policy_compose).
No I/O, no network, no clock, no randomness.
"""

from __future__ import annotations

import re
import unicodedata
from typing import Optional

from scripts.pettripfinder.importer.constants import CATEGORY_SLUG_BY_IMPORTER

# --------------------------------------------------------------------------- #
# Text.
# --------------------------------------------------------------------------- #

_WS_RE = re.compile(r"\s+")


def normalize_whitespace(value: str) -> str:
    """NFC-normalize, convert non-breaking spaces, collapse runs of
    whitespace to single ASCII spaces, and strip. Deterministic and
    idempotent -- applied identically to snapshot text and to evidence
    quotes so span matching is stable across Unicode/whitespace variation."""
    if not value:
        return ""
    text = unicodedata.normalize("NFC", value)
    text = text.replace(" ", " ").replace("​", "")
    # Normalize common smart punctuation to ASCII so quote matching is robust.
    text = (text.replace("‘", "'").replace("’", "'")
                .replace("“", '"').replace("”", '"')
                .replace("–", "-").replace("—", "-"))
    return _WS_RE.sub(" ", text).strip()


def normalize_name(value: str) -> str:
    return normalize_whitespace(value)


# --------------------------------------------------------------------------- #
# Entity-name canonicalization (AES-DATA-001 live park-name defect).
#
# Page titles append site/organization branding to the entity name with a
# separator ("Scioto Audubon - Metro Parks - Central Ohio Park System",
# "Scioto Audubon | Metro Parks", "Metro Parks: Scioto Audubon"). These
# helpers strip that branding for name selection and decide whether two
# candidate names are the same entity or genuinely different.
# --------------------------------------------------------------------------- #

# Title/site separators, each surrounded by spaces (an intra-word hyphen in
# "Wal-Mart" is NOT space-flanked, so it is never split).
_BRAND_SEP_RE = re.compile(r"\s*[|•]\s*|\s+[–—]\s+|\s+-\s+|:\s+|\s*::\s*")

# Deterministic site/brand boilerplate hints. A trailing/leading title
# segment made of these is recognized as branding, not a distinct entity.
_SITE_BRAND_HINTS = (
    "park", "parks", "system", "metro", "central ohio", "official", "home",
    "hotels", "resorts", "inn", "department", "recreation", "reservations",
    "group", "company", "network", "guide", "directory", "visit ", "book ",
    "the official", "county", "city of", "state park", "trails",
)


def brand_split(name: str) -> list:
    """Split a name on recognized title/site separators."""
    return [s.strip() for s in _BRAND_SEP_RE.split(name or "") if s.strip()]


def looks_like_site_brand(segment: str) -> bool:
    """True when a title segment reads as site/organization boilerplate."""
    s = (segment or "").lower()
    return any(h in s for h in _SITE_BRAND_HINTS)


# Page-purpose title segments (FAQ / Hours, Parking & More / Contact / ...).
# A segment is page-purpose only when EVERY meaningful token is a page-purpose
# word AND at least one is a "strong" anchor -- so an isolated title segment
# like "FAQ" or "Hours, Parking & More" is boilerplate, while a literal entity
# name that merely contains such a word ("FAQ Coffee", "About Time Brewing")
# is never stripped.
_PAGE_PURPOSE_STRONG = frozenset({
    "faq", "faqs", "frequently", "asked", "questions", "contact", "hours",
    "parking", "locations", "location", "visit", "about", "menu", "menus",
    "gallery", "directions", "reservations", "reservation",
})
_PAGE_PURPOSE_WEAK = frozenset({
    "more", "info", "information", "overview", "details", "and", "us", "our",
    "the", "a", "of",
})


def looks_like_page_purpose(segment: str) -> bool:
    """True when a title segment is a page-purpose label (a whole segment made
    only of page-purpose words, with at least one strong anchor)."""
    tokens = re.findall(r"[a-z]+", (segment or "").lower())
    if not tokens:
        return False
    if not all(t in _PAGE_PURPOSE_STRONG or t in _PAGE_PURPOSE_WEAK for t in tokens):
        return False
    return any(t in _PAGE_PURPOSE_STRONG for t in tokens)


def is_boilerplate_segment(segment: str) -> bool:
    """A title segment is boilerplate when it is site/brand branding OR a
    page-purpose label."""
    return looks_like_site_brand(segment) or looks_like_page_purpose(segment)


def clean_entity_name(name: str) -> str:
    """Strip site/brand and page-purpose title segments, returning the entity
    segment. A name with no title separator is returned unchanged."""
    segs = brand_split(name)
    if len(segs) <= 1:
        return normalize_name(name)
    non_brand = [s for s in segs if not is_boilerplate_segment(s)]
    if len(non_brand) == 1:
        return normalize_name(non_brand[0])
    if non_brand:
        return normalize_name(max(non_brand, key=len))
    return normalize_name(segs[0])


def names_compatible(a: str, b: str) -> bool:
    """True when two candidate names denote the same entity: equal after
    normalization, or one is exactly a title segment of the other and every
    remaining segment is recognized site/brand boilerplate. Genuinely
    different names (different words, partial accidental overlap) are never
    compatible."""
    na, nb = normalize_name(a).lower(), normalize_name(b).lower()
    if not na or not nb:
        return False
    if na == nb:
        return True
    a_segs = [s.lower() for s in brand_split(na)]
    b_segs = [s.lower() for s in brand_split(nb)]
    if len(b_segs) >= 2 and na in b_segs and all(
            is_boilerplate_segment(s) for s in b_segs if s != na):
        return True
    if len(a_segs) >= 2 and nb in a_segs and all(
            is_boilerplate_segment(s) for s in a_segs if s != nb):
        return True
    return False


# --------------------------------------------------------------------------- #
# Expected-city trailing qualifier (AES-DATA-001 final restaurant-name defect).
#
# "Land-Grant Brewing Columbus" vs "Land-Grant Brewing" is a supported
# brand-short form -- but ONLY with operator context: the trailing qualifier
# must exactly equal the operator's expected city AND the page's geography
# must support that city. Deliberately context-bound: there is no generic
# "strip a trailing city" normalization, so "Columbus Brewing Company" never
# loses its leading city and an unexpected/unsupported city never matches.
# --------------------------------------------------------------------------- #

def expected_city_suffix_compatible(
    resolved: str, alternate: str, expected_city: str,
    geography_supported: bool,
) -> bool:
    """True when ``alternate`` is the brand-short form of ``resolved`` minus a
    trailing expected-city qualifier: resolved == "<base> <expected_city>",
    alternate == "<base>" exactly (so a competing city/location qualifier or
    a different base can never match), and page geography supports the
    expected city. False whenever expected-city/geography context is absent
    -- never a generic city strip."""
    if not (resolved and alternate and expected_city and geography_supported):
        return False
    r = normalize_name(resolved).lower()
    a = normalize_name(alternate).lower()
    city = normalize_name(expected_city).lower()
    if not (r and a and city):
        return False
    suffix = " " + city
    if not r.endswith(suffix):
        return False
    base = r[: -len(suffix)].strip()
    return bool(base) and a == base


# --------------------------------------------------------------------------- #
# Phone.
# --------------------------------------------------------------------------- #

def normalize_phone(value: str) -> str:
    """US 10-digit -> ``NNN-NNN-NNNN`` (matches the seed CSV). Leading US
    country code ``1`` is dropped. Returns "" when not a clean 10-digit
    number (never a guessed number)."""
    if not value:
        return ""
    digits = re.sub(r"\D", "", value)
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    if len(digits) != 10:
        return ""
    return "%s-%s-%s" % (digits[0:3], digits[3:6], digits[6:10])


# --------------------------------------------------------------------------- #
# Location.
# --------------------------------------------------------------------------- #

_US_STATES = {
    "alabama": "AL", "alaska": "AK", "arizona": "AZ", "arkansas": "AR",
    "california": "CA", "colorado": "CO", "connecticut": "CT", "delaware": "DE",
    "florida": "FL", "georgia": "GA", "hawaii": "HI", "idaho": "ID",
    "illinois": "IL", "indiana": "IN", "iowa": "IA", "kansas": "KS",
    "kentucky": "KY", "louisiana": "LA", "maine": "ME", "maryland": "MD",
    "massachusetts": "MA", "michigan": "MI", "minnesota": "MN", "mississippi": "MS",
    "missouri": "MO", "montana": "MT", "nebraska": "NE", "nevada": "NV",
    "new hampshire": "NH", "new jersey": "NJ", "new mexico": "NM", "new york": "NY",
    "north carolina": "NC", "north dakota": "ND", "ohio": "OH", "oklahoma": "OK",
    "oregon": "OR", "pennsylvania": "PA", "rhode island": "RI",
    "south carolina": "SC", "south dakota": "SD", "tennessee": "TN", "texas": "TX",
    "utah": "UT", "vermont": "VT", "virginia": "VA", "washington": "WA",
    "west virginia": "WV", "wisconsin": "WI", "wyoming": "WY",
    "district of columbia": "DC",
}
_STATE_CODES = frozenset(_US_STATES.values())


def normalize_state(value: str) -> str:
    if not value:
        return ""
    v = normalize_whitespace(value)
    up = v.upper()
    if up in _STATE_CODES:
        return up
    return _US_STATES.get(v.lower(), "")


def normalize_postal(value: str) -> str:
    """US ZIP: ``NNNNN`` or ``NNNNN-NNNN`` -> the 5-digit form. "" when not a
    valid US ZIP."""
    if not value:
        return ""
    m = re.match(r"^\s*(\d{5})(?:-\d{4})?\s*$", value)
    return m.group(1) if m else ""


def normalize_city(value: str) -> str:
    return normalize_whitespace(value)


_STREET_SUFFIX = normalize_whitespace


def normalize_address(street: str, city: str = "", state: str = "") -> str:
    """The CSV ``address`` column is the street line only (the builder holds
    city/state separately). Strip a trailing redundant ``, City, ST`` -- with
    or without a trailing ZIP -- if the extractor included it (matches the
    K.2 address-duplication guard). A trailing ZIP is only removed as part of
    a locality tail (when city/state are supplied), never blindly, so callers
    can still derive the postal code from the raw address first."""
    street = normalize_whitespace(street)
    ct = normalize_whitespace(city)
    st = normalize_state(state) or (state or "")
    if ct and st:
        street = re.sub(
            r",?\s*%s\s*,\s*%s(?:\s+\d{5}(?:-\d{4})?)?\s*$" % (re.escape(ct), re.escape(st)),
            "", street, flags=re.I)
    if st:
        street = re.sub(r",?\s*%s\s+\d{5}(?:-\d{4})?\s*$" % re.escape(st), "", street, flags=re.I)
    if ct:
        street = re.sub(r",?\s*%s\s*$" % re.escape(ct), "", street, flags=re.I)
    return street.strip().rstrip(",").strip()


# --------------------------------------------------------------------------- #
# Postal code from a full address (AES-DATA-001 live defect B).
# --------------------------------------------------------------------------- #

def extract_postal_from_address(text: str) -> str:
    """Derive a US ZIP (5-digit, from ZIP or ZIP+4) from an address string
    that already contains one. Prefers a trailing ZIP, then a ZIP directly
    after a 2-letter state; returns "" when the address carries no ZIP.
    Never fabricates a ZIP from city/state alone."""
    if not text:
        return ""
    m = re.search(r"(\d{5})(?:-\d{4})?\s*$", text.strip())
    if m:
        return m.group(1)
    m = re.search(r"\b[A-Za-z]{2}\.?\s+(\d{5})(?:-\d{4})?\b", text)
    if m:
        return m.group(1)
    return ""


# --------------------------------------------------------------------------- #
# Phone role classification (AES-DATA-001 live defect A).
# --------------------------------------------------------------------------- #

PHONE_ROLE_PROPERTY = "PROPERTY_PHONE"
PHONE_ROLE_RESERVATION = "RESERVATION_PHONE"
PHONE_ROLE_BRAND = "BRAND_PHONE"
PHONE_ROLE_UNKNOWN = "UNKNOWN_PHONE"
# Deterministic precedence for the single production CSV ``phone`` field.
PHONE_ROLE_PRECEDENCE = (
    PHONE_ROLE_PROPERTY, PHONE_ROLE_RESERVATION, PHONE_ROLE_BRAND, PHONE_ROLE_UNKNOWN,
)

_TOLL_FREE_AREA = frozenset({"800", "888", "877", "866", "855", "844", "833"})
# A vanity toll-free number such as "800-DRURYINN" or "1-888-CALL-NOW".
_VANITY_RE = re.compile(r"\b(?:1[-.\s]?)?8(?:00|88|77|66|55|44|33)[-.\s]?[A-Za-z]{3,}")
_PROPERTY_SIGNAL_RE = re.compile(
    r"(?:\bp\s*:|phone\s*:|\bproperty\b|front\s*desk|local\s+(?:number|phone))", re.I)


def classify_phone_role(value: str, quote: str = "") -> str:
    """Classify a phone number's role from the number and its surrounding
    evidence wording. Deterministic; used to pick the property number over a
    central reservation/brand number without treating them as a conflict."""
    q = quote or ""
    ql = q.lower()
    digits = re.sub(r"\D", "", value or "")
    if len(digits) == 11 and digits.startswith("1"):
        digits = digits[1:]
    area = digits[:3] if len(digits) == 10 else ""
    toll_free = area in _TOLL_FREE_AREA
    vanity = bool(_VANITY_RE.search(q))

    if toll_free or vanity or "reservation" in ql or "central booking" in ql:
        if "brand" in ql or "central booking" in ql:
            return PHONE_ROLE_BRAND
        return PHONE_ROLE_RESERVATION
    if _PROPERTY_SIGNAL_RE.search(q):
        return PHONE_ROLE_PROPERTY
    return PHONE_ROLE_UNKNOWN


# --------------------------------------------------------------------------- #
# URLs and dates.
# --------------------------------------------------------------------------- #

def normalize_url(value: str) -> str:
    """Lower-case scheme+host, strip fragments and default ports. Returns ""
    for non-http(s) input. Does not fabricate a scheme."""
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
    rest = m.group(3)
    rest = rest.split("#", 1)[0]
    return "%s://%s%s" % (scheme, host, rest)


def normalize_date(value: str) -> str:
    """Accept ISO ``YYYY-MM-DD`` (or an ISO datetime prefix); return the
    date. "" for anything else -- never a guessed date."""
    if not value:
        return ""
    m = re.match(r"^\s*(\d{4})-(\d{2})-(\d{2})", value)
    if not m:
        return ""
    y, mo, d = int(m.group(1)), int(m.group(2)), int(m.group(3))
    if not (1 <= mo <= 12 and 1 <= d <= 31):
        return ""
    return "%04d-%02d-%02d" % (y, mo, d)


# --------------------------------------------------------------------------- #
# Numeric pet facts.
# --------------------------------------------------------------------------- #

def normalize_fee(value: str) -> str:
    """Extract a USD amount as ``$N`` (integer dollars). "" when no clean
    amount is present. Keeps only the number; the fee *basis* is a separate
    field."""
    if not value:
        return ""
    m = re.search(r"\$\s*([0-9][0-9,]*)(?:\.(\d{2}))?", value)
    if not m:
        return ""
    dollars = m.group(1).replace(",", "")
    return "$%d" % int(dollars)


def normalize_weight(value: str) -> str:
    """Weight in pounds -> ``N lb``. "" when absent."""
    if not value:
        return ""
    m = re.search(r"(\d{1,3})\s*(?:lb|lbs|pound)", value, re.I)
    if not m:
        return ""
    return "%d lb" % int(m.group(1))


_COUNT_WORDS = {"one": "1", "two": "2", "three": "3", "four": "4",
                "five": "5", "six": "6"}
# A pet-count phrase: a number (word or digit) directly modifying "pet"/"dog"/
# "cat", covering "limit of two pets", "maximum of 2 pets", "up to two pets",
# "no more than two pets", "two pets per room".
_COUNT_PHRASE_RE = re.compile(
    r"\b(one|two|three|four|five|six|\d{1,2})\b\s+(?:well[-\s]?behaved\s+)?"
    r"(?:pet|dog|cat)s?\b", re.I)


def normalize_count(value: str) -> str:
    """A small integer pet count -> its digits. Recognizes count phrases
    ("limit of two pets", "maximum of 2 pets", "up to two pets", "two pets
    per room") as well as a bare word/number. "" when absent."""
    if not value:
        return ""
    v = value.strip().lower()
    if v in _COUNT_WORDS:
        return _COUNT_WORDS[v]
    m = _COUNT_PHRASE_RE.search(v)
    if m:
        tok = m.group(1)
        if tok in _COUNT_WORDS:
            return _COUNT_WORDS[tok]
        return tok if tok.isdigit() and 1 <= int(tok) <= 20 else ""
    m = re.search(r"\b([1-9])\b", v)
    return m.group(1) if m else ""


_TRUE = frozenset({"true", "yes", "y", "allowed", "welcome", "permitted", "1"})
_FALSE = frozenset({"false", "no", "n", "not allowed", "prohibited",
                    "not permitted", "0"})


def normalize_bool(value: str) -> Optional[bool]:
    """Deterministic tri-state: True / False / None (unknown). Never guesses
    from marketing prose -- only explicit tokens."""
    if value is None:
        return None
    v = normalize_whitespace(str(value)).lower()
    if not v:
        return None
    if v in _TRUE:
        return True
    if v in _FALSE:
        return False
    return None


def normalize_category_id(importer_category: str) -> str:
    """Importer category -> launch-package category slug (the CSV
    ``category`` column)."""
    return CATEGORY_SLUG_BY_IMPORTER.get(importer_category, "")
