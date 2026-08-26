# PTF-ST-LOUIS-PUBLICATION-CLEANUP-008B — Duplicate Authority Cleanup, FINAL

**Market:** `st-louis-mo` **Branch:** `feature/ptf-st-louis-market-001`
**Start HEAD:** `a5e6d01`
**Offline only — zero provider calls, zero spend, zero re-fetches.**
**NOT REGISTERED. NOT PUBLISHED. NOT DEPLOYED.**

---

## A. The arithmetic checked out before anything was written

| | |
|---|---|
| Signed rows before | 121 (83 pet-friendly, 38 verified-no-pets) |
| `wingate at wyndham` | was **PET_FRIENDLY** → 83 − 1 = 82 |
| `doubletree` | was **VERIFIED_NO_PETS** → 38 − 1 = 37 |
| **Current signed authority** | **119** = 82 + 37 |

Matches your prediction exactly, so I proceeded without stopping.

## B. Supersession used the vocabulary that already existed

`contracts.enums.APPROVAL_DECISIONS` already carries **`SUPERSEDED`**, documented
as *"replaced by a later decision. Not publishable."* It is writable and is
absent from `PUBLISHING_DECISIONS`. That is precisely the semantics required, so
**no new vocabulary was invented**.

## C. Nothing was deleted and nothing was edited

The whole difficulty of "retire an attestation" is that it must not mean delete
and must not mean edit — either destroys the only evidence the founder ever
approved the row. So:

- `st_louis_mo_founder_decisions_005.json` **still signs 114 rows** and still
  contains `doubletree` with `APPROVED_AFTER_CURRENT_REVIEW / jfields80`.
- `st_louis_mo_founder_decisions_007.json` **still signs 7 rows** and still
  contains `wingate at wyndham` the same way.
- A **later** ledger, `st_louis_mo_founder_withdrawals_008b.json`, records the
  supersession.

The current authority is `(union of signed) MINUS (withdrawn)`. Both retired
rows are reported in `superseded_rows` with what they were, what they are now,
which work order signed them, **which file still holds that attestation**, and
which identity they survive in favour of. A test asserts the original rulings
are still on file, unedited.

## D. The two withdrawals

### Wingate — retired `wingate at wyndham`, kept `wingate by wyndham st louis fenton route 66`

One building on four independent signals: **identical source URL** (both rows
captured from the same page), same street, same postal code 63026, identical
facts ($25 per pet per night, 70 lb).

**One discrepancy is recorded rather than papered over.** The two census rows
carry different telephone numbers — `6366001818` on the retired row,
`6364921357` on the surviving one — and the property's own page prints
636-600-1818, which matches the *retired* row. Retiring a row does not resolve
that, so the ledger says so and flags the surviving row's telephone as a
candidate for a later census-hygiene pass. A test pins that the discrepancy is
disclosed.

### DoubleTree — retired `doubletree`, kept `doubletree by hilton hotel collinsville st louis`

One building on five signals with **no discrepancy at all**: same street, same
postal 62234, **same telephone** 6183452800, **same Hilton property code
`stlcndt`** in both source URLs, same VERIFIED_NO_PETS finding.

## E. Dual-brand confirmation — PASS

1065 Chesterfield Pkwy E: **Fairfield by Marriott (`stlff`)** and **SpringHill
Suites (`stlsu`)** confirmed as two distinct hotels. Both remain; neither was
merged or suppressed.

Persisted in the non-regenerable withdrawal ledger and surfaced on the authority
artifact as `identity_confirmations`, so the publication gate can rely on it
rather than re-asking.

The discriminator is named: **different Marriott property codes**, the same key
PTF-COLUMBUS-IDENTITY-CLEANUP-001 used to keep three Columbus Embassy Suites
apart. A shared switchboard is ordinary at a dual-brand property.

Worth stating plainly: the two rows carry **opposite** pet findings — Fairfield
pet-friendly, SpringHill verified-no-pets. That is only coherent if they really
are two hotels. Merging them would have published one of the two findings about
a building that never made it.

## F. Publication inventory, re-simulated — clean

| Check | Result |
|---|---|
| Public hotel routes | **82** |
| Distinct canonical names | 82 |
| Slug collisions (PF + NP) | **NONE** |
| Identity collisions | **NONE** |
| Rows sharing a source URL | **NONE** |
| Same-address groups | **1** — the confirmed dual-brand pair |
| Missing required fields | **NONE** |
| Fairfield + SpringHill both present | **yes** |
| Retired Wingate / DoubleTree absent | **yes** |
| Days Inn Pontoon Beach still excluded | **yes** |

## G. Reconciliation — 357

Closure is derived from the census and is unaffected by supersession:
count 357, active denominator 357, missing 0, foreign 0, duplicate 0.

**HELD_REVIEW 122 = 119 current authority + 2 superseded + 1 held.**
ACCESS_UNRESOLVED 153 · INSUFFICIENT_EVIDENCE 66 · POLICY_NOT_FOUND 16.
Total **357**.

## H. Production untouched

`build_global_authority --check` → build marker `241ce93c…`, all artifacts match.
`global_deployment.verify_manifest()` → `[]`. `markets/authority/st-louis-mo/`
and `markets/st-louis-mo.json` both absent.

## I. Remaining publication blockers — 2 (down from 3)

1. **No release contract for St. Louis** — `deploy/netlify/release_contracts/st-louis-mo.json`
   does not exist. Carries the 27 minimum release gates, expected counts, route
   mode and forbidden output tokens. Out of scope for this work order by
   instruction. Offline.
2. **Deployment authorization must be re-issued** — registration invalidates
   `ptf-auth-047-a324b1bf5023` because it copies the `launch_participation`
   sha256 that a ninth row changes. Your signature. Offline.

**Duplicate publication blockers remaining: 0.**

## J. Status

```
ST. LOUIS DUPLICATE AUTHORITY CLEANUP COMPLETE = YES
ST. LOUIS CURRENT SIGNED AUTHORITY             = 119
ST. LOUIS PET_FRIENDLY                         = 82
ST. LOUIS VERIFIED_NO_PETS                     = 37
ST. LOUIS PROJECTED PUBLIC HOTEL ROUTES        = 82
ST. LOUIS DUAL-BRAND CONFIRMED                 = YES

ST. LOUIS REGISTERED = FALSE
ST. LOUIS PUBLISHED  = FALSE
ST. LOUIS DEPLOYED   = FALSE
```
