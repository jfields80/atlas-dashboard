# ATLAS-THROUGHPUT-006 — performance scorecard

| measure | measured | note |
|---|---|---|
| market-local validation (002) | ~318 s | representative market-local lane |
| FAST data-only release safety (003) | 60.9 s | standalone lane |
| FAST lane inside a 005 candidate | 5.5 s | rules A-O with the 004 cache supplied |
| warm validated bundle reuse (004) | 3.7 s / 8.4 s | Dayton / Cleveland, builder invocations 0 |
| whole-site compose (005 seed) | 547.4 s | every market rebuilt |
| data-only candidate staging (005) | 178.0 s | 9 of 10 markets inherited, 0 rebuilt |
| candidate handoff round trip (006) | measured below | package, receive, re-hash |
| local broad regression (005 audit) | 3,669.9 s | one process, founder's desktop blocked |
| remote broad, projected wall (006) | 1375.7 s | slowest of four measured shards |
| remote broad, aggregate runner time | 3621.7 s | what the runners bill |
| ordinary DATA_ONLY release, remote broad jobs | 0 | REMOTE_BROAD_JOBS = 0 |

## Remote broad validation

| measure | value |
|---|---|
| local broad run, one process | 3,669.9 s (61 min), desktop blocked |
| remote wall clock, four measured shards | 1375.7 s (22.9 min) |
| aggregate runner time | 3621.7 s |
| wall-clock improvement | 2.67x |
| executed | **NO — REMOTE_EXECUTION_NOT_PROVEN** |

The wall clock is bounded by one indivisible module at 1375.7 s; the remaining three shards are balanced within
a second of each other.

## The path that matters

An ordinary proven data-only release requests **0** remote broad jobs. That is the number 006 is really
about: the improvement above applies to the audits that genuinely need a broad run, and a routine market
release should never reach them.

| shared change | remote broad jobs | scope |
|---|---|---|
| SHARED_RUNTIME | 4 | ALL |
| SHARED_SCHEMA | 4 | ALL |
| ASSEMBLER | 4 | ALL |
| DEPLOYMENT | 4 | DEPLOYMENT |
| UNKNOWN | 4 | ALL |

## Not yet measured

Founder active time per release, queue wait, CI wait, and activation and verification against production.
008 is the experiment that measures those; 006 does not claim throughput proof.
