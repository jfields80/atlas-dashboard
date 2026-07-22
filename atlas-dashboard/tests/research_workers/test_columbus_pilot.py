"""ATLAS-WORKERS-004 -- Columbus/Dublin hotel live intake pilot tests.

All OFFLINE: FakeProvider + mocks, no network, no paid call, no production write,
no credential persistence. Proves deterministic intake, the spend airlock, exact
Nano enforcement, routing integration, and safe gitignored persistence.
"""

from __future__ import annotations

import dataclasses
import json

import pytest

from services.research_workers import columbus_pilot as CP
from services.research_workers import routing as RT
from services.research_workers import vocabulary as V
from services.research_workers.cli import main as cli_main
from services.research_workers.contracts import Assignment, canonical_json
from services.research_workers.model_eval import VALIDATOR_VERSION
from services.research_workers.prompt import PROMPT_VERSION
from services.research_workers.providers import FakeProvider


# --------------------------------------------------------------------------- #
# Helpers.
# --------------------------------------------------------------------------- #

def _candidates():
    return CP.load_columbus_hotel_candidates()


def _fake_factory(input_tokens=1200, output_tokens=120, cached=0):
    def make(name, *, auth=None, base_url=None, request_options=None, **_):
        class _P:
            def __init__(self):
                self.name = name
                self._f = FakeProvider()

            def propose(self, assignment, *, model, output_token_cap, timeout_s, max_retries):
                p = self._f.propose(assignment, model=model)
                return dataclasses.replace(p, provider=name, model=model, input_tokens=input_tokens,
                                           output_tokens=output_tokens, cached_input_tokens=cached,
                                           latency_ms=150)
        return _P()
    return make


def _authorize(monkeypatch, key="OPENAI_KEY_VALUE"):
    monkeypatch.setenv("ATLAS_BENCHMARK_SPEND_AUTHORIZATION", "YES_MAX_1_USD")
    monkeypatch.setenv("OPENAI_API_KEY", key)


def _synth(name="Test Hotel", evidence="Pets are welcome at our hotel.",
           source_url="https://ex.example/pets", source_type=V.SOURCE_OFFICIAL_PROPERTY):
    return CP.HotelCandidate(
        name=name, listing_key=CP.normalize_listing_key(name), address="1 Main St Columbus OH",
        phone="614-000-0000", source_url=source_url, source_type=source_type,
        observed_at="2026-07-15", evidence_text=evidence, candidate_id=CP.normalize_listing_key(name))


# --------------------------------------------------------------------------- #
# 1. Discovery + deterministic assignment.
# --------------------------------------------------------------------------- #

def test_authoritative_hotel_discovery():
    cs = _candidates()
    assert len(cs) == 25                                  # authoritative Columbus/Dublin count
    keys = [c.listing_key for c in cs]
    assert keys == sorted(keys)                           # deterministic order
    names = {c.name for c in cs}
    assert "Sonesta Columbus Downtown" in names and "Drury Inn & Suites Columbus Polaris" in names
    for c in cs:                                          # every candidate carries usable authority
        assert c.evidence_text and c.source_url and c.source_type in V.SOURCE_TYPES


def test_deterministic_assignment_generation():
    c = _candidates()[0]
    a1 = CP.build_pilot_assignment(c)
    a2 = CP.build_pilot_assignment(c)
    assert a1.assignment_id == a2.assignment_id
    assert canonical_json(a1.to_dict()) == canonical_json(a2.to_dict())    # byte-identical
    a1.validate()
    # A changed evidence body yields a distinguishable identity.
    c2 = dataclasses.replace(c, evidence_text=c.evidence_text + " Updated.")
    assert CP.build_pilot_assignment(c2).assignment_id != a1.assignment_id


def test_five_verified_hotels_key_match_authoritative_facts():
    """The five formally-verified hotels key-match launch_packages
    hotel_policy_facts.json (the normalization matches the importer authority)."""
    facts = json.loads(open("launch_packages/pettripfinder/hotel_policy_facts.json",
                            encoding="utf-8").read())
    fact_keys = {h["key"] for h in facts["hotels"]}
    pilot_keys = {c.listing_key for c in _candidates()}
    assert fact_keys.issubset(pilot_keys)                 # all 5 authoritative keys present


# --------------------------------------------------------------------------- #
# 2. Readiness classification / blocking.
# --------------------------------------------------------------------------- #

def test_all_real_candidates_ready():
    classified = CP.classify_candidates(_candidates())
    assert all(c.readiness == CP.READY_FOR_RESEARCH for c in classified)
    assert len(classified) == 25


def test_missing_evidence_blocked():
    cls = CP.classify_candidates([_synth(evidence="")])
    assert cls[0].readiness == CP.BLOCKED_MISSING_EVIDENCE and cls[0].assignment is None


def test_missing_source_blocked():
    cls = CP.classify_candidates([_synth(source_url="")])
    assert cls[0].readiness == CP.BLOCKED_MISSING_EVIDENCE


def test_invalid_contract_blocked():
    cls = CP.classify_candidates([_synth(source_type="BOGUS_TYPE")])
    assert cls[0].readiness == CP.BLOCKED_INVALID_CONTRACT and cls[0].assignment is None


def test_duplicate_identity_blocked():
    dup = [_synth(name="Same Hotel"), _synth(name="Same  Hotel")]   # normalize to same key
    cls = CP.classify_candidates(dup)
    assert all(c.readiness == CP.BLOCKED_IDENTITY_CONFLICT for c in cls)


# --------------------------------------------------------------------------- #
# 3. Dry-run: zero network, zero writes.
# --------------------------------------------------------------------------- #

def test_dry_run_makes_no_network_call_and_no_write(tmp_path):
    def _boom(*a, **k):
        raise AssertionError("dry-run must never construct a provider")
    store = CP.PilotStore(root=tmp_path)
    classified = CP.classify_candidates(_candidates())
    report = CP.run_pilot(classified, CP.PilotCaps(), live=False, store=store,
                          provider_factory=_boom)
    assert report["mode"] == "dry_run" and report["hotels"] == []
    assert not any(tmp_path.iterdir())                    # nothing written


def test_checkpoint_reports_exact_nano_and_worst_case_cost():
    classified = CP.classify_candidates(_candidates())
    cp = CP.operator_checkpoint(classified, CP.PilotCaps())
    assert cp["model_snapshot"] == {
        "provider": "openai", "model_id": "gpt-5.4-nano-2026-03-17",
        "pricing_source": "Official OpenAI GPT-5.4 Nano model documentation",
        "pricing_observed_date": "2026-07-20"}
    assert cp["hotels_found"] == 25 and cp["assignments_ready"] == 25
    assert 0.0 < cp["worst_case_estimated_cost_usd"] < 1.00
    assert cp["no_production_write"] is True


# --------------------------------------------------------------------------- #
# 4. Live pilot (fake provider) -- routing + persistence integration.
# --------------------------------------------------------------------------- #

def test_live_pilot_routes_and_persists(monkeypatch, tmp_path):
    _authorize(monkeypatch)
    store = CP.PilotStore(root=tmp_path)
    classified = CP.classify_candidates(_candidates())
    report = CP.run_pilot(classified, CP.PilotCaps(), live=True, store=store,
                          provider_factory=_fake_factory())
    assert report["mode"] == "live" and report["calls_made"] == 25
    agg = report["aggregate"]
    assert sum(agg["routes"].values()) == 25
    assert agg["provider_failures"] == 0 and agg["structurally_valid"] == 25
    # Every hotel routed to a valid state via the WORKERS-003 airlock, with reasons.
    for h in report["hotels"]:
        assert h["route"] in RT.ROUTE_STATES and h["reason_codes"]
        assert h["model"] == "gpt-5.4-nano-2026-03-17"           # exact Nano, no substitution
    # Per-hotel artifacts persisted.
    for sub in ("assignments", "model_results", "validated_results", "routing_envelopes"):
        assert len(list((tmp_path / sub).glob("*.json"))) == 25
    paths = CP.persist_pilot(store, report)
    assert (tmp_path / "operator_summary.json").exists()
    assert (tmp_path / "candidate_export.json").exists()


def test_live_pilot_deterministic_idempotent_rerun(monkeypatch, tmp_path):
    _authorize(monkeypatch)
    store = CP.PilotStore(root=tmp_path)
    classified = CP.classify_candidates(_candidates())
    CP.run_pilot(classified, CP.PilotCaps(), live=True, store=store, provider_factory=_fake_factory())
    n1 = len(list((tmp_path / "assignments").glob("*.json")))
    # FakeProvider is deterministic -> a rerun reproduces identical assignments (idempotent).
    CP.run_pilot(classified, CP.PilotCaps(), live=True, store=store, provider_factory=_fake_factory())
    assert len(list((tmp_path / "assignments").glob("*.json"))) == n1 == 25


def test_resume_reuses_completed_without_network_call(monkeypatch, tmp_path):
    """The core resume guarantee: a second run over identical, already-
    successfully-completed assignments makes ZERO network calls -- the existing
    artifacts are reused, never re-paid."""
    _authorize(monkeypatch)
    store = CP.PilotStore(root=tmp_path)
    cls = CP.classify_candidates(_candidates())
    r1 = CP.run_pilot(cls, CP.PilotCaps(max_assignments=2), live=True, store=store,
                      provider_factory=_fake_factory())
    assert r1["calls_made"] == 2 and r1["aggregate"]["reused_without_call"] == 0

    def _boom(name, **_):
        class _P:
            def propose(self, *a, **k):
                raise AssertionError("no network call for an identical completed assignment")
        return _P()
    r2 = CP.run_pilot(cls, CP.PilotCaps(max_assignments=2), live=True, store=store, provider_factory=_boom)
    assert r2["calls_made"] == 0 and r2["aggregate"]["reused_without_call"] == 2
    assert r2["aggregate"]["routes"] == r1["aggregate"]["routes"]          # same outcome, reused
    assert r2["aggregate"]["reused_cost_usd"] == r2["aggregate"]["total_estimated_cost_usd"]
    assert r2["aggregate"]["new_call_cost_usd"] == 0.0


def test_resume_reattempts_prior_provider_failure(monkeypatch, tmp_path):
    """A prior PROVIDER failure (ok=false) is never reused -- it is re-attempted."""
    from services.research_workers.proposal import ModelProposal, ProviderErrorDetail
    _authorize(monkeypatch)
    store = CP.PilotStore(root=tmp_path)
    cls = CP.classify_candidates(_candidates())

    def failing(name, **_):
        class _P:
            def propose(self, assignment, *, model, output_token_cap, timeout_s, max_retries):
                return ModelProposal(ok=False, error="provider_error:http_503",
                                     structured_output_valid=False, provider=name, model=model,
                                     provider_error=ProviderErrorDetail(http_status=503, transient=True,
                                                                        attempt_count=1))
        return _P()
    CP.run_pilot(cls, CP.PilotCaps(max_assignments=1), live=True, store=store, provider_factory=failing)
    r2 = CP.run_pilot(cls, CP.PilotCaps(max_assignments=1), live=True, store=store,
                      provider_factory=_fake_factory())
    assert r2["calls_made"] == 1 and r2["aggregate"]["reused_without_call"] == 0   # re-attempted


def test_resume_rejects_differing_stored_assignment(monkeypatch, tmp_path):
    """Collision safety preserved: if the stored assignment no longer byte-matches
    the freshly-built one, it is NOT a safe reuse (would re-run / collision-detect)."""
    _authorize(monkeypatch)
    store = CP.PilotStore(root=tmp_path)
    cls = CP.classify_candidates(_candidates())[:1]
    CP.run_pilot(cls, CP.PilotCaps(max_assignments=1), live=True, store=store, provider_factory=_fake_factory())
    a = cls[0].assignment
    ap = store._safe("assignments", a.assignment_id + ".json")
    data = json.loads(ap.read_text(encoding="utf-8"))
    data["listing_name"] = "TAMPERED"
    ap.write_text(json.dumps(data), encoding="utf-8")
    assert CP._completed_artifacts_present(store, a) is False


def test_provider_error_routes_retry_not_hotel_failure(monkeypatch, tmp_path):
    from services.research_workers.proposal import ModelProposal, ProviderErrorDetail
    _authorize(monkeypatch)

    def factory(name, **_):
        class _P:
            def propose(self, assignment, *, model, output_token_cap, timeout_s, max_retries):
                return ModelProposal(ok=False, error="provider_error:http_503",
                                     structured_output_valid=False, provider=name, model=model,
                                     provider_error=ProviderErrorDetail(http_status=503, transient=True,
                                                                        attempt_count=1))
        return _P()
    store = CP.PilotStore(root=tmp_path)
    classified = CP.classify_candidates(_candidates())
    report = CP.run_pilot(classified, CP.PilotCaps(max_assignments=2), live=True, store=store,
                          provider_factory=factory)
    agg = report["aggregate"]
    assert agg["provider_failures"] == 2 and agg["structurally_valid"] == 0
    assert agg["routes"][RT.ROUTE_RETRY] == 2               # transient -> RETRY, not a policy failure
    assert len(list((tmp_path / "failure_diagnostics").glob("*.json"))) == 2


# --------------------------------------------------------------------------- #
# 5. Airlock, caps, filter, exact-model enforcement.
# --------------------------------------------------------------------------- #

def test_spend_airlock_blocks_without_authorization(monkeypatch, tmp_path):
    monkeypatch.delenv("ATLAS_BENCHMARK_SPEND_AUTHORIZATION", raising=False)
    monkeypatch.setenv("OPENAI_API_KEY", "x")
    from services.research_workers.providers import SpendingAirlockError
    classified = CP.classify_candidates(_candidates())
    with pytest.raises(SpendingAirlockError):
        CP.run_pilot(classified, CP.PilotCaps(), live=True, store=CP.PilotStore(root=tmp_path),
                     provider_factory=_fake_factory())


def test_missing_credential_blocks_live(monkeypatch, tmp_path):
    monkeypatch.setenv("ATLAS_BENCHMARK_SPEND_AUTHORIZATION", "YES_MAX_1_USD")
    monkeypatch.delenv("OPENAI_API_KEY", raising=False)
    from services.research_workers.providers import SpendingAirlockError
    classified = CP.classify_candidates(_candidates())
    with pytest.raises(SpendingAirlockError):
        CP.run_pilot(classified, CP.PilotCaps(), live=True, store=CP.PilotStore(root=tmp_path),
                     provider_factory=_fake_factory())


def test_max_assignments_cap(monkeypatch, tmp_path):
    _authorize(monkeypatch)
    classified = CP.classify_candidates(_candidates())
    report = CP.run_pilot(classified, CP.PilotCaps(max_assignments=3), live=True,
                          store=CP.PilotStore(root=tmp_path), provider_factory=_fake_factory())
    assert report["calls_made"] == 3 and len(report["hotels"]) == 3


def test_one_hotel_filter(monkeypatch, tmp_path):
    _authorize(monkeypatch)
    classified = CP.classify_candidates(_candidates())
    report = CP.run_pilot(classified, CP.PilotCaps(), live=True, store=CP.PilotStore(root=tmp_path),
                          provider_factory=_fake_factory(), only_hotel="Sonesta Columbus Downtown")
    assert report["calls_made"] == 1
    assert report["hotels"][0]["listing_name"] == "Sonesta Columbus Downtown"


# --------------------------------------------------------------------------- #
# 6. Persistence safety: deterministic paths, atomic, collision, no prod writes.
# --------------------------------------------------------------------------- #

def test_deterministic_artifact_paths_and_collision(tmp_path):
    store = CP.PilotStore(root=tmp_path)
    a = CP.build_pilot_assignment(_candidates()[0])
    p1 = store.write_assignment(a)
    assert p1 == tmp_path / "assignments" / (a.assignment_id + ".json")
    assert store.write_assignment(a) == p1                # idempotent
    assert len(list((tmp_path / "assignments").glob("*.json"))) == 1
    # Same id, different content -> collision, never silently overwritten.
    tampered = dataclasses.replace(a, listing_name="TAMPERED NAME")
    tampered = dataclasses.replace(tampered, assignment_id=a.assignment_id)
    with pytest.raises(CP.PilotStoreError):
        store.write_assignment(tampered)


def test_pilot_store_refuses_production_roots():
    from services.research_workers.columbus_pilot import _REPO_ROOT
    for bad in ("launch_packages", "scripts", "public", "dist", "services"):
        with pytest.raises(CP.PilotStoreError):
            CP.PilotStore(root=_REPO_ROOT / bad / "x")


def test_no_credential_or_secret_in_artifacts(monkeypatch, tmp_path):
    _authorize(monkeypatch, key="SUPER_SECRET_VALUE")
    store = CP.PilotStore(root=tmp_path)
    classified = CP.classify_candidates(_candidates())
    report = CP.run_pilot(classified, CP.PilotCaps(max_assignments=3), live=True, store=store,
                          provider_factory=_fake_factory())
    CP.persist_pilot(store, report)
    for path in tmp_path.rglob("*.json"):
        blob = path.read_text(encoding="utf-8")
        assert "SUPER_SECRET_VALUE" not in blob
        assert "Authorization" not in blob and "OPENAI_API_KEY" not in blob


# --------------------------------------------------------------------------- #
# 7. Candidate export + operator summary.
# --------------------------------------------------------------------------- #

def test_candidate_export_non_production_and_separated(monkeypatch, tmp_path):
    _authorize(monkeypatch)
    store = CP.PilotStore(root=tmp_path)
    classified = CP.classify_candidates(_candidates())
    report = CP.run_pilot(classified, CP.PilotCaps(), live=True, store=store,
                          provider_factory=_fake_factory())
    export = CP.build_candidate_export(report)
    assert export["non_production"] is True and export["auto_import"] is False
    assert set(export["status_markers"]) == {"NON_PRODUCTION", "HUMAN_REVIEW_REQUIRED_BEFORE_IMPORT"}
    # Routes kept in separate buckets; totals reconcile.
    total = sum(export["counts"].values())
    assert total == 25
    assert len(export["ready_candidates"]) == export["counts"]["READY"]
    assert len(export["review_candidates"]) == export["counts"]["REVIEW"]
    # No READY candidate carries a REVIEW/RETRY/REJECTED reason (separation is real).
    for h in export["ready_candidates"]:
        assert h["route"] == RT.ROUTE_READY


def test_operator_summary_counts_and_cost(monkeypatch, tmp_path):
    _authorize(monkeypatch)
    store = CP.PilotStore(root=tmp_path)
    classified = CP.classify_candidates(_candidates())
    report = CP.run_pilot(classified, CP.PilotCaps(), live=True, store=store,
                          provider_factory=_fake_factory(input_tokens=1000, output_tokens=100))
    s = CP.build_operator_summary(report)
    assert s["inventory"]["authoritative_hotel_candidates"] == 25
    assert s["inventory"]["successful_model_responses"] == 25
    assert sum(s["routing"]["counts"].values()) == 25
    # Cost aggregation reconciles with the per-hotel records.
    per_hotel = sum(h["estimated_cost_usd"] for h in report["hotels"])
    assert abs(s["cost"]["total_estimated_cost_usd"] - per_hotel) < 1e-6
    assert s["cost"]["total_estimated_cost_usd"] < 1.00
    # No unfounded accuracy claim.
    assert s["quality"]["publication_eligible_accuracy"] == "not_measurable_without_ground_truth"


# --------------------------------------------------------------------------- #
# 8. Compatibility with WORKERS-002 / WORKERS-003 contracts.
# --------------------------------------------------------------------------- #

def test_compat_workers_002_003_contract_versions(monkeypatch, tmp_path):
    _authorize(monkeypatch)
    store = CP.PilotStore(root=tmp_path)
    classified = CP.classify_candidates(_candidates())
    report = CP.run_pilot(classified, CP.PilotCaps(max_assignments=1), live=True, store=store,
                          provider_factory=_fake_factory())
    h = report["hotels"][0]
    assert h["prompt_version"] == PROMPT_VERSION and h["validator_version"] == VALIDATOR_VERSION
    assert h["routing_envelope_id"].startswith("route:")
    env = store.root / "routing_envelopes" / (h["assignment_id"] + ".json")
    data = json.loads(env.read_text(encoding="utf-8"))
    assert data["routing_version"] == RT.ROUTING_VERSION
    assert data["worker_type"] == V.WORKER_TYPE_HOTEL_POLICY


# --------------------------------------------------------------------------- #
# 9. CLI: dry-run, report, live-airlock-block.
# --------------------------------------------------------------------------- #

def test_cli_dry_run_no_writes(tmp_path, capsys):
    rc = cli_main(["columbus-hotel-pilot", "--output-root", str(tmp_path)])
    assert rc == 0
    out = capsys.readouterr().out
    assert "hotels found               : 25" in out and "DRY RUN" in out
    assert not any(tmp_path.iterdir())


def test_cli_report_without_artifacts(tmp_path, capsys):
    rc = cli_main(["columbus-hotel-pilot", "--report", "--output-root", str(tmp_path)])
    assert rc == 4 and "no pilot artifacts found" in capsys.readouterr().out


def test_cli_live_blocks_without_confirm_spend(tmp_path):
    # --live without --confirm-spend is refused by the airlock (exit 3).
    rc = cli_main(["columbus-hotel-pilot", "--live", "--output-root", str(tmp_path)])
    assert rc == 3
    assert not (tmp_path / "assignments").exists()
