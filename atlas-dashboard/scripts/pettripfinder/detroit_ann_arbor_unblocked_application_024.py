# -*- coding: utf-8 -*-
"""PTF-DETROIT-ANN-ARBOR-UNBLOCKED-APPLICATION-024, Phases 1 to 6.

Applies the nine Detroit rows that the order-023 vocabulary and guard-scope
repair unblocked.

THE INVENTORY IS RE-DERIVED, NOT READ. Order 023 wrote its results down; this
run re-runs the repaired rules over the persisted bytes and re-runs the current
publication gates, because an inventory file is a claim about what the rules
said, not the rules. If the two disagree, the gates win and the row does not
publish.

ROYAL PARK AND THE SIREN ARE REFUSED ENTRY BY NAME AS WELL AS BY RULE. They are
marketing-only prose, the repair deliberately leaves them blocked, and the
order forbids publishing them. Two independent reasons, because this is the
kind of thing that goes wrong quietly.

DAXTON MUST SUPERSEDE ITS OWN HOLD, IN THE OPEN. Silence did not become
no-pets: the property's own FAQ affirmatively answered a question Pass 3 could
not. The record says so and names what it replaces.
"""
from __future__ import annotations

import hashlib
import json
import sys
from collections import Counter, OrderedDict
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder import (                                # noqa: E402
    detroit_ann_arbor_authority_application_011 as A11,
    detroit_ann_arbor_candidate_reconciliation_011 as R11,
    market_authority as MA)
from scripts.pettripfinder.contracts import enums                  # noqa: E402

MARKET = "detroit-ann-arbor-mi"
WORK_ORDER = "PTF-DETROIT-ANN-ARBOR-UNBLOCKED-APPLICATION-024"
RULE_ORDER = "PTF-GENERIC-EVIDENCE-VOCABULARY-AND-GUARD-SCOPE-REPAIR-023"
RULE_COMMIT = "e835b3f"
CAPTURE_ORDER = "PTF-DETROIT-ANN-ARBOR-FREE-ATTENDED-PASS-020"
ADOPTION_COMMIT = "295607a"
DECISION_DATE = "2026-08-30"
FOUNDER = "jfields80"

LP = A11.LP
CORPUS = LP / "blocked_corpus_023.json"
FACTS_PATH = LP / ("hotel_policy_facts_%s.json" % MARKET)
EXCLUSIONS_PATH = MA.exclusions_shard_path(MARKET)
REPORT = LP / "detroit_ann_arbor_unblocked_application_024.json"

EXPECTED_PF, EXPECTED_NP = 7, 2
DAXTON = "daxton hotel"
LEGACY_ES_URL = ("https://www.sonesta.com/sonesta-es-suites/oh/dublin/"
                 "sonesta-es-suites-dublin-columbus")
#: Refused by name as well as by rule. Belt and braces, deliberately.
FORBIDDEN = {"royal park hotel", "the siren hotel"}


def run():
    corpus = R11.load(CORPUS)
    census = {row["identity_key"]: row for row in
              R11.load(LP / "identity_census" / ("%s.json" % MARKET))["hotels"]}
    routes = {route["hotel_ref"]["identity_key"]: route for route in
              R11.load(MA.routing_shard_path(MARKET))["routes"]
              if route["status"] == "ROUTING_CONFIRMED"}
    facts_doc = R11.load(FACTS_PATH)
    excl_doc = R11.load(EXCLUSIONS_PATH)
    published = {row["identity_key"] for row in facts_doc["hotels"]}
    excluded = {row["normalized_name"] for row in excl_doc["exclusions"]}
    pass3 = R11.load(
        LP / "detroit_ann_arbor_capture_pass3_founder_review_packet.json")
    pass3_holds = {c["identity_key"] for c in pass3["candidates"]
                   if c["outcome"] == "POLICY_NOT_FOUND"}

    # ---- Phase 1: re-derive the inventory from the bytes --------------- #
    admitted, refused = [], []
    seen_identity, seen_url = set(), {}
    for row in corpus["rows"]:
        key = row["identity_key"]
        block = row["block_text"]
        url = row["canonical_url"]
        affirmative, grade = R11.has_affirmative_pets(block)
        is_refusal = R11.has_refusal(R11.strip_service_animal_clauses(block))
        verdict = ("VERIFIED_NO_PETS" if is_refusal
                   else "PET_FRIENDLY" if affirmative else "")

        reasons = []
        if key in FORBIDDEN:
            reasons.append("REFUSED BY NAME: the order forbids publishing "
                           "this property")
        if not verdict:
            reasons.append("the repaired rules derive no verdict (%s)" % grade)
        if key in published or key in excluded:
            reasons.append("already carries authority")
        artifact = row["block_artifact"]
        if not artifact or not (_REPO_ROOT / artifact).is_file():
            reasons.append("no persisted artifact")
        elif hashlib.sha256((_REPO_ROOT / artifact).read_bytes()).hexdigest() \
                != row["block_sha256"]:
            reasons.append("evidence hash does not validate")
        if census.get(key) is None or routes.get(key) is None or not url:
            reasons.append("identity binding incomplete")
        if url == LEGACY_ES_URL:
            reasons.append("cites the Dublin/Columbus legacy alias")
        if key in seen_identity or (url and url in seen_url):
            reasons.append("duplicate identity or canonical page")

        entry = OrderedDict([
            ("identity_key", key),
            ("canonical_name", row["canonical_name"]),
            ("verdict_class", verdict),
            ("rule_grade", "REFUSED" if is_refusal else grade),
            ("canonical_url", url),
            ("block_artifact", artifact),
            ("block_sha256", row["block_sha256"]),
            ("block_text", block),
        ])
        if reasons:
            entry["refused_because"] = reasons
            refused.append(entry)
            continue
        seen_identity.add(key)
        if url:
            seen_url[url] = key
        admitted.append(entry)

    got_pf = sum(1 for r in admitted if r["verdict_class"] == "PET_FRIENDLY")
    got_np = len(admitted) - got_pf
    print("=== Phase 1: inventory re-derived from the bytes ===")
    print("   CLEAN_PET_FRIENDLY     :", got_pf)
    print("   CLEAN_VERIFIED_NO_PETS :", got_np)
    print("   refused entry          :", len(refused))
    for row in refused:
        print("      %-34s %s" % (row["canonical_name"][:34],
                                  row["refused_because"]))
    if (got_pf, got_np) != (EXPECTED_PF, EXPECTED_NP):
        raise SystemExit("STOP: rebuilt %d/%d, the order expects %d/%d"
                         % (got_pf, got_np, EXPECTED_PF, EXPECTED_NP))
    for key in FORBIDDEN:
        if key in seen_identity:
            raise SystemExit("STOP: %r entered the cohort" % key)

    # ---- Phase 2: the current gates, unloosened ------------------------ #
    A11.WORK_ORDER = WORK_ORDER
    A11.DECISION_DATE = DECISION_DATE
    A11.SOURCE_GRADE = enums.GRADE_PT1_FIRST_PARTY
    A11.ARTIFACT_KIND = enums.ARTIFACT_TEXT_EXTRACT
    A11.CAPTURE_METHOD = "attended_browser"

    passed, rejected = [], []
    for entry in admitted:
        candidate = OrderedDict([
            ("identity_key", entry["identity_key"]),
            ("canonical_name", entry["canonical_name"]),
            ("class", entry["verdict_class"]),
            ("canonical_url", entry["canonical_url"]),
            ("attempt_id", "attended:%s" % entry["block_sha256"][:16]),
            ("source_pass", "%s (unblocked by %s)"
             % (CAPTURE_ORDER, RULE_ORDER)),
            ("reading", OrderedDict([
                ("block_text", entry["block_text"]),
                ("block_artifact", entry["block_artifact"]),
                ("block_sha256", entry["block_sha256"]),
                ("document_artifact", entry["block_artifact"]),
                ("document_sha256", entry["block_sha256"]),
                ("brand_generic", False),
                ("pets_allowed",
                 entry["verdict_class"] == "PET_FRIENDLY"),
            ])),
        ])
        ok, failures = R11.gate(candidate, census, routes)
        entry = dict(entry, gate_candidate=candidate)
        if ok:
            passed.append(entry)
        else:
            entry["gate_failures"] = failures
            rejected.append(entry)

    published_rows = []
    for row in facts_doc["hotels"]:
        crow = census.get(row["identity_key"]) or {}
        published_rows.append(dict(
            row, _published=True,
            canonical_name=row.get("name") or crow.get("canonical_name") or "",
            address=crow.get("address") or "",
            postal_code=crow.get("postal_code") or ""))
    candidate_rows = [dict(r, address=(census.get(r["identity_key"]) or {}).get("address") or "",
                           postal_code=(census.get(r["identity_key"]) or {}).get("postal_code") or "")
                      for r in passed]
    collisions = R11.address_collisions(candidate_rows, published_rows)
    for row in list(passed):
        if row["identity_key"] in collisions:
            passed.remove(row)
            row = dict(row)
            row["gate_failures"] = [collisions[row["identity_key"]]]
            rejected.append(row)

    print()
    print("=== Phase 2: application-time gates ===")
    print("   PASSED  :", len(passed))
    print("   REJECTED:", len(rejected))
    for row in rejected:
        print("      %-34s %s" % (row["canonical_name"][:34],
                                  row["gate_failures"]))

    # ---- Phases 3-6: apply --------------------------------------------- #
    new_facts, new_excl, applied = [], [], []
    for entry in passed:
        key = entry["identity_key"]
        census_row = census[key]
        source_url = entry["canonical_url"]
        candidate = entry["gate_candidate"]

        if entry["verdict_class"] == "PET_FRIENDLY":
            record = A11.build_publication_record(candidate, census_row,
                                                  source_url)
            approval = record.get("approval") or OrderedDict()
        else:
            record = A11.build_exclusion_record(candidate, census_row,
                                                source_url)
            approval = OrderedDict()

        provenance = OrderedDict([
            ("acquired_by_order", CAPTURE_ORDER),
            ("unblocked_by", RULE_ORDER),
            ("rule_commit", RULE_COMMIT),
            ("rule_grade", entry["rule_grade"]),
            ("capture_method", "attended_browser"),
            ("artifact_kind", enums.ARTIFACT_TEXT_EXTRACT),
            ("source_grade", enums.GRADE_PT1_FIRST_PARTY),
            ("adoption_commit", ADOPTION_COMMIT),
            ("provider_calls", 0), ("spend_usd", 0.0),
            ("shared_vocabulary_modified_by_this_order", False),
        ])

        # ---- Phase 3: Daxton supersession, stated in the open ---------- #
        if key in pass3_holds:
            provenance["supersedes"] = (
                "the Pass-3 POLICY_NOT_FOUND hold on this identity, recorded "
                "in detroit_ann_arbor_capture_pass3_founder_review_packet.json "
                "under PTF-DETROIT-ANN-ARBOR-CLAUDE-CAPTURE-PASS3-001")
            provenance["superseded_observation"] = "POLICY_NOT_FOUND (hold)"
            provenance["superseded_by_evidence_sha256"] = entry["block_sha256"]
            provenance["historical_hold_preserved"] = (
                "the Pass-3 packet is unchanged; the hold remains on the "
                "record as the observation this supersedes")
            provenance["silence_did_not_become_no_pets"] = (
                "Pass 3 found NO policy surface for this property. That "
                "silence was never converted into a refusal. The property's "
                "own FAQ was later reached at $0 and AFFIRMATIVELY states a "
                "pet policy, and it is that affirmative evidence -- not the "
                "earlier absence -- that this record publishes.")

        if entry["verdict_class"] == "PET_FRIENDLY":
            approval["operator"] = FOUNDER
            approval["approval_date"] = DECISION_DATE
            approval["authorisation"] = OrderedDict([
                ("instrument", WORK_ORDER),
                ("clause", "Apply the nine Detroit rows unblocked by %s. "
                           "Apply every passing clean row." % RULE_ORDER),
                ("scope", "gate-passing rows only"),
                ("lane", "attended_chrome"), ("spend_usd", 0.0),
            ])
            approval["capture_provenance"] = provenance
            if key in pass3_holds:
                approval["founder_disposition"] = OrderedDict([
                    ("supersedes", provenance["supersedes"]),
                    ("basis", "AFFIRMATIVE_FIRST_PARTY_EVIDENCE"),
                    ("silence_did_not_become_no_pets", True),
                ])
            record["approval"] = approval
            new_facts.append(record)
        else:
            record["notes"] = "%s Unblocked by %s: the property's own refusal " \
                "wording was not matched by the previous shared vocabulary. " \
                "Silence was never treated as a refusal." % (
                    record.get("notes", ""), RULE_ORDER)
            record["capture_provenance"] = provenance
            new_excl.append(record)

        applied.append(OrderedDict([
            ("identity_key", key),
            ("canonical_name", entry["canonical_name"]),
            ("class", entry["verdict_class"]),
            ("rule_grade", entry["rule_grade"]),
            ("supersedes_a_hold", key in pass3_holds),
        ]))

    facts_doc["hotels"] = list(facts_doc["hotels"]) + new_facts
    A11.write_lf(FACTS_PATH, facts_doc)
    if new_excl:
        excl_doc["exclusions"] = list(excl_doc["exclusions"]) + new_excl
        excl_doc["count"] = len(excl_doc["exclusions"])
        A11.write_lf(EXCLUSIONS_PATH, excl_doc)

    R11.write_lf(REPORT, OrderedDict([
        ("schema", "ptf-detroit-unblocked-application/1.0"),
        ("work_order", WORK_ORDER), ("market_id", MARKET),
        ("as_of", DECISION_DATE),
        ("provider_calls", 0), ("spend_usd", 0.0),
        ("unblocked_by", RULE_ORDER), ("rule_commit", RULE_COMMIT),
        ("inventory_rebuilt", OrderedDict([
            ("clean_pet_friendly", got_pf),
            ("clean_verified_no_pets", got_np),
            ("refused_entry", len(refused)),
        ])),
        ("applied_pet_friendly", len(new_facts)),
        ("applied_verified_no_pets", len(new_excl)),
        ("gate_rejected", len(rejected)),
        ("rejections", [OrderedDict([
            ("canonical_name", r["canonical_name"]),
            ("class", r["verdict_class"]),
            ("reason", r["gate_failures"])]) for r in rejected]),
        ("refused_entry", [OrderedDict([
            ("canonical_name", r["canonical_name"]),
            ("reason", r["refused_because"])]) for r in refused]),
        ("applied", applied),
    ]))

    print()
    print("=== Phases 5-6: applied ===")
    print("   pet-friendly applied    :", len(new_facts))
    print("   verified-no-pets applied:", len(new_excl))
    print("   pet-friendly total now  :", len(facts_doc["hotels"]))
    print("   exclusions total now    :", len(excl_doc["exclusions"]))


if __name__ == "__main__":
    run()
