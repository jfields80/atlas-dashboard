# columbus-oh route migration report (ptf-market/1.0)

**Report only (PTF-CORRIDORS-002 Parts A10/I).** No redirect, canonical,
sitemap, or internal-link change is performed by this branch. The market
runs in `legacy_unprefixed` mode until this migration is explicitly approved.

## Route mapping (current -> proposed market-prefixed)

For every row: redirect needed = **301 permanent**; canonical change =
**yes** (self-canonical moves with the route); sitemap change = **yes**
(new URL replaces old); internal-link change = **yes** (all internal
hrefs are generated, so they follow automatically on regeneration).

| Page | Current route | Proposed route |
|---|---|---|
| market hub | `/pet-friendly-hotels/` | `/pet-friendly-hotels/columbus-oh/` |
| policy comparison | `/pet-friendly-hotels/policy-comparison/` | `/pet-friendly-hotels/columbus-oh/policy-comparison/` |
| corridor: Dublin | `/pet-friendly-hotels/dublin/` | `/pet-friendly-hotels/columbus-oh/dublin/` |
| corridor: Downtown Columbus | `/pet-friendly-hotels/downtown-columbus/` | `/pet-friendly-hotels/columbus-oh/downtown-columbus/` |
| corridor: Easton | `/pet-friendly-hotels/easton/` | `/pet-friendly-hotels/columbus-oh/easton/` |
| hotel: Aloft Columbus Easton | `/pet-friendly-hotels/aloft-columbus-easton/` | `/pet-friendly-hotels/columbus-oh/aloft-columbus-easton/` |
| hotel: Aloft Columbus University District | `/pet-friendly-hotels/aloft-columbus-university-district/` | `/pet-friendly-hotels/columbus-oh/aloft-columbus-university-district/` |
| hotel: Columbus Airport Marriott | `/pet-friendly-hotels/columbus-airport-marriott/` | `/pet-friendly-hotels/columbus-oh/columbus-airport-marriott/` |
| hotel: Courtyard Columbus Easton | `/pet-friendly-hotels/courtyard-columbus-easton/` | `/pet-friendly-hotels/columbus-oh/courtyard-columbus-easton/` |
| hotel: Courtyard Columbus Worthington | `/pet-friendly-hotels/courtyard-columbus-worthington/` | `/pet-friendly-hotels/columbus-oh/courtyard-columbus-worthington/` |
| hotel: Days Inn by Wyndham Grove City Columbus South | `/pet-friendly-hotels/days-inn-by-wyndham-grove-city-columbus-south/` | `/pet-friendly-hotels/columbus-oh/days-inn-by-wyndham-grove-city-columbus-south/` |
| hotel: Drury Inn & Suites Columbus Dublin | `/pet-friendly-hotels/drury-inn-suites-columbus-dublin/` | `/pet-friendly-hotels/columbus-oh/drury-inn-suites-columbus-dublin/` |
| hotel: Drury Inn & Suites Columbus Grove City | `/pet-friendly-hotels/drury-inn-suites-columbus-grove-city/` | `/pet-friendly-hotels/columbus-oh/drury-inn-suites-columbus-grove-city/` |
| hotel: Drury Inn & Suites Columbus Polaris | `/pet-friendly-hotels/drury-inn-suites-columbus-polaris/` | `/pet-friendly-hotels/columbus-oh/drury-inn-suites-columbus-polaris/` |
| hotel: Fairfield Inn & Suites Columbus New Albany | `/pet-friendly-hotels/fairfield-inn-suites-columbus-new-albany/` | `/pet-friendly-hotels/columbus-oh/fairfield-inn-suites-columbus-new-albany/` |
| hotel: Fairfield Inn & Suites Columbus OSU | `/pet-friendly-hotels/fairfield-inn-suites-columbus-osu/` | `/pet-friendly-hotels/columbus-oh/fairfield-inn-suites-columbus-osu/` |
| hotel: Hampton Inn Columbus Airport | `/pet-friendly-hotels/hampton-inn-columbus-airport/` | `/pet-friendly-hotels/columbus-oh/hampton-inn-columbus-airport/` |
| hotel: Hampton Inn Columbus Dublin | `/pet-friendly-hotels/hampton-inn-columbus-dublin/` | `/pet-friendly-hotels/columbus-oh/hampton-inn-columbus-dublin/` |
| hotel: Hilton Columbus at Easton | `/pet-friendly-hotels/hilton-columbus-at-easton/` | `/pet-friendly-hotels/columbus-oh/hilton-columbus-at-easton/` |
| hotel: Hilton Garden Inn Columbus Airport | `/pet-friendly-hotels/hilton-garden-inn-columbus-airport/` | `/pet-friendly-hotels/columbus-oh/hilton-garden-inn-columbus-airport/` |
| hotel: Home2 Suites by Hilton Columbus Dublin | `/pet-friendly-hotels/home2-suites-by-hilton-columbus-dublin/` | `/pet-friendly-hotels/columbus-oh/home2-suites-by-hilton-columbus-dublin/` |
| hotel: Home2 Suites by Hilton Columbus Easton | `/pet-friendly-hotels/home2-suites-by-hilton-columbus-easton/` | `/pet-friendly-hotels/columbus-oh/home2-suites-by-hilton-columbus-easton/` |
| hotel: Home2 Suites New Albany Columbus | `/pet-friendly-hotels/home2-suites-new-albany-columbus/` | `/pet-friendly-hotels/columbus-oh/home2-suites-new-albany-columbus/` |
| hotel: Homewood Suites by Hilton Columbus Dublin | `/pet-friendly-hotels/homewood-suites-by-hilton-columbus-dublin/` | `/pet-friendly-hotels/columbus-oh/homewood-suites-by-hilton-columbus-dublin/` |
| hotel: Hyatt Place Columbus OSU | `/pet-friendly-hotels/hyatt-place-columbus-osu/` | `/pet-friendly-hotels/columbus-oh/hyatt-place-columbus-osu/` |
| hotel: Hyatt Regency Columbus | `/pet-friendly-hotels/hyatt-regency-columbus/` | `/pet-friendly-hotels/columbus-oh/hyatt-regency-columbus/` |
| hotel: La Quinta Columbus West-Hilliard | `/pet-friendly-hotels/la-quinta-columbus-west-hilliard/` | `/pet-friendly-hotels/columbus-oh/la-quinta-columbus-west-hilliard/` |
| hotel: La Quinta Inn by Wyndham Columbus Dublin | `/pet-friendly-hotels/la-quinta-inn-by-wyndham-columbus-dublin/` | `/pet-friendly-hotels/columbus-oh/la-quinta-inn-by-wyndham-columbus-dublin/` |
| hotel: La Quinta Inn by Wyndham Columbus I-70E/Reynoldsburg | `/pet-friendly-hotels/la-quinta-inn-by-wyndham-columbus-i-70e-reynoldsburg/` | `/pet-friendly-hotels/columbus-oh/la-quinta-inn-by-wyndham-columbus-i-70e-reynoldsburg/` |
| hotel: Red Roof PLUS+ Columbus Downtown Convention Center | `/pet-friendly-hotels/red-roof-plus-columbus-downtown-convention-center/` | `/pet-friendly-hotels/columbus-oh/red-roof-plus-columbus-downtown-convention-center/` |
| hotel: Red Roof PLUS+ Columbus Worthington | `/pet-friendly-hotels/red-roof-plus-columbus-worthington/` | `/pet-friendly-hotels/columbus-oh/red-roof-plus-columbus-worthington/` |
| hotel: Residence Inn Columbus Airport | `/pet-friendly-hotels/residence-inn-columbus-airport/` | `/pet-friendly-hotels/columbus-oh/residence-inn-columbus-airport/` |
| hotel: Residence Inn Columbus Easton | `/pet-friendly-hotels/residence-inn-columbus-easton/` | `/pet-friendly-hotels/columbus-oh/residence-inn-columbus-easton/` |
| hotel: Residence Inn Columbus OSU | `/pet-friendly-hotels/residence-inn-columbus-osu/` | `/pet-friendly-hotels/columbus-oh/residence-inn-columbus-osu/` |
| hotel: Sheraton Suites Columbus Worthington | `/pet-friendly-hotels/sheraton-suites-columbus-worthington/` | `/pet-friendly-hotels/columbus-oh/sheraton-suites-columbus-worthington/` |
| hotel: Sonesta Columbus Downtown | `/pet-friendly-hotels/sonesta-columbus-downtown/` | `/pet-friendly-hotels/columbus-oh/sonesta-columbus-downtown/` |
| hotel: Sonesta Simply Suites Dublin Columbus | `/pet-friendly-hotels/sonesta-simply-suites-dublin-columbus/` | `/pet-friendly-hotels/columbus-oh/sonesta-simply-suites-dublin-columbus/` |
| hotel: Staybridge Suites Columbus Dublin | `/pet-friendly-hotels/staybridge-suites-columbus-dublin/` | `/pet-friendly-hotels/columbus-oh/staybridge-suites-columbus-dublin/` |
| hotel: The Plaza Hotel Columbus at Capitol Square | `/pet-friendly-hotels/the-plaza-hotel-columbus-at-capitol-square/` | `/pet-friendly-hotels/columbus-oh/the-plaza-hotel-columbus-at-capitol-square/` |
| hotel: The Westin Great Southern Columbus | `/pet-friendly-hotels/the-westin-great-southern-columbus/` | `/pet-friendly-hotels/columbus-oh/the-westin-great-southern-columbus/` |
| hotel: TownePlace Suites Columbus Airport Gahanna | `/pet-friendly-hotels/towneplace-suites-columbus-airport-gahanna/` | `/pet-friendly-hotels/columbus-oh/towneplace-suites-columbus-airport-gahanna/` |
| hotel: TownePlace Suites Columbus Dublin | `/pet-friendly-hotels/towneplace-suites-columbus-dublin/` | `/pet-friendly-hotels/columbus-oh/towneplace-suites-columbus-dublin/` |
| hotel: TownePlace Suites Columbus Easton Area | `/pet-friendly-hotels/towneplace-suites-columbus-easton-area/` | `/pet-friendly-hotels/columbus-oh/towneplace-suites-columbus-easton-area/` |

## Risk of ranking loss

- The site is young (live since 2026-07-25) with a small backlink
  profile, so consolidated-signal loss from a 301 migration is LOW but
  not zero; hotel profiles carry the indexed long-tail queries.
- Every legacy route must 301 to its exact new counterpart (never the
  hub), and the old sitemap URLs must be dropped in the same deploy the
  new ones appear -- a mixed state risks duplicate-content dilution.
- Canonicals, breadcrumb JSON-LD, and LodgingBusiness JSON-LD are all
  generated from the route, so a single regeneration keeps them
  consistent; no hand edits.

## Recommended migration order

1. Approve the target routes (this report) and freeze inventory churn
   for the migration window.
2. Regenerate the site in `market_prefixed` mode in a preview deploy;
   verify route inventory, canonicals, and internal links against the
   release-contract gates.
3. Ship the production deploy with the full legacy->new 301 map in
   `_redirects` (one rule per route, no wildcards that could shadow
   real pages).
4. Submit the new sitemap; monitor coverage and top hotel queries for
   two weeks before removing any legacy rule.
