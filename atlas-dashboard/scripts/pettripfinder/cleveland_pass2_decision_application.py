"""PTF-CLEVELAND-PASS2-FOUNDER-DECISIONS-001 -- apply the founder's 45 rulings.

Deterministic application of the founder decisions given against the Pass-2
review packet (bb9e6fa):

* 20 positive candidates become published Schema 1.2 records. Facts are taken
  from the same adjudication table the packet was built from
  (``cleveland_pass2_capture_integration.ROWS``) with the founder's
  APPROVE_WITH_CHANGE rulings applied on top (P04 boundary, P16 ceiling
  handling, P17 property-level-only). Every fact quote and every
  evidence_quote region is asserted contiguous in the hash-bound capture
  artifact before anything is written; a failed assertion aborts the run.
* 23 refusal candidates become VERIFIED_NO_PETS exclusions, validated by the
  exclusion contract, each bound to its captured page by source_hash.
* The two Drury records receive the founder's re-attestation -- written ONLY
  after the record's full current hash is re-verified against the committed
  packet delta. Any drift stops that record instead of re-signing.
* Downstream authority follows the integrate-capture-003 blueprint: seed
  inventory rows for the published twenty, routing records retired for all
  43 decided identities (the existing invariant: neither published nor
  excluded identities hold routes), the final partition and unresolved
  manifest moved to the new disposition, and the release contract re-derived.

P16's nights-7+ ruling, applied exactly: Schema 1.2 tiers carry exact prices
and no ceiling qualifier, so the "not to exceed $15" rung is NOT published as
a price. It is withheld as SCHEMA_CANNOT_REPRESENT ("The hotel states terms we
cannot summarise accurately.") with the exact source sentence retained in the
evidence array -- the same treatment the founder's Dayton ESA decision
established for ceiling wording.

Run:  python -m scripts.pettripfinder.cleveland_pass2_decision_application \
          [--data-root PATH] [--apply]
"""

from __future__ import annotations

import argparse
import copy
import csv
import hashlib
import io
import json
import sys
from collections import Counter, OrderedDict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder import hotel_exclusions as EX                     # noqa: E402
from scripts.pettripfinder.contracts import enums                            # noqa: E402
from scripts.pettripfinder.contracts import evidence as evidence_contract    # noqa: E402
from scripts.pettripfinder.contracts import policy_schema                    # noqa: E402
from scripts.pettripfinder.contracts import withholding                      # noqa: E402
from scripts.pettripfinder.contracts.fee_computation import classify         # noqa: E402
from scripts.pettripfinder.cleveland_pass2_capture_integration import (      # noqa: E402
    DRURY, ROWS, load_json, quote_backed, verify_capture, write_lf,
)
from scripts.pettripfinder.market_ownership import MARKET_ID_FIELD           # noqa: E402
from scripts.pettripfinder.policy_migration import (                         # noqa: E402
    evidence_hash, evidence_ref_for, record_hash,
)
from scripts.pettripfinder.site_data import PRODUCTION_CSV, normalize_name   # noqa: E402

MARKET = "cleveland-akron-canton-oh"
WORK_ORDER = "PTF-CLEVELAND-PASS2-FOUNDER-DECISIONS-001"
DECISION_DATE = "2026-08-15"
FOUNDER = "jfields80"

LP = _REPO_ROOT / "launch_packages" / "pettripfinder"
FACTS_PATH = LP / ("hotel_policy_facts_%s.json" % MARKET)
EXCLUSIONS_PATH = LP / "hotel_exclusions.json"
ROUTING_PATH = LP / "identity_routing.json"
CENSUS_PATH = LP / "identity_census" / ("%s.json" % MARKET)
PARTITION_PATH = LP / "cleveland_final_partition_002.json"
MANIFEST_PATH = LP / "cleveland_unresolved_manifest.json"
PACKET_PATH = LP / "cleveland_pass2_founder_review_packet.json"
CONTRACT_PATH = (_REPO_ROOT / "deploy" / "netlify" / "release_contracts"
                 / ("%s.json" % MARKET))
RAW_REL = Path("worker_runs/pettripfinder/cleveland-attended-capture-002/raw")

#: Founder decisions, verbatim scope. Positives keyed by queue_id.
POSITIVE_DECISIONS: Dict[str, str] = {
    "CLE-AAQ-001-A01": "APPROVE", "CLE-AAQ-001-A02": "APPROVE",
    "CLE-AAQ-001-A03": "APPROVE", "CLE-AAQ-001-A06": "APPROVE_WITH_CHANGE",
    "CLE-AAQ-001-A07": "APPROVE", "CLE-AAQ-001-A08": "APPROVE",
    "CLE-AAQ-001-A09": "APPROVE", "CLE-AAQ-001-A10": "APPROVE",
    "CLE-AAQ-001-A11": "APPROVE", "CLE-AAQ-001-A12": "APPROVE",
    "CLE-AAQ-001-A13": "APPROVE", "CLE-AAQ-001-A14": "APPROVE",
    "CLE-AAQ-001-A15": "APPROVE", "CLE-AAQ-001-A16": "APPROVE",
    "CLE-AAQ-001-A17": "APPROVE", "CLE-AAQ-001-C02": "APPROVE_WITH_CHANGE",
    "CLE-AAQ-001-C09": "APPROVE_PROPERTY_LEVEL_ONLY",
    "CLE-AAQ-001-C10": "APPROVE", "CLE-AAQ-001-C11": "APPROVE",
    "CLE-AAQ-001-C12": "APPROVE",
}

#: Ruling text preserved into each record's approval caveats where the founder
#: said more than APPROVE.
RULING_NOTES: Dict[str, str] = {
    "CLE-AAQ-001-A03": "Founder: keep the 50 lb limit per-pet ('pets must be "
                       "50 lbs or less' accepted as applying to each pet); do "
                       "not invent a fee scope.",
    "CLE-AAQ-001-A06": "Founder: weight 40 lb lte per_pet -- the property's "
                       "structured FAQ ('Each pet may weigh up to 40.0 lbs.') "
                       "resolves the prose boundary as inclusive. Fee stays "
                       "absent: 'Pet Fee applies' states no amount.",
    "CLE-AAQ-001-A05-NOTE": "",
    "CLE-AAQ-001-A07": "Founder: the $100/stay non-refundable fee stands; no "
                       "separate refundable deposit is created.",
    "CLE-AAQ-001-A09": "Founder: publish the $75 amount only; fee basis and "
                       "scope are not invented.",
    "CLE-AAQ-001-A11": "Founder: partial record approved; the explicit "
                       "no-deposit statement remains a note because Schema "
                       "1.2 has no stated-none deposit representation.",
    "CLE-AAQ-001-A12": "Founder: FAQ-supported 40 lb lte per-pet "
                       "interpretation.",
    "CLE-AAQ-001-A14": "Founder: keep the $100/stay fee and the cleaning_fee "
                       "withholding; no relationship is inferred between the "
                       "per-stay fee and the unexplained $5/night amount.",
    "CLE-AAQ-001-A16": "Founder: the already-approved Red Roof structure -- "
                       "first pet $0, second pet $15/night capped $105 per "
                       "pet per stay with trigger_max_nights 7; the cap "
                       "belongs to the second pet, never the property.",
    "CLE-AAQ-001-C02": "Founder: pet_count_scope is 'suite'; dimensions are "
                       "structured 36in length / 36in height; nights 1-6 are "
                       "$25 + tax per day per pet; the nights-7+ 'not to "
                       "exceed $15' rung is a ceiling Schema 1.2 tiers cannot "
                       "carry, so it is WITHHELD as SCHEMA_CANNOT_REPRESENT "
                       "with the exact source sentence retained.",
    "CLE-AAQ-001-C09": "Founder: APPROVE_PROPERTY_LEVEL_ONLY -- only "
                       "pets_allowed=true from the property page's own "
                       "wording; the brand policy page's fee-free statement "
                       "and 2-pet limit stay brand-level supplementary "
                       "evidence and are not promoted.",
    "CLE-AAQ-001-C12": "Founder: the pit-bull restriction is kept exactly as "
                       "sourced and not broadened.",
}

#: evidence_quote regions per record: (start_marker, end_marker) pairs sliced
#: from the capture's own whitespace-collapsed text (or HTML where the page
#: carries its policy in a data payload). Slicing from the artifact is what
#: guarantees each region is verbatim and contiguous. Multiple regions are
#: joined with a bracketed ellipsis so nobody can read the join as contiguity.
REGIONS: Dict[str, List[Tuple[str, str]]] = {
    "CLE-AAQ-001-A01": [("Pets Allowed: Yes",
                         "Service animals are permitted, without charge.")],
    "CLE-AAQ-001-A02": [("Pets Allowed: Yes",
                         "Service animals are permitted, without charge."),
                        ("A 200.00 USD penalty",
                         "upon arrival at check in.")],
    "CLE-AAQ-001-A03": [("Pets Allowed: Yes",
                         "Service animals are permitted, without charge.")],
    "CLE-AAQ-001-A06": [("Pet Policy Pets Welcome",
                         "Maximum Number of Pets in Room: 2"),
                        ("Yes, pets are welcome at Courtyard by Marriott "
                         "Akron Downtown", "up to 40.0 lbs.")],
    "CLE-AAQ-001-A07": [("Pet Policy Pets Welcome",
                         "Maximum Number of Pets in Room: 2"),
                        ("Up to 2 pets are allowed per room. Each pet may "
                         "weigh up to 25.0 lbs.", "$100.00 per stay applies.")],
    "CLE-AAQ-001-A08": [("Pet Policy Pets Welcome",
                         "Maximum Number of Pets in Room: 2"),
                        ("Each pet may weigh up to 60.0 lbs.",
                         "up to 60.0 lbs.")],
    "CLE-AAQ-001-A09": [("Pet Policy Pets Welcome",
                         "Maximum Number of Pets in Room: 2")],
    "CLE-AAQ-001-A10": [("Pet Policy Pets Welcome",
                         "Maximum Number of Pets in Room: 2"),
                        ("Each pet may weigh up to 50.0 lbs.",
                         "up to 50.0 lbs.")],
    "CLE-AAQ-001-A11": [("Pet Policy Pets Welcome",
                         "Maximum Number of Pets in Room: 2")],
    "CLE-AAQ-001-A12": [("Pet Policy Pets Welcome",
                         "Maximum Number of Pets in Room: 2"),
                        ("Each pet may weigh up to 40.0 lbs.",
                         "up to 40.0 lbs.")],
    "CLE-AAQ-001-A13": [("Pet Policy Pets Welcome",
                         "Maximum Number of Pets in Room: 2")],
    "CLE-AAQ-001-A14": [("Pet Policy Pets Welcome",
                         "Pet Fee Per Night: $5.00")],
    "CLE-AAQ-001-A15": [("Pet Policy Pets Welcome",
                         "Maximum Number of Pets in Room: 2"),
                        ("Each pet may weigh up to 40.0 lbs.",
                         "up to 40.0 lbs.")],
    "CLE-AAQ-001-A16": [("Pet Policy: One, well-behaved domestic pet",
                         "Service and emotional support animals are always "
                         "welcome.")],
    "CLE-AAQ-001-A17": [("Policies: Pets are welcome",
                         "$10 per pet per night")],
    "CLE-AAQ-001-C02": [("A maximum of two pets are allowed in each suite.",
                         "per day, per pet.")],
    "CLE-AAQ-001-C09": [("Amenities Pets Allowed", "Pets Allowed"),
                        ("Pets Stay Free", "Pets Stay Free")],
    "CLE-AAQ-001-C10": [("PET & SERVICE ANIMAL POLICY",
                         "additional details and availability.")],
    "CLE-AAQ-001-C11": [("PET & SERVICE ANIMAL POLICY",
                         "additional details and availability.")],
    "CLE-AAQ-001-C12": [("PET & SERVICE ANIMAL POLICY",
                         "welcome at this hotel.")],
}

#: P16 founder override: the exact canonical shape ruled on 2026-08-15.
P16_FACTS: List[Dict] = [
    {"field": "pets_allowed", "value": True,
     "quote": "A maximum of two pets are allowed in each suite."},
    {"field": "pet_count_limit", "value": 2,
     "quote": "A maximum of two pets are allowed in each suite."},
    {"field": "pet_count_scope", "value": "suite",
     "quote": "A maximum of two pets are allowed in each suite."},
    {"field": "general_restrictions",
     "value": "Height and length restrictions apply-- pets can be no longer "
              "than 36 inches and no taller than 36 inches.",
     "quote": "Height and length restrictions apply-- pets can be no longer "
              "than 36 inches and no taller than 36 inches."},
    {"field": "dimension_constraints",
     "value": [{"axis": "length", "value": 36, "unit": "in",
                "operator": "lte"},
               {"axis": "height", "value": 36, "unit": "in",
                "operator": "lte"}],
     "quote": "pets can be no longer than 36 inches and no taller than 36 "
              "inches"},
    {"field": "fee_tiers",
     "value": [{"amount_cents": 2500, "currency": "USD",
                "tax_relationship": "plus_tax", "basis": "per_night",
                "scope": "per_pet", "basis_stated": True,
                "role": "REPLACEMENT_PRICE",
                "condition_type": "stay_length_range", "condition_min": 1,
                "condition_max": 6, "boundary_unit": "nights"}],
     "quote": "up to a $25 (+ tax) per day non-refundable cleaning fee for "
              "the first six (6) nights, per pet"},
]
P16_WITHHELD = [{
    "field": "cleaning_fee",
    "reason_code": enums.SCHEMA_CANNOT_REPRESENT,
    "reason": "After the sixth night the property states its per-day, "
              "per-pet charge only as a ceiling ('not to exceed $15'). "
              "Schema 1.2 fee tiers carry exact prices and no ceiling "
              "qualifier, so publishing a $15 rung would assert a charge "
              "the page does not state. The exact sentence is retained in "
              "the evidence array.",
    "quote": "Each day thereafter there is a pet cleaning fee not to exceed "
             "$15 non-refundable fee (+tax) per day, per pet",
}]

#: A16 founder override: the canonical fee_pet_schedule shape already attested
#: on the Columbus Red Roofs (ordinal rungs; the cap on the rung it bounds).
A16_SCHEDULE = {
    "field": "fee_pet_schedule",
    "value": {"entries": [
        {"pet_ordinal": 1, "amount_cents": 0, "currency": "USD",
         "additive": False, "basis": "per_stay"},
        {"pet_ordinal": 2, "amount_cents": 1500, "currency": "USD",
         "basis": "per_night", "scope": "per_pet", "additive": True,
         "cap": {"amount_cents": 10500, "currency": "USD",
                 "basis": "per_stay", "scope": "per_pet",
                 "applies_to_pet_ordinal": 2, "trigger_max_nights": 7,
                 "qualifier_stated": True}},
    ]},
    "quote": "Second pet $15/ night, not to exceed 7 nights or $105 per pet "
             "per stay.",
}


def _c(value: str) -> str:
    return " ".join((value or "").split())


def _clean_url(url: str) -> str:
    return (url or "").split("?", 1)[0]


def _slice_region(hay: str, start: str, end: str, who: str) -> str:
    hay_c, start_c, end_c = _c(hay), _c(start), _c(end)
    i = hay_c.find(start_c)
    if i < 0:
        raise AssertionError("%s: region start %r not in artifact" % (who, start[:50]))
    j = hay_c.find(end_c, i)
    if j < 0:
        raise AssertionError("%s: region end %r not in artifact" % (who, end[:50]))
    return hay_c[i:j + len(end_c)]


def build_evidence_quote(qid: str, doc: Dict) -> str:
    hay = doc.get("text", "")
    if quote_backed(REGIONS[qid][0][0], doc) == "html":
        hay = doc.get("html", "")
    parts = [_slice_region(hay, s, e, qid) for s, e in REGIONS[qid]]
    return " […] ".join(parts)


def _value_display(value) -> str:
    if isinstance(value, bool):
        return str(value).lower()
    if isinstance(value, str):
        return value
    return json.dumps(value, ensure_ascii=False, sort_keys=True)


def build_positive_record(qid: str, spec: Dict, queue_row: Dict,
                          census_row: Dict, doc: Dict) -> Dict:
    """One published Schema 1.2 record from a founder-approved candidate."""
    integrity = verify_capture(doc)
    if not (integrity["html_agrees"] and integrity["text_agrees"]):
        raise AssertionError("%s: capture integrity failure" % qid)
    artifact_sha = "sha256:%s" % integrity["html_sha256"]
    source_url = _clean_url(doc["final_url"])
    verification_date = DECISION_DATE

    facts_list = list(spec["facts"])
    withheld_list = list(spec.get("withheld", []))
    if qid == "CLE-AAQ-001-C02":
        facts_list = copy.deepcopy(P16_FACTS)
        withheld_list = copy.deepcopy(P16_WITHHELD)
    if qid == "CLE-AAQ-001-A16":
        facts_list = [copy.deepcopy(A16_SCHEDULE) if f["field"] ==
                      "fee_pet_schedule" else f for f in facts_list]
    if qid == "CLE-AAQ-001-A02":
        # The packet proposed the deposit under its own name; the canonical
        # home for a deposit is other_charges (kind: pet_deposit), the same
        # family the Courtyard cleaning fee lives in (kind: refundable_deposit).
        facts_list = [
            {"field": "other_charges",
             "value": [{"amount_cents": 10000, "currency": "USD",
                        "kind": "refundable_deposit", "refundable": True}],
             "quote": f["quote"], "note": f.get("note", "")}
            if f["field"] == "pet_deposit" else f for f in facts_list]

    facts: "OrderedDict[str, object]" = OrderedDict()
    sas = None
    evidence: List[Dict] = []
    for fact in facts_list:
        where = quote_backed(fact["quote"], doc)
        if where == "MISSING":
            raise AssertionError("%s: quote %r not in artifact"
                                 % (qid, fact["quote"][:60]))
        entry = OrderedDict([
            ("field", fact["field"]),
            ("quote", fact["quote"]),
            ("source_url", source_url),
            ("value", _value_display(fact["value"])),
            ("evidence_ref", ""),
            ("artifact_class", enums.PUBLICATION_GRADE_EVIDENCE),
            ("artifact_sha256", artifact_sha),
            ("artifact_kind", enums.ARTIFACT_RENDERED_HTML),
            ("captured_at", doc["captured_at"]),
            ("capture_method", "attended_browser"),
            ("source_grade", enums.GRADE_PT1_FIRST_PARTY),
        ])
        entry["evidence_ref"] = evidence_ref_for(entry)
        evidence.append(entry)
        if fact["field"] == "service_animal_statement":
            sas = fact["value"]
        else:
            facts[fact["field"]] = fact["value"]

    withheld: "OrderedDict[str, Dict]" = OrderedDict()
    for w in withheld_list:
        where = quote_backed(w["quote"], doc)
        if where == "MISSING":
            raise AssertionError("%s: withheld quote %r not in artifact"
                                 % (qid, w["quote"][:60]))
        entry = OrderedDict([
            ("field", w["field"]),
            ("quote", w["quote"]),
            ("source_url", source_url),
            ("value", "WITHHELD"),
            ("evidence_ref", ""),
            ("artifact_class", enums.PUBLICATION_GRADE_EVIDENCE),
            ("artifact_sha256", artifact_sha),
            ("artifact_kind", enums.ARTIFACT_RENDERED_HTML),
            ("captured_at", doc["captured_at"]),
            ("capture_method", "attended_browser"),
            ("source_grade", enums.GRADE_PT1_FIRST_PARTY),
        ])
        entry["evidence_ref"] = evidence_ref_for(entry)
        evidence.append(entry)
        withheld[w["field"]] = OrderedDict([
            ("reason_code", w["reason_code"]),
            ("reason", w["reason"]),
            ("evidence_refs", [entry["evidence_ref"]]),
        ])

    evidence_quote = build_evidence_quote(qid, doc)
    for entry in evidence:
        if _c(entry["quote"]) not in _c(evidence_quote):
            raise AssertionError("%s: quote %r escapes evidence_quote"
                                 % (qid, entry["quote"][:60]))

    record = OrderedDict([
        ("key", census_row["identity_key"]),
        ("name", census_row["canonical_name"]),
        ("facts", facts),
        ("evidence", evidence),
        ("evidence_count", len(evidence)),
        ("evidence_quote", evidence_quote),
        ("source_url", source_url),
        ("source_type", "EXACT_ENTITY_DOMAIN"),
        ("verification_state", "VERIFIED_PET_FRIENDLY"),
        ("verification_date", verification_date),
        ("verified_at", verification_date),
        ("worker_model_id", ""),
        ("worker_prompt_version", ""),
        ("worker_result_hash", artifact_sha),
        ("worker_routing_version", ""),
        ("worker_validator_version", ""),
        ("schema_version", "1.2"),
        ("identity_key", census_row["identity_key"]),
        ("market_id", MARKET),
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
        raise AssertionError("%s: contract issues: %s" % (qid, issues[:4]))

    caveats = [
        "Founder decision %s, %s, approved against THIS record_hash. Facts "
        "were constructed only from quotes verified contiguous in the "
        "hash-bound attended capture (%s); identity was bound on the page's "
        "own address/ZIP/phone signals recorded in "
        "cleveland_pass2_capture_results.json." % (
            qid.replace("CLE-AAQ-001-", "P-"), WORK_ORDER, artifact_sha[:23]),
    ]
    note = RULING_NOTES.get(qid)
    if note:
        caveats.append(note)
    record["approval"] = OrderedDict([
        ("decision", enums.APPROVED_AFTER_CURRENT_REVIEW),
        ("operator", FOUNDER),
        ("approval_date", DECISION_DATE),
        ("caveats", caveats),
        ("record_hash", record_hash(record)),
        ("evidence_hash", evidence_hash(evidence)),
    ])
    return record


def build_exclusion(neg: Dict, census_row: Dict, doc: Dict) -> Dict:
    integrity = verify_capture(doc)
    if not (integrity["html_agrees"] and integrity["text_agrees"]):
        raise AssertionError("%s: capture integrity failure" % neg["queue_id"])
    if quote_backed(neg["refusal_quote"], doc) == "MISSING":
        raise AssertionError("%s: refusal quote not in artifact"
                             % neg["queue_id"])
    source_url = _clean_url(doc["final_url"])
    record = OrderedDict([
        ("exclusion_id", "cle-%s" % census_row["slug"]),
        ("canonical_name", census_row["canonical_name"]),
        ("normalized_name", normalize_name(census_row["canonical_name"])),
        ("address", census_row["address"]),
        ("city", census_row["city"]),
        ("state", census_row["state"]),
        ("postal_code", census_row["postal_code"]),
        ("official_url", source_url),
        ("exclusion_state", EX.VERIFIED_NO_PETS),
        ("evidence_quote", neg["refusal_quote"]),
        ("source_url", source_url),
        ("observed_at", DECISION_DATE),
        ("source_hash", "sha256:%s" % integrity["html_sha256"]),
        ("reviewer_id", FOUNDER),
        ("reviewed_at", DECISION_DATE),
        ("notes", "Founder decision %s, %s: affirmative refusal in the "
                  "property's own words, captured with retained bytes by the "
                  "attended browser (%s). Service-animal access is a legal "
                  "category and is never read as a pet permission or as a "
                  "refusal on its own." % (
                      neg["queue_id"].replace("CLE-AAQ-001-", "N-"),
                      WORK_ORDER, neg["queue_id"])),
        ("market_id", MARKET),
    ])
    record["record_hash"] = EX.record_hash(record)
    record["approval_hash"] = EX.approval_hash(record)
    return record


def reattest_drury(facts_doc: Dict, packet: Dict) -> List[str]:
    """Founder re-attestation, only against the verified full current hash."""
    deltas = {d["identity_key"]: d
              for d in packet["drury_reattestation_deltas"]}
    done = []
    for hotel in facts_doc["hotels"]:
        key = hotel["identity_key"]
        if key not in deltas:
            continue
        delta = deltas[key]
        current = record_hash(hotel)
        if current != delta["record_hash_after"]:
            raise SystemExit(
                "STOP %s: current record_hash %s does not equal the packet "
                "delta %s; NOT re-signing." % (key, current[:23],
                                               delta["record_hash_after"][:23]))
        pending = hotel["approval"]
        if pending.get("decision") != enums.MACHINE_REVIEWED_PENDING_OPERATOR:
            raise SystemExit("STOP %s: not in the pending state the founder "
                             "was shown" % key)
        prior = copy.deepcopy(pending["supersedes"])
        hotel["approval"] = OrderedDict([
            ("decision", enums.APPROVED_AFTER_CURRENT_REVIEW),
            ("operator", FOUNDER),
            ("approval_date", DECISION_DATE),
            ("supersedes", prior),
            ("caveats", [
                "Founder decision %s (%s), %s. Re-attested against THIS "
                "record_hash after the full current hash was verified equal "
                "to the committed packet delta. Basis accepted: facts, "
                "quotes and evidence_hash unchanged; the byte-retained "
                "publication-grade artifact (%s) verified; the prior "
                "2026-08-11 approval is preserved verbatim under "
                "'supersedes'. The transient pending-operator state lives in "
                "git history (bb9e6fa), not in this chain." % (
                    "D-%02d" % (delta["row"] - 47), WORK_ORDER,
                    DECISION_DATE, delta["artifact_sha256"][:23]),
            ]),
            ("record_hash", current),
            ("evidence_hash", evidence_hash(hotel["evidence"])),
        ])
        if hotel["approval"]["evidence_hash"] != pending["evidence_hash"]:
            raise SystemExit("STOP %s: evidence_hash moved" % key)
        done.append(key)
    if len(done) != 2:
        raise SystemExit("STOP: expected 2 Drury re-attestations, got %d"
                         % len(done))
    return done


def run(data_root: Path, apply: bool) -> Dict:
    raw_dir = data_root / RAW_REL
    packet = load_json(PACKET_PATH)
    census = {r["identity_key"]: r for r in load_json(CENSUS_PATH)["hotels"]}
    queue_rows = {r["queue_id"]: r for r in csv.DictReader(
        (data_root / Path("operator_evidence/cleveland-attended-artifact-002"
                          "/cleveland-attended-artifact-queue.csv")
         ).open(encoding="utf-8-sig"))}

    facts_doc = load_json(FACTS_PATH)
    have = {h["identity_key"] for h in facts_doc["hotels"]}

    # ---- 20 positives ----------------------------------------------------- #
    published: List[Dict] = []
    for qid, decision in POSITIVE_DECISIONS.items():
        spec = ROWS[qid]
        queue_row = queue_rows[qid]
        key = queue_row["hotel_id"]
        if key not in census:
            raise SystemExit("STOP %s: %r not in the census" % (qid, key))
        if key in have:
            raise SystemExit("STOP %s: %r already published" % (qid, key))
        doc = load_json(raw_dir / spec["artifact"])
        record = build_positive_record(qid, spec, queue_row, census[key], doc)
        published.append(record)
    facts_doc["hotels"] = facts_doc["hotels"] + published

    # ---- Drury re-attestations -------------------------------------------- #
    drury_done = reattest_drury(facts_doc, packet)

    # ---- 23 exclusions ----------------------------------------------------- #
    exclusions_doc = load_json(EXCLUSIONS_PATH)
    existing_norm = {e["normalized_name"] for e in exclusions_doc["exclusions"]}
    new_exclusions: List[Dict] = []
    for neg in packet["negative_candidates"]:
        key = neg["hotel_id"]
        if key not in census:
            raise SystemExit("STOP %s: %r not in the census"
                             % (neg["queue_id"], key))
        doc = load_json(raw_dir / neg["artifact_file"])
        record = build_exclusion(neg, census[key], doc)
        if record["normalized_name"] in existing_norm:
            raise SystemExit("STOP %s: already excluded" % neg["queue_id"])
        new_exclusions.append(record)
    exclusions_doc["exclusions"] = exclusions_doc["exclusions"] + new_exclusions
    EX.validate(exclusions_doc)

    # ---- seed inventory ---------------------------------------------------- #
    seed_new = []
    for record in published:
        row = census[record["identity_key"]]
        seed_new.append({
            "name": record["name"], "category": "pet-friendly-hotels",
            "address": row["address"], "city": row["city"],
            "state": row["state"], "postal_code": row["postal_code"],
            "phone": row["phone"], "website_url": record["source_url"],
            "source_url": record["source_url"],
            "source_type": "OFFICIAL_PROPERTY", "observed_at": DECISION_DATE,
            "rating": "", "amenities": "",
            "pet_policy": record["evidence_quote"], "canonical": "",
            MARKET_ID_FIELD: MARKET,
        })

    # ---- routing retirement (published + excluded hold no routes) ---------- #
    routing = load_json(ROUTING_PATH)
    decided_norm = {normalize_name(r["name"]) for r in published} | \
                   {e["normalized_name"] for e in new_exclusions}
    before_routes = len(routing["routes"])
    routing["routes"] = [r for r in routing["routes"]
                         if not (r.get("market_id") == MARKET
                                 and r["hotel_ref"]["normalized_name"]
                                 in decided_norm)]
    routing["count"] = len(routing["routes"])
    routes_retired = before_routes - len(routing["routes"])

    # ---- partition + manifest ---------------------------------------------- #
    partition = load_json(PARTITION_PATH)
    new_state = {record["identity_key"]: "PUBLISHED_PET_FRIENDLY"
                 for record in published}
    new_state.update({e["normalized_name"]: "VERIFIED_NO_PETS"
                      for e in new_exclusions})
    moved = 0
    for item in partition["items"]:
        target = new_state.get(item["identity_key"])
        if target:
            item["final_state"] = target
            item["updated_at"] = DECISION_DATE
            item["state_override_reason"] = (
                "%s: founder decision applied from the Pass-2 packet; "
                "evidence is the hash-bound attended capture." % WORK_ORDER)
            moved += 1
    if moved != len(new_state):
        raise SystemExit("STOP: %d of %d decided identities found in the "
                         "partition" % (moved, len(new_state)))
    counts = Counter(i["final_state"] for i in partition["items"])
    partition["final_state_counts"] = OrderedDict(
        (k, counts[k]) for k in partition["final_state_counts"] if counts[k])
    for k in sorted(counts):
        partition["final_state_counts"].setdefault(k, counts[k])
    terminal = ("PUBLISHED_PET_FRIENDLY", "VERIFIED_NO_PETS",
                "OUT_OF_CURRENT_CATEGORY")
    resolved = sum(counts[s] for s in terminal)
    partition["reconciliation"] = OrderedDict([
        ("confirmed_identities", 188),
        ("published_pet_friendly", counts["PUBLISHED_PET_FRIENDLY"]),
        ("verified_no_pets", counts["VERIFIED_NO_PETS"]),
        ("resolved", resolved),
        ("unresolved", 188 - resolved),
        ("reviewed_in_work_browser_pass_001",
         partition["reconciliation"]["reviewed_in_work_browser_pass_001"]),
        ("never_reviewed_by_any_browser_pass",
         partition["reconciliation"]["never_reviewed_by_any_browser_pass"]),
    ])
    partition["pass2_update"] = OrderedDict([
        ("work_order", WORK_ORDER),
        ("as_of", DECISION_DATE),
        ("moved", moved),
        ("note", "43 identities moved by founder decision after the 49-row "
                 "attended capture pass: 20 published, 23 verified no-pets. "
                 "The 2026-08-12 crosswalk and evidence determination remain "
                 "the historical record of how the queue was derived."),
    ])

    manifest = load_json(MANIFEST_PATH)
    manifest_items = [i for i in manifest["items"]
                      if i["normalized_name"] not in new_state
                      and i.get("identity_key") not in new_state]
    removed = len(manifest["items"]) - len(manifest_items)
    if removed != 43:
        # Items may be keyed by normalized_name only.
        raise SystemExit("STOP: expected 43 manifest removals, got %d"
                         % removed)
    manifest["items"] = manifest_items
    manifest["published_pet_friendly"] = counts["PUBLISHED_PET_FRIENDLY"]
    manifest["verified_no_pets"] = counts["VERIFIED_NO_PETS"]
    manifest["resolved"] = resolved
    manifest["unresolved"] = 188 - resolved
    manifest["classification_counts"] = OrderedDict(
        sorted(Counter(i["classification"] for i in manifest_items).items()))
    manifest["as_of"] = DECISION_DATE
    manifest["pass2_update"] = (
        "%s removed 43 rows (20 published, 23 verified no-pets) after the "
        "attended capture pass; every removal is traceable in "
        "cleveland_pass2_capture_results.json." % WORK_ORDER)

    summary = OrderedDict([
        ("published_added", len(published)),
        ("exclusions_added", len(new_exclusions)),
        ("drury_reattested", drury_done),
        ("seed_rows_added", len(seed_new)),
        ("routes_retired", routes_retired),
        ("partition_moved", moved),
        ("reconciliation", dict(partition["reconciliation"])),
    ])

    if apply:
        payload = write_lf(FACTS_PATH, facts_doc)
        new_sha = hashlib.sha256(payload).hexdigest()
        write_lf(EXCLUSIONS_PATH, exclusions_doc)
        write_lf(ROUTING_PATH, routing)
        write_lf(MANIFEST_PATH, manifest)
        # The partition is DERIVED, never hand-edited: with the authorities
        # written, the committed partition builder recomputes every final
        # state, count and audit section from them, so the rebuild test's
        # "the committed ledger is what the code produces" stays true.
        from scripts.pettripfinder.cleveland_final_partition_002 import             build_partition
        write_lf(PARTITION_PATH, build_partition())

        with PRODUCTION_CSV.open(encoding="utf-8", newline="") as fh:
            reader = csv.DictReader(fh)
            existing_rows = list(reader)
            fields = list(reader.fieldnames)
        existing_names = {normalize_name(r["name"]) for r in existing_rows
                          if r.get(MARKET_ID_FIELD) == MARKET}
        clash = existing_names & {normalize_name(r["name"]) for r in seed_new}
        if clash:
            raise SystemExit("STOP: seed rows already present: %s" % clash)
        buf = io.StringIO(newline="")
        writer = csv.DictWriter(buf, fieldnames=fields, lineterminator="\n")
        writer.writeheader()
        for row in existing_rows + seed_new:
            writer.writerow({k: row.get(k, "") for k in fields})
        PRODUCTION_CSV.write_text(buf.getvalue(), encoding="utf-8",
                                  newline="")

        contract = load_json(CONTRACT_PATH)
        contract["policy_package"]["expected_sha256"] = new_sha
        contract["policy_package"]["expected_record_count"] = \
            counts["PUBLISHED_PET_FRIENDLY"]
        contract["reconciliation"].update(
            {k: v for k, v in partition["reconciliation"].items()
             if k in contract["reconciliation"]})
        contract["public_surface"]["seed_hotel_rows"] = \
            counts["PUBLISHED_PET_FRIENDLY"]
        contract["public_surface"]["public_hotel_profile_count"] = \
            counts["PUBLISHED_PET_FRIENDLY"]
        contract["routes"]["hotel_route_count"] = \
            counts["PUBLISHED_PET_FRIENDLY"]
        contract["deployment_authorization"]["means"] = (
            contract["deployment_authorization"]["means"].replace(
                "159 of this market's 188", "%d of this market's 188"
                % (188 - resolved)))
        write_lf(CONTRACT_PATH, contract)

        packet["status"] = "FOUNDER_DECIDED_AND_APPLIED"
        packet["decided_at"] = DECISION_DATE
        packet["decided_by"] = FOUNDER
        packet["decision_work_order"] = WORK_ORDER
        for cand in packet["positive_candidates"]:
            cand["founder_decision"] = POSITIVE_DECISIONS[cand["queue_id"]]
            cand["outcome"] = "PUBLISHED"
        for cand in packet["negative_candidates"]:
            cand["founder_decision"] = "APPROVE_VERIFIED_NO_PETS"
            cand["outcome"] = "EXCLUDED_VERIFIED_NO_PETS"
        for delta in packet["drury_reattestation_deltas"]:
            delta["founder_decision"] = "APPROVE_REATTESTATION"
            delta["outcome"] = "REATTESTED"
        write_lf(PACKET_PATH, packet)
        report_path = LP / "cleveland_artifact_verification_001.json"
        report = load_json(report_path)
        report["facts_sha256_after_pass2_decisions"] = new_sha
        write_lf(report_path, report)
        summary["facts_sha256"] = new_sha
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--data-root", type=Path,
                        default=Path("C:/Atlas/atlas-dashboard/data"))
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    summary = run(args.data_root, args.apply)
    for key, value in summary.items():
        print("%s: %s" % (key, json.dumps(value, ensure_ascii=False)
                          if not isinstance(value, str) else value))
    if not args.apply:
        print("dry run: nothing written")
    return 0


if __name__ == "__main__":
    sys.exit(main())
