# ATLAS-THROUGHPUT-005 — FINAL REPORT

Atomic release coordinator and final candidate lifecycle. Worktree `C:\Atlas-Throughput-V1`, branch
`worker/atlas-throughput-001`, continued from the pushed 004 head `8d946af`. Engineering only: production
authority changed = 0, participation changed = 0, nothing promoted, nothing deployed, no paid provider call.

## PRECHECK

- Worktree `C:\Atlas-Throughput-V1`, branch `worker/atlas-throughput-001`, HEAD at start
  `8d946afdb6c5a2ff625b5906116f27ebe04d2c72` == `origin/worker/atlas-throughput-001`, tree clean.
- 001 TRUE_NEW = 0, 002 = 0, 003 = 0, 004 = 0 (`failure_closures/atlas-throughput-00{1,2,3,4}-1.json`, each
  `all_original_failures_accounted_for = true`; 004's 51 nodes all CLOSED).
- Read before writing anything: the 004 → 005 input packet; the sealed package contract
  (`sealed_market_package.py`), the build input manifest and persistent cache (`bundle_cache.py`), the
  validation receipt and rules A–O (`fast_release_lane.py`), the global artifact dependency map (004's packet),
  the release contracts (`release_contracts.py`), launch participation (`launch_participation.py`), deployment
  authorization and the deployment record (`deployment_authorization.py`), the global manifest
  (`global_deployment.py`), the whole-site composer (`assemble_production_site.py`: `assemble`,
  `build_fragment`, `classify_fragment`, `build_global_home/hotel_index/sitemap/llms`, `file_hashes`,
  `bundle_digest`, `_run_global_publish_gates`, `_run_migration_gate`), the release index and live reconciler
  (`release_index.py`: `current_verified_live`, `live_index`, `compose`, `compare`), and the rollback logic —
  which is not a module but a set of fields and checks spread across the record, the reconciler and rule N.

**One precheck finding worth stating first:** this worktree does not contain Toledo, which is live in
production. The branch forked before that launch, so it IS the stale lineage 005 exists to make harmless.
Everything below treats the committed records as the live truth of this tree, which is exactly what the
coordinator is specified to do.

## 004 INPUT PACKET

Nine inputs (sealed package, validated bundle, build input key, both receipts, current verified live, intended
delta, global release index, unchanged bundle reuse, parent release digest), the global-artifact map, and
seven blockers. Of the seven, 005 closes the first (a composer that accepts N trusted fragments), the third
(participation is now a keyed release input), the fourth (both receipt kinds are joined by one authorization),
the fifth (durable release storage for live and rollback) and the seventh (short scratch roots). Two remain
and are handed to 006: only two markets seal, and the store is seeded from a reproduction rather than from
the deploy.

## CURRENT LIVE MODEL

`release_coordinator.LiveTruth` — read only, and it never writes any of these files.

CURRENT VERIFIED LIVE RELEASE is not one file. Eight committed artifacts claim it, and five facts are stored
in four or more of them:

| fact | claimed in |
|---|---|
| live deploy id | deployment record, deployment-state pin, every sealed package's `parent_live_state` |
| bundle sha256 | deployment record, global manifest, consumed authorization, deployment-state pin (live and source) |
| participating markets | launch participation, global manifest, authorization, record, pin, `parent_live_state` |
| profile counts | global manifest, release contract, market-state pin, authorization, record, pin, `parent_live_state` |
| rollback target | record (`rollback_target` and `previous_deployment_id`), authorization, pin, `parent_live_state` |

The coordinator picks none of them. `release_index.current_verified_live` already reconciles the newest
DEPLOYED record against the global manifest, the deployment-state pin and the consumed authorization, and
turns every disagreement into a `problem`; `LiveTruth` adds the committed-authority index and refuses to be a
parent while any problem stands. `LIVE_REPRESENTATIONS` records all eight paths with their roles (PRIMARY,
CROSS-CHECK, MEMBERSHIP AUTHORITY, SNAPSHOT) so the duplication is visible rather than inherited.

Measured on this tree: verified, deploy `6a9d33f5dc8c3d1cf9464376`, bundle `ca59f3710abde750`, 10 markets,
786 profiles, 945 routes, rollback target `6a9ca921843f2cba2ddf8da1`, parent release digest
`sha256:637e228fc74392b6`.

**Live release manifests predate this module, so the parent is DERIVED, not read** — from the record, the
index and the participation set. That derivation is what gives the first candidate a parent digest to bind to,
and it is content-addressed so it cannot drift. One bug was found and fixed by the seeding run: the derived
manifest was returned by reference, so a caller attaching fragment digests to it silently changed the parent's
own identity. It is now returned as a copy.

## RELEASE MANIFEST

`ptf-release-manifest/1.0`, canonically serialised; the release digest is sha256 over the canonical document
(`atlas_throughput_005_release_manifest.*`). It carries the schema and coordinator version, the parent release
digest, the source commit, context/base_url/anchor, the FINAL participating markets and the participation
document's sha256, one row per market (market id, package digest, build input key, bundle digest, validation
receipt digest, fragment source, fragment digest, profile count, route count), the intended delta and its
digest, every regenerated global artifact with its hash, the global index digest, the deployment artifact
digest, the counts, the validation policy version, the assembler and builder digests, and the status.

Membership is an ARGUMENT to `release_manifest()`. By the time the document exists the participation decision
is inside the bytes that get hashed, which is what makes a pre-flip digest structurally unable to authorize a
post-flip release.

## RELEASE COORDINATOR

`scripts/pettripfinder/release_coordinator.py` — the only writer of staged release manifests. Operations:
`plan`, `stage`, `authorize-record`, `activate-simulated`, `verify-simulated`, `reconcile-simulated`,
`rollback-simulated`, `inspect`, `status`. Lifecycle: SOURCE_READY → CANDIDATE_STAGED → FOUNDER_AUTHORIZED →
LIVE, with FAILED and ABANDONED as terminal states that leave the candidate immutable and live untouched.

`ReleaseStore` (`data/release_store/{releases,fragments,bundles}`) is durable content-addressed storage, not a
cache: it holds the current live release and the rollback target so neither can depend on an evictable
artifact. It was seeded from one whole-site assembly (547.4 s), and the seed was only accepted because the
composed bundle digest equalled the live deployment record's — `ca59f3710abde750`, byte for byte. 10 fragments,
18.4 MB.

## STALE WORKTREE PROTECTION

The preservation baseline is CURRENT VERIFIED LIVE RELEASE. A stale branch contributes exactly one sealed
package delta; every other market is inherited from the release store by fragment digest, and membership comes
from the participation document, never from what happens to exist in the tree. Two independent guards:

1. `_final_membership` refuses any addition or removal relative to live that an explicit authority does not
   name. Absence is never read as a removal.
2. The parent guard refuses activation when the live release is no longer the authorized parent.

## FINAL PARTICIPATION MODEL

There is no build → authorize → flip → rebuild path, because participation is an input to staging. The
candidate that exists is the one with final membership already in it, and its digest is the only digest an
authorization can bind. A pre-flip candidate is a different artifact with a different digest and a different
bundle, and it fails its own route gate — correctly, since it withdraws a live market's routes without a delta
declaring them.

## UNCHANGED BUNDLE REUSE

Per participating market the coordinator resolves a fragment in this order: the delta market from its sealed
package through the 004 persistent cache; otherwise the parent release's stored fragment; otherwise a rebuild
of that market alone. A store miss costs a rebuild of that market and never costs it its place in the release.
Measured: 9 of 10 inherited, 0 rebuilt, 0 builder invocations (the changed market was a cache HIT published in
an earlier run).

## GLOBAL REGENERATION

Ten release-global artifacts, each with a declared class; an artifact with no class refuses staging
(`UNKNOWN_GLOBAL_DEPENDENCY`), so an unknown dependency is never optimised by assumption.

| class | artifacts |
|---|---|
| REGENERATE | `index.html`, `pet-friendly-hotels/index.html`, `sitemap.xml`, `llms.txt` |
| INCREMENTAL | `robots.txt`, `_headers`, `_redirects` |
| REUSE | `about/index.html`, `contact/index.html`, `methodology/index.html` (the anchor's shell) |

No market bundle is rebuilt because a global index changed: market bytes do not read membership, counts, the
release id or the clock (004 measured that, and 005 inherits it).

## CANDIDATE IMMUTABILITY

A candidate is composed into a temporary directory and renamed into place under its own digest. Any semantic
change — membership, package, bundle, global file, parent, intended delta, assembler or builder source —
produces a different digest; a note added beside the candidate does not. `verify_bytes()` re-hashes the staged
bundle and compares it to its own manifest, and both authorization and activation run it.

## FAST RELEASE VALIDATION

003's rules A–O run against the FINAL candidate with the 004 cache supplied, so J and K are satisfied by the
trusted bundle. Measured 5.5 s, `FAST_DATA_ONLY_RELEASE_ELIGIBLE = YES`. Twenty-two composed-bundle gates run
alongside it, all passing, including the two the route accounting added.

A cache hit is artifact identity; the FAST lane is release safety; the authorization is permission. 005 keeps
them three separate things.

## AUTHORIZATION

`ptf-release-authorization/1.0`, written beside the candidate and never into the hashed bytes. It binds four
digests — candidate, deployment artifact, parent release, intended delta — plus the participating markets and
the participation sha256. It refuses when any of them moves, when the candidate is superseded, when the
candidate no longer hashes to its manifest, or when live is no longer the authorized parent. It does not
invalidate because an unrelated report or an offline acquisition helper changed while the candidate bytes
stayed identical. There is no authorization by market name, by branch sha, or of "the latest candidate".

## PARENT GUARD

Before the host is called, `parent_guard` compares the authorized parent release digest with the live release
now. A mismatch is `STALE_PARENT` and the candidate must be re-staged on the new parent — the old
authorization does not follow it, because the new candidate has a different digest.

## ACTIVATION INTERFACE

STAGE, AUTHORIZE, ACTIVATE, VERIFY, RECONCILE, ROLLBACK, against a host adapter. Every refusal is evaluated
before the host is called, so a refused activation cannot have touched live. Activation is idempotent by
operation id: the same id returns the same host deployment and never creates a second one. The record carries
release digest, candidate digest, parent digest, operation id, host deployment id, started/activated/verified
timestamps, the outcome (ACTIVATED / ACTIVATION_FAILED / ACTIVATION_UNKNOWN / ACTIVATION_REFUSED — the order's
RESULT field), the verification results, the rollback target and the source commit. `LIVE` is written only by
`record_verification`, and only when verification passed.

The only adapter shipped is `SimulatedHost`. Nothing in this order contacted Netlify.

## LIVE VERIFICATION CONTRACT

Nine targeted checks, defined in `LIVE_VERIFICATION_CHECKS` and run in 0.022 s against the staged bytes:
release marker, host deployment id, membership, changed-market hub, changed-market profile sample, sitemap
includes the changed market, unrelated-market sample, unrelated route count, asset integrity. Minutes, not a
second broad regression. Against production these need an HTTP client; that is 006.

## ROLLBACK

The target is an exact prior verified release read from durable storage and re-hashed before it is served —
never reconstructed from a branch, an old tree, or approximate counts. The caller must name the release it
believes is current; if a newer release is live the rollback is refused (`RELEASE_NOT_CURRENT`). Measured:
restored `sha256:637e228fc74392b6` / bundle `ca59f3710abde750` with all 10 markets, and the identical rollback
refused once another release was live.

## FAILURE/CRASH CASES

| case | result |
|---|---|
| crash before staging / after staging / after authorization | live unchanged, host never called |
| activation times out | `ACTIVATION_UNKNOWN`, never recorded as LIVE; reconcile says the activation landed and must not be redeployed |
| activation succeeded, local record write failed | reconcile repairs the record; one deployment, no second deploy |
| duplicate activate | idempotent replay, one deployment |
| duplicate authorization | the same authorization id for the same candidate |
| candidate corrupted after authorization | `ACTIVATION_REFUSED` with `CANDIDATE_CORRUPT`, host never called |
| parent changed before activation | `ACTIVATION_REFUSED` with `STALE_PARENT` |
| verification failed after activation | rollback only while the failed release is still current |
| a cache artifact disappears during staging | that market is rebuilt; staging fails closed rather than dropping it; live unaffected |

## RELEASE DIFF

Machine-readable, written before authorization: markets added/removed/updated, per-market profile and route
counts, totals before and after, the global artifacts regenerated, bundles reused and rebuilt, and an
`unexpected_changes` list naming any market that moved but was not the intended one. Measured for the pilot:
786 → 782 profiles, 945 → 939 routes, `markets_updated = [dayton-oh]`, `unexpected_changes = []`.

## DATA-ONLY PILOT

The committed Dayton withdrawal package staged against CURRENT VERIFIED LIVE.

| measure | value |
|---|---|
| candidate digest | `sha256:25b69be224b34ff4` |
| deployment artifact digest | `437439f275b2f276` |
| markets | 10 (9 inherited, 1 from its validated bundle, 0 rebuilt) |
| builder invocations | 0 |
| gates | 22, none failing |
| FAST lane | ELIGIBLE, 5.5 s |
| staged in | **178.0 s** |
| activation / verification | ACTIVATED on the simulator, 9/9 checks, 0.022 s |

**The route gate found a real gap before it shipped.** `deploy/netlify/live_production_routes.txt` is 132
Columbus legacy-namespace routes, not the live site: asking it whether an unrelated market survived returns a
cheerful yes for a release that deleted Dayton. The coordinator now asks the real parent — the routes in the
stored parent bundle — and accounts for every difference:

| accounting | routes |
|---|---|
| parent release | 4,815 |
| candidate | 4,789 |
| declared by the intended delta | 6 |
| consequential to a declared profile removal | 20 |
| undeclared (fatal) | 0 |

The 20 are the five commercial action routes each withdrawn profile owns. A sealed package declares the
INDEXABLE routes a withdrawal removes, because 003's release index models exactly those; the action routes are
a consequence of the profile existing. Counting them as undeclared would fail every honest withdrawal;
ignoring them would let a real loss hide behind a `/go/` prefix. They are now a named third category, and only
when the profile slug they hang off was itself declared removed.

## STALE-LINEAGE PILOT

| measure | value |
|---|---|
| live markets | 10 |
| preserved in the candidate | 10 |
| inherited from the release store | 9 |
| rebuilt | 0 |
| UNINTENDED_REMOVAL | **0** |
| activation on the stale parent | REFUSED (`STALE_PARENT`) |
| host touched by the refusal | no |

## PARTICIPATION PILOT

| measure | value |
|---|---|
| pre-flip candidate | `sha256:a22f1c5123eeb3bf`, 9 markets |
| post-flip candidate | `sha256:25b69be224b34ff4`, 10 markets |
| digests differ / bundles differ | yes / yes |
| pre-flip authorization accepts the post-flip candidate | **no** |
| final membership inside the hashed bytes | yes |
| pre-flip gates | `release.parent_routes_preserved` FAILS — a pre-flip artifact is not releasable |

## PERFORMANCE

| measure | seconds |
|---|---|
| whole-site compose (the thing replaced) | 547.4 |
| parent load + membership | 0.0 |
| fragments (9 inherited + 1 validated bundle) | 76.6 |
| compose | 16.1 |
| gates (22, incl. the parent route accounting) | 76.0 |
| FAST release safety lane | 5.5 |
| **candidate staged, total** | **178.0** |
| targeted live verification | 0.022 |
| rollback from durable storage | 78.7 |
| release store on disk | 25.7 MB |

Target ≤ 15 minutes, preferred ≤ 5: met at 3.0 minutes. Integrity was never weakened to reach it — every
inherited fragment is extracted from a content-addressed object and the composed candidate is re-hashed before
it can be authorized.

## MIGRATION AUDIT

Run: `data/regression/atlas-throughput-005-audit` on the committed 005 change set, clean tree, after the heavy-lane check; every test under `tests/` with the 002 profiler and the session cache ON, classified by NODE ID against `regression_baselines/f75aa95.json` (`atlas_throughput_005_migration_audit.json`). Exactly one broad run.

| measure | 004 audit | 005 audit |
|---|---|---|
| wall | 3,384.8 s | **3669.867 s** |
| collected / passed / failed / skipped | 17,589 / 17,147 / 211 / 231 | 17643 / 17252 / 160 / 231 |
| against f75aa95 | PRE_EXISTING 160, TRUE_NEW 51 -> closed | PRE_EXISTING 160, EXPECTED_EPOCH 0, FLAKE 0, **TRUE_NEW 0** |
| baseline failures now passing | 0 | 0 |
| session cache | 21 reuse hits, 852.0 s avoided | 27 reuse hits, 1013.5 s avoided |
| demo-media module | 1,397.4 s | 1375.7 s |
| peak working set | 8,995 MB | 9111.1 MB |

No TRUE_NEW failure: every failing node id is in the f75aa95 baseline set. No closure needed, no second run.

**Migration audit TRUE_NEW_FAILURE after closure = 0.**

## PRODUCTION ACTIVATION STATUS

RELEASE_COORDINATOR_IMPLEMENTED = YES. RELEASE_COORDINATOR_VALIDATED = YES.
FINAL_CANDIDATE_LIFECYCLE_VALIDATED = YES. **REAL_PRODUCTION_ACTIVATION = DISABLED.**

The only host adapter is a simulator. The production deployer does not import the coordinator; no market was
promoted, no participation record changed, no authority changed, and nothing was deployed. 004's
PRODUCTION_RELEASE_CONSUMPTION and 003's FAST_PATH_PRODUCTION_ACTIVATION both remain DISABLED.

## 006 INPUT PACKET

`atlas_throughput_005_006_input_packet.md`: the eleven artifacts a candidate directory already carries, the
handoff rule (transfer and re-hash, never rebuild — no builder may run between validation, authorization and
deployment), measured shard inputs, four proposed shards with the node-id completeness requirement, the
Windows path-length and toolchain-identity constraints, and the five things still unsolved (only two markets
seal; the store is seeded from a reproduction; no queue scheduler; one adapter and it is a simulator; live
verification is a contract without an HTTP client).

## GIT

Branch `worker/atlas-throughput-001` in worktree `C:\Atlas-Throughput-V1` (no new worktree), continued from
the pushed 004 head `8d946af`. Throughput engineering only: no market authority, no participation, no
promotion, no deployment, no paid call.

| commit | subject |
|---|---|
| `c38ad8b` | ATLAS-THROUGHPUT-005 add atomic release coordinator and final candidate lifecycle (the coordinator, the durable release store, the pilot, 52 tests, the V2 and profiler integration, the reports, the work item and runbook sections, the regenerated matrix and test inventory) |

Untracked measurement directories (`data/release_store/`, `data/release_candidates/`,
`data/regression/atlas-throughput-005-audit/`) and the pilot scratch roots under `C:\ptf005` are gitignored
artifacts, never inputs. The FINAL report is committed on top and the branch pushed; origin == HEAD and a
clean tree are verified after the push and stated in the delivery message.


---

1. CAN A STALE MARKET WORKTREE STILL REMOVE A NEWER LIVE MARKET? **NO** — membership comes from the live
   release and the participation decision; a removal needs an authority naming the market, and the stale-lineage
   pilot preserved all 10 live markets with UNINTENDED_REMOVAL = 0.
2. IS FINAL PARTICIPATION INCLUDED BEFORE THE DEPLOYABLE CANDIDATE IS HASHED? **YES** — participation is an
   input to `release_manifest()`, so it is in the document that gets hashed.
3. CAN A PRE-FLIP / PREVIEW BUNDLE BE USED AS FINAL DEPLOYMENT AUTHORIZATION? **NO** — different digest,
   different bundle, and the pre-flip authorization is refused against the final candidate.
4. ARE UNCHANGED VALIDATED MARKET BUNDLES REUSED? **YES** — 9 of 10 inherited by fragment digest, 0 builder
   invocations for the changed market.
5. HOW MANY UNCHANGED MARKETS WERE REBUILT IN THE STALE-LINEAGE PILOT? **0**.
6. HOW LONG DID THE COMPLETE DATA-ONLY CANDIDATE STAGING PROCESS TAKE? **178.0 seconds** (against 547.4 s for
   the whole-site compose it replaces).
7. DOES FOUNDER AUTHORIZATION BIND THE EXACT CANDIDATE DIGEST AND EXPECTED PARENT LIVE RELEASE? **YES** — and
   the deployment artifact digest and the intended-delta digest as well.
8. IF THE LIVE PARENT CHANGES AFTER AUTHORIZATION, WILL ACTIVATION BE REFUSED? **YES** — `STALE_PARENT`,
   evaluated before the host is called.
9. DOES ROLLBACK TARGET AN EXACT PRIOR VERIFIED RELEASE? **YES** — read from durable storage and re-hashed,
   never reconstructed.
10. CAN A STALE ROLLBACK OVERWRITE A NEWER VALID LIVE RELEASE? **NO** — `RELEASE_NOT_CURRENT`.
11. IS THE EXACT VALIDATED/AUTHORIZED ARTIFACT THE ONLY FUTURE DEPLOYABLE UNIT? **YES** — the host re-hashes
    what it is handed and refuses anything but the authorized bundle digest; no builder runs after
    authorization.
12. WAS REAL PRODUCTION ACTIVATION ENABLED? **NO**.
13. MIGRATION AUDIT TRUE_NEW_FAILURE = **0 (PRE_EXISTING 160 = the f75aa95 set exactly)**
14. IS ATLAS-THROUGHPUT-006 READY? **YES** — the input packet is complete and measured; 006 is not started.

STOP. 006 not started. No market promoted. Nothing deployed.
