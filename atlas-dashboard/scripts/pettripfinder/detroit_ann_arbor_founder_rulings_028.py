# -*- coding: utf-8 -*-
"""Founder rulings on PTF-DETROIT-ANN-ARBOR-FINAL-REVIEW-AND-DEPLOY-PREP-028.

Four rulings, three of which publish.

DOUBLETREE ANN ARBOR NORTH -- APPROVE PET_FRIENDLY. The page says "Pets allowed
Yes" and prices them; the only refusal on it is scoped to food and beverage
areas. The committed classifier short-circuits on that scoped phrase and calls
the whole block a refusal, which is why this needed a founder. THE SHARED
CLASSIFIER IS NOT WIDENED -- the override is stamped on this record alone.

WESTIN BOOK CADILLAC -- HOLD. Fee text is not acceptance. The founder declined
to infer pets_allowed from "$50 per day, $150 maximum" and declined to make a
general rule of it, so nothing is published and no rule changes. This is the
third property showing that pattern; it stays a per-identity decision.

ROYAL PARK and THE SIREN -- APPROVE_PARTIAL, pets_allowed alone. Both pages are
marketing prose with no operational term, which the repaired vocabulary
deliberately grades MARKETING_ONLY. The founder ruled the boolean only, and
every unstated term stays unstated.
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

from scripts.pettripfinder import (                                # noqa: E402
    detroit_ann_arbor_authority_application_011 as A11,
    detroit_ann_arbor_candidate_reconciliation_011 as R11,
    market_authority as MA)
from scripts.pettripfinder.contracts import enums                  # noqa: E402
from scripts.pettripfinder.contracts import evidence as evidence_contract  # noqa: E402
from scripts.pettripfinder.contracts import policy_schema          # noqa: E402

MARKET = "detroit-ann-arbor-mi"
WORK_ORDER = "PTF-DETROIT-ANN-ARBOR-FINAL-REVIEW-AND-DEPLOY-PREP-028"
INSTRUMENT = "FOUNDER RULINGS -- FINAL-REVIEW-AND-DEPLOY-PREP-028"
DECISION_DATE = "2026-08-30"
FOUNDER = "jfields80"

LP = A11.LP
PACKET = LP / "detroit_ann_arbor_final_founder_packet_028.json"
FACTS_PATH = LP / ("hotel_policy_facts_%s.json" % MARKET)
RULINGS_PATH = LP / "detroit_ann_arbor_founder_rulings_028.json"

DOUBLETREE = "doubletree by hilton ann arbor north"
WESTIN = "westin book cadillac detroit"
ROYAL_PARK = "royal park hotel"
SIREN = "the siren hotel"


def facts_for(key, block):
    """Exactly the fields the founder authorised for this identity."""
    if key == DOUBLETREE:
        return OrderedDict([
            ("pets_allowed", True),
            ("pet_fee", OrderedDict([("amount_cents", 7500),
                                     ("currency", "USD"),
                                     ("basis", enums.BASIS_PER_STAY),
                                     ("refundable", False)])),
            ("weight_limit", OrderedDict([("value", 60), ("unit", "lb"),
                                          ("operator", "lte"),
                                          ("scope", "per_pet")])),
            ("combined_weight_limit", OrderedDict([("value", 60),
                                                   ("unit", "lb"),
                                                   ("operator", "lte")])),
            ("pet_count_limit", 2),
        ])
    return OrderedDict([("pets_allowed", True)])


def quotes_for(key):
    if key == DOUBLETREE:
        return OrderedDict([
            ("pets_allowed", "Pets allowed Yes"),
            ("pet_fee", "$75.00 Non-refundable Fee"),
            ("weight_limit", "Max weight 60 lbs"),
            ("pet_count_limit", "Limit 2 pets per room"),
            ("combined_weight_limit", "combined weight limit 60lbs"),
        ])
    if key == ROYAL_PARK:
        return OrderedDict([("pets_allowed", "Four-Legged Friends Welcome")])
    return OrderedDict([("pets_allowed", "Pet Friendly Hotel")])


def run():
    packet = R11.load(PACKET)
    questions = {q["identity_key"]: q for q in packet["questions"]}
    census = {row["identity_key"]: row for row in
              R11.load(LP / "identity_census" / ("%s.json" % MARKET))["hotels"]}
    routes = {route["hotel_ref"]["identity_key"]: route for route in
              R11.load(MA.routing_shard_path(MARKET))["routes"]
              if route["status"] == "ROUTING_CONFIRMED"}
    facts_doc = R11.load(FACTS_PATH)
    published = {row["identity_key"] for row in facts_doc["hotels"]}
    excluded = {row["normalized_name"] for row in
                R11.load(MA.exclusions_shard_path(MARKET))["exclusions"]}

    A11.WORK_ORDER = WORK_ORDER
    A11.DECISION_DATE = DECISION_DATE

    approvals = OrderedDict([
        (DOUBLETREE, OrderedDict([
            ("decision", "APPROVE_PET_FRIENDLY"),
            ("clause",
             "APPROVE PET_FRIENDLY. 'Pets allowed Yes' is explicit. 'Pets not "
             "allowed in food or beverage areas' is a scoped-area "
             "restriction, not a whole-property refusal. Publish "
             "pets_allowed, pet_fee $75 non-refundable, weight_limit 60 lb, "
             "pet_count_limit 2, combined weight limit 60 lb."),
            ("caveat",
             "FOUNDER DISPOSITION overriding the committed classifier, which "
             "graded this block REFUSED because its refusal patterns match "
             "the scoped food-and-beverage sentence and short-circuit. The "
             "founder ruled the scope. THE SHARED CLASSIFIER IS UNCHANGED and "
             "its judgement stands everywhere else."),
            ("source_grade", enums.GRADE_PT2_BRAND),
            ("artifact_kind", enums.ARTIFACT_RENDERED_HTML),
            ("capture_method", "rendered_fetch"),
        ])),
        (ROYAL_PARK, OrderedDict([
            ("decision", "APPROVE_PARTIAL_PET_FRIENDLY"),
            ("clause",
             "APPROVE_PARTIAL. Publish pets_allowed = true. Withhold fee, "
             "weight, count and any species detail beyond what the source "
             "explicitly supports."),
            ("caveat",
             "FOUNDER DISPOSITION on marketing prose. The repaired vocabulary "
             "grades this MARKETING_ONLY -- a welcoming sentence with no fee, "
             "weight, count or species -- and deliberately refuses to promote "
             "a slogan to a policy. The founder ruled the boolean ALONE. "
             "IDENTITY-SPECIFIC: the vocabulary is unchanged."),
            ("source_grade", enums.GRADE_PT1_FIRST_PARTY),
            ("artifact_kind", enums.ARTIFACT_TEXT_EXTRACT),
            ("capture_method", "attended_browser"),
        ])),
        (SIREN, OrderedDict([
            ("decision", "APPROVE_PARTIAL_PET_FRIENDLY"),
            ("clause",
             "APPROVE_PARTIAL. Publish pets_allowed = true. Withhold all "
             "unstated operational terms."),
            ("caveat",
             "FOUNDER DISPOSITION on marketing prose, as Royal Park. "
             "IDENTITY-SPECIFIC; the shared vocabulary is unchanged."),
            ("source_grade", enums.GRADE_PT1_FIRST_PARTY),
            ("artifact_kind", enums.ARTIFACT_TEXT_EXTRACT),
            ("capture_method", "attended_browser"),
        ])),
    ])

    rulings, new_records = [], []
    for key, spec in approvals.items():
        if key in published or key in excluded:
            raise SystemExit("STOP: %r already carries authority" % key)
        question = questions[key]
        block = question["evidence"]
        source_url = routes[key]["official_property_url"]
        census_row = census[key]

        A11.SOURCE_GRADE = spec["source_grade"]
        A11.ARTIFACT_KIND = spec["artifact_kind"]
        A11.CAPTURE_METHOD = spec["capture_method"]

        facts = facts_for(key, block)
        unknown = [f for f in facts if f not in policy_schema.KNOWN_FACT_FIELDS]
        if unknown:
            raise SystemExit("STOP: not schema fact fields: %s" % unknown)

        quotes = quotes_for(key)
        for field, quote in quotes.items():
            if not evidence_contract.quote_is_contiguous(quote, block):
                raise SystemExit("STOP: %s quote %r is not verbatim in the "
                                 "evidence" % (key, quote))
        evidence = A11.build_evidence(
            [{"quote": q, "field_refs": [f]} for f, q in quotes.items()],
            block, source_url, hashlib.sha256(block.encode("utf-8")).hexdigest(),
            key)

        record = OrderedDict([
            ("key", key), ("name", census_row["canonical_name"]),
            ("facts", facts), ("evidence", evidence),
            ("evidence_count", len(evidence)),
            ("evidence_quote", " […] ".join(dict.fromkeys(quotes.values()))),
            ("source_url", source_url),
            ("source_type", "EXACT_ENTITY_DOMAIN"),
            ("verification_state", "VERIFIED_PET_FRIENDLY"),
            ("verification_date", DECISION_DATE),
            ("verified_at", DECISION_DATE),
            ("worker_model_id", ""), ("worker_prompt_version", ""),
            ("worker_result_hash",
             hashlib.sha256(block.encode("utf-8")).hexdigest()),
            ("worker_routing_version", ""), ("worker_validator_version", ""),
            ("schema_version", "1.2"),
            ("identity_key", key), ("market_id", MARKET),
        ])
        from scripts.pettripfinder import canonical_view
        record["computation_class"] = (
            canonical_view.classify(facts).computation_class
            if hasattr(canonical_view, "classify") else "DIRECT")
        issues = (list(policy_schema.validate_record(record))
                  + list(evidence_contract.validate(record)))
        if issues:
            raise SystemExit("STOP: contract issues for %s: %s"
                             % (key, issues[:4]))

        record["approval"] = OrderedDict([
            ("decision", enums.APPROVED_AFTER_CURRENT_REVIEW),
            ("operator", FOUNDER), ("approval_date", DECISION_DATE),
            ("authorisation", OrderedDict([
                ("instrument", INSTRUMENT), ("work_order", WORK_ORDER),
                ("clause", spec["clause"]),
                ("scope", "THIS IDENTITY ONLY, bound to this exact evidence."),
                ("spend_usd", 0.0),
            ])),
            ("caveats", [spec["caveat"],
                         "Published fields are exactly those the founder "
                         "named; nothing else was added because the evidence "
                         "might support it."]),
            ("founder_disposition", OrderedDict([
                ("fields_authorised", list(facts)),
                ("pets_allowed_source", "FOUNDER_DISPOSITION"),
                ("shared_reader_modified", False),
                ("shared_classifier_modified", False),
            ])),
            ("record_hash", A11.record_hash(record)),
            ("evidence_hash", A11.evidence_hash(evidence)),
            ("decision_hash", "sha256:%s" % hashlib.sha256(json.dumps(
                OrderedDict([("identity_key", key),
                             ("work_order", WORK_ORDER),
                             ("decision", spec["decision"]),
                             ("fields", list(facts)),
                             ("evidence", block)]),
                sort_keys=True, ensure_ascii=False).encode("utf-8")
            ).hexdigest()),
        ])
        new_records.append(record)
        rulings.append(OrderedDict([
            ("identity_key", key),
            ("canonical_name", census_row["canonical_name"]),
            ("decision", spec["decision"]), ("published", True),
            ("fields_published", list(facts)),
            ("classifier_result_overridden",
             question["current_classifier_result"]),
            ("shared_rules_modified", False),
        ]))

    # ---- Westin: HOLD, publishes nothing ------------------------------- #
    westin = questions[WESTIN]
    rulings.append(OrderedDict([
        ("identity_key", WESTIN),
        ("canonical_name", census[WESTIN]["canonical_name"]),
        ("decision", "HOLD"), ("published", False), ("fields_published", []),
        ("evidence_ruled_on", westin["evidence"]),
        ("founder_reasoning",
         "Evidence gives $50/day and a $150 maximum, but ordinary-pet "
         "acceptance is not explicitly stated in words. Do NOT infer "
         "pets_allowed from fee text alone. Do NOT create a generic rule."),
        ("identity_state", "RETAINED, UNRESOLVED"),
        ("note",
         "The THIRD property in this market to show terms-without-acceptance, "
         "after TownePlace Dearborn and Embassy Suites Livonia Novi. The "
         "founder ruled the other two APPROVE and this one HOLD, all three "
         "identity-specific, and explicitly declined to generalise. The "
         "difference is what the pages say: those two named pet counts and "
         "species; this one states a price and nothing else."),
        ("shared_rules_modified", False),
    ]))

    facts_doc["hotels"] = list(facts_doc["hotels"]) + new_records
    A11.write_lf(FACTS_PATH, facts_doc)

    R11.write_lf(RULINGS_PATH, OrderedDict([
        ("schema", "ptf-detroit-ann-arbor-founder-rulings/1.3"),
        ("work_order", WORK_ORDER), ("instrument", INSTRUMENT),
        ("market_id", MARKET),
        ("decided_at", DECISION_DATE), ("decided_by", FOUNDER),
        ("provider_calls", 0), ("spend_usd", 0.0),
        ("shared_reader_modified", False),
        ("shared_classifier_modified", False),
        ("authority_added", len(new_records)),
        ("rulings", rulings),
    ]))

    print("=== founder rulings 028 applied ===")
    for ruling in rulings:
        print("   %-40s %-30s published=%s"
              % (ruling["canonical_name"][:40], ruling["decision"],
                 ruling["published"]))
    print("   pet-friendly now:", len(facts_doc["hotels"]))


if __name__ == "__main__":
    run()
