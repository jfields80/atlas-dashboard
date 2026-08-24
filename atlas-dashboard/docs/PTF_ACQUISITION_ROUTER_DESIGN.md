# PTF Acquisition Router — design

**Status:** DESIGN ONLY. Nothing here is built, and building it is a separate
authorisation. Produced under PTF-ACQUISITION-BRAND-REPAIR-003 because both
repaired lanes reached their production targets.

**Evidence base:** PTF-BRIGHTDATA-MARRIOTT-PILOT-001 (5 properties),
PTF-BRIGHTDATA-CROSS-BRAND-PILOT-002 (30 properties, 6 buckets),
PTF-ACQUISITION-BRAND-REPAIR-003 (15 properties, 4 lanes). Every number below is
measured, not projected.

---

## 1. What the three pilots actually established

| Question | Answer | Where |
| --- | --- | --- |
| Can a managed browser reach hotel property pages? | Mostly. 21/30 in pilot-002; 15/15 after repair. | 002, 003 |
| Does it ever get a fact *wrong*? | **No.** 0 mismatches in 168 comparisons (002) and 79 (003). | 002, 003 |
| Is one provider enough? | **No.** Choice refused the Browser API 14/15 times and answers the Web Unlocker. | 002, 003 |
| Is one reader enough? | **Nearly.** One generic reader covers five brands; one brand needed its own locator. | 003 |
| Does rendered DOM satisfy the evidence contract? | Yes, unmodified. 21/21 and 15/15 publication-grade. | 002, 003 |
| What does it cost? | $0.16–0.24 per property attempted. | 002, 003 |

The single most important result is that **precision has never fallen below
100%**. Across all three pilots the acquisition path has produced zero values
that contradict a founder-reviewed record. Every shortfall has been *recall* —
a field not found — which is a coverage problem an adapter fixes. That
asymmetry is what makes a router worth building: the risk of routing is a
missed field, not a wrong one.

---

## 2. The router's job

> Given a property URL, return either a publication-grade evidence package or
> an honest refusal, at the lowest cost that works for that surface.

It is **acquisition only**. It does not decide, publish, promote, or write
authority. The governance chain is unchanged:

```
ROUTER → EVIDENCE → STRUCTURED PROPOSAL → FOUNDER REVIEW → AUTHORITY
```

---

## 3. Shape

```
                    ┌──────────────────┐
   property URL ───▶│  route selector  │  brand → ordered provider ladder
                    └────────┬─────────┘
                             ▼
                    ┌──────────────────┐
                    │ provider attempt │  ≤3 fresh attempts per provider
                    └────────┬─────────┘
                             ▼
                    ┌──────────────────┐
                    │   health gate    │  blank / denied / unhydrated / wrong page
                    └────────┬─────────┘
                             ▼
                    ┌──────────────────┐
                    │  identity gate   │  code, or path + name; never name alone
                    └────────┬─────────┘
                             ▼
                    ┌──────────────────┐
                    │ surface locator  │  brand container vs generic walk — they COMPETE
                    └────────┬─────────┘
                             ▼
                    ┌──────────────────┐
                    │     reader       │  labels only; no inference
                    └────────┬─────────┘
                             ▼
                    ┌──────────────────┐
                    │ evidence package │  artifacts + hashes + contiguous quotes
                    └────────┬─────────┘
                             ▼
              existing contracts, unmodified:
              policy_observation → policy_membrane → readiness → evidence
```

Everything below the route selector already exists and is measured. The router
is the selector plus a ladder, not a rewrite.

---

## 4. The provider ladder

Ordered cheapest-first, with the escalation rule that a **refusal escalates,
a silence does not**.

| Order | Provider | Cost signal | Use for |
| --- | --- | --- | --- |
| 1 | Web Unlocker | ~$0.05/property observed on the Choice lane | brands known to refuse a browser; any static policy surface |
| 2 | Browser API (US-pinned) | ~$0.16–0.24/property | JS-hydrated or interaction-gated surfaces |
| 3 | *(none)* → `CLAUDE_FALLBACK_REQUIRED` | operator time | everything else |

**Escalation rule.** `ACCESS_DENIED`, `BLANK_PAGE`, `UNHYDRATED`,
`NAVIGATION_FAILED` and `UNEXPECTED_PAGE` escalate to the next provider.
`POLICY_NOT_FOUND` and `IDENTITY_MISMATCH` do **not** — the surface answered,
and asking a different provider the same question wastes money on the same
answer. This distinction is the one the capture worker already refuses to blur.

**Why the unlocker goes first.** It is cheaper and it succeeded where the
browser could not. It cannot click, so any brand whose policy is behind a
disclosure must fall through to the browser — which is a *routing table entry*,
not a guess, because pilot-003 recorded which brands needed disclosure.

---

## 5. Brand routing table

Seeded from measurement, not from opinion. Every row cites the run that set it.

| Brand | First provider | Locator | Measured | Source |
| --- | --- | --- | --- | --- |
| MARRIOTT | Browser API | structural heading-parent | 5/5, 100%/100% | 001, 002, 003 |
| HILTON | Browser API | generic walk | 3/3, 100%/100% | 003 |
| IHG | Browser API | generic walk (FAQ accordion) | 4/5, 100%/62% | 002 |
| CHOICE | **Web Unlocker** | static-HTML walk | 5/5, 100%/88% | 003 |
| WYNDHAM | Browser API | **brand container** (unrendered) | 5/5, 100%/100% | 003 |
| ESA / SONESTA / RED ROOF / MOTEL 6 | Browser API | generic walk | 2/5 | 002 |
| independents | Browser API | generic walk | thin | 002 |

Unknown brands start at the unlocker and escalate. The table is **data, not
code** — a new brand is a row, and a row is added only by a run that measured
it.

---

## 6. What the router must not do

These are the failures the pilots actually produced, each now a rule:

1. **Never let a brand locator pre-empt the generic walk.** Hilton's brand
   selector matched a two-word label and dropped its recall from 56% to 33%.
   Locators compete on policy features; the richest bounded block wins.
2. **Never treat a price near a pet word as a pet fee.** A Choice guest-room
   card published a $160 nightly *room rate* as the pet fee. A rate marker
   between the pet word and the amount disqualifies the amount.
3. **Never let a deposit become a fee.** Comfort Inn Canton published its $100
   refundable deposit as the fee while the real fee was $25/night.
4. **Never resolve a contradiction the corpus left open.** Aloft's fee applies
   only to pets ≥40 lb where the maximum is 40 lb; schema 1.2 cannot express
   that, so the fee is withheld as `SCHEMA_CANNOT_REPRESENT`.
5. **Never read an acceptance inside a refusal.** "Sorry no other pets are
   allowed" contains "pets are allowed" and means its opposite — the mirror of
   a false `VERIFIED_NO_PETS`, and worse.
6. **Never accept a brand homepage or a locale redirect.** An unpinned exit
   served `marriott.com/es/default.mi`; only the property-code check caught it.
   Exit geography is pinned **and verified**, never assumed.

---

## 7. Cost model

Measured, per property **attempted**:

| Lane | Provider | $/property | $/accepted |
| --- | --- | --- | --- |
| Choice | Web Unlocker | ~$0.05 | ~$0.05 |
| Wyndham / Hilton / Marriott | Browser API | ~$0.16 | ~$0.16 |
| Repair-003 overall | mixed | $0.16 | **$0.164** |
| Pilot-002 overall | Browser API only | $0.24 | $0.34 |

Routing the unlocker first where it works is what moves $0.34 → $0.16. On a
1,000-property market that is roughly **$160 rather than $340**, and the
saving grows with the share of brands the unlocker can serve.

Controls the router needs from day one: a per-run ceiling, a per-property
attempt cap (3, unchanged), and a refusal to start when the zone balance is
below the run's projected cost.

---

## 8. Open items, honestly listed

- **Recall, not precision, is the remaining gap.** IHG 62%, MIXED thin. Both
  are reader-coverage problems and both are measurable before they are fixed.
- **Two corpus defects surfaced** and are not the router's to fix: a CVB
  directory index recorded as a property's `source_url`, and brand-renamed
  properties (Red Roof) failing the name gate. These need the alias mechanism.
- **Three contract gaps stand unpatched** (GAP-01 machine screenshot kind,
  GAP-02 managed-browser capture method, GAP-03 no capture-engine binding).
  The router makes GAP-03 sharper: with two providers in play, a record that
  cannot say which one fetched it is materially less reviewable.
- **Hyatt and Best Western remain out of scope** on premium-domain cost.

---

## 9. What a build work order would cover

1. `router.py` — the selector, the ladder, the escalation rule.
2. `routing_table.json` — brand → provider/locator, seeded from the table in §5.
3. Cost controls — run ceiling, balance pre-check, attempt cap.
4. Concurrency — bounded parallelism per provider, with the journal-per-property
   durability the pilots needed.
5. Provenance — carry provider and locator into the manifest, and propose
   GAP-02/GAP-03 vocabulary changes as a **separate** contract amendment.

None of that is authorised by this document.
