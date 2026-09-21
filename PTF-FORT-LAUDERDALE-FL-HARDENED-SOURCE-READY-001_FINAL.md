# PTF-FORT-LAUDERDALE-FL-HARDENED-SOURCE-READY-001 — FINAL

Market `fort-lauderdale-fl` — **Fort Lauderdale / Greater Broward County, Florida**.
Branch `worker/ptf-fort-lauderdale-fl-market-001`, worktree `C:\Atlas-Fort-Lauderdale-FL-Hardened-V1`.
Base: the repaired release-factory lineage `0b6ad264` (PTF-RELEASE-FACTORY-INTEGRATION-006), **not** origin/main,
which the resolver reported **stale**.

Built from zero: no prior Fort Lauderdale market, census row, policy fact or evidence row existed. Miami's build
was read for **discovery intelligence only** (§3); no Miami policy row was imported.

Status: **SHADOW_UNTIL_REGISTERED**. Nothing registered, participated, authorized, pinned or deployed.

---

## 1. Headline

| Metric | Value |
|---|---|
| Raw observations (11 lanes) | 3,466 |
| Florida DBPR licensed-lodging leads | 1,512 (454 in admitted ZIPs, 1,058 in named refused ZIPs) |
| OSM lodging elements in the observation box | 548 |
| Brand-inventory leads · Visit Lauderdale roster · BringFido normalized | 186 · 376 · 921 |
| Graph nodes after hard-key identity merge | 2,558 (**0 merge conflicts**) |
| Proposed census (TRUE_HOTEL_IDENTITY) | **460** |
| Valid pet-friendly (CLEAN_PET_FRIENDLY) | **85** |
| Valid verified-no-pets (CLEAN_VERIFIED_NO_PETS) | **53** |
| Resolved / unresolved | **138 / 322** |
| Resolution rate | **30.00 %** |
| **ACTIONABLE unresolved** | **0** |
| Package | `pkg-fort-lauderdale-fl-69b617cd4c8b6ba9`, FAST **15/15 PASS**, reproduced byte-identically |

For scale: Miami's comparable source-ready state was 13.30 %, Tampa V2's 23.64 %. The difference is §7 — the
attended browser read 81 first-party brand pages here and 0 in Miami.

## 2. Phase 1 — factory lineage and CURRENT VERIFIED LIVE

`git merge-base --is-ancestor 0b6ad264 HEAD` → true. Live was resolved **mechanically** with the repaired
resolver (`release_index live-source --fetch --verify-host`), never assumed:

| | |
|---|---|
| CURRENT_LIVE_SOURCE_COMMIT | `fbaf6f73a8e4ed7fa5cf3d81588219d513743bcd` (built_from `95d23162`) |
| CURRENT LIVE DEPLOYMENT | `6ab071a5b7561c33aff6c17b` (miami-fl) |
| CURRENT LIVE BUNDLE SHA | `b2ad54b9be8b8a0121b8b664ef95e6d4dcf3feb873b4b23558c3721cdc06732a` |
| CURRENT LIVE SITEMAP SHA | `5ac34c75d6ba22d87b5da9d9ff40844dc2e986d7b778760849c03769bb088980` |
| CURRENT LIVE MARKETS / PROFILES / ROUTES | **31 / 2,290 / 2,614** |
| head_contains_live · origin_main_stale · **HOST VERIFIED** | true · true (never used) · **true** |

Live was read for context only; nothing in production was touched (§13).

## 3. Phase 2 — Miami's Broward discovery intelligence, reused as intelligence

Miami drew its observation box north over the county line deliberately. `fort_lauderdale_fl_miami_reuse_001`
reads Miami's committed graph and hands this market a prior-discovery index:

| | |
|---|---|
| MIAMI-DISCOVERED BROWARD IDENTITIES REUSED | **499** (445 with a DBPR licence, 196 with coordinates, 68 with an official URL, 60 with a brand property code) |
| MIAMI DISCOVERY COLLISIONS / STALE | 10 prior rulings carried as EVIDENCE, none binding here |
| **MIAMI POLICY EVIDENCE IMPORTED** | **0** — every Broward row in Miami's graph is `POLICY_NOT_VERIFIED`, which the helper asserts |
| NEW BROWARD IDENTITIES DISCOVERED | 2,059 of the 2,558 graph nodes were not in Miami's Broward cohort |

Membership was re-decided here for every row by this market's own corridor registry. Miami's `OUTSIDE_MARKET`
ruling is provenance, never an admission.

## 4. Phases 3–4 — Broward geography and the structure test

`fort_lauderdale_fl_geography_001` → **18 corridors over 53 admitted postal codes**, a strict postal-code
partition (9 CORE / 5 CORRIDOR / 4 FRINGE), 20 observation cells (18 admitting, 2 observation-only reaching
Aventura/Sunny Isles and Boca Raton).

Broward's defining property is that **its postal codes straddle municipalities**, which the state's own registry
shows directly: 33308 carries Fort Lauderdale's Galt Ocean Mile *and* Lauderdale-by-the-Sea *and* Sea Ranch
Lakes; 33305 / 33311 / 33334 each carry Fort Lauderdale *and* Wilton Manors; 33064 carries Lighthouse Point,
Pompano Beach *and* Deerfield Beach; 33312 carries Fort Lauderdale *and* Dania Beach. A corridor therefore covers
a shared code **whole** and reports its named places as street-and-pin overlays. It never splits a ZIP, because a
split ZIP is a judgement applied per property — exactly what the registry exists to forbid.

Structure test, recorded in full in the report: Downtown/Las Olas, Fort Lauderdale Beach, Port Everglades/17th
Street, FLL/SR-84, Dania Beach, Hollywood Beach, Hollywood, Plantation/Davie and Hallandale Beach are CORE.
Hollywood and Hollywood Beach are **separate CORE corridors** — 33019 is the densest lodging code in the county
(2,041 licences of all ranks) and a distinct beach system. Pompano Beach and Deerfield Beach are CORRIDOR tiers
with their own piers and A1A rows. Sunrise/Tamarac/Lauderhill, Weston/Southwest Ranches, Pembroke
Pines/Miramar and Coral Springs/Coconut Creek are FRINGE.

## 5. Phase 5 — the Port Everglades cruise test: a corridor IS created

**The opposite of the PortMiami finding, and for a mechanical reason.** PortMiami sits on Dodge Island (33132),
which carries terminals and no hotels, so a port corridor there would have duplicated `downtown-brickell`'s
postal codes. **Port Everglades sits inside a postal code that is full of hotels.** ZIP 33316 carries 32 DBPR
hotel-rank licences (734 lodging licences of all ranks): the port's own gates, the 17th Street Causeway hotel
wall (Embassy Suites, Hilton Fort Lauderdale Marina, Pier Sixty-Six, Omni, Hyatt Place Cruise Port, Holiday Inn
Express Cruise Port, Crowne Plaza and Four Points "Airport & Cruise"), the Broward County Convention Center,
Harbor Beach (Marriott Harbor Beach, Lago Mar) and the Bahia Mar / Seabreeze Boulevard south beach strip.

It passes every test the order sets — density, coherent traveller intent, and **not duplicate inventory**,
because the registry is a partition and 33316 is claimed by this corridor and nothing else. It publishes at
5 pet-friendly and 8 verified-no-pets, a 41.9 % resolution rate — the second-highest CORE corridor.

**FLL Airport gets no corridor: the airport owns no postal code.** Its hotel district splits on a real seam —
the south side (Stirling Road, SW 18th Avenue / 19th Court, North Compass Way, eastern Griffin Road) is Dania
Beach 33004; the north and west side (State Road 84 / Marina Mile, Maritime Boulevard, Anglers Avenue) is
33312 / 33315. "FLL Airport" is a street-and-pin overlay across both.

## 6. Phase 6 — beach, resort and condo-hotel safety

Broward carries **4,569 DBPR condominium (CNDO)** and **6,234 vacation-dwelling (DWEL)** licences against just
**427 hotel/motel/B&B** licences, plus 2,347 non-transient apartments. None enters the graph. A further 367
transient-apartment licences whose own name reads as an apartment community were refused by name.

One Broward-specific correction was needed and made: the county's vintage beachfront motels are licensed MOTL and
named "*… Apartment Motel*" (Premiere, Sea Downs, High Noon). The apartment rule now never fires on a name that
also states hotel / motel / inn / resort / hostel — those are public lodging on the state's own record.

**TIMESHARE, proved first-party.** Marriott's BeachPlace Towers (21 S Fort Lauderdale Beach Blvd, MARSHA `fllbp`)
was in the census until the attended browser read the brand's own page, which names the premises
"MARRIOTT'S BEACHPLACE TOWERS, A MARRIOTT VACATION CLUB® RESORT" and carries an Ownership section. It is excluded
as TIMESHARE **before** any policy applies — and its page's "Pets Not Allowed" line is recorded as history and
published nowhere, because an excluded row publishes nothing, not even a refusal. Visit Lauderdale files it under
Beach / Waterfront / Cruise Hotels; the bureau's classification did not decide it, the brand's own page did.

## 7. Phases 14–16 — the attended-browser lane, which is this market's whole margin

The committed route table sends **MARRIOTT** and **HILTON** to a paid browser provider and **excludes HYATT and
BEST_WESTERN** from its paid lanes on cost. This order has no authorization for new paid spend, so the lane it
exercised is the **supported attended browser** — navigate to the property's own page on the brand's own host and
read the page's own accessibility tree.

| | |
|---|---|
| ATTEMPTS | **90** (Marriott 42, Hilton 37, Hyatt 5, Best Western 6) |
| PUBLICATION-GRADE READS | **81** (Marriott 40, Hilton 33, Hyatt 4, Best Western 4) |
| CHALLENGE DENIED (terminal) | **1** |
| UNBOUND READS | **0** |
| PAID PROVIDER CALLS · Bright Data | **0** · not used |
| AKAMAI BYPASSED · BROWSER-JS EXFILTRATION · LOCAL RELAY | **false · false · false** |

**Pacing was measured, not guessed.** Marriott's Akamai allowed ~13–15 reads, then served Access Denied until
roughly five minutes of total inactivity had passed; each denial hardened the block, so the lane never retried
inside a window. Every attempt, its timestamp and its outcome are in
`raw_captures/browser_reads_001.jsonl` (90 rows) and `raw_captures/browser_closure_rows.json`.

**Evidence is durable, not ephemeral.** Each accepted read records the requested and final URL, the capture
method, the provider, the timestamp, the page title, the page's own address line, the census premises it was
matched to, the full-premises verdict, the operative quote, its byte length, a transcription sha256 over the
whole record, the parsed facts and the source class.

Quotes are in each brand's own label vocabulary. Hilton's PETS block labels ("Pets allowed: Yes",
"Non-refundable fee: $75.00", "Max weight: 75 lbs", "Pet policy: …") were verified **verbatim by a full
page-text read on two properties** (`fllbmdt` Bahia Mar and `fllcyhx` Hampton Cypress Creek) before any row was
composed from them; every other row's values are that property's own.

Four route repairs came out of it — `doubletree3.hilton.com`, `hamptoninn3.hilton.com`, `embassyflorida.com`,
`sheratonsuitesplantation.com` and `westinfortlauderdalehotel.com` are dead or non-property hosts the census
carried; the live routes came from the brands' own inventories.

## 8. Phases 12–13 — the rest of the router

| Lane | Result |
|---|---|
| Owned (rung 0) | 52 Marriott routes from the committed national harvest, 0 new requests |
| Brand inventories (rung 2) | Marriott's Florida sitemap page and Hilton's own Florida city pages answered; Wyndham / Sonesta / WoodSpring sitemaps answered; ESA, IHG, Best Western, Red Roof, Hyatt, Omni, Four Seasons, Radisson, Kimpton and Stayable answered **403**; Choice and Motel 6 timed out — each refusal measured, never inherited |
| **Visit Lauderdale (Broward's own CVB)** | **376 of 376** lodging listings, 370 in admitted codes, **360 with a website** — 81 free requests at the bureau's own crawl delay |
| Free static capture | 351 targets, 5 VALID + 4 text-bound reads; 147 ACCESS_DENIED |
| Wyndham property service | 38 routes selected, 26 read, 12 retired |
| Extended Stay America | 10 routes, 2 served (8 × 403), 2 FAQ pet answers |
| Independents' own policy / FAQ pages | 219 targets, 118 bound on their own address or phone, 56 with pet sentences, 353 free requests |
| Google Places route discovery (existing key) | **174 requests**: 124 of 151 unrouted rows bound on **street number + ZIP**, 83 with a website; plus 23 gap verifications |
| Places-discovered sites | 56 read, 37 bound, 104 free requests |
| **Firecrawl** | **143 attempts** (112 property pages, 8 route-discovery pages, 23 brand property pages): 4 publication-grade reads, 66 brand routes discovered, 21 brand pages with their own address. **Credits 1,346 → 1,235 (111), USD 0.00, no new plan, no new credits** |
| Bright Data / any other paid provider | **0** |

**FIRECRAWL ELIGIBLE 112 planned · ATTEMPTED 143 · PUBLICATION-GRADE 4 · FAILED 108** (36 BLOCKED, 46 FAILED,
26 MISMATCH). Broward's independents are a measured wall for it.

## 9. Phases 17–18 — policy safety, and four defects the rules caught

No acceptance was inferred from an amenity chip, a fee, a weight or a count; no refusal from silence. 35 negation
/ shared-reader conflicts were caught and held. Four defects were found **by the safety rules themselves**, each
before anything published:

1. **A stale DOM nearly published one hotel's address as another's.** The Signia Diplomat read came back
   carrying Hotel Dello's address (28 S Federal Hwy 33004) instead of 3555 S Ocean Dr 33019. A route/premises
   mismatch is never valid evidence (Phase 11 rule 9) — the read was discarded, not repaired.
2. **One artifact, many premises.** The package contract refused the first seal: `sha256:758c4a0c` was the only
   policy evidence for *both* Richard's Motel (1219 S Federal Hwy) and Richard's Motel Courtyard (922 S 17th
   Ave). Hollywood's Richard's family of lodgings runs six licensed buildings behind one landing page whose
   "Pet Friendly" text is the *name of one of its properties in a navigation list*. The authority now holds every
   row that shares its only artifact with another premises — the inverse of the Miami rule that two pages
   claiming one address publish neither.
3. **A dual-brand building folded into one profile.** FAST rule J refused the build: *"missing hotel profile file
   for Tru by Hilton Fort Lauderdale Downtown"*, 2 broken internal links. See §10.
4. **Three rows the browser HAD read were still labelled AWAITING_ATTENDED_CAPTURE** because this market's own
   browser outcomes had no mapping — the exact mislabel Phase 11 rule 7 forbids. They are SOURCE_SILENT.

Two smaller identity corrections: Lauderdale-by-the-Sea's independents "Courtyard Villa" and "Blue Seas
Courtyard", and Hollywood's "Richard's Motel Courtyard", were being routed into the Marriott brand lane by a bare
`courtyard` pattern — on this coast the word is a building type. And **State Road 84 is one street**: the DBPR
writes "SR 84" where the brands write "State Road 84", which built two address keys for one building and stopped
IHG's own property-page reads reaching the licence rows they belonged to. Folding it recovered 3 published rows.

## 10. Dual-brand buildings — held, with the split already proved

Broward has two, each proved distinct by **two brand property codes and two first-party pages read this order**:

| Premises | Identities | Codes |
|---|---|---|
| 315 NW 1st Avenue, Fort Lauderdale 33301 | Tru by Hilton + Home2 Suites (DBPR licenses it once, as "FORT LAUDERDALE TRU/HOMES2") | `fllruru` + `fllhtht` |
| 200 North Ocean Blvd, Pompano Beach 33062 | Home2 Suites + Tru by Hilton | `fllprht` + `fllppru` |

The site generator silently folded the first pair into one profile (both census rows are named "Tru by Hilton
Fort Lauderdale Downtown…"); the second pair survived only because its two street strings differ — an
inconsistency, not a safeguard. Publishing two identities at one address requires a committed
`same_campus_distinct_entity` row in the **shared** `identity_resolutions.json`, which this order is not
authorized to write. The order's own rule settles it: founder intervention is required only where a decision
*"cannot safely be represented as a hold"*, and this one can. **All four halves are HELD**, each hold reason names
the exact resolution a registration order should add, and no shared file was touched.

## 11. Phases 19–20 — one disposition per row (322 unresolved)

| Class | Rows | Exact root cause |
|---|---:|---|
| ROUTING | 89 | no first-party route: no brand, bureau or map website, no Places result at the row's own street number + ZIP, or only a brand/OTA host another lane owns, or a dead vanity domain |
| ACCESS_BLOCKED | 89 | every free/authorized lane attempted was refused (static plain client, and Firecrawl where the router made the row eligible) |
| SOURCE_SILENT | 69 | the property's own page or site served, bound to the identity, and stated no operative pet policy |
| IDENTITY | 38 | the page never bound these premises, or two census rows share one premises (§10) |
| EVIDENCE | 37 | fee/weight/count with no acceptance sentence, shared-reader disagreement, or one artifact bound to two premises |
| **BROWSER_CAPTURE** | **0** | every browser-required row is read or terminally classified |
| NEGATION / POLICY_NOT_FOUND / MIXED_RESORT / CONDO_HOTEL / PAID / GEOGRAPHY / FOUNDER / OTHER | 0 | — |

Partition states: PUBLISHED_PET_FRIENDLY 85, VERIFIED_NO_PETS 53, AWAITING_OFFICIAL_URL 89,
AWAITING_POLICY_OBSERVATION 106, ACCESS_BLOCKED 89, AWAITING_ROUTING_REPLACEMENT 38.
The partition contract reported **0 issues**; `uncorridored_rows` = 0.

**Exclusions**: vacation rental 103 · timeshare 3 · resort residence 0 · non-hotel 143 · closed 0 · outside
market 1,087 · duplicate listing 3 · same-campus-distinct 12. Graph residue: name-only unresolved 598,
identity-review 149. Never admitted at all: 4,526 CNDO, 6,195 DWEL, 2,347 NAPT, 367 apartment-named TAPT.
No row was classified CLOSED — DBPR extracts carry only active licences and no read stated a closure.

## 12. Phase 21 — actionability

| Class | Total | Actionable now | Router exhausted | New provider | New spend | Founder |
|---|---:|---:|---:|---:|---:|---:|
| ROUTING_HOLD | 89 | **0** | 89 | 0 | 0 | 0 |
| ACCESS_BLOCKED | 89 | **0** | 89 | 0 | 0 | 0 |
| SOURCE_SILENT | 69 | **0** | 69 | 0 | 0 | 0 |
| IDENTITY_MISMATCH_HOLD | 38 | **0** | 0 | 0 | 0 | 38 |
| EVIDENCE_HOLD | 37 | **0** | 0 | 0 | 0 | 37 |
| **TOTAL** | **322** | **0** | 247 | 0 | 0 | 75 |

**ACTIONABLE UNRESOLVED REMAINING = 0.** MATERIAL COVERAGE RISK = none.

## 13. Phase 22 — brand by brand

| Family | Census | PF | NP | Unres. | Firecrawl att./ok | Browser att./read/denied | Blocked |
|---|---:|---:|---:|---:|---|---|---:|
| MARRIOTT | 44 | 27 | 14 | 3 | 3 / 0 | **42 / 40 / 1** | 2 |
| HILTON | 35 | 25 | 2 | 8 | 1 / 0 | **37 / 33 / 0** | 0 |
| WYNDHAM | 22 | 10 | 3 | 9 | 13 / 2 | 0 | 4 |
| IHG | 15 | 5 | 9 | 1 | 5 / 2 | 0 | 1 |
| CHOICE | 15 | 4 | 0 | 11 | 0 / 0 | 0 | 4 |
| EXTENDED_STAY_AMERICA | 10 | 0 | 0 | 10 | 0 / 0 | 0 | 4 |
| BEST_WESTERN | 6 | 0 | 4 | 2 | 0 / 0 | **6 / 4 / 0** | 0 |
| HYATT | 5 | 3 | 0 | 2 | 0 / 0 | **5 / 4 / 0** | 0 |
| SONESTA | 3 | 0 | 0 | 3 | 0 / 0 | 0 | 0 |
| MOTEL6 / STUDIO6 | 2 | 0 | 0 | 2 | 2 / 0 | 0 | 2 |
| ACCOR / FOUR_SEASONS / OMNI / RED_ROOF | 1 / 1 / 1 / 1 | 0 | 0 | all | 2 / 0 | 0 | 2 |
| RESORT_INDEPENDENT | 46 | 1 | 6 | 39 | 14 / 0 | 0 | 14 |
| LUXURY_INDEPENDENT | 15 | 1 | 1 | 13 | 5 / 0 | 0 | 4 |
| INDEPENDENT | 238 | 9 | 14 | 215 | 48 / 0 | 0 | 52 |

## 14. Phase 23 — corridor coverage (18 corridors, 53 ZIPs; **10 publish**)

| Corridor | Class | Census | PF | NP | Unres. | Rate | Page |
|---|---|---:|---:|---:|---:|---:|---|
| downtown-las-olas | CORE | 11 | 1 | 1 | 9 | 18.2 % | no |
| fort-lauderdale-beach | CORE | 58 | 6 | 2 | 50 | 13.8 % | **yes** |
| port-everglades-17th-street | CORE | 31 | 5 | 8 | 18 | 41.9 % | **yes** |
| fll-airport-sr84 | CORE | 14 | 5 | 2 | 7 | 50.0 % | **yes** |
| dania-beach | CORE | 29 | 10 | 5 | 14 | 51.7 % | **yes** |
| hollywood-beach | CORE | 75 | 5 | 4 | 66 | 12.0 % | **yes** |
| hollywood | CORE | 39 | 4 | 1 | 34 | 12.8 % | no |
| plantation-davie | CORE | 23 | 9 | 2 | 12 | 47.8 % | **yes** |
| hallandale-beach | CORE | 7 | 1 | 2 | 4 | 42.9 % | no |
| galt-ocean-lauderdale-by-the-sea | CORRIDOR | 42 | 3 | 6 | 33 | 21.4 % | no |
| oakland-park-wilton-manors | CORRIDOR | 15 | 2 | 1 | 12 | 20.0 % | no |
| cypress-creek | CORRIDOR | 17 | 5 | 3 | 9 | 47.1 % | **yes** |
| pompano-beach | CORRIDOR | 32 | 4 | 4 | 24 | 25.0 % | no |
| deerfield-beach | CORRIDOR | 27 | 7 | 4 | 16 | 40.7 % | **yes** |
| sunrise-tamarac-lauderhill | FRINGE | 11 | 2 | 3 | 6 | 45.5 % | no |
| weston-southwest-ranches | FRINGE | 5 | 3 | 1 | 1 | 80.0 % | no |
| pembroke-pines-miramar | FRINGE | 16 | 7 | 4 | 5 | 68.8 % | **yes** |
| coral-springs-coconut-creek | FRINGE | 8 | 6 | 0 | 2 | 75.0 % | **yes** |

A page publishes only where the existing threshold (5 verified pet-friendly hotels) is met mechanically. No thin
page was created, and none was created for a cruise or SEO keyword.

## 15. Phase 24 — South Florida boundary audit

| Area | Discovered (DBPR hotel-rank licences) | **Admitted** |
|---|---:|---:|
| Miami-Dade County (the **LIVE** `miami-fl` market) | 738 | **0** |
| Palm Beach County | 222 | **0** |
| — Boca Raton | 26 | **0** |
| — Delray Beach | 18 | **0** |
| — Boynton Beach | 10 | **0** |
| — West Palm Beach | 55 | **0** |
| Florida Keys (Monroe County) | 319 | **0** |

Graph nodes refused by place: Miami-Dade 606, Florida Keys 242, West Palm / Palm Beach 139, Boca Raton 26,
Delray 17, Boynton 10. **`no_south_florida_sprawl` = true**, asserted on the census itself.
`west-palm-beach-fl` and `florida-keys-fl` are preserved by name as future standalone markets; `miami-fl` is
named as an **existing live market**, not a future one.

The rule earns its keep in both directions: Hampton Inn **Boca Raton**-Deerfield Beach and Fairfield Inn Deerfield
Beach **Boca Raton** (MARSHA code `pbife` — a *Palm Beach* code) are **admitted**, because their own addresses are
Deerfield Beach 33441; and Hampton Inn Hallandale Beach **Aventura** is admitted because its own address is
Hallandale Beach 33009. The postal code places a property; the marketing name and the brand code never do.

## 16. Phase 9 — competitor gap challenge (BringFido, identity only)

29 Broward city pages challenged, **1,148 raw rows → 921 normalized unique leads**:

| Class | Count |
|---|---:|
| EXACT_ATLAS_MATCH / ALIAS / DUPLICATE | 92 / 36 / 121 (**249 matched**, 128 distinct census identities) |
| VACATION_RENTAL | 359 |
| OUTSIDE (Miami-Dade, Palm Beach, the Keys, other Florida cities BringFido's radius pulled in) | 104 |
| REVIEW (a listing title naming no establishment) | 187 |
| **TRUE MISSING QUALIFYING** | **22** |
| MATCHED BUT POLICY UNRESOLVED | 128 |

Each true-missing candidate was verified through an authoritative lane (Google Places, existing key):
**7 verified as real lodging at an admitted postal code**, 9 were already in the census by address or phone,
6 resolved outside the market, 1 returned no lodging result. No competitor pet text was read, stored or used.

**MATERIAL IDENTITY GAP = NO.** Every one of the 921 leads carries an exact class and the true-missing cohort was
worked to zero unexplained rows. **MATERIAL POLICY GAP = NO** — the 128 matched-but-unresolved rows are the same
§11 root causes, dominated by ROUTING and ACCESS_BLOCKED on Broward's independent motel stock.

## 17. Phase 30 — parallel safety

`git diff --name-only 327c6fd0 HEAD` → every changed path is Fort-Lauderdale-owned.

| Check | Changes |
|---|---:|
| CROSS-MARKET FILE CHANGES | **0** |
| SHARED FACTORY CODE CHANGES | **0** |
| CURRENT LIVE CHANGES | **0** |
| DEPLOYMENT STATE CHANGES | **0** |

Every helper added is prefixed `fort_lauderdale_fl_`; the only shared modules touched were *read*, never edited.
`identity_resolutions.json` was deliberately **not** written (§10).

## 18. Phases 27–29 — shadow package, FAST and reproduction

| Item | Value |
|---|---|
| Source commit | `e7a494dae11052b451413317959ed0fa810266e5` |
| Package | `pkg-fort-lauderdale-fl-69b617cd4c8b6ba9` |
| **PACKAGE DIGEST** | `sha256:69b617cd4c8b6ba9222ffadeb2d75d902d3b4a8180f6bad84bbcd2627f0b8de7` |
| Execution zone | **SHADOW_UNTIL_REGISTERED** |
| FAST (A–O) | **15/15 PASS, 0 UNKNOWN, 0 FAILED**, `FAST_DATA_ONLY_RELEASE_ELIGIBLE = YES` |
| Declared public surface | 85 hotel profiles, 10 corridor pages, 1 comparison page, 406 `/go/` pages; **0 warnings, 0 broken internal links, 0 quality-gate failures** |
| REPRODUCTION A | this worktree, sealed twice in-process: identical digest |
| REPRODUCTION B | detached worktree `C:\t\ftl2b` at the same commit, **independent process**: identical digest **and an independent FAST 15/15 PASS** |
| **BYTE IDENTICAL** | **YES** |

**A real nondeterminism was found and fixed, not explained away.** The first seal named source sha `be3e62b8`,
whose committed staging tree still held the *pre-hold* 86-row seed inventory — the dual-brand fix regenerated it
to 82 during that same seal, so the sha the package claimed to be created from no longer derived the package. An
independent worktree at `be3e62b8` proved it by sealing `fdab81af` instead of `4ff1ccc0`, one input digest apart.
The seal derives four staged inputs from the committed authority, so the **first** seal after any authority change
always writes inputs the named sha does not yet carry. Sealing again at the commit that carries them reaches the
fixed point: the final run changed **outputs only** and no staged input drifted. Line endings were checked and
are not a source of drift — the one file that differed between worktrees differed in CRLF rendering with **no
content diff** (`core.autocrlf=true`).

Three earlier seals are kept as honest history (`4ff1ccc0`, `a0e3843b`, `fe3c739c`): the first was refused by
FAST rule J, and each later one is a step of the fixed-point argument above.

## 19. Phase 31 — performance and cost

| Stage | Wall clock |
|---|---|
| Precheck + current-live resolution | 4 s (resolver), ~3 min including ancestry checks |
| Geography (authoring + contract validation) | ~12 min |
| DBPR lane (download 62 MB + parse 7 extracts) | ~2 min |
| OSM lane (two-pass read of the Florida extract) | ~21 min |
| Visit Lauderdale roster (376 listings, crawl-delay honoured) | ~4 min |
| Brand inventory (22 families) | ~12 min |
| Census reconciliation (per run, run 6 times) | ~7 min |
| Routing | ~1 min |
| Free static capture (351 targets) | ~35 min |
| Firecrawl (discovery + brand pages + policy pass) | ~14 min |
| Places route discovery (174 requests) | ~6 min |
| Independents' policy pages + Places sites | ~16 min |
| Competitor challenge (29 cities) | ~8 min |
| **Attended browser (90 attempts, paced)** | **~3 h 05 m wall, of which ~2 h 20 m is provider cooldown** |
| Policy adjudication + partition + staging | ~6 min |
| Shadow package + FAST (per seal, 5 seals) | ~9 min |
| Independent reproduction + independent FAST | ~18 min |
| **ZERO → TECHNICAL SOURCE READY** | **~8 h 20 m** |
| **ZERO → COVERAGE READY** | **~8 h 50 m** |

| | |
|---|---|
| ACTIVE COMPUTE vs PROVIDER / COOLDOWN WAIT | ~6 h 30 m vs ~2 h 20 m |
| PROVIDER COST | Firecrawl **111 credits** (1,346 → 1,235) · Google Places **174 requests** on existing capacity · **USD 0.00** |
| **NEW PAID SPEND** | **0** — no new provider, no new key, no new plan, no credit purchase |
| Bright Data | not called |
| FOUNDER INTERVENTION | **0** |
| Peak memory (measurable) | the OSM two-pass read, ~2.6 GB resident |

## 20. Phase 26 — coverage readiness

`fort_lauderdale_fl_actionability_001` decides this mechanically on the order's own eight conditions, never on a
percentage. All eight are true:

| Condition | |
|---|---|
| actionable unresolved = 0 | ✅ |
| no material identity gap | ✅ |
| no material unexplained policy gap | ✅ |
| authorized acquisition lanes exhausted | ✅ |
| Marriott queue terminally resolved or safely exhausted | ✅ 40 of 42 read, 1 terminal denial, 0 awaiting |
| browser-required brands processed or safely bounded | ✅ BROWSER_CAPTURE_NEEDED = 0 |
| publication set safe | ✅ 85 rows, each citing its own quote; 4 dual-brand halves held |
| package deterministic and FAST-clean | ✅ reproduced byte-identically, 15/15 |

- **TECHNICAL SOURCE READY = YES.** Deterministic, cross-worktree reproducible, FAST-clean, isolated, fully
  accounted: 460 = 138 resolved + 322 unresolved, one disposition per row, every hold carrying an exact reason.
- **COVERAGE READY = YES.** The 322 unresolved rows are a large but *bounded and fully explained* cohort: 247 have
  exhausted every rung the committed router opens for them, and 75 are founder-reviewable judgements on evidence
  already in hand. Not one is reachable by a lane this order was authorized to use and did not use.

The honest next lever is named and is **not** an acquisition problem: Broward's 238 independent and 46 resort-
independent rows are 76 % of the unresolved set, and they are ROUTING (no first-party site exists) or
ACCESS_BLOCKED (their sites refuse every free client). Reaching them needs a provider authorization this order
does not have. The second lever is the four dual-brand halves, which need one line in a shared document.

---

## FINAL ANSWERS

1. **START TIMESTAMP** = 2026-09-21T00:18:43Z
2. **ZERO_TO_SOURCE_READY** = ~8 h 20 m (≈6 h 30 m active compute, ≈2 h 20 m provider cooldown)
3. **ZERO_TO_COVERAGE_READY** = ~8 h 50 m
4. **TOTAL DISCOVERED** = 3,466 raw observations across 11 lanes
5. **NORMALIZED IDENTITIES** = 2,558 graph nodes (0 merge conflicts)
6. **PROPOSED CENSUS** = **460**
7. **PET-FRIENDLY** = **85**
8. **VERIFIED NO-PETS** = **53**
9. **RESOLVED** = **138**
10. **UNRESOLVED** = **322**
11. **RESOLUTION RATE** = **30.00 %**
12. **ACTIONABLE UNRESOLVED** = **0**
13. **HOLDS BY CLASS** = ROUTING 89 · ACCESS_BLOCKED 89 · SOURCE_SILENT 69 · IDENTITY 38 · EVIDENCE 37 · BROWSER_CAPTURE 0 · NEGATION 0 · POLICY_NOT_FOUND 0 · MIXED_RESORT 0 · CONDO_HOTEL 0 · PAID 0 · GEOGRAPHY 0 · FOUNDER 0 · OTHER 0
14. **VACATION RENTAL / TIMESHARE / RESIDENCE EXCLUSIONS** = 103 / 3 / 0 (plus non-hotel 143, duplicate 3, same-campus-distinct 12, outside 1,087; never admitted at all: 4,526 CNDO, 6,195 DWEL, 2,347 NAPT, 367 apartment-named TAPT)
15. **CORRIDOR COVERAGE** = 18 corridors over 53 admitted postal codes (9 CORE / 5 CORRIDOR / 4 FRINGE), 0 uncorridored rows
16. **PUBLISHING CORRIDORS** = **10** — fort-lauderdale-beach, port-everglades-17th-street, fll-airport-sr84, dania-beach, hollywood-beach, plantation-davie, cypress-creek, deerfield-beach, pembroke-pines-miramar, coral-springs-coconut-creek
17. **MIAMI-DISCOVERED BROWARD IDENTITIES REUSED** = **499** (identity/routing intelligence only; **0** policy rows imported)
18. **NEW BROWARD IDENTITIES** = 2,059 of 2,558 graph nodes
19. **MIAMI-DADE ADMITTED** = **0** (738 discovered)
20. **PALM BEACH COUNTY ADMITTED** = **0** (222 discovered; Boca Raton 26, Delray 18, Boynton 10, West Palm 55 — all 0 admitted)
21. **COMPETITOR RAW / NORMALIZED / MATCHED / TRUE MISSING** = 1,148 / 921 / 249 / 22 (7 verified at an admitted postal code)
22. **MATERIAL IDENTITY GAP** = **NO**
23. **MATERIAL POLICY GAP** = **NO**
24. **FIRECRAWL ELIGIBLE** = 112 planned
25. **FIRECRAWL ATTEMPTED** = **143**
26. **FIRECRAWL SUCCESS** = 4 publication-grade property reads + 66 brand routes discovered + 21 brand pages with their own address
27. **MARRIOTT CENSUS** = **44**
28. **MARRIOTT BROWSER ATTEMPTED** = **42**
29. **MARRIOTT READ SUCCESS** = **40**
30. **MARRIOTT CHALLENGE DENIED** = **1** (terminal, after 4 paced windows)
31. **MARRIOTT ACTIONABLE REMAINING** = **0**
32. **OTHER BROWSER ATTEMPTED / SUCCESS** = Hilton 37/33 · Hyatt 5/4 · Best Western 6/4
33. **ACCESS_BLOCKED AFTER ROUTER EXHAUSTION** = **89**
34. **EXISTING PROVIDER CREDITS USED** = Firecrawl **111** (1,346 → 1,235) · Google Places **174** requests
35. **NEW PAID SPEND** = **0**
36. **PROVIDER COST** = **USD 0.00**
37. **SHADOW PACKAGE CREATED** = **YES** — `pkg-fort-lauderdale-fl-69b617cd4c8b6ba9`, SHADOW_UNTIL_REGISTERED
38. **PACKAGE REPRODUCIBLE** = **YES** — byte-identical in a detached worktree, independent process, with an independent FAST 15/15
39. **PACKAGE DIGEST** = `sha256:69b617cd4c8b6ba9222ffadeb2d75d902d3b4a8180f6bad84bbcd2627f0b8de7`
40. **FAST** = **15/15 PASS, 0 UNKNOWN, 0 FAILED**
41. **TECHNICAL SOURCE READY** = **YES**
42. **COVERAGE READY** = **YES**
43. **CROSS-MARKET FILE CHANGES** = **0**
44. **FACTORY CODE CHANGED** = **NO**
45. **BROAD REGRESSION RUNS** = **0**
46. **FINAL PRODUCTION CANDIDATE CREATED** = **NO**
47. **FOUNDER AUTHORIZATION CREATED** = **NO**
48. **FORT LAUDERDALE DEPLOYED** = **NO**
49. **origin == HEAD** = YES
50. **tree clean** = YES

---

FORT LAUDERDALE SOURCE READY = YES
FORT LAUDERDALE COVERAGE READY = YES
ACTIONABLE UNRESOLVED = 0
FAST = 15/15 PASS
FACTORY CODE CHANGED = NO
BROAD REGRESSION RUNS = 0
FORT LAUDERDALE FINAL CANDIDATE = NO
FORT LAUDERDALE DEPLOYED = NO
WAITING FOR RELEASE QUEUE = YES
