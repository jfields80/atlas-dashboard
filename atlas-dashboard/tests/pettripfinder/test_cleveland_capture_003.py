"""PTF-CLEVELAND-POLICY-CAPTURE-WORKER-003 -- targeted tests for this
worker's output.

These defend the proposed-authority manifest and observation batch produced
by ``scripts/pettripfinder/cleveland_capture_003_observations.py`` without
touching the frozen PTF-CLEVELAND-OVERNIGHT-AUTHORITY-001 authority that
``test_cleveland_authority.py`` guards (188 census / 19 published / 8
verified no-pets). This worker proposes; it does not publish.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.pettripfinder.policy import policy_membrane as MB
from scripts.pettripfinder.policy import policy_observation as PO

_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = (_ROOT / "launch_packages" / "pettripfinder" / "identity_census"
                  / "cleveland-policy-capture-003-proposed-authority.json")
PUBLISHED_FACTS_PATH = (_ROOT / "launch_packages" / "pettripfinder"
                         / "hotel_policy_facts_cleveland-akron-canton-oh.json")
CENSUS_PATH = (_ROOT / "launch_packages" / "pettripfinder" / "identity_census"
               / "cleveland-akron-canton-oh.json")
UNRESOLVED_MANIFEST_PATH = (_ROOT / "launch_packages" / "pettripfinder"
                             / "cleveland_unresolved_manifest.json")
RUN_DIR = (_ROOT / "data" / "worker_runs" / "pettripfinder"
           / "cleveland-policy-capture-003")


@pytest.fixture(scope="module")
def manifest():
    if not MANIFEST_PATH.exists():
        pytest.skip("proposed-authority manifest not generated; run "
                    "cleveland_capture_003_observations.py")
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def census():
    return json.loads(CENSUS_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def unresolved_manifest():
    return json.loads(UNRESOLVED_MANIFEST_PATH.read_text(encoding="utf-8"))


class TestTargetSetIsDerivedNotAssumed:

    def test_the_routed_awaiting_capture_targets_are_mutually_unique(
            self, unresolved_manifest):
        """The worker swept 74. Two of them (the Drury pair) resolved into
        published authority at PTF-CLEVELAND-POLICY-CAPTURE-INTEGRATION-003 and
        left the unresolved set, so 72 remain -- and the 72 that remain each
        carry the run's recorded attempt outcome rather than still claiming
        they are merely queued."""
        routed = [i for i in unresolved_manifest["items"]
                 if i["classification"] == "ROUTED_AWAITING_CAPTURE"]
        # 72 when capture-003 ran; 41 after the Pass-2 founder decisions
        # consumed thirty-one routed targets.
        assert len(routed) == 41
        names = [i["normalized_name"] for i in routed]
        assert len(set(names)) == 41  # 72 before the Pass-2 decisions
        for item in routed:
            attempt = item["capture_attempt"]
            assert attempt["run_id"] == "cleveland-policy-capture-003"
            assert attempt["outcome"] and attempt["detail"] and attempt["next_action"]


class TestManifestIsProposalOnly:

    def test_manifest_exists_and_is_scoped_to_cleveland(self, manifest):
        assert manifest["market_id"] == "cleveland-akron-canton-oh"
        # 6 attempted candidates: 5 published-quality + 1 membrane-rejected
        # (retained, see test_exactly_one_observation_is_membrane_rejected_on_identity).
        assert len(manifest["candidates"]) == 6

    def test_the_manifest_itself_publishes_nothing(self):
        """The manifest is a PROPOSAL and never becomes authority on its own.

        Publication happened separately and under review, in
        ``integrate_cleveland_capture_003``: of the six candidates only the two
        Drury records reached the published package (19 -> 21), and every other
        candidate is absent from it by decision, not by omission.
        """
        facts = json.loads(PUBLISHED_FACTS_PATH.read_text(encoding="utf-8"))
        # 21 when capture-003 closed; 41 after the Pass-2 publications.
        assert len(facts["hotels"]) == 41
        published = {h["key"] for h in facts["hotels"]}
        assert {"drury plaza hotel", "drury inn and suites beachwood"} <= published
        held = {"la quinta inn cleveland independence",
                "la quinta inn and suites cleveland airport north",
                "super 8 by wyndham richfield cleveland",
                "super 8 by wyndham akron south green uniontown"}
        assert held & published == set()

    def test_every_candidate_slug_is_in_the_census(self, manifest, census):
        slugs = {h["slug"] for h in census["hotels"]}
        for row in manifest["candidates"]:
            assert row["slug"] in slugs, row["slug"]

    def test_every_candidate_has_at_least_one_source_url(self, manifest):
        for row in manifest["candidates"]:
            assert row["source_urls"], row["slug"]

    def test_readiness_states_match_the_evidence_shape(self, manifest):
        states = sorted(row["state"] for row in manifest["candidates"])
        assert states == ["POLICY_CONFIRMED", "POLICY_CONFIRMED", "POLICY_NOT_FOUND",
                          "POLICY_PARTIAL", "POLICY_PARTIAL", "POLICY_PARTIAL"]


class TestObservationsValidateAgainstTheFrozenContract:

    def test_every_observation_in_the_run_directory_is_contract_valid(self):
        obs_path = RUN_DIR / "observations.json"
        if not obs_path.exists():
            pytest.skip("data/ is gitignored; run "
                        "cleveland_capture_003_observations.py to regenerate locally")
        batch = json.loads(obs_path.read_text(encoding="utf-8"))
        validated = PO.validate_emission_batch(batch)
        assert len(validated) == 6

    def test_exactly_one_observation_is_membrane_rejected_on_identity(self):
        """PTF-CLEVELAND-POLICY-CAPTURE-WORKER-003: the Super 8 Akron South/
        Green/Uniontown capture is genuine, quote-verified evidence that is
        honestly retained REJECTED (M10 name-token mismatch from the brand's
        own 'S/Green' abbreviation), never silently forced into a published
        candidate."""
        obs_path = RUN_DIR / "observations.json"
        if not obs_path.exists():
            pytest.skip("data/ is gitignored; run "
                        "cleveland_capture_003_observations.py to regenerate locally")
        batch = json.loads(obs_path.read_text(encoding="utf-8"))
        rejected = [o for o in batch if MB.evaluate(o).rejected]
        assert len(rejected) == 1
        assert rejected[0]["obs_id"] == "super-8-by-wyndham-akron-south-green-uniontown-001"
        assert MB.evaluate(rejected[0]).rule == "M10"

    def test_every_quote_is_a_literal_substring_of_its_own_raw_capture(self):
        """The exact class of error PTF-CLEVELAND-DAYTON-WORKER-INTEGRATION-001
        found in an earlier worker: an EXACT_QUOTE that was not actually a
        literal substring of the page it claimed to cite."""
        raw_dir = RUN_DIR / "raw"
        obs_path = RUN_DIR / "observations.json"
        if not obs_path.exists() or not raw_dir.is_dir():
            pytest.skip("data/ is gitignored; run "
                        "cleveland_capture_003_observations.py to regenerate locally")
        batch = json.loads(obs_path.read_text(encoding="utf-8"))
        # obs_id -> raw file stem, keyed by source_url so each observation is
        # checked against the capture it actually cites.
        by_url = {}
        for raw_file in raw_dir.glob("*.json"):
            doc = json.loads(raw_file.read_text(encoding="utf-8"))
            if doc.get("ok"):
                by_url[doc["final_url"]] = " ".join(doc["text"].split())
        for obs in batch:
            page = by_url.get(obs["source_url"])
            assert page is not None, obs["obs_id"]
            for item in obs["evidence"]:
                quote = " ".join(item["quote"].split())
                assert quote in page, (obs["obs_id"], item["quote"])

    def test_no_evidence_quote_is_an_elided_stitch(self):
        obs_path = RUN_DIR / "observations.json"
        if not obs_path.exists():
            pytest.skip("data/ is gitignored; run "
                        "cleveland_capture_003_observations.py to regenerate locally")
        for obs in json.loads(obs_path.read_text(encoding="utf-8")):
            for item in obs["evidence"]:
                assert "..." not in item["quote"], (obs["obs_id"], item["quote"])


class TestReconciliation:

    def test_the_74_target_set_reconciles_exactly(self, manifest):
        """captured + verified_no_pets + held/blocked + unresolved == 74,
        with no target double-counted and none silently dropped."""
        candidate_slugs = {row["slug"] for row in manifest["candidates"]}
        rejected_slugs = {
            row["slug"] for row in manifest["candidates"]
            if row.get("rejected_observations")
        }
        remaining = manifest["remaining_unresolved"]
        remaining_slugs = {row["slug"] for row in remaining}

        # the membrane-rejected candidate is counted once, as unresolved
        # (IDENTITY_TOKEN_MISMATCH), never also as a published-quality candidate
        assert rejected_slugs, "expected the known M10 rejection to be present"
        assert rejected_slugs <= candidate_slugs

        published_quality = candidate_slugs - rejected_slugs
        assert len(published_quality) == 5
        assert not (published_quality & remaining_slugs)

        categories = {row["category"] for row in remaining}
        assert "IDENTITY_TOKEN_MISMATCH" in categories
        assert "ACCESS_BLOCKED" in categories
        assert "JS_RENDERED_NO_STATIC_CONTENT" in categories
        assert "REDIRECTED_OFF_PROPERTY" in categories

        assert len(published_quality) + len(remaining_slugs) == 74

    def test_every_unresolved_row_has_exactly_one_category_and_next_action(self, manifest):
        for row in manifest["remaining_unresolved"]:
            assert row["category"]
            assert row["next_action"]
            assert row["detail"]
