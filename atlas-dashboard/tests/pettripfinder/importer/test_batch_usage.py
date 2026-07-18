"""AES-WORK-001C -- optional provider usage capture: real Anthropic
message.usage capture (mocked SDK response, no network/API key), static
mode always zero, usage propagation ExtractionResult -> SourceImportResult
-> CandidateListing -> JobState -> batch summary totals, legacy WORK-001B
state.json compatibility, and the deliberate USD-cost deferral (Task 9)."""

from __future__ import annotations

from dataclasses import replace
from pathlib import Path

import pytest

from scripts.pettripfinder.importer import constants as C
from scripts.pettripfinder.importer.batch import (
    JOB_DONE,
    BatchJob,
    BatchManifest,
    BatchState,
    JobState,
    batch_state_from_dict,
    build_batch_summary,
    load_batch_state,
    run_batch,
    write_batch_state,
)
from scripts.pettripfinder.importer.batch_report import build_batch_report_html
from scripts.pettripfinder.importer.candidate import run_import
from scripts.pettripfinder.importer.category_templates import allowed_fields
from scripts.pettripfinder.importer.extraction import parse_extraction_payload
from scripts.pettripfinder.importer.extraction_anthropic import AnthropicFactExtractor
from scripts.pettripfinder.importer.fetch import StaticPageFetcher
from scripts.pettripfinder.importer.models import ImportContext

_REPO_ROOT = Path(__file__).resolve().parents[3]
_HOTEL_FIXTURE = "tests/pettripfinder/importer/fixtures/hotel_01_strong.json"
_FAQ_URL = "https://landgrantbrewing.com/faq/"
_CONTACT_URL = "https://landgrantbrewing.com/taproom/"
_FAQ_FIXTURE = "tests/pettripfinder/importer/fixtures/aggregate_landgrant_faq.json"
_CONTACT_FIXTURE = "tests/pettripfinder/importer/fixtures/aggregate_landgrant_contact.json"
_GOOD = '{"facts": [{"field": "pets_allowed", "value": "true", "quote": "Dogs welcome"}]}'
_BAD = "sorry, I cannot comply"


# --------------------------------------------------------------------------- #
# Anthropic real usage capture -- mocked SDK response shape only, no network.
# --------------------------------------------------------------------------- #

class _Usage:
    def __init__(self, input_tokens, output_tokens):
        self.input_tokens = input_tokens
        self.output_tokens = output_tokens


class _Block:
    def __init__(self, text):
        self.text = text


class _Message:
    def __init__(self, text, usage=None):
        self.content = [_Block(text)]
        self.usage = usage


class _Messages:
    def __init__(self, responses):
        self._responses = list(responses)
        self._i = 0

    def create(self, **kw):
        text, usage = self._responses[self._i]
        self._i += 1
        return _Message(text, usage)


class _Client:
    def __init__(self, responses):
        self.messages = _Messages(responses)


class _RealCallAnthropic(AnthropicFactExtractor):
    """Exercises the REAL (non-overridden) _call_once, unlike
    test_anthropic_provider.py's _FakeAnthropic -- only _client() is
    injected, so the real usage-capture side channel actually runs."""

    def __init__(self, responses, **kw):
        super().__init__(**kw)
        self._fake_client = _Client(responses)

    def _client(self):
        return self._fake_client


class TestAnthropicUsageCapture:
    def test_first_call_good_captures_real_usage(self):
        ext = _RealCallAnthropic([(_GOOD, _Usage(100, 20))], model="m")
        res = ext.extract("t", "hotels", allowed_fields("hotels"))
        assert res.ok and res.retries == 0
        assert res.input_tokens == 100
        assert res.output_tokens == 20
        assert res.provider_request_count == 1

    def test_malformed_then_good_retry_aggregates_usage_from_both_calls(self):
        ext = _RealCallAnthropic(
            [(_BAD, _Usage(50, 10)), (_GOOD, _Usage(80, 15))], model="m")
        res = ext.extract("t", "hotels", allowed_fields("hotels"))
        assert res.ok and res.retries == 1
        assert res.input_tokens == 50 + 80
        assert res.output_tokens == 10 + 15
        assert res.provider_request_count == 2

    def test_two_malformed_still_aggregates_real_usage_from_both_calls(self):
        ext = _RealCallAnthropic(
            [(_BAD, _Usage(50, 10)), (_BAD, _Usage(60, 12))], model="m")
        res = ext.extract("t", "hotels", allowed_fields("hotels"))
        assert res.ok is False
        assert res.error == C.REASON_EXTRACTION_UNPARSEABLE
        assert res.input_tokens == 50 + 60
        assert res.output_tokens == 10 + 12
        assert res.provider_request_count == 2

    def test_missing_usage_attribute_degrades_to_zero_without_failing(self):
        ext = _RealCallAnthropic([(_GOOD, None)], model="m")
        res = ext.extract("t", "hotels", allowed_fields("hotels"))
        assert res.ok is True   # extraction itself never fails from this
        assert res.input_tokens == 0
        assert res.output_tokens == 0
        assert res.provider_request_count == 1

    def test_malformed_usage_object_degrades_to_zero_without_failing(self):
        class _BrokenUsage:
            input_tokens = "not-a-number"
            output_tokens = object()

        ext = _RealCallAnthropic([(_GOOD, _BrokenUsage())], model="m")
        res = ext.extract("t", "hotels", allowed_fields("hotels"))
        assert res.ok is True
        assert res.input_tokens == 0
        assert res.output_tokens == 0

    def test_call_once_signature_unchanged_existing_fake_override_still_works(self):
        """Guards the seam existing tests rely on: _call_once still
        returns a plain str, so test_anthropic_provider.py's _FakeAnthropic
        override (which returns canned strings) needs zero changes."""
        class _FakeAnthropic(AnthropicFactExtractor):
            def __init__(self, responses, **kw):
                super().__init__(**kw)
                self._responses = list(responses)
                self._i = 0

            def _client(self):
                return object()

            def _call_once(self, client, system, user):
                r = self._responses[self._i]
                self._i += 1
                return r

        ext = _FakeAnthropic([_GOOD], model="m")
        res = ext.extract("t", "hotels", allowed_fields("hotels"))
        assert res.ok
        assert res.input_tokens == 0   # _last_usage never set by the override
        assert res.provider_request_count == 1


# --------------------------------------------------------------------------- #
# Static extractor: always zero (models.py defaults do the work).
# --------------------------------------------------------------------------- #

class TestStaticUsageZero:
    def test_static_single_source_candidate_has_zero_usage(self, tmp_path):
        from scripts.import_official_url import _build_static
        fetcher, extractor = _build_static(
            "https://www.druryhotels.test/polaris", str(_REPO_ROOT / _HOTEL_FIXTURE))
        ctx = ImportContext(category="hotels", candidate_name="Drury",
                            expected_city="Columbus", expected_state="OH")
        from repositories.artifact_store_repository import ArtifactStoreRepository
        cas = ArtifactStoreRepository(tmp_path / "cas")
        candidate = run_import(
            "https://www.druryhotels.test/polaris", ctx, fetcher=fetcher, extractor=extractor,
            cas=cas, observed_at="2026-07-18", created_at="2026-07-18T00:00:00+00:00")
        assert candidate.input_tokens == 0
        assert candidate.output_tokens == 0
        assert candidate.provider_request_count == 0


# --------------------------------------------------------------------------- #
# Usage propagation: ExtractionResult -> SourceImportResult -> CandidateListing.
# --------------------------------------------------------------------------- #

class _UsageStaticExtractor:
    """Like StaticFactExtractor, but attaches KNOWN usage figures to the
    ExtractionResult -- lets a test inject exact, known usage through the
    REAL import_source/run_import/run_multi_import pipeline without a live
    Anthropic call."""

    def __init__(self, payload, input_tokens, output_tokens, provider_request_count):
        self._payload = payload
        self._input_tokens = input_tokens
        self._output_tokens = output_tokens
        self._provider_request_count = provider_request_count

    def extract(self, normalized_text, category, allowed_fields):
        payload = self._payload
        if callable(payload):
            payload = payload(normalized_text, category, allowed_fields)
        result = parse_extraction_payload(payload, allowed_fields, "anthropic", "claude-test")
        return replace(
            result, input_tokens=self._input_tokens, output_tokens=self._output_tokens,
            provider_request_count=self._provider_request_count)


class TestUsagePropagationThroughCandidate:
    def test_single_source_candidate_carries_injected_usage(self, tmp_path):
        fetcher = StaticPageFetcher()
        import json
        data = json.loads((_REPO_ROOT / _HOTEL_FIXTURE).read_text(encoding="utf-8"))
        fetcher.add_html("https://www.druryhotels.test/polaris", data["html"])
        extractor = _UsageStaticExtractor(data["extraction"], 111, 22, 1)
        ctx = ImportContext(category="hotels", candidate_name="Drury",
                            expected_city="Columbus", expected_state="OH")
        from repositories.artifact_store_repository import ArtifactStoreRepository
        cas = ArtifactStoreRepository(tmp_path / "cas")
        candidate = run_import(
            "https://www.druryhotels.test/polaris", ctx, fetcher=fetcher, extractor=extractor,
            cas=cas, observed_at="2026-07-18", created_at="2026-07-18T00:00:00+00:00")
        assert candidate.input_tokens == 111
        assert candidate.output_tokens == 22
        assert candidate.provider_request_count == 1

    def test_multi_source_candidate_sums_usage_across_sources(self, tmp_path):
        import json
        from scripts.pettripfinder.importer.aggregate import run_multi_import

        fetcher = StaticPageFetcher()
        faq_data = json.loads((_REPO_ROOT / _FAQ_FIXTURE).read_text(encoding="utf-8"))
        contact_data = json.loads((_REPO_ROOT / _CONTACT_FIXTURE).read_text(encoding="utf-8"))
        fetcher.add_html(_FAQ_URL, faq_data["html"])
        fetcher.add_html(_CONTACT_URL, contact_data["html"])

        text_to_facts = {}
        from scripts.pettripfinder.importer.source_snapshot import normalize_html_to_text
        norm_faq, _ = normalize_html_to_text(faq_data["html"])
        norm_contact, _ = normalize_html_to_text(contact_data["html"])
        text_to_facts[norm_faq] = faq_data["extraction"]
        text_to_facts[norm_contact] = contact_data["extraction"]

        # Each source reports DIFFERENT usage; the aggregate must sum both.
        usage_by_text = {norm_faq: (10, 2, 1), norm_contact: (30, 6, 1)}

        def _payload(normalized_text, _category, _allowed):
            return text_to_facts.get(normalized_text, {"facts": []})

        class _MultiUsageExtractor:
            def extract(self, normalized_text, category, allowed_fields):
                result = parse_extraction_payload(
                    _payload(normalized_text, category, allowed_fields),
                    allowed_fields, "anthropic", "claude-test")
                in_tok, out_tok, count = usage_by_text.get(normalized_text, (0, 0, 0))
                return replace(result, input_tokens=in_tok, output_tokens=out_tok,
                              provider_request_count=count)

        ctx = ImportContext(category="restaurants", candidate_name="Land-Grant Brewing Columbus",
                            expected_city="Columbus", expected_state="OH",
                            source_relationship_hint="EXACT_ENTITY_DOMAIN")
        from repositories.artifact_store_repository import ArtifactStoreRepository
        cas = ArtifactStoreRepository(tmp_path / "cas")
        candidate = run_multi_import(
            [_FAQ_URL, _CONTACT_URL], ctx, fetcher=fetcher, extractor=_MultiUsageExtractor(),
            cas=cas, observed_at="2026-07-18", created_at="2026-07-18T00:00:00+00:00")
        assert candidate.input_tokens == 40
        assert candidate.output_tokens == 8
        assert candidate.provider_request_count == 2


# --------------------------------------------------------------------------- #
# Usage totals aggregate correctly across jobs in the batch summary.
# --------------------------------------------------------------------------- #

class TestBatchSummaryUsageTotals:
    def test_summary_usage_sums_across_all_jobs(self):
        manifest = BatchManifest(
            manifest_schema_version=C.BATCH_MANIFEST_SCHEMA_VERSION, batch_id="usage-totals",
            batch_name="t", defaults={}, jobs=(
                BatchJob(job_id="a", candidate_name="A", category="hotels",
                        expected_city="c", expected_state="OH", urls=("https://a.test",)),
                BatchJob(job_id="b", candidate_name="B", category="hotels",
                        expected_city="c", expected_state="OH", urls=("https://b.test",)),
            ))
        state = BatchState(
            batch_state_version=C.BATCH_STATE_VERSION, batch_id="usage-totals",
            manifest_hash="x", manifest_schema_version="1.0", extractor="anthropic",
            model="m", observed_at="2026-07-18", jobs=(
                JobState(job_id="a", fingerprint="fpa", execution_state=JOB_DONE,
                        provider_request_count=1, input_tokens=100, output_tokens=20),
                JobState(job_id="b", fingerprint="fpb", execution_state=JOB_DONE,
                        provider_request_count=2, input_tokens=250, output_tokens=45),
            ))
        summary = build_batch_summary(state, manifest)
        assert summary["usage"] == {
            "provider_request_count": 3, "input_tokens": 350, "output_tokens": 65,
        }
        assert summary["jobs"][0]["usage"]["input_tokens"] == 100
        assert summary["jobs"][1]["usage"]["provider_request_count"] == 2


# --------------------------------------------------------------------------- #
# Task 9: USD cost estimation is deliberately deferred this phase -- never
# emitted, tokens only.
# --------------------------------------------------------------------------- #

class TestUsdCostDeferred:
    def test_no_estimated_cost_populated_by_a_real_batch_run(self, tmp_path):
        manifest = BatchManifest(
            manifest_schema_version=C.BATCH_MANIFEST_SCHEMA_VERSION, batch_id="no-cost-test",
            batch_name="t", defaults={}, jobs=(
                BatchJob(job_id="a", candidate_name="Drury", category="hotels",
                        expected_city="Columbus", expected_state="OH",
                        urls=("https://www.druryhotels.test/polaris",),
                        static_fixtures=(_HOTEL_FIXTURE,)),
            ))
        state = run_batch(
            manifest, extractor_mode="static", model=C.DEFAULT_ANTHROPIC_MODEL,
            output_root=str(tmp_path), observed_at="2026-07-18", repo_root=_REPO_ROOT,
            clock=lambda: "2026-07-18T00:00:00+00:00")
        assert state.jobs[0].estimated_cost_usd == ""
        assert state.jobs[0].pricing_version == ""
        summary = build_batch_summary(state, manifest)
        assert "estimated_cost_usd" not in summary["usage"]
        assert summary["jobs"][0]["usage"]["estimated_cost_usd"] == ""


# --------------------------------------------------------------------------- #
# Legacy WORK-001B state.json (no usage fields at all) must still load,
# resume, and render.
# --------------------------------------------------------------------------- #

def _legacy_job_dict(job_id: str) -> dict:
    """The exact WORK-001B JobState JSON shape -- no usage/cost keys."""
    return {
        "job_id": job_id, "fingerprint": "legacy-fp-%s" % job_id,
        "execution_state": JOB_DONE, "last_action": "ran",
        "recommendation": C.RECOMMEND_READY, "recommendation_reasons": [],
        "candidate_id": "cand-%s" % job_id, "candidate_path": "", "report_path": "",
        "run_id": "2026-01-01T00:00:00+00:00", "skip_reason": "", "error_type": "",
        "error_message": "", "source_outcomes": [], "snapshot_hashes": [],
        "provider": "static", "model": "static-fixture", "prompt_version": "1.0.0",
    }


class TestLegacyStateCompatibility:
    def test_legacy_job_dict_loads_with_zero_usage_defaults(self):
        legacy = {
            "batch_state_version": C.BATCH_STATE_VERSION, "batch_id": "legacy-batch",
            "manifest_hash": "x", "manifest_schema_version": "1.0", "extractor": "static",
            "model": "m", "observed_at": "2026-01-01",
            "jobs": [_legacy_job_dict("a"), _legacy_job_dict("b")],
        }
        state = batch_state_from_dict(legacy)
        for js in state.jobs:
            assert js.provider_request_count == 0
            assert js.input_tokens == 0
            assert js.output_tokens == 0
            assert js.estimated_cost_usd == ""
            assert js.pricing_version == ""

    def test_legacy_state_file_on_disk_resumes_successfully(self, tmp_path):
        manifest = BatchManifest(
            manifest_schema_version=C.BATCH_MANIFEST_SCHEMA_VERSION, batch_id="legacy-resume",
            batch_name="t", defaults={}, jobs=(
                BatchJob(job_id="drury", candidate_name="Drury Inn & Suites Columbus Dublin",
                        category="hotels", expected_city="Columbus", expected_state="OH",
                        urls=("https://www.druryhotels.test/polaris",),
                        static_fixtures=(_HOTEL_FIXTURE,)),
            ))
        # Persist a real DONE run first to get real, valid candidate/report
        # paths and a real fingerprint...
        real_state = run_batch(
            manifest, extractor_mode="static", model=C.DEFAULT_ANTHROPIC_MODEL,
            output_root=str(tmp_path), observed_at="2026-07-18", repo_root=_REPO_ROOT,
            clock=lambda: "2026-07-18T00:00:00+00:00")
        # ...then rewrite state.json in the EXACT legacy (no usage keys)
        # shape, using those real paths/fingerprint, simulating a state
        # file written before WORK-001C existed.
        real_js = real_state.jobs[0]
        legacy_job = _legacy_job_dict("drury")
        legacy_job.update({
            "fingerprint": real_js.fingerprint, "candidate_path": real_js.candidate_path,
            "report_path": real_js.report_path, "candidate_id": real_js.candidate_id,
        })
        legacy_state_dict = {
            "batch_state_version": C.BATCH_STATE_VERSION, "batch_id": "legacy-resume",
            "manifest_hash": "irrelevant-for-this-check", "manifest_schema_version": "1.0",
            "extractor": "static", "model": C.DEFAULT_ANTHROPIC_MODEL, "observed_at": "2026-07-18",
            "jobs": [legacy_job],
        }
        state_path = tmp_path / C.BATCHES_SUBDIR / "legacy-resume" / "state.json"
        import json
        state_path.write_text(json.dumps(legacy_state_dict, indent=2), encoding="utf-8")

        resumed = run_batch(
            manifest, extractor_mode="static", model=C.DEFAULT_ANTHROPIC_MODEL,
            output_root=str(tmp_path), observed_at="2026-07-18", repo_root=_REPO_ROOT,
            resume=True, clock=lambda: "2026-07-18T00:00:00+00:00")
        assert resumed.jobs[0].execution_state == JOB_DONE
        assert resumed.jobs[0].last_action == "reused"
        assert resumed.jobs[0].provider_request_count == 0   # legacy default, not migrated

    def test_report_renders_legacy_zero_usage_state_without_error(self, tmp_path):
        manifest = BatchManifest(
            manifest_schema_version=C.BATCH_MANIFEST_SCHEMA_VERSION, batch_id="legacy-report",
            batch_name="t", defaults={}, jobs=(
                BatchJob(job_id="a", candidate_name="A", category="hotels",
                        expected_city="c", expected_state="OH", urls=("https://a.test",)),
            ))
        legacy = {
            "batch_state_version": C.BATCH_STATE_VERSION, "batch_id": "legacy-report",
            "manifest_hash": "x", "manifest_schema_version": "1.0", "extractor": "static",
            "model": "m", "observed_at": "2026-01-01", "jobs": [_legacy_job_dict("a")],
        }
        state = batch_state_from_dict(legacy)
        html = build_batch_report_html(state, manifest, tmp_path)   # must not raise
        assert "READY" in html
        # The batch-level header always shows a "provider requests: 0"
        # summary line, but the PER-JOB usage row (only added when a job
        # has non-zero usage) must be omitted entirely for an all-zero
        # legacy job.
        assert "provider request(s)" not in html
