"""AES-DATA-003C -- boarding/daycare Domain Pack.

ONE category (``CATEGORY_BOARDING``) covers overnight boarding and daycare
alike -- species acceptance, same-day availability, and medication
administration are evidence-backed CAPABILITIES on this single category,
never separate categories (mission doctrine #1/#12). A business that also
grooms stays category "boarding" with ``grooming_offered=true``.

Uses the shared projection helper (``domain_packs/projection.py``, Task 8);
veterinary's own bespoke projection is left unchanged."""

from __future__ import annotations

from typing import Mapping, Sequence, Tuple

from scripts.pettripfinder.importer.constants import CATEGORY_BOARDING, REQUIRED_CSV_FIELDS
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
    "boarding_offered", "daycare_offered", "dog_boarding", "cat_boarding",
    "other_species_boarding", "grooming_offered", "medication_administration",
    "live_camera", "reservation_required", "same_day_availability", "pricing_available",
)

_TEXT_CAPABILITY_FIELDS = (
    "vaccination_requirements", "temperament_evaluation", "pickup_dropoff_windows",
    "booking_url",
)

_DETAIL_ONLY_FIELDS = ("hours",)

_BOARDING_FIELDS = _COMMON + _BOOLEAN_FIELDS + _TEXT_CAPABILITY_FIELDS + _DETAIL_ONLY_FIELDS

_BOARDING_FIELD_NORMALIZERS = (
    ("name", "whitespace"),
    ("address", "address"),
    ("phone", "phone"),
) + tuple((f, "bool") for f in _BOOLEAN_FIELDS) + (
    ("vaccination_requirements", "whitespace"),
    ("temperament_evaluation", "whitespace"),
    ("pickup_dropoff_windows", "whitespace"),
    ("booking_url", "url"),
    ("hours", "whitespace"),
)

_CAPABILITY_FIELDS = _BOOLEAN_FIELDS + _TEXT_CAPABILITY_FIELDS

_HIGH_RISK_CAPABILITIES = frozenset(HIGH_RISK_CAPABILITY_SLUGS) & frozenset(_CAPABILITY_FIELDS)

_SOURCE_ROLES = (
    SourceRoleSpec(role_id="location", capability_affinity=("boarding_offered",)),
    SourceRoleSpec(role_id="boarding_services", capability_affinity=(
        "boarding_offered", "dog_boarding", "cat_boarding", "other_species_boarding")),
    SourceRoleSpec(role_id="daycare_services", capability_affinity=("daycare_offered",)),
    SourceRoleSpec(role_id="requirements", capability_affinity=(
        "vaccination_requirements", "temperament_evaluation", "medication_administration")),
    SourceRoleSpec(role_id="pricing", capability_affinity=("pricing_available",)),
    SourceRoleSpec(role_id="hours", capability_affinity=("same_day_availability",)),
    SourceRoleSpec(role_id="contact", capability_affinity=("pickup_dropoff_windows",)),
    SourceRoleSpec(role_id="booking", capability_affinity=(
        "booking_url", "reservation_required", "same_day_availability")),
)

_DISPLAY_LABELS = (
    ("boarding_offered", "Overnight Boarding"),
    ("daycare_offered", "Daycare"),
    ("dog_boarding", "Dog Boarding"),
    ("cat_boarding", "Cat Boarding"),
    ("other_species_boarding", "Other Species Boarding"),
    ("grooming_offered", "Grooming"),
    ("medication_administration", "Medication Administration"),
    ("live_camera", "Live Camera"),
    ("reservation_required", "Reservation Required"),
    ("same_day_availability", "Same-Day Availability"),
    ("pricing_available", "Pricing Available"),
    ("vaccination_requirements", "Vaccination Requirements"),
    ("temperament_evaluation", "Temperament Evaluation"),
    ("pickup_dropoff_windows", "Pickup/Drop-off Windows"),
    ("booking_url", "Booking"),
)

_PROMPT_FRAGMENT = (
    "BOARDING/DAYCARE-SPECIFIC RULES (in addition to the rules above):\n"
    "1. Extract only facts explicitly stated on THIS official page. Never "
    "infer a fact from the business name, a photo, a logo, or generic "
    "marketing language.\n"
    "2. Generic \"boarding\" or \"pet boarding\" wording does NOT prove "
    "dog_boarding or cat_boarding. Extract dog_boarding/cat_boarding=true "
    "ONLY when the page explicitly states dogs, or cats, are boarded.\n"
    "3. Extract other_species_boarding=true ONLY when the page explicitly "
    "names a species other than dogs/cats (for example rabbits, birds, or "
    "reptiles) as boarded.\n"
    "4. \"Daycare\" wording does NOT prove drop-in/walk-in acceptance. "
    "Extract daycare_offered=true only for daycare itself; walk-in "
    "acceptance is a separate, distinct fact.\n"
    "5. Online booking availability does NOT prove same_day_availability. "
    "Extract same_day_availability=true ONLY when the page explicitly "
    "states same-day or current openings for THIS location.\n"
    "6. Extract medication_administration=true ONLY when the page "
    "explicitly states medication is administered. Generic \"special care\" "
    "or \"personal attention\" wording does NOT prove this.\n"
    "7. vaccination_requirements and temperament_evaluation must be quoted "
    "as the literal requirement stated (for example \"proof of rabies and "
    "bordetella vaccination required\") -- never summarized or guessed.\n"
    "8. pickup_dropoff_windows must be the literal stated windows, tied to "
    "THIS location -- never inferred from general business hours.\n"
    "9. booking_url must be an explicit URL on the page associated with "
    "reservations/booking for this business -- never a guessed contact or "
    "home page link.\n"
    "10. hours must be tied to the relevant location or service -- never "
    "inferred from a chain-wide or unrelated page."
)

BOARDING_PACK = DomainPack(
    pack_id="pettripfinder-boarding",
    category_ids=(CATEGORY_BOARDING,),
    allowed_fields=frozenset(_BOARDING_FIELDS),
    field_order=_BOARDING_FIELDS,
    field_normalizers=_BOARDING_FIELD_NORMALIZERS,
    prompt_fragment=_PROMPT_FRAGMENT,
    required_fields=REQUIRED_CSV_FIELDS,
    advisory_fields=("booking_url", "hours", "pickup_dropoff_windows"),
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
) -> Tuple[Capability, ...]:
    return _shared_project_capabilities(facts, evidence, _RULES, conflicts, source_url)


__all__ = [
    "BOARDING_PACK", "project_capabilities", "service_evidence_present",
    "high_risk_capability_conflict",
]
