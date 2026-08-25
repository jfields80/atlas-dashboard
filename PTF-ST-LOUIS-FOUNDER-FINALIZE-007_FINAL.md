# PTF-ST-LOUIS-FOUNDER-FINALIZE-007 — Final Founder Signature, FINAL

**Market:** `st-louis-mo` **Branch:** `feature/ptf-st-louis-market-001`
**Start HEAD:** `e948dff`
**Offline only — zero provider calls, zero spend, zero re-fetches.**
**NOT REGISTERED. NOT PUBLISHED. NOT DEPLOYED.**

---

## A. Result

| | |
|---|---|
| Previous signed authority | **114** |
| Newly signed this pass | **7** |
| **Final signed authority** | **121** |
| Final signed PET_FRIENDLY | **83** |
| Final signed VERIFIED_NO_PETS | **38** |
| Remaining HOLD | **1** |

**Wingate newly signed: YES.**

## B. Authorization 1 — the six newly clean rows

Signed, and **no row was re-signed**. The signature CLI now takes
`--already-signed`: a row an earlier ledger covers is *carried*, not rewritten.
An attestation is a dated act by a named person, and writing a second one over
the same row either duplicates a ruling or silently restates it under a new
date. The two ledgers share **zero** rows — asserted by test — and the market's
signature is their union.

| | |
|---|---|
| `st_louis_mo_founder_decisions_005.json` | 114 rows |
| `st_louis_mo_founder_decisions_007.json` | 7 rows, 114 carried, market total 121 |

## C. Authorization 2 — Wingate

`Wingate At Wyndham` → `Wingate by Wyndham St. Louis/Fenton Route 66`, applied
through the same evidence-cited overlay used for Hampton and the first three.
Repository precedent does require it: **a test asserts the census file still
says `Wingate At Wyndham`**, and the observation keeps the census reading beside
the corrected one rather than overwriting it.

After the correction the row was re-derived and checked before signing:

| Check | Result |
|---|---|
| Canonical name | Wingate by Wyndham St. Louis/Fenton Route 66 |
| Census name preserved | Wingate At Wyndham |
| Identity adjudication still binds | **yes** — `jfields80`, 2 agreeing signals |
| Membrane | **VALID** |
| Disposition | **APPROVE_PET_FRIENDLY** |

So it was marked clean, signed, and carries authority — the sequence you set out.

## D. Days Inn & Suites Pontoon Beach — still HOLD

**The rule was not weakened.** Nothing was re-evaluated in its favour and no
adjudication was written for it. The evidence is unchanged from 006:

| Signal | Census | Page | Verdict |
|---|---|---|---|
| Street | 5105 Highway 111, Pontoon Beach IL 62040 | 5105 Highway 111 | **EXACT MATCH** |
| Telephone | 618-219-8631 | 1-618-**797-2727** | **DIFFERENT** |
| Property code | absent | absent | silence |

**One agreeing signal, one contradicting.** Your rule requires two *agreeing*
signals; it does not permit one agreement plus one contradiction. Two distinct
local 618 lines — not a toll-free reservations number against a property line.

Membrane: `REJECT_WRONG_PROPERTY` / M10. No `identity_adjudication` present.
Disposition: HOLD. A test asserts the refusal stands and that every approved
identity carries ≥ 2 signals while the refused one carries 1.

**What would settle it, at no cost:** a property code on either side, or
evidence the telephone changed in a rebrand from "Days Inn & Suites" to "Days
Inn" — which would explain both the name and the number. Neither is on disk.

## E. Reconciliation — 357

| | |
|---|---|
| Census identities | 357 |
| Closure rows | 357 |
| Missing / foreign / duplicate | **0 / 0 / 0** |

| Closure state | Count |
|---|---|
| HELD_REVIEW | **122** = 121 signed + 1 unsigned |
| ACCESS_UNRESOLVED | 153 |
| INSUFFICIENT_EVIDENCE | 66 |
| POLICY_NOT_FOUND | 16 |
| **Total** | **357** |

The authority set and the union of both signature ledgers are the **same set** —
asserted, not assumed. All 121 signatures bind to the current records with zero
hash drift.

## F. Still not registered

`build_global_authority --check`: 8 source markets, 277 routes, 102 exclusions,
369 seed rows, build marker `241ce93c…` — **byte-identical**. St. Louis is not
enrolled, `markets/authority/st-louis-mo/` does not exist, and
`markets/st-louis-mo.json` does not exist. Tests assert all three.

## G. Tests

**22 new**, in `tests/pettripfinder/test_founder_finalize_007.py`. The ones that
carry the pass: a row an earlier ledger signed is carried and not re-signed; the
market total is the union; two ledgers signing one row is **refused**; authority
is built from the union rather than the newest ledger alone; a HOLD row is still
never signed on a later pass.

One earlier test was restated. 006 asserted Wingate was *absent* from the name
overlay — true then, and deliberately false now. It now asserts what 006
actually claimed: that a name correction is authorised **per row and traceable**,
with Hampton's `authorised_by` naming 006 and Wingate's naming 007. A test that
pinned Wingate's absence would have to be deleted the moment you said yes, which
is a test asserting the calendar rather than the rule.

| Chunk | Result |
|---|---|
| founder / policy / contracts / brightdata / discovery / St. Louis | 1853 passed, 29 skipped |
| `tests/pettripfinder/acquisition` | **134 failed — byte-identical to the measured baseline**, zero new, zero fixed |
| rest of `tests/pettripfinder` | 3 failed (pre-existing Indianapolis), rest passed |
| `tests/website_generation` | 3412 passed, 5 skipped |
| all other packages + top level | 3325 passed, 14 skipped |

## H. Status

```
ST. LOUIS CENSUS COMPLETE                  = YES  (357)
ST. LOUIS ACTIVE CLOSURE COMPLETE          = YES  (357/357)
ST. LOUIS FINAL FOUNDER SIGNATURE COMPLETE = YES
ST. LOUIS FINAL SIGNED AUTHORITY           = 121
ST. LOUIS FINAL PET_FRIENDLY               = 83
ST. LOUIS FINAL VERIFIED_NO_PETS           = 38
ST. LOUIS REMAINING HOLD                   = 1

ST. LOUIS REGISTERED = FALSE
ST. LOUIS PUBLISHED  = FALSE
ST. LOUIS DEPLOYED   = FALSE
```

Measurement disabled, zero affiliates enrolled — unchanged.

**121 of 357 active identities (33.9%) now carry founder-signed authority**,
built entirely from evidence already on disk. One row remains, refused by the
founder's own rule, and it needs no provider call to settle.
