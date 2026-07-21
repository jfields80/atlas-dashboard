"""ATLAS-WORKERS-002 -- deterministic cross-source contradiction detection.

Stage 3 rule 13 ("contradictory same-rank official sources force CONTRADICTORY")
was, until this module, only reachable when the *model* surfaced BOTH sides of a
conflict as separate claims. A live model that returned no claims, or that
silently picked one side, hid a genuine cross-source contradiction from the
validator -- exactly the bench-07 failure repetitions (empty response ->
COMPLETED; one-sided pets_allowed=true -> COMPLETED).

This module re-reads the supplied source text itself and reconciles across
sources, independent of anything the model returned. It is ordinary deterministic
Atlas logic: it only runs bounded string/number checks over the source content
(never treats it as instructions, Stage 3 rule 15), it never PROMOTES a fact to
SUPPORTED (only the evidence validator does that), and it only ever FLAGS a
field CONTRADICTORY when two eligible authoritative sources genuinely disagree on
the same canonical field.

Design guarantees:

* Per-source identity is preserved. Each ``SourceClaim`` keeps its source URL,
  source category, field, normalized value, and verbatim supporting quote; claims
  from different documents are never merged into one undifferentiated set before
  reconciliation.
* Missing information is never a contradiction -- a document that says nothing
  about a field yields no claim for it.
* Paraphrases that normalize to the same value are never a contradiction.
* Atlas's EXISTING source-priority rule (``vocabulary.SOURCE_TYPE_RANK``, the
  same one the validator uses for rules 5/6) is the only thing that may resolve a
  disagreement automatically: when the highest authority tier present speaks with
  a single value, that value wins and a lower-tier disagreement is not a
  contradiction. When the highest tier itself carries two different values, no
  priority rule can decide it -> CONTRADICTORY. No new source-priority assumption
  is invented here.

Only fields with a genuinely deterministic, unambiguous normalizer are
registered in ``FIELD_DETECTORS``. ``pets_allowed`` (a closed boolean stated as an
explicit welcome/deny policy sentence) is registered; numeric and fee fields are
deliberately NOT, because a false positive on noisy page text would manufacture a
contradiction where none exists. The registry is the single extension point --
adding a field is registering one detector, never editing the reconciliation core
or naming a benchmark case.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Sequence, Tuple

from services.research_workers import vocabulary as V
from services.research_workers.contracts import SourceDocument


# --------------------------------------------------------------------------- #
# Per-source normalized claim (retains full source identity).
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class SourceClaim:
    """One canonical field read deterministically from ONE source document.

    Retains every attribute reconciliation and human review need: the source
    URL, the source category, the field, the normalized value, and the verbatim
    supporting quote (an exact substring of that document's content_text)."""

    source_url: str
    source_type: str
    field_name: str
    normalized_value: str
    evidence_quote: str

    @property
    def rank(self) -> int:
        return V.SOURCE_TYPE_RANK.get(self.source_type, 0)

    def to_dict(self) -> Dict:
        return {
            "source_url": self.source_url, "source_type": self.source_type,
            "field_name": self.field_name, "normalized_value": self.normalized_value,
            "evidence_quote": self.evidence_quote,
        }


@dataclass(frozen=True)
class FieldContradiction:
    """A field two eligible authoritative sources disagree on, unresolved by any
    explicit source-priority rule. ``sides`` are the conflicting top-authority
    claims (both citations, values, and verbatim quotes preserved for review)."""

    field_name: str
    sides: Tuple[SourceClaim, ...]
    summary: str


# --------------------------------------------------------------------------- #
# Verbatim quote extraction (an exact substring of the source content).
# --------------------------------------------------------------------------- #

def _line_quote(text: str, start: int, end: int, cap: int = V.EVIDENCE_QUOTE_CAP) -> str:
    """The verbatim line of ``text`` containing [start, end), trimmed and capped.

    Stays an exact substring of the source (the quote is trimmed of surrounding
    whitespace only); if the line exceeds the cap it is clamped to a window that
    still contains the matched span."""
    left = text.rfind("\n", 0, start) + 1          # 0 when there is no newline
    right = text.find("\n", end)
    if right == -1:
        right = len(text)
    snippet = text[left:right].strip()
    if len(snippet) > cap:
        s2 = max(left, start - 40)
        snippet = text[s2:s2 + cap].strip()
    return snippet


# --------------------------------------------------------------------------- #
# Deterministic field detectors. Each takes ONE usable official document and
# returns a normalized SourceClaim, or None when the document is silent on the
# field. A detector NEVER guesses: silence -> None, never a default value.
# --------------------------------------------------------------------------- #

# pets_allowed. Negation is checked first and dominates, so "no pets are allowed"
# is read as false even though it contains the substring "pets are allowed".
_PETS_NEGATIVE = re.compile(
    r"\bno pets\b"
    r"|pets?\s+(?:are\s+)?not\s+(?:allowed|permitted|accepted|welcome)"
    r"|pets?\s+(?:are\s+)?prohibited"
    r"|do(?:es)?\s+not\s+(?:allow|permit|accept)\s+pets"
    r"|cannot accommodate pets"
    r"|not (?:a )?pet[- ]friendly",
    re.I)
_PETS_POSITIVE = re.compile(
    r"pets?\s+(?:are\s+)?(?:welcome|allowed|permitted|accepted)"
    r"|\bpet[- ]friendly\b"
    r"|we welcome (?:pets|dogs|cats)"
    # A species-specific acceptance also establishes that pets are allowed
    # (dogs/cats are pets); directional only -- it never runs the other way.
    r"|(?:dogs?|cats?)\s+(?:and\s+(?:dogs?|cats?)\s+)?(?:are\s+)?(?:welcome|accepted|allowed|permitted)",
    re.I)


def _detect_pets_allowed(doc: SourceDocument) -> Optional[SourceClaim]:
    text = doc.content_text
    neg = _PETS_NEGATIVE.search(text)
    if neg:
        return SourceClaim(doc.source_url, doc.source_type, V.FIELD_PETS_ALLOWED,
                           "false", _line_quote(text, neg.start(), neg.end()))
    pos = _PETS_POSITIVE.search(text)
    if pos:
        return SourceClaim(doc.source_url, doc.source_type, V.FIELD_PETS_ALLOWED,
                           "true", _line_quote(text, pos.start(), pos.end()))
    return None


# The single extension point: field_name -> detector. Only fields with an
# unambiguous deterministic normalizer belong here.
FIELD_DETECTORS: Dict[str, Callable[[SourceDocument], Optional[SourceClaim]]] = {
    V.FIELD_PETS_ALLOWED: _detect_pets_allowed,
}


# --------------------------------------------------------------------------- #
# Extraction + reconciliation.
# --------------------------------------------------------------------------- #

def extract_source_claims(docs: Sequence[SourceDocument]) -> List[SourceClaim]:
    """Every deterministic per-source claim across the USABLE OFFICIAL documents.

    OTHER (search-snippet/third-party) and blocked/empty sources are never
    scanned -- consistent with Stage 3 rules 4/14 (they are never publication
    evidence). Ordered deterministically (best source first, then URL, then
    field) so downstream output is stable across runs."""
    usable = [d for d in docs if d.is_usable_official]
    usable.sort(key=lambda d: (-V.SOURCE_TYPE_RANK.get(d.source_type, 0), d.source_url))
    claims: List[SourceClaim] = []
    for doc in usable:
        for field_name in V.POLICY_FIELDS:                 # authoritative field order
            detector = FIELD_DETECTORS.get(field_name)
            if detector is None:
                continue
            claim = detector(doc)
            if claim is not None:
                claims.append(claim)
    return claims


def _summarize(field_name: str, sides: Sequence[SourceClaim]) -> str:
    """A single self-contained human-review record: field, and for each side its
    value, category, verbatim quote, and URL. The field name is the prefix before
    the first ':' so downstream field parsing (benchmark scorer) is unaffected."""
    parts = ['%s [%s] "%s" (%s)' % (s.normalized_value, s.source_type,
                                    s.evidence_quote, s.source_url)
             for s in sides]
    return "%s: %s" % (field_name, " vs ".join(parts))


def detect_field_contradictions(docs: Sequence[SourceDocument]) -> Dict[str, FieldContradiction]:
    """Fields on which two eligible authoritative sources disagree, with no
    explicit source-priority rule to resolve them.

    For each field, the claims are grouped by Atlas's existing source rank. The
    field is contradictory ONLY when the HIGHEST rank present carries more than
    one distinct normalized value: at that tier no priority rule can pick a side
    (rule 13). A single value at the top tier -- even with a differing lower-tier
    source -- is resolved by rank (rules 5/6) and is NOT a contradiction here."""
    by_field: Dict[str, List[SourceClaim]] = {}
    for claim in extract_source_claims(docs):
        by_field.setdefault(claim.field_name, []).append(claim)

    contradictions: Dict[str, FieldContradiction] = {}
    for field_name, claims in by_field.items():
        top_rank = max(c.rank for c in claims)
        top = [c for c in claims if c.rank == top_rank]
        if len({c.normalized_value for c in top}) < 2:
            continue                                       # agree, or rank resolves it
        sides = tuple(sorted(top, key=lambda c: (c.normalized_value, c.source_url)))
        contradictions[field_name] = FieldContradiction(
            field_name, sides, _summarize(field_name, sides))
    return contradictions
