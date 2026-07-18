"""AES-DATA-004A discovery -- conservative deterministic deduplication and
entity resolution (Task 9).

Preconditions: callers pass records already run through
``normalize.normalize_records`` (``normalized_name``/phone/state/postal/url
populated). Merge decisions are pairwise and symmetric; the input record
order never affects the output (records are canonically sorted before any
comparison, per the required "deterministic output regardless of source
ordering" test).

Strong merge signals (any ONE is sufficient): same provider ID from the
same provider; same normalized full address; same phone plus a compatible
name; same official domain plus a compatible name and a matching
location/address; close coordinates plus a compatible name and an
overlapping address. Weak signals (chain name alone, domain alone, city
alone, coordinate proximity alone, category overlap alone) never merge by
themselves -- every strong signal above pairs a name/identity match with an
independent corroborating signal, on purpose (doctrine: never merge
locations solely because they share a brand).

Safety override: the two "softer" signals (phone+name, domain+name+
location) are refused -- and a conflict flag recorded instead -- when both
records carry a fully populated, non-overlapping, unequal address. Same-
provider-ID and same-full-address are never overridden this way (the first
is a literal provider-asserted identity; the second already *is* the
address match).
"""

from __future__ import annotations

import hashlib
import math
from typing import Dict, List, Optional, Sequence, Tuple

from scripts.pettripfinder.discovery import constants as C
from scripts.pettripfinder.discovery.models import DiscoveryCandidate, DiscoveryRecord
from scripts.pettripfinder.discovery.normalize import (
    normalize_business_name,
    registrable_domain,
)
from scripts.pettripfinder.discovery.website_state import classify_candidate_website

_EARTH_RADIUS_METERS = 6_371_000.0


def haversine_meters(lat1: float, lng1: float, lat2: float, lng2: float) -> float:
    phi1, phi2 = math.radians(lat1), math.radians(lat2)
    dphi = math.radians(lat2 - lat1)
    dlambda = math.radians(lng2 - lng1)
    a = (math.sin(dphi / 2) ** 2
         + math.cos(phi1) * math.cos(phi2) * math.sin(dlambda / 2) ** 2)
    return 2 * _EARTH_RADIUS_METERS * math.asin(min(1.0, math.sqrt(a)))


def _address_key(r: DiscoveryRecord) -> Optional[Tuple[str, str, str]]:
    line = normalize_business_name(r.address_line)
    city = normalize_business_name(r.city)
    state = (r.state or "").strip().upper()
    if line and city and state:
        return (line, city, state)
    return None


def _domain_key(r: DiscoveryRecord) -> str:
    if not r.website_url:
        return ""
    domain = registrable_domain(r.website_url)
    return "" if domain in C.NON_OFFICIAL_DOMAINS else domain


def _coords(r: DiscoveryRecord) -> Optional[Tuple[float, float]]:
    if r.latitude is None or r.longitude is None:
        return None
    return (r.latitude, r.longitude)


def _coords_close(a: DiscoveryRecord, b: DiscoveryRecord) -> bool:
    ca, cb = _coords(a), _coords(b)
    if ca is None or cb is None:
        return False
    return haversine_meters(ca[0], ca[1], cb[0], cb[1]) <= C.DEDUP_COORD_PROXIMITY_METERS


def _names_compatible(a: DiscoveryRecord, b: DiscoveryRecord) -> bool:
    na, nb = a.normalized_name, b.normalized_name
    return bool(na) and na == nb


def _address_overlaps(a: DiscoveryRecord, b: DiscoveryRecord) -> bool:
    """Weaker-than-equal address corroboration -- tolerates cross-provider
    formatting differences (e.g. Google's full formatted address vs. OSM's
    bare housenumber+street with no city/state tags)."""
    if a.city and b.city and normalize_business_name(a.city) == normalize_business_name(b.city):
        return True
    if a.postal_code and b.postal_code and a.postal_code == b.postal_code:
        return True
    sa, sb = normalize_business_name(a.address_line), normalize_business_name(b.address_line)
    if sa and sb and (sa in sb or sb in sa):
        return True
    return False


def _location_matches(a: DiscoveryRecord, b: DiscoveryRecord) -> bool:
    addr_a, addr_b = _address_key(a), _address_key(b)
    if addr_a is not None and addr_a == addr_b:
        return True
    return _coords_close(a, b) or _address_overlaps(a, b)


def _addresses_conflict(a: DiscoveryRecord, b: DiscoveryRecord) -> bool:
    """True only when BOTH records have a fully populated address that is
    definitely different (not merely un-comparable)."""
    addr_a, addr_b = _address_key(a), _address_key(b)
    if addr_a is None or addr_b is None:
        return False
    return addr_a != addr_b and not _address_overlaps(a, b)


def merge_reason_for_pair(a: DiscoveryRecord, b: DiscoveryRecord) -> Tuple[Optional[str], bool]:
    """Returns ``(reason_or_None, conflict_flagged)``."""
    if a.provider == b.provider and a.provider_record_id and a.provider_record_id == b.provider_record_id:
        return (C.MERGE_REASON_SAME_PROVIDER_ID, False)

    addr_a, addr_b = _address_key(a), _address_key(b)
    if addr_a is not None and addr_a == addr_b:
        return (C.MERGE_REASON_SAME_ADDRESS, False)

    if a.phone and a.phone == b.phone and _names_compatible(a, b):
        if _addresses_conflict(a, b):
            return (None, True)
        return (C.MERGE_REASON_PHONE_PLUS_NAME, False)

    dom_a, dom_b = _domain_key(a), _domain_key(b)
    if dom_a and dom_a == dom_b and _names_compatible(a, b) and _location_matches(a, b):
        if _addresses_conflict(a, b):
            return (None, True)
        return (C.MERGE_REASON_DOMAIN_PLUS_NAME_PLUS_ADDRESS, False)

    if _coords_close(a, b) and _names_compatible(a, b) and _address_overlaps(a, b):
        return (C.MERGE_REASON_COORDS_PLUS_NAME_PLUS_ADDRESS, False)

    return (None, False)


# --------------------------------------------------------------------------- #
# Union-find over a canonically sorted record list.
# --------------------------------------------------------------------------- #

def _sort_key(r: DiscoveryRecord) -> Tuple[str, str, str]:
    return (r.provider, r.provider_record_id, r.source_query_id)


class _UnionFind:
    def __init__(self, n: int):
        self.parent = list(range(n))

    def find(self, x: int) -> int:
        while self.parent[x] != x:
            self.parent[x] = self.parent[self.parent[x]]
            x = self.parent[x]
        return x

    def union(self, x: int, y: int) -> None:
        rx, ry = self.find(x), self.find(y)
        if rx != ry:
            self.parent[max(rx, ry)] = min(rx, ry)


def _candidate_id(records: Sequence[DiscoveryRecord]) -> str:
    keys = sorted("%s:%s" % (r.provider, r.provider_record_id) for r in records)
    digest = hashlib.sha256("|".join(keys).encode("utf-8")).hexdigest()
    return "dc_" + digest[:16]


def _best_record(records: Sequence[DiscoveryRecord]) -> DiscoveryRecord:
    def score(r: DiscoveryRecord) -> Tuple[int, int]:
        provider_rank = (C.PROVIDER_PRIORITY.index(r.provider)
                         if r.provider in C.PROVIDER_PRIORITY else len(C.PROVIDER_PRIORITY))
        completeness = sum(1 for v in (r.name, r.address_line, r.city, r.state,
                                       r.postal_code, r.phone, r.website_url) if v)
        return (provider_rank, -completeness)
    return sorted(records, key=lambda r: (score(r), _sort_key(r)))[0]


def deduplicate(records: Sequence[DiscoveryRecord], *, market_id: str = "") -> Tuple[DiscoveryCandidate, ...]:
    ordered = sorted(records, key=_sort_key)
    n = len(ordered)
    uf = _UnionFind(n)
    pair_reasons: Dict[Tuple[int, int], str] = {}
    # Indices that had a strong-signal-but-conflicting-address pairing with
    # some OTHER record. Such pairs are never unioned (mission's required
    # "conflicting addresses remain separate" test), but the tension must
    # still surface ("represent unresolved conflicts") -- both resulting
    # (separate) candidates get flagged NEEDS_REVIEW rather than silently
    # looking clean.
    conflicted_indices: set = set()

    for i in range(n):
        for j in range(i + 1, n):
            reason, conflict = merge_reason_for_pair(ordered[i], ordered[j])
            if reason is not None:
                uf.union(i, j)
                pair_reasons[(i, j)] = reason
            if conflict:
                conflicted_indices.add(i)
                conflicted_indices.add(j)

    groups: Dict[int, List[int]] = {}
    for idx in range(n):
        groups.setdefault(uf.find(idx), []).append(idx)

    candidates = []
    for indices in groups.values():
        member_records = [ordered[i] for i in indices]
        reasons = sorted({
            pair_reasons[(i, j)]
            for i in indices for j in indices if i < j and (i, j) in pair_reasons
        })
        has_conflict = any(idx in conflicted_indices for idx in indices)
        best = _best_record(member_records)
        website_state, website_url = classify_candidate_website(tuple(member_records))
        provider_ids = tuple(sorted({(r.provider, r.provider_record_id) for r in member_records}))
        category_candidates = tuple(sorted({r.canonical_category for r in member_records}))
        conflict_flags = (C.CONFLICT_ADDRESS_MISMATCH,) if has_conflict else ()
        if conflict_flags:
            review_state = C.REVIEW_STATE_NEEDS_REVIEW
        elif len(member_records) == 1:
            review_state = C.REVIEW_STATE_SINGLE_SOURCE
        else:
            review_state = C.REVIEW_STATE_AUTO_MERGED

        candidates.append(DiscoveryCandidate(
            candidate_id=_candidate_id(member_records),
            source_records=tuple(sorted(member_records, key=_sort_key)),
            name=best.name, normalized_name=best.normalized_name,
            provider_ids=provider_ids, website_url=website_url,
            website_state=website_state, latitude=best.latitude,
            longitude=best.longitude, address_line=best.address_line,
            city=best.city, state=best.state, postal_code=best.postal_code,
            category_candidates=category_candidates,
            merge_reason=",".join(reasons), conflict_flags=conflict_flags,
            review_state=review_state,
            market_id=market_id or best.provenance_dict().get("market_id", ""),
        ))

    return tuple(sorted(candidates, key=lambda c: c.candidate_id))
