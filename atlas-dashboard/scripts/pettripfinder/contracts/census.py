"""``ptf-market-identity-census/1.1`` -- the roster of a market's identities.

Two names describe this shape in the corpus today --
``ptf-market-identity-census/1.0`` (Cleveland) and ``ptf-identity-census/1.0``
(Dayton, Cincinnati) -- for records that are structurally the same. One name is
frozen; both legacy names are read.

The three-axis state model
--------------------------
Dayton's separation of identity, lodging and policy is adopted as canonical,
because it is what lets a census row be HONEST about an unresolved policy
instead of pretending verification:

    identity_state   is this a real, distinct property?
    lodging_state    is it in category?
    policy_state     what do we know about pets?

``policy_state`` is ADVISORY and no gate may read it. The partition is the
authority on disposition. Dayton carries three stale policy annotations today,
which is precisely why a build must not trust one -- but a gate may still
assert that the annotation is CONSISTENT with the partition, which turns a
comment into a checked artifact.

What 1.1 adds
-------------
``identity_key`` (the canonical join key), ``market_id`` on every row
(ownership is explicit, never inferred from a filename -- defaulting an unowned
record to the market being asked once made every Columbus exclusion count as
Cleveland's), ``assignment_value`` beside ``assignment_basis``, and
``collision_state``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Mapping, Sequence, Set, Tuple

from scripts.pettripfinder.contracts import enums
from scripts.pettripfinder.contracts.identity_key import (
    IdentityKeyError, is_canonical_key, ptf_identity_key,
)
from scripts.pettripfinder.contracts.policy_schema import Issue

SCHEMA = enums.CENSUS_SCHEMA

#: Fields 1.1 requires on every census row.
REQUIRED_ROW_FIELDS: Tuple[str, ...] = (
    "identity_key", "canonical_name", "slug", "market_id", "city", "state",
    "identity_state", "lodging_state", "policy_state",
)


@dataclass(frozen=True)
class CensusRow:
    """One market identity."""

    identity_key: str
    canonical_name: str
    slug: str
    market_id: str
    city: str
    state: str
    postal_code: str
    identity_state: str
    lodging_state: str
    policy_state: str
    corridor: str = ""
    assignment_basis: str = ""
    assignment_value: str = ""
    collision_state: str = enums.COLLISION_NONE


def row_from_mapping(row: Mapping) -> CensusRow:
    """Read a census row, deriving the identity key when absent.

    Derivation is a READ-TIME convenience for surveying legacy documents. It is
    not a migration: nothing here writes the derived key back.
    """
    name = row.get("canonical_name") or ""
    key = row.get("identity_key") or ""
    if not key and name:
        try:
            key = ptf_identity_key(name)
        except IdentityKeyError:
            key = ""
    return CensusRow(
        identity_key=key,
        canonical_name=name,
        slug=row.get("slug") or "",
        market_id=row.get("market_id") or "",
        city=row.get("city") or "",
        state=row.get("state") or "",
        postal_code=(row.get("postal_code") or "")[:5],
        identity_state=row.get("identity_state") or "",
        lodging_state=row.get("lodging_state") or "",
        policy_state=row.get("policy_state") or "",
        corridor=row.get("corridor") or "",
        assignment_basis=row.get("assignment_basis")
        or row.get("corridor_basis") or "",
        assignment_value=row.get("assignment_value") or "",
        collision_state=row.get("collision_state") or enums.COLLISION_NONE,
    )


def identity_keys(document: Mapping) -> Set[str]:
    """The set of identity keys a census document declares."""
    return {row_from_mapping(r).identity_key
            for r in (document.get("hotels") or ())
            if isinstance(r, Mapping)}


def validate(document: Mapping, *, market_states: Sequence[str] = ()) -> Tuple[Issue, ...]:
    """Validate a census document at 1.1.

    ``market_states`` is the market's declared ``states`` list. When supplied,
    every row's state must be one of them -- the check that stops sixteen
    Kentucky and nine Indiana properties publishing as Ohio because the market
    is called Cincinnati.
    """
    out: List[Issue] = []
    if not isinstance(document, Mapping):
        return (Issue("census", "NOT_OBJECT", "census must be an object"),)

    schema = document.get("schema")
    if schema != SCHEMA and schema not in enums.LEGACY_CENSUS_SCHEMAS:
        out.append(Issue("schema", "BAD_SCHEMA",
                         "expected %r, got %r" % (SCHEMA, schema)))
    if not document.get("market_id"):
        out.append(Issue("market_id", "MISSING_REQUIRED", "market_id is required"))

    hotels = document.get("hotels")
    if not isinstance(hotels, Sequence) or isinstance(hotels, (str, bytes)):
        out.append(Issue("hotels", "NOT_LIST", "hotels must be a list"))
        return tuple(out)

    declared = document.get("count")
    if not isinstance(declared, int) or isinstance(declared, bool):
        out.append(Issue("count", "MISSING_REQUIRED",
                         "count is the market's declared universe size"))
    elif declared != len(hotels):
        # A declared count that disagrees with the rows is the cheapest
        # possible signal that a document was edited in two places.
        out.append(Issue("count", "COUNT_MISMATCH",
                         "declares %d identities but carries %d rows"
                         % (declared, len(hotels))))

    market_id = document.get("market_id")
    allowed_states = {s for s in market_states}
    seen: Dict[str, int] = {}

    for index, raw in enumerate(hotels):
        path = "hotels[%d]" % index
        if not isinstance(raw, Mapping):
            out.append(Issue(path, "NOT_OBJECT", "a census row must be an object"))
            continue
        row = row_from_mapping(raw)

        for field_name in REQUIRED_ROW_FIELDS:
            if field_name == "identity_key":
                continue
            if not raw.get(field_name):
                out.append(Issue("%s.%s" % (path, field_name), "MISSING_REQUIRED",
                                 "%s is required" % field_name))

        if not raw.get("identity_key"):
            out.append(Issue(path + ".identity_key", "MISSING_REQUIRED",
                             "identity_key is the join key for every layer"))
        elif not is_canonical_key(raw["identity_key"]):
            out.append(Issue(path + ".identity_key", "NOT_CANONICAL",
                             "%r is not the output of ptf_identity_key/1.0"
                             % raw["identity_key"]))
        elif row.canonical_name and raw["identity_key"] != ptf_identity_key(
                row.canonical_name):
            out.append(Issue(path + ".identity_key", "KEY_NAME_MISMATCH",
                             "identity_key does not derive from canonical_name"))

        if row.market_id and market_id and row.market_id != market_id:
            out.append(Issue(path + ".market_id", "WRONG_MARKET",
                             "row claims %r inside %r's census"
                             % (row.market_id, market_id)))

        if row.lodging_state in enums.LODGING_AXIS_VIOLATIONS:
            # Whether a property takes pets has nothing to do with whether it
            # is a hotel. The remedy is to move the fact to policy_state and
            # restore the row's real lodging value.
            out.append(Issue(path + ".lodging_state", "AXIS_VIOLATION",
                             "%r is a POLICY fact in the lodging axis; it "
                             "belongs in policy_state as %r"
                             % (row.lodging_state,
                                enums.LODGING_AXIS_VIOLATIONS[row.lodging_state])))
        else:
            for field_name, vocabulary in (
                    ("identity_state", enums.IDENTITY_STATES),
                    ("lodging_state", enums.LODGING_STATES),
                    ("collision_state", enums.COLLISION_STATES)):
                value = getattr(row, field_name)
                if value and not enums.is_member(value, vocabulary):
                    out.append(Issue("%s.%s" % (path, field_name), "BAD_ENUM",
                                     "%r not in %s" % (value, list(vocabulary))))

        if row.policy_state and not enums.is_member(row.policy_state,
                                                    enums.CENSUS_POLICY_STATES):
            out.append(Issue(path + ".policy_state", "BAD_ENUM",
                             "%r not in %s" % (row.policy_state,
                                               list(enums.CENSUS_POLICY_STATES))))

        basis = enums.LEGACY_ASSIGNMENT_BASES.get(row.assignment_basis,
                                                 row.assignment_basis)
        if row.assignment_basis in enums.UNIMPLEMENTED_ASSIGNMENT_BASES:
            # A basis the assigner has no tier for can never be reproduced, so
            # the reproducibility gate can never pass while it stands.
            out.append(Issue(path + ".assignment_basis", "BASIS_NOT_IMPLEMENTED",
                             "%r is not a tier the assignment code can "
                             "produce, so this assignment is unreproducible by "
                             "construction" % row.assignment_basis))
        elif basis and not enums.is_member(basis, enums.ASSIGNMENT_BASES):
            out.append(Issue(path + ".assignment_basis", "BAD_ENUM",
                             "%r not in %s" % (row.assignment_basis,
                                               list(enums.ASSIGNMENT_BASES))))
        elif basis in (enums.BASIS_POSTAL_CODE, enums.BASIS_CITY_STATE) \
                and not row.assignment_value:
            # A basis without the value that fired it cannot be checked, and a
            # claim that cannot be checked is a claim that will be wrong --
            # 121 Cincinnati rows label themselves postal_code and seven of
            # them are human judgement.
            out.append(Issue(path + ".assignment_value", "MISSING_REQUIRED",
                             "record the value that actually fired the basis"))

        if allowed_states and row.state and row.state not in allowed_states:
            out.append(Issue(path + ".state", "STATE_NOT_IN_MARKET",
                             "%r is not among the market's declared states %s"
                             % (row.state, sorted(allowed_states))))

        if row.identity_key:
            seen[row.identity_key] = seen.get(row.identity_key, 0) + 1

    for key, count in sorted(seen.items()):
        if count > 1:
            out.append(Issue("hotels[%s]" % key, "DUPLICATE_IDENTITY",
                             "%d rows share this identity_key" % count))
    return tuple(out)
