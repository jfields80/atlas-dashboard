# -*- coding: utf-8 -*-
"""PTF-DETROIT-ANN-ARBOR-FINAL-REVIEW-AND-DEPLOY-PREP-028, Phases 1, 2 and 5.

Rebuilds the final founder packet and separates POLICY questions from
IDENTITY/ROUTING ones.

THE THREE NAMED SUBJECTS ARE A HYPOTHESIS, NOT THE ANSWER. This run sweeps
every unresolved Detroit identity that has first-party evidence on file and no
authority record, and asks which of them a founder actually has to rule on. A
packet assembled from a prompt's list is a packet that inherits that list's
mistakes.

A POLICY QUESTION NEEDS EVIDENCE. A row with no captured block is not a policy
question -- it is a routing or identity question, and putting it in front of a
founder as a pet-policy decision would be asking them to rule on nothing.

NO PROVIDER IS CALLED AND NO AUTHORITY IS WRITTEN.
"""
from __future__ import annotations

import json
import sys
from collections import Counter, OrderedDict
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder import (                                # noqa: E402
    detroit_ann_arbor_candidate_reconciliation_011 as R11,
    market_authority as MA)

MARKET = "detroit-ann-arbor-mi"
WORK_ORDER = "PTF-DETROIT-ANN-ARBOR-FINAL-REVIEW-AND-DEPLOY-PREP-028"
AS_OF = "2026-08-30"

LP = R11.LP
PACKET = LP / "detroit_ann_arbor_final_founder_packet_028.json"
HOLDS = LP / "detroit_ann_arbor_identity_holds_028.json"
BACKLOG = LP / "detroit_ann_arbor_expansion_backlog_028.json"

#: Every artifact that may carry a captured policy block for an unresolved row.
EVIDENCE_SOURCES = (
    "detroit_ann_arbor_attended_triage_020.json",
    "detroit_ann_arbor_paid_classification_027.json",
    "detroit_ann_arbor_blocked_rescore_023.json",
    "blocked_rescore_023.json",
)


def harvest_evidence():
    """identity_key -> the most recent captured block we hold for it."""
    found = {}
    for name in EVIDENCE_SOURCES:
        path = LP / name
        if not path.is_file():
            continue
        doc = R11.load(path)
        for bucket in ("results", "rows", "passed_rows", "rejected_rows"):
            value = doc.get(bucket)
            if not isinstance(value, list):
                continue
            for row in value:
                if not isinstance(row, dict):
                    continue
                key = row.get("identity_key")
                block = (row.get("block") or row.get("block_text")
                         or ((row.get("policy_reading") or {}).get("block_text")
                             if isinstance(row.get("policy_reading"), dict)
                             else "")
                         or ((row.get("reading") or {}).get("block_text")
                             if isinstance(row.get("reading"), dict) else "")
                         or "")
                if key and block.strip():
                    found[key] = OrderedDict([
                        ("block", block.strip()),
                        ("source_artifact", name),
                        ("recorded_class", row.get("class")
                         or row.get("triage") or row.get("outcome") or ""),
                    ])
    return found


def run():
    census = {row["identity_key"]: row for row in
              R11.load(LP / "identity_census" / ("%s.json" % MARKET))["hotels"]}
    routes = {route["hotel_ref"]["identity_key"]: route for route in
              R11.load(MA.routing_shard_path(MARKET))["routes"]}
    published = {row["identity_key"] for row in
                 R11.load(LP / ("hotel_policy_facts_%s.json" % MARKET))["hotels"]}
    excluded = {row["normalized_name"] for row in
                R11.load(MA.exclusions_shard_path(MARKET))["exclusions"]}
    classification = R11.load(
        LP / "detroit_ann_arbor_remaining_classification_020.json")
    by_class = {row["identity_key"]: row["classification"]
                for row in classification["rows"]}
    evidence = harvest_evidence()

    # Identities a founder has ALREADY ruled on. Re-presenting a settled
    # question as an open one wastes a founder's attention and invites a
    # different answer to the same evidence, which is how a market ends up
    # with two contradictory dispositions on one hotel.
    already_ruled = {}
    for path in sorted(LP.glob("detroit_ann_arbor_founder_rulings_0*.json")):
        for ruling in R11.load(path).get("rulings", []):
            key = ruling.get("identity_key")
            if key:
                already_ruled[key] = OrderedDict([
                    ("decision", ruling.get("decision")),
                    ("disposition", ruling.get("founder_disposition") or ""),
                    ("ruled_in", path.name),
                ])

    unresolved = sorted(set(census) - published - excluded)
    policy_questions, identity_items, settled = [], [], []

    for key in unresolved:
        crow = census[key]
        route = routes.get(key)
        url = (route or {}).get("official_property_url") or ""
        status = (route or {}).get("status") or "(none)"
        found = evidence.get(key)

        if not found:
            # No captured block: this is not a policy question.
            identity_items.append(OrderedDict([
                ("identity_key", key),
                ("canonical_name", crow.get("canonical_name") or ""),
                ("classification", by_class.get(key) or "UNRESOLVED"),
                ("route_status", status),
                ("canonical_url", url),
                ("why_not_a_policy_question",
                 "no first-party policy evidence is held for this identity; "
                 "a founder cannot rule on a policy nobody has captured"),
            ]))
            continue

        block = found["block"]
        affirmative, grade = R11.has_affirmative_pets(block)
        refused = R11.has_refusal(R11.strip_service_animal_clauses(block))
        classifier = ("REFUSED" if refused else
                      "AFFIRMATIVE (%s)" % grade if affirmative else grade)

        entry = OrderedDict([
            ("identity_key", key),
            ("canonical_name", crow.get("canonical_name") or ""),
            ("evidence", block),
            ("source_artifact", found["source_artifact"]),
            ("recorded_class", found["recorded_class"]),
            ("current_classifier_result", classifier),
            ("canonical_url", url),
            ("route_status", status),
            ("address", crow.get("address") or ""),
            ("city", crow.get("city") or ""),
        ])
        if key in already_ruled:
            entry["already_ruled"] = already_ruled[key]
            entry["needs_a_new_decision"] = False
            settled.append(entry)
        else:
            entry["needs_a_new_decision"] = True
            policy_questions.append(entry)

    R11.write_lf(PACKET, OrderedDict([
        ("schema", "ptf-detroit-final-founder-packet/1.0"),
        ("work_order", WORK_ORDER), ("market_id", MARKET), ("as_of", AS_OF),
        ("provider_calls", 0), ("spend_usd", 0.0),
        ("status", "AWAITING_FOUNDER_RULING"),
        ("note",
         "Rebuilt by sweeping every unresolved identity for held first-party "
         "evidence, not from a list of names. A row with no captured block is "
         "an identity or routing question and is in the holds file instead."),
        ("count", len(policy_questions)),
        ("questions", policy_questions),
        ("already_ruled_no_new_decision_needed", settled),
    ]))

    counts = Counter(row["classification"] for row in identity_items)
    R11.write_lf(HOLDS, OrderedDict([
        ("schema", "ptf-detroit-identity-holds/1.0"),
        ("work_order", WORK_ORDER), ("market_id", MARKET), ("as_of", AS_OF),
        ("note", "Non-policy unresolved rows. No new discovery was performed "
                 "and nothing is resolved on name similarity."),
        ("count", len(identity_items)),
        ("by_classification", dict(counts)),
        ("rows", identity_items),
    ]))

    print("=== Phase 1: final founder POLICY packet ===")
    print("   unresolved identities      :", len(unresolved))
    print("   POLICY questions (evidence):", len(policy_questions))
    for row in policy_questions:
        print("      %-40s %s" % (row["canonical_name"][:40],
                                  row["current_classifier_result"]))
    print("   already ruled, NOT re-asked:", len(settled))
    for row in settled:
        print("      %-40s %s (%s)"
              % (row["canonical_name"][:40],
                 row["already_ruled"]["decision"],
                 row["already_ruled"]["ruled_in"]))
    print()
    print("=== Phase 2: identity / routing holds ===")
    print("   rows:", len(identity_items))
    for name, n in sorted(counts.items()):
        print("      %-28s %d" % (name, n))
    print("wrote", PACKET.name, "and", HOLDS.name)


if __name__ == "__main__":
    run()
