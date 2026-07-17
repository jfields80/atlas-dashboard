"""AES-DATA-001 importer -- category-specific field whitelists (mission
section 10). Deliberately small: only the fields PetTripFinder V1 needs.
Anything outside a category's allowed set is rejected deterministically by
the extractor parser and evidence layer -- no broad ontology.
"""

from __future__ import annotations

from typing import Dict, FrozenSet, Tuple

from scripts.pettripfinder.importer.constants import (
    CATEGORY_HOTELS,
    CATEGORY_PARKS,
    CATEGORY_RESTAURANTS,
)

# Common identity fields every category shares.
_COMMON = ("name", "address", "phone")

_HOTEL_FIELDS = _COMMON + (
    "pets_allowed", "species_allowed", "pet_fee", "fee_basis", "weight_limit",
    "pet_count_limit", "unattended_policy", "breed_restrictions",
    "general_restrictions",
)
_PARK_FIELDS = _COMMON + (
    "pets_allowed", "off_leash", "off_leash_area_description", "fenced",
    "leash_rule", "small_dog_area", "large_dog_area", "water_available",
    "trails",
)
_RESTAURANT_FIELDS = _COMMON + (
    "pets_allowed", "patio_or_outdoor_only", "permitted_area",
    "indoor_prohibited", "seasonal_or_weather_caveat", "water_or_treats",
    "dog_menu",
)

ALLOWED_FIELDS_BY_CATEGORY: Dict[str, FrozenSet[str]] = {
    CATEGORY_HOTELS: frozenset(_HOTEL_FIELDS),
    CATEGORY_PARKS: frozenset(_PARK_FIELDS),
    CATEGORY_RESTAURANTS: frozenset(_RESTAURANT_FIELDS),
}

# Deterministic ordering for prompts and reports (whitelist as a tuple).
ALLOWED_FIELD_ORDER: Dict[str, Tuple[str, ...]] = {
    CATEGORY_HOTELS: _HOTEL_FIELDS,
    CATEGORY_PARKS: _PARK_FIELDS,
    CATEGORY_RESTAURANTS: _RESTAURANT_FIELDS,
}

# The boolean pet-friendliness field per category (drives no_pets / no
# pet-evidence recommendation logic).
PETS_ALLOWED_FIELD = "pets_allowed"

# Required CSV publish fields for a candidate to be READY (mission section
# 15). ``pet_policy`` is composed, ``observed_at``/``source_url``/
# ``source_type`` come from the snapshot/context -- checked separately.
REQUIRED_CSV_FIELDS = (
    "name", "category", "address", "city", "state",
    "website_url", "source_url", "source_type", "observed_at", "pet_policy",
)


def allowed_fields(category: str) -> FrozenSet[str]:
    return ALLOWED_FIELDS_BY_CATEGORY.get(category, frozenset())


def allowed_field_order(category: str) -> Tuple[str, ...]:
    return ALLOWED_FIELD_ORDER.get(category, ())
