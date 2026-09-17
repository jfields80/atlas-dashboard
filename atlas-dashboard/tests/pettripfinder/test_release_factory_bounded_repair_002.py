"""PTF-RELEASE-FACTORY-EFFICIENCY-BOUNDED-REPAIR-002 -- the focused battery.

Four repairs, each proven here before any broad run:

1. ``release_index.resolve_current_live_source`` names CURRENT_LIVE_SOURCE_COMMIT
   from the deployment records of every ref, and fails closed on a missing,
   conflicting or inconsistent record -- never falling back to ``origin/main``.
2. ``registration_release_lane`` refuses a stale base, derives the
   classification base itself, and records an AUTOMATIC classification.
3. ``release_coordinator.ReleaseStore`` stores a seeded live release at the
   digest ``get_release`` is asked for, and every corrupt, stale, wrong or
   mismatched release fails closed.
4. ``registration_data_only.prove_paid_ledger_append`` narrows the shared paid
   ledger only on content, never on its path.

Plus the negatives the order names: the narrow lane rejects each of them.

The resolver and lane cases run against throw-away git repositories built in
``tmp_path``; the proof and store cases run against the committed tree or
synthetic stores. No case depends on a market total.
"""

from __future__ import annotations

import copy
import json
import shutil
import subprocess
from collections import OrderedDict
from pathlib import Path

import pytest

from scripts.pettripfinder import assemble_production_site as APS
from scripts.pettripfinder import registration_data_only as REG
from scripts.pettripfinder import registration_release_lane as LANE
from scripts.pettripfinder import regression_delta as RD
from scripts.pettripfinder import release_coordinator as RC
from scripts.pettripfinder import release_index as RI
from scripts.pettripfinder import sealed_market_package as SMP
from scripts.pettripfinder.acquisition import paid_attempt_ledger as LEDGER

PREFIX = "atlas-dashboard/"
NEW_MARKET = "zz-bounded-repair-nc"


# --------------------------------------------------------------------------- #
# A throw-away repository whose deployment records current_verified_live accepts.
# --------------------------------------------------------------------------- #

def _git(root: Path, *args: str) -> str:
    proc = subprocess.run(["git", *args], cwd=str(root), capture_output=True, text=True)
    assert proc.returncode == 0, (args, proc.stderr)
    return proc.stdout.strip()


def _write(root: Path, rel: str, doc) -> None:
    path = root / PREFIX / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    text = doc if isinstance(doc, str) else json.dumps(doc, indent=1) + "\n"
    path.write_text(text, encoding="utf-8", newline="\n")


def _commit(root: Path, message: str) -> str:
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "--allow-empty", "-m", message)
    return _git(root, "rev-parse", "HEAD")


def _record(deploy_id: str, previous: str, source: str, at: str, bundle: str, markets) -> OrderedDict:
    counts = OrderedDict((m, 3) for m in markets)
    return OrderedDict((
        ("deployment_id", deploy_id), ("previous_deployment_id", previous), ("rollback_target", previous),
        ("source_commit", source), ("bundle_sha256", bundle), ("sitemap_sha256", "s-" + bundle),
        ("participating_markets", list(markets)), ("profile_counts", counts),
        ("total_profiles", sum(counts.values())), ("sitemap_route_count", 10 * len(markets)),
        ("authorization_id", "auth-" + deploy_id), ("final_status", "DEPLOYED"), ("deployed_at", at),
    ))


def _publish_live(root: Path, record: OrderedDict, *, manifest_bundle: str = None) -> None:
    """The live-truth files for ``record``, all agreeing unless told otherwise."""
    _write(root, "deploy/netlify/deployment_records/%s.json" % record["deployment_id"], record)
    _write(root, "deploy/netlify/deployment_authorizations/%s.json" % record["authorization_id"], OrderedDict((
        ("bundle_sha256", record["bundle_sha256"]), ("authorization_status", "DEPLOYED"))))
    _write(root, "deploy/netlify/global_deployment_manifest.json", OrderedDict((
        ("bundle_sha256", manifest_bundle or record["bundle_sha256"]),
        ("participating_markets", [OrderedDict((("market_id", m), ("published_profiles", 3)))
                                   for m in record["participating_markets"]]),
        ("total_published_profiles", record["total_profiles"]))))
    _write(root, "tests/pettripfinder/pins/deployment_state.json", OrderedDict((("live", OrderedDict((
        ("deploy_id", record["deployment_id"]), ("bundle_sha256", record["bundle_sha256"]),
        ("rollback_target", record["rollback_target"]), ("total_profiles", record["total_profiles"]),
        ("sitemap_route_count", record["sitemap_route_count"]),
        ("participating_markets", record["participating_markets"])))),)))


@pytest.fixture
def repo(tmp_path):
    """source A -> deploy d1 (B) -> source C -> deploy d2 (D, the live lineage).
    ``main`` and ``origin/main`` stay at B, the way the real origin/main stayed
    behind the live worker lineage."""
    root = tmp_path / "repo"
    root.mkdir()
    _git(root, "init", "-q", "-b", "main")
    _git(root, "config", "user.email", "t@example.com")
    _git(root, "config", "user.name", "t")
    _git(root, "config", "core.autocrlf", "false")
    _write(root, "README.md", "x\n")
    a = _commit(root, "A source")
    r1 = _record("d1", "d0", a, "2026-01-01T00:00:00Z", "b1", ["m-one"])
    r0 = _record("d0", "", a, "2025-12-01T00:00:00Z", "b0", ["m-one"])
    r0["rollback_target"] = r0["previous_deployment_id"] = ""
    _write(root, "deploy/netlify/deployment_records/d0.json", r0)
    _publish_live(root, r1)
    b = _commit(root, "B deploy d1")
    _git(root, "update-ref", "refs/remotes/origin/main", b)
    _git(root, "checkout", "-q", "-b", "worker/live")
    _write(root, "src.txt", "c\n")
    c = _commit(root, "C source for d2")
    r2 = _record("d2", "d1", c, "2026-02-01T00:00:00Z", "b2", ["m-one", "m-two"])
    _publish_live(root, r2)
    d = _commit(root, "D deploy d2")
    return OrderedDict((("root", root), ("A", a), ("B", b), ("C", c), ("D", d), ("r2", r2)))


# --------------------------------------------------------------------------- #
# 1. CURRENT_LIVE_SOURCE_COMMIT.
# --------------------------------------------------------------------------- #

class TestCurrentLiveSourceResolver:

    def test_the_correct_current_live_commit(self, repo):
        doc = RI.resolve_current_live_source(repo["root"], prefix=PREFIX)
        assert doc["RESOLVED"] == "YES", doc["problems"]
        assert doc["CURRENT_LIVE_SOURCE_COMMIT"] == repo["D"]
        assert doc["built_from_commit"] == repo["C"]
        assert doc["live_deploy_id"] == "d2"
        assert doc["head_contains_live"] is True
        assert RI.require_current_live_source(doc) == repo["D"]

    def test_stale_origin_main_is_reported_and_never_used(self, repo):
        _git(repo["root"], "checkout", "-q", "main")          # HEAD = B, the stale lineage
        doc = RI.resolve_current_live_source(repo["root"], prefix=PREFIX)
        assert doc["RESOLVED"] == "YES"
        assert doc["CURRENT_LIVE_SOURCE_COMMIT"] == repo["D"], "origin/main must never be read as live"
        assert doc["origin_main_contains_live"] is False and doc["origin_main_stale"] is True
        assert doc["head_contains_live"] is False
        stub = RI.LiveState("d1", "d0", "d0", repo["A"], "b1", "s-b1", ("m-one",), OrderedDict(), 3, 10, "", "")
        with pytest.raises(LANE.LaneRefusal) as exc:
            LANE.require_current_live(doc, worktree_live=stub)
        assert exc.value.code == LANE.STALE_LIVE_BASE

    def test_inconsistent_deployment_records_fail_closed(self, repo):
        # The commit that ADDS the live record carries a manifest that disagrees.
        root = repo["root"]
        _git(root, "checkout", "-q", "-b", "worker/bad", repo["C"])
        _publish_live(root, repo["r2"], manifest_bundle="not-the-deployed-bundle")
        _commit(root, "D' deploy d2 with a disagreeing manifest")
        _git(root, "branch", "-D", "worker/live")
        doc = RI.resolve_current_live_source(root, prefix=PREFIX)
        assert doc["RESOLVED"] == "NO"
        assert RI.INCONSISTENT_DEPLOYMENT_RECORDS in doc["refusal_codes"], doc["problems"]
        with pytest.raises(RI.LiveSourceError):
            RI.require_current_live_source(doc)

    def test_a_missing_live_record_fails_closed(self, tmp_path):
        root = tmp_path / "empty"
        root.mkdir()
        _git(root, "init", "-q", "-b", "main")
        _git(root, "config", "user.email", "t@example.com")
        _git(root, "config", "user.name", "t")
        _write(root, "README.md", "x\n")
        _commit(root, "nothing deployed")
        doc = RI.resolve_current_live_source(root, prefix=PREFIX)
        assert doc["RESOLVED"] == "NO"
        assert doc["refusal_codes"] == [RI.MISSING_LIVE_RECORD]
        assert doc["CURRENT_LIVE_SOURCE_COMMIT"] is None

    def test_one_record_name_with_two_contents_is_a_conflict(self, repo):
        root = repo["root"]
        _git(root, "checkout", "-q", "-b", "worker/rewrite", repo["D"])
        rewritten = copy.deepcopy(repo["r2"])
        rewritten["bundle_sha256"] = "b2-rewritten"
        _write(root, "deploy/netlify/deployment_records/d2.json", rewritten)
        _commit(root, "rewrite an immutable record")
        doc = RI.resolve_current_live_source(root, prefix=PREFIX)
        assert doc["RESOLVED"] == "NO"
        assert RI.CONFLICTING_LIVE_RECORDS in doc["refusal_codes"]

    def test_two_deployments_claiming_the_newest_instant_are_a_conflict(self, repo):
        root = repo["root"]
        _git(root, "checkout", "-q", "-b", "worker/rival", repo["C"])
        rival = _record("d2-rival", "d1", repo["C"], repo["r2"]["deployed_at"], "b2r", ["m-one"])
        _publish_live(root, rival)
        _commit(root, "a rival deploy at the same instant")
        doc = RI.resolve_current_live_source(root, prefix=PREFIX)
        assert doc["RESOLVED"] == "NO"
        assert RI.CONFLICTING_LIVE_RECORDS in doc["refusal_codes"]

    def test_the_committed_tree_resolves_to_a_lineage_head_contains(self):
        doc = RI.resolve_current_live_source()
        assert doc["RESOLVED"] == "YES", doc["problems"]
        assert doc["head_contains_live"] is True
        assert doc["live_deploy_id"] == RI.current_verified_live().deploy_id


# --------------------------------------------------------------------------- #
# 2. The registration lane derives its own base and classifies automatically.
# --------------------------------------------------------------------------- #

def _live_doc(repo) -> OrderedDict:
    return RI.resolve_current_live_source(repo["root"], prefix=PREFIX)


class TestRegistrationBase:

    def test_the_base_is_derived_past_the_market_and_after_live(self, repo):
        root = repo["root"]
        _write(root, "scripts/factory.py", "x = 1\n")
        factory = _commit(root, "F factory commit after live")
        _write(root, "launch_packages/pettripfinder/markets/%s.json" % NEW_MARKET, OrderedDict((("m", 1),)))
        _commit(root, "M register the new market")
        live = _live_doc(repo)
        base = LANE.derive_registration_base(NEW_MARKET, live["CURRENT_LIVE_SOURCE_COMMIT"], git_root=root,
                                             prefix=PREFIX)
        assert base["base"] == factory
        assert [c["commit"] for c in base["factory_commits_since_live"]] == [factory]

    def test_a_market_whose_work_predates_live_is_refused(self, repo):
        root = repo["root"]
        _git(root, "checkout", "-q", "-b", "worker/early", repo["B"])
        _write(root, "launch_packages/pettripfinder/markets/%s.json" % NEW_MARKET, OrderedDict((("m", 1),)))
        _commit(root, "the market registered on the OLD parent")
        _git(root, "merge", "-q", "--no-edit", repo["D"])
        live = _live_doc(repo)
        with pytest.raises(LANE.LaneRefusal) as exc:
            LANE.derive_registration_base(NEW_MARKET, live["CURRENT_LIVE_SOURCE_COMMIT"], git_root=root,
                                          prefix=PREFIX)
        assert exc.value.code == LANE.BASE_NOT_DERIVABLE

    def test_a_dirty_worktree_is_refused(self, repo, monkeypatch, tmp_path):
        root = repo["root"]
        live = _live_doc(repo)
        monkeypatch.setattr(LANE, "require_current_live", lambda *a, **k: live)
        _write(root, "launch_packages/pettripfinder/markets/%s.json" % NEW_MARKET, OrderedDict((("m", 1),)))
        with pytest.raises(LANE.LaneRefusal) as exc:
            LANE.classify_automatically(NEW_MARKET, out=tmp_path / "c.json", git_root=root)
        assert exc.value.code == LANE.DIRTY_WORKTREE

    def test_the_packet_records_an_automatic_classification(self, tmp_path):
        classification = OrderedDict((
            ("classification_source", LANE.CLASSIFICATION_SOURCE_AUTOMATIC),
            ("live_resolution", OrderedDict((("CURRENT_LIVE_SOURCE_COMMIT", "f" * 40),))),
            ("registration_base", OrderedDict((("base", "e" * 40),))),
            ("FULL_REGRESSION_REQUIRED", "YES"), ("plan", OrderedDict()),
            ("new_market_registration_data_only", OrderedDict((("ELIGIBLE", "NO"), ("market_id", NEW_MARKET)))),
        ))
        path = tmp_path / "classification.json"
        path.write_text(json.dumps(classification), encoding="utf-8")
        with pytest.raises(SystemExit):
            LANE.packet(NEW_MARKET, classification_path=path, lane_report=tmp_path / "none.json",
                        out=tmp_path / "packet.json", prepared_by="test")
        packet = json.loads((tmp_path / "packet.json").read_text(encoding="utf-8"))
        assert packet["status"] == "NOT_AUTHORIZATION_READY"
        assert packet["regression_v2"]["classification_source"] == LANE.CLASSIFICATION_SOURCE_AUTOMATIC
        assert packet["regression_v2"]["current_live_source_commit"] == "f" * 40
        assert packet["regression_v2"]["registration_base"] == "e" * 40


# --------------------------------------------------------------------------- #
# 3. The release store round trip.
# --------------------------------------------------------------------------- #

def _tree(root: Path, rels) -> Path:
    for rel in rels:
        path = root / rel
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("<html>%s</html>" % rel, encoding="utf-8", newline="\n")
    return root


def _assembly(tmp_path: Path, name: str = "asm", extra: str = "") -> Path:
    work = tmp_path / name
    frag = work / ".assemble_work" / "fragments"
    one = ["pet-friendly-hotels/m-one/a/index.html", "pet-friendly-hotels/m-one/b/index.html"]
    two = ["pet-friendly-hotels/m-two/c/index.html"]
    _tree(frag / "m-one", one)
    _tree(frag / "m-two", two)
    _tree(work / "site", one + two + (["pet-friendly-hotels/m-two/%s/index.html" % extra] if extra else []))
    return work


def _live_truth(site: Path, deploy_id: str = "d-live") -> RC.LiveTruth:
    bundle = APS.bundle_digest(APS.file_hashes(site))
    state = RI.LiveState(deploy_id, "d-prev", "d-prev", "c" * 40, bundle, "s", ("m-one", "m-two"),
                         OrderedDict((("m-one", 2), ("m-two", 1))), 3, 3, "rec.json", "auth")
    return RC.LiveTruth(state, RI.ReleaseIndex(), ())


def _seeded(tmp_path):
    work = _assembly(tmp_path)
    live = _live_truth(work / "site")
    store = RC.ReleaseStore(tmp_path / "store")
    seed = store.seed_from_assembly(work, {"market_fragments_included": ["m-one", "m-two"]}, live=live)
    return work, live, store, seed


def _gate(store, site, parent_digest):
    gates = OrderedDict()
    RC._parent_route_gate(gates, site, store, parent_digest, {})
    return gates["release.parent_routes_preserved"]


class TestReleaseStoreRoundTrip:

    def test_a_seeded_live_release_is_read_back_at_the_live_release_digest(self, tmp_path):
        work, live, store, seed = _seeded(tmp_path)
        # The 002 defect: the seed was written as seed-<bundle[:16]>.json, which
        # no reader ever asked for. It is now exactly the digest the parent
        # gate asks for.
        assert seed["release_digest"] == live.digest()
        assert not list((store.root / "releases").glob("seed-*.json"))
        assert (store.root / "releases" / ("%s.json" % live.digest().split(":")[-1])).is_file()
        stored = store.get_release(live.digest())
        assert RC.digest_of(RC.release_identity(stored)) == live.digest()
        assert json.loads(json.dumps(RC.release_identity(stored))) == json.loads(json.dumps(live.manifest()))
        assert sorted(store.fragment_digests(live.digest())) == ["m-one", "m-two"]
        assert _gate(store, work / "site", live.digest())["pass"] is True

    def test_the_pre_repair_seed_name_is_not_a_parent(self, tmp_path):
        work = _assembly(tmp_path)
        live = _live_truth(work / "site")
        store = RC.ReleaseStore(tmp_path / "store")
        legacy = store.root / "releases" / ("seed-%s.json" % live.state.bundle_sha256[:16])
        legacy.write_text(json.dumps({"bundle_object": "x", "markets": []}), encoding="utf-8")
        assert store.get_release(live.digest()) is None
        assert store.releases() == []
        assert _gate(store, work / "site", live.digest())["pass"] is False

    def test_a_wrong_digest_finds_no_parent(self, tmp_path):
        work, _live, store, _seed = _seeded(tmp_path)
        wrong = "sha256:" + "0" * 64
        assert store.get_release(wrong) is None
        assert _gate(store, work / "site", wrong)["pass"] is False

    def test_a_stale_release_is_not_the_new_parent_and_cannot_be_reseeded(self, tmp_path):
        work, old_live, store, _seed = _seeded(tmp_path)
        newer = _assembly(tmp_path, "newer", extra="d")
        new_live = _live_truth(newer / "site", deploy_id="d-newer")
        assert new_live.digest() != old_live.digest()
        assert store.get_release(new_live.digest()) is None
        assert _gate(store, newer / "site", new_live.digest())["pass"] is False
        with pytest.raises(RC.CoordinatorError) as exc:
            store.seed_from_assembly(work, {"market_fragments_included": ["m-one", "m-two"]}, live=new_live)
        assert exc.value.code == RC.BUNDLE_DIGEST_MISMATCH

    def test_a_corrupt_stored_record_fails_closed(self, tmp_path):
        work, live, store, _seed = _seeded(tmp_path)
        path = store.root / "releases" / ("%s.json" % live.digest().split(":")[-1])
        doc = json.loads(path.read_text(encoding="utf-8"))
        doc["total_profiles"] = doc["total_profiles"] + 1
        path.write_text(json.dumps(doc), encoding="utf-8")
        with pytest.raises(RC.CoordinatorError) as exc:
            store.get_release(live.digest())
        assert exc.value.code == RC.CANDIDATE_CORRUPT
        gate = _gate(store, work / "site", live.digest())
        assert gate["pass"] is False and RC.CANDIDATE_CORRUPT in gate["detail"]

    def test_a_corrupt_stored_bundle_object_fails_closed(self, tmp_path):
        work, live, store, _seed = _seeded(tmp_path)
        stored = store.get_release(live.digest())
        archive = store.root / "bundles" / ("%s.zip" % stored["bundle_object"].split(":")[-1])
        archive.write_bytes(archive.read_bytes() + b"tampered")
        gate = _gate(store, work / "site", live.digest())
        assert gate["pass"] is False and RC.CANDIDATE_CORRUPT in gate["detail"]

    def test_a_bundle_release_digest_mismatch_fails_closed(self, tmp_path):
        work, live, store, _seed = _seeded(tmp_path)
        with pytest.raises(RC.CoordinatorError) as exc:
            store.put_stored_release(live.manifest(), bundle_object="sha256:" + "1" * 64,
                                     bundle_sha256="not-the-live-bundle",
                                     fragments={"m-one": "x", "m-two": "y"})
        assert exc.value.code == RC.BUNDLE_DIGEST_MISMATCH
        path = store.root / "releases" / ("%s.json" % live.digest().split(":")[-1])
        doc = json.loads(path.read_text(encoding="utf-8"))
        doc["bundle_sha256"] = "not-the-live-bundle"
        path.write_text(json.dumps(doc), encoding="utf-8")
        with pytest.raises(RC.CoordinatorError) as exc:
            store.get_release(live.digest())
        assert exc.value.code == RC.CANDIDATE_CORRUPT

    def test_seeding_refuses_an_unverified_live(self, tmp_path):
        work = _assembly(tmp_path)
        live = _live_truth(work / "site")
        unverified = RC.LiveTruth(live.state, live.index, ("records disagree",))
        store = RC.ReleaseStore(tmp_path / "store")
        with pytest.raises(RC.CoordinatorError) as exc:
            store.seed_from_assembly(work, {"market_fragments_included": ["m-one", "m-two"]}, live=unverified)
        assert exc.value.code == RC.LIVE_NOT_VERIFIED

    def test_a_joining_markets_action_and_comparison_pages_are_implied(self):
        declared = {"/pet-friendly-hotels/%s/" % NEW_MARKET,
                    "/pet-friendly-hotels/%s/downtown/" % NEW_MARKET,
                    "/pet-friendly-hotels/%s/some-hotel/" % NEW_MARKET}
        implied_routes = ["/go/%s/some-hotel/%s/" % (NEW_MARKET, action)
                          for action in ("booking", "call", "directions", "official-website", "report-change")]
        implied_routes.append("/pet-friendly-hotels/%s/policy-comparison/" % NEW_MARKET)
        implied, undeclared = RC._split_implied_additions(sorted(implied_routes), declared)
        assert sorted(implied) == sorted(implied_routes) and undeclared == []

    def test_anything_else_new_stays_undeclared(self):
        declared = {"/pet-friendly-hotels/%s/" % NEW_MARKET, "/pet-friendly-hotels/%s/some-hotel/" % NEW_MARKET}
        smuggled = [
            "/go/%s/undeclared-hotel/booking/" % NEW_MARKET,          # an undeclared profile's action
            "/go/%s/some-hotel/steal/" % NEW_MARKET,                   # an unknown action
            "/go/other-market-nc/some-hotel/booking/",                 # another market's action
            "/pet-friendly-hotels/other-market-nc/policy-comparison/",  # another market's comparison
            "/pet-friendly-hotels/%s/undeclared-page/" % NEW_MARKET,  # an undeclared page
            "/about-us/",
        ]
        implied, undeclared = RC._split_implied_additions(smuggled, declared)
        assert implied == [] and sorted(undeclared) == sorted(smuggled)

    def test_the_parent_gate_fails_an_undeclared_addition_and_passes_an_implied_one(self, tmp_path):
        work, live, store, _seed = _seeded(tmp_path)
        site = tmp_path / "candidate"
        shutil.copytree(work / "site", site)
        _tree(site, ["pet-friendly-hotels/m-new/index.html", "pet-friendly-hotels/m-new/h/index.html",
                     "go/m-new/h/booking/index.html", "pet-friendly-hotels/m-new/policy-comparison/index.html"])
        delta = {"add_routes": ["/pet-friendly-hotels/m-new/", "/pet-friendly-hotels/m-new/h/"]}
        gates = OrderedDict()
        RC._parent_route_gate(gates, site, store, live.digest(), delta)
        assert gates["release.additions_are_declared"]["pass"] is True
        assert gates["release.additions_are_declared"]["implied_additions"] == 2
        _tree(site, ["pet-friendly-hotels/m-one/smuggled/index.html"])
        gates = OrderedDict()
        RC._parent_route_gate(gates, site, store, live.digest(), delta)
        assert gates["release.additions_are_declared"]["pass"] is False
        assert gates["release.additions_are_declared"]["undeclared_additions"] == 1

    def test_the_pilot_layout_still_verifies(self, tmp_path):
        store = RC.ReleaseStore(tmp_path / "store")
        release = OrderedDict((("bundle_object", "sha256:" + "2" * 64), ("markets", [{"market_id": "m-one"}])))
        store.put_release(release)
        assert store.get_release(RC.digest_of(release)) == release


# --------------------------------------------------------------------------- #
# 4. The paid ledger narrows on content, never on its path.
# --------------------------------------------------------------------------- #

def _attempt(market_id: str, key: str) -> OrderedDict:
    return LEDGER.build_attempt({"identity_key": key, "outcome": "VALID", "provider": "firecrawl",
                                 "canonical_url": "https://example.com/%s" % key},
                                market_id=market_id, work_order="PTF-TEST-001", run_id="run-%s" % market_id,
                                cost_usd_minor=1.0, firecrawl_credits=0.5)


def _ledger_bytes(tmp_path: Path, rows, mutate=None) -> bytes:
    doc = LEDGER.new_ledger()
    doc["attempts"] = [copy.deepcopy(r) for r in rows]
    if mutate:
        mutate(doc)
    path = tmp_path / ("ledger-%d.json" % len(list(tmp_path.glob("ledger-*.json"))))
    LEDGER.save(path, doc)
    return path.read_bytes()


@pytest.fixture
def ledger(tmp_path, monkeypatch):
    base_rows = [_attempt("aa-one", "h1"), _attempt("bb-two", "h2")]
    sides = {}
    sides["base"] = _ledger_bytes(tmp_path, base_rows)

    def _set_head(data: bytes) -> None:
        sides["head"] = data

    monkeypatch.setattr(REG, "bytes_at", lambda rev, rel: sides.get(rev))
    return OrderedDict((("rows", base_rows), ("set_head", _set_head), ("tmp", tmp_path)))


def _prove(status="M"):
    return REG.prove_paid_ledger_append("base", "head", NEW_MARKET, status)


class TestPaidLedgerAppend:

    def test_own_market_rows_appended_only_narrow(self, ledger):
        rows = ledger["rows"] + [_attempt(NEW_MARKET, "n1"), _attempt(NEW_MARKET, "n2")]
        ledger["set_head"](_ledger_bytes(ledger["tmp"], rows))
        proof = _prove()
        assert proof["passed"] is True, proof["failed_conditions"]
        assert proof["appended_rows"] == 2

    def _refused(self, ledger, rows, condition, mutate=None, status="M"):
        ledger["set_head"](_ledger_bytes(ledger["tmp"], rows, mutate))
        proof = _prove(status)
        assert proof["passed"] is False
        assert proof["failed_conditions"][0] == condition, proof["failed_conditions"]
        return proof

    def test_a_mutated_prior_row_fails(self, ledger):
        rows = copy.deepcopy(ledger["rows"]) + [_attempt(NEW_MARKET, "n1")]
        rows[0]["cost_usd_minor"] = 99.0
        self._refused(ledger, rows, "prefix")

    def test_a_deleted_prior_row_fails(self, ledger):
        self._refused(ledger, ledger["rows"][1:] + [_attempt(NEW_MARKET, "n1")], "prefix")

    def test_reordered_prior_rows_fail(self, ledger):
        self._refused(ledger, list(reversed(ledger["rows"])) + [_attempt(NEW_MARKET, "n1")], "prefix")

    def test_a_prior_row_replaced_by_an_own_market_row_fails(self, ledger):
        self._refused(ledger, [ledger["rows"][0], _attempt(NEW_MARKET, "n1")], "prefix")

    def test_an_appended_foreign_market_row_fails(self, ledger):
        self._refused(ledger, ledger["rows"] + [_attempt("cc-three", "f1")], "own_market")

    def test_a_mixed_own_and_foreign_append_fails(self, ledger):
        rows = ledger["rows"] + [_attempt(NEW_MARKET, "n1"), _attempt("cc-three", "f1")]
        self._refused(ledger, rows, "own_market")

    def test_an_appended_row_missing_market_id_fails(self, ledger):
        row = _attempt(NEW_MARKET, "n1")
        del row["market_id"]
        self._refused(ledger, ledger["rows"] + [row], "appended_rows")

    def test_an_appended_row_with_an_unknown_field_fails(self, ledger):
        row = _attempt(NEW_MARKET, "n1")
        row["surprise"] = "x"
        self._refused(ledger, ledger["rows"] + [row], "appended_rows")

    def test_an_appended_row_with_a_wrong_type_fails(self, ledger):
        row = _attempt(NEW_MARKET, "n1")
        row["terminal"] = "yes"
        self._refused(ledger, ledger["rows"] + [row], "appended_rows")

    def test_an_appended_row_with_a_forged_attempt_id_fails(self, ledger):
        row = _attempt(NEW_MARKET, "n1")
        row["attempt_id"] = "0" * 16
        self._refused(ledger, ledger["rows"] + [row], "appended_rows")

    def test_a_schema_change_fails(self, ledger):
        rows = ledger["rows"] + [_attempt(NEW_MARKET, "n1")]
        self._refused(ledger, rows, "header", mutate=lambda d: d.__setitem__("what_this_is", "rewritten"))

    def test_a_provenance_change_fails(self, ledger):
        rows = ledger["rows"] + [_attempt(NEW_MARKET, "n1")]
        self._refused(ledger, rows, "header", mutate=lambda d: d.__setitem__("provenance", {"x": 1}))

    def test_a_format_change_fails(self, ledger):
        doc = LEDGER.new_ledger()
        doc["attempts"] = ledger["rows"] + [_attempt(NEW_MARKET, "n1")]
        ledger["set_head"]((json.dumps(doc, indent=1) + "\n").encode("utf-8"))
        proof = _prove()
        assert proof["passed"] is False and proof["failed_conditions"][0] == "format"

    def test_invalid_json_at_head_fails(self, ledger):
        ledger["set_head"](b"{ not json")
        proof = _prove()
        assert proof["passed"] is False and proof["failed_conditions"][0] == "parse"

    def test_a_head_the_ledger_validator_refuses_fails(self, ledger, monkeypatch):
        rows = ledger["rows"] + [_attempt(NEW_MARKET, "n1")]
        ledger["set_head"](_ledger_bytes(ledger["tmp"], rows))

        def _refuse(_doc):
            raise LEDGER.PaidLedgerError("refused")
        monkeypatch.setattr(LEDGER, "LedgerIndex", _refuse)
        proof = _prove()
        assert proof["passed"] is False and proof["failed_conditions"] == ["validator"]

    def test_an_added_or_deleted_ledger_fails(self, ledger):
        ledger["set_head"](_ledger_bytes(ledger["tmp"], ledger["rows"] + [_attempt(NEW_MARKET, "n1")]))
        for status in ("A", "D", "R"):
            proof = _prove(status)
            assert proof["passed"] is False and proof["failed_conditions"][0] == "status"

    def test_the_path_alone_earns_nothing_in_the_change_set(self, ledger, monkeypatch):
        """The ledger path, carrying a foreign append, lands in SHARED inside
        the real change-set partition."""
        ledger["set_head"](_ledger_bytes(ledger["tmp"], ledger["rows"] + [_attempt("cc-three", "f1")]))
        monkeypatch.setattr(REG, "registered_market_ids_at",
                            lambda rev: ("aa-one",) if rev == "base" else ("aa-one", NEW_MARKET))
        rows = [OrderedDict((("path", REG.PAID_ATTEMPT_LEDGER_PATH), ("status", "M"),
                             ("classes", ["UNCLASSIFIED"])))]
        gate = REG.classify_change_set(rows, base="base", head="head", blockers=[])
        detail = gate["result"]["detail"]
        assert detail["buckets"][REG.PAID_ATTEMPT_LEDGER_PATH] == REG.BUCKET_SHARED
        assert gate["result"]["pass"] is False

    def test_the_real_augusta_append_passes_and_is_not_tampas(self, monkeypatch):
        monkeypatch.undo()
        assert REG.prove_paid_ledger_append("fde606aa", "ff427c27", "augusta-ga", "M")["passed"] is True
        refused = REG.prove_paid_ledger_append("fde606aa", "ff427c27", "tampa-fl", "M")
        assert refused["passed"] is False and refused["failed_conditions"][0] == "own_market"


# --------------------------------------------------------------------------- #
# 5. The narrow lane rejects every change the order names.
# --------------------------------------------------------------------------- #

@pytest.fixture(scope="module")
def live_index():
    idx, state, problems = RI.live_index()
    assert not problems, problems
    return idx, state


@pytest.fixture(scope="module")
def stale_package():
    """A real committed package sealed against a PREVIOUS live parent."""
    packages = sorted((SMP.LAUNCH_PACKAGE / "markets" / "packages").glob("*/pkg-*.json"))
    state = RI.current_verified_live()
    for path in packages:
        package = SMP.read_sealed(path)
        parent = package.get("parent_live_state") or {}
        if parent.get("live_deploy_id") and parent.get("live_deploy_id") != state.deploy_id:
            return package
    pytest.fail("no committed package sealed against an earlier live parent")


def _row(path: str, status: str = "M") -> OrderedDict:
    classes, rule = RD.classify_path(path)
    return OrderedDict((("path", path), ("status", status), ("classes", list(classes)), ("rule", rule)))


def _gate_for(monkeypatch, base_markets, head_markets, rows):
    monkeypatch.setattr(REG, "registered_market_ids_at",
                        lambda rev: tuple(base_markets) if rev == "base" else tuple(head_markets))
    return REG.classify_change_set(rows, base="base", head="head", blockers=[])


class TestTheNarrowLaneRejects:

    def test_a_stale_live_base(self, live_index, stale_package):
        idx, state = live_index
        result = REG.check_sealed_package(stale_package, stale_package["market_id"], state, idx, OrderedDict())
        assert result["status"] == REG.FAIL
        assert any("parent_live_state.live_deploy_id" in p for p in result["detail"]["problems"])
        stale = OrderedDict((("RESOLVED", "YES"), ("head_contains_live", False), ("head_commit", "a" * 40),
                             ("CURRENT_LIVE_SOURCE_COMMIT", "b" * 40), ("live_deploy_id", state.deploy_id)))
        with pytest.raises(LANE.LaneRefusal) as exc:
            LANE.require_current_live(stale, worktree_live=state)
        assert exc.value.code == LANE.STALE_LIVE_BASE

    def test_an_unauthorized_market_removal(self, monkeypatch, live_index):
        gate = _gate_for(monkeypatch, ["aa-one", "bb-two"], ["aa-one"], [])
        assert gate["result"]["pass"] is False and "removes no market" in gate["result"]["why"]
        _idx, state = live_index
        truth = RC.LiveTruth(state, RI.ReleaseIndex(), ())
        doc = copy.deepcopy(RC.LP.load_participation())
        dropped = state.participating_markets[0]
        doc["markets"] = [row for row in doc["markets"] if row["market_id"] != dropped]
        with pytest.raises(RC.CoordinatorError) as exc:
            RC._final_membership(truth, doc, RC.NO_DELTA, None, {})
        assert exc.value.code == RC.UNAUTHORIZED_REMOVAL

    def test_a_second_unexpected_market_addition(self, monkeypatch, live_index):
        gate = _gate_for(monkeypatch, ["aa-one"], ["aa-one", NEW_MARKET, "zz-second-nc"], [])
        assert gate["result"]["pass"] is False and "exactly one" in gate["result"]["why"]
        _idx, state = live_index
        truth = RC.LiveTruth(state, RI.ReleaseIndex(), ())
        doc = copy.deepcopy(RC.LP.load_participation())
        for market in (NEW_MARKET, "zz-second-nc"):
            doc["markets"].append(OrderedDict((("market_id", market),
                                               ("launch_status", RC.LP.FOUNDER_AUTHORIZED_FOR_LAUNCH))))
        with pytest.raises(RC.CoordinatorError) as exc:
            RC._final_membership(truth, doc, RC.ADD, NEW_MARKET, {"add": [NEW_MARKET]})
        assert exc.value.code == RC.UNAUTHORIZED_ADDITION

    def test_a_changed_shared_implementation(self, monkeypatch):
        gate = _gate_for(monkeypatch, ["aa-one"], ["aa-one", NEW_MARKET],
                         [_row("scripts/pettripfinder/assemble_production_site.py")])
        detail = gate["result"]["detail"]
        assert gate["result"]["pass"] is False
        assert detail["buckets"]["scripts/pettripfinder/assemble_production_site.py"] == REG.BUCKET_SHARED

    def test_a_behavior_bearing_release_contract_edit(self):
        contracts = OrderedDict()
        for path in sorted((RD.REPO_ROOT / "deploy" / "netlify" / "release_contracts").glob("*.json")):
            contracts[path.stem] = path.read_bytes()
        market, raw = next(iter(contracts.items()))
        doc = json.loads(raw.decode("utf-8-sig"), object_pairs_hook=OrderedDict)
        doc["publish"] = OrderedDict((("changed", True),))
        others = OrderedDict((m, b) for m, b in contracts.items() if m != market)
        result = REG.check_release_contract(json.dumps(doc).encode("utf-8"), market, others, verify=lambda m: [])
        assert result["status"] == REG.FAIL
        assert "publish" in result["why"]

    def test_a_broken_participation_lineage(self):
        base = (RD.REPO_ROOT / REG.PARTICIPATION_PATH).read_bytes()
        doc = json.loads(base.decode("utf-8-sig"), object_pairs_hook=OrderedDict)
        # The Augusta/Tampa merge shape: a registration row appears while an
        # existing market's row is silently lost.
        lost = doc["markets"][0]["market_id"]
        doc["markets"] = [r for r in doc["markets"] if r["market_id"] != lost] + [OrderedDict((
            ("market_id", NEW_MARKET), ("launch_status", "SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH"),
            ("note", "x")))]
        result = REG.check_participation(base, json.dumps(doc).encode("utf-8"), NEW_MARKET)
        assert result["status"] == REG.FAIL

    def test_a_stale_or_mismatched_receipt(self, live_index, stale_package, tmp_path):
        idx, state = live_index
        truth = RC.LiveTruth(state, idx, ())
        with pytest.raises(RC.CoordinatorError) as exc:
            RC.bound_fast_receipt(stale_package, truth)
        assert exc.value.code == RC.RECEIPT_NOT_BOUND
        assert REG.check_fast_receipt(stale_package, stale_package["market_id"], state, idx)["status"] == REG.FAIL
        with pytest.raises(RC.CoordinatorError) as exc:
            RC.bound_fast_receipt(stale_package, truth, receipts_dir=tmp_path / "no-receipts")
        assert exc.value.code == RC.RECEIPT_NOT_BOUND

    def test_a_missing_incoming_package(self, live_index, tmp_path):
        idx, state = live_index
        # The lookup that explains itself used to raise a TypeError here.
        lookup = OrderedDict((("why", "packages are read from the working tree only"),))
        result = REG.check_sealed_package(None, NEW_MARKET, state, idx, lookup)
        assert result["status"] == REG.FAIL
        assert result["detail"]["lookup_why"] == lookup["why"]
        with pytest.raises(RC.CoordinatorError) as exc:
            RC.stage(package=None, delta_kind=RC.ADD, live=RC.LiveTruth(state, idx, ()),
                     store=RC.ReleaseStore(tmp_path / "store"), candidates_root=tmp_path / "candidates")
        assert exc.value.code == RC.INTENDED_DELTA_MISMATCH

    def test_an_identity_or_route_collision(self, live_index):
        idx, _state = live_index
        victim = idx.markets[sorted(idx.participating)[0]]
        clone = RI.MarketIndex(**{**victim.__dict__, "market_id": NEW_MARKET, "participating": True})
        proposed = RI.compose(idx, clone, participates=True)
        report = RI.compare(idx, proposed, package_market=NEW_MARKET,
                            intended_delta={"add_routes": list(clone.routes)})
        codes = {f["code"] for f in report["findings"]}
        assert report["passed"] is False
        assert codes & {RI.DUPLICATE_ROUTE, RI.CROSS_MARKET_IDENTITY_COLLISION}

    def test_a_corrupted_parent_release(self, tmp_path):
        work, live, store, _seed = _seeded(tmp_path)
        path = store.root / "releases" / ("%s.json" % live.digest().split(":")[-1])
        path.write_text("{ corrupt", encoding="utf-8")
        gate = _gate(store, work / "site", live.digest())
        assert gate["pass"] is False and RC.CANDIDATE_CORRUPT in gate["detail"]
        with pytest.raises(RC.CoordinatorError):
            store.fragment_digests(live.digest())

    def test_a_release_store_digest_mismatch(self, tmp_path):
        work, live, store, _seed = _seeded(tmp_path)
        good = store.root / "releases" / ("%s.json" % live.digest().split(":")[-1])
        wrong = store.root / "releases" / ("%s.json" % ("9" * 64))
        wrong.write_bytes(good.read_bytes())
        with pytest.raises(RC.CoordinatorError) as exc:
            store.get_release("sha256:" + "9" * 64)
        assert exc.value.code == RC.CANDIDATE_CORRUPT

    def test_an_unknown_dependency(self, monkeypatch):
        unknown = "launch_packages/pettripfinder/a_new_global_input.json"
        gate = _gate_for(monkeypatch, ["aa-one"], ["aa-one", NEW_MARKET], [_row(unknown, "A")])
        detail = gate["result"]["detail"]
        assert gate["result"]["pass"] is False
        assert detail["buckets"][unknown] in (REG.BUCKET_UNKNOWN, REG.BUCKET_SHARED)


# --------------------------------------------------------------------------- #
# 6. Reuse staging feeds the EXISTING deployment path, and only under the
#    committed participation.
# --------------------------------------------------------------------------- #

class TestDeploymentCompatibility:

    def test_the_assembler_uses_the_extracted_description(self):
        import inspect
        source = inspect.getsource(APS._assemble_uncached)
        assert "describe_composed_bundle(" in source and "record_assembly_gates(" in source
        assert "_run_participation_gates" not in source, "the gates must live in ONE place"
        described = inspect.getsource(APS.describe_composed_bundle)
        for gate_call in ("_run_global_publish_gates", "_run_participation_gates", "_run_migration_gate",
                          "run_measurement_gates", "run_affiliate_gates", "broken_internal_links",
                          "canonical_violations"):
            assert gate_call in described

    def test_a_projected_membership_describes_no_deployable_artifact(self, tmp_path):
        chosen, _eligibility = APS.select_markets()
        manifest = OrderedDict((("participating_markets", [m.market_id for m in chosen] + [NEW_MARKET]),
                                ("deployment_artifact_digest", "x")))
        candidate = RC.Candidate(tmp_path, manifest, OrderedDict(), None, OrderedDict())
        with pytest.raises(RC.CoordinatorError) as exc:
            RC.deployment_bundle_manifest(candidate)
        assert exc.value.code == RC.NOT_DEPLOYABLE_UNDER_COMMITTED_PARTICIPATION

    def test_the_coordinator_never_enables_production_activation(self):
        assert RC.REAL_PRODUCTION_ACTIVATION == "DISABLED"
        gate = RC.load_production_gate()
        assert gate["RELEASE_COORDINATOR_PRODUCTION_ENABLED"] == "NO"
        assert gate["RELEASE_COORDINATOR_PRODUCTION_ALLOWED_MARKETS"] == []
