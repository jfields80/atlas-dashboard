# PTF-LOUISVILLE-FOUNDER-REVIEW-004 — FINAL

**Market:** louisville-ky · **Census:** 166 · **Candidates:** 63 · **Reviewed:** 63
**Founder decisions written:** 0 · **Registered / Published / Deployed:** FALSE / FALSE / FALSE
**Spend:** $0.00 · **Provider calls:** 0 · **Pages re-fetched:** 0

Every candidate was reviewed against its own persisted evidence — the policy
block the record was read from, on disk — not against the machine's disposition.

---

## Result

| Disposition | Machine (003) | **This review (004)** |
|---|---|---|
| APPROVE_PET_FRIENDLY | 37 | **30** |
| APPROVE_VERIFIED_NO_PETS | 16 | **14** |
| APPROVE_WITH_CHANGE | 5 | **15** |
| HOLD | 5 | **4** |
| **Total** | 63 | **63** |

**19 of 63 rows disagree with the machine.** Ten rows the machine proposed for
approval carry a defect a guest would see; two rows it held are answerable from
evidence already on disk.

Proposed authority if every change is applied: **59** — **42** pet-friendly,
**17** verified-no-pets. Four rows stay out.

---

## The 15 APPROVE_WITH_CHANGE rows

Every correction below quotes evidence already on disk. None adds a fact the
source does not state.

### Names that name no building (8) — *evidence-cited overlay*

| Identity | Current | Corrected to |
|---|---|---|
| candlewood suites | Candlewood Suites | Candlewood Suites Louisville - NE Downtown Area |
| days inn | Days Inn | Days Inn & Suites by Wyndham Louisville SW |
| hampton | Hampton | Hampton Inn New Albany Louisville West |
| holiday inn | Holiday Inn | Holiday Inn Louisville Downtown |
| quality suites | Quality Suites | Quality Suites Jeffersonville - Louisville North |
| residence inn | Residence Inn | Residence Inn by Marriott Louisville East |
| towneplace suites | TownePlace Suites | TownePlace Suites by Marriott Louisville Downtown |
| tru | Tru | Tru By Hilton Louisville East |

The machine caught five of these. **Quality Suites, TownePlace Suites and Tru it
did not** — its bare-name rule was a hand-maintained list of chain words, and a
list only contains the chains someone was already bitten by.

The Holiday Inn correction is also different from the machine's. It proposed
`Louisville Hotels | Holiday Inn Louisville Downtown` — a page **title**, not a
name.

### Facts the source states and the record dropped (5) — *parser logic*

| Identity | Field | Source states |
|---|---|---|
| candlewood suites | weight_limit, pet_count_limit | "Pet weight limit: 80 · 2 pets allowed" |
| hampton inn and suites louisville east | weight_limit | "$75(1-4n),$125(5+n) 2pets Max total 75lb" |
| holiday inn louisville east hurstbourne | weight_limit, pet_count_limit, pet_deposit | "Weight limit 50 lbs, limit of two dogs in room" · "Pet damage deposit: 40 USD" |
| residence inn louisville east oxmoor | pet_count_limit | "One pet is allowed per room" |
| days inn and suites by wyndham sellersburg | pets_allowed, weight_limit | "A maximum of 2 dogs up to 15 lbs each **are allowed** … Sorry no other pets are allowed" |

The last row was a machine HOLD for an "unstated allowance". The source states
the allowance in words; the second sentence restricts the **species**, it does
not withdraw the first. This is the mirror image of the trap this corpus already
knows — "no *other* pets are allowed" read as an acceptance — and it has to be
read correctly in both directions.

### Values and text that must not be published as they stand (2)

| Identity | Field | Correction | Site |
|---|---|---|---|
| residence inn by marriott louisville airport | weight_limit | withhold `{"value": 900.0, "unit": "lb"}` | parser logic |
| comfort suites east | service_animal_exception | remove | parser logic |

Marriott's own page states "Each pet may weigh up to **900.0 lbs**". The reader
quoted it faithfully; the defect is in the source, and a directory printing a
900 lb pet limit is not reporting a policy. The quote stays as evidence.

Comfort Suites East's service-animal statement was this sentence: *"Incidental
charges may include … additional cleaning required due to the actions of a
guest, service animal."* It is a damage-charge paragraph that happens to contain
the words, and it would have been published under an accessibility heading.

### One source that contradicts itself (1) — *evidence-cited overlay*

| Identity | Field | Correction |
|---|---|---|
| holiday inn | fee_basis | withhold `per_night`; the same block states the same $75 charge **per stay** and **per night** |

Also on this row: a stated `Pet damage deposit: 75 USD` the record dropped.

### One price the record said was not stated (1) — *parser logic*

| Identity | Correction |
|---|---|
| staybridge suites louisville expo center | `pet_fee` is withheld as SOURCE_SILENT while the block reads "Our Pet Policy: 1 to 6 nights: 75 USD" |

`SOURCE_SILENT` is a claim **about the source**, and this one is false.

---

## The 4 HOLD rows

| Identity | Why held | Next action | Kind |
|---|---|---|---|
| the seelbach hilton hotel | Membrane M10: the page says "The Seelbach Hilton Louisville", the census says "The Seelbach Hilton Hotel". Street, telephone **and** Hilton property code `sdfshhf` all agree. Its $100 fee is also stated and unread. | A founder confirms the two names are one building; then an evidence-cited name correction and an offline re-derive that also captures the fee. | **needs founder judgment**, then offline/free |
| candlewood suites louisville south fair and expo | Membrane M10: page "Candlewood Suites Louisville - Fair/Expo Center" vs census "…South Fair and Expo". Only one signal corroborates — the street (6540 Paramount Park Dr) — because the census row carries no telephone. | A founder confirms one building; then a name correction and offline re-derive. | **needs founder judgment**, then offline/free |
| hilton garden inn jeffersonville | Membrane refuses the observation as malformed: flag code `FLAG_TIER_STRUCTURE_REFUSED` is not in the closed `FLAG_CODES` vocabulary. The pricing evidence ($75 · $75 1-4n / $125 5+n · 2 pets · dogs and cats) is intact. | Amend `policy/policy_observation.py`'s `FLAG_CODES` as a versioned contract change, then re-derive. | **offline/free** |
| super 8 by wyndham louisville expo center | The block prices and limits a pet — "Max 2 DOGS only max weight of 40 lbs each for 25.00 USD/pet/night" — and never states that pets are accepted. | One founder policy decision covering the class: does a stated per-pet price constitute a stated allowance? If yes, this row approves from its existing quote. | **needs founder judgment** |

No hold needs a different acquisition lane, an attended capture, or a single
cent of provider spend.

---

## Special attention, answered

**1. The 8 attempted-but-unsettled rows.** None of them is a candidate — checked
by name. No row in this packet rests on an access-failure capture.

**2. Prior Louisville-001 identities.** No prior authority was carried forward.
The only 001 material used anywhere is the URLs recovered in 003, and each bound
to a 166-row census identity on telephone, name+postal or street+postal.

**3. Same-address and duplicate identities.** Six groups, written to
`louisville_ky_identity_duplicate_scan_004.json`:

| Signal | Identities | Reading |
|---|---|---|
| STREET | hampton inn louisville east hurstbourne + home2 suites by hilton louisville east hurstbourne @ 1150 Forest Bridge Rd | **Not duplicates.** The pages state "Building B" and "Building A" and different Hilton property codes. Two hotels, one address. |
| STREET | la quinta … northeast old henry + la quinta inn and suites louisville east @ 13825 Terra View Trl | **Likely one building under two identity keys.** Neither is a candidate. |
| STREET | rivue tower + the galt house hotel trademark collection by wyndham @ 140 N 4th St | One business, two tower names. Neither is a candidate. |
| STREET | comfort inn + quality inn louisville southwest @ 4444 Dixie Hwy | Two chain names at one address — a rebrand. Neither is a candidate. |
| URL | 7 Choice identities on `choicehotels.com/kentucky/shepherdsville/sleep-inn-hotels` | The bulk-edited OpenStreetMap tag 003 already refused. `comfort suites east` is a candidate but was **acquired from its own property page** (`…/comfort-suites-hotels/ky418`); its census URL is stale. |
| URL | la quinta … northeast old henry + la quinta inn and suites louisville | The captured page states 1501 Alliant Avenue, which is the **candidate's** address. The Old Henry row's census URL is wrong. |

No slug collisions. No telephone collisions.

**4. Service-animal semantics.** All 14 statements in the packet were re-checked
against the hardened rule. Thirteen state access; one (`comfort suites east`)
does not and is corrected. No exemption language became "charge applies": the
sentences carrying `except`, `free of charge` and `not applicable to` were all
verified to say a charge does **not** reach a service animal.

**5. Cleaning fees and other charges.** No candidate carries `other_charges`, a
`deposit`, or any `$$` double-currency rendering — verified across all 63
records. Comfort Suites East's block contains a $100 incidental deposit and a
$250 smoking cleaning fee; **neither was captured as a pet charge**, which is
correct. Twenty-two Hilton rows answer "Deposit: Yes" with no amount; the record
carries nothing, which is also correct, and is now reported as
`DEPOSIT_STATED_WITHOUT_AN_AMOUNT` rather than passing silently.

---

## Evidence verification across all 63

Run independently of the machine's dispositions:

- **63 of 63** policy blocks present on disk.
- **Every cited quote is a contiguous substring** of its persisted block.
- **Every published number appears in its own cited quote** — fees, tiers,
  weights and counts. The only three "misses" were sources spelling a number as
  a word ("two pets"), which is a correct parse.
- **No no-pets row carries pet pricing.** No published fact is absent from its
  source.

---

## Generic Atlas defects surfaced by Louisville

| # | Defect | Fix |
|---|---|---|
| 1 | A service-animal statement was any sentence containing "service animal". A damage-charge paragraph became a property's accessibility statement. | `states_service_animal_access` in `marriott_surface`, required by **both** readers that find the phrase — the generic reader and the Marriott surface each had their own implementation. |
| 2 | The bare-name rule was a hand-maintained list of chain words; it missed three of Louisville's eight. | `names_no_building` — the membrane's own distinguishing-token test, plus "two or more census rows extend this name". No list to maintain. |
| 3 | A page **title** was proposed as a canonical name. | `page_property_name` strips title furniture and keeps the property. |
| 4 | The review could only compare a record with itself, so a fact the reader missed was invisible. | `examine_block` reads the persisted policy block and reports what the source states and the record does not. Five Louisville rows. |
| 5 | `SOURCE_SILENT` was asserted without checking the source. Three rows claimed no price where the page states one. | `WITHHELD_REASON_CONTRADICTED_BY_BLOCK`. |
| 6 | A source stating one charge two ways had its basis chosen silently. | `FEE_BASIS_STATED_BOTH_WAYS` withholds the basis; a per-stay **cap** beside a nightly fee is correctly not a contradiction. |
| 7 | Every market's review stamped `PTF-ST-LOUIS-FOUNDER-REVIEW-003` as its work order — hard-coded. | `--work-order`. |
| 8 | An "unstated allowance" hold outranked a block that states the allowance in words. | The block wins; the finding drops to WARN. |

**Fixes that would help future markets, not done here:** a schema shape for
"a deposit is required, amount not stated" (22 Hilton rows say so and we publish
nothing); capturing a stated weight **scope** ("75lbs or less per pet" is stated
by La Quinta and dropped); and PTF-042's working-tree freeze, which fails for any
later work order that touches `policy_reading.py` and passes again only once the
change is committed.

---

## Reconciliation

```
packet rows            = 63
reviewed rows          = 63
distinct identity keys = 63
dispositions sum       = 63   (30 + 14 + 15 + 4)
each reviewed once     = True
closure                = 166 / 166   (0 missing, 0 duplicate, 0 foreign)
founder_decision       = empty on all 63
founder_reviewer_id    = empty on all 63
authority created      = none
markets registered     = the same 7; louisville-ky is not among them
```

---

## Declarations

```
LOUISVILLE CENSUS            = 166
LOUISVILLE FOUNDER CANDIDATES = 63
TOTAL REVIEWED               = 63
APPROVE_PET_FRIENDLY         = 30
APPROVE_VERIFIED_NO_PETS     = 14
APPROVE_WITH_CHANGE          = 15
HOLD                         = 4
PROPOSED AUTHORITY TOTAL     = 59

LOUISVILLE FOUNDER REVIEW COMPLETE   = YES
LOUISVILLE READY FOR OFFLINE REMEDIATION = YES

LOUISVILLE REGISTERED = FALSE
LOUISVILLE PUBLISHED  = FALSE
LOUISVILLE DEPLOYED   = FALSE
```

Every one of the 15 corrections and all four holds are resolvable offline, at
zero cost. Two holds need a person first.
