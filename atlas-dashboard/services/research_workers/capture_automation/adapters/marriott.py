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
it five ways. What it needs is the right container to scroll to, because the
block sits 1,800-3,000 characters down a long page and the screenshot is the
part that fails without help.
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

    container_selectors: Tuple[str, ...] = (
        "[data-testid='pet-policy']",
        "#hotel-policies",
        "[data-testid='property-policies']",
        ".policies-section",
    )

    # Marriott renders the pet block inline on the overview page, so there is
    # usually nothing to expand. These cover the variant where policies sit
    # behind a "More" control.
    expand_selectors: Tuple[str, ...] = (
        "button[data-testid='view-more-policies']",
        "button[aria-controls='hotel-policies']",
    )
