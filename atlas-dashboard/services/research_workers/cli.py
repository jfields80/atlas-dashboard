"""ATLAS-WORKERS-001 -- worker CLI (Stage 9).

    python -m services.research_workers benchmark --provider fake
    python -m services.research_workers validate --result <path>

The CLI defaults to OFFLINE. A network client is never initialized unless the
spending airlock is fully satisfied: --live, --confirm-spend, an explicit
--provider and --model, and a matching API credential in the environment. API
keys are never read into output and the model is never silently switched.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Optional

from services.research_workers import vocabulary as V
from services.research_workers.benchmark import Budget, run_benchmark
from services.research_workers.contracts import Assignment, WorkerResult
from services.research_workers.hotel_policy_worker import run_assignment
from services.research_workers.pricing import load_pricing
from services.research_workers.providers import (
    FakeProvider, LiveAuthorization, SpendingAirlockError, build_provider,
)
from services.research_workers.repository import WorkerRepository
from services.research_workers.web_research import (
    REASONING_EFFORTS as _WR_EFFORTS,
    SEARCH_CONTEXT_SIZES as _WR_CONTEXT_SIZES,
)


def _build_provider(args) -> object:
    """Return a provider, enforcing the airlock for any non-fake/live path."""
    if args.provider == "fake" and not args.live:
        return FakeProvider()
    # Any other provider, or --live, must pass the full airlock.
    auth = LiveAuthorization(
        live=args.live, confirm_spend=args.confirm_spend, provider=args.provider,
        model=args.model or "", api_key_env=args.api_key_env)
    return build_provider(args.provider, auth=auth)   # raises SpendingAirlockError unless authorized


def _budget(args) -> Optional[Budget]:
    if not any((args.max_assignments, args.max_total_input_tokens,
                args.max_total_output_tokens, args.max_estimated_cost)):
        return None
    return Budget(
        max_assignments=args.max_assignments,
        max_total_input_tokens=args.max_total_input_tokens,
        max_total_output_tokens=args.max_total_output_tokens,
        max_estimated_cost=args.max_estimated_cost)


def _cmd_benchmark(args) -> int:
    provider = _build_provider(args)
    model = args.model or ("fake-extractor-v1" if provider.name == "fake" else "")
    if not model:
        raise SpendingAirlockError("a --model is required")
    pricing = load_pricing(args.pricing) if args.pricing else {}
    report = run_benchmark(
        provider, model=model, benchmark_path=args.benchmark, pricing_table=pricing,
        output_token_cap=args.output_token_cap, timeout_s=args.timeout,
        max_retries=args.max_retries, budget=_budget(args))
    if args.write_report:
        repo = WorkerRepository(Path(args.output_root) if args.output_root else None)
        path = repo.write_benchmark_report("%s_%s_%s" % (report["benchmark_id"], provider.name, model), report)
        report["_written_to"] = str(path)
    if args.json:
        print(json.dumps(report, sort_keys=True, ensure_ascii=False, indent=2))
    else:
        _print_summary(report)
    return 0


def _print_summary(r: dict) -> None:
    print("benchmark: %s (%s)   provider=%s model=%s"
          % (r["benchmark_id"], r["benchmark_kind"], r["provider"], r["model"]))
    print("  NOTE: %s" % r["note"])
    print("  assignments attempted        : %d" % r["assignments_attempted"])
    print("  structured_valid_results     : %d" % r["structured_valid_results"])
    print("  validator_passed_results     : %d" % r["validator_passed_results"])
    print("  benchmark_correct_results    : %d" % r["benchmark_correct_results"])
    print("  publication_eligible_results : %d" % r["publication_eligible_results"])
    print("  human_review_results         : %d" % r["human_review_results"])
    print("  no_source_results            : %d" % r["no_source_results"])
    print("  failed_results               : %d" % r["failed_results"])
    print("  exact evidence match rate    : %.3f" % r["exact_evidence_match_rate"])
    print("  field precision / recall     : %.3f / %.3f" % (r["field_precision"], r["field_recall"]))
    print("  unsupported / forbidden      : %d / %d" % (r["unsupported_fact_count"], r["forbidden_inference_count"]))
    print("  contradiction detection      : %.3f" % r["contradiction_detection_rate"])
    print("  avg tokens in/out            : %s / %s" % (r["avg_input_tokens"], r["avg_output_tokens"]))
    print("  total estimated cost         : %s" % ("(pricing not supplied)" if r["total_estimated_cost_usd"] is None
                                                   else "$%.6f" % r["total_estimated_cost_usd"]))
    for k in ("cost_per_validator_passed_result", "cost_per_benchmark_correct_result",
              "cost_per_publication_eligible_result"):
        print("  %-29s: %s" % (k, "n/a" if r[k] is None else "$%.6f" % r[k]))
    if r.get("budget_stopped"):
        print("  BUDGET STOPPED               : %s" % r["stop_reason"])


def _print_checkpoint(cp: dict) -> None:
    print("=== ATLAS-WORKERS-002 operator checkpoint (no paid call yet) ===")
    print("  planned request count      : %d" % cp["planned_request_count"])
    print("  output token cap           : %d" % cp["output_token_cap"])
    print("  worst-case estimated cost  : $%.6f" % cp["worst_case_estimated_cost_usd"])
    print("  max estimated cost ceiling : $%.2f" % cp["max_estimated_cost_usd"])
    print("  spend authorization env    : %s" % cp["spend_authorization_env"])
    print("  spend authorization present: %s" % cp["spend_authorization_present"])
    print("  output directory           : %s" % cp["output_dir"])
    print("  providers / credentials (presence only; values never read):")
    for p in cp["providers"]:
        print("    - %-9s %-24s env=%-16s present=%s"
              % (p["provider"], p["model_id"], p["credential_env"], p["credential_present"]))


def _cmd_evaluate(args) -> int:
    from services.research_workers.eval_config import DEFAULT_MODELS, select_model
    from services.research_workers.model_eval import (
        EvalCaps, build_run_manifest, operator_checkpoint, run_live_evaluation,
    )
    from services.research_workers.providers import SpendingAirlockError
    # Explicit single-model selection: --model (with --provider) targets exactly
    # one configured model and NEVER runs DEFAULT_MODELS or falls back to another
    # model. Omitting --model preserves the default multi-model bakeoff set.
    if args.model:
        try:
            models = [select_model(args.provider, args.model)]
        except KeyError as exc:
            raise SpendingAirlockError(str(exc))
    else:
        models = DEFAULT_MODELS
    caps = EvalCaps(repetitions=args.repetitions, max_assignments=args.max_assignments or 90,
                    max_estimated_cost=(args.max_estimated_cost if args.max_estimated_cost is not None else 1.00),
                    max_retries=args.max_retries, output_token_cap=args.output_token_cap,
                    timeout_s=args.timeout)
    cp = operator_checkpoint(models, caps, args.benchmark, case_id=args.case_id)
    _print_checkpoint(cp)

    repo = WorkerRepository(Path(args.output_root) if args.output_root else None)
    if not args.live:
        manifest = build_run_manifest(models, caps, args.benchmark, case_id=args.case_id)
        repo.write_benchmark_report("aw002_run_manifest", manifest)
        print("\nDRY RUN (no --live): manifest written; no network client constructed, no paid call.")
        return 0
    # Live path: the airlock decides. A missing credential blocks only that model.
    try:
        report = run_live_evaluation(models, caps, benchmark_path=args.benchmark,
                                     case_id=args.case_id)
    except SpendingAirlockError as exc:
        print("\nLIVE BENCHMARK BLOCKED BY AIRLOCK: %s" % exc)
        print("No network client was constructed and no paid call was made.")
        return 0
    path = repo.write_benchmark_report("aw002_live_bakeoff", report)
    print("\nlive bakeoff complete: calls=%d cost=$%.6f default_model=%s"
          % (report["calls_made"], report["cumulative_cost_usd"], report["default_model"]))
    print("report:", path)
    return 0


def _cmd_canary(args) -> int:
    """ONE live call through the SAME adapter + parser the benchmark uses.
    Prints a sanitized diagnostic report (never a key, header, or request
    body). Exit 0 when the model responded and parsed; 5 otherwise."""
    from services.research_workers.eval_config import select_model
    from services.research_workers.model_eval import run_canary
    if not (args.live and args.confirm_spend):
        raise SpendingAirlockError("canary makes ONE paid call: requires --live and --confirm-spend")
    try:
        model = select_model(args.provider, args.model)
    except KeyError as exc:
        raise SpendingAirlockError(str(exc))
    report = run_canary(model, output_token_cap=args.output_token_cap,
                        timeout_s=args.timeout, max_retries=args.max_retries)
    print(json.dumps(report, sort_keys=True, ensure_ascii=False, indent=2))
    return 0 if report["ok"] else 5


def _print_routing_summary(summary: dict, envelopes: list, written: int, wrote: bool) -> None:
    print("=== ATLAS-WORKERS-003 routing summary (offline; no model call, no production write) ===")
    print("  total routed        : %d" % summary["total"])
    for r in ("READY", "REVIEW", "RETRY", "REJECTED"):
        print("  %-20s: %d" % (r, summary["routes"].get(r, 0)))
    print("  reason codes:")
    for code, n in summary["reasons"].items():
        print("    - %-32s %d" % (code, n))
    print("  per assignment:")
    for e in envelopes:
        print("    - %-34s %-9s %s" % (e.assignment_id, e.route, ",".join(e.reason_codes)))
    if wrote:
        print("  wrote %d routing envelope(s) to the gitignored routing queue" % written)
    else:
        print("  DRY RUN: no envelopes written (pass --write to persist to the gitignored queue)")


def _cmd_route(args) -> int:
    """Deterministically route validated worker results into the
    READY/REVIEW/RETRY/REJECTED airlock. Offline: it evaluates the committed
    benchmark with the deterministic FakeProvider oracle (never a model call),
    validates each result, and routes it. Dry-run by default; --write persists
    immutable envelopes to the gitignored routing queue. No production write."""
    from services.research_workers.benchmark import load_benchmark
    from services.research_workers.evidence_validator import validate_proposal
    from services.research_workers.model_eval import VALIDATOR_VERSION, select_cases
    from services.research_workers.prompt import PROMPT_VERSION
    from services.research_workers.routing import route_result, summarize_envelopes

    provider = FakeProvider()          # offline oracle; routing itself never calls a model
    _bid, cases = load_benchmark(args.benchmark)
    cases = select_cases(cases, args.assignment_id)          # exact id or bench- alias; never substitutes
    prompt_version = args.prompt_version or PROMPT_VERSION
    validator_version = args.validator_version or VALIDATOR_VERSION

    envelopes = []
    for case in cases:
        proposal = provider.propose(case.assignment, model="fake-extractor-v1")
        result = validate_proposal(case.assignment, proposal, provider=provider.name,
                                   model="fake-extractor-v1")
        envelopes.append(route_result(
            case.assignment, result, proposal, prompt_version=prompt_version,
            validator_version=validator_version, observed_at=args.observed_at, run_id=args.run_id))

    summary = summarize_envelopes(envelopes)
    written = 0
    if args.write:
        repo = WorkerRepository(Path(args.output_root) if args.output_root else None)
        for env in envelopes:
            repo.write_routing_envelope(env)
            written += 1
    _print_routing_summary(summary, envelopes, written, wrote=args.write)
    if args.json:
        print(json.dumps({"summary": summary, "envelopes": [e.to_dict() for e in envelopes]},
                         sort_keys=True, ensure_ascii=False, indent=2))
    return 0


def _print_pilot_checkpoint(cp: dict) -> None:
    print("=== ATLAS-WORKERS-004 Columbus hotel intake -- operator checkpoint (no paid call yet) ===")
    print("  hotels found               : %d" % cp["hotels_found"])
    print("  assignments ready          : %d" % cp["assignments_ready"])
    print("  assignments blocked        : %d" % cp["assignments_blocked"])
    print("  readiness                  : %s" % cp["readiness_counts"])
    print("  planned live calls         : %d" % cp["planned_live_calls"])
    print("  model snapshot             : %s / %s"
          % (cp["model_snapshot"]["provider"], cp["model_snapshot"]["model_id"]))
    print("  prompt version             : %s" % cp["prompt_version"])
    print("  output token cap           : %d" % cp["output_token_cap"])
    print("  worst-case estimated cost  : $%.6f" % cp["worst_case_estimated_cost_usd"])
    print("  spend ceiling              : $%.2f" % cp["max_estimated_cost_ceiling_usd"])
    print("  spend authorization present: %s" % cp["spend_authorization_present"])
    print("  credential present         : %s (env %s; value never read)"
          % (cp["credential_present"], cp["credential_env"]))
    print("  gitignored output root     : %s" % cp["gitignored_output_root"])
    print("  no production write         : %s" % cp["no_production_write"])


def _print_pilot_summary(s: dict) -> None:
    inv, rt, q, cost = s["inventory"], s["routing"], s["quality"], s["cost"]
    print("=== ATLAS-WORKERS-004 Columbus hotel pilot -- operator summary (mode=%s) ===" % s["mode"])
    print("  candidates=%d ready=%d blocked=%d reused=%d new_calls=%d successful=%d"
          % (inv["authoritative_hotel_candidates"], inv["assignments_constructed"],
             inv["assignments_blocked"], inv.get("reused_without_call", 0),
             inv.get("new_live_calls_attempted", 0), inv["successful_model_responses"]))
    print("  routes: %s" % rt["counts"])
    print("  route %%: %s" % rt["percentages"])
    print("  reasons: %s" % rt["reason_counts"])
    print("  quality: structurally_valid=%d contradictions=%d unsupported_inf=%d forbidden_inf=%d warnings=%d"
          % (q["structurally_valid"], q["contradictions"], q["unsupported_inferences"],
             q["forbidden_inferences"], q["validator_warnings"]))
    print("  cost: total=$%.6f attempted_avg=$%.6f ready_avg=$%.6f (ceiling $%.2f)"
          % (cost["total_estimated_cost_usd"], cost["avg_cost_per_attempted_hotel_usd"],
             cost["avg_cost_per_ready_hotel_usd"], cost["spend_ceiling_usd"]))
    print("  success criteria: %s" % s["success_criteria"])


def _cmd_columbus_pilot(args) -> int:
    """ATLAS-WORKERS-004 Columbus/Dublin hotel live intake pilot. Dry-run by
    default (no network, no writes). --report reads persisted artifacts. Live
    requires --live + --confirm-spend + the spend-authorization token, targets
    ONLY the approved Nano snapshot, and writes only gitignored pilot artifacts."""
    from services.research_workers import columbus_pilot as CP
    store = CP.PilotStore(Path(args.output_root) if args.output_root else None)

    if args.report:
        summary_path = store.root / "operator_summary.json"
        if not summary_path.exists():
            print("no pilot artifacts found at %s (run the pilot first)" % store.root)
            return 4
        summary = json.loads(summary_path.read_text(encoding="utf-8"))
        if args.json:
            print(json.dumps(summary, sort_keys=True, ensure_ascii=False, indent=2))
        else:
            _print_pilot_summary(summary)
        return 0

    candidates = CP.load_columbus_hotel_candidates(args.seed)
    classified = CP.classify_candidates(candidates)
    caps = CP.PilotCaps(max_estimated_cost=args.max_estimated_cost, output_token_cap=args.output_token_cap,
                        max_retries=args.max_retries, timeout_s=args.timeout,
                        max_assignments=args.max_assignments)
    cp = CP.operator_checkpoint(classified, caps, pilot_root=str(store.root),
                                only_hotel=args.assignment_filter)
    _print_pilot_checkpoint(cp)

    if not args.live:
        report = CP.run_pilot(classified, caps, live=False, store=store,
                              only_hotel=args.assignment_filter)
        for b in report["blocked"]:
            print("  BLOCKED %-28s %s (%s)" % (b["readiness"], b["listing_name"], b["reason"]))
        print("\nDRY RUN: no network call, no pilot artifact written. "
              "Re-run with --live --confirm-spend to execute.")
        return 0

    if not args.confirm_spend:
        raise SpendingAirlockError("live pilot requires --confirm-spend (a paid run)")
    try:
        report = CP.run_pilot(classified, caps, live=True, store=store,
                              observed_at=args.observed_at, run_id=args.run_id,
                              only_hotel=args.assignment_filter)
    except SpendingAirlockError as exc:
        print("\nLIVE PILOT BLOCKED BY AIRLOCK: %s" % exc)
        print("No network client was constructed and no paid call was made.")
        print("Operator command (needs OPENAI_API_KEY + %s=YES_MAX_1_USD):" % CP.SPEND_AUTH_ENV)
        print("  python -m services.research_workers columbus-hotel-pilot --live --confirm-spend")
        return 3
    paths = CP.persist_pilot(store, report)
    _print_pilot_summary(CP.build_operator_summary(report))
    print("\nstopped_reason:", report.get("stopped_reason") or "(none)")
    print("operator_summary:", paths["operator_summary"])
    print("candidate_export:", paths["candidate_export"])
    if args.json:
        print(json.dumps(report, sort_keys=True, ensure_ascii=False, indent=2))
    return 0


def _cmd_retrieve_official_sources(args) -> int:
    """PTF-WORKERS-003: fetch official hotel pages -> SourceDocument.

    Zero model calls by construction -- no provider is built anywhere on this
    path, so no credential and no spend authorization are consulted. Writes
    only under the gitignored pilot root's ``retrieval/`` subdir; touches no
    production data file.
    """
    import json as _json

    from repositories.artifact_store_repository import ArtifactStoreRepository
    from scripts.pettripfinder.importer import constants as _C
    from scripts.pettripfinder.importer.fetch import RequestsPageFetcher, StaticPageFetcher
    from services.research_workers import source_retrieval as SR
    from services.research_workers.columbus_pilot import (
        PilotStore, RETRIEVAL, load_columbus_hotel_candidates, normalize_listing_key,
    )

    candidates = load_columbus_hotel_candidates(args.seed)
    by_key = {normalize_listing_key(c.name): c for c in candidates}

    # HotelCandidate carries no city/state/website_url (it never needed them
    # for evidence-text extraction). Identity verification does, so read those
    # three columns straight from the same committed seed rather than widening
    # the shared loader contract for one caller.
    import csv as _csv
    from services.research_workers.columbus_pilot import DEFAULT_SEED, HOTEL_CATEGORY
    geo = {}
    seed_path = Path(args.seed) if args.seed else DEFAULT_SEED
    with seed_path.open(encoding="utf-8") as fh:
        for row in _csv.DictReader(fh):
            if row.get("category") != HOTEL_CATEGORY:
                continue
            geo[normalize_listing_key(row.get("name", ""))] = {
                "city": row.get("city", ""), "state": row.get("state", ""),
                "postal_code": row.get("postal_code", ""),
                "website_url": row.get("website_url", ""),
            }

    selected = []
    for want in args.hotel:
        key = normalize_listing_key(want)
        if key not in by_key:
            sys.stderr.write("no such hotel in seed inventory: %r (never substitutes)\n" % want)
            return 2
        selected.append(by_key[key])

    # Offline fixtures make the whole command deterministic and network-free.
    fixtures = {}
    for spec in args.offline_fixture:
        url, _, path = spec.partition("=")
        if not url or not path:
            sys.stderr.write("--offline-fixture expects URL=path, got %r\n" % spec)
            return 2
        fixtures[url] = Path(path).read_text(encoding="utf-8")
    if fixtures:
        fetcher = StaticPageFetcher()
        for url, html in fixtures.items():
            fetcher.add_html(url, html)
    else:
        fetcher = RequestsPageFetcher()

    # Per-hotel overrides must not be able to attach one hotel's evidence to
    # another, so they are refused outright for a multi-hotel run.
    rendered_text = ""
    if args.rendered_evidence or args.source_url:
        if len(selected) != 1:
            sys.stderr.write("--source-url/--rendered-evidence require exactly "
                             "one --hotel (got %d)\n" % len(selected))
            return 2
    if args.rendered_evidence:
        cap = _json.loads(Path(args.rendered_evidence).read_text(encoding="utf-8-sig"))
        rendered_text = str(
            ((cap.get("automation") or {}).get("policy") or {}).get("text_excerpt")
            or "")
        if not rendered_text.strip():
            sys.stderr.write("--rendered-evidence carries no policy text: %s\n"
                             % args.rendered_evidence)
            return 2

    store = PilotStore(Path(args.output_root) if args.output_root else None)
    cas = ArtifactStoreRepository(store.root / _C.CAS_SUBDIR)

    outcomes = []
    for cand in selected:
        g = geo.get(normalize_listing_key(cand.name), {})
        expected = SR.ExpectedEntity(
            listing_key=cand.listing_key, listing_name=cand.name,
            address=cand.address, city=g.get("city", ""), state=g.get("state", ""),
            postal_code=g.get("postal_code", ""), phone=cand.phone,
            website_url=g.get("website_url", "") or cand.source_url)
        out = SR.retrieve_official_source(
            assignment_id="retr-%s" % cand.listing_key.replace(" ", "-")[:60],
            expected=expected,
            source_url=args.source_url or cand.source_url, fetcher=fetcher,
            cas=cas, observed_at=args.observed_at,
            rendered_policy_text=rendered_text)
        store.write_per_hotel(RETRIEVAL, out.assignment_id, out.to_dict())
        outcomes.append(out)

    print("=== PTF-WORKERS-003 official-source retrieval (retrieval-only) ===")
    print("  model calls made           : 0")
    print("  spend                      : $0.00")
    print("  credential consulted       : none")
    print("  production data written    : none")
    print("  artifact root              : %s" % (store.root / RETRIEVAL))
    print("")
    for o in outcomes:
        print("  %-46s %-18s identity=%-22s role=%s"
              % (o.listing_name[:46], o.status, o.identity or "-", o.source_role or "-"))
        print("       initial : %s" % o.initial_url)
        print("       final   : %s" % (o.final_url or "-"))
        print("       redirects=%d  http=%s  reason=%s  fetch_status=%s"
              % (len(o.redirect_chain), o.http_status or "-",
                 o.importer_reason or "-", o.importer_fetch_status or "-"))
        print("       norm_text=%d bytes  text_hash=%s  raw_hash=%s"
              % (o.normalized_text_bytes, (o.normalized_text_hash or "-")[:16],
                 (o.raw_content_hash or "-")[:16]))
        print("       policy candidates=%d  applicable=%s  brand_scope=%s"
              % (len(o.policy_candidates), o.policy_applicable, o.brand_policy_scope or "-"))
        for c in o.policy_candidates[:5]:
            print("          %4d  %s" % (c.score, c.url))
        if o.warnings:
            print("       warnings: %s" % ", ".join(o.warnings))
        print("       READY FOR EXTRACTION: %s" % o.ready_for_extraction)
        print("")

    ready = [o for o in outcomes if o.ready_for_extraction]
    print("  ready for extraction : %d of %d" % (len(ready), len(outcomes)))
    if args.json:
        print(_json.dumps([o.to_dict() for o in outcomes], indent=2, sort_keys=True))
    return 0


def _cmd_attest_official_page(args) -> int:
    """PTF-WORKERS-006: record a PENDING manual official attestation.

    Zero network, zero model calls, zero credential reads. The operator
    supplies a page capture and screenshots; no policy value is ever typed by
    a human here.
    """
    import csv as _csv
    import json as _json

    from repositories.artifact_store_repository import ArtifactStoreRepository
    from scripts.pettripfinder.importer import constants as _C
    from services.research_workers import operator_capture as OC
    from services.research_workers.columbus_pilot import (
        ATTESTATIONS, DEFAULT_SEED, HOTEL_CATEGORY, PilotStore,
        load_columbus_hotel_candidates, normalize_listing_key,
    )

    candidates = load_columbus_hotel_candidates(args.seed)
    by_key = {normalize_listing_key(c.name): c for c in candidates}
    want = normalize_listing_key(args.hotel)
    if want not in by_key:
        sys.stderr.write("no such hotel in seed inventory: %r\n" % args.hotel)
        return 2
    cand = by_key[want]

    geo = {}
    seed_path = Path(args.seed) if args.seed else DEFAULT_SEED
    with seed_path.open(encoding="utf-8") as fh:
        for r in _csv.DictReader(fh):
            if r.get("category") == HOTEL_CATEGORY:
                geo[normalize_listing_key(r.get("name", ""))] = r
    row = geo.get(want, {})

    retrieval = _json.loads(Path(args.after_retrieval).read_text(encoding="utf-8-sig"))
    failure = OC.AutomatedFailure(
        status=str(retrieval.get("status") or ""),
        reason=str(retrieval.get("failure_reason") or ""),
        artifact_path=args.after_retrieval)

    job = OC.CaptureJob(
        assignment_id="attest-%s" % cand.listing_key.replace(" ", "-")[:48],
        listing_key=cand.listing_key, listing_name=cand.name,
        expected_address=cand.address, expected_city=row.get("city", ""),
        expected_state=row.get("state", ""), expected_postal_code=row.get("postal_code", ""),
        expected_phone=cand.phone,
        official_url=row.get("website_url", "") or cand.source_url,
        alternate_urls=tuple(args.alternate_url), failure_reason=failure.reason,
        retrieval_status=failure.status)

    payload = _json.loads(Path(args.capture).read_text(encoding="utf-8-sig"))

    # PTF-WORKERS-007: with --identity-capture, --capture is the POLICY surface
    # and the identity capture supplies the property URL. Without it, nothing
    # about the single-capture path changes.
    paired = None
    pair_failures = ()
    if getattr(args, "identity_capture", ""):
        identity_payload = _json.loads(
            Path(args.identity_capture).read_text(encoding="utf-8-sig"))
        ingestion, paired, pair_failures = OC.ingest_paired_capture(
            identity_payload=identity_payload, policy_payload=payload, job=job,
            observed_at=args.observed_at)
    else:
        ingestion = OC.ingest_capture(payload, job, observed_at=args.observed_at)

    # PTF-CAPTURE-003E. Before a human is asked to affirm identity, check that
    # the package in front of them can actually show it. Fails closed: an
    # operator cannot confirm an address that appears in no screenshot, and
    # being asked to is how a sincere affirmation becomes a false one.
    from services.research_workers.capture_automation.evidence_completeness import (
        FIELD_CITY, FIELD_HOTEL_NAME, FIELD_POSTAL_CODE, FIELD_PROPERTY_PHONE,
        FIELD_STATE, FIELD_STREET, assess_evidence,
    )
    from services.research_workers.capture_automation.identity_views import (
        load_views_for_capture,
    )
    expected_identity = {
        FIELD_HOTEL_NAME: job.listing_name, FIELD_STREET: job.expected_address,
        FIELD_CITY: job.expected_city, FIELD_STATE: job.expected_state,
        FIELD_POSTAL_CODE: job.expected_postal_code,
        FIELD_PROPERTY_PHONE: job.expected_phone,
    }
    evidence = assess_evidence(load_views_for_capture(args.capture),
                               official_url=str(payload.get("final_url") or ""),
                               expected=expected_identity)
    if not evidence.complete:
        # No override flag by design. "Fail closed" with a bypass is a warning,
        # and a warning is what let an incomplete package reach a human in the
        # first place. The remedy is to capture the missing views.
        sys.stderr.write(evidence.render())
        sys.stderr.write("\n\nREFUSED: the review package cannot show every field "
                         "the operator is asked to affirm.\n"
                         "Capture additional views of the same official page for "
                         "the missing fields,\nattach them to this capture, and "
                         "run again.\n")
        return 5

    print("=== PTF-WORKERS-006 manual official attestation ===")
    print("  evidence completeness      : COMPLETE (%d field(s) visibly proven)"
          % len(evidence.proven))
    for _f, (_view, _quote) in sorted(evidence.proven.items()):
        print("     %-16s %s" % (_f, _view))
    if getattr(args, "identity_capture", ""):
        print("  evidence mode              : PAIRED (identity + policy captures)")
        if pair_failures:
            print("  BINDING REFUSED            : %s" % ", ".join(pair_failures))
            return 4
        print("  identity capture           : %s" % paired.identity_capture_url)
        print("  policy capture             : %s" % paired.policy_capture_url)
        print("  binding signals            : %s" % ", ".join(paired.matched_signals))
        print("  card span / capture gap    : %d chars / %d s"
              % (paired.card_span_chars, paired.capture_gap_seconds))
    print("  model calls made           : 0")
    print("  credential consulted       : none")
    print("  production data written    : none")
    print("  hotel                      : %s" % cand.name)
    print("  capture status             : %s" % ingestion.status)
    if not ingestion.accepted:
        print("  REFUSED                    : %s" % ingestion.failure_reason)
        return 4

    store = PilotStore(Path(args.output_root) if args.output_root else None)
    cas = ArtifactStoreRepository(store.root / _C.CAS_SUBDIR)
    shots = [OC.store_screenshot(cas, Path(p).read_bytes(), note=Path(p).name)
             for p in args.screenshot]

    ref = None
    if args.model_research:
        mr = _json.loads(Path(args.model_research).read_text(encoding="utf-8-sig"))
        ref = OC.ModelResearchRef(urn=str(mr.get("source_type", "")) and
                                  "urn:atlas:model-research-report:(linked)",
                                  report_hash="")

    affirmation = OC.OperatorAffirmation(
        operator_id=args.operator_id, attested_at=args.attested_at,
        address_confirmed=args.address_confirmed, address_observed=args.address_observed,
        phone_confirmed=args.phone_confirmed, phone_observed=args.phone_observed)

    try:
        attestation = OC.build_attestation(
            ingestion=ingestion, job=job, affirmation=affirmation,
            automated_failure=failure, screenshots=shots,
            observed_at=args.observed_at, observed_timezone=args.timezone,
            model_research_ref=ref, paired_evidence=paired)
    except OC.AttestationError as exc:
        print("  ATTESTATION REFUSED        : %s" % exc)
        return 4

    print("  attestation id             : %s" % attestation.attestation_id)
    print("  attestation hash           : %s" % attestation.attestation_hash()[:39])
    print("  capture method             : %s" % attestation.capture_method)
    print("  source type                : %s" % attestation.source_type)
    print("  operator                   : %s at %s"
          % (affirmation.operator_id, affirmation.attested_at))
    print("  screenshots                : %d (CAS-referenced)" % len(shots))
    print("  approval state             : %s" % attestation.approval.state)
    print("  publishable                : %s" % attestation.publishable)
    print("")
    print("  preserved statements (nothing resolved):")
    for s in attestation.statements:
        print("     [%-20s @%6d] %s" % (s["topic"], s["char_start"], s["quote"][:100]))
    if attestation.contradictions:
        print("  CONTRADICTIONS PRESERVED   : %s" % ", ".join(attestation.contradictions))
    if attestation.fee_amounts:
        print("  fee amounts                : %s" % ", ".join(attestation.fee_amounts))

    store.write_per_hotel(ATTESTATIONS, attestation.attestation_id, attestation.to_dict())
    print("  artifact                   : %s" % (store.root / ATTESTATIONS))
    print("")
    print("  NOT PUBLISHABLE until approve-attestation records an explicit approval.")
    if args.json:
        print(_json.dumps(attestation.to_dict(), indent=2, sort_keys=True))
    return 0


def _cmd_resolve_contradiction(args) -> int:
    """PTF-APPROVAL-RESOLUTION: dispose of named markers on ONE attestation.

    Writes only inside the gitignored attestation store, leaves the attested
    content and its hash untouched, and never removes a detector marker.
    """
    import json as _json

    from services.research_workers import approval_resolution as AR
    from services.research_workers.columbus_pilot import ATTESTATIONS, PilotStore
    from services.research_workers.operator_capture import verify_attestation_record

    store = PilotStore(Path(args.output_root) if args.output_root else None)
    allowed_root = (store.root / ATTESTATIONS).resolve()
    path = Path(args.attestation).resolve()
    if allowed_root != path.parent:
        sys.stderr.write("refusing to write outside the attestation store\n"
                         "  target : %s\n  allowed: %s\n" % (path, allowed_root))
        return 2
    if not path.is_file():
        sys.stderr.write("no such attestation artifact: %s\n" % path)
        return 2

    record = _json.loads(path.read_text(encoding="utf-8-sig"))
    ok, why = verify_attestation_record(record)
    if not ok:
        sys.stderr.write("attested content does not verify: %s\n" % why)
        return 4

    recorded = [str(m) for m in (record.get("contradictions") or [])]
    wanted = []
    for family in args.family:
        hits = [m for m in recorded if AR.family_of(m) == family]
        if not hits:
            sys.stderr.write("no %s marker on this attestation; nothing to "
                             "resolve\n" % family)
            return 2
        wanted.append((family, hits))

    rationale = args.rationale
    if args.rationale_file:
        rationale = Path(args.rationale_file).read_text(encoding="utf-8").strip()

    approval = record.get("approval") or {}
    try:
        resolutions = [
            AR.build_resolution(
                markers=hits, disposition=args.disposition,
                approver_id=args.approver_id,
                approval_record_id=approval.get("approval_record_id", ""),
                attestation_id=record.get("attestation_id", ""),
                attestation_hash=record.get("attestation_hash", ""),
                rationale=rationale, resolved_at=args.resolved_at)
            for _family, hits in wanted]
        updated = AR.attach_resolutions(record, resolutions)
    except AR.ResolutionError as exc:
        sys.stderr.write("resolution refused: %s\n" % exc)
        return 4

    ok, why = verify_attestation_record(updated)
    if not ok:                                  # unreachable by construction
        sys.stderr.write("resolution altered attested content: %s\n" % why)
        return 4
    path.write_text(_json.dumps(updated, indent=2, sort_keys=True), encoding="utf-8")

    print("=== PTF-APPROVAL-RESOLUTION ===")
    print("  attestation id        : %s" % updated.get("attestation_id"))
    print("  attested content      : verified, hash unchanged")
    print("  approval record       : %s" % approval.get("approval_record_id"))
    print("  approver              : %s" % args.approver_id)
    print("  disposition           : %s" % args.disposition)
    for family, hits in wanted:
        print("  resolved %-13s : %s" % (family, ", ".join(hits)))
    print("  detector markers kept : %s" % ", ".join(recorded))
    print("  artifact updated      : %s" % path)
    print("")
    print("  Markers are NOT removed. Promotion may now carry the affected")
    print("  fields for THIS attestation hash only.")
    return 0


def _cmd_approve_attestation(args) -> int:
    """PTF-WORKERS-006: the separate, explicit approval act."""
    import json as _json

    from services.research_workers import operator_capture as OC

    from services.research_workers.columbus_pilot import ATTESTATIONS, PilotStore

    # Confinement. This command WRITES, and its target is operator-supplied, so
    # it must be proven to live inside the gitignored attestation store before a
    # single byte is written -- otherwise a mistyped path would overwrite a
    # tracked repository file with attestation JSON. Every other write in this
    # CLI already goes through PilotStore, which confines by construction.
    store = PilotStore(Path(args.output_root) if args.output_root else None)
    allowed_root = (store.root / ATTESTATIONS).resolve()
    path = Path(args.attestation).resolve()
    if allowed_root != path.parent:
        sys.stderr.write(
            "refusing to write outside the attestation store\n"
            "  target : %s\n  allowed: %s\n" % (path, allowed_root))
        return 2
    if not path.is_file():
        sys.stderr.write("no such attestation artifact: %s\n" % path)
        return 2

    record = _json.loads(path.read_text(encoding="utf-8-sig"))
    before_hash = record.get("attestation_hash", "")

    # Verify-then-approve, through the SAME function the tests exercise.
    try:
        record = OC.approve_attestation_record(
            record, approver_id=args.approver_id, approved_at=args.approved_at,
            approval_record_id=args.record_id, reject=args.reject,
            rationale=getattr(args, "rationale", ""))
    except OC.AttestationError as exc:
        sys.stderr.write("approval refused: %s\n" % exc)
        return 4

    print("=== PTF-WORKERS-006 attestation approval ===")
    print("  attested content verified  : hash matches the stored artifact")
    print("  attestation id             : %s" % record.get("attestation_id"))
    print("  attested by                : %s" % record.get("affirmation", {}).get("operator_id"))
    print("  approved by                : %s" % args.approver_id)
    print("  approval record id         : %s" % args.record_id)
    print("  state                      : %s" % record["approval"]["state"])
    print("  attestation hash           : %s" % before_hash[:39])
    print("     (unchanged by approval -- the approval provably applies to the")
    print("      exact content that was attested)")
    print("  publishable                : %s" % record["publishable"])
    path.write_text(_json.dumps(record, indent=2, sort_keys=True), encoding="utf-8")
    print("  artifact updated           : %s" % path)
    return 0


def _cmd_retrieve_rendered(args) -> int:
    """PTF-WORKERS-005: browser-render ONE official URL into real evidence.

    Zero model calls, zero credential reads, zero spend -- no provider is built
    anywhere on this path. Writes only under the gitignored pilot root's
    ``rendered_retrieval/`` subdir.
    """
    import csv as _csv
    import json as _json

    from repositories.artifact_store_repository import ArtifactStoreRepository
    from scripts.pettripfinder.importer import constants as _C
    from scripts.pettripfinder.importer.browser_fetch import (
        BrowserPageFetcher, PlaywrightBrowserDriver,
    )
    from services.research_workers import rendered_capture as RC
    from services.research_workers import source_retrieval as SR
    from services.research_workers import web_research as WR
    from services.research_workers.columbus_pilot import (
        DEFAULT_SEED, HOTEL_CATEGORY, RENDERED_RETRIEVAL, PilotStore,
        load_columbus_hotel_candidates, normalize_listing_key,
    )

    candidates = load_columbus_hotel_candidates(args.seed)
    by_key = {normalize_listing_key(c.name): c for c in candidates}
    want = normalize_listing_key(args.hotel)
    if want not in by_key:
        sys.stderr.write("no such hotel in seed inventory: %r (never substitutes)\n" % args.hotel)
        return 2
    cand = by_key[want]

    geo = {}
    seed_path = Path(args.seed) if args.seed else DEFAULT_SEED
    with seed_path.open(encoding="utf-8") as fh:
        for row in _csv.DictReader(fh):
            if row.get("category") == HOTEL_CATEGORY:
                geo[normalize_listing_key(row.get("name", ""))] = row
    row = geo.get(want, {})
    website = row.get("website_url", "") or cand.source_url

    allowed = WR.official_domains_for(website, args.allow_domain)
    expected = SR.ExpectedEntity(
        listing_key=cand.listing_key, listing_name=cand.name, address=cand.address,
        city=row.get("city", ""), state=row.get("state", ""),
        postal_code=row.get("postal_code", ""), phone=cand.phone, website_url=website)

    print("=== PTF-WORKERS-005 browser-rendered official-source retrieval ===")
    print("  model calls made           : 0")
    print("  spend                      : $0.00")
    print("  credential consulted       : none")
    print("  production data written    : none")
    print("  hotel                      : %s" % cand.name)
    print("  target URL                 : %s" % args.url)
    print("  official domain allowlist  : %s" % ", ".join(allowed))
    print("  posture                    : detect-and-classify; NO evasion of any kind")
    print("")

    if not args.live:
        print("  DRY RUN -- no browser was launched and no request was sent.")
        print("  Re-run with --live to perform the rendered capture.")
        return 0

    driver = PlaywrightBrowserDriver(headless=not args.headed)
    fetcher = BrowserPageFetcher(driver, allowed_domains=allowed,
                                 expand_content=not args.no_expand)
    store = PilotStore(Path(args.output_root) if args.output_root else None)
    cas = ArtifactStoreRepository(store.root / _C.CAS_SUBDIR)

    result = RC.capture_rendered_source(
        expected=expected, child_url=args.url, fetcher=fetcher, cas=cas,
        observed_at=args.observed_at,
        assignment_id="rend-%s" % cand.listing_key.replace(" ", "-")[:50])

    out = result.outcome
    print("  status                     : %s" % out.status)
    print("  identity                   : %s (basis=%s)" % (out.identity or "-", out.identity_basis))
    if result.parent_url:
        print("  parent page                : %s -> %s"
              % (result.parent_url, result.parent_identity or "-"))
    if result.inheritance_failures:
        print("  inheritance refused        : %s" % ", ".join(result.inheritance_failures))
    print("  final URL                  : %s" % (out.final_url or "-"))
    print("  redirect hops              : %d" % len(out.redirect_chain))
    print("  fetch status               : %s" % (out.importer_fetch_status or "-"))
    if out.failure_reason:
        print("  failure reason             : %s" % out.failure_reason)
    cap = result.child_capture
    if cap:
        print("")
        print("  raw_transport_hash         : %s" % (cap.raw_transport_hash or "-")[:32])
        print("  rendered_dom_hash          : %s" % (cap.rendered_dom_hash or "-")[:32])
        print("     (point-in-time attestation, NOT a reproducibility guarantee)")
        print("  normalized_text_hash       : %s" % (out.normalized_text_hash or "-")[:32])
        print("  normalized text bytes      : %d" % out.normalized_text_bytes)
        print("  render stability divergence: %.4f (stable=%s)"
              % (cap.stability_divergence, cap.stable))
        print("  consent banner detected    : %s" % cap.consent_banner_detected)
        print("  interactions performed     : %d" % len(cap.interactions))
    print("")
    print("  policy statements preserved (ALL matches, no first-match-wins):")
    for s in result.statements:
        print("     [%-20s @%6d] %s" % (s.topic, s.char_start, s.quote[:110]))
    if not result.statements:
        print("     (none)")
    if result.contradictions:
        print("")
        print("  CONTRADICTIONS PRESERVED (never resolved here):")
        for c in result.contradictions:
            print("     %s" % c)
    print("")
    print("  READY FOR EXTRACTION       : %s" % out.ready_for_extraction)
    if out.source_document is not None:
        print("  source_type                : %s" % out.source_document.source_type)

    store.write_per_hotel(RENDERED_RETRIEVAL, cand.listing_key.replace(" ", "-")[:60],
                          result.to_dict())
    print("  artifact                   : %s" % (store.root / RENDERED_RETRIEVAL))
    if args.json:
        print(_json.dumps(result.to_dict(), indent=2, sort_keys=True))
    return 0


def _cmd_web_research(args) -> int:
    """PTF-WORKERS-004: locate a property's official pet-policy page.

    ESCALATION ONLY. This command refuses to run for a hotel whose official
    page was already retrieved directly -- ``--after-retrieval`` must point at
    a retrieval artifact showing a genuine failure. Direct retrieval is free
    and produces stronger evidence, so paying a model to duplicate it is never
    the right move.

    Dry-run by default. The paid path additionally requires --live,
    --confirm-spend, the $5 web-research spend token, and a complete operator-
    supplied price list -- and it always prints the exact one-hotel maximum
    cost BEFORE the call is made.
    """
    import csv as _csv
    import json as _json

    from services.research_workers import research_escalation as ESC
    from services.research_workers import web_research as WR
    from services.research_workers.columbus_pilot import (
        DEFAULT_SEED, HOTEL_CATEGORY, WEB_RESEARCH, PilotStore,
        load_columbus_hotel_candidates, normalize_listing_key,
    )
    from services.research_workers.providers import (
        LiveAuthorization, web_research_spend_authorization_present,
    )

    candidates = load_columbus_hotel_candidates(args.seed)
    by_key = {normalize_listing_key(c.name): c for c in candidates}
    want = normalize_listing_key(args.hotel)
    if want not in by_key:
        sys.stderr.write("no such hotel in seed inventory: %r (never substitutes)\n" % args.hotel)
        return 2
    cand = by_key[want]

    geo = {}
    seed_path = Path(args.seed) if args.seed else DEFAULT_SEED
    with seed_path.open(encoding="utf-8") as fh:
        for row in _csv.DictReader(fh):
            if row.get("category") != HOTEL_CATEGORY:
                continue
            geo[normalize_listing_key(row.get("name", ""))] = row
    row = geo.get(want, {})
    website = row.get("website_url", "") or cand.source_url

    # ---- ESCALATION GATE (before anything else costs anything) ------------ #
    # utf-8-sig, not utf-8: this repo's own artifacts are BOM-free, but an
    # operator hand-writing the file on Windows gets a BOM by default and the
    # resulting failure ("Unexpected UTF-8 BOM") looks nothing like its cause.
    # utf-8-sig reads both.
    retrieval = _json.loads(Path(args.after_retrieval).read_text(encoding="utf-8-sig"))
    escalation_reason = ESC.require_escalation(retrieval, listing_key=cand.listing_key)

    allowed = WR.official_domains_for(website, args.allow_domain)
    caps = WR.WebResearchCaps(
        max_tool_calls=args.max_tool_calls, max_output_tokens=args.max_output_tokens,
        search_context_size=args.search_context_size, reasoning_effort=args.reasoning_effort,
        assumed_prompt_tokens=args.assumed_prompt_tokens,
        assumed_tokens_per_search_call=args.assumed_tokens_per_search_call,
        timeout_s=args.timeout, max_retries=args.max_retries)
    caps.validate()

    priced = (args.price_input_per_1k is not None and args.price_output_per_1k is not None)
    pricing = WR.WebResearchPricing(
        input_per_1k=args.price_input_per_1k or 0.0,
        output_per_1k=args.price_output_per_1k or 0.0,
        per_tool_call_usd=args.price_per_tool_call or 0.0) if priced else None
    # Tier selection is by COMPUTED cost among QUALIFIED tiers. Only the
    # flagship is qualified today, so it is what the ladder resolves to -- but
    # the selection runs for real, so the moment a cheaper tier is benchmarked
    # and priced it wins without a code change here.
    tier, max_cost = (ESC.select_research_tier(
        pricing_by_tier={ESC.TIER_FLAGSHIP.key: pricing}, caps=caps)
        if pricing is not None else (None, None))

    print("=== PTF-WORKERS-004 web research (Responses API + web_search) ===")
    print("  NOT OpenAI deep research   : dedicated deep-research models are 404 on this project")
    print("  ESCALATION ONLY            : %s" % escalation_reason)
    print("  prior retrieval status     : %s (ready_for_extraction=%s)"
          % (retrieval.get("status", "-"), retrieval.get("ready_for_extraction")))
    print("  hotel                      : %s" % cand.name)
    print("  seed website               : %s" % (website or "-"))
    print("  official domain allowlist  : %s" % (", ".join(allowed) or "(none)"))
    print("  selected tier              : %s" % (tier.key if tier else "(unpriced)"))
    print("  model                      : %s" % (tier.model if tier else WR.APPROVED_MODEL))
    print("  provenance of any output   : %s (never official evidence)"
          % V.SOURCE_MODEL_RESEARCH_REPORT)
    print("  routing cap                : forced REVIEW, never READY")
    print("")
    print("  -- provider ladder (cheapest qualified tier wins) --")
    for t in ESC.PROVIDER_LADDER:
        print("     %-26s %-18s %-18s %s"
              % (t.key, t.model, t.qualification, "SELECTABLE" if t.selectable else "blocked"))
    if ESC.PENDING_BENCHMARK_TIERS:
        print("     pending benchmark: %s"
              % ", ".join(t.model for t in ESC.PENDING_BENCHMARK_TIERS))
    print("")
    print("  -- server-enforced bounds --")
    print("  max_tool_calls             : %d" % caps.max_tool_calls)
    print("  max_output_tokens          : %d" % caps.max_output_tokens)
    print("  search_context_size        : %s" % caps.search_context_size)
    print("  -- assumed bound (no API parameter caps retrieved-context size) --")
    print("  assumed prompt tokens      : %d" % caps.assumed_prompt_tokens)
    print("  assumed tokens per search  : %d" % caps.assumed_tokens_per_search_call)
    print("  => worst-case input tokens : %d" % caps.max_input_tokens)
    print("")
    if pricing is None:
        print("  EXACT ONE-HOTEL MAX COST   : UNKNOWN -- no pricing supplied")
        print("     (pass --price-input-per-1k and --price-output-per-1k; this")
        print("      codebase never guesses a price, per pricing.py's standing rule)")
    else:
        print("  EXACT ONE-HOTEL MAX COST   : $%.2f" % max_cost)
        print("     input  %d tok @ $%.4f/1k = $%.4f"
              % (caps.max_input_tokens, pricing.input_per_1k,
                 caps.max_input_tokens / 1000.0 * pricing.input_per_1k))
        print("     output %d tok @ $%.4f/1k = $%.4f"
              % (caps.max_output_tokens, pricing.output_per_1k,
                 caps.max_output_tokens / 1000.0 * pricing.output_per_1k))
        print("     search %d calls @ $%.4f    = $%.4f"
              % (caps.max_tool_calls, pricing.per_tool_call_usd,
                 caps.max_tool_calls * pricing.per_tool_call_usd))
    print("  $5 spend token present     : %s" % web_research_spend_authorization_present())
    print("")

    if not (args.live and args.confirm_spend):
        print("  DRY RUN -- no request was sent, no credential was read, $0.00 spent.")
        print("  Re-run with --live --confirm-spend (plus prices) to execute.")
        if args.json:
            print(_json.dumps({"hotel": cand.name, "allowed_domains": list(allowed),
                               "exact_max_cost_usd": max_cost,
                               "escalation_reason": escalation_reason,
                               "ladder": ESC.ladder_report(),
                               "dry_run": True}, indent=2, sort_keys=True))
        return 0

    if pricing is None:
        raise SpendingAirlockError(
            "a live run requires --price-input-per-1k and --price-output-per-1k so the "
            "exact maximum cost is known before spending")

    if tier.model != WR.APPROVED_MODEL:
        # The ladder selected a tier this adapter cannot yet drive. Refusing is
        # correct: qualifying a cheaper model is a benchmark task, not a
        # silent substitution at call time.
        raise SpendingAirlockError(
            "tier %r selects model %r, which this adapter does not implement yet "
            "(approved: %r). Benchmark and wire the tier before selecting it."
            % (tier.key, tier.model, WR.APPROVED_MODEL))
    auth = LiveAuthorization(live=True, confirm_spend=True, provider="openai-web-research",
                             model=tier.model, api_key_env=args.api_key_env)
    provider, confirmed_max = WR.build_web_research_provider(
        auth, caps=caps, pricing=pricing)          # raises unless BOTH airlocks clear
    print("  airlocks cleared. authorized maximum for this ONE call: $%.2f" % confirmed_max)

    report = provider.research(
        listing_key=cand.listing_key, listing_name=cand.name, address=cand.address,
        city=row.get("city", ""), state=row.get("state", ""),
        allowed_domains=allowed, caps=caps, observed_at=args.observed_at)

    spent = WR.actual_cost_usd(report.usage, pricing)
    print("")
    print("  ok                         : %s" % report.ok)
    print("  request id                 : %s" % (report.request_id or "-"))
    print("  http status                : %s" % (report.http_status or "-"))
    print("  response status            : %s" % (report.response_status or "-"))
    if report.incomplete_reason:
        print("  INCOMPLETE                 : %s" % report.incomplete_reason)
    if not report.ok:
        print("  error                      : %s" % report.error)
    print("  searches performed         : %d (cap %d)"
          % (report.usage.search_calls, caps.max_tool_calls))
    print("  tokens in/out              : %d / %d"
          % (report.usage.input_tokens, report.usage.output_tokens))
    print("  ACTUAL METERED COST        : $%.6f  (ceiling was $%.2f)" % (spent, confirmed_max))
    print("  report text bytes          : %d" % len(report.report_text.encode("utf-8")))
    print("")
    print("  discovered official URLs (tool citations only, allowlist-checked):")
    for d in report.discovered_urls:
        print("     [%s] %s" % (d.origin, d.url))
    if not report.discovered_urls:
        print("     (none)")
    if report.rejected_urls:
        print("  rejected URLs:")
        for r in report.rejected_urls:
            print("     %s  <- %s" % (r["url"], r["reason"]))
    print("")
    print("  NEXT STEP (not performed here): feed a discovered URL to")
    print("    retrieve-official-sources, which fetches and hashes the real page.")
    print("    The report above is NOT evidence and cannot publish a fact.")

    if args.output_root or args.write:
        store = PilotStore(Path(args.output_root) if args.output_root else None)
        store.write_per_hotel(WEB_RESEARCH, cand.listing_key.replace(" ", "-")[:60],
                              report.to_dict())
        print("  artifact written under     : %s" % store.root)
    if args.json:
        print(_json.dumps(report.to_dict(), indent=2, sort_keys=True))
    return 0


def _cmd_manifest(args) -> int:
    from services.research_workers.manifest import validate_manifest, verify_evidence_sync
    sync = verify_evidence_sync(args.benchmark)
    gates = validate_manifest(args.benchmark)
    problems = sync + gates
    if problems:
        print("BENCHMARK MANIFEST/EVIDENCE-SYNC FAILED:")
        for p in problems:
            print("  - %s" % p)
        return 4
    print("benchmark manifest OK: 10 cases, evidence in sync with the tracked launch package, all gates pass")
    return 0


def _cmd_validate(args) -> int:
    if args.result:
        result = WorkerResult.from_dict(json.loads(Path(args.result).read_text(encoding="utf-8")))
        expected = result.compute_hash()
        ok = (result.result_hash == expected)
        out = {"assignment_id": result.assignment_id, "status": result.status,
               "supported_facts": sum(1 for f in result.proposed_facts if f.state == V.SUPPORTED),
               "contradictions": list(result.contradictions),
               "stored_hash": result.result_hash, "recomputed_hash": expected,
               "hash_ok": ok}
        print(json.dumps(out, sort_keys=True, ensure_ascii=False, indent=2))
        return 0 if ok else 2
    if args.assignment:
        assignment = Assignment.from_dict(json.loads(Path(args.assignment).read_text(encoding="utf-8")))
        provider = _build_provider(args)
        model = args.model or ("fake-extractor-v1" if provider.name == "fake" else "")
        result = run_assignment(assignment, provider, model=model, output_token_cap=args.output_token_cap,
                                timeout_s=args.timeout, max_retries=args.max_retries)
        if args.write_report:
            WorkerRepository(Path(args.output_root) if args.output_root else None).write_result(result)
        print(json.dumps(result.to_dict(), sort_keys=True, ensure_ascii=False, indent=2))
        return 0
    raise SpendingAirlockError("validate requires --result <path> or --assignment <path>")


def _cmd_capture_batch(args) -> int:
    """PTF-CAPTURE-003 Phase 1.

    Launches a dedicated, visible Chrome (never the operator's own profile),
    walks the queue, and writes captures plus a manifest. It does not attest,
    approve, promote or publish -- those stay human, per
    ADR-PTF-AUTOMATED-BROWSING.
    """
    from .browser_control import chrome_launcher
    from .browser_control.cdp_client import CdpConnection
    from .browser_control.live_session import LiveBrowserSession
    from .capture_automation.adapters import known_brands
    from .capture_automation.queue import QueueError, load_queue
    from .capture_automation.runner import CaptureRunner, RunnerConfig

    try:
        queue = load_queue(args.queue, known_brands=known_brands())
    except QueueError as exc:
        sys.stderr.write("queue preflight failed:\n%s\n" % exc)
        return 2

    print("queue OK: %d hotel(s), batch_id=%s" % (len(queue), queue.batch_id))
    if args.preflight_only:
        return 0

    batch_dir = Path(args.output)
    config = RunnerConfig(
        batch_dir=batch_dir,
        archived_corpus_dirs=tuple(args.archived_corpus or ()),
        limit=args.limit or 0,
        # PTF-DISCOVERY: previously declared on the parser and never passed
        # here, which made --resume a silent no-op.
        resume=bool(getattr(args, "resume", False)))

    profile_dir = batch_dir / ".chrome-profile"
    chrome = chrome_launcher.launch(
        user_data_dir=profile_dir, chrome_path=args.chrome_path,
        window_size=args.window_size)
    print("chrome up on port %d (dedicated profile, visible window)" % chrome.port)

    session = None
    try:
        # Attach to the tab Chrome opened at startup. Its debugger URL comes
        # from Chrome's own target list, never from string surgery on the
        # browser socket's address.
        session = LiveBrowserSession(
            CdpConnection(chrome_launcher.page_websocket_url(chrome.port)))

        result = CaptureRunner(session, config).run(queue)
    finally:
        if session is not None:
            session.close()
        chrome.stop()

    counts = result.manifest["counts"]
    if args.json:
        print(json.dumps(result.manifest, indent=2, ensure_ascii=False))
    else:
        print("\nbatch %s" % queue.batch_id)
        rs = result.manifest.get("resume") or {}
        if rs.get("resume_requested"):
            rc = rs.get("counts", {})
            print("  resume     : %d total, %d already complete (skipped), "
                  "%d attempted, %d need manual review"
                  % (rc.get("total_candidates", 0), rc.get("skipped_completed", 0),
                     rc.get("attempted", 0), rc.get("manual_review", 0)))
        print("  captured   : %d" % counts["captured"])
        print("  exceptions : %d" % counts["exceptions"])
        if counts.get("confirmed_policy_absence"):
            # Printed under exceptions, indented, because it IS a subset of
            # them -- no capture was produced. Surfaced anyway so the headline
            # failure count is not read as N adapter defects.
            print("    of which pets-not-accepted (page says so) : %d"
                  % counts["confirmed_policy_absence"])
        print("  duplicates : %d" % counts["duplicates"])
        print("  skipped    : %d" % counts["skipped"])
        print("  unattended : %.0f%%" % (result.manifest["unattended_success_rate"] * 100))
        if result.aborted_reason:
            print("  ABORTED    : %s" % result.aborted_reason)
        for reason, n in sorted(result.manifest["exceptions_by_reason"].items()):
            print("    %-32s %d" % (reason, n))
        print("  manifest   : %s" % result.manifest_path)
        print("\nNothing has been attested, approved, promoted or published.")
    return 0


def _add_common(p: argparse.ArgumentParser) -> None:
    p.add_argument("--provider", default="fake", help="fake (offline default) | openai")
    p.add_argument("--model", default="")
    p.add_argument("--live", action="store_true", help="authorize a paid/live provider")
    p.add_argument("--confirm-spend", action="store_true", help="second required live confirmation")
    p.add_argument("--api-key-env", default="OPENAI_API_KEY",
                   help="env var holding the credential (value is never logged)")
    p.add_argument("--output-token-cap", type=int, default=V.DEFAULT_OUTPUT_TOKEN_CAP)
    p.add_argument("--timeout", type=float, default=V.DEFAULT_TIMEOUT_SECONDS)
    p.add_argument("--max-retries", type=int, default=V.DEFAULT_MAX_RETRIES)
    p.add_argument("--max-assignments", type=int, default=None)
    p.add_argument("--max-total-input-tokens", type=int, default=None)
    p.add_argument("--max-total-output-tokens", type=int, default=None)
    p.add_argument("--max-estimated-cost", type=float, default=None)
    p.add_argument("--output-root", default=None, help="worker runtime root (gitignored)")
    p.add_argument("--write-report", action="store_true")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="services.research_workers", description=__doc__)
    sub = parser.add_subparsers(dest="command", required=True)

    b = sub.add_parser("benchmark", help="run the ten-hotel benchmark")
    _add_common(b)
    b.add_argument("--benchmark", default=None, help="benchmark JSON path (default: committed Columbus)")
    b.add_argument("--pricing", default=None, help="pricing JSON (provider/model -> per-1k rates)")
    b.add_argument("--json", action="store_true", help="print the full JSON report")
    b.set_defaults(func=_cmd_benchmark)

    v = sub.add_parser("validate", help="integrity-check a stored result, or run one assignment")
    _add_common(v)
    v.add_argument("--result", default=None, help="path to a stored WorkerResult JSON")
    v.add_argument("--assignment", default=None, help="path to an Assignment JSON to run (fake by default)")
    v.set_defaults(func=_cmd_validate)

    m = sub.add_parser("manifest", help="validate the benchmark manifest + evidence sync (offline)")
    m.add_argument("--benchmark", default=None, help="benchmark JSON path (default: committed Columbus)")
    m.set_defaults(func=_cmd_manifest)

    e = sub.add_parser("evaluate", help="live low-cost model bakeoff (ATLAS-WORKERS-002); dry-run without --live")
    _add_common(e)
    e.add_argument("--benchmark", default=None, help="benchmark JSON path (default: committed Columbus)")
    e.add_argument("--repetitions", type=int, default=3)
    e.add_argument("--case-id", default=None,
                   help="run exactly ONE named benchmark case (e.g. 01_rich_dogs_and_cats "
                        "or its alias bench-01_rich_dogs_and_cats); never substitutes")
    e.set_defaults(func=_cmd_evaluate)

    c = sub.add_parser("canary", help="ONE live adapter canary call (same adapter + parser as the benchmark)")
    c.add_argument("--provider", required=True)
    c.add_argument("--model", required=True)
    c.add_argument("--live", action="store_true", help="authorize the single paid call")
    c.add_argument("--confirm-spend", action="store_true", help="second required confirmation")
    c.add_argument("--output-token-cap", type=int, default=256)
    c.add_argument("--timeout", type=float, default=60.0)
    c.add_argument("--max-retries", type=int, default=0)
    c.set_defaults(func=_cmd_canary)

    r = sub.add_parser("route", help="route validated worker results (ATLAS-WORKERS-003; offline, dry-run default)")
    r.add_argument("--benchmark", default=None, help="benchmark JSON path (default: committed Columbus)")
    r.add_argument("--assignment-id", default=None,
                   help="route exactly ONE case (id or bench- alias); never substitutes")
    r.add_argument("--write", action="store_true",
                   help="persist envelopes to the gitignored routing queue (default: dry-run)")
    r.add_argument("--output-root", default=None, help="worker runtime root (gitignored)")
    r.add_argument("--prompt-version", default="", help="override recorded prompt_version (default: current)")
    r.add_argument("--validator-version", default="", help="override recorded validator_version (default: current)")
    r.add_argument("--observed-at", default="", help="explicit observation timestamp (no clock is read)")
    r.add_argument("--run-id", default="", help="optional run correlation id")
    r.add_argument("--json", action="store_true", help="print full JSON (summary + envelopes)")
    r.set_defaults(func=_cmd_route)

    cp = sub.add_parser("columbus-hotel-pilot",
                        help="ATLAS-WORKERS-004 Columbus/Dublin hotel live intake pilot (dry-run default)")
    cp.add_argument("--seed", default=None, help="seed inventory CSV (default: committed pettripfinder seed)")
    cp.add_argument("--live", action="store_true", help="authorize live Nano calls (needs --confirm-spend + spend token)")
    cp.add_argument("--confirm-spend", action="store_true", help="second required live confirmation")
    cp.add_argument("--report", action="store_true",
                    help="read previously written pilot artifacts and print the summary (no calls)")
    cp.add_argument("--max-assignments", type=int, default=None, help="cap the number of live assignments")
    cp.add_argument("--assignment-filter", default=None,
                    help="run exactly ONE hotel (name or listing key); never substitutes")
    cp.add_argument("--output-token-cap", type=int, default=1024)
    cp.add_argument("--max-retries", type=int, default=1)
    cp.add_argument("--timeout", type=float, default=60.0)
    cp.add_argument("--max-estimated-cost", type=float, default=1.00)
    cp.add_argument("--observed-at", default="", help="explicit observation timestamp (no clock is read)")
    cp.add_argument("--run-id", default="", help="optional run correlation id")
    cp.add_argument("--output-root", default=None, help="gitignored pilot root (default under data/worker_runs)")
    cp.add_argument("--json", action="store_true", help="print full JSON")
    cp.set_defaults(func=_cmd_columbus_pilot)

    # PTF-WORKERS-003 -- official-source retrieval. Deliberately a SEPARATE
    # subcommand from the model pilot: retrieval is free, credential-free and
    # airlock-free by construction, so it must not sit behind (or accidentally
    # trigger) the paid path.
    ret = sub.add_parser(
        "retrieve-official-sources",
        help="PTF-WORKERS-003 fetch official hotel pages into SourceDocuments "
             "(retrieval only; zero model calls, no API key, no spend)")
    ret.add_argument("--seed", default=None,
                     help="seed inventory CSV (default: committed pettripfinder seed)")
    ret.add_argument("--hotel", action="append", default=[], required=True,
                     help="exact hotel name or listing key; repeatable; never substitutes")
    ret.add_argument("--retrieve-only", action="store_true", default=True,
                     help="(default, and currently the only mode) fetch + verify, no model call")
    ret.add_argument("--observed-at", required=True,
                     help="explicit observation date (no clock is read)")
    ret.add_argument("--output-root", default=None,
                     help="gitignored pilot root (default under data/worker_runs)")
    ret.add_argument("--offline-fixture", action="append", default=[],
                     help="URL=path fixture for deterministic offline runs; repeatable")
    ret.add_argument("--json", action="store_true", help="print full JSON")
    ret.add_argument("--source-url", default="",
                     help="fetch this URL instead of the seed's source_url; "
                          "single --hotel only. For properties whose seed "
                          "source_url points at a brand page rather than the "
                          "property's own.")
    ret.add_argument("--rendered-evidence", default="",
                     help="PTF-CAPTURE-004A: path to a capture JSON whose "
                          "recorded policy text is deterministic evidence of "
                          "what the page shows once rendered. Single --hotel "
                          "only. Can only ever move RETRIEVED to "
                          "RENDER_REQUIRED, and only when all six conditions "
                          "in render_evidence hold.")
    ret.set_defaults(func=_cmd_retrieve_official_sources)

    # PTF-WORKERS-004 -- web research (Responses API + web_search on gpt-5.4).
    # A separate subcommand behind a separate $5 airlock. Deliberately NOT
    # folded into the model pilot or the retrieval command: retrieval must stay
    # free and credential-free, and the pilot's $1 gate must stay $1.
    wr = sub.add_parser(
        "web-research",
        help="PTF-WORKERS-004 find a hotel's official pet-policy URL via web "
             "search grounding (dry-run default; NOT OpenAI deep research)")
    wr.add_argument("--seed", default=None, help="seed inventory CSV (default: committed seed)")
    wr.add_argument("--hotel", required=True,
                    help="exact hotel name or listing key; never substitutes")
    wr.add_argument("--allow-domain", action="append", default=[],
                    help="additional official domain to permit (e.g. ihg.com); repeatable")
    wr.add_argument("--after-retrieval", required=True,
                    help="path to this hotel's retrieval artifact from "
                         "retrieve-official-sources. ESCALATION ONLY: the run is "
                         "refused unless that artifact shows direct retrieval failed")
    wr.add_argument("--live", action="store_true", help="authorize the single paid call")
    wr.add_argument("--confirm-spend", action="store_true", help="second required confirmation")
    wr.add_argument("--api-key-env", default="OPENAI_API_KEY",
                    help="env var holding the credential (value is never logged)")
    wr.add_argument("--max-tool-calls", type=int, default=4, help="server-enforced search cap")
    wr.add_argument("--max-output-tokens", type=int, default=3000)
    wr.add_argument("--search-context-size", default="medium", choices=list(_WR_CONTEXT_SIZES))
    wr.add_argument("--reasoning-effort", default="medium", choices=list(_WR_EFFORTS))
    wr.add_argument("--assumed-prompt-tokens", type=int, default=1500)
    wr.add_argument("--assumed-tokens-per-search-call", type=int, default=12000)
    wr.add_argument("--price-input-per-1k", type=float, default=None,
                    help="USD per 1k input tokens (required for --live; never guessed)")
    wr.add_argument("--price-output-per-1k", type=float, default=None,
                    help="USD per 1k output tokens (required for --live; never guessed)")
    wr.add_argument("--price-per-tool-call", type=float, default=0.0,
                    help="USD per web_search call, if the operator's plan charges one")
    wr.add_argument("--timeout", type=float, default=300.0)
    wr.add_argument("--max-retries", type=int, default=0)
    wr.add_argument("--observed-at", default="", help="explicit observation date (no clock is read)")
    wr.add_argument("--output-root", default=None, help="gitignored artifact root")
    wr.add_argument("--write", action="store_true", help="persist the report artifact")
    wr.add_argument("--json", action="store_true", help="print full JSON")
    wr.set_defaults(func=_cmd_web_research)

    # PTF-WORKERS-005 -- browser-rendered retrieval. Like the static retrieval
    # command this is free, credential-free and airlock-free by construction:
    # it builds no provider, so no paid path can be reached from here.
    rr = sub.add_parser(
        "retrieve-rendered",
        help="PTF-WORKERS-005 browser-render ONE official URL into hash-bound "
             "evidence (dry-run default; zero model calls, no API key, no spend)")
    rr.add_argument("--seed", default=None, help="seed inventory CSV (default: committed seed)")
    rr.add_argument("--hotel", required=True, help="exact hotel name or listing key")
    rr.add_argument("--url", required=True, help="exact official URL to render")
    rr.add_argument("--allow-domain", action="append", default=[],
                    help="additional official domain to permit; repeatable")
    rr.add_argument("--live", action="store_true",
                    help="actually launch the browser (dry-run without it)")
    rr.add_argument("--headed", action="store_true", help="run Chromium headed (debugging)")
    rr.add_argument("--no-expand", action="store_true",
                    help="skip bounded accordion expansion")
    rr.add_argument("--observed-at", required=True,
                    help="explicit observation date (no clock is read)")
    rr.add_argument("--output-root", default=None, help="gitignored artifact root")
    rr.add_argument("--json", action="store_true", help="print full JSON")
    rr.set_defaults(func=_cmd_retrieve_rendered)

    # PTF-WORKERS-006 -- manual official attestation. Two SEPARATE commands,
    # because attesting and approving are two separate human decisions.
    at = sub.add_parser(
        "attest-official-page",
        help="PTF-WORKERS-006 record a PENDING operator attestation for a page "
             "Atlas cannot retrieve (no network, no model call, no spend)")
    at.add_argument("--seed", default=None)
    at.add_argument("--hotel", required=True)
    at.add_argument("--capture", required=True,
                    help="operator page-capture JSON (ptf-official-capture/1.0); "
                         "with --identity-capture this is the POLICY capture")
    at.add_argument("--identity-capture", default="",
                    help="PTF-WORKERS-007 paired evidence: property-page capture "
                         "JSON proving identity, when the policy was read from an "
                         "official search surface. Routes REVIEW and needs an "
                         "explicit APPROVED_PAIRED_OFFICIAL_SOURCE approval.")
    at.add_argument("--screenshot", action="append", default=[], required=True,
                    help="screenshot image path; repeatable; at least one required")
    at.add_argument("--after-retrieval", required=True,
                    help="artifact proving automated retrieval failed")
    at.add_argument("--operator-id", required=True,
                    help="stable non-sensitive handle of the person who captured")
    at.add_argument("--attested-at", required=True)
    at.add_argument("--observed-at", required=True)
    at.add_argument("--timezone", required=True, help="observation timezone, e.g. America/New_York")
    at.add_argument("--address-confirmed", action="store_true")
    at.add_argument("--address-observed", default="")
    at.add_argument("--phone-confirmed", action="store_true")
    at.add_argument("--phone-observed", default="")
    at.add_argument("--alternate-url", action="append", default=[])
    at.add_argument("--model-research", default=None,
                    help="prior web-research artifact to REFERENCE (never a content source)")
    at.add_argument("--output-root", default=None)
    at.add_argument("--json", action="store_true")
    at.set_defaults(func=_cmd_attest_official_page)

    ap = sub.add_parser(
        "approve-attestation",
        help="PTF-WORKERS-006 explicitly approve (or reject) a PENDING attestation")
    ap.add_argument("--attestation", required=True, help="path to the attestation artifact")
    ap.add_argument("--approver-id", required=True,
                    help="stable non-sensitive handle of the approver")
    ap.add_argument("--approved-at", required=True)
    ap.add_argument("--record-id", required=True, help="approval record id")
    ap.add_argument("--reject", action="store_true", help="record a rejection instead")
    ap.add_argument("--output-root", default=None,
                    help="gitignored artifact root; the attestation MUST live "
                         "under its attestations/ subdir")
    ap.add_argument("--rationale", default="",
                    help="why this decision was made; recorded on the approval "
                         "so grounds that override a recorded observation stay "
                         "auditable")
    ap.set_defaults(func=_cmd_approve_attestation)

    rc = sub.add_parser(
        "resolve-contradiction",
        help="PTF-APPROVAL-RESOLUTION dispose of named contradiction markers on "
             "one APPROVED attestation (never removes them; never weakens the "
             "detector)")
    rc.add_argument("--attestation", required=True, help="path to the artifact")
    rc.add_argument("--family", action="append", required=True,
                    choices=list(__import__(
                        "services.research_workers.approval_resolution",
                        fromlist=["x"]).RESOLVABLE_FAMILIES),
                    help="marker family to resolve; repeatable")
    rc.add_argument("--disposition", required=True,
                    choices=list(__import__(
                        "services.research_workers.approval_resolution",
                        fromlist=["x"]).DISPOSITIONS))
    rc.add_argument("--approver-id", required=True)
    rc.add_argument("--resolved-at", required=True)
    rc.add_argument("--rationale", default="")
    rc.add_argument("--rationale-file", default="",
                    help="read the rationale from a file instead")
    rc.add_argument("--output-root", default=None)
    rc.set_defaults(func=_cmd_resolve_contradiction)

    cb = sub.add_parser(
        "capture-batch",
        help="PTF-CAPTURE-003 drive a visible Chrome through a queue of official "
             "property pages, capturing each (never attests, approves or publishes)")
    cb.add_argument("--queue", required=True, help="ptf-capture-queue/1.0 JSON path")
    cb.add_argument("--output", required=True, help="batch directory (gitignored)")
    cb.add_argument("--chrome-path", default="", help="explicit chrome.exe path")
    cb.add_argument("--limit", type=int, default=0, help="stop after N hotels")
    cb.add_argument("--resume", action="store_true",
                    help="skip hotels that already have a terminal journal record")
    cb.add_argument("--archived-corpus", action="append", default=[],
                    help="prior capture directory for cross-batch duplicate detection; "
                         "repeatable")
    cb.add_argument("--window-size", default="1440,1000")
    cb.add_argument("--preflight-only", action="store_true",
                    help="validate the queue and exit; never launches Chrome")
    cb.add_argument("--json", action="store_true")
    cb.set_defaults(func=_cmd_capture_batch)
    return parser


def main(argv=None) -> int:
    args = build_parser().parse_args(argv)
    try:
        return args.func(args)
    except SpendingAirlockError as exc:
        sys.stderr.write("airlock: %s\n" % exc)
        return 3


if __name__ == "__main__":
    raise SystemExit(main())
