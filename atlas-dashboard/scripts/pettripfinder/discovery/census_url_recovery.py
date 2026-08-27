"""Recover an official URL for a census row that has none, from evidence already paid for.

    python scripts/pettripfinder/discovery/census_url_recovery.py \
      --market st-louis-mo --cache data/discovery/st_louis_market_001/cache \
      --out launch_packages/pettripfinder/st_louis_mo_url_recovery_002.json

A market's routing coverage is capped by how many identities have a first-party
URL at all. St. Louis routes 280 of 357, and 60 of the 77 it cannot route are
not blocked by a provider or a reader: nobody knows where the hotel's website
is. That is a discovery gap, and the first place to look for it is the discovery
data the market ALREADY BOUGHT.

ZERO NETWORK. ZERO SPEND.
--------------------------
Every raw provider payload from the census pass is on disk. Google Places
returns ``websiteUri`` and OpenStreetMap carries a ``website`` tag, and the
census projection admits a URL only when the candidate it merged into carried
one. A candidate that was absorbed, or that matched on a different key, can hold
a URL the surviving row does not. Re-reading those payloads costs nothing and it
is falsifiable: every recovery names the payload it came from.

MATCHING IS STRICT, AND THAT IS THE WHOLE DESIGN
-------------------------------------------------
A wrong URL is far worse than no URL. A missing URL leaves an identity honestly
unrouted; a wrong one sends a paid lane to another hotel's page, passes an
identity gate that only checks city and brand, and publishes another building's
pet policy under this hotel's name. St. Louis has already produced that exact
failure once -- three census identities sharing one Choice city-search URL.

So a candidate binds on one of exactly two keys:

    PHONE          both sides have a telephone number and the digits are equal.
                   A telephone line is the strongest identity signal in this
                   corpus: it is per-building, it is rarely shared, and it is
                   the key the identity gate itself prefers.
    NAME + POSTAL  both sides have a name and a postal code, and BOTH match.
                   Either alone is not enough -- "Comfort Inn" is a valid name
                   for twenty buildings, and a postal code holds many hotels.

An empty field never matches an empty field. That sounds obvious and it is the
bug this module was written around: bucketing candidates by ``digits(phone)``
puts every phoneless row in one bucket keyed by the empty string, and the first
lookup marries fifty hotels to one unrelated bed-and-breakfast.

A recovered URL is a PROPOSAL. Nothing here edits the census, which stays the
canonical record of what discovery observed. The output is a report a work order
reads.
"""

from __future__ import annotations

import argparse
import glob
import json
import re
import sys
from collections import Counter, OrderedDict
from pathlib import Path
from typing import (Callable, Dict, Iterable, List, Mapping, Optional,
                    Sequence, Tuple)

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.acquisition import market_routing as MR  # noqa: E402

SCHEMA = "ptf-census-url-recovery/1.0"
from scripts.pettripfinder import census_location as CENSUS_LOCATION  # noqa: E402
CENSUS_DIR = CENSUS_LOCATION.identity_census_dir()  # committed, or $PTF_IDENTITY_CENSUS_DIR during a rebuild
GOOGLE_PLACES = "GOOGLE_PLACES"
OPENSTREETMAP = "OPENSTREETMAP"

BIND_PHONE = "PHONE"
BIND_NAME_POSTAL = "NAME_AND_POSTAL_CODE"
BIND_STREET_POSTAL = "STREET_AND_POSTAL_CODE"

#: A prior build of the same market, read back out of its own artifacts.
PRIOR_BUILD = "PRIOR_BUILD"

_NON_ALNUM = re.compile(r"[^a-z0-9]+")
_NON_DIGIT = re.compile(r"\D")


def normalise(value: str) -> str:
    return _NON_ALNUM.sub(" ", (value or "").lower()).strip()


def digits(value: str) -> str:
    """US numbers, comparable across ``(314) 731-3800`` and ``+1 314 731 3800``.

    The leading country code is dropped so a Places national number and an OSM
    international one compare equal; ten digits is what identifies the line.
    """
    only = _NON_DIGIT.sub("", value or "")
    if len(only) == 11 and only.startswith("1"):
        only = only[1:]
    return only if len(only) == 10 else ""


#: Street words that two sources spell differently for the same building.
#: "700 W Main St" and "700 West Main Street" are one address; comparing them
#: literally is why a street key that looks obvious recovers nothing.
_STREET_WORDS = {
    "north": "n", "south": "s", "east": "e", "west": "w",
    "northeast": "ne", "northwest": "nw", "southeast": "se", "southwest": "sw",
    "street": "st", "avenue": "ave", "road": "rd", "drive": "dr",
    "boulevard": "blvd", "lane": "ln", "court": "ct", "circle": "cir",
    "parkway": "pkwy", "place": "pl", "highway": "hwy", "turnpike": "tpke",
    "terrace": "ter", "trail": "trl", "square": "sq", "expressway": "expy",
}

#: Words that identify a KIND of lodging rather than one building. A name token
#: has to survive this list to corroborate a URL: "hotel" appears in half the
#: hostnames in this corpus and binds nothing.
_GENERIC_NAME_WORDS = frozenset({
    "hotel", "hotels", "motel", "motels", "inns", "suite", "suites", "resort",
    "resorts", "lodge", "lodging", "house", "rooms", "and", "the", "by", "at",
    "of", "near", "airport", "downtown", "north", "south", "east", "west",
})


def street_key(address: str, postal: str) -> str:
    """``"700 w main st|40202"`` -- or ``""`` when either half is missing.

    A street number and a postal code together name one building. Either alone
    does not: a postal code holds many hotels, and "700 Main St" exists in every
    city in the country. The key is empty unless the address actually starts
    with a number, so "Airport Road" -- a location, not an address -- never
    becomes a key that two unrelated rows can share.
    """
    words = _NON_ALNUM.sub(" ", (address or "").lower()).split()
    postal = (postal or "").strip()
    if not words or not postal or not words[0][:1].isdigit():
        return ""
    return "%s|%s" % (" ".join(_STREET_WORDS.get(w, w) for w in words), postal)


#: PTF-INDIANAPOLIS-PLACES-NAME-NORMALIZATION-009. The hotel OPERATORS whose
#: name a brand page prints as a courtesy: "Candlewood Suites Indianapolis
#: Northwest BY IHG", "Fairfield BY MARRIOTT Inn & Suites". The operator is
#: presentation, not identity -- it says who runs the chain, never which
#: building. Removed only as the exact two-token sequence ``by <operator>``, and
#: from BOTH sides, so a name that never carried it is unaffected.
#:
#: Deliberately a CLOSED list of operator names. "by the airport" and "by the
#: canal" are locations, and a rule that dropped any "by X" would delete them.
_OPERATOR_TOKENS: Tuple[str, ...] = (
    "marriott", "hilton", "ihg", "wyndham", "radisson", "hyatt", "choice",
    "sonesta", "accor", "best western",
)

#: Chain names a brand has re-presented wholesale. The left form and the right
#: form are the SAME chain, so neither can distinguish two of its hotels from
#: one another -- Extended Stay America renamed every property to "Extended
#: Stay America Suites", it did not open a second chain. Each entry needs that
#: to be true of the whole chain, which is why this is a named table and not a
#: pattern.
_CHAIN_PRESENTATION: Tuple[Tuple[str, str], ...] = (
    ("extended stay america suites", "extended stay america"),
)


def _drop_an_operator_hotel(tokens: List[str]) -> List[str]:
    """PTF-INDIANAPOLIS-PLACES-SAVED-PAYLOAD-REBIND-011.

    IHG writes ", an IHG Hotel" where it elsewhere writes "by IHG". It is the
    same courtesy, said the other way round, and it names an operator rather
    than a building. Removed only as the exact three-token run.
    """
    out: List[str] = []
    index = 0
    while index < len(tokens):
        if (tokens[index] == "an" and index + 2 < len(tokens)
                and tokens[index + 1] in _OPERATOR_TOKENS
                and tokens[index + 2] == "hotel"):
            index += 3
            continue
        out.append(tokens[index])
        index += 1
    return out


def _drop_inn_suites(tokens: List[str]) -> List[str]:
    """"Comfort Inn & Suites Fishers" and "Comfort Inn Fishers" are one hotel.

    PTF-INDIANAPOLIS-PLACES-SAVED-PAYLOAD-REBIND-011 read this off three saved
    payloads where the brand's own URL confirms it -- Hilton serves
    ``indavhx-hampton-suites-avon-indianapolis`` for a census row that still
    says "Hampton Inn Indianapolis Avon". "& Suites" is a designation a chain
    adds to a property, not a second property.

    The token is dropped ONLY when it directly follows "inn", which is what
    keeps the dangerous case dangerous: in "Comfort Suites South" the "suites"
    follows "comfort", so it survives, and "Comfort Inn South" and "Comfort
    Suites South" remain two different brands and two different buildings.
    """
    return [token for index, token in enumerate(tokens)
            if not (token == "suites" and index > 0 and tokens[index - 1] == "inn")]


def presentation_key(name: str, *, state_code: str = "",
                     unordered: bool = False) -> str:
    """``normalise`` plus the presentation differences that name one building twice.

    PTF-INDIANAPOLIS-PLACES-NAME-NORMALIZATION-009 measured this on 25 paid
    Google Places lookups. Thirteen rows that bound on nothing still came back
    with a real property page, and eleven of those were the intended hotel under
    the brand's current marketing name. The rule was not wrong to refuse them --
    it was comparing presentation, not identity.

    THREE TRANSFORMATIONS, AND NOTHING ELSE:

      by <operator>   dropped as an exact pair, both sides
      <state code>    a bare "IN" inside "Motel 6 Indianapolis, IN - Airport"
      chain re-present "extended stay america suites" -> "extended stay america"

    WHAT IT WILL NOT TOUCH, BECAUSE THESE DISTINGUISH REAL BUILDINGS:
    airport, downtown, the compass words, and every locality -- plainfield,
    carmel, castleton, fishers, westfield, greenwood, and the city itself.
    "Courtyard Indianapolis AIRPORT Plainfield" and "Courtyard Indianapolis
    Plainfield" are two hotels and stay two hotels. Nor does it touch "inn" or
    "suites": Comfort Inn and Comfort Suites are two brands.

    There is no fuzzy matching here. Every output is a token sequence, compared
    for equality, and every difference between input and output is one of the
    three rules above.
    """
    tokens = normalise(name).split()
    if not tokens:
        return ""

    out: List[str] = []
    index = 0
    while index < len(tokens):
        if tokens[index] == "by":
            for operator in _OPERATOR_TOKENS:
                parts = operator.split()
                if tokens[index + 1:index + 1 + len(parts)] == parts:
                    index += 1 + len(parts)
                    break
            else:
                out.append(tokens[index])
                index += 1
            continue
        out.append(tokens[index])
        index += 1

    # "&" and "and" are one word written two ways. ``normalise`` already turns
    # "&" into a space, so dropping the written form is what makes
    # "Inn & Suites" and "Inn and Suites" the same name.
    if len(out) > 2:
        out = [t for t in out if t != "and"] or out

    state = normalise(state_code)
    if state and len(state) == 2:
        # A bare state code is where the row already says it is. It cannot
        # separate two hotels in one market, which is the only market this is
        # ever compared inside.
        trimmed = [t for t in out if t != state]
        if len(trimmed) >= 2:
            out = trimmed

    out = _drop_an_operator_hotel(out)
    out = _drop_inn_suites(out)

    joined = " ".join(out)
    for written, canonical in _CHAIN_PRESENTATION:
        if joined.startswith(written):
            joined = canonical + joined[len(written):]
            break
    joined = joined.strip()
    if unordered:
        # Google writes "Avon Indianapolis" where the census writes
        # "Indianapolis Avon". Comparing the SORTED tokens makes those one
        # name. This is exact multiset equality, not overlap scoring: every
        # word still has to be present on both sides, and one extra or one
        # missing word is still two different hotels.
        joined = " ".join(sorted(joined.split()))
    return joined


def distinctive_name_tokens(name: str) -> List[str]:
    """The words in a hotel's name that could identify THIS building in a URL."""
    return [t for t in normalise(name).split()
            if len(t) > 3 and t not in _GENERIC_NAME_WORDS]


def url_names_the_property(name: str, url: str) -> Tuple[bool, str]:
    """Does the URL's own text corroborate that it is about THIS hotel?

    Binding says which building a sighting describes. It does not say the URL
    that sighting carries is right, and in this corpus that is a real distinction:
    OpenStreetMap's ``website`` tag is typed in by hand, and Louisville has one
    element whose name and address are a Comfort Inn in Clarksville and whose
    website is a Sleep Inn in Shepherdsville. Binding on the address would import
    that URL under the right identity.

    So a proposal must also survive a reading of the URL itself: some word that
    distinguishes this hotel from the hotel next door has to appear in the host
    or the path. It refuses a brand property CODE (``marriott.com/sdfvn``), which
    is genuinely property-specific and genuinely unverifiable offline -- and
    refusing a real URL costs an unrouted identity, while accepting a wrong one
    costs another building's pet policy published under this hotel's name.
    """
    tokens = distinctive_name_tokens(name)
    text = _NON_ALNUM.sub(" ", (url or "").lower())
    found = [t for t in tokens if t in text.replace(" ", "")]
    if not tokens:
        return (False, "the property's name carries no distinctive word to "
                       "look for in a URL")
    if found:
        return (True, "the URL names the property (%s)" % ", ".join(found))
    return (False, "no distinctive word of the property's name appears in the "
                   "URL, so the URL cannot be read as being about this hotel")


class Observation:
    """One provider's sighting of a business, reduced to what can bind it."""

    __slots__ = ("provider", "source", "name", "phone", "postal", "url",
                 "street")

    def __init__(self, *, provider: str, source: str, name: str, phone: str,
                 postal: str, url: str, street: str = "") -> None:
        self.provider = provider
        self.source = source
        self.name = normalise(name)
        self.phone = digits(phone)
        self.postal = (postal or "").strip()
        self.url = (url or "").strip()
        self.street = street_key(street, postal)

    def to_dict(self) -> Dict:
        return {"provider": self.provider, "source": self.source,
                "name": self.name, "phone": self.phone,
                "postal_code": self.postal, "street_key": self.street,
                "url": self.url}


def _places_postal(place: Mapping) -> str:
    for component in place.get("addressComponents") or ():
        if "postal_code" in (component.get("types") or ()):
            return str(component.get("longText") or "")
    return ""


def _places_street(place: Mapping) -> str:
    """``"505 Marriott Dr"`` from the components Places returns it in."""
    parts = {}
    for component in place.get("addressComponents") or ():
        types = component.get("types") or ()
        for wanted in ("street_number", "route"):
            if wanted in types:
                parts[wanted] = str(component.get("longText") or "")
    if parts.get("street_number") and parts.get("route"):
        return "%s %s" % (parts["street_number"], parts["route"])
    return ""


def _osm_street(tags: Mapping) -> str:
    number = str(tags.get("addr:housenumber") or "").strip()
    street = str(tags.get("addr:street") or "").strip()
    return ("%s %s" % (number, street)) if number and street else ""


def read_cache(cache_dir: Path) -> List[Observation]:
    """Every cached provider sighting that carries a URL. Deduplicated by id."""
    seen: Dict[Tuple[str, str], Observation] = {}
    for path in sorted(cache_dir.rglob("page_*.json")):
        try:
            document = json.loads(path.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            continue
        payload = document.get("payload") or {}
        provider = str(document.get("provider") or "")
        relative = path.relative_to(cache_dir).as_posix()
        for place in payload.get("places") or ():
            url = str(place.get("websiteUri") or "")
            if not url:
                continue
            seen[(GOOGLE_PLACES, str(place.get("id")))] = Observation(
                provider=GOOGLE_PLACES, source=relative,
                name=(place.get("displayName") or {}).get("text", ""),
                phone=str(place.get("nationalPhoneNumber") or ""),
                postal=_places_postal(place), street=_places_street(place),
                url=url)
        for element in payload.get("elements") or ():
            tags = element.get("tags") or {}
            url = str(tags.get("website") or tags.get("contact:website") or "")
            if not url:
                continue
            seen[(OPENSTREETMAP, "%s/%s" % (element.get("type"),
                                            element.get("id")))] = Observation(
                provider=OPENSTREETMAP, source=relative,
                name=str(tags.get("name") or ""),
                phone=str(tags.get("phone") or tags.get("contact:phone") or ""),
                postal=str(tags.get("addr:postcode") or ""),
                street=_osm_street(tags), url=url)
        if not provider:
            continue
    return list(seen.values())


#: Where a URL can be written in this corpus's own artifacts.
_URL_FIELDS: Tuple[str, ...] = ("official_url", "policy_url", "source_url",
                                "discovered_url", "final_url", "requested_url",
                                "official_property_url", "url")


def read_prior_census(path: Path) -> List[Observation]:
    """Every row of an earlier census of this market that carries a URL.

    A market rebuilt on a new discovery engine does not inherit what the old one
    found: Louisville's rebuild raised the census from 130 identities to 166 and
    lost the 91 official URLs the 130 carried, because the new engine (OSM) knows
    where a hotel IS and frequently not what its website is. Those URLs are on
    disk, they were paid for once, and re-reading them costs nothing.

    They are read as SIGHTINGS, not as authority. The prior row's own identity
    key is discarded here on purpose -- keys are market-build-local, and matching
    on one would carry forward whatever the old build's naming happened to be.
    What binds is what a telephone, a name, or a street says.
    """
    document = json.loads(path.read_text(encoding="utf-8-sig"))
    source = path.name
    observations: List[Observation] = []
    for row in document.get("hotels") or ():
        url = (row.get("official_url") or "").strip()
        if not url:
            continue
        observations.append(Observation(
            provider=PRIOR_BUILD, source=source,
            name=row.get("canonical_name", ""), phone=row.get("phone", ""),
            postal=row.get("postal_code", ""), street=row.get("address", ""),
            url=url))
    return observations


def urls_in_artifacts(paths: Sequence[Path]) -> Dict[str, List[Dict]]:
    """``identity_key -> [{"url": ..., "source": ...}]`` across old reports.

    A prior build leaves URLs in more places than its census: capture manifests,
    routing repairs, review packets. This reads them all so the question "does
    anything on disk know a URL for this identity?" is answered by evidence
    rather than by which file someone remembered.
    """
    out: Dict[str, List[Dict]] = {}
    for path in paths:
        try:
            document = json.loads(path.read_text(encoding="utf-8-sig"))
        except (ValueError, OSError):
            continue
        # PTF-INDIANAPOLIS-HARDENED-RECENSUS-002: the identity routing shard --
        # the canonical routing authority of every market -- keeps the key in
        # ``hotel_ref.identity_key`` and the URL in ``official_property_url``
        # one level up, so a walk that only pairs a URL with a key on the SAME
        # node read 10 Indianapolis routes and bound none of them. The key is
        # carried down from the nearest enclosing node that names one.
        stack: List = [(document, "")]
        while stack:
            node, enclosing = stack.pop()
            if isinstance(node, dict):
                hotel_ref = node.get("hotel_ref")
                key = str(node.get("identity_key")
                          or (hotel_ref.get("identity_key")
                              if isinstance(hotel_ref, dict) else "")
                          or enclosing)
                if key:
                    for field in _URL_FIELDS:
                        value = node.get(field)
                        if isinstance(value, str) and value.startswith("http"):
                            rows = out.setdefault(key, [])
                            if not any(r["url"] == value for r in rows):
                                rows.append({"url": value,
                                             "source": path.as_posix(),
                                             "field": field})
                stack.extend((child, key) for child in node.values())
            elif isinstance(node, list):
                stack.extend((child, enclosing) for child in node)
    return out


def read_prior_artifacts(census_path: Path, artifact_paths: Sequence[Path]
                         ) -> Tuple[List[Observation], Dict]:
    """``(observations, coverage)`` -- artifact URLs for prior rows that lack one.

    The prior census is what carries the identity fields a binding needs, so an
    artifact URL is only usable for an identity that census also holds. The
    coverage half is reported rather than dropped: "the old reports add nothing
    the old census did not already have" is a finding about this market, and it
    is only credible if the run that says it actually looked.
    """
    document = json.loads(census_path.read_text(encoding="utf-8-sig"))
    rows = {r["identity_key"]: r for r in document.get("hotels") or ()}
    by_key = urls_in_artifacts(artifact_paths)
    observations: List[Observation] = []
    added: List[Dict] = []
    for key, found in sorted(by_key.items()):
        row = rows.get(key)
        if row is None or (row.get("official_url") or "").strip():
            continue
        for entry in found:
            observations.append(Observation(
                provider=PRIOR_BUILD, source=entry["source"],
                name=row.get("canonical_name", ""), phone=row.get("phone", ""),
                postal=row.get("postal_code", ""), street=row.get("address", ""),
                url=entry["url"]))
            added.append(OrderedDict((("identity_key", key),
                                      ("url", entry["url"]),
                                      ("source", entry["source"]))))
    coverage = OrderedDict((
        ("artifacts_read", [p.as_posix() for p in artifact_paths]),
        ("identity_keys_with_a_url", len(by_key)),
        ("keys_absent_from_the_prior_census",
         sorted(k for k in by_key if k not in rows)),
        ("urls_for_prior_rows_whose_census_url_is_empty", len(added)),
        ("rows", added),
    ))
    return (observations, coverage)


def bind(row: Mapping, observations: Sequence[Observation],
         *, unambiguous_streets: Optional[frozenset] = None,
         acceptable: Optional[Callable[[Observation], Tuple[bool, str]]] = None,
         rejected: Optional[List[Dict]] = None,
         presentation_variants: bool = False
         ) -> Tuple[Optional[Observation], str]:
    """``(observation, binding)`` -- the strongest usable match, or ``(None, "")``.

    Phone is tried across every observation before name-and-postal is tried at
    all, so a weaker key can never win while a stronger one is available.

    ``unambiguous_streets`` opts a caller into the third key, street-and-postal,
    and carries the only street keys it may use: those held by exactly one census
    row AND exactly one observation. Passing ``None`` -- the default -- leaves
    the two original keys and nothing else, so a market that recovered its URLs
    under the old rule recovers the same ones today.

    ``acceptable`` judges the URL a bound sighting carries, and a sighting whose
    URL is rejected does not consume the row: the search CONTINUES to the next
    key. Louisville is why. Six of its Choice hotels each bind on their own
    telephone number to an OpenStreetMap element carrying one bulk-edited URL
    for a Sleep Inn in another city; one of those six also binds on its street
    address to the prior build's real property page. Stopping at the first key
    that matched would throw the good page away because a bad one was found
    first. Every rejection is appended to ``rejected`` -- what this module
    refuses is its whole value, and a silent refusal cannot be reviewed.
    """
    # PTF-INDIANAPOLIS-PLACES-NAME-NORMALIZATION-009. Opt-in, and default OFF
    # on purpose: every market that recovered its URLs under the old rule
    # recovers exactly the same ones today, and a caller has to ask for the
    # wider comparison before it applies.
    key = ((lambda n: presentation_key(n, state_code=str(row.get("state") or ""),
                                       unordered=True))
           if presentation_variants else normalise)
    name = key(row.get("canonical_name", ""))
    postal = (row.get("postal_code") or "").strip()
    phone = digits(row.get("phone", ""))
    street = (street_key(row.get("address", ""), postal)
              if unambiguous_streets is not None else "")

    levels = (
        (BIND_PHONE, (lambda o: bool(phone) and o.phone == phone)),
        (BIND_NAME_POSTAL, (lambda o: bool(name and postal) and key(o.name) == name
                            and bool(o.postal) and o.postal == postal)),
        (BIND_STREET_POSTAL, (lambda o: bool(street)
                              and street in (unambiguous_streets or frozenset())
                              and bool(o.street) and o.street == street)),
    )
    for binding, matches in levels:
        found = sorted((o for o in observations if matches(o)),
                       key=lambda o: _usefulness(row, o), reverse=True)
        if not found:
            continue
        if acceptable is None:
            return (found[0], binding)
        for observation in found:
            ok, why = acceptable(observation)
            if ok:
                return (observation, binding)
            if rejected is not None:
                rejected.append(OrderedDict((
                    ("binding", binding), ("url", observation.url),
                    ("why", why), ("evidence", observation.to_dict()))))
    return (None, "")


def _usefulness(row: Mapping, observation: Observation) -> Tuple[int, int]:
    """Which of two equally-bound sightings carries the better URL.

    Binding strength says which BUILDING a sighting describes; it says nothing
    about the quality of the URL that sighting happens to carry, and taking the
    first match makes that choice by list order. Louisville has both halves of
    the problem at one hotel: an OpenStreetMap element and the prior build's
    census both bind to the Seelbach on its telephone number, one carrying the
    hotel's bare domain -- a brand index no lane can fetch -- and the other its
    Hilton property page. The property page is the answer, and it is not the
    first one in the list.
    """
    named, _ = url_names_the_property(row.get("canonical_name", ""),
                                      observation.url)
    routable = (MR.classify_url_shape(MR.normalize_source_url(observation.url))
                in MR.ROUTABLE_SHAPES)
    return (1 if routable else 0, 1 if named else 0)


def unambiguous_street_keys(rows: Sequence[Mapping],
                            observations: Sequence[Observation]) -> frozenset:
    """Street keys that name exactly one census row.

    The census side is the side that must be unique, and it is not a formality.
    Louisville's Galt House is two towers -- Rivue Tower and the Galt House
    itself -- at one street address: a street key held by two census rows would
    bind one URL to two identities, and two identities on one URL means at least
    one of them will carry another building's policy.

    The sighting side is deliberately NOT required to be unique. Several sources
    can describe one building at one address and carry different URLs -- that is
    the normal case, not a hazard -- and demanding uniqueness there threw away a
    real Choice property page because OpenStreetMap had also seen the same hotel.
    Which of several sightings is used is decided by the URL itself: the caller
    must corroborate it against the property's name, and the most useful URL wins
    among those that survive.

    ``observations`` stays in the signature because a key no sighting holds can
    never bind, and reporting the empty intersection is cheaper than searching it.
    """
    row_counts = Counter(filter(None, (
        street_key(r.get("address", ""), r.get("postal_code", "")) for r in rows)))
    seen = {o.street for o in observations if o.street}
    return frozenset(key for key, count in row_counts.items()
                     if count == 1 and key in seen)


def recover(rows: Sequence[Mapping], observations: Sequence[Observation],
            *, allow_street: bool = False, corroborate: bool = False,
            include_unroutable: bool = False) -> Tuple[List[Dict], List[Dict]]:
    """``(recovered, still_unknown)`` over the rows with no usable official URL.

    ``allow_street`` adds the street-and-postal key, restricted to keys that are
    one-to-one on both sides. ``corroborate`` additionally requires the URL's own
    text to name the property, and every rejected sighting is reported beside the
    row it was rejected for -- a refusal is a finding, not a silent drop.

    ``include_unroutable`` widens the population from "rows with no URL" to "rows
    with no URL a lane can fetch". A brand index, a city search or a category
    listing is a URL that cannot answer this hotel's question: seven Louisville
    identities carry one OpenStreetMap ``website`` tag that points at a Sleep Inn
    in another city entirely. Proposing a property page for such a row displaces
    nothing that was ever usable, and the proposal still has to bind and still
    has to be corroborated. A row whose URL a lane CAN fetch is never touched.
    """
    streets = (unambiguous_street_keys(rows, observations) if allow_street
               else None)
    recovered: List[Dict] = []
    unknown: List[Dict] = []
    for row in rows:
        current = MR.normalize_source_url((row.get("official_url") or "").strip())
        current_shape = MR.classify_url_shape(current)
        if current and not (include_unroutable
                            and current_shape not in MR.ROUTABLE_SHAPES):
            continue

        def acceptable(observation: Observation, _row=row, _current=current,
                       _shape=current_shape) -> Tuple[bool, str]:
            url = MR.normalize_source_url(observation.url)
            if _current and url == _current:
                return (False, "it is the same %s URL the census already holds, "
                               "so accepting it would count this row as improved "
                               "while leaving it exactly as unroutable" % _shape)
            if corroborate:
                return url_names_the_property(_row.get("canonical_name", ""), url)
            return (True, "")

        rejections: List[Dict] = []
        observation, binding = bind(
            row, observations, unambiguous_streets=streets,
            acceptable=acceptable, rejected=rejections)
        base = OrderedDict((
            ("identity_key", row["identity_key"]),
            ("canonical_name", row["canonical_name"]),
            ("city", row.get("city", "")),
            ("postal_code", row.get("postal_code", "")),
            ("phone", row.get("phone", "")),
            ("corridor", row.get("corridor", "")),
        ))
        if current:
            base["census_url"] = current
            base["census_url_shape"] = current_shape
        if observation is None:
            base["why"] = (
                "%d sighting(s) bound to this identity and every one was "
                "refused" % len(rejections) if rejections else
                "no sighting on disk carries a URL and binds to this identity "
                "on telephone, on name and postal code, or on street and postal "
                "code together")
            if rejections:
                base["refused"] = rejections
                base["refused_url"] = rejections[0]["url"]
            unknown.append(base)
            continue
        url = MR.normalize_source_url(observation.url)
        base["recovered_url"] = url
        base["url_shape"] = MR.classify_url_shape(url)
        base["brand"] = MR.brand_of(url) if url else ""
        base["binding"] = binding
        base["evidence"] = observation.to_dict()
        base["routable"] = base["url_shape"] in MR.ROUTABLE_SHAPES
        if current:
            base["displaces_unroutable_census_url"] = True
        if rejections:
            base["also_refused"] = rejections
        base["why"] = ("a %s sighting carrying a URL binds to this identity "
                       "on %s" % (observation.provider, binding))
        recovered.append(base)
    recovered.sort(key=lambda r: r["identity_key"])
    unknown.sort(key=lambda r: r["identity_key"])
    return (recovered, unknown)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--market", required=True)
    parser.add_argument("--cache", default="",
                        help="the discovery cache directory from the census pass")
    parser.add_argument("--prior-census", default="",
                        help="an earlier census of this market; its rows are "
                             "read as sightings, never as authority")
    parser.add_argument("--artifact", action="append", default=[],
                        help="an earlier report of this market that may carry "
                             "URLs; repeatable, and globs are expanded")
    parser.add_argument("--allow-street-binding", action="store_true",
                        help="add the street-and-postal key, restricted to keys "
                             "that name exactly one row and one sighting")
    parser.add_argument("--include-unroutable", action="store_true",
                        help="also propose for rows whose census URL is a brand "
                             "index, a city search or a third-party page -- a "
                             "URL no lane can fetch")
    parser.add_argument("--corroborate-url", action="store_true",
                        help="additionally require the URL's own text to name "
                             "the property, and report every refusal")
    parser.add_argument("--out", required=True)
    parser.add_argument("--work-order", default="")
    args = parser.parse_args(argv)

    if args.allow_street_binding and not args.corroborate_url:
        parser.error("--allow-street-binding requires --corroborate-url: a "
                     "street address is the weakest of the three keys and "
                     "several sources can describe one address, so the URL "
                     "itself has to name the property before it may be used")

    census = json.loads((CENSUS_DIR / ("%s.json" % args.market))
                        .read_text(encoding="utf-8"))
    observations: List[Observation] = []
    if args.cache:
        observations.extend(read_cache(Path(args.cache)))
    artifact_coverage: Dict = OrderedDict()
    if args.prior_census:
        prior_path = Path(args.prior_census)
        observations.extend(read_prior_census(prior_path))
        if args.artifact:
            paths = [Path(match) for pattern in args.artifact
                     for match in sorted(glob.glob(pattern))]
            extra, artifact_coverage = read_prior_artifacts(prior_path, paths)
            observations.extend(extra)
    elif args.artifact:
        parser.error("--artifact needs --prior-census: an artifact carries a "
                     "URL and an identity key, and the identity fields that "
                     "bind it live in the census that key belongs to")
    if not observations:
        parser.error("no evidence to read: pass --cache, --prior-census, or both")
    recovered, unknown = recover(census["hotels"], observations,
                                 allow_street=args.allow_street_binding,
                                 corroborate=args.corroborate_url,
                                 include_unroutable=args.include_unroutable)

    document = OrderedDict((
        ("schema", SCHEMA),
        ("what_this_is",
         "Official URLs proposed for census identities that have none, read "
         "back out of the discovery payloads this market already paid for. "
         "Zero network, zero spend. Nothing here edits the census."),
        ("market_id", args.market),
        ("work_order", args.work_order),
        ("cache_dir", Path(args.cache).as_posix() if args.cache else ""),
        ("prior_census", (Path(args.prior_census).as_posix()
                          if args.prior_census else "")),
        ("evidence_families", OrderedDict(
            sorted(Counter(o.provider for o in observations).items()))),
        ("binding_keys_offered",
         [BIND_PHONE, BIND_NAME_POSTAL]
         + ([BIND_STREET_POSTAL] if args.allow_street_binding else [])),
        ("url_corroboration_required", bool(args.corroborate_url)),
        ("unroutable_census_urls_included", bool(args.include_unroutable)),
        ("displacements_proposed",
         sum(1 for r in recovered if r.get("displaces_unroutable_census_url"))),
        ("cached_sightings_with_a_url", len(observations)),
        ("rows_without_a_usable_url_before", len(recovered) + len(unknown)),
        ("recovered", len(recovered)),
        ("routable_recoveries", sum(1 for r in recovered if r["routable"])),
        ("still_unknown", len(unknown)),
        ("binding_counts", OrderedDict(
            sorted(Counter(r["binding"] for r in recovered).items()))),
        ("recovered_by_provider", OrderedDict(
            sorted(Counter(r["evidence"]["provider"] for r in recovered).items()))),
        ("recovered_url_shapes", OrderedDict(
            sorted(Counter(r["url_shape"] for r in recovered).items()))),
        ("binding_rule",
         "telephone digits equal, or name AND postal code both equal, or -- "
         "when street binding is allowed -- street AND postal code both equal "
         "on a key held by exactly one row and one sighting; an empty field "
         "never matches an empty field"),
        ("artifact_coverage", artifact_coverage),
        ("recoveries", recovered),
        ("still_unknown_rows", unknown),
    ))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(document, indent=1, ensure_ascii=False) + "\n",
                   encoding="utf-8", newline="\n")
    print("sightings with a URL : %d" % len(observations))
    print("no usable URL before : %d" % document["rows_without_a_usable_url_before"])
    print("recovered            : %d (%d routable)"
          % (len(recovered), document["routable_recoveries"]))
    print("still unknown        : %d" % len(unknown))
    print("written              : %s" % out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
