# PTF-FORT-MYERS-FL-PRODUCTION-DEPLOYMENT-004 — FINAL

**Status: FORT MYERS IS LIVE.** Fort Myers / Cape Coral / Sanibel, Florida is production market #46.

- **What was deployed:** the exact founder-authorized candidate `C:\t\fm4a\site`. Nothing was rebuilt, resealed,
  re-registered, re-acquired or re-authorized, and candidate B was not run again.
- **The deploy:** `netlify deploy --prod --no-build`, run **once**, as deploy **`6ac8d0c021f9d04e6aa82455`**.
- **Verification:** every host check passed (25/25), so rollback was not required.

**Branch:** `worker/ptf-fort-myers-fl-market-001` (worktree `C:\Atlas-Fort-Myers-FL-Hardened-V1`).

**Commits:**
- `35a04413` — the deployment state: authorization consumed, deployment record, live manifest, supersessions, pin,
  predeploy and live-verification reports, and the market-local deploy module
  `scripts/pettripfinder/fort_myers_fl_deployment_004.py`. This is the new **live lineage commit**.
- the final commit — this report.

## 1. Predeploy parent (Phase 1)

Re-resolved at 11:09:45Z (2026-10-09) with the canonical resolver (`release_index live-source --fetch --verify-host`),
Netlify `getSite` and a hash of the served sitemap. Predeploy PASS was written at 11:30:25Z. It was re-checked straight
after the live manifest was written, right before the call: still `6ac6f3d2`, state ready, sitemap `3806de5e…`.

| | |
|---|---|
| PREDEPLOY LIVE SOURCE COMMIT | `3d812f28de52555b15adaa5f9a19049cd064ed32` (live lineage commit; built_from `6959e985`) |
| PREDEPLOY LIVE DEPLOYMENT | **`6ac6f3d213d002249f9c3e67`** (Salt Lake City; host `published_deploy` = this id, state ready) |
| PREDEPLOY LIVE BUNDLE | `2738162fe62b5a5395c266c54d701e8d23b45da28ea02c6b1c47eebb3760df12` |
| PREDEPLOY LIVE SITEMAP | `3806de5e5093cd63f570ab60f83a76f29712b9a9158cb6bfe2dce8f51eb89dc9` — the served sitemap hashed to this and is byte-identical to the live artifact `C:/t/slc4a`; saved as the parent route set (4,885 locs) |
| PREDEPLOY LIVE MARKETS / PROFILES | 45 / 4,373 |
| PREDEPLOY LIVE RELEASE-INDEX / SERVED ROUTES | 4,807 / 4,885 |
| HOST VERIFIED | YES |

## 2. Authorization and candidate integrity (Phases 2–13)

`fort_myers_fl_deployment_004.py predeploy` (`markets/reports/fort_myers_fl_predeploy_004.json`): **PASS**.

Nothing was typed in from the recap. Each value below was read mechanically:
- **The authorization:** the one record naming fort-myers-fl that `PTF-FORT-MYERS-FL-FOUNDER-LAUNCH-AUTHORIZATION-003`
  wrote.
- **The package, its digest and the FAST receipt:** from the readiness packet.
- **The digests:** from the committed candidate manifest.

| | |
|---|---|
| DEPLOYMENT AUTHORIZATION | `ptf-auth-fort-myers-003-aad66024bf06`, market fort-myers-fl. Before: **AUTHORIZED**, CONSUMED NO, DEPLOY_ID NONE |
| AUTHORIZED PACKAGE | `pkg-fort-myers-fl-919f61116936bf5e` |
| AUTHORIZED PACKAGE DIGEST | `sha256:919f61116936bf5e23fe42f0aa745c87c6020a7896f7149b64ec603359ace47e` |
| FOUNDER DECISION COMMIT = AUTHORIZED SOURCE COMMIT | `ab616e2e53f8f82c6a36e3dd6c73f2736946ca54` (the BUILD commit). The authorization source names both it and the founder-binding commit **`6a425592`**. The participation decision (work order …-003) binds 6a425592 and reads FOUNDER_AUTHORIZED_FOR_LAUNCH |
| AUTHORIZED BUNDLE | `aad66024bf065e8b0858ef1b9b45faf57b3143bedfc644d17370b568da6c9795` |
| AUTHORIZED SITEMAP | `f3f87e096d24aebbda6eed88406bf92284b52aafe1e71ed3a9ccc177813af86c` |
| AUTHORIZED PARENT = ROLLBACK TARGET | `6ac6f3d213d002249f9c3e67`. This is the readiness packet's parent and the exact current production deployment |
| refused | shadow package `pkg-fort-myers-fl-68b3cfa8…` is not bound. No other authorization was deployable |
| checks | `verify_authorization []`, `deployability_problems []`, `verify_target []` (pettripfinder-prod / pettripfinder.com) |
| candidate on disk | `verify_bundle_directory []`: all **26,724** files re-hashed from `C:\t\fm4a\site` equal the authorization. **AUTHORIZED BUNDLE MATCH PASS**, **AUTHORIZED SITEMAP MATCH PASS** (the sitemap hashed from disk is `f3f87e09…`). The committed candidate manifest still describes the bundle on disk |
| candidate accounting | 46 markets / 4,430 profiles / **4,869** release-index routes / **4,948** served routes. Fort Myers: 57 profiles / 62 release-index routes / 63 served routes. The route set equals the staging route set exactly |
| determinism | **BYTE_IDENTICAL**: 26,724 files compared between `C:/t/fm4a` and `C:/t/fm4b`, 0 differing |
| delta | +346 files, all Fort Myers'; 0 removed; only `sitemap.xml` changed; 0 prior-market files changed; 0 unclassified. PRIOR MARKETS / PROFILES / INDEX ROUTES / SERVED ROUTES LOST 0 / 0 / 0 / 0. UNEXPECTED MARKET / PROFILE / ROUTE / FILE DELTA `[]` |
| held cohort | unapproved profiles 0. 51 unresolved and 34 verified-no-pets: 0 published. Named groups 0 published (Old Luckett 2 rows, Quality Inn 4760 1, Latitude 26 5, Pink Shell + Edison 2, router-exhausted 49). 0 pages at 9455 Old Luckett / 4760 S Cleveland / 4701 Bonita Beach Rd; 0 Travelodge pages at 4760. No `identity_resolutions.json` ruling |
| operating | published by status `{CURRENTLY_OPEN: 57}`. Nonoperating, temporarily closed, permanently closed, preopening, closed-for-rebuild and status-unknown profiles: 0 each |
| municipality | 57 pages: Lee 57. Wrong city/state/ZIP/county 0, Naples 0, other-market text 0 |
| non-hotel | published: timeshare 0/5, private condo / residence / rental 0/121, other non-hotel 0/44, military 0/0 |
| reader | explicit refusal 0, question-only 0, service-animal-only 0; shared reader not modified |
| fees | 5 safe single-basis published / 22 tiered withheld / 5 unsafe or multi-amount withheld. 5 render exactly; 27 withheld records render no fee; 0 fee-less pages gain one. MISLEADING SINGLE FEES 0 |
| route schemes | 283 `/go/` pages (absolute http 171, internal 57, tel 55). INVALID 0, HTTP-LESS FIRST-PARTY 0 |
| collisions | cross-market 0, bare-chain 0, duplicate excluded identities 0 |
| FAST receipt | see below |

**FAST receipt:**
- Resolved mechanically from the readiness packet: `pkg-fort-myers-fl-919f61116936bf5e-71b99a5343da6d8f.json`.
  - `RECEIPT_DIGEST` was recomputed from its content and equals `sha256:71b99a53…`, the digest the packet binds.
  - It is the **only** currently eligible receipt for the package.
- **RULE J NONEMPTY PASS:** 367 files / 351 HTML, market bundle `cc784255…` (the packet's bound bundle).
- **RULE K NONVACUOUS PASS:** BYTE_IDENTICAL. 0 defects.
- The source-ready shadow digest `68b3cfa8…` selects nothing from the canonical receipts. The failed first seal never
  produced a receipt. **FAILED FIRST-SEAL RECEIPT ELIGIBLE = NO.**
- **Correction to the order:** it quoted the receipt suffix `7f8811ce601d32c4`. That suffix is **Salt Lake City's**
  receipt (`pkg-salt-lake-city-ut-6d474d29…-7f8811ce601d32c4`), not Fort Myers'. The Fort Myers suffix, read from the
  canonical records and also given in the founder-authorization report, is **`71b99a5343da6d8f`**.

**Two fixes to the new module before the deploy (no data or bytes touched):**
- The first predeploy run compared the receipt digest against a hash of the receipt *file*. The packet's digest is
  the lane's own `RECEIPT_DIGEST` (canonical JSON). The module now recomputes it the lane's way.
- A dry run of `verify-live` against the unchanged parent (no write) found that the 4760 S Cleveland row is a
  non-admitted census row, so its retired Travelodge aliases had not been read. The check failed closed; it now reads
  the row at its own premises.

## 3. Live manifest and the deploy (Phases 14–15)

**Live manifest:** `write-manifest --write` wrote `deploy/netlify/global_deployment_manifest.json` from the exact
authorized bytes.
- It carries bundle `aad66024…`, sitemap `f3f87e09…`, 46 markets, 4,430 profiles and 4,948 routes.
- It is equal to the committed candidate manifest; `verify_manifest []`.
- No candidate byte was altered.

**The deploy, run ONCE:** `netlify deploy --prod --no-build --dir C:\t\fm4a\site --site pettripfinder-prod`

| | |
|---|---|
| DEPLOY START | 2026-10-09T11:31:47Z |
| DEPLOY COMPLETE | 2026-10-09T11:32:50Z (host `published_at` 11:32:49.708Z) |
| NETLIFY DEPLOYMENT ID | **`6ac8d0c021f9d04e6aa82455`** |
| EXIT STATUS | 0 |

## 4. Host verification (Phases 16–21)

`verify-live` (`markets/reports/fort_myers_fl_live_verification_004.json`): **ALL LIVE CHECKS PASS — 25 / 25**.

| | |
|---|---|
| host | publishes `6ac8d0c021f9d04e6aa82455`, state ready, context production; **previous deploy `6ac6f3d213d002249f9c3e67`** (the Salt Lake City parent) |
| HOST SITEMAP MATCH | **PASS**: the served `sitemap.xml` hashes to `f3f87e09…` and is byte-identical to `C:\t\fm4a\site\sitemap.xml`. The served route SET is identical to the authorized candidate's |
| LIVE ACCOUNTING | **46 markets / 4,430 profiles / 4,869 release-index routes / 4,948 served routes**. The canonical live index confirms it after the record: fort-myers-fl participating with 57 profiles |
| FORT MYERS ROUTES | expected set taken from the authorized candidate's own sitemap, not arithmetic: 63 = hub + policy comparison + 4 corridors (bonita-springs, colonial-cleveland, daniels-six-mile, rsw-airport-gateway) + 57 profiles. **63 / 63 HTTP 200**, 0 missing, 0 no-response |
| PRIOR PRODUCTION | all **4,885** parent served routes re-fetched in 13 detached sequential batches of up to 400 (atomic rename per batch, PID 3656, 11:33:27Z start). **4,885 / 4,885 HTTP 200**. First-pass no-response 0, so no recheck was needed. Parent routes missing from the live sitemap 0; added routes 63, all Fort Myers |
| spot hubs | **200:** Salt Lake City, New Orleans, Kansas City, Minneapolis, Portland, Seattle, San Antonio, Austin, Phoenix, Denver, San Diego, Jacksonville FL, West Palm Beach, Fort Lauderdale, Augusta, Miami, Tampa, Orlando, and the Fort Myers hub. **Detroit 404** (still withheld) |
| bundle quality | broken links 0, collisions 0, global shadowing 0, canonical violations 0 |

### Profile bytes (Phase 18)

- **All 57 live Fort Myers profiles** were fetched whole: **57 / 57 byte-identical** to the artifact. That is every
  profile, not a sample, so every area is covered:
  - Fort Myers 34 (including the RSW / Gateway corridor);
  - Bonita Springs 6, Cape Coral 4, Estero 4, Fort Myers Beach 4, Captiva 3, North Fort Myers 2.
  - **Sanibel has no published profile** in the authorized cohort, so there was none to sample.
- **29 further pages:** the apex, the category root, robots.txt, llms.txt, sitemap.xml, the Fort Myers hub, its policy
  comparison, all 4 corridors and 18 other markets' hubs. 29 / 29 byte-identical.
- **All 283 `/go/` pages** were fetched whole: 283 / 283 byte-identical.
- **SAMPLED FORT MYERS PAGES 57 profiles + 6 hub/comparison/corridor pages + 283 /go/ pages; BYTE IDENTICAL all;
  MISMATCHES 0.**

### Held rows on production (Phases 5, 19)

- **All 85 unpublished census rows** (51 unresolved + 34 verified-no-pets) were probed at the census slug and at the
  route the site forms from the name: 102 URLs, **all 404**, none in the served sitemap, 0 shared with a published
  route. **ALL 51 HELD ROWS PUBLISHED = 0.**
- Founder-named rows, listed explicitly:

| row | URLs probed | result |
|---|---|---|
| Comfort Suites Fort Myers East I-75 (9455 Old Luckett, Bldg A) | `/comfort-suites-fort-myers-east-i-75/` | 404, unpublished |
| MainStay Suites Fort Myers East I-75 (9455 Old Luckett, Bldg B) | `/mainstay-suites-fort-myers-east-i-75/` | 404, unpublished |
| Quality Inn Fort Myers Cape Coral (4760 S Cleveland Ave) | `/quality-inn-fort-myers-cape-coral/` | 404, unpublished |
| old Travelodge at 4760 S Cleveland — the retired names from that row's own aliases: Travelodge by Wyndham Fort Myers North, Travelodge Fort Myers North | `/travelodge-by-wyndham-fort-myers-north/`, `/travelodge-fort-myers-north/` | 404, 404, unpublished |
| Latitude 26 Waterfront Inn & Suites (4701 Bonita Beach Rd) | both route forms | 404, unpublished |
| all 5 Latitude 26 rows | 7 URLs | all 404 |
| Pink Shell Beach Resort & Marina | both route forms | 404, unpublished |
| Edison Beach House Hotel | `/edison-beach-house-hotel/` | 404, unpublished |

**The Quality Inn / Travelodge distinction:**
- The **only** live Travelodge is *Travelodge by Wyndham Fort Myers/Cape Coral*. Its page states **13353 North Cleveland
  Avenue, North Fort Myers 33903**; it is a different building.
- No live profile states a street at 4760 S Cleveland, 9455 Old Luckett or 4701 Bonita Beach Rd. The founder-held
  premises live hits are `[]`.

### Operating status and beach / island (Phases 6, 20)

- **Operating:** all 57 live profiles are `CURRENTLY_OPEN` with no nonoperating signal. None of the 33 nonoperating or
  status-unknown census rows has a live route.
  - NONOPERATING / TEMPORARILY CLOSED / PERMANENTLY CLOSED / PREOPENING PROFILES PUBLISHED: **0 / 0 / 0 / 0**.
- **Fort Myers Beach (4 live, all open):** Best Western Plus Beach Resort; Hampton Inn & Suites Fort Myers Beach / Sanibel
  Gateway; Holiday Inn Express & Suites Ft Myers Beach / Sanibel Gateway; Lighthouse Resort Inn & Suites.
- **Captiva (3 live, all open):** Captiva Island Inn, Jensen's Marina & Cottages, 'Tween Waters.
- **Sanibel:** 0 live.
- NONOPERATING BEACH / ISLAND PROFILES **0**. The post-hurricane decisions stand: no closed, temporarily closed or
  historical identity has resurfaced.

### Municipality and boundary (Phase 7)

- Every one of the 57 live profiles states FL, the municipality its census row carries, its own ZIP and its own street.
  All are in Lee County.
- By municipality: Fort Myers 34, Bonita Springs 6, Cape Coral 4, Estero 4, Fort Myers Beach 4, Captiva 3, North Fort
  Myers 2.
- **WRONG-CITY FORT MYERS IDENTITIES LIVE = 0. NAPLES PROFILES ADMITTED LIVE = 0.** No live locality names Naples, Marco
  Island, Punta Gorda or Port Charlotte (or any other Collier / Charlotte County place).

### Non-hotel, reader, fees, routes (Phases 8–11)

- **Non-hotel:** 5 timeshare, 121 private condo / residence / rental and 44 other non-hotel identities each return 404
  and hold no served route. **0 published.** Military-restricted: 0 rows.
- **Reader:** explicit refusal PF 0, question-only PF 0, service-animal-only 0. The shared reader and the shared
  validator are unchanged.
- **Fees live:** 5 fee records render exactly the authorized amount. The 52 fee-less records render none (the 27
  withheld records among them). FEES RENDERED WRONGLY 0.
- **Routes:** every `/go/` page redirects to `tel:`, an internal path, or absolute `http(s)://` with a host.
  INVALID ROUTE SCHEMES 0, HTTP-LESS FIRST-PARTY 0, **INVALID /go/ LINKS 0**. RULE-J route validation PASS.

### All 63 Fort Myers routes (Phase 17)

Every route 200, derived from the authorized candidate's sitemap; then all 57 live profiles with their live municipality, ZIP, operating status and byte comparison:

| # | route | HTTP |
|---|---|---|
| 1 | `/pet-friendly-hotels/fort-myers-fl/` | 200 |
| 2 | `/pet-friendly-hotels/fort-myers-fl/americas-best-value-inn-ft-myers/` | 200 |
| 3 | `/pet-friendly-hotels/fort-myers-fl/baymont-by-wyndham-fort-myers-central/` | 200 |
| 4 | `/pet-friendly-hotels/fort-myers-fl/baymont-inn-suites-by-wyndham-fort-myers-i-75/` | 200 |
| 5 | `/pet-friendly-hotels/fort-myers-fl/best-western-fort-myers-waterfront/` | 200 |
| 6 | `/pet-friendly-hotels/fort-myers-fl/best-western-plus-beach-resort/` | 200 |
| 7 | `/pet-friendly-hotels/fort-myers-fl/bonita-springs/` | 200 |
| 8 | `/pet-friendly-hotels/fort-myers-fl/candlewood-suites-fort-myers/` | 200 |
| 9 | `/pet-friendly-hotels/fort-myers-fl/candlewood-suites-ft-myers-i-75/` | 200 |
| 10 | `/pet-friendly-hotels/fort-myers-fl/captiva-island-inn/` | 200 |
| 11 | `/pet-friendly-hotels/fort-myers-fl/colonial-cleveland/` | 200 |
| 12 | `/pet-friendly-hotels/fort-myers-fl/courtyard-by-marriott-fort-myers-at-i-75-and-gulf-coast-town-center/` | 200 |
| 13 | `/pet-friendly-hotels/fort-myers-fl/courtyard-by-marriott-fort-myers-cape-coral/` | 200 |
| 14 | `/pet-friendly-hotels/fort-myers-fl/daniels-six-mile/` | 200 |
| 15 | `/pet-friendly-hotels/fort-myers-fl/days-inn-by-wyndham-fort-myers/` | 200 |
| 16 | `/pet-friendly-hotels/fort-myers-fl/drury-inn-suites-fort-myers-airport-fgcu/` | 200 |
| 17 | `/pet-friendly-hotels/fort-myers-fl/embassy-suites-fort-myers-estero/` | 200 |
| 18 | `/pet-friendly-hotels/fort-myers-fl/extended-stay-america-premier-suites-fort-myers-airport/` | 200 |
| 19 | `/pet-friendly-hotels/fort-myers-fl/extended-stay-america-select-suites-fort-myers-northeast/` | 200 |
| 20 | `/pet-friendly-hotels/fort-myers-fl/fairfield-inn-suites-bonita-springs/` | 200 |
| 21 | `/pet-friendly-hotels/fort-myers-fl/hampton-inn-bonita-springs-naples-north/` | 200 |
| 22 | `/pet-friendly-hotels/fort-myers-fl/hampton-inn-by-hilton-fort-myers-downtown/` | 200 |
| 23 | `/pet-friendly-hotels/fort-myers-fl/hampton-inn-ft-myers-airport-i-75/` | 200 |
| 24 | `/pet-friendly-hotels/fort-myers-fl/hampton-inn-suites-cape-coral-fort-myers-area-fl/` | 200 |
| 25 | `/pet-friendly-hotels/fort-myers-fl/hampton-inn-suites-fort-myers-beach-sanibel-gateway/` | 200 |
| 26 | `/pet-friendly-hotels/fort-myers-fl/hampton-inn-suites-fort-myers-colonial-blvd/` | 200 |
| 27 | `/pet-friendly-hotels/fort-myers-fl/hampton-inn-suites-fort-myers-estero-fgcu/` | 200 |
| 28 | `/pet-friendly-hotels/fort-myers-fl/hideaway-waterfront-resort-hotel/` | 200 |
| 29 | `/pet-friendly-hotels/fort-myers-fl/hilton-garden-inn-fort-myers-airport-fgcu/` | 200 |
| 30 | `/pet-friendly-hotels/fort-myers-fl/hilton-garden-inn-fort-myers/` | 200 |
| 31 | `/pet-friendly-hotels/fort-myers-fl/holiday-inn-express-cape-coral-fort-myers-area/` | 200 |
| 32 | `/pet-friendly-hotels/fort-myers-fl/holiday-inn-express-suites-ft-myers-beach-sanibel-gateway/` | 200 |
| 33 | `/pet-friendly-hotels/fort-myers-fl/holiday-inn-express-suites-naples-north-bonita-springs/` | 200 |
| 34 | `/pet-friendly-hotels/fort-myers-fl/holiday-inn-fort-myers-downtown-area/` | 200 |
| 35 | `/pet-friendly-hotels/fort-myers-fl/home2-suites-by-hilton-fort-myers-airport/` | 200 |
| 36 | `/pet-friendly-hotels/fort-myers-fl/home2-suites-by-hilton-fort-myers-colonial-blvd/` | 200 |
| 37 | `/pet-friendly-hotels/fort-myers-fl/homewood-suites-by-hilton-bonita-springs-naples-north-fl/` | 200 |
| 38 | `/pet-friendly-hotels/fort-myers-fl/homewood-suites-by-hilton-fort-myers-airport-fgcu/` | 200 |
| 39 | `/pet-friendly-hotels/fort-myers-fl/homewood-suites-by-hilton-fort-myers/` | 200 |
| 40 | `/pet-friendly-hotels/fort-myers-fl/hyatt-place-fort-myers-at-the-forum/` | 200 |
| 41 | `/pet-friendly-hotels/fort-myers-fl/hyatt-place-fort-myers-estero/` | 200 |
| 42 | `/pet-friendly-hotels/fort-myers-fl/hyatt-regency-coconut-point-resort-and-spa/` | 200 |
| 43 | `/pet-friendly-hotels/fort-myers-fl/jensen-s-marina-and-cottages/` | 200 |
| 44 | `/pet-friendly-hotels/fort-myers-fl/la-quinta-inn-suites-by-wyndham-bonita-springs-naples-n/` | 200 |
| 45 | `/pet-friendly-hotels/fort-myers-fl/la-quinta-inn-suites-by-wyndham-ft-myers-sanibel-gateway/` | 200 |
| 46 | `/pet-friendly-hotels/fort-myers-fl/lighthouse-resort-inn-suites/` | 200 |
| 47 | `/pet-friendly-hotels/fort-myers-fl/policy-comparison/` | 200 |
| 48 | `/pet-friendly-hotels/fort-myers-fl/quality-suites-fort-myers-i-75/` | 200 |
| 49 | `/pet-friendly-hotels/fort-myers-fl/residence-inn-fort-myers-at-i-75-and-gulf-coast-town-center/` | 200 |
| 50 | `/pet-friendly-hotels/fort-myers-fl/residence-inn-fort-myers-sanibel/` | 200 |
| 51 | `/pet-friendly-hotels/fort-myers-fl/residence-inn-fort-myers/` | 200 |
| 52 | `/pet-friendly-hotels/fort-myers-fl/rsw-airport-gateway/` | 200 |
| 53 | `/pet-friendly-hotels/fort-myers-fl/spark-by-hilton-fort-myers/` | 200 |
| 54 | `/pet-friendly-hotels/fort-myers-fl/springhill-suites-fort-myers-airport/` | 200 |
| 55 | `/pet-friendly-hotels/fort-myers-fl/stay-well-inn-suites/` | 200 |
| 56 | `/pet-friendly-hotels/fort-myers-fl/studiores-by-marriott-fort-myers-airport/` | 200 |
| 57 | `/pet-friendly-hotels/fort-myers-fl/the-westin-cape-coral-resort-at-marina-village/` | 200 |
| 58 | `/pet-friendly-hotels/fort-myers-fl/towneplace-suites-fort-myers-estero/` | 200 |
| 59 | `/pet-friendly-hotels/fort-myers-fl/towneplace-suites-fort-myers-gulf-coast/` | 200 |
| 60 | `/pet-friendly-hotels/fort-myers-fl/towneplace-suites-fort-myers-southeast/` | 200 |
| 61 | `/pet-friendly-hotels/fort-myers-fl/travelodge-by-wyndham-fort-myers-cape-coral/` | 200 |
| 62 | `/pet-friendly-hotels/fort-myers-fl/tween-waters/` | 200 |
| 63 | `/pet-friendly-hotels/fort-myers-fl/woodspring-suites-fort-myers-cape-coral/` | 200 |

| profile | municipality | ZIP | status | bytes |
|---|---|---|---|---|
| americas best value inn ft myers | Fort Myers | 33907 | CURRENTLY_OPEN | identical |
| baymont by wyndham fort myers central | Fort Myers | 33907 | CURRENTLY_OPEN | identical |
| baymont inn and suites by wyndham fort myers i 75 | Fort Myers | 33912 | CURRENTLY_OPEN | identical |
| best western fort myers waterfront | North Fort Myers | 33903 | CURRENTLY_OPEN | identical |
| best western plus beach resort | Fort Myers Beach | 33931 | CURRENTLY_OPEN | identical |
| candlewood suites fort myers | Fort Myers | 33908 | CURRENTLY_OPEN | identical |
| candlewood suites ft myers i 75 | Fort Myers | 33913 | CURRENTLY_OPEN | identical |
| captiva island inn | Captiva | 33924 | CURRENTLY_OPEN | identical |
| courtyard by marriott fort myers at i 75 and gulf coast town center | Fort Myers | 33913 | CURRENTLY_OPEN | identical |
| courtyard by marriott fort myers cape coral | Fort Myers | 33916 | CURRENTLY_OPEN | identical |
| days inn by wyndham fort myers | Fort Myers | 33907 | CURRENTLY_OPEN | identical |
| drury inn and suites fort myers airport fgcu | Fort Myers | 33913 | CURRENTLY_OPEN | identical |
| embassy suites fort myers estero | Estero | 33928 | CURRENTLY_OPEN | identical |
| extended stay america premier suites fort myers airport | Fort Myers | 33912 | CURRENTLY_OPEN | identical |
| extended stay america select suites fort myers northeast | Fort Myers | 33905 | CURRENTLY_OPEN | identical |
| fairfield inn and suites bonita springs | Bonita Springs | 34135 | CURRENTLY_OPEN | identical |
| hampton inn and suites cape coral fort myers area fl | Cape Coral | 33904 | CURRENTLY_OPEN | identical |
| hampton inn and suites fort myers beach sanibel gateway | Fort Myers Beach | 33931 | CURRENTLY_OPEN | identical |
| hampton inn and suites fort myers colonial blvd | Fort Myers | 33916 | CURRENTLY_OPEN | identical |
| hampton inn and suites fort myers estero fgcu | Estero | 33928 | CURRENTLY_OPEN | identical |
| hampton inn bonita springs naples north | Bonita Springs | 34135 | CURRENTLY_OPEN | identical |
| hampton inn by hilton fort myers downtown | Fort Myers | 33901 | CURRENTLY_OPEN | identical |
| hampton inn ft myers airport i 75 | Fort Myers | 33912 | CURRENTLY_OPEN | identical |
| hideaway waterfront resort and hotel | Cape Coral | 33904 | CURRENTLY_OPEN | identical |
| hilton garden inn fort myers | Fort Myers | 33907 | CURRENTLY_OPEN | identical |
| hilton garden inn fort myers airport fgcu | Fort Myers | 33913 | CURRENTLY_OPEN | identical |
| holiday inn express and suites ft myers beach sanibel gateway | Fort Myers Beach | 33931 | CURRENTLY_OPEN | identical |
| holiday inn express and suites naples north bonita springs | Bonita Springs | 34135 | CURRENTLY_OPEN | identical |
| holiday inn express cape coral fort myers area | Cape Coral | 33904 | CURRENTLY_OPEN | identical |
| holiday inn fort myers downtown area | Fort Myers | 33901 | CURRENTLY_OPEN | identical |
| home2 suites by hilton fort myers airport | Fort Myers | 33913 | CURRENTLY_OPEN | identical |
| home2 suites by hilton fort myers colonial blvd | Fort Myers | 33916 | CURRENTLY_OPEN | identical |
| homewood suites by hilton bonita springs naples north fl | Bonita Springs | 34135 | CURRENTLY_OPEN | identical |
| homewood suites by hilton fort myers | Fort Myers | 33907 | CURRENTLY_OPEN | identical |
| homewood suites by hilton fort myers airport fgcu | Fort Myers | 33913 | CURRENTLY_OPEN | identical |
| hyatt place fort myers at the forum | Fort Myers | 33905 | CURRENTLY_OPEN | identical |
| hyatt place fort myers estero | Estero | 33928 | CURRENTLY_OPEN | identical |
| hyatt regency coconut point resort and spa | Bonita Springs | 34134 | CURRENTLY_OPEN | identical |
| jensen s marina and cottages | Captiva | 33924 | CURRENTLY_OPEN | identical |
| la quinta inn and suites by wyndham bonita springs naples n | Bonita Springs | 34134 | CURRENTLY_OPEN | identical |
| la quinta inn and suites by wyndham ft myers sanibel gateway | Fort Myers | 33908 | CURRENTLY_OPEN | identical |
| lighthouse resort inn and suites | Fort Myers Beach | 33931 | CURRENTLY_OPEN | identical |
| quality suites fort myers i 75 | Fort Myers | 33912 | CURRENTLY_OPEN | identical |
| residence inn fort myers | Fort Myers | 33966 | CURRENTLY_OPEN | identical |
| residence inn fort myers at i 75 and gulf coast town center | Fort Myers | 33913 | CURRENTLY_OPEN | identical |
| residence inn fort myers sanibel | Fort Myers | 33908 | CURRENTLY_OPEN | identical |
| spark by hilton fort myers | Fort Myers | 33912 | CURRENTLY_OPEN | identical |
| springhill suites fort myers airport | Fort Myers | 33912 | CURRENTLY_OPEN | identical |
| stay well inn and suites | Fort Myers | 33912 | CURRENTLY_OPEN | identical |
| studiores by marriott fort myers airport | Fort Myers | 33912 | CURRENTLY_OPEN | identical |
| the westin cape coral resort at marina village | Cape Coral | 33914 | CURRENTLY_OPEN | identical |
| towneplace suites fort myers estero | Estero | 33928 | CURRENTLY_OPEN | identical |
| towneplace suites fort myers gulf coast | Fort Myers | 33912 | CURRENTLY_OPEN | identical |
| towneplace suites fort myers southeast | Fort Myers | 33966 | CURRENTLY_OPEN | identical |
| travelodge by wyndham fort myers cape coral | North Fort Myers | 33903 | CURRENTLY_OPEN | identical |
| tween waters | Captiva | 33924 | CURRENTLY_OPEN | identical |
| woodspring suites fort myers cape coral | Fort Myers | 33907 | CURRENTLY_OPEN | identical |

## 5. Bounded post-deploy quality (Phase 22)

No broad regression was run.

| | |
|---|---|
| pin tests + policy-reader tests | `tests/pettripfinder/contracts/test_market_state_pins.py` + `tests/pettripfinder/test_question_negation_reader_001.py`: **337 passed**, 0 failed (one pytest process, 9.3 s) |
| release-contract verification | `release_contracts.verify_all()`: **47 / 47 clean** |
| global-authority check | `build_global_authority --check`: all generated artifacts match the shards (1,920 exclusions, 4,579 seed rows) |
| participation | fort-myers-fl FOUNDER_AUTHORIZED_FOR_LAUNCH; `decision_problems []` |
| bundle | BROKEN LINKS 0, COLLISIONS 0, CANONICAL VIOLATIONS 0, GLOBAL SHADOWING 0, UNEXPECTED DELTA `[]` |
| FAST | RULE J NONEMPTY PASS, RULE K NONVACUOUS PASS, FAST RECEIPT ELIGIBLE YES |

## 6. Deployment state (Phase 23)

Written only after all 63 Fort Myers routes, all 4,885 parent routes, the host sitemap and the held-row probes had
passed.

- **Authorization** `ptf-auth-fort-myers-003-aad66024bf06`: AUTHORIZED → **DEPLOYED**, **CONSUMED YES**.
  - `status_history[-1]`: deployment_id `6ac8d0c021f9d04e6aa82455`, consumed_by `PTF-FORT-MYERS-FL-PRODUCTION-DEPLOYMENT-004`.
  - As with earlier markets, top-level `deploy_id` stays absent; consumption lives in the history.
  - No authorization is deployable afterwards.
- **Deployment record:** `deploy/netlify/deployment_records/ptf-deploy-fort-myers-004-6ac8d0c021f9d04e6aa82455.json`.
  - `work_order` is the authorizing order (…-003); `deployer.work_order` is this order.
  - `verify_record []`.
- **Supersessions:** `ptf-auth-salt-lake-city-003-2738162fe62b` is marked Historical (moved list `[]`, no drift). The
  new CURRENT entry is `ptf-auth-fort-myers-003-aad66024bf06`, with an empty moved list and 0 release-contract drift.
- **Pin:** `tests/pettripfinder/pins/deployment_state.json` live = `6ac8d0c0…`, rollback target `6ac6f3d2…`. Live and
  source agree on bundle, sitemap, profiles, routes, HTML pages and files.

## 7. Rollback (Phase 24)

**ROLLBACK REQUIRED = NO.** No critical check failed:
- no byte or sitemap mismatch;
- no Fort Myers or parent route lost;
- no held, Naples, nonoperating or non-hotel identity live;
- no reader, fee, scheme, collision or canonical defect.

The rollback target stays `6ac6f3d213d002249f9c3e67`, and no second deploy attempt was made.

## 8. Final accounting and next-market base (Phases 25–26)

| | |
|---|---|
| LIVE MARKETS / PROFILES | **46 / 4,430** |
| LIVE RELEASE-INDEX / SERVED ROUTES | **4,869 / 4,948** |
| FORT MYERS PROFILES / RELEASE-INDEX / SERVED ROUTES LIVE | **57 / 62 / 63** |
| PRIOR MARKETS PRESERVED | 45 / 45; prior profiles lost 0; prior routes lost 0 |
| CURRENT LIVE DEPLOYMENT | `6ac8d0c021f9d04e6aa82455` |
| CURRENT LIVE SOURCE COMMIT | `35a044135578f6bdf824baed92b14291910ac072` (live lineage commit; built_from `ab616e2e`). Resolver RESOLVED, host verified, problems `[]` |
| NEXT-MARKET AUTOMATIC BASE DERIVES | **YES**: `derive_registration_base(market, 35a04413…)` → base **`35a04413`**. From the final report commit it derives to that commit, which adds only this report |

**Processes:**
- Every process this order created has ended: predeploy, the `verify-live` dry run, the Fort Myers sweep, the detached
  parent sweep (PID 3656, which exited on its own) and `verify-live`.
- The pre-existing python process **PID 14180** was not touched and is still running.

## FINAL ANSWERS

1. PREDEPLOY LIVE DEPLOYMENT = 6ac6f3d213d002249f9c3e67
2. PREDEPLOY LIVE SOURCE COMMIT = 3d812f28de52555b15adaa5f9a19049cd064ed32 (built_from 6959e985)
3. DEPLOYMENT AUTHORIZATION = ptf-auth-fort-myers-003-aad66024bf06
4. AUTHORIZATION STATUS BEFORE = AUTHORIZED (unconsumed, no deploy id)
5. AUTHORIZED PACKAGE = pkg-fort-myers-fl-919f61116936bf5e
6. AUTHORIZED PACKAGE DIGEST = sha256:919f61116936bf5e23fe42f0aa745c87c6020a7896f7149b64ec603359ace47e
7. FOUNDER DECISION COMMIT = ab616e2e53f8f82c6a36e3dd6c73f2736946ca54
8. FOUNDER-BINDING COMMIT = 6a425592
9. AUTHORIZED CANDIDATE BUNDLE = aad66024bf065e8b0858ef1b9b45faf57b3143bedfc644d17370b568da6c9795
10. AUTHORIZED CANDIDATE SITEMAP = f3f87e096d24aebbda6eed88406bf92284b52aafe1e71ed3a9ccc177813af86c
11. CANDIDATE FILE COUNT = 26,724
12. CANDIDATE INTEGRITY = PASS (all 26,724 files re-hashed equal the authorization; BYTE_IDENTICAL twin build, 0 differing)
13. NETLIFY DEPLOYMENT ID = 6ac8d0c021f9d04e6aa82455
14. NETLIFY RESULT = SUCCESS (exit 0, state ready, production; previous deploy 6ac6f3d2)
15. HOST SITEMAP MATCH = PASS
16. LIVE MARKETS = 46
17. LIVE PROFILES = 4430
18. LIVE RELEASE-INDEX ROUTES = 4869
19. LIVE SERVED ROUTES = 4948
20. FORT MYERS PROFILES LIVE = 57
21. FORT MYERS RELEASE-INDEX ROUTES = 62
22. FORT MYERS SERVED ROUTES = 63
23. FORT MYERS ROUTES HTTP 200 = 63 / 63
24. SAMPLED FORT MYERS PAGES BYTE IDENTICAL = 57 / 57 profiles (every one) + 6 / 6 hub, comparison and corridor pages + 283 / 283 /go/ pages; mismatches 0
25. ALL 51 HELD ROWS PUBLISHED = 0
26. COMFORT SUITES OLD LUCKETT PUBLISHED = 0 (404)
27. MAINSTAY OLD LUCKETT PUBLISHED = 0 (404)
28. OLD TRAVELODGE S CLEVELAND PUBLISHED = 0 (both retired names 404; the only live Travelodge is 13353 N Cleveland)
29. QUALITY INN S CLEVELAND PUBLISHED = 0 (404)
30. LATITUDE 26 WATERFRONT PUBLISHED = 0 (all 5 Latitude 26 rows 404)
31. PINK SHELL PUBLISHED = 0 (404)
32. EDISON BEACH HOUSE PUBLISHED = 0 (404)
33. WRONG-CITY FORT MYERS IDENTITIES LIVE = 0
34. NAPLES PROFILES ADMITTED LIVE = 0
35. NONOPERATING PROFILES PUBLISHED = 0
36. TIMESHARE / VACATION-OWNERSHIP PROFILES PUBLISHED = 0
37. PET-FRIENDLY WITH EXPLICIT REFUSAL = 0
38. QUESTION-ONLY PET-FRIENDLY = 0
39. SERVICE-ANIMAL-ONLY ACCEPTANCE = 0
40. SAFE SINGLE-BASIS FEES = 5
41. WITHHELD FEES = 27 (22 tiered + 5 unsafe / multi-amount); 0 render
42. MISLEADING SINGLE FEES = 0
43. INVALID ROUTE SCHEMES = 0
44. INVALID /go/ LINKS = 0
45. PARENT ROUTES CHECKED = 4885
46. PARENT ROUTES HTTP 200 = 4885
47. PRIOR MARKETS LOST = 0
48. PRIOR PROFILES LOST = 0
49. PRIOR ROUTES LOST = 0
50. DETROIT STILL WITHHELD = YES (404)
51. RULE J NONEMPTY = PASS (367 files / 351 HTML)
52. RULE K NONVACUOUS = PASS (BYTE_IDENTICAL)
53. FAST RECEIPT ELIGIBLE = YES (pkg-fort-myers-fl-919f61116936bf5e-71b99a5343da6d8f; the order's 7f8811ce… suffix is Salt Lake City's)
54. BROKEN LINKS = 0
55. COLLISIONS = 0
56. CANONICAL VIOLATIONS = 0
57. GLOBAL SHADOWING = 0
58. UNEXPECTED DELTA = []
59. DEPLOYMENT AUTHORIZATION CONSUMED = YES (DEPLOYED by 6ac8d0c021f9d04e6aa82455)
60. FORT MYERS PARTICIPATION = FOUNDER_AUTHORIZED_FOR_LAUNCH, live (record + pin)
61. ROLLBACK REQUIRED = NO
62. CURRENT LIVE DEPLOYMENT = 6ac8d0c021f9d04e6aa82455
63. CURRENT LIVE SOURCE COMMIT = 35a044135578f6bdf824baed92b14291910ac072 (built_from ab616e2e)
64. NEXT-MARKET AUTOMATIC BASE DERIVES = YES
65. NEXT-MARKET BASE = 35a04413 (the deployment-state lineage commit)
66. origin == HEAD = YES
67. tree clean = YES
68. FORT MYERS LIVE = YES

FORT MYERS PRODUCTION DEPLOYMENT = PASS
LIVE MARKETS = 46
LIVE PROFILES = 4430
LIVE SERVED ROUTES = 4948
FORT MYERS PROFILES LIVE = 57
FORT MYERS ROUTES LIVE = 63
WRONG-CITY FORT MYERS IDENTITIES LIVE = 0
NAPLES PROFILES ADMITTED LIVE = 0
NONOPERATING PROFILES PUBLISHED = 0
PET-FRIENDLY RECORDS WITH EXPLICIT REFUSAL = 0
QUESTION-ONLY PET-FRIENDLY RECORDS = 0
SERVICE-ANIMAL-ONLY ACCEPTANCE = 0
UNAPPROVED FORT MYERS PROFILES LIVE = 0
MISLEADING SINGLE FEES = 0
INVALID ROUTE SCHEMES = 0
PRIOR MARKETS LOST = 0
PRIOR ROUTES LOST = 0
ROLLBACK REQUIRED = NO
FORT MYERS LIVE = YES

STOP.
