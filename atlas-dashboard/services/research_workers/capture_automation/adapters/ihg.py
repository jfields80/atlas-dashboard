"""IHG (Staybridge, Holiday Inn, Candlewood, ...).

Derived from a supervised discovery session against the real Staybridge Suites
Columbus-Dublin page, not from guesswork:

* **Identity is strong.** One JSON-LD ``Hotel`` block carries the name,
  telephone and street address, and the property code is a bare path segment
  (``/staybridge/hotels/us/en/dublin/cmhtc/hoteldetail``) that
  ``extract_property_code_from_url`` already handles via its ``hoteldetail``
  branch. Nothing new is needed for either.

* **The policy lives in an FAQ accordion, two clicks deep.** The page renders
  only the first three FAQ items; items four through eleven -- the pet question
  is the eleventh -- have zero width and height until "READ MORE FAQS" is
  clicked. Only then does clicking the pet question reveal its panel. Measured:
  rendered text goes 3,969 -> 4,490 -> 4,804 bytes across those two clicks, and
  the policy is absent from ``innerText`` until the second.

* **The panel's ``aria-controls`` is a dead reference.** The button advertises
  ``aria-controls="sect10"`` and no element with that id exists;
  ``document.getElementById('sect10')`` returns null. The panel is a sibling
  ``div[data-cmp-hook-accordion="panel"]`` carrying ``aria-labelledby`` back to
  the button. Anything keyed on ``aria-controls`` here silently finds nothing.

* **The wording is prose, and cheaper than it looks.** Staybridge Dublin reads:
  "This is a dog only hotel. Up to two friendly pups under 80 lbs are welcome.
  Pet fee per pet is 75 to 150 dollars depending on length of stay". Note there
  is no dollar SIGN -- amounts are spelled "75 to 150 dollars" -- so the core
  scorer's money pattern does not fire and the brand anchors below are what
  carry the block over the confidence threshold.
"""

from __future__ import annotations

from typing import Tuple

from .base import BaseAdapter


class IhgAdapter(BaseAdapter):
    brand = "ihg"

    # The core list contributes "Pet Policy" (matched inside "Our Pet Policy:")
    # and the weak "Pets". These are the phrases IHG's prose actually uses, and
    # they are what lifts a block with no dollar sign in it above LOW.
    extra_anchors: Tuple[str, ...] = (
        "Our Pet Policy",
        "Pets are welcome at",
        "Pet fee per pet",
        "dog only hotel",
        "Can I bring my pet",
    )

    # Deliberately EMPTY, so the policy is addressed by its text.
    #
    # IHG's accordion panels are indistinguishable from one another:
    # `div[data-cmp-hook-accordion="panel"]` matches all eleven FAQ answers,
    # and `.cmp-accordion__panel` likewise. Offering either as the container
    # made the runner scroll to and measure the FIRST panel -- a collapsed
    # parking answer with zero height -- and the hotel failed
    # POLICY_OFF_SCREEN at 0.00 visible while the pet policy sat open further
    # down the page. The buttons advertise `aria-controls`, but those ids
    # resolve to nothing, so there is no unique selector to offer.
    container_selectors: Tuple[str, ...] = ()

    # Two clicks, in order. The first expands the FAQ list so the pet question
    # is laid out at all; the second opens its panel. Both are ordinary visible
    # controls a reader would click.
    expand_text_controls: Tuple[Tuple[str, str], ...] = (
        ("a.cmp-faq__action", "FAQ"),                       # "READ MORE FAQS"
        ("button.cmp-accordion__button", "bring my pet"),
    )

    # Present only once the property view has rendered; additive readiness hint.
    hydration_identity_selectors: Tuple[str, ...] = (
        "script[type='application/ld+json']",
    )
