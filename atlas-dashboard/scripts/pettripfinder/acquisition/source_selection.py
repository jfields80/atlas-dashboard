"""WHICH PAGE acquisition starts from -- one seam, for every market.

A property has two URLs and they answer different questions.

``official_url`` in the identity census answers "where was this hotel found,
and what proves it is this hotel". It is authority: it is what the identity
resolver matched, what the exclusion registry cites, and what a reviewer opens
to check that a record is the property it claims to be. Editing it to point at
a better page would rewrite that history for a reason that has nothing to do
with identity.

The discovered-policy overlay answers a narrower question: "of the pages this
property publishes, which one carries the pet policy". Nine of eleven Milwaukee
independents named a homepage as their official URL, and a homepage is not a
policy page; the discovery layer (``source_discovery``) found a better one for
eight of them from the property's own links.

So the two live apart and this module is where they meet. The census URL stays
canonical and unedited. The overlay is a PREFERENCE layered on top of it, read
here, recorded in provenance, and withdrawable by deleting one row.

WHY ROUTING IS PASSED THE CENSUS URL
------------------------------------
``registry.resolve`` keys on the URL's HOST, so a discovered URL on a different
host would silently move a property to a different provider lane. Which page we
read and which provider fetches it are separate decisions, and a change to the
first must not quietly make the second. ``route_url`` on the selection carries
the census URL for exactly that purpose, and the router accepts it.

WHY THE CACHE KEY IS BUILT HERE
-------------------------------
015 lost three properties to a cache keyed on the URL PATH: ``/faq`` is not
unique across hotels, so one property was served another's document. A cached
document belongs to a (property, URL) pair and to nothing looser, and
``cache_key`` is the single place that decides so.
"""

from __future__ import annotations

import hashlib
import re
import sys
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, Mapping, Optional, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.acquisition import source_discovery as SD  # noqa: E402
from scripts.pettripfinder.brightdata import cross_brand_pilot_002 as P2  # noqa: E402

REPO = _REPO_ROOT

#: Where the selected URL came from. Two values, because there are two answers.
FROM_DISCOVERY = "DISCOVERED_POLICY_URL"
FROM_CENSUS = "CENSUS_OFFICIAL_URL"


def _slug(value: str) -> str:
    """A filesystem-safe form of an identity key. Local by design: the key is
    part of a cache path here, not part of any published identity."""
    return re.sub(r"[^a-z0-9]+", "-", (value or "").lower()).strip("-")


@dataclass(frozen=True)
class SourceSelection:
    """The URL acquisition will start from, and why it is that one.

    Both URLs are carried, always. A report that shows only the URL that was
    used cannot answer "was the overlay consulted, and did it change anything",
    which is the question this work order exists to make answerable.
    """

    identity_key: str
    census_url: str
    selected_url: str
    source: str
    overlay_status: str = ""
    overlay_present: bool = False
    provenance: Mapping = field(default_factory=dict)

    @property
    def route_url(self) -> str:
        """The URL ROUTING must use: always the census URL.

        Never the selected one. See the module docstring.
        """
        return self.census_url

    @property
    def changed(self) -> bool:
        return self.selected_url != self.census_url

    def to_dict(self) -> Dict:
        return {
            "identity_key": self.identity_key,
            "census_official_url": self.census_url,
            "selected_source_url": self.selected_url,
            "route_url": self.route_url,
            "source": self.source,
            "overlay_status": self.overlay_status,
            "overlay_present": self.overlay_present,
            "overlay_changed_source": self.changed,
            "provenance": dict(self.provenance),
        }


def select(identity_key: str, census_url: str, *, market_id: str,
           repo: Optional[Path] = None) -> SourceSelection:
    """Pick the page to read for one property.

    Falls back to the census URL whenever the overlay has no row, has a row
    that resolved to nothing, or does not exist for this market at all. A
    market with no overlay file behaves exactly as it did before this seam
    existed -- that is the property that makes it safe to put on the shared
    path rather than behind a market test.
    """
    repo = repo or REPO
    row = SD.load_overlay(repo, market_id).get(identity_key) or {}
    selected = SD.resolve_source_url(repo, market_id, identity_key, census_url)
    from_overlay = bool(row) and selected != census_url
    return SourceSelection(
        identity_key=identity_key,
        census_url=census_url,
        selected_url=selected,
        source=FROM_DISCOVERY if from_overlay else FROM_CENSUS,
        overlay_status=row.get("status", ""),
        overlay_present=bool(row),
        provenance=dict(row.get("provenance") or {}))


def resolved_target(record, *, market_id: str = "",
                    repo: Optional[Path] = None) -> Tuple[object, SourceSelection]:
    """A capture target aimed at the policy page, with the selection beside it.

    ``record.source_url`` -- the census URL -- is NOT modified. The target is
    built from the record and then re-aimed, so the record a caller holds after
    this call says the same thing it said before.
    """
    selection = select(record.identity_key, record.source_url,
                       market_id=market_id or record.market_id, repo=repo)
    target = P2.target_for(record)
    if selection.changed:
        target = _retargeted(target, selection.selected_url)
    return target, selection


def _retargeted(target, url: str):
    """The same target, pointed at another page of the same property.

    ``CaptureTarget`` is frozen and shared with the committed pilots, so it is
    replaced rather than mutated, and every identity field is carried across
    unchanged: this changes which PAGE is fetched, never which HOTEL it is.
    """
    fields = dict(target.__dict__)
    fields["requested_url"] = url
    return type(target)(**fields)


def cache_key(identity_key: str, url: str) -> str:
    """A cache directory name that belongs to one property and one URL.

    The failure this pins: 015 keyed cached documents on a slug of the URL
    PATH. ``/faq`` is a path many hotels publish, so a lookup for one property
    matched a directory belonging to another and returned its document. A key
    that omits the property cannot be made safe by making the path slug longer,
    so the property is IN the key, and a hash of the full URL follows it so two
    different pages of one property can never collapse either.
    """
    digest = hashlib.sha256(url.encode("utf-8")).hexdigest()[:16]
    return "%s--%s" % (_slug(identity_key)[:60], digest)


__all__ = ["FROM_CENSUS", "FROM_DISCOVERY", "SourceSelection", "select",
           "resolved_target", "cache_key", "REPO"]
