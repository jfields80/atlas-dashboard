# ATLAS-THROUGHPUT-006 → 007 input packet

Status: PROPOSED. 007 is HISTORICAL SEMANTICS + LEGACY FAILURE DEBT CLEANUP. It must stay bounded: the goal is
not to rewrite every old test before anything can launch.

## The debt, measured

| measure | value | source |
|---|---|---|
| baseline failures carried on every broad run | 160 | `regression_baselines/f75aa95.json` |
| modules holding them | 36 | same |
| suite total | 17,643 tests, 3,669.9 s | 005 audit |
| the one module that bounds every sharded run | 1,375.7 s, 18 tests, ~9.1 GB peak | 005 audit profile |

## The four highest-value items, in order

1. **Split or shrink `tests/website_generation/integration/test_pettripfinder_demo_media.py`.** It is 38% of
   the suite, it peaks near 9.1 GB, and it single-handedly sets the floor for remote wall clock: four shards
   and eight shards both finish in 1,375.7 s because of it. Until it is divisible, more runners buy nothing.
   This is the single highest-value item in 007 and it is a throughput change, not a semantics change.

2. **Retire the count pins that move whenever a market grows.** An application order has repeatedly broken
   dozens of tests in a dozen modules purely because a total changed; the epoch/cohort helpers already exist
   to scope a historical suite to the cohort it was written for. Convert the noisiest modules first, measured
   by how often they appear in application-order failure lists.

3. **Give the 160 baseline failures a signature, not just a node id.** 006 classifies PRE_EXISTING by node id
   AND normalised failure signature, but the committed baseline carries no signatures, so today a baseline
   node that starts failing for a NEW reason is still counted as pre-existing. Recording signatures closes
   that gap and costs one broad run's output, not a rewrite.

4. **Quarantine with a reason, not with silence.** The completeness contract supports explicit exclusions with
   a stated reason; any test genuinely retired should be excluded that way rather than left failing forever.

## Explicitly NOT in 007

Rewriting historical suites wholesale, changing what a historical epoch asserts, or converting markets that
are not already causing measured cost. 007 is a debt payment with a budget, not a renovation.
