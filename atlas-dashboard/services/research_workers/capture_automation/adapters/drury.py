"""Drury.

No longer provisional. PTF-COLUMBUS-FINAL-CLOSURE-001 registered the brand and
got a Drury page in front of this package for the first time; the retained
rendered DOM from that run (Drury Plaza Hotel Columbus Downtown,
``rendered_dom.html``, 439,411 bytes) is what every value below is read off.

* **The policy is real, property-specific, and shut.** It sits in a Bootstrap
  dialog, ``#additional-info-modal``, whose single ``div.policies`` holds a run
  of ``p.policy-title`` headings and their values. The dialog carries
  ``aria-hidden="true"`` on arrival, so none of it reaches ``innerText`` and the
  run terminated POLICY_NOT_FOUND with the identity gate already CONFIRMED.

* **It is the property talking, not the brand.** The same ``div.policies``
  states "Number of rooms: 180" and "On-site covered parking: $24 per night",
  and the page's own property payload carries ``ParkingFee: 24.00``. Its pet
  wording -- "Dogs and cats accepted. Rooms with pets will be charged a daily
  fee of $50 per room plus tax. Service animals are free of charge. Limit of
  two pets per room with a combined weight of 80 pounds." -- is the wording
  already quoted in the published records for the Dublin, Polaris and Grove
  City Drurys, which is corroboration this container is the one the brand
  actually authors policy in.

* **The dialog opens from a visible link.** ``section.policies-section`` holds
  ``a.section-text-link[data-target="#additional-info-modal"]`` labelled "SHOW
  MORE HOTEL INFO" -- an ordinary control a reader would click, addressed by
  its own text so the runner's expansion check can confirm the dialog opened
  and re-click once if it did not.

* **The block has to be stopped at "Payment Policy".** ``div.policies`` runs
  the pet paragraph straight into "Payment Policy", then "Guests Per Room:
  Maximum of five (5) people in a standard room or up to six (6) in a suite",
  then "Rollaways are available for $15 per day". Measured on the retained DOM,
  the unterminated excerpt is 599 characters and carries a people count and a
  nightly dollar amount belonging to neither pets nor this policy. Terminating
  cuts it to the paragraph the heading introduces.
"""

from __future__ import annotations

from typing import Tuple

from .base import BaseAdapter


class DruryAdapter(BaseAdapter):
    brand = "drury"

    #: Unique on the page: one dialog, one ``.policies`` inside it. Unlike
    #: IHG's accordion panels there is nothing else for this to match, so it is
    #: safe to offer as a scroll and measurement target.
    container_selectors: Tuple[str, ...] = (
        "#additional-info-modal .policies",
    )

    #: One click, on the visible link that opens the dialog.
    expand_text_controls: Tuple[Tuple[str, str], ...] = (
        ("a.section-text-link[data-target='#additional-info-modal']",
         "SHOW MORE HOTEL INFO"),
    )

    #: Where the pet paragraph ends. Narrowing only -- see the docstring.
    extra_terminators: Tuple[str, ...] = (
        "Payment Policy",
    )

    #: Present once the property view has rendered; additive readiness hint only.
    hydration_identity_selectors: Tuple[str, ...] = (
        "script[type='application/ld+json']",
    )
