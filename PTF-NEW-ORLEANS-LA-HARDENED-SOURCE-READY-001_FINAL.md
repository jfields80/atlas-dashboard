# PTF-NEW-ORLEANS-LA-HARDENED-SOURCE-READY-001 — FINAL

Market `new-orleans-la` — New Orleans / Greater New Orleans, Louisiana.
Branch `worker/ptf-new-orleans-la-market-001`, worktree `C:\Atlas-New-Orleans-LA-Hardened-V1`.
Built from zero on the Kansas City-live lineage. **SHADOW_UNTIL_REGISTERED.** Nothing was registered, authorized or deployed.

## Outcome

| | |
|---|---|
| Shadow package | `pkg-new-orleans-la-939f3cda64d39402` |
| Package digest | `sha256:939f3cda64d394023919387400281d378b49e68ca747ccb7a0bbe4af5abd0126` |
| Sealed from | `b31cd583` (SEALED_AT 2026-10-06T19:47:00Z — after the last capture, seq 262 at 19:42:21Z; the real clock read 19:47:18Z when it was set) |
| FAST | 15/15 PASS, 0 unknown, 0 failed, `FAST_DATA_ONLY_RELEASE_ELIGIBLE = YES` |
| Rule J | non-empty: bundle `047825df…`, 644 files / 628 HTML |
| Rule K | non-vacuous: BYTE_IDENTICAL, 4 cold builds, 0 reuse hits |
| Receipt | `pkg-new-orleans-la-939f3cda64d39402-236fd45013205813`, currently eligible (`eligible_receipts`, receipts_dir = shadow_receipts) |
| Independent reproduction | detached worktree at `71835ea1`, separate process, fresh work dir `C:/t/nola2`: same package id and digest, package git blob identical (`0294443a`), same Rule J bundle, independent FAST 15/15 — `new_orleans_la_reproduction_001.json` |
| Census | 347 qualifying identities (Orleans 282, Jefferson 62, St. Bernard 2, Plaquemines 1) |
| Published | 104 pet-friendly, 64 verified no-pets (168 resolved, 48.4 %) |
| Held | 179, **actionable 0** |
| Readiness | TECHNICAL SOURCE READY = YES; COVERAGE READY = YES |

An earlier package (`8585917a`, sealed from `5588c2fd`, FAST 15/15, reproduced byte-identical) was superseded by this one after the static-silent browser sweep below; its files were removed from the staging tree (history keeps them).

## Lineage

- Current live: Kansas City deploy `6ac4dc8a39b0e7274828a32b` (43 markets / 4,136 profiles / 4,552 release-index / 4,628 served), live source `117afe11`, built_from `c6609370`, bundle `6a35c238…`, sitemap `3d5d9425…`, host verified (`release_index live-source --verify-host`).
- Automatic base derives **YES** → `e42ae364` (`registration_release_lane.derive_registration_base`, docs-only child of `117afe11`).
- Start 2026-10-06T15:14:45Z. First FAST-clean package committed 18:55:33Z (3 h 41 min); final package committed 19:52:46Z — **4 h 38 min** zero-to-source-ready; coverage-ready verified with it (actionability recomputed on the sealed report) — **4 h 39 min**.

## Geography

16 corridors over 46 ZIPs — 7 CORE (French Quarter / Marigny / Bywater, CBD / Canal, Warehouse District / Convention Center, Garden District / Uptown, Mid-City, MSY Airport / Kenner, Metairie), 6 CORRIDOR (Elmwood / Jefferson / Harahan, Gretna, Harvey, Westwego, Algiers, New Orleans East), 3 FRINGE (Marrero, Chalmette / Arabi, Belle Chasse). The French Quarter, CBD and the other neighbourhoods are reporting overlays over the ZIP partition, never split codes (French Quarter overlay: 73 admitted rows).
6 corridors publish (≥ 5 pet-friendly profiles): French Quarter–Marigny–Bywater, CBD–Canal Street, Warehouse District–Convention Center, MSY Airport–Kenner, Metairie, Harvey–West Bank.

Municipalities are never flattened: a row publishes the municipality its own postal code carries; "New Orleans" only for an Orleans Parish code. Published: New Orleans 282, Metairie 21, Kenner 15, Harvey 10, Gretna 5, Marrero 3, Avondale 2, Chalmette 2, Harahan 2, Belle Chasse 1, Bridge City 1, Elmwood 1, Jefferson 1, Westwego 1. Rows relabelled to their own municipality: 5 (e.g. Brent House Hotel "New Orleans" → Jefferson 70121; Residence Inn Elmwood "New Orleans" → Elmwood 70123). **WRONG-CITY NEW ORLEANS IDENTITIES = 0** (a census guard raises if any appears).

MSY: corridor decided by ZIP (70062–70065), 15 admitted rows; the one airport-named row outside it is Clarion Hotel & Suites New Orleans Airport (70001, Metairie). Airport-named rows refused outside the market: Baton Rouge Airport (70807) and St. Charles Parish "New Orleans Airport South" (70087) properties.

Boundary audit (discovered / admitted): Baton Rouge 72/0, Northshore 48/0, Houma–Thibodaux 26/0, St. Charles and river parishes 13/0, St. Bernard beyond Chalmette 0/0, Plaquemines beyond Belle Chasse and NAS JRB 2/0, Jefferson south of the West Bank 1/0, Mississippi Gulf Coast 53/0, other Louisiana / Mississippi 4/0. Rows admitted from a refused ZIP: 0.

## Census and lanes

2,134 raw observations → 1,115 graph nodes → 347 identities.
Lanes: City of New Orleans lodging-licence register (data.nola.gov `iqay-p646`, 410 leads; the STR licence register `ufdg-ajws` used only as an exclusion index), OSM (Louisiana + Mississippi extracts, 652 elements), brand inventories (109 leads), New Orleans & Company and Visit Jefferson Parish rosters (293), BringFido competitor leads (269), Places route discovery / gap / map-pin verification, first-party property pages (401 observations).
Lodging qualification: a licence-only row is admitted only with a Places-bound OPERATIONAL lodging listing, a bureau hotel / B&B / guest-house listing or a first-party page; STR-licensed premises and STR-host listings are vacation rentals.

Exclusions: OUTSIDE 321; non-hotel 66; vacation rental 61; timeshare 7 (Bluegreen Club La Pension ×2, Club Wyndham Avenue Plaza, Club Wyndham La Belle Maison, Holiday Inn Club Vacations ×2, WorldMark Hotel); military-restricted 2; closed 1 (Claiborne Mansion, its own site: "The Claiborne Mansion has closed."); preopening 1 (Fairmont New Orleans, "set to open in 2026"); name-only residue 144; identity-review residue 168 (incl. The Quarter House, held LODGING_CATEGORY_UNCONFIRMED: its own site carries an "Owner's Portal").

## Policy acquisition

- **Attended browser** (claude-in-chrome; no JS exfiltration, no relay, no bypass, no CAPTCHA solved): 262 recorded attempts, 127 reads bound. Marriott 40 attempts / 40 reads, **0 denials**. Hilton 28 / 26. Other families 222 / 87 (independents 160 / 40).
- A **static-silent sweep** re-read every row the static lane had judged SOURCE_SILENT from a home page alone, through its own FAQ / policy pages: it converted Monteleone, Troubadour, Old No. 77, Alder, ONE11, Hotel St. Pierre, Maison St. Charles (pet-friendly) and Chimes, Mayfair, Monrose Row, Sully Mansion (no pets), and found The Syd, Castle Day (group villas) and Compass Point (event venue) are not hotels.
- **Quote integrity:** the accessibility-tree *find* summary paraphrased two answers (La Belle Esplanade; Crowne Plaza Astor, whose sentence actually ends "…nightly fee of 35 USD with a maximum fee of 70 USD"). Every quote taken from a summary rather than a node or the page text was re-verified; Astor was re-recorded from a zoomed screenshot (its capped fee now publishes no fee) and ESA Airport trimmed to its verified sentence (no fee).
- Hijacked / dead domains (gambling, wholesale shopping, foreign Cloudflare walls) were recorded as failed navigations; nothing on them was clicked. Two hosts were declined at the browser permission prompt and not retried.
- **Firecrawl** (existing plan credits only): 160 → 60 (100 used; the reserve floor of 60 was kept): competitor challenge 25, Choice / IHG city-page discovery 8, Choice / IHG brand property pages 40 (40 answered, 30 with own address), Firecrawl pass 27 (36 attempts: 15 blocked, 15 failed, 5 mismatch, 1 silent — bimodal billing). No retry pass was bought.
- **Google Places**: 239 requests (189 Enterprise, 50 Pro) inside the free monthly allowance; a targeted `--only` run asked just the 23 routing holds that had never been queried.
- Static plain client 202 requests; Wyndham property service 17 read / 18 retired; independents' policy pages 147 targets; Places-named sites 60 targets.
- New paid spend: **none**. Provider cost: **$0 USD**.

## Held rows (179) — all non-actionable

| Disposition | n | Class |
|---|---|---|
| SOURCE_SILENT | 71 | pages read (home and FAQ / policy pages), bound, no operative policy |
| ROUTING_HOLD | 57 | 35 no official web presence (Places queried); 11 dead / hijacked domains; 8 non-first-party sites; 2 brand routes landing on search; 1 other |
| IDENTITY_MISMATCH_HOLD | 23 | pages with no address of their own, sites Places names that never state the premises, 2 dual-brand |
| EVIDENCE_HOLD | 21 | refusals / acceptances the shared reader does not interpret (held, never published); Fairmont preopening; Claiborne closed |
| ACCESS_BLOCKED | 7 | routes refused on every free / authorized lane |

Actionability: AUTHORIZED_ROUTER_EXHAUSTED 175, REQUIRES_FOUNDER 3 (safe holds), HELD_UNTIL_OPENING 1, ACTIONABLE_NOW **0**.

**Founder rulings needed at registration** (never self-signed into `identity_resolutions.json`):
- SpringHill Suites + TownePlace Suites New Orleans Downtown/Canal Street, both 1600 Canal St 70112 (`msysi`, `msytd`): a dual-brand building is two hotels.
- The Garden District Hotel's "Pets are not permitted at The Garden District Hotel." — a refusal the shared reader does not interpret; publishing it needs a shared-reader change this order may not make.

## Publication safety (all zero)

PF with explicit refusal 0; question-only PF 0; service-animal-only acceptance 0; preopening / closed published 0; timeshare published 0; military published 0; misleading single fees 0; no-pets quote without refusal 0.
Fees: 29 single-basis published; 22 tiered withheld; 10 unsafe withheld (8 basis not stated, 2 stay-length).

## Market-local fixes made this order (no shared factory code changed)

- Policy-reads: the state regex refused every five-digit run after "LA" (it was written to skip "LA 23" route numbers), which left cities on streets and split the IHG Superdome row from its own licence; route numbers are now 1–4 digits. Glued footer seams ("BoulevardNew Orleans") are split on the market's own municipality names. A re-read that states the postal code an earlier read lacked replaces it.
- Browser lane: admitted rows bind first; one identity's review twin never ties with it; NON_LODGING rows are a fallback binding target (the chain had alternated between two census states).
- Census: spelled house numbers fold for the merge key ("Three Galleria Boulevard"); all-caps footer cities publish in display spelling.
- Clean authority: a definite attended read is not displaced by a later static / Firecrawl capture (Bourbon Orleans' static "no pets" came from "there are no pet-free rooms"); species restriction is not a refusal ("other pets are not permitted" — Hotel Peter & Paul); closure statements hold as CLOSED_PERMANENTLY; refusal / acceptance shapes added only where the shared reader rates the exact quote eligible.
- Staging: "for the first six (6) nights" / "not to exceed" are stay-length conditions.
- Non-hotel rulings from first-party pages: Gotham Lofts, Lafayette by Kasa ("by <operator>" names refused before the brand-lane override), The Eleanor, The Patterson, Little Eazy, Memoir Residential, Macarty House, The Syd, Castle Day, Compass Point; timeshare names override brand listings.
- Places lane: `--only` restricts new requests to named rows (pay once to find a page).
- Kansas City text purged from staged outputs and downstream modules; the boundary audit and accountings rewritten for New Orleans.

## Isolation and operations

- Only `new-orleans-la` / `new_orleans_la` paths committed; no shared document, generated global, factory module or other market touched; no `build_market_authorities --write`; no broad regression.
- Seal, FAST and reproduction ran detached and strictly sequentially, never two builds at once. Reproduction worktree `C:/t/nolarepro` and work dirs `C:/t/nola0`, `C:/t/nola1`, `C:/t/nola2` removed; no process created by this order remains.

## Machine-readable accountings

`launch_packages/pettripfinder/markets/reports/new_orleans_la_{source_ready,source,provider,brand,corridor,municipality,boundary}_accounting_001.json`, `new_orleans_la_competitor_reconciliation_001.json`, `new_orleans_la_actionability_001.json`, `new_orleans_la_fee_withholding_001.json`, `new_orleans_la_shadow_package_001.json`, `new_orleans_la_reproduction_001.json`; final partition `markets/staging/new-orleans-la/launch_package/new_orleans_la_final_partition_001.json`.

## FINAL ANSWERS

1. START TIMESTAMP = 2026-10-06T15:14:45Z
2. ZERO_TO_SOURCE_READY = 4 h 38 min (final package committed 19:52:46Z; first FAST-clean package 3 h 41 min)
3. ZERO_TO_COVERAGE_READY = 4 h 39 min
4. CURRENT LIVE DEPLOYMENT = 6ac4dc8a39b0e7274828a32b (Kansas City; live source 117afe11, built_from c6609370, bundle 6a35c238)
5. CURRENT LIVE MARKETS = 43 (4,136 profiles / 4,552 release-index / 4,628 served)
6. AUTOMATIC BASE DERIVES = YES → e42ae364
7. TOTAL DISCOVERED = 2,134 raw observations
8. NORMALIZED IDENTITIES = 1,115 graph nodes
9. QUALIFYING CENSUS = 347
10. PET-FRIENDLY = 104
11. VERIFIED NO-PETS = 64
12. RESOLVED = 168
13. UNRESOLVED = 179
14. RESOLUTION RATE = 48.4 %
15. ACTIONABLE UNRESOLVED = 0
16. HOLDS BY CLASS = SOURCE_SILENT 71, ROUTING 57, IDENTITY 23, EVIDENCE 21, ACCESS_BLOCKED 7, NEGATION 0, BROWSER_CAPTURE 0
17. EXCLUSIONS BY CLASS = OUTSIDE 321, NON_HOTEL 66, VACATION_RENTAL 61, TIMESHARE 7, MILITARY_RESTRICTED 2, CLOSED 1, PREOPENING 1, NAME_ONLY 144, IDENTITY_REVIEW 168
18. PREOPENING IDENTITIES = 1 (Fairmont New Orleans)
19. PREOPENING PUBLISHED = 0
20. TIMESHARE / VACATION-OWNERSHIP IDENTITIES = 7 (+1 ownership-unconfirmed hold: The Quarter House)
21. TIMESHARE / VACATION-OWNERSHIP PUBLISHED = 0
22. NEW ORLEANS WRONG-CITY IDENTITIES = 0
23. PUBLISHING CORRIDORS = 6 of 16
24. COMPETITOR RAW / NORMALIZED / MATCHED / TRUE MISSING = 380 / 269 / 116 / 0
25. MATERIAL IDENTITY GAP = NO
26. MATERIAL POLICY GAP = NO
27. FIRECRAWL ATTEMPTED / SUCCESS = 76 property-page attempts / 40 answered (brand pages; the 36-attempt pass yielded no publication-grade read); plus 25 competitor and 8 discovery pages
28. GOOGLE PLACES REQUESTS = 239 (189 Enterprise, 50 Pro)
29. MARRIOTT CENSUS = 38
30. MARRIOTT ATTEMPTED = 40
31. MARRIOTT READ SUCCESS = 40
32. MARRIOTT ACTIONABLE REMAINING = 0
33. OTHER BROWSER ATTEMPTED / SUCCESS = 222 / 87
34. DUAL-BRAND / SHARED-CAMPUS HOLDS = 2 (1600 Canal St)
35. HISTORIC-INN / GUESTHOUSE HOLDS = 79
36. SINGLE-BASIS FEES PUBLISHED = 29
37. TIERED FEES WITHHELD = 22
38. UNSAFE / MULTI-AMOUNT FEES WITHHELD = 10
39. MISLEADING SINGLE FEES = 0
40. PET-FRIENDLY WITH EXPLICIT REFUSAL = 0
41. QUESTION-ONLY PET-FRIENDLY = 0
42. SERVICE-ANIMAL-ONLY ACCEPTANCE = 0
43. EXISTING PROVIDER CREDITS USED = Firecrawl 100 plan credits (160 → 60); Places 239 requests inside the free allowance
44. NEW PAID SPEND = 0
45. PROVIDER COST = $0
46. RULE J NONEMPTY = PASS (644 files / 628 HTML)
47. RULE K NONVACUOUS = PASS (BYTE_IDENTICAL, 4 cold builds)
48. FAST RECEIPT CURRENTLY ELIGIBLE = YES
49. SHADOW PACKAGE = pkg-new-orleans-la-939f3cda64d39402
50. PACKAGE REPRODUCIBLE = YES (in-process and independent worktree, byte-identical)
51. PACKAGE DIGEST = sha256:939f3cda64d394023919387400281d378b49e68ca747ccb7a0bbe4af5abd0126
52. FAST = 15/15 PASS
53. TECHNICAL SOURCE READY = YES
54. COVERAGE READY = YES
55. CROSS-MARKET FILE CHANGES = 0
56. FACTORY CODE CHANGED = NO
57. BROAD REGRESSION RUNS = 0
58. FINAL PRODUCTION CANDIDATE CREATED = NO
59. FOUNDER AUTHORIZATION CREATED = NO
60. NEW ORLEANS DEPLOYED = NO
61. origin == HEAD = YES (verified after push)
62. tree clean = YES (verified after push)

Performance: active compute ≈ the whole wall time (browser reading dominated; the four seal / reproduction runs took ≈ 4–5 min each); provider / cooldown wait 0 (no Akamai or DataDome wall was met); founder intervention: none during the run.

NEW ORLEANS SOURCE READY = YES
NEW ORLEANS COVERAGE READY = YES
ACTIONABLE UNRESOLVED = 0
NEW ORLEANS WRONG-CITY IDENTITIES = 0
PET-FRIENDLY RECORDS WITH EXPLICIT REFUSAL = 0
QUESTION-ONLY PET-FRIENDLY RECORDS = 0
SERVICE-ANIMAL-ONLY ACCEPTANCE = 0
PREOPENING PROFILES PUBLISHED = 0
TIMESHARE / VACATION-OWNERSHIP PROFILES PUBLISHED = 0
MISLEADING SINGLE FEES = 0
RULE J NONEMPTY = PASS
RULE K NONVACUOUS = PASS
FAST = 15/15 PASS
FACTORY CODE CHANGED = NO
BROAD REGRESSION RUNS = 0
NEW ORLEANS FINAL CANDIDATE = NO
NEW ORLEANS DEPLOYED = NO
WAITING FOR RELEASE QUEUE = YES

STOP.

Do not register.
Do not authorize.
Do not deploy.
