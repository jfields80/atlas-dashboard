# PTF-DEFECT-STATIC-LANE-BLOCK-TRUNCATION-001 — the static lane truncates the policy block after the first field

**Opened:** 2026-08-25, during PTF-INDIANAPOLIS-FOUNDER-REVIEW-002 (batch 3, rows 25 and 27), by founder instruction.
**Status:** OPEN — generic reader defect. The two affected Indianapolis records are corrected by
founder decision in `indianapolis_in_founder_decisions_002.json` (rows 25, 27), citing the same saved pages.
**Severity:** guest-visible fact loss (fee tiers, count, species, weight limit dropped).

## Defect

`scripts/pettripfinder/brightdata/unlocker_capture.py::locate_policy_in_text` (the
`static_html_walk` lane used by Bright Data web-unlocker captures) builds candidate blocks by
joining a signal-phrase line with at most the next three lines (`for span in (1, 2, 3, 4)`) and
keeps the highest-feature candidate. Hilton's "Hotel policies" table renders one cell per line:

```
Pets allowed / Yes / Deposit / Yes. $50.00 Non-refundable Fee / Other pet information /
1-4 night stay $50; 5+ night stay $75; 2 pets max; dog or cat only
```

so the block ends at "Non-refundable Fee" and the tiers, count and species (row 25) or the
"Max weight / 100 lbs" pair (row 27) can never join it. The lane runs no `recover_richer_block`
afterwards either, so nothing pulls them back. The browser lane (`generic_signal_walk`) on the
same Hilton template (rows 21–24) keeps the whole container.

## Required fix (founder-specified)

Static HTML policy extraction must preserve/recover adjacent supported pet-policy facts — fee tiers,
weight, count, species, deposits and restrictions — rather than truncating after the first field:

1. Grow the block past the four-line span while the following lines carry actionable pet terms
   (`policy_surface.actionable_pet_terms`) or a policy label ("Other pet information", "Max weight",
   "Max size", "Pet weight limit", "pets allowed"), stopping at the first non-pet line
   (for example "A fee of up to $250 USD will be assessed for smoking ...").
2. Run `recover_richer_block` on the static lane too, under the P3 rule (never lose a supported term).
3. Regression coverage from the saved Indianapolis artifacts (added with this item, xfail-strict
   until the fix lands): `tests/pettripfinder/acquisition/test_static_lane_truncation_p5.py`,
   fixtures `tests/pettripfinder/fixtures/static_lane_p5/` (the exact `html_to_text` output the
   lane saw for rows 25 and 27; checked for keys/tokens, none present).
4. Re-derive every Indianapolis static-lane observation from its saved artifact after the fix
   (rows 25, 26, 27 at least), no refetch.
