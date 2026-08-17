"""Narrow, deterministic identity-only amendment for five Indianapolis rows.

Never invokes the legacy market factory and refuses to run if frozen policy
authority differs from the expected post-publication state.
"""
from __future__ import annotations

import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
PACKAGE = ROOT / "launch_packages" / "pettripfinder"
CANDIDATES = Path(__file__).with_name("indianapolis_candidates.py")
CENSUS = PACKAGE / "identity_census" / "indianapolis-in.json"
PARTITION = PACKAGE / "indianapolis_final_partition_001.json"
REVIEW = PACKAGE / "indianapolis_identity_repair_pass2_001.json"
REPORT = PACKAGE / "indianapolis_postpublication_identity_amendment_001.json"
POLICY = PACKAGE / "hotel_policy_facts_indianapolis-in.json"
EXCLUSIONS = PACKAGE / "hotel_exclusions.json"

AMENDMENTS = {
    "comfort inn indianapolis airport plainfield": ("6110 Cambridge Way", "6107 Cambridge Way", "317-204-3768", "in082", "ADDRESS_HYGIENE_ONLY"),
    "courtyard by marriott indianapolis airport": ("5525 Fortune Circle East", "2602 Fortune Circle East", "317-248-0300", "indca", "CURRENT_ADDRESS_REPLACEMENT"),
    "delta hotels by marriott indianapolis airport": ("2500 South High School Road", "5860 Fortune Circle West", "317-247-9700", "indde", "CURRENT_ADDRESS_REPLACEMENT"),
    "staybridge suites indianapolis airport plainfield": ("6291 Cambridge Way", "6295 Cambridge Way", "317-839-2700", "indpf", "ADDRESS_HYGIENE_ONLY"),
    "home2 suites by hilton indianapolis airport": ("9025 Hatfield Drive", "8345 Belfast Drive", "317-856-9900", "indcbht", "CURRENT_ADDRESS_REPLACEMENT"),
}

def digest(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()

def load(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))

def dump(path: Path, doc) -> None:
    path.write_text(json.dumps(doc, indent=2) + "\n", encoding="utf-8")

def frozen_snapshot():
    facts = load(POLICY)
    exclusions = load(EXCLUSIONS)
    published = [h for h in facts["hotels"] if h.get("published")]
    no_pets = [x for x in exclusions["exclusions"] if x.get("market_id") == "indianapolis-in"]
    if len(published) != 8 or len(no_pets) != 4:
        raise ValueError("frozen authority count precondition failed")
    return {"policy": digest(POLICY), "exclusions": digest(EXCLUSIONS),
            "published": len(published), "verified_no_pets": len(no_pets),
            "record_hashes": sorted(str(h.get("record_hash")) for h in published),
            "evidence_hashes": sorted(str(h.get("evidence_hash")) for h in published),
            "approval_hashes": sorted(str(h.get("approval_hash")) for h in published)}

def main() -> int:
    before = frozen_snapshot()
    census, partition, review = load(CENSUS), load(PARTITION), load(REVIEW)
    by_key = {x["identity_key"]: x for x in census["hotels"]}
    part_by_key = {x["identity_key"]: x for x in partition["items"]}
    for key, (old, new, phone, code, _) in AMENDMENTS.items():
        row = by_key[key]
        if row["address"] != old or row["phone"] != phone or code not in row["official_url"]:
            raise ValueError("census precondition failed: " + key)
        if "address" in part_by_key[key] and part_by_key[key]["address"] != old:
            raise ValueError("partition precondition failed: " + key)
    candidate_text = CANDIDATES.read_text(encoding="utf-8")
    for key, (old, new, _, _, _) in AMENDMENTS.items():
        if candidate_text.count('"' + old + '"') != 1:
            raise ValueError("candidate precondition failed: " + key)
        candidate_text = candidate_text.replace('"' + old + '"', '"' + new + '"')
        by_key[key]["address"] = new
        if "address" in part_by_key[key]:
            part_by_key[key]["address"] = new
    CANDIDATES.write_text(candidate_text, encoding="utf-8", newline="\n")
    dump(CENSUS, census); dump(PARTITION, partition)
    for row in review["outcomes"]:
        if row["identity_key"] in AMENDMENTS:
            row["outcome"] = "AMENDMENT_APPLIED"
            row["next_action"] = "Address amendment applied; policy remains unobserved."
    dump(REVIEW, review)
    after = frozen_snapshot()
    if before != after:
        raise ValueError("frozen policy authority drifted")
    if census["count"] != len(census["hotels"]) or len(partition["items"]) != len(census["hotels"]):
        raise ValueError("identity count changed")
    dump(REPORT, {"work_order": "PTF-INDIANAPOLIS-POSTPUBLICATION-IDENTITY-AMENDMENT-001",
                  "amendments": [{"identity_key": k, "old_address": v[0], "new_address": v[1], "classification": v[4]} for k, v in AMENDMENTS.items()],
                  "authority_before": before, "authority_after": after,
                  "census_count": census["count"], "routing_shard_updated": False})
    return 0

if __name__ == "__main__":
    raise SystemExit(main())
