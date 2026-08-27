# -*- coding: utf-8 -*-
"""PTF-INDIANAPOLIS-PLACES-NAME-NORMALIZATION-009 -- what the replay measured.

The same 25 paid Places responses, put through the old binder and the new one.
No provider was called: every payload was bought by 008 and the discovery ledger
suppresses all 25 from ever being bought again.

The improvement is worth having, but the four rows that must STAY unbound are
what make it safe to have. Two are the committed controls; two are wrong hotels
Google actually offered.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

PACKAGE_DIR = (Path(__file__).resolve().parents[2]
               / "launch_packages" / "pettripfinder")


@pytest.fixture(scope="module")
def replay():
    return json.loads(
        (PACKAGE_DIR / "indianapolis_in_name_normalization_009.json")
        .read_text(encoding="utf-8"))


class TestNothingWasBought:

    def test_no_provider_was_called(self, replay):
        assert replay["provider_calls"] == 0
        assert replay["usd_spent"] == 0.0

    def test_it_replays_the_already_paid_run(self, replay):
        assert replay["replayed_from"] == \
            "indianapolis_in_places_qualification_008.json"


class TestTheMeasuredImprovement:

    def test_overall_went_from_nine_to_thirteen(self, replay):
        overall = replay["totals"]["overall"]
        assert overall == {"attempted": 25, "old": 9, "new": 13}

    def test_name_and_postal_doubled(self, replay):
        stat = replay["totals"]["NAME_AND_POSTAL_CODE"]
        assert stat == {"attempted": 18, "old": 4, "new": 8}

    def test_the_phone_key_is_untouched(self, replay):
        assert replay["totals"]["PHONE"] == {"attempted": 5, "old": 5, "new": 5}

    def test_no_binding_was_lost(self, replay):
        assert replay["bindings_lost"] == []

    def test_four_rows_were_newly_accepted_and_each_names_its_rule(self, replay):
        newly = replay["newly_accepted"]
        assert len(newly) == 4
        for row in newly:
            assert row["rule"], row["identity_key"]
            assert row["census"] == row["places"], row["identity_key"]


class TestTheControlsAndTheWrongHotelsHeld:
    """If any of these four bind, the rule is too loose and the 118 must not run."""

    def test_the_two_committed_controls_are_still_unbound(self, replay):
        assert replay["totals"]["EXPECTED_TO_FAIL"] == {
            "attempted": 2, "old": 0, "new": 0}

    def test_no_protected_row_bound(self, replay):
        assert replay["controls"]["protected_bound_after"] == []

    def test_all_four_protected_rows_were_actually_checked(self, replay):
        assert set(replay["controls"]["protected_rows"]) == {
            "aloft", "ashley motel",
            "cambria hotel westfield indianapolis north",
            "hampton inn and suites indianapolis carmel"}

    def test_the_best_western_landmark_case_is_watched_and_held(self, replay):
        """Same brand, same city, same compass word, different building."""
        assert replay["controls"]["watched_rows"] == [
            "best western plus indianapolis north at broad ripple"]
        assert replay["controls"]["watched_bound_after"] == []

    def test_no_false_or_ambiguous_binding_was_introduced(self, replay):
        assert replay["false_or_ambiguous_bindings"] == []


class TestTheRefusalsThatAreNotAboutNames:
    """Two rows now have identical names and still do not bind. Both refusals
    are correct, and neither is a name-rule problem -- which is why the rule was
    not widened further to catch them."""

    def test_an_ihg_redirect_url_is_not_a_property_page(self, replay):
        row = [r for r in replay["rows"]
               if r["identity_key"] == "candlewood suites indianapolis east"][0]
        assert row["new_normalized_census"] == row["new_normalized_places"]
        assert row["new_decision"] == "UNBOUND"
        assert "distinctive word" in row["why_unbound"]

    def test_a_postal_disagreement_still_refuses(self, replay):
        row = [r for r in replay["rows"]
               if r["identity_key"]
               == "country inn and suites indianapolis airport south"][0]
        assert row["new_normalized_census"] == row["new_normalized_places"]
        assert row["new_decision"] == "UNBOUND"


class TestTheProjectionAndTheDecision:

    def test_the_projection_uses_only_the_name_and_postal_rate(self, replay):
        projection = replay["projection_for_the_remaining_118"]
        assert projection["new_name_and_postal_rate"] == pytest.approx(0.4444,
                                                                      abs=1e-4)
        assert projection["remaining"] == 118
        assert projection["projected_requests"] == 118
        assert projection["projected_urls"] == 52

    def test_it_says_why_the_phone_rate_cannot_be_used(self, replay):
        basis = replay["projection_for_the_remaining_118"]["basis"]
        assert "none remain" in basis

    def test_the_decision_is_qualify(self, replay):
        qualification = replay["qualification"]
        assert qualification["controls_held"] is True
        assert qualification["wrong_hotels_held"] is True
        assert qualification["no_binding_lost"] is True
        assert qualification["name_and_postal_improved"] is True
        assert qualification["decision"] == "QUALIFY_REMAINING_118"


class TestTheRuleIsDocumentedAsNarrow:

    def test_it_declares_no_fuzzy_matching(self, replay):
        assert "no edit distance" in replay["rules"]["no_fuzzy_matching"]

    def test_it_lists_what_it_never_removes(self, replay):
        never = replay["rules"]["never_removed"]
        for token in ("airport", "downtown", "northwest", "inn", "suites"):
            assert token in never

    def test_it_is_opt_in(self, replay):
        assert "default OFF" in replay["rules"]["opt_in"]
