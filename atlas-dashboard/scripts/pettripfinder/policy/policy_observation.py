"""PTF-POLICY-P0-001 -- the ptf-policy-observation/1.0 contract.

One normalized shape for what a policy capture is allowed to say: "this
source, at this URL, at this time, said these exact words, which parse to
these candidate fields". Every producer -- a deterministic adapter, the
browser-assisted worker, a human transcribing a phone call -- emits this one
shape, and a single boundary (``policy_membrane`` + ``readiness``) decides
what may be done with it.

Adopted from PTF-PARALLEL-RESEARCH-003 ``policy_observation_contract.md`` and
``schemas/policy_observation.schema.json``, re-implemented Atlas-native rather
than ported: tier constants, name normalization and identity keys already have
owners in this repository, and a second copy of any of them would be a second
source of truth.

Built as the deliberate mirror of ``discovery/identity_observation.py``, and
for the same three reasons:

1. STRICT KEYS. Unknown keys are validation failures, never extension points.
   The identity contract uses this so a policy field cannot be misspelled into
   an identity record; here it stops the inverse -- an extraction field that
   production has no vocabulary for cannot appear at all.
2. NO SECOND IDENTITY KEY. ``hotel_ref`` is a *reference* into the existing
   identity authority (market_id + normalized_name, guarded by
   street_identity). ``obs_id`` is unique within one emission batch and
   nothing else. No canonical id is minted here.
3. AN OBSERVATION IS NOT A FACT. Nothing in this module writes to the policy
   authority, and ``extraction_confidence`` is extraction FIDELITY, never a
   truth score -- exactly as ``parse_confidence`` is on the identity side. A
   numeric confidence never gates publication anywhere in this package.

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

from scripts.pettripfinder.discovery.membrane import normalize_field_name  # noqa: E402
from scripts.pettripfinder.identity_evidence import POLICY_FIELD_NAMES     # noqa: E402

SCHEMA = "ptf-policy-observation/1.0"
CONTRACT_VERSION = "1.0.0"

# --------------------------------------------------------------------------- #
# Authority tiers.
#
# PT1..PT4 name the policy-source taxonomy. They are deliberately a SEPARATE
# vocabulary from identity_evidence's numeric tiers: the identity question
# ("does this hotel exist") and the policy question ("what does it charge for
# a dog") rank sources differently, and collapsing them would let a CVB page
# that legitimately confirms existence look like it could confirm a fee.
# --------------------------------------------------------------------------- #

PT1_OFFICIAL_PROPERTY = "PT1"      #: the property's own page / booking flow / PDF
PT2_BRAND_GENERIC = "PT2"          #: brand-level policy not specific to this property
PT3_OPERATOR_ATTESTED = "PT3"      #: operator/franchisee attestation captured by us
PT4_NON_AUTHORITATIVE = "PT4"      #: OTA, map, directory, snippet -- hint only

AUTHORITY_TIERS = (PT1_OFFICIAL_PROPERTY, PT2_BRAND_GENERIC,
                   PT3_OPERATOR_ATTESTED, PT4_NON_AUTHORITATIVE)

#: Tiers that may ESTABLISH a publishable policy fact. PT2 corroborates a
#: property-specific statement; PT4 only ever hints. Neither can establish,
#: however many of them agree.
ESTABLISHING_TIERS = (PT1_OFFICIAL_PROPERTY, PT3_OPERATOR_ATTESTED)

#: source_type -> the STRONGEST tier that source type may ever claim. The table
#: is closed, and it is the mechanical form of "official source or operator
#: attestation establishes; everything else corroborates".
#: Adopted VERBATIM from the research package's
#: ``schemas/policy_observation.schema.json`` enum. The names are the
#: package's, not this repository's, on purpose: the fixtures are the
#: package's verified bytes, and a locally-invented synonym would have made
#: six of them fail for a spelling rather than a semantic reason.
SOURCE_TYPE_MAX_TIER = {
    # PT1 -- the property's own surfaces
    "official_property_page": PT1_OFFICIAL_PROPERTY,
    "official_amenities_page": PT1_OFFICIAL_PROPERTY,
    "official_booking_engine": PT1_OFFICIAL_PROPERTY,
    "official_pdf": PT1_OFFICIAL_PROPERTY,
    "official_public_json": PT1_OFFICIAL_PROPERTY,
    "official_structured_data": PT1_OFFICIAL_PROPERTY,
    # PT2 -- the brand talking about brands
    "official_brand_faq": PT2_BRAND_GENERIC,
    # PT3 -- a human at the property, attested by us
    "direct_property_contact": PT3_OPERATOR_ATTESTED,
    # PT4 -- everything that may hint and never establish
    "cvb_listing": PT4_NON_AUTHORITATIVE,
    "ota": PT4_NON_AUTHORITATIVE,
    "gds": PT4_NON_AUTHORITATIVE,
    "map_listing": PT4_NON_AUTHORITATIVE,
    "search_snippet": PT4_NON_AUTHORITATIVE,
    "cached_archive": PT4_NON_AUTHORITATIVE,
}
SOURCE_TYPES = tuple(sorted(SOURCE_TYPE_MAX_TIER))

#: The source type whose content is truncated by construction (M4).
SNIPPET_SOURCE_TYPE = "search_snippet"
#: The source type that can corroborate but never carry a live claim (M5).
ARCHIVE_SOURCE_TYPE = "cached_archive"

CAPTURE_METHODS = ("deterministic_fetch", "browser_assisted", "human_manual",
                   "phone_contact")

#: Extraction FIDELITY, not truth. INFERRED never publishes (M7).
EXTRACTION_CONFIDENCES = ("EXACT_QUOTE", "PARAPHRASE", "INFERRED")

#: Closed flag vocabulary. A producer needing a new code is proposing a
#: contract change, not picking a string.
FLAG_CODES = frozenset({
    "FLAG_SERVICE_ANIMAL_ONLY", "FLAG_MARKETING_ONLY", "FLAG_STALE_ARCHIVE",
    "FLAG_BRAND_GENERIC", "FLAG_CONTRADICTS_OFFICIAL", "FLAG_SPECIES_NARROWED",
    "FLAG_AMBIGUOUS_BASIS", "FLAG_AMBIGUOUS_SCOPE", "FLAG_MULTI_POLICY_BLOCKS",
    "FLAG_PDF_UNDATED", "FLAG_OCR_GRADE", "FLAG_UNSUPPORTED_SPECIES_WORDING",
    "W_ENCODING_REPAIRED", "W_FIELD_TRUNCATED", "W_AMBIGUOUS_ROW",
})

#: The candidate policy fields an observation may carry. Aligned with the
#: production vocabulary so the downstream mapping is a mapping and not an
#: invention: every name below except the four noted in
#: ADDITIVE_EXTRACTION_FIELDS is already in identity_evidence.POLICY_FIELD_NAMES.
EXTRACTION_FIELDS = frozenset({
    "pets_allowed", "species_allowed", "cats_allowed", "pet_count_limit",
    "pet_count_scope", "weight_limit", "weight_limit_operator",
    "weight_limit_stated_none", "pet_fee", "fee_currency", "fee_basis",
    "fee_scope", "fee_tiers", "fee_cap", "pet_deposit", "cleaning_fee",
    "breed_restrictions", "breed_restrictions_stated_none",
    "pet_room_restriction", "eligible_room_types", "reservation_requirement",
    "service_animal_exception", "unattended_policy", "general_restrictions",
})

#: Names this contract carries that the production policy vocabulary does not
#: yet have. Declared explicitly so the gap is visible rather than discovered
#: later by a translator that silently drops them.
ADDITIVE_EXTRACTION_FIELDS = frozenset(
    EXTRACTION_FIELDS - POLICY_FIELD_NAMES)

#: Fields that do NOT establish a pet policy on their own. Service-animal
#: language is a legal access category under the ADA, never a pet permission
#: (M6), so an observation carrying only this field establishes nothing.
NON_ESTABLISHING_FIELDS = frozenset({"service_animal_exception"})

#: Values that assert nothing. "not_stated" is an ABSENCE claim: it neither
#: establishes a fact nor needs a quote to back it, because M9 governs
#: asserted facts only.
NON_ASSERTING_VALUES = ("", None, "not_stated")

#: Keys whose value is money. Money is integer minor units everywhere -- the
#: house float ban -- and this is checked recursively.
MONEY_KEYS = frozenset({"pet_fee", "amount_minor"})

REQUIRED_FIELDS = ("obs_id", "contract_version", "hotel_ref", "identity_check",
                   "source_url", "source_type", "authority_tier", "observed_at",
                   "retrieved_at", "capture_method", "evidence", "extraction",
                   "extraction_confidence", "flags")
OPTIONAL_FIELDS = ("snapshot_hash", "raw_pointer", "source_freshness",
                   "parser_warnings", "capture_artifacts")
ALLOWED_FIELDS = frozenset(REQUIRED_FIELDS) | frozenset(OPTIONAL_FIELDS)

HOTEL_REF_REQUIRED = ("market_id", "canonical_name", "normalized_name")
HOTEL_REF_OPTIONAL = ("street_identity", "official_url", "property_code")
HOTEL_REF_ALLOWED = frozenset(HOTEL_REF_REQUIRED) | frozenset(HOTEL_REF_OPTIONAL)

IDENTITY_CHECK_ALLOWED = frozenset({"name_on_page", "address_on_page",
                                    "property_code", "phone_on_page"})

EVIDENCE_REQUIRED = ("quote", "location", "field_refs")
EVIDENCE_ALLOWED = frozenset(EVIDENCE_REQUIRED) | frozenset({"artifact_ref"})

_ISO_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")


class PolicyObservationError(ValueError):
    """An observation is malformed. Distinct from a membrane REJECTION: this
    means the record is not a valid observation at all, where a rejection
    means a well-formed observation may not be used for what it claims."""


def _require_nonempty_str(record: Mapping, field: str, *, where: str) -> str:
    value = record.get(field)
    if not isinstance(value, str) or not value.strip():
        raise PolicyObservationError(
            "%s: %r must be a non-empty string, got %r" % (where, field, value))
    return value


def _money_is_integer(value, *, where: str, path: str = "extraction") -> None:
    """Recursively refuse a float anywhere money is carried."""
    if isinstance(value, Mapping):
        for key, item in value.items():
            if key in MONEY_KEYS and (isinstance(item, bool)
                                      or not isinstance(item, int)):
                raise PolicyObservationError(
                    "%s: %s.%s must be an integer in minor units, got %r -- "
                    "money is never a float in this repository"
                    % (where, path, key, item))
            _money_is_integer(item, where=where, path="%s.%s" % (path, key))
    elif isinstance(value, (list, tuple)):
        for i, item in enumerate(value):
            _money_is_integer(item, where=where, path="%s[%d]" % (path, i))


def asserted_fields(extraction: Mapping) -> frozenset:
    """Fields the observation actually ASSERTS -- absence claims excluded."""
    return frozenset(k for k, v in extraction.items()
                     if v not in NON_ASSERTING_VALUES)


def establishing_fields(extraction: Mapping) -> frozenset:
    """Asserted fields that could establish a policy. Service-animal text
    alone never can."""
    return asserted_fields(extraction) - NON_ESTABLISHING_FIELDS


def quoted_fields(evidence: Sequence[Mapping]) -> frozenset:
    """Every field name some evidence quote claims to support."""
    covered: set = set()
    for item in evidence:
        covered.update(item.get("field_refs") or ())
    return frozenset(covered)


def validate_observation(record: Mapping) -> Dict:
    """Fail closed on anything the frozen 1.0 contract would reject.

    Structure only. Whether a well-formed observation may ESTABLISH anything
    is the membrane's question, not this function's -- keeping the two apart is
    what lets a rejected observation still be retained and diagnosed.
    """
    if not isinstance(record, Mapping):
        raise PolicyObservationError(
            "an observation must be a mapping, got %r" % type(record).__name__)
    where = "policy observation %r" % (record.get("obs_id") or "<no obs_id>")

    unknown = sorted(set(map(str, record.keys())) - ALLOWED_FIELDS)
    if unknown:
        raise PolicyObservationError(
            "%s carries unknown field(s) %s (additionalProperties is false)"
            % (where, unknown))
    missing = [f for f in REQUIRED_FIELDS if f not in record]
    if missing:
        raise PolicyObservationError(
            "%s is missing required field(s) %s" % (where, missing))

    _require_nonempty_str(record, "obs_id", where=where)
    _require_nonempty_str(record, "source_url", where=where)
    if record.get("contract_version") != CONTRACT_VERSION:
        raise PolicyObservationError(
            "%s: contract_version must be %r, got %r"
            % (where, CONTRACT_VERSION, record.get("contract_version")))
    if record.get("source_type") not in SOURCE_TYPE_MAX_TIER:
        raise PolicyObservationError(
            "%s: source_type %r is not in the closed taxonomy %s"
            % (where, record.get("source_type"), list(SOURCE_TYPES)))
    if record.get("authority_tier") not in AUTHORITY_TIERS:
        raise PolicyObservationError(
            "%s: authority_tier must be one of %s, got %r"
            % (where, list(AUTHORITY_TIERS), record.get("authority_tier")))
    if record.get("capture_method") not in CAPTURE_METHODS:
        raise PolicyObservationError(
            "%s: capture_method must be one of %s, got %r"
            % (where, list(CAPTURE_METHODS), record.get("capture_method")))
    if record.get("extraction_confidence") not in EXTRACTION_CONFIDENCES:
        raise PolicyObservationError(
            "%s: extraction_confidence must be one of %s, got %r"
            % (where, list(EXTRACTION_CONFIDENCES),
               record.get("extraction_confidence")))

    observed_at = _require_nonempty_str(record, "observed_at", where=where)
    if not _ISO_DATE.match(observed_at):
        raise PolicyObservationError(
            "%s: observed_at must be an ISO date (YYYY-MM-DD), got %r"
            % (where, observed_at))
    _require_nonempty_str(record, "retrieved_at", where=where)

    # ---- hotel_ref: a reference, never a new identity -------------------- #
    ref = record.get("hotel_ref")
    if not isinstance(ref, Mapping):
        raise PolicyObservationError("%s: hotel_ref must be a mapping" % where)
    unknown_ref = sorted(set(map(str, ref.keys())) - HOTEL_REF_ALLOWED)
    if unknown_ref:
        raise PolicyObservationError(
            "%s: hotel_ref carries unknown key(s) %s -- this contract "
            "references the existing identity authority and never extends it"
            % (where, unknown_ref))
    for field in HOTEL_REF_REQUIRED:
        _require_nonempty_str(ref, field, where="%s hotel_ref" % where)

    # ---- identity_check: what the PAGE said about itself ------------------ #
    check = record.get("identity_check")
    if not isinstance(check, Mapping):
        raise PolicyObservationError(
            "%s: identity_check is required -- an observation must carry the "
            "evidence that the captured page was about THIS property" % where)
    unknown_check = sorted(set(map(str, check.keys())) - IDENTITY_CHECK_ALLOWED)
    if unknown_check:
        raise PolicyObservationError(
            "%s: identity_check carries unknown key(s) %s" % (where, unknown_check))
    _require_nonempty_str(check, "name_on_page", where="%s identity_check" % where)

    # ---- evidence -------------------------------------------------------- #
    evidence = record.get("evidence")
    if not isinstance(evidence, (list, tuple)):
        raise PolicyObservationError(
            "%s: evidence must be an array (empty is allowed; absent is not)" % where)
    for item in evidence:
        if not isinstance(item, Mapping):
            raise PolicyObservationError(
                "%s: each evidence item must be a mapping, got %r" % (where, item))
        unknown_e = sorted(set(map(str, item.keys())) - EVIDENCE_ALLOWED)
        if unknown_e:
            raise PolicyObservationError(
                "%s: evidence item carries unknown key(s) %s" % (where, unknown_e))
        for field in ("quote", "location"):
            _require_nonempty_str(item, field, where="%s evidence" % where)
        if not isinstance(item.get("field_refs"), (list, tuple)):
            raise PolicyObservationError(
                "%s: evidence.field_refs must be an array naming every field "
                "that rests on this quote" % where)
        bad_refs = sorted(set(map(str, item["field_refs"])) - EXTRACTION_FIELDS)
        if bad_refs:
            raise PolicyObservationError(
                "%s: evidence.field_refs names unknown field(s) %s" % (where, bad_refs))

    # ---- extraction ------------------------------------------------------- #
    extraction = record.get("extraction")
    if not isinstance(extraction, Mapping):
        raise PolicyObservationError("%s: extraction must be a mapping" % where)
    bad_keys = sorted(set(map(str, extraction.keys())) - EXTRACTION_FIELDS)
    if bad_keys:
        raise PolicyObservationError(
            "%s: unknown extraction field(s) %s -- the vocabulary is closed so "
            "a field production cannot store cannot be invented here"
            % (where, bad_keys))
    _money_is_integer(extraction, where=where)

    # ---- flags ------------------------------------------------------------ #
    flags = record.get("flags")
    if not isinstance(flags, (list, tuple)):
        raise PolicyObservationError(
            "%s: flags must be an array (empty when clean)" % where)
    for flag in flags:
        if not isinstance(flag, Mapping):
            raise PolicyObservationError(
                "%s: each flag must be a {code, detail} mapping, got %r" % (where, flag))
        unknown_f = sorted(set(map(str, flag.keys())) - {"code", "detail"})
        if unknown_f:
            raise PolicyObservationError(
                "%s: flag carries unknown key(s) %s" % (where, unknown_f))
        if flag.get("code") not in FLAG_CODES:
            raise PolicyObservationError(
                "%s: unknown flag code %r" % (where, flag.get("code")))
        if not isinstance(flag.get("detail"), str) or not flag["detail"].strip():
            raise PolicyObservationError(
                "%s: flag %s needs a non-empty detail -- a producer that flags "
                "without saying why is guessing silently" % (where, flag.get("code")))

    # ---- optional blocks -------------------------------------------------- #
    if "parser_warnings" in record:
        warnings = record["parser_warnings"]
        if not isinstance(warnings, (list, tuple)) or \
                not all(isinstance(w, str) and w.strip() for w in warnings):
            raise PolicyObservationError(
                "%s: parser_warnings must be an array of non-empty strings" % where)
    if "source_freshness" in record:
        freshness = record["source_freshness"]
        if not isinstance(freshness, Mapping):
            raise PolicyObservationError(
                "%s: source_freshness must be a mapping" % where)
        unknown_s = sorted(set(map(str, freshness.keys()))
                           - {"page_date", "last_modified", "archive_date", "note"})
        if unknown_s:
            raise PolicyObservationError(
                "%s: source_freshness carries unknown key(s) %s" % (where, unknown_s))

    return dict(record)


def validate_emission_batch(batch: Sequence[Mapping]) -> List[Dict]:
    """One batch per (hotel, run): a JSON array with unique obs_ids."""
    if isinstance(batch, Mapping) or not isinstance(batch, (list, tuple)):
        raise PolicyObservationError(
            "an emission batch must be a JSON array of observations, got %r"
            % type(batch).__name__)
    validated = [validate_observation(record) for record in batch]
    seen: Dict[str, int] = {}
    for record in validated:
        seen[record["obs_id"]] = seen.get(record["obs_id"], 0) + 1
    duplicates = sorted(k for k, n in seen.items() if n > 1)
    if duplicates:
        raise PolicyObservationError(
            "obs_id must be unique within the batch; duplicated: %s" % duplicates)
    return validated


def assert_not_identity_evidence(record: Mapping) -> None:
    """M11, the inverse Membrane face: a policy observation may never be
    submitted as identity evidence. Called by anything tempted to feed one
    into the identity adjudicator."""
    if isinstance(record, Mapping) and record.get("contract_version") == CONTRACT_VERSION \
            and "extraction" in record:
        raise PolicyObservationError(
            "a ptf-policy-observation/1.0 record may not be used as identity "
            "evidence: a policy capture confirms nothing about a property's "
            "existence beyond its own identity_check")


__all__ = [
    "SCHEMA", "CONTRACT_VERSION", "PolicyObservationError",
    "PT1_OFFICIAL_PROPERTY", "PT2_BRAND_GENERIC", "PT3_OPERATOR_ATTESTED",
    "PT4_NON_AUTHORITATIVE", "AUTHORITY_TIERS", "ESTABLISHING_TIERS",
    "SOURCE_TYPE_MAX_TIER", "SOURCE_TYPES", "CAPTURE_METHODS",
    "EXTRACTION_CONFIDENCES", "FLAG_CODES", "EXTRACTION_FIELDS",
    "ADDITIVE_EXTRACTION_FIELDS", "NON_ESTABLISHING_FIELDS", "MONEY_KEYS",
    "REQUIRED_FIELDS", "OPTIONAL_FIELDS",
    "asserted_fields", "establishing_fields", "quoted_fields",
    "validate_observation", "validate_emission_batch",
    "assert_not_identity_evidence",
]
