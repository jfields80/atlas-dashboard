"""Move the committed Grand Rapids--Holland routing slice into its market shard.

PTF-GRAND-RAPIDS-HOLLAND-SHARD-SYNC-001.  This is a one-time, exact record
migration from the pre-sharding checkpoint.  It never writes the legacy global
authority; ``build_global_authority`` owns that generated compatibility file.
"""
from __future__ import annotations

import json
import subprocess
import sys
from pathlib import Path


MARKET = "grand-rapids-holland-mi"
SOURCE_COMMIT = "03b1aeaacd2ceecdd994616e2372bc0643dab297"
EXPECTED_ROUTING_ROWS = 97
ROOT = Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from scripts.pettripfinder import market_authority as MA  # noqa: E402


def _source_routes() -> list[dict]:
    source = "atlas-dashboard/launch_packages/pettripfinder/identity_routing.json"
    text = subprocess.check_output(
        ["git", "show", "%s:%s" % (SOURCE_COMMIT, source)], cwd=ROOT, text=True
    )
    document = json.loads(text)
    routes = [route for route in document["routes"] if route["market_id"] == MARKET]
    if len(routes) != EXPECTED_ROUTING_ROWS:
        raise SystemExit("expected %d Grand Rapids routes in %s; found %d" % (
            EXPECTED_ROUTING_ROWS, SOURCE_COMMIT, len(routes)))
    return routes


def _write_exact(path: Path, text: str) -> None:
    if path.exists():
        if path.read_text(encoding="utf-8-sig") != text:
            raise SystemExit("refusing to overwrite non-identical existing shard %s" % path)
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def main() -> None:
    routes = _source_routes()
    routing = MA.build_routing_shard(
        MARKET, routes, ["grand-rapids-holland-identity-routing-repair-001"]
    )
    exclusions = MA.build_exclusions_shard(MARKET, [])
    _write_exact(MA.routing_shard_path(MARKET), MA.render_json(routing))
    _write_exact(MA.exclusions_shard_path(MARKET), MA.render_json(exclusions))
    _write_exact(MA.seed_shard_path(MARKET), MA.render_seed_csv([]))
    print("migrated %d Grand Rapids--Holland routing records" % len(routes))


if __name__ == "__main__":
    main()
