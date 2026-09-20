"""PTF-MIAMI-FL-MARRIOTT-TERMINAL-CLOSURE-003 -- Phases 3-5: BEFORE vs AFTER, and the unresolved audit.

BEFORE is closure 002's own committed accounting at 32e183bd (read from git, never retyped). AFTER is this pass's
recomputed accounting over the whole 637-row census -- never the browser cohort alone.

PHASE 10 (the coverage question) classifies every remaining unresolved row into:
  ACTIONABLE_NOW                      a lane this order is authorized to run has not been run for it
  EXHAUSTED_UNDER_CURRENT_ROUTER      every authorized lane was attempted and refused, or the page says nothing
  REQUIRES_NEW_PROVIDER_OR_SPEND      only a provider this order is not authorized to buy would reach it
  REQUIRES_FOUNDER_DECISION           a judgement, not an acquisition

Output: launch_packages/pettripfinder/markets/reports/miami_fl_closure_accounting_003.json
"""
from __future__ import annotations

import json
import os
import subprocess
import sys
from collections import Counter, OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

WORK_ORDER = "PTF-MIAMI-FL-MARRIOTT-TERMINAL-CLOSURE-003"
BASE_SHA = "32e183bd"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
RAW = os.path.join(PKG, "markets", "staging", "miami-fl", "raw_captures")
OUT = os.path.join(REPORTS, "miami_fl_closure_accounting_003.json")
REL = "atlas-dashboard/launch_packages/pettripfinder/markets/reports/"

#: How each remaining hold class is classified for PHASE 10, with the reason stated once.
PHASE10 = OrderedDict([
    ("BROWSER_CAPTURE_NEEDED", ("ACTIONABLE_NOW", "the authorized browser lane exists for this row and this "
                                                  "terminal pass still did not attempt it -- if any row lands here "
                                                  "the closure is not terminal")),
    ("ACCESS_BLOCKED", ("EXHAUSTED_UNDER_CURRENT_ROUTER", "every free and authorized lane attempted was refused "
                                                          "(static, Firecrawl where the router made it eligible, and "
                                                          "-- for brand rows -- the authorized browser)")),
    ("ROUTING_HOLD", ("EXHAUSTED_UNDER_CURRENT_ROUTER", "no first-party route exists to read: Places route "
                                                        "discovery bound no site at this row's own street and ZIP, "
                                                        "or the only site named is a brand/OTA host")),
    ("SOURCE_SILENT", ("EXHAUSTED_UNDER_CURRENT_ROUTER", "the property's own page served, bound to the identity, "
                                                         "and states no operative pet policy")),
    ("IDENTITY_MISMATCH_HOLD", ("REQUIRES_FOUNDER_DECISION", "a page or site was read but never confirmed this "
                                                             "row's premises; the identity, not the policy, is open")),
    ("EVIDENCE_HOLD", ("REQUIRES_FOUNDER_DECISION", "evidence exists but the safety rules refuse to publish it "
                                                    "(fee/weight-only wording, a shared-reader disagreement, or a "
                                                    "route-domain conflict)")),
])


def _load(path, default=None):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8-sig") as fh:
        return json.load(fh)


def _git_show(path):
    out = subprocess.run(["git", "show", "%s:%s" % (BASE_SHA, path)], cwd=os.path.dirname(_DASH),
                         capture_output=True, text=True, encoding="utf-8")
    if out.returncode != 0:
        raise SystemExit("cannot read %s at the sealed base: %s" % (path, out.stderr[:200]))
    return json.loads(out.stdout)


def main():
    before = _git_show(REL + "miami_fl_source_ready_accounting_001.json")
    after = _load(os.path.join(REPORTS, "miami_fl_source_ready_accounting_001.json"))
    closure = _load(os.path.join(REPORTS, "miami_fl_browser_closure_003.json"), {}) or {}
    clean = _load(os.path.join(REPORTS, "miami_fl_clean_authority_001.json"))
    part = _load(os.path.join(PKG, "markets", "staging", "miami-fl", "launch_package",
                              "miami_fl_final_partition_001.json"))

    def headline(doc):
        h = doc["headline"]
        return OrderedDict([("proposed_census", h["proposed_census"]), ("pet_friendly", h["valid_pet_friendly"]),
                            ("verified_no_pets", h["valid_verified_no_pets"]), ("resolved", h["resolved"]),
                            ("unresolved", h["unresolved"]), ("resolution_rate", h["resolution_rate"])])

    b, a = headline(before), headline(after)
    delta = OrderedDict((k, (a[k] - b[k]) if isinstance(a[k], (int, float)) and isinstance(b[k], (int, float))
                         else None) for k in a)
    delta["resolution_rate"] = round(a["resolution_rate"] - b["resolution_rate"], 4)

    holds_b, holds_a = before["holds_by_class"], after["holds_by_class"]
    holds = OrderedDict((k, OrderedDict([("before", holds_b.get(k, 0)), ("after", holds_a.get(k, 0)),
                                         ("delta", holds_a.get(k, 0) - holds_b.get(k, 0))]))
                        for k in holds_a)

    fam_b, fam_a = before["brand_by_brand"], after["brand_by_brand"]
    brands = OrderedDict()
    for fam in sorted(set(fam_b) | set(fam_a)):
        x, y = fam_b.get(fam, {}), fam_a.get(fam, {})
        brands[fam] = OrderedDict([
            ("census", OrderedDict([("before", x.get("census", 0)), ("after", y.get("census", 0))])),
            ("pet_friendly", OrderedDict([("before", x.get("pet_friendly", 0)), ("after", y.get("pet_friendly", 0))])),
            ("no_pets", OrderedDict([("before", x.get("no_pets", 0)), ("after", y.get("no_pets", 0))])),
            ("unresolved", OrderedDict([("before", x.get("unresolved", 0)), ("after", y.get("unresolved", 0))])),
            ("browser_capture_needed", OrderedDict([("before", x.get("browser_capture_needed", 0)),
                                                    ("after", y.get("browser_capture_needed", 0))])),
        ])

    cor_b, cor_a = before["corridor_coverage"], after["corridor_coverage"]
    corridors = OrderedDict()
    for slug in sorted(set(cor_b) | set(cor_a)):
        x, y = cor_b.get(slug, {}), cor_a.get(slug, {})
        corridors[slug] = OrderedDict([
            ("pet_friendly", OrderedDict([("before", x.get("pet_friendly", 0)), ("after", y.get("pet_friendly", 0))])),
            ("no_pets", OrderedDict([("before", x.get("no_pets", 0)), ("after", y.get("no_pets", 0))])),
            ("page_publishes", OrderedDict([("before", x.get("page_publishes")), ("after", y.get("page_publishes"))])),
        ])

    # PHASE 10 -- the audit over EVERY remaining unresolved row
    disp = Counter(i["disposition"] for i in part["items"] if not i["resolved"])
    audit = OrderedDict()
    for klass, count in sorted(disp.items()):
        verdict, why = PHASE10.get(klass, ("REQUIRES_FOUNDER_DECISION", "unclassified"))
        audit[klass] = OrderedDict([("total_remaining", count), ("verdict", verdict), ("why", why)])
    actionable = sum(v["total_remaining"] for v in audit.values() if v["verdict"] == "ACTIONABLE_NOW")

    doc = OrderedDict([
        ("schema", "ptf-closure-accounting/1.0"), ("work_order", WORK_ORDER), ("market_id", "miami-fl"),
        ("base_sha", BASE_SHA),
        ("headline", OrderedDict([("before", b), ("after", a), ("delta", delta)])),
        ("holds_by_class", holds),
        ("browser_closure", OrderedDict([
            ("queue_total_frozen", closure.get("queue_total_frozen")),
            ("queue_in_current_census", closure.get("queue_total")),
            ("queue_by_family", closure.get("queue_by_family")),
            ("outcomes", closure.get("outcomes")),
            ("bindings", closure.get("bindings")),
            ("rows_merged_away_since_the_base", closure.get("queue_rows_merged_away_since_the_base")),
        ])),
        ("brand_by_brand", brands),
        ("corridor_coverage", corridors),
        ("phase10_unresolved_audit", audit),
        ("actionable_unresolved_remaining", actionable),
        ("provider_usage_this_pass", OrderedDict([
            ("supported_browser_reads", (closure.get("outcomes") or {}).get("READ", 0)),
            ("firecrawl_reruns", 0), ("additional_firecrawl_credits", 0), ("google_places_calls", 0),
            ("new_paid_spend_usd", 0.0), ("new_provider_authorization", "NONE"),
        ])),
    ])
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    print("before", dict(b))
    print("after ", dict(a))
    print("holds ", {k: v["delta"] for k, v in holds.items() if v["delta"]})
    print("actionable unresolved remaining:", actionable)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
