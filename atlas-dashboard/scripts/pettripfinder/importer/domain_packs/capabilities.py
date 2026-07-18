"""AES-DATA-003A -- normalized capability taxonomy: DECLARED VOCABULARY ONLY.

This module lists the cross-category capability slugs future domain packs
(veterinary, boarding, grooming, pet-store -- AES-DATA-003B/C) will project
evidenced facts onto. Nothing in this phase populates a ``Capability`` on
any candidate, computes a projection, merges capabilities across sources,
or infers a value from an existing fact. This is a reviewed vocabulary and
its schema version -- pure data, no logic.

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
)

# High-risk: claims that traveler safety/trust depends on. Never derived
# (see candidate.py's _DUAL_FACT_DERIVERS -- a future pack must exclude
# these from any deriver mapping by construction), never defaulted, never
# accepted without an explicit, direct, source-attributed evidence span.
HIGH_RISK_CAPABILITY_SLUGS: tuple = (
    "open_24h",
    "emergency_service",
    "urgent_care",
    "walk_ins_accepted",
    "existing_clients_only",
)

CAPABILITY_SLUGS_SET = frozenset(CAPABILITY_SLUGS)
HIGH_RISK_CAPABILITY_SLUGS_SET = frozenset(HIGH_RISK_CAPABILITY_SLUGS)

assert HIGH_RISK_CAPABILITY_SLUGS_SET <= CAPABILITY_SLUGS_SET, (
    "every high-risk capability must also be a declared capability slug")
