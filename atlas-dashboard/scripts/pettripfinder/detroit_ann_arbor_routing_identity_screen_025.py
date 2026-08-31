# -*- coding: utf-8 -*-
"""PTF-DETROIT-ANN-ARBOR-ROUTING-REPAIR-025, Phase 3 identity screen.

Screens the no-route cohort for rows that are NOT routing problems before any
discovery effort is spent on them.

DISCOVERING A ROUTE FOR A DUPLICATE IDENTITY IS WORSE THAN FINDING NOTHING. If
"Trumbell and Porter" is the same building as the already-published "Trumbull
and Porter Hotel", then routing it, capturing it and publishing it produces two
records for one hotel -- and the second one is invisible to every duplicate
check that keys on identity, because the misspelling makes it a different key.
The cheapest moment to catch that is before the work, not after.

NOTHING IS RENAMED, MERGED OR RETIRED HERE. This screen only flags candidates
for identity review, with the evidence for the flag. Phase 13 is explicit that a
routing order does not silently resolve identity.
"""
from __future__ import annotations

import difflib
import json
import re
import sys
from collections import Counter, OrderedDict
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder import (                                # noqa: E402
    detroit_ann_arbor_candidate_reconciliation_011 as R11,
    market_authority as MA)

MARKET = "detroit-ann-arbor-mi"
WORK_ORDER = "PTF-DETROIT-ANN-ARBOR-ROUTING-REPAIR-025"
AS_OF = "2026-08-30"

LP = R11.LP
COHORT = LP / "detroit_ann_arbor_routing_cohort_025.json"
OUT = LP / "detroit_ann_arbor_routing_identity_screen_025.json"

#: Tokens that make a row very unlikely to be a lodging business at all.
NON_LODGING_HINTS = ("direct", "supply", "warehouse", "storage", "rental",
                     "apartments", "realty", "clinic")
LODGING_TOKENS = ("hotel", "inn", "motel", "suites", "lodge", "resort",
                  "hostel", "house", "place", "studios")


def norm(name):
    text = (name or "").lower()
    text = re.sub(r"[^a-z0-9 ]+", " ", text)
    return re.sub(r"\s+", " ", text).strip()


def street_key(address):
    text = (address or "").lower()
    match = re.match(r"\s*(\d+)\s+(.*)", text)
    if not match:
        return ""
    number, rest = match.group(1), match.group(2)
    rest = re.sub(r"\b(street|st|road|rd|avenue|ave|drive|dr|boulevard|blvd|"
                  r"highway|hwy|parkway|pkwy|lane|ln|court|ct|west|w|east|e|"
                  r"north|n|south|s)\b", " ", rest)
    rest = re.sub(r"[^a-z0-9]+", "", rest)
    return "%s|%s" % (number, rest[:12])


def run():
    cohort = R11.load(COHORT)
    census = {row["identity_key"]: row for row in
              R11.load(LP / "identity_census" / ("%s.json" % MARKET))["hotels"]}
    published = {row["identity_key"] for row in
                 R11.load(LP / ("hotel_policy_facts_%s.json" % MARKET))["hotels"]}
    excluded = {row["normalized_name"] for row in
                R11.load(MA.exclusions_shard_path(MARKET))["exclusions"]}
    resolved = published | excluded

    resolved_index = []
    for key in resolved:
        crow = census.get(key) or {}
        resolved_index.append((key, norm(crow.get("canonical_name") or key),
                               street_key(crow.get("address")),
                               (crow.get("phone") or "").strip()))

    flagged, clean = [], []
    for row in cohort["rows"]:
        if row["sub_classification"] != "NO_ROUTE":
            continue
        key = row["identity_key"]
        name = norm(row["canonical_name"])
        skey = street_key(row["address"])
        phone = (row["phone"] or "").strip()

        signals = []
        best = None
        for rkey, rname, rstreet, rphone in resolved_index:
            ratio = difflib.SequenceMatcher(None, name, rname).ratio()
            same_street = bool(skey) and skey == rstreet
            same_phone = bool(phone) and phone == rphone
            if ratio >= 0.86 or same_street or same_phone:
                why = []
                if ratio >= 0.86:
                    why.append("name similarity %.2f" % ratio)
                if same_street:
                    why.append("SAME STREET ADDRESS")
                if same_phone:
                    why.append("SAME PHONE")
                if best is None or ratio > best[1]:
                    best = (rkey, ratio, why)
        if best:
            signals.append(OrderedDict([
                ("possible_duplicate_of", best[0]),
                ("evidence", best[2]),
            ]))

        lower = (row["canonical_name"] or "").lower()
        if any(hint in lower for hint in NON_LODGING_HINTS) and \
                not any(tok in lower for tok in LODGING_TOKENS):
            signals.append(OrderedDict([
                ("not_obviously_lodging", row["canonical_name"]),
                ("evidence", ["the name carries no lodging token and reads "
                              "like a non-hotel business"]),
            ]))

        entry = OrderedDict([
            ("identity_key", key),
            ("canonical_name", row["canonical_name"]),
            ("address", row["address"]),
            ("city", row["city"]),
            ("phone", row["phone"]),
        ])
        if signals:
            entry["flags"] = signals
            entry["recommended"] = "IDENTITY_REVIEW_FIRST"
            flagged.append(entry)
        else:
            clean.append(entry)

    R11.write_lf(OUT, OrderedDict([
        ("schema", "ptf-detroit-routing-identity-screen/1.0"),
        ("work_order", WORK_ORDER), ("market_id", MARKET), ("as_of", AS_OF),
        ("provider_calls", 0), ("spend_usd", 0.0),
        ("note",
         "Flags only. Nothing is renamed, merged or retired: a routing order "
         "does not silently resolve identity."),
        ("no_route_rows", len(flagged) + len(clean)),
        ("flagged_for_identity_review", len(flagged)),
        ("clean_for_route_discovery", len(clean)),
        ("flagged", flagged),
        ("clean", clean),
    ]))

    print("=== Phase 3: identity screen over the no-route rows ===")
    print("  no-route rows                 :", len(flagged) + len(clean))
    print("  FLAGGED for identity review   :", len(flagged))
    for row in flagged:
        for flag in row["flags"]:
            if "possible_duplicate_of" in flag:
                print("     %-40s ~ %s (%s)"
                      % (row["canonical_name"][:40],
                         flag["possible_duplicate_of"][:34],
                         "; ".join(flag["evidence"])))
            else:
                print("     %-40s NOT OBVIOUSLY LODGING"
                      % row["canonical_name"][:40])
    print("  clean for route discovery     :", len(clean))
    print("wrote", OUT.name)


if __name__ == "__main__":
    run()
