# PTF-DEFECT-LABEL-VALUE-FIELD-BOUNDARY-001 — label/value extraction splices one field's amount onto the next field's label

**Opened:** 2026-08-25, during PTF-INDIANAPOLIS-FOUNDER-REVIEW-002 (batch 4, row 31), by founder instruction.
**Status:** OPEN — generic reader defect. The affected Indianapolis record is corrected by founder
decision in `indianapolis_in_founder_decisions_002.json` (row 31), citing the same saved page.
**Severity:** guest-visible fact ERROR (a $75 deposit published as $25; the $25 per-pet nightly fee
and its $125 per-pet cap dropped).

## Defect

`scripts/pettripfinder/brightdata/policy_reading.py::parse` on the IHG structured policy block

```
Pet fee per night: 25 USD  Pet damage deposit: 75 USD  Pet weight limit: 50  2 pets allowed
```

emits `pet_deposit = 2500` with the evidence quote **"25 USD Pet damage deposit"** — the amount that
belongs to the field on the LEFT ("Pet fee per night: 25 USD") spliced onto the label of the field on
the RIGHT ("Pet damage deposit: 75 USD"). The fee itself is then withheld as
SCHEMA_CANNOT_REPRESENT / FLAG_PET_AMOUNT_NOT_BOUND because its amount was consumed by the deposit
pattern. The page states, in prose, "75 dollar refundable deposit plus 25.00 dollar per pet, per night
fee … capped at 125.00 per pet after staying for 5 nights".

## Required fix (founder-specified)

Label/value extraction must not cross adjacent policy-field boundaries. A parser must not splice the
amount from one field onto the label of the next field:

1. On a `label: value` surface, an amount binds only to the label that PRECEDES it within the same
   field; a `<Label>:` token ends the previous field. A deposit quote must therefore read
   "Pet damage deposit: 75 USD", never "25 USD Pet damage deposit".
2. With the boundary respected, "Pet fee per night: 25 USD" binds `pet_fee 2500 per_night` (the
   prose adds `per_pet` and the $125-per-pet cap).
3. Regression coverage from the saved Indianapolis artifact (added with this item, xfail-strict until
   the fix lands): `tests/pettripfinder/acquisition/test_label_value_field_boundary_p6.py`, fixture
   `tests/pettripfinder/fixtures/label_value_p6/indianapolis_row31_block.json` (the exact
   `policy-block.txt`, the extraction as produced, and the page's prose sentence).
4. Re-derive every IHG structured-block observation in the Indianapolis store from its saved artifact
   after the fix (no refetch); rows 3 and 28 use the same surface and should be re-checked.
