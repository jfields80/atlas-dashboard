"""AES-DATA-004A discovery -- immutable domain models (Task 1).

Frozen dataclasses only, mirroring the ``scripts.pettripfinder.importer``
frozen-model discipline: pure contracts, no I/O, no network, no validation
logic beyond type shape (validation lives in ``normalize``/``deduplicate``).
Dict-like data (provenance, per-provider counters) is carried as an ordered
tuple-of-pairs rather than a ``dict`` so every model stays hashable and
serializes deterministically without a key-sort step.

Discovery models never assert a publishable service capability (pet
policies, emergency service, 24-hour operation, walk-in rules, and so on --
doctrine #1). They describe *candidate entities* a provider returned, not
verified facts.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple


# --------------------------------------------------------------------------- #
# One provider's parsed record for one place (Task 1).
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class DiscoveryRecord:
    provider: str
    provider_record_id: str
    canonical_category: str
    provider_categories: Tuple[str, ...] = ()
    name: str = ""
    normalized_name: str = ""
    address_line: str = ""
    city: str = ""
    state: str = ""
    postal_code: str = ""
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    phone: str = ""
    website_url: str = ""
    provider_place_url: str = ""
    business_status: str = ""
    observed_at: str = ""                      # explicit date, never wall-clock
    source_query_id: str = ""
    raw_snapshot_hash: str = ""                 # sha256 of the cached raw payload
    provenance: Tuple[Tuple[str, str], ...] = ()
    warnings: Tuple[str, ...] = ()
    eligibility_state: str = ""

    def provenance_dict(self) -> dict:
        return dict(self.provenance)


# --------------------------------------------------------------------------- #
# One planned/executed provider query (Task 1/6).
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class DiscoverySourceQuery:
    query_id: str
    provider: str
    canonical_category: str
    query_text: str = ""                        # Google textQuery / OSM tag expr
    market_id: str = ""
    cell_id: str = ""
    center_lat: Optional[float] = None
    center_lng: Optional[float] = None
    radius_meters: Optional[int] = None
    max_pages: int = 1
    expected_market: str = ""
    enabled: bool = True


# --------------------------------------------------------------------------- #
# A deduplicated real-world location (Task 1/9).
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class DiscoveryCandidate:
    candidate_id: str                            # stable deterministic id
    source_records: Tuple[DiscoveryRecord, ...]
    name: str = ""
    normalized_name: str = ""
    provider_ids: Tuple[Tuple[str, str], ...] = ()   # (provider, provider_record_id)
    website_url: str = ""
    website_state: str = ""
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    address_line: str = ""
    city: str = ""
    state: str = ""
    postal_code: str = ""
    category_candidates: Tuple[str, ...] = ()
    merge_reason: str = ""                       # "" when single-source
    conflict_flags: Tuple[str, ...] = ()
    review_state: str = ""
    market_id: str = ""
    warnings: Tuple[str, ...] = ()                # e.g. "location_page_unverified"

    def provider_id_dict(self) -> dict:
        return dict(self.provider_ids)


# --------------------------------------------------------------------------- #
# Deterministic coverage/report accounting (Task 1/11).
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class CoverageSummary:
    market_id: str
    observed_at: str
    providers_enabled: Tuple[str, ...] = ()
    credentials_available: Tuple[Tuple[str, bool], ...] = ()
    records_by_provider: Tuple[Tuple[str, int], ...] = ()
    unique_candidates: int = 0
    overlap_by_provider_pair: Tuple[Tuple[str, int], ...] = ()
    provider_only_candidates: Tuple[Tuple[str, int], ...] = ()
    candidates_with_website: int = 0
    candidates_without_website: int = 0
    duplicates_merged: int = 0
    conflicts_requiring_review: int = 0
    counts_by_category: Tuple[Tuple[str, int], ...] = ()
    counts_by_municipality: Tuple[Tuple[str, int], ...] = ()
    query_completion: Tuple[Tuple[str, str], ...] = ()   # query_id -> state
    provider_errors: Tuple[Tuple[str, str], ...] = ()    # query_id -> error slug
    request_counts: Tuple[Tuple[str, int], ...] = ()     # provider -> count
    page_counts: Tuple[Tuple[str, int], ...] = ()        # provider -> count
    cache_hits: Tuple[Tuple[str, int], ...] = ()         # provider -> count
    estimated_billable_google_calls: int = 0
    # AES-DATA-004B (Phase 3/11 additions). Default-empty so every 004A
    # caller/test that doesn't pass these is unaffected.
    query_yield_table: Tuple["QueryYieldRow", ...] = ()
    saturated_query_ids: Tuple[str, ...] = ()
    low_yield_query_ids: Tuple[str, ...] = ()
    zero_result_query_ids: Tuple[str, ...] = ()
    known_inventory_recall: Tuple[Tuple[str, int], ...] = ()
    import_plan_next_action_counts: Tuple[Tuple[str, int], ...] = ()


# --------------------------------------------------------------------------- #
# Per-query yield/saturation reporting (AES-DATA-004B Phase 3). Reuses the
# real ``deduplicate()``/``normalize_records()`` functions to compute
# cumulative candidate growth -- never a parallel, approximate merge
# heuristic invented just for reporting.
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class QueryYieldRow:
    query_id: str
    provider: str
    category: str
    cell_id: str
    state: str
    raw_records_returned: int
    new_unique_provider_records: int
    already_found_by_earlier_query: int
    candidates_added: int
    candidates_merged_into_existing: int
    cumulative_unique_candidates: int
    zero_result: bool
    saturation_status: str
    cache_or_live: str
