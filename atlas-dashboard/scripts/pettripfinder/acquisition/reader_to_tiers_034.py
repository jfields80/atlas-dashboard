"""PTF-MILWAUKEE-READER-TO-TIERS-034 -- building the structure the schema had.

Schema 1.2 has carried ``fee_tiers[]``, ``fee_pet_schedule``, ``fee_cap`` and
``other_charges[]`` since the policy migration, and Cleveland's founder
adjudications wrote tier ladders by hand -- thirty-three published records
carry them. The automated reader never emitted one. It detected a band, said
the published vocabulary holds a single amount, and withheld the price as
SCHEMA_CANNOT_REPRESENT.

That withholding was right about ``pet_fee`` and wrong about the schema, and
twenty-nine Milwaukee rows sat in HELD_SCHEMA_CANNOT_REPRESENT because of it --
the largest single blocker in the market, ahead of refusals and insufficient
evidence combined.

WHAT THIS WORK ORDER IS NOT
---------------------------
It does not touch the schema, does not introduce 1.3, migrates nothing and
re-attests nothing. It reads what is already on disk with a reader that can now
build a ladder, and it publishes nothing.

WHAT MAKES A LADDER PUBLISHABLE
-------------------------------
Only a source that determines it completely. ``parse_stay_bands`` returns the
rungs AND every reason they may not be published, and the reader emits only
when that list is empty:

* contiguous ranges -- an overlap ("0-5 nights $75, 5+ $150" prices night five
  twice) and a gap ("1 to 6 nights ... over 7 nights" prices night seven not at
  all) are both refusals, because choosing for the source is quoting a price it
  never stated;
* one role -- a rung that reads as an addition rather than a replacement makes
  the ladder ambiguous, which is Hyatt Place Airport's "7-30 nights +
  additional cleaning fee : $200 / STAY";
* no ceiling standing in for a price, per the founder rule;
* no qualifier the tier cannot carry -- a stay-length tier has no field for
  "plus applicable taxes", for a room type, for a species or for a weight;
* no unexplained money, and no deposit or cleaning charge sharing a rung's
  amount, which would count the same dollars twice.

MEASURED, NOT ESTIMATED
-----------------------
The pre-work estimate was "roughly 26 of 29". The classification in this module
is derived from each row's own canonical evidence and the honest number is
smaller: three rows are pinned by a historical Marriott adjudication this work
order may not touch, and six state something 1.2 genuinely cannot hold.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts.pettripfinder.acquisition import premium_resolution_028 as P28   # noqa: E402
from scripts.pettripfinder.acquisition import store_integration_025 as S      # noqa: E402
from scripts.pettripfinder.brightdata import marriott_surface as MS           # noqa: E402
from scripts.pettripfinder.brightdata import policy_reading as PR             # noqa: E402
from scripts.pettripfinder.contracts import enums                             # noqa: E402
from scripts.pettripfinder.contracts import policy_schema as SCHEMA           # noqa: E402

WORK_ORDER = "PTF-MILWAUKEE-READER-TO-TIERS-034"
MARKET = "milwaukee-wi"

REPORTS = REPO / "launch_packages" / "pettripfinder" / "markets" / "reports"
STORE = REPORTS / ("%s_policy_proposals_001.json" % MARKET)
RUN_REPORT = REPORTS / "ptf_milwaukee_reader_to_tiers_034.json"
DATA = REPO / "data" / "acquisition"

HELD_SCHEMA = "HELD_SCHEMA_CANNOT_REPRESENT"
READY = "FOUNDER_REVIEW_READY"

#: The reader as it stood when this work order opened -- 033's commit. Pinned,
#: never read from HEAD: the moment this is committed HEAD becomes the new
#: reader and every before/after number would compare the change with itself.
BASELINE_COMMIT = "fe4b42fc9187cef613e0cb0404b0ed3365d9ae9f"
_READER_PATH = "atlas-dashboard/scripts/pettripfinder/brightdata/policy_reading.py"

_BASELINE_CACHE: Dict[str, object] = {}


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _rel(path: Path) -> str:
    try:
        return str(Path(path).resolve().relative_to(REPO)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


# --------------------------------------------------------------------------- #
# The reader as it was.
# --------------------------------------------------------------------------- #

def baseline_reader():
    """``policy_reading`` exactly as committed at ``BASELINE_COMMIT``."""
    if "module" in _BASELINE_CACHE:
        return _BASELINE_CACHE["module"]
    import importlib.util
    import tempfile
    source = subprocess.run(
        ["git", "show", "%s:%s" % (BASELINE_COMMIT, _READER_PATH)],
        cwd=str(REPO.parent), capture_output=True, text=True, encoding="utf-8",
        check=True).stdout
    if not source.strip():
        raise RuntimeError("the baseline reader came back empty; git show "
                           "echoes an unresolvable argument rather than "
                           "failing, so this is checked")
    holder = (Path(tempfile.mkdtemp(prefix="ptf034-"))
              / "policy_reading_baseline.py")
    holder.write_text(source, encoding="utf-8")
    spec = importlib.util.spec_from_file_location(
        "policy_reading_baseline_034", holder)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    _BASELINE_CACHE["module"] = module
    return module


def read_with(module, block: str, *, brand: str = "") -> Dict:
    """One block, read the way the store reads it for that brand."""
    if brand == "MARRIOTT":
        reading = MS.parse_policy_block(block, locator_id=WORK_ORDER)
        result = MS.to_extraction(reading, location=MARKET)
    else:
        reading = module.parse(block, strategy=WORK_ORDER)
        result = module.to_extraction(reading, location=MARKET)
    return {
        "extraction": dict(result.extraction),
        "withheld": dict(result.withheld or {}),
        "non_inferences": list(result.non_inferences),
        "flags": [dict(flag) for flag in (result.flags or ())],
        "evidence": [dict(item) for item in result.evidence],
    }


# --------------------------------------------------------------------------- #
# Phase 1 -- the twenty-nine, classified from their own evidence.
# --------------------------------------------------------------------------- #

def store_doc() -> Dict:
    return json.loads(STORE.read_text(encoding="utf-8-sig"))


def held_rows() -> List[Dict]:
    return [row for row in store_doc()["items"]
            if row["review_status"] == HELD_SCHEMA]


def block_for(row: Mapping) -> Tuple[str, str]:
    """(text, repo-relative path) of the canonical block a row rests on."""
    pointer = str((row.get("provenance") or {}).get("raw_pointer", ""))
    pointer = pointer.replace("\\", "/")
    marker = "data/acquisition/"
    if marker in pointer:
        pointer = pointer[pointer.index(marker):]
    path = REPO / pointer / "policy-block.txt"
    if not path.is_file():
        return "", _rel(path)
    return path.read_text(encoding="utf-8", errors="replace"), _rel(path)


#: Rows whose facts come from PTF-MARRIOTT-CLOSURE-022's adjudication rather
#: than from a live reading. The store applies that overlay last and
#: unconditionally, on purpose: one of those rows reads LESS from its block
#: than the adjudication concluded, and a projection that overrode it would
#: silently discard a decision a human made. A reader change cannot reach them
#: and this work order is forbidden to re-attest them.
def adjudicated_identities() -> Tuple[str, ...]:
    return tuple(sorted(S.marriott_supersessions()))


CLASSES = (
    "stay_length_band",
    "pet_count_schedule",
    "cap_or_ceiling",
    "multiple_charge_roles",
    "contradictory_basis",
    "overlapping_bands",
    "gap_between_bands",
    "room_type_condition",
    "species_condition",
    "weight_condition",
    "tax_qualifier",
    "recurring_charge_not_read",
    "frozen_by_adjudication",
    "brand_reader_not_extended",
    "other",
)

#: Why a class cannot be given to schema 1.2, for the rows that stay held.
_UNREPRESENTABLE = {
    "cap_or_ceiling": "a stated ceiling is not a price, and a rung priced by "
                      "one prices nothing",
    "multiple_charge_roles": "the surface states charges with different roles "
                             "and does not say which is the pet price",
    "contradictory_basis": "the same money is stated on two bases and per_day "
                           "is not per_night",
    "overlapping_bands": "two rungs claim the same night and the source does "
                         "not say which applies",
    "gap_between_bands": "a night falls between two rungs and the source "
                         "prices it nowhere",
    "room_type_condition": "1.2 has condition types for stay length and pet "
                           "count, and none for which room was booked",
    "species_condition": "1.2 has no condition type for the animal's species",
    "weight_condition": "1.2 has no condition type for the animal's weight",
    "tax_qualifier": "a tier carries no tax_relationship, so a rung stated "
                     "'plus applicable taxes' would publish a number the "
                     "guest does not pay",
    "frozen_by_adjudication": "the row's facts come from 022's Marriott "
                              "adjudication, which the store applies last and "
                              "this work order may not re-attest",
    "brand_reader_not_extended": "the store reads this row with the Marriott "
                                 "surface reader, and this work order extended "
                                 "the generic reader only",
    # Added by work order 035, which repaired the recurring-charge detector
    # and put a row into this cohort that 034's taxonomy had no name for.
    "recurring_charge_not_read": "the surface states a recurring charge and a "
                                 "one-off charge, and the single fee field can "
                                 "carry neither pair",
}

_PROBLEM_TO_CLASS = {
    "OVERLAPPING_BANDS": "overlapping_bands",
    "GAP_BETWEEN_BANDS": "gap_between_bands",
    "CEILING_NOT_PRICE": "cap_or_ceiling",
    "AMBIGUOUS_ROLE": "multiple_charge_roles",
    "CONTRADICTORY_BASIS": "contradictory_basis",
    "ROOM_TYPE_CONDITION": "room_type_condition",
    "SPECIES_CONDITIONED_PRICE": "species_condition",
    "WEIGHT_CONDITIONED_PRICE": "weight_condition",
    "TAX_QUALIFIER_NOT_REPRESENTABLE": "tax_qualifier",
    "UNEXPLAINED_AMOUNT": "multiple_charge_roles",
    "BAND_WITHOUT_A_PRICE": "other",
    "FEWER_THAN_TWO_BANDS": "other",
    "BANDS_STATE_ONE_PRICE": "other",
    "LADDER_DOES_NOT_START_AT_ONE": "gap_between_bands",
    "NO_BAND_STATES_ITS_UNIT": "other",
    "TOO_MANY_CANDIDATES_TO_PAIR": "other",
}

#: Shapes a ladder parse cannot see, because they are not ladders. Checked
#: against the block text so a held row still says WHY it is held.
_TEXT_CLASSES = (
    ("cap_or_ceiling", PR._BAND_CEILING_RE),
    ("room_type_condition", PR._BAND_ROOM_TYPE_RE),
    ("species_condition", PR._BAND_SPECIES_PRICED_RE),
    ("weight_condition", PR._BAND_WEIGHT_PRICED_RE),
    ("tax_qualifier", PR._BAND_TAX_RE),
)

#: The same charge stated on two bases. Deliberately allowed to cross a full
#: stop: Crowne Plaza says "the pet fee is 75.00 USD per stay" in one sentence
#: and "Pet fee per night: 75 USD" two sentences later, and a pattern that
#: stopped at the first period called that surface representable when the
#: reader -- correctly -- refuses it.
_TWO_BASES_RE = re.compile(
    r"per\s+stay[\s\S]{0,180}?per\s+night|per\s+night[\s\S]{0,180}?per\s+stay",
    re.IGNORECASE)


def classify(row: Mapping) -> Dict:
    """What this row's evidence states, and whether 1.2 can hold it."""
    identity = row["identity_key"]
    block, path = block_for(row)
    bands = PR.parse_stay_bands(block)
    schedule = PR.parse_pet_schedule(block)

    classes: List[str] = []
    if identity in adjudicated_identities():
        classes.append("frozen_by_adjudication")
    elif row.get("brand") == "MARRIOTT":
        # A live Marriott row is read by ``marriott_surface``, which is a
        # second implementation of the same job. 034 was commissioned to extend
        # ``policy_reading`` and it did; saying these rows are representable
        # would claim a promotion this work order cannot deliver.
        classes.append("brand_reader_not_extended")
    if bands.bands:
        classes.append("stay_length_band")
    if schedule.entries:
        classes.append("pet_count_schedule")
    for problem in bands.problems:
        mapped = _PROBLEM_TO_CLASS.get(problem)
        if mapped and mapped not in classes:
            classes.append(mapped)
    for name, pattern in _TEXT_CLASSES:
        if pattern.search(block) and name not in classes:
            classes.append(name)
    if _TWO_BASES_RE.search(block) and "contradictory_basis" not in classes:
        classes.append("contradictory_basis")
    reading = PR.parse(block, strategy=WORK_ORDER)
    if any(item.get("kind") == "recurring_charge_not_represented"
           for item in (reading.unrepresented or ())):
        classes.append("recurring_charge_not_read")
    if not classes:
        classes.append("other")

    blocking = [name for name in classes
                if name in _UNREPRESENTABLE]
    return {
        "identity_key": identity,
        "canonical_name": row["canonical_name"],
        "brand": row["brand"],
        "reader": (row.get("provenance") or {}).get("reader", ""),
        "block_path": path,
        "block_chars": len(block),
        "evidence": re.sub(r"\s+", " ", block).strip(),
        "classes": classes,
        "bands_read": len(bands.bands),
        "band_problems": list(bands.problems),
        "schedule_rungs": len(schedule.entries),
        "schedule_problems": list(schedule.problems),
        "representable_in_1_2": not blocking,
        "why_held": [_UNREPRESENTABLE[name] for name in blocking],
    }


def classification() -> List[Dict]:
    return [classify(row) for row in held_rows()]


def classification_summary() -> Dict:
    rows = classification()
    counts = Counter()
    for row in rows:
        for name in row["classes"]:
            counts[name] += 1
    return {
        "held_rows": len(rows),
        "by_class": {name: counts[name] for name in CLASSES if counts[name]},
        "representable_in_1_2": sum(1 for row in rows
                                    if row["representable_in_1_2"]),
        "not_representable": sum(1 for row in rows
                                 if not row["representable_in_1_2"]),
        "frozen_by_adjudication": sorted(adjudicated_identities()),
    }


# --------------------------------------------------------------------------- #
# Phase 2 -- the differential, on the held rows and on everything else.
# --------------------------------------------------------------------------- #

def held_differential() -> List[Dict]:
    old = baseline_reader()
    out: List[Dict] = []
    for row in held_rows():
        block, path = block_for(row)
        brand = row.get("brand", "")
        before = read_with(old, block, brand=brand)
        after = read_with(PR, block, brand=brand)
        pinned = row["identity_key"] in adjudicated_identities()
        tiers = after["extraction"].get("fee_tiers") or []
        schedule = after["extraction"].get("fee_pet_schedule") or {}
        issues = SCHEMA.validate_facts(
            {key: value for key, value in after["extraction"].items()
             if key in ("fee_tiers", "fee_pet_schedule", "fee_cap")})
        moves = (not pinned
                 and enums.SCHEMA_CANNOT_REPRESENT not in set(
                     after["withheld"].values())
                 and enums.SCHEMA_CANNOT_REPRESENT in set(
                     before["withheld"].values()))
        out.append({
            "identity_key": row["identity_key"],
            "canonical_name": row["canonical_name"],
            "brand": brand,
            "block_path": path,
            "evidence": re.sub(r"\s+", " ", block).strip(),
            "old_facts": before["extraction"],
            "old_withheld": before["withheld"],
            "new_facts": after["extraction"],
            "new_withheld": after["withheld"],
            "fee_tiers": tiers,
            "fee_pet_schedule": schedule,
            "fee_cap": after["extraction"].get("fee_cap"),
            "tier_structures_validate": [str(issue) for issue in issues],
            "frozen_by_adjudication": pinned,
            "review_state_changes": moves,
            "reason": ("the ladder is fully determined and is carried in "
                       "fee_tiers" if moves and tiers else
                       "the schedule is fully determined and is carried in "
                       "fee_pet_schedule" if moves and schedule else
                       "the row's facts come from 022's adjudication and a "
                       "reader change cannot reach them" if pinned else
                       "; ".join(classify(row)["why_held"])
                       or "the structure is not fully determined by the "
                          "source"),
        })
    return out


def persisted_blocks() -> List[Dict]:
    out: List[Dict] = []
    for run_id, _journal, capture_root in S.SOURCES:
        root = DATA / capture_root
        if not root.is_dir():
            continue
        for block_path in sorted(root.rglob("policy-block.txt")):
            out.append({"run_id": run_id, "path": _rel(block_path),
                        "slug": block_path.parent.parent.name})
    return out


def production_readers() -> Dict[str, str]:
    """(attempt dir -> reader, brand) as the store actually reads each row."""
    out: Dict[str, str] = {}
    for row in store_doc()["items"]:
        pointer = str((row.get("provenance") or {}).get("raw_pointer", ""))
        pointer = pointer.replace("\\", "/").rstrip("/")
        marker = "data/acquisition/"
        if marker in pointer:
            pointer = pointer[pointer.index(marker):]
        if pointer:
            out[pointer] = row.get("brand", "")
    return out


def corpus_wide_dry_run() -> Dict:
    """Every persisted block, read both ways. Nothing is written."""
    old = baseline_reader()
    brands = production_readers()
    scanned = 0
    changed: List[Dict] = []
    added_fields = Counter()
    removed_fields = Counter()
    withheld_lost = Counter()
    for item in persisted_blocks():
        block = (REPO / item["path"]).read_text(encoding="utf-8",
                                                errors="replace")
        brand = brands.get(item["path"].rsplit("/", 1)[0], "")
        scanned += 1
        before = read_with(old, block, brand=brand)
        after = read_with(PR, block, brand=brand)
        if (before["extraction"] == after["extraction"]
                and before["withheld"] == after["withheld"]):
            continue
        added = sorted(set(after["extraction"]) - set(before["extraction"]))
        removed = sorted(set(before["extraction"]) - set(after["extraction"]))
        for field in added:
            added_fields[field] += 1
        for field in removed:
            removed_fields[field] += 1
        for field in sorted(set(before["withheld"]) - set(after["withheld"])):
            withheld_lost[field] += 1
        changed.append({
            "run_id": item["run_id"],
            "slug": item["slug"],
            "path": item["path"],
            "brand": brand,
            "old_extraction": before["extraction"],
            "new_extraction": after["extraction"],
            "old_withheld": before["withheld"],
            "new_withheld": after["withheld"],
            "added_fields": added,
            "removed_fields": removed,
            "withheld_removed": sorted(set(before["withheld"])
                                       - set(after["withheld"])),
            "withheld_added": sorted(set(after["withheld"])
                                     - set(before["withheld"])),
        })
    return {
        "blocks_scanned": scanned,
        "blocks_changed": len(changed),
        "blocks_unchanged": scanned - len(changed),
        "newly_structured_fields": dict(added_fields),
        "fields_removed": dict(removed_fields),
        "withholdings_lifted": dict(withheld_lost),
        "affected": changed,
    }


# --------------------------------------------------------------------------- #
# Phases 3 and 4 -- the store, and the arithmetic over the market.
# --------------------------------------------------------------------------- #

def review_states() -> Dict[str, int]:
    return dict(Counter(row["review_status"] for row in store_doc()["items"]))


def counters() -> Dict:
    census = P28.full_census()
    doc = store_doc()
    states = Counter(row["review_status"] for row in doc["items"])
    ready = states.get(READY, 0)
    refusal = states.get("REFUSAL_FOUNDER_REVIEW", 0)
    return {
        "census_total": census["census_total"],
        "active_eligible": census["active_eligible_total"],
        "observed": census["phase11_final_states"]["OBSERVED"],
        "active_unresolved": census["phase11_final_states"]["TOUCHED_UNRESOLVED"],
        "store_rows": len(doc["items"]),
        "founder_review_ready": ready,
        "refusal_founder_review": refusal,
        "held_schema_cannot_represent": states.get(HELD_SCHEMA, 0),
        "held_insufficient_evidence": states.get("HELD_INSUFFICIENT_EVIDENCE", 0),
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
        "why": ("every block read here was persisted by an earlier run; this "
                "work order changed a reader and re-read what was on disk"),
    }


def schema_is_unchanged() -> Dict:
    """1.2 is still 1.2, and this work order did not touch its file."""
    diff = subprocess.run(
        ["git", "status", "--porcelain", "--",
         "atlas-dashboard/scripts/pettripfinder/contracts/policy_schema.py",
         "atlas-dashboard/scripts/pettripfinder/contracts/enums.py"],
        cwd=str(REPO.parent), capture_output=True, text=True).stdout.strip()
    return {
        "policy_schema_version": enums.POLICY_SCHEMA_VERSION,
        "schema_files_modified": diff,
        "tier_roles": list(enums.TIER_ROLES),
        "tier_condition_types": list(enums.TIER_CONDITION_TYPES),
    }


# --------------------------------------------------------------------------- #
# Reporting.
# --------------------------------------------------------------------------- #

def findings_not_acted_on() -> List[Dict]:
    """Defects this work order found and deliberately left alone."""
    return [
        {
            "finding": "the reader's recurring-charge detector has never fired",
            "detail": ("``_RECURRING_WORD_RE`` compiles two literal backspace "
                       "characters where it means word boundaries -- a heredoc "
                       "mangled them when the rule was written -- so the "
                       "multi-component check has never seen a recurring "
                       "charge. It is left exactly as committed."),
            "why_not_acted_on": ("repairing it reclassifies WoodSpring "
                                 "Menomonee Falls (\"a Daily Pet Fee 5 USD Per "
                                 "Pet along with Non-Refundable Pet Fee of 100 "
                                 "USD\") from SOURCE_AMBIGUOUS to "
                                 "SCHEMA_CANNOT_REPRESENT and moves it OUT of "
                                 "founder review. 034 was commissioned to turn "
                                 "safe holds into structures, not to demote a "
                                 "ready row for an unrelated reason."),
            "evidence": "scripts/pettripfinder/brightdata/policy_reading.py",
        },
        {
            "finding": "one Marriott row is readable and the Marriott reader "
                       "does not read it",
            "detail": ("Courtyard Milwaukee Downtown states \"Daily cleaning "
                       "fee of $5/day in addition to the one time "
                       "non-refundable pet fee\" and \"Non-Refundable Pet Fee "
                       "Per Stay: $50.00\". The generic reader has read that "
                       "correctly since 033; the store reads Marriott rows "
                       "with marriott_surface, which still holds it."),
            "why_not_acted_on": ("034's reader scope is policy_reading.py; "
                                 "extending a second reader implementation is "
                                 "a separate decision"),
            "evidence": "courtyard by marriott milwaukee downtown",
        },
        {
            "finding": "three held rows cannot be reached by any reader change",
            "detail": ("The store applies 022's Marriott adjudication last and "
                       "unconditionally, because one of those rows reads LESS "
                       "from its block than the adjudication concluded."),
            "why_not_acted_on": "re-attesting an adjudication is forbidden here",
            "evidence": ", ".join(adjudicated_identities()),
        },
    ]


def build_report() -> Dict:
    differential = held_differential()
    return {
        "schema": "ptf-milwaukee-reader-to-tiers/1.0",
        "work_order": WORK_ORDER,
        "market": MARKET,
        "generated_at": _now(),
        "baseline_commit": BASELINE_COMMIT,
        "classification_summary": classification_summary(),
        "classification": classification(),
        "held_differential": differential,
        "rows_that_change_review_state": [row["identity_key"] for row in differential
                                          if row["review_state_changes"]],
        "rows_that_stay_held": [
            {"identity_key": row["identity_key"], "reason": row["reason"]}
            for row in differential if not row["review_state_changes"]],
        "corpus_wide_dry_run": corpus_wide_dry_run(),
        "review_states": review_states(),
        "counters": counters(),
        "cost": cost(),
        "schema_freeze": schema_is_unchanged(),
        "findings_not_acted_on": findings_not_acted_on(),
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
    parser.add_argument("--classify", action="store_true")
    parser.add_argument("--differential", action="store_true")
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--counters", action="store_true")
    parser.add_argument("--report", action="store_true")
    args = parser.parse_args(argv)

    if args.classify:
        summary = classification_summary()
        print(json.dumps(summary, indent=2))
        for row in classification():
            print("%-46s %-52s %s"
                  % (row["identity_key"][:46], ",".join(row["classes"])[:52],
                     "REPRESENTABLE" if row["representable_in_1_2"] else "held"))
    if args.differential:
        for row in held_differential():
            print("== %s  moves=%s" % (row["identity_key"],
                                       row["review_state_changes"]))
            print("   old %s" % json.dumps(row["old_facts"], default=str)[:110])
            print("   new %s" % json.dumps(row["new_facts"], default=str)[:110])
            print("   tiers %d | schedule %s | %s"
                  % (len(row["fee_tiers"]),
                     bool(row["fee_pet_schedule"]), row["reason"][:70]))
    if args.dry_run:
        doc = corpus_wide_dry_run()
        print(json.dumps({k: v for k, v in doc.items() if k != "affected"},
                         indent=2))
    if args.counters:
        print(json.dumps(counters(), indent=2))
    if args.report:
        doc = write_report()
        print(json.dumps(doc["counters"], indent=2))
    return 0


if __name__ == "__main__":                                  # pragma: no cover
    raise SystemExit(main())
