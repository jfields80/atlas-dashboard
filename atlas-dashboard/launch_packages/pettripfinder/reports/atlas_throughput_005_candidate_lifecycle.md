# ATLAS-THROUGHPUT-005 — candidate lifecycle

| state | entered when | invariant |
|---|---|---|
| SOURCE_READY | a sealed package exists and its checks passed | no production membership change yet |
| CANDIDATE_STAGED | parent selected, delta applied, FINAL participation included, unchanged bundles reused, globals regenerated, gates run, digest computed | immutable; any semantic change makes a NEW candidate |
| FOUNDER_AUTHORIZED | an authorization record binds candidate + parent + intended delta | the record lives outside the candidate bytes |
| LIVE | the exact authorized candidate activated and initial verification passed | never claimed before verification |
| FAILED | activation or verification failed | the candidate stays immutable; live unchanged |
| ABANDONED | superseded or withdrawn | the candidate stays immutable |

A staged candidate is composed into a temporary directory and renamed into place under its own digest.
Nothing mutates it afterwards: changing membership, the package, a bundle, a global file, the parent or the
intended delta produces a DIFFERENT candidate digest, and the old authorization does not follow.
