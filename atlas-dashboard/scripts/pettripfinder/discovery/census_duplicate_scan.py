"""Which census identities might be the same building, asked before publication.

    python scripts/pettripfinder/discovery/census_duplicate_scan.py \
      --market louisville-ky --out launch_packages/pettripfinder/..._004.json \
      --candidates launch_packages/pettripfinder/..._founder_review_packet_003.json

A duplicate found at publication is found too late: by then two profiles carry
one building's policy, or one building's policy is split across two pages that
each look complete. The signals that would have said so are in the census the
whole time -- a street address, a telephone line, a source URL, a slug.

Nothing here merges anything. Sharing a signal is not being the same hotel, and
the two most common shapes prove it:

* a dual-brand building. Louisville's Hampton Inn and Home2 Suites are both at
  1150 Forest Bridge Road, and each page states its own Hilton property code and
  its own building letter. Two hotels, one address, no defect.
* a tower. The Galt House and Rivue Tower share 140 N 4th St and are one
  business with two names -- which IS a defect, and a different one.

So this reports groups and says which signal grouped them. A person decides.

Zero network. Zero spend.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, OrderedDict, defaultdict
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.discovery.census_url_recovery import (  # noqa: E402
    digits, street_key,
)

SCHEMA = "ptf-census-duplicate-scan/1.0"
CENSUS_DIR = _REPO_ROOT / "launch_packages" / "pettripfinder" / "identity_census"


def _url(row: Mapping) -> str:
    return (row.get("official_url") or "").strip().rstrip("/").lower()


SIGNALS = (
    ("STREET_AND_POSTAL_CODE",
     lambda row: street_key(row.get("address", ""), row.get("postal_code", "")),
     "two identities at one street address: a dual-brand building, a tower of "
     "one hotel, or one hotel entered twice"),
    ("TELEPHONE",
     lambda row: digits(row.get("phone", "")),
     "two identities on one telephone line: a shared switchboard or one hotel "
     "entered twice"),
    ("SOURCE_URL",
     lambda row: _url(row),
     "two identities claiming one page: at least one of them will carry another "
     "building's policy"),
    ("SLUG",
     lambda row: (row.get("slug") or "").strip().lower(),
     "two identities that would publish to one route"),
)


def scan(rows: Sequence[Mapping], candidates: Optional[set] = None) -> List[Dict]:
    groups: List[Dict] = []
    for name, key_of, why in SIGNALS:
        buckets: Dict[str, List[str]] = defaultdict(list)
        for row in rows:
            key = key_of(row)
            if key:
                buckets[key].append(row["identity_key"])
        for key, keys in sorted(buckets.items()):
            if len(keys) < 2:
                continue
            groups.append(OrderedDict((
                ("signal", name),
                ("value", key),
                ("identity_keys", sorted(keys)),
                ("size", len(keys)),
                ("includes_a_review_candidate",
                 bool(candidates) and any(k in candidates for k in keys)),
                ("why_it_matters", why),
            )))
    groups.sort(key=lambda g: (not g["includes_a_review_candidate"],
                               g["signal"], g["value"]))
    return groups


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--market", required=True)
    parser.add_argument("--candidates", default="",
                        help="a founder-review packet; groups touching a "
                             "candidate are reported first")
    parser.add_argument("--work-order", default="")
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)

    census = json.loads((CENSUS_DIR / ("%s.json" % args.market))
                        .read_text(encoding="utf-8-sig"))
    candidates = set()
    if args.candidates:
        packet = json.loads(Path(args.candidates).read_text(encoding="utf-8"))
        candidates = {c["identity_key"] for c in packet.get("candidates") or ()}

    groups = scan(census.get("hotels") or (), candidates)
    document = OrderedDict((
        ("schema", SCHEMA),
        ("what_this_is",
         "Census identities that share a signal strong enough that they might "
         "be one building. Nothing is merged and nothing is resolved; a person "
         "decides. Zero network, zero spend."),
        ("market_id", args.market),
        ("work_order", args.work_order),
        ("census_identities", census.get("count", len(census.get("hotels") or ()))),
        ("review_candidates", len(candidates)),
        ("groups_found", len(groups)),
        ("groups_touching_a_candidate",
         sum(1 for g in groups if g["includes_a_review_candidate"])),
        ("groups_by_signal", OrderedDict(
            sorted(Counter(g["signal"] for g in groups).items()))),
        ("groups", groups),
    ))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(document, indent=1, ensure_ascii=False) + "\n",
                   encoding="utf-8", newline="\n")
    print("census identities        : %d" % document["census_identities"])
    print("groups found             : %d" % len(groups))
    print("touching a candidate     : %d" % document["groups_touching_a_candidate"])
    for group in groups:
        print("  %-22s %-34s %s%s"
              % (group["signal"], str(group["value"])[:34],
                 group["identity_keys"],
                 "  <-- candidate" if group["includes_a_review_candidate"] else ""))
    print("written                  : %s" % out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
