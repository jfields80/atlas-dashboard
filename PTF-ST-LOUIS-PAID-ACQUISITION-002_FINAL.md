# PTF-ST-LOUIS-PAID-ACQUISITION-002 — Paid Acquisition, FINAL

**Market:** `st-louis-mo` **Branch:** `feature/ptf-st-louis-market-001`
**Start HEAD:** `7d3cfee`
**Status:** paid cohort partially acquired, closed, packaged for founder review.
**PUBLISHED = FALSE. DEPLOYED = FALSE. NOT REGISTERED. NOT LAUNCH-AUTHORIZED.**

The machine-readable form of every number below is
`launch_packages/pettripfinder/st_louis_mo_benchmark_002.json`. Each is read out
of another committed artifact, so any of them can be re-derived.

---

## A. What changed since MARKET-001

MARKET-001 built St. Louis with **no paid credential in the environment**. Its
three acquisition misses had one cause: 145 of 283 routed properties — every
Marriott, Hilton, IHG, Choice, Motel 6 and Red Roof — had never been fetched by
anything.

002 stopped twice on a Bright Data `407 wrong_password`. The operator corrected
the zone password; this session's preflight returned **all three lanes
AUTHENTICATED** and the paid cohort ran.

| | MARKET-001 | PAID-002 |
|---|---|---|
| Publication-grade observations | 17 | **122** |
| Founder-review candidates | 17 (4.8% of active) | **122 (34.2%)** |
| Acquired VALID | 19 of 138 (13.8%) | **124 of 239 (51.9%)** |
| Lanes that ran | direct_http only | Firecrawl, Browser API, Web Unlocker |
| Provider spend | $2.52 (discovery) | **$10.82** (acquisition) |

## B. THE CAP WAS EXCEEDED BY $0.82

**Final cumulative Bright Data spend: $10.82 against a $10.00 cap - 8.2% over.**
This is a breach and is reported as one.

Two causes, both in code this work order wrote.

1. **The guard stopped when exceeded, not before exceeding.** It asked
   `binding >= cap`. `budget.Budget`'s own docstring rules that out: *"Every
   ceiling is checked BEFORE an attempt is spent, never after. A budget that
   notices it was exceeded has already been exceeded."* It reserved no headroom,
   so with the vendor metered every fifth property, up to five could commit
   between readings with nothing but the estimate watching.
2. **The estimate was priced from another market.** The registry puts the
   Browser API at 16.0c/property, measured on PTF-ACQUISITION-BRAND-REPAIR-003.
   St. Louis's Marriott and Hilton pages cost **20.9c** - so the estimate ran
   30% light and could not catch the overrun either.

Both are fixed. The cap now reserves a whole metering interval priced at the
run's **own** measured rate, falling back to the registry only until it has
eight properties of its own evidence. Seven tests pin it, one replaying the
exact numbers that overshot. **The fix cannot undo this bill.**

A second defect, found in the same triage and worse in kind: **the resumed run
reported only its own batch instead of the journal.** The merge saw 39 rows
instead of 132, and the founder package fell from 122 candidates to 47 - 75
properties that had been paid for and read vanished from the market's current
state, with every downstream artifact quietly consistent with the smaller
number. The report is now a projection of the journal. Two tests pin it.

**81 cohort properties remain unattempted** and no budget remains to reach them.

## C. Cohort — 212, derived by subtraction

Every ROUTED identity minus the ones whose question is already answered:

| Prior outcome | Count | Why it is settled |
|---|---|---|
| VALID | 19 | the page served and its policy was located and read |
| POLICY_NOT_FOUND | 14 | the page served and was silent; a costlier lane receives the same nothing |
| IDENTITY_MISMATCH | 35 | the page is about a DIFFERENT hotel — a routing defect, not an access one |
| **Settled** | **68** | |
| **Cohort** | **212** | never attempted, unhydrated, access denied, navigation failed, unexpected page |

The cohort and the settled set partition the routed population exactly; a test
asserts it.

## D. Acquisition - 132 attempted, 122 publication-grade

| Family | VALID | Attempted | Lane | MARKET-001 |
|---|---|---|---|---|
| Marriott | **32** | 38 | Browser API | never fetched (403) |
| Wyndham | **26** | 31 | Firecrawl | 2 of 37 |
| Choice | **23** | 31 | Firecrawl | never fetched (timeout) |
| IHG | **16** | 19 | Firecrawl | never fetched (403) |
| **Hilton** | **8** | 11 | Browser API | never fetched (403) |

Every route the registry named performed as its row predicted. **Zero provider
decisions were reopened and zero new source families were added.**

**Hilton was entered and then cut off by the cap at 11 of 43** - 8 VALID, 2
ACCESS_DENIED, 1 POLICY_NOT_FOUND. On that sample the lane works; the brand is
unfinished for budget reasons, not capability ones.

Never reached at all: 32 more Hilton, 34 independents, Motel 6 (6), Drury (4),
Red Roof (4), Sonesta (1).

**No family circuit breaker tripped.** Every family that ran produced
publication-grade records, so no approved source-family route failed
systematically and none was stopped.

## E. Spend - $10.82 against a $10 cap, metered twice

| | |
|---|---|
| Measured (vendor per-zone month-to-date growth) | **$10.82** |
| Estimated (per-property pricing) | $9.06 - 16% light, which is the defect |
| Cap enforced on | `max(measured, estimated)`, now plus a reservation |
| Firecrawl | **93 plan credits** of 884 - no dollar figure asserted |
| Bright Data Browser | 43 properties |
| Bright Data Web Unlocker | 25 fallbacks |
| Measured browser rate | **20.9c/property** vs a registry 16.0c |

The cap binds on the larger of two numbers because neither alone is safe. The
account balance lags roughly 3x and RISES on a top-up
(PTF-MILWAUKEE-ROUTER-INTEGRATION-001); the per-zone meter is monotonic but
settles minutes after a session (PTF-CANONICAL-LOCATOR-FRESH-PROOF-019A), so a
cap enforced on it alone overshoots during the lag.

Over the first 93 properties the two meters agreed to within 14 cents, and the
browser rate measured 15.8c - indistinguishable from the registry's 16.0c. That
agreement did not hold: Marriott and Hilton are heavier pages than the brands
the registry figure was measured on, and over the next 39 properties the real
rate was **20.9c**. A unit price is a property of the pages, not of the lane,
which is exactly why the cap now calibrates from the run's own bill.

## F. Two defects found, both fixed

### 1. A city-search page was routed as a property page, and answered for a hotel

Three census identities — two Comfort Inns and a Sleep Inn — carried **one**
Choice URL: `/missouri/saint-louis/quality-inn-hotels`. Three hotels cannot
share a property page. Being shaped like one, it was routed, fetched, **passed
the capture's identity gate** on city and brand family alone, and returned
`POLICY_NOT_FOUND` — a claim about a hotel made from a page that is not that
hotel's.

`classify_url_shape` now refuses a path whose LAST segment is a category of
hotels, while keeping the same path with a property code after it
(`/illinois/alton/comfort-inn-hotels/il008`). Routed falls 283 → 280 and
`urls_claimed_more_than_once` — the general form of the check — now reports
**zero** shared URLs among routed rows.

### 2. Firecrawl declines persisted nothing, so their silence was unfalsifiable

PTF-MILWAUKEE-CLOSURE-ASSESSMENT-031 established that a decline persisting no
document is an assertion nobody can check. The free lane preserved 49 documents
in this market. **Firecrawl preserved none** — its `POLICY_NOT_FOUND` rows were
exactly the assertions 031 ruled out.

`firecrawl_capture` now keeps its declined documents under the existing
`ptf-declined-capture/1.0` contract. The judgement is unchanged; only the audit
trail is added. **This fix is not retroactive:** the 12 Firecrawl declines in
THIS run have no persisted document, and 2 of the 15 `POLICY_NOT_FOUND` rows in
the closure ledger are therefore not falsifiable. A re-run of those two would
fix it and is not worth $0.02 of anyone's attention until the lane runs again.

A third, smaller one: `zero_cost_recovery` took a single run directory, so the
first closeout reported that this market's offline recovery examined **nothing**
while 49 preserved documents sat on disk unread. `--run-dir` is now repeatable.

## G. Source discovery — 5 of 60 recovered, at zero cost

60 identities have no official URL. Before buying any, the discovery payloads
this market already paid for were re-read: **469 cached provider sightings carry
a URL**.

- **5 recovered**, every one bound on a matching **telephone number**, every one
  a PROPERTY_PAGE shape. Routing would rise 280 → 285 (78.4% → 79.8%) if applied.
- **55 still unknown** — no cached sighting binds to them at all.

Binding is deliberately strict: telephone digits equal, or name AND postal code
both equal. **An empty field never matches an empty field** — a first draft
bucketed by `digits(phone)`, put every phoneless row in one bucket keyed by the
empty string, and married fifty hotels to one unrelated bed-and-breakfast.

The recoveries are **proposed, not applied.** The census remains the record of
what discovery OBSERVED; a URL derived by re-reading a payload is a proposal,
and writing it into the census would make a derivation indistinguishable from an
observation. `--url-overlay` layers them for routing when a run is authorized to
use them.

## H. Closure — 357 / 357 (100%)

| Disposition | Count | 001 |
|---|---|---|
| HELD_REVIEW | **122** | 17 |
| ACCESS_UNRESOLVED | 153 | 263 |
| INSUFFICIENT_EVIDENCE | 66 | 63 |
| POLICY_NOT_FOUND | 16 | 14 |
| AUTHORITY_PET_FRIENDLY | **0** | 0 |
| AUTHORITY_VERIFIED_NO_PETS | **0** | 0 |
| **Total** | **357** | 357 |

Reconciled by SET: `missing=[] foreign=[] duplicate=[]`, active denominator 357.

`POLICY_NOT_FOUND` is still said only of properties whose own page served and
was silent. The 81 unattempted cohort rows are `ACCESS_UNRESOLVED` - a statement
about us, not about the hotel.

Partition: `AWAITING_FOUNDER_DECISION` 122, `AWAITING_ATTENDED_CAPTURE` 71,
`AWAITING_OFFICIAL_URL` 60, `AWAITING_POLICY_OBSERVATION` 58, `ACCESS_BLOCKED`
27, `AWAITING_ROUTING_REVIEW` 13, `AWAITING_PROPERTY_LEVEL_URL` 4,
`AWAITING_POLICY_ARTIFACT` 2.

## I. Founder review - 122 candidates (34.2% of active)

80 recommend pet-friendly, 39 recommend verified-no-pets, 3 recommend hold.
Every row is `MACHINE_REVIEWED_PENDING_OPERATOR` with empty decision fields and
carries its `semantic-approval/1.0` projection and hash.

**No authority was created.** `AUTHORITY_PET_FRIENDLY` and
`AUTHORITY_VERIFIED_NO_PETS` remain at zero and are unreachable from this code
path; only a founder decision produces one.

## J. Architecture — 4 new generic modules, 0 market-specific scripts

`acquisition/market_paid_acquisition.py` · `acquisition/acquisition_merge.py` ·
`discovery/census_url_recovery.py` · `market_closeout.sh`

**6 shared files modified, all additive:** the URL-shape classifier and its
shared-URL diagnostic; Firecrawl declined persistence; the observation store
reading provider/reader/capture_method from the row instead of asserting
`direct_http`/`generic`/`deterministic_fetch`; the closure partition naming the
lane that was refused instead of saying "the free lane"; `--suffix` on the
benchmark so a second pass cannot silently re-report the first; repeatable
`--run-dir` on zero-cost recovery.

**96 new tests** — 85 in four new files, 11 added to the routing suite.

The merge module exists because every downstream reader took ONE acquisition
report. That was true while a market had one pass and quietly wrong the moment
it had two: a property acquired by the paid lane still read UNHYDRATED from the
free lane's report, and closure would tell a founder ACCESS_UNRESOLVED about a
hotel whose policy was already on disk. An evidence-bearing outcome is never
overwritten by one that carries none — a later transport failure does not
un-read a policy.

## K. Benchmark scorecard

| Metric | Target | 001 | 002 | Verdict |
|---|---|---|---|---|
| Automatic routing | ≥ 90% | 79.3% | **78.4%** | MISS |
| Observed / acquired | ≥ 85% | 13.8% | **51.9%** | MISS |
| Publication-grade of active | ≥ 80% | 4.8% | **34.2%** | MISS |
| Active closure | = 100% | 100% | **100.0%** | MET (required) |
| Provider spend | ≤ $10 | $2.52 | **$10.82** | **BREACH** |
| Manual / custom architecture | minimal | 10 modules, 0 scripts | **4 modules, 0 scripts** | MET |
| Elapsed | 4–8 h | 2.01 h | **6.55 h** | MET |

Routing fell 79.3% → 78.4% because three rows were **correctly** demoted from a
brand city-search page. That is a number getting more honest, not worse.

The two acquisition misses are bounded by one fact: **the run covered 132 of 212
cohort properties before the cap stopped it.** The remaining 81 are not known to
be unreachable — there was no money left to try them.

## L. Production safety

Unchanged and proved by `tests/pettripfinder/test_st_louis_production_safety_001.py`:
the five live markets are still the only founder-authorized set,
`launch_participation.json` still hashes to what the manifest pins,
`global_deployment.verify_manifest` returns `[]`, the 047 deployment record and
signed authorization are byte-untouched, measurement is disabled and zero
affiliates are enrolled.

## M. Status

```
ST. LOUIS CENSUS COMPLETE          = YES  (357 identities)
ST. LOUIS ACTIVE CLOSURE COMPLETE  = YES  (357/357, reconciled by set)
ST. LOUIS FOUNDER REVIEW READY     = YES  (122 candidates)
ST. LOUIS PAID COHORT EXHAUSTED    = NO   (132 of 212; 81 unattempted)
ST. LOUIS BUDGET CAP REACHED       = YES  (exceeded: $10.82 of $10.00)
ST. LOUIS REGISTERED               = FALSE
ST. LOUIS PUBLISHED                = FALSE
ST. LOUIS DEPLOYED                 = FALSE
```

## N. Next

1. **Founder review of 122 candidates** — the highest-value action now, and the
   only one that needs no budget.
2. **A budget decision before any further acquisition.** 81 cohort properties
   remain: 32 Hilton, 34 independents, Motel 6 6, Drury 4, Red Roof 4, Sonesta 1.
   At the measured 20.9¢ that is roughly **$17**, and this work order has no
   remaining authorization. Hilton returned 8 VALID of its first 11, so the
   32 unfinished rows are a budget question, not a capability one.
3. **Apply the 5 recovered URLs** via `--url-overlay` whenever a paid pass is
   next authorized.
4. **Census correction**: 32 suspected duplicate pairs, 8 held identity-key
   collisions, 21 no-locality rows — all free.
