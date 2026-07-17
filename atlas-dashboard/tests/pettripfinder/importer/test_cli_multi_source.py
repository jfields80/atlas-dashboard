"""AES-DATA-002C -- multi-source CLI (``scripts/import_official_urls.py``):
argument validation, static-fixture pairing, persistence, and the full
Land-Grant end-to-end scenario. No network calls; static mode only. The
existing single-source CLI (``scripts/import_official_url.py``) is never
imported or modified here."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.import_official_urls import _build_static_multi, import_urls, main
from scripts.pettripfinder.importer import constants as C
from scripts.pettripfinder.importer.candidate import candidate_from_dict, dumps_candidate
from scripts.pettripfinder.importer.models import ImportContext

_FIXTURES = Path(__file__).parent / "fixtures"
_FAQ_FIXTURE = _FIXTURES / "aggregate_landgrant_faq.json"
_CONTACT_FIXTURE = _FIXTURES / "aggregate_landgrant_contact.json"
_FAQ_URL = "https://landgrantbrewing.com/faq/"
_CONTACT_URL = "https://landgrantbrewing.com/contact/"


def _ctx() -> ImportContext:
    return ImportContext(
        category="restaurants", expected_city="Columbus", expected_state="OH",
        candidate_name="Land-Grant Brewing Columbus",
        source_relationship_hint="EXACT_ENTITY_DOMAIN")


class TestLandGrantEndToEnd:
    """Task 10: the full static two-source CLI run."""

    def test_persisted_ready_with_correct_attribution(self, tmp_path):
        fetcher, extractor = _build_static_multi(
            [_FAQ_URL, _CONTACT_URL], [str(_FAQ_FIXTURE), str(_CONTACT_FIXTURE)])
        candidate, json_path, report_path = import_urls(
            [_FAQ_URL, _CONTACT_URL], _ctx(), fetcher=fetcher, extractor=extractor,
            output_root=str(tmp_path / "out"), observed_at="2026-07-17",
            created_at="1970-01-01T00:00:00")

        assert candidate.recommendation == C.RECOMMEND_READY
        assert candidate.recommendation_reasons == ()
        assert not candidate.conflicts
        assert json_path.exists()
        assert report_path.exists()

        p = dict(candidate.proposed_fields)
        assert p["address"] == "424 W Town St"
        assert p["phone"] == "614-586-0413"
        assert dict(candidate.pet_facts)["pets_allowed"] == "true"

        # Approval command displayed correctly formed.
        report_html = report_path.read_text(encoding="utf-8")
        assert "approve_import_candidate.py" in report_html
        assert str(json_path) in report_html or json_path.name in report_html

        # Source attribution: address/phone from S2 (contact), pet policy S1.
        assert "[S2]" in report_html
        assert "[S1]" in report_html
        addr_ev = [e for e in candidate.evidence if e.field_name == "address"
                  and e.support_state != C.SUPPORT_UNSUPPORTED]
        assert addr_ev and all(e.source_url == _CONTACT_URL for e in addr_ev)
        policy_ev = [e for e in candidate.evidence if e.field_name == "patio_or_outdoor_only"]
        assert policy_ev and all(e.source_url == _FAQ_URL for e in policy_ev)

        # Aggregate JSON reloads exactly.
        reloaded = candidate_from_dict(json.loads(json_path.read_text(encoding="utf-8")))
        assert reloaded == candidate
        assert [s.source_id for s in reloaded.sources] == ["S1", "S2"]

    def test_deterministic_rerun_identical_bytes(self, tmp_path):
        """Repeated identical runs against the SAME output root deterministically
        overwrite the same candidate/report paths with identical bytes (Task 2)."""
        def _run():
            fetcher, extractor = _build_static_multi(
                [_FAQ_URL, _CONTACT_URL], [str(_FAQ_FIXTURE), str(_CONTACT_FIXTURE)])
            return import_urls(
                [_FAQ_URL, _CONTACT_URL], _ctx(), fetcher=fetcher, extractor=extractor,
                output_root=str(tmp_path / "out"), observed_at="2026-07-17",
                created_at="1970-01-01T00:00:00")

        c1, jp1, rp1 = _run()
        c2, jp2, rp2 = _run()
        assert jp1 == jp2 and rp1 == rp2      # same paths -- deterministic overwrite
        assert c1.candidate_id == c2.candidate_id
        assert dumps_candidate(c1) == dumps_candidate(c2)
        assert jp1.read_text(encoding="utf-8") == jp2.read_text(encoding="utf-8")
        assert rp1.read_text(encoding="utf-8") == rp2.read_text(encoding="utf-8")

    def test_different_output_roots_share_candidate_id_and_json(self, tmp_path):
        """The underlying candidate/JSON content is deterministic across
        DIFFERENT output roots too -- only the embedded report path (which
        legitimately differs by design) is root-specific."""
        def _run(out_root):
            fetcher, extractor = _build_static_multi(
                [_FAQ_URL, _CONTACT_URL], [str(_FAQ_FIXTURE), str(_CONTACT_FIXTURE)])
            return import_urls(
                [_FAQ_URL, _CONTACT_URL], _ctx(), fetcher=fetcher, extractor=extractor,
                output_root=str(out_root), observed_at="2026-07-17",
                created_at="1970-01-01T00:00:00")

        c1, _jp1, _rp1 = _run(tmp_path / "run1")
        c2, _jp2, _rp2 = _run(tmp_path / "run2")
        assert c1.candidate_id == c2.candidate_id
        assert dumps_candidate(c1) == dumps_candidate(c2)

    def test_cli_main_end_to_end(self, tmp_path):
        """Exercises the real argv-parsing entry point, not just import_urls."""
        out_root = tmp_path / "out"
        exit_code = main([
            "--url", _FAQ_URL, "--url", _CONTACT_URL,
            "--category", "restaurants",
            "--candidate-name", "Land-Grant Brewing Columbus",
            "--expected-city", "Columbus", "--expected-state", "OH",
            "--source-relationship", "EXACT_ENTITY_DOMAIN",
            "--extractor", "static",
            "--static-fixture", str(_FAQ_FIXTURE),
            "--static-fixture", str(_CONTACT_FIXTURE),
            "--observed-at", "2026-07-17", "--created-at", "1970-01-01T00:00:00",
            "--output-root", str(out_root),
        ])
        assert exit_code == 0
        candidates = list((out_root / "candidates").glob("*.json"))
        reports = list((out_root / "reports").glob("*.html"))
        assert len(candidates) == 1
        assert len(reports) == 1


class TestArgumentValidation:
    """Task 11 scenarios 8/9: invalid combinations fail before any fetch."""

    def test_five_urls_rejected_before_fetch(self, tmp_path):
        calls = {"n": 0}
        import scripts.import_official_urls as mod
        original = mod._build_static_multi
        mod._build_static_multi = lambda *a, **k: (_ for _ in ()).throw(
            AssertionError("must not build fetcher for invalid arg count"))
        try:
            exit_code = main([
                "--url", _FAQ_URL, "--url", _FAQ_URL, "--url", _FAQ_URL,
                "--url", _FAQ_URL, "--url", _FAQ_URL,
                "--category", "restaurants", "--extractor", "static",
                "--static-fixture", str(_FAQ_FIXTURE),
                "--static-fixture", str(_FAQ_FIXTURE),
                "--static-fixture", str(_FAQ_FIXTURE),
                "--static-fixture", str(_FAQ_FIXTURE),
                "--static-fixture", str(_FAQ_FIXTURE),
                "--output-root", str(tmp_path / "out"),
            ])
        finally:
            mod._build_static_multi = original
        assert exit_code != 0

    def test_zero_urls_rejected(self, tmp_path):
        exit_code = main(["--category", "restaurants", "--extractor", "static",
                          "--output-root", str(tmp_path / "out")])
        assert exit_code != 0

    def test_fixture_count_mismatch_rejected_before_fetch(self, tmp_path):
        calls = {"n": 0}
        import scripts.import_official_urls as mod
        original = mod._build_static_multi

        def _spy(*a, **k):
            calls["n"] += 1
            return original(*a, **k)
        mod._build_static_multi = _spy
        try:
            exit_code = main([
                "--url", _FAQ_URL, "--url", _CONTACT_URL,
                "--category", "restaurants", "--extractor", "static",
                "--static-fixture", str(_FAQ_FIXTURE),   # only 1 fixture for 2 urls
                "--output-root", str(tmp_path / "out"),
            ])
        finally:
            mod._build_static_multi = original
        assert exit_code != 0
        assert calls["n"] == 0

    def test_anthropic_mode_rejects_static_fixture(self, tmp_path):
        exit_code = main([
            "--url", _FAQ_URL, "--category", "restaurants",
            "--extractor", "anthropic", "--static-fixture", str(_FAQ_FIXTURE),
            "--output-root", str(tmp_path / "out"),
        ])
        assert exit_code != 0

    def test_static_missing_fixture_rejected(self, tmp_path):
        exit_code = main([
            "--url", _FAQ_URL, "--category", "restaurants", "--extractor", "static",
            "--output-root", str(tmp_path / "out"),
        ])
        assert exit_code != 0


class TestOneSourceViaNewCLI:
    """Task 11 scenario 7: a single --url through the aggregate CLI."""

    def test_single_url_matches_old_cli_semantics(self, tmp_path):
        from scripts.import_official_url import _build_static as old_build_static
        from scripts.pettripfinder.importer.candidate import run_import

        old_fetcher, old_extractor = old_build_static(_FAQ_URL, str(_FAQ_FIXTURE))
        old_candidate = run_import(
            _FAQ_URL, _ctx(), fetcher=old_fetcher, extractor=old_extractor,
            cas=__import__(
                "repositories.artifact_store_repository",
                fromlist=["ArtifactStoreRepository"]
            ).ArtifactStoreRepository(tmp_path / "old_cas"),
            observed_at="2026-07-17", created_at="1970-01-01T00:00:00")

        new_fetcher, new_extractor = _build_static_multi([_FAQ_URL], [str(_FAQ_FIXTURE)])
        new_candidate, _jp, _rp = import_urls(
            [_FAQ_URL], _ctx(), fetcher=new_fetcher, extractor=new_extractor,
            output_root=str(tmp_path / "new_out"), observed_at="2026-07-17",
            created_at="1970-01-01T00:00:00")

        assert new_candidate.recommendation == old_candidate.recommendation
        assert new_candidate.recommendation_reasons == old_candidate.recommendation_reasons
        assert dict(new_candidate.proposed_fields) == dict(old_candidate.proposed_fields)
        assert dict(new_candidate.pet_facts) == dict(old_candidate.pet_facts)
        # The aggregate doctrine still records exactly one SourceRecord.
        assert len(new_candidate.sources) == 1
        assert new_candidate.sources[0].role == C.SOURCE_ROLE_PRIMARY
        # The single-source CLI/module remain completely untouched.
        assert old_candidate.sources == ()
