"""AES-DATA-004B Phase 9 -- known-inventory recall spot-check.

Reads the existing production seed CSV *read-only* to recover the earlier
20-hotel Columbus/Dublin research set (added in commit ``eccede7``) purely
as a recall spot-check against fresh discovery output. Never used as a
provider record, never used to inject missing candidates, never treated as
a complete denominator -- doctrine: "Use it only as a recall spot-check."
"""

from __future__ import annotations

import csv
from dataclasses import dataclass
from pathlib import Path
from typing import Sequence, Tuple

from scripts.pettripfinder.discovery.models import DiscoveryCandidate
from scripts.pettripfinder.discovery.normalize import normalize_business_name

DEFAULT_SEED_CSV_PATH = "launch_packages/pettripfinder/seed_businesses.csv"
_HOTEL_CATEGORY_SLUG = "pet-friendly-hotels"


@dataclass(frozen=True)
class KnownHotel:
    name: str
    address_line: str
    city: str
    state: str
    postal_code: str


def load_known_hotels(csv_path: str = DEFAULT_SEED_CSV_PATH) -> Tuple[KnownHotel, ...]:
    """Read-only. Never writes. Never called during a live discovery run's
    candidate-producing path -- only for the post-hoc recall comparison."""
    path = Path(csv_path)
    if not path.exists():
        return ()
    hotels = []
    with path.open(encoding="utf-8", newline="") as f:
        for row in csv.DictReader(f):
            if row.get("category") == _HOTEL_CATEGORY_SLUG:
                hotels.append(KnownHotel(
                    name=row.get("name", ""), address_line=row.get("address", ""),
                    city=row.get("city", ""), state=row.get("state", ""),
                    postal_code=row.get("postal_code", ""),
                ))
    return tuple(hotels)


@dataclass(frozen=True)
class RecallResult:
    found: Tuple[KnownHotel, ...]
    missed: Tuple[KnownHotel, ...]
    discovery_only_count: int
    discovery_only_candidate_ids: Tuple[str, ...]


def _known_matches_candidate(known: KnownHotel, candidate: DiscoveryCandidate) -> bool:
    kn = normalize_business_name(known.name)
    cn = candidate.normalized_name
    if not kn or not cn:
        return False
    name_match = kn == cn or kn in cn or cn in kn
    if not name_match:
        return False
    if known.postal_code and candidate.postal_code:
        return known.postal_code == candidate.postal_code
    if known.city and candidate.city:
        return normalize_business_name(known.city) == normalize_business_name(candidate.city)
    return name_match   # name-only match when neither side has city/postal to corroborate


def compute_recall(
    known_hotels: Sequence[KnownHotel], candidates: Sequence[DiscoveryCandidate],
) -> RecallResult:
    found = []
    missed = []
    matched_candidate_ids = set()
    for known in known_hotels:
        match = next((c for c in candidates if _known_matches_candidate(known, c)), None)
        if match is not None:
            found.append(known)
            matched_candidate_ids.add(match.candidate_id)
        else:
            missed.append(known)
    discovery_only = [c for c in candidates if c.candidate_id not in matched_candidate_ids]
    return RecallResult(
        found=tuple(found), missed=tuple(missed),
        discovery_only_count=len(discovery_only),
        discovery_only_candidate_ids=tuple(sorted(c.candidate_id for c in discovery_only)),
    )


def recall_summary_counts(result: RecallResult) -> Tuple[Tuple[str, int], ...]:
    return (
        ("known_found", len(result.found)),
        ("known_missed", len(result.missed)),
        ("discovery_only", result.discovery_only_count),
    )
