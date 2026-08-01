"""Find the pet policy in a rendered page.

Brand-neutral by construction. The anchors below are phrases, not selectors,
and the scoring keys on what a block *says*. An adapter may add anchors it
knows about (Hilton's compressed tier notation carries no anchor phrase at all)
and may supply a better selector, but it cannot loosen what counts as a hit.

The block boundary problem is real: ``document.body.innerText`` runs the pet
policy straight into whatever follows it, which in the fixture corpus is
"Parking", "All Policies" or a restaurant description. Terminators are how the
excerpt stops being the rest of the page.
"""

from __future__ import annotations

import re
from typing import List, Optional, Sequence, Tuple

from .contracts import (
    CONFIDENCE_HIGH, CONFIDENCE_LOW, CONFIDENCE_MEDIUM, DomSnapshot,
    PolicyLocation,
)

# The eight anchors from the sprint brief, ordered strongest first. A strong
# anchor is one that can only be a pet-policy heading; "Pets" alone is weak
# because it matches navigation and amenity lists too.
STRONG_ANCHORS = (
    "Pet Policy",
    "Pets Welcome",
    "Other pet information",
    "Maximum Pet Weight",
    "Maximum Number of Pets",
)
WEAK_ANCHORS = (
    "Pets allowed",
    "Non-refundable fee",
    "Pets",
)
ALL_ANCHORS = STRONG_ANCHORS + WEAK_ANCHORS

# Where a policy block stops. Everything here was observed terminating a real
# pet block in the retained corpus.
BLOCK_TERMINATORS = (
    "All Policies", "Parking", "Gather your group", "GATHER YOUR GROUP",
    "Dining and drinks", "Discover ", "More Ways to Enjoy",
    "Additional Parking Information", "Explore",
    # FAQ accordions: the answer ends where the list's own controls begin.
    "READ FEWER FAQS", "Read fewer FAQs", "READ MORE FAQS",
    "Was anything missing",
)

# Corroborating content: a real policy block says something about money,
# weight, or counts. Used for scoring and for confidence, never as a gate --
# "Pets Welcome" with no numbers is still a pet policy, just a vague one.
_MONEY_RE = re.compile(r"\$\s?\d")
_WEIGHT_RE = re.compile(r"\b\d+(?:\.\d+)?\s*(?:lbs?|pounds|kg)\b", re.I)
_COUNT_RE = re.compile(r"\b\d+\s*pets?\b|\bmax(?:imum)?\s+(?:of\s+)?\d+\b", re.I)
_NIGHTS_RE = re.compile(r"\b\d+\s*(?:n\b|nights?)\b", re.I)

MAX_EXCERPT_CHARS = 600


def _terminator_after(text: str, start: int) -> int:
    """First terminator at or after ``start``. Returns len(text) if none."""
    best = len(text)
    for term in BLOCK_TERMINATORS:
        i = text.find(term, start)
        if 0 <= i < best:
            best = i
    return best


def extract_block(text: str, start: int) -> Tuple[str, int, int]:
    """The policy block beginning at ``start``, bounded by the next terminator
    or ``MAX_EXCERPT_CHARS``, whichever comes first."""
    hard_end = min(start + MAX_EXCERPT_CHARS, len(text))
    end = min(_terminator_after(text, start + 1), hard_end)
    return (text[start:end].strip(), start, end)


def score_block(block: str, matched: Sequence[str]) -> int:
    """How much this looks like a pet policy. Additive and deliberately dull --
    a scoring function nobody can predict is a scoring function nobody can
    debug."""
    score = 0
    for anchor in matched:
        score += 10 if anchor in STRONG_ANCHORS else 3
    if _MONEY_RE.search(block):
        score += 6
    if _WEIGHT_RE.search(block):
        score += 4
    if _COUNT_RE.search(block):
        score += 4
    if _NIGHTS_RE.search(block):
        score += 2
    # A block that is only a heading is worth less than one with substance.
    if len(block) >= 60:
        score += 2
    return score


def _confidence(score: int, matched: Sequence[str], block: str) -> str:
    strong = any(a in STRONG_ANCHORS for a in matched)
    substantive = bool(_MONEY_RE.search(block) or _WEIGHT_RE.search(block)
                       or _COUNT_RE.search(block))
    if strong and substantive and score >= 20:
        return CONFIDENCE_HIGH
    if strong or substantive:
        return CONFIDENCE_MEDIUM
    return CONFIDENCE_LOW


def find_anchor_hits(text: str,
                     extra_anchors: Sequence[str] = ()) -> List[Tuple[str, int]]:
    """Every anchor occurrence, as ``(anchor, index)``, earliest first."""
    hits: List[Tuple[str, int]] = []
    for anchor in tuple(ALL_ANCHORS) + tuple(extra_anchors):
        start = 0
        while True:
            i = text.find(anchor, start)
            if i < 0:
                break
            hits.append((anchor, i))
            start = i + 1
    hits.sort(key=lambda h: h[1])
    return hits


def locate_policy(dom: DomSnapshot,
                  *, extra_anchors: Sequence[str] = (),
                  selector: str = "") -> Optional[PolicyLocation]:
    """Best pet-policy block in the page, or None.

    Candidate blocks are clustered: anchors within a few hundred characters of
    one another describe the same block, and the real Marriott page hits five
    anchors inside one 200-character span. Treating each as a separate candidate
    would score the same block five times and pick an arbitrary one of them.
    """
    text = dom.text or ""
    if not text.strip():
        return None

    hits = find_anchor_hits(text, extra_anchors)
    if not hits:
        return None

    # Cluster: start a new candidate whenever the gap from the previous anchor
    # exceeds the terminator distance.
    clusters: List[List[Tuple[str, int]]] = []
    for hit in hits:
        if clusters and hit[1] - clusters[-1][-1][1] <= 300:
            clusters[-1].append(hit)
        else:
            clusters.append([hit])

    best: Optional[PolicyLocation] = None
    for cluster in clusters:
        start = cluster[0][1]
        matched = tuple(dict.fromkeys(a for a, _ in cluster))
        block, s, e = extract_block(text, start)
        if not block:
            continue
        score = score_block(block, matched)
        loc = PolicyLocation(
            selector=selector, matched_anchors=matched, score=score,
            text_excerpt=block, text_start=s, text_end=e,
            confidence=_confidence(score, matched, block))
        if best is None or loc.score > best.score:
            best = loc

    # A lone weak anchor with nothing corroborating is not a policy. Refusing
    # here is what keeps "Pets" in a nav menu from becoming evidence.
    if best is not None and best.confidence == CONFIDENCE_LOW:
        return None
    return best
