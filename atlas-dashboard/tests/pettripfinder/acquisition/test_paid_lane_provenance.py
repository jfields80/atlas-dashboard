"""PTF-ST-LOUIS-PAID-ACQUISITION-002 -- a record must name the lane that made it.

Every module downstream of acquisition was written when a market had exactly one
lane, so each of them ASSERTED that lane rather than reading it. That was true
and is no longer: a paid pass reads one property through Firecrawl with the
Choice reader and the next through a managed browser with the Marriott reader.

An asserted provenance on a record whose whole value is its provenance is the
worst kind of wrong -- it is wrong quietly, in the field a reviewer trusts most.
"""

from __future__ import annotations

from scripts.pettripfinder import market_closure_cli as CC
from scripts.pettripfinder.acquisition import market_observation_store as MOS
from scripts.pettripfinder.acquisition import market_routing as MR


class TestCaptureMethod:
    def test_a_managed_browser_is_recorded_as_browser_assisted(self):
        assert MOS._capture_method({"provider": "brightdata_browser"}) == \
            "browser_assisted"

    def test_a_fetch_lane_is_recorded_as_a_deterministic_fetch(self):
        for provider in ("firecrawl", "brightdata_web_unlocker", "direct_http"):
            assert MOS._capture_method({"provider": provider}) == \
                "deterministic_fetch"

    def test_a_row_from_before_this_change_still_reads_as_a_fetch(self):
        # Four markets' committed rows carry no provider at all. They were all
        # captured by a fetch lane, so the default must not silently promote
        # them to browser_assisted.
        assert MOS._capture_method({}) == "deterministic_fetch"

    def test_both_values_are_in_the_observation_contract(self):
        from scripts.pettripfinder.policy import policy_observation as PO
        assert "browser_assisted" in PO.CAPTURE_METHODS
        assert "deterministic_fetch" in PO.CAPTURE_METHODS


class TestPartitionNamesTheLane:
    def _routing(self, state=MR.ROUTED):
        return {"routing_state": state, "why": "because"}

    def test_a_refusal_names_the_lane_that_was_refused(self):
        _state, why = CC._partition_state(
            routing=self._routing(),
            capture={"outcome": "ACCESS_DENIED", "detail": "403",
                     "provider": "brightdata_browser"},
            observation=None)
        assert "brightdata_browser was refused" in why

    def test_a_capture_with_no_provider_falls_back_to_the_old_wording(self):
        _state, why = CC._partition_state(
            routing=self._routing(),
            capture={"outcome": "ACCESS_DENIED", "detail": "403"},
            observation=None)
        assert "the free lane was refused" in why

    def test_silence_is_attributed_to_the_lane_that_read_the_page(self):
        state, why = CC._partition_state(
            routing=self._routing(),
            capture={"outcome": "POLICY_NOT_FOUND", "provider": "firecrawl"},
            observation=None)
        assert "as read by firecrawl" in why
        assert CC.closure_for(state, {"outcome": "POLICY_NOT_FOUND"})

    def test_a_property_nobody_fetched_no_longer_blames_a_missing_credential(self):
        # True for the first St. Louis pass and false the moment a credential
        # exists: after 002 an unfetched routed property is one the cap did not
        # reach, and the partition must not assert a cause it cannot know.
        _state, why = CC._partition_state(routing=self._routing(),
                                          capture=None, observation=None)
        assert "credential" not in why
        assert "never attempted" in why

    def test_silence_still_closes_as_a_statement_about_the_hotel(self):
        state, _why = CC._partition_state(
            routing=self._routing(),
            capture={"outcome": "POLICY_NOT_FOUND", "provider": "firecrawl"},
            observation=None)
        capture = {"outcome": "POLICY_NOT_FOUND"}
        assert CC.closure_for(state, capture) == "POLICY_NOT_FOUND"

    def test_an_unfetched_property_closes_as_a_statement_about_us(self):
        state, _why = CC._partition_state(routing=self._routing(),
                                          capture=None, observation=None)
        assert CC.closure_for(state, None) == "ACCESS_UNRESOLVED"
