# ATLAS-THROUGHPUT-004 — performance

Target: warm reuse of an unchanged market in seconds, preferably < 10 s including integrity and receipt checks.

| measure | dayton-oh (334 files) | cleveland-akron-canton-oh (120 profiles) |
|---|---|---|
| COLD BUILD TIME (first cold build) | 20.026 s | 45.892 s |
| DETERMINISM (second cold build) | 17.964 s | 42.076 s |
| CACHE PUBLICATION TIME (archive, round-trip check, receipt, index) | 3.061 s | 8.047 s |
| WARM CACHE LOOKUP TIME (index read + extract + re-hash + receipt) | 2.834 s | 7.372 s |
| ARTIFACT HASH VERIFICATION TIME (inside the lookup) | 2.818 s | 7.357 s |
| MANIFEST TIME (stage + closure hashing) | 0.897 s | 0.982 s |
| WARM TOTAL, in-process | **3.732 s** | **8.355 s** |
| WARM process wall (interpreter start + imports + lookup) | 4.212 s | 8.839 s |
| BYTES REUSED | 1405426 | 2900407 |
| REVALIDATION-ONLY TIME (policy bump, no build) | 3.271 s | — |
| CACHE INDEX LOOKUP | included in lookup (one JSON read) | |
| DISK SPACE (cache root, all objects) | 4179146 bytes | |
| PEAK MEMORY (pilot process) | 224.9 MB | |
| BUILD EXECUTIONS AVOIDED (pilot) | 3 | |

Multi-market simulated release: MARKETS 3, COLD BUILDS 1, CACHE HITS 2, REVALIDATIONS 0, GLOBAL REBUILDS not in scope (005): the whole-site compose,
TOTAL TIME 103.936 s.

Targeted tests: 39 passed, 0 failed, 0 skipped. Integrity checks were never weakened: every hit re-extracts
and re-hashes the bundle and re-reads and re-binds the receipt.
