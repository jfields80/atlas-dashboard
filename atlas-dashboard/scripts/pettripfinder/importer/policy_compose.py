"""AES-DATA-001 importer -- deterministic pet_policy composition (mission
section 13). Builds the ``pet_policy`` CSV field from accepted structured
facts using fixed templates. No LLM prose is ever used. A clause appears
only when its fact is present; a sparse-but-pet-friendly source falls back
to the approved conservative wording; no pet evidence yields "".
"""

from __future__ import annotations

from typing import Dict

from scripts.pettripfinder.importer.constants import (
    CATEGORY_HOTELS,
    CATEGORY_PARKS,
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


_BUILDERS = {
    CATEGORY_HOTELS: _hotel_clauses,
    CATEGORY_PARKS: _park_clauses,
    CATEGORY_RESTAURANTS: _restaurant_clauses,
    CATEGORY_VETERINARY: _veterinary_clauses,
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
