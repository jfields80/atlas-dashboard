"""AES-DATA-001 -- approval, staging export, and promotion (mission sections
20/21/22/23/28). No network, no LLM. Production seed CSV is never mutated by
approval; promotion is tested only against a temporary target."""

from __future__ import annotations

import csv
import hashlib
import json
from dataclasses import replace
from pathlib import Path

import pytest

from scripts.approve_import_candidate import approve_candidate
from scripts.import_official_url import _build_static, import_url
from scripts.promote_import_candidates import dry_run, promote
from scripts.pettripfinder.importer import constants as C
from scripts.pettripfinder.importer.candidate import (
    has_unsupported_published_claim,
    load_candidate,
)
from scripts.pettripfinder.importer.models import ImportContext

_FIXTURES = Path(__file__).resolve().parent / "fixtures"
_REPO = Path(__file__).resolve().parents[3]
_REAL_SEED = _REPO / "launch_packages" / "pettripfinder" / "seed_businesses.csv"


def _import(name, tmp_root):
    obj = json.loads((_FIXTURES / (name + ".json")).read_text(encoding="utf-8"))
    url = obj["url"]
    fetcher, extractor = _build_static(url, str(_FIXTURES / (name + ".json")))
    ctx = ImportContext(**obj.get("context", {}))
    return import_url(url, ctx, fetcher=fetcher, extractor=extractor,
                      output_root=str(tmp_root), observed_at="2026-07-16",
                      created_at="1970-01-01T00:00:00")


def _sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


class TestApproval:
    def test_approve_exports_to_staging(self, tmp_path):
        seed_before = _sha(_REAL_SEED)
        candidate, jp, _ = _import("hotel_01_strong", tmp_path)
        assert candidate.recommendation == C.RECOMMEND_READY
        res = approve_candidate(jp, "approve", output_root=str(tmp_path),
                                decided_at="2026-07-16T00:00:00")
        assert res["ok"] and res["review_status"] == C.REVIEW_EXPORTED_TO_STAGING
        staging = tmp_path / C.STAGING_CSV_NAME
        with staging.open(encoding="utf-8", newline="") as f:
            reader = csv.reader(f)
            header = next(reader)
            row = next(reader)
        assert header == list(C.SEED_CSV_COLUMNS)
        assert row[0] == "Drury Inn Columbus Polaris"
        # Candidate JSON updated; production seed CSV untouched.
        assert load_candidate(jp).review_status == C.REVIEW_EXPORTED_TO_STAGING
        assert (tmp_path / C.STAGING_AUDIT_NAME).exists()
        assert _sha(_REAL_SEED) == seed_before

    def test_reapprove_finalized_candidate_refused(self, tmp_path):
        # Item 11/25: a candidate already exported is never re-decided.
        _, jp, _ = _import("hotel_01_strong", tmp_path)
        approve_candidate(jp, "approve", output_root=str(tmp_path),
                          decided_at="2026-07-16T00:00:00")
        res2 = approve_candidate(jp, "approve", output_root=str(tmp_path),
                                 decided_at="2026-07-16T00:00:01")
        assert res2["ok"] is False and res2["reason"] == "already_finalized"

    def test_duplicate_inventory_row_refused(self, tmp_path):
        # A distinct candidate (different observed_at -> different id) with the
        # same (name, city, state) cannot be staged twice.
        _, jp1, _ = _import("hotel_01_strong", tmp_path)
        approve_candidate(jp1, "approve", output_root=str(tmp_path),
                          decided_at="2026-07-16T00:00:00")
        obj = json.loads((_FIXTURES / "hotel_01_strong.json").read_text(encoding="utf-8"))
        fetcher, extractor = _build_static(obj["url"], str(_FIXTURES / "hotel_01_strong.json"))
        c2, jp2, _ = import_url(obj["url"], ImportContext(**obj["context"]),
                                fetcher=fetcher, extractor=extractor,
                                output_root=str(tmp_path), observed_at="2026-07-17",
                                created_at="1970-01-01T00:00:00")
        res = approve_candidate(jp2, "approve", output_root=str(tmp_path),
                                decided_at="2026-07-17T00:00:00")
        assert res["ok"] is False and res["reason"] == C.REASON_DUPLICATE_INVENTORY_ROW

    def test_reject_recommendation_not_approvable(self, tmp_path):
        _, jp, _ = _import("restaurant_03_no_pets", tmp_path)
        res = approve_candidate(jp, "approve", output_root=str(tmp_path),
                                decided_at="2026-07-16T00:00:00")
        assert res["ok"] is False and res["reason"] == "candidate_recommendation_is_reject"

    def test_reject_decision_logs_rejection(self, tmp_path):
        _, jp, _ = _import("hotel_04_conflict", tmp_path)
        res = approve_candidate(jp, "reject", output_root=str(tmp_path),
                                operator_reason="looks wrong",
                                decided_at="2026-07-16T00:00:00")
        assert res["ok"] and res["review_status"] == C.REVIEW_REJECTED
        assert (tmp_path / C.REJECTIONS_NAME).exists()

    def test_missing_required_blocks_approval(self, tmp_path):
        _, jp, _ = _import("hotel_10_missing_address", tmp_path)
        res = approve_candidate(jp, "approve", output_root=str(tmp_path),
                                decided_at="2026-07-16T00:00:00")
        assert res["ok"] is False and res["reason"] == C.REASON_MISSING_REQUIRED_FIELD

    def test_approve_with_edits_records_diff(self, tmp_path):
        _, jp, _ = _import("hotel_10_missing_address", tmp_path)
        res = approve_candidate(jp, "approve-with-edits", output_root=str(tmp_path),
                                edits={"address": "500 Fixed St"},
                                decided_at="2026-07-16T00:00:00")
        assert res["ok"] and res["review_status"] == C.REVIEW_EXPORTED_TO_STAGING
        assert ("address", "", "500 Fixed St") in [tuple(e) for e in res["edits"]]
        reloaded = load_candidate(jp)
        assert dict(reloaded.proposed_fields)["address"] == "500 Fixed St"

    def test_unsupported_published_claim_detected(self, tmp_path):
        candidate, _jp, _ = _import("hotel_01_strong", tmp_path)
        bogus = replace(candidate, pet_facts=candidate.pet_facts + (("dog_menu", "true"),))
        assert has_unsupported_published_claim(bogus) is True
        assert has_unsupported_published_claim(candidate) is False


class TestPromotion:
    def _staging_with_row(self, tmp_path):
        _, jp, _ = _import("hotel_01_strong", tmp_path)
        approve_candidate(jp, "approve", output_root=str(tmp_path),
                          decided_at="2026-07-16T00:00:00")
        return tmp_path / C.STAGING_CSV_NAME

    def test_dry_run_reports_and_no_mutation(self, tmp_path):
        seed_before = _sha(_REAL_SEED)
        staging = self._staging_with_row(tmp_path)
        target = tmp_path / "target_seed.csv"
        target.write_bytes(_REAL_SEED.read_bytes())
        target_before = _sha(target)
        report = dry_run(staging, target, reference_date="2026-07-16")
        assert report["combined_build_ok"] is True
        assert report["existing_inventory_valid"] is True
        assert report["promotable_count"] == 1
        assert _sha(target) == target_before          # dry run never mutates
        assert _sha(_REAL_SEED) == seed_before

    def test_promote_requires_confirm(self, tmp_path):
        staging = self._staging_with_row(tmp_path)
        target = tmp_path / "target_seed.csv"
        target.write_bytes(_REAL_SEED.read_bytes())
        before = _sha(target)
        report = promote(staging, target, confirm=False, reference_date="2026-07-16")
        assert report["mode"] == "dry_run"
        assert report["confirmation_required"] == C.REASON_PROMOTION_CONFIRMATION_REQUIRED
        assert _sha(target) == before

    def test_promote_confirm_appends_atomically(self, tmp_path):
        staging = self._staging_with_row(tmp_path)
        target = tmp_path / "target_seed.csv"
        target.write_bytes(_REAL_SEED.read_bytes())
        rows_before = len(list(csv.DictReader(target.open(encoding="utf-8", newline=""))))
        report = promote(staging, target, confirm=True, reference_date="2026-07-16")
        assert report["mode"] == "promoted" and report["promoted_count"] == 1
        rows_after = len(list(csv.DictReader(target.open(encoding="utf-8", newline=""))))
        assert rows_after == rows_before + 1
        assert "Drury Inn Columbus Polaris" in report["promoted_names"]
        # Idempotent: a second promotion adds nothing (duplicate identity).
        report2 = promote(staging, target, confirm=True, reference_date="2026-07-16")
        assert report2["promoted_count"] == 0

    def test_real_seed_never_touched(self, tmp_path):
        # The whole promotion flow uses a temp target; the tracked seed is safe.
        before = _sha(_REAL_SEED)
        staging = self._staging_with_row(tmp_path)
        target = tmp_path / "target_seed.csv"
        target.write_bytes(_REAL_SEED.read_bytes())
        promote(staging, target, confirm=True, reference_date="2026-07-16")
        assert _sha(_REAL_SEED) == before
