# PTF-WEST-PALM-BEACH-FL-REGISTRATION-AND-STAGING-002 — FINAL

**Worktree** `C:\Atlas-West-Palm-Beach-FL-Hardened-V1`
**Branch** `worker/ptf-west-palm-beach-fl-market-001`
**Market** `west-palm-beach-fl`
**Source-ready commit registered from** `564c106e` (the commit the order named)
**Registration commit** `f7cb573d` · **seal** `acbab06a` · **isolation fix** `84c9f6e1` · **packet** `873425a7`

**This order stopped where it was told to stop: AUTHORIZATION_READY + a VALIDATED PROJECTED,
NON-DEPLOYABLE CANDIDATE.** West Palm Beach is registered and buildable. It is not authorized,
not deployed and not live. No founder launch authorization and no deployment authorization exist
for it.

---

## PHASE 1 — CURRENT LIVE

Resolved mechanically with the repaired resolver
(`release_index live-source --fetch --verify-host`), never from `origin/main`, which the resolver
itself reports stale. Taken again **after every write this order made** and byte-for-byte the same.

| | |
|---|---|
| CURRENT LIVE SOURCE COMMIT | `e82120cce7e48c62d3c1057a6c82785bed920485` (built_from `0cc2817b`) |
| CURRENT LIVE DEPLOYMENT | `6ab1a035c7ef3b14a23a4ec6` (`ptf-deploy-fort-lauderdale-004-…`) |
| CURRENT LIVE BUNDLE SHA | `0ec5c6557d79eaf77a4065b6700c0a5807e9bfe282408dd4779804b33af3a40f` |
| CURRENT LIVE SITEMAP SHA | `e81961ae76454ce608fcb39624d5147c8779f52b269faab9449138397cb8fa3d` |
| CURRENT LIVE MARKETS | **32** |
| CURRENT LIVE PROFILES | **2,375** |
| CURRENT LIVE RELEASE-INDEX ROUTES | **2,646** |
| CURRENT LIVE SERVED SITEMAP ROUTES | **2,711** |
| HOST VERIFIED | **true** |

The order's expectation and the authoritative resolution agree exactly. The parent had **not**
advanced, so nothing was registered against a stale parent.

---

## PHASE 2 — SOURCE PACKAGE

HEAD contains `564c106e`. The source-ready package digest was **recomputed from committed bytes**
and is identical:

| | |
|---|---|
| Package | `pkg-west-palm-beach-fl-eb802c414bf12396` |
| Digest | `sha256:eb802c414bf12396f96e6ae8ec12585ce137edb6de39243a65d720372fc5d941` |
| Reproducible in-process | **YES** |
| SOURCE READY · COVERAGE READY · ACTIONABLE UNRESOLVED | YES · YES · 0 |
| FAST | 15/15 PASS |

**Nothing was re-acquired.** No census discovery, competitor challenge, Firecrawl call, Google
Places request or brand-browser harvest was re-run. The census *was* re-derived from committed
lane outputs three times, for the naming defects in Phase 3 — that is a deterministic
re-derivation from committed bytes, not an acquisition: **0 provider calls, 0 credits, USD 0.00**.
Firecrawl credits are unchanged at 1,199 and the roster lane's post-fix report is byte-identical.

---

## PHASE 3 — CANONICAL REGISTRATION WRITES

The canonical fresh-market registration transaction was performed in full, in dependency order:

- 14 market-local writers repointed from the shadow zone to the registered zone
- census promoted to `launch_packages/pettripfinder/identity_census/west-palm-beach-fl.json`
- market document promoted to `launch_packages/pettripfinder/markets/west-palm-beach-fl.json`
- registration input at the package root as `west_palm_beach_fl_proposed_authority_001.json` — the
  **role name** the classifier recognises (Orlando lost all fifteen checks to naming it otherwise)
- registered policy package `hotel_policy_facts_west-palm-beach-fl.json`
- authority shard `markets/authority/west-palm-beach-fl/{seed_businesses.csv, hotel_exclusions.json, identity_routing.json, affiliate_destinations.json}` — 49 seed rows, 25 exclusions
- final partition `west_palm_beach_fl_final_partition_001.json` at the package root, contract 0 issues
- deterministic global regeneration: `hotel_exclusions.json`, `seed_businesses.csv`,
  `ptf_global_authority_manifest.json` — 34 markets, 1,171 exclusions, 2,573 seed rows, then
  `--check` → *all generated artifacts match the shards*
- release contract `deploy/netlify/release_contracts/west-palm-beach-fl.json`, derived, **0 disagreements**;
  `release_contracts.verify_all()` clean across **all 34** contracts
- `launch_participation.json` **reissued**, one row added
- `bundle_cache_closure.json`, `tests/pettripfinder/pins/market_state.json`, sealed package, FAST
  receipt and lane reports

**Not written, deliberately:** `identity_resolutions.json`. The source-ready order left four
duplicate-premises halves on holds rather than invent a ruling; the classifier agrees
(`identity_resolutions` PASS — *no identity-resolution ruling in the change set*).

The founder's Phase 3 authorization covered every write above. Nothing crossed into founder launch
authorization, deployment authorization, the live manifest, activation flags or Netlify.

### Four source-level defects found during promotion, each fixed at the source

**1. The policy package declared the wrong market.** `hotel_policy_facts_west-palm-beach-fl.json`
carried `"market": "Fort Lauderdale, Florida"`, and `as_of` was Fort Lauderdale's date. A clone
artifact that survived the source-ready order because the clone substituted the *source-ready*
order name and not the *registration* one, so that run's own correction silently missed its anchor.

**2. `build_global_authority` refused: `duplicate excluded identity 'Best Western'`.** The shared
exclusion registry matches normalised canonical names **across every market**, and Tampa already
holds a bare `Best Western`. Fixed at the source with the name the **brand's own page states** —
*Best Western Intracoastal Inn*, property code 10267, 810 S US Highway 1 Jupiter, read first-party
by the source-ready order — never by superseding Tampa's row.

**3. A second, latent collision: `Comfort Inn & Suites`,** which Lexington also holds. The census
module's own report *claims* bare flags take their name from the brand's route slug; **that
fallback was never implemented.** The observation search only accepts names that *start with* the
flag, and this row's own alias was the shorter "comfort inn lantana". Implemented generally: the
place comes from the brand's own URL and is accepted **only when this market's geography admits
it**, so a slug naming Orlando is refused rather than mis-naming a property. Unit-checked:
`lantana → Lantana`, `boca-raton → Boca Raton`, `orlando → ""`, unknown → `""`.
Result: **zero duplicate canonical names across all 34 markets.** Neither duplicate pre-existed —
both pairs involved west-palm-beach-fl alone, so no other market's exclusion was superseded.

**4. One unresolvable write target cost the first `packet` its narrowing** — see Phase 5.

A consequence worth recording: renaming a census row changes its `identity_key`, which invalidated
the browser lane's stored bindings and briefly moved one row from `CLEAN_VERIFIED_NO_PETS` to
`ROUTING_HOLD`. Re-running the browser lane re-bound it and restored PF 49 / NP 25.

---

## PHASE 4 — REGISTRATION TIMER

Reported separately and honestly. Nothing is hidden and nothing is mislabelled.

**A. TOTAL PROMOTION / REGISTRATION WALL CLOCK = 42 m 45 s** (18:36:03Z → 19:18:48Z)

| Segment | Duration | What it was |
|---|---|---|
| 18:36:03Z → 19:09:32Z | 33 m 29 s | Fresh-market promotion: repointing 14 writers, moving the census and market document, three census re-derivations for the two naming defects, the authority shard, the global regeneration and the release contract. **This is one-time work for a market that has never been registered; it is not lane time.** |
| 19:09:32Z → 19:18:48Z | 9 m 16 s | The generic lane, plus the refused first `packet`, the one-line isolation fix and two commits |

**B. GENERIC REPAIRED REGISTRATION-LANE TIME = 2 m 55 s**

| Step | Seconds |
|---|---|
| `registration_release_lane register` | ~3 |
| `registration_release_lane seal --work-order` | **112.7** (FAST 83.3 + pin + candidate) |
| `registration_release_lane packet` (the run that reached AUTHORIZATION_READY) | **59.0** (live resolution 2.4 + proof 55.0) |

- REGISTRATION ≤ 5 m TARGET = **MET** (2 m 55 s)
- REGISTRATION ≤ 10 m HARD BOUND = **MET**
- Counting the **refused** first `packet` as well (68.2 s: 37.1 live + 31.2 proof), the lane total
  is **4 m 03 s** — still inside the 5-minute target. Both figures are stated; neither is hidden.

There was **no human permission wait**: the order's Phase 3 authorized the canonical registration
writes in advance, so the 80-minute approval block Fort Lauderdale reported does not recur here.

---

## PHASE 5 — AUTOMATIC CLASSIFICATION

The repaired classifier ran automatically inside `packet`.

| | |
|---|---|
| Classification source | **AUTOMATIC** |
| Proof version | `ptf-registration-data-only/2.0` |
| CHANGE CLASS | **`COMPOSITE_FRESH_MARKET_DATA_ONLY`** |
| ELIGIBLE | **YES** |
| Checks | **15 PASS / 0 FAIL / 0 UNKNOWN** |
| FULL_REGRESSION_REQUIRED | **NO** |
| REMOTE BROAD JOBS REQUIRED | **0** |
| BROAD REGRESSION RUNS | **0** |
| UNCHANGED MARKETS REBUILT | **0** |
| FAST | **15/15 PASS** |
| Registration base | `efd22bc7` — *newest first-parent ancestor of HEAD that contains the live lineage commit, names no path of the registering market, and carries the live commit's live-truth files* |
| Reaches | `AUTHORIZATION_READY` · `authorizes_deployment = false` |

### The first `packet` was REFUSED, and the refusal was correct

Run 1 returned `NOT_AUTHORIZATION_READY`, `FULL_REGRESSION_REQUIRED = YES`, all fifteen checks
FAIL. The cause was a **single path**, named precisely:

```
change_set FAIL — scripts/pettripfinder/west_palm_beach_fl_destination_roster_001.py
is not market-local: writes failed (line 133 open:w: write target cannot be resolved statically)
```

Everything else was already right: the five-bucket partition summed exactly
(94 = 29 market-local + 13 registration + 51 derived + **1 shared** + 0 unknown), UNKNOWN was 0,
and the candidate class was already `COMPOSITE_FRESH_MARKET_DATA_ONLY`. The one SHARED path was
that roster module.

The market-local isolation prover resolves every **write** target statically. The module took its
cache path from `_cache_path(url)`, so the target arrived from a function call — *a bare root plus
a dynamic tail*, which the prover refuses. `west_palm_beach_fl_brand_inventory_001.persist` already
joins its path inline from the module's own `DOCS` constant, which is exactly why that module
classified MARKET_LOCAL and this one did not. The write side now does the same; reads are not
proven and still use the helper. The roster report is **byte-identical** after the change and cost
**0 credits** — it reads its committed cache.

Run 2 partitioned cleanly and narrowed. **This is the Raleigh lesson holding**: one unresolvable
write in one market-local helper is enough to collapse a 96-path fresh-market change set into a
broad classification. Per the order, no broad suite was launched at any point.

---

## PHASE 6 — REGISTRATION CHANGE ACCOUNTING

From the classifier's own five-bucket partition (final run):

| Bucket | Paths |
|---|---:|
| MARKET-LOCAL ACQUISITION | **30** |
| REGISTRATION DATA | **13** |
| PERMITTED DERIVED REGISTRATION OUTPUT | **53** |
| **SHARED FACTORY IMPLEMENTATION** | **0** |
| **UNKNOWN** | **0** |
| TOTAL | **96** (`sum_equals_total: true`) |

Requirements met: SHARED = 0, UNKNOWN = 0. The derived bucket is the canonical registration and
global output the order explicitly permits: the three regenerated globals, the sealed package, the
FAST receipt, the market reports and the build closure.

Current served production is unchanged — re-verified in Phase 16.

---

## PHASE 7 — CROSS-MARKET SAFETY

The registration preserved the geography exactly. Counted by each licence's **own** county:

| County | Hotel-rank licences | **Admitted** | Owner |
|---|---:|---:|---|
| **Palm Beach (home)** | 197 in admitted codes | — | this market |
| Broward | 609 | **0** | **LIVE** `fort-lauderdale-fl` |
| Miami-Dade | 737 | **0** | **LIVE** `miami-fl` |
| Martin | 29 | **3** | future `treasure-coast-fl` |
| Monroe | 319 | **0** | future `florida-keys-fl` |
| St. Lucie | 58 | **0** | future `treasure-coast-fl` |

`live_market_inventory_admitted = 0` · `no_south_florida_sprawl = true`. The three Martin rows are
the shared Tequesta postal code 33469, admitted whole by the explicit border rule and named
individually — exactly the state the source-ready order proved.

No Miami, Fort Lauderdale, Broward or Miami-Dade profile or route entered West Palm Beach.

**Cross-market exclusion safety:** `release_contracts.verify_all()` — **34 contracts verified, 0
disagreements**. Duplicate canonical names across all markets: **none**. The two bare-chain-flag
collisions this registration exposed were fixed in this market's own source, and no other market's
exclusion was touched or superseded.

---

## PHASE 8 — PROJECTED PARTICIPATION

`launch_participation.json` was **reissued** (never hand-edited) with one added row:

```
west-palm-beach-fl : SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH
```

34 rows total; the **authorized set is unchanged at 32**; Detroit remains withheld. No founder
authorization was written, no founder-authorized state persisted, no deployment authorization
created. The candidate is **PROJECTED** and **NON-DEPLOYABLE**.

---

## PHASE 9 — PARENT RELEASE LOOKUP

| | |
|---|---|
| PARENT LOOKUP | **PASS** |
| PARENT FOUND BY DEPLOYED BUNDLE | **PASS** — `live_deploy_id 6ab1a035c7ef3b14a23a4ec6`, `bundle_sha256 0ec5c655…` |
| PARENT ROUTES PRESERVED | **PASS** — 0 unexpected route changes |
| Parent release digest | `sha256:0ec19aa98462858d02a0770eb29e2cc124cfd7f7b82084ee34b2cc022062f94c` |

The parent was resolved by the **deployed bundle**, not by a registration-sensitive release-manifest
digest — the repaired semantics the release-store memory requires.

---

## PHASE 10 — REUSE STAGING

| | |
|---|---|
| UNCHANGED BUNDLES REUSED | **32** (every live market) |
| UNCHANGED MARKETS REBUILT | **0** |
| WEST PALM BEACH BUNDLES BUILT | **1** |
| CANDIDATE REPRODUCIBLE | **YES** — `candidate_index_digest` == `recomposed_index_digest` (`968e379a…`) |

No physical re-rendering of another market's fragments occurred, and none is being reported as
reuse: the lane names all 32 unchanged markets explicitly and rebuilt none of them. The one market
bundle built is West Palm Beach's own (`97f11441…`).

---

## PHASE 11 — PROJECTED PROFILE ACCOUNTING

| | |
|---|---|
| WEST PALM BEACH APPROVED PROFILES | **49** |
| Verified-no-pets (canonical exclusions, NOT profiles) | **25** |
| Unresolved / held identities published | **0** |
| **UNAPPROVED WEST PALM BEACH PROFILES IN CANDIDATE** | **0** |
| Parent profiles | 2,375 |
| **PROJECTED TOTAL PROFILES** | **2,424** (derived: 2,375 + 49) |

Only the sealed pet-friendly cohort became projected hotel profiles. The 25 verified-no-pets rows
are exclusion records in the authority shard, not profiles. The 116 unresolved and held rows
publish nothing.

---

## PHASE 12 — TWO ROUTE ACCOUNTING SYSTEMS, KEPT SEPARATE

**They are not equal, and the difference was derived, not assumed.**

West Palm Beach's sealed package declares **55** routes. Composition verified directly from
`intended_delta.add_routes`:

| Kind | Count |
|---|---:|
| hotel profile routes | 49 |
| market hub | 1 |
| publishing corridors | 5 |
| **policy-comparison page** | **0 — not a declared release-index route** |
| **A. WEST PALM BEACH RELEASE-INDEX ROUTES** | **55** |

The market's `/policy-comparison/` page **is** built and served (the FAST build declares it) but is
**not** a market-owned release-index route. That is the same behaviour the current production
contract already shows for Fort Lauderdale, whose deployment record states it explicitly: *2,711
served − 2,646 release-index = 65: the 64-route release-global surface no market owns, plus Fort
Lauderdale's own policy-comparison page.*

| | |
|---|---:|
| **B. WEST PALM BEACH SERVED SITEMAP ROUTES** | **56** (the 55 above **+1** comparison page) |
| PROJECTED TOTAL MARKETS | **33** |
| PROJECTED TOTAL PROFILES | **2,424** |
| PROJECTED TOTAL RELEASE-INDEX ROUTES | **2,701** (2,646 + 55) — confirmed by the built candidate |
| PROJECTED TOTAL SERVED SITEMAP ROUTES | **2,767** (2,711 + 56) |

2,701 is the figure the lane measured on the built candidate. 2,767 is derived from the unchanged
contract's own rule; it is a projection and is labelled as one — the deployment order measures the
served sitemap against the real artifact.

---

## PHASE 13 — CORRIDOR ACCOUNTING

The five publishing corridors, taken mechanically from the sealed package's declared routes (not
from the earlier narrative):

| Corridor | Class | Census | PF | NP | Rate |
|---|---|---:|---:|---:|---:|
| downtown-west-palm-beach | CORE | 18 | 7 | 2 | 50.0 % |
| palm-beach-gardens | CORE | 10 | 5 | 1 | 60.0 % |
| palm-beach-international-airport | CORE | 18 | 7 | 2 | 50.0 % |
| delray-beach | CORE | 15 | 7 | 0 | 46.7 % |
| boca-raton | CORE | 25 | 8 | 4 | 48.0 % |

The other **10** corridors remain suppressed, each below the committed threshold of 5 verified
pet-friendly hotels — including Palm Beach / Worth Avenue (0 PF) and Lake Worth Beach (2 PF over 25
census rows, the market's weakest corridor). **FORCED CORRIDORS = 0.** No thin page was created.

---

## PHASE 14 — DELTA SAFETY

| | |
|---|---|
| UNEXPECTED MARKET DELTA | **[]** (0) |
| UNEXPECTED PROFILE DELTA | **[]** (0) |
| UNEXPECTED RELEASE-INDEX ROUTE DELTA | **[]** (0) |
| UNEXPECTED SERVED-ROUTE DELTA | **[]** (0) |
| UNEXPECTED FINDINGS | **[]** (`finding_counts: {}`, `release_diff_passed: true`) |

All 32 live markets preserved, all parent profiles preserved, all parent routes preserved. The
`expected_release` gate compares EXPECTED (live parent + sealed package) against ACTUAL (committed
authority) **as complete sets** — 33 / 2,424 / 2,701 on both sides, `complete_sets_equal: true`.
The two index digests differ because they are computed over differently structured inputs; the gate
compares sets, never digests, which is the standing rule for route accounting.

---

## PHASE 15 — STAGING GATES

All fifteen registration checks PASS:

| Gate | |
|---|---|
| `change_set` · `market_local_zone` · `discovery_config` | PASS · PASS · PASS |
| `registration_input` · `identity_resolutions` · `participation` | PASS · PASS · PASS |
| `release_contract` · `build_closure` · `derived_globals` | PASS · PASS · PASS |
| `sealed_package` · `fast_receipt` · `expected_release` | PASS · PASS · PASS |
| `identity_routes` · `market_state_pin` · `release_integrity` | PASS · PASS · PASS |

`release_integrity`: *no deployment authorization, record, manifest, activation flag, production
gate or deployment pin moved; the live parent is verified and the authorized set is unchanged* —
`protected_paths_touched: []`.

**DEPLOYMENT REFUSAL = EXPECTED / PASS.** `authorizes_deployment = false`,
`founder_status = AWAITING_FOUNDER_AUTHORIZATION`. The candidate is not deployable.

The digests this readiness binds:

| | |
|---|---|
| Sealed package | `pkg-west-palm-beach-fl-789c0187e366abe8` |
| Package digest | `sha256:789c0187e366abe8c199feb799ec691241d83ae81c3178e9cd4de41dde2c7bf8` |
| FAST receipt digest | `sha256:6cccadf2a6ddd41a0469feb0b92866499b668fe23b02b72a3bd7694490a2545d` |
| Changed market bundle | `97f114417d9f98b3c3721eeeef72fa9903ede87ee3c3602a93bdbec5f3e8dc8a` |
| Parent live deploy | `6ab1a035c7ef3b14a23a4ec6` |

---

## PHASE 16 — CURRENT LIVE SAFETY (re-verified at report time)

| | |
|---|---|
| CURRENT LIVE DEPLOYMENT | `6ab1a035c7ef3b14a23a4ec6` — **unchanged** |
| CURRENT LIVE BUNDLE | `0ec5c655…` — **unchanged** |
| CURRENT LIVE SITEMAP | `e81961ae…` — **unchanged** |
| 32 markets / 2,375 profiles / 2,711 served | **unchanged** · HOST VERIFIED true |

Probed against production:

| Route | Status |
|---|---|
| `/pet-friendly-hotels/west-palm-beach-fl/` | **404** |
| `/pet-friendly-hotels/west-palm-beach-fl/boca-raton/` | **404** |
| `/pet-friendly-hotels/west-palm-beach-fl/delray-beach/` | **404** |
| `/pet-friendly-hotels/west-palm-beach-fl/aloft-delray-beach/` | **404** |
| `/pet-friendly-hotels/west-palm-beach-fl/policy-comparison/` | **404** |
| `/pet-friendly-hotels/fort-lauderdale-fl/` | **200** — Fort Lauderdale still live |
| `/pet-friendly-hotels/miami-fl/` | **200** — Miami still live |
| `/pet-friendly-hotels/detroit-ann-arbor-mi/` | **404** — Detroit still withheld |

**WEST PALM BEACH HUB LIVE = NO.**

---

## PHASE 17 — NO BROAD OR HEAVY TEST DETOUR

No broad regression was run. `test_factory_throughput_001.py`, whole-site demo-media suites and
unrelated heavy assembly suites were not run. The only test-surface artifacts touched are the
registration's own market-state pin and build closure, both written by the generic lane.
**BROAD REGRESSION RUNS = 0 · REMOTE BROAD JOBS = 0.**

---

## FINAL ANSWERS

1. **CURRENT LIVE SOURCE COMMIT** = `e82120cce7e48c62d3c1057a6c82785bed920485`
2. **CURRENT LIVE DEPLOYMENT** = `6ab1a035c7ef3b14a23a4ec6`
3. **CURRENT LIVE MARKETS** = **32**
4. **CURRENT LIVE PROFILES** = **2,375**
5. **CURRENT LIVE RELEASE-INDEX ROUTES** = **2,646**
6. **CURRENT LIVE SERVED SITEMAP ROUTES** = **2,711**
7. **WEST PALM BEACH PACKAGE** = `pkg-west-palm-beach-fl-789c0187e366abe8` (registered; the source-ready package `eb802c414bf12396` was re-verified and is the input)
8. **PACKAGE DIGEST** = `sha256:789c0187e366abe8c199feb799ec691241d83ae81c3178e9cd4de41dde2c7bf8`
9. **REGISTRATION CLASS** = **`COMPOSITE_FRESH_MARKET_DATA_ONLY`**
10. **ELIGIBLE** = **YES**
11. **FULL_REGRESSION_REQUIRED** = **NO**
12. **TOTAL PROMOTION / REGISTRATION WALL CLOCK** = **42 m 45 s** (33 m 29 s fresh-market promotion + 9 m 16 s lane window; no human permission wait)
13. **GENERIC REGISTRATION-LANE TIME** = **2 m 55 s** (register ~3 s + seal 112.7 s + packet 59.0 s); **4 m 03 s** if the refused first packet is counted
14. **REGISTRATION ≤ 5 M TARGET** = **MET**
15. **REGISTRATION ≤ 10 M HARD** = **MET**
16. **BROAD REGRESSION RUNS** = **0**
17. **MARKET-LOCAL PATHS** = **30**
18. **REGISTRATION PATHS** = **13**
19. **DERIVED GLOBAL PATHS** = **53**
20. **SHARED FACTORY PATHS** = **0**
21. **UNKNOWN PATHS** = **0**
22. **PARENT LOOKUP** = **PASS** (found by deployed bundle)
23. **PARENT ROUTES PRESERVED** = **PASS**
24. **UNCHANGED BUNDLES REUSED** = **32**
25. **UNCHANGED MARKETS REBUILT** = **0**
26. **WEST PALM BEACH BUNDLES BUILT** = **1**
27. **WEST PALM BEACH PROJECTED PROFILES** = **49**
28. **WEST PALM BEACH RELEASE-INDEX ROUTES** = **55** (49 profiles + 1 hub + 5 corridors)
29. **WEST PALM BEACH SERVED SITEMAP ROUTES** = **56** (the 55 above **+1** policy-comparison page, served but not market-owned)
30. **PUBLISHING CORRIDORS** = **5** — downtown-west-palm-beach, palm-beach-gardens, palm-beach-international-airport, delray-beach, boca-raton (of 15; 10 suppressed; FORCED CORRIDORS = 0)
31. **PROJECTED TOTAL MARKETS** = **33**
32. **PROJECTED TOTAL PROFILES** = **2,424**
33. **PROJECTED RELEASE-INDEX ROUTES** = **2,701**
34. **PROJECTED SERVED SITEMAP ROUTES** = **2,767** (projection; the deployment order measures the artifact)
35. **UNAPPROVED WEST PALM BEACH PROFILES** = **0**
36. **CROSS-MARKET COLLISION SAFETY** = **PASS** — 34/34 contracts verify, 0 disagreements, 0 duplicate canonical names, 2 bare-flag collisions fixed in this market's own source
37. **ALL STAGING GATES** = **15 PASS / 0 FAIL / 0 UNKNOWN**
38. **UNEXPECTED DELTA** = **NONE** (markets [], profiles [], routes [], findings [])
39. **CANDIDATE MODE** = **PROJECTED / NON-DEPLOYABLE**
40. **DEPLOYMENT REFUSAL** = **EXPECTED / PASS** (`authorizes_deployment = false`)
41. **CURRENT LIVE MODIFIED** = **NO**
42. **WEST PALM BEACH DEPLOYED** = **NO**
43. **origin == HEAD** = **YES**
44. **tree clean** = **YES**
45. **READY FOR FOUNDER LAUNCH AUTHORIZATION** = **YES**

---

WEST PALM BEACH REGISTRATION = PASS
WEST PALM BEACH STAGING = PASS
FULL_REGRESSION_REQUIRED = NO
BROAD REGRESSION RUNS = 0
UNCHANGED MARKETS REBUILT = 0
WEST PALM BEACH DEPLOYED = NO
CURRENT LIVE MODIFIED = NO
READY FOR FOUNDER LAUNCH AUTHORIZATION = YES
