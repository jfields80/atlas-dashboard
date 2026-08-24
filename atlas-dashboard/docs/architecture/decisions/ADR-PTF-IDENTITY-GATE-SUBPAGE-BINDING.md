# ADR-PTF-IDENTITY-GATE-SUBPAGE-BINDING — a first-party policy subpage cannot be bound

- **Status:** OPEN FINDING (recorded by PTF-...-FULL-CLOSURE-038, documented by
  PTF-...-FOUNDER-REVIEW-AND-APPROVAL-BINDING-039)
- **Changes nothing.** The identity gate is exactly as it was. Neither work
  order modified `policy_surface.py`, the router's identity assessment, or any
  threshold in it, and a test in
  `tests/pettripfinder/acquisition/test_approval_binding_039.py` fails if 039's
  own change set touches them.
- **Decision required from:** a future work order with its own controls and its
  own regression cohort. Not from a closure pass, and not from a review pass.

## What happened

038 authorised a bounded reacquisition: two Milwaukee properties whose only
persisted capture was a homepage, and whose own sites publish a policy page
that source discovery had already found and no run had ever fetched.

| property | page | outcome |
| --- | --- | --- |
| Knickerbocker on the Lake | `https://www.knickerbockeronthelake.com/faq` | fetched, DECLINED |
| The Iron Horse Hotel | `https://www.theironhorsehotel.com/dogs/` | fetched, DECLINED |

Both fetches succeeded. Both pages carry the real policy — Iron Horse states a
$100 per-night dog fee under a "DOGS WELCOME" heading; Knickerbocker states
that only ADA service animals are allowed. Both were declined by the router's
identity gate with `IDENTITY_MISMATCH`, and so neither became an observation.

## Why

The gate asks for a PHYSICAL agreement between the census identity and the
page: a street address, a telephone number, or JSON-LD naming the property. It
exists because a capture can silently land on the wrong hotel — a brand search
page, a sibling property, a redirect — and a name alone is a weak signal on a
domain like `marriott.com`, where every property's page carries every other
property's brand.

A policy SUBPAGE of an independent hotel's own site has none of those. `/dogs/`
has a title, a heading, and prose. The address lives on `/contact`. So the gate
reports `nothing physical agreed` and declines.

The result is the inversion worth recording:

> A page on the registrable domain that the census itself names as the
> property's official URL is refused for lacking a weaker binding than the one
> it already has.

For an independent hotel, the domain **is** the identity. It is the strongest
signal available, and the gate does not count it, because the rule was written
for brand hosts where a domain binds nothing.

## Why it was not fixed in place

Three reasons, in order of weight.

1. **A closure pass is the wrong place to weaken an identity rule.** Publishing
   the wrong hotel's pet policy is the most expensive error this system can
   make, and identity is the only thing standing between a capture and that
   error. A rule relaxed to admit two properties at the end of a market is a
   rule relaxed without a cohort to test it against.
2. **The narrow fix is not obviously narrow.** "Same registrable domain as the
   census official URL" sounds tight until the census URL is itself a brand
   host, an aggregator, or a chain microsite — in which case the rule admits
   every property on it. Distinguishing an independent's own domain from a
   brand host is a real classification problem, not a conditional.
3. **A founder can bind an identity; a parser cannot.** The evidence is
   persisted, the decline is recorded on the row, and both properties appear in
   the 039 founder-review package with the decline stated and **no proposed
   facts**. That is the governance path the system already has, and it was
   used.

## What a repair would need

- An explicit, testable definition of "the property's own domain", separating
  an independent's registrable domain from a brand or aggregator host, with the
  brand list derived rather than enumerated by hand.
- A regression cohort of pages that MUST still be declined — a sibling property
  on the same brand host, a search-results page, a redirect to a chain landing
  page — proving the relaxation does not admit them.
- A statement of what the binding rests on when it is the domain: probably the
  census's own `official_url` plus a name agreement, with the census URL itself
  treated as the attestation.
- Retention of the decline as a first-class outcome. A page admitted this way
  is bound by a weaker signal than an address match, and any record built on it
  should say so.

Until that exists, a declined page stays declined, and its evidence reaches a
human with the decline visible rather than reaching authority quietly.
