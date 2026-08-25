"""founder-approval-vocabulary/1.0 -- one word for "a founder approved this".

WHAT THIS IS, AND WHAT IT IS NOT
---------------------------------
It is not a new vocabulary. The repository has had one since Columbus:
``contracts.enums`` owns the strings, ``APPROVAL_DECISIONS`` enumerates the
states, ``PUBLISHING_DECISIONS`` says which of them may publish, and
``LEGACY_APPROVAL_DECISIONS`` maps older spellings onto the canonical one.
Those remain the single source of the values; nothing is restated here.

What was missing is the CONTRACT around them: a version, a resolver every
consumer can share, and a rule about what new code may write. Without those,
each work order re-derived the vocabulary from whatever it happened to read,
and PTF-MILWAUKEE-FOUNDER-DECISION-040 wrote ``APPROVED`` -- a string this
repository had already classified as LEGACY INPUT four work orders earlier.
Three records carry it. Nothing broke, because every consumer that mattered
compared against the canonical constant; what broke was the next reader, who
saw two spellings and could not tell which one to write.

THE CANONICAL VALUE IS THE LONG ONE
------------------------------------
``APPROVED_AFTER_CURRENT_REVIEW``, and this was derived rather than preferred.

  * 333 of the 336 committed approval records across six markets carry it.
  * Five markets' publication validators compare against it literally --
    Cleveland, Dayton, Indianapolis and both Pittsburgh passes refuse a record
    whose decision is anything else.
  * ``APPROVED`` is already a KEY in ``LEGACY_APPROVAL_DECISIONS``, mapping TO
    it. Promoting a registered legacy synonym to canonical would invert an
    existing versioned map and make 333 records the exception.

The shorter string reads better and the longer one names a procedure rather
than a state. Neither is worth inverting a contract five markets already
enforce, and a vocabulary normalization whose first act is to make almost
every existing record non-canonical has normalized nothing.

WHAT THE STATES MEAN
---------------------
They are six genuinely different things and this module collapses none of
them:

``APPROVED_AFTER_CURRENT_REVIEW``
    A human read this exact record and approved it. Publishable.
``LEGACY_BASELINE_REVIEWED``
    Remediated honestly with today's date and today's reviewer, because the
    original approval was never recorded. Publishable, and deliberately NOT
    spelled as an approval nobody gave.
``MACHINE_REVIEWED_PENDING_OPERATOR``
    A machine's opinion awaiting a person. Not publishable.
``HELD_FOR_REVIEW``
    A person looked and declined to approve. Not publishable.
``REJECTED`` / ``SUPERSEDED``
    Refused, or replaced by a later decision. Not publishable.

The founder's DECISION vocabulary is a different axis and is not touched here:
a ledger records ``APPROVE`` / ``APPROVE_REFUSAL`` / ``HOLD``, which is what
the person said, while an authority record's ``approval.decision`` is the state
that resulted. Both 036 and 040 already agree on the first; only the second
diverged.
"""

from __future__ import annotations

from typing import Dict, FrozenSet, Iterable, Mapping, Optional, Tuple

from scripts.pettripfinder.contracts import enums

#: Bump when the meaning of a state changes or a state is added or removed.
#: A new SPELLING of an existing state is not a version bump -- it is a legacy
#: input, and it belongs in ``enums.LEGACY_APPROVAL_DECISIONS``.
VOCABULARY_VERSION = "founder-approval-vocabulary/1.0"

#: The one value new code may write for "a founder approved this".
CANONICAL_APPROVED = enums.APPROVED_AFTER_CURRENT_REVIEW

#: Every state, canonical spelling. Owned by ``enums``; re-exported so a
#: consumer needs one import rather than two.
STATES: Tuple[str, ...] = enums.APPROVAL_DECISIONS

#: The states that may put a record in front of a traveller.
PUBLISHING_STATES: FrozenSet[str] = enums.PUBLISHING_DECISIONS

#: Older spellings, accepted on READ and never written. ``APPROVED`` is here
#: because Columbus wrote it and 040 wrote it again; both resolve to canonical.
LEGACY_INPUTS: Dict[str, str] = dict(enums.LEGACY_APPROVAL_DECISIONS)

#: Two legacy spellings carry information beyond the state. It migrates into a
#: caveat rather than being flattened away.
LEGACY_CAVEATS: Dict[str, str] = dict(enums.LEGACY_APPROVAL_CAVEATS)

#: Spellings new code may emit. Exactly the canonical states -- a legacy input
#: is an input.
WRITABLE: FrozenSet[str] = frozenset(STATES)


class ApprovalVocabularyError(ValueError):
    """Raised rather than guessing what an unrecognised approval means."""


def normalize(decision: Optional[str], *, strict: bool = True) -> str:
    """The canonical state for ``decision``, resolving a legacy spelling.

    Read-side. A record committed years ago keeps whatever it says on disk and
    resolves here; nothing is rewritten to make a comparison work.
    """
    value = (decision or "").strip()
    if value in STATES:
        return value
    if value in LEGACY_INPUTS:
        return LEGACY_INPUTS[value]
    if strict:
        raise ApprovalVocabularyError(
            "%r is not an approval state and not a registered legacy "
            "spelling. Add it to enums.LEGACY_APPROVAL_DECISIONS if it is an "
            "older spelling of an existing state, or to "
            "enums.APPROVAL_DECISIONS if it is genuinely a new state -- "
            "guessing which would either invent an approval or lose one."
            % decision)
    return value


def caveat_for(decision: Optional[str]) -> str:
    """What a legacy spelling said beyond its state, or ``""``."""
    return LEGACY_CAVEATS.get((decision or "").strip(), "")


def is_publishable(decision: Optional[str]) -> bool:
    """Whether this decision, once resolved, may reach a traveller."""
    return normalize(decision, strict=False) in PUBLISHING_STATES


def assert_writable(decision: str, *, where: str = "") -> str:
    """Guard for WRITE paths: new code emits canonical spellings only.

    ``APPROVED`` resolves cleanly on read and is still refused here. That is
    the whole point: a synonym that round-trips is exactly the kind that
    spreads, and 040 introduced its three records by writing one.
    """
    if decision in WRITABLE:
        return decision
    if decision in LEGACY_INPUTS:
        raise ApprovalVocabularyError(
            "%s may not WRITE %r: it is a legacy spelling of %r, accepted on "
            "read only. New records use the canonical value."
            % (where or "this caller", decision, LEGACY_INPUTS[decision]))
    raise ApprovalVocabularyError(
        "%s may not write %r: it is not an approval state at all"
        % (where or "this caller", decision))


def resolve_record(record: Mapping) -> Dict:
    """One authority record's approval, as the current vocabulary reads it.

    Returns what the record SAYS alongside what it MEANS, because a consumer
    that only ever sees the resolved value cannot tell a canonical record from
    a legacy one, and the difference is worth being able to report.
    """
    approval = record.get("approval") or {}
    stored = approval.get("decision")
    resolved = normalize(stored)
    return {
        "identity_key": record.get("identity_key", ""),
        "stored_decision": stored,
        "resolved_decision": resolved,
        "is_canonical_spelling": stored == resolved,
        "legacy_caveat": caveat_for(stored),
        "publishable": resolved in PUBLISHING_STATES,
        "vocabulary": VOCABULARY_VERSION,
    }


def inventory(records: Iterable[Mapping]) -> Dict:
    """Every spelling in a package, what it resolves to, and how many."""
    from collections import Counter
    rows = [resolve_record(record) for record in records]
    spellings = Counter(row["stored_decision"] for row in rows)
    return {
        "vocabulary": VOCABULARY_VERSION,
        "canonical": CANONICAL_APPROVED,
        "records": len(rows),
        "by_stored_spelling": dict(spellings),
        "by_resolved_state": dict(Counter(row["resolved_decision"]
                                          for row in rows)),
        "legacy_spellings_present": sorted(
            {row["stored_decision"] for row in rows
             if not row["is_canonical_spelling"]}),
        "publishable": sum(1 for row in rows if row["publishable"]),
    }
