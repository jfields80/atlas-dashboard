"""PTF-WORKERS-005 -- browser-rendered page fetcher.

WHY THIS EXISTS
---------------
Some official hotel pages return their pet policy only after JavaScript runs,
and some return HTTP 403 to a plain ``requests`` client while serving the same
public page to an ordinary browser. ``RequestsPageFetcher`` therefore reports
ACCESS_BLOCKED for pages a human can read perfectly well -- Staybridge Suites
Columbus-Dublin is exactly this case.

This module renders such a page with a real browser engine and returns the
result through the SAME ``PageFetcher`` protocol
(``fetch(url) -> FetchResult``). That is the entire integration: because
``source_retrieval.retrieve_official_source`` already accepts an injected
fetcher, snapshotting, hashing, identity assessment, brand-scope
classification and routing all continue to work with no change.

AUTHORIZED POSTURE -- DETECT, CLASSIFY, STOP
-------------------------------------------
The operator authorization for this module is narrow and worth restating where
the code lives: a normal Chromium browser may view public official pages that
an ordinary visitor can view. It does NOT authorize, and this module does not
implement:

    * CAPTCHA solving
    * proxy or IP rotation
    * stealth / fingerprint-evasion plugins
    * authentication or login-wall bypass
    * repeated attempts against 403 or 429
    * circumventing a hard bot challenge

When a challenge, login wall, CAPTCHA, access denial, or an unsupported
consent gate appears, this fetcher records what it saw and gives up. There is
no retry path for any of those outcomes, and a test asserts no evasion
identifier exists in this file. The user agent is the honest
``C.USER_AGENT`` -- the same string the static fetcher sends.

THE THREE HASHES
----------------
``raw_transport_hash``  sha256 of the pre-JavaScript HTTP response body. This
                        is what the server actually sent and is the most
                        reproducible of the three.
``rendered_dom_hash``   sha256 of the post-JavaScript DOM. **A point-in-time
                        attestation, NOT a reproducibility guarantee.** Session
                        ids, A/B buckets, timestamps and ad slots all change
                        between loads, so an identical page can hash
                        differently minutes apart. It answers "what did we
                        see at this instant", never "what will anyone see".
``normalized_text_hash`` sha256 of bounded visible text -- produced downstream
                        by ``source_snapshot.build_snapshot`` and the anchor
                        every evidence quote is validated against. Far more
                        stable than the DOM, which is why it, not the DOM
                        hash, is the evidence anchor.

Because a rendered DOM is not reproducible, a single capture cannot be trusted
on its own. Every page is therefore captured TWICE in the same session and the
two normalized texts compared; material divergence yields
``REASON_RENDER_NONDETERMINISTIC`` and the page is withheld rather than pinned
to whichever capture happened to arrive first.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Protocol, Sequence, Tuple
from urllib.parse import urlsplit

from scripts.pettripfinder.importer import constants as C
from scripts.pettripfinder.importer.fetch import (
    check_url_shape, classify_response, resolve_and_validate_host,
)
from scripts.pettripfinder.importer.models import FetchResult

BROWSER_FETCH_VERSION = "ptf-workers-005/1.0.0"

CAPTURE_METHOD_BROWSER_RENDERED = "BROWSER_RENDERED"
CAPTURE_METHOD_HTTP_STATIC = "HTTP_STATIC"

# A model research report is prose, not a page. Feeding one back in as a URL to
# render would launder model output into official evidence -- the precise
# confusion PTF-WORKERS-004 was built to prevent. Rejected by construction.
MODEL_RESEARCH_URN_PREFIX = "urn:atlas:model-research-report:"


# --------------------------------------------------------------------------- #
# Detection vocabularies. Deterministic substring markers, deliberately
# conservative: a false CHALLENGE_DETECTED costs one withheld page, while a
# missed one would mean treating a challenge interstitial as hotel policy.
# --------------------------------------------------------------------------- #

_CHALLENGE_MARKERS = (
    "captcha", "recaptcha", "hcaptcha", "are you a human",
    "verify you are a human", "unusual traffic", "automated requests",
    "checking your browser", "access denied", "robot check",
    "cf-challenge", "cf_chl_", "just a moment", "ray id",
    "pardon our interruption", "please enable cookies and reload",
)
_LOGIN_MARKERS = (
    "sign in to continue", "log in to continue", "please sign in",
    "please log in", "member sign in", "enter your password",
    "session expired", "you must be logged in",
)
# Consent MARKERS say a banner exists; that alone is not a failure. The gate is
# only reported when a banner is present AND the visible text is implausibly
# thin, i.e. the content really is behind it.
_CONSENT_MARKERS = (
    "we use cookies", "cookie preferences", "manage cookies",
    "accept all cookies", "your privacy choices", "cookie settings",
    "consent preferences", "privacy preference center",
)
_CONSENT_TEXT_LEN_FLOOR = 1200
_CHALLENGE_TEXT_LEN_CEILING = 3000


def _has(text: str, markers: Sequence[str]) -> bool:
    low = (text or "").lower()
    return any(m in low for m in markers)


def detect_challenge(text: str) -> bool:
    """A hard bot challenge. Requires a marker AND thin content, mirroring the
    existing CAPTCHA heuristic's conservatism -- a real hotel page can mention
    "access denied" in an unrelated FAQ and must not be discarded for it."""
    return len(text or "") < _CHALLENGE_TEXT_LEN_CEILING and _has(text, _CHALLENGE_MARKERS)


def detect_login_required(text: str) -> bool:
    return _has(text, _LOGIN_MARKERS)


def detect_consent_banner(text: str) -> bool:
    return _has(text, _CONSENT_MARKERS)


def detect_consent_gate(text: str) -> bool:
    """Banner present AND the page is essentially empty behind it."""
    return detect_consent_banner(text) and len(text or "") < _CONSENT_TEXT_LEN_FLOOR


def text_divergence(a: str, b: str) -> float:
    """Normalized length-based divergence between two captures, 0.0 .. 1.0.

    Deliberately a cheap, deterministic measure rather than a diff ratio: the
    question is only "did this page materially change between two reads",
    and a character-level diff would make the threshold hard to reason about
    and slow on 50 KB of text.
    """
    a, b = a or "", b or ""
    if a == b:
        return 0.0
    longest = max(len(a), len(b))
    if longest == 0:
        return 0.0
    return abs(len(a) - len(b)) / longest if len(a) != len(b) else _char_divergence(a, b)


def _char_divergence(a: str, b: str) -> float:
    """Same length, different content: fraction of differing positions."""
    if not a:
        return 0.0
    diff = sum(1 for x, y in zip(a, b) if x != y)
    return diff / len(a)


# --------------------------------------------------------------------------- #
# Driver seam (so every test runs offline, with no browser).
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class BrowserRenderResult:
    """Raw facts a browser driver reports. No classification lives here."""

    requested_url: str
    final_url: str = ""
    http_status: int = 0
    content_type: str = ""
    transport_body: bytes = b""            # pre-JavaScript response body
    dom_html: str = ""                     # post-JavaScript DOM, capture 1
    dom_html_second: str = ""              # capture 2 (stability check)
    visible_text: str = ""                 # innerText, capture 1
    visible_text_second: str = ""          # innerText, capture 2
    navigation_urls: Tuple[str, ...] = ()  # every navigation the page performed
    redirect_chain: Tuple[str, ...] = ()
    response_headers: Tuple[Tuple[str, str], ...] = ()
    interactions: Tuple[str, ...] = ()     # selectors clicked, in order
    elapsed_ms: int = 0                    # wall time inside the driver
    error: str = ""                        # driver-level failure slug


class BrowserDriver(Protocol):
    def render(self, url: str, *, navigation_timeout_ms: int, total_budget_ms: int,
               expand_content: bool) -> BrowserRenderResult: ...


# --------------------------------------------------------------------------- #
# Capture sidecar: everything a FetchResult has no field for.
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class BrowserCapture:
    """What one browser attempt did, recorded on EVERY post-navigation exit.

    A failed attempt is still an audit record. The live Staybridge proof
    returned HTTP 403 and produced no capture at all, which meant the artifact
    could not answer "what did we actually try, and how long did it take" --
    the attempt itself is evidence, independent of whether content arrived.
    """

    requested_url: str
    final_url: str
    capture_method: str = CAPTURE_METHOD_BROWSER_RENDERED
    http_status: int = 0
    content_type: str = ""
    elapsed_ms: int = 0
    outcome_reason: str = ""               # "" on success, else the reason slug
    raw_transport_hash: str = ""
    rendered_dom_hash: str = ""
    transport_bytes: int = 0
    dom_bytes: int = 0
    navigation_urls: Tuple[str, ...] = ()
    redirect_chain: Tuple[str, ...] = ()
    interactions: Tuple[str, ...] = ()
    consent_banner_detected: bool = False
    stability_divergence: float = 0.0
    stable: bool = True
    notes: Tuple[str, ...] = ()

    def to_dict(self) -> Dict:
        return {
            "browser_fetch_version": BROWSER_FETCH_VERSION,
            "requested_url": self.requested_url,
            "final_url": self.final_url,
            "capture_method": self.capture_method,
            "http_status": self.http_status,
            "content_type": self.content_type,
            "elapsed_ms": self.elapsed_ms,
            "outcome_reason": self.outcome_reason,
            "raw_transport_hash": self.raw_transport_hash,
            "rendered_dom_hash": self.rendered_dom_hash,
            "rendered_dom_hash_meaning":
                "point-in-time attestation of the rendered DOM; NOT a "
                "reproducibility guarantee",
            "transport_bytes": self.transport_bytes,
            "dom_bytes": self.dom_bytes,
            "navigation_urls": list(self.navigation_urls),
            "redirect_chain": list(self.redirect_chain),
            "interactions": list(self.interactions),
            "consent_banner_detected": self.consent_banner_detected,
            "stability_divergence": round(self.stability_divergence, 6),
            "stable": self.stable,
            "notes": list(self.notes),
        }


def _sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data or b"").hexdigest()


def _sha256_text(text: str) -> str:
    return hashlib.sha256((text or "").encode("utf-8")).hexdigest()


# --------------------------------------------------------------------------- #
# The fetcher.
# --------------------------------------------------------------------------- #

class BrowserPageFetcher:
    """SSRF-safe, allowlist-bound, browser-rendering ``PageFetcher``.

    Every safety decision that ``RequestsPageFetcher`` makes is made here too,
    with one honest difference recorded in the design: Chromium performs its
    own DNS resolution, so this fetcher validates the host before navigating
    and validates every navigation URL afterwards, but cannot pin the resolved
    address for the connection itself. DNS rebinding is therefore not fully
    excluded; the public-domain allowlist is what keeps that risk acceptable.
    """

    def __init__(self, driver: BrowserDriver, *, allowed_domains: Sequence[str],
                 expand_content: bool = True,
                 navigation_timeout_ms: int = C.RENDER_NAVIGATION_TIMEOUT_MS,
                 total_budget_ms: int = C.RENDER_TOTAL_BUDGET_MS,
                 max_pages: int = C.RENDER_MAX_PAGES_PER_RUN,
                 resolve_host: bool = True):
        if not allowed_domains:
            raise ValueError(
                "BrowserPageFetcher requires a non-empty official-domain allowlist; "
                "an unrestricted browser fetch is not an authorized path")
        self._driver = driver
        self._allowed = tuple(allowed_domains)
        self._expand_content = expand_content
        self._navigation_timeout_ms = navigation_timeout_ms
        self._total_budget_ms = total_budget_ms
        self._max_pages = max_pages
        self._resolve_host = resolve_host
        self._pages_fetched = 0
        self.captures: List[BrowserCapture] = []

    # -- allowlist -------------------------------------------------------- #

    def _host_allowed(self, url: str) -> bool:
        from services.research_workers.web_research import host_in_allowlist
        return host_in_allowlist(urlsplit(url).hostname or "", self._allowed)

    def _validate_url(self, url: str, *, is_hop: bool) -> Tuple[bool, str]:
        """Shape + allowlist (+ DNS on the initial URL only)."""
        ok, reason = check_url_shape(url)
        if not ok:
            return (False, C.REASON_UNSAFE_REDIRECT if is_hop and reason == C.REASON_UNSAFE_HOST
                    else reason)
        if not self._host_allowed(url):
            return (False, C.REASON_OFF_ALLOWLIST_NAVIGATION)
        return (True, "")

    # -- protocol --------------------------------------------------------- #

    def fetch(self, url: str) -> FetchResult:
        if url.startswith(MODEL_RESEARCH_URN_PREFIX):
            return FetchResult(url, False, reason=C.REASON_UNSAFE_URL,
                               warnings=("model_research_report_is_not_a_page",))
        if self._pages_fetched >= self._max_pages:
            return FetchResult(url, False, reason=C.REASON_FETCH_FAILED,
                               warnings=("render_page_budget_exhausted",))

        ok, reason = self._validate_url(url, is_hop=False)
        if not ok:
            return FetchResult(url, False, reason=reason)
        if self._resolve_host:
            host = urlsplit(url).hostname or ""
            ok, reason, _ips = resolve_and_validate_host(host)
            if not ok:
                return FetchResult(url, False, reason=reason)

        self._pages_fetched += 1
        render = self._driver.render(
            url, navigation_timeout_ms=self._navigation_timeout_ms,
            total_budget_ms=self._total_budget_ms, expand_content=self._expand_content)

        # From here on EVERY exit records a BrowserCapture. `_record` is the
        # single funnel, so a future exit path cannot silently skip the audit
        # trail the way the HTTP-status path originally did.
        def _record(reason: str) -> None:
            self.captures.append(self._capture(
                url, render.final_url or url, render, False, 0.0, False,
                ["attempt_recorded_without_content"] if reason else [], reason))

        if render.error:
            _record(render.error)
            return FetchResult(url, False, reason=render.error,
                               final_url=render.final_url,
                               redirect_chain=tuple(render.redirect_chain))

        # Every URL the page navigated to, plus the final URL, must stay on the
        # allowlist. A page that bounced us to a different property or a
        # third-party consent host is not this property's evidence.
        for hop in tuple(render.navigation_urls) + tuple(render.redirect_chain):
            ok, reason = self._validate_url(hop, is_hop=True)
            if not ok:
                _record(reason)
                return FetchResult(url, False, reason=reason,
                                   final_url=render.final_url,
                                   redirect_chain=tuple(render.redirect_chain))
        final_url = render.final_url or url
        ok, reason = self._validate_url(final_url, is_hop=True)
        if not ok:
            _record(reason)
            return FetchResult(url, False, reason=reason, final_url=final_url,
                               redirect_chain=tuple(render.redirect_chain))

        # HTTP-level rejection (403 / 429 / non-2xx / wrong content type). This
        # is the path the live Staybridge 403 took, and the one that previously
        # recorded nothing at all.
        ok, reason = classify_response(render.http_status, render.content_type)
        if not ok:
            _record(reason)
            return FetchResult(url, False, final_url=final_url,
                               http_status=render.http_status,
                               content_type=render.content_type, reason=reason,
                               redirect_chain=tuple(render.redirect_chain),
                               response_headers=tuple(render.response_headers))

        text = render.visible_text or ""
        notes: List[str] = []

        # Detection order matters: a challenge page can also carry a consent
        # banner, and reporting the consent gate would understate what happened.
        if detect_challenge(text):
            return self._blocked(url, final_url, render, C.REASON_CHALLENGE_DETECTED)
        if detect_login_required(text):
            return self._blocked(url, final_url, render, C.REASON_LOGIN_REQUIRED)
        consent_banner = detect_consent_banner(text)
        if detect_consent_gate(text):
            return self._blocked(url, final_url, render, C.REASON_CONSENT_GATED)
        if consent_banner:
            notes.append("consent_banner_present_content_readable")

        divergence = text_divergence(render.visible_text, render.visible_text_second)
        stable = divergence < C.RENDER_STABILITY_MAX_DIVERGENCE
        if not stable:
            capture = self._capture(url, final_url, render, consent_banner, divergence,
                                    False, notes + ["withheld_unstable_render"],
                                    C.REASON_RENDER_NONDETERMINISTIC)
            self.captures.append(capture)
            return FetchResult(url, False, final_url=final_url,
                               http_status=render.http_status,
                               content_type=render.content_type,
                               reason=C.REASON_RENDER_NONDETERMINISTIC,
                               redirect_chain=tuple(render.redirect_chain),
                               response_headers=tuple(render.response_headers),
                               warnings=("stability_divergence_%.4f" % divergence,))

        dom_bytes = (render.dom_html or "").encode("utf-8")
        if len(dom_bytes) > C.MAX_RESPONSE_BYTES:
            _record(C.REASON_OVERSIZED_RESPONSE)
            return FetchResult(url, False, final_url=final_url,
                               http_status=render.http_status,
                               content_type=render.content_type,
                               reason=C.REASON_OVERSIZED_RESPONSE,
                               redirect_chain=tuple(render.redirect_chain))

        capture = self._capture(url, final_url, render, consent_banner, divergence,
                                True, notes)
        self.captures.append(capture)

        # body is the RENDERED DOM, so build_snapshot normalizes what a visitor
        # actually sees rather than the pre-JavaScript shell.
        return FetchResult(
            requested_url=url, ok=True, final_url=final_url,
            http_status=render.http_status, content_type=render.content_type,
            body=dom_bytes, redirect_chain=tuple(render.redirect_chain),
            response_headers=tuple(render.response_headers),
            warnings=tuple(notes))

    # -- helpers ---------------------------------------------------------- #

    def _blocked(self, url: str, final_url: str, render: BrowserRenderResult,
                 reason: str) -> FetchResult:
        """Record and stop. There is deliberately no retry for any of these."""
        self.captures.append(self._capture(
            url, final_url, render, detect_consent_banner(render.visible_text),
            0.0, False, ["stopped_%s_no_evasion_attempted" % reason], reason))
        return FetchResult(url, False, final_url=final_url,
                           http_status=render.http_status,
                           content_type=render.content_type, reason=reason,
                           redirect_chain=tuple(render.redirect_chain),
                           response_headers=tuple(render.response_headers))

    def _capture(self, url: str, final_url: str, render: BrowserRenderResult,
                 consent_banner: bool, divergence: float, stable: bool,
                 notes: Sequence[str], outcome_reason: str = "") -> BrowserCapture:
        return BrowserCapture(
            requested_url=url, final_url=final_url,
            http_status=render.http_status, content_type=render.content_type,
            elapsed_ms=render.elapsed_ms, outcome_reason=outcome_reason,
            raw_transport_hash=_sha256_bytes(render.transport_body),
            rendered_dom_hash=_sha256_text(render.dom_html),
            transport_bytes=len(render.transport_body or b""),
            dom_bytes=len((render.dom_html or "").encode("utf-8")),
            navigation_urls=tuple(render.navigation_urls),
            redirect_chain=tuple(render.redirect_chain),
            interactions=tuple(render.interactions),
            consent_banner_detected=consent_banner,
            stability_divergence=divergence, stable=stable, notes=tuple(notes))

    @property
    def last_capture(self) -> Optional[BrowserCapture]:
        return self.captures[-1] if self.captures else None


# --------------------------------------------------------------------------- #
# Playwright driver (the only part that needs a real browser).
# --------------------------------------------------------------------------- #

class PlaywrightBrowserDriver:
    """Headless Chromium driver.

    Imported lazily and never constructed by any test, so the offline suite
    neither needs Playwright installed nor launches a browser. No stealth
    options, no proxy, no fingerprint patching -- the browser identifies itself
    with the same honest user agent the static fetcher sends.
    """

    def __init__(self, *, headless: bool = True, user_agent: str = C.USER_AGENT):
        self._headless = headless
        self._user_agent = user_agent

    def render(self, url: str, *, navigation_timeout_ms: int, total_budget_ms: int,
               expand_content: bool) -> BrowserRenderResult:
        import time  # noqa: PLC0415

        from playwright.sync_api import TimeoutError as PWTimeout  # noqa: PLC0415
        from playwright.sync_api import sync_playwright              # noqa: PLC0415

        started = time.monotonic()

        def _elapsed_ms() -> int:
            return int((time.monotonic() - started) * 1000)

        navigations: List[str] = []
        redirects: List[str] = []
        transport_body = b""
        headers: Tuple[Tuple[str, str], ...] = ()
        status = 0
        content_type = ""
        interactions: List[str] = []

        with sync_playwright() as pw:
            browser = pw.chromium.launch(headless=self._headless)
            try:
                context = browser.new_context(user_agent=self._user_agent,
                                              locale="en-US")
                context.set_default_navigation_timeout(navigation_timeout_ms)
                page = context.new_page()

                # Block heavy subresources: faster, quieter, and none of them
                # can contribute visible text anyway.
                page.route("**/*", lambda route: (
                    route.abort() if route.request.resource_type
                    in ("image", "media", "font") else route.continue_()))
                page.on("framenavigated", lambda f: (
                    navigations.append(f.url) if f == page.main_frame else None))

                try:
                    response = page.goto(url, wait_until="domcontentloaded")
                except PWTimeout:
                    return BrowserRenderResult(url, error=C.REASON_FETCH_TIMEOUT,
                                               elapsed_ms=_elapsed_ms())

                if response is not None:
                    status = response.status
                    headers_map = response.all_headers()
                    content_type = headers_map.get("content-type", "")
                    headers = tuple(sorted(
                        (k, v) for k, v in headers_map.items()
                        if k in ("content-type", "content-length", "last-modified",
                                 "etag", "server", "location")))
                    try:
                        transport_body = response.body()
                    except Exception:      # noqa: BLE001 -- body may be unavailable
                        transport_body = b""
                    for req in _redirect_chain(response):
                        redirects.append(req)

                page.wait_for_timeout(C.RENDER_SETTLE_MS)

                if expand_content:
                    interactions = _expand_collapsed(page)

                dom_1 = page.content()
                text_1 = page.evaluate("() => document.body ? document.body.innerText : ''")
                page.wait_for_timeout(C.RENDER_STABILITY_GAP_MS)
                dom_2 = page.content()
                text_2 = page.evaluate("() => document.body ? document.body.innerText : ''")
                final_url = page.url
            finally:
                browser.close()

        return BrowserRenderResult(
            requested_url=url, final_url=final_url, http_status=status,
            content_type=content_type, transport_body=transport_body,
            dom_html=dom_1, dom_html_second=dom_2,
            visible_text=text_1, visible_text_second=text_2,
            navigation_urls=tuple(navigations), redirect_chain=tuple(redirects),
            response_headers=headers, interactions=tuple(interactions),
            elapsed_ms=_elapsed_ms())


def _redirect_chain(response) -> List[str]:
    chain: List[str] = []
    req = getattr(response, "request", None)
    seen = 0
    while req is not None and seen <= C.MAX_REDIRECTS:
        prev = req.redirected_from
        if prev is None:
            break
        chain.append(prev.url)
        req = prev
        seen += 1
    chain.reverse()
    return chain


def _expand_collapsed(page) -> List[str]:
    """Open collapsed disclosure widgets so their text becomes visible.

    Bounded and logged. This is the one place the fetcher interacts with a
    page, and it is limited to expanding content the site already offers to
    any visitor -- it never submits a form, never accepts consent, and never
    dismisses a challenge.
    """
    clicked: List[str] = []
    try:
        handles = page.query_selector_all('[aria-expanded="false"]')
    except Exception:      # noqa: BLE001
        return clicked
    for idx, handle in enumerate(handles[:C.RENDER_MAX_EXPAND_CLICKS]):
        try:
            handle.click(timeout=2000)
            clicked.append('[aria-expanded="false"]#%d' % idx)
        except Exception:  # noqa: BLE001 -- a non-clickable node is not an error
            continue
    return clicked
