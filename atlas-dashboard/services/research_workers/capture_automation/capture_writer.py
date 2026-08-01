"""Build and write a ``ptf-official-capture/1.0`` file plus its screenshot.

The payload is byte-compatible with what the Chrome extension emits, field for
field, because the ingestion contract must not be able to tell which transport
produced a capture -- and should not want to. Extra automation-only context
(the located policy, its geometry, the interaction log) rides in an additive
``automation`` block that ``validate_capture`` ignores and that carries no
forbidden key.
"""

from __future__ import annotations

import base64
import hashlib
import json
import pathlib
import struct
from typing import Optional, Sequence, Tuple

from ..operator_capture import CAPTURE_SCHEMA
from .contracts import BoxModel, DomSnapshot, PolicyLocation

#: Bumped independently of the extension's version so provenance stays legible.
AUTOMATION_VERSION = "ptf-capture-003/1.0.0"

_PNG_MAGIC = b"\x89PNG\r\n\x1a\n"


class CaptureWriteError(RuntimeError):
    """Raised when a capture cannot be written safely."""


def sha256_hex(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def png_dimensions(data: bytes) -> Tuple[int, int]:
    """Width and height from the IHDR chunk.

    Also serves as the PNG integrity check: a file that is not a PNG, or whose
    header is truncated, cannot answer this.
    """
    if len(data) < 24 or not data.startswith(_PNG_MAGIC):
        raise CaptureWriteError("not_a_png")
    if data[12:16] != b"IHDR":
        raise CaptureWriteError("png_missing_ihdr")
    width, height = struct.unpack(">II", data[16:24])
    if width <= 0 or height <= 0:
        raise CaptureWriteError("png_zero_dimension")
    return (int(width), int(height))


def png_is_complete(data: bytes) -> bool:
    """A PNG that never got its IEND chunk is a truncated download."""
    return data.rstrip().endswith(b"IEND\xaeB\x60\x82") or b"IEND" in data[-16:]


def capture_stem(final_url: str, captured_at: str) -> str:
    """The shared filename stem for the JSON/PNG pair.

    Deliberately the same construction the extension uses, so both transports
    produce recognisably similar filenames and the pair check is meaningful.
    """
    from urllib.parse import urlsplit
    parts = urlsplit(final_url)
    slug = ("%s%s" % (parts.hostname or "", parts.path or ""))
    safe = "".join(c if c.isalnum() else "-" for c in slug).strip("-").lower()
    while "--" in safe:
        safe = safe.replace("--", "-")
    stamp = captured_at.replace(":", "-").replace(".", "-")
    return "%s-%s" % (safe[:80], stamp)


def build_payload(dom: DomSnapshot, *, captured_at: str, requested_url: str,
                  policy: Optional[PolicyLocation] = None,
                  policy_box: Optional[BoxModel] = None,
                  policy_box_after: Optional[BoxModel] = None,
                  interaction_log: Sequence[dict] = (),
                  viewport: Tuple[int, int] = (0, 0),
                  hydration: Optional[dict] = None) -> dict:
    """The capture payload. Same shape as the extension's, plus ``automation``.

    Both geometry readings are recorded -- the one taken before the screenshot
    and the one taken after it. A capture that carried only the "before" box
    once claimed a policy was 100% in frame while the image showed an entirely
    different section of the page, and nothing in the artifact could contradict
    it. Keeping both makes the claim re-checkable from the file alone.
    """
    payload = {
        "schema": CAPTURE_SCHEMA,
        "extension_version": AUTOMATION_VERSION,
        "captured_at": captured_at,
        "requested_url": requested_url,
        "final_url": dom.final_url,
        "title": dom.title,
        "canonical_url": dom.canonical_url,
        "html": dom.html,
        "text": dom.text,
        "jsonld": list(dom.jsonld),
        "html_sha256": sha256_hex(dom.html),
        "text_sha256": sha256_hex(dom.text),
        "capture_note": (
            "Captured by an operator-authorised controller driving a visible "
            "Chrome window over a public page (ADR-PTF-AUTOMATED-BROWSING). "
            "Not evidence of approval, and not an operator affirmation. "
            "Ingestion re-derives all hashes and re-applies every gate."),
        "automation": {
            "controller_version": AUTOMATION_VERSION,
            "viewport_width": viewport[0],
            "viewport_height": viewport[1],
            "policy": policy.to_dict() if policy else None,
            "policy_box": policy_box.to_dict() if policy_box else None,
            "policy_box_after_screenshot": (policy_box_after.to_dict()
                                            if policy_box_after else None),
            "geometry_note": (
                "policy_box was read before Page.captureScreenshot and "
                "policy_box_after_screenshot after it; both had to be in frame "
                "for this capture to be accepted"),
            "interaction_log": [dict(s) for s in interaction_log],
            "hydration": dict(hydration) if hydration else None,
            "affirmation": None,
            "affirmation_note": (
                "Automation never populates operator affirmation fields; a "
                "human must attest separately."),
        },
    }
    return payload


def _resolve_inside(root: pathlib.Path, name: str) -> pathlib.Path:
    """Refuse any path that escapes the batch directory."""
    root = root.resolve()
    target = (root / name).resolve()
    try:
        target.relative_to(root)
    except ValueError:
        raise CaptureWriteError("path_escapes_batch_directory:%s" % name)
    return target


def write_capture(payload: dict, png_bytes: bytes, *,
                  output_dir, stem: str) -> Tuple[pathlib.Path, pathlib.Path, str, int, int]:
    """Write the JSON/PNG pair. Returns paths, png hash and dimensions.

    Fails closed: the PNG is validated *before* anything is written, so a batch
    never leaves a JSON file behind with no partner. That pairing rule is the
    one the operator asked for explicitly and it is cheaper to honour here than
    to repair later.
    """
    if not png_bytes:
        raise CaptureWriteError("screenshot_missing")
    width, height = png_dimensions(png_bytes)
    if not png_is_complete(png_bytes):
        raise CaptureWriteError("png_truncated")

    root = pathlib.Path(output_dir)
    root.mkdir(parents=True, exist_ok=True)
    json_path = _resolve_inside(root, "%s.json" % stem)
    png_path = _resolve_inside(root, "%s.png" % stem)

    if json_path.exists() or png_path.exists():
        raise CaptureWriteError("capture_already_exists:%s" % stem)

    text = json.dumps(payload, indent=2, sort_keys=False, ensure_ascii=False)
    json_path.write_text(text, encoding="utf-8")
    png_path.write_bytes(png_bytes)

    png_hash = hashlib.sha256(png_bytes).hexdigest()
    return (json_path, png_path, png_hash, width, height)


def decode_screenshot(data_or_b64: str) -> bytes:
    """CDP returns base64; the extension returns a data: URL. Accept both."""
    if not data_or_b64:
        return b""
    raw = data_or_b64
    if raw.startswith("data:"):
        _, _, raw = raw.partition(",")
    try:
        return base64.b64decode(raw, validate=False)
    except (ValueError, TypeError) as exc:
        raise CaptureWriteError("screenshot_not_base64: %s" % exc)
