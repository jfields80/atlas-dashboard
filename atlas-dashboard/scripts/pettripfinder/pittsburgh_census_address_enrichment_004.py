# -*- coding: utf-8 -*-
"""PTF-PITTSBURGH-HARDENED-SYNC-004 Phase 7a -- fill the street address the seed row needs.

    python -m scripts.pettripfinder.pittsburgh_census_address_enrichment_004
    python -m scripts.pettripfinder.pittsburgh_census_address_enrichment_004 --write

WHY THIS RUNS AT ALL
---------------------
Pittsburgh's registered census carries a street address for 59 of its 96
identities. Ten of the identities this order publishes or excludes are among the
other 37, and both consumers refuse them:

  * ``market_authority.load_market_seed_rows`` -> the seed row is INVENTORY, and
    an addressless seed row is what the importer refuses.
  * ``hotel_exclusions.validate`` -> ``address`` is in REQUIRED_FIELDS and must
    be non-blank after strip().

So without this, ten founder-signed dispositions cannot be applied for want of a
field nobody disputes -- the Detroit lesson (PTF-DETROIT-FOUNDER-REVIEW-
AUTHORITY-011) that a row can pass every POLICY gate and still be unpublishable.
The difference here is that Detroit's rows had no address ANYWHERE. Pittsburgh's
are stated on each property's own captured page, which this market already owns.

WHAT THIS IS, AND WHAT IT IS EXPLICITLY NOT
---------------------------------------------
It is an ADD-ONLY field completion on identities the census ALREADY HAS.

  * No identity is added, removed, renamed, superseded or downgraded.
  * The row count stays 96 and the schema stays ptf-market-identity-census/1.1,
    which is exactly what the release contract pins -- the contract binds this
    census by COUNT and SCHEMA, not by hash, so no pin lapses.
  * A non-empty address is NEVER overwritten. The run refuses rather than
    replace one, because disagreeing with a committed address is an identity
    question and belongs to the founder.

It is therefore NOT the census promotion Phase 4 of this order reserves for a
separate SUPERSEDE / ADD-NEVER-DOWNGRADE work order. That reservation is about
the 115-row shadow recensus, which this run does not promote, read as authority,
or bring one identity of into the registered census.

WHERE EACH ADDRESS COMES FROM
------------------------------
Only from the identity's OWN bound first-party evidence, in this order:

  1. ``observation.identity_check.address_on_page`` -- the address printed on
     the property page whose SHA-256 the founder's signature names.
  2. the shadow recensus row's ``address`` for the same reconciled identity,
     which discovery read off that same page.

Both are the property stating its own street. Nothing is geocoded, inferred from
a name, or copied from a sibling property. Every fill is written to a ledger with
its source and the observation that carries it, so any one of them can be checked
or reverted on its own.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import OrderedDict
from pathlib import Path
from typing import Dict, List, Mapping

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.contracts import census as CENSUS_CONTRACT  # noqa: E402
from scripts.pettripfinder.pittsburgh_hardened_sync_004 import (       # noqa: E402
    CENSUS, OBSERVATIONS, RECENSUS, REPORTS, WORK_ORDER, AS_OF, _load, _write,
    reconcile)

LEDGER = REPORTS / "pittsburgh_hardened_sync_004_census_address_fills.json"


class EnrichmentError(RuntimeError):
    pass


def _clean(value: object) -> str:
    return str(value or "").strip()


def plan() -> Dict:
    census = _load(CENSUS)
    if len(census["hotels"]) != 96:
        raise EnrichmentError("the registered census is %d rows, not 96"
                              % len(census["hotels"]))
    shadow = {h["identity_key"]: h for h in _load(RECENSUS)["hotels"]}
    obs = {r["identity_key"]: r for r in _load(OBSERVATIONS)["records"]}
    rows = {r["registered_identity_key"]: r
            for r in reconcile()["rows"] if r["registered_identity_key"]}

    fills: List[Dict] = []
    for hotel in census["hotels"]:
        key = hotel["identity_key"]
        row = rows.get(key)
        if row is None or _clean(hotel.get("address")):
            continue
        signed_key = row["signed_identity_key"]
        record = obs.get(signed_key) or {}
        check = ((record.get("observation") or {}).get("identity_check") or {})
        address = _clean(check.get("address_on_page"))
        source = "observation.identity_check.address_on_page"
        if not address:
            address = _clean((shadow.get(signed_key) or {}).get("address"))
            source = "recensus row address (read from the same property page)"
        if not address:
            continue
        snapshot = ((record.get("observation") or {}).get("snapshot_hash")
                    or row.get("bound_snapshot_hash"))
        fills.append(OrderedDict((
            ("identity_key", key),
            ("canonical_name", hotel.get("canonical_name")),
            ("address_filled", address),
            ("source", source),
            ("observed_from_identity", signed_key),
            ("source_url", (record.get("observation") or {}).get("source_url")
             or row.get("bound_source_url")),
            ("bound_snapshot_hash", snapshot),
        )))
    return OrderedDict((("census", census), ("fills", fills)))


def apply_fills(census: Mapping, fills) -> Dict:
    by_key = {f["identity_key"]: f for f in fills}
    out = json.loads(json.dumps(census))
    for hotel in out["hotels"]:
        fill = by_key.get(hotel["identity_key"])
        if fill is None:
            continue
        if _clean(hotel.get("address")):
            raise EnrichmentError(
                "%s already carries an address; this run is ADD-ONLY and "
                "disagreeing with a committed address is a founder question"
                % hotel["identity_key"])
        hotel["address"] = fill["address_filled"]
    return out


def run(write: bool) -> int:
    planned = plan()
    census, fills = planned["census"], planned["fills"]
    print("census rows            : %d" % len(census["hotels"]))
    print("addresses before       : %d"
          % sum(1 for h in census["hotels"] if _clean(h.get("address"))))
    print("addresses this fills   : %d" % len(fills))
    for fill in fills:
        print("   %-46s %s" % (fill["identity_key"][:45], fill["address_filled"]))
    filled = apply_fills(census, fills)
    if len(filled["hotels"]) != len(census["hotels"]):
        raise EnrichmentError("the row count moved")
    issues = CENSUS_CONTRACT.validate(filled)
    if issues:
        raise EnrichmentError("the filled census does not validate: %s"
                              % list(issues)[:5])
    print("addresses after        : %d"
          % sum(1 for h in filled["hotels"] if _clean(h.get("address"))))
    print("census contract issues : %d" % len(issues))
    if not write:
        print("(check only -- pass --write)")
        return 0

    _write(CENSUS, filled)
    print("WROTE %s" % CENSUS.name)
    _write(LEDGER, OrderedDict((
        ("schema", "ptf-census-field-completion/1.0"),
        ("work_order", WORK_ORDER),
        ("market_id", census["market_id"]),
        ("as_of", AS_OF),
        ("what_this_is",
         "Street addresses filled on identities the registered census already "
         "held, each read from that identity's own bound first-party page. "
         "ADD-ONLY: no identity added, removed, renamed or superseded, and no "
         "committed address replaced. The row count and schema are unchanged, "
         "so the release contract's census pin does not lapse."),
        ("not_a_census_promotion",
         "The 115-row shadow recensus is neither promoted nor read as "
         "authority here. It supplies a street the property prints on the very "
         "page the founder's signature already names."),
        ("rows_before", len(census["hotels"])),
        ("rows_after", len(filled["hotels"])),
        ("count", len(fills)),
        ("fills", fills),
    )))
    print("WROTE %s" % LEDGER.name)
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)
    try:
        return run(args.write)
    except EnrichmentError as exc:
        print("REFUSED: %s" % exc)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
