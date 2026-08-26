"""PTF-MARKET-FACTORY-COVERAGE-HARDENING-001 -- the generic market lifecycle, sequenced.

    python scripts/pettripfinder/market_factory_cli.py \
      --market <id> --contract launch_packages/pettripfinder/markets/pending/<id>.json \
      --candidates data/discovery/<id>/candidates/<id>_candidates.json \
      --authorised-cap-usd 10 --work-order PTF-<MARKET>-001 --as-of 2026-08-25 \
      --through founder_review [--authorise-spend]

    python scripts/pettripfinder/market_factory_cli.py --market <id> ... --plan

WHY THIS FILE EXISTS
--------------------
St. Louis was built on the generic path and still needed a second work order to
raise its coverage. Louisville was built on the generic path after that, and
needed one too. Both times the tools existed -- URL recovery, declined-evidence
recovery, the merge, the cost plan, the retry classification -- and both times
a person had to remember to run them, in the right order, with the right
inputs, before handing the founder a packet. This module is that memory. It
sequences the tools that already exist; it adds no tool of its own, and it
knows nothing about any city.

THE LIFECYCLE
-------------
    1  census                        market_census_cli over persisted discovery
    2  routing                       market_routing over the census
    3  zero_cost_url_recovery        census_url_recovery over the discovery cache
    4  prior_build_reconciliation    census_url_recovery over a prior build
    5  reroute                       routing again, with the recovered URLs
    6  acquisition                   dry run -> cost plan -> GATE -> paid pass
    7  declined_evidence_recovery    zero_cost_recovery over every run directory
    8  reroute_recovered             URL recovery again over this build's own
                                     artifacts, then routing again
    9  acquire_newly_routable        the same paid machinery over what is left
   10  alternate_lane_handling       retry policy: what may run on an untried
                                     approved lane, what is terminal
   11  coverage_exhaustion           the coverage-completion artifact
   12  closure                       merge, store, partition, closure ledger
   13  founder_review_packet         packet, machine review, duplicate scan
   14  founder_review                a human; refused until 11-13 say READY

A phase is never re-run by accident: the ledger records each phase's status and
artifacts, a completed phase is skipped on the next invocation, and a phase
whose predecessor did not complete is not started. Every gate is a check on an
ARTIFACT, never on a flag someone set.

WHAT COSTS MONEY
----------------
Phases 6, 9 and 10 can spend. Without ``--authorise-spend`` each of them runs
its dry run and writes its cost plan, then stops at AWAITING_AUTHORISATION with
the plan in hand -- so the operator authorises a number they have seen. With
it, the paid pass runs under the plan's recommended cap and its own gate checks
that the plan describes the queue about to run. Nothing else here spends.
"""

from __future__ import annotations

import argparse
import json
import shutil
import sys
from collections import OrderedDict
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Callable, Dict, List, Mapping, Optional, Sequence, Tuple

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder import census_partition_builder as CPB
from scripts.pettripfinder import market_coverage_cli as MC
from scripts.pettripfinder.acquisition import market_paid_acquisition as PA
from scripts.pettripfinder.acquisition import market_routing as MR
from scripts.pettripfinder.acquisition import retry_policy as RP
from scripts.pettripfinder.contracts import coverage as COV

PACKAGE_DIR = _REPO_ROOT / "launch_packages" / "pettripfinder"
CENSUS_DIR = PACKAGE_DIR / "identity_census"
MARKETS_DIR = PACKAGE_DIR / "markets"

LEDGER_SCHEMA = "ptf-market-factory-ledger/1.0"

# Phase names, in lifecycle order. The order IS the contract.
CENSUS = "census"
ROUTING = "routing"
ZERO_COST_URL_RECOVERY = "zero_cost_url_recovery"
PRIOR_BUILD_RECONCILIATION = "prior_build_reconciliation"
REROUTE = "reroute"
PRE_ACQUISITION_DEDUP = "pre_acquisition_dedup"
ACQUISITION = "acquisition"
DECLINED_EVIDENCE_RECOVERY = "declined_evidence_recovery"
REROUTE_RECOVERED = "reroute_recovered"
ACQUIRE_NEWLY_ROUTABLE = "acquire_newly_routable"
ALTERNATE_LANE_HANDLING = "alternate_lane_handling"
COVERAGE_EXHAUSTION = "coverage_exhaustion"
CLOSURE = "closure"
FOUNDER_REVIEW_PACKET = "founder_review_packet"
FOUNDER_REVIEW = "founder_review"

PHASES: Tuple[str, ...] = (
    CENSUS, ROUTING, ZERO_COST_URL_RECOVERY, PRIOR_BUILD_RECONCILIATION,
    REROUTE, PRE_ACQUISITION_DEDUP, ACQUISITION,
    DECLINED_EVIDENCE_RECOVERY, REROUTE_RECOVERED,
    ACQUIRE_NEWLY_ROUTABLE, ALTERNATE_LANE_HANDLING, COVERAGE_EXHAUSTION,
    CLOSURE, FOUNDER_REVIEW_PACKET, FOUNDER_REVIEW,
)

#: Phases that may spend provider money. Each one is gated on a cost plan and
#: on ``--authorise-spend``; a test asserts the set.
PAID_PHASES = frozenset({ACQUISITION, ACQUIRE_NEWLY_ROUTABLE,
                         ALTERNATE_LANE_HANDLING})

# Phase statuses.
COMPLETED = "COMPLETED"
SKIPPED = "SKIPPED"
BLOCKED = "BLOCKED"
AWAITING_AUTHORISATION = "AWAITING_AUTHORISATION"
AWAITING_HUMAN = "AWAITING_HUMAN"
NOT_RUN = "NOT_RUN"

#: Statuses that let the next phase start.
SATISFIED = frozenset({COMPLETED, SKIPPED})

#: The generic improvements this factory is required to carry, each named by the
#: module and symbol that implements it. Kept as data so a test can prove every
#: one still exists -- and so nobody duplicates a module that is already here.
HARDENED_BASELINE: Tuple[Tuple[str, str, str], ...] = (
    ("durable paid-acquisition journal/resume",
     "scripts.pettripfinder.acquisition.journal", "Journal"),
    ("cumulative budget accounting",
     "scripts.pettripfinder.acquisition.market_paid_acquisition", "preflight"),
    ("calibrated vendor cost / headroom reservation",
     "scripts.pettripfinder.acquisition.market_paid_acquisition", "SpendMeter"),
    ("multi-pass acquisition merge",
     "scripts.pettripfinder.acquisition.acquisition_merge", "merge"),
    ("declined-document persistence",
     "scripts.pettripfinder.brightdata.declined_capture", "read"),
    ("URL recovery",
     "scripts.pettripfinder.discovery.census_url_recovery", "recover"),
    ("category/index URL rejection",
     "scripts.pettripfinder.acquisition.market_routing", "classify_url_shape"),
    ("shared source URL detection",
     "scripts.pettripfinder.acquisition.market_routing",
     "urls_claimed_more_than_once"),
    ("founder review against persisted source blocks",
     "scripts.pettripfinder.founder_review_analysis", "policy_block_text"),
    ("duplicate scan before publication",
     "scripts.pettripfinder.discovery.census_duplicate_scan", "scan"),
    ("improved identity normalization",
     "scripts.pettripfinder.discovery.census_projection",
     "resolve_identity_key_collisions"),
    ("service-animal exemption semantics",
     "scripts.pettripfinder.contracts.service_animal", "EXEMPT_FROM_PET_CHARGE"),
    ("source-vs-record contradiction checks",
     "scripts.pettripfinder.founder_review_analysis", "review_all"),
    ("versioned FLAG_CODES",
     "scripts.pettripfinder.policy.policy_observation", "FLAG_CODES"),
    ("publication policy schema 1.3 compatibility",
     "scripts.pettripfinder.contracts.enums", "POLICY_SCHEMA_VERSION"),
    ("corrected deposit/fee distinction",
     "scripts.pettripfinder.contracts.enums", "CHARGE_REFUNDABLE_DEPOSIT"),
    ("implausible weight withholding",
     "scripts.pettripfinder.brightdata.policy_reading", "parse"),
    ("contradictory fee-basis handling",
     "scripts.pettripfinder.fee_forms", "competing_recurrence"),
    ("explicit pet allowance from stated species acceptance",
     "scripts.pettripfinder.brightdata.policy_reading", "parse"),
    ("canonical-name overlays",
     "scripts.pettripfinder.acquisition.market_observation_store", "build"),
    ("zero-cost declined-evidence recovery",
     "scripts.pettripfinder.acquisition.zero_cost_recovery", "run"),
    ("pre-spend cohort cost plan",
     "scripts.pettripfinder.acquisition.cohort_cost_plan", "build"),
    ("same-lane retry suppression",
     "scripts.pettripfinder.acquisition.retry_policy", "apply"),
    ("coverage-completion contract",
     "scripts.pettripfinder.contracts.coverage", "document"),
)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# --------------------------------------------------------------------------- #
# Context and ledger
# --------------------------------------------------------------------------- #

@dataclass
class FactoryContext:
    """Everything a new market needs: an id, a geography, a budget."""

    market_id: str
    work_order: str
    as_of: str
    contract_path: Optional[Path] = None
    candidates_path: Optional[Path] = None
    discovery_cache: Optional[Path] = None
    prior_census: Optional[Path] = None
    prior_artifacts: Tuple[str, ...] = ()
    authorised_cap_usd: float = 0.0
    credit_cap: Optional[int] = None
    spend_authorised: bool = False
    retry_overrides: Optional[Path] = None
    reviewer: str = "market_factory_cli (machine review)"
    suffix: str = "001"
    package_dir: Path = PACKAGE_DIR
    census_dir: Path = CENSUS_DIR
    markets_dir: Path = MARKETS_DIR
    run_root: Optional[Path] = None

    def __post_init__(self) -> None:
        if self.run_root is None:
            self.run_root = (_REPO_ROOT / "data" / "acquisition"
                             / ("%s_factory_%s" % (self.slug, self.suffix)))

    @property
    def slug(self) -> str:
        return self.market_id.replace("-", "_")

    def artifact(self, name: str) -> Path:
        return self.package_dir / ("%s_%s_%s.json" % (self.slug, name, self.suffix))

    @property
    def census_path(self) -> Path:
        return self.census_dir / ("%s.json" % self.market_id)

    @property
    def ledger_path(self) -> Path:
        return self.artifact("factory_ledger")

    def optional_overlay(self, kind: str) -> str:
        """``markets/<kind>/<market>.json`` when it exists, else ''."""
        path = self.markets_dir / kind / ("%s.json" % self.market_id)
        return path.as_posix() if path.is_file() else ""


@dataclass
class PhaseResult:
    status: str
    note: str = ""
    artifacts: Dict[str, str] = field(default_factory=OrderedDict)
    facts: Dict = field(default_factory=OrderedDict)


def _sha(path: Path) -> str:
    import hashlib
    return hashlib.sha256(path.read_bytes()).hexdigest() if path.is_file() else ""


def load_ledger(ctx: FactoryContext) -> Dict:
    if ctx.ledger_path.is_file():
        return json.loads(ctx.ledger_path.read_text(encoding="utf-8"))
    return OrderedDict((
        ("schema", LEDGER_SCHEMA),
        ("what_this_is",
         "The durable record of which lifecycle phases have run for this "
         "market, with the artifacts each produced. A phase recorded here as "
         "COMPLETED or SKIPPED is not run again; a phase whose predecessor is "
         "not satisfied is not started."),
        ("market_id", ctx.market_id),
        ("work_order", ctx.work_order),
        ("suffix", ctx.suffix),
        ("lifecycle", list(PHASES)),
        ("paid_phases", sorted(PAID_PHASES)),
        ("passes", []),
        ("phases", OrderedDict((name, OrderedDict((("status", NOT_RUN),)))
                               for name in PHASES)),
    ))


def save_ledger(ctx: FactoryContext, ledger: Mapping) -> str:
    return CPB.write_json(ctx.ledger_path, ledger)


def record(ledger: Dict, phase: str, result: PhaseResult) -> None:
    entry = OrderedDict((
        ("status", result.status),
        ("ran_at", _now()),
        ("note", result.note),
        ("artifacts", OrderedDict(
            (name, OrderedDict((("path", Path(p).as_posix()),
                                ("sha256", _sha(Path(p))))))
            for name, p in result.artifacts.items())),
        ("facts", result.facts),
    ))
    ledger["phases"][phase] = entry


def phase_artifact(ledger: Mapping, phase: str, name: str) -> str:
    return str(((ledger.get("phases") or {}).get(phase) or {})
               .get("artifacts", {}).get(name, {}).get("path") or "")


def status_of(ledger: Mapping, phase: str) -> str:
    return str(((ledger.get("phases") or {}).get(phase) or {})
               .get("status") or NOT_RUN)


# --------------------------------------------------------------------------- #
# Helpers shared by phases
# --------------------------------------------------------------------------- #

def _call(main: Callable[..., int], argv: Sequence[str]) -> Tuple[int, str]:
    """Run a tool's ``main`` in-process; a SystemExit is an answer, not a crash."""
    try:
        code = main(list(argv))
    except SystemExit as exc:                         # argparse or the tool
        code = exc.code if isinstance(exc.code, int) else 1
        return (code, str(exc))
    return (int(code or 0), "")


def _read(path: str) -> Dict:
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def _write(path: Path, document: Mapping) -> str:
    return CPB.write_json(path, document)


def _routing_document(ctx: FactoryContext, *, overlay_path: str, name: str,
                      phase_note: str) -> PhaseResult:
    census = _read(ctx.census_path.as_posix())
    overlay = MR.apply_url_overlay(census["hotels"], overlay_path)
    entries, summary = MR.route_census(census["hotels"])
    shared = MR.urls_claimed_more_than_once(entries)
    out = ctx.artifact(name)
    _write(out, OrderedDict((
        ("schema", MR.CONTRACT),
        ("what_this_is", phase_note),
        ("market_id", ctx.market_id),
        ("work_order", ctx.work_order),
        ("url_overlay", overlay),
        ("summary", summary),
        ("urls_claimed_more_than_once", shared),
        ("entries", entries),
    )))
    return PhaseResult(
        COMPLETED, "%s: ROUTED %d of %d (%s%%), overlay applied %d, shared "
        "URLs %d" % (name, summary["automatically_routed"], summary["count"],
                     summary["automatically_routed_pct"], overlay["applied"],
                     len(shared)),
        artifacts=OrderedDict(((name, out.as_posix()),)),
        facts=OrderedDict((("routed", summary["automatically_routed"]),
                           ("census", summary["count"]),
                           ("overlay_applied", overlay["applied"]),
                           ("overlay_rows", [r["identity_key"]
                                             for r in overlay.get("rows") or ()]),
                           ("shared_urls", len(shared)))))


def _empty_recovery_document(ctx: FactoryContext, why: str) -> Dict:
    """A full-strength URL recovery over NO evidence, said honestly.

    The flags record what was OFFERED -- three keys, corroboration, unroutable
    census URLs included -- and the counts record that nothing was there to
    read. A coverage evaluation reads both and concludes correctly that the
    factory asked, and that there was nothing to ask.
    """
    census = _read(ctx.census_path.as_posix())
    entries, _summary = MR.route_census(census["hotels"])
    unrouted = [e for e in entries if e["routing_state"] != MR.ROUTED]
    return OrderedDict((
        ("schema", "ptf-census-url-recovery/1.0"),
        ("what_this_is", "A URL recovery pass that found no evidence on disk "
                         "to read: %s. Zero network, zero spend." % why),
        ("market_id", ctx.market_id),
        ("work_order", ctx.work_order),
        ("cache_dir", ""), ("prior_census", ""),
        ("evidence_families", OrderedDict()),
        ("binding_keys_offered", ["PHONE", "NAME_AND_POSTAL_CODE",
                                  "STREET_AND_POSTAL_CODE"]),
        ("url_corroboration_required", True),
        ("unroutable_census_urls_included", True),
        ("displacements_proposed", 0),
        ("cached_sightings_with_a_url", 0),
        ("rows_without_a_usable_url_before", len(unrouted)),
        ("recovered", 0), ("routable_recoveries", 0),
        ("still_unknown", len(unrouted)),
        ("binding_counts", OrderedDict()),
        ("recovered_by_provider", OrderedDict()),
        ("recovered_url_shapes", OrderedDict()),
        ("artifact_coverage", OrderedDict()),
        ("recoveries", []),
        ("still_unknown_rows", [OrderedDict((
            ("identity_key", e["identity_key"]),
            ("canonical_name", e["canonical_name"]),
            ("why", "no evidence on disk to read"))) for e in unrouted]),
    ))


def _url_recovery(ctx: FactoryContext, *, out: Path, cache: Optional[Path],
                  prior_census: Optional[Path], artifacts: Sequence[str],
                  work_order: str) -> Tuple[int, str]:
    from scripts.pettripfinder.discovery import census_url_recovery as CUR
    argv: List[str] = ["--market", ctx.market_id, "--out", out.as_posix(),
                       "--census", ctx.census_path.as_posix(),
                       "--work-order", work_order, "--allow-street-binding",
                       "--corroborate-url", "--include-unroutable"]
    if cache is not None and Path(cache).is_dir():
        argv += ["--cache", Path(cache).as_posix()]
    if prior_census is not None and Path(prior_census).is_file():
        argv += ["--prior-census", Path(prior_census).as_posix()]
        for pattern in artifacts:
            argv += ["--artifact", pattern]
    if "--cache" not in argv and "--prior-census" not in argv:
        _write(out, _empty_recovery_document(
            ctx, "no discovery cache and no prior census were available"))
        return (0, "no evidence on disk; wrote an honest empty recovery")
    return _call(CUR.main, argv)


def _pass_reports(ledger: Mapping) -> List[Dict]:
    return list(ledger.get("passes") or ())


def _merged_prior(ctx: FactoryContext, ledger: Mapping, name: str) -> str:
    """Fold every paid pass so far into one prior view, or write an empty one."""
    from scripts.pettripfinder.acquisition import acquisition_merge as AM
    out = ctx.artifact(name)
    passes = _pass_reports(ledger)
    if not passes:
        _write(out, OrderedDict((
            ("schema", AM.SCHEMA),
            ("what_this_is", "No acquisition pass has run for this market yet; "
                             "an empty prior so the first cohort is the whole "
                             "routed population."),
            ("market_id", ctx.market_id), ("work_order", ctx.work_order),
            ("passes", []), ("identities", 0), ("provider", ""),
            ("lanes", []), ("attempted", 0), ("valid", 0),
            ("outcome_counts", OrderedDict()), ("outcomes_by_brand", OrderedDict()),
            ("lane_refused_brands", OrderedDict()), ("skipped_lane_refused", []),
            ("rows_by_pass", OrderedDict()), ("superseded", []), ("results", []),
        )))
        return out.as_posix()
    argv = ["--market", ctx.market_id, "--work-order", ctx.work_order,
            "--out", out.as_posix()]
    for entry in passes:
        argv += ["--pass", entry["report"]]
    code, message = _call(AM.main, argv)
    if code != 0:
        raise RuntimeError("acquisition merge failed: %s" % message)
    return out.as_posix()


def _paid_pass(ctx: FactoryContext, ledger: Dict, *, label: str,
               overlay_path: str) -> PhaseResult:
    """Dry run -> cost plan -> gate -> (authorised) paid pass. Shared by every
    phase that can spend, so there is exactly one way money leaves."""
    from scripts.pettripfinder.acquisition import cohort_cost_plan as CP
    prior = _merged_prior(ctx, ledger, "acquisition_merged_%s" % label)
    run_dir = Path(ctx.run_root) / label
    run_id = "%s-%s-%s" % (ctx.market_id, ctx.suffix, label)
    dry = ctx.artifact("acquisition_dry_run_%s" % label)
    plan = ctx.artifact("cohort_cost_plan_%s" % label)
    base = ["--market", ctx.market_id, "--prior", prior,
            "--census", ctx.census_path.as_posix(),
            "--run-dir", run_dir.as_posix(), "--run-id", run_id,
            "--work-order", ctx.work_order, "--url-overlay", overlay_path]
    if ctx.retry_overrides:
        base += ["--retry-overrides", Path(ctx.retry_overrides).as_posix()]
    if ctx.credit_cap is not None:
        base += ["--credit-cap", str(ctx.credit_cap)]
    # The pre-acquisition duplicate gate's decision, spent here. Passed only
    # when the gate has run, so a market that predates it buys what it always
    # bought.
    dedup_plan = phase_artifact(ledger, PRE_ACQUISITION_DEDUP,
                                "pre_acquisition_dedup")
    if dedup_plan:
        base += ["--dedup-plan", dedup_plan]

    code, message = _call(PA.main, base + ["--cap-usd", str(ctx.authorised_cap_usd),
                                            "--out", dry.as_posix(), "--dry-run"])
    if code != 0:
        return PhaseResult(BLOCKED, "dry run failed: %s" % message)
    dry_doc = _read(dry.as_posix())
    artifacts = OrderedDict((("dry_run", dry.as_posix()), ("prior", prior)))
    if not dry_doc.get("cohort"):
        return PhaseResult(
            SKIPPED, "nothing to acquire: cohort is empty (settled %d, "
            "suppressed same-lane %d)" % (dry_doc.get("settled_size", 0),
                                          dry_doc.get("suppressed_size", 0)),
            artifacts=artifacts,
            facts=OrderedDict((("cohort", 0),
                               ("suppressed_same_lane",
                                dry_doc.get("suppressed_size", 0)))))

    plan_argv = ["--plan", dry.as_posix(), "--prior", prior,
                 "--authorised-cap-usd", str(ctx.authorised_cap_usd),
                 "--journal", (run_dir / "journal.jsonl").as_posix(),
                 "--out", plan.as_posix()]
    if ctx.credit_cap is not None:
        plan_argv += ["--credit-cap", str(ctx.credit_cap)]
    for entry in _pass_reports(ledger):
        plan_argv += ["--previous-pass", entry["report"]]
    code, message = _call(CP.main, plan_argv)
    artifacts["cost_plan"] = plan.as_posix()
    if code != 0:
        return PhaseResult(BLOCKED, "cost plan refused the cohort: a property "
                           "a prior pass already answered, or already "
                           "journalled, is in it (%s)" % (message or plan.name),
                           artifacts=artifacts)
    plan_doc = _read(plan.as_posix())
    facts = OrderedDict((
        ("cohort", dry_doc.get("cohort_size", 0)),
        ("suppressed_same_lane", dry_doc.get("suppressed_size", 0)),
        ("recommended_cap_usd_minor", plan_doc.get("recommended_cap_usd_minor")),
        ("predicted_attemptable",
         (plan_doc.get("predicted_completion_under_balance") or {}).get("attemptable")),
        ("no_property_is_bought_twice",
         (plan_doc.get("double_buy_check") or {}).get("no_property_is_bought_twice")),
    ))
    if not ctx.spend_authorised:
        return PhaseResult(
            AWAITING_AUTHORISATION,
            "cost plan written; re-run with --authorise-spend to run the paid "
            "pass under the plan's recommended cap (%s cents)"
            % plan_doc.get("recommended_cap_usd_minor"),
            artifacts=artifacts, facts=facts)

    cap_usd = float(plan_doc.get("recommended_cap_usd_minor") or 0) / 100.0
    report = ctx.artifact("market_acquisition_%s" % label)
    code, message = _call(PA.main, base + ["--cap-usd", "%.2f" % cap_usd,
                                            "--cost-plan", plan.as_posix(),
                                            "--out", report.as_posix()])
    artifacts["report"] = report.as_posix()
    if code != 0:
        return PhaseResult(BLOCKED, "paid pass failed: %s" % message,
                           artifacts=artifacts, facts=facts)
    report_doc = _read(report.as_posix())
    if report_doc.get("outcome") == "STOPPED_BEFORE_SPENDING":
        return PhaseResult(BLOCKED, "paid pass stopped before spending: %s"
                           % report_doc.get("stop_reason", ""),
                           artifacts=artifacts, facts=facts)
    ledger.setdefault("passes", []).append(OrderedDict((
        ("label", label), ("report", report.as_posix()),
        ("run_dir", run_dir.as_posix()), ("run_id", run_id),
        ("outcome", report_doc.get("outcome", "")),
        ("attempted", report_doc.get("attempted", 0)),
    )))
    facts.update(OrderedDict((
        ("outcome", report_doc.get("outcome", "")),
        ("attempted", report_doc.get("attempted", 0)),
        ("deferred", len(report_doc.get("deferred") or ())),
        ("spend_usd_minor", (report_doc.get("spend") or {}).get("binding_usd_minor")),
    )))
    return PhaseResult(COMPLETED, "paid pass %s: %s, attempted %s"
                       % (label, report_doc.get("outcome"),
                          report_doc.get("attempted")),
                       artifacts=artifacts, facts=facts)


def _coverage(ctx: FactoryContext, ledger: Mapping, *, stage: str) -> PhaseResult:
    passes = _pass_reports(ledger)
    last = passes[-1]["report"] if passes else ""
    merged = (phase_artifact(ledger, CLOSURE, "merged")
              or (ctx.artifact("acquisition_merged_closeout").as_posix()
                  if ctx.artifact("acquisition_merged_closeout").is_file() else "")
              or _merged_prior(ctx, dict(ledger), "acquisition_merged_coverage"))
    out = ctx.artifact("coverage_completion")
    document = MC.build_from_paths(
        market_id=ctx.market_id,
        url_overlay=phase_artifact(ledger, REROUTE_RECOVERED, "url_recovery")
        or phase_artifact(ledger, PRIOR_BUILD_RECONCILIATION, "url_recovery"),
        acquisition=merged, last_pass=last,
        closure=phase_artifact(ledger, CLOSURE, "closure_ledger"),
        packet=phase_artifact(ledger, FOUNDER_REVIEW_PACKET, "packet"),
        observations=phase_artifact(ledger, CLOSURE, "observation_store"),
        url_recovery=phase_artifact(ledger, REROUTE_RECOVERED, "url_recovery")
        or phase_artifact(ledger, PRIOR_BUILD_RECONCILIATION, "url_recovery"),
        declined_recovery=phase_artifact(ledger, DECLINED_EVIDENCE_RECOVERY,
                                         "declined_recovery"),
        recovery_after_last_pass=recovery_ran_after_acquisition(ledger),
        pass_run_dirs=[p["run_dir"] for p in passes],
        retry_overrides=(Path(ctx.retry_overrides).as_posix()
                         if ctx.retry_overrides else ""),
        stage=stage, work_order=ctx.work_order, as_of=ctx.as_of,
        census_path=ctx.census_path)
    _write(out, document)
    counts = document["counts"]
    booleans = document["booleans"]
    return PhaseResult(
        COMPLETED, "coverage (%s): census %d routed %d attempted %d settled %d "
        "candidates %d; READY_FOR_FOUNDER_REVIEW=%s, movable=%d"
        % (stage, counts["CENSUS"], counts["ROUTED"], counts["ATTEMPTED"],
           counts["SETTLED"], counts["FOUNDER_CANDIDATES"],
           booleans["READY_FOR_FOUNDER_REVIEW"],
           len(document["identities_the_factory_can_still_move"])),
        artifacts=OrderedDict((("coverage", out.as_posix()),)),
        facts=OrderedDict((("counts", counts), ("booleans", booleans),
                           ("benchmark", document["benchmark"]))))


def recovery_ran_after_acquisition(ledger: Mapping) -> bool:
    """Did the post-acquisition URL recovery (phase 8) run over the first paid
    pass's evidence? Vacuously true before any pass has run.

    Passes 2 and 3 run AFTER phase 8, over cohorts phase 8's recovery already
    informed, and produce no new evidence family -- the lifecycle asks for the
    recovery to run again "after the first acquisition/decline pass", and that
    is what phase 8 is.
    """
    if not _pass_reports(ledger):
        return True
    return status_of(ledger, REROUTE_RECOVERED) in SATISFIED


# --------------------------------------------------------------------------- #
# The phases
# --------------------------------------------------------------------------- #

def discovery_gate(ctx: FactoryContext) -> Tuple[Optional[Dict], str]:
    """PTF-DISCOVERY-OVERPASS-RESILIENCE-001: is free discovery finished?

    Returns ``(discovery_state_document, blocking_reason)``. A census is built
    only from a plan whose every Overpass cell is cached. Cells remaining with
    an approved endpoint available is a run the factory owes; cells remaining
    with none available is WAITING_FOR_FREE_DISCOVERY -- and neither is a
    partial census quietly called complete. No discovery cache at all means
    the state cannot be evaluated, and that is said rather than assumed.
    """
    from scripts.pettripfinder.discovery import discovery_state as DS
    from scripts.pettripfinder.discovery import overpass_endpoints as OE
    cache_root = Path(ctx.discovery_cache) if ctx.discovery_cache else None
    if cache_root is None or not cache_root.is_dir():
        return (None, "no discovery cache at %s; the free-discovery state "
                      "cannot be evaluated, so a census cannot be called complete"
                % (cache_root.as_posix() if cache_root else "(unset)"))
    try:
        document = DS.build(
            ctx.market_id, cache_root=cache_root,
            health_ledger_path=cache_root.parent / OE.HEALTH_LEDGER_FILENAME,
            as_of=ctx.as_of)
    except KeyError as exc:
        return (None, "no discovery geography for %s (%s); the market's "
                      "discovery config is missing" % (ctx.market_id, exc))
    out = ctx.artifact("discovery_state")
    DS.write(document, out)
    document["_artifact"] = out.as_posix()
    if document["state"] == DS.EXHAUSTED:
        return (document, "")
    if document["state"] == DS.WAITING:
        return (document, "%s: %d of %d Overpass cells cached, %d remaining; %s "
                          "(earliest cooldown ends %s); paid fallback %s and NOT "
                          "authorised"
                % (DS.WAITING, document["OVERPASS_CELLS_CACHED"],
                   document["OVERPASS_CELLS_TOTAL"],
                   document["OVERPASS_CELLS_REMAINING"],
                   document.get("waiting_reason") or "no approved endpoint available",
                   document["earliest_cooldown_expiry"] or "unknown",
                   document["paid_discovery_fallback"]["state"]))
    return (document, "%s: %d of %d Overpass cells cached, %d remaining and an "
                      "approved endpoint is available (%s); run discovery before "
                      "building the census"
            % (DS.RUNNABLE, document["OVERPASS_CELLS_CACHED"],
               document["OVERPASS_CELLS_TOTAL"], document["OVERPASS_CELLS_REMAINING"],
               ", ".join(document["available_endpoint_ids"])))


def phase_census(ctx: FactoryContext, ledger: Dict) -> PhaseResult:
    from scripts.pettripfinder import market_census_cli as CENSUS_CLI
    if ctx.census_path.is_file() and ctx.candidates_path is None:
        return PhaseResult(SKIPPED, "census already exists at %s and no "
                           "--candidates were given; reusing it"
                           % ctx.census_path.as_posix(),
                           artifacts=OrderedDict((("census",
                                                   ctx.census_path.as_posix()),)))
    if ctx.candidates_path is None or not Path(ctx.candidates_path).is_file():
        return PhaseResult(BLOCKED, "no census exists and no persisted discovery "
                           "candidates were given; run discovery_cli under its "
                           "own capped budget, then pass --candidates")
    discovery, blocked = discovery_gate(ctx)
    discovery_artifacts = (OrderedDict((("discovery_state", discovery["_artifact"]),))
                           if discovery else OrderedDict())
    if blocked:
        return PhaseResult(BLOCKED, "free discovery is not exhausted: %s" % blocked,
                           artifacts=discovery_artifacts,
                           facts=OrderedDict((("discovery_state",
                                               (discovery or {}).get("state", "")),)))
    if ctx.contract_path is None or not Path(ctx.contract_path).is_file():
        return PhaseResult(BLOCKED, "--contract is required to build a census: "
                           "the market geography (corridors, postal codes)")
    ledger_out = ctx.artifact("candidate_ledger")
    argv = ["--market", ctx.market_id,
            "--candidates", Path(ctx.candidates_path).as_posix(),
            "--contract", Path(ctx.contract_path).as_posix(),
            "--observed-at", ctx.as_of, "--work-order", ctx.work_order,
            "--ledger-out", ledger_out.as_posix(),
            "--out", ctx.census_path.as_posix()]
    artifacts = OrderedDict((("census", ctx.census_path.as_posix()),
                             ("candidate_ledger", ledger_out.as_posix())))
    if ctx.prior_census is not None and Path(ctx.prior_census).is_file():
        # A prior census of this market is an INPUT to the new one, never its
        # ceiling: its rows go back in as candidates with every verdict dropped.
        absorptions = ctx.artifact("prior_census_absorptions")
        argv += ["--prior-census", Path(ctx.prior_census).as_posix(),
                 "--absorptions-out", absorptions.as_posix()]
        artifacts["prior_census_absorptions"] = absorptions.as_posix()
    code, message = _call(CENSUS_CLI.main, argv)
    if code != 0:
        return PhaseResult(BLOCKED, "census build failed: %s" % message)
    census = _read(ctx.census_path.as_posix())
    facts = OrderedDict((("census", census["count"]),))
    recandidacy = census.get("prior_census_recandidacy")
    if recandidacy:
        facts["prior_census"] = OrderedDict(
            (k, recandidacy.get(k)) for k in
            ("prior_rows", "fresh_candidates", "absorbed_into_fresh_candidates",
             "prior_rows_surviving_as_candidates", "merged_candidates"))
    facts["discovery_state"] = discovery["state"]
    facts["overpass_cells_total"] = discovery["OVERPASS_CELLS_TOTAL"]
    artifacts.update(discovery_artifacts)
    return PhaseResult(COMPLETED, "census built: %d identities; free discovery "
                       "exhausted over %d Overpass cells"
                       % (census["count"], discovery["OVERPASS_CELLS_TOTAL"]),
                       artifacts=artifacts, facts=facts)


def phase_routing(ctx: FactoryContext, ledger: Dict) -> PhaseResult:
    return _routing_document(ctx, overlay_path="", name="routing",
                             phase_note="Routing over the census as discovered, "
                                        "before any URL recovery.")


def phase_zero_cost_url_recovery(ctx: FactoryContext, ledger: Dict) -> PhaseResult:
    out = ctx.artifact("url_recovery_cache")
    code, message = _url_recovery(ctx, out=out, cache=ctx.discovery_cache,
                                  prior_census=None, artifacts=(),
                                  work_order=ctx.work_order)
    if code != 0:
        return PhaseResult(BLOCKED, "URL recovery failed: %s" % message)
    doc = _read(out.as_posix())
    return PhaseResult(COMPLETED, "cache recovery: %d recovered, %d still unknown"
                       % (doc["recovered"], doc["still_unknown"]),
                       artifacts=OrderedDict((("url_recovery", out.as_posix()),)),
                       facts=OrderedDict((("recovered", doc["recovered"]),
                                          ("still_unknown", doc["still_unknown"]))))


def phase_prior_build_reconciliation(ctx: FactoryContext, ledger: Dict) -> PhaseResult:
    out = ctx.artifact("url_recovery")
    cache_report = phase_artifact(ledger, ZERO_COST_URL_RECOVERY, "url_recovery")
    if ctx.prior_census is None or not Path(ctx.prior_census).is_file():
        shutil.copyfile(cache_report, out)
        return PhaseResult(SKIPPED, "no prior build of this market on disk; the "
                           "cache recovery is the whole overlay",
                           artifacts=OrderedDict((("url_recovery", out.as_posix()),)))
    code, message = _url_recovery(ctx, out=out, cache=ctx.discovery_cache,
                                  prior_census=ctx.prior_census,
                                  artifacts=ctx.prior_artifacts,
                                  work_order=ctx.work_order)
    if code != 0:
        return PhaseResult(BLOCKED, "prior-build recovery failed: %s" % message)
    doc = _read(out.as_posix())
    return PhaseResult(COMPLETED, "prior-build reconciliation: %d recovered "
                       "(families %s), %d still unknown"
                       % (doc["recovered"], dict(doc["evidence_families"]),
                          doc["still_unknown"]),
                       artifacts=OrderedDict((("url_recovery", out.as_posix()),)),
                       facts=OrderedDict((("recovered", doc["recovered"]),
                                          ("still_unknown", doc["still_unknown"]))))


def phase_reroute(ctx: FactoryContext, ledger: Dict) -> PhaseResult:
    overlay = phase_artifact(ledger, PRIOR_BUILD_RECONCILIATION, "url_recovery")
    return _routing_document(ctx, overlay_path=overlay, name="routing_overlay",
                             phase_note="Routing with every zero-cost recovered "
                                        "URL layered over the census.")


def phase_pre_acquisition_dedup(ctx: FactoryContext, ledger: Dict) -> PhaseResult:
    """PTF-GENERIC-PRE-ACQUISITION-DEDUP-HARDENING-001 -- the spend gate.

    The closure duplicate scan (phase 13) reports too late to protect money:
    by then the duplicates have been bought. This runs the same signals AFTER
    routing and zero-cost recovery -- so it sees the final URLs -- and BEFORE
    the cost plan, and it produces three things a cost plan can act on: safe
    merges, duplicate holds, and the set of identity keys that may be paid for.

    It decides nothing about publication and removes nothing from the census.
    The later closure scan is untouched and still runs.
    """
    from scripts.pettripfinder.discovery import identity_dedup as DEDUP
    census = _read(ctx.census_path.as_posix())
    rows = census.get("hotels") or []
    analysis = DEDUP.analyse(rows)
    out = ctx.artifact("pre_acquisition_dedup")
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(analysis, indent=1) + "\n", encoding="utf-8")
    counts = analysis["groups_by_verdict"]
    return PhaseResult(
        COMPLETED,
        "pre-acquisition dedup: %d groups (%d safe-merge, %d review, %d "
        "distinct); %d merged, %d withheld from acquisition, %d payable"
        % (analysis["groups_found"], counts[DEDUP.MERGE], counts[DEDUP.REVIEW],
           counts[DEDUP.DISTINCT], analysis["merged_identities"],
           analysis["withheld_from_acquisition"],
           len(DEDUP.payable_keys(rows, analysis))),
        artifacts=OrderedDict((("pre_acquisition_dedup", out.as_posix()),)),
        facts=OrderedDict((
            ("identities_in", analysis["identities_in"]),
            ("groups_by_verdict", counts),
            ("merged_identities", analysis["merged_identities"]),
            ("withheld_from_acquisition", analysis["withheld_from_acquisition"]),
        )))


def phase_acquisition(ctx: FactoryContext, ledger: Dict) -> PhaseResult:
    overlay = phase_artifact(ledger, PRIOR_BUILD_RECONCILIATION, "url_recovery")
    return _paid_pass(ctx, ledger, label="pass1", overlay_path=overlay)


def phase_declined_evidence_recovery(ctx: FactoryContext, ledger: Dict) -> PhaseResult:
    from scripts.pettripfinder.acquisition import zero_cost_recovery as ZCR
    passes = _pass_reports(ledger)
    if not passes:
        return PhaseResult(SKIPPED, "no paid pass has run; there is no declined "
                           "evidence to re-read")
    out = ctx.artifact("zero_cost_recovery")
    argv = ["--market", ctx.market_id, "--work-order", ctx.work_order,
            "--out", out.as_posix()]
    for entry in passes:
        argv += ["--run-dir", entry["run_dir"]]
    code, message = _call(ZCR.main, argv)
    if code != 0:
        return PhaseResult(BLOCKED, "declined-evidence recovery failed: %s" % message)
    doc = _read(out.as_posix())
    return PhaseResult(COMPLETED, "declined evidence: %d examined, %s"
                       % (doc["examined"], dict(doc["verdict_counts"])),
                       artifacts=OrderedDict((("declined_recovery", out.as_posix()),)),
                       facts=OrderedDict((("examined", doc["examined"]),
                                          ("verdicts", doc["verdict_counts"]))))


def phase_reroute_recovered(ctx: FactoryContext, ledger: Dict) -> PhaseResult:
    """URL recovery again, over this build's own artifacts as well, then route."""
    out = ctx.artifact("url_recovery_post_acquisition")
    artifacts = list(ctx.prior_artifacts)
    for entry in _pass_reports(ledger):
        artifacts.append(entry["report"])
    declined = phase_artifact(ledger, DECLINED_EVIDENCE_RECOVERY, "declined_recovery")
    if declined:
        artifacts.append(declined)
    prior_census = (ctx.prior_census if ctx.prior_census
                    and Path(ctx.prior_census).is_file() else ctx.census_path)
    code, message = _url_recovery(ctx, out=out, cache=ctx.discovery_cache,
                                  prior_census=prior_census, artifacts=artifacts,
                                  work_order=ctx.work_order)
    if code != 0:
        return PhaseResult(BLOCKED, "post-acquisition URL recovery failed: %s"
                           % message)
    before = {r["identity_key"] for r in
              _read(phase_artifact(ledger, PRIOR_BUILD_RECONCILIATION,
                                   "url_recovery")).get("recoveries") or ()}
    doc = _read(out.as_posix())
    now = {r["identity_key"] for r in doc.get("recoveries") or ()}
    routing = _routing_document(
        ctx, overlay_path=out.as_posix(), name="routing_recovered",
        phase_note="Routing with the post-acquisition URL recovery layered over "
                   "the census.")
    routing.artifacts = OrderedDict((("url_recovery", out.as_posix()),)
                                    + tuple(routing.artifacts.items()))
    routing.facts["newly_recovered_after_acquisition"] = sorted(now - before)
    routing.note = ("post-acquisition recovery: %d newly recovered; %s"
                    % (len(now - before), routing.note))
    return routing


def phase_acquire_newly_routable(ctx: FactoryContext, ledger: Dict) -> PhaseResult:
    overlay = phase_artifact(ledger, REROUTE_RECOVERED, "url_recovery")
    return _paid_pass(ctx, ledger, label="pass2", overlay_path=overlay)


def phase_alternate_lane_handling(ctx: FactoryContext, ledger: Dict) -> PhaseResult:
    """Classify every unsettled routed row; run the alternates that remain."""
    overlay = phase_artifact(ledger, REROUTE_RECOVERED, "url_recovery")
    prior_path = _merged_prior(ctx, ledger, "acquisition_merged_alternate")
    census = _read(ctx.census_path.as_posix())
    MR.apply_url_overlay(census["hotels"], overlay)
    entries, _summary = MR.route_census(census["hotels"])
    prior = _read(prior_path)
    overrides = (RP.load_overrides(Path(ctx.retry_overrides))
                 if ctx.retry_overrides else None)
    eligible, settled, suppressed = PA.plan_cohort(entries, prior,
                                                   overrides=overrides)
    alternates = [r for r in eligible
                  if r.get("retry_classification") == RP.RETRY_ALLOWED_ALTERNATE_LANE]
    out = ctx.artifact("alternate_lane")
    _write(out, OrderedDict((
        ("schema", RP.SCHEMA),
        ("what_this_is", "Every routed, unsettled identity classified by the "
                         "retry policy: which may still run on an approved lane "
                         "the prior attempt never tried, and which are terminal "
                         "for the factory (RETRY_REQUIRES_ALTERNATE_LANE)."),
        ("market_id", ctx.market_id), ("work_order", ctx.work_order),
        ("retry_policy", RP.summary(eligible, suppressed)),
        ("alternate_lane_eligible", alternates),
        ("terminal_requires_alternate_lane", suppressed),
    )))
    facts = OrderedDict((("alternate_lane_eligible", len(alternates)),
                         ("requires_alternate_lane", len(suppressed)),
                         ("eligible_total", len(eligible))))
    if not eligible:
        return PhaseResult(SKIPPED, "no routed identity is eligible for another "
                           "attempt; %d are terminal RETRY_REQUIRES_ALTERNATE_LANE"
                           % len(suppressed),
                           artifacts=OrderedDict((("alternate_lane", out.as_posix()),)),
                           facts=facts)
    result = _paid_pass(ctx, ledger, label="pass3", overlay_path=overlay)
    result.artifacts = OrderedDict((("alternate_lane", out.as_posix()),)
                                   + tuple(result.artifacts.items()))
    result.facts.update(facts)
    return result


def phase_coverage_exhaustion(ctx: FactoryContext, ledger: Dict) -> PhaseResult:
    return _coverage(ctx, ledger, stage=MC.STAGE_COVERAGE_EXHAUSTION)


def phase_closure(ctx: FactoryContext, ledger: Dict) -> PhaseResult:
    from scripts.pettripfinder import market_closure_cli as CLOSURE_CLI
    from scripts.pettripfinder.acquisition import market_observation_store as MOS
    overlay = (phase_artifact(ledger, REROUTE_RECOVERED, "url_recovery")
               or phase_artifact(ledger, PRIOR_BUILD_RECONCILIATION, "url_recovery"))
    merged = _merged_prior(ctx, ledger, "acquisition_merged_closeout")
    store = ctx.artifact("observation_store")
    argv = ["--pilot", merged, "--census", ctx.census_path.as_posix(),
            "--run-id", "%s-%s" % (ctx.market_id, ctx.suffix),
            "--out", store.as_posix()]
    corrections = ctx.optional_overlay("name_corrections")
    if corrections:
        argv += ["--name-corrections", corrections]
    founder_overrides = ctx.optional_overlay("founder_overrides")
    if founder_overrides:
        argv += ["--founder-overrides", founder_overrides]
    code, message = _call(MOS.main, argv)
    if code != 0:
        return PhaseResult(BLOCKED, "observation store failed: %s" % message)
    partition = ctx.artifact("final_partition")
    closure = ctx.artifact("closure_ledger")
    code, message = _call(CLOSURE_CLI.main, [
        "--market", ctx.market_id, "--observations", store.as_posix(),
        "--census", ctx.census_path.as_posix(),
        "--pilot", merged, "--as-of", ctx.as_of, "--work-order", ctx.work_order,
        "--url-overlay", overlay, "--partition-out", partition.as_posix(),
        "--closure-out", closure.as_posix()])
    if code != 0:
        return PhaseResult(BLOCKED, "closure failed: %s" % message)
    ledger["phases"][CLOSURE] = OrderedDict((
        ("status", COMPLETED),
        ("artifacts", OrderedDict((
            ("merged", OrderedDict((("path", merged),))),
            ("observation_store", OrderedDict((("path", store.as_posix()),))),
            ("closure_ledger", OrderedDict((("path", closure.as_posix()),))),
        ))),
    ))
    coverage = _coverage(ctx, ledger, stage=MC.STAGE_CLOSURE)
    closure_doc = _read(closure.as_posix())
    return PhaseResult(
        COMPLETED, "closure %d/%d reconciled (missing %d foreign %d duplicate "
        "%d); %s" % (closure_doc["count"], closure_doc["active_denominator"],
                     len(closure_doc["reconciliation"]["missing"]),
                     len(closure_doc["reconciliation"]["foreign"]),
                     len(closure_doc["reconciliation"]["duplicate"]),
                     coverage.note),
        artifacts=OrderedDict((("merged", merged),
                               ("observation_store", store.as_posix()),
                               ("final_partition", partition.as_posix()),
                               ("closure_ledger", closure.as_posix()))
                              + tuple(coverage.artifacts.items())),
        facts=OrderedDict((("dispositions", closure_doc["disposition_counts"]),
                           ("reconciliation", closure_doc["reconciliation"]))
                          + tuple(coverage.facts.items())))


def phase_founder_review_packet(ctx: FactoryContext, ledger: Dict) -> PhaseResult:
    from scripts.pettripfinder import founder_review_analysis as FRA
    from scripts.pettripfinder import market_founder_review_cli as REVIEW_CLI
    from scripts.pettripfinder.discovery import census_duplicate_scan as DUP
    store = phase_artifact(ledger, CLOSURE, "observation_store")
    packet = ctx.artifact("founder_review_packet")
    code, message = _call(REVIEW_CLI.main, [
        "--market", ctx.market_id, "--observations", store,
        "--census", ctx.census_path.as_posix(),
        "--work-order", ctx.work_order, "--as-of", ctx.as_of,
        "--out", packet.as_posix()])
    if code != 0:
        return PhaseResult(BLOCKED, "founder-review packet failed: %s" % message)
    analysis = ctx.artifact("founder_review_analysis")
    code, message = _call(FRA.main, [
        "--packet", packet.as_posix(), "--census", ctx.census_path.as_posix(),
        "--observations", store, "--work-order", ctx.work_order,
        "--reviewer", ctx.reviewer, "--out", analysis.as_posix()])
    if code != 0:
        return PhaseResult(BLOCKED, "machine review failed: %s" % message)
    duplicates = ctx.artifact("identity_duplicate_scan")
    code, message = _call(DUP.main, [
        "--market", ctx.market_id, "--candidates", packet.as_posix(),
        "--census", ctx.census_path.as_posix(),
        "--work-order", ctx.work_order, "--out", duplicates.as_posix()])
    if code != 0:
        return PhaseResult(BLOCKED, "duplicate scan failed: %s" % message)
    ledger["phases"][FOUNDER_REVIEW_PACKET] = OrderedDict((
        ("status", COMPLETED),
        ("artifacts", OrderedDict((
            ("packet", OrderedDict((("path", packet.as_posix()),))),
        ))),
    ))
    coverage = _coverage(ctx, ledger, stage=MC.STAGE_FOUNDER_REVIEW_PACKET)
    packet_doc = _read(packet.as_posix())
    return PhaseResult(
        COMPLETED, "packet: %d candidates %s; %s"
        % (packet_doc["count"], dict(packet_doc["recommendation_counts"]),
           coverage.note),
        artifacts=OrderedDict((("packet", packet.as_posix()),
                               ("analysis", analysis.as_posix()),
                               ("duplicate_scan", duplicates.as_posix()))
                              + tuple(coverage.artifacts.items())),
        facts=OrderedDict((("candidates", packet_doc["count"]),)
                          + tuple(coverage.facts.items())))


def founder_review_gate(ledger: Mapping) -> Tuple[bool, str]:
    """Founder review may begin only after coverage completion says READY.

    Read from the artifact the founder-review-packet phase wrote, never from a
    phase status: a status says a phase ran, the artifact says what it found.
    """
    path = phase_artifact(ledger, FOUNDER_REVIEW_PACKET, "coverage")
    if not path or not Path(path).is_file():
        return (False, "no coverage-completion artifact from the founder-review-"
                       "packet phase; coverage has not been evaluated")
    document = _read(path)
    if document.get("schema") != COV.SCHEMA:
        return (False, "coverage artifact has schema %r, not %s"
                % (document.get("schema"), COV.SCHEMA))
    if document.get("evaluation_stage") != MC.STAGE_FOUNDER_REVIEW_PACKET:
        return (False, "coverage artifact was evaluated at stage %r, before the "
                       "packet existed" % document.get("evaluation_stage"))
    booleans = document.get("booleans") or {}
    if not booleans.get("READY_FOR_FOUNDER_REVIEW"):
        movable = document.get("identities_the_factory_can_still_move") or []
        failed = [k for k, v in booleans.items() if not v]
        return (False, "READY_FOR_FOUNDER_REVIEW is false: %s; %d identities "
                       "the factory can still move (first: %s)"
                % (", ".join(failed), len(movable), movable[:5]))
    return (True, "coverage completion evaluated and READY")


def phase_founder_review(ctx: FactoryContext, ledger: Dict) -> PhaseResult:
    ok, why = founder_review_gate(ledger)
    if not ok:
        return PhaseResult(BLOCKED, "founder review cannot begin: %s" % why)
    return PhaseResult(
        AWAITING_HUMAN,
        "the packet at %s is ready for a founder. Nothing here decides; a "
        "person sets founder_decision with their own identifier."
        % phase_artifact(ledger, FOUNDER_REVIEW_PACKET, "packet"),
        artifacts=OrderedDict((
            ("packet", phase_artifact(ledger, FOUNDER_REVIEW_PACKET, "packet")),
            ("coverage", phase_artifact(ledger, FOUNDER_REVIEW_PACKET, "coverage")),
        )))


DEFAULT_RUNNERS: Dict[str, Callable[[FactoryContext, Dict], PhaseResult]] = OrderedDict((
    (CENSUS, phase_census),
    (ROUTING, phase_routing),
    (ZERO_COST_URL_RECOVERY, phase_zero_cost_url_recovery),
    (PRIOR_BUILD_RECONCILIATION, phase_prior_build_reconciliation),
    (REROUTE, phase_reroute),
    (PRE_ACQUISITION_DEDUP, phase_pre_acquisition_dedup),
    (ACQUISITION, phase_acquisition),
    (DECLINED_EVIDENCE_RECOVERY, phase_declined_evidence_recovery),
    (REROUTE_RECOVERED, phase_reroute_recovered),
    (ACQUIRE_NEWLY_ROUTABLE, phase_acquire_newly_routable),
    (ALTERNATE_LANE_HANDLING, phase_alternate_lane_handling),
    (COVERAGE_EXHAUSTION, phase_coverage_exhaustion),
    (CLOSURE, phase_closure),
    (FOUNDER_REVIEW_PACKET, phase_founder_review_packet),
    (FOUNDER_REVIEW, phase_founder_review),
))


# --------------------------------------------------------------------------- #
# Sequencing gates -- checked by the sequencer, independent of any runner
# --------------------------------------------------------------------------- #

def phase_gate(phase: str, ledger: Mapping) -> Tuple[bool, str]:
    """May this phase start? Every predecessor satisfied, plus the artifact
    gates the lifecycle is built around."""
    index = PHASES.index(phase)
    for earlier in PHASES[:index]:
        if status_of(ledger, earlier) not in SATISFIED:
            return (False, "predecessor %s is %s" % (earlier, status_of(ledger, earlier)))
    if phase in PAID_PHASES:
        # Zero-cost recovery runs before paid acquisition. Not a convention: an
        # artifact must exist, and it must be the full-strength recovery.
        recovery = phase_artifact(ledger, PRIOR_BUILD_RECONCILIATION, "url_recovery")
        if not recovery or not Path(recovery).is_file():
            return (False, "no zero-cost URL recovery artifact; paid acquisition "
                           "may not begin before it")
        if phase != ACQUISITION:
            declined = status_of(ledger, DECLINED_EVIDENCE_RECOVERY)
            if declined not in SATISFIED:
                return (False, "declined-evidence recovery is %s; a second paid "
                               "pass may not begin before it" % declined)
    if phase == FOUNDER_REVIEW:
        return founder_review_gate(ledger)
    return (True, "")


def run_phases(ctx: FactoryContext, *, through: str = FOUNDER_REVIEW,
               only: Optional[str] = None,
               runners: Optional[Mapping[str, Callable]] = None,
               rerun: bool = False) -> Dict:
    """Run the lifecycle up to ``through`` (or exactly ``only``), recording each
    phase in the ledger as it finishes. Stops at the first phase that does not
    end satisfied."""
    if through not in PHASES:
        raise ValueError("unknown phase %r" % through)
    if only is not None and only not in PHASES:
        raise ValueError("unknown phase %r" % only)
    table = dict(DEFAULT_RUNNERS)
    table.update(runners or {})
    ledger = load_ledger(ctx)
    ledger["market_id"], ledger["work_order"] = ctx.market_id, ctx.work_order
    ledger["last_invocation"] = OrderedDict((
        ("at", _now()), ("through", through), ("only", only or ""),
        ("spend_authorised", bool(ctx.spend_authorised)),
    ))
    save_ledger(ctx, ledger)
    selected = [only] if only else list(PHASES[:PHASES.index(through) + 1])
    for phase in selected:
        if status_of(ledger, phase) in SATISFIED and not rerun:
            continue
        ok, why = phase_gate(phase, ledger)
        if not ok:
            record(ledger, phase, PhaseResult(BLOCKED, why))
            save_ledger(ctx, ledger)
            break
        try:
            result = table[phase](ctx, ledger)
        except Exception as exc:                                   # noqa: BLE001
            result = PhaseResult(BLOCKED, "%s: %s" % (type(exc).__name__, exc))
        record(ledger, phase, result)
        save_ledger(ctx, ledger)
        print("[%2d/%d] %-28s %-22s %s" % (PHASES.index(phase) + 1, len(PHASES),
                                           phase, result.status,
                                           result.note[:100]), flush=True)
        if result.status not in SATISFIED:
            break
    return ledger


def plan(ctx: FactoryContext) -> Dict:
    """What would run, in order, and what each phase would read. No execution."""
    ledger = load_ledger(ctx)
    rows = []
    for phase in PHASES:
        ok, why = phase_gate(phase, ledger)
        rows.append(OrderedDict((
            ("phase", phase), ("status", status_of(ledger, phase)),
            ("can_start_now", ok), ("gate", why),
            ("may_spend", phase in PAID_PHASES),
        )))
    return OrderedDict((("market_id", ctx.market_id),
                        ("work_order", ctx.work_order),
                        ("spend_authorised", ctx.spend_authorised),
                        ("phases", rows)))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--market", required=True)
    parser.add_argument("--work-order", required=True)
    parser.add_argument("--as-of", required=True)
    parser.add_argument("--contract", default="",
                        help="the ptf-market contract (geography); needed to "
                             "build a census, never to reuse one")
    parser.add_argument("--candidates", default="",
                        help="persisted discovery candidates for the census")
    parser.add_argument("--discovery-cache", default="",
                        help="the discovery cache directory the census was "
                             "built from; default data/discovery/<slug>/cache")
    parser.add_argument("--prior-census", default="")
    parser.add_argument("--prior-artifact", action="append", default=[])
    parser.add_argument("--authorised-cap-usd", type=float, default=0.0)
    parser.add_argument("--credit-cap", type=int, default=None)
    parser.add_argument("--authorise-spend", action="store_true",
                        help="let the paid phases spend under their cost "
                             "plans; without it they stop at the plan")
    parser.add_argument("--retry-overrides", default="")
    parser.add_argument("--reviewer", default="market_factory_cli (machine review)")
    parser.add_argument("--suffix", default="001")
    parser.add_argument("--census-dir", default="",
                        help="where this build's census lives; default "
                             "identity_census/. A REGISTERED market is "
                             "re-censused into a sandbox directory so its live "
                             "census -- pinned by its release contract -- is "
                             "read as prior evidence and never overwritten")
    parser.add_argument("--through", default=FOUNDER_REVIEW, choices=PHASES)
    parser.add_argument("--phase", default="", help="run exactly one phase")
    parser.add_argument("--rerun", action="store_true",
                        help="re-run phases already recorded as satisfied")
    parser.add_argument("--plan", action="store_true",
                        help="print what would run and stop")
    args = parser.parse_args(argv)

    slug = args.market.replace("-", "_")
    ctx = FactoryContext(
        market_id=args.market, work_order=args.work_order, as_of=args.as_of,
        contract_path=Path(args.contract) if args.contract else None,
        candidates_path=Path(args.candidates) if args.candidates else None,
        discovery_cache=Path(args.discovery_cache) if args.discovery_cache
        else _REPO_ROOT / "data" / "discovery" / slug / "cache",
        prior_census=Path(args.prior_census) if args.prior_census else None,
        prior_artifacts=tuple(args.prior_artifact),
        authorised_cap_usd=args.authorised_cap_usd, credit_cap=args.credit_cap,
        spend_authorised=bool(args.authorise_spend),
        retry_overrides=Path(args.retry_overrides) if args.retry_overrides else None,
        reviewer=args.reviewer, suffix=args.suffix,
        census_dir=Path(args.census_dir) if args.census_dir else CENSUS_DIR)
    if args.plan:
        print(json.dumps(plan(ctx), indent=1))
        return 0
    ledger = run_phases(ctx, through=args.through, only=args.phase or None,
                        rerun=args.rerun)
    print("ledger : %s" % ctx.ledger_path.as_posix())
    unsatisfied = [p for p in PHASES if status_of(ledger, p) not in SATISFIED]
    print("phases : %d of %d satisfied; next: %s"
          % (len(PHASES) - len(unsatisfied), len(PHASES),
             unsatisfied[0] if unsatisfied else "none -- founder review"))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
