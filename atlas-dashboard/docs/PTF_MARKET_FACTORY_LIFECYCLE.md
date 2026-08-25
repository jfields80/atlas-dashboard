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
