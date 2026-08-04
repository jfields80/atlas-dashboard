"""PTF-DISCOVERY-001 -- bounded cross-slug duplicate detection.

The existing guard compares ``hotel_id`` slugs, which are derived from the
property NAME. That misses the case the consolidated run surfaced:

    le-m-ridien-columbus-the-joseph   vs   le-meridien-columbus-the-joseph

One physical hotel. Same official property code ``cmhdm``, same phone, same
street. The slugs differ only because the accented "é" survives in one path and
is dropped in the other, so a slug comparison cannot see it -- and both entries
were queued, captured and failed independently.

**Slug normalization is not the fix.** Folding accents would catch this exact
pair and nothing else: two genuinely different hotels can share a slug, and one
hotel can appear under two unrelated names. Identity has to be decided on
identity evidence, so that is what this module compares. Accent folding is
still applied inside name normalization, but only as a tie-break input, never
as the deciding signal.

DECISION LADDER (highest confidence first)
------------------------------------------
1. exact official property code
2. exact normalized phone AND exact normalized street address
3. exact canonical official URL
4. one strong identifier PLUS a high-confidence normalized property-name match

Rules 1-3 produce a DUPLICATE_HOLD. Rule 4 produces MANUAL_REVIEW. Nothing is
ever merged: a hold records the relationship and preserves both records, their
source identifiers and their aliases, so a human decides and the decision is
auditable afterwards.
"""

from __future__ import annotations

import re
import unicodedata
from dataclasses import dataclass, field
from typing import Dict, FrozenSet, Iterable, List, Optional, Sequence, Tuple
from urllib.parse import urlsplit

# --------------------------------------------------------------------------- #
# Outcomes.
# --------------------------------------------------------------------------- #

DUPLICATE_HOLD = "DUPLICATE_HOLD"        # strong evidence; both records held
MANUAL_REVIEW = "MANUAL_REVIEW"          # suggestive only; a human decides
DISTINCT = "DISTINCT"                    # no duplicate relationship found

OUTCOMES = frozenset({DUPLICATE_HOLD, MANUAL_REVIEW, DISTINCT})

# Evidence rules, in ladder order.
RULE_PROPERTY_CODE = "exact_official_property_code"
RULE_PHONE_AND_STREET = "exact_phone_and_street_address"
RULE_CANONICAL_URL = "exact_canonical_official_url"
RULE_IDENTIFIER_PLUS_NAME = "strong_identifier_plus_name_match"

STRONG_RULES: FrozenSet[str] = frozenset({
    RULE_PROPERTY_CODE, RULE_PHONE_AND_STREET, RULE_CANONICAL_URL,
})

#: Name similarity is never sufficient alone -- it is only ever the second half
#: of rule 4, and rule 4 only ever reaches MANUAL_REVIEW.
NAME_MATCH_THRESHOLD = 0.90


# --------------------------------------------------------------------------- #
# Normalisation.
# --------------------------------------------------------------------------- #

_STREET_ABBREV = {
    "street": "st", "avenue": "ave", "road": "rd", "boulevard": "blvd",
    "drive": "dr", "lane": "ln", "parkway": "pkwy", "highway": "hwy",
    "north": "n", "south": "s", "east": "e", "west": "w",
    "northeast": "ne", "northwest": "nw", "southeast": "se", "southwest": "sw",
    "suite": "ste",
}

#: Words that carry no identity: every hotel has them.
_NAME_NOISE = frozenset({
    "hotel", "hotels", "inn", "suites", "suite", "motel", "resort", "by",
    "the", "and", "at", "a", "an", "of", "lodge",
})


def fold_accents(value: str) -> str:
    """``Le Méridien`` -> ``Le Meridien``.

    Applied inside name normalisation so an accent cannot make two spellings of
    one name look unrelated. It is NOT a duplicate rule on its own -- see the
    module docstring.
    """
    decomposed = unicodedata.normalize("NFKD", value or "")
    return "".join(c for c in decomposed if not unicodedata.combining(c))


def normalize_name(value: str) -> str:
    v = fold_accents(value).lower()
    v = re.sub(r"[^a-z0-9]+", " ", v)
    return " ".join(v.split())


def name_tokens(value: str) -> FrozenSet[str]:
    """Identity-bearing tokens only. Dropping the noise words stops
    'Hampton Inn' and 'Hilton Garden Inn' scoring on 'inn'."""
    return frozenset(t for t in normalize_name(value).split()
                     if t and t not in _NAME_NOISE)


def normalize_phone(value: str) -> str:
    """Last ten digits, so formatting and a country prefix cannot split one
    number into two."""
    return re.sub(r"\D", "", value or "")[-10:]


def normalize_street(value: str) -> str:
    """Street line only, abbreviations folded.

    ``620 N High St, Columbus, OH 43215, USA`` and ``620 North High Street``
    must normalise to the same thing -- one is a provider's formatted address
    and the other a page's street line, and they describe one doorway.
    """
    head = (value or "").split(",")[0]
    v = normalize_name(head)
    return " ".join(_STREET_ABBREV.get(t, t) for t in v.split())


def normalize_canonical_url(value: str) -> str:
    """Scheme/host/path only: no query, no fragment, no trailing slash, no
    ``www.``. Tracking parameters must not make one page look like two."""
    if not value:
        return ""
    parts = urlsplit(value.strip())
    host = (parts.netloc or "").lower()
    if host.startswith("www."):
        host = host[4:]
    path = (parts.path or "").rstrip("/").lower()
    return "%s%s" % (host, path) if host else ""


def name_similarity(a: str, b: str) -> float:
    """Jaccard over identity-bearing tokens. Deterministic and explainable --
    no edit-distance tuning, no opaque score."""
    ta, tb = name_tokens(a), name_tokens(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


# --------------------------------------------------------------------------- #
# Records.
# --------------------------------------------------------------------------- #

@dataclass(frozen=True)
class DuplicateCandidate:
    """The identity evidence one record offers. Deliberately not a QueueEntry
    or a DiscoveryCandidate: both shapes can be projected onto this, and this
    module then has exactly one thing to reason about."""

    record_id: str
    name: str = ""
    property_code: str = ""
    phone: str = ""
    street: str = ""
    canonical_url: str = ""
    source_ids: Tuple[str, ...] = ()
    aliases: Tuple[str, ...] = ()

    @staticmethod
    def from_queue_entry(entry) -> "DuplicateCandidate":
        return DuplicateCandidate(
            record_id=entry.hotel_id, name=entry.hotel_name,
            property_code=entry.expected_property_code, phone=entry.expected_phone,
            street=entry.expected_address, canonical_url=entry.official_url,
            source_ids=tuple(entry.discovery_provenance_refs or ()),
            aliases=(entry.listing_key,) if entry.listing_key else ())


@dataclass(frozen=True)
class DuplicateRelation:
    """One pair, the rule that matched, and the evidence behind it.

    Nothing is merged. Both record ids survive, both sets of source ids and
    aliases survive, and the rule is named so the decision can be audited or
    reversed later.
    """

    left_id: str
    right_id: str
    outcome: str
    rule: str
    evidence: Tuple[str, ...] = ()
    preserved_source_ids: Tuple[str, ...] = ()
    preserved_aliases: Tuple[str, ...] = ()
    name_similarity: float = 0.0

    def to_dict(self) -> dict:
        return {
            "left_id": self.left_id, "right_id": self.right_id,
            "outcome": self.outcome, "rule": self.rule,
            "evidence": list(self.evidence),
            "preserved_source_ids": list(self.preserved_source_ids),
            "preserved_aliases": list(self.preserved_aliases),
            "name_similarity": round(self.name_similarity, 4),
            "merged": False,
        }


# --------------------------------------------------------------------------- #
# The ladder.
# --------------------------------------------------------------------------- #

def compare(a: DuplicateCandidate, b: DuplicateCandidate) -> Optional[DuplicateRelation]:
    """Apply the ladder to one pair. Returns None when they are DISTINCT."""
    if a.record_id == b.record_id:
        return None

    left, right = sorted((a, b), key=lambda c: c.record_id)   # deterministic order
    sim = name_similarity(left.name, right.name)
    common = dict(
        left_id=left.record_id, right_id=right.record_id,
        preserved_source_ids=tuple(sorted(set(left.source_ids) | set(right.source_ids))),
        preserved_aliases=tuple(sorted(set(left.aliases) | set(right.aliases))),
        name_similarity=sim)

    # 1 -- exact official property code.
    lc, rc = left.property_code.strip().lower(), right.property_code.strip().lower()
    if lc and lc == rc:
        return DuplicateRelation(outcome=DUPLICATE_HOLD, rule=RULE_PROPERTY_CODE,
                                 evidence=("property_code:%s" % lc,), **common)

    # 2 -- exact phone AND exact street.
    lp, rp = normalize_phone(left.phone), normalize_phone(right.phone)
    ls, rs = normalize_street(left.street), normalize_street(right.street)
    if lp and lp == rp and ls and ls == rs:
        return DuplicateRelation(outcome=DUPLICATE_HOLD, rule=RULE_PHONE_AND_STREET,
                                 evidence=("phone:%s" % lp, "street:%s" % ls), **common)

    # 3 -- exact canonical official URL.
    lu, ru = normalize_canonical_url(left.canonical_url), normalize_canonical_url(right.canonical_url)
    if lu and lu == ru:
        return DuplicateRelation(outcome=DUPLICATE_HOLD, rule=RULE_CANONICAL_URL,
                                 evidence=("canonical_url:%s" % lu,), **common)

    # 4 -- one strong identifier PLUS a high-confidence name match.
    #      Suggestive, never decisive: MANUAL_REVIEW, never a hold.
    if sim >= NAME_MATCH_THRESHOLD:
        if lp and lp == rp:
            return DuplicateRelation(outcome=MANUAL_REVIEW, rule=RULE_IDENTIFIER_PLUS_NAME,
                                     evidence=("phone:%s" % lp, "name_similarity:%.2f" % sim),
                                     **common)
        if ls and ls == rs:
            return DuplicateRelation(outcome=MANUAL_REVIEW, rule=RULE_IDENTIFIER_PLUS_NAME,
                                     evidence=("street:%s" % ls, "name_similarity:%.2f" % sim),
                                     **common)
    return None


def find_duplicates(candidates: Sequence[DuplicateCandidate]) -> Tuple[DuplicateRelation, ...]:
    """Every duplicate relation in a set. Deterministic: candidates are sorted
    and compared pairwise in a fixed order."""
    ordered = sorted(candidates, key=lambda c: c.record_id)
    out: List[DuplicateRelation] = []
    for i in range(len(ordered)):
        for j in range(i + 1, len(ordered)):
            rel = compare(ordered[i], ordered[j])
            if rel is not None:
                out.append(rel)
    return tuple(out)


def held_record_ids(relations: Sequence[DuplicateRelation]) -> Tuple[str, ...]:
    """Records in a DUPLICATE_HOLD. Both sides are held -- we do not guess
    which of two records describing one hotel is the one to keep."""
    ids = set()
    for r in relations:
        if r.outcome == DUPLICATE_HOLD:
            ids.add(r.left_id)
            ids.add(r.right_id)
    return tuple(sorted(ids))


def manual_review_ids(relations: Sequence[DuplicateRelation]) -> Tuple[str, ...]:
    ids = set()
    for r in relations:
        if r.outcome == MANUAL_REVIEW:
            ids.add(r.left_id)
            ids.add(r.right_id)
    return tuple(sorted(ids))


def summarize(relations: Sequence[DuplicateRelation]) -> Dict[str, int]:
    out: Dict[str, int] = {"relations": len(relations)}
    for r in relations:
        out[r.outcome] = out.get(r.outcome, 0) + 1
        out["rule_%s" % r.rule] = out.get("rule_%s" % r.rule, 0) + 1
    return dict(sorted(out.items()))
