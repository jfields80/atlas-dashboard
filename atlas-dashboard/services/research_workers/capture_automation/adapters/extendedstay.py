"""Extended Stay America.

Still selector-free, but no longer for want of evidence. Keeping it empty is
now a finding, and this docstring is where that finding is recorded so nobody
re-derives it or, worse, wires up the container it warns about.

PTF-COLUMBUS-FINAL-CLOSURE-001 reached the Columbus-Dublin property page and
the identity gate CONFIRMED it on address and phone from the page's own
structured data. PTF-COLUMBUS-SELECTOR-CLOSEOUT-001 then read the retained DOM
(``rendered_dom.html``, 749,956 bytes) looking for the policy container the
locator had missed. There is not one.

* **The page has exactly one policies container**, ``#servicesAndPoliciesModal``,
  and it is chain-wide legal text. It opens "Site User Agreement -- Your use of
  any of Extended Stay America's websites (this 'Site') is governed by the
  following terms and conditions", and runs through Fees And Other Charges,
  Payment Policy, Incidental Costs, Checking In, Housekeeping (described per
  BRAND tier, "Extended Stay America Suites and Extended Stay America Select
  Suites"), Pet Policy and Coupons. Not one value in it belongs to this
  property. Contrast Drury, whose equivalent dialog states this hotel's room
  count and this hotel's parking rate.

* **Its pet numbers are a ceiling, not a price.** "There will be **up to** a
  $25 (+ tax) per day non-refundable cleaning fee for the first six (6)
  nights, per pet. Each day thereafter there is a pet cleaning fee **not to
  exceed** $15 ... Larger animals or more than two pets requires property
  manager's approval. **Please contact the property for questions.**" The
  Fees And Other Charges section says it in as many words: "Questions
  regarding specific fees and other charges applicable to your reservation
  should be directed to your destination hotel."

* **The property's own content asserts an amenity and nothing more.** Every
  ``esa-property-*`` region -- hero, rooms, amenities, FAQ -- says only
  "Pet-friendly room" / "offers pet-friendly rooms". There is no
  ``esa-property-*polic*`` class on the page at all.

So a selector pointed at ``#servicesAndPoliciesModal`` would publish a brand
default as a property fact and a rate ceiling as a rate. Both are things this
system exists to refuse, and the recorded POLICY_CONFLICT for Columbus-Dublin
stands until either the brand states a property figure or the fee schema can
carry a ceiling honestly.

The class therefore still asserts only that the brand may be ATTEMPTED, under
the core anchors and the core locator with no narrowing.
"""

from __future__ import annotations

from .base import BaseAdapter


class ExtendedStayAdapter(BaseAdapter):
    brand = "extendedstay"
