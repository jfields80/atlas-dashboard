# -*- coding: utf-8 -*-
"""PTF-INDIANAPOLIS-PLACES-QUALIFICATION-008 -- what 25 paid lookups actually bought.

The experiment ran once, under a 25-request cap, and it will not be re-run:
the discovery ledger now suppresses every one of these rows. So these tests are
the durable record of what was measured, and of the two things that matter more
than the headline rate.

FIRST, THE CONTROLS HELD -- AND ONE OF THEM HELD THE HARD WAY. "aloft" is a bare
name, and Places returned the real Aloft Indianapolis Downtown with a genuine
Marriott property URL. The binder refused it anyway, because a bare brand name
is not equal to that hotel's name and there was no telephone to decide. A guard
that only refuses when the provider finds nothing is not a guard.

SECOND, STRICTNESS CAUGHT TWO WRONG HOTELS. Asked for a Cambria in Westfield,
Places offered a Hampton Inn. Asked for a Hampton Inn in Carmel, it offered the
Homewood Suites -- the exact dual-brand confusion the ledger doctrine is written
against. Both were refused. Any future loosening of the name rule must keep
refusing them, which is why they are pinned here by name.
"""
from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.pettripfinder.acquisition import discovery_attempt_ledger as DAL
from scripts.pettripfinder.acquisition import market_routing as MR

PACKAGE_DIR = (Path(__file__).resolve().parents[2]
               / "launch_packages" / "pettripfinder")


def _load(name):
    return json.loads((PACKAGE_DIR / name).read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def run():
    return _load("indianapolis_in_places_qualification_008.json")


@pytest.fixture(scope="module")
def ledger():
    return DAL.load(PACKAGE_DIR / "ptf_discovery_attempt_ledger_001.json")


class TestTheAuthorisedCapHeld:

    def test_exactly_twenty_five_requests_were_made(self, run):
        assert run["requests_made"] == 25
        assert run["authorised_request_cap"] == 25
        assert run["cap_held"] is True

    def test_the_run_was_not_aborted(self, run):
        assert run["aborted"] == ""

    def test_the_sample_was_not_substituted(self, run):
        executed = [r for r in run["rows"] if r.get("requests_made")]
        groups = {}
        for row in executed:
            groups[row["expected_binding_method"]] = \
                groups.get(row["expected_binding_method"], 0) + 1
        assert groups == {"PHONE": 5, "NAME_AND_POSTAL_CODE": 18,
                          "EXPECTED_TO_FAIL": 2}


class TestTheFailureControlsHeld:
    """If either had bound, the experiment stops and Places does not qualify."""

    def test_neither_control_bound(self, run):
        assert run["totals"]["EXPECTED_TO_FAIL"]["bound"] == 0
        assert run["totals"]["EXPECTED_TO_FAIL"]["attempted"] == 2

    def test_aloft_was_refused_even_though_places_found_the_real_hotel(self, run):
        """The meaningful control. Places returned a genuine Marriott property
        page for Aloft Indianapolis Downtown and the rule still said no."""
        aloft = [r for r in run["rows"] if r["identity_key"] == "aloft"][0]
        assert aloft["bound"] is False
        assert aloft["places_returned"] == 1
        returned = aloft["returned"][0]
        assert "Aloft" in returned["name"]
        assert returned["website_uri"], "Places did return a URL; the rule refused it"
        assert MR.classify_url_shape(
            MR.normalize_source_url(returned["website_uri"])) == "PROPERTY_PAGE"

    def test_ashley_motel_had_no_website_to_bind(self, run):
        ashley = [r for r in run["rows"] if r["identity_key"] == "ashley motel"][0]
        assert ashley["bound"] is False
        assert ashley["bind_state"] == DAL.BIND_NO_WEBSITE


class TestTheMeasuredRates:

    def test_overall(self, run):
        assert run["totals"]["overall"] == {"attempted": 25, "bound": 9,
                                            "rate": 0.36}

    def test_the_strong_key_never_missed(self, run):
        assert run["totals"]["PHONE"] == {"attempted": 5, "bound": 5, "rate": 1.0}

    def test_the_untested_key_is_where_it_falls_down(self, run):
        stat = run["totals"]["NAME_AND_POSTAL_CODE"]
        assert stat["attempted"] == 18 and stat["bound"] == 4
        assert stat["rate"] == pytest.approx(0.2222, abs=1e-4)


class TestWhatWasRecovered:

    def test_nine_official_urls_and_all_of_them_are_property_pages(self, run):
        recovered = run["official_property_urls_recovered"]
        assert len(recovered) == 9
        for entry in recovered:
            shape = MR.classify_url_shape(MR.normalize_source_url(entry["url"]))
            assert shape in MR.ROUTABLE_SHAPES, entry

    def test_nine_identities_became_routable(self, run):
        assert run["identities_made_routable"] == 9

    def test_no_two_rows_bound_to_one_place(self, run):
        assert run["place_id_collisions"] == {}

    def test_no_bound_row_is_missing_its_evidence(self, run):
        for row in run["rows"]:
            if not row.get("bound"):
                continue
            assert row["place_id"] and row["website_uri"]
            assert row["returned_business_name"]
            assert row["bind_method"] in ("PHONE", "NAME_AND_POSTAL_CODE")


class TestStrictnessCaughtTwoWrongHotels:
    """The half of the result that justifies the rule, and the regression that
    any future loosening must not break."""

    @pytest.mark.parametrize("identity_key,wrong_brand", [
        ("cambria hotel westfield indianapolis north", "Hampton Inn"),
        ("hampton inn and suites indianapolis carmel", "Homewood Suites"),
    ])
    def test_a_different_hotel_was_offered_and_refused(self, run, identity_key,
                                                       wrong_brand):
        row = [r for r in run["rows"] if r["identity_key"] == identity_key][0]
        assert row["bound"] is False
        offered = " ".join(x["name"] for x in row["returned"])
        assert wrong_brand in offered
        assert row["bind_state"] == DAL.BIND_NO_SANCTIONED_KEY


class TestTheLedgerRecordedItAllAndWillNotPayTwice:
    """Scoped to THIS run's rows. The ledger is cross-run and has since grown --
    PTF-INDIANAPOLIS-PLACES-BROADER-RECOVERY-010 added the other 118 -- so a
    whole-ledger total would pin a number that is supposed to move."""

    @staticmethod
    def _this_run(ledger):
        return [a for a in ledger["attempts"]
                if a["run_id"] == "indianapolis-in-places-008"]

    def test_twenty_five_rows_were_written(self, run, ledger):
        assert run["ledger_rows_written"] == 25
        assert len(self._this_run(ledger)) == 25

    def test_the_recorded_request_count_matches_what_was_spent(self, ledger):
        assert sum(a["paid_requests"] for a in self._this_run(ledger)) == 25

    def test_every_bound_row_kept_its_place_id_and_url(self, ledger):
        bound = [a for a in self._this_run(ledger)
                 if a["bind_state"] == DAL.BIND_BOUND]
        assert len(bound) == 9
        assert all(a["place_id"] and a["website_uri"] for a in bound)

    def test_re_running_the_same_sample_now_costs_nothing(self, run, ledger):
        """The whole point of the discovery ledger, proved on real spend rather
        than on a fixture."""
        rows = []
        for row in run["rows"]:
            signals = row["binding_signals"]
            rows.append({"identity_key": row["identity_key"],
                         "canonical_name": row["canonical_name"],
                         "street": row["query"].split(", ")[1],
                         "city": "Indianapolis", "state": "IN",
                         "postal_code": signals["census_postal"],
                         "telephone": signals["census_phone"]})
        payable, suppressed = DAL.suppress(
            rows, ledger, provider="GOOGLE_PLACES", method="searchText",
            field_mask=tuple(_load("indianapolis_in_discovery_replay_007.json")
                             ["field_mask"]))
        assert payable == []
        assert len(suppressed) == 25

    def test_a_failed_lookup_is_remembered_as_a_finding(self, ledger):
        failed = [a for a in self._this_run(ledger)
                  if a["bind_state"] in DAL.ANSWERED_NEGATIVE_STATES]
        assert len(failed) == 16
        assert all(a["answered"] is False for a in failed)
