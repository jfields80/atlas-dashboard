"""AES-DATA-004B Phase 10 -- deterministic import-planning artifact.

Generates a reviewable ``import_plan.json`` for the next (official-site
verification) phase. Every entry is derived only from fields already on
``DiscoveryCandidate`` -- no pet policy, no unverified pet-friendly status,
no invented importer-category facts, no provider ratings/reviews/hours, no
high-risk claims. This artifact is not itself a production seed file.
"""

from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Sequence, Tuple

from scripts.pettripfinder.discovery import constants as C
from scripts.pettripfinder.discovery.models import DiscoveryCandidate


@dataclass(frozen=True)
class ImportPlanEntry:
    candidate_id: str
    name: str
    address_line: str
    city: str
    state: str
    postal_code: str
    latitude: object
    longitude: object
    provider_ids: Tuple[Tuple[str, str], ...]
    provider_categories: Tuple[str, ...]
    website_state: str
    website_url: str
    warnings: Tuple[str, ...]
    merge_reason: str
    conflict_flags: Tuple[str, ...]
    source_query_ids: Tuple[str, ...]
    recommended_next_action: str


def compute_next_action(candidate: DiscoveryCandidate) -> str:
    """Deterministic, priority-ordered. Exclusions first (don't waste
    review effort), then identity conflicts (must be resolved before
    anything else can be trusted), then website-specific states, then the
    happy path."""
    eligibility_states = {
        r.eligibility_state for r in candidate.source_records if r.eligibility_state
    }
    if C.ELIGIBILITY_PERMANENTLY_CLOSED in eligibility_states:
        return C.NEXT_ACTION_EXCLUDE_CLOSED
    if (C.ELIGIBILITY_OUT_OF_MARKET_BOUNDS in eligibility_states
            and C.ELIGIBILITY_ELIGIBLE not in eligibility_states):
        return C.NEXT_ACTION_REVIEW_OUT_OF_SCOPE
    if candidate.review_state == C.REVIEW_STATE_NEEDS_REVIEW:
        return C.NEXT_ACTION_REVIEW_IDENTITY
    if candidate.website_state == C.WEBSITE_STATE_CONFLICTING:
        return C.NEXT_ACTION_REVIEW_CONFLICTING_WEBSITE
    if candidate.website_state in (C.WEBSITE_STATE_AMBIGUOUS, C.WEBSITE_STATE_PROVIDER_URL_ONLY):
        return C.NEXT_ACTION_RESOLVE_OFFICIAL_WEBSITE
    if candidate.website_state == C.WEBSITE_STATE_MISSING:
        return C.NEXT_ACTION_MISSING_WEBSITE
    if candidate.website_state == C.WEBSITE_STATE_OFFICIAL_PRESENT:
        return C.NEXT_ACTION_READY_FOR_OFFICIAL_SITE_IMPORT
    return C.NEXT_ACTION_RESOLVE_OFFICIAL_WEBSITE


def build_import_plan(candidates: Sequence[DiscoveryCandidate]) -> Tuple[ImportPlanEntry, ...]:
    entries = []
    for c in candidates:
        source_query_ids = tuple(sorted({r.source_query_id for r in c.source_records if r.source_query_id}))
        provider_categories = tuple(sorted({
            pc for r in c.source_records for pc in r.provider_categories
        }))
        entries.append(ImportPlanEntry(
            candidate_id=c.candidate_id, name=c.name, address_line=c.address_line,
            city=c.city, state=c.state, postal_code=c.postal_code,
            latitude=c.latitude, longitude=c.longitude,
            provider_ids=c.provider_ids, provider_categories=provider_categories,
            website_state=c.website_state, website_url=c.website_url,
            warnings=c.warnings, merge_reason=c.merge_reason,
            conflict_flags=c.conflict_flags, source_query_ids=source_query_ids,
            recommended_next_action=compute_next_action(c),
        ))
    return tuple(sorted(entries, key=lambda e: e.candidate_id))


def next_action_counts(entries: Sequence[ImportPlanEntry]) -> Tuple[Tuple[str, int], ...]:
    counts = {}
    for e in entries:
        counts[e.recommended_next_action] = counts.get(e.recommended_next_action, 0) + 1
    return tuple(sorted(counts.items()))


def dumps_import_plan(entries: Sequence[ImportPlanEntry]) -> str:
    data = [
        {
            "candidate_id": e.candidate_id, "name": e.name, "address_line": e.address_line,
            "city": e.city, "state": e.state, "postal_code": e.postal_code,
            "latitude": e.latitude, "longitude": e.longitude,
            "provider_ids": dict(e.provider_ids),
            "provider_categories": list(e.provider_categories),
            "website_state": e.website_state, "website_url": e.website_url,
            "warnings": list(e.warnings), "merge_reason": e.merge_reason,
            "conflict_flags": list(e.conflict_flags),
            "source_query_ids": list(e.source_query_ids),
            "recommended_next_action": e.recommended_next_action,
        }
        for e in entries
    ]
    return json.dumps(data, sort_keys=True, indent=2)
