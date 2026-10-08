# PTF-SALT-LAKE-CITY-UT-PRODUCTION-DEPLOYMENT-004 — FINAL

**Status: SALT LAKE CITY IS LIVE.** Salt Lake City / Park City / Wasatch Front, Utah is production market #45.

- **What was deployed:** the exact founder-authorized candidate `C:\t\slc4a\site`. Nothing was rebuilt, resealed,
  re-registered or re-acquired.
- **The deploy:** `netlify deploy --prod --no-build`, run **once**, as deploy **`6ac6f3d213d002249f9c3e67`**.
- **Verification:** every host check passed, so rollback was not required.

**Branch:** `worker/ptf-salt-lake-city-ut-market-001` (worktree `C:\Atlas-Salt-Lake-City-UT-Hardened-V1`).

**Commits:**
- `3d812f28` — the deployment state: authorization consumed, deployment record, live manifest, supersessions, pin,
  predeploy and live-verification reports, and the market-local deploy module. This is the new **live lineage
  commit**.
- the final commit — this report.

## 1. Predeploy parent (Phase 1)

Re-resolved immediately before the deploy with the canonical resolver, Netlify `getSite` and a hash of the served
sitemap, at 01:21:06Z (2026-10-08); predeploy PASS written 01:35:18Z. Re-checked straight after the live manifest was written, right before the
call: still `6ac5ba3b`, state ready, sitemap `beb98d7a…`.

| | |
|---|---|
| PREDEPLOY LIVE SOURCE COMMIT | `90624cd8392d6283e38834ddafa314423eba0ea8` (built_from `4c7e7b90`) |
| PREDEPLOY LIVE DEPLOYMENT | **`6ac5ba3bcda3a604f7e467e0`** (New Orleans; host `published_deploy` = this id, state ready) |
| PREDEPLOY LIVE BUNDLE | `af70e0aa8a64496e53c67750668c33029cbda3cf318d9d3ecb1198af346a0a41` |
| PREDEPLOY LIVE SITEMAP | `beb98d7a9f4687c337dfcbd5eaa1d301ac7d74eecddba5dcebf7d7b05c2a8508` — the served sitemap hashed to it and is byte-identical to the live artifact `C:/t/nola4a`; saved as the parent route set (4,740 locs) |
| PREDEPLOY LIVE MARKETS / PROFILES | 44 / 4,240 |
| PREDEPLOY LIVE RELEASE-INDEX / SERVED ROUTES | 4,663 / 4,740 |
| HOST VERIFIED | YES |

## 2. Authorization and candidate integrity (Phases 2–11)

`salt_lake_city_ut_deployment_004.py predeploy` (`markets/reports/salt_lake_city_ut_predeploy_004.json`): **PASS**.
Every value below was read mechanically from the authorization record and the founder-authorization accounting; none
was taken from the recap.

| | |
|---|---|
| DEPLOYMENT AUTHORIZATION | `ptf-auth-salt-lake-city-003-2738162fe62b` — before: **AUTHORIZED**, CONSUMED NO, DEPLOY_ID NONE, market salt-lake-city-ut |
| AUTHORIZED PACKAGE / DIGEST | `pkg-salt-lake-city-ut-6d474d2906ae01e0` / `sha256:6d474d2906ae01e062dc5ef6158b3e167e244e5c780e2ab8478eb8ec36e0100d` |
| AUTHORIZED SOURCE / DECISION COMMIT | `6959e985dae864e5f3e276d81337be3ea3410d37` (the founder-decision BUILD commit) |
| AUTHORIZED BUNDLE | `2738162fe62b5a5395c266c54d701e8d23b45da28ea02c6b1c47eebb3760df12` |
| AUTHORIZED SITEMAP | `3806de5e5093cd63f570ab60f83a76f29712b9a9158cb6bfe2dce8f51eb89dc9` |
| AUTHORIZED PARENT = ROLLBACK TARGET | `6ac5ba3bcda3a604f7e467e0` = the exact current production deployment |
| checks | `verify_authorization []`, `deployability_problems []`, `verify_target []` (pettripfinder-prod / pettripfinder.com) |
| candidate on disk | `verify_bundle_directory []`: all **26,378** files re-hashed from `C:\t\slc4a\site` equal the authorization. AUTHORIZED BUNDLE MATCH **PASS**, AUTHORIZED SITEMAP MATCH **PASS**. The committed candidate manifest still describes the bundle on disk |
| candidate accounting | 45 markets / 4,373 profiles / **4,807** release-index routes / **4,885** served routes. Salt Lake City 133 profiles / **144** release-index routes / 145 served routes. File count 26,378 = the founder-authorization record |
| determinism | BYTE_IDENTICAL (26,378 files compared between the two sequential builds, 0 differing) |
| delta | 798 files added, all Salt Lake City's; 0 removed; only `sitemap.xml` changed; 0 prior-market files changed. PRIOR MARKETS / PROFILES / INDEX ROUTES / SERVED ROUTES LOST 0; UNEXPECTED MARKET / PROFILE / ROUTE DELTA `[]` |
| held / resort / reader / fee / collision (accounting) | unapproved 0; 47 held 0 published; 29 no-pets 0 profiles; timeshare 0/19, private condo-residence-rental 0/172, military 0/4; Park City pages 16, labelled SLC 0; reader 0/0/0; fees 21 / 39 / 13, 21 exact on the page, 0 withheld rendered; collisions 0 / 0 / 0 |
| FAST receipt | `pkg-salt-lake-city-ut-6d474d2906ae01e0-7f8811ce601d32c4` currently eligible and the only receipt selected. RULE J NONEMPTY PASS: 819 files / 803 HTML, bundle `42035f18…`. RULE K NONVACUOUS PASS: BYTE_IDENTICAL. 0 defects |

## 3. Live manifest and the deploy (Phases 12–13)

- **Live manifest:** `write-manifest --write` wrote `deploy/netlify/global_deployment_manifest.json` from the exact
  authorized bytes. It carries bundle `2738162f…`, sitemap `3806de5e…`, 45 markets, 4,373 profiles and 4,885 routes,
  and is equal to the committed candidate manifest; `verify_manifest []`. No candidate byte was altered.
- **The deploy, run ONCE:**
  `netlify deploy --prod --no-build --dir C:\t\slc4a\site --site pettripfinder-prod`

| | |
|---|---|
| DEPLOY START | 2026-10-08T01:36:54Z |
| DEPLOY COMPLETE | 2026-10-08T01:38:03Z (host `published_at` 01:38:03.671Z) |
| NETLIFY DEPLOYMENT ID | **`6ac6f3d213d002249f9c3e67`** |
| EXIT STATUS | 0 |

## 4. Host verification (Phases 14–19)

`verify-live` (`markets/reports/salt_lake_city_ut_live_verification_004.json`): **ALL LIVE CHECKS PASS — 21 / 21**.

| | |
|---|---|
| host | publishes `6ac6f3d213d002249f9c3e67`, state ready, context production; **previous deploy `6ac5ba3bcda3a604f7e467e0`** (the New Orleans parent) |
| HOST SITEMAP MATCH | **PASS** — the served `sitemap.xml` hashes to `3806de5e…` and is byte-identical to `C:\t\slc4a\site\sitemap.xml`; the served route SET is identical to the authorized candidate's |
| LIVE ACCOUNTING | **45 markets / 4,373 profiles / 4,807 release-index routes / 4,885 served routes**. Confirmed again by the canonical live index after the record: Salt Lake City participating, 133 profiles, 144 index routes |
| SALT LAKE CITY ROUTES | the expected served-route set was derived from the authorized candidate's own sitemap (145 routes: hub, policy comparison, 10 corridors, 133 profiles). Swept: **145 / 145 HTTP 200**, 0 missing, 0 no-response |
| BYTE IDENTITY | **all 133 live profiles** fetched whole and byte-identical to the artifact, plus **32 / 32** further sampled pages (see below). MISMATCHES **0** |
| PRIOR PRODUCTION | all **4,740** parent served routes re-fetched: 12 detached sequential batches of 400 (atomic rename per batch, 01:38:58 → 01:41:43Z); **4,740 / 4,740 HTTP 200**; first-pass no-response 0, so no recheck was needed. Prior markets / profiles / routes lost 0 / 0 / 0 |
| spot hubs | New Orleans, Kansas City, Minneapolis, Portland, Seattle, San Antonio, Austin, Phoenix, Denver, San Diego, Jacksonville FL, West Palm Beach, Fort Lauderdale, Augusta, Miami, Tampa and Orlando **200**; Salt Lake City hub **200**; **Detroit 404** (still withheld) |
| bundle quality | broken links 0, collisions 0, global shadowing 0, canonical violations 0 |

**Byte samples (Phase 16):**
- **Every one of the 133 live profiles is byte-identical** to the artifact, so every area is covered:
  - Downtown Salt Lake City and the SLC Airport / West Side corridor (Salt Lake City 51, West Valley City 16);
  - Murray 6, Midvale 8, Sandy 7;
  - South Jordan 4, Draper 4;
  - Park City 16, including the Deer Valley and Canyons / Kimball Junction profiles.
- **The 32 further sampled pages:** the apex, the category root, robots.txt, llms.txt, the Salt Lake City hub, its
  policy comparison, 3 corridors, 6 profiles and 17 other markets' hubs. **SAMPLED PAGES 165, BYTE IDENTICAL 165,
  MISMATCHES 0.**

**Held rows, live (Phase 17):**
- **The 76 unpublished census rows** are probed at the census slug and at the route the site forms (87 URLs): **all 404**.
  - They are the 47 held rows (AWAITING_POLICY_OBSERVATION 21, ACCESS_BLOCKED 16, AWAITING_OFFICIAL_URL 9,
    AWAITING_ROUTING_REPLACEMENT 1) and the 29 VERIFIED_NO_PETS rows.
  - The founder's named rows each 404: **Hyatt Place Cottonwood**, **Hyatt Place Lehi**, **Grand Summit / Silverado /
    Sundial at Canyons Village** and **The Ascent**.
  - The 29 verified-no-pets hotels are not profiles.
- **Identities outside hotel inventory:** **19** timeshare, **172** private condo / residence / rental and **4**
  military-restricted. All 195 return 404 and none is in the served sitemap; **0** published.

**Municipality and Park City (Phases 7, 18):**
- All **133** live profiles state UT, the municipality the census carries and that row's own ZIP; **0 wrong**.
- By county: Salt Lake 106, Summit 16, Utah 8, Davis 3. By municipality: Salt Lake City 51, Park City 16, West Valley
  City 16, Lehi 8, Midvale 8, Sandy 7, Murray 6, Draper 4, South Jordan 4, Cottonwood Heights 3, West Jordan 3, Woods
  Cross 3, Holladay 2, Bluffdale 1, Herriman 1.
- **PARK CITY PROFILES LIVE 16**; all 16 state Park City, UT and their own ZIP. **PARK CITY PROFILES LABELED SALT
  LAKE CITY LIVE = 0.**
- The municipality traps are live exactly as committed:
  - Grand Hyatt Deer Valley and Canopy by Hilton Deer Valley (84060) → Park City.
  - Holiday Inn Express Park City and Hyatt Centric Park City (84098) → Park City.
  - Fairfield Cottonwood (84121) → Holladay; MainStay Fort Union (84121) → Cottonwood Heights.
  - Fairfield SLC South (84123, Murray) → unpublished, 404.

**Reader and fees (Phases 8–9):**
- **Reader:** explicit-refusal PF 0, question-only PF 0, service-animal-only 0. The shared reader is unchanged.
- **Fees:** SAFE SINGLE-BASIS FEES 21, and each of the 21 live pages renders exactly its authorized amount.
- **Withheld fees 52** (tiered 39, unsafe / other 13): none appears, and none of the 112 fee-less profiles shows a fee.
  MISLEADING SINGLE FEES **0**.

**Collisions (Phase 10):** CROSS-MARKET 0, BARE-CHAIN 0, DUPLICATE EXCLUDED IDENTITIES 0.

## 5. Bounded postdeploy checks (Phase 20)

No broad regression was run.

| | |
|---|---|
| pin and reader tests | `contracts/test_market_state_pins.py` + `test_question_negation_reader_001.py`: **332 / 332 passed** (9.6 s; one pytest process; run on the finalized state) |
| release contracts | `verify_all()` **46 / 46** clean |
| global authority | `build_global_authority --check`: all generated artifacts match the shards (1,886 exclusions, 4,522 seed rows) |
| FAST receipt | currently eligible; RULE J NONEMPTY PASS (819 / 803); RULE K NONVACUOUS PASS (BYTE_IDENTICAL) |
| quality | BROKEN LINKS 0, COLLISIONS 0, CANONICAL VIOLATIONS 0, GLOBAL SHADOWING 0, UNEXPECTED DELTA `[]` |

## 6. Deployment state finalized (Phase 21)

These were written only after all 145 Salt Lake City routes, all 4,740 parent routes, the host verification and the
held-row production checks had passed.

| | |
|---|---|
| authorization | `ptf-auth-salt-lake-city-003-2738162fe62b` **AUTHORIZED → DEPLOYED**; **CONSUMED = YES** (status history: deployment `6ac6f3d2…`, consumed by this order, record id below). Same canonical shape as New Orleans' consumed authorization |
| deployment record | `deploy/netlify/deployment_records/ptf-deploy-salt-lake-city-004-6ac6f3d213d002249f9c3e67.json`. `work_order` = the AUTHORIZING order (003); `deployer.work_order` = this order (004); previous deployment `6ac5ba3b…`; `verify_record []` |
| supersessions | `ptf-auth-new-orleans-003-af70e0aa8a64` marked Historical (0 contracts moved); `ptf-auth-salt-lake-city-003-2738162fe62b` is the new CURRENT entry with an empty moved list |
| live pin | `tests/pettripfinder/pins/deployment_state.json` → deploy `6ac6f3d2…`, source commit `6959e985`, 45 markets / 4,373 / 4,885; live = source |
| rollback target | `6ac5ba3bcda3a604f7e467e0` (New Orleans, 44 markets) |
| participation | salt-lake-city-ut stays `FOUNDER_AUTHORIZED_FOR_LAUNCH`, the state every live market carries; New Orleans reads the same. Liveness is held by the deployment record and the pin. `decision_problems []` |

## 7. Rollback (Phase 22)

**ROLLBACK REQUIRED = NO.** There was no authorized-byte mismatch, sitemap mismatch, route loss, profile loss,
held-profile publication, Park City corruption, reader contradiction, fee corruption, collision, canonical violation
or accounting mismatch. Exactly one Salt Lake City deployment was made.

## 8. Final accounting and next-market base (Phases 23–24)

| | |
|---|---|
| LIVE MARKETS | **45** |
| LIVE PROFILES | **4,373** |
| LIVE RELEASE-INDEX ROUTES | **4,807** (= authorized candidate) |
| LIVE SERVED ROUTES | **4,885** (= authorized candidate) |
| SALT LAKE CITY PROFILES / RELEASE-INDEX / SERVED ROUTES LIVE | **133 / 144 / 145** |
| PRIOR MARKETS PRESERVED | 44 / 44; prior profiles lost 0; prior routes lost 0 |
| CURRENT LIVE DEPLOYMENT | `6ac6f3d213d002249f9c3e67` |
| CURRENT LIVE SOURCE COMMIT | `3d812f28de52555b15adaa5f9a19049cd064ed32` (live lineage commit; built_from `6959e985`); resolver RESOLVED, host verified, problems `[]` |
| NEXT-MARKET AUTOMATIC BASE DERIVES | **YES** — `derive_registration_base(market, 3d812f28…)` → base **`3d812f28`** (0 factory commits since live). From the final report commit it derives to that commit, which adds only this report |

All processes created by this order have ended: predeploy, the two route sweeps (the parent sweep PID 12668 exited on
its own) and verify-live. The pre-existing python process (PID 14180) was not touched.

## FINAL ANSWERS

1. PREDEPLOY LIVE DEPLOYMENT = 6ac5ba3bcda3a604f7e467e0
2. PREDEPLOY LIVE SOURCE COMMIT = 90624cd8392d6283e38834ddafa314423eba0ea8
3. DEPLOYMENT AUTHORIZATION = ptf-auth-salt-lake-city-003-2738162fe62b
4. AUTHORIZATION STATUS BEFORE = AUTHORIZED (unconsumed, no deploy id)
5. AUTHORIZED PACKAGE = pkg-salt-lake-city-ut-6d474d2906ae01e0
6. AUTHORIZED CANDIDATE BUNDLE = 2738162fe62b5a5395c266c54d701e8d23b45da28ea02c6b1c47eebb3760df12
7. AUTHORIZED CANDIDATE SITEMAP = 3806de5e5093cd63f570ab60f83a76f29712b9a9158cb6bfe2dce8f51eb89dc9
8. CANDIDATE FILE COUNT = 26,378
9. CANDIDATE INTEGRITY = PASS (all 26,378 files re-hashed equal to the authorization)
10. NETLIFY DEPLOYMENT ID = 6ac6f3d213d002249f9c3e67
11. NETLIFY RESULT = SUCCESS (exit 0, state ready, production)
12. HOST SITEMAP MATCH = PASS
13. LIVE MARKETS = 45
14. LIVE PROFILES = 4,373
15. LIVE RELEASE-INDEX ROUTES = 4,807
16. LIVE SERVED ROUTES = 4,885
17. SALT LAKE CITY PROFILES LIVE = 133
18. SALT LAKE CITY RELEASE-INDEX ROUTES = 144
19. SALT LAKE CITY SERVED ROUTES = 145
20. SALT LAKE CITY ROUTES HTTP 200 = 145 / 145
21. SAMPLED PAGES BYTE IDENTICAL = 165 / 165 (all 133 profiles + 32 sampled pages)
22. PARK CITY PROFILES LIVE = 16
23. PARK CITY PROFILES LABELED SALT LAKE CITY LIVE = 0
24. HYATT PLACE COTTONWOOD PUBLISHED = 0
25. HYATT PLACE LEHI PUBLISHED = 0
26. VAIL CANYONS HELD ROWS PUBLISHED = 0 / 3
27. THE ASCENT PUBLISHED = 0
28. VERIFIED NO-PETS PROFILES PUBLISHED = 0 / 29
29. TIMESHARE PROFILES PUBLISHED = 0 / 19
30. PRIVATE CONDO / RESIDENCE / RENTAL PROFILES PUBLISHED = 0 / 172
31. MILITARY-RESTRICTED PROFILES PUBLISHED = 0 / 4
32. UNAPPROVED SALT LAKE CITY PROFILES LIVE = 0
33. PET-FRIENDLY WITH EXPLICIT REFUSAL = 0
34. QUESTION-ONLY PET-FRIENDLY = 0
35. SERVICE-ANIMAL-ONLY ACCEPTANCE = 0
36. SAFE SINGLE-BASIS FEES = 21 (21 / 21 rendered exactly live)
37. WITHHELD FEES = 52 (39 tiered + 13 unsafe; 0 rendered)
38. MISLEADING SINGLE FEES = 0
39. PARENT ROUTES CHECKED = 4,740
40. PARENT ROUTES HTTP 200 = 4,740
41. PRIOR MARKETS LOST = 0
42. PRIOR PROFILES LOST = 0
43. PRIOR ROUTES LOST = 0
44. DETROIT STILL WITHHELD = YES (404)
45. RULE J NONEMPTY = PASS (819 files / 803 HTML)
46. RULE K NONVACUOUS = PASS (BYTE_IDENTICAL)
47. FAST RECEIPT ELIGIBLE = YES (pkg-salt-lake-city-ut-6d474d2906ae01e0-7f8811ce601d32c4)
48. BROKEN LINKS = 0
49. COLLISIONS = 0
50. CANONICAL VIOLATIONS = 0
51. GLOBAL SHADOWING = 0
52. UNEXPECTED DELTA = []
53. DEPLOYMENT AUTHORIZATION CONSUMED = YES (AUTHORIZED → DEPLOYED, record ptf-deploy-salt-lake-city-004-6ac6f3d213d002249f9c3e67)
54. SALT LAKE CITY PARTICIPATION = FOUNDER_AUTHORIZED_FOR_LAUNCH (participating in the live release; live per the deployment record and pin)
55. ROLLBACK REQUIRED = NO
56. CURRENT LIVE DEPLOYMENT = 6ac6f3d213d002249f9c3e67
57. CURRENT LIVE SOURCE COMMIT = 3d812f28de52555b15adaa5f9a19049cd064ed32 (built_from 6959e985)
58. NEXT-MARKET AUTOMATIC BASE DERIVES = YES
59. NEXT-MARKET BASE = 3d812f28 (lineage commit; from the final report commit it derives to that commit)
60. origin == HEAD = YES (verified after push)
61. tree clean = YES (verified after push)
62. SALT LAKE CITY LIVE = YES

SALT LAKE CITY PRODUCTION DEPLOYMENT = PASS
LIVE MARKETS = 45
LIVE PROFILES = 4373
LIVE SERVED ROUTES = 4885
SALT LAKE CITY PROFILES LIVE = 133
SALT LAKE CITY ROUTES LIVE = 145
PARK CITY PROFILES LABELED SALT LAKE CITY LIVE = 0
PET-FRIENDLY RECORDS WITH EXPLICIT REFUSAL = 0
QUESTION-ONLY PET-FRIENDLY RECORDS = 0
SERVICE-ANIMAL-ONLY ACCEPTANCE = 0
UNAPPROVED SALT LAKE CITY PROFILES LIVE = 0
MISLEADING SINGLE FEES = 0
PRIOR MARKETS LOST = 0
PRIOR ROUTES LOST = 0
ROLLBACK REQUIRED = NO
SALT LAKE CITY LIVE = YES

STOP.

## For the next order

- **Rollback target** for the next deploy: `6ac6f3d213d002249f9c3e67`. The live artifact is `C:/t/slc4a` (twin
  `C:/t/slc4b`); byte-compare against `C:/t/slc4a`.
- **Next-market base** derives automatically from lineage `3d812f28`.
- **Held rows to revisit only by a founder ruling or new evidence:** Hyatt Place Cottonwood (4th-floor refusal),
  Hyatt Place Lehi (ZIP 84048 vs 84043), the Vail Canyons Village rows (server-error pages) and The Ascent
  (preopening).
