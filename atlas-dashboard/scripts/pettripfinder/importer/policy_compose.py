"""AES-DATA-001 importer -- deterministic pet_policy composition (mission
section 13). Builds the ``pet_policy`` CSV field from accepted structured
facts using fixed templates. No LLM prose is ever used. A clause appears
only when its fact is present; a sparse-but-pet-friendly source falls back
to the approved conservative wording; no pet evidence yields "".
"""

from __future__ import annotations

from typing import Dict

from scripts.pettripfinder.importer.constants import (
    CATEGORY_BOARDING,
    CATEGORY_GROOMING,
    CATEGORY_HOTELS,
    CATEGORY_PARKS,
    CATEGORY_PET_STORE,
    CATEGORY_RESTAURANTS,
    CATEGORY_VETERINARY,
)

_CONSERVATIVE = (
    "The property identifies itself as pet-friendly. Confirm current fees "
    "and restrictions directly with the business."
)
_CONSERVATIVE_PARK = (
    "This location is identified as pet-friendly on its official page. "
    "Confirm current rules directly with the park authority."
)


def _clause(text: str) -> str:
    text = text.strip()
    if not text.endswith("."):
        text += "."
    return text


def _hotel_clauses(f: Dict[str, str]) -> list:
    out = []
    species = (f.get("species_allowed") or "").lower()
    if "dog" in species and "cat" in species:
        out.append("Dogs and cats are accepted")
    elif "dog" in species:
        out.append("Dogs are accepted")
    elif "cat" in species:
        out.append("Cats are accepted")
    fee = f.get("pet_fee")
    if fee:
        basis = (f.get("fee_basis") or "").strip()
        out.append("A %s fee applies%s" % (fee, (" %s" % basis) if basis else ""))
    count = f.get("pet_count_limit")
    if count:
        out.append("A maximum of %s pet%s is allowed" % (count, "" if count == "1" else "s"))
    weight = f.get("weight_limit")
    if weight:
        out.append("Pets may not exceed %s" % weight)
    if (f.get("unattended_policy") or "").lower() in ("no", "false", "not allowed"):
        out.append("Pets may not be left unattended")
    if f.get("general_restrictions"):
        out.append(f["general_restrictions"].rstrip("."))
    return out


def _park_clauses(f: Dict[str, str]) -> list:
    out = []
    if f.get("off_leash") == "true":
        desc = (f.get("off_leash_area_description") or "").strip()
        out.append("Dogs may be off leash in the designated area"
                   + ((" (%s)" % desc) if desc else ""))
    elif f.get("leash_rule"):
        out.append(f["leash_rule"].rstrip("."))
    if f.get("fenced") == "true":
        out.append("The dog area is fenced")
    if f.get("small_dog_area") == "true" and f.get("large_dog_area") == "true":
        out.append("Separate areas are provided for small and large dogs")
    if f.get("water_available") == "true":
        out.append("Water is available")
    if f.get("trails"):
        out.append(f["trails"].rstrip("."))
    return out


def _restaurant_clauses(f: Dict[str, str]) -> list:
    out = []
    area = (f.get("permitted_area") or "").strip()
    if f.get("patio_or_outdoor_only") == "true":
        out.append("Dogs are welcome in the outdoor%s area"
                   % ((" %s" % area) if area and area.lower() != "patio" else " patio"))
    elif area:
        out.append("Dogs are welcome in the %s" % area)
    if f.get("indoor_prohibited") == "true":
        out.append("Dogs are not permitted indoors")
    caveat = (f.get("seasonal_or_weather_caveat") or "").strip()
    if caveat:
        out.append(caveat.rstrip("."))
    if f.get("water_or_treats") == "true":
        out.append("Water is provided for dogs")
    if f.get("dog_menu") == "true":
        out.append("A dog menu is available")
    return out


def _veterinary_clauses(f: Dict[str, str]) -> list:
    """AES-DATA-003B: every clause below reads an already evidence-validated
    fact from ``pet_facts`` (built upstream from SUPPORTED/AMBIGUOUS
    evidence only, per the shared ``compose_pet_policy`` contract) -- this
    function composes text from validated facts, it never itself infers a
    fact. A high-risk fact (emergency/urgent/24h/walk-ins/existing-clients)
    is stated only when its own field is present; it is never derived from
    another field here."""
    out = []
    if f.get("general_practice") == "true":
        out.append("Provides general veterinary practice services")
    if f.get("preventive_care") == "true":
        out.append("Offers preventive care")
    if f.get("vaccinations") == "true":
        out.append("Offers vaccinations")
    if f.get("surgery") == "true":
        out.append("Offers surgery")
    if f.get("dentistry") == "true":
        out.append("Offers dentistry")
    if f.get("pharmacy") == "true":
        out.append("Has an on-site pharmacy")
    if f.get("emergency_service") == "true":
        out.append("Provides emergency veterinary services")
    elif f.get("emergency_service") == "false":
        out.append("Does not provide emergency veterinary services")
    if f.get("urgent_care") == "true":
        out.append("Provides urgent care")
    if f.get("open_24h") == "true":
        out.append("Open 24 hours")
    if f.get("walk_ins_accepted") == "true":
        out.append("Walk-ins are accepted")
    elif f.get("walk_ins_accepted") == "false":
        out.append("Walk-ins are not accepted; appointments are required")
    if f.get("existing_clients_only") == "true":
        out.append("Some services are limited to existing clients")
    if f.get("critical_care") == "true":
        out.append("Provides critical care")
    species = (f.get("species_served") or "").strip()
    if species:
        out.append("Treats %s" % species)
    specialty = (f.get("specialty_care") or "").strip()
    if specialty:
        out.append("Specialty care: %s" % specialty)
    if f.get("wellness_exams") == "true":
        out.append("Offers wellness exams")
    if f.get("diagnostics") == "true":
        out.append("Offers diagnostics")
    if f.get("prescription_fulfillment") == "true":
        out.append("Fulfills prescriptions")
    if f.get("appointment_required") == "true":
        out.append("Appointments are required")
    after_hours = (f.get("after_hours_instructions") or "").strip()
    if after_hours:
        out.append("After-hours: %s" % after_hours)
    # A veterinary fact was evidenced (``f`` is never populated with an
    # unvalidated field) but none of the specific templates above matched
    # it -- still publish a non-empty, evidence-backed summary rather than
    # silently leaving ``pet_policy`` (a REQUIRED_CSV_FIELDS member for
    # every category) empty.
    if not out and f:
        out.append("This practice provides veterinary services")
    return out


# --------------------------------------------------------------------------- #
# AES-DATA-003C -- TEMPORARY COMPATIBILITY SUMMARIES.
#
# The legacy required-CSV contract (REQUIRED_CSV_FIELDS, constants.py) still
# demands a non-empty ``pet_policy`` column for READY, for every category,
# including these three service categories where "pet_policy" is not a
# literal pet-admission policy at all. AES-DATA-003B already established
# this workaround for veterinary; this is the SAME narrow, disclosed
# workaround for boarding/grooming/pet_store -- do not multiply it further
# without also opening a category-aware promotion phase (see the module-
# level warning below). Each builder composes ONLY from already evidence-
# validated facts (the shared ``compose_pet_policy`` contract guarantees
# ``pet_facts`` here holds SUPPORTED/AMBIGUOUS values only), never invents
# pricing/availability/species-acceptance/restriction text that is not
# itself a validated fact, and the pack's own Capability/CategoryDetail
# projections remain the authoritative structured facts -- this text is a
# compatibility summary only, not a second source of truth.
#
# TODO(a later category-aware promotion phase): remove the universal
# dependence on ``pet_policy`` for service businesses (boarding/grooming/
# pet_store/veterinary) and replace it with a category-aware published-
# facts schema that reads Capability/CategoryDetail directly instead of a
# single free-text CSV column.
# --------------------------------------------------------------------------- #

def _boarding_clauses(f: Dict[str, str]) -> list:
    """Temporary compatibility summary for the legacy universal pet_policy
    column. Replace with category-aware promotion schema in a later phase."""
    out = []
    if f.get("boarding_offered") == "true":
        out.append("Offers overnight boarding")
    if f.get("daycare_offered") == "true":
        out.append("Offers dog daycare")
    if f.get("dog_boarding") == "true":
        out.append("Boards dogs")
    if f.get("cat_boarding") == "true":
        out.append("Boards cats")
    if f.get("other_species_boarding") == "true":
        out.append("Boards other species")
    if f.get("grooming_offered") == "true":
        out.append("Offers grooming")
    if f.get("medication_administration") == "true":
        out.append("Administers medication")
    if f.get("live_camera") == "true":
        out.append("Offers a live camera")
    if f.get("reservation_required") == "true":
        out.append("Reservations are required")
    if f.get("same_day_availability") == "true":
        out.append("Same-day availability has been stated by the business")
    if f.get("pricing_available") == "true":
        out.append("Pricing information is available")
    vaccination = (f.get("vaccination_requirements") or "").strip()
    if vaccination:
        out.append("Vaccination requirements: %s" % vaccination)
    temperament = (f.get("temperament_evaluation") or "").strip()
    if temperament:
        out.append("Temperament evaluation: %s" % temperament)
    windows = (f.get("pickup_dropoff_windows") or "").strip()
    if windows:
        out.append("Pickup/drop-off windows: %s" % windows)
    if not out and f:
        out.append("This business provides boarding or daycare services")
    return out


def _grooming_clauses(f: Dict[str, str]) -> list:
    """Temporary compatibility summary for the legacy universal pet_policy
    column. Replace with category-aware promotion schema in a later phase."""
    out = []
    if f.get("grooming_offered") == "true":
        out.append("Offers grooming")
    if f.get("dog_grooming") == "true":
        out.append("Grooms dogs")
    if f.get("cat_grooming") == "true":
        out.append("Grooms cats")
    if f.get("bathing") == "true":
        out.append("Offers bathing")
    if f.get("nail_trimming") == "true":
        out.append("Offers nail trimming")
    if f.get("deshedding") == "true":
        out.append("Offers deshedding")
    if f.get("mobile_service") == "true":
        out.append("Offers mobile service")
    if f.get("appointment_required") == "true":
        out.append("Available by appointment")
    if f.get("walk_ins_accepted") == "true":
        out.append("Walk-ins are accepted")
    elif f.get("walk_ins_accepted") == "false":
        out.append("Walk-ins are not accepted; appointments are required")
    if f.get("pricing_available") == "true":
        out.append("Pricing information is available")
    breed = (f.get("breed_restrictions") or "").strip()
    if breed:
        out.append("Breed restrictions: %s" % breed)
    size = (f.get("size_restrictions") or "").strip()
    if size:
        out.append("Size restrictions: %s" % size)
    area = (f.get("service_area") or "").strip()
    if area:
        out.append("Service area: %s" % area)
    if not out and f:
        out.append("This business provides grooming services")
    return out


def _pet_store_clauses(f: Dict[str, str]) -> list:
    """Temporary compatibility summary for the legacy universal pet_policy
    column. Replace with category-aware promotion schema in a later phase."""
    out = []
    if f.get("retail_products") == "true":
        out.append("Sells pet products")
    if f.get("pet_food") == "true":
        out.append("Sells pet food")
    if f.get("pet_supplies") == "true":
        out.append("Sells pet supplies")
    if f.get("pharmacy") == "true":
        out.append("Has an on-site pharmacy")
    if f.get("prescription_fulfillment") == "true":
        out.append("Fulfills prescriptions")
    if f.get("prescription_food") == "true":
        out.append("Sells prescription pet food")
    if f.get("grooming_offered") == "true":
        out.append("Offers grooming")
    if f.get("self_wash") == "true":
        out.append("Offers self-wash")
    if f.get("vaccination_clinic") == "true":
        out.append("Offers a vaccination clinic")
    if f.get("live_animals") == "true":
        out.append("Sells live animals")
    if f.get("curbside_pickup") == "true":
        out.append("Offers curbside pickup")
    if f.get("delivery") == "true":
        out.append("Offers delivery")
    if f.get("online_ordering") == "true":
        out.append("Offers online ordering")
    if not out and f:
        out.append("This business is a pet supply store")
    return out


_BUILDERS = {
    CATEGORY_HOTELS: _hotel_clauses,
    CATEGORY_PARKS: _park_clauses,
    CATEGORY_RESTAURANTS: _restaurant_clauses,
    CATEGORY_VETERINARY: _veterinary_clauses,
    CATEGORY_BOARDING: _boarding_clauses,
    CATEGORY_GROOMING: _grooming_clauses,
    CATEGORY_PET_STORE: _pet_store_clauses,
}


def compose_pet_policy(pet_facts: Dict[str, str], category: str) -> str:
    """Compose the deterministic ``pet_policy`` statement. ``pet_facts`` maps
    field -> normalized value for SUPPORTED/AMBIGUOUS facts only. Returns ""
    when there is no positive pet evidence (pets_allowed missing or false)."""
    pets_allowed = pet_facts.get("pets_allowed")
    if pets_allowed == "false":
        return ""                          # explicit no-pets: caller REJECTs
    clauses = _BUILDERS.get(category, lambda f: [])(pet_facts)
    if clauses:
        return " ".join(_clause(c) for c in clauses)
    # Sparse but pet-friendly -> conservative fallback (only with pet evidence).
    if pets_allowed == "true":
        return _CONSERVATIVE_PARK if category == CATEGORY_PARKS else _CONSERVATIVE
    return ""
