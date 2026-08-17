"""Closed vocabularies for the frozen PetTripFinder contracts.

Every enum here is CLOSED: a value outside the set is a validation failure, not
an unrecognised-but-tolerated extra. That is the whole purpose. Four markets
independently invented six spellings of fee scope, and every one of them was
accepted by a system that never checked, so twelve of fourteen values reached
no public surface at all. An open vocabulary is indistinguishable from no
vocabulary.

Style note: string constants plus frozensets, matching
``scripts/pettripfinder/policy/readiness.py``. Deliberately not ``enum.Enum`` --
these values are serialised to and from JSON on every read, and the surrounding
package already established the plain-string idiom. A second idiom would mean
every call site has to know which kind it is holding.

Legacy vocabularies
-------------------
The ``LEGACY_*`` maps are not part of the contract. They exist so
``compat_readers`` can translate today's committed records without a second
copy of the knowledge, and they are deleted when the compatibility window
closes at the end of Phase F.
"""

from __future__ import annotations

from typing import Dict, FrozenSet, Tuple

# --------------------------------------------------------------------------
# Fees
# --------------------------------------------------------------------------

#: What the charge recurs against. Only temporal/booking recurrence belongs
#: here -- scope and pet-count qualifiers have their own fields, because a
#: basis string like "per night for up to 2 pets" is three facts in a trench
#: coat and the renderer had to recover the third one with a regex.
BASIS_PER_NIGHT = "per_night"
BASIS_PER_DAY = "per_day"
BASIS_PER_STAY = "per_stay"

#: ``per_day`` is kept distinct from ``per_night`` even though lodging treats
#: them as the same arithmetic. The source said "daily"; changing that word is
#: a silent semantic edit, and §7 handles the equivalence at computation time
#: where it can be reasoned about rather than at write time where it cannot.
FEE_BASES: Tuple[str, ...] = (BASIS_PER_NIGHT, BASIS_PER_DAY, BASIS_PER_STAY)

#: Bases that mean "once per night of the stay", for computation only.
NIGHTLY_BASES: FrozenSet[str] = frozenset({BASIS_PER_NIGHT, BASIS_PER_DAY})

#: Who the charge attaches to. There is no "unstated" member: an unknown scope
#: is the ABSENCE of the key. A sentinel would have to be filtered out by every
#: consumer, and the one consumer that forgot would render "unstated" to a
#: guest as though the hotel had said it.
SCOPE_PER_ROOM = "per_room"
SCOPE_PER_PET = "per_pet"

FEE_SCOPES: Tuple[str, ...] = (SCOPE_PER_ROOM, SCOPE_PER_PET)

#: How a tier relates to its siblings. Until now every tier in the corpus
#: carried one role value, so the field discriminated nothing -- and two
#: unrelated charges stored as sibling tiers render as a range the source
#: never stated ("$100 fee + $200 cleaning fee" becoming "$100-$200").
ROLE_REPLACEMENT_PRICE = "REPLACEMENT_PRICE"
ROLE_ADDITIONAL_CHARGE = "ADDITIONAL_CHARGE"
ROLE_INCREMENTAL_UNIT_PRICE = "INCREMENTAL_UNIT_PRICE"

TIER_ROLES: Tuple[str, ...] = (ROLE_REPLACEMENT_PRICE, ROLE_ADDITIONAL_CHARGE,
                               ROLE_INCREMENTAL_UNIT_PRICE)

#: What a tier's condition range measures.
CONDITION_STAY_LENGTH_RANGE = "stay_length_range"
CONDITION_PET_COUNT_RANGE = "pet_count_range"

TIER_CONDITION_TYPES: Tuple[str, ...] = (CONDITION_STAY_LENGTH_RANGE,
                                         CONDITION_PET_COUNT_RANGE)

BOUNDARY_NIGHTS = "nights"
BOUNDARY_PETS = "pets"

TIER_BOUNDARY_UNITS: Tuple[str, ...] = (BOUNDARY_NIGHTS, BOUNDARY_PETS)

#: Charges that are not the pet fee itself. ``refundable`` is a separate
#: optional boolean and is NEVER inferred from this kind -- absence means the
#: source did not state it. Hilton renders "Deposit Yes. $75 Non-refundable
#: Fee", where the heading and the body disagree and only the body is true.
CHARGE_REFUNDABLE_DEPOSIT = "refundable_deposit"
CHARGE_NON_REFUNDABLE_FEE = "non_refundable_fee"
CHARGE_CLEANING_FEE = "cleaning_fee"
CHARGE_INCIDENTAL_DEPOSIT = "incidental_deposit"

OTHER_CHARGE_KINDS: Tuple[str, ...] = (
    CHARGE_REFUNDABLE_DEPOSIT, CHARGE_NON_REFUNDABLE_FEE,
    CHARGE_CLEANING_FEE, CHARGE_INCIDENTAL_DEPOSIT,
)

TAX_PLUS = "plus_tax"
TAX_INCLUSIVE = "tax_inclusive"

TAX_RELATIONSHIPS: Tuple[str, ...] = (TAX_PLUS, TAX_INCLUSIVE)

# --------------------------------------------------------------------------
# Fee computation readiness
# --------------------------------------------------------------------------

#: "A structured fee exists" must never be mistaken for "a total may be shown
#: to a guest". These four classes are the difference.
COMPUTATION_SAFE_ARBITRARY_ALLOWED_PET_COUNT = (
    "COMPUTATION_SAFE_ARBITRARY_ALLOWED_PET_COUNT")
COMPUTATION_SAFE_ONE_PET_ONLY = "COMPUTATION_SAFE_ONE_PET_ONLY"
CONDITIONALLY_SAFE = "CONDITIONALLY_SAFE"
NOT_COMPUTABLE = "NOT_COMPUTABLE"

COMPUTATION_CLASSES: Tuple[str, ...] = (
    COMPUTATION_SAFE_ARBITRARY_ALLOWED_PET_COUNT,
    COMPUTATION_SAFE_ONE_PET_ONLY,
    CONDITIONALLY_SAFE,
    NOT_COMPUTABLE,
)

#: Classes that may back a strict numeric fee filter for a single pet.
COMPUTABLE_FOR_ONE_PET: FrozenSet[str] = frozenset({
    COMPUTATION_SAFE_ARBITRARY_ALLOWED_PET_COUNT,
    COMPUTATION_SAFE_ONE_PET_ONLY,
})

#: Classes that may back a strict numeric fee filter for two or more pets.
COMPUTABLE_FOR_MANY_PETS: FrozenSet[str] = frozenset({
    COMPUTATION_SAFE_ARBITRARY_ALLOWED_PET_COUNT,
})

# --------------------------------------------------------------------------
# Size limits
# --------------------------------------------------------------------------

#: Comparison ONLY. "combined" is a scope and has never been a comparison;
#: admitting it here is the overload that left eleven records with no
#: recoverable answer to "is an eighty-pound dog allowed?".
OP_LT = "lt"
OP_LTE = "lte"

WEIGHT_OPERATORS: Tuple[str, ...] = (OP_LT, OP_LTE)

#: Scope of an individual weight limit. A combined limit is a SEPARATE FIELD
#: (``combined_weight_limit``) rather than a scope value, so the two limits
#: cannot share one operator and lose each other's comparison.
WEIGHT_SCOPE_PER_PET = "per_pet"
WEIGHT_SCOPE_PER_SPECIES = "per_species"

WEIGHT_SCOPES: Tuple[str, ...] = (WEIGHT_SCOPE_PER_PET, WEIGHT_SCOPE_PER_SPECIES)

UNIT_LB = "lb"
UNIT_KG = "kg"

WEIGHT_UNITS: Tuple[str, ...] = (UNIT_LB, UNIT_KG)

UNIT_IN = "in"
UNIT_CM = "cm"

DIMENSION_UNITS: Tuple[str, ...] = (UNIT_IN, UNIT_CM)

AXIS_LENGTH = "length"
AXIS_HEIGHT = "height"
AXIS_WIDTH = "width"

#: Inches are not pounds. Folding a "36 inches long" restriction into a weight
#: field would make every weight comparison in the match engine unsound.
DIMENSION_AXES: Tuple[str, ...] = (AXIS_LENGTH, AXIS_HEIGHT, AXIS_WIDTH)

# --------------------------------------------------------------------------
# Species
# --------------------------------------------------------------------------

SPECIES_ACCEPTED = "accepted"
SPECIES_PROHIBITED = "prohibited"
SPECIES_CONDITIONAL = "conditional"

#: A species the source does not name is ABSENT from the map. A generic "pets
#: welcome" yields an empty map, never dogs+cats -- the two markets that got
#: this right recorded the reasoning by hand and then had it discarded by a
#: renderer that could not see it.
SPECIES_STATES: Tuple[str, ...] = (SPECIES_ACCEPTED, SPECIES_PROHIBITED,
                                   SPECIES_CONDITIONAL)

#: Source authority tiers, reusing the PT1-PT4 vocabulary the policy layer
#: already established rather than inventing a parallel scale.
GRADE_PT1_FIRST_PARTY = "PT1_FIRST_PARTY"
GRADE_PT2_BRAND = "PT2_BRAND"
GRADE_PT3_THIRD_PARTY = "PT3_THIRD_PARTY"
GRADE_PT4_UNVERIFIED = "PT4_UNVERIFIED"

SOURCE_GRADES: Tuple[str, ...] = (GRADE_PT1_FIRST_PARTY, GRADE_PT2_BRAND,
                                  GRADE_PT3_THIRD_PARTY, GRADE_PT4_UNVERIFIED)

#: Below this grade a claim may only RESTRICT, never permit. Aggregators
#: over-report acceptance; a restrictive third-party claim is safe to surface
#: with attribution, a permissive one is not.
FIRST_PARTY_GRADES: FrozenSet[str] = frozenset({GRADE_PT1_FIRST_PARTY,
                                                GRADE_PT2_BRAND})

#: What a property said about charging for service animals. Kept OUTSIDE the
#: pet-policy facts block entirely (see ``policy_schema``): a legal access
#: category must not share a namespace with commercial terms, or a weight limit
#: sitting beside it invites something to apply one to the other.
SERVICE_ANIMAL_NO_CHARGE = "no_charge"
SERVICE_ANIMAL_CHARGE_STATED = "charge_stated"
SERVICE_ANIMAL_NOT_ADDRESSED = "not_addressed"

SERVICE_ANIMAL_CHARGE_STATES: Tuple[str, ...] = (
    SERVICE_ANIMAL_NO_CHARGE, SERVICE_ANIMAL_CHARGE_STATED,
    SERVICE_ANIMAL_NOT_ADDRESSED,
)

# --------------------------------------------------------------------------
# Withholding
# --------------------------------------------------------------------------

SOURCE_SILENT = "SOURCE_SILENT"
SOURCE_AMBIGUOUS = "SOURCE_AMBIGUOUS"
SOURCE_CONTRADICTORY = "SOURCE_CONTRADICTORY"
SCHEMA_CANNOT_REPRESENT = "SCHEMA_CANNOT_REPRESENT"
ARTIFACT_INSUFFICIENT = "ARTIFACT_INSUFFICIENT"
IDENTITY_NOT_CONFIRMED = "IDENTITY_NOT_CONFIRMED"

#: The full taxonomy, including SOURCE_SILENT -- the observation and partition
#: layers legitimately need to say "we looked and the page said nothing".
WITHHOLDING_REASONS: Tuple[str, ...] = (
    SOURCE_SILENT, SOURCE_AMBIGUOUS, SOURCE_CONTRADICTORY,
    SCHEMA_CANNOT_REPRESENT, ARTIFACT_INSUFFICIENT, IDENTITY_NOT_CONFIRMED,
)

#: What may appear inside a record's ``withheld_fields`` map. SOURCE_SILENT is
#: excluded ON PURPOSE. ``withheld_fields`` must mean exactly one thing -- we
#: know something and are choosing not to publish it. Admitting silence would
#: make the map a mixture of editorial decisions and non-events, force every
#: consumer to read the reason code to tell which, and require a sparse page to
#: enumerate fifteen entries of nothing. Silence is represented by ABSENCE.
WITHHELD_FIELD_REASONS: FrozenSet[str] = frozenset(WITHHOLDING_REASONS) - {
    SOURCE_SILENT}

#: Reasons that say the evidence CHAIN is broken rather than the source being
#: unclear. A record carrying one of these cannot publish at all: it makes no
#: sense to trust a chain for some facts and not others.
RECORD_BLOCKING_REASONS: FrozenSet[str] = frozenset({
    ARTIFACT_INSUFFICIENT, IDENTITY_NOT_CONFIRMED,
})

# --------------------------------------------------------------------------
# Evidence
# --------------------------------------------------------------------------

PUBLICATION_GRADE_EVIDENCE = "PUBLICATION_GRADE_EVIDENCE"
POINTER_TO_EVIDENCE = "POINTER_TO_EVIDENCE"
ROUTING_ONLY = "ROUTING_ONLY"
IDENTITY_ONLY = "IDENTITY_ONLY"
TRANSCRIPTION_ONLY = "TRANSCRIPTION_ONLY"
UNACCEPTABLE_FOR_PUBLICATION = "UNACCEPTABLE_FOR_PUBLICATION"

ARTIFACT_CLASSES: Tuple[str, ...] = (
    PUBLICATION_GRADE_EVIDENCE, POINTER_TO_EVIDENCE, ROUTING_ONLY,
    IDENTITY_ONLY, TRANSCRIPTION_ONLY, UNACCEPTABLE_FOR_PUBLICATION,
)

#: Hashing a transcription proves the typing was not altered. It proves nothing
#: about what the webpage said, so a hash-bound CSV never becomes page evidence.
MAY_PUBLISH_FACTS: FrozenSet[str] = frozenset({PUBLICATION_GRADE_EVIDENCE})
MAY_PROPOSE_FACTS: FrozenSet[str] = frozenset({
    PUBLICATION_GRADE_EVIDENCE, POINTER_TO_EVIDENCE, TRANSCRIPTION_ONLY})
MAY_PROPOSE_ROUTING: FrozenSet[str] = frozenset({
    PUBLICATION_GRADE_EVIDENCE, POINTER_TO_EVIDENCE, ROUTING_ONLY,
    TRANSCRIPTION_ONLY})
MAY_CONFIRM_IDENTITY: FrozenSet[str] = frozenset({
    PUBLICATION_GRADE_EVIDENCE, POINTER_TO_EVIDENCE, IDENTITY_ONLY})

ARTIFACT_RENDERED_HTML = "rendered_html"
ARTIFACT_OPERATOR_SCREENSHOT = "operator_screenshot"
ARTIFACT_PDF = "pdf"

#: What was hashed. An operator screenshot of the page is a lawful artifact of
#: the page; a screenshot of a spreadsheet about the page is not.
ARTIFACT_KINDS: Tuple[str, ...] = (ARTIFACT_RENDERED_HTML,
                                   ARTIFACT_OPERATOR_SCREENSHOT, ARTIFACT_PDF)

# --------------------------------------------------------------------------
# Approval
# --------------------------------------------------------------------------

APPROVED_AFTER_CURRENT_REVIEW = "APPROVED_AFTER_CURRENT_REVIEW"
LEGACY_BASELINE_REVIEWED = "LEGACY_BASELINE_REVIEWED"
MACHINE_REVIEWED_PENDING_OPERATOR = "MACHINE_REVIEWED_PENDING_OPERATOR"
HELD_FOR_REVIEW = "HELD_FOR_REVIEW"
REJECTED = "REJECTED"
SUPERSEDED = "SUPERSEDED"

APPROVAL_DECISIONS: Tuple[str, ...] = (
    APPROVED_AFTER_CURRENT_REVIEW, LEGACY_BASELINE_REVIEWED,
    MACHINE_REVIEWED_PENDING_OPERATOR, HELD_FOR_REVIEW, REJECTED, SUPERSEDED,
)

#: ``LEGACY_BASELINE_REVIEWED`` exists so the twenty-six Columbus records with
#: no recorded decision can be remediated HONESTLY. It carries today's date and
#: today's reviewer, because that is what actually happened. Back-dating them
#: to APPROVED would invent an approval nobody gave.
PUBLISHING_DECISIONS: FrozenSet[str] = frozenset({
    APPROVED_AFTER_CURRENT_REVIEW, LEGACY_BASELINE_REVIEWED,
})

# --------------------------------------------------------------------------
# Partition
# --------------------------------------------------------------------------

PUBLISHED_PET_FRIENDLY = "PUBLISHED_PET_FRIENDLY"
VERIFIED_NO_PETS = "VERIFIED_NO_PETS"
OUT_OF_CURRENT_CATEGORY = "OUT_OF_CURRENT_CATEGORY"

#: Terminal states have no outstanding next action. A published hotel with work
#: still to do is a contradiction the partition must be able to reject.
TERMINAL_STATES: Tuple[str, ...] = (PUBLISHED_PET_FRIENDLY, VERIFIED_NO_PETS,
                                    OUT_OF_CURRENT_CATEGORY)

AWAITING_OFFICIAL_URL = "AWAITING_OFFICIAL_URL"
AWAITING_PROPERTY_LEVEL_URL = "AWAITING_PROPERTY_LEVEL_URL"
AWAITING_ROUTING_REVIEW = "AWAITING_ROUTING_REVIEW"
AWAITING_ROUTING_REPLACEMENT = "AWAITING_ROUTING_REPLACEMENT"
AWAITING_POLICY_OBSERVATION = "AWAITING_POLICY_OBSERVATION"
AWAITING_POLICY_ARTIFACT = "AWAITING_POLICY_ARTIFACT"
AWAITING_ATTENDED_CAPTURE = "AWAITING_ATTENDED_CAPTURE"
AWAITING_CONTRADICTION_RESOLUTION = "AWAITING_CONTRADICTION_RESOLUTION"
AWAITING_CENSUS_REVIEW = "AWAITING_CENSUS_REVIEW"
AWAITING_IDENTITY_RESOLUTION = "AWAITING_IDENTITY_RESOLUTION"
ACCESS_BLOCKED = "ACCESS_BLOCKED"

#: Eleven blockers, normalised from the four markets' own vocabularies. The
#: corpus held ACCESS_BLOCKED, ADR_ACCESS_BLOCKED, SOURCE_BLOCKED and
#: ANTI_BOT_CHALLENGE for one concept and five spellings of "no property URL";
#: dozens of aliases for the same state is a vocabulary nobody can query.
BLOCKER_STATES: Tuple[str, ...] = (
    AWAITING_OFFICIAL_URL, AWAITING_PROPERTY_LEVEL_URL,
    AWAITING_ROUTING_REVIEW, AWAITING_ROUTING_REPLACEMENT,
    AWAITING_POLICY_OBSERVATION, AWAITING_POLICY_ARTIFACT,
    AWAITING_ATTENDED_CAPTURE, AWAITING_CONTRADICTION_RESOLUTION,
    AWAITING_CENSUS_REVIEW, AWAITING_IDENTITY_RESOLUTION, ACCESS_BLOCKED,
)

PARTITION_STATES: Tuple[str, ...] = TERMINAL_STATES + BLOCKER_STATES

# --------------------------------------------------------------------------
# Census / geography
# --------------------------------------------------------------------------

IDENTITY_CONFIRMED = "IDENTITY_CONFIRMED"
IDENTITY_PROVISIONAL = "IDENTITY_PROVISIONAL"
IDENTITY_UNRESOLVED = "IDENTITY_UNRESOLVED"

IDENTITY_STATES: Tuple[str, ...] = (IDENTITY_CONFIRMED, IDENTITY_PROVISIONAL,
                                    IDENTITY_UNRESOLVED)

LODGING_CONFIRMED = "LODGING_CONFIRMED"
LODGING_BY_NAME = "LODGING_BY_NAME"
LODGING_NEEDS_REVIEW = "NEEDS_REVIEW"
NOT_LODGING = "NOT_LODGING"

LODGING_STATES: Tuple[str, ...] = (LODGING_CONFIRMED, LODGING_BY_NAME,
                                   LODGING_NEEDS_REVIEW, NOT_LODGING)

#: A lodging value that is really a POLICY fact. Eight Dayton rows carry it,
#: and it is the three-axis model collapsing: whether a property takes pets has
#: nothing to do with whether it is a hotel. Reported as its own defect rather
#: than as a generic bad enum, because the remedy is to move the fact to
#: ``policy_state`` and restore the row's real lodging value.
LODGING_AXIS_VIOLATIONS: Dict[str, str] = {"LODGING_NO_PETS": VERIFIED_NO_PETS}

POLICY_NOT_VERIFIED = "POLICY_NOT_VERIFIED"
POLICY_OBSERVED = "POLICY_OBSERVED"
POLICY_CONFIRMED = "POLICY_CONFIRMED"

#: ADVISORY ONLY. The partition is the authority on disposition; a census
#: policy annotation exists to help a human triage and is never read by a gate.
#: Dayton carries three stale ones today, which is exactly why.
#:
#: ``VERIFIED_NO_PETS`` is the committed spelling and is reused rather than
#: renamed -- the exclusion registry and the partition already call a captured
#: refusal that, and a fourth name for one concept is the divergence this
#: freeze exists to end. The observation layer's own
#: ``POLICY_NEGATIVE_CONFIRMED`` (readiness.py) is a different layer's state and
#: is deliberately not imported here.
CENSUS_POLICY_STATES: Tuple[str, ...] = (
    POLICY_NOT_VERIFIED, POLICY_OBSERVED, POLICY_CONFIRMED, VERIFIED_NO_PETS,
)

COLLISION_NONE = "NONE"
COLLISION_SHARED_ADDRESS = "SHARED_ADDRESS"
COLLISION_SHARED_PHONE = "SHARED_PHONE"
COLLISION_PROPERTY_CODE = "PROPERTY_CODE_COLLISION"
COLLISION_RESOLVED = "RESOLVED"

COLLISION_STATES: Tuple[str, ...] = (
    COLLISION_NONE, COLLISION_SHARED_ADDRESS, COLLISION_SHARED_PHONE,
    COLLISION_PROPERTY_CODE, COLLISION_RESOLVED,
)

BASIS_EXPLICIT = "explicit"
BASIS_POSTAL_CODE = "postal_code"
BASIS_CITY_STATE = "city_state"
BASIS_UNASSIGNED = "unassigned"

#: The basis that ACTUALLY fired, recorded alongside the value that fired it.
#: Cincinnati labels all 121 rows ``postal_code`` and seven of them are human
#: judgement whose ZIP appears in no corridor -- a claim that cannot be checked
#: is a claim that will be wrong.
ASSIGNMENT_BASES: Tuple[str, ...] = (BASIS_EXPLICIT, BASIS_POSTAL_CODE,
                                     BASIS_CITY_STATE, BASIS_UNASSIGNED)

#: Legacy basis spellings, and what they become.
#:
#: ``city_name`` is the state-blind ancestor of ``city_state`` -- the same tier,
#: matching on a bare city string, which is exactly the defect the freeze
#: corrects. 109 Dayton rows carry it and translate cleanly.
LEGACY_ASSIGNMENT_BASES: Dict[str, str] = {"city_name": BASIS_CITY_STATE}

#: Bases claimed by committed data that the assignment code CANNOT PRODUCE.
#: ``assignment.py`` implements explicit, city and ZIP tiers and nothing else,
#: so an eleven-row county claim in the Dayton census is unreproducible by
#: construction: no run of the assigner will ever agree with it.
#:
#: This is the same class of defect as Cincinnati's seven false ``postal_code``
#: claims, and a larger instance of it. Both are resolved the same way -- either
#: the registry gains the data that makes the claim true, or the rows become
#: ``explicit``, which is honest about a human having decided.
UNIMPLEMENTED_ASSIGNMENT_BASES: FrozenSet[str] = frozenset({"county_name"})

# --------------------------------------------------------------------------
# Routing
# --------------------------------------------------------------------------

ROUTING_CONFIRMED = "ROUTING_CONFIRMED"
ROUTING_HELD = "ROUTING_HELD"
ROUTING_RETIRED = "ROUTING_RETIRED"

ROUTING_STATES: Tuple[str, ...] = (ROUTING_CONFIRMED, ROUTING_HELD,
                                   ROUTING_RETIRED)

BINDING_PAGE_RENDERED = "PAGE_RENDERED"
BINDING_BRAND_INDEX = "BRAND_INDEX_BINDING"

BINDING_METHODS: Tuple[str, ...] = (BINDING_PAGE_RENDERED, BINDING_BRAND_INDEX)

#: A brand-index binding is corroborated but not first-party confirmed. It is
#: ROUTING evidence and never publication-grade, however many sources agree.
PROPERTY_LEVEL_BINDINGS: FrozenSet[str] = frozenset({BINDING_PAGE_RENDERED})

CATEGORY_ACCOMMODATION = "accommodation"

ROUTING_CATEGORIES: Tuple[str, ...] = (CATEGORY_ACCOMMODATION,)

# --------------------------------------------------------------------------
# Coordinates
# --------------------------------------------------------------------------

PRECISION_EXACT_PROPERTY = "EXACT_PROPERTY"
PRECISION_ROOFTOP_GEOCODED = "ROOFTOP_GEOCODED"
PRECISION_POSTAL_CENTROID = "POSTAL_CENTROID"
PRECISION_MUNICIPAL_CENTROID = "MUNICIPAL_CENTROID"
PRECISION_DISCOVERY_CELL = "DISCOVERY_CELL"

COORDINATE_PRECISIONS: Tuple[str, ...] = (
    PRECISION_EXACT_PROPERTY, PRECISION_ROOFTOP_GEOCODED,
    PRECISION_POSTAL_CENTROID, PRECISION_MUNICIPAL_CENTROID,
    PRECISION_DISCOVERY_CELL,
)

#: Distance, "nearest vet", proximity ranking and map pins accept these and
#: nothing else. A centroid places a hotel on a road it is not on, and a reader
#: cannot tell the difference -- so the restriction is enforced by the type
#: rather than by remembering.
PROXIMITY_GRADE_PRECISIONS: FrozenSet[str] = frozenset({
    PRECISION_EXACT_PROPERTY, PRECISION_ROOFTOP_GEOCODED,
})

# --------------------------------------------------------------------------
# Route modes
# --------------------------------------------------------------------------

ROUTE_MODE_MARKET_PREFIXED = "market_prefixed"
ROUTE_MODE_LEGACY_UNPREFIXED = "legacy_unprefixed"

ROUTE_MODES: Tuple[str, ...] = (ROUTE_MODE_MARKET_PREFIXED,
                                ROUTE_MODE_LEGACY_UNPREFIXED)

#: Exactly one market may hold the legacy mode, and it is Columbus, whose
#: eighty-eight profiles are live and indexed. Registering the exception as
#: single-market is what stops it spreading to every market that finds
#: prefixing inconvenient.
LEGACY_ROUTE_MODE_MARKET = "columbus-oh"

# --------------------------------------------------------------------------
# Legacy vocabularies -- compatibility only, deleted at the end of Phase F
# --------------------------------------------------------------------------

#: Six spellings of fee scope reached the corpus; one rendered.
LEGACY_FEE_SCOPES: Dict[str, str] = {
    "per_room": SCOPE_PER_ROOM,
    "per room": SCOPE_PER_ROOM,
    "per_pet": SCOPE_PER_PET,
    "per pet": SCOPE_PER_PET,
}

#: Scope values that mean "the source did not say". They become ABSENCE, not a
#: translated sentinel.
LEGACY_SCOPE_ABSENT: FrozenSet[str] = frozenset({"unknown", "unstated", ""})

#: Compound bases carry a basis, a scope and sometimes a pet allowance in one
#: string. The decomposition is total and lossless; the third value is the one
#: the renderer had been recovering with a regex.
LEGACY_FEE_BASES: Dict[str, Tuple[str, str, int]] = {
    # legacy string -> (basis, scope or "", scope_pet_allowance or 0)
    "per night": (BASIS_PER_NIGHT, "", 0),
    "per stay": (BASIS_PER_STAY, "", 0),
    "per day": (BASIS_PER_DAY, "", 0),
    "per room per night": (BASIS_PER_NIGHT, SCOPE_PER_ROOM, 0),
    "per room per day": (BASIS_PER_DAY, SCOPE_PER_ROOM, 0),
    "per pet per night": (BASIS_PER_NIGHT, SCOPE_PER_PET, 0),
    "per stay per pet": (BASIS_PER_STAY, SCOPE_PER_PET, 0),
    "per night for up to 2 pets": (BASIS_PER_NIGHT, SCOPE_PER_ROOM, 2),
}

#: The overloaded operator field. ``combined`` is not translated to an
#: operator -- it is a SCOPE token, and the record's real comparison has to be
#: re-read from its evidence quote by a human. Defaulting either way is a
#: guest-visible error: ``lte`` admits an eighty-pound dog to a property that
#: wrote "under 80 pounds", and ``lt`` turns away one the hotel accepts.
LEGACY_WEIGHT_OPERATORS: Dict[str, str] = {"lt": OP_LT, "lte": OP_LTE}
LEGACY_COMBINED_SCOPE_TOKEN = "combined"

#: Columbus's four approval strings. The two qualified forms carry real
#: information, which migrates into a caveats list rather than being flattened.
LEGACY_APPROVAL_DECISIONS: Dict[str, str] = {
    "APPROVED": APPROVED_AFTER_CURRENT_REVIEW,
    "APPROVED_FOR_PROMOTION": APPROVED_AFTER_CURRENT_REVIEW,
    "APPROVED_TIERED_FEE_OMITTED": APPROVED_AFTER_CURRENT_REVIEW,
    "APPROVE_WITH_DIAGNOSTIC_ACKNOWLEDGEMENT": APPROVED_AFTER_CURRENT_REVIEW,
}

#: Approval strings that carry a caveat worth keeping.
LEGACY_APPROVAL_CAVEATS: Dict[str, str] = {
    "APPROVED_TIERED_FEE_OMITTED": "tiered_fee_omitted",
    "APPROVE_WITH_DIAGNOSTIC_ACKNOWLEDGEMENT": "diagnostic_acknowledged",
}

#: Both committed census schema names describe the same shape.
LEGACY_CENSUS_SCHEMAS: FrozenSet[str] = frozenset({
    "ptf-market-identity-census/1.0", "ptf-identity-census/1.0",
})

CENSUS_SCHEMA = "ptf-market-identity-census/1.1"
PARTITION_SCHEMA = "ptf-market-final-partition/1.1"
POLICY_SCHEMA_VERSION = "1.2"

#: Policy schema versions a compatibility reader accepts.
LEGACY_POLICY_SCHEMA_VERSIONS: FrozenSet[str] = frozenset({"1.0", "1.1"})


def is_member(value: str, vocabulary: Tuple[str, ...]) -> bool:
    """Closed-vocabulary membership.

    Trivial by design: every validator in this package asks the question the
    same way, so there is one place to change if membership ever needs to mean
    something subtler than equality.
    """
    return value in vocabulary
