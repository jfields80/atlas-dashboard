# PTF-FINAL-FRESH-MARKET-REGISTRATION-REENGINEERING-001 — final report

**FINAL REENGINEERING ATTEMPT = PASS. A TRUE FIRST registration of Raleigh —
from a state in which Raleigh is absent in every way, through the ordinary
workflow with its already-captured inputs, on the audited shared code —
reaches AUTHORIZATION_READY in 100.0 s under
`COMPOSITE_FRESH_MARKET_DATA_ONLY`, with every one of 41 changed paths in
exactly one narrow bucket, 0 broad regressions requested, 0 broad regressions
run, 0 remote broad jobs, 0 unchanged markets rebuilt, FAST 15/15, package
and candidate reproducible, unexpected deltas 0 / 0 / 0, and the shared code
byte-identical before and after.**

Starting SHA `e3c27772f5480dc34978098239f86b2be994b532` (the final policy-fix
report, `PTF-NEW-MARKET-REGISTRATION-DATA-ONLY-POLICY-001`; also the base
Raleigh was measured against), tree clean. Classifier versions at the start:
`ptf-change-classification/1.0`, `ptf-registration-data-only/1.0` (eleven
checks), `ptf-market-local-isolation-proof/1.0` (five conditions, shadow zones
only). No market authority changed on this branch; Raleigh's frozen branch was
not modified; nothing was deployed or authorized; production is still 13
markets / 902 profiles / 1078 routes on deploy `6aa212a8`.

---

## ROOT CAUSE MODEL

Read from Raleigh's committed forensic reports
(`raleigh_nc_regression_classification.json`,
`raleigh_nc_registration_data_only_evaluation.json`,
`raleigh_nc_final_fresh_city_proof_outcome.json` at `13809c36`), not from the
prompt. Four mechanisms, in the order the classifier hit them:

1. **The registration's own blocker switched the market-local proof off
   before it ran.** `classify_change` refuses every market-local refinement
   when the change set carries a narrowing blocker, and a registration
   always carries `bundle_cache_closure.json`. So the fourteen
   `raleigh_nc_*.py` helpers and the two discovery configs were never PROVEN
   or REJECTED; every row read "market-local narrowing blocked: the change set
   touches bundle_cache_closure.json". The registration proof decides whether
   that blocker is the registration's own — but it runs AFTER the refinement
   and never feeds back.
2. **The registration gate had no bucket for anything but a registration
   role.** Its first check rejected every `.py` as "code or a test
   expectation" and every role-less path as "not a registration path". Even
   with the proof switched on, the five audited conditions would have failed
   every fresh helper on condition 5 (the market IS registered at the head),
   and a shadow zone's write roots do not admit the census, policy package,
   partition or contract a fresh market's helpers legitimately write.
3. **Three inputs had no owning contract.** The proposed-authority document
   the registration CLI reads, the additive co-location ruling in
   `identity_resolutions.json` and the additive row in the OSM-extract
   registry were UNCLASSIFIED or runtime-by-prefix.
4. **The pin was a hand-edit.** The class required a `market_state.json`
   block only a human (or the Charlotte harness's hard-coded `PIN_BLOCK`)
   could state; the fresh-market proof rightly refused to edit a test
   expectation, and the gate reported the required output absent.

The controlled replay had measured a RE-registration whose helpers, configs,
input and ruling were already committed in the base — the one shape the gate
admitted.

## COMPOSITE CHANGE CLASS

`COMPOSITE_FRESH_MARKET_DATA_ONLY` — a whole-set class, CONDITIONAL on
`registration_data_only.evaluate` (proof version 2.0). The gate now
PARTITIONS every changed path into exactly one of five buckets and narrows
only the exact union:

| bucket | proof |
|---|---|
| `MARKET_LOCAL_ACQUISITION` | `market_local_isolation.prove` in REGISTRATION MODE — all five conditions, per file |
| `NEW_MARKET_REGISTRATION_DATA_ONLY` | the eleven registration roles + three typed inputs, each by field |
| `PERMITTED_DERIVED_REGISTRATION_OUTPUT` | the regenerated globals and the narrow companions, exactly as the registration class already proved them |
| `SHARED_BEHAVIOR_CHANGE` | ends the narrowing; the reason is recorded per path |
| `UNKNOWN` | ends the narrowing |

Rule: `SHARED_BEHAVIOR_CHANGE = 0`, `UNKNOWN = 0`, `sum of buckets ==
changed paths`, and every remaining check PASS. A bare re-registration keeps
`NEW_MARKET_REGISTRATION_DATA_ONLY`. Four checks were added in front of the
eleven — `market_local_zone`, `discovery_config`, `registration_input`,
`identity_resolutions` — and `ORIGINAL_CHECKS` is kept as a set so the
contract shows none was weakened. The mandatory-full set is the six classes
it was; the safe-narrow set is unchanged; the composite class is in neither.

    PRODUCTION MODULES CHANGED   5
      scripts/pettripfinder/registration_data_only.py     the partition, the four checks, the class
      scripts/pettripfinder/market_local_isolation.py     registration mode (five gated extensions)
      scripts/pettripfinder/market_local_ownership.py     registration_zone(); transaction imports parsed and fenced
      scripts/pettripfinder/regression_delta.py           the class, its surface, its matrix row, the plan branch
      scripts/pettripfinder/registration_release_lane.py  `register` (row + closure) and `seal --work-order` (pin block)
    ALSO
      launch_packages/pettripfinder/market_local_ownership.json          fresh_market_registration block; the new test module excluded from the scan
      regression_validation_matrix.json, registration_data_only_contract.json   regenerated
      docs/PTF_HARDENED_FACTORY_RUNBOOK.md                               the rule and the corrected workflow
      tests/pettripfinder/test_composite_fresh_market_001.py             56 tests
      scripts/pettripfinder/true_first_registration_replay_001.py        the replay harness (reads a manifest; names no helper)
      markets/reports/raleigh_nc_true_first_registration_inputs_001.json the manifest
      reports/factory_throughput_001_test_inventory.{json,md}            regenerated BEFORE the freeze
    IMPLEMENTATION ENGINEERING WALL TIME   ~2 h 20 min (precheck 20:58Z, freeze 22:20Z)

## COMPLETE PATH ACCOUNTING

Frozen Raleigh diff `e3c27772..b613d72d` (the 42 first-market files):

    TOTAL CHANGED PATHS               42
    MARKET_LOCAL_ACQUISITION PATHS    12   (11 helpers proven on all five conditions + the discovery config)
    REGISTRATION_DATA PATHS           14   (11 roles + the proposed authority, the ruling, the OSM row)
    DERIVED PATHS                     13   (3 regenerated globals + 10 reports)
    SHARED_BEHAVIOR PATHS              3   (rejected for real dependencies, below)
    UNKNOWN PATHS                      0
    sum of buckets == total           YES   (45/45 at the forensic head 13809c36: +3 reports, DERIVED 16)

Replay diff (the corrected workflow, both runs):

    TOTAL CHANGED PATHS               41
    MARKET_LOCAL_ACQUISITION PATHS    11   (10 helpers + the discovery config)
    REGISTRATION_DATA PATHS           15   (11 roles + input + ruling + OSM row + the pin block)
    DERIVED PATHS                     15   (3 globals, 7 captured reports, package, receipt, lane / participation / co-location reports)
    SHARED_BEHAVIOR PATHS              0
    UNKNOWN PATHS                      0
    sum of buckets == total           YES; every `git status` path except the packet (written after the classification) is classified

## MARKET LOCAL PROOF

Registration mode is an EXTENSION of the audited five conditions, admitted
only under a context the composite proof supplies for the ONE market the
change set registers: (1) the zone is `registration_zone()` — the committed
zone, or the `zone_template` instance for the registering market; the registry
(a narrowing blocker) is never edited; (2) imports may add the registry's
`transaction_imports` (release_contracts, launch_participation,
market_authority, publication_guard, bundle_cache, sealed_market_package,
market_package_writer, package_staging, fast_release_lane,
first_party_binding, release_index, registration_release_lane,
regression_delta, market_registration_cli, market_proposed_authority_cli,
build_global_authority, markets.assignment, markets.routes) — `parse_registry`
refuses an assembler, generator, deployer, renderer, reader, policy, routing
or identity module in that list; (3) a write may resolve to a path the same
change set proves as registration data, never a bare root with a dynamic
tail; (4) a mention by the market's own registration DATA document is not a
consumer; (5) the market must be UNREGISTERED at the base and registered at
the head by this change set. Every other verdict is unchanged; a market
registered at the base still fails condition 5; an unresolvable write, a
dynamic import, a non-allow-listed subprocess and a mention by shared code
still fail.

Frozen Raleigh: 11 helpers and the config PASS all five conditions; three are
REJECTED for actual dependencies — `raleigh_nc_candidate_assembly_008.py`
runs the assembler as a subprocess (reachability);
`raleigh_nc_participation_registration_010.py` imports
`assemble_production_site.market_eligibility` and writes an unresolvable
scratch path (imports, writes); `raleigh_nc_release_lane_005.py` writes an
unresolvable path (writes). The generic `register`, `seal` and `packet` steps
replace all three and the readiness-packet helper, and the runbook says so.
MARKET-LOCAL ACQUISITION PROOF = PASS (it proves what is isolated and rejects
what is not, by condition, never by name).

## DISCOVERY CONFIG PROOF

`check_discovery_config`: `discovery/config/<us>.json` loads through
`discovery.market_config.load_market_config` for exactly the new market;
`osm_extracts.json` validates under `discovery.osm_extract.ExtractRegistry`
at base and head, top-level fields identical, every pre-existing row
semantically identical (Raleigh rewrote the file's whitespace — six rows
byte-different, six rows identical by field), exactly one new row,
`markets == [<new>]`, its own `index_path`, https url, extract and index under
`data/`; any other path under `discovery/` widens. Frozen Raleigh and both
replays: PASS.

## REGISTRATION INPUT CONTRACT

`NEW_MARKET_REGISTRATION_INPUT` = role `registration_input`, pattern
`launch_packages/pettripfinder/<us>_proposed_authority_*.json`, status A only,
at most one, no other market's input. Proven by the CLI's own loader
(`market_registration_cli.load_authority`, schema
`ptf-market-proposed-authority/1.0`), `market_id`, counts reconcile
(`pet_friendly_count`, `verified_no_pets_count`, `authority_total`), the
required record fields, every identity in the market's committed census, the
written shard binding (`market_registration_cli.verify` on a worktree; the
seed and exclusion shards read at a git head), the reader and writer
unchanged; the input's digest is recorded. Frozen Raleigh and both replays:
PASS (63 / 23).

## IDENTITY RESOLUTION PROOF

`check_identity_resolutions`: status M only; head and base validate under
`publication_guard.validate_resolutions`; top-level fields identical; the
first N rulings ARE the base rulings, in place; every new ruling belongs to
the new market, is the one permitted type, re-derives its `resolution_hash`,
names exact committed identities (exclusion shard, census, policy package)
with matching canonical URLs, is `DISTINCT` pairwise under
`hotel_exclusions.co_located_distinct`, and a global slug / name scan over
every ruling is clean. Frozen Raleigh (the Brier Creek dual-brand campus) and
both replays: PASS.

## MARKET STATE HANDLING

The pin's NEW-market block is written by the transaction:
`registration_release_lane seal --work-order <ORDER>` derives the block from
the SEALED PACKAGE (`expected_pin_block`), refuses unless the release
contract states the same numbers, adds exactly one block (never moves one)
and sets `reviewed_by` / `last_moved_by` to the order. The proof still
derives its expectation independently — trusted base pin (every other block
byte-identical) + sealed package + the declared delta of one market — and
compares the whole document; `deployment_state.json` is untouched and the
contract test still holds every block to the source. Both replays: "pinned
raleigh-nc: census 90 / pet-friendly 63 / verified-no-pets 23 / corridor
routes 5", check PASS. MARKET STATE PROOF = PASS.

## REGISTRATION PROOF

The eleven checks are unchanged in code and in the committed contract. Both
replays: all fifteen PASS — the participation reissue carries the chain
forward whole with `decided_by` the order and the founder-authorized set
unchanged at thirteen; the contract's behaviour blocks equal every base
contract's; the closure gains exactly two inputs and one note; the derived
globals regenerate byte-identical; the package is sealed from the exact head
bytes and re-seals to its digest; the receipt is 15/15 PASS, 0 UNKNOWN, 0
FAILED; nothing protected moved.

## EXPECTED RELEASE PROOF

EXPECTED = trusted live parent (13 markets / 902 profiles, deploy
`6aa212a8`) + the sealed Raleigh package; ACTUAL = every registered market's
committed authority with Raleigh participating; compared as complete sets of
markets, participation, profile identities, record digests, routes and
ownership. Both replays: 14 markets / 965 profiles / 1101 routes, unexpected
0 / 0 / 0, `release_index.compare` clean.

## NEGATIVE TESTS

`tests/pettripfinder/test_composite_fresh_market_001.py` — 56 tests, all
green (the pre-audit smoke over the eleven modules that name a changed module:
638 passed, 8 skipped, 2 failed — both the parent audit's own pre-existing
nodes). Coverage of the order's matrix:

    1, 28   the frozen Raleigh partition; the two committed replay receipts (narrow when every proof passes)
    2       helper imports the assembler -> imports FAIL; a transaction import passes ONLY in registration mode
    3       shared runtime reverse-imports the helper -> reachability FAIL
    4       write to another market -> writes FAIL; a proven registration write passes; a bare root + dynamic tail never
    5, 6    changed / removed / second OSM row -> broad; one additive row -> narrow
    7       a discovery module or provider_terms in the set -> broad
    8       an input schema change is refused by the CLI's own loader; the reader's own change -> broad
    9       an input for another market, or another market's input in the set -> fail
    10-12   the frozen ruling is narrow; an edited existing ruling, a foreign market, a tampered hash,
            a duplicate URL, a stranger identity, a slug collision -> fail
    13-16   the existing 63-test registration battery is unchanged and green; case 16 (build module) added here
    17-19   assembler change -> SHARED; classifier / proof / conftest / registry -> foreign blocker, no proof runs
    20      one unknown path -> UNKNOWN = 1, broad
    21      a required output missing from the accounting -> fail
    22-27   the existing battery (profile / route swap at equal count, stale / wrong receipt, package mismatch, pin wrong)
    +       a market registered at the base fails condition 5; another market's helper is SHARED; a second
            market's shard is UNKNOWN; a bare re-registration keeps the old class; a registry that admits
            the assembler is malformed; a registration context without a market fails every condition

## RALEIGH FULL-DIFF FIXTURE

The frozen branch is read through git (`needs_raleigh` skips if absent):
42/42 and 45/45 accounted, 0 UNKNOWN, the three rejections asserted by name
and by condition, every accepted helper asserted to have passed all five
conditions in registration mode, the three typed inputs field-validated at
that head, participation and closure passing their existing proof, and the
verdict NOT narrow — because the pin block was never stated and three helpers
carry real dependencies. Raleigh's frozen change set selects the composite
class only when every proof succeeds, and it does not. Raleigh was not
modified.

## FOCUSED PERFORMANCE

`raleigh_nc_true_first_registration_replay_001_focused_benchmark.json` (code
`43738ad0`, the final implementation before the receipt and report commits;
shared python digest equal before and after):

    acquisition install + offline build steps              1.5 s   policy package, proposed authority, partition and
                                                                   ruling regenerated BYTE-IDENTICAL to the frozen branch
    shard + globals + contract + register                  4.6 s
    registration release lane (seal x2, gate, FAST A-O,
      compose x2, pin block)                              78.7 s
    Regression V2 classify                                18.0 s   (the composite proof 17.1 s: partition, 11 isolation
                                                                   proofs, 3 field checks, expected release)
    readiness packet                                       0.4 s
    REGISTRATION -> AUTHORIZATION_READY                  101.8 s   (ceiling 300)

## FINAL MIGRATION AUDIT

Code frozen at `091242a4`, tree clean, focused tests green, nothing edited
during the run.

    RUN                 python scripts/pettripfinder/regression_lanes.py run --lane full_regression
                        18392 collected, 17971 passed, 254 skipped, 167 failed, 6241.5 s (1:44:01)
    vs f75aa95          160 PRE_EXISTING, 0 EPOCH, 0 FLAKE, 7 TRUE_NEW by node id --
                        all 7 in the parent audit's own TRUE_NEW set of 8 (6 in the parent's broad run,
                        the closure-artifact test proved failing at 42cb937f before the parent's audit)
    vs the parent run   failure-set IDENTITY against PTF-NEW-MARKET-REGISTRATION-DATA-ONLY-POLICY-001's
    (fb499741, 168)     migration-audit-001 junit: 167 failing here, EVERY ONE in the parent's 168;
                        failing here and not there: 0
    PARENT FAILURES NOW PASSING   1 -- test_factory_throughput_001::test_the_committed_inventory_reproduces_from_the_suite
                        (the inventory was regenerated BEFORE the freeze, so what the parent closed by node id
                        after its run passes here on the first run)
    MIGRATION_AUDIT_TRUE_NEW      0
    POST-AUDIT CODE CHANGE        NO -- git diff 091242a4..HEAD is two receipts, one audit report and this report

`AUDITED_SHA = 091242a461eacafc1eb79623c6e0f5ffbac7fb22`. Report:
`launch_packages/pettripfinder/reports/final_registration_reengineering_001_migration_audit_report.json`.

## TRUE FIRST REGISTRATION REPLAY

`raleigh_nc_true_first_registration_replay_001.json`, code `091242a4`
(the AUDITED SHA), inputs from the frozen Raleigh branch `b613d72d` via the
manifest. A detached worktree of the audited code in which Raleigh is absent
in every way — no helper, no discovery config, no OSM row, no proposed
authority, no ruling, no shard, no census, no partition, no policy package, no
contract, no participation row, no closure input, no package, no receipt, no
pin block (the harness refuses to start otherwise). Then, with no network:
the acquisition-phase deliverable installed byte-for-byte (10 helpers, 7
captured reports, the census, the market document, the discovery config and
the OSM registry), the offline build steps EXECUTED (policy package + proposed
authority, partition, co-location ruling — all four BYTE-IDENTICAL to the
frozen branch), and the ordinary registration transaction: shard, globals,
the market-local contract helper, `register`, `seal --work-order`, `classify`,
`packet`.

    SHARED AUDITED CODE UNCHANGED         YES (1993 frozen files; python digest equal before and after)
    COMPLETE FIRST-MARKET DIFF ACCOUNTED  41/41   (11 market-local / 15 registration data / 15 derived / 0 shared / 0 unknown)
    CHANGE CLASS                          COMPOSITE_FRESH_MARKET_DATA_ONLY  (change classes: GENERATED_REPORT_ONLY,
                                          MARKET_DATA_PACKAGE, COMPOSITE_FRESH_MARKET_DATA_ONLY)
    LOCAL BROAD REQUESTED / RUN           0 / 0
    REMOTE BROAD REQUIRED                 0  (ci_validation.required_shards: scope NONE, dispatch NONE)
    UNCHANGED MARKETS REBUILT             0
    FAST                                  15/15 PASS, 0 UNKNOWN, 0 FAILED
    PACKAGE / CANDIDATE REPRODUCIBLE      YES / YES
    IDENTITY / ROUTE COLLISIONS           clean
    EXPECTED == ACTUAL                    14 markets / 965 profiles / 1101 routes, complete sets
    UNEXPECTED DELTAS                     0 / 0 / 0
    REGISTRATION -> AUTHORIZATION_READY   100.0 s  (shard 0.2, globals 1.5, contract 1.3, register 1.4, seal + FAST + pin 79.6,
                                          classify 15.5, packet 0.4)
    ORPHANED JOBS                         0;  SHARED / TEST REPAIR  none;  receipt machine-readable, 30/30 criteria true
    TRUE_FIRST_REGISTRATION_REPLAY        PASS

## FINAL DECISION

The true fresh-market path exists and is proven: 0 registration broad
regressions, 0 remote broad jobs, 0 unchanged-market rebuilds, 100 s from
registration to AUTHORIZATION_READY, on audited code, with every changed path
accounted for and every proof passing. FACTORY STATUS =
CONTINUE_WITH_ONE_FINAL_FRESH_CITY_LIVE_PROOF. The next city was not started
here; its benchmark stays ZERO -> VERIFIED LIVE <= 3h30m with registration /
test closure <= 10 min (target <= 5), 0 registration broad runs, 0 unchanged
market rebuilds, no shared code or test repairs — and it must write no
participation helper that imports the assembler, no helper with an
unresolvable write target, and no test-expectation edit; the runbook's
corrected workflow is the path.

## ARTIFACTS

    migration_audit_report        launch_packages/pettripfinder/reports/final_registration_reengineering_001_migration_audit_report.json
    focused_benchmark_receipt     launch_packages/pettripfinder/markets/reports/raleigh_nc_true_first_registration_replay_001_focused_benchmark.json
    true_first_replay_receipt     launch_packages/pettripfinder/markets/reports/raleigh_nc_true_first_registration_replay_001.json
    replay_inputs_manifest        launch_packages/pettripfinder/markets/reports/raleigh_nc_true_first_registration_inputs_001.json
    contract                      launch_packages/pettripfinder/registration_data_only_contract.json (46 field rows)
    matrix                        launch_packages/pettripfinder/regression_validation_matrix.json (16 rows)
    runbook                       docs/PTF_HARDENED_FACTORY_RUNBOOK.md  (COMPOSITE_FRESH_MARKET_DATA_ONLY)

## FINAL ANSWERS

     1. COMPOSITE FRESH-MARKET CLASS ............... COMPOSITE_FRESH_MARKET_DATA_ONLY
     2. PRODUCTION MODULES CHANGED ................. 5
     3. TOTAL FILES CHANGED ........................ 18 (git diff --stat e3c27772..HEAD)
     4. FULL RALEIGH CHANGED PATHS ACCOUNTED FOR ... 42/42 (and 45/45 at the forensic head)
     5. UNKNOWN PATHS .............................. 0
     6. MARKET-LOCAL ACQUISITION PROOF ............. PASS
     7. DISCOVERY CONFIG PROOF ..................... PASS
     8. REGISTRATION INPUT PROOF ................... PASS
     9. IDENTITY RESOLUTION PROOF .................. PASS
    10. MARKET STATE PROOF ......................... PASS
    11. EXISTING REGISTRATION PROOF ................ PASS (eleven checks unchanged)
    12. INDEPENDENT EXPECTED RELEASE ............... PASS
    13. NEGATIVE TESTS ............................. 56/56 PASS (all 28 cases covered; existing 63-test battery green)
    14. FOCUSED FIRST-REGISTRATION TIME ............ 101.8 s (1m42s), ceiling 300 s
    15. MIGRATION AUDITS RUN ....................... 1
    16. MIGRATION AUDIT TRUE_NEW ................... 0
    17. POST-AUDIT CODE CHANGE REQUIRED ............ NO
    18. AUDITED SHA ................................ 091242a461eacafc1eb79623c6e0f5ffbac7fb22
    19. TRUE-FIRST-REGISTRATION REPLAY CLASS ....... COMPOSITE_FRESH_MARKET_DATA_ONLY
    20. REPLAY LOCAL BROAD REQUESTED ............... 0
    21. REPLAY LOCAL BROAD RUN ..................... 0
    22. REPLAY REMOTE BROAD ........................ 0
    23. REPLAY UNCHANGED MARKETS REBUILT ........... 0
    24. REPLAY FAST ................................ 15/15 PASS, 0 UNKNOWN, 0 FAILED
    25. REPLAY PACKAGE REPRODUCIBLE ................ YES
    26. REPLAY CANDIDATE REPRODUCIBLE .............. YES
    27. REPLAY UNEXPECTED DELTAS ................... 0 markets / 0 profiles / 0 routes
    28. REPLAY REGISTRATION_TO_AUTH_READY .......... 100.0 s (1m40s), ceiling 300 s
    29. SHARED CODE CHANGED DURING REPLAY .......... NO
    30. FINAL TRUE-FIRST REPLAY .................... PASS
    31. FINAL FACTORY STATUS ....................... CONTINUE_WITH_ONE_FINAL_FRESH_CITY_LIVE_PROOF
    32. FINAL FRESH CITY LIVE PROOF ALLOWED ........ YES (not started by this order)
    33. origin == HEAD ............................. YES (see the closing commit)
    34. tree clean ................................. YES

FINAL REENGINEERING ATTEMPT = PASS
TRUE FIRST MARKET REGISTRATION REQUIRES BROAD = NO
TRUE FIRST MARKET REGISTRATION TIME = 100.0 s (1 minute 40 seconds) registration -> AUTHORIZATION_READY
FRESH CITY LIVE PROOF ALLOWED = YES
FACTORY STATUS = CONTINUE_WITH_ONE_FINAL_FRESH_CITY_LIVE_PROOF
