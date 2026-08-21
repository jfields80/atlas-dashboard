"""One Bright Data attempt against any brand's property page.

The Marriott capture in ``browser_capture`` is frozen: it produced the
committed PTF-BRIGHTDATA-MARRIOTT-PILOT-001 report and changing how it decides
would change what that report means. This module is its brand-agnostic
sibling. It reuses that module's session handling, artifact persistence,
blank-crop refusal and outcome vocabulary wholesale, and swaps only the three
things that were Marriott-shaped: the health gate, the identity read, and the
policy locator.

WHAT CHANGES FOR A BRAND NOBODY WROTE A SCRAPER FOR
---------------------------------------------------
* HYDRATION. Marriott's policy is in the server-rendered DOM, so waiting for
  one known selector was enough. Half of this pilot's brands render the policy
  from JavaScript, so the wait is for a POLICY SIGNAL PHRASE to appear in the
  page's text -- a condition that is true of every brand and specific to none.
* DISCLOSURE. Several brands keep the policy inside an accordion or a tab.
  The page is prodded before it is read, and every control opened is recorded.
* IDENTITY. Marriott puts a property code in every URL. Some brands do not, so
  the binding falls back to the property's own path plus its own name, and the
  attempt records WHICH binding it used rather than implying they are equal.

Everything else is unchanged, including the rule that matters most: exactly one
outcome per attempt, and only ``VALID`` may write an artifact.
"""

from __future__ import annotations

import asyncio
import sys
import time
from pathlib import Path
from typing import Dict, List, Optional, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.brightdata import browser_capture as BC   # noqa: E402
from scripts.pettripfinder.brightdata import client                  # noqa: E402
from scripts.pettripfinder.brightdata import marriott_surface as MS  # noqa: E402
from scripts.pettripfinder.brightdata import outcomes as O           # noqa: E402
from scripts.pettripfinder.brightdata import policy_reading as PR    # noqa: E402
from scripts.pettripfinder.brightdata import policy_surface as PS    # noqa: E402

#: How long to wait for a policy signal phrase to appear anywhere in the page.
#: Longer than the Marriott wait because a client-rendered brand may fetch its
#: policy panel after first paint.
SIGNAL_WAIT_MS = 45_000

#: Wait for the page's own text to name a policy act. Generic by construction:
#: it asks whether the page is talking about its pet policy yet, not whether a
#: particular brand's div has mounted.
_SIGNAL_SCRIPT = """
(phrases) => {
    const text = (document.body ? document.body.innerText || '' : '').toLowerCase();
    return phrases.some((p) => text.includes(p));
}
"""


async def run_attempt(target: BC.CaptureTarget, attempt: int, *,
                      run_dir: Path, brand: str
                      ) -> Tuple[BC.AttemptRecord, Optional[Dict]]:
    """One fresh, US-pinned Bright Data session against one property."""
    from playwright.async_api import async_playwright

    started = time.monotonic()
    started_at = BC.utc_now_iso()
    interactions = BC._Interactions()
    network: Dict = {"available": False, "requests": 0, "encoded_bytes": 0,
                     "note": "not attached"}

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
            title=title, body_chars=body_chars, detail=client.redact(detail),
            interactions=interactions.snapshot(), identity=identity,
            network=BC.NetworkUsage(
                available=bool(network.get("available")),
                requests=int(network.get("requests") or 0),
                encoded_bytes=int(network.get("encoded_bytes") or 0),
                note=str(network.get("note") or "")).to_dict(),
            artifact_dir=artifact_dir)
        return record, (payload if outcome == O.VALID else None)

    try:
        endpoint = client.browser_endpoint(country=client.DEFAULT_COUNTRY)
    except client.BrightDataCredentialError as exc:
        return finish(O.NAVIGATION_FAILED, detail=str(exc))

    try:
        async with async_playwright() as playwright:
            browser = await playwright.chromium.connect_over_cdp(
                endpoint, timeout=BC.CONNECT_TIMEOUT_MS)
            interactions.add("opened a fresh US-pinned Bright Data session")
            try:
                context = (browser.contexts[0] if browser.contexts
                           else await browser.new_context())
                page = await context.new_page()
                _, network = await BC._measure_network(context, page)

                try:
                    await page.goto(target.requested_url,
                                    wait_until="domcontentloaded",
                                    timeout=BC.NAVIGATION_TIMEOUT_MS)
                    interactions.add("navigated to the requested property URL")
                except Exception as exc:                        # noqa: BLE001
                    return finish(O.NAVIGATION_FAILED,
                                  detail="%s: %s" % (type(exc).__name__, exc))

                try:
                    await page.wait_for_function(
                        _SIGNAL_SCRIPT, arg=list(PS.SIGNAL_PHRASES),
                        timeout=SIGNAL_WAIT_MS)
                    interactions.add("a pet-policy signal phrase appeared in "
                                     "the rendered text")
                except Exception:                               # noqa: BLE001
                    interactions.add("no pet-policy signal phrase within %d ms; "
                                     "continued to disclosure and the health "
                                     "gate" % SIGNAL_WAIT_MS)
                await page.wait_for_timeout(BC.SETTLE_MS)

                opened = await PS.expand_disclosures(page)
                for control in opened:
                    interactions.add("expanded %s" % control)
                if opened:
                    await page.wait_for_timeout(BC.SETTLE_MS)

                title = ""
                body_text = ""
                try:
                    title = (await page.title() or "").strip()
                except Exception:                               # noqa: BLE001
                    title = ""
                try:
                    body_text = await page.locator("body").inner_text(
                        timeout=30_000)
                except Exception:                               # noqa: BLE001
                    body_text = ""
                final_url = page.url

                health = PS.page_health(
                    title=title, body_text=body_text, final_url=final_url,
                    expected_url=target.requested_url,
                    expected_property_code=target.property_code,
                    brand=target.identity_brand or brand)
                if health is not None:
                    return finish(health, final_url=final_url, title=title,
                                  body_chars=len(MS.collapse(body_text)),
                                  detail="rejected by the page-health gate")

                try:
                    html = await page.content()
                except Exception as exc:                        # noqa: BLE001
                    return finish(O.CAPTURE_FAILED, final_url=final_url,
                                  title=title,
                                  body_chars=len(MS.collapse(body_text)),
                                  detail="could not read the hydrated DOM: %s: %s"
                                         % (type(exc).__name__, exc))

                signals = PS.read_identity(html, final_url=final_url,
                                           title=title,
                                           brand=target.identity_brand or brand)
                assessment = PS.assess_identity(
                    signals, expected_name=target.hotel,
                    expected_property_code=target.property_code,
                    expected_url=target.requested_url,
                    expected_postal_code=target.expected_postal_code,
                    expected_street=target.expected_street,
                    expected_phone=target.expected_phone,
                    expected_locality=target.expected_locality)
                identity_block = {
                    "signals": signals.to_dict(),
                    "confirmed": assessment.confirmed,
                    "matched": list(assessment.signals_matched),
                    "conflicting": list(assessment.signals_conflicting),
                    "reasons": list(assessment.reasons),
                    "binding": ("property_code" if target.property_code
                                else "canonical_path_and_name"),
                    "binding_method": assessment.binding_method,
                }
                if not assessment.confirmed:
                    return finish(O.IDENTITY_MISMATCH, final_url=final_url,
                                  title=title,
                                  body_chars=len(MS.collapse(body_text)),
                                  identity=identity_block,
                                  detail="; ".join(assessment.reasons))

                hit = await PS.locate_policy(page, brand=brand)
                if not hit.found:
                    return finish(O.POLICY_NOT_FOUND, final_url=final_url,
                                  title=title,
                                  body_chars=len(MS.collapse(body_text)),
                                  identity=identity_block,
                                  detail="no bounded policy container on a page "
                                         "that otherwise rendered; %d signal "
                                         "candidates were considered"
                                         % hit.candidates_considered)
                interactions.add("located the policy container via %s"
                                 % hit.strategy)

                reading = PR.parse(hit.text, strategy=hit.strategy)
                if not reading.found:
                    return finish(O.POLICY_NOT_FOUND, final_url=final_url,
                                  title=title,
                                  body_chars=len(MS.collapse(body_text)),
                                  identity=identity_block,
                                  detail="the located container was empty")

                element = await PS.locate_element(page, hit)
                try:
                    persisted = await BC._persist(
                        run_dir=run_dir, target=target, attempt=attempt,
                        page=page, policy_locator=element, html=html,
                        body_text=body_text, block_text=reading.block_text,
                        interactions=interactions, hit=hit)
                except Exception as exc:                        # noqa: BLE001
                    return finish(O.CAPTURE_FAILED, final_url=final_url,
                                  title=title,
                                  body_chars=len(MS.collapse(body_text)),
                                  identity=identity_block,
                                  detail="artifact persistence failed: %s: %s"
                                         % (type(exc).__name__, exc))

                return finish(O.VALID, final_url=final_url, title=title,
                              body_chars=len(MS.collapse(body_text)),
                              identity=identity_block,
                              artifact_dir=persisted["attempt_dir"],
                              payload={"reading": reading,
                                       "surface": hit,
                                       "artifacts": persisted,
                                       "disclosures_opened": list(opened)})
            finally:
                try:
                    await browser.close()
                except Exception:                               # noqa: BLE001
                    pass
    except Exception as exc:                                    # noqa: BLE001
        return finish(O.NAVIGATION_FAILED,
                      detail="session failed: %s: %s"
                             % (type(exc).__name__, exc))


async def capture_property(target: BC.CaptureTarget, *, run_dir: Path,
                           brand: str, max_attempts: int = BC.MAX_ATTEMPTS
                           ) -> Tuple[List[BC.AttemptRecord], Optional[Dict]]:
    """Up to ``max_attempts`` fresh sessions, stopping at the first VALID.

    Identical contract to the Marriott capture: a failed attempt is recorded
    and never ends the batch, and a property whose attempts all fail returns
    ``None`` so the caller records CLAUDE_FALLBACK_REQUIRED rather than
    softening a failure into evidence.
    """
    records: List[BC.AttemptRecord] = []
    for attempt in range(1, max_attempts + 1):
        record, payload = await run_attempt(target, attempt, run_dir=run_dir,
                                            brand=brand)
        records.append(record)
        if record.outcome == O.VALID:
            return records, payload
        if not O.worth_retrying(record.outcome):
            # The page answered, and a fresh session re-fetches the same page.
            # Retrying an identity mismatch or a policy silence buys the same
            # answer at full price.
            return records, None
        if attempt < max_attempts:
            await asyncio.sleep(BC.RETRY_PAUSE_SECONDS)
    return records, None


__all__ = ["SIGNAL_WAIT_MS", "run_attempt", "capture_property"]
