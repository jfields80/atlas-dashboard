"""AES-DATA-004E (Task 5) -- property + brand multi-source lodging strategy.

Closes a real, disclosed gap in the existing AES-DATA-003F applicability
machinery (``candidate.classify_source_applicability`` /
``aggregate._merge_pet_facts``): that machinery already restricts a
HIGH-RISK field to LOCATION_SPECIFIC evidence *when such evidence exists*
(proven live for veterinary/grooming/boarding/pet_store -- see
``test_source_applicability.py``), but a legacy flat-``pet_facts`` category
(hotels/parks/dining) has no downstream step for the *other* case: a
high-risk field whose ONLY evidence is organization-wide/unknown. Veterinary
closes that gap via ``domain_packs.projection.project_capabilities``
(Capability-model categories only); this module is the equivalent gate for
lodging's flat-dict pipeline, applied to exactly the fields the AES-DATA-004E
mission scopes: ``pets_allowed``, ``pet_fee``, ``weight_limit``,
``pet_count_limit``.

Required scenarios (mission Task 5), each proven in
``tests/pettripfinder/importer/test_lodging_source_strategy.py``:

    A. Property positive + brand-only fee -> fee published ONLY when the
       brand source states universal applicability.
    B. Property negative + brand positive -> property wins silently (this
       scenario is handled entirely by the EXISTING ``_merge_pet_facts``
       restriction once ``pets_allowed`` is declared high-risk on the
       lodging pack -- no new code needed for it here).
    C. Property identifies the hotel with no pet wording; brand says
       "participating locations" -> stays REVIEW/UNKNOWN.
    D. Brand states a universal policy for ALL locations, property identity
       is otherwise established -> the brand fact MAY publish.
    E. Property and brand give genuinely different numbers for the same
       field -> a real conflict (unaffected by this module: numeric fields
       are deliberately NOT added to the lodging pack's high-risk set, so
       ``_merge_pet_facts``'s existing distinct-value conflict detection
       keeps seeing both values and raises ``policy_conflict`` exactly as it
       already does for any other multi-source numeric disagreement).
    F. Only a brand homepage exists (no property-level URL at all) -> a
       batch-construction concern, not a merge-time one; documented in the
       Task 8 strategy report and the Task 9 validation plan, not gated here.
"""

from __future__ import annotations

from typing import Dict, Mapping, Sequence, Tuple

from scripts.pettripfinder.importer import constants as C
from scripts.pettripfinder.importer.models import ExtractedEvidence

# The exact four fields the mission scopes (Task 5's scenarios + Task 6's
# numeric validator target the same three numeric fields; pets_allowed is
# the one boolean high-risk field this gate additionally covers).
GATED_FIELDS = frozenset({"pets_allowed", "pet_fee", "weight_limit", "pet_count_limit"})

# Deterministic, keyword-based brand-policy SCOPE classification. Applied
# only to a source's OWN evidence text -- never fabricated, never inferred
# from silence. "unknown" (neither marker present) is the SAFE default and
# behaves exactly like "participating" for gating purposes (doctrine:
# "brand-wide fees/limits remain UNKNOWN unless the policy clearly states
# universal applicability").
BRAND_SCOPE_UNIVERSAL = "universal"
BRAND_SCOPE_PARTICIPATING = "participating"
BRAND_SCOPE_UNKNOWN = "unknown"

_UNIVERSAL_MARKERS = (
    "all our hotels", "all of our hotels", "all our properties",
    "all of our properties", "all locations", "all our locations",
    "every location", "every one of our", "all properties",
    "brand-wide", "brandwide", "company-wide", "companywide",
    "chain-wide", "chainwide", "every hotel",
)
_PARTICIPATING_MARKERS = (
    "participating location", "participating hotel", "participating propert",
    "select location", "select hotel", "select propert",
    "certain location", "certain hotel", "certain propert",
    "some location", "some hotel", "some propert",
    "where available", "varies by location", "varies by hotel",
    "varies by propert", "may vary by location",
)


def classify_brand_policy_scope(text: str) -> str:
    lowered = (text or "").lower()
    if any(m in lowered for m in _PARTICIPATING_MARKERS):
        return BRAND_SCOPE_PARTICIPATING
    if any(m in lowered for m in _UNIVERSAL_MARKERS):
        return BRAND_SCOPE_UNIVERSAL
    return BRAND_SCOPE_UNKNOWN


def _source_text(pooled_evidence: Sequence[ExtractedEvidence], source_url: str) -> str:
    """All of ONE source's own evidence quotes, concatenated -- a brand
    page typically states its scope once and several facts flow from the
    same page, so the scope check reads the whole source, not just the
    winning field's own sentence."""
    return " ".join(
        e.snapshot_quote for e in pooled_evidence
        if e.source_url == source_url and e.snapshot_quote)


def _winning_evidence(
    pooled_evidence: Sequence[ExtractedEvidence], field: str, value: str,
) -> ExtractedEvidence:
    for e in pooled_evidence:
        if (e.field_name == field and e.proposed_value == value
                and e.support_state != C.SUPPORT_UNSUPPORTED):
            return e
    return None


def gate_high_risk_field_applicability(
    pet_facts: Mapping[str, str],
    pooled_evidence: Sequence[ExtractedEvidence],
    source_applicability: Mapping[str, str],
) -> Tuple[Dict[str, str], Tuple[str, ...]]:
    """Post-``_merge_pet_facts`` gate (Task 5). For each of ``GATED_FIELDS``
    present in ``pet_facts``, keep the value when its winning evidence is
    itself LOCATION_SPECIFIC (the property's own statement); otherwise keep
    it ONLY when the winning source's own text asserts universal brand-wide
    scope AND at least one OTHER included source establishes property
    identity (LOCATION_SPECIFIC for something). Otherwise the field is
    removed (never published as a confirmed fact on an unproven brand-wide
    claim). Returns ``(gated_pet_facts, suppressed_field_names)``; the
    evidence list itself is never mutated (index-preserving)."""
    property_identity_established = any(
        v == C.SOURCE_APPLICABILITY_LOCATION_SPECIFIC for v in source_applicability.values())
    facts = dict(pet_facts)
    suppressed = []
    for field in sorted(GATED_FIELDS):
        if field not in facts:
            continue
        winning = _winning_evidence(pooled_evidence, field, facts[field])
        if winning is None:
            continue
        applicability = source_applicability.get(winning.source_url, "")
        if applicability == C.SOURCE_APPLICABILITY_LOCATION_SPECIFIC:
            continue
        scope = classify_brand_policy_scope(_source_text(pooled_evidence, winning.source_url))
        if scope == BRAND_SCOPE_UNIVERSAL and property_identity_established:
            continue
        del facts[field]
        suppressed.append(field)
    return (facts, tuple(suppressed))
