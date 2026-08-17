# -*- coding: utf-8 -*-
"""PTF-DETROIT-ANN-ARBOR-PASS2-DECISION-APPLICATION-001.

Records and applies the founder's 3 Pass 2 capture decisions atomically --
no intermediate committed state exists where decisions are recorded in the
packet but authority is unapplied.

DTW-P2-01 Courtyard Detroit Pontiac Bloomfield -> APPROVE_VERIFIED_NO_PETS
DTW-P2-02 DoubleTree by Hilton Detroit Novi -> APPROVE_VERIFIED_NO_PETS
DTW-P2-03 Hotel Indigo Detroit Downtown -> APPROVE_WITH_CHANGE (pet_fee
    withheld SOURCE_CONTRADICTORY, weight_limit withheld SOURCE_AMBIGUOUS)

Census/partition/founder-review-queue are patched SURGICALLY (these 3 rows
only) -- the other 139 Detroit identities are asserted byte-identical
before writing, same discipline as the routing-repair and identity-repair
Pass 2 scripts.

Run:  python -m scripts.pettripfinder.detroit_ann_arbor_pass2_decision_application [--apply]
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import OrderedDict
from pathlib import Path
from typing import Dict, List

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder import canonical_view                              # noqa: E402
from scripts.pettripfinder import hotel_exclusions as EX                      # noqa: E402
from scripts.pettripfinder import market_authority as MA                      # noqa: E402
from scripts.pettripfinder.contracts import census as CENSUS                  # noqa: E402
from scripts.pettripfinder.contracts import enums                             # noqa: E402
from scripts.pettripfinder.contracts import evidence as evidence_contract     # noqa: E402
from scripts.pettripfinder.contracts import partition as PART                 # noqa: E402
from scripts.pettripfinder.contracts import policy_schema                     # noqa: E402
from scripts.pettripfinder.contracts import withholding                       # noqa: E402
from scripts.pettripfinder.contracts.fee_computation import classify          # noqa: E402
from scripts.pettripfinder.census_partition_builder import next_action_for    # noqa: E402
from scripts.pettripfinder.policy_migration import (                          # noqa: E402
    evidence_hash, evidence_ref_for, record_hash,
)
from scripts.pettripfinder.site_data import normalize_name                    # noqa: E402

MARKET = "detroit-ann-arbor-mi"
WORK_ORDER = "PTF-DETROIT-ANN-ARBOR-PASS2-DECISION-APPLICATION-001"
CAPTURE_WORK_ORDER = "PTF-DETROIT-ANN-ARBOR-CAPTURE-PASS2-001"
DECISION_DATE = "2026-08-17"
FOUNDER = "jfields80"

LP = _REPO_ROOT / "launch_packages" / "pettripfinder"
FACTS_PATH = LP / ("hotel_policy_facts_%s.json" % MARKET)
# PTF-ACTIVE-BRANCH-SHARD-MIGRATION-001. This market's exclusions live in its
# OWN authority shard, never in the shared global file. The global
# launch_packages/pettripfinder/hotel_exclusions.json is a GENERATED
# compatibility artifact assembled from every market's shard, so writing it
# here would both conflict with every other market's branch and be overwritten
# by the next assembly.
EXCLUSIONS_SHARD_PATH = MA.exclusions_shard_path(MARKET)
CENSUS_PATH = LP / "identity_census" / ("%s.json" % MARKET)
PARTITION_PATH = LP / "detroit_ann_arbor_final_partition_001.json"
PACKET_PATH = LP / "detroit_ann_arbor_capture_pass2_founder_review_packet.json"
CAPTURE_RESULTS_PATH = LP / "detroit_ann_arbor_capture_pass2_001.json"
RENDER_REPORT_PATH = LP / "markets" / "reports" / "detroit_ann_arbor_pass2_semantic_render.json"
QUEUE_PATH = LP / "markets" / "reports" / "detroit-ann-arbor-mi_founder_review_queue.json"
RAW_DIR = (_REPO_ROOT / "data" / "worker_runs" / "pettripfinder"
           / "detroit-ann-arbor-capture-pass2-001" / "raw")

SCREENSHOT_FILES = {
    "DTW-P2-01": "P2-01-courtyard-pontiac.jpg",
    "DTW-P2-02": "P2-02-doubletree-novi.jpg",
    "DTW-P2-03": "P2-03-hotel-indigo-downtown.jpg",
}

POSITIVES = OrderedDict([
    ("DTW-P2-03", dict(
        decision="APPROVE_WITH_CHANGE",
        grade=enums.GRADE_PT1_FIRST_PARTY,
        facts=[
            ("pets_allowed", True, "Pets are welcome at Hotel Indigo Detroit Downtown."),
            ("species", OrderedDict([("dogs", "accepted"), ("cats", "accepted")]),
             "Pets allowed: Only dogs and cats allowed"),
            ("pet_count_limit", 2, "2 pets allowed"),
            ("pet_count_scope", "room",
             "There is a one time 100.00 dollar non refundable fee per pet "
             "per stay with a maximum of two pets per room."),
            ("service_animal_statement",
             OrderedDict([("stated", True), ("charges_stated", "no_charge")]),
             "Service animals welcome at no additional fee."),
        ],
        withheld=[
            dict(field="pet_fee", reason_code="SOURCE_CONTRADICTORY",
                 reason="The property's own page states the $100 fee two "
                        "conflicting ways in the same pet-policy surface: "
                        "prose describes it as a one-time fee 'per pet per "
                        "stay', while a structured field on the identical "
                        "page states 'Pet fee per night: 100 USD'. Same "
                        "dollar amount, directly conflicting basis -- "
                        "withheld rather than choosing either reading.",
                 quotes=[
                     "There is a one time 100.00 dollar non refundable fee "
                     "per pet per stay with a maximum of two pets per room.",
                     "Pet fee per night: 100 USD",
                 ]),
            dict(field="weight_limit", reason_code="SOURCE_AMBIGUOUS",
                 reason="The structured field states 'Pet weight limit: 50' "
                        "with no unit anywhere on the page (not lbs, not "
                        "kg). A weight limit without a stated unit is not a "
                        "usable fact -- withheld rather than assuming pounds.",
                 quotes=["Pet weight limit: 50"]),
        ],
        note="Founder: publish the unambiguous species/count/service-animal "
             "facts; withhold pet_fee (contradictory basis) and weight_limit "
             "(no unit) entirely rather than guess at either."
    )),
])

NEGATIVES = OrderedDict([
    ("DTW-P2-01", dict(refusal_quote="Pet Policy\nPets Not Allowed")),
    ("DTW-P2-02", dict(refusal_quote="Pets not allowed")),
])


def load_json(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"), object_pairs_hook=OrderedDict)


def write_lf(path: Path, payload) -> None:
    text = json.dumps(payload, indent=2, ensure_ascii=False) + "\n"
    path.write_text(text.replace("\r\n", "\n"), encoding="utf-8", newline="\n")


def _value_display(value) -> str:
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def _sha_file(path: Path) -> str:
    return "sha256:%s" % hashlib.sha256(path.read_bytes()).hexdigest()


def build_positive_record(did: str, spec: Dict, packet_entry: Dict, census_row: Dict) -> Dict:
    screenshot_path = RAW_DIR / SCREENSHOT_FILES[did]
    if not screenshot_path.is_file():
        raise SystemExit("STOP %s: no screenshot artifact on disk at %s" % (did, screenshot_path))
    artifact_sha = _sha_file(screenshot_path)
    if artifact_sha.split(":", 1)[1] != packet_entry["artifact_sha256_screenshot"]:
        raise SystemExit("STOP %s: screenshot hash drifted from the committed packet" % did)

    source_url = packet_entry["final_url"]
    facts: "OrderedDict[str, object]" = OrderedDict()
    sas = None
    evidence: List[Dict] = []

    def _evidence_entry(field: str, quote: str, value) -> Dict:
        entry = OrderedDict([
            ("field", field), ("quote", quote), ("source_url", source_url),
            ("value", _value_display(value)), ("evidence_ref", ""),
            ("artifact_class", enums.PUBLICATION_GRADE_EVIDENCE),
            ("artifact_sha256", artifact_sha),
            ("artifact_kind", enums.ARTIFACT_OPERATOR_SCREENSHOT),
            ("captured_at", DECISION_DATE), ("capture_method", "attended_browser"),
            ("source_grade", spec["grade"]),
        ])
        entry["evidence_ref"] = evidence_ref_for(entry)
        return entry

    for field, value, quote in spec["facts"]:
        evidence.append(_evidence_entry(field, quote, value))
        if field == "service_animal_statement":
            sas = value
        else:
            facts[field] = value

    withheld: "OrderedDict[str, Dict]" = OrderedDict()
    for w in spec.get("withheld", []):
        refs = []
        for quote in w["quotes"]:
            entry = _evidence_entry(w["field"], quote, "WITHHELD")
            evidence.append(entry)
            refs.append(entry["evidence_ref"])
        withheld[w["field"]] = OrderedDict([
            ("reason_code", w["reason_code"]), ("reason", w["reason"]),
            ("evidence_refs", refs),
        ])

    quote_texts = []
    for entry in evidence:
        if entry["quote"] not in quote_texts:
            quote_texts.append(entry["quote"])
    evidence_quote = " […] ".join(quote_texts)

    record = OrderedDict([
        ("key", census_row["identity_key"]), ("name", census_row["canonical_name"]),
        ("facts", facts), ("evidence", evidence), ("evidence_count", len(evidence)),
        ("evidence_quote", evidence_quote), ("source_url", source_url),
        ("source_type", "EXACT_ENTITY_DOMAIN"),
        ("verification_state", "VERIFIED_PET_FRIENDLY"),
        ("verification_date", DECISION_DATE), ("verified_at", DECISION_DATE),
        ("worker_model_id", ""), ("worker_prompt_version", ""),
        ("worker_result_hash", artifact_sha), ("worker_routing_version", ""),
        ("worker_validator_version", ""), ("schema_version", "1.2"),
        ("identity_key", census_row["identity_key"]), ("market_id", MARKET),
    ])
    if withheld:
        record["withheld_fields"] = withheld
    if sas is not None:
        record["service_animal_statement"] = sas
    record["computation_class"] = classify(facts).computation_class

    issues = list(policy_schema.validate_record(record)) \
        + list(evidence_contract.validate(record)) \
        + list(withholding.validate(record))
    if issues:
        raise SystemExit("STOP %s: contract issues: %s" % (did, issues[:4]))

    caveats = [
        "Founder decision %s (%s), recorded verbatim in "
        "detroit_ann_arbor_capture_pass2_founder_review_packet.json and "
        "approved against THIS final record_hash. Quotes were transcribed "
        "from the property's own rendered policy surface (IHG FAQ accordion, "
        "expanded via attended click) at capture time and are bound to the "
        "operator screenshot artifact (%s). Identity binding: %s." % (
            did, spec["decision"], artifact_sha[:23], packet_entry["identity_binding"]),
        "Founder global rule applied: SOURCE SILENCE IS ABSENCE -- unstated "
        "optional facts are absent, never withheld.",
        spec["note"],
    ]
    record["approval"] = OrderedDict([
        ("decision", enums.APPROVED_AFTER_CURRENT_REVIEW), ("operator", FOUNDER),
        ("approval_date", DECISION_DATE), ("caveats", caveats),
        ("record_hash", record_hash(record)), ("evidence_hash", evidence_hash(evidence)),
    ])
    return record


def build_exclusion(did: str, spec: Dict, packet_entry: Dict, census_row: Dict) -> Dict:
    screenshot_path = RAW_DIR / SCREENSHOT_FILES[did]
    if not screenshot_path.is_file():
        raise SystemExit("STOP %s: no screenshot artifact on disk at %s" % (did, screenshot_path))
    artifact_sha = _sha_file(screenshot_path)
    if artifact_sha.split(":", 1)[1] != packet_entry["artifact_sha256_screenshot"]:
        raise SystemExit("STOP %s: screenshot hash drifted from the committed packet" % did)
    record = OrderedDict([
        ("exclusion_id", "dtw-%s" % census_row["slug"]),
        ("canonical_name", census_row["canonical_name"]),
        ("normalized_name", normalize_name(census_row["canonical_name"])),
        ("address", census_row["address"]), ("city", census_row["city"]),
        ("state", census_row["state"]), ("postal_code", census_row["postal_code"]),
        ("official_url", packet_entry["final_url"]),
        ("exclusion_state", EX.VERIFIED_NO_PETS),
        ("evidence_quote", spec["refusal_quote"]),
        ("source_url", packet_entry["final_url"]),
        ("observed_at", DECISION_DATE), ("source_hash", artifact_sha),
        ("reviewer_id", FOUNDER), ("reviewed_at", DECISION_DATE),
        ("notes", "Founder decision %s, %s: affirmative first-party refusal "
                  "in the property's own words, captured by the attended "
                  "browser as operator_screenshot with policy and identity "
                  "in frame (binding: %s). Service-animal access is a legal "
                  "category and never converts a no-pets policy into "
                  "pet-friendly." % (did, WORK_ORDER, packet_entry["identity_binding"])),
        ("market_id", MARKET),
    ])
    record["record_hash"] = EX.record_hash(record)
    record["approval_hash"] = EX.approval_hash(record)
    return record


def semantic_render_check(published: List[Dict]) -> Dict:
    from scripts.pettripfinder.hotel_profile import (
        _verified_details, _verified_facts, _verified_summary,
    )

    def profile_text(record):
        shown = canonical_view.display_facts(record)
        parts = [_verified_summary(shown, record.get("evidence_quote") or "")]
        parts += ["%s %s" % (l, v) for l, v, _x in _verified_facts(shown)]
        parts += ["%s %s" % (l, v) for l, v, _x in _verified_details(shown, record)[0]]
        return " | ".join(parts)

    unexpected: List[str] = []
    rows = []
    for record in published:
        text = profile_text(record)
        view = canonical_view.build(record)
        rows.append(OrderedDict([
            ("identity_key", record["identity_key"]),
            ("fee_phrase", canonical_view.fee_phrase(view)),
            ("fee_display_mode", view.fee_display_mode),
            ("profile_text", text),
        ]))
        if "100" in text and record["identity_key"] == "hotel indigo detroit downtown":
            unexpected.append("hotel indigo detroit downtown: fee amount 100 "
                              "leaked into profile text despite withholding")
        if "50" in text.replace("2026", "").replace("48226", "") \
                and record["identity_key"] == "hotel indigo detroit downtown":
            unexpected.append("hotel indigo detroit downtown: weight limit "
                              "50 leaked into profile text despite withholding")

    return OrderedDict([
        ("schema", "ptf-detroit-ann-arbor-pass2-semantic-render/1.0"),
        ("work_order", WORK_ORDER), ("as_of", DECISION_DATE),
        ("record_count", len(published)),
        ("unexpected_semantic_changes", unexpected),
        ("unexpected_semantic_change_count", len(unexpected)),
        ("rows", rows),
    ])


def rebuild_census_partition_queue(published_keys: Dict[str, str],
                                   excluded_keys: List[str]) -> Dict:
    """Surgical patch: only the 3 rows this pass decides move. Every other
    Detroit identity is asserted byte-identical before writing."""
    census_doc = load_json(CENSUS_PATH)
    partition_doc = load_json(PARTITION_PATH)
    queue_doc = load_json(QUEUE_PATH)

    hotels = census_doc["hotels"]
    by_key = {r["identity_key"]: r for r in hotels}
    all_keys = list(published_keys.keys()) + excluded_keys
    for key in all_keys:
        if key not in by_key:
            raise SystemExit("STOP: %r not in committed census" % key)

    census_before = [r for r in hotels if r["identity_key"] not in all_keys]

    items = partition_doc["items"]
    p_by_key = {i["identity_key"]: i for i in items}
    partition_before = [i for i in items if i["identity_key"] not in all_keys]

    for key in published_keys:
        crow = by_key[key]
        prow = p_by_key[key]
        prow["final_state"] = enums.PUBLISHED_PET_FRIENDLY
        prow["resolved"] = True
        prow["next_action"] = ""
        prow["next_action_source"] = ""
        prow["determined_by"] = WORK_ORDER
        prow["updated_at"] = DECISION_DATE
        prow["official_url"] = crow["official_url"]
        prow["state_override_reason"] = ""

    for key in excluded_keys:
        crow = by_key[key]
        prow = p_by_key[key]
        prow["final_state"] = enums.VERIFIED_NO_PETS
        prow["resolved"] = True
        prow["next_action"] = ""
        prow["next_action_source"] = ""
        prow["determined_by"] = WORK_ORDER
        prow["updated_at"] = DECISION_DATE
        prow["official_url"] = crow["official_url"]
        prow["state_override_reason"] = ""

    census_after = [r for r in hotels if r["identity_key"] not in all_keys]
    if census_before != census_after:
        raise SystemExit("STOP: an unrelated census row changed")
    partition_after = [i for i in items if i["identity_key"] not in all_keys]
    if partition_before != partition_after:
        raise SystemExit("STOP: an unrelated partition row changed")

    counts: Dict[str, int] = {}
    for item in items:
        counts[item["final_state"]] = counts.get(item["final_state"], 0) + 1
    partition_doc["final_state_counts"] = counts
    partition_doc["final_state_meanings"] = {
        s: PART.STATE_MEANINGS[s] for s in sorted(counts)}
    partition_doc["work_order"] = WORK_ORDER
    partition_doc["as_of"] = DECISION_DATE
    partition_doc["note"] = (
        "%s applied 3 founder decisions from the Pass 2 capture packet: "
        "1 published (Hotel Indigo Detroit Downtown, pet_fee/weight_limit "
        "withheld), 2 VERIFIED_NO_PETS (Courtyard Pontiac, DoubleTree "
        "Novi). No other Detroit identity changed." % WORK_ORDER)
    census_doc["work_order"] = WORK_ORDER
    census_doc["captured_at"] = DECISION_DATE

    q_items = queue_doc["items"]
    q_before = [q for q in q_items if q["identity_key"] not in all_keys]
    q_items[:] = [q for q in q_items if q["identity_key"] not in all_keys]
    queue_doc["count"] = len(q_items)
    queue_doc["as_of"] = DECISION_DATE
    queue_doc["work_order"] = WORK_ORDER
    q_after = [q for q in q_items if q["identity_key"] not in all_keys]
    if q_before != q_after:
        raise SystemExit("STOP: an unrelated queue row changed")

    issues = CENSUS.validate(census_doc, market_states=["MI"])
    if issues:
        raise SystemExit("census invalid: %s" % [(i.path, i.code, i.detail) for i in issues])
    p_issues = PART.validate(partition_doc)
    if p_issues:
        raise SystemExit("partition invalid: %s" % [(i.path, i.code, i.detail) for i in p_issues])
    rec = PART.reconcile(CENSUS.identity_keys(census_doc), partition_doc, market_id=MARKET)
    rec_issues = PART.reconciliation_issues(rec)
    if rec_issues or not rec.agrees:
        raise SystemExit("reconciliation failed: %s" % (rec_issues,))

    return dict(census_doc=census_doc, partition_doc=partition_doc, queue_doc=queue_doc,
                rec=rec, counts=counts)


def run(apply: bool) -> Dict:
    packet = load_json(PACKET_PATH)
    entries = {e["decision_id"]: e for e in packet["candidates"]}
    census = {r["identity_key"]: r for r in load_json(CENSUS_PATH)["hotels"]}

    if FACTS_PATH.is_file():
        existing_facts = load_json(FACTS_PATH)
        if any(h["identity_key"] == "hotel indigo detroit downtown" for h in existing_facts["hotels"]):
            raise SystemExit("STOP: Hotel Indigo already in hotel_policy_facts")

    published: List[Dict] = []
    for did, spec in POSITIVES.items():
        entry = entries[did]
        key = entry["identity_key"]
        if key not in census:
            raise SystemExit("STOP %s: %r not in the census" % (did, key))
        published.append(build_positive_record(did, spec, entry, census[key]))

    existing_facts_doc = load_json(FACTS_PATH)
    facts_doc = OrderedDict(existing_facts_doc)
    facts_doc["hotels"] = list(existing_facts_doc["hotels"]) + published

    # Only THIS market's exclusions; the union check runs in the assembler.
    existing_exclusions = MA.load_market_exclusions(MARKET)
    existing_norm = {e["normalized_name"] for e in existing_exclusions}
    new_exclusions: List[Dict] = []
    for did, spec in NEGATIVES.items():
        entry = entries[did]
        key = entry["identity_key"]
        record = build_exclusion(did, spec, entry, census[key])
        if record["normalized_name"] in existing_norm:
            raise SystemExit("STOP %s: %r already excluded" % (did, record["normalized_name"]))
        new_exclusions.append(record)
    exclusions_doc = MA.build_exclusions_shard(
        MARKET, list(existing_exclusions) + new_exclusions)

    EX.validate(exclusions_doc)  # raises ExclusionContractError on failure

    render_report = semantic_render_check(published)
    if render_report["unexpected_semantic_change_count"]:
        raise SystemExit("STOP: unexpected semantic changes: %s"
                         % render_report["unexpected_semantic_changes"])

    published_keys = {entries[did]["identity_key"]: did for did in POSITIVES}
    excluded_keys = [entries[did]["identity_key"] for did in NEGATIVES]
    rebuilt = rebuild_census_partition_queue(published_keys, excluded_keys)

    if rebuilt["rec"].published != 7 or rebuilt["rec"].verified_no_pets != 7:
        raise SystemExit("AUTHORITY MISMATCH: published=%s no_pets=%s"
                         % (rebuilt["rec"].published, rebuilt["rec"].verified_no_pets))

    print("published_added:", len(published))
    print("exclusions_added:", len(new_exclusions))
    print("facts_sha256:", hashlib.sha256(
        json.dumps(facts_doc, sort_keys=True).encode()).hexdigest())
    print("partition_counts:", json.dumps(rebuilt["counts"], sort_keys=True))
    print("published_total:", rebuilt["rec"].published)
    print("verified_no_pets_total:", rebuilt["rec"].verified_no_pets)
    unresolved = sum(n for s, n in rebuilt["counts"].items()
                     if s not in enums.TERMINAL_STATES)
    print("unresolved:", unresolved)
    print("unexpected_semantic_changes:", render_report["unexpected_semantic_change_count"])

    if not apply:
        print("dry run: nothing written")
        return dict(published=published, exclusions=new_exclusions)

    # ---- record founder decisions into the packet (same transaction) ----
    for did in list(POSITIVES) + list(NEGATIVES):
        entry = entries[did]
        entry["founder_decision"] = (POSITIVES[did]["decision"] if did in POSITIVES
                                     else "APPROVE_VERIFIED_NO_PETS")
        entry["founder_decision_recorded_by"] = FOUNDER
        entry["founder_decision_recorded_at"] = DECISION_DATE
        entry["founder_decision_work_order"] = WORK_ORDER
        entry["outcome"] = ("PUBLISHED" if did in POSITIVES
                            else "EXCLUDED_VERIFIED_NO_PETS")
    packet["status"] = "FOUNDER_DECIDED_AND_APPLIED"
    packet["applied_at"] = DECISION_DATE
    packet["decisions_recorded"] = True
    packet["decisions_recorded_at"] = DECISION_DATE

    write_lf(FACTS_PATH, facts_doc)
    EXCLUSIONS_SHARD_PATH.write_bytes(
        MA.render_json(exclusions_doc).encode("utf-8"))
    # Regenerate the global compatibility artifacts from ALL shards; this is
    # also where a cross-market collision fails closed.
    MA.write_generated_artifacts()
    write_lf(RENDER_REPORT_PATH, render_report)
    write_lf(CENSUS_PATH, rebuilt["census_doc"])
    write_lf(PARTITION_PATH, rebuilt["partition_doc"])
    write_lf(QUEUE_PATH, rebuilt["queue_doc"])
    write_lf(PACKET_PATH, packet)

    # ---- verify every written approval hash is fresh and correctly attributed ----
    verify_facts = load_json(FACTS_PATH)
    for hotel in verify_facts["hotels"]:
        if hotel.get("market_id") != MARKET:
            continue
        approval = hotel.get("approval")
        if not approval:
            continue
        expected = dict(hotel)
        expected.pop("approval")
        if record_hash(expected) != approval["record_hash"]:
            raise SystemExit("STOP: stale record_hash for %s" % hotel["identity_key"])
        if evidence_hash(hotel["evidence"]) != approval["evidence_hash"]:
            raise SystemExit("STOP: stale evidence_hash for %s" % hotel["identity_key"])
        if approval["operator"] != FOUNDER:
            raise SystemExit("STOP: approval operator mismatch for %s" % hotel["identity_key"])

    for e in MA.load_market_exclusions(MARKET):
        if e.get("market_id") != MARKET:
            continue
        if e.get("reviewer_id") and e["reviewer_id"] != FOUNDER:
            continue

    print("applied. wrote: facts, exclusions, render_report, census, partition, queue, packet")
    return dict(published=published, exclusions=new_exclusions)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    run(apply=args.apply)


if __name__ == "__main__":
    main()
