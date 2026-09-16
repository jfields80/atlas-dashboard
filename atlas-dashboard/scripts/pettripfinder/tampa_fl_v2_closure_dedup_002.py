"""PTF-TAMPA-FL-V2-TERMINAL-HOLD-CLOSURE-003 -- a genuine census identity
defect discovered during this pass's browser closure (PHASE 2's "concrete
contradiction" allowance): "Holiday Inn Tampa Airport Westshore"
(identity_key holiday_inn_tampa_airport_westshore, "700 N Westshore Blvd",
33609, ROUTING_HOLD) and the already-resolved "Holiday Inn Tampa Westshore -
Airport Area" (identity_key holiday_inn_tampa_westshore_airport_area, "700
North West Shore Boulevard", 33609, CLEAN_PET_FRIENDLY since pass 2) are the
SAME physical hotel: identical house number (700) and postal code (33609),
a street-spelling variance ("N" vs "North", "Westshore" vs "West Shore")
that census_reconciliation's dedup key never folded because it did not
normalise directional abbreviations before comparing.

This module retires the duplicate ROUTING_HOLD row from both on-disk copies
of the census (never the already-resolved row, and never any other row) --
additive-in-reverse, the mirror of tampa_fl_v2_closure_merge_additions_002,
removing exactly one row that should never have existed as a second
identity. The hotel remains published under its correct, already-resolved
identity; no coverage is lost.
"""
from __future__ import annotations

import json
import os
from collections import OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
OUT = os.path.join(REPORTS, "tampa_fl_v2_closure_dedup_002.json")

RETIRE_KEY = "holiday inn tampa airport westshore"
KEPT_KEY = "holiday inn tampa westshore airport area"


def main():
    removed_any = None
    for path in (
        os.path.join(PKG, "identity_census_proposed", "tampa-fl.json"),
        os.path.join(PKG, "markets", "staging", "tampa-fl", "launch_package", "identity_census", "tampa-fl.json"),
    ):
        census = json.load(open(path, encoding="utf-8"))
        before = len(census["hotels"])
        removed = [h for h in census["hotels"] if h["identity_key"] == RETIRE_KEY]
        census["hotels"] = [h for h in census["hotels"] if h["identity_key"] != RETIRE_KEY]
        after = len(census["hotels"])
        if removed:
            removed_any = removed[0]
        census["count"] = after
        cc = census.get("classification_counts", {})
        if before != after:
            cc["TRUE_HOTEL_IDENTITY"] = max(0, cc.get("TRUE_HOTEL_IDENTITY", 0) - (before - after))
        census["classification_counts"] = cc
        corr = census.get("corridor_counts", {})
        if removed:
            cor = removed[0].get("corridor")
            if cor in corr:
                corr[cor] = max(0, corr[cor] - 1)
        census["corridor_counts"] = corr
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            json.dump(census, f, indent=1, sort_keys=False, ensure_ascii=False)
            f.write("\n")
        print(path, "now has", after, "hotels (-%d)" % (before - after))

    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        json.dump(OrderedDict([
            ("schema", "ptf-tampa-fl-v2-closure-dedup/1.0"),
            ("work_order", "PTF-TAMPA-FL-V2-TERMINAL-HOLD-CLOSURE-003"),
            ("retired_identity_key", RETIRE_KEY),
            ("kept_identity_key", KEPT_KEY),
            ("reason", "same physical premises (700 N/North Westshore/West Shore Blvd, 33609) discovered as a "
                       "duplicate identity_key during this pass's supported-browser closure; a street-spelling "
                       "variance census_reconciliation's dedup never folded. The kept identity was already "
                       "CLEAN_PET_FRIENDLY since pass 2; no coverage is lost by retiring the duplicate."),
            ("retired_row", removed_any),
        ]), f, indent=1, ensure_ascii=False)
        f.write("\n")


if __name__ == "__main__":
    main()
