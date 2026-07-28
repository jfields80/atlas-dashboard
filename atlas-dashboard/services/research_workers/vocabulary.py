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
# PTF-WORKERS-004. A narrative report produced by a web-search-grounded model,
# NOT a page this system fetched. It is deliberately a distinct provenance from
# every OFFICIAL_* type and from OTHER, because the failure mode it guards
# against is specific: a model report can paraphrase, merge two properties, or
# summarize a page it half-read, and none of that is detectable by the verbatim
# quote check (the "quote" would be verbatim in the REPORT while being absent
# from the hotel's actual page). Treating it as its own source type is what lets
# routing withhold it by name instead of by accident.
SOURCE_MODEL_RESEARCH_REPORT = "MODEL_RESEARCH_REPORT"
# PTF-WORKERS-005. An official page whose property identity was established
# from its PARENT property page rather than from its own content -- e.g. an
# /amenities sub-page that carries the policy but repeats neither the street
# address nor the phone number. It is genuine official evidence (we fetched
# and hashed it), but the identity link is inferential, so it is publishable
# only after a human confirms it. See NON_AUTOMATIC_SOURCE_TYPES below.
SOURCE_OFFICIAL_PROPERTY_INHERITED = "OFFICIAL_PROPERTY_INHERITED"
# PTF-WORKERS-006. An official page a HUMAN opened in an ordinary browser and
# attested to, because Atlas cannot retrieve it (IHG/Akamai returns 403 to both
# the static fetcher and headless Chromium, and every technique that would
# defeat that is forbidden). The bytes are the official page's, transported by
# a person instead of by code -- so it is official evidence, but it can never
# publish without an explicit, separately recorded human approval.
SOURCE_MANUAL_OFFICIAL_ATTESTATION = "MANUAL_OFFICIAL_ATTESTATION"
SOURCE_TYPES = frozenset({SOURCE_OFFICIAL_PROPERTY, SOURCE_OFFICIAL_BRAND,
                          SOURCE_OFFICIAL_FAQ, SOURCE_OTHER,
                          SOURCE_MODEL_RESEARCH_REPORT,
                          SOURCE_OFFICIAL_PROPERTY_INHERITED,
                          SOURCE_MANUAL_OFFICIAL_ATTESTATION})

# Only these count as official publication evidence; OTHER (e.g. a search
# snippet or a third-party directory) can NEVER support a published fact
# (Stage 3 rule 4). MODEL_RESEARCH_REPORT is deliberately EXCLUDED: model
# research is a discovery aid, never directly-fetched official-page evidence.
OFFICIAL_SOURCE_TYPES = frozenset({SOURCE_OFFICIAL_PROPERTY, SOURCE_OFFICIAL_BRAND,
                                   SOURCE_OFFICIAL_FAQ,
                                   SOURCE_OFFICIAL_PROPERTY_INHERITED,
                                   SOURCE_MANUAL_OFFICIAL_ATTESTATION})

# Official enough to SUPPORT a fact, never enough to publish one automatically.
# Routing turns membership here into a mandatory REVIEW: the evidence is real,
# but a human confirms the identity link before it can reach a live page.
NON_AUTOMATIC_SOURCE_TYPES = frozenset({SOURCE_OFFICIAL_PROPERTY_INHERITED,
                                        SOURCE_MANUAL_OFFICIAL_ATTESTATION})

# Provenance that must never reach publication on its own, however well-formed.
# Kept as an explicit named set (rather than "not in OFFICIAL_SOURCE_TYPES") so
# the routing backstop can state WHICH non-official provenance it withheld.
NON_PUBLISHABLE_SOURCE_TYPES = frozenset({SOURCE_MODEL_RESEARCH_REPORT})

# Property-specific official sources outrank general brand sources (Stage 3
# rules 5/6). Higher rank wins source selection; equal rank + contradiction is
# a genuine contradiction.
SOURCE_TYPE_RANK = {
    SOURCE_OFFICIAL_PROPERTY: 3,
    SOURCE_OFFICIAL_FAQ: 2,        # property-level FAQ, above brand-wide policy
    SOURCE_OFFICIAL_BRAND: 1,
    SOURCE_OTHER: 0,
    # Ranked with OTHER at the bottom. Rank only orders sources that are ALREADY
    # publishable, and a MODEL_RESEARCH_REPORT never is, so this value can never
    # promote it -- it exists so rank lookups are total rather than defaulted.
    SOURCE_MODEL_RESEARCH_REPORT: 0,
    # Below OFFICIAL_FAQ and level with OFFICIAL_BRAND: a page whose identity is
    # inherited must never outrank one that identifies itself. Deliberately NOT
    # added to PROPERTY_SPECIFIC_SOURCE_TYPES -- rule 6 compares a property
    # source against a brand source, and an inherited-identity page has not
    # earned the property-specific side of that comparison.
    SOURCE_OFFICIAL_PROPERTY_INHERITED: 1,
    # Ranked BELOW every directly-fetched property source. A page a human
    # carried in is real evidence, but when Atlas has also fetched the property
    # itself, the fetched copy is the one with an unbroken machine chain of
    # custody and it must win source selection.
    SOURCE_MANUAL_OFFICIAL_ATTESTATION: 1,
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

# --------------------------------------------------------------------------- #
# ATLAS-WORKERS-006 -- structured tiered/conditional pet-fee vocabulary.
#
# The single scalar fields (pet_fee/fee_currency/fee_basis) cannot faithfully
# represent a recurring fee with a total cap, first-N/after-N tiers, short/long
# stay tiers, or a fee distinct from a refundable deposit. A PetFeePolicy is an
# ordered set of typed PetFeeTerm records. Per the AW-006 contract corrections:
# ROLE, BASIS, and SCOPE are DISTINCT typed dimensions -- never folded into a
# combinatorial value; boundaries are typed integers; amounts are canonical
# decimals separate from the verbatim quote.
# --------------------------------------------------------------------------- #

FEE_POLICY_VERSION = "1.0.0"

# Cardinal number words 0-20 -> digit (ATLAS-WORKERS-005/006). A written number
# ("two pets", "first six nights") is an EXPLICIT statement of a count, so it is
# recognized alongside digits; a bare plural names no number and is unsupported.
# Lives here as pure vocabulary so both the fact validator and the fee-term
# validator share one authority.
CARDINAL_WORDS = {
    "zero": 0, "one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6,
    "seven": 7, "eight": 8, "nine": 9, "ten": 10, "eleven": 11, "twelve": 12,
    "thirteen": 13, "fourteen": 14, "fifteen": 15, "sixteen": 16, "seventeen": 17,
    "eighteen": 18, "nineteen": 19, "twenty": 20,
}

# Role -- the semantic kind of money event (a CAP is never an ordinary charge).
FEE_ROLE_RECURRING_CHARGE = "RECURRING_CHARGE"   # a per-night / per-day recurring fee
FEE_ROLE_ONE_TIME_CHARGE = "ONE_TIME_CHARGE"     # a non-refundable one-time / per-stay fee
FEE_ROLE_CAP = "CAP"                             # an explicit maximum total for the stay
FEE_ROLE_DEPOSIT = "DEPOSIT"                     # a REFUNDABLE deposit (distinct from a fee)
FEE_TERM_ROLES = frozenset({FEE_ROLE_RECURRING_CHARGE, FEE_ROLE_ONE_TIME_CHARGE,
                            FEE_ROLE_CAP, FEE_ROLE_DEPOSIT})

# Basis -- the rate UNIT only (scope is a separate dimension, never folded in).
FEE_TERM_BASIS_PER_DAY = "per_day"
FEE_TERM_BASIS_PER_NIGHT = "per_night"
FEE_TERM_BASIS_PER_STAY = "per_stay"
FEE_TERM_BASIS_ONE_TIME = "one_time"
FEE_TERM_BASES = frozenset({FEE_TERM_BASIS_PER_DAY, FEE_TERM_BASIS_PER_NIGHT,
                            FEE_TERM_BASIS_PER_STAY, FEE_TERM_BASIS_ONE_TIME})

# Scope -- who/what the charge applies to (an independent dimension).
FEE_SCOPE_PER_ROOM = "per_room"
FEE_SCOPE_PER_PET = "per_pet"
FEE_SCOPE_POLICY_TOTAL = "policy_total"
FEE_SCOPE_UNSTATED = "unstated"                  # source states no scope -> never inferred
FEE_TERM_SCOPES = frozenset({FEE_SCOPE_PER_ROOM, FEE_SCOPE_PER_PET,
                             FEE_SCOPE_POLICY_TOTAL, FEE_SCOPE_UNSTATED})

# Applicability condition. A stay-length range subsumes first-N ([1, N]) and
# after-N ([N+1, null]); only values the evidence explicitly states are used.
FEE_CONDITION_UNCONDITIONAL = "unconditional"
FEE_CONDITION_STAY_LENGTH_RANGE = "stay_length_range"
FEE_CONDITION_TYPES = frozenset({FEE_CONDITION_UNCONDITIONAL, FEE_CONDITION_STAY_LENGTH_RANGE})

# Boundary unit for a stay-length-range condition.
BOUNDARY_UNIT_NIGHTS = "nights"
BOUNDARY_UNIT_DAYS = "days"
BOUNDARY_UNITS = frozenset({BOUNDARY_UNIT_NIGHTS, BOUNDARY_UNIT_DAYS})
