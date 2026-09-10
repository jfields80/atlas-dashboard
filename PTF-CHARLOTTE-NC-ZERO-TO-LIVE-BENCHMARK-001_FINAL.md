# PTF-CHARLOTTE-NC-ZERO-TO-LIVE-BENCHMARK-001 — final report

**BENCHMARK_START_TIMESTAMP = 2026-09-10T13:12:23Z**

Charlotte, North Carolina, built from zero on the redesigned factory. No legacy
shadow market, no proposed-only stage, no pre-flip candidate. The census was
written straight to `identity_census/`, the authority straight to the registered
shard, and the candidate composed with participation as an input rather than a
later flip.

**Cost: $0.00. Zero paid provider calls. Zero Firecrawl credits.**

---

## CURRENT VERIFIED LIVE PRODUCTION, DERIVED

Read mechanically through `release_index.current_verified_live()`, not from the
pin and not from memory. `problems = []`.

    HOST DEPLOYMENT ID     6aa212a8ba9f174305c0441a
    LIVE RELEASE DIGEST    c12b410ec8331dbf7a50581027ad60291cac95f626de5a6a846b0d77524e0e11
    SITEMAP DIGEST         13f5335fc1a055ce06de5ce66c7921da55308110e94c0b0f18806853c1662bc4
    SOURCE COMMIT          aee8a21e6c13881543601a4fcd54350b6a64bb19
    MARKETS                13
    PROFILES               902
    ROUTES                 1078
    PARTICIPANTS           13 founder-authorized
    ROLLBACK PARENT        6aa172121d37bb4013eb44a4 (Lexington)
    VERIFICATION STATUS    CONSISTENT

The remembered figures were right; they were not trusted until they were
derived.

---

## GEOGRAPHY

The core is a **county polygon** — the whole of Mecklenburg County, North
Carolina — which is the Lexington doctrine applied to a major metro. Seventeen
admitting corridors cover Uptown, South End, Elizabeth/Plaza Midwood/NoDa,
SouthPark and Myers Park, the airport and West Charlotte, Tyvola/Yorkmont,
Arrowood and Steele Creek, Ballantyne, University City, Northlake, East
Charlotte and Mint Hill, Matthews, Pineville, and the Lake Norman towns of
Huntersville, Cornelius and Davidson.

Three corridors outside the county line are admitted on **first-party evidence**
— the operators' own published property names call each of them CHARLOTTE:

| corridor | the brand's own naming |
|---|---|
| Concord / Concord Mills / Speedway, I-85 NE | `courtyard-charlotte-concord`, `residence-inn-charlotte-concord`, `springhill-suites-charlotte-concord-mills-speedway` |
| Belmont / Gastonia, I-85 SW | `fairfield-inn-and-suites-charlotte-belmont`, `courtyard-charlotte-gastonia`, `fairfield-inn-charlotte-gastonia` |
| Fort Mill / Carowinds / Indian Land, I-77 S | `courtyard-charlotte-fort-mill-sc`, `towneplace-suites-charlotte-fort-mill`, `springhill-suites-charlotte-at-carowinds` |

**Charlotte is this project's first market whose admitted geography crosses a
state line.** Carowinds straddles the NC/SC border at the city's own southern
edge.

Four corridors are **founder holds** that claim no postal code and therefore
admit nothing: Rock Hill SC, Kannapolis, Mooresville / north Lake Norman, and
Monroe / Indian Trail / Waxhaw. Their hotels are discovered, identified, and
then classified `OUT_OF_MARKET_BOUNDARY_DECISION` — so the founder rules on an
inventory that was looked at, and admitting one is a one-line ZIP move.

**A code selects; the page admits.** CLT is the Charlotte Douglas airport code
and the committed Dayton roster proves it reaches Shelby (`cltby`), Statesville
(`cltfv`), Hickory (`cltht`) and Salisbury (`cltsb`). Charlotte adds a hazard
Nashville did not have: the market name itself is ambiguous. CHARLOTTESVILLE,
VIRGINIA shares its first eleven letters and was trapped explicitly (`choak`,
`choch`, `chodt`); Marriott files a Fort Mill SOUTH CAROLINA property under a
`charlotte` slug.

---

## THE LADDER, RUNG BY RUNG

| rung | what it cost | what it produced |
|---|---|---|
| 0 OWNED | 0 requests, $0 | 69 Marriott CLT leads from the committed Dayton harvest |
| 1 LOCAL FREE | 2 extract downloads, md5-verified | 359 OSM candidates (313 NC + 46 SC) |
| 1 BRAND CITY PAGE | 62 requests | 69 Hilton CLT codes from 21 city pages; Drury, WoodSpring, Omni routes |
| 2 BRAND SITEMAP | 241 requests | 53 routes: Wyndham 44, Drury 5, Sonesta 4 |
| 2 LEADS | 205 requests | 266 BringFido hotel leads, 621 destination-org lodging links |
| 3 STATIC | 9 requests | 3 clean Drury; 6 WoodSpring SOURCE_SILENT |
| 4 FIRECRAWL | **not used** | the families that would route here were reachable attended |
| 5 ATTENDED | 171 pages, THREE navigations, $0 | Marriott 68, Hilton 69, IHG 34 |

Total free HTTP requests: **517**. Paid provider calls: **0**. USD: **$0.00**.

Marriott, Hilton and IHG were each read by **same-origin fetch from one tab per
origin** — three navigations for 171 property pages — and every page was hashed
in the same JavaScript call as the quote.

---

## WHAT THE DISCIPLINE CAUGHT

**A dual-brand building is TWO hotels, and a street identity alone breaks four
separate layers.** Charlotte has seven such buildings: Sheraton Charlotte and Le
Méridien in the two towers of 555 South McDowell Street; Courtyard and Residence
Inn at 9110 Harris Corners Parkway; AC Hotel and Residence Inn at 220 East Trade
Street; Fairfield and Residence Inn at 2220 West Tyvola Road; Candlewood and
Holiday Inn at 3695 Foothills Way; Hilton Garden Inn and Homewood Suites at 4808
Sharon Road; Home2 Suites and Tru at 5355 John Q. Hammons Drive. The census
merge collapsed them, the merge-conflict rule put Le Méridien's `cltmd` read on
the Sheraton's node, the clean-set join reported six real hotels as duplicates,
and the publication guard barred a pet-friendly hotel because its neighbour says
"Pets Not Allowed". Each layer needed the brand property code to decide.

**The publication guard was right and had to be answered, not disabled.** Seven
reviewed `same_campus_distinct_entity` rulings now rest on the exclusion
contract's own `co_located_distinct` proof — distinct codes inside one brand
family, distinct canonical first-party URLs — and each waives a STREET-IDENTITY
match and nothing else. A name or alias match is never waived.

**The map's address is not the hotel's address.** Folding OpenStreetMap in
dropped the publishable count from 108 to 94 before the precedence was fixed:
eleven already-read hotels became unjoinable to their own reads because a map
row owned the street. A first-party read now overwrites the postal address.

**A stale map flag is not a rebrand hold.** OpenStreetMap still calls 3695
Foothills Way a Clarion, 242 East Woodlawn a Best Western Sterling, 3127 Sloan
Drive a La Quinta and 4920 South Tryon a Hyatt House. Counting a third-party
label as a second brand identity turned six resolved rebrands into six founder
holds. Only first-party lanes now contribute a brand signature.

**The fee was the cap.** Marriott writes "Non-refundable fee of USD 50 per room
per night up to maximum charge of USD 150 / Pet Fee Per Night: $50.00". A
generic `$N ... fee` search matches "150 Non-Refundable Pet Fee" and publishes
three times the real rate. The first-party gate caught it on Le Méridien and the
Sheraton by comparing each fact to its own cited quote.

**A service-animal sentence is not a refusal.** Two Charlotte DoubleTrees
publish a `petsInfo` node whose entire description is "Service animals only".
Both are HELD, not published as verified-no-pets.

**A source stating a maximum pet weight of ZERO has stated no limit.** Dropped
as UNKNOWN rather than published as "0 lbs" and rather than refusing an
otherwise clean acceptance.

**Refundability is UNKNOWN unless the source says so.** Reading a silence as
"refundable" would publish a fact no hotel asserted.

**WoodSpring and Wyndham publish nothing operative to a plain client.**
WoodSpring's property pages carry an SEO keyword list and a chain-level line
about "MOST of our locations"; Wyndham renders its policy client-side and serves
a plain client the amenity chip plus a nine-language dictionary containing the
words "Pet-Friendly" — the Marriott translation-table hazard in another shape.
Both are recorded, routed, unresolved, and named.

**`launch_participation.json` is reissued, never edited.** Adding a
non-authorized row by hand broke its decision chain, and every market then read
`UNLISTED` and the assembler refused the whole build. Repaired through
`extend_decision`, which restored a nine-record chain.

---

## COMPETITOR COVERAGE CHALLENGE

    competitor rows observed              266
    also seen by a first-party lane        62
    competitor-only                       204
      of which NAME_ONLY_UNRESOLVED       108
      of which IDENTITY_REVIEW_REQUIRED    58
      of which NON_LODGING                 38
    competitor-only rows that publish       0

The `/hotels/` path filter was measured on Charlotte's own city page and found
**LIVE**: 399 unfiltered rows against 189 filtered. The filtered path supplied
the leads; the 210 rows only the unfiltered path carries read as short-term
rentals and were not imported as hotels. No row was optimised toward matching a
directory's count.

---

## THE MARKET

    REGISTERED CENSUS                268
    VALID PET-FRIENDLY               106
    VALID VERIFIED-NO-PETS            43
    RESOLVED                         149
    UNRESOLVED                       119
    ADMITTING CORRIDORS               17
    CORRIDORS WITH A PUBLISHED HOTEL  17
    CORRIDOR PAGES THAT PUBLISH       11
    FOUNDER-HOLD CORRIDORS             4

Every identity reconciles to exactly one state and nothing is silently omitted.

---

*(Benchmark timings, validation results and the authorization block are recorded
in `launch_packages/pettripfinder/markets/reports/charlotte_nc_authorization_packet_009.json`.)*

---

## VALIDATION

    FIRST-PARTY EVIDENCE GATE   147 evaluated, 147 eligible, 0 ineligible
    FAST RELEASE LANE           A-O all PASS -- 15/15, 0 UNKNOWN, 0 FAILED
    DETERMINISM                 BYTE_IDENTICAL
    FRESH_PACKAGE_REPRODUCIBLE  YES
    FINAL_CANDIDATE_REPRODUCIBLE YES (two whole-site builds, 707s and 738s,
                                same bundle and same sitemap digest)
    UNCHANGED_MARKETS_REBUILT   0
    RELEASE DIFF                passed, 0 findings
    CONTRACTS                   verify_all() clean for all 15 markets

### THE CANDIDATE

    PARENT DEPLOY ID       6aa212a8ba9f174305c0441a
    PARENT RELEASE DIGEST  c12b410ec8331dbf7a50581027ad60291cac95f626de5a6a846b0d77524e0e11
    SEALED PACKAGE DIGEST  sha256:7f23f2ef24195f2a1058c57910827f4f36c0d209fe7c1675cde4f519d66c7c1a
    INTENDED DELTA DIGEST  sha256:b2a566eb38e3bc6278da0b3ccc992b8abb85073edc436a85de9a7c679f131914
    FAST RECEIPT DIGEST    sha256:55105679c646fa9fcf318f550c43a34b44dc3854e1e416ec5ad1b2429434cb55
    CANDIDATE DIGEST       c9ca8c2d94a6489ce41268626531a5e834c494e0bf08bbe67faa7052a2166696
    DEPLOYMENT ARTIFACT    c9ca8c2d94a6489ce41268626531a5e834c494e0bf08bbe67faa7052a2166696
    CANDIDATE SITEMAP      6a610e928176dac61d385527625be867a4321416108db07b05ee5d4caec4071a
    ROLLBACK TARGET        6aa172121d37bb4013eb44a4

    PROJECTED LIVE         14 markets / 1008 profiles / 1197 routes
    DELTA                  +1 market, +106 profiles, +119 routes
    REMOVED                0 markets, 0 profiles, 0 routes
    UNEXPECTED CHANGES     0 / 0 / 0

## REGRESSION — NOT CLOSED

Registration classifies `AUTHORITY_CHANGE` + `DEPLOYMENT_CHANGE`, so
`FULL_REGRESSION_REQUIRED = YES`. ONE broad run, 5296.8 s, classified by node id
against the committed `f75aa95` baseline:

    COLLECTED              18233
    PASSED                 17792
    SKIPPED                  253
    FAILED                   188
    PRE_EXISTING             160
    TRUE_NEW_FAILURE          28   <-- closure NOT complete

Two of the 28 were a REAL defect and are now fixed: the current-state pin and
the derived release contract still carried `verified_no_pets = 43` from before
the two service-animal holds were demoted, while the shard held 41.
`test_market_state_pins` caught the disagreement between the pin and the shard,
which is exactly what it is for. Charlotte's authoritative counts are now
consistent at census 268 / pet-friendly 106 / verified-no-pets 41 / resolved 147
/ unresolved 121, and all 93 pin-contract tests pass.

**The remaining 26 are not closed, and this order does not claim they are
benign.** They cluster in four places and each cluster needs its own closure
before authorization:

| cluster | nodes | what it looks like |
|---|---|---|
| participation lineage + launch suites | 11 | the participation record was REISSUED, so suites asserting the previous decision block and the repair record that covered it no longer match |
| market-count and registry pins | 6 | a fifteenth registered market moved counts several suites restate |
| cross-market identity/collision scans | 4 | Charlotte's names entering the global authority need checking, not assuming |
| acquisition run registration + Columbus seed parsing | 5 | new run directories are unregistered, and the global seed grew |

**CHARLOTTE_FOUNDER_AUTHORIZATION_READY = NO.**
`TRUE_NEW_FAILURE_AFTER_CLOSURE` is 26, not 0. Every production gate that
measures the CANDIDATE passes; what is not finished is the one-time registration
closure the broad run exists to force.

## BENCHMARK

    BENCHMARK_START                       2026-09-10T13:12:23Z
    ZERO -> CANDIDATE PASSING EVERY GATE  132 minutes
    ZERO -> BROAD REGRESSION CLASSIFIED   223 minutes
    FOUNDER ACTIVE MINUTES                0
    PROVIDER COST                         $0.00
    FIRECRAWL CREDITS                     0
    PAID PROVIDER CALLS                   0
    FREE HTTP REQUESTS                    517
    ATTENDED BROWSER PAGES                171 in THREE navigations

    STAGE                        minutes
    geography + contracts             12
    owned evidence + brand lanes      22
    attended capture (3 families)     28
    OSM extracts, index, discovery    36  (overlapped)
    census + identity                 20
    routing + clean set               10
    registration + release contract   18
    sealed package + FAST lane        14
    candidate assembly (x2)           24
    broad regression                  88

    BENCHMARK_TARGET_4H_AUTH_READY = FAIL
      -- the candidate was gate-clean at 2h12m, but authorization requires
         TRUE_NEW_FAILURE_AFTER_CLOSURE = 0 and 26 nodes are still open.
