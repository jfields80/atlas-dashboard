# -*- coding: utf-8 -*-
"""PTF-INDIANAPOLIS-OFFICIAL-URL-RECOVERY-006.

Indianapolis holds 257 identities and 143 of them name no website, so no lane
can be pointed at them at any price. This work order asked whether they could be
routed from evidence already on disk. They cannot: zero net new routes, and the
tests below pin WHY, because "we looked and there is nothing" is only credible
if the run that says it can show what it read.

What the search did return is worth more than a URL would have been: a wrong
route sitting in the payable cohort, pointed at another brand's city-search
page, and a duplicate identity hiding behind a shared telephone number.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

PACKAGE_DIR = (Path(__file__).resolve().parents[2]
               / "launch_packages" / "pettripfinder")


def _load(name):
    return json.loads((PACKAGE_DIR / name).read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def report():
    return _load("indianapolis_in_url_recovery_report_006.json")


@pytest.fixture(scope="module")
def plan():
    return _load("indianapolis_in_recovery_cost_plan_006.json")


@pytest.fixture(scope="module")
def packet():
    return _load("indianapolis_in_recovery_founder_packet_006.json")


class TestNothingWasBoughtAndNothingMoved:

    def test_this_work_order_fetched_nothing(self, report):
        assert report["nothing_was_fetched"] is True
        assert report["usd_spent"] == 0.0
        assert report["network_calls"] == 0

    def test_the_promoted_authority_is_untouched(self, report):
        assert report["current"]["promoted_pet_friendly"] == 24
        assert report["current"]["verified_no_pets"] == 24
        assert report["current"]["census"] == 257


class TestTheUnroutableInventory:

    def test_there_are_143_of_them(self, report):
        assert report["phase_1_unroutable_inventory"]["unroutable_identities"] == 143

    def test_they_are_spread_across_every_family(self, report):
        fam = report["phase_1_unroutable_inventory"]["by_family"]
        assert fam["choice"] == 33
        assert fam["hilton"] == 23
        assert sum(fam.values()) == 143

    def test_every_row_states_a_street_city_and_postal_code(self, report):
        data = report["phase_1_unroutable_inventory"]["identifying_data"]
        assert data["with_street"] == 143
        assert data["with_city"] == 143
        assert data["with_postal_code"] == 143

    def test_almost_none_states_a_telephone_which_is_the_strong_key(self, report):
        assert report["phase_1_unroutable_inventory"]["identifying_data"][
            "with_telephone"] == 5

    def test_not_one_carries_a_property_code(self, report):
        """The reason no brand URL can be BUILT for them."""
        data = report["phase_1_unroutable_inventory"]["identifying_data"]
        assert data["with_a_known_property_code"] == 0
        assert report["phase_1_unroutable_inventory"][
            "deterministic_property_code_recovery_available"] is False


class TestZeroCostRoutingIsExhausted:

    def test_no_new_route_was_recovered(self, report):
        assert report["phase_2_zero_cost_routing"]["net_new_routes"] == 0

    def test_the_search_can_show_what_it_read(self, report):
        seen = report["phase_2_zero_cost_routing"]["evidence_consulted"]
        assert seen["discovery_cache_providers"] == ["OPENSTREETMAP"]
        assert seen["saved_acquisition_artifacts_scanned"] == 63
        assert seen["first_party_urls_found_in_those_artifacts"] == 69
        assert seen["prior_build_reports_read"] > 100

    def test_street_binding_added_nothing(self, report):
        assert report["phase_2_zero_cost_routing"]["street_binding_added"] == 0

    def test_the_one_binding_made_was_a_duplicate_not_a_route(self, report):
        p2 = report["phase_2_zero_cost_routing"]
        assert p2["duplicates_found_instead"] == 1
        dup = p2["duplicates"][0]
        assert dup["identity_key"] == "hampton inn indianapolis southwest plainfield"
        assert dup["collides_with"] == "hampton inn indianapolis sw plainfield"
        assert dup["binding"] == "PHONE"


class TestTheStreetRule:

    def test_it_is_shared_by_both_surfaces(self, report):
        p3 = report["phase_3_street_rule"]
        assert "policy_surface" in p3["implemented_in"]
        assert "marriott_surface" in p3["shared_with"]

    def test_it_freed_exactly_the_two_known_rows(self, report):
        assert report["phase_3_street_rule"]["rows_freed"] == [
            "courtyard by marriott indianapolis northwest",
            "days inn by wyndham plainfield"]

    def test_it_still_refuses_a_different_house_number(self, report):
        assert "a different house number" in \
            report["phase_3_street_rule"]["still_refused"]


class TestRoutingRerun:

    def test_a_wrong_route_was_found_and_dropped(self, report):
        p5 = report["phase_5_routing_rerun"]
        assert p5["dropped_wrong_route"] == 1
        bad = p5["dropped"][0]
        assert bad["identity_key"] == "comfort suites"
        assert "econo-lodge" in bad["url"]
        assert "shelbyville" in bad["url"]

    def test_the_cohort_moved_from_36_to_33(self, report):
        p5 = report["phase_5_routing_rerun"]
        assert p5["routing_before"] == 36
        assert p5["routing_after"] == 33
        assert p5["payable"] == 33

    def test_the_hyatt_pair_sharing_one_page_is_held_not_bought(self, report):
        """A dual-brand building is exactly where a shared page must not be
        resolved by the machine: keeping the wrong one publishes the
        neighbour's policy under this hotel's name."""
        p5 = report["phase_5_routing_rerun"]
        assert p5["dropped_shared_page"] == 2
        keys = sorted(x["identity_key"] for x in p5["shared_page_conflicts"])
        assert keys == ["hyatt house indianapolis downtown",
                        "hyatt place indianapolis downtown"]
        assert all(not x["kept_instead"] for x in p5["shared_page_conflicts"])
        assert all("hyatt-place-indianapolis-downtown" in x["why"]
                   for x in p5["shared_page_conflicts"])

    def test_the_two_freed_rows_are_not_smuggled_into_the_cohort(self, report):
        """A reader improvement is not, on its own, licence to re-buy a page
        that previously identity-mismatched. The ledger says so and it wins."""
        p5 = report["phase_5_routing_rerun"]
        assert p5["suppressed_by_paid_history"] == 2
        assert p5["suppressed_reasons"] == {"SUPPRESSED_ROUTING_REPAIR_REQUIRED": 2}
        assert p5["street_rule_rows_still_suppressed"] == [
            "courtyard by marriott indianapolis northwest",
            "days inn by wyndham plainfield"]
        assert "OPERATOR_OVERRIDE" in p5["why_the_freed_rows_are_still_suppressed"]

    def test_no_payable_row_is_a_duplicate_of_another(self, report):
        rows = report["phase_5_routing_rerun"]["rows"]
        urls = [r["source_url"].rstrip("/").lower() for r in rows]
        assert len(urls) == len(set(urls))


class TestTheCostPlanAndTheCeiling:

    def test_it_authorises_nothing(self, plan):
        assert plan["this_is_not_an_authorization"] is True
        assert plan["authorised_cap_usd_minor"] == 0

    def test_the_projection_is_bounded(self, plan):
        assert plan["cohort_size"] == 33
        assert plan["dollar_billed_properties"] == 33
        assert plan["credit_billed_properties"] == 0
        assert plan["expected_firecrawl_credits"] == 0.0
        assert plan["projection"]["worst_case_usd_minor"] == 693.0
        assert plan["safe_cap_usd_minor"] == 708

    def test_fifty_is_still_not_reachable_by_spending(self, plan):
        y = plan["yield_projection"]
        assert y["payable_cohort"] == 33
        assert y["expected_total_pet_friendly"] == 34
        assert y["still_needed"] == 16
        assert y["verdict"] == "NOT_REACHABLE_FROM_THE_CURRENT_PAYABLE_POOL"

    def test_it_names_the_only_lever_that_moves_the_number(self, plan):
        assert "143" in plan["yield_projection"]["what_would_change_it"]
        assert "discovery" in plan["yield_projection"]["what_would_change_it"]


class TestTheExceptionPacket:

    def test_nothing_is_auto_accepted(self, packet):
        assert packet["auto_accepted"] == 0
        assert packet["status"] == "EXCEPTIONS_ONLY"

    def test_it_carries_005s_exceptions_plus_006s_findings(self, packet):
        assert packet["exceptions"] == 9
        kinds = packet["by_kind"]
        assert kinds["DUPLICATE_OR_IDENTITY_CONFLICT"] == 6
        assert kinds["WRONG_ROUTE_IN_THE_CENSUS"] == 1

    def test_the_hyatt_dual_brand_finding_is_surfaced(self, packet):
        rows = [r for r in packet["rows"]
                if r["identity_key"] == "hyatt house indianapolis downtown"]
        assert len(rows) == 1
        assert "indzi" in rows[0]["evidence"]

    def test_it_publishes_nothing(self, packet):
        assert "publishes nothing" in packet["nothing_is_published_by_this_file"]
