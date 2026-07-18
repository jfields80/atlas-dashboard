"""AES-DATA-004A discovery -- deterministic JSON serialization (Task 1/5).

Every ``to_dict`` sorts nothing itself (dict key order is insertion order,
already fixed by field order below); ``dumps_*`` applies ``sort_keys=True``
at write time, matching the importer's persistence convention.
"""

from __future__ import annotations

import json
from dataclasses import asdict

from scripts.pettripfinder.discovery.models import (
    CoverageSummary,
    DiscoveryCandidate,
    DiscoveryRecord,
    DiscoverySourceQuery,
    QueryYieldRow,
)


def record_to_dict(r: DiscoveryRecord) -> dict:
    return asdict(r)


def record_from_dict(d: dict) -> DiscoveryRecord:
    d = dict(d)
    d["provider_categories"] = tuple(d.get("provider_categories", ()))
    d["provenance"] = tuple(tuple(p) for p in d.get("provenance", ()))
    d["warnings"] = tuple(d.get("warnings", ()))
    return DiscoveryRecord(**d)


def query_to_dict(q: DiscoverySourceQuery) -> dict:
    return asdict(q)


def query_from_dict(d: dict) -> DiscoverySourceQuery:
    return DiscoverySourceQuery(**d)


def candidate_to_dict(c: DiscoveryCandidate) -> dict:
    d = asdict(c)
    d["source_records"] = [record_to_dict(r) for r in c.source_records]
    return d


def candidate_from_dict(d: dict) -> DiscoveryCandidate:
    d = dict(d)
    d["source_records"] = tuple(record_from_dict(r) for r in d.get("source_records", ()))
    d["provider_ids"] = tuple(tuple(p) for p in d.get("provider_ids", ()))
    d["category_candidates"] = tuple(d.get("category_candidates", ()))
    d["conflict_flags"] = tuple(d.get("conflict_flags", ()))
    d["warnings"] = tuple(d.get("warnings", ()))
    return DiscoveryCandidate(**d)


def coverage_to_dict(s: CoverageSummary) -> dict:
    return asdict(s)


_COVERAGE_PAIR_FIELDS = (
    "credentials_available", "records_by_provider", "overlap_by_provider_pair",
    "provider_only_candidates", "counts_by_category", "counts_by_municipality",
    "query_completion", "provider_errors", "request_counts", "page_counts",
    "cache_hits", "known_inventory_recall", "import_plan_next_action_counts",
)
_COVERAGE_ID_LIST_FIELDS = ("saturated_query_ids", "low_yield_query_ids", "zero_result_query_ids")
_COVERAGE_ANNOTATION_ONLY_KEYS = ("disclosure", "pet_friendliness_warning", "market_completeness_warning")


def coverage_from_dict(d: dict) -> CoverageSummary:
    """Inverse of ``render_coverage_json`` -- that function renders every
    tuple-of-pairs field as a JSON *object* (``dict(...)``) for readability,
    not as an array of ``[key, value]`` pairs, so reconstruction must read
    each such field back via ``.items()``, not by iterating/tuple-ing a
    JSON array (there is no array to iterate)."""
    d = dict(d)
    for key in _COVERAGE_ANNOTATION_ONLY_KEYS:
        d.pop(key, None)
    d["providers_enabled"] = tuple(d.get("providers_enabled", ()))
    for key in _COVERAGE_PAIR_FIELDS:
        d[key] = tuple(sorted(d.get(key, {}).items()))
    for key in _COVERAGE_ID_LIST_FIELDS:
        d[key] = tuple(d.get(key, ()))
    d["query_yield_table"] = tuple(
        QueryYieldRow(**row) for row in d.get("query_yield_table", ())
    )
    return CoverageSummary(**d)


def dumps_candidates(candidates) -> str:
    return json.dumps([candidate_to_dict(c) for c in candidates], sort_keys=True, indent=2)


def loads_candidates(text: str):
    return tuple(candidate_from_dict(d) for d in json.loads(text))
