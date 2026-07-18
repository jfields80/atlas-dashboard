"""AES-DATA-003A/B -- normalized capability taxonomy: DECLARED VOCABULARY.

This module lists the cross-category capability slugs domain packs project
evidenced facts onto. AES-DATA-003A declared the vocabulary only (nothing
populated it). AES-DATA-003B is the first phase to actually populate
``Capability`` instances -- for the veterinary pack only; this module still
does no projection, merge, or inference itself, it only names/versions the
vocabulary and its high-risk subset.

The high-risk subset marks claims that must never be derived or defaulted:
an explicit, direct evidence span is required before any of these may be
SUPPORTED (AES-DATA-003 mission doctrine #4). Absence is UNKNOWN, never a
default negative.
"""

from __future__ import annotations

CAPABILITY_SCHEMA_VERSION = "1.0.0"

# Reviewed, deliberately flat slug registry (no ontology/graph). New slugs
# are added here only after a category pack needs them -- capabilities are
# meant to be reused across packs (e.g. "walk_ins_accepted" applies to
# veterinary, grooming, and boarding alike), not reinvented per pack.
CAPABILITY_SLUGS: tuple = (
    "pets_allowed",
    "appointment_required",
    "walk_ins_accepted",
    "open_24h",
    "emergency_service",
    "urgent_care",
    "species_served",
    "mobile_service",
    "service_area",
    "boarding_offered",
    "daycare_offered",
    "grooming_offered",
    "retail_products",
    "pharmacy",
    "prescription_fulfillment",
    "self_wash",
    "vaccination_clinic",
    "delivery",
    "curbside_pickup",
    "existing_clients_only",
    "online_ordering",
    "booking_url",
    # AES-DATA-003B -- veterinary-specific additions. Biased toward reuse:
    # every one of these is written so a future boarding/grooming/pet-store
    # pack could plausibly reuse it too (e.g. "vaccinations" is not called
    # "veterinary_vaccinations"), never a marketing-phrase-specific slug.
    "general_practice",
    "preventive_care",
    "wellness_exams",
    "vaccinations",
    "diagnostics",
    "surgery",
    "dentistry",
    "specialty_care",
    "critical_care",
    "after_hours_instructions",
)

# High-risk: claims that traveler safety/trust depends on. Never derived
# (see candidate.py's _DUAL_FACT_DERIVERS -- a future pack must exclude
# these from any deriver mapping by construction), never defaulted, never
# accepted without an explicit, direct, source-attributed evidence span.
# "species_served" is included because an exotic/specialty-species claim
# carries the same no-inference risk as an emergency claim; the veterinary
# pack's own projection logic additionally flags the PER-INSTANCE
# ``Capability.high_risk`` marker only when the evidenced value actually
# denotes an exotic/specialty species (a plain "dogs and cats" is not
# marked instance-high-risk even though the slug is pack-declared high-risk).
HIGH_RISK_CAPABILITY_SLUGS: tuple = (
    "open_24h",
    "emergency_service",
    "urgent_care",
    "walk_ins_accepted",
    "existing_clients_only",
    "species_served",
)

CAPABILITY_SLUGS_SET = frozenset(CAPABILITY_SLUGS)
HIGH_RISK_CAPABILITY_SLUGS_SET = frozenset(HIGH_RISK_CAPABILITY_SLUGS)

assert HIGH_RISK_CAPABILITY_SLUGS_SET <= CAPABILITY_SLUGS_SET, (
    "every high-risk capability must also be a declared capability slug")
