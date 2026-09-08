# ATLAS-THROUGHPUT-006 — shard manifest

Balanced by **measured duration** from the ATLAS-THROUGHPUT-005 audit's profiler output
(604 modules, 17643 tests, 3621.7 s), longest-processing-time first, at **module** granularity.

| shard | category | modules | tests | measured s | heaviest module |
|---|---|---|---|---|---|
| 1 | ASSEMBLER_DEPLOYMENT_HISTORY | 1 | 18 | 1375.7 | test_pettripfinder_demo_media.py |
| 2 | ASSEMBLER_DEPLOYMENT_HISTORY | 1 | 46 | 750.0 | test_global_deployment_architecture_045.py |
| 3 | ASSEMBLER_DEPLOYMENT_HISTORY | 300 | 8673 | 748.0 | test_per_market_release_contracts.py |
| 4 | CONTRACTS_CORE | 302 | 8906 | 748.0 | test_atlas_throughput_004.py |

**The critical path is one module.** `tests/website_generation/integration/test_pettripfinder_demo_media.py` measures 1375.7 s — more than a perfect quarter of the suite — so no
four-way split can finish faster, and adding shards buys nothing until that module is itself divisible. That
is a finding for 007, not a defect in the plan.

| projection | seconds |
|---|---|
| wall clock (slowest shard) | 1375.7 |
| aggregate runner time | 3621.7 |
| the local broad run this replaces | 3,669.9 |

Not balanced by test count: the suite's cost is concentrated in a few modules, so counting tests would put
8,900 cheap tests opposite 18 expensive ones. Not grouped by category either: the assembly-heavy category
alone measures about 2,800 s, so grouping it would roughly double the wall clock.

`peak_working_set_mb` is the PROCESS peak observed while a module ran, which for a late module includes
everything before it. It bounds a shard; it is not that module's own footprint.
