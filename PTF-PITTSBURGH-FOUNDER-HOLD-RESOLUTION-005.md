# PTF-PITTSBURGH-FOUNDER-HOLD-RESOLUTION-005

Prepared by PTF-PITTSBURGH-HARDENED-SYNC-004. Not authorised; not started.

## GOAL

Resolve the nine founder-held Pittsburgh rows, and rule on the seven signed
decisions that PTF-PITTSBURGH-HARDENED-SYNC-004 could not apply because they
name identities the registered census does not contain.

**THIS ORDER IS ZERO-COST.** Every input already exists in the repository or in
the gitignored capture tree at
`data/acquisition/pittsburgh_pa_factory_recensus_001` (92 attempted, 67 rendered
pages, all 43 hashed rows verified). Do NOT call Firecrawl, Bright Data, Google
Places or Web Unlocker, and do not run attended-Chrome acquisition.

## STARTING STATE

Committed by PTF-PITTSBURGH-HARDENED-SYNC-004:

| | |
|---|---|
| registered census | 96 (shadow recensus 115, NOT promoted) |
| published pet-friendly | 46 |
| verified no-pets | 10 |
| out of current category | 3 |
| resolved / unresolved | 59 / 37 |
| policy schema | 1.3 |
| routes | 0 (all six answered routes withdrawn) |
| release-contract disagreements | 0 |
| deployment | none; Pittsburgh hidden from navigation and sitemap |

## PART A — THE NINE HOLDS

Each is quoted from `pittsburgh_pa_founder_rulings_003.json`. All appear
solvable at $0 from owned evidence, but each needs a founder ruling, not a
mechanical fix.

**Identity adjudications (2)**
- `intown suites extended stay pittsburgh pa` — IDENTITY_NOT_CORROBORATED
- `la quinta inn and suites pittsburgh airport` — IDENTITY_NOT_CORROBORATED

  The captured page does not corroborate the identity strongly enough to bind
  policy. Both pages are owned; re-read them against the current identity
  membrane before asking the founder anything.

**Stale-twin retirements (3)**
- `courtyard by marriott pittsburgh university center` — RETIRED_STALE_TWIN,
  superseded by `courtyard pittsburgh university center`
- `hampton inn university center` — RETIRED_STALE_TWIN, superseded by
  `hampton inn pittsburgh university medical center`
- `courtyard` — HOLD_DUPLICATE_REVIEW: "rename would create a second identity
  with an existing canonical name; rename + stale-twin retirement to be ruled
  together in a future reconciliation"

  Note: 004 already applied both supersessions ONTO THE REGISTERED IDENTITIES
  and published them. What remains is retiring the recensus-side twins, which
  only matters when the census is next promoted.

**Safe merge (1)**
- `hilton garden inn` — SAFE_MERGE into the LIVE identity "Hilton Garden Inn
  Pittsburgh Downtown"; the live identity wins on street, phone, property code
  and URL.

**Founder fee-semantic rulings (2)**
- `hilton garden inn pittsburgh university place` — FEE_LOSS: overlapping bands
  not safely representable.
- `hampton inn and suites pittsburgh waterfront` — FEE_LOSS_AND_RETIRE_STALE_
  TWIN_AT_RECONCILIATION: visible first-party pricing ($125; $75) not safely
  representable.

  Before asking: check `fee_tiers` and `fee_pet_schedule` in schema 1.3 against
  the actual bands. Schema 1.3 gained `other_charges[].refundable_stated`, and
  a band shape that was unrepresentable in 1.2 may be representable now — 004
  resolved defect D1 that way rather than by withholding.

**Parser defect (1)**
- `springhill suites by marriott pittsburgh airport` — PARSER_DEFECT_WORK_ITEM:
  the surface both asserts and denies pets while a $150 fee was extracted. The
  founder declined to correct it. No refetch, no spend.

## PART B — THE SEVEN CENSUS ADDS

These carry a valid founder signature that 004 did NOT apply. Each names a real
property whose brand-scoped property code, street address and phone collide
with NOTHING in the registered 96, so applying one is a census ADD.

| signed identity | code | signed as |
|---|---|---|
| `holiday inn express pittsburgh bridgeville` | ihg:pitbv | VERIFIED_NO_PETS |
| `comfort suites` (Monroeville, PA392) | choice:pa392 | VERIFIED_NO_PETS |
| `hampton inn and suites cranberry pittsburgh` | hilton:pitcmhx | PUBLISHED_PET_FRIENDLY |
| `home2 suites by hilton pittsburgh` (McCandless) | hilton:pitmcht | PUBLISHED_PET_FRIENDLY |
| `staybridge suites pittsburgh airport` | ihg:pitsu | PUBLISHED_PET_FRIENDLY |
| `towneplace suites pittsburgh cranberry township` | marriott:pitrr | PUBLISHED_PET_FRIENDLY |
| `courtyard by marriott pittsburgh west homestead waterfront` | marriott:pithw | VERIFIED_NO_PETS |

Applying all seven would take Pittsburgh to **50 published / 13 verified
no-pets / 66 resolved of 103** — the figures the 004 prompt expected, which
assumed the adds. Note the denominator: they cannot be "66 of 96", because six
of those resolutions are not in the 96.

The last row needs its own adjudication. `courtyard by marriott pittsburgh west
homestead waterfront` (401 West Waterfront Drive, 15120, PITHW) looks like the
same building as the registered stub `courtyard by marriott pittsburgh
waterfront` (15120, no address, no phone, no URL) — but the recensus ALSO
carries a row under the stub's exact name, the founder never ruled on that
pair, and `pittsburgh_pa_prior_census_absorptions_recensus_001.json` records no
absorption because the stub has no street identity to absorb on. So it is a
merge-or-add question, not a mechanical one.

**Required discipline:** the census promotion must SUPERSEDE and ADD, never
downgrade. `build_market_authorities --write` WIPES corridor assignments — use
`--check`. The registered census is pinned by COUNT and SCHEMA in the release
contract, so any add changes `identity_census.expected_count` and the contract
must be re-authored from `release_contracts.derive_authority`, never by hand.

## PART C — THE REPLAY BACKLOG

`pittsburgh_hardened_sync_004_reader_replay.json` re-read all 66 owned pages
through the current hardened reader at $0. Reader disagreements: 0. It found:

- **5 NEW_PET_FRIENDLY_CANDIDATE** — `even hotels`, `fairfield inn and suites`,
  `embassy suites by hilton pittsburgh downtown`, `hampton inn and suites`,
  `home2 suites pittsburgh cranberry township`
- **3 NEW_VERIFIED_NO_PETS_CANDIDATE** — `holiday inn express and suites
  pittsburgh airport`, `holiday inn express pittsburgh cranberry township`,
  `cambria hotel pittsburgh downtown`
- **22 SAME_VERDICT_RICHER_READING** — the verdict is unchanged and the reading
  is fuller (more fee tiers, species, counts).
- **2 READER_RECOVERED_A_BLOCK_THE_OLD_READER_MISSED** — `doubletree by hilton
  hotel and suites pittsburgh downtown`, `homewood suites pittsburgh downtown`.
  Both are already published and both new readings AGREE with the published
  verdict.
- **14 POLICY_NOT_FOUND**, 15 still unread.

Several candidate names are bare chain words (`even hotels`, `fairfield inn and
suites`, `hampton inn and suites`) — the exact shape the name-correction
overlay exists for. Resolve the identity BEFORE proposing the policy.

None of this is authority. It is a clean-candidate packet for founder review,
and 004 deliberately applied none of it: a reader improvement is not a founder
decision.

## SEQUENCE

1. Re-read the two IDENTITY_NOT_CORROBORATED pages against the current membrane.
2. Test the two FEE_LOSS band shapes against schema 1.3.
3. Build ONE founder packet covering Part A, Part B and Part C.
4. Take the founder's rulings.
5. Apply through the sanctioned path (`pittsburgh_hardened_sync_004.py` is the
   template; its twin reconciliation and hold guards are reusable).
6. If any census add is approved: a separate SUPERSEDE / ADD-NEVER-DOWNGRADE
   promotion, then rebuild, then regenerate globals from shards.
7. Re-author the release contract from the derivation. Report disagreements = 0.

## OUT OF SCOPE

Deployment. Pittsburgh's production authorization is STALE — it was signed
against the release contract 004 replaced — and re-signing one is the founder's
act. The exact values a future authorization would pin are recorded in
`pittsburgh_hardened_sync_004_deployment_handoff.json`. Do not edit
`deploy/netlify/launch_participation.json`, and do not change the navigation or
sitemap flags.
