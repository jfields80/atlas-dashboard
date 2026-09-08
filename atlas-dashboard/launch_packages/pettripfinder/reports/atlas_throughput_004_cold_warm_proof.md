# ATLAS-THROUGHPUT-004 — cold → warm proof (the defining acceptance test)

RUN 1 builds in the pilot process; RUN 2 runs in a NEW Python process with `PTF_BUNDLE_CACHE_FORBID_BUILD=1`
(a miss would raise). Same package, same cache root.

| market | RUN 1 cache | BUILD_EXECUTED | TRUSTED_CACHE_PUBLISHED | cold build s | determinism | RUN 2 cache | BUILD_EXECUTED | PERSISTENT_CACHE_HIT | bytes identical | sha identical | warm total s (in-process) | process wall s |
|---|---|---|---|---|---|---|---|---|---|---|---|---|
| A_dayton | MISS | 2 | 1 | 20.026 | BYTE_IDENTICAL | HIT | 0 | 1 | True | True | 3.732 | 4.212 |
| B_cleveland | MISS | 2 | 1 | 45.892 | BYTE_IDENTICAL | HIT | 0 | 1 | True | True | 8.355 | 8.839 |
| C_fixture | MISS | 2 | 1 | 22.982 | BYTE_IDENTICAL | HIT | 0 | 1 | True | True | 3.882 | 4.32 |

Receipt valid on every hit (re-read, digest re-derived, bound to key + digest + policy + dependency digests);
no market builder invoked on any hit (`builder_invocations = 0`, `PTF_BUNDLE_CACHE_FORBID_BUILD` armed).
