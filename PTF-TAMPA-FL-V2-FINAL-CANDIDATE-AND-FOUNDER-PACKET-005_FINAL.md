# PTF-TAMPA-FL-V2-FINAL-CANDIDATE-AND-FOUNDER-PACKET-005 — FINAL

Market `tampa-fl`. Branch `worker/ptf-tampa-fl-market-002`, worktree `C:\Atlas-Tampa-FL-Hardened-V2`.
Baseline: packet 004 (commit `c8ff65c2`), registered package `pkg-tampa-fl-38f6e4b2dc1f6a11`, AWAITING_FOUNDER_AUTHORIZATION.

Status: **SHADOW_UNTIL_REGISTERED → REGISTERED, AWAITING_FOUNDER_AUTHORIZATION**. Nothing deployed, nothing authorized, `launch_participation.json` untouched.

---

## 1. Why this packet exists

Packet 004 (mission 004) reached `AUTHORIZATION_READY` but could not state exact deployable-bundle digests. Mission 005 set out to produce those digests directly. It could not, for a real, verified, structural reason documented below — not a tooling gap this order introduced, and not something this order tried to route around.

## 2. What was attempted and what was found

`release_coordinator.py` is the only tool in this factory that assembles a real, deployable whole-site bundle (the artifact whose hash becomes `deployment_artifact_digest`). Running `release_coordinator.py stage --package <tampa package>` against the real, current tooling produced:

```
CoordinatorError: UNAUTHORIZED_ADDITION: the delta market tampa-fl does not participate in the final membership
```

Reading `_final_membership()` in `release_coordinator.py` confirms this is deliberate design, not a bug: final membership is derived *exclusively* from the committed, founder-authorized rows in `deploy/netlify/launch_participation.json` — "membership comes from the participation document (the founder's decision), never from what happens to exist in the tree." Tampa's row there still reads `SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH`, so the tool refuses by design.

The function does accept an internal `authority={"add": [...]}` override, but the CLI never exposes it, and per explicit founder instruction this order did **not** call it with a synthetic, temporary, or non-persisted authority, did **not** bypass the membership gate, and did **not** touch `launch_participation.json`. The conclusion stands as a real fact about this factory's release lifecycle: computing the exact deployment-artifact/candidate/sitemap digest **is** the same act as authorizing the market, in every prior market's actual history (Orlando's own equivalent digests first appear in its combined "FOUNDER-AUTHORIZATION-AND-LIVE-LAUNCH" mission, never in its registration-only mission).

## 3. What is bound instead

The abstract, release-index-level "expected candidate" comparison — computed by `registration_release_lane.py`'s own seal step (`registration_data_only.check_expected_release`), which does not build a real bundle and is not gated by `launch_participation.json` — already passed cleanly and is unchanged since packet 004:

| Field | Value |
|---|---|
| expected_candidate_index_digest | `sha256:0dfd1238bb14e5e740920ed967d77336d974ae7525c36c3278c1f02cad079b4a` |
| actual_candidate_index_digest | `sha256:da1a00504b09d62fa0af401e3e234bb55358e2c421094e82227ae29747e829bc` |
| unexpected market/profile/route changes | 0 / 0 / 0 |
| projected markets/profiles/routes | 29 / 2151 / 2398 |

(The two index digests differ in raw bytes by construction — one is a synthetic union of parent + package, the other a fresh re-derivation from committed files — but `compare_complete` already proved them equal as sets, which is the actual pass/fail gate.)

## 4. Fresh verification performed this order

- **Live recheck** (three independent methods): `release_index.live_index()`, `release_coordinator.py inspect` (cross-checks 8 authoritative sources, `verified: true`, 0 problems), and a direct HTTPS fetch of the live sitemap with byte-for-byte SHA-256 comparison. All agree: deploy `6aa9dad7cf1419580b307f71` (Orlando), 28 markets, 2003 profiles, 2299 routes, sitemap digest `e057181a...41e969`, unchanged since packet 004. **STALE PARENT = NO.**
- **Registered package**: `pkg-tampa-fl-38f6e4b2dc1f6a11`, digest `sha256:38f6e4b2dc1f6a111985288f334ca93d66472423ccac760c98f05f47afaa9c8d`, unchanged, reproducibility already proven byte-identical in mission 004 (separate detached worktree, full registration replay from the correct pre-registration parent).
- **FAST**: 15/15 PASS (from the sealed package's own receipt, re-read fresh).
- **Registration classification**: `ELIGIBLE: YES`, `REACHES: AUTHORIZATION_READY`, `COMPOSITE_FRESH_MARKET_DATA_ONLY`, 0 failed checks, 0 broad regression.
- **Coverage readiness**: `YES` (mission 003's mechanical, non-percentage-based verdict — actionable unresolved = 0, competitor gap explained, no evidence cohort skipped).
- **Hold safety**: all 314 held Tampa identities cross-referenced by name/key against the registered seed (148 PF) and exclusions (45 NP) sets — **0 leaks**. 314 + 193 = 507, exactly the registered census.

## 5. Founder authorization packet 005

`launch_packages/pettripfinder/markets/reports/tampa_fl_founder_authorization_packet_005.json` — schema `ptf-registration-authorization-readiness/1.0`, `founder_status: AWAITING_FOUNDER_AUTHORIZATION`, `authorized_by: null`, `authorized_at: null`. It explicitly supersedes packet 004 (which stays committed, unedited, as history) and states plainly:

```
FINAL_CANDIDATE_DIGEST = NOT_PRODUCIBLE_PRE_AUTHORIZATION
DEPLOYMENT_ARTIFACT_DIGEST = NOT_PRODUCIBLE_PRE_AUTHORIZATION
CANDIDATE_SITEMAP_DIGEST = NOT_PRODUCIBLE_PRE_AUTHORIZATION
```

with the mechanical reason (§2 above) and a `next_launch_order_must` block spelling out the exact 12-step sequence a future launch order has to follow, starting with a fresh live recheck and ending with "deploy only if the authorized parent is still current and every gate passes; otherwise STOP as stale."

## 6. Parallel safety

Only two new files were added: this report and `tampa_fl_founder_authorization_packet_005.json`. `launch_participation.json`, all other markets' files, and shared factory code were not touched.

---

## FINAL ANSWERS

1. CURRENT LIVE DEPLOYMENT ID = `6aa9dad7cf1419580b307f71`
2. CURRENT LIVE RELEASE DIGEST = bundle `sha256:7222c0665d4b28943e13a996e9c175612657b8b17c76c04bfc05aefe26c163ae`; release_coordinator's own parent_release_digest `sha256:084ac16aba3293b1e9fa02d8e8d95700251cb001dba5a24d45b0df5b4d1eb380`
3. CURRENT LIVE MARKETS / PROFILES / ROUTES = 28 / 2003 / 2299
4. STALE PARENT = NO
5. REGISTERED TAMPA PACKAGE DIGEST = `sha256:38f6e4b2dc1f6a111985288f334ca93d66472423ccac760c98f05f47afaa9c8d`
6. FINAL CANDIDATE DIGEST = NOT_PRODUCIBLE_PRE_AUTHORIZATION
7. DEPLOYMENT ARTIFACT DIGEST = NOT_PRODUCIBLE_PRE_AUTHORIZATION
8. CANDIDATE SITEMAP DIGEST = NOT_PRODUCIBLE_PRE_AUTHORIZATION
9. INTENDED DELTA DIGEST = not producible pre-authorization for the same structural reason; `changed_market_bundle_sha256 = c1504c075e0720ec2703c86094c9e176cbecd9af06a02c76142d6dc560b5b940` is the closest available pre-authorization value (a registration-stage bundle hash of Tampa's own changed data, not a whole-site intended-delta digest)
10. PROJECTED FINAL MARKETS / PROFILES / ROUTES = 29 / 2151 / 2398
11. TAMPA PROFILES ADDED = 148
12. TAMPA SITEMAP ROUTES ADDED = 99
13. TAMPA RELEASE-INDEX ROUTES ADDED = 99
14. CANDIDATES BYTE IDENTICAL = YES (registered package only, proven in mission 004; whole-site deployable candidate cannot exist pre-authorization, see §2)
15. ALL 314 HOLDS REMAIN UNPUBLISHED = YES (0 leaks)
16. ALL PRIOR LIVE MARKETS PRESERVED = YES (28/28, 0 unexpected changes)
17. UNEXPECTED MARKET / PROFILE / ROUTE CHANGES = 0 / 0 / 0
18. FAST = 15/15 PASS, 0 unknown, 0 failed
19. BROAD REGRESSION RUN = 0
20. FACTORY CODE CHANGED = NO
21. NEW FOUNDER PACKET STATUS = AWAITING_FOUNDER_AUTHORIZATION
22. NEW FOUNDER PACKET PATH = `launch_packages/pettripfinder/markets/reports/tampa_fl_founder_authorization_packet_005.json`
23. NEW FOUNDER PACKET COMMIT = (recorded after commit, see push verification below)
24. PACKET 004 SUPERSEDED = YES (declared in packet 005's own `supersedes` field; packet 004 left committed and unedited)
25. TAMPA DEPLOYED = NO
26. origin == HEAD = (verified mechanically after push, not pre-written — see below)
27. tree clean = (verified mechanically after push, not pre-written — see below)

## Exact founder authorization statement (template — not created, not signed)

> Founder work order PTF-TAMPA-FL-V2-FOUNDER-AUTHORIZATION-AND-LIVE-LAUNCH-{NNN}: "I explicitly AUTHORIZE tampa-fl only: the exact candidate in the founder packet: atlas-dashboard/launch_packages/pettripfinder/markets/reports/tampa_fl_founder_authorization_packet_005.json committed at: {this commit's sha}" -- bound to parent deployment 6aa9dad7cf1419580b307f71, parent release digest 084ac16aba3293b1e9fa02d8e8d95700251cb001dba5a24d45b0df5b4d1eb380, registered package digest sha256:38f6e4b2dc1f6a111985288f334ca93d66472423ccac760c98f05f47afaa9c8d, expected delta +1 market / +148 profiles / +99 routes. Final candidate digest, deployment artifact digest and candidate sitemap digest are computed by the launch order itself, immediately after this authorization is persisted and the release coordinator stages the real candidate — never before.

---

TAMPA V2 FOUNDER PACKET 005 = COMPLETE
TAMPA V2 AWAITING FOUNDER AUTHORIZATION = YES
EXACT DEPLOYABLE DIGESTS PRODUCIBLE PRE-AUTHORIZATION = NO
TAMPA V2 LIVE = NO
origin == HEAD = (see push verification)
tree clean = (see push verification)

STOP.
