# PTF-GREENVILLE-NC-FOUNDER-AUTHORIZATION-AND-LIVE-LAUNCH-003 — FINAL

**GREENVILLE LIVE = YES.** Deployed as 6aa75f87aebd8377ccd67304 and published at 2026-09-14T02:44:32Z. Production is now 20 markets / 1229 profiles / 1449 routes.

## Parent (re-read at 02:38Z, and again immediately before deploy)

| field | value |
|---|---|
| host deployment | 6aa750d8fa36419d3c84ecbc (ready) |
| release digest | e6c669cf14980efc44eaee4799e060e28888cac510498310595fcd125939f965 |
| source commit | c4db424ba6b4351158708889c803643be9edc2a3 |
| sitemap | 3cb2fc6d20d6fda185345d8d25b30e5489099959b48c516dfa6ae79668b9a99f |
| markets / profiles / routes | 19 / 1221 / 1438 |
| rollback target of the parent | 6aa60a3e018fd6b1b9a40450 |
| STALE_PARENT | NO |
| status | VERIFIED |

## Authorized and deployed

All digests below were read from `greenville_nc_founder_authorization_packet_002.json` and re-verified against the package, receipt and artifact files.

| field | value |
|---|---|
| authorization | ptf-auth-greenville-003-5009281dac4e (AUTHORIZED, then DEPLOYED), greenville-nc only |
| package | sha256:f2113468ddfb4b0622164d854f18e29118126e26c9014d498d4f64aec83a476c |
| build input key | sha256:2f8e4d18c2f34a87e508f14d190e0dccbf9371016da274c87010d8cf48e385d2 |
| intended delta | sha256:05f353e06f0977f8b702e86165a17d34ef099f04ccf717c231cd24a679a4258b |
| validation receipt | sha256:db6453c5fac75a0bc091d0c84216d5480e675e08e7a4246b34a9f613caad0d6d |
| candidate = deployment artifact | 5009281dac4e2289563aeed8efcd40568311994781794894cef41e6fe872b7be |
| sitemap | 00163f47164155a4886c9d3fcecd0c2af7b80f61e704731ddd17783dfe2b262f |

**Delta:**
- +1 market and +8 profiles.
- +11 sitemap routes against +10 release-index routes. The extra sitemap route is `/pet-friendly-hotels/greenville-nc/policy-comparison/`.
- Nothing removed, and 0 unexpected changes.

**How it went out:**
- The participation flip reproduced the composed bytes (8618cd0e2bb003a6a05868ff6d1c59cc6ca0f8c9b549efcb4e9ca921ed875dfd).
- The gate was opened for greenville-nc only. Jacksonville, Detroit, Atlanta, Fayetteville, Asheville and an unnamed market were all refused while it was open.
- The staged artifact at `C:\t\gvl2a\site` re-hashed to the authorized digest. It was deployed with no build, reassembly or re-seal.

## Live verification

27/27 critical checks PASS:
- All 1449 live routes return 200. The live sitemap equals the artifact's.
- Greenville has 11 routes and 8 profiles. Its hub, corridor page and policy-comparison page all return 200.
- Downtown (Hilton Garden Inn, Red Roof), the medical district (Candlewood, Homewood, Residence Inn) and the convention corridor (Hampton, Holiday Inn) return 200.
- PGV check: no PGV-area profile is published, so it passes as not applicable.
- Every previously live market keeps its route count and fragment routes, including Fayetteville, Asheville, Wilmington, Triad, Charlotte, Raleigh, Nashville, Lexington and Toledo.
- Jacksonville, Atlanta, Outer Banks, Boone, Pinehurst and Detroit hubs return 404.

**Rollback target:** 6aa750d8fa36419d3c84ecbc / e6c669cf14980efc44eaee4799e060e28888cac510498310595fcd125939f965, the Fayetteville-live release Greenville replaced. No rollback was needed.

**Canonical record:** `ptf-deploy-greenville-003-6aa75f87aebd8377ccd67304`. The deployment-state pin was moved. The receipt is `greenville_nc_live_verification_003.json`. The gate is closed and the entry consumed.

## Performance

| step | time |
|---|---|
| registration to AUTHORIZATION_READY | 2 min 26 s |
| founder authorization processing | 159.0 s |
| final parent check | 4.4 s |
| final byte check | 3.6 s |
| host deployment | 36.3 s |
| live verification | 32.8 s |
| **authorization to verified live** | **8 min 35 s** |

Broad regressions: 0 local, 0 remote. Unchanged live markets rebuilt: 0. Factory code changed: NO.
