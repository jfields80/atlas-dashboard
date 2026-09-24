# PTF-WEST-PALM-BEACH-FL-FOUNDER-LAUNCH-AUTHORIZATION-006 — FINAL

**Worktree** `C:\Atlas-West-Palm-Beach-FL-Hardened-V1` · **Branch** `worker/ptf-west-palm-beach-fl-market-001`
**Market** `west-palm-beach-fl` · **Corrected package** `pkg-west-palm-beach-fl-94d6f4115daa9b88`
**Candidate artifacts** `C:\t\wpb6a` (build A, 3,050 s) · `C:\t\wpb6b` (build B, 3,025 s)

This order records the founder's **new** launch authorization for the corrected package. The exact authorized
candidate is built twice and is byte-identical. A **new** deployment authorization is written **AUTHORIZED and
UNCONSUMED**. **Nothing was deployed.** Netlify was never invoked, the live manifest was not written, and every
West Palm Beach route still returns 404 in production. The superseded 003 authorization carries nothing forward.

---

## PHASE 1 — CURRENT LIVE (`release_index live-source --verify-host`, at the start and again at the end)

| | |
|---|---|
| CURRENT LIVE SOURCE COMMIT | `e82120cce7e48c62d3c1057a6c82785bed920485` (built from `0cc2817b`) |
| CURRENT LIVE DEPLOYMENT | `6ab1a035c7ef3b14a23a4ec6` |
| CURRENT LIVE BUNDLE | `0ec5c6557d79eaf77a4065b6700c0a5807e9bfe282408dd4779804b33af3a40f` |
| CURRENT LIVE SITEMAP | `e81961ae76454ce608fcb39624d5147c8779f52b269faab9449138397cb8fa3d` |
| CURRENT LIVE MARKETS | 32 (Fort Lauderdale live; West Palm Beach absent) |
| CURRENT LIVE PROFILES | 2375 |
| CURRENT LIVE RELEASE-INDEX ROUTES | 2646 (index digest `97ec0244…`) |
| CURRENT LIVE SERVED ROUTES | 2711 |
| HOST VERIFIED | true |

Live had **not** advanced, so the parent is current. The byte comparison baseline `C:\t\ftl3a` is the live bundle
(`0ec5c655…`, sitemap `e81961ae…`).

## PHASE 2 — CORRECTED PACKAGE

| | |
|---|---|
| PACKAGE / DIGEST | `pkg-west-palm-beach-fl-94d6f4115daa9b88` / `sha256:94d6f4115daa9b88a8773d2b73b49593c5de4a4757125def52b7ba17c25ec086` |
| `verify_seal` · covering package · re-seal | [] · the only package covering HEAD · re-seals to the same digest |
| SOURCE READY / COVERAGE READY | YES / YES (census 190, PF 49, NP 25, unresolved 116, actionable 0) |
| Re-registration (committed packet `348c9da6`) | `AUTHORIZED_NONLIVE_MARKET_REREGISTRATION_DATA_ONLY`, ELIGIBLE YES, 17/17, FULL_REGRESSION_REQUIRED NO, SHARED_FACTORY_DELTA 0 |
| FAST | 15/15, receipt `…-5aaf1cb212b2f493.json` |
| RULE J | `file_count 320`, `html_count 304`, `receipt_output_defects []` |
| RULE K | `BYTE_IDENTICAL`, a = b = J bundle (not `e3b0c442…`) |
| **CORRECTED MARKET BUNDLE SHA256** | **`711760f09faddc8022b5d55a681c0ccd0937151a2d61be34d67cbdd0c934ef45`** (from receipt J detail, equal to ARTIFACT_DIGESTS a and b) |

## PHASE 3 — OLD AUTHORIZATIONS

| | |
|---|---|
| Records naming WPB before this order | exactly 1: `ptf-auth-west-palm-beach-003-217f87eeba72` |
| OLD DEPLOYMENT AUTH STATUS | SUPERSEDED (terminal) |
| OLD DEPLOYMENT AUTH CONSUMED | NO (`deploy_id null`) |
| OLD DEPLOYMENT AUTH DEPLOYABLE | NO (binds bundle `217f87ee…`; SUPERSEDED ∉ DEPLOYABLE_STATUSES) |
| DEPLOYABLE OLD AUTHORIZATIONS REMAINING | 0 |
| OLD AUTHORIZATION TRANSFERS TO NEW PACKAGE | NO: the new decision and the new authorization are fresh records. The old record was neither read for its bindings nor transitioned, and `_refuse_if_unsafe` refuses to run if any WPB authorization is still deployable or the new id collides |
| Historical records | preserved: the 003 authorization, the 003 decision (lineage), the 003 candidate manifest and the old package and receipt are all untouched |

## PHASE 4 — NEW FOUNDER AUTHORIZATION (commit `ff6b506d`)

Recorded by `west_palm_beach_fl_launch_participation_006.py` through `launch_participation.extend_decision`.
`decided_by: founder` records the founder's explicit grant in **this** order, quoted verbatim in `decision_basis.founder_words`.

| | |
|---|---|
| NEW FOUNDER AUTHORIZATION ID | decision `PTF-WEST-PALM-BEACH-FL-FOUNDER-LAUNCH-AUTHORIZATION-006`, participation record sha256 `837d37d324d7694a142a4e3cd0402ab76577ae4b00533967dcc4d8ac9228b5ad` |
| AUTHORIZED MARKET | `west-palm-beach-fl` |
| AUTHORIZED PACKAGE | `pkg-west-palm-beach-fl-94d6f4115daa9b88` |
| AUTHORIZED PACKAGE DIGEST | `sha256:94d6f4115daa9b88a8773d2b73b49593c5de4a4757125def52b7ba17c25ec086` |
| AUTHORIZED MARKET BUNDLE | `711760f09faddc8022b5d55a681c0ccd0937151a2d61be34d67cbdd0c934ef45` |
| AUTHORIZED SOURCE COMMIT | `ff6b506d6e6311b686e974cf3aea6cff110af262` (the commit carrying this decision; the candidate was built from it) |
| AUTHORIZED PARENT | deploy `6ab1a035c7ef3b14a23a4ec6`, release-index digest `sha256:97ec0244d157683a50ddb57f9d55ce50ba15e61a96f6c42b9118bba1cf578c7f` |
| DECISION BASIS | the re-registration readiness packet (002, sha-pinned); census 190 / PF 49 / NP 25 / unresolved 116 / actionable 0; FAST receipt and digest; class and base `d4da13d1`; trusted factory baseline `a000b167`; `identity_correction_accepted` {Hilton Garden Inn Boca Raton, bctbrgi, published true, erroneous name absent true}; `reauthorizes_after_supersession` {superseding decision 005 `c3f5fc94…`, superseded decision 003 `19328995…`, 789c0187 → 94d6f411, auth 217f87ee SUPERSEDED, `old_authorizations_authorize_this_package: false`}; the policy, shard, contract and census file digests |

## PHASE 5 — PARTICIPATION

| | |
|---|---|
| PARTICIPATION STATE | `SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH` → **`FOUNDER_AUTHORIZED_FOR_LAUNCH`** |
| authorized before / after | 32 / 33, gained exactly `[west-palm-beach-fl]`, lost `[]`, every other row byte-identical |
| supersedes | `PTF-WEST-PALM-BEACH-FL-CORRECTED-REREGISTRATION-005` (`c3f5fc94…`), whose lineage record carries `founder_authorization_superseded: [west-palm-beach-fl]` |
| lineage | 34 records; `decision_problems []`; `supersession_problems []` |
| Supersession metadata | preserved: the full 005 entry stays in the 005 record's bytes (pinned by sha in the lineage). The market id stays in the lineage record, and the old and new digests plus the superseded authorization are restated in `decision_basis.reauthorizes_after_supersession`. It is not copied as a live `founder_authorization_superseded` block, because an entry for an authorized market is a contradiction the chain refuses |
| Detroit | still SOURCE_READY (withheld) |
| `release_contracts.verify_all()` | 34 contracts, 0 problems |
| LIVE status | none invented. FOUNDER_AUTHORIZED_FOR_LAUNCH admits the market to the next assembly; it deploys nothing |

## PHASES 6–7 — THE EXACT AUTHORIZED CANDIDATE AND ITS ACCOUNTING

`python -m scripts.pettripfinder.assemble_production_site --output C:\t\wpb6a` (then `…\wpb6b`) on the committed tree
`ff6b506d`, run detached and sequentially. Accounting: `west_palm_beach_fl_candidate_accounting_006.py`, report
`markets/reports/west_palm_beach_fl_launch_authorization_006.json`, `ALL_ACCOUNTING_GATES PASS`, `problems []`.

| | |
|---|---|
| PARENT LOOKUP | PASS: the package's parent `6ab1a035…` = resolved deploy = deployed bundle `0ec5c655…` = the comparison artifact |
| PARENT ROUTES PRESERVED | PASS: 2646/2646 release-index and 2711/2711 served routes are in the candidate |
| UNCHANGED BUNDLES REUSED | 32 (release-index entries carried unchanged) |
| UNCHANGED MARKETS REBUILT | 0 |
| WEST PALM BEACH BUNDLES BUILT | 1 (`711760f0…`) |
| **PHYSICAL FRAGMENTS RERENDERED** | **33**, read from build A's log (`Market scope:` × 33). There is no populated release store in this worktree, so the whole-site composer physically renders every participating fragment. **This is not reuse.** |

| | |
|---|---|
| CANDIDATE MARKETS | 33 |
| CANDIDATE PROFILES | 2424 (derived from the bundle's own fragments) |
| CANDIDATE RELEASE-INDEX ROUTES | 2701 |
| CANDIDATE SERVED SITEMAP ROUTES | 2767 (read as a set from the bundle's own `sitemap.xml`) |
| WEST PALM BEACH PROFILES | 49 |
| WEST PALM BEACH HUB ROUTES | 1 |
| WEST PALM BEACH CORRIDOR ROUTES | 5 (downtown-west-palm-beach, palm-beach-gardens, palm-beach-international-airport, delray-beach, boca-raton; 10 suppressed, 0 forced) |
| WEST PALM BEACH RELEASE-INDEX ROUTES | 55 (49 + 1 + 5) |
| WEST PALM BEACH SERVED ROUTES | 56 (the 55 + its own `/policy-comparison/`, which is served but not market-owned) |

Hold safety: 56 WPB pages = 49 profiles + 5 corridors + hub + comparison. 0 unapproved profiles. 116 unresolved rows
are unpublished, and the 25 verified-no-pets rows are exclusions, not profiles. Collision safety: PASS (0 duplicate
canonical exclusion names; bare names still owned by Tampa and Lexington).

## PHASE 8 — IDENTITY SAFETY (on the built artifact)

| | |
|---|---|
| CORRECTED HILTON GARDEN INN PROFILE PRESENT | YES: `Hilton Garden Inn Boca Raton`, `bctbrgi`, premises `8201\|congress\|33487`, page `pet-friendly-hotels/west-palm-beach-fl/hilton-garden-inn-boca-raton/index.html`, title *Hilton Garden Inn Boca Raton Pet Policy \| PetTripFinder West Palm Beach, Florida*, in the sitemap |
| First-party binding | `bctbrgi`, `full_premises_match true`, `…/bctbrgi-hilton-garden-inn-boca-raton/hotel-info/`, READ |
| OLD APPLE TEN PROFILE PRESENT | NO |
| OLD APPLE TEN ROUTE PRESENT | NO (no route, no sitemap entry, no file, no `/go/` page) |

The gate was checked against the superseded 003 candidate (`C:\t\wpb3a`) before this build, and it **FAILED there on
3 counts** (unapproved Apple Ten page, corrected profile absent, 5 Apple Ten `/go/` files). It detects exactly the
defect it exists for. Nothing was re-acquired.

## PHASE 9 — DELTA SAFETY

UNEXPECTED MARKET / PROFILE / ROUTE / SERVED-ROUTE DELTA = `[]` / `[]` / `[]` / `[]`. `release_index.compare` passed with
no findings. 32 parent markets, profiles and routes are preserved. Byte preservation versus live:
**+299 files (all WPB: 56 pages + 243 `/go/`), 0 removed, 1 changed (`sitemap.xml`), 0 prior-market files touched,
0 unclassified.** West Palm Beach is the only new market.

## PHASE 10 — FAST RECEIPT SAFETY

SELECTED FAST RECEIPT = `pkg-west-palm-beach-fl-94d6f4115daa9b88-5aaf1cb212b2f493.json` · CURRENT ELIGIBILITY = YES ·
FILE COUNT 320 · HTML COUNT 304 · defects `[]`. Augusta's `…-5f8116aaecd97d09.json` is historically preserved and
**currently ineligible** (EMPTY_BUNDLE, NO_HTML_OUTPUT). Augusta was not modified.

## PHASE 11 — CANDIDATE DETERMINISM (measured)

```
build A C:\t\wpb6a  bundle 23728b4bff71c66d0a9a063de3882d744f92465f5f568f72b3caf16ca8641d78  sitemap 8ae34cea1c7e384f0f4c8499066c5ff2f9ca841d099c344a5860041b4b6c7546
build B C:\t\wpb6b  bundle 23728b4bff71c66d0a9a063de3882d744f92465f5f568f72b3caf16ca8641d78  sitemap 8ae34cea1c7e384f0f4c8499066c5ff2f9ca841d099c344a5860041b4b6c7546
14,760 files compared, 0 differing  ->  BYTE_IDENTICAL  (non-empty: 14,742 HTML pages, all_gates_pass true)
```

CANDIDATE DETERMINISM = PASS. No market source evidence was rebuilt.

## PHASE 12 — RELEASE GATES

| Gate | |
|---|---|
| FOUNDER AUTHORIZATION | PASS: `extend_decision`, `decision_problems []`, 34-record chain |
| PACKAGE IDENTITY | PASS: digest, seal, covering package, re-seal |
| REREGISTRATION LINEAGE | PASS: base `d4da13d1`; the packet (`348c9da6`) and the chain (003 → 005 supersession → 006) are consistent |
| AUTHORIZATION SUPERSESSION | PASS: 217f87ee SUPERSEDED, unconsumed, not transferred |
| TRUSTED FACTORY BASELINE | PASS: `a000b167`, SHARED_FACTORY_DELTA 0 (packet) |
| PARENT IDENTITY | PASS |
| PARENT ROUTES PRESERVED | PASS |
| PROFILE PRESERVATION | PASS: 2375 + 49 = 2424, measured on the artifact |
| ROUTE PRESERVATION | PASS: 0 served routes lost |
| MARKET DELTA | PASS: +1, WPB only |
| PARTICIPATION | PASS: 32 → 33 |
| IDENTITY SAFETY | PASS |
| FAST RECEIPT ELIGIBILITY | PASS |
| CANDIDATE DETERMINISM | PASS (measured) |
| DEPLOYMENT ELIGIBILITY | PASS: authorized, bound to the candidate bytes, deployable, unconsumed |
| composed-bundle gates | `all_gates_pass true`; 0 broken links, 0 collisions, 0 global shadowing, 0 canonical problems |

ALL RELEASE GATES = PASS. CANDIDATE = AUTHORIZED and DEPLOYABLE, and not deployed.

## PHASE 13 — NEW DEPLOYMENT AUTHORIZATION (commit `430ea9d2`)

| | |
|---|---|
| NEW DEPLOYMENT AUTHORIZATION CREATED | YES (new record; not 217f87ee) |
| NEW DEPLOYMENT AUTHORIZATION ID | `ptf-auth-west-palm-beach-006-23728b4bff71` |
| AUTHORIZED BUNDLE | `23728b4bff71c66d0a9a063de3882d744f92465f5f568f72b3caf16ca8641d78` |
| AUTHORIZED SITEMAP | `8ae34cea1c7e384f0f4c8499066c5ff2f9ca841d099c344a5860041b4b6c7546` |
| AUTHORIZED PARENT | rollback target `6ab1a035c7ef3b14a23a4ec6` (what production serves) |
| bound to | work order 006, `authorized_by founder`, `manifest_source_commit ff6b506d`, `launch_participation_sha256 837d37d3…` (the new founder decision), the corrected package digest and market bundle (in `authorization_source`) |
| STATUS | AUTHORIZED, UNCONSUMED (`deploy_id null`); `deployability_problems []`, `verify_authorization []` |
| AUTHORIZED records in the repo | exactly this one |

The live `global_deployment_manifest.json` was **not** written, because this order stops before deployment. The candidate
manifest is `global_deployment_manifest_candidate_west_palm_beach_006.json`, and the deploying order writes the live
manifest from these same bytes.

## PHASE 14 — LIVE SAFETY (2026-09-24T21:00Z)

Resolver RESOLVED YES, `6ab1a035c7ef3b14a23a4ec6`, 32 / 2375 / 2711, host verified. External sitemap `e81961ae…`
(unchanged), 2711 `<loc>`, 0 WPB.

| Route | |
|---|---|
| `/pet-friendly-hotels/west-palm-beach-fl/` | 404 |
| `/pet-friendly-hotels/west-palm-beach-fl/hilton-garden-inn-boca-raton/` | 404 |
| `/pet-friendly-hotels/west-palm-beach-fl/apple-ten-hospitality-management-inc/` | 404 |
| `/pet-friendly-hotels/west-palm-beach-fl/boca-raton/` · `/policy-comparison/` | 404 · 404 |
| `/pet-friendly-hotels/fort-lauderdale-fl/` | 200 |
| `/pet-friendly-hotels/augusta-ga/` | 200 |
| `/pet-friendly-hotels/detroit-ann-arbor-mi/` | 404 |

Nothing from West Palm Beach is served.

## Commits

`ff6b506d` founder decision and participation · `430ea9d2` candidate accounting, candidate manifest, new deployment
authorization and helpers · the report commit. No broad regression and no factory code change (the three new modules
are WPB-local helpers, as in 003).

---

## FINAL ANSWERS

1. CURRENT LIVE DEPLOYMENT = `6ab1a035c7ef3b14a23a4ec6`
2. CURRENT LIVE MARKETS = 32
3. CORRECTED PACKAGE = `pkg-west-palm-beach-fl-94d6f4115daa9b88`
4. CORRECTED PACKAGE DIGEST = `sha256:94d6f4115daa9b88a8773d2b73b49593c5de4a4757125def52b7ba17c25ec086`
5. CORRECTED MARKET BUNDLE SHA = `711760f09faddc8022b5d55a681c0ccd0937151a2d61be34d67cbdd0c934ef45`
6. OLD AUTHORIZATION STATUS = SUPERSEDED (terminal, unconsumed)
7. DEPLOYABLE OLD AUTH REMAINING = 0
8. OLD AUTHORIZATION TRANSFERS = NO
9. NEW FOUNDER AUTHORIZATION CREATED = YES
10. NEW FOUNDER AUTHORIZATION ID = `PTF-WEST-PALM-BEACH-FL-FOUNDER-LAUNCH-AUTHORIZATION-006` (participation sha256 `837d37d3…`)
11. PARTICIPATION STATE = FOUNDER_AUTHORIZED_FOR_LAUNCH (32 → 33)
12. PARENT LOOKUP = PASS
13. PARENT ROUTES PRESERVED = PASS
14. UNCHANGED BUNDLES REUSED = 32
15. UNCHANGED MARKETS REBUILT = 0
16. PHYSICAL FRAGMENTS RERENDERED = 33 (whole-site composer, no release store; not reuse)
17. WEST PALM BEACH BUNDLES BUILT = 1
18. AUTHORIZED CANDIDATE BUNDLE = `23728b4bff71c66d0a9a063de3882d744f92465f5f568f72b3caf16ca8641d78`
19. AUTHORIZED CANDIDATE SITEMAP = `8ae34cea1c7e384f0f4c8499066c5ff2f9ca841d099c344a5860041b4b6c7546`
20. CANDIDATE MARKETS = 33
21. CANDIDATE PROFILES = 2424
22. CANDIDATE RELEASE-INDEX ROUTES = 2701
23. CANDIDATE SERVED ROUTES = 2767
24. WEST PALM BEACH PROFILES = 49
25. HILTON GARDEN INN BOCA RATON PRESENT = YES
26. OLD APPLE TEN PROFILE PRESENT = NO
27. OLD APPLE TEN ROUTE PRESENT = NO
28. FAST RECEIPT NONEMPTY = YES (320 / 304)
29. ALL RELEASE GATES = PASS
30. UNEXPECTED DELTA = [] / [] / []
31. CANDIDATE DEPLOYABLE = YES
32. NEW DEPLOYMENT AUTHORIZATION = `ptf-auth-west-palm-beach-006-23728b4bff71`
33. NEW DEPLOYMENT AUTH STATUS = AUTHORIZED / UNCONSUMED
34. CURRENT LIVE MODIFIED = NO
35. DEPLOYMENT PERFORMED = NO
36. WEST PALM BEACH LIVE = NO
37. origin == HEAD = YES (after the push)
38. tree clean = YES
39. READY FOR WEST PALM BEACH PRODUCTION DEPLOYMENT = YES

WEST PALM BEACH NEW FOUNDER AUTHORIZATION = PASS
OLD AUTHORIZATION TRANSFERS = NO
NEW AUTHORIZED CANDIDATE = PASS
UNCHANGED MARKETS REBUILT = 0
CURRENT LIVE MODIFIED = NO
WEST PALM BEACH DEPLOYED = NO
READY FOR WEST PALM BEACH PRODUCTION DEPLOYMENT = YES
