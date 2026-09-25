"""PTF-JACKSONVILLE-FL-HARDENED-SOURCE-READY-001 -- Phases 20-21: every census identity in exactly one disposition.

Cloned from the Orlando FL V2 helper, simplified because this market's clean-authority pass
(jacksonville_fl_clean_authority_001) already computes one disposition per confirmed identity directly, with its
full router record folded in at adjudication time rather than re-derived here.

Two vocabularies on every row:
  final_state   the shared partition contract's own state (contracts.partition), which the sealed package
                reconciles set-for-set against the census.
  disposition   the order's Phase 20 vocabulary (CLEAN_PET_FRIENDLY, CLEAN_VERIFIED_NO_PETS, ROUTING_HOLD,
                ACCESS_BLOCKED, EVIDENCE_HOLD, NEGATION_HOLD, SOURCE_SILENT, BROWSER_CAPTURE_NEEDED,
                IDENTITY_MISMATCH_HOLD).

Nothing here fetches or publishes.

Output: launch_packages/pettripfinder/markets/staging/jacksonville-fl/launch_package/jacksonville_fl_final_partition_001.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter, OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

from scripts.pettripfinder.contracts import partition as PARTITION  # noqa: E402

WORK_ORDER = "PTF-JACKSONVILLE-FL-HARDENED-SOURCE-READY-001"
MARKET_ID = "jacksonville-fl"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
#: SHADOW_UNTIL_REGISTERED: a shadow market's partition belongs INSIDE its own staging launch_package, never at
#: the registry package root -- the root is where a REGISTERED market's release contract references it, and
#: writing there would put an unregistered market's document into shared space. The shadow seal reads it from
#: the staging tree.
OUT = os.path.join(PKG, "markets", "staging", MARKET_ID, "launch_package",
                   "jacksonville_fl_final_partition_001.json")
CENSUS = os.path.join(PKG, "identity_census_proposed", "jacksonville-fl.json")
CLEAN = os.path.join(REPORTS, "jacksonville_fl_clean_authority_001.json")
AS_OF = "2026-09-25"

#: disposition -> final_state
_STATE = {
    "CLEAN_PET_FRIENDLY": "PUBLISHED_PET_FRIENDLY",
    "CLEAN_VERIFIED_NO_PETS": "VERIFIED_NO_PETS",
    "NEGATION_HOLD": "AWAITING_CONTRADICTION_RESOLUTION",
    "ROUTING_HOLD": "AWAITING_OFFICIAL_URL",
    "BROWSER_CAPTURE_NEEDED": "AWAITING_ATTENDED_CAPTURE",
    "ACCESS_BLOCKED": "ACCESS_BLOCKED",
    "SOURCE_SILENT": "AWAITING_POLICY_OBSERVATION",
    "EVIDENCE_HOLD": "AWAITING_POLICY_OBSERVATION",
    "IDENTITY_MISMATCH_HOLD": "AWAITING_ROUTING_REPLACEMENT",
}
_TERMINAL = {"CLEAN_PET_FRIENDLY", "CLEAN_VERIFIED_NO_PETS"}


def _load(p, default=None):
    if not os.path.exists(p):
        return default
    with open(p, encoding="utf-8-sig") as fh:
        return json.load(fh)


def build():
    census = _load(CENSUS)
    clean = _load(CLEAN)
    clean_by_key = {r["identity_key"]: r for r in clean["rows"]}

    items = []
    for h in census["hotels"]:
        key = h["identity_key"]
        c = clean_by_key.get(key)
        disp = c["disposition"] if c else "ROUTING_HOLD"
        state = _STATE[disp]
        row = OrderedDict([("identity_key", key), ("canonical_name", h["canonical_name"]),
                           ("corridor", h.get("corridor", "")), ("brand", h.get("brand") or ""),
                           ("final_state", state), ("disposition", disp)])
        if disp in _TERMINAL:
            row["resolved"] = True
            if disp == "CLEAN_PET_FRIENDLY":
                row["policy_facts"] = c.get("policy_facts") or {}
            row["evidence"] = c.get("evidence") or {}
        else:
            row["resolved"] = False
            row["next_action_source"] = "PTF-JACKSONVILLE-FL-HARDENED-SOURCE-READY-001 acquisition router record"
            row["determined_by"] = WORK_ORDER
            reason = (c or {}).get("hold_reason") or (c or {}).get("negation_conflict") or "no evidence captured this order"
            row["next_action"] = reason
            row["router_record"] = OrderedDict([
                ("brand_family", h.get("brand") or "INDEPENDENT"),
                ("route", h.get("official_url") or ""),
                ("disposition_basis", disp),
                ("hold_reason", reason),
            ])
        items.append(row)

    counts = Counter(i["final_state"] for i in items)
    return OrderedDict((
        ("schema", PARTITION.SCHEMA), ("work_order", WORK_ORDER), ("market_id", MARKET_ID), ("as_of", AS_OF),
        ("what_this_is", "Every admitted Northeast Florida census identity in exactly one disposition state, with the "
                         "order's Phase 20 disposition and, for every unresolved row, its router record."),
        ("count", len(items)),
        ("counts_by_state", OrderedDict(sorted(counts.items()))),
        ("counts_by_disposition", OrderedDict(sorted(Counter(i["disposition"] for i in items).items()))),
        ("resolved", sum(1 for i in items if i["resolved"])),
        ("unresolved", sum(1 for i in items if not i["resolved"])),
        ("items", items),
    ))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=OUT)
    args = ap.parse_args(argv)
    doc = build()
    issues = PARTITION.validate(doc)
    print("identities :", doc["count"], "resolved", doc["resolved"], "unresolved", doc["unresolved"])
    print("by state   :", dict(doc["counts_by_state"]))
    print("by disp    :", dict(doc["counts_by_disposition"]))
    print("contract   :", len(issues), "issues")
    for i in issues[:8]:
        print("   !", str(i)[:200])
    if issues:
        return 1
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
