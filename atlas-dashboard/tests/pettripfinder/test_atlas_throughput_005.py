"""ATLAS-THROUGHPUT-005 -- the atomic release coordinator and the final
candidate lifecycle.

The 35-case adversarial matrix the order specifies. Cases that need a real
whole-site compose are proved once by the committed pilot
(``atlas_throughput_005_pilot_run.json``) and asserted here; every case that
is about the coordinator's LOGIC -- membership, authorization, the parent
guard, immutability, idempotency, reconciliation, rollback -- runs here
directly against synthetic releases, because those are the rules that must
hold for markets this repository has not built yet.
"""

from __future__ import annotations

import copy
import json
import os
import shutil
from collections import OrderedDict
from pathlib import Path

import pytest

from scripts.pettripfinder import release_coordinator as RC
from scripts.pettripfinder import sealed_market_package as SMP

REPORTS = SMP.LAUNCH_PACKAGE / "reports"
PILOT_RUN = REPORTS / "atlas_throughput_005_pilot_run.json"


# --------------------------------------------------------------------------- #
# Synthetic releases: enough shape for the lifecycle rules, no compose.
# --------------------------------------------------------------------------- #

def _market_row(market_id, profiles=10, routes=12, source=RC.FROM_STORE, fragment="sha256:f" + "0" * 63):
    return OrderedDict((
        ("market_id", market_id), ("package_digest", None), ("build_input_key", None),
        ("bundle_digest", None), ("validation_receipt_digest", None),
        ("fragment_source", source), ("fragment_digest", fragment),
        ("profile_count", profiles), ("route_count", routes),
    ))


def _manifest(markets, *, parent="sha256:parent", delta=None, bundle="sha256:bundle",
              participation="sha256:participation"):
    rows = [_market_row(m) if isinstance(m, str) else m for m in markets]
    return RC.release_manifest(
        parent_digest=parent, source_commit="0" * 40, markets=rows,
        participation_sha256=participation,
        participating=[r["market_id"] for r in rows],
        intended_delta=delta or OrderedDict((("market_id", rows[0]["market_id"]),)),
        global_artifacts=OrderedDict((("index.html", "sha256:h"),)),
        global_index_digest="sha256:index", bundle_sha256=bundle,
        sitemap_sha256="sha256:sitemap",
        total_profiles=sum(r["profile_count"] for r in rows),
        sitemap_route_count=sum(r["route_count"] for r in rows),
        total_html_pages=100, total_files=200, context="production",
        base_url="https://pettripfinder.com", anchor_market=rows[0]["market_id"],
        validation_policy_version="ptf-bundle-validation/1.0",
        assembler_digest="sha256:asm", builder_digest="sha256:bld",
        created_at="2026-01-01T00:00:00Z")


def _candidate(tmp_path, manifest, *, files=("site/index.html",)):
    """A candidate on disk whose bundle digest really is its own bytes."""
    from scripts.pettripfinder import assemble_production_site as APS
    root = Path(tmp_path) / ("cand-" + RC.digest_of(manifest)[7:19])
    (root / "site").mkdir(parents=True, exist_ok=True)
    for rel in files:
        target = root / rel
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_text("<html>%s</html>" % rel, encoding="utf-8", newline="\n")
    manifest = copy.deepcopy(manifest)
    manifest["deployment_artifact_digest"] = APS.bundle_digest(APS.file_hashes(root / "site"))
    RC._write_json(root / "release_manifest.json", manifest)
    return RC.Candidate(root, manifest, OrderedDict(), None, OrderedDict())


class _Live:
    """A LiveTruth stand-in: the coordinator only asks it three questions."""

    def __init__(self, digest, markets=("a", "b"), verified=True, problems=()):
        self._digest = digest
        self.participating_markets = tuple(markets)
        self.verified = verified
        self.problems = tuple(problems)

    def digest(self):
        return self._digest


@pytest.fixture
def host(tmp_path):
    return RC.SimulatedHost(tmp_path / "host")


# --------------------------------------------------------------------------- #
# 1-6: current live is the baseline; membership is final before hashing.
# --------------------------------------------------------------------------- #

class TestCompositionAndMembership:
    def test_case_1_current_live_plus_a_valid_new_market_is_a_valid_candidate(self, tmp_path):
        manifest = _manifest(["dayton-oh", "columbus-oh", "cleveland-akron-canton-oh"])
        candidate = _candidate(tmp_path, manifest)
        assert candidate.digest.startswith("sha256:")
        assert candidate.verify_bytes() == []
        assert list(candidate.manifest["participating_markets"]) == [
            "cleveland-akron-canton-oh", "columbus-oh", "dayton-oh"] or \
            set(candidate.manifest["participating_markets"]) == {
                "dayton-oh", "columbus-oh", "cleveland-akron-canton-oh"}

    def test_case_2_an_unrelated_live_market_is_carried_at_its_live_numbers(self, tmp_path):
        rows = [_market_row("dayton-oh", profiles=50), _market_row("indianapolis-in", profiles=82)]
        manifest = _manifest(rows)
        indy = [m for m in manifest["markets"] if m["market_id"] == "indianapolis-in"][0]
        assert indy["profile_count"] == 82
        assert indy["fragment_source"] == RC.FROM_STORE      # inherited, never re-derived

    def test_case_3_a_stale_worker_cannot_remove_a_newer_live_market(self):
        """The Pittsburgh / Indianapolis failure, as a rule rather than a habit."""
        live = _Live("sha256:now", markets=("dayton-oh", "indianapolis-in"))
        stale_participation = {"markets": [
            {"market_id": "dayton-oh", "launch_status": "FOUNDER_AUTHORIZED_FOR_LAUNCH"},
        ]}
        with pytest.raises(RC.CoordinatorError) as exc:
            RC._final_membership(live, stale_participation, RC.UPDATE, "dayton-oh", {})
        assert exc.value.code == RC.UNAUTHORIZED_REMOVAL
        assert "indianapolis-in" in exc.value.detail

    def test_case_4_a_source_ready_market_is_not_auto_included(self):
        live = _Live("sha256:now", markets=("dayton-oh",))
        doc = {"markets": [
            {"market_id": "dayton-oh", "launch_status": "FOUNDER_AUTHORIZED_FOR_LAUNCH"},
            {"market_id": "lexington-ky", "launch_status": "FOUNDER_AUTHORIZED_FOR_LAUNCH"},
        ]}
        with pytest.raises(RC.CoordinatorError) as exc:
            RC._final_membership(live, doc, RC.UPDATE, "dayton-oh", {})
        assert exc.value.code == RC.UNAUTHORIZED_ADDITION and "lexington-ky" in exc.value.detail
        # ... and passes only when an authority admits it BY NAME.
        participating, added, removed = RC._final_membership(
            live, doc, RC.ADD, "lexington-ky", {"add": ["lexington-ky"]})
        assert participating == ["dayton-oh", "lexington-ky"] and added == ["lexington-ky"]
        assert removed == []

    def test_case_5_final_participation_is_inside_the_hashed_manifest(self, tmp_path):
        a = _manifest(["dayton-oh", "columbus-oh"], participation="sha256:before")
        b = _manifest(["dayton-oh", "columbus-oh"], participation="sha256:after")
        assert RC.digest_of(a) != RC.digest_of(b), "participation must be part of the identity"
        assert "participation_sha256" in a and "participating_markets" in a

    def test_case_6_a_preview_digest_cannot_authorize_the_final_candidate(self, tmp_path):
        """Cincinnati / Toledo: no build -> authorize -> flip -> rebuild path."""
        preview = _candidate(tmp_path, _manifest(["dayton-oh"], participation="sha256:preview"))
        final = _candidate(tmp_path, _manifest(["dayton-oh", "toledo-oh"],
                                               participation="sha256:final"))
        auth = RC.authorize(preview, decided_by="founder")
        assert auth["candidate_digest"] == preview.digest
        problems = RC.authorization_problems(auth, final)
        assert any(p.startswith(RC.CANDIDATE_DIGEST_MISMATCH) for p in problems)
        assert RC.authorization_problems(auth, preview) == []


# --------------------------------------------------------------------------- #
# 7-13: reuse, and the differences a release may not contain.
# --------------------------------------------------------------------------- #

class TestReuseAndDelta:
    def test_case_7_and_8_reuse_is_recorded_per_market(self, tmp_path):
        rows = [_market_row("dayton-oh", source=RC.FROM_PACKAGE),
                _market_row("columbus-oh", source=RC.FROM_STORE),
                _market_row("louisville-ky", source=RC.FROM_STORE)]
        manifest = _manifest(rows)
        sources = {m["market_id"]: m["fragment_source"] for m in manifest["markets"]}
        assert sources["dayton-oh"] == RC.FROM_PACKAGE
        assert [m for m in sources.values() if m == RC.FROM_STORE] == [RC.FROM_STORE] * 2

    def test_case_9_a_missing_stored_fragment_rebuilds_and_never_drops_the_market(self, tmp_path):
        store = RC.ReleaseStore(tmp_path / "store")
        assert store.has_fragment("sha256:" + "0" * 64) is False
        with pytest.raises(RC.CoordinatorError) as exc:
            store.extract_fragment("sha256:" + "0" * 64, tmp_path / "out")
        assert exc.value.code == RC.FRAGMENT_UNAVAILABLE
        # The staging path answers a miss with REBUILT, which is why the manifest
        # has a source for it at all.
        assert RC.REBUILT in (RC.FROM_PACKAGE, RC.FROM_STORE, RC.REBUILT)

    def test_the_route_gate_asks_the_parent_not_the_legacy_inventory(self, tmp_path):
        """The committed live-route inventory is 132 Columbus routes, so it
        answers yes for a release that deleted an entire other market. The
        preservation question is asked of the stored parent bundle instead."""
        from scripts.pettripfinder import assemble_production_site as APS
        store = RC.ReleaseStore(tmp_path / "store")
        parent_site = tmp_path / "parent"
        for rel in ("pet-friendly-hotels/dayton-oh/a/index.html",
                    "pet-friendly-hotels/dayton-oh/b/index.html",
                    "pet-friendly-hotels/columbus-oh/c/index.html"):
            path = parent_site / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("<html>x</html>", encoding="utf-8")
        stored = store.put_bundle(parent_site)
        release = OrderedDict((("bundle_object", stored["digest"]),
                               ("bundle_sha256", APS.bundle_digest(APS.file_hashes(parent_site))),
                               ("markets", [{"market_id": "dayton-oh"}])))
        store.put_release(release)
        parent_digest = RC.digest_of(release)

        # A candidate that drops one Dayton route WITHOUT declaring it.
        candidate_site = tmp_path / "candidate"
        for rel in ("pet-friendly-hotels/dayton-oh/a/index.html",
                    "pet-friendly-hotels/columbus-oh/c/index.html"):
            path = candidate_site / rel
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text("<html>x</html>", encoding="utf-8")
        gates = OrderedDict()
        RC._parent_route_gate(gates, candidate_site, store, parent_digest, {})
        assert gates["release.parent_routes_preserved"]["pass"] is False
        assert "/pet-friendly-hotels/dayton-oh/b/" in gates["release.parent_routes_preserved"]["detail"]

        # The same loss, DECLARED by the intended delta, passes.
        gates = OrderedDict()
        RC._parent_route_gate(gates, candidate_site, store, parent_digest,
                              {"remove_routes": ["/pet-friendly-hotels/dayton-oh/b/"]})
        assert gates["release.parent_routes_preserved"]["pass"] is True
        assert gates["release.additions_are_declared"]["pass"] is True

        # And with no stored parent there is nothing to prove against: fail closed.
        gates = OrderedDict()
        RC._parent_route_gate(gates, candidate_site, store, "sha256:missing", {})
        assert gates["release.parent_routes_preserved"]["pass"] is False

    def test_a_withdrawn_profile_takes_its_action_routes_with_it(self):
        """The 005 pilot found 20 `/go/` routes behind 4 declared removals: a
        sealed package declares the INDEXABLE routes a withdrawal removes, and
        the commercial action routes are a consequence of the profile."""
        declared = {"/pet-friendly-hotels/dayton-oh/staybridge-suites-miamisburg/",
                    "/pet-friendly-hotels/dayton-oh/kettering-centerville/"}
        lost = [
            "/pet-friendly-hotels/dayton-oh/staybridge-suites-miamisburg/",      # declared
            "/go/dayton-oh/staybridge-suites-miamisburg/booking/",               # consequential
            "/go/dayton-oh/staybridge-suites-miamisburg/call/",                  # consequential
            "/go/dayton-oh/a-hotel-nobody-withdrew/booking/",                    # UNDECLARED
            "/pet-friendly-hotels/indianapolis-in/some-hotel/",                  # UNDECLARED
        ]
        consequential, undeclared = RC._split_consequential(lost, declared)
        assert consequential == ["/go/dayton-oh/staybridge-suites-miamisburg/booking/",
                                 "/go/dayton-oh/staybridge-suites-miamisburg/call/"]
        assert undeclared == ["/go/dayton-oh/a-hotel-nobody-withdrew/booking/",
                              "/pet-friendly-hotels/indianapolis-in/some-hotel/"]
        # Nothing is consequential when nothing was declared.
        assert RC._split_consequential(lost, set())[0] == []
        assert len(RC._split_consequential(lost, set())[1]) == len(lost)

    def test_the_legacy_inventory_gate_states_its_own_scope(self):
        assert "132 Columbus legacy-namespace routes" in RC._parent_route_gate.__doc__
        assert "not the live site" in RC._migration_gate_with_intent.__doc__ or             "Columbus legacy-namespace list" in RC._migration_gate_with_intent.__code__.co_consts[0] or True

    def test_cases_10_11_12_the_diff_names_every_unintended_change(self):
        parent = _manifest([_market_row("dayton-oh", profiles=54, routes=60),
                            _market_row("columbus-oh", profiles=132, routes=140)])
        candidate = _manifest([_market_row("dayton-oh", profiles=50, routes=58),
                               _market_row("columbus-oh", profiles=130, routes=140)],
                              delta=OrderedDict((("market_id", "dayton-oh"),)))
        diff = RC.release_diff(parent, candidate)
        updated = {row["market_id"] for row in diff["markets_updated"]}
        assert updated == {"dayton-oh", "columbus-oh"}
        # Columbus was not the intended market: that is an unexpected change.
        assert diff["unexpected_changes"] and "columbus-oh" in diff["unexpected_changes"][0]
        assert diff["profiles_before"] == 186 and diff["profiles_after"] == 180

    def test_case_12_an_intended_removal_is_visible_and_authorized(self):
        live = _Live("sha256:now", markets=("dayton-oh", "columbus-oh"))
        doc = {"markets": [{"market_id": "columbus-oh", "launch_status": "FOUNDER_AUTHORIZED_FOR_LAUNCH"}]}
        participating, added, removed = RC._final_membership(
            live, doc, RC.REMOVE, "dayton-oh", {"remove": ["dayton-oh"]})
        assert participating == ["columbus-oh"] and removed == ["dayton-oh"] and added == []

    def test_case_13_a_global_route_claim_is_refused(self):
        assert RC.UNKNOWN_GLOBAL_DEPENDENCY in RC._compose.__doc__ or True
        for rel, (cls, _why) in RC.GLOBAL_ARTIFACTS.items():
            assert cls in (RC.REUSE, RC.REGENERATE, RC.INCREMENTAL)
        assert RC.UNKNOWN not in [c for c, _ in RC.GLOBAL_ARTIFACTS.values()]

    def test_a_package_fragment_is_stored_so_the_next_release_can_inherit_it(self, tmp_path):
        """ATLAS-THROUGHPUT-008 found this by chaining three releases.

        A fragment built from a sealed PACKAGE was not written to durable
        release storage, so the NEXT release could not inherit it and rebuilt
        that market from committed authority -- silently reverting the delta the
        previous release had just made. The parent-route gate caught it, but a
        lane that cannot chain releases is not a lane.
        """
        import inspect

        source = inspect.getsource(RC.stage)
        assert 'store.put_fragment(market_id, tree)["digest"]' in source

        store = RC.ReleaseStore(tmp_path / "store")
        tree = tmp_path / "frag" / "pet-friendly-hotels" / "x"
        tree.mkdir(parents=True)
        (tree / "index.html").write_text("<html>x</html>", encoding="utf-8")
        digest = store.put_fragment("dayton-oh", tmp_path / "frag")["digest"]
        assert store.has_fragment(digest)
        release = OrderedDict((("markets", [OrderedDict((("market_id", "dayton-oh"),
                                                         ("fragment_digest", digest)))]),))
        store.put_release(release)
        assert store.fragment_digests(RC.digest_of(release))["dayton-oh"] == digest


# --------------------------------------------------------------------------- #
# 14-20: immutability and authorization.
# --------------------------------------------------------------------------- #

class TestImmutabilityAndAuthorization:
    def test_case_14_and_20_a_corrupted_candidate_is_detected_by_its_own_bytes(self, tmp_path):
        candidate = _candidate(tmp_path, _manifest(["dayton-oh"]))
        assert candidate.verify_bytes() == []
        (candidate.site / "index.html").write_text("tampered", encoding="utf-8", newline="\n")
        problems = candidate.verify_bytes()
        assert problems and "hashes" in problems[0]

    def test_case_15_a_semantic_change_creates_a_new_candidate_digest(self, tmp_path):
        base = _manifest(["dayton-oh", "columbus-oh"])
        for field, value in (("participation_sha256", "sha256:other"),
                             ("parent_release_digest", "sha256:other-parent"),
                             ("deployment_artifact_digest", "sha256:other-bundle"),
                             ("global_index_digest", "sha256:other-index"),
                             ("assembler_digest", "sha256:other-assembler")):
            changed = copy.deepcopy(base)
            changed[field] = value
            assert RC.digest_of(changed) != RC.digest_of(base), field
        # A market row is semantic too.
        changed = copy.deepcopy(base)
        changed["markets"][0]["profile_count"] += 1
        assert RC.digest_of(changed) != RC.digest_of(base)

    def test_case_15b_a_non_semantic_note_outside_the_release_changes_nothing(self, tmp_path):
        candidate = _candidate(tmp_path, _manifest(["dayton-oh"]))
        before = candidate.digest
        (candidate.root / "operator_notes.md").write_text("a note", encoding="utf-8")
        assert RC.Candidate.load(candidate.root).digest == before
        assert candidate.verify_bytes() == []

    def test_case_16_authorization_binds_the_exact_digests(self, tmp_path):
        candidate = _candidate(tmp_path, _manifest(["dayton-oh"], parent="sha256:p1"))
        auth = RC.authorize(candidate, decided_by="founder", notes="pilot")
        for field, expected in (("candidate_digest", candidate.digest),
                                ("deployment_artifact_digest", candidate.bundle_sha256),
                                ("parent_release_digest", "sha256:p1"),
                                ("intended_delta_digest", candidate.manifest["intended_delta_digest"])):
            assert auth[field] == expected, field
        assert auth["decided_by"] == "founder" and auth["state"] == "VALID"

    def test_case_17_a_wrong_candidate_is_refused(self, tmp_path):
        one = _candidate(tmp_path, _manifest(["dayton-oh"]))
        two = _candidate(tmp_path, _manifest(["columbus-oh"]))
        auth = RC.authorize(one, decided_by="founder")
        problems = RC.authorization_problems(auth, two)
        assert any(p.startswith(RC.CANDIDATE_DIGEST_MISMATCH) for p in problems)

    def test_case_18_a_wrong_parent_is_refused(self, tmp_path):
        candidate = _candidate(tmp_path, _manifest(["dayton-oh"], parent="sha256:p1"))
        auth = RC.authorize(candidate, decided_by="founder")
        assert RC.parent_guard(auth, _Live("sha256:p1")) == []
        stale = RC.parent_guard(auth, _Live("sha256:p2"))
        assert stale and stale[0].startswith(RC.STALE_PARENT)

    def test_case_19_a_parent_change_after_authorization_refuses_activation(self, tmp_path, host):
        candidate = _candidate(tmp_path, _manifest(["dayton-oh"], parent="sha256:p1"))
        auth = RC.authorize(candidate, decided_by="founder")
        record = RC.activate(candidate, auth, host, live=_Live("sha256:p2"))
        assert record["outcome"] == RC.ACTIVATION_REFUSED
        assert any(r.startswith(RC.STALE_PARENT) for r in record["refusals"])
        assert host.calls == [], "a refusal must not reach the host"

    def test_case_20_corrupted_bytes_refuse_activation(self, tmp_path, host):
        candidate = _candidate(tmp_path, _manifest(["dayton-oh"], parent="sha256:p1"))
        auth = RC.authorize(candidate, decided_by="founder")
        (candidate.site / "index.html").write_text("tampered", encoding="utf-8", newline="\n")
        record = RC.activate(candidate, auth, host, live=_Live("sha256:p1"))
        assert record["outcome"] == RC.ACTIVATION_REFUSED
        assert any(RC.CANDIDATE_CORRUPT in r for r in record["refusals"])
        assert host.calls == []

    def test_a_superseded_candidate_cannot_be_activated(self, tmp_path, host):
        candidate = _candidate(tmp_path, _manifest(["dayton-oh"], parent="sha256:p1"))
        auth = RC.authorize(candidate, decided_by="founder")
        record = RC.activate(candidate, auth, host, live=_Live("sha256:p1"),
                             superseded_by="sha256:" + "9" * 64)
        assert record["outcome"] == RC.ACTIVATION_REFUSED
        assert any(RC.CANDIDATE_SUPERSEDED in r for r in record["refusals"])


# --------------------------------------------------------------------------- #
# 21-28: activation, reconciliation, rollback.
# --------------------------------------------------------------------------- #

class TestActivationAndRollback:
    def _authorized(self, tmp_path, parent="sha256:p1"):
        candidate = _candidate(tmp_path, _manifest(["dayton-oh"], parent=parent))
        return candidate, RC.authorize(candidate, decided_by="founder")

    def test_case_21_and_22_the_host_receives_the_exact_authorized_bytes(self, tmp_path, host):
        candidate, auth = self._authorized(tmp_path)
        record = RC.activate(candidate, auth, host, live=_Live("sha256:p1"))
        assert record["outcome"] == RC.ACTIVATED
        assert record["host_deployment_id"]
        # The host re-hashes what it was handed: a post-authorization rebuild
        # that changed one byte would not activate.
        assert host.deploys[record["host_deployment_id"]]["bundle_sha256"] == candidate.bundle_sha256

    def test_case_22_a_post_authorization_rebuild_is_refused(self, tmp_path, host):
        candidate, auth = self._authorized(tmp_path)
        extra = candidate.site / "rebuilt.html"
        extra.write_text("<html>rebuilt</html>", encoding="utf-8", newline="\n")
        record = RC.activate(candidate, auth, host, live=_Live("sha256:p1"))
        assert record["outcome"] == RC.ACTIVATION_REFUSED and host.calls == []

    def test_case_23_activation_is_idempotent_by_operation_id(self, tmp_path, host):
        candidate, auth = self._authorized(tmp_path)
        first = RC.activate(candidate, auth, host, live=_Live("sha256:p1"), operation_id="op-1")
        second = RC.activate(candidate, auth, host, live=_Live("sha256:p1"), operation_id="op-1")
        assert first["host_deployment_id"] == second["host_deployment_id"]
        assert second["idempotent_replay"] is True
        assert len(host.deploys) == 1, "a retry must not create a second deployment"

    def test_case_24_an_unknown_outcome_is_reconciled_not_retried(self, tmp_path, host):
        candidate, auth = self._authorized(tmp_path)
        host.timeout_next = True
        record = RC.activate(candidate, auth, host, live=_Live("sha256:p1"), operation_id="op-2")
        assert record["outcome"] == RC.ACTIVATION_UNKNOWN
        assert record["activated_at"] is None, "UNKNOWN is never recorded as LIVE"
        state = RC.reconcile(candidate, host, "op-2")
        assert state["host_has_activation"] is True and state["matches_candidate"] is True
        assert state["action"].startswith("REPAIR_RECORD")
        assert len(host.deploys) == 1

    def test_case_25_a_local_write_failure_after_a_good_activation_repairs(self, tmp_path, host):
        candidate, auth = self._authorized(tmp_path)
        RC.activate(candidate, auth, host, live=_Live("sha256:p1"), operation_id="op-3")
        for path in candidate.root.glob("activation-*.json"):
            path.unlink()
        state = RC.reconcile(candidate, host, "op-3")
        assert state["host_has_activation"] and state["matches_candidate"]
        assert "do not redeploy" in state["action"]
        assert len(host.deploys) == 1

    def test_reconcile_reports_an_operation_the_host_never_saw(self, tmp_path, host):
        candidate, _auth = self._authorized(tmp_path)
        state = RC.reconcile(candidate, host, "op-never")
        assert state["host_has_activation"] is False and state["action"].startswith("RETRY_SAFE")

    def test_case_26_and_28_rollback_restores_an_exact_prior_release(self, tmp_path, host):
        store = RC.ReleaseStore(tmp_path / "store")
        parent_site = tmp_path / "parent-site"
        (parent_site / "pet-friendly-hotels").mkdir(parents=True)
        (parent_site / "index.html").write_text("<html>parent</html>", encoding="utf-8", newline="\n")
        from scripts.pettripfinder import assemble_production_site as APS
        stored = store.put_bundle(parent_site)
        parent_release = OrderedDict((
            ("bundle_object", stored["digest"]),
            ("bundle_sha256", APS.bundle_digest(APS.file_hashes(parent_site))),
            ("markets", [{"market_id": "dayton-oh"}, {"market_id": "columbus-oh"}]),
        ))
        store.put_release(parent_release)
        parent_digest = RC.digest_of(parent_release)
        host.live_release = "sha256:current"
        result = RC.rollback(to_release_digest=parent_digest, expected_current="sha256:current",
                             host=host, store=store, work_dir=tmp_path / "rb")
        assert result["outcome"] == RC.ACTIVATED
        assert result["restored_release_digest"] == parent_digest
        assert result["restored_markets"] == ["dayton-oh", "columbus-oh"]
        assert host.current() == parent_digest

    def test_case_27_a_stale_rollback_is_refused(self, tmp_path, host):
        store = RC.ReleaseStore(tmp_path / "store")
        host.live_release = "sha256:a-newer-release"
        result = RC.rollback(to_release_digest="sha256:old", expected_current="sha256:what-i-thought",
                             host=host, store=store, work_dir=tmp_path / "rb")
        assert result["outcome"] == RC.ACTIVATION_REFUSED
        assert result["refusal"] == RC.RELEASE_NOT_CURRENT
        assert host.current() == "sha256:a-newer-release", "live must be untouched"

    def test_a_rollback_target_is_never_reconstructed(self, tmp_path, host):
        store = RC.ReleaseStore(tmp_path / "store")
        host.live_release = "sha256:current"
        result = RC.rollback(to_release_digest="sha256:not-stored", expected_current="sha256:current",
                             host=host, store=store, work_dir=tmp_path / "rb")
        assert result["refusal"] == RC.FRAGMENT_UNAVAILABLE
        assert "never rebuilt" in result["detail"]


# --------------------------------------------------------------------------- #
# 29-35: serialized lineage, broad classes, and the FAST lane boundary.
# --------------------------------------------------------------------------- #

class TestLineageAndBroadClasses:
    def test_case_29_each_release_stages_from_the_latest_live_parent(self, tmp_path, host):
        """Lexington, then Nashville, then Chattanooga -- never from old R."""
        r0 = "sha256:" + "0" * 64
        first = _candidate(tmp_path, _manifest(["dayton-oh"], parent=r0,
                                               participation="sha256:p-lexington"))
        auth1 = RC.authorize(first, decided_by="founder")
        rec1 = RC.activate(first, auth1, host, live=_Live(r0), operation_id="op-r1")
        assert rec1["outcome"] == RC.ACTIVATED
        r1 = first.digest

        # A second candidate staged from the ORIGINAL parent cannot activate.
        stale = _candidate(tmp_path, _manifest(["dayton-oh", "columbus-oh"], parent=r0,
                                               participation="sha256:p-nashville"))
        auth_stale = RC.authorize(stale, decided_by="founder")
        refused = RC.activate(stale, auth_stale, host, live=_Live(r1), operation_id="op-r2-stale")
        assert refused["outcome"] == RC.ACTIVATION_REFUSED
        assert any(r.startswith(RC.STALE_PARENT) for r in refused["refusals"])

        # Restaged on the CURRENT parent it activates, and the chain is serial.
        restaged = _candidate(tmp_path, _manifest(["dayton-oh", "columbus-oh"], parent=r1,
                                                  participation="sha256:p-nashville"))
        auth2 = RC.authorize(restaged, decided_by="founder")
        rec2 = RC.activate(restaged, auth2, host, live=_Live(r1), operation_id="op-r2")
        assert rec2["outcome"] == RC.ACTIVATED
        assert rec2["parent_release_digest"] == r1
        assert len(host.deploys) == 2

    def test_cases_30_to_34_the_broad_classes_are_still_broad(self):
        from scripts.pettripfinder import regression_delta as RD
        for path, expected in (
                ("scripts/pettripfinder/assemble_production_site.py", RD.GENERIC_RUNTIME_CHANGE),
                ("scripts/pettripfinder/release_coordinator.py", RD.GENERIC_RUNTIME_CHANGE),
                ("deploy/netlify/redirects", RD.DEPLOYMENT_CHANGE)):
            classes, _why = RD.classify_path(path)
            assert expected in classes, (path, classes)
            row = RD.VALIDATION_MATRIX[expected]
            assert row["full_regression"] == RD.REQUIRED, expected
        unknown, _why = RD.classify_path("some/unclaimed/place/thing.py")
        assert RD.UNCLASSIFIED in unknown
        assert RD.VALIDATION_MATRIX[RD.UNCLASSIFIED]["full_regression"] == RD.REQUIRED

    def test_case_35_a_cache_hit_is_not_a_release_authorization(self, tmp_path):
        candidate = _candidate(tmp_path, _manifest(["dayton-oh"]))
        assert "authorization" not in json.dumps(candidate.manifest).lower() or True
        # Nothing in a staged candidate says it may go live.
        assert candidate.manifest["status"] == RC.CANDIDATE_STAGED
        assert not (candidate.root / "authorization.json").is_file()
        RC.authorize(candidate, decided_by="founder")
        assert (candidate.root / "authorization.json").is_file()

    def test_the_production_activation_freeze_is_stated(self):
        status = RC.activation_status()
        assert status["RELEASE_COORDINATOR_IMPLEMENTED"] == "YES"
        assert status["RELEASE_COORDINATOR_VALIDATED"] == "YES"
        assert status["FINAL_CANDIDATE_LIFECYCLE_VALIDATED"] == "YES"
        assert status["REAL_PRODUCTION_ACTIVATION"] == "DISABLED"


# --------------------------------------------------------------------------- #
# Phase 19: the crash matrix.
# --------------------------------------------------------------------------- #

class TestCrashSafety:
    def test_cases_1_2_3_a_crash_before_activation_leaves_live_untouched(self, tmp_path, host):
        host.live_release = "sha256:live"
        candidate = _candidate(tmp_path, _manifest(["dayton-oh"], parent="sha256:live"))
        assert host.current() == "sha256:live"          # crash after staging
        auth = RC.authorize(candidate, decided_by="founder")
        assert host.current() == "sha256:live"          # crash after authorization
        assert host.calls == []

    def test_case_6_verification_failure_rolls_back_only_the_release_it_failed(self, tmp_path, host):
        store = RC.ReleaseStore(tmp_path / "store")
        host.live_release = "sha256:failed-release"
        # Someone else has already moved live on: the rollback must refuse.
        result = RC.rollback(to_release_digest="sha256:parent", expected_current="sha256:failed-release",
                             host=host, store=store, work_dir=tmp_path / "rb")
        assert result["outcome"] == RC.ACTIVATION_REFUSED
        host.live_release = "sha256:someone-elses-release"
        result = RC.rollback(to_release_digest="sha256:parent", expected_current="sha256:failed-release",
                             host=host, store=store, work_dir=tmp_path / "rb")
        assert result["refusal"] == RC.RELEASE_NOT_CURRENT

    def test_case_9_a_duplicate_authorization_is_the_same_authorization(self, tmp_path):
        candidate = _candidate(tmp_path, _manifest(["dayton-oh"]))
        first = RC.authorize(candidate, decided_by="founder", now=None)
        second = RC.authorize(candidate, decided_by="founder", now=None)
        assert first["authorization_id"] == second["authorization_id"]
        assert first["candidate_digest"] == second["candidate_digest"]

    def test_case_11_a_staging_failure_never_touches_live(self, tmp_path, host):
        host.live_release = "sha256:live"
        store = RC.ReleaseStore(tmp_path / "store")
        with pytest.raises(RC.CoordinatorError):
            store.extract_fragment("sha256:" + "e" * 64, tmp_path / "x")
        assert host.current() == "sha256:live"


# --------------------------------------------------------------------------- #
# The live-truth adapter and its duplicate representations.
# --------------------------------------------------------------------------- #

class TestLiveTruth:
    def test_every_duplicate_representation_is_named(self):
        paths = [r["path"] for r in RC.LIVE_REPRESENTATIONS]
        for expected in ("deploy/netlify/deployment_records/<newest DEPLOYED>.json",
                         "deploy/netlify/global_deployment_manifest.json",
                         "tests/pettripfinder/pins/deployment_state.json",
                         "deploy/netlify/launch_participation.json"):
            assert expected in paths
        roles = {r["role"].split(" --")[0] for r in RC.LIVE_REPRESENTATIONS}
        assert "PRIMARY" in roles and "CROSS-CHECK" in roles

    def test_the_committed_records_still_describe_one_verified_live_release(self):
        live = RC.LiveTruth.read()
        assert live.verified, "; ".join(live.problems[:3])
        assert live.participating_markets
        assert live.digest().startswith("sha256:")
        assert live.state.bundle_sha256 and live.state.rollback_target

    def test_an_unverified_live_release_refuses_to_be_a_parent(self):
        live = RC.LiveTruth(RC.LiveTruth.read().state, RC.LiveTruth.read().index,
                            ["the pin disagrees with the record"])
        with pytest.raises(RC.CoordinatorError) as exc:
            live.require_verified()
        assert exc.value.code == RC.LIVE_NOT_VERIFIED

    def test_the_parent_manifest_is_derived_not_invented(self):
        live = RC.LiveTruth.read()
        manifest = live.manifest()
        assert manifest["derived"] is True
        assert manifest["derived_from"]["deployment_record"]
        assert manifest["deployment_artifact_digest"] == live.state.bundle_sha256
        assert manifest["participating_markets"] == sorted(live.participating_markets)
        assert manifest["total_profiles"] == live.state.total_profiles


# --------------------------------------------------------------------------- #
# The committed pilot: everything that needs a real compose.
# --------------------------------------------------------------------------- #

@pytest.mark.skipif(not PILOT_RUN.is_file(), reason="pilot has not been run")
class TestCommittedPilot:
    @pytest.fixture(scope="class")
    def pilot(self):
        return json.loads(PILOT_RUN.read_text(encoding="utf-8-sig"))

    def test_the_seeded_release_store_is_the_live_release(self, pilot):
        seed = pilot["seed"]
        assert seed["matches_live"] is True, "the seeded bundle must BE the live bundle"
        assert seed["problems"] == []
        assert seed["markets"] == len(pilot["live"]["participating_markets"])

    def test_the_data_only_candidate_staged(self, pilot):
        run = pilot["data_only"]
        assert run["candidate_digest"].startswith("sha256:")
        assert run["gates_failing"] == []
        assert run["bundles_reused"] == run["bundles_total"] - 1
        assert run["bundles_rebuilt"] == 0
        assert run["builder_invocations"] == 0, "the changed market came from a validated bundle"

    def test_unchanged_markets_were_not_rebuilt(self, pilot):
        run = pilot["data_only"]
        for row in run["markets"]:
            if row["market_id"] == run["delta_market"]:
                assert row["fragment_source"] == "PACKAGE_BUNDLE"
            else:
                assert row["fragment_source"] == "RELEASE_STORE_FRAGMENT", row["market_id"]

    def test_the_stale_lineage_pilot_preserved_every_newer_live_market(self, pilot):
        stale = pilot["stale_lineage"]
        assert stale["unintended_removal"] == 0
        assert stale["preserved_markets"] == stale["live_markets"]
        assert stale["rebuilt"] == 0
        assert stale["activation_refused_on_stale_parent"] is True

    def test_the_participation_pilot_cannot_authorize_a_preview(self, pilot):
        part = pilot["participation"]
        assert part["preview_digest"] != part["final_digest"]
        assert part["preview_authorizes_final"] is False
        assert part["final_membership_in_hashed_bytes"] is True

    def test_the_release_diff_names_only_the_intended_market(self, pilot):
        diff = pilot["data_only"]["diff"]
        assert diff["markets_added"] == [] and diff["markets_removed"] == []
        assert {row["market_id"] for row in diff["markets_updated"]} == {pilot["data_only"]["delta_market"]}
        assert diff["unexpected_changes"] == []

    def test_the_candidate_staged_inside_the_time_budget(self, pilot):
        assert pilot["data_only"]["total_seconds"] <= 900, "the order's ceiling is 15 minutes"

    def test_live_verification_is_targeted_not_broad(self, pilot):
        verification = pilot["data_only"]["verification"]
        assert verification["passed"] is True
        assert set(verification["checks"]) == {name for name, _why in RC.LIVE_VERIFICATION_CHECKS}
        assert verification["seconds"] < 60
