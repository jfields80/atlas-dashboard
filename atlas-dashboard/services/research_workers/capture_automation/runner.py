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
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

from .adapters import adapter_for
from .capture_writer import (
    CaptureWriteError, build_payload, capture_stem, png_dimensions, write_capture,
)
from .evidence_completeness import (
    FIELD_CITY, FIELD_HOTEL_NAME, FIELD_POLICY_TEXT, FIELD_POSTAL_CODE,
    FIELD_PROPERTY_PHONE, FIELD_STATE, FIELD_STREET, FieldObservation,
)
from .identity_views import attach_view_to_capture, sweep_missing_views
from .contracts import BoxModel, DomSnapshot, PolicyLocation
from .doctrine import (
    CONSECUTIVE_CHALLENGE_LIMIT, MAX_SECONDS_BETWEEN_HOTELS,
    MIN_SECONDS_BETWEEN_HOTELS, POLICY_SETTLE_POLL_SECONDS,
    POLICY_SETTLE_STABLE_CHECKS, POLICY_SETTLE_TIMEOUT_SECONDS,
)
from .diagnostics import DiagnosticCollector, DiagnosticContext
from .hydration import wait_for_identity
from .identity_check import classify_identity, verify_identity
from .manifest import Journal, build_manifest, write_manifest
from .queue import CaptureQueue, QueueEntry, remaining_entries
from .reasons import CHALLENGE_REASONS, RETRY_MANUAL, retry_for
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
    # PTF-DISCOVERY: --resume was declared on the CLI but never reached here,
    # so it was a no-op. Worse, the runner resumed UNCONDITIONALLY off
    # ``completed_hotel_ids()``, which counts EXCEPTION as terminal -- so a
    # second run over the same batch directory silently abandoned every
    # IDENTITY_FAILED, IDENTITY_UNVERIFIABLE, POLICY_NOT_FOUND and
    # POLICY_OFF_SCREEN instead of re-attempting them.
    #
    # Skipping is now driven by ``completed_capture_ids()`` -- a complete,
    # on-disk, hash-bearing capture -- in both modes. ``resume`` additionally
    # emits an auditable summary so a resumed run states exactly what it
    # skipped and why.
    resume: bool = False


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


def _identity_detail(identity) -> Tuple[str, ...]:
    """Journal lines describing WHY identity resolved the way it did.

    Emitted for confirmed captures as well as refusals. On a refusal it explains
    what was missing; on a capture it is the citation -- which independent key
    groups agreed, on what evidence basis, and which authoritative source
    carried it.
    """
    lines = ["identity_outcome:%s" % identity.outcome]
    keys = identity.keys
    if keys is None:
        return tuple(lines)

    counting = keys.counting_keys
    lines.append("independent_keys:%s" % ",".join(keys.independent_groups or ("none",)))
    lines.append("authoritative_key:%s" % ("yes" if keys.has_authoritative else "no"))
    authoritative = sorted({k.basis for k in counting if k.authoritative})
    lines.append("authoritative_basis:%s" % ",".join(authoritative or ("none",)))
    agreeing = ["%s@%s" % (k.key, k.basis) for k in counting]
    lines.append("agreeing_keys:%s" % (",".join(agreeing) if agreeing else "none"))
    return tuple(lines)


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
        #: Failure-diagnostic collector. Writes under <batch>/diagnostics/,
        #: never under captures/, and only ever for EXCEPTION outcomes.
        self._diagnostics = DiagnosticCollector(config.batch_dir)

    # -- one hotel -------------------------------------------------------- #

    def capture_one(self, entry: QueueEntry,
                    seen_hashes: Dict[str, str]) -> HotelOutcome:
        """Run one hotel to a terminal outcome. Never raises."""
        started = self._clock()

        # Diagnostic scope. Updated in place as the attempt progresses, so the
        # single ``done()`` below can preserve whatever existed at the moment
        # of failure without any exception path having to know about it. Not
        # one of the fourteen ``return done(EXCEPTION, ...)`` sites changes.
        diag: Dict[str, Any] = {
            "session": self._session, "dom": None, "adapter": None,
            "policy_location": None, "policy_box": None, "policy_box_after": None,
            "viewport": (0, 0), "interaction_log": (), "screenshot_png": None,
            "identity_outcome": "", "identity_keys": (),
        }

        def done(state: str, reason: str = "", detail: Sequence[str] = (),
                 artifacts: Optional[dict] = None, duplicate_of: str = "") -> HotelOutcome:
            # Failure diagnostics: collected BEFORE the runner moves on, while
            # the page is still live. Attached to an EXCEPTION outcome only, so
            # they can never satisfy completed_capture_ids (which requires
            # CAPTURED) and a resumed run re-attempts the hotel.
            #
            # collect() never raises: the terminal reason decided above is the
            # one that survives, whatever happens during collection.
            if state == EXCEPTION and artifacts is None and self._diagnostics is not None:
                artifacts = self._diagnostics.collect(DiagnosticContext(
                    hotel_id=entry.hotel_id, reason=reason,
                    official_url=entry.official_url, candidate_id=entry.candidate_id,
                    brand=entry.brand, attempt=1, detail=tuple(detail),
                    retry_classification=retry_for(reason),
                    property_code=entry.expected_property_code,
                    identity_outcome=diag["identity_outcome"],
                    identity_keys=diag["identity_keys"],
                    session=diag["session"], dom=diag["dom"], adapter=diag["adapter"],
                    policy_location=diag["policy_location"],
                    policy_box=diag["policy_box"],
                    policy_box_after=diag["policy_box_after"],
                    viewport=diag["viewport"],
                    interaction_log=diag["interaction_log"],
                    screenshot_png=diag["screenshot_png"]))
            return HotelOutcome(
                hotel_id=entry.hotel_id, state=state, reason=reason,
                detail=tuple(detail), artifacts=artifacts,
                duplicate_of=duplicate_of,
                elapsed_seconds=self._clock() - started)

        try:
            adapter = adapter_for(entry.brand)
            diag["adapter"] = adapter
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
            diag["dom"] = dom

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
            #
            # PTF-DISCOVERY-001 capture-time identity gate: the existing verdict
            # still runs first and still decides URL shape before content, but
            # acceptance now also requires FD-5's bar -- two INDEPENDENT approved
            # stable keys, at least one proven by an authoritative field-specific
            # source. A page that satisfies the old classifications but not FD-5
            # (name + one key, or name + city) is IDENTITY_INCOMPLETE and stops
            # here, before POLICY_SCAN. Only IDENTITY_CONFIRMED continues.
            identity = classify_identity(dom, entry, observed_at=_now_iso(self._clock),
                                         adapter_metadata=getattr(adapter, "property_metadata", None))
            identity_detail = _identity_detail(identity)
            diag["identity_outcome"] = identity.outcome
            diag["identity_keys"] = tuple(identity.keys.independent_groups) if identity.keys else ()
            if not identity.may_proceed:
                return done(EXCEPTION,
                            identity.verdict.reason if (identity.verdict
                                                        and not identity.verdict.ok)
                            else identity.outcome,
                            tuple(identity.verdict.detail if identity.verdict else ())
                            + identity_detail)
            verdict = identity.verdict

            # -- POLICY_SCAN + INTERACTING ---------------------------------- #
            # These are one loop, not two phases. A collapsed policy is invisible
            # to the scan by construction: Hilton ships its pet table inside a
            # `display:none` tab panel, so the text is in the HTML and absent
            # from innerText until the "Pets" tab is clicked. Scanning first and
            # only then interacting reported POLICY_NOT_FOUND for four of five
            # Hilton hotels while the policy sat one click away.
            location = adapter.locate_policy(dom)
            diag["policy_location"] = location
            interaction_log = self._perform_interactions(adapter, dom, location)
            diag["interaction_log"] = tuple(interaction_log or ())

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

                # One discarded capture. The FIRST Page.captureScreenshot after
                # a reveal can itself relayout the page, and a panel anchored to
                # the viewport moves when it does: measured on two real property
                # pages, the revealed block sat at page-y 1231, the first
                # screenshot moved it to 1371, and the second, third and fourth
                # moved it not at all. Measuring across that one-time reflow
                # reported 140-171px of drift for a policy that was in frame,
                # readable and thereafter perfectly still.
                #
                # Absorbing the reflow here keeps the drift check at full
                # strength rather than widening its tolerance -- the check that
                # caught a Marriott capture describing a section 470px from the
                # one in the image is the last thing to weaken.
                self._session.screenshot_png()
                self._sleep(0.5)

            if location is None:
                return done(EXCEPTION, "POLICY_NOT_FOUND",
                            ("no_anchor_after_supported_expansion",))

            handle = _policy_handle(location, self._session)
            box, viewport = self._frame_policy(location, handle)
            diag["policy_box"], diag["viewport"] = box, viewport
            if box is None:
                return done(EXCEPTION, "POLICY_OFF_SCREEN", ("no_box_for_policy",))

            # -- CAPTURING -------------------------------------------------- #
            if self._config.dry_run:
                return done(EXCEPTION, "BATCH_ABORTED", ("dry_run",))

            captured_at = _now_iso(self._clock)

            png = self._session.screenshot_png()
            diag["screenshot_png"] = png
            if not png:
                return done(EXCEPTION, "SCREENSHOT_UNAVAILABLE", ("empty_png",))

            # Re-read the SAME element now that the image exists. A single
            # pre-screenshot reading describes a moment that has already gone,
            # and one real capture recorded "100% visible" while the PNG showed
            # a different section of the page entirely.
            box_after = self._measure_policy(handle)
            diag["policy_box_after"] = box_after
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

            # -- EVIDENCE VIEWS --------------------------------------------- #
            # PTF-CAPTURE. The attestation gate asks a human to affirm seven
            # fields and refuses unless the package can SHOW each one painted.
            # sweep_missing_views was written and tested for exactly that and
            # had no production caller, so every batch capture arrived short of
            # attestable and could never be used.
            #
            # Two views, because one frame cannot hold both halves. The policy
            # is what this capture exists to photograph and is already framed
            # and geometry-checked, so the image on disk IS its evidence. The
            # identity lives on the page the interactions covered over. Nothing
            # here fabricates: the sweep probes the live DOM, photographs only
            # a frame that actually paints the value, and writes nothing for a
            # field the page does not show. An incomplete result is RECORDED,
            # not repaired -- the attestation gate stays the enforcer, so a
            # capture that was CAPTURED before is CAPTURED still.
            evidence_notes: List[str] = []
            evidence_complete = False
            try:
                evidence_notes.extend(self._attach_policy_view(
                    json_path, png_path, png_sha256=png_hash,
                    png_bytes=len(png), png_width=w, png_height=h,
                    captured_at=captured_at, final_url=dom.final_url,
                    location=location, box=box, viewport=viewport))

                # Reload the same official URL before hunting identity. The
                # click that revealed the policy left a full-viewport modal
                # over the page, and behind it the address and phone are
                # genuinely not visible -- photographing them there would be
                # photographing a backdrop. The capture is already written and
                # hashed, so nothing it says can change.
                renav = self._session.navigate(dom.final_url)
                if not renav.ok:
                    evidence_notes.append("identity_reload_failed:%s"
                                          % (renav.reason or "unknown"))
                else:
                    wait_for_identity(self._session, entry, adapter=adapter,
                                      clock=self._clock, sleep=self._sleep)

                sweep = sweep_missing_views(
                    self._session,
                    capture_path=json_path,
                    official_url=dom.final_url,
                    expected=_expected_identity(entry, location.text_excerpt),
                    write_view=self._view_writer(json_path, dom.final_url),
                    settle=lambda: self._sleep(POLICY_SETTLE_POLL_SECONDS))
                evidence_complete = sweep.complete
                evidence_notes.extend(sweep.notes)
            except Exception as exc:                  # noqa: BLE001 - isolation
                # A sweep failure must not discard a good policy capture; the
                # capture stands and the missing views are reported.
                evidence_notes.append("sweep_failed:%s: %s"
                                      % (exc.__class__.__name__, exc))

            warnings: List[str] = []
            conflicted, slugs = detect_fee_conflict(dom.text)
            if conflicted:
                warnings.append("fee_terms_conflict:%s" % ",".join(slugs[:2]))
            if not evidence_complete:
                warnings.append("identity_evidence_incomplete")

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
                "evidence_complete": evidence_complete,
                "evidence_notes": evidence_notes,
                # Why we believe this page was the right property. Recorded on
                # the SUCCESS path too: a reviewer reading a completed capture
                # needs to see which two keys confirmed it, not just that
                # something passed.
                "identity": identity.to_dict(),
            }
            seen_hashes[payload["text_sha256"]] = entry.hotel_id
            return done(CAPTURED, detail=identity_detail, artifacts=artifacts)

        except Exception as exc:                      # noqa: BLE001 - isolation
            # The whole point of this clause: a hotel that explodes is one
            # exception record, not a dead batch.
            return done(EXCEPTION, "UNEXPECTED_ERROR",
                        ("%s: %s" % (exc.__class__.__name__, exc),))

    def _captures_dir(self) -> pathlib.Path:
        return pathlib.Path(self._config.batch_dir) / "captures"

    def _attach_policy_view(self, capture_path, png_path, *, png_sha256,
                            png_bytes, png_width, png_height, captured_at,
                            final_url, location, box, viewport) -> List[str]:
        """Record the capture's OWN screenshot as the view that shows the policy.

        The policy is the one required field no later sweep can reach: it is
        why the capture exists, the framing check has already proved it was on
        screen when the shutter fired, and the modal that revealed it is gone
        by the time the identity is hunted. The image is already on disk and is
        already the evidence -- this only states what it shows, in the shape
        the completeness gate reads.

        Claims nothing the geometry does not. ``in_frame`` is computed from the
        same box ``check_policy_framing`` passed on, so a policy that was not
        actually in the picture yields an unreadable observation and no proof.
        """
        import json as _json

        top, bottom = box.viewport_rect()
        observation = FieldObservation(
            field=FIELD_POLICY_TEXT,
            text=(location.text_excerpt or "").strip(),
            visible=True,
            in_frame=(top >= 0 and bottom <= float(viewport[1] or 0)),
            context=location.selector or "",
            box={"x": box.x, "y": top, "width": box.width, "height": box.height})

        name = pathlib.Path(png_path).name
        sidecar = {
            "png_file": name,
            "png_sha256": png_sha256,
            "png_bytes": png_bytes,
            "png_width": png_width,
            "png_height": png_height,
            "captured_at": captured_at,
            "final_url": final_url,
            "scroll_y": box.scroll_y,
            "viewport_width": viewport[0],
            "viewport_height": viewport[1],
            "proves_fields": [FIELD_POLICY_TEXT] if observation.readable else [],
            "field_observations": [observation.to_dict()],
            "note": ("The capture's own screenshot, recorded as the view that "
                     "shows the pet policy. Not a second capture and never an "
                     "independent source of policy text."),
        }
        directory = pathlib.Path(png_path).parent
        (directory / (name[:-4] + ".view.json")).write_text(
            _json.dumps(sidecar, indent=1), encoding="utf-8")
        attach_view_to_capture(capture_path, sidecar)
        return [] if observation.readable else ["policy_view_unreadable"]

    def _view_writer(self, capture_path, final_url: str):
        """Persist one additional view: the PNG plus its ``.view.json`` sidecar.

        The sidecar on disk is what a later assessment reads, so the
        observations are written INTO it rather than returned for someone else
        to attach. Named from the image's own sha, so re-running a sweep
        overwrites the identical file instead of accumulating near-duplicates.
        """
        directory = pathlib.Path(capture_path).parent
        stem_base = pathlib.Path(capture_path).stem

        def write_view(png_bytes, observations, scroll_y, viewport):
            import hashlib
            import json as _json

            sha = hashlib.sha256(png_bytes).hexdigest()
            width, height = png_dimensions(png_bytes)
            png_file = "%s.view-%s.png" % (stem_base, sha[:12])
            (directory / png_file).write_bytes(png_bytes)
            sidecar = {
                "png_file": png_file,
                "png_sha256": sha,
                "png_bytes": len(png_bytes),
                "png_width": width,
                "png_height": height,
                "captured_at": _now_iso(self._clock),
                "final_url": final_url,
                "scroll_y": scroll_y,
                "viewport_width": viewport[0],
                "viewport_height": viewport[1],
                "proves_fields": sorted({o.field for o in observations if o.readable}),
                "field_observations": [
                    {"field": o.field, "text": o.text, "visible": o.visible,
                     "in_frame": o.in_frame, "context": o.context, "box": dict(o.box)}
                    for o in observations],
                "note": ("An additional VIEW of the same rendered page, taken in "
                         "the same browser session as the capture it is attached "
                         "to. Never an independent source of policy text."),
            }
            (directory / (png_file[:-4] + ".view.json")).write_text(
                _json.dumps(sidecar, indent=1), encoding="utf-8")
            return sidecar

        return write_view

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
        box = self._settle_policy(handle, box)
        return (box, self._session.viewport())

    def _settle_policy(self, handle: Tuple[str, str],
                       box: Optional[BoxModel]) -> Optional[BoxModel]:
        """Read the box until it stops changing, or the budget runs out.

        A block revealed by a click may still be animating. Its geometry only
        becomes evidence once it holds still, and a screenshot taken mid-flight
        disagrees with a measurement taken a moment earlier -- which reads as
        drift, and fails a policy that is perfectly visible.
        """
        deadline = self._clock() + POLICY_SETTLE_TIMEOUT_SECONDS
        stable = 0
        last = box
        while self._clock() < deadline:
            self._sleep(POLICY_SETTLE_POLL_SECONDS)
            current = self._measure_policy(handle)
            if current is None:
                continue
            if last is not None and _same_box(current, last):
                stable += 1
                if stable >= POLICY_SETTLE_STABLE_CHECKS:
                    return current
            else:
                stable = 0
            last = current
        return last if last is not None else box

    # -- the batch -------------------------------------------------------- #

    def run(self, queue: CaptureQueue) -> BatchResult:
        journal = Journal.open(self._config.batch_dir)
        started_at = _now_iso(self._clock)

        # Only a COMPLETE, VERIFIED capture may be skipped. An EXCEPTION is
        # unfinished work: re-attempting it is the whole point of resuming.
        # A CAPTURED record whose artifacts are missing or unhashed fails
        # closed and is re-attempted too.
        completed = journal.completed_capture_ids()
        incomplete = journal.incomplete_hotel_ids()
        pending = remaining_entries(queue, completed)
        if self._config.limit:
            pending = pending[:self._config.limit]

        queued_ids = [e.hotel_id for e in queue.entries]
        reasons = journal.last_reason_by_hotel()
        resume_summary = {
            "resume_requested": bool(self._config.resume),
            "total_candidates": len(queued_ids),
            "skipped_completed": sorted(set(completed) & set(queued_ids)),
            "reattempted_incomplete": sorted(set(incomplete) & set(queued_ids)),
            "attempted": [e.hotel_id for e in pending],
            "manual_review": sorted(
                hid for hid in (set(incomplete) & set(queued_ids))
                if retry_for(reasons.get(hid, "")) == RETRY_MANUAL),
        }
        resume_summary["counts"] = {
            "total_candidates": len(queued_ids),
            "skipped_completed": len(resume_summary["skipped_completed"]),
            "attempted": len(resume_summary["attempted"]),
            "manual_review": len(resume_summary["manual_review"]),
        }

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
        # Auditable and deterministic: the manifest states exactly which
        # hotels were skipped because a complete capture already existed,
        # which were re-attempted, and which need a human.
        manifest["resume"] = resume_summary
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


def _same_box(a: BoxModel, b: BoxModel) -> bool:
    """Identical to the pixel. A block that is still moving is not settled."""
    return (round(a.x) == round(b.x) and round(a.y) == round(b.y)
            and round(a.width) == round(b.width)
            and round(a.height) == round(b.height))


#: What ``plan_needles`` will keep of a policy needle. A longer expected value
#: cannot match the observation the probe reports back -- the observation
#: records the NEEDLE, so the two must be the same string.
POLICY_NEEDLE_MAX = 60


def _policy_needle(policy_text: str) -> str:
    """A phrase from the policy the DOM probe can actually find.

    The located excerpt is NORMALISED text: block boundaries inside the policy
    region arrive as " / ", which no element's ``innerText`` contains. Hunting
    the raw excerpt therefore finds nothing on a multi-block policy card. The
    longest separator-free run is the longest phrase that is still contiguous
    in some single element, so it is what the probe is given -- trimmed to a
    whole word at the planner's own limit so the needle hunted and the needle
    reported are one value.

    Page-derived, never authored here: if the page does not paint this phrase,
    no view is written and the field stays unproven.
    """
    segments = [s.strip() for s in (policy_text or "").split(" / ")]
    longest = max(segments, key=len) if segments else ""
    if len(longest) <= POLICY_NEEDLE_MAX:
        return longest
    head = longest[:POLICY_NEEDLE_MAX]
    return head[:head.rindex(" ")] if " " in head else head


def _expected_identity(entry, policy_text: str = "") -> Dict[str, str]:
    """The identity the VALIDATED QUEUE ENTRY expects, for the probe to hunt.

    These are needles, never evidence: the sweep only ever proves a field by
    finding it PAINTED on the page. A value here that the page does not show
    yields no view, which is why queue metadata alone can never satisfy the
    completeness gate.

    ``policy_text`` is the located policy excerpt from THIS capture, so the
    seventh required field is hunted on the same terms as the other six
    instead of being left permanently unhuntable.
    """
    return {
        FIELD_HOTEL_NAME: entry.hotel_name,
        FIELD_STREET: entry.expected_address,
        FIELD_CITY: entry.expected_city,
        FIELD_STATE: entry.expected_state,
        FIELD_POSTAL_CODE: entry.expected_postal_code,
        FIELD_PROPERTY_PHONE: entry.expected_phone,
        FIELD_POLICY_TEXT: _policy_needle(policy_text),
    }


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
