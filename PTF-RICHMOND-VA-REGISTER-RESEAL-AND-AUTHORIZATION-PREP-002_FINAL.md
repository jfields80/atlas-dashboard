# PTF-RICHMOND-VA-REGISTER-RESEAL-AND-AUTHORIZATION-PREP-002 — FINAL

Richmond, Virginia (`richmond-va`) registered against CURRENT VERIFIED LIVE, freshly resealed, FAST-validated, composed into a reproducible whole-site candidate, and packaged for founder review.

**STATUS: AWAITING_FOUNDER_AUTHORIZATION.** Nothing deployed.

- Founder packet: `atlas-dashboard/launch_packages/pettripfinder/markets/reports/richmond_va_founder_authorization_packet_002.json`
- Preflight (phases 1–4): `richmond_va_registration_preflight_002.json`
- Classification: `richmond_va_registration_classification_002.json`
- Candidate assembly: `richmond_va_candidate_assembly_002.json`
- Same-address-key rulings: `richmond_va_co_location_003.json`

## Current verified live (parent)

| Field | Value |
|---|---|
| Host deployment | `6aa7f125a91c73ba2363139e` (ready, published 2026-09-14T13:06:20Z) |
| Live release digest | `ef563dfd28d5f37eec959e39fa0ca0a36d51a12199dfdb2bbddd227352ad6cda` |
| Source commit | `67cef35678463e8e641fc056f8c3feb7f19029a2` |
| Sitemap digest | `70f2cfc3c6c0848c3ca34fd79a0b6c66220ca20db61f50a49cbc1acbaeedaccc` |
| Markets / profiles / routes | 23 / 1500 / 1744 |
| Rollback target of the parent | `6aa77cb84f4fd6b6926c5445` |
| Verification | VERIFIED (host = canonical record = live sitemap); rechecked 17:49:47Z and 18:24:58Z, unchanged — STALE_PARENT = NO |

No merge was needed: the branch already descends from the Atlanta-live line (`6825851b`).

## Source inputs and identity rulings

The committed source-ready authority was verified mechanically: 294 discovered / 196 census / 89 PF / 45 no-pets / 134 resolved / 62 unresolved, 12 corridors, 10 publishable. Geography is preserved: the Tri-Cities stay OUTSIDE (37 rows carry the future-market reason in the committed accounting).

Three registration-time rulings were added to `identity_resolutions.json`. Each uses the existing `same_campus_distinct_entity` data contract and each passes `co_located_distinct` (distinct URLs and distinct brand-scoped codes):

| Address key | Identities | Proof |
|---|---|---|
| `12500\|chestnut hill\|23836` | Hampton Inn Richmond Chester (HILTON ptbcshx) + Home2 Suites by Hilton Richmond Chester (HILTON ptbchht) | dual-brand building |
| `1320\|cary\|23219` | Residence Inn by Marriott Richmond Downtown (MARRIOTT ricrt, PF) + Courtyard by Marriott Richmond Downtown (MARRIOTT ricrl, no-pets) | dual-brand building |
| `107\|carter\|23005` | Quality Inn & Suites Ashland (CHOICE va550, 107 N. Carter Road, PF) + Holiday Inn Express & Suites Richmond North Ashland (IHG avava, 107 South Carter Road, no-pets) | opposite directionals; the address key drops them |

The rulings released 4 held PF records. Nothing merged, no name or phone key was used, and no factory code changed.

**Registered authority: census 196 / PF 93 / no-pets 45 / resolved 138 / unresolved 58.**

Holds: IDENTITY 21, ROUTING 26, ACCESS_BLOCKED 7, EVIDENCE 25, GEOGRAPHY 0, PAID 0, FOUNDER 0, CLOSED 19, OUTSIDE 70, NON_HOTEL 7.

## Stale shadow packages

- `pkg-richmond-va-68a86efaa588c103` (SHADOW_UNTIL_REGISTERED, staging only) is not production-selectable. It is absent from `markets/packages/` and `markets/receipts/`, and no authorization names it. Its parent is still current, so FAST rule N would not refuse it; the zone and the store refuse it instead.
- The superseded seal `pkg-richmond-va-9dd5d52ed75b07ec` exists only in git history.

## Registration (Regression V2)

| Check | Result |
|---|---|
| CHANGE_CLASS | **COMPOSITE_FRESH_MARKET_DATA_ONLY** (mechanically selected) |
| Changed paths | 82 = 23 market-local + 14 registration + 45 derived + 0 shared; **UNKNOWN 0** |
| Proofs | 15/15 PASS (change_set, market_local_zone, discovery_config, registration_input, identity_resolutions, participation, release_contract, build_closure, derived_globals, sealed_package, fast_receipt, expected_release, identity_routes, market_state_pin, release_integrity) |
| FULL_REGRESSION_REQUIRED | NO |
| Broad regression | local requested 0, local run 0, remote required 0 |
| Unchanged markets rebuilt | 0 |
| REGISTRATION_TO_AUTH_READY | **4 min 9 s** (17:45:08Z first write → 17:49:17Z AUTHORIZATION_READY) |

## Final package

| Field | Value |
|---|---|
| Package | `pkg-richmond-va-6099825066ea85de` |
| Package digest | `sha256:6099825066ea85de989f2653fa5a09e75f0370122f96bd3548f0d1d267507f98` |
| Build input key | `sha256:e0e17c412cb6cf41ac32fd8efa0d65cdbc5d6cbd5dcc92fd5ba194e8399d7a99` |
| Intended delta digest | `sha256:56f33adec2591d2a45af985002dfd66096e8cd556d5c7d3d0f4157b0c2db4b4e` |
| Validation receipt digest | `sha256:abffe0996720ae0db52c4340d94f7a0dac464d9082cf3d82298c7ba1ab9743ff` |
| FAST | 15/15 PASS, 0 unknown, 0 failed (78.9 s) |
| Reproducible | YES (in-lane twice; clean checkout at `76fce8ac` reseals to the same digest ×2) |

## Candidate

| Field | Value |
|---|---|
| Final candidate digest | `a81020258571f09d93eea746d3d5d195a12d87aa0ce8d98106a997466a96443d` |
| Deployment artifact digest | `a81020258571f09d93eea746d3d5d195a12d87aa0ce8d98106a997466a96443d` |
| Candidate sitemap digest | `b86f414c6233d84557568ee854754103d675f09b593e149d6107facbb7f95790` |
| Expected candidate release-index digest | `sha256:af474f5856e6d50b122304391fea1515309a3328bc82b3dd2ab7860a3d8c57ae` |
| Builds | `C:\t\rva2a` and `C:\t\rva2b`, byte-identical, rc 0/0, 1753 s in parallel; parent artifact `C:\t\at2a` rehashes to the live digest |

| Release diff | Parent | Candidate |
|---|---|---|
| Markets / profiles / sitemap routes | 23 / 1500 / 1744 | **24 / 1593 / 1849** |

- Richmond added: +93 profiles, +105 sitemap routes, +104 release-index routes. The one-route difference is the policy-comparison page.
- Removed: 0 markets, 0 profiles, 0 routes.
- Unexpected market / profile / route / file changes: 0 / 0 / 0 / 0. The only changed live file is `sitemap.xml`.
- Every live market's profile count is identical. No queued market participates (outer-banks-nc, charleston-sc, savannah-ga, pinehurst, hickory, banner-elk, detroit).

## Rollback

Rollback deployment `6aa7f125a91c73ba2363139e`, rollback release digest `ef563dfd28d5f37eec959e39fa0ca0a36d51a12199dfdb2bbddd227352ad6cda`.

## Not done, by design

No founder authorization, no production gate, no deploy, no factory code change, no broad regression.
