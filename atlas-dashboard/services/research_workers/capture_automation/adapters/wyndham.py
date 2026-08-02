"""Wyndham (La Quinta, Days Inn, Super 8, Ramada, Baymont, ...).

Derived from a supervised discovery session against the two real Columbus La
Quinta pages, not from guesswork. Wyndham is the most cooperative brand in this
package so far, and also the one whose policy is hardest to *see*.

* **Access is clean.** No bot challenge, no CAPTCHA, no login wall, and -- on
  both properties, measured -- no cookie or consent banner rendered at all.
  ``consent_selectors`` stays empty, as it is for every brand; here it is empty
  because there was nothing to dismiss.

* **Identity is strong.** One JSON-LD ``Hotel`` block per page carries name,
  telephone and street address, all matching the seed. There is no property
  code anywhere in a Wyndham URL -- ``extract_property_code_from_url`` returns
  "" -- and that is fine: ``validate_entry`` does not require one, and identity
  rests on the JSON-LD triple instead.

* **The policy is present, property-specific, and invisible.** ``span
  .pet-policy-desc`` holds the whole policy in the DOM at 0x0 pixels. One click
  on the ordinary visible "Hotel Policies" link (``a[data-target=
  '#hotelPoliciesLightbox']``) opens a lightbox and the block paints: measured
  0x0 -> 449x83 on West-Hilliard and 0x0 -> 455x104 on Dublin. Without that
  click the policy is real, quotable from ``textContent``, and unreadable by a
  human looking at a screenshot -- which PTF-CAPTURE-003E correctly refuses.

* **The two properties state different policies**, which is what proves the
  block is property-scoped rather than brand boilerplate:

      West-Hilliard: "Dogs Allowed - 2 dogs max. 75lbs or less per pet.
                      Fees - 25 USD per pet per night. Max 75 USD per stay."
      Dublin:        "Pets Allowed - 2 pets max. Cats and dogs only. 75lbs or
                      less per pet. Fees - Non-refundable 25 USD nightly for
                      up to 2 pets. Max 75 USD per stay."

  Note the fee bases differ: West-Hilliard charges PER PET per night, Dublin
  charges once nightly for up to two pets. Publishing both as "$25 per night"
  would understate West-Hilliard by half for a two-dog booking, so the
  extractor keeps them apart.

* **Amounts carry no dollar sign.** "25 USD per pet per night" -- the same
  shape as IHG's "75 to 150 dollars". The core scorer's money pattern does not
  fire on it, so the brand anchors below are what carry the block.
"""

from __future__ import annotations

from typing import Tuple
from urllib.parse import urlsplit

from .base import BaseAdapter


class WyndhamAdapter(BaseAdapter):
    brand = "wyndham"

    #: The wording Wyndham's policy block actually uses. "Pet Policy" is in the
    #: core list but never appears contiguously here -- the heading is "Pet &
    #: Service Animal Policy" -- so without these the block scores LOW and is
    #: discarded.
    extra_anchors: Tuple[str, ...] = (
        "Pet & Service Animal Policy",
        "Pet and Service Animal Policy",
        "Service Animals - ADA-defined",
        "Dogs Allowed",
        "Pets Allowed",
        "Other Information - Contact hotel",
    )

    #: The policy region, and only it. Unlike IHG's accordion -- where every
    #: panel shared one selector and the runner measured the wrong one --
    #: `.pet-policy` is unique on these pages: the sibling regions are
    #: `.smoking-policy`, `.parking-policy` and so on, each with its own class.
    #: Verified against both properties rather than one.
    container_selectors: Tuple[str, ...] = (
        "div.policy-items.pet-policy",
        "span.pet-policy-desc",
    )

    #: One click, on an ordinary visible link a reader would click. The lightbox
    #: it opens is what makes the policy paint at all.
    expand_text_controls: Tuple[Tuple[str, str], ...] = (
        ("a[data-target='#hotelPoliciesLightbox']", "Hotel Policies"),
    )

    #: Present once the property view has rendered; additive readiness hint only.
    hydration_identity_selectors: Tuple[str, ...] = (
        "script[type='application/ld+json']",
    )

    def url_is_property_page(self, url: str) -> bool:
        """A Wyndham property page, and never a brand page.

        The base implementation's URL-shape classifier accepts
        ``/laquinta/about-us/pet-friendly`` -- the brand-wide pet page that the
        Dublin retrieval actually landed on and mistook for a property. That
        page describes no single hotel, so capturing it would attribute a brand
        policy to one property. Wyndham marks its brand content with an
        ``/about-us/`` segment, which is a structural fact about the URL rather
        than a list of pages to exclude.
        """
        if not super().url_is_property_page(url):
            return False
        path = (urlsplit(url or "").path or "").lower()
        return "/about-us/" not in path
