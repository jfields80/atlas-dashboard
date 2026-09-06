"""PTF-CINCINNATI-PROMOTION-AND-APPLICATION-003 -- carry the newly published rows into the seed shard.

The seed shard is the market's list of publishable businesses. A hotel that the
policy package now publishes but the seed shard does not carry would be a record
with nowhere to render, so the two are brought back into agreement here.

WHERE EACH FIELD COMES FROM
---------------------------
The census supplies the address, city, state, postal code and telephone; the
published policy record supplies the name, the official URL and the operative
quote. Nothing is invented and nothing is copied from a sibling row: a field the
census does not carry is written empty rather than guessed.

THE NAME MUST ROUND-TRIP
------------------------
Both the verified-only display join and the public route derive from the published
name, so a name that does not normalise back to its identity key fails the join
CLOSED and the market cannot assemble. Every row added here is asserted to
round-trip before it is written, which is the guard the Louisville promotion added
after an accented character silently broke exactly that join.

Additive only. No existing seed row is rewritten, and no other market is touched.
"""

from __future__ import annotations

import csv
import io
import json
import sys
from pathlib import Path
from typing import Dict, List

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder import market_authority as MA           # noqa: E402
from scripts.pettripfinder.site_data import normalize_name         # noqa: E402

WORK_ORDER = "PTF-CINCINNATI-PROMOTION-AND-APPLICATION-003"
MARKET = "cincinnati-oh"
OBSERVED_ON = "2026-09-05"

PACKAGE = _REPO_ROOT / "launch_packages" / "pettripfinder"
POLICY_PATH = PACKAGE / ("hotel_policy_facts_%s.json" % MARKET)
CENSUS_PATH = PACKAGE / "identity_census" / ("%s.json" % MARKET)
SHARD_PATH = MA.seed_shard_path(MARKET)


def _load(path: Path) -> Dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def sync(write: bool = False) -> Dict:
    policy = _load(POLICY_PATH)
    census = {h["identity_key"]: h for h in _load(CENSUS_PATH)["hotels"]}

    text = SHARD_PATH.read_text(encoding="utf-8-sig")
    existing = list(csv.DictReader(io.StringIO(text)))
    have = {normalize_name(r["name"]) for r in existing}

    added: List[Dict[str, str]] = []
    for record in policy["hotels"]:
        key = record["identity_key"]
        if key in have:
            continue
        cen = census.get(key)
        if cen is None:
            raise SystemExit("%s: %r publishes but is not in the census"
                             % (WORK_ORDER, key))
        name = record["name"]
        if normalize_name(name) != key:
            raise SystemExit(
                "%s: published name %r does not normalise back to its identity key "
                "%r -- the display join and the public route both derive from this "
                "name and would fail closed" % (WORK_ORDER, name, key))
        added.append({
            "name": name,
            "category": "pet-friendly-hotels",
            "address": cen.get("address") or "",
            "city": cen.get("city") or "",
            "state": cen.get("state") or "",
            "postal_code": cen.get("postal_code") or "",
            "phone": cen.get("phone") or "",
            "website_url": record["source_url"],
            "source_url": record["source_url"],
            "source_type": "OFFICIAL_PROPERTY",
            "observed_at": OBSERVED_ON,
            "rating": "",
            "amenities": "",
            "pet_policy": record["evidence"][0]["quote"] if record.get("evidence") else "",
            "canonical": "",
            "market_id": MARKET,
        })

    rows = existing + added
    if write and added:
        # LF-exact bytes: launch_packages/**/*.csv is pinned to eol=lf in
        # .gitattributes, and a CRLF rewrite would change the package hash.
        SHARD_PATH.write_bytes(MA.render_seed_csv(rows).encode("utf-8"))

    return {"work_order": WORK_ORDER, "written": bool(write and added),
            "seed_rows_before": len(existing), "seed_rows_added": len(added),
            "seed_rows_after": len(rows),
            "published_records": len(policy["hotels"]),
            "added_names": [r["name"] for r in added]}


if __name__ == "__main__":
    result = sync(write="--write" in sys.argv)
    print(json.dumps({k: result[k] for k in (
        "seed_rows_before", "seed_rows_added", "seed_rows_after",
        "published_records", "written")}, indent=1))
