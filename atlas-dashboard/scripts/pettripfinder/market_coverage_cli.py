"""PTF-MARKET-FACTORY-COVERAGE-HARDENING-001 -- the coverage-completion artifact.

    python scripts/pettripfinder/market_coverage_cli.py \
      --market louisville-ky --url-overlay <url_recovery.json> \
      --acquisition <acquisition_merged.json> --last-pass <paid_pass.json> \
      --closure <closure_ledger.json> --packet <founder_review_packet.json> \
      --url-recovery <url_recovery.json> --declined-recovery <zero_cost.json> \
      --stage founder_review_packet --as-of 2026-08-25 \
      --work-order PTF-... --out <coverage.json>

Derives one ``ptf-market-coverage-completion/1.0`` document from the artifacts
the other generic tools already write. Nothing here fetches, spends, or decides;
it reads what the factory produced and says whether the factory is finished.

WHERE EACH NUMBER COMES FROM
----------------------------
    census, eligibility      the committed census, through market_closure_cli's
                             own eligibility rule (one rule, not two)
    routing                  market_routing over the census WITH the overlay the
                             paid pass routed with -- the same defect Louisville
                             found in closure and the benchmark
    attempted / settled      the merged acquisition view (every pass folded)
    retry classification     retry_policy over the cohort derive_cohort builds,
                             so this artifact and the paid pass agree on which
                             rows are suppressed
    budget deferral          the last paid pass's own deferred list, and only
                             when that pass stopped on money or telemetry
    candidates               the founder-review packet when it exists, else the
                             closure ledger's HELD_REVIEW rows, else the store
    closure reconciliation   the closure ledger's own set comparison

The document is rebuilt at three stages -- coverage exhaustion, closure, and
founder-review packet -- and each rebuild says which stage it is.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, OrderedDict
from pathlib import Path
from typing import Dict, List, Mapping, Optional, Sequence, Set

_REPO_ROOT = Path(__file__).resolve().parent.parent.parent
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder import census_partition_builder as CPB
from scripts.pettripfinder import market_closure_cli as CC
from scripts.pettripfinder.acquisition import market_paid_acquisition as PA
from scripts.pettripfinder.acquisition import market_routing as MR
from scripts.pettripfinder.acquisition import retry_policy as RP
from scripts.pettripfinder.brightdata import outcomes as O
from scripts.pettripfinder.contracts import closure as CL
from scripts.pettripfinder.contracts import coverage as COV

PACKAGE_DIR = _REPO_ROOT / "launch_packages" / "pettripfinder"
CENSUS_DIR = PACKAGE_DIR / "identity_census"

STAGE_COVERAGE_EXHAUSTION = "coverage_exhaustion"
STAGE_CLOSURE = "closure"
STAGE_FOUNDER_REVIEW_PACKET = "founder_review_packet"
STAGES = (STAGE_COVERAGE_EXHAUSTION, STAGE_CLOSURE, STAGE_FOUNDER_REVIEW_PACKET)

PUBLICATION_GRADE_CONFIRMED = "PUBLICATION_GRADE_CONFIRMED"


def _load(path: Optional[str]) -> Optional[Dict]:
    if not path:
        return None
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def candidate_keys(*, packet: Optional[Mapping], closure: Optional[Mapping],
                   store: Optional[Mapping]) -> Optional[Set[str]]:
    """Which identities are founder candidates, or ``None`` when nobody has
    evaluated that yet. The packet is authoritative; closure's HELD_REVIEW rows
    and the store's confirmed grades are the same population one step earlier."""
    if packet is not None:
        return {c["identity_key"] for c in (packet.get("candidates") or ())}
    if closure is not None:
        return {r["identity_key"] for r in (closure.get("rows") or ())
                if r.get("disposition") == CL.HELD_REVIEW}
    if store is not None:
        return {r["identity_key"] for r in (store.get("records") or ())
                if (r.get("publication_grade") or {}).get("verdict")
                == PUBLICATION_GRADE_CONFIRMED}
    return None


def recovery_evidence(*, url_recovery: Optional[Mapping],
                      declined_recovery: Optional[Mapping],
                      pass_run_dirs: Sequence[str],
                      recovery_after_last_pass: bool) -> Dict:
    """Whether every free source of URLs and evidence has actually been asked.

    Exhaustion is a claim about what was RUN, not about what was found: a URL
    recovery that offered two binding keys and refused to look at unroutable
    census URLs has not exhausted the evidence, however many URLs it found.
    """
    keys = list((url_recovery or {}).get("binding_keys_offered") or ())
    url_ran = url_recovery is not None
    url_full_strength = bool(
        url_ran and url_recovery.get("url_corroboration_required")
        and url_recovery.get("unroutable_census_urls_included")
        and "STREET_AND_POSTAL_CODE" in keys)
    covered = set((declined_recovery or {}).get("run_dirs") or ())
    wanted = {Path(d).as_posix() for d in pass_run_dirs if d}
    declined_ran_over_every_pass = (not wanted) or (
        declined_recovery is not None
        and wanted <= {Path(d).as_posix() for d in covered})
    post_pass_ok = (not wanted) or bool(recovery_after_last_pass)
    exhausted = bool(url_full_strength and declined_ran_over_every_pass
                     and post_pass_ok)
    return OrderedDict((
        ("url_recovery_ran", url_ran),
        ("url_recovery_full_strength", url_full_strength),
        ("url_recovery_binding_keys", keys),
        ("url_recovery_recovered", int((url_recovery or {}).get("recovered") or 0)),
        ("url_recovery_still_unknown",
         int((url_recovery or {}).get("still_unknown") or 0)),
        ("declined_recovery_ran", declined_recovery is not None),
        ("declined_recovery_run_dirs", sorted(covered)),
        ("acquisition_run_dirs", sorted(wanted)),
        ("declined_recovery_covers_every_pass", declined_ran_over_every_pass),
        ("url_recovery_after_last_pass", post_pass_ok),
        ("ZERO_COST_RECOVERY_EXHAUSTED", exhausted),
    ))


def build(market_id: str, census: Mapping, *, prior: Mapping,
          overlay: Mapping, last_pass: Optional[Mapping] = None,
          closure: Optional[Mapping] = None, packet: Optional[Mapping] = None,
          store: Optional[Mapping] = None,
          url_recovery: Optional[Mapping] = None,
          declined_recovery: Optional[Mapping] = None,
          recovery_after_last_pass: bool = False,
          pass_run_dirs: Sequence[str] = (),
          overrides: Optional[Mapping[str, Mapping]] = None,
          stage: str, work_order: str, as_of: str,
          registry_doc: Optional[Mapping] = None) -> Dict:
    """The coverage-completion document. ``census["hotels"]`` must already
    carry the overlay (``MR.apply_url_overlay`` mutates in place; ``overlay``
    is its report)."""
    if stage not in STAGES:
        raise COV.CoverageError("unknown evaluation stage %r" % stage)
    rows = census["hotels"]
    entries, routing_summary = MR.route_census(rows, registry_doc)
    routing_by_key = {e["identity_key"]: e for e in entries}
    prior_by_key = {r["identity_key"]: r for r in (prior.get("results") or ())}

    cohort, settled = PA.derive_cohort(entries, prior)
    eligible, suppressed = RP.apply(cohort, prior, overrides=overrides)
    eligible_by_key = {r["identity_key"]: r for r in eligible}
    suppressed_keys = {r["identity_key"] for r in suppressed}
    family_by_key = {r["identity_key"]: r["family"] for r in cohort + settled}

    budget_stopped = bool(last_pass and last_pass.get("outcome")
                          in COV.BUDGET_STOP_OUTCOMES)
    deferred = {(d if isinstance(d, str) else d.get("identity_key"))
                for d in ((last_pass or {}).get("deferred") or ())}
    tripped = {t.get("family") for t in
               ((last_pass or {}).get("family_breakers_tripped") or ())}
    newly_routable = {r["identity_key"] for r in (overlay.get("rows") or ())}

    candidates = candidate_keys(packet=packet, closure=closure, store=store)
    candidates_evaluated = candidates is not None
    recovery = recovery_evidence(
        url_recovery=url_recovery, declined_recovery=declined_recovery,
        pass_run_dirs=pass_run_dirs,
        recovery_after_last_pass=recovery_after_last_pass)
    recovery_exhausted = recovery["ZERO_COST_RECOVERY_EXHAUSTED"]

    out_rows: List[Dict] = []
    active_keys: List[str] = []
    for census_row in rows:
        key = census_row["identity_key"]
        name = census_row.get("canonical_name", "")
        eligibility, why = CC.eligibility(census_row)
        routing = routing_by_key[key]
        base = dict(routing_state=routing["routing_state"],
                    source_url=routing.get("source_url", ""),
                    brand=routing.get("brand", ""),
                    corridor=census_row.get("corridor", ""))
        if eligibility != CC.ACTIVE:
            out_rows.append(COV.row(
                identity_key=key, canonical_name=name,
                coverage_state=COV.NOT_ACTIVE, next_state=COV.NEXT_CENSUS_REVIEW,
                why=why, eligibility=eligibility, **base))
            continue
        active_keys.append(key)
        state = routing["routing_state"]
        if state != MR.ROUTED:
            unrouted = {
                MR.ROUTE_NEEDS_OFFICIAL_URL:
                    (COV.UNROUTED_NEEDS_OFFICIAL_URL, COV.NEXT_OFFICIAL_URL),
                MR.ROUTE_NEEDS_PROPERTY_URL:
                    (COV.UNROUTED_NEEDS_PROPERTY_URL, COV.NEXT_PROPERTY_URL),
                MR.ROUTE_NEEDS_FIRST_PARTY_URL:
                    (COV.UNROUTED_NEEDS_FIRST_PARTY_URL, COV.NEXT_FIRST_PARTY_URL),
                MR.ROUTE_BRAND_EXCLUDED:
                    (COV.UNROUTED_BRAND_EXCLUDED, COV.NEXT_ROUTE_REGISTRY_DECISION),
            }[state]
            coverage_state, terminal_next = unrouted
            if (coverage_state != COV.UNROUTED_BRAND_EXCLUDED
                    and not recovery_exhausted):
                next_state = COV.NEXT_RUN_ZERO_COST_RECOVERY
                reason = ("%s; zero-cost recovery has not been run to "
                          "exhaustion, so the factory still owes this row a "
                          "free look" % routing["why"])
            else:
                next_state = terminal_next
                reason = routing["why"]
            out_rows.append(COV.row(
                identity_key=key, canonical_name=name,
                coverage_state=coverage_state, next_state=next_state,
                why=reason, **base))
            continue

        prior_row = prior_by_key.get(key) or {}
        outcome = prior_row.get("outcome", "")
        provider = prior_row.get("provider", "")
        if outcome == O.VALID:
            if not candidates_evaluated:
                cov, nxt, reason = (
                    COV.SETTLED_VALID_GRADE_PENDING, COV.NEXT_FOUNDER_DECISION,
                    "the page served and was read (%s); publication grade has "
                    "not been evaluated at this stage" % provider)
            elif key in candidates:
                cov, nxt, reason = (
                    COV.SETTLED_FOUNDER_CANDIDATE, COV.NEXT_FOUNDER_DECISION,
                    "a publication-grade observation exists; the founder decides")
            else:
                cov, nxt, reason = (
                    COV.SETTLED_VALID_NOT_PUBLICATION_GRADE,
                    COV.NEXT_POLICY_ARTIFACT,
                    "the page served and was read (%s) but the capture is not "
                    "publication grade" % provider)
        elif outcome == O.POLICY_NOT_FOUND:
            cov, nxt, reason = (
                COV.SETTLED_POLICY_NOT_FOUND, COV.NEXT_NONE_PAGE_SILENT,
                "the property's own page served and states nothing about pets "
                "as read by %s" % (provider or "the lane that fetched it"))
        elif outcome == O.IDENTITY_MISMATCH:
            cov, nxt, reason = (
                COV.SETTLED_IDENTITY_MISMATCH, COV.NEXT_ROUTING_REPAIR,
                "the page reached names a different property; routing repair "
                "before any lane is spent again")
        elif key in suppressed_keys:
            cov, nxt = COV.ROUTED_ALTERNATE_LANE_REQUIRED, COV.NEXT_ALTERNATE_LANE
            reason = next(r["retry_why"] for r in suppressed
                          if r["identity_key"] == key)
        elif budget_stopped and key in deferred:
            cov, nxt, reason = (
                COV.ROUTED_BUDGET_DEFERRED, COV.NEXT_BUDGET_AUTHORIZATION,
                "routed and in the last cohort; the last pass stopped (%s) "
                "before reaching it" % last_pass.get("outcome"))
        elif family_by_key.get(key) in tripped and key in deferred:
            cov, nxt, reason = (
                COV.ROUTED_ALTERNATE_LANE_REQUIRED, COV.NEXT_ALTERNATE_LANE,
                "skipped by the family breaker: the first properties of %s all "
                "failed identically on the approved lane, which is a "
                "capability wall, not a budget stop" % family_by_key.get(key))
        else:
            row = eligible_by_key.get(key) or {}
            if row.get("retry_classification") == RP.RETRY_ALLOWED_ALTERNATE_LANE:
                cov, nxt = (COV.ROUTED_ALTERNATE_LANE_AVAILABLE,
                            COV.NEXT_RUN_ALTERNATE_LANE)
                reason = row.get("retry_why", "")
            else:
                cov, nxt = COV.ROUTED_NEVER_ATTEMPTED, COV.NEXT_RUN_ACQUISITION
                reason = (row.get("retry_why")
                          or "routed to an approved lane and not yet attempted")
                if outcome:
                    reason = ("prior attempt answered nothing (%s); %s"
                              % (outcome, reason))
        out_rows.append(COV.row(
            identity_key=key, canonical_name=name, coverage_state=cov,
            next_state=nxt, why=reason, acquisition_outcome=outcome,
            provider=provider,
            retry_classification=(eligible_by_key.get(key) or {}).get(
                "retry_classification", ""), **base))

    by_state = Counter(r["coverage_state"] for r in out_rows)
    by_next = Counter(r["next_state"] for r in out_rows)
    routed = sum(1 for e in entries if e["routing_state"] == MR.ROUTED)
    attempted = sum(1 for k in routing_by_key if k in prior_by_key
                    and prior_by_key[k].get("outcome"))
    settled_count = sum(1 for k in routing_by_key
                        if prior_by_key.get(k, {}).get("outcome")
                        in PA.DEFAULT_TERMINAL)
    valid = sum(1 for k in routing_by_key
                if prior_by_key.get(k, {}).get("outcome") == O.VALID)
    publication_grade = (len(candidates) if candidates is not None else 0)
    counts: Dict[str, int] = OrderedDict((
        ("CENSUS", len(rows)),
        ("ROUTED", routed),
        ("UNROUTED", len(rows) - routed),
        ("ATTEMPTED", attempted),
        ("VALID", valid),
        ("SETTLED", settled_count),
        ("UNSETTLED", attempted - settled_count),
        ("NEEDS_OFFICIAL_URL", by_state[COV.UNROUTED_NEEDS_OFFICIAL_URL]),
        ("NEEDS_PROPERTY_URL", by_state[COV.UNROUTED_NEEDS_PROPERTY_URL]),
        ("BRAND_EXCLUDED", by_state[COV.UNROUTED_BRAND_EXCLUDED]),
        ("BUDGET_DEFERRED", by_state[COV.ROUTED_BUDGET_DEFERRED]),
        ("ALTERNATE_LANE_REQUIRED", by_state[COV.ROUTED_ALTERNATE_LANE_REQUIRED]),
        ("FOUNDER_CANDIDATES", publication_grade),
        ("NEEDS_FIRST_PARTY_URL", by_state[COV.UNROUTED_NEEDS_FIRST_PARTY_URL]),
        ("NOT_ACTIVE", by_state[COV.NOT_ACTIVE]),
        ("ROUTED_NEVER_ATTEMPTED", by_state[COV.ROUTED_NEVER_ATTEMPTED]),
        ("ALTERNATE_LANE_AVAILABLE", by_state[COV.ROUTED_ALTERNATE_LANE_AVAILABLE]),
        ("PUBLICATION_GRADE", publication_grade),
        ("POLICY_NOT_FOUND", by_state[COV.SETTLED_POLICY_NOT_FOUND]),
        ("IDENTITY_MISMATCH", by_state[COV.SETTLED_IDENTITY_MISMATCH]),
        ("VALID_NOT_PUBLICATION_GRADE",
         by_state[COV.SETTLED_VALID_NOT_PUBLICATION_GRADE]),
        ("NEWLY_ROUTABLE_BY_URL_RECOVERY", len(newly_routable)),
        ("SAME_LANE_RETRIES_SUPPRESSED", len(suppressed)),
    ))

    factory_rows = [r for r in out_rows if r["factory_can_proceed"]]
    approved_routes_exhausted = not any(
        r["next_state"] in (COV.NEXT_RUN_ACQUISITION, COV.NEXT_RUN_ALTERNATE_LANE)
        for r in out_rows)
    newly_routable_exhausted = not any(
        r["identity_key"] in newly_routable and r["factory_can_proceed"]
        for r in out_rows)
    closure_reconciled = bool(
        closure is not None
        and not (closure.get("reconciliation") or {}).get("missing")
        and not (closure.get("reconciliation") or {}).get("foreign")
        and not (closure.get("reconciliation") or {}).get("duplicate")
        and int(closure.get("active_denominator") or -1) == len(active_keys)
        and int(closure.get("count") or -1) == len(active_keys))
    ready = bool(recovery_exhausted and approved_routes_exhausted
                 and newly_routable_exhausted and closure_reconciled
                 and candidates_evaluated and packet is not None
                 and not factory_rows)
    booleans = OrderedDict((
        ("ZERO_COST_RECOVERY_EXHAUSTED", recovery_exhausted),
        ("APPROVED_ROUTES_EXHAUSTED", approved_routes_exhausted),
        ("NEWLY_ROUTABLE_COHORT_EXHAUSTED", newly_routable_exhausted),
        ("SAME_LANE_RETRIES_SUPPRESSED", True),
        ("CLOSURE_RECONCILED", closure_reconciled),
        ("READY_FOR_FOUNDER_REVIEW", ready),
    ))
    evidence = OrderedDict((
        ("zero_cost_recovery", recovery),
        ("approved_routes", OrderedDict((
            ("routed_never_attempted", by_next[COV.NEXT_RUN_ACQUISITION]),
            ("alternate_lane_available", by_next[COV.NEXT_RUN_ALTERNATE_LANE]),
            ("budget_deferred", by_state[COV.ROUTED_BUDGET_DEFERRED]),
            ("last_pass_outcome", (last_pass or {}).get("outcome", "")),
            ("last_pass_stopped_on_budget", budget_stopped),
        ))),
        ("newly_routable_cohort", OrderedDict((
            ("newly_routable_identities", sorted(newly_routable)),
            ("still_movable_by_the_factory", sorted(
                r["identity_key"] for r in out_rows
                if r["identity_key"] in newly_routable and r["factory_can_proceed"])),
        ))),
        ("same_lane_retries", RP.summary(eligible, suppressed)),
        ("closure", OrderedDict((
            ("closure_ledger_present", closure is not None),
            ("active_eligible", len(active_keys)),
            ("closure_active_denominator",
             (closure or {}).get("active_denominator")),
            ("closure_rows", (closure or {}).get("count")),
            ("closure_reconciliation", (closure or {}).get("reconciliation")),
        ))),
        ("founder_candidates", OrderedDict((
            ("evaluated", candidates_evaluated),
            ("source", "packet" if packet is not None else
                       "closure" if closure is not None else
                       "store" if store is not None else ""),
            ("packet_present", packet is not None),
        ))),
        ("ready_requires", [
            "ZERO_COST_RECOVERY_EXHAUSTED", "APPROVED_ROUTES_EXHAUSTED",
            "NEWLY_ROUTABLE_COHORT_EXHAUSTED", "CLOSURE_RECONCILED",
            "a founder-review packet", "no identity the factory can still move",
        ]),
    ))
    return COV.document(
        market_id, out_rows, work_order=work_order, as_of=as_of,
        census_keys=[r["identity_key"] for r in rows], stage=stage,
        counts=counts, booleans=booleans, evidence=evidence,
        note=("Every census identity appears exactly once with one coverage "
              "state and one next-state. Built from the same routing, the "
              "same merged acquisition view and the same retry policy the "
              "paid pass uses, so this artifact cannot disagree with the run."),
        url_overlay=OrderedDict((("overlay", overlay.get("overlay", "")),
                                 ("applied", overlay.get("applied", 0)))),
        routing_summary=routing_summary,
        active_eligible=len(active_keys),
        suppressed_same_lane=[r["identity_key"] for r in suppressed],
    )


def build_from_paths(*, market_id: str, url_overlay: str = "",
                     acquisition: str = "", last_pass: str = "",
                     closure: str = "", packet: str = "", observations: str = "",
                     url_recovery: str = "", declined_recovery: str = "",
                     recovery_after_last_pass: bool = False,
                     pass_run_dirs: Sequence[str] = (), retry_overrides: str = "",
                     stage: str, work_order: str, as_of: str,
                     census_path: Optional[Path] = None) -> Dict:
    census_file = census_path or (CENSUS_DIR / ("%s.json" % market_id))
    census = json.loads(census_file.read_text(encoding="utf-8-sig"))
    overlay = MR.apply_url_overlay(census["hotels"], url_overlay)
    prior = _load(acquisition) or {"results": []}
    return build(
        market_id, census, prior=prior, overlay=overlay,
        last_pass=_load(last_pass), closure=_load(closure), packet=_load(packet),
        store=_load(observations), url_recovery=_load(url_recovery),
        declined_recovery=_load(declined_recovery),
        recovery_after_last_pass=recovery_after_last_pass,
        pass_run_dirs=pass_run_dirs,
        overrides=RP.load_overrides(Path(retry_overrides)) if retry_overrides
        else None,
        stage=stage, work_order=work_order, as_of=as_of)


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--market", required=True)
    parser.add_argument("--url-overlay", default="",
                        help="the ptf-census-url-recovery report the paid pass "
                             "routed with")
    parser.add_argument("--acquisition", default="",
                        help="the merged acquisition view (every pass folded); "
                             "omit before any pass has run")
    parser.add_argument("--last-pass", default="",
                        help="the most recent paid-pass report; its deferred "
                             "list and outcome decide BUDGET_DEFERRED")
    parser.add_argument("--closure", default="")
    parser.add_argument("--packet", default="")
    parser.add_argument("--observations", default="")
    parser.add_argument("--url-recovery", default="")
    parser.add_argument("--declined-recovery", default="")
    parser.add_argument("--recovery-after-last-pass", action="store_true",
                        help="a URL recovery was run AFTER the last acquisition "
                             "pass, over the evidence that pass produced")
    parser.add_argument("--pass-run-dir", action="append", default=[],
                        help="repeatable; every acquisition run directory")
    parser.add_argument("--retry-overrides", default="")
    parser.add_argument("--stage", required=True, choices=STAGES)
    parser.add_argument("--work-order", required=True)
    parser.add_argument("--as-of", required=True)
    parser.add_argument("--out", required=True)
    args = parser.parse_args(argv)

    document = build_from_paths(
        market_id=args.market, url_overlay=args.url_overlay,
        acquisition=args.acquisition, last_pass=args.last_pass,
        closure=args.closure, packet=args.packet, observations=args.observations,
        url_recovery=args.url_recovery, declined_recovery=args.declined_recovery,
        recovery_after_last_pass=args.recovery_after_last_pass,
        pass_run_dirs=args.pass_run_dir, retry_overrides=args.retry_overrides,
        stage=args.stage, work_order=args.work_order, as_of=args.as_of)
    sha = CPB.write_json(Path(args.out), document)
    for name, value in document["counts"].items():
        print("%-26s: %d" % (name, value))
    for name, value in document["booleans"].items():
        print("%-32s= %s" % (name, value))
    print("benchmark : %s" % dict(document["benchmark"]))
    print("movable   : %d" % len(document["identities_the_factory_can_still_move"]))
    print("written   : %s (%s)" % (args.out, sha))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
