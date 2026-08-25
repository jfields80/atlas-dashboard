# PTF-ACQUISITION-ROUTER-001 -- routing smoke test

Run `PTF-ROUTER-001`. US exit pin: **PASS**. Providers implemented: brightdata_browser, brightdata_web_unlocker.

This measures ROUTING, not facts. The twelve properties come from pilot-002's own sample and their policies were established by earlier runs; what is new is whether the orchestrator picks the right lane, refuses the lane known not to work, stops escalating when escalation is waste, and accounts for what it spent.

| Lane | Provider | Reader | Route ok | Fetch | Pub grade | Attempts | Browser calls | Precision | Recall | Avg s |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| MARRIOTT | brightdata_browser | marriott | 2/2 | 2/2 | 2 | 2 | 2 | 100.0% | 100.0% | 59 |
| HILTON | brightdata_browser | hilton_competing | 2/2 | 2/2 | 2 | 2 | 2 | 100.0% | 100.0% | 96 |
| IHG | brightdata_browser | ihg | 2/2 | 2/2 | 2 | 2 | 2 | 100.0% | 71.4% | 91 |
| CHOICE | brightdata_web_unlocker | choice_static | 2/2 | 2/2 | 2 | 2 | 0 | 100.0% | 100.0% | 41 |
| WYNDHAM | brightdata_browser | wyndham | 2/2 | 2/2 | 2 | 2 | 2 | 100.0% | 100.0% | 83 |
| MIXED | brightdata_browser | generic | 2/2 | 1/2 | 1 | 2 | 2 | 100.0% | 50.0% | 61 |

## Gates

- PASS **route_selection_accuracy_12_of_12**
- PASS **wrong_provider_default_zero**
- PASS **false_identity_acceptance_zero**
- PASS **false_verified_no_pets_zero**
- PASS **unsupported_inference_zero**
- PASS **publication_grade_among_valid_100**
- PASS **choice_browser_default_calls_zero**
- PASS **journal_reconciliation**
- PASS **wyndham_recall_ge_90**
- PASS **marriott_recall_ge_95**
- PASS **hilton_recall_ge_90**

## Cost

| Metric | Router | Pilot-002 baseline |
| --- | --- | --- |
| per property attempted | $0.2175 | $0.2400 |
| per property acquired | $0.2373 | — |
| per accepted record | $0.2373 | — |
| total | $2.6100 | — |


## Properties

| Lane | Property | Route | Providers tried | State | Stopped because |
| --- | --- | --- | --- | --- | --- |
| MARRIOTT | AC Hotel Dayton | brightdata_browser / marriott | brightdata_browser | ACQUIRED_PUBLICATION_GRADE |  |
| MARRIOTT | Aloft Columbus Westerville | brightdata_browser / marriott | brightdata_browser | ACQUIRED_PUBLICATION_GRADE |  |
| HILTON | Hampton Inn by Hilton Dayton South | brightdata_browser / hilton_competing | brightdata_browser | ACQUIRED_PUBLICATION_GRADE |  |
| HILTON | Hampton Inn Dayton/Huber Heights | brightdata_browser / hilton_competing | brightdata_browser | ACQUIRED_PUBLICATION_GRADE |  |
| IHG | Candlewood Suites Columbus - Grove Cit | brightdata_browser / ihg | brightdata_browser | ACQUIRED_PUBLICATION_GRADE |  |
| IHG | Hotel Indigo Cleveland-Beachwood | brightdata_browser / ihg | brightdata_browser | ACQUIRED_PUBLICATION_GRADE |  |
| CHOICE | Cambria Columbus-Polaris | brightdata_web_unlocker / choice_static | brightdata_web_unlocker | ACQUIRED_PUBLICATION_GRADE |  |
| CHOICE | Cambria Hotel Akron-Canton Airport | brightdata_web_unlocker / choice_static | brightdata_web_unlocker | ACQUIRED_PUBLICATION_GRADE |  |
| WYNDHAM | Days Inn by Wyndham Sidney | brightdata_browser / wyndham | brightdata_browser | ACQUIRED_PUBLICATION_GRADE |  |
| WYNDHAM | La Quinta Columbus West-Hilliard | brightdata_browser / wyndham | brightdata_browser | ACQUIRED_PUBLICATION_GRADE |  |
| MIXED | Extended Stay America Hotel Akron/Copl | brightdata_browser / generic | brightdata_browser | ACQUIRED_PUBLICATION_GRADE |  |
| MIXED | 50 Lincoln Short North Bed and Breakfa | brightdata_browser / generic | brightdata_browser | IDENTITY_REVIEW | IDENTITY_MISMATCH is terminal: the surface answered and a different pr |

## Contract gaps (documented, unpatched)

- **GAP-01-NO-MACHINE-SCREENSHOT-KIND** — a machine-captured screenshot has no lawful artifact_kind
- **GAP-02-NO-MANAGED-BROWSER-CAPTURE-METHOD** — the capture-method vocabulary has no term for an unattended managed browser
- **GAP-03-NO-CAPTURE-ENGINE-BINDING** — an evidence entry does not record what fetched the page

## Authority

POLICY_AUTHORITY_CHANGED: NO  
EXCLUSIONS_CHANGED: NO  
SEEDS_CHANGED: NO  
APPROVALS_CHANGED: NO  
ROUTING_AUTHORITY_CHANGED: NO  
PARTITION_CHANGED: NO
