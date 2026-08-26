"""PTF-DISCOVERY-OVERPASS-RESILIENCE-001 -- a local OSM extract as a discovery source.
Same question, same cache key, same candidate contract; no public server."""

from __future__ import annotations

import json

import pytest

from scripts.pettripfinder.discovery import constants as C
from scripts.pettripfinder.discovery import osm_extract as X
from scripts.pettripfinder.discovery import overpass as OV
from scripts.pettripfinder.discovery.cache import DiscoveryCache
from scripts.pettripfinder.discovery.models import DiscoverySourceQuery
from scripts.pettripfinder.discovery.query_plan import RequestBudget


def query(n=1, tag="tourism=hotel"):
    return DiscoverySourceQuery(
        query_id="OPENSTREETMAP__hotel__m__cell%02d" % n, provider=C.PROVIDER_OPENSTREETMAP,
        canonical_category=C.CATEGORY_HOTEL, query_text=tag, market_id="m",
        cell_id="cell%02d" % n, center_lat=40.0, center_lng=-80.0, radius_meters=3000,
        max_pages=1)


def index():
    return X.ExtractIndex(X.index_document(
        extract_id="pennsylvania-2026-08-01",
        source={"pbf": "pennsylvania-latest.osm.pbf",
                "url": "https://download.geofabrik.de/north-america/us/pennsylvania.html",
                "extracted_at": "2026-08-01"},
        elements=[
            {"type": "node", "id": 1, "lat": 40.001, "lon": -80.001,
             "tags": {"tourism": "hotel", "name": "Inside Hotel"}},
            {"type": "way", "id": 2, "center": {"lat": 40.002, "lon": -80.002},
             "tags": {"tourism": "motel", "name": "Inside Motel"}},
            {"type": "node", "id": 3, "lat": 45.0, "lon": -80.0,
             "tags": {"tourism": "hotel", "name": "Far Hotel"}},
            {"type": "node", "id": 4, "lat": 40.0, "lon": -80.0,
             "tags": {"amenity": "veterinary", "name": "Vet"}},
        ]))


class TestIndex:
    def test_a_query_answers_in_overpass_shape_bounded_by_bbox_and_tag(self):
        bbox = OV.bbox_from_center_radius(40.0, -80.0, 3000)
        payload = index().query("tourism=hotel", bbox)
        assert [e["id"] for e in payload["elements"]] == [1]
        assert payload["elements"][0]["type"] == "node"
        assert index().query("tourism=motel", bbox)["elements"][0]["id"] == 2
        assert index().query("shop=pet", bbox)["elements"] == []

    def test_a_malformed_index_fails_closed(self):
        with pytest.raises(X.ExtractError):
            X.ExtractIndex({"schema": "nope"})
        with pytest.raises(X.ExtractError):
            X.ExtractIndex({"schema": X.INDEX_SCHEMA, "extract_id": "", "elements": []})
        with pytest.raises(X.ExtractError):
            X.ExtractIndex({"schema": X.INDEX_SCHEMA, "extract_id": "x",
                            "elements": [{"type": "blob", "id": 1}]})

    def test_the_pbf_reducer_refuses_honestly_without_its_dependency(self, tmp_path, monkeypatch):
        import builtins
        real_import = builtins.__import__

        def fake_import(name, *args, **kwargs):
            if name == "osmium":
                raise ImportError("no osmium")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", fake_import)
        with pytest.raises(X.ExtractError) as raised:
            X.build_index_from_pbf(tmp_path / "x.osm.pbf", extract_id="x", out=tmp_path / "i.json")
        assert "pyosmium" in str(raised.value)


class TestSource:
    def test_it_answers_a_cell_locally_and_parses_through_the_overpass_reader(self, tmp_path):
        cache = DiscoveryCache(tmp_path)
        source = X.LocalOsmExtractSource(index())
        budget = RequestBudget(0)            # a local answer spends no public budget
        result = source.search(query(), cache=cache, budget=budget, observed_at="2026-08-25")
        assert result.state == C.QUERY_STATE_COMPLETED
        assert [r.provider_record_id for r in result.records] == ["node/1"]
        assert result.records[0].provider == C.PROVIDER_OPENSTREETMAP
        assert dict(result.records[0].provenance)["attribution"] == C.OVERPASS_ATTRIBUTION
        assert budget.used == 0

    def test_the_cache_key_is_shared_with_the_overpass_client(self, tmp_path):
        cache = DiscoveryCache(tmp_path)
        X.LocalOsmExtractSource(index()).search(query(), cache=cache, budget=None,
                                                observed_at="2026-08-25")
        entry, kind = OV.lookup_cached(cache, query(), legacy_endpoint_urls=())
        assert kind == "current"
        provenance = OV.entry_provenance(entry)
        assert provenance["endpoint_id"] == "local_extract:pennsylvania-2026-08-01"
        assert provenance["endpoint_url"].startswith("https://download.geofabrik.de")
        assert provenance["query_version"] == OV.OVERPASS_QUERY_VERSION
        # A later Overpass client finds the locally answered cell as a hit.
        legacy_client = OV.OverpassClient(session=object(), sleep_fn=lambda s: None)
        again = legacy_client.search(query(), cache=cache, budget=RequestBudget(5),
                                     observed_at="2026-08-25")
        assert again.cache_hits == 1 and again.requests_made == 0

    def test_a_cell_already_cached_is_not_re_answered(self, tmp_path):
        cache = DiscoveryCache(tmp_path)
        source = X.LocalOsmExtractSource(index())
        source.search(query(), cache=cache, budget=None, observed_at="2026-08-25")
        second = source.search(query(), cache=cache, budget=None, observed_at="2026-08-25")
        assert second.cache_hits == 1
        assert source.run_stats()["requests"] == 1 and source.run_stats()["cache_hits"] == 1

    def test_the_runner_uses_the_extract_when_configured(self, tmp_path, monkeypatch):
        from scripts.pettripfinder.discovery import runner
        path = tmp_path / "index.json"
        path.write_text(json.dumps(index().to_document()), encoding="utf-8")
        config = runner.RunConfig(market_id="m", providers=(C.PROVIDER_OPENSTREETMAP,),
                                  categories=(C.CATEGORY_HOTEL,), output_root=str(tmp_path),
                                  observed_at="2026-08-25", osm_extract_index=str(path))
        source = runner.default_overpass_source(config)
        assert isinstance(source, X.LocalOsmExtractSource)

    def test_the_runner_defaults_to_the_resilient_client_otherwise(self, tmp_path):
        from scripts.pettripfinder.discovery import runner
        config = runner.RunConfig(market_id="m", providers=(C.PROVIDER_OPENSTREETMAP,),
                                  categories=(C.CATEGORY_HOTEL,), output_root=str(tmp_path),
                                  observed_at="2026-08-25")
        source = runner.default_overpass_source(config)
        assert isinstance(source, OV.OverpassClient) and source.resilient
        assert source.selector.ledger_path == tmp_path / "overpass_endpoint_health.json"
