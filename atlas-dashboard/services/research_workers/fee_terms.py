"""ATLAS-WORKERS-006 -- structured pet-fee term validation + same-source
reconciliation.

Ordinary deterministic Atlas code over the supplied source text (never treated
as instructions). It canonicalizes each amount to an exact decimal string
(``Decimal``, never binary float), verifies every attribute against the cited
verbatim quote, and reconciles conditional terms from ONE source without either
flattening them into a misleading single fee or letting a genuine contradiction
through. It produces a validated, deterministically-ordered ``PetFeePolicy``.

Scope, basis, and role are DISTINCT dimensions (never a combinatorial value).
No hotel names, benchmark ids, or URLs drive any decision.
"""

from __future__ import annotations

import re
from decimal import Decimal, InvalidOperation
from typing import Dict, List, Optional, Sequence, Tuple

from services.research_workers import vocabulary as V
from services.research_workers.contracts import PetFeePolicy, PetFeeTerm, SourceDocument
from services.research_workers.proposal import RawFeeTerm

# Language that must be present for a role/condition to be supported.
_CAP_WORDS = ("up to", "maximum", "max ", "not to exceed", "no more than", "cap", "total of", "total")
_DEPOSIT_WORD = "deposit"
_BASIS_WORDS = {
    V.FEE_TERM_BASIS_PER_NIGHT: ("night", "nightly"),
    V.FEE_TERM_BASIS_PER_DAY: ("day", "daily"),
    V.FEE_TERM_BASIS_PER_STAY: ("stay", "visit"),
    V.FEE_TERM_BASIS_ONE_TIME: (),          # a flat one-time fee needs no recurrence word
}
_UNIT_WORD = {V.BOUNDARY_UNIT_NIGHTS: "night", V.BOUNDARY_UNIT_DAYS: "day"}
_RECURRING_BASES = (V.FEE_TERM_BASIS_PER_NIGHT, V.FEE_TERM_BASIS_PER_DAY)


def canonical_amount(raw: str) -> Optional[str]:
    """Deterministic canonical decimal string ("50.00") from a raw amount such as
    "$50", "up to $150", "50", or "$25.50". Uses ``Decimal`` (never binary
    float); returns None when no monetary number is present."""
    m = re.search(r"\d[\d,]*(?:\.\d+)?", raw or "")
    if not m:
        return None
    try:
        return str(Decimal(m.group(0).replace(",", "")).quantize(Decimal("0.01")))
    except InvalidOperation:
        return None


def _int_stated(n: int, quote: str) -> bool:
    """The integer ``n`` is explicitly stated in ``quote`` as a digit or a
    cardinal word (0-20) -- the same guarantee the fact validator uses."""
    if str(n) in quote.replace(",", ""):
        return True
    return any(V.CARDINAL_WORDS.get(w) == n for w in re.findall(r"[a-z]+", quote.lower()))


def _verbatim(quote: str, doc: SourceDocument) -> bool:
    q = (quote or "").strip()
    return bool(q) and len(q) <= V.EVIDENCE_QUOTE_CAP and q in doc.content_text


def validate_fee_term(raw: RawFeeTerm,
                      doc_by_url: Dict[str, SourceDocument]) -> Tuple[Optional[PetFeeTerm], str]:
    """Deterministically validate ONE untrusted fee term. Returns
    (term, "") on success or (None, warning_slug) on rejection. Every attribute
    must be explicitly supported by a verbatim quote from a usable official
    source; nothing is inferred."""
    if raw.role not in V.FEE_TERM_ROLES:
        return (None, "invalid_role")
    amount = canonical_amount(raw.amount)
    if amount is None:
        return (None, "amount_unparseable")
    if raw.basis not in V.FEE_TERM_BASES:
        return (None, "invalid_basis")
    scope = raw.scope or V.FEE_SCOPE_UNSTATED
    if scope not in V.FEE_TERM_SCOPES:
        return (None, "invalid_scope")
    condition_type = raw.condition_type or V.FEE_CONDITION_UNCONDITIONAL
    if condition_type not in V.FEE_CONDITION_TYPES:
        return (None, "invalid_condition_type")
    doc = doc_by_url.get(raw.source_url)
    if doc is None or not doc.is_usable_official:
        return (None, "source_not_official")
    if not _verbatim(raw.evidence_quote, doc):
        return (None, "quote_not_verbatim")

    quote = raw.evidence_quote
    ql = quote.lower()
    if not _int_stated(int(amount.split(".")[0]), quote):
        return (None, "amount_not_in_quote")
    if not raw.currency:
        return (None, "currency_missing")
    if raw.currency == "USD" and not ("$" in quote or "usd" in ql or "dollar" in ql):
        return (None, "currency_not_in_quote")
    basis_words = _BASIS_WORDS.get(raw.basis, ())
    if basis_words and not any(w in ql for w in basis_words):
        return (None, "basis_not_in_quote")
    if scope == V.FEE_SCOPE_PER_PET and "pet" not in ql:
        return (None, "scope_not_in_quote")
    if scope == V.FEE_SCOPE_PER_ROOM and "room" not in ql:
        return (None, "scope_not_in_quote")
    # Role language + fee/deposit and recurring/flat integrity.
    if raw.role == V.FEE_ROLE_CAP and not any(w in ql for w in _CAP_WORDS):
        return (None, "cap_language_absent")
    if raw.role == V.FEE_ROLE_DEPOSIT and _DEPOSIT_WORD not in ql:
        return (None, "deposit_language_absent")
    if raw.role in (V.FEE_ROLE_RECURRING_CHARGE, V.FEE_ROLE_ONE_TIME_CHARGE) and _DEPOSIT_WORD in ql:
        return (None, "fee_deposit_confusion")
    if raw.role == V.FEE_ROLE_RECURRING_CHARGE and raw.basis not in _RECURRING_BASES:
        return (None, "recurring_basis_invalid")
    if raw.role != V.FEE_ROLE_RECURRING_CHARGE and raw.basis in _RECURRING_BASES:
        return (None, "non_recurring_basis_invalid")
    # Condition boundaries (typed integers, each independently supported).
    cmin, cmax, unit = raw.condition_min, raw.condition_max, raw.boundary_unit
    if condition_type == V.FEE_CONDITION_UNCONDITIONAL:
        if cmin is not None or cmax is not None or unit:
            return (None, "condition_on_unconditional_term")
        cmin = cmax = None
        unit = ""
    else:
        if cmin is None and cmax is None:
            return (None, "range_without_boundary")
        if unit not in V.BOUNDARY_UNITS:
            return (None, "invalid_boundary_unit")
        if _UNIT_WORD[unit] not in ql:
            return (None, "boundary_unit_not_in_quote")
        for b in (cmin, cmax):
            if b is not None and not _int_stated(int(b), quote):
                return (None, "condition_boundary_not_in_quote")
    return (PetFeeTerm(role=raw.role, amount=amount, currency=raw.currency, basis=raw.basis,
                       scope=scope, condition_type=condition_type, condition_min=cmin,
                       condition_max=cmax, boundary_unit=unit, evidence_quote=quote,
                       source_url=doc.source_url, source_type=doc.source_type), "")


def _bounds(t: PetFeeTerm) -> Tuple[float, float]:
    if t.condition_type == V.FEE_CONDITION_UNCONDITIONAL:
        return (float("-inf"), float("inf"))          # the whole stay
    lo = t.condition_min if t.condition_min is not None else 1
    hi = t.condition_max if t.condition_max is not None else float("inf")
    return (float(lo), float(hi))


def _overlaps(a: PetFeeTerm, b: PetFeeTerm) -> bool:
    # Strict: adjacent tiers that merely TOUCH at a shared boundary (e.g. "up to
    # 6 nights" [.,6] then "after 6 nights" [6,.]) are sequential, not
    # overlapping; a genuine interior overlap is still caught.
    (la, ha), (lb, hb) = _bounds(a), _bounds(b)
    return max(la, lb) < min(ha, hb)


def reconcile_fee_terms(terms: Sequence[PetFeeTerm]) -> Tuple[Optional[PetFeePolicy], List[str]]:
    """Same-source reconciliation (rules A-F). Returns (policy, contradictions).

    A -- identical terms deduplicate (semantic identity ignores quote wording).
    B -- different amounts with mutually EXCLUSIVE explicit conditions stay as
         separate tiers (not contradictory).
    C -- a recurring charge plus an explicit CAP are different roles, so both are
         preserved (never contradictory).
    D -- different amounts with OVERLAPPING or absent conditions in the same
         role/basis/scope group are a genuine contradiction -> withhold.
    E -- unsupported claims never reach here (rejected in validate_fee_term).
    F -- a fee and a refundable deposit are different roles -> never merged.
    """
    seen = set()
    deduped: List[PetFeeTerm] = []
    for t in terms:                                   # rule A
        if t.identity() in seen:
            continue
        seen.add(t.identity())
        deduped.append(t)
    if not deduped:
        return (None, [])

    contradictions: List[str] = []
    groups: Dict[Tuple, List[PetFeeTerm]] = {}        # rules B/C/D/F via role/basis/scope grouping
    for t in deduped:
        groups.setdefault((t.role, t.basis, t.scope), []).append(t)
    for key, ts in sorted(groups.items()):
        if len({t.amount for t in ts}) < 2:
            continue
        for i in range(len(ts)):
            for j in range(i + 1, len(ts)):
                if ts[i].amount != ts[j].amount and _overlaps(ts[i], ts[j]):    # rule D
                    contradictions.append(
                        "pet_fee_term[%s/%s/%s]: %s vs %s (overlapping or unconditional conditions)"
                        % (key[0], key[1], key[2], ts[i].amount, ts[j].amount))
    policy = PetFeePolicy(terms=tuple(sorted(deduped, key=lambda t: t.sort_key())),
                          fee_policy_version=V.FEE_POLICY_VERSION)
    return (policy, sorted(set(contradictions)))


# --------------------------------------------------------------------------- #
# Deterministic fail-closed backstop: detect multi-amount pet-fee evidence.
# The model must never be the only protection against lossy flattening.
# --------------------------------------------------------------------------- #

_MONEY_RE = re.compile(r"\$\s?\d[\d,]*(?:\.\d+)?")
# A $-amount counts as a PET-FEE amount only when it sits in pet-fee context.
_FEE_CONTEXT_RE = re.compile(
    r"fee|deposit|charge|\bcap\b|capped|\bpet\b|\bpets\b|per\s+(?:night|day|stay|pet|room)"
    r"|\bnight\b|\bnights\b|\bstay\b|\bstays\b|plus tax", re.I)
# A $-amount immediately preceded by room-rate language is a nightly ROOM rate,
# not a pet fee -- excluded so ordinary room prices never trigger the safeguard.
_ROOM_RATE_RE = re.compile(
    r"room rates?|\brates?\b[^.$]{0,20}(?:start|from|begin)|start(?:ing)?\s+at|nightly rate", re.I)


_DEPOSIT_NEAR_RE = re.compile(r"deposit", re.I)


def _pet_fee_amounts(text: str) -> set:
    out = set()
    for m in _MONEY_RE.finditer(text):
        s, e = m.start(), m.end()
        if _ROOM_RATE_RE.search(text[max(0, s - 40):s]):
            continue                                      # a room rate, not a pet fee
        window = text[max(0, s - 45):min(len(text), e + 45)]
        if not _FEE_CONTEXT_RE.search(window):
            continue                                      # not in pet-fee context
        if _DEPOSIT_NEAR_RE.search(text[max(0, s - 30):min(len(text), e + 30)]):
            continue                                      # a refundable deposit is a DISTINCT
            #                                               scalar field, not a fee tier
        amt = canonical_amount(m.group(0))
        if amt:
            out.add(amt)                                  # dedup: repeated same amount -> one
    return out


def detect_multiple_fee_amounts(docs: Sequence[SourceDocument]) -> Tuple[bool, list]:
    """True + the distinct amounts when the usable official evidence states TWO
    OR MORE distinct pet-fee-associated monetary amounts (a tiered/capped/multi
    fee). Deterministic and hotel-independent. Repeated identical amounts count
    once; room rates and non-fee prices are excluded; a single pet fee is not
    multi-term."""
    amounts: set = set()
    for d in docs:
        if getattr(d, "is_usable_official", False):
            amounts |= _pet_fee_amounts(d.content_text)
    return (len(amounts) >= 2, sorted(amounts))


def build_fee_policy(raw_terms: Sequence[RawFeeTerm],
                     doc_by_url: Dict[str, SourceDocument]) -> Tuple[Optional[PetFeePolicy], List[str], List[str]]:
    """Validate then reconcile the model's untrusted fee terms.

    Returns (policy_or_None, contradiction_summaries, rejection_warnings). A term
    that fails validation is dropped with a ``rejected_fee_term:<slug>`` warning
    (rule E). The policy is None when no term validates."""
    validated: List[PetFeeTerm] = []
    warnings: List[str] = []
    for raw in raw_terms:
        term, why = validate_fee_term(raw, doc_by_url)
        if term is None:
            warnings.append("rejected_fee_term:" + why)
        else:
            validated.append(term)
    policy, contradictions = reconcile_fee_terms(validated)
    return (policy, contradictions, warnings)
