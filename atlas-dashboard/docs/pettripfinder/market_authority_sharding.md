# PetTripFinder market authority sharding

**Work order:** PTF-MARKET-AUTHORITY-SHARDING-001, Phase 1
**Baseline:** `20279f4b6f66a073f69823275c23f5c3481f173b`

## What changed

Three authority files were written by every market at once:

| file | records at baseline |
| --- | --- |
| `launch_packages/pettripfinder/identity_routing.json` | 277 routes |
| `launch_packages/pettripfinder/hotel_exclusions.json` | 75 exclusions |
| `launch_packages/pettripfinder/seed_businesses.csv` | 296 seed rows |

Nothing about their *content* was shared — every record already carried a
`market_id` and was read back through it. What was shared was the *file*. Two
markets working in parallel each appended to the same array, and git reported a
conflict in a file where no two records had anything to say to each other. The
resolution was always the same mechanical union.

Each market now owns its own directory:

```
launch_packages/pettripfinder/markets/authority/<market_id>/
    identity_routing.json
    hotel_exclusions.json
    seed_businesses.csv
```

A market writer touches exactly one directory, so two markets writing at the
same time touch disjoint paths and cannot conflict.

## The three global files still exist

They are now **generated compatibility artifacts**, not authored ones:

```
per-market shards -> deterministic assembler -> legacy global artifacts -> existing consumers
```

Every existing reader is unchanged. No big-bang reader migration was taken; it
is a separate decision.

## Working with the shards

Edit only your market's shard, then regenerate:

```
python -m scripts.pettripfinder.build_global_authority --write
```

Verify (this is what the test suite runs):

```
python -m scripts.pettripfinder.build_global_authority --check
```

`--check` fails and names any generated artifact whose committed bytes are not
what the shards produce. That check is the enforcement mechanism for write
discipline: a hand-edit to a generated global file cannot survive it.

`launch_packages/pettripfinder/ptf_global_authority_manifest.json` records the
per-market counts and content hashes and the hash of each generated artifact. It
carries no wall-clock timestamp on purpose — a manifest whose hash changed
because it was rebuilt on a different afternoon could not answer the only
question it exists to answer.

## Validation

Sharding moved records between files; it did not fork any contract.

* A routing shard is validated by `identity_routing.validate_authority`.
* An exclusions shard is validated by `hotel_exclusions.validate`.
* Both validators run **again on the assembled union**, which is what keeps the
  cross-market rules alive: one URL may bind one identity, one property code may
  bind one identity within its brand domain, one identity may be excluded once,
  one street identity may be excluded once.
* The seed has no contract module, so `market_authority.assemble_seed_rows`
  enforces the rule publication depends on: one identity holds at most one seed
  row per category.

A collision between two markets fails closed even though neither shard is wrong
by itself. `tests/pettripfinder/test_market_authority_sharding.py` proves that by
building colliding pairs and requiring a refusal.

## Aggregate test assertions

Per §8 of the work order:

* **Per-market exact truth stays pinned.** Columbus's 20 routes, Cleveland's 40
  exclusions, Columbus's 116 seed rows — each is one market's fact, changed only
  by that market's own work.
* **Global aggregate truth is derived** from the shards, because a global total
  is an arithmetic consequence of N independent files, and pinning a consequence
  forced every market's branch to retype a number in a file that had nothing to
  do with that market.

## Market registration

`scripts/pettripfinder/markets/contract.py::load_markets` already discovered
markets by file. Two central Python dicts remained:

* `discovery/market_config.py::_MARKET_FILENAMES` — the explicit registry still
  wins, and a market with no entry now resolves by the conventional filename
  (`market-id` → `market_id.json`) when that file exists. Every historical entry
  was that transform anyway. An unknown market with no file still fails closed.
* `discovery/source_families.py::CONCRETE_SOURCE_FAMILY` — retained verbatim so
  no registered market changes family. A market registered from now on declares
  its sources in `markets/coverage/<market_id>.json` under
  `source_family_overrides`, which `family_of` already merges on top.

---

## Deferred: lifecycle backlog (NOT in scope for this phase)

Recorded here because this phase is about git contention, not lifecycle
semantics. None of these is implemented.

1. **`AWAITING_PROPERTY_OPENING`** — there is no state for a property that is
   announced or under construction but not yet operating. Today such an identity
   is either absent or held for a reason that misdescribes it.
2. **An explicit terminal `CLOSED_OR_CONVERTED` lifecycle state.** The exclusion
   authority has `PERMANENTLY_CLOSED` and `CONVERTED_TO_NON_HOTEL_USE`, but
   `enums.py` has no terminal "closed" state for a census/partition record, so
   closures are currently carried through the candidate ledger's
   `disposition: closed` mechanism instead. The two vocabularies should be
   reconciled deliberately, not merged by accident.
3. **Conditional charge vocabulary / sanitation fees.** Whether the policy schema
   generalises a charge that applies only under a stated condition (a cleaning or
   sanitation fee charged only if required) needs a founder decision before any
   schema work.
