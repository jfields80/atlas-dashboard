# PTF-DEFECT-OBSERVATION-STORE-TIMESTAMP-001 — observed_at / retrieved_at are hard-coded

**Opened:** 2026-08-25, during PTF-INDIANAPOLIS-FOUNDER-REVIEW-002 (batch 1), by founder instruction.
**Status:** FIXED for the generic builder in PTF-INDIANAPOLIS-PROMOTION-AUTHORITY-PREP-003 (`market_observation_store.py` now derives `observed_at`/`retrieved_at` from the journal `completed_at` carried on the result row, records `capture_time` with its basis, and passes the true date into the publication-grade entries; regression `tests/pettripfinder/acquisition/test_observation_store_capture_time_p1.py`). Indianapolis stores were rebuilt (`003a`, `003`) — 51/51 and 49/49 rows carry the journal time. **Louisville (63 LIVE records, true dates 2026-08-24/25) and St. Louis (dates coincidentally right) remain as recorded and need their own correction order** — see `indianapolis_in_p1_blast_radius_003.json`.
**Severity:** data-integrity (a false capture date is written into every authority row).

## Defect

`scripts/pettripfinder/acquisition/market_observation_store.py` lines 226-227
(introduced in `df6aad57`, 2026-08-22):

```python
("observed_at", "2026-08-23"),
("retrieved_at", "2026-08-23"),
```

Every observation the generic store builds carries that literal date regardless of when
the capture happened. The true timestamp exists in the acquisition journal of the pass
that produced the artifact (`<run_dir>/journal.jsonl`, field `completed_at`, ISO-8601 UTC)
and is already joined to the result row (`acquisition_pass`, `artifact_dir`).

## Required fix

1. Derive `observed_at` and `retrieved_at` from the journal row's `completed_at` for the
   identity (date part for `observed_at`, full timestamp retained in a new
   `captured_at_utc` field); fall back to the artifact directory mtime only when no journal
   row exists, and say so in a `capture_time_basis` field.
2. A test that builds a store from a fixture journal dated on a day other than 2026-08-23
   and asserts the store carries the journal date.
3. Rebuild `indianapolis_in_observation_store_002.json` (and the packet/analysis derived
   from it) after the fix; the founder decision ledger
   `indianapolis_in_founder_decisions_002.json` already records the true
   `completed_at` per row so decisions bind to the right capture.

## Blast radius (measured 2026-08-25, read-only; nothing modified)

| market | store records with observed_at=2026-08-23 | true capture dates (journal) | factually wrong? |
|---|---|---|---|
| Indianapolis (`indianapolis_in_observation_store_002`) | 51 | 2026-08-25 (pass1 79 rows, pass2 2 rows) | YES — all 51 |
| Louisville (`louisville_ky_observation_store_002/003/005/006`) | 43 / 63 / 63 / 63 | rebuild_002: 2026-08-24 (58); expansion_003: 2026-08-25 (29) | YES — 63 attested records |
| St. Louis (`st_louis_mo_observation_store_001/002/004/006/007`) | 19 / 124 / 124 / 124 / 124 | st_louis_paid_002: 2026-08-23 (132) | NO — coincidentally correct; the mechanism is still wrong |

Downstream files carrying the literal (counts of `"observed_at": "2026-08-23"`):
`louisville_ky_proposed_authority_006.json` 63; `markets/authority/louisville-ky/hotel_exclusions.json` 17;
global `hotel_exclusions.json` 54 (17 Louisville + 37 St. Louis); `st_louis_mo_proposed_authority_005/007/008b.json` 114/121/119;
`markets/authority/st-louis-mo/hotel_exclusions.json` 37; `identity_census/st-louis-mo.json` 357 (census observed_at, separate field lineage — verify before treating as affected).

**Louisville is LIVE with 63 records whose observed_at is 1-2 days early. Per founder instruction
(PTF-INDIANAPOLIS-FOUNDER-REVIEW-002) St. Louis and Louisville are NOT modified by this item;
a separate correction work order is required for Louisville's live records.**
