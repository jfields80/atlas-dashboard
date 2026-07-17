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


_BUILDERS = {
    CATEGORY_HOTELS: _hotel_clauses,
    CATEGORY_PARKS: _park_clauses,
    CATEGORY_RESTAURANTS: _restaurant_clauses,
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
