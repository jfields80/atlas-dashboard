# PTF-ORLANDO-FL-HARDENED-V2-SOURCE-READY-001 — FINAL

Market `orlando-fl` — **Orlando – Greater Orlando / Central Florida**.
Branch `worker/ptf-orlando-fl-market-002`, worktree `C:\Atlas-Orlando-FL-Hardened-V2`.
Base: live lineage `1fa43a48` (Savannah LIVE, 27 / 1802 / 2081). `origin/main` `c236f52d` lacks the router, the Firecrawl lane and the release lane, so the founder chose a rebase onto `1fa43a48` at precheck.

Orlando V2 was rebuilt from zero. No V1 output was copied, imported or reused. V1 was read once, after V2 accounting was complete, for the Phase 29 diagnostic, using `git show` against V1's commit; the V1 worktree was not modified.

Status: **SHADOW_UNTIL_REGISTERED**. Nothing was registered, participated, authorized, pinned or deployed.

---

## 1. Headline

| Metric | Value |
|---|---|
| Total discovered (graph candidates) | 1,101 |
| DBPR licensed lodging leads | 600 (HOTL 383, MOTL 204, BNB 13) |
| Proposed census (TRUE_HOTEL_IDENTITY) | **582** |
| Valid pet-friendly (first-party gate eligible) | **168** |
| Valid verified-no-pets | **121** |
| Resolved / unresolved | **289 / 293** |
| Resolution rate | **49.66 %** |

- Non-admitted graph nodes: IDENTITY_REVIEW_REQUIRED 88, NAME_ONLY_UNRESOLVED 124, NON_LODGING 197, OUTSIDE_MARKET 106, SAME_IDENTITY_REBRAND_SUCCESSOR 4.
- DBPR licences excluded before entering the graph: CNDO 20,540, DWEL 20,006, NAPT 1,495.

## 2. Holds by class (293, one disposition per row)

| Disposition | Rows | Mechanical root cause |
|---|---:|---|
| ROUTING_HOLD | 140 | No brand inventory, bureau listing or map source stated the property's own page. Mostly DBPR-licensed independent motels and inns on US-192, OBT and Kissimmee East. |
| BROWSER_CAPTURE_NEEDED | 91 | Router's next rung is the attended browser. Marriott (Akamai) and Hilton ("Something went wrong") walled the supported browser session after about 60 reads each. |
| ACCESS_BLOCKED | 27 | Router exhausted on free and authorized lanes. Every row carries a router record: static attempt, Firecrawl eligibility/attempt/result, and a browser BLOCKED transcription where one exists. |
| SOURCE_SILENT | 12 | The own page served, but stated no operative policy. |
| IDENTITY_HOLD | 9 | Dual-brand co-location ruling required (e.g. Staybridge + EVEN Universal Blvd, Home2 + Hampton Lake Nona). |
| EVIDENCE_HOLD | 8 | QUOTE_NOT_OPERATIVE / fee-only / amenity chip. |
| NEGATION_HOLD | 3 | A refusal in plain words that no parser reads as a fact. Held, never published. |
| POLICY_NOT_FOUND | 2 | Disney All-Star Movies and All-Star Music: the page has no pet section. |
| MIXED_RESORT_HOLD | 1 | Westgate Inn: public hotel operation is not proven. |
| PAID / GEOGRAPHY / FOUNDER / OTHER | 0 | — |

Partition states: PUBLISHED_PET_FRIENDLY 168, VERIFIED_NO_PETS 121, AWAITING_OFFICIAL_URL 139, AWAITING_ATTENDED_CAPTURE 87, AWAITING_POLICY_OBSERVATION 28, ACCESS_BLOCKED 27, AWAITING_IDENTITY_RESOLUTION 9, AWAITING_ROUTING_REPLACEMENT 2, AWAITING_CONTRADICTION_RESOLUTION 1. The contract check reported 0 issues.

## 3. Corridor coverage (20 corridors, 62 ZIPs; a page publishes at PF ≥ 5)

| Corridor | Class | Census | PF | NP | Unres. | Page |
|---|---|---:|---:|---:|---:|---|
| international-drive-universal | CORE | 108 | 42 | 20 | 46 | yes |
| kissimmee-us192-maingate | CORE | 56 | 7 | 11 | 38 | yes |
| seaworld-idrive-south | CORE | 53 | 15 | 17 | 21 | yes |
| mco-airport | CORE | 37 | 16 | 12 | 9 | yes |
| celebration-west-192 | CORE | 33 | 8 | 6 | 19 | yes |
| walt-disney-world | CORE | 30 | 4 | 8 | 18 | **no** |
| lake-buena-vista | CORE | 28 | 9 | 10 | 9 | yes |
| downtown-orlando | CORE | 26 | 5 | 5 | 16 | yes |
| south-orlando | CORRIDOR | 39 | 11 | 6 | 22 | yes |
| kissimmee-east | CORRIDOR | 27 | 2 | 1 | 24 | no |
| lake-mary-sanford | CORRIDOR | 27 | 13 | 5 | 9 | yes |
| east-orlando-ucf | CORRIDOR | 20 | 7 | 4 | 9 | yes |
| altamonte-springs-longwood | CORRIDOR | 18 | 8 | 2 | 8 | yes |
| north-orlando-lee-road | CORRIDOR | 17 | 5 | 3 | 9 | yes |
| four-corners-davenport | CORRIDOR | 14 | 2 | 3 | 9 | no |
| flamingo-crossings-winter-garden | CORRIDOR | 13 | 5 | 3 | 5 | yes |
| winter-park-maitland | CORRIDOR | 8 | 2 | 1 | 5 | no |
| clermont | FRINGE | 14 | 6 | 2 | 6 | yes |
| st-cloud | FRINGE | 7 | 0 | 0 | 7 | no |
| apopka | FRINGE | 7 | 1 | 2 | 4 | no |

14 corridor pages publish and 6 do not. Pages exist only where the threshold is met mechanically; there are no thin pages.

**Disney / Universal / Kissimmee.** These figures are street and pin overlays, not corridors.

| Overlay | Census | PF | NP | Unresolved |
|---|---:|---:|---:|---:|
| Walt Disney World | 25 | 3 | 5 | 17 |
| Disney Springs | 9 | 1 | 4 | 4 |
| Universal Orlando | 34 | 11 | 2 | 21 |
| Kissimmee US-192 Maingate | 91 | 15 | 14 | 62 |
| Downtown Kissimmee / East 192 | 19 | 0 | 1 | 18 |

- **Walt Disney World:** the three PF are Art of Animation, Port Orleans Riverside and Yacht Club. Two more resorts have no pet section. Shades of Green is non-public and is excluded.
- **Universal Orlando:** the three Loews/Universal allowances are Portofino, Royal Pacific and Sapphire Falls. Helios, Stella Nova and Terra Luna publish refusals.

## 4. Exclusions

| Class | Count |
|---|---:|
| Vacation rental | 8 (and 192 BringFido rental listings never entered the census) |
| Timeshare | 24 |
| Resort residence | 0 |
| Non-hotel lodging | 165 |
| Outside market | 106 |
| Closed | 0 |

- DBPR condominium, dwelling and non-transient apartment licences are counted and never enter the graph.
- Theme-park campuses stay per-hotel identities, never a campus identity.

## 5. Owned evidence

- **Owned identities reused:** 0. **Owned policy facts reused:** 0.
- **Owned routes reused:** 104 Marriott MCO property codes from the owned Marriott harvest, confirmed against Marriott's Florida state sitemap (same 104). These are routes only; each still needed a first-party read.

## 6. Competitor challenge (BringFido, identity only, never policy authority)

| Measure | Count |
|---|---:|
| Stated total | 417 |
| Raw rows transcribed (pages 1–20; page 21 was a 404) | 361 |
| Normalized unique | 360 |
| Rental listings (excluded) | 192 |
| Hotel leads | 168 |
| Matched to census (EXACT) | 122 |
| — of which published PF | 78 |
| — of which matched but policy unresolved | 44 |
| REVIEW (name not bound to an address) | 42 |
| Rebrand | 1 |
| Timeshare | 2 |
| Vacation rental | 1 |
| Excluded stale / outside | 4 |
| **True missing qualifying hotels** | **0** |

A material competitor *identity* gap does not remain. A competitor *policy* gap does remain: 44 matched hotels are unresolved, most of them on the walled Hilton and Marriott domains.

## 7. Acquisition router and providers

- **Router plan:** 375 routed rows.
  - **Firecrawl-eligible by router:** 19 (IHG 15, Wyndham 4).
  - **Not eligible (356):** known capability wall 181, unmeasured family 92, prior outcome does not escalate 29, static lane answered 20, brand excluded 21, routing repair 12, not a property page 1.
- **Firecrawl policy pass 001:** 78 attempts across four cohorts — ROUTED 19, DISCOVERED 43 (Choice in-market routes), PROBE 14 (≤ 4 per unmeasured family), and WALL_REPROBE 2 (diagnostic only; both ACCESS_DENIED).
  - Publication grade 14, mismatch 33, blocked 20, failed 11.
- **Firecrawl pass 002 (IHG identity fill):** 27 attempts, all IDENTITY_MISMATCH by design. The adapter declines identity and persists the page; the pages were re-read offline for free.
  - The IHG FAQ re-read covers 42 pages, all with a pet block.
- **Firecrawl route discovery:** 11 city pages.
  - Choice: Orlando 46, Kissimmee 2, Davenport 3; Sanford refused.
  - IHG: three `/fl/` URLs returned 404 (3 credits spent); `/florida/` returned Orlando 43, Kissimmee 3, Clermont 4.
- **Credits** (plan credits, no USD): the stage deltas were measured against live reads (pay once per page).

  | Stage | Credits |
  |---|---|
  | Discovery, first round | 656 → 650 (6) |
  | Pass 001 | 650 → 593 (57) |
  | Discovery, second round | 593 → 589 (4) |
  | Pass 002 | 589 → 562 (27) |
  | **Total** | **94** (the opening read before the order was 657) |

- **Supported browser (navigate + accessibility tree `find` only):** 155 reads transcribed as JSONL with a TRANSCRIPTION_SHA256.
  - No page script, relay, CAPTCHA or bot check was used.
  - Marriott and Hilton walled the session. The retry pass after a cooldown was stopped at the 5-in-a-row rule: Hilton retry 1 OK and 10 BLOCKED, Marriott retry 10 BLOCKED. All BLOCKED rows are recorded in `raw_captures/*_retry.jsonl`.
- **Free static lanes:**
  - Wyndham property service: 50 read.
  - ESA FAQPage: 20.
  - Loews policy sentences.
  - Independents' own policy/FAQ pages (new lane `orlando_fl_v2_policy_pages_lane_001`): 83 sites, 39 bound by house number + ZIP or phone, or by the site's own hotel JSON-LD. 19 verbatim, quote-verified reads became `orlando_fl_v2_independent_reads_001`, including all seven Rosen properties.
- **Other providers:** Bright Data 0, Places 0, other paid 0. **USD 0.00. New paid spend 0. New provider authorization 0.**

## 8. Policy and negation safety

- The shared first-party gate reader is negation-blind. The market-local negation guard in `orlando_fl_v2_clean_authority_001` caught 5 conflicts, all NEGATION_HOLD_UNREADABLE_REFUSAL:
  - City Express I-Drive
  - HIC Vacations Orlando Breeze
  - Holiday Inn Disney Springs
  - Ramada Plaza I-Drive
  - The Point
- One more gate/quote contradiction was held: The Grove, "welcomes service animals but not pets", as QUOTE_CONTRADICTS_CLAIM.
- None was accepted. Explicit-only facts: a fee, count or weight alone never establishes acceptance (Celebration Suites and Holiday Inn Resort LBV stay held).

## 9. Identity corrections made during sealing

- **FAST rule C** (trial seal) caught two Choice no-pets records whose page code differed from the census code. The cause was Choice sitemap routes that name only a flag and a town ("Quality Inn Kissimmee"), bound by name.
  - Census fix: the property code on the building's own page now wins, and a same-family, address-less route code that differs is detached. 17 detachments are recorded in `name_bound_codes_detached_by_the_page_code`.
- **FAST rule J** (trial seal) refused an 88-character listing id. Census fix: a building whose page name slugs past 80 characters takes the longest name its brand's own inventory, then DBPR, then OSM states. This is a stated name, never a truncation.
- **Reproduction** found an unordered alias lookup in the partition, caused by per-process string hash randomization, and a wall-clock field in the OSM report. Both were fixed: ordered keys, and no clock written.

## 10. Shadow package, FAST, reproduction

| Item | Value |
|---|---|
| Source commit | `34192de425d484586eded334e3f3d6524346189d` |
| Package | `pkg-orlando-fl-42df401808bbd169` |
| PACKAGE DIGEST | `sha256:42df401808bbd169cf5481cbadd020ff4e1bffeeaeff89d6ba657b393f6bcdcc` |
| Execution zone | SHADOW_UNTIL_REGISTERED |
| Receipt | `staging/orlando-fl/shadow_receipts/orlando-fl/pkg-orlando-fl-42df401808bbd169-dc47c1172ae5b9a3.json` |
| FAST (all rules the lane exposes, A–O) | 15/15 PASS, 0 UNKNOWN, 0 FAILED; FAST_DATA_ONLY_RELEASE_ELIGIBLE = YES; determinism BYTE_IDENTICAL |
| First-party gate on package | 289 evaluated, 289 eligible, 0 ineligible |
| Declared routes | 183 |
| REPRODUCTION A | this worktree: seal twice in process, identical digest |
| REPRODUCTION B | clean detached worktree `C:\t\orl2b` at `34192de4`, data/ COPIED (no junction); geography, DBPR, OSM, BringFido, Choice/IHG re-reads, independents, reads, census, clean authority, partition, staging, shard staging and accounting all re-run in separate processes; separate-process digest-only seal returned `sha256:42df4018...bcdcc` |
| BYTE IDENTICAL | YES: `git status` of the reproduction tree shows 0 changed tracked files after every builder re-ran; the package digest matches |
| NONDETERMINISTIC FILES | 0 at the final commit. Two were found and fixed on the way: the OSM report wall-clock `seconds`, and an unordered alias lookup in the partition |

Checks covered: line endings (writers emit LF, with `core.autocrlf` normalised by git), serialization (sorted/OrderedDict, `indent=1`), ordering (ordered alias keys), hashes, source commit, absolute paths (none in package inputs), machine-specific values, and timestamps (fixed `SEALED_AT`, `CAPTURED_AT`).

FAST rule N binds this package to the current live parent (Savannah, deploy 6aa93de5). Once a later market is live, rule N fails this package by design, and the registration order reseals.

## 11. Coverage readiness

- **TECHNICAL SOURCE READY = YES.** Deterministic, reproducible, FAST-clean, isolated (§12), fully accounted (one disposition per row, 582 = 168 + 121 + 293).
- **COVERAGE READY = FOUNDER DECISION**, mechanically:
  - Competitor gap: 0 true missing, 122 exact matches; the identity gap is reconciled.
  - Provider and router lanes were exercised: static, Firecrawl (routed, discovered, probe and wall re-probe), and the supported browser up to measured walls. No lane was silently skipped, and every ACCESS_BLOCKED row has a router record.
  - The PF gap is explained, not unexplained: 44 BringFido-matched hotels are unresolved, dominated by the Hilton and Marriott walls (Hilton 36 unresolved, Marriott 24).
  - The unresolved population is bounded and justified row by row, but it is large: 50.3 %. ROUTING_HOLD alone is 140, mostly independent motels with no first-party page. The Walt Disney World corridor (PF 4) and Kissimmee East (PF 2) do not publish.
  - Whether a 49.7 % resolution rate, with the core I-Drive / Universal / airport / LBV corridors publishing, is acceptable for launch consideration is a judgment the contract leaves to the founder. It is not a FAST fact.

## 12. Parallel safety

- `git diff --name-only 1fa43a48 HEAD` lists 77 files (plus this report and the seal outputs). Every path contains `orlando`, and there are 0 non-Orlando paths.
- `market_authority.check_generated_artifacts()` returns `[]` (generated globals unchanged).

| Check | Changes |
|---|---:|
| V1 Orlando files | 0 |
| Tampa / Augusta / Myrtle Beach / Savannah / other market files | 0 |
| Shared factory files | 0 |
| Canonical live files | 0 |
| Deployment-state files | 0 |

**CROSS-MARKET FILE CHANGES = 0. SHARED FACTORY CHANGES = 0. CANONICAL LIVE CHANGES = 0. DEPLOYMENT STATE CHANGES = 0.**

## 13. V1 vs V2 diagnostic (`reports/orlando_fl_v2_v1_diagnostic_001.json`)

| | V1 | V2 | Delta |
|---|---:|---:|---:|
| Census | 545 | 582 | +37 |
| Pet-friendly | 87 | 168 | +81 |
| No-pets | 2 | 121 | +119 |
| Resolved | 89 | 289 | +200 |
| Unresolved | 456 | 293 | −163 |
| Resolution rate | 16.3 % | 49.7 % | +33.4 pts |
| ACCESS_BLOCKED | 149 | 27 (after router exhaustion) | −122 |

Causes of improvement:

1. **Refusals are now facts.** V2 reads each brand's own refusal wording (Marriott "Pets Not Allowed", Wyndham property service, IHG FAQ "No, pets are not allowed", Loews, Choice "Pets Allowed: No"), with the negation guard in front of the gate. V1 published 2 refusals.
2. **The acquisition router replaced blanket ACCESS_BLOCKED.**
   - Firecrawl routed IHG/Wyndham, discovered Choice and IHG routes from the brands' own city pages, and was re-read offline for free.
   - The supported browser read Marriott, Hilton, Hyatt, Best Western and Disney.
   - Free static brand services (Wyndham, ESA, Loews) and the independents' own policy/FAQ pages were added.
   - Of V1's shared-key ACCESS_BLOCKED rows, 20 became VERIFIED_NO_PETS and 18 became PUBLISHED_PET_FRIENDLY.
3. **The census rebuild** on the DBPR backbone, with street-spelling folds and page-code identity, admitted 37 more hotels. Keys shared with V1: 319 (V1-only 226, V2-only 263; key spellings differ).

Deterioration:

- 23 V1-published PF identities are not published in V2: 17 AWAITING_ATTENDED_CAPTURE / ACCESS_BLOCKED, 4 identity holds, 2 policy holds.
- 21 of them are Hilton properties. V1 used Hilton's inventory GraphQL, and V2's supported browser was walled after about 60 Hilton reads.
- No V1 pet-friendly row was reversed to no-pets.
- V2 was not modified toward the comparison.

## 14. Timing (ET, 2026-09-15; from file creation times and command logs)

| Phase | Window |
|---|---|
| Precheck and rebase decision | 10:03–10:20 |
| Geography, corridors, submarket split test | 10:20–10:22 |
| Census lanes (DBPR 10:23, bureau 10:33, OSM 10:38, BringFido 10:55, brand inventories 10:56) | 10:22–10:57 |
| Identity reconciliation (census) | 10:58 (re-run through 15:57) |
| Owned-data reuse (Marriott harvest) | inside brand inventory, about 2 min |
| Routing | 10:58–11:00 |
| Static acquisition (Wyndham 11:00, static 11:12, ESA 14:20, Loews 14:38, independents 14:53–15:05) | about 25 min total |
| Firecrawl acquisition (discovery 11:17; pass 001 through 14:38; pass 002 about 14:45–14:52) | about 45 min active |
| Other provider acquisition | 0 |
| Browser acquisition (Marriott 11:06–14:42, Hyatt/BW/Disney 14:27–14:37, Hilton through 15:08, retries 15:25–15:28) | about 95 min active |
| Account usage-limit stall (HTTP 429 until the 13:30 reset; resumed on "Resume") | about 2 h |
| Policy adjudication (reads, clean authority) | 14:16–15:40 (iterative) |
| Competitor reconciliation | inside census and accounting |
| Final accounting | 14:25–15:57 (iterative) |
| Shadow package (three trial seals 15:12–15:43; final seal 15:57, 170 s including FAST) | — |
| Reproduction B (clean worktree, 15:59) | 15:59–16:13 (813.6 s, of which the cold OSM PBF pass is about 11 min) |
| FAST | inside seal, about 2 min |

- **ZERO_TO_SOURCE_READY:** 6 h 10 m, 10:03 → 16:13 ET (includes about 2 h of account usage-limit stall).
- **PROVIDER COST:** $0.00 USD; 94 existing Firecrawl plan credits.
- **NEW PAID SPEND:** 0.
- **FOUNDER INTERVENTION:** 1 (base-branch choice at precheck; not a spend or factory decision).
- **PEAK MEMORY:** not instrumented; the OSM PBF pass is the largest process (656 MB extract).
- **Cleanup:** background agents stopped, wait loops finished, no HTTP servers or relays were ever started, reproduction worktree removed, browser tabs closed.

## 15. Machine-readable documents

| Document | Path |
|---|---|
| Source-ready accounting | `launch_packages/pettripfinder/markets/reports/orlando_fl_v2_source_ready_accounting_001.json` (headline, holds, exclusions, corridors, overlays) |
| Provider-attempt accounting | same file, `providers` block; per-attempt rows in `orlando_fl_v2_firecrawl_pass_001.json`, `_pass_002.json`, `_discovery_001.json`, `orlando_fl_v2_ladder_plan_001.json`, `orlando_fl_v2_free_static_capture_001.json`; router record per unresolved row in `staging/orlando-fl/launch_package/orlando_fl_final_partition_v2_001.json` |
| Brand-by-brand | accounting `brand_by_brand` |
| Competitor reconciliation | accounting `competitor_reconciliation`, `orlando_fl_v2_competitor_gap_matrix_001.json`, `orlando_fl_v2_competitor_challenge_001.json` |
| Remaining unresolved root causes | accounting `remaining_unresolved_root_causes`; per row in the partition |
| V1 vs V2 | accounting `v1_vs_v2` and `orlando_fl_v2_v1_diagnostic_001.json` |
| Shadow package report | `orlando_fl_v2_shadow_package_001.json` |

---

## FINAL ANSWERS

1. START TIMESTAMP = 2026-09-15T10:03:00-04:00
2. ZERO_TO_SOURCE_READY = 6 h 10 m, 10:03 → 16:13 ET (includes about 2 h of account usage-limit stall)
3. TOTAL DISCOVERED = 1,101 graph candidates (600 DBPR leads, 950 OSM elements, 211 bureau listings, 360 BringFido uniques, brand inventories)
4. PROPOSED CENSUS = 582
5. VALID PET-FRIENDLY = 168
6. VALID VERIFIED-NO-PETS = 121
7. RESOLVED / UNRESOLVED = 289 / 293
8. RESOLUTION RATE = 49.66 %
9. HOLDS BY CLASS = ROUTING 140; BROWSER_CAPTURE 91; ACCESS_BLOCKED 27; SOURCE_SILENT 12; IDENTITY 9; EVIDENCE 8; NEGATION 3; POLICY_NOT_FOUND 2; MIXED_RESORT 1; PAID 0; GEOGRAPHY 0; FOUNDER 0
10. CORRIDOR COVERAGE = 20 corridors, all with census rows; 14 pages publish (PF ≥ 5); 6 do not (walt-disney-world 4, kissimmee-east 2, four-corners-davenport 2, winter-park-maitland 2, st-cloud 0, apopka 1)
11. DISNEY / UNIVERSAL / KISSIMMEE COVERAGE = WDW overlay 25 (PF 3, NP 5, unresolved 17); Disney Springs 9 (1/4/4); Universal 34 (11/2/21); Kissimmee US-192 Maingate 91 (15/14/62); Downtown Kissimmee / East 192 19 (0/1/18)
12. VACATION RENTAL / TIMESHARE / RESIDENCE EXCLUSIONS = 8 / 24 / 0 (plus 192 BringFido rental listings, and DBPR CNDO 20,540 / DWEL 20,006 / NAPT 1,495 never admitted)
13. OWNED EVIDENCE REUSED = 0 identities, 0 policy facts; 104 owned Marriott routes
14. BRINGFIDO RAW / NORMALIZED / MATCHED / TRUE MISSING = 361 / 360 (168 hotel leads) / 122 / 0
15. MATERIAL COMPETITOR GAP REMAINS = NO for identity (0 true missing); a policy gap of 44 matched-unresolved remains, mostly Hilton and Marriott walled
16. FIRECRAWL ELIGIBLE = 19 by router plan (plus 43 discovered Choice routes, 14 probes, 27 IHG identity-fill routes)
17. FIRECRAWL ATTEMPTED = 105 property attempts (78 + 27) + 11 discovery pages
18. FIRECRAWL SUCCESS = 14 publication-grade in pass 001; 42 IHG pages persisted and re-read offline with a pet block; 29 Choice pages re-read; 101 routes discovered
19. FIRECRAWL FAILED = 64 in pass 001 (blocked 20, failed 11, mismatch 33); 27 pass-002 declines by design; 3 discovery 404s; 1 refusal (Sanford)
20. ACCESS_BLOCKED AFTER ROUTER EXHAUSTION = 27
21. NEGATION CONFLICTS CAUGHT = 5 (all held; plus 1 QUOTE_CONTRADICTS_CLAIM hold)
22. EXISTING PROVIDER USAGE = Firecrawl 94 plan credits (656 → 562); supported browser 155 reads; Bright Data 0; Places 0
23. NEW PAID SPEND = 0
24. PROVIDER COST = $0.00 USD (existing plan credits only)
25. SHADOW PACKAGE CREATED = YES (pkg-orlando-fl-42df401808bbd169, SHADOW_UNTIL_REGISTERED)
26. PACKAGE REPRODUCIBLE = YES (in-process A and separate-worktree B give an identical digest; tree byte-identical)
27. PACKAGE DIGEST = sha256:42df401808bbd169cf5481cbadd020ff4e1bffeeaeff89d6ba657b393f6bcdcc
28. APPLICABLE FAST = 15/15 PASS (A–O), 0 UNKNOWN, 0 FAILED
29. TECHNICAL SOURCE READY = YES
30. COVERAGE READY = FOUNDER DECISION
31. V1 CENSUS / RESOLVED / UNRESOLVED = 545 / 89 / 456
32. V2 CENSUS / RESOLVED / UNRESOLVED = 582 / 289 / 293
33. V2 IMPROVEMENT EXPLANATION = First-party refusals read as facts behind a negation guard (NP 2 → 121). The acquisition router replaced blanket ACCESS_BLOCKED (149 → 27): Firecrawl route discovery and offline re-reads, supported-browser transcription, free brand services and independents' own policy pages. A DBPR-backbone census with page-code identity (+37). The only deterioration is 23 V1-published PF held again, 21 of them Hilton-walled; none reversed.
34. CROSS-MARKET FILE CHANGES = 0
35. FACTORY CODE CHANGED = NO
36. BROAD REGRESSION RUN = 0
37. FINAL PRODUCTION CANDIDATE CREATED = NO
38. FOUNDER AUTHORIZATION CREATED = NO
39. ORLANDO DEPLOYED = NO
40. origin == HEAD = YES (verified after `git push -u origin worker/ptf-orlando-fl-market-002` of the commit carrying this report)
41. tree clean = YES (verified after that push)

ORLANDO V2 SOURCE READY = YES
ORLANDO V2 COVERAGE READY = FOUNDER DECISION
ORLANDO V2 FINAL CANDIDATE = NO
ORLANDO V2 DEPLOYED = NO
BROAD REGRESSION RUNS = 0
FACTORY CODE CHANGED = NO
WAITING FOR RELEASE QUEUE = YES
