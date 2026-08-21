"""PTF-SPIDER-BENCHMARK-001 -- a Spider (spider.cloud) acquisition lane.

Why this module is almost empty
------------------------------
A provider benchmark is only worth reading if the ONLY thing that differs is
the provider. So this module owns exactly one thing -- turning a URL into HTML
via Spider's API -- and borrows every downstream step from the Web Unlocker
lane that the pilots already measured:

    denial markers, page-health gate, identity reading and assessment,
    policy-block location, the schema-1.2 reading, artifact persistence,
    and the retry rule.

If Spider's numbers differ from Bright Data's, that difference is the fetch,
because nothing else is allowed to vary. A lane that brought its own reader
would be comparing two pipelines and calling it a comparison of two vendors.

What Spider is
--------------
A crawl API that returns raw HTML and reports its OWN per-request cost, which
is better telemetry than a zone delta: no inference, no lag, no top-up
confusion. ``costs.total_cost`` is dollars for that one request.

Not registered on any route
---------------------------
This lane is implemented and available, and ``routes.json`` is untouched, so
nothing routes to it. The proven route table is not edited by a benchmark;
promoting Spider onto a lane would be a separate, measured decision.
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

PROVIDER = "Spider Cloud"
API_URL = "https://api.spider.cloud/crawl"
CREDITS_URL = "https://api.spider.cloud/data/credits"
KEY_ENV = "SPIDER_API_KEY"

#: The request profile. ``chrome`` renders JavaScript and the proxy/stealth
#: flags are Spider's anti-bot path -- the fair comparison against an unlocker,
#: which is an anti-bot product. Measured, not assumed: see the benchmark.
DEFAULT_REQUEST: Dict = {"request": "chrome", "proxy_enabled": True,
                         "stealth": True, "return_format": "raw", "limit": 1}

REQUEST_TIMEOUT_SECONDS = 120


class SpiderError(RuntimeError):
    """The API refused or returned something unusable."""


def credential_present() -> bool:
    return bool((os.environ.get(KEY_ENV) or "").strip())


def redact(text: str) -> str:
    """Never let the key reach a log, a report or an artifact."""
    key = (os.environ.get(KEY_ENV) or "").strip()
    if key and text:
        return text.replace(key, "<redacted:spider-key>")
    return text


def _post(body: Dict, *, timeout: int = REQUEST_TIMEOUT_SECONDS) -> Dict:
    key = (os.environ.get(KEY_ENV) or "").strip()
    if not key:
        raise SpiderError("%s is not set" % KEY_ENV)
    request = urllib.request.Request(
        API_URL, data=json.dumps(body).encode("utf-8"),
        headers={"Authorization": "Bearer %s" % key,
                 "Content-Type": "application/json"})
    with urllib.request.urlopen(request, timeout=timeout) as response:
        raw = response.read().decode("utf-8", "replace")
    try:
        data = json.loads(raw)
    except ValueError:
        raise SpiderError("non-JSON response: %s" % redact(raw[:200]))
    rows = data if isinstance(data, list) else [data]
    if not rows:
        raise SpiderError("empty response")
    return rows[0]


def credits_remaining() -> Optional[float]:
    """Prepaid credits, or None when unreadable."""
    key = (os.environ.get(KEY_ENV) or "").strip()
    if not key:
        return None
    request = urllib.request.Request(
        CREDITS_URL, headers={"Authorization": "Bearer %s" % key})
    try:
        with urllib.request.urlopen(request, timeout=45) as response:
            data = json.loads(response.read().decode("utf-8", "replace"))
        return float((data.get("data") or {}).get("credits"))
    except Exception:                                            # noqa: BLE001
        return None


def fetch(url: str, *, profile: Optional[Dict] = None) -> Dict:
    """One Spider request. Returns html, status and the vendor's own cost."""
    body = dict(profile or DEFAULT_REQUEST)
    body["url"] = url
    row = _post(body)
    costs = row.get("costs") or {}
    return {
        "html": row.get("content") or "",
        "status": row.get("status"),
        "error": redact(str(row.get("error") or "")),
        "reported_usd": float(costs.get("total_cost") or 0.0),
        "cost_breakdown": {k: v for k, v in costs.items()
                           if not k.endswith("_formatted")},
        "duration_ms": row.get("duration_elasped_ms"),
        "final_url": row.get("url") or url,
    }


def run_attempt(target: BC.CaptureTarget, attempt: int, *, run_dir: Path,
                brand: str, profile: Optional[Dict] = None
                ) -> Tuple[BC.AttemptRecord, Optional[Dict]]:
    """One Spider fetch, judged by exactly the gates the unlocker lane uses."""
    started = time.monotonic()
    started_at = BC.utc_now_iso()
    interactions = BC._Interactions()
    interactions.add("fetched via %s (%s)"
                     % (PROVIDER, (profile or DEFAULT_REQUEST).get("request")))

    reported_usd = 0.0

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
                available=True,
                note="Spider reports its own per-request cost: $%.6f"
                     % reported_usd).to_dict(),
            artifact_dir=artifact_dir)
        return record, (payload if outcome == O.VALID else None)

    attempt_dir = run_dir / target.slug / ("attempt-%02d" % attempt)
    attempt_dir.mkdir(parents=True, exist_ok=True)

    try:
        result = fetch(target.requested_url, profile=profile)
    except Exception as exc:                                     # noqa: BLE001
        return finish(O.NAVIGATION_FAILED,
                      detail="%s: %s" % (type(exc).__name__, redact(str(exc))))

    reported_usd = result["reported_usd"]
    html = result["html"]
    status = result["status"]

    if not html:
        outcome = (O.ACCESS_DENIED if status in (401, 403, 429)
                   else O.BLANK_PAGE if status == 200
                   else O.NAVIGATION_FAILED)
        return finish(outcome, final_url=result["final_url"],
                      detail="status %s, no content (%s)"
                             % (status, result["error"] or "no error given"))

    body_text = UC.html_to_text(html)
    match = re.search(r"<title[^>]*>(.*?)</title>", html,
                      re.IGNORECASE | re.DOTALL)
    title = MS.collapse(htmllib.unescape(match.group(1)) if match else "")
    final_url = MS.canonical_url(html) or result["final_url"]

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
                           "provider": PROVIDER,
                           "reported_usd": reported_usd,
                           "cost_breakdown": result["cost_breakdown"],
                           "duration_ms": result["duration_ms"]})


async def capture_property(target: BC.CaptureTarget, *, run_dir: Path,
                           brand: str, max_attempts: int = BC.MAX_ATTEMPTS,
                           profile: Optional[Dict] = None
                           ) -> Tuple[List[BC.AttemptRecord], Optional[Dict]]:
    """Up to ``max_attempts`` Spider fetches, stopping at the first VALID.

    The retry rule is the unlocker's, unchanged: a page that ANSWERED is not
    re-fetched. Retrying an identity mismatch or a policy silence buys the same
    answer at full price.
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


__all__ = ["PROVIDER", "KEY_ENV", "DEFAULT_REQUEST", "SpiderError",
           "credential_present", "credits_remaining", "redact", "fetch",
           "run_attempt", "capture_property"]
