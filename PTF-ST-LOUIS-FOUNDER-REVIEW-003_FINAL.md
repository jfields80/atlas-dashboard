# PTF-ST-LOUIS-FOUNDER-REVIEW-003 — Candidate Review, FINAL

**Market:** `st-louis-mo` **Branch:** `feature/ptf-st-louis-market-001`
**Start HEAD:** `84b445f` **Reviewer:** Claude (operator)
**REVIEW ONLY. NOT REGISTERED. NOT PUBLISHED. NOT DEPLOYED. NO AUTHORITY CREATED.**

Machine-readable form:
`launch_packages/pettripfinder/st_louis_mo_founder_review_analysis_003.json`.

---

## A. One thing I did not do

The work order says "assign exactly one founder disposition". I reviewed all 122
and assigned exactly one disposition each — but I did **not** write them into
`founder_decision` / `founder_reviewer_id` / `founder_reviewed_at`. Those fields
are an attestation, and the packet's own instructions say to set the reviewer id
to "your own identifier — **never an operator's on their behalf**". That sentence
exists because PTF-POLICY-SCHEMA-MIGRATION-001 Phase F once wrote twenty-six
approvals under a founder's name for rows the founder had never seen.

So this is a review with a proposed disposition per row, attributed to me. The
packet's decision fields are still empty. Applying it is one command and one
human signature.

## B. Result — 122 reviewed, each exactly once

| Disposition | Count |
|---|---|
| APPROVE_PET_FRIENDLY | **68** |
| APPROVE_VERIFIED_NO_PETS | **31** |
| APPROVE_WITH_CHANGE | **5** |
| HOLD | **18** |
| **Total** | **122** |

A test asserts the identity keys are 122 distinct values and that the counts sum
to the packet's own `count`.

I disagree with the machine recommendation on **23 of 122**. The machine
proposed authority for every one of them; the packet is built from
`publication_grade == CONFIRMED`, which is a statement about **evidence
quality** and says nothing about whether the record is about the right hotel.

| Family | PET | NO-PETS | CHANGE | HOLD |
|---|---|---|---|---|
| Marriott | 18 | 13 | 1 | 0 |
| Wyndham | 18 | 5 | 1 | 4 |
| Choice | 11 | 8 | 2 | 2 |
| IHG | 7 | 1 | 0 | 8 |
| Independent | 6 | 1 | 0 | 0 |
| ESA | 4 | 0 | 0 | 1 |
| Hilton | 2 | 3 | 1 | 2 |
| Sonesta | 2 | 0 | 0 | 1 |

## C. The 5 changes required

Every correction **removes** something unsupported or **replaces** a value with
one the page already states. None adds a fact.

### C1. Two service-animal statements that would misstate ADA terms

The most serious finding in the review. In both rows the property's pet terms
have been glued onto the front of the service-animal sentence, so the record
states that **service animals** carry a fee and a weight cap.

| Property | Currently reads | Must read |
|---|---|---|
| Comfort Inn & Suites Saint Louis Lafayette Square | `with a 40.00 USD, per night, Limit of one pet per room, and 20 pounds max Service animals are permitted, without charge.` | `Service animals are permitted, without charge.` |
| Radisson Hotel Fairview Heights St Louis | `Max 50 Pounds Service animals are permitted, without charge.` | `Service animals are permitted, without charge.` |

Removal only. The pet fee, the per-room limit and the weight cap stay on their
own fields, where they are correct. PTF-CHOICE-READER-AND-ROUTE-CLOSURE-005
established the rule: a term *inside* the service-animal statement caps
**service animals**.

### C2. Three canonical names that name a chain, not a building

| Currently | Must read (quoted from the property's own page) |
|---|---|
| Courtyard | Courtyard by Marriott St. Louis Airport/Earth City |
| Days Inn | Days Inn & Suites by Wyndham Caseyville |
| DoubleTree | DoubleTree by Hilton Hotel Collinsville - St. Louis |

Published as they stand, the directory would carry an entry called "Courtyard".
The census admits a bare brand word as a valid identity key — the defect
MARKET-001 recorded — and this is where it surfaces to a reader.

## D. The 18 holds, and what each needs

### D1. Twelve rows the membrane refuses as the WRONG PROPERTY (M10)

`comfort inn pacific st louis` · `days inn and suites pontoon beach` ·
`extended stay america select suites st louis o fallon` · seven
`holiday inn express and suites … by ihg` rows · `travelodge st louis airport` ·
`wingate at wyndham`

**Why they cannot enter authority:** our own membrane says the observation is
about another property. No correction to the facts changes that verdict.

**But the gate is very likely wrong, and the cause is identified.** Eight of the
twelve differ from the page only by an **undecoded HTML entity** — the page says
`Holiday Inn Express &amp; Suites Edwardsville`, the census says `&`. The
remaining four differ by a chain suffix or a rename. On **all twelve**, the
page's street number and telephone independently match the census row.

**Next action:** decode HTML entities and strip chain suffixes in the M10 name
comparison, then re-derive these observations **offline from their persisted
blocks**. No re-fetch, no spend. Re-deriving must re-parse the stored block and
never re-locate the document — PTF-MILWAUKEE-OBSERVATION-REDERIVATION-018.

### D2. Four rows blocked by a contract violation in our own reader

`embassy suites by hilton st louis downtown` · `hampton` ·
`sonesta es suites st louis chesterfield` · `staybridge suites st louis westport`

`policy_reading.py` emits the flag codes `FLAG_STRUCTURED_TIERS` and
`FLAG_STRUCTURED_PET_SCHEDULE`. Neither is in `policy_observation.FLAG_CODES`,
whose docstring says: *"A producer needing a new code is proposing a contract
change, not picking a string."* The membrane correctly rejects them as malformed.

These four carry the market's **most complex pricing** — tiered fees such as
`$75 for stays up to 7 nights, $150 beyond`. The evidence is intact; the
container is not registered.

**Next action:** amend `FLAG_CODES` as a **versioned contract change**, then
re-derive offline. I have deliberately not made that edit inside a review work
order: an immutable contract is amended by version bump, never as a side effect.

(`hampton` also needs the C2 name correction. The hold dominates.)

### D3. Two rows where the allowance itself is never stated

`comfort inn collinsville near st louis` · `super 8 by wyndham troy il st louis area`

Both sources state pet terms — *"maximum of 2 dogs per room"*, *"15USD per pet
per night"* — and neither ever says pets are accepted. `pets_allowed` is
withheld as `SOURCE_SILENT`, and readiness is `POLICY_PARTIAL`, which
`PUBLISHABLE_STATES` excludes.

**Next action — one founder policy decision, not two row decisions:** does a
stated per-pet price constitute a stated allowance? If yes, both rows approve
from their existing quotes with no re-fetch. The machine will not make that
inference; a person may, once, as policy.

## E. What I validated on every row

Identity binding (name after entity-decoding and suffix-stripping, street
number, telephone — **zero agreeing signals is blocking**) · source is
property-specific · publication grade · membrane verdict · readiness state ·
`pets_allowed` present or explicitly withheld · species · pet count and its
scope · weight limit and its operator/scope · fee amount, currency, basis,
scope and cap · fee tiers vs flat fee · deposits vs fees · multi-pet rules ·
service-animal statement integrity · withheld-field register · contradictions.

Three classes I checked and found **clean**:

- **All 122 source URLs are property-specific** (`PROPERTY_PAGE`).
- **No no-pets row carries a pet fee, weight or count.** Zero contradictions.
- **Four rows carry both a deposit and a fee** — each cited to its own quote
  (`"$50 refundable deposit"` vs `"$15 per pet per night"`). Distinct charges,
  correctly separated.

The 48 weight limits without an operator, 44 pet counts without a scope and 8
fees without a basis are **not defects**: they are the codebase's non-inference
discipline, each recorded in `withheld_fields` or `non_inferences` and each
rendering as "Not stated".

## F. The rows you flagged

**Non-falsifiable POLICY_NOT_FOUND: 2 of 16 — and one is not Firecrawl.**
`comfort suites` (Firecrawl) and `doubletree by hilton st louis forest park`
(**Web Unlocker**). 14 of the 16 do have their document on disk. So the
persistence gap is wider than recorded: `unlocker_capture.py` has no declined-
capture persistence either, which the Firecrawl fix did not cover.

**Neither row is a candidate**, so neither affects this review. Both remain
closure rows whose silence cannot be checked.

**Observations produced before later corrections:** all 122 come from the 002
observation store, rebuilt after the routing and parser corrections. None
predates them.

## G. Proposed authority totals, subject to founder approval

| | |
|---|---|
| Pet-friendly authority | 68 + 4 with change = **72** |
| Verified-no-pets authority | 31 + 1 with change = **32** |
| **Total proposed authority** | **104 of 357 active (29.1%)** |
| Held | 18 |

Currently `AUTHORITY_PET_FRIENDLY` and `AUTHORITY_VERIFIED_NO_PETS` are both
**0**, and remain so. This review creates none.

## H. Status

```
ST. LOUIS CENSUS COMPLETE          = YES  (357)
ST. LOUIS ACTIVE CLOSURE COMPLETE  = YES  (357/357)
ST. LOUIS CANDIDATES REVIEWED      = YES  (122 of 122, each exactly once)
ST. LOUIS AUTHORITY CREATED        = NO   (0; review only)
ST. LOUIS REGISTERED               = FALSE
ST. LOUIS PUBLISHED                = FALSE
ST. LOUIS DEPLOYED                 = FALSE
```

## I. Is St. Louis READY FOR AUTHORITY PUBLICATION?

**Not yet — and two of the three blockers are ours, not the market's.**

1. **The 5 changes must be applied first.** Two of them would publish an
   ADA-adjacent misstatement about service animals. That is a hard blocker.
2. **The M10 entity-decoding fix** would move up to 12 rows out of hold at zero
   cost, most of IHG among them.
3. **The FLAG_CODES amendment** would move 4 more, including the tiered-fee
   rows.
4. **One founder policy question** on price-implies-allowance settles 2.

With all four done and the founder's signature, **up to 122 rows** could carry
authority. Without any of them, 99 rows are approvable today (68 + 31) and would
publish correctly.

**Recommended order:** apply the 5 changes → fix M10 entity decoding → amend
FLAG_CODES → founder sitting over the full set. Steps 2 and 3 are offline and
free; nothing here needs another provider call.
