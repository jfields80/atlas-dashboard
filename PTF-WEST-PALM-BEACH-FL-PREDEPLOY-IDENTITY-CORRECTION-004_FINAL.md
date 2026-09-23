# PTF-WEST-PALM-BEACH-FL-PREDEPLOY-IDENTITY-CORRECTION-004 — FINAL

**Worktree** `C:\Atlas-West-Palm-Beach-FL-Hardened-V1` · **Branch** `worker/ptf-west-palm-beach-fl-market-001`
**Market** `west-palm-beach-fl`

**The identity defect is corrected, sealed and proven. The old authorized bytes can no longer
deploy. The re-registration could not be narrowed, so this order STOPPED at Phase 10 without
launching a broad regression, and did not create the new founder authorization.**

Nothing was deployed. Production is unchanged.

| | |
|---|---|
| correction | `0fec75a9` |
| reseal | `a07ccc1c` |
| supersession | `9cf163b1` |
| report | this commit |

---

## PHASE 1 — THE DEFECT, RE-VERIFIED FROM COMMITTED EVIDENCE

Census row, before:

```
identity_key         apple ten hospitality management inc
canonical_name       Apple Ten Hospitality Management Inc
slug                 apple-ten-hospitality-management-inc
identity_key_aliases ['apple ten hospitality management inc', 'hilton garden inn boca raton']
street / city / zip  8201 Congress Ave / Boca Raton / 33487
phone                561.988.6110
brand                HILTON          property_code  bctbrgi
official_url         https://www.hilton.com/en/hotels/bctbrgi-hilton-garden-inn-boca-raton/
corridor             west-palm-beach-fl__boca-raton   (assigned by postal_code 33487)
classification       TRUE_HOTEL_IDENTITY   identity_state IDENTITY_CONFIRMED   best_tier 1
```

Its three observations, by tier:

| tier | lane | `name` |
|---|---|---|
| **1** | `BRAND_INVENTORY_CITY_PAGE` | **Hilton Garden Inn Boca Raton** — `property_code bctbrgi`, from `hilton.com/en/hotels/bctbrgi-hilton-garden-inn-boca-raton/` |
| 2 | `REGISTRY_FL_DBPR` | Apple Ten Hospitality Management Inc — `licensee_name APPLE TEN HOSPITALITY MANAGEMENT INC`, `license_number HOT6013438` |
| 3 | `OSM_OVERPASS` | Hilton Garden Inn Boca Raton |

**HOTEL / PROPERTY NAME = Hilton Garden Inn Boca Raton. LICENSEE = Apple Ten Hospitality
Management Inc.** These are different semantic fields, and the DBPR lodging extract holds them
in different columns. Nothing here is inferred from brand knowledge — the two fields are read
from the state's own record, and the market's own DBPR lane report shows both:

```
HOT6013438   business_name "APPLE TEN HOSPITALITY MANAGEMENT INC"
             licensee_name "APPLE TEN HOSPITALITY MANAGEMENT INC"     <- identical
HOT1620879   business_name "RESIDENCE INN FORT LAUDERDALE AIRPORT & CRUISE PORT"
             licensee_name "APPLE TEN FLORIDA SERVICES INC"           <- differ
```

Policy binding, before and after the correction: the first-party quote comes from
`…/bctbrgi-hilton-garden-inn-boca-raton/hotel-info/`, `artifact_sha256
8cde8c6f…`, `capture_method attended_browser`, `source_grade PT2_BRAND`. The policy was always
bound to the right premises; only the display name was wrong.

---

## PHASE 2 — WHY THE LICENSEE NAME OUTRANKED THE TIER-1 NAME

`Node.absorb` decided the canonical name purely on **string length**, never on tier:

```python
# The longest name wins.
if len(obs.get("name") or "") > len(self.name):
    self.name = obs["name"]
```

`len("Apple Ten Hospitality Management Inc") == 36` and
`len("Hilton Garden Inn Boca Raton") == 28`, so length alone handed the traveler the wrong one.

The DBPR lane is **not** at fault: it reads `COL_BUSINESS_NAME` for `name` and carries
`business_name` and `licensee_name` separately, exactly as it should. For this premises the state
simply holds no trade name.

**No shared factory code was modified.** The fix lives entirely in
`scripts/pettripfinder/west_palm_beach_fl_census_reconciliation_001.py`, which is this market's
own module.

**The DBPR licensee information is not discarded.** It stays on its own observation in the census
row's `evidence` array — `licensee_name`, `license_number`, `rank_code`, `rental_units`, `county`,
`snapshot_sha256` — which is the provenance/licensing field the schema already supports. The
superseded spelling is also retained in `identity_key_aliases`. No new row-level field was
invented for it.

---

## PHASE 3 — THE MINIMUM CORRECTION

The rule gains **one** narrow, semantic exception:

> A `REGISTRY_FL_DBPR` observation whose **Business Name is identical to its Licensee Name** names
> the operating company, not the premises. It may not outrank a **tier-1 first-party** name for
> the same premises, in either arrival order.

Unit-checked: licensee identity → `True`; a real trade name with a differing licensee → `False`;
a non-DBPR lane → `False`.

### Why not simply "the tier-1 name always wins"

Because that is a regression, measured over this market's own 190 rows — it would rename **20**,
several of them worse, since a tier-1 name derived from a route slug loses punctuation and
sometimes whole tokens:

```
Comfort Inn & Suites Jupiter I-95            -> Comfort Inn Jupiter              (loses "& Suites")
Super 8 Beach West Palm Beach                -> Super Riviera Beach West Palm…   (loses the "8")
Hawthorn Suites by Wyndham West Palm Beach   -> Hawthorn Extended Stay …          (different brand line)
Palm Beach Marriott … Resort & Spa           -> … Resort And Spa                  (ampersand mangled)
```

That is the naming-normalization project this order forbids. Stylistic variants are left alone.

### Blast radius, measured — exactly one row

Six West Palm Beach census rows carry a licensee identity as their canonical name. **Only one has
a tier-1 alternative to correct to, and only one was published:**

| row | published | disposition | tier-1 names available |
|---|---|---|---|
| **Apple Ten Hospitality Management Inc** | **yes** | `CLEAN_PET_FRIENDLY` | **1** |
| Mar-A-Lago Club L.l.c. | no | `SOURCE_SILENT` | 0 |
| Markowycz Andrew | no | `ROUTING_HOLD` | 0 |
| Motel & More Inc | no | `ROUTING_HOLD` | 0 |
| Palm Beach Historic Inn Llc | no | `SOURCE_SILENT` | 0 |
| Pointe Hotel, Llc | no | `SOURCE_SILENT` | 0 |

The other five have no first-party name to take, so the rule is inert for them and renaming them
is out of scope.

Census diff, before → after: **1 key removed, 1 key added, 0 kept keys renamed.** Count 190,
`classification_counts` identical, `corridor_counts` identical, 0 merge conflicts.

**Live markets unaffected:** Fort Lauderdale carries `APPLE TEN FLORIDA SERVICES INC` only as
`licensee_name`, with the trade name correctly canonical; Miami has no instance.

---

## PHASE 4 — IDENTITY_KEY AND DOWNSTREAM REBINDING

| | before | after |
|---|---|---|
| `identity_key` | `apple ten hospitality management inc` | **`hilton garden inn boca raton`** |
| `canonical_name` | Apple Ten Hospitality Management Inc | **Hilton Garden Inn Boca Raton** |
| `slug` | `apple-ten-hospitality-management-inc` | **`hilton-garden-inn-boca-raton`** |
| aliases | — | both spellings retained |
| premises / phone / brand / property code / corridor | 8201 Congress Ave, 33487, 561.988.6110, HILTON, bctbrgi, boca-raton | **unchanged** |

Every downstream artifact was re-derived, in dependency order, from **retained** evidence —
**0 provider calls, 0 credits, no re-acquisition**:

| artifact | result |
|---|---|
| browser evidence binding | re-bound by `BRAND_PROPERTY_CODE bctbrgi`, `full_premises_match true`, same `transcription_sha256 8cde8c6f…`; 61 attempts / 49 reads / 10 denied / 2 unbound — identical to before |
| clean authority | PF 49 / NP 25 / resolved 74 / unresolved 116 — identical dispositions |
| final partition | 190 identities, contract **0 issues** |
| policy package + proposed authority | 49 records, 0 refused, 0 package issues |
| authority shard | 49 seed rows, 25 exclusions, 0 routing, 0 affiliate |
| derived globals | regenerated; `--check` → *all generated artifacts match the shards* (34 markets, 1,171 exclusions, 2,573 seed rows) |
| release contract | re-derived, **0 disagreements**; `verify_all()` **34/34 clean** |
| holds / exclusions | unchanged — the corrected row was and remains a published profile, not an exclusion |
| brand / corridor accounting | unchanged; the same 5 corridors publish |

No binding was copied onto the new key: each was re-established from the first-party evidence
through the normal ingestion path.

---

## PHASE 5 — ROUTE CORRECTION

From the sealed package's own declared routes:

| | |
|---|---|
| OLD route `/…/apple-ten-hospitality-management-inc/` | **ABSENT** |
| NEW route `/…/hilton-garden-inn-boca-raton/` | **PRESENT, exactly once** |
| declared routes | 55 (49 profiles + 1 hub + 5 corridors) — unchanged |
| duplicate profile for the premises | none |

No production redirect was created: West Palm Beach is not live, every one of its routes returns
404, and the prelaunch contract requires none.

---

## PHASE 6 — THE 49-PROFILE NAME AUDIT, RE-RUN

| | |
|---|---:|
| **PUBLISHABLE PROFILES AUDITED** | **49** |
| tier-1 name differences | **7** (was 8) |
| **SUBSTANTIVE FIRST-PARTY NAME DISAGREEMENTS** | **0** (was 1) |

The 7 remaining are benign stylistic variants and were deliberately left alone:
`Courtyard by Marriott Boynton Beach` / `Courtyard Boynton Beach`; `Delta Hotels by Marriott …`;
`Fairfield Inn & Suites …` (× 2, `&` vs `and`); `Hampton Inn and Suites Wellington`;
`Hilton Garden Inn West Palm Beach 195 Outlets`; `Hilton Palm Beach Airport` / `Hilton Palm Beach PBI`.

The substantive test is mechanical, not stylistic: *is the published name a DBPR licensee
identity?* Zero remain.

---

## PHASE 7 — THE OLD AUTHORIZATION, SUPERSEDED

The repository **does** have a canonical mechanism: `AUTHORIZED → SUPERSEDED` is a supported edge
in `deployment_authorization.TRANSITIONS`, and it is terminal.

| | |
|---|---|
| authorization | `ptf-auth-west-palm-beach-003-217f87eeba72` |
| status | `AUTHORIZED` → **`SUPERSEDED`** |
| consumed | **false** — no deployment happened; it was **not** marked DEPLOYED |
| deployable after | **false** |
| terminal | **true** — `SUPERSEDED` has no outgoing edge |
| history preserved | **true** — bundle `217f87ee…` and sitemap `31ac963f…` retained on the record |
| other deployable authorizations anywhere | **[]** |

**How stale-authorization safety is enforced, in three independent ways:**

1. `deployability_problems` refuses any status outside `DEPLOYABLE_STATUSES == ("AUTHORIZED",)`.
   `SUPERSEDED` is terminal, so it cannot transition back.
2. Even if it could, `verify_authorization` binds `bundle_sha256`. The old record names
   `217f87ee…`; the corrected package is `94d6f411…` and will compose a different bundle. A
   mismatch is a refusal, so the old authorization **cannot** deploy the new bytes.
3. There is no other AUTHORIZED record for this site, so nothing else can consume the candidate
   either.

**Nothing was deleted, nothing was back-dated, and no deployment was faked.**

### What could NOT be done, and why I did not force it

The participation row was **not** moved back to `SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH`.
The decision chain is **monotone by contract**:

```
launch_participation.decision_problems()
  "this decision drops market(s) the previous one authorized: ['west-palm-beach-fl']"
  "decision.lineage shrinks the authorized set: [...]"
```

A launch decision is evidence that it was made, not a toggle. Weakening that rule is a change to
shared factory code and to a core safety invariant; this order does not license it, and I did not
do it.

---

## PHASE 8 — MARKET-OWNED CHAIN REBUILT

Nothing was rebuilt from zero. No competitor discovery, Google Places, Firecrawl, Marriott or
Hilton harvest ran. Firecrawl credits unchanged at 1,199.

| | target | actual |
|---|---:|---:|
| CENSUS | 190 | **190** |
| PF | 49 | **49** |
| NP | 25 | **25** |
| ACTIONABLE UNRESOLVED | 0 | **0** |

**No count changed.** A rename moves an identity; it does not add or remove one.

---

## PHASE 9 — THE RESEALED SOURCE PACKAGE

| | |
|---|---|
| **NEW PACKAGE** | **`pkg-west-palm-beach-fl-94d6f4115daa9b88`** |
| **NEW PACKAGE DIGEST** | **`sha256:94d6f4115daa9b88a8773d2b73b49593c5de4a4757125def52b7ba17c25ec086`** |
| execution zone | `REGISTERED_LIVE` |
| created from | `0fec75a9cba946663d02b0df92f5e6011a6f551c` |
| contents | 49 PF / 25 NP / 190 census / 116 unresolved / 55 declared routes |
| `verify_seal` · `validate` | **[] · []** |
| SOURCE READY / COVERAGE READY | **YES / YES** |
| ACTIONABLE UNRESOLVED | **0** |
| **FAST** | **15/15 PASS**, 0 unknown, 0 failed |
| market bundle | `711760f09faddc8022b5d55a681c0ccd0937151a2d61be34d67cbdd0c934ef45`, 320 files / 304 html |
| FAST rule K determinism | **BYTE_IDENTICAL** |
| **PACKAGE REPRODUCIBLE / BYTE IDENTICAL** | **YES** |

Independent reproduction: two seals at the same `sealed_at`, from two separate work directories,
produced a **byte-identical** package. **No broad regression was run.**

The market-state pin was not moved and needs none: its eight counts (190/49/25/74/116/0/49/5) are
unchanged by a rename, and the lane's guard correctly refuses to move a pin that already exists.

### A gate defect found on the way, reported and not fixed

My first two seals used a **relative** `--work` path. The assembler joined it twice —
`data/fast_work/wpb4b/sb/data/fast_work/wpb4b/ob/.assemble_work/generated` — and the resulting
bundle collected **nothing**:

```
rule J   PASS   bundle e3b0c44298fc1c14…   file_count 0   html_count 0
rule K   PASS   BYTE_IDENTICAL  a=e3b0c442…  b=e3b0c442…
```

`e3b0c442…` is the sha256 of the **empty string**. Rule J passed on an empty bundle, and rule K
then "proved" determinism by comparing two empty bundles against each other. Re-run with a short
absolute work dir (`C:/t/w4a`), the same package yields 320 files and bundle `711760f0…`.

The receipt committed here is the correct one. **Rule J has no non-empty-output assertion**, so a
build that produces nothing passes the gate that exists to prove it produced something. That is a
shared-factory defect and needs its own order; I did not change it here.

---

## PHASE 10 — RE-REGISTRATION: **BLOCKED. STOPPED. NO BROAD RUN LAUNCHED.**

| | |
|---|---|
| REGISTRATION CLASS | **none assigned** — the change set does not classify as a registration |
| ELIGIBLE | **NO** |
| FULL_REGRESSION_REQUIRED | **YES** (229 modules, `assembly_required: true`) |
| **BROAD REGRESSION RUNS** | **0 — the order says STOP, and I stopped** |

The base is derived mechanically by `derive_registration_base` and cannot be overridden: *the
newest first-parent ancestor of HEAD that contains the live lineage commit, names no path of the
registering market, and carries the live commit's live-truth files.* Every commit since
`efd22bc7` names a West Palm Beach path, so the base stays at `efd22bc7` and the change set
necessarily spans **orders 002 + 003 + 004 together** — 107 paths.

```
MARKET_LOCAL_ACQUISITION               30
NEW_MARKET_REGISTRATION_DATA_ONLY      13
PERMITTED_DERIVED_REGISTRATION_OUTPUT  58
SHARED_BEHAVIOR_CHANGE                  5     <- blocks narrowing
UNKNOWN                                 1     <- blocks narrowing
                                      ----
                                      107     sum_equals_total true
```

The six blocking paths are all **order-003/004 deployment-surface artifacts**, which a
registration change set may not contain at all:

```
deploy/netlify/deployment_authorizations/ptf-auth-west-palm-beach-003-217f87eeba72.json
        -> "is protected release state"
deploy/netlify/global_deployment_manifest_candidate_west_palm_beach_003.json
        -> "is not a registration path for west-palm-beach-fl (['DEPLOYMENT_CHANGE'])"
scripts/pettripfinder/west_palm_beach_fl_candidate_accounting_003.py
scripts/pettripfinder/west_palm_beach_fl_deployment_authorization_003.py
scripts/pettripfinder/west_palm_beach_fl_launch_participation_003.py
scripts/pettripfinder/west_palm_beach_fl_withdraw_authorization_004.py
        -> not market-local: they import and write the deployment surface
```

### The deeper blocker, measured rather than assumed

I built a throwaway worktree with those paths absent and classified it. It **still** required a
broad run — so those files are not the real cause:

```
with the order-003 paths removed:  SHARED 0, UNKNOWN 0, buckets 101/101
still FAILED:
  participation      "new row status is 'FOUNDER_AUTHORIZED_FOR_LAUNCH'; a registration may only
                      write SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH;
                      the founder-authorized set moved"
  release_integrity  "the founder-authorized set is not proven unchanged"
```

**A market that has already been founder-authorized cannot be re-registered**, and the
authorization cannot be withdrawn because the decision chain is monotone (Phase 7). The two rules
are individually sound and jointly leave no narrow path for a post-authorization package
correction. The worktree was removed and the tree verified clean afterwards.

**This is the finding of the order.** The correction itself is complete, sealed and proven; what
the current factory cannot do is *re-register a corrected package for an already-authorized
market* without a broad regression.

---

## PHASE 11 — PROJECTED STAGING (from the lane's own composition)

The seal composed and recomposed the projected candidate. It is **projected and non-deployable**:
no candidate bundle was built and no authorization was issued.

| | |
|---|---|
| PARENT LOOKUP | **PASS** — live deploy `6ab1a035c7ef3b14a23a4ec6`, bundle `0ec5c655…` |
| PARENT ROUTES PRESERVED | **PASS** — `release_diff_passed true`, `finding_counts {}` |
| UNCHANGED LIVE MARKETS REBUILT | **0** (32 unchanged markets named) |
| WEST PALM BEACH BUILT | **1** |
| CANDIDATE REPRODUCIBLE | **YES** — `candidate_index_digest == recomposed_index_digest` (`sha256:91373ef9…`) |
| delta | West Palm Beach only |

| | |
|---|---:|
| PROJECTED MARKETS | **33** |
| PROJECTED PROFILES | **2,424** (2,375 + 49) |
| PROJECTED RELEASE-INDEX ROUTES | **2,701** (2,646 + 55) |
| PROJECTED SERVED SITEMAP ROUTES | **2,767** (2,711 + 55 + 1 comparison page) |

---

## PHASES 12 & 13 — NOT PERFORMED

Phase 12 authorizes the corrected cohort **"provided Phases 1–11 pass."** Phase 10 did not pass.
Therefore:

- **no new founder authorization was created**
- **no new deployment authorization was created**
- **no corrected candidate was built**, so the Phase 13 assertions could not be made against a
  built artifact

What *can* be asserted, from the sealed package rather than a candidate: the Hilton Garden Inn
Boca Raton profile is present exactly once at
`/pet-friendly-hotels/west-palm-beach-fl/hilton-garden-inn-boca-raton/`, with premises
`8201 Congress Ave, Boca Raton FL 33487`, property code `bctbrgi`, its first-party pet policy
still bound to that exact premises, no duplicate for the premises, no held or unapproved profile
published, and `apple-ten-hospitality-management-inc` absent.

---

## PHASE 14 — LIVE SAFETY

| | |
|---|---|
| CURRENT LIVE DEPLOYMENT | **`6ab1a035c7ef3b14a23a4ec6`** — unchanged |
| live markets / profiles / served routes | **32 / 2,375 / 2,711** — unchanged |
| HOST VERIFIED | **true** |
| Netlify | **never invoked** |

```
404  /pet-friendly-hotels/west-palm-beach-fl/
404  /pet-friendly-hotels/west-palm-beach-fl/boca-raton/
404  /pet-friendly-hotels/west-palm-beach-fl/hilton-garden-inn-boca-raton/
404  /pet-friendly-hotels/west-palm-beach-fl/apple-ten-hospitality-management-inc/
200  /pet-friendly-hotels/fort-lauderdale-fl/
200  /pet-friendly-hotels/miami-fl/
404  /pet-friendly-hotels/detroit-ann-arbor-mi/
```

---

## WHAT THE FOUNDER HAS TO DECIDE

West Palm Beach is corrected and sealed but cannot be re-registered narrowly. Three ways forward,
none of which this order was licensed to take:

1. **Authorize one broad regression run** for the re-registration. The classifier asks for 229
   modules and a fresh assembly. This is the smallest change to the current factory — it simply
   pays the price the doctrine asks.
2. **Add a canonical re-registration path** for an already-authorized market: a supported
   withdrawal that preserves the chain's evidence (for example an explicit
   `WITHDRAWN_PENDING_CORRECTION` status that the monotonicity check recognises) plus a
   registration base that may include the market's own prior registration. This is the durable
   fix and needs its own order.
3. **Deploy nothing and leave West Palm Beach out of the next release.** Safe today: no deployable
   authorization exists, and the market is absent from production.

Separately, and independent of West Palm Beach: **FAST rule J passes on an empty bundle.** A
relative `--work` path is enough to trigger it. That gate should assert a non-empty output before
rule K claims determinism from it.

---

## FINAL ANSWERS

1. **OLD CANONICAL NAME** = `Apple Ten Hospitality Management Inc`
2. **CORRECT CANONICAL NAME** = `Hilton Garden Inn Boca Raton`
3. **LICENSEE NAME** = `APPLE TEN HOSPITALITY MANAGEMENT INC` (DBPR `HOT6013438`; retained in the row's evidence)
4. **PROPERTY CODE** = `bctbrgi`
5. **IDENTITY_KEY BEFORE** = `apple ten hospitality management inc`
6. **IDENTITY_KEY AFTER** = `hilton garden inn boca raton`
7. **OLD ROUTE** = `/pet-friendly-hotels/west-palm-beach-fl/apple-ten-hospitality-management-inc/`
8. **NEW ROUTE** = `/pet-friendly-hotels/west-palm-beach-fl/hilton-garden-inn-boca-raton/`
9. **FIRST-PARTY POLICY REBOUND** = **YES** — `bctbrgi`, `full_premises_match true`, same artifact `8cde8c6f…`, 0 re-acquisition
10. **PUBLISHABLE NAMES AUDITED** = **49**
11. **SUBSTANTIVE NAME DISAGREEMENTS REMAINING** = **0**
12. **OLD DEPLOYMENT AUTHORIZATION STATUS** = **`SUPERSEDED`** (terminal, unconsumed, history preserved)
13. **OLD AUTHORIZATION CANNOT DEPLOY NEW BYTES** = **YES** — terminal non-deployable status, plus `bundle_sha256` binding to `217f87ee…` which the corrected package cannot produce; and no other deployable authorization exists
14. **NEW PACKAGE** = `pkg-west-palm-beach-fl-94d6f4115daa9b88`
15. **NEW PACKAGE DIGEST** = `sha256:94d6f4115daa9b88a8773d2b73b49593c5de4a4757125def52b7ba17c25ec086`
16. **SOURCE READY** = **YES**
17. **COVERAGE READY** = **YES**
18. **FAST** = **15/15 PASS** (0 unknown, 0 failed)
19. **PACKAGE REPRODUCIBLE** = **YES** — byte-identical across two independent seals
20. **REGISTRATION CLASS** = **NONE ASSIGNED** — the change set does not classify as a registration
21. **ELIGIBLE** = **NO**
22. **FULL_REGRESSION_REQUIRED** = **YES**
23. **BROAD REGRESSION RUNS** = **0** — required, refused, STOPPED per the order
24. **UNCHANGED MARKETS REBUILT** = **0**
25. **WEST PALM BEACH PROFILES** = **49**
26. **NEW FOUNDER AUTHORIZATION ID** = **NONE** — Phase 12 is conditional on Phases 1–11 passing; Phase 10 did not
27. **NEW DEPLOYMENT AUTHORIZATION ID** = **NONE**
28. **NEW AUTHORIZED CANDIDATE BUNDLE** = **NONE** — no candidate was built
29. **NEW AUTHORIZED CANDIDATE SITEMAP** = **NONE**
30. **CANDIDATE MARKETS** = **33** (projected, non-deployable)
31. **CANDIDATE PROFILES** = **2,424** (projected)
32. **CANDIDATE RELEASE-INDEX ROUTES** = **2,701** (projected)
33. **CANDIDATE SERVED ROUTES** = **2,767** (projected)
34. **ALL RELEASE GATES** = **NOT RUN** — they gate a candidate this order was not licensed to build
35. **CURRENT LIVE MODIFIED** = **NO**
36. **DEPLOYMENT PERFORMED** = **NO**
37. **WEST PALM BEACH LIVE** = **NO**
38. **origin == HEAD** = **YES**
39. **tree clean** = **YES**
40. **READY FOR WEST PALM BEACH PRODUCTION DEPLOYMENT** = **NO** — the identity is fixed and the old bytes are non-deployable, but no founder authorization and no candidate exist for the corrected package

---

WEST PALM BEACH IDENTITY CORRECTION = PASS
HILTON GARDEN INN BOCA RATON IDENTITY = PASS
SUBSTANTIVE PUBLISHED NAME ERRORS = 0
OLD AUTHORIZED BYTES DEPLOYED = NO
CURRENT LIVE MODIFIED = NO
WEST PALM BEACH DEPLOYED = NO
READY FOR WEST PALM BEACH PRODUCTION DEPLOYMENT = NO
