# -*- coding: utf-8 -*-
"""PTF-INDIANAPOLIS-BACKLOG-COST-PLAN-015 -- what the last 6 profiles would cost.

Indianapolis stands at a projected 44 pet-friendly profiles and the founder
wants 50. The only untouched paid population is the 24 rows that
PTF-INDIANAPOLIS-TARGETED-POLICY-ACQUISITION-012 recorded as
NOT_AUTHORIZED_THIS_WORK_ORDER. This prices them and nothing else.

ZERO NETWORK. ZERO SPEND. This module reads artifacts already on disk.

THE YIELD ESTIMATE IS THE PART THAT CAN LIE
--------------------------------------------
Cost is arithmetic. Yield is a forecast, and a forecast built to justify a
purchase is worthless. Three rules keep this one honest:

    THE DENOMINATOR IS ATTEMPTS, NOT SUCCESSES. 012 attempted 50 and 20 of
    them ended as founder-signed pet-friendly rows. 40% is therefore already
    net of IDENTITY_MISMATCH, of NAVIGATION_FAILED, of POLICY_NOT_FOUND and of
    everything the founder review declined. It is not a "if it reads, it
    publishes" number.

    A RATE IS REPORTED WITH ITS SAMPLE AND ITS LOWER BOUND. HILTON went 9 for
    9. Quoting 100% off nine rows would be arithmetic dressed as evidence, so
    every family also carries a Wilson 95% lower bound and the plans are sized
    on THAT. Nine-for-nine buys a floor of 70%, not a promise of 100%.

    A FAMILY WITH NO INDIANAPOLIS EVIDENCE CONTRIBUTES ZERO. SONESTA was never
    attempted here. Its expected yield is 0.0 in both plans -- not a market
    average borrowed from other families, and not a rate imported from another
    market, which this work order forbids.

WHAT WE DELIBERATELY DID NOT USE AS A SELECTOR
-----------------------------------------------
``url_names_the_property`` was true for all 50 rows of the 012 cohort. It has
NO discriminating power inside this population, so using it to rank would be
inventing a signal. It is run anyway, and it flags exactly one backlog row --
``tru``, whose name carries no distinctive word -- which is reported as a
quality caveat rather than folded into a rate.

Hotel names are never read for pet-friendliness. The only selector is a
family's own measured Indianapolis history.
"""
from __future__ import annotations

import argparse
import json
import math
from collections import Counter, OrderedDict
from pathlib import Path
from typing import Dict, List, Mapping, Sequence

_REPO = Path(__file__).resolve().parents[2]
LP = _REPO / "launch_packages" / "pettripfinder"

WORK_ORDER = "PTF-INDIANAPOLIS-BACKLOG-COST-PLAN-015"
TARGET = 50
CURRENT_PROMOTED = 24

#: 95% two-sided. Used only to floor a rate, never to inflate one.
_Z = 1.96


def wilson_lower_bound(successes: int, trials: int, z: float = _Z) -> float:
    """The lower end of the Wilson score interval.

    Nine-for-nine is not 100%. This is what nine-for-nine is actually worth.
    """
    if trials <= 0:
        return 0.0
    p = successes / trials
    denominator = 1.0 + z * z / trials
    centre = p + z * z / (2 * trials)
    margin = z * math.sqrt((p * (1 - p) + z * z / (4 * trials)) / trials)
    return max(0.0, (centre - margin) / denominator)


def rule_of_three_upper(trials: int):
    """With zero successes in n trials, the 95% ceiling on the true rate.

    Zero-for-five is not proof of zero, it is proof of 'no more than 60%'.

    Below about ten trials the bound exceeds 1.0 and stops carrying any
    information at all: zero-for-one bounds the rate at 300%, which is to say
    it bounds nothing. Those cases return None rather than a number, because a
    ceiling of 'certainly at most everything' dressed up as a percentage reads
    like evidence and is not.
    """
    if trials <= 0:
        return None
    bound = 3.0 / trials
    return None if bound >= 1.0 else bound


# --------------------------------------------------------------------------
# evidence
# --------------------------------------------------------------------------

def load(name: str) -> Dict:
    return json.loads((LP / name).read_text(encoding="utf-8"))


def signed_authorities() -> Dict[str, str]:
    out: Dict[str, str] = {}
    for name in ("indianapolis_in_founder_signature_013.json",
                 "indianapolis_in_founder_signature_014.json"):
        for row in load(name)["signed"]:
            out[row["identity_key"]] = row["proposes_authority"]
    return out


def family_history() -> Dict[str, Dict]:
    """What each brand family actually did in Indianapolis, on paid attempts."""
    run = load("indianapolis_in_market_acquisition_012.json")
    family = {row["identity_key"]: row.get("family", "") for row in run["cohort"]}
    authority = signed_authorities()

    attempted: Counter = Counter()
    valid: Counter = Counter()
    pet_friendly: Counter = Counter()
    no_pets: Counter = Counter()
    for result in run["results"]:
        fam = family.get(result["identity_key"], "")
        attempted[fam] += 1
        if result["outcome"] == "VALID":
            valid[fam] += 1
        signed = authority.get(result["identity_key"])
        if signed == "PUBLISHED_PET_FRIENDLY":
            pet_friendly[fam] += 1
        elif signed == "VERIFIED_NO_PETS":
            no_pets[fam] += 1

    out: Dict[str, Dict] = OrderedDict()
    for fam in sorted(attempted):
        n, k = attempted[fam], pet_friendly[fam]
        out[fam] = OrderedDict((
            ("attempted", n), ("valid", valid[fam]),
            ("pet_friendly", k), ("verified_no_pets", no_pets[fam]),
            ("pet_friendly_rate", round(k / n, 4)),
            ("pet_friendly_rate_wilson_lower_95", round(wilson_lower_bound(k, n), 4)),
            ("ceiling_if_zero_observed",
             (lambda b: round(b, 4) if b is not None else None)(
                 rule_of_three_upper(n)) if k == 0 else None),
            ("ceiling_note",
             "zero observed in only %d attempts: the 95%% ceiling is not below "
             "1.0, so nothing is bounded and no rate is claimed" % n
             if k == 0 and rule_of_three_upper(n) is None else ""),
            ("basis", "%d of %d paid attempts ended as a founder-signed "
                      "pet-friendly row" % (k, n)),
        ))
    return out


# --------------------------------------------------------------------------
# the cohort
# --------------------------------------------------------------------------

def classify(dry_run: Mapping, original_backlog: Sequence[Mapping]) -> List[Dict]:
    """One line per original backlog identity, with the reason it is or is not
    payable. A suppressed row is NOT replaced by another."""
    from scripts.pettripfinder.discovery.census_url_recovery import (
        url_names_the_property)

    gate = dry_run["authorized_cohort"]
    payable = {row["identity_key"]: row for row in dry_run["cohort"]}
    suppressed = {row["identity_key"]: row
                  for row in gate.get("suppressed_rows", [])}

    rows: List[Dict] = []
    for entry in original_backlog:
        key = entry["identity_key"]
        row = payable.get(key)
        if key in suppressed:
            decision = suppressed[key]["decision"]
            why = suppressed[key]["reason"]
        elif row is not None:
            decision = "PAYABLE_FIRST_ATTEMPT"
            why = row["retry_why"]
        else:
            decision = "OTHER_NONPAYABLE"
            why = ("present in 012's backlog and absent from the re-derived "
                   "queue; it must be explained before it is bought")
        names, names_why = (url_names_the_property(row["canonical_name"],
                                                   row["source_url"])
                            if row else (None, "not costed"))
        rows.append(OrderedDict((
            ("identity_key", key),
            ("canonical_name", row["canonical_name"] if row else ""),
            ("family", row["family"] if row else entry.get("provider", "")),
            ("official_url", row["source_url"] if row else ""),
            ("provider_lane", row["provider"] if row else entry.get("provider", "")),
            ("fallback_lane", row["fallback_providers"] if row else []),
            ("reader", row["reader"] if row else ""),
            ("routing_state", "ROUTED" if row else "NOT_IN_QUEUE"),
            ("prior_outcome", row["prior_outcome"] if row else "UNKNOWN"),
            ("cross_run_paid_history_match",
             suppressed[key]["reason"] if key in suppressed
             else "no prior paid attempt matches this property"),
            ("prior_terminal_or_reusable_evidence",
             "none -- never attempted" if row and
             row["prior_outcome"] == "NEVER_ATTEMPTED" else
             (row["prior_outcome"] if row else "see paid history")),
            ("url_names_the_property", names),
            ("url_names_the_property_why", names_why),
            ("decision", decision),
            ("still_genuinely_payable", decision == "PAYABLE_FIRST_ATTEMPT"),
            ("why", why),
        )))
    return rows


# --------------------------------------------------------------------------
# the two plans
# --------------------------------------------------------------------------

UNIT_REGISTRY_C = 16.0        # routes.json unit price for brightdata_browser

#: The measured unit price the 012 COST PLAN carried going in. It is NOT what
#: 012 settled at afterwards, and this module does not claim a settled rate:
#: 012's dollars are not cleanly attributable per row (its meter was seeded
#: 222c from earlier sessions) and the Bright Data zone meter is known to
#: settle UPWARD in the minutes after a run. It is shown beside the registry
#: price as the cheaper end of a range, and every projection uses the higher.
UNIT_012_PLAN_MEASURED_C = 13.41
FALLBACK_C = 5.0              # unlocker fallback exposure, per row


def price(rows: Sequence[Mapping]) -> Dict:
    n = len(rows)
    projected = round(n * UNIT_REGISTRY_C, 2)
    fallback = round(n * FALLBACK_C, 2)
    return OrderedDict((
        ("rows", n),
        ("firecrawl_rows", sum(1 for r in rows if r["provider_lane"] == "firecrawl")),
        ("brightdata_rows", sum(1 for r in rows
                                if r["provider_lane"] == "brightdata_browser")),
        ("firecrawl_plan_credits", 0),
        ("projected_usd_minor_at_registry", projected),
        ("projected_usd_minor_at_012_plan_measured_unit",
         round(n * UNIT_012_PLAN_MEASURED_C, 2)),
        ("what_the_two_prices_are",
         "the projection bills at the routes.json price of %.0fc. The second "
         "figure uses the %.2fc measured unit the 012 cost plan carried BEFORE "
         "that run; it is the optimistic end of a range, not a settled rate, "
         "and no cap is ever set from it."
         % (UNIT_REGISTRY_C, UNIT_012_PLAN_MEASURED_C)),
        ("fallback_exposure_usd_minor", fallback),
        ("worst_case_usd_minor", round(projected + fallback, 2)),
        ("safe_cap_usd_minor", int(math.ceil((projected + fallback) / 25.0) * 25)),
    ))


def expected_yield(rows: Sequence[Mapping], history: Mapping) -> Dict:
    point = 0.0
    floor = 0.0
    contributions: List[Dict] = []
    for fam, count in sorted(Counter(r["family"] for r in rows).items()):
        stats = history.get(fam)
        if stats is None:
            contributions.append(OrderedDict((
                ("family", fam), ("rows", count),
                ("indianapolis_attempts", 0),
                ("rate_point", None), ("rate_floor", 0.0),
                ("expected_point", 0.0), ("expected_floor", 0.0),
                ("note", "never attempted in Indianapolis. It contributes ZERO "
                         "to both estimates; no market average is borrowed and "
                         "no other market is consulted."),
            )))
            continue
        p, lo = stats["pet_friendly_rate"], stats["pet_friendly_rate_wilson_lower_95"]
        point += count * p
        floor += count * lo
        contributions.append(OrderedDict((
            ("family", fam), ("rows", count),
            ("indianapolis_attempts", stats["attempted"]),
            ("rate_point", p), ("rate_floor", lo),
            ("expected_point", round(count * p, 2)),
            ("expected_floor", round(count * lo, 2)),
            ("note", stats["basis"] + (
                "; zero observed, so the true rate is only bounded ABOVE at "
                "%.0f%% -- this is 'unproven', not 'proven empty'"
                % (100 * stats["ceiling_if_zero_observed"])
                if stats["ceiling_if_zero_observed"] else "")),
        )))
    return OrderedDict((
        ("expected_pet_friendly_point", round(point, 2)),
        ("expected_pet_friendly_conservative", round(floor, 2)),
        ("by_family", contributions),
        ("method", "each family's own Indianapolis paid-attempt history, "
                   "denominated in ATTEMPTS so it already nets out identity "
                   "mismatches, navigation failures and founder declines. The "
                   "conservative column uses the Wilson 95% lower bound."),
    ))


def sub_brand_key(identity_key: str) -> str:
    """The first two words: 'hampton inn', 'hilton garden', 'home2 suites'.

    One word is not enough. 'hilton garden inn indianapolis airport' and
    'hilton indianapolis hotel and suites' both start with 'hilton' and are
    different brands with different pet policies; collapsing them would lend
    Hilton Garden Inn a precedent it does not have.
    """
    words = identity_key.split()
    return " ".join(words[:2]) if len(words) >= 2 else (words[0] if words else "")


def sub_brand_history() -> Dict[str, Dict]:
    """The same measurement as family_history, one grain finer."""
    run = load("indianapolis_in_market_acquisition_012.json")
    authority = signed_authorities()
    attempted: Counter = Counter()
    pet_friendly: Counter = Counter()
    for row in run["cohort"]:
        key = sub_brand_key(row["identity_key"])
        attempted[key] += 1
        if authority.get(row["identity_key"]) == "PUBLISHED_PET_FRIENDLY":
            pet_friendly[key] += 1
    return {k: OrderedDict((("attempted", attempted[k]),
                            ("pet_friendly", pet_friendly[k]),
                            ("rate", round(pet_friendly[k] / attempted[k], 4))))
            for k in attempted}


def minimum_cohort(payable: Sequence[Mapping], history: Mapping,
                   need: int, sub_brands: Mapping) -> Dict:
    """The smallest deterministic subset whose CONSERVATIVE yield reaches need.

    Rows are drawn family-first, by the family's Wilson floor. Within a family
    the tie is broken by that row's own SUB-BRAND record in Indianapolis, so a
    Hampton Inn (3 for 3 here) is drawn before a Hilton Garden Inn (never
    attempted here) at identical price. Both are covered by the HILTON floor;
    one of them is better evidenced, and at equal cost there is no reason to
    prefer the weaker.

    Nothing in this ordering reads a hotel's name for pet-friendliness. It
    reads measured outcomes at two grains, and the second grain only ever
    orders rows the first grain has already admitted.
    """
    def rank(row):
        fam = history.get(row["family"], {})
        sub = sub_brands.get(sub_brand_key(row["identity_key"]))
        return (-fam.get("pet_friendly_rate_wilson_lower_95", 0.0),
                -fam.get("attempted", 0),
                0 if sub else 1,                       # evidenced sub-brands first
                -(sub["rate"] if sub else 0.0),
                -(sub["attempted"] if sub else 0),
                row["identity_key"])

    chosen: List[Dict] = []
    running = 0.0
    for row in sorted(payable, key=rank):
        floor = history.get(row["family"], {}).get(
            "pet_friendly_rate_wilson_lower_95", 0.0)
        if floor <= 0.0:
            break          # a family with no proven floor cannot be counted on
        chosen.append(row)
        running += floor
        if running >= need:
            break
    return OrderedDict((
        ("derivable", running >= need),
        ("rule", "draw payable rows in descending order of their family's "
                 "Wilson 95% lower-bound pet-friendly rate, breaking ties on "
                 "the row's own sub-brand record in this market, and stop when "
                 "the cumulative conservative yield reaches the gap. A family "
                 "with a zero floor is never drawn on. No hotel name is read "
                 "for pet-friendliness."),
        ("need", need),
        ("identity_keys", [r["identity_key"] for r in chosen]),
        ("count", len(chosen)),
        ("cumulative_conservative_yield", round(running, 2)),
        ("reaches_the_target", running >= need),
    ))


def sub_brand_precedent(rows: Sequence[Mapping]) -> Dict:
    """Which chosen rows have a same-sub-brand Indianapolis result behind them.

    The family rate is a HILTON rate. Five of the backlog's Hilton rows are
    Hilton Garden Inn, a sub-brand 012 never touched. That is the honest soft
    spot in the forecast and it is named rather than buried.
    """
    run = load("indianapolis_in_market_acquisition_012.json")
    authority = signed_authorities()
    seen: Dict[str, Counter] = {}
    for row in run["cohort"]:
        token = sub_brand_key(row["identity_key"])
        bucket = seen.setdefault(token, Counter())
        bucket["attempted"] += 1
        if authority.get(row["identity_key"]) == "PUBLISHED_PET_FRIENDLY":
            bucket["pet_friendly"] += 1

    with_precedent, without = [], []
    for row in rows:
        token = sub_brand_key(row["identity_key"])
        bucket = seen.get(token)
        (with_precedent if bucket else without).append(OrderedDict((
            ("identity_key", row["identity_key"]),
            ("sub_brand_token", token),
            ("indianapolis_attempts", bucket["attempted"] if bucket else 0),
            ("indianapolis_pet_friendly", bucket["pet_friendly"] if bucket else 0),
        )))
    return OrderedDict((
        ("with_same_sub_brand_precedent", with_precedent),
        ("without_any_sub_brand_precedent", without),
        ("caveat", "the forecast is built at FAMILY grain, which is the grain "
                   "the evidence exists at. A row with no same-sub-brand "
                   "Indianapolis result is still covered by its family's "
                   "record, but it is the weakest part of the estimate and is "
                   "listed so the reader can discount it."),
    ))


# --------------------------------------------------------------------------
# the document
# --------------------------------------------------------------------------

def build(dry_run_path: str) -> Dict:
    dry_run = json.loads(Path(dry_run_path).read_text(encoding="utf-8"))
    run012 = load("indianapolis_in_market_acquisition_012.json")
    original = run012["authorized_cohort"]["backlog_rows"]

    history = family_history()
    rows = classify(dry_run, original)
    payable = [r for r in rows if r["still_genuinely_payable"]]
    suppressed = [r for r in rows if not r["still_genuinely_payable"]]

    promoted = len(load("hotel_policy_facts_indianapolis-in.json")["hotels"])
    signed_pf = sum(1 for a in signed_authorities().values()
                    if a == "PUBLISHED_PET_FRIENDLY")
    projected_now = promoted + signed_pf
    gap = TARGET - projected_now

    plan_a = OrderedDict((
        ("name", "PLAN A -- FULL PAYABLE BACKLOG"),
        ("identity_keys", [r["identity_key"] for r in payable]),
        ("cost", price(payable)),
        ("yield", expected_yield(payable, history)),
    ))

    minimum = minimum_cohort(payable, history, gap, sub_brand_history())
    picked = set(minimum["identity_keys"])
    chosen = [r for r in payable if r["identity_key"] in picked]
    plan_b = OrderedDict((
        ("name", "PLAN B -- MINIMUM TARGET-50 COHORT"),
        ("selection", minimum),
        ("identity_keys", minimum["identity_keys"]),
        ("cost", price(chosen)),
        ("yield", expected_yield(chosen, history)),
        ("sub_brand_precedent", sub_brand_precedent(chosen)),
    ))

    a_worst = plan_a["cost"]["worst_case_usd_minor"]
    b_worst = plan_b["cost"]["worst_case_usd_minor"]
    a_floor = plan_a["yield"]["expected_pet_friendly_conservative"]
    b_floor = plan_b["yield"]["expected_pet_friendly_conservative"]

    return OrderedDict((
        ("schema", "ptf-backlog-cost-plan/1.0"),
        ("market_id", "indianapolis-in"), ("work_order", WORK_ORDER),
        ("status", "PLAN_ONLY_NO_SPEND_AUTHORISED"),
        ("provider_calls", 0), ("usd_spent", 0),
        ("nothing_is_authorised_by_this_file",
         "This prices a cohort. It authorises no spend, buys nothing, "
         "promotes nothing and publishes nothing. A runner may not bill "
         "against it; an authorisation is a separate document a person signs."),
        ("current_state", OrderedDict((
            ("promoted_pet_friendly", promoted),
            ("signed_pet_friendly_013_014", signed_pf),
            ("projected_total", projected_now),
            ("target", TARGET), ("gap", gap),
        ))),
        ("backlog", OrderedDict((
            ("original_count", len(original)),
            ("payable_after_ledger", len(payable)),
            ("suppressed", len(suppressed)),
            ("by_decision", OrderedDict(sorted(
                Counter(r["decision"] for r in rows).items()))),
            ("no_substitution", "a suppressed backlog row SHRINKS the cohort. "
                                "Nothing was promoted to fill its place."),
            ("rows", rows),
        ))),
        ("lanes", OrderedDict((
            ("firecrawl", 0),
            ("brightdata_browser", len(payable)),
            ("why_no_firecrawl",
             "routes.json qualifies Firecrawl for CHOICE, IHG and WYNDHAM. The "
             "payable backlog is HILTON, INDEPENDENT, ESA, RED_ROOF and "
             "SONESTA, none of which qualify. The cheap lane is not declined "
             "here, it is unavailable, and every row is dollar-billed."),
            ("browser_required_rows", len(payable)),
            ("browser_required_reason",
             "brightdata_browser is the committed first rung for all five of "
             "these families; brightdata_web_unlocker is the fallback rung."),
            ("readers", OrderedDict(sorted(
                Counter(r["reader"] for r in payable).items()))),
        ))),
        ("family_history_indianapolis", history),
        ("plan_a", plan_a),
        ("plan_b", plan_b),
        ("recommendation", OrderedDict((
            ("recommended", "PLAN A"),
            ("why", "Plan B is defensible and derivable without guessing, but "
                    "it buys the target with almost no margin: %.1f "
                    "conservative against a gap of %d. Plan A costs %.0f cents "
                    "more in the worst case and carries %.1f conservative, "
                    "which is the difference between landing at 50 and landing "
                    "at 49 and needing a second authorisation cycle. At these "
                    "prices the margin is worth more than the money."
                    % (b_floor, gap, a_worst - b_worst, a_floor)),
            ("plan_a_worst_case_usd_minor", a_worst),
            ("plan_b_worst_case_usd_minor", b_worst),
            ("difference_usd_minor", round(a_worst - b_worst, 2)),
        ))),
        ("projected_total_after", OrderedDict((
            ("plan_a_conservative", round(projected_now + a_floor, 1)),
            ("plan_a_point", round(projected_now
                                   + plan_a["yield"]["expected_pet_friendly_point"], 1)),
            ("plan_b_conservative", round(projected_now + b_floor, 1)),
            ("caveat", "these are FORECASTS. Every row still passes identity "
                       "confirmation, the reader and a founder review before "
                       "it is a profile, and the founder may decline any of "
                       "them. Nothing here entitles the number to be claimed."),
        ))),
        ("separate_work_not_in_this_plan", OrderedDict((
            ("esa_fee_only_hold", OrderedDict((
                ("identity_key",
                 "extended stay america indianapolis airport w southern ave"),
                ("state", "HELD by 013; not reopened here"),
                ("cost", "zero -- its capture is already paid for"),
                ("why_not_here", "it is a READING question, not an acquisition "
                                 "question. Its block is a fee schedule that "
                                 "never grants permission, and no new purchase "
                                 "can change that."),
            ))),
            ("identity_mismatch_rows", OrderedDict((
                ("count", 14),
                ("state", "routing repair, not acquisition"),
                ("cost", "zero to diagnose -- the captures are already paid for"),
                ("evidence_that_some_are_OUR_defect", [
                    "extended stay america indianapolis west 86th st: page "
                    "street '8520 N.W. Blvd.' against an expected '8520 "
                    "Northwest Boulevard' -- the same address, refused on an "
                    "abbreviation",
                    "intown suites x2: the page names a marketing title "
                    "('Indianapolis South, IN Extended Stay Hotel') rather "
                    "than the census name",
                ]),
                ("why_not_here", "re-buying a page that already served is "
                                 "exactly what the paid ledger exists to stop. "
                                 "These are repaired by reading what we hold."),
            ))),
        ))),
    ))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--dry-run-report", required=True)
    parser.add_argument("--out", default="")
    args = parser.parse_args(argv)
    doc = build(args.dry_run_report)
    if args.out:
        Path(args.out).write_text(json.dumps(doc, indent=2), encoding="utf-8")

    state, backlog = doc["current_state"], doc["backlog"]
    print("at %d of %d, gap %d" % (state["projected_total"], TARGET, state["gap"]))
    print("backlog %d -> payable %d (%s)" % (
        backlog["original_count"], backlog["payable_after_ledger"],
        dict(backlog["by_decision"])))
    print("lanes: firecrawl %d, brightdata %d, plan credits 0"
          % (doc["lanes"]["firecrawl"], doc["lanes"]["brightdata_browser"]))
    for plan in (doc["plan_a"], doc["plan_b"]):
        cost, yld = plan["cost"], plan["yield"]
        print("%-38s rows %2d  proj %6.1fc  worst %6.1fc  cap %4dc  "
              "yield %.1f (floor %.1f)"
              % (plan["name"], cost["rows"],
                 cost["projected_usd_minor_at_registry"],
                 cost["worst_case_usd_minor"], cost["safe_cap_usd_minor"],
                 yld["expected_pet_friendly_point"],
                 yld["expected_pet_friendly_conservative"]))
    print("recommendation: %s" % doc["recommendation"]["recommended"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
