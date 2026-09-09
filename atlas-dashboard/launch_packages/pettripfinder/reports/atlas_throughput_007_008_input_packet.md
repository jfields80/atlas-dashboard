# ATLAS-THROUGHPUT-007 → 008 input packet

Status: PROPOSED. 008 is the THREE-MARKET LIVE FACTORY PROOF: three qualified launches in one operating day,
one small/medium, one medium and one large, against frozen quality floors. **008 is not started.**

## The five blockers 006 listed, reconciled after 007

| # | blocker (006) | changed in 007? | state now |
|---|---|---|---|
| 1 | three registered and sealed candidate markets | **NO** | still only Dayton and Cleveland seal on this branch; Lexington, Nashville and Chattanooga remain shadow-ready and unregistered here |
| 2 | a worktree whose live records include current production (Toledo) | **NO** | this worktree still predates Toledo's launch; its committed live records are one release behind |
| 3 | the production gate opened for chosen pilot markets | **NO** | `release_production_gate.json` is still `ENABLED = NO` with an empty allowlist, by design |
| 4 | remote execution actually proven | **NO** | still REMOTE_EXECUTION_NOT_PROVEN: no GitHub CLI or API token in this environment, so Actions availability and billing remain unestablished |
| 5 | the missing live measurements | **NO** | founder active time, queue wait, CI wait, production activation and HTTP live verification are all still unmeasured against production |

**007 solved none of the five, and was not supposed to.** Its targets were the broad-audit cost and the
historical-test noise that make those five expensive to work through, not the five themselves.

## What 007 did change, that 008 inherits

| capability | before 007 | after 007 |
|---|---|---|
| demo-media module | 1,349.7 s, one module, five real-chain builds | 1,133.4 s across three modules, four builds; slowest is 558.2 s |
| projected four-shard remote wall | 1,349.7 s | **852.3 s**, with all four shards within 0.1 s of each other |
| what bounds a sharded run | one indivisible module | the balanced share of total work |
| legacy baseline | 160 node ids | 160 node ids **plus** normalized signatures, categories and review dates |
| a baselined node failing differently | counted PRE_EXISTING | **TRUE_NEW** |
| a baselined node that starts passing | silently absent | reported as BASELINE_NOW_PASSING |

The practical effect for 008: a required broad audit is projected at about 14 minutes of remote wall instead
of 23, an audit no longer hides a changed defect behind an old node id, and a market that lawfully grows
during the operating day no longer breaks the two migrated current-state pins.

## What 008 must still do first, in order

1. **Rebase onto a current tree.** Everything 005 and 006 built reads CURRENT VERIFIED LIVE from committed
   records. On a tree that predates Toledo, the coordinator's parent is a release production has already
   moved past. This is the first blocker, not the last: no live proof can run from here.
2. **Seal three markets.** One small/medium, one medium, one large. Sealing is a data order per market, and
   the writer refuses eight of the eleven live markets today on legacy authority facts, so this is the
   longest-lead item.
3. **Prove remote execution once.** Dispatch the committed workflow, confirm Actions is enabled and billed
   acceptably, and capture one real CI receipt. Until then any launch carrying a shared change has no way to
   satisfy its own policy.
4. **Open the production gate per market**, with the founder's authorization bound to each exact candidate
   digest.
5. **Measure the four unknowns** during the day itself: founder active time per release, queue wait, CI wait,
   and activation plus HTTP verification against production.

## Market recommendation for the three slots

Using existing ready-market state only. Nothing here promotes or seals anything.

| slot | recommended | why | preparation still required |
|---|---|---|---|
| SMALL/MEDIUM | **Lexington, KY** (28 pet-friendly / 14 no-pets, PROMOTION_READY in shadow) | smallest ready shadow market, so the first launch of the day carries the least blast radius | register on the branch, seal a package, run the FAST lane |
| MEDIUM | **Chattanooga, TN** (48 / 8, PROMOTION_READY, broad run already proved 0 TRUE_NEW) | mid-sized and already validated against the baseline set once | register, seal, FAST lane |
| LARGE | **Nashville, TN** (80 / 19, PROMOTION_READY) | the largest ready shadow market; exercises the composer and the release index at scale | register, seal, FAST lane |

A fourth option worth keeping in reserve: **Dayton** already has a committed sealed package and is already
live, so a withdrawal-shaped delta there is the cheapest possible rehearsal of the whole lane and needs no
new market at all. 006 recommended it as the first pilot for exactly that reason, and that recommendation
stands independently of the three-market day.

## Frozen quality floors, unchanged

Every launch must clear: first-party evidence binding, the intended-delta and removal guards, the release
index comparison (no unrelated market, profile or route lost), deterministic changed-market builds,
byte-identical handoff, an authorization binding four digests, the parent guard at activation, and the nine
live checks. 008 is a throughput experiment; none of these moves for it.
