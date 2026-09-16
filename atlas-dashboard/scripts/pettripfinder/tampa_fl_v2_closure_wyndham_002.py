"""PTF-TAMPA-FL-V2-TERMINAL-HOLD-CLOSURE-003 -- reads the 2 additional
Wyndham sub-brand (La Quinta) property pages admitted by
tampa_fl_v2_closure_census_additions_002 (the ZIP-registry fix), using the
same overview-page + property-service reader as the source-ready build's own
Wyndham lane and pass 2's closure_wyndham_001. Merges into the same
closure_wyndham_rows.json clean_authority_001 already reads.
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

B.DOCS = os.path.join(_DASH, "data", "acquisition", "tampa_fl_v2_closure_wyndham_002")
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
ADDITIONS = os.path.join(PKG, "markets", "reports", "tampa_fl_v2_closure_census_additions_002.json")
OUT = os.path.join(PKG, "markets", "staging", "tampa-fl", "raw_captures", "closure_wyndham_rows.json")


def main():
    additions = json.load(open(ADDITIONS, encoding="utf-8"))["additions"]
    targets = [a for a in additions if a.get("brand") == "WYNDHAM" and a.get("official_url")]
    existing = json.load(open(OUT, encoding="utf-8")) if os.path.exists(OUT) else {"targets": 0, "read": 0, "rows": []}
    already = {r["identity_key"] for r in existing.get("rows", [])}
    new_rows = []
    for t in targets:
        if t["identity_key"] in already:
            continue
        rec = W.read(t["official_url"])
        rec["identity_key"] = t["identity_key"]
        new_rows.append(rec)
        print(t["canonical_name"], "->", rec.get("pet_indicator"), rec.get("error"))
    merged_rows = list(existing.get("rows", [])) + new_rows
    good = [r for r in merged_rows if r.get("id") and not r.get("error")]
    out = OrderedDict([("targets", existing.get("targets", 0) + len(targets)), ("read", len(good)),
                       ("rows", merged_rows)])
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
        f.write("\n")


if __name__ == "__main__":
    main()
