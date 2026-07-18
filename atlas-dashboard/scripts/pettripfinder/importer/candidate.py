"""AES-DATA-001 importer -- candidate assembly, pipeline orchestration, and
durable JSON persistence (mission sections 14/16/17). Non-artifact: a
candidate is ordinary JSON under a gitignored ``data/import`` root.

The pipeline is:
    fetch -> snapshot(+CAS) -> structured metadata -> LLM extract ->
    evidence validation -> conflict detection -> normalization ->
    policy compose -> recommendation -> CandidateListing.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlsplit

from scripts.pettripfinder.importer import constants as C
from scripts.pettripfinder.importer.category_templates import (
    REQUIRED_CSV_FIELDS,
    allowed_fields,
)
from scripts.pettripfinder.importer.domain_packs import boarding as _boarding_pack_module
from scripts.pettripfinder.importer.domain_packs import grooming as _grooming_pack_module
from scripts.pettripfinder.importer.domain_packs import pet_store as _pet_store_pack_module
from scripts.pettripfinder.importer.domain_packs.base import Capability, CategoryDetail
from scripts.pettripfinder.importer.domain_packs.capabilities import (
    CAPABILITY_SCHEMA_VERSION,
)
from scripts.pettripfinder.importer.domain_packs.registry import default_registry
from scripts.pettripfinder.importer.domain_packs.veterinary import (
    high_risk_capability_conflict as _vet_high_risk_conflict,
    project_capabilities as _vet_project_capabilities,
    service_evidence_present as _vet_service_evidence_present,
)

# AES-DATA-003C: boarding/grooming/pet_store all share the SAME projection-
# module function names (project_capabilities/service_evidence_present/
# high_risk_capability_conflict) via domain_packs/projection.py, so one
# dispatch table drives all three -- veterinary keeps its own bespoke branch
# above (it needs species-keyword high-risk logic the shared helper does not
# generalize; see domain_packs/projection.py's module docstring).
_SERVICE_PACK_MODULES = {
    C.CATEGORY_BOARDING: (
        _boarding_pack_module, C.REASON_NO_BOARDING_SERVICE_EVIDENCE,
        C.REASON_BOARDING_CAPABILITY_CONFLICT),
    C.CATEGORY_GROOMING: (
        _grooming_pack_module, C.REASON_NO_GROOMING_SERVICE_EVIDENCE,
        C.REASON_GROOMING_CAPABILITY_CONFLICT),
    C.CATEGORY_PET_STORE: (
        _pet_store_pack_module, C.REASON_NO_PET_STORE_SERVICE_EVIDENCE,
        C.REASON_PET_STORE_CAPABILITY_CONFLICT),
}
from scripts.pettripfinder.importer.evidence import (
    build_llm_evidence,
    build_structured_evidence,
    cap_quote,
)
from scripts.pettripfinder.importer.models import (
    CandidateListing,
    Conflict,
    ExtractedEvidence,
    FetchResult,
    ImportContext,
    ProposedFact,
    SourceRecord,
    SourceSnapshot,
)
from scripts.pettripfinder.importer import normalize as N
from scripts.pettripfinder.importer.policy_compose import compose_pet_policy
from scripts.pettripfinder.importer.recommend import RecommendationInput, recommend
from scripts.pettripfinder.importer.source_snapshot import (
    build_snapshot,
    snapshot_has_javascript_warning,
)
from scripts.pettripfinder.importer.structured_metadata import (
    StructuredExtraction,
    extract_structured_metadata,
)

# Fields that flow into the CSV identity columns (structured-precedence).
_IDENTITY_FIELDS = ("name", "phone", "address", "city", "state",
                    "postal_code", "website_url")
# Boolean pet/capability facts (normalized to "true"/"false"). Shared,
# category-agnostic set -- _normalize_field_value below dispatches on field
# NAME only, so a field name is safe to add here for any category as long
# as no OTHER category already uses that name for something non-boolean
# (verified: none of the AES-DATA-003B veterinary names below collide with
# any lodging/parks/dining field name). This same set also drives
# aggregate.py's _merge_pet_facts "is this field material enough to
# conflict-detect" check, so extending it here is also what makes a
# disagreeing veterinary capability across sources become a genuine
# aggregate conflict instead of silently picking the first source's value.
_BOOL_PET_FIELDS = frozenset({
    "pets_allowed", "off_leash", "fenced", "small_dog_area", "large_dog_area",
    "water_available", "indoor_prohibited", "patio_or_outdoor_only",
    "dog_menu", "water_or_treats",
    # AES-DATA-003B veterinary boolean capability fields.
    "general_practice", "preventive_care", "wellness_exams", "vaccinations",
    "diagnostics", "surgery", "dentistry", "pharmacy", "prescription_fulfillment",
    "emergency_service", "urgent_care", "open_24h", "walk_ins_accepted",
    "appointment_required", "existing_clients_only", "critical_care",
    # AES-DATA-003C boarding/grooming/pet-store boolean capability fields.
    "boarding_offered", "daycare_offered", "dog_boarding", "cat_boarding",
    "other_species_boarding", "grooming_offered", "medication_administration",
    "live_camera", "reservation_required", "same_day_availability", "pricing_available",
    "dog_grooming", "cat_grooming", "bathing", "nail_trimming", "deshedding",
    "mobile_service",
    "retail_products", "pet_food", "pet_supplies", "prescription_food", "self_wash",
    "vaccination_clinic", "live_animals", "curbside_pickup", "delivery",
    "online_ordering",
})


# --------------------------------------------------------------------------- #
# Source-relationship classification (mission section 17).
# --------------------------------------------------------------------------- #

def _registrable(host: str) -> str:
    host = (host or "").lower().strip(".")
    labels = host.split(".")
    return ".".join(labels[-2:]) if len(labels) >= 2 else host


def classify_source_relationship(
    source_url: str, website_url: str, context: ImportContext,
) -> Tuple[str, str]:
    """Deterministic relationship classification (mission section 17).
    Operator hint wins when supplied and valid; otherwise derived from
    domain analysis. Never a simplistic host-equality rule."""
    hint = (context.source_relationship_hint or "").strip().upper()
    if hint in C.SOURCE_RELATIONSHIPS:
        return (hint, "operator_hint")

    host = urlsplit(source_url).hostname or ""
    host_l = host.lower()
    for marker in C.THIRD_PARTY_HOST_MARKERS:
        if marker in host_l:
            return (C.REL_THIRD_PARTY, "third_party_host:%s" % marker)
    if host_l.endswith(".gov") or host_l.endswith(".gov.us") or ".gov." in host_l:
        return (C.REL_OFFICIAL_GOVERNMENT_DOMAIN, "government_domain")

    web_host = urlsplit(website_url).hostname or ""
    if web_host:
        if host_l == web_host.lower():
            return (C.REL_EXACT_ENTITY_DOMAIN, "source_host_equals_website")
        if _registrable(host_l) == _registrable(web_host):
            return (C.REL_OFFICIAL_BRAND_DOMAIN, "same_registrable_domain")
    # No website to compare; a non-third-party host is not automatically
    # official -> honest UNKNOWN (candidate -> REVIEW).
    return (C.REL_UNKNOWN, "no_website_comparison")


def _source_type_for(relationship: str, context: ImportContext) -> str:
    if context.source_type_hint:
        return context.source_type_hint.strip()
    return {
        C.REL_EXACT_ENTITY_DOMAIN: "OFFICIAL_PROPERTY",
        C.REL_OFFICIAL_PROPERTY_SUBDOMAIN: "OFFICIAL_PROPERTY",
        C.REL_OFFICIAL_BRAND_DOMAIN: "OFFICIAL_BRAND",
        C.REL_OFFICIAL_GROUP_DOMAIN: "OFFICIAL_GROUP",
        C.REL_OFFICIAL_GOVERNMENT_DOMAIN: "OFFICIAL_CITY",
        C.REL_OFFICIAL_HOSTED_SYSTEM: "OFFICIAL_PROPERTY",
        C.REL_OPERATOR_CONFIRMED_OFFICIAL: "OFFICIAL_PROPERTY",
    }.get(relationship, "")


# --------------------------------------------------------------------------- #
# Evidence assembly + conflict detection.
# --------------------------------------------------------------------------- #

def _normalize_field_value(field: str, value: str, city: str = "", state: str = "") -> str:
    if field == "phone":
        return N.normalize_phone(value)
    if field == "state":
        return N.normalize_state(value)
    if field == "postal_code":
        return N.normalize_postal(value)
    if field == "website_url":
        return N.normalize_url(value)
    if field == "address":
        return N.normalize_address(value, city, state)
    if field == "pet_fee":
        return N.normalize_fee(value)
    if field == "weight_limit":
        return N.normalize_weight(value)
    if field == "pet_count_limit":
        return N.normalize_count(value)
    if field in _BOOL_PET_FIELDS:
        b = N.normalize_bool(value)
        return "" if b is None else ("true" if b else "false")
    return N.normalize_whitespace(value)


# --------------------------------------------------------------------------- #
# Per-page evidence collection (AES-DATA-002A seam).
#
# ``_collect_page_evidence`` performs structured+LLM evidence collection and
# intra-page (structured-vs-LLM) conflict detection for ONE page, exactly as
# the prior monolithic ``_assemble`` did -- but stops before candidate-level
# resolution: it never resolves a final name or phone (those require
# cross-source pooling by a future aggregator; today ``_resolve_page_fields``
# performs that resolution for the single supplied page, unchanged). This is
# a mechanical split with no semantic change; ``_assemble`` remains a thin
# composition of the two phases and every existing call site is unaffected.
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class PageEvidence:
    """One page's collected evidence, prior to candidate-level resolution.
    Internal to the importer pipeline; never persisted."""

    evidence: Tuple[ExtractedEvidence, ...]
    conflicts: Tuple[Conflict, ...]
    accepted: Dict[str, str]
    # Each candidate tuple is (value, quote, char_start, char_end, method,
    # support, source_url).
    name_candidates: Tuple[Tuple[str, str, int, int, str, str, str], ...]
    phone_candidates: Tuple[Tuple[str, str, int, int, str, str, str], ...]
    required_evidence_mismatch: bool


def _collect_page_evidence(
    snapshot: SourceSnapshot,
    structured: StructuredExtraction,
    llm_facts: Tuple[ProposedFact, ...],
    category: str,
    source_url: str,
) -> PageEvidence:
    """Merge structured + LLM evidence for one page and detect intra-page
    conflicts. Name and phone candidates are pooled but NOT resolved here."""
    struct_by_field = structured.by_field()

    # Structured evidence first (SUPPORTED, deterministic). ``phone`` is
    # handled by role-aware resolution below, not the generic field path.
    evidence: List[ExtractedEvidence] = []
    accepted: Dict[str, str] = {}
    # Candidate pool tuples carry ``source_url`` as their last element (AES-
    # DATA-002B) so a future cross-source pool can attribute each candidate's
    # evidence to the right source; single-page resolution always tags with
    # this page's own ``source_url``, so single-source behavior is unchanged.
    phone_candidates: List[Tuple[str, str, int, int, str, str, str]] = []
    name_candidates: List[Tuple[str, str, int, int, str, str, str]] = []
    for field, sf in struct_by_field.items():
        if field == "phone":
            phone_candidates.append(
                (sf.value, sf.quote, -1, -1, sf.method, C.SUPPORT_SUPPORTED, source_url))
            continue
        if field == "name":
            name_candidates.append(
                (sf.value, sf.quote, -1, -1, sf.method, C.SUPPORT_SUPPORTED, source_url))
            continue
        norm = _normalize_field_value(field, sf.value)
        if not norm:
            continue
        evidence.append(build_structured_evidence(
            field, norm, sf.quote, source_url, sf.method))
        accepted[field] = norm

    # LLM evidence (span-validated).
    conflicts: List[Conflict] = []
    required_mismatch = False
    allowed = allowed_fields(category)
    for fact in llm_facts:
        if fact.field_name not in allowed:
            continue
        ev = build_llm_evidence(fact, snapshot.normalized_text, source_url)
        if ev.support_state == C.SUPPORT_UNSUPPORTED:
            if fact.field_name == "pets_allowed" and "pets_allowed" not in accepted:
                required_mismatch = True
            # Keep the failed evidence visible in the record but never publish it.
            evidence.append(ev)
            continue
        if fact.field_name == "phone":
            phone_candidates.append(
                (ev.proposed_value, ev.snapshot_quote, ev.char_start, ev.char_end,
                 C.METHOD_LLM_TEXT, ev.support_state, source_url))
            continue
        if fact.field_name == "name":
            name_candidates.append(
                (ev.proposed_value, ev.snapshot_quote, ev.char_start, ev.char_end,
                 C.METHOD_LLM_TEXT, ev.support_state, source_url))
            continue
        norm = _normalize_field_value(fact.field_name, ev.proposed_value)
        if not norm:
            continue
        if fact.field_name in accepted and accepted[fact.field_name] != norm:
            # Conflict: structured vs LLM disagree on the same field.
            struct_ev = next(
                (e for e in evidence if e.field_name == fact.field_name
                 and e.extraction_method != C.METHOD_LLM_TEXT), None)
            comp = (accepted[fact.field_name], norm)
            conflicts.append(Conflict(
                field_name=fact.field_name,
                competing_values=comp,
                evidence=tuple(e for e in (struct_ev, ev) if e is not None),
                precedence_note="structured_metadata_over_llm_text",
                resolution_status="UNRESOLVED",
            ))
            # Keep the structured value as primary; record LLM evidence too.
            evidence.append(ExtractedEvidence(
                field_name=ev.field_name, proposed_value=norm,
                source_wording=ev.source_wording, source_url=source_url,
                snapshot_quote=ev.snapshot_quote, char_start=ev.char_start,
                char_end=ev.char_end, extraction_method=C.METHOD_LLM_TEXT,
                support_state=C.SUPPORT_AMBIGUOUS,
                warnings=ev.warnings + (C.REASON_CONFLICTING_EVIDENCE,)))
        else:
            evidence.append(ExtractedEvidence(
                field_name=ev.field_name, proposed_value=norm,
                source_wording=ev.source_wording, source_url=source_url,
                snapshot_quote=ev.snapshot_quote, char_start=ev.char_start,
                char_end=ev.char_end, extraction_method=ev.extraction_method,
                support_state=ev.support_state, warnings=ev.warnings))
            accepted.setdefault(fact.field_name, norm)

    return PageEvidence(
        evidence=tuple(evidence), conflicts=tuple(conflicts), accepted=accepted,
        name_candidates=tuple(name_candidates), phone_candidates=tuple(phone_candidates),
        required_evidence_mismatch=required_mismatch)


def _expected_city_support(
    accepted: Dict[str, str], snapshot_text: str, context: ImportContext,
) -> Tuple[str, str, bool]:
    """Whether the operator's expected city is supported by this page's own
    geography (an accepted city/state agreeing with it, or the city's literal
    presence in the page text), for the context-bound expected-city (and
    expected-city+state, AES-DATA-002D) name-suffix rules. Returns
    ``(expected_city, expected_state, city_supported)``. Reused for both a
    single page (``_resolve_page_fields``) and an aggregate's PRIMARY page
    (AES-DATA-002B)."""
    exp_city = N.normalize_city(context.expected_city)
    exp_state = N.normalize_state(context.expected_state)
    page_city = accepted.get("city", "")
    page_state = accepted.get("state", "")
    city_supported = bool(exp_city)
    if city_supported:
        if page_city:
            city_supported = page_city.lower() == exp_city.lower()
        else:
            city_supported = exp_city.lower() in (snapshot_text or "").lower()
        if city_supported and exp_state and page_state and page_state != exp_state:
            city_supported = False
    return (exp_city, exp_state, city_supported)


def _resolve_page_fields(
    page: PageEvidence,
    snapshot: SourceSnapshot,
    category: str,
    source_url: str,
    context: ImportContext,
) -> Tuple[List[ExtractedEvidence], List[Conflict], Dict[str, str], bool]:
    """Candidate-level resolution over one page's collected evidence: phone
    role precedence, entity-name canonicalization/reconciliation, and derived
    dual facts. Returns ``(evidence, conflicts, accepted_values,
    required_evidence_mismatch)`` -- identical shape and semantics to the
    prior monolithic ``_assemble``."""
    evidence: List[ExtractedEvidence] = list(page.evidence)
    conflicts: List[Conflict] = list(page.conflicts)
    accepted: Dict[str, str] = dict(page.accepted)

    # Role-aware phone resolution (AES-DATA-001 defect A): pick the property
    # number over a central reservation/brand number by precedence; only a
    # same-role collision (or unresolved competing numbers) is a conflict.
    primary_phone, phone_evidence, phone_conflicts = _resolve_phone(
        list(page.phone_candidates))
    evidence.extend(phone_evidence)
    conflicts.extend(phone_conflicts)
    if primary_phone:
        accepted["phone"] = primary_phone

    # Entity-name resolution (AES-DATA-001 defect): an Open Graph/page title
    # carrying site branding is not a material conflict with the clean entity
    # name; canonicalize and select by precedence, reconcile every remaining
    # candidate against the resolved name (never raw pairwise), and only
    # conflict on genuinely different names. The expected-city suffix rule is
    # context-bound: it needs the operator's expected city AND page-geography
    # support for it (page city matches when extracted; otherwise the city
    # must at least appear in the snapshot text; a conflicting page city or
    # state withdraws support).
    exp_city, exp_state, city_supported = _expected_city_support(
        accepted, snapshot.normalized_text, context)
    primary_name, name_evidence, name_conflicts = _resolve_name(
        list(page.name_candidates), context, snapshot.normalized_text,
        expected_city=exp_city, expected_state=exp_state,
        expected_city_supported=city_supported)
    evidence.extend(name_evidence)
    conflicts.extend(name_conflicts)
    if primary_name:
        accepted["name"] = primary_name

    # Cross-derive co-stated numeric pet facts (defect C): a single sentence
    # can support both pet_count_limit and weight_limit; derive a missing one
    # from an already-SUPPORTED sibling quote (same span, honestly supported).
    _derive_dual_facts(snapshot, evidence, accepted, category, source_url)

    return (evidence, conflicts, accepted, page.required_evidence_mismatch)


def _assemble(
    snapshot: SourceSnapshot,
    structured: StructuredExtraction,
    llm_facts: Tuple[ProposedFact, ...],
    category: str,
    source_url: str,
    context: ImportContext,
) -> Tuple[List[ExtractedEvidence], List[Conflict], Dict[str, str], bool]:
    """Thin composition layer (AES-DATA-002A seam): collect per-page evidence,
    then resolve candidate-level fields. Signature and behavior are unchanged
    from the prior monolithic implementation."""
    page = _collect_page_evidence(snapshot, structured, llm_facts, category, source_url)
    return _resolve_page_fields(page, snapshot, category, source_url, context)


# --------------------------------------------------------------------------- #
# Phone role resolution (defect A).
# --------------------------------------------------------------------------- #

def _resolve_phone(
    phone_candidates: List[Tuple[str, str, int, int, str, str, str]],
) -> Tuple[str, List[ExtractedEvidence], List[Conflict]]:
    """Classify each candidate number, preserve all as evidence (with a
    ``phone_role`` marker), pick the single production number by precedence,
    and flag a conflict only for a same-role collision or unresolved
    materially-competing numbers. Each candidate tuple ends with its own
    ``source_url`` (AES-DATA-002B), so a pooled cross-source call attributes
    evidence to the right source; a single page just tags every candidate
    with its own URL, so single-source behavior is unchanged."""
    entries: List[Dict[str, str]] = []
    seen_numbers = set()
    for raw, quote, cs, ce, method, support, cand_source_url in phone_candidates:
        num = N.normalize_phone(raw)
        if not num or num in seen_numbers:
            continue
        seen_numbers.add(num)
        entries.append({
            "num": num, "role": N.classify_phone_role(raw, quote),
            "quote": quote, "cs": cs, "ce": ce, "method": method, "support": support,
            "source_url": cand_source_url})
    if not entries:
        return ("", [], [])

    prec = {r: i for i, r in enumerate(N.PHONE_ROLE_PRECEDENCE)}
    ordered = sorted(entries, key=lambda e: prec.get(e["role"], len(prec)))  # stable

    evidences = [ExtractedEvidence(
        field_name="phone", proposed_value=e["num"], source_wording=e["quote"],
        source_url=e["source_url"], snapshot_quote=e["quote"], char_start=e["cs"],
        char_end=e["ce"], extraction_method=e["method"], support_state=e["support"],
        warnings=("phone_role:%s" % e["role"],)) for e in ordered]

    best_role = ordered[0]["role"]
    numbers_at_best = {e["num"] for e in entries if e["role"] == best_role}
    distinct = {e["num"] for e in entries}
    conflicts: List[Conflict] = []
    if len(numbers_at_best) >= 2 or (
        best_role == N.PHONE_ROLE_UNKNOWN and len(distinct) >= 2
    ):
        conflicts.append(Conflict(
            field_name="phone", competing_values=tuple(e["num"] for e in ordered),
            evidence=tuple(evidences), precedence_note="phone_role_precedence",
            resolution_status="UNRESOLVED"))
    return (ordered[0]["num"], evidences, conflicts)


# --------------------------------------------------------------------------- #
# Entity-name resolution (live park-name defect).
# --------------------------------------------------------------------------- #

_NAME_METHOD_RANK = {
    C.METHOD_LLM_TEXT: 0,        # visible heading / LLM entity name
    C.METHOD_JSON_LD: 1, C.METHOD_MICRODATA: 1,   # structured entity name
    C.METHOD_OPEN_GRAPH: 2, C.METHOD_META: 2,     # page/OG title (branded)
}


def _hint_supported(hint: str, entries: List[Dict[str, str]], snapshot_text: str) -> bool:
    """An operator name hint is authoritative only when the page supports it:
    compatible with a page-derived candidate, or present in the snapshot."""
    for e in entries:
        if N.names_compatible(hint, e["value"]):
            return True
    return N.normalize_name(hint).lower() in N.normalize_name(snapshot_text or "").lower()


def _reconciles_with_resolved(
    resolved: str, candidate: str, expected_city: str,
    expected_city_supported: bool, expected_state: str = "",
) -> bool:
    """A name candidate reconciles with the resolved authoritative name when
    it denotes the same entity (title-segment rules), when its page-purpose/
    brand-stripped form equals the resolved name, or when the pair differs
    only by a trailing expected-city (or expected-city+state, AES-DATA-002D)
    qualifier under the context-bound suffix rules -- in EITHER direction,
    because the resolved page-derived name may itself be the brand-short
    form while a branded title reconciles to "<base> <expected_city>" (live
    Land-Grant regression, candidate landgrantbrewing-com-e70ad5c876). A raw
    branded title is always reconciled through the stripping rules first --
    never compared directly against a shorter alternate. ``expected_state``
    defaults to "" so every pre-002D positional 4-arg call site (including
    tests that exercise city-only reconciliation) is unaffected -- the new
    city+state and legal-suffix rules below simply never fire without it."""
    if N.names_compatible(resolved, candidate):
        return True
    reconciled = N.clean_entity_name(candidate)
    if reconciled.lower() == N.normalize_name(resolved).lower():
        return True
    if N.expected_city_suffix_compatible(
            resolved, reconciled, expected_city, expected_city_supported):
        return True
    if N.expected_city_suffix_compatible(
            reconciled, resolved, expected_city, expected_city_supported):
        return True
    # City+state trailing qualifier (AES-DATA-002D live taproom-title
    # defect): "<base> <city> <state>" vs "<base> <city>", either direction.
    if N.expected_city_state_suffix_compatible(
            resolved, reconciled, expected_city, expected_state, expected_city_supported):
        return True
    if N.expected_city_state_suffix_compatible(
            reconciled, resolved, expected_city, expected_state, expected_city_supported):
        return True
    # Terminal legal-entity suffix (AES-DATA-002D live taproom-title
    # defect): strip a trailing Company/Co/Co. from EITHER side, then the
    # result must STILL pass the existing expected-city suffix rule -- the
    # suffix strip alone never grants reconciliation.
    stripped_candidate = N.strip_legal_suffix(reconciled)
    if stripped_candidate != reconciled:
        if (N.names_compatible(resolved, stripped_candidate)
                or N.expected_city_suffix_compatible(
                    resolved, stripped_candidate, expected_city, expected_city_supported)
                or N.expected_city_suffix_compatible(
                    stripped_candidate, resolved, expected_city, expected_city_supported)):
            return True
    stripped_resolved = N.strip_legal_suffix(resolved)
    if stripped_resolved != resolved:
        if (N.names_compatible(stripped_resolved, reconciled)
                or N.expected_city_suffix_compatible(
                    stripped_resolved, reconciled, expected_city, expected_city_supported)
                or N.expected_city_suffix_compatible(
                    reconciled, stripped_resolved, expected_city, expected_city_supported)):
            return True
    return False


def _resolve_name(
    name_candidates: List[Tuple[str, str, int, int, str, str, str]],
    context: ImportContext, snapshot_text: str,
    *, expected_city: str = "", expected_state: str = "",
    expected_city_supported: bool = False,
) -> Tuple[str, List[ExtractedEvidence], List[Conflict]]:
    """Preserve all name evidence, select the entity name by precedence
    (operator hint > LLM/heading > structured > branded title), then
    reconcile every remaining candidate against the PUBLISHED authoritative
    name (AES-DATA-002D fix: reconciliation must test against ``primary`` --
    the name actually selected and shown to the operator -- not the interim
    ``resolved`` pick that a supported operator hint can override; testing
    against ``resolved`` let a candidate that only reconciles with the hint
    form spuriously conflict). Each pooled candidate is evaluated
    INDEPENDENTLY: only candidates that fail reconciliation enter the
    conflict's ``competing_values``/``evidence`` -- a candidate that already
    reconciles is never dragged into an unresolved conflict merely because
    a DIFFERENT candidate failed (live Land-Grant taproom-title regression,
    candidate landgrantbrewing-com-1b02fab45f). Every candidate's own
    evidence row is still returned unconditionally regardless of conflict
    membership. Each candidate tuple ends with its own ``source_url``
    (AES-DATA-002B): a pooled cross-source call attributes evidence to the
    right source; a single page tags every candidate with its own URL, so
    single-source behavior is unchanged."""
    entries: List[Dict[str, str]] = []
    for value, quote, cs, ce, method, support, cand_source_url in name_candidates:
        nv = N.normalize_name(value)
        if not nv:
            continue
        entries.append({"value": nv, "quote": quote, "cs": cs, "ce": ce,
                        "method": method, "support": support,
                        "source_url": cand_source_url})
    if not entries:
        return ("", [], [])

    evidences = [ExtractedEvidence(
        field_name="name", proposed_value=e["value"], source_wording=e["quote"],
        source_url=e["source_url"], snapshot_quote=e["quote"], char_start=e["cs"],
        char_end=e["ce"], extraction_method=e["method"], support_state=e["support"],
        warnings=("name_source:%s" % e["method"],)) for e in entries]

    # Resolve the authoritative page-derived name FIRST (AES-DATA-001 final
    # restaurant-name defect: raw alternates were compared pairwise, so an
    # already-reconcilable branded title still conflicted with a supported
    # brand-short form).
    best = min(entries, key=lambda e: _NAME_METHOD_RANK.get(e["method"], 3))
    resolved = N.clean_entity_name(best["value"])

    # Select the PUBLISHED name (operator hint, when the page supports it,
    # otherwise the resolved pick) BEFORE conflict detection -- every
    # candidate reconciles against what is actually published, not an
    # interim value the hint may override.
    hint = N.normalize_name(context.candidate_name)
    hint_directly_anchored = bool(hint) and any(
        N.names_compatible(hint, e["value"]) for e in entries)
    if hint and _hint_supported(hint, entries, snapshot_text):
        primary = hint
    else:
        primary = resolved

    # A candidate reconciles against the published ``primary``. When the
    # hint itself is NOT directly anchored to any real page candidate (its
    # only support is the weaker literal-substring-in-snapshot-text path --
    # e.g. an operator hint like "Scioto Audubon Metro Park" that adds its
    # own descriptive words no page title could ever be expected to
    # suffix-match), every candidate ALSO gets a second chance against the
    # raw page-derived ``resolved`` pick, preserving the established,
    # page-evidence-only reconciliation graph. This fallback is deliberately
    # withheld once the hint IS directly anchored to a real candidate
    # (``names_compatible`` succeeded) -- otherwise a DIFFERENT, genuinely
    # unrelated candidate could hide behind a trivial self-match against
    # ``resolved`` even under a wrong expected-city context (live Land-Grant
    # Dublin safety test). Both anchors go through the identical
    # deterministic rules -- never a fuzzy widening.
    allow_resolved_fallback = primary != resolved and not hint_directly_anchored

    conflicts: List[Conflict] = []
    failing_idx = [
        i for i, e in enumerate(entries)
        if not (_reconciles_with_resolved(
                    primary, e["value"], expected_city, expected_city_supported, expected_state)
                or (allow_resolved_fallback and _reconciles_with_resolved(
                        resolved, e["value"], expected_city, expected_city_supported, expected_state)))
    ]
    if failing_idx:
        failing_values = tuple(dict.fromkeys(entries[i]["value"] for i in failing_idx))
        conflicts.append(Conflict(
            field_name="name",
            competing_values=(primary,) + failing_values,
            evidence=tuple(evidences[i] for i in failing_idx),
            precedence_note="entity_name_canonicalization",
            resolution_status="UNRESOLVED"))

    return (primary, evidences, conflicts)


# --------------------------------------------------------------------------- #
# Co-stated numeric-fact derivation (defect C).
# --------------------------------------------------------------------------- #

_DUAL_FACT_DERIVERS = {
    "pet_count_limit": N.normalize_count,
    "weight_limit": N.normalize_weight,
}


def _sentence_bounds(text: str, start: int, end: int) -> Tuple[int, int]:
    s = text.rfind(".", 0, max(start, 0)) + 1
    e = text.find(".", max(end, 0))
    e = len(text) if e < 0 else e + 1
    return (s, e)


def _derive_dual_facts(snapshot, evidence, accepted, category, source_url) -> None:
    allowed = allowed_fields(category)
    for target, fn in _DUAL_FACT_DERIVERS.items():
        if target in accepted or target not in allowed:
            continue
        for ev in list(evidence):
            if ev.support_state == C.SUPPORT_UNSUPPORTED or ev.field_name == target:
                continue
            val, quote, cs, ce = fn(ev.snapshot_quote), ev.snapshot_quote, ev.char_start, ev.char_end
            if not val and ev.char_start >= 0:
                s, e = _sentence_bounds(snapshot.normalized_text, ev.char_start, ev.char_end)
                sentence = snapshot.normalized_text[s:e]
                derived = fn(sentence)
                if derived:
                    val, quote, cs, ce = derived, cap_quote(sentence)[0], s, e
            if val:
                evidence.append(ExtractedEvidence(
                    field_name=target, proposed_value=val, source_wording=ev.source_wording,
                    source_url=source_url, snapshot_quote=quote, char_start=cs, char_end=ce,
                    extraction_method=ev.extraction_method, support_state=C.SUPPORT_SUPPORTED,
                    warnings=("derived_from:%s" % ev.field_name,)))
                accepted[target] = val
                break


# --------------------------------------------------------------------------- #
# Candidate id.
# --------------------------------------------------------------------------- #

def _slug(text: str) -> str:
    return re.sub(r"-{2,}", "-", re.sub(r"[^a-z0-9]+", "-", (text or "").lower())).strip("-")


def make_candidate_id(requested_url: str, observed_at: str) -> str:
    host = urlsplit(requested_url).hostname or "source"
    short = hashlib.sha256(("%s|%s" % (requested_url, observed_at)).encode("utf-8")).hexdigest()[:10]
    return "%s-%s" % (_slug(host)[:40] or "source", short)


# --------------------------------------------------------------------------- #
# Pipeline.
# --------------------------------------------------------------------------- #

def _shallow_snapshot(fetch: FetchResult, observed_at: str) -> SourceSnapshot:
    return SourceSnapshot(
        requested_url=fetch.requested_url,
        final_url=fetch.final_url or fetch.requested_url,
        observed_at=observed_at,
        http_status=fetch.http_status,
        content_type=fetch.content_type,
        redirect_chain=fetch.redirect_chain,
        page_title="", canonical_url="",
        response_header_subset=fetch.response_headers,
        raw_content_hash="", normalized_text_hash="", normalized_text="",
        extraction_version=C.EXTRACTION_VERSION,
        fetch_warnings=(fetch.reason,) if fetch.reason else (),
        source_relationship=C.REL_UNKNOWN,
    )


@dataclass(frozen=True)
class SourceImportResult:
    """One source's per-page import outcome (AES-DATA-002A primitive): the
    unresolved building blocks a future cross-source aggregator needs.
    Internal to the importer pipeline; never persisted. ``run_import`` today
    consumes this for the existing single-source pipeline with no behavior
    change; a future aggregator would call ``import_source`` once per
    supplied URL and pool the ``page_evidence`` across sources before
    candidate-level resolution."""

    requested_url: str
    final_url: str = ""
    usable: bool = False
    fetch_result: Optional[FetchResult] = None
    fetch_reason: str = ""
    javascript_only: bool = False
    snapshot: Optional[SourceSnapshot] = None
    page_evidence: Optional[PageEvidence] = None
    source_relationship: str = ""
    source_relationship_reason: str = ""
    extraction_provider: str = ""
    extraction_model: str = ""
    prompt_version: str = ""
    extraction_ok: bool = True
    extraction_error: str = ""
    multi_entity: bool = False
    warnings: Tuple[str, ...] = ()
    # AES-WORK-001C (additive): real provider usage for THIS source's one
    # extraction call; 0 when no extraction was attempted (fetch/JS-only
    # short circuit) or the extractor is static.
    input_tokens: int = 0
    output_tokens: int = 0
    provider_request_count: int = 0


def import_source(
    url: str,
    context: ImportContext,
    *,
    fetcher,
    extractor,
    cas,
    observed_at: str,
) -> SourceImportResult:
    """Fetch, snapshot, and collect per-page evidence for ONE official URL.
    Stops before candidate-level resolution (name/phone pooling, derived dual
    facts) -- those require the full candidate context and, for a future
    aggregator, cross-source pooling; they stay in ``_resolve_page_fields``.
    Mirrors the fetch/snapshot/extraction preamble ``run_import`` used to
    perform inline, with identical behavior at every step."""
    category = context.category
    fetch = fetcher.fetch(url)

    if not fetch.ok:
        return SourceImportResult(
            requested_url=url, final_url=fetch.final_url or url, usable=False,
            fetch_result=fetch, fetch_reason=fetch.reason)

    # relationship needs the extracted website; classify after extraction, but
    # snapshot needs a relationship string -> start UNKNOWN, refine below.
    snapshot = build_snapshot(fetch, cas, observed_at, C.REL_UNKNOWN)
    if snapshot_has_javascript_warning(snapshot):
        return SourceImportResult(
            requested_url=url, final_url=snapshot.final_url, usable=False,
            fetch_result=fetch, fetch_reason=C.REASON_JAVASCRIPT_RENDERED,
            javascript_only=True, snapshot=snapshot, warnings=snapshot.fetch_warnings)

    html_bytes = cas.get_bytes(snapshot.raw_content_hash)
    structured = extract_structured_metadata(_decode(html_bytes))
    extraction = extractor.extract(
        snapshot.normalized_text, category, allowed_fields(category))

    source_url = snapshot.final_url
    page = _collect_page_evidence(snapshot, structured, extraction.facts, category, source_url)

    website_url = page.accepted.get("website_url", "")
    relationship, rel_reason = classify_source_relationship(
        source_url, website_url or source_url, context)

    warnings = list(snapshot.fetch_warnings)
    if not extraction.ok:
        warnings.append(extraction.error)

    return SourceImportResult(
        requested_url=url, final_url=source_url, usable=True, fetch_result=fetch,
        snapshot=snapshot, page_evidence=page,
        source_relationship=relationship, source_relationship_reason=rel_reason,
        extraction_provider=extraction.provider, extraction_model=extraction.model,
        prompt_version=extraction.prompt_version, extraction_ok=extraction.ok,
        extraction_error=extraction.error, multi_entity=structured.multi_entity,
        warnings=tuple(warnings),
        input_tokens=extraction.input_tokens, output_tokens=extraction.output_tokens,
        provider_request_count=extraction.provider_request_count)


def run_import(
    url: str,
    context: ImportContext,
    *,
    fetcher,
    extractor,
    cas,
    observed_at: str,
    created_at: str,
) -> CandidateListing:
    """Execute the full import pipeline for one official URL. Re-expressed
    over ``import_source`` (AES-DATA-002A seam): the per-page fetch/snapshot/
    extraction/collection preamble now lives there; this function performs
    exactly the same candidate-level resolution and finalization as before,
    with no change in output."""
    category = context.category
    source = import_source(
        url, context, fetcher=fetcher, extractor=extractor, cas=cas,
        observed_at=observed_at)

    # --- fetch-level short circuit (REVIEW/REJECT) --------------------------
    if source.snapshot is None:
        snapshot = _shallow_snapshot(source.fetch_result, observed_at)
        rec, reasons = recommend(RecommendationInput(
            fetch_ok=False, fetch_reason=source.fetch_reason, source_relationship=C.REL_UNKNOWN,
            entity_identified=False, category_resolved=bool(N.normalize_category_id(category)),
            missing_required=(), pet_policy_present=False, pets_allowed_state="",
            has_material_conflict=False, multi_entity=False,
            required_evidence_mismatch=False, ambiguous_present=False,
            extraction_ok=True, text_truncated=False))
        return _finalize(url, context, snapshot, [], [], {}, "", (), rec, reasons,
                         C.REL_UNKNOWN, "fetch_failed:" + source.fetch_reason, "", "",
                         observed_at, created_at, category_conf=C.SUPPORT_UNSUPPORTED,
                         geo_conf=C.SUPPORT_UNSUPPORTED, multi_entity=False)

    # --- snapshot + JS-only guard ------------------------------------------
    if source.javascript_only:
        rec, reasons = (C.RECOMMEND_REVIEW, (C.REASON_JAVASCRIPT_RENDERED,))
        return _finalize(url, context, source.snapshot, [], [], {}, "", (), rec, reasons,
                         C.REL_UNKNOWN, "javascript_rendered", "", "",
                         observed_at, created_at, category_conf=C.SUPPORT_UNSUPPORTED,
                         geo_conf=C.SUPPORT_UNSUPPORTED, multi_entity=False)

    # --- candidate-level resolution -----------------------------------------
    snapshot = source.snapshot
    source_url = snapshot.final_url
    evidence, conflicts, accepted, required_mismatch = _resolve_page_fields(
        source.page_evidence, snapshot, category, source_url, context)

    # --- relationship + source_type ----------------------------------------
    website_url = accepted.get("website_url", "")
    relationship, rel_reason = source.source_relationship, source.source_relationship_reason
    source_type = _source_type_for(relationship, context)

    # --- CSV fields + pet facts --------------------------------------------
    city = accepted.get("city") or N.normalize_city(context.expected_city)
    state = accepted.get("state") or N.normalize_state(context.expected_state)
    address_raw = accepted.get("address", "")

    # Postal derivation (defect B): a supported full address that carries a
    # valid ZIP fills an otherwise-empty postal_code, from the SAME address
    # evidence span -- never fabricated from city/state alone. Derive before
    # the address street is stripped of its trailing locality/ZIP.
    postal = accepted.get("postal_code", "")
    if not postal:
        derived_zip = N.extract_postal_from_address(address_raw)
        if derived_zip:
            postal = derived_zip
            addr_ev = next((e for e in evidence if e.field_name == "address"
                            and e.support_state != C.SUPPORT_UNSUPPORTED), None)
            if addr_ev is not None:
                evidence.append(ExtractedEvidence(
                    field_name="postal_code", proposed_value=postal,
                    source_wording=addr_ev.source_wording, source_url=source_url,
                    snapshot_quote=addr_ev.snapshot_quote, char_start=addr_ev.char_start,
                    char_end=addr_ev.char_end, extraction_method=addr_ev.extraction_method,
                    support_state=C.SUPPORT_SUPPORTED, warnings=("derived_from:address",)))

    address = N.normalize_address(address_raw, city, state)
    name = accepted.get("name") or N.normalize_name(context.candidate_name)
    if not website_url:
        website_url = source_url

    pet_facts: Dict[str, str] = {}
    for ev in evidence:
        if ev.support_state == C.SUPPORT_UNSUPPORTED:
            continue
        if ev.field_name in allowed_fields(category) and ev.field_name not in _IDENTITY_FIELDS:
            pet_facts.setdefault(ev.field_name, ev.proposed_value)
    pet_policy = compose_pet_policy(pet_facts, category)

    # --- AES-DATA-003B: veterinary capability projection --------------------
    # Projected AFTER ``evidence``/``conflicts`` are final (Task 7: evidence
    # indices must point at the final CandidateListing.evidence tuple).
    # ``()``/``None``/``""`` for every non-veterinary category -- legacy
    # candidates keep the AES-DATA-003A defaults untouched.
    capabilities: Tuple[Capability, ...] = ()
    category_detail: Optional[CategoryDetail] = None
    pack_id, pack_version, capability_schema_version = "", "", ""
    service_evidence_present = None
    no_service_evidence_reason = C.REASON_NO_PET_EVIDENCE
    high_risk_conflict = False
    high_risk_conflict_reason = C.REASON_VETERINARY_CAPABILITY_CONFLICT
    if category == C.CATEGORY_VETERINARY:
        pack = default_registry.for_category(category)
        capabilities = _vet_project_capabilities(
            pet_facts, evidence, conflicts, source_url)
        pack_id, pack_version = pack.pack_id, pack.pack_version
        capability_schema_version = CAPABILITY_SCHEMA_VERSION
        service_evidence_present = _vet_service_evidence_present(capabilities)
        no_service_evidence_reason = C.REASON_NO_VETERINARY_SERVICE_EVIDENCE
        high_risk_conflict = _vet_high_risk_conflict(capabilities)
        hours = pet_facts.get("hours", "")
        if hours:
            category_detail = CategoryDetail(
                detail_type="veterinary", detail_schema_version=pack.detail_schema_version,
                fields=(("hours", hours),))
    elif category in _SERVICE_PACK_MODULES:
        pack_module, no_evidence_reason, conflict_reason = _SERVICE_PACK_MODULES[category]
        pack = default_registry.for_category(category)
        capabilities = pack_module.project_capabilities(
            pet_facts, evidence, conflicts, source_url)
        pack_id, pack_version = pack.pack_id, pack.pack_version
        capability_schema_version = CAPABILITY_SCHEMA_VERSION
        service_evidence_present = pack_module.service_evidence_present(capabilities)
        no_service_evidence_reason = no_evidence_reason
        high_risk_conflict = pack_module.high_risk_capability_conflict(capabilities)
        high_risk_conflict_reason = conflict_reason
        hours = pet_facts.get("hours", "")
        if hours:
            category_detail = CategoryDetail(
                detail_type=category, detail_schema_version=pack.detail_schema_version,
                fields=(("hours", hours),))

    proposed = {
        "name": name, "category": N.normalize_category_id(category),
        "address": address, "city": city, "state": state,
        "postal_code": postal,
        "phone": accepted.get("phone", ""), "website_url": website_url,
        "source_url": source_url, "source_type": source_type,
        "observed_at": observed_at, "rating": "", "pet_policy": pet_policy,
        "canonical": "",
    }

    # --- signals for recommendation ----------------------------------------
    missing = tuple(f for f in REQUIRED_CSV_FIELDS if not proposed.get(f, "").strip())
    pets_state = pet_facts.get("pets_allowed", "")
    category_conf = C.SUPPORT_SUPPORTED if proposed["category"] else C.SUPPORT_UNSUPPORTED
    geo_conf = _geo_confidence(city, state, context)
    ambiguous_present = any(e.support_state == C.SUPPORT_AMBIGUOUS for e in evidence)

    rec, reasons = recommend(RecommendationInput(
        fetch_ok=True, fetch_reason="", source_relationship=relationship,
        entity_identified=bool(name), category_resolved=bool(proposed["category"]),
        missing_required=missing, pet_policy_present=bool(pet_policy),
        pets_allowed_state=pets_state, has_material_conflict=bool(conflicts),
        multi_entity=source.multi_entity, required_evidence_mismatch=required_mismatch,
        ambiguous_present=ambiguous_present, extraction_ok=source.extraction_ok,
        text_truncated="normalized_text_truncated_50kb" in snapshot.fetch_warnings,
        service_evidence_present=service_evidence_present,
        no_service_evidence_reason=no_service_evidence_reason,
        high_risk_capability_conflict=high_risk_conflict,
        high_risk_capability_conflict_reason=high_risk_conflict_reason))

    warnings = list(snapshot.fetch_warnings)
    if not source.extraction_ok:
        warnings.append(source.extraction_error)

    return _finalize(
        url, context, snapshot, evidence, conflicts, proposed, ",".join(sorted(pet_facts)),
        _pet_facts_pairs(pet_facts), rec, reasons, relationship, rel_reason,
        source.extraction_provider, source.extraction_model, observed_at, created_at,
        category_conf=category_conf, geo_conf=geo_conf,
        multi_entity=source.multi_entity, missing=missing, warnings=tuple(warnings),
        prompt_version=source.prompt_version,
        input_tokens=source.input_tokens, output_tokens=source.output_tokens,
        provider_request_count=source.provider_request_count,
        capabilities=capabilities, category_detail=category_detail,
        pack_id=pack_id, pack_version=pack_version,
        capability_schema_version=capability_schema_version)


def _pet_facts_pairs(pet_facts: Dict[str, str]) -> Tuple[Tuple[str, str], ...]:
    return tuple(sorted(pet_facts.items()))


def _geo_confidence(city: str, state: str, context: ImportContext) -> str:
    if not (city and state):
        return C.SUPPORT_UNSUPPORTED
    exp_city = N.normalize_city(context.expected_city)
    exp_state = N.normalize_state(context.expected_state)
    if exp_city and exp_city.lower() != city.lower():
        return C.SUPPORT_AMBIGUOUS
    if exp_state and exp_state != state:
        return C.SUPPORT_AMBIGUOUS
    return C.SUPPORT_SUPPORTED


def _decode(body: bytes) -> str:
    for enc in ("utf-8", "cp1252", "latin-1"):
        try:
            return body.decode(enc)
        except UnicodeDecodeError:
            continue
    return body.decode("utf-8", "ignore")


def _finalize(
    url, context, snapshot, evidence, conflicts, proposed, ambiguous_join,
    pet_facts_pairs, rec, reasons, relationship, rel_reason, provider, model,
    observed_at, created_at, *, category_conf, geo_conf, multi_entity,
    missing=(), warnings=(), prompt_version=C.PROMPT_VERSION,
    sources=(), aggregation_version="", candidate_id=None,
    input_tokens=0, output_tokens=0, provider_request_count=0,
    capabilities=(), category_detail=None, pack_id="", pack_version="",
    capability_schema_version="",
) -> CandidateListing:
    """``sources``/``aggregation_version``/``candidate_id`` are AES-DATA-002B
    additions for the aggregate path (``aggregate.py``); every existing
    single-source call site omits them and keeps its exact prior output
    (``sources=()``, ``aggregation_version=""``, the existing single-URL id).
    ``input_tokens``/``output_tokens``/``provider_request_count`` are the
    AES-WORK-001C total real provider usage spent producing this candidate
    (0 for static/fetch-short-circuit call sites, which is every existing
    caller that does not pass them explicitly). ``capabilities``/
    ``category_detail``/``pack_id``/``pack_version``/
    ``capability_schema_version`` are AES-DATA-003B additions -- populated
    only by the veterinary path; every legacy (lodging/parks/dining) call
    site omits them and keeps the AES-DATA-003A defaults (``()``/``None``/
    ``""``), so legacy candidate bytes are unaffected."""
    ambiguous_fields = tuple(sorted({
        e.field_name for e in evidence if e.support_state == C.SUPPORT_AMBIGUOUS}))
    return CandidateListing(
        candidate_id=candidate_id if candidate_id is not None
        else make_candidate_id(url, observed_at),
        created_at=created_at, context=context, snapshot=snapshot,
        proposed_fields=tuple((k, proposed.get(k, "")) for k in C.SEED_CSV_COLUMNS),
        pet_facts=pet_facts_pairs, evidence=tuple(evidence),
        missing_required=tuple(missing), ambiguous_fields=ambiguous_fields,
        conflicts=tuple(conflicts), warnings=tuple(warnings),
        category_confidence=category_conf, geography_confidence=geo_conf,
        source_relationship=relationship, source_relationship_reason=rel_reason,
        extraction_provider=provider, extraction_model=model,
        prompt_version=prompt_version, extraction_version=C.EXTRACTION_VERSION,
        recommendation=rec, recommendation_reasons=tuple(reasons),
        review_status=C.REVIEW_PENDING,
        sources=sources, aggregation_version=aggregation_version,
        input_tokens=input_tokens, output_tokens=output_tokens,
        provider_request_count=provider_request_count,
        capabilities=capabilities, category_detail=category_detail,
        pack_id=pack_id, pack_version=pack_version,
        capability_schema_version=capability_schema_version,
    )


# --------------------------------------------------------------------------- #
# JSON persistence (deterministic; sorted keys, LF).
# --------------------------------------------------------------------------- #

def _ev_to_dict(e: ExtractedEvidence) -> dict:
    return {
        "field_name": e.field_name, "proposed_value": e.proposed_value,
        "source_wording": e.source_wording, "source_url": e.source_url,
        "snapshot_quote": e.snapshot_quote, "char_start": e.char_start,
        "char_end": e.char_end, "extraction_method": e.extraction_method,
        "support_state": e.support_state, "warnings": list(e.warnings),
    }


def _source_record_to_dict(s: SourceRecord) -> dict:
    return {
        "source_id": s.source_id, "requested_url": s.requested_url,
        "final_url": s.final_url, "role": s.role, "usable": s.usable,
        "fetch_reason": s.fetch_reason, "excluded_reason": s.excluded_reason,
        "source_relationship": s.source_relationship,
        "source_relationship_reason": s.source_relationship_reason,
        "snapshot": s.snapshot.to_dict() if s.snapshot is not None else None,
        "extraction_provider": s.extraction_provider,
        "extraction_model": s.extraction_model,
        "prompt_version": s.prompt_version,
        "warnings": list(s.warnings),
    }


# --------------------------------------------------------------------------- #
# AES-DATA-003A (additive): capability / category-detail (de)serialization.
# Narrowly scoped helpers, matching the existing _ev_to_dict/_source_record_
# to_dict style; not yet reachable from any candidate produced in this
# phase (mission Amendment 1 -- capabilities/category_detail stay empty for
# the three existing categories), but ready for AES-DATA-003B+.
# --------------------------------------------------------------------------- #

def _capability_to_dict(cap: Capability) -> dict:
    return {
        "capability_id": cap.capability_id, "state": cap.state, "value": cap.value,
        "high_risk": cap.high_risk, "evidence_index": cap.evidence_index,
        "source_url": cap.source_url,
    }


def _capability_from_dict(d: dict) -> Capability:
    # Capability.__post_init__ validates state/evidence_index itself and
    # raises DomainPackError on a malformed record -- rejected safely and
    # clearly rather than silently accepted or a bare KeyError/AttributeError.
    return Capability(
        capability_id=d["capability_id"], state=d["state"], value=d.get("value", ""),
        high_risk=d.get("high_risk", False), evidence_index=d.get("evidence_index", -1),
        source_url=d.get("source_url", ""))


def _category_detail_to_dict(cd: CategoryDetail) -> dict:
    return {
        "detail_type": cd.detail_type, "detail_schema_version": cd.detail_schema_version,
        "fields": [list(p) for p in cd.fields],
    }


def _category_detail_from_dict(d: dict) -> CategoryDetail:
    return CategoryDetail(
        detail_type=d["detail_type"], detail_schema_version=d["detail_schema_version"],
        fields=tuple(tuple(p) for p in d.get("fields", ())))


def candidate_to_dict(c: CandidateListing) -> dict:
    d = {
        "candidate_id": c.candidate_id, "created_at": c.created_at,
        "context": c.context.__dict__,
        "snapshot": c.snapshot.to_dict(),
        "proposed_fields": [list(p) for p in c.proposed_fields],
        "pet_facts": [list(p) for p in c.pet_facts],
        "evidence": [_ev_to_dict(e) for e in c.evidence],
        "missing_required": list(c.missing_required),
        "ambiguous_fields": list(c.ambiguous_fields),
        "conflicts": [{
            "field_name": cf.field_name,
            "competing_values": list(cf.competing_values),
            "evidence": [_ev_to_dict(e) for e in cf.evidence],
            "precedence_note": cf.precedence_note,
            "resolution_status": cf.resolution_status,
        } for cf in c.conflicts],
        "warnings": list(c.warnings),
        "category_confidence": c.category_confidence,
        "geography_confidence": c.geography_confidence,
        "source_relationship": c.source_relationship,
        "source_relationship_reason": c.source_relationship_reason,
        "extraction_provider": c.extraction_provider,
        "extraction_model": c.extraction_model,
        "prompt_version": c.prompt_version,
        "extraction_version": c.extraction_version,
        "recommendation": c.recommendation,
        "recommendation_reasons": list(c.recommendation_reasons),
        "review_status": c.review_status,
        "operator_edits": [list(e) for e in c.operator_edits],
        "approval_metadata": [list(p) for p in c.approval_metadata],
        # AES-WORK-001C (additive): always present (0 for static/legacy),
        # unlike sources/aggregation_version there is no prior JSON shape to
        # preserve by omission for these new fields.
        "input_tokens": c.input_tokens,
        "output_tokens": c.output_tokens,
        "provider_request_count": c.provider_request_count,
    }
    # AES-DATA-002A (additive): omit both keys entirely for an ordinary
    # single-source candidate so the AES-DATA-001 JSON shape is unchanged.
    if c.sources or c.aggregation_version:
        d["sources"] = [_source_record_to_dict(s) for s in c.sources]
        d["aggregation_version"] = c.aggregation_version
    # AES-DATA-003A (additive): omit every new key while empty/defaulted, so
    # legacy candidate bytes for the three existing categories are byte-
    # identical in this phase (mission Amendment 1). A future pack that
    # populates capabilities/category_detail is the first to see these keys.
    if c.capabilities:
        d["capabilities"] = [_capability_to_dict(cap) for cap in c.capabilities]
    if c.category_detail is not None:
        d["category_detail"] = _category_detail_to_dict(c.category_detail)
    if c.pack_id:
        d["pack_id"] = c.pack_id
    if c.pack_version:
        d["pack_version"] = c.pack_version
    if c.capability_schema_version:
        d["capability_schema_version"] = c.capability_schema_version
    return d


def _ev_from_dict(d: dict) -> ExtractedEvidence:
    return ExtractedEvidence(
        field_name=d["field_name"], proposed_value=d["proposed_value"],
        source_wording=d["source_wording"], source_url=d["source_url"],
        snapshot_quote=d["snapshot_quote"], char_start=d["char_start"],
        char_end=d["char_end"], extraction_method=d["extraction_method"],
        support_state=d["support_state"], warnings=tuple(d.get("warnings", ())))


def _snapshot_from_dict(snap: dict) -> SourceSnapshot:
    return SourceSnapshot(
        requested_url=snap["requested_url"], final_url=snap["final_url"],
        observed_at=snap["observed_at"], http_status=snap["http_status"],
        content_type=snap["content_type"],
        redirect_chain=tuple(snap["redirect_chain"]),
        page_title=snap["page_title"], canonical_url=snap["canonical_url"],
        response_header_subset=tuple(tuple(x) for x in snap["response_header_subset"]),
        raw_content_hash=snap["raw_content_hash"],
        normalized_text_hash=snap["normalized_text_hash"],
        normalized_text=snap["normalized_text"],
        extraction_version=snap["extraction_version"],
        fetch_warnings=tuple(snap["fetch_warnings"]),
        source_relationship=snap["source_relationship"])


def _source_record_from_dict(d: dict) -> SourceRecord:
    snap = d.get("snapshot")
    return SourceRecord(
        source_id=d["source_id"], requested_url=d["requested_url"],
        final_url=d["final_url"], role=d["role"], usable=d["usable"],
        fetch_reason=d.get("fetch_reason", ""),
        excluded_reason=d.get("excluded_reason", ""),
        source_relationship=d.get("source_relationship", ""),
        source_relationship_reason=d.get("source_relationship_reason", ""),
        snapshot=_snapshot_from_dict(snap) if snap else None,
        extraction_provider=d.get("extraction_provider", ""),
        extraction_model=d.get("extraction_model", ""),
        prompt_version=d.get("prompt_version", ""),
        warnings=tuple(d.get("warnings", ())))


def candidate_from_dict(d: dict) -> CandidateListing:
    snapshot = _snapshot_from_dict(d["snapshot"])
    return CandidateListing(
        candidate_id=d["candidate_id"], created_at=d["created_at"],
        context=ImportContext(**d["context"]), snapshot=snapshot,
        proposed_fields=tuple(tuple(p) for p in d["proposed_fields"]),
        pet_facts=tuple(tuple(p) for p in d["pet_facts"]),
        evidence=tuple(_ev_from_dict(e) for e in d["evidence"]),
        missing_required=tuple(d["missing_required"]),
        ambiguous_fields=tuple(d["ambiguous_fields"]),
        conflicts=tuple(Conflict(
            field_name=cf["field_name"],
            competing_values=tuple(cf["competing_values"]),
            evidence=tuple(_ev_from_dict(e) for e in cf["evidence"]),
            precedence_note=cf["precedence_note"],
            resolution_status=cf["resolution_status"]) for cf in d["conflicts"]),
        warnings=tuple(d["warnings"]),
        category_confidence=d["category_confidence"],
        geography_confidence=d["geography_confidence"],
        source_relationship=d["source_relationship"],
        source_relationship_reason=d["source_relationship_reason"],
        extraction_provider=d["extraction_provider"],
        extraction_model=d["extraction_model"],
        prompt_version=d["prompt_version"],
        extraction_version=d["extraction_version"],
        recommendation=d["recommendation"],
        recommendation_reasons=tuple(d["recommendation_reasons"]),
        review_status=d["review_status"],
        operator_edits=tuple(tuple(e) for e in d.get("operator_edits", ())),
        approval_metadata=tuple(tuple(p) for p in d.get("approval_metadata", ())),
        sources=tuple(_source_record_from_dict(s) for s in d.get("sources", ())),
        aggregation_version=d.get("aggregation_version", ""),
        input_tokens=d.get("input_tokens", 0),
        output_tokens=d.get("output_tokens", 0),
        provider_request_count=d.get("provider_request_count", 0),
        capabilities=tuple(_capability_from_dict(cd) for cd in d.get("capabilities", ())),
        category_detail=(_category_detail_from_dict(d["category_detail"])
                         if d.get("category_detail") is not None else None),
        pack_id=d.get("pack_id", ""),
        pack_version=d.get("pack_version", ""),
        capability_schema_version=d.get("capability_schema_version", ""))


def dumps_candidate(c: CandidateListing) -> str:
    return json.dumps(candidate_to_dict(c), sort_keys=True, ensure_ascii=False, indent=2)


def persist_candidate(c: CandidateListing, candidates_dir: Path) -> Path:
    candidates_dir = Path(candidates_dir)
    candidates_dir.mkdir(parents=True, exist_ok=True)
    path = candidates_dir / ("%s.json" % c.candidate_id)
    path.write_text(dumps_candidate(c) + "\n", encoding="utf-8", newline="\n")
    return path


def load_candidate(path) -> CandidateListing:
    return candidate_from_dict(json.loads(Path(path).read_text(encoding="utf-8")))


# --------------------------------------------------------------------------- #
# Operator edits (mission section 20) -- re-validated, never re-calls the LLM.
# --------------------------------------------------------------------------- #

def apply_operator_edits(
    c: CandidateListing, edits: Dict[str, str], *, decided_at: str,
) -> Tuple[CandidateListing, Tuple[Tuple[str, str, str], ...]]:
    """Apply narrow field overrides to the CSV-mapped proposed fields. Each
    edited field is re-recorded as OPERATOR_EDIT evidence; the diff is
    returned for audit. Recommendation is re-derived deterministically; the
    LLM is never called again."""
    current = dict(c.proposed_fields)
    diffs: List[Tuple[str, str, str]] = []
    new_evidence = list(c.evidence)
    for field, new_value in edits.items():
        if field not in C.SEED_CSV_COLUMNS:
            continue
        old = current.get(field, "")
        norm = _normalize_field_value(field, new_value) if field in (
            "phone", "state", "postal_code", "website_url") else N.normalize_whitespace(new_value)
        if norm == old:
            continue
        diffs.append((field, old, norm))
        current[field] = norm
        new_evidence = [e for e in new_evidence if e.field_name != field]
        new_evidence.append(ExtractedEvidence(
            field_name=field, proposed_value=norm, source_wording=new_value,
            source_url=c.snapshot.final_url, snapshot_quote="(operator edit)",
            char_start=-1, char_end=-1, extraction_method=C.METHOD_OPERATOR_EDIT,
            support_state=C.SUPPORT_SUPPORTED, warnings=()))
    missing = tuple(f for f in REQUIRED_CSV_FIELDS if not current.get(f, "").strip())
    edited = CandidateListing(
        candidate_id=c.candidate_id, created_at=c.created_at, context=c.context,
        snapshot=c.snapshot,
        proposed_fields=tuple((k, current.get(k, "")) for k in C.SEED_CSV_COLUMNS),
        pet_facts=c.pet_facts, evidence=tuple(new_evidence),
        missing_required=missing, ambiguous_fields=c.ambiguous_fields,
        conflicts=c.conflicts, warnings=c.warnings,
        category_confidence=c.category_confidence,
        geography_confidence=c.geography_confidence,
        source_relationship=c.source_relationship,
        source_relationship_reason=c.source_relationship_reason,
        extraction_provider=c.extraction_provider, extraction_model=c.extraction_model,
        prompt_version=c.prompt_version, extraction_version=c.extraction_version,
        recommendation=c.recommendation, recommendation_reasons=c.recommendation_reasons,
        review_status=c.review_status,
        operator_edits=c.operator_edits + tuple(diffs),
        approval_metadata=c.approval_metadata + (("edited_at", decided_at),),
        sources=c.sources, aggregation_version=c.aggregation_version,
        input_tokens=c.input_tokens, output_tokens=c.output_tokens,
        provider_request_count=c.provider_request_count)
    return (edited, tuple(diffs))


def has_unsupported_published_claim(c: CandidateListing) -> bool:
    """True if any published (non-edit) CSV/pet value lacks SUPPORTED/AMBIGUOUS
    evidence -- blocks approval (mission section 20)."""
    published_pet = {k for k, v in c.pet_facts if v}
    supported = {e.field_name for e in c.evidence
                 if e.support_state in (C.SUPPORT_SUPPORTED, C.SUPPORT_AMBIGUOUS)}
    for field in published_pet:
        if field not in supported:
            return True
    return False
