# -*- coding: utf-8 -*-
"""PTF-PITTSBURGH-HARDENED-SYNC-004 Phase 10 -- replay the owned corpus, $0.

    python -m scripts.pettripfinder.pittsburgh_reader_replay_004 --write

Pittsburgh bought 67 rendered pages under PTF-PITTSBURGH-PAID-ACQUISITION-
AUTHORIZATION-003 and read them with the reader of 2026-08-23. The hardened
reader has moved a long way since -- the Cincinnati free-lane findings, the
Grand Rapids weight-semantics ruling, the Detroit parser repairs, the
label/value boundary work -- and none of those improvements has ever seen these
pages.

This replays them OFFLINE. Every byte comes from the gitignored capture tree
this market already owns; there is no provider call, no re-fetch and no spend.

WHAT IT REPORTS AND WHAT IT REFUSES TO DO
-------------------------------------------
It reports only. Phase 10 of the order is explicit: nothing the replay newly
discovers may be applied as authority unless it corresponds to one of the 32
already-signed founder decisions. A reader improvement is not a founder
decision, and a record published from one would be authority nobody signed. So
anything new lands in the exceptions list for a future clean-candidate packet.

THE LOCATOR HAS TO BE THE STATIC ONE
--------------------------------------
PTF-CANONICAL-POLICY-LOCATOR-PARITY-019 established that the in-page walk and
the static walk are DIFFERENT ALGORITHMS, not two implementations of one. These
artifacts are files, so the static entry point ``locate_policy_in_html`` is the
honest one to replay through; reporting a live-DOM result over a file would be
comparing a reading to something that never ran.

EVERY PAGE IS RE-HASHED BEFORE IT IS READ
-------------------------------------------
An artifact whose SHA-256 no longer matches the journal is reported as
CORPUS_DRIFT and read anyway, but its findings are quarantined: a reading over
bytes the founder's signature does not name proves nothing about this market.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
import sys
from collections import Counter, OrderedDict
from pathlib import Path
from typing import Dict, List, Optional

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.brightdata import policy_reading as PR      # noqa: E402
from scripts.pettripfinder.brightdata import unlocker_capture as UC    # noqa: E402
from scripts.pettripfinder.pittsburgh_hardened_sync_004 import (       # noqa: E402
    AS_OF, MARKET_ID, OBSERVATIONS, PACKAGE, REPORTS, WORK_ORDER, _load, _write)

CORPUS = (_REPO_ROOT / "data" / "acquisition"
          / "pittsburgh_pa_factory_recensus_001" / "pass1")
SOURCE_OF_RECORD = (r"C:\Atlas-Grok-Pittsburgh-Revalidate\atlas-dashboard"
                    r"\data\acquisition\pittsburgh_pa_factory_recensus_001")
REPORT = REPORTS / "pittsburgh_hardened_sync_004_reader_replay.json"


class ReplayError(RuntimeError):
    pass


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _rows() -> List[Dict]:
    journal = CORPUS / "journal.jsonl"
    if not journal.is_file():
        raise ReplayError(
            "the capture corpus is not materialised at %s -- Phase 3 of the "
            "order stops here rather than reacquiring it" % CORPUS)
    return [json.loads(line) for line in
            journal.read_text(encoding="utf-8").splitlines() if line.strip()]


def _artifact(row: Dict) -> Optional[Path]:
    """The row's rendered page, re-rooted from the source-of-record path.

    ``declined_dir`` is searched as well as ``artifact_dir``. A declined
    capture is where a hardened reader has the most to say: the page was
    fetched and kept, and only the reader of the day declined to read a policy
    off it. Skipping those would replay only the rows that already succeeded.
    """
    for field in ("artifact_dir", "declined_dir"):
        raw = str(row.get(field) or "")
        if not raw:
            continue
        tail = raw.replace(SOURCE_OF_RECORD, "").replace("\\", "/").lstrip("/")
        page = CORPUS.parent / tail / "rendered.html"
        if page.is_file():
            return page
        # A declined attempt may hold the page one level down, under the
        # attempt directory the escalation actually wrote.
        base = CORPUS.parent / tail
        if base.is_dir():
            found = sorted(base.glob("*/rendered.html")) or sorted(
                base.glob("rendered.html"))
            if found:
                return found[-1]
    return None


def replay() -> Dict:
    rows = _rows()
    observed = {r["identity_key"]: r for r in _load(OBSERVATIONS)["records"]}
    published = {h["identity_key"]: h
                 for h in _load(PACKAGE)["hotels"]}

    findings: List[Dict] = []
    counts: Counter = Counter()
    for row in rows:
        page = _artifact(row)
        if page is None:
            counts["no_owned_page"] += 1
            continue
        key = row["identity_key"]
        digest = _sha256(page)
        # Drift is only a claim the journal can support. A DECLINED capture was
        # never hashed at the time (43 of the 92 rows carry a content_hash, and
        # every one of them is an artifact_dir row), so comparing its bytes to
        # an empty string would report 23 corruptions that never happened.
        committed = str(row.get("content_hash") or "")
        drift = bool(committed) and digest != committed
        unhashed = not committed
        html = page.read_text(encoding="utf-8", errors="replace")
        hit = UC.locate_policy_in_html(html)
        if not hit.found:
            counts["POLICY_NOT_FOUND"] += 1
            reading = None
            extraction: Dict = {}
            withheld: Dict = {}
            flags: List[Dict] = []
        else:
            reading = PR.parse(hit.text, strategy="static_html_walk")
            result = PR.to_extraction(reading, location="static_html_walk")
            extraction = dict(result.extraction or {})
            withheld = dict(result.withheld or {})
            flags = [dict(f) for f in (result.flags or ())]
            counts["READ"] += 1

        before = (observed.get(key) or {}).get("observation", {}).get("extraction")
        pets_now = extraction.get("pets_allowed")
        pets_before = (before or {}).get("pets_allowed")

        # A DISAGREEMENT is only when both readers stated a verdict and the
        # verdicts differ. An observation whose extraction is EMPTY is not a
        # verdict of "no pets" -- it is the 2026-08-23 reader having read
        # nothing at all -- so the hardened reader finding a policy there is a
        # RECOVERY, and calling it a disagreement would report a contradiction
        # that does not exist.
        if before is None and pets_now is True:
            state = "NEW_PET_FRIENDLY_CANDIDATE"
        elif before is None and pets_now is False:
            state = "NEW_VERIFIED_NO_PETS_CANDIDATE"
        elif before is None:
            state = "STILL_UNREAD"
        elif pets_now == pets_before and json.dumps(
                extraction, sort_keys=True) == json.dumps(before, sort_keys=True):
            state = "UNCHANGED"
        elif pets_now == pets_before:
            state = "SAME_VERDICT_RICHER_READING"
        elif pets_before is None and pets_now is not None:
            state = "READER_RECOVERED_A_BLOCK_THE_OLD_READER_MISSED"
        elif pets_now is None:
            state = "READER_LOST_THE_BLOCK"
        else:
            state = "READER_DISAGREEMENT"
        counts[state] += 1
        if drift:
            counts["CORPUS_DRIFT"] += 1
        if unhashed:
            counts["unhashed_declined_capture"] += 1

        if state in ("UNCHANGED", "STILL_UNREAD"):
            continue
        findings.append(OrderedDict((
            ("identity_key", key),
            ("canonical_name", row.get("canonical_name")),
            ("brand", row.get("brand")),
            ("state", state),
            ("already_published", key in published),
            ("corpus_drift", drift),
            ("journal_stated_a_hash", not unhashed),
            ("committed_outcome", row.get("outcome")),
            ("pets_allowed_before", pets_before),
            ("pets_allowed_now", pets_now),
            ("extraction_before", before),
            ("extraction_now", extraction),
            ("withheld_now", withheld),
            ("flags_now", flags),
            ("locator_strategy", hit.strategy),
            ("source_url", row.get("source_url")),
            ("artifact_sha256", digest),
        )))

    return OrderedDict((
        ("schema", "ptf-market-reader-replay/1.0"),
        ("work_order", WORK_ORDER),
        ("market_id", MARKET_ID),
        ("as_of", AS_OF),
        ("what_this_is",
         "The 67 pages Pittsburgh already owns, re-read offline through the "
         "CURRENT hardened reader and compared with the readings committed on "
         "2026-08-23."),
        ("provider_calls", 0),
        ("usd_spent", 0.0),
        ("corpus_path", CORPUS.as_posix()),
        ("corpus_source_of_record", SOURCE_OF_RECORD),
        ("journal_rows", len(rows)),
        ("pages_replayed", counts["READ"] + counts["POLICY_NOT_FOUND"]),
        ("counts", OrderedDict(sorted(counts.items()))),
        ("nothing_is_applied_here",
         "Phase 10 of PTF-PITTSBURGH-HARDENED-SYNC-004 forbids applying any "
         "reader-derived authority that does not correspond to one of the 32 "
         "already-signed founder decisions. Every row below is a candidate for "
         "a future founder packet, not authority."),
        ("count", len(findings)),
        ("findings", findings),
    ))


def run(write: bool) -> int:
    report = replay()
    print("journal rows     : %d" % report["journal_rows"])
    print("pages replayed   : %d" % report["pages_replayed"])
    print("provider calls   : %d" % report["provider_calls"])
    print("spend            : $%.2f" % report["usd_spent"])
    for state, n in report["counts"].items():
        print("   %-32s %d" % (state, n))
    print("findings         : %d" % report["count"])
    if not write:
        print("(check only -- pass --write)")
        return 0
    _write(REPORT, report)
    print("WROTE %s" % REPORT.name)
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)
    try:
        return run(args.write)
    except ReplayError as exc:
        print("REFUSED: %s" % exc)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
