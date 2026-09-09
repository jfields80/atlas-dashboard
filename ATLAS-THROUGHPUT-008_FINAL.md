# ATLAS-THROUGHPUT-008 — FINAL REPORT

Live three-market factory proof and the continue / redesign / retire decision. Worktree
`C:\Atlas-Throughput-V1`, branch `worker/atlas-throughput-001`, continued from the pushed 007 head
`ab1e7a56efe5ff73cd461bbdcd7b479dc3dca1b7`. No market authority changed, no participation changed, nothing
promoted, **nothing deployed**, no paid provider call.

## PRECHECK

HEAD equalled origin at `ab1e7a5`, tree clean. Migration audits: 002, 003 and 004 carried true-new failures
that were closed by committed node-id closures; 005, 006 and 007 each ended at TRUE_NEW = 0 against the same
160-node baseline.

**Every production flag is DISABLED**, and that governs this entire order:

| flag | state |
|---|---|
| `FAST_PATH_PRODUCTION_ACTIVATION` | DISABLED |
| `PRODUCTION_RELEASE_CONSUMPTION` | DISABLED |
| `RELEASE_COORDINATOR_PRODUCTION_ENABLED` | NO, allowlist empty |
| `REAL_PRODUCTION_ACTIVATION` | DISABLED |

Phase 12 forbids bypassing a disabled flag to finish the order, so every activation here went to the
simulated host. **Nothing in this report is a live launch.**

## 001–007 REDESIGN STATE

Implemented and validated: market-local isolation, sealed packages, the FAST release-safety lane, the
persistent bundle cache, the atomic release coordinator, remote validation with trusted artifact handoff, and
the legacy-baseline cleanup. **Production consumption of every one of them is still switched off**, which is
what 005, 006 and 007 each said they were leaving for a later, explicit decision.

## CURRENT LIVE PRODUCTION

Read mechanically from the committed records in this tree, which agree across record, manifest, pin and
authorization:

| field | value |
|---|---|
| deploy id | `6a9d33f5dc8c3d1cf9464376` |
| bundle | `ca59f3710abde750…` |
| markets / profiles / routes | 10 / 786 / 945 |
| rollback parent | `6a9ca921843f2cba2ddf8da1` |
| release digest | `sha256:637e228fc74392b6…` |
| verification | verified, no problems |

**Discrepancy, reported not repaired.** Toledo is live in real production at 11 markets / 803 / 966 (deploy
`6a9e0476`) on branch `worker/ptf-toledo-promotion-002`. This worktree predates that launch, so its live
records are one release behind. Phase 2 says to stop live activation and report this; combined with the
disabled gate, live activation was impossible twice over.

## MARKET COHORT

All three proposed markets are **NOT_ELIGIBLE**, established mechanically rather than assumed:

| market | reported state | blocking reason |
|---|---|---|
| Lexington, KY | 61 census / 28 PF / 14 no-pets, ready in shadow | no registered contract, no `markets/authority/lexington-ky/`; its work exists only as reports — not even in the proposed namespace |
| Nashville, TN | 181 census / 80 PF / 19 no-pets / 82 unresolved | exists only in `markets/proposed/` with a 181-row proposed census; no registered contract, no authority shard |
| Chattanooga, TN | 102 census / 48 PF / 8 no-pets | same: proposed only |

The sealed-package contract reads the **registered** authority. Registering a market is a market-authority
change, which this order forbids. No contract was weakened to force a three-of-three result.

**Substitution, explained:** the lane was proved with the packages that can seal today — the committed Dayton
withdrawal package, Cleveland sealed read-only from committed authority, and the labelled 004 fixture market
exercising the *add a new market* path the real cohort will need.

## PACKAGE INGESTION and QUALITY FREEZE

Dayton came from its committed sealed package. Cleveland was sealed from committed authority as a read-only
derivation — no hotel or policy decision was created or changed. Frozen at seal time: Cleveland 220 identities
/ 220 census, 171 policy records evaluated.

## FAST VALIDATION

| release | market | result | detail |
|---|---|---|---|
| R1 | dayton-oh | **ELIGIBLE**, 5.5 s | all 15 rules A–O pass |
| R2 | cleveland-akron-canton-oh | **NOT ELIGIBLE**, 12.3 s | rule C (first-party policy binding) FAILED |

**The most important data finding of this order.** Cleveland is a live market at 120 profiles, and 12 of its
171 policy records fail the modern first-party evidence gate: 4 `AMENITY_CHIP_ONLY` (an amenity label such as
"Pets Allowed" states no policy) and 8 `QUOTE_NOT_OPERATIVE` (for example "We welcome your pets at our Inn.
Only in Parkview Suite." is not an acceptance a reader can interpret). 003 predicted this in general; 008
names the exact records. The lane behaved correctly — the market's legacy data is not ready.

Consequently R2's policy correctly demanded 4 remote broad shards. They were not dispatched, because remote
execution remains unproven and this proof does not spend on infrastructure.

## CACHE

Both staged releases: **9 of 10 markets inherited**, **0 unchanged markets rebuilt**, **0 builder
invocations** for the changed market. The 004 cache and the 005 release store did exactly what they were
built for.

## READY QUEUE and PARALLELISM

The queue admitted, validated, staged, authorized, activated and verified each package through its state
machine, serialized by the activation lease. While release 1 held the lane, **two other market workers made
measurable progress** (1.32 s and 1.36 s of useful cache work) without stalling the workstation. Available
memory at the end: 3.4 GB.

## RELEASE 1 — Dayton (QUALIFIED)

| measure | value |
|---|---|
| service time | **300.4 s (5.0 min)** |
| FAST validation | 5.5 s, ELIGIBLE |
| candidate staging | 177.9 s |
| remote broad jobs | **0** |
| bundles reused / rebuilt | 9 / **0** |
| diff | `dayton-oh` only; 786 → 782 profiles, 945 → 939 routes; **0 unexpected changes** |
| verification | **9 of 9 checks passed** |
| handoff | byte-identical, deterministic archive |
| DEPLOYMENT_ELIGIBLE | **NO** — `PRODUCTION_GATE_CLOSED` |

This is the complete ordinary path working end to end in five minutes, and refusing to deploy because the gate
is shut.

## RELEASE 2 — Cleveland (NOT QUALIFIED)

Service time 327.7 s. Staged and composed correctly, 9 of 10 inherited, 0 rebuilt, handoff byte-identical.
Refused twice, both correctly: the FAST lane declined it on rule C, and activation was refused with
`STALE_PARENT`.

**The stale-parent refusal is a harness limitation, stated plainly.** After release 1's *simulated*
activation, my proof did not advance its notion of current live truth, so the parent guard compared release
2's authorized parent (R1) against a live truth still reporting R0 and correctly refused. The guard is right;
the harness did not simulate the live advance. A separate probe confirmed the guard's real behaviour:
re-offering release 1's candidate after later releases moved live was refused with `STALE_PARENT` and the host
was never called.

## RELEASE 3 — fixture (BLOCKED)

Refused at two independent layers: the membership rule (a market not in the participation record cannot
participate) and then the composer (`cannot build a package for unregistered market 'fixture-dayton-oh'`).
**This is the same root cause that makes all three cohort markets ineligible**, now confirmed at the
composition layer: the release lane cannot admit an unregistered market, and registration is authority work
that lives outside it.

## BROAD-RUN PROOF

| release | local broad runs | remote broad jobs |
|---|---|---|
| R1 (qualified, data-only) | **0** | **0** |
| R2 (failed the evidence gate) | 0 | 4 required, not dispatched |

The ordinary data-only path requests zero broad validation, exactly as 006 designed. A package that fails the
evidence gate correctly loses that privilege.

## TWO DEFECTS THIS PROOF FOUND

Neither was visible to five orders of component testing, and both were caught by gates rather than escaping.

1. **Package fragments were not persisted to durable release storage.** Release N+1 therefore could not
   inherit the changed market and rebuilt it from committed authority — silently reverting release N's
   withdrawal, restoring 4 profiles and 26 routes. The parent-route gate refused to stage it. Fixed (the
   fragment now enters the store as it is composed) and pinned by a regression test.
2. **A chained release misreports its own counts.** The manifest's per-market profile counts derive from the
   LIVE release index rather than the actual parent, so release 2 reported 786 profiles while its bytes
   carried 782. A reporting defect, not a byte defect — the artifact was correct and byte-identical through
   handoff — recorded for the next data order.

## FOUNDER TIME

**UNKNOWN, and not fabricated.** Activation was simulated, so there was no authorization interaction, no
adjudication and no manual repair to measure. What the design does establish is that the lane needs exactly
**one** founder decision per release — authorize this candidate digest against this parent — and everything
else in the measured path ran unattended.

## HARDWARE

Release-lane work is light; peak memory in this factory belongs to the broad audit (~8.6 GB), not to a
release, and a qualified data-only release runs no broad suite at all. **More RAM would speed up broad audits;
it would not speed up a launch.**

## COST

008 release-lane cost: 0 Firecrawl credits, 0 Bright Data, 0 Places, 0 CI runner minutes, $0. Prior
acquisition for the cohort markets is sunk and is not counted as 008 work.

## REFRESH DEBT

The debt that is growing is **promotion**, not refresh: three markets have been built to promotion-ready and
none has been registered. Nashville alone carries 82 unresolved identities. Cleveland — already live — carries
12 policy records that fail the modern evidence gate. New-market creation is outrunning market promotion.

## THREE-MARKET SCORECARD

| market | class | qualified | service | broad jobs | reused / rebuilt | verify | result |
|---|---|---|---|---|---|---|---|
| dayton-oh | update (withdrawal) | YES | 300.4 s | 0 | 9 / 0 | 9/9 | SIMULATED |
| cleveland-akron-canton-oh | update (no-op) | NO — rule C | 327.7 s | 4 required | 9 / 0 | refused | SIMULATED, refused |
| fixture-dayton-oh | add new market | NO — unregistered | — | — | — | — | BLOCKED |

| overall | value |
|---|---|
| qualified packages | **1 of 3** |
| verified live launches | **0** |
| simulated | 2 |
| median release-lane service time | **300.4 s** |
| slowest | 327.7 s |
| local broad runs | 0 |
| unchanged markets rebuilt | **0** |
| correctness violations | **0** |

## BEFORE / AFTER

| stage | before (001) | after (008) |
|---|---|---|
| broad regression | 7,955 s / 2h13m | 3,439 s locally, 847 s projected across four shards |
| market-local validation | up to ~2 h | ~318 s |
| candidate composition | 547 s whole-site compose | 178 s staging, 9 of 10 inherited |
| release safety | the full suite | 5.5 s FAST lane |
| broad runs per data-only release | 1 (mandatory) | **0** |
| release lane, admission to verified | never measured; hours | **300 s** |

## CORRECTNESS

| assertion | result |
|---|---|
| unexpected market / profile / route removal | 0 / 0 / 0 |
| unexpected changes | 0 |
| unchanged markets rebuilt | 0 |
| stale-parent activation | 0 (and the guard refused when probed) |
| wrong artifact deployed | 0; handoff byte-identical |
| live markets preserved | yes |
| real deployments | **0** |
| paid provider calls | **0** |

## DECISION

**CONTINUE — the factory redesign sprint is complete. Return to market production.**

The measured evidence: a qualified data-only release traverses the lane in five minutes against a sixty-minute
target, requests zero broad validation, rebuilds nothing it should not, preserves every unrelated market, hands
off byte-identical bytes, and refuses to deploy when the gate is shut. Two real defects surfaced and both were
caught by gates rather than escaping.

The measured constraint is **market readiness, not architecture**. Of three intended markets none is
registered; of three attempted packages one qualified, and the one that failed did so because a live market's
legacy evidence does not meet the modern gate. Neither problem is fixed by more architecture, and authorising
another sprint would be building past the bottleneck.

Distinguishing the two claims the order asks me to separate:

- **The factory technically works** — proven for a qualified package, end to end, with correctness intact.
- **The business economics are not proven** — no live launch happened, and nothing here says anything about
  traffic or revenue.

**Do not open ATLAS-THROUGHPUT-009.** The next work is production: a promotion order per market beginning with
the smallest (Lexington), and a data order for Cleveland's 12 non-operative policy records.

## GIT

Branch `worker/atlas-throughput-001` in worktree `C:\Atlas-Throughput-V1` (no new worktree), continued from
the pushed 007 head `ab1e7a5`. Proof tooling, measurement artifacts, reports and ONE non-semantic coordinator
fix strictly necessary to run the proof. No market authority, no participation, no promotion, no deployment,
no paid call.

| commit | subject |
|---|---|
| `249d121` | ATLAS-THROUGHPUT-008 live three-market factory proof and the CONTINUE decision |
| `<this>` | ATLAS-THROUGHPUT-008 fill the FINAL report's git section |

The coordinator change is the defect this proof found: a package-built fragment now enters durable release
storage so release N+1 can inherit release N's own work. It is pinned by a regression test in the 005 suite.
Untracked measurement directories under `C:\ptf008` are gitignored scratch, never inputs.

**origin == HEAD, tree clean**, verified after the push and stated in the delivery message.

---

1. HOW MANY OF THE THREE MARKET PACKAGES WERE QUALIFIED? **1** (Dayton). Cleveland failed the first-party
   evidence gate; the fixture was refused as unregistered. The three PROPOSED markets never became packages.
2. HOW MANY WERE ACTUALLY VERIFIED LIVE? **0**.
3. HOW MANY WERE SIMULATED ONLY? **2**.
4. WHAT WAS THE MEDIAN RELEASE-LANE SERVICE TIME? **300.4 s (5.0 min)** for the qualified release; 327.7 s for
   the refused one. Across four runs the observed range was 300–582 s, varying with cache and store warmth.
5. WHAT WAS THE SLOWEST RELEASE-LANE SERVICE TIME? **327.7 s** in the final run; **582.2 s** across all runs.
6. HOW MANY LOCAL BROAD REGRESSIONS DID THE THREE DATA-ONLY RELEASES REQUIRE? **0**.
7. HOW MANY REMOTE BROAD JOBS DID THEY REQUIRE? **0 for the qualified release**; 4 for Cleveland, which failed
   the evidence gate and correctly lost the fast path. None was dispatched.
8. HOW MANY UNCHANGED LIVE MARKETS WERE REBUILT? **0**.
9. DID ANY STALE MARKET BRANCH REMOVE OR MODIFY AN UNRELATED LIVE MARKET? **NO**.
10. DID ANY WRONG IDENTITY / EVIDENCE / ROUTE / MARKET REMOVAL ESCAPE? **NO** — two defects were found and both
    were caught by gates before staging completed.
11. WHAT WAS FOUNDER ACTIVE TIME PER MARKET? **UNKNOWN** — activation was simulated, so there was no founder
    interaction to measure. The design requires one authorization decision per release.
12. CAN THE REDESIGNED FACTORY SUPPORT AT LEAST THREE QUALIFIED MIXED-MARKET LAUNCHES PER 8-HOUR DAY?
    **NOT YET PROVEN.** The lane can process a release every five minutes, but only one of three packages
    qualified and none could launch, so the capability is unproven on markets rather than on machinery.
13. IS ROUTINE DATA-ONLY RELEASE PROCESSING <= 60 MINUTES? **YES** — 5 minutes measured.
14. IS THE FACTORY TECHNICALLY SCALABLE TO 50+ MARKETS? **UNCERTAIN.** Per-release cost is dominated by
    composing the whole site from inherited fragments, which grows with market count; at 10 markets it is
    178 s. Nothing measured here rules 50 out, and nothing measured here demonstrates it.
15. DECISION: **CONTINUE**.
16. IF REDESIGN: not applicable.
17. IF CONTINUE: **FACTORY REDESIGN SPRINT COMPLETE — RETURN TO MARKET PRODUCTION.**

STOP. ATLAS-THROUGHPUT-009 not opened. Nothing promoted. Nothing deployed.
