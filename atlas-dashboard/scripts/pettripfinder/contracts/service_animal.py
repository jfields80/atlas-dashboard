"""What a property actually said about charging for a service animal.

Why this module exists
----------------------
A service animal is a legal access category, not a commercial term, and the
sentence a property writes about one is almost always written *next to* the
pet charge it is exempting the animal from. That adjacency is the whole
problem. Until PTF-MILWAUKEE-SERVICE-ANIMAL-CORRECTION-011 the interpretation
was a two-step fallback inside ``authority_build_036``::

    if re.search(r"without\\s+charge|no\\s+charge|free\\s+of\\s+charge", text):
        charges = "no_charge"
    elif re.search(r"\\bfee\\b|\\bcharge\\b", text):
        charges = "charge_stated"

The second branch asks only whether the WORD "fee" or "charge" occurs. Every
exemption sentence in English contains one, because an exemption has to name
the thing it exempts you from. So four LIVE Milwaukee profiles published

    "The property states that service animals are welcome and that a charge
     applies."

from sources that said the exact opposite -- "Service animals will be exempt
from this charge", "no pet fee required for service animals", "except ADA
Service Animals". A token match on "charge" is evidence that a charge was
MENTIONED. It is never evidence that one APPLIES.

The rule
--------
Exemption and negation WIN. They are tested before any charge pattern, over
the whole statement rather than a clause, because a sentence that both names a
charge and exempts the service animal from it is an exemption sentence.

A charge may only be concluded when the source BINDS a charge to the service
animal itself -- "service animals are subject to the pet fee", "a $50 fee
applies to service animals". A fee mentioned anywhere else in the same
sentence says nothing about the animal and must fall through to what the
sentence does establish: that the animal is welcome.

Four categories, three wire values
----------------------------------
``classify`` returns the INTERPRETATION, which distinguishes an exemption from
a bare welcome from an explicit charge from silence. ``charges_stated`` maps
that onto the published ``service_animal_statement.charges_stated`` enum,
which has three members and is pinned by schema 1.2/1.3 and by every one of
the 245 live records. Splitting the two keeps the reasoning legible without
introducing a fourth wire value that no existing consumer -- renderer,
validator, compatibility reader -- would know how to read.

``EXEMPT_FROM_PET_CHARGE`` covers both spellings of the same fact: "exempt
from this charge" and "permitted, without charge". They differ in grammar, not
in what a guest pays, and the profile row says the same true thing for both.

Pure function
-------------
Nothing here reads a record, a market, a store row or a file. The input is the
property's own sentence; the output is a category. That is what makes it
testable against the exact strings that were published wrongly.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Optional, Pattern, Tuple

from scripts.pettripfinder.contracts import enums

#: The source stated that a service animal is not charged the pet charge --
#: whether by exempting it ("exempt from this charge", "except ADA Service
#: Animals") or by saying so outright ("permitted, without charge").
EXEMPT_FROM_PET_CHARGE = "EXEMPT_FROM_PET_CHARGE"

#: The source bound a charge to the service animal ITSELF. Never inferred from
#: a fee that merely appears in the same sentence.
CHARGE_EXPLICITLY_APPLIES = "CHARGE_EXPLICITLY_APPLIES"

#: The source accepted service animals and said nothing about a charge for
#: them. Silence about a fee is not a statement that none applies.
ALLOWED = "ALLOWED"

#: The source did not address service animals at all, or addressed them in
#: terms this module refuses to guess at.
SOURCE_SILENT = "SOURCE_SILENT"

INTERPRETATIONS: Tuple[str, ...] = (
    EXEMPT_FROM_PET_CHARGE, CHARGE_EXPLICITLY_APPLIES, ALLOWED, SOURCE_SILENT,
)

#: How each interpretation is published. ``ALLOWED`` and ``SOURCE_SILENT``
#: share a wire value because the published enum answers "what did the source
#: say about CHARGES", and to that question both are "it did not say".
_WIRE = {
    EXEMPT_FROM_PET_CHARGE: enums.SERVICE_ANIMAL_NO_CHARGE,
    CHARGE_EXPLICITLY_APPLIES: enums.SERVICE_ANIMAL_CHARGE_STATED,
    ALLOWED: enums.SERVICE_ANIMAL_NOT_ADDRESSED,
    SOURCE_SILENT: enums.SERVICE_ANIMAL_NOT_ADDRESSED,
}

# --------------------------------------------------------------------------- #
# Vocabulary.
# --------------------------------------------------------------------------- #

#: A reference to the animal. ``ADA`` on its own counts: brands abbreviate the
#: whole category to "except ADA Service Animals" and sometimes to just "ADA".
_ANIMAL = (r"(?:(?:ada[- ]?(?:defined|certified)?\s+)?"
           r"(?:certified\s+|trained\s+|registered\s+)*"
           r"(?:service|assistance|guide|seeing[- ]eye|support)\s+"
           r"(?:animal|animals|dog|dogs)|\bada\b)")

_ANIMAL_RE = re.compile(_ANIMAL, re.IGNORECASE)

#: The money words. Kept in one place so an exemption and a charge can never
#: disagree about what counts as a charge.
_MONEY = r"(?:pet\s+)?(?:fee|fees|charge|charges|deposit|deposits|cost|costs)"

#: A clause boundary. An exemption may cross one ("we charge $50 ... , except
#: ADA Service Animals"); a CHARGE binding may not, which is what stops a fee
#: in a neighbouring sentence from attaching itself to the animal.
_STOP = r"[^.;\n]"

# --------------------------------------------------------------------------- #
# Exemption -- tested first, and it wins.
# --------------------------------------------------------------------------- #

_EXEMPTIONS: Tuple[Pattern, ...] = (
    # "Service animals will be exempt from this charge."
    re.compile(r"\bexempt(?:ed|ion|ions)?\b", re.IGNORECASE),
    # "We charge 50.00 per pet, per night, except ADA Service Animals."
    re.compile(r"\bexcept(?:ing)?\b(?:\s+for)?\s+%s{0,40}?(?:%s)"
               % (_STOP, _ANIMAL), re.IGNORECASE),
    # "no pet fee required for service animals", "no charge", "no fee applies"
    re.compile(r"\bno\s+(?:additional\s+|extra\s+|separate\s+)?%s\b" % _MONEY,
               re.IGNORECASE),
    # "without charge", "at no cost", "free of charge", "complimentary"
    re.compile(r"\bwithout\s+(?:any\s+)?(?:additional\s+|extra\s+)?%s\b"
               % _MONEY, re.IGNORECASE),
    re.compile(r"\bat\s+no\s+(?:additional\s+|extra\s+)?%s\b" % _MONEY,
               re.IGNORECASE),
    re.compile(r"\bfree\s+of\s+charge\b|\bcharge[- ]free\b", re.IGNORECASE),
    re.compile(r"\bcomplimentary\b", re.IGNORECASE),
    # "the pet fee is waived", "not subject to the pet fee"
    re.compile(r"\bwaive[ds]?\b|\bwaiver\b|\bwaiving\b", re.IGNORECASE),
    re.compile(r"\bnot\s+(?:be\s+)?subject\s+to\b", re.IGNORECASE),
    # "not applicable to service animals", "does not apply to service animals"
    re.compile(r"\bnot\s+applicable\s+(?:to|for)\b\s*%s{0,40}?(?:%s)"
               % (_STOP, _ANIMAL), re.IGNORECASE),
    re.compile(r"\b(?:do|does|will|shall)\s+not\s+apply\s+(?:to|for)\b\s*"
               r"%s{0,40}?(?:%s)" % (_STOP, _ANIMAL), re.IGNORECASE),
    # "clean fee excludes Service Animals"
    re.compile(r"\bexclud(?:e|es|ed|ing)\b\s*%s{0,40}?(?:%s)"
               % (_STOP, _ANIMAL), re.IGNORECASE),
    # "are not charged", "do not incur a fee", "is never charged"
    re.compile(r"\b(?:are|is|will|do|does|shall|would)\s+(?:not|never)\s+"
               r"(?:be\s+)?(?:charged|assessed|billed|"
               r"required\s+to\s+pay|incur)\b", re.IGNORECASE),
    # "no ... fee is required", "never a charge applies"
    re.compile(r"\b(?:no|not|never)\s+%s{0,30}?\b%s\s+(?:is|are|will\s+be\s+)?"
               r"(?:required|charged|applied|applicable)\b"
               % (_STOP, _MONEY), re.IGNORECASE),
)

# --------------------------------------------------------------------------- #
# An explicit charge -- only when it is BOUND to the animal.
# --------------------------------------------------------------------------- #

_CHARGE_VERB = (r"(?:are|is|will\s+be|shall\s+be|must\s+be)\s+"
                r"(?:subject\s+to|charged|assessed|billed|required\s+to\s+pay)")

_CHARGES: Tuple[Pattern, ...] = (
    # "Service animals are subject to the $50 nightly pet fee."
    re.compile(r"(?:%s)%s{0,60}?\b%s\b%s{0,60}?\b%s\b"
               % (_ANIMAL, _STOP, _CHARGE_VERB, _STOP, _MONEY),
               re.IGNORECASE),
    # "Service animals are charged $75 per night."
    re.compile(r"(?:%s)%s{0,60}?\b%s\b%s{0,20}?[$\d]"
               % (_ANIMAL, _STOP, _CHARGE_VERB, _STOP), re.IGNORECASE),
    # "Service animals incur the standard pet fee."
    re.compile(r"(?:%s)%s{0,60}?\b(?:incur|incurs|pay|pays|owe|owes)\b"
               r"%s{0,40}?\b%s\b" % (_ANIMAL, _STOP, _STOP, _MONEY),
               re.IGNORECASE),
    # "A $50 pet fee applies to service animals."
    re.compile(r"\b%s\b%s{0,60}?\b(?:applies|apply|is\s+charged|are\s+charged|"
               r"is\s+required|are\s+required|is\s+assessed|are\s+assessed)\b"
               r"\s*(?:to|for)\s+%s{0,40}?(?:%s)"
               % (_MONEY, _STOP, _STOP, _ANIMAL), re.IGNORECASE),
    # "We charge $50 per night for service animals."
    re.compile(r"\bcharg(?:e|es|ed|ing)\b%s{0,60}?\bfor\b\s+%s{0,30}?(?:%s)"
               % (_STOP, _STOP, _ANIMAL), re.IGNORECASE),
)

# --------------------------------------------------------------------------- #
# A bare acceptance.
# --------------------------------------------------------------------------- #

_ALLOWED_RE = re.compile(
    r"\b(?:welcome|welcomed|allowed|permitted|accepted|admitted|"
    r"accommodated)\b", re.IGNORECASE)


@dataclass(frozen=True)
class Reading:
    """The category, and the rule that produced it.

    ``reason`` is not decoration: the defect this module was written for was
    invisible precisely because the old code could not say WHY it had decided
    a charge applied. A category with no stated rule is a category nobody can
    audit.
    """

    interpretation: str
    reason: str

    @property
    def charges_stated(self) -> str:
        return _WIRE[self.interpretation]


def classify(statement: Optional[str]) -> Reading:
    """Interpret one property's service-animal sentence. Never inferential."""
    text = re.sub(r"\s+", " ", str(statement or "")).strip()
    if not text:
        return Reading(SOURCE_SILENT, "the source stated nothing")

    if not _ANIMAL_RE.search(text):
        # The statement does not mention the animal, so nothing in it -- fee
        # word or not -- is a claim about the animal.
        return Reading(SOURCE_SILENT,
                       "no service-animal reference in the statement")

    for pattern in _EXEMPTIONS:
        match = pattern.search(text)
        if match:
            return Reading(EXEMPT_FROM_PET_CHARGE,
                           "exemption or negation language: %r"
                           % match.group(0).strip())

    for pattern in _CHARGES:
        match = pattern.search(text)
        if match:
            return Reading(CHARGE_EXPLICITLY_APPLIES,
                           "a charge is bound to the animal itself: %r"
                           % match.group(0).strip())

    if _ALLOWED_RE.search(text):
        return Reading(ALLOWED,
                       "acceptance stated; the source did not address charges")

    return Reading(SOURCE_SILENT,
                   "service animals mentioned without an acceptance or a "
                   "charge this module will interpret")


def charges_stated(statement: Optional[str]) -> str:
    """The published ``charges_stated`` value for one statement."""
    return classify(statement).charges_stated


__all__ = ["EXEMPT_FROM_PET_CHARGE", "CHARGE_EXPLICITLY_APPLIES", "ALLOWED",
           "SOURCE_SILENT", "INTERPRETATIONS", "Reading", "classify",
           "charges_stated"]
