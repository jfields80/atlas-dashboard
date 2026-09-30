# PTF-AUSTIN-TX-HARDENED-SOURCE-READY-001 — FINAL

**Austin / Central Texas** (`austin-tx`) is the first Texas market. It was built from zero to a market-local SHADOW
package on the Phoenix-live lineage, and that package was reproduced independently. Worktree
`C:\Atlas-Austin-TX-Hardened-V1`, branch `worker/ptf-austin-tx-market-001`. Austin is not registered, not
authorized and not deployed.

| | |
|---|---|
| Shadow package | `pkg-austin-tx-3030caf7703a9c57` (`sha256:3030caf7703a9c574c14177ebcb072bbd691e94a518f6b68a045506482026331`), SHADOW_UNTIL_REGISTERED |
| Sealed from | `cb8bb6d2` (every staged input committed); sealed twice in-process with one digest; `--stage` re-derived the staged inputs byte-identical (fixed point) |
| FAST | **15/15 PASS, 0 UNKNOWN, 0 FAILED**; receipt `sha256:0149facb…9952`, currently ELIGIBLE (`eligible_receipts` returns it) |
| Rule J (non-empty) | PASS: 1,157 files, 1,141 HTML, output present, 0 output defects; bundle `6cc8b825…ced7` (not the empty `e3b0c442`); 12 corridor pages and the policy-comparison page; 0 warnings, 0 broken internal links, 0 quality-gate failures |
| Rule K (non-vacuous) | PASS: BYTE_IDENTICAL, 4 cold builds, 0 reuse hits |
| First-party gate (rule C) | 249/249 eligible |
| Independent reproduction | Detached worktree, separate OS process, separate work dir. Same package id, digest and bundle; 15/15. **FILES COMPARED 8, DIFFERING FILES 0** |
| Census / published | 407 identities: **190 pet-friendly + 59 verified no-pets** = 249 resolved (61.18 %); 158 unresolved |
| Actionability | **ACTIONABLE UNRESOLVED 0**: 50 router-exhausted, 80 need new spend, 28 need a founder decision, 0 held until opening |
| Coverage | **FOUNDER DECISION** (mechanical; see §9) |

## 0. How this order ran (read first)

This order was first issued at **2026-09-30T15:28:01Z** to a session rooted in the Phoenix worktree (transcript
`56c255fd`). That session built the Austin modules and most of the lanes directly in this worktree. The user then
interrupted it at 18:29:32Z, mid-recording, and re-issued the order to this session at about 18:54Z.

- Phase 1 requires a clean tree. The tree was **not** clean: it held 52 untracked, Austin-owned paths, the first
  session's uncommitted work.
- Deleting them would have destroyed about 195 recorded attended-browser reads and 50 Firecrawl credits of
  captures (the standing rule is pay once per page). So they were **audited and continued**, not discarded.
- The first session's transcript was read to establish exactly what it had done. The one read it never recorded
  (HomeTowne Studios) was re-read, not transcribed.
- Nothing outside the Austin paths had been touched.

The audit then found and fixed the defects in §6. Every timestamp here is real-clock.

## 1. Lineage and current live (Phase 1)

**Branch and lineage.** The branch is `worker/ptf-austin-tx-market-001` on `0e309868`, the tip of
`worker/ptf-phoenix-az-market-001` (PHOENIX IS LIVE). The Phoenix live source `e2d45272` is an ancestor. There was
no merge in progress and no reset to `origin/main`, which is stale: it does not contain live.

**Current verified live**, re-resolved by this session with the committed resolver
(`release_index live-source --verify-host`, recorded as `markets/reports/austin_tx_current_live_001.json`):

- Phoenix: deploy `6abc8387e81507b25eb94a0a`, source `e2d45272`
- bundle `19234b7a…1f78`, sitemap `647596dc…2ecb`
- **37 markets / 3,210 profiles / 3,549 release-index routes / 3,619 served routes**
- host verified: YES

The shadow package's `parent_live_state` names that release. Once a later market goes live, FAST rule N fails this
package BY DESIGN, and the registration order re-seals the same committed inputs as a new package id.

**Commits on this branch:**

1. `cb8bb6d2`: staged inputs. This covers the census, the staged policy package and authority, the shard
   documents, the partition, every Austin module and report, the raw captures, and the live-scan finding (§12).
2. `6050ffe1`: the shadow package, its receipt and the shadow report.
3. This report, the reproduction record, the seven machine-readable accountings, and the current-live record.

## 2. Geography (Phases 2–4, 25)

**Corridors.** 20 corridors over 67 ZIPs: 8 CORE, 8 STRONG CORRIDOR and 4 FRINGE. Membership is decided by the
property's OWN postal code, never by name, and a ZIP is never split.

- **CORE:** Downtown Austin, South Congress & Zilker, East Austin & Mueller, UT & Central, The Domain & North
  Austin, Arboretum & Northwest, South Austin, Austin-Bergstrom Airport (AUS).
- **STRONG CORRIDOR:** Round Rock, Pflugerville, Cedar Park, Georgetown, Lakeway & Bee Cave, Westlake / West Lake
  Hills, Buda, Kyle.
- **FRINGE:** Leander, Hutto, Manor, Dripping Springs.

**Hill Country ruling.** The metro-continuous Lake Travis south shore (Lakeway / Bee Cave / Hudson Bend / Steiner
Ranch; 78734 / 78738 / 78732) is a STRONG CORRIDOR. Dripping Springs and the US-290 Belterra corridor are FRINGE.
The destination Hill Country is OUTSIDE.

**Refused by their own postal code or municipality.** Fredericksburg, Johnson City, Wimberley, Marble Falls /
Horseshoe Bay, Spicewood, Burnet / Llano and Lake Buchanan are refused. So are the careful-evaluation towns the
evidence did not support: Bastrop, Elgin, Liberty Hill and Taylor.

**Name traps, measured.**

- TownePlace "Round Rock" states Austin 78728.
- Fairfield "Cedar Park" states Leander 78641.
- Postcard Cabins "Hill Country" states Wimberley 78676.
- Two "Austin Airport" hotels state 78744 (South Austin).

Uncorridored admitted rows: **0**.

| corridor | class | census | PF | NP | unresolved | resolution | page publishes (≥ 5 PF) |
|---|---|---:|---:|---:|---:|---:|---|
| Downtown Austin | CORE | 49 | 27 | 5 | 17 | 65.3 % | yes |
| South Congress & Zilker | CORE | 18 | 6 | 1 | 11 | 38.9 % | yes |
| East Austin & Mueller | CORE | 18 | 7 | 2 | 9 | 50.0 % | yes |
| UT & Central | CORE | 24 | 6 | 2 | 16 | 33.3 % | yes |
| The Domain & North Austin | CORE | 63 | 30 | 8 | 25 | 60.3 % | yes |
| Arboretum & Northwest | CORE | 45 | 29 | 7 | 9 | 80.0 % | yes |
| South Austin | CORE | 42 | 20 | 10 | 12 | 71.4 % | yes |
| AUS Airport | CORE | 28 | 13 | 1 | 14 | 50.0 % | yes |
| Round Rock | CORRIDOR | 34 | 21 | 8 | 5 | 85.3 % | yes |
| Pflugerville | CORRIDOR | 9 | 1 | 2 | 6 | 33.3 % | no |
| Cedar Park | CORRIDOR | 12 | 7 | 3 | 2 | 83.3 % | yes |
| Georgetown | CORRIDOR | 14 | 9 | 2 | 3 | 78.6 % | yes |
| Lakeway & Bee Cave | CORRIDOR | 14 | 5 | 1 | 8 | 42.9 % | yes |
| Westlake / West Lake Hills | CORRIDOR | 3 | 0 | 0 | 3 | 0 % | no |
| Buda | CORRIDOR | 7 | 2 | 2 | 3 | 57.1 % | no |
| Kyle | CORRIDOR | 6 | 2 | 1 | 3 | 50.0 % | no |
| Leander | FRINGE | 5 | 1 | 2 | 2 | 60.0 % | no |
| Hutto | FRINGE | 3 | 3 | 0 | 0 | 100 % | no |
| Manor | FRINGE | 2 | 0 | 1 | 1 | 50.0 % | no |
| Dripping Springs | FRINGE | 11 | 1 | 1 | 9 | 18.2 % | no |

12 corridor pages publish. No thin page is forced: a corridor with fewer than 5 pet-friendly profiles publishes no
page, and its hotels still publish as profiles.

**Boundary audit (Phase 25).** Every OUTSIDE graph node is counted by the refused place its own postal code or
municipality names.

| refused place | discovered | admitted |
|---|---:|---:|
| San Antonio | 313 | **0** |
| Waco | 67 | **0** |
| Fredericksburg | 80 | **0** |
| San Marcos | 45 | **0** |
| New Braunfels | 41 | **0** |
| Other destination Hill Country | 111 | **0** |
| Other Central Texas (Bastrop, Elgin, Liberty Hill, Taylor, Lockhart, Killeen / Temple, College Station, La Grange) | 187 | **0** |
| Other Texas / out of state | 6 | **0** |

Rows admitted from a refused postal code: **0**.

## 3. Owned data, census lanes and exclusions (Phases 5–8, 10–12)

**Owned data first.**

- 0 owned Austin identities: this is the first Texas market.
- 77 owned Marriott MARSHA routes (AUS / ILE codes).
- 8,283 live identity names loaded for the cross-market collision pass.
- No prior Firecrawl or browser history for Austin pages.

**Census lanes: 3,643 raw observations.**

| lane | observations | note |
|---|---:|---|
| Texas Comptroller hotel-tax permits | 714 | data.texas.gov `hdzd-884n`, ACTIVE permits under hotel NAICS in admitted ZIPs; 274 closed permits never admitted |
| OSM | 1,297 | Geofabrik Texas extract (md5-verified) |
| Brand inventories | 261 | Marriott owned 77, Hilton city pages 70, brand sitemaps 114 |
| Visit Austin roster | 471 | its own Simpleview listings (464 in admitted ZIPs) |
| Competitor leads | 562 | BringFido, names only, 15 cities |
| Property pages | 338 | attended browser, static client, Firecrawl brand pages, Wyndham property service |

**Graph and admission.** The graph has 2,079 nodes, of which **407 are admitted**.

**Exclusions.**

| class | count |
|---|---:|
| Vacation rental (incl. serviced-apartment products Sonder East 5th and Placemakr / "Apartments by Hilton", refused by the brand's own route) | 90 |
| Timeshare / vacation ownership | 3 |
| Resort residence | 0 |
| Non-hotel (incl. the Bunkhouse Group corporate office, §6) | 138 |
| Outside | 969 |
| Name-only residue | 323 |
| Identity-review residue | 138 |
| Same-campus distinct entity (held, §5) | 11 |
| Closed | 0 |

**Vacation ownership (Phase 5).** Three identities are excluded as TIMESHARE:

- **Club Wyndham Austin** (516 W 8th St), excluded by the brand's own `wyndham-vacations` route segment. This is
  the Phoenix correction-003 lesson, applied as a rule.
- **WorldMark Austin** (805 Nueces St).
- **Raintree Inn & Suites.**

Vacation-ownership / timeshare profiles published: **0**.

**Sentral East Austin 1630.** Its own page is both "Hotel Suites" and "Apartment Suites … for stays of 1 night or
30+ nights". It is held as LODGING_CATEGORY_UNCONFIRMED for a founder ruling on the hotel / residence boundary.

**Cross-market collisions (Phase 12).** 12 rows are held because their final name is a bare or generic name a live
market already publishes:

- Bel-Air Motel, Budget Inn, Country Inn & Suites, Deluxe Inn, Extended Stay America, Holiday Inn Express &
  Suites, Inn Cahoots, Intown Suites, Motel 6, Quality Inn & Suites Airport, Sleep Inn & Suites, Studio 6.

**Published collisions: 0.**

**Preopening and closed (Phase 6).** Every census name, every page read, every brand card, the bureau roster,
Firecrawl's persisted pages and the independents' own pages were scanned for opening / coming soon / temporarily or
permanently closed / converted / rebranded wording.

- PREOPENING IDENTITIES FOUND = 0; PREOPENING PUBLISHED = 0.
- CLOSED IDENTITIES FOUND = 0 on a first-party closure statement; CLOSED PUBLISHED = 0.
- Retired routes are routing holds, never closures: Motel 6 legacy codes, La Quinta routes Wyndham's own
  property service lists as retired, and a parked domain.
- One building was proven **rebranded** on the brand's own page: 609 Chisholm Trail Rd, Round Rock (the permit
  register's and map's "Comfort Suites") is **Spark by Hilton Round Rock** (`ausrdpe`). It publishes under that
  trade name.

## 4. Acquisition (Phases 14–18)

**Static plain client.** 162 targets:

- VALID 15, ACCESS_DENIED 61, IDENTITY_MISMATCH 36, NAVIGATION_FAILED 25, POLICY_NOT_FOUND 11,
  UNEXPECTED_PAGE 9, UNHYDRATED 3, BLANK 2.

**Other free lanes.**

- **Independents' own policy / FAQ pages:** 64 targets, 39 bound, 26 with pet sentences.
- **Wyndham property service:** 49 routes selected, 35 read, 14 retired.

**Firecrawl** (existing plan credits, capped on attempts, floor 400) — **74 credits in total (687 → 613), USD 0**:

| run | attempts | result | credits |
|---|---:|---|---:|
| Route discovery | 18 Choice / IHG city pages | 50 routes | 8 |
| Brand pages (IHG) | 42 | 42 answered, 41 with their own address, 40 with pet sentences | 42 |
| Pass 001 | 26 | 2 publication-grade, 1 source-silent, 23 blocked / failed / mismatch | 24 |

- Pass 001 took only the router's cohort restricted to still-unresolved rows. 7 already-resolved rows and 14
  non-census rows were never bought.

**Places.** Not used. Its website field is new spend this month; the allowance renews 2026-10-01.

**Attended browser** (claude-in-chrome; navigate plus accessibility read or visual read only):

- 240 attempts, 204 reads.
- Challenges: 2 DataDome CAPTCHAs (ESA, never solved) and 1 Akamai interstitial (Hilton, never bypassed; the paced
  retry 33 minutes later served normally).
- 0 JS exfiltration, 0 relay.
- **Every capture time is stamped by the recorder from the real clock** (never typed): 2026-09-30T16:09:05Z to
  T20:01:37Z, none in the future.

| family | attempts | reads | note |
|---|---:|---:|---|
| Marriott | 80 | 74 | every in-market MARSHA route read |
| Hilton | 61 | 59 | incl. Spark Round Rock after one Akamai window |
| Choice (incl. WoodSpring) | 30 | 28 | Choice's own Austin / Round Rock directories and WoodSpring's own Austin directory used for routes |
| Independents | 26 | 17 | Bunkhouse ×5, Four Seasons, Fairmont, Commodore Perry, 1 Hotel, Driskill, Green Pastures, Kalahari, Sage Hill, Strickland Arms, Mountain Star, Walnut Forest, InTown; 3 dead / parked domains |
| Hyatt | 9 | 9 | |
| Motel 6 / Studio 6 | 7 | 0 | chip or templated card only; 4 legacy routes retired to the home page |
| Sonesta | 7 | 5 | 2 source-silent |
| Best Western | 5 | 2 | conditional statements |
| IHG | 5 | 2 | Hotel Indigo and HIE Round Rock read and bound; EVEN read (its row is a held same-campus row); Holiday Inn Midtown / Town Lake source-silent |
| ESA | 4 | 2 | DataDome re-arms within one page |
| Red Roof 3, Omni 2, Drury 1 | 6 | 6 | |

**Marriott closure (Phase 16).** Every in-market Marriott route the owned harvest and the brand's Texas sitemap list
was read, with 0 challenge denials. MARRIOTT ACTIONABLE REMAINING = **0**:

- 74 census rows: 48 PF, 18 NP, 8 held.
- The 8 held rows are 3 Marriott dual-brand buildings (AC / Otis, Aloft / Element, Courtyard / Residence Inn)
  plus the 2 Marriott halves of cross-brand campuses: the two TownePlaces (§5).

## 5. Dual-brand and shared-campus safety (Phase 11)

**Held inside the census (IDENTITY_MISMATCH_HOLD, 9 buildings / 18 rows).** Each half is proved by its own brand
code and page:

| premises | pair |
|---|---|
| 1901 San Antonio St | AC Hotel / The Otis |
| 109 E 7th St | Aloft / Element |
| 300 E 4th St | Courtyard / Residence Inn |
| 2033 E 5th St | Hampton / Home2 |
| 18700 Hilltop Commercial Dr | Home2 / Tru |
| 13501 Lyndhurst St | Hilton Garden Inn "Building 1" / TownePlace |
| 901 Little Texas Ln | Staybridge / TownePlace "Building #G" |
| 6711 E Ben White Blvd | Candlewood / Holiday Inn |
| 1408 Town Center | Hawthorn / La Quinta |

**Demoted to SAME_CAMPUS_DISTINCT_ENTITY (3 buildings / 6 rows).** The package contract's own co-located-distinct
proof cannot separate these, because Choice's alphanumeric codes and Wyndham's slug routes carry no code the shared
parser reads:

- 13205 Burnet Rd — Cambria / EVEN
- 2021 Cheddar Loop — Hawthorn / Wingate
- **15295 IH-35, Buda — Comfort Suites / Holiday Inn Express & Suites. BOTH had published** (§6.2)

**Founder action.** Publishing any of these needs a `same_campus_distinct_entity` row in the SHARED
`identity_resolutions.json`, which this order does not write.

DUAL-BRAND / SHARED-CAMPUS BUILDINGS = 12; ROWS = 24; PUBLISHED WITHOUT REVIEWED RULING = **0**;
FOUNDER-DECISION ROWS = 24.

## 6. Defects found and fixed in this market's own modules

1. **A refusal published as pet-friendly.**
   - Kalahari Round Rock's own FAQ reads "Are pets allowed? | … pets (including ESAs) are not permitted …".
   - The acceptance pattern matched the QUESTION's "pets allowed", and the refusal pattern missed the
     parenthetical, so the row was CLEAN_PET_FRIENDLY.
   - The shared reader (FAST rule C) classifies the same quote ELIGIBLE pet-friendly, so FAST would not have caught
     it.
   - Fixed in Austin's clean authority: a question clause is never acceptance, and three refusal shapes are read
     (the parenthetical, "pets cannot be accommodated", "can NOT accommodate … pets").
   - Kalahari is now held. Every disposition change was diffed and re-verified; Commodore Perry's genuine
     statements ("Two pets maximum are allowed", "Pets under 60 pounds are permitted") were added so a real
     acceptance is not lost.
   - **The same defect is live in other markets** (§12).
2. **Two hotels published at one premises.**
   - Comfort Suites Buda (PF) and HIE & Suites Buda (NP) sit at 15295 IH-35. The local street key kept "S IH-35"
     and "IH 35" apart.
   - The shared package writer refused the seal (SAME_PREMISES_UNPROVEN).
   - The census now groups admitted rows by the contract's own address key and holds every pair the contract cannot
     prove distinct.
3. **Identity.**
   - "Cambria/even Hotel … Bldg 1&2" is one tax permit for two hotels: now a combined-permit refusal.
   - The map's "Cambria Hotel Austin North" at 13201 Burnet is Choice's `txi94` building: superseded by that read.
   - "Bunkhouse Group" is the operator's corporate office (1711 S Congress, Suite 300): NON_HOTEL.
   - The "Comfort Suites" at 609 Chisholm Trail publishes as Spark by Hilton Round Rock.
   - Sentral East Austin 1630 is held for the hotel / residence ruling.
4. **Phoenix leftovers in the cloned modules.**
   - `OBSERVED_AT` (2026-09-29, now 2026-09-30) and `SEALED_AT` (2026-09-29T02:00Z, now 2026-09-30T20:05:00Z,
     after the last capture) both reach the package.
   - The staged package's market text still said "Phoenix / Scottsdale / Valley of the Sun".
   - The accounting's boundary audit was Arizona's and would have crashed on Austin's geography.
   - The actionability module's ESA / Motel 6 facts were Phoenix measurements; they were re-measured in Austin.
5. **A heredoc wrote three backspace bytes** where `\b` belonged, in a new census pattern. Found, fixed, and every
   Austin module scanned: 0 remain.
6. **A challenge attempt never bound to its row.** Visit Austin's ESA links carry a tracking query, so the DataDome
   attempt showed as "never attempted". Browser-lane route matching now drops query strings.

## 7. Policy and fee safety (Phases 13, 19)

**Inference rules.**

- Acceptance is never taken from a fee, weight, count, amenity chip or templated card: Motel 6's "Pets Allowed"
  and Studio 6's "Pet-Friendly Accommodation".
- Refusal is never taken from silence.
- An area rule ("not permitted in our restaurants or pool") is never a refusal.
- A competitor claim is never authority.

**Fees. 31 single-basis fees publish, 84 are withheld, and 0 misleading single fees are published.**

- **Withheld:** 60 tiered fees, and 24 unsafe single fees (basis not stated 18, stay-length condition 4, two
  bases 2).
- **Every published fee was re-checked against its own quote:** Drury's "daily fee" and East Austin Hotel's "$30
  per night" are per_night, and no nightly or daily fee is published as per-stay.
- **Multi-amount and capped fees are withheld:** Hotel Indigo's fee + deposit, HomeTowne's "$10 per night up to
  $100 a month", Mountain Star's $500 violation charge.
- **Weights:** The Driskill's one-dog 50 lb and two-dog 75 lb combined limits are kept apart, and never published as
  a universal weight.

## 8. Competitor challenge and large-market quality challenge (Phases 9, 26)

BringFido (audit lane only, never policy): 15 cities, **671 raw / 562 normalized / 137 matched (133 distinct) /
0 true missing**. 34 matches are policy-unresolved.

| class | count |
|---|---:|
| Exact | 120 |
| Alias | 13 |
| Duplicate | 4 |
| Vacation rental | 292 |
| Outside | 4 |
| Non-hotel | 8 |
| Stale | 1 |
| Review | 120 |

The 17 leads the automatic match left true-missing were each worked through the census graph and the brands' own
directories:

- **Four match census rows:** Austin Motel (its key normalises to empty), HIE North Central, Candlewood N-Cedar
  Park, and Comfort Suites Buda (a held same-campus row).
- **La Quinta University Area** is a route Wyndham's own property service lists as retired.
- **Motel 6 Georgetown** is the map's held bare-chain node.
- **Motel 6 Round Rock, Red Roof Manor and four small independents** have no address in any lane.
- **Five are rentals / Hill Country.**

MATERIAL IDENTITY GAP = **NO**.

**Large-market quality challenge.**

- Choice's own Austin and Round Rock directories, WoodSpring's own Austin directory, and Wyndham's retired-route
  list were read against the census. Two routes were closed that way: WoodSpring Northwest and Spark Round Rock.
- The airport corridor holds 28 census rows.
- Round Rock / North Austin: 34 + 63 rows.

## 9. Actionability (Phase 22, per row) and the coverage decision (Phase 27)

| disposition | total | actionable | exhausted | new spend | founder | held until opening |
|---|---:|---:|---:|---:|---:|---:|
| ROUTING_HOLD | 88 | 0 | 8 | 80 | 0 | 0 |
| EVIDENCE_HOLD | 29 | 0 | 19 | 0 | 10 | 0 |
| IDENTITY_MISMATCH_HOLD | 20 | 0 | 2 | 0 | 18 | 0 |
| SOURCE_SILENT | 15 | 0 | 15 | 0 | 0 | 0 |
| ACCESS_BLOCKED | 6 | 0 | 6 | 0 | 0 | 0 |
| **total** | **158** | **0** | **50** | **80** | **28** | **0** |

**80 need new spend.** 76 independents, 2 Choice, 1 Sonesta and 1 Radisson. No authorized lane states a route for
them; the only lane that would is Places `websiteUri`.

**28 need a founder decision.**

- **18 dual-brand rows (9 buildings).**
- **5 route rulings.** The Bunkhouse hotels' own domains redirect to bunkhousehotels.com / hyatt.com, so the
  route-domain rule holds them. Each page states acceptance.
- **5 refusals the SHARED reader cannot interpret:** Kalahari, Mountain Star, AT&T Hotel, Strickland Arms, Heywood.

Outside the census, 11 same-campus rows and Sentral's lodging ruling also await the founder.

**50 are router-exhausted.** This includes ESA (DataDome), Motel 6 (chip only), 15 source-silent pages, and the
"acceptance-wording-not-found" holds such as WoodSpring's fee-only lines.

**Coverage decision.** All coverage conditions are true: actionable 0; no material identity gap and no unexplained
policy gap; lanes exhausted; Marriott closed; browser cohorts bounded; preopening and vacation-ownership rows safely
excluded; dual-brand rows safely held; publication set safe; package reproducible and FAST clean.

The coverage contract still returns **FOUNDER DECISION** mechanically: 108 unresolved rows are reachable only
through new spend (80) or a founder ruling (28).

## 10. Reproduction (Phase 31)

**Setup.**

- Detached worktree `C:/t/atx1b-wt` at `6050ffe1`.
- A separate OS process (PowerShell `Start-Process`, pid 6484). Its process record was written before it started
  (`reproduction/independent_reproduction_process.txt`).
- Work dir `C:/t/atx1b`; the sealing run used `C:/t/atx1a`.
- The staged tree was re-derived with `--stage`.

**Results.**

- Same package id and digest.
- Same bundle `6cc8b825…`; rule J 1,157 / 1,141 / present in both runs.
- 15/15 and BYTE_IDENTICAL in both runs.
- Staged tree: **FILES COMPARED 8, DIFFERING FILES 0**, byte-identical raw.
- Package file: identical after LF normalisation. The only raw difference is `core.autocrlf` on checkout.
- Receipt: 1,235 fields compared. The 32 that differ are wall-clock seconds, timestamps, environment, and the two
  cache `input_key`s (they hash the work-dir path); hence the receipt digest differs too.

The worktree and every scratch dir were removed afterwards.

## 11. Isolation, boundaries, performance and cleanup (Phases 33–34)

**Changed paths since `0e309868`.** These are Austin-owned only:

- scripts `austin_tx_*` and `discovery/config/austin_tx.json`
- reports `austin_tx_*`
- `markets/staging/austin-tx/`
- the proposed census and proposed market
- this report

That is **0 shared, 0 cross-market, 0 live and 0 deploy paths.**

**Boundaries kept.**

- Not registered; no founder or deployment authorization; no production candidate; no whole-site build.
- Participation, pin and `identity_resolutions` untouched.
- 0 broad regression runs; USD 0; no new provider.

**Performance.**

- START: 2026-09-30T15:28:01Z (first issue). This session resumed at about 18:54Z.
- ZERO_TO_SOURCE_READY: **4h56m**. The FAST-clean shadow package was committed as `6050ffe1` at 20:24:47Z; that is
  about 1h31m within this session.
- ZERO_TO_COVERAGE_READY: not reached (FOUNDER DECISION).
- Active compute is dominated by the census-to-clean chain (about 7 minutes a run, 6 runs this session) and the
  two seals (about 5 minutes each).
- Provider / cooldown wait: the Hilton Akamai retry waited 33 minutes while other work continued. No idle wait was
  forced.
- Existing provider credits: 74 Firecrawl. New paid spend: 0. Provider cost: USD 0.
- Founder intervention: none requested.

**Cleanup.**

- The browser tab is closed and the tab group removed.
- The seal and reproduction processes exited; their work dirs, the reproduction worktree and every background
  watcher are gone.
- No timers, servers or child workers remain.
- Unrelated pre-existing processes were left alone: `C:\t\sink.py` (2026-09-14), the Netlify telemetry nodes,
  other Claude sessions, and the Codex runtime.

**Machine-readable accounting** (`markets/reports/`):

- `austin_tx_source_accounting_001.json`, `austin_tx_provider_accounting_001.json`,
  `austin_tx_brand_accounting_001.json`, `austin_tx_corridor_accounting_001.json`,
  `austin_tx_boundary_accounting_001.json` (sections of `austin_tx_source_ready_accounting_001.json`)
- `austin_tx_competitor_reconciliation_001.json`
- `austin_tx_actionability_001.json` (per row)
- `austin_tx_fee_withholding_001.json`
- `austin_tx_shadow_package_001.json`
- `austin_tx_current_live_001.json`
- `markets/staging/austin-tx/reproduction/`

## 12. FINDING OUTSIDE THIS ORDER'S SCOPE: live refusals published as pet-friendly

The Kalahari mechanism (§6.1) exists in the modules that built earlier markets and in the shared reader. A
**read-only** scan of every committed `hotel_policy_facts_*.json` (3,243 live pet-friendly records) found rows
published VERIFIED_PET_FRIENDLY whose only acceptance words sit in an FAQ question.

**9 whose own quote REFUSES pets:**

- **Fort Lauderdale:** Dolphin Hollywood ("we do not accept pets"), Honu Cove ("strictly prohibited"), Mariner
  Motel ("pet-free").
- **Tampa:** Bellweather Beach Resort ("a pet-free facility"), Bon Aire Motel Apts ("No, we do not allow pets"),
  Boutique Beach Retreat ("we can not allow pets"), Crystal Palms Beach Resort ("not allowed on property"), Sunset
  Vistas Beachfront Suites ("pets aren't allowed"), Hotel South Tampa & Suites ("strict no-pet policy").

**2 whose quote is only a question or a referral:** Clevelander South Beach and Essex House (Miami).

**4 to review:** Vacation Village at Parkway (Orlando; conditional, and a vacation-village name), The Quinn
(Phoenix; "community"), The Scott (Phoenix; acceptance is real) and AKA West Palm.

The full list, with quotes and source URLs, is in `markets/reports/austin_tx_live_question_acceptance_finding_001.json`.

This order may not modify another market, the shared reader or live. **These pages are live and tell pet owners the
opposite of the hotel's own policy.** They need a correction order, and the shared `first_party_binding` reader
needs the question rule.

## FINAL ANSWERS

1. START TIMESTAMP = 2026-09-30T15:28:01Z (order first issued; this session resumed it at about 18:54Z, §0)
2. ZERO_TO_SOURCE_READY = 4h56m (FAST-clean shadow package committed `6050ffe1` at 20:24:47Z)
3. ZERO_TO_COVERAGE_READY = not reached. Coverage is FOUNDER DECISION; the mechanical decision was reached with the source-ready package (4h56m)
4. CURRENT LIVE DEPLOYMENT = Phoenix, deploy 6abc8387e81507b25eb94a0a (source e2d45272, bundle 19234b7a…, sitemap 647596dc…), host verified
5. CURRENT LIVE MARKETS = 37 (3,210 profiles / 3,549 release-index routes / 3,619 served routes)
6. TOTAL DISCOVERED = 3,643 raw observations
7. NORMALIZED IDENTITIES = 2,079 graph nodes
8. QUALIFYING CENSUS = 407
9. PET-FRIENDLY = 190
10. VERIFIED NO-PETS = 59
11. RESOLVED = 249
12. UNRESOLVED = 158
13. RESOLUTION RATE = 61.18 %
14. ACTIONABLE UNRESOLVED = 0
15. HOLDS BY CLASS = IDENTITY 20 (18 of them dual-brand), ROUTING 88, ACCESS_BLOCKED 6, EVIDENCE 29, SOURCE_SILENT 15, NEGATION 0, BROWSER_CAPTURE 0, POLICY_NOT_FOUND 0, PREOPENING 0, GEOGRAPHY 0
16. EXCLUSIONS BY CLASS = vacation rental 90, timeshare 3, resort residence 0, non-hotel 138, outside 969, name-only residue 323, identity-review residue 138, same-campus distinct entity 11, closed 0
17. PREOPENING IDENTITIES = 0
18. PREOPENING PUBLISHED = 0
19. VACATION-OWNERSHIP / TIMESHARE IDENTITIES = 3 (Club Wyndham Austin, WorldMark Austin, Raintree Inn & Suites); plus serviced-apartment products refused as rentals (Sonder East 5th, Placemakr Apartments by Hilton) and Sentral held for a ruling
20. VACATION-OWNERSHIP / TIMESHARE PUBLISHED = 0
21. PUBLISHING CORRIDORS = 12 of 20
22. COMPETITOR RAW / NORMALIZED / MATCHED / TRUE MISSING = 671 / 562 / 137 / 0
23. MATERIAL IDENTITY GAP = NO
24. MATERIAL POLICY GAP = NO
25. FIRECRAWL ATTEMPTED / SUCCESS = 86 / 53 (discovery 18 pages → 50 routes, 8 billed; brand pages 42 attempted / 42 answered, 41 with their own address; pass 001 26 attempted / 2 publication-grade + 1 source-silent); 74 credits
26. MARRIOTT CENSUS = 74
27. MARRIOTT BROWSER ATTEMPTED = 80
28. MARRIOTT READ SUCCESS = 74
29. MARRIOTT CHALLENGE DENIED = 0
30. MARRIOTT ACTIONABLE REMAINING = 0 (66 resolved; 8 terminally held: 3 Marriott dual-brand buildings and 2 cross-brand campuses)
31. OTHER BROWSER ATTEMPTED / SUCCESS = 160 / 130
32. DUAL-BRAND / SHARED-CAMPUS HOLDS = 12 buildings / 24 rows (9 buildings held in the census, 3 demoted to same-campus), 0 published without a ruling
33. SINGLE-BASIS FEES PUBLISHED = 31
34. TIERED FEES WITHHELD = 60
35. UNSAFE / MULTI-AMOUNT FEES WITHHELD = 24 unsafe single fees (basis not stated 18, stay-length condition 4, two bases 2); the multi-amount fees are counted in answer 34
36. MISLEADING SINGLE FEES = 0
37. ACCESS_BLOCKED AFTER ROUTER EXHAUSTION = 6
38. EXISTING PROVIDER CREDITS USED = 74 Firecrawl credits (687 → 613)
39. NEW PAID SPEND = 0
40. PROVIDER COST = USD 0 (existing Firecrawl plan only)
41. RULE J NONEMPTY = PASS (1,157 files / 1,141 HTML / output present / 0 output defects)
42. RULE K NONVACUOUS = PASS (BYTE_IDENTICAL, 4 cold builds, 0 reuse)
43. FAST RECEIPT CURRENTLY ELIGIBLE = YES (`eligible_receipts` returns it; current rule J 0 defects; 0 UNKNOWN)
44. SHADOW PACKAGE CREATED = YES, pkg-austin-tx-3030caf7703a9c57, SHADOW_UNTIL_REGISTERED
45. PACKAGE REPRODUCIBLE = YES (in-process two-seal, and independent reproduction: BYTE IDENTICAL, DIFFERING FILES 0)
46. PACKAGE DIGEST = sha256:3030caf7703a9c574c14177ebcb072bbd691e94a518f6b68a045506482026331
47. FAST = 15/15 PASS, 0 UNKNOWN, 0 FAILED
48. TECHNICAL SOURCE READY = YES
49. COVERAGE READY = FOUNDER DECISION
50. CROSS-MARKET FILE CHANGES = 0
51. FACTORY CODE CHANGED = NO
52. BROAD REGRESSION RUNS = 0
53. FINAL PRODUCTION CANDIDATE CREATED = NO
54. FOUNDER AUTHORIZATION CREATED = NO
55. AUSTIN DEPLOYED = NO
56. origin == HEAD = YES (verified after the final push)
57. tree clean = YES (verified after the final push)

```
AUSTIN SOURCE READY = YES
AUSTIN COVERAGE READY = FOUNDER DECISION
ACTIONABLE UNRESOLVED = 0
PREOPENING PROFILES PUBLISHED = 0
VACATION-OWNERSHIP / TIMESHARE PROFILES PUBLISHED = 0
MISLEADING SINGLE FEES = 0
RULE J NONEMPTY = PASS
RULE K NONVACUOUS = PASS
FAST = 15/15 PASS, 0 UNKNOWN, 0 FAILED
FACTORY CODE CHANGED = NO
BROAD REGRESSION RUNS = 0
AUSTIN FINAL CANDIDATE = NO
AUSTIN DEPLOYED = NO
WAITING FOR RELEASE QUEUE = YES
```
