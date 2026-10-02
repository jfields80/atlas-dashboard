# PTF-SAN-ANTONIO-TX-HARDENED-SOURCE-READY-001 — FINAL

**San Antonio / Greater San Antonio, Texas** (`san-antonio-tx`) was built from zero to a market-local SHADOW package
on the Austin-live lineage, and that package was reproduced independently. Worktree
`C:\Atlas-San-Antonio-TX-Hardened-V1`, branch `worker/ptf-san-antonio-tx-market-001`. San Antonio is not
registered, not authorized and not deployed.

| | |
|---|---|
| Shadow package | `pkg-san-antonio-tx-b6018714bcc2bd44` (`sha256:b6018714bcc2bd44073a6832ab47033904526b4e88bb7cf9ca315f0d6268ed36`), SHADOW_UNTIL_REGISTERED |
| Sealed from | `823e0ba4` (every staged input committed); sealed twice in-process with one digest; `--stage` re-derived the staged inputs byte-identical (fixed point) |
| FAST | **15/15 PASS, 0 UNKNOWN, 0 FAILED**; receipt `sha256:54a176a9…6c00`, currently ELIGIBLE (`eligible_receipts` returns it; stored ELIGIBLE = YES; Rule J PASS; no UNKNOWN rules) |
| Rule J (non-empty) | PASS: 884 files, 868 HTML, output present, 0 output defects; bundle `f9b4c610…2123` (not the empty `e3b0c442`); 12 corridor pages and the policy-comparison page; 0 warnings, 0 broken internal links, 0 quality-gate failures |
| Rule K (non-vacuous) | PASS: BYTE_IDENTICAL, 4 cold builds, 0 reuse hits (Rule K cannot qualify after a Rule J failure; J passed) |
| First-party gate (rule C) | 242/242 eligible (144 pet-friendly + 98 verified no-pets), 0 ineligible |
| Independent reproduction | Detached worktree at `823e0ba4`, separate OS process, separate work dir (`C:/t/sa2`). Same package id and digest, same bundle; 15/15. **DATA DIFFERENCES 0 (17 files), SITE DIFFERENCES 0 (1,892 files), BYTE IDENTICAL = YES** |
| Census / published | 414 identities: **144 pet-friendly + 98 verified no-pets** = 242 resolved (58.45 %); 172 unresolved |
| Actionability | **ACTIONABLE UNRESOLVED 0**: 159 router-exhausted, 0 new spend, 0 new provider, 9 founder rulings safely held, 4 held until opening |
| Coverage | **YES** — every Phase 28 condition holds (see §9); 9 founder-ruling rows and 4 pre-opening rows are safely held, as the order's own conditions allow |

## 0. How this order ran (read first)

The order was issued at **2026-10-02T14:06:51Z** to a session in this worktree (transcript `5759d611`). That session
verified lineage, built every San Antonio module from the Austin source-ready modules, and ran geography, the
Comptroller permit register, OSM, owned data, the brand inventories, Visit San Antonio's roster, BringFido, the IHG
route discovery, census pass 1, routing, the Wyndham, static and policy-page lanes, all 53 Marriott routes and 24 of
53 Hilton routes in the attended browser. Its terminal was closed at about 15:38Z, mid-Hilton.

This session (`3faaac14`, from about 16:05Z) was told to recover and continue, not restart:

- The tree held 82 untracked, San Antonio-owned paths and no tracked change. They were **audited and continued**.
- The first session's transcript was read to recover the exact work order, every lane it ran and the browser
  method. The three Hilton pages whose batch it never recorded (Schertz, Homewood Airport, HGI Airport South) were
  **re-read**, not transcribed.
- No paid or provider acquisition was repeated: the Places lane now reuses every recorded answer, and the brand-page,
  Firecrawl and BringFido lanes were not re-run.
- Nothing outside the San Antonio paths was touched.

Every capture time is the recorder's real clock (seq 1 2026-10-02T15:05:25Z .. seq 213 18:00:33Z). Five notes that I
had typed with approximate clock times were stripped of those times before commit, because one of them was later
than the recorder's own stamp.

## 1. Lineage and current live (Phase 1)

- Branch `worker/ptf-san-antonio-tx-market-001` on `3afa9b17` (AUSTIN IS LIVE final), clean at start for the
  first session, no merge in progress, origin `jfields80/atlas-dashboard`. The Austin live source `f0ddbcde` is an
  ancestor; `origin/main` (`c236f52d`) does not contain live and was not used as authority.
- **Current verified live** (`release_index live-source --verify-host`, recorded as
  `markets/reports/san_antonio_tx_current_live_001.json`):

| | |
|---|---|
| CURRENT LIVE SOURCE COMMIT | `f0ddbcde437cd9dd2673ac19e06e2d71d55c20b5` (built from `ef28f7b4`) |
| CURRENT LIVE DEPLOYMENT | `6abf3e749cc359701298718d` (Austin, deployed 2026-10-02T05:18:15Z) |
| CURRENT LIVE BUNDLE | `75e569412dd28a64eb4c7aa02c58c955badf065833d969b1d18b8ed339fa31b0` |
| CURRENT LIVE SITEMAP | `d6461dbc2cd4bc225c52b235c5e4b675f78117b0b2e191463fe5c4baca2ef606` |
| CURRENT LIVE MARKETS / PROFILES | 38 / 3,386 |
| RELEASE-INDEX ROUTES / SERVED ROUTES | 3,737 / 3,808 |
| HOST VERIFIED | YES |

- **NEXT-MARKET AUTOMATIC BASE DERIVES = YES.** `registration_release_lane.derive_registration_base('san-antonio-tx',
  f0ddbcde)` returns **DERIVED BASE = `3afa9b17`** (the newest first-parent ancestor that contains the live lineage
  and names no San Antonio path). The Austin registration-base issue is cleared.

## 2. Geography (Phases 2–4, 25, 26)

19 corridors over **66 admitted postal codes** in Bexar, the Comal edge (Bulverde / Garden Ridge) and the Guadalupe
edge (Schertz / Cibolo / Selma): 14 CORE (Downtown / River Walk, Pearl / Broadway, Southtown, SAT Airport, Medical
Center, North Central, Stone Oak, Northwest / La Cantera, Six Flags / Rim, SeaWorld / Westover Hills, Lackland /
West, East Side, South Side, Northeast), 3 STRONG CORRIDOR (Live Oak / Universal City, Selma / Schertz, Leon Valley /
Helotes) and 2 FRINGE (Converse, Bulverde). Alamo Heights, Windcrest, Kirby, Balcones Heights, Castle Hills and
Shavano Park are inside the CORE codes. OUTSIDE / FUTURE_STANDALONE: Austin (live), New Braunfels / Gruene / Canyon
Lake, Seguin, San Marcos, the destination Hill Country (Boerne, Fair Oaks Ranch, Comfort, Kerrville, Bandera,
Fredericksburg, Wimberley, Johnson City), Castroville / Hondo, the rural outer ring (Von Ormy, Somerset, Lytle,
Elmendorf, Adkins, St Hedwig, Floresville, Pleasanton) and Corpus Christi. A property *marketed* "San Antonio Hill
Country" or "New Braunfels / San Antonio" is placed by its own address only. The live Austin geography and this one
share no postal code.

**Boundary audit (Phase 26)** — discovered / admitted, counted by each refused node's own postal code or municipality:

| place | discovered | admitted |
|---|---:|---:|
| Austin | 84 | 0 |
| New Braunfels | 143 | 0 |
| Seguin | 13 | 0 |
| Fredericksburg | 1 | 0 |
| San Marcos | 0 | 0 |
| Corpus Christi | 0 | 0 |
| Boerne | 16 | 0 |
| Other Hill Country | 83 | 0 |
| Castroville / Hondo | 9 | 0 |
| Rural outer ring | 35 | 0 |
| Other Texas / out of state | 40 | 0 |

Rows admitted from a refused postal code: **0**.

## 3. Owned data, census lanes and exclusions (Phases 5–9, 11)

**Owned data first.** OWNED IDENTITIES = 284 San Antonio nodes in Austin's committed graph (each refused there as
OUTSIDE), OWNED VALID POLICY EVIDENCE = 0, OWNED PROVIDER HISTORY = 17 Firecrawl ledgers (1,492 prior calls, one for
a San Antonio URL), OWNED ROUTES = 58 Marriott SAT routes from the owned harvest, OWNED REBRANDS = 0 applicable,
OWNED COLLISIONS = 4 (cross-market chain-name collisions checked in-market). The owned Geofabrik Texas extract was
reused (hard-linked, md5-verified).

**Census lanes** (2,902 raw observations, 1,440 graph nodes):

| lane | yield |
|---|---:|
| Texas Comptroller hotel-tax permits (`hdzd-884n`, active, admitted codes) | 930 |
| OSM / Geofabrik Texas extract | 612 (664 lodging elements) |
| Brand inventories (Marriott Texas sitemap, Hilton city pages, Wyndham, Drury, Sonesta, WoodSpring, owned harvest) | 248 |
| Visit San Antonio (Simpleview, measured) | 422 (438 listings) |
| BringFido (identity / gap only) | 373 |
| Places-verified competitor gaps | 6 |
| Brand / property pages (attended browser, Firecrawl, static) | 311 |

**Census 414** TRUE_HOTEL_IDENTITY. Non-admitted: 540 OUTSIDE, 101 NON_LODGING, 148 IDENTITY_REVIEW_REQUIRED, 230
NAME_ONLY_UNRESOLVED, 7 SAME_CAMPUS_DISTINCT_ENTITY.

**Exclusions by class:** VACATION_RENTAL 43, TIMESHARE 8 (Hilton Vacation Club Eilan, Hyatt Vacation Club Wild Oak
Ranch, Shell Vacations Club Salado Creek …), NON_HOTEL 50 (incl. 1 CONVERTED: the former Staybridge Suites at 6919
N Loop 1604 W is now Onyx at Oslo Apartments), MILITARY_RESTRICTED 9, OUTSIDE 540, RESORT_RESIDENCE 0, CLOSED 0.

San Antonio rulings this order added (`san_antonio_tx_nonhotel_rulings_001`, each citing what was read): eleven
permit-register short-term-rental hosts at bare residential premises (Places), Siegel Suites and Eckhert Place
(apartments / condominiums), two RV / mobile-home parks and Sun Retreats, Briggs Ranch Golf Club, Tejas Rodeo
Company, the American GI Forum, UIW's student engagement center, the Army Residence Community, a dinner-theatre show,
the Pearl district, The Espee (a music venue — its own domain redirects to ATG Tickets), Casa Azul & Casa Blanca
(whole-house rentals), and the converted Staybridge. Three rows stay IDENTITY_REVIEW_REQUIRED (Siegel Select / the
former Sonesta Simply Suites Northwest — the hotel / residence boundary; two unconfirmed permits).

**Military / government lodging (Phase 5).** The three installation postal codes (78236 JBSA-Lackland, 78234
JBSA-Fort Sam Houston, 78150 JBSA-Randolph) and the on-base names (Gateway Inn, Lackland Gateway …) are
MILITARY_RESTRICTED: PUBLICLY BOOKABLE HOTEL = NO, PUBLIC ACCESS = NO, RESTRICTED ELIGIBILITY = YES, ON-BASE = YES,
ORDINARY HOTEL CONTRACT SATISFIED = NO. 9 identities refused, 0 admitted. Public commercial hotels outside the gates
(the Lackland / SeaWorld and Fort Sam corridors) are ordinary census rows.

**Preopening / closed / rebrand (Phase 7).** PREOPENING IDENTITIES = 5: The St Paul San Antonio (Hilton Outset,
"accepting reservations for January 3, 2027"), Homewood Suites at the Rim (Hilton's own card: open = false,
2027-02-05), Perlen House ("Opening 2027"), Sitio El Tropicano ("Opening Late 2026") — all four held in the census,
never verified no-pets — and Hotel St. Marys ("Coming Soon", held outside the census as a same-campus row).
**PREOPENING PUBLISHED = 0.** CLOSED IDENTITIES = 0 on a first-party closure statement; retired / dead routes are
routing holds, never a closure claim. **CLOSED PUBLISHED = 0.** REBRANDS RESOLVED = 11 (each by the premises' own
brand page): Super 7 Inn → Red Roof Inn E Frost Bank Center (RRI1153), Mi Casa Inn → Motel 6 I-35 North Corridor,
Atrium Inn → Best Western Plus Atrium Inn, Best Western Inn & Suites → BW Plus Roland Inn, BW Plus Fiesta Inn →
SureStay Plus Fiesta, SureStay West SeaWorld → Best Western SeaWorld, SureStay Plus SeaWorld → BW Sea World /
Lackland NW, Hillview Inn → Home Suites Hill Country, Hampton Northwoods → Hampton Stone Oak, Aiden by Best Western →
The St Paul (Hilton, preopening; held), the former Staybridge → apartments (converted).

## 4. Acquisition (Phases 15–19)

**Router.** The committed hardened router governs; no San Antonio bypass.

**Free lanes.** Static plain client 157 targets; independents' own policy / FAQ pages 48 targets (16 bound); Wyndham property
service 50 read; Places-found independent sites 33 targets (22 bound).

**Google Places** (existing `GOOGLE_PLACES_API_KEY`): route discovery was run because its Enterprise-SKU website field
draws on a free monthly allowance that renewed 2026-10-01 and that no worktree on this machine had used this month.
201 requests in total (187 Enterprise route discovery + 14 PRO gap verification), 0 errors; 160 routeless or
dead-route identities queried, 142 bound by house number + ZIP, 92 with a website. Every rerun reuses every prior
answer (pay once). New paid spend: none.

**Firecrawl** (existing plan credits, floor 400). STARTING CREDITS = 613, ENDING CREDITS = 503, **110 credits, USD 0**:

| run | attempts | result | credits |
|---|---:|---|---:|
| BringFido gap challenge | 11 city pages + suburbs | 421 raw leads | 53 |
| Choice / IHG route discovery | 16 pages | 230 IHG routes (Choice refused at 0 cost) | 8 |
| IHG brand pages | 35 | 35 answered, 35 with own address, 32 with pet sentences | 35 |
| Residual pass 001 | 15 | 1 publication-grade (stayAPT), 1 source-silent, 13 blocked / failed / mismatch | 14 |

ELIGIBLE 50, ATTEMPTED 50 property pages, SUCCESS 36 (35 brand pages + 1 publication-grade), PUBLICATION-GRADE 1,
IDENTITY / ADDRESS SUPPORT 35, FAILED 13.

**Attended browser** (claude-in-chrome; navigate + accessibility tree / page text / zoomed screen only; 0 JS
exfiltration, 0 relay, 0 challenge solved or bypassed): **213 attempts, 173 reads**, recorder stamps
2026-10-02T15:05:25Z .. 18:00:33Z.

| family | attempts | reads | note |
|---|---:|---:|---|
| Marriott | 54 | 52 | every in-market MARSHA route; 1 transient Akamai interstitial (re-read normally), 1 route refused (León, Spain) |
| Hilton | 51 | 39 | 12 routes terminal (11 Akamai "Something went wrong" + edge reference, 1 error page) across paced windows 16:13Z–18:00Z (one read succeeded mid-block): 10 rows ACCESS_BLOCKED, the rest held as pre-opening or routing holds |
| Choice (incl. Radisson Americas) | 33 | 30 | Choice's own San Antonio directory; 3 retired codes |
| Best Western | 18 | 16 | 1 conditional ("Pets may be accepted"), 1 retired code |
| Drury | 9 | 8 | 1 retired route |
| Hyatt | 8 | 7 | Quarry Market route retired to Hyatt's home page |
| Sonesta / ABVI | 7 | 6 | 1 policies tab silent on pets |
| Independents | 18 | 9 | Gibbs, InTown ×6, Jackson House, O'Casey's; 5 dead / retired domains; The Espee is a venue |
| Motel 6 / Studio 6 | 5 | 0 | amenity chip only (3); legacy routes retired (2) |
| ESA 4, Omni 2, Red Roof 2, IHG 1, Wyndham 1 | 10 | 7 | |

**Marriott (Phase 17).** MARRIOTT CENSUS = 52, BROWSER ATTEMPTED = 54, READ SUCCESS = 52, CHALLENGE DENIED = 1
(transient, re-read), RESOLVED = 50 (28 PF + 22 NP), TERMINAL HOLDS = 2 (AC Hotel / Element at 111 Soledad, a
dual-brand building), **MARRIOTT ACTIONABLE REMAINING = 0**.

**Other browser brands (Phase 18).** Every cohort ended resolved or terminally bounded: 10 Hilton rows held
ACCESS_BLOCKED after the Akamai windows (never bypassed); Motel 6 / Studio 6 bounded on the measured chip-only
template; every retired route recorded with what the brand served instead.

**Durable evidence (Phase 19).** Every accepted capture keeps its requested and final URL, lane, provider, the
recorder's real-clock timestamp, the page's own name and address (identity signal and premises binding), the
document SHA-256, the operative quote and parsed facts and its source class. Persisted documents live under the
git-ignored `data/acquisition/` (as in every market); their hashes and quotes are committed.

## 5. Dual-brand and shared-campus safety (Phase 12)

Held inside the census (IDENTITY_MISMATCH_HOLD, each half proved by its own brand code and page):

| premises | pair |
|---|---|
| 111 Soledad St | AC Hotel / Element (Marriott) |
| 118 Soledad St | Hampton Inn & Suites / Home2 Suites (Hilton) |
| 1025 S Frio St | Baymont / Days Inn (Wyndham) |
| 6815 W US 90 | Baymont / Days Inn (Wyndham) |

Held outside the census as SAME_CAMPUS_DISTINCT_ENTITY: 7 rows (Comfort Inn & Suites / Sleep Inn & Suites,
WoodSpring Stone Oak ×2, Hotel St. Marys ×3). `identity_resolutions.json` was not written.

DUAL-BRAND / SHARED-CAMPUS BUILDINGS = 4 in-census (+ 3 outside); ROWS = 8 (+ 7); **PUBLISHED WITHOUT REVIEWED
RULING = 0**; FOUNDER-DECISION ROWS = 8.

## 6. Defects found and fixed in this market's own modules

1. **Refusal and acceptance misreads (all were caught by the shared reader and held; none published wrongly).**
   - "a cleaning fee ... to ensure that no pet allergens are left" (Hotel Emma) read as "no pets".
   - "Service dogs are welcome at the Crockett Hotel, even if not pet friendly" read as a refusal and, through
     "dogs are welcome" / "pet friendly", as acceptance. Service-animal phrases are now neutralised before
     acceptance is read, and "not pet friendly" never accepts.
   - New refusal shapes read: "does not allow pets" (Menger), "Pets including ESAs are not permitted", "no other
     pets are allowed" (Wyndham), and the typographic apostrophe in "can’t accommodate any pets" (Noble Inns).
2. **Reviews and directories are not first-party.** Places names directory pages (`poi.place`, `jany.io`,
   `edan.io`), a travel blog (`sahotelvisit.com`) and OYO booking pages as motels' websites; their text interleaves
   guest reviews ("It was also pet-friendly ... since we brought our dog along"). A crawled site now binds a policy
   only when its registrable domain carries a distinctive word of the property's own name.
3. **A label is not a policy.** "Pet friendly." closing an amenity paragraph (The Inn at Market Square) and
   Firecrawl's bare "pet-friendly" quote (stayAPT, whose real sentence "Both small pets and service animals are
   always welcome" is now the quote) never publish on their own.
4. **A combined weight is not per pet.** "Max weight: 75 lbs … 75lbs max total weight allowed between the 2 pets"
   (Homewood Airport, Hampton Airport) no longer publishes a 75-lb per-pet limit.
5. **Identity.** Unfolded abbreviations split one hotel into two (`2861 Cinema Rdg` / `Ridge`, `Pan Am Expressway`
   / `IH-35`, `Encino Cmns` / `Commons`); folds added to the census merge key. Evidence keyed by a renamed identity
   now follows the census's own alias list; a crawled row whose key went stale is re-keyed by its own address.
6. **Places reruns.** The lane re-asked identities it had answered, and a rerun dropped the six gap verifications
   that had admitted hotels to the census. It now reuses every answer and never drops a verification.
7. **Pre-opening from the brand's own card.** Hilton's own inventory card (open = false, 2027-02-05) now holds
   Homewood Suites at the Rim even though its page could not be opened.
8. **Austin leftovers.** Staging, partition, shadow, actionability and accounting carried Austin's market text,
   dates (2026-09-30 / 2026-10-01) and a Phoenix-era capture stamp, Austin's ESA / Motel 6 measurements, Austin's
   boundary audit (which refused "San Antonio") and the claim that Places was not run. All restated from San
   Antonio's own measurements.
9. **Heredocs** wrote backspace bytes twice (fixed; 0 remain in any San Antonio module).

## 7. Policy and fee safety (Phases 13, 14, 20)

`san_antonio_tx_publication_safety_audit_001` over the staged package, before seal — **all zero**:
PET-FRIENDLY WITH EXPLICIT REFUSAL 0, QUESTION-ONLY PET-FRIENDLY 0, SERVICE-ANIMAL-ONLY PET-FRIENDLY 0, PREOPENING /
CLOSED PUBLISHED 0, TIMESHARE / VACATION OWNERSHIP PUBLISHED 0, MILITARY-RESTRICTED PUBLISHED 0, MISLEADING SINGLE
FEES 0, VERIFIED-NO-PETS WITHOUT A REFUSAL 0. The shared reader (FAST rule C) re-ran every record at seal:
242/242 eligible (144 pet-friendly + 98 verified no-pets), 0 ineligible. 9 rows where this order's reader and the shared reader disagree are held, never overridden (Emma,
Crockett, Menger, Valencia, Gibbs, Everhome, Jackson House, Hotel Indigo, Super 8 I-10).

**Fees.** SINGLE-BASIS FEES PUBLISHED = 14 (all stated per stay in the quote itself); TIERED-FEE POLICIES = 39,
TIERED FEES WITHHELD = 39; MULTI-AMOUNT / UNSAFE SINGLE FEES WITHHELD = 17 (11 basis not stated, 5 stay-length
condition, 1 two bases); **MISLEADING SINGLE FEES PUBLISHED = 0**. A daily or nightly fee never becomes per stay
(it is published as `per_day` / `per_night` only when single and safe; every such fee here was multi-amount or
truncated and was withheld). Weight is never a count; refundable amounts are never pet fees; amenity, resort,
destination, parking and smoking fees are never pet fees.

## 8. Competitor challenge and large-market quality challenge (Phases 10, 27)

BringFido, identity and gap only: COMPETITOR RAW = 421, NORMALIZED = 373, MATCHED = 148 (145 distinct identities;
EXACT 119, ALIAS 26, DUPLICATE 3), TRUE MISSING = 6 by name — all six resolve to existing census rows by address or
phone in Places (aliases / rebrands: Days Inn & Suites Frost Bank Ctr, Jackson House, Fairfield Market Square,
Home2 Lackland, Hotel Gibbs, La Quinta IH-10 West). VERIFIED TRUE MISSING = 6 earlier in the run, each Places-verified
as an operational hotel at an admitted code and admitted to the census (ESA Colonnade, four Motel 6, Super 7 Inn NW
Medical Center), then read first-party; VERIFIED TRUE MISSING remaining = 0. EXCLUDED / STALE / OUTSIDE = 156
(152 vacation rentals, 4 outside). POLICY-UNRESOLVED MATCHES = 36. **MATERIAL IDENTITY GAP = NO.**

The census was challenged against the permit register, OSM, Visit San Antonio, the brands' own inventories, the
SAT airport / Medical Center / River Walk / North San Antonio corridors and the competitor's normalized identities;
every material gap found was closed (folds, rebrands, Places-verified gaps). No raw-count parity was chased.

## 9. Accounting, actionability and coverage (Phases 21–25, 28)

TOTAL DISCOVERED = 2,902 raw observations (1,440 graph nodes); NORMALIZED IDENTITIES = 1,440; QUALIFYING CENSUS =
414; PET-FRIENDLY = 144; VERIFIED NO-PETS = 98; RESOLVED = 242; UNRESOLVED = 172; RESOLUTION RATE = 58.45 %.

**Holds by class:** ROUTING 81, ACCESS_BLOCKED 28, SOURCE_SILENT 30, EVIDENCE 17 (incl. 4 PREOPENING), IDENTITY 16
(incl. 8 DUAL_BRAND), NEGATION 0, BROWSER_CAPTURE 0.

| class | total | actionable | router exhausted | new provider | new spend | founder | until opening |
|---|---:|---:|---:|---:|---:|---:|---:|
| ROUTING_HOLD | 81 | 0 | 81 | 0 | 0 | 0 | 0 |
| ACCESS_BLOCKED | 28 | 0 | 28 | 0 | 0 | 0 | 0 |
| SOURCE_SILENT | 30 | 0 | 30 | 0 | 0 | 0 | 0 |
| EVIDENCE_HOLD | 17 | 0 | 12 | 0 | 0 | 1 | 4 |
| IDENTITY_MISMATCH_HOLD | 16 | 0 | 8 | 0 | 0 | 8 | 0 |
| **total** | **172** | **0** | **159** | **0** | **0** | **9** | **4** |

MATERIAL COVERAGE RISK: the 10 Hilton rows blocked by Akamai are the largest single reachable-later cohort (a later
paced window is likely to read them); the 81 routing holds are small independents with no first-party web presence in
any authorized lane, including Places.

**Brand accounting (Phase 24)** — census / PF / NP / unresolved / Firecrawl attempted / browser attempted / browser
read / access blocked / actionable:

| family | census | PF | NP | unresolved | Firecrawl attempted | Firecrawl success | browser attempted | browser read | access blocked | actionable |
|---|---:|---:|---:|---:|---:|---:|---:|---:|---:|---:|
| BEST_WESTERN | 17 | 1 | 14 | 2 | 0 | 0 | 18 | 16 | 0 | 0 |
| CHOICE | 29 | 7 | 18 | 4 | 0 | 0 | 33 | 30 | 0 | 0 |
| DRURY | 8 | 8 | 0 | 0 | 0 | 0 | 9 | 8 | 0 | 0 |
| EXTENDED_STAY_AMERICA | 4 | 4 | 0 | 0 | 0 | 0 | 4 | 3 | 0 | 0 |
| EXTENDED_STAY_OPERATORS | 17 | 1 | 6 | 10 | 1 | 0 | 0 | 0 | 2 | 0 |
| HILTON | 51 | 33 | 3 | 15 | 0 | 0 | 51 | 39 | 10 | 0 |
| HYATT | 8 | 7 | 0 | 1 | 0 | 0 | 8 | 7 | 0 | 0 |
| IHG | 34 | 17 | 13 | 4 | 0 | 0 | 1 | 0 | 0 | 0 |
| INDEPENDENT | 83 | 0 | 1 | 82 | 1 | 0 | 18 | 9 | 2 | 0 |
| KIMPTON | 1 | 1 | 0 | 0 | 0 | 0 | 0 | 0 | 0 | 0 |
| LUXURY_INDEPENDENT | 22 | 2 | 1 | 19 | 2 | 0 | 0 | 0 | 1 | 0 |
| MARRIOTT | 52 | 28 | 22 | 2 | 0 | 0 | 54 | 52 | 0 | 0 |
| MOTEL6_STUDIO6 | 16 | 0 | 0 | 16 | 0 | 0 | 5 | 0 | 8 | 0 |
| OMNI | 1 | 1 | 0 | 0 | 0 | 0 | 2 | 2 | 0 | 0 |
| RADISSON | 3 | 2 | 0 | 1 | 0 | 0 | 0 | 0 | 1 | 0 |
| RED_ROOF | 5 | 2 | 0 | 3 | 0 | 0 | 2 | 2 | 3 | 0 |
| SONESTA | 7 | 5 | 0 | 2 | 0 | 0 | 7 | 6 | 0 | 0 |
| WOODSPRING | 5 | 2 | 0 | 3 | 0 | 0 | 0 | 0 | 0 | 0 |
| WYNDHAM | 51 | 23 | 20 | 8 | 1 | 0 | 1 | 0 | 1 | 0 |

Firecrawl columns count only the residual pass, which is keyed per identity. The IHG brand-page lane (35 attempts, 35 answered with their own address) is what resolved IHG's 30 rows; its pages bind by their own address, not by key.

**Corridor accounting (Phase 25)** — threshold: a corridor page publishes with ≥ 5 pet-friendly profiles; a thinner
corridor is never forced:

| corridor | class | census | PF | NP | unresolved | resolution | publishes |
|---|---|---:|---:|---:|---:|---:|---|
| downtown-river-walk | CORE | 70 | 35 | 10 | 25 | 64.3 % | YES |
| pearl-broadway | CORE | 5 | 1 | 0 | 4 | 20.0 % | NO |
| southtown | CORE | 23 | 6 | 5 | 12 | 47.8 % | YES |
| sat-airport | CORE | 36 | 15 | 12 | 9 | 75.0 % | YES |
| medical-center | CORE | 35 | 13 | 6 | 16 | 54.3 % | YES |
| north-central | CORE | 25 | 13 | 7 | 5 | 80.0 % | YES |
| stone-oak | CORE | 7 | 3 | 2 | 2 | 71.4 % | NO |
| northwest-la-cantera | CORE | 16 | 5 | 5 | 6 | 62.5 % | YES |
| six-flags-rim | CORE | 13 | 3 | 2 | 8 | 38.5 % | NO |
| seaworld-westover-hills | CORE | 29 | 11 | 9 | 9 | 69.0 % | YES |
| lackland-west | CORE | 28 | 6 | 3 | 19 | 32.1 % | YES |
| east-side | CORE | 29 | 8 | 8 | 13 | 55.2 % | YES |
| south-side | CORE | 40 | 5 | 7 | 28 | 30.0 % | YES |
| northeast | CORE | 18 | 5 | 4 | 9 | 50.0 % | YES |
| live-oak-universal-city | CORRIDOR | 16 | 4 | 7 | 5 | 68.8 % | NO |
| selma-schertz | CORRIDOR | 11 | 9 | 2 | 0 | 100.0 % | YES |
| leon-valley-helotes | CORRIDOR | 12 | 2 | 8 | 2 | 83.3 % | NO |
| converse | FRINGE | 1 | 0 | 1 | 0 | 100.0 % | NO |
| bulverde | FRINGE | 0 | 0 | 0 | 0 | — | NO |

PUBLISHING CORRIDORS = 12: Downtown / River Walk, Southtown, SAT Airport, Medical Center, North Central, Northwest / La Cantera, SeaWorld / Westover Hills, Lackland / West, East Side, South Side, Northeast, Selma / Schertz. Pearl / Broadway, Stone Oak, Six Flags / Rim, Live Oak / Universal City, Leon Valley / Helotes, Converse and Bulverde stay below the threshold and are not forced. (Alamo / Convention Center hotels are in Downtown / River Walk.)

**Coverage decision (Phase 28).** `san_antonio_tx_actionability_001` decides it mechanically. Every condition holds: ACTIONABLE UNRESOLVED = 0; MATERIAL IDENTITY GAP = NO; MATERIAL UNEXPLAINED POLICY GAP = NO (every unresolved row carries its exact reason); MARRIOTT ACTIONABLE = 0; every browser cohort exhausted or bounded; question-only acceptance 0; explicit-refusal pet-friendly 0; pre-opening, timeshare and military-restricted rows excluded; dual-brand rows safely held; publication set safe; package reproducible; FAST all pass. **COVERAGE READY = YES.**

One judgment is stated so the founder can overrule it. The inherited module returned FOUNDER DECISION whenever ANY row needed a founder ruling or awaited opening. This order defines founder intervention as required only for a ruling that *cannot safely remain held*, and lists "dual-brand / shared-campus rows safely held" and "preopening rows safely excluded" among the YES conditions. San Antonio's 9 founder rows (4 dual-brand buildings = 8 rows, and The Jackson House, whose refusal the shared reader cannot read) and 4 pre-opening rows are exactly those safe holds, and 0 rows need new spend or a new provider, so the module now applies the order's rule. The 10 Hilton rows held by Akamai are the cohort most likely to move in a later paced window.

## 10. Reproduction (Phase 32)

- Main run: this worktree, detached process, work dir `C:/t/sa1`, receipt `…54a176a9`.
- Reproduction: `git worktree add --detach C:/t/sarw 823e0ba4`, a separate detached process, work dir `C:/t/sa2`, receipt `…12fdfbf6` (receipt digests differ only by run metadata).
- Same package id `pkg-san-antonio-tx-b6018714bcc2bd44` and digest; FAST 15/15 in both; Rule J bundle `f9b4c610…`, 884 files / 868 HTML and staged-input digest `6398d5e9…` identical; Rule K BYTE_IDENTICAL in both.
- Actual file sets compared (after CRLF → LF normalisation; `core.autocrlf` rendering is not nondeterminism): 17 data files (staged launch package 8, sealed package 1, raw captures 7, proposed authority 1) — 0 differ; the two runs' build trees (888 + 888 + 58 + 58 = 1,892 files) — 0 only-in-one, 0 differ.
- **DATA DIFFERENCES = 0, SITE DIFFERENCES = 0, BYTE IDENTICAL = YES.** No San Antonio nondeterminism needed fixing. Record: `markets/reports/san_antonio_tx_independent_reproduction_001.json`. The reproduction worktree and both work dirs were removed afterwards.

## 11. Isolation, performance and cleanup (Phases 34–35)

CROSS-MARKET FILE CHANGES = 0; SHARED FACTORY IMPLEMENTATION CHANGES = 0; CURRENT LIVE CHANGES = 0; DEPLOYMENT STATE
CHANGES = 0; BROAD REGRESSION RUNS = 0. Every changed path is San Antonio-owned (`san_antonio_tx_*` modules and
reports, `markets/staging/san-antonio-tx/`, the proposed census and market document, the discovery config). The
inherited Austin-live lineage is untouched.

| | |
|---|---|
| START TIMESTAMP | 2026-10-02T14:06:51Z |
| ZERO_TO_SOURCE_READY | 4 h 12 min (FAST 15/15 at 18:18:10Z; independent reproduction complete 18:19:13Z) |
| ZERO_TO_COVERAGE_READY | 4 h 12 min (coverage decided on the same evidence, 18:19Z) |
| ACTIVE COMPUTE TIME | about 3 h 37 min (wall clock less the 26 min the terminal was closed, 15:38:51Z–16:05:04Z, and the ~9 min between the low-memory stop of the first seal and the user's go-ahead at 18:14:56Z) |
| PROVIDER / COOLDOWN WAIT | Hilton's Akamai block, paced windows 16:13Z–18:00Z (≈ 1 h 47 min), overlapped with other work throughout; Choice's sensor page cleared on its own in < 1 min each time |
| EXISTING PROVIDER CREDITS USED | Firecrawl 110 plan credits (613 → 503); Google Places 201 requests inside the renewed free monthly allowance |
| NEW PAID SPEND / PROVIDER COST | none / USD 0 |
| FOUNDER INTERVENTION | none for the build. The first seal was stopped by Claude Code's low-memory reaper (an operational stop, not a failure of the package); the user asked for the re-run |

**Cleanup.** The browser tab group was closed; the seal, FAST and reproduction processes exited; their work dirs and the reproduction worktree were removed; no watcher, timer, server or child worker of this order is running. Unrelated pre-existing processes (another session's `C:\t\sink.py`, Codex and Netlify helpers) were left alone.

**Commits on this branch:**

1. `823e0ba4`: staged inputs — every San Antonio module and report, the raw captures, the census, the staged policy package, authority, shard documents and partition.
2. `6725b80d`: the shadow package, its receipt and the shadow report.
3. This report, the reproduction record, the refreshed actionability and the seven machine-readable accountings (source, provider, brand, corridor, boundary, competitor reconciliation, actionability).


## FINAL ANSWERS

1. START TIMESTAMP = 2026-10-02T14:06:51Z
2. ZERO_TO_SOURCE_READY = 4 h 12 min (2026-10-02T18:19:13Z)
3. ZERO_TO_COVERAGE_READY = 4 h 12 min (2026-10-02T18:19Z)
4. CURRENT LIVE DEPLOYMENT = 6abf3e749cc359701298718d (Austin; source f0ddbcde, bundle 75e56941, sitemap d6461dbc, host verified)
5. CURRENT LIVE MARKETS = 38 (3,386 profiles / 3,737 release-index routes / 3,808 served routes)
6. NEXT-MARKET AUTOMATIC BASE DERIVES = YES (DERIVED BASE = 3afa9b17)
7. TOTAL DISCOVERED = 2,902 raw observations
8. NORMALIZED IDENTITIES = 1,440 graph nodes
9. QUALIFYING CENSUS = 414
10. PET-FRIENDLY = 144
11. VERIFIED NO-PETS = 98
12. RESOLVED = 242
13. UNRESOLVED = 172
14. RESOLUTION RATE = 58.45 %
15. ACTIONABLE UNRESOLVED = 0
16. HOLDS BY CLASS = ROUTING 81 · ACCESS_BLOCKED 28 (after router exhaustion) · SOURCE_SILENT 30 · EVIDENCE 17 (incl. PREOPENING 4) · IDENTITY 16 (incl. DUAL_BRAND 8) · NEGATION 0 · BROWSER_CAPTURE 0
17. EXCLUSIONS BY CLASS = OUTSIDE 540 · NON_HOTEL 50 (incl. 1 converted) · VACATION_RENTAL 43 · TIMESHARE 8 · MILITARY_RESTRICTED 9 · RESORT_RESIDENCE 0 · CLOSED 0 (graph residue: NAME_ONLY 230, IDENTITY_REVIEW 148, SAME_CAMPUS_DISTINCT 7)
18. PREOPENING IDENTITIES = 5 (4 held in the census + Hotel St. Marys held outside it)
19. PREOPENING PUBLISHED = 0
20. VACATION-OWNERSHIP / TIMESHARE IDENTITIES = 8
21. VACATION-OWNERSHIP / TIMESHARE PUBLISHED = 0
22. MILITARY-RESTRICTED IDENTITIES = 9
23. MILITARY-RESTRICTED ADMITTED = 0
24. PUBLISHING CORRIDORS = 12 (Downtown / River Walk, Southtown, SAT Airport, Medical Center, North Central, Northwest / La Cantera, SeaWorld / Westover Hills, Lackland / West, East Side, South Side, Northeast, Selma / Schertz)
25. COMPETITOR RAW / NORMALIZED / MATCHED / TRUE MISSING = 421 / 373 / 148 / 6 (all six resolve to census rows by address or phone; 6 earlier Places-verified gaps were admitted)
26. MATERIAL IDENTITY GAP = NO
27. MATERIAL POLICY GAP = NO
28. FIRECRAWL ATTEMPTED / SUCCESS = 50 / 36 property pages (35 IHG brand pages + 1 publication-grade); 16 route-discovery pages and the BringFido challenge besides
29. MARRIOTT CENSUS = 52
30. MARRIOTT BROWSER ATTEMPTED = 54
31. MARRIOTT READ SUCCESS = 52
32. MARRIOTT CHALLENGE DENIED = 1 (transient; re-read normally)
33. MARRIOTT ACTIONABLE REMAINING = 0
34. OTHER BROWSER ATTEMPTED / SUCCESS = 159 / 121
35. DUAL-BRAND / SHARED-CAMPUS HOLDS = 4 buildings / 8 rows in the census (+ 7 same-campus rows outside it); published without a reviewed ruling 0
36. SINGLE-BASIS FEES PUBLISHED = 14
37. TIERED FEES WITHHELD = 39
38. UNSAFE / MULTI-AMOUNT FEES WITHHELD = 17
39. MISLEADING SINGLE FEES = 0
40. PET-FRIENDLY WITH EXPLICIT REFUSAL = 0
41. QUESTION-ONLY PET-FRIENDLY = 0
42. ACCESS_BLOCKED AFTER ROUTER EXHAUSTION = 28 (10 Hilton Akamai, 8 Motel 6 / Studio 6, 3 Red Roof, 7 other independents / extended-stay / Radisson / Wyndham)
43. EXISTING PROVIDER CREDITS USED = 110 Firecrawl plan credits (613 → 503); 201 Google Places requests inside the free monthly allowance
44. NEW PAID SPEND = 0
45. PROVIDER COST = USD 0
46. RULE J NONEMPTY = PASS (884 files, 868 HTML, output present; bundle f9b4c610, not e3b0c442)
47. RULE K NONVACUOUS = PASS (BYTE_IDENTICAL, 4 cold builds)
48. FAST RECEIPT CURRENTLY ELIGIBLE = YES
49. SHADOW PACKAGE CREATED = YES (SHADOW_UNTIL_REGISTERED)
50. PACKAGE REPRODUCIBLE = YES (in-process two-seal, and independent reproduction: BYTE IDENTICAL, data 0 / site 0 differences)
51. PACKAGE DIGEST = sha256:b6018714bcc2bd44073a6832ab47033904526b4e88bb7cf9ca315f0d6268ed36 (pkg-san-antonio-tx-b6018714bcc2bd44)
52. FAST = 15/15 PASS, 0 UNKNOWN, 0 FAILED
53. TECHNICAL SOURCE READY = YES
54. COVERAGE READY = YES
55. CROSS-MARKET FILE CHANGES = 0
56. FACTORY CODE CHANGED = NO
57. BROAD REGRESSION RUNS = 0
58. FINAL PRODUCTION CANDIDATE CREATED = NO
59. FOUNDER AUTHORIZATION CREATED = NO
60. SAN ANTONIO DEPLOYED = NO
61. origin == HEAD = YES (after the push recorded below)
62. tree clean = YES

SAN ANTONIO SOURCE READY = YES
SAN ANTONIO COVERAGE READY = YES
ACTIONABLE UNRESOLVED = 0
PET-FRIENDLY RECORDS WITH EXPLICIT REFUSAL = 0
QUESTION-ONLY PET-FRIENDLY RECORDS = 0
PREOPENING PROFILES PUBLISHED = 0
VACATION-OWNERSHIP / TIMESHARE PROFILES PUBLISHED = 0
MILITARY-RESTRICTED PROFILES PUBLISHED = 0
MISLEADING SINGLE FEES = 0
RULE J NONEMPTY = PASS
RULE K NONVACUOUS = PASS
FAST = 15/15 PASS
FACTORY CODE CHANGED = NO
BROAD REGRESSION RUNS = 0
SAN ANTONIO FINAL CANDIDATE = NO
SAN ANTONIO DEPLOYED = NO
WAITING FOR RELEASE QUEUE = YES
