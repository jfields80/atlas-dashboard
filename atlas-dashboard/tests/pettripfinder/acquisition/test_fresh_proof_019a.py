"""PTF-CANONICAL-POLICY-LOCATOR-FRESH-PROOF-019A.

019 proved the canonical locator contract offline, across artifacts that were
already on disk, and recorded the fresh end-to-end proof as
BLOCKED_NO_PROVIDER_CREDENTIAL. 019A ran it: four properties, one per lane,
captured live and replayed from disk.

WHAT THESE TESTS GUARD
----------------------
Two different things, and keeping them apart is the point.

The HARNESS tests build a capture through the production persist function and
exercise the proof's own machinery -- the replay, the provider guard, the
tamper control, the cost arithmetic -- against it. They make no provider call
and are deterministic.

The COMMITTED REPORT tests read the artifact the live run produced and assert
what it actually says: 4 of 4, every replay canonical, zero provider calls
during replay, every tamper control refused, and nothing published.

The tests deliberately do NOT re-run the acquisition. A test suite that spends
money to pass is a test suite that stops being run.
"""

import json
import socket
import subprocess
import sys
from pathlib import Path

import pytest

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts.pettripfinder.acquisition import firecrawl_capture as FC     # noqa: E402
from scripts.pettripfinder.acquisition import fresh_proof_019a as FP      # noqa: E402
from scripts.pettripfinder.acquisition import providers as PROVIDERS      # noqa: E402
from scripts.pettripfinder.acquisition import registry as REGISTRY        # noqa: E402
from scripts.pettripfinder.brightdata import policy_locator as PL         # noqa: E402
from scripts.pettripfinder.brightdata import unlocker_capture as UC       # noqa: E402

DOCUMENT = """<html><body>
<div class="page"><div class="col"><h2>Amenities</h2>
<div class="pet"><h3>Pet Policy</h3>
<p>Pets are welcome. A $35 fee per night applies, maximum 2 pets per room.</p>
<p>Each pet must weigh 50 lbs or less. Service animals stay free.</p></div>
</div></div></body></html>"""


def report():
    return json.loads(FP.REPORT.read_text(encoding="utf-8-sig"))


def a_capture(directory: Path):
    """One capture written by the production persist function, with a record."""
    hit = UC.locate_policy_in_html(DOCUMENT)
    assert hit.found
    UC._persist(attempt_dir=directory, html=DOCUMENT,
                body_text=UC.html_to_text(DOCUMENT), block_text=hit.text,
                hit=hit)
    return hit


# --------------------------------------------------------------------------- #
# The subject of the proof cannot drift.
# --------------------------------------------------------------------------- #

def test_the_cohort_is_the_four_properties_the_work_order_named():
    """Pinned, in the prompt's own words. A substitution is a different proof."""
    assert len(FP.COHORT) == 4 == FP.PASS_BAR
    assert {p.lane for p in FP.COHORT} == {
        "CHOICE", "WYNDHAM", "IHG", "GENERIC_INDEPENDENT"}
    assert [p.canonical_name for p in FP.COHORT] == [
        "Cambria Hotel Milwaukee Downtown",
        "Ambassador Hotel Milwaukee, Trademark Collection by Wyndham",
        "avid hotels Milwaukee West - Waukesha",
        "Cobblestone Hotel & Suites - Waukesha/West Milwaukee",
    ]


def test_every_pinned_property_still_matches_the_committed_queue():
    """The cohort's URL and brand are the committed ones, not a fresh lookup."""
    checks = FP.verify_cohort()
    assert checks["all_match_committed_queue"], checks["checks"]


def test_the_registry_routes_the_cohort_exactly_where_019_left_it():
    """019A changed no route. Asserted against the registry, not the report."""
    routes = FP.verify_routes()
    assert routes["all_routes_as_registered"], routes["checks"]
    by_lane = {c["lane"]: c for c in routes["checks"]}
    assert by_lane["CHOICE"]["resolved_provider"] == PROVIDERS.FIRECRAWL
    assert by_lane["WYNDHAM"]["resolved_provider"] == PROVIDERS.FIRECRAWL
    assert by_lane["IHG"]["resolved_provider"] == PROVIDERS.FIRECRAWL
    assert (by_lane["GENERIC_INDEPENDENT"]["resolved_provider"]
            == PROVIDERS.BRIGHTDATA_BROWSER)
    # The three brand lanes forbid the Browser API on cost. 019A must not have
    # quietly re-entered it to make a capture succeed.
    for lane in ("CHOICE", "WYNDHAM", "IHG"):
        assert PROVIDERS.BRIGHTDATA_BROWSER in by_lane[lane]["forbidden_providers"]


def test_provider_health_never_reports_a_credential_value():
    """Health is reported as a variable NAME and a pinned geography.

    The proof has to state that the lanes were up. It must not state what made
    them up.
    """
    detail = " ".join(v["detail"] for v in FP.provider_health().values())
    assert FC.KEY_ENV in detail or "credential present" in detail
    for secret in (FC.KEY_ENV, "BRIGHTDATA_AUTH"):
        value = __import__("os").environ.get(secret) or ""
        if value:
            assert value not in detail
            assert value not in json.dumps(report())


# --------------------------------------------------------------------------- #
# The replay: from disk, byte for byte, and against its own record.
# --------------------------------------------------------------------------- #

def test_a_fresh_capture_replays_byte_identically_from_disk(tmp_path):
    hit = a_capture(tmp_path)
    row = FP.replay_one(tmp_path)

    assert row["block_persisted"] and row["locator_persisted"]
    assert row["locator_contract"] == PL.CONTRACT
    assert row["replay_status"] == PL.REPLAYED
    assert row["byte_identical_to_disk"]
    assert row["block_hash_verified"]
    assert row["document_hash_verified"]
    assert row["block_sha256_on_disk"] == PL.sha256_text(hit.text)


def test_the_replay_reaches_no_provider(tmp_path):
    a_capture(tmp_path)
    row = FP.replay_one(tmp_path)
    assert row["provider_calls_during_replay"] == 0
    assert row["provider_calls_detail"] == []


def test_the_guard_would_have_caught_a_provider_call():
    """The control for the test above.

    Zero observed calls only means something if a call would have been seen.
    Each layer is provoked deliberately, so the guard is proved to bite rather
    than assumed to.
    """
    with FP.no_provider_calls():
        with pytest.raises(FP.ProviderCallDuringReplay):
            socket.socket().connect(("127.0.0.1", 9))
        with pytest.raises(FP.ProviderCallDuringReplay):
            subprocess.run(["echo", "hi"])
        with pytest.raises(FP.ProviderCallDuringReplay):
            FC.fetch("https://example.invalid")


def test_the_guard_puts_everything_back():
    """A guard that leaked would break every test that ran after it."""
    before = (socket.socket.connect, subprocess.run, FC.fetch, UC._run_scrape)
    with FP.no_provider_calls():
        pass
    assert (socket.socket.connect, subprocess.run, FC.fetch,
            UC._run_scrape) == before


def test_a_cold_process_with_no_credentials_replays_the_same_bytes(tmp_path):
    """The strongest form of "offline".

    The guard proves the replay made no call. This proves it could not have:
    a fresh interpreter, every provider credential removed from its
    environment, and the same block out.
    """
    hit = a_capture(tmp_path)
    cold = FP.cold_replay(tmp_path)
    assert cold["ran"], cold.get("stderr")
    assert cold["credentials_visible"] == []
    assert cold["status"] == PL.REPLAYED
    assert cold["canonical"] and cold["byte_identical_to_disk"]
    assert cold["block_sha256"] == PL.sha256_text(hit.text)


def test_the_live_runs_captures_replay_cold_and_agree():
    """What the committed report records for the four fresh captures."""
    cold = report().get("cold_replay")
    assert cold, "the cold replay is missing from the report"
    assert cold["captures_replayed_cold"] == 4
    assert cold["all_agree"]
    assert cold["no_child_saw_a_provider_credential"]
    for row in cold["rows"]:
        assert row["status"] == PL.REPLAYED, row["lane"]
        assert row["byte_identical_to_disk"]
        assert row["credentials_visible"] == []


# --------------------------------------------------------------------------- #
# The tamper control.
# --------------------------------------------------------------------------- #

def test_a_tampered_block_is_refused(tmp_path):
    a_capture(tmp_path)
    control = FP.tamper_control(tmp_path)
    assert control["returned_hash_mismatch"]
    assert control["tampered_copy_status"] == PL.HASH_MISMATCH


def test_the_tamper_control_leaves_the_real_artifact_alone(tmp_path):
    """Temporary means temporary. Proved from the bytes, not from intent."""
    a_capture(tmp_path)
    original = (tmp_path / PL.BLOCK_ARTIFACT).read_bytes()
    control = FP.tamper_control(tmp_path)
    assert control["original_block_unchanged"]
    assert (tmp_path / PL.BLOCK_ARTIFACT).read_bytes() == original
    assert FP.replay_one(tmp_path)["replay_status"] == PL.REPLAYED


def test_a_capture_predating_the_contract_cannot_be_tamper_proved(tmp_path):
    """The reason 019A needed a FRESH capture, stated as a test.

    A legacy capture has a block and no record, so nothing attests to its
    bytes and there is no hash for a tamper to mismatch. It replays exactly and
    says so; it does not get to claim the canonical status it never earned.
    """
    hit = UC.locate_policy_in_html(DOCUMENT)
    UC._persist(attempt_dir=tmp_path, html=DOCUMENT,
                body_text=UC.html_to_text(DOCUMENT), block_text=hit.text)
    row = FP.replay_one(tmp_path)
    assert row["replay_status"] == PL.BLOCK_ONLY
    assert row["byte_identical_to_disk"]          # exact, but unattested
    assert not FP.tamper_control(tmp_path)["returned_hash_mismatch"]


# --------------------------------------------------------------------------- #
# The gate arithmetic. A partial pass must not round up.
# --------------------------------------------------------------------------- #

def _passing_rows(tmp_path):
    a_capture(tmp_path)
    capture_row = {"captured": True}
    return capture_row, FP.replay_one(tmp_path), FP.tamper_control(tmp_path)


def test_every_gate_must_hold_for_a_property_to_pass(tmp_path):
    capture_row, replay_row, tamper_row = _passing_rows(tmp_path)
    verdict = FP.assess(capture_row, replay_row, tamper_row)
    assert verdict["passed"] and verdict["failed_gates"] == []
    assert set(verdict["gates"]) == {name for name, _ in FP.GATES}


@pytest.mark.parametrize("gate,break_it", [
    ("live_capture", lambda c, r, t: c.update({"captured": False})),
    ("block_persisted", lambda c, r, t: r.update({"block_persisted": False})),
    ("byte_identical", lambda c, r, t: r.update({"byte_identical_to_disk": False})),
    ("block_hash_verified", lambda c, r, t: r.update({"block_hash_verified": False})),
    ("zero_provider_calls",
     lambda c, r, t: r.update({"provider_calls_during_replay": 1})),
    ("tamper_refused", lambda c, r, t: t.update({"returned_hash_mismatch": False})),
])
def test_a_broken_gate_fails_the_property(gate, break_it, tmp_path):
    capture_row, replay_row, tamper_row = _passing_rows(tmp_path)
    break_it(capture_row, replay_row, tamper_row)
    verdict = FP.assess(capture_row, replay_row, tamper_row)
    assert not verdict["passed"]
    assert gate in verdict["failed_gates"]


def test_a_block_only_replay_does_not_count_as_canonical(tmp_path):
    """BLOCK_ONLY is exact and unattested, and 019A's bar is attested."""
    capture_row, replay_row, tamper_row = _passing_rows(tmp_path)
    replay_row["replay_status"] = PL.BLOCK_ONLY
    verdict = FP.assess(capture_row, replay_row, tamper_row)
    assert "replayed_canonically" in verdict["failed_gates"]


# --------------------------------------------------------------------------- #
# Cost arithmetic: an unknown must never present as a zero.
# --------------------------------------------------------------------------- #

def _reading(zones, credits, at="2026-08-20T12:00:00+00:00"):
    return {"label": "t", "read_at": at,
            "brightdata_zone_cost_month_usd_minor": zones,
            "firecrawl_credits_remaining": credits}


def test_an_unreadable_zone_meter_is_none_and_not_zero():
    before = _reading({z: 10 for z in FP.BILLABLE_ZONES}, 100)
    after = _reading({**{z: 10 for z in FP.BILLABLE_ZONES},
                      FP.BILLABLE_ZONES[0]: None}, 90)
    delta = FP.spend_delta(before, after)
    assert delta["brightdata_usd_minor_total"] is None
    assert delta["firecrawl_credits_consumed"] == 10


def test_a_flat_meter_is_reported_as_not_having_moved():
    """The distinction the run depends on: flat is not the same as free."""
    flat = {z: 10 for z in FP.BILLABLE_ZONES}
    delta = FP.spend_delta(_reading(flat, 100), _reading(dict(flat), 97))
    assert delta["brightdata_usd_minor_total"] == 0
    assert delta["brightdata_meter_moved"] is False
    assert delta["firecrawl_credits_consumed"] == 3


def test_the_two_currencies_are_never_summed():
    delta = FP.spend_delta(
        _reading({z: 10 for z in FP.BILLABLE_ZONES}, 100),
        _reading({**{z: 10 for z in FP.BILLABLE_ZONES},
                  FP.BILLABLE_ZONES[0]: 26}, 97))
    assert delta["brightdata_usd_minor_total"] == 16
    assert delta["firecrawl_credits_consumed"] == 3
    assert "never" in delta["note"]


def test_the_brightdata_estimate_is_labelled_as_an_estimate():
    estimate = FP.lane_rate_estimate(
        [{"provider_used": PROVIDERS.BRIGHTDATA_BROWSER, "estimated_bytes": 10},
         {"provider_used": PROVIDERS.FIRECRAWL, "estimated_bytes": 0}])
    assert estimate["is_an_estimate"] is True
    assert estimate["brightdata_browser_properties"] == 1
    assert estimate["measured_by"]


# --------------------------------------------------------------------------- #
# What the live run actually produced.
# --------------------------------------------------------------------------- #

def test_the_committed_report_records_four_of_four():
    doc = report()
    assert doc["work_order"] == FP.WORK_ORDER
    assert doc["pass_bar"] == 4
    assert doc["properties_passed"] == 4
    assert doc["pass_bar_met"] and doc["status"] == "PASS"


def test_the_live_run_covered_one_property_per_lane():
    lanes = {row["lane"]: row for row in report()["rows"]}
    assert set(lanes) == {"CHOICE", "WYNDHAM", "IHG", "GENERIC_INDEPENDENT"}
    assert lanes["CHOICE"]["provider_used"] == PROVIDERS.FIRECRAWL
    assert lanes["WYNDHAM"]["provider_used"] == PROVIDERS.FIRECRAWL
    assert lanes["IHG"]["provider_used"] == PROVIDERS.FIRECRAWL
    assert (lanes["GENERIC_INDEPENDENT"]["provider_used"]
            == PROVIDERS.BRIGHTDATA_BROWSER)


def test_every_lane_took_the_route_the_registry_gave_it():
    doc = report()
    assert doc["provider_usage"]["every_property_took_its_registered_lane"]
    assert all(not row["fallback_invoked"] for row in doc["rows"])


def test_every_replay_in_the_live_run_was_canonical_and_offline():
    doc = report()
    for row in doc["rows"]:
        replay = row["replay"]
        assert replay["replay_status"] == PL.REPLAYED, row["lane"]
        assert replay["canonical"]
        assert replay["byte_identical_to_disk"]
        assert replay["block_hash_verified"]
        assert replay["document_hash_verified"]
        assert replay["provider_calls_during_replay"] == 0
    assert doc["provider_usage"]["provider_calls_during_replay"] == 0


def test_every_tamper_control_was_refused_and_left_the_evidence_intact():
    for row in report()["rows"]:
        control = row["tamper_control"]
        assert control["tampered_copy_status"] == PL.HASH_MISMATCH, row["lane"]
        assert control["original_block_unchanged"]


def test_the_report_does_not_bank_the_unsettled_brightdata_zero():
    """The honesty gate on the cost figure.

    The Bright Data month-to-date meter does not settle inside a run that lasts
    under a minute. If it did not move, the report has to say the meter did not
    move -- not that the run was free.
    """
    cost = report()["incremental_cost"]
    acquisition = cost["acquisition"]
    assert "brightdata_meter_moved" in acquisition
    if not acquisition["brightdata_meter_moved"]:
        assert cost["brightdata_lane_estimate"]["is_an_estimate"] is True
        assert cost["brightdata_meter_is_not_evidence_over_this_window"]


def test_the_settled_followup_reports_what_the_run_could_not_see():
    """The correction to the unsettled zero, and its own limits.

    The in-run figure and the settled figure disagree, which is the finding.
    The settled one must be labelled with the reason it cannot be attributed
    to a single run with certainty, rather than presented as exact.
    """
    cost = report()["incremental_cost"]
    followup = cost.get("settled_followup")
    assert followup, "the settled follow-up reading is missing from the report"
    assert followup["status"] in ("MEASURED", "BRIGHTDATA_METER_STILL_UNSETTLED")
    assert followup["attribution_caveat"]
    assert followup["seconds_after_run_started"] > cost["acquisition"]["window_seconds"]
    if followup["status"] == "MEASURED":
        # The meter moved once it settled, so the in-run zero was lag.
        assert followup["delta_since_before_reading"]["brightdata_usd_minor_total"]
        assert not cost["acquisition"]["brightdata_meter_moved"]


def test_the_firecrawl_credit_delta_is_the_measured_acquisition_cost():
    doc = report()
    acquisition = doc["incremental_cost"]["acquisition"]
    firecrawl_rows = [r for r in doc["rows"]
                      if r["provider_used"] == PROVIDERS.FIRECRAWL]
    # One credit per property, and the plan endpoint agrees with the per-lane
    # figures. Credits settle immediately, so this one IS a measurement.
    assert acquisition["firecrawl_credits_consumed"] == len(firecrawl_rows)
    assert doc["incremental_cost"]["replay"]["firecrawl_credits_consumed"] == 0


# --------------------------------------------------------------------------- #
# Blast radius: 019A proves a contract and changes nothing else.
# --------------------------------------------------------------------------- #

def test_019a_wrote_no_authority_and_published_nothing():
    doc = report()
    assert doc["authority_written"] is False
    assert doc["observations_updated"] is False
    assert doc["published"] is False
    assert doc["routes_changed"] is False
    assert doc["readers_changed"] is False


def test_no_milwaukee_policy_authority_appeared():
    """Milwaukee still holds no published policy record. 019A published none.

    The same check 019 makes, against the same glob: a Milwaukee policy-facts
    authority would be the artifact a publication produces, and four fresh
    publication-grade captures are exactly the circumstance in which one could
    have been written by accident.
    """
    found = list((REPO / "launch_packages" / "pettripfinder")
                 .rglob("*hotel_policy_facts*milwaukee*"))
    assert not found, found


def test_the_registry_file_is_untouched_by_this_work_order():
    """The routes 019A asserts are the routes the last route decision left."""
    changed = subprocess.run(
        ["git", "log", "-1", "--format=%H", "--",
         "atlas-dashboard/scripts/pettripfinder/acquisition/routes.json"],
        cwd=str(REPO.parent), capture_output=True, text=True).stdout.strip()
    head = subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(REPO.parent),
                          capture_output=True, text=True).stdout.strip()
    assert changed and changed != head, (
        "routes.json was last changed by this commit; 019A must change no route")


def test_the_captures_live_outside_version_control():
    """Captures carry provider responses and must never be committed."""
    ignored = subprocess.run(
        ["git", "check-ignore", "-q",
         str(FP.RUN_ROOT.relative_to(REPO)).replace("\\", "/")],
        cwd=str(REPO), capture_output=True, text=True)
    assert ignored.returncode == 0, "the 019A capture tree is not gitignored"
