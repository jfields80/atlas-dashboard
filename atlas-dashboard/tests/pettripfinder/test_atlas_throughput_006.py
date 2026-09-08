"""ATLAS-THROUGHPUT-006 -- remote validation, trusted artifact handoff and the
production release lane.

The 32-case adversarial matrix. The expensive proofs (a real broad run, a real
candidate round trip) are recorded once by the committed simulation and pilot
artifacts and asserted from them; everything about the RULES runs here against
synthetic inputs, because those rules have to hold for changes this repository
has not seen yet.
"""

from __future__ import annotations

import copy
import json
import os
import zipfile
from collections import OrderedDict
from pathlib import Path

import pytest

from scripts.pettripfinder import artifact_handoff as AH
from scripts.pettripfinder import ci_report as CR
from scripts.pettripfinder import ci_validation as CI
from scripts.pettripfinder import live_verification as LV
from scripts.pettripfinder import regression_delta as RD
from scripts.pettripfinder import release_coordinator as RC
from scripts.pettripfinder import release_queue as RQ
from scripts.pettripfinder import sealed_market_package as SMP

REPORTS = SMP.LAUNCH_PACKAGE / "reports"
SHARD_MANIFEST = REPORTS / "atlas_throughput_006_shard_manifest.json"
SIMULATION = REPORTS / "atlas_throughput_006_node_completeness.json"
HANDOFF_REPORT = REPORTS / "atlas_throughput_006_artifact_handoff.json"


@pytest.fixture(scope="module")
def manifest():
    return json.loads(SHARD_MANIFEST.read_text(encoding="utf-8-sig"))


def _receipt(**overrides):
    """A receipt that verifies, so a test can break exactly one thing."""
    completeness = CI.verify_completeness(["a::t1", "b::t2"], {"1": ["a::t1"], "2": ["b::t2"]},
                                          shards_required=[1, 2], shards_completed=[1, 2])
    receipt = CI.build_receipt(
        ci_run_id="run-1", source_commit="c" * 40, change_class=["SHARED_RUNTIME_CHANGE"],
        shards_required=[1, 2], shards_completed=[1, 2], completeness=completeness,
        counts={"tests": 2, "failures": 0}, pre_existing=[], true_new=[],
        candidate_digest="sha256:" + "d" * 64)
    receipt.update(overrides)
    if "receipt_digest" not in overrides:
        receipt["receipt_digest"] = SMP.sha256_text(SMP.canonical_json(
            OrderedDict((k, v) for k, v in receipt.items() if k != "receipt_digest")))
    return receipt


def _required(shards=(1, 2)):
    return OrderedDict((("shards_required", list(shards)),
                        ("REMOTE_BROAD_JOBS", len(shards)),
                        ("reasons", [OrderedDict((("why", "test"),))])))


def _candidate(tmp_path, files=("index.html", "about/index.html")):
    from scripts.pettripfinder import assemble_production_site as APS
    root = Path(tmp_path) / "candidate"
    (root / "site").mkdir(parents=True, exist_ok=True)
    for rel in files:
        path = root / "site" / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("<html>%s</html>" % rel, encoding="utf-8", newline="\n")
    manifest = OrderedDict((
        ("schema", RC.MANIFEST_SCHEMA),
        ("participating_markets", ["dayton-oh"]),
        ("intended_delta", OrderedDict((("market_id", "dayton-oh"),))),
        ("parent_release_digest", "sha256:" + "p" * 64),
        ("source_commit", "c" * 40),
        ("deployment_artifact_digest", APS.bundle_digest(APS.file_hashes(root / "site"))),
        ("sitemap_route_count", 2),
    ))
    (root / "release_manifest.json").write_text(SMP.canonical_json(manifest) + "\n",
                                                encoding="utf-8", newline="\n")
    return root


# --------------------------------------------------------------------------- #
# 1-5: node-id completeness.
# --------------------------------------------------------------------------- #

class TestNodeCompleteness:
    def test_case_1_every_planned_node_is_assigned_exactly_once(self, manifest):
        """Proved over a REAL broad run, not a synthetic collection."""
        sim = json.loads(SIMULATION.read_text(encoding="utf-8-sig"))
        assert sim["unassigned_cases"] == 0
        assert sim["planned"] == sim["executed"]
        assert sim["complete"] is True
        assert sum(s["cases"] for s in sim["shards"]) == sim["planned"]

    def test_case_2_a_missing_shard_fails_the_run(self):
        result = CI.verify_completeness(["a::t"], {"1": ["a::t"]},
                                        shards_required=[1, 2], shards_completed=[1])
        assert result["complete"] is False
        assert any(p["code"] == CI.SHARD_MISSING for p in result["problems"])

    def test_case_3_a_timed_out_shard_fails_the_run(self):
        """A shard that timed out reports nothing, which is a missing shard --
        never a shard whose tests all passed."""
        result = CI.verify_completeness(["a::t1", "b::t2"], {"1": ["a::t1"]},
                                        shards_required=[1, 2], shards_completed=[1])
        codes = {p["code"] for p in result["problems"]}
        assert CI.SHARD_MISSING in codes and CI.NODE_MISSING in codes

    def test_case_4_an_unintended_duplicate_is_detected(self):
        result = CI.verify_completeness(["a::t"], {"1": ["a::t"], "2": ["a::t"]},
                                        shards_required=[1, 2], shards_completed=[1, 2])
        assert any(p["code"] == CI.NODE_DUPLICATED for p in result["problems"])
        # ... unless it is a documented smoke duplicated on purpose.
        allowed = CI.verify_completeness(["a::t"], {"1": ["a::t"], "2": ["a::t"]},
                                         shards_required=[1, 2], shards_completed=[1, 2],
                                         duplicates_allowed=["a::t"])
        assert allowed["complete"] is True

    def test_case_5_a_collection_error_fails_the_run(self):
        result = CI.verify_completeness(["a::t"], {"1": ["a::t"]},
                                        shards_required=[1], shards_completed=[1],
                                        collection_errors=["ERROR collecting tests/x.py"])
        assert result["complete"] is False
        assert any(p["code"] == CI.COLLECTION_ERROR for p in result["problems"])

    def test_an_explicit_exclusion_accounts_for_a_node(self):
        result = CI.verify_completeness(["a::t1", "b::t2"], {"1": ["a::t1"]},
                                        excluded={"b::t2": "quarantined by PTF-XYZ"},
                                        shards_required=[1], shards_completed=[1])
        assert result["complete"] is True and result["excluded"] == 1


# --------------------------------------------------------------------------- #
# 6-7: the legacy failure baseline.
# --------------------------------------------------------------------------- #

class TestLegacyBaseline:
    BASELINE = {"failing_node_ids": ["m.py::t_known"],
                "failure_signatures": {"m.py::t_known": CI.failure_signature("assert 1 == 2")}}

    def test_case_6_a_pre_existing_failure_is_recognised(self):
        out = CI.classify_failures({"m.py::t_known": "assert 1 == 2"}, self.BASELINE)
        assert out["PRE_EXISTING"] == ["m.py::t_known"] and out["TRUE_NEW"] == []

    def test_case_7_the_same_node_failing_differently_is_true_new(self):
        out = CI.classify_failures({"m.py::t_known": "ImportError: no module named x"}, self.BASELINE)
        assert out["TRUE_NEW"] == ["m.py::t_known"]
        assert out["changed_signature"][0]["why"] == "same node, different failure"

    def test_a_signature_ignores_paths_addresses_and_timestamps(self):
        a = CI.failure_signature("failed at C:\\\\tmp\\\\x1 0x7ff 2026-09-08T10:00:00Z")
        b = CI.failure_signature("failed at C:\\\\tmp\\\\x2 0x1aa 2026-09-09T11:30:00Z")
        assert a == b

    def test_a_node_outside_the_baseline_is_true_new(self):
        out = CI.classify_failures({"m.py::t_new": "boom"}, self.BASELINE)
        assert out["TRUE_NEW"] == ["m.py::t_new"]

    def test_the_real_audit_classified_clean(self):
        sim = json.loads(SIMULATION.read_text(encoding="utf-8-sig"))
        assert sim["PRE_EXISTING"] == 160 and sim["TRUE_NEW"] == 0


# --------------------------------------------------------------------------- #
# 8-10: the artifact handoff.
# --------------------------------------------------------------------------- #

class TestArtifactHandoff:
    def test_case_8_a_candidate_survives_the_handoff_byte_identical(self, tmp_path):
        candidate = _candidate(tmp_path)
        result = AH.round_trip(candidate, tmp_path / "work")
        assert result["identical"] is True
        assert result["staged_deployment_digest"] == result["received_deployment_digest"]
        assert result["candidate_digest_staged"] == result["candidate_digest_received"]
        assert result["archive_is_deterministic"] is True

    def test_case_9_a_modified_artifact_fails(self, tmp_path):
        candidate = _candidate(tmp_path)
        handoff = AH.package_candidate(candidate, tmp_path / "c.zip")
        # Someone edits one byte of the archive's content after packaging.
        with zipfile.ZipFile(tmp_path / "c.zip") as zf:
            names = zf.namelist()
        rebuilt = tmp_path / "tampered.zip"
        with zipfile.ZipFile(tmp_path / "c.zip") as src, zipfile.ZipFile(rebuilt, "w") as dst:
            for name in names:
                data = src.read(name)
                if name == "site/index.html":
                    data = data + b"<!-- tampered -->"
                dst.writestr(name, data)
        with pytest.raises(AH.HandoffError) as exc:
            AH.receive_candidate(rebuilt, handoff, tmp_path / "dest")
        assert exc.value.code == AH.ARCHIVE_DIGEST_MISMATCH

    def test_case_9b_a_tampered_file_is_caught_even_with_a_matching_archive(self, tmp_path):
        candidate = _candidate(tmp_path)
        handoff = AH.package_candidate(candidate, tmp_path / "c.zip")
        received = AH.receive_candidate(tmp_path / "c.zip", handoff, tmp_path / "dest")
        assert received["identical"] is True
        (tmp_path / "dest" / "site" / "index.html").write_text("edited", encoding="utf-8")
        problems = AH.substitution_problems(handoff, tmp_path / "dest")
        assert problems and any(p.startswith(AH.SUBSTITUTED_ARTIFACT) for p in problems)

    def test_case_10_ci_cannot_substitute_a_rebuilt_candidate(self, tmp_path):
        """A rebuilt tree is a different artifact, never an equivalent one."""
        candidate = _candidate(tmp_path)
        handoff = AH.package_candidate(candidate, tmp_path / "c.zip")
        rebuilt = _candidate(tmp_path / "elsewhere", files=("index.html", "about/index.html",
                                                            "extra.html"))
        problems = AH.substitution_problems(handoff, rebuilt)
        assert problems
        assert any("a rebuilt candidate is a different artifact" in p for p in problems)

    def test_the_committed_round_trip_used_a_real_candidate(self):
        doc = json.loads(HANDOFF_REPORT.read_text(encoding="utf-8-sig"))
        rt = doc["round_trip"]
        assert rt["identical"] is True
        assert rt["staged_deployment_digest"] == rt["received_deployment_digest"]
        assert doc["cross_platform"]["crlf_files"] == 0
        assert doc["cross_platform"]["case_collisions"] == []


# --------------------------------------------------------------------------- #
# 11-16: change class -> remote jobs.
# --------------------------------------------------------------------------- #

class TestDispatch:
    def _classification(self, *paths):
        rows = []
        for path in paths:
            classes, why = RD.classify_path(path)
            rows.append(OrderedDict((("path", path), ("classes", list(classes)), ("why", why),
                                     ("status", "M"), ("rule", "test"),
                                     ("shared_test_state", False),
                                     ("markets", list(RD._markets_named(path))),
                                     ("market_local_proof", None))))
        return OrderedDict((("changed_files", rows),
                            ("change_classes", sorted({c for r in rows for c in r["classes"]}))))

    def test_case_11_the_data_only_path_requests_zero_broad_jobs(self, manifest):
        classification = self._classification(
            "launch_packages/pettripfinder/markets/authority/dayton-oh/policy_records.json")
        plan = RD.plan_for(classification)
        fast = OrderedDict((("FULL_REGRESSION_REQUIRED", "NO"),
                            ("receipt_eligible", True)))
        required = CI.required_shards(classification, plan, manifest=manifest, fast_lane=fast)
        assert required["REMOTE_BROAD_JOBS"] == 0
        assert required["shards_required"] == []
        assert required["dispatch"] == "NONE"
        assert required["FAST_DATA_ONLY_RELEASE_SATISFIES"] == "YES"

    @pytest.mark.parametrize("path,case", [
        ("scripts/pettripfinder/site_pages.py", "12 shared runtime"),
        ("scripts/pettripfinder/markets/contract.py", "13 shared schema"),
        ("scripts/pettripfinder/assemble_production_site.py", "14 assembler"),
    ])
    def test_cases_12_13_14_shared_changes_request_broad_jobs(self, manifest, path, case):
        classification = self._classification(path)
        plan = RD.plan_for(classification)
        required = CI.required_shards(classification, plan, manifest=manifest)
        assert required["REMOTE_BROAD_JOBS"] == 4, case
        assert required["shards_required"] == [1, 2, 3, 4], case

    def test_case_15_a_deployment_change_requests_deployment_validation(self, manifest):
        classification = self._classification("deploy/netlify/redirects")
        plan = RD.plan_for(classification)
        required = CI.required_shards(classification, plan, manifest=manifest)
        assert required["REMOTE_BROAD_JOBS"] >= 1
        assert required["scope"] in (CI.SCOPE_DEPLOYMENT, CI.SCOPE_ALL)

    def test_case_16_an_unknown_change_falls_broad(self, manifest):
        classification = self._classification("some/unclaimed/place/thing.py")
        plan = RD.plan_for(classification)
        required = CI.required_shards(classification, plan, manifest=manifest)
        assert required["REMOTE_BROAD_JOBS"] == 4
        assert any("fall broad rather than guess" in r["why"] for r in required["reasons"])

    def test_the_selector_cannot_under_scope_a_mixed_change(self, manifest):
        classification = self._classification(
            "launch_packages/pettripfinder/markets/authority/dayton-oh/policy_records.json",
            "scripts/pettripfinder/site_pages.py")
        plan = RD.plan_for(classification)
        required = CI.required_shards(classification, plan, manifest=manifest)
        assert required["REMOTE_BROAD_JOBS"] == 4


# --------------------------------------------------------------------------- #
# 17-20: the CI receipt.
# --------------------------------------------------------------------------- #

class TestReceipt:
    def test_a_good_receipt_satisfies_the_policy(self):
        assert CI.receipt_problems(_receipt(), required=_required(),
                                   source_commit="c" * 40,
                                   candidate_digest="sha256:" + "d" * 64,
                                   dependency=CI.dependency_digest()) == []

    def test_case_17_a_stale_receipt_is_rejected(self):
        old = _receipt(ended_at="2020-01-01T00:00:00Z")
        problems = CI.receipt_problems(old, required=_required(), source_commit="c" * 40)
        assert any(p.startswith(CI.RECEIPT_STALE) for p in problems)

    def test_case_18_a_receipt_for_another_candidate_is_rejected(self):
        problems = CI.receipt_problems(_receipt(), required=_required(),
                                       candidate_digest="sha256:" + "e" * 64)
        assert any(p.startswith(CI.RECEIPT_WRONG_CANDIDATE) for p in problems)

    def test_case_18b_a_receipt_for_another_commit_is_rejected(self):
        problems = CI.receipt_problems(_receipt(), required=_required(), source_commit="a" * 40)
        assert any(p.startswith(CI.RECEIPT_WRONG_COMMIT) for p in problems)

    def test_case_19_a_wrong_dependency_digest_is_rejected(self):
        problems = CI.receipt_problems(_receipt(), required=_required(),
                                       dependency="sha256:" + "0" * 64)
        assert any(p.startswith(CI.RECEIPT_WRONG_DEPENDENCY_DIGEST) for p in problems)

    def test_case_20_an_incomplete_receipt_is_rejected(self):
        for field in ("ci_run_id", "environment", "receipt_digest"):
            problems = CI.receipt_problems(_receipt(**{field: ""}), required=_required())
            assert any(p.startswith(CI.RECEIPT_INCOMPLETE) for p in problems), field
        assert any(p.startswith(CI.RECEIPT_INCOMPLETE)
                   for p in CI.receipt_problems(None, required=_required()))

    def test_a_tampered_receipt_does_not_hash_to_itself(self):
        receipt = _receipt()
        receipt["true_new_failures"] = []
        receipt["counts"] = {"tests": 999999}
        problems = CI.receipt_problems(receipt, required=_required())
        assert any("does not hash to its own contents" in p for p in problems)

    def test_incomplete_shards_or_nodes_are_rejected(self):
        assert any(p.startswith(CI.RECEIPT_SHARDS_INCOMPLETE)
                   for p in CI.receipt_problems(_receipt(shards_completed=["1"]),
                                                required=_required((1, 2))))
        bad = _receipt()
        bad["node_completeness"] = OrderedDict((("complete", False), ("problems", [])))
        assert any(p.startswith(CI.RECEIPT_NODES_INCOMPLETE)
                   for p in CI.receipt_problems(bad, required=_required()))

    def test_a_data_only_release_is_not_missing_a_receipt(self):
        """NOT_REQUIRED_BY_POLICY is a decision; MISSING would be a gap."""
        none_required = OrderedDict((("shards_required", []), ("REMOTE_BROAD_JOBS", 0),
                                     ("reasons", [OrderedDict((("why", "data only"),))])))
        assert CI.receipt_problems(None, required=none_required) == []
        state = CI.broad_validation_state(none_required, None)
        assert state["state"] == CI.NOT_REQUIRED_BY_POLICY and state["REMOTE_BROAD_JOBS"] == 0


# --------------------------------------------------------------------------- #
# 21-24, 29: the queue and the activation lease.
# --------------------------------------------------------------------------- #

class TestQueue:
    def test_case_22_a_duplicate_submission_is_idempotent(self, tmp_path):
        queue = RQ.ReleaseQueue(tmp_path / "q")
        first = queue.submit(market_id="dayton-oh", package_digest="sha256:abc")
        second = queue.submit(market_id="dayton-oh", package_digest="sha256:abc")
        assert first["entry_id"] == second["entry_id"]
        assert len(queue.entries()) == 1
        assert second["resubmissions"] == 1

    def test_case_23_supersession_is_explicit_and_refused_once_work_started(self, tmp_path):
        queue = RQ.ReleaseQueue(tmp_path / "q")
        old = queue.submit(market_id="dayton-oh", package_digest="sha256:old")
        new = queue.submit(market_id="dayton-oh", package_digest="sha256:new")
        assert len(queue.entries()) == 2, "a newer package does not silently replace an older one"
        queue.supersede(old_entry=old["entry_id"], new_entry=new["entry_id"], reason="newer package")
        assert queue.get(old["entry_id"])["state"] == RQ.SUPERSEDED
        assert queue.get(new["entry_id"])["supersedes"] == old["entry_id"]

        started = queue.submit(market_id="cleveland-akron-canton-oh", package_digest="sha256:a")
        newer = queue.submit(market_id="cleveland-akron-canton-oh", package_digest="sha256:b")
        queue.transition(started["entry_id"], RQ.VALIDATING)
        with pytest.raises(RQ.QueueError) as exc:
            queue.supersede(old_entry=started["entry_id"], new_entry=newer["entry_id"])
        assert exc.value.code == RQ.SUPERSEDE_REFUSED

    def test_case_24_activation_is_serialized_by_a_lease(self, tmp_path):
        queue = RQ.ReleaseQueue(tmp_path / "q")
        held = queue.acquire_activation("release-A")
        assert held["holder"] == "release-A"
        with pytest.raises(RQ.QueueError) as exc:
            queue.acquire_activation("release-B")
        assert exc.value.code == RQ.LEASE_HELD
        # Re-acquiring as the same holder is not a second lease.
        assert queue.acquire_activation("release-A")["holder"] == "release-A"
        queue.release_activation("release-A")
        assert queue.acquire_activation("release-B")["holder"] == "release-B"

    def test_an_expired_lease_does_not_block_the_factory_forever(self, tmp_path):
        queue = RQ.ReleaseQueue(tmp_path / "q")
        queue.acquire_activation("crashed", ttl_seconds=1, now=1000.0)
        taken = queue.acquire_activation("next", now=2000.0)
        assert taken["holder"] == "next" and taken["took_over_from"] == "crashed"

    def test_case_29_preparation_overlaps_while_activation_serialises(self, tmp_path):
        """Release B may validate and stage while A holds the activation lease."""
        queue = RQ.ReleaseQueue(tmp_path / "q")
        a = queue.submit(market_id="dayton-oh", package_digest="sha256:a")
        b = queue.submit(market_id="cleveland-akron-canton-oh", package_digest="sha256:b")
        queue.transition(a["entry_id"], RQ.VALIDATING)
        queue.transition(a["entry_id"], RQ.CANDIDATE_STAGED)
        queue.transition(a["entry_id"], RQ.AWAITING_AUTHORIZATION)
        queue.transition(a["entry_id"], RQ.AUTHORIZED)
        queue.acquire_activation(a["entry_id"])
        queue.transition(a["entry_id"], RQ.ACTIVATING)
        # B keeps working: only the flip is serialised.
        queue.transition(b["entry_id"], RQ.VALIDATING)
        staged = queue.transition(b["entry_id"], RQ.CANDIDATE_STAGED)
        assert staged["state"] == RQ.CANDIDATE_STAGED
        with pytest.raises(RQ.QueueError):
            queue.acquire_activation(b["entry_id"])

    def test_an_illegal_transition_is_refused(self, tmp_path):
        queue = RQ.ReleaseQueue(tmp_path / "q")
        entry = queue.submit(market_id="dayton-oh", package_digest="sha256:a")
        with pytest.raises(RQ.QueueError) as exc:
            queue.transition(entry["entry_id"], RQ.LIVE)
        assert exc.value.code == RQ.ILLEGAL_TRANSITION


# --------------------------------------------------------------------------- #
# 25-27: restage after the parent moves.
# --------------------------------------------------------------------------- #

class TestRestage:
    def test_cases_25_26_27_a_stale_candidate_restages_on_the_new_parent(self, tmp_path):
        queue = RQ.ReleaseQueue(tmp_path / "q")
        entry = queue.submit(market_id="cleveland-akron-canton-oh", package_digest="sha256:b")
        for state in (RQ.VALIDATING, RQ.CANDIDATE_STAGED, RQ.AWAITING_AUTHORIZATION, RQ.AUTHORIZED):
            queue.transition(entry["entry_id"], state)
        # Release A went live: B's parent moved, so B goes back to staging and
        # its authorization does not follow it.
        restaged = queue.transition(entry["entry_id"], RQ.CANDIDATE_STAGED,
                                    parent_at_stage="sha256:new-parent",
                                    authorization=None, note="STALE_PARENT: restaged")
        assert restaged["state"] == RQ.CANDIDATE_STAGED
        assert restaged["authorization"] is None
        assert restaged["parent_at_stage"] == "sha256:new-parent"

    def test_case_27_unchanged_bundles_remain_reusable_after_a_restage(self):
        """A restage changes the parent, not the markets that did not move --
        so 004's cache and 005's release store still answer for them."""
        pilot = json.loads((REPORTS / "atlas_throughput_005_pilot_run.json")
                           .read_text(encoding="utf-8-sig"))
        assert pilot["data_only"]["bundles_reused"] == pilot["data_only"]["bundles_total"] - 1
        assert pilot["data_only"]["bundles_rebuilt"] == 0
        assert pilot["stale_lineage"]["rebuilt"] == 0


# --------------------------------------------------------------------------- #
# 28-31: activation, HTTP verification, rollback.
# --------------------------------------------------------------------------- #

class TestActivationAndVerification:
    def test_case_28_an_activation_timeout_is_unknown_and_reconciled(self, tmp_path):
        import subprocess

        def timing_out(argv):
            raise subprocess.TimeoutExpired(argv, 1)

        host = LV.NetlifyHost(enabled=True, authorised_markets=["dayton-oh"], runner=timing_out)
        os.environ["NETLIFY_SITE_ID"] = "test-site"
        try:
            result = host.deploy(tmp_path, market_id="dayton-oh", authorised=True)
        finally:
            os.environ.pop("NETLIFY_SITE_ID", None)
        assert result["outcome"] == LV.UNKNOWN
        assert "reconciled" in result["detail"]

    def test_case_29_an_http_timeout_is_unknown_not_a_failure(self):
        def always_timeout(url):
            raise TimeoutError("no answer")

        probe = LV.HTTPProbe(fetch=always_timeout, retries=1, sleep=lambda _s: None)
        result = probe.get("https://example.invalid/x")
        assert result["outcome"] == LV.UNKNOWN
        assert "not a failure" in result["detail"]

    def test_the_nine_checks_pass_against_a_served_release(self):
        manifest = OrderedDict((
            ("participating_markets", ["dayton-oh", "columbus-oh"]),
            ("intended_delta", OrderedDict((("market_id", "dayton-oh"),))),
            ("sitemap_route_count", 2),
        ))
        served = {
            "/sitemap.xml": b"<urlset><loc>https://x/pet-friendly-hotels/dayton-oh/</loc>"
                            b"<loc>https://x/pet-friendly-hotels/columbus-oh/</loc></urlset>",
            "/pet-friendly-hotels/dayton-oh/": b"<html>dayton</html>",
            "/pet-friendly-hotels/columbus-oh/": b"<html>columbus</html>",
            "/robots.txt": b"User-agent: *",
        }
        probe = LV.HTTPProbe(fetch=lambda url: served.get(url.replace("https://x", "")))
        result = LV.verify_release(manifest, base_url="https://x", probe=probe,
                                   expected_deploy_id="a" * 24,
                                   host_state={"host_deployment_id": "a" * 24})
        assert result["outcome"] == LV.OK and result["passed"] is True
        assert set(result["checks"]) == {
            "release_marker", "membership", "sitemap_includes_changed_market",
            "changed_market_hub", "changed_market_profiles", "unrelated_market_sample",
            "unrelated_route_count", "asset_integrity", "host_deployment_id"}

    def test_case_30_only_a_definite_failure_permits_a_rollback(self):
        manifest = OrderedDict((("participating_markets", ["dayton-oh"]),
                                ("intended_delta", OrderedDict((("market_id", "dayton-oh"),))),
                                ("sitemap_route_count", 1)))
        missing = LV.HTTPProbe(fetch=lambda url: None)
        failed = LV.verify_release(manifest, base_url="https://x", probe=missing)
        assert failed["outcome"] == LV.FAILED and failed["rollback_permitted"] is True

        def timeout(url):
            raise TimeoutError()

        unknown = LV.verify_release(manifest, base_url="https://x",
                                    probe=LV.HTTPProbe(fetch=timeout, retries=0,
                                                       sleep=lambda _s: None))
        assert unknown["outcome"] == LV.UNKNOWN
        assert unknown["rollback_permitted"] is False, "UNKNOWN must not trigger a rollback"

    def test_case_31_a_stale_rollback_is_still_refused(self, tmp_path):
        """005's guard, unchanged by 006's real adapter."""
        store = RC.ReleaseStore(tmp_path / "store")
        host = RC.SimulatedHost(tmp_path / "host", live_release="sha256:newer")
        result = RC.rollback(to_release_digest="sha256:old", expected_current="sha256:what-i-thought",
                             host=host, store=store, work_dir=tmp_path / "rb")
        assert result["refusal"] == RC.RELEASE_NOT_CURRENT


# --------------------------------------------------------------------------- #
# 21, 32: the production gate.
# --------------------------------------------------------------------------- #

class TestProductionGate:
    def test_case_32_the_committed_gate_is_empty_so_nothing_can_deploy(self):
        gate = RC.load_production_gate()
        assert gate["RELEASE_COORDINATOR_PRODUCTION_ENABLED"] == "NO"
        assert gate["RELEASE_COORDINATOR_PRODUCTION_ALLOWED_MARKETS"] == []
        allowed, why = RC.production_activation_allowed("dayton-oh", gate)
        assert allowed is False and why.startswith(RC.PRODUCTION_GATE_CLOSED)

    def test_a_missing_gate_file_is_a_closed_gate(self, tmp_path):
        gate = RC.load_production_gate(tmp_path / "absent.json")
        assert gate["RELEASE_COORDINATOR_PRODUCTION_ENABLED"] == "NO"
        assert RC.production_activation_allowed("dayton-oh", gate)[0] is False

    def test_a_market_outside_the_allowlist_is_refused(self):
        gate = OrderedDict((("RELEASE_COORDINATOR_PRODUCTION_ENABLED", "YES"),
                            ("RELEASE_COORDINATOR_PRODUCTION_ALLOWED_MARKETS", ["lexington-ky"])))
        assert RC.production_activation_allowed("dayton-oh", gate)[0] is False
        assert RC.production_activation_allowed("lexington-ky", gate)[0] is True

    def test_the_host_adapter_refuses_while_disabled(self, tmp_path):
        host = LV.NetlifyHost()
        result = host.deploy(tmp_path, market_id="dayton-oh", authorised=True)
        assert result["outcome"] == LV.REFUSED and result["refusal"] == LV.HOST_DISABLED
        # It still shows exactly what it WOULD run, so the plan is reviewable.
        assert result["command"][:3] == ["netlify", "deploy", "--prod"]
        assert "--no-build" in result["command"]

    def test_the_host_adapter_refuses_a_market_outside_the_allowlist(self, tmp_path):
        host = LV.NetlifyHost(enabled=True, authorised_markets=["lexington-ky"])
        result = host.deploy(tmp_path, market_id="dayton-oh", authorised=True)
        assert result["outcome"] == LV.REFUSED and result["refusal"] == LV.NOT_AUTHORISED

    def test_case_21_a_source_ready_market_still_cannot_enter_a_release(self):
        """005's membership rule, restated here because 006 adds a queue that
        could otherwise look like a way in."""
        live = type("L", (), {"participating_markets": ("dayton-oh",), "verified": True,
                              "problems": (), "digest": lambda self: "sha256:now"})()
        doc = {"markets": [{"market_id": "dayton-oh", "launch_status": "FOUNDER_AUTHORIZED_FOR_LAUNCH"},
                           {"market_id": "lexington-ky", "launch_status": "FOUNDER_AUTHORIZED_FOR_LAUNCH"}]}
        with pytest.raises(RC.CoordinatorError) as exc:
            RC._final_membership(live, doc, RC.UPDATE, "dayton-oh", {})
        assert exc.value.code == RC.UNAUTHORIZED_ADDITION


# --------------------------------------------------------------------------- #
# The shard plan itself.
# --------------------------------------------------------------------------- #

class TestShardPlan:
    def test_the_plan_is_measured_not_guessed(self, manifest):
        assert manifest["measured_total_seconds"] > 3000
        assert manifest["balanced_by"].startswith("measured wall-clock duration")
        assert "test count" in manifest["not_balanced_by"]

    def test_the_critical_path_is_named(self, manifest):
        """The manifest must always name its slowest indivisible module and
        never project a wall below it.

        Before ATLAS-THROUGHPUT-007 that module WAS the critical path: demo-media
        at 1,375.7 s exceeded a perfect quarter of the suite, so the wall equalled
        it exactly. 007 split demo-media, and the plan became work-bound instead:
        the wall is now the balanced share, which is ABOVE the slowest module.
        Both states satisfy the property this asserts, which is why it is written
        as the property."""
        critical = manifest["critical_path"]
        assert critical["module"] and critical["seconds"] > 0
        assert manifest["projected_wall_seconds"] >= critical["seconds"]
        share = manifest["measured_total_seconds"] / manifest["shard_count"]
        assert manifest["projected_wall_seconds"] >= share * 0.98

    def test_the_plan_is_work_bound_after_the_007_split(self, manifest):
        """A single module no longer dictates the wall clock."""
        critical = manifest["critical_path"]
        share = manifest["measured_total_seconds"] / manifest["shard_count"]
        assert critical["seconds"] < share, (
            "the slowest module is below the balanced share, so adding work to "
            "the plan -- not splitting another module -- is what moves the wall now")

    def test_no_number_of_shards_beats_the_slowest_module(self):
        """The enduring property: a sharded run waits for its slowest
        indivisible unit, however many runners it is given.

        Before 007 this bit at four shards, because demo-media alone exceeded a
        quarter of the suite. After the split it bites later -- but it still
        bites, and that is what a plan must never pretend otherwise about."""
        profile = REPO_PROFILE
        if not profile.is_file():
            pytest.skip("no committed profiler run")
        measurements = CI.load_measurements(profile)
        slowest = max(m.seconds for m in measurements.values())
        for count in (4, 8, 16, 64):
            wall = CI.plan_shards(measurements, shard_count=count)["projected_wall_seconds"]
            assert wall >= round(slowest, 1) - 0.05, count
        # With more shards than heavy modules the wall IS the slowest module.
        assert abs(CI.plan_shards(measurements, shard_count=64)["projected_wall_seconds"]
                   - slowest) < 0.05

    def test_every_module_lands_in_exactly_one_shard(self, manifest):
        seen = {}
        for shard in manifest["shards"]:
            for module in shard["modules"]:
                assert module not in seen, (module, shard["shard"], seen.get(module))
                seen[module] = shard["shard"]
        assert len(seen) == manifest["modules"]

    def test_the_shards_are_balanced_within_reason(self, manifest):
        others = sorted(s["seconds"] for s in manifest["shards"])[:-1]
        assert max(others) - min(others) < 60, "the non-critical shards are balanced"


REPO_PROFILE = SMP.REPO_ROOT / "data" / "regression" / "atlas-throughput-005-audit" / "profile.jsonl"
