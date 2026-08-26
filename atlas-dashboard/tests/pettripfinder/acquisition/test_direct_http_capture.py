"""PTF-ST-LOUIS-MARKET-001 -- the free lane, and the one thing it must not do.

``direct_http`` is the provider slot the router reserved and never built. The
danger of a free lane is not that it fails; it is that it fails QUIETLY, in a
way that reads as a fact about the hotel.

Wyndham is the case in point. Its property page serves 285 KB of Handlebars
whose policy region is literally ``Pet Policy {{pets}}``. The locator finds
nothing there -- correctly -- and an unguarded lane closes twenty-six St. Louis
properties as POLICY_NOT_FOUND, which asserts that twenty-six hotels state
nothing about pets. They state plenty; we fetched the template.
"""

from __future__ import annotations

import pytest

from scripts.pettripfinder.acquisition import direct_http_capture as DH
from scripts.pettripfinder.brightdata import outcomes as O


class TestTemplateDetection:
    def test_a_placeholder_beside_the_policy_is_an_unrendered_page(self):
        html = ("<div>Hotel Policies</div><div>Check In {{checkInTime}}</div>"
                "<div>Pet Policy {{pets}}</div>")
        assert DH.policy_region_is_a_template(html)

    def test_a_rendered_policy_is_not_a_template(self):
        html = "<div>Pet Policy</div><div>Pets are welcome, $25 per night.</div>"
        assert DH.policy_region_is_a_template(html) == ""

    def test_a_placeholder_far_from_any_policy_word_is_ignored(self):
        """A page may carry an unrendered widget and still have rendered its
        policy perfectly. Only a token standing WHERE the policy belongs counts."""
        html = "<span>{{cartCount}}</span>" + ("<p>lorem ipsum</p>" * 40)
        assert DH.policy_region_is_a_template(html) == ""

    def test_an_empty_document_is_not_a_template(self):
        assert DH.policy_region_is_a_template("") == ""
        assert DH.policy_region_is_a_template(None) == ""


class TestOutcomeMapping:
    @pytest.mark.parametrize("status,expected", [
        (403, O.ACCESS_DENIED),
        (401, O.ACCESS_DENIED),
        (429, O.ACCESS_DENIED),
        (451, O.ACCESS_DENIED),
        (404, O.NAVIGATION_FAILED),
        (500, O.NAVIGATION_FAILED),
        ("TRANSPORT", O.NAVIGATION_FAILED),
    ])
    def test_a_refusal_and_a_transport_failure_are_different_outcomes(
            self, status, expected):
        """One escalates to a different provider; the other is worth retrying
        on the same one. Collapsing them wastes attempts or gives up early."""
        assert DH._outcome_for_status(status) == expected

    def test_a_refusal_is_terminal_for_this_lane(self):
        """The shared ladder retries ACCESS_DENIED because a rotating vendor
        zone may not be refused twice. This lane has one exit IP and one header
        set, so the second 403 is guaranteed."""
        assert O.worth_retrying(O.ACCESS_DENIED), "shared rule unchanged"
        assert not DH.worth_retrying(O.ACCESS_DENIED)

    def test_a_navigation_failure_is_worth_one_more_try(self):
        assert DH.worth_retrying(O.NAVIGATION_FAILED)

    def test_the_lane_rule_only_ever_narrows_the_shared_one(self):
        for outcome in O.OUTCOMES:
            if DH.worth_retrying(outcome):
                assert O.worth_retrying(outcome), outcome


class TestLaneDeclaration:
    def test_the_lane_claims_the_reserved_provider_id(self):
        from scripts.pettripfinder.acquisition import providers as P
        assert DH.PROVIDER_ID == P.DIRECT_HTTP

    def test_the_lane_does_not_register_itself_as_available(self):
        """A route is added by a benchmark, never by an opinion. Building the
        lane must not silently put it in anyone's ladder."""
        from scripts.pettripfinder.acquisition import providers as P
        assert DH.PROVIDER_ID not in P.available()

    def test_no_route_in_the_registry_points_at_it_yet(self):
        from scripts.pettripfinder.acquisition import registry as R
        doc = R.load()
        serialised = str(doc)
        assert DH.PROVIDER_ID not in serialised


class TestBodyLimits:
    def test_the_body_cap_is_above_the_largest_measured_page(self):
        """960 KB was the largest hotel page in the St. Louis run."""
        assert DH.MAX_BODY_BYTES > 1_000_000
