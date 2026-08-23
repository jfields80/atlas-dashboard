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
| Publication-grade observations | 17 | **92** |
| Founder-review candidates | 17 (4.8% of active) | **92 (25.8%)** |
| Acquired VALID | 19 of 138 (13.8%) | **94 of 200 (47.0%)** |
| Lanes that ran | direct_http only | Firecrawl, Browser API, Web Unlocker |
| Provider spend | $2.52 (discovery) | **$2.41** (acquisition) |

## B. The run was interrupted, and nothing was lost

The paid run was killed at **93 of 212** cohort properties. Every completed
property had already been journalled before the next began, so no paid capture
was lost — the durability rule that cost PTF-BRIGHTDATA-CROSS-BRAND-PILOT-002
nineteen paid captures earned its keep here.

The process died before writing its report. `--report-only` was added so a
killed run still produces its artifact from the journal alone, spending nothing.

**120 cohort properties are unattempted and $7.59 of the $10 cap is unspent.**
The run stopped because it was interrupted, not because it hit a ceiling. It
resumes from the journal with one command; nothing already acquired is re-bought.

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

## D. Acquisition — 93 attempted, 75 publication-grade

| Family | VALID | Attempted | Lane | MARKET-001 |
|---|---|---|---|---|
| Wyndham | **26** | 31 | Firecrawl | 2 of 37 |
| Choice | **23** | 31 | Firecrawl | never fetched (timeout) |
| IHG | **16** | 19 | Firecrawl | never fetched (403) |
| Marriott | **10** | 12 | Browser API | never fetched (403) |

Every route the registry named performed as its row predicted. **Zero provider
decisions were reopened and zero new source families were added.**

Hilton (43), Red Roof (4), Motel 6 (6), Sonesta (1), Drury (4) and 34
independents were in the queue behind Marriott and were never reached.

**No family circuit breaker tripped.** Every family that ran produced
publication-grade records, so no approved source-family route failed
systematically and none was stopped.

## E. Spend — $2.41 of a $10 cap, metered twice

| | |
|---|---|
| Measured (vendor per-zone month-to-date growth) | **$2.41** |
| Estimated (this run's own per-property pricing) | $2.27 |
| Cap enforced on | `max(measured, estimated)` |
| Firecrawl | 81 plan credits of 884 — **no dollar figure asserted** |
| Bright Data Browser | 11 properties |
| Bright Data Web Unlocker | 7 fallbacks |

The cap binds on the larger of two numbers because neither alone is safe. The
account balance lags roughly 3x and RISES on a top-up
(PTF-MILWAUKEE-ROUTER-INTEGRATION-001); the per-zone meter is monotonic but
settles minutes after a session (PTF-CANONICAL-LOCATOR-FRESH-PROOF-019A), so a
cap enforced on it alone overshoots during the lag.

**The two meters agreed to within 14 cents over 93 properties.** That agreement
is the evidence the cap would have bound correctly had the run continued — and
it is measured, not asserted: the browser lane's real cost came out at 15.8
cents per property against a registry figure of 16.0.

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
| HELD_REVIEW | **92** | 17 |
| ACCESS_UNRESOLVED | 184 | 263 |
| INSUFFICIENT_EVIDENCE | 66 | 63 |
| POLICY_NOT_FOUND | 15 | 14 |
| AUTHORITY_PET_FRIENDLY | **0** | 0 |
| AUTHORITY_VERIFIED_NO_PETS | **0** | 0 |
| **Total** | **357** | 357 |

Reconciled by SET: `missing=[] foreign=[] duplicate=[]`, active denominator 357.

`POLICY_NOT_FOUND` is still said only of properties whose own page served and
was silent. The 120 unattempted cohort rows are `ACCESS_UNRESOLVED` — a
statement about us, not about the hotel.

Partition: `AWAITING_FOUNDER_DECISION` 92,
`AWAITING_POLICY_OBSERVATION` 96, `AWAITING_ATTENDED_CAPTURE` 68,
`AWAITING_OFFICIAL_URL` 60, `ACCESS_BLOCKED` 22, `AWAITING_ROUTING_REVIEW` 13,
`AWAITING_PROPERTY_LEVEL_URL` 4, `AWAITING_POLICY_ARTIFACT` 2.

## I. Founder review — 92 candidates (25.8% of active)

60 recommend pet-friendly, 29 recommend verified-no-pets, 3 recommend hold.
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

**85 new tests** — 74 in four new files, 11 added to the routing suite.

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
| Observed / acquired | ≥ 85% | 13.8% | **47.0%** | MISS |
| Publication-grade of active | ≥ 80% | 4.8% | **25.8%** | MISS |
| Active closure | = 100% | 100% | **100.0%** | MET (required) |
| Provider spend | ≤ $10 | $2.52 | **$2.41** | MET |
| Manual / custom architecture | minimal | 10 modules, 0 scripts | **4 modules, 0 scripts** | MET |
| Elapsed | 4–8 h | 2.01 h | **4.05 h** | MET |

Routing fell 79.3% → 78.4% because three rows were **correctly** demoted from a
brand city-search page. That is a number getting more honest, not worse.

The three acquisition misses are all bounded by the same fact: **the run covered
93 of 212 cohort properties.** The remaining 119 are not known to be
unreachable — they were not tried.

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
ST. LOUIS FOUNDER REVIEW READY     = YES  (92 candidates)
ST. LOUIS REGISTERED               = FALSE
ST. LOUIS PUBLISHED                = FALSE
ST. LOUIS DEPLOYED                 = FALSE
```

## N. Next

1. **Resume the paid cohort.** 119 properties, $7.59 of cap unspent. Hilton (43)
   is the largest untouched brand and the registry measures it at 100% on the
   Browser API. Same command, `--report-only` removed; the journal skips the 93.
2. **Founder review of 92 candidates** — now worth one sitting.
3. **Apply the 5 recovered URLs** via `--url-overlay` on the next paid pass.
4. **Census correction**: 32 suspected duplicate pairs, 8 held identity-key
   collisions, 21 no-locality rows.
