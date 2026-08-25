# PTF-BRIGHTDATA-CROSS-BRAND-PILOT-002 -- Bright Data across six brand buckets

Run `PTF-BD-XBRAND-002`. US exit pin: **PASS** (3 of 3 sessions reported an exit country and all of them were 'us').

Benchmark: this repository's own founder-reviewed policy records and exclusion registries, read only after every artifact was on disk.

| Bucket | Fetch | Identity | Policy | Text | Critical | Pub grade | Fallback | Attempts | Avg s | Zone cost |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| MARRIOTT | 5/5 | 5 | 5 | 4 | 5 | 5 | 0 | 8 | 116 | $0.85 |
| HILTON | 5/5 | 5 | 5 | 5 | 0 | 5 | 0 | 5 | 87 | $0.71 |
| IHG | 4/5 | 4 | 4 | 4 | 1 | 4 | 1 | 7 | 124 | $2.71 |
| CHOICE | 0/5 | 0 | 0 | 0 | 0 | 0 | 5 | 15 | 206 | $0.23 |
| WYNDHAM | 5/5 | 5 | 5 | 0 | 0 | 5 | 0 | 6 | 94 | $0.43 |
| MIXED | 2/5 | 2 | 2 | 2 | 1 | 2 | 3 | 11 | 89 | $1.26 |

## Field-level precision and recall

The per-property column above is all-or-nothing: one field the reader did not find drops the whole property. These two numbers separate *wrong* from *not found*, which is the difference between a correctness problem and a coverage problem.

| Set | Matched | Mismatched | Not found | Precision | Recall |
| --- | --- | --- | --- | --- | --- |
| critical | 44 | 0 | 34 | 100.0% | 56.4% |
| extended | 2 | 0 | 32 | 100.0% | 5.9% |
| all | 46 | 0 | 66 | 100.0% | 41.1% |

## Adapter observations

What the ONE generic strategy actually did, per brand. An adapter is justified where this shows the generic path struggling, and is not where it shows the generic path working.

### MARRIOTT

- captured: 5 of 5
- locator strategies: {'pet_policy_heading_parent': 4, 'generic_signal_walk': 1}
- signal phrases matched: {'pet policy': 4, 'pets are welcome': 1}
- disclosure controls opened: {'button': 7, "[aria-expanded='false']": 1, "[class*='accordion'] button": 1}
- hydrated before the signal timeout: 5 of 5
- policy block size: 27-202 chars
- brand-generic blocks: 0
- identity binding: {'property_code': 5}
- property code in URL: 5 of 5
- parser patterns fired: {'count[0]': 3, 'labelled_row': 2, 'weight[0]': 3, 'welcome[0]': 3, 'refused[0]': 1, 'count[1]': 1, 'scoped_prose_charge': 1, 'weight[1]': 1, 'welcome[1]': 1}
- failure outcomes: {'ACCESS_DENIED': 3}

### HILTON

- captured: 5 of 5
- locator strategies: {'generic_signal_walk': 5}
- signal phrases matched: {'pets allowed': 5}
- disclosure controls opened: {'button': 5}
- hydrated before the signal timeout: 0 of 5
- policy block size: 148-179 chars
- brand-generic blocks: 0
- identity binding: {'property_code': 5}
- property code in URL: 5 of 5
- parser patterns fired: {'weight[2]': 2, 'welcome[1]': 5, 'count[1]': 1, 'scoped_prose_charge': 1}
- failure outcomes: none

### IHG

- captured: 4 of 5
- locator strategies: {'generic_signal_walk': 4}
- signal phrases matched: {'pet policy': 4}
- disclosure controls opened: {'button': 4, "[role='button']": 4}
- hydrated before the signal timeout: 3 of 4
- policy block size: 331-494 chars
- brand-generic blocks: 0
- identity binding: {'canonical_path_and_name': 4}
- property code in URL: 0 of 5
- parser patterns fired: {'count[2]': 2, 'welcome[1]': 4, 'weight[1]': 1}
- failure outcomes: {'POLICY_NOT_FOUND': 3}

### CHOICE

- captured: 0 of 5
- locator strategies: -
- signal phrases matched: -
- disclosure controls opened: none needed
- hydrated before the signal timeout: 0 of 0
- policy block size: None-None chars
- brand-generic blocks: 0
- identity binding: -
- property code in URL: 0 of 5
- parser patterns fired: -
- failure outcomes: {'ACCESS_DENIED': 14, 'NAVIGATION_FAILED': 1}

### WYNDHAM

- captured: 5 of 5
- locator strategies: {'generic_signal_walk': 5}
- signal phrases matched: {'pet friendly': 1, 'service animals': 4}
- disclosure controls opened: {'button': 5}
- hydrated before the signal timeout: 5 of 5
- policy block size: 23-1013 chars
- brand-generic blocks: 0
- identity binding: {'canonical_path_and_name': 5}
- property code in URL: 0 of 5
- parser patterns fired: {'welcome[3]': 1}
- failure outcomes: {'NAVIGATION_FAILED': 1}

### MIXED

- captured: 2 of 5
- locator strategies: {'generic_signal_walk': 2}
- signal phrases matched: {'pet fee': 1, 'pets allowed': 1}
- disclosure controls opened: {'button': 7, "[role='button']": 1}
- hydrated before the signal timeout: 2 of 2
- policy block size: 606-908 chars
- brand-generic blocks: 0
- identity binding: {'canonical_path_and_name': 2}
- property code in URL: 0 of 5
- parser patterns fired: {'welcome[1]': 2}
- failure outcomes: {'NAVIGATION_FAILED': 1, 'IDENTITY_MISMATCH': 5, 'POLICY_NOT_FOUND': 3}


## Properties

| Bucket | Property | Outcome(s) | Locator | Critical | Pub grade | Disposition |
| --- | --- | --- | --- | --- | --- | --- |
| MARRIOTT | AC Hotel Dayton | VALID | pet_policy_heading_parent | exact | PUBLICATION_GRADE_CONFIRMED | PUBLICATION_CANDIDATE |
| MARRIOTT | Aloft Columbus Westerville | ACCESS_DENIED, VALID | pet_policy_heading_parent | exact | PUBLICATION_GRADE_CONFIRMED | PUBLICATION_CANDIDATE |
| MARRIOTT | BLU-Tique, Akron, A Tribute Portfolio Hotel | ACCESS_DENIED, VALID | pet_policy_heading_parent | exact | PUBLICATION_GRADE_CONFIRMED | VERIFIED_NO_PETS_CANDIDATE |
| MARRIOTT | Le Meridien Columbus, The Joseph | VALID | generic_signal_walk | exact | PUBLICATION_GRADE_CONFIRMED | PUBLICATION_CANDIDATE |
| MARRIOTT | The Westin | ACCESS_DENIED, VALID | pet_policy_heading_parent | exact | PUBLICATION_GRADE_CONFIRMED | PUBLICATION_CANDIDATE |
| HILTON | Hampton Inn by Hilton Dayton South | VALID | generic_signal_walk | pet_count_limit, species_cats, species_dogs | PUBLICATION_GRADE_CONFIRMED | PUBLICATION_CANDIDATE |
| HILTON | Hampton Inn Dayton/Huber Heights | VALID | generic_signal_walk | pet_count_limit, species_cats, species_dogs, weight_limit_value | PUBLICATION_GRADE_CONFIRMED | PUBLICATION_CANDIDATE |
| HILTON | Hampton Inn Springfield | VALID | generic_signal_walk | pet_count_limit, species_cats, species_dogs | PUBLICATION_GRADE_CONFIRMED | PUBLICATION_CANDIDATE |
| HILTON | Hilton Garden Inn Columbus Easton | VALID | generic_signal_walk | species_cats, species_dogs, weight_limit_value | PUBLICATION_GRADE_CONFIRMED | PUBLICATION_CANDIDATE |
| HILTON | Hilton Garden Inn Dayton Beavercreek | VALID | generic_signal_walk | pet_count_limit, pet_fee_minor, species_cats, species_dogs, weight_limit_value | PUBLICATION_GRADE_CONFIRMED | PUBLICATION_CANDIDATE |
| IHG | Candlewood Suites Columbus - Grove City | VALID | generic_signal_walk | exact | PUBLICATION_GRADE_CONFIRMED | PUBLICATION_CANDIDATE |
| IHG | Hotel Indigo Cleveland-Beachwood | VALID | generic_signal_walk | fee_basis, pet_fee_minor, species_dogs | PUBLICATION_GRADE_CONFIRMED | PUBLICATION_CANDIDATE |
| IHG | Hotel Indigo Cleveland Downtown | VALID | generic_signal_walk | pet_count_limit, pet_fee_minor, species_dogs, weight_limit_value | PUBLICATION_GRADE_CONFIRMED | PUBLICATION_CANDIDATE |
| IHG | Hotel Indigo Pittsburgh East Liberty | VALID | generic_signal_walk | pet_count_limit, species_cats, species_dogs | PUBLICATION_GRADE_CONFIRMED | HOLD |
| IHG | Staybridge Suites Akron Stow Cuyahoga Falls | POLICY_NOT_FOUND, POLICY_NOT_FOUND, POLICY_NOT_FOUND | - | - | - | CLAUDE_FALLBACK_REQUIRED |
| CHOICE | Cambria Columbus-Polaris | ACCESS_DENIED, ACCESS_DENIED, ACCESS_DENIED | - | - | - | CLAUDE_FALLBACK_REQUIRED |
| CHOICE | Cambria Hotel Akron-Canton Airport | ACCESS_DENIED, ACCESS_DENIED, ACCESS_DENIED | - | - | - | CLAUDE_FALLBACK_REQUIRED |
| CHOICE | Comfort Inn Canton | ACCESS_DENIED, ACCESS_DENIED, ACCESS_DENIED | - | - | - | CLAUDE_FALLBACK_REQUIRED |
| CHOICE | Comfort Inn Mayfield Heights Cleveland East | ACCESS_DENIED, ACCESS_DENIED, ACCESS_DENIED | - | - | - | CLAUDE_FALLBACK_REQUIRED |
| CHOICE | Quality Inn & Suites Richfield | ACCESS_DENIED, ACCESS_DENIED, NAVIGATION_FAILED | - | - | - | CLAUDE_FALLBACK_REQUIRED |
| WYNDHAM | Days Inn by Wyndham Sidney | VALID | generic_signal_walk | fee_basis, fee_scope, pet_count_limit, pet_fee_minor, species_cats, species_dogs | PUBLICATION_GRADE_CONFIRMED | PUBLICATION_CANDIDATE |
| WYNDHAM | La Quinta Columbus West-Hilliard | NAVIGATION_FAILED, VALID | generic_signal_walk | fee_basis, fee_scope, pet_count_limit, pet_fee_minor, pets_allowed, species_dogs, weight_limit_value | PUBLICATION_GRADE_CONFIRMED | HOLD |
| WYNDHAM | La Quinta Inn & Suites by Wyndham Fairborn W | VALID | generic_signal_walk | fee_basis, fee_scope, pet_count_limit, pet_fee_minor, pets_allowed, species_cats, species_dogs, weight_limit_value | PUBLICATION_GRADE_CONFIRMED | HOLD |
| WYNDHAM | La Quinta Inn & Suites by Wyndham Miamisburg | VALID | generic_signal_walk | fee_basis, fee_scope, pet_count_limit, pet_fee_minor, pets_allowed, species_cats, species_dogs, weight_limit_value | PUBLICATION_GRADE_CONFIRMED | HOLD |
| WYNDHAM | Microtel Inn & Suites North Canton | VALID | generic_signal_walk | pets_allowed | PUBLICATION_GRADE_CONFIRMED | HOLD |
| MIXED | Extended Stay America Hotel Akron/Copley Eas | VALID | generic_signal_walk | pet_count_limit | PUBLICATION_GRADE_CONFIRMED | PUBLICATION_CANDIDATE |
| MIXED | 50 Lincoln Short North Bed and Breakfast | NAVIGATION_FAILED, IDENTITY_MISMATCH, IDENTITY_MISMATCH | - | - | - | CLAUDE_FALLBACK_REQUIRED |
| MIXED | Motel 6 Richfield | VALID | generic_signal_walk | exact | PUBLICATION_GRADE_CONFIRMED | PUBLICATION_CANDIDATE |
| MIXED | Red Roof Inn Middleburg Heights | IDENTITY_MISMATCH, IDENTITY_MISMATCH, IDENTITY_MISMATCH | - | - | - | CLAUDE_FALLBACK_REQUIRED |
| MIXED | Sonesta Simply Suites Dublin Columbus | POLICY_NOT_FOUND, POLICY_NOT_FOUND, POLICY_NOT_FOUND | - | - | - | CLAUDE_FALLBACK_REQUIRED |

## Authority

POLICY_AUTHORITY_CHANGED: NO  
EXCLUSIONS_CHANGED: NO  
SEED_CHANGED: NO  
APPROVALS_CHANGED: NO  
PARTITION_CHANGED: NO  
ROUTING_AUTHORITY_CHANGED: NO
