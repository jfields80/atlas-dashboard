# ATLAS-THROUGHPUT-007 — shard rebalance

The 007 demo-media split moved the floor, so the committed four-shard manifest was regenerated from the new
measurements.

| measure | before 007 | after 007 |
|---|---|---|
| slowest shard (projected remote wall) | 1349.7 s | **852.3 s** |
| aggregate runner time | 3625.3 s | 3409.0 s |
| the module that sets the floor | test_pettripfinder_demo_media.py | test_global_deployment_architecture_045.py |
| that module's cost | 1349.7 s | 752.1 s |

| shard | seconds | tests | modules | heaviest module |
|---|---|---|---|---|
| 1 | 852.3 | 4463 | 148 | test_global_deployment_architecture_045.py |
| 2 | 852.2 | 4299 | 152 | test_pettripfinder_demo_media_determinism.py |
| 3 | 852.3 | 4349 | 154 | test_per_market_release_contracts.py |
| 4 | 852.3 | 4590 | 153 | test_pettripfinder_demo_media.py |

The bottleneck has MOVED rather than vanished: the floor is now `test_global_deployment_architecture_045.py`, and the next 007-style question is
whether its claims can be separated the same way. Adding runners still buys nothing beyond four, because the
slowest indivisible module is what a sharded run waits for.
