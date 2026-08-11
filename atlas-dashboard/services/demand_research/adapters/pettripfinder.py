"""PetTripFinder inventory adapter (AES-SEO-001 §7.1, §9 of Phase B, §22.2).

Maps the committed PetTripFinder launch-package structures —
``seed_businesses.csv`` rows and ``hotel_policy_facts.json`` records — into
the generic record form the Demand Mapping engine profiles. This module MAY
know PetTripFinder field semantics; the generic engine never does.

Design rules honored here:
* Core mapping functions accept already-loaded Python data so they are
  testable without filesystem access; the ``load_*`` helpers at the bottom
  are the only file readers, and they live in this service layer by law.
* Empty source values are OMITTED (missing), never emitted as empty text.
* Values whose format cannot be parsed deterministically are omitted —
  the adapter never fabricates or guesses (§20).
* Provenance is assigned honestly (§7 of the Phase-B scope): a policy fact
  backed by a per-field evidence entry is VERIFIED (or OPERATOR when the
  record's evidence is operator-supplied ``manual_evidence``); facts with
  no per-field evidence trail, and seed identity fields, are UNKNOWN.
* Multi-valued ``species_allowed`` text is exploded into deterministic
  boolean membership dimensions over the GLOBAL sorted member vocabulary,
  so "dogs" implies ``species_allowed:cats = false`` (false ≠ missing);
  records without the field omit all membership dimensions (missing). If
  the global vocabulary exceeds ``MAX_MEMBERSHIP_VALUES`` the field falls
  back to an opaque TEXT dimension instead of exploding (§8 of Phase B).
"""

from __future__ import annotations

import csv
import json
import re
from pathlib import Path
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from engines.demand_mapping.contracts.dimensions import DimensionKind
from engines.demand_mapping.contracts.provenance import Provenance
from engines.demand_mapping.contracts.records import (
    FieldValue,
    GenericEntityRecord,
    GenericInventorySnapshot,
)
from engines.demand_mapping.contracts.versions import SCHEMA_VERSIONS

ADAPTER_ID = "pettripfinder-inventory"
ADAPTER_VERSION = "1.0.0"

DEFAULT_MARKET_ID = "columbus-oh"

# Adapter policy: membership explosion is bounded (§8 of the Phase-B
# authority scope). Beyond this global cardinality the source field stays
# an opaque TEXT dimension.
MAX_MEMBERSHIP_VALUES = 8

_MONEY_RE = re.compile(r"^\$\s*(\d+)(?:\.(\d{1,2}))?$")
_POUNDS_RE = re.compile(r"^(\d+)(?:\.(\d))?\s*(?:pounds|lbs?)\b")
_INT_RE = re.compile(r"^(\d+)$")
_KEY_STRIP_RE = re.compile(r"[^a-z0-9]+")


def normalize_entity_key(name: str) -> str:
    """Lowercased, punctuation-collapsed entity key.

    Matches the launch package's policy-record ``key`` convention:
    "&" is spelled out as "and" ("Drury Inn & Suites ..." ->
    "drury inn and suites ..."), all other punctuation collapses to
    single spaces ("Aloft Columbus Easton" -> "aloft columbus easton").
    """
    lowered = name.lower().replace("&", " and ")
    return _KEY_STRIP_RE.sub(" ", lowered).strip()


def parse_money_cents(text: str) -> Optional[int]:
    """"$50.00" / "$50" -> integer cents; None when unparseable."""
    match = _MONEY_RE.match(text.strip())
    if not match:
        return None
    dollars = int(match.group(1))
    fraction = (match.group(2) or "").ljust(2, "0")
    return dollars * 100 + int(fraction or "0")


def parse_pounds_tenths(text: str) -> Optional[int]:
    """"75 pounds" / "40.0 pounds" -> integer tenths of a pound."""
    match = _POUNDS_RE.match(text.strip().lower())
    if not match:
        return None
    whole = int(match.group(1))
    tenth = int(match.group(2) or "0")
    return whole * 10 + tenth


def parse_plain_int(text: str) -> Optional[int]:
    match = _INT_RE.match(text.strip())
    return int(match.group(1)) if match else None


def parse_bool_word(text: str) -> Optional[bool]:
    lowered = text.strip().lower()
    if lowered == "true":
        return True
    if lowered == "false":
        return False
    return None


def species_members(text: str) -> Tuple[str, ...]:
    """"birds, fish, dogs and cats" -> sorted unique member tuple."""
    lowered = text.strip().lower().replace(" and ", ",")
    members = sorted(
        {part.strip() for part in lowered.split(",") if part.strip()}
    )
    return tuple(members)


def _record_provenance(policy: Mapping[str, Any], field: str) -> Provenance:
    evidence_fields = {
        entry.get("field")
        for entry in policy.get("evidence", ())
        if isinstance(entry, Mapping)
    }
    if field in evidence_fields:
        if policy.get("manual_evidence"):
            return Provenance.OPERATOR
        return Provenance.VERIFIED
    return Provenance.UNKNOWN


def _text_field(
    path: str, kind: DimensionKind, raw: Optional[str], provenance: Provenance
) -> Optional[FieldValue]:
    if raw is None:
        return None
    text = raw.strip()
    if not text:
        return None  # empty source value = missing, by doctrine
    return FieldValue(
        field_path=path, kind=kind, value_text=text, provenance=provenance
    )


def _policy_fields(
    policy: Mapping[str, Any], membership_vocab: Optional[Tuple[str, ...]]
) -> List[FieldValue]:
    facts: Mapping[str, Any] = policy.get("facts") or {}
    fields: List[FieldValue] = []

    raw_allowed = facts.get("pets_allowed")
    if isinstance(raw_allowed, str):
        parsed = parse_bool_word(raw_allowed)
        if parsed is not None:
            fields.append(FieldValue(
                field_path="policy.pets_allowed",
                kind=DimensionKind.BOOLEAN,
                value_bool=parsed,
                provenance=_record_provenance(policy, "pets_allowed"),
            ))

    raw_fee = facts.get("pet_fee")
    if isinstance(raw_fee, str):
        cents = parse_money_cents(raw_fee)
        if cents is not None:
            fields.append(FieldValue(
                field_path="policy.pet_fee",
                kind=DimensionKind.NUMERIC,
                value_int=cents,
                scale_denominator=100,
                provenance=_record_provenance(policy, "pet_fee"),
            ))

    basis = _text_field(
        "policy.fee_basis",
        DimensionKind.CATEGORICAL,
        facts.get("fee_basis") if isinstance(facts.get("fee_basis"), str)
        else None,
        _record_provenance(policy, "fee_basis"),
    )
    if basis is not None:
        fields.append(basis)

    raw_limit = facts.get("weight_limit")
    if isinstance(raw_limit, str):
        tenths = parse_pounds_tenths(raw_limit)
        if tenths is not None:
            fields.append(FieldValue(
                field_path="policy.weight_limit",
                kind=DimensionKind.NUMERIC,
                value_int=tenths,
                scale_denominator=10,
                provenance=_record_provenance(policy, "weight_limit"),
            ))

    raw_count = facts.get("pet_count_limit")
    if isinstance(raw_count, str):
        count = parse_plain_int(raw_count)
        if count is not None:
            fields.append(FieldValue(
                field_path="policy.pet_count_limit",
                kind=DimensionKind.NUMERIC,
                value_int=count,
                scale_denominator=1,
                provenance=_record_provenance(policy, "pet_count_limit"),
            ))

    raw_species = facts.get("species_allowed")
    if isinstance(raw_species, str) and raw_species.strip():
        provenance = _record_provenance(policy, "species_allowed")
        if membership_vocab is None:
            text_value = _text_field(
                "policy.species_allowed",
                DimensionKind.TEXT,
                raw_species,
                provenance,
            )
            if text_value is not None:
                fields.append(text_value)
        else:
            present = set(species_members(raw_species))
            for member in membership_vocab:
                fields.append(FieldValue(
                    field_path="policy.species_allowed:%s" % member,
                    kind=DimensionKind.BOOLEAN,
                    value_bool=member in present,
                    provenance=provenance,
                ))

    return fields


def _membership_vocabulary(
    policy_records: Sequence[Mapping[str, Any]],
) -> Optional[Tuple[str, ...]]:
    """Global sorted member vocabulary, or None when explosion is unsafe."""
    vocabulary: set = set()
    for policy in policy_records:
        facts = policy.get("facts") or {}
        raw = facts.get("species_allowed")
        if isinstance(raw, str) and raw.strip():
            vocabulary.update(species_members(raw))
    if not vocabulary or len(vocabulary) > MAX_MEMBERSHIP_VALUES:
        return None
    return tuple(sorted(vocabulary))


def build_generic_records(
    seed_rows: Iterable[Mapping[str, str]],
    policy_records: Sequence[Mapping[str, Any]],
    market_id: str = DEFAULT_MARKET_ID,
) -> Tuple[GenericEntityRecord, ...]:
    """Map committed PTF seed + policy data to generic records."""
    policy_by_key: Dict[str, Mapping[str, Any]] = {}
    for policy in policy_records:
        key = str(policy.get("key", "")).strip()
        if key:
            policy_by_key[key] = policy

    membership_vocab = _membership_vocabulary(policy_records)

    records: List[GenericEntityRecord] = []
    for row in seed_rows:
        if str(row.get("market_id", "")).strip() != market_id:
            continue
        name = str(row.get("name", "")).strip()
        category = str(row.get("category", "")).strip()
        if not name or not category:
            continue
        entity_id = normalize_entity_key(name)
        if not entity_id:
            continue

        fields: List[FieldValue] = []
        city = _text_field(
            "identity.city", DimensionKind.GEOGRAPHIC,
            row.get("city"), Provenance.UNKNOWN,
        )
        if city is not None:
            fields.append(city)
        postal = _text_field(
            "identity.postal_code", DimensionKind.GEOGRAPHIC,
            row.get("postal_code"), Provenance.UNKNOWN,
        )
        if postal is not None:
            fields.append(postal)

        policy = policy_by_key.get(entity_id)
        if policy is not None:
            fields.extend(_policy_fields(policy, membership_vocab))

        records.append(GenericEntityRecord(
            entity_id=entity_id,
            entity_kind=category,
            fields=tuple(sorted(fields, key=lambda item: item.field_path)),
        ))

    return tuple(sorted(records, key=lambda item: item.entity_id))


def build_inventory_snapshot(
    seed_rows: Iterable[Mapping[str, str]],
    policy_records: Sequence[Mapping[str, Any]],
    market_id: str = DEFAULT_MARKET_ID,
) -> GenericInventorySnapshot:
    """Frozen, content-addressed generic inventory for one PTF market."""
    return GenericInventorySnapshot.build(
        schema_version=SCHEMA_VERSIONS["GenericInventorySnapshot"],
        records=build_generic_records(seed_rows, policy_records, market_id),
    )


# ---------------------------------------------------------------------------
# Filesystem helpers — service layer only (§3.4); the engine never loads.
# ---------------------------------------------------------------------------

def load_seed_rows(path: Path) -> List[Dict[str, str]]:
    """Read a seed_businesses.csv into plain dict rows."""
    with Path(path).open("r", encoding="utf-8-sig", newline="") as handle:
        return [dict(row) for row in csv.DictReader(handle)]


def load_policy_records(path: Path) -> List[Dict[str, Any]]:
    """Read a hotel_policy_facts.json's record list."""
    with Path(path).open("r", encoding="utf-8-sig") as handle:
        payload = json.load(handle)
    return list(payload.get("hotels", ()))
