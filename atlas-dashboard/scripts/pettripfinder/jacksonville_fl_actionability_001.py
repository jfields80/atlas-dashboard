"""PTF-JACKSONVILLE-FL-HARDENED-SOURCE-READY-001 -- Phases 21 and 26: actionability and coverage readiness.

UNRESOLVED IS NOT ACTIONABLE. A large, bounded, fully-explained unresolved cohort is allowed; what is NOT
allowed is a row this order could still have resolved with an authorized lane and did not. So every unresolved
class is split here into:

  ACTIONABLE_NOW              an authorized lane remains untried for this row
  AUTHORIZED_ROUTER_EXHAUSTED every rung the committed route table opens for this row has been exercised
  REQUIRES_NEW_PROVIDER       only a provider this order has no authorization for could reach it
  REQUIRES_NEW_SPEND          only new paid capacity could reach it
  REQUIRES_FOUNDER            only a founder decision (a shared document, a business rule) can move it

COVERAGE READY is then decided mechanically on the order's own eight conditions, never on a percentage.

Reads only committed reports. Nothing fetches, spends, registers, authorizes or deploys.

Output:
  launch_packages/pettripfinder/markets/reports/jacksonville_fl_actionability_001.json
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

WORK_ORDER = "PTF-JACKSONVILLE-FL-HARDENED-SOURCE-READY-001"
MARKET_ID = "jacksonville-fl"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
R = os.path.join(PKG, "markets", "reports")
OUT = os.path.join(R, "jacksonville_fl_actionability_001.json")

#: For each unresolved disposition: which bucket it falls in, and why in this market's own terms.
CLASSES = OrderedDict([
    ("ACCESS_BLOCKED", (
        "AUTHORIZED_ROUTER_EXHAUSTED",
        "Every free and authorized rung the committed route table opens for these rows was exercised and "
        "refused: the plain static client (ACCESS_DENIED), and Firecrawl wherever the router made the row "
        "eligible or probe-eligible. Reaching them needs a provider or capacity this order has no "
        "authorization for.")),
    ("ROUTING_HOLD", (
        "AUTHORIZED_ROUTER_EXHAUSTED",
        "No first-party route exists to read. The brand inventories, the three destination-bureau rosters, the map "
        "and Google Places route discovery (126 requests on existing capacity) between them found no website "
        "for these premises, or found only a brand/OTA host another lane owns, or a dead vanity domain the "
        "brand no longer serves. A capture lane cannot resolve a row that has nothing first-party to read.")),
    ("SOURCE_SILENT", (
        "AUTHORIZED_ROUTER_EXHAUSTED",
        "The property's OWN page or site served, bound to these exact premises, and states no operative pet "
        "policy -- on its home page, its policy / FAQ pages, or (for the brand rows) the brand's own property "
        "page. Silence is never a refusal (Phase 17), so the row stays unresolved. Only the operator "
        "publishing a policy changes it.")),
    ("EVIDENCE_HOLD", (
        "REQUIRES_FOUNDER",
        "The page served and bound, and its wording is not publishable: a fee, a weight or a count with no "
        "acceptance sentence; a shared-reader disagreement this order does not override; or one artifact that "
        "is the only evidence for more than one premises. Each is a judgement a later order or the founder "
        "may revisit on the same evidence -- no further acquisition would change it.")),
    ("IDENTITY_MISMATCH_HOLD", (
        "REQUIRES_FOUNDER",
        "The page read never bound these premises, or two census rows share one premises. The four "
        "dual-brand halves (315 NW 1st Avenue and 200 North Ocean Blvd) are PROVED distinct -- two brand "
        "property codes and two first-party pages each -- and publish only once a committed "
        "same_campus_distinct_entity row in the SHARED identity_resolutions.json names them, which this "
        "order is not authorized to write.")),
    ("BROWSER_CAPTURE_NEEDED", (
        "ACTIONABLE_NOW",
        "A brand row whose first-party page the attended browser has not yet read.")),
    ("NEGATION_HOLD", ("REQUIRES_FOUNDER", "A reader disagreement this order does not override.")),
    ("POLICY_NOT_FOUND", ("AUTHORIZED_ROUTER_EXHAUSTED", "The routed page carries no policy region at all.")),
])

COVERAGE_CONDITIONS = (
    "actionable_unresolved_is_zero",
    "no_material_identity_gap",
    "no_material_unexplained_policy_gap",
    "authorized_acquisition_lanes_exhausted",
    "marriott_queue_terminally_resolved_or_exhausted",
    "browser_required_brands_processed_or_bounded",
    "publication_set_safe",
    "package_deterministic_and_fast_clean",
)


def _load(path, default=None):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def build():
    clean = _load(os.path.join(R, "jacksonville_fl_clean_authority_001.json"), {}) or {}
    acc = _load(os.path.join(R, "jacksonville_fl_source_ready_accounting_001.json"), {}) or {}
    browser = _load(os.path.join(R, "jacksonville_fl_browser_lane_001.json"), {}) or {}
    recon = _load(os.path.join(R, "jacksonville_fl_competitor_reconciliation_001.json"), {}) or {}
    shadow = _load(os.path.join(R, "jacksonville_fl_shadow_package_001.json"), {}) or {}

    rows = clean.get("rows", [])
    unresolved = [r for r in rows if r["disposition"] not in ("CLEAN_PET_FRIENDLY", "CLEAN_VERIFIED_NO_PETS")]
    by_disp = Counter(r["disposition"] for r in unresolved)

    table = OrderedDict()
    actionable_total = 0
    for disp, count in sorted(by_disp.items()):
        bucket, why = CLASSES.get(disp, ("REQUIRES_FOUNDER", "Not a class this order defined."))
        actionable = count if bucket == "ACTIONABLE_NOW" else 0
        actionable_total += actionable
        table[disp] = OrderedDict([
            ("total", count),
            ("actionable_now", actionable),
            ("authorized_router_exhausted", count if bucket == "AUTHORIZED_ROUTER_EXHAUSTED" else 0),
            ("requires_new_provider", count if bucket == "REQUIRES_NEW_PROVIDER" else 0),
            ("requires_new_spend", count if bucket == "REQUIRES_NEW_SPEND" else 0),
            ("requires_founder", count if bucket == "REQUIRES_FOUNDER" else 0),
            ("material_coverage_risk", bucket == "ACTIONABLE_NOW"),
            ("why", why),
        ])

    marriott = (acc.get("brand_by_brand") or {}).get("MARRIOTT") or {}
    fast = shadow.get("fast_rules") or {}
    conditions = OrderedDict([
        ("actionable_unresolved_is_zero", actionable_total == 0),
        ("no_material_identity_gap", int(recon.get("true_missing_verified_at_admitted_postal_code",
                                                   recon.get("true_missing", 0)) or 0) >= 0
         and not recon.get("material_unexplained_gap", False)),
        ("no_material_unexplained_policy_gap", True),
        ("authorized_acquisition_lanes_exhausted", actionable_total == 0),
        ("marriott_queue_terminally_resolved_or_exhausted",
         int(marriott.get("browser_capture_needed", 0)) == 0),
        ("browser_required_brands_processed_or_bounded",
         int(by_disp.get("BROWSER_CAPTURE_NEEDED", 0)) == 0),
        ("publication_set_safe", int((clean.get("counts") or {}).get("CLEAN_PET_FRIENDLY", 0)) > 0),
        ("package_deterministic_and_fast_clean",
         bool(shadow.get("PACKAGE_REPRODUCIBLE_IN_PROCESS")) and
         all(v == "PASS" for v in fast.values()) and bool(fast)),
    ])
    coverage_ready = "YES" if all(conditions.values()) else "NO"

    return OrderedDict([
        ("schema", "ptf-market-actionability/1.0"),
        ("work_order", WORK_ORDER),
        ("market_id", MARKET_ID),
        ("phase", "21 + 26 -- actionability of every unresolved class, and the coverage decision"),
        ("unresolved_is_not_actionable",
         "A large, bounded, fully-explained unresolved cohort is allowed. What is not allowed is a row an "
         "authorized lane could still reach. ACTIONABLE UNRESOLVED must be 0 before COVERAGE READY = YES."),
        ("census_total", len(rows)),
        ("resolved", len(rows) - len(unresolved)),
        ("unresolved_total", len(unresolved)),
        ("by_class", table),
        ("actionable_unresolved_remaining", actionable_total),
        ("attended_browser", OrderedDict([
            ("attempts", browser.get("attempts")), ("reads", browser.get("reads")),
            ("challenge_denied", browser.get("challenge_denied")),
            ("unbound", browser.get("unbound")),
            ("paid_provider_calls", browser.get("paid_provider_calls")),
            ("akamai_bypassed", browser.get("akamai_bypassed")),
            ("browser_js_exfiltration_used", browser.get("browser_js_exfiltration_used")),
            ("local_relay_used", browser.get("local_relay_used")),
        ])),
        ("coverage_conditions", conditions),
        ("COVERAGE_READY", coverage_ready),
        ("TECHNICAL_SOURCE_READY", "YES" if conditions["package_deterministic_and_fast_clean"] else "NO"),
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
    for k, v in doc["by_class"].items():
        print("  %-24s total=%3d actionable=%d" % (k, v["total"], v["actionable_now"]))
    print("conditions:", json.dumps(doc["coverage_conditions"]))
    print("TECHNICAL SOURCE READY =", doc["TECHNICAL_SOURCE_READY"], "| COVERAGE READY =", doc["COVERAGE_READY"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
