"""AES-DATA-001 -- fetch security (mission sections 5/28/32). No real
network: URL/IP validation is exercised with IP-literal hosts (no DNS), and
the redirect/size/status flow uses an injected fake session over public
IP-literal hosts so ``resolve_and_validate_host`` passes without DNS."""

from __future__ import annotations

import pytest
import requests
from requests.structures import CaseInsensitiveDict

from scripts.pettripfinder.importer import constants as C
from scripts.pettripfinder.importer.fetch import (
    RequestsPageFetcher,
    check_url_shape,
    classify_response,
    resolve_and_validate_host,
)

_PUBLIC = "http://93.184.216.34"          # public IP literal -> no DNS
_PRIVATE = "http://127.0.0.1"


class TestUrlShape:
    def test_https_and_http_accepted(self):
        assert check_url_shape("https://example.com/x")[0] is True
        assert check_url_shape("http://example.com/x")[0] is True

    @pytest.mark.parametrize("url,reason", [
        ("file:///etc/passwd", C.REASON_INVALID_SCHEME),
        ("ftp://example.com/x", C.REASON_INVALID_SCHEME),
        ("gopher://example.com", C.REASON_INVALID_SCHEME),
        ("data:text/html,x", C.REASON_INVALID_SCHEME),
        ("https://user:pass@example.com/", C.REASON_UNSAFE_URL),
        ("https://example.com:8080/", C.REASON_INVALID_PORT),
    ])
    def test_rejected_shapes(self, url, reason):
        ok, got = check_url_shape(url)
        assert ok is False and got == reason


class TestHostValidation:
    def test_public_ip_literal_ok(self):
        ok, reason, ips = resolve_and_validate_host("93.184.216.34")
        assert ok is True and reason == ""

    @pytest.mark.parametrize("host", [
        "127.0.0.1", "10.0.0.5", "192.168.1.1", "169.254.1.1", "0.0.0.0",
        "::1", "fc00::1", "fe80::1", "localhost", "foo.localhost",
    ])
    def test_unsafe_hosts_rejected(self, host):
        ok, reason, _ = resolve_and_validate_host(host)
        assert ok is False
        assert reason in (C.REASON_UNSAFE_HOST, C.REASON_DNS_RESOLUTION_FAILED)

    def test_loopback_ipv6_rejected(self):
        assert resolve_and_validate_host("::1")[0] is False


class TestClassifyResponse:
    @pytest.mark.parametrize("status,ctype,ok,reason", [
        (200, "text/html; charset=utf-8", True, ""),
        (200, "application/xhtml+xml", True, ""),
        (200, "application/pdf", False, C.REASON_PDF_SOURCE),
        (200, "image/png", False, C.REASON_UNSUPPORTED_CONTENT_TYPE),
        (403, "text/html", False, C.REASON_BLOCKED_SOURCE),
        (429, "text/html", False, C.REASON_RATE_LIMITED_SOURCE),
        (500, "text/html", False, C.REASON_FETCH_FAILED),
        (404, "text/html", False, C.REASON_FETCH_FAILED),
    ])
    def test_mapping(self, status, ctype, ok, reason):
        assert classify_response(status, ctype) == (ok, reason)


# --------------------------------------------------------------------------- #
# Fake session for the full fetch flow (no network).
# --------------------------------------------------------------------------- #

class _FakeResp:
    def __init__(self, status, headers, chunks=(b"<html>ok</html>",), raise_exc=None):
        self.status_code = status
        self.headers = CaseInsensitiveDict(headers)
        self._chunks = chunks
        self._raise = raise_exc

    def iter_content(self, chunk_size=16384):
        if self._raise:
            raise self._raise
        for c in self._chunks:
            yield c

    def close(self):
        pass


class _FakeSession:
    def __init__(self, by_url, exc=None):
        self._by_url = by_url
        self._exc = exc

    def get(self, url, **kw):
        if self._exc:
            raise self._exc
        return self._by_url[url]


class TestFetchFlow:
    def test_success_html(self):
        url = _PUBLIC + "/ok"
        sess = _FakeSession({url: _FakeResp(200, {"Content-Type": "text/html"})})
        r = RequestsPageFetcher(session=sess).fetch(url)
        assert r.ok and r.http_status == 200 and b"ok" in r.body

    def test_oversized_body_rejected(self):
        url = _PUBLIC + "/big"
        big = b"x" * (C.MAX_RESPONSE_BYTES + 16)
        sess = _FakeSession({url: _FakeResp(200, {"Content-Type": "text/html"}, (big,))})
        r = RequestsPageFetcher(session=sess).fetch(url)
        assert r.ok is False and r.reason == C.REASON_OVERSIZED_RESPONSE

    def test_pdf_review(self):
        url = _PUBLIC + "/doc"
        sess = _FakeSession({url: _FakeResp(200, {"Content-Type": "application/pdf"})})
        r = RequestsPageFetcher(session=sess).fetch(url)
        assert r.ok is False and r.reason == C.REASON_PDF_SOURCE

    def test_403_review(self):
        url = _PUBLIC + "/blocked"
        sess = _FakeSession({url: _FakeResp(403, {"Content-Type": "text/html"})})
        r = RequestsPageFetcher(session=sess).fetch(url)
        assert r.reason == C.REASON_BLOCKED_SOURCE

    def test_redirect_followed_then_success(self):
        u1 = _PUBLIC + "/r1"
        u2 = _PUBLIC + "/r2"
        sess = _FakeSession({
            u1: _FakeResp(301, {"Location": u2}),
            u2: _FakeResp(200, {"Content-Type": "text/html"}),
        })
        r = RequestsPageFetcher(session=sess).fetch(u1)
        assert r.ok and r.final_url == u2 and u2 in r.redirect_chain

    def test_redirect_to_private_ip_rejected(self):
        u1 = _PUBLIC + "/r1"
        bad = _PRIVATE + "/internal"
        sess = _FakeSession({u1: _FakeResp(302, {"Location": bad})})
        r = RequestsPageFetcher(session=sess).fetch(u1)
        assert r.ok is False and r.reason == C.REASON_UNSAFE_REDIRECT

    def test_redirect_limit(self):
        # A self-redirect loop hits the cap.
        u = _PUBLIC + "/loop"
        sess = _FakeSession({u: _FakeResp(302, {"Location": u})})
        r = RequestsPageFetcher(session=sess).fetch(u)
        assert r.ok is False and r.reason == C.REASON_REDIRECT_LIMIT

    def test_timeout_mapped(self):
        url = _PUBLIC + "/slow"
        sess = _FakeSession({}, exc=requests.Timeout())
        r = RequestsPageFetcher(session=sess).fetch(url)
        assert r.ok is False and r.reason == C.REASON_FETCH_TIMEOUT

    def test_unsafe_scheme_never_connects(self):
        r = RequestsPageFetcher(session=_FakeSession({})).fetch("file:///etc/passwd")
        assert r.ok is False and r.reason == C.REASON_INVALID_SCHEME
