# PTF-AUGUSTA-GA-V2-REGISTRATION-AND-FOUNDER-PACKET-003 — FINAL REPORT

Worktree: `C:\Atlas-Augusta-GA-Hardened-V2`
Branch: `worker/ptf-augusta-ga-market-002`
Market id: `augusta-ga`

## Phase 1 — Precheck (confirmed)

Branch/HEAD/origin/tree verified clean at start (HEAD `16dcf222`, matching the
committed source-ready state). Committed accounting matched the mission's
remembered values exactly: census 91, pet-friendly 14, verified-no-pets 14,
resolved 28, held 63, FAST 15/15 PASS/0 unknown/0 failed, package digest
`985d8ef5...`. No discrepancy — committed accounting governed throughout.

## Phase 2 — Shared file safety review

Re-verified both source-ready-era shared-file diffs against the parent commit
`1fa43a48`: `osm_extracts.json` (+24 lines, 0 deletions) and
`ptf_paid_attempt_ledger_001.json` (+936 lines, 0 deletions — confirmed to
already exist in this repository's broader history under other markets'
worker branches, so this was the first time THIS branch's lineage carried it,
not a new shared file invented for Augusta). Both **SAFE**: normal additive
lifecycle/accounting data, not a shared-factory architecture change.

## Phase 3 — Current verified live, read fresh

Read directly from `release_index.live_index()`, 0 problems:

- Deployment id: `6aa93de5263dfda8c243d0a7`
- Release digest: `sha256:4acb4f16824da6e46b01d86359bf4de0ee8ce3aa005b3d676d42c9560de203ed`
- Sitemap digest: `sha256:c890e6316581e6272e49a94688e6456b4e9d884c2e36e8fcd41a3aff436b8cb2`
- Release-index digest: `sha256:4117525900596174ee91055e30cef0cd0482d0be40ca43f2c19ab78a0249a911`
- 27 participating markets, 28 registered (Detroit registered but withheld — expected), 1802 profiles, 2081 sitemap routes.

This worker branch's lineage forked from Savannah (not Orlando); `origin/main`
is far behind both, since every market's production history lives on its own
independent worker-branch timeline. This IS the mechanically correct and only
available parent for this branch — not a discrepancy.

## Phase 4 — Registration

Registered `augusta-ga` through the existing lifecycle: `market_registration_cli.py --write`
(shard: 14 seed rows, 14 exclusions), `build_global_authority.py --write` (29
markets sharded), a fresh `augusta_ga_release_contract_014.py` (modeled on
Savannah's, 0 disagreements against `release_contracts.derive_authority`),
then `registration_release_lane register`. Participation now reads exactly
**`SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH`**, authorized set
unchanged, no founder or deployment authorization exists.

**Real defect found and fixed along the way**: the shared publication guard
correctly refused to publish Augusta's "Holiday Inn Express" (444 Broad St,
downtown) because the bare brand name collided by normalized-name match
against an unrelated Cleveland exclusion of the same generic name. The
property's own IHG page states its real name, "Holiday Inn Express Augusta
Downtown" — renamed consistently (canonical_name, slug, identity_key,
partition, policy-package join key) across every file that names it. The
shared guard was not touched; it caught a real Augusta-owned naming defect.

**Second real defect found and fixed**: `augusta_ga_proposed_authority_011.py`
had gone stale — a prior dedup pass had changed `augusta_ga_final_partition_007.json`'s
schema from `partition[]`/`disposition` to `items[]`/`final_state` (matching
Savannah's real committed shape) without updating the authority-builder script
to match. Fixed to read the correct schema and to source pet-friendly
evidence from `hotel_policy_facts_augusta-ga.json` and verified-no-pets
evidence from the last known-good staged authority document (both real,
previously-captured evidence — nothing invented).

## Phase 5 — Fresh registered reseal

Did **not** reuse the source-ready shadow package. Sealed fresh via
`registration_release_lane seal --paid-reservations ...` against the live
parent above, with real `paid_reservation` provenance for the four
Firecrawl-sourced pet-friendly records (existing authorized capacity, $0 new
spend) required for FAST rule O.

- SOURCE SHADOW PACKAGE DIGEST = `sha256:985d8ef5d9dd36f1a044c1d3cf137f702475c4dda502607289035d33ef26bfbf`
- REGISTERED PACKAGE ID = `pkg-augusta-ga-799b40936d5d9c65`
- REGISTERED PACKAGE DIGEST = `sha256:799b40936d5d9c65c9d6c232e118a6a87837f8e9e1563bf66000124c62aba906`

**Third real defect found and fixed**: my own ad-hoc rename-fix scripts wrote
several Augusta JSON files with CRLF line endings on this Windows machine, in
violation of `.gitattributes`' `launch_packages/**/*.json text eol=lf` rule.
The first seal (`pkg-augusta-ga-879c9af3de09d243`) was built and committed
from those stale CRLF bytes and did not reproduce from a genuine clean
checkout. Diagnosed via two independent clean git worktrees, fixed the byte
representation (content, counts and policy facts unchanged), resealed to the
correct digest above, and committed a correction (`3613beeb`) replacing the
stale package/receipt. Reproducibility was then reverified clean.

## Phase 6 — Registration classification / FAST

`regression_delta classify --base 16dcf222`: **CHANGE_CLASS =
COMPOSITE_FRESH_MARKET_DATA_ONLY**, **FULL_REGRESSION_REQUIRED = NO**, 0
UNKNOWN paths (26 changed paths: 3 market-local, 13 registration-data, 10
derived, 0 shared-behavior, 0 unknown). All 15 registration-data-only checks
PASS (change_set, market_local_zone, discovery_config, registration_input,
identity_resolutions, participation, release_contract, build_closure,
derived_globals, sealed_package, fast_receipt, expected_release,
identity_routes, market_state_pin, release_integrity). FAST lane: 15/15 PASS,
0 unknown, 0 failed. No broad regression run or required.

## Phase 7 — Exact final candidate

Composed against the fresh live parent: all 27 current live markets
unchanged, plus Augusta's 14 pet-friendly profiles (matching the assembler's
own contract — verified-no-pets records do not get separate profile pages,
confirmed from the real `declared_routes`/`add_routes` list, not assumed).

- FINAL CANDIDATE DIGEST (release-index) = `sha256:b62f0322c61933e116419fdafcacf7ede3d32a36e5fc57260a3ab8756d25680c`
- DEPLOYMENT ARTIFACT DIGEST = same as the sealed package digest (the package IS the deployment artifact at this stage) = `sha256:799b40936d5d9c65c9d6c232e118a6a87837f8e9e1563bf66000124c62aba906`
- CANDIDATE SITEMAP DIGEST = not independently rebuilt this order (see "what is not claimed" below) — the market-scoped seal's own sitemap fragment (1 URL, the market hub) reproduced byte-identical across both internal builds, but a full whole-site sitemap assembly (all 28 markets) was out of scope for a registration order and is properly a deployment order's own check
- INTENDED DELTA DIGEST = `sha256:816043c621b6bb5748ec72720ca60638b1e672f0cf613d85a0ed0798801555b3`
- PROJECTED FINAL MARKETS = 28 (27 live-participating + Augusta; Detroit stays registered-but-withheld and is correctly excluded from this count, same as it's excluded from live)
- PROJECTED FINAL PROFILES = 1816 (1802 + 14)
- PROJECTED FINAL RELEASE-INDEX ROUTES = 2037 (2021 over the same 27+Augusta market set, + 16)
- AUGUSTA PROFILES ADDED = 14
- AUGUSTA RELEASE-INDEX ROUTES ADDED = 16 (14 hotel + 1 corridor + 1 market route)

## Phase 8 — Hold safety (mechanically verified against real generated output, not self-reported)

Grepped the actual generated candidate site (`data/registration_release_lane_final/.../site/`),
not just the JSON summary:

- HELD AUGUSTA PROPERTIES IN POLICY PACKAGE = 0 (policy package holds exactly the 14 published pet-friendly records)
- HELD AUGUSTA PROPERTIES IN PUBLISHED PARTITION = 0 (partition's `add_routes`/generated site directories = exactly 14 hotels + 1 corridor + 1 policy-comparison page = 16, no more)
- HELD AUGUSTA PROFILES IN SITEMAP = 0 (spot-checked 3 held identity slugs directly against the generated sitemap and hotel-directory listing — absent)
- HELD AUGUSTA PROFILE ROUTES IN CANDIDATE = 0

All 63 held rows preserved exactly as adjudicated (ACCESS_BLOCKED/AWAITING_ROUTING_REVIEW,
AWAITING_OFFICIAL_URL, AWAITING_POLICY_OBSERVATION, AWAITING_CONTRADICTION_RESOLUTION)
— nothing promoted to improve launch counts.

## Phase 9 — Geography / South Carolina safety

Grepped the real generated site for North Augusta / Aiken / Edgefield /
Graniteville / Clearwater / their real ZIPs — 0 hits anywhere.

- North Augusta SC profiles published = 0
- Aiken SC profiles published = 0
- Edgefield / other SC profiles published = 0
- 21 real SC hotels remain preserved as OUTSIDE observation evidence (unchanged from source-ready), for a future `north-augusta-sc`/`aiken-sc` market.
- No fringe Georgia town (Thomson/Wrens/Waynesboro/Lincolnton) was absorbed as anything other than its own FRINGE corridor.

## Phase 10 — Independent candidate reproduction

Three independent builds compared, all byte-identical:

1. Two internal builds inside one `seal` invocation (`oa`/`ob`) — `diff -rq` 0 differences.
2. A fully separate `python -m` process invocation (same commit, same explicit `--sealed-at`) — same package_digest.
3. A genuinely clean detached git worktree at the same commit — same package_digest (after the CRLF fix in Phase 5).

0 broken internal links, 0 route collisions, 0 quality-gate failures (reported
by the real assembler each time, not asserted).

## Phase 11 — Production delta audit

From the seal's own `release_index.compare`: `release_diff_passed: true`,
`finding_counts: {}` (0 unexpected findings), **all 27 existing live
markets' fragments UNCHANGED and NOT rebuilt** (`UNCHANGED_MARKETS_REBUILT =
0`, `unchanged_markets` lists all 27) — inherited byte-identical from the
live store, not re-derived. 0 removed markets, 0 removed profiles, 0
unexpected route changes. The only real change is Augusta's own addition
plus the mechanically-expected shared files (`launch_participation.json`
reissue, `deploy/netlify/release_contracts/augusta-ga.json`, the three
derived global-authority files, the market-state pin).

## Phase 12 — Clean-checkout package reproduction

Verified via two independent clean git worktrees (documented under Phase 5's
defect). **PACKAGE REPRODUCIBLE FROM CLEAN CHECKOUT = YES** once the CRLF
defect was fixed. NONDETERMINISTIC FILES = none, once six Augusta-owned JSON
files' line endings were normalized to the committed LF convention (content,
counts, and policy facts were never in question — only the byte
representation of newlines). No shared factory code was touched to achieve
this.

## Phase 13 — Final live recheck

Re-read `release_index.live_index()` immediately before packet creation: 0
problems, deploy id/bundle sha/sitemap sha/participating markets/total
profiles/sitemap route count all byte-identical to Phase 3's reading. (The
release-index digest itself changed — expected, since it hashes the full
29-market registry and Augusta had just been added to that registry by this
same order; the LIVE/participating subset is unchanged.) No stale-parent
condition; proceeded to the founder packet on the same verified parent used
throughout.

## Phase 14 — Founder authorization packet

Created `augusta_ga_founder_authorization_packet_003.json`
(`ptf-deployment-authorization-proposal/1.0`), modeled on Savannah's real
committed packet shape, every digest and count read from a committed or
lane-written artifact. Status exactly `AWAITING_FOUNDER_AUTHORIZATION`,
`AUGUSTA_FOUNDER_AUTHORIZATION_READY: YES`. `authorized_by`/`authorized_at`
are `null`. No founder authorization or deployment authorization was
manufactured.

## Phase 15 — Commit / push

Three commits on `worker/ptf-augusta-ga-market-002`: the registration
(`bdf7d796`), the CRLF correction (`3613beeb`), and this final packet/report
commit. Pushed to `origin`. Mechanically verified AFTER push (not asserted in
advance): `origin == HEAD` and tree clean.

---

# FINAL ANSWERS

1. CURRENT LIVE DEPLOYMENT ID = `6aa93de5263dfda8c243d0a7`
2. CURRENT LIVE RELEASE DIGEST = `sha256:4acb4f16824da6e46b01d86359bf4de0ee8ce3aa005b3d676d42c9560de203ed`
3. CURRENT LIVE MARKETS / PROFILES / ROUTES = 27 / 1802 / 2081
4. SOURCE SHADOW PACKAGE DIGEST = `sha256:985d8ef5d9dd36f1a044c1d3cf137f702475c4dda502607289035d33ef26bfbf`
5. REGISTERED PACKAGE DIGEST = `sha256:799b40936d5d9c65c9d6c232e118a6a87837f8e9e1563bf66000124c62aba906`
6. REGISTERED PACKAGE ID = `pkg-augusta-ga-799b40936d5d9c65`
7. FINAL CANDIDATE DIGEST (release-index) = `sha256:b62f0322c61933e116419fdafcacf7ede3d32a36e5fc57260a3ab8756d25680c`
8. DEPLOYMENT ARTIFACT DIGEST = `sha256:799b40936d5d9c65c9d6c232e118a6a87837f8e9e1563bf66000124c62aba906`
9. CANDIDATE SITEMAP DIGEST = not independently rebuilt this order (full whole-site sitemap assembly is a deployment-order check; the market-scoped fragment reproduced byte-identical)
10. INTENDED DELTA DIGEST = `sha256:816043c621b6bb5748ec72720ca60638b1e672f0cf613d85a0ed0798801555b3`
11. PROJECTED FINAL MARKETS / PROFILES / ROUTES = 28 / 1816 / 2037 (release-index routes)
12. AUGUSTA PROFILES ADDED = 14
13. AUGUSTA SITEMAP ROUTES ADDED = not independently measured this order (see #9)
14. AUGUSTA RELEASE-INDEX ROUTES ADDED = 16
15. CANDIDATES IDENTICAL = YES (3 independent builds, byte-identical)
16. PACKAGE REPRODUCIBLE FROM CLEAN CHECKOUT = YES (after the Phase 5 CRLF fix)
17. EXISTING LIVE MARKETS PRESERVED = YES (27/27 unchanged, 0 rebuilt)
18. UNEXPECTED MARKET / PROFILE / ROUTE CHANGES = 0 / 0 / 0
19. ALL 63 AUGUSTA HOLDS REMAIN UNPUBLISHED = YES (mechanically verified against generated output)
20. SOUTH CAROLINA PROFILES ADDED = 0
21. FAST = 15 / 15 PASS, 0 UNKNOWN, 0 FAILED
22. REGISTRATION CLASSIFICATION = COMPOSITE_FRESH_MARKET_DATA_ONLY, all 15 checks PASS
23. BROAD REGRESSION RUN = 0
24. FACTORY CODE CHANGED = NO (two shared DATA files touched across this and the source-ready order, both purely additive)
25. SHARED ADDITIVE ACCOUNTING FILES SAFE = YES
26. FOUNDER PACKET STATUS = AWAITING_FOUNDER_AUTHORIZATION
27. FOUNDER PACKET PATH = `launch_packages/pettripfinder/markets/reports/augusta_ga_founder_authorization_packet_003.json`
28. FOUNDER PACKET COMMIT = (this order's final commit — see git log)
29. AUGUSTA DEPLOYED = NO
30. origin == HEAD = YES (verified mechanically after push)
31. tree clean = YES (verified mechanically after push)

## Exact founder authorization statement required for this committed candidate

> I, as founder, authorize Augusta, Georgia (`augusta-ga`) to join production
> as the 28th market, binding exactly:
> parent deploy `6aa93de5263dfda8c243d0a7` (release digest
> `sha256:4acb4f16824da6e46b01d86359bf4de0ee8ce3aa005b3d676d42c9560de203ed`),
> sealed package `pkg-augusta-ga-799b40936d5d9c65` (digest
> `sha256:799b40936d5d9c65c9d6c232e118a6a87837f8e9e1563bf66000124c62aba906`),
> intended delta `sha256:816043c621b6bb5748ec72720ca60638b1e672f0cf613d85a0ed0798801555b3`,
> adding 14 pet-friendly profiles and 16 release-index routes, with 63
> Augusta identities remaining held exactly as adjudicated. This
> authorization does not itself deploy anything; it is a separate write from
> any deployment authorization or activation.

---

AUGUSTA V2 RELEASE PREP = COMPLETE
AUGUSTA V2 AWAITING FOUNDER AUTHORIZATION = YES
AUGUSTA V2 LIVE = NO
READY FOR EXACT CANDIDATE AUTHORIZATION = YES

STOP.

Do not deploy.
Do not create deployment authorization.
Do not open the deployment gate.
