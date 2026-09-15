"""PTF-AUGUSTA-GA-POLICY-EVIDENCE-CLOSURE-002 -- Phase 2 evidence worklist.

Builds the explicit 82-property worklist (brand family, routing state,
current policy state, next evidence action) from the committed census +
partition, deriving brand family from each row's official_url domain (a
mechanical, reviewable rule -- not a guess) rather than retyping brand
labels by hand a second time.

Run:

    python -m scripts.pettripfinder.augusta_ga_evidence_worklist_004
"""

from __future__ import annotations

import json
import sys
from collections import OrderedDict
from pathlib import Path
from urllib.parse import urlparse

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.augusta_ga_market_build_001 import (
    CENSUS_PATH, MARKET_ID, PARTITION_PATH,
)

REPORTS = _REPO_ROOT / "launch_packages" / "pettripfinder" / "markets" / "reports"

_DOMAIN_BRAND = {
    "marriott.com": "Marriott",
    "hilton.com": "Hilton",
    "ihg.com": "IHG",
    "wyndhamhotels.com": "Wyndham",
    "choicehotels.com": "Choice",
    "hyatt.com": "Hyatt",
    "bestwestern.com": "Best Western",
    "sonesta.com": "Sonesta",
    "extendedstayamerica.com": "Extended Stay America",
    "woodspring.com": "WoodSpring",
    "motel6.com": "Motel 6 / Studio 6 (G6 Hospitality)",
    "studio6.com": "Motel 6 / Studio 6 (G6 Hospitality)",
    "redroof.com": "Red Roof",
    "hometowne.com": "Red Roof (HomeTowne Studios)",
    "myplacehotels.com": "My Place Hotels",
}

_BRAND_WIDE_UNIFORM_BRANDS = {
    "Motel 6 / Studio 6 (G6 Hospitality)", "Red Roof", "Red Roof (HomeTowne Studios)",
    "Extended Stay America", "WoodSpring",
}


def brand_family(official_url: str) -> str:
    if not official_url:
        return "Independent / unbranded (no official URL on file)"
    host = (urlparse(official_url).netloc or "").lower()
    host = host[4:] if host.startswith("www.") else host
    return _DOMAIN_BRAND.get(host, "Independent / regional")


def next_evidence_action(final_state: str, official_url: str, brand: str) -> str:
    if final_state == "AWAITING_IDENTITY_RESOLUTION":
        return "IDENTITY_HOLD -- resolve collision before binding policy evidence"
    if final_state == "AWAITING_OFFICIAL_URL":
        return "ROUTE_RESOLUTION -- find an official/independent property page first"
    if brand in _BRAND_WIDE_UNIFORM_BRANDS:
        return "FETCH_BRAND_WIDE_POLICY_PAGE (Tier 2 -- corporately uniform policy)"
    return "FETCH_PROPERTY_PAGE (Tier 3 -- franchise-variable brand, needs per-property read)"


def main() -> int:
    census = json.loads(CENSUS_PATH.read_text(encoding="utf-8"))
    partition = json.loads(PARTITION_PATH.read_text(encoding="utf-8"))
    partition_by_key = {i["identity_key"]: i for i in partition["items"]}

    worklist = []
    for row in census["hotels"]:
        key = row["identity_key"]
        item = partition_by_key[key]
        brand = brand_family(row.get("official_url", ""))
        worklist.append(OrderedDict((
            ("property_id", key),
            ("canonical_name", row["canonical_name"]),
            ("street", row["address"]),
            ("city", row["city"]),
            ("postal_code", row["postal_code"]),
            ("brand_family", brand),
            ("property_code", ""),
            ("official_url", row.get("official_url", "")),
            ("corridor", row["corridor"]),
            ("current_routing_state", "ROUTE_RESOLVED" if row.get("official_url")
                                     else "NO_OFFICIAL_ROUTE_FOUND"),
            ("current_policy_state", row["policy_state"]),
            ("current_partition_state", item["final_state"]),
            ("next_evidence_action", next_evidence_action(item["final_state"],
                                                          row.get("official_url", ""), brand)),
        )))

    assert len(worklist) == 82, len(worklist)

    by_brand = OrderedDict()
    for w in worklist:
        by_brand.setdefault(w["brand_family"], []).append(w["canonical_name"])

    doc = OrderedDict((
        ("schema", "ptf-augusta-evidence-worklist/1.0"),
        ("market_id", MARKET_ID),
        ("work_order", "PTF-AUGUSTA-GA-POLICY-EVIDENCE-CLOSURE-002"),
        ("count", len(worklist)),
        ("brand_family_counts", OrderedDict(sorted(
            ((b, len(v)) for b, v in by_brand.items()), key=lambda kv: -kv[1]))),
        ("properties", worklist),
    ))

    REPORTS.mkdir(parents=True, exist_ok=True)
    out_path = REPORTS / "augusta_ga_evidence_worklist_004.json"
    out_path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n",
                        encoding="utf-8", newline="\n")

    for brand, names in sorted(by_brand.items(), key=lambda kv: -len(kv[1])):
        print("%-45s %d" % (brand, len(names)))
    print("\nTOTAL: %d" % len(worklist))
    print("wrote: %s" % out_path)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
