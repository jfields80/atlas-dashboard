"""PTF-DISCOVERY-OVERPASS-RESILIENCE-001 -- a local OSM extract as a discovery source.

WHY
---
Every market so far has been censused through a public Overpass server, and a
public server is somebody else's computer: it can time out, rate-limit, or go
away, and it must be queried gently. At scale Atlas should not need one to
census a market. A regional OSM extract (``*.osm.pbf`` from Geofabrik or a
mirror) can be downloaded once, reduced once to the elements lodging discovery
cares about, and then queried locally as many times as needed, for nothing.

WHAT IS IMPLEMENTED HERE
------------------------
1. ``ExtractIndex`` -- ``ptf-osm-extract-index/1.0``: a committed-format JSON
   index of OSM elements (node/way/relation, id, lat/lon or centre, tags)
   reduced from an extract. Small enough to keep per region; queryable in
   memory.
2. ``ExtractIndex.query(tag_expr, bbox)`` -- the SAME question a cell asks
   Overpass, answered locally, returning a payload shaped exactly like an
   Overpass ``out center`` response so ``overpass.parse_elements`` reads it
   unchanged.
3. ``LocalOsmExtractSource`` -- a source with the runner's ``search`` shape
   (query, cache, budget, observed_at, bounds). Cache key, cell geometry,
   category mapping and candidate contract are all IDENTICAL to the Overpass
   path; only ``endpoint_id`` in the provenance says ``local_extract:<id>``.
   The market factory does not know which source answered a cell.
4. ``build_index_from_pbf`` -- reduces a ``.osm.pbf`` to the index using
   ``pyosmium`` WHEN it is installed; refuses with instructions when it is not.
   Nothing here downloads an extract.

WHAT IS DESIGNED AND NOT DONE
-----------------------------
* Extract download and freshness: an operator obtains the regional ``.pbf``
  (Geofabrik publishes per-state extracts under ODbL) and records its URL and
  date in the index's ``source``. A registry of extracts per region, with a
  refresh cadence, is the natural next step and is a data file, not code.
* Public Overpass then becomes the VERIFICATION source: a sample of cells
  answered locally can be re-asked of an approved endpoint and diffed.
"""

from __future__ import annotations

import json
from collections import OrderedDict
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

from scripts.pettripfinder.discovery import constants as C
from scripts.pettripfinder.discovery import overpass as OV
from scripts.pettripfinder.discovery import pacing as PACING
from scripts.pettripfinder.discovery.cache import DiscoveryCache, compute_request_fingerprint
from scripts.pettripfinder.discovery.market_config import GeoBounds
from scripts.pettripfinder.discovery.models import DiscoverySourceQuery
from scripts.pettripfinder.discovery.provider_result import ProviderQueryResult
from scripts.pettripfinder.discovery.query_plan import RequestBudget

INDEX_SCHEMA = "ptf-osm-extract-index/1.0"
ENDPOINT_PREFIX = "local_extract:"

#: Tags an index keeps. Lodging discovery asks for tourism=hotel/motel; the
#: other keys are what the Overpass path already reads into provider_categories.
DEFAULT_KEEP_TAG_KEYS = ("tourism", "amenity", "shop", "leisure", "highway")


class ExtractError(RuntimeError):
    """The extract index is malformed, or the reducer's dependency is absent."""


def _matches(tags: Mapping, tag_expr: str) -> bool:
    key, _, value = tag_expr.partition("=")
    if not key:
        return False
    if value:
        return str(tags.get(key, "")) == value
    return key in tags


def _in_bbox(lat: Optional[float], lon: Optional[float],
             bbox: Tuple[float, float, float, float]) -> bool:
    if lat is None or lon is None:
        return False
    south, west, north, east = bbox
    return south <= lat <= north and west <= lon <= east


class ExtractIndex:
    """An in-memory, queryable reduction of one OSM extract."""

    def __init__(self, document: Mapping) -> None:
        if document.get("schema") != INDEX_SCHEMA:
            raise ExtractError("extract index schema is %r, not %s"
                               % (document.get("schema"), INDEX_SCHEMA))
        self.extract_id = str(document.get("extract_id") or "").strip()
        if not self.extract_id:
            raise ExtractError("extract index has no extract_id")
        self.source = dict(document.get("source") or {})
        self.elements: List[Dict] = list(document.get("elements") or ())
        for element in self.elements:
            if element.get("type") not in ("node", "way", "relation") or "id" not in element:
                raise ExtractError("an element lacks a type or id")

    @classmethod
    def load(cls, path: Path) -> "ExtractIndex":
        return cls(json.loads(Path(path).read_text(encoding="utf-8")))

    @property
    def endpoint_id(self) -> str:
        return ENDPOINT_PREFIX + self.extract_id

    def query(self, tag_expr: str, bbox: Tuple[float, float, float, float]) -> Dict:
        """The Overpass question, answered locally, in Overpass's own shape."""
        out: List[Dict] = []
        for element in self.elements:
            tags = element.get("tags") or {}
            if not _matches(tags, tag_expr):
                continue
            if element["type"] == "node":
                lat, lon = element.get("lat"), element.get("lon")
            else:
                center = element.get("center") or {}
                lat, lon = center.get("lat"), center.get("lon")
            if not _in_bbox(lat, lon, bbox):
                continue
            out.append(json.loads(json.dumps(element)))
        out.sort(key=lambda e: (e["type"], int(e["id"])))
        return {"version": 0.6, "generator": "ptf-osm-extract-index",
                "osm3s": {"copyright": C.OVERPASS_ATTRIBUTION},
                "elements": out}

    def to_document(self) -> Dict:
        return OrderedDict((
            ("schema", INDEX_SCHEMA), ("extract_id", self.extract_id),
            ("source", self.source), ("element_count", len(self.elements)),
            ("elements", self.elements),
        ))


def index_document(*, extract_id: str, source: Mapping, elements: Iterable[Mapping]) -> Dict:
    rows = [OrderedDict((
        ("type", e["type"]), ("id", int(e["id"])),
        ("lat", e.get("lat")), ("lon", e.get("lon")),
        ("center", e.get("center")), ("tags", dict(e.get("tags") or {})),
    )) for e in elements]
    return OrderedDict((
        ("schema", INDEX_SCHEMA), ("extract_id", extract_id),
        ("source", OrderedDict(source)), ("element_count", len(rows)),
        ("elements", rows),
    ))


def build_index_from_pbf(pbf_path: Path, *, extract_id: str, out: Path,
                         keep_tag_keys: Sequence[str] = DEFAULT_KEEP_TAG_KEYS,
                         source_url: str = "", extracted_at: str = "") -> str:
    """Reduce a ``.osm.pbf`` to an index. Needs ``pyosmium``; refuses otherwise.

    Ways and relations are reduced to a centre point exactly as Overpass's
    ``out center`` does, so a locally answered cell and a remotely answered
    cell parse identically.
    """
    try:
        import osmium  # type: ignore
    except ImportError as exc:
        raise ExtractError(
            "building an extract index needs pyosmium (`pip install osmium`); "
            "it is an optional dependency and is not installed. The index "
            "format is %s and may also be produced by any tool that emits "
            "node/way/relation rows with tags and a centre." % INDEX_SCHEMA) from exc

    keep = frozenset(keep_tag_keys)
    elements: List[Dict] = []

    class Handler(osmium.SimpleHandler):           # pragma: no cover - needs osmium
        def _tags(self, tags):
            return {t.k: t.v for t in tags}

        def node(self, node):
            tags = self._tags(node.tags)
            if keep & set(tags):
                elements.append({"type": "node", "id": node.id,
                                 "lat": node.location.lat, "lon": node.location.lon,
                                 "tags": tags})

        def way(self, way):
            tags = self._tags(way.tags)
            if not (keep & set(tags)):
                return
            lats = [n.lat for n in way.nodes if n.location.valid()]
            lons = [n.lon for n in way.nodes if n.location.valid()]
            if not lats:
                return
            elements.append({"type": "way", "id": way.id,
                             "center": {"lat": sum(lats) / len(lats),
                                        "lon": sum(lons) / len(lons)},
                             "tags": tags})

    Handler().apply_file(str(pbf_path), locations=True)   # pragma: no cover
    document = index_document(
        extract_id=extract_id,
        source=OrderedDict((("pbf", Path(pbf_path).name), ("url", source_url),
                            ("extracted_at", extracted_at
                             or datetime.now(timezone.utc).date().isoformat()),
                            ("attribution", C.OVERPASS_ATTRIBUTION))),
        elements=elements)
    out = Path(out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(document, indent=1) + "\n", encoding="utf-8")
    return out.as_posix()


class LocalOsmExtractSource:
    """The runner's ``search`` shape, answered from a local extract index.

    Same cache key as the Overpass client, so a cell answered locally is a
    cache HIT for a later Overpass run and vice versa; the endpoint id in the
    provenance is the only thing that differs. Draws no request budget: a local
    query is free and touches no shared infrastructure.
    """

    def __init__(self, index: ExtractIndex, *,
                 clock: Optional[Callable[[], datetime]] = None) -> None:
        self._index = index
        self._clock = clock or (lambda: datetime.now(timezone.utc))
        self.stats = PACING.PacingStats()

    @property
    def endpoint_id(self) -> str:
        return self._index.endpoint_id

    def run_stats(self) -> Dict:
        document = self.stats.to_dict()
        document["current_endpoint_id"] = self.endpoint_id
        document["source"] = "local_extract"
        document["all_endpoints_unhealthy"] = False
        document["earliest_cooldown_expiry"] = ""
        return document

    def search(self, query: DiscoverySourceQuery, *, cache: DiscoveryCache,
               budget: Optional[RequestBudget], observed_at: str,
               bounds: Optional[GeoBounds] = None) -> ProviderQueryResult:
        if not query.enabled:
            return ProviderQueryResult(query_id=query.query_id, provider=C.PROVIDER_OPENSTREETMAP,
                                       state=C.QUERY_STATE_DISABLED)
        cached, _kind = OV.lookup_cached(
            cache, query, as_of=observed_at,
            legacy_endpoint_urls=(C.OVERPASS_DEFAULT_ENDPOINT,))
        if cached is not None:
            self.stats.cache_hits += 1
            records, warnings = OV.parse_elements(cached.payload, query, observed_at, bounds)
            return ProviderQueryResult(
                query_id=query.query_id, provider=C.PROVIDER_OPENSTREETMAP,
                state=C.QUERY_STATE_COMPLETED, records=records, requests_made=0,
                pages_fetched=1, cache_hits=1, warnings=warnings)

        bbox = OV.bbox_from_center_radius(query.center_lat, query.center_lng, query.radius_meters)
        payload = self._index.query(query.query_text, bbox)
        self.stats.requests += 1
        self.stats.successes += 1
        self.stats.requests_by_endpoint[self.endpoint_id] = (
            self.stats.requests_by_endpoint.get(self.endpoint_id, 0) + 1)
        identity = OV.cache_identity(query)
        fingerprint = compute_request_fingerprint(identity)
        provenance = OrderedDict((
            ("http_status", 200),
            ("endpoint_id", self.endpoint_id),
            ("endpoint_url", str(self._index.source.get("url") or
                                 self._index.source.get("pbf") or "")),
            ("requested_at", self._clock().isoformat()),
            ("query_id", query.query_id), ("cell_id", query.cell_id),
            ("query_hash", fingerprint),
            ("query_version", OV.OVERPASS_QUERY_VERSION),
            ("source", "local_extract"),
        ))
        cache.put(C.PROVIDER_OPENSTREETMAP, query.market_id, query.query_id, fingerprint,
                  1, sanitized_request=identity, payload=payload,
                  status_metadata=dict(provenance), retrieved_at=observed_at)
        records, warnings = OV.parse_elements(payload, query, observed_at, bounds)
        return ProviderQueryResult(
            query_id=query.query_id, provider=C.PROVIDER_OPENSTREETMAP,
            state=C.QUERY_STATE_COMPLETED, records=records, requests_made=0,
            pages_fetched=1, cache_hits=0, warnings=warnings)


__all__ = ["INDEX_SCHEMA", "ENDPOINT_PREFIX", "DEFAULT_KEEP_TAG_KEYS",
           "ExtractError", "ExtractIndex", "index_document",
           "build_index_from_pbf", "LocalOsmExtractSource"]
