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

Routing
-------
Written unrouted, exactly like the Spider lane. Since then the decision tests
PTF-WYNDHAM-FIRECRAWL-DECISION-008, PTF-IHG-FIRECRAWL-DECISION-009 and
PTF-FIRECRAWL-CHOICE-VALIDATION-004 / CHOICE-ROUTE-CLOSURE-005 earned it the
Wyndham, IHG and Choice rows of ``routes.json``. Promotion was a decision with a
measurement behind it, not a side effect of an adapter existing.

Provenance (PTF-FACTORY-THROUGHPUT-HARDENING-001)
-------------------------------------------------
Every call is described by a deterministic request envelope -- the canonical
URL and the profile, nothing else -- and every result by a provenance block:
the requested and final URLs, the upstream status, the capture timestamp, the
sha256 of the returned document, the vendor's request id and its per-call
credit figure when the response carries them, and never a credential. Each
call is also appended to a local call ledger so a run's spend can be reconciled
against the credit delta rather than assumed from a per-row constant.
"""

from __future__ import annotations

import asyncio
import hashlib
import html as htmllib
import json
import os
import re
import sys
import time
import urllib.error
import urllib.request
from collections import OrderedDict
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.brightdata import browser_capture as BC       # noqa: E402
from scripts.pettripfinder.brightdata import declined_capture as DECLINED  # noqa: E402
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

#: The profile every measurement that justified routing to this lane actually
#: used: PTF-FIRECRAWL-HARD-LANES-003, PTF-FIRECRAWL-CHOICE-VALIDATION-004 and
#: PTF-CHOICE-READER-AND-ROUTE-CLOSURE-005. It differs from DEFAULT_PROFILE by
#: pinning the exit geography, which is not cosmetic -- an unpinned exit is how
#: the Marriott pilot got redirected to /es/default.mi.
#:
#: It lives here, in the adapter, so that the registered provider and the
#: benchmarks share ONE definition. Two copies would let the routed lane drift
#: away from the lane the decision was made about, silently.
ROUTED_PROFILE: Dict = {"formats": ["rawHtml"], "waitFor": 6000,
                        "timeout": 90000, "location": {"country": "US"}}

REQUEST_TIMEOUT_SECONDS = 180


class FirecrawlError(RuntimeError):
    """The API refused or returned something unusable."""


class FirecrawlAllEnginesFailed(FirecrawlError):
    """The vendor's own SCRAPE_ALL_ENGINES_FAILED.

    Its own class because it is a CAPABILITY statement, not a transient error:
    Firecrawl is saying every engine it has was refused by this origin. A retry
    buys the same answer, and an interaction pass cannot interact with a page
    that never arrived.
    """


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
        detail = ""
        try:
            detail = exc.read().decode("utf-8", "replace")
        except Exception:                                        # noqa: BLE001
            pass
        code = ""
        try:
            code = str(json.loads(detail).get("code") or "")
        except Exception:                                        # noqa: BLE001
            pass
        if code == "SCRAPE_ALL_ENGINES_FAILED":
            raise FirecrawlAllEnginesFailed(
                "SCRAPE_ALL_ENGINES_FAILED: every Firecrawl engine was refused "
                "by this origin")
        raise FirecrawlError("HTTP %d%s: %s"
                             % (exc.code, (" %s" % code) if code else "",
                                redact(detail or str(exc))[:200]))
    try:
        return json.loads(raw)
    except ValueError:
        raise FirecrawlError("non-JSON response: %s" % redact(raw)[:200])


def credits_remaining() -> Optional[int]:
    try:
        payload = _request(CREDITS_URL, timeout=45)
        return int((payload.get("data") or {}).get("remaining_credits"))
    except Exception:                                            # noqa: BLE001
        return None


#: Where every Firecrawl call is appended, one JSON line each. Under the
#: gitignored data tree; ``RECORD_CALLS`` lets a test switch it off.
CALL_LEDGER_PATH = _REPO_ROOT / "data" / "acquisition" / "firecrawl_call_ledger.jsonl"
RECORD_CALLS = True
#: The retry ceiling per URL, shared with every other lane.
MAX_ATTEMPTS_PER_URL = BC.MAX_ATTEMPTS


def request_envelope(url: str, *, profile: Optional[Dict] = None) -> Dict:
    """The deterministic description of one call: the canonical URL and the
    profile, sorted, with a sha256 over exactly that. Two calls with the same
    envelope are the same request, whatever else was going on."""
    body = dict(profile or DEFAULT_PROFILE)
    body["url"] = url
    canonical = json.dumps(body, sort_keys=True, separators=(",", ":"))
    return {"provider": PROVIDER, "api": API_URL, "body": body,
            "envelope_sha256": hashlib.sha256(canonical.encode("utf-8")).hexdigest()}


def provenance(*, requested_url: str, result: Mapping, envelope: Mapping,
               captured_at: str) -> Dict:
    """The provenance block for one result. No credential can appear: every
    string that came from the vendor passed through ``redact``."""
    html = result.get("html") or ""
    return OrderedDict((
        ("provider", PROVIDER),
        ("requested_url", requested_url),
        ("final_url", result.get("final_url") or requested_url),
        ("status", result.get("status")),
        ("ok", bool(result.get("ok"))),
        ("captured_at", captured_at),
        ("content_sha256", hashlib.sha256(html.encode("utf-8")).hexdigest() if html else ""),
        ("content_bytes", len(html.encode("utf-8")) if html else 0),
        ("provider_request_id", redact(str(result.get("request_id") or ""))),
        ("credits_used", result.get("credits_used")),
        ("envelope_sha256", envelope.get("envelope_sha256", "")),
        ("error", redact(str(result.get("error") or ""))),
    ))


def _record_call(entry: Mapping) -> None:
    if not RECORD_CALLS:
        return
    try:
        CALL_LEDGER_PATH.parent.mkdir(parents=True, exist_ok=True)
        with open(CALL_LEDGER_PATH, "a", encoding="utf-8") as handle:
            handle.write(json.dumps(entry, sort_keys=True) + "\n")
    except OSError:                                              # noqa: BLE001
        pass


def fetch(url: str, *, profile: Optional[Dict] = None) -> Dict:
    """One Firecrawl scrape. Returns rendered HTML, the upstream status and
    the provenance of the call (under ``provenance``), and appends the call
    to the local ledger. The request goes out exactly as the envelope says."""
    envelope = request_envelope(url, profile=profile)
    captured_at = BC.utc_now_iso()
    try:
        payload = _request(API_URL, data=envelope["body"])
    except Exception as exc:                                     # noqa: BLE001
        _record_call({"provider": PROVIDER, "captured_at": captured_at,
                      "requested_url": url,
                      "envelope_sha256": envelope["envelope_sha256"],
                      "ok": False,
                      "error": redact("%s: %s" % (type(exc).__name__, exc))})
        raise
    if not payload.get("success"):
        result = {"html": "", "status": None, "ok": False,
                  "error": redact(str(payload.get("error") or "unspecified")),
                  "request_id": str(payload.get("id") or ""),
                  "credits_used": payload.get("creditsUsed")}
    else:
        data = payload.get("data") or {}
        metadata = data.get("metadata") or {}
        credits = metadata.get("creditsUsed")
        if credits is None:
            credits = payload.get("creditsUsed")
        result = {
            "html": data.get("rawHtml") or data.get("html") or "",
            "status": metadata.get("statusCode"),
            "ok": True,
            "error": redact(str(metadata.get("error") or "")),
            "final_url": metadata.get("sourceURL") or metadata.get("url") or url,
            "title": metadata.get("title") or "",
            "request_id": str(metadata.get("scrapeId") or payload.get("id") or ""),
            "credits_used": credits,
        }
    result["provenance"] = provenance(requested_url=url, result=result,
                                      envelope=envelope, captured_at=captured_at)
    _record_call(result["provenance"])
    return result


def run_attempt(target: BC.CaptureTarget, attempt: int, *, run_dir: Path,
                brand: str, profile: Optional[Dict] = None
                ) -> Tuple[BC.AttemptRecord, Optional[Dict]]:
    """One Firecrawl scrape, judged by exactly the unlocker lane's gates."""
    started = time.monotonic()
    started_at = BC.utc_now_iso()
    interactions = BC._Interactions()
    interactions.add("rendered via %s (waitFor=%sms)"
                     % (PROVIDER, (profile or DEFAULT_PROFILE).get("waitFor")))
    # Set once the document actually arrives, and read by ``finish`` when the
    # capture is then declined. A dict rather than a closure variable for the
    # same reason ``direct_http_capture`` uses one: ``finish`` is defined before
    # the document exists and must not need rebinding.
    declined_state: Dict[str, str] = {"html": "", "text": ""}

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
        if outcome != O.VALID and declined_state["html"]:
            # The document reached us and was then declined. Keeping it is what
            # makes "this page states no pet policy" FALSIFIABLE: a decline that
            # persists nothing is an assertion nobody can check, which is the
            # defect PTF-MILWAUKEE-CLOSURE-ASSESSMENT-031 found on three
            # properties whose full policy was in the document all along.
            #
            # This lane had no such persistence until PTF-ST-LOUIS-PAID-
            # ACQUISITION-002, so its declines were exactly the assertions 031
            # ruled out -- the free lane preserved 49 documents in the same
            # market while this one preserved none. The judgement is unchanged;
            # only the audit trail is added.
            DECLINED.keep(
                run_dir=run_dir, slug=target.slug, attempt=attempt,
                outcome=outcome, html=declined_state["html"],
                body_text=declined_state["text"],
                requested_url=target.requested_url, final_url=final_url,
                title=title, provider=PROVIDER, identity=identity,
                detail=redact(detail))
        return record, (payload if outcome == O.VALID else None)

    attempt_dir = run_dir / target.slug / ("attempt-%02d" % attempt)
    attempt_dir.mkdir(parents=True, exist_ok=True)

    try:
        result = fetch(target.requested_url, profile=profile)
    except FirecrawlAllEnginesFailed as exc:
        return finish(O.ACCESS_DENIED, detail="ALL_ENGINES_FAILED: %s" % exc)
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
    # From here on a document exists, so every outcome below is a DECLINE of
    # something we can keep. Set before the first gate, not after each one, so
    # a gate added later cannot forget to arm the audit trail.
    declined_state["html"] = html
    declined_state["text"] = body_text
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
                            brand=target.identity_brand or brand)
    if health is not None:
        return finish(health, final_url=final_url, title=title,
                      body_chars=len(MS.collapse(body_text)),
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
                                block_text=reading.block_text, hit=hit)
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


__all__ = ["PROVIDER", "KEY_ENV", "DEFAULT_PROFILE", "ROUTED_PROFILE",
           "FirecrawlError", "FirecrawlRateLimited", "FirecrawlAllEnginesFailed",
           "credential_present", "credits_remaining", "redact", "fetch",
           "request_envelope", "provenance", "CALL_LEDGER_PATH", "RECORD_CALLS",
           "MAX_ATTEMPTS_PER_URL", "run_attempt", "capture_property"]
