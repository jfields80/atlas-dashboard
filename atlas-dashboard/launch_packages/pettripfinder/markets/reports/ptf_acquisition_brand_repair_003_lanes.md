# PTF-ACQUISITION-BRAND-REPAIR-003 -- two repaired lanes and two controls

Run `PTF-REPAIR-003`. US exit pin: **PASS**.

| Lane | Why | Provider | Fetch | Pub grade | Attempts | Avg s | Precision | Recall |
| --- | --- | --- | --- | --- | --- | --- | --- | --- |
| WYNDHAM | repair: reader | Bright Data Browser API | 5/5 | 5 | 5 | 93 | 100.0% | 100.0% |
| CHOICE | repair: provider | Bright Data Web Unlocker | 5/5 | 5 | 7 | 91 | 100.0% | 88.2% |
| HILTON | control: recall lift from the known table structure | Bright Data Browser API | 3/3 | 3 | 3 | 82 | 100.0% | 100.0% |
| MARRIOTT | control: prove no regression | Bright Data Browser API | 2/2 | 2 | 3 | 88 | 100.0% | 100.0% |

## Against the production targets

Targets: precision >= 95%, recall >= 85% on critical fields.

- **WYNDHAM**: precision 100.0%, recall 100.0% -> MEETS TARGET
- **CHOICE**: precision 100.0%, recall 88.2% -> MEETS TARGET

## Relationship to PTF-BRIGHTDATA-CROSS-BRAND-PILOT-002

Pilot-002's committed report was produced by the reader as it stood BEFORE this work order, and is left exactly as it was. Its numbers are the honest record of that run; the numbers here are the honest record of this one, against the same properties with the same benchmark. Nothing in pilot-002 was re-derived to flatter the repair.

| Lane | Pilot-002 | Repair-003 |
| --- | --- | --- |
| WYNDHAM | 5/5 fetched, 5% critical recall | 5/5 fetched, 100% recall |
| CHOICE | 0/5 fetched (14 ACCESS_DENIED) | 5/5 fetched via Web Unlocker, 88% recall |
| HILTON | 5/5 fetched, 56% recall | 3/3 fetched, 100% recall |
| MARRIOTT | 5/5 fetched, 100% recall | 2/2 fetched, 100% recall (control) |


## Properties

| Lane | Property | Provider | Outcome(s) | Critical | Grade |
| --- | --- | --- | --- | --- | --- |
| WYNDHAM | Days Inn by Wyndham Sidney | Bright Data Browser API | VALID | exact | PUBLICATION_GRADE_CONFIRMED |
| WYNDHAM | La Quinta Columbus West-Hilliard | Bright Data Browser API | VALID | exact | PUBLICATION_GRADE_CONFIRMED |
| WYNDHAM | La Quinta Inn & Suites by Wyndham Fairbo | Bright Data Browser API | VALID | exact | PUBLICATION_GRADE_CONFIRMED |
| WYNDHAM | La Quinta Inn & Suites by Wyndham Miamis | Bright Data Browser API | VALID | exact | PUBLICATION_GRADE_CONFIRMED |
| WYNDHAM | Microtel Inn & Suites North Canton | Bright Data Browser API | VALID | exact | PUBLICATION_GRADE_CONFIRMED |
| CHOICE | Cambria Columbus-Polaris | Bright Data Web Unlocker | ACCESS_DENIED, ACCESS_DENIED, VALID | exact | PUBLICATION_GRADE_CONFIRMED |
| CHOICE | Cambria Hotel Akron-Canton Airport | Bright Data Web Unlocker | VALID | exact | PUBLICATION_GRADE_CONFIRMED |
| CHOICE | Comfort Inn Canton | Bright Data Web Unlocker | VALID | exact | PUBLICATION_GRADE_CONFIRMED |
| CHOICE | Comfort Inn Mayfield Heights Cleveland E | Bright Data Web Unlocker | VALID | pet_count_limit, species_dogs, weight_limit_value | PUBLICATION_GRADE_CONFIRMED |
| CHOICE | Quality Inn & Suites Richfield | Bright Data Web Unlocker | VALID | exact | PUBLICATION_GRADE_CONFIRMED |
| HILTON | Hampton Inn by Hilton Dayton South | Bright Data Browser API | VALID | exact | PUBLICATION_GRADE_CONFIRMED |
| HILTON | Hampton Inn Dayton/Huber Heights | Bright Data Browser API | VALID | exact | PUBLICATION_GRADE_CONFIRMED |
| HILTON | Hampton Inn Springfield | Bright Data Browser API | VALID | exact | PUBLICATION_GRADE_CONFIRMED |
| MARRIOTT | AC Hotel Dayton | Bright Data Browser API | VALID | exact | PUBLICATION_GRADE_CONFIRMED |
| MARRIOTT | Aloft Columbus Westerville | Bright Data Browser API | UNHYDRATED, VALID | exact | PUBLICATION_GRADE_CONFIRMED |

## Authority

POLICY_AUTHORITY_CHANGED: NO  
EXCLUSIONS_CHANGED: NO  
SEED_CHANGED: NO  
APPROVALS_CHANGED: NO  
PARTITION_CHANGED: NO  
ROUTING_AUTHORITY_CHANGED: NO
