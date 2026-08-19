"""PTF-FIRECRAWL-BENCHMARK-002 -- a Firecrawl acquisition lane.

Structurally identical to ``spider_capture``: this module owns one thing --
turning a URL into HTML -- and borrows every downstream step from the Web
Unlocker lane the pilots already measured. Only the fetch differs, so any
difference in the result is the fetch.

Why Firecrawl is not just another fetcher
-----------------------------------------
Spider failed this corpus for a specific reason: it returned the JavaScript
SHELL. Wyndham came back HTTP 200 at 176KB with ``div.policy-items.pet-policy``
absent from the document entirely. Firecrawl renders the page in a real browser
before returning it, so the question this lane exists to answer is narrow and
concrete: does the hydrated node arrive?

``waitFor`` is set deliberately. These pages paint their policy after the
initial load, and a renderer that returns at DOMContentLoaded is a shell
renderer with extra steps.

Cost
----
Firecrawl bills in plan CREDITS, not per-request dollars, and does not report a
cost on the response. Credits are read from the account before and after a run,
which makes the figure a measured delta rather than an estimate -- but it is
credits, and converting it to dollars depends on a plan this module does not
know. It reports credits and says so.

Not registered on any route
---------------------------
Implemented and deliberately unrouted, exactly like the Spider lane.
``routes.json`` is untouched. Promotion is a decision with a measurement behind
it, not a side effect of an adapter existing.
"""

from __future__ import annotations

import asyncio
import html as htmllib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path
from typing import Dict, List, Optional, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.brightdata import browser_capture as BC       # noqa: E402
from scripts.pettripfinder.brightdata import marriott_surface as MS      # noqa: E402
from scripts.pettripfinder.brightdata import outcomes as O               # noqa: E402
from scripts.pettripfinder.brightdata import policy_reading as PR        # noqa: E402
from scripts.pettripfinder.brightdata import policy_surface as PS        # noqa: E402
from scripts.pettripfinder.brightdata import unlocker_capture as UC      # noqa: E402

PROVIDER = "Firecrawl"
API_URL = "https://api.firecrawl.dev/v1/scrape"
CREDITS_URL = "https://api.firecrawl.dev/v1/team/credit-usage"
KEY_ENV = "FIRECRAWL_API_KEY"

#: Raw HTML because every downstream gate in this pipeline reads HTML, and a
#: markdown conversion would silently drop the class names the brand locators
#: key on. ``waitFor`` is the whole point of choosing this vendor.
DEFAULT_PROFILE: Dict = {"formats": ["rawHtml"], "waitFor": 6000,
                         "timeout": 90000}

REQUEST_TIMEOUT_SECONDS = 180


class FirecrawlError(RuntimeError):
    """The API refused or returned something unusable."""


class FirecrawlRateLimited(FirecrawlError):
    """HTTP 429.

    Kept as its own class because a rate limit is a PLAN constraint, not a
    capability failure. Folding it into NAVIGATION_FAILED would report a lane
    as unable to reach pages it reaches perfectly well when paced, which is
    exactly the wrong conclusion to hand a vendor decision.
    """


def credential_present() -> bool:
    return bool((os.environ.get(KEY_ENV) or "").strip())


def redact(text: str) -> str:
    key = (os.environ.get(KEY_ENV) or "").strip()
    if key and text:
        return text.replace(key, "<redacted:firecrawl-key>")
    return text


def _request(url: str, *, data: Optional[Dict] = None,
             timeout: int = REQUEST_TIMEOUT_SECONDS) -> Dict:
    key = (os.environ.get(KEY_ENV) or "").strip()
    if not key:
        raise FirecrawlError("%s is not set" % KEY_ENV)
    body = json.dumps(data).encode("utf-8") if data is not None else None
    request = urllib.request.Request(
        url, data=body,
        headers={"Authorization": "Bearer %s" % key,
                 "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            raw = response.read().decode("utf-8", "replace")
    except urllib.error.HTTPError as exc:
        if exc.code == 429:
            raise FirecrawlRateLimited("rate limited (HTTP 429)")
        raise FirecrawlError("HTTP %d: %s" % (exc.code, redact(str(exc))))
    try:
        return json.loads(raw)
    except ValueError:
        raise FirecrawlError("non-JSON response: %s" % redact(raw[:200]))


def credits_remaining() -> Optional[int]:
    try:
        payload = _request(CREDITS_URL, timeout=45)
        return int((payload.get("data") or {}).get("remaining_credits"))
    except Exception:                                            # noqa: BLE001
        return None


def fetch(url: str, *, profile: Optional[Dict] = None) -> Dict:
    """One Firecrawl scrape. Returns rendered HTML and the upstream status."""
    body = dict(profile or DEFAULT_PROFILE)
    body["url"] = url
    payload = _request(API_URL, data=body)
    if not payload.get("success"):
        return {"html": "", "status": None, "ok": False,
                "error": redact(str(payload.get("error") or "unspecified"))}
    data = payload.get("data") or {}
    metadata = data.get("metadata") or {}
    return {
        "html": data.get("rawHtml") or data.get("html") or "",
        "status": metadata.get("statusCode"),
        "ok": True,
        "error": redact(str(metadata.get("error") or "")),
        "final_url": metadata.get("sourceURL") or metadata.get("url") or url,
        "title": metadata.get("title") or "",
    }


def run_attempt(target: BC.CaptureTarget, attempt: int, *, run_dir: Path,
                brand: str, profile: Optional[Dict] = None
                ) -> Tuple[BC.AttemptRecord, Optional[Dict]]:
    """One Firecrawl scrape, judged by exactly the unlocker lane's gates."""
    started = time.monotonic()
    started_at = BC.utc_now_iso()
    interactions = BC._Interactions()
    interactions.add("rendered via %s (waitFor=%sms)"
                     % (PROVIDER, (profile or DEFAULT_PROFILE).get("waitFor")))

    def finish(outcome: str, *, detail: str = "", final_url: str = "",
               title: str = "", body_chars: int = 0,
               identity: Optional[Dict] = None, artifact_dir: str = "",
               payload: Optional[Dict] = None
               ) -> Tuple[BC.AttemptRecord, Optional[Dict]]:
        record = BC.AttemptRecord(
            attempt=attempt, outcome=outcome, started_at=started_at,
            ended_at=BC.utc_now_iso(),
            elapsed_seconds=time.monotonic() - started,
            requested_url=target.requested_url, final_url=final_url,
            title=title, body_chars=body_chars, detail=redact(detail),
            interactions=interactions.snapshot(), identity=identity,
            network=BC.NetworkUsage(
                available=False,
                note="Firecrawl bills in plan credits and reports no "
                     "per-request cost; spend is the credit delta over a "
                     "run").to_dict(),
            artifact_dir=artifact_dir)
        return record, (payload if outcome == O.VALID else None)

    attempt_dir = run_dir / target.slug / ("attempt-%02d" % attempt)
    attempt_dir.mkdir(parents=True, exist_ok=True)

    try:
        result = fetch(target.requested_url, profile=profile)
    except FirecrawlRateLimited:
        # ACCESS_DENIED rather than NAVIGATION_FAILED: the request was refused,
        # not lost, and the retry rule treats a refusal as worth retrying.
        return finish(O.ACCESS_DENIED,
                      detail="RATE_LIMITED: the plan's request limit was hit; "
                             "this is a quota result and says nothing about "
                             "whether the page is reachable")
    except Exception as exc:                                     # noqa: BLE001
        return finish(O.NAVIGATION_FAILED,
                      detail="%s: %s" % (type(exc).__name__, redact(str(exc))))

    html = result["html"]
    status = result["status"]

    if not result["ok"] or not html:
        outcome = (O.ACCESS_DENIED if status in (401, 403, 429)
                   else O.BLANK_PAGE if status == 200
                   else O.NAVIGATION_FAILED)
        return finish(outcome, final_url=result.get("final_url", ""),
                      detail="status %s: %s" % (status, result.get("error")
                                                or "no content"))

    body_text = UC.html_to_text(html)
    match = re.search(r"<title[^>]*>(.*?)</title>", html,
                      re.IGNORECASE | re.DOTALL)
    title = MS.collapse(htmllib.unescape(match.group(1)) if match
                        else result.get("title", ""))
    final_url = MS.canonical_url(html) or result.get("final_url") or target.requested_url

    if status in (401, 403, 429):
        return finish(O.ACCESS_DENIED, final_url=final_url, title=title,
                      body_chars=len(MS.collapse(body_text)),
                      detail="status %s" % status)

    lowered = (title + " " + body_text[:4000]).lower()
    if any(marker in lowered for marker in UC.DENIAL_MARKERS):
        return finish(O.ACCESS_DENIED, final_url=final_url, title=title,
                      body_chars=len(MS.collapse(body_text)),
                      detail="an interstitial was returned")

    health = PS.page_health(title=title, body_text=body_text,
                            final_url=final_url,
                            expected_url=target.requested_url,
                            expected_property_code=target.property_code,
                            brand=brand)
    if health is not None:
        return finish(health, final_url=final_url, title=title,
                      body_chars=len(MS.collapse(body_text)),
                      detail="rejected by the page-health gate")

    signals = PS.read_identity(html, final_url=final_url, title=title,
                               brand=brand)
    assessment = PS.assess_identity(
        signals, expected_name=target.hotel,
        expected_property_code=target.property_code,
        expected_url=target.requested_url,
        expected_postal_code=target.expected_postal_code)
    identity_block = {"signals": signals.to_dict(),
                      "confirmed": assessment.confirmed,
                      "matched": list(assessment.signals_matched),
                      "conflicting": list(assessment.signals_conflicting),
                      "reasons": list(assessment.reasons),
                      "binding": ("property_code" if target.property_code
                                  else "canonical_path_and_name")}
    if not assessment.confirmed:
        return finish(O.IDENTITY_MISMATCH, final_url=final_url, title=title,
                      body_chars=len(MS.collapse(body_text)),
                      identity=identity_block,
                      detail="; ".join(assessment.reasons))

    hit = UC.locate_policy_in_html(html)
    if not hit.found:
        return finish(O.POLICY_NOT_FOUND, final_url=final_url, title=title,
                      body_chars=len(MS.collapse(body_text)),
                      identity=identity_block,
                      detail="no bounded policy block in a page that rendered; "
                             "%d candidates considered" % hit.candidates_considered)
    interactions.add("located the policy block via %s" % hit.strategy)

    reading = PR.parse(hit.text, strategy=hit.strategy)
    if not reading.found:
        return finish(O.POLICY_NOT_FOUND, final_url=final_url, title=title,
                      body_chars=len(MS.collapse(body_text)),
                      identity=identity_block,
                      detail="the located block was empty")

    try:
        artifacts = UC._persist(attempt_dir=attempt_dir, html=html,
                                body_text=body_text,
                                block_text=reading.block_text)
    except Exception as exc:                                     # noqa: BLE001
        return finish(O.CAPTURE_FAILED, final_url=final_url, title=title,
                      body_chars=len(MS.collapse(body_text)),
                      identity=identity_block,
                      detail="artifact persistence failed: %s: %s"
                             % (type(exc).__name__, redact(str(exc))))

    return finish(O.VALID, final_url=final_url, title=title,
                  body_chars=len(MS.collapse(body_text)),
                  identity=identity_block, artifact_dir=str(attempt_dir),
                  payload={"reading": reading, "surface": hit,
                           "artifacts": artifacts, "disclosures_opened": [],
                           "provider": PROVIDER, "raw_bytes": len(html)})


async def capture_property(target: BC.CaptureTarget, *, run_dir: Path,
                           brand: str, max_attempts: int = BC.MAX_ATTEMPTS,
                           profile: Optional[Dict] = None
                           ) -> Tuple[List[BC.AttemptRecord], Optional[Dict]]:
    """Up to ``max_attempts`` scrapes, stopping at the first VALID.

    The unlocker's retry rule, unchanged: a page that ANSWERED is not
    re-fetched, because a second render buys the same answer at full price.
    """
    records: List[BC.AttemptRecord] = []
    for attempt in range(1, max_attempts + 1):
        record, payload = await asyncio.to_thread(
            run_attempt, target, attempt, run_dir=run_dir, brand=brand,
            profile=profile)
        records.append(record)
        if record.outcome == O.VALID:
            return records, payload
        if not O.worth_retrying(record.outcome):
            return records, None
        if attempt < max_attempts:
            await asyncio.sleep(BC.RETRY_PAUSE_SECONDS)
    return records, None


__all__ = ["PROVIDER", "KEY_ENV", "DEFAULT_PROFILE", "FirecrawlError",
           "FirecrawlRateLimited",
           "credential_present", "credits_remaining", "redact", "fetch",
           "run_attempt", "capture_property"]
