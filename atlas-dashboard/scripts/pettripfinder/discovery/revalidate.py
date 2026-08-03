"""PTF-DISCOVERY-001 -- bounded official-page URL revalidation pass.

WHAT THIS IS *NOT*
------------------
**This is not the primary identity path for the major hotel chains, and must
not be scaled into one.** The bounded `reval-001` pass measured why, on 40
authorized requests across 23 hosts:

  * ``bestwestern.com``, ``choicehotels.com``, ``extendedstayamerica.com``,
    ``hyatt.com`` and ``ihg.com`` returned non-200 on ``robots.txt`` itself --
    edge bot-blocking, which fail-closed correctly treats as DENIED, so their
    crawl policy is never even learned;
  * ``hilton.com`` and ``marriott.com`` returned HTTP 403 on the page fetch;
  * of 15 pages successfully retrieved, only **1** carried any lodging JSON-LD
    at all, so 14 failed with "no stable identity keys agreed" -- an absence of
    evidence, not a mismatch;
  * the single property whose identity was confirmed was an independent B&B
    with no capture adapter.

Scaling this route would buy more 403s, not more confirmed identities. Founder
decision: identity confirmation for adapter-supported brands moves to the
**visible-browser capture session** (`ADR-PTF-AUTOMATED-BROWSING`,
`capture_automation/identity_check.py`), which already reaches those hosts.

WHAT THIS IS
------------
Bounded diagnostic tooling, and the retained identity path for **statically
reachable** properties: independent hotels and any source whose official page
exposes sufficient stable identity data. The static path stays preferred
wherever it can prove identity reliably -- it is cheaper and needs no browser.

Authorized scope: **official hotel and hotel-brand pages only.** This module
contains no provider-API client and no code path to one. It does not discover
candidates, extract policy, approve, promote, assemble or deploy.

Every authorized bound is enforced here, before a request is issued:

  * robots.txt consulted FIRST, fail-closed -- DENIED and INDETERMINATE both
    block, and there is no retry-under-another-identity path anywhere;
  * <= 40 total HTTP requests. **robots.txt fetches count against this budget**
    -- the strictest reading of "total requests", chosen deliberately;
  * <= 2 requests per candidate;
  * <= 4 requests per domain;
  * >= 1.0s between requests to the same domain;
  * SSRF/redirect/content-type/size protections come from the existing
    ``importer.fetch.RequestsPageFetcher``, unmodified;
  * FD-5 identity: at least two INDEPENDENT stable keys, name never counts,
    a different-property redirect blocks handoff.

Every request and every decision is recorded in the run manifest.
"""

from __future__ import annotations

import json
import re
import time
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple
from urllib.parse import urlsplit

from scripts.pettripfinder.discovery import constants as C
from scripts.pettripfinder.discovery import robots as R
from scripts.pettripfinder.discovery import url_record as U
from scripts.pettripfinder.discovery.models import DiscoveryCandidate
from scripts.pettripfinder.discovery.normalize import normalize_business_name, registrable_domain
from scripts.pettripfinder.discovery.provider_zero import load_candidates, load_resolutions
from scripts.pettripfinder.discovery.queue_seam import project_candidate, summarize
from scripts.pettripfinder.discovery.run_context import DiscoveryRunContext

# Authorized bounds.
MAX_TOTAL_REQUESTS = 40
MAX_REQUESTS_PER_CANDIDATE = 2
MAX_REQUESTS_PER_DOMAIN = 4
MIN_DOMAIN_PACING_SECONDS = 1.0

REPO_ROOT = Path(__file__).resolve().parents[3]
DEFAULT_OUT = REPO_ROOT / "data" / "discovery" / "columbus_wave1_lodging" / "revalidation"


# --------------------------------------------------------------------------- #
# Structured-identity extraction.
#
# ``website_fetcher.parse_identity_snapshot`` flattens the JSON-LD address into
# one joined string, which loses the field boundaries FD-5 needs to tell one
# stable key from another. This extractor keeps them separate. It is additive:
# ``website_fetcher`` is not modified.
# --------------------------------------------------------------------------- #

_JSONLD_RE = re.compile(
    r'<script[^>]+type=["\']application/ld\+json["\'][^>]*>(.*?)</script>',
    re.IGNORECASE | re.DOTALL)
_LODGING_TYPES = frozenset({"hotel", "lodgingbusiness", "localbusiness", "resort",
                            "motel", "bedandbreakfast"})


@dataclass(frozen=True)
class StructuredIdentity:
    name: str = ""
    street_address: str = ""
    postal_code: str = ""
    telephone: str = ""


def _flatten(data) -> list:
    if isinstance(data, list):
        out = []
        for item in data:
            out.extend(_flatten(item))
        return out
    if isinstance(data, dict):
        if isinstance(data.get("@graph"), list):
            out = []
            for item in data["@graph"]:
                out.extend(_flatten(item))
            return out
        return [data]
    return []


def extract_structured_identity(body: bytes) -> StructuredIdentity:
    """Pure parse. Never raises -- a malformed page yields empty fields, which
    downstream becomes 'no stable key agreed', not an optimistic default."""
    try:
        text = body.decode("utf-8", errors="replace")
    except Exception:
        return StructuredIdentity()

    for block in _JSONLD_RE.findall(text):
        try:
            data = json.loads(block.strip())
        except Exception:
            continue
        for obj in _flatten(data):
            obj_type = str(obj.get("@type", "")).lower()
            if obj_type not in _LODGING_TYPES:
                continue
            addr = obj.get("address")
            street = postal = ""
            if isinstance(addr, dict):
                street = str(addr.get("streetAddress", "") or "")
                postal = str(addr.get("postalCode", "") or "")
            elif isinstance(addr, str):
                street = addr
            return StructuredIdentity(
                name=str(obj.get("name", "") or ""),
                street_address=street, postal_code=postal,
                telephone=str(obj.get("telephone", "") or ""))
    return StructuredIdentity()


# --------------------------------------------------------------------------- #
# FD-5 key agreement.
# --------------------------------------------------------------------------- #

def _digits(value: str) -> str:
    return re.sub(r"\D", "", value or "")


def _street_number(value: str) -> str:
    m = re.match(r"\s*(\d+)", value or "")
    return m.group(1) if m else ""


def compare_identity(candidate: DiscoveryCandidate, found: StructuredIdentity,
                     candidate_phone: str) -> U.IdentityKeyAgreement:
    """Which INDEPENDENT stable keys agree between our candidate and the page.

    Independence matters more than count here. ``streetAddress`` and
    ``postalCode + street number`` both derive from the SAME address block, so
    at most one of them is ever counted -- treating them as two would satisfy
    FD-5's arithmetic while defeating its intent.
    """
    agreeing: List[str] = []
    conflicting: List[str] = []
    non_identity: List[str] = []

    # --- address-derived: at most ONE key ---------------------------------- #
    cand_addr = normalize_business_name(candidate.address_line)
    page_addr = normalize_business_name(found.street_address)
    if cand_addr and page_addr:
        if cand_addr == page_addr or cand_addr in page_addr or page_addr in cand_addr:
            agreeing.append(U.KEY_NORMALIZED_STREET_ADDRESS)
        elif (_street_number(candidate.address_line)
              and _street_number(candidate.address_line) == _street_number(found.street_address)
              and candidate.postal_code and candidate.postal_code == found.postal_code):
            agreeing.append(U.KEY_POSTAL_PLUS_STREET_NUMBER)
        else:
            conflicting.append(U.KEY_NORMALIZED_STREET_ADDRESS)

    # --- phone: independent of the address block --------------------------- #
    cand_phone = _digits(candidate_phone)[-10:]
    page_phone = _digits(found.telephone)[-10:]
    if cand_phone and page_phone:
        if cand_phone == page_phone:
            agreeing.append(U.KEY_PROPERTY_PHONE)
        else:
            conflicting.append(U.KEY_PROPERTY_PHONE)

    # --- name: recorded, NEVER counted ------------------------------------- #
    if found.name:
        cn, pn = candidate.normalized_name, normalize_business_name(found.name)
        if cn and pn and (cn == pn or cn in pn or pn in cn):
            non_identity.append("name")

    return U.IdentityKeyAgreement(
        agreeing_keys=tuple(agreeing), conflicting_keys=tuple(conflicting),
        non_identity_signals_seen=tuple(non_identity))


# --------------------------------------------------------------------------- #
# Budget.
# --------------------------------------------------------------------------- #

class RequestBudget:
    """Hard caps, checked BEFORE any request. robots.txt counts."""

    def __init__(self, *, total=MAX_TOTAL_REQUESTS, per_candidate=MAX_REQUESTS_PER_CANDIDATE,
                 per_domain=MAX_REQUESTS_PER_DOMAIN):
        self.total_cap, self.per_candidate_cap, self.per_domain_cap = total, per_candidate, per_domain
        self.total = 0
        self.by_candidate: Dict[str, int] = {}
        self.by_domain: Dict[str, int] = {}
        self.domains_at_cap: set = set()

    def may_spend(self, candidate_id: str, domain: str) -> Tuple[bool, str]:
        if self.total >= self.total_cap:
            return (False, "total_request_cap_reached")
        if self.by_candidate.get(candidate_id, 0) >= self.per_candidate_cap:
            return (False, "per_candidate_cap_reached")
        if self.by_domain.get(domain, 0) >= self.per_domain_cap:
            self.domains_at_cap.add(domain)
            return (False, "per_domain_cap_reached")
        return (True, "")

    def spend(self, candidate_id: str, domain: str) -> None:
        self.total += 1
        self.by_candidate[candidate_id] = self.by_candidate.get(candidate_id, 0) + 1
        self.by_domain[domain] = self.by_domain.get(domain, 0) + 1
        if self.by_domain[domain] >= self.per_domain_cap:
            self.domains_at_cap.add(domain)


class DomainPacer:
    def __init__(self, min_seconds=MIN_DOMAIN_PACING_SECONDS, sleep_fn=None, now_fn=None):
        self._min = min_seconds
        self._sleep = sleep_fn or time.sleep
        self._now = now_fn or time.monotonic
        self._last: Dict[str, float] = {}

    def wait(self, domain: str) -> float:
        last = self._last.get(domain)
        waited = 0.0
        if last is not None:
            elapsed = self._now() - last
            if elapsed < self._min:
                waited = self._min - elapsed
                self._sleep(waited)
        self._last[domain] = self._now()
        return waited


# --------------------------------------------------------------------------- #
# Fetchers.
# --------------------------------------------------------------------------- #

def make_robots_fetcher(*, as_of: str, record):
    """robots.txt fetcher with the SAME SSRF gate the page fetcher uses.

    robots.txt is text/plain, so it cannot go through RequestsPageFetcher
    (HTML-only allowlist); the host validation is reused explicitly instead of
    being skipped.
    """
    def fetch(robots_url: str) -> R.RobotsFetchResult:
        from scripts.pettripfinder.importer.fetch import assert_fetchable
        import requests

        ok, reason = assert_fetchable(robots_url)
        if not ok:
            record(robots_url, "robots", None, "ssrf_gate:%s" % reason)
            return R.RobotsFetchResult(ok=False, retrieved_at=as_of)
        try:
            resp = requests.get(
                robots_url,
                headers={"User-Agent": C.GOOGLE_USER_AGENT,
                         "Accept": "text/plain,*/*;q=0.5"},
                timeout=(C.CONNECT_TIMEOUT_SECONDS, C.READ_TIMEOUT_SECONDS),
                allow_redirects=True)
        except Exception as exc:
            record(robots_url, "robots", None, "transport_error:%s" % type(exc).__name__)
            return R.RobotsFetchResult(ok=False, retrieved_at=as_of)

        status = resp.status_code
        if status == 404:
            # No robots.txt is a valid "no restrictions" answer, distinct from
            # an unreachable one. Represented as an empty document.
            record(robots_url, "robots", status, "absent_404_treated_as_empty")
            return R.RobotsFetchResult(ok=True, text="", http_status=status,
                                       retrieved_at=as_of)
        if status != 200:
            record(robots_url, "robots", status, "non_200")
            return R.RobotsFetchResult(ok=False, http_status=status, retrieved_at=as_of)
        text = resp.text[:512 * 1024]
        record(robots_url, "robots", status, "ok")
        return R.RobotsFetchResult(ok=True, text=text, http_status=status,
                                   retrieved_at=as_of)

    return fetch


# --------------------------------------------------------------------------- #
# The pass.
# --------------------------------------------------------------------------- #

@dataclass
class RevalidationReport:
    run_id: str = ""
    effective_time: str = ""
    eligible_candidates: int = 0
    candidates_attempted: int = 0
    urls_attempted: int = 0
    robots_requests: int = 0        # observed robots fetches
    page_requests: int = 0          # observed page fetches
    total_requests: int = 0         # AUTHORITATIVE: what the 40-cap governs
    observed_requests: int = 0      # robots_requests + page_requests
    robots_allowed: int = 0
    robots_blocked: int = 0
    robots_indeterminate: int = 0
    retrieval_success: int = 0
    retrieval_failure: int = 0
    identity_pass: int = 0
    identity_fail: int = 0
    identity_unchecked: int = 0
    queue_entries: int = 0
    still_blocked: int = 0
    domains_at_cap: List[str] = field(default_factory=list)
    stopped_reason: str = ""
    anomalies: List[str] = field(default_factory=list)
    requests: List[dict] = field(default_factory=list)
    decisions: List[dict] = field(default_factory=list)

    def to_dict(self) -> dict:
        return dict(self.__dict__)


def _phone_for(candidate: DiscoveryCandidate) -> str:
    for r in candidate.source_records:
        if (r.phone or "").strip():
            return r.phone.strip()
    return ""


def _round_robin_by_domain(items: Sequence[Tuple[DiscoveryCandidate, dict]]):
    """Interleave candidates across domains.

    With a 40-request ceiling only a sample can run, and a candidate_id-ordered
    sample would spend the whole budget on whichever brand sorts first. Domain
    round-robin makes the measured PASS rate representative rather than an
    artifact of ordering. Deterministic: domains and members both sorted.
    """
    buckets: Dict[str, List] = {}
    for cand, res in items:
        buckets.setdefault(registrable_domain(res.get("resolved_url", "")), []).append((cand, res))
    for members in buckets.values():
        members.sort(key=lambda pair: pair[0].candidate_id)
    order = sorted(buckets)
    out = []
    i = 0
    while any(buckets[d][i:] for d in order):
        for d in order:
            if i < len(buckets[d]):
                out.append(buckets[d][i])
        i += 1
    return out


def run_revalidation(*, run_id: str, effective_time: str, live: bool = False,
                     robots_fetcher=None, page_fetcher=None, pacer=None,
                     budget: Optional[RequestBudget] = None,
                     root: Path = None) -> RevalidationReport:
    """Execute the bounded pass.

    ``live=False`` (the default) performs NO network access: it is the offline
    posture used by tests. A live run must pass ``live=True`` explicitly, which
    is what makes network access an opt-in rather than an accident.
    """
    context = DiscoveryRunContext(run_id=run_id, effective_time=effective_time)
    report = RevalidationReport(run_id=run_id, effective_time=effective_time)
    budget = budget or RequestBudget()
    pacer = pacer or DomainPacer()

    def record_request(url, kind, status, outcome):
        report.requests.append({"url": url, "kind": kind, "http_status": status,
                                "outcome": outcome})
        if kind == "robots":
            report.robots_requests += 1
        else:
            report.page_requests += 1
        report.observed_requests = report.robots_requests + report.page_requests

    if live and robots_fetcher is None:
        robots_fetcher = make_robots_fetcher(as_of=effective_time, record=record_request)
    if live and page_fetcher is None:
        from scripts.pettripfinder.importer.fetch import RequestsPageFetcher
        page_fetcher = RequestsPageFetcher(min_domain_interval_seconds=0)

    candidates = load_candidates(root)
    resolutions = load_resolutions(root)
    eligible = [(c, resolutions.get(c.candidate_id, {})) for c in candidates
                if resolutions.get(c.candidate_id, {}).get("resolution_outcome")
                in C.RESOLUTION_ELIGIBLE_FOR_BATCH
                and resolutions.get(c.candidate_id, {}).get("resolved_url")]
    report.eligible_candidates = len(eligible)

    robots_cache = R.RobotsCache()
    seam_results = []

    for cand, res in _round_robin_by_domain(eligible):
        url = res["resolved_url"]
        domain = registrable_domain(url)
        host = urlsplit(url).netloc

        ok, why = budget.may_spend(cand.candidate_id, domain)
        if not ok:
            if why == "total_request_cap_reached":
                report.stopped_reason = why
                break
            continue

        # ---- robots FIRST, fail-closed ----------------------------------- #
        need_robots = robots_cache.get(host) is None
        if need_robots:
            ok, why = budget.may_spend(cand.candidate_id, domain)
            if not ok:
                if why == "total_request_cap_reached":
                    report.stopped_reason = why
                    break
                continue
            pacer.wait(domain)
            budget.spend(cand.candidate_id, domain)

        decision = R.check_url(url, cache=robots_cache, robots_fetcher=robots_fetcher,
                               as_of=effective_time)
        if decision.decision == R.ALLOWED:
            report.robots_allowed += 1
        elif decision.decision == R.DENIED:
            report.robots_blocked += 1
        else:
            report.robots_indeterminate += 1

        report.decisions.append({"candidate_id": cand.candidate_id, "url": url,
                                 "stage": "robots", **decision.to_dict()})

        if decision.decision in R.BLOCKING_DECISIONS:
            report.still_blocked += 1
            seam_results.append(project_candidate(
                cand, resolution_outcome=res.get("resolution_outcome", ""),
                resolved_url=url, run_context_ref=context.ref(),
                url_revalidation_blocked=True,
                revalidation_reason="robots_%s:%s" % (decision.decision, decision.reason)))
            continue

        # ---- page fetch --------------------------------------------------- #
        ok, why = budget.may_spend(cand.candidate_id, domain)
        if not ok:
            if why == "total_request_cap_reached":
                report.stopped_reason = why
                break
            continue

        report.candidates_attempted += 1
        report.urls_attempted += 1
        pacer.wait(domain)
        budget.spend(cand.candidate_id, domain)
        result = page_fetcher.fetch(url)
        record_request(url, "page", result.http_status, "ok" if result.ok else result.reason)

        if not result.ok:
            report.retrieval_failure += 1
            report.identity_unchecked += 1
            rec = U.OfficialUrlRecord(
                url=url, status=C.WEBSITE_RES_FETCH_BLOCKED, last_validated_at="",
                property_identity_check=U.IDENTITY_UNCHECKED,
                identity_explanation="retrieval failed: %s" % result.reason)
            report.decisions.append({"candidate_id": cand.candidate_id, "url": url,
                                     "stage": "fetch", "ok": False,
                                     "reason": result.reason,
                                     "http_status": result.http_status})
            report.still_blocked += 1
            seam_results.append(project_candidate(
                cand, resolution_outcome=res.get("resolution_outcome", ""),
                resolved_url=url, run_context_ref=context.ref(),
                official_url_record=rec.to_dict(), url_revalidation_blocked=True,
                revalidation_reason="retrieval_failed:%s" % result.reason))
            continue

        report.retrieval_success += 1
        found = extract_structured_identity(result.body)
        agreement = compare_identity(cand, found, _phone_for(cand))
        check, why_text = U.same_property_identity(agreement)

        chain = tuple(U.RedirectHop(from_url=url, to_url=hop)
                      for hop in (result.redirect_chain or ()))
        rec = U.OfficialUrlRecord(
            url=url,
            status=(C.WEBSITE_RES_PROPERTY_URL_CONFIRMED if check == U.IDENTITY_PASS
                    else C.WEBSITE_RES_PROPERTY_URL_PROBABLE),
            last_validated_at=effective_time, redirect_history=chain,
            canonical_destination=(found and result.final_url) or "",
            property_identity_check=check, identity_explanation=why_text)

        if check == U.IDENTITY_PASS:
            report.identity_pass += 1
        elif check == U.IDENTITY_FAIL:
            report.identity_fail += 1
        else:
            report.identity_unchecked += 1

        report.decisions.append({
            "candidate_id": cand.candidate_id, "url": url, "stage": "identity",
            "final_url": result.final_url, "redirects": list(result.redirect_chain or ()),
            "found_name": found.name, "found_street": found.street_address,
            "found_postal": found.postal_code,
            "found_phone_present": bool(found.telephone),
            "agreeing_keys": list(agreement.agreeing_keys),
            "conflicting_keys": list(agreement.conflicting_keys),
            "non_identity_signals": list(agreement.non_identity_signals_seen),
            "property_identity_check": check, "explanation": why_text})

        handoff = U.evaluate_handoff(rec, as_of=effective_time)
        if not handoff.allowed:
            report.still_blocked += 1
        seam_results.append(project_candidate(
            cand, resolution_outcome=res.get("resolution_outcome", ""),
            resolved_url=url, url_confirmed=(check == U.IDENTITY_PASS),
            identity_confidence=cand.review_state, run_context_ref=context.ref(),
            official_url_record=rec.to_dict(),
            url_revalidation_blocked=not handoff.allowed,
            revalidation_reason=handoff.reason))

    seam = summarize(seam_results)
    report.queue_entries = seam.get("PROJECTED", 0)
    report.domains_at_cap = sorted(budget.domains_at_cap)
    # The BUDGET is authoritative for the cap: it is what every request was
    # checked against before being issued. ``observed_requests`` is what the
    # fetchers actually reported, and the two must agree in a live run -- a
    # divergence means a request escaped accounting, which is an anomaly worth
    # surfacing rather than smoothing over.
    report.total_requests = budget.total
    if not report.stopped_reason:
        report.stopped_reason = "eligible_candidates_exhausted_or_capped"

    if report.total_requests > MAX_TOTAL_REQUESTS:
        report.anomalies.append("TOTAL REQUEST CAP EXCEEDED: %d" % report.total_requests)
    if live and report.observed_requests != report.total_requests:
        report.anomalies.append(
            "request accounting divergence: budget=%d observed=%d"
            % (report.total_requests, report.observed_requests))
    return report


def write_manifest(report: RevalidationReport, *, out_dir: Path = None) -> Path:
    base = Path(out_dir) if out_dir else DEFAULT_OUT
    base.mkdir(parents=True, exist_ok=True)
    path = base / ("revalidation_%s.json" % report.run_id)
    path.write_text(json.dumps(report.to_dict(), indent=2, sort_keys=True),
                    encoding="utf-8")
    return path
