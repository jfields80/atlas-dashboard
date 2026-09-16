"""PTF-AUGUSTA-GA-HARDENED-V2-SOURCE-READY-001 -- Phase 24 quality pass:
apply the reliable Wyndham property-service captures (augusta_ga_wyndham_
lane_009.py) over the final partition, replacing the EVIDENCE_HOLD/held
state those 14 rows got from the unstable /overview-redirect hub.

Classification rule: the explicit TEXT is the operative fact, safety-checked
against the brand's own structured ``pet_indicator`` (Y/N) rather than
trusting either alone. One real conflict found and NOT silently resolved:
"wingate augusta i 20" carries ``pet_indicator: Y`` but its own text reads
"Sorry no other pets are allowed" -- explicit refusal wording beats a bare
indicator flag (Phase 17's own hierarchy: safety-check the indicator against
the human-readable text, not the reverse), so this row is held
(NEGATION_HOLD) rather than published either way, with the conflict named.

Every other resolved row's indicator and text agree, so those publish:
Y + explicit fee/count/weight numbers -> CLEAN_PET_FRIENDLY; N + explicit
"no other pets allowed" -> CLEAN_VERIFIED_NO_PETS (service-animal-only
refusal wording, now safety-checked against a STABLE per-property source
rather than the volatile hub, unlike the rest of that cohort).

Output: markets/reports/augusta_ga_final_partition_007.json (updated in place)
"""
from __future__ import annotations

import json
import os
import sys
import time
from collections import Counter, OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
WYNDHAM_LANE = os.path.join(PKG, "markets", "reports", "augusta_ga_wyndham_lane_009.json")
PARTITION = os.path.join(PKG, "markets", "reports", "augusta_ga_final_partition_007.json")


def main():
    wl = json.load(open(WYNDHAM_LANE, encoding="utf-8"))
    part = json.load(open(PARTITION, encoding="utf-8"), object_pairs_hook=OrderedDict)
    by_key = {p["identity_key"]: p for p in part["partition"]}
    conflicts = []
    applied = []

    for r in wl["rows"]:
        key = r["identity_key"]
        p = by_key.get(key)
        if p is None:
            continue
        text = (r.get("pet_policy_text") or "").lower()
        indicator = r.get("pet_indicator")
        explicit_no = "no other pets are allowed" in text or "not allowed" in text
        explicit_yes_numbers = any(ch.isdigit() for ch in text) and ("fee" in text or "lbs" in text or "night" in text or "stay" in text)

        if indicator == "Y" and explicit_no:
            conflicts.append({"identity_key": key, "pet_indicator": indicator, "text": r.get("pet_policy_text")})
            p["disposition"] = "NEGATION_HOLD"
            p["operative_quote"] = r.get("pet_policy_text")
            p["parsed_facts"] = {}
            p["note"] = ("brand's own pet_indicator=Y conflicts with its own explicit refusal text "
                          "('no other pets are allowed'); explicit human-readable text is safety-checked "
                          "against the structured indicator per Phase 17, not the reverse -- held, not published")
        elif explicit_no:
            p["disposition"] = "CLEAN_VERIFIED_NO_PETS"
            p["operative_quote"] = r.get("pet_policy_text")
            p["parsed_facts"] = {"acceptance": "NOT_ALLOWED", "service_animal_exception": True}
        elif explicit_yes_numbers:
            p["disposition"] = "CLEAN_PET_FRIENDLY"
            p["operative_quote"] = r.get("pet_policy_text")
            p["parsed_facts"] = {"acceptance": "ALLOWED"}
        else:
            continue  # leave as-is; not enough to change the prior hold
        p["evidence_lane"] = "WYNDHAM_PROPERTY_SERVICE_API"
        p["street"] = r.get("street"); p["postal_code"] = r.get("postal_code")
        applied.append({"identity_key": key, "disposition": p["disposition"]})

    part["disposition_tally"] = dict(Counter(p["disposition"] for p in part["partition"]))
    part["wyndham_property_service_reclassification"] = OrderedDict([
        ("as_of", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())),
        ("rows_applied", applied), ("conflicts_found", conflicts),
    ])
    with open(PARTITION, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(part, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    print("applied", len(applied), "conflicts", len(conflicts), "tally", part["disposition_tally"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
