# PTF-DEFECT-LOCATOR-RECOVERY-FACT-LOSS-001 — locator recovery replaces a richer block with a poorer one

**Opened:** 2026-08-25, during PTF-INDIANAPOLIS-FOUNDER-REVIEW-002 (batch 2, row 20), by founder instruction.
**Status:** OPEN — generic reader defect; the affected Indianapolis record is corrected by founder
decision in `indianapolis_in_founder_decisions_002.json` (row 20), which cites the saved page.
**Severity:** guest-visible fact loss (a stated fee published as "Not stated").

## Defect

`scripts/pettripfinder/brightdata/policy_surface.py::recover_richer_block` accepts a replacement
window of the same document whenever it ADDS at least one actionable term the located block
lacks. It never checks what the replacement LOSES. Its score is
`(len(gained), len(terms), -len(candidate))`, so a candidate that gains one trivial term and
drops the fee, the deposit, the weight, the count, the species or a restriction still wins.

## The fixture (Indianapolis founder-review row 20)

Fairfield Inn & Suites Indianapolis Northwest — `indfn`, captured 2026-08-25T19:28:24Z,
document sha256 `6104785a69be37a73bbbf49a3921c3c6fbf4baba2852088ba85c2e42f869c8b9`.

- located block (`//div[text()='Pet Policy']/parent::*`): "Pet Policy / Pets Welcome / 2 pets max,
  75lbs max **Non-refundable fee: $75 USD Per Stay** / Maximum Pet Weight: 75.0lbs / Maximum Number of
  Pets in Room: 2"
- `locator.json.recovery`: `terms_before = ["$75","2 pets max","75.0lbs","75lbs","maximum number of
  pets","maximum pet","per stay"]`, `terms_added = ["75.0 lbs"]`, `recovered = true`
- persisted `policy-block.txt` (the replacement): the FAQ answer "Yes, pets are welcome … Up to 2
  pets are allowed per room. Each pet may weigh up to 75.0 lbs." — **no fee**.
- result: `pet_fee` withheld as SOURCE_SILENT; the profile would render "Not stated" against a
  first-party page that states $75 per stay.

Fixture files: `tests/pettripfinder/fixtures/locator_recovery_p3/` (page text, located block,
persisted replacement, metadata). Regression test:
`tests/pettripfinder/acquisition/test_locator_recovery_fact_loss_p3.py`.

## Required fix (founder-specified)

1. Recovery must **never** replace a located block with a candidate whose actionable-term set
   does not contain the located block's actionable-term set — fee, deposit, weight, count,
   species, restrictions included. `terms_after ⊇ terms_before` is a hard gate, not a score input.
2. Preserve the original richer block unless the replacement is demonstrably equal-or-better in
   policy-fact coverage; when no candidate satisfies (1), return `recovered=False` with a reason
   that names the terms the best candidate would have lost.
3. Regression coverage using row 20 as the fixture (added with this item; marked
   `xfail(strict=True)` until the fix lands so the suite stays green and the marker must be
   removed when the fix is in).
4. Re-derive every Indianapolis observation whose `locator.json.recovery.recovered` is true and
   whose `terms_before ⊄ terms_after` from its saved artifact (no re-fetch), then rebuild the
   store/packet.

## Related, found in the same review (not fixed here)

- P5 — the `static_html_walk` lane (Bright Data web-unlocker captures) bounds Hilton's policy
  block at "Non-refundable Fee" and drops the "Max weight …" / "Other pet information …" lines
  that follow it on the same page (rows 25 and 27), and runs no recovery at all. Same class of
  loss, different mechanism.
