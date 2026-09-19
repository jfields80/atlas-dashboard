# PTF-MIAMI-FL-HARDENED-SOURCE-READY-001 — FINAL

Market `miami-fl` — **Miami – Miami Beach / Greater Miami, Florida**.
Branch `worker/ptf-miami-fl-market-001`, worktree `C:\Atlas-Miami-FL-Hardened-V1`.
Base: the repaired release-factory lineage `0b6ad264` (PTF-RELEASE-FACTORY-INTEGRATION-006), **not** origin/main.

Miami was built from zero: no prior Miami market, census row, policy fact or evidence row exists or was imported.
Status: **SHADOW_UNTIL_REGISTERED**. Nothing was registered, participated, authorized, pinned or deployed.

---

## 1. Headline

| Metric | Value |
|---|---|
| Total raw observations (all lanes) | 3,640 |
| DBPR licensed-lodging leads | 1,396 (621 in admitted ZIPs, 775 in named refused ZIPs) |
| OSM lodging elements in the observation box | 1,316 |
| Brand-inventory leads | 284 · GMCVB roster listings 253 · BringFido normalized leads 660 |
| Graph nodes after hard-key identity merge | 2,334 (0 merge conflicts) |
| Proposed census (TRUE_HOTEL_IDENTITY) | **639** |
| Valid pet-friendly (CLEAN_PET_FRIENDLY) | **57** |
| Valid verified-no-pets (CLEAN_VERIFIED_NO_PETS) | **28** |
| Resolved / unresolved | **85 / 554** |
| Resolution rate | **13.30 %** |
| Package | `pkg-miami-fl-8f1ab3771880dd4e`, FAST **15/15 PASS**, reproduced byte-identically |

## 2. Phase 1 — factory lineage and CURRENT VERIFIED LIVE

`git merge-base --is-ancestor 0b6ad264 HEAD` → true; the branch carries the repaired live-source resolver,
the automatic registration classifier wiring, the release-store deployed-bundle correction and the reuse-staging
machinery. Live was resolved mechanically with the repaired resolver (`release_index live-source`), never assumed:

| | |
|---|---|
| CURRENT_LIVE_SOURCE_COMMIT | `96564199` (built_from `ff427c27`) |
| CURRENT LIVE DEPLOYMENT | `6aaeb3b7384e1bb712adb084` (augusta-ga) |
| CURRENT LIVE MARKETS / PROFILES / ROUTES | 30 / 2,165 / 2,477 |
| head_contains_live | true · `origin/main` reported **stale**, never used |

Live was read for context only; nothing in production was touched (§13).

## 3. Phases 2–4 — Greater Miami geography, the Miami / Miami Beach split test and the PortMiami cruise test

Contract: `miami_fl_geography_001.py` → 20 corridors over **79 admitted postal codes**, a strict postal-code
partition (9 CORE / 7 CORRIDOR / 4 FRINGE), 23 observation cells (20 admitting, 3 observation-only reaching
Broward and Key Largo).

- **Miami and Miami Beach are ONE market** — one airport, one county, one CVB (the GMCVB markets "Miami and the
  Beaches"), causeway-connected. Miami Beach nevertheless keeps a **distinct traveller identity**: three named
  CORE corridors on its own postal seams (South Beach 33139+33109, Mid-Beach 33140, North Beach 33141), never
  folded into generic Miami.
- **Downtown Miami and Brickell are one corridor** because ZIP 33131 straddles the Miami River (Brickell Avenue
  south, the Biscayne Boulevard Way / Chopin Plaza bayfront north). Downtown, Brickell and PortMiami are reported
  as street-and-pin overlays.
- **MIA splits on a real seam**: `mia-airport-miami-springs` (north side, NW 36th St / Miami Springs / Virginia
  Gardens) and `airport-west-blue-lagoon` (south side, Blue Lagoon / NW 7th St). **Doral is its own CORE corridor**
  even where its hotels market themselves as "Miami Airport West".
- **PortMiami cruise test: NO PortMiami corridor was created.** Dodge Island (33132) carries terminals, not
  hotels; cruise pre/post-stay demand sleeps in Downtown/Brickell, on the Beach and at MIA. A PortMiami corridor
  would claim exactly the ZIPs `downtown-brickell` already claims — a duplicate page, not a distinct cluster.
  Cruise intent is an overlay label only; it never changed premises identity or membership.
- Aventura, Sunny Isles Beach, Bal Harbour/Surfside, Key Biscayne, North Miami/NMB, Wynwood-Edgewater and Little
  Havana are named CORRIDOR tiers; Hialeah/Miami Lakes, Miami Gardens/Opa-locka, Kendall/South Dade and
  Homestead/Florida City are FRINGE, admitted at lower expected density.

## 4. Phase 5–6 — vacation rentals, condo-hotels and shared campuses

DBPR condominium (CNDO **9,446**), vacation-dwelling (DWEL **1,943**) and non-transient-apartment (NAPT **5,778**)
licences are counted and never enter the graph; 349 transient-apartment licences whose own name reads as an
apartment community were refused by name. Market-local rules added this order and applied on evidence, never on a
hunch: short-term-rental / serviced-apartment operators (Sonder, Kasa, Vacasa, Blueground, Mint House …), a
licence whose own name is a rental/management/realty **company**, and a licence whose own address is a **unit
inside a building** ("5445 Collins Ave Ste Cu14") are VACATION_RENTAL; a licence naming only an owning LLC is
IDENTITY_REVIEW, not a hotel.

**Dual-brand buildings are two hotels** (standing rule) and are HELD for the split, never published as one:
AC Hotel Miami Brickell & Element Miami Brickell (115 SW 8th St) and Eden Roc Miami Beach & Nobu Hotel Miami Beach
(4525 Collins Ave). The Nobu identity that the competitor-gap lane verified merged into that held row rather than
publishing half a building.

## 5. Phases 19–20 — holds by class (554, one disposition per row)

| Class | Rows | Exact root cause |
|---|---:|---|
| SOURCE_SILENT | 124 | the property's own page or site served, bound to the identity, and stated no operative pet policy (65 routed pages, 59 sites found via Places) |
| ROUTING | 126 | no first-party route: 93 NO_OFFICIAL_WEB_PRESENCE_FOUND (Places bound the building but no site, or no place at this row's own street number + ZIP), 41 OTHER_EXPLICIT_REASON (the site named is a brand/OTA host another lane owns) |
| BROWSER_CAPTURE | 116 | Marriott 57, Hilton 44, Hyatt 9, Best Western 7 — see §7 |
| ACCESS_BLOCKED | 113 | every free/authorized lane attempted was refused or failed (static + Firecrawl where the router made the row eligible) |
| IDENTITY | 38 | the fetched page or site never confirmed this row (21 Places-found sites, 17 routed pages) |
| EVIDENCE | 37 | fee/weight/count wording with no explicit acceptance (17), shared-reader disagreement (9+), route-domain conflict (2), ambiguous same-address evidence |
| NEGATION / POLICY_NOT_FOUND / MIXED_RESORT / CONDO_HOTEL / PAID / GEOGRAPHY / FOUNDER / OTHER | 0 | — |

Partition states: PUBLISHED_PET_FRIENDLY 57, VERIFIED_NO_PETS 28, AWAITING_OFFICIAL_URL 126,
AWAITING_ATTENDED_CAPTURE 116, AWAITING_POLICY_OBSERVATION 161, ACCESS_BLOCKED 113,
AWAITING_ROUTING_REPLACEMENT 38. The partition contract reported 0 issues; `uncorridored_rows` = 0.

## 6. Exclusions

| Class | Count |
|---|---:|
| Vacation rental | 79 | 
| Timeshare | 1 |
| Resort residence | 1 |
| Non-hotel | 128 |
| Closed | 0 (DBPR extracts carry only active licences; no read stated a closure) |
| Outside market | 920 |
| Duplicate listing | 1 |
| Graph residue: name-only unresolved 425, identity-review 138, same-campus-distinct 2 | — |

## 7. Phases 12–14 — the acquisition router, providers and the browser lanes

Every lane below is the CURRENT hardened router's own rung (`acquisition.ladder`, `acquisition/routes.json`); no
simplified substitute was invented.

| Lane | Result |
|---|---|
| Owned (rung 0) | 123 Marriott routes from the committed national harvest (`dayton_oh_brand_directory_harvest_001.json`), 0 new requests |
| Brand inventories (rung 2) | Marriott Florida sitemap page + Hilton's own Florida city pages answered; Wyndham / Loews / Sonesta / WoodSpring sitemaps answered; Choice and Motel 6 timed out, IHG / Best Western / Red Roof / Hyatt / Omni / Four Seasons / Radisson / Kimpton / Stayable answered **403** to this client — each refusal measured and recorded, never inherited |
| GMCVB roster | 253 hotel listings read from the bureau's own sitemap + listing JSON-LD (256 free requests) |
| Free static capture | 410 targets, 508 free requests across two passes, 20 VALID |
| Wyndham property service | 51 routes selected, 27 read, 24 retired |
| Extended Stay America | 7 property pages, 7 FAQ pet answers (Tampa's ESA lane was 403; Miami's answered) |
| Independents' own policy/FAQ pages | 214 sites, 137 bound on their own address/phone/JSON-LD, 422 free requests |
| Google Places route discovery (existing key) | 286 requests: 230 unrouted identities bound on **street number + ZIP**, 178 with a website; plus 13 competitor-gap verifications |
| Places-discovered sites | 126 read, 76 bound, 190 free requests |
| **Firecrawl** | **229 attempts** (116 first pass, 34 retry, 34 probe-2, 8 route-discovery pages, 37 brand property pages): 12 publication-grade property reads, 30 brand pages with their own address; **credits 1,525 → 1,346 (179), USD 0.00** |
| Bright Data / other paid providers | 0 |
| Supported browser | 5 attempts, **0 reads** — 1 Akamai challenge page (marriott.com), 4 extension read-permission refusals (marriott.com, hilton.com, hyatt.com, bestwestern.com) |

**FIRECRAWL ELIGIBLE 116 planned (first cohort) · ATTEMPTED 229 · SUCCESS 12 publication-grade + 30 brand-page
address reads · FAILED 138 (BLOCKED 54, FAILED 40, MISMATCH 33, SOURCE_SILENT 9, IDENTITY_ONLY 2).**

**The browser lane is this market's largest open lever and its blocker is exact.** The committed route table sends
Marriott and Hilton to the attended browser (Firecrawl is a *measured* capability wall for both — this order
re-probed one of each and both came back BLOCKED), and excludes Hyatt and Best Western from its paid lanes. The
supported browser could not read any of those four domains this session: marriott.com first served an Akamai
challenge page (not bypassed) and then, like hilton.com, hyatt.com and bestwestern.com, returned
`Permission denied for reading pages on this domain`. Every attempt is recorded with its URL, timestamp and
outcome in `raw_captures/browser_attempts.jsonl`. **Next action: grant the extension read permission for those
four domains and run a closure browser pass** — 116 rows (18 % of the census) wait on exactly that.

## 8. Phases 15–18 — evidence, policy and negation safety

Every published record cites the quote it rests on, with the artifact's sha256, its capture lane and method, and
the requested/final URL. Four defects were found and fixed *by the safety rules themselves*, before anything
published:

1. **FAST rule C** refused `pet_count_limit = 2` read from "up to 25 lbs" — the count reader now requires a pet
   noun after the number (Avalon Hotel).
2. **FAST rule C** refused a `$35` **amenity** fee published as a pet fee — facts are now read only from the part
   of a quote that names pets, and an amount whose own neighbourhood says amenity/resort/parking/tax is rejected
   (Cardozo South Beach).
3. **The package contract** caught a Staybridge page's policy attached to **Aloft Miami Doral**: both are house
   number 3265 in 33172 and the evidence index keyed on house number + ZIP alone. Evidence now binds on the shared
   `address_key` over the canonical street, and two different pages claiming one address publish **neither**.
4. **The package contract** caught two Wyndham-branded rows read on their own domains while the census routes them
   to the brand host (Dolce Miami Beach, Ramada Plaza Marco Polo Beach Resort) — both HELD, not published.

37 negation / shared-reader conflicts were caught and held (0 published against a disagreement), including a
Sagamore Hotel page this order's own reader took as acceptance while the shared reader would not read it as
operative. No acceptance was inferred from an amenity chip, a fee, a weight or a count; no refusal was inferred
from silence.

## 9. Phase 10 — competitor challenge and gap reconciliation (BringFido, identity only)

20 city pages challenged, 824 raw rows, **660 normalized unique leads**:

| Class | Count |
|---|---:|
| EXACT_ATLAS_MATCH / ALIAS / DUPLICATE | 147 / 57 / 78 (282 matched, 204 distinct census identities) |
| VACATION_RENTAL / CONDO_RESIDENCE / TIMESHARE / NON_HOTEL | 256 / 5 / 0 / 3 |
| OUTSIDE (Broward, Palm Beach, the Keys, other Florida cities BringFido's radius-widening pulled in) | 29 |
| REVIEW (a listing title that names no establishment) | 73 |
| **TRUE MISSING QUALIFYING** | **12** |
| MATCHED BUT POLICY UNRESOLVED | 170 |

The 12 true-missing candidates were each verified through an authoritative lane (Google Places, existing key):
**8 verified as real lodging at an admitted postal code**, 2 were already in the census by address/phone, 3 resolved
to addresses outside the market (Palm Beach, Ormond Beach, St. Augustine). Of the 8, one (Flow Hotel Miami) was a
genuine new identity and is admitted; four were already carried by the graph under a held/refused row (Eden Roc &
Nobu, Oceanside, PRAIA, Beachside/Seaside — the last excluded as an apartment-hotel); one was a hostel
(NON_LODGING by the geography's own rule) and one a Nomada-managed listing with no street.

**MATERIAL UNEXPLAINED GAP REMAINS = NO** at the identity level: every one of the 660 leads carries an exact class,
and the true-missing cohort was worked to zero unexplained rows. The POLICY gap (170 matched-but-unresolved) is
explained by the same §5/§7 root causes, dominated by the browser-lane block.

## 10. Phase 23 — South Florida boundary audit

| Area | Discovered (DBPR hotel-rank licences) | Admitted into Miami |
|---|---:|---:|
| Fort Lauderdale | 190 | 0 |
| Hollywood | 150 | 0 |
| Dania Beach | 40 | 0 |
| Hallandale Beach | 16 | 0 |
| Broward County (total) | 609 | 0 |
| West Palm Beach / Palm Beach County | 222 | 0 |
| Florida Keys (Monroe County) | 319 | 0 |

Graph nodes refused by place: Fort Lauderdale 221, Florida Keys 295, Hollywood 140, Dania Beach 40, West Palm /
Palm Beach 85, Hallandale 11. **MIAMI MARKET INCLUDED FROM THOSE AREAS = 0.** `fort-lauderdale-fl`,
`west-palm-beach-fl` and `florida-keys-fl` are preserved by name as future standalone markets. No silent sprawl.

## 11. Phase 22 — corridor coverage (20 corridors, 79 ZIPs; 3 publish)

| Corridor | Class | Census | PF | NP | Unres. | Page |
|---|---|---:|---:|---:|---:|---|
| downtown-brickell | CORE | 46 | 3 | 0 | 43 | no |
| south-beach | CORE | 202 | 16 | 7 | 179 | **yes** |
| mid-beach | CORE | 52 | 2 | 1 | 49 | no |
| north-beach | CORE | 28 | 3 | 1 | 24 | no |
| mia-airport-miami-springs | CORE | 45 | 9 | 7 | 29 | **yes** |
| airport-west-blue-lagoon | CORE | 30 | 3 | 1 | 26 | no |
| doral | CORE | 35 | 6 | 2 | 27 | **yes** |
| coral-gables | CORE | 29 | 0 | 0 | 29 | no |
| coconut-grove | CORE | 9 | 2 | 2 | 5 | no |
| midtown-wynwood-edgewater | CORRIDOR | 31 | 1 | 1 | 29 | no |
| little-havana | CORRIDOR | 11 | 0 | 0 | 11 | no |
| key-biscayne | CORRIDOR | 3 | 1 | 0 | 2 | no |
| bal-harbour-surfside | CORRIDOR | 16 | 2 | 2 | 12 | no |
| sunny-isles-beach | CORRIDOR | 9 | 1 | 0 | 8 | no |
| aventura | CORRIDOR | 7 | 0 | 0 | 7 | no |
| north-miami | CORRIDOR | 4 | 0 | 0 | 4 | no |
| hialeah-miami-lakes | FRINGE | 21 | 3 | 1 | 17 | no |
| miami-gardens-opa-locka | FRINGE | 4 | 0 | 0 | 4 | no |
| kendall-south-dade | FRINGE | 22 | 2 | 1 | 19 | no |
| homestead-florida-city | FRINGE | 35 | 3 | 2 | 30 | no |

A page publishes only where the existing threshold (5 verified pet-friendly hotels) is met mechanically. No thin
page was created, and none was created for a cruise or SEO keyword.

## 12. Phase 21 — brand-by-brand

| Family | Census | PF | NP | Unres. | Firecrawl att./ok | Browser needed | Access blocked |
|---|---:|---:|---:|---:|---|---:|---:|
| MARRIOTT | 70 | 5 | 1 | 64 | 7 / 0 | 56 | 4 |
| HILTON | 44 | 0 | 0 | 44 | 1 / 0 | 44 | 0 |
| IHG | 27 | 8 | 5 | 14 | 17 / 9 | 0 | 5 |
| WYNDHAM | 16 | 3 | 8 | 5 | 1 / 0 | 0 | 0 |
| CHOICE | 14 | 3 | 1 | 10 | 0 / 0 (read via the discovered-route brand-page lane) | 0 | 0 |
| HYATT | 9 | 0 | 0 | 9 | 0 / 0 (excluded brand) | 9 | 0 |
| BEST_WESTERN | 8 | 0 | 0 | 8 | 0 / 0 (excluded brand) | 7 | 0 |
| SONESTA | 6 | 6 | 0 | 0 | 0 / 0 | 0 | 0 |
| EXTENDED_STAY_AMERICA | 6 | 1 | 0 | 5 | 0 / 0 | 0 | 0 |
| ACCOR | 7 | 0 | 0 | 7 | 1 / 0 | 0 | 1 |
| FOUR_SEASONS / LOEWS / OMNI / RADISSON / RED_ROOF / MOTEL6 | 2 / 2 / 0 / 2 / 1 / 1 | 0 | 0 | all | 4 / 0 | 0 | 3 |
| LUXURY_INDEPENDENT | 22 | 3 | 0 | 19 | 5 / 0 | 0 | 4 |
| RESORT_INDEPENDENT | 5 | 1 | 0 | 4 | 2 / 0 | 0 | 2 |
| INDEPENDENT | 397 | 27 | 13 | 357 | 102 / 3 | 0 | 94 |

## 13. Phase 29 — parallel safety

`git diff --name-only 0b6ad264 HEAD` → **74 files, every one Miami-owned** (`miami`/`Miami`).

| Check | Changes |
|---|---:|
| CROSS-MARKET FILE CHANGES | **0** |
| SHARED FACTORY CODE CHANGES | **0** |
| CURRENT LIVE CHANGES | **0** |
| DEPLOYMENT STATE CHANGES | **0** |

Every helper added this order is prefixed `miami_fl_`; the only shared modules touched were *read*, never edited.

## 14. Phases 26–28 — shadow package, FAST and reproduction

| Item | Value |
|---|---|
| Source commit | `5a0241c30579dd6df09c53aa09558a93d8148e16` |
| Package | `pkg-miami-fl-8f1ab3771880dd4e` |
| PACKAGE DIGEST | `sha256:8f1ab3771880dd4e8773bf616bc816c0030ab009b9eced98ad428bd5308b4b7c` |
| Execution zone | SHADOW_UNTIL_REGISTERED |
| Receipt | `staging/miami-fl/shadow_receipts/miami-fl/pkg-miami-fl-8f1ab3771880dd4e-f219e23d6114a272.json` |
| FAST (A–O) | **15/15 PASS, 0 UNKNOWN, 0 FAILED**, `FAST_DATA_ONLY_RELEASE_ELIGIBLE = YES` |
| Declared public routes | 57 hotel profiles, 3 corridor pages, 1 comparison page, 280 `/go/` pages; 0 warnings, 0 broken links, 0 quality-gate failures |
| REPRODUCTION A | this worktree, sealed twice in-process: identical digest |
| REPRODUCTION B | detached worktree `C:\t\mia2b` at the same commit, independent process: `clean_authority`, `final_partition` and `registration_staging` re-run there **diffed byte-identical against the committed files** (`git status` clean), then resealed to the same digest |
| BYTE IDENTICAL | **YES** |

Three earlier seals were kept as honest history (`pkg-miami-fl-69fb0c53…`, `-cfdffb4d…`, `-706cc87c…`): each was
refused by FAST rule C or the package contract and each refusal is a fix recorded in §8.

## 15. Phase 25 — coverage readiness

- **TECHNICAL SOURCE READY = YES.** Deterministic, cross-worktree reproducible, FAST-clean, isolated, fully
  accounted: 639 = 85 resolved + 554 unresolved, one disposition per row, every hold carrying an exact reason.
- **COVERAGE READY = NO**, mechanically, and for one dominant reason that is *fixable and named*:
  - 116 rows (18 % of the census, including **all 44 Hilton and 56 of 70 Marriott** identities) sit in
    BROWSER_CAPTURE_NEEDED because the supported browser could not read marriott.com, hilton.com, hyatt.com or
    bestwestern.com this session (§7). Tampa's comparable build read 110 properties through that same lane; Miami
    read 0. Coral Gables (29 census rows, 0 resolved), Aventura, North Miami and Little Havana are unresolved
    largely for that reason.
  - The resolution rate is 13.30 %, below Tampa's source-ready 23.64 %, and only 3 of 20 corridors publish.
  - Everything else is bounded and explained: the competitor identity gap is reconciled to 0 unexplained rows
    (§9), the South Florida boundary is 0 admitted (§10), and every ACCESS_BLOCKED / ROUTING / SOURCE_SILENT row
    carries the exact lane that refused it.
  - The honest next order is small and specific: grant the browser extension read permission for those four
    domains, re-run the attended lane over the 116 held rows, and re-seal. That is a coverage-closure pass, not a
    rebuild.

## 16. Machine-readable documents

| Document | Path (under `atlas-dashboard/launch_packages/pettripfinder/`) |
|---|---|
| Source-ready accounting (headline, holds + exact sub-causes, exclusions, corridors, brand-by-brand, providers, competitor, **South Florida boundary**, root causes) | `markets/reports/miami_fl_source_ready_accounting_001.json` |
| Geography / corridor registry / split + cruise tests | `markets/reports/miami_fl_geography_001.json`, `miami_fl_corridor_registry_001.json` |
| Census reconciliation + competitor gap matrix | `markets/reports/miami_fl_census_reconciliation_001.json`, `miami_fl_competitor_gap_matrix_001.json` |
| Competitor reconciliation (per-lead class) | `markets/reports/miami_fl_competitor_reconciliation_001.json` |
| Provider accounting | `miami_fl_dbpr_lane_001.json`, `_osm_lane_001`, `_brand_inventory_001`, `_destination_roster_001`, `_routing_001`, `_free_static_capture_001`, `_wyndham_lane_001`, `_esa_lane_001`, `_places_route_discovery_001`, `_firecrawl_pass_001/002/003`, `_firecrawl_discovery_001`, `_brand_page_reads_001` |
| Policy adjudication | `markets/reports/miami_fl_clean_authority_001.json` |
| Final partition (one disposition per row) | `markets/staging/miami-fl/launch_package/miami_fl_final_partition_001.json` |
| Staged authority + policy package | `markets/staging/miami-fl/miami_fl_proposed_authority_001.json`, `launch_package/hotel_policy_facts_miami-fl.json` |
| Raw captures (durable evidence) | `markets/staging/miami-fl/raw_captures/` (`policy_pages_rows.json`, `closure_static_rows.json`, `brand_page_rows.json`, `wyndham_rows.json`, `esa_rows.json`, `browser_attempts.jsonl`) |
| Sealed package + receipt | `markets/staging/miami-fl/shadow_packages/miami-fl/pkg-miami-fl-8f1ab3771880dd4e.json`, `shadow_receipts/…` |

## 17. Phase 30 — timing, cost and cleanup

| Phase | Window (UTC, 2026-09-19) |
|---|---|
| Precheck, factory lineage, live resolution | 19:51–19:56 |
| Geography contract (20 corridors, 79 ZIPs) | 19:56–20:06 |
| DBPR registry lane (1,396 leads) | 20:06–20:08 |
| Brand inventories (359 requests) | 20:08–20:34 |
| OSM / Geofabrik lane (1,316 elements) | 20:10–20:21 |
| GMCVB roster (253 listings) | 20:24–20:33 |
| BringFido challenge (20 cities) | 20:26–20:33 |
| Census reconciliation (639 identities, 0 conflicts) + routing | 20:35–21:05 |
| Wyndham + ESA + independents' policy pages | 20:55–21:12 |
| Free static capture (410 targets) | 21:00–21:12 |
| Firecrawl pass 001 (116) | 21:14–21:39 |
| Places route discovery (286) + Places-site reads (126) | 21:20–21:45 |
| Firecrawl retry 002 (34, after the street restatement) | 21:45–21:47 |
| Firecrawl route discovery (8 pages) + brand page reads (37) | 21:50–22:04 |
| Firecrawl probe 003 (34) | 22:05–22:10 |
| Adjudication, partition, accounting, staging | 22:10–22:25 |
| Seal + FAST (four seals: three refused and fixed, one passed) | 22:15–22:40 |
| Reproduction B (clean worktree) + isolation proof | 22:40–22:50 |

- **ZERO_TO_SOURCE_READY: ≈ 3 h 05 m** (19:51:38Z → ~22:56Z).
- **PROVIDER COST: $0.00 USD.** Firecrawl plan credits 1,525 → 1,346 (**179** spent, live-read at both ends);
  Google Places 286 requests on the existing key; Bright Data 0; 1,656 free HTTP requests.
- **NEW PAID SPEND: 0. NEW PROVIDER AUTHORIZATION: 0. FOUNDER INTERVENTION: 0.**
- **Cleanup:** reproduction worktree `C:\t\mia2b` removed, scratch build dirs `C:\t\mia1` / `C:\t\mia2work`
  deleted, the browser tab closed, no background watcher, relay, HTTP server or child process left running.

---

## FINAL ANSWERS

1. **START TIMESTAMP** = 2026-09-19T19:51:38Z
2. **ZERO_TO_SOURCE_READY** = ≈ 3 h 05 m (19:51:38Z → ~22:56Z)
3. **TOTAL DISCOVERED** = 3,640 raw observations (DBPR 1,396 · OSM 1,027 in-box lodging rows from 1,316 elements · brand inventory 298 · GMCVB 253 · BringFido 660 · Places-verified 6) → 2,334 graph nodes
4. **PROPOSED CENSUS** = 639
5. **VALID PET-FRIENDLY** = 57
6. **VALID VERIFIED NO-PETS** = 28
7. **RESOLVED / UNRESOLVED** = 85 / 554
8. **RESOLUTION RATE** = 13.30 %
9. **HOLDS BY CLASS** = ROUTING 126 · SOURCE_SILENT 124 · BROWSER_CAPTURE 116 · ACCESS_BLOCKED 113 · IDENTITY 38 · EVIDENCE 37 · NEGATION 0 · POLICY_NOT_FOUND 0 · MIXED_RESORT 0 · CONDO_HOTEL 0 · PAID 0 · GEOGRAPHY 0 · FOUNDER 0 · OTHER 0
10. **CORRIDOR COVERAGE** = 20 corridors (9 CORE / 7 CORRIDOR / 4 FRINGE), 79 ZIPs; 3 pages publish (south-beach, mia-airport-miami-springs, doral); 17 do not
11. **MIAMI / MIAMI BEACH STRUCTURE** = ONE market; Miami Beach kept as three distinct CORE corridors (South Beach / Mid-Beach / North Beach), never flattened; Downtown+Brickell one corridor (ZIP 33131 straddles the river); MIA split north/south; Doral its own corridor; **no PortMiami corridor** (it would duplicate downtown-brickell)
12. **SOUTH FLORIDA BOUNDARY ACCOUNTING** = Fort Lauderdale 190 · Hollywood 150 · Dania Beach 40 · Hallandale 16 · Broward total 609 · West Palm/Palm Beach 222 · Florida Keys 319 discovered; **0 admitted into Miami**; fort-lauderdale-fl / west-palm-beach-fl / florida-keys-fl preserved
13. **VACATION RENTAL / TIMESHARE / RESIDENCE EXCLUSIONS** = 79 / 1 / 1 (plus non-hotel 128); DBPR CNDO 9,446 · DWEL 1,943 · NAPT 5,778 never admitted; 349 apartment-named TAPT licences refused
14. **OWNED EVIDENCE REUSED** = 0 identities, 0 policy facts; 123 Marriott routes from the committed national harvest and the committed Geofabrik Florida snapshot (0 new requests for either)
15. **COMPETITOR RAW / NORMALIZED / MATCHED / TRUE MISSING** = 824 / 660 / 282 (204 distinct identities) / 12 — all 12 verified: 8 real at an admitted ZIP (1 newly admitted, 4 already carried, 1 hostel, 1 apartment-hotel, 1 no street), 2 already in census, 3 outside
16. **MATERIAL COMPETITOR GAP REMAINS** = NO at identity level (0 unexplained leads); the policy gap (170 matched-but-unresolved) has the §5/§7 root causes
17. **FIRECRAWL ELIGIBLE** = 116 planned in the router-planned cohort (plus 34 retry, 34 probe-2, 8 discovery pages, 37 brand pages)
18. **FIRECRAWL ATTEMPTED** = 229
19. **FIRECRAWL SUCCESS** = 12 publication-grade property reads + 30 brand pages bound to their own address
20. **FIRECRAWL FAILED** = 138 (BLOCKED 54 · FAILED 40 · MISMATCH 33 · SOURCE_SILENT 9 · IDENTITY_ONLY 2)
21. **BROWSER LANE ATTEMPTED / SUCCESS** = 5 / 0 (1 Akamai challenge, 4 extension permission refusals; never bypassed)
22. **ACCESS_BLOCKED AFTER ROUTER EXHAUSTION** = 113
23. **NEGATION / PARSER CONFLICTS** = 37 caught and held; 0 published against a disagreement; 4 extraction/binding defects caught by FAST C and the package contract and fixed (§8)
24. **EXISTING PROVIDER USAGE** = Firecrawl 179 plan credits (1,525 → 1,346); Google Places 286 requests (existing key); supported browser 5 attempts; Bright Data 0
25. **NEW PAID SPEND** = 0
26. **PROVIDER COST** = $0.00 USD
27. **SHADOW PACKAGE CREATED** = YES — `pkg-miami-fl-8f1ab3771880dd4e`, SHADOW_UNTIL_REGISTERED
28. **PACKAGE REPRODUCIBLE** = YES — in-process double seal AND an independent detached worktree at the same commit (chain re-run byte-identical, digest identical)
29. **PACKAGE DIGEST** = `sha256:8f1ab3771880dd4e8773bf616bc816c0030ab009b9eced98ad428bd5308b4b7c`
30. **APPLICABLE FAST** = 15/15 PASS (A–O), 0 UNKNOWN, 0 FAILED
31. **TECHNICAL SOURCE READY** = YES
32. **COVERAGE READY** = NO — one named, fixable blocker holds 116 rows (§15)
33. **CROSS-MARKET FILE CHANGES** = 0
34. **FACTORY CODE CHANGED** = NO
35. **BROAD REGRESSION RUN** = 0
36. **FINAL PRODUCTION CANDIDATE CREATED** = NO
37. **FOUNDER AUTHORIZATION CREATED** = NO
38. **MIAMI DEPLOYED** = NO
39. **origin == HEAD** = YES (verified after push, below)
40. **tree clean** = YES (verified after push, below)

MIAMI SOURCE READY = YES
MIAMI COVERAGE READY = NO
MIAMI FINAL CANDIDATE = NO
MIAMI DEPLOYED = NO
BROAD REGRESSION RUNS = 0
FACTORY CODE CHANGED = NO
WAITING FOR RELEASE QUEUE = YES

STOP.

Do not deploy.
Do not create final candidate.
Do not modify factory architecture.
