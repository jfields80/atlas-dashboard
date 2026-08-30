# -*- coding: utf-8 -*-
"""PTF-DETROIT-ANN-ARBOR-MARRIOTT-SCALE-015, Phases 1 to 4.

Rebuilds the remaining Marriott cohort from current state, repairs the one
legacy route if it can be done honestly, and prices the run. NOTHING IS SPENT
HERE.

THE COUNT IS REBUILT, NOT INHERITED. Order 014 reported 18 rows remaining; that
was true when it ran, and this order checks it again against the committed
authority rather than trusting it. Every row must be a Detroit member,
unresolved, Marriott, routed, never successfully paid for, and absent from both
pilots -- each checked, each recorded.

THE LEGACY ROUTE IS REPAIRED FROM EVIDENCE OR NOT AT ALL. Pilots 013 and 014
proved Marriott's ``/hotels/travel/`` shape fails 0/2 while ``/en-us/hotels/``
succeeds 11/11, so paying Bright Data against a known-bad route would be buying
a failure at list price. But a URL is an identity claim: this order will not
compose one from a slug and hope. It rewrites a legacy URL only when the
property CODE inside it is already committed and the rewrite preserves that
code, and it leaves the row ROUTING_REPAIR_REQUIRED otherwise.
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter, OrderedDict
from pathlib import Path
from typing import Dict, List, Optional
from urllib.parse import urlsplit

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.acquisition import paid_attempt_ledger as PAL  # noqa: E402
from scripts.pettripfinder.acquisition import providers as PROVIDERS      # noqa: E402
from scripts.pettripfinder.acquisition import registry as REG             # noqa: E402
from scripts.pettripfinder.brightdata import policy_surface as PS         # noqa: E402
from scripts.pettripfinder import (                                       # noqa: E402
    detroit_ann_arbor_brightdata_pilot_014 as P14)

MARKET = "detroit-ann-arbor-mi"
WORK_ORDER = "PTF-DETROIT-ANN-ARBOR-MARRIOTT-SCALE-015"
RUN_ID = "detroit-brightdata-015-marriott-scale"
AS_OF = "2026-08-29"
FAMILY = "MARRIOTT"

LANE = PROVIDERS.BRIGHTDATA_BROWSER
CAP_USD = 3.25
MAX_ROWS = 18
#: Measured across pilots 013 and 014: $4.87 over 32 billed attempts. The
#: order's own range is $0.152-$0.165; the upper end is used to size, so the
#: cap is enforced against the least favourable measurement rather than the
#: most flattering one.
USD_PER_ATTEMPT = 0.165

LEGACY_SHAPE = "marriott:/hotels/travel/"
MODERN_PREFIX = "https://www.marriott.com/en-us/hotels/"

LP = _REPO_ROOT / "launch_packages" / "pettripfinder"
LEDGER_PATH = LP / "ptf_paid_attempt_ledger_001.json"
ROUTING_PATH = LP / "markets" / "authority" / MARKET / "identity_routing.json"
ADMITTED_PATH = LP / "detroit_ann_arbor_marriott_admitted_015.json"
PLAN_PATH = LP / "detroit_ann_arbor_marriott_cost_plan_015.json"
REPAIR_PATH = LP / "detroit_ann_arbor_marriott_route_repair_015.json"

PILOT_CLASSIFICATIONS = (
    LP / "detroit_ann_arbor_brightdata_classification_013.json",
    LP / "detroit_ann_arbor_brightdata_classification_014.json",
)


def load(path: Path) -> Dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_lf(path: Path, doc) -> None:
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8", newline="\n")


def registrable(url: str) -> str:
    return P14.registrable(url)


def legacy_repair(url: str, expected_code: str) -> Optional[Dict]:
    """A modern URL for a legacy one, ONLY when the code carries across.

    ``/hotels/travel/<code>-<slug>`` and ``/en-us/hotels/<code>-<slug>/overview/``
    are the same property expressed in two of Marriott's own templates, and the
    property CODE is the brand's own key for the building. Rewriting is safe
    exactly when the legacy URL already states the committed code -- then the
    new URL is not a guess, it is the same identity in the current shape, and
    ``page_health`` will still verify the code on the page that answers.

    Returns None when the code is absent or does not match, because then the
    rewrite would be an invention.
    """
    match = re.search(r"/hotels/travel/([a-z0-9]{4,7})-([a-z0-9-]+)", url or "",
                      re.IGNORECASE)
    if not match:
        return None
    code, slug = match.group(1).lower(), match.group(2).strip("/").lower()
    if not expected_code or code != expected_code.lower():
        return None
    repaired = "%s%s-%s/overview/" % (MODERN_PREFIX, code, slug)
    if PS.property_code(repaired, FAMILY).lower() != code:
        return None
    return OrderedDict([
        ("was", url), ("now", repaired), ("property_code", code),
        ("basis", "the legacy URL already states the committed property code "
                  "%r, and the rewrite preserves it. The brand's own key for "
                  "the building is unchanged, so this is the same identity in "
                  "Marriott's current template -- not a composed URL. "
                  "page_health still verifies the code on whatever page "
                  "answers." % code),
    ])


def build() -> Dict:
    ledger = load(LEDGER_PATH)
    census = {row["identity_key"]: row for row in
              load(LP / "identity_census" / ("%s.json" % MARKET))["hotels"]}
    routing = load(ROUTING_PATH)
    published = {row["identity_key"] for row in
                 load(LP / ("hotel_policy_facts_%s.json" % MARKET))["hotels"]}
    excluded = {row["normalized_name"] for row in
                load(LP / "markets" / "authority" / MARKET
                     / "hotel_exclusions.json")["exclusions"]}
    index = PAL.LedgerIndex(ledger)
    registry = REG.load()

    pilot_keys = set()
    for path in PILOT_CLASSIFICATIONS:
        for row in load(path)["results"]:
            pilot_keys.add(row["identity_key"])

    # Any identity Detroit has ever PAID for on any lane, and separately those
    # a paid attempt actually ANSWERED. Both matter and they are not the same:
    # a page that was paid for and failed is not "already answered".
    paid_any = {attempt["identity_key"] for attempt in ledger["attempts"]
                if attempt.get("market_id") == MARKET}
    paid_successfully = {attempt["identity_key"] for attempt in ledger["attempts"]
                         if attempt.get("market_id") == MARKET
                         and attempt.get("publication_grade")}

    starting, admitted = [], []
    suppressed_answered, suppressed_paid, suppressed_pilot = [], [], []
    repairs, repair_required = [], []

    for route in routing["routes"]:
        if route["status"] != "ROUTING_CONFIRMED":
            continue
        key = route["hotel_ref"]["identity_key"]
        url = route.get("official_property_url") or ""
        if registrable(url) != "marriott.com":
            continue
        row = census.get(key) or {}
        starting.append(key)

        if key in published or key in excluded:
            suppressed_answered.append(OrderedDict([
                ("identity_key", key),
                ("canonical_name", row.get("canonical_name") or ""),
                ("why", "already answered by Detroit authority")]))
            continue
        if key in paid_successfully:
            suppressed_paid.append(OrderedDict([
                ("identity_key", key),
                ("canonical_name", row.get("canonical_name") or ""),
                ("why", "a prior paid attempt already acquired publication-"
                        "grade evidence for this identity")]))
            continue
        if key in pilot_keys or key in paid_any:
            suppressed_pilot.append(OrderedDict([
                ("identity_key", key),
                ("canonical_name", row.get("canonical_name") or ""),
                ("why", "attempted in pilot 013 or 014; this order buys only "
                        "what those pilots did not")]))
            continue

        shape = P14.url_shape(url)
        repair = None
        if shape == LEGACY_SHAPE:
            repair = legacy_repair(url, route.get("property_code") or "")
            if repair is None:
                repair_required.append(OrderedDict([
                    ("identity_key", key),
                    ("canonical_name", row.get("canonical_name") or ""),
                    ("routed_url", url),
                    ("why", "the routed URL uses the legacy /hotels/travel/ "
                            "template, which pilots 013 and 014 measured at "
                            "0/2, and it cannot be rewritten from the "
                            "committed property code alone. Left "
                            "ROUTING_REPAIR_REQUIRED and NOT paid for: buying "
                            "a known-bad route is buying a failure."),
                ]))
                continue
            repair["identity_key"] = key
            repair["canonical_name"] = row.get("canonical_name") or ""
            repairs.append(repair)
            url = repair["now"]
            shape = P14.url_shape(url)

        checks = OrderedDict([
            ("detroit_market_member", key in census),
            ("unresolved", True),
            ("marriott_family", True),
            ("routed", bool(url)),
            ("canonical_property_page", url.lower().startswith("https://")),
            ("not_on_a_failing_template", shape != LEGACY_SHAPE),
        ])
        verdict = PAL.decide(
            OrderedDict([("identity_key", key), ("official_url", url),
                         ("market_id", MARKET), ("brand", FAMILY),
                         ("property_code", route.get("property_code") or "")]),
            index, available_lanes=(LANE,))
        checks["ledger_permits_this_lane"] = (
            verdict["decision"] not in PAL.SUPPRESSED_DECISIONS)
        checks["no_reusable_artifact_answers_it"] = not verdict.get(
            "reusable_evidence")
        decision = REG.resolve(brand=FAMILY, url=url, identity_key=key,
                               registry=registry)
        checks["registry_routes_it_to_this_lane"] = decision.provider == LANE

        entry = OrderedDict([
            ("identity_key", key),
            ("canonical_name", row.get("canonical_name") or ""),
            ("brand", FAMILY),
            ("sub_brand", P14.sub_brand_of(url, FAMILY,
                                           row.get("canonical_name") or "")),
            ("city", row.get("city") or ""),
            ("canonical_url", url),
            ("url_shape", shape),
            ("property_code", route.get("property_code") or ""),
            ("expected_property_identity", OrderedDict([
                ("address", row.get("address") or ""),
                ("postal_code", row.get("postal_code") or ""),
                ("phone", row.get("phone") or ""),
                ("city", row.get("city") or ""),
            ])),
            ("reader", decision.reader),
            ("route_repaired", bool(repair)),
            ("checks", checks),
        ])
        if all(checks.values()):
            admitted.append(entry)
        else:
            entry["rejected_because"] = [name for name, ok in checks.items()
                                         if not ok]
            repair_required.append(entry)

    # One page, one buy -- inside this cohort as well as against history.
    seen_url, seen_identity, deduped = {}, {}, []
    for entry in admitted:
        canonical = PAL.canonical_url({"official_url": entry["canonical_url"]})
        identity = PAL.property_identity(
            {"official_url": entry["canonical_url"]})
        if canonical in seen_url or (identity and identity in seen_identity):
            entry["rejected_because"] = ["duplicate page or building inside "
                                         "the cohort"]
            repair_required.append(entry)
            continue
        seen_url[canonical] = entry["identity_key"]
        if identity:
            seen_identity[identity] = entry["identity_key"]
        deduped.append(entry)
    admitted = deduped

    doc = OrderedDict([
        ("schema", "ptf-detroit-ann-arbor-marriott-admitted/1.0"),
        ("work_order", WORK_ORDER), ("market_id", MARKET), ("as_of", AS_OF),
        ("run_id", RUN_ID), ("lane", LANE), ("family", FAMILY),
        ("scope", "MARRIOTT ONLY. Hilton and the 43 registry-deferred rows are "
                  "out of scope and are not touched."),
        ("rebuilt_from_current_state",
         "order 014 reported 18 remaining; that count is re-derived here from "
         "the committed authority rather than inherited."),
        ("starting_marriott_routed", len(starting)),
        ("suppressed_already_answered", len(suppressed_answered)),
        ("suppressed_already_paid_successfully", len(suppressed_paid)),
        ("suppressed_attempted_in_a_pilot", len(suppressed_pilot)),
        ("routing_repair_required", len(repair_required)),
        ("routes_repaired_at_zero_cost", len(repairs)),
        ("genuinely_payable", len(admitted)),
        ("within_authorised_maximum", len(admitted) <= MAX_ROWS),
        ("diversity", OrderedDict([
            ("sub_brands", sorted({row["sub_brand"] for row in admitted})),
            ("cities", sorted({row["city"] for row in admitted if row["city"]})),
            ("url_shapes", sorted({row["url_shape"] for row in admitted})),
        ])),
        ("repairs", repairs),
        ("suppressed_already_answered_rows", suppressed_answered),
        ("suppressed_already_paid_rows", suppressed_paid),
        ("suppressed_pilot_rows", suppressed_pilot),
        ("routing_repair_required_rows", repair_required),
        ("admitted_rows", admitted),
    ])
    write_lf(ADMITTED_PATH, doc)
    write_lf(REPAIR_PATH, OrderedDict([
        ("schema", "ptf-detroit-ann-arbor-marriott-route-repair/1.0"),
        ("work_order", WORK_ORDER), ("market_id", MARKET), ("as_of", AS_OF),
        ("provider_calls", 0), ("spend_usd", 0.0),
        ("defect", "pilots 013 and 014 measured Marriott at 0/2 on the legacy "
                   "/hotels/travel/ template and 11/11 on /en-us/hotels/. A "
                   "row still routed to the legacy shape is a stale ROUTE, not "
                   "an unreachable hotel."),
        ("rule", "rewrite ONLY when the legacy URL already states the "
                 "committed property code and the rewrite preserves it. "
                 "Otherwise leave ROUTING_REPAIR_REQUIRED -- a URL is an "
                 "identity claim and this order will not compose one."),
        ("repaired", len(repairs)),
        ("left_for_repair", len(repair_required)),
        ("repairs", repairs),
        ("left_for_repair_rows", repair_required),
    ]))
    return doc


def cost_plan(admitted: List[Dict], usage) -> Dict:
    affordable = int(round(CAP_USD * 100)) // int(round(USD_PER_ATTEMPT * 100))
    # THE BALANCE BINDS TOO, and for a worse reason than the cap. A cap
    # reached simply stops the run; a prepaid balance exhausted mid-run makes
    # the REMAINING attempts fail on authentication, which does not just halt
    # the measurement -- it contaminates it with failures that say nothing
    # about the property. Sized on the least favourable rate, as the cap is.
    balance_usd = (usage.balance_usd_minor or 0) / 100.0
    balance_affordable = int(balance_usd * 100) // int(round(
        USD_PER_ATTEMPT * 100))
    rows = min(len(admitted), affordable, balance_affordable, MAX_ROWS)
    binding = ("the vendor balance" if balance_affordable < min(affordable,
                                                                MAX_ROWS,
                                                                len(admitted))
               else "the authorised cap" if affordable < min(MAX_ROWS,
                                                             len(admitted))
               else "the admitted cohort")
    doc = OrderedDict([
        ("schema", "ptf-detroit-ann-arbor-marriott-cost-plan/1.0"),
        ("work_order", WORK_ORDER), ("market_id", MARKET), ("as_of", AS_OF),
        ("authorisation", OrderedDict([
            ("lane", LANE), ("family", FAMILY),
            ("hard_cap_usd", CAP_USD), ("max_rows", MAX_ROWS),
            ("firecrawl", "FORBIDDEN"), ("google_places", "FORBIDDEN"),
            ("web_unlocker", "FORBIDDEN -- no escalation"),
            ("hilton", "OUT OF SCOPE"), ("other_deferred", "OUT OF SCOPE"),
        ])),
        ("unit_cost", OrderedDict([
            ("usd_per_attempt", USD_PER_ATTEMPT),
            ("basis", "MEASURED across pilots 013 and 014: $4.87 over 32 "
                      "billed attempts is $0.152. The upper end of the order's "
                      "range, $0.165, is used to SIZE, so the cap binds "
                      "against the least favourable measurement."),
        ])),
        ("cohort", OrderedDict([
            ("admitted", len(admitted)),
            ("affordable_under_cap", affordable),
            ("rows_this_run", rows),
            ("truncated_before_spending", rows < len(admitted)),
            ("affordable_under_balance", balance_affordable),
            ("binding_constraint", binding),
        ])),
        ("projected", OrderedDict([
            ("attempts", rows),
            ("worst_case_usd", round(rows * USD_PER_ATTEMPT, 2)),
            ("margin_under_cap", round(CAP_USD - rows * USD_PER_ATTEMPT, 2)),
            ("margin_under_balance", round(balance_usd
                                           - rows * USD_PER_ATTEMPT, 2)),
            ("at_the_measured_rate", round(rows * 0.152, 2)),
        ])),
        ("account", OrderedDict([
            ("zone", usage.zone),
            ("month_to_date_cost_usd",
             (usage.cost_month_usd_minor or 0) / 100.0),
            ("balance_usd", (usage.balance_usd_minor or 0) / 100.0),
            ("sufficient", (usage.balance_usd_minor or 0) / 100.0
             >= rows * USD_PER_ATTEMPT),
            ("caveat", "zone cost is MONTH-TO-DATE and settles upward; a "
                       "balance is not a cost meter"),
        ])),
        ("concurrency", OrderedDict([
            ("exclusive_run_lock", "REQUIRED before the first paid call"),
            ("one_runner_only", True),
            ("if_stdout_goes_quiet", "DO NOT RELAUNCH. Watch the process, the "
                                     "lock and the ledger's growth. A running "
                                     "process is never stalled merely because "
                                     "it is quiet -- that reading cost order "
                                     "013 its cap."),
        ])),
    ])
    write_lf(PLAN_PATH, doc)
    return doc


def run() -> None:
    from scripts.pettripfinder.brightdata import client

    doc = build()
    print("=== Phase 1: Marriott cohort rebuilt from current state ===")
    print("  starting Marriott routed        :", doc["starting_marriott_routed"])
    print("  suppressed, already answered    :",
          doc["suppressed_already_answered"])
    print("  suppressed, already paid + won  :",
          doc["suppressed_already_paid_successfully"])
    print("  suppressed, attempted in a pilot:",
          doc["suppressed_attempted_in_a_pilot"])
    print("  routing repair required         :",
          doc["routing_repair_required"])
    print("  GENUINELY PAYABLE               :", doc["genuinely_payable"],
          "(<= %d: %s)" % (MAX_ROWS, doc["within_authorised_maximum"]))
    print()
    print("=== Phase 2: zero-cost legacy route repair ===")
    print("  repaired at $0 :", doc["routes_repaired_at_zero_cost"])
    for repair in doc["repairs"]:
        print("     %s" % repair["canonical_name"])
        print("       was %s" % repair["was"])
        print("       now %s" % repair["now"])
    for row in doc["routing_repair_required_rows"]:
        print("     LEFT ROUTING_REPAIR_REQUIRED: %s"
              % row.get("canonical_name"))

    usage = client.read_usage("pre-%s" % RUN_ID)
    plan = cost_plan(doc["admitted_rows"], usage)
    print()
    print("=== Phase 4: cost gate ===")
    print("  rows this run :", plan["cohort"]["rows_this_run"],
          "(truncated)" if plan["cohort"]["truncated_before_spending"] else "")
    print("  worst case    : $%.2f of $%.2f (margin $%.2f)"
          % (plan["projected"]["worst_case_usd"], CAP_USD,
             plan["projected"]["margin_under_cap"]))
    print("  at measured   : $%.2f" % plan["projected"]["at_the_measured_rate"])
    print("  zone $%.2f | balance $%.2f"
          % (plan["account"]["month_to_date_cost_usd"],
             plan["account"]["balance_usd"]))
    print("wrote", ADMITTED_PATH.name, PLAN_PATH.name, REPAIR_PATH.name)


if __name__ == "__main__":
    run()
