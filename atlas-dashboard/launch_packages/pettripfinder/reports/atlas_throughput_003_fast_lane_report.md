# ATLAS-THROUGHPUT-003 — FAST_DATA_ONLY_RELEASE lane report

Data: `atlas_throughput_003_fast_lane_report.json` (the pilot run), `atlas_throughput_003_validation_receipt_example.json`
(the P2 receipt), the committed package `launch_packages/pettripfinder/markets/packages/dayton-oh/pkg-dayton-oh-813f7f9f089b89c7.json` and receipt `launch_packages/pettripfinder/markets/receipts/dayton-oh/pkg-dayton-oh-813f7f9f089b89c7-324148f81b55bc50.json`.

## The lane

`scripts/pettripfinder/fast_release_lane.py` runs fifteen rules over a sealed package. Every rule is PASS,
FAIL or UNKNOWN; UNKNOWN ⇒ NOT ELIGIBLE. The changed market is built through the REAL per-market assembler
over a staged tree (`package_staging.py`); no unchanged market is rendered; the live release is read from the
deployed record, the global manifest and the deployment-state pin (`release_index.current_verified_live`),
which must agree (they do: deploy 6a9d33f5, 10 markets, 786 profiles, rollback 6a9ca921 with its own record
of 9 markets).

## Pilot P2 — dayton-oh withdrawal package: FAST_DATA_ONLY_RELEASE_ELIGIBLE = **YES** in **60.9 s**

The live Dayton authority minus the five records the first-party gate refuses (below), every consequence
declared: 4 profiles removed, 4 hotel routes + 2 corridor routes removed (two corridors fell below their
published minimum — the owning assignment rule decided, and an undeclared version of the same package FAILS
rule I on exactly those two routes), `expected_verified_no_pets_delta` −1, `removal_authority` named.

| rule | name | result | seconds | problems |
|---|---|---|---|---|
| A | package schema valid | PASS | 0.016 |  |
| B | identity valid | PASS | 0.084 |  |
| C | first-party policy binding valid | PASS | 0.138 |  |
| D | policy semantics valid | PASS | 0.0 |  |
| E | route references valid | PASS | 0.0 |  |
| F | market partition valid | PASS | 0.0 |  |
| G | proposed whole-release identity/route indexes contain no forbidden collision | PASS | 0.074 |  |
| H | every unrelated live market/member is preserved | PASS | 0.074 |  |
| I | every removal is explicitly intended | PASS | 0.074 |  |
| J | changed-market artifact builds successfully | PASS | 28.656 |  |
| K | changed-market output deterministic | PASS | 31.889 |  |
| L | package/artifact hashes internally consistent | PASS | 0.001 |  |
| M | required evidence freshness/revocation rules satisfied | PASS | 0.001 |  |
| N | rollback/current-live preservation metadata valid | PASS | 0.012 |  |
| O | paid acquisitions used by the package satisfy reservation provenance | PASS | 0.0 |  |

Determinism: input digest `sha256:a6ba205ac580b5ca`, output A `6340911b0605e4e2`, output B `6340911b0605e4e2`, BYTE_IDENTICAL; 4 cold builds executed, 0 reuse hits.
Global index: live `sha256:fbbda87df4a906a0`, proposed `sha256:ebd488c1cbb3d6df`. Peak working set of the lane process: 103.8 MB.

## Pilot P1 — dayton-oh frozen copy, zero delta: NOT ELIGIBLE (rule C) in 73.6 s

The live authority as a package. Rules A, B, D–O pass; rule C refuses five of 78 records under the owning
reader (`brightdata.policy_reading.parse`):

| record | class | cited words |
|---|---|---|
| staybridge suites miamisburg | QUOTE_NOT_OPERATIVE | a fee sentence cited as the acceptance ("Guests will be charged 50 per pet …") |
| the hotel at dayton south | AMENITY_CHIP_ONLY | "Pets Allowed" — the record's only evidence |
| holiday inn express and suites dayton huber heights | AMENITY_CHIP_ONLY | "Pets are welcome" — the record's only evidence |
| holiday inn express and suites washington court house | AMENITY_CHIP_ONLY | "Pets are welcome" — the record's only evidence |
| hotel versailles (no-pets) | STRUCTURED_NO_PETS_INSUFFICIENT | `"petsAllowed": false` — a machine field with no operative words |

These are live, published records. The broad suite passes them (H2: "nothing gates the build"); the fast lane
does not. Correcting them is an evidence re-capture (a data change), not a code change, and is out of 003's
scope (production authority change = 0).

## Pilot P3 — nashville-tn shadow (branch 4f3dd7b): the writer refuses the package

{"CENSUS_MISSING_REQUIRED": 2, "EVIDENCE_MISSING_REQUIRED": 233, "EXCLUSION_CONTRACT": 1, "MISSING_IDENTITY": 8, "POLICY_MISSING_REQUIRED": 2, "PUBLICATION_BLOCKED": 233, "UNRESOLVED_PROMOTED_CLEAN": 8}

Read: 84 of the 99 clean rows are attended captures with NO page hash (`document_sha256: ""`), so under
`contracts.evidence` they are not publication-grade; 8 clean rows carry an identity key that is an alias
rather than the proposed census's primary key; no record or exclusion was founder-reviewed (the branch was
never promoted); two `fee_cap` facts lack `qualifier_stated`; two census rows lack a city. Nothing here is a
writer defect — it is what promotion would have to resolve, found in 0.029 s instead of after a build.

## Pilot P4 — toledo-oh frozen copy (launch commit d335c50): the writer refuses the package

{"CENSUS_KEY_NAME_MISMATCH": 1, "CENSUS_MISSING_REQUIRED": 216, "EVIDENCE_BAD_ENUM": 7, "EVIDENCE_NOT_FIRST_PARTY": 7, "MISSING_IDENTITY": 1, "PARTITION_MISSING_REQUIRED": 28, "PUBLICATION_BLOCKED": 7, "UNRESOLVED_PROMOTED_CLEAN": 1}

Read under THIS tree's contracts: Toledo's committed census carries none of `slug`, `market_id`,
`identity_state`, `lodging_state` (216 issues over 54 rows); its partition's 28 non-terminal rows carry no
`next_action`; seven evidence entries declare `source_grade: PT1_PROPERTY`, which the evidence contract does
not know. The launched Toledo authority satisfies the contracts of its own commit, not the contracts here —
which is exactly the "package validated under a compatible schema" condition the order lists.

## Legacy facts the writer reports on the live markets (frozen copies, read only)

| market | what the owning contracts say |
|---|---|
| cleveland-akron-canton-oh | 5 routing records bind identities the census does not carry (ROUTE_IDENTITY_NOT_IN_CENSUS) |
| pittsburgh-pa | 15 records publish a `species` fact no evidence entry cites (PUBLICATION_BLOCKED); one same-premises pair unproven (Ace Hotel / The Maverick by Kasa); one record read from the brand domain where the census binds the property's own domain |
| indianapolis-in | 41 evidence entries carry no artifact hash and 50 records are publication-blocked; 13 same-premises pairs unproven or duplicate; census/partition reconcile 21/22 rows apart |
| cincinnati-oh | 33 records publication-blocked (uncited facts); 4 same-premises pairs unproven |
| louisville-ky | 66 published records whose partition state is not PUBLISHED_PET_FRIENDLY; 2 exclusions not in the census; partition 69/33 rows apart from the census |
| st-louis-mo | 119 published records in a partition that predates the promotion (AWAITING_FOUNDER_DECISION); 6 same-premises duplicates (a bare-brand row beside the full identity); 18 unproven pairs |
| milwaukee-wi | 100 published records whose partition state is not PUBLISHED_PET_FRIENDLY; 34 publication-blocked |
| grand-rapids-holland-mi | 10 routing records bind identities the census does not carry; 8 publication-blocked; 1 exclusion not in the census |
| detroit-ann-arbor-mi (registered, not live) | 3 same-premises pairs unproven; 1 dangling routing record |
| every live market | 15 published records declare an identity_key that is a bare brand token (tru ×3, hampton ×2, holiday inn express and suites ×2, ...) rather than the key of their name; the release index therefore keys profiles by ptf_identity_key(published name) and carries the declared key beside it |

Every one of these is a legacy failure touching identity, policy binding or release integrity. Under
Phase 13 they are NOT copied into the lane: a package for such a market is INELIGIBLE until the authority is
repaired by a data order. The broad suite is green on all of them today, which is the measurement 001 predicted.

## Index benchmark (O(data), no render)

| markets | participating | profiles | compose + compare s | digest s | total s |
|---|---|---|---|---|---|
| 11 | 10 | 786 | 0.0687 | 0.0295 | 0.0982 |
| 25 | 24 | 1964 | 0.1621 | 0.0563 | 0.2185 |
| 50 | 49 | 3848 | 0.314 | 0.1114 | 0.4255 |
| 100 | 99 | 7778 | 0.5759 | 0.2366 | 0.8126 |
| 200 | 199 | 15638 | 1.0498 | 0.493 | 1.5429 |
