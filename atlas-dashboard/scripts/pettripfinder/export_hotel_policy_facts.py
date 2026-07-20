"""PTF-PROD-002A -- explicit exporter for the tracked publishable hotel-policy
facts package.

Reads the approved READY importer candidates from the gitignored operational
corpus (via site_data.load_hotel_policy_facts) and writes the deterministic,
tracked launch package launch_packages/pettripfinder/hotel_policy_facts.json,
which is the DEFAULT source the Columbus generator loads. Running this is the
ONLY step that touches operational data; normal site generation then depends
only on the committed package.

    python scripts/pettripfinder/export_hotel_policy_facts.py [--check]

--check exits non-zero if the tracked package is stale vs the operational corpus
(useful in CI where the corpus is present). No network. Writes only the tracked
package (never inventory, never operational data).
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.site_data import (  # noqa: E402
    PUBLISHED_FACTS_PATH,
    load_hotel_policy_facts,
    normalize_name,
    read_production_rows,
)

SCHEMA_VERSION = "1.0"
MARKET = "columbus-oh"


def build_package() -> dict:
    """Deterministic publishable package from the approved READY facts. Exports
    only publishable content -- the supported structured policy fields (already
    filtered to the policy vocabulary by load_hotel_policy_facts), the exact
    evidence quote, verification state/date, and the official source -- never
    operational metadata (candidate paths, run ids, blocked-source internals)
    and never an invented fact."""
    facts = load_hotel_policy_facts()
    display = {normalize_name(r["name"]): r["name"]
               for r in read_production_rows() if r["category"] == "pet-friendly-hotels"}
    hotels = []
    for key in sorted(facts):
        e = facts[key]
        pets_allowed = e["facts"].get("pets_allowed")
        state = "VERIFIED_NO_PETS" if pets_allowed == "false" else "VERIFIED_PET_FRIENDLY"
        hotels.append({
            "key": key,
            "name": display.get(key, ""),
            "verification_state": state,
            "facts": dict(e["facts"]),          # already filtered to the policy vocabulary
            "evidence_quote": e.get("evidence_quote") or "",
            "verified_at": e.get("verified_at", ""),
            "source_url": e.get("source_url", ""),
            "source_type": e.get("source_relationship", ""),
            "evidence_count": e.get("evidence_count", 0),
        })
    return {"schema_version": SCHEMA_VERSION, "market": MARKET, "hotels": hotels}


def serialize(package: dict) -> str:
    return json.dumps(package, indent=2, ensure_ascii=False, sort_keys=True) + "\n"


def write_package(path: Path = PUBLISHED_FACTS_PATH) -> int:
    text = serialize(build_package())
    path.write_text(text, encoding="utf-8", newline="\n")
    print("wrote %s (%d hotels)" % (path, len(json.loads(text)["hotels"])))
    return 0


def check(path: Path = PUBLISHED_FACTS_PATH) -> int:
    current = path.read_text(encoding="utf-8") if path.exists() else ""
    expected = serialize(build_package())
    if current != expected:
        print("STALE: %s does not match the operational corpus; re-run without --check" % path)
        return 1
    print("OK: %s is up to date" % path)
    return 0


def main(argv=None) -> int:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--check", action="store_true",
                   help="verify the tracked package matches the operational corpus (no write)")
    args = p.parse_args(argv)
    return check() if args.check else write_package()


if __name__ == "__main__":
    raise SystemExit(main())
