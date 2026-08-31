# -*- coding: utf-8 -*-
"""Founder rulings on PTF-DETROIT-ANN-ARBOR-ATTENDED-COMPLETION-ADOPTION-022.

Four rulings. Exactly ONE adds authority.

BELL TOWER -- VERIFIED_NO_PETS on a FOUNDER SEMANTIC RULING, not on the shared
refusal reader. The committed classifier records a service_animal_exception
quote and derives no ``pets_allowed`` from a service-animals-only sentence;
this run did not assert one, and the founder has now ruled that "we only allow
service animals" is an affirmative exclusive permission. The record says so in
its own notes, so no later reader is credited with a judgement it declined to
make, and THE SHARED CLASSIFIER IS NOT WIDENED.

HYATT PLACE LIVONIA -- HOLD_SOURCE_POLICY_ATTRIBUTION. Publishes nothing. The
founder was explicit that this is NOT a routing defect: the route and identity
are valid and RETAINED, and the fault is that the property's own page carries
another building's policy.

DRURY and RADISSON -- ROUTING_REPAIR_REQUIRED. Publish nothing, identities
retained, routes marked stale for acquisition purposes. Nothing is inferred
from a route that returned no hotel content.

THE THREE GUARD ISSUES ARE NOT TOUCHED HERE. The seven vocabulary-blocked rows,
Daxton and Sonesta keep their evidence intact and stay withheld, by explicit
founder instruction, for a separate rule-repair order.
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
from scripts.pettripfinder.contracts import evidence as evidence_contract  # noqa: E402
from scripts.pettripfinder import hotel_exclusions as EX          # noqa: E402

MARKET = "detroit-ann-arbor-mi"
WORK_ORDER = "PTF-DETROIT-ANN-ARBOR-ATTENDED-COMPLETION-ADOPTION-022"
INSTRUMENT = "FOUNDER RULINGS -- ATTENDED-COMPLETION-ADOPTION-022"
DECISION_DATE = "2026-08-30"
FOUNDER = "jfields80"

LP = A11.LP
TRIAGE = LP / "detroit_ann_arbor_attended_triage_020.json"
EXCLUSIONS_PATH = MA.exclusions_shard_path(MARKET)
RULINGS_PATH = LP / "detroit_ann_arbor_founder_rulings_022.json"

BELL_TOWER = "the bell tower hotel"
HYATT_LIVONIA = "hyatt place detroit livonia"
DRURY = "drury inn and suites"
RADISSON = "radisson hotel detroit farmington hills"


def run():
    triage = R11.load(TRIAGE)
    rows = {row["identity_key"]: row for row in triage["results"]}
    census = {row["identity_key"]: row for row in
              R11.load(LP / "identity_census" / ("%s.json" % MARKET))["hotels"]}
    routed = {route["hotel_ref"]["identity_key"]:
              (route.get("official_property_url") or "")
              for route in R11.load(MA.routing_shard_path(MARKET))["routes"]}
    excl_doc = R11.load(EXCLUSIONS_PATH)
    facts_doc = R11.load(LP / ("hotel_policy_facts_%s.json" % MARKET))
    published = {row["identity_key"] for row in facts_doc["hotels"]}
    excluded = {row["normalized_name"] for row in excl_doc["exclusions"]}

    # EXACT identity keys, asserted present. A substring search here matched
    # two Livonia properties and would have ruled on the wrong hotel.
    for key in (BELL_TOWER, HYATT_LIVONIA, DRURY, RADISSON):
        if key not in rows:
            raise SystemExit("STOP: %r is not in the order-020 cohort" % key)
    bell, hyatt, drury, radisson = (BELL_TOWER, HYATT_LIVONIA, DRURY,
                                    RADISSON)

    rulings = []

    # ---- ruling 2: Bell Tower, VERIFIED_NO_PETS ------------------------ #
    if bell in published or bell in excluded:
        raise SystemExit("STOP: Bell Tower already carries authority")
    row = rows[bell]
    artifact = _REPO_ROOT / row["block_artifact"]
    raw = artifact.read_bytes()
    digest = hashlib.sha256(raw).hexdigest()
    if digest != row["block_sha256"]:
        raise SystemExit("STOP: Bell Tower block sha256 does not reproduce")
    block_text = raw.decode("utf-8")
    quote = "We only allow service animals, not emotional support animals."
    if not evidence_contract.quote_is_contiguous(quote, block_text):
        raise SystemExit("STOP: the founder's quote is not verbatim in the "
                         "persisted block")
    source_url = routed.get(bell) or ""
    if not source_url.lower().startswith("https://"):
        raise SystemExit("STOP: no absolute routed URL for Bell Tower")
    census_row = census[bell]
    for field in ("address", "postal_code"):
        if not (census_row.get(field) or "").strip():
            raise SystemExit("STOP: the exclusion contract needs %s" % field)

    record = OrderedDict([
        ("exclusion_id", "dtw-%s" % census_row["slug"]),
        ("canonical_name", census_row["canonical_name"]),
        ("normalized_name", bell),
        ("address", census_row.get("address") or ""),
        ("city", census_row.get("city") or ""),
        ("state", census_row.get("state") or ""),
        ("postal_code", census_row.get("postal_code") or ""),
        ("official_url", source_url),
        ("exclusion_state", EX.VERIFIED_NO_PETS),
        ("evidence_quote", quote),
        ("source_url", source_url),
        ("observed_at", DECISION_DATE),
        ("source_hash", digest),
        ("reviewer_id", FOUNDER), ("reviewed_at", DECISION_DATE),
        ("notes",
         "FOUNDER SEMANTIC RULING under %s, IDENTITY-SPECIFIC. The property "
         "answers its own question 'Are pets allowed?' with an EXCLUSIVE "
         "PERMISSION: %r. The committed refusal classifier does NOT derive "
         "pets_allowed from a service-animals-only sentence, and this run did "
         "not assert one -- it held the row for a ruling. The founder ruled "
         "the statement is an affirmative exclusive permission meaning "
         "ordinary pets are not allowed. THE SHARED NO-PETS CLASSIFIER IS "
         "UNCHANGED and this reasoning is not generalised from this one row. "
         "Service-animal access is a legal category and never converts a "
         "no-pets policy into pet-friendly. Captured on attended Chrome at $0 "
         "across 31 first-party pages; the block sha256 was re-verified from "
         "disk at approval time and the quote checked verbatim."
         % (INSTRUMENT, quote)),
        ("market_id", MARKET),
    ])
    record["record_hash"] = EX.record_hash(record)
    record["approval_hash"] = EX.approval_hash(record)
    record["founder_disposition"] = OrderedDict([
        ("decision", "VERIFIED_NO_PETS"),
        ("basis", "FOUNDER_SEMANTIC_RULING"),
        ("derived_by_shared_reader", False),
        ("shared_classifier_modified", False),
        ("service_animal_statement_preserved_in_evidence_quote", True),
        ("scope", "THIS IDENTITY AND THIS EVIDENCE ONLY"),
        ("decision_hash", "sha256:%s" % hashlib.sha256(json.dumps(
            OrderedDict([("identity_key", bell), ("work_order", WORK_ORDER),
                         ("decision", "VERIFIED_NO_PETS"),
                         ("quote", quote), ("block_sha256", digest)]),
            sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()),
    ])
    excl_doc["exclusions"] = list(excl_doc["exclusions"]) + [record]
    excl_doc["count"] = len(excl_doc["exclusions"])
    A11.write_lf(EXCLUSIONS_PATH, excl_doc)
    rulings.append(OrderedDict([
        ("identity_key", bell), ("canonical_name", row["canonical_name"]),
        ("decision", "VERIFIED_NO_PETS"), ("published", True),
        ("basis", "FOUNDER_SEMANTIC_RULING"),
        ("run_recommendation", "RULE ON THE SEMANTICS -- not decided by me"),
        ("shared_classifier_modified", False),
    ]))

    # ---- rulings 1, 3, 4: nothing published ---------------------------- #
    def unresolved_ruling(key, decision, disposition, reasoning, routing_note):
        if key in published or key in excluded:
            raise SystemExit("STOP: %r already carries authority" % key)
        return OrderedDict([
            ("identity_key", key),
            ("canonical_name", rows[key]["canonical_name"]),
            ("decision", decision),
            ("founder_disposition", disposition),
            ("published", False), ("fields_published", []),
            ("decided_by", FOUNDER), ("decided_at", DECISION_DATE),
            ("authorisation", INSTRUMENT),
            ("identity_state", "RETAINED, UNRESOLVED"),
            ("route_state", routing_note),
            ("evidence_ruled_on", rows[key].get("block") or
             "(no property surface was reached)"),
            ("founder_reasoning", reasoning),
            ("shared_reader_modified", False),
        ])

    rulings.append(unresolved_ruling(
        hyatt, "HOLD", "HOLD_SOURCE_POLICY_ATTRIBUTION",
        "The property identity and route are valid, but the pet-policy block "
        "names Hyatt Place Detroit / Auburn Hills rather than Livonia. That is "
        "not evidence for the Livonia property.",
        "RETAINED AND VALID. Expressly NOT a routing defect: the route reached "
        "the correct page; the page itself carries the wrong hotel's policy."))
    rulings.append(unresolved_ruling(
        drury, "ROUTING_REPAIR_REQUIRED", "ROUTING_REPAIR_REQUIRED",
        "The legacy first-party route does not return hotel content. Do not "
        "infer policy from a failed route.",
        "STALE/DEAD for acquisition purposes; a new first-party property route "
        "is required before policy acquisition. Zero-cost rediscovery is the "
        "next action."))
    rulings.append(unresolved_ruling(
        radisson, "ROUTING_REPAIR_REQUIRED", "ROUTING_REPAIR_REQUIRED",
        "The committed URL now collapses to a Radisson brand index rather than "
        "a property page.",
        "STALE for acquisition purposes; property-specific first-party route "
        "recovery is required before policy acquisition."))

    R11.write_lf(RULINGS_PATH, OrderedDict([
        ("schema", "ptf-detroit-ann-arbor-founder-rulings/1.2"),
        ("work_order", WORK_ORDER), ("instrument", INSTRUMENT),
        ("market_id", MARKET),
        ("decided_at", DECISION_DATE), ("decided_by", FOUNDER),
        ("provider_calls", 0), ("spend_usd", 0.0),
        ("shared_reader_modified", False),
        ("authority_added", 1),
        ("rulings", rulings),
        ("guard_issues_deferred_by_founder", [
            OrderedDict([
                ("issue", "AFFIRMATIVE_PET_RES vocabulary-coverage defect"),
                ("rows_blocked", 7),
                ("properties", ["Shinola", "Inn on Ferry Street",
                                "Hyatt House Royal Oak", "Roost Detroit",
                                "Extended Stay America Select Suites",
                                "Royal Park Hotel", "The Siren Hotel"]),
                ("founder_instruction",
                 "Do NOT widen AFFIRMATIVE_PET_RES during Order 022. Preserve "
                 "all seven as CLEAN EVIDENCE blocked by a known vocabulary-"
                 "coverage defect. Do not downgrade them to weak evidence "
                 "merely because the current regex does not understand the "
                 "wording."),
                ("evidence_status", "PRESERVED, unmodified, still on disk"),
            ]),
            OrderedDict([
                ("issue", "Pass-3 freeze guard scope"),
                ("rows_blocked", 1), ("properties", ["Daxton Hotel"]),
                ("founder_instruction",
                 "Leave Daxton withheld. Do not edit the freeze guard during "
                 "the application it blocks. The new first-party FAQ evidence "
                 "is a valid recapture that may qualify Daxton after a "
                 "separate guard-scope review."),
                ("evidence_status", "PRESERVED, unmodified, still on disk"),
            ]),
            OrderedDict([
                ("issue", "Sonesta legacy-alias test scope"),
                ("rows_blocked", 1),
                ("properties", ["Sonesta ES Suites Auburn Hills"]),
                ("founder_instruction",
                 "Leave Sonesta withheld. Do not narrow the committed test "
                 "during this application. Preserve the Detroit first-party "
                 "evidence and URL for a separate guard-scope repair."),
                ("evidence_status", "PRESERVED, unmodified, still on disk"),
            ]),
        ]),
    ]))

    print("=== founder rulings 022 applied ===")
    for r in rulings:
        print("  %-34s %-26s published=%s"
              % (r["canonical_name"][:34], r["decision"],
                 r.get("published")))
    print("  exclusions now:", len(excl_doc["exclusions"]))


if __name__ == "__main__":
    run()
