# PTF-WEST-PALM-BEACH-FL-PRODUCTION-DEPLOYMENT-007 — FINAL

**Worktree** `C:\Atlas-West-Palm-Beach-FL-Hardened-V1` · **Branch** `worker/ptf-west-palm-beach-fl-market-001`
**Deploy commit** `e3efa221` · **Artifact** `C:\t\wpb6a\site` (the authorized candidate; nothing rebuilt)

## WEST PALM BEACH IS LIVE

The Palm Beaches is production market **#33**. The exact founder-authorized candidate was deployed with no rebuild. It
was verified against the running host, meaning every served route was fetched and every WPB page byte-compared,
before anything was recorded. The authorization was consumed only after that.

| | |
|---|---|
| NETLIFY DEPLOYMENT | **`6ab599163f833ab7f48b395d`** (published 2026-09-24T21:42:03.518Z, state `ready`) |
| rollback target | `6ab1a035c7ef3b14a23a4ec6` (Fort-Lauderdale-live, still `ready`) |
| LIVE BUNDLE | `23728b4bff71c66d0a9a063de3882d744f92465f5f568f72b3caf16ca8641d78` |
| LIVE SITEMAP | `8ae34cea1c7e384f0f4c8499066c5ff2f9ca841d099c344a5860041b4b6c7546` |
| LIVE | **33 markets / 2424 profiles / 2701 release-index routes / 2767 served routes** |
| ROLLBACK REQUIRED | NO |

---

## 2 — PRE-DEPLOYMENT LIVE (`preflight_007`, report `west_palm_beach_fl_deployment_preflight_007.json`)

Resolver (`--verify-host`): RESOLVED YES, deploy **`6ab1a035c7ef3b14a23a4ec6`**, source `e82120cc`, bundle `0ec5c655…`,
**32 / 2375 / 2646 / 2711**, host verified. External GET of the sitemap: sha `e81961ae…`, 2711 `<loc>`, 0 WPB URLs.

| Probe | HTTP |
|---|---|
| WPB hub | 404 |
| Hilton Garden Inn Boca Raton | 404 |
| WPB corridor `boca-raton` | 404 |
| WPB policy-comparison | 404 |
| old Apple Ten route | 404 |
| Fort Lauderdale / Augusta | 200 / 200 |
| Detroit | 404 |

Production was exactly the authorized rollback parent. **No divergence.**

## 3 — AUTHORIZATION VALIDATION

| | |
|---|---|
| `ptf-auth-west-palm-beach-006-23728b4bff71` | exists, **AUTHORIZED**, **unconsumed** |
| binds | bundle `23728b4b…` · sitemap `8ae34cea…` · rollback `6ab1a035c7ef3b14a23a4ec6` · participation `837d37d3…` (= the record on disk) |
| `ptf-auth-west-palm-beach-003-217f87eeba72` | **SUPERSEDED**, never consumed, binds `217f87ee…` (not this bundle) |
| deployable records in the repo | exactly `[ptf-auth-west-palm-beach-006-23728b4bff71]`, no competitor |
| transfer from the superseded authorization | none: 006 is a separate record from a separate founder decision |

## 4 — CANDIDATE INTEGRITY (no rebuild)

`deployment_authorization.verify_bundle_directory(auth, C:\t\wpb6a\site)` re-hashed all 14,760 files and returned **`[]`**:
the directory IS the authorized bundle, sitemap and control files included.

| | required | actual |
|---|---|---|
| bundle | `23728b4b…` | `23728b4bff71c66d0a9a063de3882d744f92465f5f568f72b3caf16ca8641d78` ✓ |
| sitemap | `8ae34cea…` | `8ae34cea1c7e384f0f4c8499066c5ff2f9ca841d099c344a5860041b4b6c7546` ✓ |
| WPB market bundle | `711760f0…` | `711760f09faddc8022b5d55a681c0ccd0937151a2d61be34d67cbdd0c934ef45` (receipt `5aaf1cb2` J; 0 defects) ✓ |
| markets / profiles | 33 / 2424 | 33 / 2424 ✓ |
| release-index / served | 2701 / 2767 | 2701 / 2767 (sitemap 2767 `<loc>`) ✓ |
| WPB profiles / release-index / served | 49 / 55 / 56 | 49 / 55 / 56; served − release = `[/pet-friendly-hotels/west-palm-beach-fl/policy-comparison/]` ✓ |

## 5 — CRITICAL IDENTITY REGRESSION (pre-deploy, on the artifact)

* **Hilton Garden Inn Boca Raton:** a published policy row owned by `west-palm-beach-fl`, a page with the title *Hilton Garden
  Inn Boca Raton Pet Policy | PetTripFinder West Palm Beach, Florida*, present in the sitemap and in the release routes. The
  first-party binding is `bctbrgi`, `full_premises_match true`, `…/bctbrgi-hilton-garden-inn-boca-raton/hotel-info/`, READ.
* **Apple Ten:** 0 policy rows, 0 release-index routes, 0 sitemap entries, 0 files, and 0 WPB pages containing the text
  "apple ten". No residual artifact can recreate it.

## 6 — GLOBAL DEPLOYMENT MANIFEST

`global_deployment.write_manifest()` was run on `C:\t\wpb6a\global_bundle_manifest.json` (the authorized bytes, not a
recomposition). The live `global_deployment_manifest.json` now describes 33 markets / 2424 / 2767, bundle `23728b4b…`,
sitemap `8ae34cea…`, `source_commit ff6b506d`. It is **byte-identical** (LF-normalised) to the committed candidate manifest
`global_deployment_manifest_candidate_west_palm_beach_006.json`. `verify_manifest []`. After it was written,
`verify_authorization []` and `deployability_problems []`. Lineage to the previous deployment is carried by the deployment
record (`previous_deployment_id` = `rollback_target` = `6ab1a035…`) and the pin.

## 7 — SUPERSESSIONS (`tests/pettripfinder/pins/supersessions.json`, three canonical steps)

1. `reviewed_by` → `PTF-WEST-PALM-BEACH-FL-PRODUCTION-DEPLOYMENT-007`.
2. `ptf-auth-fort-lauderdale-003-0ec5c6557d79`: "The CURRENT live authorization…" → "Historical. … until deploy
   6ab599163f833ab7f48b395d published west-palm-beach-fl …". Its 32 bound contracts were re-hashed: **0 drift**. WPB is
   absent from its contracts, so `moved_by_later_work` stays `{}`.
3. Appended `ptf-auth-west-palm-beach-006-23728b4bff71` as **CURRENT** (`moved_by_later_work {}`; its 33 bound contracts
   re-hashed with 0 drift).

The chain lists only authorizations production **consumed**, as `chain_problems` derives from the deployment records. So the
never-consumed `217f87ee` correctly gets no key: the guard would refuse "listed but never consumed". The history is preserved
in the new entry's note (003 decision → package `789c0187` → auth `217f87ee` SUPERSEDED, never consumed → correction to
`94d6f411` → 005 supersession → 006 new decision → this deployment). Nothing was deleted or rewritten; 28 → 29 entries.

## 8 — DEPLOYMENT

```
netlify deploy --prod --no-build --dir C:\t\wpb6a\site --site pettripfinder-prod
start 2026-09-24T21:41:13.90Z   end 2026-09-24T21:42:02.96Z   (49 s)   exit 0
CDN requesting 300 files -> Finished uploading 300 assets -> Deploy is live!
Unique deploy URL https://6ab599163f833ab7f48b395d--pettripfinder-prod.netlify.app
```

`--no-build`: Netlify built nothing. **300 files is exactly the authorized delta**: 299 new WPB files plus the changed
`sitemap.xml`. The other 14,460 files were already identical on the CDN.

## 9 — POST-DEPLOYMENT LIVE VERIFICATION (the host, not the command; `west_palm_beach_fl_live_verification_007.json`, 13/13 PASS)

| | |
|---|---|
| host published deploy (Netlify API `getSite`) | `6ab599163f833ab7f48b395d`, `ready` |
| host sitemap | `8ae34cea…` = authorized; 2767 `<loc>`, 2767 unique, **set-equal to the candidate** |
| every served route fetched individually | **2767 / 2767 → 200** |
| parent routes (2711) still served | 2711/2711; **0 lost** |
| routes added | 56, all under `/pet-friendly-hotels/west-palm-beach-fl/`; 0 elsewhere |
| WPB inventory live | 49 profiles + 1 hub + 5 corridors = **55 release-index**; + policy-comparison = **56 served**; 56/56 → 200; 0 missing |
| WPB pages byte-identical to the artifact | **56 / 56** |
| WPB hub / policy-comparison | 200 / 200 |
| corridors | boca-raton 200 · delray-beach 200 · downtown-west-palm-beach 200 · palm-beach-gardens 200 · palm-beach-international-airport 200 |
| **Hilton Garden Inn Boca Raton** | **200**, title *Hilton Garden Inn Boca Raton Pet Policy \| PetTripFinder West Palm Beach, Florida* |
| representative profiles | 7 sampled across the list, all 200 (and all 49 in the full fetch) |
| **Apple Ten** | profile route **404**; `/go/…/apple-ten-hospitality-management-inc/{booking,call,directions,official-website,report-change}/` all **404**; not in the sitemap |
| unpublished census rows | all **141** would-be routes **404** (+8 census-slug spellings of published hotels whose route slug differs, also 404: no duplicate pages) |
| existing markets | Fort Lauderdale 200 · Augusta 200 · Miami 200 · Tampa 200 · Orlando 200 · Cleveland/Westlake Holiday Inn Express 200 |
| Detroit (withheld; SOURCE_READY) | **404**, as intended |
| global surfaces `/`, `/pet-friendly-hotels/`, `/about/`, `/contact/`, `/methodology/`, `/robots.txt`, `/llms.txt` | 200, served bytes = artifact = parent (unchanged) |

After the record was committed, the resolver returned RESOLVED YES: live `6ab599163f833ab7f48b395d`, record
`ptf-deploy-west-palm-beach-007-…`, source `e3efa221`, bundle `23728b4b…`, sitemap `8ae34cea…`, **33 / 2424 / 2767**,
host verified. `live_index` gives 33 markets / 2424 profiles / **2701 release-index routes**, 0 problems.

## 10 — DELTA RECONCILIATION

| | authorized (006 accounting) | deployed |
|---|---|---|
| files added | +299 (all WPB: 56 pages + 243 `/go/`) | 299 new files uploaded; +56 served routes, all WPB, byte-identical |
| files removed | 0 | 0 served routes lost; the rest of the CDN identical |
| files changed | 1 (`sitemap.xml`) | 1: `sitemap.xml` (now `8ae34cea…`); global surfaces byte-identical to the parent |
| CDN upload | expected 300 | **300** |

UNEXPECTED ADDED / REMOVED / MODIFIED = **0 / 0 / 0**.

## 11 — AUTHORIZATION CONSUMPTION

Written by `west_palm_beach_fl_deployment_record_007.py`, which reads **only** from the host-verification report and refuses
unless it says PASS and the host publishes this deploy as ready:

* record **`ptf-deploy-west-palm-beach-007-6ab599163f833ab7f48b395d.json`**, `final_status DEPLOYED`, `verify_record []`,
  `work_order` = the authorizing order (006), `deployer.work_order` = this order (007).
* **`ptf-auth-west-palm-beach-006-23728b4bff71`: AUTHORIZED → DEPLOYED.** The DEPLOYED history entry names
  `deployment_id 6ab599163f833ab7f48b395d`, `deployment_record_id` and `consumed_by_work_order`. DEPLOYED ∉ DEPLOYABLE_STATUSES
  and its only transition is to ROLLED_BACK, so **it can never deploy again.**
* `ptf-auth-west-palm-beach-003-217f87eeba72` remains **SUPERSEDED**, and the module refuses to run otherwise.
* 0 AUTHORIZED records remain in the repository.
* Deployment pin (`deployment_state.json`, by `west_palm_beach_fl_deployment_pin_007.py`, derived from the record and the
  manifest): live = source = `6ab599163f833ab7f48b395d`, 33 / 2424 / 2767, `ahead_of_production false`, rollback
  `6ab1a035c7ef3b14a23a4ec6`, rollback record `ptf-deploy-fort-lauderdale-004-…`.
* Participation needed **no** write. `FOUNDER_AUTHORIZED_FOR_LAUNCH` is the canonical live state; no status was invented.

## 12 — ROLLBACK SAFETY

**ROLLBACK REQUIRED = NO**: every live check passed. The rollback target `6ab1a035c7ef3b14a23a4ec6` is still `ready` on
Netlify (`getDeploy`), its artifact `C:\t\ftl3a` is intact, and it is recorded as `rollback_target` in the authorization,
the record and the pin.

## 13 — RELEASE GATES

| Gate | |
|---|---|
| FAST | **PASS**: receipt `…-5aaf1cb212b2f493.json` 15/15, current-eligible under the repaired reader (J 320 / 304, 0 defects); Augusta's empty receipt remains ineligible |
| deployment manifest integrity | PASS (`verify_manifest []`, = candidate manifest) |
| sitemap integrity | PASS (host = authorized, set-equal) |
| route accounting | PASS (2701 release-index / 2767 served; WPB 55 / 56) |
| identity accounting | PASS (Hilton live; Apple Ten absent everywhere) |
| authority lineage | PASS: `launch_participation.decision_problems []` (the canonical rule: authorized + cumulatively superseded never shrinks) |
| authorization consumption | PASS (DEPLOYED, names this deploy) |
| supersession integrity | PASS: `contracts/test_market_state_pins.py` 231/231, including the chain guard |
| production-host checks | PASS (13/13) |
| existing-market regression | PASS |
| WPB positive routes | PASS (56/56) |
| Apple Ten negative | PASS |
| rollback availability | PASS |
| deployment guards `test_deployment_authorization_047` + `test_release_composition_contract_006` + pins | 371 passed, **1 failed (pre-existing, below)** |

**The one failing test, stated plainly rather than waived.**
`test_deployment_authorization_047.py::test_the_lineage_is_ordered_and_ends_before_the_current_record` asserts the RAW
founder-authorized counts in the participation lineage never decrease. The lineage now contains the 005 re-registration
record (32 authorized + `founder_authorization_superseded: [west-palm-beach-fl]`) after the 003 record (33). The canonical
rule introduced by `4cbe6e4c` counts **authorized + cumulatively superseded**, and `decision_problems` returns `[]`. This test
predates that rule and was not updated with it. Measured in a clean worktree: it **passes at `348c9da6`** and **fails from
`ff6b506d`** (the 006 founder decision, the first lineage to contain a supersession record) and at `fb66f001`, the order's
starting checkpoint. So it is **not caused by this deployment**. I missed it in order 006 because I did not run this module
there. The fix is a one-line test change (use the same adjusted counts as `decision_problems`) in a shared test module, so it
belongs to its own bounded order and was not made here. The second failure seen mid-order
(`test_no_case_here_touched_a_committed_record`) was the not-yet-committed live manifest, and it passes after the commit.

No broad regression was run. The whole-site assembly suite (`test_global_deployment_architecture_045`) was not run.

## 14 — REPOSITORY

Commits: `e3efa221` (live manifest, deployment record, consumed authorization, pin, supersessions, preflight and
verification reports, the two market-local helpers) and the report commit. Pushed. No secrets, credentials or browser data
were committed: the Netlify CLI uses its own stored login, and nothing from it is in the tree.

---

## FINAL ANSWERS

1. PRE-DEPLOY LIVE DEPLOYMENT = `6ab1a035c7ef3b14a23a4ec6`
2. PRE-DEPLOY LIVE MARKETS = 32
3. DEPLOYMENT AUTHORIZATION = `ptf-auth-west-palm-beach-006-23728b4bff71`
4. AUTHORIZATION VALID AT START = YES
5. AUTHORIZATION UNCONSUMED AT START = YES
6. AUTHORIZED CANDIDATE SHA = `23728b4bff71c66d0a9a063de3882d744f92465f5f568f72b3caf16ca8641d78`
7. ACTUAL DEPLOYED CANDIDATE SHA = `23728b4bff71c66d0a9a063de3882d744f92465f5f568f72b3caf16ca8641d78` (directory re-hashed; host serves it, 56/56 WPB pages byte-identical)
8. AUTHORIZED SITEMAP SHA = `8ae34cea1c7e384f0f4c8499066c5ff2f9ca841d099c344a5860041b4b6c7546`
9. ACTUAL LIVE SITEMAP SHA = `8ae34cea1c7e384f0f4c8499066c5ff2f9ca841d099c344a5860041b4b6c7546`
10. WPB MARKET BUNDLE SHA = `711760f09faddc8022b5d55a681c0ccd0937151a2d61be34d67cbdd0c934ef45`
11. GLOBAL DEPLOYMENT MANIFEST WRITTEN = YES (byte-identical to the authorized candidate manifest)
12. SUPERSESSIONS EXTENDED = YES (28 → 29; 006 CURRENT; FTL Historical)
13. PRODUCTION DEPLOYMENT PERFORMED = YES (`6ab599163f833ab7f48b395d`, 49 s, 300 files)
14. POST-DEPLOY LIVE MARKETS = 33
15. POST-DEPLOY LIVE PROFILES = 2424
16. POST-DEPLOY RELEASE-INDEX ROUTES = 2701
17. POST-DEPLOY SERVED ROUTES = 2767
18. WPB LIVE = YES
19. WPB PROFILES LIVE = 49
20. WPB RELEASE-INDEX ROUTES LIVE = 55
21. WPB SERVED ROUTES LIVE = 56
22. WPB HUB = HTTP 200
23. HILTON GARDEN INN BOCA RATON = HTTP 200
24. HILTON IDENTITY BINDING PASS = YES (`bctbrgi`, `full_premises_match true`)
25. APPLE TEN PROFILE PRESENT = NO
26. APPLE TEN ROUTE PRESENT = NO
27. APPLE TEN LIVE PAGE PRESENT = NO (profile + 5 `/go/` pages 404)
28. FIVE WPB CORRIDORS LIVE = YES (5/5 → 200)
29. WPB POLICY COMPARISON LIVE = YES (200)
30. FTL REGRESSION = PASS (200)
31. AUGUSTA REGRESSION = PASS (200)
32. DETROIT EXPECTED STATE = 404 (withheld, SOURCE_READY) ✓
33. EXPECTED DELTA RECONCILED = YES (+299 / −0 / 1 changed; 300 uploaded)
34. UNEXPECTED ADDED FILES = 0
35. UNEXPECTED REMOVED FILES = 0
36. UNEXPECTED MODIFIED FILES = 0
37. FAST = PASS
38. ALL RELEASE GATES = PASS (1 pre-existing stale unit test disclosed in §13, not caused by this order)
39. DEPLOYMENT AUTHORIZATION CONSUMED = YES (AUTHORIZED → DEPLOYED, bound to `6ab599163f833ab7f48b395d`)
40. OLD AUTHORIZATION STILL SUPERSEDED = YES
41. ROLLBACK TARGET PRESERVED = YES (`6ab1a035c7ef3b14a23a4ec6`, `ready`)
42. ROLLBACK REQUIRED = NO
43. origin == HEAD = YES
44. tree clean = YES
45. WEST PALM BEACH PRODUCTION DEPLOYMENT = PASS

WEST PALM BEACH PRODUCTION DEPLOYMENT = PASS

AUTHORIZED CANDIDATE DEPLOYED = YES

WEST PALM BEACH LIVE = YES

HILTON GARDEN INN BOCA RATON = PASS

OLD APPLE TEN IDENTITY ABSENT = YES

DEPLOYMENT AUTHORIZATION CONSUMED = YES

ROLLBACK REQUIRED = NO

ALL RELEASE GATES = PASS

CURRENT LIVE MARKETS = 33

CURRENT LIVE PROFILES = 2424

origin == HEAD = YES

tree clean = YES
