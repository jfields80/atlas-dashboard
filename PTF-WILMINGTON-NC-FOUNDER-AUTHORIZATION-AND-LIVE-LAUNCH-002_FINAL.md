# PTF-WILMINGTON-NC-FOUNDER-AUTHORIZATION-AND-LIVE-LAUNCH-002 — final report

**Wilmington is LIVE.** It is the 17th market, deployed as `6aa5e2623de160fcdf416577`.

- The founder authorized exactly the committed candidate, for `wilmington-nc` only.
- The deployed bytes are the staged artifact `C:\t\wil1a\site`. Nothing was built, reassembled, re-sealed or regenerated after authorization.
- No factory, classifier, assembler or shared test changed.

## Parent (Phase 1, re-read again at Phase 6)

| | |
|---|---|
| Host deployment | `6aa5ce23d51fa8544146ebac` (ready) |
| Live release digest | `5d6ced6ed2630d899595cef7d6c2e82dd43cfc15b56e2b48f22f0960afd4f225` |
| Source commit | `9158e1b0d23a037292f05e6d74d63219c81f584f` |
| Sitemap | `aa857f2a275cd58ba1cbc6d9b124165abf4ca52876d20c78ae1e1fae0d83b0c0` |
| Markets / profiles / routes | 16 / 1125 / 1327 |
| Rollback target | `6aa5ad211250a04bc0bc6f7f` |
| Release index problems | 0 |
| Result | STALE_PARENT = NO, VERIFIED |

## Authorization inputs

Every digest was read from `wilmington_nc_founder_authorization_packet_001.json` at `0ecab445`.

| | |
|---|---|
| Parent release | `5d6ced6ed2630d899595cef7d6c2e82dd43cfc15b56e2b48f22f0960afd4f225` |
| Package | `sha256:0720bc825aab90573b816221f45d270a6423f2ed9cae1437a228bbdcc8f08aa2` |
| Build input key | `sha256:c9afb5b30697106f1950f87e1afd74076927d0ebf18284677988ad78b348035e` |
| Intended delta | `sha256:5b9eb66b5215d676e08368f1224131a5fa609d7803dd6c7761617057d6931ef5` |
| Validation receipt | `sha256:28816890974ef052115c51be031b7bb97ba82721d753b3f16e36b52f3e88ffc1` |
| Candidate = deployment artifact | `a0f92c7fd5e052e0cf03ad8a9cfacfe9968547ad13dd546829f42ce4f39dcb05` |
| Candidate sitemap | `9344e961269df8fa6143a7ba21cb2734b3369d25294928b38d70bab037a963c8` |

**Validation**
- PACKAGE_REPRODUCIBLE: YES. FINAL_CANDIDATE_REPRODUCIBLE: YES.
- FAST 15/15, 0 unknown, 0 failed.
- COMPOSITE_FRESH_MARKET_DATA_ONLY: 42/42 paths, 0 unknown.
- Local broad regressions requested / run: 0 / 0. Remote broad jobs: 0. Unchanged markets rebuilt: 0.

## Release delta, from the exact artifact

| | Markets | Profiles | Sitemap routes |
|---|---|---|---|
| Parent | 16 | 1125 | 1327 |
| Candidate / live | 17 | 1154 | 1361 |

**Wilmington additions**
- 29 profiles.
- **34 sitemap routes**: 29 profiles + 3 corridor pages + the hub + `/pet-friendly-hotels/wilmington-nc/policy-comparison/`.
- **33 release-index routes**: the package's `intended_delta.add_routes`, which is profiles + corridors + hub.

**The 34-vs-33 difference** is exactly one route: `policy-comparison/`. The release index derives routes from `release_index._entries`, `published_corridor_routes` and `market_route`, and none of those models the policy-comparison page. The assembler emits that page into the sitemap. Both counts are true on their own basis, and the authoritative total sitemap route count is 1361.

**Removed and unexpected**
- Removed: 0 markets, 0 profiles, 0 routes.
- Unexpected market, profile and route changes: 0 / 0 / 0.
- Every live market's hotel and corridor routes are identical between the parent and the live artifact.
- Detroit does not participate.

## Authorization and gate

- **Authorization:** `ptf-auth-wilmington-002-a0f92c7fd5e0`, AUTHORIZED, bound to the five digests, `authorized_markets_by_this_decision = [wilmington-nc]`.
  - The participation flip reproduced the composed bytes: `e08952fd6414f0f8e96e13245cd53992b7583c4d3cb447947d837662d29d941b`.
  - Its status is now DEPLOYED (consumed).
- **Gate:** opened at 23:37:14Z for `wilmington-nc` only.
  - While it was open, `detroit-ann-arbor-mi`, `piedmont-triad-nc`, `charlotte-nc` and an unnamed market were all refused.
  - It was closed again after verification and is now `ENABLED NO`, allowlist `[]`.

## Deployment

**Final checks immediately before the host call**
- The parent equals the authorized parent.
- `verify_bundle_directory` found 0 problems, so the artifact digest equals the authorized digest.

**Deploy**
- Command: `netlify deploy --prod --no-build`, exit 0.
- Release operation: `ptf-auth-wilmington-002-a0f92c7fd5e0`.
- Start 23:37:41Z, complete 23:38:22Z (40.6 s).
- Host deployment: `6aa5e2623de160fcdf416577`.
- Record: `ptf-deploy-wilmington-002-6aa5e2623de160fcdf416577`.

## Live verification

The verification ran against the host, with no broad regression. Receipt: `wilmington_nc_live_verification_002.json`. **24/24 critical checks PASS.**

- The live sitemap hashes to the authorized candidate.
- All 1361 live routes were fetched, and every one returned 200.
- Wilmington hub, policy comparison and 34 routes are live; 29 profiles.

**Sampled profiles, all 200**

| Sub-area | Samples |
|---|---|
| Wilmington proper | Aloft, ARRIVE, Embassy Suites |
| ILM airport | Hotel Lela, Spark, Tru |
| Mayfaire / Wrightsville | Element, Hampton Smith Creek, Hilton Garden Inn Mayfaire |
| Carolina / Kure Beach | Carolina Beach Inn, Pirates Cove, SeaBirds |
| Leland | Holiday Inn Express, StudioRes, Tru |

- Wrightsville Beach publishes 0 profiles, matching source truth: every property read there refuses pets.
- Piedmont Triad (60 routes), Charlotte (119), Raleigh (70), Nashville (87), Lexington (25) and Toledo (21) are unchanged, and so is every other market.
- The canonical `release_index.live_index()` now reports 17 / 1154 / 1361, rollback `6aa5ce23d51fa8544146ebac`, 0 problems.

**First pass of the verifier.** It reported checks 19–21 FALSE. That was a defect in my checker, not in the site: it counted routes containing `/<market-id>/`, and Columbus (bare `/pet-friendly-hotels/`) and Cleveland (display slug) have 0 such routes both before and after. On that pass 0 routes were removed, 0 were added outside Wilmington, and every route returned 200. I corrected the predicate to compare each market's own fragment routes and re-ran the read-only verification: 24/24. No rollback was warranted.

**Rollback target:** `6aa5ce23d51fa8544146ebac`, release `5d6ced6ed2630d899595cef7d6c2e82dd43cfc15b56e2b48f22f0960afd4f225`. That is the exact Piedmont-Triad-live release Wilmington replaced.

## Live state recorded

The canonical writers updated:
- the authorization
- the deployment record
- `global_deployment_manifest.json`
- `launch_participation.json`
- `release_production_gate.json`
- `tests/pettripfinder/pins/deployment_state.json`
- the live verification receipt

| | |
|---|---|
| Host deployment | `6aa5e2623de160fcdf416577` |
| Live release | `a0f92c7fd5e052e0cf03ad8a9cfacfe9968547ad13dd546829f42ce4f39dcb05` |
| Parent | `5d6ced6ed2630d899595cef7d6c2e82dd43cfc15b56e2b48f22f0960afd4f225` |
| Package | `sha256:0720bc825aab90573b816221f45d270a6423f2ed9cae1437a228bbdcc8f08aa2` |
| Markets / profiles / routes | 17 / 1154 / 1361 |
| Rollback | `6aa5ce23d51fa8544146ebac` |

## Performance

| Stage | Time |
|---|---|
| ZERO_TO_AUTHORIZATION_READY | 59 m 15 s |
| Founder authorization received | 23:31:50Z |
| Authorization processing (Phases 1–5) | about 5 min, of which the authorization and gate script took 170 s |
| Final parent check | 4.5 s (+ 3.8 s byte re-hash) |
| Host deployment | 40.6 s |
| Live verification | two read-only passes, about 1 min each |
| AUTHORIZATION_TO_VERIFIED_LIVE | 9 m 28 s |
| ZERO_TO_VERIFIED_LIVE | 1 h 17 m 26 s |

- Local broad regressions: 0. Remote broad jobs: 0. Unchanged live markets rebuilt: 0.
- Factory status: RESUME_MARKET_PRODUCTION.
