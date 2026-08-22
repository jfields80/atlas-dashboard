# Milwaukee full-market closure -- PTF-MILWAUKEE-IDENTITY-RESOLUTION-AND-FULL-CLOSURE-038

Every one of the market's 133 active-eligible properties sits in exactly one terminal disposition below, and the whole 147-property census reconciles beneath that. Nothing was published, nothing was deployed, and no provider was called.

## Active-eligible dispositions

| disposition | rows |
| --- | ---: |
| AUTHORITY_PET_FRIENDLY | 70 |
| AUTHORITY_VERIFIED_NO_PETS | 26 |
| HELD_REVIEW | 7 |
| IDENTITY_UNRESOLVED | 2 |
| ACCESS_UNRESOLVED | 4 |
| POLICY_NOT_FOUND | 4 |
| INSUFFICIENT_EVIDENCE | 7 |
| SCHEMA_UNREPRESENTABLE | 12 |
| SOURCE_CONFLICT | 1 |
| **total** | **133** |

## The rest of the census

| census state | rows | why |
| --- | ---: | --- |
| CENSUS_REVIEW | 3 | the census flagged this row for review: it may not be a lodging property in this market at all |
| IDENTITY_UNRESOLVED | 3 | the identity itself is unsettled -- the census cannot say which property this is |
| NO_OFFICIAL_URL | 8 | no first-party page has been bound to this identity, so there is nothing to read |
| **total** | **14** | |

133 active eligible + 14 other = **147**.

## Outside authority

| property | disposition | recovery class |
| --- | --- | --- |
| Brewhouse Inn & Suites | ACCESS_UNRESOLVED | RECOVERABLE_LOW_COST |
| Chalet Motel of Mequon | ACCESS_UNRESOLVED | FINAL_ACCESS_LIMITATION |
| Drury Plaza Hotel Milwaukee Downtown | ACCESS_UNRESOLVED | RECOVERABLE_LOW_COST |
| Dubbel Dutch Hotel | ACCESS_UNRESOLVED | RECOVERABLE_LOW_COST |
| Country Inn & Suites by Radisson, Brown Deer - Milwaukee North | HELD_REVIEW | RECOVERABLE_NO_PROVIDER_CALL |
| Country Inn & Suites by Radisson, Milwaukee West (Brookfield), WI | HELD_REVIEW | RECOVERABLE_NO_PROVIDER_CALL |
| Econo Lodge Milwaukee Airport | HELD_REVIEW | RECOVERABLE_NO_PROVIDER_CALL |
| Hyatt Regency Milwaukee | HELD_REVIEW | FINAL_SOURCE_LIMITATION |
| Knickerbocker on the Lake | HELD_REVIEW | FINAL_IDENTITY_LIMITATION |
| Saint Kate - The Arts Hotel | HELD_REVIEW | RECOVERABLE_NO_PROVIDER_CALL |
| The Iron Horse Hotel | HELD_REVIEW | FINAL_IDENTITY_LIMITATION |
| County Clare Irish Inn & Pub | IDENTITY_UNRESOLVED | FINAL_IDENTITY_LIMITATION |
| The Plaza Hotel Milwaukee | IDENTITY_UNRESOLVED | FINAL_IDENTITY_LIMITATION |
| AmericInn by Wyndham Brookfield | INSUFFICIENT_EVIDENCE | FINAL_SOURCE_LIMITATION |
| Motel 6 Milwaukee, WI - Glendale | INSUFFICIENT_EVIDENCE | FINAL_SOURCE_LIMITATION |
| Motel 6 Oak Creek, WI | INSUFFICIENT_EVIDENCE | FINAL_SOURCE_LIMITATION |
| Red Roof Inn Milwaukee - Airport/ Oak Creek | INSUFFICIENT_EVIDENCE | FINAL_SOURCE_LIMITATION |
| Studio 6 Extended Stay Milwaukee Brookfield WI | INSUFFICIENT_EVIDENCE | FINAL_SOURCE_LIMITATION |
| Suburban Studios Milwaukee Airport | INSUFFICIENT_EVIDENCE | FINAL_SOURCE_LIMITATION |
| The Marc Hotel | INSUFFICIENT_EVIDENCE | FINAL_SOURCE_LIMITATION |
| Motel 6 Suites Milwaukee Brookfield, WI | POLICY_NOT_FOUND | FINAL_SOURCE_LIMITATION |
| Potawatomi Casino Hotel | POLICY_NOT_FOUND | FINAL_SOURCE_LIMITATION |
| Spark by Hilton Milwaukee Airport | POLICY_NOT_FOUND | FINAL_SOURCE_LIMITATION |
| The Clarke Hotel | POLICY_NOT_FOUND | FINAL_SOURCE_LIMITATION |
| Candlewood Suites Milwaukee Brown Deer | SCHEMA_UNREPRESENTABLE | FINAL_SCHEMA_LIMITATION |
| Comfort Suites Milwaukee Airport | SCHEMA_UNREPRESENTABLE | FINAL_SCHEMA_LIMITATION |
| Courtyard by Marriott Milwaukee Brookfield at Poplar Creek | SCHEMA_UNREPRESENTABLE | FINAL_SCHEMA_LIMITATION |
| Courtyard by Marriott Milwaukee Downtown | SCHEMA_UNREPRESENTABLE | FINAL_SCHEMA_LIMITATION |
| Crowne Plaza Milwaukee Airport | SCHEMA_UNREPRESENTABLE | FINAL_SCHEMA_LIMITATION |
| Hyatt Place Milwaukee Airport | SCHEMA_UNREPRESENTABLE | FINAL_SCHEMA_LIMITATION |
| Residence Inn by Marriott Milwaukee Brookfield at Poplar Creek | SCHEMA_UNREPRESENTABLE | FINAL_SCHEMA_LIMITATION |
| Sheraton Milwaukee Brookfield Hotel | SCHEMA_UNREPRESENTABLE | FINAL_SCHEMA_LIMITATION |
| Staybridge Suites Milwaukee Airport South | SCHEMA_UNREPRESENTABLE | FINAL_SCHEMA_LIMITATION |
| The Trade, Autograph Collection | SCHEMA_UNREPRESENTABLE | FINAL_SCHEMA_LIMITATION |
| Wildwood Lodge | SCHEMA_UNREPRESENTABLE | FINAL_SCHEMA_LIMITATION |
| WoodSpring Suites Milwaukee - Menomonee Falls | SCHEMA_UNREPRESENTABLE | FINAL_SCHEMA_LIMITATION |
| Country Inn & Suites by Radisson, Milwaukee Airport, WI | SOURCE_CONFLICT | FINAL_SOURCE_LIMITATION |

## New founder-review candidates (6)

Recovered at zero provider cost and **not approved**. 036's decisions do not reach a row the founder never saw.

* **Country Inn & Suites by Radisson, Brown Deer - Milwaukee North** -- {"pets_allowed": true, "pet_fee": 3000, "fee_currency": "USD", "fee_basis": "per_night", "fee_scope": "per_pet", "weight_limit": {"value": 65.0, "unit
  * captured by firecrawl-choice-validation-004, a run 025 classifies DECISION_TEST_ONLY and therefore excludes from the production store. The evidence is real and the capture is on disk; what it is NOT is a production observation, and that is stated here rather than smoothed over.
* **Country Inn & Suites by Radisson, Milwaukee West (Brookfield), WI** -- {"pets_allowed": true, "pet_fee": 10000, "fee_currency": "USD", "fee_basis": "per_stay", "fee_scope": "per_pet", "weight_limit": {"value": 50.0, "unit
  * captured by firecrawl-choice-validation-004, a run 025 classifies DECISION_TEST_ONLY and therefore excludes from the production store. The evidence is real and the capture is on disk; what it is NOT is a production observation, and that is stated here rather than smoothed over.
* **Econo Lodge Milwaukee Airport** -- {"pets_allowed": false, "service_animal_exception": "Pets Allowed: No General: Only service animals are permitted, free of charge."}
  * captured by choice-route-proof-006, a run 025 classifies DECISION_TEST_ONLY and therefore excludes from the production store. The evidence is real and the capture is on disk; what it is NOT is a production observation, and that is stated here rather than smoothed over.
* **Knickerbocker on the Lake** -- no proposed facts: the router declined the page on identity, so the founder reviews the quote itself (see below)
  * captured by the production run milwaukee-closure-038
* **Saint Kate - The Arts Hotel** -- {"pets_allowed": true, "pet_fee": 10000, "fee_currency": "USD", "fee_basis": "per_stay", "pet_count_limit": 2}
  * captured by the production run milwaukee-identity-027
* **The Iron Horse Hotel** -- no proposed facts: the router declined the page on identity, so the founder reviews the quote itself (see below)
  * captured by the production run milwaukee-closure-038

## The identity gate cannot bind a policy SUBPAGE

Two properties published their pet policy on their own site -- a `/faq` and a `/dogs/` page that discovery had found and no run had ever fetched. Both fetched cleanly. Both were declined.

A subpage carries the hotel's NAME in its title and nothing physical: no address, no telephone, no JSON-LD. The identity gate exists because a capture can land on the wrong property, and it asks for a physical agreement it cannot get from `/dogs/`. So a page on the registrable domain the census itself names -- the strongest binding an independent hotel has -- is refused for lacking a weaker one.

038 did not touch the gate. Weakening an identity rule inside a closure work order is how a market ends up publishing the wrong hotel, and the founder can bind an identity where a rule cannot. Both rows are candidates, both disclose the decline, and neither carries proposed facts:

* **Knickerbocker on the Lake** -- `https://www.knickerbockeronthelake.com/faq`: Smoking indoors will incur a $250 cleaning fee.&nbsp; Do you allow pets?&nbsp; Only ADA service animals are allowed. Una
* **The Iron Horse Hotel** -- `https://www.theironhorsehotel.com/dogs/`: BECUASE THEY'RE FAMILY Pet Fee A $100 per night dog fee applies to all overnight pet guests. This fee covers enhanced ro

Repairing the gate for the same-registrable-domain case is a work order of its own, with its own controls.


## One row where the store and the reader disagree

030 made the store a projection of the reader. 038 changed the reader, so `saint kate the arts hotel` now disagrees with its own store row -- and re-projecting is refused here, because it withdraws **16 of the founder's 98 decisions**, fifteen of them without changing a single fact. Their record hash covers a `reader_commit` stamp the projection re-derives on every run, so committing a reader change silently un-approves rows over a field that records when a page was read rather than what it says.

That is a governance defect and it belongs to the founder, not to a closure task. It is written down in `milwaukee-pending-store-projection-038.json` and a test refuses any stale row that is not named there.

## State

published 0 | deployed 0 | authority 70 pet-friendly + 26 verified no-pets, unchanged.

