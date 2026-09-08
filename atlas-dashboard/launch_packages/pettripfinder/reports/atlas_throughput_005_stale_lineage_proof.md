# ATLAS-THROUGHPUT-005 — stale lineage proof

The Pittsburgh / Indianapolis failure, as a measured refusal.

| measure | value |
|---|---|
| live markets | 10 |
| markets preserved in the candidate | 10 |
| inherited from the release store | 9 |
| rebuilt | 0 |
| UNINTENDED_REMOVAL | 0 |
| activation refused on the stale parent | True |
| host untouched by the refusal | True |
| this worktree is itself stale (no Toledo) | True |

The preservation baseline is CURRENT VERIFIED LIVE RELEASE, so a branch that predates a market cannot remove
it: membership never comes from the tree. When the live release moves after staging, the authorization's
parent guard refuses activation rather than deploying a candidate composed on a parent that no longer exists.
