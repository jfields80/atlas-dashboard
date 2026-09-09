# ATLAS-THROUGHPUT-004 — multi-market reuse

A simulated candidate release after a warm cache: market A (cleveland-akron-canton-oh) changed by one policy
mutation, B (dayton-oh) unchanged, C (fixture-dayton-oh, a labelled fixture clone) unchanged.

| market | cache | builder invocations | seconds |
|---|---|---|---|
| A_cleveland_changed | MISS | 2 | 95.605 |
| B_dayton_unchanged | HIT | 0 | 3.521 |
| C_fixture_unchanged | HIT | 0 | 4.688 |

Total 103.936 s. Unchanged markets rebuilt: 0. Then a shared template changed (approved_hotel_profile.css in a
shadow closure): every bundle misses — {"A": "MISS", "B": "MISS", "C": "MISS"} (builds forbidden: proven without building).
