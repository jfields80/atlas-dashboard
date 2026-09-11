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

**A node the lanes defer.** Every lane except `full_regression` deselects the
classes in `regression_lanes.DEFERRED_TO_FULL_REGRESSION` (today:
`TestEveryMarketAssembles`, which assembles every market's bundle). A
`TRUE_NEW` node in one of them comes back `NOT_EXERCISED` from the delta run
no matter what the fix did. Prove it with a run you make yourself at the fix
commit — in the order that produced the failure when the failure was
order-dependent — and hand its junit to `validate`:

```
python -m pytest <the module that leaked> <the failing modules> -q \
    -o junit_family=xunit2 --junitxml=data/regression/<order>-replay/replay.xml
python -m scripts.pettripfinder.regression_delta validate ... \
    --exercised-junit data/regression/<order>-replay/replay.xml --exercised-at <sha>
```

An exercised run fills **only** node ids the lanes left `NOT_EXERCISED`; it
never overrides a lane result, and the closure artifact records which run
proved each node (`node_id_sources`, `exercised_runs`). ATLAS-THROUGHPUT-004's
51 were closed this way: 5 by the lanes, 46 by an ordered one-process replay.

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
| `MARKET_LOCAL_TOOLING` | not required | not required — granted ONLY by the five-condition isolation proof below; every failure leaves the path in its prefix class |
| `MARKET_DATA_PACKAGE` | not required | not required — a sealed package, staging tree or receipt under `markets/{packages,staging,receipts}/<market>/`; inert data no build reads (ATLAS-THROUGHPUT-003) |
| `MARKET_AUTHORITY_DATA_ONLY` | required | conditional — a whole change set that is ONE registered market's authority data and nothing else; **not required ONLY** when a committed `FAST_DATA_ONLY_RELEASE` receipt says ELIGIBLE = YES for a sealed package covering the exact bytes AND `fast_release_activation.json` enables the market (it is DISABLED); otherwise exactly `AUTHORITY_CHANGE` |
| `NEW_MARKET_REGISTRATION_DATA_ONLY` | not required | conditional — a whole change set that is exactly ONE previously absent market's registration and nothing else; **not required ONLY** when `registration_data_only.evaluate` passes every check of the bounded registration safety union below; otherwise every path keeps its path class, and three of them are `DEPLOYMENT_CHANGE` |

### NEW_MARKET_REGISTRATION_DATA_ONLY (PTF-NEW-MARKET-REGISTRATION-DATA-ONLY-POLICY-001)

A registration writes four documents that belong to every market — the
participation record, the market's release contract, the build closure and
the market-state pin — and PTF-CHARLOTTE-CONTROLLED-REGISTRATION-REPLAY-003
measured that the ordinary workflow writes them in seven seconds and is then
charged a broad regression by their PATH classes. The path classes are right:
any of those documents can change what production serves. A registration is
the one operation where the change to all four is mechanically bounded — one
row, one contract instance, two declared inputs, one pin block — and where
every changed field can be checked directly. The committed contract is
`launch_packages/pettripfinder/registration_data_only_contract.json`
(regenerate with `registration_data_only contract --out …`; a contract test
fails if the export drifts from the module), and its field-level eligibility
matrix says, for every document and field, whether it is a registration fact
(`DATA_NARROWABLE`), checked against an independent derivation
(`DERIVED_CHECKED_INDEPENDENTLY`), behavior-bearing (`BEHAVIOR_WIDENS`), or
protected (`PROTECTED_INDEPENDENTLY`).

The class is granted to a WHOLE change set, never to a path, never because a
filename looks like a registration, a market is named, a count grew or
narrow validation was requested. `classify` runs the proof on every change
set; anything UNKNOWN is a failure. The eleven checks:

1. **change_set** — the registry gained exactly one market; every changed
   path is one registration role for that market (participation row,
   release contract, build closure, pin, market document, authority shard,
   its own census / policy package / partition, the derived globals) or a
   narrow companion (report, prose, baseline manifest, the market's OWN
   sealed package / receipt); no test, no code, no other market's data, no
   protected release state; the only narrowing blockers present are the two
   the registration owns (the closure and the pin).
2. **participation** — a REISSUE: base rows byte-identical, exactly one new
   row at `SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH` with no other
   keys, `decided_by` is the writing work order and never the founder,
   `markets_added = [<new>]`, the authorized set equals the base's,
   `supersedes` is the sha256 of the exact base bytes, and `lineage.records`
   is the base chain (repair-resolved) plus the base record;
   `decision_problems` is empty.
3. **release_contract** — a new instance with exactly the registration key
   shape; `canonical`, `minimum_release_gates`, `forbidden_output_tokens` and
   `publish` EQUAL the single value every base contract carries;
   `deployment_authorization` grants nothing; every count agrees with
   `release_contracts.derive_authority`; an unknown key widens.
4. **build_closure** — `shared_data_inputs` gains exactly the market's contract
   and market document; `remeasured_by` gains one note; `code_modules`,
   `per_market_data_inputs` and every other key are unchanged.
5. **derived_globals** — the committed globals are byte-identical to a
   regeneration from the shards (`build_global_authority --check`) and no
   other market's shard changed, so their diff IS the new market's rows.
6. **sealed_package** — a committed package under `markets/packages/<market>/`
   whose `dependency_input_digests` are exactly the head bytes of the seven
   authority files, sealed for `REGISTERED_LIVE`, declaring one joining market
   whose `add_routes` are its own derived surface, against the current live
   parent (rule N).
7. **fast_receipt** — a committed receipt for that package: 15/15 PASS,
   0 UNKNOWN, 0 FAILED, re-deriving its digest, bound to the same parent
   (deploy id, rollback target, source commit, live index digest), the same
   intended delta and dependency digest, the current lane version, the
   package's builder and contract versions, and two equal cold-build digests.
8. **expected_release** — EXPECTED = trusted live parent + the sealed package;
   ACTUAL = every registered market's committed authority with the new market
   participating; compared as COMPLETE SETS of markets, participation flags,
   profile identity keys, record digests, routes, ownership, corridor and
   market routes — never as totals, so one profile removed and one added
   fails at equal counts. Aggregates (parent + 1 market, parent + package
   profiles, parent + package routes) are checked as well.
9. **identity_routes** — `release_index.compare` over both releases: no
   cross-market identity collision, no duplicate route, no ownership
   movement, every live member preserved, every change declared.
10. **market_state_pin** — every base block byte-identical; one new block whose
    eight counts equal what the SEALED PACKAGE derives (census count, records,
    refusals, partition states, indexed profiles and corridor routes) and
    what the release contract states; `deployment_state.json` untouched.
11. **release_integrity** — nothing under deployment authorizations, records,
    the global manifest, the activation flag, the production gate or the
    deployment pin moved; the live parent is verified; the authorized set is
    unchanged.

When all eleven pass: `CHANGE_CLASS = NEW_MARKET_REGISTRATION_DATA_ONLY`,
`FULL_REGRESSION_REQUIRED = NO`, `REMOTE_BROAD_JOBS_REQUIRED = 0`,
`UNCHANGED_MARKETS_REBUILT = 0`, and the registration reaches
**AUTHORIZATION_READY**. It authorizes nothing: the founder authorization,
the current-parent guard, the exact-bytes deployment, targeted live
verification and the rollback guard are untouched and still owed by the
deployment order. The plan runs no lane, no reverse-dependent scan (the four
documents are named by 137 test modules — the broad run by another name) and
no whole-site assembly (rule J builds the joining market twice cold; no
other market's input moved).

The ordinary registration workflow, end to end:

```
python scripts/pettripfinder/market_registration_cli.py --market <id> --authority <proposed> --write
python -m scripts.pettripfinder.build_global_authority --write
python scripts/pettripfinder/<market>_release_contract_NNN.py          # the contract instance
python scripts/pettripfinder/<market>_participation_registration_NNN.py --write   # row + closure
# state the market's reviewed block in tests/pettripfinder/pins/market_state.json
python -m scripts.pettripfinder.registration_release_lane seal --market <id>   # package + FAST receipt
python -m scripts.pettripfinder.regression_delta classify --base <sha> --out <classify.json>
python -m scripts.pettripfinder.registration_release_lane packet --market <id> --classification <classify.json>
```

Measured on Charlotte (PTF-NEW-MARKET-REGISTRATION-DATA-ONLY-POLICY-001): the
registration writes in seconds, the lane in about a hundred (the two cold
builds of the joining market), the classification with its proof in about
ten. Shared runtime, schema, assembler, deployment implementation and test
infrastructure changes remain broad; a registration that also edits a test
expectation is not a registration and costs the full suite.

### FAST_DATA_ONLY_RELEASE (ATLAS-THROUGHPUT-003)

A data-only change to one market's authority owes fifteen direct checks
(rules A–O of `scripts/pettripfinder/fast_release_lane.py`) over a SEALED
MARKET PACKAGE (`scripts/pettripfinder/sealed_market_package.py`, written
only by `scripts/pettripfinder/market_package_writer.py`, which rejects
before serialization on every owning contract):

- A package schema/seal, B identity (canonical keys, same-premises proof or
  declared relation), C first-party binding (`first_party_binding.py`: eight
  checks per record, competitor evidence is LEAD ONLY, a fee / count /
  weight / amenity chip / service-animal sentence alone establishes
  nothing), D policy semantics (policy schema + evidence contracts,
  fee/deposit conflation), E route references, F partition reconciliation,
  G whole-release identity/route collisions and H unrelated-member
  preservation over the O(data) `release_index.py` (CURRENT_VERIFIED_LIVE
  from the deployed record + manifest + pin, never a render), I intended
  delta accounting (every add / update / removal / route change declared,
  removals with a ruling), J the real per-market assembler over a staged
  tree (`package_staging.py`; committed authority untouched), K the same
  build a second time COLD (`assembly_session_cache.cold()`; two cache hits
  never pass), L hashes (seal re-derives, evidence index, artifacts),
  M evidence age and `evidence_revocations.json`, N the package's parent
  live state equals the live records and the rollback chain verifies,
  O every paid capture carries a reservation key that re-derives.
- UNKNOWN ⇒ NOT ELIGIBLE. The receipt (`markets/receipts/<market>/`) names
  every rule, digest and expiry condition; `FAST_DATA_ONLY_RELEASE_ELIGIBLE`
  is YES only when all fifteen are PASS.
- `classify` grants `MARKET_AUTHORITY_DATA_ONLY` to a change set only when
  every authority row is one market's own file (or a derived global whose
  diff names only that market), no shared runtime / schema / assembler /
  deployment / test-infra row is present, and nothing is UNCLASSIFIED. The
  plan's `FAST_DATA_ONLY_RELEASE_REQUIRED` is then YES, and
  `FULL_REGRESSION_REQUIRED` is NO only with the committed ELIGIBLE receipt
  and activation. `FAST_PATH_PRODUCTION_ACTIVATION = DISABLED` until 004/005.
- Every row also carries a `release_surface`: MARKET_LOCAL_TOOLING,
  MARKET_DATA_PACKAGE, MARKET_AUTHORITY_DATA_ONLY, SHARED_SCHEMA_CHANGE,
  SHARED_RUNTIME_CHANGE, ASSEMBLER_CHANGE, DEPLOYMENT_CHANGE,
  CLASSIFIER_TEST_INFRA_CHANGE, UNKNOWN_MIXED or NARROW_NON_RELEASE.

### MARKET_LOCAL_TOOLING (ATLAS-THROUGHPUT-002)

ATLAS-THROUGHPUT-001 measured that `prefix:scripts/pettripfinder/` →
`GENERIC_RUNTIME_CHANGE` claimed every `<market>_*.py` helper of a shadow
market, so Nashville, Toledo 001, Lexington and Chattanooga each owed a
~2-hour broad regression for files no production module imports. The
classifier now has a notion of a market-local zone:

- `launch_packages/pettripfinder/market_local_ownership.json` — the ONE
  registry of zones (owned paths, allowed shared imports, allowed write
  roots, owned tests, `production_runtime_included`), plus the `never_local`
  fence no zone may cross. `python -m scripts.pettripfinder.market_local_ownership --owner <path>`.
- `scripts/pettripfinder/market_local_isolation.py` — the proof, run by
  `classify` on every path whose rule is in
  `regression_delta.MARKET_LOCAL_REFINABLE_RULES`: (1) exactly one zone owns
  the path (old AND new path of a rename); (2) every import is stdlib, an
  allow-listed shared module, or the zone's own; (3) every write target
  resolves statically inside the zone's roots (an unresolvable target FAILS);
  (4) nothing outside the zone names the module, no shared code enumerates
  the directory a data file sits in, every subprocess is read-only git or
  pytest; (5) the market is unregistered at the head being classified.
  `python -m scripts.pettripfinder.market_local_isolation --base <sha> --head <sha> <path>`.
- A change set that touches the classifier, the lanes, the registry, the
  proof, the session cache, `conftest.py`, `pytest.ini` or any shared test
  state (`regression_delta.NARROWING_BLOCKERS`) gets NO narrowing at all:
  the selector cannot authorize its own narrowing.
- The routing / policy / identity filename globs are refinable: a helper
  called `<market>_routing_001.py` is not `ROUTING_SEMANTIC_CHANGE` for its
  name when the proof passes; a change to `identity_routing.py` or to
  `discovery/config/osm_extracts.json` (shared, inside the fence) still is.
- What it owes: the zone's own test modules, the per-market contract rows,
  every test module whose source names the changed one. Never assembly,
  never `full_regression`, and therefore never the website-generation
  integration lane.
- What it does NOT change: `AUTHORITY_CHANGE`, `GENERIC_RUNTIME_CHANGE`,
  `SCHEMA_CHANGE`, `ROUTING_SEMANTIC_CHANGE`, `DEPLOYMENT_CHANGE` and
  `UNCLASSIFIED` rows are byte-for-byte what V2-001 committed. A promotion
  (registry, package, contract, participation) is `AUTHORITY_CHANGE` /
  `DEPLOYMENT_CHANGE` and still costs the full suite until
  ATLAS-THROUGHPUT-003 establishes the critical fast lane.

The website-generation integration suites (`tests/website_generation/integration/`,
above all `test_pettripfinder_demo_media.py`, measured at 57–71 % of every
broad run) are the `website_generation_integration` lane: a BROAD AUDIT of
the engine chain over the real launch package. They run inside every
`full_regression` and on their own with
`regression_lanes.py run --lane website_generation_integration`; a
market-local plan never selects them.

### Persistent market-bundle cache (ATLAS-THROUGHPUT-004)

`scripts/pettripfinder/bundle_cache.py` makes a validated market bundle
reusable ACROSS runs. The rule: if every declared build input is identical
and the exact output bytes were validated under a compatible policy, do not
rebuild — and a hit is a proof, never an assumption.

- BUILD INPUT KEY = sha256 of a canonical manifest: package digest and section
  digests, the staged render tree, the 43 shared data files + the market's
  affiliate shard and the 177 repository modules a build reads/loads
  (`launch_packages/pettripfinder/bundle_cache_closure.json`, MEASURED by
  tracing two real builds), builder/assembler sources, toolchain (Python,
  platform, requirement lockfiles, installed package versions), build
  arguments, locale, `PTF_*` environment. The output digest is never an
  input; the validation policy version sits OUTSIDE the byte key.
- Storage under `data/bundle_cache/` (`PTF_BUNDLE_CACHE_ROOT`): immutable
  `objects/<bundle sha>.zip`, `index/<key>.json`, `receipts/<digest>.json`,
  per-key `locks/`, `quarantine/`, `tmp/`, `telemetry.jsonl`.
- TRUSTED only when the build succeeded, its gates passed, the archive
  round-trips to the built digest, no undeclared repository file was read
  (an `open()`/`open_code` tracer decides), determinism was proven by a
  second cold build, no evidence is revoked or expired. Anything less is an
  UNTRUSTED row that never satisfies a lookup.
- A lookup re-extracts and re-hashes the bytes, re-reads the receipt and
  checks it binds this key, this digest, this policy and these dependency
  digests, then revocation and freshness. Corrupt, partial, zero-byte,
  mismatched or receipt-less entries are quarantined and rebuilt.
- `cold_required=True` bypasses the cache (BYPASS_COLD_REQUIRED) for a
  determinism claim; `PTF_BUNDLE_CACHE_FORBID_BUILD=1` makes a miss raise
  (the cross-process proof). Statuses: MISS, HIT, HIT_AFTER_WAIT, REVALIDATE,
  INVALID_CORRUPT, INVALID_REVOKED, INVALID_POLICY_VERSION,
  BYPASS_COLD_REQUIRED.
- A hit is artifact identity, not release safety: the FAST lane's rules
  A–I and L–O still run (`run_fast_lane(..., bundle_cache=…)` lets J be the
  hit and K inherit the bundle receipt's determinism);
  `PRODUCTION_RELEASE_CONSUMPTION = DISABLED` in
  `fast_release_activation.json` — the production assembler and the deployer
  do not read the cache until 005.
- Retention: `gc_plan()` is a DRY RUN; the live and rollback releases are
  never only in this cache.

**Session-cache isolation (the 004 migration audit's lesson).** A staged build runs under
`package_staging.overlay`, and the 002 session cache's key must be computed INSIDE that
overlay: its dynamic inputs (the overlay census dir, `PTF_*` env, module state) are what
distinguish a staged render from the committed one. The bundle cache freezes only the
tree walk while a build is traced (`_frozen_tree_fingerprint`); freezing the whole
fingerprint once stored a Dayton withdrawal render under the committed Dayton key and a
later production assembly in the same pytest session came out four profiles short.
`TestSessionCacheIsolation` pins it.

### The release coordinator (ATLAS-THROUGHPUT-005)

A release is composed, never re-derived from whatever the branch happens to hold:

```
CURRENT VERIFIED LIVE RELEASE + ONE AUTHORIZED SEALED PACKAGE DELTA
+ REUSABLE VALIDATED MARKET BUNDLES = ONE EXACT FINAL STAGED CANDIDATE
```

`scripts/pettripfinder/release_coordinator.py` is the only writer of staged release manifests.

**Source ready is not live, and the branch is not the baseline.** `LiveTruth` reads CURRENT
VERIFIED LIVE RELEASE through `release_index.current_verified_live`; every unchanged market is
inherited from `data/release_store/` by fragment digest. A stale worktree contributes exactly one
sealed package delta, so it cannot remove a market that went live after it forked. Seed the store
once from a whole-site assembly whose composed digest equals the live deployment record's, then
`plan` reports which markets are inherited and which would be rebuilt.

**Final participation is an input, not a later flip.** Membership is read from the participation
document and hashed into the candidate before its digest exists. There is no build, authorize,
flip, rebuild path: a pre-flip candidate is a different artifact with a different digest, and its
authorization refuses the post-flip one. Adding or removing a market relative to live requires an
explicit authority naming that market; absence is never read as a removal.

**Authorization binds four digests** — candidate, deployment artifact, parent release, intended
delta — and lives outside the candidate bytes. Before activation the parent guard re-checks that
the authorized parent is still live; if another release landed first the answer is `STALE_PARENT`
and the candidate must be re-staged, not re-signed.

**Activation is idempotent by operation id, and UNKNOWN is not FAILED.** A timeout means reconcile
the host before anything else: the activation may have landed. Rollback restores an exact prior
verified release from durable storage, never a rebuild, and refuses when a newer release is live.

`REAL_PRODUCTION_ACTIVATION` is DISABLED. The only host adapter is a simulator; the production
deployer does not import the coordinator.

### Session-local assembly reuse (ATLAS-THROUGHPUT-002)

`scripts/pettripfinder/assembly_session_cache.py`: within ONE process, the
generator, the per-market bundle and the whole-site compose answer a second
request for the same input key (build args + the content hash of every file
under `launch_packages/pettripfinder`, `deploy/netlify`, `scripts`,
`engines`, `repositories`, `templates`, `static`, plus the patched registry /
census directory, `PTF_*` environment and the builders' module state) with a
verified copy of the first build. A failed build stores nothing; a stored
copy is re-hashed before reuse; each consumer gets its own copy. A test whose
claim IS a cold execution wraps the calls in `assembly_session_cache.cold()`;
`PTF_ASSEMBLY_REUSE=0` disables reuse process-wide. The profiler reports
every decision as `BUILD_EXECUTED` or `REUSE_HIT` with the seconds avoided.
The production CLI runs one assembly per process and is unaffected.

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

## Profiling a run (ATLAS-THROUGHPUT-001)

`scripts/pettripfinder/throughput_profile.py` is an opt-in pytest plugin. It is
loaded only when named on the command line and is inert without an output
path, so the harness is untouched when it is absent:

```
python -m pytest tests -q -p no:cacheprovider -o junit_family=xunit2 \
    --junitxml=data/regression/<run>/full_regression.xml \
    -p scripts.pettripfinder.throughput_profile \
    --ptf-profile-out data/regression/<run>/profile.jsonl \
    --ptf-inventory-out data/regression/<run>/inventory.json
python -m scripts.pettripfinder.throughput_baseline run --profile data/regression/<run>/profile.jsonl --out <report.json>
python -m scripts.pettripfinder.throughput_baseline junit --out <report.json> <label>=data/regression/<run>/full_regression.xml
```

The JSONL carries one row per test (setup / call / teardown seconds, peak
working set), per slow fixture setup, per assembly call (kind, market, elapsed,
output hash, `market_input_hash`, `dependency_input_hash`), plus collection and
session rows. `throughput_baseline run` turns it into the phase table, the
top-node and top-fixture rankings, and the count and cost of assemblies that
rebuilt byte-identical inputs. `throughput_baseline junit` profiles any kept
junit file the same way, so past broad runs are evidence too. The measured
baseline and its findings are in
`launch_packages/pettripfinder/reports/atlas_throughput_001_baseline_report.md`.

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
