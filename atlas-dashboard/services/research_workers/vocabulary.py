"""ATLAS-WORKERS-001 -- centralized worker vocabulary and caps.

Every stable slug, enum, and cap the worker uses lives here so no module
invents ad hoc strings (the same discipline as
scripts/pettripfinder/importer/constants.py). Pure data -- no I/O, no network.

The proposed-fact field names are the PetTripFinder policy vocabulary. Where a
field is a finer-grained split of an existing importer field, the mapping to
the production importer/CSV vocabulary is recorded in PRODUCTION_FIELD_NOTES so
this worker never becomes a competing set of names -- Atlas ingestion maps
these worker proposals onto the existing importer fields.
"""

from __future__ import annotations

# --------------------------------------------------------------------------- #
# Versions (recorded in every assignment/result for replay).
# --------------------------------------------------------------------------- #

CONTRACT_VERSION = "1.0.0"
WORKER_TYPE_HOTEL_POLICY = "HOTEL_POLICY_RESEARCH"

# --------------------------------------------------------------------------- #
# Caps (bounded, deterministic; mirror the importer where a shared limit
# already exists so the two subsystems agree).
# --------------------------------------------------------------------------- #

EVIDENCE_QUOTE_CAP = 300               # chars per evidence quote (== importer)
SOURCE_CONTENT_CAP_BYTES = 200 * 1024  # supplied document content_text cap
MAX_SOURCE_DOCUMENTS = 8               # per assignment
DEFAULT_OUTPUT_TOKEN_CAP = 1024
DEFAULT_TIMEOUT_SECONDS = 60
DEFAULT_MAX_RETRIES = 2

# --------------------------------------------------------------------------- #
# Proposed policy fields (the worker's output vocabulary).
# --------------------------------------------------------------------------- #

FIELD_PETS_ALLOWED = "pets_allowed"
FIELD_DOGS_ACCEPTED = "dogs_accepted"
FIELD_CATS_ACCEPTED = "cats_accepted"
FIELD_PET_FEE = "pet_fee"
FIELD_FEE_CURRENCY = "fee_currency"
FIELD_FEE_BASIS = "fee_basis"
FIELD_REFUNDABLE_DEPOSIT = "refundable_deposit"
FIELD_MAXIMUM_PETS = "maximum_pets"
FIELD_WEIGHT_LIMIT = "weight_limit"
FIELD_BREED_RESTRICTIONS = "breed_restrictions"
FIELD_UNATTENDED_PET_RULE = "unattended_pet_rule"
FIELD_SERVICE_ANIMAL_NOTE = "service_animal_note"

POLICY_FIELDS = (
    FIELD_PETS_ALLOWED, FIELD_DOGS_ACCEPTED, FIELD_CATS_ACCEPTED, FIELD_PET_FEE,
    FIELD_FEE_CURRENCY, FIELD_FEE_BASIS, FIELD_REFUNDABLE_DEPOSIT,
    FIELD_MAXIMUM_PETS, FIELD_WEIGHT_LIMIT, FIELD_BREED_RESTRICTIONS,
    FIELD_UNATTENDED_PET_RULE, FIELD_SERVICE_ANIMAL_NOTE,
)
POLICY_FIELD_SET = frozenset(POLICY_FIELDS)

# Fields whose value must be a boolean-ish token ("true"/"false").
BOOLEAN_FIELDS = frozenset({FIELD_PETS_ALLOWED, FIELD_DOGS_ACCEPTED, FIELD_CATS_ACCEPTED})
# Fields whose SUPPORTED value must contain a number that also appears in the
# evidence quote (guards against inference from plural wording / conversions).
NUMERIC_FIELDS = frozenset({FIELD_PET_FEE, FIELD_REFUNDABLE_DEPOSIT,
                            FIELD_MAXIMUM_PETS, FIELD_WEIGHT_LIMIT})

# fee_basis is a closed vocabulary -- per-night / per-stay / per-room /
# per-room-per-day / per-room-per-night are DISTINCT and never collapsed
# (Stage 3 rule 8). ATLAS-WORKERS-005 added per_room_per_night: the Columbus
# live pilot found real official phrasing ("$50 per room per night") that no
# prior value could represent, so the model was forced into a wrong mapping.
# This is an ADDITIVE completion of the vocabulary -- existing values are
# unchanged, and Atlas ingestion (which free-passes the fee_basis display
# string) is unaffected.
FEE_BASIS_PER_NIGHT = "per_night"
FEE_BASIS_PER_STAY = "per_stay"
FEE_BASIS_PER_ROOM = "per_room"
FEE_BASIS_PER_ROOM_PER_DAY = "per_room_per_day"
FEE_BASIS_PER_ROOM_PER_NIGHT = "per_room_per_night"
FEE_BASIS_VALUES = frozenset({
    FEE_BASIS_PER_NIGHT, FEE_BASIS_PER_STAY, FEE_BASIS_PER_ROOM,
    FEE_BASIS_PER_ROOM_PER_DAY, FEE_BASIS_PER_ROOM_PER_NIGHT,
})

# How each worker field maps onto the production importer vocabulary
# (documentation only -- Atlas ingestion owns the mapping; the worker never
# writes these names into production).
PRODUCTION_FIELD_NOTES = {
    FIELD_DOGS_ACCEPTED: "component of importer species_allowed (dogs)",
    FIELD_CATS_ACCEPTED: "component of importer species_allowed (cats)",
    FIELD_MAXIMUM_PETS: "importer pet_count_limit",
    FIELD_UNATTENDED_PET_RULE: "importer unattended_policy",
    FIELD_PET_FEE: "importer pet_fee",
    FIELD_FEE_BASIS: "importer fee_basis",
    FIELD_WEIGHT_LIMIT: "importer weight_limit",
    FIELD_BREED_RESTRICTIONS: "importer breed_restrictions",
    FIELD_PETS_ALLOWED: "importer pets_allowed",
    FIELD_FEE_CURRENCY: "currency qualifier on importer pet_fee",
    FIELD_REFUNDABLE_DEPOSIT: "distinct from pet_fee -- never merged",
    FIELD_SERVICE_ANIMAL_NOTE: "advisory note; a legal access category, never a pet-policy signal",
}

# --------------------------------------------------------------------------- #
# Per-field support states (Stage 2).
# --------------------------------------------------------------------------- #

SUPPORTED = "SUPPORTED"
NOT_STATED = "NOT_STATED"
CONTRADICTORY = "CONTRADICTORY"
FIELD_STATES = frozenset({SUPPORTED, NOT_STATED, CONTRADICTORY})

# --------------------------------------------------------------------------- #
# Source-document types + retrieval statuses (Stage 1).
# --------------------------------------------------------------------------- #

SOURCE_OFFICIAL_PROPERTY = "OFFICIAL_PROPERTY"
SOURCE_OFFICIAL_BRAND = "OFFICIAL_BRAND"
SOURCE_OFFICIAL_FAQ = "OFFICIAL_FAQ"
SOURCE_OTHER = "OTHER"
SOURCE_TYPES = frozenset({SOURCE_OFFICIAL_PROPERTY, SOURCE_OFFICIAL_BRAND,
                          SOURCE_OFFICIAL_FAQ, SOURCE_OTHER})

# Only these count as official publication evidence; OTHER (e.g. a search
# snippet or a third-party directory) can NEVER support a published fact
# (Stage 3 rule 4).
OFFICIAL_SOURCE_TYPES = frozenset({SOURCE_OFFICIAL_PROPERTY, SOURCE_OFFICIAL_BRAND,
                                   SOURCE_OFFICIAL_FAQ})

# Property-specific official sources outrank general brand sources (Stage 3
# rules 5/6). Higher rank wins source selection; equal rank + contradiction is
# a genuine contradiction.
SOURCE_TYPE_RANK = {
    SOURCE_OFFICIAL_PROPERTY: 3,
    SOURCE_OFFICIAL_FAQ: 2,        # property-level FAQ, above brand-wide policy
    SOURCE_OFFICIAL_BRAND: 1,
    SOURCE_OTHER: 0,
}
# Which source types are "property-specific" vs "brand-wide" (rule 6).
PROPERTY_SPECIFIC_SOURCE_TYPES = frozenset({SOURCE_OFFICIAL_PROPERTY, SOURCE_OFFICIAL_FAQ})

RETRIEVAL_OK = "OK"
RETRIEVAL_BLOCKED = "BLOCKED"
RETRIEVAL_NOT_FOUND = "NOT_FOUND"
RETRIEVAL_ERROR = "ERROR"
RETRIEVAL_STATUSES = frozenset({RETRIEVAL_OK, RETRIEVAL_BLOCKED,
                                RETRIEVAL_NOT_FOUND, RETRIEVAL_ERROR})
USABLE_RETRIEVAL = frozenset({RETRIEVAL_OK})

# --------------------------------------------------------------------------- #
# Worker result statuses (Stage 2). The worker NEVER emits READY/REVIEW/REJECT
# -- those are Atlas's decision; these describe only what the worker found.
# --------------------------------------------------------------------------- #

STATUS_COMPLETED = "COMPLETED"
STATUS_NEEDS_REVIEW = "NEEDS_REVIEW"
STATUS_NO_OFFICIAL_SOURCE = "NO_OFFICIAL_SOURCE"
STATUS_CONTRADICTORY = "CONTRADICTORY"
STATUS_FAILED = "FAILED"
RESULT_STATUSES = frozenset({STATUS_COMPLETED, STATUS_NEEDS_REVIEW,
                             STATUS_NO_OFFICIAL_SOURCE, STATUS_CONTRADICTORY,
                             STATUS_FAILED})
