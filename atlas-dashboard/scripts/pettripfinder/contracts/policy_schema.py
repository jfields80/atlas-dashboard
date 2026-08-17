"""PetTripFinder Hotel Policy Schema 1.2 -- shape and structural validator.

Why 1.2
-------
The corpus holds 1.0 (Dayton) and 1.1 (Columbus, Cleveland) for what is
substantially the same record. A single additive successor above both is the
only version number that lets one reader handle every market without a
market-specific branch.

Why dicts rather than typed models
----------------------------------
These records are JSON on disk and JSON in every consumer, and the facts block
is sparse by design -- most properties state four or five of twenty-odd fields.
A model with twenty Optional attributes would spend its whole life being None,
and the surrounding renderer already reads ``f.get("fee_scope")``. Validation
is therefore a function over a dict rather than a constructor, and the
compatibility readers emit exactly the JSON a migration will later write.

The governing rule
------------------
ABSENCE IS SILENCE. No field is ever written as ``null``, ``""``, ``"unknown"``
or ``"unstated"`` to mean "the source did not say". A field the source did not
address is simply not there. This is the single rule that makes the withholding
contract possible: anything in ``withheld_fields`` is a deliberate editorial
decision, anything absent from both is silence, and no third state exists to be
confused with either.

Validation returns issues rather than raising, because Phase A needs to survey
all 156 published records and report on them. A caller that wants failure calls
``raise_for_issues``.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List, Mapping, Optional, Sequence, Tuple

from scripts.pettripfinder.contracts import enums
from scripts.pettripfinder.contracts.identity_key import is_canonical_key

SCHEMA_VERSION = enums.POLICY_SCHEMA_VERSION

#: Values that a legacy writer used to mean "unstated". Under 1.2 every one of
#: them is a defect, because each has to be filtered out by every consumer and
#: the consumer that forgets renders "unstated" to a guest as though the hotel
#: had said it.
_SILENCE_SENTINELS = frozenset({"", "unknown", "unstated", "n/a", "none",
                                "not stated", "null"})

#: Restriction fields carried as free prose. Verbatim-grounded, never parsed.
_PROSE_FIELDS = ("breed_restrictions", "unattended_policy",
                 "reservation_requirement", "pet_room_restriction",
                 "general_restrictions", "age_restriction")

_BOOL_FIELDS = ("pets_allowed", "weight_limit_stated_none",
                "breed_restrictions_stated_none")

#: Every fact key 1.2 recognises. An unknown key is reported rather than
#: ignored: a typo'd field name is invisible data, which is how twelve
#: ``fee_scope`` values reached no public surface at all.
KNOWN_FACT_FIELDS: Tuple[str, ...] = (
    "pets_allowed", "species", "species_other", "species_source_grade",
    "pet_fee", "fee_tiers", "fee_pet_schedule", "fee_cap", "other_charges",
    "weight_limit", "combined_weight_limit", "species_weight_limits",
    "weight_limit_stated_none", "dimension_constraints",
    "pet_count_limit", "pet_count_scope", "breed_restrictions_stated_none",
) + _PROSE_FIELDS


@dataclass(frozen=True)
class Issue:
    """One structural problem, addressed to a place in the record.

    ``path`` is dotted so a reviewer can find the field without reading the
    validator, and ``code`` is stable so the Phase F queue can group by defect
    class rather than by prose.
    """

    path: str
    code: str
    detail: str

    def __str__(self) -> str:
        return "%s: %s (%s)" % (self.path, self.detail, self.code)


class PolicySchemaError(ValueError):
    """A record that does not satisfy schema 1.2."""


def raise_for_issues(issues: Sequence[Issue], *, context: str = "") -> None:
    """Raise if any issue was found. The caller chooses when to be strict."""
    if not issues:
        return
    head = "%s: " % context if context else ""
    raise PolicySchemaError(
        "%s%d schema violation(s): %s"
        % (head, len(issues), "; ".join(str(i) for i in issues)))


# --------------------------------------------------------------------------
# primitives
# --------------------------------------------------------------------------

def money(amount_cents: int, currency: str = "USD") -> Dict[str, Any]:
    """Canonical money. Integer cents, never a float.

    The corpus stores ``"$50.00"`` -- a display string carrying a glyph. Cents
    keep the decimal exactness those strings already had while removing the
    parse, and integers keep binary rounding out of a number a guest is
    actually charged.
    """
    return {"amount_cents": int(amount_cents), "currency": currency}


def quantity(value: float, unit: str) -> Dict[str, Any]:
    """Canonical measured quantity: a number and the unit it is in.

    Stored in the unit the source used. No conversion happens at write time --
    a page stating kilograms is recorded in kilograms, and conversion is a
    display and comparison concern where it can be shown to the reader.
    """
    return {"value": value, "unit": unit}


def _is_number(value: Any) -> bool:
    # bool is an int subclass in Python, and a True that passes a number check
    # becomes 1 somewhere downstream.
    return isinstance(value, (int, float)) and not isinstance(value, bool)


def _check_money(node: Any, path: str, out: List[Issue]) -> None:
    if not isinstance(node, Mapping):
        out.append(Issue(path, "NOT_MONEY", "expected a money object"))
        return
    amount = node.get("amount_cents")
    if not isinstance(amount, int) or isinstance(amount, bool):
        out.append(Issue(path + ".amount_cents", "NOT_INT_CENTS",
                         "money must be integer cents, got %r" % (amount,)))
    elif amount < 0:
        out.append(Issue(path + ".amount_cents", "NEGATIVE_AMOUNT",
                         "amount may not be negative"))
    if not node.get("currency"):
        # A bare number is not money. The prose readers already enforce this
        # at extraction; the schema enforces it at rest.
        out.append(Issue(path + ".currency", "MISSING_CURRENCY",
                         "currency is mandatory"))


def _check_quantity(node: Any, path: str, units: Tuple[str, ...],
                    out: List[Issue]) -> None:
    if not isinstance(node, Mapping):
        out.append(Issue(path, "NOT_QUANTITY", "expected a quantity object"))
        return
    if not _is_number(node.get("value")):
        out.append(Issue(path + ".value", "NOT_NUMBER",
                         "value must be a number, got %r" % (node.get("value"),)))
    elif node["value"] <= 0:
        out.append(Issue(path + ".value", "NON_POSITIVE",
                         "a limit of zero or less is not a limit"))
    unit = node.get("unit")
    if not enums.is_member(unit or "", units):
        out.append(Issue(path + ".unit", "BAD_UNIT",
                         "unit %r not in %s" % (unit, list(units))))


def _check_operator(node: Mapping, path: str, out: List[Issue]) -> None:
    """Comparison operators only. This is where the overload is refused."""
    op = node.get("operator")
    if op == enums.LEGACY_COMBINED_SCOPE_TOKEN:
        out.append(Issue(
            path + ".operator", "SCOPE_IN_OPERATOR_SLOT",
            "'combined' is a scope, not a comparison; the record's real "
            "comparison must be re-read from its evidence quote"))
        return
    if not enums.is_member(op or "", enums.WEIGHT_OPERATORS):
        out.append(Issue(path + ".operator", "BAD_OPERATOR",
                         "operator %r not in %s" % (op, list(enums.WEIGHT_OPERATORS))))


def _check_enum(node: Mapping, key: str, vocabulary: Tuple[str, ...],
                path: str, out: List[Issue], *, required: bool = False) -> None:
    if key not in node:
        if required:
            out.append(Issue("%s.%s" % (path, key), "MISSING_REQUIRED",
                             "%s is required" % key))
        return
    value = node[key]
    if not enums.is_member(value if isinstance(value, str) else "", vocabulary):
        out.append(Issue("%s.%s" % (path, key), "BAD_ENUM",
                         "%r not in %s" % (value, list(vocabulary))))


def _check_bool(node: Mapping, key: str, path: str, out: List[Issue],
                *, required: bool = False) -> None:
    if key not in node:
        if required:
            out.append(Issue("%s.%s" % (path, key), "MISSING_REQUIRED",
                             "%s is required and is never inferred" % key))
        return
    if not isinstance(node[key], bool):
        out.append(Issue("%s.%s" % (path, key), "NOT_BOOL",
                         "expected a JSON boolean, got %r" % (node[key],)))


# --------------------------------------------------------------------------
# fee structures
# --------------------------------------------------------------------------

def _check_pet_fee(node: Any, out: List[Issue]) -> None:
    path = "facts.pet_fee"
    if not isinstance(node, Mapping):
        out.append(Issue(path, "NOT_OBJECT", "pet_fee must be an object"))
        return
    _check_money(node, path, out)
    _check_enum(node, "basis", enums.FEE_BASES, path, out)
    _check_enum(node, "scope", enums.FEE_SCOPES, path, out)
    _check_enum(node, "tax_relationship", enums.TAX_RELATIONSHIPS, path, out)
    if "refundable" in node:
        _check_bool(node, "refundable", path, out)
    allowance = node.get("scope_pet_allowance")
    if allowance is not None:
        if not isinstance(allowance, int) or isinstance(allowance, bool) or allowance < 1:
            out.append(Issue(path + ".scope_pet_allowance", "BAD_ALLOWANCE",
                             "pet allowance must be a positive integer"))
        elif node.get("scope") != enums.SCOPE_PER_ROOM:
            # "covers up to N pets" only means something for a room-scoped
            # charge; on a per-pet charge it is a contradiction.
            out.append(Issue(path + ".scope_pet_allowance", "ALLOWANCE_WITHOUT_ROOM_SCOPE",
                             "a pet allowance only qualifies a per_room charge"))


def _check_cap(node: Any, path: str, out: List[Issue]) -> None:
    """A cap must carry its own qualifiers or say it has none.

    Two prohibitions live here. A cap never inherits scope from the fee it
    caps, and a cap never covers two pets unless the source said so -- the
    corpus contains caps whose quote names a pet count that the structure lost,
    and a $105 ceiling shown against a first pet that stays free is a price the
    hotel never quoted.
    """
    if not isinstance(node, Mapping):
        out.append(Issue(path, "NOT_OBJECT", "fee cap must be an object"))
        return
    _check_money(node, path, out)
    _check_enum(node, "basis", enums.FEE_BASES, path, out)
    _check_enum(node, "scope", enums.FEE_SCOPES, path, out)
    _check_bool(node, "qualifier_stated", path, out, required=True)
    for int_key in ("applies_to_pet_count", "applies_to_pet_ordinal",
                    "trigger_max_nights"):
        value = node.get(int_key)
        if value is not None and (not isinstance(value, int)
                                  or isinstance(value, bool) or value < 1):
            out.append(Issue("%s.%s" % (path, int_key), "BAD_QUALIFIER",
                             "%s must be a positive integer" % int_key))


def _check_tier(node: Any, index: int, out: List[Issue]) -> None:
    path = "facts.fee_tiers[%d]" % index
    if not isinstance(node, Mapping):
        out.append(Issue(path, "NOT_OBJECT", "a tier must be an object"))
        return
    _check_money(node, path, out)
    # role is what separates a replacement price from an additional charge.
    # Without it, "$100 pet fee + $200 cleaning fee" renders as "$100-$200".
    _check_enum(node, "role", enums.TIER_ROLES, path, out, required=True)
    _check_enum(node, "condition_type", enums.TIER_CONDITION_TYPES, path, out,
                required=True)
    _check_enum(node, "boundary_unit", enums.TIER_BOUNDARY_UNITS, path, out,
                required=True)
    _check_enum(node, "basis", enums.FEE_BASES, path, out)
    _check_enum(node, "scope", enums.FEE_SCOPES, path, out)
    _check_bool(node, "basis_stated", path, out, required=True)
    lo, hi = node.get("condition_min"), node.get("condition_max")
    for key, value in (("condition_min", lo), ("condition_max", hi)):
        if value is not None and (not isinstance(value, int)
                                  or isinstance(value, bool) or value < 1):
            out.append(Issue("%s.%s" % (path, key), "BAD_BOUNDARY",
                             "%s must be a positive integer" % key))
    if isinstance(lo, int) and isinstance(hi, int) and not isinstance(lo, bool) \
            and not isinstance(hi, bool) and hi < lo:
        out.append(Issue(path, "INVERTED_RANGE",
                         "condition_max %d is below condition_min %d" % (hi, lo)))


def _check_pet_schedule(node: Any, out: List[Issue]) -> None:
    """Ordinal rungs, each able to carry the cap that bounds IT.

    The legacy ``{first_pet, second_pet}`` shape is positional, stops at two
    animals, and gives no rung anywhere to put its own ceiling -- so a cap that
    belongs to the second pet ends up at record level, where the renderer shows
    it against the first.
    """
    path = "facts.fee_pet_schedule"
    if not isinstance(node, Mapping):
        out.append(Issue(path, "NOT_OBJECT", "fee_pet_schedule must be an object"))
        return
    entries = node.get("entries")
    if not isinstance(entries, Sequence) or isinstance(entries, (str, bytes)):
        out.append(Issue(path + ".entries", "NOT_LIST",
                         "entries must be a list of ordinal rungs"))
        return
    seen: List[int] = []
    for index, entry in enumerate(entries):
        entry_path = "%s.entries[%d]" % (path, index)
        if not isinstance(entry, Mapping):
            out.append(Issue(entry_path, "NOT_OBJECT", "a rung must be an object"))
            continue
        ordinal = entry.get("pet_ordinal")
        if not isinstance(ordinal, int) or isinstance(ordinal, bool) or ordinal < 1:
            out.append(Issue(entry_path + ".pet_ordinal", "BAD_ORDINAL",
                             "pet_ordinal must be a positive integer"))
        else:
            seen.append(ordinal)
        _check_money(entry, entry_path, out)
        _check_enum(entry, "basis", enums.FEE_BASES, entry_path, out)
        _check_enum(entry, "scope", enums.FEE_SCOPES, entry_path, out)
        # additive says whether this rung is charged ON TOP of lower ordinals.
        # The renderer already says "an additional $15" in prose; without the
        # boolean nothing else can know that.
        _check_bool(entry, "additive", entry_path, out, required=True)
        if "cap" in entry:
            _check_cap(entry["cap"], entry_path + ".cap", out)
    if len(set(seen)) != len(seen):
        out.append(Issue(path + ".entries", "DUPLICATE_ORDINAL",
                         "two rungs claim the same pet_ordinal"))


def _check_other_charges(node: Any, out: List[Issue]) -> None:
    path = "facts.other_charges"
    if not isinstance(node, Sequence) or isinstance(node, (str, bytes)):
        out.append(Issue(path, "NOT_LIST", "other_charges must be a list"))
        return
    for index, charge in enumerate(node):
        charge_path = "%s[%d]" % (path, index)
        if not isinstance(charge, Mapping):
            out.append(Issue(charge_path, "NOT_OBJECT", "a charge must be an object"))
            continue
        _check_money(charge, charge_path, out)
        _check_enum(charge, "kind", enums.OTHER_CHARGE_KINDS, charge_path, out,
                    required=True)
        _check_enum(charge, "basis", enums.FEE_BASES, charge_path, out)
        # Never infer refundability from a charge kind. A contingent charge
        # may be stated while the source says nothing about refundability;
        # absence means SOURCE_SILENT, never false.
        _check_bool(charge, "refundable", charge_path, out, required=False)
        _check_bool(charge, "conditional", charge_path, out, required=False)
        if charge.get("conditional") is True:
            trigger = charge.get("trigger")
            if not isinstance(trigger, str) or not trigger.strip():
                out.append(Issue(charge_path + ".trigger", "MISSING_REQUIRED",
                                 "a conditional charge needs its source-stated trigger"))


# --------------------------------------------------------------------------
# size structures
# --------------------------------------------------------------------------

def _check_weight_limit(node: Any, out: List[Issue]) -> None:
    path = "facts.weight_limit"
    if not isinstance(node, Mapping):
        out.append(Issue(path, "NOT_OBJECT", "weight_limit must be an object"))
        return
    _check_quantity(node, path, enums.WEIGHT_UNITS, out)
    _check_operator(node, path, out)
    _check_enum(node, "scope", enums.WEIGHT_SCOPES, path, out, required=True)


def _check_combined_weight(node: Any, out: List[Issue]) -> None:
    path = "facts.combined_weight_limit"
    if not isinstance(node, Mapping):
        out.append(Issue(path, "NOT_OBJECT",
                         "combined_weight_limit must be an object"))
        return
    _check_quantity(node, path, enums.WEIGHT_UNITS, out)
    _check_operator(node, path, out)
    if "scope" in node:
        # The field name IS the scope. A scope key here would let a combined
        # limit claim to be per-pet, which is the overload in a new costume.
        out.append(Issue(path + ".scope", "REDUNDANT_SCOPE",
                         "a combined limit's scope is its field name; remove "
                         "the scope key"))


def _check_dimensions(node: Any, out: List[Issue]) -> None:
    path = "facts.dimension_constraints"
    if not isinstance(node, Sequence) or isinstance(node, (str, bytes)):
        out.append(Issue(path, "NOT_LIST", "dimension_constraints must be a list"))
        return
    for index, constraint in enumerate(node):
        c_path = "%s[%d]" % (path, index)
        if not isinstance(constraint, Mapping):
            out.append(Issue(c_path, "NOT_OBJECT", "expected an object"))
            continue
        _check_quantity(constraint, c_path, enums.DIMENSION_UNITS, out)
        _check_operator(constraint, c_path, out)
        _check_enum(constraint, "axis", enums.DIMENSION_AXES, c_path, out,
                    required=True)


# --------------------------------------------------------------------------
# species
# --------------------------------------------------------------------------

def _check_species(node: Any, facts: Mapping, out: List[Issue]) -> None:
    path = "facts.species"
    if not isinstance(node, Mapping):
        out.append(Issue(path, "NOT_OBJECT", "species must be a state map"))
        return
    grades = facts.get("species_source_grade") or {}
    for name, state in sorted(node.items()):
        if not enums.is_member(state if isinstance(state, str) else "",
                               enums.SPECIES_STATES):
            out.append(Issue("%s.%s" % (path, name), "BAD_ENUM",
                             "%r not in %s" % (state, list(enums.SPECIES_STATES))))
            continue
        grade = grades.get(name)
        if grade is None:
            continue
        if not enums.is_member(grade, enums.SOURCE_GRADES):
            out.append(Issue("facts.species_source_grade.%s" % name, "BAD_ENUM",
                             "%r not in %s" % (grade, list(enums.SOURCE_GRADES))))
        elif (grade not in enums.FIRST_PARTY_GRADES
              and state == enums.SPECIES_ACCEPTED):
            # Aggregators over-report acceptance. A restrictive third-party
            # claim is safe to surface with attribution; a permissive one would
            # let lower-grade evidence write a fact the property never stated.
            out.append(Issue("%s.%s" % (path, name), "LOW_GRADE_ACCEPTANCE",
                             "a %s source may restrict but never permit a "
                             "species" % grade))


# --------------------------------------------------------------------------
# top level
# --------------------------------------------------------------------------

def validate_facts(facts: Mapping) -> Tuple[Issue, ...]:
    """Structural validation of a 1.2 ``facts`` block."""
    out: List[Issue] = []
    if not isinstance(facts, Mapping):
        return (Issue("facts", "NOT_OBJECT", "facts must be an object"),)

    for key, value in sorted(facts.items()):
        if key not in KNOWN_FACT_FIELDS:
            out.append(Issue("facts.%s" % key, "UNKNOWN_FIELD",
                             "not a schema 1.2 fact field"))
        if value is None:
            out.append(Issue("facts.%s" % key, "NULL_FOR_SILENCE",
                             "silence is absence; remove the key"))
        elif isinstance(value, str) and value.strip().lower() in _SILENCE_SENTINELS:
            out.append(Issue("facts.%s" % key, "SENTINEL_FOR_SILENCE",
                             "%r is a sentinel for silence; remove the key" % value))

    for key in _BOOL_FIELDS:
        if key in facts:
            _check_bool(facts, key, "facts", out)

    if "species" in facts:
        _check_species(facts["species"], facts, out)
    if "pet_fee" in facts:
        _check_pet_fee(facts["pet_fee"], out)
    if "fee_tiers" in facts:
        tiers = facts["fee_tiers"]
        if not isinstance(tiers, Sequence) or isinstance(tiers, (str, bytes)):
            out.append(Issue("facts.fee_tiers", "NOT_LIST", "fee_tiers must be a list"))
        else:
            for index, tier in enumerate(tiers):
                _check_tier(tier, index, out)
    if "fee_pet_schedule" in facts:
        _check_pet_schedule(facts["fee_pet_schedule"], out)
    if "fee_cap" in facts:
        _check_cap(facts["fee_cap"], "facts.fee_cap", out)
    if "other_charges" in facts:
        _check_other_charges(facts["other_charges"], out)
    if "weight_limit" in facts:
        _check_weight_limit(facts["weight_limit"], out)
    if "combined_weight_limit" in facts:
        _check_combined_weight(facts["combined_weight_limit"], out)
    if "dimension_constraints" in facts:
        _check_dimensions(facts["dimension_constraints"], out)
    if "species_weight_limits" in facts:
        limits = facts["species_weight_limits"]
        if not isinstance(limits, Mapping):
            out.append(Issue("facts.species_weight_limits", "NOT_OBJECT",
                             "expected a map of species to limits"))
        else:
            for name, limit in sorted(limits.items()):
                p = "facts.species_weight_limits.%s" % name
                if not isinstance(limit, Mapping):
                    out.append(Issue(p, "NOT_OBJECT", "expected an object"))
                    continue
                _check_quantity(limit, p, enums.WEIGHT_UNITS, out)
                _check_operator(limit, p, out)

    count = facts.get("pet_count_limit")
    if count is not None and (not isinstance(count, int)
                              or isinstance(count, bool) or count < 1):
        out.append(Issue("facts.pet_count_limit", "BAD_COUNT",
                         "pet_count_limit must be a positive integer"))

    for key in _PROSE_FIELDS:
        if key in facts and not isinstance(facts[key], str):
            out.append(Issue("facts.%s" % key, "NOT_STRING",
                             "%s is free prose" % key))

    # An explicit "no weight limit" is a stated FACT, not silence -- but it
    # cannot coexist with a limit, because one of the two is then wrong.
    if facts.get("weight_limit_stated_none") is True and "weight_limit" in facts:
        out.append(Issue("facts.weight_limit_stated_none", "CONTRADICTS_LIMIT",
                         "the record states both no weight limit and a weight limit"))

    return tuple(out)


def validate_record(record: Mapping) -> Tuple[Issue, ...]:
    """Structural validation of one 1.2 hotel record, envelope included.

    Cross-contract checks that belong to other modules -- withholding
    disjointness, evidence sufficiency, computation-class agreement -- are NOT
    performed here. Each contract validates its own subject, so a caller can
    tell which contract a record failed.
    """
    out: List[Issue] = []
    if not isinstance(record, Mapping):
        return (Issue("record", "NOT_OBJECT", "record must be an object"),)

    key = record.get("identity_key")
    if not key:
        out.append(Issue("identity_key", "MISSING_REQUIRED",
                         "identity_key is the join key for every layer"))
    elif not is_canonical_key(key):
        out.append(Issue("identity_key", "NOT_CANONICAL",
                         "%r is not the output of ptf_identity_key/1.0" % key))

    if not record.get("name"):
        out.append(Issue("name", "MISSING_REQUIRED", "name is required"))

    cls = record.get("computation_class")
    if cls is not None and not enums.is_member(cls, enums.COMPUTATION_CLASSES):
        out.append(Issue("computation_class", "BAD_ENUM",
                         "%r not in %s" % (cls, list(enums.COMPUTATION_CLASSES))))

    statement = record.get("service_animal_statement")
    if statement is not None:
        if not isinstance(statement, Mapping):
            out.append(Issue("service_animal_statement", "NOT_OBJECT",
                             "expected an object"))
        else:
            _check_bool(statement, "stated", "service_animal_statement", out,
                        required=True)
            _check_enum(statement, "charges_stated",
                        enums.SERVICE_ANIMAL_CHARGE_STATES,
                        "service_animal_statement", out, required=True)

    # A legal access category must not sit in the commercial-terms namespace:
    # a weight limit beside it invites something to apply one to the other.
    if isinstance(record.get("facts"), Mapping) \
            and "service_animal_exception" in record["facts"]:
        out.append(Issue("facts.service_animal_exception", "MISPLACED_FIELD",
                         "service-animal statements belong in "
                         "service_animal_statement, outside facts"))

    out.extend(validate_facts(record.get("facts") or {}))
    return tuple(out)


def validate_package(package: Mapping) -> Tuple[Issue, ...]:
    """Validate a whole ``hotel_policy_facts`` document at 1.2."""
    out: List[Issue] = []
    if not isinstance(package, Mapping):
        return (Issue("package", "NOT_OBJECT", "package must be an object"),)

    version = package.get("schema_version")
    if version != SCHEMA_VERSION:
        out.append(Issue("schema_version", "BAD_VERSION",
                         "expected %r, got %r" % (SCHEMA_VERSION, version)))
    if not package.get("market_id"):
        out.append(Issue("market_id", "MISSING_REQUIRED",
                         "ownership is explicit, never inferred from a filename"))

    hotels = package.get("hotels")
    if not isinstance(hotels, Sequence) or isinstance(hotels, (str, bytes)):
        out.append(Issue("hotels", "NOT_LIST", "hotels must be a list"))
        return tuple(out)

    seen: Dict[str, int] = {}
    for index, record in enumerate(hotels):
        label = (record.get("identity_key") or record.get("key") or index) \
            if isinstance(record, Mapping) else index
        for issue in validate_record(record):
            out.append(Issue("hotels[%s].%s" % (label, issue.path), issue.code,
                             issue.detail))
        if isinstance(record, Mapping) and record.get("identity_key"):
            seen[record["identity_key"]] = seen.get(record["identity_key"], 0) + 1

    for key, count in sorted(seen.items()):
        if count > 1:
            out.append(Issue("hotels[%s]" % key, "DUPLICATE_IDENTITY",
                             "%d records share this identity_key" % count))
    return tuple(out)
