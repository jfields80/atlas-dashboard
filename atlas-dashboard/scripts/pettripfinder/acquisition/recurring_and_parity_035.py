"""PTF-MILWAUKEE-RECURRING-CHARGE-AND-MARRIOTT-PARITY-035 -- closing 034's two.

034 finished by reporting two defects it deliberately did not repair, because
repairing them while doing something else would have moved rows for reasons
nobody had reviewed. This work order is the review.

FINDING ONE: A RULE THAT HAD NEVER RUN
``_RECURRING_WORD_RE`` compiled two literal BACKSPACE characters (U+0008) where
it meant word boundaries -- a heredoc mangled them when the rule was written --
so it could only match a control character no scraped page contains. Proven
here rather than argued: the compiled pattern is dumped byte by byte and run
against seven surfaces that state a recurring charge, and it matches none of
them.

The rule exists because "$20 daily pet fee" is the same fact as "$20 per day"
in a form none of the charge patterns match, and a per-stay figure published
beside it understates what a stay costs. Repaired, it fires on exactly one
Milwaukee record and moves it OUT of founder review -- which is the correct
direction: that page states a $5 daily fee AND a $100 one-off, and the single
``pet_fee`` field can carry neither pair.

FINDING TWO: TWO READERS, ONE CORPUS
Marriott records are projected through ``marriott_surface``; every other brand
goes through the generic reader. Both were run over the same twenty-eight
persisted blocks. Twenty-four agree exactly. Four differ, all in the same
direction -- the generic reader reads a fact the Marriott reader does not --
and none of the four is a case where the Marriott reader is right and the
generic one wrong.

Three of those four cannot be reached by any reader change at all: the store
applies 022's Marriott adjudication last and unconditionally. The fourth is
Courtyard Milwaukee Downtown, and it is the reason this work order does not
change the Marriott reader.

WHY THE PARITY REPAIR IS REPORTED RATHER THAN MADE
Courtyard's block states a $50 per-stay pet fee and a $5-per-DAY cleaning fee.
The Marriott reader withholds both, by a guard 021/022 added for this exact
page. The generic reader reads the pet fee correctly -- and would have
published the cleaning charge as a bare "$5.00", because ``cleaning_fee`` is
one integer and the display projection has no basis to show. A seven-night
stay would be understated by thirty dollars.

So the generic reader was not simply better here, and 034's note was not
authoritative. Both readers now withhold a recurring cleaning charge for the
same stated reason, which makes their REVIEW consequence identical on this row
while the generic one additionally carries the pet fee it can prove.

The three remaining differences are weight limits, a pet count and an
allowed-flag that the Marriott reader does not parse from prose. Giving it
those means giving it the generic reader's prose parsing, and the dependency
runs the other way -- ``policy_reading`` imports ``marriott_surface``. That is
a refactor of two readers, which Phase 9 of this work order forbids doing here.
It is measured, named and left for a successor.
"""

from __future__ import annotations

import argparse
import importlib.util
import json
import re
import subprocess
import sys
import tempfile
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts.pettripfinder.acquisition import premium_resolution_028 as P28   # noqa: E402
from scripts.pettripfinder.acquisition import reader_to_tiers_034 as R34      # noqa: E402
from scripts.pettripfinder.acquisition import store_integration_025 as S      # noqa: E402
from scripts.pettripfinder.brightdata import marriott_surface as MS           # noqa: E402
from scripts.pettripfinder.brightdata import policy_reading as PR             # noqa: E402
from scripts.pettripfinder.contracts import enums                             # noqa: E402

WORK_ORDER = "PTF-MILWAUKEE-RECURRING-CHARGE-AND-MARRIOTT-PARITY-035"
MARKET = "milwaukee-wi"

REPORTS = REPO / "launch_packages" / "pettripfinder" / "markets" / "reports"
STORE = REPORTS / ("%s_policy_proposals_001.json" % MARKET)
RUN_REPORT = REPORTS / "ptf_milwaukee_recurring_and_parity_035.json"

#: The commit this work order opened on. Pinned, never read from HEAD.
BASELINE_COMMIT = "285e12bdc961e3460eff205b6c41133fcd444b52"
_READER_PATHS = {
    "policy_reading":
        "atlas-dashboard/scripts/pettripfinder/brightdata/policy_reading.py",
    "marriott_surface":
        "atlas-dashboard/scripts/pettripfinder/brightdata/marriott_surface.py",
}

#: The word boundary the recurring rule was always meant to have, and the
#: character it actually carried. Kept as data so a test can assert both.
INTENDED_RECURRING_PATTERN = r"\b(?:daily|nightly)\b"
DEFECTIVE_RECURRING_PATTERN = "\b(?:daily|nightly)\b"

EQUIVALENT = "EQUIVALENT"
MARRIOTT_BETTER = "MARRIOTT_BETTER"
GENERIC_BETTER = "GENERIC_BETTER"
DIFFERENT_BUT_BOTH_SAFE = "DIFFERENT_BUT_BOTH_SAFE"
CONFLICT_REQUIRES_HOLD = "CONFLICT_REQUIRES_HOLD"

#: Every field the parity audit compares, named rather than discovered, so a
#: field that stops being emitted cannot silently drop out of the comparison.
COMPARED_FIELDS: Tuple[str, ...] = (
    "pets_allowed", "pet_fee", "fee_currency", "fee_basis", "fee_scope",
    "fee_tiers", "fee_pet_schedule", "fee_cap", "cleaning_fee", "pet_deposit",
    "weight_limit", "combined_weight_limit", "pet_count_limit",
    "pet_count_scope", "species_allowed", "other_charges",
    "service_animal_exception",
)

_CACHE: Dict[str, object] = {}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _flat(text: str) -> str:
    return re.sub(r"\s+", " ", text or "").strip()


# --------------------------------------------------------------------------- #
# The readers as they were.
# --------------------------------------------------------------------------- #

def module_at(name: str, commit: str = BASELINE_COMMIT):
    """``policy_reading`` or ``marriott_surface`` as committed at ``commit``."""
    key = "%s@%s" % (name, commit)
    if key in _CACHE:
        return _CACHE[key]
    source = subprocess.run(
        ["git", "show", "%s:%s" % (commit, _READER_PATHS[name])],
        cwd=str(REPO.parent), capture_output=True, text=True, encoding="utf-8",
        check=True).stdout
    if not source.strip():
        raise RuntimeError("no %s at %r; git show echoes an unresolvable "
                           "argument rather than failing, so this is checked"
                           % (name, commit))
    holder = Path(tempfile.mkdtemp(prefix="ptf035-")) / ("%s_base.py" % name)
    holder.write_text(source, encoding="utf-8")
    spec = importlib.util.spec_from_file_location("%s_base_035" % name, holder)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    _CACHE[key] = module
    return module


def read_generic(module, block: str) -> Dict:
    reading = module.parse(block, strategy=WORK_ORDER)
    result = module.to_extraction(reading, location=MARKET)
    return {"extraction": dict(result.extraction),
            "withheld": dict(result.withheld or {}),
            "flags": [dict(flag) for flag in (result.flags or ())]}


def read_marriott(module, block: str) -> Dict:
    reading = module.parse_policy_block(block, locator_id=WORK_ORDER)
    result = module.to_extraction(reading, location=MARKET)
    return {"extraction": dict(result.extraction),
            "withheld": dict(result.withheld or {}),
            "flags": [dict(flag) for flag in (result.flags or ())]}


def read_as_store_does(block: str, brand: str, *, generic=PR, marriott=MS) -> Dict:
    if brand == "MARRIOTT":
        return read_marriott(marriott, block)
    return read_generic(generic, block)


# --------------------------------------------------------------------------- #
# Phase 1 -- preflight.
# --------------------------------------------------------------------------- #

def _git(*args: str) -> str:
    return subprocess.run(["git", *args], cwd=str(REPO.parent),
                          capture_output=True, text=True).stdout.strip()


def preflight() -> Dict:
    doc = R34.store_doc()
    states = Counter(row["review_status"] for row in doc["items"])
    porcelain = [line for line in _git("status", "--porcelain").splitlines()
                 if line.strip()]
    return {
        "checked_at": _now(),
        "branch": _git("rev-parse", "--abbrev-ref", "HEAD"),
        "head": _git("rev-parse", "HEAD"),
        "expected_head": BASELINE_COMMIT,
        "origin_head": _git("rev-parse", "origin/grok/ptf-milwaukee-market-001"),
        "working_tree_entries": porcelain,
        "policy_schema_version": doc["policy_schema_version"],
        "store_rows": len(doc["items"]),
        "review_states": dict(states),
        "authority_written": bool(doc.get("authority_written")),
        "published": sum(1 for row in doc["items"] if row.get("published")),
    }


# --------------------------------------------------------------------------- #
# Phase 2 -- the defect, proven rather than argued.
# --------------------------------------------------------------------------- #

def recurring_defect() -> Dict:
    """What the pattern was, what it is, and what each one can match."""
    defective = re.compile(DEFECTIVE_RECURRING_PATTERN, re.IGNORECASE)
    intended = re.compile(INTENDED_RECURRING_PATTERN, re.IGNORECASE)
    probe = "A $20 daily pet fee applies."
    return {
        "source_representation_at_baseline": repr(DEFECTIVE_RECURRING_PATTERN),
        "compiled_bytes_at_baseline": [hex(ord(c))
                                       for c in DEFECTIVE_RECURRING_PATTERN],
        "intended_semantics": ("the words 'daily' and 'nightly' as whole "
                               "words: " + INTENDED_RECURRING_PATTERN),
        "actual_semantics": ("the words 'daily' and 'nightly' flanked by "
                             "literal BACKSPACE characters (U+0008), which no "
                             "scraped page contains"),
        "defective_matches_ordinary_text": bool(defective.search(probe)),
        "intended_matches_ordinary_text": bool(intended.search(probe)),
        "installed_pattern": PR._RECURRING_WORD_RE.pattern,
        "installed_is_intended":
            PR._RECURRING_WORD_RE.pattern == INTENDED_RECURRING_PATTERN,
        "guard_unchanged": ("the search still fires only where NO charge "
                            "already carries a nightly or daily basis and the "
                            "word stands in pet context"),
    }


# --------------------------------------------------------------------------- #
# Phase 2 / 3 -- the fixed corpus.
# --------------------------------------------------------------------------- #

RECURRING_CASES: Tuple[Tuple[str, str, str], ...] = (
    ("R1-daily-plus-one-time",
     "Dogs Allowed Only, 2 Pets per room, max 50 pounds. Daily Pet Fee 5 USD "
     "Per Pet along with Non-Refundable Pet Fee of 100 USD required at "
     "check-in.",
     "a recurring charge and a one-off charge; the single fee field can carry "
     "neither pair, so the fee is withheld"),
    ("R2-per-night-plus-per-stay",
     "Pets welcome. A $10 per night pet fee and a $75 per stay pet fee apply.",
     "two charges already carrying their own bases; the recurring rule is "
     "guarded off and the ambiguity is reported as it always was"),
    ("R3-daily-cleaning-plus-one-time-pet-fee",
     "Pet Policy Pets Welcome Daily cleaning fee of $5/ day in addition to "
     "the one time non-refundable pet fee Non-Refundable Pet Fee Per Stay: "
     "$50.00 Maximum Number of Pets in Room: 2",
     "the cleaning charge is recurring and is withheld with a reason; the "
     "per-stay pet fee is stated plainly and survives"),
    ("R4-recurring-fee-with-a-cap",
     "Pets welcome. A $20 daily pet fee applies, up to a maximum of $100 per "
     "stay.",
     "the ceiling stays a ceiling and no price is invented from it"),
    ("R5-one-time-only",
     "Pets welcome. A $150 non-refundable pet fee per stay applies.",
     "a one-off charge must not become recurring"),
    ("R6-unrelated-recurring-charges",
     "Pets allowed. Self-parking is $35 daily. A nightly resort fee of $29 "
     "applies.",
     "recurring charges that are not a pet's cannot become pet charges"),
    ("R7-recurring-already-represented",
     "Pets welcome. The pet fee is 35.00 USD per day.",
     "per_day is per_day, is not per_night, and needs no withholding"),
)


def recurring_corpus() -> List[Dict]:
    old = module_at("policy_reading")
    rows = []
    for case_id, text, expectation in RECURRING_CASES:
        before = read_generic(old, text)
        after = read_generic(PR, text)
        rows.append({
            "case_id": case_id,
            "text": text,
            "expectation": expectation,
            "recurring_word_seen_before": bool(
                old._RECURRING_WORD_RE.search(text)),
            "recurring_word_seen_after": bool(PR._RECURRING_WORD_RE.search(text)),
            "old_facts": before["extraction"],
            "old_withheld": before["withheld"],
            "new_facts": after["extraction"],
            "new_withheld": after["withheld"],
            "differs": (before["extraction"] != after["extraction"]
                        or before["withheld"] != after["withheld"]),
        })
    return rows


# --------------------------------------------------------------------------- #
# Phases 4 and 5 -- what the repair does to the market.
# --------------------------------------------------------------------------- #

def _review_state_for(extraction: Mapping, withheld: Mapping,
                      refusal: bool) -> str:
    """The state the proposal builder would give this reading.

    A local copy of the builder's ordering, used only to say what a row WOULD
    become before anything is written. The store itself is still the authority
    and is rebuilt through its own code path.
    """
    reasons = set(withheld.values())
    if enums.SCHEMA_CANNOT_REPRESENT in reasons:
        return "HELD_SCHEMA_CANNOT_REPRESENT"
    if refusal:
        return "REFUSAL_FOUNDER_REVIEW"
    if enums.ARTIFACT_INSUFFICIENT in reasons or not extraction:
        return "HELD_INSUFFICIENT_EVIDENCE"
    substantive = set(extraction) - {"pets_allowed", "pets_allowed_quote",
                                     "service_animal_exception",
                                     "service_animal_statement"}
    if not substantive:
        return "HELD_INSUFFICIENT_EVIDENCE"
    return "FOUNDER_REVIEW_READY"


def differential() -> List[Dict]:
    """Old reader against new, over every persisted block, as the store reads it."""
    old_generic = module_at("policy_reading")
    old_marriott = module_at("marriott_surface")
    rows: List[Dict] = []
    for row in R34.store_doc()["items"]:
        block, path = R34.block_for(row)
        if not block:
            continue
        brand = row.get("brand", "")
        before = read_as_store_does(block, brand, generic=old_generic,
                                    marriott=old_marriott)
        after = read_as_store_does(block, brand)
        if (before["extraction"] == after["extraction"]
                and before["withheld"] == after["withheld"]):
            continue
        refusal = after["extraction"].get("pets_allowed") is False
        rows.append({
            "identity_key": row["identity_key"],
            "brand": brand,
            "reader": (row.get("provenance") or {}).get("reader", ""),
            "block_path": path,
            "evidence": _flat(block)[:400],
            "old_facts": before["extraction"],
            "old_withheld": before["withheld"],
            "new_facts": after["extraction"],
            "new_withheld": after["withheld"],
            "facts_added": sorted(set(after["extraction"])
                                  - set(before["extraction"])),
            "facts_removed": sorted(set(before["extraction"])
                                    - set(after["extraction"])),
            "withheld_added": sorted(set(after["withheld"])
                                     - set(before["withheld"])),
            "withheld_removed": sorted(set(before["withheld"])
                                       - set(after["withheld"])),
            "review_state_before": row["review_status"],
            "review_state_after": _review_state_for(after["extraction"],
                                                    after["withheld"], refusal),
        })
    return rows


def differential_summary() -> Dict:
    rows = differential()
    scanned = sum(1 for row in R34.store_doc()["items"] if R34.block_for(row)[0])
    added = Counter()
    removed = Counter()
    for row in rows:
        for field in row["facts_added"]:
            added[field] += 1
        for field in row["facts_removed"]:
            removed[field] += 1
    return {
        "blocks_scanned": scanned,
        "rows_changed": len(rows),
        "rows_unchanged": scanned - len(rows),
        "ready_to_held": [row["identity_key"] for row in rows
                          if row["review_state_before"] == "FOUNDER_REVIEW_READY"
                          and row["review_state_after"] != "FOUNDER_REVIEW_READY"],
        "held_to_ready": [row["identity_key"] for row in rows
                          if row["review_state_before"] != "FOUNDER_REVIEW_READY"
                          and row["review_state_after"] == "FOUNDER_REVIEW_READY"],
        "facts_added": dict(added),
        "facts_removed": dict(removed),
        "identities": [row["identity_key"] for row in rows],
        "rows": rows,
    }


# --------------------------------------------------------------------------- #
# Phases 6 and 7 -- the parity audit.
# --------------------------------------------------------------------------- #

def _classify(marriott: Mapping, generic: Mapping) -> Tuple[str, List[Dict]]:
    """One classification per row, decided by field, never by preference."""
    differences: List[Dict] = []
    conflict = False
    marriott_only = generic_only = 0
    for field in COMPARED_FIELDS:
        left = marriott["extraction"].get(field)
        right = generic["extraction"].get(field)
        left_withheld = marriott["withheld"].get(field)
        right_withheld = generic["withheld"].get(field)
        if left == right and left_withheld == right_withheld:
            continue
        kind = ""
        if left is not None and right is not None and left != right:
            # Both readers assert the field and they disagree about its VALUE.
            # Nothing mechanical can prefer one, and a guess is a published
            # price nobody stated.
            kind = "VALUE_CONFLICT"
            conflict = True
        elif left is not None and right is None:
            kind = "MARRIOTT_ONLY"
            marriott_only += 1
        elif right is not None and left is None:
            kind = "GENERIC_ONLY"
            generic_only += 1
        else:
            kind = "WITHHOLDING_DIFFERS"
        differences.append({"field": field, "kind": kind,
                            "marriott": left, "generic": right,
                            "marriott_withheld": left_withheld,
                            "generic_withheld": right_withheld})
    if not differences:
        return EQUIVALENT, differences
    if conflict:
        return CONFLICT_REQUIRES_HOLD, differences
    if generic_only and marriott_only:
        return DIFFERENT_BUT_BOTH_SAFE, differences
    if generic_only:
        return GENERIC_BETTER, differences
    if marriott_only:
        return MARRIOTT_BETTER, differences
    return DIFFERENT_BUT_BOTH_SAFE, differences


def marriott_parity() -> List[Dict]:
    """Both readers over the same persisted block. Read-only by construction."""
    rows: List[Dict] = []
    pinned = set(R34.adjudicated_identities())
    for row in R34.store_doc()["items"]:
        if row.get("brand") != "MARRIOTT":
            continue
        block, path = R34.block_for(row)
        if not block:
            rows.append({"identity_key": row["identity_key"],
                         "classification": "NO_PERSISTED_BLOCK",
                         "block_path": path})
            continue
        marriott = read_marriott(MS, block)
        generic = read_generic(PR, block)
        classification, differences = _classify(marriott, generic)
        refusal_m = marriott["extraction"].get("pets_allowed") is False
        refusal_g = generic["extraction"].get("pets_allowed") is False
        rows.append({
            "identity_key": row["identity_key"],
            "block_path": path,
            "evidence": _flat(block)[:400],
            "store_review_state": row["review_status"],
            "frozen_by_adjudication": row["identity_key"] in pinned,
            "marriott_facts": marriott["extraction"],
            "marriott_withheld": marriott["withheld"],
            "generic_facts": generic["extraction"],
            "generic_withheld": generic["withheld"],
            "differences": differences,
            "classification": classification,
            "review_consequence_marriott": _review_state_for(
                marriott["extraction"], marriott["withheld"], refusal_m),
            "review_consequence_generic": _review_state_for(
                generic["extraction"], generic["withheld"], refusal_g),
        })
    return rows


def parity_summary() -> Dict:
    rows = marriott_parity()
    counts = Counter(row["classification"] for row in rows)
    return {
        "rows_compared": len(rows),
        "by_classification": dict(counts),
        "identities_by_classification": {
            name: [row["identity_key"] for row in rows
                   if row["classification"] == name]
            for name in sorted(counts)},
        "same_review_consequence": sum(
            1 for row in rows
            if row.get("review_consequence_marriott")
            == row.get("review_consequence_generic")),
        "unreachable_by_any_reader_change": sorted(
            row["identity_key"] for row in rows
            if row.get("frozen_by_adjudication")),
    }


# --------------------------------------------------------------------------- #
# Phase 8 -- the one row 034 named.
# --------------------------------------------------------------------------- #

COURTYARD = "courtyard by marriott milwaukee downtown"


def courtyard_case() -> Dict:
    """034's finding, re-derived from the persisted evidence rather than trusted."""
    row = next(r for r in R34.store_doc()["items"]
               if r["identity_key"] == COURTYARD)
    block, path = R34.block_for(row)
    old_generic = module_at("policy_reading")
    old_marriott = module_at("marriott_surface")
    return {
        "identity_key": COURTYARD,
        "block_path": path,
        "evidence": _flat(block),
        "source_states": [
            "a one-time non-refundable pet fee of $50.00 per stay",
            "a cleaning fee of $5 per DAY",
            "a maximum of 2 pets in a room",
        ],
        "marriott_before": read_marriott(old_marriott, block),
        "generic_before": read_generic(old_generic, block),
        "marriott_after": read_marriott(MS, block),
        "generic_after": read_generic(PR, block),
        "store_review_state": row["review_status"],
        "finding": (
            "034's note is half right and was not authoritative. The generic "
            "reader IS correct about the pet fee -- $50.00 per stay is stated "
            "in the property's own structured row and the Marriott reader "
            "withholds it. But the generic reader was ALSO about to publish "
            "the $5-per-day cleaning charge as a bare '$5.00': cleaning_fee is "
            "one integer, the display projection has no basis to render, and a "
            "seven-night stay would have been understated by thirty dollars. "
            "Both readers now withhold a recurring cleaning charge with a "
            "reason, so this row stays held either way -- and the generic "
            "reading carries the pet fee it can actually prove."),
    }


# --------------------------------------------------------------------------- #
# Phases 12 to 15 -- the store, the states and the counters.
# --------------------------------------------------------------------------- #

def store_dry_run() -> Dict:
    """What the projection WOULD do. Writes nothing."""
    return S.integrate(write=False)


def review_states() -> Dict[str, int]:
    return dict(Counter(row["review_status"]
                        for row in R34.store_doc()["items"]))


def counters() -> Dict:
    census = P28.full_census()
    doc = R34.store_doc()
    states = Counter(row["review_status"] for row in doc["items"])
    ready = states.get("FOUNDER_REVIEW_READY", 0)
    refusal = states.get("REFUSAL_FOUNDER_REVIEW", 0)
    return {
        "census_total": census["census_total"],
        "active_eligible": census["active_eligible_total"],
        "observed": census["phase11_final_states"]["OBSERVED"],
        "active_unresolved": census["phase11_final_states"]["TOUCHED_UNRESOLVED"],
        "store_rows": len(doc["items"]),
        "founder_review_ready": ready,
        "refusal_founder_review": refusal,
        "held_schema_cannot_represent": states.get(
            "HELD_SCHEMA_CANNOT_REPRESENT", 0),
        "held_insufficient_evidence": states.get(
            "HELD_INSUFFICIENT_EVIDENCE", 0),
        "current_state_conflict": states.get("CURRENT_STATE_CONFLICT", 0),
        "held_semantic_review": states.get("HELD_SEMANTIC_REVIEW", 0),
        "first_publication_candidates": ready + refusal,
        "published": sum(1 for row in doc["items"] if row.get("published")),
        "sum_of_final_states": census["phase11_sum"],
    }


def cost() -> Dict:
    return {
        "provider_calls": 0,
        "firecrawl_calls": 0,
        "browser_api_calls": 0,
        "web_unlocker_calls": 0,
        "brightdata_spend_usd": 0.0,
        "why": "two readers were run over blocks that were already on disk",
    }


# --------------------------------------------------------------------------- #
# Phase 19 -- the readiness question, answered from the measurements.
# --------------------------------------------------------------------------- #

def publication_readiness() -> Dict:
    doc = R34.store_doc()
    ready = [row for row in doc["items"]
             if row["review_status"] == "FOUNDER_REVIEW_READY"]
    priced = [row for row in ready
              if (row["proposed_facts"] or {}).get("pet_fee") is not None
              or (row["proposed_facts"] or {}).get("fee_tiers")
              or (row["proposed_facts"] or {}).get("fee_pet_schedule")]
    # A READY row may not carry a fee AND a reason it could not be represented.
    contradictory = [row["identity_key"] for row in ready
                     if enums.SCHEMA_CANNOT_REPRESENT
                     in set((row["withheld_fields"] or {}).values())]
    # Nor a recurring charge published as a flat amount.
    flat_recurring = []
    for row in ready:
        facts = row["proposed_facts"] or {}
        if facts.get("cleaning_fee") is None:
            continue
        block, _ = R34.block_for(row)
        if re.search(r"\b(?:daily|nightly)\b|/\s*(?:day|night)\b"
                     r"|per\s+(?:day|night)\b", block or "", re.IGNORECASE):
            flat_recurring.append(row["identity_key"])
    blockers = []
    if contradictory:
        blockers.append("a READY row carries SCHEMA_CANNOT_REPRESENT: %s"
                        % ", ".join(contradictory))
    if flat_recurring:
        blockers.append("a READY row publishes a flat cleaning fee for a "
                        "recurring charge: %s" % ", ".join(flat_recurring))
    counts = counters()
    return {
        "known_pricing_defect_remaining": bool(blockers),
        "blockers": blockers,
        "ready_rows": len(ready),
        "ready_rows_carrying_a_price": len(priced),
        "first_publication_candidates":
            counts["first_publication_candidates"],
        "verdict": ("READY_FOR_FIRST_PUBLICATION" if not blockers
                    else "NOT_READY_FOR_FIRST_PUBLICATION"),
        "reason": ("no READY row carries a fee the vocabulary could not "
                   "represent, no READY row publishes a recurring charge as a "
                   "flat amount, and every remaining hold names its reason"
                   if not blockers else "; ".join(blockers)),
        "scope_note": ("this is an assessment of the CURRENT-STATE STORE. It "
                       "says nothing about whether the founder has reviewed "
                       "any row: published is 0, founder_approved is 0 and no "
                       "authority file exists for this market."),
    }


# --------------------------------------------------------------------------- #
# Phase 18 -- freezes.
# --------------------------------------------------------------------------- #

FROZEN_PATHS: Tuple[str, ...] = (
    "atlas-dashboard/scripts/pettripfinder/contracts/policy_schema.py",
    "atlas-dashboard/scripts/pettripfinder/contracts/enums.py",
    "atlas-dashboard/scripts/pettripfinder/acquisition/routes.json",
    "atlas-dashboard/scripts/pettripfinder/acquisition/registry.py",
    "atlas-dashboard/scripts/pettripfinder/acquisition/router.py",
    "atlas-dashboard/scripts/pettripfinder/acquisition/providers.py",
    "atlas-dashboard/scripts/pettripfinder/acquisition/readers.py",
    "atlas-dashboard/scripts/pettripfinder/acquisition/source_discovery.py",
    "atlas-dashboard/scripts/pettripfinder/acquisition/source_selection.py",
    "atlas-dashboard/scripts/pettripfinder/brightdata/policy_surface.py",
    "atlas-dashboard/scripts/pettripfinder/brightdata/policy_locator.py",
    "atlas-dashboard/launch_packages/pettripfinder/identity_census",
    "atlas-dashboard/launch_packages/pettripfinder/milwaukee_final_partition_001.json",
)


def freezes() -> Dict:
    out = {}
    for path in FROZEN_PATHS:
        out[path] = _git("status", "--porcelain", "--", path) or "clean"
    return {
        "policy_schema_version": enums.POLICY_SCHEMA_VERSION,
        "paths": out,
        "all_clean": all(value == "clean" for value in out.values()),
        "changed_by_035": [
            "scripts/pettripfinder/brightdata/policy_reading.py "
            "(recurring-word repair; recurring cleaning charge withheld)",
            "scripts/pettripfinder/brightdata/marriott_surface.py "
            "(the same recurring-cleaning rule, changing no current row)",
        ],
    }


# --------------------------------------------------------------------------- #
# Reporting.
# --------------------------------------------------------------------------- #

def build_report() -> Dict:
    return {
        "schema": "ptf-milwaukee-recurring-and-parity/1.0",
        "work_order": WORK_ORDER,
        "market": MARKET,
        "generated_at": _now(),
        "baseline_commit": BASELINE_COMMIT,
        "preflight": preflight(),
        "recurring_defect": recurring_defect(),
        "recurring_corpus": recurring_corpus(),
        "differential": differential_summary(),
        "marriott_parity": parity_summary(),
        "marriott_parity_rows": marriott_parity(),
        "courtyard": courtyard_case(),
        "marriott_repair": {
            "code_changed": True,
            "what": ("marriott_surface withholds a RECURRING cleaning charge "
                     "instead of publishing it as a flat amount -- the same "
                     "rule the generic reader now applies"),
            "what_was_not_done": (
                "the three remaining GENERIC_BETTER rows need the generic "
                "reader's PROSE parsing inside marriott_surface, and the "
                "dependency runs the other way: policy_reading imports "
                "marriott_surface. Achieving that parity means extracting a "
                "shared parsing component from two readers, which Phase 9 "
                "forbids doing here. Measured, named, and left."),
            "rows_changed_by_the_marriott_edit": 0,
        },
        "review_states": review_states(),
        "counters": counters(),
        "cost": cost(),
        "freezes": freezes(),
        "publication_readiness": publication_readiness(),
        "authority_written": False,
        "published": 0,
    }


def write_report() -> Dict:
    doc = build_report()
    RUN_REPORT.write_text(json.dumps(doc, indent=2, ensure_ascii=False),
                          encoding="utf-8")
    return doc


def main(argv: Optional[Sequence[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=WORK_ORDER)
    parser.add_argument("--preflight", action="store_true")
    parser.add_argument("--defect", action="store_true")
    parser.add_argument("--corpus", action="store_true")
    parser.add_argument("--differential", action="store_true")
    parser.add_argument("--parity", action="store_true")
    parser.add_argument("--courtyard", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--counters", action="store_true")
    parser.add_argument("--report", action="store_true")
    args = parser.parse_args(argv)

    if args.preflight:
        print(json.dumps(preflight(), indent=2))
    if args.defect:
        print(json.dumps(recurring_defect(), indent=2))
    if args.corpus:
        for row in recurring_corpus():
            print("%-40s changed=%-5s seen %s -> %s"
                  % (row["case_id"], row["differs"],
                     row["recurring_word_seen_before"],
                     row["recurring_word_seen_after"]))
            print("   old %s | %s" % (json.dumps(row["old_facts"], default=str)[:90],
                                      json.dumps(row["old_withheld"])))
            print("   new %s | %s" % (json.dumps(row["new_facts"], default=str)[:90],
                                      json.dumps(row["new_withheld"])))
    if args.differential:
        summary = differential_summary()
        print(json.dumps({k: v for k, v in summary.items() if k != "rows"},
                         indent=2))
        for row in summary["rows"]:
            print("== %s  %s -> %s" % (row["identity_key"],
                                       row["review_state_before"],
                                       row["review_state_after"]))
    if args.parity:
        print(json.dumps(parity_summary(), indent=2))
    if args.courtyard:
        case = courtyard_case()
        print(json.dumps({k: v for k, v in case.items()
                          if k != "evidence"}, indent=2, default=str))
        print("EVIDENCE: %s" % case["evidence"])
    if args.dry_run:
        result = store_dry_run()
        print(json.dumps({k: v for k, v in result.items()
                          if k not in ("run_classification",)}, indent=2,
                         default=str)[:4000])
    if args.counters:
        print(json.dumps(counters(), indent=2))
    if args.report:
        doc = write_report()
        print(json.dumps(doc["counters"], indent=2))
        print(json.dumps(doc["publication_readiness"], indent=2))
    return 0


if __name__ == "__main__":                                  # pragma: no cover
    raise SystemExit(main())
