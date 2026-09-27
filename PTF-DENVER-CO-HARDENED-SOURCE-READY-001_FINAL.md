# PTF-DENVER-CO-HARDENED-SOURCE-READY-001 — FINAL

**Denver / Boulder / Front Range, Colorado** (`denver-co`) is the first Colorado market. It was built from zero to a
market-local SHADOW package on the San Diego-live lineage, and that package was reproduced independently.
Worktree `C:\Atlas-Denver-CO-Hardened-V1`, branch `worker/ptf-denver-co-market-001`. Denver is not registered, not
authorized and not deployed.

| | |
|---|---|
| Shadow package | `pkg-denver-co-8de3a042157dc335` (`sha256:8de3a042157dc335213830e06c7a025b87a466874b867df5930e8aa84239febb`), SHADOW_UNTIL_REGISTERED |
| Sealed from | `becdfdcf` (every staged input committed), sealed twice with the same digest |
| FAST | **15/15 PASS**, 0 UNKNOWN, 0 FAILED; receipt `sha256:d79b48c9…8e1`, currently ELIGIBLE (`eligible_receipts` returns it) |
| Rule J (non-empty) | PASS: 1,729 files, 1,713 HTML, output present, 0 output defects; bundle `03159c8d…2df5`; 16 corridor pages, 0 warnings, 0 broken internal links |
| Rule K (non-vacuous) | PASS: BYTE_IDENTICAL, 4 cold builds, 0 reuse hits |
| First-party gate | 335/335 eligible |
| Independent reproduction | Detached worktree, separate process, separate work dir. Same package id, digest and bundle; 15/15. **FILES COMPARED 8, DIFFERING FILES 0** |
| Census / published | 441 identities: **289 pet-friendly + 46 verified no-pets** = 335 resolved (75.96 %); 106 unresolved |
| Actionability | **ACTIONABLE UNRESOLVED 0**: 38 router-exhausted, 52 need new spend, 16 need a founder decision |
| Coverage | **FOUNDER DECISION** (mechanical; see §9) |

## 1. Lineage and current live (Phases 1–2)

The order started at 2026-09-27T15:06:09Z on `1724e822` (SAN DIEGO IS LIVE); the San Diego live source `f01587ba` is an
ancestor. CURRENT VERIFIED LIVE is San Diego:

- deploy `6ab859787d349f8397e1450a`
- 35 markets / 2,666 profiles / 2,969 release-index routes / 3,037 served routes

The shadow package's `parent_live_state` names that release. Once any later market goes live, FAST rule N will fail
this package BY DESIGN. At that point the registration order re-seals the same committed inputs as a new package id.

Commits on this branch:

1. `c03541ab`: staged inputs, including the operator-authorized `registration_staging --write`.
2. First seal `pkg-denver-co-6692ee56`: FAST rule J FAIL (see §6.2).
3. `becdfdcf`: the fix.
4. `b3abf249`: the shadow package.
5. This report.

## 2. Geography (Phases 3–6)

**Corridors.** 20 corridors over 106 ZIPs. Membership is decided by the property's OWN postal code
(`classify_postal`), never by name, and a ZIP is never split.

- **10 CORE:** Downtown/LoDo/Union Station, Capitol Hill/Uptown, Highlands/RiNo/North Denver, Cherry Creek/Glendale,
  Central Park/Lowry/I-70, South Denver/University, Denver Tech Center, DEN Airport, Aurora, Lakewood/Wheat Ridge.
- **7 CORRIDOR:** Golden/Red Rocks, Arvada, Westminster/Broomfield, Thornton/Northglenn/North I-25,
  Littleton/Englewood, Boulder, Louisville/Superior/Lafayette.
- **3 FRINGE:** Longmont/Erie, Parker/Southeast, Brighton/Northeast.

**Boulder ruling.** Boulder is a STRONG CORRIDOR in its own corridor, not CORE and not a separate market today. It is
named the first promotion candidate (`boulder-co`).

**Mountain access and demand.** The ski resorts and I-70 mountain towns are refused as markets. They are recorded as
the demand that Golden/Red Rocks and the west corridors serve. DEN airport demand has its own corridor (80249 / 80239
/ 80019). Condo-hotels and extended-stay operators are admitted only as public hotel operations; vacation rentals and
timeshares are excluded.

**Refused.**

- FUTURE standalone markets: `colorado-springs-co`, `fort-collins-loveland-co`, `estes-park-co`,
  `colorado-ski-resorts`.
- Also refused: Castle Rock, Greeley, Pueblo, the plains, Wyoming.
- Refused by municipality inside ZIP 80504: Firestone, Frederick and Dacono.

Uncorridored admitted rows: **0**.

| corridor | class | census | PF | NP | unresolved | page publishes |
|---|---|---:|---:|---:|---:|---|
| downtown-lodo-union-station | CORE | 47 | 37 | 1 | 9 | yes |
| capitol-hill-uptown | CORE | 8 | 3 | 1 | 4 | no |
| highlands-rino-north-denver | CORE | 16 | 7 | 3 | 6 | yes |
| cherry-creek-glendale | CORE | 15 | 11 | 2 | 2 | yes |
| central-park-lowry-i70 | CORE | 20 | 6 | 2 | 12 | yes |
| south-denver-university | CORE | 1 | 1 | 0 | 0 | no |
| denver-tech-center | CORE | 55 | 41 | 4 | 10 | yes |
| den-airport | CORE | 47 | 33 | 8 | 6 | yes |
| aurora | CORE | 47 | 29 | 1 | 17 | yes |
| lakewood-wheat-ridge | CORE | 30 | 17 | 1 | 12 | yes |
| golden-red-rocks | CORRIDOR | 17 | 11 | 6 | 0 | yes |
| arvada | CORRIDOR | 3 | 3 | 0 | 0 | no |
| westminster-broomfield | CORRIDOR | 38 | 30 | 5 | 3 | yes |
| thornton-northglenn-north-i25 | CORRIDOR | 11 | 7 | 0 | 4 | yes |
| littleton-englewood | CORRIDOR | 19 | 12 | 4 | 3 | yes |
| boulder | CORRIDOR | 27 | 17 | 0 | 10 | yes |
| louisville-superior-lafayette | CORRIDOR | 8 | 6 | 1 | 1 | yes |
| longmont-erie | FRINGE | 19 | 10 | 3 | 6 | yes |
| parker-southeast | FRINGE | 5 | 5 | 0 | 0 | yes |
| brighton-northeast | FRINGE | 8 | 3 | 4 | 1 | no |

16 corridor pages publish. Each built and linked cleanly in FAST J.

### Boundary audit (Phase 23)

| refused place | discovered | admitted |
|---|---:|---:|
| Colorado Springs (808/809) | 310 | **0** |
| Castle Rock | 6 | **0** |
| Fort Collins / Loveland / Windsor | 62 | **0** |
| Greeley | 19 | **0** |
| Estes Park | 35 | **0** |
| Mountain resorts (Summit, Vail, Aspen, Winter Park, Steamboat) | 136 | **0** |
| I-70 foothills + refused towns (Evergreen, Idaho Springs, Black Hawk, Firestone…) | 31 | **0** |
| Pueblo / south | 9 | **0** |
| Wyoming | 0 | 0 |

Rows admitted from a refused postal code: **0**.

## 3. Owned data, census lanes and exclusions (Phases 7–13)

**Owned data first.**

- 0 owned Denver identities, because this is the first Colorado market.
- 104 owned routes.
- 7,358 live identity names loaded for the cross-market collision pass.
- 1,075 prior Firecrawl calls, of which 0 were Denver pages.

**Census lanes: 3,183 raw observations.**

| lane | observations | note |
|---|---:|---|
| OSM | 1,233 | Geofabrik Colorado extract (Overpass returned 406, no answer, and a stale answer), 1,476 elements |
| Brand inventories | 403 | Marriott owned 102, Hilton city pages 89, sitemaps 212 |
| Bureaux | 472 | Visit Denver 321 through the Simpleview API, Boulder 38, Longmont 24, Aurora 90, Golden 16, Littleton 5 |
| Competitor leads | 683 | |
| Property pages | 392 | |

There is no Colorado lodging licence register, so that lane is recorded as absent.

**Graph and admission.** The graph has 1,776 nodes, of which **441 are admitted**.

**Exclusions.**

| class | count |
|---|---:|
| Vacation rental | 90 |
| Timeshare | 3 |
| Resort residence | 1 |
| Non-hotel | 155 |
| Outside | 613 |
| Name-only residue | 339 |
| Identity-review residue | 133 |
| Rebrand successor | 1 |

**Cross-market collisions.** 8 rows are held because their name collides with a live market's identity. Published
collisions: **0** (checked against all 7,358 live names).

## 4. Acquisition (Phases 14–16)

* **Static plain client.** 243 targets: VALID 18, ACCESS_DENIED 146.
* **Wyndham property service.** 61 routes selected, 36 read, 25 retired.
* **Firecrawl** (existing credits, capped on attempts, floor 400):
  * route discovery: 17 Choice/IHG city pages → 136 routes
  * brand pages: 74 attempted / 65 answered / 60 with their own address
  * routed pass: 58 attempts / 21 publication-grade
  * follow-up pass: 2 / 2
  * **133 credits in total (997 → 864). USD 0.**
* **Places.** Not used. `websiteUri` is an Enterprise-SKU field and the month's free allowance is consumed, so using
  it would be new spend. It is not authorized; the allowance renews 2026-10-01.
* **Attended browser** (claude-in-chrome; navigate plus accessibility read only; no JS exfiltration, no relay, no
  bypass, no CAPTCHA solved): **289 attempts, 268 reads, 0 challenge denials.**

| family | attempts | reads | other outcomes |
|---|---:|---:|---|
| Marriott | 102 | 102 | 0 Akamai denials |
| Hilton | 80 | 77 | 1 persistent error page, 1 404, 1 retired; Akamai wall about every 39 reads, 60–75 min rests |
| Choice | 39 | 39 | the interstitial clears by itself in about 18 s |
| Hyatt | 20 | 17 | 1 source-silent, 1 chip only, 1 retired |
| ESA | 16 | 15 | the DataDome wall did not recur |
| Best Western | 8 | 5 | routes that land on brand search |
| Sonesta 4, Drury 2, Omni 1, Red Roof 1, Four Seasons 1 | 9 | 9 | |
| Independents | 12 | 4 | |
| Motel 6 | 2 | 0 | legacy routes redirect to the brand home page |
| IHG | 1 | 0 | bounded at one attempt (amenity chip only) |

**Marriott closure.** 102/102 in-market routes were read. MARRIOTT ACTIONABLE REMAINING = **0** (100 census rows:
76 PF, 22 NP, and 2 held as the dual-brand building at 455 Zang St).

## 5. Policy and evidence rules (Phases 16–18)

**Inference rules.**

- Acceptance is never taken from a fee, a weight, a count or an amenity chip.
- Refusal is never taken from silence.
- Denver's outdoor reputation is never read as a policy.
- A competitor claim is never used as authority.

**Fees.** **54 fees publish, 115 are withheld, and 0 misleading single fees are published:**

- 80 tiered or multi-amount fees are withheld (for example Hilton's "$75 (1–4n), $125 (5+n)").
- 35 single fees are withheld as unsafe (§6.3).
- In every withheld case, the acceptance, weight, count and species still publish.

**Other rules.**

- Conditional weights are withheld.
- The Gaylord Rockies area restriction ("not allowed in pool area…") is kept beside the quote. It restricts where a
  pet may go, and is not a refusal.
- Every published quote passes the shared first-party reader (FAST rule C; gate 335/335).
- Each row has one disposition, and every hold carries its reason.

## 6. Defects found and fixed in this market's own modules

1. **A route-built name merged four hotels into one.**
   - IHG writes every Denver Holiday Inn Express under `/holidayinnexpress/.../denver/<code>/`. The census built the
     name "Holiday Inn Express Denver" for four codes and used it as a merge alias. That joined dende (1715 Tremont
     Pl, downtown) with dentr (6910 Tower Rd, airport), producing an identity with the downtown name and the airport
     address. The same happened to Staybridge Suites (denca / densb).
   - Fix: IHG and Choice names built from a route now join by brand code and route only. A name alias may never join
     two codes of one brand.
   - Result: 441 identities, 0 with two codes. Opening the Greenwood Village DTC pair cost 2 Firecrawl reads; the
     pair is a dual-brand building.
2. **Site title collision (FAST J FAIL on the first seal, `pkg-denver-co-6692ee56`).**
   - The shared SEO engine cuts a profile title at 60 characters. "Extended Stay America Select Suites Denver - Tech
     Center South" and "… - Greenwood Village" are both the brand's own names and share their first 60 characters.
   - Both are held for a founder naming decision rather than inventing a shorter name.
3. **A single fee can mislead.**
   - The reader defaulted an unstated basis to per stay. The Crawford's quote is cut off at "$50 per n…" and was
     staged as $50 per stay.
   - Hilton's label "Non-refundable fee: $X" states no basis; the Curtis shows that the same label can be a nightly
     fee.
   - Now a fee publishes only when the quote itself states its basis and there is no stay-length condition, range,
     second basis or second amount. 35 fees are withheld on this rule: basis not stated 26, stay-length condition 6,
     two bases 2, amount range 1.
4. **Evidence precedence.** A static read of a vanity domain or bare label overwrote the attended-browser read of the
   brand's own page (Cambria RiNo, Sonesta Denver Downtown). Every read of an identity is now kept, and the shared
   reader chooses among them.
5. **Encoding.** Mojibake in browser reads ("PeÃ±a") came from a recorder reading stdin in the Windows code page. The
   file was repaired and the recorder hardened, which cleared a duplicate census code.
6. **Competitor containment matching.** One-word keys ("Boulder Marriott" → "boulder") and flag-only keys ("holiday
   express ihg") matched every rental and every property of a flag. Containment now needs a distinctive key, and
   rental-shaped titles are triaged first.

## 7. Competitor challenge (BringFido: audit lane only, never policy)

27 Colorado cities: 975 raw / 683 unique.

| class | count |
|---|---:|
| Exact | 229 |
| Alias | 19 |
| Duplicate | 3 |
| Vacation rental | 304 |
| Review | 99 |
| Outside | 13 |
| Non-hotel | 5 |
| Condo residence | 1 |
| **True missing** | **10** |

The 10 true-missing leads are Motel 6 ×4 (Downtown, Brighton, Aurora Medical Center, Thornton), Garner Hotel DEN
Airport Area, Budget Inn Denver Downtown, City Inn, Tyrolean Lodge, Lookout Mountain Lodge and La Quinta Northglenn.
BringFido publishes no street, no free authorized lane states one, and Places verification would be new spend. Each
stays a named gap and none is published.

There is no material identity gap: 251 of 683 leads match the census. There is also no material unexplained policy
gap: 27 matched rows are unresolved, and each carries its classified reason.

## 8. Actionability (Phase 21, per row)

| disposition | total | actionable | exhausted | new spend | founder |
|---|---:|---:|---:|---:|---:|
| ROUTING_HOLD | 55 | 0 | 3 | 52 | 0 |
| SOURCE_SILENT | 18 | 0 | 18 | 0 | 0 |
| EVIDENCE_HOLD | 9 | 0 | 9 | 0 | 0 |
| IDENTITY_MISMATCH_HOLD | 19 | 0 | 3 | 0 | 16 |
| ACCESS_BLOCKED | 5 | 0 | 5 | 0 | 0 |
| **total** | **106** | **0** | **38** | **52** | **16** |

* **52 need new spend.** These are mostly independents with no website in any authorized lane. The only lane that
  finds one is Places `websiteUri` (Enterprise SKU, allowance consumed). They are left exactly as classified.
* **16 need a founder decision.**
  * Seven dual-brand buildings: 455 Zang St, 620 Federal Blvd, 5980 Tower Rd, 550 15th St, 2556 N Oswego, 6951
    Yampa St and 9231 E Arapahoe Rd. Each half is proved by its own brand code and page. Publishing them needs a
    `same_campus_distinct_entity` row in the SHARED `identity_resolutions.json`.
  * The ESA title pair (§6.2).
  * **All are left held.**

## 9. Coverage decision (Phase 26)

All eight coverage conditions are true:

- actionable 0
- no material identity gap and no unexplained policy gap
- lanes exhausted
- Marriott closed
- browser brands bounded
- publication set safe
- package deterministic and FAST clean

The coverage contract still returns **FOUNDER DECISION** mechanically: 68 unresolved rows are reachable only through
new spend (52) or a founder ruling (16).

## 10. Reproduction (Phase 27)

**Setup.**

- Detached worktree `C:/t/den1b-wt` at `b3abf249`.
- A separate OS process; its process record was written before it started
  (`reproduction/independent_reproduction_process.txt`).
- Work dir `C:/t/den1b`; the sealing run used `C:/t/den1a`.
- The staged tree was re-derived with `--stage`.

**Results.**

- Same package id and digest.
- Same bundle `03159c8d…`.
- 15/15 PASS, BYTE_IDENTICAL, ELIGIBLE YES.
- Staged tree: **FILES COMPARED 8, DIFFERING FILES 0**. The package file is identical after LF normalisation.
- Receipt: 1,629 fields compared. The 32 that differ are wall-clock seconds, timestamps, peak working set, the two cache
  `input_key`s (they hash the work-dir path; both runs BUILD_EXECUTED), and therefore the receipt digest.

The worktree and the scratch work dirs were removed afterwards.

## 11. Isolation, boundaries and cleanup (Phases 29–33)

**Changed paths since `1724e822`.** These are Denver-owned only:

- scripts `denver_co_*` and `discovery/config/denver_co.json`
- reports `denver_co_*`
- `markets/staging/denver-co/`
- proposed census and proposed market
- this report

That is **0 shared, 0 cross-market, 0 live and 0 deploy paths.**

**Boundaries kept.**

- Not registered; no founder or deployment authorization; no production candidate; no whole-site build.
- Participation, pin and `identity_resolutions` untouched.
- 0 broad regression runs; USD 0; no new provider.

**Cleanup.** The browser tab is closed. No timers, watchers, servers or child workers from this order remain.

**Machine-readable accounting.**

- `markets/reports/denver_co_source_ready_accounting_001.json`: source, provider, brand, corridor, competitor,
  boundary and fees
- `denver_co_actionability_001.json`: per row
- `denver_co_fee_withholding_001.json`
- `denver_co_shadow_package_001.json`
- `markets/staging/denver-co/reproduction/`

## FINAL ANSWERS

1. START TIMESTAMP = 2026-09-27T15:06:09Z
2. ZERO_TO_SOURCE_READY = 4h12m (FAST-clean shadow package committed `b3abf249` at 19:18:34Z)
3. ZERO_TO_COVERAGE_READY = not reached. Coverage is FOUNDER DECISION, and the mechanical decision was reached with
   the source-ready package (4h12m).
4. CURRENT LIVE DEPLOYMENT = San Diego, deploy 6ab859787d349f8397e1450a (source f01587ba)
5. CURRENT LIVE MARKETS = 35 (2,666 profiles / 2,969 release-index routes / 3,037 served routes)
6. TOTAL DISCOVERED = 3,183 raw observations
7. NORMALIZED IDENTITIES = 1,776 graph nodes
8. QUALIFYING CENSUS = 441
9. PET-FRIENDLY = 289
10. VERIFIED NO-PETS = 46
11. RESOLVED = 335
12. UNRESOLVED = 106
13. RESOLUTION RATE = 75.96 %
14. ACTIONABLE UNRESOLVED = 0
15. HOLDS BY CLASS = IDENTITY 19, ROUTING 55, ACCESS_BLOCKED 5, EVIDENCE 9, SOURCE_SILENT 18, NEGATION 0,
    BROWSER_CAPTURE 0
16. EXCLUSIONS BY CLASS = vacation rental 90, timeshare 3, resort residence 1, non-hotel 155, outside 613, name-only
    residue 339, identity-review residue 133, rebrand successor 1, closed 0
17. PUBLISHING CORRIDORS = 16 of 20
18. BOULDER CLASSIFICATION = STRONG CORRIDOR (its own corridor; first promotion candidate boulder-co); 27 census /
    17 PF
19. COMPETITOR RAW / NORMALIZED / MATCHED / TRUE MISSING = 975 / 683 / 251 / 10
20. MATERIAL IDENTITY GAP = NO
21. MATERIAL POLICY GAP = NO
22. FIRECRAWL ATTEMPTED / SUCCESS = 151 / 105 (17 discovery pages → 136 routes; 65 brand-page answers; 23
    publication-grade routed reads)
23. MARRIOTT CENSUS = 100
24. MARRIOTT BROWSER ATTEMPTED = 102
25. MARRIOTT READ SUCCESS = 102
26. MARRIOTT CHALLENGE DENIED = 0
27. MARRIOTT ACTIONABLE REMAINING = 0
28. OTHER BROWSER ATTEMPTED / SUCCESS = 187 / 166
29. TIERED-FEE POLICIES = 80
30. TIERED FEES WITHHELD = 80 (plus 35 unsafe single fees withheld)
31. MISLEADING SINGLE FEES = 0
32. ACCESS_BLOCKED AFTER ROUTER EXHAUSTION = 5
33. EXISTING PROVIDER CREDITS USED = 133 Firecrawl credits (997 → 864)
34. NEW PAID SPEND = 0
35. PROVIDER COST = USD 0 (existing Firecrawl plan only)
36. RULE J NONEMPTY = PASS (1,729 files / 1,713 HTML / output present)
37. RULE K NONVACUOUS = PASS (BYTE_IDENTICAL, 4 cold builds, 0 reuse)
38. FAST RECEIPT CURRENTLY ELIGIBLE = YES
39. SHADOW PACKAGE CREATED = YES, pkg-denver-co-8de3a042157dc335, SHADOW_UNTIL_REGISTERED
40. PACKAGE REPRODUCIBLE = YES (in-process two-seal, and independent reproduction with DIFFERING FILES 0)
41. PACKAGE DIGEST = sha256:8de3a042157dc335213830e06c7a025b87a466874b867df5930e8aa84239febb
42. FAST = 15/15 PASS, 0 UNKNOWN, 0 FAILED
43. TECHNICAL SOURCE READY = YES
44. COVERAGE READY = FOUNDER DECISION
45. CROSS-MARKET FILE CHANGES = 0
46. FACTORY CODE CHANGED = NO
47. BROAD REGRESSION RUNS = 0
48. FINAL PRODUCTION CANDIDATE CREATED = NO
49. FOUNDER AUTHORIZATION CREATED = NO
50. DENVER DEPLOYED = NO
51. origin == HEAD = YES (verified after the final push)
52. tree clean = YES (verified after the final push)

```
DENVER SOURCE READY = YES
DENVER COVERAGE READY = FOUNDER DECISION
ACTIONABLE UNRESOLVED = 0
RULE J NONEMPTY = PASS
RULE K NONVACUOUS = PASS
FAST = 15/15 PASS, 0 UNKNOWN
FACTORY CODE CHANGED = NO
BROAD REGRESSION RUNS = 0
DENVER FINAL CANDIDATE = NO
DENVER DEPLOYED = NO
WAITING FOR RELEASE QUEUE = YES
```
