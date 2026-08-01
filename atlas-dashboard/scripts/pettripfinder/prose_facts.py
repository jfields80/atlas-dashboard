"""PTF-PROMOTE -- read pet-policy facts stated in ordinary prose.

The promoter is label-driven: it looks for "Maximum Pet Weight: 40.0lbs" and
"Maximum Number of Pets in Room: 2". That works for the brands that publish a
structured policy card, and finds nothing at all when a property simply writes
a sentence:

    "This is a dog only hotel. Up to two friendly pups under 80 lbs are
     welcome. Pet fee per pet is 75 to 150 dollars depending on length of
     stay of reservation."

Every fact in that sentence is stated plainly by the official source. None of
it was reachable, so the hotel could not be published at all -- not even its
species and weight limits, which are unambiguous.

This module reads that prose. It is deliberately timid:

  * a number counts only when it is ADJACENT to the thing it measures -- a
    count next to a pet noun, a weight next to a weight unit. Nothing is
    inferred from proximity alone, so a room number, a phone number, a street
    number, a year and a dollar amount are all invisible to it;
  * a weight counts only when a CEILING word governs it. "at least 20 lbs" and
    "combined weight of 100 lbs" are refused rather than guessed at, because
    each means something different from a per-pet maximum;
  * word-numbers come from a closed list, one to ten. There is no general
    numeral parser to be surprised by;
  * species are read only from explicit exclusivity or explicit permission;
  * anything ambiguous returns nothing. A fact this module cannot read is a
    fact the promoter simply does not publish, which is the existing
    fail-closed behaviour and not a regression.

Every returned fact carries the exact source span that produced it.

Nothing here names a brand, a property, a hotel id, a property code or a URL.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, Optional, Tuple

# --------------------------------------------------------------------------- #
# Shared vocabulary.
# --------------------------------------------------------------------------- #

#: Closed list. A general spelled-numeral parser would be a source of surprises
#: for no benefit -- pet policies do not permit "forty-seven" dogs.
WORD_NUMBERS = {
    "one": 1, "two": 2, "three": 3, "four": 4, "five": 5,
    "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10,
}
_WORD_NUM_RE = "|".join(sorted(WORD_NUMBERS, key=len, reverse=True))

#: Nouns a count may attach to. "pups" and "pooches" appear in real policy
#: prose; without them the count is unreadable on those pages.
_PET_NOUNS = (r"pets?|dogs?|cats?|pups?|puppies|puppy|pooches|pooch|"
              r"animals?|canines?|felines?")

#: Words that make a number a CEILING. Without one of these a weight figure is
#: not a maximum and must not be published as one.
_CEILING = (r"under|up\s+to|max(?:imum)?(?:\s+weight)?(?:\s+of)?|no\s+more\s+than|"
            r"less\s+than|not\s+(?:to\s+)?exceed(?:ing)?|below|at\s+most|"
            r"weigh(?:ing|s)?\s+less\s+than|weigh(?:ing|s)?\s+under|"
            r"weight\s+limit(?:\s+of)?|limited\s+to")

#: Contexts that disqualify a weight even when a ceiling word is present.
#: A combined allowance and a per-pet allowance are different promises, and a
#: floor is the opposite of a ceiling.
_WEIGHT_DISQUALIFIERS = (
    r"combined", r"total\s+weight", r"aggregate",
    r"at\s+least", r"minimum", r"min\.", r"over\s+\d", r"greater\s+than",
    r"heavier\s+than",
    # "no more than 80 lbs" is a CEILING; only a bare "more than" is a floor.
    r"(?<!no )more\s+than\s+\d+\s*(?:lbs?|pounds)",
)

#: Money-adjacent words. A number governed by these is a fee, never a weight
#: or a count.
_MONEY_CONTEXT = r"fee|deposit|charge|cost|rate|dollars?|usd|\$|cleaning|damage"


def _span(text: str, start: int, end: int, pad: int = 0) -> str:
    """The exact source span that produced a fact, whitespace-normalised."""
    return " ".join(text[max(0, start - pad):end + pad].split())


# --------------------------------------------------------------------------- #
# 1. Counts.
# --------------------------------------------------------------------------- #

#: Weight-limit comparison operators. "under 80 lbs" and "up to 80 lbs" are
#: different promises: the first excludes an 80-pound dog, the second admits
#: it. Publishing one as the other is a factual error about which animals the
#: hotel will take, so the operator travels with the number.
WEIGHT_OP_LT = "lt"        # strictly under
WEIGHT_OP_LTE = "lte"      # at most (the historical assumption)

#: Ceiling words that EXCLUDE the stated figure. Anything not here is treated
#: as inclusive, which is the pre-existing behaviour and the safer default for
#: labelled fields like "Maximum Pet Weight: 40.0lbs".
_EXCLUSIVE_CEILINGS = ("under", "less than", "below", "fewer than")


@dataclass(frozen=True)
class ProseFact:
    value: str
    quote: str
    rule: str
    operator: str = ""

    def to_dict(self) -> dict:
        d = {"value": self.value, "quote": self.quote, "rule": self.rule}
        if self.operator:
            d["operator"] = self.operator
        return d


# "up to two pets", "maximum of 2 dogs", "no more than two pets",
# "two friendly pups" (an adjective may sit between the number and the noun).
_COUNT_GOVERNED = re.compile(
    r"(?:up\s+to|max(?:imum)?(?:\s+of)?|no\s+more\s+than|limit(?:ed)?\s+(?:to|of)|"
    r"allows?|permits?|accepts?|welcomes?)\s+"
    r"(?P<num>\d{1,2}|" + _WORD_NUM_RE + r")\s+"
    r"(?:[a-z]+\s+){0,2}?"
    r"(?P<noun>" + _PET_NOUNS + r")\b", re.I)

# "2 pets per room", "two dogs maximum"
_COUNT_TRAILING = re.compile(
    r"\b(?P<num>\d{1,2}|" + _WORD_NUM_RE + r")\s+"
    r"(?:[a-z]+\s+){0,2}?"
    r"(?P<noun>" + _PET_NOUNS + r")\s+"
    r"(?:per\s+room|max(?:imum)?|allowed|permitted)\b", re.I)

MAX_PLAUSIBLE_PETS = 10


def _as_int(token: str) -> Optional[int]:
    t = token.strip().lower()
    if t.isdigit():
        return int(t)
    return WORD_NUMBERS.get(t)


def extract_pet_count(block: str) -> Optional[ProseFact]:
    """A stated maximum number of pets, or None.

    Requires an explicit limiting construction. A bare "two dogs" is not a
    limit -- it could be describing a photograph -- so it is not read.
    """
    text = block or ""
    for rx, rule in ((_COUNT_GOVERNED, "count_governed"),
                     (_COUNT_TRAILING, "count_trailing")):
        for m in rx.finditer(text):
            n = _as_int(m.group("num"))
            if n is None or not (1 <= n <= MAX_PLAUSIBLE_PETS):
                continue
            quote = _span(text, m.start(), m.end())
            # A count must not be a sum of money.
            if re.search(_MONEY_CONTEXT, quote, re.I):
                continue
            return ProseFact(str(n), quote, rule)
    return None


# --------------------------------------------------------------------------- #
# 2. Weight ceilings.
# --------------------------------------------------------------------------- #

_WEIGHT_CEILING = re.compile(
    r"(?P<ceil>" + _CEILING + r")\s*"
    r"(?:[a-z]+\s+){0,3}?"
    r"(?P<num>\d{1,3}(?:\.\d+)?)\s*"
    r"(?P<unit>lbs?\.?|pounds?|kilograms?|kgs?)\b", re.I)

# "pets must weigh less than 80 lbs" -- ceiling word AFTER the noun, number
# after that; covered by _WEIGHT_CEILING because "less than" precedes 80.
# "80 lb maximum" -- number first, ceiling after.
_WEIGHT_TRAILING = re.compile(
    r"\b(?P<num>\d{1,3}(?:\.\d+)?)\s*(?P<unit>lbs?\.?|pounds?|kilograms?|kgs?)\s*"
    r"(?:or\s+under|or\s+less|max(?:imum)?|limit)\b", re.I)

MAX_PLAUSIBLE_WEIGHT_LB = 400.0


def extract_weight_limit(block: str) -> Optional[ProseFact]:
    """A stated per-pet maximum weight, or None.

    Refuses combined allowances, minimums, and anything in a money context.
    """
    text = block or ""
    for rx, rule in ((_WEIGHT_CEILING, "weight_ceiling"),
                     (_WEIGHT_TRAILING, "weight_trailing")):
        for m in rx.finditer(text):
            try:
                value = float(m.group("num"))
            except ValueError:
                continue
            if not (0 < value <= MAX_PLAUSIBLE_WEIGHT_LB):
                continue
            # Look a little wider than the match: "combined" and "at least"
            # usually sit just outside the governed phrase.
            context = _span(text, m.start(), m.end(), pad=60)
            if any(re.search(d, context, re.I) for d in _WEIGHT_DISQUALIFIERS):
                continue
            if re.search(r"\$\s*%s\b" % re.escape(m.group("num")), context):
                continue
            # Which ceiling word governed it decides whether the stated figure
            # is itself allowed. "under 80 lbs" turns an 80-pound dog away;
            # "up to 80 lbs" takes it.
            governing = (m.groupdict().get("ceil") or "").lower()
            operator = (WEIGHT_OP_LT
                        if any(e in governing for e in _EXCLUSIVE_CEILINGS)
                        else WEIGHT_OP_LTE)
            return ProseFact("%.1f pounds" % value,
                             _span(text, m.start(), m.end()), rule, operator)
    return None


# --------------------------------------------------------------------------- #
# 3. Species.
# --------------------------------------------------------------------------- #

#: Both species joined, however the source punctuates it. Checked FIRST and
#: separately, because "dog/cat only" contains the literal substring
#: "cat only" -- reading that as cats-only inverted the policy of three real
#: Hilton properties, admitting cats and silently excluding the dogs the page
#: plainly allows.
_SPECIES_JOIN = r"(?:\s*/\s*|\s*&\s*|\s+or\s+|\s+and\s+|\s*,\s*)"
_BOTH_ONLY = re.compile(
    r"\bdogs?" + _SPECIES_JOIN + r"cats?\s*[-\s]*only\b"
    r"|\bcats?" + _SPECIES_JOIN + r"dogs?\s*[-\s]*only\b"
    r"|\bonly\s+dogs?" + _SPECIES_JOIN + r"cats?\b"
    r"|\bonly\s+cats?" + _SPECIES_JOIN + r"dogs?\b", re.I)
_BOTH = re.compile(r"\bdogs?" + _SPECIES_JOIN + r"cats?\b"
                   r"|\bcats?" + _SPECIES_JOIN + r"dogs?\b", re.I)

# Exclusivity, and only when the OTHER species is not adjacent.
_DOGS_ONLY = re.compile(
    r"\bdogs?\s*[-\s]*only\b(?!" + _SPECIES_JOIN + r"cats?)"
    r"|\bonly\s+dogs?\b(?!" + _SPECIES_JOIN + r"cats?)", re.I)
_CATS_ONLY = re.compile(
    r"(?<!/)\bcats?\s*[-\s]*only\b|\bonly\s+cats?\b", re.I)
_CATS_EXCLUDED = re.compile(
    r"\bno\s+cats?\b|\bcats?\s+are\s+not\s+(?:permitted|allowed|accepted)\b|"
    r"\bcats?\s+not\s+(?:permitted|allowed|accepted)\b", re.I)
_DOGS_EXCLUDED = re.compile(
    r"\bno\s+dogs?\b|\bdogs?\s+are\s+not\s+(?:permitted|allowed|accepted)\b|"
    r"\bdogs?\s+not\s+(?:permitted|allowed|accepted)\b", re.I)


def extract_species(block: str) -> Optional[ProseFact]:
    """Explicit species permission or exclusion, or None.

    Exclusivity ("dogs only") is read first: it says something about cats that
    a bare mention of dogs does not. Nothing is inferred from silence -- a page
    that mentions dogs and says nothing about cats yields None, not
    "cats excluded".
    """
    text = block or ""
    for rx, value, rule in (
        # Both-species phrasings FIRST. "dog/cat only" is a permission for two
        # species, not an exclusivity claim about one.
        (_BOTH_ONLY, "dogs, cats", "species_both_only"),
        (_BOTH, "dogs, cats", "species_both"),
        (_DOGS_ONLY, "dogs", "species_dogs_only"),
        (_CATS_ONLY, "cats", "species_cats_only"),
    ):
        m = rx.search(text)
        if m:
            return ProseFact(value, _span(text, m.start(), m.end(), pad=30), rule)

    m = _CATS_EXCLUDED.search(text)
    if m and not _DOGS_EXCLUDED.search(text):
        return ProseFact("dogs", _span(text, m.start(), m.end(), pad=30),
                         "species_cats_excluded")
    m = _DOGS_EXCLUDED.search(text)
    if m and not _CATS_EXCLUDED.search(text):
        return ProseFact("cats", _span(text, m.start(), m.end(), pad=30),
                         "species_dogs_excluded")
    return None


# --------------------------------------------------------------------------- #
# 3b. An explicit statement that pets are allowed.
# --------------------------------------------------------------------------- #

_PETS_ALLOWED = re.compile(
    r"\b(?:pets?|dogs?|cats?)\s+(?:are\s+)?(?:welcome|allowed|permitted|accepted)\b"
    r"|\bwe\s+(?:welcome|allow|permit|accept)\s+(?:pets?|dogs?|cats?)\b"
    r"|\b(?:pet|dog|cat)[-\s]friendly\b", re.I)

_PETS_REFUSED = re.compile(
    r"\bno\s+pets?\b|\bpets?\s+are\s+not\s+(?:permitted|allowed|accepted)\b"
    r"|\bpets?\s+not\s+(?:permitted|allowed|accepted)\b", re.I)


def extract_pets_allowed(block: str) -> Optional[ProseFact]:
    """An explicit welcome, or an explicit refusal. Silence yields None.

    A refusal anywhere in the block wins: "pets are welcome ... no pets in the
    restaurant" is a page this must not read as a simple yes, so it declines
    rather than choosing.
    """
    text = block or ""
    refused = _PETS_REFUSED.search(text)
    allowed = _PETS_ALLOWED.search(text)
    if refused and allowed:
        return None                      # contradictory prose: fail closed
    if refused:
        return ProseFact("false", _span(text, refused.start(), refused.end(), pad=20),
                         "pets_refused")
    if allowed:
        return ProseFact("true", _span(text, allowed.start(), allowed.end(), pad=20),
                         "pets_allowed")
    return None


# --------------------------------------------------------------------------- #
# 4. Fee ranges the schema cannot hold.
# --------------------------------------------------------------------------- #

UNREPRESENTABLE_FEE_RANGE = "unrepresentable_fee_range_in_official_source"

# "75 to 150 dollars", "$75 to $150", "$75-$150", "between 75 and 150 dollars".
_FEE_RANGE = re.compile(
    r"(?:between\s+)?"
    r"\$?\s*(?P<low>\d[\d,]*(?:\.\d{1,2})?)\s*"
    r"(?:to|through|[-–—]|and)\s*"
    r"\$?\s*(?P<high>\d[\d,]*(?:\.\d{1,2})?)\s*"
    r"(?P<unit>dollars?|usd)?", re.I)

#: A range only matters when it is a FEE. Without this a weight range, a date
#: range or a room count would be read as money.
_FEE_NEARBY = re.compile(r"fee|charge|cost|rate|price|deposit", re.I)


@dataclass(frozen=True)
class FeeRange:
    low: str
    high: str
    quote: str

    def to_dict(self) -> dict:
        return {"low": self.low, "high": self.high, "evidence_quote": self.quote}


def detect_unrepresentable_fee_range(block: str) -> Optional[FeeRange]:
    """A fee stated as a RANGE, which no single-amount field can hold.

    "75 to 150 dollars depending on length of stay" is two numbers and a
    condition. Publishing either end is wrong -- 150 overstates a short stay,
    75 understates a long one -- and the thresholds that would separate them
    are not stated, so a tier ladder cannot be built either. The honest
    representation is to withhold the number and show the sentence.

    Returns None when the range is not about money, or when the two ends are
    equal (which is a single amount awkwardly written, not a range).
    """
    text = block or ""
    for m in _FEE_RANGE.finditer(text):
        window = _span(text, m.start(), m.end(), pad=70)
        if not _FEE_NEARBY.search(window):
            continue
        if m.group("unit") is None and "$" not in text[max(0, m.start() - 2):m.end()]:
            # Neither a currency word nor a dollar sign: not demonstrably money.
            continue
        low = m.group("low").replace(",", "")
        high = m.group("high").replace(",", "")
        try:
            if float(low) >= float(high):
                continue
        except ValueError:
            continue
        # A weight or night range that happens to sit near the word "fee" is
        # not a fee range.
        if re.search(r"\b(?:lbs?|pounds?|nights?|days?|guests?|rooms?)\b",
                     text[m.end():m.end() + 12], re.I):
            continue
        return FeeRange(low, high, _span(text, m.start(), m.end(), pad=70))
    return None
