# -*- coding: utf-8 -*-
"""ATLAS-THROUGHPUT-004 -- the persistent content-addressed market-bundle
cache: the canonical build input manifest, trusted publication, the lookup
rule, corruption handling, atomic publication, per-key locking, the
invalidation matrix, the artifact-vs-receipt lifecycle, and the boundaries
(cache hit is not release authorization; production does not consume it).

Fast cases use a stub builder (the cache's contract, not the generator's);
the cases marked ``slow`` execute real cold builds of the Dayton pilot package
and prove the cross-run hit in a SEPARATE PROCESS with builds forbidden.
Case numbers follow the order's Phase 27 matrix (1-25).
"""

from __future__ import annotations

import copy
import json
import os
import shutil
import subprocess
import sys
import threading
import time
from collections import OrderedDict
from pathlib import Path

import pytest

from scripts.pettripfinder import atlas_throughput_004_pilot as P4
from scripts.pettripfinder import bundle_cache as BC
from scripts.pettripfinder import fast_release_lane as FL
from scripts.pettripfinder import first_party_binding as FPB
from scripts.pettripfinder import regression_delta as RD
from scripts.pettripfinder import sealed_market_package as SMP

REPO_ROOT = Path(__file__).resolve().parents[2]
REPORTS = REPO_ROOT / "launch_packages" / "pettripfinder" / "reports"
SHORT_ROOT = Path(os.environ.get("PTF_TEST_SHORT_ROOT", r"C:\ptf004\t4") if sys.platform == "win32" else "/tmp/ptf004")


@pytest.fixture(scope="module")
def dayton():
    return P4.dayton_package()


@pytest.fixture
def cache(tmp_path):
    return BC.BundleCache(tmp_path / "cache", run_id="test")


def _stub_cache(tmp_path, package, **kw):
    cache = BC.BundleCache(tmp_path / "cache", run_id="test")
    builder = P4.stub_builder(sleep=0.05)
    result = cache.build_or_reuse(package, work_dir=tmp_path / "w1", require_determinism=True, builder=builder, **kw)
    return cache, builder, result


# --------------------------------------------------------------------------- #
# The manifest and key.
# --------------------------------------------------------------------------- #

class TestBuildInputManifest:
    def test_the_manifest_carries_every_declared_input_and_is_canonical(self, dayton, cache, tmp_path):
        manifest, key, staged = cache.manifest_for(dayton, tmp_path / "m")
        for field in ("package_digest", "market_id", "authority_digest", "route_digest", "policy_digest",
                      "evidence_manifest_digest", "geography_identity_digest", "render_input_digest",
                      "market_config_digest", "builder_digest", "assembler_digest",
                      "shared_runtime_dependency_digest", "template_digest", "asset_digest",
                      "toolchain", "build_arguments", "locale", "env_inputs", "validation_policy_version",
                      "contract_versions"):
            assert field in manifest, field
        assert manifest["toolchain"]["lockfiles"]["requirements.txt"].startswith("sha256:")
        assert manifest["toolchain"]["python_version"] and "node_version" in manifest["toolchain"]
        assert manifest["shared_runtime_modules"] == len(cache.closure["code_modules"])
        assert key.startswith("sha256:") and key == BC.build_input_key(manifest)
        again, key2, _ = cache.manifest_for(dayton, tmp_path / "m2")
        assert key2 == key                                            # stable across work dirs
        assert SMP.canonical_json(manifest) == SMP.canonical_json(again)

    def test_the_output_digest_is_not_an_input_and_policy_is_outside_the_byte_key(self, dayton, cache, tmp_path, monkeypatch):
        manifest, key, _ = cache.manifest_for(dayton, tmp_path / "m")
        assert "output" not in SMP.canonical_json(OrderedDict((k, manifest[k]) for k in BC.KEY_FIELDS))
        assert "validation_policy_version" not in BC.KEY_FIELDS
        monkeypatch.setattr(BC, "VALIDATION_POLICY", "ptf-bundle-validation/9.9")
        manifest2, key2, _ = cache.manifest_for(dayton, tmp_path / "m3")
        assert key2 == key and manifest2["validation_policy_version"] != manifest["validation_policy_version"]

    def test_every_declared_input_changes_the_key(self, dayton, cache, tmp_path):
        base, key, _ = cache.manifest_for(dayton, tmp_path / "m")
        for field in BC.KEY_FIELDS:
            if field in ("schema", "kind"):
                continue
            mutated = copy.deepcopy(base)
            mutated[field] = "changed" if not isinstance(mutated[field], dict) else dict(mutated[field], changed=1)
            assert BC.build_input_key(mutated) != key, field

    def test_an_unknown_or_missing_closure_module_fails_closed(self, dayton, tmp_path):
        closure = copy.deepcopy(BC.load_closure())
        closure["code_modules"].append("scripts/pettripfinder/does_not_exist.py")
        cache = BC.BundleCache(tmp_path / "cache", run_id="t", closure=closure)
        with pytest.raises(BC.BundleCacheError, match="missing module"):
            cache.manifest_for(dayton, tmp_path / "m")
        bad = copy.deepcopy(BC.load_closure())
        bad["code_modules"] = []
        bad_path = tmp_path / "closure.json"
        bad_path.write_text(json.dumps(bad), encoding="utf-8")
        with pytest.raises(BC.BundleCacheError, match="code_modules"):
            BC.load_closure(bad_path)

    def test_the_committed_closure_is_the_measured_one(self):
        closure = BC.load_closure()
        assert closure["measured_from"] == ["dayton-oh", "cleveland-akron-canton-oh"]
        assert "scripts/generate_pettripfinder_columbus_site.py" in closure["code_modules"]
        assert "scripts/pettripfinder/assemble_netlify_bundle.py" in closure["code_modules"]
        assert "launch_packages/pettripfinder/seed_businesses.csv" in closure["shared_data_inputs"]
        assert "scripts/pettripfinder/approved_hotel_profile.css" in closure["shared_data_inputs"]
        assert all((REPO_ROOT / p).is_file() for p in closure["code_modules"] + closure["shared_data_inputs"])


# --------------------------------------------------------------------------- #
# Publication, lookup, trust (stub builder).
# --------------------------------------------------------------------------- #

class TestPublicationAndLookup:
    def test_case_1_cold_build_publishes_a_trusted_entry(self, dayton, tmp_path):
        cache, builder, r = _stub_cache(tmp_path, dayton)
        assert r["cache_status"] == BC.MISS and r["builder_invocations"] == 2 and r["trust_state"] == BC.TRUSTED
        entry = cache.read_entry(r["build_input_key"])
        assert entry["trust_state"] == BC.TRUSTED and cache.object_path(entry["output_bundle_digest"]).is_file()
        receipt = cache.read_receipt(entry["validation_receipt_digest"])
        assert receipt["output_bundle_digest"] == "sha256:" + r["bundle_sha256"]
        assert receipt["results"]["determinism"]["result"] == "BYTE_IDENTICAL"
        assert list((cache.root / "tmp").iterdir()) == []

    def test_case_3_and_4_a_hit_invokes_no_builder_and_verifies_the_digest(self, dayton, tmp_path):
        cache, builder, r = _stub_cache(tmp_path, dayton)
        calls = len(builder.calls)
        r2 = cache.build_or_reuse(dayton, work_dir=tmp_path / "w2", builder=builder)
        assert r2["cache_status"] == BC.HIT and r2["builder_invocations"] == 0 and len(builder.calls) == calls
        assert r2["bundle_sha256"] == r["bundle_sha256"]
        from scripts.pettripfinder.assemble_production_site import bundle_digest, file_hashes
        assert bundle_digest(file_hashes(Path(r2["output_dir"]) / "site")) == r["bundle_sha256"]
        assert r2["verify_seconds"] is not None

    def test_case_19_a_failed_build_is_never_published_trusted(self, dayton, tmp_path):
        cache = BC.BundleCache(tmp_path / "cache", run_id="t")

        def failing(package, *a, **k):
            raise RuntimeError("generator exploded")
        with pytest.raises(RuntimeError):
            cache.build_or_reuse(dayton, work_dir=tmp_path / "w", builder=failing)
        assert cache.entries() == [] and list((cache.root / "objects").iterdir()) == []

    def test_a_build_with_failing_gates_or_undeclared_reads_is_untrusted(self, dayton, tmp_path):
        base = P4.stub_builder(sleep=0.01)

        def gated(package, stage, out, **k):
            r = base(package, stage, out, **k)
            r["gates_failing"] = ["content.zero_broken_links"]
            return r
        cache = BC.BundleCache(tmp_path / "cache", run_id="t")
        r = cache.build_or_reuse(dayton, work_dir=tmp_path / "w", builder=gated, require_determinism=False)
        assert r["trust_state"] == BC.UNTRUSTED and any("gates" in p for p in r["untrusted_because"])
        r2 = cache.build_or_reuse(dayton, work_dir=tmp_path / "w2", builder=gated, require_determinism=False)
        assert r2["cache_status"] == BC.MISS                      # an UNTRUSTED entry never satisfies a lookup

        def reading(package, stage, out, **k):
            (REPO_ROOT / "pytest.ini").read_text(encoding="utf-8")   # a repo file outside the closure
            return base(package, stage, out, **k)
        cache2 = BC.BundleCache(tmp_path / "cache2", run_id="t")
        r3 = cache2.build_or_reuse(dayton, work_dir=tmp_path / "w3", builder=reading, require_determinism=False)
        assert r3["trust_state"] == BC.UNTRUSTED
        assert "pytest.ini" in r3["undeclared_dependencies"]["data"]

    def test_case_23_an_unknown_dependency_fails_closed(self, dayton, tmp_path):
        """A build that reads a repository file the closure does not declare is
        never trusted: the key cannot cover it, so a hit could be wrong."""
        base = P4.stub_builder(sleep=0.01)

        def reading(package, stage, out, **k):
            (REPO_ROOT / "docs" / "PTF_HARDENED_FACTORY_RUNBOOK.md").read_text(encoding="utf-8")
            return base(package, stage, out, **k)
        cache = BC.BundleCache(tmp_path / "cache", run_id="t")
        r = cache.build_or_reuse(dayton, work_dir=tmp_path / "w", builder=reading)
        assert r["trust_state"] == BC.UNTRUSTED and "docs/PTF_HARDENED_FACTORY_RUNBOOK.md" in r["undeclared_dependencies"]["data"]
        assert cache.build_or_reuse(dayton, work_dir=tmp_path / "w2", builder=reading)["cache_status"] == BC.MISS

    def test_case_18_cold_required_bypasses_the_cache(self, dayton, tmp_path):
        cache, builder, r = _stub_cache(tmp_path, dayton)
        calls = len(builder.calls)
        r2 = cache.build_or_reuse(dayton, work_dir=tmp_path / "w2", builder=builder, cold_required=True)
        assert r2["cache_status"] == BC.BYPASS_COLD_REQUIRED and r2["builder_invocations"] == 2
        assert len(builder.calls) == calls + 2
        assert any(e["cache_status"] == BC.BYPASS_COLD_REQUIRED for e in BC.EVENTS)

    def test_the_artifact_is_immutable_under_its_digest(self, dayton, tmp_path):
        cache, builder, r = _stub_cache(tmp_path, dayton)
        archive = cache.object_path(r["bundle_sha256"])
        before = archive.read_bytes()
        cache.build_or_reuse(dayton, work_dir=tmp_path / "w2", builder=builder, cold_required=True)
        assert archive.read_bytes() == before

    def test_a_planted_artifact_is_not_a_trusted_entry(self, dayton, tmp_path):
        """Copying bytes into the cache directory grants nothing: without an
        index row written by the publisher and a receipt that binds it, a
        lookup is a miss."""
        cache = BC.BundleCache(tmp_path / "cache", run_id="t")
        manifest, key, _ = cache.manifest_for(dayton, tmp_path / "m")
        cache.object_path("sha256:" + "a" * 64).write_bytes(b"PK\x05\x06" + b"\x00" * 18)
        assert cache.read_entry(key) is None
        # A hand-written index row without a receipt is quarantined on lookup.
        cache.index_path(key).write_text(json.dumps(OrderedDict((
            ("schema", BC.ENTRY_SCHEMA), ("build_input_key", key), ("trust_state", BC.TRUSTED),
            ("output_bundle_digest", "sha256:" + "a" * 64), ("archive_sha256", "sha256:" + "b" * 64),
            ("archive_bytes", 22), ("validation_receipt_digest", "sha256:" + "c" * 64)))), encoding="utf-8")
        entry = cache.read_entry(key)
        status, _ = cache.verify(key, entry, tmp_path / "out")
        assert status == BC.INVALID_CORRUPT
        assert cache.read_entry(key) is None and list((cache.root / "quarantine").iterdir())


# --------------------------------------------------------------------------- #
# Corruption handling.
# --------------------------------------------------------------------------- #

class TestCorruption:
    @pytest.mark.parametrize("damage,expect_quarantine", [
        ("flip", True), ("delete", True), ("zero", True), ("receipt", True), ("receipt_other", True), ("index", True),
    ])
    def test_cases_12_13_14_15_corrupt_or_incomplete_cache_data_fails_closed(self, dayton, tmp_path, damage, expect_quarantine):
        cache, builder, r = _stub_cache(tmp_path, dayton)
        P4._damage(cache.root, r["build_input_key"], damage)
        calls = len(builder.calls)
        r2 = cache.build_or_reuse(dayton, work_dir=tmp_path / "w2", builder=builder)
        assert r2["cache_status"] in (BC.MISS, BC.INVALID_CORRUPT), damage
        assert len(builder.calls) > calls                              # rebuilt, never served
        assert r2["bundle_sha256"] == r["bundle_sha256"]
        if damage != "index":
            assert list((cache.root / "quarantine").iterdir()), damage

    def test_metadata_digest_mismatch_and_wrong_input_key_are_misses(self, dayton, tmp_path):
        cache, builder, r = _stub_cache(tmp_path, dayton)
        entry = cache.read_entry(r["build_input_key"])
        entry["archive_sha256"] = "sha256:" + "0" * 64
        cache.index_path(r["build_input_key"]).write_text(json.dumps(entry), encoding="utf-8")
        assert cache.build_or_reuse(dayton, work_dir=tmp_path / "w2", builder=builder)["cache_status"] == BC.INVALID_CORRUPT
        entry = cache.read_entry(r["build_input_key"])
        entry["build_input_key"] = "sha256:" + "1" * 64
        cache.index_path(r["build_input_key"]).write_text(json.dumps(entry), encoding="utf-8")
        assert cache.read_entry(r["build_input_key"]) is None

    def test_case_20_an_interrupted_publication_is_not_visible(self, dayton, tmp_path, monkeypatch):
        cache = BC.BundleCache(tmp_path / "cache", run_id="t")
        builder = P4.stub_builder(sleep=0.01)
        real_replace = os.replace
        calls = {"n": 0}

        def crashing_replace(src, dst):
            calls["n"] += 1
            if str(dst).endswith(".zip"):
                raise OSError("power loss during publication")
            return real_replace(src, dst)
        monkeypatch.setattr(os, "replace", crashing_replace)
        with pytest.raises(OSError):
            cache.build_or_reuse(dayton, work_dir=tmp_path / "w", builder=builder, require_determinism=False)
        monkeypatch.setattr(os, "replace", real_replace)
        assert cache.entries() == [] and list((cache.root / "objects").iterdir()) == []
        assert list((cache.root / "receipts").iterdir()) == []
        r = cache.build_or_reuse(dayton, work_dir=tmp_path / "w2", builder=builder, require_determinism=False)
        assert r["cache_status"] == BC.MISS and r["trust_state"] == BC.TRUSTED

    def test_receipt_binding_requires_key_digest_policy_and_dependencies(self, dayton, tmp_path):
        cache, builder, r = _stub_cache(tmp_path, dayton)
        entry = cache.read_entry(r["build_input_key"])
        receipt = cache.read_receipt(entry["validation_receipt_digest"])
        assert BC.receipt_binding_problems(receipt, key=r["build_input_key"], bundle_sha256=entry["output_bundle_digest"],
                                           manifest_dependencies=entry["dependency"]) == []
        other = dict(receipt, build_input_key="sha256:" + "9" * 64)
        assert BC.receipt_binding_problems(other, key=r["build_input_key"], bundle_sha256=entry["output_bundle_digest"],
                                           manifest_dependencies=entry["dependency"])
        dep = dict(entry["dependency"], builder_digest="sha256:" + "8" * 64)
        assert any("builder_digest" in p for p in BC.receipt_binding_problems(
            receipt, key=r["build_input_key"], bundle_sha256=entry["output_bundle_digest"], manifest_dependencies=dep))


# --------------------------------------------------------------------------- #
# Concurrency.
# --------------------------------------------------------------------------- #

class TestConcurrency:
    def test_case_16_and_17_same_key_builds_once_different_keys_proceed(self, dayton, tmp_path):
        live = None
        b = copy.deepcopy(dayton)
        b["market_id"] = "dayton-oh"
        # Two other packages: the same market with a changed policy digest is enough for a different key.
        other1 = SMP.seal(dict(SMP.body_of(dayton), founder_holds=[{"hold_id": "x1"}]), sealed_at="2026-09-08T00:00:00Z")
        other2 = SMP.seal(dict(SMP.body_of(dayton), founder_holds=[{"hold_id": "x2"}]), sealed_at="2026-09-08T00:00:00Z")
        report = P4.concurrency_proof(tmp_path / "cache", tmp_path / "work", [dayton, other1, other2])
        assert report["same_key"]["BUILD_EXECUTED"] == 1
        assert report["same_key"]["REUSE_AFTER_WAIT"] == 1 and report["same_key"]["digests_equal"]
        assert report["different_keys"]["BUILD_EXECUTED"] == 2 and report["different_keys"]["concurrent"]

    def test_a_stale_lock_from_a_dead_holder_is_broken(self, dayton, tmp_path):
        cache = BC.BundleCache(tmp_path / "cache", run_id="t")
        manifest, key, _ = cache.manifest_for(dayton, tmp_path / "m")
        lock = cache.lock_path(key)
        lock.write_text("dead", encoding="utf-8")
        old = time.time() - 10_000
        os.utime(lock, (old, old))
        builder = P4.stub_builder(sleep=0.01)
        r = cache.build_or_reuse(dayton, work_dir=tmp_path / "w", builder=builder, require_determinism=False)
        assert r["cache_status"] == BC.MISS and not lock.exists()


# --------------------------------------------------------------------------- #
# Invalidation, revalidation, tooling-only, freshness.
# --------------------------------------------------------------------------- #

class TestInvalidation:
    def _seal(self, inputs):
        from scripts.pettripfinder import market_package_writer as W
        return W.build_sealed_package(inputs, sealed_at="2026-09-08T00:00:00Z")

    @pytest.fixture(scope="class")
    def live(self):
        from scripts.pettripfinder import release_index as RI
        return RI.live_index()

    def test_cases_5_6_7_policy_route_geography_changes_invalidate(self, dayton, live, tmp_path):
        from scripts.pettripfinder import atlas_throughput_003_pilot as P3
        cache = BC.BundleCache(tmp_path / "cache", run_id="t")
        base = P3.frozen_inputs("dayton-oh", live)
        _, key0, _ = cache.manifest_for(self._seal(base), tmp_path / "m0")
        for label, mutate in (("policy", P4.mutate_policy), ("route", P4.mutate_route), ("geography", P4.mutate_geography)):
            _, key, _ = cache.manifest_for(self._seal(mutate(base)), tmp_path / ("m_" + label))
            assert key != key0, label

    def test_cases_8_9_10_template_builder_and_tooling_changes(self, dayton, tmp_path):
        closure = BC.load_closure()
        shadow = P4.shadow_repo(tmp_path / "shadow", closure, ["dayton-oh"])
        cache = BC.BundleCache(tmp_path / "cache", run_id="t", repo_root=shadow)
        _, key0, _ = cache.manifest_for(dayton, tmp_path / "m0")
        real = BC.BundleCache(tmp_path / "cache", run_id="t")
        _, key_real, _ = real.manifest_for(dayton, tmp_path / "mr")
        assert key0 == key_real                                       # the shadow IS the closure
        css = shadow / "scripts" / "pettripfinder" / "approved_hotel_profile.css"
        css.write_text(css.read_text(encoding="utf-8") + "\n/* x */\n", encoding="utf-8")
        _, key_tpl, _ = cache.manifest_for(dayton, tmp_path / "m1")
        assert key_tpl != key0                                        # case 8: template
        P4.shadow_repo(tmp_path / "shadow", closure, ["dayton-oh"])
        gen = shadow / "scripts" / "generate_pettripfinder_columbus_site.py"
        gen.write_text(gen.read_text(encoding="utf-8") + "\n# x\n", encoding="utf-8")
        _, key_builder, _ = cache.manifest_for(dayton, tmp_path / "m2")
        assert key_builder != key0                                    # case 9: builder
        P4.shadow_repo(tmp_path / "shadow", closure, ["dayton-oh"])
        tooling = shadow / "scripts" / "pettripfinder" / "dayton_oh_revalidation_999.py"
        tooling.write_text(tooling.read_text(encoding="utf-8") + "\n# x\n", encoding="utf-8")
        _, key_tooling, _ = cache.manifest_for(dayton, tmp_path / "m3")
        assert key_tooling == key0                                    # case 10: tooling only
        req = shadow / "requirements.txt"
        req.write_text(req.read_text(encoding="utf-8") + "\n# lock\n", encoding="utf-8")
        _, key_lock, _ = cache.manifest_for(dayton, tmp_path / "m4")
        assert key_lock != key0                                       # lockfile / toolchain

    def test_case_22_a_shared_dependency_change_invalidates_every_dependent(self, dayton, tmp_path):
        """Two markets, one shared template: both keys move."""
        from scripts.pettripfinder import release_index as RI
        closure = BC.load_closure()
        shadow = P4.shadow_repo(tmp_path / "shadow", closure, ["dayton-oh", P4.FIXTURE_ID])
        fixture = self._seal(P4.fixture_inputs(RI.live_index()))
        cache = BC.BundleCache(tmp_path / "cache", run_id="t", repo_root=shadow)
        _, kd, _ = cache.manifest_for(dayton, tmp_path / "md")
        _, kf, _ = cache.manifest_for(fixture, tmp_path / "mf")
        css = shadow / "scripts" / "pettripfinder" / "approved_hotel_profile.css"
        css.write_text(css.read_text(encoding="utf-8") + "\n/* x */\n", encoding="utf-8")
        _, kd2, _ = cache.manifest_for(dayton, tmp_path / "md2")
        _, kf2, _ = cache.manifest_for(fixture, tmp_path / "mf2")
        assert kd2 != kd and kf2 != kf

    def test_case_11_a_validation_rule_change_revalidates_without_rebuilding(self, dayton, tmp_path, monkeypatch):
        cache, builder, r = _stub_cache(tmp_path, dayton)
        calls = len(builder.calls)
        monkeypatch.setattr(BC, "COMPATIBLE_POLICIES", (BC.VALIDATION_POLICY, "ptf-bundle-validation/1.1"))
        monkeypatch.setattr(BC, "VALIDATION_POLICY", "ptf-bundle-validation/1.1")
        r2 = cache.build_or_reuse(dayton, work_dir=tmp_path / "w2", builder=builder)
        assert r2["cache_status"] == BC.REVALIDATE and len(builder.calls) == calls
        assert r2["bundle_sha256"] == r["bundle_sha256"] and r2["receipt_digest"] != r["receipt_digest"]
        entry = cache.read_entry(r["build_input_key"])
        assert entry["validation_policy_version"] == "ptf-bundle-validation/1.1"
        receipt = cache.read_receipt(entry["validation_receipt_digest"])
        assert receipt["revalidated_from"] == r["receipt_digest"] and receipt["results"]["determinism"]["result"] == "BYTE_IDENTICAL"
        assert cache.build_or_reuse(dayton, work_dir=tmp_path / "w3", builder=builder)["cache_status"] == BC.HIT
        # An INCOMPATIBLE policy can never be satisfied by the old receipt.
        monkeypatch.setattr(BC, "COMPATIBLE_POLICIES", ("ptf-bundle-validation/2.0",))
        monkeypatch.setattr(BC, "VALIDATION_POLICY", "ptf-bundle-validation/2.0")
        r4 = cache.build_or_reuse(dayton, work_dir=tmp_path / "w4", builder=builder)
        assert r4["cache_status"] == BC.INVALID_POLICY_VERSION and len(builder.calls) > calls

    def test_case_24_revoked_or_expired_evidence_cannot_rely_on_a_stale_receipt(self, dayton, tmp_path):
        cache, builder, r = _stub_cache(tmp_path, dayton)
        revoked = {dayton["evidence_references"][0]["artifact_sha256"]: {"reason": "wrong property"}}
        r2 = cache.build_or_reuse(dayton, work_dir=tmp_path / "w2", builder=builder, revocations=revoked)
        assert r2["cache_status"] == BC.INVALID_REVOKED and r2["trust_state"] == BC.UNTRUSTED
        far = FPB.parse_timestamp("2030-01-01T00:00:00Z")
        cache2, builder2, r_fresh = _stub_cache(tmp_path / "fresh", dayton)
        r3 = cache2.build_or_reuse(dayton, work_dir=tmp_path / "w3", builder=builder2, now=far)
        assert r3["cache_status"] == BC.INVALID_REVOKED and r3["trust_state"] == BC.UNTRUSTED
        cache3, builder3, r_ok = _stub_cache(tmp_path / "third", dayton)
        assert cache3.revoke(r_ok["build_input_key"], "pilot")
        r4 = cache3.build_or_reuse(dayton, work_dir=tmp_path / "w4", builder=builder3)
        assert r4["cache_status"] == BC.MISS and r4["trust_state"] == BC.TRUSTED

    def test_a_test_only_change_keeps_the_bytes_reusable(self):
        closure = BC.load_closure()
        assert not any(p.startswith("tests/") for p in closure["code_modules"] + closure["shared_data_inputs"])
        assert not any("bundle_cache_closure" in p for p in closure["shared_data_inputs"])


# --------------------------------------------------------------------------- #
# Boundaries: release authorization, production consumption, V2.
# --------------------------------------------------------------------------- #

class TestBoundaries:
    def test_case_25_a_cache_hit_never_sets_a_release_authorized_or_live(self, dayton, tmp_path):
        cache, builder, r = _stub_cache(tmp_path, dayton)
        r2 = cache.build_or_reuse(dayton, work_dir=tmp_path / "w2", builder=builder)
        assert r2["cache_status"] == BC.HIT
        for forbidden in ("release_authorized", "FAST_DATA_ONLY_RELEASE_ELIGIBLE", "deployment_authorized", "live"):
            assert forbidden not in r2 and forbidden not in cache.read_entry(r["build_input_key"])
        receipt = cache.read_receipt(r["receipt_digest"])
        assert "FAST_DATA_ONLY_RELEASE_ELIGIBLE" not in receipt
        activation = FL.load_activation()
        assert activation["PRODUCTION_RELEASE_CONSUMPTION"] == "DISABLED"
        assert activation["FAST_PATH_PRODUCTION_ACTIVATION"] == "DISABLED"

    def test_the_production_assembler_and_deployer_do_not_import_the_cache(self):
        for rel in ("scripts/pettripfinder/assemble_production_site.py", "scripts/pettripfinder/assemble_netlify_bundle.py",
                    "scripts/pettripfinder/deployment_authorization.py", "scripts/pettripfinder/global_deployment.py",
                    "scripts/generate_pettripfinder_columbus_site.py"):
            assert "bundle_cache" not in (REPO_ROOT / rel).read_text(encoding="utf-8-sig"), rel

    def test_the_fast_lane_reports_market_build_required_no_on_a_trusted_bundle(self, dayton, tmp_path, monkeypatch):
        from scripts.pettripfinder import release_index as RI
        cache, builder, r = _stub_cache(tmp_path, dayton)
        live = RI.live_index()
        receipt = FL.run_fast_lane(dayton, work_dir=tmp_path / "lane", live=live, build=True, determinism=True,
                                   now=FPB.parse_timestamp("2026-09-08T12:00:00Z"), bundle_cache=cache)
        assert receipt["RESULTS"]["J"]["status"] == FL.PASS
        assert receipt["RESULTS"]["J"]["detail"]["MARKET_BUILD_REQUIRED"] == "NO"
        assert receipt["RESULTS"]["J"]["detail"]["cache_status"] == BC.HIT
        assert receipt["RESULTS"]["K"]["status"] == FL.PASS and receipt["RESULTS"]["K"]["detail"]["inherited_from_bundle_receipt"]
        # Release safety rules still ran and still decide.
        for rule in "ABCDEFGHILMNO":
            assert receipt["RESULTS"][rule]["status"] == FL.PASS, rule
        assert receipt["FAST_PATH_PRODUCTION_ACTIVATION"] == "DISABLED"

    def test_regression_v2_reports_market_build_required_from_the_cache(self, dayton, tmp_path, monkeypatch):
        rows = [{"path": "launch_packages/pettripfinder/hotel_policy_facts_dayton-oh.json", "status": "M",
                 "classes": [RD.AUTHORITY_CHANGE], "rule": "r", "why": "", "shared_test_state": False,
                 "markets": [], "market_local_proof": None, "renamed_from": None}]
        monkeypatch.setattr(SMP, "PACKAGES_DIR", tmp_path / "packages")
        monkeypatch.setattr(SMP, "RECEIPTS_DIR", tmp_path / "receipts")
        monkeypatch.setenv(BC.ROOT_ENV, str(tmp_path / "cache"))
        block = RD.fast_data_only_release("dayton-oh", rows, RD.WORKTREE)
        assert block["MARKET_BUILD_REQUIRED"] == "YES"
        # The committed package covers the committed bytes; a trusted bundle for it flips the answer.
        SMP.write_sealed(dayton, tmp_path / "packages")
        block = RD.fast_data_only_release("dayton-oh", rows, RD.WORKTREE)
        assert block["MARKET_BUILD_REQUIRED"] == "YES" and block["package_id"] == dayton["package_id"]
        _stub_cache(tmp_path, dayton)
        block = RD.fast_data_only_release("dayton-oh", rows, RD.WORKTREE)
        assert block["MARKET_BUILD_REQUIRED"] == "NO" and block["bundle_cache"]["trusted"]
        assert block["FULL_REGRESSION_REQUIRED"] == "YES"             # a bundle is not a release proof

    def test_the_closure_file_and_cache_module_block_narrowing(self):
        assert RD.is_narrowing_blocker("scripts/pettripfinder/bundle_cache.py")
        assert RD.is_narrowing_blocker("launch_packages/pettripfinder/bundle_cache_closure.json")
        assert RD.classify_path("launch_packages/pettripfinder/bundle_cache_closure.json")[0] == (RD.DEPLOYMENT_CHANGE,)

    def test_gc_is_a_dry_run_that_protects_release_bundles(self, dayton, tmp_path):
        cache, builder, r = _stub_cache(tmp_path, dayton)
        plan = cache.gc_plan(max_age_days=0, protected_digests=[r["bundle_sha256"]],
                             now=FPB.parse_timestamp("2030-01-01T00:00:00Z"))
        assert plan["dry_run"] and plan["candidates"] == [] and len(plan["protected"]) == 1
        plan2 = cache.gc_plan(max_age_days=0, now=FPB.parse_timestamp("2030-01-01T00:00:00Z"))
        assert len(plan2["candidates"]) == 1
        assert cache.object_path(r["bundle_sha256"]).is_file()      # nothing deleted

    def test_telemetry_records_every_request(self, dayton, tmp_path):
        before = len(BC.EVENTS)
        cache, builder, r = _stub_cache(tmp_path, dayton)
        cache.build_or_reuse(dayton, work_dir=tmp_path / "w2", builder=builder)
        new = BC.EVENTS[before:]
        assert [e["cache_status"] for e in new] == [BC.MISS, BC.HIT]
        for e in new:
            for field in ("run_id", "market_id", "build_input_key", "cache_status"):
                assert field in e
        assert (cache.root / "telemetry.jsonl").read_text(encoding="utf-8").count("\n") >= 2

    def test_an_exercised_run_fills_only_what_the_lanes_deferred(self):
        deferred = "tests/pettripfinder/test_per_market_release_contracts.py::TestEveryMarketAssembles::test_all_gates_pass[dayton-oh]"
        lane_node = "tests/pettripfinder/test_launch_participation_046.py::test_the_candidate_is_the_pinned_artifact"
        lane_failed = "tests/pettripfinder/test_x.py::test_lane_says_failed"
        untouched = "tests/pettripfinder/test_y.py::test_nobody_ran_me"
        lanes = {lane_node: "passed", lane_failed: "failed"}
        replay = {deferred: "passed", lane_failed: "passed", lane_node: "failed"}
        closure = RD.prove_closure([deferred, lane_node, lane_failed, untouched], lanes,
                                   OrderedDict([("replay.xml", replay)]))
        assert closure["results"] == {deferred: RD.CLOSED, lane_node: RD.CLOSED,
                                      lane_failed: RD.STILL_FAILING, untouched: RD.NOT_EXERCISED}
        assert closure["sources"][deferred] == "replay.xml"
        assert closure["sources"][lane_node] == RD.LANE_SOURCE          # a lane result is never overridden
        assert closure["sources"][lane_failed] == RD.LANE_SOURCE
        assert closure["all_accounted_for"] is False
        assert RD.prove_closure([deferred], {}, None)["results"][deferred] == RD.NOT_EXERCISED



# --------------------------------------------------------------------------- #
# The real thing: cold -> warm across processes.
# --------------------------------------------------------------------------- #

@pytest.mark.slow

class TestSessionCacheIsolation:
    """The 004 migration audit's 51 TRUE_NEW failures: a staged build's
    render remembered by the 002 session cache under the COMMITTED key."""

    def test_a_staged_build_is_remembered_under_its_overlay_key_not_the_committed_one(self, dayton):
        from scripts.pettripfinder import assembly_session_cache as ASC
        from scripts.pettripfinder import census_location as CL
        root = SHORT_ROOT / "iso"
        shutil.rmtree(root, ignore_errors=True)
        before = {e.key for e in ASC.CACHE.entries()}
        cache = BC.BundleCache(root / "cache", run_id="test")
        result = cache.build_or_reuse(dayton, work_dir=root / "w", require_determinism=False)
        assert result["cache_status"] == BC.MISS
        new = [e for e in ASC.CACHE.entries() if e.key not in before]
        assert new, "the staged build runs through the session cache"
        committed = CL.COMMITTED_CENSUS_DIR.resolve().as_posix()
        for entry in new:
            dynamic = entry.key_doc["inputs"]["dynamic"]
            assert dynamic["census_dir"] != committed, entry.kind
            assert "PTF_IDENTITY_CENSUS_DIR" in dynamic["env"], entry.kind
        # And the committed key is untouched: what production would ask for
        # is not in the session cache at all.
        live_key, _doc = ASC.session_key(new[0].kind, new[0].key_doc["args"])
        assert live_key not in {e.key for e in ASC.CACHE.entries()}


class TestCrossRun:
    def test_case_2_a_second_process_hits_the_persistent_cache(self, dayton):
        root = SHORT_ROOT / "cr"
        if root.exists():
            shutil.rmtree(root)
        root.mkdir(parents=True)
        packages = root / "pk"
        path = SMP.write_sealed(dayton, packages)
        cache = BC.BundleCache(root / "cache", run_id="cold")
        cold = cache.build_or_reuse(dayton, work_dir=root / "w1")
        assert cold["cache_status"] == BC.MISS and cold["builder_invocations"] == 2
        assert cold["trust_state"] == BC.TRUSTED and cold["determinism"]["result"] == "BYTE_IDENTICAL"
        assert cold["undeclared_dependencies"] == {"data": [], "code": []}
        warm = P4.warm_in_new_process(path, root / "cache", root / "w2", "warm")
        assert warm["cache_status"] == BC.HIT and warm["builder_invocations"] == 0
        assert warm["bundle_sha256"] == cold["bundle_sha256"] and warm["file_count"] == cold["file_count"]
        assert warm["total_seconds"] < 10, warm
        from scripts.pettripfinder.assemble_production_site import bundle_digest, file_hashes
        assert bundle_digest(file_hashes(root / "w2" / "out" / "site")) == cold["bundle_sha256"]


class TestCommittedPilot:
    def test_the_pilot_report_proves_the_acceptance_criteria(self):
        doc = json.loads((REPORTS / "atlas_throughput_004_pilot_run.json").read_text(encoding="utf-8-sig"))
        for label, cw in doc["cold_warm"].items():
            assert cw["RUN_1_COLD"]["BUILD_EXECUTED"] == 2 and cw["RUN_1_COLD"]["TRUSTED_CACHE_PUBLISHED"] == 1, label
            warm = cw["RUN_2_WARM_SEPARATE_PROCESS"]
            assert warm["cache_status"] == BC.HIT and warm["BUILD_EXECUTED"] == 0 and warm["output_identical"], label
        assert all(row["match"] for row in doc["invalidation_matrix"]), [r for r in doc["invalidation_matrix"] if not r["match"]]
        assert doc["concurrency"]["same_key"]["BUILD_EXECUTED"] == 1 and doc["concurrency"]["same_key"]["REUSE_AFTER_WAIT"] == 1
        multi = doc["multi_market"]
        assert multi["A_cleveland_changed"]["cache_status"] == BC.MISS
        assert multi["B_dayton_unchanged"]["cache_status"] == BC.HIT and multi["C_fixture_unchanged"]["cache_status"] == BC.HIT
        assert set(multi["after_shared_template_change"].values()) == {BC.MISS}
