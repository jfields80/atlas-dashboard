# PetTripFinder hardened factory — the runbook

**Authority:** PTF-FACTORY-THROUGHPUT-HARDENING-001 (2026-09-02).
**Companion:** `docs/PTF_MARKET_FACTORY_LIFECYCLE.md` (the phase sequence),
`docs/PTF_ACQUISITION_ROUTER_DESIGN.md` (the paid router),
`docs/PTF_PAID_ATTEMPT_LEDGER.md` (never pay twice).

This page is the contract a market order follows. It is short on purpose: the
three sections below are the acquisition order, the regression order and the
factory freeze rule. Everything else lives in the modules they name.

## Why this exists

Dayton APPLICATION-002 applied 23 rows in about 45 minutes and then spent about
290 minutes on 85 test failures across 19 modules. None was a defect. Each was a
historical one-shot suite asserting over the WHOLE current package, or a global
count restated in one more file, and each stale pin was followed by another
~37-minute full regression. Separately, Dayton walked 27 property pages into an
attended browser session without ever evaluating Firecrawl, a lane the route
table already sends three of those brands to.

## Acquisition order (the ladder)

`scripts/pettripfinder/acquisition/ladder.py` — one ordered vocabulary, one
decision per row, evidence-aware.

| rank | lane | billed in | what settles a row |
|---|---|---|---|
| 0 | `OWNED_EVIDENCE` | nothing | a repository-owned capture corroborates an identity-bound read |
| 1 | `LOCAL_FREE_DISCOVERY` | nothing | OSM / Geofabrik / official locators / sitemap inventory (identity, not policy) |
| 2 | `DIRECT_STATIC_FETCH` | nothing | one HTTPS GET through the canonical gates; VALID, POLICY_NOT_FOUND and IDENTITY_MISMATCH all SETTLE the row |
| 3 | `FIRECRAWL` | plan credits | a rendered fetch, **only** for a family the route table sends there on a measured decision |
| 4 | `ATTENDED_BROWSER` | nothing | a person in a real Chrome session |
| 5 | `PAID_FETCH` | USD | Bright Data browser / web unlocker, behind a cost plan |
| 6 | `PAID_IDENTITY_DISCOVERY` | USD | Places and the like, identity only |

Rules the planner enforces:

- **Firecrawl never outranks a deterministic first-party fetch.** Only a
  channel failure (`ACCESS_DENIED`, `UNHYDRATED`, `BLANK_PAGE`,
  `NAVIGATION_FAILED`, `UNEXPECTED_PAGE`, `CAPTURE_FAILED`) moves a row down
  the ladder. A refusal escalates; a silence does not.
- **Candidacy is evidence-aware.** `FIRECRAWL_ROUTED_FOR_FAMILY` (IHG, Wyndham,
  Choice today) is a candidate. `FIRECRAWL_KNOWN_CAPABILITY_WALL` (Marriott,
  Hilton, measured by HARD-LANES-003) never is. `FIRECRAWL_UNMEASURED_FOR_FAMILY`
  is probe-eligible, not a candidate. A code-bound family whose property code
  will not parse from the URL is `PROPERTY_CODE_UNPARSEABLE_ROUTING_REPAIR_REQUIRED`
  and needs a routing repair, not a credit (Detroit PASS-008 lost 49 of 65
  attempts to this).
- **Identity is never positional.** `bind_results` binds a result only to the
  request whose identity key AND requested URL it names, and only when the
  adapter's identity assessment confirmed the page. A result naming no identity,
  a different URL, an unconfirmed identity or a second result for one request
  is reported `UNBOUND`, never guessed. This is the Dayton SPA defect class.
- **A Firecrawl result is classified, not trusted.** `FIRECRAWL_PUBLICATION_GRADE`
  needs VALID + confirmed identity + publication grade + a property-specific
  surface. An amenity chip or a brand page is `FIRECRAWL_IDENTITY_ONLY`. The
  others are `SOURCE_SILENT`, `BLOCKED`, `MISMATCH`, `FAILED`.
- **The trigger.** `attended_pressure` warns when at least 20% of the
  unresolved routed cohort is Firecrawl-routable and about to be walked into a
  browser. It is a routing decision point, not a correctness rule.
- **Every Firecrawl call has provenance.** `firecrawl_capture.request_envelope`
  (deterministic, sha256 over URL + profile) and `provenance` (requested and
  final URL, status, timestamp, content sha256, vendor request id, per-call
  credits when reported, redacted error) plus a per-call ledger at
  `data/acquisition/firecrawl_call_ledger.jsonl`. Spend is still read from the
  credit delta, never from a per-row constant.

Replay a market's committed reports through the planner with
`scripts/pettripfinder/factory_throughput_benchmark_001.py`; it fetches nothing.

## Regression order (the lanes)

`scripts/pettripfinder/regression_lanes.py` — a committed lane table, a runner,
a baseline manifest and a node-id classifier. Markers are applied at collection
from the same table (`pytest.ini`, `conftest.py`); select with `-m <lane>` or
`--ptf-market <id>`.

For a **market-scoped change with no shared-code change**:

```
python scripts/pettripfinder/regression_lanes.py run --lane market_targeted --market <id> --out data/regression/1
python scripts/pettripfinder/regression_lanes.py run --lane policy_schema --lane identity_routing --out data/regression/2
python -m scripts.pettripfinder.release_contracts            # every contract against its own authority, seconds
python scripts/pettripfinder/regression_lanes.py run --lane release_contract --out data/regression/3
python scripts/pettripfinder/assemble_production_site.py --output data/deployment_staging/<candidate>
#   fix the factual epoch pins the lanes surfaced (see below); re-run 1-3 until clean
git commit
python scripts/pettripfinder/regression_lanes.py run --lane full_regression --out data/regression/full
python scripts/pettripfinder/regression_lanes.py classify --baseline launch_packages/pettripfinder/regression_baselines/<prior sha>.json --run data/regression/full --rerun-flakes
```

Every lane except `full_regression` deselects the classes listed in
`regression_lanes.DEFERRED_TO_FULL_REGRESSION` (today: the per-market
"every market assembles" proof, 638 s on the baseline); the assembly step
produces the same facts once, and the final regression runs them once more.

ONE full regression, after the commit, classified against the committed
baseline for the prior sha. Every failing node id gets exactly one class:
`PRE_EXISTING`, `EXPECTED_EPOCH_CHANGE` (named in a file the order writes),
`TEST_HARNESS_FLAKE` (passed on an isolated re-run), `TRUE_NEW_FAILURE`. The
order is clean only at `TRUE_NEW_FAILURE = 0`. Counts are never compared.

If **shared or generic code** changed, run the affected lanes at step 2 as well
(`cross_market`, `assembly`, `deployment_architecture` as the change warrants).

### Where the pins live now

| what | file | who edits it |
|---|---|---|
| current per-market counts (census, pet_friendly, verified_no_pets, resolved, unresolved, out_of_category, profiles, corridor_routes, last_moved_by) | `tests/pettripfinder/pins/market_state.json` | the order that moves the market |
| live production pins and fresh-assembly pins | `tests/pettripfinder/pins/deployment_state.json` (`live` / `source`) | an application order moves `source` and sets `ahead_of_production`; a deployment order moves `live` and clears it |
| which markets later work moved out from under a consumed authorization | `tests/pettripfinder/pins/supersessions.json` | the order that re-authors a contract adds its market under every consumed authorization that bound it |

`tests/pettripfinder/contracts/test_market_state_pins.py` is the ONE place the
pins are held to the release contracts, packages, shards, censuses, partitions,
manifest, records and authorizations. Every other suite reads the pin through
`pettripfinder.market_state` (`current(market_id)`, `live()`, `source_assembly()`).

### How a historical suite stays meaningful

`pettripfinder.epochs`:

- `HistoricalEpoch(work_order, market_id, facts)` — what a closed order left
  true; asserted only against that order's OWN artifacts (its partition, its
  report, its ledger), which never move.
- `cohort(records, by_ledger(...) | by_caveat(...) | by_identity_keys(...))` —
  the records a closed order owns inside the LIVE package; counts become
  statements about the cohort, not the package.
- `whole_market_counts_or_superseded(epoch, current(market), fields)` — the one
  whole-market assertion a closed order keeps: exact while the pin still names
  that order as `last_moved_by`, superseded BY THE NAME of the order that moved
  the market otherwise.
- `superseded(by=..., what=...)` / `superseded_assertion(...)` — an obsolete
  current-state assertion retires by a named work order; the historical
  assertions around it keep running. Blanket skips of a module are not a thing.
- `markets_moved_since(authorization_id)` — read from `supersessions.json`;
  the historical authorization still binds every market not listed.

### What an application order edits, in test terms

1. `pins/market_state.json` — the market's row and `last_moved_by`.
2. `pins/deployment_state.json` — the `source` block (`ahead_of_production: true`,
   `moved_by`, the fresh bundle/sitemap shas and totals).
3. `pins/supersessions.json` — the market under the LIVE authorization's
   `moved_by_later_work` (and any older consumed authorization that bound it).
4. The order's own suite, declaring its `HistoricalEpoch` and cohort selector.

Nothing else should need a number. If a lane surfaces a module that still
restates one, that module is the defect: move it onto the pin.

## POST-BROAD FIX RULE

**Authority:** PTF-FACTORY-REGRESSION-V2-001.

The lanes above answer *which subset finds the pins a market change moved*.
They do not answer the question that costs the most wall-clock: the first broad
regression has already run, it returned one `TRUE_NEW_FAILURE`, and you have
just fixed it. Does closing it cost **another** 90–110 minutes?

Cincinnati made it concrete. The broad regression returned exactly one node:

```
tests/pettripfinder/acquisition/test_store_integration_025.py::test_every_run_on_disk_is_classified
```

The fix added two run ids to `OTHER_MARKET_RUNS` — a module-level literal set
in a test file that declares which directories under `data/acquisition/` belong
to another market. No authority moved. No runtime module was touched. No bundle
changed, and the candidate hash was identical before and after. The workflow
still spent another full regression proving it.

**The rule.** After the first broad regression, for each fix:

1. apply the fix;
2. classify the change surface;
3. run the delta-scoped validation;
4. if `FULL_REGRESSION_REQUIRED = NO`, close the failure by **node id** and stop;
5. if `YES`, run another full regression.

```
python -m scripts.pettripfinder.regression_delta classify --base <prior sha>
python -m scripts.pettripfinder.regression_delta validate \
    --base <prior sha> --head WORKTREE \
    --baseline launch_packages/pettripfinder/regression_baselines/<prior sha>.json \
    --require-closed "<the TRUE_NEW node id>" \
    --out data/regression/delta-1 \
    --closure-out launch_packages/pettripfinder/failure_closures/<order>-1.json \
    --order <ORDER-ID> --fix-commit <sha>
```

`validate` exits non-zero unless every `--require-closed` node was **executed
and passed** in the delta run, and no node outside the baseline failed. A node
that was never collected is `NOT_EXERCISED`, not closed — absence is not
evidence, which is why no step here compares counts.

### The change classes

`classify` reads file paths and, for test modules, the two versions' syntax
trees. It never reads the commit message. The committed, machine-readable
matrix is `launch_packages/pettripfinder/regression_validation_matrix.json`
(regenerate with `regression_delta matrix --out …`; a contract test fails if
the export drifts from the module).

| change class | assembly | full regression |
|---|---|---|
| `AUTHORITY_CHANGE` | required | **required** |
| `GENERIC_RUNTIME_CHANGE` | required | **required** |
| `SCHEMA_CHANGE` | required | **required** |
| `ROUTING_SEMANTIC_CHANGE` | required | **required** |
| `DEPLOYMENT_CHANGE` | required | **required** |
| `UNCLASSIFIED` | required | **required** |
| `TEST_EXPECTATION_CHANGE` | not required | conditional — required when the expectation is *shared current state* (`tests/pettripfinder/pins/`, a `conftest.py`, `epochs.py`, `market_state.py`, a `*_freeze.py` helper, a shared fixture); not required when it is confined to the modules that name it |
| `BOOKKEEPING_REGISTRATION_CHANGE` | not required | not required |
| `DOCUMENTATION_ONLY` | not required | not required |
| `GENERATED_REPORT_ONLY` | not required | not required |
| `BASELINE_MANIFEST_ONLY` | not required | not required |

A narrow class still owes work: the owning test modules, every test module
whose source names the changed module (an over-inclusive reverse-import scan),
the owning directory for a bookkeeping change, and the `market_targeted` lane
for every market the change names — including markets named by the run ids the
registration itself adds.

### SAFE DELTA — a run-registration declaration

Adding `cincinnati_oh_free_static_001` and `cincinnati_oh_firecrawl_001` to
`OTHER_MARKET_RUNS`. Classified `BOOKKEEPING_REGISTRATION_CHANGE`, so:
`FULL_REGRESSION_REQUIRED = NO`, no assembly, and the proof is the owning
directory plus Cincinnati's own modules.

### UNSAFE DELTA — a policy parser change

Editing anything under `scripts/pettripfinder/contracts/`, a reader, a
renderer, the assembler, a market authority shard, a release contract or a
deployment record. Classified `GENERIC_RUNTIME_CHANGE` (usually alongside
`SCHEMA_CHANGE`, `ROUTING_SEMANTIC_CHANGE` or `DEPLOYMENT_CHANGE`), so
`FULL_REGRESSION_REQUIRED = YES` and assembly is mandatory.

### Why the bookkeeping narrowing is safe

Three rules, each with its own test in
`tests/pettripfinder/test_regression_delta_001.py`:

- a path no rule claims is `UNCLASSIFIED`, and `UNCLASSIFIED` requires a full
  regression — teaching the factory a new directory can only make it slower;
- a test file drops to `BOOKKEEPING_REGISTRATION_CHANGE` only when the two
  versions' module-level syntax trees differ **solely** in the elements of a
  literal collection named in `regression_delta.REGISTRATION_CONTAINERS` — a
  committed list of containers that declare *what exists* rather than what a
  computation should return. An expectation table that happens to be a literal
  set is not on that list. An added import, an added test, a changed assertion,
  or a container turned into a comprehension all block the narrowing;
- the verdict over a whole change is the **strictest** row any file selects, so
  one dangerous file among a hundred harmless ones still costs the full suite.

Every closure leaves a durable artifact under
`launch_packages/pettripfinder/failure_closures/`: the original `TRUE_NEW` node
ids, the fix commit, the changed files and their classes, the validations that
were required, the per-node verdict, and the full-regression decision with its
reason. A committed artifact that does not account for every original node id
fails its own test.

## Factory freeze rule

Shared or generic code (`scripts/pettripfinder/acquisition/*`, `brightdata/*`,
`contracts/*`, `policy/*`, the assembler, the renderer, the readers, the
routing registry) changes only for:

- a wrong identity;
- a wrong policy;
- a duplicate spend;
- data loss or corruption;
- a deployment-blocking defect;
- an explicitly authorised factory throughput engineering order such as
  PTF-FACTORY-THROUGHPUT-HARDENING-001.

A market order that finds itself editing shared code for any other reason
stops and files the finding instead. A reading rule is never widened during the
review it feeds.

## Measured on this order (source c854469, 8 cores)

| measurement | value |
|---|---|
| Dayton APPLICATION-002 total | 337 min |
| of which actual application | ~45 min |
| old full regression, each | ~37 min (several per order) |
| whole-site assembly suites (045 + 046) in the old chunk | 914 s + 528 s |
| ladder replay, Dayton static failures | 48 rows: 33 Firecrawl candidates, 12 attended, 1 routing repair, 2 settled |
| attended pages Dayton opened / of which Firecrawl-routable | 27 / 21 |
| projected attended reduction (expected, measured rates) | ~72% of rows headed to a browser |

The regression-lane timings measured by this order are in
`launch_packages/pettripfinder/reports/factory_throughput_001_benchmark.json`.
