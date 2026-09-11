# PTF-CHARLOTTE-CONTROLLED-REGISTRATION-REPLAY-003 — final report

**CONTROLLED_REPLAY = FAIL. REGISTRATION_REPLAY_PROVEN = NO.**

The registration itself was not the problem. The ordinary workflow took a
pre-Charlotte production state and registered Charlotte, correctly and
byte-for-byte, in **6.94 seconds**. Regression V2 then classified it in 2.09
more and answered **FULL_REGRESSION_REQUIRED = YES**.

Per the order the broad regression was not run, nothing was repaired, and the
replay stopped at the gate.

---

## THE PRECONDITION

Verified mechanically against the owning branch, not read out of the report.

    FINAL_TRUE_NEW_FAILURE_AFTER_CLOSURE   0
    CHARLOTTE CENSUS / PF / NO-PETS        268 / 106 / 41
    FAST RELEASE LANE                      15/15 PASS
    FRESH_PACKAGE_REPRODUCIBLE             YES
    FINAL_CANDIDATE_REPRODUCIBLE           YES
    UNEXPECTED DELTAS                      0 / 0 / 0
    LIVE, RE-DERIVED                       13 markets / 902 profiles / 1078 routes
    TREE                                   clean

One precondition was not met on arrival: the Charlotte work had never been
pushed, so `origin` did not exist. The branch was pushed before the replay
began, which is publication, not repair. `origin == HEAD == 42cb937f`.

---

## THE REPLAY WORKSPACE

An isolated detached worktree at `C:/t/replay`, assembled from two commits so
that the code and the market state could come from different places:

| half | source | what it carried |
|---|---|---|
| SHARED CODE | `42cb937f` | the final Charlotte-audited implementation, frozen |
| MARKET STATE | `11373275` | the commit before Charlotte was registered |

Charlotte's already-validated inputs stayed in place and were neither
reacquired nor altered: the 268-identity census, the proposed authority
carrying 106 pet-friendly and 41 verified-no-pets, the policy package, the
partition, the seven co-location rulings, and the geography contract, which was
held aside as an input for the registration to install.

At replay start the derived live state read **13 markets / 902 profiles / 1078
routes with zero problems**, and `charlotte-nc` appeared in neither the market
registry nor the participation record.

Both halves were committed as one detached REPLAY BASE commit, `f11bb374`, so
that the classifier had a real git base to compare the registration against.
That commit was never pushed. Nothing touched production, the live pin, the
Charlotte authority branch or the host.

---

## THE SHARED-CODE FREEZE

A digest over 1988 files — everything under `scripts/`, `tests/`, `core/`,
`engines/`, `services/`, `routes/`, `models/`, `repositories/`, `database/`,
plus the root test and app configuration — taken before the replay and again
after it.

    BEFORE  sha256:f090876bed5cbc83ba4adb1a62f5091e0472913268bcc216b122117e3325ebe1
    AFTER   sha256:f090876bed5cbc83ba4adb1a62f5091e0472913268bcc216b122117e3325ebe1

    SHARED_CODE_CHANGED = NO

`tests/pettripfinder/pins/` is excluded from the freeze on purpose: a pin is
committed market state that a registration is expected to move, not test
machinery. Moving it is exactly what the classifier then charges for.

The harness ran from outside the repository so that this proof could be taken
at all. It is committed afterwards, at
`scripts/pettripfinder/charlotte_nc_controlled_registration_replay_003.py`.

---

## WHAT THE ORDINARY WORKFLOW COST

| step | seconds | peak MB |
|---|---:|---:|
| install the market document | 0.00 | — |
| registration writer, the authority shard | 0.27 | 27 |
| regenerate the derived globals | 1.35 | 32 |
| release contract | 1.41 | 43 |
| participation row + build closure | 3.90 | 27 |
| market state pin | 0.01 | — |
| **registration subtotal** | **6.94** | |
| Regression V2 classification | 2.09 | 24 |
| **REGISTRATION → CLASSIFICATION** | **9.03** | **43** |

    BUILDER INVOCATIONS          0
    UNCHANGED MARKET REBUILDS    0
    LOCAL BROAD REGRESSIONS RUN  0
    REMOTE BROAD JOBS REQUESTED  0
    TESTS EXECUTED               0
    PEAK WORKING SET             43 MB

---

## THE REGISTRATION WAS CORRECT, AND REPRODUCIBLE

Nine of the twelve files the registration wrote are **byte-identical** to the
ones the audited Charlotte registration committed: the market document, all
four authority shard files, the release contract, and all three derived
globals.

The other three differ only in a date or in the name of the work order that
wrote them — `decided_on` moved from the 10th to the 11th, and the pin's
`reviewed_by` and `last_moved_by` name this order. Nothing about the market
moved.

    REGISTERED MARKETS AFTER          15
    CHARLOTTE CENSUS / PF / NO-PETS   268 / 106 / 41
    CHARLOTTE LAUNCH STATUS           SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH
    FOUNDER-AUTHORIZED SET            13, unchanged
    DECISION CHAIN                    9 records, 0 problems
    verify_participation              unlisted [], unregistered [], disagreement []
    LIVE STATE                        13 / 902 / 1078, unmoved, 0 problems
    NASHVILLE / LEXINGTON / TOLEDO    preserved at 79 / 20 / 17

The registration writer is generic and the numbers it derived came from
Charlotte's own committed authority. This is the half of the factory that
works.

---

## REGRESSION V2 — THE FINDING

Run normally. Narrow mode was not forced.

    CHANGED FILES              13
    CHANGE CLASSES             AUTHORITY_CHANGE, DEPLOYMENT_CHANGE,
                               TEST_EXPECTATION_CHANGE, GENERATED_REPORT_ONLY
    NARROWING BLOCKERS         bundle_cache_closure.json,
                               tests/pettripfinder/pins/market_state.json
    MARKET_AUTHORITY_DATA_ONLY None -- narrowing blocked
    FAST_DATA_ONLY_RELEASE     None
    MODULES THE PLAN SELECTS   226
    ASSEMBLY REQUIRED          True
    FULL_REGRESSION_REQUIRED   YES

**There is no `NEW_MARKET_REGISTRATION_DATA_ONLY` class, and no current
equivalent.** The classifier's vocabulary has no row for registering a market.
The nearest narrow class is `MARKET_AUTHORITY_DATA_ONLY`, and it cannot apply
here for two independent reasons: it requires the *whole* change set to be one
market's authority data, and it requires `fast_release_activation.json` to
enable the market, which reads `FAST_PATH_PRODUCTION_ACTIVATION = DISABLED`
with an empty allowlist.

### Four paths force the broad run, and a registration cannot avoid any of them

| path | class | why a registration must touch it |
|---|---|---|
| `deploy/netlify/launch_participation.json` | DEPLOYMENT_CHANGE | a registered market with no row reads UNLISTED, fails `verify_participation`, and the assembler refuses the whole build |
| `deploy/netlify/release_contracts/charlotte-nc.json` | DEPLOYMENT_CHANGE | every market with verified inventory must carry a contract, and the registry asserts it |
| `launch_packages/pettripfinder/bundle_cache_closure.json` | DEPLOYMENT_CHANGE | the closure names every registered market's two documents; an undeclared input publishes every bundle UNTRUSTED, including markets the new one never touched |
| `tests/pettripfinder/pins/market_state.json` | TEST_EXPECTATION_CHANGE | a registered market must state its reviewed counts, and a shared pin is not narrowable |

Three of the four are `DEPLOYMENT_CHANGE`, whose full-regression answer is a
hard REQUIRED — not conditional, not narrowable. Any one of them alone costs
the full suite. The fourth blocks narrowing separately.

This is not Charlotte's residue. It is what a registration *is*: the point at
which a market joins the documents that decide what production serves.
Charlotte's own audit reached exactly this verdict twice, and the replay
confirms the corrections it made did not turn registration into a data-only
change, because they were never capable of doing so.

**The broad regression was not run.** A request for one is the failure, not a
step.

---

## WHAT THE REPLAY DID NOT MEASURE

The order stops the replay at the gate, so five acceptance criteria were never
reached:

    FAST RULES                        NOT MEASURED
    PACKAGE REPRODUCIBLE              NOT MEASURED
    CANDIDATE REPRODUCIBLE            NOT MEASURED
    REPLAY CANDIDATE M / P / R        NOT MEASURED
    UNEXPECTED M / P / R DELTAS       NOT MEASURED

All five are recorded PASSING in the owning audit at
`launch_packages/pettripfinder/markets/reports/charlotte_nc_authorization_packet_009.json`
— 15/15, YES, YES, 14 / 1008 / 1197, and 0 / 0 / 0. They are deliberately not
restated here as replay measurements, because the replay did not take them.

---

## INTEGRITY

    CLASSIFIER EXEMPTION CREATED         NO
    HARD-CODED MARKET TOTAL WORKAROUND   NO
    FAILURE SUPPRESSION / XFAIL          NO
    BASELINE ADDITION                    NO
    SHARED CODE OR TEST EDITS            NO -- repairs were required and none were made
    ORPHANED BACKGROUND JOBS             0
    DEPLOYED / AUTHORIZED                NO / NO

---

## FINAL ANSWERS

     1. FINAL AUDITED CHARLOTTE TRUE_NEW ............ 0
     2. PRE-REPLAY LIVE MARKETS / PROFILES / ROUTES .. 13 / 902 / 1078
     3. CHARLOTTE ABSENT AT REPLAY START ............. YES
     4. SHARED CODE CHANGED DURING REPLAY ............ NO
     5. CHARLOTTE CENSUS / PF / NO-PETS .............. 268 / 106 / 41
     6. LOCAL BROAD REGRESSIONS REQUESTED ............ 1
     7. LOCAL BROAD REGRESSIONS RUN .................. 0
     8. REMOTE BROAD JOBS REQUIRED ................... 0
     9. UNCHANGED MARKETS REBUILT .................... 0
    10. FAST RULES .................................. NOT MEASURED
    11. PACKAGE REPRODUCIBLE ........................ NOT MEASURED
    12. CANDIDATE REPRODUCIBLE ...................... NOT MEASURED
    13. REPLAY CANDIDATE MARKETS / PROFILES / ROUTES . NOT MEASURED
    14. UNEXPECTED MARKET / PROFILE / ROUTE DELTAS ... NOT MEASURED
    15. REGISTRATION TO AUTHORIZATION-READY ......... NOT REACHED
                                                      (registration + classification = 9.03s)
    16. ORPHANED BACKGROUND JOBS AT COMPLETION ...... 0
    17. NEW SHARED TEST / CODE REPAIRS REQUIRED ..... YES, and none were made
    18. CONTROLLED_REPLAY .......................... FAIL
    19. REGISTRATION_REPLAY_PROVEN ................. NO
    20. RECOMMENDED FACTORY STATUS ................. PAUSE

---

## WHAT THIS RESULT MEANS

The registration machinery is fast, generic and deterministic: nine seconds,
zero builds, zero tests, and output byte-identical to an audit that took
fifteen hours. What costs the hours is not the writing. It is the classifier's
doctrine that any change to the documents deciding what production serves must
be proved by a fresh whole-site assembly and the full suite — and a new market
is, by definition, exactly such a change.

Under the agreed decision rule the expansion factory is **PAUSED**. No repair
sprint is recommended here, and none was attempted.

---

*The machine-readable receipt is
`launch_packages/pettripfinder/markets/reports/charlotte_nc_controlled_registration_replay_003.json`
(sha256 `9d4f0434c457dc28700faa00fd6d6500e476917c5f37ef0b97f24745508a7092`).*

*Nothing was deployed. Nothing was authorized. Production is still 13 markets /
902 profiles / 1078 routes on deploy `6aa212a8ba9f174305c0441a`.*
