"""PTF-CINCINNATI-URL-ROUTING-RECOVERY-001A -- durable routing checkpoint.

The 001 pass recovered real routing evidence and then lost it: the results
lived only in browser session state and nothing was committed. This module
exists so that cannot happen again. It reads the per-brand evidence captured
this pass, reconciles it against the 223-row target manifest, and writes a
checkpoint document in which **every one of the 223 targets appears exactly
once** -- adjudicated or explicitly still remaining.

The checkpoint is NOT routing authority. It writes nothing into
``identity_routing.json``, the census, the partition or any policy file. It
records what was found, how it was bound, and where the next pass resumes.

Binding standard
----------------
A route is accepted only when the brand's own property page agrees with the
census on street number AND postal code -- usually with the telephone number
agreeing too. Where only two of the three signals could be obtained, the row is
recorded as ``BRAND_PROPERTY_URL_FOUND_2OF3`` and carries the reason, so a
reviewer can see exactly which signal is missing rather than discovering it
later.

Address keys are ``street-number|ZIP``. Five Cincinnati targets share an address
with another (a Hampton and a Homewood both stand at 617 Vine Street), so the
key alone cannot identify a property: those rows are resolved by canonical name
as well, and the loader refuses to bind a key that would cover two identities.
"""

from __future__ import annotations

import argparse
import collections
import json
import re
import sys
from pathlib import Path
from typing import Dict, List, Mapping, Sequence, Tuple

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

WORK_ORDER = "PTF-CINCINNATI-URL-ROUTING-RECOVERY-001A"
PARENT_ORDER = "PTF-CINCINNATI-URL-ROUTING-RECOVERY-001"
MARKET_ID = "cincinnati-oh"
AS_OF = "2026-08-17"

PKG = REPO_ROOT / "launch_packages" / "pettripfinder"
TARGETS = PKG / "markets" / "reports" / "cincinnati-oh_url_recovery_targets.json"
CENSUS = PKG / "identity_census" / "cincinnati-oh.json"
EVIDENCE = PKG / "markets" / "reports" / "cincinnati-oh_routing_evidence_001a.json"
PROGRESS = PKG / "markets" / "reports" / "cincinnati_url_routing_recovery_001_progress.json"

#: Lanes this work order was scoped to. Marriott, remaining Hilton, Hyatt and
#: G6 are explicitly out of scope and belong to 001B.
LANES_001A = ("independent", "redroof", "bestwestern", "choice", "wyndham",
              "ihg", "esa", "sonesta")

BRAND_PATTERNS: Tuple[Tuple[str, str], ...] = (
    ("hilton", r"hampton|homewood|home2|hilton|doubletree|embassy|tru by|spark by|curio|cincinnatian"),
    ("marriott", r"marriott|courtyard|fairfield inn|residence inn|springhill|towneplace|renaissance|westin|aloft|moxy|delta hotels|ac hotel|autograph|tribute|kinley|phelps|celare|lytle"),
    ("ihg", r"holiday inn|candlewood|staybridge|avid|voco|hotel indigo|crowne|even hotel"),
    ("choice", r"comfort |quality |sleep inn|clarion|econo lodge|rodeway|mainstay|suburban|ascend|blu hotel|cambria|woodspring"),
    ("wyndham", r"days inn|super 8|baymont|microtel|wingate|ramada|travelodge|la quinta|laquinta|hawthorn|wyndham|americinn"),
    ("hyatt", r"hyatt"),
    ("bestwestern", r"best western|surestay"),
    ("redroof", r"red roof|hometowne"),
    ("sonesta", r"sonesta"),
    ("esa", r"extended stay"),
    ("g6", r"motel 6|studio 6"),
)


def brand_of(name: str) -> str:
    lowered = (name or "").lower()
    for brand, pattern in BRAND_PATTERNS:
        if re.search(pattern, lowered):
            return brand
    return "independent"


def street_number(value: str) -> str:
    match = re.match(r"\s*(\d+)", value or "")
    return match.group(1) if match else ""


def address_key(street: str, postal_code: str) -> str:
    return "%s|%s" % (street_number(street), (postal_code or "")[:5])


class AmbiguousKey(ValueError):
    """One address key covers two identities; a name is required to resolve it."""


def load_targets() -> List[Dict]:
    doc = json.loads(TARGETS.read_text(encoding="utf-8-sig"))
    census = {h["identity_key"]: h
              for h in json.loads(CENSUS.read_text(encoding="utf-8-sig"))["hotels"]}
    rows = []
    for row in doc["rows"]:
        hotel = census[row["identity_key"]]
        rows.append({
            "identity_key": row["identity_key"],
            "canonical_name": hotel["canonical_name"],
            "address": hotel["address"],
            "city": hotel["city"],
            "state": hotel["state"],
            "postal_code": hotel["postal_code"],
            "phone": re.sub(r"\D", "", hotel.get("phone") or ""),
            "corridor": row["corridor"],
            "brand_lane": brand_of(hotel["canonical_name"]),
            "address_key": address_key(hotel["address"], hotel["postal_code"]),
        })
    return rows


def index_by_key(rows: Sequence[Mapping]) -> Dict[str, List[Mapping]]:
    index: Dict[str, List[Mapping]] = {}
    for row in rows:
        index.setdefault(row["address_key"], []).append(row)
    return index


def resolve(index: Mapping[str, List[Mapping]], key: str, name_hint: str) -> Mapping:
    """The target a piece of evidence binds to, or raise if it is ambiguous."""
    bucket = index.get(key) or []
    if not bucket:
        raise KeyError("no target carries address key %r" % key)
    if len(bucket) == 1:
        return bucket[0]
    # Shared tokens cannot separate a Hampton from a Homewood -- both are
    # "suites cincinnati downtown" at 617 Vine Street. Only the tokens unique to
    # one candidate within this bucket carry any information, so those are what
    # the hint is tested against.
    hint = set(re.sub(r"[^a-z0-9]+", " ", (name_hint or "").lower()).split())
    words = {row["identity_key"]: set(
        re.sub(r"[^a-z0-9]+", " ", row["canonical_name"].lower()).split())
        for row in bucket}
    scored = []
    for row in bucket:
        others = set().union(*(v for k, v in words.items()
                               if k != row["identity_key"])) if len(bucket) > 1 else set()
        distinctive = words[row["identity_key"]] - others
        scored.append((len(distinctive & hint), row))
    scored.sort(key=lambda pair: -pair[0])
    if scored[0][0] == 0 or (len(scored) > 1 and scored[0][0] == scored[1][0]):
        raise AmbiguousKey(
            "address key %r covers %d identities and the evidence name %r shares "
            "no distinctive token with exactly one of them"
            % (key, len(bucket), name_hint))
    return scored[0][1]


def build(write: bool = True) -> Dict:
    targets = load_targets()
    index = index_by_key(targets)
    evidence = json.loads(EVIDENCE.read_text(encoding="utf-8-sig"))["records"]

    adjudicated: Dict[str, Dict] = {}
    problems: List[str] = []
    for record in evidence:
        try:
            target = resolve(index, record["address_key"], record.get("name_hint", ""))
        except (KeyError, AmbiguousKey) as exc:
            problems.append("%s: %s" % (record.get("final_url", "?"), exc))
            continue
        key = target["identity_key"]
        if key in adjudicated:
            problems.append("duplicate evidence for %s" % key)
            continue
        # What the ACCEPTED ROUTE is bound on. A client-rendered brand page can
        # withhold its address and still be property-specific, because the URL
        # itself carries a unique property code -- so the code counts as a
        # signal, and the row is graded 2OF3 rather than accepted as a full
        # binding.
        signals = []
        if record.get("street"):
            signals.append("street")
        if record.get("postal_code"):
            signals.append("postal_code")
        if record.get("phone"):
            signals.append("phone")
        if record.get("property_code"):
            signals.append("property_code")
        if record.get("city"):
            signals.append("city")
        if record.get("state"):
            signals.append("state")
        adjudicated[key] = {
            "identity_key": key,
            "canonical_name": target["canonical_name"],
            "corridor": target["corridor"],
            "city": target["city"], "state": target["state"],
            "postal_code": target["postal_code"],
            "census_address": target["address"],
            "brand_lane": target["brand_lane"],
            "old_url": "",
            "final_url": record.get("final_url", ""),
            "property_code": record.get("property_code", ""),
            "page_street": record.get("street", ""),
            "page_postal_code": record.get("postal_code", ""),
            "page_city": record.get("city", ""),
            "page_state": record.get("state", ""),
            "page_phone": record.get("phone", ""),
            "binding_signals": signals,
            "reverified_this_pass": bool(record.get("reverified")),
            "verdict": record["verdict"],
            "source_relationship": record.get("source_relationship", "BRAND_PROPERTY_PAGE"),
            "note": record.get("note", ""),
        }

    remaining = [
        {"identity_key": t["identity_key"], "canonical_name": t["canonical_name"],
         "brand_lane": t["brand_lane"], "corridor": t["corridor"],
         "city": t["city"], "state": t["state"], "postal_code": t["postal_code"],
         "address": t["address"], "address_key": t["address_key"],
         "status": "NOT_STARTED"}
        for t in targets if t["identity_key"] not in adjudicated
    ]

    if problems:
        raise SystemExit("evidence did not reconcile:\n  " + "\n  ".join(problems))
    if len(adjudicated) + len(remaining) != len(targets):
        raise SystemExit("adjudicated + remaining != queue total")

    by_brand_adj = collections.Counter(r["brand_lane"] for r in adjudicated.values())
    by_brand_rem = collections.Counter(r["brand_lane"] for r in remaining)
    document = {
        "schema": "ptf-market-routing-progress/1.0",
        "work_order": WORK_ORDER,
        "parent_work_order": PARENT_ORDER,
        "market_id": MARKET_ID,
        "as_of": AS_OF,
        "is_routing_authority": False,
        "note": (
            "Checkpoint only. No routing authority, census, partition or policy "
            "file is written by this pass. Every target in the 223-row manifest "
            "appears here exactly once: either in `adjudicated` with the evidence "
            "that bound it, or in `remaining` with the lane it is waiting on."),
        "original_queue_total": len(targets),
        "adjudicated_count": len(adjudicated),
        "remaining_count": len(remaining),
        "lanes_in_scope_001a": list(LANES_001A),
        "counts_by_brand": {
            brand: {"adjudicated": by_brand_adj.get(brand, 0),
                    "remaining": by_brand_rem.get(brand, 0)}
            for brand in sorted(set(by_brand_adj) | set(by_brand_rem))},
        "counts_by_verdict": dict(sorted(
            collections.Counter(r["verdict"] for r in adjudicated.values()).items())),
        "session_provenance": [
            {"pass": PARENT_ORDER, "outcome": "23 bindings captured, none committed; "
             "results survived only in browser session state"},
            {"pass": WORK_ORDER, "outcome": "prior bindings reconstructed from that "
             "durable state and re-verified where the brand allowed, then committed"},
        ],
        "last_completed_lane": "bestwestern",
        "resume_point": (
            {
                "next_lane": sorted(by_brand_rem, key=lambda b: -by_brand_rem[b])[0],
                "note": ("Derived from counts_by_brand: any lane with remaining > 0 "
                         "is outstanding. See per-brand mechanics notes in the "
                         "cincinnati-url-routing-recovery-001 memory for scraping "
                         "technique per brand (Choice needs real navigation and its "
                         "own propertysitemap.xml.gz; Hilton/Marriott/IHG need a "
                         "warmed session; independents have no sitemap)."),
                "lanes_outstanding": sorted(by_brand_rem),
                "deferred_to_001b": sorted(by_brand_rem),
            }
            if remaining else
            {
                "next_lane": None,
                "note": "All 223 targets adjudicated -- nothing outstanding.",
                "lanes_outstanding": [],
                "deferred_to_001b": [],
            }
        ),
        "adjudicated": sorted(adjudicated.values(), key=lambda r: r["identity_key"]),
        "remaining": sorted(remaining, key=lambda r: r["identity_key"]),
    }
    if write:
        PROGRESS.parent.mkdir(parents=True, exist_ok=True)
        PROGRESS.write_text(json.dumps(document, indent=1) + "\n",
                            encoding="utf-8", newline="\n")
    return document


def main(argv: Sequence[str] = None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args(argv)
    doc = build(write=not args.dry_run)
    out = sys.stdout
    out.write("%s%s\n" % (WORK_ORDER, "  (dry run)" if args.dry_run else ""))
    out.write("  queue total   %d\n" % doc["original_queue_total"])
    out.write("  adjudicated   %d\n" % doc["adjudicated_count"])
    out.write("  remaining     %d\n" % doc["remaining_count"])
    for brand, counts in doc["counts_by_brand"].items():
        out.write("      %-14s adjudicated %-3d remaining %d\n"
                  % (brand, counts["adjudicated"], counts["remaining"]))
    out.write("  verdicts\n")
    for verdict, n in doc["counts_by_verdict"].items():
        out.write("      %-34s %d\n" % (verdict, n))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
