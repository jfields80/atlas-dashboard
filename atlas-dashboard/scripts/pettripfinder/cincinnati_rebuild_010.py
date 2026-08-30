# -*- coding: utf-8 -*-
"""PTF-CINCINNATI-FREE-LANE-APPLICATION-010 Phase 8 -- rebuild the market.

    python -m scripts.pettripfinder.cincinnati_rebuild_010 --write

Seed inventory, final partition and release contract, all re-derived from the
authority this order just wrote rather than edited in place. The partition is
rebuilt whole from the census, the package and the exclusion shard, so a row
cannot keep a state that authority no longer supports.

The rename is why the partition is rebuilt rather than patched: the identity
key of the Bellevue row moved, and a patch would have left the old key sitting
in the partition beside the new one, resolved and unresolved at the same time.
"""

from __future__ import annotations

import argparse
import csv
import io
import json
import sys
from collections import Counter, OrderedDict
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder import market_authority as MA            # noqa: E402
from scripts.pettripfinder.cincinnati_free_lane_application_010 import (  # noqa: E402
    CENSUS, HELD, MARKET_ID, PACKAGE, PKG, WORK_ORDER, _load)

AS_OF = "2026-08-31"
PARTITION = PKG / "cincinnati_final_partition_001.json"
SEED = MA.seed_shard_path(MARKET_ID)
GLOBAL_SEED = PKG / "seed_businesses.csv"

SEED_COLUMNS = ("name", "category", "address", "city", "state", "postal_code",
                "phone", "website_url", "source_url", "source_type",
                "observed_at", "rating", "amenities", "pet_policy",
                "canonical", "market_id")

RESOLVED_STATES = ("PUBLISHED_PET_FRIENDLY", "VERIFIED_NO_PETS",
                   "OUT_OF_CURRENT_CATEGORY")


def _seed_row(record, census_row):
    """One inventory row for a newly published identity.

    The street address comes from the CENSUS, not from the page: the importer
    refuses a seed row without one, and PTF-...-APPLICATION-004 learned that
    the hard way when five rows arrived addressless.
    """
    # The seed NAME must normalise back to the identity key -- site_data joins
    # display rows to policy records on it and fails closed otherwise. So this
    # is the CENSUS canonical name, never the page's own name, which for ten of
    # these properties differs (a rebrand, a town prefix, a regional name).
    return OrderedDict((
        ("name", census_row["canonical_name"]),
        ("category", "pet-friendly-hotels"),
        ("address", census_row.get("address", "")),
        ("city", census_row.get("city", "")),
        ("state", census_row.get("state", "")),
        ("postal_code", census_row.get("postal_code", "")),
        ("phone", census_row.get("phone", "")),
        ("website_url", record["source_url"]),
        ("source_url", record["source_url"]),
        ("source_type", "OFFICIAL_PROPERTY"),
        ("observed_at", record["verified_at"]),
        ("rating", ""),
        ("amenities", ""),
        ("pet_policy", record["evidence_quote"]),
        ("canonical", "true"),
        ("market_id", MARKET_ID),
    ))


def rebuild_seed(package, census):
    existing = MA.load_market_seed_rows(MARKET_ID)
    have = {row["name"] for row in existing}
    rows = [OrderedDict((c, row.get(c, "")) for c in SEED_COLUMNS)
            for row in existing]
    added = 0
    for record in package["hotels"]:
        census_row = census.get(record["identity_key"])
        if census_row is not None and census_row["canonical_name"] in have:
            continue
        if record["name"] in have:
            continue
        if census_row is None:
            raise RuntimeError("%s is published but not in the census"
                               % record["identity_key"])
        if not census_row.get("address"):
            raise RuntimeError("%s has no street address; the importer refuses "
                               "an addressless seed row"
                               % record["identity_key"])
        rows.append(_seed_row(record, census_row))
        added += 1
    return rows, added


def rebuild_partition(package, census, exclusions, routes):
    published = {h["identity_key"] for h in package["hotels"]}
    excluded = {e["normalized_name"]: e for e in exclusions}
    routed = {r["hotel_ref"]["identity_key"]: r for r in routes}
    prior = {i["identity_key"]: i for i in _load(PARTITION)["items"]}

    items = []
    for key, row in sorted(census.items()):
        was = prior.get(key) or prior.get(row.get("prior_identity_key") or "")
        if key in published:
            state, resolved = "PUBLISHED_PET_FRIENDLY", True
        elif key in excluded:
            state = excluded[key]["exclusion_state"]
            resolved = True
        elif was and was["final_state"] == "OUT_OF_CURRENT_CATEGORY":
            state, resolved = "OUT_OF_CURRENT_CATEGORY", True
        elif was and not was["resolved"]:
            state, resolved = was["final_state"], False
        else:
            state, resolved = "AWAITING_POLICY_OBSERVATION", False

        determined = (WORK_ORDER
                      if (key in published or key in excluded)
                      and (not was or was["final_state"] != state)
                      else (was or {}).get("determined_by", WORK_ORDER))
        item = OrderedDict((
            ("identity_key", key),
            ("canonical_name", row.get("canonical_name", "")),
            ("slug", row.get("slug", key.replace(" ", "-"))),
            ("city", row.get("city", "")),
            ("state", row.get("state", "")),
            ("postal_code", row.get("postal_code", "")),
            ("final_state", state),
            ("resolved", resolved),
            ("next_action", "" if resolved
             else (was or {}).get("next_action", "")),
            ("next_action_source", "" if resolved
             else (was or {}).get("next_action_source", "")),
            ("determined_by", determined),
            ("updated_at", AS_OF if (was or {}).get("final_state") != state
             else (was or {}).get("updated_at", AS_OF)),
            ("official_url",
             next((h["source_url"] for h in package["hotels"]
                   if h["identity_key"] == key),
                  excluded[key]["official_url"] if key in excluded
                  else (routed.get(key) or {}).get("official_property_url",
                                                   (was or {}).get("official_url", "")))),
            ("state_override_reason",
             "Ruled HOLD_FOR_IDENTITY_ADDRESS_CLARIFICATION by the founder "
             "in %s; the property page states two different street addresses "
             "and its only fee claim is a corporate link, so the row stays "
             "unresolved until the address identity is mechanically settled."
             % WORK_ORDER if key == HELD
             else (was or {}).get("state_override_reason", "")),
        ))
        items.append(item)

    counts = Counter(i["final_state"] for i in items)
    doc = _load(PARTITION)
    doc["work_order"] = WORK_ORDER
    doc["as_of"] = AS_OF
    doc["count"] = len(items)
    doc["final_state_counts"] = OrderedDict(sorted(counts.items()))
    doc["items"] = items
    return doc, counts


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)

    package = _load(PACKAGE)
    census = {h["identity_key"]: h for h in _load(CENSUS)["hotels"]}
    exclusions = MA.load_market_exclusions_document(MARKET_ID)["exclusions"]
    routes = MA.load_market_routing_document(MARKET_ID)["routes"]

    seed_rows, added = rebuild_seed(package, census)
    doc, counts = rebuild_partition(package, census, exclusions, routes)

    print("census              : %d" % len(census))
    print("published records   : %d" % len(package["hotels"]))
    print("exclusions          : %d" % len(exclusions))
    print("active routes       : %d" % len(routes))
    print("seed rows           : %d (+%d)" % (len(seed_rows), added))
    for state, n in sorted(counts.items()):
        print("  %-32s %d" % (state, n))
    resolved = sum(counts[s] for s in RESOLVED_STATES)
    print("resolved / unresolved: %d / %d" % (resolved, len(census) - resolved))
    if not args.write:
        print("(check only -- pass --write)")
        return 0

    buf = io.StringIO()
    writer = csv.DictWriter(buf, fieldnames=SEED_COLUMNS, lineterminator="\n")
    writer.writeheader()
    for row in seed_rows:
        writer.writerow(row)
    SEED.write_text(buf.getvalue(), encoding="utf-8", newline="")
    print("WROTE %s (%d rows)" % (SEED.name, len(seed_rows)))

    PARTITION.write_text(json.dumps(doc, indent=1, ensure_ascii=False) + "\n",
                         encoding="utf-8", newline="\n")
    print("WROTE %s" % PARTITION.name)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
