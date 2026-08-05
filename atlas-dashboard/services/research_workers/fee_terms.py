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


# --------------------------------------------------------------------------- #
# PTF-WORKERS-FEE-TERMS -- parsing compressed stay-length tier notation.
#
# validate_fee_term above checks terms a MODEL proposed. This parses them
# straight out of source text, for the common case of a property publishing its
# tiers in a compressed field:
#
#     $75(1-4n)$125(5+n)2pet Max dog/cat only
#     $50(1-4n),$75(5+n) 2petsMax,dog/cat only
#     $75 for 1-4 nights; $125 for 5 nights or more
#
# Brand-neutral by construction: it keys on notation, never on a hotel, chain or
# domain. Two properties printing the same numbers is a coincidence this code
# cannot observe -- each capture is parsed on its own.
#
# Fails closed and TOTALLY: any problem returns NO terms rather than some, and
# every problem found is reported, so a reviewer sees the whole reason.
# --------------------------------------------------------------------------- #

# One tier: an amount, then a stay-length range, in the punctuation variants
# real pages use -- "(1-4n)", "(1-4 nights)", "for 1-4 nights", "5+n",
# "5 nights or more", with -, en dash or em dash.
#: Stay-length units a lodging ladder actually uses. "days" appears beside
#: "nights" on the same chain's pages ("1-4 days $75.00, 5 plus days $125.00"),
#: and the compact forms drop to "nt" or a bare "n". Longest alternative first,
#: so "nt" is never shortened to "n".
_STAY_UNIT = r"(?:nights?|nts?|days?|n)\b"

#: Open-ended marker: "5+" or "5 plus".
_TIER_OPEN = r"(?:\+|\s+plus\b)"

_TIER_RE = re.compile(
    r"\$\s?(?P<amt>\d[\d,]*(?:\.\d{1,2})?)"
    # A short connector may sit between the amount and its range -- "for",
    # "per night for", a bracket, or nothing. Digits and $ are excluded so an
    # amount can never reach past a neighbouring tier to claim its range.
    r"[^$\d]{0,20}?[\(\[]?\s*"
    r"(?P<lo>\d+)\s*"
    r"(?:(?:[-–—]|\s+to\s+)\s*(?P<hi>\d+)|(?P<plus>" + _TIER_OPEN + r"))?"
    r"\s*" + _STAY_UNIT +
    r"\s*(?P<ormore>or\s+(?:more|longer|greater))?"
    r"\s*[\)\]]?",
    re.I)

# The same ladder written range-first. Hilton's own rendered page uses this for
# one property while its embedded payload uses the amount-first form for
# another -- one chain, two notations, which is exactly why this parser keys on
# notation rather than on a source.
#
#     1-4 night stay $50; 5+ night stay $75
_TIER_RANGE_FIRST_RE = re.compile(
    r"(?P<lo>\d+)\s*"
    r"(?:(?:[-–—]|\s+to\s+)\s*(?P<hi>\d+)|(?P<plus>" + _TIER_OPEN + r"))?"
    r"\s*" + _STAY_UNIT + r"\s*"
    r"(?P<ormore>or\s+(?:more|longer|greater))?"
    r"[^$\d]{0,16}?"
    r"\$\s?(?P<amt>\d[\d,]*(?:\.\d{1,2})?)",
    re.I)

#: The open-ended rung sometimes drops its unit once the first rung has
#: established it -- "1-4n $75, 5+ $125". Admitted ONLY to supplement a ladder
#: that already carries a unit-bearing tier: a lone "5+ $125" states no stay
#: length at all, and reading one as a ladder rung would invent the unit.
#: ``hi`` is present but always empty: an open-ended rung has no upper bound,
#: and the assembly reads the same group names from every tier pattern.
_TIER_OPEN_NO_UNIT_RE = re.compile(
    r"(?P<lo>\d+)(?P<hi>)\s*(?P<plus>\+)\s*"
    r"(?P<ormore>or\s+(?:more|longer|greater))?"
    r"[^$\d]{0,16}?"
    r"\$\s?(?P<amt>\d[\d,]*(?:\.\d{1,2})?)",
    re.I)

#: An amount whose bracketed range has a NON-NUMERIC boundary -- "$75(1-na)".
#: The source plainly means a ladder and its boundary is unreadable. Such a
#: ladder is refused outright, because the alternative is publishing whichever
#: sibling rung happened to parse as though it were a flat fee for every stay.
_TIER_MALFORMED_RANGE_RE = re.compile(
    r"\$\s?\d[\d,]*(?:\.\d{1,2})?\s*[\(\[]\s*\d+\s*[-–—]\s*[A-Za-z]+", re.I)

# Wording that would make a basis EXPLICIT. Absent these, the basis is not
# stated and must never be asserted in public copy -- mirroring the existing
# FEE_SCOPE_UNSTATED rule that a scope the source omits is never inferred.
_BASIS_STATED_RE = re.compile(
    r"per\s+(?:night|day|stay|visit)|nightly|daily|each\s+night|a\s+night", re.I)

TIER_PARSE_PROBLEMS = (
    "tier_notation_unparseable",
    "tier_single_only",
    "tier_missing_range_boundary",
    "tier_invalid_range",
    "tier_duplicate_range",
    "tier_ranges_overlap",
    "tier_amount_not_in_source",
    "tier_open_tail_without_bounded_opener",
    "tier_prose_ladder_ambiguous",
)

# PTF-FEE-TIERS-005 -- the PROSE ladder.
#
# A property may write the same two-tier fee without any of the notations
# above:
#
#     $75 fee, per pet, applies for stays up to 7 nights; $150 for all
#     longer stays.
#
# Neither tier is in compressed form. The first states only its UPPER bound,
# in words ("up to 7 nights"), so _TIER_RE reads its 7 as a range START and
# then finds no boundary. The second states no number at all -- "longer" is
# its whole range -- so nothing matches it. The ladder is entirely legible to
# a reader and entirely invisible to the parser.
#
# This path is consulted ONLY when the notations above could not form a
# ladder, so no source that parses today can have its reading changed here.
# It is brand-neutral like everything else in this module: it keys on the
# wording, never on a property, chain or domain.

#: The bounded opener: an amount whose range is given as a spoken ceiling.
#: The gap excludes "$" so an amount can never reach past a neighbouring
#: amount to claim its boundary.
_PROSE_OPENER_RE = re.compile(
    r"\$\s?(?P<amt>\d[\d,]*(?:\.\d{1,2})?)"
    r"[^$]{0,64}?"
    r"\bup\s+to\s+(?P<hi>\d+)\s*(?P<unit>nights?|days?)\b",
    re.I)

#: The open final tier, amount first: "$150 for all longer stays".
_PROSE_TAIL_AFTER_RE = re.compile(
    r"\$\s?(?P<amt>\d[\d,]*(?:\.\d{1,2})?)"
    r"[^$\d]{0,28}?"
    r"\b(?:for\s+(?:all\s+|any\s+)?longer(?:\s+stays?)?"
    r"|thereafter"
    r"|for\s+stays?\s+beyond\s+that)\b",
    re.I)

#: The same tier written phrase first: "thereafter $150", "then $150".
_PROSE_TAIL_BEFORE_RE = re.compile(
    r"\b(?:then|thereafter)\b"
    r"[^$\d]{0,28}?"
    r"\$\s?(?P<amt>\d[\d,]*(?:\.\d{1,2})?)",
    re.I)

_PROSE_UNIT = {"night": V.BOUNDARY_UNIT_NIGHTS, "nights": V.BOUNDARY_UNIT_NIGHTS,
               "day": V.BOUNDARY_UNIT_DAYS, "days": V.BOUNDARY_UNIT_DAYS}

#: An explicit per-pet scope: the charge applies to each animal, so a second pet
#: doubles it. Read per TIER, from that tier's OWN span -- never from a
#: neighbouring clause, because scope elided by grammar is not scope stated.
_SCOPE_PER_PET_RE = re.compile(r"per\s+(?:pet|animal)\b|each\s+(?:pet|animal)\b", re.I)
#: A scope stated about the ROOM or the whole stay is not a per-pet scope, and a
#: span carrying both is ambiguous rather than per-pet.
_SCOPE_NOT_PER_PET_RE = re.compile(r"per\s+room\b|per\s+party\b|per\s+reservation\b", re.I)


def _prose_tier_scope(span: str) -> str:
    """The scope this tier's own wording states, or UNSTATED.

    Deliberately blind to the rest of the sentence. "$75 fee, per pet, applies
    for stays up to 7 nights; $150 for all longer stays" states a scope for the
    first tier and elides it for the second. Ellipsis is how English avoids
    repetition, not a statement -- and this module's rule is that a scope the
    source does not state is never inferred.
    """
    if _SCOPE_NOT_PER_PET_RE.search(span or ""):
        return V.FEE_SCOPE_UNSTATED
    if _SCOPE_PER_PET_RE.search(span or ""):
        return V.FEE_SCOPE_PER_PET
    return V.FEE_SCOPE_UNSTATED


def _parse_prose_ladder(text: str, *, source_url: str, source_type: str,
                        currency: str) -> Tuple[Tuple[PetFeeTerm, ...], List[str]]:
    """A bounded spoken opener followed by an open-ended spoken final tier.

    The open tier's lower bound is DERIVED as ``opener.hi + 1`` -- arithmetic
    on a boundary the source states, not a number invented here. "Longer than
    7 nights" is 8 nights or more, and nothing else, for a whole-night stay.
    Because that derivation is the one step a reader cannot see in a bare
    "$150 for all longer stays", the open tier carries the WHOLE ladder span
    as its evidence quote, so the 7 that licenses the 8 travels with it.

    Fails closed and totally, like every other path here: exactly one opener
    and exactly one tail, the tail after the opener, or no terms at all.
    """
    src = text or ""
    openers = list(_PROSE_OPENER_RE.finditer(src))
    tails = list(_PROSE_TAIL_AFTER_RE.finditer(src)) + list(_PROSE_TAIL_BEFORE_RE.finditer(src))
    if not tails:
        return ((), [])                      # not this shape; caller keeps its own verdict
    if not openers:
        # A trailing "and $150 thereafter" with nothing bounding what came
        # before it cannot be positioned on a stay at all.
        return ((), ["tier_open_tail_without_bounded_opener"])
    if len(openers) > 1 or len(tails) > 1:
        return ((), ["tier_prose_ladder_ambiguous"])

    opener, tail = openers[0], tails[0]
    if tail.start() < opener.end():
        # The open tier must FOLLOW the bounded one; a ladder written the other
        # way round is not a shape this understands.
        return ((), ["tier_prose_ladder_ambiguous"])

    lo_amount = canonical_amount(opener.group("amt"))
    hi_amount = canonical_amount(tail.group("amt"))
    if lo_amount is None or hi_amount is None:
        return ((), ["tier_amount_not_in_source"])
    boundary = int(opener.group("hi"))
    if boundary < 1:
        return ((), ["tier_invalid_range"])
    unit = _PROSE_UNIT[opener.group("unit").lower()]
    ladder_quote = " ".join(src[opener.start():tail.end()].split())

    # Scope is read PER TIER from that tier's own span. A source may state it
    # once and elide it for the rest of the sentence; carrying the first tier's
    # scope onto the second would publish an inference, and dropping it from the
    # first would discard something the source says plainly.
    return ((
        PetFeeTerm(
            role=V.FEE_ROLE_ONE_TIME_CHARGE, amount=lo_amount, currency=currency,
            basis=V.FEE_TERM_BASIS_ONE_TIME,
            scope=_prose_tier_scope(opener.group(0)),
            condition_type=V.FEE_CONDITION_STAY_LENGTH_RANGE,
            condition_min=1, condition_max=boundary, boundary_unit=unit,
            evidence_quote=" ".join(opener.group(0).split()),
            source_url=source_url, source_type=source_type),
        PetFeeTerm(
            role=V.FEE_ROLE_ONE_TIME_CHARGE, amount=hi_amount, currency=currency,
            basis=V.FEE_TERM_BASIS_ONE_TIME,
            scope=_prose_tier_scope(tail.group(0)),
            condition_type=V.FEE_CONDITION_STAY_LENGTH_RANGE,
            condition_min=boundary + 1, condition_max=None, boundary_unit=unit,
            evidence_quote=ladder_quote,
            source_url=source_url, source_type=source_type),
    ), [])


def basis_is_stated(text: str) -> bool:
    """Does the source explicitly state a fee basis (per night / per stay / ...)?

    A compressed tier field like "$75(1-4n)$125(5+n)" states an AMOUNT and a
    STAY RANGE and nothing about recurrence. Whether $75 is a per-stay total for
    a 1-4 night stay or a nightly rate within it is genuinely unstated, and
    publishing either reading as fact would invent the difference.
    """
    return bool(_BASIS_STATED_RE.search(text or ""))


def parse_fee_tiers(text: str, *, source_url: str = "", source_type: str = "",
                    currency: str = "USD") -> Tuple[Tuple[PetFeeTerm, ...], List[str]]:
    """Parse stay-length fee tiers out of source text.

    Returns ``(terms, problems)``. ``terms`` is empty whenever ``problems`` is
    non-empty -- a partially-understood tiered fee is not a fee to publish.

    The role is ONE_TIME_CHARGE and the basis ONE_TIME because the contract
    requires members of its closed vocabularies; neither is a claim about
    recurrence. ``basis_is_stated`` is what callers consult before saying
    anything about basis to a reader.
    """
    problems: List[str] = []
    # A ladder whose range boundary is unreadable is refused before anything
    # else. Parsing on would leave one surviving rung to be published as a flat
    # fee for every stay length, which is worse than saying nothing.
    if _TIER_MALFORMED_RANGE_RE.search(text or ""):
        return ((), ["tier_malformed_range_boundary"])

    matches = list(_TIER_RE.finditer(text or ""))
    if len(matches) < 2:
        # Try the range-first notation before giving up -- the same ladder,
        # written the other way round.
        alt = list(_TIER_RANGE_FIRST_RE.finditer(text or ""))
        if len(alt) > len(matches):
            matches = alt
    if len(matches) == 1:
        # One unit-bearing rung found. Its ladder may have an open-ended sibling
        # that dropped the unit ("1-4n $75, 5+ $125"). Supplement only -- and
        # only with rungs that do not overlap what already matched, so an
        # amount is never counted twice.
        spans = {(m.start(), m.end()) for m in matches}
        extra = [m for m in _TIER_OPEN_NO_UNIT_RE.finditer(text or "")
                 if not any(m.start() < e and s < m.end() for s, e in spans)]
        if extra:
            matches = sorted(matches + extra, key=lambda m: m.start())
    if len(matches) < 2:
        # PTF-FEE-TIERS-005. Neither compressed notation formed a ladder. Before
        # settling for that verdict, try the spoken form. Consulted LAST and
        # only here, so a source that parses above is never re-read by it.
        prose_terms, prose_problems = _parse_prose_ladder(
            text, source_url=source_url, source_type=source_type, currency=currency)
        if prose_terms:
            return (prose_terms, [])
        if prose_problems:
            return ((), sorted(set(prose_problems)))
    if not matches:
        return ((), ["tier_notation_unparseable"])
    if len(matches) < 2:
        # One priced range is a conditional single fee, not a tier ladder. The
        # caller keeps its ordinary scalar handling.
        return ((), ["tier_single_only"])

    terms: List[PetFeeTerm] = []
    for m in matches:
        amount = canonical_amount(m.group("amt"))
        if amount is None:
            problems.append("tier_amount_not_in_source")
            continue
        lo = int(m.group("lo"))
        hi = int(m.group("hi")) if m.group("hi") else None
        open_ended = bool(m.group("plus") or m.group("ormore"))
        if hi is None and not open_ended:
            # "$75 for 4 nights" states a point, not a range this can bound.
            problems.append("tier_missing_range_boundary")
            continue
        if hi is not None and hi < lo:
            problems.append("tier_invalid_range")
            continue
        terms.append(PetFeeTerm(
            role=V.FEE_ROLE_ONE_TIME_CHARGE, amount=amount, currency=currency,
            basis=V.FEE_TERM_BASIS_ONE_TIME, scope=V.FEE_SCOPE_UNSTATED,
            condition_type=V.FEE_CONDITION_STAY_LENGTH_RANGE,
            condition_min=lo, condition_max=hi,
            boundary_unit=V.BOUNDARY_UNIT_NIGHTS,
            evidence_quote=" ".join(m.group(0).split()),
            source_url=source_url, source_type=source_type))

    ordered = sorted(terms, key=lambda t: (t.condition_min or 0,
                                           t.condition_max if t.condition_max is not None
                                           else float("inf")))
    for i, a in enumerate(ordered):
        for b in ordered[i + 1:]:
            if (a.condition_min, a.condition_max) == (b.condition_min, b.condition_max):
                problems.append("tier_duplicate_range")
            elif _overlaps(a, b):
                problems.append("tier_ranges_overlap")

    if problems:
        return ((), sorted(set(problems)))
    return (tuple(ordered), [])


# A stated ceiling on what a stay can cost: "$50 per night up to $150",
# "up to $150 fee", "not to exceed $150", "capped at $150". The dollar sign is
# required -- "Earn up to 150,000 Bonus Points" is not a fee cap, and a bare
# number never becomes one.
_FEE_CAP_RE = re.compile(
    r"(?:up\s+to|not\s+to\s+exceed|capped\s+at|maximum\s+of|max(?:imum)?)\s*"
    r"(?:a\s+)?(?:total\s+of\s+)?\$\s?(\d[\d,]*(?:\.\d{1,2})?)",
    re.I)


def detect_fee_cap(text: str) -> Tuple[Optional[str], str]:
    """Return ``(canonical_amount, verbatim_quote)`` for a stated fee ceiling.

    PTF-FEES-CAP. A recurring fee with a cap is not the same policy as the
    recurring fee alone: "$50 per night up to $150" costs $150 for a week, not
    $350. Publishing the rate without its ceiling overstates a long stay, which
    is the mirror image of the tier-flattening bug -- same class, opposite
    direction.

    Returns ``(None, "")`` when no ceiling is stated. Never inferred from an
    amount alone.
    """
    m = _FEE_CAP_RE.search(text or "")
    if not m:
        return (None, "")
    return (canonical_amount(m.group(1)), " ".join(m.group(0).split()))


# --------------------------------------------------------------------------- #
# PTF-WORKERS -- what the CURRENT production chain can faithfully carry.
#
# Routing used to withhold every non-null fee policy as
# DOWNSTREAM_FEE_SCHEMA_UNSUPPORTED, on the grounds that the importer and
# renderer were single-value. That stopped being true when fee_tiers shipped:
# three published profiles render a stay-length ladder today. The blanket rule
# therefore answered the wrong question -- "is there a structured fee?" instead
# of "can we render THIS one honestly?"
#
# This answers the second. It is deliberately a capability statement about the
# production chain as it exists, derived from the shape those three profiles
# actually carry and from what the renderer demonstrably does with it. Anything
# outside that shape is refused rather than guessed at, because the failure mode
# is publishing a fee a guest would be charged differently for.
# --------------------------------------------------------------------------- #

#: Units the profile renderer prints verbatim in "stays of 1-7 <unit>".
_DOWNSTREAM_UNITS = (V.BOUNDARY_UNIT_NIGHTS, V.BOUNDARY_UNIT_DAYS)
#: The renderer formats every amount with a literal "$".
_DOWNSTREAM_CURRENCY = "USD"

DOWNSTREAM_UNSUPPORTED_REASONS = (
    "downstream_no_terms",
    "downstream_single_tier_is_not_a_ladder",
    "downstream_role_not_renderable",
    "downstream_condition_not_stay_length",
    "downstream_mixed_or_unsupported_unit",
    "downstream_currency_not_renderable",
    "downstream_amount_unparseable",
    "downstream_ladder_does_not_start_at_one",
    "downstream_ladder_has_gap",
    "downstream_ladder_overlaps",
    "downstream_open_tier_not_last",
    "downstream_final_tier_not_open",
    "downstream_basis_asserted_but_unrenderable",
)


def downstream_fee_schema_support(policy: Optional[PetFeePolicy]) -> Tuple[bool, List[str]]:
    """Can the production package + renderer represent THIS policy faithfully?

    Returns ``(supported, reasons)``; ``reasons`` is empty exactly when
    supported. A policy of ``None`` is trivially supported -- there is no
    structure to carry.

    The supported shape is the one three published profiles already carry: a
    contiguous stay-length ladder of two or more one-time charges, starting at
    night 1, each tier closed except the last, one unit, USD, and no asserted
    basis (the renderer states plainly that the source gives none, so a policy
    claiming one would be rendered as a falsehood).
    """
    if policy is None:
        return (True, [])
    terms = list(policy.terms or ())
    problems: List[str] = []
    if not terms:
        return (False, ["downstream_no_terms"])
    if len(terms) < 2:
        # One priced range is a conditional single fee. The renderer would print
        # "stays of 1 nights or more", which is not a ladder and reads as one.
        problems.append("downstream_single_tier_is_not_a_ladder")

    for t in terms:
        if t.role != V.FEE_ROLE_ONE_TIME_CHARGE:
            problems.append("downstream_role_not_renderable")
        if t.condition_type != V.FEE_CONDITION_STAY_LENGTH_RANGE:
            problems.append("downstream_condition_not_stay_length")
        if t.currency != _DOWNSTREAM_CURRENCY:
            problems.append("downstream_currency_not_renderable")
        if canonical_amount(t.amount) != t.amount:
            problems.append("downstream_amount_unparseable")
    units = {t.boundary_unit for t in terms}
    if len(units) != 1 or not units <= set(_DOWNSTREAM_UNITS):
        problems.append("downstream_mixed_or_unsupported_unit")

    ordered = sorted(terms, key=lambda t: (t.condition_min if t.condition_min is not None else 0))
    if ordered[0].condition_min != 1:
        problems.append("downstream_ladder_does_not_start_at_one")
    for i, t in enumerate(ordered):
        is_last = i == len(ordered) - 1
        if t.condition_max is None and not is_last:
            problems.append("downstream_open_tier_not_last")
        if t.condition_max is not None and is_last:
            problems.append("downstream_final_tier_not_open")
    for a, b in zip(ordered, ordered[1:]):
        if a.condition_max is None:
            continue                       # already reported as an open non-final tier
        if b.condition_min is None or b.condition_min <= a.condition_max:
            problems.append("downstream_ladder_overlaps")
        elif b.condition_min != a.condition_max + 1:
            # A gap leaves stays whose price nothing states. The package schema
            # has no way to say "unpriced between 5 and 8 nights".
            problems.append("downstream_ladder_has_gap")
    return (not problems, sorted(set(problems)))


def tier_facts(terms: Sequence[PetFeeTerm], *, basis_stated: bool) -> List[Dict]:
    """Publishable dicts for a parsed tier ladder.

    ``basis_stated`` travels WITH the data rather than being recomputed at
    render time, so a renderer cannot accidentally assert a basis the source
    never gave.
    """
    out = []
    for t in terms:
        d = t.to_dict()
        d["basis_stated"] = bool(basis_stated)
        out.append(d)
    return out


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


# --------------------------------------------------------------------------- #
# PTF-FEE-TIERS-005A -- read the ladder the SOURCE states, before its several
# amounts are mistaken for disagreement.
#
# ``detect_multiple_fee_amounts`` answers "does this evidence state more than
# one pet-fee amount?", and a ladder always does. That question is the right
# backstop against a model FLATTENING a ladder, but it cannot tell a ladder
# from a contradiction, so a source that states its tiers perfectly clearly was
# routed as though it disagreed with itself.
#
# This reads the tiers deterministically from the source text. It is strictly
# stronger evidence than the model's proposal -- the parser cannot paraphrase --
# and it either produces a COMPLETE ladder or nothing at all. Brand-neutral and
# notation-driven, like every other path in this module.
# --------------------------------------------------------------------------- #

def source_stay_length_ladder(
        docs: Sequence[SourceDocument]) -> Tuple[PetFeeTerm, ...]:
    """The one unambiguous stay-length ladder these official sources state.

    Returns ``()`` unless exactly one reading emerges. Specifically:

      * only usable official documents are read;
      * a document whose text yields any parse PROBLEM contributes nothing --
        the total-failure rule of ``parse_fee_tiers`` is preserved end to end;
      * if two documents yield ladders that disagree, that is a real conflict
        between sources and this reports no ladder, leaving the existing
        contradiction machinery to handle it.

    A ladder is returned only when it is also internally sound: contiguous,
    non-overlapping, and open-ended in its final tier -- the same shape the
    published package already carries.
    """
    readings: Dict[Tuple, Tuple[PetFeeTerm, ...]] = {}
    for d in docs:
        if not getattr(d, "is_usable_official", False):
            continue
        terms, problems = parse_fee_tiers(
            d.content_text, source_url=d.source_url, source_type=d.source_type)
        if problems or len(terms) < 2:
            continue
        key = tuple((t.amount, t.condition_min, t.condition_max, t.boundary_unit)
                    for t in terms)
        readings[key] = terms
    if len(readings) != 1:
        return ()                       # nothing, or two sources that disagree
    terms = next(iter(readings.values()))

    ordered = sorted(terms, key=lambda t: (t.condition_min or 0))
    for a, b in zip(ordered, ordered[1:]):
        if a.condition_max is None or b.condition_min != a.condition_max + 1:
            return ()                   # a gap or an early open tier is not a ladder
    if ordered[-1].condition_max is not None:
        return ()                       # a ladder's last tier must be open-ended
    return tuple(ordered)


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
