# PTF-KANSAS-CITY-MO-HARDENED-SOURCE-READY-001 — FINAL

Market `kansas-city-mo` — Kansas City / Greater Kansas City, Missouri & Kansas.
Branch `worker/ptf-kansas-city-mo-market-001`, worktree `C:\Atlas-Kansas-City-MO-Hardened-V1`.
Built from zero on the Minneapolis-live lineage. **SHADOW_UNTIL_REGISTERED.** Nothing was registered, authorized or deployed.

## Outcome

| | |
|---|---|
| Shadow package | `pkg-kansas-city-mo-24718ac004c967b8` |
| Package digest | `sha256:24718ac004c967b89e57ccf6215a906465e8edaae97685be5cc6e7258e600402` |
| Sealed from | `39b3ec70` (SEALED_AT 2026-10-05T23:24:00Z, after the last capture, seq 155 at 22:56:48Z) |
| FAST | 15/15 PASS, `FAST_DATA_ONLY_RELEASE_ELIGIBLE = YES` |
| Rule J | non-empty: bundle `f454f0bd…`, 976 files / 960 HTML, 0 output defects |
| Rule K | non-vacuous: BYTE_IDENTICAL, 4 cold builds, 0 reuse hits |
| Receipt | `pkg-kansas-city-mo-24718ac004c967b8-bcbd3d220f61eaa8`, currently eligible (`eligible_receipts`, receipts_dir = shadow_receipts) |
| Independent reproduction | detached worktree at `39b3ec70`, separate process, work dir `C:/t/kc2`: same package id and digest, same bundle, package file byte-identical, independent FAST 15/15 |
| Census | 290 qualifying identities (MO 189, KS 101) |
| Published | 161 pet-friendly, 60 verified no-pets (221 resolved, 76.2 %) |
| Held | 69, **actionable 0** |
| Readiness | TECHNICAL SOURCE READY = YES; COVERAGE READY = YES |

## Lineage

- Current live: Minneapolis deploy `6ac3bfda7b585d009f007620` (42 markets / 3,975 profiles / 4,377 release-index / 4,452 served), live source `d5762303`, built_from `239c2836`, bundle `3d7c53a1…`, host verified.
- Automatic base derives YES → `e74dee3b` (docs-only child of `d5762303`, same live truth).
- Start 2026-10-05T19:29:42Z. Source-ready (FAST-clean package committed) 23:33:27Z — **4 h 04 min**. Coverage-ready verified 23:40Z — **4 h 11 min**.

## Geography

25 corridors (15 MO, 10 KS; 14 CORE, 6 CORRIDOR, 5 FRINGE; 118 ZIPs), 13 publishing (≥ 5 pet-friendly profiles).
State is decided by the property's own ZIP (MO 630–658, KS 660–679); a row whose stated state disagrees with its ZIP is held (`STATE_POSTAL_CONFLICT`), never re-labelled — 0 such rows.

Two-state accounting: KS hotels mislabeled MO = **0**; MO hotels mislabeled KS = **0**; "Kansas City" rows: 123 in Missouri, 20 in Kansas.

Boundary audit (discovered / admitted): Lawrence 23/0, Topeka 28/0, St. Joseph 39/0, Columbia 73/0, Manhattan 22/0, Lake of the Ozarks 94/0, Leavenworth–Lansing 12/0, outer north metro 20/0, outer east/south metro 23/0, outer Johnson/Wyandotte/Miami KS 10/0, St. Louis (live market) 0/0, other greater MO/KS/out of state 735/0. Rows admitted from a refused ZIP: 0.

Name traps decided by ZIP: Sonesta Select "South Overland Park" is Kansas City MO 64131; ESA "Shawnee Mission" is Merriam KS 66202; Drury "Independence" is Blue Springs MO 64015; Element "Overland Park" is Leawood 66224; ESA "Tiffany Springs" route says `/ks/` but the page states MO 64153.

## Census and lanes

3,047 raw observations → 1,847 graph nodes → 290 identities.
Lanes: Missouri Licensed Lodging register (1,013 leads; Kansas publishes no register — KDA 403), OSM (MO + KS extracts, 1,106 elements), brand inventories (181 leads), Visit KC / Visit KCK / Visit Overland Park rosters (143), BringFido competitor leads (310), Places gap verification, first-party property pages (275).

Exclusions: OUTSIDE 1,199; non-hotel 72; vacation rental 53; timeshare 1; military-restricted 2; name-only residue 129; identity-review residue 99; same-campus distinct 2.

## Policy acquisition

- **Attended browser** (claude-in-chrome; no JS exfiltration, no relay, no bypass): 155 attempts, 135 reads. Marriott 57 attempts / 57 reads (56 routes + one re-read for the page's own h1), **0 denials**. Hilton 46 / 45 (a "Something went wrong" block 21:20Z–22:25Z was waited out). Other families 98 / 78.
- ESA Airport – Tiffany Springs served a **DataDome CAPTCHA** twice (seq 113, 149) — recorded, never solved or bypassed.
- One OSM-listed legacy Crossland domain rendered a **scareware page**; nothing on it was clicked, the tab was navigated away, and the route is recorded as a failed navigation.
- **Firecrawl**: 111 existing plan credits (271 → 160): competitor pages 26, Choice/IHG city-page discovery 18, brand property pages 67. The Firecrawl rung's own 19-row cohort was planned and **not bought** (every route already read — pay once per page).
- **Google Places**: 107 requests (70 Enterprise, 37 Pro), inside the free monthly allowance.
- Static plain client 94 requests; Wyndham property service 30 read / 18 retired routes; independents' policy pages 59 requests.
- New paid spend: **none**. Provider cost: $0 USD.

## Held rows (69) — all non-actionable

| Disposition | n | Class |
|---|---|---|
| SOURCE_SILENT | 25 | pages read, bound, no operative policy (incl. 4 Motel 6/Studio 6 chip-only; 5 Holiday Inn pages silent, one spot-checked in the browser: amenity chip only) |
| ROUTING_HOLD | 23 | no first-party web presence, retired/closed brand routes (La Quinta OP, Microtel KCI, Sonesta Tiffany Springs — Places CLOSED_PERMANENTLY), non-first-party sites |
| EVIDENCE_HOLD | 11 | 4 preopening (Park Hotel on the Plaza, Home2 Speedway, Spark KC Airport, DoubleTree KCI); 7 quotes the shared reader does not read as acceptance/refusal |
| IDENTITY_MISMATCH_HOLD | 8 | 6 dual-brand (REQUIRES_FOUNDER), 2 router-exhausted |
| ACCESS_BLOCKED | 2 | DataDome (ESA Tiffany Springs); Adam's Mark (site does not resolve) |

**Founder rulings needed at registration** (never self-signed into `identity_resolutions.json`):
- Aloft + Element North Kansas City, 1875 Diamond Pkwy 64116;
- AC Hotel + Residence Inn Lenexa City Center, 8710 Penrose Ln 66219;
- Courtyard + Residence Inn KC Downtown/Convention Center, 1535 Baltimore 64108;
- rebrand holds: Hilton Garden Inn Overland Park (Wyndham Garden route retired), Sleep Inn Olathe (Days Inn evidence at the same address).

## Publication safety (all zero)

PF with explicit refusal 0; question-only PF 0; service-animal-only acceptance 0; preopening/closed published 0; timeshare published 0; military published 0; misleading single fees 0; no-pets quote without refusal 0.
Fees: 25 single-basis published; 37 tiered withheld; 17 unsafe withheld (16 basis not stated, 1 stay-length). Drury's "daily fee" rows publish no fee (the known `daily`→per_stay defect is not exposed).

## Market-local fixes made this order (no shared factory code changed)

- Policy-reads state regex: `Kansas City` is never read as state KS.
- Brand-page reads: the fetch path now applies the page's own h1 name (28 Choice pages re-parsed from persisted documents, 0 credits).
- Browser lane: numbered streets bind ("500 E 105 Street" = "105th"); `Terr.` is a street type.
- Clean authority: an area restriction ("not allowed in food or beverage areas", "Jacuzzi Room") is not a refusal (Hilton KC Airport, Comfort Suites Liberty); a brand page with only non-policy "pet" text is silent, not unattempted.
- Census: a Places gap row folds into the page-read building (Hotel Lotus Merriam: page 66203 vs Places 66202, same corridor); Crowne Plaza map row (1311 Wyandotte) superseded by IHG's own page (1301); register-only "Origin Hotel" held as a second-street duplicate.
- Non-hotel rulings: Farkas Home and Bear Paws Bed and Rest (private home rentals).
- Minneapolis text purged from staged outputs (the staged package's `market` field had read "Minneapolis / St. Paul / Twin Cities, Minnesota"); boundary audit rewritten for Kansas City.

## Isolation and operations

- Only `kansas-city-mo` / `kansas_city_mo` paths committed; no shared document, generated global or other market touched; no `build_market_authorities --write`.
- Seal, FAST and reproduction ran detached, strictly sequentially, never two builds at once. Claude Code's memory reaper stopped one of my *watcher* shells during seal #1 (~3 GB free); the detached seal itself continued and completed normally — nothing was restarted.
- The reproduction worktree `C:/t/kcrw` and work dirs `C:/t/kc1`, `C:/t/kc2` were removed.
- Owned-data was re-run at the end (key rename); its prior-provider-call count (2,000) now includes this order's own Firecrawl calls (it read 1,888 at the start).

## Machine-readable accountings

`launch_packages/pettripfinder/markets/reports/kansas_city_mo_{source_ready,brand,corridor,provider,source,boundary}_accounting_001.json`, `kansas_city_mo_actionability_001.json`, `kansas_city_mo_fee_withholding_001.json`, `kansas_city_mo_shadow_package_001.json`; final partition `markets/staging/kansas-city-mo/launch_package/kansas_city_mo_final_partition_001.json`.

## Next

Registration waits for the release queue. When Kansas City reaches the front, the registration order re-seals the same committed inputs against the then-current parent (FAST rule N fails this package by design once a later release is live) and carries the founder rulings above.
