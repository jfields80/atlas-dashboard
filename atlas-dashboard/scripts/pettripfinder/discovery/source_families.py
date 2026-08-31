"""PTF-DISCOVERY-P0-001 -- the source-family taxonomy.

One shared vocabulary for "what KIND of place did this identity assertion
come from". The family -- not the concrete source -- is the unit of
independence for identity confirmation: two pages of one CVB are one voice,
and so are two different CVBs, because they syndicate the same member
directories. ``identity_evidence.independent()`` already refuses to let one
``source_family`` confirm itself; this module supplies the canonical family
names so that adapters, the identity-observation contract, and the coverage
audit all spell them one way.

Adopted from PTF-PARALLEL-RESEARCH-002 (source_adapter_contract.md SS2,
approved under FD-R1 item 3). The ten families are the frozen enum of
``ptf-identity-observation/1.0`` and may not be renamed or extended without
a contract version bump.

Deliberately NOT here: a default NON_INDEPENDENT_FAMILY_PAIRS graph.
Which families count as one voice (an OTA republishing GDS inventory, for
example) is a founder decision (FD-R4), so the pairs are supplied by
configuration -- the coverage audit accepts them as input and this module
only provides the collapse mechanics. An empty default means every family
is independent, which is the current production behavior, unchanged.

Pure constants and pure functions. No IO, no network, no clock.
"""

from __future__ import annotations

from typing import Dict, FrozenSet, Iterable, Sequence, Set, Tuple

SCHEMA = "ptf-source-families/1.0"

# --------------------------------------------------------------------------- #
# The ten families (frozen enum of ptf-identity-observation/1.0).
# --------------------------------------------------------------------------- #

FAMILY_CVB = "CVB"                  #: convention & visitors bureaus, destination marketing
FAMILY_MAP = "MAP"                  #: commercial map/places platforms (e.g. Google Places)
FAMILY_OPEN_GEO = "OPEN_GEO"        #: open geographic data (e.g. OpenStreetMap)
FAMILY_OPEN_PLACES = "OPEN_PLACES"  #: open places datasets (e.g. Overture)
FAMILY_REGISTRY = "REGISTRY"        #: government license/registration records
FAMILY_OTA = "OTA"                  #: online travel agencies
FAMILY_CHAIN = "CHAIN"              #: a hotel brand's own locator/property pages
FAMILY_GDS = "GDS"                  #: global distribution systems
FAMILY_DIRECTORY = "DIRECTORY"      #: general business directories
FAMILY_OPEN_KB = "OPEN_KB"          #: open knowledge bases (e.g. Wikidata)

SOURCE_FAMILIES: FrozenSet[str] = frozenset({
    FAMILY_CVB, FAMILY_MAP, FAMILY_OPEN_GEO, FAMILY_OPEN_PLACES,
    FAMILY_REGISTRY, FAMILY_OTA, FAMILY_CHAIN, FAMILY_GDS,
    FAMILY_DIRECTORY, FAMILY_OPEN_KB,
})

# --------------------------------------------------------------------------- #
# Concrete source -> family. Only sources Atlas actually holds data from are
# mapped; a source is added here when its data enters the system, never
# speculatively. The four CVB entries are the entire Cleveland-Akron-Canton
# identity census (source_batch cleveland-akron-canton-007).
#
# PTF-MARKET-AUTHORITY-SHARDING-001. A NEW MARKET DOES NOT BELONG HERE.
# Everything below predates the per-market coverage config and is retained
# verbatim so no already-registered market changes family. A market registered
# from now on declares its own sources in
# ``launch_packages/pettripfinder/markets/coverage/<market_id>.json`` under
# ``source_family_overrides``, which ``family_of`` merges on top of this table.
# The distinction is not cosmetic: this dict is one shared file that every
# market branch appended to at once, and it was one of the recurring merge
# conflicts that sharding exists to remove. The per-market file has no such
# contention, and an override is reviewed beside the market it belongs to.
# --------------------------------------------------------------------------- #

CONCRETE_SOURCE_FAMILY: Dict[str, str] = {
    "destination_cleveland": FAMILY_CVB,
    "akron_summit_cvb": FAMILY_CVB,
    "stark_county_cvb": FAMILY_CVB,
    "destination_hudson": FAMILY_CVB,
    "fl_dbpr_lodging": FAMILY_REGISTRY,
    # PTF-DAYTON-MARKET-FACTORY-001: VisitDayton.com CVB source family.
    # Reserved for Dayton Convention & Visitors Bureau identity data.
    "visit_dayton": FAMILY_CVB,
    # PTF-LOUISVILLE-MARKET-BUILD-001: destination sources actually transcribed.
    "goto_louisville": FAMILY_CVB,
    "soin_tourism": FAMILY_CVB,
    "flylouisville": FAMILY_DIRECTORY,
    "louisville_downtown_partnership": FAMILY_DIRECTORY,
    # PTF-INDIANAPOLIS-MARKET-REVALIDATION-001: official Indianapolis destination sources.
    "visit_indy": FAMILY_CVB,
    "visit_hamilton_county": FAMILY_CVB,
    "visit_hendricks_county": FAMILY_CVB,
    "festival_country_indiana": FAMILY_CVB,
    "indianapolis_airport": FAMILY_CVB,
    "downtown_indy_inc": FAMILY_CVB,
    # PTF-CINCINNATI-CENSUS-RECONCILIATION-001: the six destination-marketing
    # directories that produced the Cincinnati tri-state census. All six are
    # CVB, so none of them independently confirms another -- which is exactly
    # why meet_nky corroborating visit_cincy is recorded as corroboration and
    # never counted as a second voice.
    "visit_cincy": FAMILY_CVB,
    "meet_nky": FAMILY_CVB,
    "travel_butler_county": FAMILY_CVB,
    "warren_county_cvb": FAMILY_CVB,
    "discover_clermont": FAMILY_CVB,
    "visit_southeast_indiana": FAMILY_CVB,
    # PTF-PITTSBURGH-MARKET-REVALIDATION-001: official tourism, destination
    # partners, and already-registered utility sources.
    "visit_pittsburgh": FAMILY_CVB,
    "cultural_trust": FAMILY_CVB,
    "paacc": FAMILY_DIRECTORY,
    "east_liberty_chamber": FAMILY_DIRECTORY,
    "gpha": FAMILY_DIRECTORY,
    "parks_conservancy": FAMILY_DIRECTORY,
    "city_parks": FAMILY_REGISTRY,
    "avets": FAMILY_CHAIN,
    "veg_pittsburgh": FAMILY_CHAIN,
    # PTF-DETROIT-ANN-ARBOR-MARKET-FACTORY-001: official tourism, destination
    # partners, chamber directories, and brand-locator discovery.
    "visit_detroit": FAMILY_CVB,
    "destination_ann_arbor": FAMILY_CVB,
    "dearborn_chamber": FAMILY_DIRECTORY,
    "auburn_hills_chamber": FAMILY_DIRECTORY,
    "vibe_showplace": FAMILY_DIRECTORY,
    "chain_locator": FAMILY_CHAIN,
    "chain_aggregate": FAMILY_CHAIN,
    # Carried onto this lineage by PTF-DETROIT-ANN-ARBOR-HARDENED-SYNC-029.
    # PTF-DETROIT-ANN-ARBOR-CENSUS-COMPLETENESS-002: brand-locator discovery
    # sweep confirming real property-level pages before adding a candidate.
    "chain_locator_002": FAMILY_CHAIN,
    # PTF-DETROIT-ANN-ARBOR-CENSUS-COMPLETENESS-003: attended-browser sweep
    # of each brand's own location-search page for the last 5 blockers.
    "chain_locator_003": FAMILY_CHAIN,
    # PTF-DETROIT-ANN-ARBOR-FOUNDER-RULINGS-AND-SHADOW-PROMOTION-006. The
    # source_id census_projection writes for a row a DISCOVERY provider
    # found rather than one transcribed from a directory. OPEN_GEO because
    # the provider is OpenStreetMap, and the family is what the coverage
    # audit reads to decide whether two sources are independent witnesses.
    "discovery": FAMILY_OPEN_GEO,
    # PTF-GRAND-RAPIDS-HOLLAND-MARKET-FACTORY-001: official destination
    # organizations only.  Each is CVB provenance; no policy claim is implied.
    "experience_gr_kentwood": FAMILY_CVB,
    "experience_gr_directory": FAMILY_CVB,
    "holland_cvb": FAMILY_CVB,
    "visit_grand_haven": FAMILY_CVB,
    "visit_muskegon": FAMILY_CVB,
    "saugatuck_douglas_cvb": FAMILY_CVB,
    "visit_south_haven": FAMILY_CVB,
    # PTF-GRAND-RAPIDS-HOLLAND-CENSUS-COMPLETENESS-001: first-party brand
    # inventories and the official airport shuttle roster used only for
    # identity discovery/reconciliation, never policy authority.
    "hilton_locator": FAMILY_CHAIN,
    "marriott_locator": FAMILY_CHAIN,
    "ihg_locator": FAMILY_CHAIN,
    "choice_locator": FAMILY_CHAIN,
    "hyatt_locator": FAMILY_CHAIN,
    "wyndham_locator": FAMILY_CHAIN,
    "sonesta_locator": FAMILY_CHAIN,
    "best_western_locator": FAMILY_CHAIN,
    "red_roof_locator": FAMILY_CHAIN,
    "extended_stay_america_locator": FAMILY_CHAIN,
    "motel6_studio6_locator": FAMILY_CHAIN,
    "grr_airport": FAMILY_DIRECTORY,
    # PTF-GRAND-RAPIDS-HOLLAND-CENSUS-COMPLETENESS-002: additional official
    # destination material, current property pages, and a county registry.
    "experience_gr_downtown_2026": FAMILY_CVB,
    "experience_gr_cascade_2026": FAMILY_CVB,
    "experience_gr_boutique_2026": FAMILY_CVB,
    "kent_county_hotel_motel_tax": FAMILY_REGISTRY,
    "drury_locator": FAMILY_CHAIN,
}


class SourceFamilyError(ValueError):
    """An unknown family name, or a malformed non-independence pair."""


def family_of(concrete_source: str,
              overrides: Dict[str, str] = None) -> str:
    """The family of a concrete source, or '' when unmapped.

    Unmapped is an ANSWER, not an error: the coverage audit must be able to
    say "this inventory predates family tracking" rather than guessing.
    ``overrides`` lets a market's coverage config extend the mapping without
    editing code."""
    merged = dict(CONCRETE_SOURCE_FAMILY)
    for name, fam in (overrides or {}).items():
        if fam not in SOURCE_FAMILIES:
            raise SourceFamilyError(
                "source %r mapped to unknown family %r (families: %s)"
                % (name, fam, sorted(SOURCE_FAMILIES)))
        merged[name] = fam
    return merged.get((concrete_source or "").strip(), "")


def validate_non_independent_pairs(
        pairs: Iterable[Sequence[str]]) -> Tuple[FrozenSet[str], ...]:
    """Fail closed on a malformed pair; return normalized 2-element sets."""
    out = []
    for pair in pairs:
        members = frozenset(pair)
        if len(members) != 2:
            raise SourceFamilyError(
                "a non-independence pair needs exactly two distinct families: %r"
                % (sorted(pair),))
        unknown = sorted(members - SOURCE_FAMILIES)
        if unknown:
            raise SourceFamilyError(
                "non-independence pair %s names unknown family(ies) %s"
                % (sorted(members), unknown))
        out.append(members)
    return tuple(out)


def collapse_families(families: Iterable[str],
                      non_independent_pairs: Iterable[Sequence[str]] = ()) -> Set[str]:
    """The set of INDEPENDENT voices among ``families``.

    Families joined by a declared pair are one voice; the collapse keeps the
    alphabetically-first member as the representative so the result is
    deterministic. Transitive by union-find: if A~B and B~C are declared,
    A, B and C are one voice -- the conservative reading, since declaring
    two overlapping dependencies and still counting two voices would let a
    republication chain confirm itself."""
    pairs = validate_non_independent_pairs(non_independent_pairs)
    present = sorted({f for f in families if f})
    parent = {f: f for f in present}

    def find(f: str) -> str:
        while parent[f] != f:
            parent[f] = parent[parent[f]]
            f = parent[f]
        return f

    for members in pairs:
        a, b = sorted(members)
        if a in parent and b in parent:
            ra, rb = find(a), find(b)
            if ra != rb:
                parent[max(ra, rb)] = min(ra, rb)
    return {find(f) for f in present}


__all__ = [
    "SCHEMA", "SOURCE_FAMILIES", "CONCRETE_SOURCE_FAMILY", "SourceFamilyError",
    "FAMILY_CVB", "FAMILY_MAP", "FAMILY_OPEN_GEO", "FAMILY_OPEN_PLACES",
    "FAMILY_REGISTRY", "FAMILY_OTA", "FAMILY_CHAIN", "FAMILY_GDS",
    "FAMILY_DIRECTORY", "FAMILY_OPEN_KB",
    "family_of", "collapse_families", "validate_non_independent_pairs",
]
