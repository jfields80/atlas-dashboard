"""AES-DATA-004E (Task 1/7) -- blocked-source taxonomy. Pure classification
over synthetic ``FetchResult``/``SourceSnapshot`` instances; no network."""

from __future__ import annotations

from scripts.pettripfinder.importer import constants as C
from scripts.pettripfinder.importer.fetch_status import (
    FETCH_STATUS_CAPTCHA_REQUIRED,
    FETCH_STATUS_FETCHABLE,
    FETCH_STATUS_HTTP_403_BLOCKED,
    FETCH_STATUS_JAVASCRIPT_REQUIRED,
    FETCH_STATUS_REDIRECT_LOOP,
    FETCH_STATUS_TIMEOUT,
    FETCH_STATUS_TRANSIENT_SERVER_ERROR,
    FETCH_STATUS_UNKNOWN_FETCH_FAILURE,
    FETCH_STATUS_UNSUPPORTED_CONTENT,
    classify_fetch_status,
)
from scripts.pettripfinder.importer.models import FetchResult, SourceSnapshot


def _snapshot(text, warnings=()):
    return SourceSnapshot(
        requested_url="https://x.test/", final_url="https://x.test/",
        observed_at="2026-07-18", http_status=200, content_type="text/html",
        redirect_chain=(), page_title="", canonical_url="",
        response_header_subset=(), raw_content_hash="h", normalized_text_hash="t",
        normalized_text=text, extraction_version="1.0.0", fetch_warnings=warnings,
        source_relationship="")


def test_ordinary_403_is_http_403_blocked():
    fr = FetchResult("https://x.test/", False, http_status=403, reason=C.REASON_BLOCKED_SOURCE)
    assert classify_fetch_status(fr) == FETCH_STATUS_HTTP_403_BLOCKED


def test_timeout():
    fr = FetchResult("https://x.test/", False, reason=C.REASON_FETCH_TIMEOUT)
    assert classify_fetch_status(fr) == FETCH_STATUS_TIMEOUT


def test_redirect_loop():
    fr = FetchResult("https://x.test/", False, reason=C.REASON_REDIRECT_LIMIT)
    assert classify_fetch_status(fr) == FETCH_STATUS_REDIRECT_LOOP


def test_fetchable_success():
    fr = FetchResult("https://x.test/", True, http_status=200, final_url="https://x.test/")
    snap = _snapshot("Plenty of real page content describing pet policy details here.")
    assert classify_fetch_status(fr, snap) == FETCH_STATUS_FETCHABLE


def test_gzip_compressed_success_still_fetchable():
    # Decompression already happened transparently before this layer ever
    # sees the body -- a compressed page classifies identically to a plain
    # one; there is no separate "compressed" status.
    fr = FetchResult("https://x.test/", True, http_status=200, final_url="https://x.test/",
                     content_type="text/html")
    snap = _snapshot("Real decompressed page content, long enough to look genuine here.")
    assert classify_fetch_status(fr, snap) == FETCH_STATUS_FETCHABLE


def test_js_shell_success_is_javascript_required():
    fr = FetchResult("https://x.test/", True, http_status=200, final_url="https://x.test/")
    snap = _snapshot("", warnings=(C.REASON_JAVASCRIPT_RENDERED,))
    assert classify_fetch_status(fr, snap) == FETCH_STATUS_JAVASCRIPT_REQUIRED


def test_captcha_page_success_is_captcha_required():
    fr = FetchResult("https://x.test/", True, http_status=200, final_url="https://x.test/")
    snap = _snapshot("Please verify you are a human before continuing. Complete the captcha.")
    assert classify_fetch_status(fr, snap) == FETCH_STATUS_CAPTCHA_REQUIRED


def test_captcha_marker_on_a_long_normal_page_is_not_flagged():
    # A long, substantive page mentioning "captcha" in passing (e.g. in a
    # privacy policy) is not a challenge page -- the length ceiling protects
    # against that false positive.
    fr = FetchResult("https://x.test/", True, http_status=200, final_url="https://x.test/")
    long_text = "Our site may use a captcha in some forms. " + ("Real content. " * 200)
    snap = _snapshot(long_text)
    assert classify_fetch_status(fr, snap) == FETCH_STATUS_FETCHABLE


def test_unsupported_content_type():
    fr = FetchResult("https://x.test/", False, http_status=200,
                     reason=C.REASON_UNSUPPORTED_CONTENT_TYPE)
    assert classify_fetch_status(fr) == FETCH_STATUS_UNSUPPORTED_CONTENT


def test_pdf_source_is_unsupported_content():
    fr = FetchResult("https://x.test/", False, http_status=200, reason=C.REASON_PDF_SOURCE)
    assert classify_fetch_status(fr) == FETCH_STATUS_UNSUPPORTED_CONTENT


def test_transient_server_error():
    fr = FetchResult("https://x.test/", False, http_status=503, reason=C.REASON_FETCH_FAILED)
    assert classify_fetch_status(fr) == FETCH_STATUS_TRANSIENT_SERVER_ERROR


def test_unknown_binary_failure_falls_back_conservatively():
    fr = FetchResult("https://x.test/", False, http_status=404, reason=C.REASON_FETCH_FAILED)
    assert classify_fetch_status(fr) == FETCH_STATUS_UNKNOWN_FETCH_FAILURE


def test_taxonomy_never_changes_fetch_result_reason():
    # Purely a reporting layer -- FetchResult itself is untouched.
    fr = FetchResult("https://x.test/", False, http_status=403, reason=C.REASON_BLOCKED_SOURCE)
    classify_fetch_status(fr)
    assert fr.reason == C.REASON_BLOCKED_SOURCE
