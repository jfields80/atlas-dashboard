"""AES-DATA-003B -- veterinary Domain Pack: the first non-legacy pack.

ONE category (``CATEGORY_VETERINARY``) covers general practice, hospital,
emergency, urgent-care, and specialty veterinary care alike -- emergency/
urgent-care/24-hour status are evidence-backed CAPABILITIES on this single
category, never separate categories (mission doctrine #1). An
``/emergency-vets`` page is later built by filtering ``category ==
veterinary AND emergency_service == SUPPORTED``, not by a second category.

This module also owns the veterinary capability-projection logic (Task 7):
turning already-evidence-validated facts into ``Capability`` instances,
with every high-risk capability requiring direct, explicit evidence and
never derived from another fact (mission doctrine #4/#5/#6/#7)."""

from __future__ import annotations

from typing import List, Mapping, Sequence, Tuple

from scripts.pettripfinder.importer import constants as C
from scripts.pettripfinder.importer.constants import (
    CATEGORY_VETERINARY,
    REQUIRED_CSV_FIELDS,
)
from scripts.pettripfinder.importer.domain_packs.base import (
    Capability,
    CapabilityState,
    DomainPack,
    SourceRoleSpec,
)
from scripts.pettripfinder.importer.domain_packs.capabilities import (
    CAPABILITY_SCHEMA_VERSION,
    HIGH_RISK_CAPABILITY_SLUGS,
)
from scripts.pettripfinder.importer.domain_packs.projection import _source_applicable
from scripts.pettripfinder.importer.models import Conflict, ExtractedEvidence

# --------------------------------------------------------------------------- #
# Field vocabulary (Task 4). Same "_COMMON identity + category facts"
# pattern the three legacy packs use: name/address/phone are the only
# LLM-extractable identity fields (city/state/postal_code/website_url come
# from structured metadata, exactly as for lodging/parks/dining).
# --------------------------------------------------------------------------- #

_COMMON = ("name", "address", "phone")

# Boolean capability fields: normalized "true"/"false" strings, one LLM fact
# each, no nuance lost by a boolean (doctrine: "Use normalized boolean
# strings only where current importer conventions support them").
_BOOLEAN_FIELDS = (
    "general_practice", "preventive_care", "wellness_exams", "vaccinations",
    "diagnostics", "surgery", "dentistry", "pharmacy", "prescription_fulfillment",
    "emergency_service", "urgent_care", "open_24h", "walk_ins_accepted",
    "appointment_required", "existing_clients_only", "critical_care",
)

# Text-valued capability fields: nuance matters, never forced into a boolean
# (doctrine: species_served/after_hours_instructions/specialty_care/hours
# stay free text; booking_url stays a URL).
_TEXT_CAPABILITY_FIELDS = (
    "species_served", "specialty_care", "after_hours_instructions", "booking_url",
)

# "hours" is extracted (evidence-backed, normalized text) but is NOT a
# capability slug (not in domain_packs/capabilities.py's taxonomy) -- it is
# the one field this pack routes into CategoryDetail instead (Task 8: an
# explanatory/idiosyncratic fact, not a filterable cross-category one).
_DETAIL_ONLY_FIELDS = ("hours",)

_VETERINARY_FIELDS = _COMMON + _BOOLEAN_FIELDS + _TEXT_CAPABILITY_FIELDS + _DETAIL_ONLY_FIELDS

_VETERINARY_FIELD_NORMALIZERS = (
    ("name", "whitespace"),
    ("address", "address"),
    ("phone", "phone"),
) + tuple((f, "bool") for f in _BOOLEAN_FIELDS) + (
    ("species_served", "whitespace"),
    ("specialty_care", "whitespace"),
    ("after_hours_instructions", "whitespace"),
    ("booking_url", "url"),
    ("hours", "whitespace"),
)

# Every text/boolean capability field maps 1:1 to a capability_id of the
# same name (Task 7); "hours" is deliberately excluded (routes to
# CategoryDetail instead, see _DETAIL_ONLY_FIELDS above).
_CAPABILITY_FIELDS = _BOOLEAN_FIELDS + _TEXT_CAPABILITY_FIELDS

_HIGH_RISK_CAPABILITIES = frozenset(HIGH_RISK_CAPABILITY_SLUGS) & frozenset(_CAPABILITY_FIELDS)

_SOURCE_ROLES = (
    SourceRoleSpec(role_id="location", capability_affinity=("general_practice",)),
    SourceRoleSpec(role_id="services", capability_affinity=(
        "general_practice", "preventive_care", "wellness_exams", "vaccinations",
        "diagnostics", "surgery", "dentistry", "pharmacy", "specialty_care")),
    SourceRoleSpec(role_id="emergency", capability_affinity=(
        "emergency_service", "urgent_care", "open_24h", "critical_care")),
    SourceRoleSpec(role_id="hours", capability_affinity=("open_24h",)),
    SourceRoleSpec(role_id="contact", capability_affinity=("existing_clients_only",)),
    SourceRoleSpec(role_id="booking", capability_affinity=(
        "booking_url", "appointment_required", "walk_ins_accepted")),
    SourceRoleSpec(role_id="after_hours", capability_affinity=("after_hours_instructions",)),
)

_DISPLAY_LABELS = (
    ("general_practice", "General Practice"),
    ("preventive_care", "Preventive Care"),
    ("wellness_exams", "Wellness Exams"),
    ("vaccinations", "Vaccinations"),
    ("diagnostics", "Diagnostics"),
    ("surgery", "Surgery"),
    ("dentistry", "Dentistry"),
    ("pharmacy", "Pharmacy"),
    ("prescription_fulfillment", "Prescription Fulfillment"),
    ("emergency_service", "Emergency Service"),
    ("urgent_care", "Urgent Care"),
    ("open_24h", "Open 24 Hours"),
    ("walk_ins_accepted", "Walk-Ins Accepted"),
    ("appointment_required", "Appointment Required"),
    ("existing_clients_only", "Existing Clients Only"),
    ("species_served", "Species Served"),
    ("specialty_care", "Specialty Care"),
    ("critical_care", "Critical Care"),
    ("after_hours_instructions", "After-Hours Instructions"),
    ("booking_url", "Booking"),
)

# --------------------------------------------------------------------------- #
# Bounded prompt fragment (Task 5). Concise, deterministic, additive only --
# the global anti-hallucination/evidence-span rules in extraction.py remain
# authoritative and are never replaced. No business-specific wording.
# --------------------------------------------------------------------------- #

_PROMPT_FRAGMENT = (
    "VETERINARY-SPECIFIC RULES (in addition to the rules above):\n"
    "1. Extract only facts explicitly stated on THIS official page. Never "
    "infer a fact from the business name, a photo, a logo, or generic "
    "marketing language.\n"
    "2. The words \"hospital\" or \"animal hospital\" in a business name do "
    "NOT prove emergency_service. \"Critical care\" without explicit "
    "emergency wording does not prove emergency_service or open_24h.\n"
    "3. Extract emergency_service=true ONLY when the page explicitly states "
    "this practice provides emergency care.\n"
    "4. Extract urgent_care=true ONLY when the page explicitly uses "
    "\"urgent care\" (or equivalent explicit wording) for this practice. "
    "Never infer urgent_care or open_24h from emergency_service alone.\n"
    "5. Extract open_24h=true ONLY when the page explicitly states 24-hour "
    "or 24/7 availability tied to THIS location or service. \"Open 7 days a "
    "week\" or \"open late\" is NOT 24-hour availability. Never infer "
    "open_24h from emergency_service, urgent_care, or an after-hours phone "
    "line alone.\n"
    "6. Extract walk_ins_accepted=true ONLY when the page explicitly states "
    "walk-ins or no-appointment-necessary for THIS location/service. Never "
    "infer walk_ins_accepted from emergency_service or urgent_care alone.\n"
    "7. Extract existing_clients_only=true ONLY when the page explicitly "
    "restricts a service to established/current clients.\n"
    "8. species_served must be the literal species stated (for example "
    "\"dogs and cats\" or \"dogs, cats, and exotics\"). The words \"pets\" "
    "or \"animals\" alone do NOT specify a species. Never infer an exotic "
    "or specialty species from a photo, logo, or business name.\n"
    "9. after_hours_instructions (for example an after-hours phone line) is "
    "NOT the same as emergency_service or open_24h -- extract it only as "
    "its own fact.\n"
    "10. booking_url must be an explicit URL on the page associated with "
    "scheduling/booking for this business -- never a guessed contact or "
    "home page link."
)


VETERINARY_PACK = DomainPack(
    pack_id="pettripfinder-veterinary",
    category_ids=(CATEGORY_VETERINARY,),
    allowed_fields=frozenset(_VETERINARY_FIELDS),
    field_order=_VETERINARY_FIELDS,
    field_normalizers=_VETERINARY_FIELD_NORMALIZERS,
    prompt_fragment=_PROMPT_FRAGMENT,
    required_fields=REQUIRED_CSV_FIELDS,
    advisory_fields=("booking_url", "hours", "after_hours_instructions"),
    high_risk_capabilities=_HIGH_RISK_CAPABILITIES,
    source_roles=_SOURCE_ROLES,
    display_labels=_DISPLAY_LABELS,
    detail_schema_version="1.0.0",
    pack_version="1.0.0",
)


# --------------------------------------------------------------------------- #
# Capability projection (Task 7). Pure function: only ever reads already-
# evidence-validated facts/evidence/conflicts assembled by the UNCHANGED
# candidate.py/aggregate.py pipeline -- never re-validates evidence itself,
# never fetches, never calls a provider. Callers MUST pass the FINAL
# evidence sequence (the one that will become CandidateListing.evidence)
# so evidence_index values are correct (Task 7 rule #11).
# --------------------------------------------------------------------------- #

# Species text that indicates an exotic/specialty species claim -- used only
# to set the PER-INSTANCE Capability.high_risk marker on species_served
# (the slug itself is always pack-declared high-risk; see capabilities.py).
# A deliberately narrow, literal keyword list -- never a fuzzy/ML match.
_EXOTIC_SPECIES_KEYWORDS = (
    "exotic", "reptile", "avian", "bird", "rabbit", "ferret", "rodent",
    "small mammal", "pocket pet", "snake", "lizard", "turtle",
    "tortoise", "guinea pig", "hedgehog", "chinchilla", "amphibian",
)


def _is_exotic_species_claim(value: str) -> bool:
    v = (value or "").lower()
    return any(kw in v for kw in _EXOTIC_SPECIES_KEYWORDS)


def _first_evidence_index(
    evidence: Sequence[ExtractedEvidence], field: str, value: str = None,
) -> int:
    """First index of a SUPPORTED/AMBIGUOUS evidence entry for ``field``
    (optionally also matching ``value`` exactly). Never matches an
    UNSUPPORTED entry -- an unsupported claim can never back a capability
    (Task 7 rule #1/#10)."""
    for i, ev in enumerate(evidence):
        if ev.field_name != field or ev.support_state == C.SUPPORT_UNSUPPORTED:
            continue
        if value is not None and ev.proposed_value != value:
            continue
        return i
    return -1


def project_capabilities(
    facts: Mapping[str, str],
    evidence: Sequence[ExtractedEvidence],
    conflicts: Sequence[Conflict] = (),
    source_url: str = "",
    source_applicability: Mapping[str, str] = None,
) -> Tuple[Capability, ...]:
    """Project veterinary ``Capability`` instances from already-resolved,
    already-evidence-validated facts (Task 7).

    Rules enforced here directly (mission doctrine #4/#5/#6/#7/#8, Task 7):
    - Only a field that survived evidence validation (SUPPORTED/AMBIGUOUS,
      never UNSUPPORTED) and appears in ``facts`` OR ``conflicts`` is
      considered at all; a merely-missing fact is silently omitted (never a
      published UNKNOWN entry -- Task 7 rule #3).
    - A field-by-field CONFLICT (multi-source only; Task 12) always
      overrides an agreeing single value: the capability is emitted as
      CONFLICTED, never as SUPPORTED, no matter what any individual source
      said.
    - Every capability is projected INDEPENDENTLY from its OWN field's
      evidence -- never derived from another capability's state (this
      function has no branch that reads one field's value to set another
      field's state; that is what makes "emergency_service implies
      open_24h" etc. structurally impossible here, not just discouraged).
    - Deterministic order: the pack's declared field order.
    - AES-DATA-003F (Task 2): a high-risk field whose winning evidence's own
      ``source_url`` is positively classified (``source_applicability``) as
      something other than LOCATION_SPECIFIC is still emitted -- never
      silently dropped -- but downgraded to UNKNOWN rather than SUPPORTED/
      EXPLICITLY_ABSENT/CONFLICTED, exactly mirroring
      ``domain_packs/projection.py``'s shared behavior (this pack's
      projection stays bespoke for the exotic-species logic, but reuses the
      SAME applicability check via ``_source_applicable`` so both paths
      enforce identical doctrine). ``source_applicability`` empty/None (every
      pre-003F call site) is a no-op -- full backward compatibility.
    """
    applicability = source_applicability or {}
    conflicted_fields = {cf.field_name for cf in conflicts if cf.field_name in _CAPABILITY_FIELDS}
    out: List[Capability] = []
    seen_ids = set()
    for field in _CAPABILITY_FIELDS:
        if field in conflicted_fields:
            idx = _first_evidence_index(evidence, field)
            if idx < 0:
                continue   # no real evidence at all -> omit, never emit CONFLICTED
            high_risk = field in _HIGH_RISK_CAPABILITIES
            ev_url = evidence[idx].source_url or source_url
            state = CapabilityState.CONFLICTED.value
            if high_risk and not _source_applicable(ev_url, applicability):
                state = CapabilityState.UNKNOWN.value
            out.append(Capability(
                capability_id=field, state=state,
                value="", high_risk=high_risk, evidence_index=idx, source_url=ev_url))
            seen_ids.add(field)
            continue

        if field not in facts:
            continue   # Task 7 rule #3: omit, never flood with UNKNOWN
        value = facts[field]

        if field in _BOOLEAN_FIELDS:
            if value == "true":
                state = CapabilityState.SUPPORTED.value
            elif value == "false":
                state = CapabilityState.EXPLICITLY_ABSENT.value
            else:
                continue   # not a clean true/false -> never guess (rule #6)
            cap_value = ""
        else:
            if not value:
                continue
            state = CapabilityState.SUPPORTED.value
            cap_value = value

        idx = _first_evidence_index(evidence, field, value)
        if idx < 0:
            continue   # Task 7 rule #10: invalid/missing evidence -> omit

        high_risk = field in _HIGH_RISK_CAPABILITIES
        if field == "species_served":
            high_risk = _is_exotic_species_claim(value)

        ev_url = evidence[idx].source_url or source_url
        if high_risk and not _source_applicable(ev_url, applicability):
            state = CapabilityState.UNKNOWN.value
            cap_value = ""

        out.append(Capability(
            capability_id=field, state=state, value=cap_value, high_risk=high_risk,
            evidence_index=idx, source_url=ev_url))
        seen_ids.add(field)

    assert len(seen_ids) == len(out), "project_capabilities emitted a duplicate capability_id"
    return tuple(out)


def service_evidence_present(capabilities: Sequence[Capability]) -> bool:
    """Whether at least one capability carries REAL evidence of any kind
    (SUPPORTED, EXPLICITLY_ABSENT, or CONFLICTED) -- an explicit negative or
    a genuine cross-source disagreement both prove this is a real,
    identifiable veterinary practice with substantive page content, exactly
    as much as a positive claim does. Only when EVERY capability is
    UNKNOWN/absent does this return False (drives the veterinary REJECT
    gate's "no veterinary service evidence at all")."""
    return any(
        cap.state in (CapabilityState.SUPPORTED.value, CapabilityState.EXPLICITLY_ABSENT.value,
                     CapabilityState.CONFLICTED.value)
        for cap in capabilities)


def high_risk_capability_conflict(capabilities: Sequence[Capability]) -> bool:
    """Whether any HIGH-RISK capability is CONFLICTED -- drives the
    veterinary REVIEW gate (mission Task 10: "high-risk capability is
    conflicted... conflicting high-risk capability forces REVIEW")."""
    return any(
        cap.state == CapabilityState.CONFLICTED.value and cap.high_risk
        for cap in capabilities)
