"""Apply the ten approved Pittsburgh Pass 4 founder decisions.

The writer is intentionally fail-closed: all final records validate before it
writes either Pittsburgh authority shard.  It never touches the three holds.
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
WORK_ORDER = "PTF-PITTSBURGH-PASS4-DECISION-APPLICATION-001"
DECISION_DATE = "2026-08-17"
FOUNDER = "jfields80"
LP = ROOT / "launch_packages" / "pettripfinder"
REPORTS = LP / "markets" / "reports"
FACTS_PATH = LP / "hotel_policy_facts_pittsburgh-pa.json"
EXCLUSIONS_PATH = MA.exclusions_shard_path(MARKET)
SEED_PATH = MA.seed_shard_path(MARKET)
CENSUS_PATH = LP / "identity_census" / "pittsburgh-pa.json"
PARTITION_PATH = LP / "pittsburgh_final_partition_001.json"
PACKET_PATH = REPORTS / "pittsburgh_pass4_claude_founder_review_packet.json"
PLAN_PATH = REPORTS / "pittsburgh_pass4_decision_application_001_plan.json"
SEMANTIC_PATH = REPORTS / "pittsburgh_pass4_semantic_render_001.json"
REPORT_PATH = REPORTS / "pittsburgh_pass4_application_001_report.json"
RELEASE_CONTRACT_PATH = ROOT / "deploy" / "netlify" / "release_contracts" / "pittsburgh-pa.json"


def tier(amount: int, minimum: int, maximum: int | None) -> dict:
    value = OrderedDict([
        ("amount_cents", amount), ("currency", "USD"),
        ("role", enums.ROLE_REPLACEMENT_PRICE),
        ("condition_type", enums.CONDITION_STAY_LENGTH_RANGE),
        ("condition_min", minimum), ("boundary_unit", enums.BOUNDARY_NIGHTS),
        ("basis_stated", False),
    ])
    if maximum is not None:
        value["condition_max"] = maximum
    return value


POSITIVES = OrderedDict([
    ("PGH-P4-C003", {"facts": [("pets_allowed", True, ["This pet-friendly motel welcomes your four-legged companions, so you can travel with peace of mind knowing your pets are part of the journey."])], "note": "Only pets_allowed publishes; no brand-wide Motel 6 terms are imported."}),
    ("PGH-P4-C004", {"facts": [
        ("pets_allowed", True, ["Sonesta Simply Suites Pittsburg Airport is pet-friendly and welcomes well-mannered pets, with no breed or weight restrictions. Up to two pets are permitted per suite."]),
        ("pet_count_limit", 2, ["Sonesta Simply Suites Pittsburg Airport is pet-friendly and welcomes well-mannered pets, with no breed or weight restrictions. Up to two pets are permitted per suite."]),
        ("weight_limit_stated_none", True, ["Sonesta Simply Suites Pittsburg Airport is pet-friendly and welcomes well-mannered pets, with no breed or weight restrictions. Up to two pets are permitted per suite."]),
        ("breed_restrictions_stated_none", True, ["Sonesta Simply Suites Pittsburg Airport is pet-friendly and welcomes well-mannered pets, with no breed or weight restrictions. Up to two pets are permitted per suite."]),
        ("fee_tiers", [tier(7500, 1, 7), tier(15000, 8, None)], ["$75 fee applies for stays up to 7 nights; $150 for all longer stays."]),
    ], "withheld": [("fee_tiers.basis", enums.SOURCE_AMBIGUOUS, "The duration bands state amounts and stay applicability, not a canonical per-night, per-day, or per-stay basis.", ["$75 fee applies for stays up to 7 nights; $150 for all longer stays."])], "note": "Species and suite-to-room scope remain absent; no fee basis or refundability is inferred."}),
    ("PGH-P4-C005", {"facts": [
        ("pets_allowed", True, ["Pets Welcome"]),
        ("pet_fee", {"amount_cents": 15000, "currency": "USD", "basis": "per_stay", "refundable": False}, ["Non-Refundable Pet Fee Per Stay: $150.00"]),
    ], "note": "No species, count, scope, weight, or reservation requirement was added."}),
    ("PGH-P4-C006", {"facts": [
        ("pets_allowed", True, ["Pets Welcome"]),
        ("pet_fee", {"amount_cents": 7500, "currency": "USD", "basis": "per_stay", "scope": "per_pet", "refundable": False}, ["2 pets 75 pounds or less with USD 75 non-refundable fee per pet per stay"]),
        ("weight_limit", {"value": 75, "unit": "lb", "operator": "lte", "scope": "per_pet"}, ["2 pets 75 pounds or less with USD 75 non-refundable fee per pet per stay"]),
        ("pet_count_limit", 2, ["Maximum Number of Pets in Room: 2"]),
        ("pet_count_scope", "room", ["Maximum Number of Pets in Room: 2"]),
    ], "note": "Species, reservation requirement, and service-animal terms remain absent."}),
    ("PGH-P4-C007", {"facts": [
        ("pets_allowed", True, ["Our hotel is designed to bring home comfort to every guest—even the ones with four legs. Relax with up to two of your furry friends in a spacious, suite-inspired room."]),
        ("pet_count_limit", 2, ["Maximum number of pets is 2."]),
        ("weight_limit", {"value": 25, "unit": "lb", "operator": "lte", "scope": "per_pet"}, ["Individual pet weight limit: 25 Pounds"]),
        ("combined_weight_limit", {"value": 50, "unit": "lb", "operator": "lte"}, ["Combined pets weight limit: 50 Pounds"]),
        ("fee_tiers", [tier(7500, 1, 6), tier(27500, 7, 30)], ["1-6 nights:", "$75", "7-30 nights (includes cleaning fee):", "$275"]),
    ], "withheld": [("fee_tiers.basis", enums.SOURCE_AMBIGUOUS, "The source states stay-length amounts but no canonical fee basis; its $275 tier already says it includes a cleaning fee.", ["1-6 nights:", "$75", "7-30 nights (includes cleaning fee):", "$275"])], "note": "The included cleaning component is not split into a synthetic charge."}),
    ("PGH-P4-C008", {"facts": [
        ("pets_allowed", True, ["Our hotel is pet friendly for up to two housebroken dogs. Please call ahead at +1 412 494 0202 to let us know you'll be bringing canine company."]),
        ("species", {"dogs": "accepted"}, ["Our hotel is pet friendly for up to two housebroken dogs. Please call ahead at +1 412 494 0202 to let us know you'll be bringing canine company."]),
        ("pet_count_limit", 2, ["Maximum number of pets is 2."]),
        ("weight_limit", {"value": 50, "unit": "lb", "operator": "lte", "scope": "per_pet"}, ["Individual pet weight limit: 50 Pounds"]),
        ("combined_weight_limit", {"value": 75, "unit": "lb", "operator": "lte"}, ["Combined pets weight limit: 75 Pounds"]),
    ], "withheld": [("pet_fee", enums.SOURCE_AMBIGUOUS, "The source gives stay-length dollar figures while also naming an additional cleaning fee without a complete separable monetary relationship.", ["1–6 nights:", "$100", "7–30 nights + additional cleaning fee:", "$200"])], "note": "The call-ahead wording is retained in evidence but is not transformed into a reservation requirement."}),
    ("PGH-P4-C009", {"facts": [
        ("pets_allowed", True, ["We welcome a maximum of two canine companions. Please call us at +1 412 321 3000 prior to your arrival to let us know you’ll be bringing your dog(s), which must be housebroken."]),
        ("species", {"dogs": "accepted"}, ["We welcome a maximum of two canine companions. Please call us at +1 412 321 3000 prior to your arrival to let us know you’ll be bringing your dog(s), which must be housebroken."]),
        ("pet_count_limit", 2, ["Maximum number of pets is 2."]),
        ("weight_limit", {"value": 50, "unit": "lb", "operator": "lte", "scope": "per_pet"}, ["Individual pet weight limit: 50 Pounds"]),
        ("combined_weight_limit", {"value": 75, "unit": "lb", "operator": "lte"}, ["Combined pets weight limit: 75 Pounds"]),
        ("fee_tiers", [tier(7500, 1, 6), tier(7500, 7, 30)], ["1 - 6 nights:", "$75", "7 - 30 nights :"]),
        ("other_charges", [{"kind": "cleaning_fee", "amount_cents": 10000, "currency": "USD", "conditional": True, "trigger": "7 - 30 nights"}], ["7 - 30 nights :", "+ $100", "Cleaning fee"]),
    ], "withheld": [("fee_tiers.basis", enums.SOURCE_AMBIGUOUS, "Stay-length applicability does not establish a canonical fee basis; refundability is unstated and absent.", ["1 - 6 nights:", "$75", "7 - 30 nights :", "+ $100", "Cleaning fee"])], "note": "The $100 cleaning fee is a distinct conditional charge; refundability remains absent."}),
    ("PGH-P4-C011", {"facts": [
        ("pets_allowed", True, ["Yes, $50 Pet Fee per night up to 2 pets."]),
        ("pet_count_limit", 2, ["Yes, $50 Pet Fee per night up to 2 pets."]),
    ], "withheld": [("pet_fee", enums.SOURCE_CONTRADICTORY, "The same property FAQ says both that a $50 fee applies and that it is $50 per night, while its answer to whether there are pet fees or weight restrictions is 'No.' No monetary policy is selected.", ["Yes. Pet Fee applies $50.", "Yes, $50 Pet Fee per night up to 2 pets.", "No."])], "note": "Only the approved non-fee facts publish; species, weight, and service-animal terms remain absent."}),
])
NEGATIVES = OrderedDict([("PGH-P4-C001", "Pets Not Allowed"), ("PGH-P4-C002", "Pets Not Allowed")])


def load(path: Path) -> dict:
    return json.loads(path.read_text(encoding="utf-8-sig"), object_pairs_hook=OrderedDict)


def dump(path: Path, value: object) -> None:
    path.write_bytes((json.dumps(value, indent=1, ensure_ascii=False) + "\n").encode("utf-8"))


def file_sha(path: Path) -> str:
    return "sha256:" + hashlib.sha256(path.read_bytes()).hexdigest()


def display(value: object) -> str:
    return str(value).lower() if isinstance(value, bool) else (value if isinstance(value, str) else json.dumps(value, ensure_ascii=False, sort_keys=True))


def verify_preflight(packet: dict, plan: dict) -> tuple[dict, bool]:
    assert packet["status"] == "ALL_FOUNDER_DECISIONS_RECORDED_APPLICATION_PREP_PENDING"
    assert packet["decisions_recorded"] == 10 and packet["decisions_applied"] == 0
    assert plan["status"] == "PREPARED_NOT_EXECUTED" and plan["authority_changes_executed"] is False
    before = plan["authority_before"]
    assert {key: before[key] for key in ("census", "published", "verified_no_pets", "out_of_category", "unresolved")} == {"census": 96, "published": 29, "verified_no_pets": 6, "out_of_category": 3, "unresolved": 58}
    hashes_match = (file_sha(FACTS_PATH) == before["policy_facts_sha256"]
                    and file_sha(EXCLUSIONS_PATH) == before["exclusions_sha256"]
                    and file_sha(PARTITION_PATH) == before["partition_sha256"])
    entries = {entry["capture_id"]: entry for entry in packet["entries"]}
    assert list(entries) == list(NEGATIVES) + list(POSITIVES)
    assert len(entries) == len(set(entries)) == 10
    for did, entry in entries.items():
        assert entry["authority_application_status"] == "NOT_APPLIED"
        assert entry["founder_review_required"] is False
        art = entry["artifacts"][0]
        path = ROOT / art["artifact_file"]
        assert path.is_file() and file_sha(path) == art["artifact_sha256"], "artifact drift: " + did
        text = path.read_text(encoding="utf-8")
        assert all(evidence_contract.quote_is_contiguous(q["quote"], text) for q in entry["quotes"]), "quote drift: " + did
    holds = {row["hotel"]: row["state"] for row in plan["excluded_from_application"]}
    assert holds == {"Hyatt Regency Pittsburgh International Airport": "IDENTITY_UNCERTAIN", "Mansions on Fifth": "POLICY_NOT_FOUND", "Sunnyledge Boutique Hotel": "SOURCE_AMBIGUOUS"}
    return entries, not hashes_match


def evidence_entry(field: str, quote: str, value: object, entry: dict, artifact: dict) -> dict:
    row = OrderedDict([("field", field), ("quote", quote), ("source_url", entry["final_url"]), ("value", display(value)), ("evidence_ref", ""), ("artifact_class", "PUBLICATION_GRADE_EVIDENCE"), ("artifact_sha256", artifact["artifact_sha256"]), ("artifact_kind", artifact["artifact_kind"]), ("captured_at", artifact["captured_at"]), ("capture_method", artifact["capture_method"]), ("source_grade", artifact["source_grade"])])
    row["evidence_ref"] = evidence_ref_for(row)
    return row


def build_positive(did: str, spec: dict, entry: dict, census: dict) -> dict:
    artifact = entry["artifacts"][0]
    facts, evidence = OrderedDict(), []
    for field, value, quotes in spec["facts"]:
        facts[field] = value
        evidence.extend(evidence_entry(field, quote, value, entry, artifact) for quote in quotes)
    withheld_fields = OrderedDict()
    for field, reason_code, reason, quotes in spec.get("withheld", []):
        refs = []
        for quote in quotes:
            evidence.append(evidence_entry(field, quote, "WITHHELD", entry, artifact))
            refs.append(evidence[-1]["evidence_ref"])
        withheld_fields[field] = withholding.withheld(field, reason_code, reason, refs)
    unique_quotes = list(dict.fromkeys(row["quote"] for row in evidence))
    record = OrderedDict([("key", census["identity_key"]), ("name", census["canonical_name"]), ("facts", facts), ("evidence", evidence), ("evidence_count", len(evidence)), ("evidence_quote", " […] ".join(unique_quotes)), ("source_url", entry["final_url"]), ("source_type", "EXACT_ENTITY_DOMAIN"), ("verification_state", "VERIFIED_PET_FRIENDLY"), ("verification_date", DECISION_DATE), ("verified_at", DECISION_DATE), ("worker_model_id", ""), ("worker_prompt_version", ""), ("worker_result_hash", artifact["artifact_sha256"]), ("worker_routing_version", ""), ("worker_validator_version", ""), ("schema_version", "1.2"), ("identity_key", census["identity_key"]), ("market_id", MARKET)])
    if withheld_fields:
        record["withheld_fields"] = withheld_fields
    record["computation_class"] = classify(facts).computation_class
    issues = list(policy_schema.validate_record(record)) + list(evidence_contract.validate(record)) + list(withholding.validate(record))
    assert not issues, (did, issues)
    record["approval"] = OrderedDict([("decision", enums.APPROVED_AFTER_CURRENT_REVIEW), ("operator", FOUNDER), ("approval_date", DECISION_DATE), ("caveats", ["Founder decision %s in pittsburgh_pass4_claude_founder_review_packet.json was bound after construction of this final record and its evidence array." % did, "Every quote was revalidated contiguous in the retained hash-bound official property artifact. Identity binding: %s." % entry["identity_binding"], spec["note"]]), ("record_hash", record_hash(record)), ("evidence_hash", evidence_hash(evidence))])
    return record


def build_exclusion(did: str, quote: str, entry: dict, census: dict) -> dict:
    artifact = entry["artifacts"][0]
    founder_hash = "sha256:" + hashlib.sha256(json.dumps({"capture_id": did, "founder_decision": entry["founder_decision"], "source": entry["founder_decision_source"]}, sort_keys=True).encode()).hexdigest()
    record = OrderedDict([("exclusion_id", "pgh-" + census["slug"]), ("canonical_name", census["canonical_name"]), ("normalized_name", normalize_name(census["canonical_name"])), ("address", census["address"]), ("city", census["city"]), ("state", census["state"]), ("postal_code", census["postal_code"]), ("official_url", entry["final_url"]), ("exclusion_state", EX.VERIFIED_NO_PETS), ("evidence_quote", quote), ("source_url", entry["final_url"]), ("observed_at", DECISION_DATE), ("source_hash", artifact["artifact_sha256"]), ("reviewer_id", FOUNDER), ("reviewed_at", DECISION_DATE), ("founder_decision_id", did), ("founder_decision_hash", founder_hash), ("notes", "Founder decision %s, %s: explicit property-specific first-party refusal bound to retained artifact %s and identity %s." % (did, WORK_ORDER, artifact["artifact_sha256"], entry["identity_binding"])), ("market_id", MARKET)])
    record["record_hash"] = EX.record_hash(record); record["approval_hash"] = EX.approval_hash(record)
    record["founder_evidence_binding_hash"] = "sha256:" + hashlib.sha256(json.dumps({"record_hash": record["record_hash"], "approval_hash": record["approval_hash"], "source_hash": record["source_hash"], "founder_decision_id": did, "founder_decision_hash": founder_hash}, sort_keys=True).encode()).hexdigest()
    return record


def write_seed_rows(records: list[dict], census: dict) -> None:
    with SEED_PATH.open(encoding="utf-8-sig", newline="") as fh:
        reader = csv.DictReader(fh); rows = list(reader); fields = list(reader.fieldnames or [])
    new_rows = []
    for record in records:
        row = census[record["identity_key"]]
        new_rows.append({"name": record["name"], "category": "pet-friendly-hotels", "address": row["address"], "city": row["city"], "state": row["state"], "postal_code": row["postal_code"], "phone": row["phone"], "website_url": record["source_url"], "source_url": record["source_url"], "source_type": "OFFICIAL_PROPERTY", "observed_at": DECISION_DATE, "rating": "", "amenities": "", "pet_policy": record["evidence_quote"], "canonical": "", MARKET_ID_FIELD: MARKET})
    existing = {normalize_name(row["name"]) for row in rows if row.get(MARKET_ID_FIELD) == MARKET}
    assert not existing & {normalize_name(row["name"]) for row in new_rows}
    text = io.StringIO(newline=""); writer = csv.DictWriter(text, fieldnames=fields, lineterminator="\n"); writer.writeheader()
    for row in rows + new_rows: writer.writerow({key: row.get(key, "") for key in fields})
    SEED_PATH.write_text(text.getvalue(), encoding="utf-8", newline="")


def update_release_contract(facts: dict, partition: dict) -> None:
    contract = load(RELEASE_CONTRACT_PATH); counts = Counter(item["final_state"] for item in partition["items"])
    unresolved = sum(count for state, count in counts.items() if state.startswith("AWAITING_"))
    contract["description"] = "Deterministic release-gate contract for the PetTripFinder Pittsburgh market through PTF-PITTSBURGH-PASS4-DECISION-APPLICATION-001."
    contract["reconciliation"].update({"published_pet_friendly": counts["PUBLISHED_PET_FRIENDLY"], "verified_no_pets": counts["VERIFIED_NO_PETS"], "out_of_current_category": counts["OUT_OF_CURRENT_CATEGORY"], "resolved": len(partition["items"]) - unresolved, "unresolved": unresolved, "note": "Pittsburgh Pass 4 applied eight artifact-backed publications and two explicit first-party refusals. Hyatt Regency, Mansions on Fifth, and Sunnyledge remain unresolved in their distinct hold states; partition counts are mechanically derived."})
    contract["deployment_authorization"]["means"] = "A passing contract is structural only; it is not a deployment authorization. %d of this market's %d confirmed identities remain unresolved; navigation and sitemap remain disabled and no founder deployment decision exists." % (unresolved, len(partition["items"]))
    package = contract["policy_package"]; package["expected_sha256"] = hashlib.sha256(FACTS_PATH.read_bytes()).hexdigest(); package["expected_record_count"] = len(facts["hotels"])
    public = contract["public_surface"]; public["seed_hotel_rows"] = len(facts["hotels"]); public["public_hotel_profile_count"] = len(facts["hotels"])
    contract["routes"]["hotel_route_count"] = len(facts["hotels"])
    market = market_by_id(load_markets(), MARKET); seeds = owned_by(read_production_rows(), MARKET, context="Pittsburgh release contract")
    assignment = assign_hotels(market, verified_public_hotels(seeds, {record["key"]: record for record in facts["hotels"]}))
    contract["routes"]["published_corridor_route_count"] = len(assignment.published)
    dump(RELEASE_CONTRACT_PATH, contract)


def semantic_check(records: list[dict], partition: dict) -> dict:
    by_key = {record["identity_key"]: record for record in records}; failures = []
    joinery = by_key["joinery hotel pittsburgh"]
    if "pet_fee" in joinery["facts"] or joinery.get("withheld_fields", {}).get("pet_fee", {}).get("reason_code") != enums.SOURCE_CONTRADICTORY: failures.append("Joinery fee changed")
    north = by_key["hyatt place pittsburgh north shore"]; charges = north["facts"].get("other_charges") or []
    if charges != [{"kind": "cleaning_fee", "amount_cents": 10000, "currency": "USD", "conditional": True, "trigger": "7 - 30 nights"}] or "refundable" in charges[0]: failures.append("Hyatt North Shore cleaning charge changed")
    airport = by_key["hyatt place pittsburgh airport"]
    if "pet_fee" in airport["facts"] or airport.get("withheld_fields", {}).get("pet_fee", {}).get("reason_code") != enums.SOURCE_AMBIGUOUS: failures.append("Hyatt Airport fee changed")
    sonesta = by_key["sonesta simply suites pittsburgh airport"]
    if "species" in sonesta["facts"] or not sonesta["facts"].get("weight_limit_stated_none") or not sonesta["facts"].get("breed_restrictions_stated_none"): failures.append("Sonesta facts changed")
    states = {item["identity_key"]: item["final_state"] for item in partition["items"]}
    for key, state in {"hyatt regency pittsburgh international airport": "AWAITING_POLICY_OBSERVATION", "mansions on fifth": "AWAITING_POLICY_OBSERVATION", "sunnyledge boutique hotel": "AWAITING_POLICY_OBSERVATION"}.items():
        if states.get(key) != state: failures.append(key + " hold changed")
    return {"schema": "ptf-pittsburgh-pass4-semantic-render/1.0", "work_order": WORK_ORDER, "unexpected_semantic_changes": failures, "unexpected_semantic_change_count": len(failures)}


def run(apply: bool) -> dict:
    packet, plan = load(PACKET_PATH), load(PLAN_PATH); entries, partial_resume = verify_preflight(packet, plan)
    census = {row["identity_key"]: row for row in load(CENSUS_PATH)["hotels"]}; facts = load(FACTS_PATH); exclusions = load(EXCLUSIONS_PATH)
    published = [build_positive(did, spec, entries[did], census[entries[did]["identity_key"]]) for did, spec in POSITIVES.items()]
    new_exclusions = [build_exclusion(did, quote, entries[did], census[entries[did]["identity_key"]]) for did, quote in NEGATIVES.items()]
    if partial_resume:
        # The first application attempt reached only the three local shards and
        # stopped before generated authority, partition, packet, governance,
        # or release outputs.  Resume only when those partial writes are
        # byte-for-byte the records this deterministic writer just rebuilt.
        current_by_key = {record["identity_key"]: record for record in facts["hotels"]}
        assert len(facts["hotels"]) == 37
        assert all(current_by_key[record["identity_key"]] == record for record in published)
        current_exclusions = {record["normalized_name"]: record for record in exclusions["exclusions"]}
        assert len(exclusions["exclusions"]) == 11
        assert all(current_exclusions[record["normalized_name"]] == record for record in new_exclusions)
        next_facts = facts
        next_exclusions = OrderedDict(exclusions)
    else:
        assert not ({record["identity_key"] for record in facts["hotels"]} & {record["identity_key"] for record in published})
        assert not ({record["normalized_name"] for record in exclusions["exclusions"]} & {record["normalized_name"] for record in new_exclusions})
        next_facts = OrderedDict(facts); next_facts["hotels"] = facts["hotels"] + published
        next_exclusions = OrderedDict(exclusions); next_exclusions["exclusions"] = exclusions["exclusions"] + new_exclusions
    next_exclusions["count"] = len(next_exclusions["exclusions"])
    EX.validate(next_exclusions)
    if not apply: return {"published_added": len(published), "exclusions_added": len(new_exclusions), "partial_resume_required": partial_resume, "authority_written": False}
    if not partial_resume:
        dump(FACTS_PATH, next_facts); write_seed_rows(published, census)
    dump(EXCLUSIONS_PATH, next_exclusions); MA.write_generated_artifacts()
    from scripts.pettripfinder import build_pittsburgh_market_001 as builder
    builder._AUTHORITY_CACHE = None; builder.build()
    partition = load(PARTITION_PATH); counts = Counter(item["final_state"] for item in partition["items"])
    assert {"published": counts["PUBLISHED_PET_FRIENDLY"], "verified_no_pets": counts["VERIFIED_NO_PETS"], "out_of_category": counts["OUT_OF_CURRENT_CATEGORY"], "unresolved": sum(count for state, count in counts.items() if state.startswith("AWAITING_"))} == {"published": 37, "verified_no_pets": 8, "out_of_category": 3, "unresolved": 48}
    semantic = semantic_check(published, partition); assert semantic["unexpected_semantic_change_count"] == 0, semantic; dump(SEMANTIC_PATH, semantic)
    update_release_contract(next_facts, partition)
    for record in published:
        assert record["approval"]["operator"] == FOUNDER and record["approval"]["decision"] == enums.APPROVED_AFTER_CURRENT_REVIEW and record["approval"]["record_hash"] == record_hash(record) and record["approval"]["evidence_hash"] == evidence_hash(record["evidence"])
    packet["status"] = "FOUNDER_DECISIONS_APPLIED"; packet["decisions_applied"] = 10; packet["applied_at"] = DECISION_DATE; packet["application_work_order"] = WORK_ORDER
    for did, entry in entries.items(): entry["authority_application_status"] = "APPLIED"; entry["outcome"] = "EXCLUDED_VERIFIED_NO_PETS" if did in NEGATIVES else "PUBLISHED"
    dump(PACKET_PATH, packet)
    report = {"schema": "ptf-pittsburgh-pass4-application-001-report/1.0", "work_order": WORK_ORDER, "authority_before": {key: plan["authority_before"][key] for key in ("published", "verified_no_pets", "out_of_category", "unresolved")}, "authority_after": {"published": 37, "verified_no_pets": 8, "out_of_category": 3, "unresolved": 48}, "published_decisions": list(POSITIVES), "exclusion_decisions": list(NEGATIVES), "not_applied_holds": plan["excluded_from_application"], "approval_drift": 0, "unexpected_semantic_change_count": 0}
    dump(REPORT_PATH, report); return report


def main() -> None:
    parser = argparse.ArgumentParser(); parser.add_argument("--apply", action="store_true"); args = parser.parse_args()
    print(json.dumps(run(args.apply), indent=2))
    if not args.apply: print("dry run: nothing written")


if __name__ == "__main__": main()
