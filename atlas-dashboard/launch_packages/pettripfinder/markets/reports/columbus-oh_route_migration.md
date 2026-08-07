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
| corridor: Polaris | `/pet-friendly-hotels/polaris/` | `/pet-friendly-hotels/columbus-oh/polaris/` |
| corridor: OSU / University Area | `/pet-friendly-hotels/osu-university-area/` | `/pet-friendly-hotels/columbus-oh/osu-university-area/` |
| corridor: Reynoldsburg / East Columbus | `/pet-friendly-hotels/reynoldsburg-east-columbus/` | `/pet-friendly-hotels/columbus-oh/reynoldsburg-east-columbus/` |
| corridor: Airport | `/pet-friendly-hotels/airport/` | `/pet-friendly-hotels/columbus-oh/airport/` |
| corridor: Easton | `/pet-friendly-hotels/easton/` | `/pet-friendly-hotels/columbus-oh/easton/` |
| hotel: Aloft Columbus Easton | `/pet-friendly-hotels/aloft-columbus-easton/` | `/pet-friendly-hotels/columbus-oh/aloft-columbus-easton/` |
| hotel: Aloft Columbus University District | `/pet-friendly-hotels/aloft-columbus-university-district/` | `/pet-friendly-hotels/columbus-oh/aloft-columbus-university-district/` |
| hotel: BrewDog DogHouse Columbus | `/pet-friendly-hotels/brewdog-doghouse-columbus/` | `/pet-friendly-hotels/columbus-oh/brewdog-doghouse-columbus/` |
| hotel: Candlewood Suites Columbus North - Polaris by IHG | `/pet-friendly-hotels/candlewood-suites-columbus-north-polaris-by-ihg/` | `/pet-friendly-hotels/columbus-oh/candlewood-suites-columbus-north-polaris-by-ihg/` |
| hotel: Columbus Airport Marriott | `/pet-friendly-hotels/columbus-airport-marriott/` | `/pet-friendly-hotels/columbus-oh/columbus-airport-marriott/` |
| hotel: Courtyard Columbus Easton | `/pet-friendly-hotels/courtyard-columbus-easton/` | `/pet-friendly-hotels/columbus-oh/courtyard-columbus-easton/` |
| hotel: Courtyard Columbus Worthington | `/pet-friendly-hotels/courtyard-columbus-worthington/` | `/pet-friendly-hotels/columbus-oh/courtyard-columbus-worthington/` |
| hotel: Days Inn by Wyndham Columbus Airport | `/pet-friendly-hotels/days-inn-by-wyndham-columbus-airport/` | `/pet-friendly-hotels/columbus-oh/days-inn-by-wyndham-columbus-airport/` |
| hotel: Days Inn by Wyndham Grove City Columbus South | `/pet-friendly-hotels/days-inn-by-wyndham-grove-city-columbus-south/` | `/pet-friendly-hotels/columbus-oh/days-inn-by-wyndham-grove-city-columbus-south/` |
| hotel: Drury Inn & Suites Columbus Dublin | `/pet-friendly-hotels/drury-inn-suites-columbus-dublin/` | `/pet-friendly-hotels/columbus-oh/drury-inn-suites-columbus-dublin/` |
| hotel: Drury Inn & Suites Columbus Grove City | `/pet-friendly-hotels/drury-inn-suites-columbus-grove-city/` | `/pet-friendly-hotels/columbus-oh/drury-inn-suites-columbus-grove-city/` |
| hotel: Drury Inn & Suites Columbus Polaris | `/pet-friendly-hotels/drury-inn-suites-columbus-polaris/` | `/pet-friendly-hotels/columbus-oh/drury-inn-suites-columbus-polaris/` |
| hotel: Embassy Suites by Hilton Columbus Airport | `/pet-friendly-hotels/embassy-suites-by-hilton-columbus-airport/` | `/pet-friendly-hotels/columbus-oh/embassy-suites-by-hilton-columbus-airport/` |
| hotel: Fairfield by Marriott Inn & Suites Columbus East | `/pet-friendly-hotels/fairfield-by-marriott-inn-suites-columbus-east/` | `/pet-friendly-hotels/columbus-oh/fairfield-by-marriott-inn-suites-columbus-east/` |
| hotel: Fairfield Inn & Suites Columbus New Albany | `/pet-friendly-hotels/fairfield-inn-suites-columbus-new-albany/` | `/pet-friendly-hotels/columbus-oh/fairfield-inn-suites-columbus-new-albany/` |
| hotel: Fairfield Inn & Suites Columbus OSU | `/pet-friendly-hotels/fairfield-inn-suites-columbus-osu/` | `/pet-friendly-hotels/columbus-oh/fairfield-inn-suites-columbus-osu/` |
| hotel: Four Points by Sheraton Columbus - Polaris | `/pet-friendly-hotels/four-points-by-sheraton-columbus-polaris/` | `/pet-friendly-hotels/columbus-oh/four-points-by-sheraton-columbus-polaris/` |
| hotel: Hampton Inn & Suites Columbus Downtown | `/pet-friendly-hotels/hampton-inn-suites-columbus-downtown/` | `/pet-friendly-hotels/columbus-oh/hampton-inn-suites-columbus-downtown/` |
| hotel: Hampton Inn & Suites Columbus-Easton Area | `/pet-friendly-hotels/hampton-inn-suites-columbus-easton-area/` | `/pet-friendly-hotels/columbus-oh/hampton-inn-suites-columbus-easton-area/` |
| hotel: Hampton Inn & Suites Columbus Hilliard | `/pet-friendly-hotels/hampton-inn-suites-columbus-hilliard/` | `/pet-friendly-hotels/columbus-oh/hampton-inn-suites-columbus-hilliard/` |
| hotel: Hampton Inn & Suites Columbus Polaris | `/pet-friendly-hotels/hampton-inn-suites-columbus-polaris/` | `/pet-friendly-hotels/columbus-oh/hampton-inn-suites-columbus-polaris/` |
| hotel: Hampton Inn and Suites Columbus Scioto Downs | `/pet-friendly-hotels/hampton-inn-and-suites-columbus-scioto-downs/` | `/pet-friendly-hotels/columbus-oh/hampton-inn-and-suites-columbus-scioto-downs/` |
| hotel: Hampton Inn Columbus Airport | `/pet-friendly-hotels/hampton-inn-columbus-airport/` | `/pet-friendly-hotels/columbus-oh/hampton-inn-columbus-airport/` |
| hotel: Hampton Inn Columbus Dublin | `/pet-friendly-hotels/hampton-inn-columbus-dublin/` | `/pet-friendly-hotels/columbus-oh/hampton-inn-columbus-dublin/` |
| hotel: Hawthorn Extended Stay by Wyndham Columbus West | `/pet-friendly-hotels/hawthorn-extended-stay-by-wyndham-columbus-west/` | `/pet-friendly-hotels/columbus-oh/hawthorn-extended-stay-by-wyndham-columbus-west/` |
| hotel: Hilton Columbus at Easton | `/pet-friendly-hotels/hilton-columbus-at-easton/` | `/pet-friendly-hotels/columbus-oh/hilton-columbus-at-easton/` |
| hotel: Hilton Columbus Downtown | `/pet-friendly-hotels/hilton-columbus-downtown/` | `/pet-friendly-hotels/columbus-oh/hilton-columbus-downtown/` |
| hotel: Hilton Columbus/Polaris | `/pet-friendly-hotels/hilton-columbus-polaris/` | `/pet-friendly-hotels/columbus-oh/hilton-columbus-polaris/` |
| hotel: Hilton Garden Inn Columbus Airport | `/pet-friendly-hotels/hilton-garden-inn-columbus-airport/` | `/pet-friendly-hotels/columbus-oh/hilton-garden-inn-columbus-airport/` |
| hotel: Hilton Garden Inn Columbus/Dublin | `/pet-friendly-hotels/hilton-garden-inn-columbus-dublin/` | `/pet-friendly-hotels/columbus-oh/hilton-garden-inn-columbus-dublin/` |
| hotel: Hilton Garden Inn Columbus Easton | `/pet-friendly-hotels/hilton-garden-inn-columbus-easton/` | `/pet-friendly-hotels/columbus-oh/hilton-garden-inn-columbus-easton/` |
| hotel: Hilton Garden Inn Columbus/Grove City | `/pet-friendly-hotels/hilton-garden-inn-columbus-grove-city/` | `/pet-friendly-hotels/columbus-oh/hilton-garden-inn-columbus-grove-city/` |
| hotel: Hilton Garden Inn Columbus/Polaris | `/pet-friendly-hotels/hilton-garden-inn-columbus-polaris/` | `/pet-friendly-hotels/columbus-oh/hilton-garden-inn-columbus-polaris/` |
| hotel: Hilton Garden Inn Columbus-University Area | `/pet-friendly-hotels/hilton-garden-inn-columbus-university-area/` | `/pet-friendly-hotels/columbus-oh/hilton-garden-inn-columbus-university-area/` |
| hotel: Holiday Inn Express & Suites Columbus East - Reynoldsburg by IHG | `/pet-friendly-hotels/holiday-inn-express-suites-columbus-east-reynoldsburg-by-ihg/` | `/pet-friendly-hotels/columbus-oh/holiday-inn-express-suites-columbus-east-reynoldsburg-by-ihg/` |
| hotel: Home2 Suites by Hilton Columbus Airport East Broad | `/pet-friendly-hotels/home2-suites-by-hilton-columbus-airport-east-broad/` | `/pet-friendly-hotels/columbus-oh/home2-suites-by-hilton-columbus-airport-east-broad/` |
| hotel: Home2 Suites by Hilton Columbus Downtown | `/pet-friendly-hotels/home2-suites-by-hilton-columbus-downtown/` | `/pet-friendly-hotels/columbus-oh/home2-suites-by-hilton-columbus-downtown/` |
| hotel: Home2 Suites by Hilton Columbus Dublin | `/pet-friendly-hotels/home2-suites-by-hilton-columbus-dublin/` | `/pet-friendly-hotels/columbus-oh/home2-suites-by-hilton-columbus-dublin/` |
| hotel: Home2 Suites by Hilton Columbus Easton | `/pet-friendly-hotels/home2-suites-by-hilton-columbus-easton/` | `/pet-friendly-hotels/columbus-oh/home2-suites-by-hilton-columbus-easton/` |
| hotel: Home2 Suites by Hilton Reynoldsburg Columbus East | `/pet-friendly-hotels/home2-suites-by-hilton-reynoldsburg-columbus-east/` | `/pet-friendly-hotels/columbus-oh/home2-suites-by-hilton-reynoldsburg-columbus-east/` |
| hotel: Home2 Suites New Albany Columbus | `/pet-friendly-hotels/home2-suites-new-albany-columbus/` | `/pet-friendly-hotels/columbus-oh/home2-suites-new-albany-columbus/` |
| hotel: Homewood Suites by Hilton Columbus Dublin | `/pet-friendly-hotels/homewood-suites-by-hilton-columbus-dublin/` | `/pet-friendly-hotels/columbus-oh/homewood-suites-by-hilton-columbus-dublin/` |
| hotel: Homewood Suites by Hilton Columbus-Hilliard | `/pet-friendly-hotels/homewood-suites-by-hilton-columbus-hilliard/` | `/pet-friendly-hotels/columbus-oh/homewood-suites-by-hilton-columbus-hilliard/` |
| hotel: Homewood Suites by Hilton Columbus/OSU, OH | `/pet-friendly-hotels/homewood-suites-by-hilton-columbus-osu-oh/` | `/pet-friendly-hotels/columbus-oh/homewood-suites-by-hilton-columbus-osu-oh/` |
| hotel: Homewood Suites by Hilton Columbus/Polaris, OH | `/pet-friendly-hotels/homewood-suites-by-hilton-columbus-polaris-oh/` | `/pet-friendly-hotels/columbus-oh/homewood-suites-by-hilton-columbus-polaris-oh/` |
| hotel: Hotel LeVeque, Autograph Collection | `/pet-friendly-hotels/hotel-leveque-autograph-collection/` | `/pet-friendly-hotels/columbus-oh/hotel-leveque-autograph-collection/` |
| hotel: Hyatt Place Columbus OSU | `/pet-friendly-hotels/hyatt-place-columbus-osu/` | `/pet-friendly-hotels/columbus-oh/hyatt-place-columbus-osu/` |
| hotel: Hyatt Regency Columbus | `/pet-friendly-hotels/hyatt-regency-columbus/` | `/pet-friendly-hotels/columbus-oh/hyatt-regency-columbus/` |
| hotel: La Quinta Columbus West-Hilliard | `/pet-friendly-hotels/la-quinta-columbus-west-hilliard/` | `/pet-friendly-hotels/columbus-oh/la-quinta-columbus-west-hilliard/` |
| hotel: La Quinta Inn & Suites by Wyndham Columbus - Grove City | `/pet-friendly-hotels/la-quinta-inn-suites-by-wyndham-columbus-grove-city/` | `/pet-friendly-hotels/columbus-oh/la-quinta-inn-suites-by-wyndham-columbus-grove-city/` |
| hotel: La Quinta Inn by Wyndham Columbus Dublin | `/pet-friendly-hotels/la-quinta-inn-by-wyndham-columbus-dublin/` | `/pet-friendly-hotels/columbus-oh/la-quinta-inn-by-wyndham-columbus-dublin/` |
| hotel: La Quinta Inn by Wyndham Columbus I-70E/Reynoldsburg | `/pet-friendly-hotels/la-quinta-inn-by-wyndham-columbus-i-70e-reynoldsburg/` | `/pet-friendly-hotels/columbus-oh/la-quinta-inn-by-wyndham-columbus-i-70e-reynoldsburg/` |
| hotel: Red Roof PLUS+ Columbus Downtown Convention Center | `/pet-friendly-hotels/red-roof-plus-columbus-downtown-convention-center/` | `/pet-friendly-hotels/columbus-oh/red-roof-plus-columbus-downtown-convention-center/` |
| hotel: Red Roof PLUS+ Columbus Worthington | `/pet-friendly-hotels/red-roof-plus-columbus-worthington/` | `/pet-friendly-hotels/columbus-oh/red-roof-plus-columbus-worthington/` |
| hotel: Renaissance Columbus Downtown Hotel | `/pet-friendly-hotels/renaissance-columbus-downtown-hotel/` | `/pet-friendly-hotels/columbus-oh/renaissance-columbus-downtown-hotel/` |
| hotel: Residence Inn by Marriott Columbus Dublin | `/pet-friendly-hotels/residence-inn-by-marriott-columbus-dublin/` | `/pet-friendly-hotels/columbus-oh/residence-inn-by-marriott-columbus-dublin/` |
| hotel: Residence Inn Columbus Airport | `/pet-friendly-hotels/residence-inn-columbus-airport/` | `/pet-friendly-hotels/columbus-oh/residence-inn-columbus-airport/` |
| hotel: Residence Inn Columbus Easton | `/pet-friendly-hotels/residence-inn-columbus-easton/` | `/pet-friendly-hotels/columbus-oh/residence-inn-columbus-easton/` |
| hotel: Residence Inn Columbus OSU | `/pet-friendly-hotels/residence-inn-columbus-osu/` | `/pet-friendly-hotels/columbus-oh/residence-inn-columbus-osu/` |
| hotel: Sheraton Suites Columbus Worthington | `/pet-friendly-hotels/sheraton-suites-columbus-worthington/` | `/pet-friendly-hotels/columbus-oh/sheraton-suites-columbus-worthington/` |
| hotel: Sonesta Columbus Downtown | `/pet-friendly-hotels/sonesta-columbus-downtown/` | `/pet-friendly-hotels/columbus-oh/sonesta-columbus-downtown/` |
| hotel: Sonesta Simply Suites Columbus Airport Gahanna | `/pet-friendly-hotels/sonesta-simply-suites-columbus-airport-gahanna/` | `/pet-friendly-hotels/columbus-oh/sonesta-simply-suites-columbus-airport-gahanna/` |
| hotel: Sonesta Simply Suites Dublin Columbus | `/pet-friendly-hotels/sonesta-simply-suites-dublin-columbus/` | `/pet-friendly-hotels/columbus-oh/sonesta-simply-suites-dublin-columbus/` |
| hotel: SpringHill Suites by Marriott Columbus Dublin | `/pet-friendly-hotels/springhill-suites-by-marriott-columbus-dublin/` | `/pet-friendly-hotels/columbus-oh/springhill-suites-by-marriott-columbus-dublin/` |
| hotel: Staybridge Suites Columbus Dublin | `/pet-friendly-hotels/staybridge-suites-columbus-dublin/` | `/pet-friendly-hotels/columbus-oh/staybridge-suites-columbus-dublin/` |
| hotel: Staybridge Suites Columbus Polaris by IHG | `/pet-friendly-hotels/staybridge-suites-columbus-polaris-by-ihg/` | `/pet-friendly-hotels/columbus-oh/staybridge-suites-columbus-polaris-by-ihg/` |
| hotel: The Plaza Hotel Columbus at Capitol Square | `/pet-friendly-hotels/the-plaza-hotel-columbus-at-capitol-square/` | `/pet-friendly-hotels/columbus-oh/the-plaza-hotel-columbus-at-capitol-square/` |
| hotel: The Westin Great Southern Columbus | `/pet-friendly-hotels/the-westin-great-southern-columbus/` | `/pet-friendly-hotels/columbus-oh/the-westin-great-southern-columbus/` |
| hotel: TownePlace Suites by Marriott Columbus North - OSU | `/pet-friendly-hotels/towneplace-suites-by-marriott-columbus-north-osu/` | `/pet-friendly-hotels/columbus-oh/towneplace-suites-by-marriott-columbus-north-osu/` |
| hotel: TownePlace Suites Columbus Airport Gahanna | `/pet-friendly-hotels/towneplace-suites-columbus-airport-gahanna/` | `/pet-friendly-hotels/columbus-oh/towneplace-suites-columbus-airport-gahanna/` |
| hotel: TownePlace Suites Columbus Dublin | `/pet-friendly-hotels/towneplace-suites-columbus-dublin/` | `/pet-friendly-hotels/columbus-oh/towneplace-suites-columbus-dublin/` |
| hotel: TownePlace Suites Columbus Easton Area | `/pet-friendly-hotels/towneplace-suites-columbus-easton-area/` | `/pet-friendly-hotels/columbus-oh/towneplace-suites-columbus-easton-area/` |
| hotel: Tru by Hilton Columbus East Broad | `/pet-friendly-hotels/tru-by-hilton-columbus-east-broad/` | `/pet-friendly-hotels/columbus-oh/tru-by-hilton-columbus-east-broad/` |

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
