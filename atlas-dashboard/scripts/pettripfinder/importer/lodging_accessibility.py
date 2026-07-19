"""AES-DATA-004G (Task 1) -- manifest-level lodging accessibility classifier.

Classifies every generated lodging import job BEFORE any live execution, so
Anthropic/HTTP spend is directed only at properties whose official source is
plausibly reachable through the compliant fetcher. Built entirely on OBSERVED
evidence -- live fetch outcomes from AES-DATA-004D/004E operational runs and
the earlier PTF inventory waves whose results sit in production -- never on a
hotel's name, and never on speculation dressed up as fact.

The registry below is a versioned, domain-level record of that evidence.
Domain entries are acceptable (the mission authorizes "a versioned
domain-access registry based on observed results"); individual property-name
exceptions are not, and none exist here.
"""

from __future__ import annotations

from typing import Tuple
from urllib.parse import urlsplit

# --------------------------------------------------------------------------- #
# Accessibility states (Task 1).
# --------------------------------------------------------------------------- #

ACCESS_ACCESSIBLE_CONFIRMED = "ACCESSIBLE_CONFIRMED"
ACCESS_ACCESSIBLE_PROBABLE = "ACCESSIBLE_PROBABLE"
ACCESS_TIMEOUT_RETRY_ELIGIBLE = "TIMEOUT_RETRY_ELIGIBLE"
ACCESS_WAF_BLOCKED = "WAF_BLOCKED"
ACCESS_CHAIN_POLICY_ONLY = "CHAIN_POLICY_ONLY"
ACCESS_MISSING_OFFICIAL_SOURCE = "MISSING_OFFICIAL_SOURCE"
ACCESS_MANUAL_REVIEW = "MANUAL_REVIEW"
ACCESS_DEFER = "DEFER"

ACCESS_STATES = frozenset({
    ACCESS_ACCESSIBLE_CONFIRMED, ACCESS_ACCESSIBLE_PROBABLE,
    ACCESS_TIMEOUT_RETRY_ELIGIBLE, ACCESS_WAF_BLOCKED,
    ACCESS_CHAIN_POLICY_ONLY, ACCESS_MISSING_OFFICIAL_SOURCE,
    ACCESS_MANUAL_REVIEW, ACCESS_DEFER,
})

# States eligible for an executable accessible batch (Task 5). WAF_BLOCKED,
# MANUAL_REVIEW, DEFER, CHAIN_POLICY_ONLY, and MISSING_OFFICIAL_SOURCE are
# never executable in this phase.
EXECUTABLE_STATES = frozenset({
    ACCESS_ACCESSIBLE_CONFIRMED, ACCESS_ACCESSIBLE_PROBABLE,
    ACCESS_TIMEOUT_RETRY_ELIGIBLE,
})

# --------------------------------------------------------------------------- #
# Domain-access registry (versioned; observed evidence only).
#
# Evidence provenance key:
#   live_2026_07_403      -- HTTP 403 observed in AES-DATA-004D and/or the
#                            AES-DATA-004E live validation (hilton and ihg were
#                            each confirmed blocked TWICE, on separate days,
#                            the second time with the hardened fetcher).
#   live_2026_07_ok       -- HTTP 200 + successful extraction observed in
#                            AES-DATA-004D / AES-WORK-001D live runs.
#   live_2026_07_timeout  -- fetch_timeout observed in AES-DATA-004D
#                            (choicehotels x3, columbusgrandhotel x1) and/or
#                            Cloudflare 522 in AES-DATA-004E.
#   production_import_ok  -- the domain's property rows exist in the production
#                            seed CSV, imported by THIS importer in earlier PTF
#                            inventory waves (historical fetch success, no
#                            current negative observation).
#   operator_flagged      -- manifest inspection found the resolved website is
#                            not a lodging site at all (a brewery, a health
#                            system, a cosmetics brand, ...) -- a discovery
#                            misresolution; requires human review, never an
#                            automated import. Domain-level fact, not a
#                            property-name exception.
#   untested_major_chain  -- enterprise chain domain with NO observation in
#                            either direction; conservatively deferred rather
#                            than spending capped batch slots on probes with
#                            WAF-scale infrastructure.
# --------------------------------------------------------------------------- #

DOMAIN_REGISTRY_VERSION = "2026.07.19-1"

WAF_BLOCKED_DOMAINS = frozenset({
    "hilton.com", "marriott.com", "ihg.com", "hyatt.com",
    "redroof.com", "radissonhotels.com",
    # 2026.07.19-1: extendedstayamerica.com returned HTTP 403 in the live
    # AES-DATA-004G accessible wave -- its earlier production_import_ok
    # evidence is stale; reclassified on the newer observation.
    "extendedstayamerica.com",
})

ACCESSIBLE_CONFIRMED_DOMAINS = frozenset({
    "sonesta.com", "intownsuites.com", "druryhotels.com",
    # 2026.07.19-1: wyndhamhotels.com fetched HTTP 200 with a successful
    # extraction in the live AES-DATA-004G wave (La Quinta Reynoldsburg) --
    # promoted from historical-probable to confirmed.
    "wyndhamhotels.com",
})

TIMEOUT_OBSERVED_DOMAINS = frozenset({
    # choicehotels.com: fetch_timeout observed on FOUR jobs across THREE
    # separate live runs (004D x3, 004G probe x1, the last with the hardened
    # 20s-read-timeout fetcher). Still classified retry-ELIGIBLE by state,
    # but wave planning should not spend another probe soon.
    "choicehotels.com", "columbusgrandhotel.com",
})

HISTORICAL_OK_CHAIN_DOMAINS = frozenset()

MANAGEMENT_COMPANY_DOMAINS = frozenset({"oyorooms.com"})

UNTESTED_MAJOR_CHAIN_DOMAINS = frozenset({
    "bestwestern.com", "motel6.com", "woodspring.com",
})

# Operator-flagged non-lodging or quality-suspect resolved websites (observed
# manifest defects, domain-level).
SUSPECT_WEBSITE_DOMAINS = frozenset({
    "nocterrabrewing.com", "elliotswoodfired.com", "thelocust-table.com",
    "ohiohealth.com", "naturabisse.com", "gahannahistory.com",
    "hulihulipowell.com", "coccokaybites.com", "614rentme.com",
    "schwartzcastle.com", "holidaymotelcolumbusohio.top",
})


def _registrable(host: str) -> str:
    host = (host or "").lower().strip(".")
    labels = host.split(".")
    return ".".join(labels[-2:]) if len(labels) >= 2 else host


def _matches(host: str, domains: frozenset) -> bool:
    reg = _registrable(host)
    return reg in domains


def classify_url_accessibility(url: str) -> Tuple[str, str]:
    """Classify ONE official URL into an accessibility state.

    Returns ``(state, reason)``. Deterministic; registry-driven; never
    consults the property name. A URL on an unknown (unregistered) domain is
    an independent/small property site -- exactly the class every live run
    so far has been able to fetch -- and classifies ACCESSIBLE_PROBABLE with
    an explicit ``unobserved_independent_domain`` reason; it is never
    promoted to CONFIRMED without observed evidence.
    """
    if not url or not url.strip():
        return (ACCESS_MISSING_OFFICIAL_SOURCE, "no_official_url")
    host = urlsplit(url).hostname or ""
    if not host:
        return (ACCESS_MISSING_OFFICIAL_SOURCE, "unparseable_url")

    if _matches(host, WAF_BLOCKED_DOMAINS):
        return (ACCESS_WAF_BLOCKED, "live_2026_07_403")
    if _matches(host, SUSPECT_WEBSITE_DOMAINS):
        return (ACCESS_MANUAL_REVIEW, "operator_flagged_non_lodging_website")
    if _matches(host, TIMEOUT_OBSERVED_DOMAINS):
        return (ACCESS_TIMEOUT_RETRY_ELIGIBLE, "live_2026_07_timeout")
    if _matches(host, ACCESSIBLE_CONFIRMED_DOMAINS):
        # A chain-root URL with no property path proves nothing about a
        # selected property (Task 1: CHAIN_POLICY_ONLY).
        path = urlsplit(url).path.strip("/")
        if not path:
            return (ACCESS_CHAIN_POLICY_ONLY, "chain_root_url_only")
        return (ACCESS_ACCESSIBLE_CONFIRMED, "live_2026_07_ok")
    if _matches(host, HISTORICAL_OK_CHAIN_DOMAINS):
        return (ACCESS_ACCESSIBLE_PROBABLE, "production_import_ok_historical")
    if _matches(host, MANAGEMENT_COMPANY_DOMAINS):
        return (ACCESS_ACCESSIBLE_PROBABLE, "management_company_property_page")
    if _matches(host, UNTESTED_MAJOR_CHAIN_DOMAINS):
        return (ACCESS_DEFER, "untested_major_chain")
    # Unknown domain: an independent/small-chain property site.
    path = urlsplit(url).path.strip("/")
    if not path:
        # Root URL on an independent single-property domain IS the property
        # page (e.g. columbusgrandhotel.com) -- still probable.
        return (ACCESS_ACCESSIBLE_PROBABLE, "unobserved_independent_domain")
    return (ACCESS_ACCESSIBLE_PROBABLE, "unobserved_independent_domain")


# Ranking (Task 3): state order first, then source-class preference within
# state -- confirmed domains, then independents/small chains, then
# historically-OK chains, then management companies. Lower rank sorts first.
_STATE_RANK = {
    ACCESS_ACCESSIBLE_CONFIRMED: 0,
    ACCESS_ACCESSIBLE_PROBABLE: 1,
    ACCESS_TIMEOUT_RETRY_ELIGIBLE: 2,
}

_REASON_RANK = {
    "live_2026_07_ok": 0,
    "unobserved_independent_domain": 1,
    "production_import_ok_historical": 2,
    "management_company_property_page": 3,
    "live_2026_07_timeout": 4,
}


def executable_sort_key(state: str, reason: str, job_id: str) -> Tuple[int, int, str]:
    """Deterministic priority key for executable jobs. job_id is the final
    tiebreaker so output order is stable across runs."""
    return (_STATE_RANK.get(state, 99), _REASON_RANK.get(reason, 99), job_id)
