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
from scripts.pettripfinder.importer.domain_packs.base import DomainPack, SourceRoleSpec
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

# AES-DATA-004E (Task 5): declaring "pets_allowed" high-risk activates the
# EXISTING, proven AES-DATA-003F restriction in aggregate._merge_pet_facts
# (restrict a high-risk field to LOCATION_SPECIFIC evidence whenever such
# evidence exists) for lodging's multi-source path -- scenario B (a
# property-specific negative silently wins over a chain-wide positive, no
# fabricated conflict) needs nothing beyond this declaration. The three
# NUMERIC fields (pet_fee/weight_limit/pet_count_limit) are deliberately
# NOT declared high-risk here: they must stay unrestricted so a genuine
# property-vs-brand numeric disagreement still surfaces as a real
# ``policy_conflict`` (scenario E) instead of being silently dropped by the
# restriction. The "no applicable evidence at all" case (scenarios C/D) for
# all four fields is handled by the separate, lodging-specific
# ``lodging_source_strategy.gate_high_risk_field_applicability`` gate that
# runs downstream in aggregate.py -- see that module's docstring.
_HIGH_RISK_FIELDS = frozenset({"pets_allowed"})

_SOURCE_ROLES = (
    SourceRoleSpec(role_id="property_identity", capability_affinity=("pets_allowed",)),
    SourceRoleSpec(role_id="property_policy", capability_affinity=(
        "pets_allowed", "pet_fee", "weight_limit", "pet_count_limit")),
    SourceRoleSpec(role_id="brand_policy", capability_affinity=(
        "pets_allowed", "pet_fee", "weight_limit", "pet_count_limit")),
    SourceRoleSpec(role_id="management_company", capability_affinity=("pets_allowed",)),
)

LODGING_PACK = DomainPack(
    pack_id="pettripfinder-lodging",
    category_ids=(CATEGORY_HOTELS,),
    allowed_fields=frozenset(_HOTEL_FIELDS),
    field_order=_HOTEL_FIELDS,
    field_normalizers=_HOTEL_FIELD_NORMALIZERS,
    required_fields=REQUIRED_CSV_FIELDS,
    high_risk_capabilities=_HIGH_RISK_FIELDS,
    source_roles=_SOURCE_ROLES,
    pack_version="1.0.0",
    compose_summary_fn=lambda facts: compose_pet_policy(facts, CATEGORY_HOTELS),
)
