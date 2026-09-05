# PTF-CINCINNATI-PARALLEL-REVALIDATION-002 — FINAL

Market-local hardened revalidation of Cincinnati, run parallel-safe while
Pittsburgh owns the serialized promotion lane.

**Nothing was promoted, no shared global was regenerated, no shared pin moved,
no production candidate was assembled, nothing was deployed, and no provider
was paid. Total spend: $0.00, 0 plan credits, 0 vendor calls.**

---

## BASELINE

Re-derived mechanically from source. The historical expectation in the order was
not trusted; every number below comes from a committed file.

| fact | value | agrees with |
|---|---|---|
| census | 257 | `identity_census/cincinnati-oh.json` |
| published pet-friendly | 99 | partition, policy package, release contract |
| verified no-pets | 49 | Cincinnati exclusions shard |
| out of current category | 6 | partition, exclusions shard |
| resolved | 154 | 99 + 49 + 6 |
| unresolved | 103 | 257 − 154 |
| profiles | 99 | policy package (99 records, schema 1.3) |
| corridors defined / published | 22 / 14 | market contract, release contract |
| discovered official-URL routes | 80 | Cincinnati routing shard |

`python -m scripts.pettripfinder.release_contracts` → **11 of 11 markets
AGREEMENT: ok**, Cincinnati included, 0 disagreements.

The order's stated expectation of "resolved 154 / unresolved 103" is right; its
"PF 99 / no-pets 49" is right; the arithmetic closes on 257 exactly.

### Lineage, stated plainly

HEAD entered at `d06e2eb`, the PTF-FACTORY-REGRESSION-V2-001 tip. That is
**behind the deployed Indianapolis lineage** (production is 9 markets / 641
profiles / 782 routes at deploy `6a9b4046`). Acceptable for market-local
evidence work, and the order says so.

It was also behind **Cincinnati's own** hardened revalidation 001 (`3fe46f6`),
which the order did not anticipate. Re-running that order's lanes would have
been a duplicate buy: 5 Firecrawl credits already spent, 75 free static requests
already proven to yield zero publication-grade, 38 Overpass requests already
proven to yield zero TRUE_MISSING. Its artifacts were **carried onto this base
as owned evidence** (two verbatim cherry-picks). Every path in them is
Cincinnati market-local; the one shared path in the original commit, the
generated test inventory, was resolved to this base's newer version so no shared
bookkeeping walked backwards.

---

## OWNED EVIDENCE FIRST

| source order | what it holds |
|---|---|
| revalidation 001 | 23 clean rows — 21 bought across orders 014/015/016 and never applied, 2 read by Firecrawl |
| this order | 46 attended captures, 46 distinct document hashes |

Nothing already owned and valid was reacquired.

---

## WRONG-LIVE AUDIT

001 replayed live records against **stored** verdicts: 118 corroborated, 0
contradicted. That can only surface a contradiction already sitting in the
corpus. This order re-read live rows **first-party, today**.

| brand | live pet-friendly rows re-read | result |
|---|---|---|
| Hilton | 39 | 39 return `petsInfo.petsAllowed = true` |
| IHG | 10 | 10 return a per-property FAQ answer accepting pets |
| Choice | 8 | 8 return the label `Pets Allowed: Yes` |

**CURRENT_AUTHORITY_CORRECT 57. WRONG_LIVE_PF 0. WRONG_LIVE_NO_PETS 0.
SOURCE_CHANGED 0. IDENTITY_MISMATCH 0.**

42 live pet-friendly rows on other hosts were not re-read this order. They are
named in the report rather than left implied.

Cincinnati has 42 committed Marriott routes and **none** of them is a live
pet-friendly row. That is not an oversight — the attended pass read 21
unresolved Marriott properties first-party and 13 refuse pets outright.

---

## THE ATTENDED PASS — the wall 001 measured, walked

Revalidation 001 recorded Marriott and Hilton as "a measured capability wall"
and correctly refused to spend on them. That was true of the lanes it ran. It is
**not true of the attended lane**, which it did not run.

Method: enter the brand's own origin once, then read the whole cohort by
same-origin fetch. Every row's sha256 is computed in the same call that reads
the quote, so hash and quote provably describe one document. Identity binds on
what the **page** declares about itself, never on the route that led there.

| verdict | rows |
|---|---|
| CLEAN_PET_FRIENDLY | 19 |
| CLEAN_VERIFIED_NO_PETS | 17 |
| IDENTITY_REVIEW_REQUIRED | 4 |
| CAPTURE_FAILED | 3 |
| SOURCE_SILENT | 2 |
| POLICY_NOT_FOUND | 1 |

46 attempted, 45 bound to an identity, **46 distinct document hashes**, $0.

### What was refused as evidence

- an amenity chip is a category label, not a policy — Studio 6 Fairfield offers
  only "Pet-Friendly Accommodation" and a site-wide "Pets Stay Free" footer
  link, and is held at POLICY_NOT_FOUND;
- a search facet is not a property statement — the SureStay Florence route
  redirects to a brand search page;
- a service-animal sentence is never acceptance;
- silence is never a refusal — Hyatt Regency Cincinnati says nothing about pets
  and stays unresolved.

### Two identity guards that cost rows on purpose

1. A clean row must be corroborated by something the page declared. Two rows
   that served a usable policy but no address of their own were demoted.
2. A postal code shared with a sibling cannot tell two hotels apart. Mason OH
   45040 carries two Choice properties; both were demoted from clean to review
   even though both refuse pets in identical words.

---

## RECENSUS AND COMPETITOR CHALLENGE

Free OSM recensus (carried from 001): 38 Overpass requests, 201 candidates,
63 explained by the census, 110 bare chain instances, 28 named review leads,
**TRUE_MISSING_IDENTITY 0**.

Competitor lane, this order. Free static is exhausted — BringFido 403,
PetsWelcome 403, GoPetFriendly serves one client-rendered shell for every path
including `/robots.txt`, TripsWithPets 404. Attended, BringFido serves.

The committed doctrine warns that this directory's query-string category filter
is inert and the real filter is a path segment. Three path values were tested:

| path | headline |
|---|---|
| `/lodging/city/cincinnati_oh_us/` | 135 pet friendly **hotels** |
| `/lodging/hotels/city/cincinnati_oh_us/` | 36 pet friendly **hotels** |
| `/lodging/rentals/city/cincinnati_oh_us/` | 99 pet friendly **vacation rentals** |

**36 + 99 = 135, exactly.** The path filter is live, and the unfiltered page
calls itself "hotels" while serving hotels and vacation rentals together. The
competitor's real Cincinnati hotel inventory is 36, not 135. Taking 135 as a
census would have manufactured a discovery gap out of 99 vacation rentals.

Of 12 rows that rendered: 7 already published by Atlas, 2 existing but
unresolved, 2 rental-category rows on a page headed "hotels", 1 needing identity
review, **0 TRUE_MISSING**. The served cohort was **not** fully harvested — the
listing gates it behind an interactive date selection, and this order reports
what it got rather than an estimate.

BringFido scopes to the literal string "Cincinnati, OH" and cannot see Florence,
Erlanger, Newport, Mason, West Chester, Hamilton, Middletown or Lawrenceburg.
Atlas publishes 99 pet-friendly Cincinnati profiles today — 2.75× the
competitor's entire city hotel directory.

---

## BRAND INVENTORY AUDIT

The official first-party sitemap is a routing and identity lane, never a policy
lane. **564 free first-party requests, 96 minutes, 28,779 published US
properties read, $0.** Reruns cost nothing — every response is cached on disk.

| brand | lane | shards | properties published |
|---|---|---|---|
| Marriott | INVENTORY_READ | 7 / 7 | 10,221 |
| Hilton | INVENTORY_READ | 539 / 539 | 9,751 |
| Sonesta | INVENTORY_READ | 1 / 1 | 4,925 |
| Best Western | INVENTORY_READ | 1 / 1 | 3,882 |
| ESA | INVENTORY_EMPTY | 1 / 1 | 0 |
| IHG, Choice, Hyatt, Red Roof, Motel 6 | ENTRY_REFUSED | — | 0 |
| Wyndham | OPEN_UNEXPECTEDLY | — | 0 |

Wyndham refused an earlier probe and served a later one. **The wall is not
stable, and a refusal is a measurement, never a permanent fact.** For the five
brands that refuse, this lane is *silent* about them — not clean.

### What it decided about Cincinnati's own rows

| classification | rows |
|---|---|
| EXACT_ACTIVE_ROUTE | 99 |
| BRAND_INVENTORY_SILENT | 98 |
| NOT_A_BRAND_LANE (independents) | 54 |
| ROUTE_REPAIR_AVAILABLE | 3 |
| REBRAND_ROUTE | 2 |
| DEAD_PROPERTY_CODE | 1 |

**Three free route repairs**, two of them for census rows sitting in
`AWAITING_IDENTITY_RESOLUTION` with no official URL at all — Home2 Suites
Springdale Cincinnati (`cvgspht`) and SpringHill Suites Cincinnati Mason
(`cvgms`) — plus Americas Best Value Inn Williamstown.

**One dead property code**, which answers a founder item mechanically: SureStay
Florence `55078` is not among Best Western's 3,882 published properties. That is
why its URL falls through to a search page. The code is dead, not mis-routed.

**Two rebrand routes**: the committed routes for BEST WESTERN PLUS Hannaford Inn
and Best Western Premier Mariemont Inn are marked retired, and Best Western
still publishes both pages.

**Routing-shard hygiene.** Of the 99 identities whose committed URL the brand's
own inventory confirms: 47 have no row at all in the Cincinnati routing shard,
43 have a row carrying an empty `property_code`, and 9 agree. No live route is
wrong — the audit proved that separately — but a routing table that cannot name
a property code cannot detect a dead one.

### 18 census leads, after the first matcher was thrown away

| classification | rows |
|---|---|
| TRUE_MISSING_BRAND_IDENTITY | 5 |
| IDENTITY_REVIEW_REQUIRED | 13 |
| NOT_DECIDABLE_BY_THIS_LANE | 133 |

The five: Fairfield Inn & Suites Cincinnati Oakley (`cvgfn`), Hampton Suites
Williamstown Ark Encounter (`cvgarhx`), Home2 Suites Lawrenceburg/Greendale
(`cvggrht`), Spark Walton (`cvguspe`), The Hotel Rambler Montgomery (`cvgqkup`).
**Neither the OSM recensus nor the competitor directory found any of them.**

**The first matcher this order wrote reported 2,708 missing hotels.** Every
sample was a Marriott in Atlanta or Austin, matched on the word "fairfield" —
which is a Marriott *brand*, not a city — or on fragments like "park", "ridge"
and "union". It was replaced before any number was reported. Two tests now have
to pass:

1. the slug must contain a **whole** market city as a contiguous phrase;
2. the brand's own property code must carry a market prefix this market already
   owns — Marriott `cvg`/`mwd`, Hilton `cvg`/`lku`/`luk`/`mwo`/`oxf`/`sgo` —
   **read back off the routes this same run matched**, never invented.

A second correction followed: Sonesta's "property code" is its whole slug, so
every Sonesta row shared the prefix `son` and the prefix test passed for a hotel
in Baton Rouge. A real property code is short and fixed-length. Brands whose
codes carry no market prefix now return `NOT_DECIDABLE_BY_THIS_LANE` rather than
a discovery this lane cannot support.

---

## SHADOW

Census does not move. This order resolved no identity and moved no geography.

| | pinned | shadow |
|---|---|---|
| census | 257 | 257 |
| PUBLISHED_PET_FRIENDLY | 99 | 130 |
| VERIFIED_NO_PETS | 49 | 77 |
| OUT_OF_CURRENT_CATEGORY | 6 | 6 |
| AWAITING_POLICY_OBSERVATION | 70 | 12 |
| AWAITING_IDENTITY_RESOLUTION | 17 | 16 |
| AWAITING_OFFICIAL_URL | 16 | 16 |

Both columns sum to 257.

Retirements 0, successors 0, same-campus 0, explicit assignments 0, geography
holds 0, identity holds 4.

---

## PENDING APPLICATION

| | rows |
|---|---|
| clean pet-friendly | 31 |
| clean verified-no-pets | 28 |
| held with evidence | 10 |

59 clean rows, **59 distinct identities, 59 distinct document hashes**, every
row carrying a contiguous quote and a capture timestamp. 23 inherited from 001,
36 from this order's attended pass.

**No census admission is inside this inventory.** All 59 identity keys exist in
the committed census. Every recensus and competitor lead is a question in
founder group A, never a row — a verified new hotel is a census admission and
belongs to an identity order.

### PROJECTED STATE if a later order promoted the clean inventory

| | current | projected |
|---|---|---|
| pet-friendly | 99 | 130 |
| verified no-pets | 49 | 77 |
| resolved | 154 | 213 |
| unresolved | 103 | 44 |
| profiles | 99 | 130 |

001 projected 111 / 60. The difference is the attended lane.

---

## FOUNDER PACKET

17 items in one grouped packet. **0 promotion blockers.**

| group | items |
|---|---|
| A identity / alias / successor / same-campus | 5 |
| B geography | 1 (none) |
| C closure / conversion / non-lodging | 2 |
| D policy ambiguity / reader exception | 4 |
| E evidence conflict | 4 |
| F cross-market collision | 1 |

Highlights:

- **A1** supersedes 001's A1 and A2 with better evidence. Both Mason 45040
  Choice properties refuse pets in identical words; the Comfort Suites page
  declares a street the census row has never had, the Quality Inn page declares
  none. Admit the address, then the policy.
- **A3** — the DoubleTree Lawrenceburg route is marked `ROUTING_RETIRED` and
  still returns HTTP 200 with a live policy from Hilton's own inventory.
- **C1** — two committed routes now resolve to sites that are not hotels.
  `iresteasy.com` serves unrelated Japanese-language content; `theglendalia.com`
  serves an online-gambling site. Withdraw both routes; a lapsed domain says the
  URL is dead, never that the hotel is.
- **D1** — Holiday Inn Express Fairfield states three different pet charges on
  one page: per stay, per pet, and per night. Publishing one would publish a
  price the source does not support.
- **D2/D3** carry forward 001's unanswered questions with fresh confirmation:
  Homewood Midtown still leaves nights 2–4 unpriced, Tru Monroe still says the
  fee is TAXABLE, Tru Sharonville still says "*No Cats" against a brand template
  that says dog/cat.
- **A5** — 18 Cincinnati-area brand properties absent from the census, five of
  them with no close match at all, found in the brands' own inventories.
- **E3** — three free route repairs, two of them for rows that have never had an
  official URL.
- **E4** — the routing shard names a property code for 9 of 99 live routes.

No founder ruling was invented.

---

## PAID READINESS

Shared ledgers were **read and not written**.

| lane | eligible rows this order | why |
|---|---|---|
| Firecrawl | 0 | the attended lane answered every routed row for $0 and 0 credits; buying a credit for a page a browser already read is a double buy |
| Bright Data | 0 | same; Cincinnati has spent $6.24 over 39 attempts, 29 of them reusable and terminal |
| Places discovery | 16 qualified, recommend NOT NOW | free routing is not exhausted — the official brand inventories are the cheaper instrument and are only partly applied |

Cincinnati has **never** bought a places lookup, so there is no double-buy risk
and no cached answer to reuse.

**Ledger gap flagged, not fixed:** 001's Firecrawl run (7 attempts, 5 credits,
$0) is in that order's market report but has no Cincinnati rows in the shared
paid-attempt ledger on this base. A serialized order should reconcile it. This
order may not write that ledger.

---

## PROMOTION READINESS

**PROMOTION_READY = YES**, with one prerequisite that is a lineage matter, not
an evidence matter.

**REQUIRED BEFORE PROMOTION**

1. Integrate the then-current deployed canonical lineage into this branch first.
   This branch is based on `d06e2eb` and predates the Indianapolis deployment
   lineage. Market-local evidence work is safe on it; promotion is not.

**OPTIONAL COVERAGE EXPANSION**

- the 28 OSM review leads;
- the 16 `AWAITING_OFFICIAL_URL` identities, routed against the official brand
  inventories rather than bought;
- the three route repairs in C1 and E2.

---

## PARALLEL SAFETY

Proven mechanically by reading every path this branch changed against its base,
not by asserting intent.

| forbidden class | files changed |
|---|---|
| Pittsburgh | 0 |
| Louisville | 0 |
| Indianapolis | 0 |
| Cincinnati authority | 0 |
| identity census | 0 |
| final partition | 0 |
| generated globals + manifest | 0 |
| market policy packages | 0 |
| shared current-state pins | 0 |
| shared ledgers | 0 |
| deployment files | 0 |
| release contracts | 0 |
| site bundle | 0 |

37 paths changed against base `d06e2eb`: 33 Cincinnati market-local, 4 allowed
shared, **0 unaccounted**. The set is read from git, not asserted.

Every one of the four shared paths is named in the proof with the reason it is
allowed, and none of them is authority, census, a global, a pin, a ledger, a
contract, a deployment file or a bundle.

- `tests/.../acquisition/test_store_integration_025.py` — run-registration
  bookkeeping. Phase 19 permits adding Cincinnati only, and the diff adds four
  `cincinnati_oh_*` run ids and changes nothing else.
- `tests/pettripfinder/test_regression_delta_001.py` — the replay fixture, fixed
  because this order's own registration commit made the edit under test a no-op.
- `launch_packages/pettripfinder/reports/factory_throughput_001_test_inventory.json`
  and its `.md` — the generated description of the suite, regenerated because
  the carried pin migration moved 32 restated sites onto the shared pins. It is
  a report *about* the tests and holds no market's counts.

Three of these four were touched only to close TRUE_NEW failures. **The shared
surface grew for closure, never for convenience**, and the thirteen forbidden
classes stayed at zero throughout.

Production assembly NOT RUN — no assembler invoked, no bundle directory exists.
Deployment NOT RUN. Promotion NOT RUN.

**PARALLEL_SAFE = True.**

---

## REGRESSION

The committed validation matrix was asked, not guessed. It classified this
order's five new `scripts/pettripfinder/` modules as `GENERIC_RUNTIME_CHANGE`,
one of the six mandatory-full classes, and returned
`FULL_REGRESSION_REQUIRED = YES`. So the broad run was earned, not skipped.

### The broad run, at `aa4ba7d`

| | |
|---|---|
| collected | 17,380 |
| passed | 16,998 |
| skipped | 219 |
| failed | 163 |
| wall clock | 5,935 s (1 h 38 m) |

163 against a baseline of 160 proves nothing by itself. **Counts were not used.**
Classified by node id against `regression_baselines/f75aa95.json`:

| | |
|---|---|
| PRE_EXISTING | 160 |
| EXPECTED_EPOCH_CHANGE | 0 |
| TEST_HARNESS_FLAKE | 0 |
| **TRUE_NEW_FAILURE** | **3** |

The 160 pre-existing failures are the f75aa95 baseline set exactly, by identity.

**The classifier lied once, and the committed doctrine is why it was caught.**
`classify --run` was first handed `run.json`. It returned all four buckets at
zero — a clean pass that was not a pass at all. `--run` wants the run
**directory**; a file gives a false all-zero result. Handed the directory, it
returned the three real failures below.

### The three TRUE_NEW failures, all this order's own unpaid bookkeeping

None was a defect in the market work. Each is a consequence of a commit this
order had already made, and each is closed in `16475f2`.

1. **`test_every_run_on_disk_is_classified`.** This order's own two runs,
   `cincinnati_oh_attended_002` and `cincinnati_oh_brand_inventory_002`, sit on
   disk and were never declared. An unclassified run is a run nobody decided
   about. Both are now named with what they cost and what they may touch.
2. **`test_the_replay_edit_really_is_the_two_run_ids_and_nothing_else`.** The
   replay builds its BEFORE from the live registration file and then applies the
   registration as the edit under test. Once `29cc465` actually applied that fix
   here, re-adding the two run ids became a no-op and the edit vanished. The
   fixture now strips those two elements back out before committing its base, so
   the BEFORE is the pre-fix file whichever side of the fix a checkout sits on.
   No assertion was changed and none was relaxed.
3. **`test_the_committed_inventory_reproduces_from_the_suite`.** Carrying
   revalidation 001's evidence onto this base brought its pin migration, which
   moved 32 restated sites onto the shared pins across 9 suites. Two Cincinnati
   modules correctly stopped restating whole-package literals —
   `test_cincinnati_zip_integrity_002` now asserts `NOW.census` where it once
   asserted a bare `257` — so the committed inventory no longer described the
   suite. Regenerated: 1,586 sites to 1,554, 264 modules to 263. **Every one of
   those assertions still fires; each now follows the pin instead of restating
   it.**

### The late fix cost 4 minutes, not another 99

This is exactly the case PTF-FACTORY-REGRESSION-V2-001 exists for. The late fix
was classified on its own change surface, `aa4ba7d..16475f2`:
`BOOKKEEPING_REGISTRATION_CHANGE`, `TEST_EXPECTATION_CHANGE` and
`GENERATED_REPORT_ONLY` — all narrow, no row of the matrix making a broad run
mandatory. **`FULL_REGRESSION_REQUIRED = NO`, assembly not required.**

| | |
|---|---|
| targeted modules | 35 |
| collected | 3,593 |
| failing | 139, all PRE_EXISTING |
| TRUE_NEW | **0** |
| wall clock | 237.6 s |

All three node ids returned **CLOSED**.

### Result

| | |
|---|---|
| release contracts | 11 of 11 markets AGREEMENT ok, 0 disagreements |
| **TRUE_NEW_FAILURE** | **0** |

Production assembly was never run and no bundle directory exists.

---

## FACTORY SPEED

| | this order (002) | revalidation 001 |
|---|---|---|
| USD spent | **$0.00** | $0.00 |
| plan credits | **0** | 5 |
| vendor calls | **0** | 7 Firecrawl |
| free first-party requests | ~745 (564 measured in the brand sweep) | 120 |
| attended pages | ~118 | 0 |
| clean rows produced | **36** | 23 |
| census leads produced | **18** brand + 12 competitor rows reconciled | 28 OSM |
| route findings | 3 repairs, 2 rebrands, 1 dead code, 2 dead domains | 0 |
| live rows re-read first-party | 57 | 0 (replay only) |

Owned evidence reused rather than reacquired: all 23 of 001's clean rows, its
75-request static corpus, its 38-request Overpass recensus and its 7-call
Firecrawl pass. **Reacquiring them would have cost 5 credits and 120 requests
for zero new information.**

The brand sweep is cached on disk keyed by URL, so a rerun of the whole Phase 7
audit costs **0 requests**. Both corrections to its matcher were made against
the cache at no network cost at all.

### What made this order fast, and what made it slow

Fast: entering a brand's origin once and reading a whole cohort by same-origin
fetch. Twenty-one Marriott properties in two calls; thirty-nine live Hilton rows
in three.

Slow: 539 Hilton sitemap shards at roughly ten seconds each, 96 minutes for one
brand. Worth it once — the cache makes it free forever after — but a later order
should read only the brand-and-number shards a market actually needs.

---

## GIT

Branch `worker/ptf-cincinnati-parallel-revalidation-002`, based on `d06e2eb`.

| commit | what |
|---|---|
| `5a5aae2` | carry revalidation 001's evidence onto this base as owned evidence |
| `29cc465` | declare 001's two capture runs in the shared run table |
| `aa4ba7d` | this order's evidence — 8 market reports and 5 scripts |
| `16475f2` | close the three TRUE_NEW failures the broad run surfaced |
| `HEAD` | this report, and the parallel-safety proof re-derived over the final tree |

Working tree clean at the end. Branch pushed to `origin`, `origin == HEAD`.

One correction was made to this report during closeout rather than papered over.
It claimed 29 Cincinnati market-local paths; the mechanical proof said 33 local
and 1 shared. **The proof was right and the prose was wrong**, and the prose was
corrected. A second apparent mismatch was not a mismatch: the routing-shard
split of 47 / 43 / 9 does not reproduce when joined on identity key, because the
audit joins routes on official URL. Joined the way the audit joins them, it
reproduces exactly.

---

## NEXT — the Cincinnati serialized promotion / application order

**DO NOT START IT FROM THIS BRANCH.** Cincinnati must first integrate the
then-current deployed canonical lineage. This branch is based on `d06e2eb`,
which predates the Indianapolis deployment lineage that production runs on.
Promoting from here would promote onto a stale base.

The order, when it is authorized:

1. **Integrate the canonical lineage.** Merge the then-current deployed tip into
   a Cincinnati branch and prove the merge by failure-set **identity**, not by
   counts. Baseline-prove any new failure in a scratch worktree at the prior
   commit.
2. **Re-derive Cincinnati from source** on the merged base and confirm the
   baseline still reads 257 / 99 / 49 / 154 / 103 / 99.
3. **Settle founder groups A, C, D and E first.** A1 and A3 unlock rows; C1 and
   E2 are route withdrawals; D1–D3 decide how much of three sentences survives
   into a published fact. Retire by MOVING a row, never by deleting it.
4. **Promote the clean inventory into the pinned source census** — 31
   pet-friendly and 28 verified-no-pets, 99 → 130 and 49 → 77. Edit the
   Cincinnati **shard only**; never the three generated globals by hand.
5. **Regenerate the globals BEFORE the contract derivation**, then re-author the
   Cincinnati release contract and require 0 disagreements across all markets.
6. **Assemble the production candidate** and reproduce it byte-for-byte before
   anything is called ready. The renderer is the last gate.
7. **Run the full regression** and classify by node id against the current
   baseline manifest. Require `TRUE_NEW_FAILURE = 0`.
8. **Prepare a deployment packet. Do not deploy.** Deployment is a separate
   authorization, and no founder deployment decision exists for a promoted
   Cincinnati.

STOP.
