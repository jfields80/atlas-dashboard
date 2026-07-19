"""AES-DATA-001 importer -- SSRF-safe deterministic page fetcher (mission
sections 5/32).

``PageFetcher`` is the provider seam. ``RequestsPageFetcher`` is the live
implementation with a strict URL-fetch security policy; ``StaticPageFetcher``
is the deterministic, network-free implementation the whole test suite and
the deterministic benchmark run against.

Security posture (V1): scheme/port/credential/hostname validation, DNS
resolution with rejection when *any* resolved address is
private/loopback/link-local/reserved/multicast/unspecified, manual redirect
following with per-hop re-validation and a hard cap, streaming body read
with a decompressed-size cap (defeats content-length lies and decompression
bombs), and a content-type whitelist. Residual: a sub-second TOCTOU
DNS-rebinding window between validation and connect (all A/AAAA records are
validated, which closes the common case); IP-pinned connections are the
named future hardening. No JavaScript is ever executed; no downloaded bytes
are ever executed or written to arbitrary paths.
"""

from __future__ import annotations

import ipaddress
import socket
import time
from typing import Dict, List, Optional, Protocol, Tuple
from urllib.parse import urlsplit

from scripts.pettripfinder.importer import constants as C
from scripts.pettripfinder.importer.models import FetchResult

# Response headers worth preserving on the snapshot (bounded subset).
_KEEP_HEADERS = ("content-type", "content-length", "last-modified", "etag",
                 "server", "location")
_REDIRECT_STATUSES = frozenset({301, 302, 303, 307, 308})


class PageFetcher(Protocol):
    def fetch(self, url: str) -> FetchResult: ...


# --------------------------------------------------------------------------- #
# URL / host safety (pure; no network except the explicit DNS step).
# --------------------------------------------------------------------------- #

def check_url_shape(url: str) -> Tuple[bool, str]:
    """Scheme, credentials, and port checks that need no DNS. Returns
    ``(ok, reason)``; reason is "" on success."""
    parts = urlsplit(url)
    scheme = (parts.scheme or "").lower()
    if scheme not in C.ALLOWED_SCHEMES:
        return (False, C.REASON_INVALID_SCHEME)
    if "@" in (parts.netloc or ""):
        return (False, C.REASON_UNSAFE_URL)          # embedded credentials
    host = parts.hostname
    if not host:
        return (False, C.REASON_UNSAFE_URL)
    port = parts.port
    if port is not None and port not in C.ALLOWED_PORTS:
        return (False, C.REASON_INVALID_PORT)
    return (True, "")


def _ip_is_unsafe(ip: str) -> bool:
    try:
        addr = ipaddress.ip_address(ip)
    except ValueError:
        return True
    return (
        addr.is_private or addr.is_loopback or addr.is_link_local
        or addr.is_multicast or addr.is_reserved or addr.is_unspecified
        or (getattr(addr, "is_site_local", False))
    )


def resolve_and_validate_host(host: str) -> Tuple[bool, str, List[str]]:
    """Resolve ``host`` and validate *every* resolved address. Returns
    ``(ok, reason, ips)``. An IP-literal host is validated directly. If any
    resolved address is unsafe, the whole host is rejected (``unsafe_host``);
    a resolution failure is ``dns_resolution_failed``."""
    # IP-literal host: validate without DNS.
    try:
        ipaddress.ip_address(host)
        if _ip_is_unsafe(host):
            return (False, C.REASON_UNSAFE_HOST, [host])
        return (True, "", [host])
    except ValueError:
        pass
    # Reject obvious localhost aliases before resolving.
    if host.lower() in ("localhost", "localhost.localdomain") or host.lower().endswith(".localhost"):
        return (False, C.REASON_UNSAFE_HOST, [])
    try:
        infos = socket.getaddrinfo(host, None)
    except socket.gaierror:
        return (False, C.REASON_DNS_RESOLUTION_FAILED, [])
    except (socket.error, UnicodeError):
        return (False, C.REASON_UNSAFE_HOST, [])
    ips = sorted({info[4][0] for info in infos})
    if not ips:
        return (False, C.REASON_DNS_RESOLUTION_FAILED, [])
    for ip in ips:
        if _ip_is_unsafe(ip):
            return (False, C.REASON_UNSAFE_HOST, ips)
    return (True, "", ips)


def assert_fetchable(url: str) -> Tuple[bool, str]:
    """Full pre-connect gate (shape + DNS + IP validation)."""
    ok, reason = check_url_shape(url)
    if not ok:
        return (False, reason)
    host = urlsplit(url).hostname or ""
    ok, reason, _ = resolve_and_validate_host(host)
    return (ok, reason)


# --------------------------------------------------------------------------- #
# Content-type / status mapping.
# --------------------------------------------------------------------------- #

def _media_type(content_type_header: str) -> str:
    return (content_type_header or "").split(";", 1)[0].strip().lower()


def classify_response(status: int, content_type_header: str) -> Tuple[bool, str]:
    """Map a *final* response to ``(ok, reason)``. ``ok`` True only for a
    2xx HTML/XHTML body; every other case names a slug (mission section 5)."""
    media = _media_type(content_type_header)
    if status == 403:
        return (False, C.REASON_BLOCKED_SOURCE)
    if status == 429:
        return (False, C.REASON_RATE_LIMITED_SOURCE)
    if status < 200 or status >= 300:
        return (False, C.REASON_FETCH_FAILED)
    if media == C.PDF_CONTENT_TYPE:
        return (False, C.REASON_PDF_SOURCE)
    if media not in C.HTML_CONTENT_TYPES:
        return (False, C.REASON_UNSUPPORTED_CONTENT_TYPE)
    return (True, "")


def _header_subset(headers) -> Tuple[Tuple[str, str], ...]:
    out = []
    for key in _KEEP_HEADERS:
        val = headers.get(key)
        if val is not None:
            out.append((key, str(val)))
    return tuple(out)


# AES-DATA-004E (Task 4): ordinary, non-deceptive content-negotiation
# headers only -- no browser fingerprint, no stealth. ``Accept-Encoding``
# names exactly what this fetcher can actually decode (gzip/deflate, both
# handled transparently by ``requests``/``urllib3``); nothing is claimed
# that isn't true.
def _request_headers() -> Dict[str, str]:
    return {
        "User-Agent": C.USER_AGENT,
        "Accept": C.ACCEPT_HEADER,
        "Accept-Language": C.ACCEPT_LANGUAGE_HEADER,
        "Accept-Encoding": C.ACCEPT_ENCODING_HEADER,
    }


_TRANSIENT_SERVER_STATUSES = frozenset({500, 502, 503, 504})


# --------------------------------------------------------------------------- #
# Live fetcher.
# --------------------------------------------------------------------------- #

class RequestsPageFetcher:
    """Live SSRF-safe fetcher over ``requests`` with manual redirects.

    AES-DATA-004E (Task 4) adds three general, disclosed, compliant
    improvements, all bounded and all off by default in tests (which inject
    a fake session and a no-op ``sleep_fn``):

    1. Ordinary content-negotiation headers (see ``_request_headers``).
    2. ONE bounded retry, after a short fixed delay, for a TRANSIENT server
       error (500/502/503/504) only -- never for a block/timeout/redirect
       outcome, and never more than once per hop (mirrors the existing
       ``LLM_MALFORMED_RETRIES = 1`` "one retry only" convention elsewhere
       in this package).
    3. A minimum per-domain gap between requests issued by THIS fetcher
       instance (``min_domain_interval_seconds``) -- request pacing, never a
       rotating identity or anti-detection mechanism. Meaningful within one
       multi-source job (several URLs on the same domain) and for any
       caller that chooses to share one instance across a batch; a
       fresh-fetcher-per-job caller (the default live batch path today)
       gets no cross-job pacing from this alone -- disclosed, not a
       correctness issue (the pacing is purely a politeness floor, never
       required for safety).
    """

    def __init__(self, session=None, *, min_domain_interval_seconds: float = None,
                 sleep_fn=time.sleep, time_fn=time.monotonic):
        self._session = session   # injectable for tests; lazily created
        self._min_domain_interval = (
            C.MIN_DOMAIN_INTERVAL_SECONDS if min_domain_interval_seconds is None
            else min_domain_interval_seconds)
        self._sleep_fn = sleep_fn
        self._time_fn = time_fn
        self._last_request_at: Dict[str, float] = {}

    def _get_session(self):
        if self._session is None:
            import requests  # lazy: keeps the module importable without deps
            self._session = requests.Session()
        return self._session

    def _pace(self, host: str) -> None:
        if self._min_domain_interval <= 0:
            return
        now = self._time_fn()
        last = self._last_request_at.get(host)
        if last is not None:
            elapsed = now - last
            remaining = self._min_domain_interval - elapsed
            if remaining > 0:
                self._sleep_fn(remaining)
                now = self._time_fn()
        self._last_request_at[host] = now

    def fetch(self, url: str) -> FetchResult:
        import requests  # lazy import; deterministic tests use StaticPageFetcher
        session = self._get_session()
        redirect_chain: List[str] = []
        current = url

        for _hop in range(C.MAX_REDIRECTS + 1):
            ok, reason = check_url_shape(current)
            if not ok:
                return FetchResult(url, False, reason=reason,
                                   redirect_chain=tuple(redirect_chain))
            host = urlsplit(current).hostname or ""
            ok, reason, _ips = resolve_and_validate_host(host)
            if not ok:
                slug = reason if not redirect_chain else (
                    C.REASON_UNSAFE_REDIRECT if reason == C.REASON_UNSAFE_HOST else reason
                )
                return FetchResult(url, False, reason=slug,
                                   redirect_chain=tuple(redirect_chain))

            attempts_remaining = 1 + C.TRANSIENT_SERVER_ERROR_RETRY_COUNT
            resp = None
            first_attempt = True
            while attempts_remaining > 0:
                attempts_remaining -= 1
                if first_attempt:
                    # Domain pacing applies once per hop, before the FIRST
                    # attempt only -- a transient-error retry already carries
                    # its own explicit backoff (below), so stacking generic
                    # pacing on top of it is redundant.
                    self._pace(host)
                    first_attempt = False
                try:
                    resp = session.get(
                        current,
                        headers=_request_headers(),
                        timeout=(C.CONNECT_TIMEOUT_SECONDS, C.READ_TIMEOUT_SECONDS),
                        allow_redirects=False,
                        stream=True,
                    )
                except requests.Timeout:
                    return FetchResult(url, False, reason=C.REASON_FETCH_TIMEOUT,
                                       redirect_chain=tuple(redirect_chain))
                except requests.RequestException:
                    return FetchResult(url, False, reason=C.REASON_FETCH_FAILED,
                                       redirect_chain=tuple(redirect_chain))
                if resp.status_code in _TRANSIENT_SERVER_STATUSES and attempts_remaining > 0:
                    resp.close()
                    self._sleep_fn(C.TRANSIENT_SERVER_ERROR_RETRY_DELAY_SECONDS)
                    continue
                break

            status = resp.status_code
            if status in _REDIRECT_STATUSES:
                location = resp.headers.get("Location")
                resp.close()
                if not location:
                    return FetchResult(url, False, reason=C.REASON_FETCH_FAILED,
                                       redirect_chain=tuple(redirect_chain))
                # Resolve relative redirects against the current URL.
                from urllib.parse import urljoin
                nxt = urljoin(current, location)
                redirect_chain.append(nxt)
                current = nxt
                continue

            # Terminal response.
            content_type = resp.headers.get("Content-Type", "")
            header_subset = _header_subset(resp.headers)
            ok, reason = classify_response(status, content_type)
            if not ok:
                resp.close()
                return FetchResult(
                    url, False, final_url=current, http_status=status,
                    content_type=content_type, reason=reason,
                    redirect_chain=tuple(redirect_chain),
                    response_headers=header_subset,
                )
            # Stream body with a hard decompressed-size cap.
            body = bytearray()
            oversized = False
            try:
                for chunk in resp.iter_content(chunk_size=16384):
                    if not chunk:
                        continue
                    body.extend(chunk)
                    if len(body) > C.MAX_RESPONSE_BYTES:
                        oversized = True
                        break
            except requests.RequestException:
                resp.close()
                return FetchResult(url, False, final_url=current,
                                   http_status=status, reason=C.REASON_FETCH_FAILED,
                                   redirect_chain=tuple(redirect_chain))
            finally:
                resp.close()
            if oversized:
                return FetchResult(
                    url, False, final_url=current, http_status=status,
                    content_type=content_type, reason=C.REASON_OVERSIZED_RESPONSE,
                    redirect_chain=tuple(redirect_chain),
                    response_headers=header_subset,
                )
            return FetchResult(
                url, True, final_url=current, http_status=status,
                content_type=content_type, body=bytes(body),
                redirect_chain=tuple(redirect_chain),
                response_headers=header_subset,
            )

        return FetchResult(url, False, reason=C.REASON_REDIRECT_LIMIT,
                           redirect_chain=tuple(redirect_chain))


# --------------------------------------------------------------------------- #
# Deterministic test fetcher.
# --------------------------------------------------------------------------- #

class StaticPageFetcher:
    """Canned fetcher for tests/benchmark. Map exact URL -> ``FetchResult``
    (or bytes for the common success case). No network, ever."""

    def __init__(self, results: Optional[dict] = None):
        self._results = dict(results or {})

    def add_html(self, url: str, html: str, content_type: str = "text/html",
                 status: int = 200) -> None:
        self._results[url] = FetchResult(
            requested_url=url, ok=True, final_url=url, http_status=status,
            content_type=content_type, body=html.encode("utf-8"),
        )

    def add_result(self, url: str, result: FetchResult) -> None:
        self._results[url] = result

    def fetch(self, url: str) -> FetchResult:
        if url in self._results:
            return self._results[url]
        return FetchResult(url, False, reason=C.REASON_FETCH_FAILED)
