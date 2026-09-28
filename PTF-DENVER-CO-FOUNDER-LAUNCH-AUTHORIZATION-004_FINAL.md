# PTF-DENVER-CO-FOUNDER-LAUNCH-AUTHORIZATION-004 — FINAL

`denver-co` (Denver / Boulder / Front Range, Colorado) is **FOUNDER_AUTHORIZED_FOR_LAUNCH** on
**`pkg-denver-co-07f10db29ab56d98`**, exactly as the founder decided in this conversation:

> AUTHORIZE: pkg-denver-co-07f10db29ab56d98
> DO NOT AUTHORIZE: pkg-denver-co-91b2e0a2

**The candidate.** The exact authorized production candidate is built. Two sequential whole-site assemblies are
byte-identical. It is bound to deployment authorization **`ptf-auth-denver-004-7d3471c79e2d`**, which is **AUTHORIZED
and UNCONSUMED**.

**The refused package.** The superseded 289-profile package `pkg-denver-co-91b2e0a2` is not authorized. Every writer
in this order refuses unless the readiness packet binds `07f10db2`.

**Not deployed.** No Netlify invocation, no deployment record, no LIVE flag, and the authorization is not consumed.
Current live is untouched and the live `global_deployment_manifest.json` was not written. There was no acquisition,
no broad regression, no spend, no Places, no `identity_resolutions.json` write and no ESA display name.

**Work-order id.** The founder's message carried no work-order id. This order records it as
`PTF-DENVER-CO-FOUNDER-LAUNCH-AUTHORIZATION-004`, the next number in Denver's chain (001 → 002 → 003 → 004),
following San Diego's convention.

Commits: `5bc62502` founder decision (committed **before** the whole-site build), then the candidate + authorization +
this report.

---

## 1. Current live (verified at start and end, 06:16Z)

| | |
|---|---|
| CURRENT LIVE | San Diego, deploy `6ab859787d349f8397e1450a`, source `f01587ba` |
| CURRENT LIVE BUNDLE / SITEMAP | `553a858f…` / `4f648fff…` |
| MARKETS / PROFILES / RELEASE-INDEX / SERVED | **35 / 2,666 / 2,969 / 3,037** |
| HOST VERIFIED | true |

The live bytes compared against below are San Diego's authorized artifact `C:\t\sd3a`. Its manifest names the live
bundle `553a858f…` and sitemap `4f648fff…`.

## 2. Registered package (nothing re-derived)

| | |
|---|---|
| PACKAGE | `pkg-denver-co-07f10db29ab56d98` (`sha256:07f10db29ab56d982490df7341831d731c8015e198d9805572730113056c6707`) |
| READINESS | AUTHORIZATION_READY, COMPOSITE_FRESH_MARKET_DATA_ONLY 15/15, FULL_REGRESSION_REQUIRED NO |
| COHORT | 441 census / **288 pet-friendly** / 46 verified no-pets / 107 unresolved / actionable 0 |
| COVERAGE | YES by founder decision (`denver_co_founder_coverage_decision_003.json`) |
| FAST | 15/15; J 1,723 files / 1,707 HTML, bundle `475633a2…`; K BYTE_IDENTICAL |

## 3. Founder authorization (participation)

The decision was written by `denver_co_launch_participation_004.py`, which calls `launch_participation.extend_decision`.
The chain was extended, not rebuilt.

| | |
|---|---|
| denver-co | `SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH` → **`FOUNDER_AUTHORIZED_FOR_LAUNCH`** |
| decided_by / decided_on | `founder` / 2026-09-28 (the founder's own words are transcribed; no person's name is signed) |
| AUTHORIZED SET | 35 → **36**, gained **denver-co only**, lost none |
| OTHER ROWS CHANGED | **0** (37 rows); Detroit stays SOURCE_READY and is excluded |
| DECISION PROBLEMS | `[]`; lineage 40 records; supersedes the 003 decision (`ec030d31…`) |
| FIRST AUTHORIZATION | yes: no `founder_authorization_superseded` entry exists or was written |

**Guards.** Each founder statement is a guard that refuses to write unless committed state agrees:

- **Package:** the bound package is `07f10db2`, never `91b2e0a2`.
- **Cohort:** exactly 288 / 46.
- **Held rows:** each held group matches its count and publishes nothing.
  - 52 no-website: 0 published.
  - 16 founder-decision: 0 published. These are the 7 dual-brand address keys × 2 rows plus 2 ESA title rows.
  - 38 router-exhausted: 0 published.
  - 1 preopening (ECHO Suites Thornton, held by the clean-authority preopening rule): 0 published.
- **Fees:** 0 flattened fees.
- **Status:** ACTIONABLE 0, coverage YES, source ready.

## 4. The exact authorized candidate

`assemble_production_site` ran on the committed tree `5bc62502`:

- build A: `--output C:/t/den4a` (manifests at 05:04Z)
- build B: `--output C:/t/den4b` (manifests at 06:11Z)

| | |
|---|---|
| AUTHORIZED CANDIDATE BUNDLE | **`7d3471c79e2d20d01c69e6dbd134bd3a5caec35e35967958f797decd06ee338a`** |
| AUTHORIZED CANDIDATE SITEMAP | **`5d3d07a4c96563c0147cdca2ad0061ea437fee9748bc5cd3169eefe083712a2c`** |
| total files | 17,904 |
| all gates pass | **true** |
| markets included / excluded | 36 / Detroit |
| PARENT LOOKUP / PARENT ROUTES PRESERVED | **PASS / PASS** (2,969/2,969 index, 3,037/3,037 served) |

| Release-factory accounting | |
|---|---:|
| **UNCHANGED BUNDLES REUSED** | **35** (live index entries carried unchanged) |
| **UNCHANGED MARKETS REBUILT** | **0** |
| **DENVER BUNDLES BUILT** | **1** |
| **PHYSICAL FRAGMENTS RERENDERED** | **36** (reported separately: no release store is populated here, so the composer physically rendered every fragment. This is **not** reuse. Counted from the bundle manifest; the log shows 32 scopes because the terminated process lost unflushed stdout) |

**The known assembler hang was handled as documented.** Each build wrote both manifests and then idled:

- CPU over 10 s: A 0.36 s, B 0.45 s.
- The manifests were hashed twice, 75 s apart, and were stable.
- Only then was the process terminated: A was PID 24484 and B was PID 14236.
- Build B started only after build A was gone.

## 5. Candidate determinism

| | |
|---|---|
| builds | 2, sequential (never concurrent), separate short absolute work dirs |
| bundle / sitemap | `7d3471c7…` = `7d3471c7…` / `5d3d07a4…` = `5d3d07a4…` |
| manifest files | byte-identical (`global_bundle_manifest.json` `59cc1931…`, `file_hash_manifest.json` `37e5e05d…` in both) |
| FILES COMPARED / DIFFERING | **17,904 / 0** |
| RESULT | **BYTE_IDENTICAL** |

## 6. Route accounting (as sets, from the artifacts)

| | live | Denver | candidate |
|---|---:|---:|---:|
| RELEASE-INDEX ROUTES | 2,969 | **+305** (288 hotel + 16 corridor + 1 hub) | **3,274** |
| SERVED SITEMAP ROUTES | 3,037 | **+306** (305 + `/pet-friendly-hotels/denver-co/policy-comparison/`) | **3,343** |
| PROFILES | 2,666 | **+288** | **2,954** |
| MARKETS | 35 | **+1** | **36** |

- **Served-route difference:** candidate minus live is 306 routes added, all Denver's. 0 are foreign and 0 prior
  served routes were lost.
- **Corridors:** 16 publish. The 4 suppressed ones (arvada, brighton-northeast, capitol-hill-uptown,
  south-denver-university) were not forced.

## 7. Publication cohort safety (on the BUILT artifact)

Every held row was resolved to its census slug and checked in `C:/t/den4a` for a profile page, a sitemap route, a
release-index route and a `/go/` file.

| group | rows | slugs resolved | pages | sitemap | index | /go/ |
|---|---:|---:|---:|---:|---:|---:|
| no-website | 52 | 52 | 0 | 0 | 0 | 0 |
| founder-decision (14 dual-brand + 2 ESA) | 16 | 16 | 0 | 0 | 0 | 0 |
| router-exhausted | 38 | 38 | 0 | 0 | 0 | 0 |
| preopening (ECHO Suites Thornton) | 1 | 1 | 0 | 0 | 0 | 0 |
| verified-no-pets (as profiles) | 46 | 46 | 0 | 0 | 0 | 0 |

- **Profiles:** approved Denver profiles in the candidate: **288**. Unapproved: **0**.
- **ECHO Suites:** 0 HTML files anywhere in the 17,904-file candidate mention it.
- `identity_resolutions.json` was not modified.

## 8. Fee, collision and receipt safety

- **Fees.**
  - 80 tiered fees are withheld and 35 unsafe single fees are withheld.
  - 103 published records quote more than one amount, and **0** of them publish a single fee.
  - **Misleading single fees: 0.**
- **Collisions:** Denver names held by another market: 0. Bare-chain names: 0. Duplicate excluded identities across
  the 1,327-row registry: 0.
- **FAST receipt:** `pkg-denver-co-07f10db29ab56d98-d3f8fea6996a6fcb.json` is currently eligible under today's reader.
  - file_count 1,723 and html_count 1,707.
  - Bundle `475633a2…` ≠ `e3b0c442…`.
  - Rules J and K PASS.
  - Augusta's vacuous historical receipt is still ineligible.

## 9. Byte preservation (candidate vs the live bytes)

| | |
|---|---|
| files live → candidate | 16,202 → 17,904 |
| **FILES ADDED** | **1,702**, all under Denver's own `pet-friendly-hotels/denver-co/` and `go/denver-co/` |
| **FILES REMOVED** | **0** |
| **FILES CHANGED** | **1**: `sitemap.xml` (global, regenerated for every release) |
| prior-market files changed / unclassified paths | **0 / 0** |
| UNEXPECTED MARKET / PROFILE / ROUTE DELTA | **`[]` / `[]` / `[]`** (release_diff passed, 0 findings) |

## 10. Deployment authorization

| | |
|---|---|
| DEPLOYMENT AUTHORIZATION ID | **`ptf-auth-denver-004-7d3471c79e2d`** |
| AUTHORIZED BUNDLE / SITEMAP | `7d3471c7…ee338a` / `5d3d07a4…712a2c` |
| AUTHORIZED PARENT / ROLLBACK TARGET | `6ab859787d349f8397e1450a` (San Diego, current live) |
| authorized_by | `founder` (the founder's words are quoted in `authorization_source`) |
| STATUS | **AUTHORIZED, UNCONSUMED** (`deploy_id` null, no deployment record) |
| deployability / verify problems | `[]` / `[]`; the only deployable authorization in the repository |
| candidate manifest | `deploy/netlify/global_deployment_manifest_candidate_denver_004.json`; the live `global_deployment_manifest.json` was **not** written |

It was created only after determinism was proven, and only for the exact candidate bytes.

The writer's "no deployable authorization for this market may already exist" check was repaired locally. The
San Diego module it was cloned from tested a bare market id against a list of market records, so that check could
never fire. Denver's writer reads the ids out of the records.

`markets/reports/denver_co_launch_authorization_004.json` records **ALL_ACCOUNTING_GATES = PASS**.

## 11. Final live safety (06:16Z)

The resolver reports deploy `6ab859787d349f8397e1450a`, 35 / 2,666 / 3,037, host verified. The live sitemap is
**`4f648fff…`**, byte-identical.

| Route | Expected | Actual |
|---|---|---|
| `/pet-friendly-hotels/denver-co/` | 404 | **404** ✅ |
| `/pet-friendly-hotels/denver-co/policy-comparison/` | 404 | **404** ✅ |
| `/pet-friendly-hotels/denver-co/boulder/` | 404 | **404** ✅ |
| San Diego / Jacksonville / West Palm Beach / Fort Lauderdale / Augusta | 200 | **200** ✅ |
| `/pet-friendly-hotels/detroit-ann-arbor-mi/` | 404 | **404** ✅ |

## 12. Cleanup

Both whole-site processes were terminated after their bytes were proven stable. No monitors, watchers or build
processes from this order remain.

`C:/t/den4a` is the authorized artifact the deploying order will ship. `C:/t/den4b` is its determinism twin. Both are
kept on disk outside the repository.

---

## FOR THE DEPLOYING ORDER

1. Consume `ptf-auth-denver-004-7d3471c79e2d`.
2. Deploy bundle `7d3471c7…` from `C:\t\den4a`, with rollback `6ab859787d349f8397e1450a`.
3. Write the live `global_deployment_manifest.json` from those same bytes; verification fails until it does.
4. Extend `supersessions.json`.

Expect 36 / 2,954 / 3,274 / 3,343, with Denver's 306 routes newly returning 200 and every prior route unchanged. The
ECHO Suites Thornton row, every dual-brand and ESA row and every other held row must stay 404.

```
DENVER FOUNDER AUTHORIZATION = PASS (pkg-denver-co-07f10db29ab56d98; pkg-denver-co-91b2e0a2 NOT authorized)
DENVER AUTHORIZED CANDIDATE = PASS (7d3471c7..., BYTE_IDENTICAL 17,904 / 0)
DEPLOYMENT AUTHORIZATION = ptf-auth-denver-004-7d3471c79e2d (AUTHORIZED, UNCONSUMED)
UNAPPROVED DENVER PROFILES = 0
HELD ROWS PUBLISHED = 0 (52 + 16 + 38 + 1 preopening)
MISLEADING SINGLE FEES = 0
UNCHANGED MARKETS REBUILT = 0
CURRENT LIVE MODIFIED = NO
DENVER DEPLOYED = NO
READY FOR DENVER PRODUCTION DEPLOYMENT = YES
```
