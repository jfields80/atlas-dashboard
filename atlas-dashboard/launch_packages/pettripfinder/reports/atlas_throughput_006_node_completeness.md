# ATLAS-THROUGHPUT-006 — node-id completeness

A sharded run is a run only if every planned node id is accounted for **exactly once**.

Proved over a real broad run rather than a synthetic collection: the 005 audit's junit, partitioned by the
committed shard manifest and verified by the same `ci_report` code the workflow runs.

| shard | cases | seconds | failures |
|---|---|---|---|
| 1 | 18 | 1375.7 | 0 |
| 2 | 46 | 750.0 | 0 |
| 3 | 8673 | 748.8 | 63 |
| 4 | 8906 | 748.9 | 97 |

| measure | value |
|---|---|
| planned node ids | 17643 |
| executed | 17643 |
| explicitly excluded | 0 |
| unassigned cases | 0 |
| PRE_EXISTING / TRUE_NEW | 160 / 0 |
| complete | True |

**This contract earned its place before it shipped.** The first simulation left 11,600 of 17,643 cases
unassigned, because the shard lookup derived a module from the junit classname without stripping the test
class. The run failed and named the missing nodes instead of reporting a cheerful partial green. Every case
now routes through the same node-id reconstruction the receipt uses.

Failure modes, each of which fails the RUN and not merely a shard: `SHARD_MISSING`, `SHARD_TIMEOUT`, `SHARD_CANCELLED`, `COLLECTION_ERROR`, `NODE_MISSING`, `NODE_DUPLICATED`, `NODE_UNPLANNED`, `ARTIFACT_MISSING`.
