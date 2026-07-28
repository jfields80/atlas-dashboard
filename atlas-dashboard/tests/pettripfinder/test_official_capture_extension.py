"""PTF-WORKERS-006 -- contract tests for the operator capture extension.

The extension is the ONE component of the attestation path that runs outside
this repository, on an operator's machine, against a live site. It cannot be
integration-tested here, so what is tested instead is the contract in both
directions:

  * a payload of the exact shape the extension emits is ACCEPTED by the
    committed ingestion validator; and
  * the extension source contains none of the things it promises not to do.

Both matter. The first stops the extension drifting away from the schema; the
second stops it quietly acquiring a network call, a tracker, or an
auto-approval.
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from services.research_workers import operator_capture as OC

_EXT = Path(__file__).resolve().parents[2] / "tools" / "pettripfinder_official_capture"
_MANIFEST = _EXT / "manifest.json"
_WORKER = _EXT / "background.js"


# --------------------------------------------------------------------------- #
# The extension loads at all.
# --------------------------------------------------------------------------- #

def test_every_declared_file_exists():
    """The defect this suite was written for: manifest declared a service
    worker that did not exist, so Chrome could not load the extension."""
    assert _MANIFEST.is_file()
    manifest = json.loads(_MANIFEST.read_text(encoding="utf-8"))
    worker = manifest["background"]["service_worker"]
    assert (_EXT / worker).is_file(), "declared service worker %r is missing" % worker


def test_manifest_requests_only_the_minimum_permissions():
    manifest = json.loads(_MANIFEST.read_text(encoding="utf-8"))
    assert manifest["manifest_version"] == 3
    # activeTab is granted only by the click, so no host permission is needed.
    assert sorted(manifest["permissions"]) == ["activeTab", "downloads", "scripting"]
    for over_reach in ("host_permissions", "content_scripts", "web_accessible_resources"):
        assert over_reach not in manifest, "%s widens reach beyond one clicked tab" % over_reach


def test_manifest_requests_no_sensitive_permission():
    manifest = json.loads(_MANIFEST.read_text(encoding="utf-8"))
    perms = set(manifest.get("permissions", []))
    for sensitive in ("cookies", "storage", "history", "webRequest", "tabs",
                      "browsingData", "privacy", "proxy", "declarativeNetRequest"):
        assert sensitive not in perms


def test_action_has_no_popup_so_capture_requires_a_click():
    manifest = json.loads(_MANIFEST.read_text(encoding="utf-8"))
    assert "default_popup" not in manifest.get("action", {})
    assert "onClicked" in _WORKER.read_text(encoding="utf-8")


# --------------------------------------------------------------------------- #
# The promises in the header are true of the code.
# --------------------------------------------------------------------------- #

def _executable_js() -> str:
    """Source with comments and string literals stripped.

    Necessary, not fastidious: the file's header names the techniques it does
    NOT implement, and the forbidden-key list is itself a list of sensitive
    words. A naive substring scan would flag the very text that documents the
    restraint.
    """
    src = _WORKER.read_text(encoding="utf-8")
    src = re.sub(r"/\*.*?\*/", " ", src, flags=re.S)      # block comments
    src = re.sub(r"//[^\n]*", " ", src)                     # line comments
    src = re.sub(r'"(?:[^"\\]|\\.)*"', '""', src)           # double-quoted strings
    src = re.sub(r"'(?:[^'\\]|\\.)*'", "''", src)           # single-quoted strings
    return src


def test_extension_makes_no_network_request_of_its_own():
    code = _executable_js()
    for banned in ("fetch(", "XMLHttpRequest", "WebSocket", "sendBeacon",
                   "EventSource", "importScripts"):
        assert banned not in code, "network primitive %r present" % banned


def test_extension_has_no_analytics_or_telemetry():
    code = _executable_js().lower()
    for banned in ("analytics", "telemetry", "gtag", "mixpanel", "segment.",
                   "sentry", "datadog", "amplitude"):
        assert banned not in code


def test_extension_reads_no_credentials_or_storage():
    code = _executable_js()
    for banned in ("document.cookie", "chrome.cookies", "localStorage",
                   "sessionStorage", "chrome.history", "indexedDB",
                   "chrome.identity", "chrome.storage"):
        assert banned not in code


def test_extension_contains_no_stealth_or_evasion():
    code = _executable_js().lower()
    for banned in ("stealth", "undetected", "webdriver", "proxy", "useragent",
                   "user-agent", "spoof", "captcha", "puppeteer", "playwright"):
        assert banned not in code


def test_extension_never_approves_or_publishes():
    code = _executable_js().lower()
    for banned in ("approve", "publish", "promote", "approved_tiered_fee"):
        assert banned not in code
    # and it says so where an operator will read it
    assert "NEVER approves" in _WORKER.read_text(encoding="utf-8")


def test_extension_refuses_non_http_pages():
    assert re.search(r"https\?", _WORKER.read_text(encoding="utf-8"))


# --------------------------------------------------------------------------- #
# The emitted payload satisfies the committed ingestion contract.
# --------------------------------------------------------------------------- #

def emitted_capture(**over) -> dict:
    """A payload with exactly the fields background.js writes."""
    payload = {
        "schema": "ptf-official-capture/1.0",
        "extension_version": "1.0.0",
        "captured_at": "2026-07-28T14:05:00.000Z",
        "requested_url": "https://www.hilton.com/en/hotels/cmhchhf-hilton-columbus-at-easton/",
        "final_url": "https://www.hilton.com/en/hotels/cmhchhf-hilton-columbus-at-easton/",
        "title": "Hilton Columbus at Easton",
        "canonical_url": "https://www.hilton.com/en/hotels/cmhchhf-hilton-columbus-at-easton/",
        "html": "<html><head><title>Hilton Columbus at Easton</title></head>"
                "<body><h1>Hilton Columbus at Easton</h1>"
                "<p>3900 Chagrin Dr, Columbus, OH 43219</p>"
                "<p>Pets are welcome. A $100 non-refundable pet fee applies.</p>"
                "</body></html>",
        "text": "Hilton Columbus at Easton 3900 Chagrin Dr, Columbus, OH 43219 "
                "Pets are welcome. A $100 non-refundable pet fee applies.",
        "jsonld": [{"@type": "Hotel", "name": "Hilton Columbus at Easton"}],
        "html_sha256": "0" * 64,
        "text_sha256": "1" * 64,
        "capture_note": "Captured by a human operator from a public official page.",
    }
    payload.update(over)
    return payload


def test_emitted_payload_is_accepted_by_the_committed_validator():
    ok, reason = OC.validate_capture(emitted_capture())
    assert ok is True, reason


def test_emitted_payload_carries_every_required_field():
    payload = emitted_capture()
    for field in OC._REQUIRED_CAPTURE_FIELDS:
        assert field in payload, "extension omits required field %r" % field


@pytest.mark.parametrize("missing", OC._REQUIRED_CAPTURE_FIELDS)
def test_validator_refuses_a_payload_missing_any_required_field(missing):
    payload = emitted_capture()
    payload.pop(missing)
    ok, reason = OC.validate_capture(payload)
    assert ok is False and missing in reason


def test_validator_refuses_a_wrong_schema_version():
    ok, reason = OC.validate_capture(emitted_capture(schema="ptf-official-capture/2.0"))
    assert ok is False and "unsupported_schema" in reason


def test_validator_refuses_an_empty_html_capture():
    ok, reason = OC.validate_capture(emitted_capture(html="   "))
    assert ok is False and reason == "empty_html"


@pytest.mark.parametrize("bad_url,slug", [
    ("ftp://example.com/x", "unsafe_scheme"),
    ("https://user:pw@example.com/x", "embedded_credentials"),
])
def test_validator_refuses_an_unsafe_final_url(bad_url, slug):
    ok, reason = OC.validate_capture(emitted_capture(final_url=bad_url))
    assert ok is False and slug in reason


def test_a_forbidden_key_is_refused_even_if_an_extension_ever_added_one():
    ok, reason = OC.validate_capture(emitted_capture(cookies={"session": "abc"}))
    assert ok is False and "forbidden_keys" in reason


def test_extension_and_validator_agree_on_the_forbidden_key_list():
    """The JS list is a promise; the Python list is the enforcement. They must
    not drift apart, or the extension could emit something ingestion rejects
    (or worse, stop refusing something it should)."""
    src = _WORKER.read_text(encoding="utf-8")
    block = src.split("FORBIDDEN_KEYS = [", 1)[1].split("];", 1)[0]
    js_keys = set(re.findall(r'"([a-z_]+)"', block))
    assert js_keys == set(OC.FORBIDDEN_CAPTURE_KEYS)


# --------------------------------------------------------------------------- #
# End to end against ingestion, with no network.
# --------------------------------------------------------------------------- #

def test_emitted_capture_ingests_into_an_attestable_outcome():
    job = OC.CaptureJob(
        assignment_id="attest-hilton-columbus-at-easton",
        listing_key="hilton columbus at easton",
        listing_name="Hilton Columbus at Easton",
        expected_address="3900 Chagrin Dr", expected_city="Columbus",
        expected_state="OH", expected_postal_code="43219", expected_phone="614-414-5000",
        official_url="https://www.hilton.com/en/hotels/cmhchhf-hilton-columbus-at-easton/",
        failure_reason="blocked_source", retrieval_status="ACCESS_BLOCKED")
    payload = emitted_capture(
        html=emitted_capture()["html"].replace("</body>", "<p>%s</p></body>" % ("filler " * 90)))
    out = OC.ingest_capture(payload, job, observed_at="2026-07-28")
    assert out.status == OC.CAPTURE_ACCEPTED, out.failure_reason
    assert out.source_document is not None
    out.source_document.validate()
    # provenance is manual attestation, never a directly-fetched official page
    from services.research_workers import vocabulary as V
    assert out.source_document.source_type == V.SOURCE_MANUAL_OFFICIAL_ATTESTATION
    assert out.source_document.source_type in V.NON_AUTOMATIC_SOURCE_TYPES


def test_a_captured_challenge_page_is_refused_not_attested():
    """An operator who accidentally captures a bot-check page must not be able
    to turn it into evidence."""
    job = OC.CaptureJob(
        assignment_id="a", listing_key="hilton columbus at easton",
        listing_name="Hilton Columbus at Easton", expected_address="3900 Chagrin Dr",
        expected_city="Columbus", expected_state="OH", expected_postal_code="43219",
        expected_phone="614-414-5000",
        official_url="https://www.hilton.com/en/hotels/cmhchhf-hilton-columbus-at-easton/",
        failure_reason="blocked_source", retrieval_status="ACCESS_BLOCKED")
    payload = emitted_capture(
        html="<html><body><h1>Access Denied</h1><p>%s</p></body></html>" % ("x " * 300))
    out = OC.ingest_capture(payload, job, observed_at="2026-07-28")
    assert out.status == OC.CAPTURE_REJECTED
    assert out.failure_reason in ("access_denied_page", "captcha_or_challenge_page")
