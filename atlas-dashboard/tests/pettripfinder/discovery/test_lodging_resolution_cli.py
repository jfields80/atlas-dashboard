"""AES-DATA-004C -- lodging resolution CLI tests. No network; synthetic
input root, never the real Wave 1 output, keeps this hermetic and fast."""

from __future__ import annotations

import json

from scripts.pettripfinder.discovery import constants as C
from scripts.pettripfinder.discovery.deduplicate import deduplicate
from scripts.pettripfinder.discovery.models import DiscoveryRecord
from scripts.pettripfinder.discovery.normalize import normalize_records
from scripts.pettripfinder.discovery.serialization import dumps_candidates
from scripts.pettripfinder import lodging_resolution_cli as cli


def _make_input_root(tmp_path):
    hotel_records = [
        DiscoveryRecord(provider=C.PROVIDER_GOOGLE_PLACES, provider_record_id="h1",
                        canonical_category=C.CATEGORY_HOTEL, name="Test Hotel Downtown",
                        address_line="1 Main St", city="Columbus", state="OH", postal_code="43215",
                        website_url="https://example-hotel.com/property"),
        DiscoveryRecord(provider=C.PROVIDER_GOOGLE_PLACES, provider_record_id="h2",
                        canonical_category=C.CATEGORY_HOTEL, name="No Site Inn",
                        address_line="2 Main St", city="Columbus", state="OH", postal_code="43215"),
    ]
    motel_records = [
        DiscoveryRecord(provider=C.PROVIDER_GOOGLE_PLACES, provider_record_id="m1",
                        canonical_category=C.CATEGORY_MOTEL, name="Test Motel West",
                        address_line="3 West St", city="Dublin", state="OH", postal_code="43017",
                        website_url="https://example-motel.com/property"),
    ]
    hotel_candidates = deduplicate(normalize_records(tuple(hotel_records)), market_id="columbus-oh")
    motel_candidates = deduplicate(normalize_records(tuple(motel_records)), market_id="columbus-oh")

    input_root = tmp_path / "input"
    (input_root / "hotel" / "candidates").mkdir(parents=True)
    (input_root / "motel" / "candidates").mkdir(parents=True)
    (input_root / "hotel" / "candidates" / "columbus-oh_candidates.json").write_text(
        dumps_candidates(hotel_candidates), encoding="utf-8")
    (input_root / "motel" / "candidates" / "columbus-oh_candidates.json").write_text(
        dumps_candidates(motel_candidates), encoding="utf-8")
    return input_root


def test_plan_makes_no_output_and_no_network(tmp_path, capsys):
    input_root = _make_input_root(tmp_path)
    output_root = tmp_path / "resolution"
    rc = cli.main(["plan", "--input-root", str(input_root), "--output-root", str(output_root),
                  "--max-http-requests", "40"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "total candidates" in out
    assert "Google Places calls             : 0" in out
    assert not output_root.exists()


def test_run_with_zero_cap_is_fully_static(tmp_path, capsys):
    input_root = _make_input_root(tmp_path)
    output_root = tmp_path / "resolution"
    rc = cli.main(["run", "--input-root", str(input_root), "--output-root", str(output_root),
                  "--observed-at", "2026-07-18"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "HTTP requests (actual)   : 0" in out
    assert (output_root / "resolved_candidates.json").exists()
    assert (output_root / "batch_index.json").exists()


def test_run_generates_schema_valid_batches(tmp_path):
    from scripts.pettripfinder.importer.batch import load_manifest, validate_manifest
    input_root = _make_input_root(tmp_path)
    output_root = tmp_path / "resolution"
    cli.main(["run", "--input-root", str(input_root), "--output-root", str(output_root),
             "--observed-at", "2026-07-18"])
    batch_dir = output_root / "import_batches"
    manifests = list(batch_dir.glob("*.json"))
    assert len(manifests) >= 1
    for path in manifests:
        manifest = load_manifest(str(path))
        errors = validate_manifest(manifest, extractor="anthropic", repo_root=".")
        assert errors == ()


def test_report_regenerates_without_network(tmp_path):
    input_root = _make_input_root(tmp_path)
    output_root = tmp_path / "resolution"
    cli.main(["run", "--input-root", str(input_root), "--output-root", str(output_root),
             "--observed-at", "2026-07-18"])
    rc = cli.main(["report", "--output-root", str(output_root), "--observed-at", "2026-07-18"])
    assert rc == 0
    assert (output_root / "website_resolution_report.html").exists()


def test_report_missing_run_returns_error(tmp_path):
    rc = cli.main(["report", "--output-root", str(tmp_path / "never-ran")])
    assert rc == 2


def test_no_website_candidate_never_discarded(tmp_path):
    input_root = _make_input_root(tmp_path)
    output_root = tmp_path / "resolution"
    cli.main(["run", "--input-root", str(input_root), "--output-root", str(output_root),
             "--observed-at", "2026-07-18"])
    data = json.loads((output_root / "resolved_candidates.json").read_text(encoding="utf-8"))
    names = {d["name"] for d in data}
    assert "No Site Inn" in names


def test_excluded_and_unresolved_queues_written(tmp_path):
    input_root = _make_input_root(tmp_path)
    output_root = tmp_path / "resolution"
    cli.main(["run", "--input-root", str(input_root), "--output-root", str(output_root),
             "--observed-at", "2026-07-18"])
    assert (output_root / "unresolved_queue.json").exists()
    assert (output_root / "excluded_candidates.json").exists()


def test_output_confined_to_output_root(tmp_path):
    input_root = _make_input_root(tmp_path)
    output_root = tmp_path / "sub" / "resolution"
    cli.main(["run", "--input-root", str(input_root), "--output-root", str(output_root),
             "--observed-at", "2026-07-18"])
    # only the sub/ directory tree was created under tmp_path, plus "input"
    created = {p.name for p in tmp_path.iterdir()}
    assert created == {"input", "sub"}


def test_missing_input_root_produces_empty_but_valid_run(tmp_path, capsys):
    output_root = tmp_path / "resolution"
    rc = cli.main(["run", "--input-root", str(tmp_path / "nonexistent"),
                  "--output-root", str(output_root), "--observed-at", "2026-07-18"])
    assert rc == 0
    out = capsys.readouterr().out
    assert "resolved candidates      : 0" in out
