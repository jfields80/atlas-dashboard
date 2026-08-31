# -*- coding: utf-8 -*-
"""PTF-GENERIC-EVIDENCE-VOCABULARY-AND-GUARD-SCOPE-REPAIR-023, Phase 5.

Re-scores every committed policy-evidence row in this worktree under the
repaired vocabulary and compares it against the OLD vocabulary, across all
markets.

THE HARD REQUIREMENT IS A FLIP, NOT A COUNT. A rule repair that turns an
already-published pet-friendly hotel into a no-pets hotel, or the reverse, is
not an improvement; it is a guest-visible error that authority already carries.
This run reconstructs the OLD behaviour verbatim and refuses to pass if any
already-published verdict moves.

NO PROVIDER IS CALLED, NO AUTHORITY IS WRITTEN.
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter, OrderedDict
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder import (                                # noqa: E402
    detroit_ann_arbor_candidate_reconciliation_011 as R11)

WORK_ORDER = "PTF-GENERIC-EVIDENCE-VOCABULARY-AND-GUARD-SCOPE-REPAIR-023"
AS_OF = "2026-08-30"
LP = R11.LP
OUT = LP / "corpus_rescore_023.json"

#: The vocabulary AS COMMITTED BEFORE THIS ORDER, reproduced exactly so the
#: comparison is against real prior behaviour rather than a description of it.
OLD_AFFIRMATIVE = (
    re.compile(r"\bpets?\s+(?:are\s+)?(?:welcome|allowed|permitted|accepted)", re.I),
    re.compile(r"\bpets?\s+allowed\s*[:\-]?\s*yes", re.I),
    re.compile(r"\bwe\s+(?:accept|allow|welcome)\s+(?:up\s+to\s+)?"
               r"(?:\d+\s+)?(?:dogs?|cats?|pets?)", re.I),
    re.compile(r"\b(?:dogs?|cats?)\s+(?:and|or)\s+(?:dogs?|cats?)\s+"
               r"(?:only\s+)?(?:are\s+)?(?:welcome|allowed|permitted)", re.I),
    re.compile(r"\bpet\s+(?:fee|deposit|charge)\s+per\b", re.I),
    re.compile(r"\bmaximum\s+of\s+\d+\s+pets?\b", re.I),
    re.compile(r"\b(?:two|three|\d+)\s+(?:dogs?|cats?|pets?)\s+"
               r"(?:per\s+room|up\s+to|maximum|max)", re.I),
    re.compile(r"\bpet\s+policy\s+description\b.{0,80}?"
               r"\b(?:welcome|allowed|accept)", re.I | re.S),
    re.compile(r"\b(?:dogs?|cats?)\s+(?:are\s+)?"
               r"(?:allowed|welcome|permitted|accepted)\b", re.I),
    re.compile(r"\b\d+\s*(?:usd|dollars?|\$)?\s*(?:per\s+)?pets?\s+"
               r"(?:per\s+)?(?:night|day|stay)\b", re.I),
    re.compile(r"\bpets?\s+(?:per\s+)?(?:night|stay)\s*[:\-]?\s*\$?\s*\d", re.I),
)
OLD_REFUSAL = (
    re.compile(r"\bno\s+other\s+pets?\s+(?:are\s+)?(?:allowed|permitted)", re.I),
    re.compile(r"\bpets?\s+(?:are\s+)?not\s+(?:allowed|permitted|accepted)", re.I),
    re.compile(r"\bno\s+pets?\s+(?:are\s+)?(?:allowed|permitted)", re.I),
    re.compile(r"\bpets?\s+allowed\s*[:\-]?\s*no\b", re.I),
    re.compile(r"\bonly\s+service\s+animals?\s+(?:are\s+)?(?:permitted|allowed)", re.I),
    re.compile(r"\bsorry,?\s+no(?:t)?\s+other\s+pets?", re.I),
)


def old_verdict(block):
    ordinary = R11.strip_service_animal_clauses(block or "")
    refused = any(p.search(ordinary) for p in OLD_REFUSAL)
    allowed = any(p.search(ordinary) for p in OLD_AFFIRMATIVE)
    if refused and not allowed:
        return False
    if allowed and not refused:
        return True
    return None


def new_verdict(block):
    if R11.has_refusal(R11.strip_service_animal_clauses(block or "")):
        return False
    affirmative, _grade = R11.has_affirmative_pets(block or "")
    return True if affirmative else None


def harvest():
    """Every committed policy block in this worktree, with its market."""
    rows = []
    seen = set()
    for path in sorted(LP.glob("*.json")):
        try:
            doc = json.loads(path.read_text(encoding="utf-8-sig"))
        except Exception:
            continue
        if not isinstance(doc, dict):
            continue
        for bucket in ("results", "candidates", "passed_rows", "rows",
                       "clean_candidates", "rejected_rows"):
            value = doc.get(bucket)
            if not isinstance(value, list):
                continue
            for row in value:
                if not isinstance(row, dict):
                    continue
                block = (row.get("block")
                         or row.get("block_text")
                         or ((row.get("reading") or {}).get("block_text")
                             if isinstance(row.get("reading"), dict) else "")
                         or "")
                key = row.get("identity_key") or row.get("normalized_name")
                if not block or not key:
                    continue
                fingerprint = (key, block[:200], path.name)
                if fingerprint in seen:
                    continue
                seen.add(fingerprint)
                rows.append(OrderedDict([
                    ("identity_key", key),
                    ("market_id", row.get("market_id")
                     or doc.get("market_id") or ""),
                    ("source_artifact", path.name),
                    ("block", block),
                ]))
    return rows


def run():
    rows = harvest()

    # For each identity in authority: what evidence its record CITES, and
    # whether the shared reader is what derived its verdict. A newly ambiguous
    # row only contradicts authority if the record leaned on the reader AND
    # cites this very block. Superseded evidence and founder-derived verdicts
    # are neither -- and treating them as blockers would freeze every rule in
    # the factory forever, since old artifacts keep their old blocks.
    published, excluded, cited, reader_derived = {}, {}, {}, {}
    for path in LP.glob("hotel_policy_facts_*.json"):
        doc = json.loads(path.read_text(encoding="utf-8-sig"))
        for row in doc.get("hotels") or []:
            key = row["identity_key"]
            published[key] = path.name
            cited[key] = (row.get("evidence_quote") or "")
            disposition = (row.get("approval") or {}).get(
                "founder_disposition") or {}
            reader_derived[key] = not bool(disposition)
    for path in list((LP / "markets" / "authority").glob("*/hotel_exclusions.json")):
        doc = json.loads(path.read_text(encoding="utf-8-sig"))
        for row in doc.get("exclusions") or []:
            key = row["normalized_name"]
            excluded[key] = path.parent.name
            cited[key] = (row.get("evidence_quote") or "")
            disposition = row.get("founder_disposition") or {}
            reader_derived[key] = disposition.get(
                "derived_by_shared_reader", True) is not False

    transitions = Counter()
    flips, gained_true, gained_false, new_ambiguous = [], [], [], []
    for row in rows:
        before, after = old_verdict(row["block"]), new_verdict(row["block"])
        transitions["%s -> %s" % (before, after)] += 1
        if before == after:
            continue
        entry = OrderedDict([
            ("identity_key", row["identity_key"]),
            ("market_id", row["market_id"]),
            ("source_artifact", row["source_artifact"]),
            ("before", before), ("after", after),
            ("in_authority",
             "published" if row["identity_key"] in published
             else "excluded" if row["identity_key"] in excluded else ""),
            ("block", row["block"][:300]),
        ])
        if before is True and after is False:
            flips.append(entry)
        elif before is False and after is True:
            flips.append(entry)
        elif before is None and after is True:
            gained_true.append(entry)
        elif before is None and after is False:
            gained_false.append(entry)
        elif after is None:
            new_ambiguous.append(entry)

    def contradicts_authority(entry):
        key = entry["identity_key"]
        if not entry["in_authority"]:
            return False
        if not reader_derived.get(key, True):
            entry["why_not_a_contradiction"] = (
                "the authority record states its verdict was NOT derived by "
                "the shared reader (founder disposition), so the reader's "
                "result was never its basis")
            return False
        quote = (cited.get(key) or "").strip()
        if quote and quote[:60] not in entry["block"]:
            entry["why_not_a_contradiction"] = (
                "the authority record cites DIFFERENT evidence (%r); this "
                "block is superseded and no longer the basis of anything"
                % quote[:70])
            return False
        return True

    authority_flips = [f for f in flips if contradicts_authority(f)]
    authority_ambiguous = [a for a in new_ambiguous
                           if contradicts_authority(a)]
    benign_ambiguous = [a for a in new_ambiguous
                        if a["in_authority"] and a not in authority_ambiguous]
    by_market = Counter(
        (r["market_id"] or "(unknown)")
        for r in gained_true + gained_false + new_ambiguous + flips)

    R11.write_lf(OUT, OrderedDict([
        ("schema", "ptf-corpus-rescore/1.0"),
        ("work_order", WORK_ORDER), ("as_of", AS_OF),
        ("provider_calls", 0), ("spend_usd", 0.0),
        ("note",
         "The OLD vocabulary is reproduced verbatim in this module so the "
         "comparison is against real prior behaviour, not a description of "
         "it."),
        ("rows_checked", len(rows)),
        ("transitions", dict(transitions)),
        ("existing_verdict_flips", len(flips)),
        ("flips_touching_authority", len(authority_flips)),
        ("unresolved_to_true", len(gained_true)),
        ("unresolved_to_false", len(gained_false)),
        ("newly_ambiguous", len(new_ambiguous)),
        ("newly_ambiguous_contradicting_authority", len(authority_ambiguous)),
        ("newly_ambiguous_but_benign", benign_ambiguous),
        ("cross_market_effects", dict(by_market)),
        ("flips", flips),
        ("newly_ambiguous_rows", new_ambiguous),
        ("unresolved_to_true_rows", gained_true),
        ("unresolved_to_false_rows", gained_false),
    ]))

    print("=== Phase 5: corpus re-score ===")
    print("  rows checked                    :", len(rows))
    print("  transitions                     :", dict(transitions))
    print("  EXISTING VERDICT FLIPS          :", len(flips))
    print("  flips touching AUTHORITY        :", len(authority_flips))
    print("  unresolved -> true              :", len(gained_true))
    print("  unresolved -> false             :", len(gained_false))
    print("  newly ambiguous                 :", len(new_ambiguous))
    print("  ambiguous CONTRADICTING authority:", len(authority_ambiguous))
    print("  ambiguous but BENIGN            :", len(benign_ambiguous))
    for a in benign_ambiguous:
        print("     benign %-40s %s"
              % (a["identity_key"][:40], a.get("why_not_a_contradiction", "")[:70]))
    print("  cross-market effects            :", dict(by_market))
    for f in flips[:10]:
        print("     FLIP %-34s %s -> %s  [%s]"
              % (f["identity_key"][:34], f["before"], f["after"],
                 f["in_authority"] or "not in authority"))
    for a in authority_ambiguous[:10]:
        print("     AMBIGUOUS-IN-AUTHORITY %-30s [%s]"
              % (a["identity_key"][:30], a["in_authority"]))
    if authority_flips or authority_ambiguous:
        raise SystemExit(
            "STOP: the repair moves a verdict that authority already carries. "
            "Do not adopt until reviewed.")
    print("wrote", OUT.name)


if __name__ == "__main__":
    run()
