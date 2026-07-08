"""
dimensions.py — Phase 1 support module.

The dimension banks the drill engine decomposes across. These are the
"axes" of the decision tree: geography, specialty, intent, customer type,
services, products, events, attributes.

Design notes:
- Geography is data-driven (user supplies state/cities, or engine uses
  the defaults below). Everything else is a modifier bank.
- SPECIALTY banks are per-vertical where we have them, with a generic
  fallback. Add verticals to VERTICAL_SPECIALTIES as you learn niches —
  this file is meant to grow with real research, not stay static.
- Each modifier is tagged with which dimension it belongs to, so a node's
  lineage is always explainable ("this node = seed + geo + specialty + attribute").
"""

from dataclasses import dataclass


@dataclass(frozen=True)
class Modifier:
    text: str
    dimension: str          # geography|specialty|intent|customer_type|service|product|event|attribute
    position: str = "prefix"  # prefix | suffix


# ---------------------------------------------------------------------------
# Modifier tiers — the architectural insight. Each dimension maps to a tier
# that determines what kind of ASSET a node using it can become:
#
#   Tier 1 (structural)  — geography, specialty     -> directories & categories
#   Tier 2 (attributes)  — attribute, service,       -> filters (promotable to
#                           customer_type               category if supply high)
#   Tier 3 (intent)      — intent                    -> SEO landing pages
#   Tier 4 (occasion)    — event                     -> articles / content hubs
#
# Tiers 2-4 are LEAVES: they attach to their parent directory and are never
# expanded further. This structurally prevents modifier stacking — the
# engine can no longer invent "grain-free dog bakeries in Ohio for weddings"
# as a standalone directory, because "grain-free" ends the branch as a filter.
# ---------------------------------------------------------------------------
DIMENSION_TIERS: dict[str, int] = {
    "geography": 1,
    "specialty": 1,
    "attribute": 2,
    "service": 2,
    "customer_type": 2,
    "intent": 3,
    "event": 4,
}


# ---------------------------------------------------------------------------
# Vertical-specific specialty banks. Key = lowercase substring matched
# against the seed niche. First match wins; falls back to GENERIC.
# ---------------------------------------------------------------------------
VERTICAL_SPECIALTIES: dict[str, list[str]] = {
    "mexican": ["birria", "street tacos", "seafood", "vegan", "tex-mex",
                 "authentic", "food truck", "breakfast", "quesabirria",
                 "tamales", "pozole", "carne asada", "margarita"],
    "restaurant": ["farm-to-table", "food truck", "breakfast", "brunch",
                    "fine dining", "fast casual", "buffet"],
    # NOTE: dietary/product attributes (grain-free, organic, gluten-free)
    # deliberately EXCLUDED from specialty banks — they're Tier-2 filters,
    # not business subtypes. Specialties = kinds of businesses that exist.
    "dog": ["custom cake", "gourmet treat", "pupcake", "training treat"],
    "bakery": ["custom cake", "wedding cake", "artisan", "cupcake", "donut"],
    "gym": ["crossfit", "powerlifting", "24 hour", "women only", "boxing"],
    "martial arts": ["bjj", "karate", "taekwondo", "mma", "judo", "kids"],
    "coffee": ["specialty", "drive-thru", "roastery", "study-friendly"],
    "barber": ["fade specialist", "kids", "hot towel shave", "walk-in"],
    "salon": ["balayage", "curly hair", "bridal", "organic"],
    "farm": ["grass-fed", "organic", "pasture-raised", "csa", "u-pick"],
    "hotel": ["boutique", "pet-friendly", "extended stay", "historic"],
    "lawyer": ["personal injury", "family", "criminal defense", "estate", "immigration"],
    "dentist": ["pediatric", "cosmetic", "emergency", "sedation", "implant"],
    "contractor": ["kitchen remodel", "bathroom remodel", "deck", "basement"],
}

GENERIC_SPECIALTIES = ["specialty", "boutique", "premium", "mobile", "24 hour"]

INTENT_MODIFIERS = [
    Modifier("best", "intent"),
    Modifier("cheap", "intent"),
    Modifier("luxury", "intent"),
    Modifier("top-rated", "intent"),
    Modifier("near me", "intent", "suffix"),
    Modifier("open late", "intent", "suffix"),
    Modifier("open now", "intent", "suffix"),
    Modifier("with delivery", "intent", "suffix"),
    Modifier("with reservations", "intent", "suffix"),
]

CUSTOMER_TYPE_MODIFIERS = [
    Modifier("family-friendly", "customer_type"),
    Modifier("kid-friendly", "customer_type"),
    Modifier("dog-friendly", "customer_type"),
    Modifier("date night", "customer_type"),
    Modifier("for large groups", "customer_type", "suffix"),
    Modifier("for students", "customer_type", "suffix"),
    Modifier("for tourists", "customer_type", "suffix"),
    Modifier("gluten-free friendly", "customer_type"),
    Modifier("vegetarian-friendly", "customer_type"),
]

SERVICE_MODIFIERS = [
    Modifier("with catering", "service", "suffix"),
    Modifier("with private rooms", "service", "suffix"),
    Modifier("with outdoor seating", "service", "suffix"),
    Modifier("with live music", "service", "suffix"),
    Modifier("with patio", "service", "suffix"),
    Modifier("with drive-thru", "service", "suffix"),
]

EVENT_MODIFIERS = [
    Modifier("for birthday parties", "event", "suffix"),
    Modifier("for weddings", "event", "suffix"),
    Modifier("for corporate events", "event", "suffix"),
    Modifier("for game day", "event", "suffix"),
    Modifier("for graduation parties", "event", "suffix"),
]

ATTRIBUTE_MODIFIERS = [
    Modifier("family-owned", "attribute"),
    Modifier("locally owned", "attribute"),
    Modifier("women-owned", "attribute"),
    Modifier("veteran-owned", "attribute"),
    Modifier("new", "attribute"),
    Modifier("award-winning", "attribute"),
]

# Default Ohio geography ladder (state -> metro -> suburb). Callers can
# pass their own; this is the out-of-the-box set matching Jon's home market.
DEFAULT_GEOGRAPHY = {
    "Ohio": {
        "Columbus": ["Downtown Columbus", "North Columbus", "Dublin",
                      "Westerville", "Hilliard", "Grandview", "Short North",
                      "Clintonville", "Gahanna", "Grove City"],
        "Cleveland": ["Downtown Cleveland", "Lakewood", "Ohio City", "Tremont"],
        "Cincinnati": ["Over-the-Rhine", "Hyde Park", "Downtown Cincinnati"],
        "Dayton": [],
        "Toledo": [],
        "Akron": [],
    }
}


def specialties_for(seed_niche: str) -> list[Modifier]:
    lowered = seed_niche.lower()
    for key, bank in VERTICAL_SPECIALTIES.items():
        if key in lowered:
            return [Modifier(s, "specialty") for s in bank]
    return [Modifier(s, "specialty") for s in GENERIC_SPECIALTIES]


def all_modifier_banks(seed_niche: str) -> dict[str, list[Modifier]]:
    """Every non-geographic dimension bank, keyed by dimension name."""
    return {
        "specialty": specialties_for(seed_niche),
        "intent": INTENT_MODIFIERS,
        "customer_type": CUSTOMER_TYPE_MODIFIERS,
        "service": SERVICE_MODIFIERS,
        "event": EVENT_MODIFIERS,
        "attribute": ATTRIBUTE_MODIFIERS,
    }
