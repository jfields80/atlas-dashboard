# ATLAS-THROUGHPUT-007 — shard rebalance

The 007 demo-media split moved the floor, so the committed four-shard manifest was regenerated — from the 007
migration audit's OWN profiler run, a full-suite measurement rather than a projection.

| measure | before 007 | after 007 |
|---|---|---|
| slowest shard (projected remote wall) | 1349.7 s | **847.2 s** |
| aggregate runner time | 3625.3 s | 3388.9 s |
| the module that sets the floor | test_pettripfinder_demo_media.py | test_global_deployment_architecture_045.py |
| that module's cost | 1349.7 s | 770.9 s |
| the local broad run this replaces | 3,674.5 s | 3439.2 s |

| shard | seconds | tests | modules | heaviest module |
|---|---|---|---|---|
| 1 | 847.2 | 3978 | 146 | test_global_deployment_architecture_045.py |
| 2 | 847.2 | 4382 | 154 | test_pettripfinder_demo_media_determinism.py |
| 3 | 847.2 | 4903 | 154 | test_per_market_release_contracts.py |
| 4 | 847.2 | 4458 | 154 | test_pettripfinder_demo_media.py |

**The plan is now work-bound, not bottleneck-bound.** All four shards land on the same second, because the
slowest indivisible module (770.9 s) is below the balanced share (847.2 s). Before 007 one module was 1,375.7 s
and no number of runners could beat it.

The bottleneck has MOVED rather than vanished: it is now `test_global_deployment_architecture_045.py`, and whether its claims separate the way
demo-media's did is the next question of this kind. Adding runners beyond four still buys nothing, because a
sharded run waits for its slowest indivisible unit.
