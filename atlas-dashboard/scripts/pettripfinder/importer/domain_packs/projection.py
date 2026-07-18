"""AES-DATA-003C -- shared capability-projection helper.

AES-DATA-003B proved the projection pattern once, bespoke, inside
``domain_packs/veterinary.py``: turn already evidence-validated facts into
``Capability`` instances, deterministically, with every high-risk claim
requiring direct evidence and never derived from another fact. This module
extracts the REUSABLE part of that pattern -- the field-by-field
true/false/text/conflict projection loop -- into a single generic helper so
the boarding/grooming/pet-store packs do not each carry a near-identical
copy.

Design decision (Task 8, disclosed): veterinary's OWN ``project_capabilities``
in ``veterinary.py`` is left completely UNCHANGED in this phase. It has one
behavior this generic helper deliberately does not generalize -- dynamic,
per-instance high-risk flagging for ``species_served`` based on exotic-
species keyword matching -- and 003B's tests pin its exact behavior. Forcing
veterinary onto this shared path would be a real-risk, zero-benefit change
(veterinary needs no new capability fields this phase). The safe choice,
taken here, is: implement the shared helper, use it for boarding/grooming/
pet-store only, leave veterinary as its own bespoke (but now-proven)
implementation.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import List, Mapping, Sequence, Tuple

from scripts.pettripfinder.importer import constants as C
from scripts.pettripfinder.importer.domain_packs.base import Capability, CapabilityState
from scripts.pettripfinder.importer.models import Conflict, ExtractedEvidence


@dataclass(frozen=True)
class CapabilityProjectionRule:
    """One pack-declared field -> capability projection rule.

    ``field_name`` is the extraction field read from ``pet_facts``;
    ``capability_id`` is the (usually identical) capability slug it projects
    onto. ``value_kind`` is ``"bool"`` (true/false -> SUPPORTED/
    EXPLICITLY_ABSENT) or ``"text"`` (non-empty value -> SUPPORTED with that
    value). ``detail_only=True`` marks a rule that is declared for
    documentation/completeness but never actually projected as a capability
    (kept out of the rules tuple entirely achieves the same effect; the flag
    exists for a future pack that needs a field in both channels)."""

    field_name: str
    capability_id: str
    value_kind: str
    high_risk: bool = False
    detail_only: bool = False


def _first_evidence_index(
    evidence: Sequence[ExtractedEvidence], field_name: str, value: str = None,
) -> int:
    for i, ev in enumerate(evidence):
        if ev.field_name != field_name or ev.support_state == C.SUPPORT_UNSUPPORTED:
            continue
        if value is not None and ev.proposed_value != value:
            continue
        return i
    return -1


def _source_applicable(url: str, source_applicability: Mapping[str, str]) -> bool:
    """AES-DATA-003F (Task 2). ``source_applicability`` is empty/None for
    every pre-003F call site (single-source callers that never opted in),
    and a URL absent from a populated mapping is treated the same way --
    both mean "no applicability classification was computed", which must
    NEVER itself suppress a claim (that would silently change every
    existing high-risk test). Suppression fires ONLY for a URL the caller
    positively classified as something other than LOCATION_SPECIFIC."""
    if not source_applicability:
        return True
    state = source_applicability.get(url)
    if state is None:
        return True
    return state == C.SOURCE_APPLICABILITY_LOCATION_SPECIFIC


def project_capabilities(
    facts: Mapping[str, str],
    evidence: Sequence[ExtractedEvidence],
    rules: Sequence[CapabilityProjectionRule],
    conflicts: Sequence[Conflict] = (),
    source_url: str = "",
    source_applicability: Mapping[str, str] = None,
) -> Tuple[Capability, ...]:
    """Pure function. Iterates ``rules`` in declared (pack) order --
    deterministic output order. For each non-``detail_only`` rule:

    1. If the field is in ``conflicts`` -> CONFLICTED (evidence_index = first
       matching evidence for that field, regardless of value).
    2. Elif the field is missing from ``facts`` -> omitted entirely (never
       UNKNOWN-flooded; mission doctrine #2/#3).
    3. Elif ``value_kind == "bool"``: "true" -> SUPPORTED, "false" ->
       EXPLICITLY_ABSENT, anything else -> omitted.
    4. Elif ``value_kind == "text"``: non-empty -> SUPPORTED with that value;
       empty -> omitted.

    ``high_risk`` is the rule's own declared flag -- never derived from any
    other fact (mission doctrine #5/#13/#14).

    AES-DATA-003F (Task 2): when a rule is ``high_risk`` and its winning
    evidence's own ``source_url`` is positively classified (via
    ``source_applicability``) as something other than LOCATION_SPECIFIC,
    the capability is still emitted -- never silently dropped -- but with
    ``state`` downgraded to UNKNOWN rather than SUPPORTED/EXPLICITLY_ABSENT/
    CONFLICTED, so the evidence stays visible and inspectable (``value=""``,
    ``evidence_index`` still points at the real evidence) while the
    candidate can never read this as a supported location-specific claim.
    Never applied to a non-high-risk rule (doctrine: "do not automatically
    block safe non-high-risk capabilities from the same source").

    Raises via assertion if a caller's rule set ever produces a duplicate
    capability_id (a pack authoring bug, not a runtime data condition)."""
    applicability = source_applicability or {}
    projected_fields = tuple(r.field_name for r in rules if not r.detail_only)
    conflicted_fields = {cf.field_name for cf in conflicts if cf.field_name in projected_fields}

    out: List[Capability] = []
    seen_ids = set()
    for rule in rules:
        if rule.detail_only:
            continue
        field_name = rule.field_name

        if field_name in conflicted_fields:
            idx = _first_evidence_index(evidence, field_name)
            if idx < 0:
                continue
            ev_url = evidence[idx].source_url or source_url
            state = CapabilityState.CONFLICTED.value
            if rule.high_risk and not _source_applicable(ev_url, applicability):
                state = CapabilityState.UNKNOWN.value
            out.append(Capability(
                capability_id=rule.capability_id, state=state,
                value="", high_risk=rule.high_risk, evidence_index=idx,
                source_url=ev_url))
            seen_ids.add(rule.capability_id)
            continue

        if field_name not in facts:
            continue
        value = facts[field_name]

        if rule.value_kind == "bool":
            if value == "true":
                state = CapabilityState.SUPPORTED.value
            elif value == "false":
                state = CapabilityState.EXPLICITLY_ABSENT.value
            else:
                continue
            cap_value = ""
        elif rule.value_kind == "text":
            if not value:
                continue
            state = CapabilityState.SUPPORTED.value
            cap_value = value
        else:
            raise ValueError("unknown CapabilityProjectionRule.value_kind %r" % rule.value_kind)

        idx = _first_evidence_index(evidence, field_name, value)
        if idx < 0:
            continue

        ev_url = evidence[idx].source_url or source_url
        if rule.high_risk and not _source_applicable(ev_url, applicability):
            state = CapabilityState.UNKNOWN.value
            cap_value = ""

        out.append(Capability(
            capability_id=rule.capability_id, state=state, value=cap_value,
            high_risk=rule.high_risk, evidence_index=idx,
            source_url=ev_url))
        seen_ids.add(rule.capability_id)

    assert len(seen_ids) == len(out), "project_capabilities emitted a duplicate capability_id"
    return tuple(out)


def service_evidence_present(capabilities: Sequence[Capability]) -> bool:
    """True when at least one capability carries real (non-UNKNOWN)
    evidence -- SUPPORTED, EXPLICITLY_ABSENT, or CONFLICTED all count, since
    each implies genuine service-relevant evidence exists even if it
    disagrees. Drives the category's no-service-evidence REJECT gate."""
    return any(
        cap.state in (CapabilityState.SUPPORTED.value, CapabilityState.EXPLICITLY_ABSENT.value,
                     CapabilityState.CONFLICTED.value)
        for cap in capabilities)


def high_risk_capability_conflict(capabilities: Sequence[Capability]) -> bool:
    """True when a high-risk capability is CONFLICTED -- drives the
    category's high-risk-conflict REVIEW gate (mission doctrine: a
    conflicting high-risk claim can never silently resolve to READY)."""
    return any(
        cap.state == CapabilityState.CONFLICTED.value and cap.high_risk
        for cap in capabilities)


def has_inapplicable_high_risk_capability(capabilities: Sequence[Capability]) -> bool:
    """AES-DATA-003F (Task 2). True when ``project_capabilities`` downgraded
    a high-risk claim to UNKNOWN because its only evidence came from a
    source not established as applicable to the selected location -- drives
    the ``source_not_location_applicable`` REVIEW reason (never READY on
    the strength of an unproven location-specific claim alone)."""
    return any(
        cap.high_risk and cap.state == CapabilityState.UNKNOWN.value
        for cap in capabilities)
