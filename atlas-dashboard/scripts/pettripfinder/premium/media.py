"""PetTripFinder — category keys + re-export of the reusable media renderer.

The placeholder-first media system lives in ``scripts.atlas_directory.media``
(keyed by visual family, not domain category). This module exposes the
PetTripFinder category keys the Columbus generator passes around and re-exports
``MediaSpec``/``render_media`` for convenience.
"""

from __future__ import annotations

from scripts.atlas_directory.media import render_media  # noqa: F401
from scripts.atlas_directory.viewmodels import MediaSpec  # noqa: F401

# Opaque PetTripFinder category keys (the generator passes these as the
# ``category`` argument; the delegators resolve the visual family from the
# category *slug* via scripts.pettripfinder.premium.config).
CATEGORY_HOTEL = "hotels"
CATEGORY_PARK = "parks"
CATEGORY_RESTAURANT = "restaurants"
CATEGORY_CITY = "city"
CATEGORY_BRAND = "brand"
