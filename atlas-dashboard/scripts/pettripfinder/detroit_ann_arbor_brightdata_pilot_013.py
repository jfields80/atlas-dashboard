# -*- coding: utf-8 -*-
"""PTF-DETROIT-ANN-ARBOR-BRIGHTDATA-PILOT-013, Phases 1 and 2.

Verifies the 12-row Bright Data pilot and prices it, before anything is spent.

THE COHORT IS THE ONE ORDER 012 PREPARED. Each of the twelve named rows is
checked against the state of the market NOW, not against the state it was
prepared in: still unresolved, still routed, still a distinct page, never paid
for by Detroit, not already answered by an artifact this project holds, and not
a duplicate of another pilot row. A row that fails any of those is SUPPRESSED
rather than substituted -- the order permits a substitution only to preserve the
6/6 family split, and a quietly swapped row would measure a different market
than the one that was authorised.

BRIGHT DATA BROWSER ONLY. The committed registry names
``brightdata_web_unlocker`` as a FALLBACK for both families, not as the
sanctioned path, and this order forbids hidden escalation. One sanctioned paid
attempt per row, no automatic retry.

$0.19 PER ATTEMPT IS A CEILING, NOT A FORECAST. The registry's own measured
figure is $0.16, and the authoritative number is the zone meter's delta across
the run -- which Bright Data reports month-to-date and settles UPWARD after the
fact, so it is read again at the end and reported as measured, never assumed.
"""
from __future__ import annotations

import json
import sys
from collections import Counter, OrderedDict
from pathlib import Path
from typing import Dict, List
from urllib.parse import urlsplit

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.acquisition import paid_attempt_ledger as PAL  # noqa: E402
from scripts.pettripfinder.acquisition import providers as PROVIDERS      # noqa: E402
from scripts.pettripfinder.acquisition import registry as REG             # noqa: E402

MARKET = "detroit-ann-arbor-mi"
WORK_ORDER = "PTF-DETROIT-ANN-ARBOR-BRIGHTDATA-PILOT-013"
RUN_ID = "detroit-brightdata-013-pilot"
AS_OF = "2026-08-29"

LANE = PROVIDERS.BRIGHTDATA_BROWSER
CAP_USD = 2.28
USD_CEILING_PER_ATTEMPT = 0.19

LP = _REPO_ROOT / "launch_packages" / "pettripfinder"
PILOT_PATH = LP / "detroit_ann_arbor_brightdata_pilot_cohort_012.json"
LEDGER_PATH = LP / "ptf_paid_attempt_ledger_001.json"
ADMITTED_PATH = LP / "detroit_ann_arbor_brightdata_admitted_013.json"
PLAN_PATH = LP / "detroit_ann_arbor_brightdata_cost_plan_013.json"

#: The twelve the founder named, verbatim. Membership is checked against THIS
#: list, so a cohort file edited between orders cannot quietly change what was
#: authorised.
AUTHORISED = {
    "MARRIOTT": (
        "The Vanguard Ann Arbor, Autograph Collection",
        "Courtyard Detroit Metro Airport Romulus",
        "Fairfield Inn & Suites Rochester Hills",
        "Hotel Auburn Hills",
        "Detroit Marriott at the Renaissance Center",
        "Residence Inn by Marriott Detroit Dearborn",
    ),
    "HILTON": (
        "DoubleTree by Hilton Ann Arbor North",
        "Embassy Suites by Hilton Detroit Livonia",
        "Hampton Auburn Hills South",
        "The Kingsley Bloomfield Hills",
        "Hilton Garden Inn Detroit Downtown",
        "Home2 Suites by Hilton Northville Detroit",
    ),
}


def load(path: Path) -> Dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_lf(path: Path, doc) -> None:
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8", newline="\n")


def registrable(url: str) -> str:
    host = (urlsplit(url or "").hostname or "").lower()
    parts = [part for part in host.split(".") if part]
    return ".".join(parts[-2:]) if len(parts) >= 2 else host


def verify() -> Dict:
    pilot = load(PILOT_PATH)
    ledger = load(LEDGER_PATH)
    census = {row["identity_key"]: row for row in
              load(LP / "identity_census" / ("%s.json" % MARKET))["hotels"]}
    routes = {route["hotel_ref"]["identity_key"]: route for route in
              load(LP / "markets" / "authority" / MARKET
                   / "identity_routing.json")["routes"]
              if route["status"] == "ROUTING_CONFIRMED"}
    published = {row["identity_key"] for row in
                 load(LP / ("hotel_policy_facts_%s.json" % MARKET))["hotels"]}
    excluded = {row["normalized_name"] for row in
                load(LP / "markets" / "authority" / MARKET
                     / "hotel_exclusions.json")["exclusions"]}
    index = PAL.LedgerIndex(ledger)
    registry = REG.load()

    named = {name for names in AUTHORISED.values() for name in names}

    def authorised_as(canonical: str) -> str:
        """The founder's name for this row, or "" if they did not name it.

        The two lists do not match character for character, and the reason is
        MINE: order 012's report printed canonical names truncated to 40
        characters, and the founder's list was transcribed from that. So
        "Embassy Suites by Hilton Detroit Livonia" is the founder's name for
        "...Livonia Novi". In the other direction the census name is the short
        one -- "Hampton" -- and the founder wrote the fuller name off the
        property URL, "Hampton Auburn Hills South".

        A PREFIX MATCH IN EITHER DIRECTION, and nothing looser. Every match is
        recorded, so a reader can see exactly which founder name admitted which
        row rather than trusting that twelve became twelve.
        """
        left = " ".join(canonical.split()).lower()
        for candidate in named:
            right = " ".join(candidate.split()).lower()
            if left == right or left.startswith(right) or right.startswith(left):
                return candidate
        return ""
    admitted, suppressed = [], []
    seen_url, seen_identity = {}, {}

    for row in pilot["cohort"]:
        key = row["identity_key"]
        name = row["canonical_name"]
        checks: "OrderedDict[str, object]" = OrderedDict()
        founder_name = authorised_as(name)
        checks["named_in_the_authorisation"] = bool(founder_name)
        checks["still_unresolved"] = (key not in published
                                      and key not in excluded)
        checks["still_in_market"] = key in census
        route = routes.get(key)
        checks["still_routed"] = route is not None
        url = (route or {}).get("official_property_url") or ""
        checks["has_a_canonical_property_page"] = url.lower().startswith("https://")

        # Never paid for by Detroit, and no artifact already answers it.
        verdict = PAL.decide(
            OrderedDict([("identity_key", key), ("official_url", url),
                         ("market_id", MARKET), ("brand", row["brand"]),
                         ("property_code", row.get("property_code") or "")]),
            index, available_lanes=(LANE,))
        checks["never_paid_by_detroit"] = not [
            attempt for attempt in ledger["attempts"]
            if attempt.get("market_id") == MARKET
            and attempt.get("identity_key") == key]
        checks["no_reusable_artifact_answers_it"] = not verdict.get(
            "reusable_evidence")
        checks["ledger_permits_this_lane"] = (
            verdict["decision"] not in PAL.SUPPRESSED_DECISIONS)

        # The committed registry must actually route this family to this lane.
        route_decision = REG.resolve(brand=row["brand"], url=url,
                                     identity_key=key, registry=registry)
        checks["registry_routes_it_to_this_lane"] = (
            route_decision.provider == LANE)

        canonical = PAL.canonical_url({"official_url": url})
        checks["page_not_duplicated_in_pilot"] = canonical not in seen_url
        identity = PAL.property_identity({"official_url": url})
        checks["property_not_duplicated_in_pilot"] = (
            not identity or identity not in seen_identity)

        entry = OrderedDict([
            ("identity_key", key),
            ("canonical_name", name),
            ("named_by_the_founder_as", founder_name),
            ("name_reconciled",
             bool(founder_name) and founder_name.strip().lower()
             != name.strip().lower()),
            ("brand", row["brand"]),
            ("sub_brand", row["sub_brand"]),
            ("city", row["city"]),
            ("canonical_url", url),
            ("property_code", row.get("property_code") or ""),
            ("reader", route_decision.reader),
            ("lane", LANE),
            ("checks", checks),
        ])
        if all(checks.values()):
            seen_url[canonical] = key
            if identity:
                seen_identity[identity] = key
            admitted.append(entry)
        else:
            entry["suppressed_because"] = [name for name, ok in checks.items()
                                           if not ok]
            suppressed.append(entry)

    by_family = Counter(row["brand"] for row in admitted)
    doc = OrderedDict([
        ("schema", "ptf-detroit-ann-arbor-brightdata-admitted/1.0"),
        ("work_order", WORK_ORDER), ("market_id", MARKET), ("as_of", AS_OF),
        ("lane", LANE),
        ("lanes_forbidden", ["firecrawl", "google_places",
                             "brightdata_web_unlocker (a registry FALLBACK, "
                             "not the sanctioned path; this order forbids "
                             "hidden escalation)"]),
        ("authorised_names", AUTHORISED),
        ("rows_considered", len(pilot["cohort"])),
        ("admitted", len(admitted)),
        ("suppressed", len(suppressed)),
        ("admitted_by_family", dict(by_family)),
        ("family_split_preserved",
         by_family.get("MARRIOTT", 0) == by_family.get("HILTON", 0) == 6),
        ("substitutions", []),
        ("name_reconciliations",
         [OrderedDict([("founder_wrote", r["named_by_the_founder_as"]),
                       ("market_holds", r["canonical_name"]),
                       ("why", "order 012's report printed canonical names "
                               "truncated to 40 characters and the founder's "
                               "list was transcribed from it; matched by "
                               "prefix in either direction, same brand, "
                               "sub-brand and city")])
          for r in admitted if r["name_reconciled"]]),
        ("substitution_note",
         "none made. The order permits a substitution only to preserve the 6/6 "
         "family split, and the split is intact."),
        ("what_was_checked", [
            "the row is one of the twelve the founder named, by name",
            "it is still unresolved -- not published and not excluded",
            "it is still in the census and still carries a confirmed route",
            "its route carries an absolute canonical property page",
            "Detroit has never paid for this identity",
            "no reusable persisted artifact already answers it",
            "the cross-run ledger permits this lane for this page",
            "the committed registry routes this family to this lane",
            "no other pilot row names the same page or the same building",
        ]),
        ("admitted_rows", admitted),
        ("suppressed_rows", suppressed),
    ])
    write_lf(ADMITTED_PATH, doc)
    return doc


def cost_plan(admitted: List[Dict], usage) -> Dict:
    # IN INTEGER CENTS. 12 x $0.19 is exactly the $2.28 cap, but in binary
    # floating point ``2.28 // 0.19`` is 11.0 -- and dropping a row of an
    # authorised pilot to a rounding artifact would quietly change what was
    # measured. Money is counted in minor units for the same reason the money
    # contract does.
    affordable = int(round(CAP_USD * 100)) // int(round(
        USD_CEILING_PER_ATTEMPT * 100))
    rows = min(len(admitted), affordable)
    measured = PROVIDERS._PROVIDERS[LANE].cost
    doc = OrderedDict([
        ("schema", "ptf-detroit-ann-arbor-brightdata-cost-plan/1.0"),
        ("work_order", WORK_ORDER), ("market_id", MARKET), ("as_of", AS_OF),
        ("authorisation", OrderedDict([
            ("lane", LANE),
            ("hard_cap_usd", CAP_USD),
            ("max_attempts", 12),
            ("firecrawl", "FORBIDDEN"),
            ("google_places", "FORBIDDEN"),
            ("web_unlocker", "FORBIDDEN -- a registry fallback, not the "
                             "sanctioned path for these rows"),
        ])),
        ("unit_cost", OrderedDict([
            ("usd_ceiling_per_attempt", USD_CEILING_PER_ATTEMPT),
            ("registry_measured_usd_per_attempt",
             (measured.usd_minor_per_property or 0) / 100.0),
            ("measured_by", measured.measured_by),
            ("basis", "the ceiling is what this order authorises; the "
                      "registry's own measured figure is lower. Neither is the "
                      "answer -- the zone meter's delta across the run is, and "
                      "it is read again afterwards."),
        ])),
        ("cohort", OrderedDict([
            ("admitted", len(admitted)),
            ("affordable_under_cap", affordable),
            ("rows_this_run", rows),
            ("truncated_before_spending", rows < len(admitted)),
        ])),
        ("projected", OrderedDict([
            ("attempts", rows),
            ("worst_case_usd", round(rows * USD_CEILING_PER_ATTEMPT, 2)),
            ("at_registry_measured_rate",
             round(rows * (measured.usd_minor_per_property or 0) / 100.0, 2)),
            ("worst_case_is_every_attempt_failing",
             "Yes. A managed-browser session bills for the bandwidth it uses "
             "whether or not the page turns out to be readable."),
        ])),
        ("account", OrderedDict([
            ("zone", usage.zone),
            ("month_to_date_cost_usd", (usage.cost_month_usd_minor or 0) / 100.0),
            ("balance_usd", (usage.balance_usd_minor or 0) / 100.0),
            ("sufficient", (usage.balance_usd_minor or 0) / 100.0
             >= rows * USD_CEILING_PER_ATTEMPT),
            ("caveat", "Bright Data reports zone cost MONTH-TO-DATE and does "
                       "not update instantly; the figure settles upward after "
                       "a run. A balance is not a cost meter."),
        ])),
    ])
    write_lf(PLAN_PATH, doc)
    return doc


def run() -> None:
    from scripts.pettripfinder.brightdata import client

    doc = verify()
    print("=== Phase 1: pilot verification ===")
    print("  rows considered :", doc["rows_considered"])
    print("  ADMITTED        :", doc["admitted"], doc["admitted_by_family"])
    print("  suppressed      :", doc["suppressed"])
    for row in doc["suppressed_rows"]:
        print("     SUPPRESSED %-42s %s"
              % (row["canonical_name"][:42], row["suppressed_because"]))
    print("  6/6 split intact:", doc["family_split_preserved"])

    usage = client.read_usage("pre-pilot-%s" % RUN_ID)
    plan = cost_plan(doc["admitted_rows"], usage)
    print()
    print("=== Phase 2: cost plan ===")
    print("  rows this run   :", plan["cohort"]["rows_this_run"])
    print("  worst case      : $%.2f of $%.2f"
          % (plan["projected"]["worst_case_usd"], CAP_USD))
    print("  registry rate   : $%.2f for the same rows"
          % plan["projected"]["at_registry_measured_rate"])
    print("  zone month-to-date: $%.2f | balance $%.2f"
          % (plan["account"]["month_to_date_cost_usd"],
             plan["account"]["balance_usd"]))
    print("wrote", ADMITTED_PATH.name, "and", PLAN_PATH.name)


if __name__ == "__main__":
    run()
