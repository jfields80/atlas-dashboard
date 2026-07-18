"""AES-DATA-003C -- pet grooming Domain Pack.

ONE category (``CATEGORY_GROOMING``) covers dog and cat grooming alike --
species coverage, mobile service, and walk-in acceptance are evidence-backed
CAPABILITIES on this single category, never separate categories (mission
doctrine #1/#12).

Uses the shared projection helper (``domain_packs/projection.py``, Task 8);
veterinary's own bespoke projection is left unchanged."""

from __future__ import annotations

from typing import Mapping, Sequence, Tuple

from scripts.pettripfinder.importer.constants import CATEGORY_GROOMING, REQUIRED_CSV_FIELDS
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
    "grooming_offered", "dog_grooming", "cat_grooming", "bathing", "nail_trimming",
    "deshedding", "mobile_service", "appointment_required", "walk_ins_accepted",
    "pricing_available",
)

_TEXT_CAPABILITY_FIELDS = (
    "breed_restrictions", "size_restrictions", "service_area", "booking_url",
)

_DETAIL_ONLY_FIELDS = ("hours",)

_GROOMING_FIELDS = _COMMON + _BOOLEAN_FIELDS + _TEXT_CAPABILITY_FIELDS + _DETAIL_ONLY_FIELDS

_GROOMING_FIELD_NORMALIZERS = (
    ("name", "whitespace"),
    ("address", "address"),
    ("phone", "phone"),
) + tuple((f, "bool") for f in _BOOLEAN_FIELDS) + (
    ("breed_restrictions", "whitespace"),
    ("size_restrictions", "whitespace"),
    ("service_area", "whitespace"),
    ("booking_url", "url"),
    ("hours", "whitespace"),
)

_CAPABILITY_FIELDS = _BOOLEAN_FIELDS + _TEXT_CAPABILITY_FIELDS

_HIGH_RISK_CAPABILITIES = frozenset(HIGH_RISK_CAPABILITY_SLUGS) & frozenset(_CAPABILITY_FIELDS)

_SOURCE_ROLES = (
    SourceRoleSpec(role_id="location", capability_affinity=("grooming_offered",)),
    SourceRoleSpec(role_id="services", capability_affinity=(
        "grooming_offered", "dog_grooming", "cat_grooming", "bathing",
        "nail_trimming", "deshedding")),
    SourceRoleSpec(role_id="restrictions", capability_affinity=(
        "breed_restrictions", "size_restrictions")),
    SourceRoleSpec(role_id="pricing", capability_affinity=("pricing_available",)),
    SourceRoleSpec(role_id="service_area", capability_affinity=(
        "mobile_service", "service_area")),
    SourceRoleSpec(role_id="booking", capability_affinity=(
        "booking_url", "appointment_required", "walk_ins_accepted")),
    SourceRoleSpec(role_id="hours", capability_affinity=()),
    SourceRoleSpec(role_id="contact", capability_affinity=()),
)

_DISPLAY_LABELS = (
    ("grooming_offered", "Grooming"),
    ("dog_grooming", "Dog Grooming"),
    ("cat_grooming", "Cat Grooming"),
    ("bathing", "Bathing"),
    ("nail_trimming", "Nail Trimming"),
    ("deshedding", "Deshedding"),
    ("mobile_service", "Mobile Service"),
    ("appointment_required", "Appointment Required"),
    ("walk_ins_accepted", "Walk-Ins Accepted"),
    ("pricing_available", "Pricing Available"),
    ("breed_restrictions", "Breed Restrictions"),
    ("size_restrictions", "Size Restrictions"),
    ("service_area", "Service Area"),
    ("booking_url", "Booking"),
)

_PROMPT_FRAGMENT = (
    "GROOMING-SPECIFIC RULES (in addition to the rules above):\n"
    "1. Extract only facts explicitly stated on THIS official page. Never "
    "infer a fact from the business name, a photo, a logo, or generic "
    "marketing language.\n"
    "2. Generic \"grooming\" or \"professional grooming\" wording does NOT "
    "prove dog_grooming or cat_grooming. Extract dog_grooming/cat_grooming"
    "=true ONLY when the page explicitly names that species.\n"
    "3. Appointment availability does NOT prove walk_ins_accepted. Extract "
    "walk_ins_accepted=true ONLY when the page explicitly states walk-ins "
    "or no-appointment-necessary. \"Same-day appointments\" is still an "
    "appointment, not a walk-in, and does NOT prove walk_ins_accepted.\n"
    "4. Extract mobile_service=true ONLY when the page explicitly states "
    "the business travels to the client (for example \"we come to you\" or "
    "\"mobile grooming van\") -- generic delivery-style wording alone does "
    "not qualify.\n"
    "5. service_area must be the literal stated coverage area (for example "
    "\"Columbus and surrounding suburbs\") -- NEVER inferred from the "
    "business's own street address alone. A single city name in the "
    "address is not a service-area claim.\n"
    "6. breed_restrictions and size_restrictions must be quoted as the "
    "literal restriction stated. Never infer \"no restrictions\" from "
    "silence -- omit the field entirely when the page does not state a "
    "restriction.\n"
    "7. nail_trimming/bathing/deshedding must each be extracted only when "
    "explicitly listed as a service -- never inferred from a generic "
    "\"grooming package\" phrase.\n"
    "8. booking_url must be an explicit URL on the page associated with "
    "scheduling/booking for this business -- never a guessed contact or "
    "home page link.\n"
    "9. hours must be tied to the relevant location or service -- never "
    "inferred from a chain-wide or unrelated page."
)

GROOMING_PACK = DomainPack(
    pack_id="pettripfinder-grooming",
    category_ids=(CATEGORY_GROOMING,),
    allowed_fields=frozenset(_GROOMING_FIELDS),
    field_order=_GROOMING_FIELDS,
    field_normalizers=_GROOMING_FIELD_NORMALIZERS,
    prompt_fragment=_PROMPT_FRAGMENT,
    required_fields=REQUIRED_CSV_FIELDS,
    advisory_fields=("booking_url", "hours", "service_area"),
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
    "GROOMING_PACK", "project_capabilities", "service_evidence_present",
    "high_risk_capability_conflict",
]
