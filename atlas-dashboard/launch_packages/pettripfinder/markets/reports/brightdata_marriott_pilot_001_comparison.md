# PTF-BRIGHTDATA-MARRIOTT-PILOT-001 -- Bright Data vs. known PetTripFinder facts

Run `PTF-BD-MARRIOTT-PILOT-001-R2`. Capture engine: Bright Data Browser API driven by Playwright (chromium over CDP).

The benchmark column is what manual PTF work already established. It was read only after every artifact was on disk, and no capture value below was corrected, filled in, or nudged towards it.

| Property | Fetch | Identity | Policy | Text match | Critical fields | Publication grade | Disposition |
| --- | --- | --- | --- | --- | --- | --- | --- |
| AC Hotel Ann Arbor Downtown | 1/1 | confirmed | pet_policy_heading_parent | yes | exact | PUBLICATION_GRADE_CONFIRMED | PUBLICATION_CANDIDATE |
| Courtyard by Marriott Detroit Downtown | 2/2 | confirmed | pet_policy_heading_parent | yes | exact | PUBLICATION_GRADE_CONFIRMED | VERIFIED_NO_PETS_CANDIDATE |
| Courtyard by Marriott Detroit Dearborn | 1/1 | confirmed | pet_policy_heading_parent | yes | exact | PUBLICATION_GRADE_CONFIRMED | PUBLICATION_CANDIDATE |
| Detroit Marriott Livonia | FAILED (3 attempts) | - | - | - | - | - | CLAUDE_FALLBACK_REQUIRED |
| Detroit Metro Airport Marriott | 1/1 | confirmed | pet_policy_heading_parent | yes | exact | PUBLICATION_GRADE_CONFIRMED | PUBLICATION_CANDIDATE |

## Field-by-field

### AC Hotel Ann Arbor Downtown

| Field | Benchmark | Captured | Verdict |
| --- | --- | --- | --- |
| pets_allowed | True | True | MATCH |
| pet_fee_minor | 15000 | 15000 | MATCH |
| fee_basis | per_stay | per_stay | MATCH |
| weight_limit_lb | 50.0 | 50.0 | MATCH |
| pet_count_limit | 1 | 1 | MATCH |
| cleaning_fee_minor | None | None | BENCHMARK_SILENT |
| species_allowed | None | None | BENCHMARK_SILENT |
| cats_allowed | None | None | BENCHMARK_SILENT |

Policy quote (verbatim, contiguous in the saved page text):

> Pet Policy Pets Welcome Pet Fee Per Stay $150 Maximum Pet Weight 50lbs Maximum Number of Pets in Room 1 Non-Refundable Pet Fee Per Stay: $150.00 Maximum Pet Weight: 50.0lbs Maximum Number of Pets in Room: 1

### Courtyard by Marriott Detroit Downtown

| Field | Benchmark | Captured | Verdict |
| --- | --- | --- | --- |
| pets_allowed | False | False | MATCH |
| pet_fee_minor | None | None | BENCHMARK_SILENT |
| fee_basis | None | None | BENCHMARK_SILENT |
| weight_limit_lb | None | None | BENCHMARK_SILENT |
| pet_count_limit | None | None | BENCHMARK_SILENT |
| cleaning_fee_minor | None | None | BENCHMARK_SILENT |
| species_allowed | None | None | BENCHMARK_SILENT |
| cats_allowed | None | None | BENCHMARK_SILENT |

Policy quote (verbatim, contiguous in the saved page text):

> Pet Policy Pets Not Allowed

### Courtyard by Marriott Detroit Dearborn

| Field | Benchmark | Captured | Verdict |
| --- | --- | --- | --- |
| pets_allowed | True | True | MATCH |
| pet_fee_minor | 2000 | 2000 | MATCH |
| fee_basis | ABSENT (SOURCE_CONTRADICTORY) | ABSENT (SOURCE_CONTRADICTORY) | MATCH |
| weight_limit_lb | 35.0 | 35.0 | MATCH |
| pet_count_limit | 2 | 2 | MATCH |
| cleaning_fee_minor | 10000 | 10000 | MATCH |
| species_allowed | None | None | BENCHMARK_SILENT |
| cats_allowed | None | None | BENCHMARK_SILENT |

Withheld: `fee_basis` (SOURCE_CONTRADICTORY).

Policy quote (verbatim, contiguous in the saved page text):

> Pet Policy Pets Welcome Pet fee $20/day with $100/stay nonrefundable clean fee excludes Service Animals Non-Refundable Pet Fee Per Stay: $100.00 Non-Refundable Pet Fee Per Night: $20.00 Maximum Pet Weight: 35.0lbs Maximum Number of Pets in Room: 2

### Detroit Marriott Livonia

Capture failed after 3 attempts; nothing to compare.

| Attempt | Outcome | Title seen | Final URL | Body chars |
| --- | --- | --- | --- | --- |
| 1 | ACCESS_DENIED | Access Denied | https://www.marriott.com/en-us/hotels/dtwli-detroit-marriott-livonia/overview/ | 249 |
| 2 | ACCESS_DENIED | Access Denied | https://www.marriott.com/en-us/hotels/dtwli-detroit-marriott-livonia/overview/ | 249 |
| 3 | UNEXPECTED_PAGE | Hoteles Marriott Bonvoy | Reserva directamente y obtén tarifas exclusi | https://www.marriott.com/es/default.mi | 4146 |

Claude's attended browser was NOT used: this pilot measures Bright Data standalone, so the fallback is reported rather than exercised.

### Detroit Metro Airport Marriott

| Field | Benchmark | Captured | Verdict |
| --- | --- | --- | --- |
| pets_allowed | True | True | MATCH |
| pet_fee_minor | 5000 | 5000 | MATCH |
| fee_basis | per_stay | per_stay | MATCH |
| weight_limit_lb | 45.0 | 45.0 | MATCH |
| pet_count_limit | 2 | 2 | MATCH |
| cleaning_fee_minor | None | None | BENCHMARK_SILENT |
| species_allowed | None | None | BENCHMARK_SILENT |
| cats_allowed | None | None | BENCHMARK_SILENT |

Policy quote (verbatim, contiguous in the saved page text):

> Pet Policy Pets Welcome Non-Refundable Pet Fee Per Stay: $50.00 Maximum Pet Weight: 45.0lbs Maximum Number of Pets in Room: 2


## Harness notes

Defects found in this repository's own instrumentation, recorded so the acquisition measurement is not credited or blamed for them:

- Run 1 (2026-08-18, 5/5 captured, 6 attempts) lost one Bright Data session to a HARNESS failure, not a Bright Data block: 'Page.screenshot: Timeout 30000ms exceeded ... waiting for fonts to load' on Courtyard Detroit Downtown. Playwright's 30 s default is not enough for a full-page capture of a Marriott overview page over a remote browser. Screenshots now carry their own 90000 ms budget.
- Run 1 also recorded a policy-section screenshot for Courtyard Detroit Dearborn that was a uniform white rectangle: the page had not scrolled, the hotel-information section had mounted its DOM without painting, and the summary counted the FILE rather than the IMAGE. The capture now centres the block, waits for its bounding box to stop moving, checks the crop for a single flat colour, retakes once, and REFUSES to record a blank crop as an artifact.
- Both defects were in this repository's code. Neither was a refusal, a challenge, or a block by Marriott or by Bright Data.
- The metrics below were captured with an UNPINNED Bright Data exit. PTF-BRIGHTDATA-CROSS-BRAND-PILOT-002 made US exit geography the default for every session in this package, so re-running this pilot today will not reproduce the one failure it recorded -- that failure was a non-US exit serving marriott.com/es/default.mi, and it is the reason the pin exists.

## Contract integration gaps

**GAP-01-NO-MACHINE-SCREENSHOT-KIND** -- a machine-captured screenshot has no lawful artifact_kind

enums.ARTIFACT_KINDS offers ['rendered_html', 'operator_screenshot', 'pdf']. The only screenshot member is 'operator_screenshot', whose meaning in this repository is an image a human took of a page they were looking at. A Bright Data screenshot is of the same page and by a different witness, and calling it an operator screenshot would misstate who took it. So this pilot files NO screenshot as evidence: full-page.png and policy-section.png are persisted, hashed and referenced, but they carry no artifact_class and back no fact.

_Contract: `scripts/pettripfinder/contracts/enums.py ARTIFACT_KINDS`. Blocks publication: False._

**GAP-02-NO-MANAGED-BROWSER-CAPTURE-METHOD** -- the capture-method vocabulary has no term for an unattended managed browser

policy_observation.CAPTURE_METHODS is ['deterministic_fetch', 'browser_assisted', 'human_manual', 'phone_contact']. This pilot records 'browser_assisted' because it is the nearest member, but the plain meaning of that term in this repository is an OPERATOR driving a browser -- the attended-capture path several markets depend on. A third-party managed browser has different failure modes (a silently rotated exit IP, a session that renders a shell) and a reviewer cannot currently tell the two apart from a committed record.

_Contract: `scripts/pettripfinder/policy/policy_observation.py CAPTURE_METHODS`. Blocks publication: False._

**GAP-03-NO-CAPTURE-ENGINE-BINDING** -- an evidence entry does not record what fetched the page

evidence.PUBLICATION_GRADE_REQUIRED is ['evidence_ref', 'field', 'quote', 'source_url', 'source_grade', 'artifact_class', 'artifact_sha256', 'artifact_kind', 'captured_at']. It binds the SOURCE and the ARTIFACT and never the ACQUISITION PATH, so a record cannot say whether its page witness came from an operator's own browser, a deterministic fetch, or a third-party managed browser. That distinction is exactly what this pilot exists to evaluate, and today it survives only in the free-text capture_method field, which nothing validates.

_Contract: `scripts/pettripfinder/contracts/evidence.py PUBLICATION_GRADE_REQUIRED`. Blocks publication: False._


## Authority

POLICY_AUTHORITY_CHANGED: NO  
EXCLUSIONS_CHANGED: NO  
SEED_AUTHORITY_CHANGED: NO  
FOUNDER_APPROVALS_CHANGED: NO  
PARTITION_CHANGED: NO  
ROUTING_AUTHORITY_CHANGED: NO
