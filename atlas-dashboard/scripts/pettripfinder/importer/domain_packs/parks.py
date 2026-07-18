"""AES-DATA-003A -- parks legacy compatibility pack descriptor.

Reproduces today's ``category_templates.py`` park field set and
``policy_compose.py`` park composer EXACTLY. See ``lodging.py`` for the
full design rationale (identical pattern, different category)."""

from __future__ import annotations

from scripts.pettripfinder.importer.constants import CATEGORY_PARKS, REQUIRED_CSV_FIELDS
from scripts.pettripfinder.importer.domain_packs.base import DomainPack
from scripts.pettripfinder.importer.policy_compose import compose_pet_policy

# Identical to category_templates._COMMON + category_templates._PARK_FIELDS.
_PARK_FIELDS = (
    "name", "address", "phone",
    "pets_allowed", "off_leash", "off_leash_area_description", "fenced",
    "leash_rule", "small_dog_area", "large_dog_area", "water_available",
    "trails",
)

_PARK_FIELD_NORMALIZERS = (
    ("name", "whitespace"),
    ("address", "address"),
    ("phone", "phone"),
    ("pets_allowed", "bool"),
    ("off_leash", "bool"),
    ("off_leash_area_description", "whitespace"),
    ("fenced", "bool"),
    ("leash_rule", "whitespace"),
    ("small_dog_area", "bool"),
    ("large_dog_area", "bool"),
    ("water_available", "bool"),
    ("trails", "whitespace"),
)

PARKS_PACK = DomainPack(
    pack_id="pettripfinder-parks",
    category_ids=(CATEGORY_PARKS,),
    allowed_fields=frozenset(_PARK_FIELDS),
    field_order=_PARK_FIELDS,
    field_normalizers=_PARK_FIELD_NORMALIZERS,
    required_fields=REQUIRED_CSV_FIELDS,
    pack_version="1.0.0",
    compose_summary_fn=lambda facts: compose_pet_policy(facts, CATEGORY_PARKS),
)
