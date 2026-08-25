"""What a founder approval is actually ABOUT.

A founder approves a claim: this property, these facts, this evidence, from
this source, under this schema. An approval must stop binding the moment any
of that changes -- that is the whole point of hashing it.

The original binding hashed the entire store row minus its approval block. It
was right about the direction and too broad in scope: the row also carries how
the reading was produced -- which commit of the reader ran, when the capture
happened, which provider fetched it, where the bytes sit on disk. None of that
is the claim. It is how the claim can be reproduced.

The consequence was measured, not theorised. PTF-...-FULL-CLOSURE-038 repaired
a reader defect and re-projecting the store then withdrew SIXTEEN of the
founder's ninety-eight decisions. FIFTEEN of the sixteen had no fact and no
evidence change whatsoever; the only thing that had moved was
``rederivation.reader_commit``, a field the projection re-derives on every
single run. An approval that evaporates because a comment changed in a parser
is not a tamper-detection mechanism, it is noise that trains people to
re-attest without reading.

So this module splits one question into two:

  * ``semantic_projection`` -- the approved MEANING. Change any of it and the
    approval must be earned again.
  * everything else -- PROVENANCE. Kept, recorded, never deleted, and never on
    its own a reason to withdraw an approval.

THE LISTS ARE EXHAUSTIVE ON PURPOSE
------------------------------------
Both sides are enumerated, and ``unclassified_fields`` reports anything in a
row that appears on neither. An allow-list alone would silently DROP a new
semantic field out of the binding, which is a tamper hole; an exclusion list
alone would silently ADMIT a new provenance field, which reopens exactly the
defect above. A field nobody has classified must fail loudly, and a test holds
that line.
"""

from __future__ import annotations

import hashlib
import json
from typing import Any, Dict, Iterable, Mapping, Tuple

#: Bump when the definition of the approved meaning changes. Approvals record
#: the version they were bound under, so an old approval is never silently
#: reinterpreted by a newer rule.
BINDING_CONTRACT_VERSION = "semantic-approval/1.0"

# --------------------------------------------------------------------------- #
# The approved meaning.
# --------------------------------------------------------------------------- #

#: WHICH property, WHAT is claimed about it, and HOW GOOD the evidence is.
SEMANTIC_TOP_LEVEL: Tuple[str, ...] = (
    "identity_key",
    "canonical_name",
    "market_id",
    "brand",
    "policy_schema_version",
    # The claim itself, and its exact negative space: a withholding says "this
    # is not being asserted", which is as much a part of what was approved as
    # an asserted fee.
    "proposed_facts",
    "withheld_fields",
    "service_animal_statement",
    "is_refusal",
    # What the claim rests on.
    "evidence",
    "publication_grade",
    "identity_check",
    "review_status",
    "frozen_semantics_violations",
)

#: Source identity: which page, and the page's own content hash. Read a
#: different URL, or the same URL after the page changed, and the approval is
#: about something else.
SEMANTIC_PROVENANCE: Tuple[str, ...] = (
    "source_url",
    "final_url",
    "snapshot_hash",
    "authority_tier",
    "source_type",
)

#: The canonical identity of the located evidence. The PATH to the block is
#: provenance; the block's content hash is the evidence itself.
SEMANTIC_REDERIVATION: Tuple[str, ...] = (
    "evidence_block_sha256",
)

# --------------------------------------------------------------------------- #
# Recorded, never deleted, never load-bearing for approval.
# --------------------------------------------------------------------------- #

#: State the approval process itself sets, or that says nothing about the
#: claim. ``founder_approved`` and ``published`` are outcomes of decisions, not
#: inputs to them -- hashing them would make an approval unable to match the
#: record it approves. ``non_inferences`` is the reader explaining what it
#: refused to guess: real prose, but a restatement of the withholdings that
#: are already bound above.
PROVENANCE_TOP_LEVEL: Tuple[str, ...] = (
    "founder_approved",
    "published",
    "non_inferences",
    "source_run",
    "provenance",
    "rederivation",
)

#: How the bytes were obtained. Change the provider, re-run the capture, move
#: the repository: the claim is untouched.
PROVENANCE_PROVENANCE: Tuple[str, ...] = (
    "retrieved_at",
    "capture_method",
    "provider",
    "reader",
    "raw_pointer",
    "obs_id",
)

#: How the reading was produced. ``reader_commit`` is the field that caused
#: this module to exist. ``previous_facts`` is a historical record of an
#: earlier reader's output -- interesting, auditable, and not the approved
#: claim.
PROVENANCE_REDERIVATION: Tuple[str, ...] = (
    "superseded_by",
    "derivation",
    "reader_commit",
    "evidence_block_path",
    "previous_facts",
    "previous_withheld_fields",
)


def _stable(value: Any) -> str:
    return json.dumps(value, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False, default=str)


def _sorted_evidence(entries: Iterable[Mapping]) -> Tuple:
    """Evidence as a SET, not a sequence.

    Re-ordering the array is not a change to what is cited; adding, removing or
    editing a quote is. Sorting by the canonical rendering gives the first
    without giving up the second.
    """
    return tuple(sorted(
        (_stable({"quote": entry.get("quote", ""),
                  "location": entry.get("location", ""),
                  "field_refs": sorted(entry.get("field_refs") or ())})
         for entry in entries if isinstance(entry, Mapping))))


def unclassified_fields(record: Mapping) -> Dict[str, Tuple[str, ...]]:
    """Any key in this record that neither list mentions.

    A new field is a question -- is this part of the claim? -- and nobody but a
    person can answer it. Until they do, this reports it and the caller refuses
    to hash.
    """
    known_top = set(SEMANTIC_TOP_LEVEL) | set(PROVENANCE_TOP_LEVEL)
    known_prov = set(SEMANTIC_PROVENANCE) | set(PROVENANCE_PROVENANCE)
    known_reder = set(SEMANTIC_REDERIVATION) | set(PROVENANCE_REDERIVATION)
    out = {
        "record": tuple(sorted(set(record) - known_top)),
        "provenance": tuple(sorted(set(record.get("provenance") or {})
                                   - known_prov)),
        "rederivation": tuple(sorted(set(record.get("rederivation") or {})
                                     - known_reder)),
    }
    return {where: names for where, names in out.items() if names}


def semantic_projection(record: Mapping) -> Dict:
    """The part of a store row a founder approval is a statement about."""
    unclassified = unclassified_fields(record)
    if unclassified:
        raise ValueError(
            "%s carries fields classified as neither semantic nor provenance: "
            "%s. Classify them in approval_binding before any approval binds "
            "to this record -- an unclassified field is either a tamper hole "
            "or a spurious invalidation, and guessing which is not available."
            % (record.get("identity_key", "<unknown>"), unclassified))

    provenance = record.get("provenance") or {}
    rederivation = record.get("rederivation") or {}
    projection: Dict[str, Any] = {
        name: record.get(name) for name in SEMANTIC_TOP_LEVEL
        if name != "evidence"
    }
    projection["evidence"] = list(_sorted_evidence(record.get("evidence") or ()))
    projection["source"] = {name: provenance.get(name)
                            for name in SEMANTIC_PROVENANCE}
    projection["evidence_identity"] = {name: rederivation.get(name)
                                       for name in SEMANTIC_REDERIVATION}
    return projection


def semantic_hash(record: Mapping) -> str:
    """The durable identity of an approved claim."""
    return "sha256:%s" % hashlib.sha256(
        _stable(semantic_projection(record)).encode("utf-8")).hexdigest()


def semantic_difference(before: Mapping, after: Mapping) -> Dict[str, Dict]:
    """Which parts of the approved meaning moved, field by field.

    Used to prove a rebinding rather than assert it: a migration that cannot
    show an empty difference has not shown the meaning is unchanged.
    """
    left, right = semantic_projection(before), semantic_projection(after)
    return {key: {"before": left.get(key), "after": right.get(key)}
            for key in sorted(set(left) | set(right))
            if _stable(left.get(key)) != _stable(right.get(key))}
