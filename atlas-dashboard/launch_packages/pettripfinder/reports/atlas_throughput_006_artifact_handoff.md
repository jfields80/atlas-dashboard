# ATLAS-THROUGHPUT-006 — trusted artifact handoff

005's rule, now with teeth: **no builder may run between validation, authorization and deployment.**

A candidate travels as a deterministic content-addressed archive with a manifest naming every file's digest.
Remote CI may COPY, EXTRACT, HASH, READ and TEST. It may not produce replacement deployment bytes —
`substitution_problems` compares a received tree against the SENDER's digests, so a rebuilt candidate is
caught as a different artifact rather than accepted as an equivalent one.

## Byte round trip, on the real 005 candidate

| hop | value |
|---|---|
| staged deployment digest | 437439f275b2f276fa2969adbc0ddc69 |
| digest in the handoff manifest | 437439f275b2f276fa2969adbc0ddc69 |
| digest after receipt | 437439f275b2f276fa2969adbc0ddc69 |
| candidate digest staged / received | 25b69be224b34ff4 / 25b69be224b34ff4 |
| archive deterministic | True |
| identical | True |
| problems | none |

The archive is deterministic: repackaging the received tree reproduces the same archive digest, which is what
makes "the artifact changed in transit" a decidable question.

## Cross platform

| hazard | count |
|---|---|
| files in the candidate | 4807 |
| CRLF files | 0 |
| case collisions | 0 |
| longest path (chars) | 122 |
| paths over 180 chars | 0 |
| backslash members | 0 |
| executable bits | 0 |

The factory builds on Windows and a runner is likely Linux. The archive stores bytes and a fixed mode and the
receiver proves the digest, so line endings, path case and file modes cannot drift in transit. Linux never has
to reproduce Windows output; it carries it and tests it. A receiver that REBUILT instead would hit every one
of these hazards, which is what the substitution check refuses.
