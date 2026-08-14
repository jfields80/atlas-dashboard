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

    def test_every_candidate_is_adjudicated_into_exactly_one_outcome(self, manifest):
        """PTF-DAYTON-CANDIDATE-PROMOTION-001 reviewed all fourteen proposals.

        The worker proposed; this is what integration decided. Eleven publish,
        one is an exclusion, and two stay proposals because readiness.derive
        puts them in POLICY_PARTIAL. A candidate in two buckets, or in none, is
        the failure this asserts against."""
        from scripts.pettripfinder.hotel_exclusions import load_exclusions
        from scripts.pettripfinder.site_data import normalize_name

        facts = json.loads(PUBLISHED_FACTS_PATH.read_text(encoding="utf-8"))
        published = {h["key"] for h in facts["hotels"]}
        excluded = {normalize_name(e["canonical_name"]) for e in load_exclusions()
                    if e.get("market_id") == "dayton-oh"}

        outcomes = {"published": set(), "excluded": set(), "still_proposed": set()}
        for row in manifest["candidates"]:
            key = normalize_name(row["canonical_name"])
            hits = [b for b, s in (("published", published), ("excluded", excluded))
                    if key in s]
            assert len(hits) <= 1, (row["slug"], hits)
            outcomes[hits[0] if hits else "still_proposed"].add(row["slug"])

        assert len(outcomes["published"]) == 11
        assert outcomes["excluded"] == {"hotel-versailles"}
        assert outcomes["still_proposed"] == {"baymont-by-wyndham-dayton-north",
                                              "wingate-by-wyndham-dayton-north"}
        # 44 -> 47: PTF-DAYTON-WORK-BROWSER-INTEGRATION-001 published three more
        # identities from hash-verified captures. None of them is one of these
        # fourteen candidates, which is why the three assertions above are
        # unchanged -- this one counts the whole package, not this batch.
        assert len(facts["hotels"]) == 47

    def test_the_two_unpromoted_candidates_are_not_publishable(self, manifest):
        """They are held back by the readiness engine, not by opinion."""
        from scripts.pettripfinder.policy import readiness as RD

        held = {"baymont-by-wyndham-dayton-north", "wingate-by-wyndham-dayton-north"}
        for row in manifest["candidates"]:
            if row["slug"] in held:
                assert row["state"] not in RD.PUBLISHABLE_STATES, row["slug"]

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

    def test_no_candidate_publishes_twice(self, manifest):
        """Promotion appends; it must never duplicate an identity already in the
        package, and no identity may hold two records."""
        from scripts.pettripfinder.site_data import normalize_name

        facts = json.loads(PUBLISHED_FACTS_PATH.read_text(encoding="utf-8"))
        keys = [h["key"] for h in facts["hotels"]]
        assert len(keys) == len(set(keys)), "a hotel key is published twice"
        names = [h["name"] for h in facts["hotels"]]
        assert len(names) == len(set(names))
        for row in manifest["candidates"]:
            assert keys.count(normalize_name(row["canonical_name"])) <= 1, row["slug"]

    def test_no_published_hotel_is_also_excluded(self):
        """The distinction the two authorities exist to hold apart."""
        from scripts.pettripfinder.hotel_exclusions import load_exclusions
        from scripts.pettripfinder.site_data import normalize_name

        facts = json.loads(PUBLISHED_FACTS_PATH.read_text(encoding="utf-8"))
        published = {h["key"] for h in facts["hotels"]}
        excluded = {normalize_name(e["canonical_name"]) for e in load_exclusions()}
        assert not (published & excluded), sorted(published & excluded)


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

    def test_hotel_versailles_no_pets_finding_is_now_committed_authority(self, census):
        """The worker recorded this negative fact in the census only and left
        the exclusion registry to the integrator. PTF-DAYTON-CANDIDATE-PROMOTION-001
        made that call: the evidence is a hash-verified JSON-LD refusal on the
        property's own Hotel node, so it is now committed authority."""
        from scripts.pettripfinder.hotel_exclusions import load_exclusions
        from scripts.pettripfinder.site_data import normalize_name

        # PTF-CENSUS-PARTITION-NORMALIZATION-001 moved the no-pets fact off
        # the LODGING axis, where it was never a statement about the property's
        # category, and onto the POLICY axis where it belongs. The finding
        # itself is unchanged and still committed authority.
        assert census["no_pets_count"] == 7
        h = next(x for x in census["hotels"] if x["slug"] == "hotel-versailles")
        assert h["lodging_state"] == "LODGING_CONFIRMED"
        assert h["policy_state"] == "VERIFIED_NO_PETS"

        rec = next((e for e in load_exclusions()
                    if normalize_name(e["canonical_name"]) == normalize_name("Hotel Versailles")),
                   None)
        assert rec is not None, "the adjudicated refusal is not in the registry"
        assert rec["market_id"] == "dayton-oh"
        assert rec["source_hash"] == (
            "3819c19720bac29d04068f6f398fc0d27dab96b124c3be088b2177af26ab5813")

    def test_the_census_no_pets_set_and_the_registry_are_not_the_same_set(self, census):
        """Both hold eight, and they are not the same eight. That is the point.

        The census's eighth is Holiday Inn Express & Suites Troy, which the
        worker counted VERIFIED_NO_PETS on a research-agent assertion with no
        quote, capture or hash. Silence about evidence is not evidence, so it
        has never entered the registry and still has not.

        The registry's eighth is Best Western Celina, added by
        PTF-DAYTON-WORK-BROWSER-INTEGRATION-001 on a hash-verified capture whose
        visible PET POLICY block reads "Pets are not accepted." The census has
        not caught up -- it still carries that row LODGING_CONFIRMED, because a
        census is a record of a discovery pass and this integrator does not
        rewrite one. Asserting the divergence in both directions is what keeps
        the equal counts from reading as agreement."""
        from scripts.pettripfinder.hotel_exclusions import load_exclusions
        from scripts.pettripfinder.site_data import normalize_name

        registry = {normalize_name(e["canonical_name"]) for e in load_exclusions()
                    if e.get("market_id") == "dayton-oh"
                    and e["exclusion_state"] == "VERIFIED_NO_PETS"}
        census_no_pets = {normalize_name(h["canonical_name"]) for h in census["hotels"]
                          if h["policy_state"] == "VERIFIED_NO_PETS"}
        # The asymmetry is still real, and it has NARROWED in the honest
        # direction. Holiday Inn Express & Suites Troy claimed a captured
        # refusal that no exclusion record holds, and the later Work-browser
        # pass recorded the opposite -- the page rendered and stated no pet
        # policy at all. Phase C withdrew that unsupported claim rather than
        # inventing evidence for it, so the census now under-claims relative to
        # the registry instead of disagreeing with it in both directions.
        assert len(registry) == 8
        assert len(census_no_pets) == 7
        assert registry != census_no_pets
        assert census_no_pets - registry == set()
        assert registry - census_no_pets == {normalize_name("Best Western Celina")}
        # And the partition -- which owns disposition -- places Troy as
        # unresolved, which is what "unadjudicated" has always meant.
        partition = json.loads(
            (_ROOT / "launch_packages" / "pettripfinder"
             / "dayton_final_partition_001.json").read_text(encoding="utf-8"))
        troy = next(i for i in partition["items"]
                    if i["slug"] == "holiday-inn-express-suites-troy")
        assert troy["final_state"] == "AWAITING_POLICY_OBSERVATION"
        assert troy["resolved"] is False

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
        policy = Counter(h["policy_state"] for h in census["hotels"])
        assert census["count_confirmed"] == ids["IDENTITY_CONFIRMED"] == 102
        assert census["count_provisional"] == ids["IDENTITY_PROVISIONAL"] == 27
        assert census["count_confirmed"] + census["count_provisional"] == 129
        # Every identity is lodging: the eight rows that read LODGING_NO_PETS
        # were stating a POLICY fact in the category axis, and Phase C moved it.
        # The roll-ups follow the rows, which is the whole point of pinning them.
        assert census["active_count"] == lodging["LODGING_CONFIRMED"] == 129
        assert lodging["LODGING_NO_PETS"] == 0
        assert census["no_pets_count"] == policy["VERIFIED_NO_PETS"] == 7

    def test_the_129_partition_is_mutually_exclusive_and_exhaustive(self, manifest, census):
        """Every one of the 129 Dayton identities sits in exactly one state.

        PTF-DAYTON-CANDIDATE-PROMOTION-001 adjudicated the fourteen proposals
        and PTF-DAYTON-WORK-BROWSER-INTEGRATION-001 then answered four more of
        the unresolved (three published, one excluded), so the partition is now:

            47 published pet-friendly
           + 8 verified no-pets
           + 2 still proposed (readiness POLICY_PARTIAL)
          + 72 unresolved
          ---
           129

        ``remaining_unresolved`` shrank 76 -> 72 because the manifest DERIVES it
        by subtracting whatever has since reached the published package or the
        exclusion registry, the same way ``candidates_still_proposed`` has
        always been derived. Without that, the four answered properties would sit
        in two buckets at once and this assertion is what would catch it.

        Mutual exclusivity is the point: a property that is both published and
        excluded, or that falls out of every bucket, is exactly the drift this
        reconciliation exists to catch."""
        from scripts.pettripfinder.hotel_exclusions import load_exclusions
        from scripts.pettripfinder.site_data import normalize_name

        by_norm = {normalize_name(h["canonical_name"]): h["slug"] for h in census["hotels"]}
        facts = json.loads(PUBLISHED_FACTS_PATH.read_text(encoding="utf-8"))
        published = {by_norm[h["key"]] for h in facts["hotels"] if h["key"] in by_norm}
        no_pets = {by_norm[normalize_name(e["canonical_name"])] for e in load_exclusions()
                   if e.get("market_id") == "dayton-oh"
                   and e.get("exclusion_state") == "VERIFIED_NO_PETS"
                   and normalize_name(e["canonical_name"]) in by_norm}
        remaining = {r["slug"] for r in manifest["remaining_unresolved"]}
        # Whatever the manifest proposed that review did not adopt is still a
        # proposal -- derived, not restated, so it cannot disagree with reality.
        proposed = ({r["slug"] for r in manifest["candidates"]}
                    - published - no_pets - remaining)

        assert (len(published), len(no_pets)) == (47, 8)
        assert (len(proposed), len(remaining)) == (2, 72)
        buckets = (published, no_pets, proposed, remaining)
        for i, a in enumerate(buckets):
            for b in buckets[i + 1:]:
                assert not (a & b), sorted(a & b)
        assert sum(len(b) for b in buckets) == 129
        assert set().union(*buckets) == {h["slug"] for h in census["hotels"]}
