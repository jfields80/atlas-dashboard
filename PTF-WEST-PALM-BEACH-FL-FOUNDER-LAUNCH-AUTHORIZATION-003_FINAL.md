# PTF-WEST-PALM-BEACH-FL-FOUNDER-LAUNCH-AUTHORIZATION-003 — FINAL

**Worktree** `C:\Atlas-West-Palm-Beach-FL-Hardened-V1`
**Branch** `worker/ptf-west-palm-beach-fl-market-001`
**Market** `west-palm-beach-fl`
**Registered package** `pkg-west-palm-beach-fl-789c0187e366abe8`
**Candidate artifact** `C:\t\wpb3a` (14,760 files) · second assembly `C:\t\wpb3b`

The founder's launch authorization is recorded, the exact authorized candidate is built and
gated, and a deployment authorization is written **AUTHORIZED and UNCONSUMED**. **Nothing was
deployed.** Netlify was never invoked, no deployment record exists, the live manifest was not
touched, and every West Palm Beach route still returns 404 in production.

---

## PHASE 1 — CURRENT LIVE, RESOLVED TWICE

Resolved with the repaired resolver (`release_index live-source --fetch --verify-host`), at the
start of the order and again after every write it made. Byte-for-byte the same both times, and
identical to the parent the registration used.

| | |
|---|---|
| CURRENT LIVE SOURCE COMMIT | `e82120cce7e48c62d3c1057a6c82785bed920485` (built_from `0cc2817b`) |
| CURRENT LIVE DEPLOYMENT | `6ab1a035c7ef3b14a23a4ec6` |
| CURRENT LIVE BUNDLE | `0ec5c6557d79eaf77a4065b6700c0a5807e9bfe282408dd4779804b33af3a40f` |
| CURRENT LIVE SITEMAP | `e81961ae76454ce608fcb39624d5147c8779f52b269faab9449138397cb8fa3d` |
| CURRENT LIVE MARKETS | **32** |
| CURRENT LIVE PROFILES | **2,375** |
| CURRENT LIVE RELEASE-INDEX ROUTES | **2,646** |
| CURRENT LIVE SERVED ROUTES | **2,711** |
| HOST VERIFIED | **true** |

`origin/main` is stale and was not used; the resolver says so itself
(`origin_main_contains_live: False`). Current live had **not** advanced, so nothing was built
against a stale parent.

---

## PHASE 2 — THE REGISTERED PACKAGE, RE-VERIFIED FROM COMMITTED BYTES

| | |
|---|---|
| PACKAGE | `pkg-west-palm-beach-fl-789c0187e366abe8` |
| DIGEST | `sha256:789c0187e366abe8c199feb799ec691241d83ae81c3178e9cd4de41dde2c7bf8` |
| digest recomputed from the file | **identical** · `verify_seal` [] · `validate` [] |
| PACKAGE REPRODUCIBLE | **YES** |
| SOURCE READY / COVERAGE READY | **YES / YES** |
| ACTIONABLE UNRESOLVED | **0** |
| FAST | **15/15 PASS** (rules A–O, 0 UNKNOWN, 0 FAILED) |
| ELIGIBLE | **YES** |
| FULL_REGRESSION_REQUIRED | **NO** |

The committed blob is LF and the worktree file is CRLF (`core.autocrlf=true`); normalised, the
bytes are identical. That is the repository's own line-ending policy, not a difference in
content.

**Nothing was re-acquired.** No census, discovery, Firecrawl, Places or brand-browser call was
made. Firecrawl credits unchanged at 1,199.

---

## PHASES 3 & 4 — THE FOUNDER'S DECISION, RECORDED

| | |
|---|---|
| FOUNDER AUTHORIZATION ID | **`ptf-auth-west-palm-beach-003-217f87eeba72`** |
| AUTHORIZED PACKAGE | `pkg-west-palm-beach-fl-789c0187e366abe8` |
| AUTHORIZED SOURCE COMMIT | `b32cf356ee0a8e9df252ee9aa85261a369eda5cf` |
| AUTHORIZED PARENT | deploy `6ab1a035c7ef3b14a23a4ec6`, release-index digest `sha256:0ec19aa9…` |
| DECISION BASIS | 190 census identities · 49 pet-friendly profiles · 25 verified-no-pets · 116 unresolved but bounded · actionable unresolved 0 |

Participation, written by `launch_participation.extend_decision`:

| | |
|---|---|
| PARTICIPATION STATE | `SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH` → **`FOUNDER_AUTHORIZED_FOR_LAUNCH`** |
| authorized before / after | **32 / 33** |
| gained / lost | exactly `[west-palm-beach-fl]` / `[]` |
| supersedes | `PTF-WEST-PALM-BEACH-FL-REGISTRATION-AND-STAGING-002`, sha256 `5da443c1…` |
| lineage records | **32** (every ancestor carried forward with its own digest) |
| `decision_problems` | **[]** |
| Detroit | still `SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH` |
| `release_contracts.verify_all()` after the flip | **34 markets, 0 problems** |

I used the canonical `extend_decision` rather than building the decision block by hand. It is
the one writer that cannot drop `supersedes` or `lineage` — the chain nineteen launches lost
before `PTF-SUPERSESSIONS-LINEAGE-REPAIR-001` paid to put it back — and a founder decision is
exactly the write that lost it.

**No literal LIVE status was invented.** `FOUNDER_AUTHORIZED_FOR_LAUNCH` authorizes a market to
be *built into* the next assembly; it does not deploy it. `tests/pettripfinder/pins/supersessions.json`
was not touched: it records markets moved out from under *consumed* historical authorizations,
and belongs to the deploying order.

---

## PHASE 5 — THE EXACT AUTHORIZED CANDIDATE

| | |
|---|---|
| AUTHORIZED CANDIDATE BUNDLE | **`217f87eeba72c9f94c2eaf3ce82c37af35b261e8f21abb847c0b6337216c5054`** |
| AUTHORIZED CANDIDATE SITEMAP | **`31ac963ff95191fef42713b6c44dcbf5f1aa88dd97bbb1897566f0655e7b6005`** |
| markets / profiles | **33 / 2,424** |
| served sitemap routes | **2,767** |
| composed-bundle gates | **27/27 PASS** (`all_gates_pass: true`) |
| route collisions / global shadowing / broken links | 0 / 0 / 0 |
| artifact | `C:\t\wpb3a`, 14,760 files, 3,375 s |

| | |
|---|---|
| PARENT LOOKUP | **PASS** — resolved by DEPLOYED BUNDLE (`0ec5c655…` → `6ab1a035c7ef3b14a23a4ec6`) |
| PARENT ROUTES PRESERVED | **PASS** — live routes ⊆ candidate routes, 0 lost |

### Physical re-rendering, reported separately — the order's own requirement

`release_coordinator plan` against this worktree:

```
fragments_available_from_store : 0
fragments_needing_build        : 32
refusal                        : UNAUTHORIZED_ADDITION —
                                 "west-palm-beach-fl participates in the candidate
                                  but no authority admits it"
```

This worktree has **no populated release store**, so the whole-site composer physically rendered
every fragment: the build log shows **33 `Market scope:` passes**, one per participating market
including West Palm Beach. That is **PHYSICAL FRAGMENTS RERENDERED = 33**, and it is *not*
reuse — it is stated separately here precisely because calling it reuse would be false.

The `release_coordinator` refusal is the same shape Fort Lauderdale's authorization order
recorded. That lane is the ATLAS-THROUGHPUT-005 staging machine with production activation
DISABLED and its own admission authority (a staged release record), which this order does not
create. It is a reporting input, not a gate: the candidate is built by the whole-site assembler,
and every release gate below ran against the built artifact.

---

## PHASE 6 — TWO ROUTE ACCOUNTING SYSTEMS, DERIVED AND KEPT SEPARATE

**A. RELEASE-INDEX ROUTES** — what markets own, from `release_index`:

| | |
|---|---:|
| hotel profile routes | 49 |
| market hub | 1 |
| publishing corridors | 5 |
| **WEST PALM BEACH RELEASE-INDEX ROUTES** | **55** |

**B. SERVED SITEMAP ROUTES** — what the composed bundle publishes, read as a set from its own
`sitemap.xml`:

| | |
|---|---:|
| the 55 owned routes | 55 |
| its own `/policy-comparison/` — served, not market-owned | **+1** |
| **WEST PALM BEACH SERVED ROUTES** | **56** |

Not assumed: the module reads `comparison_route` from the candidate's own fragment manifest and
requires the served delta to equal *owned routes + the comparison page*. The 56 page files the
candidate adds under `pet-friendly-hotels/west-palm-beach-fl/` are the same 56.

| candidate totals | |
|---|---:|
| MARKETS | **33** |
| PROFILES | **2,424** |
| RELEASE-INDEX ROUTES | **2,701** |
| SERVED SITEMAP ROUTES | **2,767** |

Every one matches the projection the registration order made, measured on the artifact rather
than carried forward.

---

## PHASE 7 — CORRIDOR ACCOUNTING

**PUBLISHING CORRIDORS = 5**, exactly the five expected: `downtown-west-palm-beach`,
`palm-beach-gardens`, `palm-beach-international-airport`, `delray-beach`, `boca-raton`.

**SUPPRESSED = 10**: `boynton-beach`, `jupiter-tequesta`, `lake-worth-beach`,
`lantana-manalapan-hypoluxo`, `north-palm-beach-juno-beach`, `northwood-metrocentre`,
`palm-beach-worth-avenue`, `riviera-beach-singer-island`, `the-glades`, `western-communities`.

**FORCED CORRIDORS = 0.** Each suppressed corridor is below its own committed publication
minimum — Palm Beach / Worth Avenue at 0 pet-friendly over 11 census rows, Lake Worth Beach at 2
over 25. No thin page was created to make a number.

---

## PHASE 8 — HOLD / EXCLUSION SAFETY, CHECKED AGAINST THE BUILT ARTIFACT

| | |
|---|---:|
| APPROVED WEST PALM BEACH PROFILES | **49** |
| West Palm Beach pages in the candidate | 56 (49 profiles + 5 corridors + hub + comparison) |
| hotel profile pages | **49** |
| **UNAPPROVED / HELD PROFILES IN CANDIDATE** | **0** |
| unresolved kept unpublished | **116** |
| verified-no-pets kept as exclusions, not profiles | **25** |

Adjudication of the 190-row census: 49 `CLEAN_PET_FRIENDLY`, 25 `CLEAN_VERIFIED_NO_PETS`, 58
`ROUTING_HOLD`, 26 `SOURCE_SILENT`, 24 `ACCESS_BLOCKED`, 4 `IDENTITY_MISMATCH_HOLD`.

Every held identity was probed against the rendered candidate and **none is published**:

```
ben-west-palm ............................... not published
the-ben-autograph-collection ................ not published
courtyard-by-marriott-west-palm-beach-airport not published
sonesta-select-boca-raton ................... not published
casa-loma ................................... not published
cypress-lodge ............................... not published
mango-inn-bed-and-breakfast ................. not published
travel-inn-of-riviera ....................... not published
```

**One correction to the order's framing, so the record is accurate.** The **four
duplicate-premises halves** — `Ben West Palm` / `The Ben Autograph Collection` and
`Courtyard by Marriott West Palm Beach Airport` / `Sonesta Select Boca Raton` — are held
*outside* the 190-row census, as `IDENTITY_REVIEW_REQUIRED` / `IDENTITY_UNRESOLVED`. The four
`IDENTITY_MISMATCH_HOLD` rows *inside* the census are a different set: Casa Loma, Cypress Lodge,
Mango Inn Bed & Breakfast, Travel Inn of Riviera. Both sets stay unpublished, so the requirement
holds either way — but they are not the same four properties, and the report should not pretend
they are.

---

## PHASE 9 — CROSS-MARKET COLLISION SAFETY

West Palm Beach's registration repaired two collisions in the shared exclusion registry, which
matches on normalised canonical name **across every market**. Both sides of both collisions are
*excluded* identities, so neither has a published page to watch — the canary here is the registry
itself.

| | |
|---|---|
| registry rows | 1,171 |
| **DUPLICATE CANONICAL EXCLUSION NAMES** | **0** |
| bare `best western` | belongs to `tampa-fl` alone, count 1 |
| bare `comfort inn & suites` | belongs to `lexington-ky` alone, count 1 |
| West Palm Beach carries its first-party names | **yes** — `Best Western Intracoastal Inn`, `Comfort Inn & Suites Lantana` |
| **PRIOR LIVE PROFILE SUPPRESSION** | **0** — 0 prior-market files removed or changed |
| **ALL CURRENT MARKET CONTRACTS VERIFY** | **PASS** — 34/34, 0 disagreements |
| CROSS_MARKET_COLLISION_SAFE | **PASS** |

Neither collision was resolved by superseding another market's exclusion; both were fixed in
West Palm Beach's own source with the name the brand's own page states.

---

## PHASE 10 — GEOGRAPHY SAFETY

Counted by each DBPR licence's **own** county; admission is by the corridor registry over the
property's own postal code and by nothing else.

| County | Hotel-rank licences | **Admitted** | Owner |
|---|---:|---:|---|
| Palm Beach (home) | 197 in admitted codes | — | this market |
| **Broward** | 609 | **0** | **LIVE** `fort-lauderdale-fl` |
| **Miami-Dade** | 737 | **0** | **LIVE** `miami-fl` |
| **Monroe** | 319 | **0** | future `florida-keys-fl` |
| **St. Lucie** | 58 | **0** | future `treasure-coast-fl` |
| Martin | 29 | **3** | future `treasure-coast-fl` |

`live_market_inventory_admitted = 0`. The three Martin rows are the already-approved Tequesta
cases in the shared postal code **33469**, covered whole by the market's explicit border rule and
named individually — unchanged from the source-ready and registration states. **No new geography
expansion:** this order made no census, geography, authority or contract write at all.

---

## PHASE 11 — DELTA / BYTE SAFETY

| | |
|---|---|
| UNEXPECTED MARKET DELTA | **[]** |
| UNEXPECTED PROFILE DELTA | **[]** |
| UNEXPECTED RELEASE-INDEX ROUTE DELTA | **[]** |
| UNEXPECTED SERVED ROUTE DELTA | **[]** |
| `release_index.compare` | passed, `finding_counts {}`, `findings []` |
| parent markets / routes / profiles preserved | true / true / true |

| | |
|---|---:|
| files live | 14,461 |
| files candidate | 14,760 |
| **FILES ADDED** | **299** |
| **FILES REMOVED** | **0** |
| **FILES CHANGED** | **1** |

All 299 added files are West Palm Beach's — 56 pages and 243 `/go/` interstitials. The single
changed file is `sitemap.xml`, which describes the whole site and is regenerated for every
release. `index.html`, `llms.txt` and the category root did **not** change, because the market is
hidden from navigation at this stage.

| | |
|---|---:|
| unexplained removals | **0** |
| prior-market route loss | **0** |
| prior-profile loss | **0** |
| unexplained prior-market file changes | **0** |
| unclassified paths | **0** |

---

## PHASE 12 — RELEASE GATES

| Gate | |
|---|---|
| FOUNDER AUTHORIZATION | **PASS** — `decision_problems []`, chain of 32 extended |
| PACKAGE IDENTITY | **PASS** — digest recomputed, seal and shape clean |
| PARENT IDENTITY | **PASS** — found by deployed bundle `0ec5c655…` |
| PARENT ROUTES PRESERVED | **PASS** |
| PROFILE PRESERVATION | **PASS** — 2,375 + 49 = 2,424, measured on the artifact |
| ROUTE PRESERVATION | **PASS** — 0 served routes lost, live ⊆ candidate |
| MARKET DELTA | **PASS** — +1, West Palm Beach only |
| COLLISION SAFETY | **PASS** — 0 duplicate canonical names, 0 prior-market files touched |
| PARTICIPATION | **PASS** — 32 → 33, gained exactly one, lost none |
| **CANDIDATE DETERMINISM** | **PASS — MEASURED** |
| DEPLOYMENT ELIGIBILITY | **PASS** |
| composed-bundle gates | **27/27 PASS** |
| accounting gates | **ALL PASS**, `problems: []` |

**Determinism was measured, not inherited.** Two independent full assemblies of the identical
tree:

```
build A (C:\t\wpb3a) bundle_sha256 217f87eeba72c9f94c2eaf3ce82c37af35b261e8f21abb847c0b6337216c5054
build B (C:\t\wpb3b) bundle_sha256 217f87eeba72c9f94c2eaf3ce82c37af35b261e8f21abb847c0b6337216c5054
14,760 files compared, 0 differing  ->  BYTE_IDENTICAL
```

FAST rule K already proved the West Palm Beach *market bundle* deterministic; this proves the
whole 33-market composed site deterministic, which is the artifact a deploy would actually ship.

CANDIDATE = **AUTHORIZED** and **DEPLOYABLE**. It was not deployed.

---

## PHASE 13 — DEPLOYMENT AUTHORIZATION

| | |
|---|---|
| DEPLOYMENT AUTHORIZATION CREATED | **YES** |
| DEPLOYMENT AUTHORIZATION ID | **`ptf-auth-west-palm-beach-003-217f87eeba72`** |
| AUTHORIZED BUNDLE | `217f87eeba72c9f94c2eaf3ce82c37af35b261e8f21abb847c0b6337216c5054` |
| AUTHORIZED SITEMAP | `31ac963ff95191fef42713b6c44dcbf5f1aa88dd97bbb1897566f0655e7b6005` |
| ROLLBACK TARGET | **`6ab1a035c7ef3b14a23a4ec6`** (what production serves today) |
| status | **AUTHORIZED** |
| `deploy_id` | **None — UNCONSUMED** |
| `deployability_problems` / `verify_authorization_problems` | **[] / []** |
| bound to candidate bytes | **true** |
| deployment records for this market | **none** |
| target | `pettripfinder-prod` · `https://pettripfinder.com` |

The **live** manifest `deploy/netlify/global_deployment_manifest.json` was deliberately **not**
written. This order stops before deployment, and writing it would leave the repository's own
cross-check describing a bundle production does not serve. The candidate manifest went to
`global_deployment_manifest_candidate_west_palm_beach_003.json`; the deploying order writes the
live manifest from these same bytes.

---

## PHASE 14 — FINAL LIVE SAFETY

Re-resolved after every write: deployment `6ab1a035c7ef3b14a23a4ec6`, 32 markets, 2,375 profiles,
2,711 served routes, `host_verified true` — **unchanged**.

| Route | | |
|---|---|---|
| `/pet-friendly-hotels/west-palm-beach-fl/` | **404** | market hub |
| `/pet-friendly-hotels/west-palm-beach-fl/boca-raton/` | **404** | corridor |
| `/pet-friendly-hotels/west-palm-beach-fl/delray-beach/` | **404** | corridor |
| `/pet-friendly-hotels/west-palm-beach-fl/aloft-delray-beach/` | **404** | hotel profile |
| `/pet-friendly-hotels/west-palm-beach-fl/policy-comparison/` | **404** | comparison page |
| `/pet-friendly-hotels/fort-lauderdale-fl/` | **200** | still live |
| `/pet-friendly-hotels/miami-fl/` | **200** | still live |
| `/pet-friendly-hotels/detroit-ann-arbor-mi/` | **404** | still withheld |

**WEST PALM BEACH LIVE = NO.**

---

## AN UNRESOLVED FINDING THE FOUNDER SHOULD RULE ON BEFORE DEPLOYMENT

This order was told to build the exact authorized candidate, and it did. While selecting a probe
route I found a real defect *inside* that authorized cohort, and it would go live unchanged:

```
route   /pet-friendly-hotels/west-palm-beach-fl/apple-ten-hospitality-management-inc/
title   <title>Apple Ten Hospitality Management Inc Pet Policy | PetTripFinder West Palm Beach, Florida</title>
h1      Apple Ten Hospitality Management Inc

what it actually is
        Hilton Garden Inn Boca Raton, 8201 Congress Ave, Boca Raton FL 33487
        brand HILTON, property_code bctbrgi
        https://www.hilton.com/en/hotels/bctbrgi-hilton-garden-inn-boca-raton/
        the census row's own identity_key_aliases already carries "hilton garden inn boca raton"

why the wrong name won
        TIER 1  BRAND_INVENTORY_CITY_PAGE -> "Hilton Garden Inn Boca Raton"
        TIER 2  REGISTRY_FL_DBPR          -> "Apple Ten Hospitality Management Inc"   <- chosen
        "APPLE TEN HOSPITALITY MANAGEMENT INC" is the DBPR **licensee_name** field:
        a management company, not the property's trade name.
```

**The policy itself is correct and correctly sourced** — the evidence is an attended-browser read
of `…/bctbrgi-hilton-garden-inn-boca-raton/hotel-info/`, publication-grade, with the operator's own
quote. The identity is right. Only the *name* is wrong, and a tier-2 licensee name outranked a
tier-1 first-party brand name in the canonical-name chooser.

I audited all 49 published rows the same way. Eight differ from their tier-1 first-party name;
seven are benign brand variants (`Courtyard by Marriott Boynton Beach` vs `Courtyard Boynton
Beach`, `&` vs `and`, `I-95` vs `i95`). **This is the only substantive one.**

**I did not fix it, deliberately.** The founder authorized this exact sealed cohort, this order
names package `789c0187…` by digest and forbids re-running acquisition, and renaming a census row
moves its `identity_key`, slug and route — which means a new package digest and a re-registration.
That is a registration order's work, not this one's. The remedy is small and bounded: prefer the
tier-1 first-party name over the DBPR licensee name when both exist, rename the one row, re-seal,
re-register. The founder should decide whether West Palm Beach deploys with this page as it
stands or waits for that repair.

---

## FINAL ANSWERS

1. **CURRENT LIVE DEPLOYMENT** = `6ab1a035c7ef3b14a23a4ec6`
2. **CURRENT LIVE MARKETS** = **32**
3. **CURRENT LIVE PROFILES** = **2,375**
4. **REGISTERED PACKAGE** = `pkg-west-palm-beach-fl-789c0187e366abe8` (`sha256:789c0187e366abe8…`)
5. **FOUNDER AUTHORIZATION CREATED** = **YES**
6. **FOUNDER AUTHORIZATION ID** = `ptf-auth-west-palm-beach-003-217f87eeba72`
7. **PARTICIPATION STATE** = **`FOUNDER_AUTHORIZED_FOR_LAUNCH`** (32 → 33 authorized; Detroit still withheld)
8. **PARENT LOOKUP** = **PASS** (by deployed bundle `0ec5c655…`)
9. **PARENT ROUTES PRESERVED** = **PASS**
10. **UNCHANGED BUNDLES REUSED** = **32** (registration-lane release-store accounting)
11. **UNCHANGED MARKETS REBUILT** = **0** (same accounting)
12. **PHYSICAL FRAGMENTS RERENDERED** = **33** — the release store in this worktree is empty, so the composer rendered every fragment; this is reported separately and is **not** counted as reuse
13. **WEST PALM BEACH BUNDLES BUILT** = **1**
14. **AUTHORIZED CANDIDATE BUNDLE** = `217f87eeba72c9f94c2eaf3ce82c37af35b261e8f21abb847c0b6337216c5054`
15. **AUTHORIZED CANDIDATE SITEMAP** = `31ac963ff95191fef42713b6c44dcbf5f1aa88dd97bbb1897566f0655e7b6005`
16. **CANDIDATE MARKETS** = **33**
17. **CANDIDATE PROFILES** = **2,424**
18. **CANDIDATE RELEASE-INDEX ROUTES** = **2,701**
19. **CANDIDATE SERVED ROUTES** = **2,767**
20. **WEST PALM BEACH PROFILES** = **49**
21. **WEST PALM BEACH RELEASE-INDEX ROUTES** = **55** (49 + 1 hub + 5 corridors)
22. **WEST PALM BEACH SERVED ROUTES** = **56** (+1 policy-comparison, served but not market-owned)
23. **UNAPPROVED WEST PALM BEACH PROFILES** = **0**
24. **CROSS-MARKET COLLISION SAFETY** = **PASS** (0 duplicate canonical names; `best western` → Tampa only; `comfort inn & suites` → Lexington only; 34/34 contracts verify)
25. **GEOGRAPHY SAFETY** = **PASS** (Broward 0, Miami-Dade 0, Monroe 0, St. Lucie 0, Martin 3 = the approved 33469 Tequesta cases)
26. **ALL RELEASE GATES** = **PASS** (27/27 composed-bundle, all accounting gates, `problems []`)
27. **UNEXPECTED DELTA** = **NONE** (markets [], profiles [], release-index routes [], served routes [])
28. **CANDIDATE DEPLOYABLE** = **YES** (AUTHORIZED, bound to the candidate bytes, unconsumed)
29. **DEPLOYMENT AUTHORIZATION CREATED** = **YES**
30. **DEPLOYMENT AUTHORIZATION ID** = `ptf-auth-west-palm-beach-003-217f87eeba72`
31. **CURRENT LIVE MODIFIED** = **NO**
32. **DEPLOYMENT PERFORMED** = **NO**
33. **WEST PALM BEACH LIVE** = **NO** (every probed route 404)
34. **origin == HEAD** = **YES**
35. **tree clean** = **YES**
36. **READY FOR WEST PALM BEACH PRODUCTION DEPLOYMENT** = **YES** — every mechanical gate passes and the authorization is bound and unconsumed. One non-gate finding is open for the founder: the `Apple Ten Hospitality Management Inc` profile, above.

---

WEST PALM BEACH FOUNDER AUTHORIZATION = PASS
WEST PALM BEACH AUTHORIZED CANDIDATE = PASS
UNAPPROVED WEST PALM BEACH PROFILES = 0
CURRENT LIVE MODIFIED = NO
WEST PALM BEACH DEPLOYED = NO
READY FOR WEST PALM BEACH PRODUCTION DEPLOYMENT = YES
