"""PTF-WORKERS-005 -- offline tests for the browser-rendered fetcher.

Every test injects a fake driver, so no test here installs, imports, or
launches Playwright, and none can reach the network. What is under test is the
FETCHER's logic -- allowlist enforcement, redirect/navigation validation,
detection-and-stop behaviour, stability, hashing -- not Chromium's.
"""

from __future__ import annotations

import hashlib

import pytest

from scripts.pettripfinder.importer import constants as C
from scripts.pettripfinder.importer import browser_fetch as BF
from scripts.pettripfinder.importer.fetch_status import (
    FETCH_STATUS_BLOCKED_LIKE, FETCH_STATUS_CHALLENGE_DETECTED,
    FETCH_STATUS_CONSENT_GATED, FETCH_STATUS_LOGIN_REQUIRED,
    FETCH_STATUS_RENDER_NONDETERMINISTIC, classify_fetch_status,
)

URL = "https://www.ihg.com/staybridge/hotels/us/en/dublin/cmhtc/hoteldetail/amenities"
ALLOWED = ("ihg.com",)

POLICY_TEXT = (
    "Pets are welcome at Staybridge Suites Columbus-Dublin. This is a dog only hotel. "
    "Up to two friendly pups under 80 lbs are welcome. Pet fee per pet is 75 dollars "
    "plus tax for 1-7 nights. A fee of $150 plus tax applies per stay for 8 or more "
    "nights. The pet fee is non-refundable. " * 6
)


class FakeDriver:
    """Returns a canned BrowserRenderResult. Records what it was asked for."""

    def __init__(self, result: BF.BrowserRenderResult):
        self._result = result
        self.calls = []

    def render(self, url, *, navigation_timeout_ms, total_budget_ms, expand_content):
        self.calls.append({"url": url, "navigation_timeout_ms": navigation_timeout_ms,
                           "total_budget_ms": total_budget_ms,
                           "expand_content": expand_content})
        return self._result


def _render(**over):
    base = dict(
        requested_url=URL, final_url=URL, http_status=200,
        content_type="text/html; charset=utf-8",
        transport_body=b"<html><body>shell</body></html>",
        dom_html="<html><body><p>%s</p></body></html>" % POLICY_TEXT,
        dom_html_second="<html><body><p>%s</p></body></html>" % POLICY_TEXT,
        visible_text=POLICY_TEXT, visible_text_second=POLICY_TEXT,
    )
    base.update(over)
    return BF.BrowserRenderResult(**base)


def _fetcher(render_result, **kw):
    kw.setdefault("resolve_host", False)      # no DNS in tests
    return BF.BrowserPageFetcher(FakeDriver(render_result), allowed_domains=ALLOWED, **kw)


# --------------------------------------------------------------------------- #
# No-evasion guarantee.
# --------------------------------------------------------------------------- #

def executable_source(module) -> str:
    """Module source with comments and docstrings removed.

    Necessary rather than fastidious: this module's docstring deliberately
    NAMES the evasion techniques it does not implement, so a naive substring
    scan would flag the very paragraph promising they are absent. Stripping to
    executable code means the assertion tests behaviour, not prose.
    """
    import ast
    import inspect
    tree = ast.parse(inspect.getsource(module))
    for node in ast.walk(tree):
        body = getattr(node, "body", None)
        if not isinstance(body, list) or not body:
            continue
        first = body[0]
        if (isinstance(first, ast.Expr) and isinstance(first.value, ast.Constant)
                and isinstance(first.value.value, str)):
            body.pop(0)
    return ast.unparse(tree)


def test_module_contains_no_evasion_machinery():
    """The authorization is explicit: detect and stop, never evade."""
    code = executable_source(BF)
    for banned in ("stealth", "undetected", "playwright_stealth", "solve_captcha",
                   "anticaptcha", "2captcha", "rotate_proxy",
                   "webdriver=False", "navigator.webdriver"):
        assert banned not in code, "evasion identifier %r present" % banned
    # No proxy is ever configured on the browser context.
    assert "proxy" not in code


def test_user_agent_is_the_honest_importer_agent():
    driver = BF.PlaywrightBrowserDriver()
    assert driver._user_agent == C.USER_AGENT
    assert "Atlas" in C.USER_AGENT


# --------------------------------------------------------------------------- #
# Allowlist enforcement.
# --------------------------------------------------------------------------- #

def test_empty_allowlist_is_refused_at_construction():
    with pytest.raises(ValueError):
        BF.BrowserPageFetcher(FakeDriver(_render()), allowed_domains=())


@pytest.mark.parametrize("url", [
    "https://www.tripadvisor.com/x",
    "https://evil-ihg.com/spoof",
    "https://ihg.com.attacker.net/x",
])
def test_initial_url_off_allowlist_is_rejected(url):
    out = _fetcher(_render()).fetch(url)
    assert out.ok is False
    assert out.reason == C.REASON_OFF_ALLOWLIST_NAVIGATION


def test_subdomain_of_an_allowed_domain_is_accepted():
    u = "https://digital.ihg.com/is/content/ihg/policy"
    out = _fetcher(_render(requested_url=u, final_url=u)).fetch(u)
    assert out.ok is True


def test_navigation_to_an_off_allowlist_host_is_rejected():
    """A page that bounces us to a third-party consent host is not evidence."""
    out = _fetcher(_render(navigation_urls=(URL, "https://consent.example.com/gate"))).fetch(URL)
    assert out.ok is False
    assert out.reason == C.REASON_OFF_ALLOWLIST_NAVIGATION


def test_off_allowlist_redirect_hop_is_rejected():
    out = _fetcher(_render(redirect_chain=("https://tracker.example.net/r",))).fetch(URL)
    assert out.ok is False
    assert out.reason == C.REASON_OFF_ALLOWLIST_NAVIGATION


def test_final_url_off_allowlist_is_rejected():
    out = _fetcher(_render(final_url="https://www.booking.com/hotel")).fetch(URL)
    assert out.ok is False
    assert out.reason == C.REASON_OFF_ALLOWLIST_NAVIGATION


def test_model_research_urn_is_never_rendered():
    urn = BF.MODEL_RESEARCH_URN_PREFIX + "abc123"
    out = _fetcher(_render()).fetch(urn)
    assert out.ok is False
    assert "model_research_report_is_not_a_page" in out.warnings


# --------------------------------------------------------------------------- #
# Detect-and-stop.
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("text,reason,status", [
    ("Just a moment... checking your browser. Ray ID: 8ab",
     C.REASON_CHALLENGE_DETECTED, FETCH_STATUS_CHALLENGE_DETECTED),
    ("Access denied. Please enable cookies and reload.",
     C.REASON_CHALLENGE_DETECTED, FETCH_STATUS_CHALLENGE_DETECTED),
    ("Please sign in to continue to your account.",
     C.REASON_LOGIN_REQUIRED, FETCH_STATUS_LOGIN_REQUIRED),
    ("We use cookies. Accept all cookies to continue.",
     C.REASON_CONSENT_GATED, FETCH_STATUS_CONSENT_GATED),
])
def test_blocking_conditions_stop_and_classify(text, reason, status):
    f = _fetcher(_render(visible_text=text, visible_text_second=text))
    out = f.fetch(URL)
    assert out.ok is False
    assert out.reason == reason
    assert classify_fetch_status(out) == status
    assert status in FETCH_STATUS_BLOCKED_LIKE
    # the capture records that we stopped rather than worked around it
    assert any("no_evasion_attempted" in n for n in f.last_capture.notes)


def test_a_blocked_page_is_never_retried():
    """One driver call, no second attempt -- 403/challenge must not be retried."""
    driver = FakeDriver(_render(visible_text="Access denied", visible_text_second="Access denied"))
    f = BF.BrowserPageFetcher(driver, allowed_domains=ALLOWED, resolve_host=False)
    f.fetch(URL)
    assert len(driver.calls) == 1


def test_http_403_maps_to_blocked_source():
    out = _fetcher(_render(http_status=403)).fetch(URL)
    assert out.ok is False
    assert out.reason == C.REASON_BLOCKED_SOURCE


def test_http_429_maps_to_rate_limited():
    out = _fetcher(_render(http_status=429)).fetch(URL)
    assert out.reason == C.REASON_RATE_LIMITED_SOURCE


def test_a_consent_banner_over_readable_content_is_not_a_gate():
    """A banner alone must not discard a page whose policy text is right there."""
    text = "We use cookies. " + POLICY_TEXT
    f = _fetcher(_render(visible_text=text, visible_text_second=text))
    out = f.fetch(URL)
    assert out.ok is True
    assert f.last_capture.consent_banner_detected is True
    assert "consent_banner_present_content_readable" in out.warnings


def test_driver_timeout_is_reported_not_retried():
    out = _fetcher(_render(error=C.REASON_FETCH_TIMEOUT)).fetch(URL)
    assert out.ok is False
    assert out.reason == C.REASON_FETCH_TIMEOUT


# --------------------------------------------------------------------------- #
# Stability + hashing.
# --------------------------------------------------------------------------- #

def test_identical_captures_are_stable():
    f = _fetcher(_render())
    out = f.fetch(URL)
    assert out.ok is True
    assert f.last_capture.stable is True
    assert f.last_capture.stability_divergence == 0.0


def test_divergent_captures_are_withheld_as_nondeterministic():
    f = _fetcher(_render(visible_text_second=POLICY_TEXT + " Rooms left: 3. " * 200))
    out = f.fetch(URL)
    assert out.ok is False
    assert out.reason == C.REASON_RENDER_NONDETERMINISTIC
    assert classify_fetch_status(out) == FETCH_STATUS_RENDER_NONDETERMINISTIC
    assert f.last_capture.stable is False


def test_trivial_divergence_is_tolerated():
    """A clock or a view counter must not discard an otherwise good capture."""
    f = _fetcher(_render(visible_text_second=POLICY_TEXT + " 1"))
    assert f.fetch(URL).ok is True


def test_three_hashes_are_distinct_and_correct():
    render = _render()
    f = _fetcher(render)
    out = f.fetch(URL)
    cap = f.last_capture
    assert cap.raw_transport_hash == hashlib.sha256(render.transport_body).hexdigest()
    assert cap.rendered_dom_hash == hashlib.sha256(
        render.dom_html.encode("utf-8")).hexdigest()
    assert cap.raw_transport_hash != cap.rendered_dom_hash
    # the FetchResult body is the RENDERED dom, so downstream normalization
    # sees what a visitor sees rather than the pre-JavaScript shell
    assert out.body == render.dom_html.encode("utf-8")


def test_capture_dict_states_the_dom_hash_is_not_reproducible():
    f = _fetcher(_render())
    f.fetch(URL)
    meaning = f.last_capture.to_dict()["rendered_dom_hash_meaning"]
    assert "point-in-time" in meaning.lower()
    assert "not a reproducibility guarantee" in meaning.lower()


def test_oversized_dom_is_rejected():
    huge = "<html><body>" + ("x" * (C.MAX_RESPONSE_BYTES + 10)) + "</body></html>"
    out = _fetcher(_render(dom_html=huge, dom_html_second=huge)).fetch(URL)
    assert out.ok is False
    assert out.reason == C.REASON_OVERSIZED_RESPONSE


def test_page_budget_is_bounded():
    f = _fetcher(_render(), max_pages=2)
    assert f.fetch(URL).ok is True
    assert f.fetch(URL).ok is True
    third = f.fetch(URL)
    assert third.ok is False
    assert "render_page_budget_exhausted" in third.warnings


# --------------------------------------------------------------------------- #
# PTF-WORKERS-006: a failed attempt is still an audit record.
#
# The live Staybridge proof returned 403 and recorded NOTHING, so the artifact
# could not say what was tried or how long it took. Every post-navigation exit
# must now leave a capture behind.
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("render_over,expected_reason", [
    ({"http_status": 403}, C.REASON_BLOCKED_SOURCE),
    ({"http_status": 429}, C.REASON_RATE_LIMITED_SOURCE),
    ({"http_status": 500}, C.REASON_FETCH_FAILED),
    ({"content_type": "application/pdf"}, C.REASON_PDF_SOURCE),
    ({"final_url": "https://www.booking.com/x"}, C.REASON_OFF_ALLOWLIST_NAVIGATION),
    ({"navigation_urls": (URL, "https://evil.example/x")}, C.REASON_OFF_ALLOWLIST_NAVIGATION),
    ({"error": C.REASON_FETCH_TIMEOUT}, C.REASON_FETCH_TIMEOUT),
])
def test_every_failure_path_records_an_attempt(render_over, expected_reason):
    f = _fetcher(_render(elapsed_ms=4321, **render_over))
    out = f.fetch(URL)
    assert out.ok is False
    assert out.reason == expected_reason
    cap = f.last_capture
    assert cap is not None, "no capture recorded for %s" % expected_reason
    assert cap.requested_url == URL                  # attempted URL
    assert cap.outcome_reason == expected_reason     # why it ended
    assert cap.elapsed_ms == 4321                    # timing
    assert cap.capture_method == BF.CAPTURE_METHOD_BROWSER_RENDERED


def test_a_403_capture_carries_status_type_timing_and_hops():
    f = _fetcher(_render(http_status=403, content_type="text/html",
                         elapsed_ms=1500, redirect_chain=("https://www.ihg.com/a",)))
    f.fetch(URL)
    d = f.last_capture.to_dict()
    assert d["http_status"] == 403
    assert d["content_type"] == "text/html"
    assert d["elapsed_ms"] == 1500
    assert d["redirect_chain"] == ["https://www.ihg.com/a"]
    assert d["outcome_reason"] == C.REASON_BLOCKED_SOURCE
    assert d["final_url"] == URL


def test_a_failed_capture_still_records_the_transport_hash_when_a_body_exists():
    f = _fetcher(_render(http_status=403, transport_body=b"<html>denied</html>"))
    f.fetch(URL)
    assert f.last_capture.raw_transport_hash == hashlib.sha256(
        b"<html>denied</html>").hexdigest()
    # ...but no rendered content was accepted
    assert f.last_capture.stable is False


def test_oversized_response_records_an_attempt():
    huge = "<html>" + "x" * (C.MAX_RESPONSE_BYTES + 10) + "</html>"
    f = _fetcher(_render(dom_html=huge, dom_html_second=huge, elapsed_ms=99))
    f.fetch(URL)
    assert f.last_capture.outcome_reason == C.REASON_OVERSIZED_RESPONSE
    assert f.last_capture.elapsed_ms == 99


def test_recording_an_attempt_does_not_change_retry_behaviour():
    """Audit must not become a second request."""
    driver = FakeDriver(_render(http_status=403))
    f = BF.BrowserPageFetcher(driver, allowed_domains=ALLOWED, resolve_host=False)
    f.fetch(URL)
    assert len(driver.calls) == 1
    assert len(f.captures) == 1


def test_a_successful_capture_has_no_outcome_reason():
    f = _fetcher(_render())
    assert f.fetch(URL).ok is True
    assert f.last_capture.outcome_reason == ""
    assert f.last_capture.stable is True


def test_bounds_are_passed_to_the_driver():
    driver = FakeDriver(_render())
    f = BF.BrowserPageFetcher(driver, allowed_domains=ALLOWED, resolve_host=False)
    f.fetch(URL)
    call = driver.calls[0]
    assert call["navigation_timeout_ms"] == C.RENDER_NAVIGATION_TIMEOUT_MS
    assert call["total_budget_ms"] == C.RENDER_TOTAL_BUDGET_MS
