"""AES-DATA-004C Tasks 4/5/8 -- official-website resolution: static URL
classification (no fetch) and post-fetch identity validation.

Static classification (``classify_url_statically``) never marks a URL
CONFIRMED -- confirmation requires an actual fetch and matching identity
signals (``validate_fetched_identity``), per doctrine: "Do not call a URL
confirmed merely from path syntax."
"""

from __future__ import annotations

from typing import Optional, Tuple
from urllib.parse import urlsplit

from scripts.pettripfinder.discovery import constants as C
from scripts.pettripfinder.discovery.models import DiscoveryCandidate, WebsiteResolution
from scripts.pettripfinder.discovery.normalize import normalize_business_name, normalize_url, registrable_domain


def _path_segments(url: str) -> Tuple[str, ...]:
    path = urlsplit(url).path.strip("/")
    return tuple(s for s in path.split("/") if s)


def classify_url_statically(url: str) -> Tuple[str, Tuple[str, ...]]:
    """Returns ``(resolution_state, warnings)``. Pure, no network. Only
    reaches states in ``constants.STATIC_REACHABLE_WEBSITE_STATES``."""
    if not url or not url.strip():
        return (C.WEBSITE_RES_MISSING, ())

    normalized = normalize_url(url)
    if not normalized:
        return (C.WEBSITE_RES_UNRESOLVED, ("malformed_url",))

    domain = registrable_domain(normalized)

    if domain in C.URL_SHORTENER_DOMAINS:
        return (C.WEBSITE_RES_UNRESOLVED, ("url_shortener_unverified",))
    if domain in C.THIRD_PARTY_BOOKING_DOMAINS:
        return (C.WEBSITE_RES_THIRD_PARTY_BOOKING_URL, ())
    if domain in C.SOCIAL_OR_DIRECTORY_DOMAINS:
        return (C.WEBSITE_RES_SOCIAL_OR_DIRECTORY_URL, ())

    segments = _path_segments(normalized)

    if domain in C.KNOWN_CHAIN_BRAND_DOMAINS:
        if not segments:
            return (C.WEBSITE_RES_CHAIN_HOMEPAGE_ONLY, ())
        # Check every segment, not just the first -- brand sites commonly
        # prefix a language code first (e.g. "/en/locations/...").
        lowered = [s.lower() for s in segments]
        if any(hint in seg for seg in lowered for hint in C.BRAND_LOCATOR_PATH_HINTS):
            return (C.WEBSITE_RES_BRAND_LOCATION_SEARCH_ONLY, ())
        if len(segments) >= 2:
            return (C.WEBSITE_RES_PROPERTY_URL_PROBABLE, ())
        return (C.WEBSITE_RES_CHAIN_HOMEPAGE_ONLY, ("shallow_path_on_chain_domain",))

    # Independent (non-chain, non-third-party) domain -- probable, never
    # confirmed without a fetch, per Task 5.
    return (C.WEBSITE_RES_PROPERTY_URL_PROBABLE, ())


def classify_candidate_urls_statically(candidate: DiscoveryCandidate) -> Tuple[WebsiteResolution, ...]:
    """One static classification per distinct URL contributed by this
    candidate's source records (never just the already-resolved
    ``candidate.website_url``, so a genuinely conflicting second URL is
    still visible to the fetch-planning stage)."""
    seen = {}
    for r in candidate.source_records:
        if not r.website_url:
            continue
        normalized = normalize_url(r.website_url)
        key = normalized or r.website_url
        if key in seen:
            continue
        state, warnings = classify_url_statically(r.website_url)
        seen[key] = WebsiteResolution(
            candidate_id=candidate.candidate_id, source_provider=r.provider,
            original_url=r.website_url, normalized_url=normalized,
            registrable_domain=registrable_domain(normalized) if normalized else "",
            resolution_state=state, warnings=warnings,
        )
    if not seen:
        return (WebsiteResolution(
            candidate_id=candidate.candidate_id, source_provider="", original_url="",
            normalized_url="", registrable_domain="", resolution_state=C.WEBSITE_RES_MISSING,
        ),)
    return tuple(seen.values())


def static_conflicting_urls(resolutions: Tuple[WebsiteResolution, ...]) -> bool:
    """True when two or more distinct registrable domains were both
    classified as plausibly official (probable/confirmed-eligible states),
    i.e. providers disagree about which domain is the real one."""
    plausible_domains = {
        r.registrable_domain for r in resolutions
        if r.resolution_state in (C.WEBSITE_RES_PROPERTY_URL_PROBABLE, C.WEBSITE_RES_PROPERTY_URL_CONFIRMED)
        and r.registrable_domain
    }
    return len(plausible_domains) > 1


# --------------------------------------------------------------------------- #
# Task 8: post-fetch property-identity validation.
# --------------------------------------------------------------------------- #

def _name_matches(candidate: DiscoveryCandidate, snapshot_name: str) -> bool:
    if not snapshot_name or not candidate.normalized_name:
        return False
    sn = normalize_business_name(snapshot_name)
    cn = candidate.normalized_name
    return bool(sn) and (sn == cn or cn in sn or sn in cn)


def _address_matches(candidate: DiscoveryCandidate, snapshot_address: str) -> bool:
    if not snapshot_address or not candidate.address_line:
        return False
    sa = normalize_business_name(snapshot_address)
    ca = normalize_business_name(candidate.address_line)
    if not sa or not ca:
        return False
    return ca in sa or sa in ca


def validate_fetched_identity(
    candidate: DiscoveryCandidate,
    *,
    page_title: str,
    structured_name: str,
    structured_address: str,
    fetch_ok: bool,
    fetch_reason: str,
    registrable_domain_value: str,
) -> Tuple[str, Tuple[str, ...]]:
    """Deterministic post-fetch identity classification. Never evaluates
    pet policy -- identity signals only (mission Task 8)."""
    if not fetch_ok:
        return (C.WEBSITE_RES_FETCH_BLOCKED, (fetch_reason or "fetch_failed",))

    name_match = _name_matches(candidate, structured_name) or _name_matches(candidate, page_title)
    address_match = _address_matches(candidate, structured_address)
    has_structured = bool(structured_name)

    if (name_match and address_match) or (has_structured and name_match and address_match):
        if registrable_domain_value in C.PROPERTY_MANAGEMENT_DOMAINS:
            return (C.WEBSITE_RES_MANAGEMENT_COMPANY_PAGE, ())
        return (C.WEBSITE_RES_PROPERTY_URL_CONFIRMED, ())
    if name_match or (has_structured and name_match):
        return (C.WEBSITE_RES_PROPERTY_URL_PROBABLE, ("weak_identity_signal",))
    if registrable_domain_value in C.KNOWN_CHAIN_BRAND_DOMAINS:
        return (C.WEBSITE_RES_CHAIN_HOMEPAGE_ONLY, ("no_location_identity",))
    return (C.WEBSITE_RES_UNRESOLVED, ("no_identity_signal",))
