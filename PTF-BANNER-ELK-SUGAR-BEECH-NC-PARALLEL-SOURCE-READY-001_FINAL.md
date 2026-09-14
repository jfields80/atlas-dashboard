# PTF-BANNER-ELK-SUGAR-BEECH-NC-PARALLEL-SOURCE-READY-001 — FINAL

Market `banner-elk-sugar-beech-nc` ("Banner Elk – Sugar Mountain – Beech Mountain, North Carolina").
Branch `worker/ptf-banner-elk-nc-market-001`. Built from zero on the Jacksonville-live parent `7b630cfa`.

**State: NOT SOURCE READY.** The census, the evidence, the staged authority and the shadow seal are all built, and they
reproduce byte for byte. The FAST lane refuses the market for one reason. Its cold bundle build stops at the launch
floor: **4 verified pet-friendly listings, and the market's own `minimum_published_hotels` is 5.** That floor was set
before any inventory existed, and every registered market carries the same value. It was not lowered.

Machine-readable accounting: `atlas-dashboard/launch_packages/pettripfinder/markets/reports/banner_elk_sugar_beech_nc_source_ready_accounting_009.json`

## Timings (UTC)

| Phase | Observed |
|---|---|
| **BANNER_ELK_START_TIMESTAMP** | **2026-09-14T13:22:48Z** (09:22:48 EDT) |
| Geography and corridor model | by 13:36Z |
| OSM lane | 413.2 s (226 lodging elements) |
| Brand inventory | 93 free requests |
| Destination rosters | 99 free requests, plus 42 Explore Boone rows owned at 0 requests |
| Static and policy-page lanes | 27 targets; 47 sites and 119 documents |
| Attended browser | The Lodge at Banner Elk; 4 Seasons at Beech Mountain |
| First inputs `b31d1f5e` → seal → FAST refused | 13:54:56Z → 13:55:55Z |
| Final inputs `e7684f85` → seal → FAST refused | 14:01:37Z → 14:02Z |
| Clean-worktree reproduction | 14:04Z–14:05Z, byte-identical, same digest |
| **ZERO_TO_SOURCE_READY** | **NOT REACHED.** First refusal came 33 min 07 s after start. |

## Geography

Membership is decided by the property's own postal code, looked up in a postal-code partition.

| Class | Corridor (ZIPs) |
|---|---|
| CORE | Banner Elk / Sugar Mountain / Beech Mountain / Seven Devils (28604) |
| CORRIDOR | Linville / Grandfather Mountain, Montezuma, Pineola (28646, 28653, 28662) |
| FRINGE | Newland (28657); Elk Park (28622) |
| OUTSIDE | Refused by name: every Boone – Blowing Rock ZIP (28607, 28608, 28605, 28691, 28692, 28618, 28679, 28698, 28684); Ashe County; Crossnore, Minneapolis and Plumtree; Spruce Pine; Lenoir; Roan Mountain and Elizabethton TN |

* A Watauga town stated beside 28604 is a **GEOGRAPHY_HOLD**. The ZIP alone never decides.
  * The Mast Farm Inn's own page says "Valle Crucis 28604", so it is held.
  * Taylor House Inn's own page says "Banner Elk 28604", so it is admitted.
* A name-only row that matches a registered Boone census identity is OUTSIDE (live neighbour market). No Boone identity is duplicated. Cross-market identity-key collisions: **0**.

## Accounting

| Measure | Value |
|---|---|
| TOTAL DISCOVERED | **157** |
| PROPOSED CENSUS | **15** |
| VALID PET-FRIENDLY | **4** — Courtyard Sugar Mountain Banner Elk (owned Marriott row), The Lodge at Banner Elk, Parkview Lodge & Cabins, The Pineola |
| VALID VERIFIED-NO-PETS | **2** — Smoketree Lodge, The Azalea Inn |
| RESOLVED / UNRESOLVED | **6 / 9** |

## Holds by class

| Class | Count | Rows |
|---|---|---|
| IDENTITY | 10 | Review (2): Eseeola Lodge (private club lodge), Pineola Motel (map-only; possibly The Pineola's stale name). Name-only (8): Banner Elk Winery & Villa, Bear's Loft, Beech Mountain Inns, Deer Brook Inn, Hillcrest Haven, The Banner Elk Inn (×2), Tufts House Inn |
| ROUTING | 1 | Pixie Motor Inn (no own website) |
| ACCESS-BLOCKED | 1 | Top of the Beech Inn (operator site 403; browser not permitted on that domain) |
| EVIDENCE | 7 | 4 Seasons ("We do not allow pets." is QUOTE_NOT_OPERATIVE to the reader); Taylor House (QUOTE_NOT_OPERATIVE); Little Main Street Inn and Perry House (FEE_ONLY, no bindable address); Beech Alpen Inn, Huskins Court, Inn at Shady Lawn (no policy on own pages) |
| GEOGRAPHY | 1 | The Mast Farm Inn |
| PAID | 0 | $0 spent |
| FOUNDER | 0 | — |
| OUTSIDE | 56 | 34 in the live Boone market; Hilton neighbours in Asheville, Hickory, Lenoir and Marion; Linville Falls Lodge (its own site states 28647); Roan Mountain TN |
| NON-HOTEL | 75 | 48 roster-typed cabins, condos and vacation homes; 8 rental companies or platforms; 7 condo complexes (Pinnacle Inn, Sugar Top, Sugar Ski & CC, Christie Village, Highlands at Sugar…); 6 camps or campgrounds; 3 cabins; 1 timeshare (Bluegreen); 1 dining village; 1 competitor rental |
| CLOSED / RETIRED | 1 | Best Western Mountain Lodge, now The Lodge at Banner Elk |

## Corridor coverage

Rows are counts: census / pet-friendly / no-pets / unresolved.

| Corridor | Class | Counts |
|---|---|---|
| Banner Elk / Sugar / Beech | CORE | 10 / 2 / 2 / 6 |
| Linville / Grandfather | CORRIDOR | 1 / 0 / 0 / 1 |
| Newland / Elk Park | FRINGE | 4 / 2 / 0 / 2 |

| Town (reporting overlay) | Counts |
|---|---|
| Banner Elk | 6 / 1 / 2 / 3 |
| Sugar Mountain | 1 / 1 / 0 / 0 |
| Beech Mountain | 3 / 0 / 0 / 3 |
| Seven Devils | 0 (only a cabin rental, refused) |
| Linville / Grandfather | 1 / 0 / 0 / 1 |
| Newland | 4 / 2 / 0 / 2 |
| Elk Park | 0 (only an RV park, refused) |

## Owned evidence reused

* **Identities.** Boone preserved 30 rows for this market. Each was re-classified here.
* **Routes.** 1 (Courtyard `tribc`).
* **Policy.** 1 Marriott row, carried verbatim with its provenance and digest.
* **Rosters.** 42 Explore Boone rows.

## Shadow seal

| Item | Value |
|---|---|
| Package | `pkg-banner-elk-sugar-beech-nc-eb8d7487a044a10a` |
| Digest | `sha256:eb8d7487a044a10afb80b84c4790530099e954d89df7c9f381ea01124b242fa2` |
| Zone | SHADOW_UNTIL_REGISTERED |
| Source | `e7684f85` |
| Reproducible | YES: in-process, and in a separate process in a clean worktree |
| FAST | Aborted at the cold bundle build, 0/15, no receipt |
| Committed | **NO** — a package with no receipt is not lifecycle-safe to keep |

## Not done, by design

* No factory or shared code changed.
* No shared state changed: registry, participation, closure, pin, contract, globals and `identity_resolutions.json` are untouched.
* No broad regression, no candidate, no authorization, no deploy. $0 paid.

## What would make it source-ready

Any one of these:

1. A fifth operative first-party pet-friendly read. Open candidates: The Banner Elk Inn (site did not resolve), Top of the Beech Inn, Beech Alpen Inn, The Inn at Shady Lawn, Huskins Court, Pixie Motor Inn.
2. A geography ruling on The Mast Farm Inn. Its own policies page is an operative acceptance.
3. Otherwise, re-probe before registration.

Shared notes, recorded here and not repaired:

* The shared reader does not accept "We do not allow pets." or "we cannot accommodate any pets" as refusals.
* The launch floor is enforced inside the FAST bundle build, not as a named rule.
