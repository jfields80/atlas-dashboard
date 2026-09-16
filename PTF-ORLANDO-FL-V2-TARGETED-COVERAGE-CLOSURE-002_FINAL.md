# PTF-ORLANDO-FL-V2-TARGETED-COVERAGE-CLOSURE-002 — FINAL

- **Market:** `orlando-fl`
- **Branch:** `worker/ptf-orlando-fl-market-002`
- **Baseline:** source-ready head `ad2423b5`, package `pkg-orlando-fl-42df401808bbd169`
- **Timing:** started 2026-09-15T17:01 ET
- **Status:** SHADOW_UNTIL_REGISTERED. Nothing was registered, participated, authorized or deployed.

This was one targeted pass over three cohorts only: BringFido-matched unresolved hotels, the V1 pet-friendly regression set, and corridor-critical hotels. Independents were worked only inside those cohorts. BringFido and V1 were used as leads only. Every new fact comes from a current first-party page, is copied verbatim, is bound to the census identity by street + postal code (or phone / structured address), and passes the shared first-party gate with the market-local negation guard in front of it.

Machine-readable document: `atlas-dashboard/launch_packages/pettripfinder/markets/reports/orlando_fl_v2_targeted_closure_002.json`. It contains the BringFido closure (43 identities / 44 leads), the 23-row V1 reconciliation, targeted Hilton/Marriott/Hyatt accounting, corridor-critical accounting, per-target router tracks and revised root causes.

## 1. Coverage recomputed

| | Before (ad2423b5) | After |
|---|---:|---:|
| TOTAL CENSUS | 582 | **583** |
| VERIFIED PET-FRIENDLY | 168 | **201** |
| VERIFIED NO-PETS | 121 | **122** |
| RESOLVED | 289 | **323** |
| UNRESOLVED | 293 | **260** |
| RESOLUTION RATE | 49.66 % | **55.40 %** |
| BRINGFIDO-MATCHED STILL UNRESOLVED | 43 | **16** |
| V1 PET-FRIENDLY CHALLENGE STILL UNRESOLVED | 23 | **8** |
| ACCESS_BLOCKED | 27 | **18** |
| BROWSER_NEEDED | 91 | **73** |
| ROUTING_HOLDS | 140 | **138** |
| EVIDENCE_HOLDS | 8 | **7** |
| NEGATION_HOLDS | 3 | **3** |
| OTHER (identity 9, source-silent 9, policy-not-found 2, mixed resort 1) | 24 | **21** |

**Census 582 → 583.** This is an identity correction, not growth:
- The TownePlace Suites Orlando **Airport** Marriott route (`mcota`) had been bound by name to TownePlace Suites Orlando **Downtown** (51 Columbia St).
- The Airport page's own address (5530 Butler National Dr, 32812) admitted the DBPR-licensed Airport building, which was previously held as IDENTITY_REVIEW. The Downtown building now carries its own route (`mcoto`).
- The other key changes are renames to the name the hotel's own page states; the street identity is the same.

## 2. Priority 1 — BringFido matched unresolved

| Measure | Value |
|---|---:|
| BRINGFIDO UNRESOLVED START | 44 leads → 43 census identities (two leads name one building) |
| BRINGFIDO RESOLVED THIS PASS | 27 |
| BRINGFIDO PET-FRIENDLY FOUND | 27 |
| BRINGFIDO VERIFIED NO-PETS FOUND | 0 |
| BRINGFIDO STILL UNRESOLVED | 16 |

**Resolved (27, all pet-friendly on current first-party pages):**

| Lane | Hotels |
|---|---|
| Hilton browser | Hampton SeaWorld; Hampton East UCF; HGI Airport; HGI SeaWorld; HGI East UCF; HGI I-Drive North; Home2 Airport; Home2 Near Universal; Home2 South Park; Homewood Theme Parks; Spark Universal Blvd; Tru Convention Center |
| Marriott browser | Hotel Landy; Renaissance SeaWorld; Residence Inn SeaWorld; Residence Inn Downtown; TownePlace SeaWorld; TownePlace East UCF; TownePlace Near Universal |
| Hyatt browser | Hyatt Place LBV (full pet module re-read); Hyatt House Orlando Airport |
| Static | Drury Inn & Suites Near Universal; Sonesta ES Suites LBV; Lake Nona Wave; Westgate Blue Tree; The Delaney |
| Operator page | Hard Rock Hotel (Universal operator page policy + Loews property page address) |

**Still unresolved (16), each with its exact blocker:**

| Hotel | Disposition | Blocker |
|---|---|---|
| DoubleTree Entrance to Universal; DoubleTree Theme Park; Hampton Closest to Universal; Homewood LBV | ACCESS_BLOCKED | hilton.com serves "Something went wrong … Reference No. …" for these property pages in every pass (browser); plain client 403; Firecrawl known wall |
| TownePlace Suites Orlando Downtown (`mcoto`) | ACCESS_BLOCKED | Marriott Akamai "Access Denied" in the source-ready pass; the BringFido "Airport" lead itself resolved to the Airport building |
| Home2 Downtown; Home2 SE Nona; Residence Inn Lake Nona | IDENTITY_HOLD | own page read; a VERIFIED_NO_PETS brand shares the street identity (dual-brand building), and a same-campus ruling in the shared identity_resolutions document is a registration/founder step |
| Waldorf Astoria | BROWSER_CAPTURE_NEEDED | hotel-info redirects to /resort/; the Pets panel is not exposed to the supported reader |
| Red Roof South Florida Mall | ACCESS_BLOCKED | page read in the browser ("One, well-behaved domestic pet (cat or dog) Stays Free! …") but no first-party page states 32809, so it does not bind |
| Villatel Resort | SOURCE_SILENT | FAQ answer is not rendered to the supported reader |
| Holiday Inn Resort LBV | SOURCE_SILENT | own FAQ answers "Are pets permitted?" with fees only (explicit-only rule) |
| Garnet Inn; Orlando I-Drive North Hotel; OYO Orlando Airport; Motel 6 Winter Park | ROUTING_HOLD | no first-party property page found (Motel 6 property 293842 route found; Motel 6 static times out, Firecrawl probe UNEXPECTED_PAGE, not worked further) |

## 3. Priority 2 — V1 pet-friendly regression (23 rows)

V1 was a lead only. No V1 result entered V2.

| # | V1 identity | Closure verdict | Current evidence |
|---|---|---|---|
| 1 | Embassy Suites Sunset Walk | ACCESS BLOCKED | hilton.com error page (browser); plain client 403 |
| 2 | Hampton Inn & Suites SeaWorld | VERIFIED PET-FRIENDLY | Hilton page, "Pets allowed: Yes" |
| 3 | Hampton Inn & Suites East UCF | VERIFIED PET-FRIENDLY | Hilton page |
| 4 | Hampton Inn Closest to Universal | ACCESS BLOCKED | hilton.com error page |
| 5 | Hampton Inn Maingate South | ACCESS BLOCKED | hilton.com error page |
| 6 | Hampton Inn SE Nona | IDENTITY CHANGE (dual-brand hold) | page read; co-location ruling required |
| 7 | HGI Airport | VERIFIED PET-FRIENDLY | Hilton page |
| 8 | HGI SeaWorld | VERIFIED PET-FRIENDLY | Hilton page |
| 9 | HGI Downtown | IDENTITY CHANGE (dual-brand hold) | page read; co-location ruling required |
| 10 | HGI East UCF | VERIFIED PET-FRIENDLY | Hilton page |
| 11 | HGI I-Drive North | VERIFIED PET-FRIENDLY | Hilton page |
| 12 | HGI Winter Park | VERIFIED PET-FRIENDLY | Hilton page |
| 13 | Home2 Airport | VERIFIED PET-FRIENDLY | Hilton page |
| 14 | Home2 Downtown | IDENTITY CHANGE (dual-brand hold) | page read; co-location ruling required |
| 15 | Home2 Near Universal | VERIFIED PET-FRIENDLY | Hilton page |
| 16 | Home2 South Park | VERIFIED PET-FRIENDLY | Hilton page |
| 17 | Home2 SE Nona | IDENTITY CHANGE (dual-brand hold) | page read; co-location ruling required |
| 18 | Home2 Winter Garden | VERIFIED PET-FRIENDLY | Hilton page |
| 19 | Homewood LBV | ACCESS BLOCKED | hilton.com error page |
| 20 | Homewood Theme Parks | VERIFIED PET-FRIENDLY | Hilton page |
| 21 | Lake Nona Wave | VERIFIED PET-FRIENDLY | own FAQ: "We welcome pets under 40 lbs" |
| 22 | Sonesta ES Suites LBV | VERIFIED PET-FRIENDLY | own page: "…is pet-friendly and welcomes well-mannered pets…"; "Up to two pets are permitted per suite" |
| 23 | Spark by Hilton Universal Blvd | VERIFIED PET-FRIENDLY | Hilton page |

Verdicts: VERIFIED PET-FRIENDLY 15, ACCESS BLOCKED 4, IDENTITY CHANGE 4, VERIFIED NO-PETS 0, STALE/CLOSED 0, INSUFFICIENT CURRENT EVIDENCE 0. Resolved 15, still unresolved 8.

## 4. Priority 3 — Hilton / Marriott (targeted only)

Only cohort members were retried: 24 Hilton and 9 Marriott pages. The 3 Hilton/Marriott co-location identity holds were excluded, because their pages were already read.

- **Router before the browser:**
  - Owned evidence: Marriott route harvest; no owned policy.
  - Brand inventory / property code: routes present.
  - Static: Hilton hotel pages 403 on a plain client, Marriott Akamai.
  - Firecrawl: both families are known capability walls, measured again in pass 001's wall re-probes.
  - Other approved provider: none authorized.
  - The supported browser was therefore the next rung.

| Brand | Targeted | Browser OK | Blocked | Resolved PF | Resolved NP | Still unresolved |
|---|---:|---:|---:|---:|---:|---:|
| HILTON | 24 | 18 | 6 | 15 | 0 | 9 |
| MARRIOTT | 9 | 9 | 0 | 8 | 1 (SpringHill Suites Winter Park: "Pets Not Allowed") | 0 |
| HYATT (non-cohort brand read inside the cohort) | 2 | 2 | 0 | 2 | 0 | 0 |

- **Hilton blocker:**
  - The page shows "Something went wrong / Maybe it's us, maybe it's you. (It's probably us). / Reference No. …" with tab title "Hilton Page Reference Code".
  - It hit the same 6 property codes (`mcoundt`, `mcosrdt`, `mcowhhx`, `mcovshw`, `mcostes`, `mcoswhx`) while neighbouring pages loaded. This is a per-property block observed in three passes.
  - Not retried further: 3-in-a-row stop rule, 8 s spacing.
- **Hilton pages with no policy text:** 3 OK pages (Waldorf, Buena Vista Palace, Hilton LBV) redirect to an amenities/resort layout whose Pets panel the supported reader cannot expose. They stay BROWSER_CAPTURE_NEEDED.
- **Choice:** choicehotels.com served an Akamai bot check to the browser for `fla64`. Not retried; not hammered.

## 5. Priority 4 — corridor-critical (threshold PF ≥ 5)

**CORRIDORS PUBLISHING: 14 → 15.**

| Corridor | PF before → after | Minimum cohort that could change the decision | Result |
|---|---|---|---|
| walt-disney-world | 4 → **5 (publishes)** | Drury Plaza Disney Springs, Hilton Buena Vista Palace, Hilton LBV | Drury Plaza own page "Pet Policy Dogs and cats accepted … Limit of two pets per room with a combined weight of 80 pounds"; both Hiltons' Pets panel not exposed |
| winter-park-maitland | 2 → 4 | HGI Winter Park, SpringHill Winter Park, Park Plaza, Thurston House, Sweet Lodge | HGI WP PF; Park Plaza own policies page "Dogs up to 25 pounds allowed with a non-refundable pet fee"; SpringHill "Pets Not Allowed" (NP); Thurston House and Sweet Lodge have no first-party site. Cannot reach 5 legitimately. |
| four-corners-davenport | 2 → 2 | Omni ChampionsGate, Hampton Maingate South, Comfort Inn Maingate South, Rodeway Davenport | Omni's own page "Pets under 50 lbs. are allowed on the second floor of the main resort building, deluxe rooms only" is held because the shared gate reads it as weight-only (FEE_ONLY) — gate result respected, not reworded; Hampton hilton.com blocked; Comfort Inn Firecrawl UNEXPECTED_PAGE, then Akamai bot check; Rodeway Firecrawl ACCESS_DENIED (pass 001) |
| apopka | 1 → 2 | all 4 unresolved (needs 4 of 4) | HGI Apopka PF; three DBPR-only motels have no route |
| kissimmee-east | 2 → 2 | the 6 routed of 24 unresolved | Routes dead (Crown, Park Royal), retired (Secrets Hideaway: old Ramada page), foreign (Tropicana: another business), shell (Staymore), or silent (Heritage Park Inn) |
| st-cloud | 0 → 0 | none | needs 5 of 7, all DBPR-only with no route; not worked |

No threshold was manufactured. Every allowance counted is a first-party statement accepted by the gate.

## 6. Priority 5 — independents

Independents were worked only inside the cohorts: The Delaney, Lake Nona Wave, Westgate Blue Tree, Villatel, Garnet Inn, OYO, I-Drive North Hotel, Park Plaza, Thurston House, Sweet Lodge, and the Kissimmee East / Apopka / Four Corners routed rows. The other ROUTING_HOLD independents keep their existing bounded reason: no first-party property page from any source in the order.

## 7. Router / Firecrawl / providers

- **Per-target router tracks** (`per_target_router_tracks` in every row of the JSON) record: OWNED ROUTE, STATIC ATTEMPT, OFFICIAL ROUTE, FIRECRAWL ELIGIBLE / ATTEMPTED / RESULT, OTHER PROVIDER, BROWSER RESULT, FINAL DISPOSITION.
- **ACCESS_BLOCKED** was assigned only after static, Firecrawl (eligible or measured wall) and a browser BLOCKED transcription, or when a first-party page cannot bind (Red Roof).
- **Firecrawl this pass:** 1 attempted (`fla64`, CLOSURE_ROUTED, Choice route table), 0 success (UNEXPECTED_PAGE). Credits 562 → 561 (**1 credit**).
- **Free static lane** (`orlando_fl_v2_closure_static_001`): 8 targets, 7 reads bound and verbatim-verified. Omni answered 200 while probing, then 403 twice in the lane; it was read through the browser rung.
- **Supported browser:** 38 page reads — 24 Hilton, 9 Marriott, and 5 by me (Hyatt ×2, Red Roof, Omni, Hard Rock). Plus 3 non-yielding reads (Villatel FAQ, Delaney, and the Hilton LBV panel) and 1 Choice bot check.
  - No page script, no relay, no bot-check or CAPTCHA interaction.
  - One accordion button (Villatel FAQ, Hilton Pets panel) was expanded as a normal navigation action; no form was submitted.
- **Other provider:** none. Bright Data 0, Places 0, USD 0.00. The discovery web search found routes only, never facts.

## 8. Policy safety

- **Negation / contradiction conflicts caught and held:** 6 — 5 NEGATION_HOLD_UNREADABLE_REFUSAL (unchanged set) and 1 QUOTE_CONTRADICTS_CLAIM. No acceptance was published against refusal wording.
- **New parser disagreement this pass:** Omni ChampionsGate. An allowance was read by the gate as FEE_ONLY; it is held and not reworded.
- **Earlier AMENITY_CHIP_ONLY holds:** Sonesta ES LBV's operative sentence and Hyatt Place LBV's pet module were read in full and now pass on their own words.
- **Mixed-page readings:**
  - Marriott `mcozd` and `mcosr` carry fee amounts that disagree between the free text and the structured line. Both are transcribed verbatim; fee fields are whatever the shared Marriott parser reads, and the pets-allowed fact does not depend on the fee.
  - Omni "Pets are not permitted in the villas" is a restriction, not a refusal of the hotel.

## 9. Coverage readiness decision

**COVERAGE READY = FOUNDER DECISION**

What the pass closed:
- The competitor gap is reconciled: 0 true missing. Of 43 matched-unresolved, 27 were resolved, and each of the 16 left has an exact, first-party-grounded blocker (§2).
- The V1 regression is reconciled: 15/23 verified pet-friendly on current pages. The remaining 8 are 4 hilton.com per-property error pages and 4 dual-brand buildings awaiting a shared co-location ruling. None is unexplained, none was reversed, and none used V1 as evidence.
- Walt Disney World now publishes (15/20 corridors).

Why this is not YES:
1. **Unexplored brand inventory (outside this order's cohorts).** BROWSER_CAPTURE_NEEDED still holds 21 brand hotels that no pass has read. Among them:
   - Orlando World Center Marriott, Signia by Hilton Bonnet Creek, The Celeste
   - Courtyard across Universal, Courtyard Grande Lakes
   - Fairfield Near Universal, Fairfield East UCF, Fairfield I-Drive
   - DoubleTree East UCF, HGI Lake Mary, Westin Lake Mary, Evermore
   - Best Western Plus Convention Center, Rodeway ×2, Comfort Inn Kissimmee

   They also include 13 Disney resorts whose own pages carry no dog section. These are explained (the router's next rung is the browser), but brand hotels in core corridors are a plausibly material pet-friendly population that has not been read.
2. **Walled brand properties.** ACCESS_BLOCKED holds 10 Hilton properties, including Conrad and the DoubleTrees, where hilton.com's per-property error page persisted through three passes.
3. **Independents.** ROUTING_HOLD 138 are DBPR/OSM-only independents with no first-party page. They are bounded and low-yield, but they keep the resolution rate at 55.4 %, with 5 corridors not publishing.

Whether launch consideration should wait for one more attended read of the 21 unexplored brand hotels, or accept them as held, is a founder decision. The evidence no longer shows an *unexplained* gap, but it does show an *unread* one.

## 10. Shadow package

| Item | Value |
|---|---|
| OLD PACKAGE DIGEST | `sha256:42df401808bbd169cf5481cbadd020ff4e1bffeeaeff89d6ba657b393f6bcdcc` (`pkg-orlando-fl-42df401808bbd169`, kept as history) |
| NEW PACKAGE DIGEST | `sha256:9ac70eaa99a020cbbc89e2e6c957e3e4f73016644c2f55b8dfd9e90258bfd504` (`pkg-orlando-fl-9ac70eaa99a020cb`) |
| Source commit | `50668d58aa2f5ba28c7f976e6230e06ab53d803b` |
| Receipt | `staging/orlando-fl/shadow_receipts/orlando-fl/pkg-orlando-fl-9ac70eaa99a020cb-f8cda28fc99ace4a.json` |
| FAST | 15/15 PASS (A–O, every rule the lane exposes), 0 UNKNOWN, 0 FAILED, FAST_DATA_ONLY_RELEASE_ELIGIBLE = YES |
| PACKAGE REPRODUCIBLE | YES. A = seal twice in process (identical). B = clean detached worktree `C:\t\orl2b` at `50668d58`, data/ copied (no junction); every offline builder re-run in separate processes (geography, DBPR, OSM, BringFido, Choice/IHG re-reads, independents, closure browser reads, reads, census, clean, partition, staging, shard staging, accounting, closure accounting). `git status` shows 0 changed tracked files, and the separate-process seal returned `sha256:9ac70eaa...bfd504` (identical). 814.7 s. |

**Reproduction caught a fixed-point defect, fixed before the final seal.**
- A first seal (`pkg-orlando-fl-5308ce4eace65833`, from `96087e32`) did not reproduce.
- `orlando_fl_v2_closure_browser_reads_001` copied the name, street and phone from the census, and looked the building up by its baseline key. Once the read joins, the census renames the Omni building to the name its own page states. A clean rebuild then could not find the old key, and dropped the read.
- The builder now emits only what the transcription itself states. It uses the census only to check the binding (key, alias, or house number + postal code). The chain was run twice with no change between runs, and resealed.
- The non-reproducible package and its receipt were discarded, not kept.

## 11. Parallel safety

- `git diff --name-only ad2423b5 HEAD` (before the report and seal outputs): 25 files, every path Orlando-owned, 0 non-Orlando paths.
- `git diff --name-only 1fa43a48 HEAD`: 0 non-Orlando paths.
- `market_authority.check_generated_artifacts()` returns `[]`, so the generated globals are unchanged.
- No shared factory file, other market file, canonical live file or deployment-state file was touched.

**CROSS-MARKET FILE CHANGES = 0. SHARED FACTORY CHANGES = 0. CANONICAL LIVE CHANGES = 0. DEPLOYMENT STATE CHANGES = 0.**

## FINAL ANSWERS

1. CENSUS = 583 (582 + 1 identity correction: TownePlace Suites Orlando Airport)
2. PET-FRIENDLY BEFORE / AFTER = 168 / 201
3. VERIFIED NO-PETS BEFORE / AFTER = 121 / 122
4. RESOLVED BEFORE / AFTER = 289 / 323
5. UNRESOLVED BEFORE / AFTER = 293 / 260
6. RESOLUTION RATE = 49.66 % → 55.40 %
7. BRINGFIDO MATCHED UNRESOLVED BEFORE / AFTER = 43 (44 leads) / 16
8. V1 PET-FRIENDLY CHALLENGE RESOLVED = 15 of 23 (all verified pet-friendly on current first-party pages)
9. V1 CHALLENGE STILL UNRESOLVED = 8 (4 ACCESS BLOCKED — hilton.com per-property error page; 4 IDENTITY CHANGE — dual-brand co-location holds)
10. HILTON TARGETS RESOLVED = 15 of 24
11. MARRIOTT TARGETS RESOLVED = 9 of 9 (8 pet-friendly, 1 no-pets)
12. ACCESS_BLOCKED BEFORE / AFTER = 27 / 18
13. FIRECRAWL ATTEMPTED / SUCCESS = 1 / 0
14. FIRECRAWL CREDITS USED THIS PASS = 1 (562 → 561)
15. NEGATION CONFLICTS CAUGHT = 6 held (5 unreadable-refusal + 1 quote-contradicts-claim); 0 published; plus 1 new non-negation parser disagreement held (Omni, FEE_ONLY)
16. CORRIDORS PUBLISHING BEFORE / AFTER = 14 / 15 (walt-disney-world now publishes)
17. MATERIAL PET-FRIENDLY GAP REMAINS = NO unexplained competitor or V1 gap. An unread gap remains: 21 brand hotels never read, outside this order's cohorts, plus 10 walled Hilton properties.
18. OLD PACKAGE DIGEST = sha256:42df401808bbd169cf5481cbadd020ff4e1bffeeaeff89d6ba657b393f6bcdcc
19. NEW PACKAGE DIGEST = sha256:9ac70eaa99a020cbbc89e2e6c957e3e4f73016644c2f55b8dfd9e90258bfd504
20. PACKAGE REPRODUCIBLE = YES (clean-worktree reproduction byte-identical; same digest)
21. FAST = 15/15 PASS, 0 UNKNOWN, 0 FAILED
22. TECHNICAL SOURCE READY = YES
23. COVERAGE READY = FOUNDER DECISION
24. NEW PAID SPEND = 0
25. FACTORY CODE CHANGED = NO
26. BROAD REGRESSION RUN = 0
27. FINAL CANDIDATE CREATED = NO
28. ORLANDO DEPLOYED = NO
29. origin == HEAD = YES (verified after push of the commit carrying this report)
30. tree clean = YES (verified after that push)

ORLANDO V2 TARGETED COVERAGE CLOSURE = COMPLETE
ORLANDO V2 TECHNICAL SOURCE READY = YES
ORLANDO V2 COVERAGE READY = FOUNDER DECISION
ORLANDO V2 FINAL CANDIDATE = NO
ORLANDO V2 DEPLOYED = NO
FACTORY CODE CHANGED = NO
BROAD REGRESSION RUNS = 0
