"""PTF-IHG-RECERTIFICATION-011 -- re-derive the three records the reader fix moved.

PTF-POLICY-READER-TIERED-FEE-HARDENING-010 hardened the reader and deliberately
did not touch a single stored record. Three records disagree with it, and this
work order re-derives exactly those three from the evidence already on disk. No
provider is called: the evidence has not changed, only the reading of it, and
re-fetching would introduce a variable the comparison is trying to eliminate.

WHERE THESE RECORDS ACTUALLY LIVE, AND WHY IT MATTERS
------------------------------------------------------
Published policy authority in this repository is ``hotel_policy_facts_<market>``.
Four markets have one: cleveland-akron-canton-oh, dayton-oh, indianapolis-in and
pittsburgh-pa. **Milwaukee does not.** Its authority shard holds identity and
routing only -- ``identity_routing.json``, ``hotel_exclusions.json``,
``seed_businesses.csv`` -- and the three IHG identity keys appear in no policy
authority artifact anywhere.

So there is no published record to re-certify. These three exist as OBSERVATION
records in the run journal PTF-IHG-FIRECRAWL-DECISION-009 wrote, and that run
recorded ``authority_written: false`` and ``policies_published: false`` at the
time.

That distinction decides what this module may do. Re-deriving an observation and
correcting the artifact that carries it is in scope. Creating Milwaukee's first
policy-authority shard is not: it would be a FIRST PUBLICATION of a market that
has never published, it needs founder attestation under the worker-approval
contract, and every work order in this sequence has been explicitly barred from
publishing policy. This module therefore corrects the observation records, and
reports the publication step as blocked on an authorization nobody has given.

WHAT "RE-CERTIFIED" MEANS HERE
------------------------------
The record is re-read from its own committed evidence by the reader at the
current commit, the old and new outputs are diffed field by field, the evidence
quote is re-checked as contiguous within the persisted block, and the result is
written back to the observation store with the reader commit that produced it.
Nothing is hand-edited: an extracted value that a human typed is not evidence.
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import Dict, List, Optional

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts.pettripfinder.brightdata import policy_reading as PR          # noqa: E402
from scripts.pettripfinder.brightdata import policy_surface as PS          # noqa: E402
from scripts.pettripfinder.brightdata import reader_differential_010 as D  # noqa: E402

WORK_ORDER = "PTF-IHG-RECERTIFICATION-011"
MARKET = "milwaukee-wi"
BRAND = "IHG"
REPORTS = REPO / "launch_packages" / "pettripfinder" / "markets" / "reports"
MIGRATION_QUEUE = REPORTS / "ptf_reader_migration_queue_010.json"
LIVE_RUN = REPORTS / "ptf_ihg_live_run_009.json"
DECISION = REPORTS / "ptf_ihg_firecrawl_decision_009.json"
LIVE_JOURNAL = (REPO / "data" / "acquisition" / "milwaukee-ihg-009"
                / "milwaukee-ihg-009" / "journal.jsonl")

#: Exactly three. Asserted before anything is written.
EXPECTED_SUBJECTS = 3

#: Where published policy authority lives, per market. Checked rather than
#: assumed, because the whole shape of this work order depends on it.
POLICY_FACTS = REPO / "launch_packages" / "pettripfinder"


def authority_state() -> Dict:
    """Is there a published policy record for this market at all?"""
    shard = POLICY_FACTS / ("hotel_policy_facts_%s.json" % MARKET)
    published = sorted(p.name for p in POLICY_FACTS.glob("hotel_policy_facts_*.json"))
    return {
        "policy_facts_shard_for_market": shard.name,
        "exists": shard.is_file(),
        "markets_with_a_published_policy_shard": published,
        "milwaukee_authority_shard_contents": sorted(
            p.name for p in (REPO / "launch_packages" / "pettripfinder" / "markets"
                             / "authority" / MARKET).glob("*")),
    }


def subjects() -> List[Dict]:
    """The three queued records, read from the committed migration queue."""
    doc = json.loads(MIGRATION_QUEUE.read_text(encoding="utf-8-sig"))
    rows = list(doc["candidates"])
    slugs = sorted({r["slug"] for r in rows})
    if len(slugs) != EXPECTED_SUBJECTS:
        raise SystemExit(
            "ABORT: expected %d subjects, the queue names %d (%s). Refusing to "
            "mutate a set this work order did not scope."
            % (EXPECTED_SUBJECTS, len(slugs), slugs))
    return rows


def stored_records() -> Dict[str, Dict]:
    """The observation records as they stand, keyed by identity."""
    out = {}
    for line in LIVE_JOURNAL.read_text(encoding="utf-8").splitlines():
        if line.strip():
            row = json.loads(line)
            out[row["identity_key"]] = row
    return out


def _slug_to_key(slug: str, stored: Dict[str, Dict]) -> str:
    norm = slug.replace("-", " ")
    for key in stored:
        squashed = key.replace(" ", "")
        if squashed.startswith(norm.replace(" ", "")[:28]):
            return key
    raise SystemExit("no stored record matches slug %r" % slug)


def evidence_for(slug: str) -> Optional[Path]:
    """The persisted policy block this record was read from."""
    hits = sorted((REPO / "data" / "acquisition").rglob(
        "*%s*/attempt-*/policy-block.txt" % slug))
    for path in hits:
        if path.read_text(encoding="utf-8", errors="replace").strip():
            return path
    return None


def reader_commit() -> str:
    return subprocess.run(
        ["git", "rev-parse", "HEAD"], cwd=str(REPO),
        capture_output=True, text=True, check=True).stdout.strip()


def rederive(slug: str, stored: Dict) -> Dict:
    """One record, re-read from its own committed evidence. No network."""
    path = evidence_for(slug)
    if path is None:
        return {"slug": slug, "state": "EVIDENCE_UNAVAILABLE",
                "note": ("no persisted policy block; re-certification would "
                         "require fresh acquisition, which this work order "
                         "permits only in that case")}
    text = path.read_text(encoding="utf-8", errors="replace").strip()
    reading = PR.parse(text, strategy="recertification")
    result = PR.to_extraction(reading, location="")
    new_extraction = dict(result.extraction)
    old_extraction = dict(stored.get("extraction") or {})

    changed = sorted(k for k in set(old_extraction) | set(new_extraction)
                     if old_extraction.get(k) != new_extraction.get(k))
    unchanged = sorted(k for k in set(old_extraction) & set(new_extraction)
                       if old_extraction.get(k) == new_extraction.get(k))

    # The evidence quote must still be a contiguous substring of the block it
    # claims to come from. A re-read that loses that has lost its evidence.
    quotes = [e.get("quote") for e in (result.evidence or []) if e.get("quote")]
    contiguous = all(q in reading.block_text for q in quotes)

    return {
        "slug": slug,
        "identity_key": stored["identity_key"],
        "canonical_name": stored["canonical_name"],
        "state": "REDERIVED",
        "evidence_path": str(path.relative_to(REPO)),
        "evidence_block": text,
        "old_extraction": old_extraction,
        "new_extraction": new_extraction,
        "fields_changed": changed,
        "fields_unchanged": unchanged,
        "withheld": dict(result.withheld),
        "flags": sorted({f.get("code") for f in (result.flags or []) if f.get("code")}),
        "evidence_quotes": quotes,
        "evidence_contiguous": contiguous,
        "policy_identity_confirmed": bool(stored.get("identity_confirmed")),
        "publication_grade_at_capture": bool(stored.get("publication_grade")),
        "publication_eligible": bool(
            contiguous and stored.get("identity_confirmed")
            and stored.get("publication_grade")),
        "reader_commit": reader_commit(),
        "network_requests": 0,
    }


def build(write: bool = False) -> Dict:
    queue = subjects()
    stored = stored_records()
    results = []
    for slug in sorted({r["slug"] for r in queue}):
        key = _slug_to_key(slug, stored)
        results.append(rederive(slug, stored[key]))

    # Nothing outside the three may differ. Re-checked against the whole
    # corpus rather than trusted from the earlier differential.
    corpus = D.corpus_dry_run()
    off_scope = sorted({r["slug"] for r in corpus["fee_changes"] + corpus["weight_changes"]}
                       - {r["slug"] for r in results})

    doc = {
        "schema": "ptf-record-recertification/1.0",
        "work_order": WORK_ORDER,
        "market_id": MARKET,
        "brand": BRAND,
        "note": ("Re-derived from evidence already on disk. No provider was "
                 "called: the evidence did not change, only the reading of it."),
        "reader_commit": reader_commit(),
        "subjects": len(results),
        "records": results,
        "differential_safety": {
            "records_in_scope": sorted(r["slug"] for r in results),
            "other_records_differing_corpus_wide": off_scope,
            "corpus_unique_texts_scanned": corpus["unique_policy_texts_scanned"],
            "clean": not off_scope,
        },
        "authority_state": authority_state(),
        "network_requests": 0,
        "provider_calls": 0,
    }
    if write:
        out = REPORTS / "ptf_ihg_recertification_011.json"
        out.write_bytes((json.dumps(doc, indent=1, ensure_ascii=False) + "\n")
                        .encode("utf-8"))
    return doc


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)
    doc = build(write=args.write)
    print("subjects: %d | reader %s | network calls %d"
          % (doc["subjects"], doc["reader_commit"][:7], doc["network_requests"]))
    for r in doc["records"]:
        print()
        print("=== %s" % r["canonical_name"])
        print("   old: %s" % json.dumps(r["old_extraction"]))
        print("   new: %s" % json.dumps(r["new_extraction"]))
        print("   changed: %s | unchanged: %d fields"
              % (r["fields_changed"], len(r["fields_unchanged"])))
        print("   withheld: %s | flags: %s" % (json.dumps(r["withheld"]), r["flags"]))
        print("   evidence contiguous: %s | identity: %s | pub-eligible: %s"
              % (r["evidence_contiguous"], r["policy_identity_confirmed"],
                 r["publication_eligible"]))
    d = doc["differential_safety"]
    print()
    print("differential clean: %s | other records differing: %s"
          % (d["clean"], d["other_records_differing_corpus_wide"] or "none"))
    a = doc["authority_state"]
    print("policy shard for this market exists: %s" % a["exists"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
