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
