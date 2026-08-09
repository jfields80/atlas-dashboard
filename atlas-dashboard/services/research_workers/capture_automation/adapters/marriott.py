"""Marriott.

Observed across eleven real captures in the retained corpus, every one of them
a ``/en-us/hotels/<code>-<slug>/overview/`` page:

  * The block always opens "Pet Policy" then "Pets Welcome", then free prose,
    then the labelled fields ("Non-Refundable Pet Fee Per Stay: $75.00",
    "Maximum Pet Weight: 40.0lbs", "Maximum Number of Pets in Room: 2").
  * It always terminates at "Parking".
  * JSON-LD carries a Hotel block with name, telephone and a full postal
    address -- the strongest identity evidence of any brand we handle.
  * The canonical URL equals the final URL and is clean.

So Marriott needs almost nothing brand-specific: the core anchors already hit
it five ways.

PTF-COLUMBUS-SELECTOR-CLOSEOUT-001 measured two things that changed the rest
of this file.

**There are two Marriott property templates, and only one of them paints the
policy by itself.** All eleven corpus pages -- and Residence Inn Columbus
Polaris, captured again in the closeout run -- carry an always-visible "HOTEL
INFORMATION" band (``div.hotel-info__column``, the pet column marked
``span.icon-pet-friendly``). Le Meridien Columbus, The Joseph carries **zero**
of those: no ``hotel-info__column``, no "HOTEL INFORMATION" anywhere in the
served HTML. The same content lives instead inside a property-details
accordion, ``.property-details.hotel-info.column-wise > .accordion-content``,
behind ``button.faq-accordion-faq-question`` labelled "Hotel Information".
That body is in the HTML and absent from ``innerText``, so the locator saw only
the accordion's own button labels -- "Pet Policy / Smoke-Free Policy / Cash
Free / Community Fee Notice / Our History" -- scored the marketing prose that
followed them at 12, and returned a policy block containing no policy. One
click is the whole difference.

**The four container selectors this adapter used to declare exist on no
Marriott page we have ever captured.** ``[data-testid='pet-policy']``,
``#hotel-policies``, ``[data-testid='property-policies']`` and
``.policies-section`` are all absent from both closeout DOMs and from the
corpus. They were never load-bearing -- ``_policy_handle`` checks
``query_selector_exists`` and falls back to the policy text -- so removing
them changes no behaviour. Following IHG's precedent, the honest value is
empty rather than a guess, and the observed containers are not offered either:
``.hotel-info__column`` matches three columns and ``.accordion-content``
nineteen, and IHG already paid for measuring the first of many.
"""

from __future__ import annotations

from typing import Tuple

from .base import BaseAdapter


class MarriottAdapter(BaseAdapter):
    brand = "marriott"

    # The core list already covers "Pet Policy", "Pets Welcome", "Maximum Pet
    # Weight" and "Maximum Number of Pets". These are the labelled-field forms
    # that appear only here, and they sharpen the block boundary.
    extra_anchors: Tuple[str, ...] = (
        "Non-Refundable Pet Fee Per Stay",
        "Non-Refundable Pet Fee Per Night",
        "Maximum Number of Pets in Room",
    )

    # Deliberately EMPTY: see the module docstring. No selector Marriott has
    # ever served identifies the pet block uniquely, and the policy text is the
    # primary handle everywhere else in this package.
    container_selectors: Tuple[str, ...] = ()

    # One click, on an ordinary visible accordion control a reader would click.
    # Addressed by label because the accordion's ids are per-render
    # (``accordion-body6`` on one page, a hashed id on the next) while its
    # wording is not.
    #
    # Safe on the template that does not need it: the click is optional, the
    # runner re-locates afterwards, and ``_verify_expanded`` asks the locator
    # whether the policy is visible before it ever re-clicks -- so a page whose
    # HOTEL INFORMATION band was already painted keeps the block it had.
    expand_text_controls: Tuple[Tuple[str, str], ...] = (
        ("button.faq-accordion-faq-question", "Hotel Information"),
    )
