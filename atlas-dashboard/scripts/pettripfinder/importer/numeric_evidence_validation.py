"""AES-DATA-004E (Task 6) -- numeric pet-policy evidence semantic validator.

Fixes the live-observed defect (AES-DATA-004D, InTown Suites candidate): an
LLM extraction quoted "Room Reservations: 1-888-882-0805" as evidence for
``pet_count_limit = 1``, misreading a phone number as a pet count. It never
reached a published fact (the candidate correctly REJECTed on
``pets_allowed=false``), but nothing in the pipeline would have caught it had
the same page been otherwise pet-friendly.

Deterministic, category-general: a POSITIVE semantic anchor for the target
field must be present in the evidence's OWN ``snapshot_quote`` (never the
whole page) before the number is trusted. Evidence containing an unrelated
number is never rejected merely for containing another number -- only for
lacking the anchor a real pet-policy statement about THIS field would carry.
"""

from __future__ import annotations

import re
from typing import Tuple

# Fields this validator applies to (mission Task 6). "pet_deposit" is not a
# lodging-pack field today (only pet_fee/weight_limit/pet_count_limit are);
# included defensively so any future numeric field reuses this validator
# without a second implementation.
NUMERIC_SEMANTIC_FIELDS = frozenset({
    "pet_count_limit", "weight_limit", "pet_fee", "pet_deposit",
})

_PET_KEYWORDS = ("pet", "pets", "animal", "animals", "dog", "dogs", "cat", "cats")
_COUNT_KEYWORDS = (
    "per room", "per stay", "per suite", "per night", "per reservation",
    "maximum", "max", "up to", "limit", "allowed", "permitted", "each room",
)
_WEIGHT_KEYWORDS = ("pound", "pounds", "lb", "lbs", "weigh", "weight")
_FEE_KEYWORDS = (
    "fee", "fees", "deposit", "charge", "non-refundable", "nonrefundable",
    "per stay", "per night", "per pet", "per visit",
)

# Negative/noise patterns, used only to LABEL why a non-anchored quote is
# implausible (never to override a genuine positive anchor -- doctrine: "do
# not reject valid evidence merely because it contains other numbers").
_PHONE_RE = re.compile(r"\b1?[\s.\-]?\(?\d{3}\)?[\s.\-]\d{3}[\s.\-]\d{4}\b")
_PHONE_KEYWORDS = ("call ", "reservations", "phone:", "phone ", "tel:", "toll-free", "toll free")
_ADDRESS_KEYWORDS = (
    "street", " st.", " st,", " ave", "avenue", "blvd", "boulevard", "suite",
    " dr.", " dr,", "drive", " rd.", " rd,", "road", "highway", "hwy",
)
_ZIP_RE = re.compile(r"\b\d{5}(-\d{4})?\b")
_COPYRIGHT_KEYWORDS = ("copyright", "©", "all rights reserved")
_ROOM_COUNT_RE = re.compile(r"\b\d{1,4}\s+(guest\s+)?rooms?\b")
_RESERVATION_KEYWORDS = (
    "confirmation", "reservation number", "reservation #", "loyalty",
    "rewards number", "rewards #", "member id", "membership number",
)

REASON_PHONE_NUMBER_PATTERN = "phone_number_pattern"
REASON_ZIP_OR_ADDRESS_PATTERN = "zip_or_address_pattern"
REASON_COPYRIGHT_YEAR_PATTERN = "copyright_year_pattern"
REASON_ROOM_COUNT_PATTERN = "room_count_pattern"
REASON_RESERVATION_NUMBER_PATTERN = "reservation_number_pattern"
REASON_NO_FIELD_SEMANTIC_ANCHOR = "no_field_semantic_anchor"


def _has_positive_anchor(field_name: str, lowered: str) -> bool:
    if field_name == "pet_count_limit":
        return (any(k in lowered for k in _PET_KEYWORDS)
                and any(k in lowered for k in _COUNT_KEYWORDS))
    if field_name == "weight_limit":
        return any(k in lowered for k in _WEIGHT_KEYWORDS)
    if field_name in ("pet_fee", "pet_deposit"):
        return "$" in lowered and any(k in lowered for k in _FEE_KEYWORDS)
    return False


def _negative_reason(lowered: str) -> str:
    # Keyword-anchored checks (reservation/confirmation, copyright, room
    # count, phone) are checked before the bare-shape ZIP regex: a coincidental
    # 5-digit number (e.g. a confirmation number) must not be mislabeled as a
    # ZIP code just because it happens to be five digits long.
    if any(k in lowered for k in _RESERVATION_KEYWORDS):
        return REASON_RESERVATION_NUMBER_PATTERN
    if any(k in lowered for k in _COPYRIGHT_KEYWORDS):
        return REASON_COPYRIGHT_YEAR_PATTERN
    if _ROOM_COUNT_RE.search(lowered):
        return REASON_ROOM_COUNT_PATTERN
    if _PHONE_RE.search(lowered) or any(k in lowered for k in _PHONE_KEYWORDS):
        return REASON_PHONE_NUMBER_PATTERN
    if any(k in lowered for k in _ADDRESS_KEYWORDS) or _ZIP_RE.search(lowered):
        return REASON_ZIP_OR_ADDRESS_PATTERN
    return REASON_NO_FIELD_SEMANTIC_ANCHOR


def validate_numeric_plausibility(field_name: str, snapshot_quote: str) -> Tuple[bool, str]:
    """Returns ``(is_plausible, reason)``; ``reason`` is "" when plausible.
    Positive-anchor-first: a quote containing BOTH a phone-shaped number and
    a genuine field anchor (e.g. "Call 1-888-555-0100 about our pet policy:
    maximum 2 pets per room.") is still plausible -- the anchor is what
    matters, not the mere presence of another number."""
    lowered = (snapshot_quote or "").lower()
    if field_name not in NUMERIC_SEMANTIC_FIELDS:
        return (True, "")
    if _has_positive_anchor(field_name, lowered):
        return (True, "")
    return (False, _negative_reason(lowered))
