# PTF-ST-LOUIS-FOUNDER-DECISIONS-006 — Human Decision Resolution, FINAL

**Market:** `st-louis-mo` **Branch:** `feature/ptf-st-louis-market-001`
**Start HEAD:** `766ea4f`
**Offline only — zero provider calls, zero spend, zero re-fetches.**
**NOT REGISTERED. NOT PUBLISHED. NOT DEPLOYED.**

---

## A. The work order was truncated

It ends mid-sentence at *"approve the identity despite"*. I completed the
substantive work, because the founder rule is stated fully enough to apply and
the completion of that clause is unambiguous. **What I did not do is extend the
signature**, because the instruction covering it is in the missing text. See §G.

## B. Result — 7 of 8 resolved

| | 005 | **006** |
|---|---|---|
| APPROVE_PET_FRIENDLY | 76 | **82** |
| APPROVE_VERIFIED_NO_PETS | 38 | **38** |
| APPROVE_WITH_CHANGE | 1 | **1** |
| HOLD | 7 | **1** |
| **Clean and signable** | 114 | **120** |

**6 rows became newly clean**, all pet-friendly: Comfort Inn Collinsville,
Super 8 Troy, Sonesta ES Chesterfield, Comfort Inn Pacific, Travelodge St. Louis
Airport, Hampton.

## C. The allowance ruling — 3 rows, all five conditions checked

Applied to the three named rows only. Each was verified against every condition
you scoped it to before admission:

| Row | Property-specific | Identity valid | Pet terms | No contradiction | Species |
|---|---|---|---|---|---|
| Comfort Inn Collinsville | PROPERTY_PAGE | membrane VALID | *"maximum of 2 dogs per room"* | none | **dogs only** |
| Super 8 Troy | PROPERTY_PAGE | membrane VALID | *"15USD per pet per night"*, 50 lb, max 2 | none | none named |
| Sonesta ES Chesterfield | PROPERTY_PAGE | membrane VALID | *"$75 non refundable pet fee…"* | none | none named |

**The species limit was honoured exactly.** Comfort Inn Collinsville says
*"Dogs Only"* — `species_allowed` stays `["dog"]` and is not widened. The other
two say *"pet"* and name no species, so **no species is asserted at all** and
`species_allowed` is absent. A test pins both directions.

The ruling is recorded per row with its citation, the five conditions, and the
reason the machine would not make it. The cited quote is always the **property's
own text** — never the ruling's words. An evidence quote must stay something a
reader can find on the page; a test asserts the founder's words never enter the
evidence array.

## D. Identity judgements — the evidence, then the rule

| | Comfort Inn Pacific | Days Inn Pontoon Beach | Travelodge Airport | Wingate |
|---|---|---|---|---|
| Census name | Comfort Inn Pacific - St. Louis | Days Inn & Suites Pontoon Beach | Travelodge St. Louis Airport | Wingate At Wyndham |
| Page name | Comfort Inn Near Six Flags St. Louis | Days Inn by Wyndham Pontoon Beach | Travelodge by Wyndham St. Louis | Wingate by Wyndham St. Louis/Fenton Route 66 |
| Census address | 1320 Thornton St, Pacific MO 63069 | 5105 Highway 111, Pontoon Beach IL 62040 | 9645 Natural Bridge Rd, 63134 | 1100 South Highway Drive, Fenton MO 63026 |
| Page address | 1320 Thornton St. | 5105 Highway 111 | 9645 Natural Bridge Road | 1100 S Hwy Dr |
| **Street** | **EXACT MATCH** | **EXACT MATCH** | **EXACT MATCH** | **same address** ¹ |
| Census phone | 6362574600 | 6182198631 | 3148909000 | 6366001818 |
| Page phone | (636) 257-4600 | 1-618-**797-2727** | +1-314-890-9000 | 636-600-1818 |
| **Telephone** | **EXACT MATCH** | **DIFFERENT** | **EXACT MATCH** | **EXACT MATCH** |
| Property code | absent both sides | absent both sides | absent both sides | absent both sides |
| URL shape | PROPERTY_PAGE | PROPERTY_PAGE | PROPERTY_PAGE | PROPERTY_PAGE |
| Membrane (before) | REJECT_WRONG_PROPERTY / M10 | REJECT_WRONG_PROPERTY / M10 | REJECT_WRONG_PROPERTY / M10 | REJECT_WRONG_PROPERTY / M10 |
| **Signals agreeing** | **2** | **1** | **2** | **2** |
| **Verdict** | **APPROVED** | **REFUSED** | **APPROVED** | **APPROVED** |

¹ **Wingate's street needs stating plainly.** `1100 South Highway Drive` and
`1100 S Hwy Dr` are the same address. The repository's `street_identity` folds
`Highway→hwy` and `Drive→dr` but does **not** fold the directional `South→S`, so
they normalise to two different strings. That is a gap in a spelling table, not
evidence of a different place. I reported it rather than patching it:
`street_identity` is shared by every market, and this work order is a decision,
not a normaliser change. The approval rests on the **telephone plus the street as
a human reads it**, and the census name — a bare chain word — carries no weight.

**Days Inn is refused**, and this is the rule working. One strong signal agrees
and the second *actively disagrees*: two distinct local 618 lines, not a
toll-free reservations number against a property line. Your rule requires two
agreeing signals; it does not permit one agreement plus one contradiction. What
would settle it: a property code, or evidence the line changed in a rebrand from
"Days Inn & Suites" to "Days Inn". Neither is on disk, and neither needs a paid
fetch.

Your ruling matches this repository's own comparator, which already routes
exactly this shape to `NEEDS_ADJUDICATION` and says why: *"a directory may
transcribe a house number inconsistently, but two hotels do not share a line."*

## E. Hampton — authorised name correction

`Hampton` → `Hampton Inn Collinsville`, added to the evidence-cited overlay, not
the census. Repository precedent does require the overlay: the census stays the
record of what discovery **observed**, and a test asserts the census file still
says `Hampton`. The replacement is character-for-character what the captured page
states.

## F. How the overrides are held

Both live in `markets/founder_overrides/st-louis-mo.json`, per row, with
`decided_by: jfields80` and `recorded_by` naming me as transcriber.

The observation contract moved to **1.2.0** — an additive amendment adding two
**optional** fields, `founder_overrides` and `identity_adjudication`.
`ACCEPTED_CONTRACT_VERSIONS` keeps 1.0.0 and 1.1.0 valid.

**The gate is unchanged for every row nobody ruled on.** Tests prove a name
mismatch with no adjudication is still refused, that an adjudication with no
named approver admits nothing, and that an identity ruling does **not** excuse
any other membrane rule — a row with an adjudication and an unquoted field is
still refused by M9.

## G. What I did not do, and why

**I did not sign the 6 newly clean rows or extend authority past 114.** The
instruction covering that is in the truncated text. Your decisions here resolve
the *blockers*; extending the signature is a separate act, and work order 005
required an explicit authorisation sentence before I would write one. All 114
existing signatures still bind — **zero hash drift**, asserted by test.

**I did not add Wingate to the name overlay.** Its identity is now approved,
which surfaces its bare-chain census name as a correction — the same class as
Hampton. You authorised Hampton's name and not Wingate's, so Wingate sits at
APPROVE_WITH_CHANGE awaiting one.

## H. Reconciliation — 357

| | |
|---|---|
| Census identities | 357 |
| Closure rows | 357 |
| Missing / foreign / duplicate | **0 / 0 / 0** |

HELD_REVIEW 122 · ACCESS_UNRESOLVED 153 · INSUFFICIENT_EVIDENCE 66 ·
POLICY_NOT_FOUND 16 — **total 357**.
Within the 122: 114 signed + 6 newly clean unsigned + 2 outstanding.

## I. Status

```
ST. LOUIS CENSUS COMPLETE          = YES  (357)
ST. LOUIS ACTIVE CLOSURE COMPLETE  = YES  (357/357)
ST. LOUIS FOUNDER DECISIONS APPLIED = YES  (7 of 8 resolved; 1 refused by your rule)
ST. LOUIS SIGNED AUTHORITY          = 114  (unchanged this pass)
ST. LOUIS CLEAN AND SIGNABLE        = 120  (114 signed + 6 awaiting signature)
ST. LOUIS OUTSTANDING ROWS          = 2    (1 name authorisation, 1 refused identity)
ST. LOUIS REGISTERED = FALSE
ST. LOUIS PUBLISHED  = FALSE
ST. LOUIS DEPLOYED   = FALSE
```

Global authority build marker `241ce93c…` unchanged; 8 source markets; St. Louis
still not enrolled. Measurement disabled, zero affiliates.
