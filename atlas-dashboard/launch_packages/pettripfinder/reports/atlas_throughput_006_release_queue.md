# ATLAS-THROUGHPUT-006 — release queue

A durable JSON queue and a single-holder lease. Not a distributed orchestrator: the thing being protected is
one transition, and everything else in the factory stays parallel.

States: `QUEUED`, `VALIDATING`, `NEEDS_REPAIR`, `CANDIDATE_STAGED`, `AWAITING_AUTHORIZATION`, `AUTHORIZED`, `ACTIVATING`, `VERIFYING`, `LIVE`, `FAILED`, `ABANDONED`, `SUPERSEDED`.

- **Idempotent.** Entries are keyed by `(market_id, package_digest)`; the same sealed package submitted twice
  is one entry, not two.
- **Explicit supersession.** A newer package for a market does not silently replace an older one, and an entry
  that has begun work is finished or abandoned explicitly rather than superseded out from under itself.
- **The lease protects the flip, not the preparation.** Release B may validate and stage while A holds it, and
  a TTL means a crashed holder cannot block the factory forever.
- **Restage is a legal transition.** `AUTHORIZED -> CANDIDATE_STAGED` is how a candidate answers a moved
  parent; the authorization does not follow it, because the restaged candidate has a different digest.
