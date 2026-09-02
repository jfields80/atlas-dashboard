# -*- coding: utf-8 -*-
"""PTF-FACTORY-THROUGHPUT-HARDENING-001 -- the acquisition ladder, and the
Firecrawl provenance block.

No network. Every Firecrawl call here goes through a patched ``_request``.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.pettripfinder.acquisition import firecrawl_capture as FC
from scripts.pettripfinder.acquisition import ladder as L
from scripts.pettripfinder.acquisition import providers as PROVIDERS
from scripts.pettripfinder.acquisition import registry as REGISTRY
from scripts.pettripfinder.brightdata import outcomes as O

REPO_ROOT = Path(__file__).resolve().parents[3]
REPORTS = REPO_ROOT / "launch_packages" / "pettripfinder" / "markets" / "reports"

IHG_URL = "https://www.ihg.com/holidayinnexpress/hotels/us/en/troy/daytr/hoteldetail"
WYNDHAM_URL = "https://www.wyndhamhotels.com/baymont/dayton-ohio/baymont-dayton-north/overview"
CHOICE_URL = "https://www.choicehotels.com/ohio/dayton/comfort-inn-hotels/oh123"
MARRIOTT_URL = "https://www.marriott.com/en-us/hotels/daytn-courtyard-dayton-north/overview/"
INDEP_URL = "https://www.cobblestonehotels.com/urbana"


# --------------------------------------------------------------------------- #
# The ladder itself.
# --------------------------------------------------------------------------- #

class TestTheLadder:

    def test_seven_rungs_in_the_documented_order(self):
        assert L.LANE_IDS == (
            L.OWNED_EVIDENCE, L.LOCAL_FREE_DISCOVERY, L.DIRECT_STATIC_FETCH,
            L.FIRECRAWL, L.ATTENDED_BROWSER, L.PAID_FETCH, L.PAID_IDENTITY_DISCOVERY)
        assert [l.rank for l in L.LADDER] == list(range(7))

    def test_free_rungs_precede_paid_ones_and_firecrawl_sits_between_static_and_attended(self):
        assert L.lane_rank(L.DIRECT_STATIC_FETCH) < L.lane_rank(L.FIRECRAWL) \
            < L.lane_rank(L.ATTENDED_BROWSER) < L.lane_rank(L.PAID_FETCH)
        assert L.LANE_BY_ID[L.FIRECRAWL].billed_in == "credits"
        assert L.LANE_BY_ID[L.FIRECRAWL].needs_authorization is True
        assert L.LANE_BY_ID[L.ATTENDED_BROWSER].billed_in == "none"

    def test_the_route_table_really_sends_three_families_to_firecrawl(self):
        assert L.firecrawl_routed_families() == ("CHOICE", "IHG", "WYNDHAM")
        assert PROVIDERS.FIRECRAWL in PROVIDERS.all_ids()


# --------------------------------------------------------------------------- #
# Candidacy: evidence-aware, and static is never outranked.
# --------------------------------------------------------------------------- #

class TestFirecrawlCandidacy:

    def test_a_static_success_is_never_escalated(self):
        c = L.firecrawl_candidacy(family="IHG", url=IHG_URL,
                                  prior_static_outcome=O.VALID)
        assert not c.candidate and c.reason == L.NOT_CANDIDATE_STATIC_ANSWERED

    @pytest.mark.parametrize("outcome", [O.POLICY_NOT_FOUND, O.IDENTITY_MISMATCH])
    def test_a_statement_about_the_page_does_not_escalate(self, outcome):
        c = L.firecrawl_candidacy(family="IHG", url=IHG_URL,
                                  prior_static_outcome=outcome)
        assert not c.candidate and c.reason == L.NOT_CANDIDATE_NOT_ESCALATABLE

    @pytest.mark.parametrize("family,url", [("IHG", IHG_URL), ("WYNDHAM", WYNDHAM_URL),
                                            ("CHOICE", CHOICE_URL)])
    def test_a_channel_failure_on_a_routed_family_is_a_candidate(self, family, url):
        c = L.firecrawl_candidacy(family=family, url=url,
                                  prior_static_outcome=O.ACCESS_DENIED)
        assert c.candidate and c.reason == L.CANDIDATE_ROUTED
        assert c.measured_by.startswith("PTF-")

    def test_a_measured_capability_wall_is_never_a_candidate(self):
        c = L.firecrawl_candidacy(family="MARRIOTT", url=MARRIOTT_URL,
                                  prior_static_outcome=O.ACCESS_DENIED)
        assert not c.candidate and c.reason == L.NOT_CANDIDATE_KNOWN_WALL
        assert c.measured_by == "PTF-FIRECRAWL-HARD-LANES-003"

    def test_an_unmeasured_family_is_probe_eligible_not_a_candidate(self):
        c = L.firecrawl_candidacy(family="INDEPENDENT", url=INDEP_URL,
                                  prior_static_outcome=O.ACCESS_DENIED)
        assert not c.candidate and c.reason == L.NOT_CANDIDATE_UNMEASURED
        assert c.probe_eligible is True

    def test_a_brand_index_url_is_not_a_candidate(self):
        c = L.firecrawl_candidacy(family="WYNDHAM",
                                  url="https://www.wyndhamhotels.com/baymont/search-results",
                                  prior_static_outcome=O.UNEXPECTED_PAGE)
        assert not c.candidate and c.reason == L.NOT_CANDIDATE_URL_SHAPE

    def test_an_unparseable_property_code_needs_a_routing_repair_not_a_credit(self):
        """Detroit FIRECRAWL-PASS-008 lost 49 of 65 attempts to exactly this."""
        c = L.firecrawl_candidacy(family="IHG",
                                  url="https://www.ihg.com/holidayinnexpress/hotels/us/troy/hoteldetail",
                                  prior_static_outcome=O.ACCESS_DENIED)
        assert not c.candidate and c.reason == L.NOT_CANDIDATE_CODE_UNPARSEABLE

    def test_a_second_firecrawl_attempt_on_one_url_is_refused(self):
        c = L.firecrawl_candidacy(family="IHG", url=IHG_URL,
                                  prior_static_outcome=O.ACCESS_DENIED,
                                  firecrawl_already_tried=True)
        assert not c.candidate and c.reason == L.NOT_CANDIDATE_ALREADY_TRIED

    def test_an_excluded_brand_is_refused_before_anything_else(self):
        excluded = next(iter(REGISTRY.excluded_brands()), None)
        if excluded is None:
            pytest.skip("the route table excludes no brand")
        c = L.firecrawl_candidacy(family=excluded, url=INDEP_URL,
                                  prior_static_outcome=O.ACCESS_DENIED)
        assert not c.candidate and c.reason == L.NOT_CANDIDATE_BRAND_EXCLUDED


# --------------------------------------------------------------------------- #
# Planning rows.
# --------------------------------------------------------------------------- #

def _row(**kw):
    base = dict(identity_key="x", family="IHG", url=IHG_URL)
    base.update(kw)
    return L.RowEvidence(**base)


class TestPlanRow:

    def test_owned_evidence_settles_a_row_before_any_fetch(self):
        d = L.plan_row(_row(owned_state=L.OWNED_EVIDENCE_ANSWERS,
                            static_outcome=O.ACCESS_DENIED))
        assert d.settled and d.next_lane == L.OWNED_EVIDENCE

    def test_an_untried_row_goes_to_the_static_lane_first(self):
        d = L.plan_row(_row())
        assert not d.settled and d.next_lane == L.DIRECT_STATIC_FETCH

    def test_a_static_answer_settles_the_row_and_firecrawl_never_outranks_it(self):
        for outcome in (O.VALID, O.POLICY_NOT_FOUND, O.IDENTITY_MISMATCH):
            d = L.plan_row(_row(static_outcome=outcome))
            assert d.settled and d.next_lane == L.DIRECT_STATIC_FETCH, outcome
            assert not d.firecrawl.candidate

    def test_a_static_channel_failure_on_a_routed_family_goes_to_firecrawl(self):
        d = L.plan_row(_row(static_outcome=O.ACCESS_DENIED))
        assert not d.settled and d.next_lane == L.FIRECRAWL
        assert d.firecrawl.candidate

    def test_a_static_channel_failure_on_a_walled_family_goes_to_the_browser(self):
        d = L.plan_row(_row(family="MARRIOTT", url=MARRIOTT_URL,
                            static_outcome=O.ACCESS_DENIED))
        assert d.next_lane == L.ATTENDED_BROWSER
        assert d.firecrawl.reason == L.NOT_CANDIDATE_KNOWN_WALL

    def test_a_firecrawl_answer_settles_the_row(self):
        for cls in (L.FIRECRAWL_PUBLICATION_GRADE, L.FIRECRAWL_SOURCE_SILENT,
                    L.FIRECRAWL_MISMATCH):
            d = L.plan_row(_row(static_outcome=O.ACCESS_DENIED, firecrawl_class=cls))
            assert d.settled and d.next_lane == L.FIRECRAWL, cls

    def test_a_firecrawl_block_falls_through_to_the_browser_not_back_to_firecrawl(self):
        d = L.plan_row(_row(static_outcome=O.ACCESS_DENIED,
                            firecrawl_class=L.FIRECRAWL_BLOCKED))
        assert not d.settled and d.next_lane == L.ATTENDED_BROWSER
        assert d.firecrawl.reason == L.NOT_CANDIDATE_ALREADY_TRIED

    def test_without_an_attended_session_the_next_rung_is_paid_and_gated(self):
        d = L.plan_row(_row(family="MARRIOTT", url=MARRIOTT_URL,
                            static_outcome=O.ACCESS_DENIED), attended_available=False)
        assert d.next_lane == L.PAID_FETCH
        assert L.LANE_BY_ID[L.PAID_FETCH].needs_authorization

    def test_a_row_without_a_routable_url_goes_to_discovery(self):
        d = L.plan_row(_row(url="", static_outcome=""))
        assert d.next_lane == L.LOCAL_FREE_DISCOVERY

    def test_an_unparseable_code_is_a_routing_repair_not_a_lane(self):
        d = L.plan_row(_row(url="https://www.ihg.com/holidayinnexpress/hotels/us/troy/hoteldetail",
                            static_outcome=O.ACCESS_DENIED))
        assert d.next_lane == L.LOCAL_FREE_DISCOVERY
        assert d.reason.startswith(L.ROUTING_REPAIR)


# --------------------------------------------------------------------------- #
# Classification (B6).
# --------------------------------------------------------------------------- #

class TestFirecrawlClassification:

    def test_the_six_classes_are_exhaustive_over_the_outcome_vocabulary(self):
        for outcome in O.ALL_OUTCOMES if hasattr(O, "ALL_OUTCOMES") else (
                O.VALID, O.ACCESS_DENIED, O.BLANK_PAGE, O.UNHYDRATED,
                O.IDENTITY_MISMATCH, O.POLICY_NOT_FOUND, O.NAVIGATION_FAILED,
                O.CAPTURE_FAILED, O.UNEXPECTED_PAGE):
            for confirmed in (True, False):
                cls = L.classify_firecrawl_result(outcome=outcome,
                                                  identity_confirmed=confirmed,
                                                  publication_grade=True)
                assert cls in L.FIRECRAWL_CLASSES, (outcome, confirmed)

    def test_publication_grade_needs_valid_confirmed_and_a_real_surface(self):
        assert L.classify_firecrawl_result(outcome=O.VALID, identity_confirmed=True,
                                           publication_grade=True,
                                           surface_strategy="brand_container") \
            == L.FIRECRAWL_PUBLICATION_GRADE

    @pytest.mark.parametrize("surface", ["amenity_chip", "brand_generic", "heading_only"])
    def test_an_amenity_chip_or_brand_page_is_identity_only(self, surface):
        assert L.classify_firecrawl_result(outcome=O.VALID, identity_confirmed=True,
                                           publication_grade=True,
                                           surface_strategy=surface) \
            == L.FIRECRAWL_IDENTITY_ONLY

    def test_a_confirmed_silence_is_source_silent(self):
        assert L.classify_firecrawl_result(outcome=O.POLICY_NOT_FOUND,
                                           identity_confirmed=True) \
            == L.FIRECRAWL_SOURCE_SILENT

    def test_a_mismatch_is_a_mismatch_whatever_else_arrived(self):
        assert L.classify_firecrawl_result(outcome=O.IDENTITY_MISMATCH,
                                           identity_confirmed=False,
                                           publication_grade=True) \
            == L.FIRECRAWL_MISMATCH

    def test_a_refusal_is_blocked_and_a_transport_failure_is_failed(self):
        assert L.classify_firecrawl_result(outcome=O.ACCESS_DENIED,
                                           identity_confirmed=False) == L.FIRECRAWL_BLOCKED
        assert L.classify_firecrawl_result(outcome=O.NAVIGATION_FAILED,
                                           identity_confirmed=False) == L.FIRECRAWL_FAILED

    def test_valid_without_a_confirmed_identity_is_not_evidence(self):
        assert L.classify_firecrawl_result(outcome=O.VALID, identity_confirmed=False,
                                           publication_grade=True) == L.FIRECRAWL_FAILED


# --------------------------------------------------------------------------- #
# The trigger (B7).
# --------------------------------------------------------------------------- #

class TestAttendedPressure:

    def test_the_warning_fires_at_twenty_percent_of_the_unresolved_routed_cohort(self):
        rows = [_row(identity_key="ihg-%d" % i, static_outcome=O.ACCESS_DENIED)
                for i in range(2)]
        rows += [_row(identity_key="mar-%d" % i, family="MARRIOTT", url=MARRIOTT_URL,
                      static_outcome=O.ACCESS_DENIED) for i in range(8)]
        pressure = L.attended_pressure(L.plan_cohort(rows))
        assert pressure["unresolved_routed"] == 10
        assert pressure["firecrawl_candidates"] == 2
        assert pressure["share_firecrawl_candidates"] == 0.2
        assert pressure["warning"] is True
        assert "evaluate the Firecrawl lane" in pressure["message"]

    def test_below_the_threshold_it_is_quiet(self):
        rows = [_row(identity_key="ihg-0", static_outcome=O.ACCESS_DENIED)]
        rows += [_row(identity_key="mar-%d" % i, family="MARRIOTT", url=MARRIOTT_URL,
                      static_outcome=O.ACCESS_DENIED) for i in range(9)]
        pressure = L.attended_pressure(L.plan_cohort(rows))
        assert pressure["warning"] is False and pressure["message"] == ""

    def test_settled_rows_leave_the_denominator(self):
        rows = [_row(identity_key="done", owned_state=L.OWNED_EVIDENCE_ANSWERS),
                _row(identity_key="ihg-0", static_outcome=O.ACCESS_DENIED)]
        pressure = L.attended_pressure(L.plan_cohort(rows))
        assert pressure["unresolved_routed"] == 1

    def test_an_empty_cohort_never_warns(self):
        assert L.attended_pressure([])["warning"] is False


# --------------------------------------------------------------------------- #
# Binding results (B5): never by position.
# --------------------------------------------------------------------------- #

class TestBinding:

    def _requests(self):
        return [L.Request("a", "https://x.example/a", L.FIRECRAWL),
                L.Request("b", "https://x.example/b", L.FIRECRAWL)]

    def test_results_bind_by_identity_and_url_regardless_of_order(self):
        out = L.bind_results(self._requests(), [
            {"identity_key": "b", "requested_url": "https://x.example/b",
             "identity_confirmed": True, "text": "B"},
            {"identity_key": "a", "requested_url": "https://x.example/a",
             "identity_confirmed": True, "text": "A"},
        ])
        assert out["bound"]["a"]["text"] == "A" and out["bound"]["b"]["text"] == "B"
        assert out["unbound"] == []

    def test_the_dayton_spa_defect_class_is_refused(self):
        """A's text arriving under B's URL binds to nobody."""
        out = L.bind_results(self._requests(), [
            {"identity_key": "a", "requested_url": "https://x.example/b",
             "identity_confirmed": True, "text": "A"}])
        assert out["bound"] == {}
        assert out["unbound"][0]["why"] == L.UNBOUND_URL_MISMATCH

    def test_a_result_without_an_identity_never_binds_by_position(self):
        out = L.bind_results(self._requests(), [
            {"requested_url": "https://x.example/a", "identity_confirmed": True}])
        assert out["bound"] == {}
        assert out["unbound"][0]["why"] == L.UNBOUND_NO_IDENTITY

    def test_an_unconfirmed_identity_never_binds(self):
        out = L.bind_results(self._requests(), [
            {"identity_key": "a", "requested_url": "https://x.example/a",
             "identity_confirmed": False}])
        assert out["bound"] == {}
        assert out["unbound"][0]["why"] == L.UNBOUND_IDENTITY_UNCONFIRMED

    def test_a_second_result_for_one_request_is_refused(self):
        r = {"identity_key": "a", "requested_url": "https://x.example/a",
             "identity_confirmed": True}
        out = L.bind_results(self._requests(), [r, dict(r)])
        assert list(out["bound"]) == ["a"]
        assert out["unbound"][0]["why"] == L.UNBOUND_DUPLICATE

    def test_an_unrequested_identity_is_reported(self):
        out = L.bind_results(self._requests(), [
            {"identity_key": "zzz", "requested_url": "https://x.example/a",
             "identity_confirmed": True}])
        assert out["unbound"][0]["why"] == L.UNBOUND_UNKNOWN_IDENTITY

    def test_two_requests_for_one_identity_and_url_are_refused_up_front(self):
        with pytest.raises(ValueError):
            L.bind_results([L.Request("a", "https://x.example/a", L.FIRECRAWL),
                            L.Request("a", "https://x.example/a", L.FIRECRAWL)], [])


# --------------------------------------------------------------------------- #
# The Dayton replay (Part C) reproduces from the committed reports.
# --------------------------------------------------------------------------- #

@pytest.fixture(scope="module")
def static_only():
    static = json.loads((REPORTS / "dayton_oh_free_static_capture_001.json")
                        .read_text(encoding="utf-8"))
    return L.plan_document(L.rows_from_reports(static_report=static),
                           market_id="dayton-oh",
                           work_order="PTF-FACTORY-THROUGHPUT-HARDENING-001")


class TestDaytonReplay:

    def test_the_static_failures_split_as_the_benchmark_reports(self, static_only):
        lanes = static_only["by_next_lane_unsettled"]
        assert static_only["rows"] == 48
        assert lanes[L.FIRECRAWL] == 33
        assert lanes[L.ATTENDED_BROWSER] == 12
        assert lanes[L.LOCAL_FREE_DISCOVERY] == 1
        assert static_only["attended_pressure"]["warning"] is True

    def test_every_firecrawl_candidate_is_a_routed_family_with_a_parseable_identity(self, static_only):
        for d in static_only["decisions"]:
            if d["next_lane"] == L.FIRECRAWL:
                assert d["family"] in ("IHG", "WYNDHAM", "CHOICE"), d
                assert d["firecrawl_reason"] == L.CANDIDATE_ROUTED

    def test_nothing_the_static_lane_answered_is_re_fetched(self, static_only):
        for d in static_only["decisions"]:
            if d["settled"]:
                assert d["next_lane"] == L.DIRECT_STATIC_FETCH


# --------------------------------------------------------------------------- #
# Firecrawl adapter provenance -- no network.
# --------------------------------------------------------------------------- #

class TestFirecrawlProvenance:

    @pytest.fixture(autouse=True)
    def _no_ledger(self, monkeypatch):
        monkeypatch.setattr(FC, "RECORD_CALLS", False)

    def test_the_request_envelope_is_deterministic_and_carries_no_secret(self, monkeypatch):
        monkeypatch.setenv(FC.KEY_ENV, "fc-test-secret-value")
        a = FC.request_envelope(IHG_URL, profile=FC.ROUTED_PROFILE)
        b = FC.request_envelope(IHG_URL, profile=dict(FC.ROUTED_PROFILE))
        assert a["envelope_sha256"] == b["envelope_sha256"]
        assert "fc-test-secret-value" not in json.dumps(a)
        assert a["body"]["url"] == IHG_URL and a["body"]["formats"] == ["rawHtml"]
        c = FC.request_envelope(WYNDHAM_URL, profile=FC.ROUTED_PROFILE)
        assert c["envelope_sha256"] != a["envelope_sha256"]

    def test_fetch_returns_provenance_with_content_hash_and_request_id(self, monkeypatch):
        monkeypatch.setenv(FC.KEY_ENV, "fc-test-secret-value")
        html = "<html><title>Holiday Inn Express Troy</title><body>Pets: no</body></html>"

        def fake_request(url, *, data=None, timeout=0):
            assert data["url"] == IHG_URL
            return {"success": True, "data": {"rawHtml": html, "metadata": {
                "statusCode": 200, "sourceURL": IHG_URL, "title": "HIE Troy",
                "scrapeId": "scr_123", "creditsUsed": 1}}}

        monkeypatch.setattr(FC, "_request", fake_request)
        result = FC.fetch(IHG_URL, profile=FC.ROUTED_PROFILE)
        prov = result["provenance"]
        assert prov["provider"] == "Firecrawl"
        assert prov["requested_url"] == IHG_URL and prov["final_url"] == IHG_URL
        assert prov["status"] == 200 and prov["ok"] is True
        assert prov["captured_at"]
        assert prov["content_sha256"] == __import__("hashlib").sha256(html.encode()).hexdigest()
        assert prov["provider_request_id"] == "scr_123"
        assert prov["credits_used"] == 1
        assert prov["envelope_sha256"] == FC.request_envelope(
            IHG_URL, profile=FC.ROUTED_PROFILE)["envelope_sha256"]
        assert "fc-test-secret-value" not in json.dumps(prov)

    def test_a_vendor_error_is_redacted_in_the_provenance(self, monkeypatch):
        monkeypatch.setenv(FC.KEY_ENV, "fc-test-secret-value")
        monkeypatch.setattr(FC, "_request", lambda url, *, data=None, timeout=0: {
            "success": False, "error": "bad key fc-test-secret-value refused", "id": "req_9"})
        result = FC.fetch(IHG_URL)
        assert result["ok"] is False
        assert "fc-test-secret-value" not in json.dumps(result)
        assert "<redacted:firecrawl-key>" in result["provenance"]["error"]
        assert result["provenance"]["content_sha256"] == ""

    def test_the_call_ledger_records_each_call_once(self, monkeypatch, tmp_path):
        monkeypatch.setenv(FC.KEY_ENV, "fc-test-secret-value")
        monkeypatch.setattr(FC, "RECORD_CALLS", True)
        monkeypatch.setattr(FC, "CALL_LEDGER_PATH", tmp_path / "calls.jsonl")
        monkeypatch.setattr(FC, "_request", lambda url, *, data=None, timeout=0: {
            "success": True, "data": {"rawHtml": "<html>x</html>", "metadata": {"statusCode": 200}}})
        FC.fetch(IHG_URL)
        FC.fetch(WYNDHAM_URL)
        lines = (tmp_path / "calls.jsonl").read_text(encoding="utf-8").splitlines()
        assert len(lines) == 2
        assert {json.loads(l)["requested_url"] for l in lines} == {IHG_URL, WYNDHAM_URL}
        assert all("fc-test-secret-value" not in l for l in lines)

    def test_the_retry_ceiling_is_the_shared_one(self):
        from scripts.pettripfinder.brightdata import browser_capture as BC
        assert FC.MAX_ATTEMPTS_PER_URL == BC.MAX_ATTEMPTS
        assert FC.REQUEST_TIMEOUT_SECONDS > 0
