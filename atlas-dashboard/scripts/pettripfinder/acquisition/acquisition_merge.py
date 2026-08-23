"""Fold several acquisition passes into one current-state view of a market.

    python scripts/pettripfinder/acquisition/acquisition_merge.py \
      --market st-louis-mo --out <merged.json> \
      --pass <direct_http_pilot.json> --pass <paid_acquisition.json>

WHY A MARKET NEEDS THIS AT ALL
------------------------------
The observation store, the closure ledger and the founder-review builder each
take ONE acquisition report and ask it what happened to each identity. That was
true while a market had one pass. It stops being true the moment a second pass
runs, and the wrong answers it produces are quiet ones: a property acquired by
the paid lane still reads UNHYDRATED from the free lane's report, and closure
reports ACCESS_UNRESOLVED for a hotel whose policy is already on disk.

So the passes are folded FIRST, into one row per identity, and the downstream
modules keep taking exactly one report.

WHICH PASS WINS
---------------
Later passes are listed later and win by default -- a second look is a better
look. But not unconditionally: an EVIDENCE-BEARING outcome is never overwritten
by one that carries no evidence.

    VALID > POLICY_NOT_FOUND | IDENTITY_MISMATCH > everything else

A page that served and was read outranks a later 403, because the 403 does not
un-read the policy already on disk. A page that served and was silent, or that
served and was another hotel, outranks a later failure to connect for the same
reason: both are findings about the property, and a transport failure is a
finding about us. Within one rank the later pass wins, which is what makes a
re-run an update rather than an argument.

Every superseded row is kept in ``superseded`` with the rule that displaced it,
so any merged row can be traced back to the pass it came from.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, OrderedDict
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.brightdata import outcomes as O  # noqa: E402

SCHEMA = "ptf-acquisition-merged/1.0"

#: Higher wins. Ties go to the later pass. See the module docstring.
EVIDENCE_RANK: Dict[str, int] = {
    O.VALID: 3,
    O.POLICY_NOT_FOUND: 2,
    O.IDENTITY_MISMATCH: 2,
}
DEFAULT_RANK = 1


def rank_of(outcome: str) -> int:
    return EVIDENCE_RANK.get(outcome, DEFAULT_RANK)


def merge(passes: Sequence[Tuple[str, Mapping]]) -> Tuple[List[Dict], List[Dict]]:
    """``(rows, superseded)`` -- one row per identity, worst case unchanged.

    ``passes`` is ``(label, document)`` in the order they ran.
    """
    chosen: "OrderedDict[str, Dict]" = OrderedDict()
    superseded: List[Dict] = []
    for label, document in passes:
        for result in (document.get("results") or ()):
            key = result["identity_key"]
            row = dict(result)
            row["acquisition_pass"] = label
            previous = chosen.get(key)
            if previous is None:
                chosen[key] = row
                continue
            new_rank, old_rank = rank_of(row["outcome"]), rank_of(previous["outcome"])
            if new_rank >= old_rank:
                loser, winner, why = previous, row, (
                    "a later pass with an outcome at least as evidence-bearing"
                    if new_rank == old_rank else
                    "a later pass returned a more evidence-bearing outcome")
            else:
                loser, winner, why = row, previous, (
                    "the earlier pass holds evidence this one does not; a "
                    "transport failure does not un-read a policy already on disk")
            chosen[key] = winner
            superseded.append(OrderedDict((
                ("identity_key", key),
                ("kept_pass", winner["acquisition_pass"]),
                ("kept_outcome", winner["outcome"]),
                ("dropped_pass", loser["acquisition_pass"]),
                ("dropped_outcome", loser["outcome"]),
                ("why", why),
            )))
    rows = sorted(chosen.values(), key=lambda r: r["identity_key"])
    return (rows, superseded)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--market", required=True)
    parser.add_argument("--out", required=True)
    parser.add_argument("--work-order", default="")
    parser.add_argument("--pass", dest="passes", action="append", required=True,
                        help="an acquisition report, earliest first")
    args = parser.parse_args(argv)

    loaded: List[Tuple[str, Mapping]] = []
    for path in args.passes:
        document = json.loads(Path(path).read_text(encoding="utf-8"))
        loaded.append((Path(path).name, document))

    rows, superseded = merge(loaded)
    outcomes = Counter(r["outcome"] for r in rows)
    by_pass = Counter(r["acquisition_pass"] for r in rows)

    # Everything below makes the merged document a DROP-IN for a single pilot
    # report. The benchmark reads a lane name, a per-brand outcome table and
    # the brands a lane was measured to refuse; if this document omitted them
    # the benchmark would either crash or quietly report a market's acquisition
    # as though only its last pass had happened.
    by_brand: "OrderedDict[str, Counter]" = OrderedDict()
    for row in rows:
        brand = row.get("brand", "")
        family = "INDEPENDENT" if brand.startswith("INDEP:") else brand
        by_brand.setdefault(family, Counter())[row["outcome"]] += 1
    lanes = sorted({r.get("provider", "") for r in rows if r.get("provider")}
                   or {d.get("provider", "") for _l, d in loaded
                       if d.get("provider")})
    refused: "OrderedDict[str, str]" = OrderedDict()
    skipped: List[Dict] = []
    for label, document_in in loaded:
        for brand, why in (document_in.get("lane_refused_brands") or {}).items():
            refused["%s (%s)" % (brand, label)] = why
        skipped.extend(document_in.get("skipped_lane_refused") or ())

    document = OrderedDict((
        ("schema", SCHEMA),
        ("what_this_is",
         "Every acquisition pass over one market, folded to one row per "
         "identity. Shaped as an acquisition report so the observation store, "
         "the closure ledger and the founder-review builder keep taking "
         "exactly one input."),
        ("market_id", args.market),
        ("work_order", args.work_order),
        ("passes", [OrderedDict((("label", label),
                                 ("schema", doc.get("schema", "")),
                                 ("work_order", doc.get("work_order", "")),
                                 ("results", len(doc.get("results") or ()))))
                    for label, doc in loaded]),
        ("precedence_rule",
         "later pass wins at equal evidence rank; VALID > POLICY_NOT_FOUND | "
         "IDENTITY_MISMATCH > everything else, so a transport failure never "
         "overwrites a page that served"),
        ("identities", len(rows)),
        # Pilot-compatible fields, so one merged view feeds every reader.
        ("provider", ", ".join(lanes)),
        ("lanes", lanes),
        ("attempted", len(rows)),
        ("valid", outcomes.get(O.VALID, 0)),
        ("outcome_counts", OrderedDict(sorted(outcomes.items()))),
        ("outcomes_by_brand", OrderedDict(
            (brand, OrderedDict(sorted(counts.items())))
            for brand, counts in sorted(by_brand.items()))),
        ("lane_refused_brands", refused),
        ("skipped_lane_refused", skipped),
        ("rows_by_pass", OrderedDict(sorted(by_pass.items()))),
        ("superseded", superseded),
        ("results", rows),
    ))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(document, indent=1, ensure_ascii=False) + "\n",
                   encoding="utf-8", newline="\n")
    print("identities : %d" % len(rows))
    print("outcomes   : %s" % dict(document["outcome_counts"]))
    print("by pass    : %s" % dict(document["rows_by_pass"]))
    print("superseded : %d" % len(superseded))
    print("written    : %s" % out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
