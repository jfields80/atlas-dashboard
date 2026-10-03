# PTF-SEATTLE-WA-HARDENED-SOURCE-READY-001 — FINAL

Market `seattle-wa` — Seattle / Bellevue / Puget Sound, Washington.
Worktree `C:\Atlas-Seattle-WA-Hardened-V1`, branch `worker/ptf-seattle-wa-market-001`.
Built from zero on the San Antonio-live lineage (base `5bd54304`, live lineage `60683902`, built_from `be83dab2`).
Report written 2026-10-03 (UTC). Nothing registered, authorized or deployed.

## 1. Outcome

| | |
|---|---|
| Qualifying census | **303** |
| Pet-friendly (published in the shadow package) | **139** |
| Verified no-pets | **61** |
| Resolved / unresolved | 200 / 103 (66.0 %) |
| Actionable unresolved | **0** (98 router-exhausted, 4 dual-brand founder holds held safely, 1 preopening) |
| Shadow package | `pkg-seattle-wa-d39a3919f10cf45b`, `SHADOW_UNTIL_REGISTERED` |
| FAST | **15/15 PASS**, 0 UNKNOWN, 0 FAILED |
| Rule J | 853 files / 837 HTML, bundle `1872172c…`, output present |
| Rule K | BYTE_IDENTICAL (non-vacuous: two cold builds of the 853-file bundle) |
| Receipt | `pkg-seattle-wa-d39a3919f10cf45b-d315b3cad2dba55d.json` — `eligible_receipts` returns it, `receipt_output_defects` = [] |
| Independent reproduction | separate process, detached worktree at `3b54e157`: same package id + digest, FAST 15/15, data 0 / site 0 differences |
| Technical source ready | **YES** |
| Coverage ready | **YES** |

## 2. Lineage and current live (Phase 1)

`release_index live-source --fetch --verify-host` → `seattle_wa_current_live_001.json`:
deploy `6ac064cd6a4261e60054a2f3` (record `ptf-deploy-san-antonio-005-…`), source `606839025c4c…`,
built_from `be83dab2…`, bundle `50b1ce95d80386ed…`, sitemap `e2a6b1c94dff6f91…`, host verified.
39 markets / 3,530 profiles / 3,894 release-index routes / 3,966 served routes.
Automatic base derivation for the next market: `derive_registration_base('seattle-wa', 60683902…)` → `5bd54304` (**YES**).
The shadow package's `parent_live_state` names this deploy; FAST rule N will fail it by design once any later release
is live, and the registration order re-seals the same committed inputs against that parent.

## 3. Geography (Phase 2)

22 corridors over 73 ZIPs (`seattle_wa_geography_001`):

- **CORE (12)**: downtown-waterfront, seattle-center-slu, capitol-hill-central, university-district, ballard-fremont,
  north-seattle, south-west-seattle, sea-airport (SeaTac/Tukwila/Burien-airport ZIPs), bellevue, redmond, kirkland, renton.
- **STRONG CORRIDOR (5)**: bothell-kenmore, lynnwood, issaquah, kent, federal-way.
- **FRINGE (5)**: mercer-island, shoreline-lake-forest-park, burien-white-center, woodinville, edmonds-mountlake-terrace.
- **OUTSIDE / FUTURE STANDALONE**: tacoma-wa, olympia-wa, everett-wa, bellingham-wa, kitsap-wa (future markets);
  Auburn, Sammamish, Snoqualmie/North Bend, Enumclaw, Vashon, Bainbridge, Duvall are outside.
- Boundary audit (`county_and_border_boundary`): Tacoma 65 discovered / 0 admitted, Olympia 23/0, Everett 29/0,
  Bellingham 68/0, Kitsap/Bremerton 60/0, other Puget Sound 24/0, out-of-state 2/0.
- Airport / Eastside identity safety: postal-code admission only; brand routes whose own city segment is a refused
  city are refused (3); the I-5/405/90, SR-99 (International Blvd / Pacific Hwy S) and state-route street folds merge
  spelling variants without merging different premises.
- Non-public lodging: Navy Lodge (×2) and the JBLM-named Comfort Inn are MILITARY_RESTRICTED (all three are also outside
  the market by ZIP; see §12 on the JBLM label).

## 4. Census (Phases 4–9)

2,190 raw observations in 11 lanes → 1,295 graph nodes → 303 qualifying identities.

| Lane | Observations |
|---|---|
| City of Seattle business-licence register (data.seattle.gov `wnbq-64tb`, NAICS 721110 + lodging-named 7211x/7213x) | 242 |
| OSM (Geofabrik washington-261002 extract) | 811 |
| Owned brand inventory | 55 |
| Brand city pages / sitemaps | 54 + 65 |
| Destination organisations (Visit Seattle 152 lodging members, Visit Bellevue 55, Seattle Southside) | 178 |
| Competitor leads (BringFido, identity only) | 475 |
| Places identity verification | 14 |
| Property pages (static, Firecrawl, attended browser) | 296 |

Exclusions (non-admitted): vacation rental 84, timeshare / vacation ownership 2 (WorldMark Camlin, WorldMark Deer
Harbor), non-hotel 175 (apartments, senior living, hostels, member club, patient housing, offices, housing
nonprofits), military-restricted 3, outside 380, duplicate listing 4, same-campus distinct entity 1, name-only graph
residue 247, identity-review residue 99, closed 0.

Identity rules: a name proposes, never decides; the register's corporate phone is metadata, not a merge key (it had
fused four Silver Cloud hotels); OSM's multi-valued phone tag takes its first value (the fused value broke FAST J —
§10); policy subpages bind only when the page's own house number agrees; a page with no ZIP binds only on its own
house number + street words + municipality to exactly one row.

Competitor challenge (BringFido, 20 cities, 654 raw → 475 unique, never policy authority): 155 matched, 7 TRUE_MISSING,
all explained — Hotel Nexus is in the census under its own name; Executive Residency is in Everett (outside);
FairBridge Inn Express (13050 48th Ave S) and Motel 6 Suites Kent (22520 83rd Ave S) are rebrands sitting at census
rows (Days Inn Seattle South/Tukwila, held for review; ESA Seattle Kent); Green Lake Firefly Lodge is a four-bedroom
house; Pensione Nichols is a B&B under the non-lodging rule; Gold Crest Suites has no lodging result in Places.
**MATERIAL IDENTITY GAP = NO.**

## 5. Acquisition (Phases 11–17)

- **Router**: committed router only; no Seattle bypass.
- **Static plain client**: 129 targets, 125 requests (12 valid; 47 access-denied; the rest mismatch/error/unhydrated).
- **Wyndham property service**: 39 selected, 21 read, 15 retired routes.
- **Independents' own sites**: 76 targets bound 48 (159 free requests); Places-discovered sites 31 targets bound 24.
- **Google Places**: 169 requests (149 Enterprise route discovery + 20 PRO gap verification) inside the free monthly
  allowance renewed 2026-10-01 — existing capacity, USD 0.
- **Firecrawl** (existing credits only, 503 → 426 = 77 credits): BringFido 42 pages; brand route discovery 19 pages
  (10 credited, Choice refused at 0 credits) → 62 routes; IHG brand pages 16/16 with own address; residual pass 10
  attempts / 9 credits (3 publication-grade, none states pet acceptance: two Sonesta Select pages welcome service
  animals only, WoodSpring Redmond states limits but not acceptance).
- **Attended browser** (claude-in-chrome; navigate + find/read_page only; no Akamai bypass, no JS exfiltration,
  no relay, paced): 193 attempts, 160 bound reads, 3 challenge denials (2 Hilton, 1 Marriott), 3 unbound (two
  out-of-market Best Western pages and one dead Warwick route). Hilton's Akamai block that began at seq 97–98 cleared on
  a paced retry about an hour later (seq 180–182); every row it held was read.
  - **Marriott**: census 50, 56 attempts, 55 reads, 1 denial; 35 PF / 12 NP / 3 held (Aloft + Element Redmond dual-brand,
    Courtyard Northgate self-contradictory). **Marriott actionable = 0.**
  - Other families: 137 attempts, 105 reads (Hilton 43, Choice 17, Hyatt 9, ESA 8, Best Western 6, IHG 3,
    Red Roof 2, Wyndham 1, independents 16), plus 14 identity-bound silent pages and 5 chip-only pages.
- Every browser read is in `raw_captures/browser_reads_001.jsonl` (seq 1–193) with the recorder's real-clock stamp;
  the last first-party capture is seq 193 at 2026-10-03T07:11:54Z. The package's `CAPTURED_AT` is that stamp and
  `SEALED_AT` is 2026-10-03T07:15:00Z, set when the clock read 07:15:32Z. No timestamp is ahead of the clock.

## 6. Policy safety (Phases 16–19)

Publication safety audit — every count zero: pet-friendly with explicit refusal 0, question-only pet-friendly 0,
service-animal-only pet-friendly 0, preopening/closed published 0, timeshare published 0, military published 0,
misleading single fee 0, no-pets without a refusal sentence 0.

Market-local reader additions (the shared reader is untouched):
- refusal shapes "pet-free hotel/environment/property/inn" and "do not accept pets";
- **service-animal-only beside acceptance** is held, never published (Courtyard Northgate: "Pets Welcome | Service Animals
  with credentials only");
- shared-reader disagreements are held (Edgewater, Olive 8, Hyatt Regency Lake Washington, Ballard Inn, Coast Gateway,
  Coast Seattle Downtown, Baroness, Inn at Virginia Mason, Gaslight Inn, La Hacienda, State Hotel, Larkspur Renton);
  negation conflicts 8, none published.

Preopening: Hotel Interurban Seattle Tukwila (Tapestry by Hilton) — "We're opening in November 2026, but aren't
accepting reservations yet." Held until opening; never verified-no-pets.

## 7. Fees (Phase 19)

25 single-basis fees published (each states its own basis; daily → per_day, nightly → per_night, never per stay).
39 tiered fees withheld. 15 unsafe single fees withheld: basis not stated 8, two bases 2, fee stated as waived 2
(Residence Inn Seattle East/Redmond and a second Redmond hotel: "waived … covered by the Redmond Tourism Promotion
Area"), additional pet only 1 (Red Roof Seattle Airport: "First pet stays free. Second pet $15 per night."), amount
range 1, stay-length condition 1. **Misleading single fees = 0.**

## 8. Holds and actionability (Phases 20–24)

| Disposition | Rows | Actionable |
|---|---|---|
| ROUTING_HOLD (no first-party web presence 30, dead route 5, social/OTA only 2) | 37 | 0 |
| SOURCE_SILENT | 33 | 0 |
| EVIDENCE_HOLD (incl. 1 preopening) | 19 | 0 |
| IDENTITY_MISMATCH_HOLD (4 dual-brand + 4 page never confirmed premises) | 8 | 0 |
| ACCESS_BLOCKED | 6 | 0 |

Dual-brand buildings (held; publishing them needs a `same_campus_distinct_entity` row in the shared
`identity_resolutions.json`, which this order did not write or sign): Aloft + Element Seattle Redmond (15220 NE Shen
St), Holiday Inn Express + Staybridge Suites Federal Way (32124 25th Ave S). Under the order's own rule these are safe
holds and do not gate coverage.

Publishing corridors (≥ 5 pet-friendly profiles): downtown-waterfront 25, sea-airport 26, bellevue 19,
seattle-center-slu 11, bothell-kenmore 9, lynnwood 8, kent 6, redmond 5, renton 5, federal-way 5 — **10 of 22**.
Below threshold: north-seattle 4, kirkland 4, issaquah 4, woodinville 3, university-district 2, ballard-fremont 1,
south-west-seattle 1, edmonds-mountlake-terrace 1, capitol-hill-central 0; mercer-island, shoreline-lake-forest-park,
burien-white-center have no census row.

**MATERIAL POLICY GAP = NO** — every unresolved row carries a terminal, explained reason.

## 9. Coverage decision (Phase 26)

All eight conditions hold (`seattle_wa_actionability_001.json`): actionable 0, no material identity gap, no
unexplained policy gap, authorized lanes exhausted, Marriott queue resolved or exhausted, browser brands processed,
publication set safe, package deterministic and FAST clean. **COVERAGE READY = YES.**

## 10. Shadow package, FAST, receipt, reproduction (Phases 27–30)

- Inputs committed at `23b40258` and staged at `c31381ce`. The first seal (`c31381ce`, pkg `5b2ee4fc…`) failed FAST
  J: the build refused `tel:1206901926818775152176`, Cedarbrook Lodge's two OSM phone numbers fused into one link
  (five admitted rows carried a multi-valued phone). Fixed in the census (`d8f141b0`), re-staged (`3b54e157`),
  re-sealed. The failed attempt's uncommitted package, receipt and report were deleted, not committed.
- Final seal from `3b54e157` (detached `Start-Process`, work dir `C:/t/sea1`): `pkg-seattle-wa-d39a3919f10cf45b`,
  digest `sha256:d39a3919f10cf45bb1d5728fbb6255c0fefb6e17b819c0e4bc9b4376d749061f`, reproducible in-process, FAST
  15/15, first-party gate 200/200 eligible, Rule J 853 files / 837 HTML, Rule K BYTE_IDENTICAL. Committed at `0347007e`.
- Receipt `…-d315b3cad2dba55d.json` is **currently eligible**: `eligible_receipts('seattle-wa', digest)` returns it, and it
  has no output defects (not empty, not vacuous).
- Independent reproduction (`seattle_wa_independent_reproduction_001.json`): `git worktree add --detach C:/t/searw
  3b54e157`, a separate detached process run **after** the main seal exited (work dir `C:/t/sea2`). Same package
  id and digest, FAST 15/15, same Rule J bundle; data 17 files / 0 differences, site 1,832 files / 0 differences
  (CRLF-normalised). **BYTE IDENTICAL = YES.** The worktree was removed afterwards.
- Runs were sequential on this ~16 GB machine. The low-memory reaper killed one of my idle background WAIT shells
  during the first seal; the detached seal process itself was unaffected and finished. Nothing was restarted on the
  reaper's account.

## 11. Isolation (Phase 31)

`git diff --name-only 5bd54304 HEAD`: 85 paths (plus this report and the reproduction record), every one Seattle-owned
(`seattle_wa_*` modules and reports, `seattle-wa` shard/census/staging, `discovery/config/seattle_wa.json`).
Cross-market source changes 0; shared factory code changes 0; current live changes 0; deployment state changes 0.
No broad regression was run. `identity_resolutions.json`, `launch_participation.json`, supersessions, the generated
globals and every other market's files are untouched.

## 12. Issues for the operator

1. **San Antonio worktree has one stray uncommitted line (needs your revert).** Early in this order I ran the stale
   `C:\t\mr.py` (the San Antonio session's recorder helper). It appended a malformed Seattle read (seq 214,
   captured_at 2026-10-03T04:17:55Z, empty fields) to
   `C:\Atlas-San-Antonio-TX-Hardened-V1\atlas-dashboard\launch_packages\pettripfinder\markets\staging\san-antonio-tx\raw_captures\browser_reads_001.jsonl`.
   It is uncommitted (`git diff --stat`: 1 insertion). My `git checkout --` revert was blocked by the permission
   classifier, so I left it. To fix: `git -C C:\Atlas-San-Antonio-TX-Hardened-V1 checkout -- atlas-dashboard/launch_packages/pettripfinder/markets/staging/san-antonio-tx/raw_captures/browser_reads_001.jsonl`.
   All later Seattle reads used a session-scratchpad helper. Memory note: `ptf-shared-c-t-scripts-hazard`.
2. **JBLM label.** "Comfort Inn & Suites Lakewood by JBLM" carries a MILITARY_RESTRICTED reason because its name contains
   "jblm". It is a public hotel, and it is excluded correctly anyway (Lakewood is outside the market by ZIP). This has
   no effect on publication. Correcting the label would change the sealed census, so it is left for the
   registration order.
3. **Competitor report prose.** The cloned competitor-challenge method note still named Texas towns. The module text
   was corrected, and the committed report's `method_note` was replaced with the corrected sentence, without
   refetching BringFido. No count changed. The census report's equivalent sentence was regenerated by the module.
4. **Rebrands seen but not published**: FairBridge Inn Express at the Days Inn Tukwila row (held for review), and Motel
   6 Suites at the ESA Seattle Kent row (unresolved). The registration order should re-read both.

## FINAL ANSWERS

1. CURRENT LIVE DEPLOYMENT = 6ac064cd6a4261e60054a2f3 (san-antonio-tx; source 60683902, built_from be83dab2, bundle 50b1ce95)
2. CURRENT LIVE MARKETS = 39 (3,530 profiles / 3,894 release-index / 3,966 served)
3. AUTOMATIC BASE DERIVES = YES (base 5bd54304)
4. TOTAL DISCOVERED = 2,190 raw observations (11 lanes)
5. NORMALIZED IDENTITIES = 1,295 graph nodes
6. QUALIFYING CENSUS = 303
7. PET-FRIENDLY = 139
8. VERIFIED NO-PETS = 61
9. RESOLVED = 200
10. UNRESOLVED = 103
11. RESOLUTION RATE = 66.0 %
12. ACTIONABLE UNRESOLVED = 0
13. HOLDS BY CLASS = ROUTING 37, SOURCE_SILENT 33, EVIDENCE 19, IDENTITY_MISMATCH 8, ACCESS_BLOCKED 6 (NEGATION 0, BROWSER_CAPTURE 0)
14. EXCLUSIONS BY CLASS = vacation rental 84, timeshare 2, non-hotel 175, military-restricted 3, outside 380, duplicate 4, same-campus 1, name-only residue 247, identity-review residue 99, closed 0
15. PREOPENING IDENTITIES = 1 (Hotel Interurban Seattle Tukwila)
16. PREOPENING PUBLISHED = 0
17. TIMESHARE/VACATION-OWNERSHIP PUBLISHED = 0
18. PUBLISHING CORRIDORS = 10 of 22 (downtown-waterfront, seattle-center-slu, sea-airport, bellevue, redmond, renton, bothell-kenmore, lynnwood, kent, federal-way)
19. COMPETITOR TRUE MISSING = 7, all explained (1 in census, 1 outside, 2 rebrands at census rows, 1 house, 1 B&B, 1 no lodging result)
20. MATERIAL IDENTITY GAP = NO
21. MATERIAL POLICY GAP = NO
22. FIRECRAWL ATTEMPTED / SUCCESS = 87 / 77 served (BringFido 42/42, route discovery 19/10, IHG pages 16/16, residual 10/9 with 3 publication-grade); 77 existing credits
23. MARRIOTT CENSUS = 50
24. MARRIOTT ATTEMPTED = 56
25. MARRIOTT READ SUCCESS = 55
26. MARRIOTT ACTIONABLE REMAINING = 0
27. OTHER BROWSER ATTEMPTED / SUCCESS = 137 / 105
28. DUAL-BRAND HOLDS = 4 rows (2 buildings: Aloft/Element Redmond, HIX/Staybridge Federal Way)
29. SINGLE-BASIS FEES PUBLISHED = 25
30. TIERED FEES WITHHELD = 39
31. UNSAFE FEES WITHHELD = 15
32. MISLEADING SINGLE FEES = 0
33. PET-FRIENDLY WITH EXPLICIT REFUSAL = 0
34. QUESTION-ONLY PET-FRIENDLY = 0
35. EXISTING PROVIDER CREDITS USED = Firecrawl 77 credits (503 → 426); Google Places 169 requests inside the free monthly allowance
36. NEW PAID SPEND = 0 (USD 0)
37. RULE J NONEMPTY = PASS (853 files, 837 HTML, output present)
38. RULE K NONVACUOUS = PASS (BYTE_IDENTICAL)
39. FAST RECEIPT CURRENTLY ELIGIBLE = YES
40. SHADOW PACKAGE = pkg-seattle-wa-d39a3919f10cf45b (SHADOW_UNTIL_REGISTERED)
41. PACKAGE REPRODUCIBLE = YES (in-process and independent; data 0 / site 0 differences)
42. PACKAGE DIGEST = sha256:d39a3919f10cf45bb1d5728fbb6255c0fefb6e17b819c0e4bc9b4376d749061f
43. FAST = 15/15 PASS, 0 UNKNOWN, 0 FAILED
44. TECHNICAL SOURCE READY = YES
45. COVERAGE READY = YES
46. CROSS-MARKET FILE CHANGES = 0
47. FACTORY CODE CHANGED = NO
48. BROAD REGRESSION RUNS = 0
49. FINAL PRODUCTION CANDIDATE CREATED = NO
50. FOUNDER AUTHORIZATION CREATED = NO
51. SEATTLE DEPLOYED = NO
52. origin == HEAD = YES (verified after push)
53. tree clean = YES (verified after push)

SEATTLE SOURCE READY = YES
SEATTLE COVERAGE READY = YES
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
SEATTLE FINAL CANDIDATE = NO
SEATTLE DEPLOYED = NO
WAITING FOR RELEASE QUEUE = YES
