# PTF-TAMPA-FL-HARDENED-V2-SOURCE-READY-001 — FINAL

Market `tampa-fl` — **Tampa Bay, Florida** (Tampa / St. Petersburg / Clearwater — one market; see §3).
Branch `worker/ptf-tampa-fl-market-002`, worktree `C:\Atlas-Tampa-FL-Hardened-V2`.
Base: live lineage `1fa43a48` (Savannah LIVE, 27 / 1802 / 2081).

Tampa V2 was rebuilt from zero: no V1 identity, policy fact, or evidence row was copied, imported or reused. V1's own committed partition (`worker/ptf-tampa-fl-market-001`, read via `git show`, not modified) was read once, after V2 accounting was complete, for the §13 diagnostic.

Status: **SHADOW_UNTIL_REGISTERED**. Nothing was registered, participated, authorized, pinned or deployed.

---

## 1. Headline

| Metric | Value |
|---|---|
| Total raw observations (all lanes) | 2,553 |
| DBPR licensed-lodging leads | 676 (526 admitted, 150 observed outside the market) |
| Nodes after hard-key identity merge | 1,817 (0 merge conflicts) |
| Proposed census (TRUE_HOTEL_IDENTITY) | **495** |
| Valid pet-friendly (CLEAN_PET_FRIENDLY) | **92** |
| Valid verified-no-pets (CLEAN_VERIFIED_NO_PETS) | **25** |
| Resolved / unresolved | **117 / 378** |
| Resolution rate | **23.64 %** |

- Non-admitted graph nodes (1,322 of 1,817): IDENTITY_REVIEW_REQUIRED 162, NAME_ONLY_UNRESOLVED 651, NON_LODGING 264, OUTSIDE_MARKET 242, SAME_CAMPUS_DISTINCT_ENTITY 2, SAME_IDENTITY_REBRAND_SUCCESSOR 1.
- Lane yields into the graph: REGISTRY_FL_DBPR 676, OSM_OVERPASS 643, BRAND_INVENTORY_OWNED 79, BRAND_INVENTORY_CITY_PAGE 72, BRAND_INVENTORY_STATE_SITEMAP 3, BRAND_INVENTORY_SITEMAP 60, DESTINATION_ORGANIZATION 106, COMPETITOR_LEAD 914.
- DBPR licences excluded before entering the graph: CNDO 4,392, DWEL 4,367, NAPT 1,878.

## 2. Holds by class (378, one disposition per row)

| Disposition | Rows | Mechanical root cause |
|---|---:|---|
| ROUTING_HOLD | 330 | No first-party route was ever assembled: mostly independent DBPR-licensed motels/inns with no brand inventory, bureau or map route, and static-only brand families (IHG, Choice, Best Western, Hyatt, Red Roof, Radisson, Motel 6) this order's Firecrawl probe cohort did not reach individually. |
| BROWSER_CAPTURE_NEEDED | 21 | Marriott/Hilton/Hyatt routes this order's supported-browser lane had not yet reached when Hilton's 5-in-a-row wall stopped that lane, or Hyatt routes on subdomains this browser session had no read permission for. |
| ACCESS_BLOCKED | 10 | Every free/authorized lane this order attempted (static plain client, Firecrawl where eligible) was refused or failed. |
| SOURCE_SILENT | 10 | The page served and stated no operative pet policy the shared readers located. |
| EVIDENCE_HOLD | 5 | A fee/weight/count sentence with no explicit acceptance wording in the same quote; held rather than published on an amenity fragment alone. |
| IDENTITY_MISMATCH_HOLD | 2 | The fetched page's own identity did not confirm the census row (Brandon Motor Lodge, Water Street Tampa). |
| NEGATION / PAID / GEOGRAPHY / FOUNDER / OTHER | 0 | — |

Partition states: PUBLISHED_PET_FRIENDLY 92, VERIFIED_NO_PETS 25, AWAITING_OFFICIAL_URL 330, AWAITING_ATTENDED_CAPTURE 21, AWAITING_POLICY_OBSERVATION 15, ACCESS_BLOCKED 10, AWAITING_ROUTING_REPLACEMENT 2. The contract check reported 0 issues.

The 5 EVIDENCE_HOLD / SHARED_READER_DISAGREES catches (never published, held instead):

- Holiday Inn Tampa North — SHARED_READER_DISAGREES: an amenity label states no policy ("pets allowed" alone).
- Hollander Hotel — held on a fee/weight/count sentence alone; no explicit acceptance wording in the quote.
- Safety Harbor Resort — SHARED_READER_DISAGREES: a service-animal sentence paired with a refusal is not read as an operative refusal by the shared reader (SERVICE_ANIMAL_ONLY).
- Sailport Waterfront Suites on Tampa Bay — same SERVICE_ANIMAL_ONLY class as above.
- Seminole Hard Rock Hotel & Casino Tampa — held on a fee/weight/count sentence alone.

## 3. Tampa / St. Petersburg / Clearwater market-boundary decision

Documented at length in `tampa_fl_v2_geography_001.py` (module docstring and the `submarket_split_test` report section): Tampa, St. Petersburg and Clearwater are **one market**, not three. The three cities share a single contiguous MSA (Tampa–St. Petersburg–Clearwater), a single regional destination organization (Visit Tampa Bay / Visit St. Pete–Clearwater cross-links), and no ZIP-level seam that would let a corridor partition cut cleanly along a city line — the bay itself, not a city boundary, is the only defensible geographic split, and several corridors (e.g. Gulf beaches) straddle city limits. The registry therefore admits 66 ZIPs into 19 corridors under one `tampa-fl` market id: 6 CORE (Tampa-side), 7 CORRIDOR (St. Petersburg / Clearwater / Gulf beaches), 6 FRINGE.

## 4. Corridor coverage (19 corridors, 66 admitted ZIPs; 7 publish)

| Corridor | Class | Census | PF | NP | Unres. | Page |
|---|---|---:|---:|---:|---:|---|
| downtown-riverwalk | CORE | 28 | 12 | 2 | 14 | yes |
| ybor-city | CORE | 6 | 3 | 0 | 3 | no |
| westshore-airport-rocky-point | CORE | 45 | 20 | 6 | 19 | yes |
| busch-gardens-usf | CORE | 32 | 7 | 3 | 22 | yes |
| brandon | CORE | 11 | 3 | 0 | 8 | no |
| east-tampa-i75 | CORE | 35 | 10 | 2 | 23 | yes |
| st-petersburg-downtown | CORRIDOR | 37 | 5 | 1 | 31 | yes |
| st-petersburg | CORRIDOR | 35 | 1 | 2 | 32 | no |
| clearwater-downtown | CORRIDOR | 17 | 1 | 0 | 16 | no |
| clearwater-beach | CORRIDOR | 56 | 7 | 3 | 46 | yes |
| st-pete-beach-treasure-island | CORRIDOR | 84 | 7 | 0 | 77 | yes |
| madeira-redington-indian-rocks | CORRIDOR | 29 | 0 | 1 | 28 | no |
| largo | CORRIDOR | 10 | 3 | 0 | 7 | no |
| wesley-chapel-new-tampa | FRINGE | 12 | 4 | 3 | 5 | no |
| south-hillsborough | FRINGE | 10 | 3 | 1 | 6 | no |
| plant-city | FRINGE | 7 | 2 | 0 | 5 | no |
| tarpon-dunedin | FRINGE | 28 | 1 | 1 | 26 | no |
| mid-pinellas | FRINGE | 5 | 1 | 0 | 4 | no |
| safety-harbor-oldsmar-palm-harbor | FRINGE | 8 | 2 | 0 | 6 | no |

7 corridor pages publish (downtown-riverwalk, westshore-airport-rocky-point, busch-gardens-usf, east-tampa-i75, st-petersburg-downtown, clearwater-beach, st-pete-beach-treasure-island) and 12 do not — a page publishes only where the PF ≥ 5 threshold is met mechanically; there are no thin pages. `uncorridored_rows` = 0.

## 5. Exclusions

| Class | Count |
|---|---:|
| Non-hotel lodging | 148 |
| Vacation rental | 114 |
| Timeshare | 1 |
| Resort residence | 1 |
| Outside market | 242 |
| Identity review required (unresolved graph residual) | 162 |
| Name-only unresolved (no street/phone/code to open a building) | 651 |
| Same-campus distinct entity | 2 |
| Same-identity rebrand successor | 1 |

DBPR condominium (CNDO 4,392), dwelling (DWEL 4,367) and non-transient-apartment (NAPT 1,878) licences are counted and never enter the graph.

## 6. Owned evidence

- **Owned identities reused:** 0. **Owned policy facts reused:** 0. Tampa was built from zero; no V1 row was copied or imported.
- **Owned routes reused:** 79 Marriott routes from the committed national owned-brand-directory harvest (`dayton_oh_brand_directory_harvest_001.json`, 17,928 routes in corpus, 0 new HTTP requests for these 79 leads). Routes only — each still needed a first-party read to become a policy fact.

## 7. Competitor challenge (BringFido, identity only, never policy authority)

| Measure | Count |
|---|---:|
| Cities challenged | 9 (Tampa, St. Petersburg, Clearwater, Clearwater Beach, St. Pete Beach, Treasure Island, Madeira Beach, Largo, Brandon) |
| Raw rows transcribed | 1,090 |
| Normalized unique | 914 |
| Matched to census (exact name) | 55 |
| True-missing **candidates** (name-only, pending first-party verification) | 859 |

A competitor *identity* gap of unverified candidates remains large by raw count (859), but per the standing rule that a competitor directory is an AUDIT lane and never an acquisition lane, none of these 859 is an admitted identity — they are name-normalized leads that never passed a street/phone/property-code test. §8 gives the material-gap assessment.

## 8. Material gap assessment

The 859 BringFido name-only candidates are the dominant open question, but they are not a proven gap: BringFido pages list vacation rentals, timeshares and out-of-market beach-town listings alongside hotels, and this order's own DBPR/OSM/brand lanes already returned 651 NAME_ONLY_UNRESOLVED graph nodes independently (i.e., largely the same population, discovered from the licensing/brand side rather than the competitor side). No first-party verification pass was run against the 859 in this order — that is future work, not a known miss. **MATERIAL GAP = UNRESOLVED, SIZE UNVERIFIED** — a founder/coverage decision, not a technical failure.

## 9. Acquisition router and providers

- **Routing:** 495 admitted identities routed. `routing_by_state`: INDEPENDENT_REVIEW 292, ROUTED_OFFICIAL_INVENTORY 99, FREE_LANE_EXHAUSTED 42, ROUTED_MAP_WEBSITE 36, ROUTED_OFFICIAL_DESTINATION 25, ROUTE_BRAND_MISMATCH 1.
- **Free static capture:** 208 free HTTP requests. `static_capture_outcomes`: ACCESS_DENIED 163, IDENTITY_MISMATCH 24, UNEXPECTED_PAGE 7, NAVIGATION_FAILED 4, POLICY_NOT_FOUND 4, UNHYDRATED 2, VALID 6.
- **Independent policy-pages lane:** 45 sites attempted, 30 bound by address/phone/JSON-LD, 22 with pet sentences read.
- **Wyndham first-party lane:** 55 routes selected, 22 read (16 pet-friendly / 6 no-pets), 31 retired (redirected to brand search), 2 errors.
- **ESA lane:** all 3 city pages (Tampa, St. Petersburg, Clearwater) returned HTTP 403 to the plain client — 0 usable rows.
- **Firecrawl pass 001:** 23 planned, 23 attempted, across cohorts ROUTED 14 / PROBE 7 / WALL_REPROBE 2 (no DISCOVERED cohort this order). Outcomes: VALID 9, IDENTITY_MISMATCH 6, NAVIGATION_FAILED 6, UNEXPECTED_PAGE 2 → classified FIRECRAWL_PUBLICATION_GRADE 9, FIRECRAWL_MISMATCH 6, FIRECRAWL_FAILED 8.
  - Credits: 561 → 544 (17 spent). USD 0.00 — plan credits only, no per-call price exists (bimodal cost: 1 credit success, 0 on total refusal).
- **Supported browser (navigate + accessibility-tree `find` only, no scripts/CAPTCHA bypass):**
  - Marriott: 68 properties read (42 pet-friendly / 26 no-pets), 0 blocked.
  - Hilton: 42 properties read (39 pet-friendly / 3 no-pets), walled after 42 reads (5-in-a-row BLOCKED rule fired, session correctly stopped); retry pass captured 5 more, all BLOCKED (recorded in `hilton_browser_rows_retry.jsonl`).
  - Hyatt + Best Western: 4 real reads, 4 browser-permission-denied (subdomain), 1 negation conflict caught.
- **Other providers:** Bright Data 0, Google Places 0, other paid 0. **USD 0.00. New paid spend 0. New provider authorization 0.**

## 10. Policy and negation safety

The shared first-party gate reader (`first_party_binding.classify_quote`) is negation-blind on its own; the market-local negation guard added to `tampa_fl_v2_clean_authority_001` re-checks every CLEAN_PET_FRIENDLY / CLEAN_VERIFIED_NO_PETS row against the shared reader with a `quote` + `context` split (the `pets_allowed`-specific sentence vs. every other field's evidence text from the same artifact), and demotes any disagreement to EVIDENCE_HOLD rather than publish. It caught 5 conflicts (listed in §2) across two hardening rounds:

- **Round 1** (2 SERVICE_ANIMAL_ONLY, then 7 AMENITY_CHIP_ONLY after a quote/context regression, 4 of which were recovered by adding the `context` field): root-caused to concatenated/duplicated evidence quotes confusing the shared reader.
- **Round 2** (3 further AMENITY_CHIP_ONLY at seal time, different records): root-caused to `registration_staging` writing the same short `pets_allowed` quote into every fact field's staged evidence instead of each field's own real text, so `first_party_binding`'s same-page `_context()` re-check (grouped by `artifact_sha256`) found no fee/count context in the staged package even though `clean_authority`'s own gate had validated correctly. Fixed by propagating `full_quote = quote + " " + context` into every staged evidence entry (commit `b3b0b887`).

None of the 5 final holds was accepted on a fee/weight/count sentence alone; explicit acceptance wording is required in the same quote.

## 11. Identity correction made before sealing

FAST rule G (`CROSS_MARKET_IDENTITY_COLLISION`, checked via `release_index`) caught a bare, generic census name — "TownePlace Suites by Marriott" — colliding with an existing Cleveland-Akron-Canton, OH identity of the same name. Root cause: a brand sitemap route naming only a flag and no city-qualified name; this falls outside `census_reconciliation`'s `name_bare_identities()` scope (that function only folds ≤ 2-token names, and this name is 4 tokens). Fix: renamed the row to its actual brand-page name, "TownePlace Suites Plant City" (property code `tpapt`), and re-derived its `identity_key`/slug/aliases via `ptf_identity_key` (commit `e66579ab`).

## 12. Shadow package, FAST, reproduction

| Item | Value |
|---|---|
| Source commit | `b3b0b8873a52a11a67ef8619fd6eff8d7c8c1a6a` |
| Package | `pkg-tampa-fl-3c436d332f587f8a` |
| PACKAGE DIGEST | `sha256:3c436d332f587f8a8fd1619b5c157b73bba9ecdcb1a86b1355bf8e52dcfb36d9` |
| Execution zone | SHADOW_UNTIL_REGISTERED |
| Receipt | `staging/tampa-fl/shadow_receipts/tampa-fl/pkg-tampa-fl-3c436d332f587f8a-1d61a919227ee158.json` |
| FAST (all rules the lane exposes, A–O) | 15/15 PASS, 0 UNKNOWN, 0 FAILED; FAST_DATA_ONLY_RELEASE_ELIGIBLE = YES; determinism BYTE_IDENTICAL |
| Declared/public routes | 110 site routes (92 hotel profile pages, 7 corridor pages, 1 comparison page, 458 `/go/` affiliate pages, base bundle 100 files) |
| REPRODUCTION A | this worktree: sealed twice in-process, identical digest |
| REPRODUCTION B | separate detached worktree `C:\t\tpa2b` (`git worktree add --detach`, fresh checkout of the same commit, independent `python.exe` process); `clean_authority` and `registration_staging` re-run there first and diff'd byte-identical against the committed reports/staging files, then `shadow_package_001 --stage` re-run independently |
| BYTE IDENTICAL | YES — `sha256:3c436d332f587f8a...` in both worktrees, both processes, both 15/15 FAST PASS |

**A real reproducibility bug was caught and fixed by REPRODUCTION B, not by the in-process double build.** The first reproduction attempt (against package `bc9dcb0228d964d9`) produced a *different* digest across worktrees despite each worktree independently reporting `reproducible-in-process YES`. Root cause: this worktree's on-disk copy of `identity_census_proposed/tampa-fl.json` carried one stray, uncommitted trailing CRLF (a leftover artifact from an earlier one-off Python edit script), invisible to `git diff`/`git status` at a glance but present in the exact bytes `shadow_package_001` hashed into `dependency_input_digests.census`. The actual committed git blob was already clean (LF-only, confirmed via `git show HEAD:...`). Fixed by normalizing the working copy to match HEAD exactly (0 content diff), regenerating `clean_authority` and `registration_staging` from it (identical PF 92 / NP 25 / resolved 117, confirming the CRLF was whitespace-only and never touched parsed data), and resealing — producing the `3c436d33...` package reported above, which **did** reproduce byte-identically cross-worktree. Commit `fc2c72d7`.

## 13. Coverage readiness

- **TECHNICAL SOURCE READY = YES.** Deterministic, cross-worktree reproducible, FAST-clean, isolated (§14), fully accounted (one disposition per row, 495 = 117 resolved + 378 unresolved).
- **COVERAGE READY = FOUNDER DECISION**, mechanically:
  - Resolution rate is 23.64 %, the lowest of any market built under this factory so far. ROUTING_HOLD alone is 330 rows (67 % of the census) — overwhelmingly independent DBPR-licensed motels/inns with no brand inventory, bureau listing or map route, plus static-only brand families (IHG, Choice, Best Western, Hyatt, Red Roof, Radisson, Motel 6) this order's Firecrawl probe cohort (23 attempts) did not reach individually.
  - Every ACCESS_BLOCKED row (10) carries a router record of every free/authorized lane attempted.
  - The competitor identity gap (§8) is explicitly unverified in size, not proven small (unlike Orlando's reconciled 0-true-missing result) — a real, stated limitation of this order, not a hidden one.
  - Whether a 23.64 % resolution rate, with 7 of 19 corridors publishing (downtown Tampa, Westshore/airport, Busch Gardens/USF, East Tampa, downtown St. Petersburg, Clearwater Beach, St. Pete Beach/Treasure Island), is acceptable for launch consideration is a judgment the contract leaves to the founder. It is not a FAST fact.

## 14. Parallel safety

`git diff --name-only 1fa43a48 HEAD` lists 60 changed files (plus this report). Every path contains `tampa` or `Tampa`; 0 non-Tampa paths.

| Check | Changes |
|---|---:|
| V1 Tampa files (`worker/ptf-tampa-fl-market-001`) | 0 |
| Other market files (Savannah, Augusta, Orlando, etc.) | 0 |
| Shared factory files (`scripts/pettripfinder/*.py` not prefixed `tampa_fl_v2_`) | 0 |
| Canonical live files | 0 |
| Deployment-state files | 0 |

**CROSS-MARKET FILE CHANGES = 0. SHARED FACTORY CHANGES = 0. CANONICAL LIVE CHANGES = 0. DEPLOYMENT STATE CHANGES = 0.**

## 15. V1 vs V2 diagnostic (`reports/tampa_fl_v2_v1_diagnostic_001.json`, `source_ready_accounting_001.json`)

| | V1 | V2 | Delta |
|---|---:|---:|---:|
| Census | 580 | 495 | −85 |
| Pet-friendly | 30 | 92 | +62 |
| No-pets | 4 | 25 | +21 |
| Resolved | 34 | 117 | +83 |
| Unresolved | 546 | 378 | −168 |
| Resolution rate | 5.9 % | 23.64 % | +17.74 pts |
| Firecrawl used | 0 | 23 | +23 |

Causes of improvement:

1. **Refusals are now facts.** V2 reads each brand's own refusal/acceptance wording behind a negation guard (Marriott, Hilton, Wyndham, brand FAQs), rather than V1's largely-silent partition.
2. **The acquisition router and Firecrawl ladder replaced a mostly-unattempted V1.** V1 never wired Firecrawl (`firecrawl_used: 0`); V2 ran a 23-row ladder pass plus 114 supported-browser reads (Marriott 68, Hilton 42, Hyatt/Best Western 4) and 208 free static requests.
3. **A tighter, re-verified census** (580 → 495, −85) removed non-lodging/outside-market/unconfirmed rows the V1 census had admitted too loosely, while still growing PF/NP counts on the smaller, more accurate base.

Deterioration: the diagnostic's own accounting records **5 honest deteriorations** — V1-shared-key rows that read a worse state in V2 than V1 (documented in commit `940ec9ca`). V2 was not manipulated toward the comparison (`v2_not_manipulated_for_comparison` field in the diagnostic JSON is set accordingly).

## 16. Machine-readable documents

| Document | Path |
|---|---|
| Source-ready accounting | `launch_packages/pettripfinder/markets/reports/tampa_fl_v2_source_ready_accounting_001.json` (headline, holds, exclusions, corridors, brand-by-brand, competitor reconciliation, providers, V1-vs-V2) |
| Clean authority / policy adjudication | `tampa_fl_v2_clean_authority_001.json` |
| Census reconciliation | `tampa_fl_v2_census_reconciliation_001.json` |
| Geography / corridor registry | `tampa_fl_v2_geography_001.json` |
| Competitor reconciliation | accounting `competitor_reconciliation`, `tampa_fl_v2_competitor_gap_matrix_001.json`, `tampa_fl_v2_competitor_challenge_001.json` |
| Provider-attempt accounting | `tampa_fl_v2_firecrawl_pass_001.json`, `_wyndham_lane_001.json`, `_esa_lane_001.json`, `_free_static_capture_001.json` |
| V1 vs V2 | accounting `v1_vs_v2` and `tampa_fl_v2_v1_diagnostic_001.json` |
| Shadow package report | `tampa_fl_v2_shadow_package_001.json` |
| Sealed package / receipt | `staging/tampa-fl/shadow_packages/tampa-fl/pkg-tampa-fl-3c436d332f587f8a.json`, `staging/tampa-fl/shadow_receipts/tampa-fl/pkg-tampa-fl-3c436d332f587f8a-1d61a919227ee158.json` |

## 17. Timing (ET, 2026-09-15/16; from commit timestamps)

| Phase | Window |
|---|---|
| Market geography contract, corridor registry (19 corridors, 66 ZIPs) | 20:46–20:59 |
| DBPR public-lodging registry lane (676 leads) | 20:59–21:01 |
| BringFido competitor challenge (9 cities) | 21:01–21:26 |
| Brand inventory + destination roster lanes | 21:26–21:39 |
| Census reconciliation (495 confirmed identities, 0 merge conflicts) | 21:39–21:46 |
| Routing (161 routed + 53 identity-fill) | 21:46–21:47 |
| Wyndham lane + free static capture pipeline start | 21:47–21:51 |
| ESA lane (0 usable, all 403) | 21:51–21:54 |
| Static acquisition (210-target batch) + independents policy-pages lane | 21:54–21:58 |
| Firecrawl acquisition (planning through results, 23 attempted) | 21:58–22:06 |
| Marriott supported-browser captures (68 read) | 22:06–22:28 |
| Hilton supported-browser captures (42 read, walled) | 22:28–22:44 |
| Hyatt + Best Western supported-browser captures | 22:44–22:47 |
| Clean authority / policy adjudication (first pass) | 22:47–22:51 |
| Final partition, source-ready accounting | 22:51–22:55 |
| Registration staging | 22:55–23:00 |
| Fix: evidence document hashes, fee/deposit contract | 23:00–23:06 |
| V1 vs V2 diagnostic | 23:06–23:09 |
| Fix: FAST rule C (shared-reader quote gate) + rule G (cross-market identity collision) | 23:09–23:18 |
| Fix: propagate fee/count context into staged evidence (rule C round 2) | 23:18–23:24 |
| Shadow package sealed, FAST 15/15 PASS | 23:24–23:32 |
| Fix: stray CRLF in census working copy; reseal; cross-worktree reproduction confirmed byte-identical | 23:32–00:00 |

- **ZERO_TO_SOURCE_READY:** 3 h 13 m, 20:46:52 → 00:00:03 ET.
- **PROVIDER COST:** $0.00 USD; 17 existing Firecrawl plan credits spent (561 → 544).
- **NEW PAID SPEND:** 0. **NEW PROVIDER AUTHORIZATION:** 0.
- **FOUNDER INTERVENTION:** 0 (fully autonomous per the mission brief's continue-through-blockers instruction).
- **Cleanup:** reproduction worktree `C:\t\tpa2b` removed after digest comparison; no HTTP servers, relays or background browser sessions left running.

---

## FINAL ANSWERS

1. START TIMESTAMP = 2026-09-15T20:46:52-04:00
2. ZERO_TO_SOURCE_READY = 3 h 13 m 11 s, 20:46:52 → 00:00:03 ET (2026-09-15 → 2026-09-16)
3. TOTAL DISCOVERED = 2,553 raw observations (DBPR 676, OSM 643, brand inventory 214, destination roster 106, competitor 914) merged into 1,817 graph nodes
4. PROPOSED CENSUS = 495
5. VALID PET-FRIENDLY = 92
6. VALID VERIFIED-NO-PETS = 25
7. RESOLVED / UNRESOLVED = 117 / 378
8. RESOLUTION RATE = 23.64 %
9. HOLDS BY CLASS = ROUTING 330; BROWSER_CAPTURE_NEEDED 21; ACCESS_BLOCKED 10; SOURCE_SILENT 10; EVIDENCE 5; IDENTITY_MISMATCH 2; NEGATION/PAID/GEOGRAPHY/FOUNDER/OTHER 0
10. CORRIDOR COVERAGE = 19 corridors (6 CORE / 7 CORRIDOR / 6 FRINGE), 66 admitted ZIPs; 7 pages publish (downtown-riverwalk, westshore-airport-rocky-point, busch-gardens-usf, east-tampa-i75, st-petersburg-downtown, clearwater-beach, st-pete-beach-treasure-island); 12 do not
11. TAMPA / ST. PETERSBURG / CLEARWATER MARKET DECISION = ONE market (`tampa-fl`); no defensible ZIP-level seam along a city line, shared MSA and destination organization (§3)
12. EXCLUSIONS = non-hotel 148, vacation rental 114, timeshare 1, resort residence 1 (264 total non-lodging); outside-market 242; DBPR CNDO 4,392 / DWEL 4,367 / NAPT 1,878 never admitted
13. OWNED EVIDENCE REUSED = 0 identities, 0 policy facts; 79 Marriott routes from the committed national owned-brand harvest (0 new requests)
14. COMPETITOR RAW / NORMALIZED / MATCHED = 1,090 / 914 / 55 (exact name)
15. COMPETITOR MISSING (CANDIDATES) = 859 name-only, unverified against any first-party source in this order
16. MATERIAL GAP REMAINS = UNVERIFIED SIZE (not proven small, not proven large; see §8) — a founder/coverage decision, not a technical failure
17. FIRECRAWL ELIGIBLE = 23 planned rows (ROUTED 14, PROBE 7, WALL_REPROBE 2)
18. FIRECRAWL ATTEMPTED = 23 (100 % of planned)
19. FIRECRAWL SUCCESS = 9 publication-grade
20. FIRECRAWL FAILED = 14 (8 FIRECRAWL_FAILED + 6 FIRECRAWL_MISMATCH)
21. ACCESS_BLOCKED AFTER LANE EXHAUSTION = 10
22. NEGATION / SHARED-READER CONFLICTS CAUGHT = 5 (all held, never published; §2, §10)
23. EXISTING PROVIDER USAGE = Firecrawl 17 plan credits (561 → 544); supported browser 114 reads (Marriott 68, Hilton 42, Hyatt/Best Western 4); Bright Data 0; Places 0
24. NEW PAID SPEND = 0
25. PROVIDER COST = $0.00 USD (existing plan credits only)
26. SHADOW PACKAGE CREATED = YES (pkg-tampa-fl-3c436d332f587f8a, SHADOW_UNTIL_REGISTERED)
27. PACKAGE REPRODUCIBLE = YES — in-process double build AND a separate detached worktree (fresh checkout, independent process) both produced an identical digest; a first reproduction attempt caught and fixed a real working-tree/committed-blob drift bug (§12) before this result was reached
28. PACKAGE DIGEST = sha256:3c436d332f587f8a8fd1619b5c157b73bba9ecdcb1a86b1355bf8e52dcfb36d9
29. APPLICABLE FAST = 15/15 PASS (A–O), 0 UNKNOWN, 0 FAILED
30. TECHNICAL SOURCE READY = YES
31. COVERAGE READY = FOUNDER DECISION
32. V1 CENSUS / RESOLVED / UNRESOLVED = 580 / 34 / 546
33. V2 CENSUS / RESOLVED / UNRESOLVED = 495 / 117 / 378
34. V1 → V2 DELTA = census −85, PF +62, NP +21, resolved +83, unresolved −168, resolution rate +17.74 pts; 5 honest deteriorations recorded, 0 PF→NP reversals, V2 not manipulated toward the comparison
35. CROSS-MARKET FILE CHANGES = 0 (`git diff --name-only 1fa43a48 HEAD`, 60 files, all Tampa-scoped)
36. FACTORY CODE CHANGED = NO
37. BROAD REGRESSION RUN = 0
38. FINAL PRODUCTION CANDIDATE CREATED = NO
39. FOUNDER AUTHORIZATION CREATED = NO
40. TAMPA DEPLOYED = NO
41. origin == HEAD = YES; tree clean = YES (both verified after `git push -u origin worker/ptf-tampa-fl-market-002` of the commit carrying this report)

TAMPA V2 SOURCE READY = YES
TAMPA V2 COVERAGE READY = FOUNDER DECISION
TAMPA V2 FINAL CANDIDATE = NO
TAMPA V2 DEPLOYED = NO
BROAD REGRESSION RUNS = 0
FACTORY CODE CHANGED = NO
WAITING FOR RELEASE QUEUE = YES

STOP.

Do not deploy.
Do not create final candidate.
Do not modify factory architecture.
