"""AES-DATA-003A -- lodging (hotels) legacy compatibility pack descriptor.

Reproduces today's ``category_templates.py`` hotel field set and
``policy_compose.py`` hotel composer EXACTLY -- this is metadata capture,
not a new implementation. The real, executed pet-policy composition and
recommendation-gate logic remain in ``policy_compose.py``/``recommend.py``
unchanged (mission Amendment 2); ``compose_summary_fn`` below is a thin,
verified-equivalent reference to the real composer for future use, not a
duplicate implementation.
"""

from __future__ import annotations

from scripts.pettripfinder.importer.constants import CATEGORY_HOTELS, REQUIRED_CSV_FIELDS
from scripts.pettripfinder.importer.domain_packs.base import DomainPack
from scripts.pettripfinder.importer.policy_compose import compose_pet_policy

# Identical to category_templates._COMMON + category_templates._HOTEL_FIELDS
# (AES-DATA-001/mission section 10) -- the source of truth for this tuple
# now lives here; category_templates.py delegates to the registry.
_HOTEL_FIELDS = (
    "name", "address", "phone",
    "pets_allowed", "species_allowed", "pet_fee", "fee_basis", "weight_limit",
    "pet_count_limit", "unattended_policy", "breed_restrictions",
    "general_restrictions",
)

# field -> normalizer NAME, matching candidate.py's _normalize_field_value
# dispatch exactly (declarative capture only; _normalize_field_value itself
# is untouched and remains the actually-executed normalizer).
_HOTEL_FIELD_NORMALIZERS = (
    ("name", "whitespace"),
    ("address", "address"),
    ("phone", "phone"),
    ("pets_allowed", "bool"),
    ("species_allowed", "whitespace"),
    ("pet_fee", "fee"),
    ("fee_basis", "whitespace"),
    ("weight_limit", "weight"),
    ("pet_count_limit", "count"),
    ("unattended_policy", "whitespace"),
    ("breed_restrictions", "whitespace"),
    ("general_restrictions", "whitespace"),
)

LODGING_PACK = DomainPack(
    pack_id="pettripfinder-lodging",
    category_ids=(CATEGORY_HOTELS,),
    allowed_fields=frozenset(_HOTEL_FIELDS),
    field_order=_HOTEL_FIELDS,
    field_normalizers=_HOTEL_FIELD_NORMALIZERS,
    required_fields=REQUIRED_CSV_FIELDS,
    pack_version="1.0.0",
    compose_summary_fn=lambda facts: compose_pet_policy(facts, CATEGORY_HOTELS),
)
