"""PTF-GENERIC-CHEAPEST-VALID-LANE-001 -- the cheapest PROVEN lane.

Two lanes can actually acquire: brightdata_browser at 16.0 US cents a
property, and firecrawl on plan credits, which draws no dollars. Choosing the
cheaper one everywhere is not a policy -- most of this corpus has no Firecrawl
evidence at all -- and choosing the browser everywhere is a policy of paying
for what has already been proven cheaper.

What these tests pin is that a lane is chosen on EVIDENCE and that cost only
breaks ties between lanes that are already qualified. The failure this guards
is asymmetric and that shapes every threshold below: routing a family to an
unproven cheap lane costs a re-acquisition AND publishes weaker evidence,
while leaving a provable family on the browser costs only money.
"""

from __future__ import annotations

from scripts.pettripfinder.acquisition import lane_qualification as LQ
from scripts.pettripfinder.brightdata import outcomes as O

COSTS = {
    "firecrawl": {"usd_minor_per_property": None, "credit_billed": True,
                  "available": True},
    "brightdata_browser": {"usd_minor_per_property": 16.0,
                           "credit_billed": False, "available": True},
    "brightdata_web_unlocker": {"usd_minor_per_property": 5.0,
                                "credit_billed": False, "available": True},
    "direct_http": {"usd_minor_per_property": None, "credit_billed": True,
                    "available": False},
}
AVAILABLE = {k: v["available"] for k, v in COSTS.items()}


def rows(provider, family, *, n, publication_grade, outcome=O.VALID,
         identity_failures=0, defect=""):
    """``n`` attempts of which ``publication_grade`` were publication-grade."""
    out = []
    for i in range(identity_failures):
        out.append({"provider": provider, "family": family,
                    "outcome": O.IDENTITY_MISMATCH, "failure_class": "IDENTITY",
                    "publication_grade": False, "identity_key": "id-%d" % i})
    for i in range(n):
        row = {"provider": provider, "family": family,
               "outcome": outcome if i < publication_grade else O.POLICY_NOT_FOUND,
               "publication_grade": i < publication_grade,
               "identity_key": "%s-%d" % (family.lower(), i)}
        if defect:
            row["defect_class"] = defect
        out.append(row)
    return out


def verdicts(*row_groups):
    merged = [r for group in row_groups for r in group]
    return LQ.qualify(LQ.summarise(merged), available=AVAILABLE)


# --------------------------------------------------------------------------- #
# 1-3, 9. Qualification.
# --------------------------------------------------------------------------- #

def test_a_proven_firecrawl_family_chooses_firecrawl_first():
    v = verdicts(rows("firecrawl", "WYNDHAM", n=33, publication_grade=33))
    plan = LQ.plan_lane("WYNDHAM", v, COSTS)
    assert plan["primary_lane"] == "firecrawl"
    assert plan["fallback_lane"] == "brightdata_browser"
    assert plan["browser_required"] is False


def test_an_insufficient_sample_stays_on_bright_data():
    """One lucky success is not a qualification."""
    v = verdicts(rows("firecrawl", "SONESTA", n=1, publication_grade=1))
    plan = LQ.plan_lane("SONESTA", v, COSTS)
    assert plan["primary_lane"] == "brightdata_browser"
    assert plan["browser_required"] is True


def test_a_high_rate_below_the_minimum_sample_still_does_not_qualify():
    v = verdicts(rows("firecrawl", "DRURY", n=19, publication_grade=19))
    assert v[("firecrawl", "DRURY")]["qualified"] is False
    assert "below the 20" in v[("firecrawl", "DRURY")]["why"]


def test_an_amenity_only_family_does_not_qualify_at_any_rate():
    v = verdicts(rows("firecrawl", "TRUNCATOR", n=40, publication_grade=40,
                      defect="AMENITY_ONLY"))
    verdict = v[("firecrawl", "TRUNCATOR")]
    assert verdict["qualified"] is False
    assert "AMENITY_ONLY" in verdict["why"]
    assert LQ.plan_lane("TRUNCATOR", v, COSTS)["primary_lane"] == "brightdata_browser"


def test_a_poor_rate_at_a_large_sample_does_not_qualify():
    """The real shape of brightdata_web_unlocker on Marriott: 31 attempts, one
    publication-grade."""
    v = verdicts(rows("brightdata_web_unlocker", "MARRIOTT", n=31,
                      publication_grade=1))
    assert v[("brightdata_web_unlocker", "MARRIOTT")]["qualified"] is False


def test_bright_data_remains_the_fallback_for_an_unqualified_family():
    plan = LQ.plan_lane("NEVER_SEEN", {}, COSTS)
    assert plan["primary_lane"] == "brightdata_browser"
    assert plan["browser_required"] is True
    assert "no lane is qualified" in plan["qualification_reason"]


def test_identity_failures_leave_the_denominator():
    """A routing defect must not disqualify the lane that fetched the URL it
    was handed. Choice: 28 of 37 with them, 28 of 30 without."""
    v = verdicts(rows("firecrawl", "CHOICE", n=30, publication_grade=28,
                      identity_failures=7))
    record = v[("firecrawl", "CHOICE")]
    assert record["attempts"] == 37
    assert record["effective_attempts"] == 30
    assert record["qualified"] is True


# --------------------------------------------------------------------------- #
# 10, 11. Lane safety.
# --------------------------------------------------------------------------- #

def test_the_unavailable_direct_http_lane_is_never_chosen():
    """Reserved and UNAVAILABLE. Even a perfect record may not select it."""
    v = verdicts(rows("direct_http", "MARRIOTT", n=100, publication_grade=100))
    assert v[("direct_http", "MARRIOTT")]["qualified"] is False
    assert LQ.plan_lane("MARRIOTT", v, COSTS)["primary_lane"] != "direct_http"


def test_a_property_cannot_enter_two_primary_lanes():
    cohort = [{"identity_key": "a", "family": "WYNDHAM", "provider": "firecrawl"},
              {"identity_key": "a", "family": "WYNDHAM", "provider": "brightdata_browser"}]
    v = verdicts(rows("firecrawl", "WYNDHAM", n=33, publication_grade=33))
    plans = LQ.plan_cohort_lanes(cohort, v, COSTS)
    assert len(plans) == 1
    assert len({p["identity_key"] for p in plans}) == 1


def test_the_cheapest_QUALIFIED_lane_wins_not_the_cheapest_lane():
    """The unlocker is cheaper than the browser in dollars and is not proven;
    the browser must still take an unqualified family."""
    v = verdicts(rows("brightdata_web_unlocker", "MARRIOTT", n=31,
                      publication_grade=1))
    assert LQ.plan_lane("MARRIOTT", v, COSTS)["primary_lane"] == "brightdata_browser"


def test_a_credit_billed_qualified_lane_outranks_a_dollar_qualified_lane():
    v = verdicts(rows("firecrawl", "IHG", n=28, publication_grade=28),
                 rows("brightdata_browser", "IHG", n=28, publication_grade=28))
    plan = LQ.plan_lane("IHG", v, COSTS)
    assert plan["primary_lane"] == "firecrawl"
    assert plan["primary_credit_billed"] is True


# --------------------------------------------------------------------------- #
# 6-8, 14. Escalation.
# --------------------------------------------------------------------------- #

def test_an_approved_failure_escalates_once():
    for outcome in (O.ACCESS_DENIED, O.UNHYDRATED, O.UNEXPECTED_PAGE,
                    O.NAVIGATION_FAILED):
        ok, why = LQ.may_escalate(outcome)
        assert ok is True, outcome
        assert why


def test_a_valid_result_never_escalates():
    ok, why = LQ.may_escalate(O.VALID)
    assert ok is False
    assert "terminal" in why


def test_identity_mismatch_does_not_escalate():
    """No crawler fixes a wrong URL; that is a routing repair."""
    assert LQ.may_escalate(O.IDENTITY_MISMATCH)[0] is False


def test_a_silence_does_not_escalate():
    """The router's own rule: a refusal escalates, a silence does not."""
    assert LQ.may_escalate(O.POLICY_NOT_FOUND)[0] is False


def test_the_no_escalation_set_is_the_same_terminal_set_acquisition_uses():
    """Two definitions of "answered" that can disagree is how a market pays
    twice."""
    from scripts.pettripfinder.acquisition import market_paid_acquisition as MPA
    assert set(LQ.NO_ESCALATION_OUTCOMES) == set(MPA.DEFAULT_TERMINAL)


def test_an_unknown_outcome_does_not_escalate():
    assert LQ.may_escalate("SOMETHING_NEW")[0] is False


# --------------------------------------------------------------------------- #
# 12, 13. The cost model.
# --------------------------------------------------------------------------- #

def test_usd_and_plan_credits_are_accounted_separately():
    v = verdicts(rows("firecrawl", "WYNDHAM", n=33, publication_grade=33))
    firecrawl = LQ.plan_lane("WYNDHAM", v, COSTS)
    browser = LQ.plan_lane("MARRIOTT", v, COSTS)
    assert firecrawl["primary_credit_billed"] is True
    assert firecrawl["primary_usd_minor"] is None, "a credit lane draws no dollars"
    assert browser["primary_credit_billed"] is False
    assert browser["primary_usd_minor"] == 16.0


def test_every_browser_required_row_carries_a_deterministic_reason():
    cohort = [{"identity_key": "a", "family": "MARRIOTT"},
              {"identity_key": "b", "family": "INDEPENDENT"},
              {"identity_key": "c", "family": ""}]
    plans = LQ.plan_cohort_lanes(cohort, {}, COSTS)
    assert all(p["browser_required"] for p in plans)
    assert all(p["qualification_reason"] for p in plans)
    # Deterministic: the same input yields the same reasons.
    again = LQ.plan_cohort_lanes(cohort, {}, COSTS)
    assert [p["qualification_reason"] for p in plans] == \
           [p["qualification_reason"] for p in again]


def test_costs_come_from_the_registry_and_are_never_invented():
    live = LQ.lane_costs()
    assert live["brightdata_browser"]["usd_minor_per_property"] == 16.0
    assert live["firecrawl"]["credit_billed"] is True
    assert live["direct_http"]["available"] is False


# --------------------------------------------------------------------------- #
# 4-5. Reusable evidence suppresses acquisition -- the pre-existing rule.
# --------------------------------------------------------------------------- #

def test_saved_reusable_evidence_suppresses_acquisition():
    """derive_cohort already subtracts an answered property. This pins that the
    lane policy did not weaken it."""
    from scripts.pettripfinder.acquisition import market_paid_acquisition as MPA
    from scripts.pettripfinder.acquisition import market_routing as MR
    entry = {"identity_key": "a", "canonical_name": "A", "brand": "WYNDHAM",
             "corridor": "c", "source_url": "https://x.com/a",
             "provider": "firecrawl", "reader": "r",
             "routing_state": MR.ROUTED, "ladder": [], "fallback_providers": []}
    prior = {"results": [{"identity_key": "a", "outcome": O.VALID}]}
    cohort, settled = MPA.derive_cohort([entry], prior)
    assert cohort == []
    assert len(settled) == 1


def test_settled_prior_evidence_is_not_re_bought_for_any_terminal_outcome():
    from scripts.pettripfinder.acquisition import market_paid_acquisition as MPA
    from scripts.pettripfinder.acquisition import market_routing as MR
    for outcome in MPA.DEFAULT_TERMINAL:
        entry = {"identity_key": "a", "canonical_name": "A", "brand": "B",
                 "corridor": "c", "source_url": "https://x.com/a",
                 "provider": "firecrawl", "reader": "r",
                 "routing_state": MR.ROUTED, "ladder": [],
                 "fallback_providers": []}
        cohort, settled = MPA.derive_cohort(
            [entry], {"results": [{"identity_key": "a", "outcome": outcome}]})
        assert cohort == [], outcome
        assert len(settled) == 1, outcome


def test_the_same_lane_retry_suppression_still_applies():
    """PTF-MARKET-FACTORY-COVERAGE-HARDENING-001's retry policy is untouched:
    a row that already failed on its lane is not re-bought on that same lane."""
    from scripts.pettripfinder.acquisition import market_paid_acquisition as MPA
    from scripts.pettripfinder.acquisition import market_routing as MR
    entry = {"identity_key": "a", "canonical_name": "A", "brand": "B",
             "corridor": "c", "source_url": "https://x.com/a",
             "provider": "brightdata_browser", "reader": "r",
             "routing_state": MR.ROUTED, "ladder": ["brightdata_browser"],
             "fallback_providers": []}
    prior = {"results": [{"identity_key": "a", "outcome": O.ACCESS_DENIED,
                          "provider": "brightdata_browser",
                          "providers_tried": ["brightdata_browser"]}]}
    cohort, settled, suppressed = MPA.plan_cohort([entry], prior)
    assert len(cohort) + len(settled) + len(suppressed) == 1


# --------------------------------------------------------------------------- #
# The committed corpus. These pin the DERIVED table, so a change to the
# evidence or to a threshold has to be seen and explained rather than
# absorbed silently.
# --------------------------------------------------------------------------- #

import json
from pathlib import Path

PACKAGE = Path(__file__).resolve().parents[3] / "launch_packages" / "pettripfinder"

COMMITTED_RUNS = (
    "st_louis_mo_paid_acquisition_002.json",
    "louisville_ky_market_acquisition_002.json",
    "louisville_ky_market_acquisition_003.json",
)


def _committed_verdicts():
    rows = []
    for name in COMMITTED_RUNS:
        path = PACKAGE / name
        if path.is_file():
            rows += json.loads(path.read_text(encoding="utf-8")).get("results") or []
    costs = LQ.lane_costs()
    available = {k: v["available"] for k, v in costs.items()}
    return LQ.qualify(LQ.summarise(rows), available=available), costs


class TestTheCommittedCorpus:

    def test_firecrawl_is_qualified_for_exactly_the_families_it_has_proven(self):
        verdicts, _ = _committed_verdicts()
        qualified = {f for (p, f), v in verdicts.items()
                     if p == "firecrawl" and v["qualified"]}
        assert qualified == {"CHOICE", "WYNDHAM", "IHG"}

    def test_independent_is_qualified_for_no_lane(self):
        """15 browser attempts, one publication-grade. An independent hotel's
        site is not a family with a shape a lane can learn."""
        verdicts, _ = _committed_verdicts()
        assert not any(v["qualified"] for (p, f), v in verdicts.items()
                       if f == "INDEPENDENT")

    def test_the_web_unlocker_is_qualified_for_nothing(self):
        verdicts, _ = _committed_verdicts()
        assert not any(v["qualified"] for (p, f), v in verdicts.items()
                       if p == "brightdata_web_unlocker")

    def test_the_grand_rapids_cohort_is_already_optimally_laned(self):
        """The finding this work order actually produced: the hand-maintained
        routing registry ALREADY agrees with the derived policy, so the policy
        moves nothing. If this test ever fails, either the evidence changed or
        the registry drifted -- both are worth reading."""
        path = PACKAGE / "grand_rapids_holland_mi_acquisition_dry_run_pass1_001.json"
        if not path.is_file():
            return
        cohort = json.loads(path.read_text(encoding="utf-8")).get("cohort") or []
        verdicts, costs = _committed_verdicts()
        plans = LQ.plan_cohort_lanes(cohort, verdicts, costs)
        moved = [p for p in plans
                 if p["current_lane"] and p["current_lane"] != p["primary_lane"]]
        assert moved == [], moved
