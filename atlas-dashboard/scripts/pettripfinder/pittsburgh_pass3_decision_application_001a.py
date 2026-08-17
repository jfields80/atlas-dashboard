"""Apply the five approved Pittsburgh Pass 3 founder decisions.

The application is deterministic and fail-closed: it validates the recorded
packet, authority hashes, retained artifacts, and final record contracts before
writing any authority. Sunnyledge is deliberately not an input to this writer.
"""
from __future__ import annotations

import argparse
import csv
import hashlib
import io
import json
import sys
from collections import Counter, OrderedDict
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.pettripfinder import canonical_view
from scripts.pettripfinder import hotel_exclusions as EX
from scripts.pettripfinder import market_authority as MA
from scripts.pettripfinder.contracts import enums, evidence as evidence_contract
from scripts.pettripfinder.contracts import policy_schema, withholding
from scripts.pettripfinder.contracts.fee_computation import classify
from scripts.pettripfinder.market_ownership import MARKET_ID_FIELD, owned_by
from scripts.pettripfinder.markets import assign_hotels, load_markets, market_by_id
from scripts.pettripfinder.policy_migration import evidence_hash, evidence_ref_for, record_hash
from scripts.pettripfinder.site_data import normalize_name, read_production_rows, verified_public_hotels

MARKET = "pittsburgh-pa"
WORK_ORDER = "PTF-PITTSBURGH-PASS3-DECISION-APPLICATION-001A"
DECISION_DATE = "2026-08-17"
FOUNDER = "jfields80"
LP = ROOT / "launch_packages" / "pettripfinder"
REPORTS = LP / "markets" / "reports"
FACTS_PATH = LP / "hotel_policy_facts_pittsburgh-pa.json"
EXCLUSIONS_PATH = MA.exclusions_shard_path(MARKET)
SEED_PATH = MA.seed_shard_path(MARKET)
CENSUS_PATH = LP / "identity_census" / "pittsburgh-pa.json"
PARTITION_PATH = LP / "pittsburgh_final_partition_001.json"
PACKET_PATH = REPORTS / "pittsburgh_pass3_founder_review_packet.json"
PLAN_PATH = REPORTS / "pittsburgh_pass3_decision_application_001a_plan.json"
SEMANTIC_PATH = REPORTS / "pittsburgh_pass3_semantic_render_001a.json"
APPLICATION_REPORT_PATH = REPORTS / "pittsburgh_pass3_application_001a_report.json"
RELEASE_CONTRACT_PATH = ROOT / "deploy" / "netlify" / "release_contracts" / "pittsburgh-pa.json"

POSITIVES = OrderedDict([
    ("PGH-P3-D001", {
        "facts": [
            ("pets_allowed", True, "Pets Welcome"),
            ("pet_fee", {"amount_cents": 10000, "currency": "USD", "basis": "per_stay", "refundable": False}, "Non-Refundable Pet Fee Per Stay: $100.00"),
            ("weight_limit", {"value": 90, "unit": "lb", "operator": "lte", "scope": "per_pet"}, "Maximum Pet Weight: 90.0lbs"),
            ("pet_count_limit", 2, "Maximum Number of Pets in Room: 2"),
            ("pet_count_scope", "room", "Maximum Number of Pets in Room: 2"),
            ("other_charges", [{"kind": "cleaning_fee", "amount_cents": 25000, "currency": "USD", "conditional": True, "trigger": "Must sign waiver stating cats are neutered or a $250.00 cleaning fee may apply."}], "Must sign waiver stating cats are neutered or a $250.00 cleaning fee may apply."),
        ],
        "note": "The conditional $250 cleaning charge remains a separate other_charges entry with its exact trigger and no refundability field.",
    }),
    ("PGH-P3-D002", {
        "facts": [
            ("pets_allowed", True, "Pets Welcome"),
            ("species", {"dogs": "accepted"}, "One dog up to 50 pounds allowed with a $75 pet fee."),
            ("pet_fee", {"amount_cents": 7500, "currency": "USD", "basis": "per_stay", "refundable": False}, "Non-Refundable Pet Fee Per Stay: $75.00"),
            ("weight_limit", {"value": 50, "unit": "lb", "operator": "lte", "scope": "per_pet"}, "Maximum Pet Weight: 50.0lbs"),
            ("pet_count_limit", 1, "Maximum Number of Pets in Room: 1"),
            ("pet_count_scope", "room", "Maximum Number of Pets in Room: 1"),
        ],
        "note": "Dogs only; no cats, reservation requirement, or unstated scope is added.",
    }),
    ("PGH-P3-D006", {
        "facts": [
            ("pets_allowed", True, "Pets Welcome"),
            ("weight_limit", {"value": 50, "unit": "lb", "operator": "lte", "scope": "per_pet"}, "Maximum Pet Weight: 50.0lbs"),
            ("pet_count_limit", 2, "Maximum Number of Pets in Room: 2"),
            ("pet_count_scope", "room", "Maximum Number of Pets in Room: 2"),
        ],
        "withheld": [{
            "field": "pet_fee", "reason_code": "SOURCE_CONTRADICTORY",
            "reason": "The property-specific source states '$20/night and Cleaning Fee is $50/stay' and separately 'Non-Refundable Pet Fee Per Stay: $50.00'. Per the founder decision, no monetary schedule is selected, combined, normalized, or synthesized.",
            "quotes": ["Pet Fee is $20/night and Cleaning Fee is $50/stay.", "Non-Refundable Pet Fee Per Stay: $50.00"],
        }],
        "note": "Only non-monetary pet facts publish; pet_fee remains SOURCE_CONTRADICTORY.",
    }),
])

NEGATIVES = OrderedDict([
    ("PGH-P3-D003", "Pets Not Allowed"),
    ("PGH-P3-D004", "Pets Not Allowed"),
])


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"), object_pairs_hook=OrderedDict)


def dump(path: Path, value: object) -> bytes:
    data = (json.dumps(value, indent=1, ensure_ascii=False) + "\n").encode("utf-8")
    path.write_bytes(data)
    return data


def file_sha(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def display(value: object) -> str:
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def verify_preflight(packet: dict, plan: dict) -> tuple[dict, dict]:
    assert packet["status"] == "FOUNDER_DECISIONS_RECORDED_NOT_APPLIED"
    assert plan["status"] == "PREPARED_NOT_EXECUTED"
    authority = plan["authority_before_application"]
    assert (authority["published"], authority["verified_no_pets"], authority["unresolved"]) == (26, 4, 63)
    for key, path in {
        "hotel_policy_facts_pittsburgh_pa": FACTS_PATH,
        "hotel_exclusions": EXCLUSIONS_PATH,
        "pittsburgh_final_partition": PARTITION_PATH,
    }.items():
        assert file_sha(path) == authority["authority_sha256"][key], "stale authority: " + key
    entries = {entry["decision_id"]: entry for entry in packet["entries"]}
    assert set(entries) == set(POSITIVES) | set(NEGATIVES) | {"PGH-P3-D005"}
    expected = {"PGH-P3-D001": "APPROVE_PUBLISH_STRUCTURED", "PGH-P3-D002": "APPROVE_PUBLISH_STRUCTURED", "PGH-P3-D003": "APPROVE_VERIFIED_NO_PETS", "PGH-P3-D004": "APPROVE_VERIFIED_NO_PETS", "PGH-P3-D006": "APPROVE_WITH_CHANGE"}
    for did, decision in expected.items():
        assert entries[did]["founder_decision"] == decision
        assert entries[did]["authority_application_status"] == "NOT_APPLIED"
    sunnyledge = entries["PGH-P3-D005"]
    assert sunnyledge["founder_decision"] == "NO_FOUNDER_POLICY_DECISION"
    assert sunnyledge["next_action"] == "RECAPTURE_REQUIRED"
    return entries, authority


def artifact(entry: dict) -> tuple[dict, str]:
    row = entry["artifacts"][0]
    path = ROOT / row["artifact_file"]
    assert file_sha(path) == row["artifact_sha256"], "artifact hash drift: " + entry["decision_id"]
    text = path.read_text(encoding="utf-8")
    for quote in (item["quote"] for item in entry["quotes"]):
        assert evidence_contract.quote_is_contiguous(quote, text), "quote drift: " + entry["decision_id"]
    return row, text


def evidence_entry(field: str, quote: str, value: object, entry: dict, art: dict) -> dict:
    result = OrderedDict([
        ("field", field), ("quote", quote), ("source_url", entry["final_url"]),
        ("value", display(value)), ("evidence_ref", ""),
        ("artifact_class", "PUBLICATION_GRADE_EVIDENCE"),
        ("artifact_sha256", art["artifact_sha256"]), ("artifact_kind", art["artifact_kind"]),
        ("captured_at", art["captured_at"]), ("capture_method", art["capture_method"]),
        ("source_grade", art["source_grade"]),
    ])
    result["evidence_ref"] = evidence_ref_for(result)
    return result


def build_positive(did: str, spec: dict, entry: dict, census_row: dict) -> dict:
    art, _ = artifact(entry)
    facts, evidence = OrderedDict(), []
    for field, value, quote in spec["facts"]:
        evidence.append(evidence_entry(field, quote, value, entry, art))
        facts[field] = value
    withheld_fields = OrderedDict()
    for item in spec.get("withheld", []):
        refs = []
        for quote in item["quotes"]:
            evidence.append(evidence_entry(item["field"], quote, "WITHHELD", entry, art))
            refs.append(evidence[-1]["evidence_ref"])
        withheld_fields[item["field"]] = withholding.withheld(item["field"], item["reason_code"], item["reason"], refs)
    quotes = []
    for item in evidence:
        if item["quote"] not in quotes:
            quotes.append(item["quote"])
    record = OrderedDict([
        ("key", census_row["identity_key"]), ("name", census_row["canonical_name"]),
        ("facts", facts), ("evidence", evidence), ("evidence_count", len(evidence)),
        ("evidence_quote", " […] ".join(quotes)), ("source_url", entry["final_url"]),
        ("source_type", "EXACT_ENTITY_DOMAIN"), ("verification_state", "VERIFIED_PET_FRIENDLY"),
        ("verification_date", DECISION_DATE), ("verified_at", DECISION_DATE),
        ("worker_model_id", ""), ("worker_prompt_version", ""),
        ("worker_result_hash", art["artifact_sha256"]), ("worker_routing_version", ""),
        ("worker_validator_version", ""), ("schema_version", "1.2"),
        ("identity_key", census_row["identity_key"]), ("market_id", MARKET),
    ])
    if withheld_fields:
        record["withheld_fields"] = withheld_fields
    record["computation_class"] = classify(facts).computation_class
    issues = list(policy_schema.validate_record(record)) + list(evidence_contract.validate(record)) + list(withholding.validate(record))
    assert not issues, (did, issues)
    record["approval"] = OrderedDict([
        ("decision", enums.APPROVED_AFTER_CURRENT_REVIEW), ("operator", FOUNDER),
        ("approval_date", DECISION_DATE),
        ("caveats", [
            "Founder decision %s recorded in pittsburgh_pass3_founder_review_packet.json and bound only after construction of this final record and its final evidence array." % did,
            "Every quote was revalidated contiguous in the retained hash-bound official-page rendered-text artifact. Identity binding: %s." % entry["identity_binding"],
            spec["note"],
        ]),
        ("record_hash", record_hash(record)), ("evidence_hash", evidence_hash(evidence)),
    ])
    return record


def build_exclusion(did: str, refusal: str, entry: dict, census_row: dict) -> dict:
    art, _ = artifact(entry)
    founder_binding = "sha256:" + hashlib.sha256(json.dumps({"decision_id": did, "founder_decision": entry["founder_decision"], "source": entry["founder_decision_source"]}, sort_keys=True).encode()).hexdigest()
    record = OrderedDict([
        ("exclusion_id", "pgh-" + census_row["slug"]), ("canonical_name", census_row["canonical_name"]),
        ("normalized_name", normalize_name(census_row["canonical_name"])), ("address", census_row["address"]),
        ("city", census_row["city"]), ("state", census_row["state"]), ("postal_code", census_row["postal_code"]),
        ("official_url", entry["final_url"]), ("exclusion_state", EX.VERIFIED_NO_PETS),
        ("evidence_quote", refusal), ("source_url", entry["final_url"]), ("observed_at", DECISION_DATE),
        ("source_hash", art["artifact_sha256"]), ("reviewer_id", FOUNDER), ("reviewed_at", DECISION_DATE),
        ("founder_decision_id", did), ("founder_decision_hash", founder_binding),
        ("notes", "Founder decision %s, %s: explicit property-specific first-party refusal bound to retained artifact %s and identity %s. Service-animal language is a legal-access exception and does not create pet-friendly authority." % (did, WORK_ORDER, art["artifact_sha256"], entry["identity_binding"])),
        ("market_id", MARKET),
    ])
    record["record_hash"] = EX.record_hash(record)
    record["approval_hash"] = EX.approval_hash(record)
    record["founder_evidence_binding_hash"] = "sha256:" + hashlib.sha256(json.dumps({
        "record_hash": record["record_hash"], "approval_hash": record["approval_hash"],
        "source_hash": record["source_hash"], "founder_decision_id": did,
        "founder_decision_hash": founder_binding,
    }, sort_keys=True).encode()).hexdigest()
    return record


def update_release_contract(facts: dict, exclusions: dict, partition: dict) -> None:
    contract = load(RELEASE_CONTRACT_PATH)
    counts = Counter(item["final_state"] for item in partition["items"])
    published = counts["PUBLISHED_PET_FRIENDLY"]
    no_pets = counts["VERIFIED_NO_PETS"]
    resolved = sum(count for state, count in counts.items() if state in enums.TERMINAL_STATES)
    unresolved = len(partition["items"]) - resolved
    reconciliation = contract["reconciliation"]
    reconciliation.update({"published_pet_friendly": published, "verified_no_pets": no_pets, "resolved": resolved, "unresolved": unresolved})
    reconciliation["note"] = "Pittsburgh Pass 3 applied five founder decisions: three artifact-backed publications and two explicit first-party refusals. Sunnyledge remains unresolved for RECAPTURE_REQUIRED. The final partition mechanically derives all counts."
    contract["description"] = "Deterministic release-gate contract for the PetTripFinder Pittsburgh market through PTF-PITTSBURGH-PASS3-DECISION-APPLICATION-001A."
    contract["deployment_authorization"]["means"] = "A passing contract is structural only; it is not a deployment authorization. %d of this market's %d confirmed identities remain unresolved; navigation and sitemap remain disabled and no founder deployment decision exists." % (unresolved, len(partition["items"]))
    package = contract["policy_package"]
    package["expected_sha256"] = hashlib.sha256(FACTS_PATH.read_bytes()).hexdigest()
    package["expected_record_count"] = len(facts["hotels"])
    public = contract["public_surface"]
    public["seed_hotel_rows"] = len(facts["hotels"])
    public["public_hotel_profile_count"] = len(facts["hotels"])
    contract["routes"]["hotel_route_count"] = len(facts["hotels"])
    market = market_by_id(load_markets(), MARKET)
    seeds = owned_by(read_production_rows(), MARKET, context="Pittsburgh release contract")
    policy_by_key = {record["key"]: record for record in facts["hotels"]}
    assignment = assign_hotels(market, verified_public_hotels(seeds, policy_by_key))
    contract["routes"]["published_corridor_route_count"] = len(assignment.published)
    dump(RELEASE_CONTRACT_PATH, contract)


def semantic_check(records: list[dict], partition: dict) -> dict:
    by_key = {record["identity_key"]: record for record in records}
    residence = by_key["residence inn pittsburgh north shore"]
    sheraton = by_key["sheraton pittsburgh hotel at station square"]
    oaklander = by_key["the oaklander hotel autograph collection"]
    failures = []
    residence_charge = residence["facts"]["other_charges"][0]
    if residence_charge.get("refundable") is not None or not residence_charge.get("conditional") or not residence_charge.get("trigger"):
        failures.append("Residence conditional charge changed")
    if sheraton["facts"].get("species") != {"dogs": "accepted"}:
        failures.append("Sheraton species changed")
    if "pet_fee" in oaklander["facts"] or oaklander.get("withheld_fields", {}).get("pet_fee", {}).get("reason_code") != "SOURCE_CONTRADICTORY":
        failures.append("Oaklander fee changed")
    states = {item["identity_key"]: item["final_state"] for item in partition["items"]}
    for key in ("springhill suites pittsburgh bakery square", "springhill suites pittsburgh north shore"):
        if states.get(key) != "VERIFIED_NO_PETS": failures.append(key + " not excluded")
    if states.get("sunnyledge boutique hotel") != "AWAITING_POLICY_OBSERVATION":
        failures.append("Sunnyledge changed")
    return {"schema": "ptf-pittsburgh-pass3-semantic-render/1.0", "work_order": WORK_ORDER, "unexpected_semantic_changes": failures, "unexpected_semantic_change_count": len(failures)}


def finalize_exclusion_bindings() -> int:
    """Add final founder/evidence bindings to an already-written exclusion pair."""
    packet = {entry["decision_id"]: entry for entry in load(PACKET_PATH)["entries"]}
    doc = load(EXCLUSIONS_PATH)
    changed = 0
    for record in doc["exclusions"]:
        did = record.get("founder_decision_id")
        if did not in NEGATIVES:
            continue
        entry = packet[did]
        assert record["record_hash"] == EX.record_hash(record)
        assert record["approval_hash"] == EX.approval_hash(record)
        founder_hash = "sha256:" + hashlib.sha256(json.dumps({"decision_id": did, "founder_decision": entry["founder_decision"], "source": entry["founder_decision_source"]}, sort_keys=True).encode()).hexdigest()
        assert record["founder_decision_hash"] == founder_hash
        binding = "sha256:" + hashlib.sha256(json.dumps({"record_hash": record["record_hash"], "approval_hash": record["approval_hash"], "source_hash": record["source_hash"], "founder_decision_id": did, "founder_decision_hash": founder_hash}, sort_keys=True).encode()).hexdigest()
        if record.get("founder_evidence_binding_hash") != binding:
            record["founder_evidence_binding_hash"] = binding
            changed += 1
    EX.validate(doc)
    dump(EXCLUSIONS_PATH, doc)
    MA.write_generated_artifacts()
    return changed


def run(apply: bool) -> dict:
    packet, plan = load(PACKET_PATH), load(PLAN_PATH)
    entries, authority = verify_preflight(packet, plan)
    census = {row["identity_key"]: row for row in load(CENSUS_PATH)["hotels"]}
    facts = load(FACTS_PATH)
    exclusions = load(EXCLUSIONS_PATH)
    assert len(facts["hotels"]) == 26
    assert sum(row.get("market_id") == MARKET and row.get("exclusion_state") == EX.VERIFIED_NO_PETS for row in exclusions["exclusions"]) == 4
    published = []
    existing_keys = {record["identity_key"] for record in facts["hotels"]}
    for did, spec in POSITIVES.items():
        entry = entries[did]
        assert entry["identity_key"] not in existing_keys
        published.append(build_positive(did, spec, entry, census[entry["identity_key"]]))
    new_exclusions = []
    existing_names = {row["normalized_name"] for row in exclusions["exclusions"]}
    for did, refusal in NEGATIVES.items():
        entry = entries[did]
        record = build_exclusion(did, refusal, entry, census[entry["identity_key"]])
        assert record["normalized_name"] not in existing_names
        new_exclusions.append(record)
    next_facts = OrderedDict(facts)
    next_facts["hotels"] = facts["hotels"] + published
    next_exclusions = OrderedDict(exclusions)
    next_exclusions["exclusions"] = exclusions["exclusions"] + new_exclusions
    EX.validate(next_exclusions)
    summary = {"published_added": len(published), "exclusions_added": len(new_exclusions), "authority_before": authority}
    if not apply:
        return summary
    dump(FACTS_PATH, next_facts)
    dump(EXCLUSIONS_PATH, next_exclusions)
    with SEED_PATH.open(encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh); rows = list(reader); fields = list(reader.fieldnames or [])
    seeds = []
    for record in published:
        row = census[record["identity_key"]]
        seeds.append({"name": record["name"], "category": "pet-friendly-hotels", "address": row["address"], "city": row["city"], "state": row["state"], "postal_code": row["postal_code"], "phone": row["phone"], "website_url": record["source_url"], "source_url": record["source_url"], "source_type": "OFFICIAL_PROPERTY", "observed_at": DECISION_DATE, "rating": "", "amenities": "", "pet_policy": record["evidence_quote"], "canonical": "", MARKET_ID_FIELD: MARKET})
    existing = {normalize_name(row["name"]) for row in rows if row.get(MARKET_ID_FIELD) == MARKET}
    assert not existing & {normalize_name(row["name"]) for row in seeds}
    buf = io.StringIO(newline="")
    writer = csv.DictWriter(buf, fieldnames=fields, lineterminator="\n")
    writer.writeheader()
    for row in rows + seeds:
        writer.writerow({key: row.get(key, "") for key in fields})
    SEED_PATH.write_text(buf.getvalue(), encoding="utf-8", newline="")
    MA.write_generated_artifacts()
    from scripts.pettripfinder import build_pittsburgh_market_001 as builder
    builder._AUTHORITY_CACHE = None
    builder.build()
    partition = load(PARTITION_PATH)
    counts = Counter(item["final_state"] for item in partition["items"])
    assert counts["PUBLISHED_PET_FRIENDLY"] == 29
    assert counts["VERIFIED_NO_PETS"] == 6
    assert sum(counts.values()) == 96
    semantic = semantic_check(published, partition)
    assert semantic["unexpected_semantic_change_count"] == 0, semantic
    dump(SEMANTIC_PATH, semantic)
    update_release_contract(next_facts, next_exclusions, partition)
    for record in load(FACTS_PATH)["hotels"]:
        approval = record["approval"]
        assert approval["decision"] == enums.APPROVED_AFTER_CURRENT_REVIEW
        assert approval["operator"] == FOUNDER
        assert approval["record_hash"] == record_hash(record)
        assert approval["evidence_hash"] == evidence_hash(record["evidence"])
    packet["status"] = "FOUNDER_DECISIONS_APPLIED"
    packet["applied_at"] = DECISION_DATE
    packet["application_work_order"] = WORK_ORDER
    for did, entry in entries.items():
        if did in POSITIVES:
            entry["authority_application_status"] = "APPLIED"; entry["outcome"] = "PUBLISHED"
        elif did in NEGATIVES:
            entry["authority_application_status"] = "APPLIED"; entry["outcome"] = "EXCLUDED_VERIFIED_NO_PETS"
        else:
            entry["authority_application_status"] = "NOT_APPLIED_RECAPTURE_REQUIRED"; entry["outcome"] = "RECAPTURE_REQUIRED"
    dump(PACKET_PATH, packet)
    unresolved = sum(count for state, count in counts.items() if state.startswith("AWAITING_"))
    report = {"schema": "ptf-pittsburgh-pass3-application-001a-report/1.0", "work_order": WORK_ORDER, "authority_before": authority, "authority_after": {"published": counts["PUBLISHED_PET_FRIENDLY"], "verified_no_pets": counts["VERIFIED_NO_PETS"], "unresolved": unresolved}, "published_decisions": list(POSITIVES), "exclusion_decisions": list(NEGATIVES), "not_applied": ["PGH-P3-D005"], "unexpected_semantic_change_count": 0}
    dump(APPLICATION_REPORT_PATH, report)
    summary.update({"partition_counts": dict(counts), "unresolved": unresolved, "semantic": semantic})
    return summary


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--finalize-exclusion-bindings", action="store_true")
    args = parser.parse_args()
    if args.finalize_exclusion_bindings:
        print("finalized exclusion founder/evidence bindings: %d" % finalize_exclusion_bindings())
        return
    summary = run(args.apply)
    print(json.dumps(summary, indent=2))
    if not args.apply:
        print("dry run: nothing written")


if __name__ == "__main__":
    main()
