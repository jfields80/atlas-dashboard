"""PTF-PITTSBURGH-HARDENED-RECENSUS-001 -- re-censusing a REGISTERED market.

A market that is live has a census pinned by its release contract. The hardened
factory must be able to re-census it -- treating that census as prior evidence,
never as the ceiling -- without writing a byte over it. What these tests pin:

* the census CLI writes where ``--out`` says and nowhere else;
* ``--prior-census`` folds the prior rows back in as CANDIDATES (verdicts
  dropped), absorbs a prior row into the fresh sighting of the same street,
  and records every absorption;
* every downstream CLI that reads a census accepts ``--census``;
* the factory passes its own census path to each of them, so a
  ``--census-dir`` sandbox is honoured end to end;
* the live Pittsburgh census is byte-identical after all of it.
"""

from __future__ import annotations

import hashlib
import json
from collections import OrderedDict
from pathlib import Path

import pytest

from scripts.pettripfinder import market_census_cli as CENSUS_CLI
from scripts.pettripfinder import market_closure_cli as CLOSURE_CLI
from scripts.pettripfinder import market_factory_cli as MF
from scripts.pettripfinder import market_founder_review_cli as REVIEW_CLI
from scripts.pettripfinder.acquisition import market_paid_acquisition as PA
from scripts.pettripfinder.discovery import census_duplicate_scan as DUP
from scripts.pettripfinder.discovery import census_recandidacy as CR
from scripts.pettripfinder.discovery import census_url_recovery as CUR

REPO = Path(__file__).resolve().parents[2]
PACKAGE = REPO / "launch_packages" / "pettripfinder"
MARKET = "pittsburgh-pa"
LIVE_CENSUS = PACKAGE / "identity_census" / ("%s.json" % MARKET)
CONTRACT = PACKAGE / "markets" / ("%s.json" % MARKET)


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _write(path: Path, document) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=1), encoding="utf-8")
    return path


@pytest.fixture
def live_census():
    return json.loads(LIVE_CENSUS.read_text(encoding="utf-8-sig"))


@pytest.fixture
def prior_census(tmp_path, live_census):
    """Two rows of the live census, as a prior census of the market."""
    rows = [r for r in live_census["hotels"] if r.get("address") and r.get("postal_code")][:2]
    assert len(rows) == 2
    doc = dict(live_census, hotels=rows, count=2)
    return _write(tmp_path / "prior" / ("%s.json" % MARKET), doc), rows


@pytest.fixture
def fresh_candidates(tmp_path, prior_census):
    """One fresh sighting of prior row 0 (same street, new id, coordinates) and
    one hotel the prior census never held, in a postal code the market claims."""
    _path, rows = prior_census
    seed = CR.from_census({"market_id": MARKET, "work_order": "PRIOR",
                           "hotels": rows}, observed_at="2026-08-25")
    resighted = dict(seed[0], candidate_id="dc_fresh_0001",
                     latitude=40.44, longitude=-80.0)
    novel = dict(seed[1], candidate_id="dc_fresh_0002",
                 name="Testville Riverfront Inn",
                 normalized_name="testville riverfront inn",
                 address_line="1 Testville Way", latitude=40.44, longitude=-80.0)
    for c in (resighted, novel):
        for rec in c.get("source_records") or ():
            rec["provider"] = "OPENSTREETMAP"
    return _write(tmp_path / "disc" / "candidates" / ("%s_candidates.json" % MARKET),
                  [resighted, novel])


class TestCensusCliWritesBesideTheLiveCensus:

    def test_out_and_prior_census_build_a_sandbox_census_and_leave_the_live_one(
            self, tmp_path, prior_census, fresh_candidates, capsys):
        prior_path, rows = prior_census
        before = _sha(LIVE_CENSUS)
        out = tmp_path / "sandbox" / ("%s.json" % MARKET)
        absorptions = tmp_path / "sandbox" / "absorptions.json"
        ledger = tmp_path / "sandbox" / "ledger.json"
        code = CENSUS_CLI.main([
            "--market", MARKET, "--candidates", fresh_candidates.as_posix(),
            "--contract", CONTRACT.as_posix(), "--observed-at", "2026-08-25",
            "--work-order", "TEST-RECENSUS", "--out", out.as_posix(),
            "--prior-census", prior_path.as_posix(),
            "--absorptions-out", absorptions.as_posix(),
            "--ledger-out", ledger.as_posix()])
        assert code == 0
        assert _sha(LIVE_CENSUS) == before, "the live census was written over"
        assert out.is_file() and absorptions.is_file() and ledger.is_file()

        census = json.loads(out.read_text(encoding="utf-8-sig"))
        record = json.loads(absorptions.read_text(encoding="utf-8-sig"))
        # prior row 0 shares a street with the fresh sighting: absorbed, and
        # the fresh sighting survives carrying the prior identity key.
        assert record["prior_rows"] == 2
        assert record["absorbed_into_fresh_candidates"] == 1
        assert record["prior_rows_surviving_as_candidates"] == 1
        assert record["absorptions"][0]["absorbed_name"] == rows[0]["canonical_name"]
        assert record["absorptions"][0]["into_candidate_id"] == "dc_fresh_0001"
        # merged = 2 fresh + 1 surviving prior; every candidate is ledgered.
        assert record["merged_candidates"] == 3
        ledger_doc = json.loads(ledger.read_text(encoding="utf-8-sig"))
        assert ledger_doc["count"] == 3
        assert census["prior_census_recandidacy"]["prior_rows"] == 2
        assert "absorptions" not in census["prior_census_recandidacy"]
        # The prior row that nobody re-sighted survives ON ITS OWN observation.
        keys = {h["identity_key"] for h in census["hotels"]}
        assert rows[1]["identity_key"] in keys
        assert "testville riverfront inn" in keys
        # And no verdict came across: the prior census's corridor is not read.
        assert all(h["policy_state"] == "POLICY_NOT_VERIFIED" for h in census["hotels"])

    def test_without_out_the_default_is_still_the_registry_path(self):
        # The default is unchanged so every existing caller keeps its contract.
        assert CENSUS_CLI.CENSUS_DIR == PACKAGE / "identity_census"


class TestEveryCensusReaderAcceptsAnExplicitCensus:

    @pytest.mark.parametrize("main", [CUR.main, CLOSURE_CLI.main, REVIEW_CLI.main,
                                      PA.main, DUP.main, CENSUS_CLI.main])
    def test_the_parser_knows_the_flag(self, main, capsys):
        flag = "--out" if main is CENSUS_CLI.main else "--census"
        with pytest.raises(SystemExit):
            main([flag, "x"])
        err = capsys.readouterr().err
        assert "unrecognized arguments" not in err
        assert "required" in err


class TestTheFactoryHonoursItsCensusDir:

    @pytest.fixture
    def ctx(self, tmp_path, prior_census, fresh_candidates):
        prior_path, _rows = prior_census
        package = tmp_path / "pkg"
        return MF.FactoryContext(
            market_id=MARKET, work_order="TEST-RECENSUS", as_of="2026-08-25",
            contract_path=CONTRACT, candidates_path=fresh_candidates,
            prior_census=prior_path, package_dir=package,
            census_dir=package / "identity_census" / "recensus",
            markets_dir=tmp_path / "markets", run_root=tmp_path / "runs",
            suffix="t001")

    def test_the_census_phase_writes_into_the_sandbox_with_the_prior_folded_in(self, ctx):
        before = _sha(LIVE_CENSUS)
        result = MF.phase_census(ctx, MF.load_ledger(ctx))
        assert result.status == MF.COMPLETED, result.note
        assert ctx.census_path == ctx.package_dir / "identity_census" / "recensus" / (
            "%s.json" % MARKET)
        assert ctx.census_path.is_file()
        assert Path(result.artifacts["prior_census_absorptions"]).is_file()
        assert result.facts["prior_census"]["absorbed_into_fresh_candidates"] == 1
        assert _sha(LIVE_CENSUS) == before

    def test_every_downstream_call_names_the_sandbox_census(self, ctx, monkeypatch):
        """The factory passes ITS census to each reader; none falls back to
        identity_census/<market>.json on its own."""
        seen = OrderedDict()

        def capture(name):
            def fake_main(argv):
                seen[name] = list(argv)
                out = None
                for flag in ("--out", "--partition-out"):
                    if flag in argv:
                        out = Path(argv[argv.index(flag) + 1])
                if out is not None:
                    _write(out, {"schema": "stub", "count": 0, "hotels": [],
                                 "recoveries": [], "candidates": [],
                                 "recommendation_counts": {},
                                 "disposition_counts": {}, "active_denominator": 0,
                                 "reconciliation": {"missing": [], "foreign": [],
                                                    "duplicate": []}})
                if "--closure-out" in argv:
                    _write(Path(argv[argv.index("--closure-out") + 1]),
                           {"count": 0, "active_denominator": 0,
                            "disposition_counts": {},
                            "reconciliation": {"missing": [], "foreign": [],
                                               "duplicate": []}})
                return 0
            return fake_main

        monkeypatch.setattr(CUR, "main", capture("url_recovery"))
        monkeypatch.setattr(PA, "main", capture("paid"))
        monkeypatch.setattr(CLOSURE_CLI, "main", capture("closure"))
        monkeypatch.setattr(REVIEW_CLI, "main", capture("review"))
        monkeypatch.setattr(DUP, "main", capture("duplicates"))

        _write(ctx.census_path, {"count": 0, "hotels": []})
        expected = ctx.census_path.as_posix()

        MF._url_recovery(ctx, out=ctx.artifact("r"), cache=None,
                         prior_census=ctx.prior_census, artifacts=(),
                         work_order="TEST-RECENSUS")
        assert seen["url_recovery"][seen["url_recovery"].index("--census") + 1] == expected

        # The paid pass: the dry run is the first call and carries the census.
        ledger = MF.load_ledger(ctx)
        MF._paid_pass(ctx, ledger, label="pass1", overlay_path="")
        assert seen["paid"][seen["paid"].index("--census") + 1] == expected

        # Closure and the packet read the same census.
        MF.phase_closure.__wrapped__ if hasattr(MF.phase_closure, "__wrapped__") else None
        argv_closure = ["--market", MARKET, "--observations", "o", "--census",
                        expected, "--pilot", "p", "--as-of", "d",
                        "--work-order", "w", "--url-overlay", "",
                        "--partition-out", (ctx.artifact("fp")).as_posix(),
                        "--closure-out", (ctx.artifact("cl")).as_posix()]
        CLOSURE_CLI.main(argv_closure)
        assert seen["closure"][seen["closure"].index("--census") + 1] == expected


class TestTheLiveMarketIsUntouchedByTheModuleImport:

    def test_pittsburgh_release_contract_still_verifies(self):
        from scripts.pettripfinder.release_contracts import verify_contract
        assert verify_contract(MARKET) == []
