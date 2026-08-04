"""Failure diagnostics for capture attempts -- evidence about WHY a capture
failed, never evidence about a hotel.

WHY THIS EXISTS
---------------
Fourteen POLICY_NOT_FOUND and four POLICY_OFF_SCREEN outcomes could not be
diagnosed, because the exception path preserved nothing: no rendered DOM, no
bounding box, no scroll position, no expansion trace. Every proposed adapter or
framing change was therefore guesswork, and a guessed selector that happens to
match the wrong block is worse than no selector at all.

The page is still live at every exception point inside ``capture_one`` -- the
browser is not closed until the whole batch ends -- so the state exists and was
simply being discarded. This module collects it before the runner moves on.

WHAT THIS IS NOT
----------------
A diagnostic is **not** a capture. It is:

  * ``NON_AUTHORITATIVE`` -- nothing here is evidence of a pet policy;
  * ``FAILURE_DIAGNOSTIC`` -- it exists to explain a failure;
  * ``NOT_FOR_EXTRACTION`` -- no extraction, validation, attestation, approval,
    promotion, assembly or publication path may read it.

It is written under ``diagnostics/`` -- never ``captures/`` -- and it hangs off
an EXCEPTION outcome, so ``Journal.completed_capture_ids`` (which requires
CAPTURED) can never count it as work already done. A hotel with only
diagnostics is re-attempted by a resumed run, which is the correct behaviour.

TWO RULES THAT SHAPE EVERY FUNCTION HERE
----------------------------------------
1. **Collection must never change the outcome.** Every collector is wrapped so
   that a failure to gather one artifact records an error and moves on. The
   terminal reason the runner already decided is never replaced, masked or
   upgraded -- a diagnostic crash must not turn POLICY_NOT_FOUND into
   UNEXPECTED_ERROR.
2. **Bounded, redacted, hashed.** Every text artifact has a documented cap,
   secrets are scrubbed before writing, and every file records its size and
   SHA-256 so the manifest can be reconciled against the disk.
"""

from __future__ import annotations

import hashlib
import json
import os
import pathlib
import re
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional, Sequence, Tuple

DIAGNOSTIC_SCHEMA = "ptf-capture-diagnostic/1.0"

#: Stamped on every diagnostic record and every manifest reference to one.
LABEL_NON_AUTHORITATIVE = "NON_AUTHORITATIVE"
LABEL_FAILURE_DIAGNOSTIC = "FAILURE_DIAGNOSTIC"
LABEL_NOT_FOR_EXTRACTION = "NOT_FOR_EXTRACTION"
DIAGNOSTIC_LABELS = (LABEL_NON_AUTHORITATIVE, LABEL_FAILURE_DIAGNOSTIC,
                     LABEL_NOT_FOR_EXTRACTION)

DIAGNOSTICS_DIRNAME = "diagnostics"

# --------------------------------------------------------------------------- #
# Size limits. Documented, enforced, and recorded when they truncate.
# --------------------------------------------------------------------------- #

MAX_DOM_BYTES = 4 * 1024 * 1024        # rendered HTML
MAX_TEXT_SNIPPET = 2_000               # one candidate element's text
MAX_LABEL_CHARS = 200                  # one control label
MAX_STRUCTURED_BYTES = 256 * 1024      # JSON-LD excerpt
MAX_HYDRATION_BYTES = 256 * 1024       # hydration excerpt
MAX_INLINE_SCRIPT_BYTES = 64 * 1024    # policy-relevant inline script only
MAX_INLINE_SCRIPTS = 5
MAX_EXCEPTION_MESSAGE = 500

# --------------------------------------------------------------------------- #
# Failure classes.
# --------------------------------------------------------------------------- #

#: Full DOM + geometry. These are the cases that could not be diagnosed.
FULL_DIAGNOSTIC_REASONS = frozenset({"POLICY_NOT_FOUND", "POLICY_OFF_SCREEN"})

#: Bounded diagnostics only -- enough to explain the refusal, no page dump.
#: An identity refusal is already fully explained by its own detail list, and
#: dumping a page we have just decided is the WRONG hotel is the last thing
#: this system should retain.
BOUNDED_DIAGNOSTIC_REASONS = frozenset({
    "IDENTITY_FAILED", "IDENTITY_UNVERIFIABLE", "IDENTITY_INCOMPLETE",
    "ACCESS_BLOCKED", "SEARCH_URL", "REDIRECTED_OFF_PROPERTY",
    "PROPERTY_CODE_MISMATCH", "IDENTITY_MISMATCH",
})

#: Infrastructure. Preserve whatever existed; never weaken retry/stop logic.
INFRASTRUCTURE_REASONS = frozenset({
    "SCREENSHOT_UNAVAILABLE", "NAVIGATION_FAILED", "NAVIGATION_TIMEOUT",
    "CAPTCHA_OR_CHALLENGE", "ACCESS_DENIED", "LOGIN_REQUIRED",
    "ADAPTER_UNAVAILABLE", "CAPTURE_WRITE_FAILED", "UNEXPECTED_ERROR",
})


def diagnostic_level(reason: str) -> str:
    """``full`` | ``bounded`` | ``infrastructure`` | ``none``."""
    if reason in FULL_DIAGNOSTIC_REASONS:
        return "full"
    if reason in BOUNDED_DIAGNOSTIC_REASONS:
        return "bounded"
    if reason in INFRASTRUCTURE_REASONS:
        return "infrastructure"
    return "none"


# --------------------------------------------------------------------------- #
# Redaction.
#
# The DOM of a hotel page should not contain credentials, but "should not" is
# not a control. Anything matching a secret shape is replaced before a byte
# reaches disk. Cookies, storage and headers are never read at all -- there is
# no code path here that requests them.
# --------------------------------------------------------------------------- #

_REDACTIONS: Tuple[Tuple[re.Pattern, str], ...] = (
    (re.compile(r'("?(?:api[_-]?key|apikey|access[_-]?token|auth[_-]?token|'
                r'bearer|password|secret|session[_-]?id|csrf[_-]?token|'
                r'x-goog-api-key)"?\s*[:=]\s*")([^"]{4,})(")', re.I), r"\1[REDACTED]\3"),
    # Consume the WHOLE header value, not the first token. `(\S+)` matched
    # only "Bearer" and left the credential itself in the output -- caught by
    # test_secret_shaped_content_is_redacted_from_the_dom.
    (re.compile(r"(Authorization\s*:\s*)([^\r\n<]+)", re.I), r"\1[REDACTED]"),
    (re.compile(r"(Set-Cookie\s*:\s*)([^\r\n]+)", re.I), r"\1[REDACTED]"),
    (re.compile(r"\bBearer\s+[A-Za-z0-9\-._~+/]{12,}=*", re.I), "Bearer [REDACTED]"),
    (re.compile(r"\bAIza[0-9A-Za-z\-_]{20,}\b"), "[REDACTED_API_KEY]"),
    (re.compile(r"\bsk-[A-Za-z0-9]{16,}\b"), "[REDACTED_API_KEY]"),
)

#: Field names that must never appear in a diagnostic record.
FORBIDDEN_FIELDS = frozenset({
    "cookies", "cookie", "authorization", "headers", "local_storage",
    "session_storage", "localStorage", "sessionStorage", "api_key", "apiKey",
    "access_token", "auth_token", "password", "secret", "network_log",
})


def redact(text: str) -> str:
    """Scrub secret-shaped substrings. Applied to every text artifact."""
    if not text:
        return ""
    out = text
    for pattern, replacement in _REDACTIONS:
        out = pattern.sub(replacement, out)
    return out


def assert_no_forbidden_fields(payload: Any, *, path: str = "") -> None:
    """Fail closed if a diagnostic record grows a field it must not have."""
    if isinstance(payload, dict):
        for key, value in payload.items():
            if str(key) in FORBIDDEN_FIELDS:
                raise DiagnosticError(
                    "diagnostic record may not contain %r (at %s)" % (key, path or "root"))
            assert_no_forbidden_fields(value, path="%s.%s" % (path, key))
    elif isinstance(payload, (list, tuple)):
        for i, item in enumerate(payload):
            assert_no_forbidden_fields(item, path="%s[%d]" % (path, i))


class DiagnosticError(ValueError):
    """Raised when a diagnostic record is malformed or unsafe to write."""


# --------------------------------------------------------------------------- #
# Artifact bookkeeping.
# --------------------------------------------------------------------------- #

STATUS_OK = "ok"
STATUS_FAILED = "failed"
STATUS_SKIPPED = "skipped"
STATUS_TRUNCATED = "truncated"


@dataclass
class ArtifactRecord:
    """One preserved file. Every field is required by the contract."""

    artifact_type: str
    relative_path: str = ""
    bytes: int = 0
    sha256: str = ""
    status: str = STATUS_OK
    error: str = ""
    truncated: bool = False

    def to_dict(self) -> dict:
        return {
            "artifact_type": self.artifact_type,
            "relative_path": self.relative_path,
            "bytes": self.bytes,
            "sha256": self.sha256,
            "status": self.status,
            "error": self.error,
            "truncated": self.truncated,
        }


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _atomic_write(path: pathlib.Path, data: bytes) -> None:
    """Write via a temp file in the same directory, then replace.

    A half-written diagnostic that still hashes and sizes as if complete would
    be worse than no diagnostic, because the manifest would reconcile against
    a lie.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("wb") as fh:
        fh.write(data)
        fh.flush()
        os.fsync(fh.fileno())
    os.replace(str(tmp), str(path))


def attempt_dir(batch_dir, hotel_id: str, *, attempt: int = 1) -> pathlib.Path:
    """``<batch>/diagnostics/<hotel_id>/attempt-<n>/``, never reusing one.

    If the requested attempt directory exists, the next free number is used.
    A prior attempt's evidence is exactly what a comparison needs; silently
    overwriting it would destroy the ability to see that a failure reproduced.
    """
    root = pathlib.Path(batch_dir) / DIAGNOSTICS_DIRNAME / _safe_component(hotel_id)
    n = max(1, int(attempt or 1))
    while (root / ("attempt-%d" % n)).exists():
        n += 1
    return root / ("attempt-%d" % n)


_UNSAFE = re.compile(r"[^A-Za-z0-9._-]+")


def _safe_component(value: str) -> str:
    cleaned = _UNSAFE.sub("-", (value or "unknown").strip()).strip("-")
    return cleaned[:120] or "unknown"


# --------------------------------------------------------------------------- #
# The collector.
# --------------------------------------------------------------------------- #

@dataclass
class DiagnosticContext:
    """Whatever the runner had in scope at the moment of failure.

    Every field is optional on purpose: the failure points differ in what
    exists, and a diagnostic that demanded all of them would collect nothing
    from the earliest ones.
    """

    hotel_id: str
    reason: str
    official_url: str = ""
    candidate_id: str = ""
    brand: str = ""
    attempt: int = 1
    detail: Tuple[str, ...] = ()
    retry_classification: str = ""
    exception_class: str = ""
    exception_message: str = ""
    identity_outcome: str = ""
    identity_keys: Tuple[str, ...] = ()
    property_code: str = ""
    session: Any = None
    dom: Any = None
    adapter: Any = None
    policy_location: Any = None
    policy_box: Any = None
    policy_box_after: Any = None
    viewport: Tuple[int, int] = (0, 0)
    interaction_log: Tuple[dict, ...] = ()
    screenshot_png: Optional[bytes] = None


class DiagnosticCollector:
    """Gathers failure evidence. Never raises to the runner."""

    def __init__(self, batch_dir, *, clock: Optional[Callable[[], float]] = None):
        self.batch_dir = pathlib.Path(batch_dir)
        self._clock = clock

    # -- individual collectors ------------------------------------------- #

    def _guard(self, artifact_type: str, fn: Callable[[], Optional[Tuple[str, bytes, bool]]],
               out_dir: pathlib.Path, records: List[ArtifactRecord]) -> None:
        """Run one collector in isolation.

        A failure here is recorded against that artifact and nothing else --
        the remaining artifacts still collect, and the runner's terminal reason
        is untouched.
        """
        try:
            produced = fn()
        except Exception as exc:                       # noqa: BLE001 - isolation
            records.append(ArtifactRecord(
                artifact_type=artifact_type, status=STATUS_FAILED,
                error="%s: %s" % (exc.__class__.__name__, str(exc)[:MAX_EXCEPTION_MESSAGE])))
            return
        if produced is None:
            records.append(ArtifactRecord(artifact_type=artifact_type,
                                          status=STATUS_SKIPPED,
                                          error="not available at this failure point"))
            return
        filename, data, truncated = produced
        try:
            _atomic_write(out_dir / filename, data)
        except Exception as exc:                       # noqa: BLE001 - isolation
            records.append(ArtifactRecord(
                artifact_type=artifact_type, status=STATUS_FAILED,
                error="write failed: %s" % str(exc)[:MAX_EXCEPTION_MESSAGE]))
            return
        records.append(ArtifactRecord(
            artifact_type=artifact_type, relative_path=filename, bytes=len(data),
            sha256=_sha256_bytes(data),
            status=STATUS_TRUNCATED if truncated else STATUS_OK,
            truncated=truncated))

    def _dom_artifact(self, ctx: DiagnosticContext):
        html = getattr(ctx.dom, "html", "") or ""
        if not html:
            return None
        cleaned = redact(html).encode("utf-8", errors="replace")
        truncated = len(cleaned) > MAX_DOM_BYTES
        return ("rendered_dom.html", cleaned[:MAX_DOM_BYTES], truncated)

    def _structured_artifact(self, ctx: DiagnosticContext):
        blocks = getattr(ctx.dom, "jsonld", None)
        if not blocks:
            return None
        body = redact(json.dumps(list(blocks), indent=2, ensure_ascii=False))
        data = body.encode("utf-8", errors="replace")
        truncated = len(data) > MAX_STRUCTURED_BYTES
        return ("structured_data.json", data[:MAX_STRUCTURED_BYTES], truncated)

    def _expansion_artifact(self, ctx: DiagnosticContext):
        adapter = ctx.adapter
        trace = {
            "labels": list(DIAGNOSTIC_LABELS),
            "anchor_terms_attempted": list(getattr(adapter, "extra_anchors", ()) or ()),
            "container_selectors_attempted": list(
                getattr(adapter, "container_selectors", ()) or ()),
            "expansion_controls_declared": [
                {"selector": sel, "text": txt}
                for sel, txt in (getattr(adapter, "expand_text_controls", ()) or ())],
            "expansion_controls_performed": [
                {k: v for k, v in dict(step).items() if str(k) not in FORBIDDEN_FIELDS}
                for step in (ctx.interaction_log or ())],
        }
        data = redact(json.dumps(trace, indent=2, ensure_ascii=False)).encode("utf-8")
        return ("expansion_trace.json", data, False)

    def _geometry_artifact(self, ctx: DiagnosticContext):
        geo = self._page_geometry(ctx)
        geo["labels"] = list(DIAGNOSTIC_LABELS)
        geo["policy_box"] = _box_to_dict(ctx.policy_box)
        geo["policy_box_after_screenshot"] = _box_to_dict(ctx.policy_box_after)
        geo["viewport"] = {"width": ctx.viewport[0] if ctx.viewport else 0,
                           "height": ctx.viewport[1] if len(ctx.viewport or ()) > 1 else 0}
        data = json.dumps(geo, indent=2, ensure_ascii=False).encode("utf-8")
        return ("geometry.json", data, False)

    def _viewport_png_artifact(self, ctx: DiagnosticContext):
        if ctx.screenshot_png:
            return ("viewport.png", ctx.screenshot_png, False)
        session = ctx.session
        if session is None or not hasattr(session, "screenshot_png"):
            return None
        png = session.screenshot_png()
        if not png:
            return None
        return ("viewport.png", png, False)

    # -- page geometry ---------------------------------------------------- #

    def _page_geometry(self, ctx: DiagnosticContext) -> dict:
        """Scroll, document and overlay geometry, read from the live page.

        Wrapped defensively: a page that refuses evaluation yields an error
        string rather than taking the whole diagnostic down.
        """
        session = ctx.session
        if session is None or not hasattr(session, "evaluate"):
            return {"collected": False, "error": "no session"}
        expression = """(function () {
          function boxes(sel) {
            var out = [];
            var nodes = document.querySelectorAll(sel);
            for (var i = 0; i < nodes.length && i < 12; i++) {
              var s = window.getComputedStyle(nodes[i]);
              if (s.position !== 'fixed' && s.position !== 'sticky') continue;
              var r = nodes[i].getBoundingClientRect();
              if (r.width <= 0 || r.height <= 0) continue;
              out.push({tag: nodes[i].tagName, position: s.position,
                        x: r.x, y: r.y, width: r.width, height: r.height,
                        zIndex: s.zIndex});
            }
            return out;
          }
          var scrollers = [];
          var all = document.querySelectorAll('*');
          for (var i = 0; i < all.length && scrollers.length < 12; i++) {
            var el = all[i];
            if (el.scrollHeight > el.clientHeight + 40 && el.clientHeight > 40) {
              var st = window.getComputedStyle(el).overflowY;
              if (st === 'auto' || st === 'scroll') {
                scrollers.push({tag: el.tagName, cls: (el.className || '').toString().slice(0, 80),
                                clientHeight: el.clientHeight, scrollHeight: el.scrollHeight,
                                scrollTop: el.scrollTop});
              }
            }
          }
          var ae = document.activeElement;
          return {
            collected: true,
            url: location.href,
            title: document.title,
            viewport: {width: window.innerWidth, height: window.innerHeight,
                       deviceScaleFactor: window.devicePixelRatio || 1},
            document: {width: document.documentElement.scrollWidth,
                       height: document.documentElement.scrollHeight},
            scroll: {x: window.scrollX, y: window.scrollY,
                     maxY: Math.max(0, document.documentElement.scrollHeight - window.innerHeight),
                     maxX: Math.max(0, document.documentElement.scrollWidth - window.innerWidth)},
            activeElement: ae ? (ae.tagName + (ae.id ? '#' + ae.id : '')) : '',
            fixedOverlays: boxes('div,header,footer,section,aside'),
            scrollContainers: scrollers,
            openDetails: document.querySelectorAll('details[open]').length,
            dialogsOpen: document.querySelectorAll('dialog[open],[role=dialog]').length,
            ariaExpandedTrue: document.querySelectorAll('[aria-expanded=true]').length,
            ariaExpandedFalse: document.querySelectorAll('[aria-expanded=false]').length
          };
        })()"""
        try:
            result = session.evaluate(expression)
        except Exception as exc:                       # noqa: BLE001 - isolation
            return {"collected": False,
                    "error": "%s: %s" % (exc.__class__.__name__,
                                         str(exc)[:MAX_EXCEPTION_MESSAGE])}
        return result if isinstance(result, dict) else {"collected": False,
                                                        "error": "non-dict result"}

    # -- entry point ------------------------------------------------------ #

    def collect(self, ctx: DiagnosticContext) -> Optional[dict]:
        """Collect and write diagnostics for one failed attempt.

        Returns the diagnostic record, or ``None`` when this failure class is
        not diagnosed. NEVER raises: any internal problem is recorded inside
        the record, because the caller is in the middle of returning a terminal
        outcome and must not be disturbed.
        """
        try:
            return self._collect(ctx)
        except Exception as exc:                       # noqa: BLE001 - isolation
            # Last-resort: the original failure reason must survive intact.
            try:
                return {
                    "schema": DIAGNOSTIC_SCHEMA,
                    "labels": list(DIAGNOSTIC_LABELS),
                    "hotel_id": ctx.hotel_id,
                    "terminal_reason": ctx.reason,
                    "collection_status": STATUS_FAILED,
                    "collection_error": "%s: %s" % (
                        exc.__class__.__name__, str(exc)[:MAX_EXCEPTION_MESSAGE]),
                    "artifacts": [],
                }
            except Exception:                          # noqa: BLE001
                return None

    def _collect(self, ctx: DiagnosticContext) -> Optional[dict]:
        level = diagnostic_level(ctx.reason)
        if level == "none":
            return None

        out_dir = attempt_dir(self.batch_dir, ctx.hotel_id, attempt=ctx.attempt)
        out_dir.mkdir(parents=True, exist_ok=True)
        records: List[ArtifactRecord] = []

        # Full: the two classes that could not be diagnosed at all.
        if level == "full":
            self._guard("rendered_dom", lambda: self._dom_artifact(ctx), out_dir, records)
            self._guard("structured_data", lambda: self._structured_artifact(ctx), out_dir, records)
            self._guard("expansion_trace", lambda: self._expansion_artifact(ctx), out_dir, records)
            self._guard("geometry", lambda: self._geometry_artifact(ctx), out_dir, records)
            self._guard("viewport_png", lambda: self._viewport_png_artifact(ctx), out_dir, records)
        elif level == "bounded":
            # An identity refusal is explained by its own detail; do NOT dump a
            # page already judged to be the wrong hotel.
            self._guard("geometry", lambda: self._geometry_artifact(ctx), out_dir, records)
        else:  # infrastructure -- whatever happened to exist, nothing forced.
            self._guard("geometry", lambda: self._geometry_artifact(ctx), out_dir, records)
            if ctx.screenshot_png:
                self._guard("viewport_png", lambda: self._viewport_png_artifact(ctx),
                            out_dir, records)

        record = {
            "schema": DIAGNOSTIC_SCHEMA,
            "labels": list(DIAGNOSTIC_LABELS),
            "non_authoritative": True,
            "not_for_extraction": True,
            "diagnostic_level": level,
            "hotel_id": ctx.hotel_id,
            "candidate_id": ctx.candidate_id,
            "official_url": ctx.official_url,
            "brand": ctx.brand,
            "attempt": ctx.attempt,
            "attempt_dir": out_dir.name,
            "relative_dir": str(pathlib.PurePosixPath(
                DIAGNOSTICS_DIRNAME, _safe_component(ctx.hotel_id), out_dir.name)),
            "terminal_reason": ctx.reason,
            "terminal_detail": list(ctx.detail or ()),
            "retry_classification": ctx.retry_classification,
            "exception_class": ctx.exception_class,
            "exception_message": redact(ctx.exception_message or "")[:MAX_EXCEPTION_MESSAGE],
            "identity_outcome": ctx.identity_outcome,
            "identity_keys": list(ctx.identity_keys or ()),
            "property_code": ctx.property_code,
            "page_url_at_failure": getattr(ctx.dom, "final_url", "") or "",
            "page_title": (getattr(ctx.dom, "title", "") or "")[:MAX_LABEL_CHARS],
            "collection_status": STATUS_OK,
            "artifacts": [r.to_dict() for r in records],
        }
        assert_no_forbidden_fields(record)

        data = json.dumps(record, indent=2, ensure_ascii=False).encode("utf-8")
        _atomic_write(out_dir / "diagnostic.json", data)
        record["self_sha256"] = _sha256_bytes(data)
        return record


def _box_to_dict(box: Any) -> Optional[dict]:
    if box is None:
        return None
    out = {}
    for name in ("x", "y", "width", "height", "scroll_y"):
        if hasattr(box, name):
            out[name] = getattr(box, name)
    return out or None


def is_diagnostic_artifact(artifacts: Any) -> bool:
    """True when an outcome's artifacts are failure diagnostics.

    Used by anything that must NOT treat diagnostics as capture evidence.
    """
    return (isinstance(artifacts, dict)
            and artifacts.get("schema") == DIAGNOSTIC_SCHEMA)
