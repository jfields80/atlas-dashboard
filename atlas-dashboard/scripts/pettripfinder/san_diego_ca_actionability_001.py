"""PTF-SAN-DIEGO-CA-HARDENED-SOURCE-READY-001 -- Phases 21 and 26: actionability and coverage readiness.

UNRESOLVED IS NOT ACTIONABLE. A large, bounded, fully-explained unresolved cohort is allowed; what is NOT
allowed is a row this order could still have resolved with an authorized lane and did not. So EVERY unresolved
ROW (not every disposition) is assigned exactly one class, from its own hold reason, its own route and its own
brand family:

  ACTIONABLE_NOW              an authorized lane remains untried for this row
  AUTHORIZED_ROUTER_EXHAUSTED every rung the committed route table and the supported browser open for this row
                              was exercised, and the row's own evidence is what it is
  REQUIRES_NEW_PROVIDER       only a provider this order has no authorization for could reach it
  REQUIRES_NEW_SPEND          only new paid capacity could reach it
  REQUIRES_FOUNDER            only a founder decision (a shared document, a business rule) can move it

WHY THIS IS PER-ROW. The port this module replaced bucketed whole dispositions, so a row the router had just
routed and no lane had yet attempted ("routed but no acquisition lane in this order attempted the page yet")
was counted AUTHORIZED_ROUTER_EXHAUSTED with every other ROUTING_HOLD. That is exactly the row the order forbids
hiding. Here the reason text decides, and an unrecognised reason falls to ACTIONABLE_NOW -- never the other way.

COVERAGE READY is then decided mechanically: YES only when nothing is actionable and nothing needs a founder or
new spend to reach; FOUNDER DECISION when nothing is actionable but a material cohort is reachable only through
new spend or a founder ruling; NO while anything is actionable.

Reads only committed reports. Nothing fetches, spends, registers, authorizes or deploys.

Output:
  launch_packages/pettripfinder/markets/reports/san_diego_ca_actionability_001.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter, OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

WORK_ORDER = "PTF-SAN-DIEGO-CA-HARDENED-SOURCE-READY-001"
MARKET_ID = "san-diego-ca"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
R = os.path.join(PKG, "markets", "reports")
STAGING = os.path.join(PKG, "markets", "staging", MARKET_ID, "raw_captures")
OUT = os.path.join(R, "san_diego_ca_actionability_001.json")

ACTIONABLE_NOW = "ACTIONABLE_NOW"
EXHAUSTED = "AUTHORIZED_ROUTER_EXHAUSTED"
NEW_PROVIDER = "REQUIRES_NEW_PROVIDER"
NEW_SPEND = "REQUIRES_NEW_SPEND"
FOUNDER = "REQUIRES_FOUNDER"
CLASSES = (ACTIONABLE_NOW, EXHAUSTED, NEW_PROVIDER, NEW_SPEND, FOUNDER)

#: Places route discovery is the ONLY lane that finds a website for a row no brand roster, bureau or map links.
#: Its website field is an Enterprise-SKU field; the month's free allowance was already consumed by other markets
#: (measured in this order), so running it is NEW SPEND. The allowance renews on 2026-10-01.
PLACES_SPEND = ("no first-party route exists in any authorized lane (brand inventory, three bureau rosters, the "
                "map, the brand's own area lists); the only lane that finds one is Places website discovery, an "
                "Enterprise-SKU field whose free monthly allowance is already consumed -- new spend (the allowance "
                "renews 2026-10-01)")


def _load(path, default=None):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def classify(row, route):
    """(class, why) for one unresolved clean-authority row."""
    disp = row["disposition"]
    why = row.get("hold_reason") or ""
    family = (route or {}).get("brand_family") or ""
    state = (route or {}).get("routing_state") or ""
    if disp == "BROWSER_CAPTURE_NEEDED":
        return ACTIONABLE_NOW, "a brand page the attended browser has not yet read"
    if disp == "ROUTING_HOLD":
        if why.startswith("routed but no acquisition lane"):
            return ACTIONABLE_NOW, "routed, and no lane has attempted the route yet"
        if family == "ESA":
            return EXHAUSTED, ("Extended Stay America: the brand's own city page answered the attended browser "
                               "with a DataDome CAPTCHA (never solved) and its sitemap refused the plain client; no "
                               "route can be read for any ESA row in this market")
        if family == "MOTEL6":
            return EXHAUSTED, ("Motel 6: every Motel 6 property page this order read states only an amenity chip "
                               "(never a policy), so no route for this row could yield a publishable statement; "
                               "its route is also unknown -- " + PLACES_SPEND)
        if why.startswith(("RETIRED_BRAND_ROUTE", "the route the census carries served an error page",
                           "the brand's own property-code route lands", "the census routes this identity to a brand HOME")):
            return NEW_SPEND, why.split(" (")[0] + "; " + PLACES_SPEND
        if why.startswith("routing state") or "NO_OFFICIAL_WEB_PRESENCE" in why:
            return NEW_SPEND, PLACES_SPEND
        return ACTIONABLE_NOW, "unrecognised routing reason (never silently exhausted): " + why[:160]
    if disp == "ACCESS_BLOCKED":
        return EXHAUSTED, why[:300]
    if disp == "SOURCE_SILENT":
        return EXHAUSTED, ("the property's own page served, bound, and states no operative pet policy; silence "
                           "is never a refusal, and only the operator publishing a policy changes it")
    if disp in ("EVIDENCE_HOLD", "NEGATION_HOLD"):
        if "ROUTE_DOMAIN_CONFLICT" in why:
            return FOUNDER, ("two first-party routes for one premises; which one the package cites is a routing "
                             "ruling -- " + why[:200])
        return EXHAUSTED, ("the first-party evidence was read and is not publishable as stated (conditional, "
                           "fee/weight-only, chip-only, or the shared reader disagrees); no further acquisition "
                           "changes the page's own wording -- " + why[:200])
    if disp == "IDENTITY_MISMATCH_HOLD":
        if why.startswith("SAME PREMISES, TWO IDENTITIES"):
            return FOUNDER, ("a dual-brand building is TWO hotels, each proved by its own brand code and page; "
                             "publishing them needs a same_campus_distinct_entity row in the SHARED "
                             "identity_resolutions.json, which this order may not write")
        return EXHAUSTED, why[:300]
    return ACTIONABLE_NOW, "unrecognised disposition (never silently exhausted): " + disp


def build():
    clean = _load(os.path.join(R, "san_diego_ca_clean_authority_001.json"), {}) or {}
    routing = _load(os.path.join(R, "san_diego_ca_routing_001.json"), {}) or {}
    browser = _load(os.path.join(R, "san_diego_ca_browser_lane_001.json"), {}) or {}
    recon = _load(os.path.join(R, "san_diego_ca_competitor_reconciliation_001.json"), {}) or {}
    shadow = _load(os.path.join(R, "san_diego_ca_shadow_package_001.json"), {}) or {}
    by_route = {r["identity_key"]: r for r in routing.get("routes", [])}

    rows = clean.get("rows", [])
    unresolved = [r for r in rows if r["disposition"] not in ("CLEAN_PET_FRIENDLY", "CLEAN_VERIFIED_NO_PETS")]
    per_row = []
    for r in unresolved:
        cls, why = classify(r, by_route.get(r["identity_key"]))
        rt = by_route.get(r["identity_key"]) or {}
        per_row.append(OrderedDict([
            ("identity_key", r["identity_key"]), ("canonical_name", r["canonical_name"]),
            ("corridor", r.get("corridor", "")), ("brand_family", rt.get("brand_family") or ""),
            ("disposition", r["disposition"]), ("actionability", cls), ("why", why),
        ]))
    per_row.sort(key=lambda x: (x["actionability"], x["disposition"], x["identity_key"]))

    table = OrderedDict()
    for disp in sorted({x["disposition"] for x in per_row}):
        c = Counter(x["actionability"] for x in per_row if x["disposition"] == disp)
        table[disp] = OrderedDict([("total", sum(c.values()))] + [(k.lower(), c.get(k, 0)) for k in CLASSES])
    totals = Counter(x["actionability"] for x in per_row)
    actionable_total = totals.get(ACTIONABLE_NOW, 0)

    marriott_open = sum(1 for x in per_row if x["brand_family"] == "MARRIOTT" and x["actionability"] == ACTIONABLE_NOW)
    browser_open = sum(1 for x in per_row if x["disposition"] == "BROWSER_CAPTURE_NEEDED")
    fast = shadow.get("fast_rules") or {}
    conditions = OrderedDict([
        ("actionable_unresolved_is_zero", actionable_total == 0),
        ("no_material_identity_gap", not recon.get("material_unexplained_gap", False)),
        ("no_material_unexplained_policy_gap", all(x["why"] for x in per_row)),
        ("authorized_acquisition_lanes_exhausted", actionable_total == 0),
        ("marriott_queue_terminally_resolved_or_exhausted", marriott_open == 0),
        ("browser_required_brands_processed_or_bounded", browser_open == 0),
        ("publication_set_safe", int((clean.get("counts") or {}).get("CLEAN_PET_FRIENDLY", 0)) > 0),
        ("package_deterministic_and_fast_clean",
         bool(shadow.get("PACKAGE_REPRODUCIBLE_IN_PROCESS")) and bool(fast)
         and all(v == "PASS" for v in fast.values())),
    ])
    gated = totals.get(NEW_SPEND, 0) + totals.get(NEW_PROVIDER, 0) + totals.get(FOUNDER, 0)
    if actionable_total:
        coverage = "NO"
    elif gated:
        coverage = "FOUNDER DECISION"
    else:
        coverage = "YES" if all(conditions.values()) else "NO"

    return OrderedDict([
        ("schema", "ptf-market-actionability/2.0"),
        ("work_order", WORK_ORDER),
        ("market_id", MARKET_ID),
        ("phase", "21 + 26 -- actionability of every unresolved ROW, and the coverage decision"),
        ("unresolved_is_not_actionable",
         "A large, bounded, fully-explained unresolved cohort is allowed. What is not allowed is a row an "
         "authorized lane could still reach. ACTIONABLE UNRESOLVED must be 0 before COVERAGE READY = YES."),
        ("census_total", len(rows)),
        ("resolved", len(rows) - len(unresolved)),
        ("unresolved_total", len(unresolved)),
        ("totals_by_class", OrderedDict((k, totals.get(k, 0)) for k in CLASSES)),
        ("by_disposition", table),
        ("actionable_unresolved_remaining", actionable_total),
        ("rows_gated_on_new_spend_provider_or_founder", gated),
        ("new_spend_note", PLACES_SPEND),
        ("attended_browser", OrderedDict([
            ("attempts", browser.get("attempts")), ("reads", browser.get("reads")),
            ("challenge_denied", browser.get("challenge_denied")), ("unbound", browser.get("unbound")),
            ("paid_provider_calls", browser.get("paid_provider_calls")),
            ("akamai_bypassed", browser.get("akamai_bypassed")),
            ("browser_js_exfiltration_used", browser.get("browser_js_exfiltration_used")),
            ("local_relay_used", browser.get("local_relay_used")),
        ])),
        ("coverage_conditions", conditions),
        ("COVERAGE_READY", coverage),
        ("TECHNICAL_SOURCE_READY", "YES" if conditions["package_deterministic_and_fast_clean"] else "NO"),
        ("rows", per_row),
    ])


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=OUT)
    args = ap.parse_args(argv)
    doc = build()
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    print("unresolved", doc["unresolved_total"], "actionable", doc["actionable_unresolved_remaining"])
    print("by class:", json.dumps(doc["totals_by_class"]))
    for k, v in doc["by_disposition"].items():
        print("  %-24s %s" % (k, json.dumps(v)))
    for x in doc["rows"]:
        if x["actionability"] == ACTIONABLE_NOW:
            print("  ACTIONABLE:", x["canonical_name"], "|", x["why"][:120])
    print("conditions:", json.dumps(doc["coverage_conditions"]))
    print("TECHNICAL SOURCE READY =", doc["TECHNICAL_SOURCE_READY"], "| COVERAGE READY =", doc["COVERAGE_READY"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
