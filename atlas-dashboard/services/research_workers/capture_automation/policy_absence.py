"""Confirmed policy absence -- the official page says pets are NOT accepted.

WHY THIS EXISTS
---------------
Ten of the fourteen POLICY_NOT_FOUND outcomes in the consolidated run were not
adapter failures at all: the hotels do not take pets, so there was no pet policy
on the page to find. Reporting those as "no anchor appeared in the rendered
page" makes a correct result look like an extraction defect, and buries the one
genuine miss among nine non-problems.

``POLICY_ABSENT_CONFIRMED`` separates:

    "we could not locate policy information"          -> POLICY_NOT_FOUND
    "the official page affirmatively says no pets"    -> POLICY_ABSENT_CONFIRMED

WHAT IT IS NOT
--------------
It is **not** a policy fact and **not** a successful capture. It is a
capture-stage observation, non-authoritative like every other capture output.
The official-source worker plus human approval remain the sole producers of
published policy facts, including negative ones. Nothing here enters
extraction, attestation, approval, promotion, assembly, publication or
deployment.

THE RULE THAT MATTERS MOST
--------------------------
**It may never be inferred from silence.** Absence of an anchor, absence of pet
text, absence of structured data, a missing amenity, a brand default, a
chain-wide assumption, an absent fee, an absent badge -- none of these can
produce this classification. Only an affirmative, property-level statement on
the official page can, and only from the evidence forms enumerated below.

Service-animal language is handled with particular care: "service animals only"
is affirmative evidence that ordinary pets are NOT accepted. It is never
evidence that pets ARE accepted.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Any, FrozenSet, Optional, Sequence, Tuple

#: The terminal reason. Registered in ``reasons.EXCEPTION_REASONS``.
POLICY_ABSENT_CONFIRMED = "POLICY_ABSENT_CONFIRMED"

# --------------------------------------------------------------------------- #
# Evidence forms. Each names WHERE the affirmative statement came from, so a
# reviewer can audit the classification rather than trust it.
# --------------------------------------------------------------------------- #

EVIDENCE_STRUCTURED_FALSE = "structured_pets_allowed_false"
EVIDENCE_VISIBLE_NO_PETS = "visible_text_no_pets_allowed"
EVIDENCE_VISIBLE_SERVICE_ANIMALS_ONLY = "visible_text_service_animals_only"

SUPPORTED_EVIDENCE: FrozenSet[str] = frozenset({
    EVIDENCE_STRUCTURED_FALSE, EVIDENCE_VISIBLE_NO_PETS,
    EVIDENCE_VISIBLE_SERVICE_ANIMALS_ONLY,
})

# --------------------------------------------------------------------------- #
# Visible-text patterns.
#
# Deliberately narrow and property-level. Each requires an explicit negative
# statement -- not a missing amenity, not an absent badge, not ambiguity.
# --------------------------------------------------------------------------- #

_NO_PETS = re.compile(
    r"\b(?:no\s+pets?\s+(?:are\s+)?(?:allowed|permitted|accepted)"
    r"|pets?\s+(?:are\s+)?not\s+(?:allowed|permitted|accepted)"
    r"|we\s+(?:do\s+not|don'?t)\s+(?:allow|accept|permit)\s+pets?"
    r"|this\s+hotel\s+does\s+not\s+(?:allow|accept|permit)\s+pets?)\b", re.I)

_SERVICE_ANIMALS_ONLY = re.compile(
    r"\bservice\s+animals?\s+only\b"
    r"|\bonly\s+service\s+animals?\s+(?:are\s+)?(?:allowed|permitted|accepted)\b"
    r"|\bno\s+pets?\s*[-–—,]?\s*service\s+animals?\s+only\b", re.I)

#: Phrases that look negative but are NOT property-level refusals. A page that
#: says pets are welcome *except* in some area is a pet-friendly hotel, and
#: must never be classified absent.
_AMBIGUOUS = re.compile(
    r"\bnot\s+allowed\s+in\s+(?:the\s+)?(?:pool|restaurant|dining|spa|fitness"
    r"|gym|lobby|breakfast)\b"
    r"|\bpets?\s+are\s+welcome\b"
    r"|\bpet[-\s]?friendly\b", re.I)


@dataclass(frozen=True)
class AbsenceVerdict:
    """Whether the official page affirmatively refuses ordinary pets."""

    confirmed: bool
    evidence: Tuple[str, ...] = ()
    quotes: Tuple[str, ...] = ()
    explanation: str = ""

    def to_dict(self) -> dict:
        return {
            "confirmed": self.confirmed,
            "evidence": list(self.evidence),
            "quotes": list(self.quotes),
            "explanation": self.explanation,
            "non_authoritative": True,
            "not_for_extraction": True,
        }


def _structured_pets_allowed(blocks: Sequence[Any]) -> Optional[bool]:
    """``petsAllowed`` from a Hotel-ish JSON-LD block, or None if unstated.

    None and False are deliberately different answers: None is silence, which
    can never confirm absence.
    """
    def walk(node):
        if isinstance(node, dict):
            if "@graph" in node and isinstance(node["@graph"], list):
                for item in node["@graph"]:
                    yield from walk(item)
                return
            yield node
        elif isinstance(node, (list, tuple)):
            for item in node:
                yield from walk(item)

    for block in walk(list(blocks or ())):
        if "petsAllowed" not in block:
            continue
        value = block.get("petsAllowed")
        if isinstance(value, bool):
            return value
        if isinstance(value, str):
            v = value.strip().lower()
            if v in ("false", "no"):
                return False
            if v in ("true", "yes"):
                return True
            # Prose such as "no pets allowed-service animals only" is a real
            # affirmative refusal, and is read as such.
            if _NO_PETS.search(v) or _SERVICE_ANIMALS_ONLY.search(v):
                return False
            return None
    return None


def _snippet(text: str, match: re.Match, width: int = 120) -> str:
    start = max(0, match.start() - width // 2)
    return " ".join(text[start:match.end() + width // 2].split())


def assess_absence(*, jsonld: Sequence[Any] = (), visible_text: str = "") -> AbsenceVerdict:
    """Decide whether the OFFICIAL page affirmatively refuses ordinary pets.

    ``visible_text`` must be the page's RENDERED text. Passing raw HTML would
    let a ``display:none`` panel decide the outcome, which would break the
    correspondence between what a capture records and what its screenshot can
    show.
    """
    evidence: list = []
    quotes: list = []

    structured = _structured_pets_allowed(jsonld)
    if structured is True:
        # An affirmative "pets allowed" outranks everything: a page that says
        # pets are welcome is never classified absent, whatever else it says.
        return AbsenceVerdict(False, explanation="structured data states petsAllowed: true")
    if structured is False:
        evidence.append(EVIDENCE_STRUCTURED_FALSE)
        quotes.append("petsAllowed: false")

    text = visible_text or ""
    if text:
        positive = _AMBIGUOUS.search(text)
        no_pets = _NO_PETS.search(text)
        service_only = _SERVICE_ANIMALS_ONLY.search(text)

        # A page carrying both a refusal and pet-friendly language is
        # ambiguous, and ambiguity is never confirmation.
        if positive and not structured is False and (no_pets or service_only):
            return AbsenceVerdict(
                False,
                explanation="page carries both negative and pet-friendly language; "
                            "ambiguous evidence never confirms absence")
        if no_pets:
            evidence.append(EVIDENCE_VISIBLE_NO_PETS)
            quotes.append(_snippet(text, no_pets))
        if service_only:
            evidence.append(EVIDENCE_VISIBLE_SERVICE_ANIMALS_ONLY)
            quotes.append(_snippet(text, service_only))

    if not evidence:
        return AbsenceVerdict(
            False,
            explanation="no affirmative property-level refusal found; silence is "
                        "never confirmation of absence")

    return AbsenceVerdict(
        True, evidence=tuple(dict.fromkeys(evidence)), quotes=tuple(quotes[:3]),
        explanation="official page affirmatively indicates ordinary pets are not accepted")
