"""PTF-TAMPA-FL-V2-COVERAGE-CLOSURE-002 -- merges the verified census
additions (tampa_fl_v2_closure_census_additions_001.json) into both on-disk
copies of the Tampa identity census, appended at the end (existing 495 rows
are untouched byte-for-byte in position and content -- this is additive
only, per PHASE 2)."""
from __future__ import annotations

import json
import os
import sys
from collections import OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
ADDITIONS = os.path.join(PKG, "markets", "reports", "tampa_fl_v2_closure_census_additions_001.json")


def main():
    additions = json.load(open(ADDITIONS, encoding="utf-8"))["additions"]
    for path in (
        os.path.join(PKG, "identity_census_proposed", "tampa-fl.json"),
        os.path.join(PKG, "markets", "staging", "tampa-fl", "launch_package", "identity_census", "tampa-fl.json"),
    ):
        census = json.load(open(path, encoding="utf-8"))
        keys_in_file = {h["identity_key"] for h in census["hotels"]}
        new_rows = [a for a in additions if a["identity_key"] not in keys_in_file]
        census["hotels"].extend(new_rows)
        census["count"] = len(census["hotels"])
        census["total_candidates"] = census.get("total_candidates", census["count"])
        cc = census.get("classification_counts", {})
        cc["TRUE_HOTEL_IDENTITY"] = cc.get("TRUE_HOTEL_IDENTITY", 0) + len(new_rows)
        census["classification_counts"] = cc
        corr = census.get("corridor_counts", {})
        for r in new_rows:
            corr[r["corridor"]] = corr.get(r["corridor"], 0) + 1
        census["corridor_counts"] = corr
        with open(path, "w", encoding="utf-8", newline="\n") as f:
            json.dump(census, f, indent=1, sort_keys=False, ensure_ascii=False)
            f.write("\n")
        print(path, "now has", census["count"], "hotels (+%d)" % len(new_rows))


if __name__ == "__main__":
    main()
