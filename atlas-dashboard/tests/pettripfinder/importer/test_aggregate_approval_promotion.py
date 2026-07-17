"""AES-DATA-002C Task 8/9 -- approval and promotion compatibility: an
aggregate CandidateListing must flow through the EXISTING, unmodified
``approve_import_candidate.py`` and ``promote_import_candidates.py`` with
every guard intact. No production CSV is ever mutated by these tests --
promotion runs only against tmp_path copies. No network."""

from __future__ import annotations

import csv
import json
from dataclasses import replace
from datetime import date
from pathlib import Path

from pettripfinder.importer._aggregate_helpers import (
    CONTACT_URL,
    FAQ_URL,
    build_fetcher_extractor,
    contact_facts,
    contact_html,
    default_context,
    faq_facts,
    faq_html,
    make_cas,
)

from scripts.approve_import_candidate import approve_candidate
from scripts.pettripfinder.importer import constants as C
from scripts.pettripfinder.importer.aggregate import run_multi_import
from scripts.pettripfinder.importer.candidate import (
    candidate_from_dict,
    load_candidate,
    persist_candidate,
)
from scripts.promote_import_candidates import dry_run, promote

_FAQ_MARKER = "Beer Garden operations are weather dependent"
_CONTACT_MARKER = "Call the taproom at"

_REPO_ROOT = Path(__file__).resolve().parents[3]
_LAUNCH_DIR = _REPO_ROOT / "launch_packages" / "pettripfinder"
_REAL_SEED_CSV = _LAUNCH_DIR / "seed_businesses.csv"


def _ready_aggregate_candidate(tmp_path):
    fetcher, extractor = build_fetcher_extractor(
        [(FAQ_URL, faq_html()), (CONTACT_URL, contact_html())],
        {_FAQ_MARKER: faq_facts(), _CONTACT_MARKER: contact_facts()})
    return run_multi_import(
        [FAQ_URL, CONTACT_URL], default_context(), fetcher=fetcher, extractor=extractor,
        cas=make_cas(tmp_path), observed_at="2026-07-17", created_at="1970-01-01T00:00:00")


def _persist(c, tmp_path, name="run"):
    root = tmp_path / name
    path = persist_candidate(c, root / C.CANDIDATES_SUBDIR)
    return (root, path)


class TestApprovalCompatibility:
    def test_aggregate_candidate_loads_correctly(self, tmp_path):
        c = _ready_aggregate_candidate(tmp_path)
        _root, path = _persist(c, tmp_path)
        reloaded = load_candidate(path)
        assert reloaded == c
        assert len(reloaded.sources) == 2

    def test_approve_when_ready_writes_staging(self, tmp_path):
        c = _ready_aggregate_candidate(tmp_path)
        assert c.recommendation == C.RECOMMEND_READY
        root, path = _persist(c, tmp_path)
        result = approve_candidate(
            path, "approve", output_root=str(root), decided_at="2026-07-17T09:00:00")
        assert result["ok"] is True
        assert result["review_status"] == C.REVIEW_EXPORTED_TO_STAGING

        staging_csv = root / C.STAGING_CSV_NAME
        assert staging_csv.exists()
        with staging_csv.open(encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        assert len(rows) == 1
        assert set(rows[0].keys()) == set(C.SEED_CSV_COLUMNS)   # no aggregate metadata leaks
        assert rows[0]["name"] == "Land-Grant Brewing Columbus"
        assert rows[0]["address"] == "424 W Town St"

        audit_path = root / C.STAGING_AUDIT_NAME
        audit_records = [json.loads(l) for l in audit_path.read_text(encoding="utf-8").splitlines()]
        assert audit_records[0]["candidate_id"] == c.candidate_id

        # sources/aggregation_version preserved on the persisted, approved candidate.
        approved = load_candidate(root / C.CANDIDATES_SUBDIR / ("%s.json" % c.candidate_id))
        assert len(approved.sources) == 2
        assert approved.aggregation_version == C.AGGREGATION_VERSION
        assert approved.review_status == C.REVIEW_EXPORTED_TO_STAGING

    def test_missing_required_field_refuses_approval(self, tmp_path):
        """Only the FAQ page (no address/phone) -- an aggregate missing a
        required field must refuse approval exactly like a single source."""
        fetcher, extractor = build_fetcher_extractor(
            [(FAQ_URL, faq_html())], {_FAQ_MARKER: faq_facts()})
        c = run_multi_import(
            [FAQ_URL], default_context(), fetcher=fetcher, extractor=extractor,
            cas=make_cas(tmp_path), observed_at="2026-07-17", created_at="1970-01-01T00:00:00")
        assert "address" in c.missing_required
        root, path = _persist(c, tmp_path)
        result = approve_candidate(
            path, "approve", output_root=str(root), decided_at="2026-07-17T09:00:00")
        assert result["ok"] is False
        assert result["reason"] == C.REASON_MISSING_REQUIRED_FIELD
        assert "address" in result["missing"]

    def test_unsupported_published_claim_refuses_approval(self, tmp_path):
        c = _ready_aggregate_candidate(tmp_path)
        # Force a published pet fact with no SUPPORTED/AMBIGUOUS evidence.
        tampered = replace(c, pet_facts=c.pet_facts + (("dog_menu", "true"),))
        root, path = _persist(tampered, tmp_path)
        result = approve_candidate(
            path, "approve", output_root=str(root), decided_at="2026-07-17T09:00:00")
        assert result["ok"] is False
        assert result["reason"] == "unsupported_material_claim_remains"

    def test_approve_with_edits_keeps_aggregate_shape(self, tmp_path):
        """apply_operator_edits (AES-DATA-002A) preserves sources/
        aggregation_version -- proven end-to-end through the real approval
        CLI function, not just the unit-level construction."""
        c = _ready_aggregate_candidate(tmp_path)
        root, path = _persist(c, tmp_path)
        result = approve_candidate(
            path, "approve-with-edits", output_root=str(root),
            edits={"rating": "4.5"}, decided_at="2026-07-17T09:00:00")
        assert result["ok"] is True
        approved = load_candidate(root / C.CANDIDATES_SUBDIR / ("%s.json" % c.candidate_id))
        assert len(approved.sources) == 2
        assert approved.aggregation_version == C.AGGREGATION_VERSION
        assert dict(approved.proposed_fields)["rating"] == "4.5"


class TestPromotionCompatibility:
    def test_dry_run_validates_through_existing_builder_no_mutation(self, tmp_path):
        c = _ready_aggregate_candidate(tmp_path)
        root, path = _persist(c, tmp_path)
        approve_candidate(path, "approve", output_root=str(root), decided_at="2026-07-17T09:00:00")

        target_csv = tmp_path / "target_seed.csv"
        target_csv.write_text(
            ",".join(C.SEED_CSV_COLUMNS) + "\n", encoding="utf-8", newline="\n")
        before = target_csv.read_text(encoding="utf-8")

        report = dry_run(
            str(root / C.STAGING_CSV_NAME), str(target_csv),
            launch_dir=_LAUNCH_DIR, reference_date="2026-07-17")
        assert report["combined_build_ok"] is True
        assert report["promotable_count"] == 1
        assert report["per_staging_row"][0]["promotable"] is True
        after = target_csv.read_text(encoding="utf-8")
        assert before == after   # dry run never mutates

    def test_confirm_promotes_row_based_no_aggregate_metadata_leak(self, tmp_path):
        c = _ready_aggregate_candidate(tmp_path)
        root, path = _persist(c, tmp_path)
        approve_candidate(path, "approve", output_root=str(root), decided_at="2026-07-17T09:00:00")

        target_csv = tmp_path / "target_seed.csv"
        target_csv.write_text(
            ",".join(C.SEED_CSV_COLUMNS) + "\n", encoding="utf-8", newline="\n")

        result = promote(
            str(root / C.STAGING_CSV_NAME), str(target_csv), confirm=True,
            launch_dir=_LAUNCH_DIR, reference_date="2026-07-17")
        assert result["mode"] == "promoted"
        assert result["promoted_count"] == 1
        assert result["promoted_names"] == ["Land-Grant Brewing Columbus"]

        with target_csv.open(encoding="utf-8") as f:
            rows = list(csv.DictReader(f))
        assert len(rows) == 1
        assert set(rows[0].keys()) == set(C.SEED_CSV_COLUMNS)
        assert "sources" not in rows[0] and "aggregation_version" not in rows[0]

    def test_real_production_csv_never_touched(self, tmp_path):
        """The real repository seed CSV is read (for realistic dedup context)
        but never written to -- promotion always targets an explicit
        --target path, and this test never passes the real one as --target."""
        assert _REAL_SEED_CSV.exists()
        before = _REAL_SEED_CSV.read_bytes()

        c = _ready_aggregate_candidate(tmp_path)
        root, path = _persist(c, tmp_path)
        approve_candidate(path, "approve", output_root=str(root), decided_at="2026-07-17T09:00:00")
        target_csv = tmp_path / "target_seed.csv"
        target_csv.write_bytes(_REAL_SEED_CSV.read_bytes())  # start from a COPY

        promote(
            str(root / C.STAGING_CSV_NAME), str(target_csv), confirm=True,
            launch_dir=_LAUNCH_DIR, reference_date="2026-07-17")

        after = _REAL_SEED_CSV.read_bytes()
        assert before == after
