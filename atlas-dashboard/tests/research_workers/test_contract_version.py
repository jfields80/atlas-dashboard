"""FD-3 -- worker contract version: ownership, semver, and compatibility.

Founder decision FD-3 (PTF-DISCOVERY-001) made three things binding:

  * the policy worker OWNS ``worker_contract_version``; everything downstream
    reads and propagates it and never invents one;
  * it follows semver, with MINOR reserved for backward-compatible additive
    contract changes;
  * an older contract version is accepted ONLY through an explicit
    compatibility allowlist -- never implicitly, never by range parsing.

The correction these tests lock in: 1.0.0 -> 1.1.0, because two additive
contract changes (ATLAS-WORKERS-005's FEE_BASIS_PER_ROOM_PER_NIGHT enum
value, ATLAS-WORKERS-006's optional WorkerResult.fee_policy) shipped after
1.0.0 without a bump, leaving the version non-discriminating.

The most important test in this file is
``test_stored_validated_results_still_rehash_identically``: 13 recorded
approvals are hash-bound to results produced under 1.0.0, and a version bump
that changed those hashes would silently invalidate every one of them.
"""

from __future__ import annotations

import glob
import json
import pathlib

import pytest

from services.research_workers import vocabulary as V
from services.research_workers.contracts import Assignment, SourceDocument, WorkerResult
from services.research_workers.routing import ROUTE_REJECTED, INVALID_WORKER_CONTRACT, route_result

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]


# --------------------------------------------------------------------------- #
# Ownership and semver shape.
# --------------------------------------------------------------------------- #

class TestOwnershipAndVersionShape:
    def test_the_worker_defines_the_version(self):
        """One definition, in the worker's own vocabulary. Discovery and the
        queue read this; they never declare their own."""
        assert V.CONTRACT_VERSION == "1.1.0"

    def test_version_is_semver(self):
        major, minor, patch = V.CONTRACT_VERSION.split(".")
        assert major.isdigit() and minor.isdigit() and patch.isdigit()

    def test_the_additive_changes_that_justified_the_minor_bump_are_present(self):
        """Guards the rationale: if either additive change disappeared, the
        1.1.0 justification recorded in vocabulary.py would be stale."""
        # ATLAS-WORKERS-005 -- additive enum value.
        assert V.FEE_BASIS_PER_ROOM_PER_NIGHT in V.FEE_BASIS_VALUES
        # ATLAS-WORKERS-006 -- optional additive result metadata.
        import dataclasses
        names = {f.name for f in dataclasses.fields(WorkerResult)}
        assert "fee_policy" in names

    def test_assignment_and_result_default_to_the_worker_version(self):
        assert Assignment(
            assignment_id="a", market_slug="m", listing_key="k", listing_name="n",
            address="", official_website="", allowed_source_urls=(),
            source_documents=(), requested_fields=(), created_by="t",
        ).contract_version == "1.1.0"


# --------------------------------------------------------------------------- #
# The compatibility allowlist (FD-3 rule 6).
# --------------------------------------------------------------------------- #

class TestCompatibilityAllowlist:
    def test_current_version_accepts_the_prior_minor(self):
        assert V.contract_versions_compatible("1.1.0", "1.0.0")

    def test_current_version_accepts_itself(self):
        assert V.contract_versions_compatible("1.1.0", "1.1.0")

    def test_it_is_not_symmetric(self):
        """Old code must not accept a newer assignment -- 1.0.0 cannot know
        what 1.1.0 added."""
        assert not V.contract_versions_compatible("1.0.0", "1.1.0")

    def test_unknown_versions_fail_closed(self):
        assert not V.contract_versions_compatible("2.0.0", "1.1.0")
        assert not V.contract_versions_compatible("1.1.0", "9.9.9")
        assert not V.contract_versions_compatible("", "")

    def test_the_allowlist_is_enumerated_not_parsed(self):
        """No version-range logic: every accepted pair is written down."""
        assert V.CONTRACT_COMPATIBILITY["1.1.0"] == frozenset({"1.1.0", "1.0.0"})
        assert V.CONTRACT_COMPATIBILITY["1.0.0"] == frozenset({"1.0.0"})

    def test_every_row_accepts_itself(self):
        for version, accepted in V.CONTRACT_COMPATIBILITY.items():
            assert version in accepted, "%s does not accept its own version" % version

    def test_the_current_version_has_a_row(self):
        assert V.CONTRACT_VERSION in V.CONTRACT_COMPATIBILITY


# --------------------------------------------------------------------------- #
# Routing honours the allowlist -- and still fails closed.
# --------------------------------------------------------------------------- #

DOC_TEXT = "Pets are welcome. Pet fee is 50 USD per night."


def _assignment(contract_version: str) -> Assignment:
    doc = SourceDocument(
        source_url="https://example.com/hotel", source_type=V.SOURCE_OFFICIAL_PROPERTY,
        retrieved_at="2026-08-02", title="Hotel", content_text=DOC_TEXT,
        content_hash="", retrieval_status=V.RETRIEVAL_OK)
    return Assignment(
        assignment_id="a-1", market_slug="columbus-oh", listing_key="hotel",
        listing_name="Hotel", address="1 Main St", official_website="https://example.com",
        allowed_source_urls=("https://example.com/hotel",), source_documents=(doc,),
        requested_fields=(V.FIELD_PETS_ALLOWED,), created_by="test",
        contract_version=contract_version)


def _result(contract_version: str) -> WorkerResult:
    return WorkerResult(
        assignment_id="a-1", listing_key="hotel", status=V.STATUS_COMPLETED,
        selected_source_url="https://example.com/hotel",
        selected_source_type=V.SOURCE_OFFICIAL_PROPERTY,
        evidence_quotes=("Pets are welcome.",),
        proposed_facts=(), unknown_fields=(), contradictions=(), warnings=(),
        provider="fake", model="fake", contract_version=contract_version).with_hash()


def _route(assignment_version: str, result_version: str):
    return route_result(_assignment(assignment_version), _result(result_version),
                        observed_at="2026-08-02", run_id="r-1")


class TestRoutingHonoursTheAllowlist:
    def test_an_older_assignment_is_routable_under_newer_code(self):
        """The regression this correction exists to prevent: before the
        allowlist, bumping to 1.1.0 rejected every 1.0.0 assignment -- which
        collapsed the frozen Columbus pilot replay from 15 launch-safe to 0."""
        env = _route("1.0.0", "1.1.0")
        assert INVALID_WORKER_CONTRACT not in env.reason_codes

    def test_matching_versions_route_normally(self):
        env = _route("1.1.0", "1.1.0")
        assert INVALID_WORKER_CONTRACT not in env.reason_codes

    def test_a_forward_pairing_is_rejected(self):
        env = _route("1.1.0", "1.0.0")
        assert env.route == ROUTE_REJECTED
        assert INVALID_WORKER_CONTRACT in env.reason_codes

    def test_an_unknown_version_is_rejected(self):
        env = _route("1.0.0", "3.0.0")
        assert env.route == ROUTE_REJECTED
        assert INVALID_WORKER_CONTRACT in env.reason_codes

    def test_the_envelope_propagates_the_result_version(self):
        """FD-3 rule 3: the version is carried through the RoutingEnvelope."""
        env = _route("1.0.0", "1.1.0")
        assert env.worker_contract_version == "1.1.0"


# --------------------------------------------------------------------------- #
# Hash stability -- the approval-binding guarantee.
# --------------------------------------------------------------------------- #

_STORED_RESULTS = sorted(glob.glob(str(
    REPO_ROOT / "data" / "worker_runs" / "pettripfinder" / "**" / "validated_results" / "*.json"
), recursive=True))


class TestApprovalHashBindingSurvivesTheBump:
    def test_a_serialized_result_rehashes_from_its_own_stored_version(self):
        """``contract_version`` is inside the hashed content, so a result must
        rehash from the version it STORES, never from the current default."""
        r = _result("1.0.0")
        payload = json.loads(json.dumps(r.to_dict()))
        assert WorkerResult.from_dict(payload).compute_hash() == r.result_hash

    @pytest.mark.parametrize("path", _STORED_RESULTS)
    def test_stored_validated_results_still_rehash_identically(self, path):
        """THE test that matters. 13 recorded approvals are hash-bound to
        results produced under contract 1.0.0. Those results store their
        version explicitly, so rehashing them must reproduce the stored
        ``result_hash`` exactly -- otherwise the bump would silently
        invalidate every approval and make the corpus unpromotable.

        ``data/`` is gitignored, so this parametrization is empty in a clean
        clone and the synthetic test above carries the guarantee.
        """
        stored = json.loads(pathlib.Path(path).read_text(encoding="utf-8"))
        if "result_hash" not in stored or "contract_version" not in stored:
            pytest.skip("not a serialized WorkerResult")
        result = WorkerResult.from_dict(stored)
        assert result.contract_version == stored["contract_version"]
        assert result.compute_hash() == stored["result_hash"], (
            "rehashing %s changed its result_hash; recorded approvals bound to "
            "it would be invalidated" % pathlib.Path(path).name)

    def test_approvals_file_is_still_hash_bound(self):
        """The approval records themselves are untouched by this change."""
        path = REPO_ROOT / "launch_packages" / "pettripfinder" / "hotel_worker_approvals.json"
        data = json.loads(path.read_text(encoding="utf-8"))
        approvals = data.get("approvals", [])
        assert approvals, "expected recorded approvals"
        for a in approvals:
            assert a.get("result_hash", "").startswith("sha256:")
