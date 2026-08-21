"""PTF-MILWAUKEE-HIGH-VALUE-REPAIR-WAVE-032 -- reading what we already have.

031 found three Milwaukee properties whose complete pet policy sits in the
document a capture persisted, while the block that capture located carries a
fragment of it. This re-derives those three from that evidence. No page is
fetched and no provider is contacted.

HOW A RECOVERY BECOMES AN OBSERVATION WITHOUT REWRITING HISTORY
----------------------------------------------------------------
The original attempt directories are not touched. Each recovery writes a NEW
attempt directory under its own run id, carrying the SAME document -- byte for
byte, same sha256 -- and a different policy block, with a locator record that
says the block was recovered offline and names the capture it came from.

That keeps two things true at once. The historical run still says what it said
in August, and the current-state store gets a row whose evidence is checkable:
the document hash matches the original capture's, so anyone can confirm the
recovered block is a span of the page that was actually served.

WHAT THIS RUN CANNOT DO
-----------------------
It cannot make the reader understand a surface it does not understand. Two of
the three recovered blocks are Hyatt's label-and-value layout -- "Weight Limits
Individual pet weight limit : 150 Pounds", "Maximum number of pets is 2" -- and
the generic reader extracts none of it. The locator repair is complete and
correct for those pages; what stands between them and an observation is now a
READER gap, which this work order was not commissioned to fix and which is
reported rather than quietly patched.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts.pettripfinder.acquisition import closure_assessment_031 as C31   # noqa: E402
from scripts.pettripfinder.acquisition.hilton_decision_023 import (          # noqa: E402
    SUBSTANTIVE_FIELDS,
)
from scripts.pettripfinder.acquisition import premium_resolution_028 as P28   # noqa: E402
from scripts.pettripfinder.acquisition import store_integration_025 as S      # noqa: E402
from scripts.pettripfinder.brightdata import policy_locator as PL             # noqa: E402
from scripts.pettripfinder.brightdata import policy_reading as PR             # noqa: E402
from scripts.pettripfinder.brightdata import policy_surface as PS             # noqa: E402

WORK_ORDER = "PTF-MILWAUKEE-HIGH-VALUE-REPAIR-WAVE-032"
MARKET = "milwaukee-wi"

REPORTS = REPO / "launch_packages" / "pettripfinder" / "markets" / "reports"
STORE = REPORTS / ("%s_policy_proposals_001.json" % MARKET)
RUN_REPORT = REPORTS / "ptf_milwaukee_locator_recovery_032.json"

RUN_ID = "milwaukee-locator-032"
RUN_ROOT = REPO / "data" / "acquisition" / RUN_ID
RUN_DIR = RUN_ROOT / RUN_ID
JOURNAL = RUN_ROOT / "journal.jsonl"

PUBLICATION_GRADE = "ACQUIRED_PUBLICATION_GRADE"
EXPECTED_SUBJECTS = 3


def _now() -> str:
    return datetime.now(timezone.utc).isoformat(timespec="seconds")


def _rel(path: Path) -> str:
    try:
        return str(path.relative_to(REPO)).replace("\\", "/")
    except ValueError:
        return str(path).replace("\\", "/")


# --------------------------------------------------------------------------- #
# Phase 1 -- the cohort, derived from 031.
# --------------------------------------------------------------------------- #

ASSESSMENT_031 = REPORTS / "ptf_milwaukee_closure_assessment_031.json"


def subjects() -> List[Dict]:
    """The identities 031 classified as locator recoveries.

    Read from 031's COMMITTED report rather than by re-running its classifier.
    The classifier answers "what is unresolved NOW", and the moment one of
    these three becomes an observation it leaves that set -- so a live
    derivation shrinks its own cohort as it succeeds, and this module could
    not report on the work it had just done. The subject set is a historical
    fact about what 031 found, and it is read as one.
    """
    if ASSESSMENT_031.is_file():
        doc = json.loads(ASSESSMENT_031.read_text(encoding="utf-8-sig"))
        rows = [row for row in doc["properties"]
                if row["closure_class"] == C31.TARGETED_REPAIR
                and row["repair"] == C31.REPAIR_LOCATOR]
        if rows:
            return sorted(rows, key=lambda row: row["identity_key"])
    return sorted((row for row in C31.classify()
                   if row["closure_class"] == C31.TARGETED_REPAIR
                   and row["repair"] == C31.REPAIR_LOCATOR),
                  key=lambda row: row["identity_key"])


def assert_subjects() -> List[Dict]:
    rows = subjects()
    if len(rows) != EXPECTED_SUBJECTS:
        raise SystemExit("ABORT: locator_recovery_subjects is %d, expected %d"
                         % (len(rows), EXPECTED_SUBJECTS))
    return rows


def preflight() -> Dict:
    store = json.loads(STORE.read_text(encoding="utf-8-sig"))
    census = P28.full_census()
    rows = subjects()
    return {
        "checked_at": _now(),
        "store_rows": len(store["items"]),
        "observed": census["phase11_final_states"]["OBSERVED"],
        "active_unresolved": census["phase11_final_states"]["TOUCHED_UNRESOLVED"],
        "published": sum(1 for row in store["items"] if row.get("published")),
        "authority_written": bool(store.get("authority_written")),
        "authority_files": len(list(
            (REPO / "launch_packages" / "pettripfinder")
            .rglob("*hotel_policy_facts*milwaukee*"))),
        "locator_recovery_subjects": len(rows),
        "subjects": [row["identity_key"] for row in rows],
        "assertions": {
            "store_is_114": len(store["items"]) == 114,
            "unresolved_is_19":
                census["phase11_final_states"]["TOUCHED_UNRESOLVED"] == 19,
            "locator_recovery_subjects_is_3": len(rows) == EXPECTED_SUBJECTS,
            "every_subject_has_a_persisted_document":
                all(row["document_persisted"] for row in rows),
            "nothing_published": all(not row.get("published")
                                     for row in store["items"]),
            "authority_absent": not bool(store.get("authority_written")),
        },
    }


# --------------------------------------------------------------------------- #
# Phase 2 / 7 -- reproduce, then recover, from disk only.
# --------------------------------------------------------------------------- #

def source_document(row: Mapping) -> Dict:
    """The document the original capture persisted, and its hashes."""
    directory = REPO / row["attempt_dir"]
    html_path = directory / "rendered.html"
    text_path = directory / "page-text.txt"
    html = (html_path.read_text(encoding="utf-8", errors="replace")
            if html_path.is_file() else "")
    text = (text_path.read_text(encoding="utf-8", errors="replace")
            if text_path.is_file() else "")
    return {
        "attempt_dir": row["attempt_dir"],
        "html": html,
        "page_text": text,
        "document_sha256": PL.sha256_text(html),
        "searchable": C31.document_text(directory),
    }


def recover(row: Mapping) -> Dict:
    """One offline recovery: old block, richer candidate, what the reader makes."""
    document = source_document(row)
    old_block = row["policy_block"] or ""
    recovery = PS.recover_richer_block(old_block, document["searchable"])
    block = recovery.text if recovery.recovered else old_block
    reading = PR.parse(block, strategy="richer_block_recovery")
    result = PR.to_extraction(reading, location=PL.BLOCK_ARTIFACT)
    return {
        "identity_key": row["identity_key"],
        "canonical_name": row["canonical_name"],
        "brand": row["brand"],
        "source_run": row["last_run"],
        "source_url": row["source_url"],
        "source_attempt_dir": document["attempt_dir"],
        "document_sha256": document["document_sha256"],
        "old_block": old_block,
        "old_block_chars": len(old_block),
        "recovered": recovery.recovered,
        "recovery": recovery.to_dict(),
        "new_block": block,
        "new_block_chars": len(block),
        "extraction": dict(result.extraction),
        "withheld": dict(result.withheld or {}),
        "evidence": [dict(item) for item in result.evidence],
        "non_inferences": list(result.non_inferences),
        "reader_found": bool(reading.found),
        # An observation has to state a PET fact. Judged with the corpus's own
        # substantive-field set rather than "the extraction is non-empty",
        # because Hyatt Place Airport's recovered block produces exactly one
        # field and it is wrong: the reader labels the 1-6 night PET fee of
        # $100 a cleaning fee, when the page's own words put the cleaning
        # charge inside the $200 band. ``cleaning_fee`` is not in that set, so
        # the row is withheld by the same rule that keeps an amenity chip out,
        # and no hand-picking was needed to reach it.
        "substantive_pet_fields": sorted(
            (set(result.extraction) & SUBSTANTIVE_FIELDS)
            | ({"pets_allowed"} if "pets_allowed" in result.extraction
               else set())),
        "yields_an_observation": bool(
            (set(result.extraction) & SUBSTANTIVE_FIELDS)
            or "pets_allowed" in result.extraction),
        "_html": document["html"],
        "_page_text": document["page_text"],
    }


def recoveries() -> List[Dict]:
    return [recover(row) for row in assert_subjects()]


# --------------------------------------------------------------------------- #
# Writing the derived evidence.
# --------------------------------------------------------------------------- #

def _slug(row: Mapping) -> str:
    import re
    return re.sub(r"[^a-z0-9]+", "-",
                  (row["canonical_name"] or "").lower()).strip("-")[:80]


def write_evidence(row: Mapping) -> Dict:
    """A new attempt directory carrying the same document and a better block.

    The original is never modified. The document is copied verbatim so its
    sha256 still matches the capture that served it, which is what makes the
    recovered block checkable rather than merely asserted.
    """
    directory = RUN_DIR / _slug(row) / "attempt-01"
    directory.mkdir(parents=True, exist_ok=True)
    (directory / "rendered.html").write_text(row["_html"], encoding="utf-8")
    (directory / "page-text.txt").write_text(row["_page_text"],
                                             encoding="utf-8")
    (directory / PL.BLOCK_ARTIFACT).write_text(row["new_block"],
                                               encoding="utf-8")

    class _Hit:
        found = True
        strategy = "richer_block_recovery"
        selector = ""
        matched_phrase = ""
        policy_features = PS.policy_features(row["new_block"])
        container_chars = len(row["new_block"])
        candidates_considered = row["recovery"]["candidates_considered"]
        brand_generic = False
        rendered = False

    record = PL.build_record(
        hit=_Hit(), block_text=row["new_block"],
        document_sha256=row["document_sha256"],
        walk=PL.STATIC_TEXT_WALK,
        recovery=dict(row["recovery"],
                      work_order=WORK_ORDER,
                      recovered_from_run=row["source_run"],
                      recovered_from_attempt_dir=row["source_attempt_dir"],
                      provider_calls=0))
    PL.persist(directory, record)
    return {"attempt_dir": _rel(directory),
            "block_sha256": record["block_sha256"],
            "document_sha256": record["document_sha256"]}


def journal_entry(row: Mapping, evidence: Mapping) -> Dict:
    return {
        "identity_key": row["identity_key"],
        "canonical_name": row["canonical_name"],
        "brand": row["brand"],
        "source_url": row["source_url"],
        "official_url": row["source_url"],
        "provider": "",
        "provider_used": "",
        "providers_tried": [],
        "reader": "generic",
        "final_state": PUBLICATION_GRADE,
        "acquisition_status": "ACQUIRED",
        "publication_grade": True,
        "policy_locator": "richer_block_recovery",
        "policy_block": row["new_block"],
        "policy_block_chars": row["new_block_chars"],
        "reader_fields": sorted(row["extraction"]),
        "reader_withheld": sorted(row["withheld"]),
        "attempt_records": [],
        "recovered_from": {
            "work_order": WORK_ORDER,
            "run": row["source_run"],
            "attempt_dir": row["source_attempt_dir"],
            "document_sha256": row["document_sha256"],
            "provider_calls": 0,
        },
        "attempt_dir": evidence["attempt_dir"],
        "completed_at": _now(),
    }


def run(*, write: bool = True) -> List[Dict]:
    """Write derived evidence for every recovery that yields an observation."""
    rows = recoveries()
    out: List[Dict] = []
    if write:
        RUN_DIR.mkdir(parents=True, exist_ok=True)
        if JOURNAL.is_file():
            JOURNAL.unlink()
    for row in rows:
        entry = None
        if row["recovered"] and row["yields_an_observation"]:
            if write:
                evidence = write_evidence(row)
                entry = journal_entry(row, evidence)
                with JOURNAL.open("a", encoding="utf-8") as handle:
                    handle.write(json.dumps(entry, ensure_ascii=False) + "\n")
        out.append(dict({k: v for k, v in row.items()
                         if not k.startswith("_")},
                        journalled=entry is not None))
    return out


def journal_rows() -> List[Dict]:
    if not JOURNAL.is_file():
        return []
    return [json.loads(line) for line in
            JOURNAL.read_text(encoding="utf-8").splitlines() if line.strip()]


# --------------------------------------------------------------------------- #
# Phase 6 -- the controls that must not expand.
# --------------------------------------------------------------------------- #

NEGATIVE_CONTROLS: Tuple[Tuple[str, str, str], ...] = (
    ("spark-amenity-flag",
     "Pets allowed Yes",
     "Hotel policies Parking Pets Smoking Pets allowed Yes All Policies "
     "A fee will be assessed for smoking in a non-smoking room. "
     "Free breakfast Indoor pool Free parking Pet-friendly rooms"),
    ("motel6-amenity-chip",
     "Pet Friendly",
     "Amenities Free WiFi Pet Friendly Outdoor Pool Guest Laundry "
     "Rooms from $59 per night. Rated 3.5 of 5 by 412 guests."),
    ("red-roof-service-animal-only",
     "Service Animals are Welcome",
     "Service Animals are Welcome. Deposit Policy: A $50 refundable deposit "
     "for incidentals is required at check-in for all guests."),
    ("unrelated-room-prices",
     "Pets Welcome",
     "Pets Welcome. 1 King Bed 4 Guests Discounted rate: $160 USD /night "
     "Strikethrough Rate: $172 Member Rate 160.00 per night"),
    ("smoking-and-parking-fees",
     "Pets allowed",
     "Pets allowed. Self-parking $35 per night. A cleaning fee will be "
     "assessed for smoking in a non-smoking room."),
)


def negative_controls() -> List[Dict]:
    rows = []
    for name, block, document in NEGATIVE_CONTROLS:
        recovery = PS.recover_richer_block(block, document)
        rows.append({
            "control": name,
            "block": block,
            "document": document,
            "recovered": recovery.recovered,
            "reason": recovery.reason,
            "terms_added": list(recovery.terms_added),
            "expanded": recovery.recovered,
        })
    return rows


# --------------------------------------------------------------------------- #
# Reporting.
# --------------------------------------------------------------------------- #

def counters() -> Dict:
    census = P28.full_census()
    store = json.loads(STORE.read_text(encoding="utf-8-sig"))
    return {
        "census_total": census["census_total"],
        "active_eligible": census["active_eligible_total"],
        "observed": census["phase11_final_states"]["OBSERVED"],
        "active_unresolved": census["phase11_final_states"]["TOUCHED_UNRESOLVED"],
        "published": sum(1 for row in store["items"] if row.get("published")),
        "sum_of_final_states": census["phase11_sum"],
    }


def build_report() -> Dict:
    rows = [dict({k: v for k, v in row.items() if not k.startswith("_")})
            for row in recoveries()]
    journalled = {entry["identity_key"] for entry in journal_rows()}
    for row in rows:
        row["journalled"] = row["identity_key"] in journalled
    controls = negative_controls()
    return {
        "schema": "ptf-milwaukee-locator-recovery/1.0",
        "work_order": WORK_ORDER,
        "market": MARKET,
        "run_id": RUN_ID,
        "generated_at": _now(),
        "preflight": preflight(),
        "recoveries": rows,
        "recovered": sum(1 for row in rows if row["recovered"]),
        "yielding_an_observation": sum(1 for row in rows
                                       if row["yields_an_observation"]),
        "journalled": len(journalled),
        "negative_controls": controls,
        "negative_controls_that_expanded": [row["control"] for row in controls
                                            if row["expanded"]],
        "counters": counters(),
        "provider_calls": 0,
        "incremental_spend_usd": 0.0,
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
    parser.add_argument("--recover", action="store_true")
    parser.add_argument("--controls", action="store_true")
    parser.add_argument("--apply", action="store_true")
    parser.add_argument("--report", action="store_true")
    args = parser.parse_args(argv)

    if args.preflight:
        print(json.dumps(preflight(), indent=2))
    if args.recover:
        for row in recoveries():
            print("== %s" % row["identity_key"])
            print("   old %4d chars | new %4d chars | recovered=%s"
                  % (row["old_block_chars"], row["new_block_chars"],
                     row["recovered"]))
            print("   added %s" % row["recovery"]["terms_added"])
            print("   reader %s" % json.dumps(row["extraction"], default=str))
            print("   withheld %s" % json.dumps(row["withheld"]))
            print("   yields an observation: %s" % row["yields_an_observation"])
    if args.controls:
        for row in negative_controls():
            print("%-32s expanded=%s  %s"
                  % (row["control"], row["expanded"], row["reason"][:70]))
    if args.apply:
        for row in run(write=True):
            print("%-44s recovered=%-5s journalled=%s"
                  % (row["identity_key"][:44], row["recovered"],
                     row["journalled"]))
    if args.report:
        doc = write_report()
        print(json.dumps({k: v for k, v in doc.items()
                          if k not in ("recoveries", "preflight",
                                       "negative_controls")}, indent=2))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
