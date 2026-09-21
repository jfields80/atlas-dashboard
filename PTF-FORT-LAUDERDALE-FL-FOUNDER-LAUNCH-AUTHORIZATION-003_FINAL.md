# PTF-FORT-LAUDERDALE-FL-FOUNDER-LAUNCH-AUTHORIZATION-003 — FINAL

**Worktree** `C:\Atlas-Fort-Lauderdale-FL-Hardened-V1`
**Branch** `worker/ptf-fort-lauderdale-fl-market-001`
**Market** `fort-lauderdale-fl`
**Source commit at authorization** `0cc2817b536eda2b62e59f9b05e8da38ae6ecc85`

Fort Lauderdale is **founder-authorized** and an **exact authorized production candidate**
exists, verified and deterministic. **It is not deployed and it is not live.** Netlify was
never invoked, no deployment record was created, the live deployment manifest was not
overwritten, and the deployment authorization is written AUTHORIZED and left UNCONSUMED —
exactly where this order says to stop.

---

## PHASE 1 — CURRENT LIVE REVERIFIED

Resolved with the repaired resolver, host-verified, never from `origin/main` (which the
resolver itself still reports as stale). Re-read at the start of this order and again at the
end; identical both times.

| | |
|---|---|
| CURRENT LIVE SOURCE COMMIT | `fbaf6f73a8e4ed7fa5cf3d81588219d513743bcd` |
| built_from_commit | `95d23162ea2ae6528045fb56648e15358ae0c6f7` |
| CURRENT LIVE DEPLOYMENT | `6ab071a5b7561c33aff6c17b` |
| CURRENT LIVE BUNDLE SHA | `b2ad54b9be8b8a0121b8b664ef95e6d4dcf3feb873b4b23558c3721cdc06732a` |
| CURRENT LIVE SITEMAP SHA | `5ac34c75d6ba22d87b5da9d9ff40844dc2e986d7b778760849c03769bb088980` |
| CURRENT LIVE MARKETS | 31 |
| CURRENT LIVE PROFILES | 2290 |
| CURRENT LIVE SERVED SITEMAP ROUTES | 2614 |
| CURRENT LIVE RELEASE-INDEX ROUTES | 2550 |
| HOST VERIFIED | **true** |

Current live has **not** advanced since registration, so the parent is not stale and this
authorization is bound to the parent the readiness packet named.

---

## PHASE 2 — REGISTERED PACKAGE VERIFIED

| | |
|---|---|
| REGISTERED PACKAGE | `pkg-fort-lauderdale-fl-398ca08f89a75b8a` |
| PACKAGE DIGEST | `sha256:398ca08f89a75b8aab47af83a8a56ad4300075b37fa7f10c9ec31df4fdda0518` |
| recomputed digest | **matches** (`sealed_market_package.digest_of`) |
| `verify_seal` / `validate` | `()` / `()` — clean |
| execution zone | `REGISTERED_LIVE` |
| created_from_source_sha | `4a45d973…` |
| census / PF / NP / unresolved | 461 / 85 / 53 / 323 |
| declared routes | 96 |
| FAST | 15/15 PASS, determinism `BYTE_IDENTICAL` |
| ELIGIBLE / FULL_REGRESSION_REQUIRED | YES / NO |

Nothing was reopened. The census, discovery, Firecrawl, attended-browser acquisition, the
Marriott closure and the competitor work were all read from committed bytes. No provider was
called and no acquisition lane was re-run.

---

## PHASE 3 — FOUNDER AUTHORIZATION

**FOUNDER AUTHORIZATION ID** `PTF-FORT-LAUDERDALE-FL-FOUNDER-LAUNCH-AUTHORIZATION-003`

| | |
|---|---|
| AUTHORIZED MARKET | `fort-lauderdale-fl` |
| AUTHORIZED PACKAGE | `pkg-fort-lauderdale-fl-398ca08f89a75b8a` |
| AUTHORIZED SOURCE COMMIT | `0cc2817b536eda2b62e59f9b05e8da38ae6ecc85` |
| AUTHORIZED PARENT | deploy `6ab071a5b7561c33aff6c17b`, release digest `sha256:1bbcb59d60b999065fe9be1f140cf544026a431c15d30c5049d7d23c25eaeac7` |
| DECISION BASIS | 461 census identities, 85 approved pet-friendly profiles, 53 verified-no-pets, 323 unresolved, ACTIONABLE UNRESOLVED 0 — all derived from committed authority at write time, none typed |
| decided_by | `founder` |
| decided_on | 2026-09-21 |

The record is a RECORD of a decision, not the decision. The founder made it in this order's
own words: *"The founder explicitly grants launch authorization for: fort-lauderdale-fl"* and
*"The founder explicitly accepts launching the current safe cohort."* The module writes that
down and refuses to do anything else — it aborts if the market is already authorized, if there
is not exactly one row for it, or if the flip would add anything other than Fort Lauderdale or
remove anything at all.

**The limits of the grant are recorded inside the record itself**, because a later reader
must not be able to mistake the scope. `decision_basis.not_authorized_by_this_decision`:

- weaker evidence rules
- anti-bot bypass
- invented dual-brand identity rulings
- publication of held properties

Nothing about *which* Fort Lauderdale identities publish changed. This decision authorizes the
market, not any of its held rows.

---

## PHASE 4 — PARTICIPATION

`launch_participation.json` was **REISSUED**, never edited — a hand-added row breaks the
decision chain and makes every market read UNLISTED.

| | |
|---|---|
| PARTICIPATION STATE | `SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH` → **`FOUNDER_AUTHORIZED_FOR_LAUNCH`** |
| authorized before / after | 31 / 32 |
| gained | exactly `[fort-lauderdale-fl]` |
| lost | `[]` |
| supersedes | `PTF-FORT-LAUDERDALE-FL-REGISTRATION-AND-STAGING-002`, sha256 `5ea5affd…` |
| lineage records | 30 (every ancestor carried forward with its own digest) |
| `decision_problems` | `[]` |

All 31 previously live markets are preserved. **Detroit stays withheld** at
`SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH` — the decision named Fort Lauderdale and
nothing else. `release_contracts.verify_all()` after the flip: **33 markets, 0 problems.**

Fort Lauderdale is marked LIVE nowhere. Participation authorizes a market to be *built into*
the next production assembly; it does not deploy it.

---

## PHASE 5 — THE EXACT AUTHORIZED CANDIDATE

| | |
|---|---|
| AUTHORIZED CANDIDATE BUNDLE | `0ec5c6557d79eaf77a4065b6700c0a5807e9bfe282408dd4779804b33af3a40f` |
| candidate sitemap sha256 | `e81961ae76454ce608fcb39624d5147c8779f52b269faab9449138397cb8fa3d` |
| generated_from_commit | `0cc2817b536eda2b62e59f9b05e8da38ae6ecc85` |
| markets / profiles | 32 / 2375 |
| composed-bundle gates | **27/27 pass** |
| route collisions / global shadowing / broken links | 0 / 0 / 0 |
| artifact | `C:\t\ftl3a` (14,461 files) |

PARENT LOOKUP = **PASS** — resolved by DEPLOYED BUNDLE (`b2ad54b9…` → `6ab071a5b7561c33aff6c17b`),
not by a registration-sensitive release-manifest lookup, because the release-store key moves on
registration and a manifest-only lookup would have failed here for that reason alone.
PARENT ROUTES PRESERVED = **PASS**.

### Physical re-rendering, reported separately — this is the order's own requirement

`release_coordinator plan` reports, against this worktree:

```
fragments_available_from_store : 0
fragments_needing_build        : 31
```

This worktree has **no populated release store**, so the whole-site composer physically
re-rendered every fragment. **That is not fragment reuse and is not labelled as such here.**

| Accounting | Value | What it means |
|---|---|---|
| UNCHANGED BUNDLES REUSED | **31** | release-factory/bundle-cache level: 31 unchanged markets were inherited by content identity, and each one's composed bytes are reproduced identically (0 prior-market files changed, proven in Phase 10) |
| UNCHANGED MARKETS REBUILT | **0** | no unchanged market's authority, package or published bytes changed |
| **PHYSICAL FRAGMENTS RERENDERED** | **32** | what the composer actually did in this worktree: all 31 unchanged fragments plus Fort Lauderdale |
| FORT LAUDERDALE BUNDLES BUILT | **1** | `e823657e4e620abe552c3298976ad4a9d618e07bfac69d1819bf1bff2db0d37b` |

Candidate-byte preservation is what governs, and it holds exactly: re-rendering 31 fragments
produced the same bytes the live release serves, which is the point of a deterministic
composer. Had any of those 31 come out different, Phase 10 would have caught it as a
prior-market change; none did.

Assembly cost: build A ≈ 48 min, build B ≈ 39 min.

---

## PHASE 6 — ROUTE ACCOUNTING, THE TWO SYSTEMS KEPT APART

|  | RELEASE-INDEX ROUTES | SERVED SITEMAP ROUTES |
|---|---|---|
| current live | 2550 | 2614 |
| **candidate** | **2646** | **2711** |
| delta | +96 | **+97** |

They are not equal and were never assumed to be. Each was derived from its own source: the
release-index totals from `release_index` over the committed authority, the served totals read
as **route SETS** out of each bundle's own `sitemap.xml`.

**The exact difference.** A market's release-index routes are the routes it OWNS: its hub, its
publishing corridors and its hotel profiles. The served sitemap additionally publishes the
release-global surface no market owns (the apex, the category root, the editorial and legal
pages, the market directory) — 64 routes on both sides — **plus each market's
policy-comparison page, which is published but is not a route the release index counts as
owned.** Fort Lauderdale brings one such page,
`/pet-friendly-hotels/fort-lauderdale-fl/policy-comparison/`, which is the entire +1.

Set-level proof, not arithmetic: **97 routes added, 0 removed, and every single added route is
a `fort-lauderdale-fl` route.**

---

## PHASE 7 — CANDIDATE ACCOUNTING

| | |
|---|---|
| FORT LAUDERDALE PROFILES | **85** |
| FORT LAUDERDALE HUB ROUTES | **1** |
| FORT LAUDERDALE CORRIDOR ROUTES | **10** |
| FORT LAUDERDALE OTHER ROUTES | **0** |
| FORT LAUDERDALE RELEASE-INDEX MARKET ROUTES | **96** |
| CANDIDATE MARKETS | **32** |
| CANDIDATE PROFILES | **2375** |
| CANDIDATE RELEASE-INDEX ROUTES | **2646** |
| CANDIDATE SERVED SITEMAP ROUTES | **2711** |

Publishing corridors (10): `coral-springs-coconut-creek`, `cypress-creek`, `dania-beach`,
`deerfield-beach`, `fll-airport-sr84`, `fort-lauderdale-beach`, `hollywood-beach`,
`pembroke-pines-miramar`, `plantation-davie`, `port-everglades-17th-street`.

Suppressed corridors (8), each below its own publication minimum and **not forced**:
`downtown-las-olas`, `galt-ocean-lauderdale-by-the-sea`, `hallandale-beach`, `hollywood`,
`oakland-park-wilton-manors`, `pompano-beach`, `sunrise-tamarac-lauderhill`,
`weston-southwest-ranches`.

Every number above is derived from the committed authority and the composed bundle. None is
typed.

---

## PHASE 8 — DELTA SAFETY

| | |
|---|---|
| UNEXPECTED MARKET DELTA | `[]` |
| UNEXPECTED PROFILE DELTA | `[]` |
| UNEXPECTED ROUTE DELTA | `[]` |
| `release_index.compare` | `passed: true`, `findings: []`, `finding_counts: {}` |
| parent markets preserved | **YES** (all 31) |
| parent routes preserved | **YES** (2550 ⊆ 2646) |
| parent profiles preserved | **YES** (2290 + 85 = 2375) |

The candidate release index recomposes to
`sha256:e68857b4c564b2ed6984e227bb16e56d976595f88a5b7ac31e8b285907bb2587` — **the exact digest
the registration order projected before the founder flip existed.** The authorized candidate is
the candidate that was validated, not a new one that happens to resemble it.

Fort Lauderdale is the only newly authorized market.

---

## PHASE 9 — HOLD / EXCLUSION SAFETY

| | |
|---|---|
| APPROVED FORT LAUDERDALE PROFILES | **85** |
| UNAPPROVED / HELD FORT LAUDERDALE PROFILES IN CANDIDATE | **0** |
| Fort Lauderdale pages in the candidate | 97 = 85 hotel profiles + 1 hub + 10 corridors + 1 policy-comparison |

Kept unpublished, exactly as adjudicated (461 rows, one disposition each):

| Rows | Disposition | In the candidate? |
|---|---|---|
| 85 | `CLEAN_PET_FRIENDLY` | published |
| 53 | `CLEAN_VERIFIED_NO_PETS` | canonical exclusion representation only — not profiles |
| 90 | `ROUTING_HOLD` | no |
| 89 | `ACCESS_BLOCKED` | no |
| 69 | `SOURCE_SILENT` | no |
| 38 | `IDENTITY_MISMATCH_HOLD` (includes the four dual-brand halves) | no |
| 37 | `EVIDENCE_HOLD` | no |

### MIRAMAR / CLEVELAND EXCLUSION COLLISION SAFE = **PASS**

The registration order found that Florida DBPR licenses a Miramar property as the bare chain
flag "Holiday Inn Express & Suites", and because `hotel_exclusions.json` matches on the
normalized canonical name **across every market**, that Fort Lauderdale row was barring
**Cleveland's** Holiday Inn Express & Suites at 30500 Clemens Rd, Westlake OH 44145.

Explicitly re-verified in the authorized candidate, as this order requires:

```
pet-friendly-hotels/cleveland-akron-canton/holiday-inn-express-suites/index.html
  live      sha256:3147177b0b656ea6e4a8489b36f032f273e8a434d68f253de07a3fcefc8dd83e
  candidate sha256:3147177b0b656ea6e4a8489b36f032f273e8a434d68f253de07a3fcefc8dd83e
  BYTE-IDENTICAL — Cleveland's profile is present and unsuppressed
```

---

## PHASE 10 — BYTE / FILE PRESERVATION

Candidate compared to the CURRENT VERIFIED LIVE bundle (`C:\t\mia5a`, `b2ad54b9…`) file by
file, by sha256, from each bundle's own `file_hash_manifest.json`.

| | |
|---|---|
| files live / candidate | 13,943 / 14,461 |
| **FILES ADDED** | **518** — all `fort-lauderdale-fl`; 0 prior-market, 0 unclassified |
| **FILES REMOVED** | **0** |
| **FILES CHANGED** | **1** — `sitemap.xml`, and nothing else |

| Requirement | Result |
|---|---|
| 0 unexplained removed files | **0 removed at all** |
| 0 unexplained prior-market changes | **0 prior-market files changed** |
| 0 prior-profile loss | **0** |
| 0 prior-route loss | **0** |
| unclassified paths | **0** |

### Every changed global artifact, classified

Exactly one global artifact moved: **`sitemap.xml`**, gaining Fort Lauderdale's 97 published
routes and losing nothing.

The other global artifacts — `index.html` (apex), `pet-friendly-hotels/index.html` (category
root), `llms.txt`, `robots.txt`, `_headers`, `_redirects` — are **byte-identical to live**.
That is correct and worth stating plainly, because it looks surprising: Fort Lauderdale joins
with `show_in_navigation=false` and `show_in_sitemap=false`, exactly as every recently launched
market does at this stage. Those flags govern the market hub's place in global navigation and
the market directory — not whether its profile URLs are indexed. So the navigation surface does
not move, and the sitemap does.

---

## PHASE 11 — RELEASE GATES

| Gate | Result |
|---|---|
| FOUNDER AUTHORIZATION | **PASS** — decided_by `founder`, chain intact, `decision_problems []` |
| PACKAGE IDENTITY | **PASS** — digest recomputes, seal and validation clean |
| PARENT IDENTITY | **PASS** — found by deployed bundle `b2ad54b9…` |
| PARENT ROUTES PRESERVED | **PASS** |
| PROFILE PRESERVATION | **PASS** — 2290 + 85 = 2375 |
| ROUTE PRESERVATION | **PASS** — 0 removed, live ⊆ candidate |
| MARKET DELTA | **PASS** — +1, Fort Lauderdale only |
| PARTICIPATION | **PASS** — 31 → 32, gained exactly one, lost none |
| **CANDIDATE DETERMINISM** | **PASS — MEASURED** |
| DEPLOYMENT ELIGIBILITY | **PASS** |
| composed-bundle gates | **27/27 PASS** |
| accounting gates | **ALL PASS**, `problems: []` |

**Determinism was measured, not inherited.** Two independent full assemblies of the identical
tree:

```
build A (C:\t\ftl3a) bundle_sha256 0ec5c6557d79eaf77a4065b6700c0a5807e9bfe282408dd4779804b33af3a40f
build B (C:\t\ftl3b) bundle_sha256 0ec5c6557d79eaf77a4065b6700c0a5807e9bfe282408dd4779804b33af3a40f
14,461 files compared, 0 differing  ->  BYTE_IDENTICAL
```

The market-level FAST rule K already proved the Fort Lauderdale bundle deterministic; this
proves the whole 32-market composed site deterministic, which is the artifact a deploy would
actually ship.

---

## TARGETED TEST DIFFERENTIAL — 0 NEW FAILURES

This order did not ask for a regression run and no broad suite was launched. I ran a targeted
set anyway, because this order rewrites the participation record, and then proved every
failure it found is pre-existing by **failure-set identity** against a clean worktree at
`0cc2817b` (my changes were uncommitted, so HEAD is exactly the pre-authorization state).

| Selection | Working tree (authorized) | Clean baseline at `0cc2817b` | Identical? |
|---|---|---|---|
| `test_participation_lineage_contract_006`, `test_deployment_authorization_047`, `test_prod003_launch_safety`, `test_per_market_release_contracts` | 4 failed, 439 passed, 2 skipped (23:22) | 4 failed, 439 passed, 2 skipped (27:02) | **YES** — same 4 IDs |
| the 4 failing tests in `test_launch_participation_046` | 4 failed (18.7 s) | 4 failed (20.9 s) | **YES** — same 4 IDs |

**CLASSIFY ALL TARGETED FAILURES = PRE_EXISTING**
**NEW REPAIR / AUTHORIZATION FAILURES = 0**

The eight pre-existing failures, for the record:

```
test_launch_participation_046.py::test_the_record_is_committed_and_names_its_decision
test_launch_participation_046.py::test_only_the_live_set_is_founder_authorized
test_launch_participation_046.py::test_indianapolis_is_now_selected
test_launch_participation_046.py::test_the_record_still_vetoes_a_market_that_is_source_ready
test_participation_lineage_contract_006.py::TestTheCommittedRecordAndItsOneDocumentedException::test_the_committed_record_loads_and_its_chain_is_reachable
test_participation_lineage_contract_006.py::TestTheCommittedRecordAndItsOneDocumentedException::test_the_repair_names_the_block_the_next_write_must_carry
test_participation_lineage_contract_006.py::TestTheCommittedRecordAndItsOneDocumentedException::test_the_next_write_would_produce_exactly_that_block
test_per_market_release_contracts.py::TestContractRegistry::test_every_market_with_verified_inventory_has_a_contract
```

**Worth a founder's attention, though it is outside this order's scope to repair.** These are
stale HISTORICAL PINS, not broken behaviour. `test_launch_participation_046.py` asserts
`"Charlotte" in decision["reason"]` and pins an Indianapolis/Cincinnati-era live set; its own
comment says *"The CURRENT decision is the Charlotte registration. Each reissue moves these
lines."* Every market registered since Charlotte has moved that decision and nobody moved the
pin, so the file has been failing for many launches — it was failing before Fort Lauderdale
existed and it will keep failing after. The same is true of the participation-lineage pins.
**These tests currently assert nothing about correctness, which means the participation record
has had no effective test guard for several launches.** That is a real gap and deserves its own
work order.

---

## PHASE 12 — DEPLOYMENT AUTHORIZATION (CREATED, NOT CONSUMED)

| | |
|---|---|
| DEPLOYMENT AUTHORIZATION CREATED | **YES** |
| DEPLOYMENT AUTHORIZATION ID | `ptf-auth-fort-lauderdale-003-0ec5c6557d79` |
| AUTHORIZED BUNDLE | `0ec5c6557d79eaf77a4065b6700c0a5807e9bfe282408dd4779804b33af3a40f` |
| AUTHORIZED SITEMAP | `e81961ae76454ce608fcb39624d5147c8779f52b269faab9449138397cb8fa3d` |
| status | **AUTHORIZED** |
| bound to the candidate bytes | **true** |
| `deployability_problems` / `verify_authorization` | `[]` / `[]` |
| DEPLOYABLE | **true** |
| **CONSUMED** | **false** — no `deploy_id`, no deployment record |
| source commit | `0cc2817b…` |
| rollback target | `6ab071a5b7561c33aff6c17b` |
| target | `pettripfinder-prod` / `https://pettripfinder.com` |

It was created **only** for the exact authorized candidate bytes, and `bundle_sha256` is
checked against the composed bundle rather than asserted.

**The live deployment manifest was deliberately NOT overwritten.** Every recent launch wrote
`deploy/netlify/global_deployment_manifest.json` and deployed minutes later, so manifest and
record agreed again immediately. This order stops before deployment, so writing the live
manifest would leave the repository's own cross-check (`release_coordinator inspect`:
*"disagreement with the record is a problem, not a tiebreak"*) describing a bundle production
does not serve. The candidate manifest therefore went to
`global_deployment_manifest_candidate_fort_lauderdale_003.json`, and
`global_deployment_manifest.json` still reads `b2ad54b9…` — what production actually serves.
The deploying order writes the live manifest from these same bytes.

---

## PHASE 13 — FINAL LIVE SAFETY CHECK

Re-verified externally, against the real host, after every write this order made:

| Probe | Result |
|---|---|
| resolver | `fbaf6f73…` / `6ab071a5b7561c33aff6c17b` / 31 / 2290 / 2614, host verified — **unchanged** |
| `/pet-friendly-hotels/fort-lauderdale-fl/` | **404** |
| `/pet-friendly-hotels/fort-lauderdale-fl/dania-beach/` | **404** |
| `/pet-friendly-hotels/fort-lauderdale-fl/policy-comparison/` | **404** |
| `/pet-friendly-hotels/miami-fl/` | 200 |
| served sitemap sha256 | `5ac34c75…` — **matches the live record exactly** |
| served sitemap routes | 2614 |
| occurrences of `fort-lauderdale-fl` in the served sitemap | **0** |
| `deploy/netlify/deployment_records/` | no `fort-lauderdale` record |

CURRENT LIVE = **unchanged**. FORT LAUDERDALE SERVED LIVE = **NO**. No Fort Lauderdale
production route is served.

---

## WHAT CHANGED IN THE REPOSITORY

Seven paths, all legitimate authorization artifacts, and nothing else:

```
M  deploy/netlify/launch_participation.json                                     (REISSUED, 31->32)
A  deploy/netlify/deployment_authorizations/ptf-auth-fort-lauderdale-003-0ec5c6557d79.json
A  deploy/netlify/global_deployment_manifest_candidate_fort_lauderdale_003.json
A  launch_packages/pettripfinder/markets/reports/fort_lauderdale_fl_launch_authorization_003.json
A  scripts/pettripfinder/fort_lauderdale_fl_launch_participation_003.py
A  scripts/pettripfinder/fort_lauderdale_fl_deployment_authorization_003.py
A  scripts/pettripfinder/fort_lauderdale_fl_candidate_accounting_003.py
```

`global_deployment_manifest.json`, every deployment record, every other market's shard,
authority, contract and package: untouched.

---

## WHAT A DEPLOYING ORDER STILL HAS TO DO

Nothing in this order deployed anything, so the next order owns all of it: consume
`ptf-auth-fort-lauderdale-003-0ec5c6557d79`, run `netlify deploy --prod` (which auto mode
refuses without explicit user permission — ask before opening that gate), write the live
manifest from these same authorized bytes, write the deployment record, and verify the live
routes. Rollback target is `6ab071a5b7561c33aff6c17b`. The authorized artifact is `C:\t\ftl3a`.

---

## FINAL ANSWERS

1. **CURRENT LIVE SOURCE COMMIT** = `fbaf6f73a8e4ed7fa5cf3d81588219d513743bcd`
2. **CURRENT LIVE DEPLOYMENT** = `6ab071a5b7561c33aff6c17b`
3. **CURRENT LIVE MARKETS** = 31
4. **CURRENT LIVE PROFILES** = 2290
5. **CURRENT LIVE SERVED SITEMAP ROUTES** = 2614
6. **CURRENT LIVE RELEASE-INDEX ROUTES** = 2550
7. **REGISTERED PACKAGE** = `pkg-fort-lauderdale-fl-398ca08f89a75b8a`
8. **PACKAGE DIGEST** = `sha256:398ca08f89a75b8aab47af83a8a56ad4300075b37fa7f10c9ec31df4fdda0518`
9. **FOUNDER AUTHORIZATION CREATED** = YES
10. **FOUNDER AUTHORIZATION ID** = `PTF-FORT-LAUDERDALE-FL-FOUNDER-LAUNCH-AUTHORIZATION-003`
11. **PARTICIPATION STATE** = `FOUNDER_AUTHORIZED_FOR_LAUNCH` (31 → 32 authorized; Detroit still withheld)
12. **PARENT LOOKUP** = PASS (by deployed bundle `b2ad54b9…`)
13. **PARENT ROUTES PRESERVED** = PASS
14. **UNCHANGED BUNDLES REUSED** = 31
15. **UNCHANGED MARKETS REBUILT** = 0
16. **PHYSICAL FRAGMENTS RERENDERED** = 32 (no populated release store in this worktree; reported separately and never called reuse)
17. **FORT LAUDERDALE BUNDLES BUILT** = 1 (`e823657e4e620abe…`)
18. **AUTHORIZED CANDIDATE BUNDLE** = `0ec5c6557d79eaf77a4065b6700c0a5807e9bfe282408dd4779804b33af3a40f`
19. **CANDIDATE MARKETS** = 32
20. **CANDIDATE PROFILES** = 2375
21. **CANDIDATE RELEASE-INDEX ROUTES** = 2646
22. **CANDIDATE SERVED SITEMAP ROUTES** = 2711
23. **FORT LAUDERDALE PROFILES** = 85
24. **FORT LAUDERDALE HUB ROUTES** = 1
25. **FORT LAUDERDALE CORRIDOR ROUTES** = 10
26. **FORT LAUDERDALE RELEASE-INDEX ROUTES** = 96
27. **UNAPPROVED FORT LAUDERDALE PROFILES IN CANDIDATE** = 0
28. **MIRAMAR / CLEVELAND EXCLUSION COLLISION SAFE** = PASS (byte-identical Cleveland profile)
29. **ALL RELEASE GATES** = PASS
30. **UNEXPECTED DELTA** = NONE — markets `[]`, profiles `[]`, routes `[]`
31. **CANDIDATE DEPLOYABLE** = YES (AUTHORIZED, deployability_problems `[]`)
32. **DEPLOYMENT AUTHORIZATION CREATED** = YES — `ptf-auth-fort-lauderdale-003-0ec5c6557d79`, UNCONSUMED
33. **CURRENT LIVE MODIFIED** = NO
34. **DEPLOYMENT PERFORMED** = NO
35. **FORT LAUDERDALE LIVE** = NO
36. **origin == HEAD** = YES
37. **tree clean** = YES
38. **READY FOR FORT LAUDERDALE PRODUCTION DEPLOYMENT** = YES

---

FORT LAUDERDALE FOUNDER AUTHORIZATION = PASS
FORT LAUDERDALE AUTHORIZED CANDIDATE = PASS
UNAPPROVED FORT LAUDERDALE PROFILES = 0
CURRENT LIVE MODIFIED = NO
FORT LAUDERDALE DEPLOYED = NO
READY FOR FORT LAUDERDALE PRODUCTION DEPLOYMENT = YES

STOP.
