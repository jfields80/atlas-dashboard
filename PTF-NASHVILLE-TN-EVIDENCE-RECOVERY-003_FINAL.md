# PTF-NASHVILLE-TN-EVIDENCE-RECOVERY-003 — FINAL

Nashville's held authority is recovered. **8 published becomes 79, 5 refusals
become 18, and 88 holds fall to 4.** Nothing is deployed, nothing is activated,
and no authorization exists. Production is untouched: twelve live markets, 823
profiles, 991 routes on deploy `6aa172121d37bb4013eb44a4`.

The loss was never a census, routing or identity problem. The shadow's attended
lane recorded each page's byte **length** and no document hash, and its
acquisition directories are gitignored and empty, so 84 otherwise-clean rows
could not be tied to any document. This order re-fetched those exact pages and
hashed them. It cost **$0.00, zero paid provider calls and zero Firecrawl
credits.**

---

## PRECHECK AND CURRENT LIVE

| | |
|---|---|
| Worktree | `C:\Atlas-Nashville-Launch-V2` |
| Branch | `worker/ptf-nashville-new-lane-launch-002` |
| HEAD at start | `35e4fd2631246ac0b961c17a75523b41725957f9` |
| origin == HEAD | yes |
| Tree | clean |

Current verified live, read three ways and agreeing:

| | |
|---|---|
| Deployment id | `6aa172121d37bb4013eb44a4` |
| Release digest | `67fe8617b79febb9b2248895441c31ac65931cf9fdcfa4da4f8014ee190cde78` |
| Sitemap digest | `dd0d87f2da07615776016690af64452d42cafc24d3c82e310b5f44efc6f7e611` |
| Markets / profiles / routes | 12 / 823 / 991 |

Lexington live: **YES**. Toledo live: **YES**. Re-read again immediately before
staging: unchanged, and the live sitemap fetched over HTTPS still hashes to the
committed record.

---

## THE RECOVERY COHORT

Built from the hold file's own gate classification, never from a lane name, so
nothing unrelated was re-fetched. Every one of the 88 holds lands in exactly one
bucket and the buckets sum to 88.

| Bucket | Rows | |
|---|---|---|
| **Recovery cohort** | **85** | 84 NO_CAPTURE_HASH + 1 NO_TIMESTAMP |
| Adjunct | 1 | evidence already durable; blocked on a missing city |
| Other holds | 2 | cross-market collisions re-fetching cannot fix |

Cohort by host: Marriott 50, Hilton 34, WoodSpring 1. By prior class: 71
pet-friendly, 14 verified-no-pets.

---

## THE LADDER, PROBED RATHER THAN ASSUMED

The committed static report measured Marriott and Hilton as walled two days
earlier. A refusal goes stale in days, and this order exists because an earlier
one trusted a stored fact instead of a durable one, so the rung was probed live
and bounded to two requests per host.

| Host | Cohort rows | Probe result | Lane used |
|---|---|---|---|
| `www.marriott.com` | 50 | HTTP 403 | attended |
| `www.hilton.com` | 34 | HTTP 403 | attended |
| `www.woodspring.com` | 1 | HTTP 200 | direct static |

**Firecrawl was not called, and that was a measurement, not a preference.**
`ptf_firecrawl_hard_lanes_003` records Hilton **0 of 3** acquired with the policy
surface ABSENT on every one, and Marriott **1 of 4** for seven scrape calls.
Spending credits on this cohort would have bought refusals. No founder
authorization question was needed, because no paid request was required.

| Lane | Pages | Requests | Cost |
|---|---|---|---|
| Static probe | — | 5 | $0.00 |
| Direct static | 2 | 2 | $0.00 |
| Attended browser | 84 | 84 fetches, 2 navigations | $0.00 |
| Firecrawl | 0 | 0 | 0 credits |

---

## THE DURABLE CAPTURE

sha256 is computed over the ArrayBuffer the fetch returned, **in the same call
that takes the quote**, so the hash and the quote cannot come from different
documents. 84 attended pages produced **84 distinct hashes and 0 collisions**.

Each brand is read where it publishes its policy, not from rendered prose:

- **Hilton** — the `__NEXT_DATA__` `petsInfo` node, anchored on its own key set.
  The same pages carry guest-review text saying pets were allowed; the walk
  cannot reach it.
- **Marriott** — the Hotel JSON-LD for identity, and a bounded window after the
  HOTEL INFORMATION "Pet Policy" label for the operative statement.

Identity is decided by the page: the street number and postal code the page's own
structured data states must agree with the census identity. **84 of 84 agreed;
zero identity mismatches.**

### How the payload crossed, and why that is safe

The browser could not reach this machine's loopback. A threaded receiver was
built, self-tested successfully from Python, and still refused from the page, so
the capture came back through the page-text channel instead. A transcription is
exactly the step that silently corrupts a hash, so the **page** computed sha256
over each rendered JSON chunk and every transcribed chunk was verified against
it before use: **four chunks, four matches.** The applier refuses a chunk that
does not reproduce its digest.

---

## CURRENT POLICY ADJUDICATION

| Classification | Rows |
|---|---|
| RECOVERED_CLEAN_PET_FRIENDLY | 71 |
| RECOVERED_CLEAN_VERIFIED_NO_PETS | 13 |
| QUOTE_NOT_OPERATIVE | 1 |
| IDENTITY_MISMATCH / CAPTURE_FAILED / SOURCE_SILENT / ROUTE_REPAIR | 0 |

**Zero policy changes.** All 84 current reads agree with the shadow's
classification — 70 pet-friendly, 14 no-pets. The shadow's reading was right all
along; what it lacked was proof. Nothing was forced to match: the applier
compares the current read against the superseded one and would have recorded a
disagreement had there been any.

**The one row the gate still refuses.** Hilton Brentwood Nashville Suites
publishes `petsAllowed: false` and the single sentence "Service animals only".
The modern gate calls that SERVICE_ANIMAL_ONLY — a service-animal sentence is not
a refusal unless the reader reads one, and a structured flag alone is not
evidence. The shadow's own attended module had an explicit rule treating exactly
this string as a clean refusal. It is held, and the gate was not argued with.

The quote cited for each row is chosen **by the gate**, not by this order:
candidates are offered narrowest-first and the first `classify_quote` calls
ELIGIBLE is used. Where it called none of them operative, the row is held.

---

## RECONCILIATION

| | |
|---|---|
| Recovery cohort | 85 |
| Successfully recaptured | 84 |
| Recovered pet-friendly | 71 |
| Recovered verified-no-pets | 13 |
| Current policy changed | 0 |
| Still held | 1 of the cohort, 4 in total |
| Capture failed / source silent / identity or route issue | 0 |

| | Before | After |
|---|---|---|
| Registered census | 180 | 180 |
| Valid pet-friendly | 8 | **79** |
| Valid verified-no-pets | 5 | **18** |
| Holds | 88 | **4** |
| Unresolved | 167 | 83 |
| Corridors reaching their publication minimum | 0 of 19 | **6 of 19** |

Every recovery row reconciles exactly once, asserted by the applier rather than
by hand.

### What is still held

| Identity | Class | Reversible without re-capture |
|---|---|---|
| Hampton (1919 West End Avenue) | CROSS_MARKET_COLLISION | yes, by founder ruling |
| Hampton Inn & Suites (2324 Crestmoor Road) | CROSS_MARKET_COLLISION | yes, by founder ruling |
| Hilton Brentwood Nashville Suites | SERVICE_ANIMAL_ONLY | no |
| WoodSpring Suites Hermitage | no city stated | yes, by founder ruling |

The WoodSpring row was re-read anyway as an adjunct, one free request, to see
whether the page states a locality. **It does not** — so its blocker survives
re-capture and it stays held. That is reported apart from the cohort so the
recovery accounting stays exact.

---

## SEALED PACKAGE

| | |
|---|---|
| Package id | `pkg-nashville-tn-8cdb83d4413cd487` |
| Package digest | `sha256:8cdb83d4413cd48713113f32230877ba52998861e811d01bd06855f10a47b478` |
| Build input key | `sha256:e75ddfed7d8ea0bcbe99b1c3a4dc9f6425e31c1345a32f14bf80d8e28467b210` |
| Pet-friendly records | 79 |
| Verified-no-pets records | 18 |
| Evidence references | 97 |

`FRESH_PACKAGE_REPRODUCIBLE = YES` — re-sealed from a fresh checkout of the
committed tree in an independent worktree and identical.

`created_from_source_sha` is a field of the package, so the digest is pinned to
the commit that holds the authority. The value above was measured at `a83505e`,
the commit that wrote the recovered authority. Re-sealing at the later
report-and-test commit gives
`sha256:727581ef0bb9cbe208f9f12b845b250e49b8d9c9f7ea26ebd558f975980d05cf` with
**all seven dependency input digests identical** — the authority did not move,
only the commit did.

---

## REGRESSION V2

**The routine release is data-only.** The fast lane's own receipt records
`CHANGE_CLASS = MARKET_AUTHORITY_DATA_ONLY`,
`FAST_DATA_ONLY_RELEASE_ELIGIBLE = YES`,
`FULL_REGRESSION_REQUIRED_BY_LANE = NO`, remote broad jobs 0.

**This order's own diff is not.** No shared runtime module, schema, contract or
assembler changed — but `tests/pettripfinder/pins/market_state.json` did, and
that is shared test infrastructure read by nineteen modules. Regression V2
refuses to narrow a change set carrying it, so `FULL_REGRESSION_REQUIRED = YES`
and exactly one broad run was executed. It was not run merely because evidence
changed.

| | |
|---|---|
| Collected | 18,132 |
| Passed | 17,700 |
| Failures | 179 |
| Baseline (`f75aa95`) | 160 |
| PRE_EXISTING | 160 |
| TRUE_NEW reported by the classifier | 19 |
| Wall clock | 6,390.3 s (1 h 47 m) |
| Broad runs executed | 1 |
| Remote broad jobs | 0 |

Running those 19 node ids at the parent commit splits them:

| | Count |
|---|---|
| PRE_EXISTING_AT_PARENT | 16 |
| CAUSED_BY_THIS_ORDER | 3 |

The 16 are the same set the previous order proved and did not touch, still
absent from the committed baseline only because `f75aa95.json` predates the
Lexington launch. They are reported, not absorbed.

**One mechanical verdict was wrong, and is corrected in writing.**
`test_every_run_on_disk_is_classified` FAILED at the parent, so the split called
it pre-existing. It is not. It failed there for an environmental reason: the node
calls `(REPO / "data" / "acquisition").iterdir()` and a fresh git worktree has no
`data/` directory, so the call raised before the assertion ran. At HEAD it fails
for the real reason — this order created a recovery run directory and had not
classified it. A node that could not **execute** at the parent is not proved
pre-existing there, so it was moved to CAUSED_BY_THIS_ORDER and the correction is
recorded in the audit rather than left in a comment.

That gate was right and is now answered properly: the static run is named with
what it was and what it cost, and the note says why the attended half has no
directory beside it — its 84 pages were fetched inside the browser, so the bytes
never reached this machine and what is durable for those rows is the committed
sha256.

All three were closed at their cause and re-run by node id.
**`TRUE_NEW_FAILURE_AFTER_CLOSURE = 0`.** No second broad run. Nothing was
deselected, relaxed or deleted to make a count.

---

## FAST RELEASE-SAFETY LANE

All fifteen rules PASS. Zero UNKNOWN, zero FAIL.

```
A schema  B identity  C first-party  D policy   E routes
F partition  G collisions  H preservation  I intended delta
J build  K determinism  L hashes  M freshness  N rollback  O paid provenance
```

First-party evidence gate: **97 evaluated, 97 eligible, 0 ineligible.**
Rule O still holds: the thirteen Firecrawl-bought rows from the previous order
keep their reservations from the shared paid-attempt ledger, and this order added
no paid evidence to check.
Receipt digest `sha256:600afcf7829f6d3b6994417bcd783b9f8e33554f76575d50a30713c5f69d599b`.
`PRODUCTION_ACTIVATION_ALLOWED = NO`.

---

## FINAL CANDIDATE AND RELEASE DIFF

Composed with Nashville PARTICIPATING, from a participation document differing
from the committed one in exactly one field, in throwaway worktrees.

| | Parent | Candidate |
|---|---|---|
| Markets | 12 | 13 |
| Profiles | 823 | 902 |
| Routes | 991 | 1,078 |

| | |
|---|---|
| Candidate digest | `c12b410ec8331dbf7a50581027ad60291cac95f626de5a6a846b0d77524e0e11` |
| Sitemap digest | `13f5335fc1a055ce06de5ce66c7921da55308110e94c0b0f18806853c1662bc4` |
| Intended delta digest | `sha256:104ed7ba3c0a917ffc274e62de175b5a1469d276784a62856ee81676fa33c79d` |
| HTML pages | 5,506 |
| Files | 5,524 |
| Gates | 27 of 27 pass |
| Broken links | 0 |
| `deployment_authorized` | **false** |

Markets added: `nashville-tn`. Updated: none. Removed: none. Every other
market's profile count is identical to live, market by market. Detroit stays
excluded; Chattanooga and Fort Wayne are not registered at all.

Nashville contributes 79 profiles and 87 routes — hub, 79 profiles, six
corridors and the policy-comparison page. Measured against the **live** sitemap:
**87 added, 0 removed.**

**Unexpected market changes 0. Unexpected profile changes 0. Unexpected route
changes 0. Release-index findings 0. `UNCHANGED_MARKETS_REBUILT = 0`.**

---

## REPRODUCIBILITY

`FINAL_CANDIDATE_REPRODUCIBLE = YES`. Three independent assemblies, two
worktrees, two commits. All **5,524 files byte-identical**; bundle and sitemap
digests identical.

The third ran at a later commit than the first two and produced a byte-identical
bundle, which is also the proof that the test closures and the reports are not
site inputs. The only manifest field that moves is `generated_from_commit`,
which records the commit the assembly ran at and is not part of the bundle.

---

## PERFORMANCE

| Stage | Seconds |
|---|---|
| Cohort build | 0.4 |
| Static probe (5 requests) | 1.6 |
| Static recapture (2 pages) | 0.5 |
| Attended browser (84 pages, 2 navigations) | ~230 |
| Adjudication and application | 3.1 |
| Authority write + globals + release contract | 2.4 |
| Package seal | 0.17 |
| First-party evidence gate | 0.15 |
| Fast release lane (rules A–O, two cold builds) | 84.3 |
| Candidate index compose + diff | 0.10 |
| Regression V2 classification | 2.4 |
| Cache lookup | 0.73 |
| **Routine data-only release path** | **94.9 s** |

Kept separate, because a one-time cost must not be billed to a routine one:

| | Seconds |
|---|---|
| One broad audit | 6,390.3 |
| Parent baseline-proof run (19 node ids) | 41.9 |
| Closure run (3 node ids) | 13.0 |
| Full 13-market bundle assembly, ×3 | ~1,900 each |

**The cost of recovering legacy evidence itself was about four minutes of
network and CPU, and $0.00.** Everything else in this order is the price of
proving it did not break anything.

Total wall time from order start to authorization-ready: **≈ 4 h 05 m**, of
which ≈ 1 h 47 m is the one broad run and ≈ 1 h 35 m the three assemblies.

---

## ROLLBACK

| | |
|---|---|
| Target deployment id | `6aa172121d37bb4013eb44a4` |
| Target release digest | `67fe8617b79febb9b2248895441c31ac65931cf9fdcfa4da4f8014ee190cde78` |
| Markets / profiles / routes | 12 / 823 / 991 |
| Is the current verified parent | **YES** |

Not the parent's own `rollback_target` (`6a9e047690ec8bdaf99bcad2`), which is the
Toledo deploy Lexington replaced; rolling back to that would un-deploy Lexington.

---

## FOUNDER AUTHORIZATION PACKET

`launch_packages/pettripfinder/markets/reports/nashville_deployment_authorization_004_PROPOSED.json`

Status **AWAITING_FOUNDER_AUTHORIZATION**. `authorized_by` and `authorized_at`
are null. Written to `markets/reports/` and never to
`deploy/netlify/deployment_authorizations/`, because a file in that directory IS
an authorization and only a founder creates one. All twenty-two DEPLOYMENT_READY
gates derive true, including four this order added: every recovery row accounted
for once, every attended page carrying a distinct hash, every transcribed chunk
verified against the page's own digest, and no paid provider called.

What the founder would be authorizing: one field change in
`deploy/netlify/launch_participation.json` — the `nashville-tn` row's
`launch_status` from SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH to
FOUNDER_AUTHORIZED_FOR_LAUNCH, plus the founder's own decision block.

---

## PRODUCTION ENABLEMENT PLAN

`nashville_tn_production_enablement_plan_003.json`, status
**PROPOSED_NOT_APPLIED**, scope NASHVILLE_ONLY. Five fields across two files.
Both allowlists are still empty, so the coordinator refuses all fourteen
registered markets today, and the proposal adds exactly one market id to each.

---

## WHAT A LATER ORDER SHOULD DO

1. **Fix the Toledo applier's manufactured hash.** All 39 of Toledo's live
   attended evidence entries carry `sha256(source_url + quote)` — a value
   computable without ever fetching the page. Toledo is live now. The recovery
   lane this order built reads that market's brands for $0.
2. **Re-pin the regression baseline** at the Lexington-live commit. Sixteen real
   failures are still invisible to the classifier.
3. **Rule on the four remaining Nashville holds** — two cross-market names, one
   missing city, one service-animal-only refusal.
4. **Teach the change classifier a rule for `*_identity_holds_*.json`**, still
   UNCLASSIFIED for Toledo, Lexington and Nashville alike.

---

## HARD STOP

No production activation was enabled. No founder authorization was created. No
host was called. No live participation record was mutated. No live verification
of a Nashville route was performed. Nothing was deployed. Chattanooga was not
started.
