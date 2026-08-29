# -*- coding: utf-8 -*-
"""PTF-INDIANAPOLIS-PLACES-BROADER-RECOVERY-010, part 2 -- what the URLs are worth.

Discovery bought routes, not policies. This works out, offline and for nothing,
what those routes change: how many identities Indianapolis can now point a lane
at, which lane the committed registry picks for each, how many already have a
policy answer we own, and how many would genuinely need buying.

It calls no provider and it does not run acquisition. It ends at a cohort a
human authorises or does not.

WHY THE PET-FRIENDLY NUMBER MOVES SO MUCH LESS THAN THE ROUTING NUMBER
----------------------------------------------------------------------
A recovered URL makes a hotel ASKABLE. It does not make it pet-friendly, and it
does not make it publishable. Indianapolis's own record is the only honest
multiplier: 79 identities were attempted for policy and 24 became promoted
pet-friendly profiles. That is 30.4%, and it already includes every way an
attempt can end short -- a page that refuses pets, a page that never states a
policy, a lane that cannot reach the brand, an identity that fails its gate.
"""
from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, OrderedDict
from pathlib import Path
from typing import Dict, List

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.acquisition import paid_attempt_ledger as PAL       # noqa: E402
from scripts.pettripfinder.acquisition import registry as REGISTRY             # noqa: E402
from scripts.pettripfinder.acquisition import cohort_cost_plan as CP           # noqa: E402
from scripts.pettripfinder.acquisition.market_paid_acquisition import family_of  # noqa: E402
from scripts.pettripfinder.brightdata import corpus as CORPUS                  # noqa: E402

LP = _REPO_ROOT / "launch_packages" / "pettripfinder"
SCHEMA = "ptf-market-routing-gain/1.0"
WORK_ORDER = "PTF-INDIANAPOLIS-PLACES-BROADER-RECOVERY-010"
MARKET = "indianapolis-in"
TARGET = 50


def _load(name):
    return json.loads((LP / name).read_text(encoding="utf-8"))


def recovered_urls() -> List[Dict]:
    """Every official URL the two Places runs produced, under the CURRENT rule.

    The 25-row sample was bound twice: nine under the rule as it stood, and
    thirteen after PTF-INDIANAPOLIS-PLACES-NAME-NORMALIZATION-009 taught the
    binder to compare identity instead of presentation. The thirteen are what
    the market actually has, so the four the ledger recorded as unbound are
    counted here from the 009 replay rather than from the ledger row.
    """
    out: Dict[str, Dict] = {}
    replay = _load("indianapolis_in_name_normalization_009.json")
    for row in replay["rows"]:
        if row["new_decision"] == "BOUND" and row["url"]:
            out[row["identity_key"]] = OrderedDict((
                ("identity_key", row["identity_key"]),
                ("url", row["url"]),
                ("bind_method", row["final_binding_method"]),
                ("source", "008+009 qualification sample")))
    broader = _load("indianapolis_in_places_broader_010.json")
    for row in broader["official_property_urls_recovered"]:
        out[row["identity_key"]] = OrderedDict((
            ("identity_key", row["identity_key"]), ("url", row["url"]),
            ("bind_method", row["bind_method"]),
            ("source", "010 broader cohort")))
    return sorted(out.values(), key=lambda r: r["identity_key"])


def build() -> Dict:
    census = _load("identity_census/indianapolis-in.json")
    package = _load("hotel_policy_facts_indianapolis-in.json")
    exclusions = _load("markets/authority/indianapolis-in/hotel_exclusions.json")
    merged = _load("indianapolis_in_acquisition_merged_promotion_003.json")
    paid_ledger = _load("ptf_paid_attempt_ledger_001.json")
    inventory = _load("indianapolis_in_url_recovery_report_006.json")

    by_key = {h["identity_key"]: h for h in census["hotels"]}
    key_map = census["promotion"]["key_map"]
    signed = ({h["identity_key"] for h in package["hotels"]}
              | {e["normalized_name"] for e in exclusions["exclusions"]})
    attempted = {key_map.get(r["identity_key"], r["identity_key"])
                 for r in merged["results"]}
    unroutable = {r["identity_key"]
                  for r in inventory["phase_1_unroutable_inventory"]["rows"]}

    recovered = recovered_urls()
    newly_routed = [r for r in recovered if r["identity_key"] in unroutable]

    # Route each newly routed identity through the committed registry.
    cohort: List[Dict] = []
    for row in newly_routed:
        hotel = by_key.get(row["identity_key"], {})
        brand = CORPUS.brand_of(row["url"])
        route = REGISTRY.resolve(brand=brand, url=row["url"],
                                 identity_key=row["identity_key"])
        cohort.append(OrderedDict((
            ("identity_key", row["identity_key"]),
            ("canonical_name", hotel.get("canonical_name", "")),
            ("source_url", row["url"]), ("brand", brand),
            ("family", family_of(brand)), ("provider", route.provider),
            ("street", hotel.get("address", "")),
            ("postal_code", hotel.get("postal_code", "")),
            ("telephone", hotel.get("phone", "")),
            ("bind_method", row["bind_method"]), ("basis", row["source"]),
        )))

    # Does the paid ledger already own an answer for any of them?
    payable, suppressed = PAL.suppress(cohort, paid_ledger)
    reusable = [r for r in suppressed
                if r["paid_history"].get("reusable_evidence")]

    routing_before = len(census["hotels"]) - len(unroutable)
    routing_after = routing_before + len(newly_routed)

    promoted = len(package["hotels"])
    attempted_count = len({r["identity_key"] for r in merged["results"]})
    pf_rate = promoted / attempted_count if attempted_count else 0.0
    expected_new = int(round(len(payable) * pf_rate))

    lanes = Counter(r["provider"] for r in payable)
    firecrawl = [r for r in payable if r["provider"] == "firecrawl"]
    brightdata = [r for r in payable if r["provider"].startswith("brightdata")]

    plan = CP.build({"cohort": [dict(r, family=family_of(r["brand"]))
                                for r in payable]},
                    _load("indianapolis_in_market_acquisition_pass1_002.json"),
                    authorised_cap_usd=0.0, paid_ledger=paid_ledger,
                    available_lanes=("brightdata_browser",
                                     "brightdata_web_unlocker", "firecrawl"))

    return OrderedDict((
        ("schema", SCHEMA), ("market_id", MARKET), ("work_order", WORK_ORDER),
        ("provider_calls", 0), ("usd_spent", 0.0),
        ("no_policy_acquisition_ran", True),
        ("routing", OrderedDict((
            ("census", len(census["hotels"])),
            ("routing_before", routing_before),
            ("newly_routed", len(newly_routed)),
            ("routing_after", routing_after),
            ("url_less_before", len(unroutable)),
            ("url_less_after", len(unroutable) - len(newly_routed)),
        ))),
        ("newly_routed_lane_split", OrderedDict((
            ("firecrawl", lanes.get("firecrawl", 0)),
            ("brightdata_browser", lanes.get("brightdata_browser", 0)),
            ("brightdata_web_unlocker", lanes.get("brightdata_web_unlocker", 0)),
            ("other", sum(v for k, v in lanes.items()
                          if k not in ("firecrawl", "brightdata_browser",
                                       "brightdata_web_unlocker"))),
        ))),
        ("policy_evidence", OrderedDict((
            ("already_reusable_no_buy_needed", len(reusable)),
            ("suppressed_by_paid_history", len(suppressed)),
            ("genuinely_need_acquisition", len(payable)),
            ("reusable_rows", [r["identity_key"] for r in reusable]),
        ))),
        ("target_50", OrderedDict((
            ("current_promoted_pet_friendly", promoted),
            ("target", TARGET), ("gap", TARGET - promoted),
            ("observed_pet_friendly_rate", round(pf_rate, 4)),
            ("rate_basis", "%d identities attempted for policy produced %d "
                           "promoted pet-friendly profiles" % (attempted_count, promoted)),
            ("acquirable_cohort", len(payable)),
            ("expected_new_pet_friendly", expected_new),
            ("expected_total", promoted + expected_new),
            ("remaining_gap_after", max(0, TARGET - promoted - expected_new)),
            ("reaches_50", promoted + expected_new >= TARGET),
        ))),
        ("minimum_next_acquisition_cohort", OrderedDict((
            ("this_is_not_an_authorization", True),
            ("cohort_size", plan["cohort_size"]),
            ("cohort_by_provider", plan["cohort_by_provider"]),
            ("cohort_by_family", plan["cohort_by_family"]),
            ("firecrawl_properties", len(firecrawl)),
            ("firecrawl_credits", plan["expected_firecrawl_credits"]),
            ("brightdata_properties", len(brightdata)),
            ("dollar_billed_properties", plan["dollar_billed_properties"]),
            ("credit_billed_properties", plan["credit_billed_properties"]),
            ("measured_unit_usd_minor", plan["measured_unit_usd_minor"]),
            ("expected_brightdata_usd_minor", plan["expected_brightdata_usd_minor"]),
            ("projection", plan["projection"]),
            ("safe_cap_usd_minor",
             int(plan["projection"]["worst_case_usd_minor"]) + 15),
            ("cheapest_valid_lane_note",
             "the lane on every row is the committed registry's own answer for "
             "that brand and host; nothing here re-routes a property to a "
             "cheaper lane than the registry allows"),
            ("rows", payable),
        ))),
    ))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="")
    args = parser.parse_args(argv)
    report = build()
    if args.out:
        Path(args.out).write_text(json.dumps(report, indent=2), encoding="utf-8")
    routing = report["routing"]
    print("routing      %d -> %d  (+%d)   url-less %d -> %d"
          % (routing["routing_before"], routing["routing_after"],
             routing["newly_routed"], routing["url_less_before"],
             routing["url_less_after"]))
    print("lane split   %s" % dict(report["newly_routed_lane_split"]))
    evidence = report["policy_evidence"]
    print("evidence     reusable %d, need acquisition %d"
          % (evidence["already_reusable_no_buy_needed"],
             evidence["genuinely_need_acquisition"]))
    target = report["target_50"]
    print("target 50    %d + %d expected = %d (gap %d)"
          % (target["current_promoted_pet_friendly"],
             target["expected_new_pet_friendly"], target["expected_total"],
             target["remaining_gap_after"]))
    plan = report["minimum_next_acquisition_cohort"]
    print("next cohort  %d rows | firecrawl %d (%s credits) | brightdata %d"
          % (plan["cohort_size"], plan["firecrawl_properties"],
             plan["firecrawl_credits"], plan["brightdata_properties"]))
    print("             projection %s, safe cap %sc"
          % (plan["expected_brightdata_usd_minor"], plan["safe_cap_usd_minor"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
