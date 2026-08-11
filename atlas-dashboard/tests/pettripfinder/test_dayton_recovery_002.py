"""PTF-DAYTON-RECOVERY-WORKER-002 -- targeted tests for this worker's output.

These defend the proposed-authority manifest and observation batch produced
by ``scripts/pettripfinder/dayton_recovery_002_observations.py`` without
touching the frozen PTF-DAYTON-INTEGRATION-ADJUDICATION-001 authority that
``test_dayton_authority.py`` guards (33 published / 6 no-pets / 6 held / 129
census). This worker proposes; it does not publish.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from scripts.pettripfinder.policy import policy_membrane as MB
from scripts.pettripfinder.policy import policy_observation as PO

_ROOT = Path(__file__).resolve().parents[2]
MANIFEST_PATH = (_ROOT / "launch_packages" / "pettripfinder" / "identity_census"
                  / "dayton-recovery-002-proposed-authority.json")
PUBLISHED_FACTS_PATH = (_ROOT / "launch_packages" / "pettripfinder"
                         / "hotel_policy_facts_dayton-oh.json")
CENSUS_PATH = (_ROOT / "launch_packages" / "pettripfinder" / "identity_census"
               / "dayton-oh.json")


@pytest.fixture(scope="module")
def manifest():
    return json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def census():
    return json.loads(CENSUS_PATH.read_text(encoding="utf-8"))


class TestManifestIsProposalOnly:

    def test_manifest_exists_and_is_scoped_to_dayton(self, manifest):
        assert manifest["market_id"] == "dayton-oh"
        assert len(manifest["candidates"]) == 14

    def test_manifest_does_not_touch_published_authority(self):
        """The frozen 33/6/6/129 partition is untouched by this worker."""
        facts = json.loads(PUBLISHED_FACTS_PATH.read_text(encoding="utf-8"))
        assert len(facts["hotels"]) == 33

    def test_every_candidate_slug_is_in_the_census(self, manifest, census):
        slugs = {h["slug"] for h in census["hotels"]}
        for row in manifest["candidates"]:
            assert row["slug"] in slugs, row["slug"]

    def test_every_candidate_has_at_least_one_source_url(self, manifest):
        for row in manifest["candidates"]:
            assert row["source_urls"], row["slug"]

    def test_remaining_unresolved_plus_candidates_reconciles_the_full_census(self, manifest):
        """33 published + 6 no-pets excluded + 14 new candidates + everything
        still unresolved must equal exactly the 129-hotel census, with no
        property double-counted and none dropped silently."""
        from scripts.pettripfinder.hotel_exclusions import load_exclusions
        from scripts.pettripfinder.site_data import normalize_name

        candidate_slugs = {row["slug"] for row in manifest["candidates"]}
        remaining_slugs = {row["slug"] for row in manifest["remaining_unresolved"]}
        assert not (candidate_slugs & remaining_slugs), "a slug is in both buckets"

        facts = json.loads(PUBLISHED_FACTS_PATH.read_text(encoding="utf-8"))
        published_keys = {h["key"] for h in facts["hotels"]}
        census = json.loads(CENSUS_PATH.read_text(encoding="utf-8"))
        by_norm = {normalize_name(h["canonical_name"]): h["slug"] for h in census["hotels"]}
        published_slugs = {by_norm[k] for k in published_keys if k in by_norm}

        excluded = [e for e in load_exclusions() if e.get("market_id") == "dayton-oh"]
        excluded_slugs = {by_norm[normalize_name(e["canonical_name"])]
                          for e in excluded if normalize_name(e["canonical_name"]) in by_norm}

        assert len(published_slugs | excluded_slugs | candidate_slugs | remaining_slugs) == 129

    def test_no_candidate_duplicates_a_published_hotel(self, manifest):
        facts = json.loads(PUBLISHED_FACTS_PATH.read_text(encoding="utf-8"))
        published_keys = {h["key"] for h in facts["hotels"]}
        for row in manifest["candidates"]:
            from scripts.pettripfinder.site_data import normalize_name
            assert normalize_name(row["canonical_name"]) not in published_keys


class TestObservationsValidateAgainstTheFrozenContract:
    """The defect this worker exists to avoid repeating: the original 44
    worker records never validated against ptf-policy-observation/1.0."""

    def test_every_observation_in_the_run_directory_is_contract_valid(self):
        obs_path = (_ROOT / "data" / "worker_runs" / "pettripfinder"
                    / "dayton-recovery-002" / "observations.json")
        if not obs_path.exists():
            pytest.skip("data/ is gitignored; run dayton_recovery_002_observations "
                        "to regenerate locally")
        batch = json.loads(obs_path.read_text(encoding="utf-8"))
        validated = PO.validate_emission_batch(batch)
        assert len(validated) == 14

    def test_no_observation_is_rejected_by_the_membrane(self):
        obs_path = (_ROOT / "data" / "worker_runs" / "pettripfinder"
                    / "dayton-recovery-002" / "observations.json")
        if not obs_path.exists():
            pytest.skip("data/ is gitignored; run dayton_recovery_002_observations "
                        "to regenerate locally")
        batch = json.loads(obs_path.read_text(encoding="utf-8"))
        for obs in batch:
            verdict = MB.evaluate(obs)
            assert not verdict.rejected, (obs["obs_id"], verdict.to_dict())

    def test_every_quote_is_a_literal_substring_of_its_own_capture(self):
        """The exact class of error the original worker made three times."""
        capture_dir = (_ROOT / "data" / "worker_runs" / "pettripfinder"
                       / "dayton-recovery-002" / "captures")
        obs_path = (_ROOT / "data" / "worker_runs" / "pettripfinder"
                    / "dayton-recovery-002" / "observations.json")
        if not obs_path.exists() or not capture_dir.is_dir():
            pytest.skip("data/ is gitignored; run dayton_recovery_002_observations "
                        "to regenerate locally")
        batch = json.loads(obs_path.read_text(encoding="utf-8"))
        cache = {}
        for obs in batch:
            slug = obs["obs_id"].rsplit("-", 1)[0]
            if slug not in cache:
                doc = json.loads((capture_dir / (slug + ".json")).read_text(encoding="utf-8"))
                cache[slug] = " ".join(doc["text"].split())
            page = cache[slug]
            for item in obs["evidence"]:
                quote = " ".join(item["quote"].split())
                # PTF-CLEVELAND-DAYTON-WORKER-INTEGRATION-001: this loop used to
                # `continue` on any quote containing "...", on the stated grounds
                # that it was "a stitched two-part quote; each half is checked
                # below" -- but no such check existed below, and the exemption
                # covered exactly the three Extended Stay America records whose
                # stitched quote was not a substring of its own capture. A test
                # that names a defect class and then exempts the only records
                # exhibiting it is worse than no test. The exemption is removed;
                # every quote must stand on its own.
                assert quote in page, (obs["obs_id"], item["quote"])

    def test_no_evidence_quote_is_an_elided_stitch(self):
        """An ellipsis inside a quote means text was dropped from the middle,
        which `extraction_confidence: EXACT_QUOTE` does not permit."""
        obs_path = (_ROOT / "data" / "worker_runs" / "pettripfinder"
                    / "dayton-recovery-002" / "observations.json")
        if not obs_path.exists():
            pytest.skip("data/ is gitignored; run dayton_recovery_002_observations "
                        "to regenerate locally")
        for obs in json.loads(obs_path.read_text(encoding="utf-8")):
            for item in obs["evidence"]:
                assert "..." not in item["quote"], (obs["obs_id"], item["quote"])


class TestCensusUpdatesAreConservative:

    def test_scioto_inn_identity_upgrade_is_recorded_with_a_note(self, census):
        h = next(x for x in census["hotels"] if x["slug"] == "scioto-inn-urbana")
        assert h["identity_state"] == "IDENTITY_CONFIRMED"
        assert "_recovery_002_note" in h

    def test_hotel_versailles_no_pets_finding_is_census_only(self, census):
        """This worker found one new negative fact (Hotel Versailles, JSON-LD
        petsAllowed:false) and recorded it in the census's lodging_state/
        policy_state roll-up (no_pets_count 7 -> 8). It is NOT written into
        the frozen hotel_exclusions.json authority -- that stays the
        integrator's call, same as every accepted candidate here."""
        assert census["no_pets_count"] == 8
        h = next(x for x in census["hotels"] if x["slug"] == "hotel-versailles")
        assert h["lodging_state"] == "LODGING_NO_PETS"
        from scripts.pettripfinder.hotel_exclusions import load_exclusions
        from scripts.pettripfinder.site_data import normalize_name
        names = {normalize_name(e["canonical_name"]) for e in load_exclusions()}
        assert normalize_name("Hotel Versailles") not in names

    def test_the_census_is_still_the_full_129(self, census):
        assert census["count"] == 129 == len(census["hotels"])

    def test_census_rollup_counts_match_the_records_they_summarize(self, census):
        """PTF-CLEVELAND-DAYTON-WORKER-INTEGRATION-001: the worker advanced two
        records to IDENTITY_CONFIRMED but left count_confirmed/count_provisional
        at their old 100/29. A roll-up that disagrees with the rows it counts is
        the failure mode the manifest doctrine exists to prevent -- it looks like
        verification while being stale -- so every declared count is pinned to
        the records here."""
        from collections import Counter

        ids = Counter(h["identity_state"] for h in census["hotels"])
        lodging = Counter(h["lodging_state"] for h in census["hotels"])
        assert census["count_confirmed"] == ids["IDENTITY_CONFIRMED"] == 102
        assert census["count_provisional"] == ids["IDENTITY_PROVISIONAL"] == 27
        assert census["count_confirmed"] + census["count_provisional"] == 129
        assert census["active_count"] == lodging["LODGING_CONFIRMED"] == 121
        assert census["no_pets_count"] == lodging["LODGING_NO_PETS"] == 8
        assert census["active_count"] + census["no_pets_count"] == 129

    def test_the_129_partition_is_mutually_exclusive_and_exhaustive(self, manifest, census):
        """The worker reported 33 + 6 + 14 + 75 = 128 and category counts that
        summed to 76. The census settles it: the unresolved remainder is 76, not
        75, so the true partition is 33 published + 6 verified-no-pets + 14
        proposed candidates + 76 still-unresolved = 129, with no overlaps."""
        from scripts.pettripfinder.hotel_exclusions import load_exclusions
        from scripts.pettripfinder.site_data import normalize_name

        by_norm = {normalize_name(h["canonical_name"]): h["slug"] for h in census["hotels"]}
        facts = json.loads(PUBLISHED_FACTS_PATH.read_text(encoding="utf-8"))
        published = {by_norm[h["key"]] for h in facts["hotels"] if h["key"] in by_norm}
        no_pets = {by_norm[normalize_name(e["canonical_name"])] for e in load_exclusions()
                   if e.get("market_id") == "dayton-oh"
                   and e.get("exclusion_state") == "VERIFIED_NO_PETS"
                   and normalize_name(e["canonical_name"]) in by_norm}
        candidates = {r["slug"] for r in manifest["candidates"]}
        remaining = {r["slug"] for r in manifest["remaining_unresolved"]}

        assert (len(published), len(no_pets)) == (33, 6)
        assert (len(candidates), len(remaining)) == (14, 76)
        buckets = (published, no_pets, candidates, remaining)
        for i, a in enumerate(buckets):
            for b in buckets[i + 1:]:
                assert not (a & b), sorted(a & b)
        assert sum(len(b) for b in buckets) == 129
        assert set().union(*buckets) == {h["slug"] for h in census["hotels"]}
