# PTF-RALEIGH-NC-FINAL-PRODUCTION-LAUNCH-002 — final report

**Raleigh is REGISTERED on the FINAL audited factory and AUTHORIZATION_READY
under `COMPOSITE_FRESH_MARKET_DATA_ONLY` — 46/46 changed paths accounted, 0
shared, 0 unknown, 0 local broad requested, 0 run, 0 remote, 0 unchanged
markets rebuilt, FAST 15/15, package and release-index candidate reproducible,
unexpected deltas 0 / 0 / 0, registration → AUTHORIZATION_READY in 119.6 s.
It is NOT deployable as prepared: the whole-site deployment artifact a launch
must bind could not be assembled, because `assemble_production_site` resolves a
market's partition through a named table that has no `raleigh-nc` entry, and
the one-line shared-code fix every prior market applied is a broad-regression
`DEPLOYMENT_CHANGE` this order was forbidden to make. The order STOPPED at
Phase 9, as instructed. Nothing was deployed, nothing authorized, no live pin
moved, no shared code or test edited.**

Worktree `C:\Atlas-Raleigh-Launch-V2`, branch `worker/ptf-raleigh-final-launch-002`,
started at `ce5c25029a408090d02aaf5af0954781273785ed` (the tip of
`worker/ptf-final-registration-reengineering-001`, the branch that carries the
audited implementation `091242a4`; `git diff --stat ce5c2502..HEAD` before this
order touched no shared module). Tree clean at start. Production at start and at
finish: 13 markets / 902 profiles / 1078 routes on deploy `6aa212a8ba9f174305c0441a`.

---

## PHASE 1 — PRECHECK

    WORKTREE           C:\Atlas-Raleigh-Launch-V2
    BRANCH             worker/ptf-raleigh-final-launch-002 (no upstream at start; pushed at the end)
    HEAD at start      ce5c25029a408090d02aaf5af0954781273785ed
    contained by       origin/worker/ptf-final-registration-reengineering-001
    TREE CLEAN         YES (0 lines of git status)
    audited code       the five reengineered modules, the ownership registry, the contract (proof
                       version 2.0), the matrix (16 rows), the replay harness and its manifest are all
                       present and byte-identical to ce5c2502; ce5c2502 differs from the AUDITED SHA
                       091242a4 by two receipts and two reports only (the reengineering report says so and
                       git agrees). The implementation was not edited.
    Raleigh at start   ABSENT in every way (registry, participation, closure, pin, rulings, OSM row,
                       helpers, config, inputs, authority, census, contract, packages) — probed, not assumed.

## PHASE 2 — CURRENT VERIFIED LIVE

Derived from `release_index.live_index()` (0 problems) and the deployment record
it names, then checked against the host itself: `https://pettripfinder.com/sitemap.xml`
fetched at precheck hashed to the recorded digest with 1078 `<loc>` routes.

    HOST DEPLOYMENT ID     6aa212a8ba9f174305c0441a
    LIVE RELEASE DIGEST    c12b410ec8331dbf7a50581027ad60291cac95f626de5a6a846b0d77524e0e11   (bundle_sha256)
    LIVE SITEMAP DIGEST    13f5335fc1a055ce06de5ce66c7921da55308110e94c0b0f18806853c1662bc4
    LIVE INDEX DIGEST      sha256:b7be3484adb40f63ba8977b579b2601fbb1a7e80d4a8e53f16489c7cc0e15f56
    SOURCE COMMIT          aee8a21e6c13881543601a4fcd54350b6a64bb19
    MARKETS / PROFILES / ROUTES   13 / 902 / 1078
    PARTICIPANTS           cincinnati-oh 130, cleveland-akron-canton-oh 120, columbus-oh 88, dayton-oh 54,
                           grand-rapids-holland-mi 43, indianapolis-in 82, lexington-ky 20, louisville-ky 53,
                           milwaukee-wi 73, nashville-tn 79, pittsburgh-pa 61, st-louis-mo 82, toledo-oh 17
    ROLLBACK PARENT        6aa172121d37bb4013eb44a4 (Lexington-live; ptf-deploy-lexington-006)
    AUTHORIZATION          ptf-auth-nashville-005-c12b410ec833 (DEPLOYED)
    VERIFICATION STATUS    CONSISTENT — record ALL_CRITICAL_CHECKS_PASS, 1078/1078 routes 200 and byte-identical;
                           live sitemap re-fetched and re-hashed by this order
    Nashville / Lexington / Toledo   live.  Charlotte   registered, NOT live.  Raleigh   NOT live.

## PHASE 3 — OLD RALEIGH SOURCE

`worker/ptf-raleigh-new-market-001` (worktree `C:\Atlas-Raleigh-Hardened-V1`),
tip `13809c36`, frozen acquisition + registration at `b613d72d`. Diff
`e3c27772..13809c36` = 45 paths (14 helpers, 2 discovery configs, 11 registration
roles, the proposed authority, the ruling, the OSM row, 3 regenerated globals,
13 reports). Read through git only, via the committed replay manifest
`raleigh_nc_true_first_registration_inputs_001.json`; the branch was not merged
and not modified. Its shared files (participation, rulings, OSM registry,
closure, pin, globals) are byte-identical between `e3c27772` and `ce5c2502`, so
the Raleigh semantic delta is exactly one row / one ruling / one block each.

## PHASE 4 — IMPORT RALEIGH DATA ONLY

    installed byte-for-byte    10 market-local helpers, 7 captured reports, the census, the market document,
                               the discovery config — 24 of 25 imported/regenerated blobs identical to b613d72d
    OSM registry row           applied ADDITIVELY to HEAD's file: 6 base rows byte-preserved, 1 row added,
                               semantically equal to the frozen file (the frozen branch had rewritten whitespace)
    regenerated by helpers     hotel_policy_facts_raleigh-nc.json, raleigh_nc_proposed_authority_002.json,
                               raleigh_nc_final_partition_007.json, identity_resolutions.json (+1 ruling)
                               — all four BYTE-IDENTICAL to the frozen branch
    NOT imported               raleigh_nc_release_lane_005 / _authorization_packet_009 / _participation_registration_010 /
                               _candidate_assembly_008 (replaced by the generic lane; rejected by the isolation proof),
                               the three frozen forensic reports, and no shared classifier / test / assembler /
                               coordinator / deployment / FAST / runtime code of any version

## PHASE 5 — RECONCILE RALEIGH

    REGISTERED CENSUS   90    (90 IDENTITY_CONFIRMED / LODGING_CONFIRMED; 2 SHARED_ADDRESS under the co_located_distinct ruling)
    PET-FRIENDLY        63    (seed shard 63 rows; policy package 63 VERIFIED_PET_FRIENDLY; HILTON 35 / MARRIOTT 18 / IHG 10)
    VERIFIED NO-PETS    23    (exclusion shard 23 records)
    RESOLVED            86    UNRESOLVED   4    (AWAITING_POLICY_OBSERVATION: DoubleTree Raleigh-Cary, DoubleTree
                                                 Crabtree Valley, DoubleTree Midtown, Tempo Downtown)
    HOLDS               4 unresolved rows, 0 founder holds, 0 out of category; none reaches a route
    pin block           census 90 / pet_friendly 63 / verified_no_pets 23 / resolved 86 / unresolved 4 / profiles 63 /
                        corridor_routes 5 — written by the transaction, held to the release contract
    Every count equals the frozen order's (90 / 63 / 23 / 86 / 4). No evidence reacquired, no policy semantics changed.

## PHASE 6 — TRUE FIRST-MARKET CLASSIFICATION

Regression V2 in normal mode, `--base ce5c2502 --head WORKTREE`, run three
times as the tree grew (the transaction's own run, the committed registration,
and the final working set with every report of this order):

    run                        paths   market-local / registration / derived / SHARED / UNKNOWN   class
    transaction (packet after)   41        11 / 15 / 15 / 0 / 0                                   COMPOSITE_FRESH_MARKET_DATA_ONLY
    committed 726232df           43        11 / 15 / 17 / 0 / 0                                   COMPOSITE_FRESH_MARKET_DATA_ONLY
    final working set            46        11 / 15 / 20 / 0 / 0                                   COMPOSITE_FRESH_MARKET_DATA_ONLY

    UNKNOWN PATHS                     0          sum of buckets == total   YES, every time
    MARKET-LOCAL ACQUISITION PROOF    PASS       (11 paths, all five conditions in registration mode)
    DISCOVERY CONFIG PROOF            PASS       REGISTRATION INPUT PROOF   PASS      IDENTITY RESOLUTION PROOF   PASS
    MARKET STATE PROOF                PASS       REGISTRATION PROOF (11)    PASS      INDEPENDENT EXPECTED RELEASE  PASS
    FULL_REGRESSION_REQUIRED          NO         LOCAL BROAD REQUESTED / RUN   0 / 0
    REMOTE BROAD REQUIRED             0          (ci_validation.required_shards: scope NONE, dispatch NONE, shards [])
    narrowing blockers present        the two the registration owns (closure, pin)
    plan                              lanes [], assembly_required false, ONE module: tests/pettripfinder/test_composite_fresh_market_001.py

The plan's one narrow module was run (60 tests, 26.8 s): 59 passed, 1 failed —
`TestThePartition::test_a_bare_re_registration_keeps_the_original_class`. It
PASSES at the parent `ce5c2502` in a worktree, so it is TRUE_NEW by node id, and
its mechanism is a stale expectation, not a Raleigh defect: the test builds a
synthetic Charlotte re-registration with base `11373275` and head WORKTREE, and
the gate correctly answers "exactly one previously absent market must be
registered; the registry gained ['charlotte-nc', 'raleigh-nc']", whose FAIL
result lacks the key the test indexes. It was not repaired (the order forbids
it); it is the hazard PTF-NEW-MARKET-REGISTRATION-DATA-ONLY-POLICY-001 recorded
("test modules that enumerate markets by hand go stale silently under a narrow
registration").

## PHASE 7 — SEALED PACKAGE + FAST

    package                 pkg-raleigh-nc-c162cb540fab7e91
    PACKAGE DIGEST          sha256:c162cb540fab7e91ffeb816b410dc3131f18c69db17fd93f43e977ab36da983c
    created_from_source     ce5c25029a408090d02aaf5af0954781273785ed   sealed_at 2026-09-12T00:28:24Z
    PACKAGE_REPRODUCIBLE    YES (sealed twice; the committed-set and final-set proofs re-seal the head bytes to the same digest)
    FAST                    15/15 PASS, 0 UNKNOWN, 0 FAILED, DETERMINISM BYTE_IDENTICAL, 69.7 s
    receipt                 sha256:a3385748f4e6cd9e14bc97493a860e20bb3b7a0bde8a16adc8d39c20f566553c
    changed-market bundle   25802a6fac7d51e16994d273f30ddef65f8f3ef09196ea6fe3dbdd7fadb3c8c2 (two cold builds equal)
    BUILD INPUT KEY         sha256:79f6160d28f03e1b824630f2031a644d9239292660953fb29e94b40b7eb55a7c
    INTENDED DELTA DIGEST   sha256:e93147c2a7b8dfd482bca74941a7148302b48b1ccd6b342e65f7fdc591d917d5
    first-party gate        PASS; evidence and provenance unchanged (86 evidence references, 86 hashes)

## PHASE 8 — CURRENT PARENT RECHECK

Re-read immediately before the lane composed (step 4b, 6.7 s): still
`6aa212a8ba9f174305c0441a`, 13 / 902 / 1078, 0 problems. Charlotte not
participating; no non-live market auto-participated. Rule N re-checked the
package's declared parent against it and passed.

## PHASE 9 — FINAL RALEIGH CANDIDATE: BLOCKED

The lane's composition — CURRENT VERIFIED LIVE + the sealed package, as complete
sets — is done and clean:

    release-index candidate   14 markets / 965 profiles / 1101 routes
    candidate index digest    sha256:c8bc258ee3e878f501551d9302d332373358ec0d96a350dae6a000092446788a  (recomposed: identical)
    expected vs actual        complete sets of markets, participation, profile identities, record digests, routes,
                              ownership — unexpected market / profile / route changes 0 / 0 / 0; release diff 0 findings
    every live market preserved   YES (Nashville, Lexington, Toledo included; profile count per market identical)
    UNCHANGED_MARKETS_REBUILT     0 (the lane built the joining market alone, twice)
    Raleigh adds                  63 profiles, 69 declared routes (release-index basis)

The whole-site deployment artifact — the bytes an authorization binds
(`binding_identity: bundle_sha256`, as every live authorization does) — was
attempted the way every launch-prep order since Toledo produced it: a throwaway
worktree at the registration commit `726232df`, the participation document
staged with exactly one field flipped, `assemble_production_site --output`.
It failed (rc=1, 577 s): 13 fragments built, no `raleigh-nc` fragment, no
global manifest. Mechanism, proven directly:

    assemble_production_site.market_eligibility(raleigh-nc)
        census_present true, final_partition_present FALSE, policy_authority_present true,
        meets_minimum_published true (63 >= 5)  ->  assemblable FALSE
    _partition_path("raleigh-nc")  -> None: the named table has 13 markets (every one since Indianapolis
        was added by hand); the glob strips the last id segment and looks for raleigh_final_partition_*.json,
        while the committed, contract-conformant file is raleigh_nc_final_partition_007.json
    market_package_writer.committed_partition_path -> None as well; the package writer's LAST-RESORT
        <us>_final_partition_* glob is why the sealed package, FAST rule J and the release-index candidate
        all resolved the partition and never saw this.

The fix Toledo, Lexington, Nashville and Charlotte each applied is one named
entry in `assemble_production_site._partition_path` — path class
`DEPLOYMENT_CHANGE` / `GENERIC_RUNTIME_CHANGE`, bucket `SHARED_BEHAVIOR_CHANGE`,
`FULL_REGRESSION_REQUIRED = YES`. This order forbids editing factory code and
forbids a broad regression, so it STOPPED here. A data-only rename of the
partition to the glob's spelling was considered and rejected: the registration
contract's `final_partition` role is `<us>_final_partition_*.json` and the
market-local helper writes that name, so the rename would be UNKNOWN to the
composite proof. Recorded mechanically in
`raleigh_nc_candidate_assembly_002.json` (FINAL_CANDIDATE_REPRODUCIBLE = BLOCKED;
digests null, nothing invented).

The frozen Raleigh order never produced this artifact either: its
`candidate_assembly_008` helper exists at `b613d72d` but its output was never
committed, and its "candidate 14 / 965 / 1101" was the lane's release-index
composition. The audited reengineering measured registration → AUTHORIZATION_READY
and left the whole-site artifact to "the deployment order" (the readiness packet
says so in `what_is_not_claimed`). This is the first time the final factory's
readiness has been carried through to the artifact, and the artifact is where
the fresh-city path is still not data-only.

## PHASE 10 — CANDIDATE REPRODUCIBILITY

    PARENT RELEASE DIGEST          c12b410ec8331dbf7a50581027ad60291cac95f626de5a6a846b0d77524e0e11
    PARENT RELEASE INDEX DIGEST    sha256:b7be3484adb40f63ba8977b579b2601fbb1a7e80d4a8e53f16489c7cc0e15f56
    RALEIGH PACKAGE DIGEST         sha256:c162cb540fab7e91ffeb816b410dc3131f18c69db17fd93f43e977ab36da983c
    BUILD INPUT KEY                sha256:79f6160d28f03e1b824630f2031a644d9239292660953fb29e94b40b7eb55a7c
    INTENDED DELTA DIGEST          sha256:e93147c2a7b8dfd482bca74941a7148302b48b1ccd6b342e65f7fdc591d917d5
    CANDIDATE INDEX DIGEST         sha256:c8bc258ee3e878f501551d9302d332373358ec0d96a350dae6a000092446788a  (lane: CANDIDATE_REPRODUCIBLE YES)
    FINAL CANDIDATE DIGEST         NOT PRODUCED (blocked, Phase 9)
    DEPLOYMENT ARTIFACT DIGEST     NOT PRODUCED (blocked, Phase 9)
    SITEMAP DIGEST                 NOT PRODUCED (blocked, Phase 9)
    FINAL_CANDIDATE_REPRODUCIBLE   BLOCKED — not YES, not NO; no whole-site bundle exists to reproduce

## PHASE 11 — REGISTRATION PERFORMANCE

    REGISTRATION_ADMITTED          2026-09-12T00:28:24Z      AUTHORIZATION_READY_AT   2026-09-12T00:30:23Z
    acquisition install + offline build steps (before the clock)      7.4 s   (live parent read 5.9 s of it)
    1 shard 0.23  ·  2 globals 1.37  ·  3 contract 2.04  ·  4 register 1.23   (registration writes 4.9 s)
    4b current-parent recheck (this order's own step)                 6.68 s
    5 seal x2 + first-party gate + FAST A–O + compose x2 + pin       84.63 s  (FAST 69.7 s: rule J 43.9, rule K 25.3)
    6 Regression V2 classify (composite proof)                       22.98 s
    7 readiness packet                                                0.45 s
    REGISTRATION_TO_AUTH_READY                                      119.62 s  (2 min 0 s; target <= 300 s)
    broad 0 · remote broad 0 · unchanged-market rebuilds 0 · shared or test edits 0
    Not in the clock: the committed-set classification (~25 s), the plan's one narrow module (26.8 s), and the
    blocked whole-site assembly attempt (577 s, rc=1).

## PHASE 12 — FOUNDER AUTHORIZATION PACKET

`launch_packages/pettripfinder/markets/reports/raleigh_nc_founder_authorization_packet_002.json`
— every digest read from a committed or lane-written artifact, full length, none
typed. Its status is **`BLOCKED_AT_PHASE_9 — NOT_DEPLOYABLE_AS_PREPARED`**, not
AWAITING_FOUNDER_AUTHORIZATION: a packet whose deployment-artifact digest reads
NOT_PRODUCED cannot honestly ask for a deployment authorization. It carries the
parent, the registration counts and holds, the package / build-input / intended-
delta / receipt / candidate-index digests, the projected 14 / 965 / 1101, the
0 / 0 / 0 deltas, the classification, FAST, 0 broad, 0 rebuilds, the rollback
(deployment `6aa212a8ba9f174305c0441a`, release digest
`c12b410ec8331dbf7a50581027ad60291cac95f626de5a6a846b0d77524e0e11`), the
119.6 s, the one narrow-test failure with its mechanism, and the founder decision
it needs: order the one-line assembler entry (with its broad run) or a factory
order that removes the assembler's dependence on the table — then the exact-bytes
candidate, targeted live verification and the record follow in the deployment
order. The registration readiness packet
(`raleigh_nc_registration_authorization_readiness.json`) stands at
AUTHORIZATION_READY, unsigned, exactly as the lane wrote it.

## PHASE 13 — HARD STOP

Stopped before founder authorization, production activation, host deployment
and live verification. No approval inferred. `launch_participation.json`'s
Raleigh row reads SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH; the
staged copy used by the failed assembly attempt lived only in the throwaway
worktree and was restored by `git checkout` (0 lines of status).

## PHASE 14 — COMMITS

    726232df   feat(ptf): register raleigh-nc on the FINAL audited factory -- COMPOSITE_FRESH_MARKET_DATA_ONLY,
               41/41 accounted, 0 broad, FAST 15/15, AUTHORIZATION_READY (PTF-RALEIGH-NC-FINAL-LAUNCH-PREP-002)
               43 paths: the 41 classified + the readiness packet + the prep receipt
    (closing)  docs(ptf): the founder packet, the committed-set classification, the Phase 9 blocker and this
               report (PTF-RALEIGH-NC-FINAL-LAUNCH-PREP-002) — the four report-zone companions classify as
               PERMITTED_DERIVED_REGISTRATION_OUTPUT (46/46, class unchanged)
    Pushed with upstream; origin == HEAD and tree clean are stated in the closing message.

## ARTIFACTS (all under atlas-dashboard/launch_packages/pettripfinder/)

    markets/reports/raleigh_nc_final_launch_prep_002.json                 the in-place transaction receipt (timings, proofs, tree)
    markets/reports/raleigh_nc_regression_classification_002.json         Regression V2 over the committed registration (43/43)
    markets/reports/raleigh_nc_registration_authorization_readiness.json  the lane's UNSIGNED readiness packet (AUTHORIZATION_READY)
    markets/reports/raleigh_nc_registration_release_lane.json             seal x2, FAST, compose x2, pin block
    markets/reports/raleigh_nc_registration_participation.json            the participation reissue
    markets/reports/raleigh_nc_candidate_assembly_002.json                the Phase 9 blocker, proven mechanically
    markets/reports/raleigh_nc_founder_authorization_packet_002.json      the proposal, status BLOCKED_AT_PHASE_9
    markets/packages/raleigh-nc/pkg-raleigh-nc-c162cb540fab7e91.json      the sealed package
    markets/receipts/raleigh-nc/pkg-raleigh-nc-c162cb540fab7e91-a3385748f4e6cd9e.json   the FAST receipt

## FINAL ANSWERS

     1. CURRENT LIVE MARKETS / PROFILES / ROUTES ...... 13 / 902 / 1078 (deploy 6aa212a8ba9f174305c0441a)
     2. RALEIGH CENSUS / PF / NO-PETS ................. 90 / 63 / 23
     3. RESOLVED / UNRESOLVED ......................... 86 / 4
     4. CHANGE CLASS .................................. COMPOSITE_FRESH_MARKET_DATA_ONLY
     5. FULL RALEIGH CHANGED PATHS ACCOUNTED .......... 46/46 (41/41 in the transaction, 43/43 committed)
     6. UNKNOWN PATHS ................................. 0
     7. LOCAL BROAD REQUESTED ......................... 0
     8. LOCAL BROAD RUN ............................... 0
     9. REMOTE BROAD REQUIRED ......................... 0
    10. UNCHANGED LIVE MARKETS REBUILT ................ 0
    11. FAST ......................................... 15/15 PASS, 0 UNKNOWN, 0 FAILED
    12. PACKAGE REPRODUCIBLE ......................... YES
    13. FINAL CANDIDATE REPRODUCIBLE ................. BLOCKED — release-index candidate YES; whole-site artifact NOT PRODUCED
    14. PROJECTED LIVE MARKETS / PROFILES / ROUTES .... 14 / 965 / 1101 (release-index basis; sitemap basis not produced)
    15. UNEXPECTED DELTAS ............................ 0 markets / 0 profiles / 0 routes
    16. REGISTRATION_TO_AUTH_READY ................... 119.6 s
    17. RALEIGH_FOUNDER_AUTHORIZATION_READY .......... NO — registration AUTHORIZATION_READY, deployment artifact BLOCKED (Phase 9)
    18. RALEIGH_DEPLOYED ............................. NO
    19. origin == HEAD ............................... see the closing message (pushed after this file was committed)
    20. tree clean ................................... see the closing message

STOP. Not deployed. No other city started. No factory code edited.
