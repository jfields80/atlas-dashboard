# -*- coding: utf-8 -*-
"""PTF-GENERIC-EVIDENCE-VOCABULARY-AND-GUARD-SCOPE-REPAIR-023, Phase 1.

Rebuilds the exact set of Detroit rows that are blocked by one of the THREE
generic defects this order repairs, from committed artifacts only.

THE BLOCKER IS DERIVED, NOT ASSERTED. A row is admitted here only if the
current committed rules actually block it for one of the named reasons -- the
order's list of eleven names is a claim to check, not an input to trust. Any
row blocked for some other reason, or blocked by a founder hold, is refused
entry so a rule repair cannot quietly sweep in a decision a founder made.

NO SHARED CODE IS TOUCHED IN THIS PHASE and no provider is called.
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
    detroit_ann_arbor_candidate_reconciliation_011 as R11,
    market_authority as MA)

MARKET = "detroit-ann-arbor-mi"
WORK_ORDER = "PTF-GENERIC-EVIDENCE-VOCABULARY-AND-GUARD-SCOPE-REPAIR-023"
AS_OF = "2026-08-30"

LP = R11.LP
TRIAGE = LP / "detroit_ann_arbor_attended_triage_020.json"
OUT = LP / "blocked_corpus_023.json"

EXPECTED = {"PF_VOCABULARY": 7, "NO_PETS_VOCABULARY": 2,
            "PASS3_FREEZE_GUARD": 1, "SONESTA_ALIAS_GUARD": 1}

#: Identities a founder has ruled on. A rule repair must never re-open one.
FOUNDER_RULED = {
    "the kensington hotel ann arbor", "roberts riverwalk hotel",
    "embassy suites by hilton detroit livonia novi", "the bell tower hotel",
    "hyatt place detroit livonia", "drury inn and suites",
    "radisson hotel detroit farmington hills",
}
SONESTA_FRAGMENT = "sonesta-es-suites"


def classify_blocker(row, block, pass3_keys, url):
    """Which of the three named defects, if any, is blocking this row."""
    ordinary = R11.strip_service_animal_clauses(block)
    refused = any(p.search(ordinary) for p in R11.REFUSAL_RES)
    allowed = any(p.search(ordinary) for p in R11.AFFIRMATIVE_PET_RES)
    triage = row.get("triage")

    if row["identity_key"] in pass3_keys:
        return "PASS3_FREEZE_GUARD"
    if SONESTA_FRAGMENT in (url or ""):
        return "SONESTA_ALIAS_GUARD"
    if triage == "CLEAN_PET_FRIENDLY_CANDIDATE" and not allowed:
        return "PF_VOCABULARY"
    if triage == "CLEAN_VERIFIED_NO_PETS_CANDIDATE" and not refused:
        return "NO_PETS_VOCABULARY"
    return ""


def run():
    triage = R11.load(TRIAGE)
    census = {row["identity_key"]: row for row in
              R11.load(LP / "identity_census" / ("%s.json" % MARKET))["hotels"]}
    routes = {route["hotel_ref"]["identity_key"]: route for route in
              R11.load(MA.routing_shard_path(MARKET))["routes"]}
    published = {row["identity_key"] for row in
                 R11.load(LP / ("hotel_policy_facts_%s.json" % MARKET))["hotels"]}
    excluded = {row["normalized_name"] for row in
                R11.load(MA.exclusions_shard_path(MARKET))["exclusions"]}
    pass3_keys = {c["identity_key"] for c in R11.load(
        LP / "detroit_ann_arbor_capture_pass3_founder_review_packet.json"
    )["candidates"]}

    admitted, refused_entry = [], []
    for row in triage["results"]:
        key = row["identity_key"]
        block = (row.get("block") or "").strip()
        artifact = row.get("block_artifact") or ""
        route = routes.get(key)
        url = (route or {}).get("official_property_url") or ""

        if key in published or key in excluded:
            continue
        if row.get("triage") not in ("CLEAN_PET_FRIENDLY_CANDIDATE",
                                     "CLEAN_VERIFIED_NO_PETS_CANDIDATE"):
            continue

        blocker = classify_blocker(row, block, pass3_keys, url)
        reasons = []
        if not blocker:
            reasons.append("not blocked by any of the three named defects")
        if key in FOUNDER_RULED:
            reasons.append("a founder has ruled on this identity; a RULE "
                           "REPAIR MAY NOT RE-OPEN IT")
        if not block:
            reasons.append("no evidence")
        if not artifact or not (_REPO_ROOT / artifact).is_file():
            reasons.append("no persisted artifact on disk")
        elif hashlib.sha256(
                (_REPO_ROOT / artifact).read_bytes()).hexdigest() != row.get(
                    "block_sha256"):
            reasons.append("evidence hash does not validate")
        if census.get(key) is None:
            reasons.append("no census identity")
        if route is None or not url:
            reasons.append("no identity binding")

        entry = OrderedDict([
            ("identity_key", key),
            ("canonical_name", row.get("canonical_name") or ""),
            ("triage", row.get("triage")),
            ("blocker", blocker),
            ("canonical_url", url),
            ("block_artifact", artifact),
            ("block_sha256", row.get("block_sha256") or ""),
            ("block_text", block),
        ])
        if reasons:
            entry["refused_because"] = reasons
            refused_entry.append(entry)
            continue
        admitted.append(entry)

    counts = Counter(row["blocker"] for row in admitted)
    R11.write_lf(OUT, OrderedDict([
        ("schema", "ptf-blocked-corpus/1.0"),
        ("work_order", WORK_ORDER), ("market_id", MARKET), ("as_of", AS_OF),
        ("provider_calls", 0), ("spend_usd", 0.0),
        ("note",
         "The blocker is DERIVED by running the current committed rules, not "
         "read from the order. A row blocked for any other reason, or bearing "
         "a founder ruling, is refused entry."),
        ("admitted", len(admitted)),
        ("counts", dict(counts)),
        ("expected", EXPECTED),
        ("rows", admitted),
        ("refused_entry", refused_entry),
    ]))

    print("=== Phase 1: blocked corpus rebuilt ===")
    for name in sorted(EXPECTED):
        print("   %-22s got %d  expected %d" % (name, counts.get(name, 0),
                                                EXPECTED[name]))
    print("   admitted total        :", len(admitted))
    print("   refused entry         :", len(refused_entry))
    for row in refused_entry:
        print("      %-34s %s" % (row["canonical_name"][:34],
                                  row["refused_because"]))
    if dict(counts) != EXPECTED:
        raise SystemExit("STOP: the rebuilt blocked corpus is %s, the order "
                         "expects %s" % (dict(counts), EXPECTED))
    print("wrote", OUT.name)


if __name__ == "__main__":
    run()
