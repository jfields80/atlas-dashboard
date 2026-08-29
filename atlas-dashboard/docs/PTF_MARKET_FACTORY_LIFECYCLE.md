# PetTripFinder market factory — the default lifecycle

**Authority:** PTF-MARKET-FACTORY-COVERAGE-HARDENING-001 (2026-08-25).
**Entrypoint:** `scripts/pettripfinder/market_factory_cli.py`.

St. Louis (PTF-ST-LOUIS-MARKET-001/002) and Louisville (PTF-LOUISVILLE-002/003)
were both built on the generic path and both needed a separate coverage-expansion
work order after their first acquisition pass. Every tool that work order used
already existed; what did not exist was anything that sequenced them, gated the
paid pass on them, or asked "is there anything left the factory can do for free?"
before a founder was handed a packet. This document records what the hardened
factory does by default so that the next market needs only a market id, a
geography contract, and a budget authorisation.

## The lifecycle

| # | Phase | Tool | Spends? |
|---|---|---|---|
| 1 | `census` | `market_census_cli` over persisted discovery candidates | no |
| 2 | `routing` | `acquisition/market_routing` over the census | no |
| 3 | `zero_cost_url_recovery` | `discovery/census_url_recovery` over the discovery cache (three keys, corroboration, unroutable URLs included) | no |
| 4 | `prior_build_reconciliation` | `census_url_recovery` over a prior census and its artifacts, when one exists | no |
| 5 | `reroute` | routing again with the recovered URLs layered over the census | no |
| 6 | `acquisition` | dry run → `cohort_cost_plan` → **gate** → `market_paid_acquisition` | **yes** |
| 7 | `declined_evidence_recovery` | `acquisition/zero_cost_recovery` over every run directory | no |
| 8 | `reroute_recovered` | URL recovery again over this build's own artifacts, then routing | no |
| 9 | `acquire_newly_routable` | the same paid machinery over what is left | **yes** |
| 10 | `alternate_lane_handling` | `acquisition/retry_policy` classification; a pass over rows with an untried approved lane | **yes** |
| 11 | `coverage_exhaustion` | `market_coverage_cli` → `ptf-market-coverage-completion/1.0` | no |
| 12 | `closure` | merge, observation store, partition, closure ledger; coverage re-evaluated | no |
| 13 | `founder_review_packet` | packet, machine review, duplicate scan; coverage finalised | no |
| 14 | `founder_review` | a human — refused until phase 13's coverage artifact says READY | no |

A phase recorded in the ledger (`<slug>_factory_ledger_<suffix>.json`) as
COMPLETED or SKIPPED is not run again. A phase whose predecessor is not satisfied
is not started. Every gate reads an artifact, never a flag.

## The three rules the hardening adds

**Zero-cost recovery is mandatory before paid acquisition.** Phase 6 refuses to
start unless the phase-4 URL-recovery artifact exists. Phase 9 additionally
refuses unless declined-evidence recovery ran over every run directory.

**No same-lane retry waste** (`acquisition/retry_policy.py`). A prior
access/navigation/unhydrated failure re-enters a paid cohort only on a different
approved lane (the row is started on that lane via a per-property registry
override), a changed source URL, a reader change that addresses the failure, or
an explicit, authored operator override. Otherwise the row is
`RETRY_REQUIRES_ALTERNATE_LANE` — suppressed, named, and never marked settled.

**No paid pass without a cost plan.** `market_paid_acquisition --cost-plan` is
mandatory for a spending run; the gate checks the plan's schema, its double-buy
proof, and that its cohort fingerprint matches the queue about to run. The plan
states expected Firecrawl credits, expected Bright Data cost, the vendor balance,
the authorised cap, the recommended cap, cumulative prior spend, and predicted
completion under the balance, in queue order.

## The coverage-completion contract

`contracts/coverage.py` — every census identity, by set, with one coverage state
and one next-state. Terminal next-states need a human, a new authorisation, a
registry change or a routing repair; factory next-states name a phase the
factory has not yet run for that identity. `READY_FOR_FOUNDER_REVIEW` is true
only when no identity carries a factory next-state, closure reconciles, and the
packet exists. It may be true with many unresolved identities. A market is
`FACTORY_COMPLETE` when READY is true and for no other reason.

## Running a new market

```
python scripts/pettripfinder/market_factory_cli.py \
  --market <id> --contract launch_packages/pettripfinder/markets/pending/<id>.json \
  --candidates data/discovery/<slug>/candidates/<id>_candidates.json \
  --discovery-cache data/discovery/<slug>/cache \
  --authorised-cap-usd 10 --work-order PTF-<MARKET>-001 --as-of <date> \
  --through founder_review
```

Without `--authorise-spend` the paid phases stop at their cost plan with status
`AWAITING_AUTHORISATION`; re-run with the flag once the plan has been read.
`--plan` prints the phases, their status and which may spend, and runs nothing.

## Re-censusing a registered market

**Authority:** PTF-PITTSBURGH-HARDENED-RECENSUS-001 (2026-08-25).

A live market has a census at `identity_census/<id>.json` whose count its
release contract pins, plus published authority in its shards. Re-running the
factory over it must treat all of that as **prior evidence, never the ceiling**
— and must not write a byte over any of it, because the founder has not decided
anything yet. Two things make that possible without a market-specific script:

* `--census-dir <dir>` — the factory builds and reads ITS census under that
  directory (`<dir>/<id>.json`). Every downstream reader accepts the same path
  through `--census` (`census_url_recovery`, `market_paid_acquisition`,
  `market_closure_cli`, `market_founder_review_cli`, `census_duplicate_scan`;
  `market_observation_store`, `founder_review_analysis` and
  `market_coverage_cli` already did), and the factory passes it to each of them.
  The convention is `identity_census/recensus/<id>.json`: beside the live
  census, invisible to anything that resolves a census by market id.
* `--prior-census <live census>` — the census phase folds the prior rows back
  in as discovery candidates (`market_census_cli --prior-census`, over
  `discovery/census_recandidacy`): observation carried, every verdict dropped,
  a prior row absorbed into the fresh sighting of the same street, and each
  absorption written to `<slug>_prior_census_absorptions_<suffix>.json`. The
  same path is then read by the URL-recovery phases as sightings.

```
python scripts/pettripfinder/discovery_cli.py run --market <id> --providers overpass \
  --categories hotel,motel --output-root data/discovery/<slug>_recensus_001 \
  --max-google-requests 0 --max-overpass-requests 40          # $0
python scripts/pettripfinder/market_factory_cli.py \
  --market <id> --contract launch_packages/pettripfinder/markets/<id>.json \
  --candidates data/discovery/<slug>_recensus_001/candidates/<id>_candidates.json \
  --discovery-cache data/discovery/<slug>_recensus_001/cache \
  --prior-census launch_packages/pettripfinder/identity_census/<id>.json \
  --prior-artifact 'launch_packages/pettripfinder/markets/reports/<slug>*' \
  --census-dir launch_packages/pettripfinder/identity_census/recensus \
  --suffix recensus_001 --authorised-cap-usd 10 --work-order <WO> --as-of <date> \
  --through founder_review
```

Promotion of the sandbox census and of any packet decision into the live
authority is a separate, founder-signed work order; this lifecycle stops at the
founder-review gate exactly as it does for a new market.

### When free discovery cannot finish

The census phase reads the discovery state first and refuses a partial census.
`FREE_DISCOVERY_RUNNABLE` is a run the factory owes. `WAITING_FOR_FREE_DISCOVERY`
is one of two things, and the state says which (`waiting_reason`): every
approved endpoint cooling down, or `FORWARD_PROGRESS_STALLED` — three resume
cycles that completed no cell. Neither is answered by retrying in a loop: an
outer supervisor cannot be paced by a breaker inside one process
(`docs/PTF_DISCOVERY_OVERPASS_RESILIENCE.md`, "What the first real outage
taught the breaker"). The answer is the local extract:

```
python scripts/pettripfinder/osm_extract_cli.py plan    --market <id>       # what is missing, offline
python scripts/pettripfinder/osm_extract_cli.py dry-run --market <id> --output-root data/discovery/<slug>_recensus_001
python scripts/pettripfinder/discovery_cli.py run --market <id> --providers overpass \
  --categories hotel,motel --output-root data/discovery/<slug>_recensus_001 \
  --max-google-requests 0 --max-overpass-requests 0 --resume \
  --osm-extract-index data/osm_extracts/<extract>.<id>.index.json                   # $0, 0 requests
```

The cells the public servers already answered stay exactly as cached; the rest
are answered from the index and carry `local_extract:<extract_id>` in their
provenance. The discovery state then reads EXHAUSTED and the census phase runs.
## Re-censusing a market that already has a census (PTF-INDIANAPOLIS-HARDENED-RECENSUS-002)

Indianapolis was the first REGISTERED market rebuilt on the generic path, and a
registered market has three bindings Louisville did not: `markets/<id>.json`, a
release contract in `deploy/netlify/release_contracts/` that pins
`identity_census/<id>.json` at an `expected_count`, and (for Indianapolis) a
policy package `published: true` in source. The generic tools read and write the
census by convention at `launch_packages/pettripfinder/identity_census/`, so a
rebuild on the generic path would have overwritten the pinned file -- and a
release contract that no longer matches its market makes `verify_all()` raise
for every market. Four things make a re-census safe:

1. **The census location is a run-level setting.** `census_location.py` resolves
   every generic tool's `CENSUS_DIR`; set
   `PTF_IDENTITY_CENSUS_DIR=launch_packages/pettripfinder/identity_census_proposed`
   for the whole run and the committed census is never touched. Promoting the
   proposed census over the committed one is a founder step, taken together with
   the release contract and the registration row it invalidates.
2. **Prior work is an INPUT.** `discovery/census_recandidacy` (now a command)
   projects the committed census back into candidates and merges them with fresh
   discovery, absorbing by street identity ONLY when the names are compatible --
   a dual-brand building is two hotels, a rebrand is a finding -- and taking the
   fuller prior name over a provider's bare brand, which is how identity keys
   collide. The census row carries `prior_census_identity_keys`,
   `name_before_recandidacy` and `street_shared_with`.
3. **Every prior row is classified once.** `discovery/prior_build_reconciliation`
   reports MATCHED_EXISTING / RENAMED_REBRANDED / DUPLICATE /
   OUT_OF_CURRENT_GEOGRAPHY / UNRESOLVED_IDENTITY for every prior row, plus what
   the prior build still offers (USEFUL_SOURCE_URL, USEFUL_POLICY_EVIDENCE,
   PRIOR_AUTHORITY_MATCH). Prior authority is reported, never carried.
4. **An interrupted paid pass resumes.** The cost plan now treats a key already
   in the run directory's journal as RESUMED, not bought twice, unless the pass
   runs with `--no-resume`; and a pass killed mid-run (journal, no report) is
   reported from its journal and registered before the next plan is built.
5. **The authorisation is for the work order.** The recommended cap can never
   exceed what earlier passes left of it (`cumulative_prior_spend`); an
   exhausted authorisation SKIPS the paid phase with its rows BUDGET_DEFERRED
   instead of running a pass under a fresh ceiling. Before this, the plan for
   pass 2 reported 8 cents remaining and recommended 1000.
6. **A budget stop stands behind a continuation pass.** The coverage builder
   reads EVERY pass report (`--pass-report`, oldest first): a STOPPED_* pass's
   deferrals stay BUDGET_DEFERRED until a later pass attempts them, and the
   factory re-runs declined-evidence recovery over every pass's run directory
   before judging coverage.

Also fixed on this work order, all generic: `census_projection` honours a
corridor's `explicit_hotel_ids` (five explicitly placed downtown hotels had been
rejected as out of market, with a reason about coordinates they did not have);
`census_url_recovery` reads the routing-shard shape (`hotel_ref.identity_key` +
`official_property_url`); `market_routing.classify_url_shape` calls a hotel
search (`find-hotels`, `hotel-search`, `?city=`) a BRAND_INDEX whatever else the
path carries; and `discovery_cli run --overpass-endpoint` (or
`$ATLAS_OVERPASS_ENDPOINT`) names the Overpass mirror explicitly when the public
default is down -- the client never falls back on its own.

```
python -m scripts.pettripfinder.discovery.census_recandidacy   --prior-census <committed census> --discovery-candidates <fresh candidates>   --observed-at <date> --work-order <wo> --out <merged candidates>
PTF_IDENTITY_CENSUS_DIR=launch_packages/pettripfinder/identity_census_proposed python scripts/pettripfinder/market_factory_cli.py --market <id>   --contract launch_packages/pettripfinder/markets/<id>.json   --candidates <merged candidates> --discovery-cache <cache>   --prior-census <committed census> --prior-artifact "<prior reports glob>" ...
python scripts/pettripfinder/discovery/prior_build_reconciliation.py   --prior-census <committed census> --new-census <proposed census>   --candidate-ledger <ledger> --absorptions <merged>_prior_absorptions.json   --policy-package launch_packages/pettripfinder/hotel_policy_facts_<id>.json --out <report>
```


## Promoting a re-censused, registered market (PTF-INDIANAPOLIS-PROMOTION-AUTHORITY-PREP-003)

After the founder review is CLOSED, promotion is prepared in a SHADOW, never in place:

1. **Fix the store's capture time first.** `market_observation_store` derives `observed_at` from the
   journal's `completed_at` (`capture_time.basis = acquisition_journal_completed_at`); a store built
   before that fix carries a literal date and must be rebuilt from the same closeout (no refetch).
2. **Plan as data.** `<market>_census_promotion_plan_<n>.json` (schema `ptf-census-promotion-plan/1.0`)
   is derived from the closed ledger: renames, merges, retirements, address supersessions, phone/URL
   corrections, fact corrections with the quotes they rest on, and the HOLD rulings.
3. **`scripts/pettripfinder/census_promotion.py`** applies the plan to a COPY of the proposed census
   (`identity_census_promotion/<market>.json`), re-keys renamed rows by `ptf_identity_key/1.0`,
   validates against the census contract, and re-keys the merged closeout so the store joins the shadow
   row for row. The pinned census is never written.
4. **Founder rulings go through `markets/founder_overrides/<market>.json`**: `identity_overrides`
   (adjudicate M10 on street + property code), `fact_overrides` (set/unset/unwithhold/withhold, every
   assertion cited to a quote that must be contiguous in the persisted page), keyed by the
   POST-promotion keys. The store is rebuilt from the re-keyed closeout + shadow census + overrides.
5. **Signature view + proposed authority.** A ledger-shaped signature view (one signed row per surviving
   identity, bound to the promotion store's snapshot hashes, HOLD resolutions carried by the work order
   that made them) feeds `market_proposed_authority_cli.py`. The proposed authority is NOT a shard.
6. **Prove, then stop.** The semantic-rebinding proof (packet vs packet under the key map) must explain
   every moved row by a founder correction, rename or merge; the validation script must pass all eight
   checks. Replacing the pinned census, the release contract, launch participation, publication and
   deployment remain founder-authorised steps outside the preparation order.


## Promoting the prepared authority (PTF-INDIANAPOLIS-FOUNDER-PROMOTION-004)

Executed from the PREP-003 artifacts only (no refetch, no spend), in this order, each step a
separate command so a failure stops before the next write:

0. **Collision gate first.** `indianapolis_in_promotion_collision_gate_004.json` classifies every
   remaining shared street / URL / phone group in the shadow census. Groups outside the authority
   that cannot create a duplicate live route, a duplicate authority identity or a conflicting
   canonical identity are `NON_PUBLICATION_COHORT_UNRESOLVED` (they need a ruling only before
   either row may enter authority). Two authority rows at one street are `KNOWN_MULTI_HOTEL_COMPLEX`
   only when the exclusion contract's own co-location rule proves them distinct; otherwise STOP.
1. **Census**: copy the shadow over the pinned file; register the old release contract's content
   hash in `release_contracts_superseded.json` (contracts are superseded by content, never edited).
2. **Package**: `market_policy_package_cli.py --normalize-weight --cap-qualifier-stated false
   --publish <work order>` -- the named founder rulings (decision 1: an unqualified blanket
   maximum publishes as `lte / per_pet`; decision 3: a cap whose source states no further
   qualifier records `qualifier_stated: false`, as every prior market's La Quinta cap does).
   A founder withholding reaches the package only through an observation FLAG from the existing
   vocabulary (`fact_overrides[].flag_codes`); an invented code is a malformed observation.
3. **Shard**: `market_registration_cli.py --write`, then **globals**:
   `python -m scripts.pettripfinder.build_global_authority --write` and `--check`.
4. **Release contract**: rewritten from `release_contracts.derive_authority` (never typed);
   `verify_all()` must be clean for every market. A market rebuilt on the generic path has NO
   partition mapping in `build_market_manifest._PARTITION_FILES` (Louisville precedent): its
   partition is a factory artifact with no terminal states, so `unresolved` is the exact
   subtraction. **Launch participation is NOT edited by a promotion**: the composed deployment
   manifest pins that file's hash, so it is reissued only with a deployment authorization.
5. **Pins move with the authority.** Tests that pinned the earlier build's live counts are updated
   to the promoted truth and named for the work order; historical artifacts (`*_001.json`) stay
   committed and keep their own tests.

### Exclusion contract: co-located hotels (founder ruling A, this work order)

`hotel_exclusions.validate` still refuses two exclusions at one street identity, unless
`co_located_distinct` proves two properties: distinct identity keys, distinct canonical
first-party URLs, and a brand family + property code readable from BOTH official URLs that differ
within the same family (codes are never compared as raw strings across families -- Marriott
`indsw` and IHG `indsw` are two hotels). A missing code, a missing family or a shared URL is
INSUFFICIENT / DUPLICATE and the guard fires as before. Regression:
`tests/pettripfinder/test_hotel_exclusions_co_located_004.py` (cases A-F).
