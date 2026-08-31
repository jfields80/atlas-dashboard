# -*- coding: utf-8 -*-
"""PTF-DETROIT-ANN-ARBOR-BRIGHTDATA-AUTHORITY-APPLICATION-019, Phase 6.

Applies the founder's two rulings on the policy-wording exceptions.

EMBASSY SUITES LIVONIA NOVI -- HOLD FOR RE-CAPTURE. Nothing is published, no
pet-policy field is written, and the identity stays unresolved and routed so a
later zero-cost capture can answer it. Recorded so the hold is a decision on the
record rather than an absence.

TOWNEPLACE SUITES DEARBORN -- APPROVED PET_FRIENDLY, IDENTITY-SPECIFIC.

THE APPROVED FIELD LIST IS EXHAUSTIVE AND IS TREATED THAT WAY. The founder
approved pets_allowed, pet_fee, fee_basis, non_refundable and pet_count_limit,
and withheld weight_limit. The committed projection ALSO reads
``pet_count_scope: per_room`` from the same sentence -- "Maximum Number of Pets
in Room: 2" -- and it is still not published, because it is not on the list. An
approval binds to the fields it names; quietly adding a sixth because the
evidence would support it is how an approval stops meaning anything.

THE SHARED READER IS NOT TOUCHED. The reader withheld ``pets_allowed`` as
SOURCE_SILENT and the fee as SCHEMA_CANNOT_REPRESENT; those judgements stand
everywhere else. Here a founder ruled on one property's wording, and each
overridden field is stamped with that ruling so no later reader is credited with
a decision it declined to make.
"""
from __future__ import annotations

import hashlib
import json
import sys
from collections import OrderedDict
from pathlib import Path
from typing import Dict

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder import (                                # noqa: E402
    detroit_ann_arbor_authority_application_011 as A11,
    detroit_ann_arbor_candidate_reconciliation_011 as R11)
from scripts.pettripfinder.contracts import enums                  # noqa: E402
from scripts.pettripfinder.contracts import evidence as evidence_contract  # noqa: E402
from scripts.pettripfinder.contracts import policy_schema          # noqa: E402

MARKET = "detroit-ann-arbor-mi"
WORK_ORDER = "PTF-DETROIT-ANN-ARBOR-BRIGHTDATA-AUTHORITY-APPLICATION-019"
DECISION_DATE = "2026-08-30"
FOUNDER = "jfields80"

LP = A11.LP
EXCEPTIONS = LP / "detroit_ann_arbor_founder_exceptions_019.json"
FACTS_PATH = LP / ("hotel_policy_facts_%s.json" % MARKET)
RULINGS_PATH = LP / "detroit_ann_arbor_founder_rulings_019.json"

HOLD_KEY = "embassy suites by hilton detroit livonia novi"
APPROVE_KEY = "towneplace suites by marriott detroit dearborn"

#: Verbatim from the founder. Exhaustive: nothing outside it is published.
APPROVED_FIELDS = ("pets_allowed", "pet_fee", "fee_basis", "non_refundable",
                   "pet_count_limit")
WITHHELD_BY_FOUNDER = {"weight_limit":
                       "the captured surface does not establish the operator "
                       "and scope the schema requires"}
#: Read by the committed projection from the very sentence the founder quoted,
#: and still not published, because it is not on the approved list.
NOT_ON_THE_APPROVED_LIST = {"pet_count_scope": "per_room"}


def run() -> None:
    exceptions = R11.load(EXCEPTIONS)
    rows = {row["identity_key"]: row
            for row in exceptions["policy_wording_exceptions"]}
    facts_doc = R11.load(FACTS_PATH)
    published = {row["identity_key"] for row in facts_doc["hotels"]}

    # ---- ruling 1: HOLD ------------------------------------------------ #
    hold = rows[HOLD_KEY]
    if HOLD_KEY in published:
        raise SystemExit("STOP: the held identity already carries authority")
    hold_record = OrderedDict([
        ("identity_key", HOLD_KEY),
        ("canonical_name", hold["canonical_name"]),
        ("brand", hold["brand"]),
        ("decision", "HOLD_FOR_RE_CAPTURE"),
        ("decided_by", FOUNDER), ("decided_at", DECISION_DATE),
        ("authorisation", WORK_ORDER),
        ("evidence_ruled_on", (hold["reading"] or {}).get("block_text") or ""),
        ("block_sha256", (hold["reading"] or {}).get("block_sha256") or ""),
        ("document_sha256", (hold["reading"] or {}).get("document_sha256") or ""),
        ("founder_reasoning",
         "That is a question, not an answer. Publish no pet-policy fields from "
         "this evidence."),
        ("fields_published", []),
        ("identity_state", "UNRESOLVED -- kept available for a later "
                           "zero-cost or recovery capture"),
        ("shared_reader_modified", False),
    ])

    # ---- ruling 2: APPROVE, identity-specific -------------------------- #
    row = rows[APPROVE_KEY]
    if APPROVE_KEY in published:
        raise SystemExit("STOP: the approved identity already carries "
                         "authority")
    census = {entry["identity_key"]: entry for entry in
              R11.load(LP / "identity_census" / ("%s.json" % MARKET))["hotels"]}
    census_row = census[APPROVE_KEY]
    routed = {route["hotel_ref"]["identity_key"]:
              (route.get("official_property_url") or "")
              for route in R11.load(LP / "markets" / "authority" / MARKET
                                    / "identity_routing.json")["routes"]}
    source_url = routed.get(APPROVE_KEY) or ""
    if not source_url.lower().startswith("https://"):
        raise SystemExit("STOP: no absolute routed URL for %r" % APPROVE_KEY)

    block_text, _block_sha, document_sha = A11.verify_artifacts(row)

    quotes = OrderedDict([
        ("pets_allowed", "Non-Refundable Pet Fee Per Stay: $100.00"),
        ("pet_fee", "Non-Refundable Pet Fee Per Stay: $100.00"),
        ("pet_count_limit", "Maximum Number of Pets in Room: 2"),
    ])
    for field, quote in quotes.items():
        if not evidence_contract.quote_is_contiguous(quote, block_text):
            raise SystemExit("STOP: the quote for %s is not verbatim in the "
                             "persisted block: %r" % (field, quote))

    facts = OrderedDict([
        ("pets_allowed", True),
        ("pet_fee", OrderedDict([
            ("amount_cents", 10000), ("currency", "USD"),
            ("basis", enums.BASIS_PER_STAY), ("refundable", False),
        ])),
        ("pet_count_limit", 2),
    ])
    unknown = [name for name in facts if name not in policy_schema.KNOWN_FACT_FIELDS]
    if unknown:
        raise SystemExit("STOP: not schema 1.2 fact fields: %s" % unknown)

    evidence = A11.build_evidence(
        [{"quote": quote, "field_refs": [field]}
         for field, quote in quotes.items()],
        block_text, source_url, document_sha, APPROVE_KEY)

    record = OrderedDict([
        ("key", APPROVE_KEY), ("name", census_row["canonical_name"]),
        ("facts", facts), ("evidence", evidence),
        ("evidence_count", len(evidence)),
        ("evidence_quote", " […] ".join(dict.fromkeys(quotes.values()))),
        ("source_url", source_url),
        ("source_type", "EXACT_ENTITY_DOMAIN"),
        ("verification_state", "VERIFIED_PET_FRIENDLY"),
        ("verification_date", DECISION_DATE), ("verified_at", DECISION_DATE),
        ("worker_model_id", ""), ("worker_prompt_version", ""),
        ("worker_result_hash", document_sha), ("worker_routing_version", ""),
        ("worker_validator_version", ""), ("schema_version", "1.2"),
        ("identity_key", APPROVE_KEY), ("market_id", MARKET),
    ])
    from scripts.pettripfinder import canonical_view
    record["computation_class"] = (
        canonical_view.classify(facts).computation_class
        if hasattr(canonical_view, "classify") else "DIRECT")

    issues = (list(policy_schema.validate_record(record))
              + list(evidence_contract.validate(record)))
    if issues:
        raise SystemExit("STOP: contract issues %s" % issues[:4])

    record["approval"] = OrderedDict([
        ("decision", enums.APPROVED_AFTER_CURRENT_REVIEW),
        ("operator", FOUNDER), ("approval_date", DECISION_DATE),
        ("authorisation", OrderedDict([
            ("instrument", WORK_ORDER),
            ("clause", "APPROVE PET_FRIENDLY, IDENTITY-SPECIFIC. Approve "
                       "pets_allowed, pet_fee $100, fee_basis per_stay, "
                       "non_refundable true, pet_count_limit 2. WITHHOLD "
                       "weight_limit."),
            ("scope", "THIS IDENTITY ONLY, bound to this exact evidence."),
            ("acquired_by_order", row["acquired_by_order"]),
            ("attempt_id", row["attempt_id"]),
        ])),
        ("caveats", [
            "FOUNDER DISPOSITION on one property's wording. The page states "
            "pet TERMS -- a $100.00 non-refundable per-stay fee, a 50lb "
            "ceiling and a 2-pet room maximum -- but never says in words that "
            "pets are accepted, so the committed reader withheld "
            "pets_allowed as SOURCE_SILENT and the fee as "
            "SCHEMA_CANNOT_REPRESENT. The founder ruled those terms are "
            "affirmative acceptance. THE SHARED READER IS UNCHANGED: its "
            "judgement stands everywhere else.",
            "WITHHELD BY THE FOUNDER: weight_limit -- the surface states "
            "50.0lbs but not the operator and scope the schema requires, so "
            "the ceiling is not published.",
            "NOT PUBLISHED because it is not on the approved list: "
            "pet_count_scope (the projection reads 'per_room' from the same "
            "sentence). An approval binds to the fields it names.",
            "Evidence re-verified at approval time: the document sha256 "
            "reproduces from disk (%s) and every cited quote appears verbatim "
            "and contiguously in the persisted block." % document_sha[:23],
        ]),
        ("founder_disposition", OrderedDict([
            ("fields_authorised", list(APPROVED_FIELDS)),
            ("fields_withheld_by_founder", WITHHELD_BY_FOUNDER),
            ("fields_available_but_not_authorised", NOT_ON_THE_APPROVED_LIST),
            ("pets_allowed_source", "FOUNDER_DISPOSITION"),
            ("shared_reader_modified", False),
        ])),
        ("record_hash", A11.record_hash(record)),
        ("evidence_hash", A11.evidence_hash(evidence)),
    ])
    record["approval"]["decision_hash"] = "sha256:%s" % hashlib.sha256(
        json.dumps(OrderedDict([
            ("identity_key", APPROVE_KEY),
            ("work_order", WORK_ORDER),
            ("decision", "APPROVE_PET_FRIENDLY"),
            ("fields", list(APPROVED_FIELDS)),
            ("block_sha256", (row["reading"] or {}).get("block_sha256") or ""),
            ("document_sha256", document_sha),
        ]), sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()

    facts_doc["hotels"] = list(facts_doc["hotels"]) + [record]
    A11.write_lf(FACTS_PATH, facts_doc)

    R11.write_lf(RULINGS_PATH, OrderedDict([
        ("schema", "ptf-detroit-ann-arbor-founder-rulings/1.0"),
        ("work_order", WORK_ORDER), ("market_id", MARKET),
        ("decided_at", DECISION_DATE), ("decided_by", FOUNDER),
        ("provider_calls", 0), ("spend_usd", 0.0),
        ("shared_reader_modified", False),
        ("rulings", [
            hold_record,
            OrderedDict([
                ("identity_key", APPROVE_KEY),
                ("canonical_name", census_row["canonical_name"]),
                ("brand", row["brand"]),
                ("decision", "APPROVE_PET_FRIENDLY"),
                ("decided_by", FOUNDER), ("decided_at", DECISION_DATE),
                ("authorisation", WORK_ORDER),
                ("scope", "IDENTITY-SPECIFIC"),
                ("fields_authorised", list(APPROVED_FIELDS)),
                ("fields_withheld_by_founder", WITHHELD_BY_FOUNDER),
                ("fields_available_but_not_authorised",
                 NOT_ON_THE_APPROVED_LIST),
                ("evidence_ruled_on", record["evidence_quote"]),
                ("block_sha256", (row["reading"] or {}).get("block_sha256") or ""),
                ("document_sha256", document_sha),
                ("record_hash", record["approval"]["record_hash"]),
                ("evidence_hash", record["approval"]["evidence_hash"]),
                ("decision_hash", record["approval"]["decision_hash"]),
                ("shared_reader_modified", False),
            ]),
        ]),
    ]))

    print("ruling 1  %-44s HOLD_FOR_RE_CAPTURE (0 fields published)"
          % hold["canonical_name"][:44])
    print("ruling 2  %-44s APPROVE_PET_FRIENDLY"
          % census_row["canonical_name"][:44])
    print("            fields published :", list(facts))
    print("            withheld (founder):", list(WITHHELD_BY_FOUNDER))
    print("            not on the list   :", list(NOT_ON_THE_APPROVED_LIST))
    print("            decision hash     :",
          record["approval"]["decision_hash"][:26])
    print("published now:", len(facts_doc["hotels"]))


if __name__ == "__main__":
    run()
