"""PTF-ST-LOUIS-PAID-ACQUISITION-002 -- the paid-lane preflight.

The work order this module was written for stopped on its first probe, which
is the outcome the module exists to produce: a lane reported healthy, and was
not. These tests hold the two claims that made the stop trustworthy --

* a lane's verdict comes from what the vendor said, not from whether a
  variable is set; and
* the three lanes are probed independently because they do not share a
  secret.

Nothing here touches the network. The probes are exercised through injected
failures and through the recorded artifact of the live run.
"""

from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.acquisition import lane_preflight as LP    # noqa: E402
from scripts.pettripfinder.acquisition import providers as PROVIDERS  # noqa: E402
from scripts.pettripfinder.brightdata import client                   # noqa: E402

RECORD = (_REPO_ROOT / "launch_packages" / "pettripfinder"
          / "st_louis_mo_lane_preflight_002.json")


# --------------------------------------------------------------------------- #
# The lanes, and what each one presents.
# --------------------------------------------------------------------------- #

def test_the_paid_lanes_are_exactly_the_three_approved_ones():
    assert LP.PAID_LANES == (PROVIDERS.FIRECRAWL,
                             PROVIDERS.BRIGHTDATA_BROWSER,
                             PROVIDERS.BRIGHTDATA_WEB_UNLOCKER)
    assert set(LP._PROBES) == set(LP.PAID_LANES)


def test_the_two_brightdata_lanes_do_not_present_the_same_secret():
    """The finding that makes a per-lane probe necessary.

    Both lanes bill to one Bright Data account, which invites the assumption
    that a working Web Unlocker proves a working Browser API. It does not:
    the Browser API presents the zone password in ``BRIGHTDATA_BROWSER_AUTH``
    and the Web Unlocker presents the CLI's own stored token. In the live run
    the second passed while the first was refused with ``407``.
    """
    browser = LP.LANE_SECRET[PROVIDERS.BRIGHTDATA_BROWSER]
    unlocker = LP.LANE_SECRET[PROVIDERS.BRIGHTDATA_WEB_UNLOCKER]
    assert browser == client.AUTH_ENV
    assert browser != unlocker
    assert client.AUTH_ENV in unlocker and "independent" in unlocker


# --------------------------------------------------------------------------- #
# A verdict is what the vendor said.
# --------------------------------------------------------------------------- #

@pytest.mark.parametrize("detail, expected", [
    ("407 Auth Failed (wrong_password)", True),
    ("Wrong customer password.", True),
    ("HTTP 401 Unauthorized", True),
    ("invalid api key", True),
    ("HTTP 402 payment required", True),
    ("connect ETIMEDOUT after 30000ms", False),
    ("getaddrinfo ENOTFOUND brd.superproxy.io", False),
    ("the zone did not answer within 90s", False),
    ("", False),
])
def test_an_authentication_rejection_is_told_apart_from_an_outage(detail, expected):
    """Different owners: a refused credential is fixed by whoever holds it,
    and an unreachable lane may fix itself."""
    assert LP._looks_like_auth_rejection(detail) is expected


def test_an_absent_credential_is_not_reported_as_a_rejection(monkeypatch):
    monkeypatch.delenv(client.AUTH_ENV, raising=False)
    probe = LP.probe_brightdata_browser()
    assert probe.verdict == LP.FAIL_ABSENT
    assert not probe.ok
    assert client.AUTH_ENV in probe.detail


def test_a_health_check_pass_is_not_a_preflight_pass(monkeypatch):
    """The gap this module closes, stated as a test.

    ``providers.available()`` asks whether a credential is PRESENT. With a
    present-but-wrong credential it answers yes and the lane answers 407.
    """
    monkeypatch.setenv(client.AUTH_ENV,
                       "brd-customer-hl_test-zone-z1:wrongpassword"
                       "@brd.superproxy.io:9222")
    assert PROVIDERS.get(PROVIDERS.BRIGHTDATA_BROWSER).health_check().available

    monkeypatch.setattr(LP.BC, "probe_exit_country", _refusing_probe)
    probe = LP.probe_brightdata_browser()
    assert probe.verdict == LP.FAIL_AUTH
    assert not probe.ok


async def _refusing_probe(**_kwargs):
    return LP.BC.GeoProbe(
        False, expected="us",
        detail="only 0 of 3 sessions reported an exit country "
               "(Error: WebSocket error: 407 Auth Failed (wrong_password))")


# --------------------------------------------------------------------------- #
# The gate fails closed.
# --------------------------------------------------------------------------- #

def _report(**verdicts):
    return {"lanes": [{"lane": lane, "ok": verdict == LP.PASS,
                       "verdict": verdict, "detail": ""}
                      for lane, verdict in verdicts.items()]}


def test_the_gate_refuses_when_any_required_lane_failed():
    report = _report(**{PROVIDERS.FIRECRAWL: LP.PASS,
                        PROVIDERS.BRIGHTDATA_BROWSER: LP.FAIL_AUTH,
                        PROVIDERS.BRIGHTDATA_WEB_UNLOCKER: LP.PASS})
    may_start, reason = LP.gate(report)
    assert not may_start
    assert PROVIDERS.BRIGHTDATA_BROWSER in reason


def test_the_gate_refuses_a_lane_that_was_never_probed():
    """Fail closed: unprobed is not the same as fine."""
    report = _report(**{PROVIDERS.FIRECRAWL: LP.PASS})
    may_start, reason = LP.gate(report)
    assert not may_start
    assert "not probed" in reason


def test_the_gate_passes_only_when_every_required_lane_authenticated():
    report = _report(**{lane: LP.PASS for lane in LP.PAID_LANES})
    may_start, reason = LP.gate(report)
    assert may_start
    assert "3" in reason


# --------------------------------------------------------------------------- #
# The recorded live run.
# --------------------------------------------------------------------------- #

def test_the_recorded_preflight_exists_and_is_the_stop_that_was_reported():
    assert RECORD.is_file(), RECORD
    report = json.loads(RECORD.read_text(encoding="utf-8"))
    assert report["contract"] == LP.CONTRACT
    assert report["all_lanes_authenticated"] is False
    assert report["authentication_rejections"] == [PROVIDERS.BRIGHTDATA_BROWSER]

    by_lane = {row["lane"]: row for row in report["lanes"]}
    assert set(by_lane) == set(LP.PAID_LANES)
    assert by_lane[PROVIDERS.FIRECRAWL]["ok"] is True
    assert by_lane[PROVIDERS.BRIGHTDATA_WEB_UNLOCKER]["ok"] is True
    assert by_lane[PROVIDERS.BRIGHTDATA_BROWSER]["ok"] is False

    # The vendor's own words, kept, or the record is only an assertion.
    assert "407" in by_lane[PROVIDERS.BRIGHTDATA_BROWSER]["detail"]

    may_start, _ = LP.gate(report)
    assert not may_start, "the paid cohort must not start from this record"


def test_the_recorded_preflight_carries_no_credential():
    """The live run that produced this file printed a real password before the
    redaction ordering was fixed. The committed artifact must be clean of the
    whole secret AND of any prefix of it."""
    import os
    text = RECORD.read_text(encoding="utf-8")
    assert not client.contains_credential(text)
    for marker in ("brd-customer", "superproxy", "FIRECRAWL_API_KEY="):
        assert marker not in text, marker
    password = (os.environ.get(client.AUTH_ENV) or "").split("@")[0]
    password = password.rsplit(":", 1)[-1] if ":" in password else ""
    if len(password) > 4:
        assert password[:5] not in text, "a password PREFIX survived"


def test_the_recorded_preflight_metered_itself():
    """A preflight that claims to be free without measuring is the same class
    of unmeasured statement this package refuses elsewhere."""
    account = json.loads(RECORD.read_text(encoding="utf-8"))["account"]
    assert account["before"]["available"] is True
    assert account["after"]["available"] is True
    assert account["after"]["balance_usd_minor"] is not None
