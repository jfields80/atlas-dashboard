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
