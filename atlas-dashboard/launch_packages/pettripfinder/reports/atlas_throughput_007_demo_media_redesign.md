# ATLAS-THROUGHPUT-007 — demo-media redesign

| measure | before | after |
|---|---|---|
| modules | 1 | 3 |
| tests | 18 | 20 |
| full real-chain builds | 5 | 4 |
| aggregate seconds | 1349.7 | 1133.4 |
| slowest module (the shard floor) | 1349.7 | **558.2** |
| safety claims | 8 | 10 (2 added, 0 removed) |

Aggregate fell -16%; the floor fell -59%.

**What was removed:** one redundant build. A test that asserted the dataset carries no filesystem path was
building a second identical chain to look at an artifact the module had already built. It now reads the shared
one and checks strictly MORE — the fixture's own temp root is a filesystem path that must not have leaked in
either, which the private build could never have caught because it was inspecting a tree it created itself.

**What was not removed:** the cold executions. Determinism keeps two independent builds and the zero-image
fallback keeps its own, because their inputs and claims genuinely differ. The preferred 600 s target is met at
558.2 s; the strong 450 s target is not, and cannot be at module granularity, because two real executions of
the chain cost about 265 s each and comparing a build against itself proves nothing.
