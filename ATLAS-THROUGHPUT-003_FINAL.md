# ATLAS-THROUGHPUT-003 — FINAL REPORT

Critical fast release lane + sealed market package writer. Worktree `C:\Atlas-Throughput-V1`, branch
`worker/atlas-throughput-001`, continued from the pushed 002 head `e982aad`. Engineering only: production
authority changed = 0, nothing promoted, nothing deployed, no paid provider call, no browser research.

## PRECHECK

- Worktree `C:\Atlas-Throughput-V1`, branch `worker/atlas-throughput-001`, HEAD at start `e982aad42549141223fb65a92b658be14b9d7071` == `origin/worker/atlas-throughput-001`, tree clean.
- 001 closure `failure_closures/atlas-throughput-001-1.json`: TRUE_NEW 0. 002 migration audit: PRE_EXISTING 160, TRUE_NEW 1 → closed by node id (`failure_closures/atlas-throughput-002-1.json`) → 0.
- Read: `atlas_throughput_001_safety_invariants.md` (H1–H13, the minimum covering set, §E gaps), `atlas_throughput_001_release_model.md` (29 release-state rows, the duplicated-state list, the hash of the release), `atlas_throughput_002_003_input_packet.md`, the ownership registry, Regression V2, the isolation proof, the session cache, and the owning contracts — actual files, not neighbouring JSON:
  - identity: `scripts/pettripfinder/contracts/identity_key.py` (`ptf_identity_key`, `is_canonical_key`), `contracts/census.py` (`validate`, `identity_keys`, `CensusRow`), `hotel_exclusions.py` (`address_key`, `brand_scoped_property_identity`, `co_located_distinct`, `validate`, `record_hash`, `approval_hash`), `publication_guard.py` (`identity_resolutions.json`, `assert_publishable`)
  - policy: `contracts/policy_schema.py` (`validate_record`, `validate_facts`, `_check_pet_fee`, `_check_other_charges`, `KNOWN_FACT_FIELDS`, `_SILENCE_SENTINELS`), `contracts/enums.py` (`FEE_BASES`, `FEE_SCOPES`, `CHARGE_*`, `FIRST_PARTY_GRADES`, `PUBLICATION_GRADE_EVIDENCE`, `TERMINAL_STATES`), `contracts/service_animal.py`, `brightdata/policy_reading.py` (`parse`, `_is_amenity_label_only`)
  - evidence/provenance: `contracts/evidence.py` (`PUBLICATION_GRADE_REQUIRED`, `validate`, `validate_entry`, `publication_blockers`, `unevidenced_facts`, `quote_is_contiguous`, `SOURCE_GRADE_ALIASES`), `acquisition/paid_attempt_ledger.py` (`attempt_id`), `acquisition/firecrawl_capture.py`
  - geography/routes: `markets/contract.py` (`parse_market`, `load_markets`, `validate_markets`, `slugify`), `markets/routes.py` (`hotel_route`, `corridor_route`, `market_route`, `build_route_table`), `markets/assignment.py` (`assign_hotels`), `identity_routing.py` (`validate_authority`, `validate_record`, `NEVER_OFFICIAL_DOMAINS`, `registrable_domain`)
  - partition/pins: `contracts/partition.py` (`validate`, `reconcile`, `normalise_blocker`), `build_market_manifest.py` (`_PARTITION_FILES`, `build_package`), `assemble_production_site.py` (`_partition_path`, `market_eligibility`, `file_hashes`, `bundle_digest`), `tests/pettripfinder/market_state.py` + pins
  - promotion/assembly/release: `market_authority.py` (`build_routing_shard`, `build_exclusions_shard`, `assemble_*`, `build_manifest`, `SEED_COLUMNS`), `site_data.py` (`read_production_rows`, `load_published_hotel_policy_facts` keyed by `key`, `verified_public_hotels`), `assemble_netlify_bundle.py` (`assemble`, `_assemble_uncached`, `validate_output_path`, the contract keys it reads), `release_contracts.py` (`derive_authority`, `contract_disagreements`, `load_contract`), `launch_participation.py`, `global_deployment.py`
  - rollback/deployment: `deployment_authorization.py` (`verify_target`, `verify_bundle_directory`, `verify_record`, `_shape_problems`), `deploy/netlify/deployment_records/*`, `global_deployment_manifest.json`, `tests/pettripfinder/pins/deployment_state.json`
  - shadow inputs: Nashville `4f3dd7b` (proposed market + census, clean authority, attended/static/Firecrawl captures, routing, founder packet, evidence audit) and Toledo `d335c50`, read through `git show`, never checked out.

## 002 INPUTS

The §E gaps of 001, unchanged by 002 and taken as the design input: H2 no first-party binding gate; H9
determinism skipped by default; H7 route preservation Columbus-only; H12 rollback market set unchecked; H13
paid call sites bypass the ledgers; H3 `validate_record` not a build gate; H1 name-only join. Plus 002's two
findings: root-level shadow artifacts broaden a market order, and shared registries stay shared. 002's
mechanisms reused as-is: the ownership registry (extended), Regression V2 (extended), the session cache
(`cold()` is what the determinism gate uses), the profiler (the audit).

## CRITICAL HAZARD MAP

| hazard | 003 rule(s) | fixture that proves it |
|---|---|---|
| H1 property identity | writer (`MISSING_IDENTITY`, `DUPLICATE_IDENTITY`, `IDENTITY_NOT_CANONICAL`, census contract), rule B, rule G keyed by `ptf_identity_key(published name)`; explicit relations (`CO_LOCATED_DISTINCT`, `REBRAND_OF`, `SUPERSEDES`) | 15 live records with bare-brand identity keys; St. Louis `tru` / `tru by hilton st louis downtown` on one premises |
| H2 first-party binding | rule C: property identity, source class, URL, capture hash, timestamp, operative quote, parsed facts, authority status; competitor = LEAD ONLY | 5 live Dayton records refused; wrong-property, same-brand-wrong-code, fee-only, service-animal-only, amenity chip, structured no-pets fixtures |
| H3 policy contract validity | writer + rule D run `validate_record`, `evidence.validate`, `publication_blockers`, fee/deposit conflation on every record; rule J renders the changed market | Pittsburgh 15 uncited `species` facts; Indianapolis 41 hash-less entries |
| H4 duplicate / same premises | rule B: `co_located_distinct` or a declared relation; address-less rows are not collisions | Marriott `indsw` / IHG `indsw` admitted; Galt House / Rivue Tower admitted by relation; bare-brand duplicate refused |
| H5 market / partition | rules E, F: routes bind census identities on first-party domains; partition validate + reconcile + state agreement | Louisville partition 69/33 rows apart; Cleveland 5 dangling routing records; case 7, 20 |
| H6 membership preservation | rule H over the composed index (unchanged markets are the SAME live entries, never re-derived) | case 11 |
| H7 route preservation | rules H, I (routes vs intent, corridor-minimum consequences) | two corridor routes silently lost by a withdrawal |
| H8 intended delta | rule I + `removal_authority` required to seal | cases 12, 13 |
| H9 determinism | rule K: two COLD builds, digests equal, `BUILD_EXECUTED` ×2 / `REUSE_HIT` 0 | cases 15, 16, "two hits never pass" |
| H10 artifact integrity | rules A, L: seal re-derives, evidence index, one artifact one identity, artifact bytes + quote contiguity, dependency digests | cases 18, 19 |
| H11 authorization integrity | invariant + interface only: `PACKAGE_DIGEST`, `PARENT_RELEASE`, `RECEIPT_DIGEST`; consumed by 004/005 | — |
| H12 rollback / live set | rule N + `current_verified_live` (record ↔ manifest ↔ pin ↔ authorization; rollback target = previous DEPLOYED record with its own market set) | case 17; synthetic broken chain |
| H13 paid coordination | rule O: reservation key (`paid_attempt_ledger.attempt_id`) + envelope hash per paid capture; ledger cross-check; UNKNOWN ⇒ NOT ELIGIBLE | cases 21, 22; uncoordinated call sites reported |

## SEALED PACKAGE CONTRACT

`scripts/pettripfinder/sealed_market_package.py`, schema `ptf-sealed-market-package/1.0`; report
`atlas_throughput_003_package_contract.md/.json`. Every field the order names is a body field
(PACKAGE_SCHEMA_VERSION, MARKET_ID, CENSUS, IDENTITY RECORDS, GEOGRAPHY/CORRIDORS, OFFICIAL ROUTES, PET-FRIENDLY
and VERIFIED NO-PETS records, EVIDENCE REFERENCES + HASHES, UNRESOLVED ROWS, FOUNDER HOLDS, INTENDED DELTA,
PARENT LIVE STATE, DEPENDENCY INPUT DIGESTS, BUILDER/CONTRACT VERSIONS, COVERAGE SCORECARD, VALIDATION STATE)
and the seal (PACKAGE_ID / DIGEST, `sealed_at` outside the digest; CREATED_FROM_SOURCE_SHA; EXECUTION_ZONE).
Digest = sha256 of canonical JSON of the body; id = `pkg-<market>-<digest16>`; `write_sealed` never overwrites;
a correction is a new id (pilot P1 `pkg-dayton-oh-97f504ad2794e767` → P2 `pkg-dayton-oh-813f7f9f089b89c7`).
No duplicate authority system: every section is the owning contract's own document.

## TYPED WRITER

`scripts/pettripfinder/market_package_writer.py` — `PackageInputs` → `build_sealed_package` → sealed document,
or `PackageWriteError` carrying EVERY issue. Rejected before serialization (with the code): invalid fee
enum/currency/basis (`POLICY_BAD_ENUM`, `POLICY_MISSING_CURRENCY`, `POLICY_NOT_INT_CENTS`), pet-count/weight
structures (`POLICY_BAD_COUNT`, `POLICY_*`), fee/deposit conflation (`FEE_DEPOSIT_CONFLATION`), missing identity
(`MISSING_IDENTITY`, `IDENTITY_NOT_CANONICAL`, `DUPLICATE_IDENTITY`), invalid policy status
(`INVALID_POLICY_STATUS`, `CONFLICTING_STATUS`), missing evidence binding (`MISSING_EVIDENCE_BINDING`,
`EVIDENCE_MISSING_REQUIRED`, `PUBLICATION_BLOCKED`), policy/evidence identity mismatch
(`POLICY_EVIDENCE_IDENTITY_MISMATCH`), invalid market assignment (`INVALID_MARKET_ASSIGNMENT`), invalid route
(`INVALID_ROUTE`, `ROUTING_CONTRACT`, `ROUTE_IDENTITY_NOT_IN_CENSUS`), orphan partition (`ORPHAN_PARTITION`,
`UNRESOLVED_PROMOTED_CLEAN`), unsupported enums (`CENSUS_BAD_ENUM`, `EXCLUSION_CONTRACT`), malformed
unknown/N-A (`POLICY_SENTINEL_FOR_SILENCE`, `SENTINEL_VALUE`), plus same premises and the display join.
`proposed_authority(package)` derives every authority document (registry entry, census, policy package,
shards, seed CSV, partition) from ONE proposed state; `inputs_from_committed_market` reads a registered
market read-only. Measured over the committed authority of this tree: only Dayton seals as-is (0.13 s); every
other live market is refused on legacy facts (see PILOT MARKET).

## SHADOW OWNERSHIP

`market_local_ownership.json` zone template now owns `markets/packages/<id>/`, `markets/staging/<id>/`,
`markets/receipts/<id>/` (owned paths and write roots); Regression V2 classifies them `MARKET_DATA_PACKAGE`
(safe-narrow: a package is the lane's input, never a build's). The classifier around root-level artifacts and
shared registries is unchanged. No active production file was moved; the pilot layout was proven with frozen
copies (Dayton), and the Dayton pilot package + receipt are committed under the market's own directories. LOCAL
DATA IS LOCAL BY CONSTRUCTION.

## FIRST-PARTY EVIDENCE GATE

`scripts/pettripfinder/first_party_binding.py`: for every clean pet-friendly record and every VERIFIED_NO_PETS
exclusion, eight checks — PROPERTY IDENTITY (record ↔ census ↔ references ↔ the page's brand-scoped property
code), SOURCE CLASS (`FIRST_PARTY_GRADES`; anything else is LEAD ONLY), SOURCE URL (never a
`NEVER_OFFICIAL_DOMAINS` host; own domain or agreeing brand family), CAPTURE HASH (page hash bound to the identity
in the package references), TIMESTAMP, OPERATIVE QUOTE (the owning reader `policy_reading.parse` judges the
words; the amenity-chip rule is judged over the record's same-page quotes; species acceptance via the reader's
own species readings; a bare machine key/value is `STRUCTURED_NO_PETS_INSUFFICIENT`), PARSED FACTS
(`unevidenced_facts` + no cited quote contradicts its fact), AUTHORITY STATUS (publishable state + a review).
Explicitly tested: wrong hotel page → WRONG_PROPERTY; same brand wrong property → WRONG_PROPERTY; fee present,
acceptance absent → FEE_ONLY; service animals only → SERVICE_ANIMAL_ONLY; amenity chip only → AMENITY_CHIP_ONLY
(and the same label beside the page's fee sentence is a policy); structured no-pets → insufficient; valid
operative policy → ELIGIBLE; valid explicit refusal → ELIGIBLE. On the live Dayton authority it refuses 5 of 78
records.

## GLOBAL INDEX

`scripts/pettripfinder/release_index.py`. CURRENT_VERIFIED_LIVE = the newest DEPLOYED record
(`ptf-deploy-cincinnati-004-6a9d33f5…`), the global manifest, the deployment-state pin and the authorization,
which must agree (they do: 10 markets, 786 profiles, 945 routes, rollback `6a9ca921` with its own record of 9
markets); the committed authority of every participating market is indexed through the SAME helpers the
assembler publishes from (`build_package`, `hotel_route`, `corridor_route`, `assign_hotels`) and must reproduce
the record's profile counts (it does). Per profile: MARKET_ID, PROPERTY_ID (canonical identity), the declared
key, display name, ROUTE, premises key, official URL, BRAND family + PROPERTY CODE, record digest; per market:
participation, corridor and market routes. `compare` detects missing live market, missing unrelated profile /
route, cross-market identity collision, duplicate route, ownership movement, unexpected deletion / addition /
update, unexpected membership change, intent not realised, delta mismatch (profiles, markets, no-pets).
Benchmark: 11 markets / 786 profiles 0.10 s; 100 markets / 7,778 profiles 0.81 s; 200 / 15,638 1.54 s. Live
index derivation 4.4 s. No render anywhere.

## DELTA/REMOVAL GUARD

Intended delta fields: MARKET, ADD/UPDATE/REMOVE PROPERTY IDS, ADD/CHANGE/REMOVE ROUTES, EXPECTED PROFILE DELTA,
EXPECTED MARKET COUNT DELTA, EXPECTED PARTICIPATION DELTA (+ optional no-pets delta), `removal_authority`
(required to seal any removal). Rule I compares the actual proposed state to the intent; any difference fails.
The historic failure mode: `test_case_17_the_stale_pittsburgh_like_package_cannot_remove_newer_indianapolis_like_state`
— a Dayton package whose parent live state is one deploy behind with Indianapolis at 67 fails rule N (stale
parent) in 0.01 s; rule H passes because the proposed release carries Indianapolis's CURRENT 82 profiles from
the live index, never the package's view; rule J stays UNKNOWN — nothing was rebuilt to find out.

## DETERMINISM

Rule K: the changed market is built twice, COLD (`assembly_session_cache.cold()`), into isolated temporary
trees; the receipt records INPUT DIGEST (`staged_input_digest` over every staged file), OUTPUT DIGEST A, OUTPUT
DIGEST B (`bundle_digest`, the deployer's formula), RESULT. The cache events must show `BUILD_EXECUTED` for both
bundles and no `REUSE_HIT`, so two cache hits can never pass (tested). P2: input `sha256:a6ba205ac580b5ca…`,
A = B = `6340911b0605e4e2…`, BYTE_IDENTICAL, 4 cold builds, 0 hits, 31.9 s. A monkeypatched nondeterministic
build FAILS (case 16). Not skippable: `determinism=False` leaves K UNKNOWN and the package NOT ELIGIBLE.

## VALIDATION RECEIPT

`atlas_throughput_003_validation_receipt_example.json` (the committed P2 receipt
`markets/receipts/dayton-oh/pkg-dayton-oh-813f7f9f089b89c7-324148f81b55bc50.json`): PACKAGE_ID,
PACKAGE_DIGEST, PARENT_RELEASE (live deploy id, rollback target, source commit, live index digest), CHANGE_CLASS,
DEPENDENCY_DIGEST, VALIDATION_POLICY_VERSION, RULES_EXECUTED, RESULTS (per rule: status, seconds, detail,
problems), TIMESTAMPS, ARTIFACT_DIGESTS (bundle A/B, staged input, staged contract), GLOBAL_INDEX_DIGEST,
INTENDED_DELTA_DIGEST, DETERMINISM_RESULT, FIRST_PARTY_BINDING_RESULT, COLLISION_RESULT, REMOVAL_RESULT,
LEGACY_EXCEPTIONS, ENVIRONMENT (python, platform, builder, contract versions, source sha, peak memory),
EXPIRY_REVOCATION_CONDITIONS (valid while the live deploy and index digest are unchanged, no artifact revoked,
evidence younger than 365 days — earliest expiry 2027-08-10, contracts at the recorded versions, package bytes
unchanged), UNKNOWN_RULES, FAILED_RULES, FAST_DATA_ONLY_RELEASE_ELIGIBLE, FULL_REGRESSION_REQUIRED_BY_LANE,
FAST_PATH_PRODUCTION_ACTIVATION, PRODUCTION_ACTIVATION_ALLOWED, PERFORMANCE, RECEIPT_DIGEST. UNKNOWN ⇒ NOT
ELIGIBLE (proved: `build=False` leaves the otherwise-clean P2 NOT ELIGIBLE).

## REGRESSION V2

Extended, not duplicated (`atlas_throughput_003_regression_v2_matrix.md/.json`; committed matrix regenerated,
14 rows, mandatory-full set unchanged). New classes `MARKET_DATA_PACKAGE` (safe-narrow) and
`MARKET_AUTHORITY_DATA_ONLY` (assembly required, full CONDITIONAL); every row carries a `release_surface`:
MARKET_LOCAL_TOOLING, MARKET_DATA_PACKAGE, MARKET_AUTHORITY_DATA_ONLY, SHARED_SCHEMA_CHANGE,
SHARED_RUNTIME_CHANGE, ASSEMBLER_CHANGE, DEPLOYMENT_CHANGE, CLASSIFIER_TEST_INFRA_CHANGE, UNKNOWN_MIXED,
NARROW_NON_RELEASE. A change set is data-only ONLY when every authority row is one market's own file (or a
derived global whose diff names only that market), nothing else but reports/docs/packages is present, nothing
is UNCLASSIFIED and no blocker is present. Then `FAST_DATA_ONLY_RELEASE_REQUIRED = YES`, and
`FULL_REGRESSION_REQUIRED = NO` only with a sealed package covering the head bytes, a committed ELIGIBLE receipt
with no UNKNOWN rule (rule N has verified the parent/live state), and activation. The six 003 modules and the
activation file are `NARROWING_BLOCKERS`. This order's own change set classifies CLASSIFIER_TEST_INFRA_CHANGE +
UNKNOWN_MIXED → broad (the audit).

## ADVERSARIAL TESTS

`tests/pettripfinder/test_atlas_throughput_003.py`: 69 passed, 0 failed (`atlas_throughput_003_adversarial_results.md`).
The 25-case matrix: 1 PASS (non-build rules + the slow two-cold-build test + the committed receipt), 2 FAIL
WRONG_PROPERTY, 3 FAIL LEAD_ONLY, 4 FAIL FEE_ONLY, 5 FAIL SERVICE_ANIMAL_ONLY, 6 FAIL POLICY_BAD_ENUM, 7 FAIL
ORPHAN_PARTITION, 8 FAIL DUPLICATE_IDENTITY, 9 PASS, 10 FAIL collision + ownership movement, 11 FAIL missing
market/profile/route, 12 PASS with authority / refused without, 13 FAIL unintended route change, 14 FAIL invalid
assignment / duplicate route, 15 PASS byte-identical cold, 16 FAIL nondeterministic, 17 NOT ELIGIBLE stale
parent, 18 FAIL tampered digest, 19 FAIL hash mismatch, 20 FAIL unresolved promoted, 21 FAIL no reservation,
22 PASS reserved (no provider call), 23 not data-only, 24 not data-only, 25 not data-only. Every mutation is of
the real Dayton authority or the real live index.

## PILOT MARKET

`scripts/pettripfinder/atlas_throughput_003_pilot.py`; `atlas_throughput_003_fast_lane_report.md/.json`.
Frozen, non-production copies; no market edited or promoted.

- P1 dayton-oh frozen copy, zero delta: seals in 0.06 s; lane NOT ELIGIBLE on rule C only (5 records:
  3 amenity chips "Pets Allowed"/"Pets are welcome" as the record's only evidence, 1 fee sentence cited as the
  acceptance, 1 `"petsAllowed": false`), every other rule PASS, 73.6 s with builds.
- P2 dayton-oh withdrawal (P1 minus those five, every consequence declared incl. two corridor routes the
  assignment minimum retires): FAST_DATA_ONLY_RELEASE_ELIGIBLE = **YES** in **60.9 s** — package committed at
  `markets/packages/dayton-oh/pkg-dayton-oh-813f7f9f089b89c7.json`, receipt at
  `markets/receipts/dayton-oh/pkg-dayton-oh-813f7f9f089b89c7-324148f81b55bc50.json`.
- P3 nashville-tn shadow (branch 4f3dd7b, consumed through git, branch untouched): the writer REFUSES the
  package — 84 of 99 clean rows carry no page hash (attended captures), 8 clean rows use an alias key the
  proposed census does not carry as primary, no reviewer on any record, 2 `fee_cap` facts without
  `qualifier_stated`, 2 census rows without a city. Found in 0.03 s.
- P4 toledo-oh frozen (launch commit d335c50): REFUSED under this tree's contracts — the census is not
  contract-shaped (216 issues), 28 partition rows lack `next_action`, 7 evidence entries declare
  `PT1_PROPERTY`, which the evidence contract does not know.
- Legacy facts on the other live markets (all read-only): Cleveland 5 dangling routing records; Pittsburgh 15
  uncited `species` facts + 1 unproven same-premises pair; Indianapolis 41 hash-less entries, 13 premises
  pairs, census/partition 21/22 apart; Cincinnati 33 uncited facts + 4 pairs; Louisville 66 published records
  outside PUBLISHED_PET_FRIENDLY + a partition 69/33 apart; St. Louis 119 published records in a
  pre-promotion partition + 6 bare-brand duplicates; Milwaukee 100 + 34; Grand Rapids 10 dangling routes;
  15 live records with bare-brand identity keys across 4 markets. None changed here.

## PERFORMANCE

`atlas_throughput_003_performance.md/.json` — P2: PACKAGE WRITE 0.07 s; PACKAGE VALIDATION (A–F, L, M, O)
0.24 s; GLOBAL INDEX 4.9 s (live index 4.4 s + compare 0.07 s); CHANGED MARKET BUILD 28.7 s (real per-market
assembler, cold, 334 HTML files); DETERMINISM 31.9 s; TOTAL FAST LANE 60.9 s (65.7 s with the live index);
PEAK MEMORY 104 MB; 15 rules; 69 tests in the targeted module (82 s including the slow test); ASSEMBLY
EXECUTIONS 4 cold (generator + bundle ×2), 0 reuse hits. Target P50 ≤ 5 min and proof ≤ 15 min: met by
a factor of five with every mandatory hazard executed (nothing omitted: J and K are real builds, C evaluates
every record, G/H/I/N read the real live release).

## OLD VS NEW SAFETY

`atlas_throughput_003_safety_matrix.md/.json` — per hazard: cheaper everywhere (seconds vs 7,955 s / 3,815 s);
EQUIVALENT for H3 (same contracts, now a gate), H6, H11 (interface only); SUPERIOR on named fixtures for H1,
H2, H4, H5, H7, H8, H9, H10, H12; H13 enforced at the package boundary with the uncoordinated call sites
(`firecrawl_capture.fetch`, `brightdata/browser_capture`, `unlocker_capture`, `spider_capture`,
`direct_http_capture`, `discovery/google_places`) reported for follow-up. BROAD STILL REQUIRED? NO for a
data-only package; YES for every shared runtime / schema / assembler / deployment / classifier change, because
rules J and K trust the assembler the last broad run proved.

## MIGRATION AUDIT

Run: `data/regression/atlas-throughput-003-audit` on commit c79ed9d, clean tree, launched 2026-09-08T01:05:10-04:00 after the
heavy-lane check found no competing python job (WAIT_FOR_HEAVY_LANE not triggered). Every test under `tests/`
-- demo-media included -- with the 002 profiler and the session cache ON, classified by NODE ID against
`regression_baselines/f75aa95.json` (`atlas_throughput_003_migration_audit.json`). Exactly one broad run.

| measure | 002 migration audit | 003 migration audit |
|---|---|---|
| wall | 3,815 s | **3608.66 s** |
| collected / passed / failed / skipped | 17,480 / 17,088 / 161 / 231 | 17549 / 17155 / 163 / 231 |
| against f75aa95 | PRE_EXISTING 160, TRUE_NEW 1 -> closed | PRE_EXISTING 160, EXPECTED_EPOCH 0, FLAKE 0, **TRUE_NEW 3** -> closed by node id (below) |
| baseline failures now passing | 0 | 0 |
| assembly outer calls / unique keys | 45 / 18 | 47 / 18 |
| session cache | 27 reuse hits, 746 s avoided | 27 reuse hits, 1172.8 s avoided (events by kind: {"generator_site": {"BUILD_EXECUTED": 32, "REUSE_HIT": 47}, "market_bundle": {"BUILD_EXECUTED": 17, "REUSE_HIT": 2}, "production_site": {"BUILD_EXECUTED": 2, "REUSE_HIT": 1}}) |
| demo-media module | 1,494 s | 1389.7 s |
| peak working set (in-process) | 8,486 MB | 8876.8 MB |

The three TRUE_NEW: `test_commercial_actions.py::test_go_route_shape`, `::test_build_go_page_happy_path`, `::test_build_go_page_allows_internal_path` read a prefixed `/go/dayton-oh/...` route. Cause (verified): the 003 determinism test's staged Dayton build ran through the generator's `_prepare_build`, which sets the process-wide `commercial_actions._GO_MARKET_PREFIX`, and `package_staging.overlay` restored the path constants but not the generator's build state, so every later test in the session saw Dayton's prefix. Fix `df1ec32`: `overlay` snapshots and restores `BUILD_STATE_ATTRIBUTES` (categories, labels, /go/ prefix, measurement config); pinned by `test_a_staged_build_leaves_no_build_state_behind`; the whole 003 module (two real cold builds) followed by `test_commercial_actions` passes in one process (87/87). Regression V2 delta closure (`failure_closures/atlas-throughput-003-1.json`, run `data/regression/atlas-throughput-003-closure`): classes ['GENERIC_RUNTIME_CHANGE', 'TEST_EXPECTATION_CHANGE', 'GENERATED_REPORT_ONLY'], 132 modules, 4525 collected, 24 failed, node ids test_build_go_page_allows_internal_path=CLOSED, test_build_go_page_happy_path=CLOSED, test_go_route_shape=CLOSED, against f75aa95 TRUE_NEW 0, FULL_REGRESSION_REQUIRED (V2's verdict for a change to a shared runtime module) = YES -- the order permits exactly one broad run, so that verdict is recorded and left for the next broad run rather than executed here.

The 003 change set (six new modules, the extended classifier, a new test module, packages/receipts/reports)
classifies CLASSIFIER_TEST_INFRA_CHANGE + UNKNOWN_MIXED under Regression V2 and therefore owed exactly this
broad run; it cannot self-authorise through the lane it introduces. **Migration audit TRUE_NEW_FAILURE after
closure = 0.**

## PRODUCTION ACTIVATION STATUS

FAST_PATH_IMPLEMENTED = YES. FAST_PATH_VALIDATED = YES (the Dayton pilot receipt, the 25-case matrix, the
migration audit). FAST_PATH_PRODUCTION_ACTIVATION = **DISABLED** (`launch_packages/pettripfinder/fast_release_activation.json`,
empty `pilot_allowlist`; `regression_delta.fast_data_only_release` keeps `FULL_REGRESSION_REQUIRED = YES` for
every real change set until a founder line enables a market there, after 004/005). The fast path was not used
to deploy anything; the existing deployment workflow is untouched.

## 004 INPUT PACKET

`atlas_throughput_003_004_input_packet.md`: what 004 builds on (package digest, dependency digest, receipts,
staged input digest, byte-deterministic changed-market bundles, the session cache's verify-on-hit) and the seven
measured obstacles to safe cross-run reuse (the undeclared input closure, module-state identity, commit-bearing
metadata, the un-keyed whole-site compose, no persistence, receipt expiry on live movement, and the fact that
only Dayton currently seals).

## GIT

Commits on `worker/atlas-throughput-001` after the 002 head `e982aad`, all pushed:

1. `c79ed9d` -- ATLAS-THROUGHPUT-003 build critical fast release lane (the six modules, the Regression V2
   extension, the ownership template, the activation and revocation files, 69 tests, the Dayton pilot package
   + ELIGIBLE receipt, the eight report families, the 004 input packet, the runbook section, the work-item doc,
   the regenerated test inventory).
2. `df1ec32` -- staged builds restore the generator's build state (the audit's one TRUE_NEW class), its test,
   the migration audit report.
3. `the closure commit (branch tip at push)` -- the node-id closure artifact, the closure run's delta, this FINAL.

Regression proof: targeted suites green (test_atlas_throughput_003 69/69 incl. the two-cold-build determinism
test; test_regression_delta_001 + test_atlas_throughput_001/002 + test_factory_throughput_001 202 passed);
ONE migration audit (17549 collected, PRE_EXISTING 160 = the f75aa95 set, TRUE_NEW 3 -> 0 after closure); `origin == HEAD`; tree
clean. Committed content: engineering, tests, reports, docs, one inert pilot package under the market's own
directory. No market authority, no participation, no deployment.

---

1. DOES A PROVEN DATA-ONLY MARKET AUTHORITY PACKAGE REQUIRE THE 17K FULL REGRESSION? **NO** — by proof: the
   Dayton pilot package is FAST_DATA_ONLY_RELEASE_ELIGIBLE = YES on fifteen direct rules; by policy it still
   does today, because `FAST_PATH_PRODUCTION_ACTIVATION = DISABLED` keeps `FULL_REGRESSION_REQUIRED = YES`
   until 004/005 and a founder activation.
2. HOW LONG DID THE COMPLETE FAST RELEASE-SAFETY LANE TAKE? **60.9 s** for the eligible Dayton package (65.7 s
   including the live-index derivation; 73.6 s for the frozen copy that fails rule C), against a 15-minute proof
   budget.
3. HOW MANY TESTS/RULES DID IT EXECUTE? **15 rules (A–O)** over 129 identities, 50 pet-friendly + 23 no-pets
   records, 78 evidence references, 4 cold builds, the 10-market live index; plus **69 adversarial tests** in the
   targeted module.
4. DID WRONG HOTEL / WRONG EVIDENCE FAIL? **YES** (WRONG_PROPERTY, LEAD_ONLY, MISSING_EVIDENCE_BINDING,
   POLICY_EVIDENCE_IDENTITY_MISMATCH; and 5 live Dayton records refused by the gate).
5. DID UNINTENDED MARKET/PROFILE/ROUTE REMOVAL FAIL? **YES** (MISSING_LIVE_MARKET, MISSING_UNRELATED_PROFILE,
   MISSING_UNRELATED_ROUTE, UNEXPECTED_PROPERTY_DELETION, UNINTENDED_ROUTE_CHANGE; the stale-parent fixture
   fails rule N without rebuilding Indianapolis).
6. DID CROSS-MARKET COLLISION FAIL? **YES** (CROSS_MARKET_IDENTITY_COLLISION + OWNERSHIP_MOVEMENT; DUPLICATE_ROUTE).
7. IS DETERMINISM NOW A BLOCKING CHECK FOR THE FAST PATH? **YES** — rule K, two cold builds, cannot be skipped
   or satisfied by cache hits.
8. ARE SHARED RUNTIME / SCHEMA / ASSEMBLER / UNKNOWN CHANGES STILL BROAD? **YES** — surfaces
   SHARED_RUNTIME_CHANGE, SHARED_SCHEMA_CHANGE, ASSEMBLER_CHANGE, DEPLOYMENT_CHANGE,
   CLASSIFIER_TEST_INFRA_CHANGE, UNKNOWN_MIXED all require the full regression; this order's own change set did.
9. WAS PRODUCTION AUTHORITY CHANGED? **NO** — 0 bytes of registry, census, policy package, shard, partition,
   contract, participation, pins, ledgers or deployment records changed (the pilot package lives under the
   market's own `markets/packages/` directory; it is inert data no build reads).
10. WAS THE FAST PATH USED TO DEPLOY? **NO**.
11. MIGRATION AUDIT TRUE_NEW_FAILURE = **0 (1 found, closed by node id)**
12. IS ATLAS-THROUGHPUT-004 READY? **YES** — the input packet is complete and measured; 004 is not started.

STOP. 004 not started. No market promoted. Nothing deployed.
