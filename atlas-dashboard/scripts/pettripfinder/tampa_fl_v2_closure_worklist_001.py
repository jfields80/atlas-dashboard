"""PTF-TAMPA-FL-V2-COVERAGE-CLOSURE-002 -- Phase 3.

Builds the machine-readable closure worklist: every currently-unresolved
Tampa V2 census row, exactly once, grouped by hold class, joined from the
committed final partition (disposition/router record) and identity census
(address/brand/phone/corridor/official_url) so acquisition work has a
concrete target list without re-deriving the census.

Durable-key discipline (Orlando closure lesson): every row here carries its
identity_key straight from the committed census/partition. Downstream
closure builders must re-look-up by that key (or by street+postal/phone)
fresh on every run -- never cache a name binding across passes.
"""
import json
from collections import OrderedDict, defaultdict

MARKET = "tampa-fl"
REPORTS = "launch_packages/pettripfinder/markets/reports"
STAGING = "launch_packages/pettripfinder/markets/staging/tampa-fl"

HOLD_GROUP = {
    "ROUTING_HOLD": "ROUTING_HOLD",
    "ACCESS_BLOCKED": "ACCESS_BLOCKED",
    "EVIDENCE_HOLD": "EVIDENCE_HOLD",
    "SOURCE_SILENT": "SOURCE_SILENT",
    "BROWSER_CAPTURE_NEEDED": "BROWSER_NEEDED",
    "IDENTITY_MISMATCH_HOLD": "IDENTITY_REVIEW",
}


def load(path):
    with open(path, encoding="utf-8") as f:
        return json.load(f)


def main():
    partition = load(f"{STAGING}/launch_package/tampa_fl_final_partition_v2_001.json")
    census = load(f"{STAGING}/launch_package/identity_census/tampa-fl.json")
    census_by_key = {h["identity_key"]: h for h in census["hotels"]}

    worklist = []
    groups = defaultdict(list)
    for item in partition["items"]:
        if item.get("resolved"):
            continue
        key = item["identity_key"]
        c = census_by_key.get(key, {})
        disp = item["disposition"]
        group = HOLD_GROUP.get(disp, "OTHER")
        rr = item.get("router_record", {})
        row = OrderedDict([
            ("property_id", key),
            ("canonical_name", item.get("canonical_name", c.get("canonical_name", ""))),
            ("street", c.get("street", "")),
            ("city", c.get("city", "")),
            ("postal_code", c.get("postal_code", "")),
            ("phone", c.get("phone", "")),
            ("corridor", item.get("corridor", c.get("corridor", ""))),
            ("brand", c.get("brand", "") or rr.get("brand_family", "")),
            ("property_code", c.get("property_code", "")),
            ("current_official_url", c.get("official_url", "")),
            ("current_route_status", rr.get("route", "") or "NONE"),
            ("current_hold_class", disp),
            ("hold_group", group),
            ("previous_provider_attempts", {
                "lanes_in_census": c.get("lanes", []),
                "disposition_basis": rr.get("disposition_basis", ""),
                "hold_reason": rr.get("hold_reason", item.get("next_action", "")),
            }),
            ("next_authorized_acquisition_action", item.get("next_action", "")),
        ])
        worklist.append(row)
        groups[group].append(key)

    assert len(worklist) == partition["unresolved"], (len(worklist), partition["unresolved"])
    seen = set()
    for row in worklist:
        assert row["property_id"] not in seen, f"duplicate {row['property_id']}"
        seen.add(row["property_id"])

    out = OrderedDict([
        ("schema", "ptf-tampa-fl-v2-closure-worklist/1.0"),
        ("work_order", "PTF-TAMPA-FL-V2-COVERAGE-CLOSURE-002"),
        ("market_id", MARKET),
        ("source_partition", "tampa_fl_final_partition_v2_001.json"),
        ("total_unresolved", len(worklist)),
        ("group_counts", OrderedDict(sorted((k, len(v)) for k, v in groups.items()))),
        ("items", worklist),
    ])
    with open("launch_packages/pettripfinder/markets/reports/tampa_fl_v2_closure_worklist_001.json",
              "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, sort_keys=False, ensure_ascii=False)
        f.write("\n")

    print("total_unresolved", len(worklist))
    print("group_counts", dict(out["group_counts"]))


if __name__ == "__main__":
    main()
