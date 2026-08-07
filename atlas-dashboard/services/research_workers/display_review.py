"""PTF-DISPLAY review -- approving a seed DISPLAY ROW, not a pet policy.

Deliberately a separate contract from ``machine_capture_review``. The two answer
different questions about different evidence:

  * a machine-review approval says *this is what the hotel's official page states
    about pets*, bound to a capture of that policy;
  * a display approval says *this name, address, phone and URL are appropriate to
    publish*, bound to identity evidence and to the policy approval it will be
    shown beside.

Reusing the policy contract for both would let one reviewer's judgement about a
street address travel under a hash that certifies a fee. So a display decision
binds BOTH hashes -- the policy record and the policy approval current at the
time -- and goes stale the moment either moves.

The register is append-only. A correction appends a superseding decision;
``current_decisions`` resolves each hotel to its last entry. Nothing is rewritten,
because a display row that was approved and later replaced is a fact about the
review, not an embarrassment to erase.
"""

from __future__ import annotations

import hashlib
import json
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

DISPLAY_REVIEW_SCHEMA = "ptf-display-review-decisions/1.0"
DISPLAY_INDEX_SCHEMA = "atlas-display-review-index/1.0"

DECISIONS_PATH = "launch_packages/pettripfinder/display_review_decisions.json"
INDEX_PATH = "docs/pettripfinder/artifact_indexes/display_review_index.json"

DISPLAY_APPROVED = "APPROVED"
DISPLAY_HELD = "HELD"
DISPLAY_DECISIONS = (DISPLAY_APPROVED, DISPLAY_HELD)

#: The exact seed display schema, in order. The hash is taken over this tuple, so
#: a column reordering cannot silently produce the same digest.
SEED_COLUMNS: Tuple[str, ...] = (
    "name", "category", "address", "city", "state", "postal_code", "phone",
    "website_url", "source_url", "source_type", "observed_at", "rating",
    "amenities", "pet_policy", "canonical",
)

#: Columns a row must carry a value for. ``phone`` is absent deliberately: three
#: already-published hotels ship without one, so requiring it here would reject
#: rows the live site already renders.
REQUIRED_COLUMNS: Tuple[str, ...] = (
    "name", "category", "address", "city", "state", "postal_code",
    "website_url", "source_url", "source_type", "observed_at", "pet_policy",
)

#: Columns that must stay empty unless evidence supports them. Nothing in the
#: current corpus fills any of these, and a rating invented for display would be
#: indistinguishable from one a source stated.
OPTIONAL_EMPTY_COLUMNS: Tuple[str, ...] = ("rating", "amenities", "canonical")

DISPLAY_REVIEW_STATEMENT = (
    "The reviewer confirms that the display name, address, phone, official URL, "
    "source classification, observed date and customer-facing policy summary are "
    "appropriate for publication and are bound to the cited evidence and current "
    "approved policy record."
)


class DisplayReviewError(ValueError):
    """Refusal to build, validate or record a display decision."""


def _canonical(payload) -> str:
    return json.dumps(payload, sort_keys=True, separators=(",", ":"),
                      ensure_ascii=False)


def display_row_hash(row: Mapping) -> str:
    """Deterministic digest over the exact 15 seed columns, in schema order.

    Taken over an ordered list of ``[column, value]`` pairs rather than a dict so
    the column ORDER is part of what is signed. Any key outside ``SEED_COLUMNS``
    -- the bookkeeping fields a candidate file carries -- is excluded, so adding
    provenance to the candidate artifact never changes the row's identity.
    """
    missing = [c for c in SEED_COLUMNS if c not in row]
    if missing:
        raise DisplayReviewError("row_missing_columns:%s" % ",".join(missing))
    body = [[c, str(row[c])] for c in SEED_COLUMNS]
    return "sha256:" + hashlib.sha256(_canonical(body).encode("utf-8")).hexdigest()


def row_problems(row: Mapping) -> Tuple[str, ...]:
    """Every gate this row fails, or an empty tuple. Never repairs anything."""
    found: List[str] = []
    for column in REQUIRED_COLUMNS:
        if not str(row.get(column, "")).strip():
            found.append("missing:%s" % column)
    for column in OPTIONAL_EMPTY_COLUMNS:
        if str(row.get(column, "")).strip():
            found.append("unexpected_value:%s" % column)
    if str(row.get("category", "")) != "pet-friendly-hotels":
        found.append("category_must_be_pet_friendly_hotels")
    return tuple(sorted(set(found)))


def _refuse_excluded_row(row: Mapping) -> None:
    """Raise ``DisplayReviewError`` if this display row's identity is excluded.

    The row carries name, address and postal code, so both the name and the
    street-identity bases apply here -- this is the boundary where a renamed
    property at a known excluded address is caught.

    Imported lazily so the review service does not take a module-level
    dependency on the publication layer.
    """
    from scripts.pettripfinder.publication_guard import (
        PublicationBlockedError, assert_publishable)

    try:
        assert_publishable([{"name": row.get("name", ""),
                             "address": row.get("address", ""),
                             "postal_code": row.get("postal_code", ""),
                             "category": row.get("category", "")}],
                           check_collisions=False)
    except PublicationBlockedError as exc:
        block = exc.blocks[0]
        raise DisplayReviewError(
            "cannot approve an excluded identity:%s:%s (matched by %s)"
            % (block.get("exclusion_state", ""), block.get("exclusion_id", ""),
               block.get("match_basis", ""))) from exc


def build_decision(*, hotel_id: str, normalized_name: str, row: Mapping,
                   identity_evidence_hash: str, policy_source_record_hash: str,
                   policy_approval_hash: str, reviewer_id: str, reviewed_at: str,
                   decision: str, notes: str = "",
                   statement: str = DISPLAY_REVIEW_STATEMENT) -> dict:
    """One display decision, with its approval hash. Refuses rather than coerces."""
    if decision not in DISPLAY_DECISIONS:
        raise DisplayReviewError("decision_must_be_approved_or_held:%s" % decision)
    if statement != DISPLAY_REVIEW_STATEMENT:
        raise DisplayReviewError("the reviewer statement may not be altered")
    for name, value in (("hotel_id", hotel_id), ("normalized_name", normalized_name),
                        ("identity_evidence_hash", identity_evidence_hash),
                        ("policy_source_record_hash", policy_source_record_hash),
                        ("policy_approval_hash", policy_approval_hash),
                        ("reviewer_id", reviewer_id), ("reviewed_at", reviewed_at)):
        if not str(value or "").strip():
            raise DisplayReviewError("%s is required" % name)
    problems = row_problems(row)
    if problems and decision == DISPLAY_APPROVED:
        raise DisplayReviewError("cannot approve a row that fails its gates:%s"
                                 % ",".join(problems))
    if decision == DISPLAY_APPROVED:
        # PTF-EXCLUSIONS-002. An approved display row is the seed row a hotel
        # publishes with. Held rows are still recordable -- holding an excluded
        # identity is exactly what a reviewer should be able to do -- but it can
        # never be approved.
        _refuse_excluded_row(row)
    body = {
        "schema": DISPLAY_REVIEW_SCHEMA,
        "hotel_id": hotel_id,
        "normalized_name": normalized_name,
        "row": {c: str(row[c]) for c in SEED_COLUMNS},
        "display_row_hash": display_row_hash(row),
        "identity_evidence_hash": identity_evidence_hash,
        "policy_source_record_hash": policy_source_record_hash,
        "policy_approval_hash": policy_approval_hash,
        "reviewer_id": reviewer_id.strip(),
        "reviewed_at": reviewed_at.strip(),
        "decision": decision,
        "notes": notes,
        "statement": statement,
    }
    out = dict(body)
    out["approval_hash"] = "sha256:" + hashlib.sha256(
        _canonical(body).encode("utf-8")).hexdigest()
    return out


def rederive_approval_hash(decision: Mapping) -> str:
    """Recompute a stored decision's hash from its own content."""
    body = {k: v for k, v in dict(decision).items() if k != "approval_hash"}
    return "sha256:" + hashlib.sha256(_canonical(body).encode("utf-8")).hexdigest()


def empty_register() -> dict:
    return {"schema": DISPLAY_REVIEW_SCHEMA,
            "note": ("Append-only display-row review decisions. A correction is "
                     "appended as a superseding entry; nothing here is rewritten."),
            "decisions": []}


def append_decision(register: Mapping, decision: Mapping) -> dict:
    """A NEW register with one more entry. Never mutates an existing entry."""
    if decision.get("decision") not in DISPLAY_DECISIONS:
        raise DisplayReviewError("decision_must_be_approved_or_held:%s"
                                 % decision.get("decision"))
    if rederive_approval_hash(decision) != decision.get("approval_hash"):
        raise DisplayReviewError("approval_hash does not match its own content")
    existing = list(register.get("decisions") or [])
    if any(e["approval_hash"] == decision["approval_hash"] for e in existing):
        return dict(register, decisions=existing)          # idempotent re-append
    return dict(register, schema=register.get("schema", DISPLAY_REVIEW_SCHEMA),
                note=register.get("note", empty_register()["note"]),
                decisions=existing + [decision])


def current_decisions(register: Mapping) -> Dict[str, dict]:
    """hotel_id -> its LAST entry. Append order, so a superseder wins."""
    out: Dict[str, dict] = {}
    for entry in register.get("decisions") or []:
        out[entry["hotel_id"]] = entry
    return out


def build_index(register: Mapping, candidates: Sequence[Mapping],
                *, policy_state: Mapping[str, Mapping]) -> dict:
    """What a reviewer needs to trust the register, recomputed not remembered.

    ``policy_state`` maps hotel_id -> {"source_record_hash", "approval_hash"} as
    they stand NOW. A decision whose bound hashes differ from those is stale: the
    policy moved under a display approval that was granted against the old one.
    """
    current = current_decisions(register)
    by_id = {c["_hotel_id"]: c for c in candidates}
    approved, held, stale, mismatched, undecided = [], [], [], [], []
    for hotel_id, candidate in sorted(by_id.items()):
        entry = current.get(hotel_id)
        if entry is None:
            undecided.append(hotel_id)
            continue
        if entry["decision"] == DISPLAY_HELD:
            held.append(hotel_id)
        else:
            approved.append(hotel_id)
        if entry["display_row_hash"] != display_row_hash(candidate):
            stale.append(hotel_id)
        live = policy_state.get(hotel_id) or {}
        if (entry["policy_source_record_hash"] != live.get("source_record_hash")
                or entry["policy_approval_hash"] != live.get("approval_hash")):
            mismatched.append(hotel_id)
    seen: Dict[str, int] = {}
    for entry in register.get("decisions") or []:
        seen[entry["approval_hash"]] = seen.get(entry["approval_hash"], 0) + 1
    return {
        "schema": DISPLAY_INDEX_SCHEMA,
        "description": ("Git-safe state of the display-row review register. "
                        "Recomputed from the register and the current candidate "
                        "rows -- never a remembered total."),
        "totals": {
            "total_candidate_rows": len(by_id),
            "current_approved": len(approved),
            "current_held": len(held),
            "stale_approvals": len(stale),
            "duplicate_current_decisions": sum(1 for n in seen.values() if n > 1),
            "policy_hash_mismatches": len(mismatched),
            "candidates_without_a_current_decision": len(undecided),
            "register_entries": len(register.get("decisions") or []),
        },
        "stale": sorted(stale),
        "policy_hash_mismatched": sorted(mismatched),
        "undecided": sorted(undecided),
        "held": sorted(held),
        "approved": sorted(approved),
    }
