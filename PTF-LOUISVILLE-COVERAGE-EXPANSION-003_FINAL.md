# PTF-LOUISVILLE-COVERAGE-EXPANSION-003 — FINAL

**Market:** louisville-ky · **As of:** 2026-08-24 · **Census:** 166, unchanged
**Registered:** FALSE · **Published:** FALSE · **Deployed:** FALSE · **Founder decisions written:** 0

Coverage was raised on the existing 166-identity census. No discovery was re-run,
no geography was rebuilt, no census row was added, removed or edited.

---

## The funnel, before and after

| | Before (002) | After (003) |
|---|---|---|
| CENSUS | 166 | **166** |
| ROUTED | 84 | **101** |
| ATTEMPTED (cumulative) | 77 | **98** |
| VALID (cumulative) | 62 | **82** |
| FOUNDER-REVIEW CANDIDATES | 43 | **63** |
| PROPOSED PET_FRIENDLY | 24 | **37** |
| PROPOSED VERIFIED_NO_PETS | 11 | **16** |
| APPROVE_WITH_CHANGE | 4 | **5** |
| HOLD | 4 | **5** |
| CLOSURE | 166 / 166 | **166 / 166** |

Routing states: `ROUTED 84 → 101`, `NEEDS_OFFICIAL_URL 70 → 55`,
`NEEDS_PROPERTY_URL 8 → 6`, `BRAND_EXCLUDED 4 → 4`. Auto-routed 50.6% → 60.8%.

---

## Phase 1 — zero-cost URL recovery (70 rows examined)

**15 official URLs recovered**, every one a `PROPERTY_PAGE`. 55 rows remain
without a URL. Zero network calls, zero spend.

| Binding key | Recoveries |
|---|---|
| `STREET_AND_POSTAL_CODE` | 7 |
| `NAME_AND_POSTAL_CODE` | 6 |
| `PHONE` | 2 |

Every recovery names the sighting it came from and the key that bound it, in
`launch_packages/pettripfinder/louisville_ky_url_recovery_003.json`.

The evidence families read: the OpenStreetMap discovery cache from the 002
census pass, the preserved 001 census, and every 001 report and capture manifest
on disk. **All 15 came from the 001 census.** The OSM cache contributed none:
64 of its 65 URL-bearing sightings describe rows that already have a URL.

## Phase 2 — NEEDS_PROPERTY_URL (8 rows examined)

**2 of 8 become ROUTED.**

- `comfort suites east` — street+postal → a Choice property page
- `the seelbach hilton hotel` — telephone → its Hilton property page, displacing
  the bare domain `seelbachhilton.com`

The other **6 are one defect**: they all carry the same census URL,
`choicehotels.com/kentucky/shepherdsville/sleep-inn-hotels` — a Sleep Inn in a
different city. Seven Louisville identities inherited one bulk-edited
OpenStreetMap `website` tag. Each of the six binds correctly on its own
telephone number and each was refused because the URL names no distinctive word
of the hotel it claims to be. No brand homepage, city search, category listing
or third-party page was accepted: the shape classifier refuses them and the
overlay refuses any proposal it cannot classify as fetchable.

## Phase 3 — prior-001 reconciliation

- **Old rows matched: 17** — the whole recovered set, bound to the preserved
  130-identity 001 census by telephone, name+postal, or street+postal.
- **Useful source URLs recovered: 17.**
- **Useful evidence recovered: 0 beyond URLs.** No old authority was carried
  forward; no approval, decision or published fact from 001 was reused.
- **Old reports and capture manifests: 0 additional URLs.** Measured, not
  assumed: 91 identity keys carry URLs across them, 0 are absent from the 001
  census, and 0 belong to a prior row whose census URL is empty.
- **Duplicates / renames detected:** the Galt House pair (`rivue tower` and
  `the galt house hotel trademark collection by wyndham`) share one street
  address and one 001 predecessor. Both were refused.
- **Rows refused because identity does not safely bind: 53.** Seven were refused
  with a bound-but-rejected URL, and every refusal is recorded beside the row it
  was refused for.

## Phase 4 — routing rebuild

The census file was never edited. The 17 recovered URLs are an overlay applied
for routing only, and closure and the benchmark now route with the same overlay
the paid pass routed with.

## Phase 5 — cohort (34)

| Provenance | Count |
|---|---|
| Newly routed by URL recovery | 13 |
| Previously deferred by the 002 cap | 13 |
| Retried after an attempt that answered nothing | 8 |
| Routed before and never attempted | 0 |

Providers: 23 `brightdata_browser`, 11 `firecrawl`.
Families: HILTON 10, CHOICE 6, MARRIOTT 6, INDEPENDENT 5, IHG 4, DRURY 1,
MOTEL6 1, WYNDHAM 1.

**No property is bought twice.** 67 routed identities were settled by a terminal
outcome (60 VALID, 7 IDENTITY_MISMATCH) and none appears in the cohort; the run
directory's journal was empty when the pass began. The 8 retries are named
individually with the outcome that failed to answer them (6 UNEXPECTED_PAGE,
1 ACCESS_DENIED, 1 UNHYDRATED) — a property that was paid for and
answered nothing is not a property that was answered.

## Phase 6 — cost plan, printed before the first call

| | |
|---|---|
| Firecrawl-credit cohort | 11 properties, 0 dollars |
| Bright Data browser cohort | 23 properties |
| Projected at the measured rate (15.19¢ = 002's 881¢ ÷ 58) | 349.37¢ |
| Projected at the registry rate (16.0¢) | 368¢ |
| Unlocker fallback exposure (5¢ × 23) | 115¢ |
| Worst case | 483¢ |
| **Vendor balance** | **494¢** |
| Authorised cap | 1000¢ |
| **Recommended cap** | **444¢** |

The Bright Data balance was **$4.94, below the $10 authorisation**, and the
preflight gate refuses a cap the account cannot cover — the first dry run
stopped before spending for exactly that reason. The run cap was set to $4.44,
90% of the balance. That is less than authorised, so the pass stayed inside its
authorisation; **$5.56 of the authorisation is unspent and needs a top-up.**

## Phase 7 — paid acquisition

| | |
|---|---|
| Attempted | **29 of 34** |
| Outcome | `STOPPED_HARD_CAP` — 420 of 444 cents measured; the next metering interval would have cost ~72 more |
| VALID | 20 |
| UNEXPECTED_PAGE | 5 |
| ACCESS_DENIED | 2 |
| POLICY_NOT_FOUND | 1 |
| UNHYDRATED | 1 |
| Deferred | 5 (`21c museum hotel`, `hotel bourre bonne`, `hotel genevieve`, `radisson hotel louisville north`, `the myriad hotel`) |
| Bright Data spend | **$4.20** |
| Firecrawl credits | **11** |
| Elapsed | 0.84 h |

Every identity was journalled before the next began. No new provider was tried.

**The 8 retries returned nothing.** Of the 29 attempted, 21 were properties this
market had never reached — 20 came back VALID and 1 POLICY_NOT_FOUND, so every
one of them was answered. The other 8 were the properties a prior pass had
already paid for and failed to read, and all 8 failed again on the same lanes
(5 UNEXPECTED_PAGE, 2 ACCESS_DENIED, 1 UNHYDRATED). At the measured unit price
they consumed roughly **$1.20 of the $4.20 and produced no fact.**

Your Phase 5 definition excluded them. The generic cohort derivation does not:
it subtracts prior outcomes that ANSWERED a property, and an access failure
answers nothing, so those 8 came back automatically. Declaring them settled to
keep them out would have written into the artifact that a page nobody could read
had answered its question, so they were kept and named instead. The evidence now
says they should be excluded next time: **a retry of an access failure on the
same lane does not convert, and needs a different lane or an attended capture.**

## Phase 8 — offline closeout (zero cost)

- Declined-evidence recovery over **both** run directories: 8 captures re-read,
  7 `DOCUMENT_NAMES_A_DIFFERENT_PROPERTY`, 1 `NO_RECOVERY_THE_DOCUMENT_IS_AS_SILENT_AS_THE_BLOCK`.
- Three acquisition passes merged: 98 identities, 8 superseded.
- Observation store rebuilt: **63 observations**, all `PUBLICATION_GRADE_CONFIRMED`
  (41 POLICY_CONFIRMED, 17 POLICY_NEGATIVE_CONFIRMED, 4 POLICY_NOT_FOUND,
  1 POLICY_PARTIAL), plus 19 rows restating prior evidence that carry no capture.
- Closure rebuilt: **166 / 166**, reconciling with 0 missing, 0 duplicate,
  0 foreign — HELD_REVIEW 63, ACCESS_UNRESOLVED 41, INSUFFICIENT_EVIDENCE 61,
  POLICY_NOT_FOUND 1.
- Founder-review packet rebuilt: **63 candidates**, every one
  `MACHINE_REVIEWED_PENDING_OPERATOR`.
- Machine review: 37 APPROVE_PET_FRIENDLY, 16 APPROVE_VERIFIED_NO_PETS,
  5 APPROVE_WITH_CHANGE, 5 HOLD. **No founder decision was written.**
- Benchmark rebuilt.

---

## What remains

| | |
|---|---|
| Remaining unrouted | **65** (55 no official URL, 6 no property URL, 4 brand-excluded) |
| Remaining unattempted (routed) | **5 deferred by the cap** |
| Remaining unsettled after attempt | 8 (5 UNEXPECTED_PAGE, 2 ACCESS_DENIED, 1 UNHYDRATED) |
| Closure | **166 / 166** |

---

## Engineering

One generic module added — `scripts/pettripfinder/acquisition/cohort_cost_plan.py`
— and five shared modules changed. **Zero Louisville-specific scripts.**

Five interventions, each a defect this market found in the shared factory:

1. `census_url_recovery` bound on the first key that matched, so one bulk-edited
   OSM URL consumed six Choice identities a weaker key would have routed
   correctly. A rejected URL now falls through to the next key.
2. Two sightings can bind equally well and carry different URLs. The Seelbach
   binds on its telephone to both a bare domain and its Hilton property page;
   the usable one is now preferred over whichever came first in the list.
3. The overlay may now displace a census URL **only** when no lane can fetch it.
4. Closure and the benchmark routed without the overlay the paid pass routed
   with, and would have reported this market as less routed than it is.
5. The observation store crashed on a VALID row that restates prior evidence and
   carries no capture; those rows are now counted as restated.

---

## Declarations

```
LOUISVILLE CENSUS COMPLETE          = YES
LOUISVILLE CENSUS TOTAL             = 166
LOUISVILLE COVERAGE EXPANSION COMPLETE = NO
LOUISVILLE FOUNDER REVIEW PACKAGE READY = YES

LOUISVILLE REGISTERED = FALSE
LOUISVILLE PUBLISHED  = FALSE
LOUISVILLE DEPLOYED   = FALSE
```

Coverage expansion is **not complete**: 65 identities are still unrouted, 5
routed identities were deferred when the cap bound, and the cap that bound was
the vendor balance rather than the authorisation. The founder-review package is
ready — 63 candidates, machine-reviewed, every one awaiting a human.
