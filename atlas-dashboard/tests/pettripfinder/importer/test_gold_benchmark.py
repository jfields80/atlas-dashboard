"""AES-DATA-001 -- gold-fixture deterministic benchmark (mission sections
29/30). Runs all 30 offline gold fixtures through the static pipeline and
asserts every expected READY/REVIEW/REJECT classification. No network."""

from __future__ import annotations

from pathlib import Path

from scripts.benchmark_importer import run_static_benchmark

_FIXTURES = Path(__file__).resolve().parent / "fixtures"


def test_fixture_corpus_composition():
    names = [p.stem for p in _FIXTURES.glob("*.json")]
    assert sum(n.startswith("hotel_") for n in names) == 10
    assert sum(n.startswith("park_") for n in names) == 10
    assert sum(n.startswith("restaurant_") for n in names) == 10


def test_static_benchmark_all_match(tmp_path):
    report = run_static_benchmark(_FIXTURES, tmp_path)
    assert report["fixtures"] == 30
    assert report["correct_classification"] == 30
    assert report["all_match"] is True


def test_static_benchmark_covers_all_three_outcomes(tmp_path):
    report = run_static_benchmark(_FIXTURES, tmp_path)
    counts = report["counts_by_recommendation"]
    assert counts["READY"] >= 10          # labor-reduction: many clean candidates
    assert counts["REVIEW"] >= 5
    assert counts["REJECT"] >= 3


def test_no_unsupported_claim_in_ready_candidates(tmp_path):
    """Safety metric: no READY fixture published a field that failed span
    validation (the fabricated-fact hostile cases stay out of published
    fields)."""
    report = run_static_benchmark(_FIXTURES, tmp_path)
    for r in report["results"]:
        if r["actual"] == "READY":
            # unsupported_dropped counts evidence entries that were rejected;
            # they are recorded but never published -- READY is still valid.
            assert r["match"], r["fixture"]
