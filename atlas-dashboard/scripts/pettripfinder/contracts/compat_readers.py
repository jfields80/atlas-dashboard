"""Read today's 1.0 and 1.1 records as schema 1.2, without rewriting a byte.

This module is the whole reason the migration can be additive. Every consumer
built on the frozen contracts reads through here, so the renderer, the
validators and the computation classifier can move to 1.2 while three markets'
committed authority stays exactly as it is until Phase F migrates it
deliberately, one market at a time.

The line this module will not cross
-----------------------------------
It performs only MECHANICAL transformations -- ones where the legacy form
determines the 1.2 form completely and no judgement is involved. Everything
else is REPORTED, never guessed:

    "$50.00"                  -> {"amount_cents": 5000, "currency": "USD"}
    "75 pounds"               -> {"value": 75.0, "unit": "lb"}
    "true"                    -> True
    "per room"                -> "per_room"
    "per room per night"      -> basis per_night + scope per_room
    {first_pet, second_pet}   -> ordinal entries

    weight_limit_operator: "combined"      -> REVIEW. The value is a scope
                                              token, so the record's real
                                              comparison is unknown; defaulting
                                              to lte admits an eighty-pound dog
                                              to a property that wrote "under
                                              80 pounds", and lt turns away one
                                              the hotel accepts. Both are
                                              guest-visible errors.
    withheld_fields: "prose"               -> REVIEW. The reason lives in the
                                              sentence. Assigning SOURCE_SILENT
                                              where the truth is
                                              SOURCE_CONTRADICTORY would
                                              publish "Not stated" over a known
                                              contradiction.
    species_allowed: "dogs, cats"          -> REVIEW.
    approval.decision: ""                  -> REVIEW.

A ``ReviewItem`` is not a failure. It is the honest output of a reader that
knows the difference between translating and deciding, and together they ARE
the Phase F queue.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from scripts.pettripfinder.contracts import enums
from scripts.pettripfinder.contracts.identity_key import (
    IdentityKeyError, ptf_identity_key,
)

#: "$50.00", "$50", "50.00 USD", "50"
_MONEY_RE = re.compile(r"^\s*\$?\s*(?P<amount>\d+(?:\.\d{1,2})?)\s*(?:USD)?\s*$",
                       re.IGNORECASE)

#: "75 pounds", "80 lb", "40.0 pounds", "20 lbs", "30 kg"
_WEIGHT_RE = re.compile(
    r"^\s*(?P<value>\d+(?:\.\d+)?)\s*(?P<unit>pounds?|lbs?|kilograms?|kgs?)\s*$",
    re.IGNORECASE)

_LB_WORDS = frozenset({"pound", "pounds", "lb", "lbs"})

_TRUE_WORDS = frozenset({"true", "yes"})
_FALSE_WORDS = frozenset({"false", "no"})


@dataclass(frozen=True)
class ReviewItem:
    """One thing a human must decide before this record can reach 1.2."""

    identity_key: str
    market_id: str
    field_path: str
    code: str
    detail: str
    legacy_value: str = ""

    def __str__(self) -> str:
        return "%s / %s: %s (%s)" % (self.identity_key, self.field_path,
                                     self.detail, self.code)


@dataclass
class ReadResult:
    """A record read as 1.2, plus what could not be read mechanically."""

    record: Dict[str, Any]
    review: List[ReviewItem] = field(default_factory=list)


def parse_money(value: Any, currency: str = "USD") -> Optional[Dict[str, Any]]:
    """``"$50.00"`` -> integer cents. ``None`` when it is not money.

    Rounds through a string rather than float arithmetic: ``float("0.29") * 100``
    is 28.999999999999996, and a cent lost here is a cent wrong on a price.
    """
    if isinstance(value, Mapping) and "amount_cents" in value:
        return dict(value)
    if isinstance(value, (int, float)) and not isinstance(value, bool):
        return {"amount_cents": int(round(float(value) * 100)), "currency": currency}
    if not isinstance(value, str):
        return None
    match = _MONEY_RE.match(value)
    if not match:
        return None
    whole, _, frac = match.group("amount").partition(".")
    cents = int(whole) * 100 + int((frac + "00")[:2] or 0)
    return {"amount_cents": cents, "currency": currency}


def parse_weight(value: Any) -> Optional[Dict[str, Any]]:
    """``"75 pounds"`` / ``"80 lb"`` / ``"40.0 pounds"`` -> value + unit."""
    if isinstance(value, Mapping) and "value" in value:
        return dict(value)
    if not isinstance(value, str):
        return None
    match = _WEIGHT_RE.match(value)
    if not match:
        return None
    word = match.group("unit").lower()
    return {"value": float(match.group("value")),
            "unit": enums.UNIT_LB if word in _LB_WORDS else enums.UNIT_KG}


def parse_bool(value: Any) -> Optional[bool]:
    """``"true"`` -> ``True``. ``None`` when the value is not a boolean."""
    if isinstance(value, bool):
        return value
    if isinstance(value, str):
        lowered = value.strip().lower()
        if lowered in _TRUE_WORDS:
            return True
        if lowered in _FALSE_WORDS:
            return False
    return None


def parse_int(value: Any) -> Optional[int]:
    if isinstance(value, int) and not isinstance(value, bool):
        return value
    if isinstance(value, str) and value.strip().isdigit():
        return int(value.strip())
    return None


def parse_fee_scope(value: Any) -> Tuple[Optional[str], bool]:
    """``("per_room", True)`` when translatable.

    The second element says whether the value was RECOGNISED at all. A legacy
    sentinel such as ``"unknown"`` returns ``(None, True)`` -- recognised, and
    correctly translated to absence. An unrecognised string returns
    ``(None, False)`` so the caller can raise it for review.
    """
    if not isinstance(value, str):
        return None, False
    lowered = value.strip().lower()
    if lowered in enums.LEGACY_SCOPE_ABSENT:
        return None, True
    if lowered in enums.LEGACY_FEE_SCOPES:
        return enums.LEGACY_FEE_SCOPES[lowered], True
    return None, False


def decompose_fee_basis(value: Any) -> Tuple[Optional[str], Optional[str],
                                             Optional[int], bool]:
    """Split a legacy basis into ``(basis, scope, pet_allowance, recognised)``.

    Seven Columbus and Cleveland records carry scope and a pet-count qualifier
    inside the basis string. ``"per night for up to 2 pets"`` is three facts,
    and the third is the one the renderer had been recovering with a regex.
    """
    if not isinstance(value, str):
        return None, None, None, False
    lowered = " ".join(value.strip().lower().split())
    if lowered in enums.LEGACY_FEE_BASES:
        basis, scope, allowance = enums.LEGACY_FEE_BASES[lowered]
        return basis, scope or None, allowance or None, True
    return None, None, None, False


def _legacy_operator(operator: Any) -> str:
    """A legacy weight operator, with absence read as inclusive.

    This is MECHANICAL, not a guess, and it is worth saying why -- the freeze
    that specified this work assumed every unoperated weight needed a human to
    re-read its quote, which would have put roughly a hundred records into a
    review queue they do not belong in.

    The convention is already established and already documented in the
    renderer that has been publishing these records for months
    (``hotel_profile.weight_phrase``): *"Absent operator means inclusive --
    what every labelled 'Maximum Pet Weight: N' has always meant -- so existing
    hotels read exactly as before."* An explicit ``lt`` is written only where a
    source said "under"; everything else is a stated maximum.

    So reading absence as ``lte`` PRESERVES the meaning these records already
    publish, which is exactly what the migration rule requires. Sending them to
    review would be the change, not the preservation.
    """
    mapped = enums.LEGACY_WEIGHT_OPERATORS.get(
        operator if isinstance(operator, str) else "")
    return mapped or enums.OP_LTE


def _read_fee(facts: Mapping, out: Dict[str, Any], review: List[ReviewItem],
              ident: str, market: str) -> None:
    amount = parse_money(facts.get("pet_fee"))
    if amount is None:
        if facts.get("pet_fee") is not None:
            review.append(ReviewItem(ident, market, "facts.pet_fee",
                                     "UNPARSEABLE_MONEY",
                                     "cannot read as money",
                                     str(facts.get("pet_fee"))))
        return

    fee: Dict[str, Any] = dict(amount)

    basis, basis_scope, allowance, recognised = decompose_fee_basis(
        facts.get("fee_basis"))
    if facts.get("fee_basis") is not None and not recognised:
        review.append(ReviewItem(ident, market, "facts.fee_basis",
                                 "UNKNOWN_BASIS",
                                 "basis string is not in the decomposition "
                                 "table", str(facts.get("fee_basis"))))
    if basis:
        fee["basis"] = basis
    if allowance:
        fee["scope_pet_allowance"] = allowance

    scope, scope_recognised = parse_fee_scope(facts.get("fee_scope"))
    if facts.get("fee_scope") is not None and not scope_recognised:
        review.append(ReviewItem(ident, market, "facts.fee_scope",
                                 "UNKNOWN_SCOPE", "scope value not recognised",
                                 str(facts.get("fee_scope"))))
    # An explicit fee_scope wins over one implied by a compound basis; they
    # agree everywhere in the corpus, and where they would not, the explicit
    # field is the one a human wrote on purpose.
    if scope:
        fee["scope"] = scope
    elif basis_scope:
        fee["scope"] = basis_scope

    out["pet_fee"] = fee


def _read_cap(node: Any, ident: str, market: str, path: str,
              review: List[ReviewItem]) -> Optional[Dict[str, Any]]:
    if not isinstance(node, Mapping):
        return None
    amount = parse_money(node.get("amount"))
    if amount is None:
        return None
    cap: Dict[str, Any] = dict(amount)
    basis, _, _, recognised = decompose_fee_basis(node.get("basis"))
    if basis:
        cap["basis"] = basis
    elif node.get("basis") and not recognised:
        review.append(ReviewItem(ident, market, path + ".basis", "UNKNOWN_BASIS",
                                 "cap basis not recognised", str(node.get("basis"))))
    # A cap NEVER inherits scope from the fee it caps, so nothing is filled in
    # here. Every legacy cap therefore arrives with qualifier_stated False and
    # goes to review -- which is correct: none of them recorded its scope, and
    # the corpus contains caps whose quote names a pet count the structure lost.
    cap["qualifier_stated"] = False
    review.append(ReviewItem(
        ident, market, path, "CAP_QUALIFIERS_INCOMPLETE",
        "cap carries no structured scope; re-read the evidence quote for "
        "scope, pet count and any night trigger",
        str(node.get("evidence_quote") or "")[:160]))
    return cap


def _read_weight(facts: Mapping, out: Dict[str, Any], review: List[ReviewItem],
                 ident: str, market: str) -> None:
    operator = facts.get("weight_limit_operator")
    individual = parse_weight(facts.get("weight_limit"))
    combined = parse_weight(facts.get("weight_limit_combined"))
    combined_op = facts.get("weight_limit_combined_operator")

    is_scope_token = operator == enums.LEGACY_COMBINED_SCOPE_TOKEN

    if individual is not None:
        if is_scope_token:
            # The value was never an individual limit at all: the overloaded
            # operator says it applies to the pets together. It moves to the
            # combined field, and its comparison is unknown.
            combined = combined or individual
            review.append(ReviewItem(
                ident, market, "facts.weight_limit_operator",
                "COMBINED_IN_OPERATOR_SLOT",
                "'combined' is a scope; the limit moves to "
                "combined_weight_limit and its lt/lte must be re-read from the "
                "evidence quote", "combined"))
        else:
            limit = dict(individual)
            limit["operator"] = _legacy_operator(operator)
            limit["scope"] = enums.WEIGHT_SCOPE_PER_PET
            out["weight_limit"] = limit
    elif facts.get("weight_limit") is not None:
        review.append(ReviewItem(ident, market, "facts.weight_limit",
                                 "UNPARSEABLE_WEIGHT", "cannot read as a weight",
                                 str(facts.get("weight_limit"))))

    if combined is not None:
        limit = dict(combined)
        limit["operator"] = _legacy_operator(combined_op)
        out["combined_weight_limit"] = limit

    species_limits = facts.get("species_weight_limits")
    if isinstance(species_limits, Mapping):
        converted: Dict[str, Any] = {}
        for name, rule in sorted(species_limits.items()):
            if not isinstance(rule, Mapping):
                continue
            parsed = parse_weight(rule.get("value"))
            if parsed is None:
                continue
            parsed["operator"] = _legacy_operator(rule.get("operator"))
            converted[name] = parsed
        if converted:
            out["species_weight_limits"] = converted


def _read_pet_schedule(node: Any, ident: str, market: str,
                       review: List[ReviewItem]) -> Optional[Dict[str, Any]]:
    """``{first_pet, second_pet}`` -> ordinal entries.

    Mechanical: the legacy shape's ordering IS the ordinal. What cannot be read
    mechanically is whether a rung is additive -- the legacy shape never
    recorded it, though the renderer's prose has been asserting it -- so every
    converted rung goes to review.
    """
    if not isinstance(node, Mapping):
        return None
    entries: List[Dict[str, Any]] = []
    for ordinal, key in ((1, "first_pet"), (2, "second_pet")):
        rung = node.get(key)
        if not isinstance(rung, Mapping):
            continue
        amount = parse_money(rung.get("amount"))
        if amount is None:
            continue
        entry: Dict[str, Any] = {"pet_ordinal": ordinal}
        entry.update(amount)
        basis, scope, _, _ = decompose_fee_basis(rung.get("basis"))
        if basis:
            entry["basis"] = basis
        if scope:
            entry["scope"] = scope
        entries.append(entry)
    if not entries:
        return None
    review.append(ReviewItem(
        ident, market, "facts.fee_pet_schedule.entries", "ADDITIVE_UNRECORDED",
        "the legacy schedule never recorded whether a rung is charged in "
        "addition to lower ordinals; confirm from the evidence quote", ""))
    return {"entries": entries}


def _read_species(facts: Mapping, ident: str, market: str,
                  review: List[ReviewItem]) -> None:
    """Species stays as REVIEW, always.

    Five prose spellings exist and the semantics are not mechanical: a page
    naming only "pets" must yield an EMPTY map, never dogs+cats, and two
    markets already record that judgement by hand in their withholding
    reasons. Parsing the prose here would be exactly the inference the contract
    forbids.
    """
    if facts.get("species_allowed") is not None:
        review.append(ReviewItem(ident, market, "facts.species_allowed",
                                 "SPECIES_PROSE", "convert prose to a species "
                                 "state map under review",
                                 str(facts.get("species_allowed"))))
    if facts.get("cats_allowed") is not None:
        review.append(ReviewItem(ident, market, "facts.cats_allowed",
                                 "SPECIES_PROSE",
                                 "fold into the species map as an explicit "
                                 "cats state", str(facts.get("cats_allowed"))))


def _read_withheld(record: Mapping, ident: str, market: str,
                   review: List[ReviewItem]) -> Dict[str, Any]:
    """Carry the legacy withholding forward, flagging every prose entry.

    Cleveland's 20 and Dayton's 46 entries are flat prose with no reason code.
    The reason lives in the sentence, and a machine assigning SOURCE_SILENT
    where the truth is SOURCE_CONTRADICTORY would publish "Not stated" over a
    known contradiction -- so every one is raised.
    """
    out: Dict[str, Any] = {}
    for path, entry in sorted((record.get("withheld_fields") or {}).items()):
        if isinstance(entry, Mapping) and entry.get("reason_code"):
            out[path] = dict(entry)
            continue
        out[path] = {"reason_code": "", "reason": str(entry), "evidence_refs": []}
        review.append(ReviewItem(
            ident, market, "withheld_fields.%s" % path, "WITHHELD_PROSE",
            "assign a reason code, or drop the entry if it merely restates "
            "silence", str(entry)[:160]))

    facts = record.get("facts") or {}
    # Columbus's two fee-specific mechanisms are the same decision under
    # another name, and they already carry a machine-readable reason.
    for legacy_key, reason_code in (
            ("fee_conflict", enums.SOURCE_CONTRADICTORY),
            ("fee_withheld", enums.SCHEMA_CANNOT_REPRESENT)):
        node = facts.get(legacy_key)
        if not isinstance(node, Mapping):
            continue
        out["pet_fee"] = {
            "reason_code": reason_code,
            "reason": "; ".join(node.get("detail") or []) or str(node.get("reason") or ""),
            "evidence_refs": [],
        }
        review.append(ReviewItem(
            ident, market, "facts.%s" % legacy_key, "LEGACY_FEE_WITHHOLDING",
            "migrated to withheld_fields[pet_fee] as %s; attach evidence_refs"
            % reason_code, str(node.get("reason") or "")))
    return out


def _read_approval(record: Mapping, ident: str, market: str,
                   review: List[ReviewItem]) -> Dict[str, Any]:
    approval = record.get("approval")
    if not isinstance(approval, Mapping) or not (approval.get("decision") or "").strip():
        # 21 Columbus records carry a blank decision and 5 carry no approval
        # block at all. Neither is back-dated: the remediation is a review
        # performed today and recorded as LEGACY_BASELINE_REVIEWED.
        review.append(ReviewItem(
            ident, market, "approval.decision", "NO_APPROVAL_DECISION",
            "no recorded decision; re-review and record "
            "LEGACY_BASELINE_REVIEWED with today's date -- never back-date an "
            "approval nobody gave", ""))
        return {}

    decision = approval["decision"]
    mapped = enums.LEGACY_APPROVAL_DECISIONS.get(decision)
    if mapped is None:
        review.append(ReviewItem(ident, market, "approval.decision",
                                 "UNKNOWN_DECISION",
                                 "decision string not in the legacy map",
                                 str(decision)))
        return dict(approval)

    out = {"decision": mapped,
           "operator": approval.get("operator") or "",
           "approval_date": approval.get("approval_date") or ""}
    caveat = enums.LEGACY_APPROVAL_CAVEATS.get(decision)
    if caveat:
        # The qualified forms carry real information -- a tiered fee omitted, a
        # diagnostic acknowledged -- which survives rather than being flattened.
        out["caveats"] = [caveat]
    return out


def read_record(record: Mapping, *, market_id: str = "") -> ReadResult:
    """Read one legacy hotel record as in-memory 1.2."""
    review: List[ReviewItem] = []
    name = record.get("name") or record.get("key") or ""
    try:
        ident = ptf_identity_key(name)
    except IdentityKeyError:
        ident = str(record.get("key") or "<unkeyed>")
        review.append(ReviewItem(ident, market_id, "identity_key",
                                 "NO_IDENTITY_KEY",
                                 "name does not produce an identity key", str(name)))

    legacy = record.get("facts") or {}
    facts: Dict[str, Any] = {}

    allowed = parse_bool(legacy.get("pets_allowed"))
    if allowed is not None:
        facts["pets_allowed"] = allowed

    _read_fee(legacy, facts, review, ident, market_id)
    _read_weight(legacy, facts, review, ident, market_id)
    _read_species(legacy, ident, market_id, review)

    cap = _read_cap(legacy.get("fee_cap"), ident, market_id, "facts.fee_cap", review)
    if cap:
        facts["fee_cap"] = cap

    schedule = _read_pet_schedule(legacy.get("fee_pet_schedule"), ident,
                                 market_id, review)
    if schedule:
        facts["fee_pet_schedule"] = schedule

    tiers = legacy.get("fee_tiers")
    if isinstance(tiers, Sequence) and not isinstance(tiers, (str, bytes)):
        converted: List[Dict[str, Any]] = []
        for tier in tiers:
            if not isinstance(tier, Mapping):
                continue
            amount = parse_money(tier.get("amount"))
            if amount is None:
                continue
            new: Dict[str, Any] = dict(amount)
            new["condition_type"] = tier.get("condition_type") or enums.CONDITION_STAY_LENGTH_RANGE
            new["boundary_unit"] = tier.get("boundary_unit") or enums.BOUNDARY_NIGHTS
            new["basis_stated"] = bool(tier.get("basis_stated"))
            for key in ("condition_min", "condition_max"):
                value = parse_int(tier.get(key))
                if value is not None:
                    new[key] = value
            scope, _ = parse_fee_scope(tier.get("scope"))
            if scope:
                new["scope"] = scope
            # Every corpus tier says ONE_TIME_CHARGE, a value that discriminates
            # nothing. Role is what separates a replacement price from an
            # additional charge, and it has to be decided per tier.
            converted.append(new)
        if converted:
            facts["fee_tiers"] = converted
            review.append(ReviewItem(
                ident, market_id, "facts.fee_tiers[].role", "TIER_ROLE_UNSET",
                "legacy tiers carry no discriminating role; confirm each is a "
                "replacement price rather than an additional charge", ""))

    cleaning = legacy.get("cleaning_fee")
    if cleaning is not None:
        amount = parse_money(cleaning)
        if amount is not None:
            review.append(ReviewItem(
                ident, market_id, "facts.other_charges", "CLEANING_FEE_SHAPE",
                "a bare cleaning-fee amount needs an explicit refundable flag; "
                "never infer refundability from a heading", str(cleaning)))

    deposit = legacy.get("pet_deposit")
    if isinstance(deposit, Mapping) and parse_money(deposit.get("amount")):
        review.append(ReviewItem(
            ident, market_id, "facts.other_charges", "DEPOSIT_SHAPE",
            "confirm refundability from the quote before writing "
            "refundable_deposit -- 'Deposit Yes. $75 Non-refundable Fee' is a "
            "non-refundable fee", str(deposit.get("evidence_quote") or "")[:160]))

    for key in ("breed_restrictions", "unattended_policy",
                "reservation_requirement", "pet_room_restriction",
                "general_restrictions"):
        if isinstance(legacy.get(key), str) and legacy[key].strip():
            facts[key] = legacy[key]

    for key in ("weight_limit_stated_none", "breed_restrictions_stated_none"):
        value = parse_bool(legacy.get(key))
        if value is not None:
            facts[key] = value

    count = parse_int(legacy.get("pet_count_limit"))
    if count is not None:
        facts["pet_count_limit"] = count
    if legacy.get("pet_count_scope"):
        facts["pet_count_scope"] = legacy["pet_count_scope"]

    exception = legacy.get("service_animal_exception")
    statement: Dict[str, Any] = {}
    if exception is not None:
        statement = {"stated": parse_bool(exception) is True,
                     "charges_stated": enums.SERVICE_ANIMAL_NOT_ADDRESSED}
        review.append(ReviewItem(
            ident, market_id, "service_animal_statement", "SERVICE_ANIMAL_MOVED",
            "moved out of facts; recover the property's quote before claiming "
            "no_charge", str(exception)))

    withheld = _read_withheld(record, ident, market_id, review)
    approval = _read_approval(record, ident, market_id, review)

    out: Dict[str, Any] = {
        "identity_key": ident,
        "name": record.get("name") or "",
        "market_id": market_id,
        "facts": facts,
        "evidence": list(record.get("evidence") or []),
        "verification_state": record.get("verification_state") or "",
        "source_type": record.get("source_type") or "",
        "source_url": record.get("source_url") or "",
        "verified_at": record.get("verified_at") or "",
    }
    if withheld:
        out["withheld_fields"] = withheld
    if approval:
        out["approval"] = approval
    if statement:
        out["service_animal_statement"] = statement
    return ReadResult(record=out, review=review)


def read_package(package: Mapping) -> Tuple[Dict[str, Any], Tuple[ReviewItem, ...]]:
    """Read a whole ``hotel_policy_facts`` document as in-memory 1.2."""
    version = str(package.get("schema_version") or "")
    if version not in enums.LEGACY_POLICY_SCHEMA_VERSIONS \
            and not enums.is_canonical_policy_schema(version):
        raise ValueError("unsupported policy schema version %r" % version)

    market_id = package.get("market") or package.get("market_id") or ""
    records: List[Dict[str, Any]] = []
    review: List[ReviewItem] = []
    for record in package.get("hotels") or ():
        if not isinstance(record, Mapping):
            continue
        result = read_record(record, market_id=market_id)
        records.append(result.record)
        review.extend(result.review)

    return ({"schema_version": enums.POLICY_SCHEMA_VERSION,
             "market_id": market_id,
             "hotels": records},
            tuple(review))
