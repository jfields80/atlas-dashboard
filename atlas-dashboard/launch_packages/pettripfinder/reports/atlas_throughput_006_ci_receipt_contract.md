# ATLAS-THROUGHPUT-006 — CI validation receipt contract

`ptf-ci-validation-receipt/1.0`. "CI passed" is a string; this is evidence. The release coordinator verifies the receipt's own digest,
the commit, the candidate, the dependency digest, the shards completed, the node accounting and the failure
classification before it will treat a broad validation as satisfied.

Refusals: `RECEIPT_INCOMPLETE`, `RECEIPT_WRONG_CANDIDATE`, `RECEIPT_WRONG_COMMIT`, `RECEIPT_WRONG_DEPENDENCY_DIGEST`, `RECEIPT_STALE`, `RECEIPT_SHARDS_INCOMPLETE`, `RECEIPT_NODES_INCOMPLETE`, `RECEIPT_TRUE_NEW`.

**A data-only release is not missing a receipt.** When the change class owes no broad run the state is
`NOT_REQUIRED_BY_POLICY` — a decision, not a gap.

**Legacy failures keep their existing identity semantics.** A failure is PRE_EXISTING only when the node id is
in the f75aa95 baseline AND its normalised signature matches; the same node failing for a materially different
reason is TRUE_NEW. Addresses, absolute paths, temp paths and timestamps are normalised away so a signature
survives a different machine.
