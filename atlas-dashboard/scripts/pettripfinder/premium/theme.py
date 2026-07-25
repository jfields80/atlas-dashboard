"""PetTripFinder — re-export of the reusable Atlas Directory stylesheet.

The design system now lives in ``scripts.atlas_directory.theme``. This module
preserves the ``PREMIUM_CSS`` name the Columbus generator appends to styles.css.
"""

from __future__ import annotations

from scripts.atlas_directory.theme import DIRECTORY_CSS as PREMIUM_CSS  # noqa: F401
from scripts.atlas_directory.theme import DIRECTORY_CSS  # noqa: F401
