# ATLAS-THROUGHPUT-006 — FINAL REPORT

Remote CI sharding, trusted artifact handoff and the production release lane. Worktree
`C:\Atlas-Throughput-V1`, branch `worker/atlas-throughput-001`, continued from the pushed 005 head `5da74f3`.
Engineering only: no market authority changed, no participation changed, nothing promoted, nothing deployed,
no paid provider call.

## PRECHECK

- Worktree `C:\Atlas-Throughput-V1`, branch `worker/atlas-throughput-001`, HEAD at start
  `5da74f3aae4c71d63411777b11b87c9cd4ede2bf` == `origin/worker/atlas-throughput-001`, tree clean.
- 001 TRUE_NEW = 0, 002 = 0, 003 = 0, 004 = 0 (each closure `all_original_failures_accounted_for = true`;
  004's 51 nodes all CLOSED). 005 = 0 with no closure file, because it had no true-new failure to close —
  its audit classified 160 PRE_EXISTING and 0 TRUE_NEW.
- Read mechanically rather than assumed: the git remote (`github.com/jfields80/atlas-dashboard`), **the
  complete absence of any CI configuration** (no `.github`, no GitLab, Jenkins, Circle, Azure or Travis file
  anywhere in the tree), `pytest.ini` and its lane markers, Regression V2 and the lane runner, the collection
  inventory, `netlify.toml`, the committed deployment records and authorizations, `requirements*.txt` as the
  only lockfiles, Python 3.13.5 and Node v22.17.0, and the Windows path-length constraint.

**One precheck finding carried forward from 005:** this worktree still does not contain Toledo, which is live
in production. Its committed live records are one release behind. Everything below is measured against this
tree's records, which is what the coordinator is specified to use, and it is a blocker recorded for 008.

## 005 INPUT PACKET

Eleven artifacts a candidate directory already carries, the handoff rule, measured shard inputs, four proposed
shards with the node-id completeness requirement, the Windows and toolchain constraints, and five unsolved
items. 006 implements the handoff rule, the shards, the completeness contract and the queue; it does not solve
"only two markets seal" or "the store is seeded from a reproduction", both of which stay with 007/008.

## CI PROVIDER

**GitHub Actions**, `.github/workflows/ptf-broad-validation.yml`, `workflow_dispatch` ONLY.

The repository's only remote is GitHub and it had no CI of any kind, so Actions is the provider that needs no
new account. The workflow is committed and complete. It was **not executed**: the GitHub CLI is not installed
here and no API token is available, so neither Actions' availability for this repository nor what a run would
bill could be established from this checkout, and dispatching one would be provisioning infrastructure without
authorisation.

**REMOTE_EXECUTION_NOT_PROVEN.** No remote run was faked. The `workflow_dispatch`-only trigger means
committing the file starts nothing and spends nothing.

## TEST INVENTORY

Measured from the 005 audit's profiler output — a real broad run, not an estimate: **604 modules, 17,643
tests, 3,621.7 s** of test time.

| module | seconds | tests | share |
|---|---|---|---|
| `test_pettripfinder_demo_media.py` | 1,375.7 | 18 | 38% |
| `test_global_deployment_architecture_045.py` | 750.0 | 46 | 21% |
| `test_per_market_release_contracts.py` | 353.7 | 240 | 10% |
| everything else (601 modules) | 1,142.3 | 17,339 | 31% |

The cost is concentrated in three modules that are 68% of the suite. That single fact determines the shard
design and is the most important measurement in this order.

## SHARD DESIGN

Four jobs, balanced by measured duration, longest-processing-time first, at **module** granularity.

| shard | category | modules | tests | measured s |
|---|---|---|---|---|
| 1 | website-generation chain | 1 | 18 | 1,375.7 |
| 2 | global deployment architecture | 1 | 46 | 750.0 |
| 3 | per-market release contracts + 299 more | 300 | 8,673 | 748.0 |
| 4 | contracts, core and the long tail | 302 | 8,906 | 748.0 |

Three deliberate choices, each contradicting an obvious default:

- **Not balanced by test count.** Counting tests would put 8,900 cheap tests opposite 18 expensive ones.
- **Not grouped by the four named categories.** The assembly-heavy category alone measures about 2,800 s, so
  grouping it would roughly double the wall clock. The order permits adjusting the split when measurements
  say so, and they do.
- **Not split below a module.** A module's session fixtures are the expensive part — the website-generation
  chain peaks near 9.1 GB — and splitting one would run that fixture twice. This is the `pytest -n auto` trap
  the order warns about, and it is why job-level parallelism was chosen over xdist.

**The wall clock is bounded by one indivisible module.** Four shards and eight shards both finish in 1,375.7 s.
More runners buy nothing until `test_pettripfinder_demo_media.py` is itself divisible, which is item one of
the 007 packet.

## NODE COMPLETENESS

A sharded run is a run only if every planned node id is accounted for exactly once. Proved over the real 005
audit junit, partitioned by the committed manifest and verified by the same `ci_report` code the workflow runs.

| measure | value |
|---|---|
| planned node ids | 17,643 |
| executed | 17,643 |
| explicitly excluded | 0 |
| unassigned | 0 |
| PRE_EXISTING / TRUE_NEW | 160 / 0 |
| complete | YES |

**This contract caught a real defect before it shipped.** The first simulation left 11,600 of 17,643 cases
unassigned, because the shard lookup derived a module from the junit classname without stripping the test
class. The run failed and named the missing nodes rather than reporting a cheerful partial green. Had the
contract been advisory, a broad "green" run would have skipped two thirds of the suite.

Failure modes, each of which fails the RUN and not merely a shard: missing shard, timed-out shard, cancelled
shard, collection error, missing node, unintended duplicate, unplanned node, missing artifact. A shard's own
exit status is deliberately not the verdict — the 160 baseline failures make every honest broad run exit
non-zero, and a workflow that treated that as failure would teach everyone to ignore it.

## REGRESSION V2 DISPATCH

The remote validator consumes V2's existing plan; it does not invent a second policy.

| change | remote broad jobs |
|---|---|
| proven data-only market authority | **0** |
| shared runtime | 4 |
| shared schema | 4 |
| assembler | 4 |
| deployment | 4 (deployment modules are spread across every shard by the duration balance) |
| unknown or mixed | 4 |

Honest consequence of a duration-balanced split: most broad requirements resolve to every shard, because the
modules that prove a surface are spread across all four. The saving that matters is therefore not a smaller
broad run — it is **not running one at all** for the ordinary release.

## REMOTE VALIDATION RECEIPT

`ptf-ci-validation-receipt/1.0` binds the run id, source commit, candidate digest, parent release digest,
change class, dependency digest, shards required and completed, the node-id accounting, result counts, the
classified failures, artifact digests, the environment and its Python and Node versions, timestamps, the
result, and its own digest. "CI passed" is a string; this is checkable. The coordinator refuses a receipt that
is incomplete, binds another candidate or commit, ran against a different dependency digest, is stale beyond
seven days, completed fewer shards than policy required, failed node completeness, or carries any true-new
failure.

## LEGACY FAILURE HANDLING

A failure is PRE_EXISTING only when the node id is in the f75aa95 baseline **and** its normalised signature
matches; addresses, absolute paths, temp paths and timestamps are normalised away so a signature survives a
different machine. The same node failing for a materially different reason is TRUE_NEW — the baseline records
that a test fails, not a licence for it to fail in new ways. The baseline is never normalised into green.

Gap recorded honestly: the committed baseline carries node ids but no signatures, so today the signature check
only strengthens classification where a caller supplies them. Recording signatures is item three of the 007
packet.

## ARTIFACT HANDOFF and BYTE ROUND TRIP

A candidate travels as a deterministic content-addressed archive with per-file digests. CI may COPY, EXTRACT,
HASH, READ and TEST. It may not rebuild a replacement and call it equivalent: `substitution_problems` compares
a received tree against the SENDER's digests, so a regenerated candidate is caught as a different artifact.

Measured on the real 005 candidate:

| hop | deployment artifact digest |
|---|---|
| staged locally | `437439f275b2f276` |
| recorded in the handoff manifest | `437439f275b2f276` |
| after receipt and re-hash | `437439f275b2f276` |

The candidate digest is identical staged and received, repackaging the received tree reproduces the same
archive digest, and there were zero problems.

## CROSS PLATFORM

The factory builds on Windows; a runner is likely Linux. The archive stores bytes and a fixed mode and the
receiver proves the digest, so line endings, path case and file modes cannot drift in transit. Linux never has
to reproduce Windows output — it carries it and tests it.

Audited on the real candidate: 4,807 files, **0** CRLF files, **0** case collisions, longest path 122
characters, no backslash members, no executable bits. The artifact is already cross-platform clean.

## HOST ADAPTER

`NetlifyHost`, with its semantics read from `netlify.toml` and the committed records rather than guessed:
prebuilt manual deploys with `--no-build` (without it the CLI runs a git build and uploads nothing from
`--dir`), the site linked at deploy time by `NETLIFY_SITE_ID`, 24-hex deploy ids, per-deploy URLs at
`<deploy-id>--<site>.netlify.app`, and a gitignored `.netlify/` the CLI scaffolds that fails the assembler
gate.

Two host facts that shape the design: upload and publish are ONE operation for `--prod`, so there is no
separate activate step to hold and the parent guard must run immediately before the call; and rollback is
"publish an earlier deploy", not "undo", which is why 005 keeps the previous release in durable storage.

The adapter is constructed **disabled** and refuses every mutating command in that state, while still
returning the exact command it would run so the plan stays reviewable.

## HTTP LIVE VERIFICATION

005's nine checks, now asked of a real origin: release marker, host deployment id, membership, changed-market
hub, changed-market profile sample, sitemap inclusion, unrelated-market sample, unrelated route count, asset
integrity. Bounded retries with backoff.

**A timeout is UNKNOWN** — not a pass, not a failure, and never grounds for a rollback until the host has been
reconciled. Only a definite failure on a critical check permits one, and only while the failed release is
still current. Tested against a served fixture and against a silent origin; production was not contacted.

## RELEASE QUEUE and ACTIVATION SERIALIZATION

A durable JSON queue with twelve states and a checked transition table, keyed by `(market_id,
package_digest)`. The same package submitted twice is one entry. A newer package supersedes an older one only
explicitly, and only while the older has not started work.

The activation lease has a single holder and protects one thing: the CURRENT LIVE to NEXT LIVE transition. It
does not protect research, sealing, cache lookups or candidate planning, all of which stay parallel. It
carries a TTL so a crashed holder cannot block the factory, and a takeover is recorded rather than silent.

## OVERLAP and REBASE

Proved: while release A holds the lease and activates, release B validates and stages. B cannot acquire the
lease. When A goes live, B's parent has moved, so `AUTHORIZED -> CANDIDATE_STAGED` restages it on the new
parent and its authorization does not follow, because the restaged candidate has a different digest. Unchanged
markets stay reusable across that restage — the 005 pilot's nine inherited bundles and zero rebuilds are
unaffected by a parent change.

## DATA-ONLY PROOF

The path that matters, on a real classified change:

```
sealed market package -> MARKET_AUTHORITY_DATA_ONLY -> FAST_DATA_ONLY_RELEASE
-> trusted cached bundle -> coordinator candidate -> REMOTE_BROAD_JOBS = 0
```

`dispatch = NONE`, because the FAST lane proved the package on its own evidence and V2 says
FULL_REGRESSION_REQUIRED = NO. The coordinator records the remote validation state as
`NOT_REQUIRED_BY_POLICY`, which is a decision rather than a gap.

## SHARED-CHANGE PROOF

Shared runtime, shared schema, assembler, deployment and unknown all select four shards. A mixed change
containing both a data-only authority edit and a shared runtime edit selects four: the selector cannot
under-scope.

## REMOTE BROAD BENCHMARK

**NOT EXECUTED** — REMOTE_EXECUTION_NOT_PROVEN.

The shard plan was instead validated against a real broad run: the 005 audit's junit partitioned by the
committed manifest, with the measured per-shard times matching the plan within a second (748.8 and 748.9
against 748.0 predicted).

| measure | value |
|---|---|
| local broad run, one process | 3,669.9 s (61 min), desktop blocked |
| projected remote wall, four shards | 1,375.7 s (22.9 min) |
| projected aggregate runner time | 3,623.4 s |
| projected improvement | 2.67x wall clock |

Four memory-heavy local jobs were not started simultaneously on this machine, per the order.

## PRODUCTION FEATURE GATE

`launch_packages/pettripfinder/release_production_gate.json`:
`RELEASE_COORDINATOR_PRODUCTION_ENABLED = NO`, `RELEASE_COORDINATOR_PRODUCTION_ALLOWED_MARKETS = []`.

A missing gate file is a closed gate: the absence of a permission is not a permission. The coordinator's
`deployment_eligible` reports YES or NO with reasons, requiring the candidate's own bytes, an authorization
binding four digests, the parent guard, the package and bundle receipts, a CI receipt when policy demands one,
and the market's presence in the allowlist. With the allowlist empty, no market can be deployed by this
machinery whatever else is green.

## PILOT MARKET RECOMMENDATION

**Recommended: `dayton-oh`. The founder chooses; 006 selected and deployed nothing.**

It is the only market with a committed sealed package on this branch, it is already live so the pilot
exercises the machinery without admitting a new market to production, its candidate is already staged, gated,
diffed and FAST-lane eligible, and its blast radius is four profiles and six routes with the current live
release held byte-identical in durable storage as the rollback target.

Lexington, Nashville and Chattanooga are shadow-ready but unregistered on this branch; launching a new market
is a larger first pilot than the machinery needs.

Blockers before any pilot: the gate must be opened per market by the founder; a shared-change pilot would need
a remote receipt that does not exist yet; and this worktree's live records are one release behind production.

## PERFORMANCE SCORECARD

| stage | measured |
|---|---|
| market-local validation (002) | ~318 s |
| FAST data-only release safety (003) | 60.9 s standalone, 5.5 s inside a 005 candidate |
| warm validated bundle reuse (004) | 3.7 s Dayton, 8.4 s Cleveland, 0 builder invocations |
| whole-site compose (005) | 547.4 s |
| data-only candidate staging (005) | 178.0 s, 9 of 10 markets inherited, 0 rebuilt |
| candidate handoff round trip (006) | byte-identical, deterministic archive |
| local broad regression | 3,669.9 s, desktop blocked |
| remote broad, projected | 1,375.7 s wall, 3,623.4 s aggregate, NOT EXECUTED |
| **ordinary data-only release, remote broad jobs** | **0** |

Not yet measured: founder active time per release, queue wait, CI wait, and activation plus verification
against production. 006 does not claim throughput proof; 008 is the experiment.

## MIGRATION AUDIT

Run: `data/regression/atlas-throughput-006-audit` on the committed 006 change set, clean tree, after the heavy-lane check; every test under `tests/` with the 002 profiler and the session cache ON, classified by NODE ID against `regression_baselines/f75aa95.json` (`atlas_throughput_006_migration_audit.json`). Exactly one broad run.

| measure | 005 audit | 006 audit |
|---|---|---|
| wall | 3,669.9 s | **3,674.5 s** |
| collected / passed / failed / skipped | 17,643 / 17,252 / 160 / 231 | 17,699 / 17,308 / 160 / 231 |
| against f75aa95 | PRE_EXISTING 160, TRUE_NEW 0 | PRE_EXISTING 160, EXPECTED_EPOCH 0, FLAKE 0, **TRUE_NEW 0** |
| baseline failures now passing | 0 | 0 |
| session cache | 27 reuse hits, 1,013.5 s avoided | 27 reuse hits, 1,043.2 s avoided |
| demo-media module | 1,375.7 s | 1,349.7 s |
| peak working set | 9,111 MB | 8,802 MB |

The suite grew by 56 tests (the 006 module) and the failure set did not move: same 160 node ids, same
baseline, nothing new.

No TRUE_NEW failure: every failing node id is in the f75aa95 baseline set. No closure needed, no second run.

**Migration audit TRUE_NEW_FAILURE after closure = 0.**

## 007 INPUT

`atlas_throughput_006_007_input_packet.md`: bounded debt payment. Split or shrink the demo-media module (38%
of the suite and the floor on every sharded run), retire the count pins that break on every application order,
give the 160 baseline failures signatures rather than bare node ids, and quarantine with a stated reason
rather than silence. Explicitly not a renovation of historical suites.

## 008 INPUT

`atlas_throughput_006_008_input_packet.md`: what the three-market day now has, and the five things it still
needs — three registered and sealed markets, a tree whose live records are current, an opened production gate,
remote execution actually proven, and the four measurements 006 could not take. The quality floors do not move
for the experiment.

## GIT

Branch `worker/atlas-throughput-001` in worktree `C:\Atlas-Throughput-V1` (no new worktree), continued from
the pushed 005 head `5da74f3`. Throughput engineering only: no market authority, no participation, no
promotion, no deployment, no paid call.

| commit | subject |
|---|---|
| `3ad9033` | ATLAS-THROUGHPUT-006 add remote validation and trusted release handoff (the CI policy and shard planner, the node-id completeness contract, the receipt contract and reporter, the artifact handoff, the release queue and activation lease, the Netlify adapter and HTTP verification client, the dispatch-only workflow, the empty production gate, the coordinator's DEPLOYMENT_ELIGIBLE, V2 narrowing blockers, 56 tests and the reports) |

Untracked measurement directories (`data/regression/atlas-throughput-006-audit/`) and the scratch roots under
`C:\ptf006` are gitignored artifacts, never inputs. The FINAL report is committed on top and the branch
pushed; origin == HEAD and a clean tree are verified after the push and stated in the delivery message.


---

1. CAN REQUIRED BROAD REGRESSION NOW RUN WITHOUT BLOCKING THE FOUNDER'S LOCAL MARKET-RESEARCH MACHINE?
   **IMPLEMENTED_NOT_EXECUTED** — the workflow, the shard plan, the completeness contract and the receipt are
   complete and tested; no remote run was dispatched because Actions' availability and billing could not be
   established from this checkout.
2. HOW MANY REMOTE SHARDS ARE USED? **4**.
3. WHAT WAS THE WALL CLOCK OF THE REMOTE BROAD RUN? **NOT EXECUTED.** Projected 1,375.7 s (22.9 min) from
   measured per-module durations, validated against a real broad run's junit.
4. DOES AN ORDINARY PROVEN DATA-ONLY RELEASE REQUIRE A REMOTE BROAD RUN? **NO**.
5. HOW MANY BROAD JOBS DOES THE NORMAL DATA-ONLY PATH REQUEST? **0**.
6. CAN CI REBUILD/SUBSTITUTE DIFFERENT BYTES AFTER CANDIDATE VALIDATION? **NO** — the receiver compares
   against the sender's per-file digests, so a rebuilt tree is refused as a different artifact.
7. DID THE CANDIDATE SURVIVE THE ARTIFACT HANDOFF BYTE-IDENTICAL? **YES** — `437439f275b2f276` staged, in the
   archive and after receipt, with a deterministic repackage.
8. DOES THE CI RECEIPT BIND THE EXACT CANDIDATE/COMMIT/DEPENDENCY/SUITES? **YES**, and its own digest.
9. WILL A MISSING/TIMED-OUT SHARD FAIL THE VALIDATION? **YES**.
10. CAN MARKET RESEARCH CONTINUE LOCALLY WHILE REMOTE VALIDATION RUNS? **YES** — the broad run leaves the
    desktop, and the activation lease protects only the live transition.
11. IS ACTIVATION STILL SERIALIZED AND GUARDED BY CURRENT LIVE PARENT? **YES**.
12. IF RELEASE A GOES LIVE WHILE RELEASE B WAS PREPARED, CAN B SAFELY RESTAGE ON THE NEW PARENT? **YES**, and
    its old authorization does not follow it.
13. IS REAL PRODUCTION ACTIVATION STILL BEHIND AN EXPLICIT EMPTY PILOT GATE? **YES**.
14. WAS ANY REAL MARKET DEPLOYED IN 006? **NO**.
15. MIGRATION AUDIT TRUE_NEW_FAILURE = **0 (PRE_EXISTING 160 = the f75aa95 set exactly)**
16. ARE 007 AND 008 READY? **YES** — both input packets are complete and measured; neither is started.

STOP. 007 not started. 008 not started. No market deployed.
