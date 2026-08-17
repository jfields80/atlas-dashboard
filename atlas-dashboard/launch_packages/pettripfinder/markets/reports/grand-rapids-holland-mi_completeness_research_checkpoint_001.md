# Grand Rapids--Holland census completeness: discovery checkpoint 001

As of 2026-08-16, the Phase-1 32-row census is being independently challenged.
This is discovery provenance only. No pet-policy content was collected or used.

## Completed official source families (all PARTIAL)

| Source family | Official source | Outcome |
| --- | --- | --- |
| Hilton | `hilton.com/en/locations/usa/michigan/grand-rapids/` | The locator reports 11 Grand Rapids hotels and exposes in-scope properties absent from Phase 1, including Canopy Grand Rapids Downtown, Embassy Suites Grand Rapids Downtown, Hampton Inn & Suites Grand Rapids Downtown, Hampton Inn Grand Rapids-North, Home2 Suites Grand Rapids North, Spark by Hilton Walker Grand Rapids North, and Home2 Suites Grand Rapids Northeast. Its airport and Holland flag locators also expose Hampton Inn & Suites Grand Rapids Airport 28th Street and Hampton Inn Holland. |
| Marriott | `marriott.com/en-us/destinations/united-states/michigan/grand-rapids.mi` | The destination inventory exposes absent in-scope properties including Courtyard Grand Rapids Downtown, SpringHill Suites Grand Rapids North, Residence Inn Grand Rapids West, TownePlace Suites Grand Rapids Airport Southeast, and Sheraton Grand Rapids Airport Hotel. |
| IHG | `ihg.com/grand-rapids-michigan` | The inventory exposes absent in-scope properties including Holiday Inn Express & Suites Grand Rapids-North, Holiday Inn Grand Rapids North - Walker, Staybridge Suites Grand Rapids SW - Grandville, Holiday Inn Express Grand Rapids SW, Holiday Inn Express & Suites Grand Rapids South - Wyoming, Holiday Inn Express & Suites Grand Rapids - Airport North, Candlewood Suites Grand Rapids Airport, and Staybridge Suites Grand Rapids South. |
| Choice | `choicehotels.com/michigan/grand-rapids/hotels` | The official locator reports 24 nearby hotels and exposes Comfort Suites Grand Rapids North, absent from Phase 1. |
| Hyatt | `hyatt.com/hyatt-place/en-US/grrzd-hyatt-place-grand-rapids-downtown` | Confirms Hyatt Place Grand Rapids/Downtown at 140 Ottawa Ave NW, Grand Rapids, MI 49503, absent from Phase 1. |
| Wyndham | `wyndhamhotels.com` property and flag-location pages | Exposes absent in-scope Travelodge by Wyndham Grand Rapids North (777 Three Mile Rd NW), Days Inn & Suites by Wyndham Grand Rapids Near Downtown, Hawthorn Suites by Wyndham Grand Rapids, AmericInn by Wyndham Grand Rapids Airport North, and AmericInn by Wyndham Holland MI. It also corroborates the existing Wyndham Garden Grand Rapids Airport. |

The source families are deliberately marked PARTIAL: locator pagination, date-dependent inventory, and several other brand families remain to be audited. This checkpoint establishes a material, additive gap; it is not a completeness finding.

## Follow-on durable checks

- Sonesta's Michigan inventory confirms Sonesta Hotel Grand Rapids Airport at
  3333 28th Street SE.  The Gerald R. Ford International Airport ground
  transportation page independently names several shuttle hotels.  Its names
  are treated as leads because some are legacy flags rather than present-day
  identity bindings.
- Best Western yielded boundary corroboration for Saugatuck and Grand Haven,
  not a basis to extend this market.  Red Roof, Extended Stay America, and
  Motel 6 / Studio 6 searches did not surface a new, address-bound in-scope
  first-party property in this pass.  Their absence is not a completeness
  claim.
- The deterministic `*_census_completeness_001.json` report and the
  second-pass candidate ledger are the current machine-readable continuation
  checkpoint.  The resulting verdict is `CENSUS_STILL_INCOMPLETE`.
