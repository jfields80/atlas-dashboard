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
from .identity_check import verify_identity
from .manifest import Journal, build_manifest, write_manifest
from .queue import CaptureQueue, QueueEntry, remaining_entries
from .reasons import CHALLENGE_REASONS
from .state_machine import (
    CAPTURED, CAPTURING, EXCEPTION, HotelOutcome, IDENTITY, INTERACTING,
    KillSwitch, NAVIGATING, POLICY_SCAN, QUEUED, URL_SHAPE, VALIDATING,
)
from .validators import detect_fee_conflict, validate_written_capture


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

            dom = self._session.snapshot()

            # A challenge or denial is visible in the rendered text, so check
            # before spending any more effort on this hotel.
            from ..operator_capture import _page_block_reason
            blocked = _page_block_reason(dom.text)
            if blocked:
                mapped = {"captcha_or_challenge_page": "CAPTCHA_OR_CHALLENGE",
                          "access_denied_page": "ACCESS_DENIED",
                          "login_required_page": "LOGIN_REQUIRED"}.get(
                              blocked, "ACCESS_DENIED")
                return done(EXCEPTION, mapped, (blocked,))

            # -- URL_SHAPE + IDENTITY -------------------------------------- #
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

            box, viewport = self._frame_policy(location)
            if box is None:
                return done(EXCEPTION, "POLICY_OFF_SCREEN", ("no_box_for_policy",))

            # -- CAPTURING -------------------------------------------------- #
            if self._config.dry_run:
                return done(EXCEPTION, "BATCH_ABORTED", ("dry_run",))

            captured_at = _now_iso(self._clock)
            payload = build_payload(
                dom, captured_at=captured_at, requested_url=entry.official_url,
                policy=location, policy_box=box,
                interaction_log=interaction_log, viewport=viewport)

            png = self._session.screenshot_png()
            if not png:
                return done(EXCEPTION, "SCREENSHOT_UNAVAILABLE", ("empty_png",))

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

    def _frame_policy(self, location: PolicyLocation) -> Tuple[Optional[BoxModel], Tuple[int, int]]:
        """Scroll the policy into view and read its box.

        Text is the primary handle, not a selector. The locator works on
        rendered text, brands rarely offer a stable selector for a policy
        block, and the text is what the operator will be asked to confirm.
        """
        needle = _needle_for(location)
        if location.selector and self._session.query_selector_exists(location.selector):
            self._session.scroll_into_view(location.selector)
            box = self._session.box_model(location.selector)
        else:
            self._session.scroll_to_text(needle)
            box = self._session.box_for_text(needle)
        if box is None and needle:
            self._session.scroll_to_text(needle)
            box = self._session.box_for_text(needle)
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
        self._sleep(self._jitter(low, high))


def _needle_for(location: PolicyLocation) -> str:
    """A short, distinctive slice of the policy to scroll to and measure."""
    excerpt = (location.text_excerpt or "").strip()
    if not excerpt:
        return location.matched_anchors[0] if location.matched_anchors else ""
    first_line = excerpt.splitlines()[0].strip()
    return first_line or excerpt[:40]
