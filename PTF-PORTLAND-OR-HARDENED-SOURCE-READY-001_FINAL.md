# PTF-PORTLAND-OR-HARDENED-SOURCE-READY-001 — FINAL

Market `portland-or`: Portland / Greater Portland, Oregon, including the Vancouver, Washington corridor.
Worktree `C:\Atlas-Portland-OR-Hardened-V1`, branch `worker/ptf-portland-or-market-001`.
Built from zero on the Seattle-live lineage: base `0e2e8bb8`, live lineage `f0003e78`, built_from `438348c7`.
Report written 2026-10-04 (UTC).

Portland was not registered, authorized or deployed.

## 1. Outcome

| | |
|---|---|
| Qualifying census | **272** |
| Pet-friendly (published in the shadow package) | **150** |
| Verified no-pets | **47** |
| Resolved / unresolved | 197 / 75 (72.4 %) |
| Actionable unresolved | **0** (74 router-exhausted, 1 contradictory page held safely) |
| Shadow package | `pkg-portland-or-b6f95c2ae170f44b`, `SHADOW_UNTIL_REGISTERED` |
| FAST | **15/15 PASS**, 0 UNKNOWN, 0 FAILED |
| Rule J | 908 files / 892 HTML, bundle `f8a0a46d…`, output present |
| Rule K | BYTE_IDENTICAL (non-vacuous: two cold builds of the 908-file bundle) |
| Receipt | `pkg-portland-or-b6f95c2ae170f44b-84acb4fb89e4e3df.json`. `eligible_receipts` returns it and `receipt_output_defects` = [] |
| Independent reproduction | Separate detached process in a detached worktree at `a8fa126d`. Same package id and digest, FAST 15/15, 0 data and 0 site differences |
| Technical source ready | **YES** |
| Coverage ready | **YES** |

## 2. Lineage and current live (Phase 1)

`portland_or_current_live_001.json` (verified with `release_index live-source --fetch --verify-host`):

- Deploy `6ac169ef7c75c383eb79f824` (record `ptf-deploy-seattle-004-…`).
- Source `f0003e78b10d…`, built_from `438348c7…`.
- Bundle `cfaad64a7bcb…`, sitemap `63e052812b36…`. Host verified.
- 40 markets / 3,669 profiles / 4,044 release-index routes / 4,117 served routes.
- Automatic base derivation for Portland works and gives base `0e2e8bb8`.

The shadow package's `parent_live_state` names this deploy. Once any later release is live, FAST rule N will fail this package; that is by design. The registration order will then re-seal the same committed inputs against the new parent.

## 3. Geography (Phases 2–5)

The market has 21 corridors covering 70 ZIP codes (`portland_or_geography_001`):

- **CORE (13):** downtown-portland, pearl-old-town-northwest, south-waterfront-southwest, lloyd-convention-center, central-eastside, pdx-airport, northeast-north-portland, southeast-east-portland, beaverton, hillsboro, tigard, lake-oswego, gresham.
- **CORRIDOR (4):** tualatin-wilsonville, clackamas-happy-valley, troutdale-fairview, **vancouver-wa**.
- **FRINGE (4):** milwaukie, oregon-city-west-linn, sherwood, forest-grove-cornelius.

On the Oregon side, a place is admitted if it lies inside Oregon's Metro urban growth boundary.

**Vancouver, WA = CORRIDOR (class `CORRIDOR`, corridor `vancouver-wa`, 11 ZIPs).**
- Every one of its 34 admitted rows keeps its Washington identity: state WA, 98xxx postal code, and a Washington page.
- Precedent: Charlotte admitting Fort Mill, SC.
- Camas, Washougal, Battle Ground, Ridgefield and the rest of outer Clark County are outside the market.

**Columbia Gorge and Mount Hood are outside the market** (both are future standalone markets). This covers:
- Corbett, Cascade Locks, Hood River, The Dalles and Stevenson.
- Sandy, Welches and Government Camp.

Boundary audit (`county_and_border_boundary`), rows discovered / rows admitted:

| Area | Discovered | Admitted |
|---|---|---|
| Gorge | 25 | 0 |
| Mount Hood | 11 | 0 |
| Salem / Woodburn | 73 | 0 |
| Oregon Coast | 62 | 0 |
| Yamhill wine country | 22 | 0 |
| Outer Clackamas | 2 | 0 |
| Columbia County | 5 | 0 |
| Outer Clark County | 8 | 0 |
| Longview / Kelso | 4 | 0 |
| Seattle and other Washington | 4 | 0 |
| Other Oregon | 8 | 0 |

Rows admitted from a refused postal code: **0**.

Airport and suburban identity:
- Admission is decided by postal code only.
- Brand routes whose own city segment names a refused city are refused.
- Street spelling variants are folded so they merge without merging different premises. The folds cover the I-5/84/205/405 interstates, MLK Blvd ("Martin Luther King Jr/Junior", "M L King"), state routes (OR-99W/99E/213/217, SR-14), TV Hwy and quadrant directionals.
- Marriott's PDX codes are selected by prefix, so Portland, Maine (PWM) never enters.
- Milwaukie, OR is not Milwaukee, WI; identity is decided by premises, never by name.

## 4. Census (Phases 6–12)

1,644 raw observations from 9 productive lanes produced 933 graph nodes and 272 qualifying identities.

| Lane | Observations |
|---|---|
| Public lodging register | 0 (neither state publishes one; measurement record in `portland_or_registry_lane_001`) |
| OSM (Geofabrik oregon + washington extracts, merged by element) | 622 |
| Owned brand inventory | 47 |
| Brand city pages / sitemaps | 36 + 51 |
| Destination organisations (Travel Portland WP-REST POIs and map cards; Visit Vancouver USA Simpleview; Explore Washington County refused with 403) | 265 |
| Competitor leads (BringFido, identity only) | 327 |
| Places identity verification | 21 |
| Property pages (static, Firecrawl, attended browser) | 275 |

**Exclusions (rows not admitted):**
- Vacation rental: 48, including Kasa-operated The Clyde as a serviced-apartment operator.
- Timeshare / vacation ownership: 3. Only WorldMark Portland – Waterfront Park is in the market's ZIPs; it is NON_LODGING by the brand's own wyndham-vacations route.
- Non-hotel: 95 (RV parks/resorts, campgrounds, hostels, mobile-home parks, apartments, offices).
- Military-restricted: 0.
- Outside: 325.
- Duplicate listing: 1.
- Same-campus distinct entity: 2.
- Name-only graph residue: 149.
- Identity-review residue: 38.
- Closed: 0.

Identity safety corrections made in this order (all in Portland-local modules):
- **Dotted quadrants.** "875 S.W. 158th Ave." was read as two directionals against the map's "Southwest". The brand's own page therefore opened a second node at its own premises. This held ESA Beaverton and six Choice/Travel Portland pairs as false same-campus pairs. `S.W.` now folds to `SW`.
- **Hyatt House.** The flag "Hyatt House" contains the word "house", so the private-house map rule had refused Hyatt House Portland/Beaverton. Hyatt's own Portland search lists the hotel, and it is now admitted.
- **Plus codes.** A static capture had lifted a Google plus code ("G8C6+9W") as Hotel deLuxe's street. Plus codes are now never accepted as a street.
- **Duplicate Super 8.** "Super 8 by Wyndham" at 11504 NE 2nd St 98682 (with a 509 phone) is a DUPLICATE of Super 8 by Wyndham Vancouver East. The brand's own page gives ZIP 98684.
- **Bare chain flag.** "My Place Hotel" at 8300 NE Vancouver Mall is now named from the brand's own h1, "My Place Hotel-Vancouver, WA". The page and map addresses differ only in street type (Loop / Drive), so the page now joins that node by its own route at the same house number and ZIP.
- **Page titles.** Tab titles used as page names would have renamed hotels (for example "FAQs - Hotel Grand Stark" or "Hotel Policies | Hyatt House…"). Section and search phrases are now stripped.
- **Replacement characters.** Travel Portland's U+FFFD characters now become an apostrophe or a separator ("Schooner's Cove Inn", "Hotel Indigo Vancouver Waterfront - Portland").
- **Campground.** "RV Resort" is a campground: Sandy Riverfront RV Resort is now NON_LODGING.

**Competitor challenge** (BringFido; 18 cities; 473 raw → 327 unique; never a policy authority):
- 118 leads matched the census.
- 28 were TRUE_MISSING candidates, and all were put to Google Places gap verification:
  - 21 were verified as operational hotels at admitted ZIPs and admitted as census identities. Most were Motel 6, ESA, Choice and Best Western properties.
  - 7 were already in the census by address or phone.
- **MATERIAL IDENTITY GAP = NO.**

**Large-market quality challenge (Phase 29):** census rows by inventory:
- Travel Portland: 173 rows in admitted ZIPs.
- Brand inventories: owned 47, city 36, sitemap 51, plus every brand's own Portland directory read in the browser (Choice 20, ESA 7, Hyatt 7).
- PDX airport corridor: 39.
- Beaverton / Hillsboro: 37.
- East side (southeast-east, gresham, troutdale-fairview): 15.

No unexplained gap remains.

## 5. Acquisition (Phases 16–20)

- **Router.** Only the committed router was used; there was no Portland bypass.
- **Static plain client.** 164 targets, 157 requests. 7 valid, 59 access-denied, 48 identity-mismatch; the rest were navigation errors, unhydrated pages or no policy found.
- **Wyndham property service.** 22 selected, 10 read, 12 retired routes.
- **Independents' own sites.** 68 targets, 43 bound (129 free requests). Places-discovered sites: 12 targets, 11 bound.
- **Google Places.** 77 requests (49 Enterprise route discovery + 28 PRO gap verification) inside the free monthly allowance renewed 2026-10-01. Existing capacity, USD 0. The final 22 route-discovery requests covered rows whose census route had died. The lane pays once per query; prior answers were reused.
- **Firecrawl.** Existing credits only, 426 → 336 = **90 credits**:
  - BringFido: 31 credits over all runs.
  - Brand route discovery: 18 pages, 9 credited (Choice refused at 0 credits), giving 49 IHG routes.
  - IHG brand pages: 22/22 with their own address, 22 credits.
  - Routed residual pass: 42 identities, 28 credits, 0 publication-grade (17 blocked, 13 failed, 9 mismatch, 3 silent).
- **Attended browser** (claude-in-chrome; navigate + find/read_page/get_page_text only; no Akamai bypass, no JS exfiltration, no relay; paced):
  - 210 attempts, 164 bound reads, 2 challenge denials, 4 unbound reads. Two of the unbound reads are Hyatt House Airport and The Mindaro, whose rows are a held shared premises. The other two are a chain-wide Staypineapple FAQ and a guesthouse FAQ with no address.
  - **Marriott:** 46 in the census; 47 attempts, 45 reads, 2 Akamai denials (seq 41 pdxfp and seq 79 pdxac). Both were read on paced retries; pdxac was read about an hour after its denial. Result: 32 pet-friendly, 14 no-pets, 0 held. **Marriott actionable = 0.**
  - **Other families:** 163 attempts, 119 reads:
    - Hilton 36/36, Choice 19 (incl. WoodSpring) + Radisson 3, Best Western 12, ESA 7, Hyatt 5 (incl. the two shared-premises reads), Sonesta 4, IHG 2, Wyndham 1, independents 30.
    - All 16 Motel 6 / Studio 6 pages state only an amenity chip.
- Every browser read is in `raw_captures/browser_reads_001.jsonl` (seq 1–210) with the recorder's real-clock stamp.
- The last first-party capture is seq 210 at 2026-10-04T01:13:08Z. The package's `CAPTURED_AT` is that stamp, read from the log. `SEALED_AT` is 2026-10-04T01:33:00Z, set when the clock read 01:33:09Z. No timestamp is ahead of the clock.

## 6. Policy and evidence safety (Phases 14–15, 21–22)

The publication-safety audit returned zero on every count:

| Check | Count |
|---|---|
| Pet-friendly with explicit refusal | 0 |
| Question-only pet-friendly | 0 |
| Service-animal-only pet-friendly | 0 |
| Preopening / closed published | 0 |
| Timeshare published | 0 |
| Military published | 0 |
| Misleading single fee | 0 |
| No-pets record without a refusal sentence | 0 |

The first-party gate passed 197/197 records.

**Booking-affiliate template sites are not first-party.** Google Places names a templated affiliate site for several independents. These sites carry "Car Rental" / "Tours & Activities" tabs, a "Search Availability" widget, a generated FAQ, and a "Recommended Hotels" list of motels in Reedsport, Seattle and Cle Elum.
- `portlandinn.site` and `cameomotel-portland.us` had been bound by the static lane, and both rows were staged **verified no-pets**.
- The attended browser exposed the template before the seal. Both hosts, and the `.xyz` / `.top` throwaway domains (Bridgeway Inn's `bridgewayinnandsuitesportlandairport.xyz`), are now refused as first-party.
- Those rows hold as `NOT_FIRST_PARTY_SITE` routing holds.

Shared-reader disagreements and wording that does not state a policy are held, never published:
- Hampton Inn Portland East contradicts itself.
- The Dunes Motel says both "Dogs are welcome with a $25 nightly fee" and "is not pet-friendly".
- Fee-only, chip-only and question-only answers are held: Hotel deLuxe, CASCADA, Dossier, Oxford Suites, Red Lion Vancouver, WoodSpring ×2, Hyatt House Beaverton, Jupiter.
- The Paramount's "not allowed in the hotel" and the Super 8 / Grand Hotel at Bridgeport service-animal-only lines are held.
- Negation conflicts caught: 8, none published.

Route conflicts:
- Hotel Eastlund (BW Premier Collection) was read on bestwestern.com while the census bound its vanity domain. A brand page now outranks the vanity domain. It is published verified no-pets: "Pets are not accepted."
- Oxford Suites' own domain redirects to oxfordcollection.com. The census now binds the page that answered.

Preopening: none found. Closed or rebranded:
- Econo Lodge Portland Downtown: the brand route answers 404 and the brand's own Portland directory omits it.
- Inn at Marquam Hill: Places reports "permanently closed", and its domain answers an error page.
- Hyatt Place Portland – Pearl District: absent from Hyatt's own Portland search.
- All three are held, never published, and no closure is claimed on third-party evidence.

## 7. Fees (Phase 22)

- **20** single-basis fees are published. Each states its own basis; daily maps to per_day (McMenamins: "$30 per pet, per day"), nightly to per_night, and none becomes per stay.
- **33** tiered fees are withheld.
- **20** unsafe single fees are withheld: basis not stated 13, stay-length condition 5, two bases 2.

Three fees were caught by this order's own audit of the staged fees and withheld before the seal:
- Courtyard Portland Downtown/Convention Center: "fee increases after 5 nights" beside a $100 per-stay template.
- The Society Hotel: a daily fee with a "maximum charge".
- Residence Inn Portland Vancouver: "per stay/per month".

**Misleading single fees = 0.**

## 8. Holds and actionability (Phases 23–25)

| Disposition | Rows | Actionable |
|---|---|---|
| SOURCE_SILENT (16 Motel 6/Studio 6 chip-only, 6 page silent, 6 Places-found site silent) | 28 | 0 |
| ROUTING_HOLD (no web presence 9, dead route 5, not-first-party site 3, brand route lands on search 1) | 18 | 0 |
| EVIDENCE_HOLD | 17 | 0 |
| ACCESS_BLOCKED | 8 | 0 |
| IDENTITY_MISMATCH_HOLD (page never confirmed the premises) | 4 | 0 |

Founder-class rows: 1, The Dunes Motel, whose own page contradicts itself. It is held safely and does not gate coverage.

**Shared-campus hold.** Hyatt House Portland Airport and The Mindaro (JdV by Hyatt) both state 11707 NE Airport Way 97220. Hyatt's own search lists both. Publishing them needs a `same_campus_distinct_entity` row in the shared `identity_resolutions.json`, which this order did not write or sign.

**Publishing corridors (≥ 5 pet-friendly profiles): 11 of 21.**

| Corridor | Pet-friendly profiles |
|---|---|
| downtown-portland | 29 |
| pdx-airport | 22 |
| vancouver-wa | 21 |
| hillsboro | 12 |
| beaverton | 11 |
| northeast-north-portland | 9 |
| pearl-old-town-northwest | 8 |
| lloyd-convention-center | 6 |
| tigard | 6 |
| lake-oswego | 5 |
| tualatin-wilsonville | 5 |

Below the threshold:
- clackamas-happy-valley 4, troutdale-fairview 3.
- south-waterfront-southwest 2, central-eastside 2, forest-grove-cornelius 2.
- southeast-east-portland 1, gresham 1, sherwood 1.
- milwaukie 0, oregon-city-west-linn 0.

**MATERIAL POLICY GAP = NO.** Every unresolved row carries a terminal, explained reason.

## 9. Coverage decision (Phase 30)

All eight conditions hold (`portland_or_actionability_001.json`):
- actionable 0;
- no material identity gap;
- no unexplained policy gap;
- authorized lanes exhausted;
- Marriott queue resolved;
- browser brands processed;
- publication set safe;
- package deterministic and FAST clean.

Preopening rows: 0. Timeshare, apartment and rental rows are excluded. The shared-campus pair is held.

**COVERAGE READY = YES.**

## 10. Shadow package, FAST, receipt, reproduction (Phases 31–35)

- Inputs were committed at `82bee0e0` and staged at `a8fa126d`.
- **Seal.** Run from `a8fa126d` as a detached `Start-Process` with work dir `C:/t/pdx1`; it was the only seal.
  - Package `pkg-portland-or-b6f95c2ae170f44b`, digest `sha256:b6f95c2ae170f44b64f120f054cf07ef8ee48734d7ec2c6ee541882790eace5c`, reproducible in-process.
  - FAST 15/15; first-party gate 197/197 eligible.
  - Rule J: 908 files / 892 HTML, output present. Rule K: BYTE_IDENTICAL.
  - Committed at `cc1bc100`.
- **Receipt.** `…-84acb4fb89e4e3df.json` is **currently eligible**: `eligible_receipts('portland-or', digest, receipts_dir=shadow_receipts)` returns it, and it has no output defects (not empty, not vacuous).
- **Independent reproduction** (`portland_or_independent_reproduction_001.json`):
  - Ran from `git worktree add --detach C:/t/pdxrw a8fa126d` as a separate detached process, started **after** the main seal exited, with work dir `C:/t/pdx2`.
  - Result: same package id and digest, FAST 15/15, same Rule J bundle.
  - Data: 17 files compared, 0 differences. Site: 1,944 files compared, 0 differences (CRLF-normalised). **BYTE IDENTICAL = YES.**
  - The worktree was removed afterwards.
- Runs were sequential on this ~16 GB machine. There was no memory event.

## 11. Isolation (Phase 36)

`git diff --name-only 0e2e8bb8 HEAD` lists 85 paths, plus this report and the reproduction record. Every path is Portland-owned:
- `portland_or_*` modules and reports;
- the `portland-or` census, proposed market and staging tree;
- `discovery/config/portland_or.json`.

Changes made: none outside Portland's own files.

| Category | Changes |
|---|---|
| Cross-market source | 0 |
| Shared factory code | 0 |
| Current live | 0 |
| Deployment state | 0 |

No broad regression was run. These are untouched: `identity_resolutions.json`, `launch_participation.json`, supersessions, the generated globals, and every other market's files.

## 12. Performance (Phase 37)

| | |
|---|---|
| Start | 2026-10-03T21:33:31Z |
| Zero to source ready (FAST receipt written) | 4 h 05 m 40 s (01:39:11Z) |
| Zero to coverage ready (actionability decided) | 4 h 06 m 11 s (01:39:42Z) |
| Active compute time | Not separately metered: the order ran continuously over 4 h 06 m wall clock |
| Provider / cooldown wait | 0 idle. The Marriott Akamai cooldowns (after seq 41 and seq 79; about 64 minutes from seq 79 to the pdxac read at seq 145) overlapped with Hilton, ESA, Motel 6, Best Western, Hyatt and Choice reads |
| Firecrawl credits used | 90 (426 → 336) |
| Places requests | 77 (inside the free allowance) |
| New paid spend / provider cost | USD 0 / USD 0 |
| Founder intervention | none |

Cleanup:
- No order-created watcher, server or child process remains.
- The two detached seal processes exited on their own, and the reproduction worktree was removed.
- Work dirs `C:/t/pdx0`, `C:/t/pdx1` and `C:/t/pdx2` are scratch output outside the repo.

## 13. Issues for the operator

1. **Affiliate template sites.** Two rows (Cameo Motel and Portland INN) had been staged verified no-pets from templated booking-affiliate sites that Places names as the hotels' websites. The browser exposed this before the seal, and both rows are held. The pattern is likely in earlier markets too: any no-pets or pet-friendly record sourced from a `.site`, `.us`, `.xyz` or `.top` hotel-name domain deserves a look (memory note `ptf-affiliate-template-sites-are-not-first-party`).
2. **Shared premises: Hyatt House Portland Airport and The Mindaro** (11707 NE Airport Way). Both are live Hyatt hotels, and each was read on its own page. A `same_campus_distinct_entity` ruling in the shared `identity_resolutions.json` would publish both. The registration order should carry it.
3. **Probably closed or rebranded:**
   - Econo Lodge Portland Downtown: Choice route 404; absent from Choice's directory.
   - Inn at Marquam Hill: Places says permanently closed.
   - Hyatt Place Portland – Pearl District: not on Hyatt's search.
   - Twelve Wyndham routes retired.

   All are held; none is published. A registration order may confirm each closure first-party.
4. **The Paramount Hotel.** Its FAQ states "Pets of any type or size are not allowed in the hotel." The market-local reader treats "not allowed in the …" as an area rule, so the row is held rather than published verified no-pets. Publishing it would need a shared-reader refinement.

## FINAL ANSWERS

1. START TIMESTAMP = 2026-10-03T21:33:31Z
2. ZERO_TO_SOURCE_READY = 4 h 05 m 40 s (FAST receipt 2026-10-04T01:39:11Z)
3. ZERO_TO_COVERAGE_READY = 4 h 06 m 11 s (coverage decided 2026-10-04T01:39:42Z)
4. CURRENT LIVE DEPLOYMENT = 6ac169ef7c75c383eb79f824 (seattle-wa; source f0003e78, built_from 438348c7, bundle cfaad64a)
5. CURRENT LIVE MARKETS = 40 (3,669 profiles / 4,044 release-index / 4,117 served)
6. AUTOMATIC BASE DERIVES = YES (base 0e2e8bb8)
7. TOTAL DISCOVERED = 1,644 raw observations (9 productive lanes)
8. NORMALIZED IDENTITIES = 933 graph nodes
9. QUALIFYING CENSUS = 272
10. PET-FRIENDLY = 150
11. VERIFIED NO-PETS = 47
12. RESOLVED = 197
13. UNRESOLVED = 75
14. RESOLUTION RATE = 72.4 %
15. ACTIONABLE UNRESOLVED = 0
16. HOLDS BY CLASS = SOURCE_SILENT 28, ROUTING 18, EVIDENCE 17, ACCESS_BLOCKED 8, IDENTITY_MISMATCH 4 (NEGATION 0, BROWSER_CAPTURE 0)
17. EXCLUSIONS BY CLASS = vacation rental 48, timeshare 3, non-hotel 95, military-restricted 0, outside 325, duplicate 1, same-campus 2, name-only residue 149, identity-review residue 38, closed 0
18. PREOPENING IDENTITIES = 0
19. PREOPENING PUBLISHED = 0
20. TIMESHARE / VACATION-OWNERSHIP IDENTITIES = 3 (WorldMark Portland – Waterfront Park in-market; WorldMark Gleneden and WorldMark Seaside outside)
21. TIMESHARE / VACATION-OWNERSHIP PUBLISHED = 0
22. VANCOUVER WA CLASSIFICATION = CORRIDOR (corridor vancouver-wa, 11 ZIPs; 34 admitted rows, all state WA; 21 PF / 5 NP)
23. PUBLISHING CORRIDORS = 11 of 21 (downtown-portland, pdx-airport, vancouver-wa, hillsboro, beaverton, northeast-north-portland, pearl-old-town-northwest, lloyd-convention-center, tigard, lake-oswego, tualatin-wilsonville)
24. COMPETITOR RAW / NORMALIZED / MATCHED / TRUE MISSING = 473 / 327 / 118 / 28 (21 Places-verified and admitted, 7 already in census)
25. MATERIAL IDENTITY GAP = NO
26. MATERIAL POLICY GAP = NO
27. FIRECRAWL ATTEMPTED / SUCCESS = BringFido 31 credits; route discovery 18 pages / 9 served (Choice refused at 0); IHG pages 22 / 22 with own address; residual 42 / 28 credited, 0 publication-grade
28. GOOGLE PLACES REQUESTS = 77 (49 Enterprise + 28 PRO, free monthly allowance)
29. MARRIOTT CENSUS = 46
30. MARRIOTT ATTEMPTED = 47
31. MARRIOTT READ SUCCESS = 45 (2 Akamai denials, both rows read on paced retries)
32. MARRIOTT ACTIONABLE REMAINING = 0
33. OTHER BROWSER ATTEMPTED / SUCCESS = 163 / 119
34. DUAL-BRAND / SHARED-CAMPUS HOLDS = 2 rows (1 premises: Hyatt House Portland Airport + The Mindaro, 11707 NE Airport Way)
35. SINGLE-BASIS FEES PUBLISHED = 20
36. TIERED FEES WITHHELD = 33
37. UNSAFE / MULTI-AMOUNT FEES WITHHELD = 20 (basis not stated 13, stay-length condition 5, two bases 2)
38. MISLEADING SINGLE FEES = 0
39. PET-FRIENDLY WITH EXPLICIT REFUSAL = 0
40. QUESTION-ONLY PET-FRIENDLY = 0
41. EXISTING PROVIDER CREDITS USED = Firecrawl 90 credits (426 → 336); Google Places 77 requests inside the free monthly allowance
42. NEW PAID SPEND = 0 (USD 0)
43. PROVIDER COST = USD 0
44. RULE J NONEMPTY = PASS (908 files, 892 HTML, output present)
45. RULE K NONVACUOUS = PASS (BYTE_IDENTICAL)
46. FAST RECEIPT CURRENTLY ELIGIBLE = YES
47. SHADOW PACKAGE = pkg-portland-or-b6f95c2ae170f44b (SHADOW_UNTIL_REGISTERED)
48. PACKAGE REPRODUCIBLE = YES (in-process and independent; data 0 / site 0 differences)
49. PACKAGE DIGEST = sha256:b6f95c2ae170f44b64f120f054cf07ef8ee48734d7ec2c6ee541882790eace5c
50. FAST = 15/15 PASS, 0 UNKNOWN, 0 FAILED
51. TECHNICAL SOURCE READY = YES
52. COVERAGE READY = YES
53. CROSS-MARKET FILE CHANGES = 0
54. FACTORY CODE CHANGED = NO
55. BROAD REGRESSION RUNS = 0
56. FINAL PRODUCTION CANDIDATE CREATED = NO
57. FOUNDER AUTHORIZATION CREATED = NO
58. PORTLAND DEPLOYED = NO
59. origin == HEAD = YES (verified after push)
60. tree clean = YES (verified after push)

PORTLAND SOURCE READY = YES
PORTLAND COVERAGE READY = YES
ACTIONABLE UNRESOLVED = 0
PET-FRIENDLY RECORDS WITH EXPLICIT REFUSAL = 0
QUESTION-ONLY PET-FRIENDLY RECORDS = 0
PREOPENING PROFILES PUBLISHED = 0
TIMESHARE / VACATION-OWNERSHIP PROFILES PUBLISHED = 0
MISLEADING SINGLE FEES = 0
RULE J NONEMPTY = PASS
RULE K NONVACUOUS = PASS
FAST = 15/15 PASS
FACTORY CODE CHANGED = NO
BROAD REGRESSION RUNS = 0
PORTLAND FINAL CANDIDATE = NO
PORTLAND DEPLOYED = NO
WAITING FOR RELEASE QUEUE = YES
