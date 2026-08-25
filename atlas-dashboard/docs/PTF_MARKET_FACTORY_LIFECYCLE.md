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
