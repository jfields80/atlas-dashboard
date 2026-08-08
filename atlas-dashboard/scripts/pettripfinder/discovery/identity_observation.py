"""PTF-DISCOVERY-P0-001 -- the ptf-identity-observation/1.0 contract.

One normalized shape for what a discovery source adapter is allowed to say:
"a lodging-like entity exists, this is what the source called it, here is
exactly where I read that". Every future adapter -- human or AI, any source
family -- emits this one shape, and a single translator (here) turns
accepted observations into ``ptf-identity-evidence/1.0`` records for the
existing adjudication pipeline. Adapters never merge, never resolve
identity, and never assert identity confidence; ``parse_confidence`` is
extraction fidelity only.

Adopted from PTF-PARALLEL-RESEARCH-002 ``source_adapter_contract.md`` and
``identity_observation.schema.json`` (FD-R1 item 3). The contract is
ADDITIVE: it does not replace ``ptf-identity-evidence/1.0``, and the WO-1
field diff confirmed the two do not collapse (the evidence contract carries
no provenance block, no parse warnings, and no parse confidence).

Three rules with teeth:

1. STRICT KEYS. The schema is ``additionalProperties: false``; an unknown
   key is a validation failure, never an extension point. This is what
   makes the Membrane structural: a pet-policy field cannot even be
   *misspelled* into an observation.
2. MEMBRANE, TWICE. On top of strict keys, every key is scanned by NAME
   against the policy denylists (camelCase-normalized, exactly like
   ``membrane.normalize_field_name``) so that a policy smuggle fails with
   the right error class even if the key list ever widens.
3. NO SECOND IDENTITY KEY. ``obs_id`` is unique within one emission batch
   and nothing else; ``property_code`` is a namespaced passthrough of the
   SOURCE's identifier. Neither is an Atlas property key -- identity keys
   remain owned by the existing census/dedupe layer (``property_identity``).

Pure and deterministic: no network, no clock, no file reads.
"""

from __future__ import annotations

import re
import sys
from pathlib import Path
from typing import Dict, List, Mapping, Sequence

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.identity_evidence import (  # noqa: E402
    POLICY_FIELD_NAMES,
    TIER_1_OFFICIAL_PROPERTY,
    TIER_2_OFFICIAL_DESTINATION,
    TIER_3_BUSINESS_LISTING,
    TIER_4_OTA_DIRECTORY,
    validate_evidence,
)
from scripts.pettripfinder.discovery.membrane import (  # noqa: E402
    DISCOVERY_DENYLIST,
    normalize_field_name,
)
from scripts.pettripfinder.discovery.source_families import (  # noqa: E402
    FAMILY_CHAIN,
    FAMILY_CVB,
    FAMILY_DIRECTORY,
    FAMILY_GDS,
    FAMILY_MAP,
    FAMILY_OPEN_GEO,
    FAMILY_OPEN_KB,
    FAMILY_OPEN_PLACES,
    FAMILY_OTA,
    FAMILY_REGISTRY,
    SOURCE_FAMILIES,
)

SCHEMA = "ptf-identity-observation/1.0"
CONTRACT_VERSION = "1.0.0"

PARSE_CONFIDENCES = ("HIGH", "MEDIUM", "LOW")
RETRIEVAL_MODES = ("bulk_file", "api", "permissioned_crawl", "manual")

#: The closed warning-code vocabulary. An adapter that needs a new code is
#: proposing a contract change, not picking a string.
WARNING_CODES = frozenset({
    "W_ADDR_UNPARSED", "W_PHONE_INVALID", "W_GEO_MISSING",
    "W_ENCODING_REPAIRED", "W_FIELD_TRUNCATED", "W_AMBIGUOUS_ROW",
})

REQUIRED_FIELDS = ("obs_id", "contract_version", "source_id", "source_family",
                   "observed_at", "name", "provenance", "parse_confidence",
                   "warnings")
OPTIONAL_FIELDS = ("address", "city", "state", "zip", "phone", "lat", "lon",
                   "category_hint", "license_class", "prior_names",
                   "permanently_closed", "property_code")
ALLOWED_FIELDS = frozenset(REQUIRED_FIELDS) | frozenset(OPTIONAL_FIELDS)

PROVENANCE_REQUIRED = ("retrieval_mode", "retrieved_at", "raw_pointer")
PROVENANCE_OPTIONAL = ("snapshot_hash", "ephemeral", "license_tag")
PROVENANCE_ALLOWED = frozenset(PROVENANCE_REQUIRED) | frozenset(PROVENANCE_OPTIONAL)

_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class IdentityObservationError(ValueError):
    """An observation is malformed, or policy has been smuggled into it."""


def _assert_membrane_clean(keys, *, where: str) -> None:
    """Defense in depth over strict keys: NAME scan against both denylists."""
    denied = DISCOVERY_DENYLIST | POLICY_FIELD_NAMES
    hits = sorted({str(k) for k in keys if normalize_field_name(k) in denied})
    if hits:
        raise IdentityObservationError(
            "%s carries pet-policy field name(s) %s -- an identity observation "
            "may never carry a policy field; only an official property source "
            "read by the policy pipeline may establish a pet policy" % (where, hits))


def _require_nonempty_str(record: Mapping, field: str, *, where: str) -> str:
    value = record.get(field)
    if not isinstance(value, str) or not value.strip():
        raise IdentityObservationError(
            "%s: %r must be a non-empty string, got %r" % (where, field, value))
    return value


def validate_observation(record: Mapping) -> Dict:
    """Fail closed on anything the frozen 1.0 schema would reject.

    Mirrors ``identity_observation.schema.json`` exactly: required fields,
    strict keys at every level, closed enums, and the Membrane clause."""
    if not isinstance(record, Mapping):
        raise IdentityObservationError(
            "an observation must be a mapping, got %r" % type(record).__name__)
    where = "observation %r" % (record.get("obs_id") or "<no obs_id>")

    _assert_membrane_clean(record.keys(), where=where)
    unknown = sorted(set(map(str, record.keys())) - ALLOWED_FIELDS)
    if unknown:
        raise IdentityObservationError(
            "%s carries unknown field(s) %s (additionalProperties is false)"
            % (where, unknown))

    for field in ("obs_id", "source_id", "name"):
        _require_nonempty_str(record, field, where=where)
    if record.get("contract_version") != CONTRACT_VERSION:
        raise IdentityObservationError(
            "%s: contract_version must be %r, got %r"
            % (where, CONTRACT_VERSION, record.get("contract_version")))
    if record.get("source_family") not in SOURCE_FAMILIES:
        raise IdentityObservationError(
            "%s: source_family %r is not one of the ten families %s"
            % (where, record.get("source_family"), sorted(SOURCE_FAMILIES)))
    observed_at = _require_nonempty_str(record, "observed_at", where=where)
    if not _ISO_DATE.match(observed_at):
        raise IdentityObservationError(
            "%s: observed_at must be an ISO date (YYYY-MM-DD), got %r"
            % (where, observed_at))
    if record.get("parse_confidence") not in PARSE_CONFIDENCES:
        raise IdentityObservationError(
            "%s: parse_confidence must be one of %s, got %r"
            % (where, list(PARSE_CONFIDENCES), record.get("parse_confidence")))

    # ---- warnings ------------------------------------------------------- #
    warnings = record.get("warnings")
    if not isinstance(warnings, (list, tuple)):
        raise IdentityObservationError(
            "%s: warnings must be an array (empty when clean), got %r"
            % (where, warnings))
    for warning in warnings:
        if not isinstance(warning, Mapping):
            raise IdentityObservationError(
                "%s: each warning must be a {code, detail} mapping, got %r"
                % (where, warning))
        unknown_w = sorted(set(map(str, warning.keys())) - {"code", "detail"})
        if unknown_w:
            raise IdentityObservationError(
                "%s: warning carries unknown key(s) %s" % (where, unknown_w))
        if warning.get("code") not in WARNING_CODES:
            raise IdentityObservationError(
                "%s: unknown warning code %r (codes: %s)"
                % (where, warning.get("code"), sorted(WARNING_CODES)))
        if not isinstance(warning.get("detail"), str) or not warning["detail"].strip():
            raise IdentityObservationError(
                "%s: warning %s needs a non-empty detail -- an adapter that "
                "warns without saying why is guessing silently"
                % (where, warning.get("code")))

    # ---- provenance ----------------------------------------------------- #
    provenance = record.get("provenance")
    if not isinstance(provenance, Mapping):
        raise IdentityObservationError(
            "%s: provenance is required and must be a mapping" % where)
    _assert_membrane_clean(provenance.keys(), where="%s provenance" % where)
    unknown_p = sorted(set(map(str, provenance.keys())) - PROVENANCE_ALLOWED)
    if unknown_p:
        raise IdentityObservationError(
            "%s: provenance carries unknown key(s) %s" % (where, unknown_p))
    if provenance.get("retrieval_mode") not in RETRIEVAL_MODES:
        raise IdentityObservationError(
            "%s: retrieval_mode must be one of %s, got %r"
            % (where, list(RETRIEVAL_MODES), provenance.get("retrieval_mode")))
    for field in ("retrieved_at", "raw_pointer"):
        _require_nonempty_str(provenance, field, where="%s provenance" % where)
    if "ephemeral" in provenance and not isinstance(provenance["ephemeral"], bool):
        raise IdentityObservationError(
            "%s: provenance.ephemeral must be a boolean" % where)

    # ---- optional identity fields --------------------------------------- #
    for field in ("address", "city", "state", "zip", "phone", "category_hint",
                  "license_class"):
        if field in record and not isinstance(record[field], str):
            raise IdentityObservationError(
                "%s: %r must be a string when present" % (where, field))
    for field, low, high in (("lat", -90, 90), ("lon", -180, 180)):
        if field in record:
            value = record[field]
            if isinstance(value, bool) or not isinstance(value, (int, float)) \
                    or not (low <= value <= high):
                raise IdentityObservationError(
                    "%s: %r must be a number in [%d, %d], got %r"
                    % (where, field, low, high, value))
    if "prior_names" in record:
        names = record["prior_names"]
        if not isinstance(names, (list, tuple)) or \
                not all(isinstance(n, str) and n.strip() for n in names):
            raise IdentityObservationError(
                "%s: prior_names must be an array of non-empty strings" % where)
    if "permanently_closed" in record and \
            not isinstance(record["permanently_closed"], bool):
        raise IdentityObservationError(
            "%s: permanently_closed must be a boolean" % where)
    if "property_code" in record and record["property_code"] is not None \
            and not isinstance(record["property_code"], str):
        raise IdentityObservationError(
            "%s: property_code must be a string or null" % where)

    return dict(record)


def validate_emission_batch(batch: Sequence[Mapping]) -> List[Dict]:
    """One batch per (source, market, run): a JSON array, obs_ids unique."""
    if isinstance(batch, Mapping) or not isinstance(batch, (list, tuple)):
        raise IdentityObservationError(
            "an emission batch must be a JSON array of observations, got %r"
            % type(batch).__name__)
    validated = [validate_observation(record) for record in batch]
    seen: Dict[str, int] = {}
    for record in validated:
        seen[record["obs_id"]] = seen.get(record["obs_id"], 0) + 1
    duplicates = sorted(k for k, n in seen.items() if n > 1)
    if duplicates:
        raise IdentityObservationError(
            "obs_id must be unique within the batch; duplicated: %s" % duplicates)
    return validated


# --------------------------------------------------------------------------- #
# Translation into ptf-identity-evidence/1.0 (the ingestion boundary).
# --------------------------------------------------------------------------- #

#: Evidence tier by family -- the translator's judgment, made once, in the
#: open, conservatively. A government registry and a CVB are official
#: NON-property bodies (tier 2); a chain's own locator is tier 1; OTA and
#: GDS listings are tier 4; everything else is a business/map listing
#: (tier 3). No family maps to a stronger tier than adjudicate() would
#: grant a human transcribing the same source.
OBSERVATION_TIER_BY_FAMILY = {
    FAMILY_CHAIN: TIER_1_OFFICIAL_PROPERTY,
    FAMILY_CVB: TIER_2_OFFICIAL_DESTINATION,
    FAMILY_REGISTRY: TIER_2_OFFICIAL_DESTINATION,
    FAMILY_MAP: TIER_3_BUSINESS_LISTING,
    FAMILY_OPEN_GEO: TIER_3_BUSINESS_LISTING,
    FAMILY_OPEN_PLACES: TIER_3_BUSINESS_LISTING,
    FAMILY_DIRECTORY: TIER_3_BUSINESS_LISTING,
    FAMILY_OPEN_KB: TIER_3_BUSINESS_LISTING,
    FAMILY_OTA: TIER_4_OTA_DIRECTORY,
    FAMILY_GDS: TIER_4_OTA_DIRECTORY,
}


def observation_to_evidence(observation: Mapping) -> Dict:
    """One validated observation -> one ptf-identity-evidence/1.0 record.

    The ONLY place the two contracts meet. Notes on the mapping:

    * ``source_family`` stays the FAMILY, not the concrete source, so
      ``identity_evidence.independent()`` treats two same-family sources as
      one voice. That is deliberately stricter than the census's historical
      per-source families and can only under-confirm, never over-confirm.
    * ``source_url`` is the observation's ``raw_pointer`` -- the re-findable
      locator of the raw assertion, which is exactly what the evidence
      contract wants that field for.
    * ``permanently_closed`` and ``prior_names`` become a ``status_note``
      phrased in the vocabulary ``adjudicate()`` already matches
      (CLOSURE_MARKERS / REBRAND_MARKERS), so closure and rebrand signals
      flow into the existing outcomes instead of a parallel mechanism.
    """
    observation = validate_observation(observation)
    tier = OBSERVATION_TIER_BY_FAMILY[observation["source_family"]]

    notes = []
    if observation.get("permanently_closed"):
        notes.append("permanently closed per the source record")
    if observation.get("prior_names"):
        notes.append("formerly %s" % ", ".join(observation["prior_names"]))

    evidence = {
        "tier": tier,
        "source_family": observation["source_family"],
        "source_url": observation["provenance"]["raw_pointer"],
        "observed_at": observation["observed_at"],
        "name": observation["name"],
        "address": observation.get("address", ""),
        "postal_code": observation.get("zip", ""),
        "city": observation.get("city", ""),
        "state": observation.get("state", ""),
        "phone": observation.get("phone", ""),
        "source_id": observation["source_id"],
        "obs_id": observation["obs_id"],
        "parse_confidence": observation["parse_confidence"],
    }
    if notes:
        evidence["status_note"] = "; ".join(notes)
    if observation.get("license_class"):
        evidence["license_class"] = observation["license_class"]
    if observation.get("property_code"):
        evidence["property_code"] = observation["property_code"]
    return validate_evidence(evidence)


def translate_emission_batch(batch: Sequence[Mapping]) -> List[Dict]:
    """A validated emission batch -> evidence records, order preserved."""
    return [observation_to_evidence(o) for o in validate_emission_batch(batch)]


__all__ = [
    "SCHEMA", "CONTRACT_VERSION", "IdentityObservationError",
    "PARSE_CONFIDENCES", "RETRIEVAL_MODES", "WARNING_CODES",
    "REQUIRED_FIELDS", "OPTIONAL_FIELDS",
    "OBSERVATION_TIER_BY_FAMILY",
    "validate_observation", "validate_emission_batch",
    "observation_to_evidence", "translate_emission_batch",
]
