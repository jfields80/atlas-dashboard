"""PTF-MILWAUKEE-OBSERVATION-REDERIVATION-018 -- re-read what is already on disk.

016 and 017 hardened the reader and deliberately touched no stored record. 23
persisted documents across 9 Milwaukee properties disagree with the reader as it
now stands, and this work order re-derives exactly those from evidence already
captured. No provider is called: the evidence has not changed, only the reading
of it, and re-fetching would introduce the one variable the comparison exists to
remove.

WHAT IS RE-READ, AND WHY IT IS NOT THE DOCUMENT
-----------------------------------------------
Each capture persisted two things: ``rendered.html``, the hashed artifact, and
``policy-block.txt``, the bounded block the locator selected from it. The block
is byte-identical to the ``policy_text`` on the stored observation, and it is
what the record's evidence quotes are quotes FROM.

This module re-parses THE BLOCK. Re-locating from ``rendered.html`` would change
two things at once -- which text the record is about, and how that text is read
-- and only the second is a re-derivation. The first is a re-acquisition, and it
is not authorised here.

That distinction is not academic. It changes the answer on two of these nine:

  One property's stored block reads "the pet fee is 75.00 USD per stay ... Pet
  fee per night: 75 USD" -- the same amount on two bases. The current reader
  sees both and withholds. Re-locating instead returns a shorter block holding
  only the per-night half, which looks clean and yields a confident $75/night --
  publishing one of two stated bases, which the frozen semantics forbid.

  Another's stored block states "Dogs only" and prices the pet in a form this
  reader still cannot parse; the shorter re-located block states the fee in a
  form it can, and never mentions the species. Neither block is a superset of
  the other.

So the static walk under-reads the saved artifact relative to the in-page walk
that produced these records. That is a real locator gap and it is REPORTED here,
not acted on: acting on it would silently move what every one of these records
is about.

WHERE A MILWAUKEE OBSERVATION LIVES
-----------------------------------
  the run JOURNAL      gitignored, append-only, a record of what THAT RUN saw
                       with THAT reader. A log, not a mutable store.
  the PROPOSALS store  ``milwaukee-wi_policy_proposals_001.json`` -- the
                       committed current-state observation record, a projection
                       of the router journal, ``published: false`` throughout.
  the run REPORTS      what one work order measured, on a date. Historical.

The update path is therefore: re-parse the stored block, write a SUPERSEDING
artifact carrying both readings, and regenerate the proposals store through its
own builder. No historical report is edited and nothing is hand-entered.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path
from typing import Dict, List, Optional, Tuple

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts.pettripfinder.brightdata import policy_reading as PR    # noqa: E402
from scripts.pettripfinder.brightdata import unlocker_capture as UC  # noqa: E402

WORK_ORDER = "PTF-MILWAUKEE-OBSERVATION-REDERIVATION-018"
MARKET = "milwaukee-wi"
REPORTS = REPO / "launch_packages" / "pettripfinder" / "markets" / "reports"
DATA = REPO / "data" / "acquisition"

QUEUE_SOURCE = REPORTS / "ptf_reader_corpus_dry_run_017.json"
REPORT = REPORTS / "ptf_milwaukee_observation_rederivation_018.json"

#: The runs whose captures ARE the observation of record for a property.
ROUTER_RUN = "milwaukee-router-001"
IHG_RUN = "milwaukee-ihg-009"
OBSERVATION_RUNS = (ROUTER_RUN, IHG_RUN)

JOURNALS = {ROUTER_RUN: DATA / ROUTER_RUN / ROUTER_RUN / "journal.jsonl",
            IHG_RUN: DATA / IHG_RUN / IHG_RUN / "journal.jsonl"}

#: Asserted before anything is written. A queue that has moved is a different
#: work order.
EXPECTED_DOCUMENTS = 23
EXPECTED_PROPERTIES = 9

#: The persisted evidence block beside every capture.
BLOCK_ARTIFACT = "policy-block.txt"


class Blocked(Exception):
    """Evidence missing or unreadable. Classified, never reacquired."""


def _slug(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", (value or "").lower()).strip("-")


def reader_commit() -> str:
    try:
        out = subprocess.run(["git", "rev-parse", "HEAD"], cwd=REPO,
                             capture_output=True, check=True).stdout
        return out.decode("utf-8").strip()
    except (subprocess.CalledProcessError, FileNotFoundError):
        return ""


# --------------------------------------------------------------------------- #
# The queue, derived and asserted.
# --------------------------------------------------------------------------- #

def queue() -> List[str]:
    doc = json.loads(QUEUE_SOURCE.read_text(encoding="utf-8"))
    documents = sorted(doc["re_derivation_queue"]["documents"])
    properties = sorted({d.split("/")[2] for d in documents})
    if len(documents) != EXPECTED_DOCUMENTS:
        raise SystemExit("ABORT: expected %d queued documents, the queue names "
                         "%d. Refusing to mutate a set this work order did not "
                         "scope." % (EXPECTED_DOCUMENTS, len(documents)))
    if len(properties) != EXPECTED_PROPERTIES:
        raise SystemExit("ABORT: expected %d affected properties, derived %d: %s"
                         % (EXPECTED_PROPERTIES, len(properties), properties))
    return documents


def stored_journal(path: Path) -> Dict[str, Dict]:
    """One run's observations, keyed by the property slug it captured."""
    if not path.is_file():
        return {}
    out = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            out[_slug(row["canonical_name"])] = row
    return out


def _document_of(row: Dict) -> Dict:
    return (row.get("result") or {}).get("document") or {}


def stored_extraction(row: Dict) -> Dict:
    doc = _document_of(row)
    obs = doc.get("observation") or {}
    if obs.get("extraction"):
        return dict(obs["extraction"])
    return dict(row.get("extraction") or {})


def stored_withheld(row: Dict) -> Dict:
    doc = _document_of(row)
    return dict(doc.get("withheld_fields") or row.get("withheld_fields") or {})


# --------------------------------------------------------------------------- #
# The persisted evidence block.
# --------------------------------------------------------------------------- #

def evidence_block(run: str, slug: str, row: Dict) -> Tuple[str, Path]:
    """The block this observation was read from, and where it lives.

    Preferred from the ``policy-block.txt`` artifact so the re-derivation reads
    a FILE rather than a field, which is what makes it checkable in a fresh
    worktree. The stored ``policy_text`` is used only to verify the file, never
    in place of it.
    """
    candidates = sorted((DATA / run / run / slug).glob("attempt-*/%s" % BLOCK_ARTIFACT))
    stored_text = (_document_of(row).get("policy_text") or "").strip()
    for path in candidates:
        text = path.read_text(encoding="utf-8", errors="replace").strip()
        if not text:
            continue
        if stored_text and text != stored_text:
            continue
        return text, path
    if candidates and stored_text:
        raise Blocked("no persisted %s matches the stored policy_text for %r"
                      % (BLOCK_ARTIFACT, slug))
    if stored_text:
        raise Blocked("no persisted %s for %r; only the journal field survives"
                      % (BLOCK_ARTIFACT, slug))
    raise Blocked("no persisted evidence block for %r" % slug)


def _relative(path: Path) -> str:
    return str(path.relative_to(REPO)).replace("\\", "/")


# --------------------------------------------------------------------------- #
# Re-derivation. Mechanical, from the bytes.
# --------------------------------------------------------------------------- #

def read_block(text: str, location: str) -> Dict:
    reading = PR.parse(text, strategy="observation_rederivation_018")
    result = PR.to_extraction(reading, location=location)
    return {
        "extraction": dict(result.extraction),
        "withheld": dict(result.withheld or {}),
        "flags": [f.get("code") for f in (result.flags or [])],
        "evidence_quotes": [e.get("quote", "") for e in (result.evidence or ())],
        "evidence": [dict(e) for e in (result.evidence or ())],
        "non_inferences": list(result.non_inferences),
    }


def _field_delta(old: Dict, new: Dict) -> Dict:
    return {
        "fields_added": sorted(set(new) - set(old)),
        "fields_removed": sorted(set(old) - set(new)),
        "fields_changed": sorted(f for f in set(old) & set(new)
                                 if old[f] != new[f]),
        "fields_unchanged": sorted(f for f in set(old) & set(new)
                                   if old[f] == new[f]),
    }


def locator_discrepancy(row: Dict, block: str) -> Dict:
    """What the STATIC walk would find in the saved artifact instead.

    Reported so the gap is visible and countable. Never applied: a different
    block is a different subject, and changing the subject is a re-acquisition.
    """
    path = Path(_document_of(row).get("rendered_html_path") or "")
    if not path.is_file():
        return {"comparable": False, "reason": "the saved artifact is not on disk"}
    hit = UC.locate_policy_in_html(path.read_text(encoding="utf-8",
                                                  errors="replace"))
    static_text = hit.text if hit.found else ""
    if static_text.strip() == block.strip():
        return {"comparable": True, "differs": False}
    static = read_block(static_text, "static-walk") if static_text else \
        {"extraction": {}, "withheld": {}}
    stored_read = read_block(block, "stored-block")
    return {
        "comparable": True,
        "differs": True,
        "stored_block_chars": len(block),
        "static_block_chars": len(static_text),
        "static_only_fields": sorted(set(static["extraction"])
                                     - set(stored_read["extraction"])),
        "stored_only_fields": sorted(set(stored_read["extraction"])
                                     - set(static["extraction"])),
        "note": ("the static walk over the saved artifact selects a different "
                 "block from the in-page walk that produced this record; "
                 "reported, not applied"),
    }


def rederive() -> Dict:
    documents = queue()
    journals = {run: stored_journal(path) for run, path in JOURNALS.items()}

    by_property: Dict[str, List[str]] = defaultdict(list)
    for relative in documents:
        by_property[relative.split("/")[2]].append(relative)

    records, blocked = [], []
    for slug in sorted(by_property):
        run = next((r for r in OBSERVATION_RUNS
                    if any(d.startswith(r + "/") for d in by_property[slug])),
                   "")
        if not run:
            raise SystemExit(
                "ABORT: %r has no queued document from a run that carries its "
                "observation." % slug)
        stored = journals.get(run, {}).get(slug)
        if stored is None:
            raise SystemExit("ABORT: no stored observation for %r in %s"
                             % (slug, run))
        try:
            block, block_path = evidence_block(run, slug, stored)
        except Blocked as exc:
            blocked.append({"property_slug": slug, "run": run,
                            "reason": str(exc)})
            continue

        derived = read_block(block, _relative(block_path))
        old_extraction = stored_extraction(stored)
        old_withheld = stored_withheld(stored)
        doc = _document_of(stored)
        records.append({
            "property_slug": slug,
            "identity_key": stored["identity_key"],
            "canonical_name": stored["canonical_name"],
            "brand": stored.get("brand", ""),
            "market_id": MARKET,
            "observation_run": run,
            "source_url": stored.get("official_url", "")
                          or doc.get("source_url", ""),
            "evidence_block_path": _relative(block_path),
            "evidence_block_sha256": hashlib.sha256(
                block.encode("utf-8")).hexdigest(),
            "stored_artifact_content_hash": doc.get("content_hash", ""),
            "policy_text": block,
            # Two runs shape their journal rows differently: the router nests
            # the whole document, the decision runs record the route beside a
            # flat extraction. The reader is on both, in different places, and
            # is read from whichever one this row has rather than defaulted.
            "reader_at_capture": (doc.get("reader")
                                  or (stored.get("route") or {}).get("reader", "")),
            "old_extraction": old_extraction,
            "new_extraction": derived["extraction"],
            "old_withheld": old_withheld,
            "new_withheld": derived["withheld"],
            "old_flags": [f.get("code") if isinstance(f, dict) else f
                          for f in ((doc.get("observation") or {}).get("flags")
                                    or ())],
            "new_flags": derived["flags"],
            "evidence": derived["evidence"],
            # Where the CAPTURE said these words live, kept so a re-derivation
            # does not overwrite container provenance with a file path.
            "capture_evidence_location": next(
                (e.get("location", "") for e in
                 ((doc.get("observation") or {}).get("evidence") or ())
                 if e.get("location")), ""),
            "evidence_quotes": derived["evidence_quotes"],
            "evidence_quotes_contiguous": all(
                q in block for q in derived["evidence_quotes"]),
            "non_inferences": derived["non_inferences"],
            "queued_documents": sorted(by_property[slug]),
            "locator_discrepancy": locator_discrepancy(stored, block),
            "publication_grade_at_capture": bool(stored.get("publication_grade")),
            "identity_confirmed_at_capture": bool(
                stored.get("identity_confirmed")),
            # Publication is a separate decision this work order may not make.
            # A better reading does not publish a record.
            "published": False,
            "founder_approved": False,
            **_field_delta(old_extraction, derived["extraction"]),
        })
    return {"records": records, "blocked": blocked, "documents": documents,
            "documents_by_property": dict(sorted(by_property.items()))}


def changed(records: List[Dict]) -> List[Dict]:
    return [r for r in records
            if r["fields_added"] or r["fields_removed"] or r["fields_changed"]
            or r["old_withheld"] != r["new_withheld"]]


def build() -> Dict:
    derived = rederive()
    records = derived["records"]
    return {
        "schema": "ptf-record-recertification/1.0",
        "work_order": WORK_ORDER,
        "market_id": MARKET,
        "note": ("Re-derived from evidence already on disk by re-parsing the "
                 "persisted policy BLOCK, not by re-locating one. No provider "
                 "was called and no value was entered by hand."),
        "reader_commit": reader_commit(),
        "supersedes": {
            "observation_store": "milwaukee-wi_policy_proposals_001.json",
            "note": ("The previous reading survives on every record below as "
                     "old_extraction / old_withheld, and in the historical run "
                     "reports, which are not edited."),
            "prior_readings_preserved_in": [
                "ptf_ihg_live_run_009.json",
                "ptf_ihg_recertification_011.json",
                "ptf_milwaukee_provider_utilization_007.json",
            ],
        },
        "queued_documents": len(derived["documents"]),
        "affected_properties": len(records) + len(derived["blocked"]),
        "records_rederived": len(records),
        "records_changed": len(changed(records)),
        "blocked": derived["blocked"],
        "documents_by_property": derived["documents_by_property"],
        "network_requests": 0,
        "provider_calls": 0,
        "firecrawl_credits": 0,
        "brightdata_usd_minor": 0,
        "authority_written": False,
        "published": False,
        "founder_approvals_created": 0,
        "records": records,
    }


# --------------------------------------------------------------------------- #
# Applying it: through the observation store's OWN builder, never by hand.
# --------------------------------------------------------------------------- #

PROPOSALS = REPORTS / ("%s_policy_proposals_001.json" % MARKET)


def overlay(doc: Dict) -> Dict[str, Dict]:
    """The re-derived readings, keyed the way the proposals builder keys rows.

    Only records whose observation run feeds that store appear. The two IHG
    records were captured by a different run and the store is a projection of
    the router journal alone, so they have no row to update -- reported rather
    than invented.
    """
    return {
        r["identity_key"]: {
            "work_order": WORK_ORDER,
            "reader_commit": doc["reader_commit"],
            "evidence_block_path": r["evidence_block_path"],
            "evidence_block_sha256": r["evidence_block_sha256"],
            "extraction": r["new_extraction"],
            "withheld": r["new_withheld"],
            "non_inferences": r["non_inferences"],
            "evidence": _relocated_evidence(r),
        }
        for r in doc["records"] if r["observation_run"] == ROUTER_RUN
    }


def _relocated_evidence(record: Dict) -> List[Dict]:
    """Re-derived citations, still pointing at where the quote was CAPTURED.

    ``to_extraction`` stamps each citation with the location it was handed,
    which here is the persisted block file. That is where this module read the
    words, and it is not where the property published them: the capture
    recorded the DOM container the in-page walk selected, and that is strictly
    more informative about where on the page the fact lives.

    So the capture's own location survives, and the block file -- which is a
    serialization of that same container -- is recorded once, on the
    supersession record, rather than smeared over every citation.
    """
    captured_at = record.get("capture_evidence_location") or ""
    out = []
    for item in record["evidence"]:
        entry = dict(item)
        if captured_at:
            entry["location"] = captured_at
        out.append(entry)
    return out


def differential(doc: Dict) -> Dict:
    """What applying the overlay would change in the observation store.

    Run BEFORE anything is written. A tenth property differing is a stop.
    """
    from scripts.pettripfinder import milwaukee_policy_proposals_001 as PROP
    committed = json.loads(PROPOSALS.read_text(encoding="utf-8-sig"))
    rebuilt = PROP.build(rederived=overlay(doc), write=False)

    def rows(store):
        return {i["identity_key"]: i for i in store["items"]}

    old_rows, new_rows = rows(committed), rows(rebuilt)
    if set(old_rows) != set(new_rows):
        return {"clean": False,
                "reason": "the set of proposal rows changed",
                "added": sorted(set(new_rows) - set(old_rows)),
                "removed": sorted(set(old_rows) - set(new_rows))}

    differing = []
    for key, old in old_rows.items():
        new = dict(new_rows[key])
        # the always-present supersession key is not itself a change
        new_cmp = {k: v for k, v in new.items() if k != "rederivation"}
        old_cmp = {k: v for k, v in old.items() if k != "rederivation"}
        if new_cmp != old_cmp:
            differing.append({
                "identity_key": key,
                "canonical_name": old["canonical_name"],
                "fields": sorted(k for k in set(old_cmp) | set(new_cmp)
                                 if old_cmp.get(k) != new_cmp.get(k)),
            })

    expected = sorted(overlay(doc))
    actual = sorted(r["identity_key"] for r in differing)
    unexpected = sorted(set(actual) - set(expected))
    return {
        "clean": not unexpected,
        "expected_rows": expected,
        "rows_that_differ": actual,
        "unexpected_rows": unexpected,
        "detail": differing,
        "identity_fields_unchanged": all(
            old_rows[k]["canonical_name"] == new_rows[k]["canonical_name"]
            and old_rows[k]["brand"] == new_rows[k]["brand"]
            and old_rows[k]["provenance"] == new_rows[k]["provenance"]
            for k in old_rows),
        "publication_status_unchanged": all(
            new_rows[k]["published"] is False
            and new_rows[k]["founder_approved"] is False for k in new_rows),
        "rows_not_in_this_store": sorted(
            r["identity_key"] for r in doc["records"]
            if r["observation_run"] != ROUTER_RUN),
    }


def apply(doc: Dict) -> Dict:
    from scripts.pettripfinder import milwaukee_policy_proposals_001 as PROP
    check = differential(doc)
    if not check["clean"]:
        raise SystemExit("ABORT: the observation differential is not clean: %s"
                         % json.dumps(check, indent=1)[:800])
    store = PROP.build(rederived=overlay(doc), write=True)
    return {"differential": check, "rows_written": len(store["items"]),
            "authority_written": store["authority_written"],
            "founder_approvals_created": store["founder_approvals_created"]}


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    parser.add_argument("--apply", action="store_true",
                        help="write the re-derived readings into the "
                             "observation store, after the differential passes")
    args = parser.parse_args(argv)
    doc = build()
    print("queued documents %d | properties %d | re-derived %d | changed %d"
          % (doc["queued_documents"], doc["affected_properties"],
             doc["records_rederived"], doc["records_changed"]))
    print("reader %s | provider calls %d | credits %d"
          % (doc["reader_commit"][:7], doc["provider_calls"],
             doc["firecrawl_credits"]))
    for r in doc["records"]:
        print()
        print("=== %s  [%s]" % (r["canonical_name"], r["observation_run"]))
        print("   old: %s" % json.dumps(r["old_extraction"]))
        print("   new: %s" % json.dumps(r["new_extraction"]))
        print("   +%s  -%s  ~%s" % (r["fields_added"], r["fields_removed"],
                                    r["fields_changed"]))
        if r["old_withheld"] != r["new_withheld"]:
            print("   withheld: %s -> %s" % (json.dumps(r["old_withheld"]),
                                             json.dumps(r["new_withheld"])))
        disc = r["locator_discrepancy"]
        if disc.get("differs"):
            print("   locator gap: static walk would add %s / lose %s"
                  % (disc["static_only_fields"], disc["stored_only_fields"]))
    for b in doc["blocked"]:
        print("\nBLOCKED (not reacquired): %s -- %s"
              % (b["property_slug"], b["reason"]))
    check = differential(doc)
    doc["observation_store_differential"] = check
    print()
    print("differential clean       : %s" % check["clean"])
    print("  rows expected to differ: %s" % check["expected_rows"])
    print("  rows that differ       : %s" % check["rows_that_differ"])
    print("  unexpected             : %s" % (check["unexpected_rows"] or "none"))
    print("  identity unchanged     : %s" % check["identity_fields_unchanged"])
    print("  publication unchanged  : %s" % check["publication_status_unchanged"])
    print("  no row in this store   : %s" % check["rows_not_in_this_store"])

    if args.apply:
        result = apply(doc)
        doc["applied"] = result
        print()
        print("observation store updated: %d rows | authority_written=%s | "
              "approvals=%d" % (result["rows_written"],
                                result["authority_written"],
                                result["founder_approvals_created"]))
    if args.write:
        REPORT.write_bytes(
            (json.dumps(doc, indent=1, ensure_ascii=False) + "\n").encode("utf-8"))
        print("report written: %s" % REPORT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
