# ATLAS-THROUGHPUT-005 → 006 input packet

Status: PROPOSED. 006 is REMOTE CI SHARDING + TRUSTED ARTIFACT HANDOFF + RELEASE LANE. Nothing here is
implemented in 005.

## What 006 inherits (all measured, all committed)

| input | where | identity |
|---|---|---|
| SEALED PACKAGE | `markets/packages/<market>/<package_id>.json` (003) | `package_digest` |
| VALIDATED MARKET BUNDLE | `data/bundle_cache/objects/<bundle sha>.zip` (004) | `output_bundle_digest` |
| DURABLE RELEASE STORE | `data/release_store/{releases,fragments,bundles}` (005) | fragment digest / bundle digest |
| CURRENT VERIFIED LIVE RELEASE | `release_coordinator.LiveTruth` over `release_index.current_verified_live` | `parent_release_digest` |
| STAGED CANDIDATE | `data/release_candidates/<digest[7:23]>/` | `candidate_digest` = sha256 over the canonical release manifest |
| RELEASE MANIFEST | `<candidate>/release_manifest.json` | `ptf-release-manifest/1.0` |
| RELEASE DIFF | `<candidate>/release_diff.json` | parent → candidate, per market |
| FAST LANE RECEIPT | `<candidate>/fast_lane_receipt.json` (003 rules A–O) | receipt digest |
| AUTHORIZATION | `<candidate>/authorization.json` | binds candidate + bundle + parent + intended delta |
| GATE RESULTS | `<candidate>/gates.json` | 20 gates over the composed candidate |
| TELEMETRY | `<candidate>/telemetry.json` | the release-operation row 006 ships to CI |

## The handoff format 006 needs

A candidate directory is already self-describing and content-addressed: `site/` (the deployable bytes),
`release_manifest.json`, `release_diff.json`, `gates.json`, `fast_lane_receipt.json`, `telemetry.json`, and
`authorization.json` once signed. Everything required to deploy is present before authorization, and the
deployable identity (`bundle_digest(file_hashes(site))`) is recomputable by the receiver. 006's handoff is
therefore a transfer of that directory plus a re-hash on arrival — not a rebuild.

**The one rule 006 must not break:** no builder may run between validation, authorization and deployment. A
remote runner that rebuilds to deploy has produced a different artifact, whatever its inputs were.

## Measured inputs for shard planning

| measure | value | source |
|---|---|---|
| broad suite, whole tree | 17,589 collected, ~56 min, peak ~9.0 GB | 004 migration audit |
| demo-media module alone | ~1,397 s, 57–71% of every broad run | 001 baseline, 004 audit |
| whole-site compose (10 markets) | 547.4 s | 005 seeding run |
| candidate staging (9 inherited + 1 validated bundle) | 155.4 s | 005 data-only pilot |
| of which fragments / compose / gates / FAST lane | 82.7 / 17.7 / 45.6 / 5.8 s | 005 data-only pilot |
| targeted live verification | under 1 s, 9 checks | 005 verification contract |
| release store on disk | 18.4 MB for one 10-market release | 005 seeding run |
| warm market bundle reuse | 3.7 s Dayton, 8.4 s Cleveland | 004 |

## Shard candidates (proposed, not measured as shards yet)

1. **demo-media integration** — the single largest module; already isolated as its own lane by 002.
2. **per-market release contracts** — `TestEveryMarketAssembles` assembles every market's bundle and is
   deferred out of every lane today; it is the natural second shard and the reason 004 needed
   `validate --exercised-junit`.
3. **the acquisition suites** — large, independent, no assembly.
4. **contracts + pins** — fast, and the right smoke shard.

Node-id completeness is mandatory: the classifier proves closure by node id, so every shard must emit junit
with `classname` + `name` for every test, and the union of shards must equal the whole-tree node-id set. A
shard that silently collects fewer nodes reads as "not exercised", never as "passed".

## Host compatibility

Windows `MAX_PATH` is the live constraint: staged builds fail above roughly 120 characters of work-directory
prefix, so both the coordinator and the bundle cache take short scratch roots (`C:\\ptf005\\...`). A remote
runner on Linux removes that constraint but changes the toolchain identity in the 004 build input key, so a
Linux-built bundle is a cache MISS against a Windows-built one by design. 006 must decide whether CI
publishes into the trusted cache at all, or only validates.

## What is still not solved

1. **Only two markets seal.** Dayton and Cleveland; the other eight are refused by the writer on legacy
   authority facts. Every unchanged market therefore enters a candidate as a stored fragment rather than a
   receipted package bundle, which is safe but weaker: the fragment's identity is its bytes, not a validation
   receipt. A data order per market is the honest fix.
2. **The release store is seeded from a reproduction, not from the deploy.** The seed is trustworthy here
   because the composed digest equalled the live record's, but a store populated directly from the deployed
   artifact would remove the reproduction step entirely.
3. **No queue scheduler.** 005 admits one delta per release and proves serialized lineage; deciding WHICH
   ready package goes next is 006 or later.
4. **The activation interface has one adapter, and it is a simulator.** A real adapter needs the Netlify
   specifics (`--no-build`, the scaffolded `.netlify/`, deploy-id reconciliation) that the deployment orders
   already documented.
5. **Live verification is a contract, not an implementation.** The nine checks are defined and run against
   staged bytes; against production they need an HTTP client and the live route sample.

`REAL_PRODUCTION_ACTIVATION` remains DISABLED, and 006 does not change that.
