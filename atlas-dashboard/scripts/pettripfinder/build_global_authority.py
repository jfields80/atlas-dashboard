"""PTF-MARKET-AUTHORITY-SHARDING-001 -- regenerate the global compatibility files.

The per-market shards under
``launch_packages/pettripfinder/markets/authority/<market_id>/`` are the
authority. The three legacy global files, and the global manifest beside them,
are generated from those shards:

    python -m scripts.pettripfinder.build_global_authority --check
    python -m scripts.pettripfinder.build_global_authority --write

``--check`` is the default and is what CI and the test suite run: it exits
non-zero and names every artifact whose committed bytes are not what the shards
produce. ``--write`` regenerates them.

Deterministic: same shards, same bytes, no clock, no network.
"""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.market_authority import (   # noqa: E402
    MarketAuthorityError,
    build_manifest,
    check_generated_artifacts,
    sharded_market_ids,
    write_generated_artifacts,
)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    group = parser.add_mutually_exclusive_group()
    group.add_argument("--check", action="store_true",
                       help="verify the committed artifacts match the shards "
                            "(default)")
    group.add_argument("--write", action="store_true",
                       help="regenerate the artifacts from the shards")
    args = parser.parse_args(argv)

    try:
        market_ids = sharded_market_ids()
        manifest = build_manifest()
    except MarketAuthorityError as exc:
        print("REFUSED: %s" % exc)
        return 2

    print("markets sharded : %d (%s)" % (len(market_ids), ", ".join(market_ids)))
    print("global routes   : %d" % manifest["global_routing_count"])
    print("global exclusions: %d" % manifest["global_exclusions_count"])
    print("global seed rows: %d" % manifest["global_seed_count"])
    print("build marker    : %s" % manifest["build_marker"])

    if args.write:
        changed = write_generated_artifacts()
        if changed:
            for path in changed:
                print("WROTE  %s" % path)
        else:
            print("no change: generated artifacts already match the shards")
        return 0

    stale = check_generated_artifacts()
    for path in stale:
        print("STALE  %s" % path)
    if stale:
        print("\n%d generated artifact(s) do not match the shards. Run with "
              "--write." % len(stale))
        return 1
    print("all generated artifacts match the shards")
    return 0


if __name__ == "__main__":   # pragma: no cover
    raise SystemExit(main())
