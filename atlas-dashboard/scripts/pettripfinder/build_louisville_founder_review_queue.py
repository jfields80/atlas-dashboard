"""PTF-LOUISVILLE-MARKET-BUILD-001 -- outgoing founder-review queue.

Deterministic. Reads the committed Louisville census + partition and writes
batch CSVs and manifests. Does not approve, capture, or publish policy.

    python -m scripts.pettripfinder.build_louisville_founder_review_queue
    python -m scripts.pettripfinder.build_louisville_founder_review_queue --output <dir>
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import json
from collections import OrderedDict
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

from scripts.pettripfinder.contracts import census, enums, partition

REPO_ROOT = Path(__file__).resolve().parents[2]
PACKAGE_DIR = REPO_ROOT / "launch_packages" / "pettripfinder"
DEFAULT_OUT = (
    REPO_ROOT / "data" / "operator_evidence" / "louisville-founder-review-001"
    / "outgoing" / "work-browser-pass-001"
)
MARKET = "louisville-ky"
BATCH_SIZE = 10
REVIEW_STATUS = "NOT_STARTED"
WORK_ORDER = "PTF-LOUISVILLE-MARKET-BUILD-001"

CSV_FIELDS = [
    "identity_key",
    "hotel ID",
    "slug",
    "queued name",
    "corridor",
    "queued URL",
    "blocker",
    "evidence requested",
    "exactly one next action",
    "batch ID",
    "review_status",
    "final displayed name",
    "final URL",
    "displayed address",
    "displayed phone",
    "displayed ZIP",
    "visibly displayed property code",
    "exact visible policy wording",
    "supported facts",
    "withheld facts",
    "contradiction or warning",
    "comparison with prior recovery result",
    "browser classification",
    "proposed replacement URL",
    "identity keys supporting the proposed correction",
    "screenshot-ready",
]

EVIDENCE_BY_STATE = {
    enums.AWAITING_IDENTITY_RESOLUTION:
        "Confirm this is a distinct in-boundary lodging property and record a street address.",
    enums.AWAITING_OFFICIAL_URL:
        "Find and bind the property's own official page.",
    enums.AWAITING_POLICY_OBSERVATION:
        "Capture the pet-policy surface on the property's own official page.",
    enums.AWAITING_CENSUS_REVIEW:
        "Review this identity's presence and category in the market census.",
}


def _load(path: Path) -> Mapping:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _sha256_bytes(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def _csv_bytes(rows: Sequence[Mapping]) -> bytes:
    from io import StringIO
    buf = StringIO()
    writer = csv.DictWriter(buf, fieldnames=CSV_FIELDS, lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow({k: row.get(k, "") for k in CSV_FIELDS})
    return buf.getvalue().encode("utf-8")


def unresolved_rows(census_doc: Mapping, partition_doc: Mapping) -> List[Dict]:
    hotels = {h["identity_key"]: h for h in census_doc["hotels"]}
    items = [i for i in partition_doc["items"]
             if i["final_state"] not in enums.TERMINAL_STATES]
    items.sort(key=lambda i: i["identity_key"])
    out = []
    for item in items:
        hotel = hotels[item["identity_key"]]
        out.append({
            "identity_key": item["identity_key"],
            "hotel ID": item["identity_key"],
            "slug": item.get("slug") or hotel.get("slug") or "",
            "queued name": item.get("canonical_name") or hotel.get("canonical_name") or "",
            "corridor": hotel.get("corridor") or "",
            "queued URL": hotel.get("official_url") or "",
            "blocker": item["final_state"],
            "evidence requested": EVIDENCE_BY_STATE.get(
                item["final_state"], "Record the single next action already on the partition."),
            "exactly one next action": item.get("next_action") or "",
            "batch ID": "",
            "review_status": REVIEW_STATUS,
            "final displayed name": "",
            "final URL": "",
            "displayed address": hotel.get("address") or "",
            "displayed phone": hotel.get("phone") or "",
            "displayed ZIP": hotel.get("postal_code") or "",
            "visibly displayed property code": "",
            "exact visible policy wording": "",
            "supported facts": "",
            "withheld facts": "",
            "contradiction or warning": "",
            "comparison with prior recovery result": "",
            "browser classification": item["final_state"],
            "proposed replacement URL": "",
            "identity keys supporting the proposed correction": "",
            "screenshot-ready": "",
        })
    return out


def batch_rows(rows: Sequence[Mapping]) -> List[List[Dict]]:
    batches = []
    current: List[Dict] = []
    for row in rows:
        current.append(dict(row))
        if len(current) == BATCH_SIZE:
            batches.append(current)
            current = []
    if current:
        batches.append(current)
    for index, batch in enumerate(batches, start=1):
        batch_id = "batch-%03d" % index
        for row in batch:
            row["batch ID"] = batch_id
    return batches


def write_queue(destination: Path, *,
                census_doc: Optional[Mapping] = None,
                partition_doc: Optional[Mapping] = None) -> OrderedDict:
    census_doc = census_doc or _load(
        PACKAGE_DIR / "identity_census" / ("%s.json" % MARKET))
    partition_doc = partition_doc or _load(
        PACKAGE_DIR / "louisville_final_partition_001.json")
    rec = partition.reconcile(census.identity_keys(census_doc), partition_doc,
                              market_id=MARKET)
    if not rec.agrees:
        raise ValueError("census and partition do not agree; refusing to cut a queue")
    rows = unresolved_rows(census_doc, partition_doc)
    keys = [r["identity_key"] for r in rows]
    if len(keys) != len(set(keys)):
        raise ValueError("duplicate identity_key in unresolved queue")
    unresolved = {i["identity_key"] for i in partition_doc["items"]
                  if i["final_state"] not in enums.TERMINAL_STATES}
    if set(keys) != unresolved:
        raise ValueError("queue identity_key set does not equal unresolved partition set")

    destination.mkdir(parents=True, exist_ok=True)
    batches = batch_rows(rows)
    file_hashes = OrderedDict()
    for index, batch in enumerate(batches, start=1):
        csv_name = "batch-%03d-review.csv" % index
        man_name = "batch-%03d-manifest.json" % index
        payload = _csv_bytes(batch)
        (destination / csv_name).write_bytes(payload)
        digest = _sha256_bytes(payload)
        file_hashes[csv_name] = digest
        manifest = OrderedDict([
            ("schema", "ptf-louisville-founder-review-batch/1.0"),
            ("work_order", WORK_ORDER),
            ("market_id", MARKET),
            ("batch_id", "batch-%03d" % index),
            ("row_count", len(batch)),
            ("sha256", digest),
            ("review_status", REVIEW_STATUS),
            ("identity_keys", [r["identity_key"] for r in batch]),
        ])
        text = json.dumps(manifest, indent=2, ensure_ascii=False) + "\n"
        (destination / man_name).write_text(text, encoding="utf-8", newline="\n")
        file_hashes[man_name] = _sha256_bytes(text.encode("utf-8"))

    rollup_payload = _csv_bytes([row for batch in batches for row in batch])
    (destination / "work-browser-pass-001-review.csv").write_bytes(rollup_payload)
    rollup_digest = _sha256_bytes(rollup_payload)
    file_hashes["work-browser-pass-001-review.csv"] = rollup_digest

    screenshot_fields = ["identity_key", "hotel ID", "slug", "queued name",
                         "queued URL", "batch ID", "review_status"]
    from io import StringIO
    shot = StringIO()
    writer = csv.DictWriter(shot, fieldnames=screenshot_fields, lineterminator="\n")
    writer.writeheader()
    for row in (item for batch in batches for item in batch):
        writer.writerow({k: row.get(k, "") for k in screenshot_fields})
    shot_bytes = shot.getvalue().encode("utf-8")
    (destination / "work-browser-screenshot-queue.csv").write_bytes(shot_bytes)
    file_hashes["work-browser-screenshot-queue.csv"] = _sha256_bytes(shot_bytes)

    pass_manifest = OrderedDict([
        ("schema", "ptf-louisville-founder-review-pass/1.0"),
        ("work_order", WORK_ORDER),
        ("market_id", MARKET),
        ("pass_id", "work-browser-pass-001"),
        ("row_count", len(rows)),
        ("batch_count", len(batches)),
        ("sha256", rollup_digest),
        ("review_status", REVIEW_STATUS),
        ("identity_keys", keys),
        ("duplicates", 0),
        ("omissions", 0),
        ("files", file_hashes),
    ])
    text = json.dumps(pass_manifest, indent=2, ensure_ascii=False) + "\n"
    (destination / "work-browser-pass-001-manifest.json").write_text(
        text, encoding="utf-8", newline="\n")
    return pass_manifest


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=DEFAULT_OUT)
    args = parser.parse_args(argv)
    report = write_queue(args.output)
    print("wrote %s rows in %s batches to %s" % (
        report["row_count"], report["batch_count"], args.output))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
