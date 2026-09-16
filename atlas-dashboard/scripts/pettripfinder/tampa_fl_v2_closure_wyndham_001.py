"""PTF-TAMPA-FL-V2-COVERAGE-CLOSURE-002 -- reads the 4 newly-admitted Wyndham
sub-brand (La Quinta / Days Inn) property pages this closure pass discovered
via Google Places (tampa_fl_v2_closure_census_additions_001), using the exact
same overview-page + property-service reader as the source-ready build's own
Wyndham lane. These specific routes were not in the original build's Wyndham
route selection because the properties themselves were not yet in the census.

Output:
  launch_packages/pettripfinder/markets/staging/tampa-fl/raw_captures/closure_wyndham_rows.json
"""
from __future__ import annotations

import json
import os
import sys
from collections import OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

from scripts.pettripfinder import tampa_fl_v2_wyndham_lane_001 as W  # noqa: E402
from scripts.pettripfinder import tampa_fl_v2_brand_inventory_001 as B  # noqa: E402

B.DOCS = os.path.join(_DASH, "data", "acquisition", "tampa_fl_v2_closure_wyndham_001")
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
ADDITIONS = os.path.join(PKG, "markets", "reports", "tampa_fl_v2_closure_census_additions_001.json")
OUT = os.path.join(PKG, "markets", "staging", "tampa-fl", "raw_captures", "closure_wyndham_rows.json")


def main():
    additions = json.load(open(ADDITIONS, encoding="utf-8"))["additions"]
    targets = [a for a in additions if a.get("brand") == "WYNDHAM" and a.get("official_url")]
    rows = []
    for t in targets:
        rec = W.read(t["official_url"])
        rec["identity_key"] = t["identity_key"]
        rows.append(rec)
        print(t["canonical_name"], "->", rec.get("pet_indicator"), rec.get("error"))
    good = [r for r in rows if r.get("id") and not r.get("error")]
    out = OrderedDict([("targets", len(targets)), ("read", len(good)), ("rows", rows)])
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
        f.write("\n")


if __name__ == "__main__":
    main()
