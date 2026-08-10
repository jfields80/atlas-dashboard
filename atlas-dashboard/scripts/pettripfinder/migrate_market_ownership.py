"""PTF-MULTI-MARKET-INVENTORY-SCOPING-001 -- one-time Columbus ownership migration.

Adds the ``market_id`` column to the seed inventory and assigns every existing
row to ``columbus-oh``, then proves the assignment rather than asserting it.

Why every row and not only the corridor-assigned ones: ownership is not
corridor membership. Twelve published Columbus hotels belong to no corridor at
all and must stay published, so the migration reads the existing Columbus
identity universe -- the inventory file itself -- and never a corridor.

Why this is safe to run mechanically: the seed CSV is single-market today. The
audit below proves that before writing -- every row is an Ohio row, and no row's
identity is claimed by another market's committed census -- and refuses if
anything does not fit. It is idempotent: a row already carrying ownership is
left exactly as it is.

Run:  python -m scripts.pettripfinder.migrate_market_ownership [--apply]
"""

from __future__ import annotations

import csv
import io
import json
import sys
from collections import OrderedDict
from pathlib import Path
from typing import Dict, List

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.market_ownership import (            # noqa: E402
    MARKET_ID_FIELD, MarketOwnershipError, ownership_summary,
    registered_market_ids, validate_ownership,
)
from scripts.pettripfinder.markets import load_markets, market_by_id  # noqa: E402
from scripts.pettripfinder.site_data import PRODUCTION_CSV, normalize_name  # noqa: E402

COLUMBUS = "columbus-oh"


def _read_rows() -> List[Dict[str, str]]:
    with PRODUCTION_CSV.open(encoding="utf-8", newline="") as fh:
        reader = csv.DictReader(fh)
        return list(reader), list(reader.fieldnames or [])


def _other_market_identities() -> Dict[str, str]:
    """Identity keys already claimed by a market that is NOT Columbus.

    Read from the committed identity censuses, which are the only place a
    non-Columbus identity universe currently exists. This is the check that
    actually matters for the migration: not "does this row look like Columbus"
    but "is this row already known to belong to somebody else".
    """
    out: Dict[str, str] = {}
    census_dir = PRODUCTION_CSV.parent / "identity_census"
    if not census_dir.is_dir():
        return out
    for path in sorted(census_dir.glob("*.json")):
        blob = json.loads(path.read_text(encoding="utf-8-sig"))
        market_id = str(blob.get("market_id") or path.stem)
        if market_id == COLUMBUS:
            continue
        for hotel in blob.get("hotels", []):
            key = hotel.get("normalized_name") or normalize_name(hotel.get("canonical_name", ""))
            if key:
                out[key] = market_id
    return out


def audit(rows: List[Dict[str, str]]) -> OrderedDict:
    """Prove the inventory really is single-market before claiming it is.

    Two blocking checks, and deliberately NOT a geographic one:

      * every row is an Ohio row
      * no row's identity is already claimed by another market's census

    A city-based check was tried first and was wrong. Ten Columbus rows sit in
    cities no Columbus corridor lists -- Westerville, New Albany, Gahanna,
    Canal Winchester, and four metro parks -- because corridors do not cover
    the market exhaustively. Rejecting those rows would have re-created the
    exact defect this work order exists to remove: inferring ownership from
    corridor geography. Their city spread is reported below as information,
    never as a blocker.
    """
    out_of_state = [r["name"] for r in rows if (r.get("state") or "").strip().upper() != "OH"]

    foreign = _other_market_identities()
    claimed_elsewhere = sorted(
        "%s -> %s" % (r.get("name", ""), foreign[normalize_name(r.get("name", ""))])
        for r in rows if normalize_name(r.get("name", "")) in foreign)

    market = market_by_id(load_markets(), COLUMBUS)
    corridor_cities = {market.primary_city.strip().lower()}
    for corridor in market.corridors:
        corridor_cities.update(c.strip().lower() for c in corridor.included_cities)
    outside_corridor_geography = sorted(
        {"%s (%s)" % (r.get("name", ""), r.get("city", "")) for r in rows
         if (r.get("city") or "").strip().lower() not in corridor_cities})

    already = [r["name"] for r in rows if (r.get(MARKET_ID_FIELD) or "").strip()]
    dupes: Dict[str, int] = {}
    for r in rows:
        key = normalize_name(r.get("name", ""))
        dupes[key] = dupes.get(key, 0) + 1

    return OrderedDict([
        ("total_rows", len(rows)),
        ("by_category", ownership_summary([{MARKET_ID_FIELD: r.get("category", "")}
                                           for r in rows])),
        ("out_of_state_rows", out_of_state),
        ("identities_claimed_by_another_market", claimed_elsewhere),
        ("other_market_identities_checked_against", len(foreign)),
        ("informational_rows_outside_corridor_geography", outside_corridor_geography),
        ("rows_already_owned", already),
        ("duplicate_identity_keys", {k: v for k, v in dupes.items() if v > 1}),
    ])


def migrate(*, apply: bool = False) -> int:
    rows, fieldnames = _read_rows()
    report = audit(rows)

    blocking = (report["out_of_state_rows"]
                or report["identities_claimed_by_another_market"]
                or report["duplicate_identity_keys"])
    if blocking:
        print("REFUSING to migrate -- inventory is not provably single-market:")
        print(json.dumps(report, indent=1))
        return 1

    if MARKET_ID_FIELD not in fieldnames:
        fieldnames = list(fieldnames) + [MARKET_ID_FIELD]
    migrated = 0
    for row in rows:
        if not (row.get(MARKET_ID_FIELD) or "").strip():
            row[MARKET_ID_FIELD] = COLUMBUS
            migrated += 1

    # Post-conditions, checked on the in-memory result before anything is
    # written: the ownership contract itself must accept the migrated rows.
    validate_ownership(rows, registered=registered_market_ids(),
                       context="migrated seed inventory")
    assert all(r[MARKET_ID_FIELD] == COLUMBUS for r in rows)

    if apply:
        buf = io.StringIO(newline="")
        writer = csv.DictWriter(buf, fieldnames=fieldnames, lineterminator="\n")
        writer.writeheader()
        for row in rows:
            writer.writerow(row)
        PRODUCTION_CSV.write_text(buf.getvalue(), encoding="utf-8", newline="")

    print("=== COLUMBUS MARKET-OWNERSHIP MIGRATION ===")
    print("  inventory rows        :", report["total_rows"])
    print("  rows migrated         :", migrated)
    print("  already owned         :", len(report["rows_already_owned"]))
    print("  ownership after       :", ownership_summary(rows))
    print("  out-of-state rows     :", len(report["out_of_state_rows"]))
    print("  claimed by another mkt:", len(report["identities_claimed_by_another_market"]),
          "(checked against %d foreign identities)" % report["other_market_identities_checked_against"])
    print("  outside corridor geo  :", len(report["informational_rows_outside_corridor_geography"]),
          "(informational -- ownership is NOT corridor-derived)")
    print("  duplicate identities  :", len(report["duplicate_identity_keys"]))
    print("  mode                  :", "APPLIED" if apply else "DRY RUN")
    return 0


if __name__ == "__main__":
    raise SystemExit(migrate(apply="--apply" in sys.argv))
