"""PTF-MARKET-FACTORY-COVERAGE-HARDENING-001 -- the generic lifecycle, sequenced.

What these tests pin is ORDER and GATES, with every phase runner stubbed so
nothing fetches, spends or writes into the committed package directory:

* zero-cost recovery runs before paid acquisition, as an artifact gate;
* newly recovered URLs are rerouted automatically (the reroute phase reads the
  recovery artifact, not a flag);
* founder review cannot begin before the coverage-completion artifact says READY;
* a paid phase without --authorise-spend stops at its cost plan;
* the hardened baseline every module the work order names still exists;
* live production data is unchanged.
"""

from __future__ import annotations

import json
from collections import OrderedDict
from pathlib import Path

import pytest

from scripts.pettripfinder import market_coverage_cli as MC
from scripts.pettripfinder import market_factory_cli as MF
from scripts.pettripfinder.contracts import coverage as COV


def _write(path: Path, document) -> str:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(document, indent=1), encoding="utf-8")
    return path.as_posix()


@pytest.fixture
def ctx(tmp_path):
    package = tmp_path / "pkg"
    census_dir = package / "identity_census"
    census_dir.mkdir(parents=True)
    _write(census_dir / "testville-xx.json", {"count": 1, "hotels": [
        {"identity_key": "inn", "canonical_name": "Inn", "official_url": "",
         "identity_state": "IDENTITY_CONFIRMED", "lodging_state": "LODGING_BY_NAME",
         "corridor": "testville-xx__core", "market_id": "testville-xx"}]})
    return MF.FactoryContext(
        market_id="testville-xx", work_order="TEST", as_of="2026-08-25",
        package_dir=package, census_dir=census_dir, markets_dir=tmp_path / "markets",
        run_root=tmp_path / "runs", authorised_cap_usd=10.0)


class Stubs:
    """Runners that record the order they ran in and write minimal artifacts."""

    def __init__(self, ctx, *, ready=True):
        self.ctx = ctx
        self.ran = []
        self.ready = ready

    def _ok(self, phase, **artifacts):
        def runner(ctx, ledger):
            self.ran.append(phase)
            written = OrderedDict()
            for name, doc in artifacts.items():
                written[name] = _write(ctx.artifact("%s_%s" % (phase, name)), doc)
            return MF.PhaseResult(MF.COMPLETED, "stub", artifacts=written)
        return runner

    def table(self):
        recovery_doc = {"schema": "ptf-census-url-recovery/1.0", "recoveries": [
            {"identity_key": "inn", "recovered_url": "https://inn.example/",
             "binding": "PHONE", "evidence": {}}]}
        coverage_doc = {
            "schema": COV.SCHEMA, "evaluation_stage": MC.STAGE_FOUNDER_REVIEW_PACKET,
            "booleans": {"READY_FOR_FOUNDER_REVIEW": self.ready,
                         "CLOSURE_RECONCILED": True},
            "identities_the_factory_can_still_move": [] if self.ready else ["inn"],
        }
        return {
            MF.CENSUS: self._ok(MF.CENSUS),
            MF.ROUTING: self._ok(MF.ROUTING),
            MF.ZERO_COST_URL_RECOVERY: self._ok(MF.ZERO_COST_URL_RECOVERY,
                                                url_recovery=recovery_doc),
            MF.PRIOR_BUILD_RECONCILIATION: self._ok(MF.PRIOR_BUILD_RECONCILIATION,
                                                    url_recovery=recovery_doc),
            MF.REROUTE: MF.phase_reroute,           # the real one: reads the artifact
            MF.ACQUISITION: self._ok(MF.ACQUISITION),
            MF.DECLINED_EVIDENCE_RECOVERY: self._ok(MF.DECLINED_EVIDENCE_RECOVERY),
            MF.REROUTE_RECOVERED: self._ok(MF.REROUTE_RECOVERED,
                                           url_recovery=recovery_doc),
            MF.ACQUIRE_NEWLY_ROUTABLE: self._ok(MF.ACQUIRE_NEWLY_ROUTABLE),
            MF.ALTERNATE_LANE_HANDLING: self._ok(MF.ALTERNATE_LANE_HANDLING),
            MF.COVERAGE_EXHAUSTION: self._ok(MF.COVERAGE_EXHAUSTION),
            MF.CLOSURE: self._ok(MF.CLOSURE),
            MF.FOUNDER_REVIEW_PACKET: self._ok(MF.FOUNDER_REVIEW_PACKET,
                                               packet={"count": 1},
                                               coverage=coverage_doc),
            MF.FOUNDER_REVIEW: MF.phase_founder_review,   # the real gate
        }


class TestLifecycleOrder:
    def test_the_lifecycle_is_the_fourteen_phases_in_the_work_orders_order(self):
        assert MF.PHASES == (
            "census", "routing", "zero_cost_url_recovery",
            "prior_build_reconciliation", "reroute", "acquisition",
            "declined_evidence_recovery", "reroute_recovered",
            "acquire_newly_routable", "alternate_lane_handling",
            "coverage_exhaustion", "closure", "founder_review_packet",
            "founder_review")

    def test_zero_cost_recovery_runs_before_paid_acquisition(self, ctx):
        stubs = Stubs(ctx)
        MF.run_phases(ctx, through=MF.ACQUISITION, runners=stubs.table())
        assert stubs.ran.index(MF.ZERO_COST_URL_RECOVERY) < stubs.ran.index(MF.ACQUISITION)
        assert stubs.ran.index(MF.PRIOR_BUILD_RECONCILIATION) < stubs.ran.index(MF.ACQUISITION)

    def test_paid_acquisition_is_gated_on_the_recovery_artifact_not_a_flag(self, ctx):
        stubs = Stubs(ctx)
        table = stubs.table()
        # A reconciliation phase that "completes" without writing its artifact.
        table[MF.PRIOR_BUILD_RECONCILIATION] = stubs._ok(MF.PRIOR_BUILD_RECONCILIATION)
        table[MF.REROUTE] = stubs._ok(MF.REROUTE)
        ledger = MF.run_phases(ctx, through=MF.ACQUISITION, runners=table)
        assert MF.status_of(ledger, MF.ACQUISITION) == MF.BLOCKED
        assert "zero-cost URL recovery artifact" in ledger["phases"][MF.ACQUISITION]["note"]
        assert MF.ACQUISITION not in stubs.ran

    def test_newly_recovered_urls_are_rerouted_automatically(self, ctx):
        stubs = Stubs(ctx)
        ledger = MF.run_phases(ctx, through=MF.REROUTE, runners=stubs.table())
        assert MF.status_of(ledger, MF.REROUTE) == MF.COMPLETED
        facts = ledger["phases"][MF.REROUTE]["facts"]
        assert facts["overlay_applied"] == 1
        assert facts["overlay_rows"] == ["inn"]
        assert facts["routed"] == 1          # unrouted before, routed after
        routing = json.loads(Path(ledger["phases"][MF.REROUTE]["artifacts"]
                                  ["routing_overlay"]["path"]).read_text(encoding="utf-8"))
        assert routing["entries"][0]["routing_state"] == "ROUTED"
        assert routing["entries"][0]["source_url"] == "https://inn.example/"

    def test_a_second_paid_pass_waits_for_declined_evidence_recovery(self, ctx):
        stubs = Stubs(ctx)
        ledger = MF.run_phases(ctx, through=MF.ACQUISITION, runners=stubs.table())
        # Pretend declined-evidence recovery was skipped over by hand.
        ledger["phases"][MF.DECLINED_EVIDENCE_RECOVERY] = {"status": MF.NOT_RUN}
        ok, why = MF.phase_gate(MF.ACQUIRE_NEWLY_ROUTABLE, ledger)
        assert not ok and "declined_evidence_recovery" in why
        # And the artifact gate behind the predecessor check says the same
        # thing when every predecessor is nominally satisfied.
        ledger["phases"][MF.DECLINED_EVIDENCE_RECOVERY] = {"status": MF.BLOCKED}
        ledger["phases"][MF.REROUTE_RECOVERED] = {"status": MF.COMPLETED}
        ok, why = MF.phase_gate(MF.ACQUIRE_NEWLY_ROUTABLE, ledger)
        assert not ok and "declined_evidence_recovery" in why

    def test_a_satisfied_phase_is_not_run_twice(self, ctx):
        stubs = Stubs(ctx)
        MF.run_phases(ctx, through=MF.ROUTING, runners=stubs.table())
        MF.run_phases(ctx, through=MF.ROUTING, runners=stubs.table())
        assert stubs.ran.count(MF.CENSUS) == 1

    def test_a_blocked_phase_stops_the_sequence(self, ctx):
        stubs = Stubs(ctx)
        table = stubs.table()
        table[MF.ROUTING] = lambda c, l: MF.PhaseResult(MF.BLOCKED, "no")
        ledger = MF.run_phases(ctx, through=MF.FOUNDER_REVIEW, runners=table)
        assert MF.status_of(ledger, MF.ROUTING) == MF.BLOCKED
        assert MF.status_of(ledger, MF.ZERO_COST_URL_RECOVERY) == MF.NOT_RUN
        assert stubs.ran == [MF.CENSUS]

    def test_a_crashing_runner_is_recorded_as_blocked_not_raised(self, ctx):
        stubs = Stubs(ctx)
        table = stubs.table()

        def boom(c, l):
            raise RuntimeError("provider exploded")

        table[MF.ROUTING] = boom
        ledger = MF.run_phases(ctx, through=MF.ROUTING, runners=table)
        assert MF.status_of(ledger, MF.ROUTING) == MF.BLOCKED
        assert "provider exploded" in ledger["phases"][MF.ROUTING]["note"]


class TestFounderReviewGate:
    def test_founder_review_cannot_begin_before_coverage_is_evaluated(self, ctx):
        stubs = Stubs(ctx)
        table = stubs.table()
        table[MF.FOUNDER_REVIEW_PACKET] = stubs._ok(MF.FOUNDER_REVIEW_PACKET,
                                                    packet={"count": 1})
        ledger = MF.run_phases(ctx, through=MF.FOUNDER_REVIEW, runners=table)
        assert MF.status_of(ledger, MF.FOUNDER_REVIEW) == MF.BLOCKED
        assert "coverage has not been evaluated" in ledger["phases"][MF.FOUNDER_REVIEW]["note"]

    def test_founder_review_is_refused_while_the_factory_can_still_move_a_row(self, ctx):
        stubs = Stubs(ctx, ready=False)
        ledger = MF.run_phases(ctx, through=MF.FOUNDER_REVIEW, runners=stubs.table())
        assert MF.status_of(ledger, MF.FOUNDER_REVIEW) == MF.BLOCKED
        note = ledger["phases"][MF.FOUNDER_REVIEW]["note"]
        assert "READY_FOR_FOUNDER_REVIEW is false" in note and "inn" in note

    def test_founder_review_hands_off_to_a_human_when_ready(self, ctx):
        stubs = Stubs(ctx, ready=True)
        ledger = MF.run_phases(ctx, through=MF.FOUNDER_REVIEW, runners=stubs.table())
        assert MF.status_of(ledger, MF.FOUNDER_REVIEW) == MF.AWAITING_HUMAN
        assert "a person sets founder_decision" in ledger["phases"][MF.FOUNDER_REVIEW]["note"]

    def test_the_gate_reads_the_stage_the_artifact_was_evaluated_at(self, ctx):
        stubs = Stubs(ctx, ready=True)
        table = stubs.table()
        early = {"schema": COV.SCHEMA, "evaluation_stage": MC.STAGE_COVERAGE_EXHAUSTION,
                 "booleans": {"READY_FOR_FOUNDER_REVIEW": True},
                 "identities_the_factory_can_still_move": []}
        table[MF.FOUNDER_REVIEW_PACKET] = stubs._ok(MF.FOUNDER_REVIEW_PACKET,
                                                    packet={"count": 1}, coverage=early)
        ledger = MF.run_phases(ctx, through=MF.FOUNDER_REVIEW, runners=table)
        assert MF.status_of(ledger, MF.FOUNDER_REVIEW) == MF.BLOCKED
        assert "before the packet existed" in ledger["phases"][MF.FOUNDER_REVIEW]["note"]


class TestSpending:
    def test_the_paid_phases_are_exactly_the_three_that_can_spend(self):
        assert MF.PAID_PHASES == {"acquisition", "acquire_newly_routable",
                                  "alternate_lane_handling"}

    def test_without_authorisation_a_paid_phase_stops_at_its_cost_plan(self, ctx, monkeypatch):
        # The real _paid_pass, with the dry run and the plan stubbed at the
        # tool boundary so nothing touches a vendor.
        calls = []

        def fake_pa_main(argv):
            calls.append(list(argv))
            out = Path(argv[argv.index("--out") + 1])
            _write(out, {"cohort": [{"identity_key": "inn", "provider": "firecrawl",
                                     "family": "INDEPENDENT"}],
                         "cohort_size": 1, "settled_size": 0, "suppressed_size": 0,
                         "queue": ["inn"], "cohort_rule": {"terminal_prior_outcomes": []},
                         "preflight": {"checks": []}, "market_id": "testville-xx",
                         "run_id": "r"})
            return 0

        def fake_cp_main(argv):
            calls.append(list(argv))
            out = Path(argv[argv.index("--out") + 1])
            _write(out, {"schema": "ptf-cohort-cost-plan/1.0",
                         "recommended_cap_usd_minor": 444,
                         "predicted_completion_under_balance": {"attemptable": 1},
                         "double_buy_check": {"no_property_is_bought_twice": True}})
            return 0

        monkeypatch.setattr(MF.PA, "main", fake_pa_main)
        from scripts.pettripfinder.acquisition import cohort_cost_plan as CP
        monkeypatch.setattr(CP, "main", fake_cp_main)
        ledger = MF.load_ledger(ctx)
        result = MF._paid_pass(ctx, ledger, label="pass1", overlay_path="")
        assert result.status == MF.AWAITING_AUTHORISATION
        assert "cost_plan" in result.artifacts and "dry_run" in result.artifacts
        assert result.facts["no_property_is_bought_twice"] is True
        # Only the dry run was invoked on the paid tool; never a spending call.
        pa_calls = [c for c in calls if "--cap-usd" in c]
        assert len(pa_calls) == 1 and "--dry-run" in pa_calls[0]
        assert ledger["passes"] == []

    def test_with_authorisation_the_pass_runs_under_the_plans_cap_and_its_gate(
            self, ctx, monkeypatch):
        calls = []

        def fake_pa_main(argv):
            calls.append(list(argv))
            out = Path(argv[argv.index("--out") + 1])
            if "--dry-run" in argv:
                _write(out, {"cohort": [{"identity_key": "inn", "provider": "firecrawl",
                                         "family": "INDEPENDENT"}],
                             "cohort_size": 1, "settled_size": 0,
                             "suppressed_size": 0, "queue": ["inn"],
                             "cohort_rule": {"terminal_prior_outcomes": []},
                             "preflight": {"checks": []},
                             "market_id": "testville-xx", "run_id": "r"})
            else:
                assert "--cost-plan" in argv
                _write(out, {"outcome": "BATCH_COMPLETE", "attempted": 1,
                             "deferred": [], "spend": {"binding_usd_minor": 16},
                             "results": []})
            return 0

        def fake_cp_main(argv):
            out = Path(argv[argv.index("--out") + 1])
            _write(out, {"schema": "ptf-cohort-cost-plan/1.0",
                         "recommended_cap_usd_minor": 444,
                         "predicted_completion_under_balance": {"attemptable": 1},
                         "double_buy_check": {"no_property_is_bought_twice": True}})
            return 0

        monkeypatch.setattr(MF.PA, "main", fake_pa_main)
        from scripts.pettripfinder.acquisition import cohort_cost_plan as CP
        monkeypatch.setattr(CP, "main", fake_cp_main)
        ctx.spend_authorised = True
        ledger = MF.load_ledger(ctx)
        result = MF._paid_pass(ctx, ledger, label="pass1", overlay_path="")
        assert result.status == MF.COMPLETED
        spending = [c for c in calls if "--dry-run" not in c][0]
        assert spending[spending.index("--cap-usd") + 1] == "4.44"
        assert len(ledger["passes"]) == 1
        assert ledger["passes"][0]["outcome"] == "BATCH_COMPLETE"

    def test_a_plan_that_finds_a_double_buy_blocks_the_pass(self, ctx, monkeypatch):
        def fake_pa_main(argv):
            out = Path(argv[argv.index("--out") + 1])
            _write(out, {"cohort": [{"identity_key": "inn", "provider": "firecrawl",
                                     "family": "INDEPENDENT"}],
                         "cohort_size": 1, "settled_size": 0, "suppressed_size": 0,
                         "queue": ["inn"], "cohort_rule": {"terminal_prior_outcomes": []},
                         "preflight": {"checks": []}, "market_id": "testville-xx",
                         "run_id": "r"})
            return 0

        def fake_cp_main(argv):
            out = Path(argv[argv.index("--out") + 1])
            _write(out, {"schema": "ptf-cohort-cost-plan/1.0",
                         "double_buy_check": {"no_property_is_bought_twice": False}})
            return 1

        monkeypatch.setattr(MF.PA, "main", fake_pa_main)
        from scripts.pettripfinder.acquisition import cohort_cost_plan as CP
        monkeypatch.setattr(CP, "main", fake_cp_main)
        ctx.spend_authorised = True
        result = MF._paid_pass(ctx, MF.load_ledger(ctx), label="pass1", overlay_path="")
        assert result.status == MF.BLOCKED
        assert "already answered" in result.note


class TestPlanAndLedger:
    def test_plan_names_every_phase_and_which_may_spend(self, ctx):
        document = MF.plan(ctx)
        assert [p["phase"] for p in document["phases"]] == list(MF.PHASES)
        assert {p["phase"] for p in document["phases"] if p["may_spend"]} == MF.PAID_PHASES
        assert document["phases"][0]["can_start_now"] is True
        assert document["phases"][5]["can_start_now"] is False

    def test_the_ledger_is_durable_across_invocations(self, ctx):
        stubs = Stubs(ctx)
        MF.run_phases(ctx, through=MF.ROUTING, runners=stubs.table())
        ledger = MF.load_ledger(ctx)
        assert ledger["schema"] == MF.LEDGER_SCHEMA
        assert MF.status_of(ledger, MF.CENSUS) == MF.COMPLETED
        assert MF.status_of(ledger, MF.ROUTING) == MF.COMPLETED
        assert MF.status_of(ledger, MF.REROUTE) == MF.NOT_RUN


class TestHardenedBaseline:
    def test_every_generic_improvement_the_work_order_names_still_exists(self):
        import importlib
        for label, module, symbol in MF.HARDENED_BASELINE:
            loaded = importlib.import_module(module)
            assert hasattr(loaded, symbol), (label, module, symbol)

    def test_the_baseline_names_no_market(self):
        for label, module, symbol in MF.HARDENED_BASELINE:
            for city in ("louisville", "st_louis", "milwaukee", "pittsburgh",
                         "indianapolis", "columbus", "cleveland", "dayton",
                         "cincinnati", "detroit"):
                assert city not in module.lower(), (label, module)

    def test_the_orchestrator_names_no_market(self):
        source = Path(MF.__file__).read_text(encoding="utf-8")
        body = source.split('"""', 2)[2]          # everything after the docstring
        for city in ("louisville", "st-louis", "st_louis", "milwaukee",
                     "pittsburgh", "indianapolis", "columbus", "cleveland",
                     "dayton", "cincinnati", "detroit"):
            assert city not in body.lower(), city


class TestLiveProductionUnchanged:
    def test_every_launch_authorized_market_still_agrees_with_its_release_contract(self):
        from scripts.pettripfinder import release_contracts as RC
        participation = json.loads(
            Path("deploy/netlify/launch_participation.json").read_text(encoding="utf-8"))
        live = [m["market_id"] for m in participation["markets"]
                if m["launch_status"] == "FOUNDER_AUTHORIZED_FOR_LAUNCH"]
        assert len(live) >= 7          # seven markets were live at PTF-010
        disagreements = RC.verify_all()
        for market_id in live:
            assert disagreements.get(market_id, []) == [], market_id

    def test_no_new_module_edits_a_committed_authority_file(self):
        # The hardening touches scripts and tests only; no authority shard, no
        # release contract, no census, no deployment record.
        import subprocess
        changed = subprocess.run(
            ["git", "diff", "--name-only", "HEAD", "--"],
            capture_output=True, text=True, check=False).stdout.split()
        untracked = subprocess.run(
            ["git", "ls-files", "--others", "--exclude-standard"],
            capture_output=True, text=True, check=False).stdout.split()
        for path in changed + untracked:
            assert not path.startswith("launch_packages/pettripfinder/markets/authority/"), path
            assert not path.startswith("deploy/netlify/"), path
            assert not path.startswith("launch_packages/pettripfinder/identity_census/"), path


# -- PTF-DISCOVERY-OVERPASS-RESILIENCE-001 ----------------------------------- #

class TestCensusGatesOnFreeDiscovery:
    """A census is never built, and never called complete, while free discovery
    has cells left that an approved endpoint could still answer -- or while
    every approved endpoint is cooling down."""

    def _ctx_with_candidates(self, ctx, tmp_path):
        candidates = tmp_path / "cands.json"
        candidates.write_text("[]", encoding="utf-8")
        ctx.candidates_path = candidates
        ctx.contract_path = tmp_path / "contract.json"
        ctx.contract_path.write_text("{}", encoding="utf-8")
        ctx.census_path.unlink()
        return ctx

    def test_no_discovery_cache_blocks_the_census_rather_than_assuming(self, ctx, tmp_path):
        ctx = self._ctx_with_candidates(ctx, tmp_path)
        ctx.discovery_cache = tmp_path / "nowhere" / "cache"
        result = MF.phase_census(ctx, MF.load_ledger(ctx))
        assert result.status == MF.BLOCKED
        assert "cannot be evaluated" in result.note

    def test_cells_remaining_with_an_endpoint_available_blocks_as_runnable(self, ctx, tmp_path, monkeypatch):
        from scripts.pettripfinder.discovery import discovery_state as DS
        ctx = self._ctx_with_candidates(ctx, tmp_path)
        ctx.discovery_cache = tmp_path / "disc" / "cache"
        ctx.discovery_cache.mkdir(parents=True)
        monkeypatch.setattr(DS, "build", lambda *a, **k: {
            "state": DS.RUNNABLE, "OVERPASS_CELLS_TOTAL": 30, "OVERPASS_CELLS_CACHED": 8,
            "OVERPASS_CELLS_REMAINING": 22, "available_endpoint_ids": ["overpass.kumi.systems"],
            "earliest_cooldown_expiry": "", "paid_discovery_fallback": {"state": "x"}})
        result = MF.phase_census(ctx, MF.load_ledger(ctx))
        assert result.status == MF.BLOCKED
        assert "FREE_DISCOVERY_RUNNABLE" in result.note and "22 remaining" in result.note
        assert result.facts["discovery_state"] == DS.RUNNABLE

    def test_every_endpoint_down_blocks_as_waiting_with_the_cooldown(self, ctx, tmp_path, monkeypatch):
        from scripts.pettripfinder.discovery import discovery_state as DS
        ctx = self._ctx_with_candidates(ctx, tmp_path)
        ctx.discovery_cache = tmp_path / "disc" / "cache"
        ctx.discovery_cache.mkdir(parents=True)
        monkeypatch.setattr(DS, "build", lambda *a, **k: {
            "state": DS.WAITING, "OVERPASS_CELLS_TOTAL": 30, "OVERPASS_CELLS_CACHED": 8,
            "OVERPASS_CELLS_REMAINING": 22, "available_endpoint_ids": [],
            "earliest_cooldown_expiry": "2026-08-25T13:00:00+00:00",
            "paid_discovery_fallback": {"state": "PAID_DISCOVERY_FALLBACK_AVAILABLE"}})
        result = MF.phase_census(ctx, MF.load_ledger(ctx))
        assert result.status == MF.BLOCKED
        assert "WAITING_FOR_FREE_DISCOVERY" in result.note
        assert "2026-08-25T13:00:00" in result.note
        assert "NOT authorised" in result.note
        assert (tmp_path / "pkg" / "testville_xx_discovery_state_001.json").is_file()

    def test_the_lifecycle_still_gates_everything_behind_the_census(self, ctx, tmp_path):
        ctx = self._ctx_with_candidates(ctx, tmp_path)
        ctx.discovery_cache = tmp_path / "nowhere" / "cache"
        ledger = MF.run_phases(ctx, through=MF.FOUNDER_REVIEW)
        assert MF.status_of(ledger, MF.CENSUS) == MF.BLOCKED
        assert all(MF.status_of(ledger, p) == MF.NOT_RUN for p in MF.PHASES[1:])
