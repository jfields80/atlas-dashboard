# PTF-AUSTIN-TX-FOUNDER-LAUNCH-AUTHORIZATION-AND-DEPLOYMENT-004 — FINAL

**AUSTIN IS LIVE.** Deploy `6abf3e749cc359701298718d` (published 2026-10-02T05:18:15Z) serves **38 markets /
3,386 profiles / 3,737 release-index routes / 3,808 served routes**. Austin / Central Texas is the
thirty-eighth market and the first in Texas. Rollback is `6abdbcb87e046e3e673760ac`, the reader-safety correction.

> Founder authorizes Austin pkg-austin-tx-ee3f5c9147638f51 for launch; deploy after gates.

Only that package was authorized. The stale `pkg-austin-tx-3030caf7`, sealed under the replaced reader, and the
shadow id `pkg-austin-tx-024e6fb4` were refused by every writer.

Branch `worker/ptf-austin-tx-market-001`. Commits:
- `ef28f7b4`: the founder decision, committed before the whole-site build;
- `02495af4`: the candidate and the deployment authorization;
- `f0ddbcde`: AUSTIN IS LIVE (record, supersessions, pins);
- then this report.

## 1. Live parent

Verified at the start, and again immediately before the deploy (05:1xZ):

- deploy `6abdbcb87e046e3e673760ac`, source `46e49a02` (built from `18f4f979`);
- bundle `63ae17cf…`, sitemap `4ee06422…`;
- 37 / 3,196 / 3,534 / 3,604, host verified;
- Netlify published `6abdbcb8` (ready).

**The parent never advanced.** The pre-deploy baseline sweep returned 3,604 / 3,604 routes 200.

## 2. Founder authorization (participation)

`austin_tx_launch_participation_004.py` uses `launch_participation.extend_decision`, so the chain is extended, not
rewritten.

- **Status:** austin-tx moved from `SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH` to
  `FOUNDER_AUTHORIZED_FOR_LAUNCH`.
- **Authorized set:** 37 → 38, gained austin-tx only, lost none; 0 other rows changed.
- **Integrity:** `decision_problems` `[]`; the lineage has 44 records; this is the first authorization, with no
  supersession entry.
- **Attribution:** decided_by `founder`, decided_on 2026-10-01. The founder's words are transcribed; no name is
  signed.
- **Guards that held** (each refuses to write if committed state disagrees):
  - package `ee3f5c91`;
  - cohort 190 / 63;
  - new-spend 80 / founder 25 (18 dual-brand rows on 9 address keys × 2, 5 operator-domain, Mountain Star,
    Strickland) / exhausted 49 / preopening 0, each publishing 0;
  - 3 timeshare identities NON_LODGING / TIMESHARE, outside inventory;
  - 82 multi-amount records, 0 publishing a single fee;
  - actionable 0, coverage YES by founder decision, source ready YES.

## 3. The exact candidate

**Builds.** `assemble_production_site` ran twice, sequentially, on the committed tree `ef28f7b4`:

| | build | started | outcome |
|---|---|---|---|
| A | `C:/t/atx4a` | 02:03:49Z | went idle after its manifests (1.44 s CPU over 30 s, manifests stable); terminated at 03:31:11Z |
| B | `C:/t/atx4b` | 03:31:12Z | exited on its own |

| | |
|---|---|
| CANDIDATE BUNDLE / SITEMAP | `75e569412dd28a64eb4c7aa02c58c955badf065833d969b1d18b8ed339fa31b0` / `d6461dbc2cd4bc225c52b235c5e4b675f78117b0b2e191463fe5c4baca2ef606` |
| DETERMINISM | **BYTE_IDENTICAL**: 20,488 files compared, 0 differing; both manifests byte-identical |
| MARKETS / PROFILES / RELEASE-INDEX / SERVED | **38 / 3,386 / 3,737 / 3,808** (+1 / +190 / +203 / +204) |
| BYTE PRESERVATION vs live | +1,136 files (all Austin's), 0 removed, 1 changed (`sitemap.xml`), **0 prior-market files changed** |
| REUSE | 37 unchanged markets reused, 0 rebuilt, 1 Austin bundle; 38 fragments physically rendered (no release store populated), reported separately and not called reuse |

**Accounting: `austin_tx_launch_authorization_004.json`, ALL GATES PASS.** Checked on the BUILT artifact, by the
route the site forms:

- 0 of 154 held rows and 0 of 63 verified-no-pets rows publish;
- 0 timeshare profiles or exclusions;
- 0 misleading single fees;
- 0 collisions (any market, bare chain, duplicates);
- FAST receipt `pkg-austin-tx-ee3f5c9147638f51-2a0d99ea…` currently eligible, non-vacuous.

## 4. Deployment authorization

| | |
|---|---|
| ID | **`ptf-auth-austin-004-75e569412dd2`** |
| binds | bundle `75e56941…`, sitemap `d6461dbc…`, 38 / 3,386 / 3,808 |
| source_commit | `ef28f7b4`, the BUILD commit (not HEAD; the lesson of the reader-safety correction) |
| rollback target | `6abdbcb87e046e3e673760ac` |
| authorized_by | `founder`, with the founder's words quoted in `authorization_source` |
| checks before deploy | `verify_authorization` `[]`, `deployability_problems` `[]`, `verify_target` `[]`, `verify_bundle_directory` `[]` |
| live manifest | written from the authorized bytes immediately before the deploy; identical to the candidate manifest; `verify_manifest` `[]` |

## 5. The deployment

```
netlify deploy --prod --no-build --dir C:\t\atx4a\site --site pettripfinder-prod
DEPLOY START 2026-10-02T05:17:12Z   END 05:18:14Z   EXIT 0   (1,138 files uploaded)
NETLIFY DEPLOYMENT ID = 6abf3e749cc359701298718d
```

It ran once, with no retry and no rebuild.

## 6. Host verification

`austin_tx_live_verification_004.json`: **13/13 PASS**, ROLLBACK_REQUIRED NO.

**Served state:**
- The served sitemap is the authorized `d6461dbc…`, and the served route set is identical to the candidate's.
- The host publishes `6abf3e74` (ready, production), and its previous deploy is `6abdbcb8`.

**Routes:**
- **All 204 Austin routes return 200** (190 hotels, 12 corridors, hub, policy comparison).
- **All 3,604 prior routes return 200, with 0 lost.** Only Austin routes were added.
- **Every unpublished Austin census row returns 404**: 217 rows (154 held + 63 verified-no-pets), probed at both
  the census slug and the route the site forms (259 URLs).

**Other checks:**
- The three timeshare identities have no route and are not named on the hub, the comparison page or any corridor
  page.
- 26 / 26 sampled pages are byte-identical to the artifact (Austin hub, comparison, 3 corridors, 6 hotels, 11 other
  market hubs, global surfaces).
- Phoenix, Denver, San Diego, Jacksonville FL, West Palm Beach, Fort Lauderdale, Augusta, Miami, Tampa, Orlando,
  Jacksonville NC and Austin return 200; **Detroit returns 404**, still withheld.

## 7. Deployment state finalized (only after host verification passed)

- **Record:** `ptf-deploy-austin-004-6abf3e749cc359701298718d`; `verify_record` `[]`.
- **Authorization:** consumed (DEPLOYED).
- **`supersessions.json`:** the reader-safety authorization entry is now historical, with 0 contract drift; a new
  CURRENT entry with an empty moved list was appended.
- **`deployment_state.json`:** the live and source pins both point at `6abf3e74`; source_commit equals the manifest's
  `ef28f7b4`.

**Bounded post-deploy checks:**
- `test_market_state_pins.py` plus the reader tests: **297 / 297**;
- `release_contracts`: 39 / 39;
- `build_global_authority --check`: clean;
- resolver: deploy `6abf3e74`, live lineage commit `f0ddbcde`, host verified;
- 0 broad regression runs.

**The registration base-derivation block (from order 003) is cleared.** The new lineage commit `f0ddbcde` carries
its own record, and `derive_registration_base` now returns `f0ddbcde` automatically for a future market. Rule for
next time: correct a deployment record with a new record, never by editing it in place.

**One small bug of mine in the post-deploy module.** `supersessions` first passed a string where
`DA._sha256_file` needs a `Path`. It crashed after the record was written and before anything else was; I fixed it
and re-ran it.

## 8. Cleanup

- Both build processes are gone.
- `C:/t/atx4a` is the live artifact (the next deploy's parent bytes); `C:/t/atx4b` is its twin.
- No watchers or child processes remain. The unrelated pre-existing process from 2026-09-14 was left alone.

## FINAL STATE

| | |
|---|---|
| LIVE DEPLOYMENT | `6abf3e749cc359701298718d` |
| LIVE MARKETS / PROFILES / RELEASE-INDEX / SERVED | **38 / 3,386 / 3,737 / 3,808** |
| AUSTIN | LIVE: 190 profiles, 12 corridors, 63 verified-no-pets as exclusions, 154 held unpublished |
| PRIOR MARKETS / PROFILES / ROUTES LOST | 0 / 0 / 0 |
| PET-FRIENDLY WITH EXPLICIT REFUSAL / QUESTION-ONLY | 0 / 0 |
| MISLEADING SINGLE FEES | 0 |
| BROAD REGRESSION RUNS | 0 |
| ROLLBACK USED | NO (target `6abdbcb8` stays available) |
| DETROIT | withheld (404) |
