"""ATLAS-WORKERS-001 -- deterministic evidence validator (Stage 3).

Ordinary, pure code that re-derives every fact from the supplied source text
*after* the model responds. The model's claims are untrusted input; a fact only
survives if this validator can prove it from the assignment's own documents.
The validator rejects unsupported AI output even when the model claims
confidence, and it never treats source content as instructions -- it only runs
string/number checks over it (Stage 3 rule 15).

Rule coverage (Stage 3):
  1  every SUPPORTED fact cites an exact evidence quote
  2  every quote appears verbatim in a supplied source document
  3  the cited URL belongs to the assignment (and is a usable official doc)
  4  search snippets / OTHER sources are never publication evidence
  5  property-specific official sources outrank general brand sources
  6  a brand policy cannot override a contradictory property-specific policy
  7  fee and deposit remain separate (distinct fields, distinct quotes)
  8  per-night / per-stay / per-room / per-room-per-day remain distinct
  9  maximum pets is never inferred from plural wording (number must be quoted)
  10 weight limit is not converted (the stated number must be quoted verbatim)
  11 a species claim needs the species word in its quote, whether the species
     is accepted or NOT -- a generic "pets welcome"/"no pets" statement implies
     neither dogs nor cats in either direction
  12 missing data becomes NOT_STATED, never false or zero
  13 contradictory same-rank official sources force CONTRADICTORY -- now detected
     DETERMINISTICALLY by re-reading the sources (services.research_workers.
     reconciliation), so an empty or one-sided model response can no longer hide
     a genuine cross-source conflict
  14 missing/blocked sources produce no supported facts
  15 source content is untrusted data, not instructions
"""

from __future__ import annotations

import re
import time
from typing import Dict, List, Optional, Tuple

from services.research_workers import vocabulary as V
from services.research_workers.contracts import (
    Assignment, ProposedField, SourceDocument, WorkerResult,
)
from services.research_workers.proposal import ModelProposal, RawFactClaim
from services.research_workers.reconciliation import detect_field_contradictions


# fee_basis -> (required phrases, forbidden phrases). Ordered longest-first so
# "per room per day" is never mistaken for "per room".
_FEE_BASIS_PHRASES = {
    V.FEE_BASIS_PER_ROOM_PER_DAY: (("per room per day", "per room, per day", "per room/day", "room per day"), ()),
    V.FEE_BASIS_PER_NIGHT: (("per night", "nightly", "/night", "a night"), ()),
    V.FEE_BASIS_PER_STAY: (("per stay", "each stay", "/stay", "a stay"), ()),
    V.FEE_BASIS_PER_ROOM: (("per room",), ("per room per day", "per room, per day", "room per day")),
}


def _usable_official_docs(assignment: Assignment) -> List[SourceDocument]:
    """OK + official + non-empty documents, best source first (rule 4/5/14)."""
    docs = [d for d in assignment.source_documents if d.is_usable_official]
    return sorted(docs, key=lambda d: (-V.SOURCE_TYPE_RANK.get(d.source_type, 0), d.source_url))


def _quote_verbatim(quote: str, doc: SourceDocument) -> bool:
    q = (quote or "").strip()
    if not q or len(q) > V.EVIDENCE_QUOTE_CAP:
        return False
    return q in doc.content_text


def _digits(value: str) -> str:
    m = re.search(r"\d[\d,\.]*", value or "")
    return m.group(0).replace(",", "") if m else ""


def _numeric_supported(value: str, quote: str) -> bool:
    """The number in ``value`` must appear in ``quote`` (rules 9/10): never
    inferred from plural wording, never unit-converted."""
    num = _digits(value)
    if not num:
        return False
    ql = quote.replace(",", "")
    return num in ql


def _species_supported(field_name: str, quote: str) -> bool:
    ql = quote.lower()
    if field_name == V.FIELD_DOGS_ACCEPTED:
        return "dog" in ql
    if field_name == V.FIELD_CATS_ACCEPTED:
        return "cat" in ql
    return True


def _fee_basis_supported(value: str, quote: str) -> bool:
    if value not in V.FEE_BASIS_VALUES:
        return False
    required, forbidden = _FEE_BASIS_PHRASES[value]
    ql = quote.lower()
    if any(bad in ql for bad in forbidden):
        return False
    return any(good in ql for good in required)


def _field_claim_valid(field_name: str, value: str, quote: str) -> Tuple[bool, str]:
    """Field-specific deterministic checks. Returns (ok, warning_slug)."""
    if not value or not quote:
        return (False, "empty_value_or_quote")           # rule 1/12
    if field_name in V.BOOLEAN_FIELDS and value not in ("true", "false"):
        return (False, "non_boolean_value")               # rule 12
    if field_name in (V.FIELD_DOGS_ACCEPTED, V.FIELD_CATS_ACCEPTED):
        # Rule 11 is symmetric across the boolean value: a species claim --
        # accepted OR not -- is supportable only when its quote actually names
        # that species. A generic "no pets allowed" (or "pets welcome") quote
        # names no species, so it can never support dogs_accepted / cats_accepted
        # in EITHER direction; a negative species value is legitimate only from
        # an explicit "dogs are not accepted"-style statement. (The boolean
        # format itself is already enforced immediately above.)
        if not _species_supported(field_name, quote):
            return (False, "species_not_in_quote")        # rule 11
    if field_name in V.NUMERIC_FIELDS and not _numeric_supported(value, quote):
        return (False, "number_not_in_quote")             # rules 9/10
    if field_name == V.FIELD_FEE_BASIS and not _fee_basis_supported(value, quote):
        return (False, "fee_basis_phrase_absent")         # rule 8
    if field_name == V.FIELD_REFUNDABLE_DEPOSIT and "deposit" not in quote.lower():
        return (False, "deposit_word_absent")             # rule 7
    return (True, "")


class _ValidClaim:
    __slots__ = ("value", "quote", "url", "source_type", "rank")

    def __init__(self, value, quote, url, source_type, rank):
        self.value = value
        self.quote = quote
        self.url = url
        self.source_type = source_type
        self.rank = rank


def validate_proposal(
    assignment: Assignment, proposal: ModelProposal, *, provider: str = "", model: str = "",
) -> WorkerResult:
    """Turn an untrusted ModelProposal into a validated WorkerResult."""
    provider = provider or proposal.provider
    model = model or proposal.model
    requested = tuple(assignment.requested_fields) or V.POLICY_FIELDS

    def _finish(status, facts, contradictions, warnings, sel_url, sel_type):
        proposed = tuple(facts)
        unknown = tuple(f.field_name for f in proposed
                        if f.state == V.NOT_STATED and f.field_name in requested)
        quotes = tuple(sorted({f.evidence_quote for f in proposed
                               if f.state == V.SUPPORTED and f.evidence_quote}))
        return WorkerResult(
            assignment_id=assignment.assignment_id, listing_key=assignment.listing_key,
            status=status, selected_source_url=sel_url, selected_source_type=sel_type,
            evidence_quotes=quotes, proposed_facts=proposed, unknown_fields=unknown,
            contradictions=tuple(contradictions), warnings=tuple(sorted(set(warnings))),
            provider=provider, model=model, input_tokens=proposal.input_tokens,
            output_tokens=proposal.output_tokens, cached_input_tokens=proposal.cached_input_tokens,
            latency_ms=proposal.latency_ms, attempt_count=proposal.attempt_count,
        ).with_hash()

    # Provider-level failure (rule 14 for the ok=False case).
    if not proposal.ok:
        facts = [ProposedField(f, V.NOT_STATED) for f in requested]
        return _finish(V.STATUS_FAILED, facts, (), ("provider_error:" + (proposal.error or "unknown"),), "", "")

    usable = _usable_official_docs(assignment)
    if not usable:
        # No usable official source -> no supported facts (rules 4/14).
        facts = [ProposedField(f, V.NOT_STATED) for f in requested]
        return _finish(V.STATUS_NO_OFFICIAL_SOURCE, facts, (), ("no_usable_official_source",), "", "")

    doc_by_url = {d.source_url: d for d in usable}
    selected = usable[0]                     # highest rank, deterministic (rule 5)

    warnings: List[str] = []
    valid_by_field: Dict[str, List[_ValidClaim]] = {}
    for claim in proposal.claims:
        f = claim.field_name
        if f not in V.POLICY_FIELD_SET:
            warnings.append("dropped_unknown_field:" + f)
            continue
        doc = doc_by_url.get(claim.source_url)
        if doc is None:                       # rule 3/4: cited source not a usable official doc
            warnings.append("rejected_%s:source_not_official" % f)
            continue
        if not _quote_verbatim(claim.evidence_quote, doc):   # rule 2
            warnings.append("rejected_%s:quote_not_verbatim" % f)
            continue
        ok, why = _field_claim_valid(f, claim.value, claim.evidence_quote)
        if not ok:                            # rules 1/7/8/9/10/11/12
            warnings.append("rejected_%s:%s" % (f, why))
            continue
        valid_by_field.setdefault(f, []).append(
            _ValidClaim(claim.value, claim.evidence_quote, doc.source_url,
                        doc.source_type, V.SOURCE_TYPE_RANK.get(doc.source_type, 0)))

    facts: List[ProposedField] = []
    contradictions: List[str] = []
    field_names = list(requested) + [f for f in valid_by_field if f not in requested]
    seen = set()
    for f in field_names:
        if f in seen:
            continue
        seen.add(f)
        claims = valid_by_field.get(f, [])
        if not claims:
            facts.append(ProposedField(f, V.NOT_STATED))    # rule 12
            continue
        top_rank = max(c.rank for c in claims)
        top = [c for c in claims if c.rank == top_rank]
        top_values = {c.value for c in top}
        if len(top_values) > 1:
            # Two same-rank (e.g. property-specific) sources disagree -> genuine
            # contradiction (rule 13). Never silently pick one.
            contradictions.append("%s: %s" % (f, " vs ".join(sorted(top_values))))
            c = sorted(top, key=lambda c: c.url)[0]
            facts.append(ProposedField(f, V.CONTRADICTORY, source_url=c.url,
                                       source_type=c.source_type,
                                       warnings=("same_rank_sources_disagree",)))
            continue
        winner = sorted(top, key=lambda c: c.url)[0]
        w = []
        lower_disagree = {c.value for c in claims if c.rank < top_rank and c.value != winner.value}
        if lower_disagree:
            # A brand (lower rank) disagrees with the property -- property wins,
            # brand disagreement noted, never allowed to override (rule 6).
            w.append("lower_rank_source_disagrees")
            warnings.append("brand_disagrees_with_property:" + f)
        facts.append(ProposedField(f, V.SUPPORTED, value=winner.value,
                                   evidence_quote=winner.quote, source_url=winner.url,
                                   source_type=winner.source_type, warnings=tuple(w)))

    # Rule 7: fee and deposit must not share a single quote (never merged).
    fee = next((f for f in facts if f.field_name == V.FIELD_PET_FEE and f.state == V.SUPPORTED), None)
    dep = next((f for f in facts if f.field_name == V.FIELD_REFUNDABLE_DEPOSIT and f.state == V.SUPPORTED), None)
    if fee and dep and fee.evidence_quote == dep.evidence_quote:
        facts = [ProposedField(V.FIELD_REFUNDABLE_DEPOSIT, V.NOT_STATED) if x is dep else x
                 for x in facts]
        warnings.append("rejected_refundable_deposit:fee_deposit_same_quote")

    # Deterministic cross-source reconciliation (rule 13, ATLAS-WORKERS-002).
    # Re-read the supplied official sources ourselves and flag any field on which
    # two eligible authoritative sources genuinely disagree. This does NOT depend
    # on the model surfacing both sides: an empty response, or one that silently
    # picked a side, still yields CONTRADICTORY. A disputed field is forced to
    # CONTRADICTORY (overriding any model SUPPORTED value -- the model must never
    # silently choose one side), and both citations, values, and verbatim quotes
    # are preserved in the contradiction record for human review. Fields already
    # flagged by the model path above are left untouched (no double-reporting).
    already_contradictory = {c.split(":", 1)[0].strip() for c in contradictions}
    for field_name, contra in sorted(detect_field_contradictions(usable).items()):
        if field_name in already_contradictory:
            continue
        contradictions.append(contra.summary)
        first = contra.sides[0]
        forced = ProposedField(field_name, V.CONTRADICTORY, source_url=first.source_url,
                               source_type=first.source_type,
                               warnings=("cross_source_contradiction",))
        if any(f.field_name == field_name for f in facts):
            facts = [forced if f.field_name == field_name else f for f in facts]
        else:
            facts.append(forced)

    # Status derivation.
    if contradictions:
        status = V.STATUS_CONTRADICTORY
    elif any(w.startswith("rejected_") or w.startswith("brand_disagrees_with_property")
             for w in warnings):
        status = V.STATUS_NEEDS_REVIEW
    else:
        status = V.STATUS_COMPLETED
    return _finish(status, facts, contradictions, warnings,
                   selected.source_url, selected.source_type)
