# PTF-NASHVILLE-TN-FINAL-REGRESSION-CLOSURE-004 — FINAL

The shared-pin question is answered by measurement: **A. The classification is
correct and no classifier correction was made.** The recovery's one broad
regression was genuinely required, was executed, and closed at
TRUE_NEW_FAILURE_AFTER_CLOSURE = 0. **No second broad run was needed** and none
was launched.

Nashville's authority is untouched: 180 census, 79 published, 18
verified-no-pets, 4 held. Nothing was authorized and nothing was deployed.

---

## THE QUESTION

Regression V2 classifies `tests/pettripfinder/pins/market_state.json` as
SHARED_TEST_STATE, which turns TEST_EXPECTATION_CHANGE's conditional full
regression into a yes. Is that:

- **A** — a legitimate shared semantic change that truly requires one broad run, or
- **B** — a generated current-state view already covered by the sealed package
  and the fast release contract, which should not widen a data-only release?

Four measurements decide it. None of them reads the classifier's own comment and
calls that a proof.

---

## MEASUREMENT 1 — IS IT GENERATED?

| | |
|---|---|
| Writers of the pin | **0** |
| Write calls correctly **not** counted | 2 |
| Reading test modules | 40 |

Every `.py` under `scripts/` and `tests/` was parsed, not grepped, looking for a
`json.dump` or `write_text` whose target resolves to the pin.

**The first pass of this detector was wrong and the correction is worth
recording.** It reported two writers. Both are fixtures in
`test_atlas_throughput_002` writing `"{}"` and `'{"x": 1}'` into a temporary
package a test builds to exercise the classifier — they target a throwaway tree,
not the repository's pin. Reporting them as writers would have recorded a
generation path that does not exist, so the detector now resolves the leftmost
identifier of each target expression and separates fixture roots from real ones,
listing both.

With no writer, there is no generation path. The pin is an authored, reviewed
expectation — which its owning module states outright: *"It is not a derivation.
Nothing here opens a policy package, a census or a manifest."* **B's premise is
false.**

---

## MEASUREMENT 2 — WHAT DOES IT ACTUALLY CONTROL?

Measured by experiment rather than argued from an import graph. Hold the whole
tree at HEAD, revert **only** the `nashville-tn` entry to its pre-recovery
values, run all 41 pin-consuming modules, and subtract a control run of the same
modules at HEAD.

| | |
|---|---|
| Probe failures (pin reverted) | 18 |
| Control failures (HEAD) | 9 |
| **Controlled by the pin entry** | **9** |

The control matters. Of the probe's 18, five are in the committed `f75aa95`
baseline and four fail at HEAD anyway — a node that fails either way is not
controlled by the pin, and counting it would have inflated the radius by double.

Every one of the 9 control failures is accounted for: 5 baseline, 4 in the
recovery order's own PRE_EXISTING_AT_PARENT set. **Zero unaccounted.** The 41
pin-consuming modules are otherwise green at HEAD — 1,808 passed.

---

## MEASUREMENT 3 — DOES IT CROSS MARKETS?

| | |
|---|---|
| Parameterised `[nashville-tn]` | 7 |
| **Registry-wide** | **2** |

```
test_factory_throughput_001 :: test_every_market_pin_is_held_to_its_release_contract
test_global_assembler       :: test_current_live_inventory_preserves_all_assemblable_market_profiles
```

Both are statements about **every** pinned market at once — one holds each
market's pin against its release contract, the other asserts the per-market
published-count table and its sum across all fourteen. Moving one market's entry
moves an assertion that is not about that market. A per-market node could in
principle be narrowed to its market; these cannot.

---

## MEASUREMENT 4 — IS IT ALREADY COVERED?

**No.** The fast release lane reads the sealed package for **one** market and
release indexes derived from committed authority. It never opens the pin. The
only thing that holds pins to release contracts, policy packages, exclusion
shards, censuses and partitions is
`tests/pettripfinder/contracts/test_market_state_pins.py`, which is not one of
the fifteen rules and is not run by the lane.

All fifteen rules PASS, and that is not the same as covering this.

---

## VERDICT: A

B required all three of: a generation path, no cross-market reach, and coverage
by the lane. **All three are false.** The verdict is derived from the
measurements, not written into the report.

### No classifier correction was made

Not only because the measurements went the other way. Two facts would make a
correction here a change to tested shared safety semantics rather than a bug fix:

- `test_regression_delta_001` contains a test named
  `test_a_shared_pin_makes_the_conditional_row_a_yes` whose entire purpose is to
  assert `full_regression_required is True` for this exact path, and to contrast
  it with a market-**owned** test file, which is False. The distinction is
  designed, not incidental.
- `release_coordinator` lists the pin in its own claim table with the role
  *"CROSS-CHECK — reviewed per-market numbers, not a live record."*

There is also a narrowing mechanism that already exists and deliberately does
not reach this file. `REGISTRATION_CONTAINERS` narrows a shared test file when
its elements name **things that exist** — a run directory, a file, an id — and
its own note draws the line this question turns on: *"Adding a number to an
expectations table can [change an assertion's answer]."* The pin is an
expectations table of numbers.

A classifier change cannot self-authorize, and none was needed.

---

## WAS A BROAD REGRESSION ACTUALLY REQUIRED?

**Yes, and it was already run.** The recovery order executed exactly one:

| | |
|---|---|
| Collected | 18,132 |
| Failures | 179 |
| PRE_EXISTING | 160 |
| TRUE_NEW reported | 19 |
| Pre-existing at the parent | 16 |
| Caused by the order | 3 |
| Closed by node id | 3 |
| **TRUE_NEW_FAILURE_AFTER_CLOSURE** | **0** |
| Wall clock | 6,390.3 s (1 h 47 m) |
| Remote broad jobs | 0 |

---

## WAS A SECOND ONE NEEDED?

**No.** Regression V2 calls the delta since that run
`FULL_REGRESSION_REQUIRED = YES` on one ground only: five modules under
`scripts/pettripfinder/` that the prefix rule calls SHARED_RUNTIME_CHANGE, with
no narrowing blockers.

A prefix is a rule about a path. Whether those modules are a **dependency** of
anything is a fact, measured five ways:

| Route | Result |
|---|---|
| `import` / `from` statements naming the module | 0 |
| Entries in `bundle_cache_closure.code_modules` (177 declared) | 0 |
| References from `.github/workflows` | 0 |
| Dynamic-import literals feeding `importlib` | 0 |
| Collected by pytest | no — none is under `tests/` |

All five are new in this delta and unreachable by every route, so a second broad
run would execute **zero new lines**. The three test-expectation changes in the
same delta were closed by node id.

The closure refuses to say no the moment a genuinely distinct shared dependency
moves: a schema, an assembler, an UNCLASSIFIED path, a narrowing blocker, or an
edit to a **pre-existing** shared module all short-circuit it to yes. None
occurred — `distinct shared deps moved: 0`.

---

## THE AUTHORITY DID NOT MOVE

This order wrote no authority, no pin, no participation record and no release
contract. Only two report writers and their two reports.

| | Recovery | This order |
|---|---|---|
| Census | 180 | 180 |
| Published pet-friendly | 79 | 79 |
| Verified no-pets | 18 | 18 |
| Holds | 4 | 4 |

**All seven of the sealed package's dependency input digests are identical at
both commits** — census, exclusions, market, partition, policy package, routing
and seed. That is the measurement that says the authority did not move.

The package digest itself changed, `sha256:8cdb83d4…` → `sha256:4a26dfe8…`,
because `created_from_source_sha` is a **field** of the sealed package and so
binds it to the commit. The intended-delta digest is unchanged.

---

## THE CANDIDATE IS UNCHANGED

Assembled a fourth time, at a third distinct commit, and byte-identical to the
digest the founder packet binds:

| | |
|---|---|
| Bundle | `c12b410ec8331dbf7a50581027ad60291cac95f626de5a6a846b0d77524e0e11` |
| Sitemap | `13f5335fc1a055ce06de5ce66c7921da55308110e94c0b0f18806853c1662bc4` |
| Markets / profiles / routes | 13 / 902 / 1,078 |
| Gates | 27 of 27 pass |
| Broken links | 0 |
| `deployment_authorized` | **false** |

That the bundle is identical at a commit which added two modules and two reports
is also the proof that neither is a site input.

---

## COMPLETION

| Requirement | |
|---|---|
| Nashville authority counts unchanged | **YES** |
| Package reproduced from the intended current input | **YES** |
| Final candidate reproducible | **YES** |
| FAST | **15 / 15 PASS**, 0 unknown, 0 failed |
| Unexpected deltas | **0 / 0 / 0** |
| Remote broad jobs required | **0** |
| Nothing weakened | **YES** |
| Founder authorization | still AWAITING, `authorized_by` null |

First-party evidence gate at HEAD: 97 evaluated, 97 eligible, 0 ineligible.

---

## WHAT THIS LEAVES FOR LATER

Unchanged from the recovery order, and none of it is this order's to do:

1. Fix the Toledo applier's manufactured hash — 39 live evidence entries carry
   `sha256(source_url + quote)`.
2. Re-pin the regression baseline at the Lexington-live commit; 16 real failures
   are still invisible to the classifier, and they inflate every TRUE_NEW count
   until someone does.
3. Rule on the four remaining Nashville holds.
4. Teach the change classifier a rule for `*_identity_holds_*.json`.

---

## HARD STOP

No classifier semantics were changed. No shared runtime, schema, assembler or
unknown-change coverage was weakened. No production activation was enabled. No
founder authorization was created. No host was called. Nothing was deployed.
