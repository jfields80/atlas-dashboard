"""Wait, bounded, until a page has actually rendered its identity.

``Page.domContentEventFired`` says the markup arrived. It says nothing about
whether a single-page app has rendered the JSON-LD, the property name or
anything else that identifies the hotel. The runner used to take exactly one
snapshot at that moment and let its contents decide the hotel's fate, so a page
that was merely slow was indistinguishable from a page with no identity:
Aloft Columbus University District failed IDENTITY_UNVERIFIABLE after 7.2
seconds and then succeeded, unchanged, on a later run.

This module polls instead. It is deliberately narrow:

  * it decides only WHEN TO STOP WAITING. ``verify_identity`` remains the gate,
    and is applied afterwards exactly as before. Nothing here can admit a page
    that the identity check would refuse -- a readiness signal is a reason to
    look, never a reason to accept;
  * it is brand-neutral. An adapter may contribute a selector, which can only
    add a way to notice the page is ready, never remove a check;
  * it is bounded: a maximum wait, a fixed interval, and a stability
    requirement. It never refreshes, never re-navigates, and never retries the
    hotel;
  * a challenge page stops the wait immediately. Waiting politely for a bot
    wall to hydrate would be the wrong instinct entirely.
"""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable, List, Optional, Sequence, Tuple

from .contracts import DomSnapshot, ObservedIdentity
from .doctrine import (
    HYDRATION_POLL_SECONDS, HYDRATION_STABLE_CHECKS,
    HYDRATION_TEXT_DRIFT_TOLERANCE, HYDRATION_TIMEOUT_SECONDS,
)
from .identity_check import identity_from_jsonld, observe_identity

# The strong signals, strongest first. Each names a way the page has shown us
# who it is; none of them is on its own sufficient to ACCEPT the page.
SIGNAL_JSONLD_HOTEL = "jsonld_hotel"
SIGNAL_URL_CODE_AND_NAME = "url_code_and_visible_name"
SIGNAL_ADAPTER_SELECTOR = "adapter_identity_selector"
SIGNAL_OBSERVED_IDENTITY = "observed_name_and_contact"

STRONG_SIGNALS = (SIGNAL_JSONLD_HOTEL, SIGNAL_URL_CODE_AND_NAME,
                  SIGNAL_ADAPTER_SELECTOR, SIGNAL_OBSERVED_IDENTITY)

# Bot-defence interstitials that replace the page with a challenge loader.
#
# These carry NO text, so `_page_block_reason` -- which reads rendered text --
# cannot see them, and the hotel would time out as IDENTITY_UNVERIFIABLE:
# "we could not tell who this is" rather than the truth, "this brand refused
# us". Hyatt serves exactly this: an 811-byte body holding window.KPSDK and an
# ips.js loader, unchanged across 15 seconds with the page blank.
#
# Recognising it is honest reporting, not evasion. The response is still to
# stop and hand the hotel to a human.
_CHALLENGE_SHELL_MARKERS = (
    "KPSDK",            # Kasada
    "_Incapsula_Resource",
    "distil_r_captcha",
    "/_sec/cp_challenge",
    "px-captcha",       # PerimeterX
    "awswaf",           # AWS WAF challenge
)

#: A body this small cannot be a hotel page; used only together with a marker.
CHALLENGE_SHELL_MAX_HTML_BYTES = 8000


def looks_like_challenge_shell(dom: DomSnapshot) -> str:
    """Is this a bot-defence interstitial rather than a page? Returns a slug."""
    if dom is None:
        return ""
    html = dom.html or ""
    if len(html) > CHALLENGE_SHELL_MAX_HTML_BYTES:
        return ""
    if (dom.text or "").strip():
        return ""                       # a page with words is not a bare shell
    for marker in _CHALLENGE_SHELL_MARKERS:
        if marker in html:
            return "captcha_or_challenge_page"
    return ""


@dataclass(frozen=True)
class ReadinessResult:
    """What the wait saw. Recorded on the capture as diagnostics."""

    ready: bool
    signal: str = ""
    checks: int = 0
    waited_seconds: float = 0.0
    timed_out: bool = False
    blocked_reason: str = ""
    dom: Optional[DomSnapshot] = None
    identity: Optional[ObservedIdentity] = None
    signal_history: Tuple[str, ...] = ()

    def to_dict(self) -> dict:
        return {
            "ready": self.ready,
            "signal": self.signal,
            "checks": self.checks,
            "waited_seconds": round(self.waited_seconds, 3),
            "timed_out": self.timed_out,
            "blocked_reason": self.blocked_reason,
            "signal_history": list(self.signal_history),
            "identity": self.identity.to_dict() if self.identity else None,
        }


def _name_tokens(name: str) -> List[str]:
    """Distinctive words from a hotel name, for a visible-text check.

    Brand words alone would match a brand landing page, so tokens shorter than
    four characters and the commonest chain words are dropped.
    """
    stop = {"hotel", "hotels", "inn", "inns", "suites", "suite", "the", "and",
            "by", "at", "of", "resort", "motel"}
    out = []
    for raw in (name or "").replace("-", " ").replace("&", " ").split():
        tok = "".join(c for c in raw if c.isalnum()).lower()
        if len(tok) >= 4 and tok not in stop:
            out.append(tok)
    return out


def identity_signal(dom: DomSnapshot, entry, *,
                    adapter=None, session=None) -> str:
    """The strongest identity signal this snapshot shows, or "".

    Pure with respect to the snapshot. ``session`` is consulted only for an
    adapter-supplied selector, and only when the cheaper checks found nothing.
    """
    if dom is None:
        return ""

    # 1. A Hotel JSON-LD block carrying a name is the strongest thing a page
    #    can say about itself, and it is what identity_check prefers.
    if identity_from_jsonld(dom.jsonld).name:
        return SIGNAL_JSONLD_HOTEL

    text = dom.text or ""
    code = (getattr(entry, "expected_property_code", "") or "").lower()

    # 2. The property code in the page's own URL, corroborated by the hotel's
    #    distinctive words appearing in rendered text.
    if code and text:
        in_url = code in (dom.final_url or "").lower() or \
            code in (dom.canonical_url or "").lower()
        if in_url:
            tokens = _name_tokens(getattr(entry, "hotel_name", ""))
            low = text.lower()
            if tokens and all(t in low for t in tokens[:2]):
                return SIGNAL_URL_CODE_AND_NAME

    # 3. Whatever identity_check itself can already observe, corroborated.
    observed = observe_identity(dom, known_codes=[code] if code else [])
    if observed.name and (observed.phone or observed.street):
        return SIGNAL_OBSERVED_IDENTITY

    # 4. A brand adapter may point at a selector that only appears once the
    #    property view has rendered. Additive only.
    if adapter is not None and session is not None:
        getter = getattr(adapter, "identity_selectors", None)
        selectors: Sequence[str] = ()
        if callable(getter):
            try:
                selectors = getter() or ()
            except Exception:                          # noqa: BLE001 - advisory
                selectors = ()
        for selector in selectors:
            try:
                if session.query_selector_exists(selector):
                    return SIGNAL_ADAPTER_SELECTOR
            except Exception:                          # noqa: BLE001 - advisory
                continue
    return ""


def _text_is_settling(previous: DomSnapshot, current: DomSnapshot) -> bool:
    """Has the rendered text stopped materially changing?"""
    a = len((previous.text or "").encode("utf-8"))
    b = len((current.text or "").encode("utf-8"))
    if a == 0 and b == 0:
        return True
    biggest = max(a, b, 1)
    return (abs(b - a) / biggest) <= HYDRATION_TEXT_DRIFT_TOLERANCE


def wait_for_identity(session, entry, *, adapter=None,
                      timeout: float = HYDRATION_TIMEOUT_SECONDS,
                      interval: float = HYDRATION_POLL_SECONDS,
                      stable_checks: int = HYDRATION_STABLE_CHECKS,
                      clock: Callable[[], float] = time.monotonic,
                      sleep: Callable[[float], None] = time.sleep,
                      block_reason: Callable[[str], str] = None) -> ReadinessResult:
    """Poll until the page shows a stable identity signal, or time out.

    Never refreshes, never re-navigates, never retries the hotel: the only
    actions are ``snapshot()`` and an optional selector probe.
    """
    if block_reason is None:
        from ..operator_capture import _page_block_reason
        block_reason = _page_block_reason

    started = clock()
    deadline = started + timeout
    checks = 0
    history: List[str] = []
    consecutive = 0
    previous: Optional[DomSnapshot] = None
    dom: Optional[DomSnapshot] = None
    last_signal = ""

    while True:
        dom = session.snapshot()
        checks += 1

        # A bot wall or denial ends the wait at once. The textless
        # interstitial is checked too, because a challenge that renders no
        # words would otherwise be reported as "we could not identify this
        # hotel" -- which is not what happened.
        blocked = block_reason(dom.text or "") or looks_like_challenge_shell(dom)
        if blocked:
            return ReadinessResult(
                ready=False, checks=checks, waited_seconds=clock() - started,
                blocked_reason=blocked, dom=dom,
                signal_history=tuple(history))

        signal = identity_signal(dom, entry, adapter=adapter, session=session)
        history.append(signal or "-")

        if signal and signal == last_signal and previous is not None \
                and _text_is_settling(previous, dom):
            consecutive += 1
        elif signal:
            consecutive = 1
        else:
            consecutive = 0

        last_signal = signal
        previous = dom

        if signal and consecutive >= stable_checks:
            code = (getattr(entry, "expected_property_code", "") or "")
            return ReadinessResult(
                ready=True, signal=signal, checks=checks,
                waited_seconds=clock() - started, dom=dom,
                identity=observe_identity(dom, known_codes=[code] if code else []),
                signal_history=tuple(history))

        if clock() >= deadline:
            code = (getattr(entry, "expected_property_code", "") or "")
            return ReadinessResult(
                ready=False, signal=signal, checks=checks,
                waited_seconds=clock() - started, timed_out=True, dom=dom,
                identity=observe_identity(dom, known_codes=[code] if code else []),
                signal_history=tuple(history))

        sleep(interval)
