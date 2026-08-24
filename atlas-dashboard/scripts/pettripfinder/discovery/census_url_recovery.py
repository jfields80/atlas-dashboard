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
import json
import re
import sys
from collections import Counter, OrderedDict
from pathlib import Path
from typing import Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.acquisition import market_routing as MR  # noqa: E402

SCHEMA = "ptf-census-url-recovery/1.0"
CENSUS_DIR = _REPO_ROOT / "launch_packages" / "pettripfinder" / "identity_census"

GOOGLE_PLACES = "GOOGLE_PLACES"
OPENSTREETMAP = "OPENSTREETMAP"

BIND_PHONE = "PHONE"
BIND_NAME_POSTAL = "NAME_AND_POSTAL_CODE"

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


class Observation:
    """One provider's sighting of a business, reduced to what can bind it."""

    __slots__ = ("provider", "source", "name", "phone", "postal", "url")

    def __init__(self, *, provider: str, source: str, name: str, phone: str,
                 postal: str, url: str) -> None:
        self.provider = provider
        self.source = source
        self.name = normalise(name)
        self.phone = digits(phone)
        self.postal = (postal or "").strip()
        self.url = (url or "").strip()

    def to_dict(self) -> Dict:
        return {"provider": self.provider, "source": self.source,
                "name": self.name, "phone": self.phone,
                "postal_code": self.postal, "url": self.url}


def _places_postal(place: Mapping) -> str:
    for component in place.get("addressComponents") or ():
        if "postal_code" in (component.get("types") or ()):
            return str(component.get("longText") or "")
    return ""


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
                postal=_places_postal(place), url=url)
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
                postal=str(tags.get("addr:postcode") or ""), url=url)
        if not provider:
            continue
    return list(seen.values())


def bind(row: Mapping, observations: Sequence[Observation]
         ) -> Tuple[Optional[Observation], str]:
    """``(observation, binding)`` -- the strongest match, or ``(None, "")``.

    Phone is tried across every observation before name-and-postal is tried at
    all, so a weaker key can never win while a stronger one is available.
    """
    phone = digits(row.get("phone", ""))
    if phone:
        for observation in observations:
            if observation.phone and observation.phone == phone:
                return (observation, BIND_PHONE)
    name = normalise(row.get("canonical_name", ""))
    postal = (row.get("postal_code") or "").strip()
    if name and postal:
        for observation in observations:
            if (observation.name == name and observation.postal
                    and observation.postal == postal):
                return (observation, BIND_NAME_POSTAL)
    return (None, "")


def recover(rows: Sequence[Mapping], observations: Sequence[Observation]
            ) -> Tuple[List[Dict], List[Dict]]:
    """``(recovered, still_unknown)`` over the rows with no official URL."""
    recovered: List[Dict] = []
    unknown: List[Dict] = []
    for row in rows:
        if (row.get("official_url") or "").strip():
            continue
        observation, binding = bind(row, observations)
        base = OrderedDict((
            ("identity_key", row["identity_key"]),
            ("canonical_name", row["canonical_name"]),
            ("city", row.get("city", "")),
            ("postal_code", row.get("postal_code", "")),
            ("phone", row.get("phone", "")),
            ("corridor", row.get("corridor", "")),
        ))
        if observation is None:
            base["why"] = ("no cached provider sighting carries a URL and binds "
                           "to this identity on telephone or on name and postal "
                           "code together")
            unknown.append(base)
            continue
        url = MR.normalize_source_url(observation.url)
        base["recovered_url"] = url
        base["url_shape"] = MR.classify_url_shape(url)
        base["brand"] = MR.brand_of(url) if url else ""
        base["binding"] = binding
        base["evidence"] = observation.to_dict()
        base["routable"] = base["url_shape"] in MR.ROUTABLE_SHAPES
        base["why"] = ("a cached %s sighting carrying a URL binds to this "
                       "identity on %s" % (observation.provider, binding))
        recovered.append(base)
    recovered.sort(key=lambda r: r["identity_key"])
    unknown.sort(key=lambda r: r["identity_key"])
    return (recovered, unknown)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--market", required=True)
    parser.add_argument("--cache", required=True,
                        help="the discovery cache directory from the census pass")
    parser.add_argument("--out", required=True)
    parser.add_argument("--work-order", default="")
    args = parser.parse_args(argv)

    census = json.loads((CENSUS_DIR / ("%s.json" % args.market))
                        .read_text(encoding="utf-8"))
    observations = read_cache(Path(args.cache))
    recovered, unknown = recover(census["hotels"], observations)

    document = OrderedDict((
        ("schema", SCHEMA),
        ("what_this_is",
         "Official URLs proposed for census identities that have none, read "
         "back out of the discovery payloads this market already paid for. "
         "Zero network, zero spend. Nothing here edits the census."),
        ("market_id", args.market),
        ("work_order", args.work_order),
        ("cache_dir", Path(args.cache).as_posix()),
        ("cached_sightings_with_a_url", len(observations)),
        ("no_url_before", len(recovered) + len(unknown)),
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
         "telephone digits equal, or name AND postal code both equal; an empty "
         "field never matches an empty field"),
        ("recoveries", recovered),
        ("still_unknown_rows", unknown),
    ))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(document, indent=1, ensure_ascii=False) + "\n",
                   encoding="utf-8", newline="\n")
    print("sightings with a URL : %d" % len(observations))
    print("no URL before        : %d" % document["no_url_before"])
    print("recovered            : %d (%d routable)"
          % (len(recovered), document["routable_recoveries"]))
    print("still unknown        : %d" % len(unknown))
    print("written              : %s" % out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
