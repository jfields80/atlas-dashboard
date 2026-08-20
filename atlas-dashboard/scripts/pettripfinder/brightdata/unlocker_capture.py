"""Reaching a property page without a browser, for the brand that blocks one.

WHY THIS EXISTS
---------------
PTF-BRIGHTDATA-CROSS-BRAND-PILOT-002 could not reach a single Choice property:
fifteen Browser API attempts, fourteen ``ACCESS_DENIED``. Choice's protection
refuses the managed browser specifically, and no amount of retrying a refused
door opens it. So this module knocks on a different one -- Bright Data's Web
Unlocker, which returns the rendered HTML of a page without giving us a browser
to drive.

WHAT IS LOST AND WHAT IS NOT
----------------------------
Lost: interaction and screenshots. There is no page to click and no viewport to
photograph, so a Web Unlocker capture carries ``rendered.html`` and its derived
text and nothing else.

Not lost: everything the evidence contract actually requires. The artifact is
the page, it is hashed, the quote is contiguous within it, the identity comes
from the page's own JSON-LD, and the source URL is first-party. Screenshots were
never backing facts anyway -- ``enums.ARTIFACT_KINDS`` has no lawful kind for a
machine-captured one, which is GAP-01 and still unpatched.

THE SAME RULES, ENFORCED THE SAME WAY
-------------------------------------
One outcome per attempt from the same closed vocabulary, at most three fresh
attempts, only ``VALID`` writes an artifact, and the same identity and health
gates. A provider change is not a licence to relax a gate: Choice is exactly
the brand where a captcha interstitial would otherwise be mistaken for a page.
"""

from __future__ import annotations

import asyncio
import html as htmllib
import re
import subprocess
import sys
import time
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Sequence, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.brightdata import browser_capture as BC   # noqa: E402
from scripts.pettripfinder.brightdata import client                  # noqa: E402
from scripts.pettripfinder.brightdata import marriott_surface as MS  # noqa: E402
from scripts.pettripfinder.brightdata import outcomes as O           # noqa: E402
from scripts.pettripfinder.brightdata import policy_reading as PR    # noqa: E402
from scripts.pettripfinder.brightdata import policy_surface as PS    # noqa: E402

PROVIDER = "Bright Data Web Unlocker"

#: Unlocker zones, tried in rotation. One zone refusing a captcha does not mean
#: the next will: during the first probe ``cli_unlocker`` failed three times and
#: ``mcp_unlocker`` succeeded on the same property.
UNLOCKER_ZONES: Tuple[str, ...] = ("mcp_unlocker", "cli_unlocker")

SCRAPE_TIMEOUT_SECONDS = 180

#: Markers that mean the unlocker returned an interstitial rather than a page.
DENIAL_MARKERS: Tuple[str, ...] = MS.DENIAL_MARKERS + (
    "captcha resolve failed", "px-captcha", "just a moment",
    "checking your browser",
)

_SCRIPT_STYLE_RE = re.compile(
    r"<(script|style|noscript)[^>]*>.*?</\1>", re.IGNORECASE | re.DOTALL)
_BLOCK_TAG_RE = re.compile(
    r"</?(div|p|li|ul|ol|tr|td|th|section|article|h[1-6]|br|span|dd|dt)[^>]*>",
    re.IGNORECASE)
_TAG_RE = re.compile(r"<[^>]+>")


def html_to_text(html: str) -> str:
    """Readable text from static HTML, with block boundaries preserved.

    Block tags become newlines before the rest are stripped, so adjacent cells
    do not fuse into "Pets allowedYes" -- the same defect ``innerText`` fixed
    on the browser side.
    """
    without_code = _SCRIPT_STYLE_RE.sub(" ", html or "")
    with_breaks = _BLOCK_TAG_RE.sub("\n", without_code)
    stripped = _TAG_RE.sub(" ", with_breaks)
    text = htmllib.unescape(stripped)
    lines = [" ".join(line.split()) for line in text.splitlines()]
    return "\n".join(line for line in lines if line)


def locate_policy_in_html(html: str) -> PS.SurfaceHit:
    """The bounded policy block, found without a browser."""
    return locate_policy_in_text(html_to_text(html))


def locate_policy_in_text(text: str) -> PS.SurfaceHit:
    """The bounded policy block, over text that is already text.

    The same objective as the in-page walk -- the richest container under the
    ceiling that carries a policy signal phrase -- computed over static text.
    Candidate blocks are the page's own line structure; a line is grown with
    its neighbours only while it stays under the ceiling.

    Split out from ``locate_policy_in_html`` so a corpus can hold extracted
    text rather than whole documents and still exercise the locator itself. The
    HTML entry point is unchanged and still the one every caller uses.
    """
    lines = text.splitlines()
    best: Optional[Tuple[int, int, str]] = None      # (features, -length, text)
    considered = 0

    for index, line in enumerate(lines):
        lowered = line.lower()
        phrase = next((p for p in PS.SIGNAL_PHRASES if p in lowered), None)
        if not phrase:
            continue
        considered += 1
        for span in (1, 2, 3, 4):
            block = " ".join(lines[index:index + span]).strip()
            block = MS.collapse(block)
            if len(block) < PS.MIN_BLOCK_CHARS or len(block) > PS.MAX_BLOCK_CHARS:
                continue
            mentions = len(re.findall(r"pets?|animals?|dogs?|cats?", block, re.I))
            floor = (PS.MIN_PET_MENTIONS_LONG
                     if len(block) > PS.LONG_BLOCK_CHARS
                     else PS.MIN_PET_MENTIONS_SHORT)
            if mentions < floor:
                continue
            features = _policy_features(block)
            if features < PS.MIN_POLICY_FEATURES:
                continue
            key = (features, -len(block))
            if best is None or key > (best[0], best[1]):
                best = (features, -len(block), block)

    if best is None:
        return PS.SurfaceHit(found=False, strategy="static_html_walk",
                             candidates_considered=considered)
    return PS.SurfaceHit(found=True, text=best[2], strategy="static_html_walk",
                         selector="(static text)", matched_phrase="signal phrase",
                         container_chars=len(best[2]), policy_features=best[0],
                         candidates_considered=considered, rendered=True)


def _policy_features(text: str) -> int:
    """The same yardstick the in-page locators use."""
    return PS.policy_features(text)


def _run_scrape(url: str, zone: str, out_path: Path) -> Tuple[bool, str]:
    """One Web Unlocker fetch. Returns (ok, detail)."""
    import shutil
    executable = shutil.which(client.CLI_NAME)
    if not executable:
        return False, "the %r CLI is not on PATH" % client.CLI_NAME
    try:
        completed = subprocess.run(
            [executable, "scrape", url, "--format", "html",
             "--country", client.DEFAULT_COUNTRY, "--zone", zone,
             "-o", str(out_path)],
            capture_output=True, text=True, timeout=SCRAPE_TIMEOUT_SECONDS)
    except subprocess.TimeoutExpired:
        return False, "the unlocker did not answer within %ds" % SCRAPE_TIMEOUT_SECONDS
    except Exception as exc:                                     # noqa: BLE001
        return False, client.redact("%s: %s" % (type(exc).__name__, exc))
    output = ((completed.stdout or "") + (completed.stderr or "")).strip()
    if completed.returncode != 0 or not out_path.exists():
        return False, client.redact(output[-300:] or "exit %d" % completed.returncode)
    return True, client.redact(output[-200:])


def run_attempt(target: BC.CaptureTarget, attempt: int, *, run_dir: Path,
                brand: str) -> Tuple[BC.AttemptRecord, Optional[Dict]]:
    """One Web Unlocker fetch, judged by the same gates as a browser attempt."""
    started = time.monotonic()
    started_at = BC.utc_now_iso()
    interactions = BC._Interactions()
    zone = UNLOCKER_ZONES[(attempt - 1) % len(UNLOCKER_ZONES)]
    interactions.add("fetched via %s zone %r (US)" % (PROVIDER, zone))

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
                available=False, note="the Web Unlocker exposes no per-request "
                                      "transfer figure; cost is measured from "
                                      "the zone delta").to_dict(),
            artifact_dir=artifact_dir)
        return record, (payload if outcome == O.VALID else None)

    attempt_dir = run_dir / target.slug / ("attempt-%02d" % attempt)
    attempt_dir.mkdir(parents=True, exist_ok=True)
    staged = attempt_dir / "unlocker-response.html"

    ok, detail = _run_scrape(target.requested_url, zone, staged)
    if not ok:
        staged.unlink(missing_ok=True)
        lowered = detail.lower()
        outcome = (O.ACCESS_DENIED
                   if any(m in lowered for m in ("captcha", "denied", "blocked",
                                                 "403"))
                   else O.NAVIGATION_FAILED)
        return finish(outcome, detail=detail)

    html = staged.read_text(encoding="utf-8", errors="replace")
    body_text = html_to_text(html)
    title_match = re.search(r"<title[^>]*>(.*?)</title>", html,
                            re.IGNORECASE | re.DOTALL)
    title = MS.collapse(htmllib.unescape(title_match.group(1))
                        if title_match else "")
    canonical = MS.canonical_url(html)
    final_url = canonical or target.requested_url

    lowered = (title + " " + body_text[:4000]).lower()
    if any(marker in lowered for marker in DENIAL_MARKERS):
        staged.unlink(missing_ok=True)
        return finish(O.ACCESS_DENIED, final_url=final_url, title=title,
                      body_chars=len(MS.collapse(body_text)),
                      detail="the unlocker returned an interstitial")

    health = PS.page_health(title=title, body_text=body_text,
                            final_url=final_url,
                            expected_url=target.requested_url,
                            expected_property_code=target.property_code,
                            brand=brand)
    if health is not None:
        staged.unlink(missing_ok=True)
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
        staged.unlink(missing_ok=True)
        return finish(O.IDENTITY_MISMATCH, final_url=final_url, title=title,
                      body_chars=len(MS.collapse(body_text)),
                      identity=identity_block,
                      detail="; ".join(assessment.reasons))

    hit = locate_policy_in_html(html)
    if not hit.found:
        staged.unlink(missing_ok=True)
        return finish(O.POLICY_NOT_FOUND, final_url=final_url, title=title,
                      body_chars=len(MS.collapse(body_text)),
                      identity=identity_block,
                      detail="no bounded policy block in a page that rendered; "
                             "%d signal candidates considered"
                             % hit.candidates_considered)
    interactions.add("located the policy block via %s" % hit.strategy)

    reading = PR.parse(hit.text, strategy=hit.strategy)
    if not reading.found:
        staged.unlink(missing_ok=True)
        return finish(O.POLICY_NOT_FOUND, final_url=final_url, title=title,
                      body_chars=len(MS.collapse(body_text)),
                      identity=identity_block,
                      detail="the located block was empty")

    try:
        artifacts = _persist(attempt_dir=attempt_dir, html=html,
                             body_text=body_text, block_text=reading.block_text)
    except Exception as exc:                                     # noqa: BLE001
        return finish(O.CAPTURE_FAILED, final_url=final_url, title=title,
                      body_chars=len(MS.collapse(body_text)),
                      identity=identity_block,
                      detail="artifact persistence failed: %s: %s"
                             % (type(exc).__name__, exc))
    finally:
        staged.unlink(missing_ok=True)

    return finish(O.VALID, final_url=final_url, title=title,
                  body_chars=len(MS.collapse(body_text)),
                  identity=identity_block,
                  artifact_dir=str(attempt_dir),
                  payload={"reading": reading, "surface": hit,
                           "artifacts": artifacts, "disclosures_opened": [],
                           "provider": PROVIDER, "zone": zone})


def _persist(*, attempt_dir: Path, html: str, body_text: str,
             block_text: str) -> Dict:
    artifacts: Dict[str, Dict] = {}

    def record(name: str, path: Path, mime: str, note: str = "") -> None:
        artifacts[name] = {"file": name, "path": str(path), "mime_type": mime,
                           "bytes": path.stat().st_size,
                           "sha256": BC.sha256_file(path)}
        if note:
            artifacts[name]["note"] = note

    html_path = attempt_dir / "rendered.html"
    html_path.write_text(html, encoding="utf-8")
    record("rendered.html", html_path, "text/html; charset=utf-8",
           "the page as %s returned it" % PROVIDER)

    text_path = attempt_dir / "page-text.txt"
    text_path.write_text(body_text, encoding="utf-8")
    record("page-text.txt", text_path, "text/plain; charset=utf-8",
           "derived from rendered.html with block boundaries preserved")

    block_path = attempt_dir / "policy-block.txt"
    block_path.write_text(block_text, encoding="utf-8")
    record("policy-block.txt", block_path, "text/plain; charset=utf-8",
           "the bounded policy block only; every quote is a contiguous "
           "substring of this file")

    return {"files": artifacts, "attempt_dir": str(attempt_dir),
            "policy_section": {"attempted": False,
                               "reason": "the Web Unlocker returns HTML and no "
                                         "browser, so there is no viewport to "
                                         "photograph"},
            "identity_linkage": "identity comes from the page's own JSON-LD "
                                "inside rendered.html, which is hashed"}


async def capture_property(target: BC.CaptureTarget, *, run_dir: Path,
                           brand: str, max_attempts: int = BC.MAX_ATTEMPTS
                           ) -> Tuple[List[BC.AttemptRecord], Optional[Dict]]:
    """Up to ``max_attempts`` unlocker fetches, stopping at the first VALID.

    ``async`` so a caller can use one runner for both providers; the fetch
    itself is a subprocess and is run in a thread so the loop is not blocked.
    """
    records: List[BC.AttemptRecord] = []
    for attempt in range(1, max_attempts + 1):
        record, payload = await asyncio.to_thread(
            run_attempt, target, attempt, run_dir=run_dir, brand=brand)
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


__all__ = ["PROVIDER", "UNLOCKER_ZONES", "DENIAL_MARKERS", "html_to_text",
           "locate_policy_in_html", "locate_policy_in_text", "run_attempt",
           "capture_property"]
