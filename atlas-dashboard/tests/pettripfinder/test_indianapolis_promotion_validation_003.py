"""The committed Indianapolis promotion-preparation artifacts must keep validating.

This runs the same eight checks the work order named over the artifacts under
launch_packages/ (no network, no spend). If a later change to the shadow census,
the promotion store, the signature view or the proposed authority breaks one of
them, this test says which.
"""
from __future__ import annotations

import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parents[2]
if str(REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(REPO_ROOT))

from scripts.pettripfinder import indianapolis_promotion_validation_003 as V  # noqa: E402


def test_every_promotion_preparation_check_passes():
    result = V.run_checks()
    failed = [c["check"] for c in result["checks"] if not c["passed"]]
    assert not failed, failed
    assert result["all_passed"] is True


def test_the_reviewed_cohort_lands_as_24_and_24_with_no_hold_left():
    summary = V.run_checks()["summary"]
    assert summary["pet_friendly"] == 24
    assert summary["verified_no_pets"] == 24
    assert summary["authority_total"] == 48
    assert summary["unresolved"] == 0 and summary["remaining_holds"] == 0


def test_nothing_is_registered_published_or_deployed():
    summary = V.run_checks()["summary"]
    assert summary["registered"] is False
    assert summary["published"] is False
    assert summary["deployed"] is False
