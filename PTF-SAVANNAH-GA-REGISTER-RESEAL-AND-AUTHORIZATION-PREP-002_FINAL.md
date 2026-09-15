# PTF-SAVANNAH-GA-REGISTER-RESEAL-AND-AUTHORIZATION-PREP-002 — FINAL

Status: **AWAITING_FOUNDER_AUTHORIZATION**. Nothing deployed, no deployment authorization created, production gate not activated.

Founder packet: `atlas-dashboard/launch_packages/pettripfinder/markets/reports/savannah_ga_founder_authorization_packet_002.json`

## Current verified live parent (re-read 2026-09-15T03:34:47Z, immediately before the packet)
- Host deployment: `6aa8992493a75f80cd0e3887` (ready), record `ptf-deploy-outer-banks-004-6aa8992493a75f80cd0e3887.json`
- Release digest: `a12830db2fa6002816e42aeae39eee557ae68a5ee402c023736271da3867599e`
- Source commit: `e74548ade3d9d116a7a5d2f21d6b814a37c3cadc`
- Sitemap: `120cf33dca357620f1fcc8ba54f4c03ed8798608880ae9f7ddc02180cbbc6261`
- 26 markets / 1703 profiles / 1972 routes; rollback target of the parent `6aa8625938b7e0e0d66e6912`
- Release index digest (post-registration): `sha256:92cd406c9fdcae0856f60a4b80e893858ff4466398da73ecc208dbe708c63fb4`
- VERIFIED; STALE_PARENT = NO (unchanged across 02:00:47Z, 02:11:53Z, 03:34:47Z)

## Savannah registered authority
- Census 187 / pet-friendly 99 / verified no-pets 40 / resolved 139 / unresolved 48 (source-ready 96 / 40 / 136 / 51)
- Same-campus DATA rulings (identity_resolutions.json, `same_campus_distinct_entity`, co_located_distinct = DISTINCT, no merge, no code/schema change):
  - 190 Pioneer Way 31324 — Courtyard by Marriott Richmond Hill (MARRIOTT savrc) + Residence Inn by Marriott Richmond Hill (MARRIOTT savrr)
  - 100 Half Moon Way 31322 — TownePlace Suites Savannah Pooler (savtp, PF) + Fairfield Inn & Suites Savannah Pooler (savfp, verified no-pets)
  - Effect: +3 pet-friendly profiles; no-pets unchanged
- Street-directional collisions — ALL HELD (founder order; no shared normalization/publishing/identity change, no ruling row):
  - 201 E. Bay St. (Hampton Inn Savannah Historic District, savdthx) vs 201 West Bay Street (Hotel Indigo Savannah Historic District)
  - 11 Gateway Blvd East (Holiday Inn Savannah S - I-95 Gateway) vs 11 West Gateway Blvd (TownePlace Suites Savannah South)
  - None of the four appears in the package or the candidate site
- Holds: IDENTITY 27, ROUTING 8, ACCESS 4, EVIDENCE 36, GEOGRAPHY 0, PAID 0, FOUNDER 0, CLOSED 26, OUTSIDE 49 (Tybee 27), NON_HOTEL 28
- Geography: 10 corridors, 8 publish (Historic District, Midtown, Southside, SAV Airport / Garden City, Pooler, Gateway / I-95, Port Wentworth, Richmond Hill). Tybee Island 31328 OUTSIDE (future tybee-island-ga). No Tybee path in the candidate.

## Sealed package
- `pkg-savannah-ga-f05133ff84354b83`, digest `sha256:f05133ff84354b837c951ec19e50730242055a72b45e365d3386de5fec005f6b`, sealed_at 2026-09-15T02:06:40Z, source e0a7f5b3
- Build input key `sha256:bf3ef9e10738207455884f34170e0c6f14ab2067828e91d42b6e3f088f867564`
- Intended delta `sha256:720d279086010a4d8902cf9d03af1c4bb40ffa808f2cf2807789304808787035`
- FAST receipt `sha256:0e0b363c345a22d5b37b1b21d0bcebdad8e870d4e966bf13d1ad391e6a897dbb` — 15/15 PASS, 0 unknown, 0 failed
- Reproducible; clean-checkout reseal (9b06fa46) = same digest ×2; all 7 inputs LF and equal to blobs
- Stale shadow `pkg-savannah-ga-b3497309a1a2729e` stays SHADOW_UNTIL_REGISTERED, non-production, non-selectable, unauthorized

## Classification (Regression V2, base cf6cdded)
- COMPOSITE_FRESH_MARKET_DATA_ONLY, 83/83 paths (23 market-local, 14 registration, 46 derived, 0 shared, 0 unknown), 15/15 proofs PASS
- LOCAL BROAD REQUESTED 0 / RUN 0 / REMOTE BROAD REQUIRED 0 / UNCHANGED MARKETS REBUILT 0

## Candidate
- Builds a/b (C:\t\sav2a, C:\t\sav2b, commit 9b06fa46): byte-identical, `4acb4f16824da6e46b01d86359bf4de0ee8ce3aa005b3d676d42c9560de203ed`
- Deployment artifact digest (rehash) = same; sitemap `c890e6316581e6272e49a94688e6456b4e9d884c2e36e8fcd41a3aff436b8cb2`
- 27 markets / 1802 profiles / 2081 sitemap routes; 11003 files; gates pass; 0 broken links, 0 collisions, 0 canonical violations
- Delta vs live artifact C:\t\obx3a (rehash matches live record): +1 market, +99 profiles, +109 sitemap routes (+108 release-index routes; the difference is the policy-comparison page), 0 removed, 0 routes outside Savannah, only `sitemap.xml` changed among existing files, UNEXPECTED FILE CHANGES 0
- Every live market's profile count identical; columbia-sc, hampton-roads-va, pinehurst (both ids), hickory-nc, banner-elk-nc, detroit-ann-arbor-mi non-participating

## Timings
- Registration first write 02:05:03Z → AUTHORIZATION_READY 02:11:04Z (6 min 1 s); FAST 130.8 s; classify 52 s; candidate builds 2165 s parallel

## Factory
- FACTORY CODE CHANGED = NO (0 shared script/test/engine paths vs cf6cdded besides the lane-owned market_state pin)
- FACTORY STATUS = RESUME_MARKET_PRODUCTION
