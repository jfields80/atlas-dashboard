# PTF-CANONICAL-REREGISTRATION-LANE-REPAIR-001 — FINAL

**Branch** `worker/ptf-reregistration-lane-repair-001` (worktree `C:\Atlas-PTF-Reregistration-Repair`)
**Base** `efd22bc7` (`origin/worker/ptf-deployment-work-order-semantics-001`)
**Shared factory repair.** No market data, participation record, authorization, deployment record or
live state was touched. Nothing was deployed. West Palm Beach was **not** registered, authorized or
modified; its branch `worker/ptf-west-palm-beach-fl-market-001` was only read.

---

## PHASE 1 — CURRENT VERIFIED LIVE (resolved mechanically, unchanged)

| | |
|---|---|
| CURRENT LIVE SOURCE | `e82120cce7e48c62d3c1057a6c82785bed920485` (built from `0cc2817b`) |
| CURRENT LIVE DEPLOYMENT | `6ab1a035c7ef3b14a23a4ec6` (`ptf-deploy-fort-lauderdale-004-…`) |
| CURRENT LIVE MARKETS | 32 |
| CURRENT LIVE PROFILES | 2375 |
| CURRENT LIVE RELEASE-INDEX ROUTES | 2646 |
| CURRENT LIVE SERVED ROUTES | 2711 |
| HOST VERIFIED | YES — `https://pettripfinder.com/sitemap.xml` HTTP 200, sha256 `e81961ae…` = the record's, 2711 `<loc>`, 0 West Palm Beach URLs; `/pet-friendly-hotels/west-palm-beach-fl/` → 404 |

`release_index.resolve_current_live_source()` → RESOLVED YES, head contains live, 0 problems.

## PHASE 2 — THE DEAD END, REPRODUCED (synthetic, before any edit)

Synthetic records only (live `alpha-zz`/`beta-zz`, corrected market `gamma-zz`), run against the untouched
factory: A register → B founder-authorize package A → C/D deployment authorization A written, then SUPERSEDED
→ E not live → F/G classify the correction.

```
G. check_participation: FAIL
   - new row status is 'FOUNDER_AUTHORIZED_FOR_LAUNCH'; a registration may only write SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH
   - the founder-authorized set moved: ['alpha-zz', 'beta-zz'] -> ['alpha-zz', 'beta-zz', 'gamma-zz']
   check_release_integrity: FAIL -- the founder-authorized set is not proven unchanged
   => ELIGIBLE = NO, FULL_REGRESSION_REQUIRED = YES
Withdrawing the row instead -> decision_problems:
   "this decision drops market(s) the previous one authorized: ['gamma-zz']"
Using the market's own prior state as base -> check_participation:
   "gamma-zz already had a participation row at the base; existing row gamma-zz changed; the founder-authorized set moved"
derive_registration_base -> walks back to the pre-market live commit (the market "is brand-new")
```

These stay as regression tests (`TestTheDeadEnd`): the REGISTRATION lane still refuses all three.

### ROOT CAUSE

Three rules, each right for a *first* registration, with no state for "authorized, never live, old bytes
superseded, new founder decision owed":

1. `registration_data_only.check_participation` accepts only a NEW row at SOURCE_READY and an
   unchanged founder-authorized set; `check_release_integrity` requires the same and forbids every
   protected path, including the supersession of the market's own authorization.
2. `launch_participation.decision_problems` is monotone: any decision that drops an authorized market is
   refused, and there was no recorded, package-bound way to say the authorization no longer describes
   shippable bytes.
3. `derive_registration_base` walks to the newest commit naming NO path of the market, so the base can
   never be the market's own prior registration and the change set drags in the authorization order's
   deployment-surface artifacts.

## PHASES 3–4 — THE CONTRACT AND THE MONOTONICITY TRANSITION

Existing vocabulary reused wherever it is faithful:

* **Row status**: the existing `SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH` (no new launch status;
  the assembler still admits only FOUNDER_AUTHORIZED_FOR_LAUNCH).
* **Deployment authorization**: the existing terminal `AUTHORIZED → SUPERSEDED` transition.
* **Package binding**: the existing founder `decision_basis.registered_package_digest`.

One new, narrow, schema-validated field — `decision.founder_authorization_superseded` in
`launch_participation.py` — a list of entries carrying exactly, in order:
`market_id, authorizing_decision{work_order, sha256}, superseded_package_digest, corrected_package_digest,
deployment_authorizations[{authorization_id, bundle_sha256, authorization_status}], market_live,
reauthorization_required`. `supersession_problems` refuses an entry unless the market was authorized by the
predecessor, is NOT authorized now, reads SOURCE_READY, the authorizing decision is a lineage record that
authorized it, both digests are `sha256:<64hex>` and differ, every listed authorization is SUPERSEDED with a
bundle, `market_live` is false and `reauthorization_required` is true.

Monotonicity is **not** weakened: `lost` markets are excused only by such an entry; the lineage check
becomes "authorized + cumulatively superseded never shrinks" (identical to the old count check for every
existing record — `decision_record` adds the annotation only to a record that carries an entry). There is
no generic withdrawal: an unannotated drop and an entry that does not drop its market are both refused.

The narrow lane requires **all 14 conditions** of the order and fails closed on any absence:

| # | condition | where enforced |
|---|---|---|
| 1 | registered at the base | gate (`reregistering_market` ∈ registry at base), isolation cond. 5, `derive_reregistration_base` |
| 2 | not CURRENT VERIFIED LIVE | `live_veto` (+ never in any deployment record) |
| 3 | market-local / derived only | five-bucket partition, SHARED = UNKNOWN = 0; helpers by the isolation proof in re-registration mode |
| 4 | old authorization bound to OLD bytes | participation: base decision is a founder decision with `decision_basis.registered_package_digest` = entry's superseded digest; `authorization_supersession`: each authorization binds the market's contract sha AT THE BASE |
| 5 | every authorization of the old bytes SUPERSEDED | `authorization_supersession` (PREPARED/AUTHORIZED = still deployable → FAIL; DEPLOYED/ROLLED_BACK/FAILED = consumed → FAIL) |
| 6 | corrected package SOURCE READY | row reads SOURCE_READY; `sealed_package` (package covers the exact head bytes) |
| 7 | COVERAGE READY where required | unchanged contract checks (`release_contract` vs `derive_authority`, `market_state_pin` vs the package) |
| 8 | FAST passes | unchanged `fast_receipt` (15/15, 0 UNKNOWN) |
| 9 | no other market's source changes | partition + `derived_globals` (no other shard) + `expected_release` |
| 10 | no unrelated participation change | every other row byte-identical; authorized set loses exactly the market, gains nothing |
| 11 | no live market demoted | same (a live market can't be the one removed: `live_veto`) |
| 12 | no silent transfer A → B | row may not stay FOUNDER_AUTHORIZED; entry names both digests; `corrected_package_digest` must be the package covering the head |
| 13 | new founder authorization required | `reauthorization_required: true`; packet `founder_status AWAITING_FOUNDER_AUTHORIZATION`, `authorized_by null` |
| 14 | production unchanged | `release_integrity`: only the proven SUPERSEDED transitions among protected paths; live verified |

## PHASE 5 — CLASSIFIER

New whole-set class **`AUTHORIZED_NONLIVE_MARKET_REREGISTRATION_DATA_ONLY`** (naming follows
`NEW_MARKET_REGISTRATION_DATA_ONLY` / `COMPOSITE_FRESH_MARKET_DATA_ONLY`): `regression_delta` change class,
release surface, CONDITIONAL matrix row (assembly not required, no lanes), plan key; granted only by
`registration_data_only.evaluate` in RE-REGISTRATION mode. The gate enters that mode only when the registry
is unchanged and the head decision supersedes exactly one market. In that mode: contract/market doc/input
may be MODIFIED, the build closure may not move, the market's own pin block is re-derived (others
byte-identical), and the one permitted protected path is an authorization file's SUPERSEDED transition.
Two checks are added (`authorization_supersession`, `live_veto`) → 17 in all; the original fifteen and the
registration/composite classes are unchanged. Proof: synthetic lifecycle → **ELIGIBLE YES,
FULL_REGRESSION_REQUIRED NO, SHARED 0, UNKNOWN 0, sum_equals_total**.

## PHASE 6 — AUTHORIZATION INVALIDATION (mechanical)

* OLD PACKAGE A AUTHORIZATION DOES NOT AUTHORIZE PACKAGE B — the row must read SOURCE_READY (a head that keeps
  it FOUNDER_AUTHORIZED fails `check_reregistration_participation` and `supersession_problems`).
* OLD DEPLOYMENT AUTHORIZATION DOES NOT AUTHORIZE PACKAGE B — SUPERSEDED ∉ `DEPLOYABLE_STATUSES`,
  `transition(SUPERSEDED → AUTHORIZED)` raises, and `verify_authorization` against a different bundle returns
  `bundle_sha256: authorization binds …` (tested on a committed real record, read-only).
* SUPERSEDED REMAINS TERMINAL — a changed authorization may move only `authorization_status` and append one
  SUPERSEDED history entry; any other field change fails.
* NEW PACKAGE B: FOUNDER AUTHORIZATION = NO, DEPLOYMENT AUTHORIZATION = NO. No inheritance by market id: the
  entry is bound to the authorizing decision's sha256 and both package digests.

## PHASE 7 — HARD VETOES (all fail closed, tested)

live market · market named by a deployment record · unsuperseded (AUTHORIZED) authorization · consumed
(DEPLOYED) authorization · supersession that moved another field · another market's shard · another market's
contract · shared factory code · unknown path · unowned global · build closure · live production manifest ·
deployment pin · a NEW authorization file · reuse of the old founder authorization (row kept authorized) ·
a head that supersedes nothing · authorization not bound to the base registration · corrected digest ≠ the
covering package · not-package-bound founder decision · wrong superseded digest · base that is not the
authorizing decision · another participation row moving · founder named as writer · malformed entries
(7 variants). The lane's `reregister` step itself refuses a live market and any authorization not
SUPERSEDED, writing nothing.

## PHASE 8 — REGISTRATION BASE

`registration_release_lane.derive_reregistration_base`: the first-parent commit that **wrote** the
authorizing decision named by the head's entry (oldest commit of the contiguous run whose participation
record hashes to it) — the market's own prior registered state. Refused unless it contains the live lineage
commit, registers the market, and carries live's deployment records, manifest and deployment pin
byte-for-byte and every live authorization unchanged, its only extra authorizations being undeployed ones of
this market. `classify_automatically` selects it when the HEAD supersedes the market. Proven: base = AUTH
commit (package A, contract v1, pin block A); head = corrected package B; `alpha-zz`/`beta-zz` pin blocks and
paths identical; the old rule (`derive_registration_base`) still walks back to the pre-market commit.

## PHASE 9 — FOCUSED TESTS

`tests/pettripfinder/test_reregistration_lane_001.py` — **55 tests**, all synthetic; the lifecycle runs in a
throwaway git repo with the classifier's git seams pointed at it. Only the checks this order did not touch
(package seal, FAST receipt, expected release, identity routes, contract derivation, global regeneration)
are stubbed; each keeps its own audited battery. Covers all 16 required cases.

## PHASE 10 — TARGETED EXISTING TESTS (one pytest process)

Modules: the new battery, `test_registration_data_only_001`, `test_composite_fresh_market_001`,
`test_regression_delta_001`, `test_release_factory_bounded_repair_002`,
`test_participation_lineage_contract_006`, `test_deployment_authorization_047`, `test_atlas_throughput_002`,
`test_release_composition_contract_006`, `test_registered_market_partition_resolution_001`.

| | |
|---|---|
| COLLECTED | 586 (new battery 55) |
| PASSED | 572 (new battery 55/55) |
| FAILED | 14 — exactly the 14 PRE_EXISTING nodes below (failure-set identity) |
| SKIPPED | 0 |
| RUNTIME | 409.5 s (pytest 408.2 s), one process |
| PEAK MEMORY | 124.9 MB peak working set (`K32GetProcessMemoryInfo`) |

An earlier run of the same set (before the runbook fix) failed 15: the 14 below plus the runbook node.

`test_launch_participation_046.py` was started in the first attempt and **stopped**: its module fixture
assembles the whole production site, which this order forbids. It was not counted. Not run (per the order):
broad regression, `test_factory_throughput_001.py`, demo-media, whole-site assembly, unrelated market tests.

## PHASE 11 — DIFFERENTIAL (exact nodes at untouched `efd22bc7`, worktree `C:\t\rrbase`)

| node | at base | class |
|---|---|---|
| `test_registration_data_only_001` × 12 (Charlotte fixture pinned to base `11373275`; the registry has since gained 20+ markets) | FAIL, same reasons | PRE_EXISTING |
| `test_composite_fresh_market_001::TestThePartition::test_a_bare_re_registration_keeps_the_original_class` (same stale base → `KeyError: 'change_class'`) | FAIL, same | PRE_EXISTING |
| `test_regression_delta_001::test_the_committed_closures_all_verify` (`KeyError: 'node_id_results'`, the known closure-artifact shape) | FAIL, same | PRE_EXISTING |
| `test_regression_delta_001::test_the_runbook_carries_the_post_broad_fix_rule` | PASS at base | REPAIR_CAUSED → **fixed** (runbook now names the class) → PASS |

**REPAIR_CAUSED = 0 (after fix) · UNRESOLVED = 0 · CURRENT_REAL_DEFECT = 0.**

Also found, not this order's: `reports/factory_throughput_001_test_inventory.json` is already stale at the
base (+1 HISTORICAL_COHORT site from `test_release_factory_bounded_repair_002.py`). The new module adds **0**
pin sites (the Phase-1 live numbers are measured here, not pinned in a test), so this order moves the
inventory by nothing; it was left for the order that owns that debt.

## PHASE 12 — SIMULATED RE-REGISTRATION (synthetic repository)

`L` live (alpha, beta) → `REG` register gamma, package A → `AUTH` founder authorizes A + deployment
authorization A AUTHORIZED (never deployed) → `CORR` market-local correction + helper + package B → `SUP`
authorization A → SUPERSEDED → `REREG` `registration_release_lane.reregister` → `classify_document(base=AUTH)`.

| | |
|---|---|
| REREGISTRATION CLASS | `AUTHORIZED_NONLIVE_MARKET_REREGISTRATION_DATA_ONLY` |
| ELIGIBLE | YES (17/17 checks PASS) |
| FULL_REGRESSION_REQUIRED | NO (assembly not required, REMOTE_BROAD_JOBS_REQUIRED 0) |
| BROAD RUNS | 0 |
| partition | SHARED 0, UNKNOWN 0, sum = total; helper proven in re-registration mode |
| Package B | SOURCE_READY (row), readiness `AUTHORIZATION_READY` / `AWAITING_FOUNDER_AUTHORIZATION`, `authorized_by null`, `old_authorizations_authorize_the_corrected_package false` — NON-DEPLOYABLE until a new founder decision |
| Old package A | authorization SUPERSEDED, bound to bundle A — NON-DEPLOYABLE |
| Current live | UNCHANGED (only gamma paths moved; `reregister` wrote exactly the participation record and gamma's own pin block) |

## PHASE 13 — PRODUCTION DELTA

Production files changed (shared factory implementation + its generated contract/matrix + runbook):

* `scripts/pettripfinder/launch_participation.py` — supersession entry, annotated lineage record, narrowed monotonicity
* `scripts/pettripfinder/registration_data_only.py` — re-registration mode, 2 new checks, contract section
* `scripts/pettripfinder/registration_release_lane.py` — `derive_reregistration_base`, `reregister`, packet section, pin `replace`
* `scripts/pettripfinder/regression_delta.py` — the class, surface, matrix row, plan key
* `scripts/pettripfinder/market_local_isolation.py` — condition 5 in re-registration mode
* `launch_packages/pettripfinder/registration_data_only_contract.json` — regenerated (additive `reregistration` section)
* `launch_packages/pettripfinder/regression_validation_matrix.json` — regenerated (additive row/surface)
* `docs/PTF_HARDENED_FACTORY_RUNBOOK.md` — the class row and its procedure

Test files: `tests/pettripfinder/test_reregistration_lane_001.py` (new). Report: this file.

MARKET DATA CHANGES = 0 · PARTICIPATION DATA CHANGES = 0 · AUTHORIZATION RECORD CHANGES = 0 ·
DEPLOYMENT RECORD CHANGES = 0 · CURRENT LIVE CHANGES = 0 · DEPLOYMENT = NO.

The repo's CLAUDE.md asks for a full regression before commits; this order explicitly forbids a broad run,
and none was run.

## WEST PALM BEACH APPLICABILITY (read-only measurement of `6fa2ae34`)

Measured against the real branch without touching it:

* The base the new rule derives would be **`d4da13d1`** (wrote participation `19328995…`, unchanged through
  `6fa2ae34`; parent `5da443c1…`). Its deployment records, manifest and deployment pin equal live's; its only
  extra authorization is WPB's own.
* Authorization `ptf-auth-west-palm-beach-003-217f87eeba72` binds contract sha `1c45fc75…` = the contract at
  `d4da13d1`; package A `pkg-west-palm-beach-fl-789c0187e366abe8` is committed there; the founder decision's
  `registered_package_digest` is `sha256:789c0187…`.
* `d4da13d1..6fa2ae34` = 21 paths: 20 land in narrow buckets (roles with re-registration statuses, companions,
  the supersession claim), and `west_palm_beach_fl_census_reconciliation_001.py` **passes** the isolation proof
  in re-registration mode.
* **One path would still be refused, correctly:** `scripts/pettripfinder/west_palm_beach_fl_withdraw_authorization_004.py`
  imports `deployment_authorization` → SHARED. The WPB re-registration order must remove it from the tree
  (it stays in history at `9cf163b1`) before `reregister` + `packet`. It must also merge this branch.

---

## FINAL ANSWERS

1. CURRENT DEAD-END REPRODUCED = YES (synthetic; exact participation + release_integrity messages; monotone refusal; base walks past the market)
2. ROOT CAUSE = registration-only participation/integrity rules + a monotone chain with no package-bound supersession + a base that can never be the market's own prior registration
3. NEW REREGISTRATION CLASS = `AUTHORIZED_NONLIVE_MARKET_REREGISTRATION_DATA_ONLY`
4. LIVE MARKET HARD VETO = YES (`live_veto`: CURRENT_VERIFIED_LIVE and every deployment record; `reregister` refuses too)
5. OLD AUTH MUST BE SUPERSEDED = YES (every authorization naming the market, terminally, never consumed)
6. OLD AUTH CAN AUTHORIZE NEW PACKAGE = NO
7. NEW FOUNDER AUTH REQUIRED = YES
8. OWN PRIOR REGISTRATION ALLOWED AS BASE = YES (`derive_reregistration_base` → the authorizing commit)
9. VALID CORRECTION ELIGIBLE = YES
10. FULL_REGRESSION_REQUIRED = NO
11. BROAD RUNS = 0
12. NEGATIVE CASES = 41 (20 hard-veto lifecycle refusals + 10 chain + 6 participation + 2 base + 3 dead-end refusals), all fail closed
13. FOCUSED TESTS COLLECTED = 586 (targeted, 10 modules; new battery 55)
14. FOCUSED TESTS PASSED = 572 (new battery 55/55)
15. FOCUSED TESTS FAILED = 14 (all PRE_EXISTING, identical at `efd22bc7`)
16. REPAIR_CAUSED FAILURES = 0
17. UNRESOLVED = 0
18. PRODUCTION FILES CHANGED = 8 (5 modules, 2 regenerated documents, 1 runbook)
19. TEST FILES CHANGED = 1 (new)
20. MARKET DATA CHANGED = NO
21. PARTICIPATION DATA CHANGED = NO
22. AUTHORIZATION DATA CHANGED = NO
23. DEPLOYMENT RECORDS CHANGED = NO
24. CURRENT LIVE MODIFIED = NO
25. DEPLOYMENT PERFORMED = NO
26. READY FOR WEST PALM BEACH REREGISTRATION = YES — the lane is ready; the WPB order must merge this branch and remove `west_palm_beach_fl_withdraw_authorization_004.py` from its tree, then `reregister` → `packet`, then a new founder authorization.

PTF CANONICAL REREGISTRATION LANE REPAIR = PASS
LIVE MARKET CORRECTION THROUGH THIS LANE = FORBIDDEN
OLD AUTHORIZATION TRANSFERS TO NEW PACKAGE = NO
NEW FOUNDER AUTHORIZATION REQUIRED = YES
FULL_REGRESSION_REQUIRED FOR VALID CORRECTION = NO
REPAIR-CAUSED FAILURES = 0
CURRENT LIVE MODIFIED = NO
DEPLOYMENT PERFORMED = NO
READY FOR WEST PALM BEACH REREGISTRATION = YES
