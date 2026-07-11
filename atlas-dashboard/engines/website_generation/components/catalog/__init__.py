"""Component catalog — ComponentDefinition data, one module per family.

AES-WEB-002 §29.1: the catalog holds declarative ``ComponentDefinition``
data (one module per wave/family grouping), importing only ``contracts/``
and ``constants/``. AES-WEB-002B shipped Wave 1 (:mod:`.layout_atoms` — the
fifteen §27.2 foundation primitives). AES-WEB-002C ships Wave 2
(:mod:`.navigation` — the eight §27.3 navigation/legal/status components).
Later waves add their modules (discovery, listings_profiles,
trust_conversion, seo_editorial, monetization_status) and extend the
registry tuple.
"""

from engines.website_generation.components.catalog.layout_atoms import (
    WAVE1_COMPONENTS,
)
from engines.website_generation.components.catalog.navigation import (
    WAVE2_COMPONENTS,
)

__all__ = ["WAVE1_COMPONENTS", "WAVE2_COMPONENTS"]
