# PTF-SUPERSESSIONS-LINEAGE-REPAIR-001 — FINAL

**Verdict: PASS.** The consumed-authorization chain in
`tests/pettripfinder/pins/supersessions.json` stopped nineteen launches ago. It has
been continued, mechanically, from the last entry it carried through to the
authorization production actually serves under. The three guards the gap had
disabled now run, and they cover all 32 live markets with 0 mismatches.

Nothing that serves production was touched. No deployment was performed.

| | |
|---|---|
| worktree | `C:\Atlas-PTF-Supersessions-Repair` |
| branch | `worker/ptf-supersessions-lineage-repair-001` |
| base | `09851d50` (PTF-PARTICIPATION-GUARD-REPAIR-001), tree clean at start |
| files changed | 2 (one reviewed pin, one test module) + this report |
| production delta | **zero** |

---

## PHASE 1 — CLEAN BASE / CURRENT LIVE

Base verified at `09851d50` on the named branch, tree clean.

Resolved mechanically through `release_index.current_verified_live()` +
`release_index.live_index()` — the authoritative resolver, which reconciles the
deployment record, the global manifest, the deployment-state pin and the consumed
authorization and reports every disagreement.

```
CURRENT LIVE SOURCE COMMIT   = 0cc2817b536eda2b62e59f9b05e8da38ae6ecc85
CURRENT LIVE DEPLOYMENT      = 6ab1a035c7ef3b14a23a4ec6
CURRENT LIVE AUTHORIZATION   = ptf-auth-fort-lauderdale-003-0ec5c6557d79
CURRENT LIVE BUNDLE          = 0ec5c6557d79eaf77a4065b6700c0a5807e9bfe282408dd4779804b33af3a40f
CURRENT LIVE SITEMAP         = e81961ae76454ce608fcb39624d5147c8779f52b269faab9449138397cb8fa3d
CURRENT LIVE MARKETS         = 32
CURRENT LIVE PROFILES        = 2375
CURRENT LIVE RELEASE-INDEX   = 2646   (participating markets; detroit-ann-arbor-mi is indexed and withheld)
CURRENT LIVE SERVED ROUTES   = 2711
RESOLVER PROBLEMS            = []
HOST VERIFIED                = YES — https://pettripfinder.com/sitemap.xml HTTP 200,
                               sha256 e81961ae76454ce608fcb39624d5147c8779f52b269faab9449138397cb8fa3d
                               (byte-identical to the authorized digest), 2711 <loc> entries,
                               /pet-friendly-hotels/fort-lauderdale-fl/ → 200,
                               /pet-friendly-hotels/detroit-ann-arbor-mi/ → 404, 0 "detroit" in the sitemap
```

Matches the expected 32 / 2375 / 2646 / 2711 exactly.

---

## PHASE 2 — THE EXACT CURRENT FAILURES

`python -m pytest tests/pettripfinder/contracts/test_market_state_pins.py`
at the untouched base: **3 failed, 180 passed**.

### 1
```
NODE ID   = tests/pettripfinder/contracts/test_market_state_pins.py::
            TestDeploymentPinsAgreeWithTheSource::test_live_profile_counts_are_the_market_pins
ERROR     = KeyError: 'ptf-auth-fort-lauderdale-003-0ec5c6557d79 is not in supersessions.json'
            raised at epochs.py:297, before the first market was compared
STALE DATA= supersessions.json lists 9 authorizations, the last being
            ptf-auth-nashville-005-c12b410ec833, whose note calls itself
            "The CURRENT live authorization"
CURRENT   = production serves under ptf-auth-fort-lauderdale-003-0ec5c6557d79
SURFACE   = tests/pettripfinder/pins/supersessions.json (data)
```

### 2
```
NODE ID   = tests/pettripfinder/contracts/test_market_state_pins.py::
            TestSupersessionRegistry::test_the_live_authorization_has_nothing_moved
ERROR     = the same KeyError, same cause
SURFACE   = the same
```

### 3
```
NODE ID   = tests/pettripfinder/contracts/test_market_state_pins.py::
            TestDeploymentPinsAgreeWithTheSource::test_live_block_is_the_latest_deployment_record
ERROR     = assert record["work_order"] == live.deployed_by
            'PTF-FORT-LAUDERDALE-FL-FOUNDER-LAUNCH-AUTHORIZATION-003'
            != 'PTF-FORT-LAUDERDALE-FL-PRODUCTION-DEPLOYMENT-004'
STALE DATA= none — see PHASE 11. Neither document is wrong.
SURFACE   = OUT OF SCOPE for this order (Phase 11 says inspect only)
```

A fourth, in another module, has the same root cause and was found by reading the
consumers rather than by running them — it never surfaced in Phase 2 because it
lives outside the named module:

```
NODE ID   = tests/pettripfinder/test_factory_throughput_001.py::
            TestDeploymentHistoryIsProtected::test_the_live_authorization_binds_every_market_exactly
ERROR     = the same KeyError
```

That one matters most: it is the test that re-hashes **all 32 live release
contracts** against what the founder authorized. It had not executed since Raleigh.

---

## PHASE 3 — RECONSTRUCTED SUPERSESSION HISTORY

Nothing below is inferred from a market name or from recency. Each claim names the
committed artifact it was read from.

### 1. What the registry represents

Its own header states it: *"Which later work orders moved a market out from under a
CONSUMED historical deployment authorization … a test that re-verifies a historical
authorization skips exactly the markets named here — named, never blanket — and
still binds every market that was not moved."*

`epochs.moved_by_later_work()` is the reader. It raises `KeyError` for an
authorization the registry does not list, deliberately: an unregistered
authorization must bind **every** market, which is the honest default.

### 2. What `reviewed_by` means

It is the work order that last reviewed and wrote the document — not a person, and
not the currently live launch. Proved by the writers: `miami_fl_deployment_pin_006.py:100`,
`fort_lauderdale_fl_deployment_pin_004.py:105` and `nashville_tn_launch_record_005.py:235`
all execute `pin["reviewed_by"] = WORK_ORDER`, i.e. each order signs the pin it
itself rewrote. `registration_data_only.py:1890` requires the value to be a
work-order id.

### 3. Which order last legitimately reviewed the record

`git log --follow tests/pettripfinder/pins/supersessions.json` → last touched at
`ba55ec81`, the Nashville launch, on 2026-09-10. `reviewed_by` has read
`PTF-NASHVILLE-TN-FOUNDER-AUTHORIZATION-AND-LIVE-LAUNCH-005` ever since, correctly:
that order really was the last to review it.

### 4. Which later launches should have advanced it

The maintenance rule is visible in the diff of every launch that touched the file.
At `ba55ec81` the Nashville launch did exactly three things, and `c6849f42`
(Lexington) and `0bf6384a` (Toledo) did the same three before it:

1. set `reviewed_by` to **its own** work order;
2. rewrote the outgoing live entry's note from *"The CURRENT live authorization…"*
   to *"Historical. It was the live authorization until …"*, stating whether
   anything had moved out from under it;
3. appended the newly-live authorization with its `moved_by_later_work` and the
   note *"The CURRENT live authorization…"*.

So the registry is a **chain**: every authorization that has been live since the
registry existed, in the order production consumed them, ending at the live one.
That is also what its membership is: `ptf-auth-047` (the first multi-market
authorization) plus a contiguous run from `ptf-auth-003-de669c40d811` — the
authorization live on the day `PTF-FACTORY-THROUGHPUT-HARDENING-001` created the
file — through `ptf-auth-nashville-005`.

Nineteen launches — Raleigh (2026-09-12) through Fort Lauderdale (2026-09-21) —
performed none of the three steps.

### 5. Which repair is correct

Not "one current reviewed record", and not an epoch change. **A sequence/history
update**: continue the chain, because the chain is what the document is and what
its notes assert. The scope is derivable, not chosen — the deployment records give
the order production consumed authorizations in, and the missing suffix is exactly
`raleigh-003 … fort-lauderdale-003`, 19 entries.

What each new entry's `moved_by_later_work` must hold was computed, never typed:
for every authorization, every row of its `release_contracts` was re-hashed against
the committed file. **Zero drift** on all 19 — and on every authorization from
`louisville-003` (2026-09-05) onward. So every new entry is `{}`, and the claim in
each note that "all N release contracts it bound still hash exactly" is measured,
not asserted.

The seven pre-registry authorizations (`012, 011, 008, 020, 032, 015, 006`,
consumed between `047` and `dayton-003`) were **left exactly as found**. They
predate the registry, no test re-verifies them, and their drift is already
attributed by the two entries that do cover that era. Adding them would mean
manufacturing history — which this order is forbidden to do, and does not need to.

### `reviewed_by`: old → new

```
OLD = PTF-NASHVILLE-TN-FOUNDER-AUTHORIZATION-AND-LIVE-LAUNCH-005
NEW = PTF-SUPERSESSIONS-LINEAGE-REPAIR-001
```

It is set to **this** order, not to `PTF-FORT-LAUDERDALE-FL-PRODUCTION-DEPLOYMENT-004`.
The Fort Lauderdale launch never reviewed this document; writing its name here
would be a false attestation of who did the reading, which is the one thing a
`reviewed_by` field exists to record. (The Fort Lauderdale order *does* correctly
own `reviewed_by` in `deployment_state.json`, which it did rewrite.)

---

## PHASE 4 — ALL 32 LIVE MARKETS AUDITED

Every live market: launch record and release contract reachable, supersession
lineage reachable, `moved_by_later_work` resolves, profile-pin check executes,
PASS.

```
asheville-nc  atlanta-ga  augusta-ga  boone-blowing-rock-nc  charleston-sc
charlotte-nc  cincinnati-oh  cleveland-akron-canton-oh  columbus-oh  dayton-oh
fayetteville-nc  fort-lauderdale-fl  grand-rapids-holland-mi  greenville-nc
indianapolis-in  jacksonville-nc  lexington-ky  louisville-ky  miami-fl
milwaukee-wi  nashville-tn  orlando-fl  outer-banks-nc  piedmont-triad-nc
pittsburgh-pa  raleigh-nc  richmond-va  savannah-ga  st-louis-mo  tampa-fl
toledo-oh  wilmington-nc
```

```
LIVE MARKETS AUDITED                   = 32
MISSING SUPERSESSION COVERAGE          = 0   (was 32 — the lookup raised for every one)
MISSING EPOCH COVERAGE                 = 0
PROFILE-PIN CHECKS PREVIOUSLY BYPASSED = 32
MARKETS SKIPPED BY SUPERSESSION LOOKUP = 0
PROFILE COUNT MISMATCHES               = 0
PINS WITH A NON-WORK-ORDER last_moved_by = none
```

No market was *silently* skipped: the lookup failed closed and took the whole test
with it, so the count of markets checked was 0, not 31. That is the fail-closed
behaviour working — what was missing was anything downstream that named the real
defect, which is what Phase 8 adds.

---

## PHASE 5 — THE DATA REPAIR

`tests/pettripfinder/pins/supersessions.json`, +97 / −2 lines:

* `reviewed_by` → `PTF-SUPERSESSIONS-LINEAGE-REPAIR-001`;
* `ptf-auth-nashville-005-c12b410ec833`'s note rewritten from CURRENT to Historical;
* 19 entries appended, `raleigh-003` → `fort-lauderdale-003`, each
  `moved_by_later_work: {}`, each with a note naming the deploy and authorization
  that replaced it and the number of contracts it still binds;
* `ptf-auth-fort-lauderdale-003-0ec5c6557d79` carries the CURRENT note.

28 entries, LF, UTF-8, ASCII, `indent=1` — the file's existing shape, and what
`test_pin_files_are_lf_utf8_json` requires.

The write was generated by a script that asserts every claim before emitting it and
refuses otherwise; the first run aborted on its own contiguity assertion (it had
assumed the pre-registry era belonged in the chain) and wrote nothing. Nothing else
was changed. Nothing was hand-typed.

---

## PHASE 6 — THE KEYERROR IS INTACT

`epochs.moved_by_later_work()` is **unmodified**. It still raises `KeyError` for an
unlisted authorization. `test_an_unregistered_authorization_binds_everything` still
passes, and a new negative test
(`test_a_missing_moved_by_later_work_lookup_raises_rather_than_defaulting`) pins the
behaviour against a registry fixture with the live entry removed.

No production implementation file was touched by this order.

---

## PHASE 7 — PROFILE-PIN COVERAGE

```
LIVE MARKETS EXPECTED                  = 32
LIVE MARKETS CHECKED                   = 32
MARKETS SKIPPED BY SUPERSESSION LOOKUP = 0      (target met)
PROFILE COUNT MISMATCHES               = 0
```

No mismatch surfaced, so no pin was classified and none was overwritten. The
contract-binding guard in `test_factory_throughput_001` also runs again and
re-hashes all 32 live release contracts byte for byte — all bind.

---

## PHASE 8 — NEGATIVE GUARD COVERAGE

Added to `tests/pettripfinder/contracts/test_market_state_pins.py` — the module
that already is "the ONE place the pins are held to the source". Deliberately **not**
a new module: a new module moves the committed suite inventory, which is a shared
report this order has no mandate to re-pin.

A module-level `chain_problems(registry, live_authorization_id)` derives what the
registry owes from the **deployment records**, so the two sides of the comparison
come from different documents. One implementation, used in both directions.

Positive (`TestTheSupersessionChainReachesProduction`):

1. the chain is complete, in deployment order, ending at the live authorization;
2. the live authorization resolves and 32 of 32 markets are checked;
3. `reviewed_by` names a work order;
4. no withheld market is treated as live or excused.

Negative (`TestTheSupersessionContractFailsClosed`) — nine cases, covering the
seven the order asked for. Every fixture is a deep copy written to `tmp_path` with
the module path monkeypatched; **no committed pin is mutated**.

| # | order's requirement | test |
|---|---|---|
| 1 | live market lacks supersession/epoch coverage | `test_a_registry_that_forgets_the_live_authorization_is_caught` |
| 2 | `reviewed_by` unreachable / not a work order | `test_a_reviewed_by_that_names_no_work_order_is_caught` |
| 2 | a mover that is not a work order | `test_a_mover_that_names_no_work_order_is_caught` |
| 3 | `moved_by_later_work` lookup missing | `test_a_missing_moved_by_later_work_lookup_raises_rather_than_defaulting` |
| 4 | chronology goes backward | `test_a_chain_listed_out_of_deployment_order_is_caught` |
| 5 | deployment and supersession lineage disagree | `test_an_entry_for_an_authorization_that_does_not_exist_is_caught` |
| 5 | …and disagree on the work order | `test_an_entry_whose_work_order_is_not_the_authorizations_is_caught` |
| 5 | an exemption claimed for a market that never moved | `test_a_market_excused_without_having_moved_is_caught` |
| 6 | a market profile pin cannot be reached | `test_a_live_market_with_no_pin_fails_rather_than_defaulting` |
| 7 | a withheld market treated as current live | `test_a_withheld_market_named_as_live_is_caught` |

Four of the negative tests drive the **real** guards
(`TestSupersessionRegistry`, `TestDeploymentPinsAgreeWithTheSource`) against the bad
fixture under `pytest.raises`, rather than restating their logic.

`NEGATIVE GUARD CASES = 10` (across 7 requirements), `POSITIVE CONTRACT TESTS = 4`.

---

## PHASE 9 — TARGETED TEST RUN

One pytest process. No parallel suites. No demo-media suites. No broad regression.
`-m "not slow"`.

Modules: `contracts/test_market_state_pins.py`, `test_factory_throughput_001.py`,
`test_deployment_authorization_047.py`, `test_nashville_tn_launch_005.py`,
`test_toledo_oh_launch_003.py`, `test_participation_lineage_contract_006.py`,
`test_per_market_release_contracts.py`, `test_release_composition_contract_006.py`.

```
COLLECTED   = 1795
PASSED      = 1786
FAILED      = 8
SKIPPED     = 1
RUNTIME     = 4084.64 s (1:08:04)
PEAK MEMORY = 45.9 MB (process peak working set)
```

The contract module alone: **196 passed, 1 failed** (was 180 passed / 3 failed).

---

## PHASE 10 — DIFFERENTIAL

Baseline run in a detached worktree at the untouched base `09851d50`
(`C:\t\ssbase`), same three modules that still carry failures, same flags:
**11 failed, 233 passed, 1 skipped in 18.25 s, peak 76.3 MB.**

| node id | base | after | class |
|---|---|---|---|
| `test_market_state_pins::…::test_live_profile_counts_are_the_market_pins` | FAIL | **PASS** | FIXED |
| `test_market_state_pins::…::test_the_live_authorization_has_nothing_moved` | FAIL | **PASS** | FIXED |
| `test_factory_throughput_001::…::test_the_live_authorization_binds_every_market_exactly` | FAIL | **PASS** | FIXED |
| `test_market_state_pins::…::test_live_block_is_the_latest_deployment_record` | FAIL | FAIL | PRE_EXISTING (Phase 11) |
| `test_factory_throughput_001::TestTheHarness::test_the_committed_inventory_reproduces_from_the_suite` | FAIL | FAIL | PRE_EXISTING |
| `test_nashville_tn_launch_005::…::test_the_live_release_is_the_nashville_deploy` | FAIL | FAIL | PRE_EXISTING |
| `test_nashville_tn_launch_005::…::test_lexington_and_every_other_market_survived_unchanged` | FAIL | FAIL | PRE_EXISTING |
| `test_nashville_tn_launch_005::…::test_participation_carries_the_founder_decision_for_nashville_only` | FAIL | FAIL | PRE_EXISTING |
| `test_nashville_tn_launch_005::…::test_it_verifies_against_the_repository_it_names` | FAIL | FAIL | PRE_EXISTING |
| `test_nashville_tn_launch_005::…::test_the_live_pin_agrees_and_the_verifier_is_silent` | FAIL | FAIL | PRE_EXISTING |
| `test_nashville_tn_launch_005::…::test_the_opening_is_recorded_as_consumed_and_names_what_it_replaced` | FAIL | FAIL | PRE_EXISTING |

```
REPAIR_CAUSED       = 0
PRE_EXISTING        = 8
CURRENT_REAL_DEFECT = 0
UNRESOLVED          = 0
FIXED               = 3
```

Two of the pre-existing eight deserve a note, because both could be mistaken for
this order's doing:

* **The suite inventory pin.** It fails with `HISTORICAL_COHORT_INVARIANT 908 != 907`
  — the **identical** numbers at base and after. The 14 tests added here move it by
  zero, because the scanner counts numeric pin sites and the new tests assert
  against derived values, not literals. The pin was already one short at base;
  re-pinning a shared generated report requires an order that names what it moved
  (`test_inventory_repin_006.py` is the pattern), and this is not it.
* **The six Nashville-launch failures.** That suite asserts Nashville's deploy is
  the live one. It stopped being true at Raleigh, nineteen launches ago. Its
  supersession assertions — `TestTheSupersessionRegistryNamesTheLiveAuthorization`,
  which requires `registry[nashville]["moved_by_later_work"] == {}` and its
  `work_order` — **still pass** after this repair, by design: the chain rewrote that
  entry's prose and left its data alone.

The other five modules in the targeted run carry no failures at all after the
repair, so there is nothing in them to classify.

---

## PHASE 11 — THE FORT LAUDERDALE `work_order` FINDING

Inspected only. Not repaired here.

```
FORT LAUDERDALE WORK_ORDER SEMANTICS = A (valid schema semantics) + C (ambiguously
                                       named) + D (the test misinterprets it).
                                       NOT B — the record is not stale or incorrect.
REPAIR NEEDED                        = YES, but in the TEST, not in any record
SEPARATE ORDER NEEDED                = YES
```

The record is right, and it already carries both facts:

```
ptf-deploy-fort-lauderdale-004-6ab1a035c7ef3b14a23a4ec6.json
  work_order                        = PTF-FORT-LAUDERDALE-FL-FOUNDER-LAUNCH-AUTHORIZATION-003
  deployer.work_order               = PTF-FORT-LAUDERDALE-FL-PRODUCTION-DEPLOYMENT-004
  deployer.authorizing_work_order   = PTF-FORT-LAUDERDALE-FL-FOUNDER-LAUNCH-AUTHORIZATION-003
```

`deployment_authorization.build_deployment_record()` sets the top-level field as
`("work_order", auth.get("work_order"))` — by construction it is the **authorizing**
order, carried forward from the authorization it consumed. Verified across the
whole history: for all **35** deployment records, `record["work_order"] ==
authorization["work_order"]`, without exception.

`deployment_state.json`'s `live.deployed_by` is a different fact — the order that
performed the deploy. For 33 launches authorize and deploy were the same order, so
nothing distinguished them. They first diverged at **Miami** (`fbaf6f73`,
2026-09-20, `deployed_by = PTF-MIAMI-FL-PRODUCTION-DEPLOYMENT-006`), and again at
Fort Lauderdale. So `test_live_block_is_the_latest_deployment_record` has been
failing for **two** launches, not one.

The correct fix is one line in the test: compare `record["deployer"]["work_order"]`
with `live.deployed_by`, and `record["work_order"]` with the authorization's own
work order. That is a separate defect from the supersession lineage, on a different
document, and it is separable — so it is reported, not taken. Suggested follow-up:
**PTF-DEPLOYMENT-RECORD-WORK-ORDER-SEMANTICS-001**.

---

## PHASE 12 — PRODUCTION DELTA SAFETY

```
HOTEL DATA CHANGES          = 0
MARKET DATA CHANGES         = 0
PROFILE DATA CHANGES        = 0
LIVE PARTICIPATION CHANGES  = 0
AUTHORIZATION CHANGES       = 0
DEPLOYMENT RECORD CHANGES   = 0
RELEASE FACTORY CODE CHANGES= 0
CURRENT LIVE SITE CHANGES   = 0
```

`git diff --stat 09851d50`:

```
 atlas-dashboard/tests/pettripfinder/contracts/test_market_state_pins.py | 244 +++++
 atlas-dashboard/tests/pettripfinder/pins/supersessions.json             |  99 +++--
 2 files changed, 341 insertions(+), 2 deletions(-)
```

Both are under `tests/`. Nothing under `deploy/`, `launch_packages/`, `scripts/`,
`engines/`, `services/` or `templates/` was written.

---

## PHASE 13 — FINAL CURRENT-LIVE VERIFICATION

Resolver re-run after the repair:

```
deploy      = 6ab1a035c7ef3b14a23a4ec6      (unchanged)
auth        = ptf-auth-fort-lauderdale-003-0ec5c6557d79
source      = 0cc2817b
bundle      = 0ec5c655
sitemap     = e81961ae
markets     = 32      profiles = 2375
rel-index   = 2646    served   = 2711
problems    = []
fort-lauderdale-fl live = True
detroit-ann-arbor-mi withheld = True
```

Host: `https://pettripfinder.com/sitemap.xml` HTTP 200, 2711 routes,
sha256 `e81961ae76454ce608fcb39624d5147c8779f52b269faab9449138397cb8fa3d` —
byte-identical to the authorized sitemap and to the Phase 1 read.

**No deployment was performed.**

---

## FINAL ANSWERS

```
 1. CURRENT LIVE DEPLOYMENT               = 6ab1a035c7ef3b14a23a4ec6
 2. CURRENT LIVE MARKETS                  = 32
 3. SUPERSESSIONS OLD REVIEWED_BY         = PTF-NASHVILLE-TN-FOUNDER-AUTHORIZATION-AND-LIVE-LAUNCH-005
 4. SUPERSESSIONS NEW REVIEWED_BY         = PTF-SUPERSESSIONS-LINEAGE-REPAIR-001
 5. SUPERSESSION SEMANTICS                = a CHAIN of every consumed authorization that has
                                            been live since the registry was created, in the
                                            order production consumed them, each naming the
                                            markets a later order moved out from under it
                                            (named, never blanket), ending at the live one
 6. LIVE MARKETS AUDITED                  = 32
 7. MARKETS PREVIOUSLY WITHOUT COVERAGE   = 32
 8. MISSING EPOCH KEYS BEFORE             = 19 consumed authorizations (raleigh-003 … fort-lauderdale-003)
 9. MISSING EPOCH KEYS AFTER              = 0
10. PROFILE-PIN CHECKS PREVIOUSLY BYPASSED= 32
11. PROFILE-PIN CHECKS NOW EXECUTED       = 32
12. PROFILE COUNT MISMATCHES              = 0
13. SUPERSESSION FILES CHANGED            = 1
14. TEST FILES CHANGED                    = 1
15. PRODUCTION CODE FILES CHANGED         = 0
16. DEPLOYMENT RECORDS CHANGED            = 0
17. NEGATIVE GUARD CASES                  = 10 (covering all 7 required)
18. TARGETED TESTS COLLECTED              = 1795
19. TARGETED TESTS PASSED                 = 1786
20. TARGETED TESTS FAILED                 = 8
21. TARGETED TESTS SKIPPED                = 1
22. REPAIR_CAUSED FAILURES                = 0
23. PRE_EXISTING FAILURES                 = 8
24. CURRENT_REAL_DEFECTS                  = 0
25. UNRESOLVED                            = 0
26. FTL DEPLOYMENT WORK_ORDER SEMANTICS   = valid by schema (the authorizing order, copied from
                                            the authorization); the deploying order is already
                                            recorded in deployer.work_order; the test conflates them
27. FTL WORK_ORDER SEPARATE REPAIR NEEDED = YES — test-only, suggested
                                            PTF-DEPLOYMENT-RECORD-WORK-ORDER-SEMANTICS-001
28. CURRENT LIVE MODIFIED                 = NO
29. DEPLOYMENT PERFORMED                  = NO
30. FORT LAUDERDALE STILL LIVE            = YES
31. DETROIT STILL WITHHELD                = YES
32. origin == HEAD                        = YES
33. tree clean                            = YES
34. READY TO RESUME MARKET EXPANSION      = YES
```

---

```
PTF SUPERSESSIONS LINEAGE REPAIR = PASS
MISSING LIVE SUPERSESSION COVERAGE = 0
PROFILE-PIN GUARD ACTIVE FOR CURRENT LIVE = YES
REPAIR-CAUSED FAILURES = 0
UNRESOLVED FAILURES = 0
PRODUCTION CODE CHANGED = NO
DEPLOYMENT RECORDS CHANGED = NO
CURRENT LIVE MODIFIED = NO
DEPLOYMENT PERFORMED = NO
READY TO RESUME MARKET EXPANSION = YES
```
