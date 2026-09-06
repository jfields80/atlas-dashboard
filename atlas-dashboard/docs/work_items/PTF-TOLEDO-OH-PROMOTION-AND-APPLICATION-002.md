PTF-TOLEDO-OH-PROMOTION-AND-APPLICATION-002

STATUS: AUTHORED, NOT STARTED.
Authored by PTF-TOLEDO-OH-NEW-MARKET-001 at the serialized boundary, under the
founder rulings recorded in
`launch_packages/pettripfinder/toledo_oh_founder_rulings_001.json`.

WORKTREE
A FRESH worktree. Do not reuse C:\Atlas-Toledo-Hardened-V1 — it is pinned to
2163c4e and this order must start from the then-current deployed lineage.

BRANCH
worker/ptf-toledo-promotion-002

BASE
The THEN-CURRENT deployed canonical lineage. NOT 2163c4e.
Phase 0 derives it mechanically; do not type a SHA from this document.

MARKET ID
toledo-oh

SOURCE OF TRUTH FOR EVERYTHING TOLEDO
Branch worker/ptf-toledo-new-market-001 at 385c18a. Every artifact this order
consumes is committed there:

  launch_packages/pettripfinder/markets/proposed/toledo-oh.json
  launch_packages/pettripfinder/identity_census_proposed/toledo-oh.json
  launch_packages/pettripfinder/toledo_oh_founder_rulings_001.json
  launch_packages/pettripfinder/markets/reports/toledo_oh_clean_authority_001.json
  launch_packages/pettripfinder/markets/reports/toledo_oh_routing_001.json
  launch_packages/pettripfinder/markets/reports/toledo_oh_evidence_audit_001.json
  launch_packages/pettripfinder/markets/reports/toledo_oh_attended_capture_001.json
  launch_packages/pettripfinder/markets/reports/toledo_oh_firecrawl_pass_001.json
  launch_packages/pettripfinder/markets/reports/toledo_oh_free_static_capture_001.json
  launch_packages/pettripfinder/markets/reports/toledo_oh_shadow_market_001.json
  scripts/pettripfinder/discovery/config/toledo_oh.json

GOAL

Promote Toledo from a shadow package into shared production source, and prove
the composed production candidate. REGISTER the market.

This order MAY:
- integrate the then-current deployed canonical lineage
- register toledo-oh in markets/*.json
- promote the census into identity_census/
- build the Toledo authority shard
- write hotel_policy_facts_toledo-oh.json
- write the Toledo final partition
- regenerate the three generated globals
- derive the Toledo release contract
- move the three current-state pins
- assemble a production candidate and measure it
- run the broad regression and classify it

This order MUST NOT:
- deploy
- create or consume a deployment authorization
- flip launch participation
- publish any row the founder held
- admit Bowling Green
- alter another market's authority, census, partition or release contract

STOP at DEPLOYMENT_READY. Launch is PTF-TOLEDO-OH-DEPLOYMENT-AND-LAUNCH-
AUTHORIZATION-003 and is a separate, founder-authorized order.

============================================================
FOUNDER RULINGS THIS ORDER IS BOUND BY
============================================================

R1 BOWLING GREEN — EXCLUDED.
"Keep Bowling Green OUT of the Toledo market for this promotion. Do not create
or widen a Toledo fringe corridor to include Bowling Green. Preserve the
evidence and candidates for a future Bowling Green / northwest Ohio market
decision."

  - REMOVE the corridor toledo-oh__bowling-green from the contract that gets
    registered. Do not register it empty, do not suppress it below a minimum.
  - MOVE its three identities and every artifact bound to them out of the
    Toledo package and into
    launch_packages/pettripfinder/toledo_oh_bowling_green_preserved_001.json.
    MOVE, never delete (PTF-INDIANAPOLIS-FOUNDER-RULINGS-013).
      hampton                                            142 Campbell Hill Road   43402
      home2 suites                                       1630 East Wooster Street 43402
      fairfield by marriott inn and suites bowling green 1544 East Wooster Street 43402
  - ZIP 43402 is claimed by no Toledo corridor after this.

R2 GROUP A — HELD.
"Keep all unresolved Group A rows HELD outside promotion unless an existing
signed precedent makes the identity disposition fully deterministic. Do not
invent a rebrand, merge, duplicate retirement, or same-campus ruling merely to
increase coverage."

  Held addresses, each carrying two identities:
      3100 Glendale Avenue, Toledo 43614     Radisson / Delta Hotels Toledo
      6425 Kit Lane, Maumee 43537            Best Western / Baymont Maumee
      1390 Arrowhead Drive, Maumee 43537     Super 8 / Spark by Hilton Maumee
      10667 Fremont Pike, Perrysburg 43551   Days Inn Perrysburg / Super 8 Perrysburg
      101 N Summit Street, Toledo 43604      Hilton Garden Inn / Homewood Suites (same campus)

  "Fully deterministic" means a PRIOR SIGNED ruling settles this exact
  disposition on facts this market already holds. A precedent that merely
  resembles the case does not qualify. If you find yourself arguing a precedent
  across, it does not apply: leave the row held and say so.

============================================================
THE COUNT GATE — READ THIS BEFORE PHASE 0
============================================================

The founder's ruling excludes Bowling Green and then restates the clean set as
17 CLEAN_PET_FRIENDLY and 10 CLEAN_VERIFIED_NO_PETS. Those disagree. 17/10 are
the counts WITH Bowling Green in; two of the seventeen and one of the ten are
Bowling Green properties.

The EXPLICIT RULING governs. The promotion set is:

    census                    51
    CLEAN_PET_FRIENDLY        15
    CLEAN_VERIFIED_NO_PETS     9
    corridors                 12

This order FAILS CLOSED if it computes anything else. It does not reconcile the
difference by choosing; if 51/15/9 does not reproduce, stop and report.

============================================================
PHASE 0 — DERIVE THE CURRENT LINEAGE. DO NOT TYPE A SHA.
============================================================

Toledo was built at 2163c4e. Ten markets were live then. Production may have
moved: Fort Wayne and Lexington were running market-local orders in parallel and
either may have promoted since.

1. Fetch. Read the CURRENT live deployment from committed truth, not from this
   document and not from memory:
       tests/pettripfinder/pins/deployment_state.json  -> live block
   Record deploy_id, source_commit, participating_markets, total_profiles,
   sitemap_route_count, rollback_target.

2. Identify the canonical lineage tip that live deployment was assembled from.
   Branch from THAT commit.

3. Report, before touching anything:
       lineage tip SHA
       live deploy id
       live markets, profiles, routes
       what moved since 2163c4e, market by market
       whether Fort Wayne or Lexington registered

4. If ANOTHER market is mid-promotion or mid-deployment right now, STOP.
   Registration is serialized: registering market N+1 invalidates the current
   production deployment record (PTF-047). Two registrations cannot interleave.

============================================================
PHASE 1 — INTEGRATE TOLEDO ONTO THAT LINEAGE
============================================================

Merge worker/ptf-toledo-new-market-001 (385c18a) into the fresh branch.

Toledo touched ZERO tracked bytes at 2163c4e — every one of its 35 paths is an
addition — so this merge should be conflict-free by construction. Prove it:

    git diff --name-status <lineage tip> <merged head>

Every row must be A. A single M, D or R row means something is wrong; stop.

Then RE-DERIVE, do not assume:
  - the Toledo contract still parses against the CURRENT markets.contract
  - the Toledo discovery config still loads
  - toledo-oh is still absent from every registry and pin
  - no market registered since 2163c4e claims a Toledo-area ZIP
  - the 60 Toledo gates still pass at the new base

A whole-file cherry-pick is a wholesale copy; re-derive unions from canonical
bytes (PTF-INDIANAPOLIS-CANONICAL-TRANSPLANT-011).

============================================================
PHASE 2 — APPLY THE FOUNDER RULINGS TO THE SHADOW
============================================================

Before any shared file moves.

1. Remove the bowling-green corridor from the contract to be registered.
2. Move its three identities to
   launch_packages/pettripfinder/toledo_oh_bowling_green_preserved_001.json,
   carrying route, attended read, exact quote, document provenance and the
   ruling that moved them.
3. Re-derive the census, the clean authority and the shadow package from the
   ruled contract. Do not hand-edit counts.
4. Assert the count gate: 51 / 15 / 9 / 12 corridors. FAIL CLOSED otherwise.
5. Assert that no held Group A identity appears in the clean inventory.
6. Assert that ZIP 43402 is claimed by no corridor.

Commit this before Phase 3. The ruling application is reviewable on its own.

============================================================
PHASE 3 — REGISTER THE MARKET
============================================================

Order matters. Registering is what invalidates the live deployment record, so it
happens once, deliberately, and the pins move with it.

1. MOVE (git mv, preserving history):
       markets/proposed/toledo-oh.json    -> markets/toledo-oh.json
       identity_census_proposed/toledo-oh.json -> identity_census/toledo-oh.json
   Drop the `_status` PROPOSED_NOT_REGISTERED field from the contract and the
   `status` PROPOSED_NOT_REGISTERED field from the census as part of the move.

2. Build the authority shard at markets/authority/toledo-oh/:
       seed_businesses.csv
       hotel_exclusions.json      (the 9 VERIFIED_NO_PETS)
   Market work edits its SHARD ONLY. Call MA.exclusions_shard_path; never pad
   LEGACY_GLOBAL_WRITERS (PTF-PITTSBURGH-PROMOTION-AND-APPLICATION-002).

3. Write hotel_policy_facts_toledo-oh.json from the clean PF rows.
   - the READER decides pets_allowed; never re-derive it here
   - service_animal_statement is STRUCTURED; a bare quote string crashes the
     renderer
   - fee tiers: several Hilton rows state a per-night ladder
     ("$75(1-4 nights) $125(5+ nights)") alongside a headline fee. Use
     fee_tiers, do not flatten to one number
   - every fact carries its source URL, exact quote and document provenance
   - a published name must round-trip normalize_name -> identity_key or the
     join fails CLOSED (PTF-LOUISVILLE-PROMOTION-AND-APPLICATION-002)

4. Write toledo_oh_final_partition_001.json. Count unresolved FROM the
   partition, never by subtraction alone.

5. Run the publication guard INSIDE the applier, not after it
   (PTF-CINCINNATI-PROMOTION-AND-APPLICATION-003).

6. Display names: ten admitted identities carry a bare brand label
   ("Best Western", "Comfort Inn", "Quality Inn", "Super 8", "Relax Inn",
   "Sunset Motel", "Country Inn & Suites", "Comfort Suites", "Econo Lodge",
   "Hampton"). Fill each from the property's OWN page. A display rename goes in
   the name_corrections overlay, never in the identity
   (PTF-INDIANAPOLIS-PROMOTION-AND-ASSEMBLY-014). Any that cannot be filled
   from a first-party read stays as it is; do not invent a label.

============================================================
PHASE 4 — GLOBALS, THEN THE CONTRACT
============================================================

Regenerate the three generated globals BEFORE the contract derivation
(PTF-INDIANAPOLIS-PROMOTION-AND-ASSEMBLY-014). The other order is a defect.

    hotel_policy_facts.json
    hotel_exclusions.json
    production_hotels.csv

`build_market_authorities --write` WIPES corridor assignments. Use --check only.

Then derive deploy/netlify/release_contracts/toledo-oh.json and run
`python -m scripts.pettripfinder.release_contracts` — every contract against its
own authority, seconds.

Route = slugify(NAME) (PTF-LOUISVILLE-PUBLISHED-008). Verify, do not assume.

============================================================
PHASE 5 — THE THREE PINS AND THE ASSEMBLER TABLE
============================================================

An application order edits three JSON pins and its own suite, never a module
hunt (PTF-FACTORY-THROUGHPUT-HARDENING-001).

1. tests/pettripfinder/pins/market_state.json
   Add the toledo-oh row; set last_moved_by to this order.

2. tests/pettripfinder/pins/deployment_state.json
   Move the SOURCE block only. ahead_of_production: true, moved_by this order,
   fresh bundle/sitemap shas and totals. Do NOT touch the live block.

3. tests/pettripfinder/pins/supersessions.json
   Add toledo-oh under every consumed authorization that bound the markets this
   registration moves out from under.

4. scripts/pettripfinder/assemble_production_site.py
   Add "toledo-oh" to the EXPLICIT partition table. Do not rely on the glob: it
   beat the explicit table once and shipped a 153-row partition to production
   (PTF-INDIANAPOLIS-PROMOTION-REMEDIATION-005). Note that the glob would
   compute "toledo" for this market and match nothing.

5. scripts/pettripfinder/regression_lanes.py
   Add ("toledo-oh", ("test_toledo_",)) to MARKET_PREFIXES so the market-targeted
   lane can select this market's modules.

`scripts/pettripfinder/discovery/market_config.py` needs NO edit: the
conventional-filename rule already resolves toledo_oh.json.

============================================================
PHASE 6 — ASSEMBLE AND MEASURE
============================================================

    python scripts/pettripfinder/assemble_production_site.py --output data/deployment_staging/<candidate>

Delete any .netlify/ the tooling scaffolds before any lane runs: it fails the
assembler gate and it is gitignored, so it is invisible until it bites
(PTF-LOUISVILLE-DEPLOYMENT-AUTHORIZATION-003).

Report against the CURRENT live numbers from Phase 0:
    markets before -> after
    profiles before -> after (+15 expected)
    routes before -> after
    routes ADDED and routes REMOVED — removals must be 0
    bundle sha256, sitemap sha256

Measure an unauthorized candidate in a THROWAWAY worktree
(PTF-CINCINNATI-PROMOTION-AND-APPLICATION-003).

============================================================
PHASE 7 — REGRESSION
============================================================

Registering a market is a MANDATORY-FULL class under Regression V2. A narrow
lane is not available to this order and the delta classifier will say so.

    lanes: market_targeted --market toledo-oh, policy_schema, identity_routing,
           release_contract, cross_market, assembly, deployment_architecture
    then: full_regression, ONCE, after the commit
    classify --baseline <the baseline for the lineage tip> --run <full run> --rerun-flakes

`classify --run` wants the DIRECTORY. A file gives a false all-zero pass.

Every failing node id gets exactly one class. Counts are never the proof; the
node-id SET is. Expect to inherit this worktree's 24 known failures — 14
MISSING_GITIGNORED_FIXTURE_IN_A_FRESH_WORKTREE and 10 PRE_EXISTING — plus
whatever the lineage tip's own baseline carries.

Require TRUE_NEW_FAILURE = 0.

Growing a package breaks historical suites that restate a whole-package count.
Scope each to its cohort; never relax one
(PTF-APPLICATION-ORDER-EPOCH-PIN-COST). Deselect the demo-media pilot-ingestion
test in a fresh worktree.

============================================================
PHASE 8 — PARALLEL SAFETY
============================================================

Re-run the Toledo parallel-safety classifier with its ALLOWED set widened for a
registration, and prove per class rather than asserting:

    other registered market authority changed      0
    other market census / partition / contract     0
    another market's release contract              0
    deployment authorizations created              0
    deployments                                    0
    launch_participation.json changed              0

Shared files this order IS allowed to touch, and only these:
    markets/toledo-oh.json (created by move)
    identity_census/toledo-oh.json (created by move)
    markets/authority/toledo-oh/**
    the three generated globals
    deploy/netlify/release_contracts/toledo-oh.json
    the three pins
    assemble_production_site.py (one table row)
    regression_lanes.py (one MARKET_PREFIXES row)

============================================================
PHASE 9 — COMMIT, PUSH, REPORT
============================================================

Subject: PTF-TOLEDO-OH-PROMOTION-AND-APPLICATION-002

Report:
    lineage tip integrated, and what moved since 2163c4e
    census 51 / PF 15 / no-pets 9 / corridors 12
    Bowling Green: 3 identities MOVED to the preserved file, corridor removed
    Group A: rows still held, and any precedent applied with the signature named
    candidate id, bundle sha, sitemap sha
    routes added / removed (removed must be 0)
    TRUE_NEW_FAILURE
    DEPLOYMENT_READY = YES / NO
    nothing deployed

============================================================
WHAT THIS ORDER HANDS TO THE NEXT ONE
============================================================

If DEPLOYMENT_READY = YES, the next order is

    PTF-TOLEDO-OH-DEPLOYMENT-AND-LAUNCH-AUTHORIZATION-003

and it needs a founder decision this order cannot make: launch participation.
That order verifies against the COMMITTED packet, not against an inline SHA in
its own text — the Cincinnati launch order's own inline bundle SHA was wrong in
five characters and its rollback target was one deploy stale
(PTF-CINCINNATI-DEPLOYMENT-AND-LAUNCH-AUTHORIZATION-004).

STOP.
No deployment. No launch flip. No held row published. No Bowling Green.
