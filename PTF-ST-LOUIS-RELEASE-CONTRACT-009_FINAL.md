# PTF-ST-LOUIS-RELEASE-CONTRACT-009 — STOPPED BEFORE THE CONTRACT

**Market:** `st-louis-mo` **Branch:** `feature/ptf-st-louis-market-001`
**Start HEAD:** `a8ff0bc`
**Offline only — zero provider calls, zero spend, zero re-fetches.**
**NOT REGISTERED. NOT PUBLISHED. NOT DEPLOYED.**

---

## A. Headline

**The release contract was NOT created, and it should not be.** A release
contract points at a policy package by path, sha256, schema version and record
count. St. Louis has no policy package, and **the package cannot be built from
the signed authority without either inventing values the sources never stated or
silently dropping facts the founder validated.**

**Only 19 of the 82 pet-friendly rows reach schema 1.2 today.**

Writing a contract now would mean pointing `policy_package.expected_sha256` at a
file that does not exist, or building that file on four guesses. Step 4 of this
work order says to report a gate as blocked "rather than weakening or skipping it
silently" — this is that instruction applied one level up.

## B. Step 1 — preconditions, all pass

| Check | Result |
|---|---|
| HEAD `a8ff0bc`, tree clean | ✔ |
| Current authority 119 / PF 82 / NP 37 | ✔ |
| Superseded recorded | 2 |
| Distinct names / slugs / identities / source URLs | 119 each |
| Retired Wingate + DoubleTree absent | ✔ |
| Held Days Inn absent | ✔ |
| Fairfield + SpringHill present, confirmation persisted | ✔ |
| Foreign rows | 0 |

## C. Step 2 — precedent studied

`ptf-market-release-contract/1.0`, 27 minimum release gates, market-prefixed
routing, `publishable_root: site/`, two control files, 8 forbidden output tokens,
5 forbidden basenames, 7 forbidden extensions, 13 forbidden path segments.
`deployment_authorization.grants_deployment: false` — a passing contract means
structurally deployable, never authorized.

The decisive detail: **`policy_package` is the identity authority.** Its note
says the verified identities are *derived from the package at assembly time via
`site_data.verified_public_hotels()`*, which treats the package as authority and
**fails closed** when a record has no seed row.

## D. Step 3 — why the contract could not be written

I built a generic projector, `market_policy_package_cli.py`, which reshapes the
signed authority into schema 1.2 and runs **every** record through the
repository's own `contracts.policy_schema.validate_facts`. It refuses to write
if any record raises. It refused.

| Cause | Rows affected |
|---|---|
| `weight_limit` missing required `operator` **and** `scope` | **48** |
| `service_animal_exception` is not a schema-1.2 fact field | **41** |
| `fee_cap` missing required `qualifier_stated` | **6** |
| `pet_deposit` is not a schema-1.2 fact field | **5** |
| **Passes as-is** | **19** |

(Rows can trip more than one; 19 pass, 63 are refused.)

### These are decisions, not bugs — and I verified that

**Every live market's weight limits carry `operator` and `scope`.** I checked
Pittsburgh, Milwaukee and Dayton: 84 weight limits, all with both fields. So the
schema requirement is real and settled, and St. Louis's reader is the outlier —
deliberately. Its own `non_inferences` say:

> *"weight_limit.operator: 'maximum' / 'up to' / 'under' are recorded as a value
> only; defaulting a comparison is a guest-visible error in both directions"*

Defaulting `lte`/`per_pet` for 48 St. Louis rows would contradict the reader's
recorded refusal on each one. There *is* corpus precedent (Detroit-Ann-Arbor
treated `scope: per_pet` on a blanket number as established), but that is a
founder ruling of exactly the kind you gave on the allowance question in 006 —
not an agent default.

**No live market carries `service_animal_exception` in `facts`.** Zero, across
all three I checked. So the schema implies dropping it — and that silently
discards a guest-useful statement on 41 St. Louis hotels that your own review
validated and that 008B's cleanup specifically corrected on two rows.

**`fee_cap.qualifier_stated` is required on purpose.** `_check_cap`'s docstring:
*"a cap never covers two pets unless the source said so — the corpus contains
caps whose quote names a pet count that the structure lost, and a $105 ceiling
shown against a first pet that stays free is a price the hotel never quoted."*
St. Louis's six caps quote *"Max 75 USD per stay"*, which names no qualifier, so
`false` is defensible — but it is a claim about the source, and the schema made
it required so a person makes it.

**One of the five causes was my own bug and I fixed it:** the reader spells the
cap amount `amount_minor`, schema 1.2 spells it `amount_cents`. Same integer,
same unit — a rename. Fixing it did not change the count, because
`qualifier_stated` is still required.

## E. Steps 4 and 5 — what could and could not be evaluated

**Evaluated and PASSING (12), from the authority directly:**
82 profile inputs · 82 distinct canonical names · 82 distinct slugs · no
duplicate identities · no duplicate source URLs · no foreign authority rows · no
held or superseded rows admitted · no missing required fields · no city or
corridor gaps · no route collisions with live markets · no dual-brand ambiguity ·
no authority or signature hash drift.

**BLOCKED_BY_POLICY_PACKAGE (11)** — every gate whose subject is the package:
`authority.package_exists`, `authority.package_sha256`,
`authority.package_schema_version`, `authority.package_count`,
`identity.verified_from_package`, `identity.held_derived`,
`route.profile_count_matches_contract`, `route.all_committed_profiles_present`,
`route.all_held_absent`, `content.build_report_hotel_count_matches_contract`,
`authority.reconciliation_matches_market_authority`.

**BLOCKED_BY_REGISTRATION (4)** — the seed inventory lives at
`markets/authority/<market>/seed_businesses.csv`, and that directory cannot
exist for an unregistered market: `route.no_excluded_reference_on_any_surface`,
`content.zero_broken_links`, `content.quality_report_clean`,
`publish.control_files_present`.

**Not evaluable without a build (12):** the remaining `publish.*`, `headers.*`
and `tech.*` gates need generated output. I did **not** run a build — there is no
package and no seed inventory to build from.

**Projected global profile count if St. Louis published all 82: 415** (333 + 82).
**Route collision status: NONE** — market-prefixed routing puts everything under
`/pet-friendly-hotels/st-louis-mo/`, and Columbus remains the anchor. Existing
live routes are untouched. I could not compute projected HTML/file/sitemap counts
deterministically without a build.

## F. Production untouched

`verify_manifest()` → `[]`. Release contracts still exactly the six live ones —
no `st-louis-mo.json` was created. No policy package written. No participation,
manifest or authorization file touched.

## G. Remaining blockers, in priority order

1. **Weight-limit operator and scope — 48 rows.** A founder ruling: does the
   corpus precedent (`lte` / `per_pet` for a blanket "maximum N lb") apply to
   St. Louis, or do these rows publish without a weight limit? Offline either way.
2. **Service-animal statements — 41 rows.** Schema 1.2 has no home for them.
   Drop them from published facts, or amend the schema to carry them? A versioned
   contract change if the latter.
3. **`fee_cap.qualifier_stated` — 6 rows.** The quotes name no qualifier; confirm
   `false`.
4. **`pet_deposit` — 5 rows.** Map to `other_charges` (live markets use it) or
   drop.
5. **Seed inventory — registration-blocked.** Downstream of registration, which
   is downstream of the deployment-authorization re-issue.
6. **Release contract** — authorable the moment 1–4 are settled and the package
   builds.

## H. Status

```
ST. LOUIS RELEASE CONTRACT READY      = NO
ST. LOUIS CURRENT SIGNED AUTHORITY    = 119
ST. LOUIS PET_FRIENDLY                = 82
ST. LOUIS VERIFIED_NO_PETS            = 37
ST. LOUIS PROJECTED PUBLIC HOTEL ROUTES = 82
ST. LOUIS RELEASE GATES READY         = NO

ST. LOUIS REGISTERED = FALSE
ST. LOUIS PUBLISHED  = FALSE
ST. LOUIS DEPLOYED   = FALSE
```
