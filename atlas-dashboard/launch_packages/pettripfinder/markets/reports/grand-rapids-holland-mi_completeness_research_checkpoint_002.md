# Grand Rapids--Holland completeness research checkpoint 002

Work order: `PTF-GRAND-RAPIDS-HOLLAND-CENSUS-COMPLETENESS-002`  
Checkpoint date: 2026-08-17  
Scope: discovery and identity reconciliation only. No pet-policy surface was
opened, interpreted, or captured.

## Preflight

- Branch: `grok/ptf-grand-rapids-holland-market-001`
- Starting checkpoint: `df307cce5dd605e7242719405c70ea57ce971b00`
- `origin/main`: `4999c59dc3a743373b76a01e550915c684101d3a` (advanced since
  the prior checkpoint).
- The branch/main changed-path comparison had no overlap with the
  Grand Rapids--Holland market-factory files. This census-only audit may
  proceed without a merge; no rebase or cherry-pick is authorized.

## Address-bound official property results retained so far

The following previously unresolved locator leads have first-party property
pages with exact address and telephone bindings:

- Courtyard by Marriott Grand Rapids Downtown — 11 Monroe Ave NW, Grand
  Rapids, MI 49503; Marriott property code `GRRDT`.
- SpringHill Suites by Marriott Grand Rapids North — 450 Center Dr, Grand
  Rapids, MI 49544; Marriott property code `GRRSH`.
- Residence Inn by Marriott Grand Rapids West — 3451 Rivertown Point Ct SW,
  Grandville, MI 49418; Marriott property code `GRRRW`.
- TownePlace Suites Grand Rapids Airport Southeast — 4850 Town Center Dr SE,
  Grand Rapids, MI 49512; Marriott property code `GRRTE`.
- Sheraton Grand Rapids Airport Hotel — 5700 28th St SE, Grand Rapids, MI
  49546; Marriott property code `GRRIS`.
- Hampton Inn & Suites Grand Rapids-Airport 28th St — 5200 28th St SE, Grand
  Rapids, MI 49512; Hilton property code `GRRHSHX`.
- Hampton Inn & Suites Grandville Grand Rapids South — 4755 Wilson Ave SW,
  Grandville, MI 49418; Hilton property code `GRRADHX`.
- Hampton Inn Grand Rapids-South — 755 54th St SW, Wyoming, MI 49509; Hilton
  property code `GRRSOHX`.
- Home2 Suites by Hilton Holland — 3140 West Shore Dr, Holland, MI 49424;
  Hilton property code `HLMHTHT`.
- AmericInn by Wyndham Grand Rapids Airport North — 5500 28th St SE, Grand
  Rapids, MI 49512.
- AmericInn by Wyndham Holland MI — 422 E 32nd St, Holland, MI 49423.

`Home2 Suites by Hilton Grand Rapids South`, at 2288 64th St SW, Byron Center,
MI 49315, was also address-bound. It is held for explicit boundary exclusion:
Byron Center is outside the current Grand Rapids--Holland municipality set and
is not being added merely to increase the census.

## Local official discovery results retained so far

- Experience Grand Rapids documents 13 downtown hotels. The existing census
  plus the resolved Courtyard totals 12; The Finnley Hotel, 65 Monroe Center
  St NW, is the independently surfaced thirteenth hotel.
- Experience Grand Rapids documents The BlueJay Hotel at 644 Bridge St NW,
  Grand Rapids, a northwest/downtown boutique hotel.
- The same official tourism family identifies a new Ada hotel and airport
  candidates that require independent property-page binding before census
  inclusion.
- Experience Grand Rapids establishes address bindings for Baymont Inn &
  Suites Grand Rapids Southeast (2873 Kraft Ave SE), Country Inn & Suites
  East Beltline (3251 Deposit Dr NE), Country Inn & Suites Grand Rapids
  Airport (5399 28th St SE), and the current Clarion Inn & Suites Airport
  listing (4921 28th St SE).
- Drury and Choice property pages establish Drury Inn & Suites Grand Rapids
  (5175 28th St SE) and Rodeway Inn & Suites Grand Rapids Southeast (4855
  28th St SE).

## Closure status at checkpoint

The discovery is additive and the 56-row census remains intact pending builder
regeneration. Major destination and chain locators continue to expose partial,
dynamic inventories. The pass cannot yet issue `CENSUS_COMPLETE`.
