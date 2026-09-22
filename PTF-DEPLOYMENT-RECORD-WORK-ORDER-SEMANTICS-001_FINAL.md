# PTF-DEPLOYMENT-RECORD-WORK-ORDER-SEMANTICS-001 — FINAL

**Verdict: PASS.** A deployment record names two different orders — the one that
**authorized** the release and the one that **performed** the deploy — and a guard
in `test_market_state_pins.py` had been comparing the first against the second.
It reported a defect that does not exist while checking neither fact against the
document that defines it. Both are now checked, separately, each against its own
document, and the failure is gone.

No deployment record, authorization, pin or line of factory production code was
modified. No deployment was performed. Production is byte-identical.

| | |
|---|---|
| worktree | `C:\Atlas-PTF-Deployment-WorkOrder-Repair` |
| branch | `worker/ptf-deployment-work-order-semantics-001` |
| base | `9075596f` (PTF-SUPERSESSIONS-LINEAGE-REPAIR-001), tree clean at start |
| files changed | 1 test module + this report |
| production delta | **zero** |

---

## PHASE 1 — BASE AND CURRENT LIVE

Base verified on the named branch, tree clean, containing both predecessors:
`09851d50` (participation guard repair) and `9075596f` (supersessions lineage
repair).

Live resolved mechanically through `release_index.current_verified_live()` and
`release_index.live_index()` — the authoritative resolver, which reconciles the
deployment record, the global manifest, the deployment-state pin and the consumed
authorization and reports every disagreement.

```
CURRENT LIVE DEPLOYMENT      = 6ab1a035c7ef3b14a23a4ec6
CURRENT LIVE SOURCE COMMIT   = 0cc2817b536eda2b62e59f9b05e8da38ae6ecc85
CURRENT LIVE AUTHORIZATION   = ptf-auth-fort-lauderdale-003-0ec5c6557d79
CURRENT LIVE BUNDLE          = 0ec5c6557d79eaf77a4065b6700c0a5807e9bfe282408dd4779804b33af3a40f
CURRENT LIVE SITEMAP         = e81961ae76454ce608fcb39624d5147c8779f52b269faab9449138397cb8fa3d
CURRENT LIVE MARKETS         = 32
CURRENT LIVE PROFILES        = 2375
CURRENT LIVE RELEASE-INDEX   = 2646   (detroit-ann-arbor-mi indexed and withheld)
CURRENT LIVE SERVED ROUTES   = 2711
RESOLVER PROBLEMS            = ()
HOST VERIFIED                = YES — https://pettripfinder.com/sitemap.xml HTTP 200,
                               sha256 e81961ae76454ce608fcb39624d5147c8779f52b269faab9449138397cb8fa3d,
                               2711 <loc> entries,
                               /pet-friendly-hotels/fort-lauderdale-fl/ -> 200,
                               /pet-friendly-hotels/detroit-ann-arbor-mi/ -> 404,
                               0 occurrences of "detroit" in the sitemap
```

Matches the expected 32 / 2375 / 2646 / 2711 exactly.

---

## PHASE 2 — THE EXACT FAILURE

Reproduced with the smallest node, nothing else collected.

```
TEST NODE ID   = tests/pettripfinder/contracts/test_market_state_pins.py::
                 TestDeploymentPinsAgreeWithTheSource::test_live_block_is_the_latest_deployment_record
BASE RESULT    = FAILED (1 failed in 0.54s)
ASSERTION      = assert record["work_order"] == live.deployed_by
EXPECTED VALUE = PTF-FORT-LAUDERDALE-FL-PRODUCTION-DEPLOYMENT-004        (live.deployed_by)
ACTUAL VALUE   = PTF-FORT-LAUDERDALE-FL-FOUNDER-LAUNCH-AUTHORIZATION-003 (record["work_order"])
```

---

## PHASE 3 — THE RECORD'S REAL SEMANTICS, FROM THE IMPLEMENTATION

`deployment_authorization.build_deployment_record()` line 612:

```python
("work_order", auth.get("work_order")),
```

The field is copied off the consumed authorization. By construction it can be
nothing but the **authorizing** order — a deployment record cannot name the
order that deployed it in that field, because the field is written from a
document signed before the deploy existed.

The deploying order is recorded separately, inside `deployer`.

```
DEPLOYMENT_RECORD.WORK_ORDER SEMANTIC   = the order that AUTHORIZED the release.
                                          Copied verbatim from the consumed
                                          authorization by build_deployment_record().

DEPLOYMENT_RECORD.DEPLOYER.WORK_ORDER   = the order that PERFORMED the Netlify
                                          deployment. Present on 23 of 35 records,
                                          contiguously from ptf-deploy-cincinnati-004
                                          (2026-09-06) onward. Where it differs from the
                                          top-level work_order the record also carries
                                          deployer.authorizing_work_order echoing the
                                          top-level value, so neither fact is lost.

DEPLOYMENT_STATE.LIVE.DEPLOYED_BY       = the order that performed the CURRENT live
                                          deployment — the deploying order of the live
                                          record, not its authorizing order.
```

### The record audit

Every committed record, against the authorization it names — not a sample.

```
DEPLOYMENT RECORDS AUDITED = 35
AUTHORIZATIONS ON DISK     = 35
RECORDS FOLLOWING CONTRACT = 35     (record["work_order"] == its authorization's work_order)
RECORDS VIOLATING CONTRACT = 0
UNREACHABLE AUTHORIZATIONS = 0
```

35/35, without exception, exactly as the previous order proved.

### A correction to the previous order's Phase 11

PTF-SUPERSESSIONS-LINEAGE-REPAIR-001 reported that the two concepts "first
diverged at **Miami**", making two affected launches. The full audit finds
**three**, and the first is earlier:

| deployed | record | authorizing order | deploying order |
|---|---|---|---|
| 2026-09-14 | `ptf-deploy-fayetteville-004-6aa750d8…` | `PTF-FAYETTEVILLE-NC-FOUNDER-AUTHORIZATION-AND-LIVE-LAUNCH-002` | `PTF-FAYETTEVILLE-NC-RESUME-HOST-DEPLOY-004` |
| 2026-09-20 | `ptf-deploy-miami-006-6ab071a5…` | `PTF-MIAMI-FL-FOUNDER-LAUNCH-AUTHORIZATION-005` | `PTF-MIAMI-FL-PRODUCTION-DEPLOYMENT-006` |
| 2026-09-21 | `ptf-deploy-fort-lauderdale-004-6ab1a035…` | `PTF-FORT-LAUDERDALE-FL-FOUNDER-LAUNCH-AUTHORIZATION-003` | `PTF-FORT-LAUDERDALE-FL-PRODUCTION-DEPLOYMENT-004` |

Fayetteville is the one the earlier report missed: a host 403 split that launch
in two, and `…RESUME-HOST-DEPLOY-004` shipped byte-identically what `…-002` had
authorized. That is the same shape as Miami and Fort Lauderdale, and it is the
first time the factory recorded a deploy performed by an order other than the
one that signed it. The guard has therefore been wrong since 2026-09-14, not
2026-09-20 — but the divergence was never visible while Fayetteville and
Greenville were not live-latest, so it only surfaced once Miami landed.

All three carry `deployer.authorizing_work_order`, so in every diverging case the
record states both orders explicitly and nothing had to be inferred.

### The `deployer` block has no fixed schema

Worth recording, because it constrains what the repaired guard may demand. Seven
distinct `deployer` shapes exist across the history:

| keys | count |
|---|---|
| `authorized_by`, `authorizing_work_order`, `executed_by`, `work_order` | 14 |
| `authorized_by`, `executed_by`, `work_order` | 8 |
| `authorized_by`, `executed_by`, `netlify_account`, `started_at` | 6 |
| `authorized_by`, `executed_by` | 3 |
| `kind`, `operator`, `version` | 2 |
| `authorized_by`, `credential`, `executed_by`, `work_order` | 1 |
| `account`, `by`, `team`, `via` | 1 |

The twelve oldest records name no deploying order at all. A guard that demanded
`deployer.work_order` from every record would fail on correct history, so the
repaired guard derives the point at which the field entered the schema from the
records themselves and requires it from there on — which is contiguous and holds.

---

## PHASE 4 — THE REPAIR

One line changed in the existing guard:

```python
-        assert record["work_order"] == live.deployed_by
+        assert deploying_work_order(record) == live.deployed_by
```

and the real contract asserted in full alongside it. The guard is not weakened:
it still binds every field it bound before, and now binds each of the two orders
to the document that defines it rather than to each other.

Two module-level readers and two problem-reporters were added, in the shape the
previous order established for `chain_problems`:

- `authorizing_work_order(record)` — `record["work_order"]`, named for what it is.
- `deploying_work_order(record)` — `deployer.work_order` when carried, else the
  top-level order (before the field existed, one order did both and it is the
  only order the record names). This is a read, never an excuse: a record that
  owes the field and lacks it is caught by `record_problems`, not defaulted here.
- `first_record_naming_its_deployer(records)` — derives the schema boundary from
  the records, so no market name is hard-coded.
- `record_problems(records, authorizations)` — every way the committed records
  fail the two-order contract.
- `live_lineage_problems(live, records, authorizations)` — every way the live pin
  fails to describe the deployment production actually runs.

### What the guards now assert

| # | the order's requirement | how it is asserted |
|---|---|---|
| 1 | record `work_order` agrees with its authorization's | `test_every_record_was_released_under_its_authorizations_own_order`, over all 35, both sides read from different documents |
| 2 | `deployer.work_order` identifies the deploying order | `test_every_record_since_the_field_existed_names_its_deploying_order` — derived boundary, no market named |
| 3 | `live.deployed_by` agrees with live lineage | `test_the_live_pin_describes_the_deployment_production_runs` |
| 4 | latest record agrees with live ID / bundle / site | same guard: latest-by-time IS the live record, and its deploy id, bundle, sitemap and `target_site` all match |
| 5 | the two concepts are not conflated | `test_the_two_orders_are_allowed_to_differ_and_some_really_do` — requires that committed records really do separate them, and that each such record carries both |

Requirement 5 is the one that keeps this honest. If no committed record ever
separated the two orders, the repaired guard would be indistinguishable from the
broken one, so the module asserts that the divergence exists and is recorded.

No Miami or Fort Lauderdale string appears in any assertion. The one hard-coded
value is `LIVE_TARGET_SITE = "pettripfinder-prod"`, which every committed record
shares and which exists so that a record deployed to some other site is a finding
rather than a comparison against itself.

---

## PHASE 5 — NEGATIVE COVERAGE

Nineteen negative tests, each handing a real guard a fixture that is wrong in one
specific way and requiring the failure. Every fixture is a `json.loads(json.dumps(…))`
deep copy or a `dataclasses.replace` of the live pin, mutated in memory. Nothing
is written to disk; no committed record, authorization or pin is touched.

| the order's case | tests |
|---|---|
| 1 — record `work_order` disagrees with its authorization | `test_a_record_that_disagrees_with_its_authorization_is_caught`, `test_a_disagreeing_record_also_fails_the_positive_guard` |
| 2 — `deployer.work_order` missing | `test_a_record_that_drops_its_deploying_order_is_caught`, `test_a_dropped_deploying_order_also_fails_the_positive_guard` |
| 3 — `deployer.work_order` wrong | `test_a_deploying_order_that_is_not_a_work_order_is_caught`, `test_a_divergence_recorded_with_the_wrong_authorizing_order_is_caught`, `test_an_undeclared_divergence_is_caught` |
| 4 — `live.deployed_by` points at another action | `test_a_live_deployed_by_naming_another_action_is_caught`, `test_a_live_deployed_by_that_is_not_a_work_order_is_caught`, `test_the_repaired_live_guard_catches_a_moved_deployed_by` |
| 5 — latest record differs from live | `test_a_latest_record_that_is_not_the_live_one_is_caught`, `test_a_live_pin_naming_no_record_at_all_is_caught`, `test_a_live_deploy_id_the_record_never_shipped_is_caught` |
| 6 — bundle / site identity differs | `test_a_live_bundle_that_the_record_never_shipped_is_caught`, `test_a_live_sitemap_that_the_record_never_shipped_is_caught`, `test_a_record_deployed_to_another_site_is_caught` |
| 7 — authorization lineage unreachable | `test_a_record_whose_authorization_is_unreachable_is_caught`, `test_a_live_authorization_that_is_unreachable_is_caught`, `test_an_unreachable_authorization_also_fails_the_positive_guard` |

Three further tests exist so the guards cannot pass vacuously or by side effect:
`test_the_unmutated_fixture_reports_no_problems`,
`test_the_repaired_live_guard_still_accepts_the_committed_pin` (it is repaired,
not relaxed) and `test_the_committed_records_are_not_touched_by_these_fixtures`,
which re-reads the live record off disk after the mutating tests have run and
requires its bytes still to say what the live pin was built from.

---

## PHASE 6 — TARGETED VERIFICATION

One pytest process at a time throughout. No broad regression, no demo-media, no
unrelated market suites.

### A — the exact repaired node

```
tests/pettripfinder/contracts/test_market_state_pins.py::
  TestDeploymentPinsAgreeWithTheSource::test_live_block_is_the_latest_deployment_record

BEFORE = FAILED (1 failed in 0.54s)
AFTER  = PASSED (1 passed in 0.41s)
```

### B — its own module, whole

```
tests/pettripfinder/contracts/test_market_state_pins.py

COLLECTED = 226
PASSED    = 226
FAILED    = 0
SKIPPED   = 0
RUNTIME   = 4.32 s
```

At base this module was 180 passed / 3 failed; the supersessions repair took it
to 196 passed / 1 failed; this repair takes it to **226 passed / 0 failed** — the
29 tests added here and the last remaining failure cleared.

### C — the related deployment-record, authorization and live-state modules

```
tests/pettripfinder/contracts/test_market_state_pins.py
tests/pettripfinder/test_deployment_authorization_047.py
tests/pettripfinder/test_deployment_012.py
tests/pettripfinder/test_production_deploy_012.py
tests/pettripfinder/test_global_deployment_architecture_045.py
tests/pettripfinder/test_factory_throughput_001.py
tests/pettripfinder/test_launch_participation_046.py

COLLECTED   = 422
PASSED      = 419
FAILED      = 2
SKIPPED     = 1
RUNTIME     = 5187.66 s (1:26:27)
PEAK MEMORY = not captured (the wrapper read PeakWorkingSet64 after exit, which
              reports 0 for an exited process; the run was observed at ~371-391 MB
              working set while live)
```

This selection was wider than it needed to be: `test_factory_throughput_001.py`
rebuilds the whole test inventory and dominated the 1:26 runtime. The two
failures it surfaced are both outside this repair and are classified in Phase 7.

```
FAILED tests/pettripfinder/test_production_deploy_012.py::
       TestTheRepositoryMatchesProduction::test_the_manifest_verifies_and_is_a_later_bundle_than_this_one
FAILED tests/pettripfinder/test_factory_throughput_001.py::
       TestTheHarness::test_the_committed_inventory_reproduces_from_the_suite
```

---

## PHASE 7 — DIFFERENTIAL

Both remaining failures were re-run as their exact nodes in a detached worktree
at the untouched base `9075596f` (`C:\t\dwobase`, `git status` clean, the test
module at its original 530 lines), same flags: **2 failed in 9.96 s**.

| node id | base `9075596f` | after repair | class |
|---|---|---|---|
| `test_market_state_pins::…::test_live_block_is_the_latest_deployment_record` | FAIL | **PASS** | **FIXED** (the target) |
| `test_production_deploy_012::TestTheRepositoryMatchesProduction::test_the_manifest_verifies_and_is_a_later_bundle_than_this_one` | FAIL | FAIL | PRE_EXISTING |
| `test_factory_throughput_001::TestTheHarness::test_the_committed_inventory_reproduces_from_the_suite` | FAIL | FAIL | PRE_EXISTING |

```
REPAIR_CAUSED       = 0
PRE_EXISTING        = 2
CURRENT_REAL_DEFECT = 0
UNRESOLVED          = 0
FIXED               = 1
```

The failure set is identical at base and after — proved by identity, not by
arithmetic. Neither pre-existing failure is this order's to take:

* **The suite inventory pin** fails `HISTORICAL_COHORT_INVARIANT 908 != 907` —
  the **same two numbers** before and after, so the 29 tests added here move it
  by exactly zero. That is structural, not luck: the scanner classifies by module
  name, and `_HISTORICAL_NAME` matches a work-order number in the filename.
  `contracts/test_market_state_pins.py` carries none, so nothing added to it can
  land in that class at all. The pin was already one short at base. Re-pinning a
  shared generated report needs an order that names what it moved
  (`test_inventory_repin_006.py` is the pattern); PTF-SUPERSESSIONS-LINEAGE-REPAIR-001
  reached the same conclusion and left it, and so does this one.

* **The 012 manifest flag** fails `assert manifest["deployment_authorized"] is True`
  against a committed manifest that holds `false`. That is committed data in
  `global_deployment`, which this order does not touch and whose bytes are
  unchanged. The assertion is a stale expectation from the Indianapolis-era
  launch, in the same family as the Nashville-launch staleness the previous order
  documented. Repairing it means changing a launch-era module's expectations,
  which is outside a bounded test-semantics repair on the deployment record.

Neither is a CURRENT_REAL_DEFECT: production is verified live and correct in
Phases 1 and 9, and no committed record or pin disagrees with what is served.

---

## PHASE 8 — ZERO PRODUCTION DELTA

```
DEPLOYMENT RECORD CHANGES      = 0
DEPLOYMENT STATE CHANGES       = 0
AUTHORIZATION CHANGES          = 0
PARTICIPATION CHANGES          = 0
SUPERSESSION DATA CHANGES      = 0
MARKET DATA CHANGES            = 0
FACTORY PRODUCTION CODE CHANGES= 0
CURRENT LIVE SITE CHANGES      = 0
```

Checked per directory: `deploy/netlify/deployment_records`,
`deploy/netlify/deployment_authorizations`, `tests/pettripfinder/pins`,
`launch_packages`, `scripts` and `data` each report **0 changed files**.

The whole delta of this order:

```
 M atlas-dashboard/tests/pettripfinder/contracts/test_market_state_pins.py   (+481 / -1)
?? PTF-DEPLOYMENT-RECORD-WORK-ORDER-SEMANTICS-001_FINAL.md
```

One test module and one report. No fixture files were needed — every negative
case is an in-memory deep copy, so nothing new was written to the tree.

---

## PHASE 9 — CURRENT LIVE REVERIFY

Re-read from the host at the end of the order and compared byte-for-byte with
the Phase 1 capture:

```
CURRENT LIVE DEPLOYMENT   = 6ab1a035c7ef3b14a23a4ec6      unchanged
MARKETS                   = 32                            unchanged
PROFILES                  = 2375                          unchanged
RELEASE-INDEX ROUTES      = 2646                          unchanged
SERVED ROUTES             = 2711                          unchanged
SITEMAP sha256            = e81961ae76454ce608fcb39624d5147c8779f52b269faab9449138397cb8fa3d
SITEMAP vs PHASE 1        = BYTE-IDENTICAL (cmp clean)
FORT LAUDERDALE           = /pet-friendly-hotels/fort-lauderdale-fl/ -> 200   LIVE
DETROIT                   = /pet-friendly-hotels/detroit-ann-arbor-mi/ -> 404 WITHHELD
DEPLOYMENT PERFORMED      = NO
```

---

## FINAL ANSWERS

```
 1. CURRENT LIVE DEPLOYMENT        = 6ab1a035c7ef3b14a23a4ec6
 2. CURRENT LIVE MARKETS           = 32
 3. FAILING TEST NODE              = tests/pettripfinder/contracts/test_market_state_pins.py::
                                     TestDeploymentPinsAgreeWithTheSource::
                                     test_live_block_is_the_latest_deployment_record
 4. OLD TEST ASSUMPTION            = that a deployment record's `work_order` names the order
                                     which EXECUTED the Netlify deployment, so it must equal
                                     deployment_state live.deployed_by
 5. DEPLOYMENT_RECORD.WORK_ORDER   = the AUTHORIZING order, copied verbatim from the consumed
                                     authorization by build_deployment_record()
 6. DEPLOYER.WORK_ORDER MEANS      = the order that PERFORMED the deployment (with
                                     deployer.authorizing_work_order echoing the authorizing
                                     one whenever the two differ)
 7. LIVE.DEPLOYED_BY MEANS         = the order that performed the CURRENT live deployment
 8. DEPLOYMENT RECORDS AUDITED     = 35
 9. RECORDS FOLLOWING CONTRACT     = 35
10. RECORDS VIOLATING CONTRACT     = 0
11. TEST FILES CHANGED             = 1
12. PRODUCTION FILES CHANGED       = 0
13. NEGATIVE CASES ADDED           = 19  (all 7 required cases; plus 3 non-vacuity /
                                     no-mutation safety tests and 7 positive contract guards
                                     = 29 tests added in total)
14. TARGETED TESTS COLLECTED       = 422
15. TARGETED TESTS PASSED          = 419
16. TARGETED TESTS FAILED          = 2   (both PRE_EXISTING, proved at base)
17. TARGETED TESTS SKIPPED         = 1
18. REPAIR_CAUSED FAILURES         = 0
19. PRE_EXISTING FAILURES          = 2
20. CURRENT_REAL_DEFECTS           = 0
21. UNRESOLVED                     = 0
22. DEPLOYMENT RECORDS CHANGED     = 0
23. DEPLOYMENT STATE CHANGED       = 0
24. CURRENT LIVE MODIFIED          = NO
25. DEPLOYMENT PERFORMED           = NO
26. FORT LAUDERDALE STILL LIVE     = YES (200)
27. DETROIT STILL WITHHELD         = YES (404, absent from the sitemap)
28. origin == HEAD                 = YES
29. tree clean                     = YES
30. READY TO RESUME MARKET EXPANSION = YES
```

---

PTF DEPLOYMENT WORK_ORDER SEMANTICS REPAIR = PASS
DEPLOYMENT RECORDS FOLLOW CONTRACT = 35/35
REPAIR-CAUSED FAILURES = 0
UNRESOLVED FAILURES = 0
PRODUCTION CODE CHANGED = NO
DEPLOYMENT RECORDS CHANGED = NO
CURRENT LIVE MODIFIED = NO
DEPLOYMENT PERFORMED = NO
READY TO RESUME MARKET EXPANSION = YES
