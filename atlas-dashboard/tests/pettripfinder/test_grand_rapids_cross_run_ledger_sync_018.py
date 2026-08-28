# -*- coding: utf-8 -*-
"""PTF-GRAND-RAPIDS-CROSS-RUN-LEDGER-SYNC-018.

Two things are asserted here and they are different questions.

The FIRST is the market result: the committed replay artifact says what a
spending run over the currently routed Grand Rapids / Holland cohort would buy,
and the answer must be nothing. Every one of the 65 routed, non-duplicate
candidates is already answered, already failed on every permitted lane, or
waiting on a routing repair. A test that only asserted "validation passed"
would still pass if the cohort silently became empty, so the counts are pinned
and they have to add up.

The SECOND is the generic defect this replay surfaced. ``ingest_run`` writes
every lane of one in-run escalation with a single ``attempted_at``, because the
run records one timestamp per property rather than one per lane. ``decide``
sorted that tie on ``attempt_id`` -- a hash -- so which lane counted as "the
last word" was arbitrary, and for the Motel 6 Grand Rapids Northeast row the
blank-outcome PREDECESSOR won. The suppression was still correct; its stated
reason was not, and a suppression whose reason is wrong is one nobody can argue
with. The regression is written against a synthetic ladder so it keeps failing
if the ordering regresses even when the market data changes.
"""
from __future__ import annotations

import json
import sys
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.pettripfinder import grand_rapids_holland_ledger_replay_018 as R  # noqa: E402
from scripts.pettripfinder.acquisition import paid_attempt_ledger as PAL       # noqa: E402

LP = REPO_ROOT / "launch_packages" / "pettripfinder"
REPLAY = LP / "grand_rapids_holland_mi_cross_run_ledger_replay_018.json"
LEDGER = LP / "ptf_paid_attempt_ledger_001.json"
MARKET = "grand-rapids-holland-mi"


@pytest.fixture(scope="module")
def replay():
    assert REPLAY.is_file(), "the committed replay artifact is missing"
    return json.loads(REPLAY.read_text(encoding="utf-8"))


# --------------------------------------------------------------------------- #
# The sync itself
# --------------------------------------------------------------------------- #

def test_the_generic_ledger_is_present_and_holds_the_grand_rapids_run():
    """A ledger that does not know about this market's own paid run protects
    nothing, and every suppression in the replay would be an accident."""
    ledger = PAL.load(LEDGER)
    grand_rapids = [a for a in ledger["attempts"] if a["market_id"] == MARKET]
    assert len(grand_rapids) == 68, "68 lane attempts over 65 properties"
    assert {a["run_id"] for a in grand_rapids} == {
        "grand-rapids-holland-mi-001-pass1"}


def test_re_ingesting_the_paid_run_adds_nothing(replay):
    """Idempotency is what makes an audit safe to re-run. If a second ingest
    added rows, an audit run twice would invent a double buy."""
    completeness = replay["ledger_completeness"]
    assert completeness["rows_from_re_ingesting_the_paid_run"] == 68
    assert completeness["new_rows_added"] == 0
    assert completeness["ok"] is True


def test_the_cost_planner_consults_the_ledger_before_budgeting():
    """The sync is only real if the generic cost plan can be handed a ledger."""
    from scripts.pettripfinder.acquisition import cohort_cost_plan as CCP
    assert "paid_ledger" in CCP.build.__code__.co_varnames


# --------------------------------------------------------------------------- #
# The replay
# --------------------------------------------------------------------------- #

def test_every_routed_candidate_is_classified_exactly_once(replay):
    counts = replay["counts"]
    classes = replay["by_classification"]
    assert counts["routed_identities_before"] == 82
    assert counts["acquisition_cohort_before"] == 65
    assert counts["settled_before_the_ledger_by_the_dedup_gate"] == 17
    assert sum(classes.values()) == counts["acquisition_cohort_before"]
    assert len(replay["rows"]) == counts["acquisition_cohort_before"]
    assert len({row["identity_key"] for row in replay["rows"]}) == 65


def test_the_whole_cohort_is_suppressed_and_nothing_is_payable(replay):
    counts, classes = replay["counts"], replay["by_classification"]
    assert counts["suppressed_by_cross_run_ledger"] == 65
    assert counts["genuinely_payable_after_replay"] == 0
    assert classes["REUSABLE_POLICY_EVIDENCE"] == 54
    assert classes["ALREADY_PAID"] == 0
    assert classes["SAME_PAGE_ALREADY_FAILED"] == 3
    assert classes["ROUTING_REPAIR_REQUIRED"] == 8
    assert classes["GENUINELY_PAYABLE"] == 0


def test_no_hotel_was_suppressed_on_proximity(replay):
    """All 65 matched the URL that was actually fetched. Over-suppression is
    the expensive mistake -- a suppressed hotel never gets a policy -- so the
    replay has to show that not one row was refused on a shared address."""
    check = replay["validation"]["every_suppression_rests_on_a_page_key"]
    assert check["ok"] is True
    assert check["suppressed_on_a_weak_key"] == []
    assert check["by_match_key"] == {"CANONICAL_URL": 65}


def test_an_unknown_ledger_decision_is_never_filed_as_payable():
    """The classification table is total over the ledger's decisions. A new
    decision must break this test rather than default into the buy list."""
    assert set(R.CLASSIFICATION) == set(PAL.DECISIONS)
    with pytest.raises(PAL.PaidLedgerError):
        R.classify({"paid_history": {"decision": "SOMETHING_NEW"}})


def test_nothing_is_bought_and_the_cost_plan_is_zero(replay):
    cost = replay["cost_plan"]
    assert cost["current_spend_usd_minor"] == 0
    assert cost["firecrawl_credits_required"] == 0
    assert cost["projected_brightdata_usd_minor"] == 0
    assert cost["worst_case_usd_minor"] == 0
    assert cost["recommended_hard_cap_usd_minor"] == 0
    lanes = replay["lane_plan"]
    assert lanes["rows"] == 0
    assert (lanes["firecrawl"], lanes["brightdata_browser"],
            lanes["brightdata_web_unlocker"], lanes["other"]) == (0, 0, 0, 0)


def test_the_lane_rules_qualify_exactly_the_five_pairs_the_corpus_supports(replay):
    """The cross-run ledger, read through the committed qualification rules,
    reproduces the five pairs ``lane_qualification`` documents. Grand Rapids on
    its own evidence qualifies none of them -- Marriott on the browser is 17 of
    17 and Hilton 16 of 18, both short of the 20 effective attempts the policy
    demands -- so recording both views is what stops the wider corpus from
    being taken on trust."""
    plan = replay["lane_plan"]
    assert plan["evidence_used"] == "CROSS_RUN_LEDGER"
    assert plan["qualified_pairs"] == [
        "brightdata_browser/HILTON", "brightdata_browser/MARRIOTT",
        "firecrawl/CHOICE", "firecrawl/IHG", "firecrawl/WYNDHAM"]
    assert plan["qualified_pairs_on_this_markets_evidence_alone"] == []


def test_no_new_provider_family_is_introduced_by_this_pass(replay):
    """Every qualified lane is one this project has already measured. The order
    forbids experimenting with a new provider family, and the rules cannot
    invent one: a lane with no evidence cannot clear a threshold."""
    lanes = {pair.split("/")[0] for pair in replay["lane_plan"]["qualified_pairs"]}
    assert lanes <= {"brightdata_browser", "brightdata_web_unlocker", "firecrawl"}


def test_every_validation_check_passes(replay):
    validation = replay["validation"]
    for name, check in validation.items():
        if name == "all_pass":
            continue
        assert check["ok"] is True, "%s: %r" % (name, check)
    assert validation["all_pass"] is True


# --------------------------------------------------------------------------- #
# The identity holds
# --------------------------------------------------------------------------- #

def test_the_two_identity_questions_are_still_open(replay):
    """Neither pair was merged and neither half was promoted. The dedup gate
    ruled them DISTINCT_PROPERTIES; a replay reads history, it does not rule."""
    holds = replay["identity_holds"]
    assert holds["count"] == 2
    pairs = {tuple(h["identity_keys"]) for h in holds["holds"]}
    assert ("comfort inn", "comfort suites grandville grand rapids sw") in pairs
    assert ("sleep inn and suites", "spark by hilton grand rapids") in pairs
    for hold in holds["holds"]:
        assert hold["dedup_verdict"] == "DISTINCT_PROPERTIES"
        assert hold["still_two_identities"] is True
        assert hold["resolved_by_this_pass"] is False
        assert hold["in_payable_cohort"] == []


def test_a_shared_switchboard_never_collapses_two_hotels_in_the_ledger():
    """The Comfort Inn / Comfort Suites pair shares a street AND a telephone,
    which is exactly the premises evidence the ledger is allowed to confirm a
    match on. Two different property pages outrank it, because the page keys
    decide alone and the walk stops at the first one that matches."""
    ledger = PAL.new_ledger()
    ledger = PAL.merge(ledger, [PAL.build_attempt(
        {"identity_key": "comfort suites grandville grand rapids sw",
         "canonical_name": "Comfort Suites Grandville Grand Rapids SW",
         "source_url": "https://www.choicehotels.com/michigan/grandville/comfort-suites-hotels/mi333",
         "street": "4520 Kenowa Ave SW", "postal_code": "49418",
         "telephone": "616-667-0733", "outcome": "VALID",
         "publication_grade": True},
        market_id=MARKET, work_order="TEST", run_id="test", lane="firecrawl")])

    other = {"identity_key": "comfort inn", "canonical_name": "Comfort Inn",
             "source_url": "https://www.choicehotels.com/michigan/grandville/comfort-inn-hotels/mi999",
             "street": "4520 Kenowa Ave SW", "postal_code": "49418",
             "telephone": "616-667-0733"}
    decision = PAL.decide(other, PAL.LedgerIndex(ledger))
    assert decision["decision"] == PAL.FIRST_PAID_ATTEMPT


def test_a_rebrand_at_one_address_is_a_question_for_a_person():
    """Sleep Inn and Suites -> Spark by Hilton, one street, one switchboard.

    Either it is one renamed building or it is two hotels, and the ledger is
    not the thing that decides which. Falling through costs at most one repeat
    purchase; deciding wrongly costs a hotel its policy for ever."""
    shared = {"street": "4284 29th St SE", "postal_code": "49512",
              "telephone": "616-975-9000"}
    ledger = PAL.merge(PAL.new_ledger(), [PAL.build_attempt(
        dict(shared, identity_key="sleep inn and suites",
             canonical_name="Sleep Inn & Suites",
             source_url="https://www.choicehotels.com/mi/sleep-inn/mi111",
             outcome="VALID", publication_grade=True),
        market_id=MARKET, work_order="TEST", run_id="test",
        lane="firecrawl")])
    decision = PAL.decide(
        dict(shared, identity_key="spark by hilton grand rapids",
             canonical_name="Spark by Hilton Grand Rapids",
             source_url="https://www.hilton.com/en/hotels/grrsp-spark/"),
        PAL.LedgerIndex(ledger))
    assert decision["decision"] == PAL.FIRST_PAID_ATTEMPT
    assert decision["match_key"] == ""


def test_a_rename_that_only_lengthened_the_name_still_confirms():
    """The fix bounds what a shared address may decide; it does not disarm it.
    A compatible name is still confirmation, which is the re-census case the
    ledger was built for."""
    shared = {"street": "500 E Broad St", "postal_code": "43215",
              "telephone": "614-555-0100"}
    ledger = PAL.merge(PAL.new_ledger(), [PAL.build_attempt(
        dict(shared, identity_key="athenaeum inn",
             canonical_name="Athenaeum Inn",
             source_url="https://athenaeum.example/one",
             outcome="VALID", publication_grade=True),
        market_id=MARKET, work_order="TEST", run_id="test",
        lane="firecrawl")])
    decision = PAL.decide(
        dict(shared, identity_key="athenaeum inn columbus",
             canonical_name="Athenaeum Inn Columbus",
             source_url="https://athenaeum.example/two"),
        PAL.LedgerIndex(ledger))
    assert decision["decision"] == PAL.SUPPRESSED_EVIDENCE_REUSABLE
    assert decision["match_key"] == PAL.MATCH_PREMISES_EVIDENCE


def test_the_held_pairs_are_not_in_the_payable_cohort_for_a_stated_reason(replay):
    """Three of the four halves carry no official URL at all, so they never
    reach a paid lane; the fourth is answered. Recording WHY matters: 'not
    payable' by accident is not the same fact as 'not payable' by rule."""
    states = {}
    for hold in replay["identity_holds"]["holds"]:
        states.update(hold["routing_state"])
    assert states["comfort inn"] == "ROUTE_NEEDS_OFFICIAL_URL"
    assert states["sleep inn and suites"] == "ROUTE_NEEDS_OFFICIAL_URL"
    assert states["spark by hilton grand rapids"] == "ROUTE_NEEDS_OFFICIAL_URL"
    assert states["comfort suites grandville grand rapids sw"] == "ROUTED"
    answered = [r for r in replay["rows"]
                if r["identity_key"] == "comfort suites grandville grand rapids sw"]
    assert len(answered) == 1
    assert answered[0]["classification"] == "REUSABLE_POLICY_EVIDENCE"
    assert answered[0]["match_key"] == PAL.MATCH_CANONICAL_URL


# --------------------------------------------------------------------------- #
# The ordering defect this replay surfaced
# --------------------------------------------------------------------------- #

def _ladder_pair(outcome):
    """One property, two lanes, ONE timestamp -- what ``ingest_run`` writes."""
    run = {
        "market_id": MARKET, "work_order": "TEST", "run_id": "test-run",
        "results": [{
            "identity_key": "motel 6 somewhere",
            "canonical_name": "Motel 6 Somewhere",
            "source_url": "https://www.motel6.com/content/g6/en/home/x.html",
            "provider": "brightdata_web_unlocker",
            "providers_tried": ["brightdata_browser", "brightdata_web_unlocker"],
            "outcome": outcome, "final_state": "PROVIDER_EXHAUSTED",
            "publication_grade": False,
        }],
    }
    return PAL.ingest_run(run, market_id=MARKET)


def test_the_last_word_on_a_ladder_is_the_lane_that_ran_last():
    """Not the one whose attempt_id happens to sort highest."""
    records = _ladder_pair("UNEXPECTED_PAGE")
    assert len(records) == 2
    assert len({r["attempted_at"] for r in records}) == 1, (
        "the fixture is only meaningful while the two lanes share a timestamp")
    ordered = sorted(records, key=R.PAL._attempt_order)
    assert [r["lane"] for r in ordered] == ["brightdata_browser",
                                            "brightdata_web_unlocker"]
    assert ordered[-1]["outcome"] == "UNEXPECTED_PAGE"


def test_the_suppression_reason_names_the_outcome_the_ledger_recorded():
    """The defect: the decision reported the prior outcome as unrecorded when
    the ledger plainly recorded UNEXPECTED_PAGE on the second lane."""
    ledger = PAL.merge(PAL.new_ledger(), _ladder_pair("UNEXPECTED_PAGE"))
    row = {"identity_key": "motel 6 somewhere renamed",
           "canonical_name": "Motel 6 Somewhere",
           "source_url": "https://www.motel6.com/content/g6/en/home/x.html"}
    decision = PAL.decide(row, PAL.LedgerIndex(ledger),
                          available_lanes=("brightdata_browser",
                                           "brightdata_web_unlocker"))
    assert decision["prior_outcome"] == "UNEXPECTED_PAGE"
    assert decision["prior_lane"] == "brightdata_web_unlocker"
    assert decision["decision"] == PAL.SUPPRESSED_ESCALATION_EXHAUSTED
    assert "unrecorded" not in decision["reason"]


def test_the_ordering_fix_does_not_make_anything_payable():
    """It moves a row between two SUPPRESSED classes and no further. A repair
    to a reason must never turn into a licence to spend."""
    ledger = PAL.merge(PAL.new_ledger(), _ladder_pair("UNEXPECTED_PAGE"))
    row = {"identity_key": "motel 6 somewhere renamed",
           "canonical_name": "Motel 6 Somewhere",
           "source_url": "https://www.motel6.com/content/g6/en/home/x.html"}
    payable, suppressed = PAL.suppress(
        [row], ledger,
        available_lanes=("brightdata_browser", "brightdata_web_unlocker"))
    assert (len(payable), len(suppressed)) == (0, 1)
