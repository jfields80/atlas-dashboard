"""PTF-GENERIC-CROSS-RUN-PAID-ATTEMPT-LEDGER-001 -- pay once per page, ever.

The three guards that came before this one are all keyed on the identity key,
inside one market pass, against one named prior document. These tests are about
the cases that frame cannot see: the same page under two identity keys, the
same building after a rename, the same hotel rediscovered by a re-census, and
the same answer bought again by a later work order.

They are equally about the mistake in the other direction, which is the more
expensive one. A guard that suppresses too eagerly does not waste money, it
loses coverage -- a hotel that never gets a policy because something decided it
was a duplicate of its neighbour. So a dual-brand building, a shared
switchboard and a shared street each get a test proving they stay DISTINCT.
"""

from __future__ import annotations

import pytest

from scripts.pettripfinder.acquisition import cohort_cost_plan as CP
from scripts.pettripfinder.acquisition import paid_attempt_ledger as PAL
from scripts.pettripfinder.discovery import identity_dedup as DEDUP

LANES = ("firecrawl", "brightdata_browser", "brightdata_web_unlocker")


def attempt(key, url, *, lane="firecrawl", outcome=PAL.O.VALID,
            market="louisville-ky", run="run-001", work_order="WO-001",
            name="", street="", zipc="", phone="", brand="", at="2026-01-01"):
    """One paid attempt, as the ledger records it."""
    return PAL.build_attempt(
        {"identity_key": key, "source_url": url, "outcome": outcome,
         "provider": lane, "providers_tried": [lane],
         "canonical_name": name or key.title(), "brand": brand,
         "street": street, "postal_code": zipc, "telephone": phone,
         "completed_at": at, "content_hash": "hash-%s" % key,
         "artifact_dir": "data/acquisition/%s/%s" % (run, key),
         "final_state": ("ACQUIRED_PUBLICATION_GRADE"
                         if outcome == PAL.O.VALID else "")},
        market_id=market, work_order=work_order, run_id=run, lane=lane,
        cost_usd_minor=15.0)


def ledger_of(*attempts):
    return PAL.merge(PAL.new_ledger(), attempts)


def cohort_row(key, url, *, lane="firecrawl", name="", street="", zipc="",
               phone="", brand="", family="CHOICE"):
    return {"identity_key": key, "source_url": url, "provider": lane,
            "family": family, "canonical_name": name or key.title(),
            "brand": brand, "street": street, "postal_code": zipc,
            "telephone": phone}


def decide(row, ledger, **kw):
    kw.setdefault("available_lanes", LANES)
    return PAL.decide(row, PAL.LedgerIndex(ledger), **kw)


# --------------------------------------------------------------------------- #
# 1-3. One page, however the census spells its name
# --------------------------------------------------------------------------- #

class TestOnePageOneHistory:
    """The identity key is not the property, and the money follows the page."""

    def test_1_the_same_url_under_two_identity_keys_is_one_paid_history(self):
        # Pittsburgh's re-census produced exactly this: a bare OpenStreetMap
        # name and a qualified prior-census name for one building. Both were
        # bought.
        url = "https://www.choicehotels.com/kentucky/louisville/sleep-inn/ky434"
        ledger = ledger_of(attempt("sleep inn", url))
        verdict = decide(cohort_row("sleep inn louisville expo", url), ledger)
        assert verdict["decision"] == PAL.SUPPRESSED_EVIDENCE_REUSABLE
        assert verdict["match_key"] == PAL.MATCH_CANONICAL_URL
        # The suppression must be arguable with: it names the attempt it found.
        assert verdict["prior_run_id"] == "run-001"
        assert verdict["prior_artifact"]

    def test_2_a_rename_does_not_buy_the_property_code_again(self):
        # PROPERTY_CODE:INDNEHX in the historical audit: "Hampton Inn
        # Indianapolis - NE / Castleton" was bought VALID, renamed to
        # "Hampton Inn Indianapolis Northeast Castleton", and bought again.
        before = "https://www.hilton.com/en/hotels/INDNEHX-hampton-ne/"
        after = "https://www.hilton.com/en/hotels/INDNEHX-hampton-northeast/"
        ledger = ledger_of(attempt("hampton inn indianapolis ne castleton",
                                   before, brand="HILTON"))
        verdict = decide(cohort_row("hampton inn indianapolis northeast castleton",
                                    after, brand="HILTON"), ledger)
        assert verdict["decision"] == PAL.SUPPRESSED_EVIDENCE_REUSABLE
        # The URL moved, so only the brand's own key could have caught this.
        assert verdict["match_key"] == PAL.MATCH_PROPERTY_CODE
        assert verdict["match_value"] == "INDNEHX"

    def test_3_a_later_recensus_rediscovering_the_hotel_does_not_rebuy_it(self):
        # A re-census re-derives the identity key AND may re-derive the URL
        # spelling. What survives both is the building: brand, street, postcode.
        ledger = ledger_of(attempt(
            "drury inn st louis", "https://www.druryhotels.com/locations/12345",
            brand="DRURY", street="711 N 2nd St", zipc="63102"))
        verdict = decide(cohort_row(
            "drury inn and suites st louis convention center",
            "https://www.druryhotels.com/locations/st-louis-convention-center",
            brand="DRURY", street="711 North 2nd Street", zipc="63102-1234"),
            ledger)
        assert verdict["decision"] == PAL.SUPPRESSED_EVIDENCE_REUSABLE
        assert verdict["match_key"] == PAL.MATCH_PROPERTY_IDENTITY


# --------------------------------------------------------------------------- #
# 4-5. A terminal answer closes the lane that produced it
# --------------------------------------------------------------------------- #

class TestTerminalResultsAreNotRebought:

    def test_4_a_terminal_firecrawl_result_is_not_bought_from_firecrawl_again(self):
        ledger = ledger_of(attempt("a", "https://x.example/a", lane="firecrawl",
                                   outcome=PAL.O.POLICY_NOT_FOUND))
        verdict = decide(cohort_row("a", "https://x.example/a",
                                    lane="firecrawl"), ledger)
        assert verdict["decision"] == PAL.SUPPRESSED_EVIDENCE_REUSABLE
        # POLICY_NOT_FOUND is a FINDING -- the page rendered and said nothing --
        # and is exactly as durable as a finding that said something.
        assert verdict["reusable_evidence"] is True

    def test_5_a_terminal_brightdata_result_is_not_bought_from_brightdata_again(self):
        ledger = ledger_of(attempt("b", "https://x.example/b",
                                   lane="brightdata_browser"))
        verdict = decide(cohort_row("b", "https://x.example/b",
                                    lane="brightdata_browser"), ledger)
        assert verdict["decision"] == PAL.SUPPRESSED_EVIDENCE_REUSABLE

    def test_a_terminal_answer_closes_every_lane_not_merely_its_own(self):
        # The answer is a property of the PAGE, not of the channel that
        # fetched it, so a dearer lane may not re-buy an answer we hold.
        ledger = ledger_of(attempt("c", "https://x.example/c", lane="firecrawl"))
        verdict = decide(cohort_row("c", "https://x.example/c",
                                    lane="brightdata_browser"), ledger)
        assert verdict["decision"] == PAL.SUPPRESSED_EVIDENCE_REUSABLE


# --------------------------------------------------------------------------- #
# 6-7. Escalation: exactly one, and then closed
# --------------------------------------------------------------------------- #

class TestEscalationLineage:

    def test_6_an_eligible_failure_buys_exactly_one_escalation(self):
        ledger = ledger_of(attempt("d", "https://x.example/d", lane="firecrawl",
                                   outcome=PAL.O.ACCESS_DENIED))
        verdict = decide(cohort_row("d", "https://x.example/d"), ledger)
        assert verdict["decision"] == PAL.ALLOWED_ESCALATION
        # It escalates to a lane that has never been paid for this page...
        assert verdict["escalate_to"] not in verdict["prior_lanes_paid"]
        # ...and it says WHY it was allowed. An unexplained repeat is the thing
        # this module exists to prevent.
        assert verdict["material_change_reason"]
        assert verdict["predecessor_attempt_id"]

    def test_7_a_successful_escalation_closes_the_property(self):
        # attempt 1 fails on the channel -> attempt 2 on a different lane
        # succeeds -> there is no attempt 3.
        first = attempt("e", "https://x.example/e", lane="firecrawl",
                        outcome=PAL.O.ACCESS_DENIED, at="2026-01-01")
        second = attempt("e", "https://x.example/e", lane="brightdata_browser",
                         outcome=PAL.O.VALID, run="run-002", at="2026-01-02")
        verdict = decide(cohort_row("e", "https://x.example/e"),
                         ledger_of(first, second))
        assert verdict["decision"] == PAL.SUPPRESSED_EVIDENCE_REUSABLE

    def test_an_escalation_that_also_failed_does_not_buy_a_third_lane(self):
        # The rule the spec names: attempt 1 -> 2 -> 3 -> 4 may not happen on
        # ONE material-change decision. One escalation is a decision to spend
        # once more, not a licence to walk the whole ladder.
        first = attempt("f", "https://x.example/f", lane="firecrawl",
                        outcome=PAL.O.ACCESS_DENIED, at="2026-01-01")
        second = attempt("f", "https://x.example/f", lane="brightdata_browser",
                         outcome=PAL.O.ACCESS_DENIED, run="run-002",
                         at="2026-01-02")
        second["predecessor_attempt_id"] = first["attempt_id"]
        verdict = decide(cohort_row("f", "https://x.example/f"),
                         ledger_of(first, second))
        assert verdict["decision"] == PAL.SUPPRESSED_ESCALATION_EXHAUSTED

    def test_an_unnamed_ladder_cannot_prove_an_untried_lane_exists(self):
        # "We cannot prove it was a different lane" is not evidence that it
        # was. The refusal says which gap it is refusing on, rather than
        # claiming lanes were exhausted when none were ever offered.
        ledger = ledger_of(attempt("q", "https://x.example/q",
                                   outcome=PAL.O.ACCESS_DENIED))
        verdict = PAL.decide(cohort_row("q", "https://x.example/q"),
                             PAL.LedgerIndex(ledger))
        assert verdict["decision"] == PAL.SUPPRESSED_ESCALATION_EXHAUSTED
        assert "no permitted-lane list was supplied" in verdict["reason"]

    def test_every_permitted_lane_already_paid_closes_the_page(self):
        spent = [attempt("g", "https://x.example/g", lane=lane,
                         outcome=PAL.O.ACCESS_DENIED, run="run-%s" % lane)
                 for lane in LANES]
        verdict = decide(cohort_row("g", "https://x.example/g"),
                         ledger_of(*spent))
        assert verdict["decision"] == PAL.SUPPRESSED_ESCALATION_EXHAUSTED
        assert "already been paid" in verdict["reason"]


# --------------------------------------------------------------------------- #
# 8. A wrong property is a repair, not a purchase
# --------------------------------------------------------------------------- #

class TestIdentityMismatch:

    def test_8_an_identity_mismatch_requires_a_repair_not_a_blind_rebuy(self):
        ledger = ledger_of(attempt("h", "https://x.example/h",
                                   outcome=PAL.O.IDENTITY_MISMATCH))
        verdict = decide(cohort_row("h", "https://x.example/h"), ledger)
        assert verdict["decision"] == PAL.SUPPRESSED_ROUTING_REPAIR_REQUIRED
        assert verdict["routing_repair_required"] is True
        # It is terminal, but its evidence answers a question we did not ask,
        # so it may never be reused as this property's policy.
        assert verdict["reusable_evidence"] is False

    def test_a_documented_repair_unlocks_the_purchase_the_mismatch_blocked(self):
        ledger = ledger_of(attempt("h", "https://x.example/h",
                                   outcome=PAL.O.IDENTITY_MISMATCH))
        verdict = decide(
            cohort_row("h", "https://x.example/h"), ledger,
            material_changes={PAL.MATERIAL_ROUTING_REPAIR:
                              "PTF-ROUTING-REPAIR-007 rebound this row to the "
                              "property page instead of the brand index"})
        assert verdict["decision"] == PAL.ALLOWED_ROUTING_REPAIRED
        assert "PTF-ROUTING-REPAIR-007" in verdict["material_change_reason"]


# --------------------------------------------------------------------------- #
# 9-10, 13. What may unlock a repeat, and what it costs to assert it
# --------------------------------------------------------------------------- #

class TestMaterialChange:

    def test_9_a_materially_changed_url_may_permit_another_attempt(self):
        # Matched on the premises key -- same brand, street and postcode, and a
        # name the census dedup calls compatible -- so the history is found;
        # the URL it would now fetch is simply not the one that was fetched.
        here = dict(street="1 Main St", zipc="40202", brand="DRURY")
        ledger = ledger_of(attempt("drury inn louisville",
                                   "https://x.example/i-old",
                                   name="Drury Inn Louisville", **here))
        verdict = decide(
            cohort_row("drury inn louisville east", "https://x.example/i-new",
                       name="Drury Inn Louisville East", **here),
            ledger,
            material_changes={PAL.MATERIAL_URL_CHANGED:
                              "url recovery displaced the census URL"})
        assert verdict["decision"] == PAL.ALLOWED_URL_CHANGED
        assert verdict["material_change_reason"]

    def test_an_asserted_url_change_that_is_the_same_page_does_not_unlock(self):
        # The assertion is checked against the ledger rather than believed. A
        # trailing slash and a scheme are not a different page.
        ledger = ledger_of(attempt("j", "https://www.x.example/j"))
        verdict = decide(cohort_row("j", "http://x.example/j/"), ledger,
                         material_changes={PAL.MATERIAL_URL_CHANGED: "moved"})
        assert verdict["decision"] == PAL.SUPPRESSED_EVIDENCE_REUSABLE

    def test_10_a_changed_provider_capability_may_permit_a_new_attempt(self):
        ledger = ledger_of(attempt("k", "https://x.example/k",
                                   outcome=PAL.O.UNHYDRATED))
        verdict = decide(
            cohort_row("k", "https://x.example/k"), ledger,
            material_changes={
                PAL.MATERIAL_CAPABILITY_CHANGED:
                    "the Bright Data browser lane gained a hydration wait that "
                    "post-dates run-001"})
        assert verdict["decision"] == PAL.ALLOWED_CAPABILITY_CHANGED
        assert "hydration wait" in verdict["material_change_reason"]

    def test_13_an_override_with_no_reason_is_refused_not_believed(self):
        ledger = ledger_of(attempt("l", "https://x.example/l"))
        with pytest.raises(PAL.PaidLedgerError):
            decide(cohort_row("l", "https://x.example/l"), ledger,
                   material_changes={PAL.MATERIAL_OPERATOR_OVERRIDE: "   "})

    def test_13b_a_reasoned_override_outranks_even_a_terminal_answer(self):
        ledger = ledger_of(attempt("l", "https://x.example/l"))
        verdict = decide(
            cohort_row("l", "https://x.example/l"), ledger,
            material_changes={PAL.MATERIAL_OPERATOR_OVERRIDE:
                              "PTF-FOUNDER-001 asked for a fresh capture after "
                              "the brand redesigned its policy page"})
        assert verdict["decision"] == PAL.ALLOWED_OPERATOR_OVERRIDE
        assert "PTF-FOUNDER-001" in verdict["material_change_reason"]


# --------------------------------------------------------------------------- #
# 11-12. What must NEVER be collapsed
# --------------------------------------------------------------------------- #

class TestDistinctPropertiesStayDistinct:
    """Suppressing too much costs coverage, which is worse than costing money."""

    def test_11_a_dual_brand_building_with_two_property_codes_stays_distinct(self):
        # One building, one street, one switchboard, two hotels -- and two
        # brand property codes, which is the brand's own authority saying so.
        shared = dict(street="601 W Washington St", zipc="46204",
                      phone="317-555-0100", brand="HILTON")
        ledger = ledger_of(attempt(
            "hampton inn indianapolis downtown",
            "https://www.hilton.com/en/hotels/INDDTHX-hampton/", **shared))
        verdict = decide(cohort_row(
            "homewood suites indianapolis downtown",
            "https://www.hilton.com/en/hotels/INDDTHW-homewood/", **shared),
            ledger)
        assert verdict["decision"] == PAL.FIRST_PAID_ATTEMPT
        assert verdict["match_key"] == ""

    def test_12_a_shared_address_alone_does_not_suppress_two_hotels(self):
        # No property code on either side, one address, incompatible names.
        # Two independents in one complex are two policies.
        shared = dict(street="500 E Broad St", zipc="43215")
        ledger = ledger_of(attempt("the athenaeum inn",
                                   "https://athenaeum.example/", **shared))
        verdict = decide(cohort_row("broad street lodge",
                                    "https://broadstlodge.example/", **shared),
                         ledger)
        assert verdict["decision"] == PAL.FIRST_PAID_ATTEMPT

    def test_a_shared_address_WITH_a_compatible_name_does_confirm_one_property(self):
        # The premises key is allowed to confirm what a rename obscured -- it
        # simply may not decide on its own.
        shared = dict(street="500 E Broad St", zipc="43215")
        ledger = ledger_of(attempt("athenaeum inn", "https://a.example/one",
                                   **shared))
        verdict = decide(cohort_row("athenaeum inn columbus",
                                    "https://a.example/two", **shared), ledger)
        assert verdict["decision"] == PAL.SUPPRESSED_EVIDENCE_REUSABLE
        assert verdict["match_key"] == PAL.MATCH_PREMISES_EVIDENCE

    def test_the_match_hierarchy_is_walked_strongest_first(self):
        assert PAL.MATCH_PRIORITY == (
            PAL.MATCH_CANONICAL_URL, PAL.MATCH_PROPERTY_CODE,
            PAL.MATCH_PROPERTY_IDENTITY, PAL.MATCH_PREMISES_EVIDENCE)


# --------------------------------------------------------------------------- #
# 14-15. The cost planner, and what coverage still owes
# --------------------------------------------------------------------------- #

def _plan(*cohort):
    return {"market_id": "louisville-ky", "work_order": "WO-002",
            "run_id": "run-002", "cohort": list(cohort),
            "cohort_rule": {"terminal_prior_outcomes": ["VALID"]},
            "preflight": {"checks": []}}


class TestCostPlanIntegration:

    def test_14_the_cost_planner_removes_historical_duplicates_before_budgeting(self):
        ledger = ledger_of(attempt("paid", "https://x.example/paid",
                                   lane="brightdata_browser"))
        cohort = [cohort_row("paid", "https://x.example/paid",
                             lane="brightdata_browser", family="HILTON"),
                  cohort_row("fresh", "https://x.example/fresh",
                             lane="brightdata_browser", family="HILTON")]
        with_guard = CP.build(_plan(*cohort), {"results": []},
                              authorised_cap_usd=10, paid_ledger=ledger,
                              available_lanes=LANES)
        without = CP.build(_plan(*cohort), {"results": []},
                           authorised_cap_usd=10)

        assert with_guard["cohort_size"] == 1
        assert without["cohort_size"] == 2
        # The budget is computed over the SURVIVING cohort, not the submitted
        # one. A projection that still prices a page we already own is a
        # projection of a purchase that must not happen.
        assert (with_guard["projection"]["worst_case_usd_minor"]
                < without["projection"]["worst_case_usd_minor"])
        assert with_guard["paid_history_suppressed"]["count"] == 1
        assert with_guard["paid_history_suppressed"]["consulted"] is True

    def test_the_fingerprint_describes_the_cohort_the_plan_actually_budgets(self):
        # The paid pass checks this hash to prove the plan it was handed
        # describes the queue it is about to run. If the gate removed a row,
        # the submitted plan's own fingerprint no longer describes anything
        # this plan authorises, and carrying it forward would hand the pass a
        # token that still validates the cohort the gate just rejected.
        ledger = ledger_of(attempt("paid", "https://x.example/paid"))
        cohort = [cohort_row("paid", "https://x.example/paid", family="HILTON"),
                  cohort_row("fresh", "https://x.example/fresh", family="HILTON")]
        submitted = CP.cohort_fingerprint(["paid", "fresh"])
        plan = dict(_plan(*cohort), cohort_keys_sha256=submitted)

        document = CP.build(plan, {"results": []}, authorised_cap_usd=10,
                            paid_ledger=ledger, available_lanes=LANES)
        assert document["cohort_keys_sha256"] == CP.cohort_fingerprint(["fresh"])
        assert document["cohort_keys_sha256"] != submitted

    def test_an_untouched_cohort_keeps_the_plans_own_fingerprint(self):
        plan = dict(_plan(cohort_row("fresh", "https://x.example/fresh",
                                     family="HILTON")),
                    cohort_keys_sha256="carried-through")
        document = CP.build(plan, {"results": []}, authorised_cap_usd=10,
                            paid_ledger=PAL.new_ledger(), available_lanes=LANES)
        assert document["cohort_keys_sha256"] == "carried-through"

    def test_an_absent_ledger_changes_nothing(self):
        # The guard is additive. A market with no recorded paid history buys
        # exactly what it bought before.
        cohort = [cohort_row("a", "https://x.example/a", family="HILTON")]
        assert (CP.build(_plan(*cohort), {"results": []}, authorised_cap_usd=10)
                ["cohort_size"] == 1)
        assert CP.build(_plan(*cohort), {"results": []}, authorised_cap_usd=10,
                        paid_ledger=PAL.new_ledger())["cohort_size"] == 1

    def test_15_coverage_still_accounts_for_every_suppressed_identity(self):
        ledger = ledger_of(attempt("paid", "https://x.example/paid"))
        cohort = [cohort_row("paid", "https://x.example/paid", family="HILTON"),
                  cohort_row("fresh", "https://x.example/fresh", family="HILTON")]
        document = CP.build(_plan(*cohort), {"results": []},
                            authorised_cap_usd=10, paid_ledger=ledger,
                            available_lanes=LANES)
        accounted = document["cohort_accounted_for"]
        assert accounted["total"] == len(cohort)
        assert accounted["payable"] + accounted["paid_history_suppressed"] == 2
        # A suppressed row is named, not deleted: closure can still say what
        # happened to it.
        rows = document["paid_history_suppressed"]["rows"]
        assert [r["identity_key"] for r in rows] == ["paid"]
        assert rows[0]["reason"]

    def test_suppress_is_a_partition_it_never_drops_or_invents_a_row(self):
        ledger = ledger_of(attempt("paid", "https://x.example/paid"))
        cohort = [cohort_row("paid", "https://x.example/paid"),
                  cohort_row("fresh", "https://x.example/fresh"),
                  cohort_row("bare", "")]
        payable, suppressed = PAL.suppress(cohort, ledger, available_lanes=LANES)
        assert len(payable) + len(suppressed) == len(cohort)
        assert ({r["identity_key"] for r in payable}
                | {r["identity_key"] for r in suppressed}
                == {"paid", "fresh", "bare"})

    def test_a_row_with_no_url_at_all_is_payable_not_silently_suppressed(self):
        # Absence of a page key is not evidence of anything. Suppressing on it
        # would delete a hotel from the market for having a thin census row.
        verdict = decide(cohort_row("bare", ""),
                         ledger_of(attempt("other", "https://x.example/other")))
        assert verdict["decision"] == PAL.FIRST_PAID_ATTEMPT


# --------------------------------------------------------------------------- #
# 16-18. Durability, and living with the guards that came before
# --------------------------------------------------------------------------- #

class TestDurabilityAndComposition:

    def test_16_the_ledger_survives_a_new_run_and_a_new_work_order(self):
        ledger = ledger_of(attempt("m", "https://x.example/m",
                                   run="pass-1", work_order="WO-001"))
        # A different work order, a different run id, a different market
        # directory -- and the same page.
        verdict = decide(cohort_row("m", "https://x.example/m"), ledger)
        assert verdict["decision"] == PAL.SUPPRESSED_EVIDENCE_REUSABLE
        assert verdict["prior_run_id"] == "pass-1"

    def test_16b_a_ledger_round_trips_through_disk(self, tmp_path):
        path = tmp_path / "ledger.json"
        PAL.save(path, ledger_of(attempt("n", "https://x.example/n")))
        reloaded = PAL.load(path)
        assert reloaded["schema"] == PAL.SCHEMA
        assert (decide(cohort_row("n", "https://x.example/n"), reloaded)
                ["decision"] == PAL.SUPPRESSED_EVIDENCE_REUSABLE)

    def test_16c_ingesting_one_run_twice_records_it_once(self):
        # An audit that runs twice must not invent a double-buy that never
        # happened.
        one = attempt("o", "https://x.example/o")
        assert len(PAL.merge(ledger_of(one), [one])["attempts"]) == 1

    def test_16d_a_dry_run_contributes_nothing_because_it_bought_nothing(self):
        assert PAL.ingest_run({"dry_run": True, "market_id": "m",
                               "results": [{"identity_key": "a"}]}) == []

    def test_16e_an_unknown_schema_is_refused_rather_than_read(self):
        with pytest.raises(PAL.PaidLedgerError):
            PAL.load(_write_json("ledger.json", {"schema": "something-else/1.0"}))

    def test_17_same_lane_retry_suppression_is_still_intact(self):
        # The retry policy's own rule, restated at the ledger level: the lane
        # that failed does not get paid again on the same unchanged page.
        ledger = ledger_of(attempt("p", "https://x.example/p", lane="firecrawl",
                                   outcome=PAL.O.ACCESS_DENIED))
        verdict = decide(cohort_row("p", "https://x.example/p",
                                    lane="firecrawl"), ledger,
                         available_lanes=("firecrawl",))
        assert verdict["decision"] == PAL.SUPPRESSED_ESCALATION_EXHAUSTED
        assert "firecrawl" in verdict["reason"]

    def test_18_dedup_and_paid_history_do_not_remove_one_identity_twice(self):
        # Two census rows naming one page, and that page was ALSO bought on a
        # previous run. The dedup gate merges the pair; the ledger suppresses
        # the survivor. The identity the dedup absorbed must not also appear in
        # the ledger's suppression list, or closure would count one hotel's
        # removal twice and the coverage arithmetic would stop adding up.
        url = "https://www.choicehotels.com/kentucky/louisville/sleep-inn/ky434"
        census = [{"identity_key": "sleep inn", "official_url": url,
                   "canonical_name": "Sleep Inn"},
                  {"identity_key": "sleep inn louisville expo",
                   "official_url": url,
                   "canonical_name": "Sleep Inn Louisville Expo"}]
        analysis = DEDUP.analyse(census)
        payable_after_dedup = DEDUP.payable_keys(census, analysis)
        assert len(payable_after_dedup) == 1, "the dedup gate merges the twins"

        survivor = payable_after_dedup[0]
        cohort = [cohort_row(survivor, url)]
        payable, suppressed = PAL.suppress(
            cohort, ledger_of(attempt("sleep inn", url)), available_lanes=LANES)

        assert payable == []
        assert len(suppressed) == 1
        # Exactly one row was removed by each gate, and they are not the same
        # row counted twice: the absorbed twin never reached the ledger at all.
        absorbed = {r["identity_key"] for r in census} - set(payable_after_dedup)
        assert absorbed & {r["identity_key"] for r in suppressed} == set()
        assert len(payable) + len(suppressed) == len(cohort)


def _write_json(name, payload):
    import json
    import tempfile
    path = __import__("pathlib").Path(tempfile.mkdtemp()) / name
    path.write_text(json.dumps(payload), encoding="utf-8")
    return path
