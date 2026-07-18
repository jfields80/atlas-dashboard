"""AES-DATA-004A discovery -- website readiness classification (Task 10).

Syntax/domain classification only -- no live HTTP fetch of candidate
websites happens anywhere in this module or phase (the mission's "tiny
live validation" allowance for a minimal safety check is deliberately not
exercised: the two live-validation categories, veterinary via Google and
dog park via Overpass, don't need it to prove the classifier works, and
skipping it keeps the live run to exactly the Google/Overpass request caps
with nothing else touching the network).
"""

from __future__ import annotations

from typing import Tuple

from scripts.pettripfinder.discovery import constants as C
from scripts.pettripfinder.discovery.models import DiscoveryRecord
from scripts.pettripfinder.discovery.normalize import normalize_url, registrable_domain


def classify_candidate_website(records: Tuple[DiscoveryRecord, ...]) -> Tuple[str, str]:
    """Returns ``(website_state, resolved_website_url)``. ``resolved_website_url``
    is "" whenever the state is not ``OFFICIAL_WEBSITE_PRESENT``."""
    raw_present = [r.website_url for r in records if (r.website_url or "").strip()]
    if not raw_present:
        return (C.WEBSITE_STATE_MISSING, "")

    valid_urls = []
    excluded_urls = []
    for raw in raw_present:
        normalized = normalize_url(raw)
        if not normalized:
            continue
        domain = registrable_domain(normalized)
        if domain in C.NON_OFFICIAL_DOMAINS:
            excluded_urls.append(normalized)
        else:
            valid_urls.append(normalized)

    if not valid_urls:
        if excluded_urls:
            return (C.WEBSITE_STATE_PROVIDER_URL_ONLY, excluded_urls[0])
        # Something was supplied but nothing parsed as a usable http(s) URL.
        return (C.WEBSITE_STATE_AMBIGUOUS, "")

    distinct_domains = sorted({registrable_domain(u) for u in valid_urls})
    if len(distinct_domains) > 1:
        return (C.WEBSITE_STATE_CONFLICTING, "")
    return (C.WEBSITE_STATE_OFFICIAL_PRESENT, valid_urls[0])
