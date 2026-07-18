"""AES-DATA-002B importer -- deterministic identity gate and cross-source
aggregate merger.

Builds directly on the AES-DATA-002A seam: one ``import_source`` call per
unique supplied URL, then a deterministic identity gate (same registrable
domain, reconcilable entity name, agreeing geography) decides which sources
may contribute fields, and a field-by-field merge over the raw
``PageEvidence`` pools -- never a second LLM call, never concatenated source
text, never a fuzzy match -- produces one evidence-backed ``CandidateListing``.

A source that fails the gate is never silently dropped: its ``SourceRecord``
is always preserved (with an ``excluded_reason``), just excluded from field
merging. The output is an ordinary ``CandidateListing`` (``sources`` populated,
``aggregation_version`` set) so every existing serialization, approval, and
promotion code path works unchanged.
"""

from __future__ import annotations

import hashlib
from dataclasses import dataclass, replace
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlsplit

from scripts.pettripfinder.importer import constants as C
from scripts.pettripfinder.importer import normalize as N
from scripts.pettripfinder.importer.candidate import (
    PageEvidence,
    SourceImportResult,
    _BOOL_PET_FIELDS,
    _IDENTITY_FIELDS,
    _NAME_METHOD_RANK,
    _derive_dual_facts,
    _expected_city_support,
    _finalize,
    _geo_confidence,
    _hint_supported,
    _pet_facts_pairs,
    _reconciles_with_resolved,
    _registrable,
    _resolve_name,
    _resolve_phone,
    _shallow_snapshot,
    _slug,
    _source_type_for,
    import_source,
)
from scripts.pettripfinder.importer.category_templates import (
    REQUIRED_CSV_FIELDS,
    allowed_fields,
)
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
from scripts.pettripfinder.importer.models import (
    CandidateListing,
    Conflict,
    ExtractedEvidence,
    ImportContext,
    SourceRecord,
)
from scripts.pettripfinder.importer.policy_compose import compose_pet_policy
from scripts.pettripfinder.importer.recommend import RecommendationInput, recommend

# Numeric pet facts -- a material disagreement (not descriptive prose) that
# must never silently pick one source's number over another's.
_NUMERIC_PET_FIELDS = frozenset({"pet_fee", "weight_limit", "pet_count_limit"})

# Conflict.precedence_note values that already have their OWN dedicated
# aggregate recommendation reason (identity_conflict / geography_conflict /
# policy_conflict, AES-DATA-002D). Excluded from the generic material-
# conflict count so the same underlying issue is never reported under both
# its specific slug and the generic ``conflicting_evidence`` slug.
_AGGREGATE_SPECIFIC_PRECEDENCE_NOTES = frozenset({
    "entity_name_canonicalization", "aggregate_geography_conflict",
    "aggregate_policy_conflict",
})


# --------------------------------------------------------------------------- #
# Candidate id + URL deduplication (Task 1/2/12).
# --------------------------------------------------------------------------- #

def make_aggregate_candidate_id(urls: List[str], observed_at: str) -> str:
    """Deterministic id from the ordered, deduplicated, normalized requested-
    URL set plus the primary host and the observation date: the same source
    set requested on the same day overwrites the same candidate artifact."""
    host = urlsplit(urls[0]).hostname or "source"
    key = "|".join(N.normalize_url(u) or u for u in urls) + "|" + observed_at
    short = hashlib.sha256(key.encode("utf-8")).hexdigest()[:10]
    return "%s-%s" % (_slug(host)[:40] or "source", short)


def _dedupe_urls(urls: List[str]) -> Tuple[List[str], List[str]]:
    """Pre-fetch, deterministic dedup: an exact or normalized-duplicate
    requested URL collapses to its first occurrence, before any fetch.
    First occurrence wins, so operator order (and PRIMARY designation) is
    preserved. Returns ``(unique_urls, warnings)`` -- a URL with no
    ``SourceRecord`` (it was never fetched) is only traceable via the
    returned warning, per the "narrowest existing equivalent" doctrine."""
    unique: List[str] = []
    warnings: List[str] = []
    seen = set()
    for u in urls:
        key = N.normalize_url(u) or u.strip()
        if key in seen:
            warnings.append("%s:%s" % (C.REASON_DUPLICATE_SOURCE_URL, u))
            continue
        seen.add(key)
        unique.append(u)
    return (unique, warnings)


def _source_order_index(source_id: str) -> int:
    return int(source_id[1:])


def _build_source_records(
    unique_urls: List[str], results: List[SourceImportResult],
) -> List[SourceRecord]:
    """One ``SourceRecord`` per unique requested URL, in operator order
    (S1 = PRIMARY, S2.. = SUPPLEMENTAL). A redirect duplicate (two distinct
    requested URLs landing on the same final URL) IS fetched -- it gets its
    own record -- but is marked excluded so it never double-contributes."""
    records: List[SourceRecord] = []
    seen_final: Dict[str, str] = {}
    for i, (u, res) in enumerate(zip(unique_urls, results)):
        sid = "S%d" % (i + 1)
        role = C.SOURCE_ROLE_PRIMARY if i == 0 else C.SOURCE_ROLE_SUPPLEMENTAL
        excluded_reason = ""
        if res.usable and res.final_url:
            norm_final = N.normalize_url(res.final_url) or res.final_url
            if norm_final in seen_final:
                excluded_reason = C.REASON_DUPLICATE_SOURCE_URL
            else:
                seen_final[norm_final] = sid
        records.append(SourceRecord(
            source_id=sid, requested_url=u, final_url=res.final_url or u,
            role=role, usable=res.usable, fetch_reason=res.fetch_reason,
            excluded_reason=excluded_reason,
            source_relationship=res.source_relationship,
            source_relationship_reason=res.source_relationship_reason,
            snapshot=res.snapshot, extraction_provider=res.extraction_provider,
            extraction_model=res.extraction_model, prompt_version=res.prompt_version,
            warnings=res.warnings))
    return records


# --------------------------------------------------------------------------- #
# Domain/relationship gate (Task 4).
# --------------------------------------------------------------------------- #

def _domain_and_relationship_gate(primary_final_url: str, record: SourceRecord) -> str:
    """A supplemental never merges from a different registrable domain, and
    never from a THIRD_PARTY host. Returns an ``excluded_reason`` ("" =
    passes). The known third-party host markers are re-checked directly
    (not only via ``record.source_relationship``) because the operator's
    ``source_relationship_hint`` is a single global value applied to every
    supplied URL (it exists to classify PRIMARY) -- it must never be able to
    bless a discovery/review host like Yelp as merge-eligible just because
    it was supplied alongside a hinted primary."""
    supp_host = (urlsplit(record.final_url).hostname or "").lower()
    if any(marker in supp_host for marker in C.THIRD_PARTY_HOST_MARKERS):
        return C.REASON_THIRD_PARTY_SOURCE
    if record.source_relationship == C.REL_THIRD_PARTY:
        return C.REASON_THIRD_PARTY_SOURCE
    primary_host = urlsplit(primary_final_url).hostname or ""
    if _registrable(primary_host) != _registrable(supp_host):
        return C.REASON_DIFFERENT_REGISTRABLE_DOMAIN
    return ""


# --------------------------------------------------------------------------- #
# Entity identity gate (Task 5): name reconciliation, then geography
# agreement. Reuses the exact single-source machinery -- no fuzzy matching.
# --------------------------------------------------------------------------- #

def _page_resolved_name(page: PageEvidence) -> str:
    """The same "best by method rank, then brand-stripped" pick
    ``_resolve_name`` uses internally, applied to one page's own pool."""
    entries = [(N.normalize_name(v), m) for v, _q, _cs, _ce, m, _s, _u in page.name_candidates
               if N.normalize_name(v)]
    if not entries:
        return ""
    best_value, _best_method = min(entries, key=lambda e: _NAME_METHOD_RANK.get(e[1], 3))
    return N.clean_entity_name(best_value)


def _identity_gate(
    primary_page: PageEvidence, primary_resolved_name: str, primary_text: str,
    supplemental_page: PageEvidence, supplemental_text: str,
    context: ImportContext, expected_city: str, expected_city_supported: bool,
    expected_state: str = "",
) -> str:
    """Returns an ``excluded_reason`` ("" = passes). Name: the supplemental's
    resolved name must reconcile with PRIMARY's (context-bound expected-city
    (+state, AES-DATA-002D) suffix and terminal-legal-suffix rules included,
    via ``_reconciles_with_resolved``), OR a supported operator
    ``candidate_name`` hint must reconcile with BOTH pages. Geography: when
    both sides carry a supported city/state/street address, they must agree
    (address compared via existing deterministic normalization, never
    fuzzy)."""
    supp_resolved = _page_resolved_name(supplemental_page)
    if supp_resolved:
        direct = bool(primary_resolved_name) and _reconciles_with_resolved(
            primary_resolved_name, supp_resolved, expected_city,
            expected_city_supported, expected_state)
        if not direct:
            hint = N.normalize_name(context.candidate_name)
            hint_ok = False
            if hint:
                p_entries = [{"value": N.normalize_name(v)}
                            for v, *_ in primary_page.name_candidates]
                s_entries = [{"value": N.normalize_name(v)}
                            for v, *_ in supplemental_page.name_candidates]
                hint_ok = (_hint_supported(hint, p_entries, primary_text)
                          and _hint_supported(hint, s_entries, supplemental_text))
            if not hint_ok:
                return C.REASON_IDENTITY_CONFLICT

    p_city = primary_page.accepted.get("city", "")
    s_city = supplemental_page.accepted.get("city", "")
    if p_city and s_city and p_city.lower() != s_city.lower():
        return C.REASON_GEOGRAPHY_CONFLICT
    # PRIMARY may state no city at all (a policy-only FAQ page, the
    # motivating case) -- the pairwise check above then has nothing to
    # compare. The operator's own expected_city is still a supported,
    # non-fuzzy signal: a supplemental whose OWN structured/accepted city
    # contradicts it is never silently merged just because PRIMARY was
    # silent on geography.
    if expected_city and s_city and s_city.lower() != expected_city.lower():
        return C.REASON_GEOGRAPHY_CONFLICT
    p_state = primary_page.accepted.get("state", "")
    s_state = supplemental_page.accepted.get("state", "")
    if p_state and s_state and p_state != s_state:
        return C.REASON_GEOGRAPHY_CONFLICT
    # AES-DATA-002D: the same PRIMARY-silent gap as the city fallback above
    # -- a supplemental's own state must not contradict the operator's
    # expected_state just because PRIMARY never stated one.
    expected_state = N.normalize_state(expected_state) if expected_state else ""
    if expected_state and s_state and s_state != expected_state:
        return C.REASON_GEOGRAPHY_CONFLICT
    p_addr = primary_page.accepted.get("address", "")
    s_addr = supplemental_page.accepted.get("address", "")
    if p_addr and s_addr:
        p_norm = N.normalize_address(p_addr, p_city, p_state).lower()
        s_norm = N.normalize_address(s_addr, s_city, s_state).lower()
        if p_norm and s_norm and p_norm != s_norm:
            return C.REASON_GEOGRAPHY_CONFLICT

    return ""


# --------------------------------------------------------------------------- #
# Per-source preparation (Task 6): per-page dual-fact derivation (span-bound
# to that page's own snapshot) runs before pooling, exactly as the
# single-source ``_resolve_page_fields`` runs it -- just scoped per source.
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class _IncludedSource:
    source_id: str
    source_url: str
    relationship: str
    evidence: Tuple[ExtractedEvidence, ...]
    conflicts: Tuple[Conflict, ...]
    accepted: Dict[str, str]
    name_candidates: Tuple[Tuple[str, str, int, int, str, str, str], ...]
    phone_candidates: Tuple[Tuple[str, str, int, int, str, str, str], ...]
    required_evidence_mismatch: bool
    # multi_entity (Task 5C): may still contribute pet-policy facts, but
    # never identity (name/phone) or geography (address/city/state/postal).
    restrict_identity: bool


def _prepare_included_source(
    record: SourceRecord, result: SourceImportResult, category: str,
) -> _IncludedSource:
    page = result.page_evidence
    evidence = list(page.evidence)
    accepted = dict(page.accepted)
    _derive_dual_facts(result.snapshot, evidence, accepted, category, record.final_url)
    return _IncludedSource(
        source_id=record.source_id, source_url=record.final_url,
        relationship=record.source_relationship,
        evidence=tuple(evidence), conflicts=page.conflicts, accepted=accepted,
        name_candidates=page.name_candidates, phone_candidates=page.phone_candidates,
        required_evidence_mismatch=page.required_evidence_mismatch,
        restrict_identity=result.multi_entity)


# --------------------------------------------------------------------------- #
# Geography merge (Task 9).
# --------------------------------------------------------------------------- #

def _method_for_field(src: _IncludedSource, field: str) -> str:
    ev = next((e for e in src.evidence if e.field_name == field
               and e.support_state != C.SUPPORT_UNSUPPORTED), None)
    return ev.extraction_method if ev else C.METHOD_LLM_TEXT


@dataclass(frozen=True)
class _FieldMergeResult:
    value: str
    winning_source_url: str
    conflict: bool


def _merge_simple_field(field: str, included: List[_IncludedSource]) -> _FieldMergeResult:
    """city/state/postal_code: structured evidence outranks LLM text; source
    order breaks ties among equivalent (already-normalized) evidence; a
    genuine disagreement is a conflict, never silently resolved by rank."""
    candidates = []
    for src in included:
        if src.restrict_identity:
            continue
        val = src.accepted.get(field, "")
        if not val:
            continue
        rank = 0 if _method_for_field(src, field) != C.METHOD_LLM_TEXT else 1
        candidates.append((val, rank, _source_order_index(src.source_id), src.source_url))
    if not candidates:
        return _FieldMergeResult("", "", False)
    key_fn = (lambda c: c[0].lower()) if field == "city" else (lambda c: c[0])
    if len({key_fn(c) for c in candidates}) > 1:
        return _FieldMergeResult("", "", True)
    best = min(candidates, key=lambda c: (c[1], c[2]))
    return _FieldMergeResult(best[0], best[3], False)


def _merge_address(included: List[_IncludedSource]) -> _FieldMergeResult:
    """Compare each candidate's OWN normalized form (its own city/state) for
    conflict detection -- so "424 W Town St, Columbus, OH" and "424 W Town
    St" are recognized as the same address -- but publish the RAW winning
    value; the final trailing-locality strip happens once, after the
    aggregate city/state are resolved, exactly like the single-source path."""
    candidates = []
    for src in included:
        if src.restrict_identity:
            continue
        raw = src.accepted.get("address", "")
        if not raw:
            continue
        own_city = src.accepted.get("city", "")
        own_state = src.accepted.get("state", "")
        norm = N.normalize_address(raw, own_city, own_state).lower()
        rank = 0 if _method_for_field(src, "address") != C.METHOD_LLM_TEXT else 1
        candidates.append((raw, norm, rank, _source_order_index(src.source_id), src.source_url))
    if not candidates:
        return _FieldMergeResult("", "", False)
    if len({c[1] for c in candidates if c[1]}) > 1:
        return _FieldMergeResult("", "", True)
    best = min(candidates, key=lambda c: (c[2], c[3]))
    return _FieldMergeResult(best[0], best[4], False)


def _geo_conflict_object(field: str, included: List[_IncludedSource]) -> Optional[Conflict]:
    evs: List[ExtractedEvidence] = []
    values: List[str] = []
    for src in included:
        if src.restrict_identity:
            continue
        for e in src.evidence:
            if e.field_name == field and e.support_state != C.SUPPORT_UNSUPPORTED:
                evs.append(e)
                if e.proposed_value not in values:
                    values.append(e.proposed_value)
    if len(values) <= 1:
        return None
    return Conflict(field_name=field, competing_values=tuple(values), evidence=tuple(evs),
                    precedence_note="aggregate_geography_conflict", resolution_status="UNRESOLVED")


# --------------------------------------------------------------------------- #
# Pet-fact merge (Task 10).
# --------------------------------------------------------------------------- #

def _merge_pet_facts(
    category: str, pooled_evidence: List[ExtractedEvidence],
) -> Tuple[Dict[str, str], List[Conflict]]:
    """Boolean and numeric pet facts: a genuine disagreement across sources
    is a ``policy_conflict`` -- the fact is not published, all evidence is
    preserved. Descriptive text: never classified as contradictory; the
    published value follows stable (pooled, source-ordered) precedence while
    every value's evidence stays visible."""
    fields = allowed_fields(category) - set(_IDENTITY_FIELDS)
    pet_facts: Dict[str, str] = {}
    conflicts: List[Conflict] = []
    for field in sorted(fields):
        evs = [e for e in pooled_evidence if e.field_name == field
               and e.support_state != C.SUPPORT_UNSUPPORTED]
        if not evs:
            continue
        distinct = {e.proposed_value for e in evs}
        is_material = field in _BOOL_PET_FIELDS or field in _NUMERIC_PET_FIELDS
        if is_material and len(distinct) > 1:
            conflicts.append(Conflict(
                field_name=field, competing_values=tuple(sorted(distinct)),
                evidence=tuple(evs), precedence_note="aggregate_policy_conflict",
                resolution_status="UNRESOLVED"))
            continue
        pet_facts[field] = evs[0].proposed_value   # stable pooled (source) order
    return (pet_facts, conflicts)


# --------------------------------------------------------------------------- #
# Orchestration (Task 1).
# --------------------------------------------------------------------------- #

def run_multi_import(
    urls: List[str],
    context: ImportContext,
    *,
    fetcher,
    extractor,
    cas,
    observed_at: str,
    created_at: str,
) -> CandidateListing:
    """Fetch and merge up to ``C.MAX_AGGREGATE_SOURCES`` official pages for
    ONE intended entity into a single evidence-backed ``CandidateListing``.
    One ``import_source`` call per unique URL (never a second LLM call, never
    concatenated source text); a deterministic identity gate decides which
    sources may contribute fields; every supplied source stays visible via
    its ``SourceRecord``, gated out or not. Raises ``ValueError`` before any
    fetch when the URL count is invalid."""
    urls = list(urls)
    if not urls:
        raise ValueError("run_multi_import: at least one source URL is required")
    if len(urls) > C.MAX_AGGREGATE_SOURCES:
        raise ValueError(
            "run_multi_import: at most %d source URLs are supported (got %d)"
            % (C.MAX_AGGREGATE_SOURCES, len(urls)))

    category = context.category
    unique_urls, dedupe_warnings = _dedupe_urls(urls)

    results = [
        import_source(u, context, fetcher=fetcher, extractor=extractor, cas=cas,
                      observed_at=observed_at)
        for u in unique_urls
    ]
    records = _build_source_records(unique_urls, results)
    aggregate_id = make_aggregate_candidate_id(unique_urls, observed_at)

    # AES-WORK-001C: total REAL provider usage across every attempted
    # source (every entry in ``results``, not just the gate-included ones --
    # an excluded/conflicting source still made a real, billed call).
    total_input_tokens = sum(r.input_tokens for r in results)
    total_output_tokens = sum(r.output_tokens for r in results)
    total_provider_requests = sum(r.provider_request_count for r in results)

    primary_record = records[0]
    primary_result = results[0]

    # --- PRIMARY failure short-circuit (existing single-source doctrine;
    # "PRIMARY rejection-class failures retain existing doctrine") ---------
    if not primary_result.usable:
        if primary_result.snapshot is None:
            snap = _shallow_snapshot(primary_result.fetch_result, observed_at)
            rel_reason = "fetch_failed:" + primary_result.fetch_reason
        else:
            snap = primary_result.snapshot
            rel_reason = "javascript_rendered"
        rec, reasons = recommend(RecommendationInput(
            fetch_ok=False, fetch_reason=primary_result.fetch_reason,
            source_relationship=C.REL_UNKNOWN, entity_identified=False,
            category_resolved=bool(N.normalize_category_id(category)),
            missing_required=(), pet_policy_present=False, pets_allowed_state="",
            has_material_conflict=False, multi_entity=False,
            required_evidence_mismatch=False, ambiguous_present=False,
            extraction_ok=True, text_truncated=False))
        return _finalize(
            unique_urls[0], context, snap, [], [], {}, "", (), rec, reasons,
            C.REL_UNKNOWN, rel_reason, "", "", observed_at, created_at,
            category_conf=C.SUPPORT_UNSUPPORTED, geo_conf=C.SUPPORT_UNSUPPORTED,
            multi_entity=False, warnings=tuple(dedupe_warnings),
            sources=tuple(records), aggregation_version=C.AGGREGATION_VERSION,
            candidate_id=aggregate_id,
            input_tokens=total_input_tokens, output_tokens=total_output_tokens,
            provider_request_count=total_provider_requests)

    primary_page = primary_result.page_evidence
    primary_text = primary_result.snapshot.normalized_text
    exp_city, exp_state, city_supported = _expected_city_support(
        primary_page.accepted, primary_text, context)
    primary_resolved_name = _page_resolved_name(primary_page)

    # --- gates: domain/relationship, then identity/geography (Task 4/5) ----
    gated_records: List[SourceRecord] = [primary_record]
    included_results: List[Tuple[SourceRecord, SourceImportResult]] = [
        (primary_record, primary_result)]
    for record, result in zip(records[1:], results[1:]):
        if record.excluded_reason:               # already a redirect duplicate
            gated_records.append(record)
            continue
        if not result.usable:
            gated_records.append(record)          # fetch/JS-only failure: visible, unmerged
            continue
        reason = _domain_and_relationship_gate(primary_result.final_url, record)
        if not reason and not result.multi_entity:
            reason = _identity_gate(
                primary_page, primary_resolved_name, primary_text,
                result.page_evidence, result.snapshot.normalized_text,
                context, exp_city, city_supported, exp_state)
        if reason:
            record = replace(record, excluded_reason=reason)
        gated_records.append(record)
        if not reason:
            included_results.append((record, result))

    # --- pool raw PageEvidence from every gate-passed, usable source -------
    included = [_prepare_included_source(record, result, category)
                for record, result in included_results]

    pooled_evidence: List[ExtractedEvidence] = []
    pooled_conflicts: List[Conflict] = []
    for src in included:
        pooled_evidence.extend(src.evidence)
        pooled_conflicts.extend(src.conflicts)

    # --- name/phone: resolve ONCE over the pooled, source-tagged candidates
    # (Task 7/8) -- the exact single-source resolvers, unmodified in logic. -
    pooled_name_candidates = [
        cand for src in included if not src.restrict_identity for cand in src.name_candidates]
    pooled_phone_candidates = [
        cand for src in included if not src.restrict_identity for cand in src.phone_candidates]

    resolved_name, name_evidence, name_conflicts = _resolve_name(
        pooled_name_candidates, context, primary_text,
        expected_city=exp_city, expected_state=exp_state,
        expected_city_supported=city_supported)
    pooled_evidence.extend(name_evidence)
    pooled_conflicts.extend(name_conflicts)

    resolved_phone, phone_evidence, phone_conflicts = _resolve_phone(pooled_phone_candidates)
    pooled_evidence.extend(phone_evidence)
    pooled_conflicts.extend(phone_conflicts)

    # --- geography merge (Task 9) -------------------------------------------
    geo_conflict_flag = False
    field_results = {
        "city": _merge_simple_field("city", included),
        "state": _merge_simple_field("state", included),
        "postal_code": _merge_simple_field("postal_code", included),
        "address": _merge_address(included),
    }
    for field, result_ in field_results.items():
        if result_.conflict:
            geo_conflict_flag = True
            cf = _geo_conflict_object(field, included)
            if cf is not None:
                pooled_conflicts.append(cf)

    city = field_results["city"].value or N.normalize_city(context.expected_city)
    state = field_results["state"].value or N.normalize_state(context.expected_state)
    address_raw = field_results["address"].value

    # Postal derivation (mirrors the single-source defect-B rule): only from
    # the WINNING address's own evidence span -- never a mismatched source.
    postal = field_results["postal_code"].value
    if not postal:
        derived_zip = N.extract_postal_from_address(address_raw)
        winning_url = field_results["address"].winning_source_url
        if derived_zip and winning_url:
            postal = derived_zip
            addr_ev = next(
                (e for e in pooled_evidence if e.field_name == "address"
                 and e.support_state != C.SUPPORT_UNSUPPORTED
                 and e.source_url == winning_url), None)
            if addr_ev is not None:
                pooled_evidence.append(ExtractedEvidence(
                    field_name="postal_code", proposed_value=postal,
                    source_wording=addr_ev.source_wording, source_url=addr_ev.source_url,
                    snapshot_quote=addr_ev.snapshot_quote, char_start=addr_ev.char_start,
                    char_end=addr_ev.char_end, extraction_method=addr_ev.extraction_method,
                    support_state=C.SUPPORT_SUPPORTED, warnings=("derived_from:address",)))

    address = N.normalize_address(address_raw, city, state)
    primary_final_url = primary_result.final_url
    website_url = next(
        (src.accepted.get("website_url", "") for src in included
         if not src.restrict_identity and src.accepted.get("website_url")), "")
    if not website_url:
        website_url = primary_final_url
    name = resolved_name or N.normalize_name(context.candidate_name)

    # --- pet-fact merge (Task 10) -------------------------------------------
    pet_facts, pet_conflicts = _merge_pet_facts(category, pooled_evidence)
    pooled_conflicts.extend(pet_conflicts)
    pet_policy = compose_pet_policy(pet_facts, category)

    # --- AES-DATA-003B: veterinary capability projection (Task 12) ---------
    # Projected from the FINAL pooled evidence/conflicts (nothing is appended
    # to ``pooled_evidence``/``pooled_conflicts`` after this point), so
    # evidence indices match the ``CandidateListing.evidence`` tuple
    # ``_finalize`` builds below. Each evidence entry already carries its OWN
    # ``source_url`` (pooled from every gate-included source), so a
    # capability projected from a supplemental's evidence is attributed to
    # that supplemental automatically -- no separate merge algorithm needed.
    # A conflicting high-risk capability across sources is detected the same
    # way single-source conflicts are: via ``_merge_pet_facts`` (materiality
    # driven by the shared ``_BOOL_PET_FIELDS`` set) surfacing an
    # ``aggregate_policy_conflict`` Conflict that ``project_capabilities``
    # then turns into a CONFLICTED capability.
    capabilities: Tuple[Capability, ...] = ()
    category_detail: Optional[CategoryDetail] = None
    pack_id, pack_version, capability_schema_version = "", "", ""
    vet_service_evidence_present = None
    no_service_evidence_reason = C.REASON_NO_PET_EVIDENCE
    high_risk_conflict = False
    if category == C.CATEGORY_VETERINARY:
        pack = default_registry.for_category(category)
        capabilities = _vet_project_capabilities(
            pet_facts, pooled_evidence, pooled_conflicts, primary_final_url)
        pack_id, pack_version = pack.pack_id, pack.pack_version
        capability_schema_version = CAPABILITY_SCHEMA_VERSION
        vet_service_evidence_present = _vet_service_evidence_present(capabilities)
        no_service_evidence_reason = C.REASON_NO_VETERINARY_SERVICE_EVIDENCE
        high_risk_conflict = _vet_high_risk_conflict(capabilities)
        hours = pet_facts.get("hours", "")
        if hours:
            category_detail = CategoryDetail(
                detail_type="veterinary", detail_schema_version=pack.detail_schema_version,
                fields=(("hours", hours),))

    # --- relationship: the weakest CONTRIBUTING relationship (Task 11) -----
    # An UNKNOWN-relationship contributor never hides behind a stronger
    # PRIMARY; recommend() only distinguishes THIRD_PARTY/UNKNOWN from every
    # "official" relationship, so that is the only comparison that matters.
    unknown_src = next((src for src in included if src.relationship == C.REL_UNKNOWN), None)
    if unknown_src is not None:
        relationship = C.REL_UNKNOWN
        rel_reason = "aggregate_weakest_relationship:%s" % unknown_src.source_id
    else:
        relationship = primary_record.source_relationship
        rel_reason = primary_record.source_relationship_reason
    source_type = _source_type_for(relationship, context)

    proposed = {
        "name": name, "category": N.normalize_category_id(category),
        "address": address, "city": city, "state": state,
        "postal_code": postal, "phone": resolved_phone, "website_url": website_url,
        "source_url": primary_final_url, "source_type": source_type,
        "observed_at": observed_at, "rating": "", "pet_policy": pet_policy,
        "canonical": "",
    }

    missing = tuple(f for f in REQUIRED_CSV_FIELDS if not proposed.get(f, "").strip())
    pets_state = pet_facts.get("pets_allowed", "")
    category_conf = C.SUPPORT_SUPPORTED if proposed["category"] else C.SUPPORT_UNSUPPORTED
    geo_conf = _geo_confidence(city, state, context)
    ambiguous_present = any(e.support_state == C.SUPPORT_AMBIGUOUS for e in pooled_evidence)
    agg_multi_entity = any(result_.multi_entity for _rec, result_ in included_results)

    # A pets_allowed contradiction already surfaces as a policy_conflict
    # (below); the required-evidence-mismatch REJECT is reserved for the
    # genuine "no source has real evidence at all" case.
    pets_allowed_conflicted = any(cf.field_name == "pets_allowed" for cf in pet_conflicts)
    agg_required_mismatch = (
        any(src.required_evidence_mismatch for src in included)
        and "pets_allowed" not in pet_facts and not pets_allowed_conflicted)

    sources_excluded = any(
        r.role == C.SOURCE_ROLE_SUPPLEMENTAL
        and (not r.usable or (r.excluded_reason
                              and r.excluded_reason != C.REASON_DUPLICATE_SOURCE_URL))
        for r in gated_records)
    aggregate_identity_conflict = bool(name_conflicts) or any(
        r.excluded_reason == C.REASON_IDENTITY_CONFLICT for r in gated_records)
    aggregate_geography_conflict = geo_conflict_flag or any(
        r.excluded_reason == C.REASON_GEOGRAPHY_CONFLICT for r in gated_records)
    aggregate_policy_conflict = bool(pet_conflicts)

    # AES-DATA-002D: a name/geography/policy conflict already surfaces
    # through its OWN dedicated aggregate reason above -- counting it again
    # toward the generic ``has_material_conflict`` would emit both
    # ``conflicting_evidence`` and (e.g.) ``identity_conflict`` for the SAME
    # underlying issue (the live taproom-title regression's exact reasons:
    # ["conflicting_evidence", "identity_conflict"]). An intra-page
    # (structured-vs-LLM) or phone conflict has no dedicated aggregate
    # reason, so it genuinely is a distinct class and still counts here.
    has_material_conflict = any(
        cf.precedence_note not in _AGGREGATE_SPECIFIC_PRECEDENCE_NOTES
        for cf in pooled_conflicts)

    rec, reasons = recommend(RecommendationInput(
        fetch_ok=True, fetch_reason="", source_relationship=relationship,
        entity_identified=bool(name), category_resolved=bool(proposed["category"]),
        missing_required=missing, pet_policy_present=bool(pet_policy),
        pets_allowed_state=pets_state, has_material_conflict=has_material_conflict,
        multi_entity=agg_multi_entity, required_evidence_mismatch=agg_required_mismatch,
        ambiguous_present=ambiguous_present,
        extraction_ok=all(r.extraction_ok for _rec, r in included_results),
        text_truncated=any(
            "normalized_text_truncated_50kb" in r.warnings for _rec, r in included_results),
        sources_excluded=sources_excluded,
        aggregate_identity_conflict=aggregate_identity_conflict,
        aggregate_geography_conflict=aggregate_geography_conflict,
        aggregate_policy_conflict=aggregate_policy_conflict,
        service_evidence_present=vet_service_evidence_present,
        no_service_evidence_reason=no_service_evidence_reason,
        high_risk_capability_conflict=high_risk_conflict))

    warnings = list(primary_result.snapshot.fetch_warnings) + list(dedupe_warnings)
    for _rec, r in included_results:
        if not r.extraction_ok:
            warnings.append(r.extraction_error)

    return _finalize(
        unique_urls[0], context, primary_result.snapshot, pooled_evidence, pooled_conflicts,
        proposed, ",".join(sorted(pet_facts)), _pet_facts_pairs(pet_facts),
        rec, reasons, relationship, rel_reason,
        primary_result.extraction_provider, primary_result.extraction_model,
        observed_at, created_at, category_conf=category_conf, geo_conf=geo_conf,
        multi_entity=agg_multi_entity, missing=missing, warnings=tuple(warnings),
        prompt_version=primary_result.prompt_version, sources=tuple(gated_records),
        aggregation_version=C.AGGREGATION_VERSION, candidate_id=aggregate_id,
        input_tokens=total_input_tokens, output_tokens=total_output_tokens,
        provider_request_count=total_provider_requests,
        capabilities=capabilities, category_detail=category_detail,
        pack_id=pack_id, pack_version=pack_version,
        capability_schema_version=capability_schema_version)
