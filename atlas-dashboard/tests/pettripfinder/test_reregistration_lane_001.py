"""PTF-CANONICAL-REREGISTRATION-LANE-REPAIR-001 -- the focused battery.

West Palm Beach was registered, founder-authorized, corrected BEFORE any
deployment, its deployment authorization SUPERSEDED -- and could not be
re-registered without a broad run: the registration proof demanded a NEW row
and an unchanged founder-authorized set, the decision chain is monotone, and
the base could never include the market's own prior registration.

Everything here is SYNTHETIC. The lifecycle runs in a throwaway git repository
with three invented markets (``alpha-zz`` and ``beta-zz`` live, ``gamma-zz``
the corrected one); the classifier's git seams are pointed at it, and only
the checks this order did not touch (package seal, FAST receipt, expected
release, identity routes, contract derivation, global regeneration) are
stubbed -- each is proven by its own audited battery. No production file is
written.
"""

from __future__ import annotations

import copy
import dataclasses
import hashlib
import json
import shutil
import subprocess
import tempfile
from collections import OrderedDict
from pathlib import Path
from types import SimpleNamespace

import pytest

from scripts.pettripfinder import deployment_authorization as DA
from scripts.pettripfinder import launch_participation as LP
from scripts.pettripfinder import market_authority as MA
from scripts.pettripfinder import market_local_isolation as ISO
from scripts.pettripfinder import registration_data_only as REG
from scripts.pettripfinder import registration_release_lane as LANE
from scripts.pettripfinder import regression_delta as RD
from scripts.pettripfinder import release_index as RI

MARKET = "gamma-zz"
US = "gamma_zz"
LIVE_MARKETS = ("alpha-zz", "beta-zz")
PREFIX = "atlas-dashboard/"
PKG_A = "sha256:" + "a1" * 32
PKG_B = "sha256:" + "b2" * 32
BUNDLE_A = "c3" * 32
W_LIVE = "PTF-SYNTH-LIVE-001"
W_REG = "PTF-SYNTH-GAMMA-REGISTRATION-002"
W_AUTH = "PTF-SYNTH-GAMMA-FOUNDER-AUTHORIZATION-003"
W_CORR = "PTF-SYNTH-GAMMA-CORRECTION-004"
W_REREG = "PTF-SYNTH-GAMMA-REREGISTRATION-005"
AUTH_ID = "ptf-auth-gamma-003-" + BUNDLE_A[:12]
AUTH_REL = "deploy/netlify/deployment_authorizations/%s.json" % AUTH_ID
RECORD_REL = "deploy/netlify/deployment_records/ptf-deploy-live-001.json"
CONTRACT_REL = "deploy/netlify/release_contracts/%s.json" % MARKET
PKG_DIR = "launch_packages/pettripfinder/markets/packages/%s/" % MARKET
HELPER_REL = "scripts/pettripfinder/%s_identity_fix_004.py" % US

BLOCK_A = OrderedDict((("census", 20), ("pet_friendly", 8), ("verified_no_pets", 4), ("resolved", 12),
                       ("unresolved", 8), ("out_of_category", 0), ("profiles", 8), ("corridor_routes", 2)))
BLOCK_B = OrderedDict((("census", 20), ("pet_friendly", 9), ("verified_no_pets", 4), ("resolved", 13),
                       ("unresolved", 7), ("out_of_category", 0), ("profiles", 9), ("corridor_routes", 2)))
LIVE_STATE = RI.LiveState("d" * 24, "e" * 24, "e" * 24, "f" * 40, "1" * 64, "2" * 64, LIVE_MARKETS,
                          OrderedDict((("alpha-zz", 10), ("beta-zz", 12))), 22, 30, "ptf-deploy-live-001.json",
                          "ptf-auth-live-001")


# --------------------------------------------------------------------------- #
# Synthetic documents.
# --------------------------------------------------------------------------- #

def _dump(doc) -> bytes:
    return (json.dumps(doc, indent=1, ensure_ascii=False) + "\n").encode("utf-8")


def _sha(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _load(data: bytes):
    return json.loads(data.decode("utf-8"), object_pairs_hook=OrderedDict)


def _row(mid: str, status: str) -> OrderedDict:
    return OrderedDict((("market_id", mid), ("launch_status", status), ("note", "synthetic %s" % mid)))


def _p0() -> OrderedDict:
    root = OrderedDict((("work_order", "PTF-SYNTH-ROOT-000"), ("sha256", "0" * 64),
                        ("founder_authorized", list(LIVE_MARKETS))))
    return OrderedDict((
        ("schema", LP.PARTICIPATION_SCHEMA), ("what_this_is", "synthetic participation"),
        ("decision", OrderedDict((
            ("work_order", W_LIVE), ("decided_by", "founder"), ("decided_on", "2026-01-01"),
            ("reason", "the synthetic live release"), ("supersedes", copy.deepcopy(root)),
            ("lineage", OrderedDict((("what_this_is", LP.LINEAGE_NOTE), ("records", [copy.deepcopy(root)]))))))),
        ("launch_statuses", OrderedDict((s, s.lower()) for s in LP.LAUNCH_STATUSES)),
        ("markets", [_row(m, LP.FOUNDER_AUTHORIZED_FOR_LAUNCH) for m in LIVE_MARKETS]),
    ))


def _reissue(prev: OrderedDict, rows, **block) -> OrderedDict:
    prev_bytes = _dump(prev)
    doc = _load(prev_bytes)
    doc["markets"] = sorted(rows, key=lambda r: r["market_id"])
    with tempfile.TemporaryDirectory() as scratch:
        path = Path(scratch) / "launch_participation.json"
        path.write_bytes(prev_bytes)
        doc["decision"] = LP.extend_decision(prev, _sha(prev_bytes), path=path, **block)
    return doc


def _p1(p0) -> OrderedDict:
    return _reissue(p0, list(p0["markets"]) + [_row(MARKET, LP.SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH)],
                    work_order=W_REG, decided_by=W_REG, decided_on="2026-01-02", reason="register gamma",
                    markets_added=[MARKET], founder_authorized_set_unchanged=True)


def _p2(p1, package_digest=PKG_A) -> OrderedDict:
    basis = OrderedDict((("market_id", MARKET),))
    if package_digest is not None:
        basis["registered_package_digest"] = package_digest
    rows = [r if r["market_id"] != MARKET else _row(MARKET, LP.FOUNDER_AUTHORIZED_FOR_LAUNCH) for r in p1["markets"]]
    return _reissue(p1, rows, work_order=W_AUTH, decided_by="founder", decided_on="2026-01-03",
                    reason="the founder authorizes gamma package A", decision_basis=basis)


def _entry(p2_bytes: bytes, **overrides) -> OrderedDict:
    entry = OrderedDict((
        ("market_id", MARKET),
        ("authorizing_decision", OrderedDict((("work_order", W_AUTH), ("sha256", _sha(p2_bytes))))),
        ("superseded_package_digest", PKG_A),
        ("corrected_package_digest", PKG_B),
        ("deployment_authorizations", [OrderedDict((("authorization_id", AUTH_ID), ("bundle_sha256", BUNDLE_A),
                                                    ("authorization_status", "SUPERSEDED")))]),
        ("market_live", False),
        ("reauthorization_required", True),
    ))
    entry.update(overrides)
    return entry


def _rereg(p2, entry=None, *, status=LP.SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH,
           decided_by=W_REREG, **extra) -> OrderedDict:
    entry = entry if entry is not None else _entry(_dump(p2))
    rows = [r if r["market_id"] != MARKET else _row(MARKET, status) for r in p2["markets"]]
    block = {LP.FOUNDER_AUTHORIZATION_SUPERSEDED: [entry]} if entry else {}
    block.update(extra)
    return _reissue(p2, rows, work_order=W_REREG, decided_by=decided_by, decided_on="2026-01-05",
                    reason="re-register gamma after a pre-deploy correction", **block)


def _problems(doc) -> list:
    with tempfile.TemporaryDirectory() as scratch:
        path = Path(scratch) / "launch_participation.json"
        path.write_bytes(_dump(doc))
        return LP.decision_problems(doc, path=path)


def _contract(block: OrderedDict, version: int) -> OrderedDict:
    return OrderedDict((
        ("schema", "synthetic-release-contract"), ("market_id", MARKET), ("version", version),
        ("identity_census", OrderedDict((("expected_count", block["census"]),))),
        ("reconciliation", OrderedDict((("confirmed_identities", block["census"]),
                                        ("published_pet_friendly", block["pet_friendly"]),
                                        ("verified_no_pets", block["verified_no_pets"]),
                                        ("resolved", block["resolved"]), ("unresolved", block["unresolved"])))),
        ("policy_package", OrderedDict((("expected_record_count", block["pet_friendly"]),))),
        ("public_surface", OrderedDict((("public_hotel_profile_count", block["profiles"]),))),
        ("routes", OrderedDict((("hotel_route_count", block["profiles"]),
                                ("published_corridor_route_count", block["corridor_routes"])))),
    ))


def _auth(contract_sha: str, status: str = "AUTHORIZED") -> OrderedDict:
    doc = OrderedDict((
        ("schema", DA.AUTHORIZATION_SCHEMA), ("authorization_id", AUTH_ID), ("authorized_by", "founder"),
        ("authorized_at", "2026-01-03T00:00:00+00:00"), ("work_order", W_AUTH), ("bundle_sha256", BUNDLE_A),
        ("participating_markets", sorted(LIVE_MARKETS + (MARKET,))),
        ("founder_authorized_markets", sorted(LIVE_MARKETS + (MARKET,))),
        ("release_contracts", [OrderedDict((("market_id", MARKET), ("path", CONTRACT_REL), ("sha256", contract_sha)))]),
        ("target_site", "synthetic-prod"), ("authorization_status", DA.PREPARED),
        ("status_history", [OrderedDict((("status", DA.PREPARED), ("at", "2026-01-03T00:00:00+00:00"),
                                         ("note", "bound")))]),
    ))
    doc = DA.transition(doc, DA.AUTHORIZED, at="2026-01-03T00:00:00+00:00", note="founder order")
    if status == DA.SUPERSEDED:
        doc = DA.transition(doc, DA.SUPERSEDED, at="2026-01-04T00:00:00+00:00", note="pre-deploy correction")
    elif status == DA.DEPLOYED:
        doc = DA.transition(doc, DA.DEPLOYED, at="2026-01-04T00:00:00+00:00", note="consumed")
    return doc


def _package(digest: str, block: OrderedDict) -> OrderedDict:
    return OrderedDict((("package_id", "pkg-%s-%s" % (MARKET, digest[7:23])), ("package_digest", digest),
                        ("market_id", MARKET), ("counts", block)))


# --------------------------------------------------------------------------- #
# The throwaway repository: register A -> authorize -> deploy-auth A ->
# (never deploy) -> correct -> package B -> supersede A -> re-register B.
# --------------------------------------------------------------------------- #

def _git(root: Path, *args: str) -> str:
    proc = subprocess.run(["git", *args], cwd=str(root), capture_output=True, text=True)
    assert proc.returncode == 0, proc.stderr
    return proc.stdout.strip()


def _put(dash: Path, rel: str, content) -> None:
    path = dash / rel
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(content if isinstance(content, bytes) else
                     (_dump(content) if not isinstance(content, str) else content.encode("utf-8")))


def _commit(root: Path, message: str) -> str:
    _git(root, "add", "-A")
    _git(root, "commit", "-q", "-m", message)
    return _git(root, "rev-parse", "HEAD")


def _pin(blocks: "OrderedDict[str, OrderedDict]", reviewed_by: str) -> OrderedDict:
    return OrderedDict((("schema", "synthetic-market-state"), ("reviewed_by", reviewed_by),
                        ("markets", OrderedDict(sorted(blocks.items())))))


def _closure(markets) -> OrderedDict:
    inputs = sorted(p for m in markets for p in REG.closure_inputs_for(m))
    return OrderedDict((("shared_data_inputs", inputs), ("remeasured_by", [])))


def _live_block(n: int) -> OrderedDict:
    return OrderedDict((("census", n), ("pet_friendly", n), ("verified_no_pets", 0), ("resolved", n),
                        ("unresolved", 0), ("out_of_category", 0), ("profiles", n), ("corridor_routes", 1),
                        ("last_moved_by", W_LIVE)))


def _stub_market_authority(monkeypatch) -> None:
    ids = LIVE_MARKETS + (MARKET,)
    monkeypatch.setattr(MA, "load_markets", lambda: [SimpleNamespace(market_id=m) for m in ids])


def _build(root: Path, *, auth_rewrites_live_manifest: bool = False, after_auth=None) -> "OrderedDict[str, str]":
    root.mkdir(parents=True)
    dash = root / "atlas-dashboard"
    _git(root, "init", "-q", "-b", "main")
    _git(root, "config", "user.email", "t@example.com")
    _git(root, "config", "user.name", "t")
    _git(root, "config", "core.autocrlf", "false")
    _git(root, "config", "core.longpaths", "true")   # pytest's tmp paths pass MAX_PATH on Windows
    commits: "OrderedDict[str, str]" = OrderedDict()

    # L -- the live release: alpha + beta, one deployment record.
    p0 = _p0()
    _put(dash, REG.PARTICIPATION_PATH, p0)
    _put(dash, RECORD_REL, OrderedDict((("deployment_record_id", "ptf-deploy-live-001"),
                                        ("participating_markets", list(LIVE_MARKETS)), ("final_status", "DEPLOYED"))))
    _put(dash, "deploy/netlify/deployment_authorizations/ptf-auth-live-001.json",
         OrderedDict((("authorization_id", "ptf-auth-live-001"), ("authorization_status", "DEPLOYED"),
                      ("participating_markets", list(LIVE_MARKETS)), ("bundle_sha256", "1" * 64))))
    _put(dash, "deploy/netlify/global_deployment_manifest.json", OrderedDict((("bundle_sha256", "1" * 64),)))
    _put(dash, REG.DEPLOYMENT_STATE_PIN_PATH, OrderedDict((("live_deploy_id", "d" * 24),)))
    _put(dash, REG.MARKET_STATE_PIN_PATH, _pin(OrderedDict((m, _live_block(10 + i)) for i, m in enumerate(LIVE_MARKETS)),
                                               W_LIVE))
    _put(dash, REG.CLOSURE_PATH, _closure(LIVE_MARKETS))
    for m in LIVE_MARKETS:
        _put(dash, "launch_packages/pettripfinder/markets/%s.json" % m, OrderedDict((("market_id", m),)))
        _put(dash, "deploy/netlify/release_contracts/%s.json" % m, OrderedDict((("market_id", m),)))
        _put(dash, "launch_packages/pettripfinder/markets/authority/%s/seed_businesses.csv" % m, "name\n%s hotel\n" % m)
    _put(dash, "README.md", "synthetic factory\n")
    commits["L"] = _commit(root, "L the live release")

    # REG -- register gamma with package A.
    p1 = _p1(p0)
    contract_a = _dump(_contract(BLOCK_A, 1))
    _put(dash, "launch_packages/pettripfinder/markets/%s.json" % MARKET, OrderedDict((("market_id", MARKET),)))
    _put(dash, CONTRACT_REL, contract_a)
    _put(dash, "launch_packages/pettripfinder/markets/authority/%s/seed_businesses.csv" % MARKET,
         "name\napple ten hospitality management inc\n")
    _put(dash, "launch_packages/pettripfinder/identity_census/%s.json" % MARKET,
         OrderedDict((("hotels", [OrderedDict((("canonical_name", "Apple Ten Hospitality Management Inc"),))]),)))
    _put(dash, PKG_DIR + "pkg-%s-%s.json" % (MARKET, PKG_A[7:23]), _package(PKG_A, BLOCK_A))
    _put(dash, REG.PARTICIPATION_PATH, p1)
    _put(dash, REG.CLOSURE_PATH, _closure(LIVE_MARKETS + (MARKET,)))
    blocks = OrderedDict((m, _live_block(10 + i)) for i, m in enumerate(LIVE_MARKETS))
    blocks[MARKET] = OrderedDict(BLOCK_A, last_moved_by=W_REG)
    _put(dash, REG.MARKET_STATE_PIN_PATH, _pin(blocks, W_REG))
    commits["REG"] = _commit(root, "REG register gamma (package A)")

    # AUTH -- the founder authorizes package A; deployment authorization A is
    # written AUTHORIZED; nothing is deployed.
    p2 = _p2(p1)
    _put(dash, REG.PARTICIPATION_PATH, p2)
    _put(dash, AUTH_REL, _auth(_sha(contract_a)))
    _put(dash, "deploy/netlify/global_deployment_manifest_candidate_gamma_003.json",
         OrderedDict((("bundle_sha256", BUNDLE_A),)))
    _put(dash, "scripts/pettripfinder/%s_deployment_authorization_003.py" % US,
         "from scripts.pettripfinder import deployment_authorization as DA\n")
    if auth_rewrites_live_manifest:
        _put(dash, "deploy/netlify/global_deployment_manifest.json", OrderedDict((("bundle_sha256", BUNDLE_A),)))
    commits["AUTH"] = _commit(root, "AUTH founder authorizes gamma package A (not deployed)")
    if after_auth is not None:
        # PTF-REREGISTRATION-TRUSTED-FACTORY-BASELINE-CORRECTION-002: a factory
        # lineage merged into the market line after the authorizing commit.
        after_auth(root, dash, commits)

    # CORR -- a market-local correction and the corrected package B.
    _put(dash, "launch_packages/pettripfinder/markets/authority/%s/seed_businesses.csv" % MARKET,
         "name\nhilton garden inn boca raton\n")
    _put(dash, "launch_packages/pettripfinder/identity_census/%s.json" % MARKET,
         OrderedDict((("hotels", [OrderedDict((("canonical_name", "Hilton Garden Inn Boca Raton"),))]),)))
    _put(dash, CONTRACT_REL, _contract(BLOCK_B, 2))
    _put(dash, HELPER_REL, '"""gamma-zz: a licensee identity is not a hotel name."""\nimport json\n\n\n'
                           'def rule(record):\n    return json.dumps(record)\n')
    _put(dash, PKG_DIR + "pkg-%s-%s.json" % (MARKET, PKG_B[7:23]), _package(PKG_B, BLOCK_B))
    _put(dash, "launch_packages/pettripfinder/markets/reports/%s_identity_correction_004.json" % US,
         OrderedDict((("work_order", W_CORR),)))
    commits["CORR"] = _commit(root, "CORR correct gamma, seal package B")

    # SUP -- deployment authorization A AUTHORIZED -> SUPERSEDED (terminal).
    _put(dash, AUTH_REL, DA.transition(_load((dash / AUTH_REL).read_bytes()), DA.SUPERSEDED,
                                       at="2026-01-04T00:00:00+00:00", note="superseded by the correction"))
    commits["SUP"] = _commit(root, "SUP supersede deployment authorization A")

    # REREG -- the generic lane step.
    with pytest.MonkeyPatch.context() as mp:
        _point_seams_at(mp, dash)
        _stub_market_authority(mp)
        mp.setattr(LANE, "pin_block_from_package",
                   lambda package, market_id, work_order: OrderedDict(package["counts"], last_moved_by=work_order))
        LANE.reregister(MARKET, work_order=W_REREG, out=root / "reregistration_report.json", decided_on="2026-01-05",
                        live=(RI.ReleaseIndex(label="LIVE"), LIVE_STATE, []),
                        participation_path=dash / REG.PARTICIPATION_PATH,
                        pin_path=dash / REG.MARKET_STATE_PIN_PATH, package=_package(PKG_B, BLOCK_B))
    (root / "reregistration_report.json").unlink()
    commits["REREG"] = _commit(root, "REREG re-register gamma package B")
    return commits


def _point_seams_at(mp, dash: Path) -> None:
    mp.setattr(RD, "REPO_ROOT", dash)
    mp.setattr(REG, "REPO_ROOT", dash)
    mp.setattr(ISO, "REPO_ROOT", dash)


@pytest.fixture(scope="module")
def pristine(tmp_path_factory):
    root = tmp_path_factory.mktemp("rereg") / "repo"
    return root, _build(root)


@pytest.fixture
def repo(pristine, tmp_path, monkeypatch):
    """A private copy of the lifecycle repository, the classifier's git seams
    pointed at it, and the unchanged audited checks stubbed."""
    return _attach(pristine, tmp_path, monkeypatch)


def _attach(pristine, tmp_path, monkeypatch):
    src, commits = pristine
    root = tmp_path / "repo"
    shutil.copytree(src, root)
    dash = root / "atlas-dashboard"
    _point_seams_at(monkeypatch, dash)
    monkeypatch.setattr(REG, "live_index", lambda: (RI.ReleaseIndex(label="LIVE"), LIVE_STATE, []))
    calls = OrderedDict()

    def _pass(name, **detail):
        return REG._result(True, "stub: %s is proven by its own audited battery" % name, **detail)

    def _contract_check(head_bytes, market_id, base_contracts, *, verify=None, reregistration=False):
        calls["release_contract.reregistration"] = reregistration
        calls["release_contract.own_base_contract"] = market_id in base_contracts
        return _pass("release_contract")

    monkeypatch.setattr(REG, "check_release_contract", _contract_check)
    monkeypatch.setattr(REG, "check_derived_globals", lambda rows, market_id, head: _pass("derived_globals"))
    monkeypatch.setattr(REG, "check_registration_input",
                        lambda rows, head, market_id, reregistration=False: _pass("registration_input"))
    monkeypatch.setattr(REG, "find_covering_package",
                        lambda market_id, head: (_package(PKG_B, BLOCK_B), OrderedDict((("covering", 1),))))
    monkeypatch.setattr(REG, "check_sealed_package", lambda *a: _pass("sealed_package"))
    monkeypatch.setattr(REG, "check_fast_receipt", lambda *a: _pass("fast_receipt", receipt="synthetic"))
    monkeypatch.setattr(REG, "check_expected_release",
                        lambda *a: (_pass("expected_release", expected_digest="e", actual_digest="e", actual_markets=3,
                                          actual_profiles=31, actual_routes=40, unexpected_market_changes=0,
                                          unexpected_profile_changes=0, unexpected_route_changes=0), None))
    monkeypatch.setattr(REG, "check_identity_routes", lambda *a: _pass("identity_routes"))
    monkeypatch.setattr(REG, "expected_pin_block", lambda package: OrderedDict(package["counts"]))
    monkeypatch.setattr(RD, "resolve_sha", lambda rev: rev)
    return SimpleNamespace(root=root, dash=dash, commits=commits, calls=calls)


def _classify(repo) -> dict:
    RD.RENAMED_FROM.clear()
    return RD.classify_document(repo.commits["AUTH"], RD.WORKTREE)


def _rows(repo, extra=None):
    paths = RD.changed_files(repo.commits["AUTH"], RD.WORKTREE)
    paths.update(extra or {})
    rows = []
    for rel, status in paths.items():
        classes, rule = RD.classify_path(rel)
        rows.append(OrderedDict((("path", rel), ("status", status), ("classes", list(classes)), ("rule", rule))))
    return rows


def _gate(repo, extra=None):
    rows = _rows(repo, extra)
    return REG.classify_change_set(rows, base=repo.commits["AUTH"], head=RD.WORKTREE,
                                   blockers=[r["path"] for r in rows if RD.is_narrowing_blocker(r["path"])])


def _evaluate(repo):
    rows = _rows(repo)
    return REG.evaluate(rows, repo.commits["AUTH"], RD.WORKTREE,
                        blockers=[r["path"] for r in rows if RD.is_narrowing_blocker(r["path"])])


# --------------------------------------------------------------------------- #
# Phase 2: the dead end, reproduced -- and still refused by the REGISTRATION
# lane, which this order did not weaken.
# --------------------------------------------------------------------------- #

class TestTheDeadEnd:
    def test_the_registration_proof_refuses_an_authorized_market(self):
        p0 = _p0()
        p2 = _p2(_p1(p0))
        result = REG.check_participation(_dump(p0), _dump(p2), MARKET)
        assert result["status"] == REG.FAIL
        problems = result["detail"]["problems"]
        assert any("new row status is 'FOUNDER_AUTHORIZED_FOR_LAUNCH'" in p for p in problems)
        assert any("the founder-authorized set moved" in p for p in problems)
        integrity = REG.check_release_integrity([], LIVE_STATE, result)
        assert integrity["status"] == REG.FAIL
        assert "the founder-authorized set is not proven unchanged" in integrity["why"]

    def test_a_silent_withdrawal_is_still_refused_by_the_monotone_chain(self):
        p2 = _p2(_p1(_p0()))
        silent = _rereg(p2, entry=OrderedDict())
        assert any("drops market(s) the previous one authorized: ['gamma-zz']" in p for p in _problems(silent))

    def test_the_registration_base_pretends_the_market_is_brand_new(self, repo):
        base = LANE.derive_registration_base(MARKET, repo.commits["L"], git_root=repo.root, prefix=PREFIX)
        assert base["base"] == repo.commits["L"], "the old rule walks back past the market's own registration"


# --------------------------------------------------------------------------- #
# Phase 4: monotonicity -- one narrow, package-bound transition.
# --------------------------------------------------------------------------- #

class TestTheChain:
    def test_a_package_bound_supersession_is_a_valid_decision(self):
        p2 = _p2(_p1(_p0()))
        doc = _rereg(p2)
        assert _problems(doc) == []
        assert LP.superseded_market_ids(doc) == [MARKET]
        assert not LP.is_founder_authorized(MARKET, doc)
        assert LP.launch_status(MARKET, doc) == LP.SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH

    def test_later_decisions_carry_the_supersession_forward(self):
        p2 = _p2(_p1(_p0()))
        r = _rereg(p2)
        record = LP.decision_record(r, _sha(_dump(r)))
        assert record[LP.FOUNDER_AUTHORIZATION_SUPERSEDED] == [MARKET]
        later = _reissue(r, list(r["markets"]), work_order="PTF-SYNTH-OTHER-006", decided_by="PTF-SYNTH-OTHER-006",
                         decided_on="2026-01-06", reason="unrelated reissue")
        assert _problems(later) == []
        again = _reissue(r, [x if x["market_id"] != MARKET else _row(MARKET, LP.FOUNDER_AUTHORIZED_FOR_LAUNCH)
                             for x in r["markets"]], work_order="PTF-SYNTH-GAMMA-FOUNDER-AUTHORIZATION-006",
                         decided_by="founder", decided_on="2026-01-07", reason="the founder authorizes package B",
                         decision_basis=OrderedDict((("market_id", MARKET), ("registered_package_digest", PKG_B))))
        assert _problems(again) == []

    def test_every_existing_record_is_unchanged(self):
        p1 = _p1(_p0())
        assert list(LP.decision_record(p1, "0" * 64)) == ["work_order", "sha256", "founder_authorized"]

    def test_an_unannotated_shrink_in_the_lineage_is_still_refused(self):
        p2 = _p2(_p1(_p0()))
        r = _rereg(p2)
        later = _reissue(r, list(r["markets"]), work_order="PTF-SYNTH-OTHER-006", decided_by="PTF-SYNTH-OTHER-006",
                         decided_on="2026-01-06", reason="unrelated")
        del later["decision"]["lineage"]["records"][-1][LP.FOUNDER_AUTHORIZATION_SUPERSEDED]
        assert any("shrinks the authorized set" in p for p in _problems(later))

    @pytest.mark.parametrize("label,overrides,expect", [
        ("market_live true", {"market_live": True}, "market_live must be false"),
        ("no reauthorization", {"reauthorization_required": False}, "reauthorization_required must be true"),
        ("same package", {"corrected_package_digest": PKG_A}, "the corrected package is the superseded one"),
        ("bad digest", {"corrected_package_digest": "b2"}, "sha256:<64 hex>"),
        ("authorization still AUTHORIZED",
         {"deployment_authorizations": [OrderedDict((("authorization_id", AUTH_ID), ("bundle_sha256", BUNDLE_A),
                                                     ("authorization_status", "AUTHORIZED")))]}, "not SUPERSEDED"),
        ("no authorization", {"deployment_authorizations": []}, "at least one"),
        ("unknown decision", {"authorizing_decision": OrderedDict((("work_order", W_AUTH), ("sha256", "9" * 64)))},
         "is not a record of this decision's lineage"),
    ])
    def test_a_malformed_entry_is_refused(self, label, overrides, expect):
        p2 = _p2(_p1(_p0()))
        doc = _rereg(p2, _entry(_dump(p2), **overrides))
        assert any(expect in p for p in _problems(doc)), (label, _problems(doc))

    def test_an_entry_for_a_market_that_stays_authorized_is_refused(self):
        p2 = _p2(_p1(_p0()))
        doc = _rereg(p2, status=LP.FOUNDER_AUTHORIZED_FOR_LAUNCH)
        problems = _problems(doc)
        assert any("still FOUNDER_AUTHORIZED_FOR_LAUNCH" in p for p in problems)

    def test_an_entry_cannot_withdraw_a_market_the_predecessor_did_not_authorize(self):
        p1 = _p1(_p0())
        doc = _rereg(p1, _entry(_dump(p1)))
        assert any("was not founder-authorized by the previous decision" in p for p in _problems(doc))


# --------------------------------------------------------------------------- #
# Phase 6: the participation proof -- no authorization transfers.
# --------------------------------------------------------------------------- #

class TestReregistrationParticipation:
    def test_the_valid_reissue_passes(self):
        p2 = _p2(_p1(_p0()))
        r = _rereg(p2)
        result = REG.check_reregistration_participation(_dump(p2), _dump(r), MARKET)
        assert result["status"] == REG.PASS, result["why"]
        detail = result["detail"]
        assert detail["founder_authorized_change"] == {"removed": [MARKET], "added": []}
        assert detail["status_head"] == LP.SOURCE_READY_BUT_NOT_FOUNDER_AUTHORIZED_FOR_LAUNCH
        assert detail["superseded_package_digest"] == PKG_A and detail["corrected_package_digest"] == PKG_B

    def test_reusing_the_old_founder_authorization_is_refused(self):
        p2 = _p2(_p1(_p0()))
        kept = _rereg(p2, status=LP.FOUNDER_AUTHORIZED_FOR_LAUNCH)
        result = REG.check_reregistration_participation(_dump(p2), _dump(kept), MARKET)
        assert result["status"] == REG.FAIL
        assert any("the old founder authorization does not carry over" in p for p in result["detail"]["problems"])

    def test_an_authorization_that_is_not_package_bound_is_refused(self):
        p2 = _p2(_p1(_p0()), package_digest=None)
        r = _rereg(p2)
        result = REG.check_reregistration_participation(_dump(p2), _dump(r), MARKET)
        assert result["status"] == REG.FAIL
        assert any("not a package-bound founder authorization" in p for p in result["detail"]["problems"])

    def test_a_superseded_digest_other_than_the_one_the_founder_saw_is_refused(self):
        p2 = _p2(_p1(_p0()))
        r = _rereg(p2, _entry(_dump(p2), superseded_package_digest="sha256:" + "d4" * 32))
        result = REG.check_reregistration_participation(_dump(p2), _dump(r), MARKET)
        assert any("is not the package the founder was shown" in p for p in result["detail"]["problems"])

    def test_a_base_that_is_not_the_authorizing_decision_is_refused(self):
        p1 = _p1(_p0())
        p2 = _p2(p1)
        r = _rereg(p2)
        result = REG.check_reregistration_participation(_dump(p1), _dump(r), MARKET)
        assert result["status"] == REG.FAIL

    def test_another_row_moving_is_refused(self):
        p2 = _p2(_p1(_p0()))
        r = _rereg(p2)
        r["markets"] = [x if x["market_id"] != "alpha-zz" else _row("alpha-zz", LP.NOT_SOURCE_READY)
                        for x in r["markets"]]
        result = REG.check_reregistration_participation(_dump(p2), _dump(r), MARKET)
        assert any("existing row alpha-zz changed" in p for p in result["detail"]["problems"])

    def test_the_founder_may_not_be_named_as_the_writer(self):
        p2 = _p2(_p1(_p0()))
        r = _rereg(p2, decided_by="founder")
        result = REG.check_reregistration_participation(_dump(p2), _dump(r), MARKET)
        assert any("names the founder" in p for p in result["detail"]["problems"])

    def test_the_old_deployment_authorization_is_terminal_and_bound_to_the_old_bundle(self):
        superseded = _auth("0" * 64, status=DA.SUPERSEDED)
        assert DA.SUPERSEDED not in DA.DEPLOYABLE_STATUSES
        with pytest.raises(DA.DeploymentAuthorizationError):
            DA.transition(superseded, DA.AUTHORIZED)
        assert superseded["bundle_sha256"] == BUNDLE_A != "b2" * 32, "it binds the OLD bundle, forever"

    def test_a_real_authorization_refuses_a_different_bundle(self):
        """verify_authorization's own binding, read-only over a committed record."""
        auths = [a for a in DA.list_authorizations() if a.get("authorization_status") == DA.DEPLOYED]
        assert auths
        auth = auths[-1]
        from scripts.pettripfinder import global_deployment as GD
        manifest = dict(GD.load_manifest(), bundle_sha256="b2" * 32)
        problems = DA.verify_authorization(auth, manifest, check_manifest=False)
        assert any(p.startswith("bundle_sha256: authorization binds") for p in problems)


# --------------------------------------------------------------------------- #
# Phase 8: the base is the market's OWN prior registration.
# --------------------------------------------------------------------------- #

class TestTheReregistrationBase:
    def test_the_base_is_the_authorizing_commit(self, repo):
        base = LANE.derive_reregistration_base(MARKET, repo.commits["L"], git_root=repo.root, prefix=PREFIX)
        assert base["base"] == repo.commits["AUTH"]
        assert base["authorizations_of_the_market_at_base"] == [AUTH_ID + ".json"]
        assert LANE.reregistration_market_at("HEAD", git_root=repo.root, prefix=PREFIX) == MARKET
        assert LANE.reregistration_market_at(repo.commits["AUTH"], git_root=repo.root, prefix=PREFIX) is None

    def test_the_base_holds_package_a_and_every_other_market_unchanged(self, repo):
        auth, head = repo.commits["AUTH"], RD.WORKTREE
        assert MARKET in REG.registered_market_ids_at(auth)
        assert REG.bytes_at(auth, PKG_DIR + "pkg-%s-%s.json" % (MARKET, PKG_A[7:23])) is not None
        pin_base = _load(REG.bytes_at(auth, REG.MARKET_STATE_PIN_PATH))["markets"]
        pin_head = _load(REG.bytes_at(head, REG.MARKET_STATE_PIN_PATH))["markets"]
        assert pin_base[MARKET]["pet_friendly"] == BLOCK_A["pet_friendly"]
        assert pin_head[MARKET]["pet_friendly"] == BLOCK_B["pet_friendly"]
        for m in LIVE_MARKETS:
            assert pin_base[m] == pin_head[m]
        changed = RD.changed_files(auth, head)
        assert not [p for p in changed if any(m in p for m in LIVE_MARKETS)]

    def test_a_head_without_a_supersession_has_no_reregistration_base(self, repo):
        with pytest.raises(LANE.LaneRefusal) as exc:
            LANE.derive_reregistration_base(MARKET, repo.commits["L"], head=repo.commits["SUP"],
                                            git_root=repo.root, prefix=PREFIX)
        assert exc.value.code == LANE.BASE_NOT_DERIVABLE

    def test_an_authorizing_commit_that_moved_live_truth_is_refused(self, tmp_path, monkeypatch):
        root = tmp_path / "moved"
        commits = _build(root, auth_rewrites_live_manifest=True)
        with pytest.raises(LANE.LaneRefusal) as exc:
            LANE.derive_reregistration_base(MARKET, commits["L"], git_root=root, prefix=PREFIX)
        assert exc.value.code == LANE.BASE_NOT_DERIVABLE
        assert "global_deployment_manifest.json differs" in exc.value.detail


# --------------------------------------------------------------------------- #
# Phases 5, 9, 12: the lifecycle classifies narrowly, and only the lifecycle.
# --------------------------------------------------------------------------- #

class TestTheLifecycle:
    def test_the_valid_correction_is_the_narrow_class(self, repo):
        doc = _classify(repo)
        proof = doc["new_market_registration_data_only"]
        assert proof["ELIGIBLE"] == "YES", (proof["why"], proof["failed_checks"])
        assert proof["CHANGE_CLASS"] == RD.AUTHORIZED_NONLIVE_MARKET_REREGISTRATION_DATA_ONLY
        assert doc["FULL_REGRESSION_REQUIRED"] == "NO"
        plan = doc["plan"]
        assert plan["full_regression_required"] is False and plan["assembly_required"] is False
        assert plan["REMOTE_BROAD_JOBS_REQUIRED"] == 0
        assert plan[RD.AUTHORIZED_NONLIVE_MARKET_REREGISTRATION_DATA_ONLY] == "YES"
        assert plan["COMPOSITE_FRESH_MARKET_DATA_ONLY"] == "NO"
        assert set(proof["checks"]) == set(REG.CHECKS) | set(REG.REREGISTRATION_CHECKS)
        assert all(c["status"] == REG.PASS for c in proof["checks"].values())
        assert repo.calls["release_contract.reregistration"] is True
        assert repo.calls["release_contract.own_base_contract"] is True

    def test_shared_and_unknown_are_zero_and_every_path_is_accounted(self, repo):
        proof = _classify(repo)["new_market_registration_data_only"]
        accounting = proof["accounting"]
        assert accounting["SHARED_BEHAVIOR_PATHS"] == 0 and accounting["UNKNOWN_PATHS"] == 0
        assert accounting["sum_equals_total"] is True
        partition = proof["partition"]
        assert HELPER_REL in partition["MARKET_LOCAL_ACQUISITION"]
        assert AUTH_REL in partition["NEW_MARKET_REGISTRATION_DATA_ONLY"]
        zone = proof["checks"]["market_local_zone"]["detail"]
        assert zone["proofs_passed"] == zone["proofs_run"] == 1

    def test_only_the_corrected_market_changes(self, repo):
        changed = RD.changed_files(repo.commits["AUTH"], RD.WORKTREE)
        others = [p for p in changed if any(m in p for m in LIVE_MARKETS)]
        assert others == []
        proof = _classify(repo)["new_market_registration_data_only"]
        assert proof["market_id"] == MARKET
        assert proof["checks"]["participation"]["detail"]["founder_authorized_change"] == {"removed": [MARKET],
                                                                                          "added": []}

    def test_the_package_b_packet_is_ready_but_not_deployable(self, repo, tmp_path):
        doc = _classify(repo)
        classification = tmp_path / "classification.json"
        classification.write_text(json.dumps(doc), encoding="utf-8")
        packet = LANE.packet(MARKET, classification_path=classification, lane_report=tmp_path / "absent.json",
                             out=tmp_path / "packet.json", prepared_by="test")
        assert packet["status"] == "AUTHORIZATION_READY"
        assert packet["founder_status"] == "AWAITING_FOUNDER_AUTHORIZATION"
        assert packet["authorized_by"] is None and packet["authorized_at"] is None
        rereg = packet["reregistration"]
        assert rereg["old_authorizations_authorize_the_corrected_package"] is False
        assert rereg["new_founder_authorization_required"] is True
        assert rereg["superseded_package_digest"] == PKG_A and rereg["corrected_package_digest"] == PKG_B
        head = _load((repo.dash / REG.PARTICIPATION_PATH).read_bytes())
        assert not LP.is_founder_authorized(MARKET, head), "nothing admits package B until the founder decides"
        old = _load((repo.dash / AUTH_REL).read_bytes())
        assert old["authorization_status"] == DA.SUPERSEDED and old["bundle_sha256"] == BUNDLE_A

    def test_the_lane_wrote_exactly_the_reissue_and_the_own_pin_block(self, repo):
        diff = _git(repo.root, "diff", "--name-status", repo.commits["SUP"], repo.commits["REREG"])
        assert sorted(line.split("\t")[1] for line in diff.splitlines()) == sorted(
            [PREFIX + REG.PARTICIPATION_PATH, PREFIX + REG.MARKET_STATE_PIN_PATH])


# --------------------------------------------------------------------------- #
# Phase 7: the hard vetoes. Each breaks exactly one thing and must fail closed.
# --------------------------------------------------------------------------- #

def _set_auth_status(repo, status: str) -> None:
    doc = _load((repo.dash / AUTH_REL).read_bytes())
    doc["authorization_status"] = status
    doc["status_history"][-1]["status"] = status
    _put(repo.dash, AUTH_REL, doc)


def _ineligible(repo) -> dict:
    doc = _classify(repo)
    proof = doc["new_market_registration_data_only"]
    assert proof["ELIGIBLE"] == "NO"
    assert doc["FULL_REGRESSION_REQUIRED"] == "YES"
    assert RD.AUTHORIZED_NONLIVE_MARKET_REREGISTRATION_DATA_ONLY not in doc["change_classes"]
    return proof


class TestTheHardVetoes:
    def test_a_live_market_is_refused(self, repo, monkeypatch):
        live = dataclasses.replace(LIVE_STATE, participating_markets=LIVE_MARKETS + (MARKET,))
        monkeypatch.setattr(REG, "live_index", lambda: (RI.ReleaseIndex(label="LIVE"), live, []))
        proof = _ineligible(repo)
        assert proof["checks"]["live_veto"]["status"] == REG.FAIL
        assert "is LIVE" in proof["checks"]["live_veto"]["why"]

    def test_a_market_named_by_a_deployment_record_is_refused(self, repo):
        veto = REG.check_live_veto(MARKET, LIVE_STATE, RD.WORKTREE)
        assert veto["pass"]
        _put(repo.dash, "deploy/netlify/deployment_records/ptf-deploy-gamma-004.json",
             OrderedDict((("deployment_record_id", "ptf-deploy-gamma-004"),
                          ("participating_markets", list(LIVE_MARKETS) + [MARKET]))))
        assert not REG.check_live_veto(MARKET, LIVE_STATE, RD.WORKTREE)["pass"]
        proof = _ineligible(repo)
        assert any("protected release state" in p for p in proof["checks"]["change_set"]["detail"]["problems"])

    def test_an_unsuperseded_deployment_authorization_is_refused(self, repo):
        _set_auth_status(repo, DA.AUTHORIZED)
        proof = _ineligible(repo)
        assert "still deployable" in proof["checks"]["authorization_supersession"]["why"]

    def test_a_consumed_deployment_authorization_is_refused(self, repo):
        _set_auth_status(repo, DA.DEPLOYED)
        proof = _ineligible(repo)
        assert "was consumed" in proof["checks"]["authorization_supersession"]["why"]

    def test_a_supersession_that_moved_another_field_is_refused(self, repo):
        doc = _load((repo.dash / AUTH_REL).read_bytes())
        doc["bundle_sha256"] = "b2" * 32
        _put(repo.dash, AUTH_REL, doc)
        proof = _ineligible(repo)
        assert "a field other than its status and history changed" in proof["checks"]["authorization_supersession"]["why"]

    @pytest.mark.parametrize("label,rel,content", [
        ("cross-market data", "launch_packages/pettripfinder/markets/authority/alpha-zz/seed_businesses.csv",
         "name\nalpha hotel\nalpha annex\n"),
        ("another market's contract", "deploy/netlify/release_contracts/beta-zz.json", '{"market_id": "beta-zz", "x": 1}\n'),
        ("shared factory code", "scripts/pettripfinder/site_data.py", "X = 1\n"),
        ("unknown path", "launch_packages/pettripfinder/gamma_zz_loose_099.json", "{}\n"),
        ("a new unowned global", "launch_packages/pettripfinder/identity_routing.json", "{}\n"),
        ("the build closure", REG.CLOSURE_PATH, '{"shared_data_inputs": [], "remeasured_by": []}\n'),
        ("live production manifest", "deploy/netlify/global_deployment_manifest.json", '{"bundle_sha256": "x"}\n'),
        ("the deployment pin", REG.DEPLOYMENT_STATE_PIN_PATH, '{"live_deploy_id": "x"}\n'),
        ("a new authorization", "deploy/netlify/deployment_authorizations/ptf-auth-gamma-006-000000000000.json", "{}\n"),
    ])
    def test_everything_but_the_correction_widens(self, repo, label, rel, content):
        _put(repo.dash, rel, content)
        gate = _gate(repo)
        assert not gate["result"]["pass"], label
        _ineligible(repo)

    def test_reusing_the_old_founder_authorization_is_not_a_reregistration(self, repo):
        head = _load((repo.dash / REG.PARTICIPATION_PATH).read_bytes())
        for row in head["markets"]:
            if row["market_id"] == MARKET:
                row["launch_status"] = LP.FOUNDER_AUTHORIZED_FOR_LAUNCH
        _put(repo.dash, REG.PARTICIPATION_PATH, head)
        proof = _ineligible(repo)
        assert proof["checks"]["participation"]["status"] == REG.FAIL

    def test_a_head_that_supersedes_nothing_is_no_reregistration(self, repo):
        _git(repo.root, "checkout", "-q", repo.commits["SUP"], "--", PREFIX + REG.PARTICIPATION_PATH)
        gate = _gate(repo)
        assert not gate["result"]["pass"]
        assert "no re-registration" in gate["result"]["why"]

    def test_an_authorization_not_bound_to_the_base_registration_is_refused(self, repo):
        doc = _load((repo.dash / AUTH_REL).read_bytes())
        doc["release_contracts"][0]["sha256"] = "0" * 64
        _put(repo.dash, AUTH_REL, doc)
        proof = _ineligible(repo)
        assert "is not bound to the market's registration at the base" in \
            proof["checks"]["authorization_supersession"]["why"]

    def test_a_corrected_digest_other_than_the_covering_package_is_refused(self, repo, monkeypatch):
        other = _package("sha256:" + "e5" * 32, BLOCK_B)
        monkeypatch.setattr(REG, "find_covering_package", lambda market_id, head: (other, OrderedDict()))
        proof = _ineligible(repo)
        assert "the package covering the head is" in proof["checks"]["authorization_supersession"]["why"]

    def test_the_lane_refuses_to_reregister_while_an_authorization_is_live(self, repo, monkeypatch):
        _git(repo.root, "checkout", "-q", repo.commits["CORR"], "--", PREFIX + REG.PARTICIPATION_PATH,
             PREFIX + AUTH_REL, PREFIX + REG.MARKET_STATE_PIN_PATH)
        _stub_market_authority(monkeypatch)
        with pytest.raises(SystemExit) as exc:
            LANE.reregister(MARKET, work_order=W_REREG, out=repo.root / "r.json",
                            live=(RI.ReleaseIndex(label="LIVE"), LIVE_STATE, []),
                            participation_path=repo.dash / REG.PARTICIPATION_PATH,
                            pin_path=repo.dash / REG.MARKET_STATE_PIN_PATH, package=_package(PKG_B, BLOCK_B))
        assert "are not SUPERSEDED" in str(exc.value)
        assert not (repo.root / "r.json").exists()

    def test_the_lane_refuses_a_live_market(self, repo, monkeypatch):
        _git(repo.root, "checkout", "-q", repo.commits["SUP"], "--", PREFIX + REG.PARTICIPATION_PATH,
             PREFIX + REG.MARKET_STATE_PIN_PATH)
        _stub_market_authority(monkeypatch)
        live = dataclasses.replace(LIVE_STATE, participating_markets=LIVE_MARKETS + (MARKET,))
        with pytest.raises(SystemExit) as exc:
            LANE.reregister(MARKET, work_order=W_REREG, out=repo.root / "r.json",
                            live=(RI.ReleaseIndex(label="LIVE"), live, []),
                            participation_path=repo.dash / REG.PARTICIPATION_PATH,
                            pin_path=repo.dash / REG.MARKET_STATE_PIN_PATH, package=_package(PKG_B, BLOCK_B))
        assert "live veto" in str(exc.value)


# --------------------------------------------------------------------------- #
# The class itself: conditional, and never selected by a path.
# (Phases 1 and 13 -- current live and the production delta -- are MEASURED
# in the order's report, not pinned here: a live-epoch pin goes stale at the
# next launch.)
# --------------------------------------------------------------------------- #

class TestTheClass:
    def test_the_class_is_conditional_and_never_selected_by_path(self):
        row = RD.VALIDATION_MATRIX[RD.AUTHORIZED_NONLIVE_MARKET_REREGISTRATION_DATA_ONLY]
        assert row["full_regression"] == RD.CONDITIONAL and row["assembly"] == RD.NOT_REQUIRED
        for rel in (REG.PARTICIPATION_PATH, AUTH_REL, CONTRACT_REL):
            classes, _rule = RD.classify_path(rel)
            assert RD.AUTHORIZED_NONLIVE_MARKET_REREGISTRATION_DATA_ONLY not in classes


# --------------------------------------------------------------------------- #
# PTF-REREGISTRATION-TRUSTED-FACTORY-BASELINE-CORRECTION-002: the two
# lineages. A factory repair proven in its own order and merged into the
# market line AFTER the authorizing commit is compared against its own proven
# tip, by bytes; the market is still compared against its authorizing commit.
# --------------------------------------------------------------------------- #

FACTORY_MODULE = "scripts/pettripfinder/factory_repair_zz.py"
FACTORY_TEST = "tests/pettripfinder/test_factory_repair_zz.py"
FACTORY_DOC = "README.md"


def _merge_lineage(root: Path, dash: Path, branch: str, start: str, files, message: str):
    """Branch ``branch`` from ``start``, commit ``files``, merge it into main
    with an explicit merge commit. Returns (lineage tip, merge commit)."""
    _git(root, "checkout", "-q", "-b", branch, start)
    for rel, content in files.items():
        _put(dash, rel, content)
    tip = _commit(root, message)
    _git(root, "checkout", "-q", "main")
    _git(root, "merge", "-q", "--no-ff", "-m", "merge %s into the market line" % branch, branch)
    return tip, _git(root, "rev-parse", "HEAD")


def _factory_after_auth(root: Path, dash: Path, commits) -> None:
    commits["FACTORY"], commits["MERGE"] = _merge_lineage(
        root, dash, "worker/factory-repair-zz", commits["L"],
        OrderedDict(((FACTORY_MODULE, '"""a proven factory repair."""\nX = 2\n'),
                     (FACTORY_TEST, "def test_x():\n    assert True\n"),
                     (FACTORY_DOC, "synthetic factory, repaired\n"))),
        "FACTORY a repair proven in its own order")


@pytest.fixture(scope="module")
def pristine_factory(tmp_path_factory):
    root = tmp_path_factory.mktemp("rereg_factory") / "repo"
    return root, _build(root, after_auth=_factory_after_auth)


@pytest.fixture
def frepo(pristine_factory, tmp_path, monkeypatch):
    return _attach(pristine_factory, tmp_path, monkeypatch)


def _baseline(frepo, head: str = "HEAD"):
    return LANE.derive_trusted_factory_baseline(MARKET, frepo.commits["AUTH"], frepo.commits["L"], head=head,
                                                git_root=frepo.root, prefix=PREFIX)


def _fclassify(frepo, baseline=None) -> dict:
    RD.RENAMED_FROM.clear()
    return RD.classify_document(frepo.commits["AUTH"], RD.WORKTREE,
                                factory_baseline=baseline if baseline is not None else _baseline(frepo))


def _fineligible(frepo, baseline=None) -> dict:
    doc = _fclassify(frepo, baseline)
    proof = doc["new_market_registration_data_only"]
    assert proof["ELIGIBLE"] == "NO"
    assert doc["FULL_REGRESSION_REQUIRED"] == "YES"
    assert RD.AUTHORIZED_NONLIVE_MARKET_REREGISTRATION_DATA_ONLY not in doc["change_classes"]
    return doc


def _refused(callable_, *args, **kwargs) -> str:
    with pytest.raises(LANE.LaneRefusal) as exc:
        callable_(*args, **kwargs)
    assert exc.value.code == LANE.FACTORY_BASELINE_NOT_DERIVABLE
    return exc.value.detail


class TestTheTrustedFactoryBaseline:
    def test_the_merged_factory_reproduces_the_refusal_without_a_baseline(self, frepo):
        RD.RENAMED_FROM.clear()
        doc = RD.classify_document(frepo.commits["AUTH"], RD.WORKTREE)
        proof = doc["new_market_registration_data_only"]
        assert proof["ELIGIBLE"] == "NO" and doc["FULL_REGRESSION_REQUIRED"] == "YES"
        assert proof["checks"]["change_set"]["status"] == REG.FAIL
        assert "trusted_factory_baseline" not in doc

    def test_the_baseline_is_derived_mechanically(self, frepo):
        baseline = _baseline(frepo)
        assert baseline["commit"] == frepo.commits["FACTORY"]
        assert baseline["merge_base"] == frepo.commits["L"]
        assert baseline["merges"] == [frepo.commits["MERGE"]]
        assert baseline["independent_refs"] == ["refs/heads/worker/factory-repair-zz"]
        assert sorted(baseline["factory_paths"]) == sorted([FACTORY_DOC, FACTORY_MODULE, FACTORY_TEST])

    def test_the_correction_is_the_narrow_class_against_both_lineages(self, frepo):
        doc = _fclassify(frepo)
        proof = doc["new_market_registration_data_only"]
        assert proof["ELIGIBLE"] == "YES", (proof["why"], proof["failed_checks"])
        assert proof["CHANGE_CLASS"] == RD.AUTHORIZED_NONLIVE_MARKET_REREGISTRATION_DATA_ONLY
        assert doc["FULL_REGRESSION_REQUIRED"] == "NO"
        assert doc["base"] == frepo.commits["AUTH"], "the market is still compared against its authorizing commit"
        assert proof["accounting"]["SHARED_BEHAVIOR_PATHS"] == 0 and proof["accounting"]["UNKNOWN_PATHS"] == 0
        factory = doc["trusted_factory_baseline"]
        assert sorted(factory["inherited_paths"]) == sorted([FACTORY_DOC, FACTORY_MODULE, FACTORY_TEST])
        assert factory["SHARED_FACTORY_DELTA"] == 0
        changed = [row["path"] for row in doc["changed_files"]]
        assert not set(changed) & {FACTORY_DOC, FACTORY_MODULE, FACTORY_TEST}
        assert HELPER_REL in changed and AUTH_REL in changed

    def test_an_ordinary_lifecycle_has_no_factory_baseline(self, repo):
        assert LANE.derive_trusted_factory_baseline(MARKET, repo.commits["AUTH"], repo.commits["L"],
                                                    git_root=repo.root, prefix=PREFIX) is None

    def test_the_lane_wires_both_lineages(self, frepo, monkeypatch, tmp_path):
        monkeypatch.setattr(RI, "current_verified_live", lambda: LIVE_STATE)
        resolution = OrderedDict((("RESOLVED", "YES"), ("head_contains_live", True),
                                  ("live_deploy_id", LIVE_STATE.deploy_id),
                                  ("CURRENT_LIVE_SOURCE_COMMIT", frepo.commits["L"])))
        RD.RENAMED_FROM.clear()
        doc = LANE.classify_automatically(MARKET, out=tmp_path / "c.json", git_root=frepo.root, resolution=resolution)
        assert doc["registration_base"]["base"] == frepo.commits["AUTH"]
        assert doc["registration_base"]["trusted_factory_baseline"]["commit"] == frepo.commits["FACTORY"]
        assert doc["new_market_registration_data_only"]["ELIGIBLE"] == "YES"
        packet = LANE.packet(MARKET, classification_path=tmp_path / "c.json", lane_report=tmp_path / "absent.json",
                             out=tmp_path / "p.json", prepared_by="test")
        assert packet["status"] == "AUTHORIZATION_READY"
        assert packet["regression_v2"]["trusted_factory_baseline"] == frepo.commits["FACTORY"]
        assert packet["regression_v2"]["SHARED_FACTORY_DELTA"] == 0
        assert packet["authorized_by"] is None

    # ---- hard negatives: each breaks one thing and must fail closed. ---- #

    def test_1_a_shared_file_that_differs_from_the_baseline_is_refused(self, frepo):
        _put(frepo.dash, FACTORY_MODULE, '"""a proven factory repair."""\nX = 3\n')
        doc = _fineligible(frepo)
        assert doc["trusted_factory_baseline"]["SHARED_FACTORY_DELTA"] == 1
        assert FACTORY_MODULE in doc["trusted_factory_baseline"]["re_edited_paths"]
        assert FACTORY_MODULE in [row["path"] for row in doc["changed_files"]]
        assert doc["new_market_registration_data_only"]["checks"]["change_set"]["status"] == REG.FAIL

    def test_2_a_correction_that_edits_a_shared_module_after_the_merge_is_refused(self, frepo):
        _put(frepo.dash, FACTORY_DOC, "synthetic factory, repaired, then edited by the market\n")
        _commit(frepo.root, "the market line edits a factory file after the merge")
        doc = _fineligible(frepo)
        assert FACTORY_DOC in doc["trusted_factory_baseline"]["re_edited_paths"]
        assert FACTORY_DOC in doc["narrowing_blockers"], "a re-edited factory path blocks whatever its class"

    def test_2b_reverting_a_factory_change_on_the_market_line_is_refused(self, frepo):
        (frepo.dash / FACTORY_MODULE).unlink()
        _commit(frepo.root, "the market line drops the factory module")
        doc = _fineligible(frepo)
        assert FACTORY_MODULE in doc["trusted_factory_baseline"]["re_edited_paths"]
        assert FACTORY_MODULE in [row["path"] for row in doc["changed_files"]]

    def test_3_a_baseline_that_is_not_an_ancestor_is_refused(self, frepo):
        _git(frepo.root, "checkout", "-q", "-b", "worker/unmerged-zz", frepo.commits["L"])
        _put(frepo.dash, "scripts/pettripfinder/unmerged_zz.py", "Y = 1\n")
        tip = _commit(frepo.root, "a lineage never merged")
        _git(frepo.root, "checkout", "-q", "main")
        detail = _refused(LANE.prove_factory_lineage, tip, MARKET, frepo.commits["AUTH"], frepo.commits["L"],
                          git_root=frepo.root, prefix=PREFIX)
        assert "is not an ancestor of HEAD" in detail

    def test_4_two_unrelated_lineages_are_not_resolvable_uniquely(self, frepo):
        _merge_lineage(frepo.root, frepo.dash, "worker/second-repair-zz", frepo.commits["L"],
                       {"scripts/pettripfinder/second_repair_zz.py": "Z = 1\n"}, "a second, unrelated repair")
        assert "cannot be resolved uniquely" in _refused(_baseline, frepo)

    def test_4b_a_later_lineage_that_contains_the_first_is_the_baseline(self, frepo):
        tip, _merge = _merge_lineage(frepo.root, frepo.dash, "worker/repair-on-repair-zz", frepo.commits["FACTORY"],
                                     {"scripts/pettripfinder/second_repair_zz.py": "Z = 1\n"}, "a repair on the repair")
        baseline = _baseline(frepo)
        assert baseline["commit"] == tip and len(baseline["merges"]) == 2
        assert _fclassify(frepo, baseline)["new_market_registration_data_only"]["ELIGIBLE"] == "YES"

    def test_5_a_lineage_published_by_no_ref_of_its_own_is_refused(self, frepo):
        _git(frepo.root, "branch", "-q", "-D", "worker/factory-repair-zz")
        assert "published by no ref of its own" in _refused(_baseline, frepo)

    def test_5b_a_merged_lineage_carrying_market_data_is_refused(self, frepo):
        _merge_lineage(frepo.root, frepo.dash, "worker/not-a-factory-zz", frepo.commits["L"],
                       {"launch_packages/pettripfinder/markets/authority/alpha-zz/seed_businesses.csv":
                        "name\nalpha hotel\nalpha annex\n"}, "market data dressed as a factory lineage")
        assert "non-factory path" in _refused(_baseline, frepo)

    def test_5c_a_merged_lineage_naming_the_market_is_refused(self, frepo):
        _merge_lineage(frepo.root, frepo.dash, "worker/gamma-helper-zz", frepo.commits["L"],
                       {"scripts/pettripfinder/%s_helper_zz.py" % US: "W = 1\n"}, "a helper naming the market")
        assert "naming %s" % MARKET in _refused(_baseline, frepo)

    def test_5d_an_unproven_shared_commit_on_the_market_line_is_refused(self, frepo):
        _put(frepo.dash, "scripts/pettripfinder/site_data.py", "X = 1\n")
        _commit(frepo.root, "an arbitrary shared change committed straight onto the market line")
        doc = _fineligible(frepo)
        assert "scripts/pettripfinder/site_data.py" in [row["path"] for row in doc["changed_files"]]

    def test_6_an_unknown_path_is_refused(self, frepo):
        _put(frepo.dash, "launch_packages/pettripfinder/gamma_zz_loose_099.json", "{}\n")
        _fineligible(frepo)

    def test_7_another_market_changing_is_refused(self, frepo):
        _put(frepo.dash, "launch_packages/pettripfinder/markets/authority/alpha-zz/seed_businesses.csv",
             "name\nalpha hotel\nalpha annex\n")
        _fineligible(frepo)

    def test_8_a_live_market_is_refused(self, frepo, monkeypatch):
        live = dataclasses.replace(LIVE_STATE, participating_markets=LIVE_MARKETS + (MARKET,))
        monkeypatch.setattr(REG, "live_index", lambda: (RI.ReleaseIndex(label="LIVE"), live, []))
        doc = _fineligible(frepo)
        assert doc["new_market_registration_data_only"]["checks"]["live_veto"]["status"] == REG.FAIL

    def test_9_a_still_deployable_old_authorization_is_refused(self, frepo):
        _set_auth_status(frepo, DA.AUTHORIZED)
        doc = _fineligible(frepo)
        assert "still deployable" in doc["new_market_registration_data_only"]["checks"][
            "authorization_supersession"]["why"]

    def test_10_authorization_inheritance_is_refused(self, frepo):
        head = _load((frepo.dash / REG.PARTICIPATION_PATH).read_bytes())
        for row in head["markets"]:
            if row["market_id"] == MARKET:
                row["launch_status"] = LP.FOUNDER_AUTHORIZED_FOR_LAUNCH
        _put(frepo.dash, REG.PARTICIPATION_PATH, head)
        doc = _fineligible(frepo)
        assert doc["new_market_registration_data_only"]["checks"]["participation"]["status"] == REG.FAIL
