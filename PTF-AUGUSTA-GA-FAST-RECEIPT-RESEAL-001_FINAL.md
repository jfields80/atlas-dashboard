# PTF-AUGUSTA-GA-FAST-RECEIPT-RESEAL-001 — FINAL

Branch `worker/ptf-augusta-fast-receipt-reseal-001`, base `f182cc08`
(`origin/worker/ptf-fast-nonempty-bundle-guard-001`, the Rule J non-empty guard). Market `augusta-ga`.

## Outcome in one paragraph

The vacuous receipt is real and was found mechanically. The Augusta package's **real** market-local
build is non-empty and deterministic: 94 files, 78 HTML, bundle `2dfb9afb…`, byte-identical across two
independent builds at short absolute paths, and its 17 Augusta routes equal the 17 live Augusta routes.
**The receipt was not resealed, and no corrective receipt was written.** Phase 3 found the old
receipt is **historical immutable evidence**: its `RECEIPT_DIGEST` is one of *the digests this
authorization binds* in the founder authorization packet 005, which the deployed authorization
`ptf-auth-augusta-006` names word for word. The receipt schema
`ptf-fast-release-receipt/1.0` and its reader have **no supersession or correction mechanism**, so a
second receipt cannot displace the first. The order's rule for that case is *STOP and report the
minimal new representation*. That is what this report does (§8). Nothing in the repository changed
except this report. Production was not touched and nothing was deployed.

---

## Phase 1 — Current verified live (before)

`python -m scripts.pettripfinder.release_index live-source --verify-host` + `release_index.live_index()`:

| | |
|---|---|
| RESOLVED | YES, 0 problems, 230 refs scanned |
| CURRENT LIVE SOURCE COMMIT | `e82120cce7e48c62d3c1057a6c82785bed920485` (built from `0cc2817b`) |
| CURRENT LIVE DEPLOYMENT | `6ab1a035c7ef3b14a23a4ec6` (`ptf-deploy-fort-lauderdale-004-…`) |
| CURRENT LIVE BUNDLE | `0ec5c6557d79eaf77a4065b6700c0a5807e9bfe282408dd4779804b33af3a40f` |
| CURRENT LIVE SITEMAP | `e81961ae76454ce608fcb39624d5147c8779f52b269faab9449138397cb8fa3d` |
| CURRENT LIVE MARKETS | 32 |
| CURRENT LIVE PROFILES | 2375 |
| CURRENT LIVE RELEASE-INDEX ROUTES | 2646 (live index digest `sha256:74c368f2…`, 0 problems) |
| CURRENT LIVE SERVED ROUTES | 2711 (host sitemap HTTP 200, sha256 = `e81961ae…`) |
| HOST VERIFIED | YES |

Augusta is served: participating, 14 profiles on the live record, **17/17 sitemap routes HTTP 200**.
Fort Lauderdale: 97/97 routes 200. Detroit and West Palm Beach are not participating and their hubs are 404.

## Phase 2 — The vacuous receipt (located on disk, not from memory)

| | |
|---|---|
| RECEIPT PATH | `atlas-dashboard/launch_packages/pettripfinder/markets/receipts/augusta-ga/pkg-augusta-ga-14806eca154760a0-5f8116aaecd97d09.json` (file sha256 `a2e22ce8ca4f74e1…`, identical to the HEAD blob) |
| RECEIPT DIGEST | `sha256:5f8116aaecd97d0948810aab759a1670ce99cb7ce81b27adc7691bf87dafbe80` |
| PACKAGE ID | `pkg-augusta-ga-14806eca154760a0` |
| PACKAGE DIGEST | `sha256:14806eca154760a0a9dc59b200b4fa83e4f748b4ebc8eba197eab8d1e50c0df6` |
| SOURCE COMMIT | package sealed from `ba80b69266a8…`; receipt committed in `e56cc7eb` (2026-09-16, "reseal augusta-ga against the current Tampa-live parent") |
| PARENT RELEASE | Tampa-live `6aab379e0777c9ee96702a4f`, parent source `9c63dabd…`, live index `sha256:0adab72c…` |
| RULE J STATUS | **PASS** |
| RULE J FILE COUNT | **0** |
| RULE J HTML COUNT | **0** |
| RULE J BUNDLE SHA | **`e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855`** (sha256 of the empty string) |
| RULE K STATUS | **PASS** |
| RULE K DETERMINISM RESULT | **BYTE_IDENTICAL**: `output_digest_a` = `output_digest_b` = `e3b0c442…` |
| RECEIPT VERDICT | ELIGIBLE YES, 15/15 PASS, 0 UNKNOWN, 0 FAILED |

**Historical defect confirmed:** file_count 0, html_count 0, bundle `e3b0c442…`, J PASS, K PASS/BYTE_IDENTICAL.
The J detail's `release_name` is `package-augusta-ga-ba80b69-…`, which carries a git sha. That means the
original stage lived inside the repository. This fits the relative-`--work` double-join recorded by the
guard order, but the original work path was never written down, so the cause is **consistent, not
proven**.

## Phase 3 — Historical immutability

Every inbound reference in the tree (`git grep` of the receipt digest, the package digest and the
receipts path):

| Referrer | Binds | Kind |
|---|---|---|
| `markets/reports/augusta_ga_founder_authorization_packet_005.json` → `the_digests_this_authorization_binds.validation_receipt_digest` | **receipt digest `5f8116aa…`**, package digest, 7 input digests | **founder authorization packet** |
| `deploy/netlify/deployment_authorizations/ptf-auth-augusta-006-55e0f5bbf02a.json` (status **DEPLOYED**) | "I explicitly AUTHORIZE augusta-ga only under the exact committed founder packet: …packet_005.json" + package digest | **deployment authorization** |
| `markets/reports/augusta_ga_registration_release_lane.json` → `fast_lane_receipt` | receipt **path** and receipt digest | registration release-lane report |
| `release_production_gate.json` (Augusta entry, CONSUMED) | package digest | production gate record |
| `markets/reports/augusta_ga_launch_report_006.json` | package id and digest | launch report |
| `scripts/pettripfinder/augusta_ga_deployment_authorization_006.py`, `augusta_ga_launch_participation_006.py` | package digest | authorizing and participation helpers |
| `deploy/netlify/deployment_records/ptf-deploy-augusta-006-6aaeb3b7384e1bb712adb084.json` | the auth 006 → bundle `55e0f5bb…` chain (no direct receipt reference) | deployment record |
| `markets/packages/augusta-ga/pkg-augusta-ga-14806eca154760a0.json` | the package itself; immutable by `SMP.write_sealed` | package registry |
| `PTF-FAST-NONEMPTY-BUNDLE-GUARD-001_FINAL.md` | receipt path, as the known vacuous example | report |

The release contract, the launch participation decision, `supersessions.json`, the current-live pin
and the rollback records carry **no** reference to this receipt or package.

**Determination: B, historical immutable evidence.** The founder authorization packet lists the
receipt digest under *the digests this authorization binds*, and the deployed authorization is bound
to that packet. Regenerating the receipt in place would change the bytes behind a digest that a
consumed founder authorization names. Whether the receipt is rewritten in place or deleted, that
authorization's evidence chain breaks. **The receipt is preserved byte-for-byte.**

**Is there a schema-supported corrective mechanism? No.** Checked mechanically:

1. `ptf-fast-release-receipt/1.0` (`fast_release_lane._receipt`) has no `SUPERSEDES`, `CORRECTS`,
   `REVOKED` or replay field. `EXPIRY_REVOCATION_CONDITIONS` is free text.
2. Receipts are content-addressed (`<package_id>-<receipt digest[:16]>.json`, `write_receipt`).
   A second receipt for the same package is a *second file*, not a successor.
3. The reader `fast_release_lane.eligible_receipts` returns **every** receipt that says ELIGIBLE = YES.
   It never checks rule J's counts, so today it returns the vacuous receipt (verified:
   `eligible_receipts('augusta-ga', 14806eca…)` → `[…-5f8116aaecd97d09.json]`). Every consumer
   (`release_coordinator.bound_fast_receipt`, `registration_data_only.check_fast_receipt`,
   `regression_delta.fast_data_only_release`) picks `sorted(paths)[-1]`. That is the **lexical order
   of the digest hex**, not time and not supersession.
4. `evidence_revocations.json` revokes evidence *artifacts*, not receipts. `sealed_market_package`
   says a correction is a new *package*. The re-registration lane (`4cbe6e4c`) serves only markets
   that are authorized and **never deployed**, and Augusta is live.
5. A fresh lane run for this package **cannot** be ELIGIBLE today. Its parent is Tampa-live, so rule N
   correctly reports a stale parent, and rule I sees Augusta already live (Phase 6). A corrected
   receipt written with `write_receipt` would say ELIGIBLE **NO**. `eligible_receipts` would skip it,
   and the vacuous receipt would remain the only "eligible" one. Writing it would not repair anything.
   It would also add a second receipt that marks the package as failing I and N purely because time
   has passed.

So the order's branch applies: **STOP. Do not invent an ad hoc file.** Phases 4–7 are read-only, so
they were still run: they produce the proof that the minimal representation in §8 would record.

## Phase 4 — Augusta source inputs (read-only)

`market_package_writer.inputs_from_committed_market('augusta-ga')` re-hashed the committed inputs at HEAD:

| input | package digest | HEAD |
|---|---|---|
| census | `163f7d0a191f6c27…` | SAME |
| exclusions | `e5cca7e91ad9f5d3…` | SAME |
| market (geography) | `068aa70b34253527…` | SAME |
| partition | `31470bdb86415ae7…` | SAME |
| policy_package | `9c5c748d92bd86e0…` | SAME |
| routing | `1e1e277e39d72bf3…` | SAME |
| seed | `0efdce74ec66d654…` | SAME |

`SMP.read_sealed` re-derives the package digest. **AUGUSTA SOURCE DATA CHANGES = 0.** No reacquisition was needed.

## Phase 5 — Paths (short, absolute, resolved once)

Runner: `aug_build.py` (session scratchpad, not committed). It refuses a relative `--work`, a path over
12 characters, or a non-empty directory. It resolves the path once, and records the assembler's own
`validate_output_path` result next to the collector root (`<output>/site`) that `build_changed_market`
hashes.

| | Build A (FAST lane, J) | K's second build (same lane) | Build B (independent process) |
|---|---|---|---|
| WORK DIRECTORY | `C:\t\agr1a` | `C:\t\agr1a` | `C:\t\agr1b` |
| ASSEMBLER OUTPUT DIRECTORY | `C:\t\agr1a\oa` | `C:\t\agr1a\ob` | `C:\t\agr1b\oa` |
| COLLECTOR DIRECTORY | `C:\t\agr1a\oa\site` | `C:\t\agr1a\ob\site` | `C:\t\agr1b\oa\site` |
| OUTPUT DIRECTORY EXISTS | true | true | true |

The assembler logged `output path: C:\t\agr1a\ob\.assemble_work\generated` and
`C:\t\agr1b\oa\.assemble_work\generated`, with no doubled path. Collector and assembler agree.

## Phase 6 — Non-empty Rule J (the corrected `f182cc08` lane)

`fast_release_lane.run_fast_lane(package, work_dir=C:\t\agr1a)` against current live:

| | |
|---|---|
| RULE J | **PASS**, `output_defects: []`, `output_present: true`, gates failing 0 |
| FILE COUNT | **94** |
| HTML COUNT | **78** |
| BUNDLE SHA256 | **`2dfb9afbab9447006af210675aaeeb7c61c2b7eecc93f4dcb9dac8037fdd3f1c`** (not `e3b0c442…`) |
| cache events | `generator_site` BUILD_EXECUTED, `market_bundle` BUILD_EXECUTED (cold) |
| contract sha256 | `710cdc1b2805fa1b…`, **identical to the historical receipt's**, so the same staged market contract was built |
| staged input digest | `bcba744b…` (historical `2612c2b2…`). Staged inputs include the *registry of every market*, and that registry has since gained Miami, Fort Lauderdale and West Palm Beach. The Augusta inputs themselves are the same (Phase 4) |

The same run gave rules A–H, J, K, L, M, O **PASS** and **I, N FAIL**. That is correct behaviour for a
historical package, not a package defect:

* N: `live_deploy_id: package parent 6aab379e…, live 6ab1a035…` (plus rollback target, source commit,
  totals, participation and index digest). The package's parent is Tampa-live. Production has moved on
  by three deployments (Augusta, Miami, Fort Lauderdale).
* I: `expected_market_count_delta 1, actual 0`. Augusta already participates, so joining is a no-op.

That in-memory receipt (`RECEIPT_DIGEST sha256:e921ce9d…`, ELIGIBLE NO) was **not** written to
`markets/receipts/`.

## Phase 7 — Independent determinism

| | files | HTML | bundle sha256 |
|---|---|---|---|
| BUILD A (`C:\t\agr1a\oa`) | 94 | 78 | `2dfb9afbab9447006af210675aaeeb7c61c2b7eecc93f4dcb9dac8037fdd3f1c` |
| K second build (`C:\t\agr1a\ob`) | 94 | 78 | `2dfb9afb…` (lane K: PASS, BYTE_IDENTICAL, 4 cold builds, 0 reuse) |
| BUILD B (`C:\t\agr1b\oa`, separate process) | 94 | 78 | `2dfb9afbab9447006af210675aaeeb7c61c2b7eecc93f4dcb9dac8037fdd3f1c` |

The actual files were compared by per-file sha256, not only by manifest counts:
**A vs B differing files = 0**, **A vs K-second differing files = 0**, and no zero-byte files. Both
builds pass `bundle_output_defects` with `[]`. **BYTE_IDENTICAL = YES.**

Cross-check against production: the build's Augusta route set (hub, 14 profiles, `washington-road`,
`policy-comparison`) is **exactly** the 17 Augusta routes in the live host sitemap. The symmetric
difference is empty.

## Why production was never affected

The FAST receipt proves the **market-local** build that the registration lane runs. Augusta went live
through the **whole-site production assembler**: `ptf-auth-augusta-006` binds bundle `55e0f5bb…`
(13,188 files, 13,170 HTML), reproduced byte-identical across two build processes, deployed as
`6aaeb3b7…` and verified live. Today 17/17 Augusta routes return 200. The vacuous receipt showed that
one gate proved nothing. It did not show that anything shipped wrong. Phases 6–7 now show that the
package the gate should have proved does build a real, deterministic Augusta bundle, and that the
bundle carries the live route set.

## §8 — Corrective receipt: NOT WRITTEN (the minimal representation that is missing)

| | |
|---|---|
| OLD RECEIPT STATUS | preserved, byte-identical (`a2e22ce8…`). Still returned by `eligible_receipts` as ELIGIBLE = YES |
| CORRECTIVE RECEIPT STATUS | **NOT WRITTEN**: no schema-supported mechanism exists (Phase 3) |
| OLD RECEIPT PRESERVED | YES |
| SUPERSESSION / CORRECTION LINK | NONE. The schema has no field for one |

The **smallest** change that makes the vacuous receipt non-effective without touching history is a
**reader-side rule. No new file is needed**:

> `fast_release_lane.eligible_receipts` (and therefore `bound_fast_receipt`, `check_fast_receipt`,
> `regression_delta`) must refuse a receipt whose `RESULTS.J.detail` fails
> `bundle_output_defects(...)`, or whose `DETERMINISM_RESULT` rests on `e3b0c442…`. This is the same
> predicate `f182cc08` applies when a receipt is **written**, now applied when one is **read**.

With that rule the old receipt stays byte-identical, so the founder packet's digest and the auth 006
chain stay intact. It simply stops counting as ELIGIBLE. That is safe for Augusta: every gating
consumer already rejects this receipt, because they require the parent to be current live, and a
future Augusta change needs a new package sealed against the live parent, which the J guard will
check. This rule is a **FAST implementation change**, which this order forbids. It needs its own
order, with a focused test that shows the committed Augusta receipt is refused and the 22 non-empty
receipts are still accepted.

**Only if** the founder also wants the real J/K proof *recorded* for this historical package, a second
representation is needed. The minimum would be receipt schema `1.1` with an optional block such as
`CORRECTS: {receipt_digest, defect: "RULE_J_EMPTY_BUNDLE", evaluation: "REPLAY_AT_RECORDED_PARENT"}`.
It would let rules G/H/I/N be evaluated against the package's *recorded* parent index (`0adab72c…`)
rather than current live, and the reader would honour the link. Without the replay flag, a corrected
receipt either fails N/I (Phase 6) or falsely claims N ("the parent IS current live") for a parent
that is three deployments old. The numbers it would carry are the ones in Phases 6–7.

## Phase 9 — Lineage safety

`git diff f182cc08` over the tree is empty apart from this report.

| | |
|---|---|
| HISTORICAL PACKAGE DIGEST INVALIDATED | NO (`read_sealed` re-derives `14806eca…`) |
| HISTORICAL AUTHORIZATION INVALIDATED | NO (packet 005 and `ptf-auth-augusta-006` unchanged, status DEPLOYED, receipt digest still resolves to its bytes) |
| DEPLOYMENT RECORD MODIFIED | NO (`ptf-deploy-augusta-006-6aaeb3b7…` unchanged) |
| CURRENT LIVE MODIFIED | NO |
| rollback lineage | resolver clean; current rollback target `6ab071a5…` (`ptf-deploy-miami-006-…`) present |

## Phase 10 — FAST verification

The applicable rules were run on the corrected lane. **J PASS, K PASS**, and every package-intrinsic
rule (A–F, L, M, O) PASS, with 0 UNKNOWN. G and H also PASS. The two parent-relative rules, **I and
N, FAIL against current live**, for the reasons in Phase 6. Answering them PASS needs the replay
representation in §8. So "all applicable rules PASS" holds for everything this repair concerns (J, K
and the package-intrinsic rules). It does **not** hold for a whole receipt, which is why no receipt
was written.

## Phase 11 — Targeted tests (one pytest process)

Modules (one detached process, output straight to a file):
`test_ptf_fast_nonempty_bundle_guard_001.py` (Rule J / Rule K guard), `test_atlas_throughput_003.py`
(the lane, J/K, the receipt, `eligible_receipts`), `test_atlas_throughput_004.py` (the J/K cache path),
`test_release_factory_bounded_repair_002.py` (`bound_fast_receipt`), `test_registration_data_only_001.py`
(`check_fast_receipt`, package and receipt binding), and `test_reregistration_lane_001.py`
(integrity of historical authorizations and supersessions).

| | |
|---|---|
| COLLECTED | 322 |
| PASSED | 309 |
| FAILED | 13 |
| SKIPPED | 0 |
| RUNTIME | 941.0 s |
| PEAK MEMORY | 149.6 MB working set (`throughput_profile.peak_working_set_mb`) |

**Differential by failure-set identity.** The same 13 nodes were re-run in a clean detached worktree
at base `f182cc08` (`C:\t\agrbase`, since removed): **the same 13 fail** (63 s).

| Node(s) | Class |
|---|---|
| `test_atlas_throughput_004::TestBoundaries::test_the_fast_lane_reports_market_build_required_no_on_a_trusted_bundle` (rule N on the Dayton fixture's stale parent; already classified in the guard order) | PRE_EXISTING |
| 12 × `test_registration_data_only_001` (`case_01`, `case_26`, `case_04`, `the_real_reissue`, `case_06`, `case_07`, `the_real_closure`, `the_real_pin_block`, `the_real_releases_scan_clean`, `the_real_package_and_receipt_bind`, `missing_a_required_output`, `an_unknown_check`) | PRE_EXISTING: "real tree" assertions pinned to the **Charlotte** registration ("rows must be the base rows plus charlotte-nc", `DELTA_MISMATCH charlotte-nc`), which went stale as later markets went live. None involves Augusta or the receipt |

**REPAIR_CAUSED = 0. UNRESOLVED = 0.** The repository code is identical to base, so no failure can be
repair-caused. The stale Charlotte-pinned module deserves its own bounded guard-repair order, like
[`PTF-PARTICIPATION-GUARD-REPAIR-001`].

Not run (as ordered): `test_factory_throughput_001.py`, demo-media, broad regression, unrelated
markets, whole-site assembly.

## Phase 12 — Production delta

| | |
|---|---|
| AUGUSTA HOTEL DATA CHANGES | 0 |
| AUGUSTA PROFILE SET CHANGES | 0 |
| OTHER MARKET CHANGES | 0 |
| PARTICIPATION CHANGES | 0 |
| AUTHORIZATION CHANGES | 0 |
| DEPLOYMENT RECORD CHANGES | 0 |
| FACTORY IMPLEMENTATION CHANGES | 0 |
| CURRENT LIVE CHANGES | 0 |
| DEPLOYMENT PERFORMED | NO |

Committed: this report only.

## Phase 13 — Current live re-verified (after)

The same read-only check as Phase 1, re-run after the tests. The field-by-field diff against the
before-snapshot is **empty**.

deployment `6ab1a035c7ef3b14a23a4ec6` (unchanged) · source `e82120cc` · bundle `0ec5c655…` ·
**32 markets · 2375 profiles · 2646 release-index routes · 2711 served routes** · host sitemap
`e81961ae…` = record (unchanged) · live index `74c368f2…` (unchanged) · **Augusta live, 17/17 200** ·
**Fort Lauderdale live, 97/97 200** · **Detroit withheld (404)** · **West Palm Beach not live (404)**.
No deployment was performed.

## Final answers

1. VACUOUS AUGUSTA RECEIPT FOUND = YES
2. OLD RECEIPT PATH = atlas-dashboard/launch_packages/pettripfinder/markets/receipts/augusta-ga/pkg-augusta-ga-14806eca154760a0-5f8116aaecd97d09.json
3. OLD PACKAGE ID = pkg-augusta-ga-14806eca154760a0
4. OLD RULE J = PASS (vacuous)
5. OLD FILE COUNT = 0
6. OLD HTML COUNT = 0
7. OLD BUNDLE SHA = e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855
8. OLD RULE K = PASS / BYTE_IDENTICAL (vacuous: two empty bundles)
9. HISTORICAL RECEIPT IMMUTABLE = YES (receipt digest bound by founder packet 005 → ptf-auth-augusta-006, DEPLOYED)
10. REPAIR METHOD = NONE APPLIED: STOP per Phase 3 (no schema-supported corrective mechanism); minimal representation specified in §8 (reader-side vacuous-receipt refusal in `eligible_receipts`; optional receipt 1.1 `CORRECTS` + replay-at-recorded-parent)
11. BUILD A FILE COUNT = 94
12. BUILD A HTML COUNT = 78
13. BUILD A BUNDLE SHA = 2dfb9afbab9447006af210675aaeeb7c61c2b7eecc93f4dcb9dac8037fdd3f1c
14. BUILD B FILE COUNT = 94
15. BUILD B HTML COUNT = 78
16. BUILD B BUNDLE SHA = 2dfb9afbab9447006af210675aaeeb7c61c2b7eecc93f4dcb9dac8037fdd3f1c
17. BYTE IDENTICAL = YES
18. DIFFERING FILES = 0
19. NEW RULE J = PASS (non-empty: 94 files / 78 HTML / output present; in-memory run, not committed)
20. NEW RULE K = PASS / BYTE_IDENTICAL (in-memory run, not committed)
21. EFFECTIVE AUGUSTA FAST = UNCHANGED: the committed vacuous receipt remains the only receipt `eligible_receipts` returns; a current-live run is J/K PASS but I/N FAIL (historical parent), ELIGIBLE NO
22. OLD RECEIPT PRESERVED = YES (byte-identical, a2e22ce8…)
23. CORRECTIVE / SUPERSEDING RECEIPT = NONE WRITTEN (no schema-supported mechanism)
24. HISTORICAL PACKAGE DIGEST INVALIDATED = NO
25. HISTORICAL AUTHORIZATION INVALIDATED = NO
26. DEPLOYMENT RECORD CHANGED = NO
27. TARGETED TESTS COLLECTED = 322
28. TARGETED TESTS PASSED = 309
29. TARGETED TESTS FAILED = 13 (all PRE_EXISTING; same 13 at base f182cc08)
30. REPAIR_CAUSED FAILURES = 0
31. UNRESOLVED = 0
32. AUGUSTA HOTEL DATA CHANGED = NO
33. AUGUSTA PROFILE SET CHANGED = NO
34. OTHER MARKET DATA CHANGED = NO
35. FACTORY CODE CHANGED = NO
36. CURRENT LIVE MODIFIED = NO
37. DEPLOYMENT PERFORMED = NO
38. AUGUSTA STILL LIVE = YES
39. origin == HEAD = YES (verified after pushing the commit that carries this report)
40. tree clean = YES (verified after the push; build dirs `C:/t/agr1a`, `C:/t/agr1b` and worktree `C:/t/agrbase` removed)

```
PTF AUGUSTA FAST RECEIPT RESEAL = FAIL
VACUOUS AUGUSTA RECEIPT REMAINS EFFECTIVE = YES
RULE J NONEMPTY PROOF = PASS
RULE K DETERMINISM PROOF = PASS
HISTORICAL AUTHORIZATION PRESERVED = YES
CURRENT LIVE MODIFIED = NO
DEPLOYMENT PERFORMED = NO
AUGUSTA STILL LIVE = YES
```

The RESEAL is FAIL because it was **blocked by design**, not by a defect: the build is proven, and
recording that proof needs a representation this order may not create.
