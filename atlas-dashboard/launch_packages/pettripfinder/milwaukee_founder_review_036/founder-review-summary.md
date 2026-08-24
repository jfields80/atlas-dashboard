# Milwaukee founder review -- PTF-MILWAUKEE-FIRST-AUTHORITY-AND-FOUNDER-REVIEW-036

**Status: AWAITING_FOUNDER_DECISION. Nothing here is approved.**

98 candidates: 72 readable policies and 26 captured refusals.

| proposed | rows |
| --- | ---: |
| APPROVE | 70 |
| APPROVE_REFUSAL | 23 |
| NEEDS_INDIVIDUAL_REVIEW | 5 |

## What a decision means

`APPROVE` admits a pet policy to Milwaukee authority. `APPROVE_REFUSAL` admits a verified no-pets finding, which answers a traveller's question as usefully as an allowance does. A proposed decision is a recommendation from a machine that checked identity, evidence, schema validity and withholding; it is not an approval and cannot become one without an explicit written decision.

## What was checked before anything was proposed

* the identity resolves in the 147-property census exactly once
* the canonical policy block is on disk and its document hash is recorded
* the allowance or the refusal is supported by a quote
* every structured fee validates under schema 1.2 as it stands
* no field is asserted and withheld at the same time
* a service-animal statement is never read as a pet permission

Unknown is not a failure. A policy that states no weight limit and no breed rule is still a policy, and no value is ever invented to fill a gap.

## Prices stated as ladders

20 rows price by stay length. The ladder IS the price: no single amount is asserted for them, and the CSV spells every band out rather than collapsing it.

## The 5 rows that need your eyes, not a checkbox

Each of these is mechanically clean. What is left is a judgement, and the machine states the question rather than answering it.

* **Hyatt Regency Milwaukee** (FOUNDER_REVIEW_READY)
  * a pet policy is published with no stated allowance (pets_allowed SOURCE_SILENT); whether a priced policy may be listed as pet-friendly is a founder's call, not a reader's
* **Saint Kate - The Arts Hotel** (FOUNDER_REVIEW_READY)
  * a pet policy is published with no stated allowance (pets_allowed SOURCE_CONTRADICTORY); whether a priced policy may be listed as pet-friendly is a founder's call, not a reader's
* **Baymont by Wyndham Mequon Milwaukee Area** (REFUSAL_FOUNDER_REVIEW)
  * the refusal rests on 'no other pets', which is a contrast rather than a statement -- read in full: 'ADA Defined service animals are welcome at this hotel. Sorry no other pets are allowed.'
* **Days Inn by Wyndham West Allis/Milwaukee** (REFUSAL_FOUNDER_REVIEW)
  * the refusal rests on 'no other pets', which is a contrast rather than a statement -- read in full: 'ADA defined service animals are welcome at this hotel. Sorry no other pets are allowed.'
* **Super 8 by Wyndham Milwaukee Airport** (REFUSAL_FOUNDER_REVIEW)
  * the refusal rests on 'no other pets', which is a contrast rather than a statement -- read in full: 'ADA defined service animals are welcome at this hotel. Sorry no other pets are allowed.'

## Not in this package

| state | rows | why |
| --- | ---: | --- |
| HELD_SCHEMA_CANNOT_REPRESENT | 12 | the source states a price the schema cannot hold |
| HELD_INSUFFICIENT_EVIDENCE | 7 | the surface carried no term worth publishing |
| active unresolved | 16 | no store row exists; there is nothing to approve |

## Milwaukee

census 147 | active eligible 133 | observed 117 | candidates 98 | founder approved 0 | authority 0 | deployed 0

