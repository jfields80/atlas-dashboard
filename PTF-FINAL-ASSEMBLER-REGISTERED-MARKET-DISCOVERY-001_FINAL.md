# PTF-FINAL-ASSEMBLER-REGISTERED-MARKET-DISCOVERY-001 — FINAL

**A correctly registered market is now assemblable with no assembler edit and no
static-table entry. The whole-site deployment artifact Raleigh could not produce
is produced, and every one of the thirteen live markets comes out of the new
lookup byte-for-byte identical to what production serves today.**

Worktree `C:\Atlas-Assembler-Registration-Fix`, branch
`worker/ptf-final-assembler-registration-001`, base
`ce5c25029a408090d02aaf5af0954781273785ed`. Production at start and at finish:
13 markets / 902 profiles / 1078 routes on deploy `6aa212a8ba9f174305c0441a`.
Nothing deployed, nothing authorized, no live pin moved.

---

## PHASE 1 — THE OLD LOOKUP, TRACED

`assemble_production_site._partition_path(market_id)` was the only answer to
"which file is this market's final partition", and `market_eligibility` turned
its result into the boolean `final_partition_present`. Three other modules
consumed it: `market_package_writer.committed_partition_path` (which is why the
sealed package, FAST rule J and the release-index candidate all resolved
Raleigh and never saw the defect), `registration_data_only.authority_digests`
and `regression_delta.market_authority_owner`.

The lookup was, in order:

1. **A named table** of thirteen market ids inside the assembler's own source.
   Every market since Indianapolis was added by hand in its own launch order —
   Toledo, Lexington, Nashville and Charlotte each one line.
2. **A glob fallback**, `<market id minus its last segment, with "-oh"
   removed>_final_partition_*.json`, first match in sorted order.

Raleigh missed both: no table row, and the glob looked for
`raleigh_final_partition_*.json` while the committed, contract-conformant file
is `raleigh_nc_final_partition_007.json`. `final_partition_present` read False,
the market was NOT ASSEMBLABLE, no fragment was built, and a candidate staged
with Raleigh participating failed `global.launch_participation_agrees_with_source`.

**Do the existing live markets already expose enough to derive their partition
without the table?** Measured across all fifteen registered markets
(`raleigh_nc_partition_lookup_trace_001.json`), the answer is no:

| question | markets |
| --- | --- |
| contract identifies the partition at all | 6 of 15 |
| in a machine-readable `final_partition` block | 1 (Indianapolis) |
| only as a `reconciliation_cross_checks` path | 5 |
| old glob resolved correctly | 6 of 15 |
| a `<market id underscored>_` glob would resolve correctly | 4 of 15 |
| markets committing more than one partition, where any glob must guess | 4 |

That is why the legacy fallback is a table and not a cleverer pattern, and why
Indianapolis is the case that matters most: the old glob did not miss for
Indianapolis, it matched confidently and returned the wrong file.

## PHASE 2 — THE CANONICAL LOOKUP

The owning object is the market's own release contract,
`deploy/netlify/release_contracts/<market_id>.json`. It already binds the
market's identity census and its policy package by path and digest; the final
partition is the third leg of the same reconciliation and is now bound the same
way. No new registry, no new database, no second source of truth.

    REGISTERED MARKET (launch_packages/pettripfinder/markets/<id>.json)
      -> MARKET RELEASE CONTRACT (deploy/netlify/release_contracts/<id>.json)
        -> final_partition { path, schema, expected_sha256, expected_count }
          -> the partition file, verified to be THIS market's
            -> assembler

`scripts/pettripfinder/market_partition_resolution.py` implements
`resolve_registered_market_partition(market_id)`. It requires a registered
market, reads the owning contract, parses exactly ONE unambiguous reference,
and verifies five things about the file: it exists, it declares a
`ptf-market-final-partition/*` schema, it declares THIS market_id, it hashes to
the stated content digest, and it carries the stated identity count. It never
guesses a filename and never contains a market-specific condition. Fifteen
named failure codes, every one fail-closed.

`release_contracts.final_partition_block()` WRITES the reference from the
committed file rather than letting anyone type it, and refuses to choose when a
market commits several partitions — the sorted-order guess is exactly the
coincidence this replaces. `release_contracts.final_partition_disagreements()`
verifies it, and `contract_disagreements()` now calls it, so a regenerated
partition with a stale contract fails the contract gate.

## PHASE 3 — LEGACY COMPATIBILITY

Fifteen markets were registered before the reference existed. They resolve
through `LEGACY_PARTITION_TABLE`: the assembler's former named table verbatim,
plus the two ids its glob happened to serve (Milwaukee, Pittsburgh), each
recorded as the file the old lookup actually returned. The rules:

- a modern registered market uses contract-driven resolution;
- the legacy fallback is explicit and FROZEN — the resolver's own test pins its
  exact key set, so a new entry is a visible test-expectation change;
- no new market may require an entry: `registration_release_lane register`
  refuses a registering market whose partition is not owned by its contract;
- fallback usage is observable — every resolution reports `CONTRACT` or
  `LEGACY_TABLE`, `market_eligibility` reports `partition_source`,
  `partition_path` and `partition_error`, and the bundle manifest carries a
  `partition_resolution` block with per-source counts;
- contract and table disagreeing fails closed: neither is chosen.
## PHASE 4 AND PHASE 9 — RALEIGH, REGISTERED AND ASSEMBLED

Raleigh was replayed from an ABSENT state in a detached worktree of the frozen
code `50093f84`, with its already-captured acquisition deliverable imported
byte for byte from the frozen data branch `2e87d441` through the committed
replay manifest. Absence was PROBED, not assumed: registry, participation row,
build closure, market-state pin, identity ruling, OSM extract row, helpers,
discovery config, typed input, authority shard, census, partition, policy
package, release contract and package zone were all checked empty first.

    REGISTRATION -> AUTHORIZATION_READY                110.3 s   (ceiling 300)
    shared code digest before == after                 YES, 1829 python files
    CHANGE_CLASS                     COMPOSITE_FRESH_MARKET_DATA_ONLY
    ELIGIBLE                         YES        FULL_REGRESSION_REQUIRED   NO
    41 paths = 11 market-local / 15 registration / 15 derived
                                     0 SHARED, 0 UNKNOWN, sum == total
    15 of 15 proof checks             PASS
    FAST rules A-O                    15 PASS, 0 UNKNOWN, 0 FAILED
    LOCAL BROAD REQUESTED 0    LOCAL BROAD RUN 0    REMOTE BROAD 0
    UNCHANGED MARKETS REBUILT         0
    PACKAGE_REPRODUCIBLE  YES         CANDIDATE_REPRODUCIBLE  YES
    the four regenerated build outputs   byte-identical to the frozen branch
    partition resolution   source CONTRACT, verified exists / schema /
                           market_id / sha256 / count

    census 90 / pet-friendly 63 / verified-no-pets 23 / resolved 86 / unresolved 4

NO ASSEMBLER EDIT, NO TABLE ENTRY, NO SHARED FILE OF ANY KIND: the registration
commit `fa125e27` touches 42 paths and every one is Raleigh's own data or a
shared registration document the registration contract already owns
(participation, build closure, market-state pin, the three derived globals,
the identity ruling, the OSM registry row).

### The artifact the previous order could not produce

Assembled TWICE from the committed tree, into two separate output roots:

    bundle sha256    61ca6a2ef2f170c0ede36cdce03cbf36ee3ae498371d25b79e85e30cc20dc046
    sitemap sha256   55996aa7707e57888ce3545bfb0e55d3ec1c558204264bc4dfcbaf9573f0a72a
    build A 1344.1 s     build B 832.9 s     identical across all 5,907 files
    14 markets / 965 profiles / 1,148 sitemap routes / 5,889 html pages
    every global gate passes; 0 broken links, 0 collisions, 0 canonical violations
    Raleigh: 63 profiles, 63 hotel routes, 5 corridor routes
    partition resolution across the 16 registered markets:
        CONTRACT 2   LEGACY_TABLE 14   UNRESOLVED 0

Against the live bundle, file by file:

    live 5,524 files   candidate 5,907 files   identical 5,523
    added   383, every one under pet-friendly-hotels/raleigh-nc/ (70) or go/raleigh-nc/ (313)
    added anywhere else   0
    removed               0
    changed               1 -- sitemap.xml, which must change when routes are added
    UNEXPECTED FILE CHANGES = 0

    markets +1   profiles +63   routes +70 (sitemap basis) / +69 (release-index basis)
    unexpected market / profile / route changes = 0 / 0 / 0

Two route bases are stated because they count different things: the release
index counts hub, profile and corridor routes (1032 live -> 1101 candidate);
the assembled sitemap also renders the policy-comparison page and the other
composed surfaces (1078 live -> 1148 candidate). Neither is wrong and neither
is the other.

Participation was STAGED for the build and restored: the committed record
hashes to `db657522…` before and after and still reads
SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH. Membership is an input to
the candidate's digest, so a candidate built any other way would be a
different artifact than the one an authorization binds.
## PHASE 5 — NEGATIVE TESTS

`tests/pettripfinder/test_registered_market_partition_resolution_001.py`, 44
tests, all passing. Every item the order names, by test:

| # | requirement | test |
| --- | --- | --- |
| 1 | modern registered Raleigh resolves without a table entry | the frozen replay, plus `TestAModernRegisteredMarket::test_resolves_without_any_table_entry` |
| 2 | another synthetic modern market resolves generically | `test_a_second_synthetic_market_resolves_generically` (`harbor-town-qq`) |
| 3 | missing partition reference fails | `test_a_missing_partition_reference_fails` (`MISSING_PARTITION_REFERENCE`) |
| 4 | wrong-market partition reference fails | `test_a_wrong_market_partition_reference_fails` (`WRONG_MARKET_PARTITION`) |
| 5 | ambiguous reference fails | `test_an_ambiguous_or_malformed_reference_fails`, 10 parameterised cases (`AMBIGUOUS_REFERENCE`, `MALFORMED_REFERENCE`) |
| 6 | contract/table disagreement | `test_contract_and_legacy_table_disagreement_fails` — fails closed, neither side chosen; `..._agreement_resolves_by_contract` is the documented precedence when they agree |
| 7 | legacy live market resolves through the permitted fallback | `test_a_legacy_live_market_resolves_through_the_permitted_fallback_and_says_so` |
| 8 | a new market cannot silently rely on the legacy table | `test_a_new_market_cannot_silently_rely_on_the_legacy_path` — `boise-id` commits `boise_final_partition_001.json`, exactly what the OLD glob would have built for it, and is refused |
| 9 | unregistered market fails | `test_an_unregistered_market_fails_even_with_a_contract_and_a_file` (+ `EMPTY_MARKET_ID`) |
| 10 | a filename change works when the reference changes | `test_a_partition_filename_change_follows_the_contract_reference` |
| 11 | unrelated markets preserve exact bundle identity | the control builds below: 5,524 files, byte-identical |
| 12 | no route/profile changes outside the new market | the candidate comparison below |

Beyond the list: `UNREADABLE_PARTITION` and `UNREADABLE_CONTRACT` (a corrupt
file is a named refusal, never a traceback out of market selection, and a
corrupt contract never falls through to the table), `REFERENCE_DIGEST_MISMATCH`,
`REFERENCE_COUNT_MISMATCH`, `WRONG_PARTITION_SCHEMA`, `LEGACY_PARTITION_MISSING`,
`NO_RELEASE_CONTRACT`, a memo that cannot serve a stale answer, and a source
scan proving the assembler names no partition file and no glob any more.

## PHASE 6 — THE FUTURE-MARKET PROOF

`westlake-xx` is a market id that appears in no assembler source, no table and
no shared module. The fixture registers it the ordinary way — market document,
identity census, policy package, seed row, partition, contract written by
`release_contracts.final_partition_block` — and then asks the assembler:

    market_eligibility(westlake-xx).conditions
        census_present            True
        final_partition_present   True
        policy_authority_present  True
        meets_minimum_published   True
      -> assemblable              True
      partition_source            CONTRACT
      partition_path              westlake_xx_final_partition_001.json

with, measured in the same test before and after:

    ASSEMBLER CODE CHANGES        0   (sha256 of assemble_production_site.py unchanged)
    RESOLVER CODE CHANGES         0   (sha256 of market_partition_resolution.py unchanged)
    STATIC TABLE CHANGES          0   (LEGACY_PARTITION_TABLE identical)
    the market id appears in the assembler's source   never
    the market id appears in the resolver's source    never
## COMPATIBILITY, PROVEN BY BYTES

Three whole-site builds of the thirteen live markets, and the artifact
production is serving right now:

| build | commit | bundle sha256 | sitemap sha256 | files |
| --- | --- | --- | --- | --- |
| parent (old table + glob) | `ce5c2502` | `c12b410e…` | `13f5335f…` | 5,524 |
| this order's frozen code | `50093f84` | `c12b410e…` | `13f5335f…` | 5,524 |
| live deployment `6aa212a8` | `aee8a21e` | `c12b410e…` | `13f5335f…` | 5,524 |

Not just the same digest — the same 5,524 per-file digests, compared entry by
entry. 13 markets / 902 profiles / 1078 routes in all three, every global gate
passing. Removing the table and the glob moved nothing that production serves.

Each of the fifteen registered markets resolves to exactly the file the old
lookup returned, and the bundle manifest now records how: 1 by `CONTRACT`
(Indianapolis, whose contract already carried a block), 14 by `LEGACY_TABLE`,
0 unresolved.

## PHASE 7 — PERFORMANCE

    partition resolution, 15 markets, cold      20.0 ms   (1.33 ms per market)
    partition resolution, 15 markets, warm       3.6 ms   (0.24 ms per market)
    legacy-fallback resolutions                 14
    modern-contract resolutions                  1        (2 once Raleigh joins)
    unresolved                                   0

The resolution is memoised on the stat of the files the answer depends on --
the contract and the partition -- so a rewritten file changes the key and
nothing stale is ever served (there is a test for exactly that). Against a
whole-site assembly measured in minutes, the generic lookup is noise.
## PHASE 8 — THE ONE MIGRATION AUDIT

Preconditions met before it started: implementation complete, code frozen at
`50093f84` with a clean tree, the Raleigh candidate assembled and reproducible,
the future-market fixture green, and the fifteen-module targeted set run at the
audited commit — 750 passed, 4 failed, and the SAME four fail at the parent
`ce5c2502`, identical node-id sets, TRUE_NEW 0.

    RUN            python scripts/pettripfinder/regression_lanes.py run --lane full_regression
                   18,436 collected, 18,015 passed, 253 skipped, 168 failed, 5068.6 s (1:24:28)
    vs f75aa95     160 PRE_EXISTING, 0 EPOCH, 0 FLAKE, 8 TRUE_NEW
                   -- 7 of the 8 are the parent audit's own known TRUE_NEW set
    vs the parent  failure-set IDENTITY against the audited parent's broad run
    audit (167)    (091242a4): 167 of this run's 168 are the parent's; parent
                   failures now passing 0; failing here and not there: ONE.

    MIGRATION_AUDITS_RUN          1
    MIGRATION_AUDIT_TRUE_NEW      1

### The one node

    tests/pettripfinder/test_toledo_oh_promotion_002.py::test_the_assembler_names_toledos_partition_explicitly
    PASSED in the parent audit. Its whole body is:

        src = (REPO_ROOT / "scripts" / "pettripfinder"
               / "assemble_production_site.py").read_text(encoding="utf-8")
        assert '"toledo-oh": "toledo_oh_final_partition_001.json"' in src

It asserts the TEXT of the assembler's source. This order removed the table
from the assembler, so the dict-literal string is gone; Toledo's entry now
lives in `market_partition_resolution.LEGACY_PARTITION_TABLE` as a tuple pair.

**The behaviour that test protects is intact**, proven three independent ways:
the resolver returns `toledo_oh_final_partition_001.json` for `toledo-oh` and
its own test pins that by name in a frozen table; the whole-site control build
at this audited commit is byte-identical to live production across all 5,524
files with Toledo's 17 profiles in it; and the resolution report records
`toledo-oh` as `LEGACY_TABLE`, never `UNRESOLVED`. What broke is an assertion
about where a string lives in a file, not about which partition Toledo has.

Repairing it is a one-line TEST_EXPECTATION_CHANGE — point the assertion at
the resolver's frozen table. **It was not made.** Phase 8 of this order says
that any post-audit code or test correction is FINAL ENGINEERING ATTEMPT =
FAIL, forbids the correction and forbids a second broad audit. No correction
was made, no second audit was run.

This is the order's own rule applied to its own result, and it decides the
verdict below regardless of the engineering outcome.

## PHASE 10 — RALEIGH AUTHORIZATION READINESS

`raleigh_nc_founder_authorization_packet_003.json` on branch
`worker/ptf-raleigh-nc-assembler-discovery-003` at `fa125e27`, status
**AWAITING_FOUNDER_AUTHORIZATION**, `authorized_by` and `authorized_at` null.
Every digest is read from a committed or lane-written artifact, at full length:

    parent release digest      c12b410ec8331dbf7a50581027ad60291cac95f626de5a6a846b0d77524e0e11
    parent sitemap digest      13f5335fc1a055ce06de5ce66c7921da55308110e94c0b0f18806853c1662bc4
    parent release index       sha256:b7be3484adb40f63ba8977b579b2601fbb1a7e80d4a8e53f16489c7cc0e15f56
    sealed package digest      sha256:0acacc0707bd2b47da30e16b443a8a2a1d6aa20f9a48ef66a811ec463d017465
    fast lane receipt digest   sha256:3044b0bd76788da5aad0a57bdf7a6c169599dbfac344902227e807edd0412410
    changed market bundle      25802a6fac7d51e16994d273f30ddef65f8f3ef09196ea6fe3dbdd7fadb3c8c2
    expected candidate index   sha256:90513eea910411a1f0352fd403b2c353152107f46c2b469245dc4f7ca4695a0c
    deployment artifact        61ca6a2ef2f170c0ede36cdce03cbf36ee3ae498371d25b79e85e30cc20dc046
    candidate sitemap          55996aa7707e57888ce3545bfb0e55d3ec1c558204264bc4dfcbaf9573f0a72a
    independent second tree    61ca6a2ef2f170c0ede36cdce03cbf36ee3ae498371d25b79e85e30cc20dc046
    rollback parent            deployment 6aa212a8ba9f174305c0441a, release digest c12b410e…,
                               sitemap 13f5335f… -- the CURRENT live deployment, not that
                               deployment's own rollback target, which would un-deploy Nashville

Nothing was authorized, nothing deployed, no live pin moved, and the committed
participation record still reads SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH.

## WHAT THE FOUNDER IS ACTUALLY CHOOSING BETWEEN

The engineering the order asked for exists and is proven. The order's audit
rule failed it on one stale assertion about a source file's text. Those are
different facts and both are stated above. The decision is whether the rule's
verdict stands as written, or whether a one-line test repair plus a second
broad audit is worth ordering. This order is not permitted to make that call
and did not: no correction, no second audit, nothing deployed.
## COMMITS

    fcd8545d  feat  the contract-driven resolver; the table and glob removed from the assembler
    ead91964  fix   no market's partition filename in the resolver's prose
    444cbc25  fix   an unreadable partition or contract is a named refusal, never a traceback
    7ce3f435  fix   keep the resolver off the per-market build's import path (closure unmoved)
    50093f84  test  pin the staged-build properties the closure decision rests on   <- AUDITED
    (docs)    docs  this report, the lookup trace and the migration audit record

    worker/ptf-raleigh-nc-assembler-discovery-003:
    fa125e27  feat  register raleigh-nc on the contract-driven assembler
    6854e924  docs  the candidate, the frozen replay and the founder packet

Two of those fixes are defects this order found in its OWN work before the
audit, and both are worth recording because they are traps a later order will
walk into:

  * the resolver's docstring illustrated the contract reference with a REAL
    committed partition filename. A partition's filename is its market-local
    helper's importable stem, so the isolation proof's reverse-reachability
    condition read "raleigh_nc_final_partition_007 is named by
    market_partition_resolution.py" and correctly rejected the registering
    market's own helper as SHARED_BEHAVIOR_CHANGE. One prose line cost a
    registration its narrowing. Caught by running the replay, not by reading.
  * declaring the resolver in `bundle_cache_closure.code_modules` was correct
    while the assembler imported it at module scope -- and it broke three
    tests that hold the committed closure to a historical base as a legitimate
    registration delta, because `check_build_closure` refuses ANY code_modules
    movement. The closure is a registration-shaped document; a factory order
    must not move it. The fix was to keep the resolver off the per-market
    build's import path instead, which is also the better design.

## FINAL ANSWERS

     1. OLD PARTITION RESOLUTION METHOD = a hand-maintained 13-entry named table inside
        assemble_production_site._partition_path, then a glob built from the market id with its
        last segment stripped and "-oh" deleted, first match in sorted order.
     2. NEW PARTITION RESOLUTION METHOD = market_partition_resolution.resolve_registered_market_partition:
        registered market -> its own release contract -> the final_partition reference (path +
        content digest) -> the file, verified to exist, to declare a ptf-market-final-partition
        schema, to declare THIS market_id, to hash to the stated digest and to carry the stated
        count. Fifteen named fail-closed refusals; no filename is ever guessed.
     3. RALEIGH STATIC TABLE ENTRY ADDED = NO
     4. MODERN MARKET REQUIRES ASSEMBLER EDIT = NO
     5. LEGACY FALLBACK RETAINED = YES -- frozen at 15 markets, pinned by key set in the resolver's
        own test, observable in every eligibility row and in the bundle manifest, and closed to new
        markets by the registration lane's own refusal.
     6. RALEIGH PARTITION RESOLUTION = PASS  (source CONTRACT; exists / schema / market_id / sha256 / count)
     7. GENERIC FUTURE MARKET FIXTURE = PASS  (westlake-xx assemblable; assembler bytes, resolver
        bytes and the legacy table all unchanged, measured in the test)
     8. TARGETED TESTS = 44/44 in the resolver's own module; the 15-module targeted set at the
        audited commit 750 passed / 4 failed / 4 skipped, and those same 4 fail at the parent
        ce5c2502 -- identical node-id sets, TRUE_NEW 0.
     9. MIGRATION AUDITS RUN = 1
    10. MIGRATION AUDIT TRUE_NEW = 1
        (tests/pettripfinder/test_toledo_oh_promotion_002.py::test_the_assembler_names_toledos_partition_explicitly
        -- a grep of the assembler's source text for the table literal; the behaviour it protects
        is intact and independently proven)
    11. POST-AUDIT CODE CHANGE REQUIRED = YES -- one stale test expectation. NOT MADE, and no
        second broad audit was run.
    12. AUDITED SHA = 50093f847872adad99901e616fd52e9ed64674bd
    13. RALEIGH REPLAY CLASS = COMPOSITE_FRESH_MARKET_DATA_ONLY
    14. REPLAY LOCAL BROAD REQUESTED = 0
    15. REPLAY LOCAL BROAD RUN = 0
    16. REPLAY REMOTE BROAD = 0
    17. REPLAY UNCHANGED MARKETS REBUILT = 0
    18. REPLAY FAST = 15/15 PASS, 0 UNKNOWN, 0 FAILED
    19. RALEIGH PACKAGE REPRODUCIBLE = YES
    20. RALEIGH DEPLOYMENT CANDIDATE REPRODUCIBLE = YES -- two whole-site builds into separate
        roots, identical across all 5,907 files
    21. PROJECTED LIVE MARKETS / PROFILES / ROUTES = 14 / 965 / 1148 on the assembled sitemap
        (1101 on the release-index basis; live is 1078 / 1032)
    22. UNEXPECTED DELTAS = 0 / 0 / 0  (and 0 unexpected file changes across 5,907 files)
    23. SHARED CODE CHANGED DURING FROZEN REPLAY = NO -- 1829 python files, identical digest
        before and after
    24. RALEIGH_FOUNDER_AUTHORIZATION_READY = YES -- packet prepared, UNSIGNED,
        AWAITING_FOUNDER_AUTHORIZATION
    25. FACTORY STATUS = SHELF_EXPANSION_FACTORY
    26. origin == HEAD = YES
    27. tree clean = YES

FINAL ASSEMBLER CORRECTION = FAIL
FUTURE NEW MARKET REQUIRES ASSEMBLER CODE EDIT = NO
FUTURE NEW MARKET REQUIRES STATIC TABLE ENTRY = NO
RALEIGH DEPLOYMENT ARTIFACT READY = YES
RALEIGH AUTHORIZATION READY = YES
FACTORY STATUS = SHELF_EXPANSION_FACTORY
