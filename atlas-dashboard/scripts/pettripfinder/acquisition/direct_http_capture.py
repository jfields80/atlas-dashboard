"""PTF-ST-LOUIS-MARKET-001 -- the ``direct_http`` lane, finally built.

``providers.DIRECT_HTTP`` has existed as a reserved, deliberately UNAVAILABLE
provider id since the router was written, with this note:

    "The long-term goal is that PetTripFinder owns acquisition for easy pages
     and pays a vendor only for hard ones. That slot is declared here so the
     router's ladder can already express 'cheapest first' honestly, and it is
     declared UNAVAILABLE so nothing routes to it by accident."

This module fills the slot. It is one HTTPS GET with a browser user-agent, put
through the SAME gates every other lane is put through -- page health, identity,
canonical locator, reader -- and it writes the same artifact set. Nothing about
the evidence contract is relaxed because the fetch was free.

WHAT IT CAN AND CANNOT REACH
----------------------------
Measured on the St. Louis routed population, one probe per brand, 2026-08-23:

    reached (HTTP 200, policy text present)  DRURY, ESA, SONESTA, WYNDHAM,
                                             most independents
    refused (HTTP 403 at the edge)           MARRIOTT, HILTON, IHG, RED_ROOF
    timed out (no response in 25s)           CHOICE, MOTEL6

That is a capability wall, not a retry problem, and the outcome vocabulary
already distinguishes them: a 403 is ``ACCESS_DENIED`` (terminal for this lane,
escalate), a timeout is ``NAVIGATION_FAILED`` (worth one retry, then escalate).

WHAT THIS MODULE DOES NOT DO
----------------------------
It does not register itself as available in ``providers``, and it does not add a
row to ``routes.json``. A route is added by a benchmark, never by an opinion --
so this lane is exercised by an explicit pilot that measures it, and promoting
it to a route is a separate, evidenced decision.
"""

from __future__ import annotations

import asyncio
import gzip
import html as htmllib
import re
import ssl
import sys
import time
import urllib.error
import urllib.request
import zlib
from pathlib import Path
from typing import Dict, List, Optional, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.brightdata import browser_capture as BC   # noqa: E402
from scripts.pettripfinder.brightdata import declined_capture as DECLINED  # noqa: E402
from scripts.pettripfinder.brightdata import marriott_surface as MS  # noqa: E402
from scripts.pettripfinder.brightdata import outcomes as O           # noqa: E402
from scripts.pettripfinder.brightdata import policy_reading as PR    # noqa: E402
from scripts.pettripfinder.brightdata import policy_surface as PS    # noqa: E402
from scripts.pettripfinder.brightdata import unlocker_capture as UC  # noqa: E402

PROVIDER = "direct HTTPS GET (first-party, no vendor)"
PROVIDER_ID = "direct_http"

#: A real browser's user-agent. Not a disguise: this fetch IS a browser request
#: for one public page, and sending a default urllib agent gets a 403 from
#: origins that serve the same bytes to a browser.
USER_AGENT = ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
              "(KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36")

REQUEST_HEADERS = {
    "User-Agent": USER_AGENT,
    "Accept": ("text/html,application/xhtml+xml,application/xml;q=0.9,"
               "image/avif,image/webp,*/*;q=0.8"),
    "Accept-Language": "en-US,en;q=0.9",
    "Accept-Encoding": "gzip, deflate",
    "Connection": "close",
}

TIMEOUT_SECONDS = 25
#: Refuse a body large enough to be a download rather than a page. 8 MB is well
#: above the largest hotel page measured here (960 KB) and well below anything
#: that would exhaust memory in a 300-property run.
MAX_BODY_BYTES = 8 * 1024 * 1024

#: One free fetch of one URL. A second identical fetch returns the same bytes,
#: so a retry only makes sense for a transport failure.
DEFAULT_MAX_ATTEMPTS = 2

#: An unrendered client-side interpolation token. Handlebars, Mustache, Angular
#: and Vue all spell it the same way, and a served document containing one has
#: not finished being a page.
TEMPLATE_TOKEN = re.compile(r"\{\{[^{}]{1,80}\}\}")

#: Words that mean the template token we found is standing where the POLICY
#: should be, rather than somewhere harmless elsewhere in the document.
POLICY_NEIGHBOURHOOD = ("pet", "pets", "policies", "policy")

#: How far either side of a template token to look for a policy word.
TEMPLATE_NEIGHBOURHOOD_CHARS = 120

#: Outcomes the SHARED ladder calls retryable that are terminal HERE.
#:
#: ``outcomes.worth_retrying`` describes a provider that rotates: a Bright Data
#: zone refused once may not be refused twice, so ACCESS_DENIED earns another
#: attempt there. This lane has one exit IP and one header set, so a refusal is
#: the same refusal every time -- retrying it spends the origin patience and
#: our wall clock to learn nothing. It is terminal, and the ladder escalates.
LANE_TERMINAL_OUTCOMES = frozenset({O.ACCESS_DENIED})


def worth_retrying(outcome: str) -> bool:
    """Retry policy for THIS lane. Never widens the shared rule, only narrows."""
    if outcome in LANE_TERMINAL_OUTCOMES:
        return False
    return O.worth_retrying(outcome)


def policy_region_is_a_template(text: str) -> str:
    """The unrendered token standing where the pet policy belongs, or "".

    Deliberately narrow. A page may carry ``{{...}}`` in an unrelated widget and
    still have rendered its policy perfectly; only a token sitting next to a
    policy word says the thing we came for has not been rendered.
    """
    lowered = (text or "").lower()
    for match in TEMPLATE_TOKEN.finditer(lowered):
        start = max(0, match.start() - TEMPLATE_NEIGHBOURHOOD_CHARS)
        end = min(len(lowered), match.end() + TEMPLATE_NEIGHBOURHOOD_CHARS)
        window = lowered[start:end]
        if any(word in window for word in POLICY_NEIGHBOURHOOD):
            return lowered[match.start():match.end()][:80]
    return ""


class _Fetched:
    __slots__ = ("status", "body", "final_url", "detail")

    def __init__(self, status, body, final_url, detail=""):
        self.status = status
        self.body = body
        self.final_url = final_url
        self.detail = detail


def _decode_body(raw: bytes, encoding: str) -> bytes:
    encoding = (encoding or "").lower()
    try:
        if "gzip" in encoding:
            return gzip.decompress(raw)
        if "deflate" in encoding:
            return zlib.decompress(raw, -zlib.MAX_WBITS)
    except Exception:                                            # noqa: BLE001
        return raw
    return raw


def fetch(url: str, *, timeout: int = TIMEOUT_SECONDS) -> _Fetched:
    """One GET. Never raises: every failure comes back as a status string."""
    request = urllib.request.Request(url, headers=dict(REQUEST_HEADERS))
    context = ssl.create_default_context()
    try:
        with urllib.request.urlopen(request, timeout=timeout,
                                    context=context) as response:
            raw = response.read(MAX_BODY_BYTES + 1)
            if len(raw) > MAX_BODY_BYTES:
                return _Fetched("OVERSIZED", b"", response.geturl(),
                                "body exceeds %d bytes" % MAX_BODY_BYTES)
            body = _decode_body(raw, response.headers.get("Content-Encoding", ""))
            return _Fetched(response.status, body, response.geturl())
    except urllib.error.HTTPError as exc:
        return _Fetched(exc.code, b"", url, "HTTP %s" % exc.code)
    except Exception as exc:                                     # noqa: BLE001
        return _Fetched("TRANSPORT", b"", url,
                        "%s: %s" % (type(exc).__name__, exc))


def _outcome_for_status(status) -> str:
    if status in (401, 403, 406, 429, 451):
        return O.ACCESS_DENIED
    return O.NAVIGATION_FAILED


def run_attempt(target: BC.CaptureTarget, attempt: int, *, run_dir: Path,
                brand: str) -> Tuple[BC.AttemptRecord, Optional[Dict]]:
    """One direct fetch, judged by exactly the gates the paid lanes use."""
    started = time.monotonic()
    started_at = BC.utc_now_iso()
    interactions = BC._Interactions()
    interactions.add("direct HTTPS GET, no vendor, no browser")
    #: Filled the moment a document exists, so every decline AFTER that point
    #: preserves it. A transport failure leaves them empty and keeps nothing,
    #: which is correct: there is no document to keep.
    declined_state = {"html": "", "text": ""}
    declined_manifest: List[Dict] = []

    def finish(outcome: str, *, detail: str = "", final_url: str = "",
               title: str = "", body_chars: int = 0,
               identity: Optional[Dict] = None, artifact_dir: str = "",
               payload: Optional[Dict] = None, bytes_moved: int = 0
               ) -> Tuple[BC.AttemptRecord, Optional[Dict]]:
        record = BC.AttemptRecord(
            attempt=attempt, outcome=outcome, started_at=started_at,
            ended_at=BC.utc_now_iso(),
            elapsed_seconds=time.monotonic() - started,
            requested_url=target.requested_url, final_url=final_url,
            title=title, body_chars=body_chars, detail=detail,
            interactions=interactions.snapshot(), identity=identity,
            network=BC.NetworkUsage(
                available=True, requests=1, encoded_bytes=bytes_moved,
                note="one HTTPS GET; encoded_bytes is what came off the socket, "
                     "not a CDP estimate. This lane has no vendor and no "
                     "per-request price.").to_dict(),
            artifact_dir=artifact_dir)
        declined_html = declined_state["html"]
        declined_text = declined_state["text"]
        if outcome != O.VALID and declined_html:
            # The document reached us and was then declined. Keeping it is what
            # makes "this page states no pet policy" falsifiable: a decline that
            # persists nothing is an assertion nobody can check, which is the
            # defect PTF-MILWAUKEE-CLOSURE-ASSESSMENT-031 found on three
            # properties whose full policy was in the document all along.
            kept = DECLINED.keep(
                run_dir=run_dir, slug=target.slug, attempt=attempt,
                outcome=outcome, html=declined_html,
                body_text=declined_text,
                requested_url=target.requested_url, final_url=final_url,
                title=title, provider=PROVIDER, identity=identity,
                detail=detail)
            declined_manifest.append(kept)
        return record, (payload if outcome == O.VALID else None)

    attempt_dir = run_dir / target.slug / ("attempt-%02d" % attempt)
    attempt_dir.mkdir(parents=True, exist_ok=True)

    fetched = fetch(target.requested_url)
    if fetched.status != 200 or not fetched.body:
        return finish(_outcome_for_status(fetched.status),
                      detail=fetched.detail or ("status %s" % fetched.status),
                      final_url=fetched.final_url)

    bytes_moved = len(fetched.body)
    html = fetched.body.decode("utf-8", "replace")
    body_text = UC.html_to_text(html)
    declined_state["html"] = html
    declined_state["text"] = body_text
    title_match = re.search(r"<title[^>]*>(.*?)</title>", html,
                            re.IGNORECASE | re.DOTALL)
    title = MS.collapse(htmllib.unescape(title_match.group(1))
                        if title_match else "")
    canonical = MS.canonical_url(html)
    final_url = canonical or fetched.final_url or target.requested_url

    lowered = (title + " " + body_text[:4000]).lower()
    if any(marker in lowered for marker in UC.DENIAL_MARKERS):
        return finish(O.ACCESS_DENIED, final_url=final_url, title=title,
                      body_chars=len(MS.collapse(body_text)),
                      bytes_moved=bytes_moved,
                      detail="the origin served an interstitial, not the page")

    health = PS.page_health(title=title, body_text=body_text,
                            final_url=final_url,
                            expected_url=target.requested_url,
                            expected_property_code=target.property_code,
                            brand=target.identity_brand or brand)
    if health is not None:
        return finish(health, final_url=final_url, title=title,
                      body_chars=len(MS.collapse(body_text)),
                      bytes_moved=bytes_moved,
                      detail="rejected by the page-health gate")

    signals = PS.read_identity(html, final_url=final_url, title=title,
                               brand=target.identity_brand or brand)
    assessment = PS.assess_identity(
        signals, expected_name=target.hotel,
        expected_property_code=target.property_code,
        expected_url=target.requested_url,
        expected_postal_code=target.expected_postal_code,
        expected_street=target.expected_street,
        expected_phone=target.expected_phone,
        expected_locality=target.expected_locality)
    identity_block = {"signals": signals.to_dict(),
                      "confirmed": assessment.confirmed,
                      "matched": list(assessment.signals_matched),
                      "conflicting": list(assessment.signals_conflicting),
                      "reasons": list(assessment.reasons),
                      "binding": ("property_code" if target.property_code
                                  else "canonical_path_and_name"),
                      "binding_method": assessment.binding_method}
    if not assessment.confirmed:
        return finish(O.IDENTITY_MISMATCH, final_url=final_url, title=title,
                      body_chars=len(MS.collapse(body_text)),
                      bytes_moved=bytes_moved, identity=identity_block,
                      detail="; ".join(assessment.reasons))

    hit = UC.locate_policy_in_html(html)
    if not hit.found:
        # Before calling a page silent, check that it is a page at all. A
        # document whose policy region is still an unrendered template says
        # nothing about the hotel; it says this lane cannot render it, and the
        # ladder has an outcome for that which escalates instead of closing.
        token = policy_region_is_a_template(html)
        if token:
            return finish(O.UNHYDRATED, final_url=final_url, title=title,
                          body_chars=len(MS.collapse(body_text)),
                          bytes_moved=bytes_moved, identity=identity_block,
                          detail="the policy region of the served document is "
                                 "an unrendered client-side template (%r); "
                                 "this lane fetched the template, not the "
                                 "render" % token)
        return finish(O.POLICY_NOT_FOUND, final_url=final_url, title=title,
                      body_chars=len(MS.collapse(body_text)),
                      bytes_moved=bytes_moved, identity=identity_block,
                      detail="no bounded policy block in a page that served; "
                             "%d signal candidates considered"
                             % hit.candidates_considered)
    interactions.add("located the policy block via %s" % hit.strategy)

    reading = PR.parse(hit.text, strategy=hit.strategy)
    if not reading.found:
        return finish(O.POLICY_NOT_FOUND, final_url=final_url, title=title,
                      body_chars=len(MS.collapse(body_text)),
                      bytes_moved=bytes_moved, identity=identity_block,
                      detail="the located block was empty")

    try:
        artifacts = UC._persist(attempt_dir=attempt_dir, html=html,
                                body_text=body_text,
                                block_text=reading.block_text, hit=hit)
    except Exception as exc:                                     # noqa: BLE001
        return finish(O.CAPTURE_FAILED, final_url=final_url, title=title,
                      body_chars=len(MS.collapse(body_text)),
                      bytes_moved=bytes_moved, identity=identity_block,
                      detail="artifact persistence failed: %s: %s"
                             % (type(exc).__name__, exc))

    return finish(O.VALID, final_url=final_url, title=title,
                  body_chars=len(MS.collapse(body_text)),
                  bytes_moved=bytes_moved, identity=identity_block,
                  artifact_dir=str(attempt_dir),
                  payload={"reading": reading, "surface": hit,
                           "artifacts": artifacts, "disclosures_opened": [],
                           "provider": PROVIDER, "zone": ""})


async def capture_property(target: BC.CaptureTarget, *, run_dir: Path,
                           brand: str, max_attempts: int = DEFAULT_MAX_ATTEMPTS
                           ) -> Tuple[List[BC.AttemptRecord], Optional[Dict]]:
    """Up to ``max_attempts`` direct fetches, stopping at the first VALID."""
    records: List[BC.AttemptRecord] = []
    for attempt in range(1, max_attempts + 1):
        record, payload = await asyncio.to_thread(
            run_attempt, target, attempt, run_dir=run_dir, brand=brand)
        records.append(record)
        if record.outcome == O.VALID:
            return records, payload
        if not worth_retrying(record.outcome):
            return records, None
        if attempt < max_attempts:
            await asyncio.sleep(BC.RETRY_PAUSE_SECONDS)
    return records, None


__all__ = ["PROVIDER", "PROVIDER_ID", "USER_AGENT", "REQUEST_HEADERS",
           "TIMEOUT_SECONDS", "LANE_TERMINAL_OUTCOMES",
           "policy_region_is_a_template", "worth_retrying", "fetch",
           "run_attempt", "capture_property"]
