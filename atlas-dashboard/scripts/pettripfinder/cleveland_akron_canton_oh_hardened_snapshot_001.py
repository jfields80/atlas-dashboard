"""PTF-CLEVELAND-AKRON-CANTON-HARDENED-REVALIDATION-001 -- Phase 1.

Deterministic preservation snapshot of the LIVE Cleveland-Akron-Canton market
as it stands on the canonical lineage.  This is the "do not regress" baseline
every later phase of the order is measured against.

It reads only committed authority (plus the gitignored evidence mirror, whose
bytes are hashed and cross-checked against the hashes the pass-2/3/4 capture
results committed) and writes ONE report.  It never writes to any authority
file, the pinned census, the release contract or the deployment manifest.

Usage (from atlas-dashboard):
    python scripts/pettripfinder/cleveland_akron_canton_oh_hardened_snapshot_001.py [--out PATH]
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import os
import sys
from collections import Counter, OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

from scripts.pettripfinder.markets.contract import slugify  # noqa: E402
from scripts.pettripfinder.markets.routes import CATEGORY_ROOT  # noqa: E402

WORK_ORDER = "PTF-CLEVELAND-AKRON-CANTON-HARDENED-REVALIDATION-001"
MARKET_ID = "cleveland-akron-canton-oh"
SCHEMA = "ptf-market-preservation-snapshot/1.0"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
AUTH = os.path.join(PKG, "markets", "authority", MARKET_ID)
DEPLOY = os.path.join(_DASH, "deploy", "netlify")
EVIDENCE_ROOT = os.path.join(_DASH, "data", "worker_runs", "pettripfinder")

# Every file whose bytes this order promises not to regress.  Relative to
# atlas-dashboard so the report carries no machine path.
PROTECTED_FILES = [
    f"launch_packages/pettripfinder/identity_census/{MARKET_ID}.json",
    f"launch_packages/pettripfinder/hotel_policy_facts_{MARKET_ID}.json",
    f"launch_packages/pettripfinder/markets/authority/{MARKET_ID}/hotel_exclusions.json",
    f"launch_packages/pettripfinder/markets/authority/{MARKET_ID}/identity_routing.json",
    f"launch_packages/pettripfinder/markets/authority/{MARKET_ID}/seed_businesses.csv",
    f"launch_packages/pettripfinder/markets/authority/{MARKET_ID}/affiliate_destinations.json",
    f"launch_packages/pettripfinder/markets/{MARKET_ID}.json",
    f"launch_packages/pettripfinder/markets/coverage/{MARKET_ID}.json",
    f"launch_packages/pettripfinder/markets/reports/{MARKET_ID}_coverage_audit.json",
    "launch_packages/pettripfinder/cleveland_final_partition_002.json",
    "launch_packages/pettripfinder/cleveland_unresolved_manifest.json",
    f"deploy/netlify/release_contracts/{MARKET_ID}.json",
    "deploy/netlify/launch_participation.json",
    "deploy/netlify/global_deployment_manifest.json",
]

CAPTURE_RESULTS = [
    ("cleveland_pass2_capture_results.json", "cleveland-attended-capture-002"),
    ("cleveland_pass3_capture_results.json", "cleveland-attended-capture-003"),
    ("cleveland_pass4_capture_results.json", "cleveland-attended-capture-004"),
]


def sha256_bytes(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def sha256_file(path: str) -> str:
    with open(path, "rb") as fh:
        return sha256_bytes(fh.read())


def canonical_json(obj) -> bytes:
    return json.dumps(obj, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")


def read_json(rel: str):
    with open(os.path.join(_DASH, rel), "r", encoding="utf-8") as fh:
        return json.load(fh)


def build() -> "OrderedDict[str, object]":
    files = OrderedDict()
    for rel in PROTECTED_FILES:
        path = os.path.join(_DASH, rel)
        files[rel] = OrderedDict([
            ("sha256", sha256_file(path)),
            ("bytes", os.path.getsize(path)),
        ])

    census = read_json(PROTECTED_FILES[0])
    policy = read_json(PROTECTED_FILES[1])
    exclusions = read_json(PROTECTED_FILES[2])
    routing = read_json(PROTECTED_FILES[3])
    market = read_json(PROTECTED_FILES[6])
    partition = read_json(PROTECTED_FILES[9])
    unresolved = read_json(PROTECTED_FILES[10])
    contract = read_json(PROTECTED_FILES[11])
    participation = read_json(PROTECTED_FILES[12])
    manifest = read_json(PROTECTED_FILES[13])

    with open(os.path.join(AUTH, "seed_businesses.csv"), "r", encoding="utf-8", newline="") as fh:
        seed_rows = list(csv.DictReader(fh))

    census_rows = census["hotels"]
    policy_rows = policy["hotels"]
    exclusion_rows = exclusions["exclusions"]
    routing_rows = routing["routes"]

    # Per-record immutable checks: a canonical-JSON hash of every row, keyed on
    # the row's identity, so a later phase can prove no live row changed even
    # if a file is regenerated with different whitespace.
    census_hashes = OrderedDict((r["identity_key"], sha256_bytes(canonical_json(r))) for r in census_rows)
    policy_hashes = OrderedDict((r["identity_key"], sha256_bytes(canonical_json(r))) for r in policy_rows)
    exclusion_hashes = OrderedDict((r["exclusion_id"], sha256_bytes(canonical_json(r))) for r in exclusion_rows)
    routing_hashes = OrderedDict((r["routing_id"], sha256_bytes(canonical_json(r))) for r in routing_rows)

    # Routes exactly as markets/routes.hotel_route builds them for this
    # market (route_mode market_prefixed): /pet-friendly-hotels/<slug>/<hotel>/.
    market_slug = market["market_slug"]
    hotel_routes = []
    for r in policy_rows:
        hotel_routes.append("%s%s/%s/" % (CATEGORY_ROOT, market_slug, slugify(r["name"])))
    if len(set(hotel_routes)) != len(hotel_routes):
        raise SystemExit("duplicate hotel route in the live package")
    corridor_routes = ["%s%s/%s/" % (CATEGORY_ROOT, market_slug, slugify(c["corridor_id"].split("__", 1)[1]))
                       for c in market["corridors"]]

    # Owned evidence: the pass-2/3/4 artifacts.  We hash the mirrored bytes
    # and compare with the sha256 each capture-results document committed.
    evidence = OrderedDict()
    custody_agree = custody_disagree = custody_missing = 0
    for results_name, run_dir in CAPTURE_RESULTS:
        doc = read_json(f"launch_packages/pettripfinder/{results_name}")
        raw_dir = os.path.join(EVIDENCE_ROOT, run_dir, "raw")
        for row in doc["results"]:
            refs = [(row.get("artifact_file"), row.get("artifact_file_sha256"))]
            supp = row.get("supplementary_artifact")
            if isinstance(supp, dict) and supp.get("artifact_file"):
                refs.append((supp["artifact_file"], supp.get("artifact_file_sha256")))
            for name, committed_sha in refs:
                if not name:
                    continue
                path = os.path.join(raw_dir, name)
                entry = OrderedDict([("run", run_dir), ("results_document", results_name),
                                     ("committed_sha256", committed_sha)])
                if os.path.exists(path):
                    got = sha256_file(path)
                    entry["mirrored_sha256"] = got
                    entry["bytes"] = os.path.getsize(path)
                    if committed_sha and got == committed_sha:
                        entry["custody"] = "AGREES"
                        custody_agree += 1
                    elif committed_sha:
                        entry["custody"] = "DISAGREES"
                        custody_disagree += 1
                    else:
                        entry["custody"] = "UNPINNED"
                else:
                    entry["custody"] = "MISSING_FROM_MIRROR"
                    custody_missing += 1
                evidence[name] = entry

    pinned_policy_sha = contract["policy_package"]["expected_sha256"]
    policy_file_sha = files[PROTECTED_FILES[1]]["sha256"]

    participation_row = next(r for r in participation["markets"] if r["market_id"] == MARKET_ID) \
        if isinstance(participation.get("markets"), list) else participation["markets"][MARKET_ID]

    report = OrderedDict([
        ("schema", SCHEMA),
        ("work_order", WORK_ORDER),
        ("phase", "1 -- freeze / snapshot current live state"),
        ("market_id", MARKET_ID),
        ("what_this_is",
         "The do-not-regress baseline for the hardened revalidation of an ALREADY LIVE market. "
         "Every file below is hashed as committed on the canonical lineage; every live row carries "
         "a canonical-JSON hash; every owned evidence artifact is hashed and checked against the "
         "sha256 its capture-results document committed. Nothing in this order may change a "
         "protected file. Later phases prove preservation by re-deriving this document and "
         "comparing hashes."),
        ("canonical_head_expected", "9618a407a56edc6b26c036452412bcf271e5c8e6"),
        ("counts", OrderedDict([
            ("census_identities", len(census_rows)),
            ("policy_package_rows", len(policy_rows)),
            ("verified_no_pets_exclusions", len(exclusion_rows)),
            ("identity_routes", len(routing_rows)),
            ("identity_routes_by_status", OrderedDict(sorted(Counter(r["status"] for r in routing_rows).items()))),
            ("partition_items", len(partition["items"])),
            ("partition_final_state_counts", partition["final_state_counts"]),
            ("unresolved_manifest_items", len(unresolved["items"])),
            ("seed_rows", len(seed_rows)),
            ("hotel_routes", len(hotel_routes)),
            ("corridor_routes_declared", len(corridor_routes)),
            ("contract_hotel_route_count", contract["routes"]["hotel_route_count"]),
            ("contract_published_corridor_route_count", contract["routes"]["published_corridor_route_count"]),
        ])),
        ("release_contract", OrderedDict([
            ("contract_id", contract["contract_id"]),
            ("expected_census_count", contract["identity_census"]["expected_count"]),
            ("reconciliation", contract["reconciliation"]),
            ("policy_package_expected_sha256", pinned_policy_sha),
            ("policy_package_sha256_matches", pinned_policy_sha == policy_file_sha),
            ("grants_deployment", contract["deployment_authorization"]["grants_deployment"]),
        ])),
        ("launch_participation", OrderedDict([
            ("row", participation_row),
            ("decision_work_order", participation["decision"]["work_order"]),
        ])),
        ("global_deployment_manifest", OrderedDict([
            ("sha256", files[PROTECTED_FILES[13]]["sha256"]),
            ("source_commit", manifest.get("source_commit")),
            ("participating_markets", manifest.get("participating_markets")),
            ("total_published_profiles", manifest.get("total_published_profiles")),
        ])),
        ("protected_files", files),
        ("hotel_routes", hotel_routes),
        ("corridor_routes_declared", corridor_routes),
        ("row_hashes", OrderedDict([
            ("hash_rule", "sha256 of json.dumps(row, sort_keys=True, ensure_ascii=False, separators=(',',':'))"),
            ("census_by_identity_key", census_hashes),
            ("policy_by_identity_key", policy_hashes),
            ("exclusions_by_exclusion_id", exclusion_hashes),
            ("routing_by_routing_id", routing_hashes),
        ])),
        ("owned_evidence", OrderedDict([
            ("mirror_root", "data/worker_runs/pettripfinder/<run>/raw (gitignored; mirrored read-only from the main checkout)"),
            ("artifacts", len(evidence)),
            ("custody_agrees", custody_agree),
            ("custody_disagrees", custody_disagree),
            ("custody_missing", custody_missing),
            ("by_artifact", evidence),
        ])),
    ])
    return report


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(PKG, f"{MARKET_ID.replace('-', '_')}_hardened_snapshot_001.json"))
    args = ap.parse_args(argv)
    report = build()
    payload = json.dumps(report, indent=1, ensure_ascii=False) + "\n"
    with open(args.out, "wb") as fh:
        fh.write(payload.encode("utf-8"))
    c = report["counts"]
    print("snapshot written:", os.path.relpath(args.out, _DASH))
    print("census %d / policy %d / no-pets %d / routes %d / partition %d / unresolved %d / seed %d / hotel routes %d"
          % (c["census_identities"], c["policy_package_rows"], c["verified_no_pets_exclusions"], c["identity_routes"],
             c["partition_items"], c["unresolved_manifest_items"], c["seed_rows"], c["hotel_routes"]))
    ev = report["owned_evidence"]
    print("evidence artifacts %d: custody agrees %d / disagrees %d / missing %d"
          % (ev["artifacts"], ev["custody_agrees"], ev["custody_disagrees"], ev["custody_missing"]))
    print("policy package sha matches contract:", report["release_contract"]["policy_package_sha256_matches"])
    return 0 if ev["custody_disagrees"] == 0 and report["release_contract"]["policy_package_sha256_matches"] else 2


if __name__ == "__main__":
    raise SystemExit(main())
