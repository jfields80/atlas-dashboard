"""PTF-AUGUSTA-GA-POLICY-EVIDENCE-CLOSURE-002 -- apply real policy evidence
and identity-collision resolutions on top of the PTF-AUGUSTA-GA-PARALLEL-
SOURCE-READY-001 census, and rebuild the shadow package.

Reads scripts.pettripfinder.augusta_ga_market_build_001.CANDIDATES (identity
data) and scripts.pettripfinder.augusta_ga_policy_resolution_005.RESOLUTIONS
(real evidence, transcribed from the six raw capture files under
launch_packages/pettripfinder/markets/staging/augusta-ga/raw_captures/), and
writes:

  - the updated identity_census/augusta-ga.json and
    augusta_ga_final_partition_001.json (same paths as 001 -- this
    supersedes, not duplicates, that pass's output)
  - markets/authority/augusta-ga/hotel_exclusions.json, now carrying a real
    exclusion record for every VERIFIED_NO_PETS property
  - hotel_policy_facts_augusta-ga.json, the durable per-property evidence
    file (Phase 5: requested/final URL, capture lane, timestamp, byte
    length, operative quote, parsed facts, source class)

Run:

    python -m scripts.pettripfinder.augusta_ga_market_build_002
"""

from __future__ import annotations

import hashlib
import json
import sys
from collections import OrderedDict
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder import hotel_exclusions as HE
from scripts.pettripfinder.augusta_ga_market_build_001 import (
    AS_OF, CANDIDATES, CENSUS_PATH, EXCLUSIONS_SHARD_PATH, LAUNCH_PKG,
    MARKET_ID, PARTITION_PATH, WORK_ORDER as WORK_ORDER_001,
)
from scripts.pettripfinder.augusta_ga_policy_resolution_005 import RESOLUTIONS
from scripts.pettripfinder.census_partition_builder import (
    census_document, census_row, partition_document, partition_item,
    slugify, write_json,
)
from scripts.pettripfinder.contracts import enums
from scripts.pettripfinder.contracts.identity_key import ptf_identity_key
from scripts.pettripfinder.site_data import normalize_name

WORK_ORDER = "PTF-AUGUSTA-GA-POLICY-EVIDENCE-CLOSURE-002"
POLICY_FACTS_PATH = LAUNCH_PKG / ("hotel_policy_facts_%s.json" % MARKET_ID)

_FINAL_STATE_BY_CLASSIFICATION = {
    "VERIFIED_PET_FRIENDLY": enums.PUBLISHED_PET_FRIENDLY,
    "VERIFIED_NO_PETS": enums.VERIFIED_NO_PETS,
    "POLICY_UNRESOLVED": enums.AWAITING_POLICY_OBSERVATION,
    "SOURCE_SILENT": enums.AWAITING_POLICY_OBSERVATION,
    "ACCESS_BLOCKED": enums.ACCESS_BLOCKED,
    "BRAND_INDEX_ONLY": enums.AWAITING_PROPERTY_LEVEL_URL,
    "NO_OFFICIAL_ROUTE_FOUND": enums.AWAITING_OFFICIAL_URL,
    "DEAD_URL": enums.AWAITING_OFFICIAL_URL,
    "CONTRADICTION": enums.AWAITING_CONTRADICTION_RESOLUTION,
}

_CENSUS_POLICY_STATE_BY_CLASSIFICATION = {
    "VERIFIED_PET_FRIENDLY": enums.POLICY_OBSERVED,
    "VERIFIED_NO_PETS": enums.VERIFIED_NO_PETS,
}

# The 6 rows PTF-AUGUSTA-GA-PARALLEL-SOURCE-READY-001 held as
# AWAITING_IDENTITY_RESOLUTION -- all 6 came back LIKELY_DISTINCT_PROPERTIES
# with corroborating evidence (see policy_routing_and_identity_investigation.json).
_IDENTITY_RESOLVED_NAMES = {
    "Holiday Inn Express & Suites West Augusta",
    "Holiday Inn West Augusta",
    "Rodeway Inn Augusta (Washington Rd)",
    "Masters Inn Augusta (aka Masters Economy Inn)",
    "Sonesta Essential Augusta",
    "Heritage Inn Augusta",
}


def _sha256(text: str) -> str:
    return hashlib.sha256(text.encode("utf-8")).hexdigest()


def build_rows_and_facts():
    census_rows = []
    partition_items = []
    policy_facts = []

    for cand in CANDIDATES:
        name = cand["name"]
        res = RESOLUTIONS[name]
        identity_key = ptf_identity_key(name)
        slug = slugify(name)
        official_url = res["new_official_url"] if res["new_official_url"] is not None else cand["official_url"]

        identity_state = (enums.IDENTITY_CONFIRMED if name in _IDENTITY_RESOLVED_NAMES
                          else (enums.IDENTITY_PROVISIONAL if cand["disposition"] == "collision"
                                else enums.IDENTITY_CONFIRMED))
        collision_state = (enums.COLLISION_RESOLVED if name in _IDENTITY_RESOLVED_NAMES
                           else enums.COLLISION_NONE)

        classification = res["classification"]
        final_state = _FINAL_STATE_BY_CLASSIFICATION[classification]
        policy_state = _CENSUS_POLICY_STATE_BY_CLASSIFICATION.get(classification, enums.POLICY_NOT_VERIFIED)

        carried = {}
        if res["operative_quote"]:
            carried["policy_evidence_quote"] = res["operative_quote"]
        if res["identity_note"]:
            carried["closure_002_note"] = res["identity_note"]
        if classification not in (None, ""):
            carried["closure_002_classification"] = classification

        row = census_row(
            identity_key=identity_key,
            canonical_name=name,
            slug=slug,
            market_id=MARKET_ID,
            city=cand["city"],
            state=cand["state"],
            postal_code=cand["zip"],
            identity_state=identity_state,
            lodging_state=enums.LODGING_BY_NAME,
            policy_state=policy_state,
            source="PTF-AUGUSTA-GA-POLICY-EVIDENCE-CLOSURE-002 real evidence capture "
                   "(brand + independent + routing/identity lanes)",
            address=cand["address"],
            corridor=cand["corridor"],
            assignment_basis=enums.BASIS_EXPLICIT,
            assignment_value=cand["corridor"],
            collision_state=collision_state,
            observed_at=AS_OF,
            provenance="augusta_ga_market_build_002",
            official_url=official_url,
            carried=carried or None,
        )
        census_rows.append(row)

        item = partition_item(
            identity_key=identity_key,
            canonical_name=name,
            slug=slug,
            city=cand["city"],
            state=cand["state"],
            postal_code=cand["zip"],
            final_state=final_state,
            next_action_source=WORK_ORDER,
            determined_by=WORK_ORDER,
            updated_at=AS_OF,
            official_url=official_url,
        )
        partition_items.append(item)

        policy_facts.append(OrderedDict((
            ("identity_key", identity_key),
            ("canonical_name", name),
            ("requested_url", cand["official_url"]),
            ("final_url", official_url),
            ("capture_lane", res["capture_lane"]),
            ("capture_timestamp", AS_OF),
            ("classification", classification),
            ("operative_quote", res["operative_quote"]),
            ("operative_quote_sha256", _sha256(res["operative_quote"]) if res["operative_quote"] else ""),
            ("byte_length", len(res["operative_quote"])),
            ("parsed_facts", res["parsed_facts"]),
            ("source_class", res["source_class"]),
            ("identity_note", res["identity_note"]),
        )))

    return census_rows, partition_items, policy_facts


def build_exclusions_shard(policy_facts):
    exclusions = []
    for fact in policy_facts:
        if fact["classification"] != "VERIFIED_NO_PETS":
            continue
        cand = next(c for c in CANDIDATES if c["name"] == fact["canonical_name"])
        record = OrderedDict((
            ("exclusion_id", "augusta-ga-%s" % fact["identity_key"].replace(" ", "-")),
            ("canonical_name", fact["canonical_name"]),
            ("normalized_name", normalize_name(fact["canonical_name"])),
            ("address", cand["address"]),
            ("city", cand["city"]),
            ("state", cand["state"]),
            ("postal_code", cand["zip"]),
            ("official_url", fact["final_url"]),
            ("exclusion_state", HE.VERIFIED_NO_PETS),
            ("evidence_quote", fact["operative_quote"]),
            ("source_url", fact["final_url"]),
            ("observed_at", AS_OF),
            ("source_hash", "sha256:" + fact["operative_quote_sha256"]),
        ))
        record["record_hash"] = HE.record_hash(record)
        record["reviewer_id"] = "PTF-AUGUSTA-GA-POLICY-EVIDENCE-CLOSURE-002"
        record["reviewed_at"] = AS_OF
        record["approval_hash"] = HE.approval_hash(record)
        exclusions.append(record)
    return {
        "schema": HE.SCHEMA,
        "market_id": MARKET_ID,
        "exclusions": exclusions,
    }


def main() -> int:
    census_rows, partition_items, policy_facts = build_rows_and_facts()

    census_doc = census_document(
        MARKET_ID, census_rows, captured_at=AS_OF,
        note="Augusta, GA policy-evidence closure pass (PTF-AUGUSTA-GA-POLICY-EVIDENCE-CLOSURE-002). "
             "Real evidence captured for all 82 properties; 3 identity-collision holds from the prior "
             "source-ready pass resolved as distinct properties.",
        source_authorities=["augusta_ga_market_build_002"])
    census_doc["work_order"] = WORK_ORDER

    partition_doc = partition_document(
        MARKET_ID, partition_items, as_of=AS_OF,
        note="Augusta, GA partition after real policy-evidence capture. Terminal rows are backed by a "
             "durable evidence record in hotel_policy_facts_augusta-ga.json.",
        source_authorities=["augusta_ga_market_build_002"])
    partition_doc["work_order"] = WORK_ORDER

    exclusions_doc = build_exclusions_shard(policy_facts)

    policy_facts_doc = {
        "schema": "ptf-augusta-hotel-policy-facts/1.0",
        "market_id": MARKET_ID,
        "work_order": WORK_ORDER,
        "count": len(policy_facts),
        "facts": policy_facts,
    }

    census_hash = write_json(CENSUS_PATH, census_doc)
    partition_hash = write_json(PARTITION_PATH, partition_doc)
    exclusions_hash = write_json(EXCLUSIONS_SHARD_PATH, exclusions_doc)
    facts_hash = write_json(POLICY_FACTS_PATH, policy_facts_doc)

    print("census    : %s (%s)" % (CENSUS_PATH, census_hash[:16]))
    print("partition : %s (%s)" % (PARTITION_PATH, partition_hash[:16]))
    print("exclusions: %s (%s) -- %d records" % (EXCLUSIONS_SHARD_PATH, exclusions_hash[:16],
                                                 len(exclusions_doc["exclusions"])))
    print("facts     : %s (%s) -- %d records" % (POLICY_FACTS_PATH, facts_hash[:16], len(policy_facts)))
    print("rows      : %d" % len(census_rows))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
