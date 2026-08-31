# -*- coding: utf-8 -*-
"""Founder rulings on PTF-DETROIT-ANN-ARBOR-FREE-ATTENDED-PASS-020.

Applies the three rulings on the order-020 exception packet. No provider is
called and nothing is acquired.

KENSINGTON -- APPROVE_PARTIAL. pets_allowed only, with the founder's exact
wording preserved as the limitation. I recommended a HOLD and the founder ruled
the other way; the ruling governs. What that changes is the boolean ALONE: no
fee, species, count or weight is published, because the site states none.

ROBERTS RIVERWALK -- ROUTING_REPAIR_REQUIRED. Nothing published. The identity
is RETAINED as unresolved, explicitly NOT withdrawn as abandoned, and the dead
route is preserved as evidence so the next pass inherits the finding instead of
rediscovering a gambling redirect.

EMBASSY SUITES LIVONIA NOVI -- APPROVE PET_FRIENDLY, IDENTITY-SPECIFIC, on the
newly captured evidence. The founder extends the TownePlace reasoning to this
property and this evidence only.

THE SHARED READER IS NOT TOUCHED BY ANY OF THIS. The reader withheld
``pets_allowed`` on Embassy as SOURCE_SILENT and that judgement still stands
everywhere else; here a founder ruled on one property's wording, and the
overridden field is stamped so no later reader is credited with a decision it
declined to make.

THE APPROVED FIELD LISTS ARE EXHAUSTIVE. Kensington's block would also support
nothing else, but Embassy's reader additionally emits FLAG_STRUCTURED_TIERS and
a ``basis_stated: false`` on each rung; the tiers are published as the founder
named them and no basis is invented for either rung.
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
    detroit_ann_arbor_candidate_reconciliation_011 as R11)
from scripts.pettripfinder.contracts import enums                  # noqa: E402
from scripts.pettripfinder.contracts import evidence as evidence_contract  # noqa: E402
from scripts.pettripfinder.contracts import policy_schema          # noqa: E402

MARKET = "detroit-ann-arbor-mi"
WORK_ORDER = "PTF-DETROIT-ANN-ARBOR-FREE-ATTENDED-PASS-020"
INSTRUMENT = "FOUNDER RULINGS -- DETROIT FREE ATTENDED PASS 020"
DECISION_DATE = "2026-08-30"
FOUNDER = "jfields80"

LP = A11.LP
RESULTS = LP / "detroit_ann_arbor_attended_results_020.json"
FACTS_PATH = LP / ("hotel_policy_facts_%s.json" % MARKET)
RULINGS_PATH = LP / "detroit_ann_arbor_founder_rulings_020.json"

KENSINGTON = "the kensington hotel ann arbor"
ROBERTS = "roberts riverwalk hotel"
EMBASSY = "embassy suites by hilton detroit livonia novi"

#: Verbatim from the founder. Exhaustive: nothing outside these is published.
KENSINGTON_FIELDS = ("pets_allowed", "general_restrictions")
EMBASSY_FIELDS = ("pets_allowed", "fee_tiers", "pet_count_limit", "species")

#: The founder's own words, preserved exactly as instructed.
KENSINGTON_LIMITATION = "pet-friendly rooms"


class Stop(SystemExit):
    pass


def verify_block(artifact: str, expected_sha: str, key: str):
    path = _REPO_ROOT / artifact
    if not path.exists():
        raise Stop("STOP: %s -- persisted block missing at %s" % (key, artifact))
    raw = path.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != expected_sha:
        raise Stop("STOP: %s -- block sha256 does not reproduce from disk "
                   "(%s vs %s)" % (key, digest, expected_sha))
    return raw.decode("utf-8"), digest


def approval_block(key, decision, clause, fields, caveats, record, evidence,
                   block_sha, document_sha, extra=None):
    approval = OrderedDict([
        ("decision", enums.APPROVED_AFTER_CURRENT_REVIEW),
        ("operator", FOUNDER), ("approval_date", DECISION_DATE),
        ("authorisation", OrderedDict([
            ("instrument", INSTRUMENT),
            ("work_order", WORK_ORDER),
            ("clause", clause),
            ("scope", "THIS IDENTITY ONLY, bound to this exact evidence."),
            ("lane", "attended_chrome"), ("spend_usd", 0.0),
        ])),
        ("caveats", caveats),
        ("founder_disposition", OrderedDict([
            ("fields_authorised", list(fields)),
            ("pets_allowed_source", "FOUNDER_DISPOSITION"),
            ("shared_reader_modified", False),
        ])),
        ("record_hash", A11.record_hash(record)),
        ("evidence_hash", A11.evidence_hash(evidence)),
    ])
    if extra:
        approval["founder_disposition"].update(extra)
    approval["decision_hash"] = "sha256:%s" % hashlib.sha256(
        json.dumps(OrderedDict([
            ("identity_key", key), ("work_order", WORK_ORDER),
            ("decision", decision), ("fields", list(fields)),
            ("block_sha256", block_sha), ("document_sha256", document_sha),
        ]), sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()
    return approval


def build_record(key, name, facts, evidence, source_url, document_sha, quotes):
    record = OrderedDict([
        ("key", key), ("name", name),
        ("facts", facts), ("evidence", evidence),
        ("evidence_count", len(evidence)),
        ("evidence_quote", " […] ".join(dict.fromkeys(quotes))),
        ("source_url", source_url),
        ("source_type", "EXACT_ENTITY_DOMAIN"),
        ("verification_state", "VERIFIED_PET_FRIENDLY"),
        ("verification_date", DECISION_DATE), ("verified_at", DECISION_DATE),
        ("worker_model_id", ""), ("worker_prompt_version", ""),
        ("worker_result_hash", document_sha), ("worker_routing_version", ""),
        ("worker_validator_version", ""), ("schema_version", "1.2"),
        ("identity_key", key), ("market_id", MARKET),
    ])
    from scripts.pettripfinder import canonical_view
    record["computation_class"] = (
        canonical_view.classify(facts).computation_class
        if hasattr(canonical_view, "classify") else "DIRECT")
    issues = (list(policy_schema.validate_record(record))
              + list(evidence_contract.validate(record)))
    if issues:
        raise Stop("STOP: contract issues for %s: %s" % (key, issues[:4]))
    return record


def run() -> None:
    results = R11.load(RESULTS)
    rows = {row["identity_key"]: row for row in results["results"]}
    recap = results["recapture"]
    facts_doc = R11.load(FACTS_PATH)
    published = {row["identity_key"] for row in facts_doc["hotels"]}
    census = {row["identity_key"]: row for row in
              R11.load(LP / "identity_census" / ("%s.json" % MARKET))["hotels"]}
    routed = {route["hotel_ref"]["identity_key"]:
              (route.get("official_property_url") or "")
              for route in R11.load(LP / "markets" / "authority" / MARKET
                                    / "identity_routing.json")["routes"]}

    for key in (KENSINGTON, EMBASSY, ROBERTS):
        if key in published:
            raise Stop("STOP: %r already carries Detroit authority" % key)

    new_records = []

    # ---- ruling 1: Kensington, APPROVE_PARTIAL ------------------------- #
    row = rows[KENSINGTON]
    block_text, block_sha = verify_block(row["block_artifact"],
                                         row["block_sha256"], KENSINGTON)
    source_url = routed.get(KENSINGTON) or ""
    if not source_url.lower().startswith("https://"):
        raise Stop("STOP: no absolute routed URL for %r" % KENSINGTON)
    if KENSINGTON_LIMITATION not in block_text:
        raise Stop("STOP: the founder's wording is not verbatim in the block")

    k_facts = OrderedDict([
        ("pets_allowed", True),
        ("general_restrictions", KENSINGTON_LIMITATION),
    ])
    unknown = [f for f in k_facts if f not in policy_schema.KNOWN_FACT_FIELDS]
    if unknown:
        raise Stop("STOP: not schema 1.2 fact fields: %s" % unknown)
    k_quotes = [block_text.strip()]
    k_evidence = A11.build_evidence(
        [{"quote": k_quotes[0],
          "field_refs": ["pets_allowed", "general_restrictions"]}],
        block_text, source_url, block_sha, KENSINGTON)
    k_record = build_record(KENSINGTON, census[KENSINGTON]["canonical_name"],
                            k_facts, k_evidence, source_url, block_sha,
                            k_quotes)
    k_record["approval"] = approval_block(
        KENSINGTON, "APPROVE_PARTIAL_PET_FRIENDLY",
        "APPROVE_PARTIAL PET_FRIENDLY. Approve pets_allowed = true. Preserve "
        "the exact wording 'pet-friendly rooms'. WITHHOLD pet_fee, species, "
        "pet_count_limit, weight_limit and all other unsupported terms. Do "
        "not infer that every room is pet-friendly.",
        KENSINGTON_FIELDS,
        ["FOUNDER DISPOSITION. The property's own marketing prose names "
         "'pet-friendly rooms' as a room type and states NO terms anywhere on "
         "15 swept pages. This run recommended a HOLD on exactly that ground; "
         "the founder ruled the phrase is affirmative property-specific "
         "evidence that the hotel accommodates pets. The ruling governs, and "
         "it moves the boolean ALONE.",
         "WITHHELD: pet_fee, species, pet_count_limit, weight_limit and every "
         "other term -- the source states none of them, and silence is not a "
         "fact.",
         "THE LIMITATION IS CARRIED, NOT DROPPED: general_restrictions holds "
         "the founder's exact wording so the record never implies every room "
         "is pet-friendly.",
         "THE SHARED READER IS UNCHANGED. Marketing prose remains "
         "insufficient everywhere else in this market.",
         "Evidence re-verified at approval time: the block sha256 reproduces "
         "from disk (%s) and the cited quote is verbatim and contiguous."
         % block_sha[:23]],
        k_record, k_evidence, block_sha, block_sha,
        extra=OrderedDict([
            ("fields_withheld_by_founder", OrderedDict([
                ("pet_fee", "not stated by the source"),
                ("species", "not stated by the source"),
                ("pet_count_limit", "not stated by the source"),
                ("weight_limit", "not stated by the source"),
            ])),
            ("run_recommendation_overridden", "HOLD"),
            ("do_not_infer", "that every room is pet-friendly"),
        ]))
    new_records.append(k_record)

    # ---- ruling 2: Roberts Riverwalk, ROUTING_REPAIR_REQUIRED ---------- #
    roberts = rows[ROBERTS]
    roberts_record = OrderedDict([
        ("identity_key", ROBERTS),
        ("canonical_name", roberts["canonical_name"]),
        ("decision", "ROUTING_REPAIR_REQUIRED"),
        ("decided_by", FOUNDER), ("decided_at", DECISION_DATE),
        ("authorisation", INSTRUMENT),
        ("fields_published", []),
        ("identity_state", "RETAINED AS UNRESOLVED -- expressly NOT withdrawn "
                           "as abandoned"),
        ("dead_route", OrderedDict([
            ("committed_route", routed.get(ROBERTS) or ""),
            ("observed", roberts["note"]),
            ("pages_checked", roberts["pages_checked"]),
            ("verdict", "no longer a hotel policy source"),
        ])),
        ("requirement",
         "a NEW first-party identity route must be established before any "
         "policy publication for this identity"),
        ("founder_reasoning",
         "detroitriverwalkhotel.com is no longer a hotel policy source and "
         "redirects to an unrelated gambling site. Do not publish policy from "
         "the current route. Retain the identity as unresolved."),
        ("shared_reader_modified", False),
    ])

    # ---- ruling 3: Embassy Suites Livonia Novi, APPROVE ---------------- #
    artifact = recap.get("block_artifact") or recap.get("artifact") or ""
    block_text, block_sha = verify_block(artifact, recap["block_sha256"],
                                         EMBASSY)
    source_url = recap["surface_reached"]
    if not source_url.lower().startswith("https://"):
        raise Stop("STOP: no absolute captured URL for %r" % EMBASSY)
    binding = recap["identity_binding"]
    if binding["jsonld_name"] != census[EMBASSY]["canonical_name"]:
        raise Stop("STOP: the captured page does not name this identity")
    if binding["routed_property_code"] not in source_url:
        raise Stop("STOP: the captured URL does not carry the routed property "
                   "code")

    e_facts = OrderedDict([
        ("pets_allowed", True),
        ("fee_tiers", [
            OrderedDict([("amount_cents", 7500), ("currency", "USD"),
                         ("role", "REPLACEMENT_PRICE"),
                         ("condition_type", "stay_length_range"),
                         ("boundary_unit", "nights"),
                         ("condition_min", 1), ("condition_max", 4),
                         ("basis_stated", False)]),
            OrderedDict([("amount_cents", 12500), ("currency", "USD"),
                         ("role", "REPLACEMENT_PRICE"),
                         ("condition_type", "stay_length_range"),
                         ("boundary_unit", "nights"),
                         ("condition_min", 5),
                         ("basis_stated", False)]),
        ]),
        ("pet_count_limit", 2),
        ("species", OrderedDict([("dogs", enums.SPECIES_ACCEPTED),
                                 ("cats", enums.SPECIES_ACCEPTED)])),
    ])
    unknown = [f for f in e_facts if f not in policy_schema.KNOWN_FACT_FIELDS]
    if unknown:
        raise Stop("STOP: not schema 1.2 fact fields: %s" % unknown)

    e_quotes = OrderedDict([
        ("1-4 night stay $75", ["pets_allowed", "fee_tiers"]),
        ("5+ night stay $125", ["fee_tiers"]),
        ("2 pets max", ["pet_count_limit"]),
        ("dog or cat only", ["species"]),
    ])
    e_evidence = A11.build_evidence(
        [{"quote": quote, "field_refs": refs}
         for quote, refs in e_quotes.items()],
        block_text, source_url, block_sha, EMBASSY)
    e_record = build_record(EMBASSY, census[EMBASSY]["canonical_name"],
                            e_facts, e_evidence, source_url, block_sha,
                            list(e_quotes))
    e_record["approval"] = approval_block(
        EMBASSY, "APPROVE_PET_FRIENDLY",
        "APPROVE PET_FRIENDLY, IDENTITY-SPECIFIC. Approve pets_allowed = "
        "true, fee tier $75 for 1-4 nights, fee tier $125 for 5+ nights, "
        "pet_count_limit = 2, species = dogs and cats. Bind only to this "
        "identity and the newly captured evidence.",
        EMBASSY_FIELDS,
        ["FOUNDER DISPOSITION on one property's wording, extending the "
         "TownePlace Suites Dearborn ruling of order 019 to this identity and "
         "this evidence. The page states operative pet terms but never says "
         "in words that pets are accepted, so the committed reader withheld "
         "pets_allowed as SOURCE_SILENT. The founder ruled those terms are "
         "meaningful only as terms governing accepted pets.",
         "THE SHARED READER IS UNCHANGED. Its SOURCE_SILENT judgement stands "
         "everywhere else, and this reasoning is not transferred into it.",
         "THE HOLD OF ORDER 019 IS CLEARED BY NEW EVIDENCE. The prior "
         "question-only block ('Are pets allowed at ...?') is SUPERSEDED IN "
         "PROVENANCE, NOT ERASED: it remains on the record as the evidence "
         "the founder held on, and this record cites only the new capture.",
         "NO BASIS IS INVENTED FOR EITHER RUNG. The surface states amounts "
         "and stay lengths and never says whether a rung is charged per night "
         "or per stay; basis_stated records that it did not, and no single "
         "pet_fee amount is asserted over a two-band ladder.",
         "IDENTITY RE-VERIFIED AT APPROVAL TIME: the page's own JSON-LD name "
         "matches the census identity, the stated address is %s, and the "
         "captured URL carries the routed property code %r."
         % (binding["page_address"], binding["routed_property_code"]),
         "Evidence re-verified at approval time: the block sha256 reproduces "
         "from disk (%s), cross-verified in-page against crypto.subtle at "
         "capture, and every cited quote is verbatim and contiguous."
         % block_sha[:23]],
        e_record, e_evidence, block_sha, block_sha,
        extra=OrderedDict([
            ("supersedes",
             "the order-019 HOLD_FOR_RE_CAPTURE on question-only evidence"),
            ("precedent_applied",
             "the founder's TownePlace Suites Dearborn ruling, order 019 -- "
             "applied BY THE FOUNDER to this identity, not generalised by "
             "this run"),
            ("acquired_by", "attended Chrome, order 020, $0"),
        ]))
    new_records.append(e_record)

    facts_doc["hotels"] = list(facts_doc["hotels"]) + new_records
    A11.write_lf(FACTS_PATH, facts_doc)

    R11.write_lf(RULINGS_PATH, OrderedDict([
        ("schema", "ptf-detroit-ann-arbor-founder-rulings/1.1"),
        ("work_order", WORK_ORDER), ("instrument", INSTRUMENT),
        ("market_id", MARKET),
        ("decided_at", DECISION_DATE), ("decided_by", FOUNDER),
        ("provider_calls", 0), ("spend_usd", 0.0),
        ("shared_reader_modified", False),
        ("rulings", [
            OrderedDict([
                ("identity_key", KENSINGTON),
                ("decision", "APPROVE_PARTIAL_PET_FRIENDLY"),
                ("published", True),
                ("fields_published", list(k_facts)),
                ("run_recommendation", "HOLD"),
                ("overridden_by_founder", True),
            ]),
            roberts_record,
            OrderedDict([
                ("identity_key", EMBASSY),
                ("decision", "APPROVE_PET_FRIENDLY"),
                ("published", True),
                ("fields_published", list(e_facts)),
                ("run_recommendation", "APPROVE (packet)"),
                ("overridden_by_founder", False),
            ]),
        ]),
    ]))

    print("=== founder rulings applied ===")
    print("  Kensington      : APPROVE_PARTIAL -> published %s"
          % list(k_facts))
    print("  Roberts Riverwalk: ROUTING_REPAIR_REQUIRED -> nothing published, "
          "identity retained unresolved")
    print("  Embassy Livonia : APPROVE_PET_FRIENDLY -> published %s"
          % list(e_facts))
    print("  pet-friendly now: %d" % len(facts_doc["hotels"]))
    print("wrote", FACTS_PATH.name, "and", RULINGS_PATH.name)


if __name__ == "__main__":
    run()
