# ATLAS-THROUGHPUT-007 — performance

The 007 success metric is demo-media and broad-audit cost reduced WITHOUT safety loss. Both halves are
measured below; the safety half is the claims table, where nothing was removed and two claims were added.

## The broad audit

| measure | 006 audit | 007 audit |
|---|---|---|
| wall | 3674.5 s | **3439.2 s** |
| collected | 17699 | 17721 |
| passed | 17308 | 17330 |
| failed | 160 | 160 |
| skipped | 231 | 231 |
| PRE_EXISTING | 160 | 160 |
| TRUE_NEW | 0 | 0 |
| peak working set | 8802 MB | 8636 MB |

The suite GREW by 22 collected tests and the failure set did not move: the same 160 node ids, now matched on
signature as well as id.

## Demo-media

| measure | before | after |
|---|---|---|
| total seconds | 1349.7 | **1083.8** |
| modules | 1 | 3 |
| slowest module | 1349.7 s | **534.0 s** |
| real-chain builds | 5 | 4 |
| safety claims | 8 | 10 (2 added, 0 removed) |

Five real-chain builds became four, and the claims went from 8 to 10 with none removed. The slowest module is
what a sharded run waits for, and it fell from 1,349.7 s to 534.0 s.

## Top 10 modules after 007

| module | seconds | tests |
|---|---|---|
| test_global_deployment_architecture_045.py | 770.9 | 46 |
| test_pettripfinder_demo_media_determinism.py | 534.0 | 2 |
| test_per_market_release_contracts.py | 357.6 | 240 |
| test_pettripfinder_demo_media.py | 290.7 | 16 |
| test_pettripfinder_demo_media_fallback.py | 259.1 | 2 |
| test_atlas_throughput_004.py | 144.3 | 41 |
| test_prod005_netlify_config.py | 115.9 | 50 |
| test_atlas_throughput_003.py | 79.9 | 70 |
| test_atlas_throughput_002.py | 79.1 | 73 |
| test_prod004_verified_only.py | 69.5 | 15 |

## Shards

| measure | before 007 | after 007 |
|---|---|---|
| projected remote wall | 1349.7 s | **847.2 s** |
| aggregate runner time | 3,621.7 s | 3388.9 s |
| module setting the floor | demo-media, 1,375.7 s | test_global_deployment_architecture_045.py, 770.9 s |

The plan is now work-bound rather than bottleneck-bound: the slowest indivisible module (770.9 s) sits below
the balanced share, so all four shards land on the same second. Before 007 one module was 1,375.7 s and no
number of runners could beat it.

## The factory, end to end

| stage | measured |
|---|---|
| market-local validation (002) | ~318 s |
| FAST release safety (003) | 60.9 s standalone, 5.5 s in a 005 candidate |
| warm validated bundle reuse (004) | 3.7 s Dayton, 8.4 s Cleveland, 0 builder invocations |
| whole-site compose (005) | 547.4 s |
| data-only candidate staging (005) | 178.0 s |
| candidate handoff round trip (006) | byte-identical, deterministic archive |
| local broad audit (007) | 3439.2 s |
| projected remote broad wall (007) | 847.2 s, NOT EXECUTED |
| ordinary data-only release, remote broad jobs | 0 |

## Not yet measured

- founder active time per release
- queue wait
- CI wait
- production activation
- HTTP live verification against production

007 does not claim throughput proof; 008 is the experiment that measures the live day.
