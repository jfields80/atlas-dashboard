"""PTF-RELEASE-STORE-LIVE-CONTENT-KEY-CORRECTION-005 -- Phase 1 identity snapshot.

    python mig5_identity.py <dash> <label> <out.json>

Records, for the tree as it stands: the deployed-content identity (the committed
live record's bundle_sha256, sitemap_sha256, route/profile counts) and the
release-manifest digest with every field that contributes to it, plus the live
release index's registered-vs-participating markets. Read only.
"""
import json
import sys
from collections import OrderedDict
from pathlib import Path

DASH, LABEL, OUT = Path(sys.argv[1]), sys.argv[2], Path(sys.argv[3])
sys.path.insert(0, str(DASH))
from scripts.pettripfinder import release_coordinator as RC  # noqa: E402

live = RC.LiveTruth.read()
manifest = live.manifest()
out = OrderedDict((
    ("label", LABEL),
    ("head", __import__("subprocess").run(["git", "-C", str(DASH), "rev-parse", "HEAD"], capture_output=True,
                                          text=True).stdout.strip()),
    ("live_verified", live.verified),
    ("deployed_content_identity", OrderedDict((
        ("bundle_sha256", live.state.bundle_sha256),
        ("sitemap_sha256", live.state.sitemap_sha256),
        ("deploy_id", live.state.deploy_id),
        ("participating_markets", len(live.participating_markets)),
        ("total_profiles", live.state.total_profiles),
        ("sitemap_route_count", live.state.sitemap_route_count),
    ))),
    ("release_manifest_digest", live.digest()),
    ("release_manifest_fields", sorted(manifest)),
    ("global_index_digest", manifest.get("global_index_digest")),
    ("index_markets_registered", len(live.index.markets)),
    ("index_markets_not_participating", sorted(set(live.index.markets) - set(live.participating_markets))),
    ("manifest_without_global_index_digest", RC.digest_of(OrderedDict(
        (k, v) for k, v in manifest.items() if k != "global_index_digest"))),
))
OUT.write_text(json.dumps(out, indent=1), encoding="utf-8")
print(json.dumps(out, indent=1))
