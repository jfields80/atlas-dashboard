"""AES-DATA-004C Task 3 -- lodging identity-conflict resolution.

Operates on candidates that dedup already flagged ``NEEDS_REVIEW`` (never
merged) and groups them by shared normalized address to reconstruct which
candidates conflicted with which. Classification is deterministic,
keyword/token-based, and conservative: falls back to ``UNRESOLVED_IDENTITY``
whenever the available evidence doesn't clearly support a more specific
outcome, per doctrine ("never merge solely because of ... resolve only with
deterministic evidence already present").
"""

from __future__ import annotations

from typing import Dict, List, Sequence, Tuple

from scripts.pettripfinder.discovery import constants as C
from scripts.pettripfinder.discovery.models import DiscoveryCandidate
from scripts.pettripfinder.discovery.normalize import normalize_business_name


def group_conflicting_candidates(
    candidates: Sequence[DiscoveryCandidate],
) -> Tuple[Tuple[DiscoveryCandidate, ...], ...]:
    """Groups NEEDS_REVIEW candidates by normalized (address, city, state).
    Only candidates dedup already refused to merge are considered -- this
    never re-examines candidates dedup was confident about."""
    groups: Dict[Tuple[str, str, str], List[DiscoveryCandidate]] = {}
    for c in candidates:
        if c.review_state != C.REVIEW_STATE_NEEDS_REVIEW:
            continue
        key = (normalize_business_name(c.address_line),
              normalize_business_name(c.city), (c.state or "").upper())
        if not key[0]:
            continue
        groups.setdefault(key, []).append(c)
    return tuple(
        tuple(sorted(g, key=lambda c: c.candidate_id))
        for g in groups.values() if len(g) >= 2
    )


def _is_non_lodging_entity(candidate: DiscoveryCandidate) -> bool:
    if any(cat not in (C.CATEGORY_HOTEL, C.CATEGORY_MOTEL) for cat in candidate.category_candidates):
        return True
    tokens = set(candidate.normalized_name.split())
    return bool(tokens & C.IDENTITY_RESTAURANT_KEYWORDS) or bool(tokens & C.IDENTITY_CONFERENCE_KEYWORDS)


def classify_identity_relationship(group: Sequence[DiscoveryCandidate]) -> str:
    """Pure, deterministic. Never merges -- only labels an already-separate
    conflict group for the resolution report/import-eligibility gate."""
    if len(group) != 2:
        # 3+-way conflicts at one address are inherently more ambiguous --
        # always deferred to human review rather than guessed.
        return C.IDENTITY_UNRESOLVED

    a, b = group
    na, nb = a.normalized_name, b.normalized_name
    if not na or not nb:
        return C.IDENTITY_UNRESOLVED
    a_tok, b_tok = na.split(), nb.split()
    if not a_tok or not b_tok:
        return C.IDENTITY_UNRESOLVED

    if _is_non_lodging_entity(a) != _is_non_lodging_entity(b):
        return C.IDENTITY_DIFFERENT_ENTITY

    if a_tok[0] == b_tok[0]:
        return C.IDENTITY_POSSIBLE_REBRAND

    a_family = {t for t in a_tok if t in C.IDENTITY_HOTEL_BRAND_FAMILY_TOKENS}
    b_family = {t for t in b_tok if t in C.IDENTITY_HOTEL_BRAND_FAMILY_TOKENS}
    if a_family & b_family:
        return C.IDENTITY_SHARED_COMPLEX_DISTINCT_PROPERTIES

    return C.IDENTITY_DISTINCT_LOCATIONS


def resolve_identity_conflicts(
    candidates: Sequence[DiscoveryCandidate],
) -> Tuple[Tuple[Tuple[DiscoveryCandidate, ...], str], ...]:
    """Returns ``((group, outcome), ...)`` for every conflicting group found."""
    groups = group_conflicting_candidates(candidates)
    return tuple((group, classify_identity_relationship(group)) for group in groups)
