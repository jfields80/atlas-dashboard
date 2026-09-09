# ATLAS-THROUGHPUT-005 — release coordinator contract

One equation, one writer:

```
CURRENT VERIFIED LIVE RELEASE + ONE AUTHORIZED SEALED MARKET PACKAGE DELTA
+ REUSABLE VALIDATED MARKET BUNDLES = ONE EXACT FINAL STAGED CANDIDATE
```

`scripts/pettripfinder/release_coordinator.py` (ptf-release-coordinator/1.0) is the only writer of staged release manifests.
Operations: plan, stage, authorize, activate, verify, reconcile, rollback, inspect. Lifecycle: SOURCE_READY -> CANDIDATE_STAGED -> FOUNDER_AUTHORIZED -> LIVE.

## Release-global artifacts

| artifact | class | depends on |
|---|---|---|
| index.html | REGENERATE | membership and navigation: build_global_home over the visible markets |
| pet-friendly-hotels/index.html | REGENERATE | membership and per-market published counts |
| sitemap.xml | REGENERATE | every indexable route in the composed bundle |
| llms.txt | REGENERATE | membership and base_url |
| robots.txt | INCREMENTAL | base_url only; identical bytes for an unchanged base_url |
| _headers | INCREMENTAL | copied from the tracked context source and hashed |
| _redirects | INCREMENTAL | copied from the tracked source and hashed |
| about/index.html | REUSE | the anchor market's shell page, inherited with the anchor fragment |
| contact/index.html | REUSE | the anchor market's shell page |
| methodology/index.html | REUSE | the anchor market's shell page |

An artifact with no declared class refuses staging (`UNKNOWN_GLOBAL_DEPENDENCY`): 005 never optimises an
unknown dependency by assumption.

## Refusals

`AUTHORIZATION_REVOKED`, `BUNDLE_DIGEST_MISMATCH`, `CANDIDATE_CORRUPT`, `CANDIDATE_DIGEST_MISMATCH`, `CANDIDATE_SUPERSEDED`, `FRAGMENT_UNAVAILABLE`, `GATES_FAILED`, `INTENDED_DELTA_MISMATCH`, `LIVE_NOT_VERIFIED`, `NOT_AUTHORIZED`, `PARENT_DIGEST_MISMATCH`, `RELEASE_NOT_CURRENT`, `STALE_PARENT`, `UNAUTHORIZED_ADDITION`, `UNAUTHORIZED_REMOVAL`, `UNKNOWN_GLOBAL_DEPENDENCY`

## Production activation

REAL_PRODUCTION_ACTIVATION = **DISABLED**. The only host adapter is `SimulatedHost`; the production deployer does not import the coordinator.
