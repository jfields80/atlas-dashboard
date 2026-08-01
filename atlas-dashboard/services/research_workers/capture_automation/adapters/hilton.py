"""Hilton.

Harder than Marriott, in three specific ways the retained corpus makes plain:

1. **The policy often carries no anchor phrase.** Hampton Columbus Airport
   states its entire pet policy as ``$75(1-4n)$125(5+n)2pet Max dog/cat only``
   under the heading "Other pet information". Home2 Suites New Albany says
   ``1-4 night stay $50; 5+ night stay $75; 2 pets max; dog or cat only``.
   Neither line contains the word "pet fee", "per night" or a dollar label the
   core scorer would recognise as strong.

2. **Titles go stale.** The property page for
   ``cmhcagi-hilton-garden-inn-columbus-airport`` carries the page title
   "Embassy Suites by Hilton Columbus Airport". JSON-LD has it right. Anything
   that trusted ``<title>`` would mislabel that hotel, so identity here leans
   entirely on JSON-LD and the URL -- which the base adapter already does.

3. **Pages render thin.** Hilton property pages produce 2.3-3.8 KB of
   ``innerText`` against 500-690 KB of HTML. That clears
   ``MIN_USEFUL_TEXT_BYTES`` (400) comfortably but leaves far less corroborating
   text than Marriott's, so scoring has less to work with.

Hilton also serves two page shapes -- the property root and ``/hotel-info/`` --
and the policy lives in a different structure on each.
"""

from __future__ import annotations

from typing import Tuple

from .base import BaseAdapter


class HiltonAdapter(BaseAdapter):
    brand = "hilton"

    # "Other pet information" and "Pets allowed" are in the core list; these
    # are the surrounding labels Hilton's policy table uses, and they are what
    # gives the compressed tier notation enough context to score.
    extra_anchors: Tuple[str, ...] = (
        "Non-refundable Fee",
        "Max weight",
        "Max size",
        "Deposit",
        "Service animals",
    )

    container_selectors: Tuple[str, ...] = (
        "[data-testid='policies-pets']",
        "#policies",
        "[data-osc-product='policies']",
        ".policy-table",
    )

    expand_selectors: Tuple[str, ...] = (
        "button[data-testid='all-policies']",
    )

    # The pet policy lives in a tab panel that ships as `class="w-full hidden"`
    # (display:none) and enters innerText only after its tab is clicked. On
    # Hampton Columbus Airport that tab is `#policies-tab-1`, but the index
    # varies by property while the label does not -- so the durable handle is
    # the word "Pets" on a button wired to a policies tab panel.
    #
    # Without this the policy is present in the HTML and absent from the
    # rendered text, which is precisely what POLICY_NOT_FOUND reported for four
    # of five Hilton hotels in the first pilot run.
    expand_text_controls: Tuple[Tuple[str, str], ...] = (
        ("button[aria-controls^='tab-panel-policies-tab']", "Pets"),
        ("button[role='tab']", "Pets"),
    )
