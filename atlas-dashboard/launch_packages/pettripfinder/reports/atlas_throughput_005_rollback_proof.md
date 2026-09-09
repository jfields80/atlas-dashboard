# ATLAS-THROUGHPUT-005 — rollback and serialized lineage

| measure | value |
|---|---|
| restored release | sha256:637e228fc74392b6c |
| restored bundle | ca59f3710abde750 |
| restored markets | 10 |
| outcome | ACTIVATED |
| stale rollback refused | True |
| refusal | RELEASE_NOT_CURRENT |

A rollback target is an exact prior verified release read from durable storage and re-hashed before it is
served; it is never reconstructed from a branch, an old source tree, or approximate counts. The
expected-current guard means a rollback that was correct a minute ago is refused once someone else's release
is live.

## Serialized lineage

| measure | value |
|---|---|
| release 1 outcome | ACTIVATED |
| second release staged from the ORIGINAL parent | refused |
| R1 in durable storage | True |
| R1 fragments available to the next release | 9 |
| deployments on the host | 1 |
