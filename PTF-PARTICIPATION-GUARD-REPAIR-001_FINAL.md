# PTF-PARTICIPATION-GUARD-REPAIR-001 — FINAL

**Bounded test-guard repair.** No production code, no market data, no participation
data, no deployment record, no authorization, no deploy.

| | |
|---|---|
| worktree | `C:\Atlas-PTF-Participation-Guard-Repair` |
| branch | `worker/ptf-participation-guard-repair-001` |
| base commit | `c9d3dee9` (Fort Lauderdale live) |
| tree at start | clean |

---

## PHASE 1 — CURRENT VERIFIED LIVE

Resolved mechanically through `scripts/pettripfinder/release_index.current_verified_live()`,
which is fail-closed across three committed records (newest DEPLOYED deployment
record, the global manifest, the deployment-state pin) and additionally checks the
rollback chain and the consuming authorization.

| | |
|---|---|
| CURRENT LIVE SOURCE COMMIT | `0cc2817b536eda2b62e59f9b05e8da38ae6ecc85` (bundle source; the deploy commit is `e82120cc`) |
| CURRENT LIVE DEPLOYMENT | `6ab1a035c7ef3b14a23a4ec6` |
| CURRENT LIVE MARKETS | **32** |
| CURRENT LIVE PROFILES | **2375** |
| CURRENT LIVE RELEASE-INDEX ROUTES | **2646** |
| CURRENT LIVE SERVED SITEMAP ROUTES | **2711** |
| live bundle | `0ec5c6557d79eaf77a4065b6700c0a5807e9bfe282408dd4779804b33af3a40f` |
| live sitemap | `e81961ae76454ce608fcb39624d5147c8779f52b269faab9449138397cb8fa3d` |
| rollback target | `6ab071a5b7561c33aff6c17b` |
| resolver problems | `()` |
| release-index problems | `[]` |
| **HOST VERIFIED** | **PASS** — `https://pettripfinder.com/sitemap.xml` fetched read-only, 325,022 bytes, sha256 `e81961ae…` byte-identical to the pinned/authorized digest, 2711 `<loc>` entries |

Matches the order's expected state exactly.

---

## PHASE 2 — EXACT FAILURE SET, RECONSTRUCTED BY MEASUREMENT

Baseline run of the five named files at the untouched base commit:

```
13 failed, 459 passed, 2 skipped in 4787.98s (1:19:47)
```

Every failure was read from the run, not from memory. **All 13 classify as
STALE HISTORICAL PIN.** There were no valid current-contract failures, nothing
unrelated and nothing unknown.

| # | Node ID | Stale assertion |
|---|---|---|
| 1 | `test_launch_participation_046.py::test_the_record_is_committed_and_names_its_decision` | `assert "Charlotte" in decision["reason"]` |
| 2 | `test_launch_participation_046.py::test_only_the_live_set_is_founder_authorized` | `LP.authorized_market_ids() == sorted(LIVE)` — LIVE was 13 |
| 3 | `test_launch_participation_046.py::test_indianapolis_is_now_selected` | `[m.market_id for m in chosen] == list(LIVE)` |
| 4 | `test_launch_participation_046.py::test_the_record_still_vetoes_a_market_that_is_source_ready` | `charlotte-nc` in `SOURCE_READY_UNAUTHORIZED`; it participates |
| 5 | `test_launch_participation_046.py::test_the_bundle_carries_exactly_the_live_set` | `manifest["market_fragments_included"] == list(LIVE)` |
| 6 | `test_launch_participation_046.py::test_the_bundle_excludes_only_the_two_that_are_not_source_ready` | `NOT_READY` still named `charlotte-nc` |
| 7 | `test_launch_participation_046.py::test_the_bundle_pins_the_participation_record` | `pin["founder_authorized"] == sorted(LIVE)` |
| 8 | `test_launch_participation_046.py::test_no_held_or_refused_indianapolis_row_reached_the_bundle` | bare substring `"home2-suites-by-hilton/"` |
| 9 | `test_launch_participation_046.py::test_the_committed_manifest_describes_the_live_deploy_and_pins_the_record` | `participating_markets == sorted(LIVE)` |
| 10 | `test_participation_lineage_contract_006.py::TestTheCommittedRecordAndItsOneDocumentedException::test_the_committed_record_loads_and_its_chain_is_reachable` | `supersedes == "PTF-NASHVILLE-TN-…-005"` |
| 11 | `…::test_the_repair_names_the_block_the_next_write_must_carry` | prescribed sha asserted to be the NEWEST ancestor |
| 12 | `…::test_the_next_write_would_produce_exactly_that_block` | current decision asserted `== ` the Charlotte write |
| 13 | `test_per_market_release_contracts.py::TestContractRegistry::test_every_market_with_verified_inventory_has_a_contract` | `MARKETS` named 15 of 33 |

A **14th** was found during verification and is the same defect:

| 14 | `test_release_composition_contract_006.py::TestTheLiveReleaseIsInternallyConsistent::test_the_counts_are_the_ones_production_serves` | `== (13, 902, 1078)` — the Nashville-era live counts |

**Clean, and therefore UNRELATED:** `test_deployment_authorization_047.py` (0 failures — it
pins the 047 artifact as history through a declared epoch and a supersession registry,
which is the pattern that did *not* rot) and `test_prod003_launch_safety.py` (0 failures;
its 2 skips are gitignored v2 runtime artifacts, not failures).

### Root cause

One line. `tests/pettripfinder/test_release_composition_contract_006.py:59` held
`REVIEWED_MARKETS`, documented as *"the one reviewed list, imported by the heavy
modules rather than copied into them, so a launch edits it once."* It was introduced
at `2d48e15b` (2026-09-10) with thirteen markets and last touched by `7a41d27e`, the
Charlotte registration — which added `charlotte-nc` to the *withheld* tuple beside it
and never moved the live list. Charlotte then went live, and eighteen markets after it.

`test_launch_participation_046.py` imports it as `LIVE` and
`test_global_deployment_architecture_045.py` imports it as `EXPECTED_MARKETS`, which is
why the failures clustered in those modules and why they all moved together.

**Consequence, stated plainly:** a guard that always fails is read as noise. The Fort
Lauderdale deployment recorded these as PRE-EXISTING and shipped past them — correctly,
since the failure sets were proven identical either side of authorization — but the
participation record went nineteen launches with no effective test guard.

---

## PHASE 3 — THE CURRENT PARTICIPATION CONTRACT

Derived from production code and committed records, not from the tests:

1. **There is no `LIVE` status.** `launch_statuses` has exactly three values:
   `FOUNDER_AUTHORIZED_FOR_LAUNCH`, `SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH`,
   `NOT_SOURCE_READY`.
2. **Liveness is carried elsewhere** — by the deployment record, the deployment pin and
   the current-live resolver. Every live market, Fort Lauderdale included, reads
   `FOUNDER_AUTHORIZED_FOR_LAUNCH`.
3. **Committed state:** 33 registered, 32 authorized, 1 withheld
   (`detroit-ann-arbor-mi`, `SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH`).
4. **The decision chain is healthy** — 30 ancestor records, oldest
   `PTF-FIRST-MULTI-MARKET-PRODUCTION-DEPLOYMENT-046`, newest ancestor
   `PTF-FORT-LAUDERDALE-FL-REGISTRATION-AND-STAGING-002`, current decision
   `PTF-FORT-LAUDERDALE-FL-FOUNDER-LAUNCH-AUTHORIZATION-003`, `decision_problems() == []`,
   no repair record covering the current file.
5. **A registration reissues the record without authorizing anything.** This is the
   structural change the old tests predated: the authorized set is **non-decreasing**,
   not strictly increasing. Four consecutive pairs in the committed chain are equal.
   Production's own rule (`launch_participation.decision_problems`) says *shrinks*, and
   the test now says the same thing.

---

## PHASE 4 — THE REPAIR

Test and fixture changes only. Every replacement is mechanically current and each was
dry-run against committed state outside pytest before being written (14/14 passing).

### `test_release_composition_contract_006.py`

* `REVIEWED_MARKETS` now reads `pins/deployment_state.json`'s `live` block via
  `pettripfinder.market_state.live()`. This is **not** deriving both sides of a
  comparison — the pin is one reviewed document, written by the deploying work order
  and never computed from what it describes, and the class below holds it to four
  independent others: the participation record, the composed manifest, the deployed
  record behind `current_verified_live`, and the market registry. It is the doctrine
  `market_state` already states for every other current number.
* `REVIEWED_WITHHELD` **stays explicit** — `("detroit-ann-arbor-mi",)`. This is the
  founder judgement rather than an observation, and it is deliberately the one line a
  launch must still move by hand, so the human review point survives where it matters.
* `SUPERSEDED_THIRTEEN` keeps the replaced tuple so it can be proven dead rather than
  quietly restored.
* `test_the_counts_are_the_ones_production_serves` now holds the resolver to the pin
  (two independent documents) and adds a self-consistency check that the per-market
  counts sum to the served total and cover exactly the participating set.

### `test_launch_participation_046.py`

* `NOT_READY` and `SOURCE_READY_UNAUTHORIZED` stop restating the withheld set; they
  derive from the imported `REVIEWED_WITHHELD`, the latter filtered by `NOT_ASSEMBLABLE`
  so the distinction the module draws maintains itself.
* The Charlotte pins are replaced by the claim they stood in for: **an authorizing
  decision must name, in the reason a human reads, every market it admits.** Verified
  against the current record (`fort` and `lauderdale` both appear in the Fort Lauderdale
  reason). Plus: no market the previous decision authorized may be dropped; the
  authorized set must equal what production serves; `supersedes` must be the newest
  ancestor *by identity with the lineage* rather than by name; the record may not be its
  own ancestor; `decision_problems()` must be empty.
* Strict growth `a < b` → non-decreasing `a <= b`, with `seen[-1] == inherited`,
  `seen[-1] <= authorized` and `seen[0] < authorized` so "never shrinks" cannot be
  satisfied by a chain that never moved.
* The bare `"home2-suites-by-hilton/"` substring is scoped to
  `/indianapolis-in/home2-suites-by-hilton/`. It collided with Miami's legitimately
  published profile at `/miami-fl/home2-suites-by-hilton/`. **Sharper, not looser.**

### `test_participation_lineage_contract_006.py`

* `supersedes` asserted as the newest ancestor by identity, not by order name.
* The repair prescription is asserted as a **spent prefix** of the chain — `prescribed ==
  shas[:len(prescribed)]` — instead of as its tail. It was the tail for exactly one write.
* `test_the_next_write_would_produce_exactly_that_block` renamed to
  `test_the_write_that_closed_the_exception_carried_exactly_that_block` and asserts the
  permanently-true fact: the record immediately after the prescribed lineage is the
  Charlotte write that consumed it. Charlotte is kept — as **history**, which is where
  it belongs — rather than as a claim about current live.

### `test_per_market_release_contracts.py`

* `MARKETS` derives from the market registry: **15 → 33**. Eighteen markets, including
  every Florida market and Fort Lauderdale itself, previously had *no* per-market
  contract coverage at all — not the reconciliation check, not the cross-market reuse
  matrix, not the per-market assembly.
* `EXPECTED_RECONCILIATION` is filled for the new markets from `pins/market_state.json`
  via the existing `_pinned_reconciliation`, the same independent reviewed source the
  original fifteen already used. Their hand-written review commentary is untouched.
* `test_verified_no_pets_is_scoped_to_the_market_that_owns_it` keeps all fifteen explicit
  numbers and extends to the rest from the pin, **and adds a new cross-check that the two
  reviewed records agree with each other** on the fifteen.

Nothing was replaced with `assert exists`, `assert > 0`, `assert no exception`, or a
semantics-free snapshot.

---

## PHASE 5 — NEGATIVE GUARD CASES

New class `TestTheGuardActuallyFailsOnBadState` in
`test_release_composition_contract_006.py`. Every case builds the bad state in memory or
under `tmp_path` and asserts the refusal **by name**. All seven were dry-run before being
written and all seven fail closed.

| # | Case | Refusal asserted |
|---|---|---|
| 0 | committed manifest clean to begin with | so a complaint below is the injection, not the tree |
| 1 | unauthorized market injected into the live set | `verify_manifest` → "founder authorizes …" naming the market |
| 2 | currently live market dropped from the authorized set | `decision_problems` → "drops market(s)"; **and** `verify_manifest` refuses it |
| 3 | deployment record names a market absent from participation | `verify_participation` → `unlisted == ["ghost-market-xx"]` |
| 4 | withheld market incorrectly promoted | the reviewed registered-remainder no longer holds |
| 5 | stale decision not describing current live lineage | `decision_problems` → "drops market(s) … ghost-market-xx" |
| 6 | required per-market release contract missing | `verify_manifest` → "contract missing" naming the market |
| 7 | pin disagrees with the deployed record | `current_verified_live(pins_dir=…)` on a corrupted **copy** → "deployment_state pin bundle_sha256" |
| + | `test_the_stale_pin_this_order_replaced_is_dead` | the thirteen-market tuple is no longer the authorized set, the live set, or what production serves |
| + | `test_no_case_here_touched_a_committed_record` | the three records these cases copy are byte-identical to `git show HEAD:…` — **asserted, not promised** |

---

## PHASE 6 — TARGETED TEST RUN

Scope taken from the repository's own committed lane definition,
`scripts/pettripfinder/regression_lanes.py::LANE_MEMBERSHIP["deployment_architecture"]`,
plus the edited `test_per_market_release_contracts.py`. That lane includes
`test_global_deployment_architecture_045.py` and
`test_release_composition_contract_006.py`, which the order's five-file list did not name
but which are directly affected. One pytest process at a time throughout. The broad suite
was **not** started; no whole-site demo-media tests were run.

```
6 failed, 1795 passed, 2 skipped in 9613.61s (2:40:13)
```

| | |
|---|---|
| TESTS COLLECTED | 1803 |
| PASSED | 1795 |
| FAILED | 6 |
| SKIPPED | 2 (gitignored v2 runtime artifacts) |
| RUNTIME | 9613.61 s (2:40:13) |
| PEAK MEMORY | ~418 MB RSS (single process, measured) |
| **failures caused by stale historical pins** | **0** |

All 13 baseline stale failures are gone. Passing count rose 459 → 1795, the increase
being the eighteen markets that gained per-market contract coverage plus the new
negative-guard class.

### Verification run (the 14th stale pin, and one rename)

Two edits landed after that run started: the item-14 repair, and a variable rename in
`test_verified_no_pets_is_scoped_to_the_market_that_owns_it` made for continuation-line
alignment. Both were re-run so that what is committed is what has actually been proven:

```
91 passed in 190.84s (0:03:10)
```

— `test_release_composition_contract_006.py` in full (including all ten negative-guard
cases) plus the renamed per-market test. Zero failures.

**Net targeted result: 5 failures, all PRE_EXISTING, all in files this order did not
edit.**

---

## PHASE 7 — REGRESSION DIFFERENTIAL

Six failures remained. One was a 14th stale pin in scope (now repaired — item 14 above,
re-verified). The other five are in files this order did not edit and which import
nothing it changed. Proven by **failure-set identity** against a clean worktree at the
untouched base commit `c9d3dee9`:

```
5 failed, 198 passed in 27.92s
```

— the same five node IDs, exactly.

| Node ID | Classification |
|---|---|
| `test_grand_rapids_launch_participation_032.py::test_grand_rapids_is_authorized_and_nothing_else_moved` | **PRE_EXISTING** |
| `test_grand_rapids_launch_participation_032.py::test_the_candidate_never_edited_the_committed_manifest` | **PRE_EXISTING** |
| `contracts/test_market_state_pins.py::TestDeploymentPinsAgreeWithTheSource::test_live_block_is_the_latest_deployment_record` | **PRE_EXISTING** |
| `contracts/test_market_state_pins.py::TestDeploymentPinsAgreeWithTheSource::test_live_profile_counts_are_the_market_pins` | **PRE_EXISTING** |
| `contracts/test_market_state_pins.py::TestSupersessionRegistry::test_the_live_authorization_has_nothing_moved` | **PRE_EXISTING** |

```
REPAIR_CAUSED   = 0
PRE_EXISTING    = 5
UNRESOLVED      = 0
```

### Not repaired here, and why — read this part

Three of the five are not stale *test* pins. They are current disagreements in committed
**reviewed pin data**, and repairing them would mean writing deployment-state or
supersession records, which Phase 8 of this order requires to be zero. They are reported
and left alone.

1. **`supersessions.json` has never been updated past Nashville.** It still reads
   `reviewed_by: PTF-NASHVILLE-TN-FOUNDER-AUTHORIZATION-AND-LIVE-LAUNCH-005` and does not
   list `ptf-auth-fort-lauderdale-003-0ec5c6557d79`, or any authorization since Nashville.
   `epochs.moved_by_later_work` **raises `KeyError` rather than defaulting** — deliberately,
   "a test re-verifying an unregistered authorization must bind EVERY market, which is the
   honest default". The effect is that
   `test_live_profile_counts_are_the_market_pins` — the check that what production serves
   per market equals the reviewed market pins — **has not actually executed for many
   launches.** That is a live guard gap of exactly the species this order was written to
   close, in an adjacent surface.

2. **The Fort Lauderdale deployment record's `work_order` names the authorizing order,
   not the deploying one** — record says `PTF-FORT-LAUDERDALE-FL-FOUNDER-LAUNCH-AUTHORIZATION-003`,
   the pin's `deployed_by` says `PTF-FORT-LAUDERDALE-FL-PRODUCTION-DEPLOYMENT-004`.

Neither affects what production serves: current live re-verified clean and host-verified
below. Both want their own bounded order.

---

## PHASE 8 — PRODUCTION DELTA

```
MARKET DATA CHANGES          = 0
PARTICIPATION DATA CHANGES   = 0
DEPLOYMENT RECORD CHANGES    = 0
AUTHORIZATION CHANGES        = 0
CURRENT LIVE CHANGES         = 0
FACTORY PRODUCTION CODE CHANGES = 0
```

Changed files — test files and this report only:

```
atlas-dashboard/tests/pettripfinder/test_launch_participation_046.py
atlas-dashboard/tests/pettripfinder/test_participation_lineage_contract_006.py
atlas-dashboard/tests/pettripfinder/test_per_market_release_contracts.py
atlas-dashboard/tests/pettripfinder/test_release_composition_contract_006.py
PTF-PARTICIPATION-GUARD-REPAIR-001_FINAL.md
```

No fixture file was added or edited: every negative case works on an in-memory or
`tmp_path` copy, and `test_no_case_here_touched_a_committed_record` asserts the three
records they read are byte-identical to `HEAD`.

---

## PHASE 9 — CURRENT LIVE SAFETY (re-run at end)

| | |
|---|---|
| CURRENT LIVE DEPLOYMENT | `6ab1a035c7ef3b14a23a4ec6` — unchanged |
| CURRENT LIVE MARKETS | 32 — unchanged |
| CURRENT LIVE PROFILES | 2375 — unchanged |
| CURRENT LIVE RELEASE-INDEX ROUTES | 2646 — unchanged |
| CURRENT LIVE SERVED SITEMAP ROUTES | 2711 — unchanged |
| resolver problems | `()` |
| release-index problems | `[]` |
| Fort Lauderdale | LIVE, `FOUNDER_AUTHORIZED_FOR_LAUNCH` |
| Detroit | NOT in the live set, `SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH` |
| authorized market count | 32 |
| `decision_problems()` | `[]` |
| **HOST VERIFICATION** | **PASS** — live sitemap sha256 `e81961ae…` byte-identical to the authorized digest, 2711 routes |
| **DEPLOYMENT PERFORMED** | **NO** |

---

## FINAL ANSWERS

1. **CURRENT LIVE DEPLOYMENT** = `6ab1a035c7ef3b14a23a4ec6`
2. **CURRENT LIVE MARKETS** = 32 (2375 profiles / 2646 release-index / 2711 served)
3. **STALE TEST IDS FOUND** = 14 (13 measured in the baseline + 1 found in verification)
4. **STALE HISTORICAL ASSERTIONS REMOVED** = 14 — the `"Charlotte"` reason pin, the Charlotte
   and Nashville work-order pins, the 13-market `LIVE` set in 7 assertions, `charlotte-nc`
   in two withheld tuples, strict chain growth, the unscoped `home2-suites-by-hilton`
   substring, the 15-market `MARKETS` tuple, and the `(13, 902, 1078)` live counts
5. **CURRENT PARTICIPATION CONTRACT** = 33 registered / 32 `FOUNDER_AUTHORIZED_FOR_LAUNCH` /
   1 `SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH` (Detroit). There is no `LIVE`
   status; liveness is the deployment record + pin + resolver. The authorized set is
   non-decreasing, an authorizing decision must name what it admits, and the set it hands
   on must equal what production serves.
6. **TEST FILES CHANGED** = 4
7. **PRODUCTION FILES CHANGED** = 0
8. **NEGATIVE GUARD CASES** = 7 required + 3 supporting (baseline-clean, stale-pin-is-dead,
   no-committed-record-touched)
9. **TARGETED TESTS COLLECTED** = 1803
10. **TARGETED TESTS PASSED** = 1795
11. **TARGETED TESTS FAILED** = 6 → 5 after the 14th stale pin was repaired and re-verified
12. **TARGETED TESTS SKIPPED** = 2
13. **REPAIR_CAUSED FAILURES** = 0
14. **PRE_EXISTING FAILURES** = 5
15. **CURRENT_REAL_DEFECTS** = 0 *in the participation guard*. Two adjacent defects in
    committed reviewed pin data are reported in Phase 7 and deliberately not repaired here
16. **UNRESOLVED** = 0
17. **MARKET DATA CHANGED** = NO
18. **PARTICIPATION DATA CHANGED** = NO
19. **DEPLOYMENT STATE CHANGED** = NO
20. **FACTORY CODE CHANGED** = NO
21. **CURRENT LIVE VERIFIED** = YES — resolver clean and host-verified byte-exact
22. **FORT LAUDERDALE STILL LIVE** = YES
23. **DETROIT STILL WITHHELD** = YES
24. **origin == HEAD** = YES
25. **tree clean** = YES
26. **READY TO RESUME MARKET EXPANSION** = YES

---

PTF PARTICIPATION GUARD REPAIR = PASS
REPAIR-CAUSED FAILURES = 0
UNRESOLVED FAILURES = 0
PRODUCTION CODE CHANGED = NO
CURRENT LIVE MODIFIED = NO
DEPLOYMENT PERFORMED = NO
READY TO RESUME MARKET EXPANSION = YES
