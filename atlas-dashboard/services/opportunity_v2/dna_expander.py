"""
dna_expander.py — DNA-driven candidate generation.

Fully replaces hardcoded modifier banks. Two generation modes:

1. STRUCTURAL EXPANSION (drill children): iterate the DNA's
   search_dimensions and produce one child per example under each
   dimension. Each generated child records:
     - which dimension it used
     - which example value it used
     - what the DNA said that dimension typically becomes
       (typically_produces_asset -> asset_type hint)

2. ECOSYSTEM TRAVERSAL (siblings): for a node that maps to an ecosystem
   node in the DNA, generate SIBLING candidates from ecosystem_edges —
   opportunities the DNA declares are commercially adjacent, not just
   linguistically deeper. These get their own seed lineage; they aren't
   children of the current node.

Geography is a search_dimension in the DNA now (destinations, locations,
regions). If the DNA declares one, the engine uses THAT dimension's
examples as the geo axis. If none is declared, geography drilling is off
for that market — which is correct: not every market is local.

Zero references to hardcoded modifier banks anywhere in this module.
"""

from __future__ import annotations

import itertools
from dataclasses import dataclass

from .dna.schema import OpportunityDNA, EdgeType, SearchDimension


@dataclass
class DimensionUse:
    dimension_name: str      # e.g. "destination", "insurance"
    dimension_intent: str    # structural | attribute | intent | occasion
    value: str               # the example value used ("Aetna", "Asheville")
    asset_hint: str          # what asset the DNA said this dimension produces


@dataclass
class Candidate:
    niche_name: str
    dimensions_used: dict           # dimension_name -> value
    dimension_intents: dict         # dimension_name -> intent_type (structural/attribute/intent/occasion)
    dimension_asset_hints: dict     # dimension_name -> asset_hint from the DNA
    origin: str                     # 'drill_child' | 'ecosystem_sibling'
    origin_note: str = ""           # e.g. "sibling of pet-friendly hotels via complementary"


# ---------------------------------------------------------------------------
# Naming: build a readable niche label from base + dimension use.
# We use plain " " concatenation for structural/attribute dimensions;
# intent dimensions read more naturally with the modifier in front
# ("best pet-friendly hotels"); occasion dimensions are prepositional
# ("pet-friendly hotels for weddings").
# ---------------------------------------------------------------------------

def _phrase(base: str, dim: SearchDimension, value: str) -> str:
    """Produce a readable niche label based on the dimension's declared
    asset hint. The DNA is authoritative — we don't guess from dimension
    names. Six patterns cover every declared asset target."""
    target = (dim.typically_produces_asset or "category").lower()
    intent = (dim.intent_type or "structural").lower()

    if target == "geo_category":
        # Geography: "pet-friendly travel in Asheville"
        return f"{base} in {value}"
    if target == "category":
        # Category dimension: the value is a subtype OR a business type.
        # "business type" in pet travel -> "pet-friendly hotels" (value is head noun)
        # "product" in dog bakeries    -> "dog bakery cupcakes" (value stacks)
        # "problem" in therapists      -> "anxiety therapists" (value stacks)
        # Distinguish by whether the value is a plural noun on its own
        # (likely head) vs a modifier (likely stacks). Heuristic: multi-word
        # or "-therapy" / "-y" endings tend to be head nouns; simple nouns
        # like "cupcake" or "anxiety" stack in front of the base.
        base_head = base.split()[-1] if " " in base else base
        # If base is a compound like "pet-friendly travel" and value is a
        # head noun like "hotels", we want "pet-friendly hotels".
        # Detect by asking: does the DNA's dimension_name suggest a
        # replacement axis? "business type" replaces; "product" stacks.
        replaces = "business" in dim.name.lower() or "type" in dim.name.lower() \
            or "provider" in dim.name.lower() or "activity" in dim.name.lower()
        if replaces and " " in base:
            modifier = " ".join(base.split()[:-1])
            return f"{modifier} {value}"
        # Stacks: value + base
        return f"{value} {base}"
    if target == "filter":
        return f"{value} {base}"
    if target == "seo_page":
        # Intent phrasing: "best pet-friendly hotels"
        return f"{value} {base}"
    if target == "article":
        # Occasion: "pet-friendly travel for weddings" / "therapists for postpartum"
        return f"{base} for {value}"
    if target in ("buying_guide", "comparison", "tool", "affiliate_hub"):
        return f"{value} {base}"
    # Unknown target — safe stacking default
    return f"{value} {base}"


# ---------------------------------------------------------------------------
# Structural expansion: children generated from the DNA's search_dimensions
# ---------------------------------------------------------------------------

def expand_from_dna(base_niche: str, dna: OpportunityDNA,
                     used_dimensions: set[str],
                     seed_niche: str,
                     accumulated_dims: dict | None = None,
                     examples_per_dimension: int = 6) -> list[Candidate]:
    """Generate child candidates. One dimension per new child (accumulates
    down the tree). Names are composed from the ACCUMULATED dimension
    values in intentional order rather than by nesting labels — that
    keeps compound niches like "child anxiety therapists in Columbus"
    reading naturally regardless of drill order.

    ONLY dimensions the DNA actually declares. If the DNA has no
    geography-like dimension, geography is not expanded — that's a market
    where local isn't the primary axis (e.g. online-only DTC brands).
    """
    candidates: list[Candidate] = []
    accumulated_dims = accumulated_dims or {}

    for dim in dna.search_dimensions:
        if dim.name in used_dimensions:
            continue
        if not dim.examples:
            continue
        for value in dim.examples[:examples_per_dimension]:
            new_dims = {**accumulated_dims, dim.name: value}
            # Compose fresh from all accumulated values, using each
            # dimension's DNA metadata to place it correctly.
            name = compose_niche_name(seed_niche, new_dims, dna)
            dim_intents = {dim.name: dim.intent_type or "structural"}
            dim_assets = {dim.name: dim.typically_produces_asset or "category"}
            candidates.append(Candidate(
                niche_name=name,
                dimensions_used={dim.name: value},
                dimension_intents=dim_intents,
                dimension_asset_hints=dim_assets,
                origin="drill_child",
                origin_note=f"expanded on dimension '{dim.name}'"))
    return candidates


def compose_niche_name(seed_niche: str, dims_used: dict,
                         dna: OpportunityDNA) -> str:
    """Assemble a readable niche label from the seed + all accumulated
    dimension values. Order matters for readability:

        [intent] [attribute+] [category-stackers] SEED [category-replacers] [in geo] [for occasion]

    Concrete example (therapists):
        seed "therapists" + {problem: anxiety, patient population: child,
         insurance: BCBS, location: Columbus, life event: postpartum}
        -> "best child anxiety therapists BCBS in Columbus for postpartum"

    Each dimension's typically_produces_asset (from the DNA) determines
    which bucket it goes into.
    """
    intent_vals: list[str] = []
    attribute_vals: list[str] = []
    stacker_vals: list[str] = []       # modifiers that stack in front of seed
    replacer_val: str | None = None    # a value that REPLACES the seed's head noun
    geo_val: str | None = None
    occasion_val: str | None = None

    for dim_name, value in dims_used.items():
        # Find the dimension metadata
        dim = next((d for d in dna.search_dimensions if d.name == dim_name), None)
        if dim is None:
            stacker_vals.append(value)
            continue
        target = (dim.typically_produces_asset or "category").lower()
        intent = (dim.intent_type or "structural").lower()

        if target == "geo_category":
            geo_val = value
        elif target == "article" or intent == "occasion":
            occasion_val = value
        elif target == "seo_page" or intent == "intent":
            intent_vals.append(value)
        elif target == "filter" or intent == "attribute":
            attribute_vals.append(value)
        elif target in ("directory", "category"):
            # 'directory' target means this dimension names a full business
            # type (hotels, campgrounds, ABA centers) — it's the head noun.
            # 'category' with a "type"-ish dim name behaves the same.
            replaces = (target == "directory"
                          or "business" in dim.name.lower()
                          or "type" in dim.name.lower()
                          or "provider" in dim.name.lower()
                          or "activity" in dim.name.lower())
            if replaces:
                replacer_val = value
            else:
                stacker_vals.append(value)
        else:
            stacker_vals.append(value)

    # Build the head noun
    if replacer_val:
        # "pet-friendly travel" + business-type "hotels" -> "pet-friendly hotels"
        base_words = seed_niche.split()
        if len(base_words) >= 2:
            head_noun = " ".join(base_words[:-1]) + " " + replacer_val
        else:
            head_noun = replacer_val
    else:
        head_noun = seed_niche

    parts = []
    if intent_vals:
        parts.extend(intent_vals)
    if attribute_vals:
        parts.extend(attribute_vals)
    if stacker_vals:
        parts.extend(stacker_vals)
    parts.append(head_noun)
    if geo_val:
        parts.append(f"in {geo_val}")
    if occasion_val:
        parts.append(f"for {occasion_val}")

    return " ".join(parts)


# ---------------------------------------------------------------------------
# Ecosystem traversal: siblings generated from ecosystem_edges
# ---------------------------------------------------------------------------

# Which edge types produce commercially interesting siblings? All of them
# in principle — but strength filtering keeps the noise down. High/very_high
# edges are the ones worth spawning as separate opportunities.
STRONG_EDGES = ("high", "very_high")


def expand_ecosystem_siblings(dna: OpportunityDNA,
                                 edge_types: list[EdgeType] | None = None,
                                 min_strength: tuple = STRONG_EDGES) -> list[Candidate]:
    """Return the ecosystem graph's strongest opportunities as seed
    candidates. Every node in the DNA with directory_potential HIGH or
    above becomes a candidate seed. Edges add sibling recommendations
    on top — they don't generate the sibling itself (the node does)."""
    from .dna.schema import Intensity

    interesting_intensities = {Intensity.HIGH, Intensity.VERY_HIGH,
                                 Intensity.EXTREME}

    candidates: list[Candidate] = []
    for node in dna.ecosystem_nodes:
        if node.directory_potential not in interesting_intensities:
            continue
        # Which edges make this node interesting? Note them in origin_note.
        incoming = [e for e in dna.ecosystem_edges
                     if e.to_node == node.name and e.strength.value in min_strength]
        outgoing = [e for e in dna.ecosystem_edges
                     if e.from_node == node.name and e.strength.value in min_strength]
        note_parts = []
        if incoming:
            note_parts.append(
                f"connected from: {', '.join(f'{e.from_node} ({e.edge_type.value})' for e in incoming[:3])}")
        if outgoing:
            note_parts.append(
                f"connects to: {', '.join(f'{e.to_node} ({e.edge_type.value})' for e in outgoing[:3])}")
        candidates.append(Candidate(
            niche_name=node.name,
            dimensions_used={},
            dimension_intents={},
            dimension_asset_hints={"_ecosystem_role": "directory"},
            origin="ecosystem_sibling",
            origin_note=(node.notes + " · " + " · ".join(note_parts)).strip(" ·")))
    return candidates
