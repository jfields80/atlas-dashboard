"""AES-DATA-003A -- dining (restaurants/breweries) legacy compatibility pack
descriptor.

Reproduces today's ``category_templates.py`` restaurant field set and
``policy_compose.py`` restaurant composer EXACTLY. See ``lodging.py`` for
the full design rationale (identical pattern, different category)."""

from __future__ import annotations

from scripts.pettripfinder.importer.constants import CATEGORY_RESTAURANTS, REQUIRED_CSV_FIELDS
from scripts.pettripfinder.importer.domain_packs.base import DomainPack
from scripts.pettripfinder.importer.policy_compose import compose_pet_policy

# Identical to category_templates._COMMON + category_templates._RESTAURANT_FIELDS.
_RESTAURANT_FIELDS = (
    "name", "address", "phone",
    "pets_allowed", "patio_or_outdoor_only", "permitted_area",
    "indoor_prohibited", "seasonal_or_weather_caveat", "water_or_treats",
    "dog_menu",
)

_RESTAURANT_FIELD_NORMALIZERS = (
    ("name", "whitespace"),
    ("address", "address"),
    ("phone", "phone"),
    ("pets_allowed", "bool"),
    ("patio_or_outdoor_only", "bool"),
    ("permitted_area", "whitespace"),
    ("indoor_prohibited", "bool"),
    ("seasonal_or_weather_caveat", "whitespace"),
    ("water_or_treats", "bool"),
    ("dog_menu", "bool"),
)

DINING_PACK = DomainPack(
    pack_id="pettripfinder-dining",
    category_ids=(CATEGORY_RESTAURANTS,),
    allowed_fields=frozenset(_RESTAURANT_FIELDS),
    field_order=_RESTAURANT_FIELDS,
    field_normalizers=_RESTAURANT_FIELD_NORMALIZERS,
    required_fields=REQUIRED_CSV_FIELDS,
    pack_version="1.0.0",
    compose_summary_fn=lambda facts: compose_pet_policy(facts, CATEGORY_RESTAURANTS),
)
