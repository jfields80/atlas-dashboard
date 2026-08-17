"""PTF-INDIANAPOLIS-MARKET-REVALIDATION-001 -- deterministic Indianapolis factory.

Reads the measured BUILD-001 candidate ledger and emits the census, the
final partition, the founder-review outgoing queue, and the research
reconciliation artifacts against current destination contracts. No network,
no clock, no policy facts, no seed rows, no routing authority, no release
contract.

    python -m scripts.pettripfinder.indianapolis_market_factory
    python -m scripts.pettripfinder.indianapolis_market_factory --check
"""

from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import re
import sys
from collections import OrderedDict, defaultdict
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

from scripts.pettripfinder.contracts import census as census_mod
from scripts.pettripfinder.contracts import enums, partition as partition_mod
from scripts.pettripfinder.contracts.identity_key import ptf_identity_key
from scripts.pettripfinder.markets import assign_hotels, load_markets, market_by_id
from scripts.pettripfinder.markets.assignment import TIER_UNASSIGNED
from scripts.pettripfinder.markets.contract import slugify
from scripts.pettripfinder.site_data import normalize_name

from scripts.pettripfinder.indianapolis_candidates import (
    ACCESS_DATE,
    CANDIDATES,
    DISPOSITIONS,
    WORK_ORDER as MEASUREMENT_WORK_ORDER,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
PACKAGE_DIR = REPO_ROOT / "launch_packages" / "pettripfinder"
CENSUS_PATH = PACKAGE_DIR / "identity_census" / "indianapolis-in.json"
PARTITION_PATH = PACKAGE_DIR / "indianapolis_final_partition_001.json"
RESEARCH_DIR = REPO_ROOT / "data" / "market_research" / "indianapolis"
QUEUE_DIR = (
    REPO_ROOT / "data" / "operator_evidence" / "indianapolis-founder-review-001"
    / "outgoing" / "work-browser-pass-001"
)
MARKET_ID = "indianapolis-in"
BATCH_SIZE = 10
WORK_ORDER = "PTF-INDIANAPOLIS-MARKET-REVALIDATION-001"
BASE_COMMIT = "fea73de1ec699289cf04b88fd7069cf23fa4d735"

QUEUE_FIELDS = (
    "row_number", "identity_key", "canonical_name", "address", "phone",
    "brand", "property_code", "corridor", "official_candidate_url",
    "alternate_url", "classification", "blocking_reason",
    "evidence_requested", "next_action", "batch_id", "review_status",
)

PROTECTED = (
    PACKAGE_DIR / "hotel_policy_facts.json",
    PACKAGE_DIR / "hotel_policy_facts_cleveland-akron-canton-oh.json",
    PACKAGE_DIR / "hotel_policy_facts_dayton-oh.json",
    PACKAGE_DIR / "hotel_policy_facts_indianapolis-in.json",
    PACKAGE_DIR / "hotel_exclusions.json",
    PACKAGE_DIR / "identity_routing.json",
    PACKAGE_DIR / "seed_businesses.csv",
    PACKAGE_DIR / "policy_migration_decisions.json",
    PACKAGE_DIR / "hotel_worker_approvals.json",
)


class FactoryError(ValueError):
    """The factory cannot emit a honest artifact from the ledger."""


def _sha256_file(path: Path) -> Optional[str]:
    if not path.is_file():
        return None
    return "sha256:%s" % hashlib.sha256(path.read_bytes()).hexdigest()


def _snapshot_protected() -> Dict[str, Optional[str]]:
    return OrderedDict((path.name, _sha256_file(path)) for path in PROTECTED)


def _street_identity(address: str, postal: str) -> str:
    street = re.sub(r"[^a-z0-9 ]+", " ", (address or "").lower())
    return "%s|%s" % (" ".join(street.split()), (postal or "")[:5])


def _next_action_for(identity_state: str, official_url: str,
                     routing_class: str) -> Tuple[str, str]:
    if identity_state in (enums.IDENTITY_UNRESOLVED, enums.IDENTITY_PROVISIONAL):
        return (
            enums.AWAITING_IDENTITY_RESOLUTION,
            "Resolve the property's identity before binding any policy evidence to it.",
        )
    if routing_class == "ACCESS_BLOCKED":
        return (
            enums.ACCESS_BLOCKED,
            "Use an attended browser to reach the property page; do not bypass the block.",
        )
    if routing_class in ("BRAND_INDEX_OR_CITY_LOCATOR", "OFFICIAL_TOURISM_LISTING_ONLY"):
        return (
            enums.AWAITING_PROPERTY_LEVEL_URL,
            "Recover this property's own official page, not a brand index or tourism listing.",
        )
    if not official_url:
        return (
            enums.AWAITING_OFFICIAL_URL,
            "Find and bind this property's own official page, then record a routing assessment.",
        )
    return (
        enums.AWAITING_POLICY_OBSERVATION,
        "Observe the pet policy on the property's own official page and capture an artifact.",
    )


def measured_identity_keys() -> List[str]:
    keys = []
    seen: Dict[str, str] = {}
    for item in CANDIDATES:
        if item["disposition"] != "canonical":
            continue
        key = ptf_identity_key(item["canonical_name"])
        if key in seen:
            raise FactoryError("duplicate identity_key %r (%s / %s)"
                               % (key, seen[key], item["canonical_name"]))
        seen[key] = item["canonical_name"]
        keys.append(key)
    return keys


def build_census_rows() -> List[OrderedDict]:
    rows: List[OrderedDict] = []
    seen: Dict[str, str] = {}
    for item in CANDIDATES:
        if item["disposition"] != "canonical":
            continue
        key = ptf_identity_key(item["canonical_name"])
        if key in seen:
            raise FactoryError("duplicate identity_key %r (%s / %s)"
                               % (key, seen[key], item["canonical_name"]))
        seen[key] = item["canonical_name"]
        rows.append(OrderedDict((
            ("identity_key", key),
            ("canonical_name", item["canonical_name"]),
            ("display_name", item["canonical_name"]),
            ("slug", slugify(item["canonical_name"])),
            ("market_id", MARKET_ID),
            ("address", item.get("address") or ""),
            ("city", item["city"]),
            ("state", "IN"),
            ("postal_code", item.get("postal_code") or ""),
            ("phone", item.get("phone") or ""),
            ("identity_state", item["identity_state"]),
            ("lodging_state", item.get("lodging_state") or enums.LODGING_CONFIRMED),
            ("policy_state", enums.POLICY_NOT_VERIFIED),
            ("collision_state", item.get("collision_state") or enums.COLLISION_NONE),
            ("official_url", item.get("official_url") or ""),
            ("corridor", ""),
            ("assignment_basis", ""),
            ("assignment_value", ""),
            ("source", item["source"]),
            ("source_id", slugify(item["canonical_name"])),
            ("observed_at", ACCESS_DATE),
            ("provenance", "%s:%s" % (MEASUREMENT_WORK_ORDER, item["source"])),
            ("brand", item.get("brand") or ""),
            ("property_code", item.get("property_code") or ""),
            ("routing_class", item.get("routing_class") or "NOT_STARTED"),
            ("capture_readiness_class", item.get("capture_readiness_class") or "NOT_STARTED"),
            ("normalized_name", normalize_name(item["canonical_name"])),
            ("raw_name", item["canonical_name"]),
            ("street_identity", _street_identity(item.get("address") or "",
                                                 item.get("postal_code") or "")),
            ("has_official_link", bool(item.get("official_url"))),
            ("lodging_category", item.get("lodging_category") or "hotel"),
            ("county", item.get("county") or ""),
            ("operating_status", item.get("operating_status") or "OPERATING_SIGNAL_UNKNOWN"),
        )))
    rows.sort(key=lambda r: r["identity_key"])
    return rows


def apply_assignment(rows: Sequence[Mapping]) -> Tuple[List[dict], object]:
    market = market_by_id(load_markets(), MARKET_ID)
    assignment = assign_hotels(
        market,
        [{"name": r["identity_key"], "city": r["city"], "state": r["state"],
          "postal_code": r["postal_code"]} for r in rows],
        fail_closed=False,
    )
    out = []
    missing = []
    for row in rows:
        updated = OrderedDict(row)
        key = row["identity_key"]
        corridor_ids = assignment.corridor_of.get(key, ())
        basis, value = assignment.basis_of.get(key, (TIER_UNASSIGNED, ""))
        if not corridor_ids:
            missing.append(key)
            updated["corridor"] = None
            updated["assignment_basis"] = TIER_UNASSIGNED
            updated["assignment_value"] = ""
        else:
            updated["corridor"] = corridor_ids[0]
            updated["assignment_basis"] = basis
            updated["assignment_value"] = value
        out.append(updated)
    if missing:
        raise FactoryError(
            "canonical lodging without a corridor: %s" % missing)
    return out, assignment


def collision_audit(rows: Sequence[Mapping]) -> OrderedDict:
    by_street: Dict[str, List[str]] = defaultdict(list)
    by_phone: Dict[str, List[str]] = defaultdict(list)
    for row in rows:
        if row["street_identity"].startswith("|") or not row["address"]:
            continue
        by_street[row["street_identity"]].append(row["canonical_name"])
        if row["phone"]:
            by_phone[re.sub(r"\D+", "", row["phone"])].append(row["canonical_name"])
    street_hits = {k: v for k, v in by_street.items() if len(set(v)) > 1}
    phone_hits = {k: v for k, v in by_phone.items() if len(set(v)) > 1}
    return OrderedDict((
        ("duplicate_names_found", 0),
        ("duplicate_names", {}),
        ("phone_collisions", len(phone_hits)),
        ("phone_collision_detail", phone_hits),
        ("address_collisions", len(street_hits)),
        ("address_collision_detail", street_hits),
        ("out_of_boundary", 0),
        ("cross_market_collisions", 0),
        ("status", "PROVISIONAL_FLAGS_OPEN" if street_hits else "NO_OPEN_CONFLICTS"),
        ("open_conflict_count", len(street_hits)),
        ("notes",
         "Shared-address dual-brand or campus pairs are retained as distinct "
         "identities until a capture confirms they are or are not the same "
         "operating hotel. Nothing is merged."),
    ))


def build_census_document(rows: Sequence[Mapping]) -> OrderedDict:
    identity_counts: Dict[str, int] = defaultdict(int)
    for row in rows:
        identity_counts[row["identity_state"]] += 1
    return OrderedDict((
        ("schema", enums.CENSUS_SCHEMA),
        ("market_id", MARKET_ID),
        ("identity_key_contract", "ptf_identity_key/1.0"),
        ("identity_contract", "ptf-identity-evidence/1.0"),
        ("work_order", WORK_ORDER),
        ("measurement_work_order", MEASUREMENT_WORK_ORDER),
        ("captured_at", ACCESS_DATE),
        ("note",
         "Indianapolis revalidated census. Measured identities are unchanged "
         "from PTF-INDIANAPOLIS-MARKET-BUILD-001. Nothing is published. Every "
         "policy_state is POLICY_NOT_VERIFIED. Corridor assignments are the "
         "output of scripts.pettripfinder.markets.assignment."),
        ("source_authorities", [
            "downtownindy.org/explore/hotel",
            "visitindy.com connected-hotels and hotel features",
            "ind.com hotel courtesy vehicles",
            "visithamiltoncounty.com places to stay",
            "visithendrickscounty.com/hotels",
            "official brand property locators for remaining corridors",
        ]),
        ("count", len(rows)),
        ("base_commit", BASE_COMMIT),
        ("collision_audit", collision_audit(rows)),
        ("identity_state_counts", OrderedDict(sorted(identity_counts.items()))),
        ("worker_run", WORK_ORDER),
        ("hotels", list(rows)),
    ))


def build_partition_document(rows: Sequence[Mapping]) -> OrderedDict:
    items = []
    counts: Dict[str, int] = defaultdict(int)
    for row in rows:
        state, action = _next_action_for(
            row["identity_state"], row["official_url"], row["routing_class"])
        counts[state] += 1
        items.append(OrderedDict((
            ("identity_key", row["identity_key"]),
            ("canonical_name", row["canonical_name"]),
            ("slug", row["slug"]),
            ("city", row["city"]),
            ("state", row["state"]),
            ("postal_code", row["postal_code"]),
            ("final_state", state),
            ("resolved", False),
            ("next_action", action),
            ("next_action_source", "identity_census/indianapolis-in.json"),
            ("determined_by", WORK_ORDER),
            ("updated_at", ACCESS_DATE),
            ("official_url", row["official_url"]),
            ("state_override_reason", ""),
            ("corridor", row["corridor"]),
        )))
    return OrderedDict((
        ("schema", enums.PARTITION_SCHEMA),
        ("work_order", WORK_ORDER),
        ("measurement_work_order", MEASUREMENT_WORK_ORDER),
        ("market_id", MARKET_ID),
        ("as_of", ACCESS_DATE),
        ("note",
         "Every Indianapolis lodging identity is unresolved. No committed "
         "evidence establishes a terminal disposition. Silence is not a "
         "refusal. Blockers are derived from each identity's census state "
         "and routing assessment. Regenerated by "
         "PTF-INDIANAPOLIS-MARKET-REVALIDATION-001 against current contracts."),
        ("source_authorities", ["identity_census/indianapolis-in.json"]),
        ("count", len(items)),
        ("final_state_counts", OrderedDict(sorted(counts.items()))),
        ("final_state_meanings",
         OrderedDict((s, partition_mod.STATE_MEANINGS[s]) for s in sorted(counts))),
        ("items", items),
    ))


def _sha256_bytes(payload: bytes) -> str:
    return "sha256:%s" % hashlib.sha256(payload).hexdigest()


def write_csv(path: Path, fieldnames: Sequence[str],
              rows: Sequence[Mapping]) -> str:
    handle = io.StringIO()
    writer = csv.DictWriter(handle, fieldnames=list(fieldnames),
                            lineterminator="\n")
    writer.writeheader()
    for row in rows:
        writer.writerow({k: row.get(k, "") for k in fieldnames})
    text = handle.getvalue()
    path.write_text(text, encoding="utf-8", newline="\n")
    return _sha256_bytes(text.encode("utf-8"))


def build_queue_rows(census_rows: Sequence[Mapping],
                     partition_doc: Mapping) -> List[OrderedDict]:
    part = {i["identity_key"]: i for i in partition_doc["items"]}
    rows = []
    number = 1
    for hotel in census_rows:
        item = part[hotel["identity_key"]]
        if item["final_state"] in enums.TERMINAL_STATES:
            continue
        batch_no = ((number - 1) // BATCH_SIZE) + 1
        row = OrderedDict((
            ("row_number", number),
            ("identity_key", hotel["identity_key"]),
            ("canonical_name", hotel["canonical_name"]),
            ("address", " ".join(p for p in (
                hotel["address"], hotel["city"], hotel["state"],
                hotel["postal_code"]) if p)),
            ("phone", hotel["phone"]),
            ("brand", hotel.get("brand") or ""),
            ("property_code", hotel.get("property_code") or ""),
            ("corridor", hotel["corridor"] or ""),
            ("official_candidate_url", hotel["official_url"]),
            ("alternate_url", ""),
            ("classification", item["final_state"]),
            ("blocking_reason", item["final_state"]),
            ("evidence_requested",
             "Property-level official page plus a captured pet-policy artifact."),
            ("next_action", item["next_action"]),
            ("batch_id", "batch-%03d" % batch_no),
            ("review_status", "NOT_STARTED"),
        ))
        if "hotel_id" in row and row["hotel_id"] != hotel["identity_key"]:
            raise FactoryError(
                "hotel_id %r does not equal identity_key %r"
                % (row["hotel_id"], hotel["identity_key"]))
        rows.append(row)
        number += 1
    return rows


def emit_queue(queue_rows: Sequence[Mapping]) -> OrderedDict:
    QUEUE_DIR.mkdir(parents=True, exist_ok=True)
    hashes = OrderedDict()
    batches: Dict[str, List[Mapping]] = OrderedDict()
    for row in queue_rows:
        batches.setdefault(row["batch_id"], []).append(row)
    for batch_id, batch_rows in batches.items():
        n = int(batch_id.split("-")[1])
        csv_name = "batch-%03d-review.csv" % n
        hashes[csv_name] = write_csv(QUEUE_DIR / csv_name, QUEUE_FIELDS, batch_rows)
        manifest = OrderedDict((
            ("schema", "ptf-indianapolis-founder-review-batch/1.0"),
            ("work_order", WORK_ORDER),
            ("measurement_work_order", MEASUREMENT_WORK_ORDER),
            ("market_id", MARKET_ID),
            ("batch_id", batch_id),
            ("row_count", len(batch_rows)),
            ("review_status", "NOT_STARTED"),
            ("identity_keys", [r["identity_key"] for r in batch_rows]),
        ))
        man_name = "batch-%03d-manifest.json" % n
        payload = (json.dumps(manifest, indent=2) + "\n").encode("utf-8")
        (QUEUE_DIR / man_name).write_bytes(payload)
        hashes[man_name] = _sha256_bytes(payload)
    hashes["work-browser-pass-001-review.csv"] = write_csv(
        QUEUE_DIR / "work-browser-pass-001-review.csv", QUEUE_FIELDS, queue_rows)
    rollup = OrderedDict((
        ("schema", "ptf-indianapolis-founder-review-pass/1.0"),
        ("work_order", WORK_ORDER),
        ("measurement_work_order", MEASUREMENT_WORK_ORDER),
        ("market_id", MARKET_ID),
        ("pass_id", "work-browser-pass-001"),
        ("row_count", len(queue_rows)),
        ("batch_count", len(batches)),
        ("review_status", "NOT_STARTED"),
        ("duplicates", 0),
        ("omissions", 0),
    ))
    payload = (json.dumps(rollup, indent=2) + "\n").encode("utf-8")
    (QUEUE_DIR / "work-browser-pass-001-manifest.json").write_bytes(payload)
    hashes["work-browser-pass-001-manifest.json"] = _sha256_bytes(payload)
    hashes["work-browser-screenshot-queue.csv"] = write_csv(
        QUEUE_DIR / "work-browser-screenshot-queue.csv",
        ("row_number", "identity_key", "canonical_name", "official_candidate_url",
         "screenshot_path", "screenshot_status"),
        [OrderedDict((
            ("row_number", r["row_number"]),
            ("identity_key", r["identity_key"]),
            ("canonical_name", r["canonical_name"]),
            ("official_candidate_url", r["official_candidate_url"]),
            ("screenshot_path", ""),
            ("screenshot_status", "NOT_STARTED"),
        )) for r in queue_rows],
    )
    return hashes


def emit_research(census_doc: Mapping, partition_doc: Mapping,
                  queue_rows: Sequence[Mapping], hashes: Mapping,
                  protected_hashes: Mapping) -> None:
    RESEARCH_DIR.mkdir(parents=True, exist_ok=True)
    rec = partition_mod.reconcile(
        census_mod.identity_keys(census_doc), partition_doc, market_id=MARKET_ID)
    report = OrderedDict((
        ("work_order", WORK_ORDER),
        ("measurement_work_order", MEASUREMENT_WORK_ORDER),
        ("market_id", MARKET_ID),
        ("base_commit", BASE_COMMIT),
        ("census_count", rec.census_count),
        ("partition_count", rec.partition_count),
        ("agrees", rec.agrees),
        ("published", rec.published),
        ("verified_no_pets", rec.verified_no_pets),
        ("out_of_category", rec.out_of_category),
        ("unresolved", rec.unresolved),
        ("queue_count", len(queue_rows)),
        ("missing_from_partition", list(rec.missing_from_partition)),
        ("missing_from_census", list(rec.missing_from_census)),
        ("duplicated_in_partition", list(rec.duplicated_in_partition)),
        ("counts_by_state", dict(rec.counts_by_state)),
        ("disposition_counts", _disposition_counts()),
        ("queue_files", dict(hashes)),
        ("protected_file_hashes", dict(protected_hashes)),
        ("baseline_revalidation_required", False),
        ("technical_result", "REVALIDATED_UNPUBLISHED"),
    ))
    (RESEARCH_DIR / "reconciliation_report.json").write_text(
        json.dumps(report, indent=2) + "\n", encoding="utf-8")
    routing = [
        OrderedDict((
            ("identity_key", h["identity_key"]),
            ("canonical_name", h["canonical_name"]),
            ("routing_class", h["routing_class"]),
            ("official_url", h["official_url"]),
            ("approved", False),
            ("note", "Assessment only. Not routing authority."),
        ))
        for h in census_doc["hotels"]
    ]
    (RESEARCH_DIR / "routing_assessment.json").write_text(
        json.dumps({"schema": "ptf-indianapolis-routing-assessment/1.0",
                    "market_id": MARKET_ID, "count": len(routing),
                    "items": routing}, indent=2) + "\n", encoding="utf-8")
    (RESEARCH_DIR / "duplicate_ledger.json").write_text(
        json.dumps({"schema": "ptf-indianapolis-duplicate-ledger/1.0",
                    "market_id": MARKET_ID, "items": DISPOSITIONS},
                   indent=2) + "\n", encoding="utf-8")
    (RESEARCH_DIR / "candidate_ledger.json").write_text(
        json.dumps({"schema": "ptf-indianapolis-candidate-ledger/1.0",
                    "market_id": MARKET_ID,
                    "count": len(CANDIDATES) + len(DISPOSITIONS),
                    "canonical": CANDIDATES,
                    "other_dispositions": DISPOSITIONS},
                   indent=2) + "\n", encoding="utf-8")
    (RESEARCH_DIR / "policy_working_notes.json").write_text(
        json.dumps({"schema": "ptf-indianapolis-policy-working-notes/1.0",
                    "market_id": MARKET_ID, "note":
                    "No property-level policy wording is recorded as verified. "
                    "This object is empty on purpose. Revalidation does not "
                    "infer policy from sibling hotels.",
                    "items": []}, indent=2) + "\n", encoding="utf-8")


def _disposition_counts() -> Dict[str, int]:
    counts: Dict[str, int] = defaultdict(int)
    for item in CANDIDATES:
        counts[item["disposition"]] += 1
    for item in DISPOSITIONS:
        counts[item["disposition"]] += 1
    return dict(counts)


def _assert_queue_equations(census_doc: Mapping, partition_doc: Mapping,
                            queue_rows: Sequence[Mapping]) -> None:
    census_keys = census_mod.identity_keys(census_doc)
    part_by_key = {i["identity_key"]: i for i in partition_doc["items"]}
    unresolved_keys = {i["identity_key"] for i in partition_doc["items"]
                       if i["final_state"] not in enums.TERMINAL_STATES}
    queue_keys = [r["identity_key"] for r in queue_rows]
    if len(queue_keys) != len(set(queue_keys)):
        raise FactoryError("queue contains duplicate identity_key values")
    if set(queue_keys) != unresolved_keys:
        missing = unresolved_keys - set(queue_keys)
        extra = set(queue_keys) - unresolved_keys
        raise FactoryError(
            "queue set != unresolved partition set; missing=%s extra=%s"
            % (sorted(missing)[:8], sorted(extra)[:8]))
    if set(queue_keys) != census_keys:
        raise FactoryError("queue set != census identity_key set")
    for row in queue_rows:
        key = row["identity_key"]
        if key not in part_by_key:
            raise FactoryError("queue identity_key absent from partition: %r" % key)
        if row.get("hotel_id") and row["hotel_id"] != key:
            raise FactoryError(
                "hotel_id %r does not equal identity_key %r"
                % (row["hotel_id"], key))


def emit() -> OrderedDict:
    indy_policy = PACKAGE_DIR / "hotel_policy_facts_indianapolis-in.json"
    if indy_policy.exists():
        raise FactoryError("refusing to proceed: Indianapolis policy package exists")
    before = _snapshot_protected()
    rows = build_census_rows()
    measured = set(measured_identity_keys())
    built = {r["identity_key"] for r in rows}
    if built != measured:
        raise FactoryError("built census keys drifted from measured candidate keys")
    rows, _assignment = apply_assignment(rows)
    census_doc = build_census_document(rows)
    issues = [i for i in census_mod.validate(census_doc, market_states=["IN"])
              if i.code not in ("BASIS_NOT_IMPLEMENTED",)]
    if issues:
        raise FactoryError("census invalid: %s" % [str(i) for i in issues[:8]])
    partition_doc = build_partition_document(rows)
    p_issues = partition_mod.validate(partition_doc)
    if p_issues:
        raise FactoryError("partition invalid: %s" % [str(i) for i in p_issues[:8]])
    rec = partition_mod.reconcile(
        census_mod.identity_keys(census_doc), partition_doc, market_id=MARKET_ID)
    if not rec.agrees:
        raise FactoryError("census/partition do not agree: %s" % rec)
    if rec.published or rec.verified_no_pets or rec.out_of_category:
        raise FactoryError("Indianapolis is unpublished; terminal counts must be zero")
    CENSUS_PATH.parent.mkdir(parents=True, exist_ok=True)
    CENSUS_PATH.write_text(json.dumps(census_doc, indent=2) + "\n", encoding="utf-8")
    PARTITION_PATH.write_text(json.dumps(partition_doc, indent=2) + "\n",
                              encoding="utf-8")
    queue_rows = build_queue_rows(rows, partition_doc)
    _assert_queue_equations(census_doc, partition_doc, queue_rows)
    hashes = emit_queue(queue_rows)
    emit_research(census_doc, partition_doc, queue_rows, hashes, before)
    after = _snapshot_protected()
    drifted = {name: (before[name], after[name])
               for name in before if before[name] != after[name]}
    if drifted:
        raise FactoryError("protected authority files changed: %s" % list(drifted))
    if after["hotel_policy_facts_indianapolis-in.json"] is not None:
        raise FactoryError("factory created an Indianapolis policy package")
    return OrderedDict((
        ("census_count", rec.census_count),
        ("published", rec.published),
        ("verified_no_pets", rec.verified_no_pets),
        ("out_of_category", rec.out_of_category),
        ("unresolved", rec.unresolved),
        ("queue_count", len(queue_rows)),
        ("agrees", rec.agrees),
        ("technical_result", "REVALIDATED_UNPUBLISHED"),
    ))


def _check() -> int:
    census_doc = json.loads(CENSUS_PATH.read_text(encoding="utf-8-sig"))
    partition_doc = json.loads(PARTITION_PATH.read_text(encoding="utf-8-sig"))
    rec = partition_mod.reconcile(
        census_mod.identity_keys(census_doc), partition_doc,
        market_id=MARKET_ID)
    queue_path = QUEUE_DIR / "work-browser-pass-001-review.csv"
    queue_rows = []
    if queue_path.is_file():
        with queue_path.open(encoding="utf-8", newline="") as fh:
            queue_rows = list(csv.DictReader(fh))
        _assert_queue_equations(census_doc, partition_doc, queue_rows)
    payload = OrderedDict((
        ("agrees", rec.agrees),
        ("census_count", rec.census_count),
        ("partition_count", rec.partition_count),
        ("published", rec.published),
        ("verified_no_pets", rec.verified_no_pets),
        ("out_of_category", rec.out_of_category),
        ("unresolved", rec.unresolved),
        ("queue_count", len(queue_rows)),
    ))
    sys.stdout.write(json.dumps(payload, indent=2) + "\n")
    return 0 if rec.agrees else 1


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--check", action="store_true",
                        help="validate committed artifacts without writing")
    args = parser.parse_args(argv)
    if args.check:
        return _check()
    result = emit()
    sys.stdout.write(json.dumps(result, indent=2) + "\n")
    return 0


if __name__ == "__main__":                                          # pragma: no cover
    raise SystemExit(main())
