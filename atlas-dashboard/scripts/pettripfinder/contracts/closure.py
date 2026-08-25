"""``ptf-market-closure-ledger/1.0`` -- every active identity, dispositioned once.

The vocabulary here is not new. It is the one PTF-MILWAUKEE-...-038 was given
and used, lifted out of ``acquisition/closure_038.py`` -- a module that opens
with ``MARKET = "milwaukee-wi"`` and can therefore never close a second market.
Nothing about the words changed; a test pins this module's tuple to that one so
the two cannot drift apart.

WHAT A CLOSURE LEDGER IS FOR
----------------------------
The final partition says what each identity is WAITING ON. The closure ledger
says what each identity IS, right now, in terms a founder can act on:

    AUTHORITY_PET_FRIENDLY       a founder-approved pet policy exists
    AUTHORITY_VERIFIED_NO_PETS   a founder-approved refusal exists
    HELD_REVIEW                  publication-grade evidence exists and is
                                 waiting for a human decision
    SCHEMA_UNREPRESENTABLE       the source states something the schema has no
                                 slot for
    POLICY_NOT_FOUND             the property's own page served, and says
                                 nothing about pets
    INSUFFICIENT_EVIDENCE        something was read, but not enough to publish
    ACCESS_UNRESOLVED            the surface would not serve us
    IDENTITY_UNRESOLVED          we cannot safely say which building this is
    SOURCE_CONFLICT              the evidence contradicts itself
    OTHER_REQUIRES_EXPLANATION   anything else, and it must say what

THE DENOMINATOR RULE
--------------------
``reconcile`` compares SETS, never counts. A ledger that sums to the right total
over the wrong membership is the failure the partition contract already names:
swap one active identity for one that is not in the census and no total moves.
"""

from __future__ import annotations

from collections import Counter, OrderedDict
from typing import Dict, Iterable, List, Mapping, Sequence, Set, Tuple

SCHEMA = "ptf-market-closure-ledger/1.0"

AUTHORITY_PET_FRIENDLY = "AUTHORITY_PET_FRIENDLY"
AUTHORITY_VERIFIED_NO_PETS = "AUTHORITY_VERIFIED_NO_PETS"
HELD_REVIEW = "HELD_REVIEW"
IDENTITY_UNRESOLVED = "IDENTITY_UNRESOLVED"
ACCESS_UNRESOLVED = "ACCESS_UNRESOLVED"
POLICY_NOT_FOUND = "POLICY_NOT_FOUND"
INSUFFICIENT_EVIDENCE = "INSUFFICIENT_EVIDENCE"
SCHEMA_UNREPRESENTABLE = "SCHEMA_UNREPRESENTABLE"
SOURCE_CONFLICT = "SOURCE_CONFLICT"
OTHER = "OTHER_REQUIRES_EXPLANATION"

DISPOSITIONS: Tuple[str, ...] = (
    AUTHORITY_PET_FRIENDLY, AUTHORITY_VERIFIED_NO_PETS, HELD_REVIEW,
    IDENTITY_UNRESOLVED, ACCESS_UNRESOLVED, POLICY_NOT_FOUND,
    INSUFFICIENT_EVIDENCE, SCHEMA_UNREPRESENTABLE, SOURCE_CONFLICT, OTHER,
)

#: What each disposition means. Kept in the contract, not in a market's
#: document, so N markets cannot drift into N definitions of "held".
DISPOSITION_MEANINGS: Dict[str, str] = {
    AUTHORITY_PET_FRIENDLY:
        "A founder-approved pet policy exists for this identity.",
    AUTHORITY_VERIFIED_NO_PETS:
        "A founder-approved refusal exists, captured with a citable artifact.",
    HELD_REVIEW:
        "Publication-grade evidence exists on the property's own surface and "
        "is waiting for a founder decision. Never an authority.",
    IDENTITY_UNRESOLVED:
        "Which building this record names cannot be established safely, so no "
        "policy work may bind to it.",
    ACCESS_UNRESOLVED:
        "Every lane available to this market was refused by the surface, or no "
        "lane is available at all. Records the FETCH OUTCOME only.",
    POLICY_NOT_FOUND:
        "The property's own page served its content and states nothing about "
        "pets. UNKNOWN, never a refusal.",
    INSUFFICIENT_EVIDENCE:
        "Something was read, but not enough of it to publish a fact.",
    SCHEMA_UNREPRESENTABLE:
        "The source states a policy the current schema has no slot for.",
    SOURCE_CONFLICT:
        "The evidence contradicts itself or another authority, and no side may "
        "be chosen silently.",
    OTHER:
        "Anything else. A row here MUST carry an explanation; a bucket nobody "
        "explains is a bucket that hides the thing you needed to see.",
}

#: Dispositions that are an authority. Only a founder decision may produce one.
AUTHORITY_DISPOSITIONS = frozenset({AUTHORITY_PET_FRIENDLY,
                                    AUTHORITY_VERIFIED_NO_PETS})


class ClosureError(ValueError):
    """The ledger does not reconcile with the active population (fail closed)."""


def ledger_row(*, identity_key: str, canonical_name: str, corridor: str,
               disposition: str, why: str, source_url: str = "",
               brand: str = "", routing_state: str = "",
               acquisition_outcome: str = "", evidence_ref: str = "",
               **extra) -> "OrderedDict":
    if disposition not in DISPOSITIONS:
        raise ClosureError("unknown disposition %r for %s"
                           % (disposition, identity_key))
    if disposition == OTHER and not why.strip():
        raise ClosureError(
            "%s is OTHER_REQUIRES_EXPLANATION with no explanation" % identity_key)
    row = OrderedDict((
        ("identity_key", identity_key),
        ("canonical_name", canonical_name),
        ("corridor", corridor),
        ("disposition", disposition),
        ("why", why),
        ("brand", brand),
        ("source_url", source_url),
        ("routing_state", routing_state),
        ("acquisition_outcome", acquisition_outcome),
        ("evidence_ref", evidence_ref),
    ))
    for key in sorted(extra):
        row[key] = extra[key]
    return row


def reconcile(rows: Sequence[Mapping], active_keys: Iterable[str]) -> Dict:
    """Set comparison, never arithmetic.

    ``missing``   active identities with no ledger row
    ``foreign``   ledger rows naming an identity that is not active
    ``duplicate`` identities appearing more than once
    """
    active: Set[str] = set(active_keys)
    seen = [r["identity_key"] for r in rows]
    counts = Counter(seen)
    return {
        "missing": sorted(active - set(seen)),
        "foreign": sorted(set(seen) - active),
        "duplicate": sorted(k for k, n in counts.items() if n > 1),
        "active_count": len(active),
        "ledger_count": len(rows),
    }


def document(market_id: str, rows: Sequence[Mapping], *, work_order: str,
             as_of: str, active_keys: Iterable[str], note: str = "",
             **extra) -> "OrderedDict":
    """A closure ledger that refuses to exist unless it reconciles."""
    problems = reconcile(rows, active_keys)
    if problems["missing"] or problems["foreign"] or problems["duplicate"]:
        raise ClosureError(
            "closure ledger for %s does not reconcile: %d missing, %d foreign, "
            "%d duplicate (first missing: %s)"
            % (market_id, len(problems["missing"]), len(problems["foreign"]),
               len(problems["duplicate"]), problems["missing"][:3]))
    ordered = sorted(rows, key=lambda r: r["identity_key"])
    counts = Counter(r["disposition"] for r in ordered)
    doc = OrderedDict((
        ("schema", SCHEMA),
        ("market_id", market_id),
        ("work_order", work_order),
        ("as_of", as_of),
        ("note", note),
        ("active_denominator", problems["active_count"]),
        ("count", len(ordered)),
        ("disposition_counts",
         OrderedDict((name, counts[name]) for name in DISPOSITIONS if counts[name])),
        ("disposition_meanings",
         OrderedDict((name, DISPOSITION_MEANINGS[name]) for name in DISPOSITIONS
                     if counts[name])),
        ("reconciliation", OrderedDict(sorted(problems.items()))),
    ))
    for key in sorted(extra):
        doc[key] = extra[key]
    doc["rows"] = ordered
    return doc
