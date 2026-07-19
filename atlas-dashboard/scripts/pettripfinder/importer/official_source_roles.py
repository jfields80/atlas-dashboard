"""AES-DATA-004E (Task 2) -- official lodging source-role model.

Purely descriptive/reporting metadata layered on top of the EXISTING,
unmodified evidence/applicability pipeline (``candidate.py``/``aggregate.py``/
``domain_packs``). ``classify_source_role`` never gates a recommendation and
never changes what a source is permitted to contribute -- it only LABELS,
deterministically, what kind of official source a URL already turned out to
be, using facts the pipeline already computed (which fields it contributed
evidence for, its ``source_applicability`` classification, its
``source_relationship``). Used by the Task 8 strategy report and by
``lodging_source_strategy.py``'s brand-scope gate.

A brand-wide policy source is never treated as independently proving a
selected property accepts pets (mission Task 2 doctrine) -- that gate lives
in ``lodging_source_strategy.py``; this module only classifies roles.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Sequence, Tuple
from urllib.parse import urlsplit

from scripts.pettripfinder.importer import constants as C
from scripts.pettripfinder.importer.models import ExtractedEvidence

# --------------------------------------------------------------------------- #
# Role vocabulary (Task 2).
# --------------------------------------------------------------------------- #

LODGING_SOURCE_ROLE_PROPERTY_IDENTITY = "PROPERTY_IDENTITY_SOURCE"
LODGING_SOURCE_ROLE_PROPERTY_POLICY = "PROPERTY_POLICY_SOURCE"
LODGING_SOURCE_ROLE_BRAND_POLICY = "BRAND_POLICY_SOURCE"
LODGING_SOURCE_ROLE_MANAGEMENT_COMPANY = "MANAGEMENT_COMPANY_SOURCE"
LODGING_SOURCE_ROLE_SUPPLEMENTAL = "SUPPLEMENTAL_SOURCE"
LODGING_SOURCE_ROLE_UNKNOWN = "UNKNOWN_SOURCE"

LODGING_SOURCE_ROLE_VALUES = frozenset({
    LODGING_SOURCE_ROLE_PROPERTY_IDENTITY, LODGING_SOURCE_ROLE_PROPERTY_POLICY,
    LODGING_SOURCE_ROLE_BRAND_POLICY, LODGING_SOURCE_ROLE_MANAGEMENT_COMPANY,
    LODGING_SOURCE_ROLE_SUPPLEMENTAL, LODGING_SOURCE_ROLE_UNKNOWN,
})

# Minimal, disclosed, extend-as-needed list -- the ONE pattern already vetted
# live in AES-DATA-004C's website-resolution work (PROPERTY_MANAGEMENT_DOMAINS
# there covers the same "oyorooms.com" case). Deliberately not copied via a
# cross-package import from ``discovery`` (importer and discovery stay
# independent packages); kept tiny rather than guessed/expanded speculatively.
MANAGEMENT_COMPANY_DOMAINS = frozenset({"oyorooms.com"})

_IDENTITY_FIELDS = frozenset({
    "name", "address", "city", "state", "postal_code", "phone", "website_url",
})
_POLICY_FIELDS = frozenset({
    "pets_allowed", "pet_fee", "fee_basis", "weight_limit", "pet_count_limit",
    "unattended_policy", "breed_restrictions", "general_restrictions",
    "species_allowed",
})


def _registrable_suffix_match(host: str, domains: frozenset) -> bool:
    host = (host or "").lower()
    return any(host == d or host.endswith("." + d) for d in domains)


def classify_source_role(
    *, source_url: str, evidence_for_source: Sequence[ExtractedEvidence],
    applicability: str, has_snapshot: bool,
) -> str:
    """Deterministic role label from already-computed facts. Never fetches,
    never re-evaluates evidence validity -- ``evidence_for_source`` must
    already be filtered to this ``source_url``."""
    host = urlsplit(source_url).hostname or ""
    if _registrable_suffix_match(host, MANAGEMENT_COMPANY_DOMAINS):
        return LODGING_SOURCE_ROLE_MANAGEMENT_COMPANY
    if not has_snapshot:
        return LODGING_SOURCE_ROLE_UNKNOWN

    has_policy = any(
        e.field_name in _POLICY_FIELDS and e.support_state != C.SUPPORT_UNSUPPORTED
        for e in evidence_for_source)
    has_identity = any(
        e.field_name in _IDENTITY_FIELDS and e.support_state != C.SUPPORT_UNSUPPORTED
        for e in evidence_for_source)

    if has_policy and applicability == C.SOURCE_APPLICABILITY_LOCATION_SPECIFIC:
        return LODGING_SOURCE_ROLE_PROPERTY_POLICY
    if has_policy:
        return LODGING_SOURCE_ROLE_BRAND_POLICY
    if has_identity and applicability == C.SOURCE_APPLICABILITY_LOCATION_SPECIFIC:
        return LODGING_SOURCE_ROLE_PROPERTY_IDENTITY
    return LODGING_SOURCE_ROLE_SUPPLEMENTAL


def policy_fields_supported(evidence_for_source: Sequence[ExtractedEvidence]) -> Tuple[str, ...]:
    return tuple(sorted({
        e.field_name for e in evidence_for_source
        if e.field_name in _POLICY_FIELDS and e.support_state != C.SUPPORT_UNSUPPORTED
    }))


def identity_signals(evidence_for_source: Sequence[ExtractedEvidence]) -> Tuple[str, ...]:
    return tuple(sorted({
        e.field_name for e in evidence_for_source
        if e.field_name in _IDENTITY_FIELDS and e.support_state != C.SUPPORT_UNSUPPORTED
    }))


def is_official_domain(source_relationship: str) -> bool:
    """True for any relationship the pipeline already treats as an official
    source -- never re-derives domain trust itself (single source of truth:
    ``candidate.classify_source_relationship``)."""
    return source_relationship not in (C.REL_UNKNOWN, C.REL_THIRD_PARTY, "")


@dataclass(frozen=True)
class SourceRoleAssessment:
    """One source's full Task-2 role record. Advisory/reporting only --
    never persisted onto ``CandidateListing`` in this phase."""

    source_url: str
    source_role: str
    property_applicability: str
    identity_signals: Tuple[str, ...]
    policy_fields_supported: Tuple[str, ...]
    official_domain: bool
    fetch_status: str
    cache_reference: str = ""


def assess_source(
    *, source_url: str, evidence_for_source: Sequence[ExtractedEvidence],
    applicability: str, has_snapshot: bool, source_relationship: str,
    fetch_status: str, cache_reference: str = "",
) -> SourceRoleAssessment:
    role = classify_source_role(
        source_url=source_url, evidence_for_source=evidence_for_source,
        applicability=applicability, has_snapshot=has_snapshot)
    return SourceRoleAssessment(
        source_url=source_url, source_role=role,
        property_applicability=applicability or C.SOURCE_APPLICABILITY_UNKNOWN,
        identity_signals=identity_signals(evidence_for_source),
        policy_fields_supported=policy_fields_supported(evidence_for_source),
        official_domain=is_official_domain(source_relationship),
        fetch_status=fetch_status, cache_reference=cache_reference,
    )
