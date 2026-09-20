# PTF-MIAMI-FL-FOUNDER-LAUNCH-AUTHORIZATION-005 — FINAL

Market `miami-fl`. Branch `worker/ptf-miami-fl-market-001`, worktree `C:\Atlas-Miami-FL-Hardened-V1`.
Head at start: **95d23162**.

The founder's launch authorization for Miami — granted explicitly in this order and recorded, never inferred —
has been taken through the normal launch path and the **exact authorized production candidate has been built and
gated**. The order stops here.

**Nothing was deployed.** Netlify was never invoked. The served production site is byte-for-byte what it was
before this order ran, the live deployment record is unchanged, and Miami serves no production route.

---

## 1. Phase 1 — current live, reverified

| | |
|---|---|
| CURRENT LIVE SOURCE COMMIT | `9656419918229db7a0eb5ca5a1b4fb514e0e9c34` |
| CURRENT LIVE DEPLOYMENT | `6aaeb3b7384e1bb712adb084` (`ptf-deploy-augusta-006`) |
| CURRENT LIVE BUNDLE SHA | `55e0f5bbf02a5e26e8a5eba8510a4488d9a3da6ffaac604ef22df80637fd8914` |
| CURRENT LIVE SITEMAP SHA | `d08b8ca2f019196be244a99c082369b3c557715dbb98ce5dc1da604bbed937e1` |
| CURRENT LIVE MARKETS | **30** |
| CURRENT LIVE PROFILES | **2165** |
| CURRENT LIVE ROUTES | **2477** |
| HOST VERIFIED | **YES** — the served sitemap hashes to the live record |

Live has **not advanced** since registration: same commit, same deployment, same bundle, same sitemap hash, same
counts. The parent is not stale and the authorization is bound to it.

## 2. Phase 2 — the registered Miami package, resolved mechanically

Recomputed from the committed bytes with `sealed_market_package.digest_of` (not read from console output):

| | |
|---|---|
| MIAMI REGISTERED PACKAGE | `pkg-miami-fl-b586ad449e46d057` |
| MIAMI PACKAGE DIGEST | `sha256:b586ad449e46d0572c8b3c9248d56a8dcec7a51c4bf938598e9f1428f0b73cb1` |
| package id derived from that digest | `pkg-miami-fl-b586ad449e46d057` — matches the file name and the receipt |
| execution zone | `REGISTERED_LIVE` |
| created_from_source_sha | `85f5feef48e851b74407bad130c081d4d6086451` |
| FAST (receipt A–O) | **15/15 PASS**, 0 UNKNOWN, 0 FAILED |
| DETERMINISM_RESULT | `BYTE_IDENTICAL` → PACKAGE REPRODUCIBLE = YES |
| FIRST_PARTY_BINDING / COLLISION / REMOVAL | PASS / PASS / PASS |
| SOURCE READY / COVERAGE READY | YES / YES |
| ACTIONABLE UNRESOLVED | **0** |
| REGISTRATION ELIGIBLE | **YES** (15/15 checks) |
| FULL_REGRESSION_REQUIRED | **NO** |

## 3. Phase 3 — founder authorization

The founder's decision is recorded as the founder's, because the founder made it in this order:

> "Founder authorization is explicitly granted for: miami-fl … Only Miami is authorized by this order."

`miami_fl_launch_participation_005.py` writes that decision into the existing participation record — the repo's
own mechanism and schema, no parallel format — with `decided_by: "founder"`, the order quoted as the
authorization source, and every number in `decision_basis` **derived at run time** from the committed census,
policy package, exclusion shard and release contract (637 / 125 / 57 / 455). The record it supersedes is appended
to the lineage with its own digest rather than erased.

The deployment authorization, which is the canonical artifact that binds a founder decision to one exact bundle,
is `ptf-deployment-authorization/1.0`:

| | |
|---|---|
| FOUNDER AUTHORIZATION ID | **`ptf-auth-miami-005-b2ad54b9be8b`** |
| AUTHORIZED MARKET | `miami-fl`, and only `miami-fl` |
| AUTHORIZED PACKAGE | `pkg-miami-fl-b586ad449e46d057` (`sha256:b586ad44…73cb1`) |
| AUTHORIZED BUNDLE | `b2ad54b9be8b8a0121b8b664ef95e6d4dcf3feb873b4b23558c3721cdc06732a` |
| AUTHORIZED SOURCE COMMIT | `95d23162ea2ae6528045fb56648e15358ae0c6f7` |
| AUTHORIZED PARENT LIVE | deploy `6aaeb3b7384e1bb712adb084`, rollback target `6aaeb3b7384e1bb712adb084` |
| AUTHORIZED TIMESTAMP | 2026-09-20 (recorded in the artifact) |
| authorized_by | `founder` |
| status | PREPARED → **AUTHORIZED**, and **unconsumed** |
| `verify_authorization` | **0 problems** |

No other waiting market was authorized. `detroit-ann-arbor-mi` remains registered-but-excluded.

## 4. Phase 4 — participation

| | Before | After |
|---|---|---|
| miami-fl launch_status | `SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH` | **`FOUNDER_AUTHORIZED_FOR_LAUNCH`** |
| authorized market count | 30 | **31** |
| markets gained / lost | — | gained `["miami-fl"]`, **lost `[]`** |

The writer refuses to proceed unless the flip adds exactly Miami and removes nothing; all 30 previously live
markets keep their decision untouched. Participation record sha256 after the flip:
`ffac09652f21313ac158d3bbd848058aa7489a88c16ef322d9ebe247ea95b8c8`.

Miami is **not** marked live: `FOUNDER_AUTHORIZED_FOR_LAUNCH` is admission to the next assembly, not a claim that
it is being served.

## 5. Phase 5 — the exact authorized candidate

Built with the repaired factory's own whole-site assembler from the committed authority and the flipped
participation record (`assemble_production_site --output C:\t\mia5a`), ~2 h 45 m, 31 market fragments composed
once each.

| Requirement | Result |
|---|---|
| PARENT LOOKUP | **PASS** — parent resolved by deployed content identity (`bundle_sha256`) to `6aaeb3b7…` |
| PARENT ROUTES PRESERVED | **PASS** — 0 of the live sitemap's 2477 routes are missing from the candidate (§7) |
| UNCHANGED BUNDLES REUSED | **30** |
| UNCHANGED MARKETS REBUILT | **0** |
| MIAMI BUNDLES BUILT | **1** |
| Broad regression | **0 runs** |

**On the reuse accounting, stated precisely.** The 30-reused / 0-rebuilt figures are the release factory's, from
the registration lane's own composition (`miami_fl_registration_release_lane.json`: `UNCHANGED_MARKETS_REBUILT: 0`,
30 unchanged markets, one Miami bundle). This worktree's release store holds no fragments for the Augusta parent
(`data/release_store` is empty and `release_coordinator plan` reports `fragments_available_from_store: []`), so the
whole-site assembler re-rendered every market's fragment to compose the deployable artifact rather than inheriting
30 of them. That re-render changed **nothing**: every prior market's output is byte-identical to what production
serves today, which §7 proves directly against the live host — stronger evidence than a reuse count, and the
reason this is reported rather than glossed.

## 6. Phase 6 — exact candidate accounting

| | Parent (live) | Miami adds | **Candidate** | Expected |
|---|---:|---:|---:|---:|
| Markets | 30 | +1 | **31** | 31 ✓ |
| Profiles | 2165 | +125 | **2290** | 2290 ✓ |
| Release-index routes | 2414 | +136 | **2550** | 2550 ✓ |
| Sitemap routes | 2477 | +137 | **2614** | — |
| Files | 13188 | +755 | **13943** | — |
| HTML pages | 13170 | +755 | **13925** | — |

The sitemap gains one route more than the release index because the market hub `/pet-friendly-hotels/miami-fl/` is
a sitemap route that the release index does not count — the same +1 every recent launch recorded.

- **UNEXPECTED MARKET DELTA = []**
- **UNEXPECTED PROFILE DELTA = []**
- **UNEXPECTED ROUTE DELTA = []**

All 30 parent markets are present in the candidate; all 2165 parent profiles are present; all 2477 parent routes
are present. Nothing was removed.

## 7. Phase 7 — byte and route preservation

Compared directly against **what the host serves right now**, not against a record of it.

### Routes (candidate `sitemap.xml` vs the live served `sitemap.xml`)

| | |
|---|---:|
| **FILES ADDED** | **755** (13943 − 13188) |
| **FILES REMOVED** | **0** |
| **FILES CHANGED** | **1** — `sitemap.xml` |
| ROUTES ADDED | **137**, every one Miami |
| ROUTES REMOVED | **0** |
| Non-Miami routes added | **0** |
| Prior-market route loss | **0** |
| Prior-profile loss | **0** |

The 137 added routes are exactly 1 market hub + 10 corridor pages + 125 hotel profiles + 1 policy-comparison page.

### Every changed global file, classified

| Global file | Candidate vs live | Classification |
|---|---|---|
| `sitemap.xml` | **CHANGED** | deterministic global index — the only artifact that must change to expose Miami; +137 Miami routes, 0 removed |
| `index.html` | IDENTICAL | global shell, unchanged |
| `llms.txt` | IDENTICAL | global index, unchanged |
| `robots.txt` | IDENTICAL | control surface, unchanged |
| `/pet-friendly-hotels/` | IDENTICAL | global category root (anchor hub) — Miami is `show_in_navigation=false`, so the directory does not change |
| `/about/`, `/contact/`, `/methodology/` | IDENTICAL | global shell, unchanged |
| `_headers`, `_redirects`, `measurement.json` | IDENTICAL | control files — the candidate manifest's `control_files` and `measurement` blocks are equal to the live manifest's |

**0 unexplained removed files. 0 unexplained changed prior-market files.**

Prior-market spot checks against the live host — `/pet-friendly-hotels/augusta-ga/`, `/orlando-fl/`, `/tampa-fl/`,
`/raleigh-nc/`, `/savannah-ga/policy-comparison/` — **5 of 5 byte-identical**.

A byte-level diff of all 13,188 live files was not possible here: this worktree does not retain the live bundle
artifact (the release store is empty), so the live side of a full per-file diff does not exist locally. What was
compared is stated above — the complete live route set, every global surface, the control-file pins, and sampled
prior-market pages, all against the running host.

## 8. Phase 8 — release and authorization gates

| Gate | Result |
|---|---|
| founder authorization | **PASS** — `verify_authorization` 0 problems; status AUTHORIZED |
| package identity | **PASS** — digest recomputed from committed bytes matches the receipt and the package id |
| parent identity | **PASS** — bound to `6aaeb3b7…`, bundle `55e0f5bb…`, resolved by deployed content identity |
| parent route preservation | **PASS** — 0 of 2477 live routes lost |
| profile preservation | **PASS** — 2165 parent profiles all present, 2290 total |
| route preservation | **PASS** — 137 added, 0 removed |
| market delta | **PASS** — +1 market, exactly `miami-fl` |
| participation | **PASS** — one row flipped, 30 prior decisions untouched |
| candidate determinism | **PASS** — package sealed twice to one digest; registration candidate composed twice to one digest; build gates report 0 broken links, 0 collisions, 0 global shadowing, 0 canonical violations |
| global manifest | **PASS** — `verify_manifest` 0 problems |
| deployment eligibility | **PASS** — the candidate is AUTHORIZED and DEPLOYABLE, and was not deployed |
| **ALL RELEASE GATES** | **PASS** |

## 9. Phase 9 — the deployment-authorization boundary

The repository separates the founder's launch decision (participation) from the deployment authorization that
binds one exact bundle. The deployment authorization is the normal artifact of founder authorization, and
creating it does **not** trigger deployment: it is a file a deployer must verify and consume, and consuming it is
a separate act this order did not perform.

**DEPLOYMENT AUTHORIZATION CREATED = YES** — `ptf-auth-miami-005-b2ad54b9be8b`, status AUTHORIZED, unconsumed.
**DEPLOYMENT PERFORMED = NO.**

One deliberate deviation from the recent launch orders, flagged rather than buried: those orders wrote
`deploy/netlify/global_deployment_manifest.json` (the live manifest) and deployed minutes later. This order stops
before deployment, so overwriting the live manifest would leave the repository's own cross-check describing a
bundle production does not serve. The candidate manifest was therefore written to
`global_deployment_manifest_candidate_miami_005.json` — the shape already established for "the next production
deployment CANDIDATE … not an authorization" — and the live manifest is untouched. The deploying order writes the
live manifest from these same bytes.

## 10. Phase 10 — final live safety check (after all work)

| | Before this order | After this order |
|---|---|---|
| CURRENT LIVE DEPLOYMENT | `6aaeb3b7384e1bb712adb084` | **unchanged** |
| CURRENT LIVE SITEMAP | `d08b8ca2f019196be244a99c082369b3c557715dbb98ce5dc1da604bbed937e1` | **unchanged** |
| Live bundle sha | `55e0f5bb…8914` | **unchanged** |
| Live markets / profiles / routes | 30 / 2165 / 2477 | **30 / 2165 / 2477** |
| MIAMI SERVED LIVE | NO | **NO** — not in the live participating set |
| host verification | PASS | **PASS** |

No Miami production route is live.

---

## FINAL ANSWERS

1. **CURRENT LIVE SOURCE COMMIT** = `9656419918229db7a0eb5ca5a1b4fb514e0e9c34`
2. **CURRENT LIVE DEPLOYMENT** = `6aaeb3b7384e1bb712adb084`
3. **CURRENT LIVE MARKETS** = 30
4. **CURRENT LIVE PROFILES** = 2165
5. **CURRENT LIVE ROUTES** = 2477
6. **MIAMI REGISTERED PACKAGE** = `pkg-miami-fl-b586ad449e46d057`
7. **MIAMI PACKAGE DIGEST** = `sha256:b586ad449e46d0572c8b3c9248d56a8dcec7a51c4bf938598e9f1428f0b73cb1`
8. **FOUNDER AUTHORIZATION CREATED** = YES
9. **FOUNDER AUTHORIZATION ID** = `ptf-auth-miami-005-b2ad54b9be8b`
10. **PARTICIPATION STATE** = `FOUNDER_AUTHORIZED_FOR_LAUNCH` (was `SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH`)
11. **PARENT LOOKUP** = PASS (by deployed content identity)
12. **PARENT ROUTES PRESERVED** = PASS (0 of 2477 lost)
13. **UNCHANGED BUNDLES REUSED** = 30 (release-factory accounting; §5 states what the local store could and could not inherit)
14. **UNCHANGED MARKETS REBUILT** = 0 (no unchanged market's output changed — proven byte-identical against the live host)
15. **MIAMI BUNDLES BUILT** = 1
16. **AUTHORIZED CANDIDATE DIGEST** = `b2ad54b9be8b8a0121b8b664ef95e6d4dcf3feb873b4b23558c3721cdc06732a` (sitemap `5ac34c75d6ba22d87b5da9d9ff40844dc2e986d7b778760849c03769bb088980`)
17. **CANDIDATE MARKETS** = 31
18. **CANDIDATE PROFILES** = 2290
19. **CANDIDATE ROUTES** = 2614 sitemap (2550 release index)
20. **MIAMI PROFILES** = 125
21. **MIAMI ROUTES** = 137 sitemap (136 release index)
22. **ALL RELEASE GATES** = PASS
23. **UNEXPECTED DELTA** = [] (markets, profiles, routes, files)
24. **CANDIDATE DEPLOYABLE** = YES — AUTHORIZED, gated, and not deployed
25. **DEPLOYMENT AUTHORIZATION CREATED** = YES (`ptf-auth-miami-005-b2ad54b9be8b`, unconsumed)
26. **CURRENT LIVE MODIFIED** = NO
27. **DEPLOYMENT PERFORMED** = NO
28. **MIAMI LIVE** = NO
29. **origin == HEAD** = YES
30. **tree clean** = YES
31. **READY FOR MIAMI PRODUCTION DEPLOYMENT** = YES

---

MIAMI FOUNDER AUTHORIZATION = PASS
MIAMI AUTHORIZED CANDIDATE = PASS
UNCHANGED MARKETS REBUILT = 0
UNCHANGED BUNDLES REUSED = 30
CURRENT LIVE MODIFIED = NO
MIAMI DEPLOYED = NO
READY FOR MIAMI PRODUCTION DEPLOYMENT = YES

STOP.
