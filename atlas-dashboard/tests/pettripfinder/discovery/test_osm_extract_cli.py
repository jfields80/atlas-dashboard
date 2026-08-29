"""PTF-PITTSBURGH-HARDENED-RECENSUS-001 -- the local-extract fallback, operated:
the extract registry, a market's readiness, and the dry run that says which
cells an index would answer. No network, no pyosmium."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.pettripfinder import osm_extract_cli as CLI
from scripts.pettripfinder.discovery import constants as C
from scripts.pettripfinder.discovery import osm_extract as OX
from scripts.pettripfinder.discovery import overpass as OV
from scripts.pettripfinder.discovery.cache import DiscoveryCache, compute_request_fingerprint
from scripts.pettripfinder.discovery.market_config import load_market_config
from scripts.pettripfinder.discovery.query_plan import plan_queries


def registry_doc(local_pbf="data/osm_extracts/x.osm.pbf",
                 index_path="data/osm_extracts/x.index.json"):
    return {
        "schema": OX.REGISTRY_SCHEMA,
        "extracts": [{
            "extract_id": "test-extract", "region": "Testland",
            "url": "https://example.invalid/x.osm.pbf",
            "md5_url": "https://example.invalid/x.osm.pbf.md5",
            "local_pbf": local_pbf, "index_path": index_path,
            "markets": ["pittsburgh-pa"], "license": "ODbL 1.0",
        }],
    }


def pittsburgh_index(elements_per_cell=2):
    """An index with ``elements_per_cell`` hotels at every Pittsburgh cell centre."""
    market = load_market_config("pittsburgh-pa")
    elements = []
    n = 0
    for cell in market.cells:
        for _ in range(elements_per_cell):
            n += 1
            elements.append({"type": "node", "id": n, "lat": cell.center_lat,
                             "lon": cell.center_lng,
                             "tags": {"tourism": "hotel", "name": "Hotel %d" % n}})
    return OX.ExtractIndex(OX.index_document(
        extract_id="test-extract", source={"pbf": "x.osm.pbf"}, elements=elements))


class TestTheCommittedRegistry:
    def test_pennsylvania_covers_pittsburgh_and_names_its_provenance(self):
        registry = OX.ExtractRegistry.load()
        record = registry.for_market("pittsburgh-pa")
        assert record.extract_id == "geofabrik-pennsylvania"
        assert record.url.startswith("https://download.geofabrik.de/")
        assert record.md5_url == record.url + ".md5"
        assert record.local_pbf.startswith("data/osm_extracts/")
        assert record.index_path.startswith("data/osm_extracts/")
        assert "ODbL" in record.license
        with pytest.raises(KeyError):
            registry.for_market("nowhere-zz")

    @pytest.mark.parametrize("mutate", [
        lambda d: d.update(schema="other"),
        lambda d: d["extracts"][0].pop("url"),
        lambda d: d["extracts"][0].update(url="http://insecure/x.pbf"),
        lambda d: d["extracts"].append(dict(d["extracts"][0])),
    ])
    def test_a_malformed_registry_fails_closed(self, mutate):
        doc = registry_doc()
        mutate(doc)
        with pytest.raises(OX.ExtractError):
            OX.ExtractRegistry.from_document(doc)

    def test_the_default_index_tag_keys_leave_highway_out(self):
        assert "highway" not in OX.DEFAULT_INDEX_TAG_KEYS
        assert "tourism" in OX.DEFAULT_INDEX_TAG_KEYS


class TestReadiness:
    def test_nothing_on_disk_is_not_downloaded_and_names_the_operator_steps(self, tmp_path):
        registry = OX.ExtractRegistry.from_document(registry_doc())
        document = OX.readiness("pittsburgh-pa", registry=registry, repo_root=tmp_path)
        assert document["status"] == OX.NOT_DOWNLOADED
        assert document["pbf_present"] is False and document["index_present"] is False
        assert document["network_required"] is True
        steps = "\n".join(document["next_steps"])
        assert "https://example.invalid/x.osm.pbf" in steps
        assert "build-index --market pittsburgh-pa" in steps
        assert "dry-run --market pittsburgh-pa" in steps
        assert "--osm-extract-index data/osm_extracts/x.index.json" in steps
        assert "--max-overpass-requests 0" in steps

    def test_an_extract_on_disk_is_downloaded_and_an_index_is_indexed(self, tmp_path):
        registry = OX.ExtractRegistry.from_document(registry_doc())
        pbf = tmp_path / "data" / "osm_extracts" / "x.osm.pbf"
        pbf.parent.mkdir(parents=True)
        pbf.write_bytes(b"\x00" * 10)
        document = OX.readiness("pittsburgh-pa", registry=registry, repo_root=tmp_path)
        assert document["status"] == OX.DOWNLOADED and document["pbf_bytes"] == 10
        assert not any("download" in s for s in document["next_steps"])
        index = tmp_path / "data" / "osm_extracts" / "x.index.json"
        index.write_text(json.dumps(pittsburgh_index().to_document()), encoding="utf-8")
        document = OX.readiness("pittsburgh-pa", registry=registry, repo_root=tmp_path)
        assert document["status"] == OX.INDEXED
        assert document["index_element_count"] == 30
        assert document["network_required"] is False
        assert document["next_steps"][0].startswith("python scripts/pettripfinder/osm_extract_cli.py dry-run")

    def test_the_plan_command_prints_the_readiness_and_writes_it(self, tmp_path, capsys, monkeypatch):
        monkeypatch.setattr(OX, "REPO_ROOT", tmp_path)
        reg = tmp_path / "registry.json"
        reg.write_text(json.dumps(registry_doc()), encoding="utf-8")
        out = tmp_path / "plan.json"
        assert CLI.main(["plan", "--market", "pittsburgh-pa", "--registry", reg.as_posix(),
                         "--out", out.as_posix()]) == 0
        printed = capsys.readouterr().out
        assert "status                  : NOT_DOWNLOADED" in printed
        assert "network required        : yes" in printed
        assert json.loads(out.read_text(encoding="utf-8"))["schema"] == OX.READINESS_SCHEMA

    def test_the_plan_command_refuses_an_uncovered_market(self, tmp_path, capsys):
        reg = tmp_path / "registry.json"
        reg.write_text(json.dumps(registry_doc()), encoding="utf-8")
        assert CLI.main(["plan", "--market", "nowhere-zz", "--registry", reg.as_posix()]) == 2
        assert "no extract" in capsys.readouterr().out


class TestBuildIndexRefusesHonestly:
    def test_without_the_extract_it_names_the_plan(self, tmp_path, capsys, monkeypatch):
        monkeypatch.setattr(OX, "REPO_ROOT", tmp_path)
        reg = tmp_path / "registry.json"
        reg.write_text(json.dumps(registry_doc()), encoding="utf-8")
        assert CLI.main(["build-index", "--market", "pittsburgh-pa",
                         "--registry", reg.as_posix()]) == 2
        assert "no extract at" in capsys.readouterr().out

    def test_without_pyosmium_the_reducer_refuses_with_instructions(self, tmp_path, monkeypatch):
        import builtins
        real_import = builtins.__import__

        def no_osmium(name, *args, **kwargs):
            if name == "osmium":
                raise ImportError("no osmium")
            return real_import(name, *args, **kwargs)

        monkeypatch.setattr(builtins, "__import__", no_osmium)
        pbf = tmp_path / "x.osm.pbf"
        pbf.write_bytes(b"\x00")
        with pytest.raises(OX.ExtractError) as raised:
            OX.build_index_from_pbf(pbf, extract_id="x", out=tmp_path / "x.index.json")
        assert "pip install osmium" in str(raised.value)
        assert not OX.pyosmium_available()


class TestTheDryRun:
    def _cache_some(self, root, queries, n):
        cache = DiscoveryCache(root / C.CACHE_SUBDIR)
        for q in queries[:n]:
            identity = OV.cache_identity(q)
            cache.put(C.PROVIDER_OPENSTREETMAP, q.market_id, q.query_id,
                      compute_request_fingerprint(identity), 1, sanitized_request=identity,
                      payload={"elements": [{"type": "node", "id": 900 + n, "lat": 40.44,
                                             "lon": -80.0, "tags": {"tourism": "hotel"}}]},
                      status_metadata={"http_status": 200, "endpoint_id": "overpass-api.de",
                                       "endpoint_url": "https://overpass-api.de/api/interpreter",
                                       "query_version": OV.OVERPASS_QUERY_VERSION},
                      retrieved_at="2026-08-25")
        return cache

    def test_it_answers_the_uncached_pittsburgh_cells_and_leaves_the_cached_ones(self, tmp_path):
        market = load_market_config("pittsburgh-pa")
        queries = plan_queries(market, (C.PROVIDER_OPENSTREETMAP,),
                               (C.CATEGORY_HOTEL, C.CATEGORY_MOTEL))
        assert len(queries) == 30
        cache = self._cache_some(tmp_path, queries, 13)
        document = OX.answerability(pittsburgh_index(2), market=market, queries=queries,
                                    cache=cache, as_of="2026-08-26")
        assert (document["cells_total"], document["cells_cached"],
                document["cells_answerable"]) == (30, 13, 17)
        by_id = {row["query_id"]: row for row in document["cells"]}
        # Every hotel cell that is not cached gets its two elements; motel
        # cells are answerable and honestly EMPTY (the index holds no motel).
        hotel_answerable = [r for r in document["cells"] if r["disposition"] == "ANSWERABLE"
                            and r["category"] == C.CATEGORY_HOTEL]
        motel_answerable = [r for r in document["cells"] if r["disposition"] == "ANSWERABLE"
                            and r["category"] == C.CATEGORY_MOTEL]
        assert hotel_answerable and all(r["elements"] == 2 for r in hotel_answerable)
        assert motel_answerable and all(r["elements"] == 0 for r in motel_answerable)
        assert document["empty_answerable_cells"] == len(motel_answerable)
        assert by_id[queries[0].query_id]["disposition"] == "CACHED"

    def test_the_dry_run_command_reads_the_index_and_makes_no_request(self, tmp_path, capsys):
        index_path = tmp_path / "x.index.json"
        index_path.write_text(json.dumps(pittsburgh_index(1).to_document()), encoding="utf-8")
        out = tmp_path / "dry.json"
        assert CLI.main(["dry-run", "--market", "pittsburgh-pa", "--index", index_path.as_posix(),
                         "--output-root", (tmp_path / "root").as_posix(),
                         "--out", out.as_posix()]) == 0
        printed = capsys.readouterr().out
        assert "cells total/cached/ans. : 30 / 0 / 30" in printed
        assert "network requests        : 0" in printed
        assert json.loads(out.read_text(encoding="utf-8"))["cells_answerable"] == 30

    def test_a_local_extract_run_serves_cached_cells_and_answers_the_rest(self, tmp_path):
        # The end-to-end shape the fallback will run: 13 cells from the public
        # cache, 17 from the index, thirty COMPLETED, zero requests, the
        # cached 13 byte-identical.
        from scripts.pettripfinder.discovery import runner as RUNNER
        market = load_market_config("pittsburgh-pa")
        queries = plan_queries(market, (C.PROVIDER_OPENSTREETMAP,),
                               (C.CATEGORY_HOTEL, C.CATEGORY_MOTEL))
        cache = self._cache_some(tmp_path, queries, 13)
        before = {p: p.read_bytes() for p in (tmp_path / C.CACHE_SUBDIR).rglob("page_1.json")}
        assert len(before) == 13
        source = OX.LocalOsmExtractSource(pittsburgh_index(2))
        config = RUNNER.RunConfig(
            market_id="pittsburgh-pa", providers=(C.PROVIDER_OPENSTREETMAP,),
            categories=(C.CATEGORY_HOTEL, C.CATEGORY_MOTEL), output_root=str(tmp_path),
            observed_at="2026-08-26", max_overpass_requests=0, resume=True,
            osm_extract_index="(injected)")
        _m, _q, results, _c = RUNNER.execute_run(config, overpass_client=source, cache=cache)
        assert len(results) == 30
        assert all(r.state == C.QUERY_STATE_COMPLETED for r in results)
        assert sum(r.cache_hits for r in results) == 13
        assert sum(r.requests_made for r in results) == 0
        for path, content in before.items():
            assert path.read_bytes() == content
        stats = json.loads((tmp_path / "overpass_run_stats.json").read_text(encoding="utf-8"))
        assert stats["source"] == "local_extract"
        assert stats["current_endpoint_id"] == "local_extract:test-extract"
        # A local-extract run never touches the forward-progress gate.
        assert not (tmp_path / "discovery_progress.json").is_file()
