"""PTF-ST-LOUIS-MARKET-001 -- what the persisted evidence already contains.

Before any repeated network acquisition, ask the documents already on disk
whether they were read as well as they could be. Zero network. Zero spend.

TWO QUESTIONS, ASKED OF DECLINED EVIDENCE ONLY
----------------------------------------------
1. **Is the document richer than the block the locator bounded?**
   PTF-MILWAUKEE-LOCATOR-RECOVERY-032 established that a located block can be
   poorer than its own document. Here the case is sharper: the capture found NO
   block at all and recorded POLICY_NOT_FOUND. If the document text, read with
   every tag stripped -- including the contents of ``<script>`` and
   ``<noscript>``, which the painted-text walk removes -- does contain a
   bounded policy block, then the page was never silent and the closure
   disposition is wrong.

2. **Did we reach a page that names a DIFFERENT property?**
   For an IDENTITY_MISMATCH the document is somebody's page, just not this
   property's. Recording which one is what turns a dead end into a routing
   repair.

NOTHING HERE PRODUCES AN OBSERVATION
------------------------------------
A block recovered from inside a ``<script>`` payload is not what the page says
to a guest, and it is not automatically the property's own policy either -- a
brand bundle carries every property's template. So a recovery is REPORTED, with
its text, for a human to accept or refuse. The declined capture stays declined,
which is the rule ``declined_capture`` is built on.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, OrderedDict
from pathlib import Path
from typing import Dict, List, Mapping, Optional

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.brightdata import declined_capture as DECLINED
from scripts.pettripfinder.brightdata import marriott_surface as MS
from scripts.pettripfinder.brightdata import policy_reading as PR
from scripts.pettripfinder.brightdata import unlocker_capture as UC

SCHEMA = "ptf-zero-cost-recovery/1.0"

RECOVERED_RICHER_DOCUMENT = "RECOVERED_BLOCK_IN_A_DOCUMENT_THE_WALK_DID_NOT_READ"
NO_RECOVERY = "NO_RECOVERY_THE_DOCUMENT_IS_AS_SILENT_AS_THE_BLOCK"
WRONG_PROPERTY_NAMED = "DOCUMENT_NAMES_A_DIFFERENT_PROPERTY"

_TAG = re.compile(r"<[^>]+>")


def full_document_text(html: str) -> str:
    """Every character the document contains, tags removed and nothing else.

    Deliberately NOT the painted text. ``unlocker_capture.html_to_text`` drops
    ``<script>``, ``<style>`` and ``<noscript>`` bodies, which is right for
    reading what a guest sees and wrong for asking what the document HOLDS.
    """
    return MS.collapse(_TAG.sub(" ", html or ""))


def examine(directory: Path) -> Optional[Dict]:
    """One declined directory -> what its document turns out to contain."""
    manifest = DECLINED.read(directory)
    if manifest is None:
        return None
    document_path = directory / DECLINED.DOCUMENT_ARTIFACT
    if not document_path.is_file():
        return None
    html = document_path.read_text(encoding="utf-8", errors="replace")

    painted = UC.locate_policy_in_html(html)
    whole = UC.locate_policy_in_text(full_document_text(html))

    entry = OrderedDict((
        ("declined_directory", str(directory)),
        ("outcome", manifest.get("outcome", "")),
        ("requested_url", manifest.get("requested_url", "")),
        ("final_url", manifest.get("final_url", "")),
        ("title", manifest.get("title", "")),
        ("document_sha256", manifest.get("document_sha256", "")),
        ("painted_walk_found", bool(painted.found)),
        ("whole_document_found", bool(whole.found)),
    ))

    if manifest.get("outcome") == "IDENTITY_MISMATCH":
        entry["verdict"] = WRONG_PROPERTY_NAMED
        entry["why"] = ("the fetch reached a page that names a different "
                        "property; the document is kept so a routing repair "
                        "can start from what it actually served")
        entry["identity_reasons"] = list(
            (manifest.get("identity") or {}).get("reasons") or ())
        return entry

    if whole.found and not painted.found:
        reading = PR.parse(whole.text, strategy=whole.strategy)
        entry["verdict"] = RECOVERED_RICHER_DOCUMENT
        entry["why"] = ("the painted text carries no policy block but the "
                        "document does; the block below was never visible to "
                        "the walk that ran")
        entry["recovered_block"] = whole.text[:4000]
        entry["recovered_block_chars"] = len(whole.text)
        entry["reader_found_facts"] = bool(reading.found and (
            reading.pets_allowed is not None or reading.charges))
        entry["requires_human_acceptance"] = (
            "a block recovered from a part of the document the page never "
            "paints may be a brand template rather than this property's own "
            "statement; it is reported, never admitted")
        return entry

    entry["verdict"] = NO_RECOVERY
    entry["why"] = ("reading the whole document, script bodies included, finds "
                    "no policy block either; the silence is the page's own")
    return entry


def run(run_dir: Path) -> List[Dict]:
    entries: List[Dict] = []
    for directory in sorted(run_dir.glob("*/declined-*")):
        entry = examine(directory)
        if entry is not None:
            entries.append(entry)
    return entries


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--market", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)

    entries = run(Path(args.run_dir))
    verdicts = Counter(e["verdict"] for e in entries)
    document = OrderedDict((
        ("schema", SCHEMA),
        ("what_this_is",
         "Everything the persisted DECLINED evidence turns out to contain, "
         "asked offline before any repeated network acquisition. Nothing here "
         "is an observation and nothing here changes a capture's verdict."),
        ("market_id", args.market),
        ("work_order", "PTF-ST-LOUIS-MARKET-001"),
        ("network_calls", 0),
        ("usd_spent", 0.0),
        ("examined", len(entries)),
        ("verdict_counts", OrderedDict(sorted(verdicts.items()))),
        ("entries", entries),
    ))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(document, indent=1, ensure_ascii=False) + "\n",
                   encoding="utf-8", newline="\n")
    print("examined : %d declined captures" % len(entries))
    print("verdicts : %s" % dict(sorted(verdicts.items())))
    print("spend    : $0.00, network calls: 0")
    print("written  : %s" % out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
