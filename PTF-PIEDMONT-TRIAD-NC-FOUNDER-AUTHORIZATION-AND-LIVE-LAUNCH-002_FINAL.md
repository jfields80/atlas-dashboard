# PTF-PIEDMONT-TRIAD-NC-FOUNDER-AUTHORIZATION-AND-LIVE-LAUNCH-002 — final report

The Piedmont Triad is LIVE as the 16th market.

- Host deploy: `6aa5ce23d51fa8544146ebac`
- Production: 16 markets / 1125 profiles / 1327 sitemap routes

## Phase 1 — parent recheck

The live parent still matched the packet, so STALE_PARENT = NO.

| Field | Value |
|---|---|
| Host deployment ID | `6aa5ad211250a04bc0bc6f7f` |
| Live release | `606d6088460a48c7787fac6deb1befcc12e39d6ee384342cc13d8ab43ad8a815` |
| Source commit | `c65e9f28b16fe77c55a0a8d2497ed18c519efeed` |
| Sitemap | `3c6713782208a486f96d7177663625d56606f2bc0bd6bdc353a9b7111af45e6d` |
| Markets / profiles / routes | 15 / 1071 / 1267 |
| Rollback target | `6aa593019a24fc17a07566a4` |
| Release-index problems | 0 |

## Phase 2 — authorization inputs

Every value below was read from the committed packet and matched against the package and receipt.

| Input | Value |
|---|---|
| Parent release | `606d6088460a48c7787fac6deb1befcc12e39d6ee384342cc13d8ab43ad8a815` |
| Triad package | `sha256:27c754bed2d608521cd47cea8611c46efc18e2a430d5a5f290b4d8cef135e432` |
| Build input key | `sha256:dbdf939eb74d491c7e2f21c023a6ed4a3ee5da4829c37908e4d3b99b654ffd4b` |
| Intended delta | `sha256:bc6a2c87de686841a4dbfb1731b2e31a3439b231f902187dc65bf3bb075be6ca` |
| Validation receipt | `sha256:a868fb4bf4834cf4668442484bb2baa855856c250704d1fb3ff093a4498694d5` |
| Final candidate / deployment artifact | `5d6ced6ed2630d899595cef7d6c2e82dd43cfc15b56e2b48f22f0960afd4f225` |
| Candidate sitemap | `aa857f2a275cd58ba1cbc6d9b124165abf4ca52876d20c78ae1e1fae0d83b0c0` |

- Package and candidate both reproducible: YES.
- FAST: 15/15 PASS, 0 unknown, 0 failed.
- Change class: COMPOSITE_FRESH_MARKET_DATA_ONLY, with 15/15 proofs passing.
- Broad regressions (local requested, local run, remote): 0 / 0 / 0.
- Unchanged markets rebuilt: 0.

## Phase 3 — release delta (from the artifact)

- Candidate: 16 / 1125 / 1327. It adds 1 market, 54 profiles and 60 routes.
- Removed: 0 markets, 0 profiles, 0 routes.
- Every live market's profile count is preserved.
- No non-live market participates; Detroit is not included.
- Unexpected market, profile, route and file changes: all 0.

## Phases 4–5 — authorization and gate

- **Authorization:** `ptf-auth-piedmont-triad-002-5d6ced6ed263`, AUTHORIZED, market `piedmont-triad-nc` only. It binds the parent, package, build input key, intended delta, receipt, candidate and artifact digests.
- **Participation:** one row flipped.
  - Before: `f6d21e6a44d3de50db17f214b3aa5dbb04cfac13af6dd095bc71739d0b710d22`
  - After: `b7c6311da2e9761e7b6e64b5aaf08be2fd48bdee57491d73bda18062d6ae71ae`
  - The "after" hash equals the participation the candidate was composed under. Decision problems: 0.
- **Gate:** changed from NO/[] to YES/[piedmont-triad-nc]. The loader refused Detroit, Charlotte and an unnamed market while the gate was open.

## Phases 6–7 — final check and deploy

- **Final parent check:** the live release still equaled the authorized parent (4.4 s).
- **Byte check:** `verify_bundle_directory` on `C:\t\tri1a\site` returned no problems (3.4 s).
- **Deploy:** `netlify deploy --prod --no-build`, exit 0.
  - Start 22:11:19Z, complete 22:12:01Z (42 s).
  - Host deployment `6aa5ce23d51fa8544146ebac`.
  - No build, reassembly, re-seal or policy change happened after authorization.

## Phase 8 — live verification

All 22 checks PASS, and all 1327 live routes return 200.

- The live sitemap sha equals the candidate sitemap.
- Triad routes: hub, policy comparison, 54 profiles and 4 corridor pages (PTI Airport, Coliseum, Hanes Mall, Downtown Winston-Salem) are all 200.
- Greensboro, Winston-Salem and High Point samples are all 200.
- Kernersville publishes no corridor page (2 published hotels, below the minimum of 5).
- Route counts are unchanged for Charlotte (119), Raleigh (70), Nashville (87), Lexington (25) and Toledo (21).
- Unrelated surfaces return 200.
- Rollback target is the Charlotte-live release: `6aa5ad211250a04bc0bc6f7f` / `606d6088460a48c7787fac6deb1befcc12e39d6ee384342cc13d8ab43ad8a815`.

On the first verification run, check 7 read false. The cause was a type bug in my verification script, which compared a route list to an integer. No page failed. I fixed the check, re-ran it, and all 22 passed. No rollback was required.

## Phases 10–11 — record and gate

- The authorization is DEPLOYED, and `ptf-deploy-piedmont-triad-002-6aa5ce23d51fa8544146ebac` is written with no record problems.
- The `deployment_state` pin has moved to the new deploy.
- Receipt: `markets/reports/piedmont_triad_nc_live_verification_002.json`.
- `release_index.live_index()` derives 16 / 1125 / 1327 with 0 problems, and `verify_all` is clean.
- The gate is closed again (NO/[]), and its entry moved to `previously_consumed`.

## Performance

| Stage | Time |
|---|---|
| Founder authorization processing | 4.2 s |
| Final parent + byte check | 7.8 s |
| Host deployment | 42 s |
| Live verification | 27 s |
| **AUTHORIZATION_TO_VERIFIED_LIVE** | **6 min 54 s** (22:08:23 → 22:15:17) |
| ZERO_TO_AUTHORIZATION_READY | 1 h 19 m 47 s |
| ZERO_TO_VERIFIED_LIVE, wall clock (includes the wait for the founder decision) | **1 h 33 m 46 s** |
| ZERO_TO_VERIFIED_LIVE, active engineering | 1 h 26 m 41 s |

- Broad regressions: 0.
- Remote broad jobs: 0.
- Unchanged markets rebuilt: 0.
- Factory code changed: NO.
- FACTORY STATUS = RESUME_MARKET_PRODUCTION.
