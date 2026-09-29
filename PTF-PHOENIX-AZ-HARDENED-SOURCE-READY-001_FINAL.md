# PTF-PHOENIX-AZ-HARDENED-SOURCE-READY-001 — FINAL

**Phoenix / Scottsdale / Valley of the Sun, Arizona** (`phoenix-az`) is the first Arizona market. It was built from
zero to a market-local SHADOW package on the Denver-live lineage, and that package was reproduced independently.
Worktree `C:\Atlas-Phoenix-AZ-Hardened-V1`, branch `worker/ptf-phoenix-az-market-001`. Phoenix is not registered,
not authorized and not deployed.

| | |
|---|---|
| Shadow package | `{{PKG_ID}}` (`{{DIGEST}}`), SHADOW_UNTIL_REGISTERED |
| Sealed from | `2907c502` (every staged input committed), sealed twice in-process with the same digest |
| FAST | **{{FAST}}**; receipt `{{RECEIPT}}`, currently ELIGIBLE (`eligible_receipts` returns it) |
| Rule J (non-empty) | {{RULE_J}} |
| Rule K (non-vacuous) | {{RULE_K}} |
| First-party gate | {{GATE}} |
| Independent reproduction | {{REPRO}} |
| Census / published | 488 identities: **256 pet-friendly + 63 verified no-pets** = 319 resolved (65.37 %); 169 unresolved |
| Actionability | **ACTIONABLE UNRESOLVED 0**: 88 router-exhausted, 48 need new spend, 30 need a founder decision, 3 held until opening |
| Coverage | **FOUNDER DECISION** (mechanical; see §9) |

## 1. Lineage and current live (Phases 1–2)

The order started at 2026-09-29T01:45:20Z on `630d1198` (DENVER IS LIVE); the Denver live source `edf11b7a` is an
ancestor. CURRENT VERIFIED LIVE is Denver:

- deploy `6aba7587ddcc33a192bdf694`, source `edf11b7a`, bundle `7d3471c7…`, sitemap `5d3d07a4…`
- 36 markets / 2,954 profiles / 3,274 release-index routes / 3,343 served routes

The shadow package's `parent_live_state` names that release. Once any later market goes live, FAST rule N fails this
package BY DESIGN, and the registration order re-seals the same committed inputs as a new package id.

Commits on this branch:

1. `2907c502`: staged inputs (census, staged policy package, shard documents, partition, every Phoenix module and
   report).
2. `{{PKG_COMMIT}}`: the shadow package, its receipt and report.
3. This report and the reproduction record.

## 2. Geography (Phases 3–6)

**Corridors.** 26 corridors over 130 ZIPs. Membership is decided by the property's OWN postal code
(`classify_postal`), never by name, and a ZIP is never split.

- **11 CORE:** Downtown Phoenix, Midtown/Central Phoenix, Biltmore/Camelback/Arcadia, PHX Sky Harbor, Tempe, Old Town
  Scottsdale, Central Scottsdale & Talking Stick, Paradise Valley, Mesa, Chandler & Wild Horse Pass, Glendale &
  Westgate.
- **11 CORRIDOR:** Scottsdale Airpark & Kierland, North Scottsdale, Desert Ridge & Mayo, North Phoenix & Deer Valley,
  West Phoenix & Tolleson, Ahwatukee & South Mountain, Gilbert, Peoria, Goodyear/Avondale/Litchfield,
  Surprise & Sun City, Fountain Hills & Fort McDowell.
- **4 FRINGE:** Queen Creek, Apache Junction & Gold Canyon, Buckeye, Cave Creek & Carefree.

Two codes were added from measurement during the order: 85242 (Queen Creek's former code, which a Hampton Inn's own
page still states) and 85363 (the Town of Youngtown on Grand Avenue, stated by a Quality Inn).

**Scottsdale ruling.** Scottsdale stays inside `phoenix-az` and is not a separate market. It is split into its own
corridors by its own postal codes: Old Town Scottsdale (CORE), Central Scottsdale (CORE), Paradise Valley (CORE),
Scottsdale Airpark & Kierland (STRONG CORRIDOR) and North Scottsdale (STRONG CORRIDOR). One airport (PHX) serves
both cities, and "Scottsdale" is the postal city of Paradise Valley's resorts, the Salt River community's Talking
Stick hotels and the City of Phoenix's Kierland and Desert Ridge. The four Scottsdale-named corridors hold 75 census
rows and 44 pet-friendly profiles.

**Resort, casita, condo, timeshare and rental safety.** Timeshare codes are excluded before any policy applies
(Marriott phxcv/phxso/phxwk/phxpr, IHG phxcv, Choice az385/az654, the three Hilton Vacation Club resorts). Vacation
rentals, condominium communities (the Racquet Club), serviced-apartment operators and RV resorts are never hotel
identities. A resort's own casitas and villas publish only as the resort's own policy.

**Refused.** Sedona / Verde Valley, Flagstaff, the Grand Canyon, Prescott, Tucson and southern Arizona, Payson and
the White Mountains, Pinal County outside the contiguous East Valley, north-west and west Maricopa County
(Wickenburg, Tonopah, Gila Bend), Yuma, Mohave County, and every non-Arizona code.

Uncorridored admitted rows: **0**.

| corridor | class | census | PF | NP | unresolved | resolution | page publishes (≥ 5 PF) |
|---|---|---:|---:|---:|---:|---:|---|
| downtown-phoenix | CORE | 27 | 11 | 7 | 9 | 66.7 % | yes |
| midtown-central-phoenix | CORE | 14 | 3 | 2 | 9 | 35.7 % | no |
| biltmore-camelback-arcadia | CORE | 11 | 10 | 0 | 1 | 90.9 % | yes |
| phx-sky-harbor | CORE | 33 | 14 | 8 | 11 | 66.7 % | yes |
| tempe | CORE | 47 | 26 | 5 | 16 | 66.0 % | yes |
| old-town-scottsdale | CORE | 29 | 20 | 2 | 7 | 75.9 % | yes |
| central-scottsdale | CORE | 20 | 12 | 2 | 6 | 70.0 % | yes |
| paradise-valley | CORE | 10 | 7 | 0 | 3 | 70.0 % | yes |
| mesa | CORE | 62 | 22 | 7 | 33 | 46.8 % | yes |
| chandler | CORE | 42 | 27 | 5 | 10 | 76.2 % | yes |
| glendale | CORE | 17 | 11 | 3 | 3 | 82.4 % | yes |
| scottsdale-airpark-kierland | CORRIDOR | 13 | 6 | 2 | 5 | 61.5 % | yes |
| north-scottsdale | CORRIDOR | 13 | 6 | 1 | 6 | 53.8 % | yes |
| desert-ridge-mayo | CORRIDOR | 4 | 3 | 1 | 0 | 100 % | no |
| north-phoenix-deer-valley | CORRIDOR | 36 | 20 | 3 | 13 | 63.9 % | yes |
| west-phoenix | CORRIDOR | 26 | 8 | 4 | 14 | 46.2 % | yes |
| ahwatukee-south-mountain | CORRIDOR | 7 | 2 | 3 | 2 | 71.4 % | no |
| gilbert | CORRIDOR | 15 | 14 | 1 | 0 | 100 % | yes |
| peoria | CORRIDOR | 10 | 4 | 2 | 4 | 60.0 % | no |
| goodyear-avondale-litchfield | CORRIDOR | 17 | 17 | 0 | 0 | 100 % | yes |
| surprise-sun-city | CORRIDOR | 12 | 5 | 3 | 4 | 66.7 % | yes |
| fountain-hills-fort-mcdowell | CORRIDOR | 4 | 1 | 0 | 3 | 25.0 % | no |
| queen-creek | FRINGE | 1 | 1 | 0 | 0 | 100 % | no |
| apache-junction-gold-canyon | FRINGE | 4 | 0 | 2 | 2 | 50.0 % | no |
| buckeye | FRINGE | 10 | 5 | 0 | 5 | 50.0 % | yes |
| cave-creek-carefree | FRINGE | 4 | 1 | 0 | 3 | 25.0 % | no |

18 corridor pages publish. No thin page is forced: a corridor with fewer than 5 pet-friendly profiles publishes no
page, and its hotels still publish as profiles.

### Boundary audit (Phase 25)

| refused place | discovered | admitted |
|---|---:|---:|
| Sedona / Verde Valley | 44 | **0** |
| Flagstaff / Grand Canyon / Williams | 93 | **0** |
| Prescott | 18 | **0** |
| Tucson / southern Arizona | 116 | **0** |
| Other Arizona markets (Payson / Rim / White Mountains / Globe 16, Pinal outside the East Valley 10, north-west Maricopa 16, Yuma 0, Mohave 0) | 42 | **0** |
| Out of state | 0 | 0 |

Rows admitted from a refused postal code: **0**. Refused nodes under a Valley prefix (850–853) are listed by code in
the accounting (the refused Pinal and north-west Maricopa codes, Ajo, Black Canyon City, and one Sedona row that
states a downtown Phoenix ZIP and is refused by its own municipality).

## 3. Owned data, census lanes and exclusions (Phases 7–13)

**Owned data first.**

- 0 owned Phoenix identities, because this is the first Arizona market.
- 105 owned routes (Marriott MARSHA `phx…`).
- 7,799 live identity names loaded for the cross-market collision pass.
- 1,226 prior Firecrawl calls, of which 0 were Phoenix pages.

**Census lanes: 3,915 raw observations.**

| lane | observations | note |
|---|---:|---|
| OSM | 1,029 | Geofabrik Arizona extract `arizona-260928` (Overpass returned 406, 504 and no answer, all recorded); 1,673 elements |
| Brand inventories | 382 | Marriott owned 104, Hilton Arizona city pages 100, brand sitemaps 175, state sitemap 3 (Choice, IHG, Best Western, Hyatt, Omni, Red Roof and Motel 6 refused their sitemaps) |
| Bureaux | 541 | Visit Phoenix 188, Experience Scottsdale 111, Visit Mesa 102, Visit Chandler 57, Tempe Tourism 39, Discover Gilbert 26, Experience Glendale 18 (Simpleview read unfiltered; Craft; WordPress hotel sitemaps) |
| Competitor leads | 1,544 | BringFido, 22 Valley cities |
| Property pages | 419 | attended browser, static client, Firecrawl brand pages, Wyndham property service |

Arizona publishes no statewide lodging licence register that this order could read, so that lane is recorded as
absent.

**Graph and admission.** The graph has 2,499 nodes, of which **488 are admitted**.

**Exclusions.**

| class | count |
|---|---:|
| Vacation rental | 271 |
| Timeshare | 11 |
| Resort residence | 0 |
| Non-hotel | 137 |
| Outside | 440 |
| Name-only residue | 1,034 |
| Identity-review residue | 112 |
| Same-campus distinct entity | 4 |
| Closed | 0 |

**Cross-market collisions.** 8 Valley rows are held because their final name (a bare chain name such as "Ramada",
"Quality Inn", "Everhome Suites", or "Royal Palms Resort and Spa", which fort-lauderdale-fl publishes for a different
hotel) collides with a live market's identity. Published collisions: **0**. Site titles (60 characters): 0
in-market collisions and 0 collisions with any live policy package.

**Preopening and closed (Phase 11).** Three identities are PREOPENING and held, never published and never
verified-no-pets: Home2 Suites Peoria North (its own page: "We're accepting reservations for September 30, 2026 and
beyond."), ECHO Suites Phoenix-Chandler ("Opening Late 2026") and Vai Resort ("coming soon"). DoubleTree Suites
Phoenix (a 2027 date on a card) is operating and is not preopening. No row is CLOSED on a first-party closure
statement; lapsed routes are routing holds.

## 4. Acquisition (Phases 14–19)

* **Static plain client.** 209 targets: VALID 16, ACCESS_DENIED 80, IDENTITY_MISMATCH 47, NAVIGATION_FAILED 42,
  POLICY_NOT_FOUND 12, UNHYDRATED 6, UNEXPECTED_PAGE 5, BLANK 1.
* **Wyndham property service.** 73 routes selected, 35 read, 38 retired.
* **Independents' own policy pages.** 74 targets, 44 bound.
* **Firecrawl** (existing credits, capped on attempts, floor 400):
  * route discovery: 22 Choice/IHG city pages → 77 routes (22 credits)
  * brand pages: 76 attempted / 76 answered / 66 with their own address (76 credits)
  * routed pass 001: 33 attempts / 5 publication-grade (30 credits)
  * an aborted first start of pass 001 spent 5 credits, 4 of them re-buying brand pages the brand-page lane had
    already bought; the pass was stopped and now excludes those routes (pay once per page)
  * **133 credits in total (864 → 731). USD 0.**
* **Places.** Not used. `websiteUri` is an Enterprise-SKU field; using it would be new spend, which this order is not
  authorized for (the free allowance renews 2026-10-01).
* **Attended browser** (claude-in-chrome; navigate plus accessibility read only; no JS exfiltration, no relay, no
  bypass, no CAPTCHA solved): **286 attempts, 254 reads (252 bound to a census row), 0 Akamai denials, 2 DataDome
  CAPTCHAs (ESA, never solved).**

| family | attempts | reads | other outcomes |
|---|---:|---:|---|
| Marriott | 106 | 102 | 4 timeshare resorts excluded on the brand's own page; 0 Akamai denials |
| Hilton | 97 | 94 | 3 resorts whose pet accordion never exposed its text on two bounded attempts |
| Hyatt | 17 | 17 | includes the dual-brand Hyatt Place / Hyatt House North Scottsdale pair |
| Best Western | 16 | 15 | Aiden's own site states nothing about pets |
| Sonesta | 7 | 7 | the Pet Policy tab panel is hidden from a static fetch |
| Drury | 5 | 5 | |
| IHG | 6 | 3 | 3 rendered pages carry no pet element (bounded at one attempt) |
| Independents | 22 | 8 | 11 source-silent, 2 dead domains, 1 lands on its operator's home page |
| Omni 2, Red Roof 1 | 3 | 3 | |
| Motel 6 | 4 | 0 | each page states only the amenity chip "Pets Allowed" |
| ESA | 2 | 0 | DataDome CAPTCHA on every property page (the brand's directory served) |
| Wyndham | 1 | 0 | the retired Ramada Mesa route lands on the brand's search |

**Marriott closure.** Every in-market Marriott route the owned harvest and the brand's Arizona sitemap list was read.
MARRIOTT ACTIONABLE REMAINING = **0** (100 census rows: 66 PF, 18 NP, 16 held — 8 dual-brand buildings = 16 rows).

## 5. Policy and evidence rules (Phases 16–19)

**Inference rules.**

- Acceptance is never taken from a fee, a weight, a count or an amenity chip.
- Refusal is never taken from silence.
- A resort's reputation is never read as a policy.
- A competitor claim is never used as authority.

**Fees. 49 fees publish, 112 are withheld, and 0 misleading single fees are published:**

- 77 tiered or multi-amount fees are withheld (for example Hilton's "$75 (1–4 nights), $125 (5+ nights)", Hyatt's
  stay-length tiers, IHG's fee-plus-deposit).
- 35 single fees are withheld as unsafe: basis not stated 30, stay-length condition 5.
- Every published fee was re-checked against its own quote: one amount, and the published basis (per night / per
  stay) is the basis the quote states.
- In every withheld case, the acceptance, weight, count and species still publish.

**Other rules.**

- Every published quote passes the shared first-party reader (FAST rule C; gate {{GATE}}).
- Each row has one disposition, and every hold carries its reason.

## 6. Defects found and fixed in this market's own modules

1. **A nightly fee could publish as per-stay.** The staging module cleared a fee with a pattern that reads "daily"
   as nightly, then re-derived the published basis from a narrower pattern without "daily" — Drury's "a daily fee of
   $50 per room" would have published as a one-time fee. The basis now comes from the same pattern that cleared the
   fee. **The same defect is live in other markets** (§12).
2. **Dual-brand buildings vanished through a shared phone.** Hilton's own cards put Home2 Suites and Tru at 3150 N
   Central with one telephone, and Homewood and Tempo at 5057 S Power; the phone key folded each pair into one node.
   No key but the brand code may now join a node that already carries a different code of the same brand.
3. **IHG and Marriott reuse five-letter codes in this market** (phxmz, phxff, phxcv, phxtt, phxpe, phxww, phxac): a
   browser read binds by code only under the same brand family.
4. **A Choice room chip read as a refusal.** Choice pages carry per-room chips ("No Pets Allowed…") beside the
   property's own "Pets Allowed: Yes" block; only the property's block is read.
5. **Firecrawl pay-once.** Pass 001's first start re-bought 4 brand pages; the pass now excludes routes any Phoenix
   lane already bought.
6. **Transcription.** Two property sites render street and city on two lines that the accessibility text joins
   ("Main StScottsdale"); the joined form spawned a second node with Hotel Valley Ho's key and the census refused to
   write. The line break is now transcribed as a space, with a note on the read.
7. **Same-name demotion hid a real hotel.** OSM put Sonesta Suites Gainey Ranch at 85253 and the brand at 85258, and
   the same-name pair was demoted to review. The property's own page (85258) now decides it: it publishes.

## 7. Competitor challenge and large-market quality challenge (Phases 10 and 26)

BringFido (audit lane only, never policy): 22 Valley cities, 1,858 raw / 1,544 unique.

| class | count |
|---|---:|
| Exact | 229 |
| Alias | 29 |
| Duplicate | 18 |
| Vacation rental | 860 |
| Review | 378 |
| Outside | 4 |
| Non-hotel | 13 |
| Condo residence | 1 |
| **True missing** | **12** |

The 12 true-missing leads were each investigated through the operator's own site:

- LivAway Suites ×3 (Surprise, Glendale, Tolleson): "Now Open" on the operator's own directory; each page states a
  street but no postal code and only the chip "Pet-friendly rooms", so none can be admitted or published from it.
- Motel 6 ×5 (Midtown, North Bell Road, Tempe Elliot Road, Glendale, Youngtown) and Red Roof ×2 (Deer Valley/Bell
  Rd, Midtown): the brands publish no directory a free lane can read (their finders are search forms); OSM's bare
  "Motel 6" nodes at 2330 W Bell Rd, 7116 N 59th Ave and 8152 N Black Canyon are held as a same-name tie. Motel 6's
  pages in this market state only a chip, so no Motel 6 row could publish.
- Garner Hotel Surprise (IHG refused its sitemap) and The Four Queens Inn: no first-party page in any authorized lane.

Each stays a named gap and none is published. There is no material identity gap: 276 of 1,544 leads match the
census, and every rental-shaped title is filed as one.

**Quality challenge against the major resorts and the airport.** Every major Valley resort was checked against the
census. Three real gaps were found and closed through the properties' own pages: Sonesta Suites Scottsdale Gainey
Ranch (now published), Hotel San Carlos (admitted; source-silent) and Drury Inn & Suites Phoenix Happy Valley (the
brand sitemap carried a name only and OSM a bare name; now published). Central Phoenix Budget Suites was found on
its operator's own Arizona list and admitted (source-silent). Royal Palms Resort and Spa is held as a cross-market
name collision (a founder display-name ruling). The PHX Sky Harbor corridor holds 33 census rows and 43 admitted
names carry "airport". The remaining OSM brand residue is stale addresses of admitted hotels (Aloft Tempe at 901 vs
951 E Playa del Norte, Spark East Mesa, The McCormick at 85258 vs 85253).

## 8. Actionability (Phase 22, per row)

| disposition | total | actionable | exhausted | new spend | founder | held until opening |
|---|---:|---:|---:|---:|---:|---:|
| ROUTING_HOLD | 61 | 0 | 13 | 48 | 0 | 0 |
| SOURCE_SILENT | 30 | 0 | 30 | 0 | 0 | 0 |
| EVIDENCE_HOLD | 22 | 0 | 17 | 0 | 2 | 3 |
| IDENTITY_MISMATCH_HOLD | 49 | 0 | 21 | 0 | 28 | 0 |
| ACCESS_BLOCKED | 7 | 0 | 7 | 0 | 0 | 0 |
| **total** | **169** | **0** | **88** | **48** | **30** | **3** |

* **48 need new spend.** These are mostly independents (38) with no website in any authorized lane, plus 6 retired
  Wyndham routes, 2 routeless Red Roof, 1 Best Western and 1 Choice. The only lane that finds a route is Places
  `websiteUri`. They are left exactly as classified.
* **30 need a founder decision.**
  * 14 dual-brand buildings (28 rows), each half proved by its own brand code and page: Marriott 25100 N 22nd Ln
    (AC/Element), 1100 S Price Rd (Courtyard/Fairfield), 132 S Central Ave (Courtyard/Residence Inn), 1550 N Verrado
    Way, 13430 N 163rd Dr and 1929 E Rio Salado Pkwy (Fairfield/TownePlace), 9425 N Black Canyon Hwy
    (SpringHill/TownePlace), 6000 E Camelback Rd (The Phoenician / The Canyon Suites); Hilton 7290 S Price Rd
    (Hilton Garden Inn/Home2), 3150 N Central Ave and 8401 N Pima Center Pkwy (Home2/Tru), 5057 S Power Rd
    (Homewood/Tempo); Hyatt 18513 N Scottsdale Rd (Hyatt Place/Hyatt House); 2735 W Sweetwater Ave (Econo Lodge /
    Super 8). Publishing them needs a `same_campus_distinct_entity` row in the SHARED `identity_resolutions.json`,
    which this order may not write.
  * 2 route rulings: Tempe Mission Palms (the census route missionpalms.com now redirects to its Destination by
    Hyatt page, which states "does not allow pets") and Best Western Plus Scottsdale Thunderbird Suites (own domain
    vs bestwestern.com, whose statement is conditional anyway).
  * **All are left held.**
* **88 router-exhausted**, including ESA (13 rows: DataDome on every property page), Motel 6 (chip only),
  three Hilton resort accordions and 30 source-silent pages.

## 9. Coverage decision (Phase 27)

All coverage conditions are true: actionable 0; no material identity gap and no unexplained policy gap; lanes
exhausted; Marriott closed; browser cohorts bounded; preopening rows safely excluded; dual-brand rows safely held;
publication set safe; package reproducible and FAST clean.

The coverage contract still returns **FOUNDER DECISION** mechanically: 81 unresolved rows are reachable only through
new spend (48), a founder ruling (30) or the hotel's opening (3).

## 10. Reproduction (Phase 31)

{{REPRO_SECTION}}

## 11. Isolation, boundaries and cleanup (Phases 33–34)

**Changed paths since `630d1198`.** These are Phoenix-owned only:

- scripts `phoenix_az_*` and `discovery/config/phoenix_az.json`
- reports `phoenix_az_*`
- `markets/staging/phoenix-az/`
- the proposed census and proposed market
- this report

That is **0 shared, 0 cross-market, 0 live and 0 deploy paths.**

**Boundaries kept.**

- Not registered; no founder or deployment authorization; no production candidate; no whole-site build.
- Participation, pin and `identity_resolutions` untouched.
- 0 broad regression runs; USD 0; no new provider.

**Cleanup.** The browser tab is closed and the tab group removed. The seal and reproduction processes exited, and
their scratch work dirs and worktree were removed. No timers, watchers, servers or child workers from this order
remain. One unrelated pre-existing process (`C:\t\sink.py`, started 2026-09-14) was left alone.

**Performance (Phase 34).**

- START 2026-09-29T01:45:20Z; ZERO_TO_SOURCE_READY {{ZTSR}}.
- Active compute is dominated by the census reconciliation (about 6 minutes a run, run to a fixpoint after each
  browser batch).
- Provider / cooldown wait: none forced; browser pacing ~6–8 s per page, Marriott ~30 s.
- Existing provider credits: 133 Firecrawl credits. New paid spend: 0. Provider cost: USD 0.
- Founder intervention: none requested during the build.

**Machine-readable accounting.**

- `markets/reports/phoenix_az_source_ready_accounting_001.json`: source, provider, brand, corridor, competitor,
  boundary and fees
- `phoenix_az_actionability_001.json`: per row
- `phoenix_az_competitor_reconciliation_001.json`
- `phoenix_az_fee_withholding_001.json`
- `phoenix_az_shadow_package_001.json`
- `markets/staging/phoenix-az/reproduction/`

## 12. Finding outside this order's scope: a nightly fee published as per-stay in live markets

The staging defect fixed in §6.1 exists in the modules that built earlier live markets. A read-only scan of the live
`hotel_policy_facts_*.json` packages found per-stay fees whose own quote states a daily or nightly charge:

- charlotte-nc: Drury Inn & Suites Charlotte Arrowood, Northlake and University ("a daily fee of $65 / $50"), and
  Hilton Charlotte Airport ("$100.00 non-refundable fee … $10 each night thereafter", also tiered)
- tampa-fl: Drury Plaza Hotel Tampa Brandon ("a daily fee of $50 per room")

This order may not modify another market. It needs its own correction order.

## FINAL ANSWERS

{{ANSWERS}}
