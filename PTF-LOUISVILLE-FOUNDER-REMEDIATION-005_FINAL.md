# PTF-LOUISVILLE-FOUNDER-REMEDIATION-005 — FINAL

**Market:** louisville-ky · **Census:** 166, unchanged · **Candidates:** 63
**Spend:** $0.00 · **Provider calls:** 0 · **Pages re-fetched:** 0
**Registered / Published / Deployed:** FALSE / FALSE / FALSE · **Founder signature:** not written

---

## Result

| Disposition | Before (004) | **After remediation** |
|---|---|---|
| APPROVE_PET_FRIENDLY | 30 | **45** |
| APPROVE_VERIFIED_NO_PETS | 14 | **17** |
| APPROVE_WITH_CHANGE | 15 | **0** |
| HOLD | 4 | **1** |
| **CLEAN SIGNABLE TOTAL** | 44 | **62** |

Closure **166 / 166**, reconciling with 0 missing, 0 duplicate, 0 foreign.

**Every one of the 15 corrections is applied.** Not one is deferred, and no
correction was applied by typing a value: each is either a name the property's
own page states, or a fact its own persisted block states that the reader now
reads.

---

## The two founder decisions, as folded in

### 1. The Seelbach Hilton — one property

Recorded in `markets/founder_overrides/louisville-ky.json` as an identity
override, with the three signals the founder named:

| Signal | Census | Page | Verdict |
|---|---|---|---|
| Street | 500 South 4th Street, Louisville 40202 | 500 S 4TH Street | EXACT MATCH |
| Telephone | 5025853200 | +1 502-585-3200 | EXACT MATCH |
| Property code | — | `sdfshhf`, and the source URL is that code's own page | AGREES |

The canonical name is corrected to **The Seelbach Hilton Louisville** through the
evidence-cited overlay, the record carries the adjudication, and the membrane now
admits it. Re-reading the same block also recovered the **$100.00 fee** its page
had been stating all along.

### 2. The allowance class — concrete terms are evidence of acceptance

Recorded with the founder's ruling verbatim and their five scoping conditions.
The ruling's practical effect was in the reader, not in a per-row override: a
page that states "Max 2 DOGS only … 40 lbs each for 25.00 USD/pet/night" states
an acceptance of dogs, and the reader now reads it — under all five conditions,
with `species_allowed` never widened beyond what the source names. Super 8
Louisville Expo Center reads completely and is no longer held.

The override file carries `records: []` for the allowance with the reason
written down: applying it per row would have recorded "was withheld as
SOURCE_SILENT", which stopped being true in this same work order. A row that
states terms and no acceptance in any form still returns to the founder.

---

## What was applied

### 9 canonical-name corrections — *evidence-cited overlay, census unedited*

`candlewood suites` · `days inn` · `hampton` · `holiday inn` · `quality suites` ·
`residence inn` · `towneplace suites` · `tru` · `the seelbach hilton hotel`

### 11 reader repairs — *each verified against a persisted Louisville block*

| # | What was wrong | Where it showed |
|---|---|---|
| 1 | A **fee and a deposit sharing an amount** were one charge: the labelled pass skipped any amount already explained | Holiday Inn East/Hurstbourne and Holiday Inn Downtown each dropped a $40 / $75 damage deposit |
| 2 | A **weight limit with no connector** ("Weight limit 50 lbs") matched nothing | 50 lb limit published as "Not stated" |
| 3 | A **word-number with a species** ("limit of two dogs") | count dropped |
| 4 | A **count stated as an allowance** ("One pet is allowed per room", "2 pets allowed") | counts of 1 and 2 dropped |
| 5 | A **compressed cell** ("2petsMax") needed whitespace | count dropped |
| 6 | A label with **two qualifier words** ("$100.00 non-refundable pet fee") | the Seelbach's whole price |
| 7 | **Money about a pet that no pattern binds** was reported as SOURCE_SILENT | Staybridge Expo: "1 to 6 nights: 75 USD" |
| 8 | One charge **stated on two bases** had its basis chosen silently | Holiday Inn Downtown: $75 per stay *and* per night |
| 9 | A **weight no pet has** was published faithfully | Residence Inn Airport: 900.0 lbs |
| 10 | A **species acceptance** was not an acceptance, so a "no other pets" clause made the page look self-contradictory | Days Inn Sellersburg: species, count, weight and price all withheld |
| 11 | **"No dogs allowed" contained "dogs allowed"** and was read as an affirmation | a page refusing dogs listed dog as an accepted species |

Two of those — the 900 lb weight and the two-basis fee — are repairs that publish
**less**: the value is withheld, the quote is kept, and the reason is recorded.
Three more now say why a weight is absent (`FLAG_WEIGHT_NOT_USABLE`,
`FLAG_WEIGHT_IMPLAUSIBLE`) instead of being silently missing.

### 1 contract amendment — `ptf-policy-observation` 1.2.0 → **1.3.0**

`FLAG_TIER_STRUCTURE_REFUSED` was the row that was held, and it was not alone:
**seven** flag codes the readers emit were absent from the closed vocabulary, so
the membrane refused whole observations over the *name* of a note attached to
them. Reconciled by listing every code the readers emit — not by adding the one
that happened to be found. Additive: 1.0.0, 1.1.0 and 1.2.0 records all still
validate.

---

## Rows still requiring founder judgment: 1

**`candlewood suites louisville south fair and expo`** — the membrane refuses it
(M10). The page identifies *Candlewood Suites Louisville - Fair/Expo Center*; the
census says *Candlewood Suites Louisville South Fair and Expo*. The street agrees
exactly (6540 Paramount Park Dr, 40213) and it is the **only** signal available —
the census row carries no telephone, so one of three signals could corroborate at
all.

*Next action:* a person decides whether they are one building. If yes, a
canonical-name correction and an offline re-derive, exactly as the Seelbach took.
**Offline and free either way; no re-fetch, no spend.**

---

## Duplicate scan (re-run at 005)

5 groups, 1 touching a candidate:

| Signal | Identities | Reading |
|---|---|---|
| STREET | hampton inn louisville east hurstbourne + home2 suites by hilton louisville east hurstbourne | **Not duplicates** — the pages state Building B and Building A with different Hilton codes |
| STREET | la quinta … northeast old henry + la quinta inn and suites louisville east | Likely one building, two keys. Neither is a candidate |
| STREET | rivue tower + the galt house hotel … | One business, two tower names. Neither is a candidate |
| STREET | comfort inn + quality inn louisville southwest | A rebrand. Neither is a candidate |
| URL | 7 Choice identities on one OpenStreetMap tag | The stale census URL 003 already refused |

The seven-identity URL group no longer touches a candidate: Comfort Suites East
was acquired from its own property page.

---

## Reconciliation

```
census                 = 166   (file unchanged: 166 rows, 96 URLs)
packet rows            = 63
reviewed rows          = 63
distinct identity keys = 63
dispositions sum       = 63    (45 + 17 + 0 + 1)
closure                = 166 / 166   (0 missing, 0 duplicate, 0 foreign)
observations           = 63, all PUBLICATION_GRADE_CONFIRMED
membrane               = 62 VALID, 1 REJECT_WRONG_PROPERTY
withheld fields        = fee_basis 8, pet_fee 7, weight_limit 3 -- every one with a reason
founder_decision       = empty on all 63
founder_reviewer_id    = empty on all 63
founder_reviewed_at    = empty on all 63
identity adjudications = 1 (the Seelbach, by the founder)
canonical names shown  = 9 corrected, census file untouched
provider calls         = 0
spend                  = $0.00
```

---

## Declarations

```
APPROVE_PET_FRIENDLY     = 45
APPROVE_VERIFIED_NO_PETS = 17
APPROVE_WITH_CHANGE      = 0
HOLD                     = 1
CLEAN SIGNABLE TOTAL     = 62

ROWS REQUIRING FOUNDER JUDGMENT = 1 (candlewood suites louisville south fair and expo)

LOUISVILLE REGISTERED = FALSE
LOUISVILLE PUBLISHED  = FALSE
LOUISVILLE DEPLOYED   = FALSE
FOUNDER SIGNATURE     = NOT WRITTEN
```
