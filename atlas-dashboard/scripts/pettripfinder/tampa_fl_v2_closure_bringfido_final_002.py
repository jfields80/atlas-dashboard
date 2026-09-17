"""PTF-TAMPA-FL-V2-TERMINAL-HOLD-CLOSURE-003 -- Phase 10 final BringFido
reconciliation. Recomputes the pass-2 reconciliation's 22
TRUE_MISSING_QUALIFYING_CANDIDATE rows against this pass's own
census-additions verification (tampa_fl_v2_closure_census_additions_002),
producing the final classification for every one of the 22 without
re-running the raw BringFido capture (identity discovery only, never policy
authority; unchanged from pass 2).
"""
from __future__ import annotations

import json
import os
from collections import OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
REPORTS = os.path.join(_DASH, "launch_packages", "pettripfinder", "markets", "reports")
RECON = os.path.join(REPORTS, "tampa_fl_v2_closure_bringfido_reconciliation_001.json")
ADDITIONS = os.path.join(REPORTS, "tampa_fl_v2_closure_census_additions_002.json")
OUT = os.path.join(REPORTS, "tampa_fl_v2_closure_bringfido_final_002.json")


def main():
    recon = json.load(open(RECON, encoding="utf-8"))
    additions = json.load(open(ADDITIONS, encoding="utf-8"))
    admitted_names = {a["evidence"][0]["name"] for a in additions["additions"]}
    rejected_by_name = {r["name"]: r["reason"] for r in additions["rejected_rows"]}

    candidates = [r for r in recon["rows"] if r["classification"] == "TRUE_MISSING_QUALIFYING_CANDIDATE"]
    final_rows = []
    counts = OrderedDict([
        ("QUALIFYING_TRUE_MISSING_ADMITTED", 0), ("EXISTING_CENSUS_MATCH_ALIAS", 0),
        ("VACATION_RENTAL_OR_NON_HOTEL", 0), ("CLOSED", 0), ("OUTSIDE_ADMITTED_GEOGRAPHY", 0),
        ("STILL_IDENTITY_REVIEW", 0),
    ])
    for c in candidates:
        name = c["bringfido_name"]
        if name in admitted_names:
            cls = "QUALIFYING_TRUE_MISSING_ADMITTED"
        elif name == "Days Inn by Wyndham Bradenton - Near the Gulf":
            cls = "OUTSIDE_ADMITTED_GEOGRAPHY"
        else:
            reason = rejected_by_name.get(name, "")
            if reason == "ALREADY_IN_CENSUS_SAME_ADDRESS":
                cls = "EXISTING_CENSUS_MATCH_ALIAS"
            elif reason in ("NAME_PATTERN_INDIVIDUAL_UNIT_NOT_HOTEL", "VACATION_RENTAL_OR_OTA_ONLY_URL"):
                cls = "VACATION_RENTAL_OR_NON_HOTEL"
            elif reason == "CLOSED_PERMANENTLY":
                cls = "CLOSED"
            elif reason == "POSTAL_NOT_IN_ADMITTED_SET":
                cls = "OUTSIDE_ADMITTED_GEOGRAPHY"
            else:
                cls = "STILL_IDENTITY_REVIEW"
        counts[cls] += 1
        final_rows.append(OrderedDict([("bringfido_name", name), ("final_classification", cls),
                                       ("reason", rejected_by_name.get(name, "admitted to census"))]))

    out = OrderedDict([
        ("schema", "ptf-tampa-fl-v2-closure-bringfido-final/1.0"),
        ("work_order", "PTF-TAMPA-FL-V2-TERMINAL-HOLD-CLOSURE-003"),
        ("starting_true_missing", len(candidates)),
        ("counts", counts),
        ("true_missing_qualifying_remaining", counts["STILL_IDENTITY_REVIEW"]),
        ("material_gap_remains", counts["STILL_IDENTITY_REVIEW"] > 0),
        ("rows", final_rows),
    ])
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
        f.write("\n")
    print(json.dumps(counts, indent=1))
    print("TRUE MISSING QUALIFYING REMAINING:", counts["STILL_IDENTITY_REVIEW"])


if __name__ == "__main__":
    main()
