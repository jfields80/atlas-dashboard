"""PTF-AUSTIN-TX-HARDENED-SOURCE-READY-001 -- Phase 18: the attended-browser READ RECORDER.

WHY THIS EXISTS (THE PHOENIX FINDING, FIXED AT THE SOURCE)
---------------------------------------------------------
The Phoenix order transcribed each attended-browser read with a TYPED ``captured_at``; the typed clock drifted up to
three hours AHEAD of the wall clock on 275 of 286 reads and had to be clamped afterwards. The supported browser tool
(claude-in-chrome) returns no timestamp of its own, so this recorder stamps every read from the machine's real UTC
clock AT THE MOMENT IT IS RECORDED, which is immediately after the page was read -- an honest upper bound that can
never be in the future. No capture time is ever typed.

Each call appends one or more reads (a JSON object or a JSON array, from a file) to
``markets/staging/austin-tx/raw_captures/browser_reads_001.jsonl`` with the next sequence number, the recording
clock, and the fixed capture-method statement. A read that carries its own ``captured_at`` is refused.

Usage:
  python -m scripts.pettripfinder.austin_tx_browser_recorder_001 <reads.json>
"""
from __future__ import annotations

import json
import os
import sys
import time
from collections import OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
READS = os.path.join(_DASH, "launch_packages", "pettripfinder", "markets", "staging", "austin-tx", "raw_captures",
                     "browser_reads_001.jsonl")
METHOD = "claude-in-chrome navigate + page text / accessibility-tree find (no JS exfiltration, no relay, no bypass)"
FIELDS = ("family", "property_code", "requested_url", "final_url", "page_title", "page_address_line",
          "census_street", "census_postal", "full_premises_match", "read_outcome", "operative_quote", "parsed",
          "source_class", "note", "hilton_template", "preopening_statement", "closure_statement")


def _next_seq():
    if not os.path.exists(READS):
        return 1
    last = 0
    with open(READS, encoding="utf-8") as fh:
        for line in fh:
            if line.strip():
                last = max(last, int(json.loads(line).get("seq") or 0))
    return last + 1


def record(reads):
    os.makedirs(os.path.dirname(READS), exist_ok=True)
    seq = _next_seq()
    out = []
    for r in reads:
        if r.get("captured_at"):
            raise SystemExit("a read carries a typed captured_at; the recorder stamps the real clock")
        rec = OrderedDict([("seq", seq)])
        for k in FIELDS[:4]:
            rec[k] = r.get(k, "" if k != "full_premises_match" else None)
        rec["capture_method"] = METHOD
        rec["captured_at"] = time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())
        rec["captured_at_basis"] = "RECORDING_CLOCK_IMMEDIATELY_AFTER_THE_READ (never typed; an upper bound)"
        for k in FIELDS[4:]:
            if k in ("hilton_template", "preopening_statement", "closure_statement") and not r.get(k):
                continue
            rec[k] = r.get(k, None if k in ("full_premises_match",) else ({} if k == "parsed" else ""))
        if not rec.get("source_class"):
            rec["source_class"] = "BRAND_OWN_PROPERTY_PAGE"
        out.append(rec)
        seq += 1
    with open(READS, "a", encoding="utf-8", newline="\n") as fh:
        for rec in out:
            fh.write(json.dumps(rec, ensure_ascii=False) + "\n")
    return out


def main(argv=None):
    argv = argv if argv is not None else sys.argv[1:]
    data = json.load(open(argv[0], encoding="utf-8"))
    reads = data if isinstance(data, list) else [data]
    for rec in record(reads):
        print(rec["seq"], rec["captured_at"], rec["family"], rec["property_code"], rec["read_outcome"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
