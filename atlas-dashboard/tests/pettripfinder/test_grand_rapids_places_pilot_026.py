# -*- coding: utf-8 -*-
"""PTF-GRAND-RAPIDS-HOLLAND-PLACES-PILOT-026.

This is the first Grand Rapids order that spends money, and the cheapest place
to find out that the binder is wrong is here, before the first request. So the
binding rules are exercised offline against synthetic places -- the right
hotel, a sibling sub-brand, a booking aggregator, a brand index, a place with
no website, no results at all -- and only then does the run go live.

THREE PROTECTIONS ARE LOAD-BEARING AND EACH HAS ITS OWN TEST.

``names_may_share_a_url`` (Grand Rapids' own, from CHOICE-ROUTING-REPAIR-007)
stops a Comfort Inn taking a Comfort Suites page. ``presentation_key``
(Indianapolis 009 + 011) makes "Fairfield by Marriott Inn & Suites" and
"Fairfield Inn & Suites" one name. They answer DIFFERENT questions and this
pass is the first to run both, so the tests pin that neither swallowed the
other: the presentation key must not make a Comfort Inn into a Comfort Suites,
and it must not erase airport, downtown or a compass word.

THE COHORT IS EVIDENCE, NOT A CONVENIENCE. It is committed before the run and
the runner refuses any other length, so the tests check the exclusions cite a
prior ruling, that every family in the pool is represented, and that the
evidence mix matches the pool it was drawn from. A sample that over-weighted
telephone rows would have measured a rate this market cannot repeat.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.pettripfinder.acquisition import discovery_attempt_ledger as DAL  # noqa: E402
from scripts.pettripfinder.discovery import census_url_recovery as URC         # noqa: E402
from scripts.pettripfinder import grand_rapids_holland_places_cohort_026 as COHORT  # noqa: E402
from scripts.pettripfinder import grand_rapids_holland_places_pilot_026 as PILOT    # noqa: E402

LP = REPO_ROOT / "launch_packages" / "pettripfinder"
COHORT_DOC = LP / "grand_rapids_holland_mi_places_pilot_cohort_026.json"
REPORT_DOC = LP / "grand_rapids_holland_mi_places_pilot_026.json"


def _load(path):
    assert path.is_file(), "%s is missing" % path.name
    return json.loads(path.read_text(encoding="utf-8-sig"))


@pytest.fixture(scope="module")
def cohort():
    return _load(COHORT_DOC)


@pytest.fixture(scope="module")
def report():
    return _load(REPORT_DOC)


class _Place(object):
    """The fields the binder reads off a Places record, and nothing else."""

    def __init__(self, place_id, name, address, postal, phone, website):
        self.provider_record_id = place_id
        self.name = name
        self.address_line = address
        self.postal_code = postal
        self.phone = phone
        self.website_url = website
        self.business_status = "OPERATIONAL"


CENSUS_ROW = {
    "identity_key": "comfort inn airport",
    "canonical_name": "Comfort Inn Airport",
    "address": "4155 28th Street", "street": "4155 28th Street",
    "city": "Grand Rapids", "state": "MI", "postal_code": "49512",
    "phone": "6169425511", "telephone": "6169425511", "official_url": "",
}


# --------------------------------------------------------------------------- #
# The binder, proved offline before a cent is spent
# --------------------------------------------------------------------------- #

def test_the_right_hotel_binds_on_its_own_telephone():
    place = _Place("A", "Comfort Inn Airport", "4155 28th St SE, Grand Rapids",
                   "49512", "6169425511",
                   "https://www.choicehotels.com/michigan/grand-rapids/"
                   "comfort-inn-hotels/mi123")
    observation, binding, rejections, matched = PILOT.bind_one(CENSUS_ROW, [place])
    assert observation is not None
    assert binding == URC.BIND_PHONE
    assert matched is place
    assert not rejections


def test_a_sibling_sub_brand_is_refused_even_on_a_shared_switchboard():
    """The defect CHOICE-ROUTING-REPAIR-007 fixed, and the reason
    ``names_may_share_a_url`` still runs with the presentation key switched on.

    Two Choice brands share a building and a switchboard in Grandville. They do
    not share a pet policy.
    """
    place = _Place("B", "Comfort Suites Grandville - Grand Rapids SW",
                   "4520 Kenowa Ave SW", "49512", "6169425511",
                   "https://www.choicehotels.com/michigan/grandville/"
                   "comfort-suites-hotels/mi169")
    observation, binding, rejections, _ = PILOT.bind_one(CENSUS_ROW, [place])
    assert observation is None and binding == ""
    assert rejections, "a refusal that is not recorded cannot be reviewed"
    assert "one may not lend the other its URL" in rejections[0]["why"]


def test_a_booking_aggregator_is_refused():
    place = _Place("C", "Comfort Inn Airport", "4155 28th St SE", "49512",
                   "6169425511", "https://www.booking.com/hotel/us/comfort-inn.html")
    observation, _, rejections, _ = PILOT.bind_one(CENSUS_ROW, [place])
    assert observation is None
    assert any("no lane can fetch" in r["why"] for r in rejections)


def test_a_brand_index_page_is_refused_because_it_names_no_property():
    place = _Place("D", "Comfort Inn Airport", "4155 28th St SE", "49512",
                   "6169425511", "https://www.choicehotels.com/")
    observation, _, rejections, _ = PILOT.bind_one(CENSUS_ROW, [place])
    assert observation is None
    assert rejections


def test_a_place_with_no_website_binds_nothing_and_says_which():
    place = _Place("E", "Comfort Inn Airport", "4155 28th St SE", "49512",
                   "6169425511", "")
    observation, binding, rejections, _ = PILOT.bind_one(CENSUS_ROW, [place])
    assert observation is None
    assert PILOT.bind_state(observation, binding, [place], rejections) == \
        DAL.BIND_NO_WEBSITE


def test_no_result_at_all_is_its_own_state():
    observation, binding, rejections, _ = PILOT.bind_one(CENSUS_ROW, [])
    assert PILOT.bind_state(observation, binding, [], rejections) == \
        DAL.BIND_NO_RESULT


def test_a_wrong_hotel_at_the_right_postal_does_not_bind():
    """A different building in the same postal code, no shared telephone. The
    name is the only thing left and it does not match."""
    place = _Place("F", "Hampton Inn Grand Rapids Airport", "4981 28th St SE",
                   "49512", "6169499222",
                   "https://www.hilton.com/en/hotels/grrapqx-hampton-grand-rapids")
    observation, _, _, _ = PILOT.bind_one(CENSUS_ROW, [place])
    assert observation is None


# --------------------------------------------------------------------------- #
# The two hardenings, and the line between them
# --------------------------------------------------------------------------- #

def test_the_presentation_key_makes_one_building_one_name():
    key = lambda n: URC.presentation_key(n, state_code="MI", unordered=True)  # noqa: E731
    assert key("Fairfield by Marriott Inn & Suites Grand Rapids Wyoming") == \
        key("Fairfield Inn & Suites Grand Rapids Wyoming")
    assert key("Candlewood Suites Grand Rapids, an IHG Hotel") == \
        key("Candlewood Suites Grand Rapids")
    assert key("Extended Stay America Suites Grand Rapids Kentwood") == \
        key("Extended Stay America Grand Rapids Kentwood")


@pytest.mark.parametrize("left,right", [
    ("Comfort Inn Holland", "Comfort Suites Holland"),
    ("Courtyard Grand Rapids Airport", "Courtyard Grand Rapids Downtown"),
    ("Holiday Inn Grand Rapids North", "Holiday Inn Grand Rapids South"),
    ("Staybridge Suites Holland", "Staybridge Suites Grand Rapids"),
])
def test_the_presentation_key_never_merges_two_buildings(left, right):
    """Airport, downtown, the compass words and every locality survive it.
    These are the words that tell one hotel from another."""
    key = lambda n: URC.presentation_key(n, state_code="MI", unordered=True)  # noqa: E731
    assert key(left) != key(right)


def test_the_dual_brand_refusal_survived_the_merge():
    """Both hardenings now live in one module. Neither replaced the other."""
    assert hasattr(URC, "names_may_share_a_url")
    assert hasattr(URC, "presentation_key")
    ok, _ = URC.names_may_share_a_url(
        "Comfort Inn", "Comfort Suites Grandville Grand Rapids SW")
    assert ok is False
    ok, _ = URC.names_may_share_a_url(
        "Rodeway Inn", "Rodeway Inn Grandville Grand Rapids")
    assert ok is True


def test_the_wider_comparison_is_opt_in():
    """Default OFF: every market that recovered its URLs under the old rule
    recovers exactly the same ones today."""
    row = dict(CENSUS_ROW, phone="", canonical_name="Fairfield Inn & Suites")
    place = _Place("G", "Fairfield by Marriott Inn & Suites",
                   "4155 28th St SE", "49512", "",
                   "https://www.marriott.com/en-us/hotels/grrfi-fairfield-inn")
    sightings = PILOT.observations([place])
    assert URC.bind(row, sightings)[0] is None
    assert URC.bind(row, sightings, presentation_variants=True)[0] is not None


# --------------------------------------------------------------------------- #
# The cohort was chosen before the money
# --------------------------------------------------------------------------- #

def test_the_cohort_is_exactly_the_authorised_size(cohort):
    assert cohort["sample"]["size"] == PILOT.MAX_REQUESTS == 20
    assert cohort["sample"]["provider_requests_if_authorised"] == 20
    assert cohort["provider_calls"] == 0 and cohort["usd_spent"] == 0.0
    assert cohort["nothing_was_fetched"] is True


def test_the_runner_refuses_a_cohort_that_is_not_the_authorised_one(tmp_path,
                                                                   monkeypatch):
    document = _load(COHORT_DOC)
    document["sample"]["rows"] = document["sample"]["rows"][:5]
    short = tmp_path / "short.json"
    short.write_text(json.dumps(document), encoding="utf-8")
    monkeypatch.setattr(PILOT, "COHORT_PATH", short)
    with pytest.raises(SystemExit) as raised:
        PILOT.load_cohort()
    assert "not the authorised one" in str(raised.value)


def test_every_family_in_the_pool_is_asked_about(cohort):
    """A family the pilot never asks about is a family the projection would be
    guessing about, and two of this market's nine hold one hotel each."""
    assert cohort["sample"]["families_covered"] == \
        cohort["sample"]["families_in_the_pool"] == 9


def test_the_evidence_mix_matches_the_pool_it_was_drawn_from(cohort):
    """Telephone is the strongest key the binder holds. Over-weighting phone
    rows would measure a rate this market cannot repeat."""
    block = cohort["representativeness"]["evidence"]
    pool_share = (block["pool"]["TELEPHONE_STATED"]
                  / sum(block["pool"].values()))
    cohort_share = (block["cohort"]["TELEPHONE_STATED"]
                    / sum(block["cohort"].values()))
    assert abs(pool_share - cohort_share) < 0.05


def test_every_municipality_in_the_corridor_is_represented(cohort):
    block = cohort["representativeness"]["municipality"]
    assert set(block["cohort"]) == set(block["pool"])
    assert len(block["cohort"]) == 7


def test_the_hard_names_were_not_left_out(cohort):
    """17 of the 76 carry a name that is a strict token subset of another
    property's in this market -- the rows a provider is most likely to answer
    with the wrong building. Cherry-picking them out would have produced a
    flattering rate and no false-binding evidence at all."""
    block = cohort["representativeness"]["name_shape"]
    assert block["cohort"]["UNDERSPECIFIED_IN_MARKET"] >= 3
    at_risk = [r for r in cohort["sample"]["rows"]
               if r["expected_binding_method"] == "NAME_AND_POSTAL_CODE_AT_RISK"]
    assert at_risk


def test_every_exclusion_cites_a_ruling_that_already_existed(cohort):
    rules = {row["rule"] for row in cohort["excluded_rows"]}
    assert rules <= {COHORT.EXCLUDED_IDENTITY_HOLD,
                     COHORT.EXCLUDED_DEDUP_SAFE_MERGE,
                     COHORT.EXCLUDED_ALREADY_LOOKED_UP}
    for row in cohort["excluded_rows"]:
        assert row["why"]
    keys = {row["identity_key"] for row in cohort["excluded_rows"]}
    # Both halves of both 019 holds, and the third same-switchboard pair.
    assert "comfort inn" in keys
    assert "sleep inn and suites" in keys and "spark by hilton grand rapids" in keys
    assert "budgetel inn and suites hotel" in keys


def test_a_deferred_sibling_rules_nothing_about_identity(cohort):
    """The doorway guard is a SAMPLING rule. The dedup gate has ruled several
    of these pairs DISTINCT_PROPERTIES and this module does not overrule it."""
    for row in cohort["deferred_rows"]:
        assert row["rule"] == COHORT.DEFERRED_SHARED_DOORWAY
        assert "rules nothing about whether the two are one hotel" in row["why"]
        assert row["sampled_instead"]


def test_the_doorway_keeper_is_the_better_evidenced_half(cohort):
    """Alphabetical order once kept the bare "MainStay Suites" over the
    "MainStay Suites Grand Rapids" that states a telephone."""
    deferred = {row["identity_key"]: row["sampled_instead"]
                for row in cohort["deferred_rows"]}
    assert deferred.get("mainstay suites") == "mainstay suites grand rapids"
    assert deferred.get("cityflatshotel") == "cityflatshotel grand rapids"


def test_the_cohort_is_deterministic():
    """Re-running the builder on the same census produces the same twenty rows
    in the same order, which is what makes it auditable before the run."""
    again = COHORT.build()
    committed = _load(COHORT_DOC)
    assert [r["identity_key"] for r in again["sample"]["rows"]] == \
           [r["identity_key"] for r in committed["sample"]["rows"]]


# --------------------------------------------------------------------------- #
# The run
# --------------------------------------------------------------------------- #

def test_the_cap_held(report):
    assert report["authorised_request_cap"] == 20
    assert report["requests_made"] <= 20
    assert report["cap_held"] is True
    assert report["live"] is True


def test_every_executed_attempt_is_in_the_cross_run_ledger(report):
    ledger = _load(LP / "ptf_discovery_attempt_ledger_001.json")
    ours = [a for a in ledger["attempts"] if a["work_order"] == PILOT.WORK_ORDER]
    assert len(ours) == report["ledger_rows_written"] == report["requests_made"]
    keys = {a["identity_key"] for a in ours}
    executed = {r["identity_key"] for r in report["rows"]
                if r.get("requests_made")}
    assert keys == executed, (
        "a lookup that found nothing is still a lookup this project has paid "
        "for; repeating it buys the same nothing twice")


def test_the_pilot_will_not_run_twice(report):
    """Every row it executed is now suppressed by the ledger, so a re-run buys
    nothing."""
    ledger = DAL.load(LP / "ptf_discovery_attempt_ledger_001.json")
    index = DAL.DiscoveryIndex(ledger)
    cohort = _load(COHORT_DOC)
    executed = {r["identity_key"] for r in report["rows"]
                if r.get("requests_made")}
    for entry in cohort["sample"]["rows"]:
        if entry["identity_key"] not in executed:
            continue
        decision = DAL.decide(PILOT.census_row(entry), index,
                              provider=cohort["provider"],
                              method=cohort["discovery_method"],
                              field_mask=tuple(cohort["field_mask"]))
        assert decision["decision"] not in DAL.ALLOWED_DECISIONS


def test_no_dollar_figure_was_invented(report):
    billing = report["billing"]
    assert billing["usd_observable"] is False
    assert billing["measured_cost_usd"] is None
    assert billing["priced_in"] == "REQUESTS"
    assert "no USD rate" in billing["why"]
    for row in report["rows"]:
        if row.get("requests_made"):
            assert row["measured_cost_usd"] is None


def test_no_other_provider_was_touched(report):
    joined = " ".join(report["nothing_else_was_run"]).lower()
    for provider in ("bright data", "firecrawl", "policy acquisition",
                     "premium-domain"):
        assert provider in joined


def test_every_recovered_url_is_a_routable_property_page(report):
    from scripts.pettripfinder.acquisition import market_routing as MR
    for row in report["recovered_urls"]:
        assert MR.classify_url_shape(row["url"]) in MR.ROUTABLE_SHAPES
        assert row["bind_method"] in (URC.BIND_PHONE, URC.BIND_NAME_POSTAL)


def test_no_two_identities_bound_to_one_google_place(report):
    """The systematic false-binding signal. If it ever fires, one of the two is
    the wrong hotel and the run must have stopped where it stood."""
    assert report["results"]["place_id_collisions"] == {}
    if report["aborted"]:
        assert report["aborted"] in (PILOT.ABORT_PLACE_ID_COLLISION,
                                     PILOT.ABORT_PREMISES_DISAGREEMENT,
                                     PILOT.ABORT_BUDGET)
        assert report["abort_detail"]


def test_the_projection_borrows_no_rate(report):
    projection = report["projection"]
    assert "no rate is borrowed" in projection["basis"]
    pet = projection["pet_friendly_rate"]
    assert pet["successes"] == 34 and pet["trials"] == 65
    url = projection["url_recovery_rate"]
    assert url["trials"] == report["results"]["executed"]
    assert url["successes"] == report["results"]["urls_recovered"]
    assert url["wilson_lower_95"] <= (url["point"] or 0) <= url["wilson_upper_95"]


def test_both_denominators_are_reported(report):
    """56 is the number the work order names; 49 is the number a next batch
    could actually be drawn from. Silently substituting either one is what a
    reader could not check."""
    projection = report["projection"]
    assert projection["remaining_named_by_the_work_order"] == 56
    assert projection["remaining_eligible_identities"] == 49
    assert "held out for cause" in projection["why_the_two_differ"]


def test_a_recovered_url_is_not_a_published_profile(report):
    assert "still has to be fetched" in report["projection"]["caveat"]


def test_exactly_one_recommendation_is_given(report):
    decision = report["recommendation"]["decision"]
    assert decision in ("CONTINUE_WITH_NEXT_SMALL_BATCH",
                        "STOP_RECOVERY_AND_LAUNCH_35")
    if decision == "CONTINUE_WITH_NEXT_SMALL_BATCH":
        size = report["recommendation"]["next_batch_size"]
        assert 0 < size <= PILOT.MAX_REQUESTS
        assert size <= report["projection"]["remaining_eligible_identities"]
    else:
        assert report["recommendation"]["next_batch_size"] == 0
    assert "no further request may be made" in \
        report["recommendation"]["this_is_not_an_authorization"]


def test_wilson_bounds_bracket_the_point_estimate():
    assert PILOT.wilson_lower(7, 20) < 7 / 20 < PILOT.wilson_upper(7, 20)
    assert PILOT.wilson_lower(0, 0) == 0.0 and PILOT.wilson_upper(0, 0) == 0.0
    assert PILOT.wilson_lower(1, 1) < 0.5


# --------------------------------------------------------------------------- #
# Nothing else moved
# --------------------------------------------------------------------------- #

def test_no_authority_was_written():
    import subprocess
    result = subprocess.run(
        ["git", "status", "--porcelain", "--",
         "launch_packages/pettripfinder/markets",
         "launch_packages/pettripfinder/identity_census",
         "launch_packages/pettripfinder/hotel_policy_facts_grand-rapids-holland-mi.json",
         "deploy/netlify"],
        cwd=str(REPO_ROOT.parent), capture_output=True, text=True)
    assert result.returncode == 0, result.stderr
    assert result.stdout.strip() == "", (
        "a discovery pilot writes no authority: %r" % result.stdout)


def test_the_published_count_did_not_move():
    package = _load(LP / "hotel_policy_facts_grand-rapids-holland-mi.json")
    assert package["count"] == 35
