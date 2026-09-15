"""PTF-AUGUSTA-GA-POLICY-EVIDENCE-CLOSURE-002 -- brand-by-brand closure
report and updated accounting, derived mechanically from the census,
partition, and evidence worklist.

Run AFTER augusta_ga_market_build_002:

    python -m scripts.pettripfinder.augusta_ga_brand_closure_report_006
"""

from __future__ import annotations

import json
import sys
from collections import OrderedDict, defaultdict
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.augusta_ga_evidence_worklist_004 import brand_family
from scripts.pettripfinder.augusta_ga_market_build_001 import (
    CENSUS_PATH, MARKET_ID, PARTITION_PATH,
)
from scripts.pettripfinder.augusta_ga_market_build_002 import POLICY_FACTS_PATH

REPORTS = _REPO_ROOT / "launch_packages" / "pettripfinder" / "markets" / "reports"


def main() -> int:
    census = json.loads(CENSUS_PATH.read_text(encoding="utf-8"))
    partition = json.loads(PARTITION_PATH.read_text(encoding="utf-8"))
    facts = json.loads(POLICY_FACTS_PATH.read_text(encoding="utf-8"))["facts"]
    facts_by_key = {f["identity_key"]: f for f in facts}
    partition_by_key = {i["identity_key"]: i for i in partition["items"]}

    by_brand = defaultdict(lambda: defaultdict(int))
    for row in census["hotels"]:
        key = row["identity_key"]
        item = partition_by_key[key]
        fact = facts_by_key[key]
        brand = brand_family(fact["requested_url"] or row.get("official_url", ""))
        state = item["final_state"]
        by_brand[brand]["TOTAL"] += 1
        if state == "PUBLISHED_PET_FRIENDLY":
            by_brand[brand]["VERIFIED_PET_FRIENDLY"] += 1
        elif state == "VERIFIED_NO_PETS":
            by_brand[brand]["VERIFIED_NO_PETS"] += 1
        elif state == "ACCESS_BLOCKED":
            by_brand[brand]["ACCESS_BLOCKED"] += 1
        elif state in ("AWAITING_PROPERTY_LEVEL_URL", "AWAITING_OFFICIAL_URL",
                      "AWAITING_ROUTING_REVIEW", "AWAITING_ROUTING_REPLACEMENT"):
            by_brand[brand]["ROUTING_HOLD"] += 1
        elif state in ("AWAITING_POLICY_OBSERVATION", "AWAITING_POLICY_ARTIFACT",
                      "AWAITING_CONTRADICTION_RESOLUTION"):
            by_brand[brand]["EVIDENCE_HOLD"] += 1
        elif state == "AWAITING_IDENTITY_RESOLUTION":
            by_brand[brand]["IDENTITY_HOLD"] += 1
        else:
            by_brand[brand]["OTHER_UNRESOLVED"] += 1

    brand_report = OrderedDict()
    for brand in sorted(by_brand, key=lambda b: -by_brand[b]["TOTAL"]):
        counts = by_brand[brand]
        row = OrderedDict((
            ("TOTAL", counts["TOTAL"]),
            ("VERIFIED_PET_FRIENDLY", counts.get("VERIFIED_PET_FRIENDLY", 0)),
            ("VERIFIED_NO_PETS", counts.get("VERIFIED_NO_PETS", 0)),
            ("ROUTING_HOLD", counts.get("ROUTING_HOLD", 0)),
            ("ACCESS_BLOCKED", counts.get("ACCESS_BLOCKED", 0)),
            ("EVIDENCE_HOLD", counts.get("EVIDENCE_HOLD", 0)),
            ("IDENTITY_HOLD", counts.get("IDENTITY_HOLD", 0)),
            ("OTHER_UNRESOLVED", counts.get("OTHER_UNRESOLVED", 0)),
        ))
        brand_report[brand] = row

    final_counts = partition["final_state_counts"]
    total = partition["count"]
    pf = final_counts.get("PUBLISHED_PET_FRIENDLY", 0)
    np_ = final_counts.get("VERIFIED_NO_PETS", 0)
    resolved = pf + np_
    unresolved = total - resolved

    accounting = OrderedDict((
        ("TOTAL_CENSUS", total),
        ("VERIFIED_PET_FRIENDLY", pf),
        ("VERIFIED_NO_PETS", np_),
        ("RESOLVED", resolved),
        ("UNRESOLVED", unresolved),
        ("RESOLUTION_RATE", round(100.0 * resolved / total, 1)),
        ("IDENTITY_HOLDS", final_counts.get("AWAITING_IDENTITY_RESOLUTION", 0)),
        ("ROUTING_HOLDS", final_counts.get("AWAITING_PROPERTY_LEVEL_URL", 0)
                         + final_counts.get("AWAITING_OFFICIAL_URL", 0)),
        ("ACCESS_BLOCKED", final_counts.get("ACCESS_BLOCKED", 0)),
        ("EVIDENCE_HOLDS", final_counts.get("AWAITING_POLICY_OBSERVATION", 0)),
        ("NEGATION_HOLDS", 0),
        ("BROWSER_CAPTURE_NEEDED", 0),
        ("POLICY_NOT_SEEN", final_counts.get("AWAITING_POLICY_OBSERVATION", 0)),
        ("PAID_PROVIDER_HOLDS", 0),
        ("CONTRADICTION_HOLDS", final_counts.get("AWAITING_CONTRADICTION_RESOLUTION", 0)),
    ))

    bucket_sum = (accounting["RESOLVED"] + accounting["IDENTITY_HOLDS"] + accounting["ROUTING_HOLDS"]
                 + accounting["ACCESS_BLOCKED"] + accounting["EVIDENCE_HOLDS"]
                 + accounting["CONTRADICTION_HOLDS"])
    accounting["RECONCILES"] = bucket_sum == total

    doc = OrderedDict((
        ("schema", "ptf-augusta-policy-closure-accounting/1.0"),
        ("market_id", MARKET_ID),
        ("work_order", "PTF-AUGUSTA-GA-POLICY-EVIDENCE-CLOSURE-002"),
        ("accounting", accounting),
        ("brand_closure", brand_report),
        ("partition_final_state_counts", final_counts),
    ))

    REPORTS.mkdir(parents=True, exist_ok=True)
    out_path = REPORTS / "augusta_ga_policy_evidence_closure_006.json"
    out_path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n", encoding="utf-8", newline="\n")

    print("ACCOUNTING")
    for k, v in accounting.items():
        print("  %-22s %s" % (k, v))
    print("\nBRAND CLOSURE")
    for brand, row in brand_report.items():
        print("  %-45s %s" % (brand, dict(row)))
    print("\nwrote: %s" % out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
