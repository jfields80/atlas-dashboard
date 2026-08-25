"""What a cohort will cost, and what it must not buy twice, BEFORE any call.

    python scripts/pettripfinder/acquisition/cohort_cost_plan.py \
      --plan launch_packages/pettripfinder/louisville_ky_cost_plan_003.json \
      --prior launch_packages/pettripfinder/louisville_ky_acquisition_merged_003.json \
      --authorised-cap-usd 10 --out launch_packages/pettripfinder/..._plan.json

A paid pass is authorised as a ceiling -- "ten dollars for this work order" --
and a ceiling is not a plan. Two questions have to be answered before the first
call, and answering them after it is answering them too late:

WHAT WILL IT COST
-----------------
Every lane bills in its own currency. The Bright Data browser draws dollars, the
Web Unlocker draws fewer dollars, and Firecrawl draws plan credits and no dollars
at all, so a cohort of thirty-four properties can cost anything between nothing
and the whole cap depending on which lanes it lands in. The projection is stated
twice, from the registry's published unit price and from the price this market
actually MEASURED on its last pass, because those two numbers disagree -- and the
gap between them is the honest error bar on the total.

The vendor's account balance is part of the plan and not a footnote. A cap of ten
dollars against a balance of four is not a ten-dollar plan; the run will stop at
four however the cap is written, and a cost plan that does not say so is a
forecast of something that cannot happen.

WHAT MUST IT NOT BUY
--------------------
A property that a previous pass already answered must not be paid for again. The
cohort is derived by subtraction upstream, so this module does not re-derive it:
it CHECKS it, by intersecting the cohort against every identity any prior pass
settled and against every identity already in the run's journal. An empty
intersection is the proof; a non-empty one is a defect, and it is reported as
one rather than quietly filtered, because a cohort that contains a settled
property means the subtraction that built it was wrong.

Zero network. Zero spend. The plan is a document, not a decision.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter, OrderedDict
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.acquisition import journal as JOURNAL  # noqa: E402
from scripts.pettripfinder.acquisition import providers as PROVIDERS  # noqa: E402

SCHEMA = "ptf-cohort-cost-plan/1.0"

#: A lane that bills in plan credits draws nothing from a dollar cap. Saying so
#: explicitly is what keeps a credit-billed cohort out of the dollar projection.
CREDIT_BILLED = "PLAN_CREDITS"


def cohort_fingerprint(keys: Sequence[str]) -> str:
    """One hash over a cohort's identity keys, order-independent.

    PTF-MARKET-FACTORY-COVERAGE-HARDENING-001 makes the cost plan a gate the
    paid pass checks before spending. A gate that only checks a plan EXISTS
    admits a plan for last week's cohort; the fingerprint is how the pass proves
    the plan it was handed describes the queue it is about to run.
    """
    material = "\n".join(sorted(str(k) for k in keys))
    return hashlib.sha256(material.encode("utf-8")).hexdigest()


def cumulative_prior_spend(previous_passes: Sequence[Mapping]) -> Dict:
    """What every earlier paid pass on this market has already cost, by run.

    Summed over DISTINCT run ids: a resumed pass reports a cumulative figure for
    its own work order, so two reports of one run must count once. The reason
    this is in the plan at all is that an authorisation is per market, not per
    pass, and a third pass that does not know what the first two spent cannot
    say whether it is still inside it.
    """
    by_run: "OrderedDict[str, Dict]" = OrderedDict()
    for document in previous_passes:
        run_id = str(document.get("run_id") or document.get("work_order") or "")
        spend = document.get("spend") or {}
        binding = spend.get("binding_usd_minor")
        credits = spend.get("estimated_plan_credits")
        by_run[run_id] = OrderedDict((
            ("run_id", run_id),
            ("work_order", document.get("work_order", "")),
            ("usd_minor", float(binding or 0)),
            ("plan_credits", float(credits or 0)),
            ("attempted", int(document.get("attempted") or 0)),
        ))
    return OrderedDict((
        ("runs", list(by_run.values())),
        ("usd_minor", round(sum(r["usd_minor"] for r in by_run.values()), 2)),
        ("plan_credits", round(sum(r["plan_credits"] for r in by_run.values()), 2)),
    ))


def predicted_completion(queue: Sequence[Mapping], *, available_usd_minor: float,
                         unit_usd_minor_by_provider: Mapping[str, float],
                         credit_cap: Optional[int] = None) -> Dict:
    """How far down the queue the money reaches, property by property.

    Walked in QUEUE order because that is the order the cap will cut. A total
    that says "the cohort costs 349 cents and you have 444" is true and useless
    when the first twenty properties are the expensive ones; the answer a
    person needs is WHICH properties the balance covers and which it defers.
    """
    spent = 0.0
    credits = 0.0
    attemptable: List[str] = []
    deferred: List[str] = []
    stopped_on = ""
    for row in queue:
        provider = row.get("provider", "")
        unit = float(unit_usd_minor_by_provider.get(provider, 0.0) or 0.0)
        is_credit = unit == 0.0 and provider in unit_usd_minor_by_provider
        if is_credit:
            if credit_cap is not None and credits + 1 > credit_cap:
                if not stopped_on:
                    stopped_on = "plan-credit cap"
                deferred.append(row["identity_key"])
                continue
            credits += 1
            attemptable.append(row["identity_key"])
            continue
        if stopped_on or spent + unit > available_usd_minor:
            if not stopped_on:
                stopped_on = "dollar balance"
            deferred.append(row["identity_key"])
            continue
        spent += unit
        attemptable.append(row["identity_key"])
    return OrderedDict((
        ("available_usd_minor", round(available_usd_minor, 2)),
        ("attemptable", len(attemptable)),
        ("deferred", len(deferred)),
        ("completes_cohort", not deferred),
        ("stops_on", stopped_on),
        ("projected_spend_usd_minor", round(spent, 2)),
        ("projected_plan_credits", round(credits, 2)),
        ("attemptable_keys", attemptable),
        ("deferred_keys", deferred),
        ("basis", "walked in queue order at each lane's higher of registry and "
                  "measured unit price; a credit-billed lane draws no dollars"),
    ))


def unit_price_usd_minor(provider: str) -> Optional[float]:
    """The registry's published price for one property on this lane."""
    try:
        cost = PROVIDERS.get(provider).cost_metadata()
    except (PROVIDERS.ProviderError, KeyError):
        return None
    return (None if cost.usd_minor_per_property is None
            else float(cost.usd_minor_per_property))


def measured_unit_usd_minor(prior: Mapping) -> Optional[float]:
    """What the last pass on this market actually paid per property attempted.

    Read from the pass's own spend and its own attempt count rather than from a
    stored unit: a stored unit is a claim, and these two numbers are the evidence
    for it. A pass that attempted nothing has no measurement and says so.
    """
    spend = prior.get("spend") or {}
    binding = spend.get("binding_usd_minor")
    attempted = prior.get("attempted_this_session") or prior.get("attempted") or 0
    if not binding or not attempted:
        return None
    return round(float(binding) / float(attempted), 2)


def double_buy_check(cohort: Sequence[Mapping], prior: Mapping,
                     journal_path: Optional[Path],
                     terminal: Sequence[str], *,
                     resumes: bool = True) -> Dict:
    """Nothing in the cohort was already ANSWERED, and nothing was already run.

    ``resumes`` says whether the pass this plan is for will resume from the
    run directory's journal (the default of ``market_paid_acquisition``) and
    skip every key already completed there. PTF-INDIANAPOLIS-HARDENED-
    RECENSUS-002 stopped a pass after four properties because the census had
    changed under it; the next plan refused the whole cohort because those
    four were 'already journalled', and a factory that cannot resume an
    interrupted pass would have had to discard the journal to continue --
    which is exactly the double buy the check exists to prevent. A key the
    resume will skip is reported as RESUMED, not bought, and does not fail the
    proof; with ``--no-resume`` it fails the proof as before.

    Answered is not the same as attempted, and conflating them fails the check on
    exactly the properties a second pass exists for. A page that served and was
    read is answered; a page that timed out, refused, or arrived unhydrated was
    paid for and answered nothing, and the money that bought it bought no fact.
    Those are reported as retries -- named, counted, and not a defect -- while a
    property whose question a prior pass actually settled appearing in the cohort
    is a defect in the subtraction that built it.
    """
    terminal_set = frozenset(terminal)
    answered = {r["identity_key"] for r in (prior.get("results") or ())
                if r.get("outcome") in terminal_set}
    unsettled = {r["identity_key"]: r.get("outcome", "")
                 for r in (prior.get("results") or ())
                 if r.get("outcome") and r.get("outcome") not in terminal_set}
    cohort_keys = {r["identity_key"] for r in cohort}
    journalled = set()
    if journal_path and journal_path.is_file():
        journalled = set(JOURNAL.Journal(path=journal_path).completed_keys())
    return OrderedDict((
        ("terminal_outcomes", list(terminal)),
        ("prior_results_examined", len(prior.get("results") or ())),
        ("prior_results_that_answered", len(answered)),
        ("journal_examined", journal_path.as_posix() if journal_path else ""),
        ("journalled_keys", len(journalled)),
        ("cohort_size", len(cohort_keys)),
        ("already_answered_by_a_prior_pass", sorted(cohort_keys & answered)),
        ("already_journalled_in_this_run_dir",
         sorted(cohort_keys & journalled)),
        ("pass_resumes_from_that_journal", bool(resumes)),
        ("resumed_from_journal_not_bought_again",
         sorted(cohort_keys & journalled) if resumes else []),
        ("retries_of_attempts_that_answered_nothing", OrderedDict(
            sorted((k, unsettled[k]) for k in cohort_keys & set(unsettled)))),
        ("no_property_is_bought_twice",
         not (cohort_keys & answered)
         and (bool(resumes) or not (cohort_keys & journalled))),
    ))


def cohort_provenance(plan: Mapping, previous: Optional[Mapping]) -> Dict:
    """Where each property in the cohort came from, by name.

    A cohort of thirty-four is three different populations wearing one number:
    identities a zero-cost URL recovery routed for the first time, identities the
    last pass had routed and never reached because the cap bound first, and
    identities the last pass reached without getting an answer. They carry
    different risk and they justify different spend, so the plan names them
    rather than reporting one total.
    """
    cohort_keys = {r["identity_key"] for r in (plan.get("cohort") or ())}
    overlay = {r["identity_key"] for r in
               (plan.get("url_overlay", {}).get("rows") or ())}
    # A deferred entry is written as a bare identity key by one pass and as a
    # row by another; both spellings mean the same property was never reached.
    deferred = {(r if isinstance(r, str) else r.get("identity_key"))
                for r in ((previous or {}).get("deferred") or ())}
    attempted = {r["identity_key"] for r in ((previous or {}).get("results") or ())}
    newly_routed = sorted(cohort_keys & overlay)
    previously_deferred = sorted((cohort_keys & deferred) - set(newly_routed))
    retried = sorted((cohort_keys & attempted) - set(newly_routed)
                     - set(previously_deferred))
    rest = sorted(cohort_keys - set(newly_routed) - set(previously_deferred)
                  - set(retried))
    return OrderedDict((
        ("newly_routed_by_url_recovery", newly_routed),
        ("previously_deferred_by_the_cap", previously_deferred),
        ("retried_after_an_attempt_that_answered_nothing", retried),
        ("routed_before_and_never_attempted", rest),
        ("counts", OrderedDict((
            ("newly_routed_by_url_recovery", len(newly_routed)),
            ("previously_deferred_by_the_cap", len(previously_deferred)),
            ("retried_after_an_attempt_that_answered_nothing", len(retried)),
            ("routed_before_and_never_attempted", len(rest)),
        ))),
    ))


def _credits_per_property(provider: str) -> float:
    try:
        cost = PROVIDERS.get(provider).cost_metadata()
    except (PROVIDERS.ProviderError, KeyError):
        return 0.0
    return float(cost.credits_per_property or 0.0)


def build(plan: Mapping, prior: Mapping, *, authorised_cap_usd: float,
          journal_path: Optional[Path] = None,
          previous: Optional[Mapping] = None,
          previous_passes: Sequence[Mapping] = (),
          credit_cap: Optional[int] = None,
          fallback_provider: str = "brightdata_web_unlocker",
          resumes: bool = True) -> Dict:
    cohort = list(plan.get("cohort") or ())
    by_provider = Counter(r["provider"] for r in cohort)
    if previous is None and previous_passes:
        previous = previous_passes[-1]
    measured = measured_unit_usd_minor(previous or prior)

    lanes: List[Dict] = []
    dollar_low = dollar_high = 0.0
    credit_properties = 0
    expected_credits = 0.0
    unit_by_provider: Dict[str, float] = {}
    for provider, count in sorted(by_provider.items()):
        registry = unit_price_usd_minor(provider)
        lane = OrderedDict((
            ("provider", provider),
            ("properties", count),
            ("billing", CREDIT_BILLED if registry is None else "USD"),
            ("registry_unit_usd_minor", registry),
            ("measured_unit_usd_minor", measured if registry is not None else None),
        ))
        if registry is None:
            credit_properties += count
            lane["projected_usd_minor"] = 0
            lane["projected_plan_credits"] = round(
                count * _credits_per_property(provider), 2)
            expected_credits += lane["projected_plan_credits"]
            unit_by_provider[provider] = 0.0
            lane["note"] = ("this lane bills plan credits and draws nothing "
                            "from the dollar cap")
        else:
            low = count * (measured if measured is not None else registry)
            high = count * max(registry, measured or registry)
            lane["projected_usd_minor_at_measured"] = round(low, 2)
            lane["projected_usd_minor_at_registry"] = round(count * registry, 2)
            dollar_low += low
            dollar_high += high
            unit_by_provider[provider] = max(registry, measured or registry)
        lanes.append(lane)

    fallback_unit = unit_price_usd_minor(fallback_provider) or 0.0
    dollar_properties = sum(l["properties"] for l in lanes
                            if l["billing"] == "USD")
    fallback_exposure = round(dollar_properties * fallback_unit, 2)

    balance = None
    for check in plan.get("preflight", {}).get("checks") or ():
        detail = str(check.get("detail") or "")
        if check.get("check") == "balance_covers_the_remaining_cap":
            for word in detail.replace(",", " ").split():
                if word.isdigit():
                    balance = int(word)
                    break
            break

    ceiling = round(dollar_high + fallback_exposure, 2)
    authorised_minor = int(round(authorised_cap_usd * 100))
    cumulative = cumulative_prior_spend(list(previous_passes) or
                                        ([previous] if previous else []))
    remaining_minor = int(round(authorised_minor - cumulative["usd_minor"]))
    recommended = authorised_minor
    why = ("the authorised ceiling covers the projection with room for the "
           "fallback lane")
    if balance is not None and balance < authorised_minor:
        recommended = int(balance * 0.9 // 1)
        why = ("the vendor balance (%d cents) is below the authorised ceiling "
               "(%d cents); a cap above the balance is a cap the run cannot "
               "reach, so it is set to 90%% of the balance and the remaining "
               "authorisation stays unspent" % (balance, authorised_minor))
    elif ceiling > authorised_minor:
        recommended = authorised_minor
        why = ("the worst case (%s cents) exceeds the authorised ceiling, so "
               "the cap binds first and the queue order decides what is "
               "reached" % ceiling)
    # PTF-INDIANAPOLIS-HARDENED-RECENSUS-002: the authorisation is for the
    # WORK ORDER, not per pass. The plan already reported the cumulative
    # spend and the authorisation remaining -- and then recommended the
    # whole ceiling again: a second pass after a STOPPED_HARD_CAP first pass
    # (992 of 1000 cents) was handed a 1000-cent cap and started buying. The
    # recommended cap can never exceed what the authorisation has left.
    if recommended > max(remaining_minor, 0):
        recommended = max(remaining_minor, 0)
        why = ("earlier passes of this work order have spent %s of the %d "
               "cents authorised; the cap is what remains (%d cents)%s"
               % (cumulative["usd_minor"], authorised_minor, recommended,
                  "" if recommended > 0 else " -- the authorisation is "
                  "exhausted and this pass may buy nothing"))

    # The queue in run order, when the plan carries one; the cohort's own order
    # otherwise (older dry-run reports predate the field).
    by_key = {r["identity_key"]: r for r in cohort}
    queue_keys = [k for k in (plan.get("queue") or ()) if k in by_key]
    queue = ([by_key[k] for k in queue_keys] if queue_keys else cohort)
    available = float(min(recommended, balance) if balance is not None
                      else recommended)
    completion = predicted_completion(
        queue, available_usd_minor=available,
        unit_usd_minor_by_provider=unit_by_provider, credit_cap=credit_cap)
    suppressed = list(plan.get("suppressed_same_lane") or ())

    return OrderedDict((
        ("schema", SCHEMA),
        ("what_this_is",
         "What one cohort is expected to cost, in each currency its lanes bill "
         "in, and the proof that it buys nothing a previous pass already "
         "answered. Zero network, zero spend."),
        ("market_id", plan.get("market_id", "")),
        ("work_order", plan.get("work_order", "")),
        ("derived_from", OrderedDict((
            ("plan", plan.get("run_id", "")),
            ("prior", prior.get("work_order", "")),
        ))),
        ("cohort_size", len(cohort)),
        ("cohort_keys_sha256",
         plan.get("cohort_keys_sha256")
         or cohort_fingerprint([r["identity_key"] for r in cohort])),
        ("cohort_by_provider", OrderedDict(sorted(by_provider.items()))),
        ("cohort_by_family", OrderedDict(
            sorted(Counter(r["family"] for r in cohort).items()))),
        ("dollar_billed_properties", dollar_properties),
        ("credit_billed_properties", credit_properties),
        ("measured_unit_usd_minor", measured),
        ("lanes", lanes),
        ("expected_firecrawl_credits", round(expected_credits, 2)),
        ("expected_brightdata_usd_minor", OrderedDict((
            ("at_measured", round(dollar_low, 2)),
            ("at_registry", round(dollar_high, 2)),
            ("worst_case_with_fallback", ceiling),
        ))),
        ("projection", OrderedDict((
            ("at_measured_rates_usd_minor", round(dollar_low, 2)),
            ("at_registry_rates_usd_minor", round(dollar_high, 2)),
            ("unlocker_fallback_exposure_usd_minor", fallback_exposure),
            ("worst_case_usd_minor", ceiling),
            ("basis", "every dollar-billed property attempted once at the "
                      "higher of the registry and measured unit price, plus a "
                      "fallback attempt on every one of them"),
        ))),
        ("vendor_balance_usd_minor", balance),
        ("authorised_cap_usd_minor", authorised_minor),
        ("cumulative_prior_spend", cumulative),
        ("authorisation_remaining_usd_minor",
         round(authorised_minor - cumulative["usd_minor"], 2)),
        ("authorisation_exhausted", recommended <= 0),
        ("recommended_cap_usd_minor", recommended),
        ("recommended_cap_why", why),
        ("predicted_completion_under_balance", completion),
        ("queue_order", plan.get("queue_order") or []),
        ("cohort_provenance", cohort_provenance(plan, previous)),
        ("same_lane_retries_suppressed", OrderedDict((
            ("count", len(suppressed)),
            ("identity_keys", sorted(r.get("identity_key", "")
                                     for r in suppressed)),
            ("note", "excluded from this cohort by the retry policy; not "
                     "settled, not bought"),
        ))),
        ("double_buy_check", double_buy_check(
            cohort, prior, journal_path,
            plan.get("cohort_rule", {}).get("terminal_prior_outcomes") or (),
            resumes=resumes)),
    ))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--plan", required=True,
                        help="a --dry-run ptf-market-paid-acquisition report")
    parser.add_argument("--prior", required=True,
                        help="the merged prior acquisition view the plan used")
    parser.add_argument("--authorised-cap-usd", type=float, required=True)
    parser.add_argument("--previous-pass", action="append", default=[],
                        help="every earlier paid pass on this market, oldest "
                             "first; repeatable. The last one's spend and "
                             "deferred list make the projection measured rather "
                             "than quoted, and all of them together are the "
                             "cumulative spend against the authorisation")
    parser.add_argument("--credit-cap", type=int, default=None,
                        help="the plan-credit ceiling the pass will run under")
    parser.add_argument("--journal", default="",
                        help="the journal of the run directory the pass will "
                             "use, if it already exists")
    parser.add_argument("--no-resume", action="store_true",
                        help="the pass will NOT resume from the run directory's "
                             "journal, so a journalled key in the cohort IS a "
                             "double buy")
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)

    plan = json.loads(Path(args.plan).read_text(encoding="utf-8"))
    prior = json.loads(Path(args.prior).read_text(encoding="utf-8"))
    previous_passes = [json.loads(Path(p).read_text(encoding="utf-8"))
                       for p in args.previous_pass]
    document = build(plan, prior, previous_passes=previous_passes,
                     authorised_cap_usd=args.authorised_cap_usd,
                     credit_cap=args.credit_cap,
                     journal_path=Path(args.journal) if args.journal else None,
                     resumes=not args.no_resume)
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(document, indent=1, ensure_ascii=False) + "\n",
                   encoding="utf-8", newline="\n")

    print("cohort                : %d (%d dollar-billed, %d credit-billed)"
          % (document["cohort_size"], document["dollar_billed_properties"],
             document["credit_billed_properties"]))
    for lane in document["lanes"]:
        print("  %-24s %3d properties  %s"
              % (lane["provider"], lane["properties"], lane["billing"]))
    projection = document["projection"]
    print("projected (measured)  : %s cents"
          % projection["at_measured_rates_usd_minor"])
    print("projected (registry)  : %s cents"
          % projection["at_registry_rates_usd_minor"])
    print("fallback exposure     : %s cents"
          % projection["unlocker_fallback_exposure_usd_minor"])
    print("worst case            : %s cents" % projection["worst_case_usd_minor"])
    print("vendor balance        : %s cents" % document["vendor_balance_usd_minor"])
    print("authorised cap        : %s cents" % document["authorised_cap_usd_minor"])
    print("recommended cap       : %s cents -- %s"
          % (document["recommended_cap_usd_minor"],
             document["recommended_cap_why"]))
    print("prior spend           : %s cents over %d run(s); authorisation "
          "remaining %s cents"
          % (document["cumulative_prior_spend"]["usd_minor"],
             len(document["cumulative_prior_spend"]["runs"]),
             document["authorisation_remaining_usd_minor"]))
    completion = document["predicted_completion_under_balance"]
    print("predicted completion  : %d attemptable, %d deferred (%s)"
          % (completion["attemptable"], completion["deferred"],
             "completes the cohort" if completion["completes_cohort"]
             else "stops on the " + completion["stops_on"]))
    print("same-lane suppressed  : %d"
          % document["same_lane_retries_suppressed"]["count"])
    print("cohort provenance     : %s"
          % dict(document["cohort_provenance"]["counts"]))
    check = document["double_buy_check"]
    print("no property bought twice: %s" % check["no_property_is_bought_twice"])
    if check.get("resumed_from_journal_not_bought_again"):
        print("  resumed from journal (not bought again): %s"
              % check["resumed_from_journal_not_bought_again"])
    print("  retries (answered nothing before): %d"
          % len(check["retries_of_attempts_that_answered_nothing"]))
    if not check["no_property_is_bought_twice"]:
        print("  already answered  : %s" % check["already_answered_by_a_prior_pass"])
        print("  already journalled: %s" % check["already_journalled_in_this_run_dir"])
    print("written               : %s" % out)
    return 0 if check["no_property_is_bought_twice"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
