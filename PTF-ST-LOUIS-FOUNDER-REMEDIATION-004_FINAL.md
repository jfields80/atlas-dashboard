# PTF-ST-LOUIS-FOUNDER-REMEDIATION-004 — Offline Remediation, FINAL

**Market:** `st-louis-mo` **Branch:** `feature/ptf-st-louis-market-001`
**Start HEAD:** `7f421bb`
**OFFLINE ONLY — zero provider calls, zero spend, zero re-fetches.**
**NOT REGISTERED. NOT PUBLISHED. NOT DEPLOYED. NO FOUNDER ATTESTATION WRITTEN.**

---

## A. Result

| Disposition | 003 | **004** | Change |
|---|---|---|---|
| APPROVE_PET_FRIENDLY | 68 | **76** | +8 |
| APPROVE_VERIFIED_NO_PETS | 31 | **38** | +7 |
| APPROVE_WITH_CHANGE | 5 | **1** | −4 |
| HOLD | 18 | **7** | −11 |
| **Total** | 122 | **122** | each reviewed exactly once |

**Proposed authority after remediation: 115 of 357 active (32.2%)** — 77
pet-friendly, 38 verified-no-pets. Up from 104. Still zero authority created.

| Family | PET | NO-PETS | CHANGE | HOLD |
|---|---|---|---|---|
| Marriott | 19 | 13 | 0 | 0 |
| Wyndham | 19 | 5 | 0 | 4 |
| Choice | 13 | 8 | 0 | 2 |
| IHG | 9 | 7 | 0 | 0 |
| Independent | 6 | 1 | 0 | 0 |
| ESA | 5 | 0 | 0 | 0 |
| Hilton | 3 | 4 | 1 | 0 |
| Sonesta | 2 | 0 | 0 | 1 |

## B. Step 1 — the five corrections, applied at their root

Not one of the five was applied as a hand-edit to a record. Each was fixed where
it was produced, and the artifacts were re-derived offline.

**The two service-animal statements** were fixed in `policy_reading.py`.
`_service_animal_span` already refused to read a limit stated *before* the phrase
as a limit on service animals, and said why. That reasoning governed which
limits were *attributed* and never the quote that was *published*, so the two
disagreed. `_service_animal_quote` now trims a prefix back to the phrase — and
only when that prefix carries a price, a weight or a count, so
`"Only service animals are permitted"` keeps its `"Only"`.

Both St. Louis records now read exactly `Service animals are permitted, without
charge.` The pet fee, the per-room limit and the weight cap remain on their own
fields, unchanged.

**The three canonical names** went into an evidence-cited overlay,
`markets/name_corrections/st-louis-mo.json`, not into the census. The census
stays the record of what discovery *observed*; a name read off the property's
page is a derivation, and the two must stay distinguishable. A test asserts the
census file still says `Courtyard`, `Days Inn` and `DoubleTree`, and that every
replacement is character-for-character what the captured page states.

One correction of mine needed correcting: I first wrote plausible-looking
`source_url` values into that overlay with guessed property codes (`stlap`,
`stlcldt`). The real captures say `stlbr` and `stlcndt`. Replaced with the
captured URLs.

## C. Step 2 — the M10 identity defect

Three separate faults, each fixed:

1. **HTML entities were never decoded.** `_tokens` split `&amp;` into a stray
   `amp` token present on one side only. Purely corrective.
2. **`hotel_ref.street_identity` was never populated.** The contract calls
   hotel_ref "a reference … guarded by street_identity", and this market's
   builder left the guard empty — so *both* of M10's escapes were unreachable
   for every market on this path. It now comes from the census.
3. **`street_identity` carries a postal suffix a hotel page rarely prints**, so
   `"1320 thornton st|63069"` never equalled `"1320 thornton st|"`. The halves
   are now compared separately: the street must agree; the postal code is
   checked only when both sides carry one.

A second conjunctive escape was added — **street agreement AND names agreeing
once owner qualifiers are stripped** — because only Marriott and Hilton put a
property code on the page, and the first escape needs one.

### The safety work is the point

**My first version of that escape was wrong, and an existing test caught it.**
`test_m10_code_and_address_override` encodes PTF-COLUMBUS-IDENTITY-CLEANUP-001:
Columbus has three Embassy Suites, and the Corporate Exchange page calls itself
`"Embassy Suites by Hilton Columbus"` — a name the *Airport* sibling answers to
just as well. My symmetric subset test let that sibling through as VALID.

The escape now requires **the page to name at least what the record names**
(`known ⊆ page`, one direction only). A page that names *less* cannot tell the
record's hotel from a sibling sharing the shorter name, so the street would be
doing all the work — and the street alone was never enough. It also fails closed
when both sides carry a property code and the codes **disagree**: a disagreeing
code is a disagreement, not the silence an absent code represents.

That correctness costs three St. Louis rows whose pages drop a real token
(`& Suites`, `Airport`). They go back to a human, which is the right side to be
wrong on.

Bare-brand names are refused outright by `_has_distinguishing_token`: every
Hampton Inn in a market is a superset of `{hampton}`.

**8 of the 12 moved out of HOLD:**
`extended stay america select suites st louis o fallon` and the seven
`holiday inn express and suites … by ihg` rows.

## D. Step 3 — the FLAG_CODES amendment, versioned

`policy_observation` now stands at **1.1.0**, registering `FLAG_STRUCTURED_TIERS`
and `FLAG_STRUCTURED_PET_SCHEDULE` — codes `policy_reading` had been emitting
unregistered since PTF-READER-TO-TIERS-034.

`ACCEPTED_CONTRACT_VERSIONS = ("1.0.0", "1.1.0")`. An amendment that only *adds*
to a closed vocabulary cannot invalidate a record written before it, and four
markets' committed stores carry 1.0.0. Bumping the emission version without
widening acceptance is how a "versioned" change quietly becomes a breaking one.

The vocabulary is still closed — a test asserts an unregistered code is still
refused.

**3 of the 4 moved out of HOLD:** `embassy suites by hilton st louis downtown`,
`staybridge suites st louis westport by ihg`, and `hampton` (to
APPROVE_WITH_CHANGE). The fourth, `sonesta es suites st louis chesterfield`,
moved from a malformed-observation hold to the founder-policy class below.

## E. Step 4 — the founder policy question, asked and not answered

`st_louis_mo_founder_policy_question_004.json`, status
`AWAITING_FOUNDER_DECISION`, decision fields empty.

> Does an official property page that states explicit pet terms — *"maximum of 2
> dogs per room"*, *"15USD per pet per night"*, *"$75 non refundable pet fee for
> stays of up to 7 nights"* — but never literally states that pets are allowed,
> count as sufficient evidence that pets are accepted?

**It is three rows, not two.** The FLAG_CODES amendment admitted Sonesta ES
Suites Chesterfield, and the allowance question is what it turns out to be
waiting on underneath. The others are Comfort Inn Collinsville and Super 8 Troy.

The artifact states the risk on **both** sides — publishing an allowance on the
strength of a price, versus leaving three plainly pet-friendly properties
invisible — and scopes a YES to these three rows only.

## F. The 7 remaining holds

| Row | Why | Next action |
|---|---|---|
| comfort inn collinsville near st louis | allowance never stated | founder policy question (E) |
| super 8 by wyndham troy il st louis area | allowance never stated | founder policy question (E) |
| sonesta es suites st louis chesterfield | allowance never stated | founder policy question (E) |
| comfort inn pacific st louis | page says *"Comfort Inn Near Six Flags"* — a rename, not an encoding artifact | a person decides whether they are one building; street and telephone both agree |
| days inn and suites pontoon beach | page names less than the record (`& Suites` absent) | same; sibling risk is why the machine will not decide it |
| travelodge st louis airport | page names less than the record (`Airport` absent) | same |
| wingate at wyndham | census name is a bare chain word | give the census row the name its own page states, then re-derive offline |

**One new APPROVE_WITH_CHANGE surfaced:** `hampton` → `Hampton Inn
Collinsville`. It was invisible in 003 because the row was held as malformed. It
is **not** one of the five authorised corrections, so I did not apply it — it
needs the founder's authorisation like the first five did.

## G. Tests

**44 new tests**, every fix paired with the case it must still refuse.
`tests/pettripfinder/test_founder_remediation_004.py`.

Two committed expectations were re-baselined, each with the reason recorded in
the artifact itself:

- `reader_hardening_016` baseline and its committed differential, case
  `control--service-animal-after-weight`. The pinned value was the contaminated
  published quote. **`weight_limit` stays 65 lb** and every other field on the
  case is unchanged — 016 fixed the attribution, 004 fixes the sentence.
- `test_existing_contract_vocabularies_are_untouched` now pins 1.1.0 *and*
  asserts 1.0.0 is still accepted. Its purpose — that importing a package must
  never mutate a vocabulary — is intact.

**Full regression:** 135 failures in `tests/pettripfinder/acquisition/` against a
measured baseline of **134**. The single delta is
`test_publication_042::test_nothing_outside_the_publication_surface_changed`,
which shells out to `git status --porcelain` and fails on *any* uncommitted
change to `policy_reading.py`. It is a working-tree guard scoped to the 042
commit, and it clears once this work is committed — confirmed below.

The baseline was measured, not assumed: the tree was stashed under a unique tag,
the suite re-run at `7f421bb`, and the work restored by SHA.

## H. Status

```
ST. LOUIS CENSUS COMPLETE              = YES  (357, file unedited)
ST. LOUIS ACTIVE CLOSURE COMPLETE      = YES  (357/357, reconciled by set)
ST. LOUIS FOUNDER REVIEW COMPLETE      = YES  (122, each exactly once)
ST. LOUIS OFFLINE REMEDIATION COMPLETE = YES
ST. LOUIS READY FOR FINAL FOUNDER SIGNATURE = YES, for 114 of 122 rows
ST. LOUIS REGISTERED                   = FALSE
ST. LOUIS PUBLISHED                    = FALSE
ST. LOUIS DEPLOYED                     = FALSE
```

## I. Ready for final founder signature?

**Yes for 114 of 122** — 76 pet-friendly and 38 verified-no-pets, every one
carrying a corroborated identity, a property-specific source, a
publication-grade capture and a VALID membrane verdict. Nothing further can be
done for them offline; they are waiting on a signature and nothing else.

**Eight need a person first**, and none needs money:

1. **One name correction** (`hampton`) — the same class as the five already
   authorised, newly visible.
2. **One policy question** covering three rows (E).
3. **Four identity judgements** — one rename, two pages that name less than the
   record, one bare-brand census name.

Every blocker that could be resolved from persisted evidence has been.
