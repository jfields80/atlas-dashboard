"""PTF-FEES-PROSE -- read a pet-fee SCHEDULE stated in ordinary prose.

The label-driven promoter reads "Non-Refundable Pet Fee Per Night: $75.00", and
``prose_facts.extract_fee_with_basis`` reads a single amount written as a
sentence. Neither can read a fee that has more than one DIMENSION:

    "Nonrefundable pet fee of 25 dollars per night with a maximum of 75 dollars
     for stays 1 to 6 nights and 150 dollars for 7 or more nights."

    "Pets ... are allowed for a non-refundable fee of 45 USD for the 1st night
     and 10 USD for each additional night to a maximum of 180USD per stay."

Both are stated plainly by the official source and both were unreadable. Worse,
the second is actively dangerous to the scalar reader: it sees "45 USD" first
and would publish $45 as *the* pet fee, when $45 buys one night and a five-night
stay costs $85. Flattening a schedule into a single number is the specific error
this module exists to prevent, so a schedule found here SUPPRESSES the scalar
reader rather than competing with it.

The dimensions are kept apart because they are different promises:

    rate              what each night (or the stay) costs
    first_night       what the first night costs, when it differs
    additional_night  what every night after the first costs
    cap               a stated ceiling on the total
    cap_tiers         a ceiling that itself varies with stay length

A caller cannot take one without the others: they arrive in one object or not
at all.

Timidity rules, in the same spirit as ``prose_facts``:

  * a number is invisible unless it carries EXPLICIT currency -- "$", "USD",
    "dollar" or "dollars". "a 500.00 penalty" and "40 lbs" are not amounts here;
  * an amount is invisible unless an explicit fee PHRASE classifies it -- "per
    night", "per stay", "for the first night", "for each additional night", or a
    stay-length range. A bare amount is never assigned a meaning;
  * a sentence naming a penalty, deposit, damage, cleaning or incidental charge
    contributes NOTHING, even if it also says "fee". Those are different
    obligations and are not pet fees;
  * a sentence that is only partly understood -- some amounts classified, one
    not -- is refused outright. A half-read schedule is not a schedule;
  * two sentences that disagree about the same dimension refuse. Nothing picks
    a winner;
  * a fee asserted with no amount produces nothing, which leaves the promoter
    exactly as refused as it already was.

Nothing here names a brand, a property, a hotel id, a property code or a URL.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Dict, List, Optional, Tuple

# The pet-noun vocabulary is shared deliberately rather than restated here: two
# copies of it would drift, and a fee reader that recognises fewer animals than
# the count reader would refuse policies its sibling accepts.
from scripts.pettripfinder.prose_facts import WORD_NUMBERS, _PET_NOUNS

# --------------------------------------------------------------------------- #
# 1. Vocabulary.
# --------------------------------------------------------------------------- #

_WORD_NUM_ALT = "|".join(sorted(WORD_NUMBERS, key=len, reverse=True))

#: Currency is MANDATORY. This is the single guard that makes "a 500.00
#: penalty", a room number, a weight and a year all unreadable as money.
_CURRENCY_WORD = r"(?:USD|usd|dollars?|DOLLARS?)"
_NUMERAL = r"\d[\d,]*(?:\.\d{1,2})?"
_AMOUNT_RE = re.compile(
    r"\$\s*(?P<sym>" + _NUMERAL + r")"
    r"|(?P<num>" + _NUMERAL + r")\s*" + _CURRENCY_WORD + r"\b"
    r"|\b(?P<word>" + _WORD_NUM_ALT + r")\s+" + _CURRENCY_WORD + r"\b",
    re.I)

#: The sentence must say it is talking about a fee. Requiring this -- rather
#: than trusting the enclosing block -- is what keeps a resort fee or a parking
#: charge that happens to sit in a pet card from being read as a pet fee.
_FEE_CONTEXT_RE = re.compile(
    r"pet\s+fee|non[-\s]?refundable\s+fee|nonrefundable\s+(?:pet\s+)?fee"
    r"|fee\s+of\b|per\s+night|per\s+stay|first\s+night|1st\s+night"
    r"|additional\s+night|extra\s+night", re.I)

#: ... and it must be about ANIMALS. Belt and braces over the pet-scoped block.
_PET_NOUN_RE = re.compile(r"\b(?:" + _PET_NOUNS + r")\b", re.I)

#: Words that make a word-number the TAIL of a compound. The shared list runs
#: one to ten, so "twenty five dollars" matches only on "five" and would be read
#: as $5 -- a fee understated fivefold, silently. A compound is refused instead:
#: there is no general numeral parser here to be surprised by, and money is the
#: last field to start guessing at.
_COMPOUND_NUMBER_BEFORE_RE = re.compile(
    r"\b(?:twenty|thirty|forty|fourty|fifty|sixty|seventy|eighty|ninety"
    r"|hundred|thousand|" + _WORD_NUM_ALT + r")[\s-]+$", re.I)

#: Obligations that are not ordinary pet fees. A sentence carrying any of these
#: contributes nothing at all -- the amounts in it are not this module's to read.
_DISQUALIFIER_RE = re.compile(
    r"penalt(?:y|ies)|\bfines?\b|\bfined\b|deposit|damages?|cleaning\s+fee"
    r"|incidental|forfeit|replacement|smoking\s+fee|unregistered|violation",
    re.I)

# --------------------------------------------------------------------------- #
# 2. Classifying phrases, matched against the text immediately around an amount.
# --------------------------------------------------------------------------- #

#: A ceiling marker sitting immediately BEFORE the amount.
_CAP_PREFIX_RE = re.compile(
    r"(?:max(?:imum)?|cap(?:ped)?|ceiling|not\s+to\s+exceed|no\s+more\s+than)"
    r"(?:\s+(?:of|at|is|being))?\s*(?:a\s+)?$", re.I)

_FIRST_NIGHT_RE = re.compile(
    r"^\s*(?:for|on)\s+(?:the\s+)?(?:first|1st)\s+night", re.I)
_ADDITIONAL_NIGHT_RE = re.compile(
    r"^\s*(?:for|per)\s+(?:each|every|any|the)?\s*"
    r"(?:additional|extra|subsequent|thereafter)\s+night", re.I)
#: "stays 1 to 6 nights", "1-6 nights", "stays of 1 through 6 nights"
_TIER_RANGE_RE = re.compile(
    r"^\s*(?:for\s+)?(?:stays?\s+)?(?:of\s+)?(\d+)\s*(?:to|through|[-–—])\s*"
    r"(\d+)\s*nights?", re.I)
#: "7 or more nights", "7+ nights", "7 or longer"
_TIER_OPEN_RE = re.compile(
    r"^\s*(?:for\s+)?(?:stays?\s+)?(?:of\s+)?(\d+)\s*"
    r"(?:\+|or\s+(?:more|longer|greater))\s*(?:nights?)?", re.I)

#: Recurrence basis. Normalised so "a night" and "nightly" are one value.
_BASIS_PATTERNS = (
    (re.compile(r"^\s*per\s+pet\s+per\s+night", re.I), "per pet per night"),
    (re.compile(r"^\s*per\s+night\s+per\s+pet", re.I), "per pet per night"),
    (re.compile(r"^\s*per\s+pet\s+per\s+stay", re.I), "per pet per stay"),
    (re.compile(r"^\s*per\s+stay\s+per\s+pet", re.I), "per pet per stay"),
    (re.compile(r"^\s*(?:per|each|a)\s+night", re.I), "per night"),
    (re.compile(r"^\s*nightly", re.I), "per night"),
    (re.compile(r"^\s*(?:per|the\s+entire|for\s+the)\s+stay", re.I), "per stay"),
    (re.compile(r"^\s*per\s+pet\b", re.I), "per pet"),
)

#: How far either side of an amount a classifying phrase may sit.
_LOOKBEHIND = 44
_LOOKAHEAD = 60

# Roles an amount can be given.
_ROLE_RATE = "rate"
_ROLE_FIRST = "first_night"
_ROLE_ADDITIONAL = "additional_night"
_ROLE_CAP = "cap"
_ROLE_CAP_TIER = "cap_tier"


# --------------------------------------------------------------------------- #
# 3. Result types.
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class FeeAmount:
    """One stated money value, with the basis the source gave it."""

    amount: str                 # normalised, always two decimals
    basis: str                  # "" when the source did not state one
    quote: str

    def to_dict(self) -> Dict[str, str]:
        d = {"amount": self.amount, "currency": "USD", "evidence_quote": self.quote}
        if self.basis:
            d["basis"] = self.basis
        return d


@dataclass(frozen=True)
class CapTier:
    """A ceiling that applies only to stays of a given length."""

    amount: str
    min_nights: int
    max_nights: Optional[int]   # None means "and longer"
    quote: str

    def to_dict(self) -> Dict[str, object]:
        return {"amount": self.amount, "currency": "USD",
                "min_nights": self.min_nights,
                "max_nights": self.max_nights if self.max_nights else "",
                "evidence_quote": self.quote}


@dataclass(frozen=True)
class ProseFeeSchedule:
    """Every fee dimension one official sentence stated, kept apart."""

    rate: Optional[FeeAmount] = None
    first_night: Optional[FeeAmount] = None
    additional_night: Optional[FeeAmount] = None
    cap: Optional[FeeAmount] = None
    cap_tiers: Tuple[CapTier, ...] = ()
    quote: str = ""

    @property
    def is_staged(self) -> bool:
        """True when the nightly price CHANGES across the stay.

        A staged schedule has no single "the fee", so the scalar readers must
        stand down rather than publish its first number.
        """
        return bool(self.first_night or self.additional_night)


# --------------------------------------------------------------------------- #
# 4. Parsing.
# --------------------------------------------------------------------------- #

def _normalise(token: str) -> Optional[str]:
    """A money token as a fixed two-decimal string, or None if unreadable."""
    word = WORD_NUMBERS.get(token.strip().lower())
    if word is not None:
        return "%.2f" % word
    try:
        return "%.2f" % Decimal(token.replace(",", "").strip())
    except (InvalidOperation, ArithmeticError, ValueError):
        return None


def _sentences(block: str) -> List[str]:
    """Split on sentence terminators. Offsets are not needed downstream."""
    text = " ".join((block or "").split())
    return [s for s in re.split(r"(?<=[.!?])\s+", text) if s.strip()]


def _classify(sentence: str, match: "re.Match", cap_open: bool
              ) -> Tuple[str, str, Optional[Tuple[int, Optional[int]]]]:
    """Return ``(role, basis, nights)`` for one amount, or ``("", "", None)``.

    ``nights`` is the stay-length window a cap tier applies to. An empty role
    means the phrasing around the amount did not say what the amount IS, and the
    caller must refuse rather than assume.
    """
    before = sentence[max(0, match.start() - _LOOKBEHIND):match.start()]
    after = sentence[match.end():match.end() + _LOOKAHEAD]

    if _CAP_PREFIX_RE.search(before):
        # A ceiling may itself be tiered: "maximum of 75 dollars for stays 1 to
        # 6 nights". The stay window travels with it.
        window = _tier_window(after)
        if window:
            return (_ROLE_CAP_TIER, "", window)
        return (_ROLE_CAP, _basis(after), None)

    if _FIRST_NIGHT_RE.match(after):
        return (_ROLE_FIRST, "first night", None)
    if _ADDITIONAL_NIGHT_RE.match(after):
        return (_ROLE_ADDITIONAL, "each additional night", None)

    window = _tier_window(after)
    if window:
        # "and 150 dollars for 7 or more nights" continues a ceiling ladder that
        # a previous amount opened. With no ceiling word anywhere this is a
        # tiered FEE, which this module cannot represent -- refuse, do not guess.
        if cap_open:
            return (_ROLE_CAP_TIER, "", window)
        return ("", "", None)

    basis = _basis(after)
    if basis:
        return (_ROLE_RATE, basis, None)
    return ("", "", None)


def _tier_window(after: str) -> Optional[Tuple[int, Optional[int]]]:
    m = _TIER_RANGE_RE.match(after)
    if m:
        low, high = int(m.group(1)), int(m.group(2))
        return (low, high) if low <= high else None
    m = _TIER_OPEN_RE.match(after)
    if m:
        return (int(m.group(1)), None)
    return None


def _basis(after: str) -> str:
    for rx, value in _BASIS_PATTERNS:
        if rx.match(after):
            return value
    return ""


def _quote(sentence: str, match: "re.Match") -> str:
    """The source span around an amount, snapped to whole words.

    A quotation is shown to a reader as the property's own words, so it must not
    begin mid-word: "ach are allowed for a non-refundable fee of 45 USD" is the
    right span and the wrong quotation.
    """
    start = max(0, match.start() - _LOOKBEHIND)
    if start:
        space = sentence.find(" ", start)
        start = space + 1 if 0 <= space < match.start() else start
    end = min(len(sentence), match.end() + _LOOKAHEAD)
    if end < len(sentence):
        space = sentence.rfind(" ", match.end(), end)
        end = space if space > match.end() else end
    return " ".join(sentence[start:end].split())


def parse_prose_fee_schedule(block: str) -> Optional[ProseFeeSchedule]:
    """Read a multi-dimension pet fee out of ``block``, or return None.

    None is the normal, safe answer: it leaves every existing reader and every
    existing refusal exactly as it was.
    """
    rate = first = additional = cap = None
    cap_tiers: List[CapTier] = []
    used: List[str] = []

    for sentence in _sentences(block):
        if _DISQUALIFIER_RE.search(sentence):
            continue
        if not _FEE_CONTEXT_RE.search(sentence) or not _PET_NOUN_RE.search(sentence):
            continue

        matches = list(_AMOUNT_RE.finditer(sentence))
        if not matches:
            continue

        cap_open = False
        found: List[Tuple[str, FeeAmount, Optional[Tuple[int, Optional[int]]]]] = []
        unreadable = False
        for m in matches:
            amount = _normalise(m.group("sym") or m.group("num") or m.group("word") or "")
            if amount is None or (m.group("word")
                                  and _COMPOUND_NUMBER_BEFORE_RE.search(
                                      sentence[:m.start()])):
                unreadable = True
                break
            role, basis, nights = _classify(sentence, m, cap_open)
            if not role:
                unreadable = True
                break
            if role in (_ROLE_CAP, _ROLE_CAP_TIER):
                cap_open = True
            found.append((role, FeeAmount(amount, basis, _quote(sentence, m)), nights))

        # A sentence understood only in part is not a fee to publish. Skipping
        # the unreadable amount and keeping the rest is precisely how a ceiling
        # gets published as a rate.
        if unreadable and found:
            return None
        # Nothing classified at all: not a fee sentence. Leave it alone -- a
        # labelled row like "Pet fee per night: 25 USD" is another reader's job.
        if not found:
            continue

        for role, value, nights in found:
            if role == _ROLE_RATE:
                if rate and rate.amount != value.amount:
                    return None
                rate = rate or value
            elif role == _ROLE_FIRST:
                if first and first.amount != value.amount:
                    return None
                first = first or value
            elif role == _ROLE_ADDITIONAL:
                if additional and additional.amount != value.amount:
                    return None
                additional = additional or value
            elif role == _ROLE_CAP:
                if cap and cap.amount != value.amount:
                    return None
                cap = cap or value
            elif role == _ROLE_CAP_TIER and nights:
                cap_tiers.append(CapTier(value.amount, nights[0], nights[1], value.quote))
        used.append(sentence)

    # A ceiling with nothing to ceiling is not a fee. So is a schedule with no
    # money in it at all -- which is what "there is a pet fee" alone amounts to.
    if not rate and not first and not additional:
        return None
    # A first-night price with no follow-on price, or the reverse, is half a
    # schedule. Publishing half of one misstates every stay but the first night.
    if bool(first) != bool(additional):
        return None
    if cap_tiers:
        windows = [(t.min_nights, t.max_nights) for t in cap_tiers]
        if len(set(windows)) != len(windows):
            return None
        cap_tiers.sort(key=lambda t: t.min_nights)

    # This module answers ONLY for the two shapes the existing readers cannot
    # represent: a fee staged across the stay, and a ceiling that varies with
    # stay length. A plain "50 USD per stay", with or without a flat ceiling, is
    # already read correctly by ``prose_facts`` -- answering for it as well
    # would change the evidence quotation on hotels that publish today, for no
    # gain in what is known about them.
    if not (first or additional or cap_tiers):
        return None

    return ProseFeeSchedule(rate=rate, first_night=first, additional_night=additional,
                            cap=cap, cap_tiers=tuple(cap_tiers),
                            quote=" ".join(" ".join(used).split()))


def has_prose_fee_schedule(block: str) -> bool:
    """Does this block state a readable pet-fee schedule?

    Used by block SELECTION: a property that publishes its fee as a sentence and
    nothing else still has a pet-policy block, and it was previously unreachable.
    """
    return parse_prose_fee_schedule(block) is not None
