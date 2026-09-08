# ATLAS-THROUGHPUT-005 — authorization contract

`ptf-release-authorization/1.0`. An authorization binds **four digests** and is stored outside the candidate bytes, so signing cannot
change what it signs:

| binds | example value |
|---|---|
| candidate_digest | sha256:25b69be224b34ff42a4b96845 |
| deployment_artifact_digest | 437439f275b2f276fa2969adbc0ddc69 |
| parent_release_digest | sha256:637e228fc74392b6c7617735d |
| intended_delta_digest | sha256:c7b7fb29b5c91001d78856288 |
| decided_by | ATLAS-THROUGHPUT-005 pilot (simu |
| state | VALID |

It refuses when any of them moves, when membership changes, when the candidate is superseded, when the
candidate no longer hashes to its own manifest, or when the live release is no longer the authorized parent.
It does NOT invalidate because an unrelated report or an offline acquisition helper changed while the
candidate bytes stayed identical.

There is no authorization by market name, by branch sha, or of "the latest candidate".
