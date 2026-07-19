"""AES-DATA-004E (Task 1) -- blocked-source taxonomy.

Purely a CLASSIFICATION/reporting layer over an existing ``FetchResult`` (and,
for a successful fetch, its ``SourceSnapshot``): it never changes what
``fetch.py`` returns, never changes ``FetchResult.reason``, and never feeds
into ``recommend.py`` -- READY/REVIEW/REJECT gating is completely unaffected
by this module. Its purpose is to answer "why, specifically, did this source
fail" with a richer, disclosed vocabulary than the single ``reason`` slug
already carries, for operator-facing reports (Task 8) and future triage.

Not every status below is reachable today. ``ROBOTS_DISALLOWED`` is declared
now (completing the taxonomy per Task 1) but the fetcher does not fetch or
parse ``robots.txt`` -- Task 4's allowed-improvements list does not include
robots handling, and no Wave 1 failure was robots-driven, so adding a whole
robots.txt subsystem is out of this phase's proportionate scope. This is
disclosed, not silently implied.
"""

from __future__ import annotations

from typing import Optional

from scripts.pettripfinder.importer import constants as C
from scripts.pettripfinder.importer.models import FetchResult, SourceSnapshot

# --------------------------------------------------------------------------- #
# Taxonomy (Task 1).
# --------------------------------------------------------------------------- #

FETCH_STATUS_FETCHABLE = "FETCHABLE"
FETCH_STATUS_HTTP_403_BLOCKED = "HTTP_403_BLOCKED"
FETCH_STATUS_ROBOTS_DISALLOWED = "ROBOTS_DISALLOWED"          # reserved, unreachable today
FETCH_STATUS_JAVASCRIPT_REQUIRED = "JAVASCRIPT_REQUIRED"
FETCH_STATUS_CAPTCHA_REQUIRED = "CAPTCHA_REQUIRED"
FETCH_STATUS_TIMEOUT = "TIMEOUT"
FETCH_STATUS_REDIRECT_LOOP = "REDIRECT_LOOP"
FETCH_STATUS_UNSUPPORTED_CONTENT = "UNSUPPORTED_CONTENT"
FETCH_STATUS_RATE_LIMITED = "RATE_LIMITED"
FETCH_STATUS_TRANSIENT_SERVER_ERROR = "TRANSIENT_SERVER_ERROR"
FETCH_STATUS_UNKNOWN_FETCH_FAILURE = "UNKNOWN_FETCH_FAILURE"

FETCH_STATUS_VALUES = frozenset({
    FETCH_STATUS_FETCHABLE, FETCH_STATUS_HTTP_403_BLOCKED,
    FETCH_STATUS_ROBOTS_DISALLOWED, FETCH_STATUS_JAVASCRIPT_REQUIRED,
    FETCH_STATUS_CAPTCHA_REQUIRED, FETCH_STATUS_TIMEOUT,
    FETCH_STATUS_REDIRECT_LOOP, FETCH_STATUS_UNSUPPORTED_CONTENT,
    FETCH_STATUS_RATE_LIMITED, FETCH_STATUS_TRANSIENT_SERVER_ERROR,
    FETCH_STATUS_UNKNOWN_FETCH_FAILURE,
})

# A "blocked" outcome an operator must never force to READY (mission
# doctrine: "Do not force blocked properties to READY").
FETCH_STATUS_BLOCKED_LIKE = frozenset({
    FETCH_STATUS_HTTP_403_BLOCKED, FETCH_STATUS_ROBOTS_DISALLOWED,
    FETCH_STATUS_CAPTCHA_REQUIRED, FETCH_STATUS_RATE_LIMITED,
})

_SERVER_ERROR_STATUSES = frozenset({500, 502, 503, 504})

# Conservative, deterministic CAPTCHA/challenge-page markers. Only used on a
# SUCCESSFUL fetch with unusually thin visible text (mirrors the existing
# javascript-shell heuristic's conservatism in source_snapshot.py) -- never
# used to bypass or solve anything, only to label the outcome so an operator
# does not mistake a challenge page for real page content.
_CAPTCHA_MARKERS = (
    "captcha", "are you a human", "verify you are a human",
    "unusual traffic", "automated requests", "checking your browser",
    "access denied", "robot check",
)
_CAPTCHA_TEXT_LEN_CEILING = 2000


def _looks_like_captcha(normalized_text: str) -> bool:
    text = (normalized_text or "")
    if len(text) >= _CAPTCHA_TEXT_LEN_CEILING:
        return False
    lowered = text.lower()
    return any(marker in lowered for marker in _CAPTCHA_MARKERS)


def classify_fetch_status(
    fetch_result: FetchResult, snapshot: Optional[SourceSnapshot] = None,
) -> str:
    """Deterministic refinement of ``fetch_result``/``snapshot`` into the
    Task 1 taxonomy. Never raises; unrecognized failure shapes fall back to
    ``UNKNOWN_FETCH_FAILURE`` rather than guessing."""
    if fetch_result.ok:
        text = snapshot.normalized_text if snapshot is not None else ""
        if snapshot is not None and C.REASON_JAVASCRIPT_RENDERED in snapshot.fetch_warnings:
            return FETCH_STATUS_JAVASCRIPT_REQUIRED
        if _looks_like_captcha(text):
            return FETCH_STATUS_CAPTCHA_REQUIRED
        return FETCH_STATUS_FETCHABLE

    reason = fetch_result.reason
    status = fetch_result.http_status
    if reason == C.REASON_BLOCKED_SOURCE:
        return FETCH_STATUS_HTTP_403_BLOCKED
    if reason == C.REASON_RATE_LIMITED_SOURCE:
        return FETCH_STATUS_RATE_LIMITED
    if reason == C.REASON_FETCH_TIMEOUT:
        return FETCH_STATUS_TIMEOUT
    if reason == C.REASON_REDIRECT_LIMIT:
        return FETCH_STATUS_REDIRECT_LOOP
    if reason in (C.REASON_UNSUPPORTED_CONTENT_TYPE, C.REASON_PDF_SOURCE):
        return FETCH_STATUS_UNSUPPORTED_CONTENT
    if reason == C.REASON_FETCH_FAILED and status in _SERVER_ERROR_STATUSES:
        return FETCH_STATUS_TRANSIENT_SERVER_ERROR
    return FETCH_STATUS_UNKNOWN_FETCH_FAILURE
