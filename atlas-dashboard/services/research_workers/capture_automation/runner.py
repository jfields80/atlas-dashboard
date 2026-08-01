"""Batch orchestration.

The contract this module owes the operator:

  * one hotel's failure never stops the batch -- every per-hotel step runs
    inside one try/except and every escape becomes an outcome, not a traceback;
  * nothing is attested, approved, promoted or published -- the last act is
    writing a manifest;
  * a challenge page stops that hotel, and three in a row stop the batch,
    because continuing to request a brand that has started challenging us is
    the one behaviour that would genuinely look like abuse.

Timing and randomness arrive as injected callables so a test can run a whole
batch instantly and deterministically.
"""

from __future__ import annotations

import pathlib
import random
import time
from dataclasses import dataclass, field
from typing import Callable, Dict, List, Optional, Sequence, Tuple

from .adapters import adapter_for
from .capture_writer import (
    CaptureWriteError, build_payload, capture_stem, write_capture,
)
from .contracts import BoxModel, DomSnapshot, PolicyLocation
from .doctrine import (
    CONSECUTIVE_CHALLENGE_LIMIT, MAX_SECONDS_BETWEEN_HOTELS,
    MIN_SECONDS_BETWEEN_HOTELS,
)
from .hydration import wait_for_identity
from .identity_check import verify_identity
from .manifest import Journal, build_manifest, write_manifest
from .queue import CaptureQueue, QueueEntry, remaining_entries
from .reasons import CHALLENGE_REASONS
from .state_machine import (
    CAPTURED, CAPTURING, EXCEPTION, HotelOutcome, IDENTITY, INTERACTING,
    KillSwitch, NAVIGATING, POLICY_SCAN, QUEUED, URL_SHAPE, VALIDATING,
)
from .validators import (
    check_policy_framing, detect_fee_conflict, validate_written_capture,
)


@dataclass
class RunnerConfig:
    """Everything the runner needs that is not the queue."""

    batch_dir: pathlib.Path
    challenge_limit: int = CONSECUTIVE_CHALLENGE_LIMIT
    min_pace: float = MIN_SECONDS_BETWEEN_HOTELS
    max_pace: float = MAX_SECONDS_BETWEEN_HOTELS
    archived_corpus_dirs: Tuple[str, ...] = ()
    limit: int = 0
    dry_run: bool = False


@dataclass
class BatchResult:
    manifest: dict
    manifest_path: Optional[pathlib.Path]
    outcomes: Tuple[HotelOutcome, ...]
    aborted_reason: str = ""


def _now_iso(clock: Callable[[], float]) -> str:
    """ISO-8601 UTC to milliseconds, from the injected clock."""
    import datetime as _dt
    stamp = _dt.datetime.fromtimestamp(clock(), _dt.timezone.utc)
    return stamp.strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"


class CaptureRunner:
    """Drives one batch through one browser session."""

    def __init__(self, session, config: RunnerConfig, *,
                 clock: Callable[[], float] = time.time,
                 sleep: Callable[[float], None] = time.sleep,
                 jitter: Callable[[float, float], float] = random.uniform):
        self._session = session
        self._config = config
        self._clock = clock
        self._sleep = sleep
        self._jitter = jitter
        #: Every inter-hotel pause, in order. Recorded separately from the
        #: injected sleep because the runner also sleeps for page settling and
        #: hydration polling, and the pacing floor is a guarantee that has to
        #: stay independently checkable.
        self.pace_waits: List[float] = []

    # -- one hotel -------------------------------------------------------- #

    def capture_one(self, entry: QueueEntry,
                    seen_hashes: Dict[str, str]) -> HotelOutcome:
        """Run one hotel to a terminal outcome. Never raises."""
        started = self._clock()

        def done(state: str, reason: str = "", detail: Sequence[str] = (),
                 artifacts: Optional[dict] = None, duplicate_of: str = "") -> HotelOutcome:
            return HotelOutcome(
                hotel_id=entry.hotel_id, state=state, reason=reason,
                detail=tuple(detail), artifacts=artifacts,
                duplicate_of=duplicate_of,
                elapsed_seconds=self._clock() - started)

        try:
            adapter = adapter_for(entry.brand)
            if adapter is None:
                return done(EXCEPTION, "ADAPTER_UNAVAILABLE", ("brand:%s" % entry.brand,))

            # -- NAVIGATING ------------------------------------------------ #
            nav = self._session.navigate(entry.official_url)
            if not nav.ok:
                return done(EXCEPTION, nav.reason or "NAVIGATION_FAILED",
                            (nav.detail,) if nav.detail else ())

            # Wait, bounded, for the page to render something identity-bearing.
            # domContentEventFired says the markup arrived, not that a
            # single-page app has drawn anything; a single snapshot at that
            # moment made "slow" and "anonymous" indistinguishable.
            readiness = wait_for_identity(
                self._session, entry, adapter=adapter,
                clock=self._clock, sleep=self._sleep)
            dom = readiness.dom

            # A challenge or denial is visible in the rendered text, and ends
            # the wait immediately rather than being waited out.
            if readiness.blocked_reason:
                mapped = {"captcha_or_challenge_page": "CAPTCHA_OR_CHALLENGE",
                          "access_denied_page": "ACCESS_DENIED",
                          "login_required_page": "LOGIN_REQUIRED"}.get(
                              readiness.blocked_reason, "ACCESS_DENIED")
                return done(EXCEPTION, mapped, (readiness.blocked_reason,))

            if dom is None:
                return done(EXCEPTION, "IDENTITY_UNVERIFIABLE", ("no_snapshot",))

            if not readiness.ready:
                # Fails closed exactly as before; the diagnostics say whether
                # the page was anonymous or merely slower than the budget.
                return done(EXCEPTION, "IDENTITY_UNVERIFIABLE",
                            ("hydration_timeout" if readiness.timed_out
                             else "no_identity_signal",
                             "checks:%d" % readiness.checks,
                             "waited:%.1fs" % readiness.waited_seconds))

            # -- URL_SHAPE + IDENTITY -------------------------------------- #
            # Readiness decided only WHEN to look. This is still the gate.
            verdict = verify_identity(dom, entry, observed_at=_now_iso(self._clock))
            if not verdict.ok:
                return done(EXCEPTION, verdict.reason, verdict.detail)

            # -- POLICY_SCAN + INTERACTING ---------------------------------- #
            # These are one loop, not two phases. A collapsed policy is invisible
            # to the scan by construction: Hilton ships its pet table inside a
            # `display:none` tab panel, so the text is in the HTML and absent
            # from innerText until the "Pets" tab is clicked. Scanning first and
            # only then interacting reported POLICY_NOT_FOUND for four of five
            # Hilton hotels while the policy sat one click away.
            location = adapter.locate_policy(dom)
            interaction_log = self._perform_interactions(adapter, dom, location)

            # Re-read whenever the page was touched: expanding a section changes
            # the text the capture will carry, and capturing the pre-click DOM
            # would cite a page state that no longer existed when the screenshot
            # was taken.
            if any(s.get("performed") and s.get("action") in ("click", "click_text")
                   for s in interaction_log):
                # A revealed panel needs a beat to lay out before its text
                # exists to be read or its box to be measured.
                self._sleep(1.0)
                dom = self._session.snapshot()
                relocated = adapter.locate_policy(dom)
                if relocated is not None:
                    location = relocated

            if location is None:
                return done(EXCEPTION, "POLICY_NOT_FOUND",
                            ("no_anchor_after_supported_expansion",))

            handle = _policy_handle(location, self._session)
            box, viewport = self._frame_policy(location, handle)
            if box is None:
                return done(EXCEPTION, "POLICY_OFF_SCREEN", ("no_box_for_policy",))

            # -- CAPTURING -------------------------------------------------- #
            if self._config.dry_run:
                return done(EXCEPTION, "BATCH_ABORTED", ("dry_run",))

            captured_at = _now_iso(self._clock)

            png = self._session.screenshot_png()
            if not png:
                return done(EXCEPTION, "SCREENSHOT_UNAVAILABLE", ("empty_png",))

            # Re-read the SAME element now that the image exists. A single
            # pre-screenshot reading describes a moment that has already gone,
            # and one real capture recorded "100% visible" while the PNG showed
            # a different section of the page entirely.
            box_after = self._measure_policy(handle)
            framed, detail = check_policy_framing(box, box_after, float(viewport[1]))
            if not framed:
                return done(EXCEPTION, "POLICY_OFF_SCREEN", (detail,))

            payload = build_payload(
                dom, captured_at=captured_at, requested_url=entry.official_url,
                policy=location, policy_box=box, policy_box_after=box_after,
                interaction_log=interaction_log, viewport=viewport,
                hydration=readiness.to_dict())

            stem = capture_stem(dom.final_url, captured_at)
            try:
                json_path, png_path, png_hash, w, h = write_capture(
                    payload, png, output_dir=self._captures_dir(), stem=stem)
            except CaptureWriteError as exc:
                return done(EXCEPTION, "CAPTURE_WRITE_FAILED", (str(exc),))

            # -- VALIDATING ------------------------------------------------- #
            result = validate_written_capture(
                json_path, png_path, policy_box=box,
                viewport_height=float(viewport[1]),
                seen_text_hashes=seen_hashes)
            if not result.ok:
                return done(EXCEPTION, result.reason, result.problems,
                            duplicate_of=result.duplicate_of)

            warnings: List[str] = []
            conflicted, slugs = detect_fee_conflict(dom.text)
            if conflicted:
                warnings.append("fee_terms_conflict:%s" % ",".join(slugs[:2]))

            from ..operator_capture import _citable_url
            artifacts = {
                "hotel_id": entry.hotel_id,
                "json_path": str(json_path), "png_path": str(png_path),
                "html_sha256": payload["html_sha256"],
                "text_sha256": payload["text_sha256"],
                "png_sha256": png_hash, "png_width": w, "png_height": h,
                "citable_url": _citable_url(dom.final_url, dom.canonical_url),
                "policy": location.to_dict(), "policy_box": box.to_dict(),
                "policy_box_after_screenshot": box_after.to_dict() if box_after else None,
                "hydration": readiness.to_dict(),
                "interaction_log": interaction_log,
                "warnings": warnings,
            }
            seen_hashes[payload["text_sha256"]] = entry.hotel_id
            return done(CAPTURED, artifacts=artifacts)

        except Exception as exc:                      # noqa: BLE001 - isolation
            # The whole point of this clause: a hotel that explodes is one
            # exception record, not a dead batch.
            return done(EXCEPTION, "UNEXPECTED_ERROR",
                        ("%s: %s" % (exc.__class__.__name__, exc),))

    def _captures_dir(self) -> pathlib.Path:
        return pathlib.Path(self._config.batch_dir) / "captures"

    def _perform_interactions(self, adapter, dom: DomSnapshot,
                              location: PolicyLocation) -> List[dict]:
        """Run the adapter's plan. Optional steps that fail are recorded and
        forgiven; a required step that fails is recorded too, and the geometry
        check downstream is what actually decides the hotel's fate."""
        log: List[dict] = []
        for step in adapter.interaction_plan(dom, location):
            entry = step.to_dict()
            performed = False
            try:
                if step.action == "click":
                    performed = self._session.click(step.selector)
                elif step.action == "click_text":
                    performed = self._session.click_text(step.selector, step.text)
                elif step.action == "scroll_into_view":
                    performed = self._session.scroll_into_view(step.selector)
                elif step.action == "wait":
                    self._sleep(step.wait_seconds)
                    performed = True
            except Exception as exc:                  # noqa: BLE001
                entry["error"] = exc.__class__.__name__
            entry["performed"] = bool(performed)
            log.append(entry)
        return log

    def _measure_policy(self, handle: Tuple[str, str]) -> Optional[BoxModel]:
        """Read the policy element's box via a fixed handle.

        The handle is resolved once and reused, so the reading taken after the
        screenshot measures the SAME element as the one taken before it.
        Re-deriving the handle each time would risk comparing two different
        elements and calling the difference "drift".
        """
        kind, value = handle
        if kind == "selector":
            return self._session.box_model(value)
        return self._session.box_for_text(value)

    def _frame_policy(self, location: PolicyLocation,
                      handle: Tuple[str, str]) -> Tuple[Optional[BoxModel], Tuple[int, int]]:
        """Scroll the policy into view and read its box.

        Text is the primary handle, not a selector. The locator works on
        rendered text, brands rarely offer a stable selector for a policy
        block, and the text is what the operator will be asked to confirm.
        """
        kind, value = handle
        if kind == "selector":
            self._session.scroll_into_view(value)
        else:
            self._session.scroll_to_text(value)
        box = self._measure_policy(handle)
        if box is None and kind == "text" and value:
            self._session.scroll_to_text(value)
            box = self._measure_policy(handle)
        return (box, self._session.viewport())

    # -- the batch -------------------------------------------------------- #

    def run(self, queue: CaptureQueue) -> BatchResult:
        journal = Journal.open(self._config.batch_dir)
        started_at = _now_iso(self._clock)

        already = journal.completed_hotel_ids()
        pending = remaining_entries(queue, already)
        if self._config.limit:
            pending = pending[:self._config.limit]

        seen: Dict[str, str] = {}
        from .manifest import archived_text_hashes
        seen.update(archived_text_hashes(*self._config.archived_corpus_dirs))
        seen.update(journal.captured_text_hashes())

        kill = KillSwitch(self._config.challenge_limit)
        outcomes: List[HotelOutcome] = []
        aborted = ""
        skipped: List[str] = []

        for i, entry in enumerate(pending):
            if aborted:
                skipped.append(entry.hotel_id)
                continue

            outcome = self.capture_one(entry, seen)
            journal.append(outcome, at=_now_iso(self._clock))
            outcomes.append(outcome)

            kill = kill.observe(outcome)
            if kill.tripped:
                aborted = ("consecutive_challenges:%d" % kill.consecutive)
                continue

            if i < len(pending) - 1:
                self._pace()

        manifest = build_manifest(
            batch_id=queue.batch_id, queue_size=len(queue), journal=journal,
            started_at=started_at, finished_at=_now_iso(self._clock),
            aborted_reason=aborted, skipped_hotel_ids=skipped)
        path = write_manifest(manifest, self._config.batch_dir)

        return BatchResult(manifest=manifest, manifest_path=path,
                           outcomes=tuple(outcomes), aborted_reason=aborted)

    def _pace(self) -> None:
        """Wait between hotels. The floor is a module constant, not a flag, so
        a batch cannot be told to run flat out from the command line."""
        low = max(MIN_SECONDS_BETWEEN_HOTELS, self._config.min_pace)
        high = max(low, self._config.max_pace)
        waited = self._jitter(low, high)
        self.pace_waits.append(waited)
        self._sleep(waited)


def _policy_handle(location: PolicyLocation, session) -> Tuple[str, str]:
    """How this policy element will be addressed, resolved once.

    Prefers the adapter's selector when the page actually has it; otherwise
    falls back to a distinctive slice of the policy text, which is what the
    locator worked on and what the operator will be asked to confirm.
    """
    if location.selector:
        try:
            if session.query_selector_exists(location.selector):
                return ("selector", location.selector)
        except Exception:                              # noqa: BLE001
            pass
    return ("text", _needle_for(location))


def _needle_for(location: PolicyLocation) -> str:
    """A short, distinctive slice of the policy to scroll to and measure."""
    excerpt = (location.text_excerpt or "").strip()
    if not excerpt:
        return location.matched_anchors[0] if location.matched_anchors else ""
    first_line = excerpt.splitlines()[0].strip()
    return first_line or excerpt[:40]
