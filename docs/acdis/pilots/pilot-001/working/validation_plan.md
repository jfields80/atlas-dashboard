# Pilot-001 Validation Plan

Primary decision:
PROCEED TO VALIDATION

Scope constraint:
- This plan authorizes manual validation only. It does not authorize product implementation.

Narrow service scope:
- Front brake pad and rotor replacement for the front axle only.

Requests involving rear brakes, calipers, brake-fluid service, diagnostics, or other repairs are outside this initial validation and must not be normalized into the pilot comparison.

Explicit exclusions:
- caliper replacement
- brake-fluid service
- rear-brake work
- diagnostic work
- unrelated repairs
- binding price guarantees

## Gate sequence

1. Gate 1 - Shop Supply Test must pass before any consumer acquisition.
2. Gate 2 - Consumer Demand Test starts only if Gate 1 passes.

## Gate 1 - Shop Supply Test

Objective:
Determine whether shops will provide comparable manual responses.

Recruitment target:
- 3 to 5 Columbus-area repair shops

Integration constraint:
- No software integration required.

Standard shop-response fields:
- shop name
- vehicle year, make, model
- service scope confirmation: front brake pads and rotors, front axle only
- labor amount
- parts amount
- parts brand or quality tier
- taxes and additional fees
- total estimated price
- warranty
- earliest appointment
- quote expiration
- exclusions and assumptions
- whether inspection could change the price

Outreach method:
- Manual email and/or phone outreach using one standardized script.

Participation script:
- Briefly explain pilot purpose, one narrow brake scope, required fields, response window, and non-binding nature of pilot outputs.

Response template:
- Single structured form (spreadsheet row or plain text template) matching required fields above.

Success criteria:
- At least 3 shops agree to participate.
- At least 2 comparable complete responses can be obtained for the same standardized request scope.
- Field completeness reaches operator-defined minimum threshold.

Failure criteria:
- Fewer than 3 participating shops.
- Responses are too incomplete or inconsistent for side-by-side comparison.
- Response latency consistently exceeds usefulness threshold for pilot operations.

Maximum outreach count:
- OPERATOR DECISION REQUIRED

Maximum test duration:
- OPERATOR DECISION REQUIRED

Stop conditions:
- Outreach cap reached without minimum participation.
- Time cap reached without minimum comparable responses.
- Responses contain unacceptable ambiguity that cannot be normalized honestly.

## Gate 2 - Consumer Demand Test

Objective:
Test whether consumers submit a qualified request and value a manually prepared comparison.

Required intake fields:
- ZIP code
- vehicle year
- make
- model
- mileage
- confirmation that the request is for front brake pads and rotors on the front axle
- known symptoms
- urgency
- preferred contact method
- permission to contact participating shops

One explicit traffic source:
- OPERATOR DECISION REQUIRED (single source only)

Maximum acquisition budget:
- OPERATOR DECISION REQUIRED

Test duration:
- OPERATOR DECISION REQUIRED

Qualified-submission definition:
- Submission contains all required intake fields and explicit permission to contact participating shops.

Comparison-delivery process:
- Operator sends standardized request to participating shops.
- Operator normalizes received responses into a side-by-side comparison table.
- Operator returns comparison to consumer with assumptions/exclusions clearly labeled.

Response-time measurement:
- Track timestamps for intake received, shop outreach sent, first response received, and final comparison delivered.

Consumer follow-up questions:
- Was the comparison understandable?
- Was it fast enough to be useful?
- Did it influence your next step?
- What key information was missing?

Success metrics:
- qualified submissions count
- percent of submissions receiving at least two comparable responses
- median time to comparison delivery
- consumer-reported usefulness of delivered comparison

Failure metrics:
- low qualified-submission volume relative to operator threshold
- low two-response completion rate
- high delivery time relative to usefulness threshold
- low consumer-reported usefulness

Privacy and consent requirements:
- collect only required intake fields
- explicit consent before contacting shops on consumer behalf
- no unnecessary personal data collection
- retain pilot records only as long as needed for evaluation

Stop conditions:
- budget cap reached without sufficient qualified signal
- time cap reached without sufficient qualified signal
- operational burden exceeds operator capacity
- consumer complaints indicate unclear consent or data handling

## Evidence language guardrails

When summarizing competitor evidence:
- Use NO only when absence was directly observed on an accessible page.
- Use UNKNOWN when evidence was not established.
- Use BLOCKED when access prevented observation.
- Do not convert non-observation into absence.

## What must not be automated yet

- estimator engine
- automated pricing model
- marketplace matching/routing logic
- automatic lead routing
- appointment integration
- crawler or scraping automation
- ranking/scoring system
- broad production directory implementation

## Operator decisions still required

- max outreach count for Gate 1
- max Gate 1 duration
- explicit single traffic source for Gate 2
- max Gate 2 acquisition budget
- max Gate 2 duration
- quantitative thresholds for pass/fail on qualified demand and response-time usefulness
