"""AES-DATA-004C Tasks 9/10 -- missing-website categorization and final
import-eligibility outcomes. Pure, deterministic; never fetches, never
asserts pet-friendliness.
"""

from __future__ import annotations

from typing import Sequence, Tuple

from scripts.pettripfinder.discovery import constants as C
from scripts.pettripfinder.discovery.models import DiscoveryCandidate, WebsiteResolution
from scripts.pettripfinder.discovery.website_resolution import static_conflicting_urls


def _eligibility_states(candidate: DiscoveryCandidate) -> set:
    return {r.eligibility_state for r in candidate.source_records if r.eligibility_state}


def categorize_missing_website(candidate: DiscoveryCandidate, scope: str) -> str:
    """Task 9: a scalable queue categorization, not unlimited research."""
    if scope == C.SCOPE_OUT_OF_SCOPE:
        return C.MISSING_ACTION_OUT_OF_SCOPE
    if C.ELIGIBILITY_PERMANENTLY_CLOSED in _eligibility_states(candidate):
        return C.MISSING_ACTION_CLOSED_OR_REBRANDED_REVIEW
    tokens = set(candidate.normalized_name.split())
    if tokens & C.MISSING_WEBSITE_CHAIN_NAME_TOKENS:
        return C.MISSING_ACTION_RESOLVE_FROM_BRAND_LOCATOR
    return C.MISSING_ACTION_DEFER_LOW_PRIORITY


def compute_resolution_outcome(
    candidate: DiscoveryCandidate, *, scope: str, identity_outcome: str,
    website_resolutions: Sequence[WebsiteResolution],
) -> str:
    """Task 10: priority-ordered, deterministic. Never marks a candidate
    pet-friendly -- outcomes describe import readiness only."""
    if C.ELIGIBILITY_PERMANENTLY_CLOSED in _eligibility_states(candidate):
        return C.RESOLUTION_EXCLUDE_CLOSED
    if scope == C.SCOPE_OUT_OF_SCOPE:
        return C.RESOLUTION_EXCLUDE_OUT_OF_SCOPE
    if not (candidate.city or "").strip() or not (candidate.state or "").strip():
        # A candidate can be geographically IN_SCOPE from coordinates alone
        # (Task 1) while still lacking a usable city/state string -- the
        # importer's own batch schema requires both non-empty (found live
        # while validating generated batches: 5/353 real candidates hit
        # this, all cases where the deduped "best record" happened to be an
        # OSM element with no addr:city/addr:state tags). Never generate an
        # invalid batch job; defer instead.
        return C.RESOLUTION_DEFER
    if identity_outcome in (C.IDENTITY_UNRESOLVED, C.IDENTITY_POSSIBLE_REBRAND):
        # A possible rebrand is NOT yet confirmed as one location or two --
        # letting both sides proceed independently risks exactly the
        # duplicate-import-job outcome doctrine forbids ("do not create
        # duplicate import jobs for one location"). Held for review until a
        # fetch confirms current identity (-> SAME_LOCATION_CURRENT_NAME)
        # or genuine distinctness.
        return C.RESOLUTION_REVIEW_IDENTITY

    states = {r.resolution_state for r in website_resolutions}
    if static_conflicting_urls(tuple(website_resolutions)):
        return C.RESOLUTION_REVIEW_WEBSITE
    if C.WEBSITE_RES_FETCH_BLOCKED in states:
        return C.RESOLUTION_REVIEW_WEBSITE

    # MANAGEMENT_COMPANY_PAGE is a confirmed-identity state with different
    # provenance (Task 8) -- it qualifies as a property-level signal on its
    # own, not merely a brand supplement.
    property_states = {C.WEBSITE_RES_PROPERTY_URL_CONFIRMED, C.WEBSITE_RES_PROPERTY_URL_PROBABLE,
                       C.WEBSITE_RES_MANAGEMENT_COMPANY_PAGE}
    has_property = bool(states & property_states)
    has_brand_supplement = bool(states & {C.WEBSITE_RES_CHAIN_HOMEPAGE_ONLY})

    if has_property and scope == C.SCOPE_IN_SCOPE:
        if has_brand_supplement:
            return C.RESOLUTION_READY_WITH_BRAND_SUPPLEMENT
        return C.RESOLUTION_READY_FOR_PET_POLICY_IMPORT

    if (states & {C.WEBSITE_RES_MISSING, C.WEBSITE_RES_UNRESOLVED}) and not has_property:
        return C.RESOLUTION_MISSING_OFFICIAL_WEBSITE

    return C.RESOLUTION_DEFER
