"""Shared fixtures for AES-WEB-001 Phase 1 tests.

Frozen, deterministic fixture inputs only — no clock, no randomness.
"""

from __future__ import annotations

import pytest

from engines.website_generation import SpecCompilerInput

FIXED_GENERATED_AT = "2026-07-11T00:00:00Z"
FIXED_BUILD_SALT = "phase1-golden"
FIXED_TIMESTAMP = "2026-07-11T00:00:00Z"

# 64-hex provenance stand-ins for upstream Atlas records (external to the
# CAS — see artifact_store_repository source-hash policy).
UPSTREAM_PROJECT_HASH = "a" * 64
UPSTREAM_LAUNCH_KIT_HASH = "b" * 64


@pytest.fixture
def golden_compiler_input() -> SpecCompilerInput:
    """PetTripFinder-shaped fixture spec input (AES-WEB-001 §11.5)."""
    return SpecCompilerInput(
        business_name="Pet Trip Finder",
        niche="pet-friendly travel",
        audience="traveling pet owners",
        value_proposition="Find verified pet-friendly stays fast",
        directory_taxonomy=("parks", "hotels", "restaurants"),
        monetization_model="featured listings",
        geography="United States",
        legal_footer_facts=(
            "Operated by Atlas Holdings",
            "Listings verified quarterly",
        ),
        upstream_hashes={
            "external:directory_builder_project": UPSTREAM_PROJECT_HASH,
            "external:launch_kit_metadata": UPSTREAM_LAUNCH_KIT_HASH,
        },
    )
