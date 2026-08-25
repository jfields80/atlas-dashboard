# PTF-LOUISVILLE-FOUNDER-FINAL-006 — FINAL

**Market:** louisville-ky · **Census:** 166, unchanged · **Candidates:** 63
**Spend:** $0.00 · **Provider calls:** 0 · **Pages re-fetched:** 0
**Registered / Published / Deployed:** FALSE / FALSE / FALSE

---

## Result

```
LOUISVILLE CENSUS                 = 166
LOUISVILLE FINAL PET_FRIENDLY     = 46
LOUISVILLE FINAL VERIFIED_NO_PETS = 17
LOUISVILLE FINAL SIGNED AUTHORITY = 63
LOUISVILLE REMAINING HOLD         = 0
```

---

## 1. Candlewood Suites Louisville South Fair and Expo — **identity APPROVED**

A second strong property-specific signal exists in evidence already on disk, and
nothing contradicts it. The identity rule was applied, not weakened: two
agreeing strong signals, exactly as the founder's own rule requires.

### The evidence, exactly

| Signal | Census | Page | Verdict |
|---|---|---|---|
| **Street** | 6540 Paramount Park Dr, Louisville 40213 | 6540 Paramount Park Dr. | **EXACT MATCH** |
| **IHG property code** | `sdfpp`, carried in the census row's `official_url` | `sdfpp` in the captured document's own `<link rel="canonical">` **and** its `og:url` | **EXACT MATCH** |
| Telephone | *(absent)* | 1-502-8904270 | **silence, not agreement** — corroborates nothing either way |

**Why the code is independent evidence and not a circular reading of our own
request:**

- The census row inherited that URL from the **prior 001 build**, whose own
  record names its source as `goto_louisville` — the Louisville destination
  directory — and its provenance as
  `data/market_research/louisville/candidate_ledger.json`. It predates this
  capture entirely.
- The captured page then identifies **itself** as `sdfpp`: 112 occurrences,
  including the canonical link and the Open Graph URL.
- `sdfpp` is the **only** IHG property code anywhere in the document — 42
  code-shaped path matches, 1 distinct value. There is no competing identity.
- The capture was **not redirected**: requested URL == final URL, so the page
  served is the page the code names.

The only disagreement is the marketing form of the name — *"Candlewood Suites
Louisville - Fair/Expo Center"* against *"…South Fair and Expo"*.

**Applied:** an identity override in
`markets/founder_overrides/louisville-ky.json` recording all of the above, and a
canonical-name correction in `markets/name_corrections/louisville-ky.json`. The
census file itself is untouched — it still reads "Candlewood Suites Louisville
South Fair and Expo", and a test asserts it.

One reader repair came with it: the block states *"A nonrefundable pet fee
applies. 75 USD for one to six nights, 150 USD for seven or more nights"*, and
the record had been calling that `SOURCE_SILENT`. A pet charge noun and its money
now bind across the sentence break, so the reason reads `SOURCE_AMBIGUOUS` with
`FLAG_PET_AMOUNT_NOT_BOUND`. The value is still not published — a word-numbered
ladder is not yet readable — but the record no longer claims the page said
nothing.

**Disposition after re-derivation: APPROVE_PET_FRIENDLY.** Membrane VALID,
publication grade confirmed, and every other check passes.

---

## 2. Founder signature

| | |
|---|---|
| **Ledger** | `launch_packages/pettripfinder/louisville_ky_founder_decisions_006.json` |
| Schema | `ptf-founder-decision-ledger/1.0` |
| Signed | **63** — 46 `PUBLISHED_PET_FRIENDLY`, 17 `VERIFIED_NO_PETS` |
| Withheld | **0** |
| `decided_by` | `jfields80` on 2026-08-24 |
| `recorded_by` | `claude-opus-5 (PTF-LOUISVILLE-FOUNDER-FINAL-006, agent) — transcription only` |
| Authorization | the founder's words from this work order, quoted in full, including the Candlewood condition |

Safeguards, as established in the St. Louis flow:

- **The attestation does not live in the packet.** The packet is emitted by an
  idempotent builder; the ledger is a separate, non-regenerable file.
- **Canonical vocabulary** — `founder-approval-vocabulary/1.0`.
- **Who decided and who typed are two different fields**, and the second says so
  in words.
- **Every signature binds the semantic hash the founder was shown**, plus the
  snapshot hash and source URL. A record that changes afterwards stops matching,
  and the ledger visibly stops covering it. Asserted for all 63.
- **No row signed twice** — asserted.
- **Scope is named, not inferred**: only `APPROVE_PET_FRIENDLY` and
  `APPROVE_VERIFIED_NO_PETS` were signable, with `--expect-signed 63`.
- **No held row could enter**: there were none left, and the authority is
  asserted equal to the signed set.

---

## 3. Proposed authority

| | |
|---|---|
| **Artifact** | `launch_packages/pettripfinder/louisville_ky_proposed_authority_006.json` |
| Schema | `ptf-market-proposed-authority/1.0` |
| Rows | **63** — 46 pet-friendly, 17 verified-no-pets |
| Gate | only a row the founder signed |
| `registered` / `published` / `deployed` | false / false / false |

It deliberately does **not** live in `markets/authority/louisville-ky/`: creating
that directory would register the market, and registering market N+1 invalidates
the current production deployment record. There is no Louisville authority shard,
the market contract is still in `markets/pending/`, and
`available_market_ids()` still returns the same seven markets.

Every authority row carries its evidence quotes, source URL, snapshot hash,
reader provenance, withheld fields and non-inferences — 63 of 63 on each.

---

## 4. Reconciliation — 166 / 166

```
census identities        = 166   (file unchanged)
closure rows             = 166 / 166
closure reconciliation   = 0 missing, 0 duplicate, 0 foreign
closure keys == census keys        = True
closure dispositions     = HELD_REVIEW 63 · ACCESS_UNRESOLVED 41 ·
                           INSUFFICIENT_EVIDENCE 61 · POLICY_NOT_FOUND 1
signed rows              = 63 (46 + 17), 0 withheld
authority rows           = 63, distinct 63
authority ⊆ census       = True
authority == HELD_REVIEW = True
observations             = 63, all PUBLICATION_GRADE_CONFIRMED
membrane                 = 63 VALID
```

The 103 census identities outside the authority are accounted for by closure:
41 routed but unreachable, 61 without enough evidence, 1 whose page states no
policy.

---

## Declarations

```
LOUISVILLE CENSUS                 = 166
LOUISVILLE FINAL PET_FRIENDLY     = 46
LOUISVILLE FINAL VERIFIED_NO_PETS = 17
LOUISVILLE FINAL SIGNED AUTHORITY = 63
LOUISVILLE REMAINING HOLD         = 0

LOUISVILLE FOUNDER SIGNATURE COMPLETE = YES
LOUISVILLE AUTHORITY CREATED          = YES  (proposed, outside the registry)

LOUISVILLE REGISTERED = FALSE
LOUISVILLE PUBLISHED  = FALSE
LOUISVILLE DEPLOYED   = FALSE
```
