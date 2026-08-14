"""PTF-GEOGRAPHY-NORMALIZATION-001 -- census geography, made reproducible.

Recomputes every census row's corridor assignment from its market's committed
configuration and writes back exactly three fields:

    corridor
    assignment_basis
    assignment_value

Nothing else is touched. This is a PATCH, not a rebuild.

Why that matters here specifically
----------------------------------
Phase C's census upgrader was initially written as a rebuild from a reduced
model, and it silently deleted every field the model did not name --
``normalized_name``, which Cleveland's partition generator joins on, and
Dayton's roll-up blocks. The data came back because it was in git; the lesson
is cheaper to keep than to relearn. So this module:

  * reads each row, changes three keys, and leaves the rest of the object as it
    found it -- including keys it has never heard of;
  * is idempotent, because it recomputes from the market config rather than
    from its own previous output;
  * refuses to write a basis it cannot prove against the corridor registry.

What it will not do
-------------------
It does not read hotel names. A property called "SpringHill Suites Columbus
Airport Gahanna" whose record states no city gets NO city -- the name is a
brand string, not evidence, and one Columbus identity genuinely has no stated
city. Where geography is missing, the row becomes ``unassigned``, which is a
legitimate published state and not a failure.

    python -m scripts.pettripfinder.normalize_census_geography
    python -m scripts.pettripfinder.normalize_census_geography --write
"""

from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

from scripts.pettripfinder.markets import assign_hotels, load_markets, market_by_id
from scripts.pettripfinder.markets.assignment import (
    TIER_CITY, TIER_EXPLICIT, TIER_UNASSIGNED, TIER_ZIP,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
PACKAGE_DIR = REPO_ROOT / "launch_packages" / "pettripfinder"
CENSUS_DIR = PACKAGE_DIR / "identity_census"

#: Only these three keys are ever written.
OWNED_FIELDS = ("corridor", "assignment_basis", "assignment_value")


class GeographyError(ValueError):
    """A basis that cannot be proved against the registry (fail closed)."""


def _row_for_assignment(row: Mapping) -> Dict:
    """The minimum an assignment needs, keyed the way the assigner expects.

    ``name`` carries the identity KEY rather than the display name: explicit
    corridor lists are keyed by identity, and the assigner normalises whatever
    it is handed. Passing the display name here would make an explicit list
    silently fail to match.
    """
    return {"name": row["identity_key"], "city": row.get("city", ""),
            "state": row.get("state", ""),
            "postal_code": row.get("postal_code", "")}


def verify_basis(corridor, basis: str, value: str, row: Mapping) -> None:
    """Prove the claimed basis really is what the registry supports."""
    if basis == TIER_ZIP:
        if value not in corridor.included_postal_codes:
            raise GeographyError(
                "%s claims postal_code %r but that ZIP is not in %s's registry"
                % (row["identity_key"], value, corridor.corridor_id))
    elif basis == TIER_CITY:
        city = (row.get("city") or "").strip().lower()
        if city not in tuple(c.lower() for c in corridor.included_cities):
            raise GeographyError(
                "%s claims city_state %r but that city is not in %s's registry"
                % (row["identity_key"], value, corridor.corridor_id))
        state = (row.get("state") or "").strip().upper()
        if corridor.state_code and state and corridor.state_code != state:
            raise GeographyError(
                "%s is in %s but %s is a %s corridor"
                % (row["identity_key"], state, corridor.corridor_id,
                   corridor.state_code))
    elif basis == TIER_EXPLICIT:
        if value not in corridor.explicit_hotel_ids:
            raise GeographyError(
                "%s claims an explicit assignment that %s does not list"
                % (row["identity_key"], corridor.corridor_id))


def recompute(market_id: str) -> Tuple[List[Dict], List[Dict]]:
    """``(rows, changes)`` -- the patched rows and what moved."""
    market = market_by_id(load_markets(), market_id)
    path = CENSUS_DIR / ("%s.json" % market_id)
    document = json.loads(path.read_text(encoding="utf-8-sig"),
                          object_pairs_hook=collections.OrderedDict)
    rows = document["hotels"]

    assignment = assign_hotels(
        market, [_row_for_assignment(r) for r in rows], fail_closed=False)
    conflicts = {c["hotel"] for c in assignment.conflicts}

    changes = []
    for row in rows:
        key = row["identity_key"]
        corridor_ids = assignment.corridor_of.get(key, ())
        basis, value = assignment.basis_of.get(key, (TIER_UNASSIGNED, ""))

        if key in conflicts:
            # Ambiguous between corridors that do not authorise sharing. The
            # honest answer is no corridor, not whichever matched first.
            corridor_id, basis, value = None, TIER_UNASSIGNED, ""
        elif corridor_ids:
            corridor_id = corridor_ids[0]
            verify_basis(market.corridor_by_id(corridor_id), basis, value, row)
        else:
            corridor_id, basis, value = None, TIER_UNASSIGNED, ""

        before = (row.get("corridor") or None, row.get("assignment_basis") or "",
                  row.get("assignment_value") or "")
        after = (corridor_id, basis, value)
        if before != after:
            changes.append({
                "market_id": market_id, "identity_key": key,
                "canonical_name": row.get("canonical_name", ""),
                "city": row.get("city", ""), "state": row.get("state", ""),
                "postal_code": row.get("postal_code", ""),
                "before_corridor": before[0], "before_basis": before[1],
                "after_corridor": after[0], "after_basis": after[1],
                "assignment_value": after[2],
            })
        # PATCH: exactly three keys, in place. Every other key on this row --
        # including ones this module has never heard of -- is left as found.
        row["corridor"] = corridor_id
        row["assignment_basis"] = basis
        row["assignment_value"] = value

    return document, changes


def write(market_id: str, document: Mapping) -> None:
    path = CENSUS_DIR / ("%s.json" % market_id)
    path.write_text(json.dumps(document, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8", newline="\n")


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)

    out = sys.stdout.write
    all_changes: List[Dict] = []
    for market in load_markets():
        if not (CENSUS_DIR / ("%s.json" % market.market_id)).is_file():
            continue
        document, changes = recompute(market.market_id)
        bases = collections.Counter(r.get("assignment_basis") for r in document["hotels"])
        out("%-28s rows=%3d changed=%3d  %s\n"
            % (market.market_id, len(document["hotels"]), len(changes), dict(bases)))
        all_changes.extend(changes)
        if args.write:
            write(market.market_id, document)
    out("\ntotal changed: %d\n" % len(all_changes))
    return 0


if __name__ == "__main__":                                # pragma: no cover
    raise SystemExit(main())
