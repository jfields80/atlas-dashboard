"""PTF-CINCINNATI-21C-FOUNDER-DECISION-APPLICATION-001 -- apply exactly one ruling.

Applies the founder's single explicit decision for 21c Museum Hotel
Cincinnati (APPROVE_PARTIAL_PUBLICATION, pets_allowed only), recorded
against the durable artifact captured under
PTF-CINCINNATI-21C-RECAPTURE-001 (checkpoint 338816b). This is the sole
row PTF-CINCINNATI-PASS1-AUTHORITY-APPLICATION-001 (45c6e1b) held back as
ARTIFACT_INSUFFICIENT. No other Cincinnati identity is touched. Cincinnati's
Fidelity Hotel (HOLD_PREOPENING) remains untouched.

Run:  python -m scripts.pettripfinder.cincinnati_21c_founder_decision_application \
          [--apply]
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import sys
from collections import OrderedDict
from pathlib import Path
from typing import Dict, Optional

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder import market_authority as MA                     # noqa: E402
from scripts.pettripfinder.contracts import enums                            # noqa: E402
from scripts.pettripfinder.contracts import evidence as evidence_contract    # noqa: E402
from scripts.pettripfinder.contracts import policy_schema                    # noqa: E402
from scripts.pettripfinder.contracts import withholding                      # noqa: E402
from scripts.pettripfinder.contracts.evidence import quote_is_contiguous     # noqa: E402
from scripts.pettripfinder.contracts.fee_computation import classify         # noqa: E402
from scripts.pettripfinder.market_ownership import MARKET_ID_FIELD           # noqa: E402
from scripts.pettripfinder.policy_migration import (                         # noqa: E402
    evidence_hash, evidence_ref_for, record_hash,
)

WORK_ORDER = "PTF-CINCINNATI-21C-FOUNDER-DECISION-APPLICATION-001"
MARKET = "cincinnati-oh"
IDENTITY_KEY = "21c museum hotel cincinnati"
DECISION_DATE = "2026-08-17"
FOUNDER = "jfields80"
CAPTURED_AT = "2026-08-17"
CAPTURE_METHOD = "attended_first_party_fetch"
GRADE = enums.GRADE_PT1_FIRST_PARTY

SOURCE_URL = "https://21cmuseumhotels.com/cincinnati/experience/"
ARTIFACT_SHA256 = (
    "19fc9579bc99b2ae437c9a697c9bfd04b8929ce9436d00d7120d04f7b31af00e")
QUOTE = "Pet-Friendly Rooms"

LP = _REPO_ROOT / "launch_packages" / "pettripfinder"
CENSUS_PATH = LP / "identity_census" / "cincinnati-oh.json"
FACTS_PATH = LP / "hotel_policy_facts_cincinnati-oh.json"
PARTITION_PATH = LP / "cincinnati_final_partition_001.json"

CAVEAT = (
    "Founder decision APPROVE_PARTIAL_PUBLICATION recorded by jfields80 "
    "under PTF-CINCINNATI-21C-FOUNDER-DECISION-APPLICATION-001, against "
    "the artifact captured under PTF-CINCINNATI-21C-RECAPTURE-001 "
    "(commit 338816b). Only pets_allowed is approved; species, pet count, "
    "fee, fee basis/scope, refundability, weight, breed restrictions, "
    "reservation requirement, and service-animal terms are all absent "
    "from the source and are withheld as genuine silence, not inferred. "
    "The recapture artifact was persisted to disk (not just an in-browser "
    "hash) and re-validated byte-for-byte immediately before this "
    "application ran."
)


def _evidence(field: str, quote: str, source_url: str, value_disp: str,
             artifact_sha: Optional[str]) -> Dict:
    entry = OrderedDict([
        ("field", field),
        ("quote", quote),
        ("source_url", source_url),
        ("value", value_disp),
        ("evidence_ref", ""),
        ("artifact_class", enums.PUBLICATION_GRADE_EVIDENCE),
        ("artifact_sha256", ("sha256:%s" % artifact_sha) if artifact_sha else ""),
        ("artifact_kind", enums.ARTIFACT_RENDERED_HTML),
        ("captured_at", CAPTURED_AT),
        ("capture_method", CAPTURE_METHOD),
        ("source_grade", GRADE),
    ])
    entry["evidence_ref"] = evidence_ref_for(entry)
    return entry


def load_json(path: Path) -> Dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_json(path: Path, doc) -> None:
    path.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n",
                    encoding="utf-8")


def build_record(census_row: Dict) -> Dict:
    facts = OrderedDict([("pets_allowed", True)])
    evidence = [_evidence("pets_allowed", QUOTE, SOURCE_URL, "true",
                          ARTIFACT_SHA256)]

    evidence_quote = QUOTE
    for e in evidence:
        if not quote_is_contiguous(e["quote"], evidence_quote):
            raise AssertionError("21c: evidence quote for %s escapes evidence_quote"
                                 % e["field"])

    record = OrderedDict([
        ("key", IDENTITY_KEY),
        ("name", census_row["canonical_name"]),
        ("facts", facts),
        ("evidence", evidence),
        ("evidence_count", len(evidence)),
        ("evidence_quote", evidence_quote),
        ("source_url", SOURCE_URL),
        ("source_type", "EXACT_ENTITY_DOMAIN"),
        ("verification_state", "VERIFIED_PET_FRIENDLY"),
        ("verification_date", DECISION_DATE),
        ("verified_at", DECISION_DATE),
        ("worker_model_id", ""),
        ("worker_prompt_version", ""),
        ("worker_result_hash", ARTIFACT_SHA256),
        ("worker_routing_version", ""),
        ("worker_validator_version", ""),
        ("schema_version", "1.2"),
        ("identity_key", IDENTITY_KEY),
        ("market_id", MARKET),
    ])
    record["computation_class"] = classify(facts).computation_class

    issues = list(policy_schema.validate_record(record)) \
        + list(evidence_contract.validate(record)) \
        + list(withholding.validate(record))
    if issues:
        raise AssertionError("21c: contract issues: %s"
                             % [str(i) for i in issues[:6]])

    record["approval"] = OrderedDict([
        ("decision", enums.APPROVED_AFTER_CURRENT_REVIEW),
        ("operator", FOUNDER),
        ("approval_date", DECISION_DATE),
        ("caveats", [CAVEAT]),
        ("record_hash", record_hash(record)),
        ("evidence_hash", evidence_hash(record["evidence"])),
    ])
    return record


def run(apply: bool) -> Dict:
    census_doc = load_json(CENSUS_PATH)
    census_rows = {h["identity_key"]: h for h in census_doc["hotels"]}
    if IDENTITY_KEY not in census_rows:
        raise SystemExit("STOP: 21c not in the census")

    facts_doc = load_json(FACTS_PATH)
    routing_doc = load_json(MA.routing_shard_path(MARKET))
    partition_doc = load_json(PARTITION_PATH)

    before = OrderedDict([
        ("census", census_doc["count"]),
        ("published", len(facts_doc["hotels"])),
    ])
    if before["published"] != 20:
        raise SystemExit("STOP: expected 20 published before this "
                         "application, found %d" % before["published"])

    have = {h["identity_key"] for h in facts_doc["hotels"]}
    if IDENTITY_KEY in have:
        raise SystemExit("STOP: 21c already published")

    record = build_record(census_rows[IDENTITY_KEY])

    routes = routing_doc["routes"]
    route_idx = None
    for i, r in enumerate(routes):
        if r["hotel_ref"]["identity_key"] == IDENTITY_KEY:
            route_idx = i
            break
    if route_idx is None:
        raise SystemExit("STOP: no routing record found for 21c")
    if routes[route_idx]["status"] == "ROUTING_RETIRED":
        raise SystemExit("STOP: 21c route already retired")

    partition_items = partition_doc["items"]
    part_idx = None
    for i, r in enumerate(partition_items):
        if r["identity_key"] == IDENTITY_KEY:
            part_idx = i
            break
    if part_idx is None:
        raise SystemExit("STOP: 21c not found in partition")
    if partition_items[part_idx]["final_state"] != "AWAITING_POLICY_OBSERVATION":
        raise SystemExit("STOP: 21c partition final_state is not "
                         "AWAITING_POLICY_OBSERVATION (found %r)"
                         % partition_items[part_idx]["final_state"])

    seed_row = census_rows[IDENTITY_KEY]
    seed_new = OrderedDict([
        ("name", record["name"]), ("category", "pet-friendly-hotels"),
        ("address", seed_row["address"]), ("city", seed_row["city"]),
        ("state", seed_row["state"]), ("postal_code", seed_row["postal_code"]),
        ("phone", seed_row.get("phone", "")), ("website_url", record["source_url"]),
        ("source_url", record["source_url"]),
        ("source_type", "OFFICIAL_PROPERTY"), ("observed_at", DECISION_DATE),
        ("rating", ""), ("amenities", ""),
        ("pet_policy", record["evidence_quote"]), ("canonical", ""),
        (MARKET_ID_FIELD, MARKET),
    ])

    facts_doc["hotels"] = facts_doc["hotels"] + [record]

    routes[route_idx]["status"] = "ROUTING_RETIRED"
    routes[route_idx]["retired_at"] = DECISION_DATE
    routes[route_idx]["retired_reason"] = (
        "Identity resolved by PTF-CINCINNATI-21C-FOUNDER-DECISION-"
        "APPLICATION-001 -- published to hotel_policy_facts_cincinnati-oh.json. "
        "Routing is for a CONFIRMED hotel that is NOT yet inventory; this "
        "identity is now seed inventory (published), so its route is "
        "retired rather than left coexisting with it.")
    routes[route_idx]["retired_by"] = WORK_ORDER

    partition_items[part_idx]["final_state"] = "PUBLISHED_PET_FRIENDLY"
    partition_items[part_idx]["resolved"] = True
    partition_items[part_idx]["next_action"] = ""
    partition_items[part_idx]["next_action_source"] = WORK_ORDER
    partition_items[part_idx]["determined_by"] = WORK_ORDER
    partition_items[part_idx]["updated_at"] = DECISION_DATE

    counts = partition_doc["final_state_counts"]
    counts["AWAITING_POLICY_OBSERVATION"] -= 1
    counts["PUBLISHED_PET_FRIENDLY"] += 1

    after = OrderedDict([
        ("census", census_doc["count"]),
        ("published", len(facts_doc["hotels"])),
    ])

    result = OrderedDict([
        ("before", before), ("after", after),
        ("published_added", 1),
        ("final_state_counts_after", dict(counts)),
    ])

    if apply:
        write_json(FACTS_PATH, facts_doc)
        write_json(MA.routing_shard_path(MARKET), routing_doc)
        write_json(PARTITION_PATH, partition_doc)
        header = ["name", "category", "address", "city", "state", "postal_code",
                  "phone", "website_url", "source_url", "source_type",
                  "observed_at", "rating", "amenities", "pet_policy", "canonical",
                  MARKET_ID_FIELD]
        buf = io.StringIO()
        w = csv.DictWriter(buf, fieldnames=header)
        w.writeheader()
        w.writerow(seed_new)
        seed_shard_path = MA.seed_shard_path(MARKET)
        with open(seed_shard_path, "a", encoding="utf-8", newline="") as f:
            f.write(buf.getvalue()[buf.getvalue().index("\n") + 1:])
        result["applied"] = True
    else:
        result["applied"] = False
    return result


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    result = run(apply=args.apply)
    print(json.dumps(result, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
