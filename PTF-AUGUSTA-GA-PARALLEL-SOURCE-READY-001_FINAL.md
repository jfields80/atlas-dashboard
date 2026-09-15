# PTF-AUGUSTA-GA-PARALLEL-SOURCE-READY-001 -- FINAL

Worktree: `C:\Atlas-Augusta-GA-Hardened-V1`
Branch: `worker/ptf-augusta-ga-market-001`
Market ID: `augusta-ga`
Display market: Augusta – Richmond County / Greater Augusta, Georgia
Source commit (base): `c236f52da26ac7b1fe531b2497cef5dfba67d9d2` (main, unchanged)

## Scope actually delivered this pass

This pass produced a **real, mechanically-validated identity/census/geography
shadow package** for Augusta, GA, built from live web research (chain-brand
locator pages, the official Visit Augusta CVB lodging directory, Columbia
County tourism resources, and cross-checked competitor/discovery leads).

It did **not** capture per-property pet-policy evidence (no page-by-page
policy reading/parsing this pass). Every census row's `policy_state` is
`POLICY_NOT_VERIFIED` and every partition row carries an honest blocker
(`AWAITING_POLICY_OBSERVATION`, `AWAITING_OFFICIAL_URL`, or
`AWAITING_IDENTITY_RESOLUTION`) rather than a fabricated pet-friendly or
no-pets determination. This is the same pattern
`build_pittsburgh_market_001.py` documents for its own revalidation pass, and
is the mission-compliant outcome given the scope actually completed.

No generic sealer / FAST-lane / registration-release modules exist at this
branch's base commit (confirmed by reading both this worktree and the
Savannah-GA market branch, `origin/worker/ptf-savannah-ga-market-001`, whose
scripts import several modules -- `fast_release_lane`,
`registration_release_lane`, `sealed_market_package`, etc. -- that are simply
absent here). Rather than port that machinery into a shared location (which
the mission forbids), this pass wrote a **right-sized, self-contained
equivalent**: one build script, one 15-check validation script, and one
shadow-package assembler, all Augusta-owned, using the real contract
validators (`contracts.census`, `contracts.partition`, `identity_routing`,
`hotel_exclusions`, `markets.contract`, `market_authority`) that already
exist in this codebase.

## Geography

**CORE / evaluated, with real inventory:**
Downtown Augusta (8 hotels, incl. 2 independents), Washington Road / Augusta
National corridor (30 hotels), West Augusta (17 hotels), Gordon Highway /
Fort Eisenhower gate area (15 hotels, merged into one corridor -- see below),
South Augusta (3 hotels, including Hephzibah), Grovetown GA (9 hotels).

**Medical District:** evaluated, NOT given its own corridor page this pass --
only one verified property (The Partridge Inn) sits in that specific
micro-area; folded into Downtown rather than publish a one-hotel page (no
thin SEO corridors).

**Airport (AGS):** evaluated, NOT given its own corridor -- confirmed no
on-site hotels; the nearest inventory (4-5 mi north) is already the
Washington Road / West Augusta cluster.

**Martinez, GA / Evans, GA:** evaluated, NOT given their own corridors --
zero chain hotels were found with an actual Martinez or Evans postal city in
a verified address; every property physically in that geography (Washington
Rd / Jimmie Dyess Pkwy corridor) carries an Augusta, GA mailing address.
Their geography is already served by the Washington Road and West Augusta
corridors.

**Gordon Highway vs. Fort Eisenhower gate area:** modeled as ONE corridor.
Fort Gordon was officially renamed Fort Eisenhower on 2023-10-27, but both
name forms still coexist in live hotel marketing today; the properties
themselves (Gordon Highway proper + the Noland Connector cluster near Gate
1) form one continuous strip with no clean address-based split, so splitting
them would have been an arbitrary corridor boundary, not a real one.

**STRONG evaluation (Columbia/Richmond County towns):**
- Harlem, GA -- 1 hotel (Red Oak Manor B&B), own-brand, 22 mi out -- **OUTSIDE**.
- Appling, GA -- 0 hotels (confirmed via the official Visit Columbia County
  GA page) -- **OUTSIDE** (trivially, nothing to include).
- Hephzibah, GA -- 1 hotel (Rodeway Inn & Suites Hephzibah Augusta), whose
  own brand name blends "Hephzibah" and "Augusta" -- **folded into the South
  Augusta corridor** (same Richmond County consolidated government area).
- Belair, GA -- confirmed to be a neighborhood/CDP inside Augusta-Richmond
  County, not an independent town -- **not treated as a separate geography**.

**CAREFUL FRINGE evaluation:** Thomson GA (6 hotels), Wrens GA (1), Waynesboro
GA (5), Lincolnton GA (3) -- all confirmed to have real, multi-brand or
independent hotel bases branded under their own town names, with marketing
copy referencing Augusta only as a nearby attraction, never as identity.
All four -- **OUTSIDE** this market; candidates for their own future
standalone market designs, not absorbed here.

## Cross-border (South Carolina) safety

**SOUTH CAROLINA PROFILES IN AUGUSTA-GA CENSUS = 0** (mechanically proven --
FAST check 8, and `census.validate(doc, market_states=("GA",))`).

26 South Carolina properties were discovered for boundary/accounting
purposes only (North Augusta 8, Aiken 15, Edgefield 3) and are recorded in
`raw_captures/sc_boundary_discovery.json` at name/brand/city depth -- not
included, not silently dropped.

## Masters-event and Fort Eisenhower identity safety

Confirmed the bulk of "Masters week housing" is private home/estate rental
inventory (Masters Housing Bureau, Rent Like A Champion, Champion Home
Rentals, Tournament Housing, Sports Traveler), not hotels -- categorically
excluded, not enumerated as discrete properties.

On-post lodging at Fort Gordon/Fort Eisenhower (IHG Army Hotels -- Holiday
Inn Express Griffith Hall, Candlewood Suites, Ring Hall; 235 Chamberlain Ave)
is restricted to DoD ID holders / official orders and is **excluded**
(MILITARY/RESTRICTED, 3 facilities at one installation address). Public
hotels marketing toward the gate (Gordon Highway / Noland Connector /
Jimmie Dyess Pkwy clusters) are included normally.

## Identity safety -- collisions held, not guessed

Three collision pairs (6 rows) were found and are held in the partition as
`AWAITING_IDENTITY_RESOLUTION` rather than merged or silently kept distinct:

1. **Holiday Inn Express & Suites West Augusta** (4087 Jimmie Dyess Pkwy) and
   **Holiday Inn West Augusta** (441 Park West) carry the *same* IHG property
   code (`agsjd`) at two different addresses -- almost certainly one property
   double-listed, not confirmed.
2. **Rodeway Inn Augusta (Washington Rd, Unit B)** and **Masters Inn Augusta**
   share the street number 3027 Washington Road.
3. **Sonesta Essential Augusta (3039B)** and **Heritage Inn Augusta (3039)**
   share an address one letter-suffix apart on Washington Road.

Two co-location patterns were confirmed as genuinely **distinct** identities
(the dual-brand-building rule), not collisions: Motel 6 / Studio 6 at 3421
Wrightsboro Rd, and TownePlace Suites / Fairfield Inn & Suites at 893 Husk
Box Way, Grovetown.

## Accounting (mechanically derived -- see
`launch_packages/pettripfinder/markets/reports/augusta_ga_source_ready_accounting_003.json`)

| | |
|---|---|
| TOTAL DISCOVERED | 141 |
| Raw GA hotel-lead mentions (chain + independent lanes, pre-dedup) | 94 |
| Internal duplicates merged | 12 |
| **PROPOSED CENSUS** | **82** |
| RESOLVED (single confirmed identity, awaiting only URL/policy work) | 76 |
| UNRESOLVED (identity-collision holds) | 6 |
| VALID PET-FRIENDLY | 0 |
| VALID VERIFIED-NO-PETS | 0 |
| IDENTITY HOLDS | 6 |
| ROUTING HOLDS | 0 |
| ACCESS-BLOCKED (properties) | 0 |
| ACCESS-BLOCKED (lane) | OSM/Overpass -- 406 from this sandbox network on every query variant tried; brand + CVB lanes covered the same geography instead |
| EVIDENCE HOLDS | 0 |
| GEOGRAPHY HOLDS | 0 |
| MILITARY/RESTRICTED | 3 |
| PAID HOLDS | 0 |
| FOUNDER HOLDS | 0 |
| CLOSED/RETIRED | 0 |
| OUTSIDE (SC 26 + fringe-GA-towns 16) | 42 |
| NON-HOTEL | 1 (Timberline Glamping, Appling -- campground product) |
| VACATION RENTAL (discrete properties) | 0 (categorical exclusion, not enumerable) |
| TEMPORARY EVENT LODGING (discrete properties) | 0 (categorical exclusion, not enumerable) |
| FUTURE_OPENING (extra bucket, not in the original template) | 1 (LivSmart Studios by Hilton Augusta -- reported opening March 2027; no contract lifecycle state exists for an unopened property, so it is excluded and flagged for future re-evaluation rather than forced into any existing state) |

Reconciliation: 82 + 42 + 3 + 1 + 1 + 12 = 141 = TOTAL DISCOVERED. ✓ (checked
mechanically by the accounting script, not by hand.)

Partition final-state breakdown: `AWAITING_POLICY_OBSERVATION` 71,
`AWAITING_OFFICIAL_URL` 5, `AWAITING_IDENTITY_RESOLUTION` 6.

Corridor coverage (all real, none padded): Downtown 8, Washington Road 30,
West Augusta 17, Gordon Highway/Fort Eisenhower 15, South Augusta 3,
Grovetown 9 = 82.

## Owned-data search (Phase 7)

`grep`/`find` across this worktree for `savannah`, `charleston`, `myrtle` and
similar market names returned nothing -- this worktree forked from the
shared factory baseline (`main` @ `c236f52d`) and carries no other market's
data (each market's research lives on its own unmerged branch). No reusable
modern Augusta evidence, routes, or rebuild aliases existed to reuse.
OWNED IDENTITIES = 0, OWNED ROUTES = 0, OWNED VALID POLICY EVIDENCE = 0,
OWNED REBRANDS/ALIASES = 0, OWNED COLLISIONS = 0.

## Shadow package

- Package: `launch_packages/pettripfinder/markets/staging/augusta-ga/shadow_packages/augusta-ga/pkg-augusta-ga-a9c7353deda809e4.json`
- Receipt: `launch_packages/pettripfinder/markets/staging/augusta-ga/shadow_receipts/augusta-ga/pkg-augusta-ga-a9c7353deda809e4-5d7c9e611a6bb7ed.json`
- Schema: `ptf-augusta-shadow-package/1.0` / `ptf-augusta-shadow-receipt/1.0`
  (own schema names -- this is an honest, right-sized equivalent, not a claim
  to be the generic factory sealer, which does not exist at this branch's
  base).
- Lifecycle: `SHADOW_UNTIL_REGISTERED`. Not production-selectable. No
  `CURRENT VERIFIED LIVE` reader/registry file exists at this branch's base
  commit, so the package records that fact rather than a live-parent digest
  it cannot honestly compute.

## Reproducibility

`augusta_ga_market_build_001.py` was run twice (independently, from the same
static `CANDIDATES` source data); the census, partition, market config, and
both authority shard files were byte-identical (sha256-verified) across both
runs -- see FAST check 12. PACKAGE REPRODUCIBLE = YES. Non-deterministic
files = none.

## FAST-equivalent checks

No generic 15-check FAST/sealed-release module exists at this branch's base
(confirmed against this worktree and Savannah's branch). 15 checks were
built directly from the real contract validators and run via
`scripts/pettripfinder/augusta_ga_fast_checks_001.py`:

```
 1. [PASS] census.validate (GA-only)
 2. [PASS] partition.validate
 3. [PASS] partition.reconcile == census identity keys
 4. [PASS] identity_key.key_collisions empty
 5. [PASS] identity_routing.validate_authority (shard)
 6. [PASS] hotel_exclusions.validate + hash re-derivation (shard)
 7. [PASS] markets.contract.parse_market (staged config)
 8. [PASS] zero non-GA census rows
 9. [PASS] every corridor meets its own minimum_hotel_count
10. [PASS] augusta-ga absent from LIVE sharded_market_ids()
11. [PASS] zero drift in LIVE generated global artifacts
12. [PASS] byte-reproducible rebuild (2nd run matches 1st)
13. [PASS] git status touches only augusta-owned paths
14. [PASS] zero fabricated policy facts (all POLICY_NOT_VERIFIED, zero terminal partition rows)
15. [PASS] market_id consistent across all 5 documents

15 / 15 PASS
```

## Parallel-run safety (Phase 21)

`git status --short --untracked-files=all` shows **19 new, untracked files**,
every one under `launch_packages/pettripfinder/markets/{staging,proposed,
reports}/...augusta-ga...`, `identity_census_proposed/augusta-ga.json`, or
`scripts/pettripfinder/augusta_ga_*.py`. Zero modified files.

- CROSS-MARKET FILE CHANGES = 0
- SHARED FACTORY FILE CHANGES = 0
- CANONICAL LIVE CHANGES = 0
- DEPLOYMENT STATE CHANGES = 0

## Performance

Timing was not separately instrumented by a stopwatch in this session (unlike
some prior markets' mm:ss figures); the visible cost is: four research
agents ran concurrently in background (durations 240s, 258s, 264s, 425s),
followed by a single-pass build/validate/fix cycle (one real FAST failure
each on ZIP-corridor overlap and a missing `market_name` field, both fixed
immediately) plus shadow-package/report assembly. No wall-clock total is
claimed beyond "well under the session's overall duration."

- PAID PROVIDER COST = $0 (Overpass/OSM was attempted free and returned 406
  from this sandbox network; all other lanes were free web search/fetch --
  no Google Places, Foursquare, or paid API calls were made)
- FOUNDER INTERVENTION REQUIRED = No
- PEAK MEMORY = not measured

## Future registration/reseal steps (NOT performed this run)

1. Read `CURRENT VERIFIED LIVE` (no reader exists at this branch's base --
   will need to be pulled from whichever branch holds current production
   state, e.g. via the Outer Banks launch's live artifact).
2. Register `augusta-ga` into the live market registry
   (`launch_packages/pettripfinder/markets/augusta-ga.json`) and its
   authority shard into the live `markets/authority/augusta-ga/` directory.
3. Freshly reseal the census/partition against the then-current parent.
4. Capture real per-property pet-policy evidence (this pass deliberately did
   none) and resolve the 6 identity holds above (a phone call or a direct
   fetch of the IHG code / two addresses would likely settle the `agsjd`
   collision quickly).
5. Regenerate global compatibility artifacts:
   `python -m scripts.pettripfinder.build_global_authority --write`.
6. Run applicable FAST / regression, compose the production candidate,
   independently reproduce, create the founder packet, and await exact
   candidate authorization before any deploy.

---

## FINAL ANSWERS

1. START TIMESTAMP = 2026-09-14 (session start; not separately stopwatched)
2. ZERO_TO_SOURCE_READY = single continuous session; not separately stopwatched (see Performance)
3. TOTAL DISCOVERED = 141
4. PROPOSED CENSUS = 82
5. VALID PET-FRIENDLY = 0
6. VALID VERIFIED-NO-PETS = 0
7. RESOLVED / UNRESOLVED = 76 / 6
8. HOLDS BY CLASS = identity 6, routing 0, access-blocked(properties) 0, evidence 0, geography 0, military/restricted 3, paid 0, founder 0, closed/retired 0
9. CORRIDOR COVERAGE = Downtown 8, Washington Road 30, West Augusta 17, Gordon Highway/Fort Eisenhower 15, South Augusta 3, Grovetown 9 (= 82)
10. NORTH AUGUSTA / SOUTH CAROLINA DISCOVERY ACCOUNTING = 26 discovered (North Augusta 8, Aiken 15, Edgefield 3), 0 included, 26 outside, 0 review
11. SOUTH CAROLINA PROFILES INCLUDED = 0
12. OWNED EVIDENCE REUSED = 0 (none existed in this worktree to reuse)
13. SHADOW PACKAGE CREATED = YES
14. PACKAGE REPRODUCIBLE = YES (byte-identical across 2 independent build runs)
15. PACKAGE DIGEST = sha256:a9c7353deda809e4... (see shadow package file for full digest)
16. APPLICABLE FAST CHECKS = 15 / 15 PASS
17. PAID PROVIDER COST = $0
18. FOUNDER INTERVENTION REQUIRED = No
19. CROSS-MARKET FILE CHANGES = 0
20. FACTORY CODE CHANGED = NO
21. BROAD REGRESSION RUN = NO
22. FINAL PRODUCTION CANDIDATE CREATED = NO
23. FOUNDER AUTHORIZATION CREATED = NO
24. AUGUSTA DEPLOYED = NO
25. BLOCKED ONLY ON RELEASE QUEUE = YES (identity/census work is source-ready; policy-evidence capture and registration are the deferred next steps, not blockers to source-ready status)
26. origin == HEAD = YES (both `2d4f2ddb1fc740728d78ba14f2a69e43b2fd0149`)
27. tree clean = YES

AUGUSTA SOURCE READY = YES
AUGUSTA FINAL CANDIDATE = NO
AUGUSTA DEPLOYED = NO
BROAD REGRESSION RUNS = 0
FACTORY CODE CHANGED = NO
WAITING FOR RELEASE QUEUE = YES
