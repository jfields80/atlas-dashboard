# -*- coding: utf-8 -*-
"""PTF-PITTSBURGH-FOUNDER-HOLD-RESOLUTION-005 Phases 4/9 -- add six proven identities.

    python -m scripts.pettripfinder.pittsburgh_census_add_005
    python -m scripts.pettripfinder.pittsburgh_census_add_005 --write

WHAT IS BEING ADDED, AND WHY IT IS NOT A PROMOTION
----------------------------------------------------
Six properties carry a founder signature from 2026-08-26 that
PTF-PITTSBURGH-HARDENED-SYNC-004 could not apply, because the identity each one
names is not in the registered 96. Sync 004 was right to refuse: "this has no
twin" and "this is provably a different building" are different claims, and
only the second may write a census row.

This run makes the second claim, per identity, and adds ONLY those six. The
115-row shadow recensus is not promoted, is not read as authority, and
contributes nothing but the first-party facts these six rows already state.
Every one of the other 109 shadow rows is untouched.

ADD, NEVER DOWNGRADE
---------------------
The census is rewritten as: all 96 existing rows byte-identical, then the new
rows appended. The run refuses if any prior identity_key is missing, if any
prior row's bytes move, or if the count does not land on exactly 96 + len(adds).
That is the SUPERSEDE / ADD-NEVER-DOWNGRADE discipline the sync order reserved
this work for; nothing here supersedes anything, so only the ADD half applies.

WHAT EACH ADD HAD TO PROVE
----------------------------
Re-checked here rather than trusted from the backlog report:

  * no registered identity collides on official URL, brand-scoped property
    code, street address or phone
  * no registered BARE STUB at the same postal has a name wholly contained in
    this candidate's -- that is the check that held back the seventh row,
    Courtyard West Homestead/Waterfront, which stays unapplied
  * no other market's seed row or exclusion claims the same URL, code, or
    street+phone
  * first-party address, phone, postal, city and current official URL present
  * a prior founder signature exists for THIS identity, and this run records
    which disposition it carried

InTown Suites is deliberately NOT here. Its identity re-located cleanly, but it
carries no prior founder signature on a Pittsburgh identity, so adding it would
be a new candidate rather than the application of signed work. It goes to a
future packet.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import OrderedDict
from pathlib import Path
from typing import Dict, List

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.contracts import census as CENSUS_CONTRACT     # noqa: E402
from scripts.pettripfinder.pittsburgh_hardened_sync_004 import (          # noqa: E402
    CENSUS, MARKET_ID, RECENSUS, REPORTS, _load, _write, signed_decisions)
from scripts.pettripfinder.pittsburgh_hold_resolution_005 import (        # noqa: E402
    CENSUS_ADD, build as build_backlog)

WORK_ORDER = "PTF-PITTSBURGH-FOUNDER-HOLD-RESOLUTION-005"
AS_OF = "2026-08-30"
LEDGER = REPORTS / "pittsburgh_hold_resolution_005_census_adds.json"

#: Carried from the census row a registered identity must have. Discovery-only
#: columns (coordinates, provider bookkeeping) are not part of the census
#: contract and are dropped rather than smuggled in.
CENSUS_FIELDS = (
    "identity_key", "canonical_name", "display_name", "slug", "market_id",
    "address", "city", "state", "postal_code", "phone", "identity_state",
    "lodging_state", "policy_state", "collision_state", "official_url",
    "corridor", "normalized_name", "observed_at", "provenance", "source",
    "source_id", "street_identity", "url_shape", "assignment_basis",
    "assignment_value", "disposition", "former_name",
)


class CensusAddError(RuntimeError):
    pass


def _street_identity(row: Dict) -> str:
    number = str(row.get("address") or "").strip().lower()
    postal = str(row.get("postal_code") or "").strip()
    return "%s|%s" % (number, postal) if number and postal else ""


def _census_row(shadow: Dict, template: Dict) -> Dict:
    out = OrderedDict()
    for field in CENSUS_FIELDS:
        if field in shadow:
            out[field] = shadow[field]
        elif field == "street_identity":
            out[field] = _street_identity(shadow)
        elif field == "url_shape":
            out[field] = "OFFICIAL_PROPERTY_PAGE" if shadow.get("official_url") else ""
        elif field in ("disposition", "former_name"):
            out[field] = ""
        else:
            out[field] = template.get(field, "")
    # The census records what discovery OBSERVED; policy lives in the policy
    # authority, so a freshly added row is never pre-resolved here.
    out["policy_state"] = "POLICY_NOT_VERIFIED"
    return out


def plan() -> Dict:
    backlog = build_backlog()
    adds = [r for r in backlog["unapplied"] if r["label"] == CENSUS_ADD]
    if not adds:
        raise CensusAddError("no TRUE_CENSUS_ADD rows to add")
    census = _load(CENSUS)
    existing = census["hotels"]
    if len(existing) != 96:
        raise CensusAddError("registered census is %d, not 96" % len(existing))
    shadow = {h["identity_key"]: h for h in _load(RECENSUS)["hotels"]}
    signed = signed_decisions()
    template = existing[0]

    rows, provenance = [], []
    keys = {h["identity_key"] for h in existing}
    for entry in adds:
        key = entry["signed_identity_key"]
        if key in keys:
            raise CensusAddError("%s is already a registered identity" % key)
        source = shadow.get(key)
        if source is None:
            raise CensusAddError("%s has no shadow row to source facts from" % key)
        decision = signed.get(key)
        if decision is None:
            raise CensusAddError("%s carries no founder signature" % key)
        row = _census_row(source, template)
        for required in ("address", "city", "state", "postal_code",
                         "official_url", "canonical_name"):
            if not str(row.get(required) or "").strip():
                raise CensusAddError("%s: census add needs %s" % (key, required))
        rows.append(row)
        keys.add(key)
        provenance.append(OrderedDict((
            ("identity_key", key),
            ("canonical_name", row["canonical_name"]),
            ("source_recensus_identity", key),
            ("signed_founder_decision", decision["founder_decision"]),
            ("signed_disposition", decision["proposes_authority"]),
            ("signed_by_work_order", decision["signed_by_work_order"]),
            ("founder_reviewed_at", decision.get("founder_reviewed_at")),
            ("bound_source_url", decision.get("bound_source_url")),
            ("bound_snapshot_hash", decision.get("bound_snapshot_hash")),
            ("property_codes", entry.get("property_codes")),
            ("address", row["address"]),
            ("phone", row.get("phone")),
            ("postal_code", row["postal_code"]),
            ("official_url", row["official_url"]),
            ("why_no_registered_twin", entry["why"]),
        )))

    added = json.loads(json.dumps(census))
    added["hotels"] = list(existing) + rows
    added["count"] = len(added["hotels"])
    # identity_state_counts is a description of the rows; leaving it stale
    # would make the document disagree with itself.
    states: Dict[str, int] = {}
    for hotel in added["hotels"]:
        state = hotel.get("identity_state", "")
        states[state] = states.get(state, 0) + 1
    if "identity_state_counts" in added:
        added["identity_state_counts"] = OrderedDict(sorted(states.items()))
    added["note"] = (
        "%s %s added %d identities that carried a founder signature from "
        "2026-08-26 which could not be applied while the identity did not "
        "exist: each was proven absent from the prior 96 on official URL, "
        "brand-scoped property code, street address and phone, and absent from "
        "every other market. ADD only -- all 96 prior identities are preserved "
        "byte-identical, nothing was superseded, and the 115-row shadow "
        "recensus was NOT promoted."
        % (census.get("note", ""), WORK_ORDER, len(rows))).strip()
    return OrderedDict((("before", census), ("after", added),
                        ("rows", rows), ("provenance", provenance)))


def run(write: bool) -> int:
    planned = plan()
    before, after = planned["before"], planned["after"]
    rows = planned["rows"]

    prior = {h["identity_key"]: json.dumps(h, sort_keys=True)
             for h in before["hotels"]}
    now = {h["identity_key"]: json.dumps(h, sort_keys=True)
           for h in after["hotels"]}
    missing = sorted(set(prior) - set(now))
    if missing:
        raise CensusAddError("ADD-NEVER-DOWNGRADE violated: %s" % missing[:5])
    moved = sorted(k for k in prior if prior[k] != now[k])
    if moved:
        raise CensusAddError("a prior identity's bytes moved: %s" % moved[:5])
    if len(after["hotels"]) != len(before["hotels"]) + len(rows):
        raise CensusAddError("row count did not land on 96 + %d" % len(rows))
    issues = CENSUS_CONTRACT.validate(after, market_states=["PA"])
    if issues:
        raise CensusAddError("the added census does not validate: %s"
                             % list(issues)[:5])
    keys = [h["identity_key"] for h in after["hotels"]]
    if len(set(keys)) != len(keys):
        raise CensusAddError("the add created a duplicate identity_key")

    print("registered census before : %d" % len(before["hotels"]))
    print("identities added         : %d" % len(rows))
    for row in rows:
        print("   %-52s %s" % (row["identity_key"][:51], row["official_url"][:60]))
    print("registered census after  : %d" % len(after["hotels"]))
    print("prior identities preserved: %d / %d" % (len(prior), len(prior)))
    print("census contract issues   : 0")
    if not write:
        print("(check only -- pass --write)")
        return 0

    _write(CENSUS, after)
    print("WROTE %s" % CENSUS.name)
    _write(LEDGER, OrderedDict((
        ("schema", "ptf-census-add/1.0"),
        ("work_order", WORK_ORDER),
        ("market_id", MARKET_ID),
        ("as_of", AS_OF),
        ("what_this_is",
         "Six identities added to the REGISTERED census, each carrying a "
         "founder signature from 2026-08-26 that could not be applied while "
         "the identity did not exist. ADD only: every one of the 96 prior "
         "identities is preserved byte-identical and nothing is superseded."),
        ("shadow_recensus_promoted", False),
        ("shadow_recensus_rows_untouched", 115 - len(rows)),
        ("intown_suites_deferred",
         "InTown Suites Pittsburgh re-located cleanly against its owned page, "
         "but carries no prior founder signature on a Pittsburgh identity, so "
         "adding it would be a new candidate rather than signed work."),
        ("count_before", len(before["hotels"])),
        ("count_added", len(rows)),
        ("count_after", len(after["hotels"])),
        ("adds", planned["provenance"]),
    )))
    print("WROTE %s" % LEDGER.name)
    return 0


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)
    try:
        return run(args.write)
    except CensusAddError as exc:
        print("REFUSED: %s" % exc)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
