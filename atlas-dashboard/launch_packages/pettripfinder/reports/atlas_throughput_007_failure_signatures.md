# ATLAS-THROUGHPUT-007 — failure signature baseline

006 found the baseline carried node ids but no signatures, so a baselined node could start failing for a
completely different reason and still be counted PRE_EXISTING. All 160 now carry one.

| case | verdict |
|---|---|
| same node, same signature | PRE_EXISTING |
| same node, different signature | TRUE_NEW |
| different node | TRUE_NEW unless separately baselined |
| baselined node not failing | BASELINE_NOW_PASSING — reported, never erased |
| no messages supplied | node-id classification, as before 007 |

Normalization removes memory addresses, absolute paths, temp directories, timestamps and run ids, and
preserves the semantic identity — the asserted values and the exception type. A signature therefore survives a
different machine but not a different defect.

**Provenance, stated plainly:** the signatures were captured from the 006 migration audit, not from the
f75aa95 commit itself. That run failed on exactly these 160 node ids, so the signatures record how each fails
today, which is what a future run must match.

Both classifiers honour them, and both are backward compatible: with no messages supplied, classification is
by node id exactly as before, so every earlier run's verdict still means what it meant.
