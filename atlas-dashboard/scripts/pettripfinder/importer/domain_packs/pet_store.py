"""AES-DATA-003C -- pet supply store Domain Pack.

ONE category (``CATEGORY_PET_STORE``) covers retail pet stores alike --
pharmacy, live-animal sales, and delivery are evidence-backed CAPABILITIES
on this single category, never separate categories (mission doctrine
#1/#12). A store that also grooms stays category "pet_store" with
``grooming_offered=true``.

Uses the shared projection helper (``domain_packs/projection.py``, Task 8);
veterinary's own bespoke projection is left unchanged."""

from __future__ import annotations

from typing import Mapping, Sequence, Tuple

from scripts.pettripfinder.importer.constants import CATEGORY_PET_STORE, REQUIRED_CSV_FIELDS
from scripts.pettripfinder.importer.domain_packs.base import Capability, DomainPack, SourceRoleSpec
from scripts.pettripfinder.importer.domain_packs.capabilities import HIGH_RISK_CAPABILITY_SLUGS
from scripts.pettripfinder.importer.domain_packs.projection import (
    CapabilityProjectionRule,
    high_risk_capability_conflict,
    project_capabilities as _shared_project_capabilities,
    service_evidence_present,
)
from scripts.pettripfinder.importer.models import Conflict, ExtractedEvidence

_COMMON = ("name", "address", "phone")

_BOOLEAN_FIELDS = (
    "retail_products", "pet_food", "pet_supplies", "pharmacy",
    "prescription_fulfillment", "prescription_food", "grooming_offered", "self_wash",
    "vaccination_clinic", "live_animals", "curbside_pickup", "delivery",
    "online_ordering",
)

_TEXT_CAPABILITY_FIELDS = ("booking_url",)

_DETAIL_ONLY_FIELDS = ("hours",)

_PET_STORE_FIELDS = _COMMON + _BOOLEAN_FIELDS + _TEXT_CAPABILITY_FIELDS + _DETAIL_ONLY_FIELDS

_PET_STORE_FIELD_NORMALIZERS = (
    ("name", "whitespace"),
    ("address", "address"),
    ("phone", "phone"),
) + tuple((f, "bool") for f in _BOOLEAN_FIELDS) + (
    ("booking_url", "url"),
    ("hours", "whitespace"),
)

_CAPABILITY_FIELDS = _BOOLEAN_FIELDS + _TEXT_CAPABILITY_FIELDS

_HIGH_RISK_CAPABILITIES = frozenset(HIGH_RISK_CAPABILITY_SLUGS) & frozenset(_CAPABILITY_FIELDS)

_SOURCE_ROLES = (
    SourceRoleSpec(role_id="location", capability_affinity=("retail_products",)),
    SourceRoleSpec(role_id="products", capability_affinity=(
        "retail_products", "pet_food", "pet_supplies")),
    SourceRoleSpec(role_id="services", capability_affinity=(
        "grooming_offered", "self_wash")),
    SourceRoleSpec(role_id="pharmacy", capability_affinity=(
        "pharmacy", "prescription_fulfillment", "prescription_food", "vaccination_clinic")),
    SourceRoleSpec(role_id="ordering", capability_affinity=("online_ordering", "booking_url")),
    SourceRoleSpec(role_id="delivery", capability_affinity=("delivery", "curbside_pickup")),
    SourceRoleSpec(role_id="hours", capability_affinity=()),
    SourceRoleSpec(role_id="contact", capability_affinity=()),
)

_DISPLAY_LABELS = (
    ("retail_products", "Retail Products"),
    ("pet_food", "Pet Food"),
    ("pet_supplies", "Pet Supplies"),
    ("pharmacy", "Pharmacy"),
    ("prescription_fulfillment", "Prescription Fulfillment"),
    ("prescription_food", "Prescription Food"),
    ("grooming_offered", "Grooming"),
    ("self_wash", "Self-Wash"),
    ("vaccination_clinic", "Vaccination Clinic"),
    ("live_animals", "Live Animals"),
    ("curbside_pickup", "Curbside Pickup"),
    ("delivery", "Delivery"),
    ("online_ordering", "Online Ordering"),
    ("booking_url", "Booking"),
)

_PROMPT_FRAGMENT = (
    "PET-STORE-SPECIFIC RULES (in addition to the rules above):\n"
    "1. Extract only facts explicitly stated on THIS official page. Never "
    "infer a fact from the business name, a photo, a logo, or generic "
    "marketing language.\n"
    "2. \"Pharmacy\" wording does NOT prove prescription_fulfillment. "
    "Extract prescription_fulfillment=true ONLY when the page explicitly "
    "states prescriptions are filled for this location.\n"
    "3. Ordinary pet food does NOT prove prescription_food. Extract "
    "prescription_food=true ONLY when the page explicitly states "
    "prescription or veterinary diet food is sold.\n"
    "4. \"Self-wash\" or \"self-serve wash\" is NOT professional grooming. "
    "Extract grooming_offered=true ONLY when the page explicitly states "
    "professional/staffed grooming, separate from any self-wash facility.\n"
    "5. Health or wellness product sales do NOT prove vaccination_clinic. "
    "Extract vaccination_clinic=true ONLY when the page explicitly states "
    "vaccination clinic services are offered at this location.\n"
    "6. Curbside pickup does NOT prove delivery. Extract delivery=true "
    "ONLY when the page explicitly states delivery to the customer.\n"
    "7. Extract live_animals=true ONLY when the page explicitly states "
    "live animals are sold or available for adoption AT THIS LOCATION. An "
    "animal photo or generic pet-store marketing image is never evidence.\n"
    "8. A normal business website does NOT prove online_ordering. Extract "
    "online_ordering=true ONLY when the page explicitly offers ordering "
    "products online.\n"
    "9. If the supplied page is a chain-wide or company-level page not "
    "clearly tied to one physical location, do not extract location-"
    "specific service facts (pharmacy, grooming, self_wash, vaccination "
    "clinic, live_animals) unless the page explicitly states they apply to "
    "THIS location.\n"
    "10. hours must be tied to the relevant location -- never inferred "
    "from a chain-wide or unrelated page."
)

PET_STORE_PACK = DomainPack(
    pack_id="pettripfinder-pet-store",
    category_ids=(CATEGORY_PET_STORE,),
    allowed_fields=frozenset(_PET_STORE_FIELDS),
    field_order=_PET_STORE_FIELDS,
    field_normalizers=_PET_STORE_FIELD_NORMALIZERS,
    prompt_fragment=_PROMPT_FRAGMENT,
    required_fields=REQUIRED_CSV_FIELDS,
    advisory_fields=("booking_url", "hours"),
    high_risk_capabilities=_HIGH_RISK_CAPABILITIES,
    source_roles=_SOURCE_ROLES,
    display_labels=_DISPLAY_LABELS,
    detail_schema_version="1.0.0",
    pack_version="1.0.0",
)

_RULES = tuple(
    CapabilityProjectionRule(
        field_name=f, capability_id=f, value_kind="bool",
        high_risk=(f in _HIGH_RISK_CAPABILITIES))
    for f in _BOOLEAN_FIELDS
) + tuple(
    CapabilityProjectionRule(
        field_name=f, capability_id=f, value_kind="text",
        high_risk=(f in _HIGH_RISK_CAPABILITIES))
    for f in _TEXT_CAPABILITY_FIELDS
)


def project_capabilities(
    facts: Mapping[str, str],
    evidence: Sequence[ExtractedEvidence],
    conflicts: Sequence[Conflict] = (),
    source_url: str = "",
    source_applicability: Mapping[str, str] = None,
) -> Tuple[Capability, ...]:
    return _shared_project_capabilities(
        facts, evidence, _RULES, conflicts, source_url, source_applicability)


__all__ = [
    "PET_STORE_PACK", "project_capabilities", "service_evidence_present",
    "high_risk_capability_conflict",
]
