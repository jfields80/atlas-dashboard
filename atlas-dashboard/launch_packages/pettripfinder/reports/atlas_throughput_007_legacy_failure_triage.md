# ATLAS-THROUGHPUT-007 — legacy failure triage

All 160 failures in the 006 audit are in the f75aa95 baseline, none is outside it, and **none has started
passing**.

| category | count |
|---|---|
| LEGACY_EXPECTATION | 74 |
| ENVIRONMENT | 39 |
| HISTORICAL_COUNT_PIN | 29 |
| TEST_INFRA | 11 |
| UNKNOWN | 7 |

Concentrated in historical acquisition suites: test_identity_binding_027.py, test_marriott_template_021.py, test_observation_rederivation_018.py, test_reader_hardening_029.py, test_recurring_and_parity_035.py, test_store_reader_sync_030.py.

## Were any critical defects hiding here?

28 nodes have an id mentioning identity, policy, artifact, release, authorization, deployment or bundle. Every
one is a HISTORICAL suite asserting what its OWN order left true — not a live integrity check. The modern
critical lane is 003's FAST rules A–O, 004's bundle validation receipts, 005's release coordinator and 006's
artifact handoff, and **none of them appears in the baseline**. No critical identity, policy, artifact or
release defect is hidden behind legacy status.

## What 007 fixed

**Zero.** That is deliberate: the order forbids eliminating the ~160, and every one is already suppressed
correctly by node id. What 007 changed is that they can no longer drift — each now carries a signature, so a
baselined node that starts failing differently is TRUE_NEW.

The 7 UNKNOWN entries are the ones that must be reviewed before they are tolerated further; they are named in
the baseline's `failure_records` with `review_by: ATLAS-THROUGHPUT-008`.
