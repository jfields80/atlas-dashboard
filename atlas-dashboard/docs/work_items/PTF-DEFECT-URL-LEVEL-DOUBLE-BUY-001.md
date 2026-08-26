# PTF-DEFECT-URL-LEVEL-DOUBLE-BUY-001 — the cost plan lets the same page be bought twice under two identity keys

**Opened:** 2026-08-25, during PTF-INDIANAPOLIS-FOUNDER-REVIEW-002 (batch 3, rows 25/26), by founder instruction.
**Status:** OPEN — generic acquisition defect. No refetch and no spend are involved in this item.
**Severity:** money (a paid page bought twice) and identity (two census rows for one building).

## Defect

`scripts/pettripfinder/acquisition/cohort_cost_plan.py::double_buy_check` proves "no property is
bought twice" by identity key only: `answered = {identity_key ...}`, `journalled = completed_keys()`.
Two census identities that resolve to the same canonical property — same URL, same property
code, same street — are two keys, so the check passes and the page is bought again.

## What happened (Indianapolis, saved artifacts)

- census rows `hampton inn indianapolis ne castleton` (OSM) and `hampton inn indianapolis northeast
  castleton` (prior census, the LIVE published key) — both 6817 East 82nd Street, both Hilton
  `indnehx` (URLs differ only by a trailing slash).
- `indianapolis_in_identity_duplicate_scan_002.json` flagged the pair on SOURCE_URL and on
  STREET_AND_POSTAL_CODE before any paid pass ran.
- pass 1 bought the page for the OSM key (VALID, 2026-08-25T20:51:44Z); pass 2 bought it again
  for the prior key (VALID, 2026-08-25T20:58:26Z, about 39c of the 78c pass-2 spend).
- `indianapolis_in_cohort_cost_plan_pass2_002.json.double_buy_check.no_property_is_bought_twice = true`.
- Recandidacy did not merge them because "NE" and "Northeast" are not name-compatible under its rule.

## Required fix (founder-specified)

If two candidate identities resolve to the same canonical property URL / property code / address,
the cost plan must prevent buying that page twice even when identity keys differ:

1. `double_buy_check` computes a canonical page key per cohort row (normalised URL without a
   trailing slash or query; the brand property code when the URL shape carries one; street
   identity as a third signal) and reports `same_page_as_a_prior_answer` and
   `same_page_within_the_cohort`.
2. Any hit fails `no_property_is_bought_twice`; the pass must SKIP the later key and carry the
   prior answer to it (SETTLED_BY_SHARED_PAGE) instead of paying again.
3. The duplicate scan's SOURCE_URL / STREET groups are an input to (1), not a report nobody reads.
4. Regression coverage from the saved Indianapolis artifacts (added with this item, xfail-strict
   until the fix lands): `tests/pettripfinder/acquisition/test_double_buy_url_level_p4.py`,
   fixture `tests/pettripfinder/fixtures/double_buy_p4/indianapolis_castleton_pair.json`.
5. Recandidacy: treat brand-standard abbreviations (NE/Northeast, NW/Northwest, Dwtn/Downtown,
   Dr/Drive, St/Street) as name-compatible so the twin is merged before it can be routed twice.
