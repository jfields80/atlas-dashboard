# Multi-market inventory scoping (PTF-MULTI-MARKET-INVENTORY-SCOPING-001)

Atlas was built as a one-market product. Inventory carried no statement of
which market a row belonged to, because there was only one answer, and the
generator selected *every* approved row. This document records the contract
that replaced that assumption, and exactly what a second or third market's
integrator has to do.

## The contract

Every inventory row in `launch_packages/pettripfinder/seed_businesses.csv`
carries exactly one `market_id`.

* it must exist in the committed market registry
  (`launch_packages/pettripfinder/markets/*.json`)
* missing, blank, or unknown ownership **fails closed** — it never defaults to
  the market being built
* ownership is independent of corridor assignment, in both directions
* one identity may not hold primary ownership in two markets

Implemented in `scripts/pettripfinder/market_ownership.py`. Selection order:

```
global inventory
  → explicit market selection      (owned_by(rows, market_id))
  → market-owned inventory
  → optional corridor assignment   (assign_hotels)
  → market package
```

Corridor assignment runs **after** market selection, never as a substitute
for it.

## Why corridor membership is not ownership

`markets/assignment.py` has five tiers, and the fifth is *unassigned:
published normally, reported, never dropped*. **Twelve** published Columbus
hotels sit in that tier deliberately — Westerville, New Albany, Gahanna, Canal
Winchester and the Easton cluster are all outside any published corridor.

Selecting "hotels some corridor claims" would have deleted those twelve from
production. Any future change that derives ownership from geography, corridor
membership, city text, or ZIP is reintroducing this bug.

> The originating work order estimated this population at 16. Measured against
> the live authority it is 12. The tests assert the measured value.

## Market packages vs the production site

`scripts/pettripfinder/market_package.py` separates two things that must not be
conflated:

| | owns |
|---|---|
| **market package** | its hotel routes, corridor routes, reconciliation counts, and the hashes of the files it produced |
| **production site** | several validated market packages, plus global pages and shared assets |

`assemble_market_packages()` refuses — rather than silently resolving — route
collisions, duplicate markets, corridor route crossover, and a market claiming
a globally-owned route. Combination is additive: a market's hashes and
reconciliation pass through unchanged, which is the property that makes
"adding Cleveland cannot alter Columbus" checkable instead of hoped for.

Manifests are written **outside** the generated site directory.
`build_market_manifest.py` refuses `--output` inside `--site`, because a
manifest placed in the bundle changes the bundle it describes.

## Cleveland integration — DONE (PTF-CLEVELAND-OVERNIGHT-AUTHORITY-001)

Cleveland is integrated as a source package. **It is not deployed and is not
freeze-ready.** Final state: 188 confirmed / 19 published / 8 verified-no-pets
/ 27 resolved / 161 unresolved.

What the integration needed beyond the ownership contract, all of it
generalisation rather than duplication:

* **per-market policy facts** — `hotel_policy_facts_<market_id>.json`, with
  Columbus keeping the original path so its authority file is untouched
* **per-market launch bar** — the pilot config's 30-listings/10-per-category
  bar encodes a three-category consumer product; a hotels-only regional market
  fails it for lacking parks, which is not a finding about its hotels. Non-
  Columbus markets use their own committed `minimum_published_hotels` applied
  to the categories they actually carry.
* **category scoping** — a market plans routes only for categories it carries,
  or it ships an empty directory page (which fails component compilation, and
  should)
* **market-aware labels and links** — the approved hotel-profile renderer
  hard-coded "Columbus" in its brand lockup, footer, tagline, title and meta
  description, and the nav hard-coded all three categories. Unset, Cleveland
  pages announced themselves as *PetTripFinder Columbus*.
* **route_mode honoured for the comparison page** — Cleveland is
  `market_prefixed`; the page was being written to a hard-coded unprefixed
  path while every link pointed at the prefixed one.
* **explicit exclusion ownership** — `market_id` is now required on every
  exclusion record. Defaulting an unowned record to the market being asked
  counted Columbus's 14 no-pets as Cleveland's and reported 22 for a market
  with 8.

### Known limitation, not fixed here

`hotel_profile` renders a FIXED sentence for any record carrying `fee_tiers`:
"Tiered by stay length; the source does not state a per-night or per-stay
basis." It never reads `basis_stated`/`stated_basis`. Holiday Inn Express
Westlake's page *does* say "Per stay", and Columbus's Hyatt House OSU record
has the same shape, so the page understates what the source states — in both
markets, today. Correcting the renderer necessarily changes Columbus's bytes
and therefore needs its own work order and its own zero-drift decision. The
authority is recorded truthfully in the meantime.

## Cleveland integration (original plan, retained for provenance)

Cleveland's evidence is already captured and preserved; **none of it needs
recapturing**. The proposed package lives at
`data/worker_runs/pettripfinder/discovery/review_batches/cleveland-factory-001/`:

* `proposed_cleveland_authority.json` — 19 pet-friendly proposals,
  8 verified-no-pets proposals, 11 unresolved, 1 out-of-market excluded
* `evidence_manifest.json` — 28 captures, 112 integrity checks, path + byte
  size + sha256 per artifact
* `manual_evidence_queue.json` — 150 items
* `reclassification_ledger.json` — the 193 → 188 census correction

Steps, in order:

1. The registered market id is **`cleveland-akron-canton-oh`**, not
   `cleveland-oh`. That id is already load-bearing in the committed market
   config, the identity census, and 87 identity-routing records. Renaming it
   would orphan all three; use the existing id.
2. Extract policy facts from the 19 captured proposals into
   `hotel_policy_facts.json` (observation → membrane → publication guard, as
   Columbus does). Facts are still **not** transcribed in the proposed file —
   that was deliberate, so no fact is written twice or from memory.
3. Add the 8 verified-no-pets identities to `hotel_exclusions.json` with
   `exclusion_state: VERIFIED_NO_PETS`.
4. Add Cleveland seed rows with `market_id = cleveland-akron-canton-oh`.
5. Build the Cleveland package, then rebuild Columbus and require bundle
   `404c4ff5` unchanged.
6. Combine with `assemble_market_packages()` and require Columbus's owned file
   hashes and reconciliation identical to its solo build.

## Dayton integration (`worker/ptf-dayton-market-001`)

The Dayton worktree was **not** touched by this work order. Its integrator must:

1. Rebase or merge onto `main` **after** this architecture lands — the seed CSV
   gained a `market_id` column, so any Dayton branch that edits
   `seed_businesses.csv` will conflict there and must resolve by keeping the
   column and filling it.
2. Commit a `dayton-oh` market config to
   `launch_packages/pettripfinder/markets/`. There is deliberately **no**
   `dayton-oh` entry today: creating one here would collide with the worktree's
   own configuration. Ownership validation takes the registry as a parameter,
   which is how the isolation tests prove Dayton behaviour without it.
3. Assign every confirmed Dayton inventory row `market_id = dayton-oh`.
4. Preserve Dayton's actual city and corridor labels — the 12-county regional
   umbrella (Clark County is Tier 1, 8 Tier 2 counties) is Dayton's own scope
   decision and market ownership does not change it.
5. Run the same guards: `validate_ownership`, a Columbus zero-drift rebuild at
   `404c4ff5`, and `assemble_market_packages()` across all three markets.
6. Prevent crossover: no Dayton identity may appear in a Columbus or Cleveland
   package, and no identity may hold two primary markets.
