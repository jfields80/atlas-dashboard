# PTF-NASHVILLE-TN-NEW-MARKET-001 — final report

Greater Nashville, Tennessee, built from no prior authority to an
evidence-bound shadow market and stopped at the serialized promotion boundary.

**Nashville is NOT registered.** Production is unchanged at eleven live
markets, 803 profiles and 966 routes on deploy `6a9e047690ec8bdaf99bcad2`.
Detroit keeps the serialized launch lane. Nothing was promoted, assembled,
authorized or deployed.

    base commit        d335c509e8e4b0f54796d07c4bd4abdff00cb801
    census             181 confirmed identities
    clean pet-friendly 80
    clean no-pets      19
    resolved           99      unresolved 82
    founder packet     25 grouped items, six groups, 0 promotion blockers
    PROMOTION_READY    YES
    spend              $0.00 USD; 17 Firecrawl plan credits (459 -> 442)

---

## GEOGRAPHY

Nineteen corridors. Thirty-one admitted postal codes, each claimed by exactly
one corridor, so a hotel is never placed by mailing city — "Nashville" is the
mailing city of Antioch, Hermitage, Bellevue, Donelson, Green Hills and Old
Hickory alike and decides nothing here.

**Two corridors a postal partition cannot express.** ZIP 37214 carries both the
Donelson/BNA airport cluster and the Gaylord Opryland cluster four miles north;
ZIP 37203 carries the Gulch, Midtown, Music Row and the West End spine. Each
gets a corridor that claims NO postal code and names its properties explicitly,
derived from the STREET each property's own page states — Music Valley Drive,
Opryland Drive, Music City Circle and Rudy Circle for Opryland; West End
Avenue, Hayes Street and 29th Avenue North for Vanderbilt. Membership is
untouched. Only display moves, at tier 2 of the one assignment authority, which
outranks the tier-3 ZIP match. McGavock Pike was considered and deliberately
excluded: it runs from the airport terminal to Opry Mills and carries hotels of
both kinds, and a street that spans two districts cannot decide either.

**The fringe was held, not guessed.** Five corridors exist claiming no postal
code at all — Franklin/Cool Springs, Mount Juliet, Hendersonville, Smyrna/La
Vergne and Lebanon. Their hotels were discovered, identified, routed and read,
and then classified `OUTSIDE_MARKET` on the postal code they state. That is the
point: the founder rules on an inventory that was looked at, and each ruling is
a one-line move of postal codes.

What the holds are worth, measured: of the 61 attended reads classified
OUTSIDE_MARKET, **35 sit in a HELD postal code** and 26 sit in a town this
market excludes outright (Murfreesboro, Gallatin, White House, Memphis,
Dyersburg, Martin, Union City and Franklin, Kentucky). **Zero** outside-market
reads fall in an admitted ZIP. So the founder is not being asked an abstract
question: the packet states, per corridor, the inventory each ruling admits.

Two fringe areas ARE admitted, on first-party evidence rather than assumption.
Brentwood (37027) is contiguous with Davidson County at I-65 and its operators
name their own properties `Nashville Brentwood` five separate times in
Marriott's published roster. Goodlettsville (37072) sits on a ZIP that
STRADDLES the Davidson/Sumner county line. Both are founder item B6 for
confirmation.

The discovery box is deliberately larger than the market and reaches every held
town, because a hold whose inventory was never fetched is an omission dressed
as a hold.

## THE LADDER, RUNG BY RUNG

| rung | what it cost | what it produced |
|---|---|---|
| 0 OWNED | 0 requests, $0 | 70 Marriott BNA leads, already in the committed Dayton harvest |
| 1 LOCAL FREE | 1 extract download + 2 Overpass | 308 OSM candidates; 163 of them carry a website |
| 1 BRAND CITY PAGE | 53 requests | Hilton's 60 BNA codes from 16 city pages; Drury and WoodSpring routes |
| 2 BRAND SITEMAP | 188 requests | 55 routes: Wyndham 48, Sonesta 5, Omni 1, Loews 1 |
| 2 LEADS | 213 requests | 349 BringFido hotel leads, 123 destination-org lodging leads |
| 3 STATIC | 164 requests | 9 VALID; 117 walled |
| 4 FIRECRAWL | 17 attempts, 17 credits, $0 | 15 publication-grade, 2 failed, 0 unbound |
| 5 ATTENDED | 154 pages, TWO navigations, $0 | 154 identity-confirmed, 93 in market |

Total free HTTP requests: 618. Paid provider calls: 0. USD: $0.00.

The public Overpass API answered two of fifty-eight cells and then rate-limited
every approved mirror into a fifteen-minute cooldown. The lane moved to a
Geofabrik Tennessee extract, md5-verified against the publisher's own checksum
and reduced to this market's bounding box, which answered every remaining cell
offline. That is Lexington's rule followed: register the extract before leaning
on Overpass.

## WHAT THE DISCIPLINE CAUGHT

**A code selects; the page admits.** BNA is the Nashville AIRPORT code and it
reaches Clarksville, Cookeville, Columbia, Murfreesboro, Manchester, Tullahoma,
Hopkinsville KY and Bowling Green KY. The sharpest case is `bnafs`: Marriott's
own roster slugs it `springhill-suites-franklin-mint`, its code carries the
Nashville prefix, and its street is literally **5629 Nashville Rd**. Three
signals point at this market. Its own page states Franklin, **KENTUCKY** 42134,
and that is what decided.

**A locality token is not a place.** The same roster carries a Brentwood in Los
Angeles and another in Mussoorie, INDIA; an Antioch in Pittsburg, CALIFORNIA; a
Hendersonville in Flat Rock, NORTH CAROLINA; and a Mount Juliet estate in
JAMAICA. All dropped by name with the reason recorded.

**A brand URL that states a state settles a token.** The first pass of the
owned-evidence scan produced three non-Marriott "Nashville leads" and all three
were Franklin, **OHIO**.

**Serving robots.txt is not serving a sitemap.** IHG, Choice, Red Roof, Motel 6
and Radisson each answered robots.txt WITH a sitemap URL and then refused that
very sitemap to the same client seconds later. Recorded as a refusal by this
client at this moment — never as silence, and never as a closure.

**A directory URL is never a route.** The map source states
`choicehotels.com/tennessee/white-house/quality-inn-hotels` for a hotel that is
in Nashville: a brand town index, and the wrong town. Rejected before capture.

**The competitor's category filter is live, and it mattered.** BringFido's
unfiltered path returned 399 rows and its `/hotels/` path 245, with 250 rows in
the first that are not in the second — "Hart Suite 8 by Avantstay", "2BR Urban
Bungalow", "Mid Century Luxe Boutique Condo Near Broadway". Those are
short-term rentals. The filtered path supplies the leads; the unfiltered cohort
is kept only as the measurement that proves it.

**A BringFido city page serves a RADIUS, not a city.** Antioch's page states 5
results and serves the same 399 rows as Belle Meade's, which states 0. The
headline count and the served cohort are recorded as two different facts, and
twenty redundant walks of one cohort were not performed.

**A brand's own URL path is not evidence of geography either.** WoodSpring
files `woodspring-suites-hermitage-nashville-airport` under a `/chattanooga/`
path segment. The page's own address — 1415 Princeton Place, 37076 — is
Hermitage, and that is what admitted it. Nothing here reads a city out of a URL
path; the one rule that reads a URL segment as a city is scoped to a single
brand whose taxonomy was validated against this market's own data first.

**Marriott ships a translation table containing the string being searched for.**
Its pages render the Pet Policy label in two different markup shapes AND carry
an i18n dictionary with `"hws.petPolicy":"Pet Policy"`. The read anchors on a
CLOSING TAG, which the dictionary entry has none of. A looser search would have
published a translation table as a hotel's policy.

## FIVE DEFECTS FOUND AND FIXED IN THIS ORDER'S OWN PIPELINE

1. **A state name was truncated, not normalised.** Marriott writes
   `Tennessee`; the reader took the first two characters, produced `TE`, and
   membership read an unrecognised state as affirmative evidence of being
   elsewhere. **Twenty real Nashville hotels** were classified
   `OUTSIDE_MARKET`. Fixed with a state-code normaliser that returns "" — not a
   guess — for anything it does not recognise.
2. **A same-brand collision counted addressless leads.** The rule demotes a
   same-brand, same-city PAIR to review; it was counting name-only lead rows as
   the second half of the pair. **Forty-seven fully addressed,
   identity-confirmed hotels** were demoted because a BringFido row spelled the
   same name. Narrowed to nodes that state a street or a phone.
3. **The Hilton attended rows carried no name.** The census kept
   OpenStreetMap's bare `Hilton Garden Inn` and `Hampton Inn & Suites`, two
   identities collided on a bare brand label at different addresses, and both
   were demoted — taking their clean reads with them. The rows now carry the
   name each page states.
4. **An HTML entity reached an identity key.** A Firecrawl read returned
   `Holiday Inn Express &amp; Suites` and `normalize_name` turned that into
   `holiday inn express andamp suites`, a key no other lane can meet, so one
   building opened a second row. Entities are now decoded at the observation
   door, once, for every lane.
5. **Backspace bytes in regex literals.** A shell here-document collapsed `\b`
   into a single 0x08 byte in two of this order's own modules. Repaired, and
   every file re-scanned.

## A FINDING FILED, NOT FIXED

`tests/pettripfinder/test_toledo_oh_new_market_001.py:453` carries the same
0x08 corruption in the committed Toledo gate module:

```
assert not re.search(r"<BS>we (asked|were told|searched)<BS>", r["exact_quote"], re.I)
```

A pattern containing a literal backspace can never match hotel prose, so
`assert not re.search(...)` passes unconditionally. That gate reads as a check
and is not one. **It was not edited.** It belongs to another market's closed
order, and the factory freeze rule says a market order files the finding rather
than touching shared or foreign code. The Nashville copy of the same gate is
repaired.

## POLICY, AUDITED

110 reads across three lanes — 91 attended, 13 Firecrawl, 6 static. After the
wrong-evidence audit: **80 clean pet-friendly, 19 clean verified-no-pets, 11
held.**

Held by class — a read can carry more than one, so these sum above eleven: 6
`IDENTITY_UNRESOLVED_BY_THE_MERGE`, 5 `TWO_PROPERTIES_READ_ONTO_ONE_IDENTITY`,
5 `NOT_IN_THE_PROPOSED_CENSUS` (four of them WoodSpring rows in Clarksville,
Lebanon, Murfreesboro and Smyrna — correctly outside).

Two in-market pages state no operative pet policy at all: Marriott's `bnama`
publishes no Pet Policy row and Hilton's `bnaleci` ships no `petsInfo` node.
Both are identity-confirmed and both contribute nothing in either direction.
Source silence is not a refusal and it is not an acceptance.

Two Nashville Fairfields state ADA service animals only. Both are read as
`pets_allowed: false`. The service-animal sentence every Hilton row carries is
stored separately and never turns a refusal into an acceptance.

## COMPETITOR GAP

348 competitor rows observed, 104 also seen by a first-party lane, 244
competitor-only. **Zero competitor-only rows are true hotel identities**: 199
are name-only and unresolved, 39 are short-term rentals, 6 are identity
reviews. No competitor row entered authority on competitor evidence, and no
competitor pet claim was read as policy.

## PAID READINESS

Nothing is required for promotion. Both shared ledgers were READ and neither
was written; Nashville has zero rows in either, so there is no double-buy risk.
Bright Data and Places are UNQUOTED: no call has been made for this market and
no rate may be carried over from another market's run. Firecrawl's residual
cohort is zero — the measured 17 were attempted and 15 landed.

## REGRESSION

The delta classifier was run rather than reasoned about, and its verdict is
reported as it came:

```
python -m scripts.pettripfinder.regression_delta classify --base d335c50
FULL_REGRESSION_REQUIRED:  YES
```

It classifies by PATH and cannot know that every Nashville path is new and
unregistered, so a proposed census reads as `AUTHORITY_CHANGE` and a proposed
contract reads as `UNCLASSIFIED`. Its own rule is that uncertainty costs the
full suite until somebody teaches it otherwise, and teaching it is a shared-code
edit this order will not make. **This order ran the market-local lanes the work
order specifies and did not run a broad regression**, on a 16 GB machine, per
the order's own instruction. That gap is stated here rather than papered over:
the promotion order, which touches production, owes the broad run.

**The market's own gates run in no lane.** `regression_lanes.MARKET_PREFIXES`
maps a test-module prefix to a market, and Nashville is not in it, so
`--market nashville-tn` selects only the per-market contract modules. That is
the established shape, not an oversight: the table's own comment records
`toledo-oh` being added by the PROMOTION order. The Nashville gate module was
therefore run DIRECTLY and recorded as its own lane, so no `market_targeted`
total is allowed to imply those gates ran inside it.

Lane results, three runs. Run 1 is pre-fix; runs 2 and 3 are post-fix and are
compared by failure-set IDENTITY, never by count.

| lane | run 1 (pre-fix) | run 2 | run 3 |
|---|---|---|---|
| nashville_gates | not run | 0 | 0 |
| market_targeted | 1 | 0 | 0 |
| policy_schema | 5 | 5 | 5 |
| identity_routing | 14 | 14 | 14 |
| cross_market | 5 | 5 | 5 |
| release_contract | not run | 0 | 0 |

The one market_targeted failure was the suite-derived inventory pin, closed by
the re-pin described above. Every other failing module is one Toledo's
new-market order saw at the same base: `test_identity_binding_027` (a capture
artifact under the gitignored `data/acquisition/` tree that a fresh worktree has
never had), `test_normalization_041`, `test_vocabulary_normalization_043` and
`test_louisville_authority`.

**A self-referential gate, closed by executing it.** One gate in this order's
own module reads the classification report that classifies it. A lane log
captured before the report existed cannot classify such a gate without
circularity: the gate fails because the report says TRUE_NEW, and the report
says TRUE_NEW because the gate failed. It is not waved through. The classifier
publishes the report with that gate set aside, RE-EXECUTES it against the
finished report, and records the verdict. It passed. A failing re-run would
have stayed `TRUE_NEW_FAILURE`.

Run 2 and run 3 produced **identical failure SETS** — `only_in_run_1: []`,
`only_in_run_2: []` — so nothing done between them changed any test's outcome.

`TRUE_NEW_FAILURE = 0`.

## FACTORY SPEED

Nashville is the first LARGE destination market this factory has built from
zero, and the order asked for three to five active hours.

    active minutes    ~125
    target            180 to 300
    census            181
    free HTTP         618
    Firecrawl         17 attempts, 17 credits, $0
    attended          154 pages in TWO navigations
    PROMOTION_READY   YES

**DID NASHVILLE REACH PROMOTION_READY WITHIN 3-5 HOURS? YES**, in about two.

There was no bottleneck, because the two lanes that could have been one were
avoided rather than endured. The public Overpass API answered two of fifty-eight
cells and then rate-limited every approved mirror into a fifteen-minute
cooldown; at that rate the OSM lane alone would have taken hours, so it moved to
a local md5-verified extract and answered the rest offline. And the
Marriott/Hilton wall — 154 property pages, the largest attended cohort this
factory has run — was walked by same-origin fetch batching from one tab per
origin: TWO navigations, not 154.

## PARALLEL SAFETY, PROVED MECHANICALLY

Detroit 0, Lexington 0, Fort Wayne 0, other registered markets 0, shared
globals 0, market registry 0, registered census 0, authority shards 0,
current-state pins 0, deployment files 0, shared ledgers written 0, shared
factory code 0. Production assembly NOT RUN. No deployment authorization.
Nothing deployed. Zero violations across every changed path.

## NEXT

`PTF-NASHVILLE-TN-PROMOTION-AND-APPLICATION-002` is the next serialized order,
and it is NOT started here.

**Nashville must first integrate the then-current deployed canonical lineage.**
This order is pinned to `d335c50`, which was the deployed tip when it began.
Production serves eleven live markets and Detroit holds the serialized launch
lane, so the lineage may have moved underneath this work. Promotion is a MOVE
of two files — `markets/proposed/nashville-tn.json` into `markets/` and
`identity_census_proposed/nashville-tn.json` into `identity_census/` — onto
that integrated base, never a rewrite and never onto this base.
