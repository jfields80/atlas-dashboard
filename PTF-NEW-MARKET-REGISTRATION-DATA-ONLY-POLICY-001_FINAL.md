# PTF-NEW-MARKET-REGISTRATION-DATA-ONLY-POLICY-001 — final report

**FINAL CORRECTION COMPLETE = YES. CONTROLLED_REPLAY = PASS. An ordinary
new-market registration now reaches AUTHORIZATION_READY in 2 minutes 2
seconds, under `NEW_MARKET_REGISTRATION_DATA_ONLY`, with zero broad
regressions requested, zero remote broad jobs and zero unchanged markets
rebuilt.**

Starting SHA `42cb937fbdff33430b864ad4c4217f4128cc6879` (the final audited
Charlotte code, `FINAL_TRUE_NEW_FAILURE_AFTER_CLOSURE = 0`). The controlled
replay it corrects, PTF-CHARLOTTE-CONTROLLED-REGISTRATION-REPLAY-003 at
`83ce8c93`, wrote Charlotte in 6.94 s with shared code frozen and was answered
`FULL_REGRESSION_REQUIRED = YES` by four paths a registration cannot avoid.

---

## THE CORRECTION

One whole-set change class, `NEW_MARKET_REGISTRATION_DATA_ONLY`, added to
the existing Regression V2 classifier. It is never selected by a filename, a
market name, a count or a request. `classify` runs an eleven-check proof over
every change set, and the class is granted only when all eleven PASS; anything
UNKNOWN is a failure that leaves every path in its path class.

| check | what it proves |
|---|---|
| change_set | the registry gained exactly ONE market; every path is a registration role for it or a narrow companion; the only blockers present are the two a registration owns |
| participation | a reissue: base rows byte-identical, one new SOURCE_READY row, `decided_by` is the writing order and never the founder, `supersedes` is the sha256 of the exact base bytes, the chain comes forward whole, the authorized set is unchanged |
| release_contract | a new instance whose `canonical` / gates / tokens / `publish` EQUAL every base contract's, grants no deployment, carries only recognized keys, and agrees with `derive_authority` |
| build_closure | exactly two declared inputs and one note; every build control unchanged |
| derived_globals | byte-identical to a regeneration from the shards; no other shard changed |
| sealed_package | a committed package sealed from exactly the head bytes, re-sealing to the same digest, declaring one joining market against the current live parent |
| fast_receipt | 15/15 PASS, 0 UNKNOWN, 0 FAILED, digest re-derives, bound to the same parent, delta, dependency, lane and builder versions |
| expected_release | EXPECTED (trusted parent + package) equals ACTUAL (committed authority) as complete sets of markets, profiles, routes, ownership, participation |
| identity_routes | `release_index.compare` clean over both releases |
| market_state_pin | one new block equal to what the SEALED PACKAGE derives; every other block byte-identical; the live pin untouched |
| release_integrity | no authorization, record, manifest, activation flag, production gate or deployment pin moved |

The four path classes are unchanged: the participation record, the release
contract and the build closure are still `DEPLOYMENT_CHANGE` by path and the
pin is still a shared blocker. The class is CONDITIONAL, so the mandatory set
(six classes) and the safe-narrow set are exactly what they were. The plan it
yields runs no lane and no reverse-dependent scan (the four documents are
named by 137 test modules, which is the broad run by another name; the
market-targeted lane alone measures 4.7 minutes without the whole-site class
and 15.7 with it) and no whole-site assembly (rule J builds the joining market
twice, cold). It reaches AUTHORIZATION_READY and authorizes nothing.

    PRODUCTION MODULES CHANGED     3
      scripts/pettripfinder/regression_delta.py          the class, its row, its surface, the plan
      scripts/pettripfinder/registration_data_only.py    the eleven checks and the committed contract
      scripts/pettripfinder/registration_release_lane.py seal + FAST + COMMIT the package and receipt;
                                                         the unsigned readiness packet
    ALSO
      launch_packages/pettripfinder/registration_data_only_contract.json   (generated; a blocker)
      launch_packages/pettripfinder/regression_validation_matrix.json      (regenerated)
      docs/PTF_HARDENED_FACTORY_RUNBOOK.md                                 (the rule)
      tests/pettripfinder/test_registration_data_only_001.py               (63 tests, all 26 cases)
      scripts/pettripfinder/charlotte_nc_controlled_registration_replay_004.py (the replay harness)
      markets/packages/charlotte-nc/, markets/receipts/charlotte-nc/       (the committed fixture)
    IMPLEMENTATION ENGINEERING WALL TIME   ~1 hour (precheck 11:35, implementation committed 12:33)

Why the generic lane exists: every market so far sealed its package in memory
and embedded the receipt in a report, so nothing under `markets/packages/` or
`markets/receipts/` existed for a classifier to find. The lane commits both,
in the market's own zone, which is what lets the change set prove itself.

## WHAT THE PROOF REFUSES

Sixty-three focused tests, one process, 44 s, all green
(`registration_data_only_001_focused_negative_results.json`). Every one of the
order's 26 cases is covered, on the real Charlotte registration as the fixture
with exactly one thing broken per case: two markets, a removed market, a
profile swapped at equal count, a route moved at equal count, a truncated
chain, a predecessor named by position, a founder impersonation, a fabricated
authorization, a gate removed from the contract, a code module added to the
closure, a pin off by one, a circular pin (the pin agrees with the TREE but
not with the package: it fails, and the tampered package covers nothing
because it does not re-seal), an identity collision, a route collision, a
stale parent, a stale / corrupt / UNKNOWN / missing receipt, a package whose
digests are not the head bytes, a candidate that differs from the package,
unknown fields in each of the four documents, and a shared-runtime, schema,
assembler, deployment, classifier, conftest, test-expectation, other-market
or loose-file path in the set.

## THE ONE MIGRATION AUDIT

Code frozen at `fb499741`, tree clean, nothing edited for 84 minutes.

    RUN                 18332 collected, 17911 passed, 253 skipped, 168 failed, 5056 s
    vs f75aa95          160 PRE_EXISTING, 8 TRUE_NEW by node id
      6 of the 8        in the audited parent's own broad run (charlotte-close, 168 failing)
      1                 test_regression_delta_001::test_the_committed_closures_all_verify --
                        proved failing at 42cb937f in a worktree BEFORE the audit
                        (the Charlotte closure artifact's shape); not this order's
      1                 test_factory_throughput_001::test_the_committed_inventory_reproduces_from_the_suite --
                        the committed test inventory counts assertion sites by class and
                        the focused battery added two; regenerating it is GENERATED_REPORT_ONLY,
                        classified NO, closed by node id in a 12 s delta run
    PARENT FAILURES NOW PASSING   2 (a run-on-disk test that reads this worktree's empty
                                  data/, and the node the operator broke during the
                                  Charlotte run by editing the tree)
    MIGRATION_AUDIT_TRUE_NEW      0
    POST-AUDIT CODE CHANGE        NO -- git diff fb499741..87e8de3d is three report files

`AUDITED_CODE_SHA = 87e8de3d` (shared code byte-identical to `fb499741`).

## THE CONTROLLED REPLAY

Workspace built by the harness: a detached worktree of `87e8de3d` with the
participation record, the build closure, the market-state pin and the four
derived globals checked out from `11373275`, Charlotte's registry document
held aside, her shard / contract / package / receipt / reports removed, and
the result committed as REPLAY BASE `f6652d64`. At start: 14 registered, 13
live, 902 profiles, 1078 sitemap routes, no `charlotte-nc` anywhere, live
problems `[]`. Shared-code digest over 1992 files taken before and after:
`87e3f4ac…` both times.

| step | seconds |
|---|---:|
| install the market document | 0.01 |
| registration writer (shard) | 0.29 |
| regenerate the derived globals | 1.36 |
| release contract | 2.08 |
| participation row + build closure | 3.71 |
| market state pin | 0.00 |
| **registration write subtotal** | **7.46** |
| registration release lane: seal ×2, first-party gate, FAST A–O, compose ×2 | 104.97 |
| Regression V2 classify, with the eleven-check proof (8.3 s of it) | 8.93 |
| authorization-readiness packet | 0.42 |
| **REGISTRATION → AUTHORIZATION_READY** | **121.79** |

    CHANGE_CLASSES              GENERATED_REPORT_ONLY, MARKET_DATA_PACKAGE,
                                NEW_MARKET_REGISTRATION_DATA_ONLY  (16 files; the 12
                                registration paths carry the new class)
    FULL_REGRESSION_REQUIRED    NO      LOCAL BROAD REQUESTED 0 / RUN 0
    REMOTE_BROAD_JOBS           0       (ci_validation.required_shards, untouched)
    UNCHANGED_MARKETS_REBUILT   0
    FAST                        15/15 PASS, 0 UNKNOWN, 0 FAILED, 92.6 s
    PACKAGE_REPRODUCIBLE        YES     CANDIDATE_REPRODUCIBLE YES
    EXPECTED vs ACTUAL          14 markets / 1008 profiles / 1150 index routes, 0 / 0 / 0 unexpected
    PACKET                      AUTHORIZATION_READY, AWAITING_FOUNDER_AUTHORIZATION,
                                authorized_by null, authorized_at null
    CONTROLLED_REPLAY           PASS on all 21 criteria

The receipt is
`launch_packages/pettripfinder/markets/reports/charlotte_nc_controlled_registration_replay_004.json`.
The focused benchmark before the audit measured the same lane at 162.9 s on a
cold stage (`registration_data_only_001_focused_performance.json`).

## WHAT THE FRESH CITY WILL MEET

Recorded in `registration_data_only_001_final_factory_decision.json`, not
repaired here: a partition filename the assembler's glob cannot resolve costs a
named entry in shared code (name it `<us>_final_partition_NNN.json`); loose
files at the launch-package root are UNCLASSIFIED and belong to the
acquisition phase, not the registration; eleven test modules enumerate markets
by hand and will go stale silently under a narrow registration — a hygiene
debt, not a release-safety gap, and editing them is not a registration.

## ARTIFACTS

    registration_data_only_contract          launch_packages/pettripfinder/registration_data_only_contract.json
    field_level_eligibility_matrix           launch_packages/pettripfinder/reports/registration_data_only_001_field_level_eligibility_matrix.json
    independent_expected_release_report      launch_packages/pettripfinder/reports/registration_data_only_001_independent_expected_release_report.json
    focused_negative_results                 launch_packages/pettripfinder/reports/registration_data_only_001_focused_negative_results.json
    focused_performance                      launch_packages/pettripfinder/reports/registration_data_only_001_focused_performance.json
    migration_audit_report                   launch_packages/pettripfinder/reports/registration_data_only_001_migration_audit_report.json
    controlled_replay_receipt                launch_packages/pettripfinder/markets/reports/charlotte_nc_controlled_registration_replay_004.json
    final_factory_decision                   launch_packages/pettripfinder/reports/registration_data_only_001_final_factory_decision.json

Nothing was deployed. Nothing was authorized. No hotel authority changed.
Production is still 13 markets / 902 profiles / 1078 routes on deploy
`6aa212a8ba9f174305c0441a`. The fresh city was not started.

## FINAL ANSWERS

     1. CHANGE CLASS IMPLEMENTED .................. NEW_MARKET_REGISTRATION_DATA_ONLY
     2. PRODUCTION MODULES CHANGED ................ 3
     3. TOTAL FILES CHANGED ....................... 22 (git diff --stat 42cb937f..HEAD: 3 modules,
                                                    1 test module, 1 harness, matrix, contract, runbook,
                                                    package, receipt, lane report, inventory json+md,
                                                    closure, 7 artifacts, this report)
     4. IMPLEMENTATION ENGINEERING WALL TIME ...... ~1 hour (cap 8)
     5. PARTICIPATION ROW NARROWING ............... PASS
     6. RELEASE CONTRACT NARROWING ................ PASS
     7. BUILD CLOSURE NARROWING ................... PASS
     8. CURRENT-STATE PIN NARROWING ............... PASS
     9. COMPLETE CHANGE-SET FIELD VALIDATION ...... PASS
    10. INDEPENDENT EXPECTED RELEASE CHECK ........ PASS
    11. FOCUSED NEGATIVE TESTS .................... PASS (63/63)
    12. FOCUSED REGISTRATION TIME ................. 162.9 s (benchmark), 121.8 s (replay)
    13. MIGRATION AUDITS RUN ...................... 1
    14. MIGRATION AUDIT TRUE_NEW .................. 0
    15. DID AUDIT REQUIRE POST-AUDIT CODE CHANGE .. NO
    16. AUDITED_CODE_SHA .......................... 87e8de3de0fb459cb8a8c09babdffe983c72337c
                                                    (code == fb49974110b5fdf8049a810426646a9fb4761632)
    17. CONTROLLED REPLAY CHANGE CLASS ............ NEW_MARKET_REGISTRATION_DATA_ONLY
    18. REPLAY LOCAL BROAD REQUESTED .............. 0
    19. REPLAY LOCAL BROAD RUN .................... 0
    20. REPLAY REMOTE BROAD REQUIRED .............. 0
    21. REPLAY UNCHANGED MARKETS REBUILT .......... 0
    22. REPLAY FAST ............................... 15/15 PASS, 0 UNKNOWN, 0 FAILED
    23. REPLAY PACKAGE REPRODUCIBLE ............... YES
    24. REPLAY CANDIDATE REPRODUCIBLE ............. YES
    25. REPLAY UNEXPECTED DELTAS .................. 0 markets / 0 profiles / 0 routes
    26. REPLAY REGISTRATION_TO_AUTH_READY ......... 121.79 s (2m02s), ceiling 300 s
    27. SHARED CODE CHANGED DURING REPLAY ......... NO
    28. CONTROLLED_REPLAY ......................... PASS
    29. FINAL FACTORY STATUS ...................... CONTINUE_WITH_ONE_FINAL_FRESH_CITY_PROOF
    30. FINAL FRESH CITY ALLOWED .................. YES (not started by this order)
    31. origin == HEAD ............................ YES (see the closing commit)
    32. tree clean ................................ YES

FINAL CORRECTION COMPLETE = YES
MIGRATION AUDITS USED = 1
CONTROLLED REPLAY PASSED = YES
NORMAL NEW-MARKET REGISTRATION REQUIRES BROAD = NO
NORMAL NEW-MARKET REGISTRATION TIME = 2 minutes 2 seconds (121.79 s) registration -> AUTHORIZATION_READY
FACTORY STATUS = CONTINUE_WITH_ONE_FINAL_FRESH_CITY_PROOF
FINAL FRESH CITY PROOF ALLOWED = YES
