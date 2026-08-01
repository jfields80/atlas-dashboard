"""Immediate post-capture validation.

Runs against what was actually written, not against what we believe we wrote.
Hashes are recomputed from the file on disk; the PNG is re-read and re-parsed.
A capture that cannot survive being read back is not a capture.

The screenshot check is the one worth explaining. "Is the policy visible in the
screenshot?" cannot be answered by looking at the image without making a claim
nobody can re-verify. It CAN be answered by geometry: the policy element's box
in page coordinates, minus the scroll offset in force when the shot was taken,
must lie inside the viewport. Both rectangles are recorded in the capture, so
anyone can re-check the claim later from the artifact alone.
"""

from __future__ import annotations

import hashlib
import json
import pathlib
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple

from ..operator_capture import (
    _page_block_reason, url_carries_private_params, validate_capture,
    MIN_USEFUL_TEXT_BYTES,
)
from .capture_writer import png_dimensions, png_is_complete
from .contracts import BoxModel, PolicyLocation

#: A policy box must be at least this visible to count as "in frame". A block
#: half off the bottom edge is not evidence the operator can read.
MIN_VISIBLE_FRACTION = 0.5


@dataclass(frozen=True)
class ValidationResult:
    ok: bool
    reason: str = ""
    problems: Tuple[str, ...] = ()
    duplicate_of: str = ""

    def to_dict(self) -> dict:
        return {"ok": self.ok, "reason": self.reason,
                "problems": list(self.problems),
                "duplicate_of": self.duplicate_of}


def visible_fraction(box: BoxModel, viewport_height: float) -> float:
    """How much of the box lies inside the viewport, 0.0-1.0."""
    if box.height <= 0 or viewport_height <= 0:
        return 0.0
    top, bottom = box.viewport_rect()
    visible = min(bottom, viewport_height) - max(top, 0.0)
    if visible <= 0:
        return 0.0
    return min(1.0, visible / box.height)


def policy_in_frame(box: Optional[BoxModel], viewport_height: float,
                    *, minimum: float = MIN_VISIBLE_FRACTION) -> bool:
    if box is None:
        return False
    return visible_fraction(box, viewport_height) >= minimum


def _box_from(raw) -> Optional[BoxModel]:
    """Rebuild a BoxModel from a capture's recorded geometry, or None."""
    if not isinstance(raw, dict):
        return None
    try:
        return BoxModel(x=float(raw.get("x") or 0.0), y=float(raw.get("y") or 0.0),
                        width=float(raw.get("width") or 0.0),
                        height=float(raw.get("height") or 0.0),
                        scroll_x=float(raw.get("scroll_x") or 0.0),
                        scroll_y=float(raw.get("scroll_y") or 0.0))
    except (TypeError, ValueError):
        return None


def viewport_offset(box: BoxModel) -> float:
    """Top edge of the box relative to the visible viewport."""
    return box.y - box.scroll_y


def check_policy_framing(before: Optional[BoxModel], after: Optional[BoxModel],
                         viewport_height: float,
                         *, tolerance_px: float = None) -> Tuple[bool, str]:
    """Both readings must agree that the policy was on screen.

    Reading the box only BEFORE ``Page.captureScreenshot`` is not enough, and
    that is not a theoretical worry: a real Marriott capture recorded
    "100% visible at viewport y=368" while the PNG showed the bar section 470px
    further down the page. Every automated gate passed and the artifact could
    not contradict itself, because it held a single measurement of a moment
    that had already gone.

    Returns ``(ok, detail)``. ``detail`` is empty when ok.
    """
    if tolerance_px is None:
        from .doctrine import POLICY_BOX_DRIFT_TOLERANCE_PX
        tolerance_px = POLICY_BOX_DRIFT_TOLERANCE_PX

    if before is None:
        return (False, "no_box_before_screenshot")
    if after is None:
        # The element vanished while the image was being taken. Whatever the
        # screenshot shows, it is not a page we can still measure.
        return (False, "policy_element_missing_after_screenshot")
    if viewport_height <= 0:
        return (False, "unknown_viewport_height")

    if not policy_in_frame(before, viewport_height):
        return (False, "off_screen_before_screenshot:%.2f"
                % visible_fraction(before, viewport_height))
    if not policy_in_frame(after, viewport_height):
        return (False, "off_screen_after_screenshot:%.2f"
                % visible_fraction(after, viewport_height))

    drift = abs(viewport_offset(after) - viewport_offset(before))
    if drift > tolerance_px:
        return (False, "geometry_drift_px:%.0f" % drift)

    if abs(after.height - before.height) > tolerance_px:
        return (False, "geometry_height_changed_px:%.0f"
                % abs(after.height - before.height))

    return (True, "")


def check_pair(json_path: pathlib.Path, png_path: pathlib.Path) -> List[str]:
    """JSON and PNG must exist and share a stem."""
    problems: List[str] = []
    if not json_path.exists():
        problems.append("json_missing")
    if not png_path.exists():
        problems.append("png_missing")
    if json_path.stem != png_path.stem:
        problems.append("stem_mismatch:%s!=%s" % (json_path.stem, png_path.stem))
    return problems


def check_hashes(payload: dict) -> List[str]:
    """Recompute both content hashes from the payload's own content."""
    problems: List[str] = []
    for field_name, source in (("html_sha256", "html"), ("text_sha256", "text")):
        declared = str(payload.get(field_name) or "")
        actual = hashlib.sha256(
            str(payload.get(source) or "").encode("utf-8")).hexdigest()
        if declared != actual:
            problems.append("%s_mismatch" % field_name)
    return problems


def check_png(png_path: pathlib.Path) -> List[str]:
    problems: List[str] = []
    try:
        data = png_path.read_bytes()
    except OSError as exc:
        return ["png_unreadable:%s" % exc.__class__.__name__]
    try:
        png_dimensions(data)
    except Exception as exc:                      # noqa: BLE001 - reported, not raised
        problems.append("png_invalid:%s" % exc)
    if not png_is_complete(data):
        problems.append("png_truncated")
    return problems


def validate_written_capture(
        json_path, png_path, *,
        policy_box: Optional[BoxModel] = None,
        viewport_height: float = 0.0,
        seen_text_hashes: Optional[Dict[str, str]] = None) -> ValidationResult:
    """The nine immediate checks, in the order that fails cheapest first.

    ``seen_text_hashes`` maps ``text_sha256 -> hotel_id`` for everything already
    captured, in this batch and in the archived corpus. Duplicate detection is a
    lookup, not a heuristic.
    """
    jp, pp = pathlib.Path(json_path), pathlib.Path(png_path)

    problems = check_pair(jp, pp)
    if problems:
        return ValidationResult(False, "VALIDATION_FAILED", tuple(problems))

    try:
        payload = json.loads(jp.read_text("utf-8"))
    except (ValueError, UnicodeDecodeError) as exc:
        return ValidationResult(False, "VALIDATION_FAILED",
                                ("json_unparseable:%s" % exc.__class__.__name__,))

    # 1. The ingestion contract's own structural + privacy gate. Running the
    #    real function rather than a copy is the point: a capture this build
    #    accepts is one ingestion will accept.
    ok, reason = validate_capture(payload)
    if not ok:
        rc = "FORBIDDEN_CONTENT" if reason.startswith("forbidden_keys") else "VALIDATION_FAILED"
        return ValidationResult(False, rc, ("validate_capture:%s" % reason,))

    # 2. Hashes, recomputed.
    problems.extend(check_hashes(payload))

    # 3. PNG integrity, re-read from disk.
    problems.extend(check_png(pp))
    if problems:
        return ValidationResult(False, "VALIDATION_FAILED", tuple(problems))

    text = str(payload.get("text") or "")

    # 4. Challenge / denial / login content.
    blocked = _page_block_reason(text)
    if blocked:
        mapped = {"captcha_or_challenge_page": "CAPTCHA_OR_CHALLENGE",
                  "access_denied_page": "ACCESS_DENIED",
                  "login_required_page": "LOGIN_REQUIRED"}.get(blocked, "VALIDATION_FAILED")
        return ValidationResult(False, mapped, (blocked,))

    # 5. Enough rendered text to carry a policy at all.
    if len(text.encode("utf-8")) < MIN_USEFUL_TEXT_BYTES:
        return ValidationResult(False, "INSUFFICIENT_TEXT",
                                ("text_bytes:%d" % len(text.encode("utf-8")),))

    # 6. The citation must not carry a session or ad-tracking parameter. The
    #    canonical URL rescues most of these -- Hilton captures arrive with
    #    WT.mc_id from a marketing link -- so only flag when neither is clean.
    final_url = str(payload.get("final_url") or "")
    canonical = str(payload.get("canonical_url") or "")
    if url_carries_private_params(final_url) and (
            not canonical or url_carries_private_params(canonical)):
        return ValidationResult(False, "PRIVATE_PARAMS_IN_CITATION",
                                ("no_clean_citable_url",))

    # 7. Policy geometry: was the block actually in frame -- BEFORE and AFTER
    #    the screenshot? Read back from the file rather than trusted from the
    #    caller, so the artifact validates itself.
    auto = payload.get("automation") or {}
    vh = float(viewport_height or auto.get("viewport_height") or 0.0)
    stored_before = _box_from(auto.get("policy_box"))
    stored_after = _box_from(auto.get("policy_box_after_screenshot"))

    if stored_before is not None and stored_after is not None and vh > 0:
        ok, detail = check_policy_framing(stored_before, stored_after, vh)
        if not ok:
            return ValidationResult(False, "POLICY_OFF_SCREEN", (detail,))
    elif policy_box is not None and vh > 0:
        # Caller-supplied single box: still checked, but this path cannot prove
        # the page held still while the image was taken.
        if not policy_in_frame(policy_box, vh):
            return ValidationResult(
                False, "POLICY_OFF_SCREEN",
                ("visible_fraction:%.2f" % visible_fraction(policy_box, vh),))

    # 8. Duplicate detection, by exact rendered text.
    if seen_text_hashes:
        digest = str(payload.get("text_sha256") or "")
        prior = seen_text_hashes.get(digest)
        if prior:
            return ValidationResult(False, "DUPLICATE_CAPTURE",
                                    ("text_sha256:%s" % digest[:16],),
                                    duplicate_of=prior)

    return ValidationResult(True)


def detect_fee_conflict(text: str) -> Tuple[bool, Tuple[str, ...]]:
    """Advisory only.

    The authoritative fee-conflict gate lives in the promotion adapter, where it
    can see the attestation's recorded contradictions. Re-deriving the rule here
    would be two definitions of "conflicting", which is how they drift apart. So
    this imports the real detector and reports what it finds, purely so the
    operator learns at capture time that a REVIEW is coming.
    """
    try:
        from ..rendered_capture import collect_statements, detect_contradictions
    except ImportError:
        return (False, ())
    try:
        statements = collect_statements(text)
        found = tuple(detect_contradictions(statements) or ())
    except Exception:                              # noqa: BLE001 - advisory only
        return (False, ())
    conflicts = tuple(c for c in found if str(c).startswith("conflicting_fee_basis"))
    return (bool(conflicts), conflicts)
