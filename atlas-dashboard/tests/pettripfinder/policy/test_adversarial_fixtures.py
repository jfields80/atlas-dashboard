"""PTF-POLICY-P0-001 -- the 24 adversarial policy fixtures.

Ported byte-for-byte from the verified research package (MANIFEST hash
``44bc634a...``), never retyped. Each fixture declares the checker verdict the
Atlas-native membrane must produce for its input.

A divergence is not automatically a bug in Atlas. ``divergence_report`` (below,
and the standalone report script) classifies each mismatch so a human decides
which side was right. The work order is explicit: production behaviour is not
bent to force fixtures green.
"""

from __future__ import annotations

import hashlib
import json
from pathlib import Path

import pytest

from scripts.pettripfinder.policy import evidence_bundle as EB
from scripts.pettripfinder.policy import policy_membrane as M

FIXTURE_PATH = Path(__file__).resolve().parent / "fixtures" / "adversarial_policy_fixtures.json"

#: The hash recorded in the research package's MANIFEST.sha256. If this test
#: fails the fixtures were edited, which is exactly what must not happen.
PACKAGE_FIXTURE_SHA256 = \
    "44bc634ad8d5d1b12adebf05be56a6f7a148b4df1c0243f69ca980a5915f75dd"


@pytest.fixture(scope="module")
def fixtures():
    return json.loads(FIXTURE_PATH.read_text(encoding="utf-8"))["fixtures"]


def test_fixtures_are_the_verified_package_bytes():
    actual = hashlib.sha256(FIXTURE_PATH.read_bytes()).hexdigest()
    assert actual == PACKAGE_FIXTURE_SHA256, (
        "the adversarial fixtures have been modified; they must be the "
        "package's verified bytes, not a local edit")


def test_there_are_exactly_24_fixtures(fixtures):
    assert len(fixtures) == 24


def evaluate_fixture(fixture):
    """Run one fixture through the Atlas-native layer, returning its verdict."""
    if fixture["input_kind"] == "observation":
        return M.evaluate(fixture["input"]).verdict
    if fixture["input_kind"] == "worker_result":
        # A worker result is validated by the evidence-bundle contract: a
        # well-formed transcript with a valid manifest hash is VALID.
        result = fixture["input"]
        try:
            EB.validate_transcript(result.get("ladder_transcript") or [])
        except EB.EvidenceBundleError:
            return "REJECT_MALFORMED_WORKER_RESULT"
        return "VALID_WORKER_RESULT"
    raise AssertionError("unknown input_kind %r" % fixture["input_kind"])


def divergence_report(fixtures):
    """Per-fixture comparison of expected vs Atlas-native verdict."""
    rows = []
    for fixture in fixtures:
        expected = fixture["expected"]["checker_verdict"]
        actual = evaluate_fixture(fixture)
        rows.append({
            "id": fixture["id"],
            "title": fixture["title"],
            "category": fixture["category"],
            "expected": expected,
            "atlas": actual,
            "agrees": expected == actual,
        })
    return rows


@pytest.mark.parametrize("fixture_id", [
    "FXP-01", "FXP-02", "FXP-03", "FXP-04", "FXP-05", "FXP-06", "FXP-07",
    "FXP-08", "FXP-09", "FXP-10", "FXP-11", "FXP-12", "FXP-13", "FXP-14",
    "FXP-15", "FXP-16", "FXP-17", "FXP-18", "FXP-19", "FXP-20", "FXP-21",
    "FXP-22", "FXP-23", "FXP-24",
])
def test_fixture_matches_atlas_native_verdict(fixtures, fixture_id):
    fixture = next(f for f in fixtures if f["id"] == fixture_id)
    expected = fixture["expected"]["checker_verdict"]
    actual = evaluate_fixture(fixture)
    assert actual == expected, (
        "%s (%s): package expects %s, Atlas produced %s. If Atlas is right, "
        "record the divergence rather than editing the fixture."
        % (fixture_id, fixture["title"], expected, actual))


def test_no_fixture_carries_a_policy_fact_into_publication(fixtures):
    """The whole fixture set must remain inert: nothing here may name a real
    published Columbus hotel, which would risk a fixture becoming a fact."""
    from scripts.pettripfinder.site_data import (
        load_published_hotel_policy_facts, normalize_name,
    )
    published = set(load_published_hotel_policy_facts())
    for fixture in fixtures:
        ref = (fixture["input"].get("hotel_ref") or {})
        name = normalize_name(ref.get("canonical_name", ""))
        assert name not in published, (
            "%s references published hotel %r; fixtures must use sample "
            "identities so a test can never be mistaken for evidence"
            % (fixture["id"], name))
