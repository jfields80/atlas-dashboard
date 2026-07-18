"""AES-DATA-004C Task 6 -- deterministic website-resolution fetch plan.

Priority order: (1) identity-review candidates, (2) candidates with
statically-conflicting URLs, (3) probable/chain-homepage URLs on candidates
that would otherwise be import-ready, (4) [not populated in this phase --
see disclosure below]. Never includes a blocked third-party/social URL,
never invents a URL, never performs search-engine scraping.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Sequence, Tuple

from scripts.pettripfinder.discovery import constants as C
from scripts.pettripfinder.discovery.models import DiscoveryCandidate, WebsiteResolution
from scripts.pettripfinder.discovery.website_resolution import static_conflicting_urls

_FETCHABLE_STATES = frozenset({C.WEBSITE_RES_PROPERTY_URL_PROBABLE, C.WEBSITE_RES_CHAIN_HOMEPAGE_ONLY})

PRIORITY_IDENTITY_REVIEW = 1
PRIORITY_CONFLICTING_WEBSITE = 2
PRIORITY_PROBABLE_OR_CHAIN_HOMEPAGE = 3
PRIORITY_MISSING_WITH_DOMAIN_LEAD = 4


@dataclass(frozen=True)
class FetchPlanItem:
    candidate_id: str
    url: str
    registrable_domain: str
    priority: int
    reason: str


@dataclass(frozen=True)
class FetchPlan:
    items: Tuple[FetchPlanItem, ...]
    total_candidates: int
    static_only_count: int
    fetch_required_count: int
    blocked_third_party_urls: Tuple[str, ...]
    excluded_by_cap_count: int
    max_http_requests: int
    per_domain_counts: Tuple[Tuple[str, int], ...]


def build_fetch_plan(
    candidates: Sequence[DiscoveryCandidate],
    static_resolutions_by_candidate: Dict[str, Tuple[WebsiteResolution, ...]],
    identity_review_candidate_ids: Sequence[str],
    *,
    max_total: int = C.RESOLUTION_MAX_HTTP_REQUESTS,
    max_per_candidate: int = C.RESOLUTION_MAX_REQUESTS_PER_CANDIDATE,
    max_per_domain: int = C.RESOLUTION_MAX_REQUESTS_PER_DOMAIN,
) -> FetchPlan:
    identity_review_ids = set(identity_review_candidate_ids)
    raw_items = []
    blocked = []

    for c in candidates:
        resolutions = static_resolutions_by_candidate.get(c.candidate_id, ())
        conflicting = static_conflicting_urls(resolutions)
        for r in resolutions:
            if r.resolution_state in (
                C.WEBSITE_RES_THIRD_PARTY_BOOKING_URL, C.WEBSITE_RES_SOCIAL_OR_DIRECTORY_URL,
                C.WEBSITE_RES_MISSING, C.WEBSITE_RES_UNRESOLVED,
            ):
                if r.original_url:
                    blocked.append(r.original_url)
                continue
            if r.resolution_state not in _FETCHABLE_STATES:
                continue
            if c.candidate_id in identity_review_ids:
                priority, reason = PRIORITY_IDENTITY_REVIEW, "identity_review"
            elif conflicting:
                priority, reason = PRIORITY_CONFLICTING_WEBSITE, "conflicting_website"
            else:
                priority, reason = PRIORITY_PROBABLE_OR_CHAIN_HOMEPAGE, "probable_or_chain_homepage"
            raw_items.append(FetchPlanItem(
                candidate_id=c.candidate_id, url=r.normalized_url,
                registrable_domain=r.registrable_domain, priority=priority, reason=reason,
            ))
    # Task 6 priority 4 (missing-website candidates with a useful domain
    # lead) is disclosed as structurally empty in this phase: "missing
    # website" means every source record's website_url is already empty,
    # so there is no domain lead anywhere in discovery provenance to fetch
    # -- populating this tier would require inventing a URL, which
    # doctrine #7 forbids. Left as a defined, always-empty tier here.

    raw_items.sort(key=lambda item: (item.priority, item.candidate_id, item.url))

    selected: list = []
    per_candidate_count: Dict[str, int] = {}
    per_domain_count: Dict[str, int] = {}
    total = 0
    excluded_by_cap = 0
    seen = set()

    for item in raw_items:
        key = (item.candidate_id, item.url)
        if key in seen:
            continue
        seen.add(key)
        if total >= max_total:
            excluded_by_cap += 1
            continue
        if per_candidate_count.get(item.candidate_id, 0) >= max_per_candidate:
            excluded_by_cap += 1
            continue
        if per_domain_count.get(item.registrable_domain, 0) >= max_per_domain:
            excluded_by_cap += 1
            continue
        selected.append(item)
        per_candidate_count[item.candidate_id] = per_candidate_count.get(item.candidate_id, 0) + 1
        per_domain_count[item.registrable_domain] = per_domain_count.get(item.registrable_domain, 0) + 1
        total += 1

    static_only = len(candidates) - len({item.candidate_id for item in selected})

    return FetchPlan(
        items=tuple(selected), total_candidates=len(candidates),
        static_only_count=static_only, fetch_required_count=len(selected),
        blocked_third_party_urls=tuple(sorted(set(blocked))),
        excluded_by_cap_count=excluded_by_cap, max_http_requests=len(selected),
        per_domain_counts=tuple(sorted(per_domain_count.items())),
    )
