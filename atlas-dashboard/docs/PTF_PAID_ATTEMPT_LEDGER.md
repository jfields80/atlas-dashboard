# PTF-GENERIC-CROSS-RUN-PAID-ATTEMPT-LEDGER-001 — pay once per page, ever

## Why this exists

Three guards already stand between the factory and a wasted dollar, and each is
correct inside its own frame:

| guard | rule | scope |
|---|---|---|
| `acquisition/retry_policy` | a prior FAILURE may not be re-bought on the lane that already failed | one market, one prior report, **matched by identity key** |
| `market_paid_acquisition.derive_cohort` | a prior ANSWER settles the property | one market, one prior report, **matched by identity key** |
| `discovery/identity_dedup` | two rows of ONE proposed census naming one page collapse before the money | one census, one run |

Every one of them is keyed on the identity key, inside a single pass, against a
single named prior document. That is exactly the frame in which the money
leaks, because **the identity key is not the property**:

- a **re-census renames** — Indianapolis went 153 → 265, Pittsburgh rebuilt 30
  cells — and a renamed hotel has no history to any guard above;
- a **brand rename** does the same with no re-census at all;
- a **later work order** passes a different `--prior`, so what pass 1 bought is
  invisible to pass 3;
- **twin rows** held at `DUPLICATE_REVIEW_REQUIRED` stay distinct on purpose,
  and then both get bought.

None of those guards has a durable memory of *what we have ever paid to fetch*.
`acquisition/paid_attempt_ledger` is that memory.

## The core invariant

> Same property + same page + same lane + materially unchanged acquisition
> state: **NEVER PAY AGAIN.**

A repeat purchase is permitted only when one of five things is affirmatively
true, and the decision record names which:

| decision | when |
|---|---|
| `ALLOWED_ESCALATION` | the prior outcome is a CHANNEL failure and a permitted lane has never been paid for this page |
| `ALLOWED_URL_CHANGED` | the page this row would fetch is not the page that was fetched |
| `ALLOWED_CAPABILITY_CHANGED` | a provider or reader capability post-dates the prior attempt |
| `ALLOWED_ROUTING_REPAIRED` | a documented repair changed *which property* this row fetches |
| `ALLOWED_OPERATOR_OVERRIDE` | a named human, with a durable reason |

An asserted material change with **no reason** raises `PaidLedgerError` rather
than being believed. An override nobody has to justify is not a control.

## The match hierarchy

Walked strongest-first, stopping at the first key that matches:

1. **`CANONICAL_URL`** — decides alone. Same page.
2. **`PROPERTY_CODE`** — decides alone. The brand's own key for the building;
   survives a URL move and a rename.
3. **`PROPERTY_IDENTITY`** — brand + normalised street + postcode. **Needs
   confirmation.**
4. **`PREMISES_EVIDENCE`** — normalised street + postcode. **Needs
   confirmation.**

Keys 3 and 4 *propose* and never *decide*. Each must be confirmed by a
compatible name (`identity_dedup.names_compatible`), and each is **refuted
outright by two disagreeing brand property codes**. A key that fails to get its
confirmation does not stop the walk — it falls through.

### A shared switchboard is not a shared hotel

A shared telephone used to confirm keys 3 and 4 on its own.
`PTF-GRAND-RAPIDS-CROSS-RUN-LEDGER-SYNC-018` removed that, because Grand Rapids
carries two open identity questions and both are exactly that shape: a Comfort
Inn and a prior-census Comfort Suites at 4520 Kenowa Ave SW sharing
616-667-0733, and a Sleep Inn and Suites and a Spark by Hilton at 4284 29th St
SE sharing 616-975-9000. The pre-acquisition dedup gate saw the same two
signals and ruled both pairs `DISTINCT_PROPERTIES`; phone-alone confirmation
made this ledger rule the opposite way on the same evidence, and its ruling is
the one that leaves a hotel with no policy for ever.

The two cases a shared switchboard covers are a dual-brand building and a
rebrand, and in both the answer is a person, not a purchase. Where a rename
merely lengthened the name, `names_compatible` already confirms it. The
telephone stays on the record as a signal and stops being a decider.
compatible name (`identity_dedup.names_compatible`) or a shared telephone, and
each is **refuted outright by two disagreeing brand property codes**. A key
that fails to get its confirmation does not stop the walk — it falls through.

### Why keys 3 and 4 may not decide

A Hampton Inn and a Homewood Suites share one address, one switchboard **and
one brand**. Brand-plus-address alone would have collapsed them into a single
purchase and left one of the two hotels with no policy for ever. Different
first-party property pages, or different property codes, are affirmative
evidence of two properties on the brand's own authority.

**Losing a hotel is worse than paying for it twice.** Over-suppression costs
coverage; over-purchase costs cents.

## Terminal and reusable history

| outcome | terminal | evidence reusable | what changes it |
|---|---|---|---|
| `VALID` | yes | yes | nothing — we own the answer |
| `POLICY_NOT_FOUND` | yes | yes | nothing — the page rendered and said nothing, which is a finding |
| `IDENTITY_MISMATCH` | yes | **no** | a **routing repair**, never another purchase of the same wrong page |
| `ACCESS_DENIED`, `BLANK_PAGE`, `UNHYDRATED`, `NAVIGATION_FAILED`, `CAPTURE_FAILED`, `UNEXPECTED_PAGE` | no | no | one escalation to an untried permitted lane |

## Escalation lineage

    attempt 1 (firecrawl, ACCESS_DENIED)
      → reason: a channel failure, and brightdata_browser has never been paid
        for this page
      → attempt 2 (brightdata_browser)

One escalation is a decision to spend once more, **not a licence to walk the
whole ladder**. `attempt 1 → 2 → 3 → 4` on one justification is refused with
`SUPPRESSED_ESCALATION_EXHAUSTED`. Once an escalation produces a terminal
result, the page is closed to further automatic paid acquisition.

## Factory integration

`cohort_cost_plan.build(..., paid_ledger=...)` consults the history **before
anything is budgeted** — a budget computed over a cohort still holding
already-bought pages sizes the cap, the lane mix and the predicted completion
around purchases that must not happen. Each suppression reports:

`current identity · matched historical attempt · match key used · prior lane ·
prior outcome · prior artifact (+ hash) · suppression reason ·
reusable_evidence · routing_repair_required`

Absent ledger means no filtering: the guard is **additive**, and a market with
no recorded history buys exactly what it bought before.

### Suppressed ≠ missing

`suppress()` **partitions** the cohort it is given: every row lands in exactly
one list and neither list invents a row. The plan carries a
`cohort_accounted_for` block proving `payable + suppressed == submitted`. A
property we already have the answer for is **covered**, not missing, and
closure still counts it.

The pre-acquisition dedup gate runs earlier and its merged twins never reach
the ledger at all, so **no identity is removed twice**.

## The historical audit

`acquisition/paid_attempt_audit` reads saved artifacts offline — no network, no
provider, no re-acquisition — and never modifies a historical artifact.

An **entity** is a page: the property code where one exists, else the canonical
URL. Repeats are classified as `JUSTIFIED_ESCALATION` (not waste),
`SAME_LANE_REPEAT`, `REPEAT_AFTER_TERMINAL`, or `UNJUSTIFIED_REPEAT`.

Findings across six markets (663 attempts, 556 unique pages) are committed as
`launch_packages/pettripfinder/ptf_paid_attempt_audit_001.json`. Two distinct
leak modes were found:

- **Louisville** — 8 pages bought 4× each: `louisville-rebuild-002` walked the
  lane ladder, then `louisville-expansion-003` walked the *same* ladder again.
  Same identity key, cross-run. This is the leak `retry_policy` was built for.
- **Pittsburgh / Indianapolis / St. Louis** — 6 / 3 / 1 pages bought under **two
  identity keys**. `PROPERTY_CODE:INDNEHX` is the sharpest case: bought `VALID`
  in Indianapolis pass 1, then bought again in pass 2 under a renamed identity
  key. **No existing guard could see that**, which is why this module exists.

Grand Rapids-Holland, which ran *with* the pre-acquisition dedup gate, shows
zero unjustified repeats.

### On the money

The vendor meters a **zone over a session**, not a property, so no per-property
price was ever recorded. Every dollar figure is the run total apportioned
evenly over that run's attempts, and is labelled `estimated`. It is the right
order of magnitude and the wrong number to invoice anybody for.
