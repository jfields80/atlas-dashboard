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
                     terminal: Sequence[str]) -> Dict:
    """Nothing in the cohort was already ANSWERED, and nothing was already run.

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
        ("retries_of_attempts_that_answered_nothing", OrderedDict(
            sorted((k, unsettled[k]) for k in cohort_keys & set(unsettled)))),
        ("no_property_is_bought_twice",
         not (cohort_keys & answered) and not (cohort_keys & journalled)),
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


def build(plan: Mapping, prior: Mapping, *, authorised_cap_usd: float,
          journal_path: Optional[Path] = None,
          previous: Optional[Mapping] = None,
          fallback_provider: str = "brightdata_web_unlocker") -> Dict:
    cohort = list(plan.get("cohort") or ())
    by_provider = Counter(r["provider"] for r in cohort)
    measured = measured_unit_usd_minor(previous or prior)

    lanes: List[Dict] = []
    dollar_low = dollar_high = 0.0
    credit_properties = 0
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
            lane["note"] = ("this lane bills plan credits and draws nothing "
                            "from the dollar cap")
        else:
            low = count * (measured if measured is not None else registry)
            high = count * max(registry, measured or registry)
            lane["projected_usd_minor_at_measured"] = round(low, 2)
            lane["projected_usd_minor_at_registry"] = round(count * registry, 2)
            dollar_low += low
            dollar_high += high
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
        ("cohort_by_provider", OrderedDict(sorted(by_provider.items()))),
        ("cohort_by_family", OrderedDict(
            sorted(Counter(r["family"] for r in cohort).items()))),
        ("dollar_billed_properties", dollar_properties),
        ("credit_billed_properties", credit_properties),
        ("measured_unit_usd_minor", measured),
        ("lanes", lanes),
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
        ("recommended_cap_usd_minor", recommended),
        ("recommended_cap_why", why),
        ("queue_order", plan.get("queue_order") or []),
        ("cohort_provenance", cohort_provenance(plan, previous)),
        ("double_buy_check", double_buy_check(
            cohort, prior, journal_path,
            plan.get("cohort_rule", {}).get("terminal_prior_outcomes") or ())),
    ))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--plan", required=True,
                        help="a --dry-run ptf-market-paid-acquisition report")
    parser.add_argument("--prior", required=True,
                        help="the merged prior acquisition view the plan used")
    parser.add_argument("--authorised-cap-usd", type=float, required=True)
    parser.add_argument("--previous-pass", default="",
                        help="the last real paid pass on this market; its spend "
                             "and its deferred list are what make the "
                             "projection measured rather than quoted")
    parser.add_argument("--journal", default="",
                        help="the journal of the run directory the pass will "
                             "use, if it already exists")
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)

    plan = json.loads(Path(args.plan).read_text(encoding="utf-8"))
    prior = json.loads(Path(args.prior).read_text(encoding="utf-8"))
    previous = (json.loads(Path(args.previous_pass).read_text(encoding="utf-8"))
                if args.previous_pass else None)
    document = build(plan, prior, previous=previous,
                     authorised_cap_usd=args.authorised_cap_usd,
                     journal_path=Path(args.journal) if args.journal else None)
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
    print("cohort provenance     : %s"
          % dict(document["cohort_provenance"]["counts"]))
    check = document["double_buy_check"]
    print("no property bought twice: %s" % check["no_property_is_bought_twice"])
    print("  retries (answered nothing before): %d"
          % len(check["retries_of_attempts_that_answered_nothing"]))
    if not check["no_property_is_bought_twice"]:
        print("  already answered  : %s" % check["already_answered_by_a_prior_pass"])
        print("  already journalled: %s" % check["already_journalled_in_this_run_dir"])
    print("written               : %s" % out)
    return 0 if check["no_property_is_bought_twice"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
