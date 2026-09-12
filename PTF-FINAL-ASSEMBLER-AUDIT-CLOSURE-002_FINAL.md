# PTF-FINAL-ASSEMBLER-AUDIT-CLOSURE-002 — FINAL

**The one procedural failure is closed. The corrected assertion states Toledo's
partition claim against behaviour instead of against a string in a source file,
and the single final broad audit comes back with a failure set IDENTICAL to the
parent audit's 167 nodes: nothing new, nothing lost. No production code
changed.**

Branch `worker/ptf-final-assembler-registration-001`, audited commit
`168aa5536ef0d1524ed383270a94b8fde1b75ba4`. Production unchanged at 13 markets /
902 profiles / 1078 routes on deploy `6aa212a8ba9f174305c0441a`. Nothing
deployed, nothing authorized, no live pin moved.

## PHASE 1 — PRECHECK

All four conditions confirmed mechanically before the test was touched:

| check | result |
| --- | --- |
| Toledo resolves to | `toledo_oh_final_partition_001.json`, source `LEGACY_TABLE` |
| the assembler's own lookup agrees | yes, same path |
| partition content digest, parent vs HEAD | identical, `6c77eadc2ab80e43…` |
| production output at the audited commit vs live | identical, all 5,524 files |
| Toledo's own pages in that comparison | 21 files identical, 17 profiles |
| what the failing assertion checked | implementation LOCATION, not behaviour |

## PHASE 2 — THE ONE CORRECTION

`tests/pettripfinder/test_toledo_oh_promotion_002.py::test_the_assembler_names_toledos_partition_explicitly`
— node id unchanged, so the audit compares like with like.

It used to read the text of `assemble_production_site.py` and assert the dict
literal `"toledo-oh": "toledo_oh_final_partition_001.json"` appeared in it. The
assembler correction moved that mapping into the resolver's frozen legacy
table, so the string is gone while Toledo's partition never moved.

The claim is now made through the public resolver: Toledo must resolve, to
exactly that file, by a supported path; the mapping must still be declared in
the frozen table; the assembler's own lookup must return the same path; and a
glob built from the market id with its last segment stripped must still match
nothing — which is the reason the mapping has to be explicit and is what this
test has always been about.

It was not weakened. Proved by in-memory mutation, with no file edited:

| mutation | outcome |
| --- | --- |
| mapping removed | fails, `PartitionResolutionError` |
| mapping repointed at another market's partition | fails, `AssertionError` |
| contract reference disagreeing with the table | fails, `PartitionResolutionError` |
| unmutated | passes |

## PHASE 3 — TARGETED PROOF

158 passed, 8 skipped, 0 failed across the resolver's own module, the Toledo
promotion module, the Grand Rapids partition-lookup module, the global
assembler and the factory-throughput harness.

    PRODUCTION MODULE DIFF = 0
    (git diff --stat 50093f84 168aa553 -- atlas-dashboard/scripts = 0 lines)

Only two files changed: the one test, and the generated test inventory, which
moved by two line numbers because the edit shifted lines in that module.

## PHASE 4 — THE ONE FINAL BROAD AUDIT

    RUN            python scripts/pettripfinder/regression_lanes.py run --lane full_regression
                   18,436 collected, 18,016 passed, 253 skipped, 167 failed, 1:30:59
    vs f75aa95     160 PRE_EXISTING, 0 EPOCH, 0 FLAKE, 7 TRUE_NEW -- and those
                   seven are EXACTLY the parent audit's own known set, compared
                   node id by node id, with nothing of this order's in them
    vs the parent  167 failing here, 167 failing there, failing here and not
    audit (167)    there: 0; parent failures now passing: 0 -- the two failure
                   sets are the SAME SET

    the corrected node in this audit    PASSED
    BROAD AUDITS RUN                    1
    TRUE_NEW_FAILURE                    0

The previous audit's 168 became 167 by exactly the one node this order
corrected, and nothing else moved in either direction.

## PHASE 5 — FACTORY CLAIMS, RE-VERIFIED AT THE CORRECTED COMMIT

Raleigh replayed from an absent state at `168aa553`, 109.3 s to
AUTHORIZATION_READY, shared code digest identical before and after:

    CHANGE CLASS                    COMPOSITE_FRESH_MARKET_DATA_ONLY
    41 paths = 11 market-local / 15 registration / 15 derived / 0 shared / 0 unknown
    15 of 15 proof checks           PASS
    LOCAL BROAD REQUESTED 0    LOCAL BROAD RUN 0    REMOTE BROAD 0
    UNCHANGED MARKETS REBUILT       0
    FAST                            15/15 PASS, 0 UNKNOWN, 0 FAILED
    PACKAGE REPRODUCIBLE            YES
    CANDIDATE REPRODUCIBLE          YES
    PROJECTED                       14 markets / 965 profiles / 1101 routes
    UNEXPECTED DELTAS               0 / 0 / 0
    Raleigh's partition             CONTRACT, verified exists / schema /
                                    market_id / sha256 / count

Two facts make this a re-verification rather than a fresh claim: the sealed
package's seven dependency input digests are IDENTICAL to the previous run, so
Raleigh's authority did not move, and the changed-market bundle digest is the
same `25802a6f…` as before, so its rendered output did not either. The
whole-site deployment artifact `61ca6a2e…` was built twice and proved identical
across all 5,907 files at `fa125e27`; no production code has changed since, and
no unrelated live market was rebuilt here.

The future-market claims need no separate run: the fixture that registers an
arbitrary market id and measures the assembler's bytes, the resolver's bytes
and the legacy table as unchanged passed inside this very audit.

## FINAL ANSWERS

     1. PRODUCTION CODE CHANGED = NO
     2. TEST FILES CHANGED = 1
     3. ORIGINAL FAILING NODE = tests/pettripfinder/test_toledo_oh_promotion_002.py::
        test_the_assembler_names_toledos_partition_explicitly
     4. CORRECTED SAFETY CLAIM = Toledo resolves, through the public resolver's supported
        contract/legacy path, to exactly toledo_oh_final_partition_001.json; the mapping is still
        declared in the frozen legacy table; the assembler's own lookup returns the same path; and
        the stripped-id glob still matches nothing. It fails if Toledo cannot resolve, resolves to
        the wrong partition, loses the mapping, or gains a contract reference that disagrees with it.
     5. TARGETED TEST = PASS  (the node, and 158 passed / 8 skipped across the focused set)
     6. TOLEDO RESOLVES TO EXACT EXPECTED PARTITION = YES
     7. BROAD AUDITS RUN = 1
     8. BROAD AUDIT TRUE_NEW_FAILURE = 0
     9. FUTURE NEW MARKET REQUIRES ASSEMBLER CODE EDIT = NO
    10. FUTURE NEW MARKET REQUIRES STATIC TABLE ENTRY = NO
    11. RALEIGH CHANGE CLASS = COMPOSITE_FRESH_MARKET_DATA_ONLY
    12. RALEIGH LOCAL BROAD REQUESTED = 0
    13. RALEIGH REMOTE BROAD = 0
    14. RALEIGH FAST = 15/15 PASS, 0 UNKNOWN, 0 FAILED
    15. RALEIGH PACKAGE REPRODUCIBLE = YES
    16. RALEIGH CANDIDATE REPRODUCIBLE = YES
    17. RALEIGH PROJECTED LIVE = 14 markets / 965 profiles / 1101 routes
    18. RALEIGH UNEXPECTED DELTAS = 0 / 0 / 0
    19. RALEIGH_FOUNDER_AUTHORIZATION_READY = YES
    20. FACTORY STATUS = RESUME_MARKET_PRODUCTION
    21. origin == HEAD = YES
    22. tree clean = YES

FINAL PROCEDURAL CLOSURE = PASS
TRUE_NEW_FAILURE = 0
PRODUCTION CODE CHANGED = NO
FACTORY STATUS = RESUME_MARKET_PRODUCTION
RALEIGH AUTHORIZATION READY = YES
