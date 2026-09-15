# PTF-ORLANDO-FL-PARALLEL-SOURCE-READY-001 — FINAL

Worktree `C:\Atlas-Orlando-FL-Hardened-V1` · branch `worker/ptf-orlando-fl-market-001` · market `orlando-fl`
Display market: **Orlando – Greater Orlando / Central Florida**
Base (source commit): `c236f52da26ac7b1fe531b2497cef5dfba67d9d2` (= `origin/main`, clean at start)

## 1. Clock

| | |
|---|---|
| ORLANDO_START_TIMESTAMP | 2026-09-15T04:23:42Z |
| Source-ready (shadow package sealed) | 2026-09-15T07:20:06Z |
| **ZERO_TO_SOURCE_READY** | **2h 56m 24s** |

Approximate phase breakdown (UTC): precheck 04:23–04:25 · owned-data search + lane probes 04:25–04:40 ·
census lanes (DBPR, Overpass, Hilton, Visit Orlando, Wyndham sitemaps) 04:28–05:15 · attended Hilton
capture 04:55–05:05 · identity resolution + geography iterations 05:15–06:15 · first-party crawl +
evidence adjudication 06:15–06:40 · repo build / reconciliation / quality challenge 06:40–07:03 ·
FAST + reproduction A 07:05–07:12 · reproduction B 07:13–07:19 · package 07:20. Peak memory: not measured.

## 2. Precheck

Worktree, branch, HEAD `c236f52d` = upstream `origin/main`, tree clean, origin
`github.com/jfields80/atlas-dashboard`. Isolation: this worktree is the only one on
`worker/ptf-orlando-fl-market-001`; no file of any other market was read for writing. CURRENT VERIFIED LIVE
was read for context only (latest known live launch: Outer Banks, `origin/worker/ptf-outer-banks-nc-market-001`
@ `cf6cdded`); no live-state reader exists at this base.

## 3. What was built (all Orlando-owned paths)

```
atlas-dashboard/scripts/pettripfinder/orlando_fl_identity_rules_001.py     address / brand / category / geography rules
atlas-dashboard/scripts/pettripfinder/orlando_fl_policy_evidence_001.py    durable evidence + SHARED prose readers (unmodified)
atlas-dashboard/scripts/pettripfinder/orlando_fl_market_build_001.py       deterministic build (leads → identities → census/partition/config/accounting)
atlas-dashboard/scripts/pettripfinder/orlando_fl_fast_checks_001.py        15 applicable FAST checks
atlas-dashboard/scripts/pettripfinder/orlando_fl_shadow_package_001.py     SHADOW_UNTIL_REGISTERED package + receipt
atlas-dashboard/scripts/pettripfinder/orlando_fl_stage_raw_captures_001.py capture-time staging of raw inputs
atlas-dashboard/launch_packages/pettripfinder/markets/staging/orlando-fl/
    raw_captures/ (DBPR licences, Overpass, Visit Orlando, Hilton inventory, owned Marriott codes, 145 evidence pages .jsonl.gz, lane attempts)
    evidence_rulings_001.json · identity_rulings_001.json · orlando_fl_identity_resolution_001.json
    launch_package/ (identity_census/orlando-fl.json, orlando_fl_final_partition_001.json, markets/orlando-fl.json,
                     markets/authority/orlando-fl/{identity_routing,hotel_exclusions}.json + seed_businesses.csv, evidence ledger)
    shadow_packages/pkg-orlando-fl-b5667776c6e8df99.json · shadow_receipts/…-receipt.json
atlas-dashboard/launch_packages/pettripfinder/markets/reports/orlando_fl_source_ready_accounting_001.json   (machine-readable accounting)
```

No generic FAST / sealer / registration lane exists at `c236f52d` (same finding as Augusta), so the package,
receipt and checks use Orlando-owned schema names and the contract validators that do exist.

## 4. Owned-data search (Phase 7)

| | |
|---|---|
| OWNED IDENTITIES | 0 Orlando identities (no Orlando/Florida market on any branch) |
| OWNED ROUTES | 0 |
| OWNED VALID POLICY EVIDENCE | 0 |
| OWNED REBRANDS / ALIASES | 0 |
| OWNED COLLISIONS | 0 |
| Owned assets reused | **Florida DBPR registry adapter** (`discovery/fl_dbpr_registry.py`, column vocabulary) and the **Marriott sitemap harvest** in `dayton_oh_brand_directory_harvest_001.json` (commit `2030358b`) → 136 Orlando-area Marriott property codes at 0 requests |

## 5. Geography (Phases 2–3, 6)

Backbone: counties Orange, Osceola, Seminole in full; Lake / Polk / Volusia by city. Each identity gets a
class from its city and a corridor from its coordinates (rule recorded per row; ZIP fallback only when no
lane has coordinates).

| Class | Areas |
|---|---|
| **CORE** | Downtown Orlando · MCO & Lake Nona · International Drive · Orange County Convention Center · Universal Orlando & Epic Universe · SeaWorld · Lake Buena Vista / SR-535 / Bonnet Creek · Disney Springs · Walt Disney World · Kissimmee US-192 Maingate · Downtown Kissimmee & East US-192 · Celebration · South Orlando (Florida Mall / OBT / Millenia) · East Orlando / UCF |
| **CORRIDOR** | Winter Park / Maitland / North Orlando · West Orlando / Ocoee / Winter Garden / Windermere · Apopka · Clermont / Minneola · Altamonte Springs / Longwood / Casselberry · Lake Mary / Sanford (SFB) · Four Corners / Davenport / ChampionsGate / Reunion · Flamingo Crossings (WDW west entrance) |
| **FRINGE** (admitted) | St. Cloud, Poinciana |
| **OUTSIDE / FUTURE STANDALONE** | Haines City · Mount Dora / Eustis / Tavares / Leesburg / Lady Lake (Lake County towns) · DeLand / DeBary / Orange City / Deltona (West Volusia) · Lakeland · Winter Haven / Auburndale / Lake Wales / Bartow (Polk) · Tampa, Daytona Beach, Space Coast, Ocala — not absorbed |

**Split test (Phase 3).** Downtown, MCO, I-Drive, Convention Center, Universal and SeaWorld are CORE ORLANDO. Lake
Buena Vista, Disney Springs and Walt Disney World are CORE with **future standalone optionality** preserved
as three distinct corridor IDs (Disney-area census 76). Kissimmee US-192 / East US-192 / Celebration are CORE with
future standalone optionality (census 100; separate corridor IDs). Four Corners / Davenport / ChampionsGate is an
ORLANDO CORRIDOR (15 hotels; its dominant inventory is vacation homes, which are excluded).

**Corridor pages (threshold: ≥ 5 published pet-friendly, `minimum_hotel_count` 5, nothing navigable in shadow).**
Page-eligible now: Downtown (5 PF / 25), MCO (9/37), International Drive (6/39), Convention Center (7/18),
Universal (11/45), Lake Buena Vista (7/38), South Orlando (5/45), Lake Mary–Sanford (5/29) = **8 of 23**.
Not eligible (thin or policy-blocked): SeaWorld 3/19, Disney Springs 2/7, WDW 2/24, Flamingo Crossings 2/7,
Kissimmee Maingate 4/77, Kissimmee East 1/21, Celebration 1/2, Four Corners 2/15, East Orlando 4/21, Winter Park 3/20,
West Orlando 2/11, Altamonte 2/19, Apopka 2/9, Clermont 2/9, St. Cloud 0/8. No thin SEO page is created.

## 6. Census lanes (Phase 8)

| Lane | Result |
|---|---|
| Florida DBPR public-lodging licences (hrlodge1–7, 203,337 rows) | 765 in-scope HOTL/MOTL/TAPT/BNB licences; geocoded 646 (Census batch) + 78 (Nominatim) |
| OpenStreetMap / Overpass | 1,420 elements (1,015 named) — **Overpass answered this run** (it refused Augusta's sandbox earlier) |
| Hilton (attended same-origin GraphQL, 26 localities) | 121 codes |
| Marriott (owned harvest) | 136 codes, 0 requests |
| Visit Orlando CVB listing API (catid 167) | 211 hotels |
| Wyndham sitemaps (plain) | 297 area property URLs; property pages then 403 |
| Disney / Universal / Loews / Sonesta / ESA / WoodSpring / InTown / independents | first-party crawl (plain client) |
| Refused to a plain client this run | marriott.com, ihg.com, hyatt.com, bestwestern.com, redroof.com, omnihotels.com, radissonhotels.com, fourseasons.com, experiencekissimmee.com (403); choicehotels.com, motel6.com (timeout); wyndhamhotels.com property pages (403 after sitemap walk) |

## 7. Accounting (Phases 10, 15) — reconciles mechanically

Unit = premises identity after cross-lane resolution (DBPR licence group or brand property code).

| | |
|---|---|
| **TOTAL DISCOVERED** | **1,117** |
| **PROPOSED CENSUS** | **545** |
| **VALID PET-FRIENDLY** | **87** |
| **VALID VERIFIED NO-PETS** | **2** |
| RESOLVED / UNRESOLVED | 89 / 456 |
| OUTSIDE | 168 |
| TIMESHARE | 82 |
| VACATION RENTAL | 185 (144 are individually mapped numbered villa units of rental communities) |
| RESORT RESIDENCE | 1 (Evermore residences) |
| NON-HOTEL (apartments, RV/fish camp, B&B) | 48 |
| RESTRICTED / NON-PUBLIC (Shades of Green wings, JetBlue lodge, Lake Nona Club) | 3 |
| Discovery leads without an active hotel licence: DUPLICATE 1 · REBRAND 10 · REVIEW 74 | 85 |
| CLOSED / RETIRED | 0 asserted (unlicensed OSM-only hotels are held as REVIEW, not declared closed) |

545 + 168 + 82 + 185 + 1 + 48 + 3 + 85 = 1,117 ✓ (asserted in the build). Lead-level: 5 ambiguous leads left
unattached and counted as duplicates.

**Holds by class (census rows):** IDENTITY 6 · ROUTING 225 (no official URL 177, brand-index URL only 25, dead route 23) ·
ACCESS-BLOCKED 149 · EVIDENCE 13 · ATTENDED-CAPTURE 31 · POLICY-OBSERVATION pending 19 · GEOGRAPHY 0 · MIXED RESORT 13 ·
PAID 0 · FOUNDER 0.

## 8. Theme-park / vacation-ownership safety (Phases 4, 5, 17)

| | |
|---|---|
| DISNEY-AREA QUALIFYING HOTELS | 76 (13 PF) |
| UNIVERSAL-AREA QUALIFYING HOTELS | 45 (11 PF) |
| KISSIMMEE QUALIFYING HOTELS | 100 (6 PF) |
| TIMESHARE EXCLUSIONS | 82 |
| VACATION-RENTAL EXCLUSIONS | 185 |
| MIXED RESORT HOLDS | 13 |
| AMBIGUOUS PREMISES HOLDS | 6 |

Rules: a census row must hold a DBPR HOTL/MOTL licence (the state's public-lodging class). Vacation-ownership
resorts without one (Disney Vacation Club villas, Marriott Vacation Club, Sheraton Vistana, HGV / Diamond,
Club Wyndham / WorldMark, Westgate, Bluegreen, Holiday Inn Club Vacations, …) are TIMESHARE exclusions;
vacation-ownership names that DO hold a hotel licence (Marriott's Lakeshore Reserve, HGV Las Palmeras,
WorldMark Kingstown Reef, Fantasy World villas, Barefoot'n) and CVB-listed condo-hotels without one
(Grove, Floridays, The Point, LBV Resort Village, Blue Heron Beach, Enclave, Palms Hotel & Villas) are
**MIXED RESORT HOLDS** (`AWAITING_CENSUS_REVIEW`, `lodging_state NEEDS_REVIEW`). A timeshare-named lead is never
attached to a hotel identity (BoardWalk Villas ≠ BoardWalk Inn; Beach Club Villas ≠ Beach Club Resort).
Campus merges never on brand/campus/phone: Swan, Dolphin and Swan Reserve are three identities; Marriott Village is
three hotels; dual-brand buildings (HGI + Home2 Downtown, Hampton + Home2 Lake Nona, Residence Inn + SpringHill
Millenia, Courtyard + Residence Inn Lake Nona, SpringHill + TownePlace LBV, Holiday Inn + Candlewood Lee Rd,
EVEN + Staybridge Universal Blvd) are two hotels each. **FAST 15 proves no TAPT/CNDO/DWEL unit licence, numbered
villa, timeshare, vacation-rental or resort-residence identity is in the census.**

Identity holds kept, not guessed: Motel 6 Kissimmee (two same-name licences, 5731/5733 W Irlo Bronson);
Super 8 / Travelodge single licence; Courtyard at Marriott Village (umbrella CVB listing at its address);
Aloft SeaWorld (legal-entity licence beside Element); Grand Bohemian → "Hotel Beauden" licence (rebrand unconfirmed).
Rebrand confirmed and bound: Celebration Hotel → The Inn at Celebration (licence, CVB, OSM and first-party site agree at 700 Bloom St).

## 9. Evidence (Phases 11–14)

144 evidence records over 145 stored pages; every page body is retained (`raw_captures/evidence_pages_001.jsonl.gz`)
with requested/final URL, lane, timestamp, sha256, byte length, operative quote, facts and decision.

| Lane | Records |
|---|---|
| attended browser, same-origin fetch on hilton.com (hotel-info pages) | 105 |
| plain HTTPS client, property's own site / brand property page | 39 |

Decisions: PET_FRIENDLY 103 · NO_PETS 2 · EVIDENCE_HOLD 16 · SILENT (client-rendered policy card) 22 · FETCH_FAILED 1.

Policy safety as run:
- Acceptance/refusal comes only from the **shared** `prose_facts.extract_pets_allowed`; facts from the shared
  count/weight/species/fee readers and `prose_fee_ladder`. Neither was modified.
- The shared acceptance pattern cannot see negation. On real Orlando pages it reads *"The hotel is not
  pet-friendly"* and *"We currently do not allow pets"* as acceptance. The Orlando layer overrules such a
  reading **toward EVIDENCE_HOLD only** and preserves the wording. It never overrules toward publication.
- Wording the shared reader declines ("pets are prohibited", "do not allow pets", "No pets allowed at …",
  "unable to accommodate pets") → EVIDENCE_HOLD with wording kept; it is **not** promoted to no-pets.
- Headings, amenity chips ("petsAllowed", "Pets not allowed" chips), marketing adjectives and fees/counts alone
  never decide anything (Alfond Inn heading, Holiday Inn Resort LBV fee list → holds).
- Labelled Hilton card values (e.g. "Non-refundable fee: $75.00", "Max weight: 75 lbs") are recorded as labels,
  with unstated basis/scope left absent.

## 10. Quality challenge (Phase 16)

The DBPR registry is the completeness authority (licensing is mandatory for Florida public lodging); every
other lane was reconciled against it. Unexplained gaps are listed, not absorbed: 74 OSM/CVB hotel leads with no
active HOTL/MOTL licence located (e.g. Wyndham Orlando Resort I-Drive, StaySky Suites I-Drive, Clarion Suites
Maingate, Destiny Palms, Champions World, Maingate Lakeside, Red Lion Kissimmee, Best Western Orlando West) are
`REVIEW` and must return through first-party verification plus a licence lookup; 10 are stale OSM brand names at a
licensed premises (REBRAND). Competitor directories were not used; no raw-count parity was chased.

## 11. Shadow package, reproduction, FAST (Phases 18–20)

| | |
|---|---|
| SHADOW PACKAGE CREATED | YES — `staging/orlando-fl/shadow_packages/pkg-orlando-fl-b5667776c6e8df99.json` (`SHADOW_UNTIL_REGISTERED`, `production_selectable: false`) |
| PACKAGE DIGEST | `sha256:b5667776c6e8df99a6e2ac1989ccb7660dbf524e2dd7ba3963ab05741c9f88c8` (manifest of 9 inputs + 6 code files + 9 outputs) |
| REPRODUCTION RUN A | independent process, no cache, temp out-root: 9/9 outputs byte-identical |
| REPRODUCTION RUN B | clean detached worktree at `9fecd09a` (autocrlf checkout), fresh process: 9/9 byte-identical |
| BYTE IDENTICAL | YES |
| NONDETERMINISTIC FILES | none (sorted serialisation, LF, gzip mtime 0, no wall-clock or machine paths in outputs) |

FAST — **15 / 15 PASS, 0 UNKNOWN, 0 FAILED**:
census.validate (FL) · partition.validate · partition.reconcile · key collisions · identity_routing shard ·
hotel_exclusions shard · markets.contract.parse_market · no non-FL/OUTSIDE rows · corridor assignment complete ·
orlando-fl absent from live registry/shards · zero drift in generated globals · byte-reproducible rebuild ·
git status Orlando-only · evidence integrity (every terminal row re-hashed against a stored first-party page) ·
lodging safety + accounting reconciles.

## 12. Parallel-run safety (Phase 21)

| | |
|---|---|
| CROSS-MARKET FILE CHANGES | 0 |
| SHARED FACTORY FILE CHANGES | 0 |
| CANONICAL LIVE CHANGES | 0 |
| DEPLOYMENT STATE CHANGES | 0 |

`git diff --stat c236f52d` touches only `scripts/pettripfinder/orlando_fl_*`, `markets/staging/orlando-fl/**`,
`markets/reports/orlando_fl_*` and this report. `market_authority.check_generated_artifacts() == []`.

## 13. Blockers and operator notes

1. **Attended browser capture on marriott.com was denied by the Claude Code permission classifier**
   ("Browser JS Exfil") when installing the same same-origin capture that had just succeeded on hilton.com; a
   follow-up status read in the browser was also denied. I did not retry on other origins. Consequence: Marriott
   (~120), IHG, Hyatt, Choice, Best Western, Wyndham, Red Roof, Motel 6 properties sit in `ACCESS_BLOCKED` (149)
   with their property URLs bound. If the operator wants this lane, a permission rule for the local capture relay
   is needed; no work-around was attempted.
2. Disney and Universal resort pages are client-rendered shells to a plain client → `AWAITING_ATTENDED_CAPTURE`.
3. 177 licensed hotels have no official URL in any lane (largely DBPR-only independents / motels) → `AWAITING_OFFICIAL_URL`.
4. Shared-reader negation blindness (section 9) is recorded as a factory observation; the shared reader was not changed.

## 14. Future registration / reseal steps (NOT performed)

1. Read CURRENT VERIFIED LIVE; discard `current_live_parent_context` (`cf6cdded`) if stale.
2. Register `orlando-fl`: copy `staging/orlando-fl/launch_package/markets/orlando-fl.json` and
   `markets/authority/orlando-fl/*` into the live tree; run `build_global_authority --write` then `--check`.
3. Add the market's participation, release-contract and build-closure entries (both shared documents).
4. Freshly reseal census/partition against the then-current parent; re-run FAST.
5. Optional before release: attended capture for the 149 ACCESS_BLOCKED and 31 attended-capture rows; resolve
   the 6 identity and 13 mixed-resort holds; URL discovery for the 177 no-URL rows; licence lookups for 74 REVIEW leads.
6. Compose candidate → independent reproduction → founder packet → await exact candidate authorization → deploy.

## FINAL ANSWERS

1. START TIMESTAMP = 2026-09-15T04:23:42Z
2. ZERO_TO_SOURCE_READY = 2h 56m 24s
3. TOTAL DISCOVERED = 1,117
4. PROPOSED CENSUS = 545
5. VALID PET-FRIENDLY = 87
6. VALID VERIFIED-NO-PETS = 2
7. RESOLVED / UNRESOLVED = 89 / 456
8. HOLDS BY CLASS = identity 6 · routing 225 · access-blocked 149 · evidence 13 · attended-capture 31 · policy-observation 19 · geography 0 · mixed resort 13 · paid 0 · founder 0
9. CORRIDOR COVERAGE = 23 corridors, 545 rows; 8 page-eligible (Downtown, MCO, I-Drive, Convention Center, Universal, Lake Buena Vista, South Orlando, Lake Mary–Sanford)
10. DISNEY / UNIVERSAL / KISSIMMEE COVERAGE = 76 (13 PF) / 45 (11 PF) / 100 (6 PF)
11. VACATION RENTAL / TIMESHARE EXCLUSIONS = 185 / 82 (+1 resort residence, 13 mixed-resort holds)
12. OWNED EVIDENCE REUSED = 0 policy evidence; owned DBPR adapter + 136 owned Marriott codes reused
13. SHADOW PACKAGE CREATED = YES
14. PACKAGE REPRODUCIBLE = YES (runs A and B byte-identical)
15. PACKAGE DIGEST = sha256:b5667776c6e8df99a6e2ac1989ccb7660dbf524e2dd7ba3963ab05741c9f88c8
16. APPLICABLE FAST CHECKS = 15 / 15 PASS, 0 UNKNOWN, 0 FAILED
17. PAID PROVIDER COST = $0
18. FOUNDER INTERVENTION REQUIRED = NO (operator permission needed only to widen the attended browser lane — section 13)
19. CROSS-MARKET FILE CHANGES = 0
20. FACTORY CODE CHANGED = NO
21. BROAD REGRESSION RUN = NO
22. FINAL PRODUCTION CANDIDATE CREATED = NO
23. FOUNDER AUTHORIZATION CREATED = NO
24. ORLANDO DEPLOYED = NO
25. BLOCKED ONLY ON RELEASE QUEUE = YES
26. origin == HEAD = YES (verified after push)
27. tree clean = YES (verified after push)

ORLANDO SOURCE READY = YES
ORLANDO FINAL CANDIDATE = NO
ORLANDO DEPLOYED = NO
BROAD REGRESSION RUNS = 0
FACTORY CODE CHANGED = NO
WAITING FOR RELEASE QUEUE = YES
