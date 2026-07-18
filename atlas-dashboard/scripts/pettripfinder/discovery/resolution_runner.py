"""AES-DATA-004C -- orchestration for lodging scope cleanup and
official-website resolution. Ties together Tasks 1/3/5/6/7/8/9/10 into one
deterministic static pass, plus an optional live-fetch upgrade pass
(Tasks 14/15/16) that is never invoked implicitly.
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from pathlib import Path
from typing import Dict, Optional, Sequence, Tuple

from scripts.pettripfinder.discovery import constants as C
from scripts.pettripfinder.discovery.identity_resolution import resolve_identity_conflicts
from scripts.pettripfinder.discovery.lodging_scope import classify_lodging_scope
from scripts.pettripfinder.discovery.market_config import MarketConfig
from scripts.pettripfinder.discovery.models import DiscoveryCandidate, WebsiteResolution
from scripts.pettripfinder.discovery.resolution_eligibility import (
    categorize_missing_website,
    compute_resolution_outcome,
)
from scripts.pettripfinder.discovery.resolution_fetch_plan import FetchPlan, build_fetch_plan
from scripts.pettripfinder.discovery.website_fetcher import DomainPacer, ResolutionCache, fetch_for_identity
from scripts.pettripfinder.discovery.website_resolution import (
    classify_candidate_urls_statically,
    validate_fetched_identity,
)


@dataclass(frozen=True)
class ResolvedCandidate:
    candidate_id: str
    name: str
    category: str
    city: str
    state: str
    scope: str
    identity_outcome: str
    website_resolutions: Tuple[WebsiteResolution, ...]
    missing_website_action: str
    resolution_outcome: str
    resolved_url: str
    is_confirmed: bool


def combine_lodging_candidate_pools(
    hotel_candidates: Sequence[DiscoveryCandidate], motel_candidates: Sequence[DiscoveryCandidate],
) -> Tuple[DiscoveryCandidate, ...]:
    """A real business can be discovered independently under both the
    'hotel' and 'motel' discovery categories (e.g. Google's fuzzy category
    matching returning the same Google Place ID for both "hotel" and
    "motel" text queries) -- since ``candidate_id`` is derived purely from
    the underlying provider IDs, this produces the SAME candidate_id in
    both the hotel and motel candidate pools (found live during Wave 1:
    "Travel lodge motel", Google Place ID ChIJ-yplDOyEOIgRsH4TCI68plk).
    Combining the two pools without deduplication double-counts that
    candidate everywhere downstream (reports, batches). This merges
    same-ID candidates into one, unioning ``category_candidates`` and
    ``source_records`` -- never inventing a new merge heuristic, since
    same candidate_id already IS the existing strong-identity signal."""
    by_id: Dict[str, DiscoveryCandidate] = {}
    for c in list(hotel_candidates) + list(motel_candidates):
        existing = by_id.get(c.candidate_id)
        if existing is None:
            by_id[c.candidate_id] = c
            continue
        merged_categories = tuple(sorted(set(existing.category_candidates) | set(c.category_candidates)))
        merged_records = tuple(sorted(
            set(existing.source_records) | set(c.source_records),
            key=lambda r: (r.provider, r.provider_record_id, r.source_query_id)))
        by_id[c.candidate_id] = replace(
            existing, category_candidates=merged_categories, source_records=merged_records)
    return tuple(sorted(by_id.values(), key=lambda c: c.candidate_id))


def _candidate_category(candidate: DiscoveryCandidate) -> str:
    if C.CATEGORY_MOTEL in candidate.category_candidates:
        return C.CATEGORY_MOTEL
    if C.CATEGORY_HOTEL in candidate.category_candidates:
        return C.CATEGORY_HOTEL
    return candidate.category_candidates[0] if candidate.category_candidates else ""


def resolve_static(
    candidates: Sequence[DiscoveryCandidate], market: MarketConfig,
) -> Tuple[ResolvedCandidate, ...]:
    """Task 1/3/5/9/10 combined, no network. Deterministic."""
    identity_by_candidate: Dict[str, str] = {}
    for group, outcome in resolve_identity_conflicts(candidates):
        for c in group:
            identity_by_candidate[c.candidate_id] = outcome

    resolved = []
    for c in candidates:
        scope = classify_lodging_scope(c, market)
        identity_outcome = identity_by_candidate.get(c.candidate_id, "")
        website_resolutions = classify_candidate_urls_statically(c)
        missing_action = ""
        if all(r.resolution_state == C.WEBSITE_RES_MISSING for r in website_resolutions):
            missing_action = categorize_missing_website(c, scope)
        outcome = compute_resolution_outcome(
            c, scope=scope, identity_outcome=identity_outcome,
            website_resolutions=website_resolutions)
        resolved_url, is_confirmed = _pick_resolved_url(website_resolutions)
        resolved.append(ResolvedCandidate(
            candidate_id=c.candidate_id, name=c.name, category=_candidate_category(c),
            city=c.city, state=c.state, scope=scope, identity_outcome=identity_outcome,
            website_resolutions=website_resolutions, missing_website_action=missing_action,
            resolution_outcome=outcome, resolved_url=resolved_url, is_confirmed=is_confirmed,
        ))
    return tuple(resolved)


def _pick_resolved_url(resolutions: Tuple[WebsiteResolution, ...]) -> Tuple[str, bool]:
    for r in resolutions:
        if r.resolution_state == C.WEBSITE_RES_PROPERTY_URL_CONFIRMED:
            return (r.normalized_url, True)
    for r in resolutions:
        if r.resolution_state == C.WEBSITE_RES_PROPERTY_URL_PROBABLE:
            return (r.normalized_url, False)
    return ("", False)


def build_identity_review_ids(candidates: Sequence[DiscoveryCandidate]) -> Tuple[str, ...]:
    ids = set()
    for group, _outcome in resolve_identity_conflicts(candidates):
        ids.update(c.candidate_id for c in group)
    return tuple(sorted(ids))


def plan_fetch(
    candidates: Sequence[DiscoveryCandidate], *, max_total: int, max_per_candidate: int,
    max_per_domain: int,
) -> FetchPlan:
    static_map = {c.candidate_id: classify_candidate_urls_statically(c) for c in candidates}
    identity_ids = build_identity_review_ids(candidates)
    return build_fetch_plan(candidates, static_map, identity_ids, max_total=max_total,
                            max_per_candidate=max_per_candidate, max_per_domain=max_per_domain)


@dataclass
class FetchRunStats:
    http_requests: int = 0
    cache_hits: int = 0
    redirects: int = 0
    timeouts_errors: int = 0
    blocked: int = 0
    confirmed: int = 0
    probable: int = 0
    chain_homepage: int = 0
    third_party: int = 0
    social: int = 0
    unresolved: int = 0


def resolve_with_fetch(
    candidates: Sequence[DiscoveryCandidate], market: MarketConfig, *,
    fetch_plan: FetchPlan, fetcher, cache: ResolutionCache, pacer: Optional[DomainPacer],
    observed_at: str, cache_only: bool = False,
) -> Tuple[Tuple[ResolvedCandidate, ...], FetchRunStats]:
    """Task 15/16: applies the (already-approved) fetch plan on top of the
    static pass. Only touches candidates present in ``fetch_plan.items`` --
    every other candidate's static resolution is carried through unchanged."""
    candidates_by_id = {c.candidate_id: c for c in candidates}
    static_results = {r.candidate_id: r for r in resolve_static(candidates, market)}
    stats = FetchRunStats()

    fetched_by_candidate: Dict[str, list] = {}
    for item in fetch_plan.items:
        fetch_result = fetch_for_identity(
            item.url, fetcher=fetcher, cache=cache, pacer=pacer,
            registrable_domain_value=item.registrable_domain, retrieved_at=observed_at,
            cache_only=cache_only,
        )
        # Distinguish a genuine live network attempt from a --cache-only
        # miss (no cache entry, no fetcher call was ever made -- bug found
        # and fixed live: the miss was being miscounted as an HTTP request,
        # which would have made a true zero-network cache-only proof look
        # like it made real calls).
        cache_only_miss = fetch_result.get("reason") == "cache_only_no_entry"
        if fetch_result["from_cache"]:
            stats.cache_hits += 1
        elif not cache_only_miss:
            stats.http_requests += 1

        if cache_only_miss:
            # No data either way -- never touched, never fetched. Leave
            # this candidate exactly as the static pass classified it
            # rather than downgrading it to FETCH_BLOCKED (bug found and
            # fixed live: planning the full ceiling under --cache-only so
            # the 10 REAL cached results replay correctly was incorrectly
            # also making the other 30 never-fetched items look like
            # failed fetch attempts, wrongly demoting otherwise-fine
            # PROPERTY_OFFICIAL_URL_PROBABLE candidates to REVIEW_WEBSITE).
            continue

        if fetch_result.get("final_url") and fetch_result["final_url"] != item.url:
            stats.redirects += 1

        candidate = candidates_by_id[item.candidate_id]
        snap = fetch_result["snapshot"]
        state, warnings = validate_fetched_identity(
            candidate, page_title=snap.title, structured_name=snap.structured_name,
            structured_address=snap.structured_address, fetch_ok=fetch_result["ok"],
            fetch_reason=fetch_result.get("reason", ""),
            registrable_domain_value=item.registrable_domain,
        )
        if state == C.WEBSITE_RES_FETCH_BLOCKED:
            stats.blocked += 1
            if fetch_result.get("reason") in ("fetch_timeout",):
                stats.timeouts_errors += 1
        elif state == C.WEBSITE_RES_PROPERTY_URL_CONFIRMED:
            stats.confirmed += 1
        elif state == C.WEBSITE_RES_PROPERTY_URL_PROBABLE:
            stats.probable += 1
        elif state == C.WEBSITE_RES_CHAIN_HOMEPAGE_ONLY:
            stats.chain_homepage += 1
        else:
            stats.unresolved += 1

        resolution = WebsiteResolution(
            candidate_id=item.candidate_id, source_provider=C.PROVIDER_GOOGLE_PLACES,
            original_url=item.url, normalized_url=item.url, registrable_domain=item.registrable_domain,
            redirect_target=fetch_result.get("final_url", ""), http_status=fetch_result.get("http_status", 0),
            page_title=snap.title, canonical_url=snap.canonical_url,
            structured_identity_name=snap.structured_name, structured_identity_address=snap.structured_address,
            resolution_state=state, warnings=warnings, retrieved_at=observed_at,
            cache_reference=fetch_result.get("cache_reference", ""),
        )
        fetched_by_candidate.setdefault(item.candidate_id, []).append(resolution)

    final = []
    for cid, base in static_results.items():
        if cid not in fetched_by_candidate:
            final.append(base)
            continue
        website_resolutions = tuple(fetched_by_candidate[cid])
        identity_outcome = base.identity_outcome
        candidate = candidates_by_id[cid]
        scope = base.scope
        outcome = compute_resolution_outcome(
            candidate, scope=scope, identity_outcome=identity_outcome,
            website_resolutions=website_resolutions)
        resolved_url, is_confirmed = _pick_resolved_url(website_resolutions)
        final.append(replace(
            base, website_resolutions=website_resolutions, resolution_outcome=outcome,
            resolved_url=resolved_url, is_confirmed=is_confirmed,
        ))
    return tuple(sorted(final, key=lambda r: r.candidate_id)), stats
