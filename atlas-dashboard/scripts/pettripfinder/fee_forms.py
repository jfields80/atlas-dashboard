"""PTF-FEES-FORMS -- two fee wordings the labelled patterns cannot reach, and
the contradiction that must never be resolved by picking a side.

The labelled patterns in the promoter all read LABEL then AMOUNT:
"Non-Refundable Pet Fee Per Stay: $100.00". Two shapes in the live corpus put
the pieces in a different order and were read as no fee at all:

    "$50 USD pet fee will apply per pet per night"   -- amount BEFORE the label
    "$150 non-refundable fee."                       -- amount BEFORE the label
    "Pet fee per night: 30 USD"                      -- basis INSIDE the label

Silence is the dangerous outcome here. A property whose own page says $50 per
pet per night published "Pet charge: Not stated", which is not a gap a reader
can see -- it reads as a hotel that does not charge for pets.

The third thing this module does is refuse to answer. One property states a
stay-length ladder AND a flat nightly rate on the same page:

    "Nonrefundable fee of 75USD for 1 to 4 nights and 125USD for 5 nights or
     more. Pet fee per night: 50 USD"

A four-night stay costs $75 under the first sentence and $200 under the second.
Both are the property's own words, nothing here can tell which governs, and
choosing silently would invent the difference. The fee is withheld and both
quotations are carried so a reviewer sees exactly what the source said.

Timidity rules, shared with the other prose readers:

  * currency is mandatory -- "$", "USD", "dollar(s)". A bare number is not money;
  * the amount must sit against explicit FEE language, not merely near a number;
  * a segment naming a penalty, deposit, damage, cleaning or incidental charge
    contributes nothing, whatever else it says;
  * basis is never invented. "$150 non-refundable fee" yields an amount and an
    empty basis, which downstream renders as "Not stated";
  * only the already-located policy block is ever read. There is no page-wide
    search here and no model.

Nothing here names a brand, a property, a hotel id, a property code or a URL.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import List, Optional, Tuple

from scripts.pettripfinder.prose_facts import _PET_NOUNS, is_stay_conditional_multi_amount

# --------------------------------------------------------------------------- #
# Shared vocabulary.
# --------------------------------------------------------------------------- #

#: Currency is mandatory in both directions: "$50", "50 USD", "$50 USD".
_MONEY = (r"(?:\$\s*(?P<sym>\d[\d,]*(?:\.\d{1,2})?)(?:\s*(?:USD|dollars?))?"
          r"|(?P<num>\d[\d,]*(?:\.\d{1,2})?)\s*(?:USD|dollars?))")

#: The basis vocabulary, longest first so "per pet per night" wins over
#: "per night". Each is a DIFFERENT policy: a second dog doubles some and not
#: others, so the dimensions are preserved exactly as written.
_BASIS_ALT = (r"per\s+pet\s+per\s+night|per\s+night\s+per\s+pet"
              r"|per\s+pet\s+per\s+stay|per\s+stay\s+per\s+pet"
              r"|per\s+night|per\s+stay|per\s+pet")

_BASIS_CANON = {
    "per night per pet": "per pet per night",
    "per stay per pet": "per pet per stay",
}

#: Obligations that are not ordinary pet fees. A segment carrying one of these
#: is skipped entirely -- a $500 penalty for an unregistered animal is not the
#: price of bringing a registered one.
_DISQUALIFIER_RE = re.compile(
    r"penalt(?:y|ies)|\bfines?\b|\bfined\b|deposit|damages?|cleaning\s+fee"
    r"|incidental|forfeit|replacement|smoking\s+fee|unregistered|violation",
    re.I)

_PET_NOUN_RE = re.compile(r"\b(?:" + _PET_NOUNS + r")\b", re.I)

#: How far either side of a fee an animal may be named. Wide enough for the line
#: above in a table, narrow enough that a resort fee elsewhere in the block
#: cannot borrow the word "pets" from the policy heading.
_PET_CONTEXT_WINDOW = 130

# --------------------------------------------------------------------------- #
# 1. Amount before the label.
# --------------------------------------------------------------------------- #

#: "$50 USD pet fee ...". The label names the animal, so this needs no further
#: pet context.
_AMOUNT_THEN_PET_FEE = re.compile(
    _MONEY + r"\s+(?:non-?refundable\s+)?pets?\s+fee\b", re.I)

#: "$150 non-refundable fee." -- the label does NOT name an animal, so a pet
#: noun must appear nearby or this is some other property's charge.
_AMOUNT_THEN_NONREFUNDABLE_FEE = re.compile(
    _MONEY + r"\s+non-?refundable\s+fee\b", re.I)

#: Filler permitted between the label and its basis: "will apply", "applies",
#: "is charged". Letters and spaces only, so a sentence boundary stops it and
#: "$150 non-refundable fee. Maximum Pet Weight" cannot acquire a basis.
_TRAILING_BASIS = re.compile(
    r"^[a-z\s]{0,18}?(?P<basis>" + _BASIS_ALT + r")\b", re.I)

# --------------------------------------------------------------------------- #
# 2. Basis interposed in a labelled field.
# --------------------------------------------------------------------------- #

#: "Pet fee per night: 30 USD", "Pet fee per pet per night: 25 USD".
_LABEL_BASIS_AMOUNT = re.compile(
    r"pets?\s+fee\s+(?P<basis>" + _BASIS_ALT + r")\s*:?\s*" + _MONEY, re.I)

# --------------------------------------------------------------------------- #
# 3. Result type.
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class StatedFee:
    """One fee amount, with the basis the source gave it and nothing more."""

    amount: str            # normalised, two decimals
    basis: str             # "" when the source stated none
    quote: str
    rule: str

    def to_dict(self) -> dict:
        out = {"amount": self.amount, "currency": "USD",
               "evidence_quote": self.quote}
        if self.basis:
            out["basis"] = self.basis
        return out


@dataclass(frozen=True)
class FeeContradiction:
    """Two incompatible fee terms in one official source. Neither is chosen."""

    ladder_quote: str
    rate_quote: str
    detail: str


# --------------------------------------------------------------------------- #
# 4. Helpers.
# --------------------------------------------------------------------------- #

def _normalise(match: "re.Match") -> Optional[str]:
    token = match.group("sym") or match.group("num") or ""
    try:
        return "%.2f" % Decimal(token.replace(",", "").strip())
    except (InvalidOperation, ArithmeticError, ValueError):
        return None


def _segments(block: str) -> List[Tuple[int, str]]:
    """Sentence-ish spans with their offsets, for disqualifier scoping."""
    text = " ".join((block or "").split())
    out, start = [], 0
    for m in re.finditer(r"[.!?](?:\s+|$)", text):
        out.append((start, text[start:m.end()]))
        start = m.end()
    if start < len(text):
        out.append((start, text[start:]))
    return out


def _segment_for(block_norm: str, index: int) -> str:
    for start, seg in _segments(block_norm):
        if start <= index < start + len(seg):
            return seg
    return block_norm


def _canon_basis(raw: str) -> str:
    value = " ".join((raw or "").lower().split())
    return _BASIS_CANON.get(value, value)


def _quote(text: str, start: int, end: int, pad: int = 0) -> str:
    lo, hi = max(0, start - pad), min(len(text), end + pad)
    return " ".join(text[lo:hi].split())


# --------------------------------------------------------------------------- #
# 5. Readers.
# --------------------------------------------------------------------------- #

def amount_before_label(block: str) -> Optional[StatedFee]:
    """A fee written amount-first, or None.

    Basis is read only from what follows the label, and only through filler that
    cannot cross a sentence boundary.
    """
    text = " ".join((block or "").split())
    for rx, rule, needs_pet_noun in (
            (_AMOUNT_THEN_PET_FEE, "amount_before_pet_fee_label", False),
            (_AMOUNT_THEN_NONREFUNDABLE_FEE, "amount_before_nonrefundable_fee_label", True)):
        for m in rx.finditer(text):
            segment = _segment_for(text, m.start())
            if _DISQUALIFIER_RE.search(segment):
                continue
            # The pet noun is looked for in a WINDOW, not the sentence: a table
            # commonly gives the fee its own line -- "Dogs and 20-lb. cats. $150
            # non-refundable fee." -- and the animal it belongs to is in the
            # line above. The disqualifier check stays sentence-scoped, so a
            # neighbouring deposit still cannot lend this amount its context.
            if needs_pet_noun and not _PET_NOUN_RE.search(
                    text[max(0, m.start() - _PET_CONTEXT_WINDOW):
                         m.end() + _PET_CONTEXT_WINDOW]):
                continue
            amount = _normalise(m)
            if amount is None:
                continue
            tail = _TRAILING_BASIS.match(text[m.end():m.end() + 40])
            basis = _canon_basis(tail.group("basis")) if tail else ""
            end = m.end() + (tail.end() if tail else 0)
            return StatedFee(amount, basis, _quote(text, m.start(), end), rule)
    return None


def labelled_basis_amount(block: str) -> Optional[StatedFee]:
    """"Pet fee per night: 30 USD" -- the basis sits inside the label."""
    text = " ".join((block or "").split())
    for m in _LABEL_BASIS_AMOUNT.finditer(text):
        segment = _segment_for(text, m.start())
        if _DISQUALIFIER_RE.search(segment):
            continue
        amount = _normalise(m)
        if amount is None:
            continue
        return StatedFee(amount, _canon_basis(m.group("basis")),
                         _quote(text, m.start(), m.end()),
                         "labelled_fee_with_interposed_basis")
    return None


#: Cap clauses are removed before recurrence is judged: "up to a maximum of $75
#: per stay" bounds a nightly rate rather than competing with it.
_CAP_CLAUSE_RE = re.compile(
    r"(?:max(?:imum)?|cap(?:ped)?|not\s+to\s+exceed|up\s+to)\b[^.]{0,40}", re.I)

_ONE_TIME_RE = re.compile(
    r"\bone[-\s]?time\b|\bper\s+stay\b|\bsingle\s+charge\b|\bflat\s+fee\b", re.I)
_NIGHTLY_RE = re.compile(r"\bper\s+night\b|\bnightly\b|\beach\s+night\b", re.I)


def competing_recurrence(block: str) -> bool:
    """Does the block assert BOTH a one-time and a nightly fee basis?

    One property states "There is a 75 USD, one time pet fee" and, further down,
    "Pet fee per night: 75 USD". A five-night stay costs $75 under the first and
    $375 under the second. Reading either basis as fact invents the difference,
    so neither new reader answers for such a block at all -- which leaves the
    property exactly as it already was: an amount, with the basis not stated.
    """
    stripped = _CAP_CLAUSE_RE.sub(" ", " ".join((block or "").split()))
    return bool(_ONE_TIME_RE.search(stripped)) and bool(_NIGHTLY_RE.search(stripped))


def stated_fee(block: str) -> Optional[StatedFee]:
    """The first of the two new forms that reads, or None.

    The interposed-basis form is tried first: it states its basis explicitly and
    unambiguously, where the amount-first form has to reach past filler for one.
    """
    if competing_recurrence(block):
        return None
    return labelled_basis_amount(block) or amount_before_label(block)


# --------------------------------------------------------------------------- #
# 6. The contradiction.
# --------------------------------------------------------------------------- #

def _ladder_quote(block: str) -> str:
    """The segment stating a stay-length ladder, or ""."""
    from scripts.pettripfinder.prose_facts import _FEE_AMOUNT_RE, _STAY_CONDITION_RE
    for _start, seg in _segments(" ".join((block or "").split())):
        if not _STAY_CONDITION_RE.search(seg):
            continue
        amounts = {(m.group(1) or m.group(2) or "").replace(",", "")
                   for m in _FEE_AMOUNT_RE.finditer(seg)}
        amounts.discard("")
        if len(amounts) >= 2:
            return seg.strip()
    return ""


def fee_contradiction(block: str) -> Optional[FeeContradiction]:
    """A stay-length ladder stated beside a flat recurring rate, or None.

    Both are the property's own words and they price the same stay differently.
    Nothing here decides between them: the caller withholds the fee and keeps
    both quotations.
    """
    if not is_stay_conditional_multi_amount(block):
        return None
    ladder = _ladder_quote(block)
    if not ladder:
        return None
    rate = labelled_basis_amount(block)
    if rate is None:
        candidate = amount_before_label(block)
        rate = candidate if (candidate and candidate.basis) else None
    if rate is None or rate.quote in ladder:
        return None
    return FeeContradiction(ladder_quote=ladder, rate_quote=rate.quote,
                            detail="stay_length_ladder_conflicts_with_flat_rate")


# --------------------------------------------------------------------------- #
# 7. Ordinal pet schedules, and one more contradiction shape.
# --------------------------------------------------------------------------- #

#: "$80 for first pet and $50 for second pet". A second animal costs a different
#: amount from the first, so a single number cannot describe the policy: a
#: two-pet stay at this property is $130, not $80.
_ORDINAL_PET_FEE_RE = re.compile(
    _MONEY + r"\s+for\s+(?:the\s+|each\s+)?"
    r"(?P<ord>first|1st|second|2nd|additional|extra)\s+"
    r"(?:pet|animal|dog|cat)\b", re.I)

_ORDINAL_CANON = {"first": "first_pet", "1st": "first_pet",
                  "second": "second_pet", "2nd": "second_pet",
                  "additional": "additional_pet", "extra": "additional_pet"}


@dataclass(frozen=True)
class OrdinalPetFees:
    """What each successive animal costs, kept apart."""

    fees: Tuple[Tuple[str, StatedFee], ...]
    quote: str

    def to_dict(self) -> Dict[str, object]:
        out: Dict[str, object] = {"evidence_quote": self.quote}
        for name, fee in self.fees:
            out[name] = fee.to_dict()
        return out


def ordinal_pet_fees(block: str) -> Optional[OrdinalPetFees]:
    """A per-animal fee ladder, or None.

    The basis is read from the clause, not from each amount: a source writes
    "$80 for first pet and $50 for second pet per stay" once, and the trailing
    "per stay" governs both. It is applied only when the whole list sits in ONE
    sentence and that sentence states exactly one basis -- otherwise no basis is
    asserted at all.
    """
    text = " ".join((block or "").split())
    for sentence in _segments(text):
        seg = sentence[1]
        if _DISQUALIFIER_RE.search(seg):
            continue
        found = []
        for m in _ORDINAL_PET_FEE_RE.finditer(seg):
            amount = _normalise(m)
            if amount is None:
                continue
            name = _ORDINAL_CANON[m.group("ord").lower()]
            found.append((name, m, amount))
        if len(found) < 2:
            continue
        bases = {_canon_basis(b) for b in
                 re.findall(r"\b(" + _BASIS_ALT + r")\b", seg, re.I)}
        basis = bases.pop() if len(bases) == 1 else ""
        fees = tuple((name, StatedFee(amount, basis,
                                      _quote(seg, m.start(), m.end()),
                                      "ordinal_pet_fee"))
                     for name, m, amount in found)
        if len({n for n, _f in fees}) != len(fees):
            return None                      # the same rung named twice
        return OrdinalPetFees(fees=fees, quote=seg.strip())
    return None


#: A per-stay fee that is NOT a ceiling. "max $300 per stay" bounds a nightly
#: rate; "Per Stay: $100.00" competes with it.
_PER_STAY_SCALAR_RE = re.compile(
    r"(?<!max )(?<!maximum )pet\s+fee\s+per\s+stay\s*:?\s*" + _MONEY, re.I)
_NIGHTLY_FEE_RE = re.compile(
    _MONEY + r"[^.$]{0,40}?\bper\s+night\b", re.I)

#: A ceiling word immediately before an amount. A capped total is not a second
#: fee competing with the rate it bounds.
_CAP_BEFORE_RE = re.compile(
    r"(?:max(?:imum)?|cap(?:ped)?|not\s+to\s+exceed|up\s+to)"
    r"(?:\s+(?:of|at))?\s*(?:a\s+)?$", re.I)


def nightly_versus_per_stay_conflict(block: str) -> Optional[FeeContradiction]:
    """A nightly fee stated beside an unrelated per-stay fee, or None.

    One property says "$50 nonrefundable pet fee per night; max $300 per stay"
    and, further down, "Non-Refundable Pet Fee Per Stay: $100.00". Four nights
    costs $200 under the first and $100 under the second. The ceiling belongs to
    the nightly statement, so pairing it with the per-stay scalar would publish a
    total neither sentence supports. Nothing here chooses.
    """
    text = " ".join((block or "").split())
    nightly = None
    for m in _NIGHTLY_FEE_RE.finditer(text):
        if _DISQUALIFIER_RE.search(_segment_for(text, m.start())):
            continue
        if _CAP_BEFORE_RE.search(text[max(0, m.start() - 40):m.start()]):
            continue
        nightly = (_normalise(m), _quote(text, m.start(), m.end()))
        break
    if not nightly or nightly[0] is None:
        return None
    per_stay = None
    for m in _PER_STAY_SCALAR_RE.finditer(text):
        if _DISQUALIFIER_RE.search(_segment_for(text, m.start())):
            continue
        per_stay = (_normalise(m), _quote(text, m.start(), m.end()))
        break
    if not per_stay or per_stay[0] is None or per_stay[0] == nightly[0]:
        return None
    return FeeContradiction(ladder_quote=nightly[1], rate_quote=per_stay[1],
                            detail="nightly_fee_conflicts_with_per_stay_fee")


# --------------------------------------------------------------------------- #
# 8. What a ceiling applies to.
# --------------------------------------------------------------------------- #

#: "Maximum of $150 per stay for two (2) pets". The ceiling is qualified: it is
#: the most two animals can cost, and the source says nothing about what one
#: animal costs. Recording the qualifier verbatim keeps the caller from turning
#: a two-pet ceiling into a per-pet charge, or from claiming a different ceiling
#: for a single pet.
_CAP_QUALIFIER_RE = re.compile(
    r"for\s+(?:up\s+to\s+)?(?:\d+|one|two|three|four)\s*(?:\(\s*\d+\s*\))?\s*"
    r"(?:pets?|animals?|dogs?|cats?)\b", re.I)


def cap_qualifier(block: str, cap_amount: str) -> str:
    """The verbatim clause qualifying a stated ceiling, or "".

    Read from the text immediately AFTER the ceiling amount, so a qualifier
    belonging to some other sentence cannot attach itself to this one.
    """
    text = " ".join((block or "").split())
    if not cap_amount:
        return ""
    bare = cap_amount.rstrip("0").rstrip(".") if "." in cap_amount else cap_amount
    for token in (cap_amount, bare):
        for m in re.finditer(re.escape(token), text):
            # Bounded to the same clause: the qualifier may sit after the basis
            # ("per stay for two (2) pets"), but never past the sentence end.
            tail = text[m.end():m.end() + 48].split(".")[0]
            found = _CAP_QUALIFIER_RE.search(tail)
            if found:
                return " ".join(found.group(0).split())
    return ""


# --------------------------------------------------------------------------- #
# 9. Pet deposits, basis recovery, and the recurrence contradiction.
# --------------------------------------------------------------------------- #

#: A deposit the source explicitly calls a PET deposit. Distinct from an
#: incidentals deposit, which is not a pet-related charge and must stay out of
#: pet facts, and distinct from the pet FEE, which is not refundable.
_PET_DEPOSIT_AFTER = re.compile(
    r"pets?\s+deposit\s*(?:is|of|are|:)?\s*" + _MONEY, re.I)
_PET_DEPOSIT_BEFORE = re.compile(
    _MONEY + r"\s+(?:refundable\s+)?pets?\s+deposit\b", re.I)

#: Charges that are conditional or purpose-specific. A sanitation fee "if
#: required" is not the price of bringing an animal.
_CONDITIONAL_FEE_RE = re.compile(
    r"sanitation|cleaning|damage|if\s+required|if\s+needed|as\s+needed", re.I)

#: A basis sitting immediately after an amount, with no filler at all. Stricter
#: than ``_TRAILING_BASIS``: this recovers a recurrence for an amount already
#: captured elsewhere, so it must not reach across words to find one.
_TRAILING_BASIS_ONLY = re.compile(
    r"^\s*(?P<basis>" + _BASIS_ALT + r")\b", re.I)


def pet_deposit(block: str) -> Optional[StatedFee]:
    """A deposit the source names as a PET deposit, or None.

    Requires the word "pet" beside "deposit". An incidentals deposit stays out:
    the source has not called it pet-related, and inferring that it is would
    invent a charge the guest may never face.
    """
    text = " ".join((block or "").split())
    for rx, rule in ((_PET_DEPOSIT_AFTER, "pet_deposit_label_first"),
                     (_PET_DEPOSIT_BEFORE, "pet_deposit_amount_first")):
        for m in rx.finditer(text):
            amount = _normalise(m)
            if amount is None:
                continue
            return StatedFee(amount, "", _quote(text, m.start(), m.end()), rule)
    return None


def basis_for_amount(block: str, amount: str) -> Tuple[str, str]:
    """``(basis, quote)`` for a basis stated beside THIS amount, or ``("", "")``.

    Recovers a recurrence the first reader missed because it captured the amount
    from a different row -- a labelled deposit row, say -- while the basis sits
    beside the same figure further along ("Other pet information $75 per stay").
    The amounts must match exactly, so no other charge's recurrence can attach.
    """
    text = " ".join((block or "").split())
    if not amount:
        return ("", "")
    bare = amount.rstrip("0").rstrip(".") if "." in amount else amount
    for token in (amount, bare):
        for m in re.finditer(r"\$?\s*" + re.escape(token) + r"(?![\d.])", text):
            seg = _segment_for(text, m.start())
            if _CONDITIONAL_FEE_RE.search(seg) or _DISQUALIFIER_RE.search(seg):
                continue
            tail = text[m.end():m.end() + 26]
            found = _TRAILING_BASIS_ONLY.match(tail)
            if found:
                return (_canon_basis(found.group("basis")),
                        _quote(text, m.start(), m.end() + found.end()))
    return ("", "")


#: An explicit statement that ONE charge covers the room, however many animals
#: occupy it. Both forms bind the scope to the FEE, which is the whole point:
#: "per room" on its own is far more often a count qualifier -- "max 2 pets per
#: room" says nothing about how the fee is charged, and reading it as a fee
#: scope would put words in the hotel's mouth on most of this corpus.
_ROOM_SCOPE_RE = re.compile(
    r"per\s+room\s+with\b[^.]{0,40}?\bfee\b"
    r"|(?:for|covers)\s+up\s+to\s+\d{1,2}\s+(?:" + _PET_NOUNS + r")\b",
    re.I)

#: A source that says "per pet per room" has stated BOTH scopes. Choosing one
#: would be this reader's choice, not the hotel's, so it declines to choose.
_COMPETING_PET_SCOPE_RE = re.compile(r"per\s+pet\s+per\s+room\b", re.I)


def room_scope_for_amount(block: str, amount: str) -> Tuple[str, str]:
    """``("per_room", quote)`` when THIS amount is stated to cover the room.

    A pet fee is silent about its own scope far more often than not, and that
    silence must survive: a guest booking two animals reads an unscoped fee at
    their own risk either way, but a fee this reader *invented* a scope for
    would be worse than the silence it replaced. So the phrase must sit in the
    same clause as the amount, and the amounts must match exactly -- a room
    scope stated about some neighbouring charge cannot travel to this one.

    Returns ``("", "")`` when the source does not say. There is deliberately no
    ``per_pet`` return: nothing in the corpus states it about a scalar fee, and
    a scope this function guessed would be indistinguishable from one it read.
    """
    text = " ".join((block or "").split())
    if not amount:
        return ("", "")
    bare = amount.rstrip("0").rstrip(".") if "." in amount else amount
    for token in (amount, bare):
        for m in re.finditer(r"\$?\s*" + re.escape(token) + r"(?![\d.])", text):
            seg = _segment_for(text, m.start())
            if _DISQUALIFIER_RE.search(seg) or _COMPETING_PET_SCOPE_RE.search(seg):
                continue
            found = _ROOM_SCOPE_RE.search(seg)
            if found:
                return ("per_room",
                        _quote(seg, found.start(), found.end(), pad=30))
    return ("", "")


#: The two halves of a recurrence contradiction.
#: Bounded on BOTH sides. A run to the next full stop is not a quotation when
#: the source omits one -- it swallows the rest of the card and hands a reviewer
#: a paragraph where a clause was meant.
_ONE_TIME_STATEMENT_RE = re.compile(
    r"[^.]{0,60}\b(?:one[-\s]?time|single\s+charge|flat\s+fee)\b[^.]{0,20}", re.I)
_NIGHTLY_STATEMENT_RE = re.compile(
    r"[^.]{0,40}\b(?:per\s+night|nightly|each\s+night)\b"
    r"(?:\s*:?\s*\$?\s*\d[\d,]*(?:\.\d{1,2})?\s*(?:USD|dollars?)?)?", re.I)


def recurrence_conflict(block: str) -> Optional[FeeContradiction]:
    """A source that calls the same fee both one-time and nightly, or None.

    "There is a 75 USD, one time pet fee" beside "Pet fee per night: 75 USD"
    prices a five-night stay at $75 or $375. The amounts agreeing does not make
    the terms agree -- it is the RECURRENCE that decides the bill, and the source
    states two. Publishing the amount with a silent basis would let a reader
    assume the cheaper reading.
    """
    text = " ".join((block or "").split())
    if not competing_recurrence(text):
        return None
    stripped = _CAP_CLAUSE_RE.sub(" ", text)
    one = _ONE_TIME_STATEMENT_RE.search(stripped)
    nightly = _NIGHTLY_STATEMENT_RE.search(stripped)
    if not one or not nightly:
        return None
    one_q, night_q = " ".join(one.group(0).split()), " ".join(nightly.group(0).split())
    if one_q == night_q:
        return None
    return FeeContradiction(ladder_quote=one_q, rate_quote=night_q,
                            detail="one_time_fee_conflicts_with_nightly_fee")
