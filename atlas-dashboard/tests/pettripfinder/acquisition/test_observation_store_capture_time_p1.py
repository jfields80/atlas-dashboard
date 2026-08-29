"""PTF-DEFECT-OBSERVATION-STORE-TIMESTAMP-001 (P1).

The observation store must derive ``observed_at`` / ``retrieved_at`` from the
acquisition journal's ``completed_at`` carried on the result row -- never from
a literal date -- and must say where the time came from. A result without a
journal time falls back to the artifact's modification time and names that
basis.
"""
from __future__ import annotations

import json
import os
import sys
from datetime import datetime, timezone
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[3]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.pettripfinder.acquisition import market_observation_store as MOS  # noqa: E402

BLOCK = ("Pet & Service Animal Policy Service Animals - ADA-defined service "
         "animals welcome. / Dogs Allowed. 3 dogs max. 50lbs or less per pet. "
         "/ Fees - 30USD per pet per night.")
HTML = ("<html><body><h1>Baymont by Wyndham Testville</h1><p>4402 Creek View "
        "Drive</p><div>%s</div></body></html>" % BLOCK)


def _attempt_dir(tmp_path: Path) -> Path:
    attempt = tmp_path / "baymont-testville" / "attempt-01"
    attempt.mkdir(parents=True)
    (attempt / "rendered.html").write_text(HTML, encoding="utf-8")
    (attempt / "page-text.txt").write_text(
        "Baymont by Wyndham Testville\n4402 Creek View Drive\n%s\n" % BLOCK,
        encoding="utf-8")
    (attempt / "policy-block.txt").write_text(BLOCK, encoding="utf-8")
    return attempt


def _result(attempt: Path, **extra):
    row = {
        "identity_key": "baymont testville",
        "canonical_name": "Baymont Testville",
        "brand": "WYNDHAM",
        "corridor": "testville__south",
        "source_url": "https://www.wyndhamhotels.com/baymont/testville/overview",
        "final_url": "https://www.wyndhamhotels.com/baymont/testville/overview",
        "outcome": "VALID",
        "provider": "firecrawl",
        "reader": "wyndham",
        "locator_strategy": "static_html_walk",
        "identity_confirmed": True,
        "artifact_dir": str(attempt),
    }
    row.update(extra)
    return row


def _build(result):
    records, refusals, _ = MOS.build(
        {"market_id": "testville-xx", "results": [result]}, run_id="testville-001")
    assert not refusals, refusals
    assert len(records) == 1
    return records[0]


def test_the_journal_completed_at_is_the_capture_time(tmp_path):
    attempt = _attempt_dir(tmp_path)
    record = _build(_result(attempt, completed_at="2026-08-25T18:25:24.116911+00:00"))
    observation = record["observation"]
    assert observation["observed_at"] == "2026-08-25"
    assert observation["retrieved_at"] == "2026-08-25"
    assert record["capture_time"] == {
        "observed_at": "2026-08-25",
        "retrieved_at": "2026-08-25",
        "captured_at_utc": "2026-08-25T18:25:24.116911+00:00",
        "basis": MOS.CAPTURE_TIME_FROM_JOURNAL,
    }


def test_the_publication_grade_entries_carry_the_same_date(tmp_path):
    attempt = _attempt_dir(tmp_path)
    record = _build(_result(attempt, completed_at="2026-08-25T18:25:24+00:00"))
    entries = record["publication_grade"]["evidence_entries"]
    assert entries
    assert {e["captured_at"] for e in entries} == {"2026-08-25"}


def test_no_literal_date_survives_a_journal_on_another_day(tmp_path):
    attempt = _attempt_dir(tmp_path)
    record = _build(_result(attempt, completed_at="2026-09-02T03:04:05+00:00"))
    dumped = json.dumps(record)
    assert "2026-08-23" not in dumped
    assert record["observation"]["observed_at"] == "2026-09-02"


def test_a_result_without_a_journal_time_falls_back_to_the_artifact_and_says_so(tmp_path):
    attempt = _attempt_dir(tmp_path)
    stamp = datetime(2026, 7, 4, 12, 0, 0, tzinfo=timezone.utc).timestamp()
    os.utime(attempt / "rendered.html", (stamp, stamp))
    record = _build(_result(attempt))
    assert record["capture_time"]["basis"] == MOS.CAPTURE_TIME_FROM_ARTIFACT_MTIME
    assert record["observation"]["observed_at"] == "2026-07-04"
    assert record["capture_time"]["captured_at_utc"].startswith("2026-07-04T12:00:00")


def test_a_malformed_journal_stamp_is_not_trusted(tmp_path):
    attempt = _attempt_dir(tmp_path)
    stamp = datetime(2026, 7, 4, 12, 0, 0, tzinfo=timezone.utc).timestamp()
    os.utime(attempt / "rendered.html", (stamp, stamp))
    record = _build(_result(attempt, completed_at="yesterday"))
    assert record["capture_time"]["basis"] == MOS.CAPTURE_TIME_FROM_ARTIFACT_MTIME
    assert record["observation"]["observed_at"] == "2026-07-04"
