# ATLAS-THROUGHPUT-005 — atomic release coordinator and final candidate lifecycle

**Authority:** ATLAS-THROUGHPUT-005. Builds on 003's sealed package and FAST release lane and 004's
persistent validated market-bundle cache.

A release is now one equation:

```
CURRENT VERIFIED LIVE RELEASE
+ ONE AUTHORIZED SEALED MARKET PACKAGE DELTA
+ REUSABLE VALIDATED MARKET BUNDLES
= ONE EXACT FINAL STAGED CANDIDATE
```

and that candidate is the only artifact a founder can authorize.

## What exists now

`scripts/pettripfinder/release_coordinator.py` — the single writer of staged release manifests.

- **`LiveTruth`** — CURRENT VERIFIED LIVE RELEASE, read only. Wraps `release_index.current_verified_live`
  (which already reconciles the deployment record, the global manifest, the deployment-state pin and the
  consumed authorization and fails closed on any disagreement) and adds the committed-authority index plus a
  DERIVED parent release manifest, so the first candidate has a parent digest to bind to. `LIVE_REPRESENTATIONS`
  names all eight committed places that claim live truth, including the five facts each stored in four or more
  of them; the coordinator reconciles rather than picks.
- **`ReleaseStore`** — durable, content-addressed storage under `data/release_store/`
  (`releases/`, `fragments/`, `bundles/`). Not a cache: it holds the current live release and the rollback
  target so neither depends on an evictable artifact, and it is what lets a candidate inherit unchanged
  markets. Seeded from one whole-site assembly whose composed digest must equal the live record's.
- **`stage()`** — composes a candidate: every unchanged market inherited by fragment digest, the delta market
  from its validated 004 bundle, the release-global artifacts regenerated per `GLOBAL_ARTIFACTS` (an unknown
  artifact refuses). Final participation is an INPUT, so it is inside the bytes before the candidate is hashed.
  Membership that adds or removes a market relative to live must be named in an explicit authority.
- **`authorize()` / `authorization_problems()` / `parent_guard()`** — an authorization lives outside the
  candidate and binds the candidate digest, the deployment artifact digest, the parent release digest and the
  intended-delta digest. All four must still hold at activation.
- **`activate()` / `reconcile()` / `verify_live()` / `rollback()`** — the activation interface, idempotent by
  operation id, with UNKNOWN kept distinct from FAILED and reconciliation required before any retry. Rollback
  targets an exact prior verified release from durable storage and refuses if a newer release is live.
- **`SimulatedHost`** — the only host adapter 005 ships.

## How to use it

```
python -m scripts.pettripfinder.release_coordinator inspect     # live truth + every file that claims it
python -m scripts.pettripfinder.release_coordinator plan --package <sealed package>
python -m scripts.pettripfinder.release_coordinator status      # the production activation freeze
```

Seed the release store once from a whole-site assembly (`assemble(..., keep_fragments=True)`) before staging;
`plan` reports which markets have a stored fragment and which would be rebuilt.

## Boundaries

A staged candidate is an artifact, not a permission. Staging proves composition; 003's FAST lane proves
release safety; the founder's authorization is a separate record that binds one digest. `REAL_PRODUCTION_ACTIVATION`
is DISABLED: the production deployer is untouched, no market was promoted, no participation changed, and the
only activation in this order was against a simulator.
