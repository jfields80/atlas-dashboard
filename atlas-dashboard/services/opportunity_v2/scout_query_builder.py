"""
scout_query_builder.py — Scout Query Builder.

Converts a raw Atlas opportunity (niche_name + DNA) into deterministic,
provider-specific search queries. Solves a real problem: the raw
opportunity name Atlas drills to (e.g. "pet-friendly vacation hiking")
is an internal category label, not a phrase real businesses or Google
Places index themselves under. This module cleans that up.

Single responsibility:
    Scout Query Builder answers exactly one question:
        "What search queries should a provider actually run for this
         opportunity?"
    It NEVER scores anything, NEVER recommends anything, and NEVER makes
    a live API call. It is a pure text-transformation utility that other
    Scout provider adapters (starting with GooglePlacesBusinessDataSource)
    can use to turn a niche_name into better search text.

Design — general, deterministic, reusable transformations, not per-niche
hardcoding:
    Every transformation below is a general rule or a general, documented
    table (filler-word removal, a small synonym-swap table, a "bare
    activity word -> complete Places-style phrase" completion table, and
    a general "X for Y" -> "Y X" grammatical reorder). None of these
    reference any specific opportunity name. The DNA-driven parts (which
    dimension a term belongs to, which sibling example to offer as an
    alternate) come entirely from whatever OpportunityDNA is passed in —
    swap the DNA profile and the same code produces different, correct
    results for a different market, with zero code changes.

Output — ScoutQuerySet:
    primary_query      — the single best query to try first
    alternate_queries   — up to _MAX_ALTERNATES additional queries, in a
                          fixed, deterministic priority order
    location_terms      — DNA search-dimension examples (geo-typed
                          dimensions only) found in the niche text, if any
    category_terms       — other DNA search-dimension examples found in
                          the niche text (business type, activity,
                          attribute, etc.)
    provider_notes       — human-readable trail of which transformations
                          fired, for auditability (not scoring — just an
                          explanation of how the queries were built)

Integration:
    GooglePlacesBusinessDataSource accepts an optional query_builder
    (this module's build_scout_queries function, or any callable with the
    same signature) or a precomputed query_set, and uses primary_query
    (falling back to alternate_queries on zero results) instead of the
    raw niche_name — with zero change to its public BusinessDataSource
    behavior when neither is supplied.
"""

from __future__ import annotations

import re
from dataclasses import dataclass, field
from typing import Optional

from .dna.schema import OpportunityDNA, SearchDimension


# ─────────────────────────────────────────────────────────────────────────────
# Named constants — general tables, not tied to any one opportunity
# ─────────────────────────────────────────────────────────────────────────────

# Words that reduce search specificity rather than add it. Stripped from
# every stage of query construction. General stopword-style list, not
# specific to any niche.
_FILLER_WORDS = {
    "vacation", "options", "service", "services", "info", "information",
    "guide", "trip", "ideas",
}

# Dimension name / typically_produces_asset hints that mark a DNA search
# dimension as location-oriented, used to split location_terms from
# category_terms. General classification, applies to any DNA profile.
_LOCATION_DIMENSION_ASSET_TYPES = {"geo_category"}
_LOCATION_DIMENSION_NAME_KEYWORDS = ["destination", "location", "city", "region", "area", "metro"]

# Synonym swaps: general lexical neighbours commonly used interchangeably
# across directory/local-search categories. Applied wherever the left-hand
# phrase appears, regardless of what niche it's found in. Text is
# hyphen-normalized (see _normalize below) before matching, so only the
# space-separated form needs to be listed here.
_SYNONYM_SWAPS: list[tuple[str, str]] = [
    ("pet friendly", "dog friendly"),
    ("hotels", "lodging"),
    ("therapists", "counselors"),
    ("counselors", "therapists"),
    ("attorneys", "lawyers"),
    ("lawyers", "attorneys"),
    ("restaurants", "places to eat"),
    ("coffee shops", "cafes"),
    ("cafes", "coffee shops"),
]

# Bare activity/root words that are too vague as standalone Places search
# terms. Maps to an ordered list of complete, Places-style phrases — the
# first entry is used to complete the primary query; later entries are
# available for alternates. General activity -> place-type vocabulary,
# not specific to any one DNA profile or opportunity.
_PLACE_TYPE_COMPLETIONS: dict[str, list[str]] = {
    "hiking":   ["hiking trails", "parks"],
    "biking":   ["bike trails", "parks"],
    "swimming": ["swimming holes", "pools"],
    "camping":  ["campgrounds"],
    "beach":    ["beaches"],
}

# Broad category umbrella for activity words — a general fallback when a
# still-broader alternate is useful (e.g. "outdoor activities" as a wide
# net alongside a specific completion like "hiking trails").
_ACTIVITY_BROAD_CATEGORY: dict[str, str] = {
    "hiking":      "outdoor activities",
    "biking":      "outdoor activities",
    "beach":       "outdoor activities",
    "swimming":    "outdoor activities",
    "camping":     "outdoor activities",
    "off-leash":   "outdoor activities",
    "patio dining": "dining",
}

# General grammatical reorder: "<subject> for <qualifier>" reads more
# naturally, and searches/lists more like real businesses, as
# "<qualifier> <subject>" (e.g. "therapists for anxiety" -> "anxiety
# therapists"). Whole-word "for" only; not niche-specific.
_FOR_PATTERN = re.compile(r"^(.*?)\bfor\b(.*)$")

_MAX_ALTERNATES = 3


# ─────────────────────────────────────────────────────────────────────────────
# Output model
# ─────────────────────────────────────────────────────────────────────────────

@dataclass
class ScoutQuerySet:
    """Deterministic, provider-agnostic query set for one opportunity.
    No scores, no recommendations — query text and an explanation trail
    only."""
    niche_name: str
    dna_slug: str

    primary_query: str
    alternate_queries: list[str] = field(default_factory=list)
    location_terms: list[str] = field(default_factory=list)
    category_terms: list[str] = field(default_factory=list)
    provider_notes: list[str] = field(default_factory=list)


# ─────────────────────────────────────────────────────────────────────────────
# Internal helpers — each a small, general, documented transformation
# ─────────────────────────────────────────────────────────────────────────────

def _normalize(text: str) -> str:
    """
    General text normalization applied before any other transformation:
    hyphens become spaces (Places-style search text is natural language —
    "dog friendly hotels", not "dog-friendly hotels"), and whitespace is
    collapsed. Not niche-specific; applies identically to any input.
    """
    return " ".join(text.replace("-", " ").split())


def _strip_filler_words(text: str) -> str:
    words = [w for w in text.split() if w not in _FILLER_WORDS]
    return " ".join(words)


def _reorder_for_pattern(text: str) -> tuple[str, bool]:
    """
    General "X for Y" -> "Y X" reorder. Whole-word match on "for" only
    (so words like "before" or "reformed" never trigger it). Returns the
    reordered text and whether a reorder actually happened.
    """
    match = _FOR_PATTERN.match(text)
    if not match:
        return text, False
    subject, qualifier = match.group(1).strip(), match.group(2).strip()
    if not subject or not qualifier:
        return text, False
    return f"{qualifier} {subject}", True


def _apply_synonym_swap(text: str) -> tuple[str, Optional[tuple[str, str]]]:
    """
    Apply the FIRST matching synonym swap found (in table order) and
    return the swapped text plus which (src, dst) pair fired, or
    (text, None) if no swap applies. Only one swap is applied per call
    so alternates can meaningfully offer "the swapped variant" as a
    single, distinct option rather than compounding multiple swaps.
    """
    for src, dst in _SYNONYM_SWAPS:
        if src in text:
            return text.replace(src, dst, 1), (src, dst)
    return text, None


def _apply_next_synonym_swap(text: str,
                                exclude_src: Optional[str]) -> tuple[str, Optional[tuple[str, str]]]:
    """
    Like _apply_synonym_swap, but skips any table entry whose source
    phrase matches exclude_src. Used to find a SECOND, genuinely
    different swap opportunity for alternates (e.g. if 'pet friendly'
    was already swapped for the primary query, this looks for a
    different swap such as 'hotels' -> 'lodging' elsewhere in the same
    phrase, instead of rediscovering the same swap already used).
    """
    for src, dst in _SYNONYM_SWAPS:
        if exclude_src is not None and src == exclude_src:
            continue
        if src in text:
            return text.replace(src, dst, 1), (src, dst)
    return text, None


def _apply_place_type_completion(text: str) -> tuple[str, Optional[str], list[str]]:
    """
    If any bare activity word in _PLACE_TYPE_COMPLETIONS appears in text,
    replace it with the first completion and return the completed text,
    the matched root word, and the remaining (unused) completion options
    for alternate generation. Returns (text, None, []) if nothing matches.
    """
    for root, completions in _PLACE_TYPE_COMPLETIONS.items():
        if root in text.split() or root in text:
            completed = text.replace(root, completions[0], 1)
            return completed, root, completions[1:]
    return text, None, []


def _dimension_is_location(dim: SearchDimension) -> bool:
    if dim.typically_produces_asset in _LOCATION_DIMENSION_ASSET_TYPES:
        return True
    name_lower = dim.name.lower()
    return any(kw in name_lower for kw in _LOCATION_DIMENSION_NAME_KEYWORDS)


def _find_dimension_matches(text: str, dna: OpportunityDNA
                              ) -> list[tuple[SearchDimension, str]]:
    """
    Return every (dimension, matched_example) pair whose example appears
    as a substring of text, checked in DNA-declared dimension order, then
    DNA-declared example order within each dimension. Deterministic.
    """
    matches: list[tuple[SearchDimension, str]] = []
    for dim in dna.search_dimensions:
        for example in dim.examples:
            if example.lower() in text:
                matches.append((dim, example))
                break   # one match per dimension is enough signal
    return matches


def _pick_sibling_example(dim: SearchDimension, matched_example: str) -> Optional[str]:
    """
    Deterministically pick the first OTHER example declared in the same
    DNA dimension as matched_example. Used to build a DNA-driven adjacent
    alternate (e.g. within a "problem" dimension containing
    [anxiety, depression, trauma, ...], matching "anxiety" offers the
    next declared example as a sibling). Purely data-driven — changing
    the DNA profile changes the sibling offered, with no code change.
    """
    for example in dim.examples:
        if example.lower() != matched_example.lower():
            return example
    return None


def _dedupe_preserve_order(items: list[str]) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for item in items:
        key = item.strip().lower()
        if key and key not in seen:
            seen.add(key)
            out.append(item.strip())
    return out


# ─────────────────────────────────────────────────────────────────────────────
# Public builder
# ─────────────────────────────────────────────────────────────────────────────

def build_scout_queries(niche_name: str, dna: OpportunityDNA,
                          ctx: Optional[dict] = None) -> ScoutQuerySet:
    """
    Build a deterministic ScoutQuerySet for one opportunity.

    Pipeline (every step general and documented above, none niche-specific):
        1. Reorder "X for Y" -> "Y X" if that pattern is present.
        2. Strip filler words.
        3. Match DNA search-dimension examples in the cleaned text, split
           into location_terms vs category_terms.
        4. Complete any bare activity word into a Places-style phrase.
        5. Apply the first matching synonym swap to produce the primary
           query's final wording.
        6. Build up to _MAX_ALTERNATES alternates from: the pre-swap
           wording, a second place-type completion, a broadened activity
           category, an un-used synonym swap, a DNA-sibling substitution,
           and a "core subject near me" broadening — in that fixed
           priority order, skipping any strategy that doesn't apply.

    ctx is accepted for interface symmetry with the rest of Scout's
    providers (niche_name, dna, ctx) but is not currently read; reserved
    for future provider-specific hints (e.g. a location bias) without
    another signature change.
    """
    notes: list[str] = []
    original = niche_name.lower().strip()

    # 0. Normalize (hyphens -> spaces, collapse whitespace)
    normalized = _normalize(original)
    if normalized != original:
        notes.append(f"Normalized '{original}' -> '{normalized}'.")

    # 1. Reorder
    reordered, did_reorder = _reorder_for_pattern(normalized)
    if did_reorder:
        notes.append(f"Reordered '{normalized}' -> '{reordered}' ('X for Y' -> 'Y X').")
    working = reordered

    # 2. Strip filler words
    cleaned = _strip_filler_words(working)
    if cleaned != working:
        notes.append(f"Stripped filler word(s): '{working}' -> '{cleaned}'.")

    # 3. DNA dimension matches -> location_terms / category_terms
    dim_matches = _find_dimension_matches(cleaned, dna)
    location_terms = [ex for dim, ex in dim_matches if _dimension_is_location(dim)]
    category_terms = [ex for dim, ex in dim_matches if not _dimension_is_location(dim)]
    if dim_matches:
        notes.append(
            "DNA dimension matches: " +
            ", ".join(f"{dim.name}='{ex}'" for dim, ex in dim_matches))

    # 4. Place-type completion
    completed, completion_root, remaining_completions = _apply_place_type_completion(cleaned)
    if completion_root:
        notes.append(
            f"Completed bare activity term '{completion_root}' -> "
            f"'{_PLACE_TYPE_COMPLETIONS[completion_root][0]}'.")

    # 5. Synonym swap for the primary query
    primary_query, swap_used = _apply_synonym_swap(completed)
    if swap_used:
        notes.append(f"Synonym swap on primary query: '{swap_used[0]}' -> '{swap_used[1]}'.")
    primary_query = primary_query.strip() or cleaned.strip() or original

    # 6. Alternates — fixed priority order, each strategy contributes at
    #    most one candidate, skipped silently if it doesn't apply.
    candidates: list[str] = []

    # (a) Pre-swap wording (offers the un-swapped attribute wording back,
    #     since real businesses list under both).
    if swap_used and completed.strip() != primary_query.strip():
        candidates.append(completed.strip())

    # (b) Second place-type completion, paired with the swapped wording
    #     if a swap fired, to diversify wording across the alternate set.
    if remaining_completions:
        second = cleaned.replace(completion_root, remaining_completions[0], 1)
        if swap_used:
            second = second.replace(swap_used[0], swap_used[1], 1)
        candidates.append(second.strip())

    # (c) Broadened activity category, using the ORIGINAL (pre-swap)
    #     attribute wording to maximize distinct real-world phrasing
    #     coverage across the alternate set.
    if completion_root and completion_root in _ACTIVITY_BROAD_CATEGORY:
        broadened = cleaned.replace(completion_root, _ACTIVITY_BROAD_CATEGORY[completion_root], 1)
        candidates.append(broadened.strip())

    # (d) A second, DIFFERENT synonym swap elsewhere in the phrase —
    #     covers cases where the swap used for primary (e.g. 'pet
    #     friendly' -> 'dog friendly') isn't the only one available (e.g.
    #     'hotels' -> 'lodging' elsewhere in the same phrase).
    if not remaining_completions and not (completion_root and completion_root in _ACTIVITY_BROAD_CATEGORY):
        exclude_src = swap_used[0] if swap_used else None
        alt_swap_text, alt_swap_used = _apply_next_synonym_swap(cleaned, exclude_src)
        if alt_swap_used:
            candidates.append(alt_swap_text.strip())

    # (e) DNA-sibling substitution: replace the matched dimension example
    #     with a sibling example from the same DNA dimension.
    for dim, matched_example in dim_matches:
        sibling = _pick_sibling_example(dim, matched_example)
        if sibling:
            sibling_variant = cleaned.replace(matched_example.lower(), sibling.lower(), 1)
            candidates.append(sibling_variant.strip())
            notes.append(
                f"DNA sibling alternate: '{matched_example}' -> '{sibling}' "
                f"(same '{dim.name}' dimension).")
            break   # one sibling alternate is enough signal

    # (f) Core-subject "near me" broadening — general fallback, always
    #     available: strip any matched dimension example out of the
    #     cleaned text (leaving just the core subject) and append
    #     "near me". Only used to fill remaining alternate slots.
    core = cleaned
    for _, matched_example in dim_matches:
        core = core.replace(matched_example.lower(), "").strip()
    core = " ".join(core.split())   # collapse repeated whitespace
    if core and core != cleaned:
        candidates.append(f"{core} near me")

    alternate_queries = _dedupe_preserve_order(candidates)
    # Never let the primary query also appear as an alternate.
    alternate_queries = [a for a in alternate_queries
                          if a.lower() != primary_query.strip().lower()]
    alternate_queries = alternate_queries[:_MAX_ALTERNATES]

    return ScoutQuerySet(
        niche_name=niche_name,
        dna_slug=dna.slug,
        primary_query=primary_query.strip(),
        alternate_queries=alternate_queries,
        location_terms=_dedupe_preserve_order(location_terms),
        category_terms=_dedupe_preserve_order(category_terms),
        provider_notes=notes,
    )
