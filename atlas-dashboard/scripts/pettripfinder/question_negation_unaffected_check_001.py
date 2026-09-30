"""PTF-FIRST-PARTY-QUESTION-NEGATION-AND-LIVE-CORRECTION-001 -- the bounded proof that the reader repair reclassifies
no UNAFFECTED market.

    cd <old atlas-dashboard> && python <this file> gate --label before --out before.json
    cd <new atlas-dashboard> && python <this file> gate --label after  --out after.json
    python <this file> compare --before before.json --after after.json [--out report.json]

FAST rule C (``first_party_binding.evaluate_package``) is run over every committed sealed package of every market
under the reader of the checkout it runs in (imported from the working directory, like the live scan). A record
whose rule-C verdict differs between the two readers is RECLASSIFIED. The seven corrected markets' sealed packages are
measured too, but only an unaffected market's reclassification fails the check. The live scan
(``live_pet_policy_quote_safety_scan_001``) is the same proof over the published root packages.
"""
from __future__ import annotations

import argparse
import glob
import json
import os
import sys
from collections import OrderedDict

WORK_ORDER = "PTF-FIRST-PARTY-QUESTION-NEGATION-AND-LIVE-CORRECTION-001"
REPORT_REL = os.path.join("launch_packages", "pettripfinder", "markets", "reports",
                          "question_negation_unaffected_markets_001.json")
CORRECTED = ("fort-lauderdale-fl", "tampa-fl", "san-diego-ca", "jacksonville-fl", "miami-fl", "phoenix-az",
             "orlando-fl")


def gate(label, only=None):
    sys.path.insert(0, os.getcwd())
    from scripts.pettripfinder import first_party_binding as FPB
    root = os.path.join(os.getcwd(), "launch_packages", "pettripfinder", "markets", "packages")
    out = OrderedDict()
    for path in sorted(glob.glob(os.path.join(root, "*", "pkg-*.json"))):
        name = os.path.basename(path)
        if only is not None and name not in only:
            continue
        package = json.load(open(path, encoding="utf-8-sig"))
        report = FPB.evaluate_package(package)
        # rule C reports its INELIGIBLE records by name and every class by count: a record that moves between
        # eligible and ineligible, or between two ineligible classes, moves one of the two
        verdicts = OrderedDict(("%s|%s" % (row.get("kind"), row.get("identity_key")), row.get("classification"))
                               for row in report.get("failures") or ())
        verdicts.update(("class-count|%s" % k, v) for k, v in sorted((report.get("classes") or {}).items()))
        out[name] = OrderedDict((("market_id", package.get("market_id")), ("passed", report["passed"]),
                                 ("records_evaluated", report["records_evaluated"]),
                                 ("eligible", report["eligible"]), ("ineligible", report["ineligible"]),
                                 ("verdicts", verdicts)))
    return OrderedDict((("label", label), ("packages", out)))


def compare(before, after):
    rows = OrderedDict()
    unaffected_moved = []
    for name, b in before["packages"].items():
        a = after["packages"].get(name)
        if a is None:
            continue
        moved = OrderedDict((k, [b["verdicts"].get(k), a["verdicts"].get(k)])
                            for k in sorted(set(b["verdicts"]) | set(a["verdicts"]))
                            if b["verdicts"].get(k) != a["verdicts"].get(k))
        same = (b["passed"], b["eligible"], b["ineligible"]) == (a["passed"], a["eligible"], a["ineligible"]) \
            and not moved
        rows[name] = OrderedDict((("market_id", b["market_id"]), ("corrected_market", b["market_id"] in CORRECTED),
                                  ("before", [b["passed"], b["eligible"], b["ineligible"]]),
                                  ("after", [a["passed"], a["eligible"], a["ineligible"]]),
                                  ("records_reclassified", moved), ("identical", same)))
        if not same and b["market_id"] not in CORRECTED:
            unaffected_moved.append(name)
    return OrderedDict((
        ("schema", "ptf-reader-reclassification-check/1.0"), ("work_order", WORK_ORDER),
        ("what_this_is", "FAST rule C over every committed sealed package, under the reader before and after the "
                         "repair. The corrected markets' pre-correction packages are measured too; an UNAFFECTED "
                         "market whose verdicts move fails the check."),
        ("packages_compared", len(rows)),
        ("unaffected_packages_compared", sum(1 for r in rows.values() if not r["corrected_market"])),
        ("unaffected_markets_compared", len({r["market_id"] for r in rows.values() if not r["corrected_market"]})),
        ("UNAFFECTED_PACKAGES_RECLASSIFIED", len(unaffected_moved)),
        ("unaffected_reclassified", unaffected_moved),
        ("corrected_market_packages_reclassified",
         [n for n, r in rows.items() if r["corrected_market"] and not r["identical"]]),
        ("packages", rows),
    ))


def main(argv=None):
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("gate")
    g.add_argument("--label", required=True)
    g.add_argument("--out", required=True)
    g.add_argument("--only-from", help="a gate output whose package list this run is limited to")
    c = sub.add_parser("compare")
    c.add_argument("--before", required=True)
    c.add_argument("--after", required=True)
    c.add_argument("--out", default=None)
    args = ap.parse_args(argv)
    if args.cmd == "gate":
        only = set(json.load(open(args.only_from, encoding="utf-8"))["packages"]) if args.only_from else None
        doc = gate(args.label, only)
        out = args.out
    else:
        doc = compare(json.load(open(args.before, encoding="utf-8")), json.load(open(args.after, encoding="utf-8")))
        out = args.out or os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", REPORT_REL)
    with open(out, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    if args.cmd == "compare":
        for k in ("packages_compared", "unaffected_packages_compared", "unaffected_markets_compared",
                  "UNAFFECTED_PACKAGES_RECLASSIFIED", "unaffected_reclassified",
                  "corrected_market_packages_reclassified"):
            print(k, "=", doc[k])
    else:
        print(args.label, len(doc["packages"]), "packages")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
