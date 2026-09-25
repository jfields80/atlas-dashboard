# PTF-JACKSONVILLE-FL-PRODUCTION-DEPLOYMENT-004 — FINAL

**JACKSONVILLE / NORTHEAST FLORIDA IS LIVE.** Deploy `6ab6c8798bd9daf5038ae3e5`.

Production serves **34 markets / 2,519 profiles / 2,807 release-index routes / 2,874 served routes**.
The exact founder-authorized candidate was deployed with **no rebuild and no reseal**.
**ROLLBACK REQUIRED = NO.**

---

## 1 — PREDEPLOY LIVE, REVERIFIED IMMEDIATELY BEFORE THE CALL

| | |
|---|---|
| PREDEPLOY LIVE SOURCE COMMIT | `e3efa2210f759886aaad830b07fa241231a8f734` |
| PREDEPLOY LIVE DEPLOYMENT | `6ab599163f833ab7f48b395d` (west-palm-beach-fl) |
| PREDEPLOY LIVE BUNDLE | `23728b4bff71c66d0a9a063de3882d744f92465f5f568f72b3caf16ca8641d78` |
| PREDEPLOY LIVE SITEMAP | `8ae34cea1c7e384f0f4c8499066c5ff2f9ca841d099c344a5860041b4b6c7546` |
| PREDEPLOY LIVE MARKETS / PROFILES | **33 / 2,424** |
| PREDEPLOY LIVE RELEASE-INDEX ROUTES | **2,701** (derived from the 33 committed contracts) |
| PREDEPLOY LIVE SERVED ROUTES | **2,767** (fetched from the host) |
| HOST VERIFIED | **true** |

The parent had **not** advanced since the authorization. The comparison artifact `C:\t\wpb6a` was proved to BE
current live rather than assumed: its route set is **identical** to the host's, and its sitemap hashes to the same
`8ae34cea…` production served.

## 2 — DEPLOYMENT AUTHORIZATION, RESOLVED FROM COMMITTED DATA

| | |
|---|---|
| AUTHORIZATION | `ptf-auth-jacksonville-003-f82f0714db2d` |
| STATUS BEFORE / CONSUMED / DEPLOY_ID | **AUTHORIZED / NO / NONE** |
| MARKET | `jacksonville-fl`, present in the bound set |
| authorized bundle_sha256 | `f82f0714db2dd4d714b6b789c68492f60de8a1f3287a11b1e6f1afd680cf0c4e` |
| authorized sitemap_sha256 | `d34b0e5d7d5ed045a3f727e49f18e2fe61de3df108e9ef0666c5413d1bb48e4f` |
| authorized package | `pkg-jacksonville-fl-60ba2edccd4882b3` |
| authorized source commit | `e7e02d4394dde29e949c13cf06732f3f7d69dc5f` |
| parent deployment / rollback target | `6ab599163f833ab7f48b395d` / `6ab599163f833ab7f48b395d` |
| bound release contracts | 34 |
| existing Jacksonville deployment records | **0** |

Full hashes were read from the committed authorization document, never from abbreviated console output.

### `verify_authorization` failed first, and that was the documented ordering — not a defect

On first load it returned a long list of problems, and **every one** was the authorization being compared against
`global_deployment_manifest.json`, which still described West Palm Beach production: *"bundle_sha256:
authorization binds f82f0714…, artifact has 23728b4b…"*, *"total_profiles: binds 2519, artifact has 2424"*,
*"participating_markets: … artifact has [… without jacksonville-fl]"*.

This order's own Phase 8 exists to fix exactly that, and the same thing happened at Miami. The substantive
bindings — status, consumption, market, bundle, sitemap, parent, rollback — were all correct from the start.
After Phase 8 wrote the live manifest **from the authorized bytes**, both `verify_authorization` and
`deployability_problems` returned `[]`. **The candidate was never touched to make a check pass.**

## 3 — CANDIDATE INTEGRITY: THE EXACT AUTHORIZED BYTES

| | Authorization | `C:\t\jax3a` |
|---|---|---|
| bundle_sha256 | `f82f0714…0c4e` | **identical** |
| sitemap_sha256 | `d34b0e5d…8e4f` | **identical** |
| `site/sitemap.xml` hashed from disk | — | **`d34b0e5d…8e4f`** |

| | |
|---|---:|
| MARKETS | **34** |
| PROFILES | **2,519** (summed from the bundle's own fragments) |
| RELEASE-INDEX ROUTES | **2,807** (2,519 hotels + 254 corridors + 34 hubs) |
| SERVED ROUTES | **2,874** |
| FILES | **15,342** (site directory and hash manifest agree) |
| broken links · collisions · global shadowing · canonical violations | **0 · 0 · 0 · 0** |

**CANDIDATE INTEGRITY = PASS.** Nothing was rebuilt, resealed or regenerated.

## 4 — ROUTE AND FILE DELTA, BY SETS AND BYTES

```
PRIOR SERVED ROUTES LOST : 0
ROUTES ADDED             : 107
  of which jacksonville-fl : 107
  NOT jacksonville-fl      : 0
```

| | |
|---|---:|
| FILES ADDED | **582** — every one Jacksonville |
| FILES REMOVED | **0** |
| FILES CHANGED | **1** |
| the changed file | **`sitemap.xml`** |
| UNEXPLAINED PRIOR-MARKET FILE CHANGES | **0** |
| `jacksonville-nc` files / bytes changed | 99 / 99 · **0** |

Measured **two independent ways** — the builds' own `file_hash_manifest.json` files, and a full byte-level walk of
both 15k-file site trees. Both agree exactly.

### Netlify uploaded 584 files; the local delta is 583. The difference is Netlify's, not the artifact's

582 added + 1 changed = **583** files differ between the parent artifact and the authorized candidate. Netlify
reported *"CDN requesting 584 files"*. Its CDN diff runs against its own stored deploy state, not against my
comparison artifact, so the count is Netlify-side accounting. What matters is what is **served**, and that is
proven below: the host sitemap hashes to the authorized value and 20/20 sampled pages are byte-identical to the
artifact. `_headers` and `_redirects` are byte-identical locally and are consumed by Netlify as configuration
rather than served (both return 404), so neither is a content change.

## 5 — PUBLICATION SAFETY

| | |
|---|---:|
| APPROVED JACKSONVILLE PROFILES | **95** |
| seed rows in the authority shard | **95** |
| UNAPPROVED / HELD PROFILES IN CANDIDATE | **0** |
| **KINGS AVENUE DUAL-BRAND PUBLISHED** | **NO** |

Held rows present as candidate routes: **0**. Kings Avenue routes in the candidate: **0**; files: **0**. No
`identity_resolutions.json` ruling was added during deployment.

## 6 — GEOGRAPHY SAFETY

| | |
|---|---|
| **AMELIA ISLAND REMAINS CORRIDOR** | **YES** — tier `CORRIDOR`, postal codes 32034/32035, serving `/pet-friendly-hotels/jacksonville-fl/amelia-island-fernandina-beach/` |
| amelia-island standalone market document | **does not exist** |
| **ST AUGUSTINE ADMITTED** | **0** — 32080, 32084, 32086, 32092, 32095 all classify `OUTSIDE`, none in the 47 admitted codes |
| corridors registered / admitted postal codes | 17 / 47 — **unchanged** |
| geography changed by this order | **NO** |

**A correction worth recording.** My first St. Augustine check printed "ADMITTED: 5". That was my test, not the
geography: `classify_postal` returns a 3-tuple whose first element is the class **string**, and `'OUTSIDE'` is
truthy, so a naive truth test counted every refusal as an admission. Re-checked properly, all five codes are
`OUTSIDE` and none appears in the admitted set.

## 7 — CROSS-MARKET COLLISION SAFETY

| | |
|---|---:|
| **JACKSONVILLE-NC COLLISIONS** | **0** (seed↔seed, seed↔exclusion, exclusion↔seed, exclusion↔exclusion) |
| **BARE-CHAIN CROSS-MARKET COLLISIONS** | **0** |
| **ANY-MARKET DUPLICATE EXCLUDED IDENTITIES** | **0** |

`jacksonville-nc` — a **live** market sharing this one's city name, against a registry that matches a normalised
name before it looks at an address — is **byte-identical**: 99 files, 0 changed; 19 served routes, identical set;
16 profiles, unchanged. No existing live profile was displaced.

## 8 — LIVE MANIFEST

`global_deployment.write_manifest()` was run on `C:\t\jax3a\global_bundle_manifest.json` — the authorized bytes,
not a recomposition. The live manifest now describes **34 markets / 2,519 / 2,874**, bundle `f82f0714…`, sitemap
`d34b0e5d…`, `source_commit e7e02d43`. `verify_manifest []`, and it is **byte-identical** (LF-normalised) to the
committed candidate manifest `global_deployment_manifest_candidate_jacksonville_003.json`.

## 9 — THE DEPLOYMENT

```
netlify deploy --prod --no-build --dir C:\t\jax3a\site --site pettripfinder-prod

DEPLOY START    = 2026-09-25T19:14:41.27Z
DEPLOY COMPLETE = 2026-09-25T19:16:45.98Z        (125 s)        EXIT STATUS = 0
NETLIFY DEPLOYMENT ID = 6ab6c8798bd9daf5038ae3e5
DEPLOY URL  = https://pettripfinder.com
unique URL  = https://6ab6c8798bd9daf5038ae3e5--pettripfinder-prod.netlify.app

CDN requesting 584 files -> Finished uploading 584 assets -> Deploy is live!
```

`--no-build`: Netlify built nothing and the site was not regenerated. One deploy command, run once.

Netlify's own API confirms the lineage: published deploy **`6ab6c8798bd9daf5038ae3e5`**, `state: ready`,
`context: production`, `published_at 2026-09-25T19:16:36.816Z`, and the **previous** deploy is
`6ab599163f833ab7f48b395d` — the authorized parent.

## 10–13 — HOST VERIFICATION (`jacksonville_fl_live_verification_004.json`, **15/15 PASS**)

The host is the authority, not the deploy command.

| | |
|---|---|
| **HOST SITEMAP SHA** | `d34b0e5d7d5ed045a3f727e49f18e2fe61de3df108e9ef0666c5413d1bb48e4f` |
| **AUTHORIZED CANDIDATE SITEMAP SHA** | `d34b0e5d7d5ed045a3f727e49f18e2fe61de3df108e9ef0666c5413d1bb48e4f` |
| **HOST SITEMAP MATCH** | **PASS** |
| served route SET identical to authorized | **true** |
| **LIVE MARKETS** | **34** |
| **LIVE PROFILES** | **2,519** |
| **LIVE RELEASE-INDEX ROUTES** | **2,807** |
| **LIVE SERVED ROUTES** | **2,874** |

| Gate | Result |
|---|---|
| sitemap_is_authorized | **PASS** |
| served_route_set_is_authorized | **PASS** |
| every_jacksonville_route_200 | **PASS** — 107/107, 0 missing |
| no_parent_route_lost | **PASS** — 0 lost |
| every_prior_route_200 | **PASS** — **2,767/2,767 refetched 200**, 0 non-200 |
| only_jacksonville_added | **PASS** — 107 added, all Jacksonville |
| served_bytes_are_authorized_bytes | **PASS** — **20/20** sampled pages byte-identical |
| held_identities_404 | **PASS** — 32 probed, all 404 |
| kings_avenue_withheld | **PASS** — 404/404 |
| amelia_island_is_a_corridor | **PASS** |
| st_augustine_absent | **PASS** — 0 routes |
| name_twin_unchanged | **PASS** |
| detroit_withheld | **PASS** — 404, 0 routes in the live sitemap |
| host_publishes_this_deploy | **PASS** — `ready` |
| host_previous_deploy_is_the_parent | **PASS** |

**Jacksonville's 107 live routes**: 95 hotel profiles + 10 corridor pages + the market hub + the
policy-comparison page. **Release-index 106 / served 107** — the +1 is the comparison page, which is served but
not market-owned.

Spot checks, all 200: west-palm-beach-fl, fort-lauderdale-fl, augusta-ga, miami-fl, tampa-fl, orlando-fl,
cleveland-akron-canton, jacksonville-nc, jacksonville-fl. Detroit **404**.

Byte-identity sample (20 pages): the apex, the category root, `robots.txt`, `llms.txt`, Jacksonville's hub,
comparison page and Amelia corridor, six Jacksonville hotel profiles, and the hubs of west-palm-beach-fl,
fort-lauderdale-fl, augusta-ga, miami-fl, tampa-fl, orlando-fl and jacksonville-nc — **all identical to the
authorized artifact**.

### Two false alarms, both mine, both worth recording

**"All 107 Jacksonville routes non-200."** I wrote the route list with Python's default text mode on Windows, so
every URL carried a trailing `\r` and curl returned `000` — a connection failure, not an HTTP status. Direct
fetches were 200 the whole time. Rewritten with LF: **107/107**.

**"PRIOR 200=2211 NOT200=550" with zero failures recorded.** Internally impossible — and 2211+550=2761, not
2767. My earlier `pkill` had not actually killed the first (CRLF) sweep, so **two** sweeps were writing to the
same files and one truncated the other. I refused to act on contaminated evidence in either direction, killed
both processes, verified none remained, and re-ran **one** sweep with a self-consistency check built in:
`total=2767 ok=2767 bad=0 lines=2767`, single distinct status code `200`. The set comparison had already proved
independently that no route was lost; this is the confirmation that they serve.

## 14 — FAST / RECEIPT SAFETY

| | |
|---|---|
| currently eligible receipts for the deployed package | **1** |
| **RULE J NONEMPTY** | **PASS** — file_count 603, html_count 587, defects `[]` |
| **RULE K NONVACUOUS** | **PASS** — BYTE_IDENTICAL |
| bundle | `a98efbea…` — not `e3b0c442…` |
| Augusta's historical empty receipt | on disk, **NOT currently eligible** (`EMPTY_BUNDLE`, `NO_HTML_OUTPUT`) |

No vacuous historical receipt qualifies, and Augusta's receipts were not modified.

## 15 — POSTDEPLOY QUALITY

| | |
|---|---:|
| BROKEN LINKS | **0** |
| COLLISIONS | **0** |
| CANONICAL VIOLATIONS | **0** |
| GLOBAL SHADOWING | **0** |
| UNEXPECTED DELTA | **`[]`** (market, profile, route and served-route all empty) |

No broad regression was run.

## 16 — DEPLOYMENT STATE FINALIZED

Only after host verification passed:

| | |
|---|---|
| **AUTHORIZATION CONSUMED** | **YES** — `AUTHORIZED` → **`DEPLOYED`**, consumed deployment_id `6ab6c8798bd9daf5038ae3e5` |
| deployment record | `ptf-deploy-jacksonville-004-6ab6c8798bd9daf5038ae3e5`, `verify_record []`, final_status **DEPLOYED**, `rollback_used false`, `exit_status 0` |
| deployment pin | moved to `6ab6c8798bd9daf5038ae3e5`; **live and source agree**, so `ahead_of_production false`, `moved_by null` |
| supersessions chain | **29 → 30** entries |
| **JACKSONVILLE PARTICIPATION** | `FOUNDER_AUTHORIZED_FOR_LAUNCH` — untouched by this order |

**The supersessions chain was extended, not rewritten**, in the three canonical steps: `reviewed_by` became this
order; West Palm Beach's entry stopped calling itself current and became historical naming the deploy that
replaced it; Jacksonville was **appended** as the new CURRENT entry. Both authorizations' bound release contracts
were re-hashed — **33 and 34 contracts, 0 drift on either**. A silent hash change there would be a market moving
under a live authorization.

The deployment record names **two orders**, as the contract requires: `work_order` is the authorizing order
(`…FOUNDER-LAUNCH-AUTHORIZATION-003`) and `deployer.work_order` is this one.

**The resolver now agrees**, from the committed record: `CURRENT_LIVE_SOURCE_COMMIT e9a059e5`,
`built_from e7e02d43`, `live_deploy_id 6ab6c8798bd9daf5038ae3e5`, 34 markets, 2,519 profiles, 2,874 routes,
`host_verified true`.

## 17 — ROLLBACK

**ROLLBACK REQUIRED = NO.** No critical failure occurred: no hash mismatch, no sitemap mismatch, no Jacksonville
route loss, no prior route or profile loss, no held-property publication, no collision, no canonical violation,
no unexpected delta, no accounting mismatch. The rollback target `6ab599163f833ab7f48b395d` stands unused and is
recorded in the pin and the record.

## 18 — FINAL PRODUCTION ACCOUNTING

| | |
|---|---:|
| **LIVE MARKETS** | **34** |
| **LIVE PROFILES** | **2,519** |
| **LIVE RELEASE-INDEX ROUTES** | **2,807** |
| **LIVE SERVED ROUTES** | **2,874** |
| **JACKSONVILLE PROFILES LIVE** | **95** |
| **JACKSONVILLE RELEASE-INDEX ROUTES** | **106** |
| **JACKSONVILLE SERVED ROUTES** | **107** |
| **PRIOR MARKETS PRESERVED** | **33 / 33** |
| **PRIOR PROFILES LOST** | **0** |
| **PRIOR ROUTES LOST** | **0** |

---

## FINAL ANSWERS

```
 1. PREDEPLOY LIVE DEPLOYMENT      = 6ab599163f833ab7f48b395d (west-palm-beach-fl)
 2. PREDEPLOY LIVE BUNDLE          = 23728b4bff71c66d0a9a063de3882d744f92465f5f568f72b3caf16ca8641d78
 3. DEPLOYMENT AUTHORIZATION       = ptf-auth-jacksonville-003-f82f0714db2d
 4. AUTHORIZATION STATUS BEFORE    = AUTHORIZED (unconsumed, deploy_id NONE)
 5. AUTHORIZED CANDIDATE BUNDLE    = f82f0714db2dd4d714b6b789c68492f60de8a1f3287a11b1e6f1afd680cf0c4e
 6. AUTHORIZED CANDIDATE SITEMAP   = d34b0e5d7d5ed045a3f727e49f18e2fe61de3df108e9ef0666c5413d1bb48e4f
 7. CANDIDATE INTEGRITY            = PASS (bundle and sitemap both exact; 34/2519/2807/2874;
                                     15,342 files; 0 broken links / collisions / shadowing /
                                     canonical violations)
 8. NETLIFY DEPLOYMENT ID          = 6ab6c8798bd9daf5038ae3e5
 9. NETLIFY RESULT                 = SUCCESS, exit 0, 125 s, 584 assets uploaded,
                                     state ready / context production
10. HOST SITEMAP MATCH             = PASS (byte-identical to the authorized sitemap)
11. LIVE MARKETS                   = 34
12. LIVE PROFILES                  = 2,519
13. LIVE RELEASE-INDEX ROUTES      = 2,807
14. LIVE SERVED ROUTES             = 2,874
15. JACKSONVILLE PROFILES LIVE     = 95
16. JACKSONVILLE RELEASE-INDEX     = 106
17. JACKSONVILLE SERVED ROUTES     = 107
18. JACKSONVILLE ROUTES HTTP 200   = 107 / 107 (0 missing)
19. UNAPPROVED JACKSONVILLE
    PROFILES ERRONEOUSLY LIVE      = 0 (32 held rows probed, all 404)
20. KINGS AVENUE DUAL-BRAND
    PUBLISHED                      = NO (both halves 404; no identity_resolutions.json ruling)
21. AMELIA ISLAND REMAINS CORRIDOR = YES (corridor page live; no standalone market document)
22. ST AUGUSTINE ADMITTED          = 0
23. JACKSONVILLE-NC COLLISIONS     = 0 (and 0 bytes of jacksonville-nc changed)
24. BARE-CHAIN COLLISIONS          = 0
25. PRIOR MARKETS LOST             = 0
26. PRIOR PROFILES LOST            = 0
27. PRIOR ROUTES LOST              = 0 (2,767/2,767 refetched 200)
28. DETROIT STILL WITHHELD         = YES (404; 0 routes in the live sitemap)
29. RULE J NONEMPTY                = PASS (603 files / 587 html / 0 defects)
30. RULE K NONVACUOUS              = PASS (BYTE_IDENTICAL)
31. BROKEN LINKS                   = 0
32. COLLISIONS                     = 0
33. CANONICAL VIOLATIONS           = 0
34. GLOBAL SHADOWING               = 0
35. UNEXPECTED DELTA               = [] (market, profile, route, served route)
36. DEPLOYMENT AUTHORIZATION
    CONSUMED                       = YES (AUTHORIZED -> DEPLOYED)
37. JACKSONVILLE PARTICIPATION     = FOUNDER_AUTHORIZED_FOR_LAUNCH (untouched)
38. ROLLBACK REQUIRED              = NO
39. CURRENT LIVE DEPLOYMENT        = 6ab6c8798bd9daf5038ae3e5
40. CURRENT LIVE BUNDLE            = f82f0714db2dd4d714b6b789c68492f60de8a1f3287a11b1e6f1afd680cf0c4e
41. origin == HEAD                 = YES
42. tree clean                     = YES
43. JACKSONVILLE LIVE              = YES
```

### Answers 41 and 42 were measured after the push, not pre-written

```
$ git push                       # f6e28a42..754b0b3d
$ git fetch origin worker/ptf-jacksonville-fl-market-001
$ git rev-parse HEAD             -> 754b0b3dd7b07219f0ac84d54849af4779c2f632
$ git rev-parse origin/worker/ptf-jacksonville-fl-market-001
                                 -> 754b0b3dd7b07219f0ac84d54849af4779c2f632
origin == HEAD : YES
$ git status --porcelain         # no output
tree clean : YES
```

This document is committed and pushed on top, and both checks are re-run against that commit; both still hold.

| Commit | What it holds |
|---|---|
| `f6e28a42` | the authorized, undeployed candidate (order 003) |
| `e9a059e5` | **JACKSONVILLE LIVE** — live manifest, deployment record, consumed authorization, pin, supersessions |
| `754b0b3d` | this report |

### Processes and temporary state

The two hung whole-site assembly processes from the authorization order were terminated after their outputs were
verified stable. All route-sweep shells were stopped and confirmed gone. The deploy process exited on its own
(exit 0). The one pre-existing Python process on this machine (`C:	\sink.py`, started 2026-09-14 by another
session) was **not** touched. The authorized artifact `C:	\jax3a` is deliberately retained: it is now the LIVE
artifact and the comparison parent for the next market.

---

## THE MARKET THAT WENT LIVE

Jacksonville / Northeast Florida is the **34th** PetTripFinder market: **95 published profiles** over **10
publishing corridors**, built from zero in 3h23m and taken from nothing to live across four orders without a
single broad regression run.

What it publishes is shaped by decisions that are all on the record. **Downtown Jacksonville does not get a
corridor page** — it carries 5 of the market's 258 hotel-rank licences, under 2 %, and it sits below the
publication minimum alongside six other corridors that were **not forced**. **JAX airport does** — 32218 is the
market's largest hotel-rank code, the first Florida airport to earn one. **St. Augustine is refused entirely**,
148 hotel-rank licences preserved for a market of its own rather than absorbed into this one. **Amelia Island
publishes as a corridor**, not a market, by explicit founder decision — and it is the named first candidate for
promotion later.

Two hotels at **1201 Kings Avenue** are live nowhere: a dual-brand building is two hotels, resolving it needs a
reviewed entry in shared data, and the founder chose to hold both rather than have that signature invented. They
return 404 in production today, and the next order can release them with one reviewed edit.

And the market's defining hazard never materialised in production: **`jacksonville-nc` is untouched, byte for
byte** — 99 files, 19 routes, 16 profiles, zero changed — even though a shared registry that matches names before
addresses had every opportunity to confuse the two.
