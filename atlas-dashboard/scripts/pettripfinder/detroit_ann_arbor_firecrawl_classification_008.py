# -*- coding: utf-8 -*-
"""PTF-DETROIT-ANN-ARBOR-FIRECRAWL-PASS-008, Phase 5.

Classifies every completed attempt of the Detroit Firecrawl pass into exactly
one class, and repairs two defects this run's own runner wrote into the durable
cross-run ledger.

CLASSIFICATION IS READ FROM THE ADAPTER, NOT RE-DECIDED HERE. ``run_attempt``
already reaches VALID only after ``assess_identity`` confirms the property, and
already emits IDENTITY_MISMATCH, POLICY_NOT_FOUND, ACCESS_DENIED and
UNEXPECTED_PAGE as distinct outcomes. Re-deriving those from the artifacts
would be grading pages by a rule the rest of the system does not use.  The only
judgement added here splits the VALID rows on what the policy READER returned.

For that split the persisted ``policy-block.txt`` is re-parsed with the
project's own reader. RE-PARSE THE BLOCK, NEVER RE-LOCATE: the located block is
the observation, and re-running the locator against a document fetched at a
different moment would silently substitute a new observation for the one that
was paid for.

A VALID row whose block was located but whose ``pets_allowed`` the reader did
not resolve is HOLD -- a founder exception, not a decision for this pass. One
row is in that state because the property's own page reads "Sorry NOT other
pets are allowed"; the reader's negative pattern wants "no other pets". The
rule is NOT widened here: a reading rule must not be widened during the review
it feeds, and widening it would decide the very row the founder is being asked
to rule on.
"""
from __future__ import annotations

import json
import sys
from collections import Counter, OrderedDict
from pathlib import Path
from typing import Dict, List, Optional

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.brightdata import policy_reading as PR  # noqa: E402

MARKET = "detroit-ann-arbor-mi"
WORK_ORDER = "PTF-DETROIT-ANN-ARBOR-FIRECRAWL-PASS-008"
RUN_ID = "detroit-firecrawl-008"
AS_OF = "2026-08-29"

LP = _REPO_ROOT / "launch_packages" / "pettripfinder"
LEDGER_PATH = LP / "ptf_paid_attempt_ledger_001.json"
RUN_DIR = (_REPO_ROOT / "data" / "worker_runs" / "pettripfinder"
           / "detroit-ann-arbor-firecrawl-008")
OUT_PATH = LP / "detroit_ann_arbor_firecrawl_classification_008.json"
PACKET_PATH = LP / "detroit_ann_arbor_firecrawl_founder_exceptions_008.json"

#: The order's vocabulary.
PET_FRIENDLY = "PET_FRIENDLY"
VERIFIED_NO_PETS = "VERIFIED_NO_PETS"
POLICY_NOT_FOUND = "POLICY_NOT_FOUND"
HOLD = "HOLD"
IDENTITY_MISMATCH = "IDENTITY_MISMATCH"
UNEXPECTED_PAGE = "UNEXPECTED_PAGE"
ACQUISITION_FAILURE = "ACQUISITION_FAILURE"

CLASSES = (PET_FRIENDLY, VERIFIED_NO_PETS, POLICY_NOT_FOUND, HOLD,
           IDENTITY_MISMATCH, UNEXPECTED_PAGE, ACQUISITION_FAILURE)

#: Adapter outcome -> class, for every outcome that is not VALID. VALID is
#: split by the reader below.
OUTCOME_TO_CLASS = {
    "IDENTITY_MISMATCH": IDENTITY_MISMATCH,
    "POLICY_NOT_FOUND": POLICY_NOT_FOUND,
    "UNEXPECTED_PAGE": UNEXPECTED_PAGE,
}

#: Classes that need a founder ruling before anything may be published.
EXCEPTION_CLASSES = (HOLD, IDENTITY_MISMATCH, UNEXPECTED_PAGE,
                     ACQUISITION_FAILURE, POLICY_NOT_FOUND)

#: Classes that mean publication-grade evidence was actually acquired.
ACQUIRED_CLASSES = (PET_FRIENDLY, VERIFIED_NO_PETS)


def load(path: Path) -> Dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_lf(path: Path, doc) -> None:
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8", newline="\n")


def _rel(path: Path) -> str:
    return str(path.relative_to(_REPO_ROOT)).replace("\\", "/")


def persisted(slug: str) -> Optional[Dict]:
    """The located block and its hashes, as they were written at capture."""
    if not slug:
        return None
    directory = RUN_DIR / slug / "attempt-01"
    block = directory / "policy-block.txt"
    locator = directory / "locator.json"
    if not block.is_file() or not locator.is_file():
        return None
    rendered = directory / "rendered.html"
    return {
        "block_text": block.read_text(encoding="utf-8-sig"),
        "locator": json.loads(locator.read_text(encoding="utf-8-sig")),
        "block_path": _rel(block),
        "rendered_html": _rel(rendered) if rendered.is_file() else "",
    }


def classify(row: Dict, art: Optional[Dict]) -> Dict:
    """The class this attempt falls in, why, and the reading behind it."""
    outcome = row.get("outcome") or ""
    if outcome != "VALID":
        return {
            "class": OUTCOME_TO_CLASS.get(outcome, ACQUISITION_FAILURE),
            "why": ("the adapter returned %s; the class follows the adapter's "
                    "own outcome and is not re-derived here"
                    % (outcome or "no outcome")),
            "reading": None,
        }
    if art is None:
        # VALID means the adapter persisted artifacts. If they are gone the
        # evidence is gone with them, and a claim about the hotel cannot rest
        # on a document nobody can re-read.
        return {
            "class": ACQUISITION_FAILURE,
            "why": ("the adapter returned VALID but no persisted policy block "
                    "is on disk, so the reading is not re-checkable"),
            "reading": None,
        }
    reading = PR.parse(art["block_text"],
                       strategy=(art["locator"].get("strategy") or ""))
    allowed = reading.pets_allowed
    if allowed is True:
        cls = PET_FRIENDLY
        why = "the located block states pets are accepted"
    elif allowed is False:
        cls = VERIFIED_NO_PETS
        why = ("the located block refuses pets other than ADA service "
               "animals")
    else:
        cls = HOLD
        why = ("the block was located and persisted, but the reader did not "
               "resolve whether pets are accepted; a reading rule is not "
               "widened during the review it feeds, so this is a founder "
               "exception")
    return {
        "class": cls,
        "why": why,
        "reading": OrderedDict([
            ("pets_allowed", allowed),
            ("block_text", reading.block_text),
            ("block_sha256", art["locator"].get("block_sha256") or ""),
            ("document_sha256", art["locator"].get("document_sha256") or ""),
            ("brand_generic", bool(reading.brand_generic)),
            ("charges", [charge.to_dict() if hasattr(charge, "to_dict")
                         else dict(charge)
                         for charge in (reading.charges or [])]),
            ("service_animal_quote", reading.service_animal_quote),
            ("dogs_only_quote", reading.dogs_only_quote),
            ("block_artifact", art["block_path"]),
            ("document_artifact", art["rendered_html"]),
        ]),
    }


def repair_ledger(rows: List[Dict], verdicts: Dict[int, Dict]) -> Dict:
    """Two defects this run's runner wrote into the durable ledger.

    1. Duplicate ``attempt_id``. Two pages were fetched twice -- once in a
       smoke test and again in the full pass -- and both writes used the same
       id. BOTH ATTEMPTS STAY: the ledger records what this project PAID, and
       dropping the second row would understate the spend. Only the id is made
       unique, so the index can address them separately.
    2. ``publication_grade`` was false on every row, including rows that
       returned a located, persisted, non-generic policy block. The runner read
       identity from a key the record does not carry (``bound`` rather than
       ``confirmed``) and additionally demanded a resolved ``pets_allowed``.
       Both were wrong: the adapter reaches VALID only after identity is
       confirmed, and an unresolved boolean is a founder exception, not a
       failure to acquire evidence.
    """
    fixed_ids: List[Dict] = []
    regraded: List[Dict] = []
    seen: Counter = Counter()
    for row in rows:
        verdict = verdicts[id(row)]
        base = row["attempt_id"]
        seen[base] += 1
        if seen[base] > 1:
            new = "%s-r%d" % (base, seen[base])
            fixed_ids.append(OrderedDict([
                ("was", base),
                ("now", new),
                ("identity_key", row["identity_key"]),
                ("note", "a second PAID fetch of the same page; kept, not "
                         "merged, because the spend was real"),
            ]))
            row["attempt_id"] = new
        was = bool(row.get("publication_grade"))
        now = verdict["class"] in ACQUIRED_CLASSES
        if was != now:
            row["publication_grade"] = now
            regraded.append(OrderedDict([
                ("attempt_id", row["attempt_id"]),
                ("identity_key", row["identity_key"]),
                ("was", was),
                ("now", now),
            ]))
        art = verdict.get("_artifact")
        if art:
            row["artifact_path"] = art["block_path"]
            row["artifact_hash"] = art["locator"].get("document_sha256") or ""
    return OrderedDict([
        ("duplicate_attempt_ids_made_unique", fixed_ids),
        ("publication_grade_corrected", regraded),
    ])


def run() -> None:
    ledger = load(LEDGER_PATH)
    rows = [a for a in ledger["attempts"] if a.get("run_id") == RUN_ID]
    if not rows:
        raise SystemExit("no attempts for run %r in the ledger" % RUN_ID)

    census = {row["identity_key"]: row for row in
              load(LP / "identity_census" / ("%s.json" % MARKET))["hotels"]}

    results: List[Dict] = []
    verdicts: Dict[int, Dict] = {}
    for row in rows:
        crow = census.get(row["identity_key"]) or {}
        art = persisted(crow.get("slug") or "")
        verdict = classify(row, art)
        verdict["_artifact"] = art
        verdicts[id(row)] = verdict
        results.append(OrderedDict([
            ("attempt_id", row["attempt_id"]),
            ("identity_key", row["identity_key"]),
            ("canonical_name", row["canonical_name"]),
            ("brand", row["brand"]),
            ("canonical_url", row["canonical_url"]),
            ("adapter_outcome", row["outcome"]),
            ("class", verdict["class"]),
            ("why", verdict["why"]),
            ("reading", verdict["reading"]),
        ]))

    repairs = repair_ledger(rows, verdicts)
    ledger["count"] = len(ledger["attempts"])
    write_lf(LEDGER_PATH, ledger)
    # ``attempt_id`` may have changed, so re-stamp the classification rows from
    # the ledger and keep the two artifacts addressing the same attempts.
    for result, row in zip(results, rows):
        result["attempt_id"] = row["attempt_id"]

    counts = Counter(result["class"] for result in results)
    for cls in CLASSES:
        counts.setdefault(cls, 0)
    if sum(counts[cls] for cls in CLASSES) != len(results):
        raise SystemExit("every attempt must fall in exactly one class")

    by_brand = OrderedDict()
    for brand in sorted({result["brand"] for result in results}):
        sub = [result for result in results if result["brand"] == brand]
        by_brand[brand] = OrderedDict(
            [("attempts", len(sub))]
            + [(cls, sum(1 for result in sub if result["class"] == cls))
               for cls in CLASSES
               if any(result["class"] == cls for result in sub)])

    write_lf(OUT_PATH, OrderedDict([
        ("schema", "ptf-detroit-ann-arbor-firecrawl-classification/1.0"),
        ("work_order", WORK_ORDER),
        ("market_id", MARKET),
        ("as_of", AS_OF),
        ("run_id", RUN_ID),
        ("lane", "firecrawl"),
        ("note",
         "Every completed attempt of the Detroit Firecrawl pass in exactly one "
         "class. The class follows the ADAPTER's own outcome for everything "
         "that is not VALID; VALID is split by re-parsing the persisted policy "
         "block with the project's own reader. The block is re-parsed, never "
         "re-located. Nothing here publishes anything."),
        ("attempts", len(results)),
        ("counts", OrderedDict((cls, counts[cls]) for cls in CLASSES)),
        ("by_brand", by_brand),
        ("ledger_repairs", repairs),
        ("results", results),
    ]))

    exceptions = [result for result in results
                  if result["class"] in EXCEPTION_CLASSES]
    write_lf(PACKET_PATH, OrderedDict([
        ("schema", "ptf-detroit-ann-arbor-firecrawl-founder-exceptions/1.0"),
        ("work_order", WORK_ORDER),
        ("market_id", MARKET),
        ("as_of", AS_OF),
        ("status", "AWAITING_FOUNDER_REVIEW"),
        ("note",
         "EXCEPTIONS ONLY. The rows that acquired a clean answer are not here; "
         "they are in the classification artifact, and this order does not "
         "publish those either. Each row states what was observed and what is "
         "being asked; none of them is decided here."),
        ("count", len(exceptions)),
        ("counts", OrderedDict(
            (cls, sum(1 for result in exceptions if result["class"] == cls))
            for cls in EXCEPTION_CLASSES
            if any(result["class"] == cls for result in exceptions))),
        ("exceptions", exceptions),
    ]))

    print("attempts classified :", len(results))
    for cls in CLASSES:
        if counts[cls]:
            print("   %-20s %d" % (cls, counts[cls]))
    print("founder exceptions  :", len(exceptions))
    print("ledger repairs      : %d duplicate ids, %d regraded"
          % (len(repairs["duplicate_attempt_ids_made_unique"]),
             len(repairs["publication_grade_corrected"])))
    print("wrote", OUT_PATH.name, "and", PACKET_PATH.name)


if __name__ == "__main__":
    run()
