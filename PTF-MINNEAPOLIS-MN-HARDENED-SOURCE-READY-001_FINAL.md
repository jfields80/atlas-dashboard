# PTF-MINNEAPOLIS-MN-HARDENED-SOURCE-READY-001 — FINAL

Market `minneapolis-mn`: Minneapolis / St. Paul / Twin Cities, Minnesota.
Worktree `C:\Atlas-Minneapolis-MN-Hardened-V1`, branch `worker/ptf-minneapolis-mn-market-001`.
Built from zero on the Portland-live lineage: base `e494698f`, live lineage `aeb57df1`, built_from `22ff1c94`.
Report written 2026-10-04 (UTC).

Minneapolis was not registered, authorized or deployed.

## 1. Outcome

| | |
|---|---|
| Qualifying census | **258** |
| Pet-friendly (published in the shadow package) | **156** |
| Verified no-pets | **66** |
| Resolved / unresolved | 222 / 36 (86.0 %) |
| Actionable unresolved | **0** (30 router-exhausted, 6 dual-brand rows held for a shared ruling) |
| Shadow package | `pkg-minneapolis-mn-5e356167a116c464`, `SHADOW_UNTIL_REGISTERED`, sealed from `4b019137` |
| FAST | **15/15 PASS**, 0 UNKNOWN, 0 FAILED |
| Rule J | 953 files / 937 HTML, bundle `cdd95614…`, output present |
| Rule K | BYTE_IDENTICAL (non-vacuous: 4 cold builds of the 953-file bundle, 0 reuse hits) |
| Receipt | `pkg-minneapolis-mn-5e356167a116c464-88a5ed7276ec6ba9.json`. `eligible_receipts(..., receipts_dir=shadow_receipts)` returns it; `receipt_output_defects` = [] |
| Independent reproduction | Separate detached process in a detached worktree at `4b019137`. Same package id and digest, FAST 15/15, 0 data and 0 site differences |
| Technical source ready | **YES** |
| Coverage ready | **YES** |

## 2. Lineage and current live (Phase 1)

`minneapolis_mn_current_live_001.json` (verified with `release_index live-source --fetch --verify-host`):

- Deploy `6ac264b79e70ce6a7db4baaf` (record `ptf-deploy-portland-004-…`), deployed 2026-10-04T14:38:20Z.
- Source `aeb57df15d91…`, built_from `22ff1c94…`.
- Bundle `d674d2898af1…`, sitemap `a50f1e343949…`. Host verified.
- 41 markets / 3,819 profiles / 4,206 release-index routes / 4,280 served routes.
- `origin/main` is stale (`c236f52d`); HEAD `e494698f` contains the live release.
- Automatic base derivation works and gives base `e494698f`.

The shadow package's `parent_live_state` names this deploy. Once any later release is live, FAST rule N will fail this package; that is by design. The registration order will then re-seal the same committed inputs against the new parent.

## 3. Geography (Phases 2–5)

24 corridors over the postal-code partition (`minneapolis_mn_geography_001`, `minneapolis_mn_corridor_registry_001.json`):

- **CORE (10):** downtown-minneapolis, university-dinkytown, uptown-south-minneapolis, northeast-minneapolis, north-minneapolis, downtown-st-paul, st-paul-midway, st-paul-neighborhoods, msp-airport, bloomington-mall-of-america.
- **CORRIDOR (9):** eagan, richfield, edina, eden-prairie, minnetonka-hopkins, plymouth, roseville, maplewood-oakdale, woodbury.
- **FRINGE (5):** brooklyn-center-brooklyn-park, maple-grove, burnsville-shakopee, mendota-heights-inver-grove, golden-valley-st-louis-park.

The neighbourhood overlays (North Loop, Mill District, Lowertown, Cathedral Hill / West 7th, Mall of America, Bloomington East / West) never split a ZIP code.

**Two cities, never flattened.** St. Paul has its own three corridors. Admitted rows keep their own city: 19 St. Paul and 57 Minneapolis by stated city; the rest sit in the suburbs.

**MSP / Bloomington / Mall of America identity safety.** A name never places a property. "MSP Airport" or "Mall of America" in a name decides nothing; the property's own postal code does. Ten admitted rows carry an airport or mall name and sit outside the msp-airport and bloomington-mall-of-america corridors, each where its own code puts it. Examples:
- Four Points by Sheraton *Mall of America* Minneapolis Airport is Richfield (55423).
- Courtyard / Fairfield / ESA *Minneapolis-St. Paul Airport* are Mendota Heights (55120).
- SpringHill / TownePlace *Airport/Eagan* are Eagan (55122).

**Boundary audit** (`minneapolis_mn_boundary_accounting_001.json`), rows discovered / admitted:

| Area | Discovered | Admitted |
|---|---|---|
| Rochester (FUTURE_STANDALONE rochester-mn) | 44 | 0 |
| Duluth / North Shore (FUTURE_STANDALONE duluth-mn) | 37 | 0 |
| St. Cloud (FUTURE_STANDALONE st-cloud-mn) | 24 | 0 |
| Mankato (FUTURE_STANDALONE mankato-mn) | 24 | 0 |
| Stillwater / St. Croix | 11 | 0 |
| North metro beyond I-694 | 24 | 0 |
| Outer south metro | 23 | 0 |
| Western exurbs | 16 | 0 |
| Wisconsin | 1 | 0 |
| Other Minnesota / out of state | 28 | 0 |

Rows admitted from a refused postal code: **0**.

## 4. Discovery and census (Phases 6–11)

- **Owned data:** 0 owned Minneapolis identities or policies. 9,679 live names were used for the cross-market collision test.
- **Public register:** none readable. The Minneapolis and St. Paul open-data hubs carry liquor and rental licences only, and MDH lodging licensing is informational (14 free requests measured this).
- **OSM:** Geofabrik Minnesota extract, 754 lodging elements.
- **Brand inventories:** 177 leads (Marriott 75, Hilton 60, Wyndham 40, Drury 1, Sonesta 1), 228 free requests. A re-run with every admitted suburb added to the locality filter found the same 177.
- **Destination organisations:** 105 rows (Meet Minneapolis 72 via its public listing index, Visit Saint Paul 21, Visit Roseville 12).
- **BringFido:** 531 raw / 316 normalized (identity only, never policy).
- **Places gap and map-pin verification:** see §6.

Census: 1,545 raw observations → **866 graph nodes** → **258 qualifying identities**.

## 5. Policy acquisition (Phases 12–19)

| Lane | Result |
|---|---|
| Attended browser (claude-in-chrome) | 212 attempts, 192 reads, **0 challenge denials**. Marriott 71 / 70 (no Akamai denial); Hilton 57; Choice 21; Radisson 12; Hyatt 10; independents 21; ESA 5; Motel 6 / Studio 6 4; Best Western 3; others 8 |
| Wyndham property service (plain client) | 42 routes, 23 read, 19 retired (brand redirects to its own search) |
| Firecrawl (existing credits) | BringFido 30 credits; route discovery 10 credits (IHG 54 routes; Choice refused at 0 credits); IHG brand pages 25 / 25 with own JSON-LD address. 65 credits in all (336 → 271) |
| Free static capture | 65 targets (45 ACCESS_DENIED) |
| Independents' own sites (Places-named) | 15 targets, 7 bound |

Repaired reader rules held throughout:
- A question is never acceptance.
- An explicit refusal is never pet-friendly.
- Service-animal-only is never acceptance.
- A Choice "Pets Allowed: Yes" chip with no General line is held.
- A Motel 6 "Pets Allowed" amenity chip is SOURCE_SILENT.

The shared reader was not modified. Two market-local refusal shapes and one acceptance shape were added, each only after the shared reader rated the exact quote the same way:
- "is not a pet-friendly hotel" (The Saint Paul Hotel);
- "Pets and pets classified as ESAs are not allowed" (Holiday Inn St. Paul Downtown);
- "Only dogs weighing N pounds and under are permitted" (Hyatt Regency Minneapolis, Hyatt Place St. Paul).

**Fees** (`minneapolis_mn_fee_withholding_001.json`):
- 35 single-basis fees published.
- 47 tiered fees withheld.
- 16 unsafe single fees withheld: basis not stated 12, stay-length condition 4. Hyatt Regency Bloomington's "One to seven nights: $100 … per stay" is withheld; the stay-length rule was extended to spelled-out lengths for it.
- Misleading single fees published: **0**.
- A daily fee never publishes as per-stay: "daily" maps to per_day.

## 6. Closure work in this order's final stretch, and the defects it exposed

1. **A Portland coordinate envelope was live in the census (fixed).** The clone carried Portland's "refused by pin" box (45.255–45.79 N, 123.17–122.34 W). Under it, every Twin Cities row with a map pin but no postal code was classified OUTSIDE_MARKET (101 rows).
   - It is replaced by the admitted corridors' measured extent, 44.73–45.14 N / 93.60–92.89 W.
   - Places map-pin verification (46 PRO requests, binding only within 400 m of the row's own pin or on its own house number) found 13 operating lodging places at admitted ZIPs. **9 were admitted** as census identities the census had missed: Hotel Alma, Celeste of St. Paul, Como Lake B&B, Emerald Inn, Northernaire Motel, Midwest Hotel, Valley Inn Shakopee, Motel 6 Brooklyn Center and Coratel Maple Grove.
   - Two of the 13 stay held at census review:
     - Midway Motel: its bare name collides with Nashville's live identity.
     - La Quinta Minneapolis Northwest (7011 Northland Cir, Brooklyn Park): Wyndham's own route redirects to its Brooklyn Park search, so there is no property page.
   - The other two of the 13 are the three Northernaire map rows, which are one building.
   - Of the other pins, 16 were duplicates of admitted rows, 6 were outside the market and 1 was permanently closed.
2. **The Wyndham lane matched city slugs exactly** and skipped `inver-grove-heights`. It now matches the way the brand inventory does, and it also reads Wyndham routes the map carries. Microtel Inver Grove Heights and Ramada Plymouth were then read on the brand's own property service (Ramada published pet-friendly; Microtel held, see §8).
3. **Portland provenance in comments and report text (fixed).** The clone's market rename had turned 22 Portland findings into "MINNEAPOLIS:" claims (for example "Residence Inn Minneapolis Vancouver"). Those comment lines are restored to their Portland text.
   - The competitor lane's out-of-region list (Oregon towns) and the census's fold description (Portland interstates) are rewritten for Minnesota.
   - The accounting's boundary areas are rewritten too.
4. **Places gap-verification query text (defect, reported, not re-run).** The 30 BringFido gap queries ran as `"<name> Minneapolis OR"`. Binding was by each place's own postal code and admitted ZIPs, so the 22 / 5 / 3 verdicts stand. Pay-once keeps the recorded answers; the query text is corrected for any future run.
5. **The census step had failed silently in the helper loop** for several cycles: a duplicate "Prime Rate Inn" key, from a page address printed without commas. Fixed (a trailing in-market "City MN" is dropped from a page-read street when its own ZIP was read). The loop now stops on any failing step.

## 7. Accounting (Phases 20–29)

Holds by class (36):
- **SOURCE_SILENT 10:** Alma, Como Lake B&B, Four Seasons, Holiday Inn & Suites Maple Grove, Motel 6 Brooklyn Center / Burnsville / Roseville (amenity chip only), Nicollet Island Inn, Northernaire Motel, Norwood Inn.
- **ROUTING 10:** Aqua City Motel, Metro Inn, Midwest Hotel and Sonesta Simply Suites Richfield (no web presence); Coratel Maple Grove, Coratel Richfield and Emerald Inn (affiliate template sites); Super 8 Brooklyn Center (brand route retired; Places CLOSED_PERMANENTLY); University Inn (dead domain; Places CLOSED_PERMANENTLY); ESA Airport Eagan (now a Studio 6 page with no house number).
- **IDENTITY_MISMATCH 9:** 6 dual-brand rows (§8); enVision St. Paul South and Valu Stay (site states no address); Key Inn (page states no address).
- **ACCESS_BLOCKED 4:** 300 Clifton (challenge), Historic District B&B, Sandalwood (site not published), Valley Inn (site never serves).
- **EVIDENCE 3:** AmericInn Burnsville (service-animal-only), Holiday Inn Express Eagan (quote contradicts claim), Microtel Inver Grove Heights (§8).

Exclusions:
- vacation rental 46, non-hotel 64 (UMN Conference & Event Services ruled NON_HOTEL), timeshare 0, military 0;
- outside 320, duplicate 0, closed 0;
- graph residue: name-only 142, identity-review 36.

Corridors publishing (5 or more PF): **14 of 24**. Downtown Minneapolis 33 PF, Bloomington / MOA 28, Brooklyn Center / Park, Burnsville / Shakopee, Eagan, Roseville and Maple Grove 5–9 each, plus 7 more. The 10 thinner corridors are never forced.

Competitor reconciliation: 531 raw / 316 normalized / 141 matched (137 distinct identities) / 9 TRUE_MISSING. All 9 are explained:
- 4 are census rows under another name (Places matched address);
- 2 are outside (White Bear Lake, Coon Rapids);
- Historic District B&B is admitted;
- Lyndale Church Lodge (×2) has no street number.

Machine-readable accounting: `minneapolis_mn_{source,provider,brand,corridor,boundary}_accounting_001.json`, `minneapolis_mn_competitor_reconciliation_001.json`, `minneapolis_mn_actionability_001.json`.

## 8. Issues for the operator

1. **Dual-brand buildings: 3 premises, 6 rows held.**
   - Home2 + Tru Minneapolis Downtown (317 2nd Ave S).
   - Home2 + Tru Mall of America (2415 E Old Shakopee Rd, Suites A / B).
   - Comfort Inn + MainStay MSP (1321 E 78th St, Bldg A / B).

   Each needs a shared `identity_resolutions.json` ruling. That is not self-signed here; the registration order should carry it.
2. **Microtel Inver Grove Heights.** Wyndham's own text accepts dogs ≤30 lb, then ends "Sorry no other pets are allowed". The market reader reads that as a refusal; the shared reader rates the quote an acceptance. Held, rather than weakening the publication audit's refusal guard for one row.
3. **Probably closed or rebranded:**
   - Super 8 Brooklyn Center and University Inn (Places CLOSED_PERMANENTLY).
   - ESA Airport Eagan → Studio 6.
   - Bloom Hotel (ex-La Quinta Bloomington W) is published from its own site.
   - Loews Minneapolis is now The Lofton.
   - Sonesta Simply Suites Richfield is not on Sonesta's own search.

   None is excluded as closed without a first-party statement.
4. **The census-envelope defect class may exist in other clones.** Any market cloned from Portland that kept `45.255 / 45.79 / -123.17 / -122.34` silently refuses its own pinned no-ZIP rows.

## 9. Shadow package, FAST, receipt, reproduction (Phases 30–35)

- Inputs were committed at `8b82199f`; the shard was staged and committed at `4b019137`.
- **Seal.** Run from `4b019137` as a detached `Start-Process` with work dir `C:/t/msp1` (18:42:21Z → receipt 18:50:29Z); it was the only seal.
  - Package `pkg-minneapolis-mn-5e356167a116c464`, digest `sha256:5e356167a116c464a4d9e78dbc5907a5b7299ed4f5a5e23dbf87301d7f5cef34`, reproducible in-process.
  - FAST 15/15; first-party gate 222 / 222 eligible.
  - Rule J: 953 files / 937 HTML, output present. Rule K: BYTE_IDENTICAL.
  - `SEALED_AT` = 2026-10-04T18:40:00Z, after the last capture (seq 212, 18:38:42Z) and set by the real clock (18:40:04Z).
- **Receipt** `…-88a5ed7276ec6ba9.json`: stored ELIGIBLE = YES, currently eligible, no output defects, no UNKNOWN rules.
- **Independent reproduction** (`minneapolis_mn_independent_reproduction_001.json`):
  - Ran from `git worktree add --detach C:/t/msprw 4b019137` as a separate detached process, started **after** the main seal exited (18:53:29Z → receipt 18:58:05Z), with work dir `C:/t/msp2`.
  - Result: same package id and digest, FAST 15/15, same Rule J bundle `cdd95614…` (953 / 937), Rule K BYTE_IDENTICAL.
  - Data: 17 files compared, 0 differences. Site: 2,036 files compared (oa / ob 957 each, sa / sb 61 each), 0 differences (CRLF-normalised). **BYTE IDENTICAL = YES.**
  - The worktree was removed afterwards.
- Runs were sequential on this ~16 GB machine (free memory 1.9–2.6 GB during the builds). There was no memory event.

## 10. Isolation (Phase 35)

`git diff --name-only e494698f HEAD` lists only Minneapolis-owned paths:
- `minneapolis_mn_*` modules and reports;
- the `minneapolis-mn` census, proposed market and staging tree;
- `discovery/config/minneapolis_mn.json`;
- this report.

| Category | Changes |
|---|---|
| Cross-market source | 0 |
| Shared factory code | 0 |
| Current live | 0 |
| Deployment state | 0 |

No broad regression was run. These are untouched: `identity_resolutions.json`, `launch_participation.json`, supersessions, the generated globals, and every other market's files. No write landed in another worktree.

## 11. Performance (Phase 36)

| | |
|---|---|
| Start | 2026-10-04T15:15:49Z |
| Zero to source ready (FAST receipt written) | 3 h 34 m 40 s (18:50:29Z) |
| Zero to coverage ready (actionability decided) | 3 h 37 m 56 s (18:53:45Z) |
| Active compute time | Not separately metered: the order ran continuously over the wall clock above |
| Provider / cooldown wait | 0 (no Akamai, DataDome or rate-limit cooldown occurred) |
| Firecrawl credits used | 65 (336 → 271) |
| Places requests | 135 (59 Enterprise + 76 PRO, inside the free monthly allowance) |
| New paid spend / provider cost | USD 0 / USD 0 |
| Founder intervention | none |

Cleanup:
- The seal and reproduction processes exited on their own, and the reproduction worktree was removed.
- No order-created watcher, server or child process remains.
- Work dirs `C:/t/msp0`, `C:/t/msp1` and `C:/t/msp2` are scratch output outside the repo.
- The browser tab used for the reads was closed.

## FINAL ANSWERS

1. START TIMESTAMP = 2026-10-04T15:15:49Z
2. ZERO_TO_SOURCE_READY = 3 h 34 m 40 s (FAST receipt 2026-10-04T18:50:29Z)
3. ZERO_TO_COVERAGE_READY = 3 h 37 m 56 s (coverage decided 2026-10-04T18:53:45Z)
4. CURRENT LIVE DEPLOYMENT = 6ac264b79e70ce6a7db4baaf (portland-or; source aeb57df1, built_from 22ff1c94, bundle d674d289)
5. CURRENT LIVE MARKETS = 41 (3,819 profiles / 4,206 release-index / 4,280 served)
6. AUTOMATIC BASE DERIVES = YES (base e494698f)
7. TOTAL DISCOVERED = 1,545 raw observations
8. NORMALIZED IDENTITIES = 866 graph nodes
9. QUALIFYING CENSUS = 258
10. PET-FRIENDLY = 156
11. VERIFIED NO-PETS = 66
12. RESOLVED = 222
13. UNRESOLVED = 36
14. RESOLUTION RATE = 86.0 %
15. ACTIONABLE UNRESOLVED = 0
16. HOLDS BY CLASS = SOURCE_SILENT 10, ROUTING 10, IDENTITY_MISMATCH 9, ACCESS_BLOCKED 4, EVIDENCE 3 (NEGATION 0, BROWSER_CAPTURE 0)
17. EXCLUSIONS BY CLASS = vacation rental 46, non-hotel 64, timeshare 0, military-restricted 0, outside 320, duplicate 0, closed 0, name-only residue 142, identity-review residue 36
18. PREOPENING IDENTITIES = 0
19. PREOPENING PUBLISHED = 0
20. TIMESHARE / VACATION-OWNERSHIP IDENTITIES = 0
21. TIMESHARE / VACATION-OWNERSHIP PUBLISHED = 0
22. PUBLISHING CORRIDORS = 14 of 24 (downtown-minneapolis, university-dinkytown, downtown-st-paul, bloomington-mall-of-america, eagan, eden-prairie, minnetonka-hopkins, plymouth, roseville, woodbury, brooklyn-center-brooklyn-park, maple-grove, burnsville-shakopee, golden-valley-st-louis-park)
23. COMPETITOR RAW / NORMALIZED / MATCHED / TRUE MISSING = 531 / 316 / 141 / 9 (all 9 explained: 4 census aliases, 2 outside, 1 admitted, 2 no street number)
24. MATERIAL IDENTITY GAP = NO
25. MATERIAL POLICY GAP = NO
26. FIRECRAWL ATTEMPTED / SUCCESS = BringFido 30 credits; route discovery 18 pages (IHG 10 served / 54 routes; Choice 8 refused at 0 credits); IHG brand pages 25 / 25 with own address; residual pass 0
27. GOOGLE PLACES REQUESTS = 135 (59 Enterprise + 76 PRO, free monthly allowance)
28. MARRIOTT CENSUS = 68
29. MARRIOTT ATTEMPTED = 71
30. MARRIOTT READ SUCCESS = 70 (0 Akamai denials)
31. MARRIOTT ACTIONABLE REMAINING = 0
32. OTHER BROWSER ATTEMPTED / SUCCESS = 141 / 122
33. DUAL-BRAND / SHARED-CAMPUS HOLDS = 6 rows (3 premises: Home2 + Tru Downtown, Home2 + Tru Mall of America, Comfort Inn + MainStay MSP)
34. SINGLE-BASIS FEES PUBLISHED = 35
35. TIERED FEES WITHHELD = 47
36. UNSAFE / MULTI-AMOUNT FEES WITHHELD = 16 (basis not stated 12, stay-length condition 4)
37. MISLEADING SINGLE FEES = 0
38. PET-FRIENDLY WITH EXPLICIT REFUSAL = 0
39. QUESTION-ONLY PET-FRIENDLY = 0
40. SERVICE-ANIMAL-ONLY ACCEPTANCE = 0
41. EXISTING PROVIDER CREDITS USED = Firecrawl 65 credits (336 → 271); Google Places 135 requests inside the free monthly allowance
42. NEW PAID SPEND = 0 (USD 0)
43. PROVIDER COST = USD 0
44. RULE J NONEMPTY = PASS (953 files, 937 HTML, output present)
45. RULE K NONVACUOUS = PASS (BYTE_IDENTICAL, 4 cold builds)
46. FAST RECEIPT CURRENTLY ELIGIBLE = YES
47. SHADOW PACKAGE = pkg-minneapolis-mn-5e356167a116c464 (SHADOW_UNTIL_REGISTERED)
48. PACKAGE REPRODUCIBLE = YES (in-process and independent; data 0 / site 0 differences)
49. PACKAGE DIGEST = sha256:5e356167a116c464a4d9e78dbc5907a5b7299ed4f5a5e23dbf87301d7f5cef34
50. FAST = 15/15 PASS, 0 UNKNOWN, 0 FAILED
51. TECHNICAL SOURCE READY = YES
52. COVERAGE READY = YES
53. CROSS-MARKET FILE CHANGES = 0
54. FACTORY CODE CHANGED = NO
55. BROAD REGRESSION RUNS = 0
56. FINAL PRODUCTION CANDIDATE CREATED = NO
57. FOUNDER AUTHORIZATION CREATED = NO
58. MINNEAPOLIS DEPLOYED = NO
59. origin == HEAD = YES (verified after push)
60. tree clean = YES (verified after push)

MINNEAPOLIS SOURCE READY = YES
MINNEAPOLIS COVERAGE READY = YES
ACTIONABLE UNRESOLVED = 0
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
MINNEAPOLIS FINAL CANDIDATE = NO
MINNEAPOLIS DEPLOYED = NO
WAITING FOR RELEASE QUEUE = YES

STOP.

Do not register.
Do not authorize.
Do not deploy.
