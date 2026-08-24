"""PTF-CHOICE-READER-AND-ROUTE-CLOSURE-005 -- re-derive from persisted artifacts.

PTF-FIRECRAWL-CHOICE-VALIDATION-004 held one record because it contradicted
itself: Country Inn & Suites by Radisson, Milwaukee Airport came back with
``pets_allowed: false`` alongside a 40 lb weight limit and a one-pet count. A
property that refuses pets cannot also cap them.

This module re-reads that record, and every other Choice record from that run,
from the artifacts already on disk. No request is made, so no credit is spent
and nothing about the source can drift between the two readings: the only thing
that changed is the reader.

What the source actually says
-----------------------------
The bounded block the locator chose is, verbatim:

    Pets Allowed: No, only Service animals are permitted. Pet limit 1 Pet Per
    Room with Max 40 Pounds for stays 1-3 night only.

and the wider page carries, in its "Hotel alerts" section, all three of:

    Pet fee 25 USD per pet per day.
    This property does not allow pets / is not pet friendly.
    Pets Allowed: No, only Service animals are permitted. Pet limit 1 Pet Per
    Room with Max 40 Pounds for stays 1-3 night only.

That is a first-party contradiction, not a parsing artifact. The property's own
page states a pet fee, a pet limit and a pet weight cap, and also states that it
does not allow pets. The corpus rule for that is to publish neither reading, so
the record resolves to SOURCE_CONTRADICTORY rather than to a tidy answer.

The reader defect was real and separate
---------------------------------------
The contradiction detector already existed, but it only fired on a refusal
standing next to an explicit acceptance. A refusal standing next to ordinary-pet
TERMS was emitted silently as both. That is the general Choice pattern this
work order fixes, and it is fixed in ``policy_reading.parse`` for every brand
rather than special-cased for a property name.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Optional

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts.pettripfinder.brightdata import policy_reading as PR     # noqa: E402

WORK_ORDER = "PTF-CHOICE-READER-AND-ROUTE-CLOSURE-005"
MARKET = "milwaukee-wi"
PKG = REPO / "launch_packages" / "pettripfinder"
REPORTS = PKG / "markets" / "reports"
RUN_DIR = (REPO / "data" / "acquisition" / "firecrawl-choice-validation-004"
           / "choice-validation-004")
VALIDATION_REPORT = REPORTS / "ptf_firecrawl_choice_validation_004.json"

#: The record this work order was opened for.
HELD_KEY = "country inn and suites by radisson milwaukee airport wi"


def _slug_dirs() -> Dict[str, Path]:
    """Every persisted capture directory from the 004 run, by slug."""
    scrape = RUN_DIR / "scrape"
    if not scrape.is_dir():
        return {}
    return {d.name: d for d in sorted(scrape.iterdir()) if d.is_dir()}


def _latest_block(slug_dir: Path) -> Optional[Dict]:
    """The bounded policy block from the last attempt that produced one."""
    for attempt in sorted(slug_dir.glob("attempt-*"), reverse=True):
        path = attempt / "policy-block.txt"
        if not path.is_file():
            continue
        text = path.read_text(encoding="utf-8", errors="replace").strip()
        if text:
            return {"attempt": attempt.name, "block_text": text,
                    "path": str(path.relative_to(REPO))}
    return None


def _page_text(slug_dir: Path) -> str:
    for attempt in sorted(slug_dir.glob("attempt-*"), reverse=True):
        path = attempt / "page-text.txt"
        if path.is_file():
            text = path.read_text(encoding="utf-8", errors="replace")
            if text.strip():
                return text
    return ""


#: Wordings that cannot all be true of the same property at the same time.
_ACCEPTS_RE = re.compile(r"pet\s+fee|pet\s+charge|pet\s+limit|"
                         r"pets?\s+allowed\s*\.|pets?\s+(?:are\s+)?welcome",
                         re.IGNORECASE)
_REFUSES_RE = re.compile(r"does\s+not\s+allow\s+pets|not\s+pet\s+friendly|"
                         r"pets?\s+allowed\s*:?\s*no\b|"
                         r"pets?\s+(?:are\s+)?not\s+(?:allowed|permitted)",
                         re.IGNORECASE)


def _contradictory_lines(page_text: str) -> Dict[str, List[str]]:
    """The page's own conflicting sentences, quoted rather than summarised.

    A contradiction asserted without the words that make it one is just an
    opinion about a page, so both sides are carried verbatim.
    """
    accepts, refuses = [], []
    for line in page_text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if _ACCEPTS_RE.search(stripped):
            accepts.append(stripped)
        if _REFUSES_RE.search(stripped):
            refuses.append(stripped)
    return {"states_pet_terms": accepts[:6], "states_refusal": refuses[:6]}


def rederive(slug_dir: Path) -> Dict:
    """Parse a persisted block with the current reader. No network."""
    found = _latest_block(slug_dir)
    if not found:
        return {"slug": slug_dir.name, "state": "NO_PERSISTED_BLOCK",
                "extraction": {}}
    reading = PR.parse(found["block_text"], strategy="static_html_walk")
    result = PR.to_extraction(reading, location="")
    return {
        "slug": slug_dir.name,
        "state": "REDERIVED",
        "attempt": found["attempt"],
        "artifact": found["path"],
        "block_text": found["block_text"],
        "extraction": dict(result.extraction),
        "contradictions": [dict(c) for c in reading.contradictions],
        "parser_notes": list(reading.parser_notes),
        "patterns_fired": list(reading.patterns_fired),
    }


def old_extractions() -> Dict[str, Dict]:
    """What the 004 run published, keyed by identity, for the before/after."""
    if not VALIDATION_REPORT.is_file():
        return {}
    doc = json.loads(VALIDATION_REPORT.read_text(encoding="utf-8-sig"))
    return {row["identity_key"]: dict(row.get("firecrawl_extraction") or {})
            for row in doc["items"]}


def journal_rows() -> Dict[str, Dict]:
    path = RUN_DIR / "journal.jsonl"
    if not path.is_file():
        return {}
    out = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            out[row["identity_key"]] = row
    return out


def contradiction_state(entry: Dict) -> str:
    """SOURCE_CONTRADICTORY, or the ordinary state, named once."""
    for c in entry.get("contradictions") or []:
        if c.get("field") == "pets_allowed":
            return "SOURCE_CONTRADICTORY"
    return "RESOLVED"


def build(argv=None) -> Dict:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)

    dirs = _slug_dirs()
    old = old_extractions()

    results: List[Dict] = []
    for slug, slug_dir in dirs.items():
        entry = rederive(slug_dir)
        entry["state_class"] = contradiction_state(entry)
        results.append(entry)

    held = next((r for r in results
                 if "milwaukee-airport" in r["slug"] and "country-inn" in r["slug"]),
                None)
    if held:
        # The bounded block is not the only place the page contradicts itself,
        # and the wider evidence is what makes SOURCE_CONTRADICTORY the answer
        # rather than a reader excuse. Quoted from the persisted page text.
        held["wider_page_evidence"] = _contradictory_lines(
            _page_text(dirs[held["slug"]]))
        held["source_verdict"] = (
            "SOURCE_CONTRADICTORY. The property's own page states a pet fee, a "
            "pet limit and a pet weight cap, and also states that it does not "
            "allow pets. No reader can resolve that, and the corpus rule is to "
            "publish neither side. The record is not repaired into a clean "
            "answer.")

    doc = {
        "schema": "ptf-choice-reader-rederive/1.0",
        "work_order": WORK_ORDER,
        "market_id": MARKET,
        "brand": "CHOICE",
        "note": ("Re-derived from artifacts persisted by "
                 "PTF-FIRECRAWL-CHOICE-VALIDATION-004. No network request was "
                 "made and no Firecrawl credit was spent: the source is byte "
                 "for byte the source that produced the original reading, so "
                 "the only variable is the reader."),
        "network_requests": 0,
        "firecrawl_credits_spent": 0,
        "held_record": held,
        "rederived": results,
        "old_extractions": old,
    }
    if args.write:
        out = REPORTS / "ptf_choice_reader_rederive_005.json"
        out.write_bytes((json.dumps(doc, indent=1, ensure_ascii=False) + "\n")
                        .encode("utf-8"))
        doc["written_to"] = str(out.relative_to(REPO))
    return doc


def main(argv=None) -> int:
    doc = build(argv)
    held = doc["held_record"]
    print("re-derived %d Choice captures from disk, 0 requests, 0 credits"
          % len(doc["rederived"]))
    if held:
        print()
        print("HELD RECORD: %s" % held["slug"])
        print("  block: %s" % held["block_text"])
        print("  now:   %s" % json.dumps(held["extraction"]))
        print("  class: %s" % held["state_class"])
        for note in held["parser_notes"]:
            print("  note:  %s" % note)
    changed = [r for r in doc["rederived"] if r["state_class"] != "RESOLVED"]
    print()
    print("SOURCE_CONTRADICTORY: %d of %d" % (len(changed), len(doc["rederived"])))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
