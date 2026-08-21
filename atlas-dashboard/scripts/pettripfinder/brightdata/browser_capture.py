"""One Bright Data attempt, start to finish, with an honest ending.

This is the only impure module in the package: it opens a session, drives a
page, and writes bytes. Everything it DECIDES it delegates to
``marriott_surface``, which is pure, so the judgement half of a capture can be
tested without spending a session.

ONE ATTEMPT IS ONE FRESH SESSION
--------------------------------
Every attempt connects, works, and closes. Nothing is reused between attempts,
because the failure this harness exists to survive is a bad session -- a blank
page, an identity shell that never hydrated -- and retrying inside the same
session retries the same bad session.

A property gets at most :data:`MAX_ATTEMPTS`. A failed attempt is recorded and
the batch continues; an exception inside one attempt can never end the run.
The single-page proof already demonstrated the behaviour worth keeping: it
rejected two bad sessions and accepted the third.

NAVIGATION SUCCESS IS NOT PAGE SUCCESS
--------------------------------------
``page.goto`` returning is worth nothing. A capture is VALID only when the page
is rendered, is on the first-party domain, is the property we asked for by its
own structured data, and carries a located pet-policy surface. Each of those
failing has its own outcome, and only VALID may write an artifact -- enforced
by :func:`outcomes.may_bear_evidence` guarding the write, not by remembering.

CREDENTIAL SAFETY
-----------------
Playwright puts the endpoint into the exception message when a connection
fails, so every string that reaches an attempt record passes through
``client.redact`` first. The endpoint itself is never printed, never stored,
and never passed anywhere except ``connect_over_cdp``.
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.brightdata import client                  # noqa: E402
from scripts.pettripfinder.brightdata import marriott_surface as MS  # noqa: E402
from scripts.pettripfinder.brightdata import policy_locator as PL   # noqa: E402
from scripts.pettripfinder.brightdata import outcomes as O           # noqa: E402

#: Three fresh sessions per property, then the property is handed to a human.
MAX_ATTEMPTS = 3

CONNECT_TIMEOUT_MS = 120_000
NAVIGATION_TIMEOUT_MS = 120_000
#: How long to wait for the policy container specifically. A Marriott overview
#: page that has not mounted it within this window is the "identity shell"
#: failure, which is a session to throw away rather than a page to wait on.
POLICY_WAIT_MS = 35_000
#: A short settle after the policy container appears, so lazily-mounted
#: siblings are in the screenshot rather than half-painted.
SETTLE_MS = 3_000
#: Screenshots get their own, longer budget. Playwright's 30 s default is not
#: enough for a full-page capture of a Marriott overview page over a remote
#: browser -- run 1 of this pilot lost an entire Bright Data session to
#: "Page.screenshot: Timeout 30000ms exceeded ... waiting for fonts to load",
#: which is a harness failure charged as a property retry.
SCREENSHOT_TIMEOUT_MS = 90_000
#: How long to let the page settle after scrolling the policy block into view.
#: Marriott's hotel-information section paints lazily: on run 1 the Dearborn
#: element crop came back a uniform white rectangle because the region had not
#: painted yet, and the file's mere existence was counted as a screenshot.
SCROLL_SETTLE_MS = 1_500
#: Seconds between attempts. Long enough that a retry is a new session rather
#: than the same rate-limit window.
RETRY_PAUSE_SECONDS = 4

#: Bandwidth optimisation is OFF for this baseline. The installed Bright Data
#: CLI exposes no ad/tracker-blocking switch for the Browser API, and blocking
#: assets by CDP interception during a FIRST benchmark risks changing what the
#: page renders -- which would make the evidence-quality question unanswerable.
#: Recorded in every manifest so a later run can be compared against it.
OPTIMIZATION_ENABLED = False
OPTIMIZATION_NOTE = (
    "no ad/tracker blocking. 'brightdata browser --help' (CLI 0.3.5) exposes "
    "no such switch, and CDP request interception during a baseline benchmark "
    "could alter policy hydration or strip identity context from a screenshot."
)

CAPTURE_ENGINE = "Bright Data Browser API"
AUTOMATION = "Playwright (chromium over CDP)"


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for chunk in iter(lambda: handle.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def utc_now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def image_is_blank(path: Path) -> Optional[bool]:
    """Whether a PNG is a single flat colour. ``None`` when undecidable.

    A blank crop is the failure mode that a file-existence check cannot see,
    and counting a uniform white rectangle as a policy screenshot is exactly
    the kind of artifact-census error this repository has made before (135
    screenshot directories holding zero images).

    Pillow is used when it is importable and this degrades to ``None``
    otherwise, because the pilot must not quietly add a runtime dependency to
    the AES-DEP-001 baseline.
    """
    try:
        from PIL import Image                                    # noqa: PLC0415
    except Exception:                                            # noqa: BLE001
        return None
    try:
        with Image.open(path) as image:
            low, high = image.convert("L").getextrema()
    except Exception:                                            # noqa: BLE001
        return None
    return low == high


# --------------------------------------------------------------------------- #
# Targets and records.
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class CaptureTarget:
    """One property to capture.

    Everything here is an INPUT -- a name, a URL, a code, and whatever the
    existing identity census already knows. No expected policy value appears in
    this structure, and none may: the benchmark lives in the pilot module and
    is compared to the capture only after the capture is finished.
    """

    slug: str
    hotel: str
    requested_url: str
    property_code: str
    market_id: str
    normalized_name: str
    identity_key: str = ""
    street_identity: str = ""
    expected_postal_code: str = ""
    expected_street: str = ""
    #: The census telephone line and the property's city/state. Both are
    #: identity INPUTS in the same sense as the name and the code: they say
    #: which building was asked for, never what it charges.
    expected_phone: str = ""
    expected_locality: str = ""
    #: The property's OWN brand, which is not the same thing as the brand whose
    #: locator will be tried. A route may read a coded brand with the generic
    #: walk -- Hyatt and Best Western both do -- and the capture then received
    #: an empty brand and re-derived the property code as empty while the
    #: expected code was a real one. Two concepts, two fields.
    identity_brand: str = ""
    census_matched: bool = False
    census_note: str = ""

    def hotel_ref(self) -> Dict[str, str]:
        ref = {"market_id": self.market_id,
               "canonical_name": self.hotel,
               "normalized_name": self.normalized_name,
               "official_url": self.requested_url,
               "property_code": self.property_code}
        if self.street_identity:
            ref["street_identity"] = self.street_identity
        return ref


@dataclass(frozen=True)
class NetworkUsage:
    """Bytes the browser reported moving, for an ESTIMATE and nothing more.

    This is CDP's view of encoded response sizes. It is not Bright Data
    billing, it does not include the proxy's own overhead, and it is labelled
    ESTIMATED everywhere it is reported.
    """

    available: bool
    requests: int = 0
    encoded_bytes: int = 0
    note: str = ""

    def to_dict(self) -> Dict:
        return {"available": self.available, "requests": self.requests,
                "encoded_bytes": self.encoded_bytes,
                "measurement": "CDP Network.loadingFinished encodedDataLength",
                "is_brightdata_billing": False, "note": self.note}


@dataclass(frozen=True)
class AttemptRecord:
    """What one attempt did. Exactly one outcome, always."""

    attempt: int
    outcome: str
    started_at: str
    ended_at: str
    elapsed_seconds: float
    requested_url: str
    final_url: str = ""
    title: str = ""
    body_chars: int = 0
    detail: str = ""
    interactions: Tuple[str, ...] = ()
    identity: Optional[Dict] = None
    network: Optional[Dict] = None
    artifact_dir: str = ""

    def to_dict(self) -> Dict:
        return {
            "attempt": self.attempt,
            "outcome": self.outcome,
            "started_at": self.started_at,
            "ended_at": self.ended_at,
            "elapsed_seconds": round(self.elapsed_seconds, 3),
            "requested_url": self.requested_url,
            "final_url": self.final_url,
            "title": self.title,
            "body_chars": self.body_chars,
            "detail": self.detail,
            "interactions": list(self.interactions),
            "identity": self.identity,
            "network": self.network,
            "artifact_dir": self.artifact_dir,
            "may_bear_evidence": O.may_bear_evidence(self.outcome),
        }


class _Interactions:
    """An ordered record of what was done to the page, for the manifest."""

    def __init__(self) -> None:
        self._steps: List[str] = []

    def add(self, step: str) -> None:
        self._steps.append(step)

    def snapshot(self) -> Tuple[str, ...]:
        return tuple(self._steps)


# --------------------------------------------------------------------------- #
# Exit geography.
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class GeoProbe:
    """What country a Bright Data session actually exits from.

    Asked rather than assumed. Setting ``-country-us`` on the username is a
    REQUEST; this reads Bright Data's own geolocation echo and reports what was
    granted, because an unpinned exit is what produced a Spanish brand
    homepage in the previous pilot and a request nobody verified would have
    left that failure mode in place while looking fixed.
    """

    ok: bool
    country: str = ""
    expected: str = ""
    detail: str = ""
    raw: Optional[Dict] = None

    def to_dict(self) -> Dict:
        return {"ok": self.ok, "country": self.country,
                "expected": self.expected, "detail": self.detail,
                "probe_url": client.GEO_PROBE_URL, "raw": self.raw}


async def probe_exit_country(*, expected: str = client.DEFAULT_COUNTRY,
                             reads: int = 3, max_sessions: int = 6) -> GeoProbe:
    """Open sessions until ``reads`` of them report their exit country.

    Two rules, and they pull in opposite directions on purpose:

    * a session that never connected tells us nothing about geography, so a
      transient ``ERR_TUNNEL_CONNECTION_FAILED`` is RETRIED rather than
      counted as a foreign exit;
    * every session that DOES report must agree. One US exit out of three
      proves nothing about the fourth, and an intermittently foreign exit is
      exactly the failure being guarded against.

    Failing to obtain ``reads`` successful reads within ``max_sessions`` is
    itself a FAIL: geography that cannot be established is not geography that
    may be assumed.
    """
    from playwright.async_api import async_playwright

    seen: List[str] = []
    errors: List[str] = []
    raw: Optional[Dict] = None
    try:
        endpoint = client.browser_endpoint(country=expected)
    except client.BrightDataCredentialError as exc:
        return GeoProbe(False, expected=expected, detail=str(exc))

    sessions = 0
    while len(seen) < reads and sessions < max_sessions:
        sessions += 1
        try:
            async with async_playwright() as playwright:
                browser = await playwright.chromium.connect_over_cdp(
                    endpoint, timeout=CONNECT_TIMEOUT_MS)
                try:
                    context = (browser.contexts[0] if browser.contexts
                               else await browser.new_context())
                    page = await context.new_page()
                    await page.goto(client.GEO_PROBE_URL,
                                    wait_until="domcontentloaded",
                                    timeout=NAVIGATION_TIMEOUT_MS)
                    body = await page.locator("body").inner_text(timeout=30_000)
                    payload = json.loads(body)
                    raw = payload if isinstance(payload, dict) else {"body": body}
                    country = str((raw.get("country")
                                   or (raw.get("geo") or {}).get("country")
                                   or "")).strip().lower()
                    seen.append(country or "<absent>")
                finally:
                    await browser.close()
        except Exception as exc:                                # noqa: BLE001
            errors.append(client.redact("%s: %s"
                                        % (type(exc).__name__, str(exc)[:120])))
        if len(seen) < reads:
            await asyncio.sleep(RETRY_PAUSE_SECONDS)

    unique = sorted(set(seen))
    enough = len(seen) >= reads
    agreed = unique == [expected.lower()]
    ok = enough and agreed
    if ok:
        detail = ("%d of %d sessions reported an exit country and all of them "
                  "were %r" % (len(seen), sessions, expected))
    elif not enough:
        detail = ("only %d of %d sessions reported an exit country (%s); "
                  "geography that cannot be established may not be assumed"
                  % (len(seen), sessions, "; ".join(errors[:3]) or "no detail"))
    else:
        detail = ("sessions exited from %s; every session must exit from %r "
                  "before a benchmark may run" % (unique, expected))
    return GeoProbe(ok=ok, country=",".join(unique) or "<none>",
                    expected=expected, raw=raw, detail=detail)


# --------------------------------------------------------------------------- #
# The attempt.
# --------------------------------------------------------------------------- #

async def _measure_network(context, page) -> Tuple[Optional[object], Dict]:
    """Attach a CDP network meter. Returns (session, totals) or (None, ...)."""
    totals = {"requests": 0, "encoded_bytes": 0, "available": True, "note": ""}
    try:
        session = await context.new_cdp_session(page)
        await session.send("Network.enable")

        def on_finished(event):
            totals["requests"] += 1
            try:
                totals["encoded_bytes"] += int(event.get("encodedDataLength") or 0)
            except (TypeError, ValueError):
                pass

        session.on("Network.loadingFinished", on_finished)
        return session, totals
    except Exception as exc:                                    # noqa: BLE001
        totals["available"] = False
        totals["note"] = client.redact("CDP metering unavailable: %s: %s"
                                       % (type(exc).__name__, exc))
        return None, totals


async def _locate_policy_block(page, interactions: _Interactions):
    """Find the bounded pet-policy container. Returns (locator_id, element,
    text) or (``""``, None, ``""``).

    Tried in the order declared in ``marriott_surface.POLICY_LOCATORS``: the
    structural heading-parent first, the icon block as template-drift
    fallbacks.
    """
    for locator_id, selector in MS.POLICY_LOCATORS:
        try:
            locator = page.locator(selector).first
            if await locator.count() == 0:
                continue
            text = await locator.inner_text(timeout=10_000)
        except Exception:                                       # noqa: BLE001
            continue
        if MS.collapse(text):
            interactions.add("located policy container via %s" % locator_id)
            return locator_id, locator, text
    return "", None, ""


async def _identity_visible_with(page, name: str) -> bool:
    """Whether the hotel's name is on screen at the current scroll position.

    Answers the work order's screenshot question mechanically instead of by
    eye. Reported alongside :func:`_policy_visible`, because on run 1 this
    returned True for a property whose page had not scrolled at all -- the
    name was visible in the masthead and the policy was two thousand pixels
    below it, and "identity visible" on its own read as though one frame had
    carried both.
    """
    script = """(name) => {
        const target = String(name || '').toLowerCase();
        if (!target) return false;
        const nodes = document.querySelectorAll('h1,h2,h3,h4,span,div,a,p,li');
        for (const el of nodes) {
            if (el.children.length) continue;
            const text = (el.textContent || '').trim().toLowerCase();
            if (!text || !text.includes(target)) continue;
            const r = el.getBoundingClientRect();
            if (r.width > 0 && r.height > 0 && r.top < window.innerHeight
                && r.bottom > 0 && r.left < window.innerWidth && r.right > 0) {
                return true;
            }
        }
        return false;
    }"""
    try:
        return bool(await page.evaluate(script, name))
    except Exception:                                           # noqa: BLE001
        return False


async def _policy_visible(locator) -> bool:
    """Whether the policy container itself is inside the viewport right now."""
    script = """(el) => {
        const r = el.getBoundingClientRect();
        return r.width > 0 && r.height > 0 && r.top < window.innerHeight
               && r.bottom > 0;
    }"""
    try:
        return bool(await locator.evaluate(script))
    except Exception:                                           # noqa: BLE001
        return False


async def _bring_into_view(page, locator, interactions: _Interactions) -> bool:
    """Scroll the policy block into the middle of the viewport and let it paint.

    Three steps rather than one, because ``scroll_into_view_if_needed`` alone
    was not enough on run 1: Marriott's hotel-information section mounts its
    DOM before it paints, so an element crop taken immediately after the call
    can be a uniform white rectangle of the right size.

    1. Playwright's own scroll, which also waits for actionability.
    2. An explicit ``scrollIntoView({block: 'center'})``, which puts the block
       in the middle rather than flush against an edge under a sticky header.
    3. A settle, then a bounding-box STABILITY check -- the box is read twice
       and the wait repeats while it is still moving, so a smooth-scrolling
       page is not photographed mid-flight.
    """
    try:
        await locator.scroll_into_view_if_needed(timeout=15_000)
        interactions.add("scrolled the policy container into view")
    except Exception:                                           # noqa: BLE001
        interactions.add("scroll_into_view_if_needed did not complete")
    try:
        await locator.evaluate(
            "el => el.scrollIntoView({block: 'center', inline: 'nearest'})")
        interactions.add("centred the policy container in the viewport")
    except Exception:                                           # noqa: BLE001
        pass

    previous = None
    for _ in range(4):
        await page.wait_for_timeout(SCROLL_SETTLE_MS)
        try:
            box = await locator.bounding_box()
        except Exception:                                       # noqa: BLE001
            return False
        if box and previous == box:
            interactions.add("policy container settled at a stable position")
            return await _policy_visible(locator)
        previous = box
    return await _policy_visible(locator)


async def _persist(*, run_dir: Path, target: CaptureTarget, attempt: int,
                   page, policy_locator, html: str, body_text: str,
                   block_text: str, interactions: _Interactions,
                   hit=None) -> Dict:
    """Write the artifact set. Raises on failure; the caller maps that to
    CAPTURE_FAILED so a half-written directory never counts as evidence."""
    attempt_dir = run_dir / target.slug / ("attempt-%02d" % attempt)
    attempt_dir.mkdir(parents=True, exist_ok=True)

    artifacts: Dict[str, Dict] = {}

    def record(name: str, path: Path, mime: str, note: str = "") -> None:
        artifacts[name] = {
            "file": name,
            "path": str(path),
            "mime_type": mime,
            "bytes": path.stat().st_size,
            "sha256": sha256_file(path),
        }
        if note:
            artifacts[name]["note"] = note

    html_path = attempt_dir / "rendered.html"
    html_path.write_text(html, encoding="utf-8")
    record("rendered.html", html_path, "text/html; charset=utf-8",
           "the hydrated DOM after all interactions, not the original HTTP "
           "response body")

    text_path = attempt_dir / "page-text.txt"
    text_path.write_text(body_text, encoding="utf-8")
    record("page-text.txt", text_path, "text/plain; charset=utf-8")

    block_path = attempt_dir / "policy-block.txt"
    block_path.write_text(block_text, encoding="utf-8")
    record("policy-block.txt", block_path, "text/plain; charset=utf-8",
           "the bounded pet-policy container only; every quote in this "
           "manifest is a contiguous substring of this file")

    if hit is not None:
        # The boundary this LIVE walk chose, recorded so a replay recovers it
        # instead of recomputing a different one from the saved HTML. The two
        # walks are different algorithms and are not required to agree.
        locator_path = PL.persist(attempt_dir, PL.build_record(
            hit=hit, block_text=block_text,
            document_sha256=sha256_file(html_path), walk=PL.LIVE_DOM_WALK))
        record(PL.LOCATOR_ARTIFACT, locator_path, "application/json",
               "how this block's boundary was chosen; a replay reads the block "
               "and checks it against this record rather than locating again")

    full_path = attempt_dir / "full-page.png"
    await page.screenshot(path=str(full_path), full_page=True,
                          timeout=SCREENSHOT_TIMEOUT_MS)
    interactions.add("captured full-page screenshot")
    record("full-page.png", full_path, "image/png",
           "carries the property identity context for the linked set")

    # Policy-section imagery. The element crop is the tight one; the viewport
    # shot is the same content in page context. A crop that paints blank is
    # NOT recorded as an artifact -- run 1 produced one and the summary counted
    # it, which is how an artifact census comes to over-report itself.
    section_note: Dict = {"attempted": True}
    identity_visible = False
    policy_in_view = False
    try:
        policy_in_view = await _bring_into_view(page, policy_locator,
                                                interactions)
        identity_visible = await _identity_visible_with(page, target.hotel)

        section_path = attempt_dir / "policy-section.png"
        blank: Optional[bool] = None
        for shot in (1, 2):
            await policy_locator.screenshot(path=str(section_path),
                                            timeout=SCREENSHOT_TIMEOUT_MS)
            blank = image_is_blank(section_path)
            if blank is not True:
                break
            interactions.add("policy element crop %d painted blank; settling "
                             "and retaking" % shot)
            await page.wait_for_timeout(SCROLL_SETTLE_MS)
            policy_in_view = await _bring_into_view(page, policy_locator,
                                                    interactions)

        section_note["content_check"] = ("blank" if blank is True
                                         else "non_blank" if blank is False
                                         else "unavailable")
        if blank is True:
            section_path.unlink(missing_ok=True)
            section_note["captured"] = False
            section_note["reason"] = (
                "the element crop painted a single flat colour twice; a "
                "uniform rectangle is not a screenshot of a policy and is not "
                "recorded as one")
        else:
            section_note["captured"] = True
            record("policy-section.png", section_path, "image/png",
                   "element crop of the bounded pet-policy container")

        context_path = attempt_dir / "policy-context.png"
        await page.screenshot(path=str(context_path), full_page=False,
                              timeout=SCREENSHOT_TIMEOUT_MS)
        record("policy-context.png", context_path, "image/png",
               "viewport with the policy container scrolled into view")
    except Exception as exc:                                    # noqa: BLE001
        section_note["captured"] = False
        section_note["reason"] = client.redact("%s: %s"
                                               % (type(exc).__name__, exc))

    return {
        "files": artifacts,
        "policy_section": section_note,
        "policy_visible_in_viewport": policy_in_view,
        "identity_visible_in_policy_screenshot": identity_visible,
        "identity_and_policy_in_one_frame": bool(identity_visible
                                                 and policy_in_view),
        "identity_linkage": (
            "policy-section.png shows the policy wording; the property "
            "identity is carried by full-page.png and by rendered.html's "
            "JSON-LD. The set is linked rather than cropped, because cropping "
            "identity away to fit one frame is what makes a screenshot "
            "unverifiable."),
        "attempt_dir": str(attempt_dir),
    }


async def run_attempt(target: CaptureTarget, attempt: int, *, run_dir: Path
                      ) -> Tuple[AttemptRecord, Optional[Dict]]:
    """One fresh Bright Data session against one property.

    Returns the attempt record and, for a VALID attempt only, the payload it
    produced (the policy reading and the artifact block). The payload is
    returned rather than stored on the record because a record is serialised
    into every property result and a ``PolicyReading`` is not JSON.

    Never raises. Every failure path -- connection, navigation, parsing,
    writing -- resolves to one of the nine outcomes.
    """
    from playwright.async_api import async_playwright

    started = time.monotonic()
    started_at = utc_now_iso()
    interactions = _Interactions()
    network: Dict = {"available": False, "requests": 0, "encoded_bytes": 0,
                     "note": "not attached"}

    def finish(outcome: str, *, detail: str = "", final_url: str = "",
               title: str = "", body_chars: int = 0,
               identity: Optional[Dict] = None, artifact_dir: str = "",
               payload: Optional[Dict] = None
               ) -> Tuple[AttemptRecord, Optional[Dict]]:
        record = AttemptRecord(
            attempt=attempt, outcome=outcome, started_at=started_at,
            ended_at=utc_now_iso(), elapsed_seconds=time.monotonic() - started,
            requested_url=target.requested_url, final_url=final_url,
            title=title, body_chars=body_chars,
            detail=client.redact(detail),
            interactions=interactions.snapshot(),
            identity=identity,
            network=NetworkUsage(
                available=bool(network.get("available")),
                requests=int(network.get("requests") or 0),
                encoded_bytes=int(network.get("encoded_bytes") or 0),
                note=str(network.get("note") or "")).to_dict(),
            artifact_dir=artifact_dir)
        return record, (payload if outcome == O.VALID else None)

    try:
        endpoint = client.browser_endpoint()
    except client.BrightDataCredentialError as exc:
        return finish(O.NAVIGATION_FAILED, detail=str(exc))

    try:
        async with async_playwright() as playwright:
            browser = await playwright.chromium.connect_over_cdp(
                endpoint, timeout=CONNECT_TIMEOUT_MS)
            interactions.add("opened a fresh Bright Data Browser API session")
            try:
                context = (browser.contexts[0] if browser.contexts
                           else await browser.new_context())
                page = await context.new_page()
                _, network = await _measure_network(context, page)

                try:
                    await page.goto(target.requested_url,
                                    wait_until="domcontentloaded",
                                    timeout=NAVIGATION_TIMEOUT_MS)
                    interactions.add("navigated to the requested property URL")
                except Exception as exc:                        # noqa: BLE001
                    return finish(O.NAVIGATION_FAILED,
                                  detail="%s: %s" % (type(exc).__name__, exc))

                # Wait for the policy container specifically rather than for a
                # generic load state: the shell failures observed during the
                # proof satisfied every generic signal.
                try:
                    await page.wait_for_selector(
                        MS.POLICY_LOCATORS[0][1], timeout=POLICY_WAIT_MS,
                        state="attached")
                    interactions.add("waited for the pet-policy container to mount")
                except Exception:                               # noqa: BLE001
                    interactions.add("pet-policy container did not mount within "
                                     "%d ms; continued to the health checks"
                                     % POLICY_WAIT_MS)
                await page.wait_for_timeout(SETTLE_MS)

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

                health = MS.page_health(
                    title=title, body_text=body_text, final_url=final_url,
                    expected_property_code=target.property_code)
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
                                  detail="could not read the hydrated DOM: "
                                         "%s: %s" % (type(exc).__name__, exc))

                signals = MS.read_identity(html, final_url=final_url,
                                           title=title)
                assessment = MS.assess_identity(
                    signals,
                    expected_name=target.hotel,
                    expected_property_code=target.property_code,
                    expected_postal_code=target.expected_postal_code,
                    expected_street=target.expected_street)
                identity_block = {
                    "signals": signals.to_dict(),
                    "confirmed": assessment.confirmed,
                    "matched": list(assessment.signals_matched),
                    "conflicting": list(assessment.signals_conflicting),
                    "reasons": list(assessment.reasons),
                    "binding_method": assessment.binding_method,
                }
                if not assessment.confirmed:
                    return finish(O.IDENTITY_MISMATCH, final_url=final_url,
                                  title=title,
                                  body_chars=len(MS.collapse(body_text)),
                                  identity=identity_block,
                                  detail="; ".join(assessment.reasons))

                locator_id, policy_locator, block_text = \
                    await _locate_policy_block(page, interactions)
                if not policy_locator:
                    return finish(O.POLICY_NOT_FOUND, final_url=final_url,
                                  title=title,
                                  body_chars=len(MS.collapse(body_text)),
                                  identity=identity_block,
                                  detail="none of the %d bounded policy "
                                         "locators resolved on a page that "
                                         "otherwise rendered"
                                         % len(MS.POLICY_LOCATORS))

                reading = MS.parse_policy_block(block_text,
                                                locator_id=locator_id)
                if not reading.found or not reading.heading_present:
                    return finish(O.POLICY_NOT_FOUND, final_url=final_url,
                                  title=title,
                                  body_chars=len(MS.collapse(body_text)),
                                  identity=identity_block,
                                  detail="the located container carried no "
                                         "'%s' heading" % MS.POLICY_HEADING)

                try:
                    persisted = await _persist(
                        run_dir=run_dir, target=target, attempt=attempt,
                        page=page, policy_locator=policy_locator, html=html,
                        body_text=body_text, block_text=reading.block_text,
                        interactions=interactions)
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
                                       "artifacts": persisted,
                                       "locator_id": locator_id})
            finally:
                try:
                    await browser.close()
                except Exception:                               # noqa: BLE001
                    pass
    except Exception as exc:                                    # noqa: BLE001
        return finish(O.NAVIGATION_FAILED,
                      detail="session failed: %s: %s"
                             % (type(exc).__name__, exc))


async def capture_property(target: CaptureTarget, *, run_dir: Path,
                           max_attempts: int = MAX_ATTEMPTS
                           ) -> Tuple[List[AttemptRecord], Optional[Dict]]:
    """Up to ``max_attempts`` fresh sessions, stopping at the first VALID.

    Returns every attempt record and, when one succeeded, the payload that
    attempt produced. A property whose attempts all fail returns ``None`` and
    is the caller's cue to record CLAUDE_FALLBACK_REQUIRED -- never to soften
    a failed attempt into evidence.
    """
    records: List[AttemptRecord] = []
    for attempt in range(1, max_attempts + 1):
        record, payload = await run_attempt(target, attempt, run_dir=run_dir)
        records.append(record)
        if record.outcome == O.VALID:
            return records, payload
        if attempt < max_attempts:
            await asyncio.sleep(RETRY_PAUSE_SECONDS)
    return records, None


__all__ = [
    "MAX_ATTEMPTS", "CONNECT_TIMEOUT_MS", "NAVIGATION_TIMEOUT_MS",
    "POLICY_WAIT_MS", "SETTLE_MS", "RETRY_PAUSE_SECONDS",
    "OPTIMIZATION_ENABLED", "OPTIMIZATION_NOTE", "CAPTURE_ENGINE",
    "SCREENSHOT_TIMEOUT_MS", "SCROLL_SETTLE_MS",
    "AUTOMATION", "sha256_file", "utc_now_iso", "image_is_blank",
    "CaptureTarget",
    "NetworkUsage", "AttemptRecord", "GeoProbe", "probe_exit_country",
    "run_attempt", "capture_property",
]
