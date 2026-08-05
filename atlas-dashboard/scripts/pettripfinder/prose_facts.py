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

#: The same statement with the spaces squeezed out -- "2petsMax", "2pet Max",
#: "2pets max", "2petsmaximum". Three Columbus properties publish their limit
#: this way and every one of them read as "not stated". Deliberately narrow: an
#: explicit integer, a pet noun, an explicit max word, and nothing between them.
_COUNT_COMPACT = re.compile(
    r"\b(?P<num>\d{1,2})\s*(?P<noun>pets?|dogs?|cats?)\s*(?:max(?:imum)?)\b", re.I)

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
                     (_COUNT_TRAILING, "count_trailing"),
                     (_COUNT_COMPACT, "count_compact")):
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
#: "75lbs or less", "40 lb max", and -- the form that reached a live page --
#: "75lb weight limit", where the noun sits between the unit and the ceiling
#: word. Without it a plainly stated limit reads as silence.
_WEIGHT_TRAILING = re.compile(
    r"\b(?P<num>\d{1,3}(?:\.\d+)?)\s*(?P<unit>lbs?\.?|pounds?|kilograms?|kgs?)\s*"
    r"(?:or\s+under|or\s+less|max(?:imum)?|(?:weight\s+)?limit)\b", re.I)

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


#: Sentences about service animals, which are a legal access category and
#: never evidence of a pet-species permission.
_SERVICE_ANIMAL_SENTENCE = re.compile(
    r"[^.]*\bservice\s+(?:animals?|dogs?|cats?)\b[^.]*\.?", re.I)


#: A species named in a permission-row LABEL: "Dogs Allowed", "Cats
#: Permitted". Deliberately NOT "dogs are welcome" -- that is prose, and a
#: page that mentions dogs in prose has said nothing about cats.
_LABEL_DOGS = re.compile(r"\bdogs?\s+(?:allowed|permitted)\b", re.I)
_LABEL_CATS = re.compile(r"\bcats?\s+(?:allowed|permitted)\b", re.I)


def _labelled_species(text: str) -> Optional[ProseFact]:
    """Species named by a permission-row label, or None.

    Returns None for "Pets Allowed": that label names no species, and treating
    it as one would publish a restriction the source never stated.

    Service-animal sentences are removed first. A policy block that opens
    "Service Animals - ADA-defined service animals are welcome free of charge"
    would otherwise read as "dogs accepted", turning a legal-access statement
    into a pet-policy permission -- a hotel that takes guide dogs has said
    nothing about whether it takes pets.
    """
    text = _SERVICE_ANIMAL_SENTENCE.sub(" ", text or "")
    dogs = _LABEL_DOGS.search(text)
    cats = _LABEL_CATS.search(text)
    if dogs and cats:
        first = dogs if dogs.start() <= cats.start() else cats
        return ProseFact("dogs, cats", _span(text, first.start(), first.end(), pad=30),
                         "species_labelled_both")
    if dogs:
        return ProseFact("dogs", _span(text, dogs.start(), dogs.end(), pad=30),
                         "species_labelled_dogs")
    if cats:
        return ProseFact("cats", _span(text, cats.start(), cats.end(), pad=30),
                         "species_labelled_cats")
    return None


#: Species beyond the usual two, in the order a reader expects them. Matched
#: only as an explicit run -- "Birds/fish/2 ... dogs or cats" -- so a passing
#: mention of a bird elsewhere on a page can never widen a policy.
_EXTENDED_SPECIES_RUN = re.compile(
    r"\b(?P<run>(?:birds?|fish|dogs?|cats?)"
    r"(?:\s*/\s*(?:\d{1,2}\s+)?(?:[a-z-]+\s+){0,2}?(?:birds?|fish|dogs?|cats?))+"
    r"(?:\s+or\s+(?:birds?|fish|dogs?|cats?))?)", re.I)

_SPECIES_CANON = (("bird", "birds"), ("fish", "fish"), ("dog", "dogs"), ("cat", "cats"))


def _extended_species(text: str) -> Optional[ProseFact]:
    """A slash-separated species run naming more than dogs and cats, or None."""
    m = _EXTENDED_SPECIES_RUN.search(text or "")
    if not m:
        return None
    run = m.group("run").lower()
    found = [plural for stem, plural in _SPECIES_CANON if stem in run]
    if len(found) < 3:
        return None                      # dogs+cats alone is the ordinary case
    return ProseFact(", ".join(found), _span(text, m.start(), m.end(), pad=20),
                     "species_extended_run")


def extract_species(block: str) -> Optional[ProseFact]:
    """Explicit species permission or exclusion, or None.

    Exclusivity ("dogs only") is read first: it says something about cats that
    a bare mention of dogs does not. Nothing is inferred from silence -- a page
    that mentions dogs and says nothing about cats yields None, not
    "cats excluded".
    """
    text = block or ""

    # A source that lists MORE than dogs and cats has permitted more. Narrowing
    # "Birds/fish/2 well-mannered dogs or cats per room" to "dogs, cats" tells an
    # owner with a bird the hotel will refuse it, which the page does not say.
    # Read first, because every rule below stops at two species.
    extended = _extended_species(text)
    if extended is not None:
        return extended

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

    # Labelled permission rows: "Dogs Allowed - 2 dogs max." A brand that
    # names the species in the LABEL is stating a restriction as surely as one
    # that writes "dogs only" -- West-Hilliard permits dogs and says nothing
    # about cats anywhere on the page.
    #
    # Checked after the both-species and exclusivity rules so an explicit
    # sentence always outranks a row label, and skipped entirely when the label
    # is the generic "Pets Allowed", which names no species at all. Reading
    # that as a species would invent one.
    labelled = _labelled_species(text)
    if labelled is not None:
        return labelled

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


# --------------------------------------------------------------------------- #
# 5. Fees stated in prose, with an explicit basis.
# --------------------------------------------------------------------------- #

#: An amount with or without a dollar sign. Sources write "$25.00", "25 USD"
#: and "25 dollars" interchangeably, and the labelled patterns only ever taught
#: the promoter the first of those.
_AMOUNT = r"(?:\$\s*(?P<dollar>\d[\d,]*(?:\.\d{2})?)|(?P<plain>\d[\d,]*(?:\.\d{2})?)\s*(?:USD|usd|dollars?))"

#: Fee bases, most specific FIRST. Per-pet must beat per-night: "25 USD per pet
#: per night" satisfies both patterns, and the per-pet reading is the one that
#: doubles for a second animal.
FEE_BASIS_PER_PET_PER_NIGHT = "per pet per night"
FEE_BASIS_PER_PET_PER_STAY = "per pet per stay"
FEE_BASIS_PER_NIGHT_UP_TO_N = "per night for up to %s pets"
FEE_BASIS_PER_NIGHT = "per night"
FEE_BASIS_PER_STAY = "per stay"

_BASIS_PATTERNS = (
    (re.compile(r"per\s+pet\s+per\s+night\b", re.I), FEE_BASIS_PER_PET_PER_NIGHT),
    (re.compile(r"per\s+night\s+per\s+pet\b", re.I), FEE_BASIS_PER_PET_PER_NIGHT),
    (re.compile(r"per\s+pet\s+per\s+stay\b", re.I), FEE_BASIS_PER_PET_PER_STAY),
    (re.compile(r"(?:nightly|per\s+night|each\s+night)\s+for\s+up\s+to\s+"
                r"(?P<n>\d+|one|two|three|four)\s+pets?\b", re.I), None),
    (re.compile(r"\bper\s+pet\b", re.I), "per pet"),
    (re.compile(r"\b(?:per\s+night|nightly|each\s+night)\b", re.I), FEE_BASIS_PER_NIGHT),
    (re.compile(r"\bper\s+stay\b", re.I), FEE_BASIS_PER_STAY),
)

#: "Max 75 USD per stay" -- a ceiling, not a rate.
_PROSE_CAP = re.compile(
    r"(?:max(?:imum)?|up\s+to|not\s+to\s+exceed|capped\s+at)\s*"
    r"(?:of\s+|a\s+total\s+of\s+)?" + _AMOUNT + r"(?P<tail>[^.]{0,24})", re.I)

#: The rate itself. Anchored on a fee word so a room rate is never harvested.
_PROSE_FEE = re.compile(
    r"(?:fees?|charge)\b[^.]{0,40}?" + _AMOUNT + r"(?P<tail>[^.]{0,60})", re.I)

_NUMBER_WORD = {"one": "1", "two": "2", "three": "3", "four": "4"}


def _amount_from(m) -> str:
    raw = m.group("dollar") or m.group("plain") or ""
    raw = raw.replace(",", "")
    if not raw:
        return ""
    return "$%.2f" % float(raw)


def _basis_from(tail: str) -> str:
    """The stated basis, or "" when the source states none."""
    for rx, basis in _BASIS_PATTERNS:
        m = rx.search(tail or "")
        if not m:
            continue
        if basis is None:                       # "nightly for up to N pets"
            n = (m.groupdict().get("n") or "").lower()
            return FEE_BASIS_PER_NIGHT_UP_TO_N % _NUMBER_WORD.get(n, n)
        return basis
    return ""


# PTF-FEE-TIERS-005 -- the flattening guard.
#
# A sentence that names two different fees for two different stay lengths is a
# LADDER, whatever the parser managed to make of it. The scalar readers below
# see only one amount at a time, so on such a sentence they answer with
# whichever amount they reach first -- and publishing "$150" for a policy that
# charges $75 for a week overstates every short stay, exactly as publishing
# "$75" would understate every long one.
#
# The tier parser is the only path allowed to speak for these sentences. When
# it cannot read one, the honest outcome is that no fee publishes at all --
# not that a scalar reader gets to guess. This guard makes that structural
# rather than incidental: before PTF-FEE-TIERS-005 the promoter's scalar
# fallback was gated only on a ladder having been SUCCESSFULLY parsed, so a
# ladder the parser failed on fell straight through to it.
#
# Deliberately narrow. It fires only when BOTH are true: two or more distinct
# fee-adjacent amounts, and stay-length conditioning. A single fee with a cap
# ("$25 per night, max $75 per stay") has two amounts and no stay condition;
# a flat fee on a page mentioning a 7-night minimum has a stay condition and
# one amount. Neither is a ladder and neither is blocked.

#: Wording that makes an amount conditional on how long the stay is.
_STAY_CONDITION_RE = re.compile(
    r"\bfor\s+(?:all\s+|any\s+)?longer(?:\s+stays?)?\b"
    r"|\bthereafter\b"
    r"|\bfor\s+stays?\s+beyond\s+that\b"
    r"|\bup\s+to\s+\w+\s+(?:nights?|days?)\b"
    r"|\bfor\s+the\s+first\s+\w+\s+(?:nights?|days?)\b"
    r"|\bfor\s+stays?\s+of\s+\w+(?:\s+to\s+\w+)?\s+(?:nights?|days?)\b"
    r"|\b\d+\s*(?:[-–—]|\s+to\s+)\s*\d+\s*(?:nights?|days?)\b"
    r"|\b\d+\+\s*(?:nights?|days?|n)\b",
    re.I)

#: An amount that sits in money context, for counting distinct fees.
_FEE_AMOUNT_RE = re.compile(
    r"(?:\$\s*(\d[\d,]*(?:\.\d{2})?)|(\d[\d,]*(?:\.\d{2})?)\s*(?:USD|usd|dollars?))")


def is_stay_conditional_multi_amount(block: str) -> bool:
    """Two or more distinct fee amounts, at least one conditioned on stay length.

    This is a ladder the scalar readers must not answer for -- whether or not
    ``parse_fee_tiers`` succeeded in reading it.
    """
    text = block or ""
    if not _STAY_CONDITION_RE.search(text):
        return False
    amounts = set()
    for m in _FEE_AMOUNT_RE.finditer(text):
        raw = (m.group(1) or m.group(2) or "").replace(",", "")
        if raw:
            amounts.add("%.2f" % float(raw))
    return len(amounts) >= 2


def extract_fee_with_basis(block: str) -> Optional[ProseFact]:
    """A pet fee stated in prose, carrying the basis the source gave it.

    ``value`` is the amount; ``operator`` carries the basis, so a caller cannot
    take one without the other. A fee whose basis is unstated still returns --
    the amount is a fact -- but with an empty basis, which downstream renders
    as "Not stated" rather than as an invented "per night".

    Returns None outright on a stay-conditional multi-amount sentence: that is
    a ladder, and this reader is structurally unable to represent one.
    """
    text = block or ""
    if is_stay_conditional_multi_amount(text):
        return None
    # A cap is not a rate. Remove cap phrases before looking for the rate, or
    # "Max 75 USD per stay" is harvested as a 75-per-stay fee.
    for m in _PROSE_FEE.finditer(text):
        span = text[m.start():m.end()]
        if re.search(r"max(?:imum)?|not\s+to\s+exceed|capped", span, re.I):
            continue
        amount = _amount_from(m)
        if not amount:
            continue
        return ProseFact(amount, _span(text, m.start(), m.end()),
                         "prose_fee_with_basis", _basis_from(m.group("tail")))
    return None


def extract_fee_cap(block: str) -> Optional[ProseFact]:
    """A stated ceiling on the total, or None. Never inferred from a rate.

    Refuses a stay-conditional multi-amount sentence for the same reason
    ``extract_fee_with_basis`` does, and for one more: on such a sentence the
    "up to" that reads as a ceiling is usually bounding NIGHTS, not dollars
    ("up to $25 ... for the first six nights" is a rate, not a $25 cap).
    """
    if is_stay_conditional_multi_amount(block):
        return None
    m = _PROSE_CAP.search(block or "")
    if not m:
        return None
    amount = _amount_from(m)
    if not amount:
        return None
    return ProseFact(amount, _span(block or "", m.start(), m.end()),
                     "prose_fee_cap", _basis_from(m.group("tail")))
