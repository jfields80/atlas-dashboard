"""PTF-RELEASE-FACTORY-BOUNDED-MIGRATION-DECISION-004 -- ONE_TIME_MIGRATION_SEED.

    python mig4_seed.py <dash> <store> <work> <out.json>

Run in the replay worktree BEFORE Columbia is merged (tree = current live source
commit + the repair's factory code only). One whole-site assembly of CURRENT LIVE,
refused unless its bundle IS the live bundle byte for byte; recorded into the
release store at the live release digest; round trip verified. This is the store
migration the repair introduced, not part of any market's stage. No repo writes.
"""
import json
import shutil
import sys
import time
from collections import OrderedDict
from pathlib import Path

DASH, STORE, WORK, OUT = (Path(a) for a in sys.argv[1:5])
sys.path.insert(0, str(DASH))
from scripts.pettripfinder import assemble_production_site as APS  # noqa: E402
from scripts.pettripfinder import release_coordinator as RC  # noqa: E402

out = OrderedDict((("mode", "ONE_TIME_MIGRATION_SEED"), ("dash", str(DASH))))


def save():
    OUT.write_text(json.dumps(out, indent=1, default=str), encoding="utf-8")


live = RC.LiveTruth.read()
live.require_verified()
out["live_deploy_id"] = live.state.deploy_id
out["live_bundle_sha256"] = live.state.bundle_sha256
out["live_release_digest"] = live.digest()
out["live_markets"] = len(live.participating_markets)
if WORK.exists():
    shutil.rmtree(WORK)
t = time.monotonic()
manifest = APS.assemble(str(WORK), keep_fragments=True)
out["assemble_seconds"] = round(time.monotonic() - t, 1)
out["assembled_bundle_sha256"] = manifest["bundle_sha256"]
out["assembled_markets"] = len(manifest["market_fragments_included"])
out["bundle_is_live"] = manifest["bundle_sha256"] == live.state.bundle_sha256
save()
if not out["bundle_is_live"]:
    out["ONE_TIME_MIGRATION_SEED"] = "REFUSED_NOT_LIVE_BUNDLE"
    save()
    raise SystemExit("seed refused: the assembly is not the live bundle")
if STORE.exists():
    shutil.rmtree(STORE)
store = RC.ReleaseStore(STORE)
t = time.monotonic()
seed = store.seed_from_assembly(WORK, manifest, live=live)
out["seed_seconds"] = round(time.monotonic() - t, 1)
stored = store.get_release(live.digest())
out["seed_release_digest"] = seed["release_digest"]
out["round_trip_get_release"] = stored is not None
out["round_trip_identity_is_live_manifest"] = (
    stored is not None and RC.digest_of(RC.release_identity(stored)) == live.digest())
out["fragments_stored"] = len(store.fragment_digests(live.digest()))
out["ONE_TIME_MIGRATION_SEED"] = "SEEDED" if (
    out["round_trip_get_release"] and out["round_trip_identity_is_live_manifest"]
    and out["fragments_stored"] == len(live.participating_markets)) else "FAILED"
save()
print(json.dumps(out, indent=1, default=str))
