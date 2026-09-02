"""PTF-DAYTON-OH-HARDENED-APPLICATION-002 -- Phase 8.

Rebuild Dayton's final partition against the authority this order just applied.

Terminal states are DERIVED, never carried: PUBLISHED_PET_FRIENDLY is read from
the committed policy package and VERIFIED_NO_PETS from this market's exclusion
shard, so the partition cannot drift from the authorities it claims to describe.
Every other identity keeps the state it already had, because nothing in this
order ruled on it and a fresher-looking state would be a finding no work order
made.

One exception, and it is evidence-backed rather than editorial: Baymont by
Wyndham Greenville is moved from AWAITING_POLICY_OBSERVATION to
AWAITING_ROUTING_REPLACEMENT. The committed state says its route is sound and
only its policy is unread; PTF-DAYTON-OH-HARDENED-REVALIDATION-001 observed that
the URL on record redirects to a Wyndham SEARCH RESULTS page. A soft-404 means
the route is not this property's page, and policy work cannot start until it is
replaced. The identity is NOT retired -- a redirect to search is a renamed slug
until the brand inventory says otherwise.

A NEW artifact is written. The historical partition is not rewritten as though
it described this epoch; it is named as superseded and left intact.
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter, OrderedDict
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder import census_partition_builder as CPB  # noqa: E402
from scripts.pettripfinder import hotel_exclusions as HX  # noqa: E402

LP = _REPO_ROOT / "launch_packages" / "pettripfinder"
MARKET = "dayton-oh"
CENSUS = LP / "identity_census" / ("%s.json" % MARKET)
PRIOR = LP / "dayton_final_partition_001.json"
POLICY = LP / ("hotel_policy_facts_%s.json" % MARKET)
EXCL = LP / "markets" / "authority" / MARKET / "hotel_exclusions.json"
OUT = LP / "dayton_final_partition_002.json"

WORK_ORDER = "PTF-DAYTON-OH-HARDENED-APPLICATION-002"
AS_OF = "2026-09-02"

# Evidence-backed state corrections this order makes on rows it did NOT publish.
# Each names the observation that forces it; nothing here is a preference.
CORRECTIONS = {
    "baymont by wyndham greenville": (
        "AWAITING_ROUTING_REPLACEMENT",
        "PTF-DAYTON-OH-HARDENED-REVALIDATION-001 observed the URL on record "
        "redirecting to wyndhamhotels.com/hotels/greenville-ohio?brand_id=BU, a "
        "brand search-results page. The route is provably not this property's "
        "page, so the prior AWAITING_POLICY_OBSERVATION (which asserts the route "
        "is sound) is wrong. The identity stands: a soft-404 is a renamed slug "
        "until the brand inventory says otherwise."),
}


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def build():
    census = {h["identity_key"]: h for h in _load(CENSUS)["hotels"]}
    prior = {i["identity_key"]: i for i in _load(PRIOR)["items"]}
    published = {r["identity_key"] for r in _load(POLICY)["hotels"]}
    excluded_names = {e["normalized_name"] for e in _load(EXCL)["exclusions"]}

    missing = sorted(published - set(census))
    if missing:
        raise SystemExit("published identities absent from the pinned census: %s" % missing)
    unpartitioned = sorted(set(census) - set(prior))
    if unpartitioned:
        raise SystemExit("census identities the prior partition never named: %s" % unpartitioned)

    excluded_keys = set()
    for key, row in census.items():
        if HX.normalize_name(row["canonical_name"]) in excluded_names:
            excluded_keys.add(key)
    overlap = published & excluded_keys
    if overlap:
        raise SystemExit("identities both published and excluded: %s" % sorted(overlap))

    items = []
    corrected = []
    for key in sorted(census):
        row, before = census[key], prior[key]
        if key in published:
            state, determined, reason = "PUBLISHED_PET_FRIENDLY", WORK_ORDER, ""
        elif key in excluded_keys:
            state, determined, reason = "VERIFIED_NO_PETS", WORK_ORDER, ""
        elif key in CORRECTIONS:
            state, why = CORRECTIONS[key]
            determined, reason = WORK_ORDER, why
            corrected.append((key, before["final_state"], state))
        else:
            state = before["final_state"]
            determined = before.get("determined_by", "")
            reason = before.get("state_override_reason", "")
        changed = state != before["final_state"]
        items.append(CPB.partition_item(
            identity_key=key,
            canonical_name=row.get("canonical_name", before["canonical_name"]),
            slug=row.get("slug") or before["slug"],
            city=row.get("city", ""), state=row.get("state", ""),
            postal_code=row.get("postal_code", ""),
            final_state=state,
            next_action_source=("" if changed else before.get("next_action_source", "")),
            determined_by=determined,
            updated_at=AS_OF if changed else before.get("updated_at", AS_OF),
            official_url=row.get("official_url", "") or before.get("official_url", ""),
            state_override_reason=reason,
        ))

    doc = CPB.partition_document(
        MARKET, items, as_of=AS_OF,
        note=("Rebuilt after PTF-DAYTON-OH-HARDENED-APPLICATION-002 applied the "
              "23-row clean inventory recovered by "
              "PTF-DAYTON-OH-HARDENED-REVALIDATION-001. PUBLISHED_PET_FRIENDLY is "
              "derived from the committed policy package and VERIFIED_NO_PETS from "
              "this market's exclusion shard, so neither can drift from the "
              "authority it describes. The census is unchanged at 129: this order "
              "promoted policy, not membership, and the market's census coverage "
              "is NOT confirmed -- the free recensus could not register a local "
              "OSM extract and Marriott refused 244 of 252 scoped pages."),
        source_authorities=[
            "PTF-DAYTON-OH-HARDENED-APPLICATION-002",
            "PTF-DAYTON-OH-HARDENED-REVALIDATION-001",
            "PTF-CENSUS-PARTITION-NORMALIZATION-001 (the states of rows nobody has ruled on since)",
        ])
    doc["supersedes"] = OrderedDict((
        ("path", PRIOR.relative_to(_REPO_ROOT).as_posix()),
        ("work_order", _load(PRIOR).get("work_order", "")),
        ("why", "it describes the 47/8 epoch, before this order applied 7 pet-friendly "
                "records and 16 verified-no-pets exclusions"),
    ))
    doc["state_corrections"] = [
        OrderedDict((("identity_key", k), ("from", a), ("to", b),
                     ("why", CORRECTIONS[k][1]))) for k, a, b in corrected]
    return doc


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=str(OUT))
    args = ap.parse_args(argv)
    doc = build()
    CPB.write_json(Path(args.out), doc)
    counts = Counter(i["final_state"] for i in doc["items"])
    resolved = sum(1 for i in doc["items"] if i["resolved"])
    print("written", os.path.relpath(args.out, str(_REPO_ROOT)))
    print("count", doc["count"], " resolved", resolved, " unresolved", doc["count"] - resolved)
    print(json.dumps(dict(sorted(counts.items())), indent=1))
    print("state corrections:", json.dumps([{k: v for k, v in c.items() if k != "why"}
                                            for c in doc["state_corrections"]]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
