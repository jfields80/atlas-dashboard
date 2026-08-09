"""State machine transitions, the adapter contract, and manifest derivation."""

from __future__ import annotations

import json

import pytest

from services.research_workers.capture_automation.adapters import (
    BaseAdapter, adapter_for, known_brands, register,
)
from services.research_workers.capture_automation.adapters.hilton import HiltonAdapter
from services.research_workers.capture_automation.adapters.marriott import (
    MarriottAdapter,
)
from services.research_workers.capture_automation.contracts import (
    DomSnapshot, InteractionStep, PolicyLocation,
)
from services.research_workers.capture_automation.manifest import (
    Journal, archived_text_hashes, build_manifest, write_manifest,
)
from services.research_workers.capture_automation.reasons import (
    EXCEPTION_REASONS, RETRY_MANUAL, explain, retry_for,
)
from services.research_workers.capture_automation.state_machine import (
    CAPTURED, CAPTURING, EXCEPTION, IDENTITY, INTERACTING, NAVIGATING,
    ORDERED_STATES, POLICY_SCAN, QUEUED, StateError, URL_SHAPE, VALIDATING,
    HotelOutcome, fail, next_state,
)

from .conftest import fixture_names, load_fixture, snapshot_for


class TestTransitions:
    def test_the_happy_path_runs_in_order(self):
        state = QUEUED
        seen = [state]
        while state != CAPTURED:
            state = next_state(state)
            seen.append(state)
        assert seen == list(ORDERED_STATES)

    @pytest.mark.parametrize("state", [
        QUEUED, NAVIGATING, URL_SHAPE, IDENTITY, POLICY_SCAN, INTERACTING,
        CAPTURING, VALIDATING])
    def test_any_state_can_fail_to_exception(self, state):
        assert fail(state, "UNEXPECTED_ERROR") == EXCEPTION

    def test_terminal_states_have_no_exit(self):
        for terminal in (CAPTURED, EXCEPTION):
            with pytest.raises(StateError):
                next_state(terminal)
            with pytest.raises(StateError):
                fail(terminal, "UNEXPECTED_ERROR")

    def test_an_unknown_state_is_an_error(self):
        with pytest.raises(StateError, match="unknown state"):
            next_state("DAYDREAMING")


class TestOutcomes:
    def test_a_capture_has_no_retry(self):
        assert HotelOutcome("a", CAPTURED).retry == ""
        assert HotelOutcome("a", CAPTURED).succeeded

    def test_an_exception_carries_its_disposition(self):
        out = HotelOutcome("a", EXCEPTION, "CAPTCHA_OR_CHALLENGE")
        assert out.retry == RETRY_MANUAL
        assert out.is_challenge

    def test_serialisation_round_trips_the_essentials(self):
        out = HotelOutcome("a", EXCEPTION, "POLICY_NOT_FOUND", ("x",))
        d = out.to_dict()
        assert d["hotel_id"] == "a" and d["reason"] == "POLICY_NOT_FOUND"
        assert d["retry"] == retry_for("POLICY_NOT_FOUND")

    def test_an_unknown_reason_defaults_to_a_human(self):
        assert retry_for("SOMETHING_NEW") == RETRY_MANUAL
        assert explain("SOMETHING_NEW")


class TestAdapterContract:
    def test_the_registered_brands_are_exactly_the_supported_ones(self):
        """Phase 1 shipped Marriott and Hilton; 2A added IHG; 004B added Wyndham.

        Wyndham was previously absent on the grounds that its pages answer
        ordinary retrieval with HTTP 200 and EXACT_MATCH. That was half right:
        the 200 does not carry the policy, which exists only after rendering
        and a click. PTF-CAPTURE-004A gave that state its own classification
        and 004B registers the adapter it licenses.

        Hyatt is still absent, and for a reason that has not changed --
        hyatt.com serves a Kasada interstitial our automation must not defeat.
        """
        # PTF-COLUMBUS-INTEGRATE-UNRESOLVED-001 registered three more brands,
        # each PROVISIONAL and selector-free, so eight confirmed Columbus
        # identities could be attempted at all. Hyatt is deliberately not
        # among them and the assertion below is why this test exists.
        assert set(known_brands()) == {"marriott", "hilton", "ihg", "wyndham",
                                       "bestwestern", "choice", "redroof"}
        assert adapter_for("hyatt") is None

    def test_an_unknown_brand_returns_none(self):
        assert adapter_for("fictional-inns") is None
        assert adapter_for("") is None

    def test_lookup_is_case_insensitive(self):
        assert adapter_for("MARRIOTT").brand == "marriott"

    @pytest.mark.parametrize("adapter", [MarriottAdapter(), HiltonAdapter()])
    def test_consent_is_never_auto_dismissed_in_phase_one(self, adapter):
        """The operator ruled consent banners an exception. Returning nothing
        is that ruling, in code."""
        assert adapter.consent_selectors() == ()

    @pytest.mark.parametrize("adapter", [MarriottAdapter(), HiltonAdapter()])
    def test_adapters_are_pure_functions_of_a_snapshot(self, adapter):
        """No adapter may hold a browser handle, so calling twice on the same
        snapshot must give the same answer."""
        dom = snapshot_for("marriott-cmham.json" if adapter.brand == "marriott"
                           else "hilton-cmhaphx.json")
        first, second = adapter.locate_policy(dom), adapter.locate_policy(dom)
        assert first.text_excerpt == second.text_excerpt

    def test_an_adapter_cannot_widen_the_url_gate(self):
        """A brand may narrow, never loosen: a search URL stays refused."""
        for adapter in (MarriottAdapter(), HiltonAdapter()):
            assert not adapter.url_is_property_page(
                "https://www.marriott.com/search/findHotels.mi?d=Columbus")

    def test_the_plan_scrolls_the_policy_into_view(self):
        adapter = MarriottAdapter()
        dom = snapshot_for("marriott-cmham.json")
        loc = adapter.locate_policy(dom)
        plan = adapter.interaction_plan(dom, PolicyLocation(
            selector="#hotel-policies", matched_anchors=loc.matched_anchors,
            score=loc.score, text_excerpt=loc.text_excerpt))
        assert any(s.action == "scroll_into_view" for s in plan)

    def test_no_click_is_proposed_for_a_control_the_page_lacks(self):
        adapter = MarriottAdapter()
        dom = DomSnapshot(final_url="https://x/y", html="<html></html>", text="Pets")
        plan = adapter.interaction_plan(dom, None)
        assert not [s for s in plan if s.action == "click"]

    def test_brand_extra_anchors_are_applied(self):
        """Hilton's compressed notation needs its own labels to score."""
        assert "Max weight" in HiltonAdapter().extra_anchors
        assert "Non-Refundable Pet Fee Per Stay" in MarriottAdapter().extra_anchors

    def test_a_custom_adapter_can_register(self):
        class Fake(BaseAdapter):
            brand = "test-only-brand"
        register(Fake())
        try:
            assert adapter_for("test-only-brand").brand == "test-only-brand"
        finally:
            from services.research_workers.capture_automation.adapters import registry
            registry._REGISTRY.pop("test-only-brand", None)


class TestJournalAndManifest:
    def test_append_and_read_back(self, tmp_path):
        j = Journal.open(tmp_path)
        j.append(HotelOutcome("a", CAPTURED, artifacts={"text_sha256": "d1"}),
                 at="2026-07-31T00:00:00Z")
        j.append(HotelOutcome("b", EXCEPTION, "POLICY_NOT_FOUND"), at="t")
        assert j.completed_hotel_ids() == ("a", "b")
        assert j.captured_text_hashes() == {"d1": "a"}

    def test_an_empty_journal_is_not_an_error(self, tmp_path):
        assert Journal.open(tmp_path).completed_hotel_ids() == ()

    def test_both_terminal_states_count_as_complete(self, tmp_path):
        """A hotel that failed is done for this batch; re-attempting it inside
        the same run is the retry storm the design forbids."""
        j = Journal.open(tmp_path)
        j.append(HotelOutcome("failed", EXCEPTION, "NAVIGATION_TIMEOUT"), at="t")
        assert "failed" in j.completed_hotel_ids()

    def test_manifest_counts_add_up(self, tmp_path):
        j = Journal.open(tmp_path)
        j.append(HotelOutcome("a", CAPTURED, artifacts={"json_path": "a.json"}), at="t")
        j.append(HotelOutcome("b", EXCEPTION, "POLICY_NOT_FOUND"), at="t")
        j.append(HotelOutcome("c", EXCEPTION, "DUPLICATE_CAPTURE",
                              duplicate_of="a"), at="t")
        m = build_manifest(batch_id="b1", queue_size=3, journal=j)
        # confirmed_policy_absence is a SUBSET of exceptions, not a fourth
        # total: a hotel whose page says it takes no pets still produced no
        # capture. Counted separately so a batch's headline failure number
        # stops reading as N adapter defects.
        assert m["counts"] == {"queued": 3, "attempted": 3, "captured": 1,
                               "exceptions": 1, "duplicates": 1, "skipped": 0,
                               "confirmed_policy_absence": 0}
        assert m["duplicate_captures"][0]["duplicate_of"] == "a"

    def test_retry_recommendations_are_grouped(self, tmp_path):
        j = Journal.open(tmp_path)
        j.append(HotelOutcome("a", EXCEPTION, "NAVIGATION_TIMEOUT"), at="t")   # now
        j.append(HotelOutcome("b", EXCEPTION, "CAPTCHA_OR_CHALLENGE"), at="t")  # manual
        j.append(HotelOutcome("c", EXCEPTION, "SEARCH_URL"), at="t")            # never
        m = build_manifest(batch_id="b1", queue_size=3, journal=j)
        assert m["retry_recommendations"] == {
            "now": ["a"], "manual": ["b"], "never": ["c"]}

    def test_manifest_states_that_nothing_was_published(self, tmp_path):
        j = Journal.open(tmp_path)
        m = build_manifest(batch_id="b1", queue_size=0, journal=j)
        assert "attested" in m["note"] and "approved" in m["note"]

    def test_manifest_is_written_and_reloadable(self, tmp_path):
        j = Journal.open(tmp_path)
        m = build_manifest(batch_id="b1", queue_size=0, journal=j)
        path = write_manifest(m, tmp_path)
        assert json.loads(path.read_text("utf-8"))["batch_id"] == "b1"

    def test_archived_hashes_are_read_from_prior_corpora(self, tmp_path):
        name = "marriott-cmham.json"
        (tmp_path / name).write_text(json.dumps(load_fixture(name)), encoding="utf-8")
        found = archived_text_hashes(str(tmp_path))
        assert load_fixture(name)["text_sha256"] in found

    def test_unreadable_archive_files_are_skipped_not_fatal(self, tmp_path):
        (tmp_path / "broken.json").write_text("{not json", encoding="utf-8")
        assert archived_text_hashes(str(tmp_path)) == {}

    def test_a_missing_archive_directory_is_fine(self, tmp_path):
        assert archived_text_hashes(str(tmp_path / "absent")) == {}
