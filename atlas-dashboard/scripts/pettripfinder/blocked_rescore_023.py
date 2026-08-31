# -*- coding: utf-8 -*-
"""PTF-GENERIC-EVIDENCE-VOCABULARY-AND-GUARD-SCOPE-REPAIR-023, Phases 8 and 10.

Re-scores the eleven blocked Detroit rows under the repaired rules and puts
them through the CURRENT publication gates, then prepares an application
inventory.

NO AUTHORITY IS WRITTEN. The order is explicit: prepare, do not apply.

THE CEILING IS NOT A TARGET. The order names +9 and +2 as a theoretical
maximum; whatever the gates return is the answer, and a row that stays blocked
stays blocked.
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
WORK_ORDER = "PTF-GENERIC-EVIDENCE-VOCABULARY-AND-GUARD-SCOPE-REPAIR-023"
AS_OF = "2026-08-30"

LP = R11.LP
CORPUS = LP / "blocked_corpus_023.json"
OUT = LP / "blocked_rescore_023.json"

LEGACY_ES_URL = ("https://www.sonesta.com/sonesta-es-suites/oh/dublin/"
                 "sonesta-es-suites-dublin-columbus")


def run():
    corpus = R11.load(CORPUS)
    census = {row["identity_key"]: row for row in
              R11.load(LP / "identity_census" / ("%s.json" % MARKET))["hotels"]}
    routes = {route["hotel_ref"]["identity_key"]: route for route in
              R11.load(MA.routing_shard_path(MARKET))["routes"]
              if route["status"] == "ROUTING_CONFIRMED"}
    facts_doc = R11.load(LP / ("hotel_policy_facts_%s.json" % MARKET))

    scored = []
    for row in corpus["rows"]:
        key = row["identity_key"]
        block = row["block_text"]
        affirmative, grade = R11.has_affirmative_pets(block)
        refused = R11.has_refusal(R11.strip_service_animal_clauses(block))

        if refused:
            verdict = "VERIFIED_NO_PETS"
        elif affirmative:
            verdict = "PET_FRIENDLY"
        else:
            verdict = ""

        entry = OrderedDict([
            ("identity_key", key),
            ("canonical_name", row["canonical_name"]),
            ("prior_blocker", row["blocker"]),
            ("new_rule_grade", grade if not refused else "REFUSED"),
            ("new_verdict", verdict or "UNRESOLVED"),
            ("evidence", block),
            ("canonical_url", row["canonical_url"]),
        ])

        if not verdict:
            entry["classification"] = "STILL_BLOCKED"
            entry["gate_result"] = "not run -- the rules still read no verdict"
            entry["founder_review_required"] = True
            entry["why"] = (
                "welcoming MARKETING prose with no operational term; the "
                "repair deliberately does not promote a slogan to a policy"
                if grade == "MARKETING_ONLY" else
                "the repaired rules still derive no ordinary-pet verdict")
            scored.append(entry)
            continue

        candidate = OrderedDict([
            ("identity_key", key),
            ("canonical_name", row["canonical_name"]),
            ("class", verdict),
            ("canonical_url", row["canonical_url"]),
            ("reading", OrderedDict([
                ("block_text", block),
                ("block_artifact", row["block_artifact"]),
                ("block_sha256", row["block_sha256"]),
                ("document_artifact", row["block_artifact"]),
                ("document_sha256", row["block_sha256"]),
                ("brand_generic", False),
                ("pets_allowed", verdict == "PET_FRIENDLY"),
            ])),
        ])
        ok, failures = R11.gate(candidate, census, routes)
        entry["gate_result"] = "PASS" if ok else failures

        # The Sonesta guard, now bound to the ONE legacy URL it was written
        # for rather than a shared brand slug.
        if row["canonical_url"] == LEGACY_ES_URL:
            ok, entry["gate_result"] = False, ["cites the Dublin/Columbus "
                                               "legacy alias"]

        if not ok:
            entry["classification"] = "STILL_BLOCKED"
            entry["founder_review_required"] = True
        elif verdict == "PET_FRIENDLY":
            entry["classification"] = "CLEAN_PET_FRIENDLY"
            entry["founder_review_required"] = False
        else:
            entry["classification"] = "CLEAN_VERIFIED_NO_PETS"
            entry["founder_review_required"] = False

        if row["blocker"] == "PASS3_FREEZE_GUARD" and ok:
            entry["supersedes"] = (
                "the Pass-3 POLICY_NOT_FOUND hold on this identity; the "
                "property's own FAQ now states an affirmative pet policy")
            entry["founder_review_required"] = False
        scored.append(entry)

    counts = Counter(row["classification"] for row in scored)
    clean_pf = [r for r in scored if r["classification"] == "CLEAN_PET_FRIENDLY"]
    clean_np = [r for r in scored
                if r["classification"] == "CLEAN_VERIFIED_NO_PETS"]
    blocked = [r for r in scored if r["classification"] == "STILL_BLOCKED"]

    published = len(facts_doc["hotels"])
    excluded = len(R11.load(MA.exclusions_shard_path(MARKET))["exclusions"])

    R11.write_lf(OUT, OrderedDict([
        ("schema", "ptf-blocked-rescore/1.0"),
        ("work_order", WORK_ORDER), ("market_id", MARKET), ("as_of", AS_OF),
        ("provider_calls", 0), ("spend_usd", 0.0),
        ("authority_written", False),
        ("counts", dict(counts)),
        ("application_inventory", OrderedDict([
            ("clean_pet_friendly", len(clean_pf)),
            ("clean_verified_no_pets", len(clean_np)),
            ("founder_exception", 0),
            ("still_blocked", len(blocked)),
        ])),
        ("projection_if_later_applied", OrderedDict([
            ("current_pet_friendly", published),
            ("projected_pet_friendly", published + len(clean_pf)),
            ("current_verified_no_pets", excluded),
            ("projected_verified_no_pets", excluded + len(clean_np)),
            ("current_resolved", published + excluded),
            ("projected_resolved",
             published + excluded + len(clean_pf) + len(clean_np)),
            ("note", "PROJECTION ONLY. Nothing is applied by this order."),
        ])),
        ("rows", scored),
    ]))

    print("=== Phase 8: the eleven, re-scored ===")
    for row in scored:
        print("  %-38s %-22s -> %-24s %s"
              % (row["canonical_name"][:38], row["prior_blocker"],
                 row["classification"],
                 "" if row["gate_result"] == "PASS" else
                 str(row["gate_result"])[:44]))
    print()
    print("=== Phase 10: application inventory (NOT applied) ===")
    print("  clean pet-friendly    :", len(clean_pf))
    print("  clean verified-no-pets:", len(clean_np))
    print("  still blocked         :", len(blocked))
    print("  projection: %d -> %d PF | %d -> %d no-pets | %d -> %d resolved"
          % (published, published + len(clean_pf), excluded,
             excluded + len(clean_np), published + excluded,
             published + excluded + len(clean_pf) + len(clean_np)))
    print("wrote", OUT.name)


if __name__ == "__main__":
    run()
