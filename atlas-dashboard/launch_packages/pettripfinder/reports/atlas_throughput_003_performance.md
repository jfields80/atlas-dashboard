# ATLAS-THROUGHPUT-003 — performance

Target: P50 ≤ 5 min; initial proof ≤ 15 min on the 16 GB machine. Measured on the pilot (`atlas_throughput_003_performance.json`).

| measure | P2 dayton-oh withdrawal package (ELIGIBLE = YES) |
|---|---|
| PACKAGE WRITE TIME | 0.07 s (a second write, different `sealed_at`, same digest) |
| PACKAGE VALIDATION TIME (rules A–F, L, M, O) | 0.24 s |
| GLOBAL INDEX TIME (live index of 10 markets / 786 profiles + compare) | 4.939 s |
| CHANGED MARKET BUILD TIME (rule J, real per-market assembler, cold) | 28.656 s |
| DETERMINISM TIME (rule K, second cold build) | 31.889 s |
| TOTAL FAST LANE TIME | **60.872 s** (65.737 s including the live index) |
| PEAK MEMORY (lane process) | 103.8 MB |
| TEST COUNT (rules) | 15 rules; 69 adversarial tests in the targeted module |
| ASSEMBLY EXECUTIONS | 4 cold builds (generator + bundle, twice), 0 reuse hits |

Versus the old path: the broad suite measured 7,955 s in 001 and 3,815 s in the 002 audit (with reuse), with a
7.5 GB working set, to answer the same data-only question indirectly.

Index at scale (synthetic clones of the real markets; findings 0 by construction):

| markets | profiles | total s |
|---|---|---|
| 11 | 786 | 0.0982 |
| 25 | 1964 | 0.2185 |
| 50 | 3848 | 0.4255 |
| 100 | 7778 | 0.8126 |
| 200 | 15638 | 1.5429 |

The lane never renders an unchanged market; its cost is two cold builds of the changed market plus O(data) work.
