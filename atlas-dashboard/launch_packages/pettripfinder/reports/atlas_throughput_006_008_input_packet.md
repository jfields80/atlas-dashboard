# ATLAS-THROUGHPUT-006 → 008 input packet

Status: PROPOSED. 008 is the THREE-MARKET LIVE FACTORY PROOF: three qualified launches in one operating day,
one small/medium, one medium, one large, against frozen quality floors.

## What 008 needs that now exists

| capability | where | measured |
|---|---|---|
| market-local validation | 002 | ~318 s |
| sealed package + FAST release safety | 003 | 60.9 s standalone, 5.5 s inside a candidate |
| persistent validated bundle reuse | 004 | 3.7–8.4 s, 0 builder invocations |
| candidate composition from live + one delta | 005 | 178.0 s, 9 of 10 markets inherited |
| durable release store and guarded rollback | 005 | restore from storage, stale rollback refused |
| remote broad validation when required | 006 | projected 1,375.7 s wall, 0 jobs for data-only |
| trusted artifact handoff | 006 | byte-identical round trip on a real candidate |
| release queue and serialized activation | 006 | idempotent, explicit supersession, leased flip |
| live HTTP verification | 006 | nine checks, UNKNOWN distinct from FAILED |

## What 008 still needs, and must not assume

1. **Markets.** Three qualified candidates. On this branch only Dayton and Cleveland seal; Lexington,
   Nashville and Chattanooga are shadow-ready but unregistered here. 008 needs its three markets registered,
   sealed and package-clean BEFORE the operating day, not during it.
2. **A current tree.** This worktree predates Toledo's launch, so its committed live records are one release
   behind production. 008 must run from a tree whose CURRENT VERIFIED LIVE is actually current.
3. **An open production gate.** `release_production_gate.json` is empty by design. 008 needs it opened per
   market, with the founder's authorization bound to each exact candidate digest.
4. **Remote execution actually proven.** 006 implemented the workflow but could not dispatch it. If any of the
   three launches carries a shared change, 008 needs a real CI receipt, which needs Actions verified enabled.
5. **The measurements 006 could not take:** founder active time per release, queue wait, CI wait, and
   activation plus verification against production.

## Frozen quality floors to carry in

Every launch must still clear: first-party evidence binding, the intended-delta and removal guards, the
release index comparison (no unrelated market, profile or route lost), deterministic changed-market builds,
byte-identical handoff, an authorization binding four digests, the parent guard at activation, and the nine
live checks. 008 is a throughput experiment; none of these floors moves for it.

## The shape of the day

Serialized activation, overlapping preparation: while release A activates and verifies, B and C validate,
stage and queue. Each subsequent release restages on the release its predecessor produced. That path is proved
in 005 and 006 against simulators; 008 is where it meets production.
