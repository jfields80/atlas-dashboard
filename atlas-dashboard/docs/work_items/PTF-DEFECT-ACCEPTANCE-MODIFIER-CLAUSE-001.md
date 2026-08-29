# PTF-DEFECT-ACCEPTANCE-MODIFIER-CLAUSE-001 — the acceptance parser misses "pets … are welcome" when a modifier sits between

**Opened:** 2026-08-25, during PTF-INDIANAPOLIS-FOUNDER-REVIEW-002 (batch 5, row 48), by founder instruction.
**Status:** OPEN — generic reader defect. The affected Indianapolis record is corrected by founder
decision in `indianapolis_in_founder_decisions_002.json` (row 48), citing the same saved page.
**Severity:** a pet-friendly property withheld as "allowance not stated" (readiness POLICY_PARTIAL,
machine RECOMMEND_HOLD_EVIDENCE_INCOMPLETE) although the page states acceptance in plain words.

## Defect

`scripts/pettripfinder/brightdata/policy_reading.py::parse` on the Wyndham policy block

```
Up to 2 pets with a maximum weight of 50lbs are welcome for a non-refundable charge of
10.00 USD per pet per night. ADA defined service animals are welcome at this hotel.
```

extracts the fee, weight, count and service-animal sentence but withholds `pets_allowed` as
SOURCE_SILENT ("the source prices or limits a pet without ever stating that pets are accepted").
The sentence's subject is "Up to 2 pets" and its predicate is "are welcome"; the parser's
acceptance patterns do not allow the modifier clause "with a maximum weight of 50lbs" between them.
The machine then asked the founder for a class-wide ruling on whether a price implies an allowance —
a ruling this sentence does not need.

## Required fix (founder-specified)

The pet-acceptance parser must recognise affirmative constructions where modifiers occur between
"pets" and "are welcome", such as "Up to 2 pets with a maximum weight of 50lbs are welcome":

1. Acceptance detection matches `pets? … (are|is) welcome` with an intervening modifier clause
   (weight, count, species, "per room", parenthetical) bounded to the same sentence, and quotes the
   whole subject-to-predicate span as evidence.
2. Negations and service-animal-only statements in the same span still win (existing rules).
3. Regression coverage from the saved Indianapolis artifact (added with this item, xfail-strict
   until the fix lands): `tests/pettripfinder/acquisition/test_acceptance_modifier_clause_p7.py`,
   fixture `tests/pettripfinder/fixtures/acceptance_p7/indianapolis_row48_block.json`.
4. Re-run readiness over the Indianapolis store after the fix; any other row carrying
   ALLOWANCE_NOT_STATED with a "… are welcome" sentence is the same defect.
