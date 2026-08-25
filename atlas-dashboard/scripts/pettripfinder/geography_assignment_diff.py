"""PTF-GEOGRAPHY-NORMALIZATION-001 -- what the new precedence actually moves.

Phase D reverses two tiers: postal code now outranks city, and city matching is
state-aware. Either could move a corridor label that is already public, so this
report answers the only question that matters before the change lands -- WHICH
hotels move, and is each move a correction or a surprise?

It compares the LEGACY engine (explicit -> city -> ZIP, state-blind) against the
canonical one, over every committed census row, using each market's current
configuration for both. Read-only.

Classification:

  CORRECTNESS_FIX          the corridor changes, and the new one is where the
                           property actually is
  REPRODUCIBILITY_FIX_ONLY the corridor is unchanged; only the recorded basis
                           becomes provable
  NEWLY_UNASSIGNED         the property had a corridor and now has none
  NEWLY_ASSIGNED           the property had none and now has one
  UNEXPECTED_CHANGE        anything the rules above do not explain

    python -m scripts.pettripfinder.geography_assignment_diff
    python -m scripts.pettripfinder.geography_assignment_diff --out <path>.json
"""

from __future__ import annotations

import argparse
import collections
import json
import sys
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Tuple

from scripts.pettripfinder.contracts.identity_key import ptf_identity_key
from scripts.pettripfinder.markets import load_markets, market_by_id
from scripts.pettripfinder.markets.assignment import (
    TIER_CITY, TIER_EXPLICIT, TIER_UNASSIGNED, TIER_ZIP,
)

REPO_ROOT = Path(__file__).resolve().parents[2]
PACKAGE_DIR = REPO_ROOT / "launch_packages" / "pettripfinder"
from scripts.pettripfinder import census_location as CENSUS_LOCATION  # noqa: E402
CENSUS_DIR = CENSUS_LOCATION.identity_census_dir()  # committed, or $PTF_IDENTITY_CENSUS_DIR during a rebuild
REPORT_PATH = PACKAGE_DIR / "markets" / "reports" / "ohio_phase_d_assignment_diff.json"

POLICY_FILES = {
    "columbus-oh": "hotel_policy_facts.json",
    "cleveland-akron-canton-oh": "hotel_policy_facts_cleveland-akron-canton-oh.json",
    "dayton-oh": "hotel_policy_facts_dayton-oh.json",
}


def _legacy_assign(corridors: Sequence, key: str, city: str,
                   zip5: str) -> Tuple[Optional[str], str, str]:
    """The engine as it behaved before Phase D: city-first and state-blind."""
    eligible = [c for c in corridors if key not in c.excluded_hotel_ids]
    explicit = [c for c in eligible if key in c.explicit_hotel_ids]
    if explicit:
        return (explicit[0].corridor_id if len(explicit) == 1 else None,
                TIER_EXPLICIT, key)
    by_city = [c for c in eligible
               if city and city in tuple(x.lower() for x in c.included_cities)]
    if by_city:
        return (by_city[0].corridor_id if len(by_city) == 1 else None,
                TIER_CITY, city)
    by_zip = [c for c in eligible if zip5 and zip5 in c.included_postal_codes]
    if by_zip:
        return (by_zip[0].corridor_id if len(by_zip) == 1 else None,
                TIER_ZIP, zip5)
    return None, TIER_UNASSIGNED, ""


def classify(before_corridor, after_corridor, before_basis, after_basis) -> str:
    if before_corridor == after_corridor:
        return ("REPRODUCIBILITY_FIX_ONLY" if before_basis != after_basis
                else "UNEXPECTED_CHANGE")
    if before_corridor is None:
        return "NEWLY_ASSIGNED"
    if after_corridor is None:
        return "NEWLY_UNASSIGNED"
    return "CORRECTNESS_FIX"


def build_report() -> Dict:
    from scripts.pettripfinder.normalize_census_geography import recompute

    markets = {m.market_id: m for m in load_markets()}
    rows: List[Dict] = []
    for market_id, market in sorted(markets.items()):
        path = CENSUS_DIR / ("%s.json" % market_id)
        if not path.is_file():
            continue
        published = set()
        policy_file = POLICY_FILES.get(market_id)
        if policy_file and (PACKAGE_DIR / policy_file).is_file():
            published = {
                ptf_identity_key(h["name"]) for h in json.loads(
                    (PACKAGE_DIR / policy_file).read_text(encoding="utf-8-sig"))["hotels"]}

        after_doc, _changes = recompute(market_id)
        source = json.loads(path.read_text(encoding="utf-8-sig"))
        by_key = {h["identity_key"]: h for h in source["hotels"]}

        for row in after_doc["hotels"]:
            key = row["identity_key"]
            legacy = by_key.get(key, {})
            before_corridor, before_basis, before_value = _legacy_assign(
                market.corridors, key,
                (legacy.get("city") or "").strip().lower(),
                (legacy.get("postal_code") or "")[:5])
            after_corridor = row["corridor"]
            after_basis = row["assignment_basis"]
            if (before_corridor, before_basis) == (after_corridor, after_basis):
                continue
            rows.append({
                "market_id": market_id,
                "identity_key": key,
                "canonical_name": row.get("canonical_name", ""),
                "city": row.get("city", ""), "state": row.get("state", ""),
                "postal_code": row.get("postal_code", ""),
                "published": key in published,
                "before_corridor": before_corridor,
                "before_basis": before_basis,
                "after_corridor": after_corridor,
                "after_basis": after_basis,
                "assignment_value": row["assignment_value"],
                "classification": classify(before_corridor, after_corridor,
                                           before_basis, after_basis),
            })

    by_class = collections.Counter(r["classification"] for r in rows)
    by_market = collections.Counter(r["market_id"] for r in rows)
    return collections.OrderedDict((
        ("work_order", "PTF-GEOGRAPHY-NORMALIZATION-001"),
        ("phase", "D"),
        ("note", "Legacy engine (city-first, state-blind) compared against the "
                 "canonical one over every committed census row. Read-only."),
        ("total_changed", len(rows)),
        ("published_changed", sum(1 for r in rows if r["published"])),
        ("by_market", dict(by_market)),
        ("by_classification", dict(by_class)),
        ("corridor_changed", sum(1 for r in rows
                                 if r["before_corridor"] != r["after_corridor"])),
        ("unexpected", [r for r in rows
                        if r["classification"] == "UNEXPECTED_CHANGE"]),
        ("changes", rows),
    ))


def main(argv: Optional[List[str]] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--out", type=Path, nargs="?", const=REPORT_PATH)
    args = parser.parse_args(argv)

    report = build_report()
    out = sys.stdout.write
    out("\n%s -- assignment diff\n%s\n" % (report["work_order"], "=" * 70))
    out("total changed      : %d  (published: %d)\n"
        % (report["total_changed"], report["published_changed"]))
    out("corridor changed   : %d\n" % report["corridor_changed"])
    out("by market          : %s\n" % report["by_market"])
    out("by classification  : %s\n" % report["by_classification"])
    out("UNEXPECTED_CHANGE  : %d\n\n" % len(report["unexpected"]))
    for row in report["changes"]:
        if row["before_corridor"] == row["after_corridor"]:
            continue
        out("  [%s] %-13s %-42s %-6s pub=%-5s %s -> %s\n"
            % (row["classification"][:20], row["market_id"][:13],
               row["canonical_name"][:42], row["postal_code"], row["published"],
               (row["before_corridor"] or "-").split("__")[-1],
               (row["after_corridor"] or "-").split("__")[-1]))
    if args.out:
        args.out.parent.mkdir(parents=True, exist_ok=True)
        args.out.write_text(json.dumps(report, indent=2) + "\n", encoding="utf-8",
                            newline="\n")
        out("\nwrote %s\n" % args.out)
    return 0


if __name__ == "__main__":                                # pragma: no cover
    raise SystemExit(main())
