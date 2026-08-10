"""PTF-MULTI-MARKET-INVENTORY-SCOPING-001 -- derive a market's package manifest.

Builds a :class:`MarketPackage` from committed authority plus an already-
generated site directory, and writes it OUTSIDE that directory.

The manifest is derived, never authored: counts come from the same authority
files the build reads, and hashes come from the files the build actually wrote.
A hand-maintained manifest would drift from the build the first time anyone
forgot to update it, and a drifting manifest is worse than none because it
looks like verification.

Run:
    python -m scripts.pettripfinder.build_market_manifest \
        --market columbus-oh --site <build>/site --output <path>.json
"""

from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path
from typing import List, Optional

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.hotel_exclusions import load_exclusions          # noqa: E402
from scripts.pettripfinder.market_ownership import owned_by                  # noqa: E402
from scripts.pettripfinder.market_package import (                           # noqa: E402
    MarketPackage, hash_owned_files, write_manifest,
)
from scripts.pettripfinder.markets import (                                  # noqa: E402
    assign_hotels, corridor_route, load_markets, market_by_id,
)
from scripts.pettripfinder.site_data import (                                # noqa: E402
    load_published_hotel_policy_facts, normalize_name, read_production_rows,
    verified_public_hotels,
)


def _slug(text: str) -> str:
    import re
    return re.sub(r"[^a-z0-9]+", "-", (text or "").strip().lower()).strip("-")


def _authority_commit() -> str:
    try:
        return subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(_REPO_ROOT),
                              capture_output=True, check=True).stdout.decode().strip()
    except Exception:                                    # pragma: no cover - git absent
        return "unknown"


def build_package(market_id: str, site_root: Optional[Path] = None,
                  *, confirmed_identity_count: Optional[int] = None) -> MarketPackage:
    market = market_by_id(load_markets(), market_id)
    rows = owned_by(read_production_rows(), market_id, context="market manifest")
    hotel_rows = [r for r in rows if r.get("category") == "pet-friendly-hotels"]
    verified = verified_public_hotels(hotel_rows, load_published_hotel_policy_facts())

    assignment = assign_hotels(market, verified, fail_closed=False)
    hotel_routes = tuple(sorted("/pet-friendly-hotels/%s/" % _slug(r["name"])
                                for r in verified))
    corridor_routes = tuple(sorted(
        corridor_route(market, market.corridor_by_id(cid))
        for cid in assignment.published))
    unassigned = tuple(sorted(r["name"] for r in assignment.unassigned))

    # Only VERIFIED_NO_PETS counts as "verified no pets". The exclusions file
    # also carries OUT_OF_CURRENT_CATEGORY rows (a bed-and-breakfast and a
    # guesthouse), and counting the file's length would report 16 where the
    # market has 14 -- overstating negative evidence by two properties.
    exclusions = [e for e in load_exclusions()
                  if str(e.get("market_id") or market_id) == market_id
                  and e.get("exclusion_state") == "VERIFIED_NO_PETS"]

    # The confirmed universe lives in the market's identity census when one is
    # committed; otherwise the caller supplies it. It is never inferred from
    # published + excluded, which would silently under-report every hotel that
    # is confirmed but still unresolved.
    confirmed = confirmed_identity_count
    if confirmed is None:
        census = (_REPO_ROOT / "launch_packages" / "pettripfinder" / "identity_census"
                  / ("%s.json" % market_id))
        if census.is_file():
            confirmed = int(json.loads(census.read_text(encoding="utf-8-sig")).get("count") or 0)

    published = len(verified)
    no_pets = len(exclusions)
    unresolved = None if confirmed is None else max(0, confirmed - published - no_pets)

    file_hashes = {}
    if site_root is not None:
        file_hashes = hash_owned_files(Path(site_root), hotel_routes + corridor_routes)

    return MarketPackage(
        market_id=market_id,
        authority_commit=_authority_commit(),
        confirmed_identity_count=confirmed,
        published_pet_friendly_count=published,
        verified_no_pets_count=no_pets,
        unresolved_count=unresolved,
        hotel_routes=hotel_routes,
        corridor_routes=corridor_routes,
        corridor_unassigned_hotels=unassigned,
        file_hashes=file_hashes,
    )


def main(argv: Optional[List[str]] = None) -> int:
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument("--market", required=True)
    ap.add_argument("--site", default=None, help="generated site root (for file hashes)")
    ap.add_argument("--output", default=None, help="manifest path (MUST be outside --site)")
    ap.add_argument("--confirmed", type=int, default=None)
    args = ap.parse_args(argv)

    site = Path(args.site) if args.site else None
    pkg = build_package(args.market, site, confirmed_identity_count=args.confirmed)

    if args.output:
        out = Path(args.output)
        if site is not None and site.resolve() in out.resolve().parents:
            raise SystemExit(
                "refusing to write the manifest inside the generated site (%s): it would "
                "change the bundle it describes" % site)
        write_manifest(pkg, out)
        print("manifest written:", out)

    c, p, n, r, u = pkg.reconciliation()
    print("=== MARKET PACKAGE: %s ===" % pkg.market_id)
    print("  authority commit          :", pkg.authority_commit[:12])
    fmt = lambda v: "n/a" if v is None else str(v)
    print("  reconciliation            : %s confirmed / %d published / %d no-pets / %d resolved / %s unresolved"
          % (fmt(c), p, n, r, fmt(u)))
    if c is None:
        print("  note                      : this market commits no identity census, so the"
              " confirmed universe is not derivable here; pass --confirmed to state it.")
    print("  owned hotel routes        :", len(pkg.hotel_routes))
    print("  owned corridor routes     :", len(pkg.corridor_routes))
    print("  corridor-unassigned, still published:", len(pkg.corridor_unassigned_hotels))
    print("  owned files hashed        :", len(pkg.file_hashes))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
