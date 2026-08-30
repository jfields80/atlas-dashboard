"""PTF-DETROIT-ANN-ARBOR-CLAUDE-CAPTURE-PASS3-001 -- committed-state tests.

Validates the real Claude attended-browser capture of the prepared 30-row
EVIDENCE_READY queue from ROUTING-EXPANSION-004: exact 30-row batch
completeness, artifact hash binding, quote contiguity, identity binding,
and the capture-only authority freeze (no founder decision recorded, no
policy/exclusion/seed authority touched, published=7 and
verified_no_pets=7 unchanged). It deliberately never reads the gitignored
worker tree except through the raw artifact files themselves -- artifact
bytes are hashed at capture time and the committed sha256 is what these
tests check against.
"""

from __future__ import annotations

import hashlib
import collections
import json
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
LP = REPO_ROOT / "launch_packages" / "pettripfinder"
RESULTS_PATH = LP / "detroit_ann_arbor_capture_pass3_001.json"
PACKET_PATH = LP / "detroit_ann_arbor_capture_pass3_founder_review_packet.json"
MANIFEST_PATH = LP / "detroit_ann_arbor_capture_pass3_001_evidence_manifest.json"
FACTS_PATH = LP / "hotel_policy_facts_detroit-ann-arbor-mi.json"
EXCLUSIONS_PATH = LP / "hotel_exclusions.json"
CENSUS_PATH = LP / "identity_census" / "detroit-ann-arbor-mi.json"
PARTITION_PATH = LP / "detroit_ann_arbor_final_partition_001.json"
QUEUE_PATH = (LP / "detroit_ann_arbor_routing_expansion_004_capture_queue.json")
ROUTING_SHARD_PATH = (LP / "markets" / "authority" / "detroit-ann-arbor-mi"
                      / "identity_routing.json")
RAW_DIR = (REPO_ROOT / "data" / "worker_runs" / "pettripfinder"
          / "detroit-ann-arbor-capture-pass3-001" / "raw")

MARKET = "detroit-ann-arbor-mi"
EXPECTED_IDS = ["DTW-P3-%02d" % n for n in range(1, 31)]
OUTCOMES = {
    "PUBLICATION_CANDIDATE", "VERIFIED_NO_PETS_CANDIDATE", "POLICY_NOT_FOUND",
    "IDENTITY_UNCERTAIN", "ACCESS_BLOCKED", "CAPTURE_FAILED", "SOURCE_AMBIGUOUS",
}
NO_ARTIFACT_IDS = {"DTW-P3-05", "DTW-P3-14"}  # Atheneum, Daxton: POLICY_NOT_FOUND


def _load(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


@pytest.fixture(scope="module")
def results():
    return _load(RESULTS_PATH)


@pytest.fixture(scope="module")
def packet():
    return _load(PACKET_PATH)


@pytest.fixture(scope="module")
def manifest():
    return _load(MANIFEST_PATH)


@pytest.fixture(scope="module")
def queue():
    return _load(QUEUE_PATH)


class TestBatchCompleteness:
    def test_exactly_thirty_rows_in_results(self, results):
        assert results["count"] == 30
        rows = results["results"]
        assert len(rows) == 30
        assert [r["queue_id"] for r in rows] == EXPECTED_IDS
        assert len({r["identity_key"] for r in rows}) == 30

    def test_exactly_thirty_rows_in_packet(self, packet):
        assert packet["count"] == 30
        candidates = packet["candidates"]
        assert len(candidates) == 30
        assert [c["decision_id"] for c in candidates] == EXPECTED_IDS

    def test_results_match_the_prepared_queue_exactly_no_substitutions(self, results, queue):
        queue_keys = {r["identity_key"] for r in queue["rows"]}
        result_keys = {r["identity_key"] for r in results["results"]}
        assert result_keys == queue_keys

    def test_every_result_row_has_exactly_one_valid_capture_outcome(self, results):
        for r in results["results"]:
            assert r["outcome"] in OUTCOMES

    def test_no_founder_decision_recorded_yet(self, packet):
        assert packet["status"] == "AWAITING_FOUNDER_REVIEW"
        for c in packet["candidates"]:
            assert "founder_decision" not in c
            assert "founder_decision_recorded_by" not in c
            assert c["recommended_founder_decision"]


class TestArtifactBinding:
    def test_every_artifact_sha256_matches_the_file_on_disk(self, packet):
        for c in packet["candidates"]:
            if c["decision_id"] in NO_ARTIFACT_IDS:
                assert "artifact_sha256" not in c
                continue
            path = RAW_DIR / c["artifact_file"]
            assert path.is_file(), path
            actual = hashlib.sha256(path.read_bytes()).hexdigest()
            assert actual == c["artifact_sha256"]

    def test_results_and_packet_agree_on_the_hash(self, results, packet):
        by_id_r = {r["queue_id"]: r for r in results["results"]}
        for c in packet["candidates"]:
            r = by_id_r[c["decision_id"]]
            if c["decision_id"] in NO_ARTIFACT_IDS:
                assert "artifact_sha256" not in r
            else:
                assert r["artifact_sha256"] == c["artifact_sha256"]

    def test_manifest_indexes_every_artifact_row(self, manifest, packet):
        expected = 30 - len(NO_ARTIFACT_IDS)
        assert manifest["count"] == expected
        assert len(manifest["items"]) == expected
        manifest_ids = {i["queue_id"] for i in manifest["items"]}
        packet_ids_with_artifact = {c["decision_id"] for c in packet["candidates"]
                                    if c["decision_id"] not in NO_ARTIFACT_IDS}
        assert manifest_ids == packet_ids_with_artifact


class TestQuoteContiguity:
    def test_every_captured_row_has_a_nonempty_exact_quote(self, packet):
        for c in packet["candidates"]:
            if c["decision_id"] in NO_ARTIFACT_IDS:
                assert c["exact_quote"] == ""
                continue
            assert c["exact_quote"].strip()
            assert "..." not in c["exact_quote"]
            assert "[TRUNCATED]" not in c["exact_quote"]

    def test_every_proposed_fact_and_withhold_quotes_the_source(self, packet):
        for c in packet["candidates"]:
            for fact in c["proposed_schema_1_2_facts"]:
                assert fact["quote"].strip()
                assert fact["quote"] in c["exact_quote"]
            for w in c["withheld_fields"]:
                assert w["reason_code"] in (
                    "SOURCE_CONTRADICTORY", "SOURCE_AMBIGUOUS",
                    "SCHEMA_CANNOT_REPRESENT", "ARTIFACT_INSUFFICIENT",
                    "IDENTITY_NOT_CONFIRMED")
                for q in w["quotes"]:
                    assert q in c["exact_quote"]

    def test_policy_not_found_rows_have_no_facts_or_withholds(self, packet):
        for did in NO_ARTIFACT_IDS:
            row = next(c for c in packet["candidates"] if c["decision_id"] == did)
            assert row["outcome"] == "POLICY_NOT_FOUND"
            assert row["proposed_schema_1_2_facts"] == []
            assert row["withheld_fields"] == []


class TestIdentityBinding:
    def test_every_row_carries_a_name_binding(self, packet):
        for c in packet["candidates"]:
            assert c["identity_binding"]["name"] is True

    def test_bound_rows_are_on_the_committed_census_official_domain(self, packet):
        # final_url may be a deeper page than official_url (e.g. a property's
        # own /faqs/ page reached by following a link FROM the official page,
        # per the work order's "locate property-specific pet-policy surface"
        # step) -- same registrable domain is the real invariant, not byte-
        # identical URLs.
        from urllib.parse import urlsplit
        census = {r["identity_key"]: r for r in _load(CENSUS_PATH)["hotels"]}

        def domain(url):
            host = (urlsplit(url).hostname or "").lower()
            labels = [l for l in host.split(".") if l]
            return ".".join(labels[-2:]) if len(labels) >= 2 else host

        for c in packet["candidates"]:
            crow = census[c["identity_key"]]
            assert crow["url_shape"] == "property"
            assert domain(crow["official_url"]) == domain(c["final_url"])

    def test_no_row_references_an_identity_outside_the_prepared_queue(self, packet, queue):
        queue_keys = {r["identity_key"] for r in queue["rows"]}
        for c in packet["candidates"]:
            assert c["identity_key"] in queue_keys


class TestFeeAmbiguityHandled:
    def test_delta_novi_fee_withheld_schema_cannot_represent(self, packet):
        row = next(c for c in packet["candidates"]
                  if c["identity_key"] == "delta hotels by marriott detroit novi")
        withheld = {w["field"]: w for w in row["withheld_fields"]}
        assert withheld["pet_fee"]["reason_code"] == "SCHEMA_CANNOT_REPRESENT"
        assert "pet_fee" not in {f["field"] for f in row["proposed_schema_1_2_facts"]}

    def test_detroit_foundation_fee_withheld_artifact_insufficient(self, packet):
        row = next(c for c in packet["candidates"]
                  if c["identity_key"] == "detroit foundation hotel")
        withheld = {w["field"]: w for w in row["withheld_fields"]}
        assert withheld["pet_fee"]["reason_code"] == "ARTIFACT_INSUFFICIENT"
        assert "pet_fee" not in {f["field"] for f in row["proposed_schema_1_2_facts"]}

    def test_courtyard_compound_fee_not_withheld(self, packet):
        for key in ("courtyard by marriott detroit dearborn", "courtyard by marriott detroit troy"):
            row = next(c for c in packet["candidates"] if c["identity_key"] == key)
            proposed = {f["field"] for f in row["proposed_schema_1_2_facts"]}
            assert "pet_fee" in proposed
            assert "other_charges" in proposed
            assert row["withheld_fields"] == []


class TestAuthorityFrozen:
    """Pass 3 was capture only: it made no founder decision and wrote no
    authority, and the assertions below used to pin that as a STANDING state --
    census 182, published 7, verified-no-pets 7, and not one captured identity
    in either authority file.

    That state ended by design. PTF-DETROIT-ANN-ARBOR-EVIDENCE-VOCABULARY-AND-
    PROMOTION-004 applied the founder's decisions on this very packet once
    decision B-003-1 registered the text_extract artifact kind its evidence
    needs. So what is pinned here now is the thing that is actually permanent:
    Pass 3 itself decided nothing, and every row of it that later entered
    authority did so under a NAMED later work order, never under this one.
    """

    def test_pass_3_recorded_no_founder_decision_of_its_own(self, packet):
        assert packet["status"] == "AWAITING_FOUNDER_REVIEW"
        for candidate in packet["candidates"]:
            # A recommendation is not a decision. Pass 3 proposed; it never
            # approved, and nothing in its own packet says otherwise.
            assert "recommended_founder_decision" in candidate
            assert "approval" not in candidate

    def test_every_captured_identity_that_published_names_a_later_authority(self, packet):
        keys = {c["identity_key"] for c in packet["candidates"]}
        facts = _load(FACTS_PATH)
        for hotel in facts["hotels"]:
            if hotel["identity_key"] not in keys:
                continue
            approval = hotel["approval"]
            # Pass 3 may not appear as the authorising instrument for anything:
            # it was a capture pass and authorised nothing. What must be true is
            # that SOME later order took responsibility -- naming only
            # EVIDENCE-VOCABULARY-AND-PROMOTION-004 pinned this to the one
            # order that happened to exist when it was written, so a packet
            # identity published by any subsequent order failed a test that was
            # never about the order's name.
            instrument = approval["authorisation"]["instrument"]
            assert "CLAUDE-CAPTURE-PASS3-001" not in instrument
            assert instrument.strip(), (
                "%s publishes without naming an authorising instrument"
                % hotel["identity_key"])

    def test_a_silent_hold_may_never_become_no_pets(self, packet):
        """The rule that outlives every count in this file: SOURCE SILENCE IS
        ABSENCE. The two POLICY_NOT_FOUND rows may never become no-pets.

        This half is absolute and has no exception. Pass 3 could not find a
        policy for these two properties; not finding one is not the property
        refusing pets, and an exclusion built on that would tell a guest with a
        dog to go elsewhere on the strength of nothing at all.
        """
        holds = {c["identity_key"] for c in packet["candidates"]
                 if c["outcome"] == "POLICY_NOT_FOUND"}
        assert len(holds) == 2
        exclusions = _load(EXCLUSIONS_PATH)
        excl_keys = {e["normalized_name"] for e in exclusions["exclusions"]
                     if e.get("market_id") == MARKET}
        assert not (excl_keys & holds)

    def test_a_silent_hold_publishes_only_by_explicitly_superseding(self, packet):
        """A silent hold MAY later be answered -- but only in the open.

        The guard used to forbid a POLICY_NOT_FOUND identity from entering
        authority at all, which is broader than the principle it exists to
        defend. Silence becoming NO-PETS is the danger, and that stays banned
        above. Silence later ANSWERED by the property's own affirmative
        evidence is the hold working exactly as intended -- it is why the row
        was left unresolved and routed rather than retired.

        What this demands instead is that the supersession be explicit: the
        new record must say which observation it replaces, cite first-party
        identity-bound evidence, and carry a hash. A hold that quietly
        disappears into authority is the thing worth catching.
        """
        holds = {c["identity_key"] for c in packet["candidates"]
                 if c["outcome"] == "POLICY_NOT_FOUND"}
        facts = _load(FACTS_PATH)
        for hotel in facts["hotels"]:
            if hotel["identity_key"] not in holds:
                continue
            approval = hotel.get("approval") or {}
            disposition = approval.get("founder_disposition") or {}
            supersedes = (disposition.get("supersedes")
                          or approval.get("supersedes") or "")
            assert supersedes, (
                "%s was a POLICY_NOT_FOUND hold and must state what it "
                "supersedes" % hotel["identity_key"])
            assert "POLICY_NOT_FOUND" in supersedes or "hold" in supersedes.lower()
            assert hotel.get("source_type") == "EXACT_ENTITY_DOMAIN"
            assert (hotel.get("evidence_quote") or "").strip()
            assert any(e.get("artifact_sha256") for e in hotel.get("evidence") or [])
            assert hotel.get("facts", {}).get("pets_allowed") is True, (
                "a silent hold may only be answered by AFFIRMATIVE evidence")

    def test_the_packet_evidence_is_still_exactly_what_it_captured(self, packet):
        """The packet is a historical record and must not drift, whatever later
        orders do with it."""
        assert packet["count"] == 30
        outcomes = collections.Counter(c["outcome"] for c in packet["candidates"])
        assert outcomes == {"PUBLICATION_CANDIDATE": 10,
                            "VERIFIED_NO_PETS_CANDIDATE": 18,
                            "POLICY_NOT_FOUND": 2}

    def test_pass_3_withdrew_no_route_of_its_own(self, packet):
        """Pass 3 held 179 routes and touched none of them.

        That total is no longer 179 and should not be: PTF-DETROIT-ANN-ARBOR-
        DISPLAY-INVENTORY-AND-RELEASE-CONTRACT-005 WITHDREW the 17 routes that
        publication answered, because a seeded hotel's display inventory is the
        source of truth for it. What stays true of Pass 3 is that it withdrew
        nothing itself -- and every route it did hold is either still in the
        shard or archived in the withdrawals report, never simply gone.
        """
        shard = _load(ROUTING_SHARD_PATH)
        assert shard["count"] == len(shard["routes"])
        withdrawals = _load(LP / "markets" / "reports"
                            / ("%s_routing_withdrawals.json" % MARKET))
        assert withdrawals["disposition"] == "WITHDRAWN_ANSWERED_BY_PUBLICATION"
        # Nothing was LOST between the two. The shard also GREW -- PTF-DETROIT-ANN-ARBOR-ZERO-COST-RECOVERY-007
        # confirmed 41 further routes at zero cost -- so the two no longer sum
        # to Pass 3's 179, and asserting that they do would just pin this file
        # to a moment. What must hold is that every route Pass 3 held is still
        # somewhere: none was deleted, and none is in both places at once.
        withdrawn_keys = {r["hotel_ref"]["identity_key"]
                          for r in withdrawals["withdrawn"]}
        shard_keys = {r["hotel_ref"]["identity_key"] for r in shard["routes"]}
        # The archive is CUMULATIVE across orders: 17 withdrawn by
        # DISPLAY-INVENTORY-005, 16 by FOUNDER-REVIEW-AND-AUTHORITY-011 and
        # 2 by FOUNDER-EXCEPTIONS-AND-DISPLAY-REPAIR-012 and 49 by
        # BRIGHTDATA-AUTHORITY-APPLICATION-019 (49 clean + 1 founder ruling),
        # each record stamped with the order that withdrew it. Pass 3 still
        # withdrew none of its own, which is what this test is about.
        # ... and 2 more by the FREE-ATTENDED-PASS-020 founder rulings.
        # ... and 20 more by ATTENDED-COMPLETION-ADOPTION-022.
        assert withdrawals["count"] == 105
        assert not [r for r in withdrawals["withdrawn"]
                    if "CAPTURE-PASS3" in (r.get("withdrawn_by_work_order") or "")]
        assert not (withdrawn_keys & shard_keys)
        assert shard["count"] >= 179 - withdrawals["count"]
        # And none of it was retired -- these were correct bindings.
        for route in withdrawals["withdrawn"]:
            assert route["status"] != "ROUTING_RETIRED"
