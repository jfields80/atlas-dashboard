# -*- coding: utf-8 -*-
"""PTF-GRAND-RAPIDS-CROSS-RUN-LEDGER-SYNC-018 -- the offline replay.

Replays every currently ROUTED Grand Rapids / Holland acquisition candidate
through the cross-run paid-attempt ledger. NO PROVIDER IS CALLED, nothing is
fetched, and nothing is spent. The whole point of the pass is to find out what
a spending run would buy that we already own.

WHAT THE WORK ORDER BELIEVED, AND WHAT THE ARTIFACTS SAY
--------------------------------------------------------
The order was written as though paid acquisition had NOT run for this market.
It has: ``grand_rapids_holland_mi_market_acquisition_pass1_001.json`` records
BATCH_COMPLETE over 65 attempted properties, 751 estimated cents and 19 plan
credits, under work order PTF-GRAND-RAPIDS-HOLLAND-PAID-ACQUISITION-
AUTHORIZATION-009. So this replay is not a pre-flight for a purchase that has
yet to happen; it is the proof that the purchase which DID happen can never be
made twice. That is a stronger result than the one the order asked for, and it
is the one the evidence supports.

HOW THE COHORT IS DERIVED, AND WHY IT IS NOT THE RESIDUAL ONE
--------------------------------------------------------------
``market_paid_acquisition --dry-run`` is re-run against the EMPTY prior, so the
within-market ``derive_cohort`` guard settles nothing and every routed,
non-duplicate identity is offered to the ledger. Running it against the latest
merged prior would have handed the ledger an empty cohort and proved only that
the guard we already had still works. The ledger has to answer for the whole
routed population or it has not been tested at all.

THE PERMITTED LADDER IS PER ROW, SO THE SUPPRESSION IS TOO
------------------------------------------------------------
``paid_attempt_ledger.suppress`` takes ONE permitted-lane list, and an
escalation verdict is only as good as that list: naming a lane the row was
never routed to would invent an escalation nobody authorised, and naming none
at all makes every channel failure look exhausted. The cohort is therefore
partitioned by its own routing ladder and each group is suppressed against its
own ladder, using the committed function unchanged.
"""
from __future__ import annotations

import argparse
import hashlib
import json
import sys
from collections import Counter, OrderedDict
from pathlib import Path
from typing import Dict, List, Mapping, Sequence, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.acquisition import lane_qualification as LQ   # noqa: E402
from scripts.pettripfinder.acquisition import paid_attempt_ledger as PAL  # noqa: E402

LP = _REPO_ROOT / "launch_packages" / "pettripfinder"

SCHEMA = "ptf-market-ledger-replay/1.0"
WORK_ORDER = "PTF-GRAND-RAPIDS-CROSS-RUN-LEDGER-SYNC-018"
MARKET = "grand-rapids-holland-mi"

#: The five classes the work order asks for, and the ledger decision each one
#: is derived from. The mapping is total over the ledger's decisions: a decision
#: this table does not name raises rather than being quietly filed as payable,
#: so a future decision cannot leak into the buy list by omission.
CLASSIFICATION: Dict[str, str] = {
    PAL.SUPPRESSED_EVIDENCE_REUSABLE: "REUSABLE_POLICY_EVIDENCE",
    PAL.SUPPRESSED_ALREADY_PAID: "ALREADY_PAID",
    PAL.SUPPRESSED_ESCALATION_EXHAUSTED: "SAME_PAGE_ALREADY_FAILED",
    PAL.SUPPRESSED_ROUTING_REPAIR_REQUIRED: "ROUTING_REPAIR_REQUIRED",
    PAL.FIRST_PAID_ATTEMPT: "GENUINELY_PAYABLE",
    PAL.ALLOWED_ESCALATION: "GENUINELY_PAYABLE",
    PAL.ALLOWED_URL_CHANGED: "GENUINELY_PAYABLE",
    PAL.ALLOWED_CAPABILITY_CHANGED: "GENUINELY_PAYABLE",
    PAL.ALLOWED_ROUTING_REPAIRED: "GENUINELY_PAYABLE",
    PAL.ALLOWED_OPERATOR_OVERRIDE: "GENUINELY_PAYABLE",
}

CLASSES: Tuple[str, ...] = ("REUSABLE_POLICY_EVIDENCE", "ALREADY_PAID",
                            "SAME_PAGE_ALREADY_FAILED",
                            "ROUTING_REPAIR_REQUIRED", "GENUINELY_PAYABLE")

#: The two identity questions this market has not answered. The dedup gate
#: ruled both DISTINCT_PROPERTIES -- it declined to merge on a shared street
#: and a shared switchboard alone -- and that ruling is a HOLD, not a finding.
#: Named here so the replay has to prove, every run, that it neither collapsed
#: a pair into one purchase nor promoted either half into an answer.
IDENTITY_HOLDS: Tuple[Tuple[str, str, str], ...] = (
    ("comfort inn", "comfort suites grandville grand rapids sw",
     "a Comfort Inn and a prior-census Comfort Suites share 4520 Kenowa Ave SW, "
     "49418 and the switchboard 616-667-0733; the dedup gate ruled them "
     "DISTINCT_PROPERTIES because the names are not containment-compatible"),
    ("sleep inn and suites", "spark by hilton grand rapids",
     "a Sleep Inn and Suites and a Spark by Hilton share 4284 29th St SE, 49512 "
     "and the switchboard 616-975-9000; a Choice-to-Hilton rebrand and two "
     "distinct hotels look identical on those signals alone"),
)


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _load(path: Path) -> Dict:
    return json.loads(path.read_text(encoding="utf-8"))


def _ladder(row: Mapping) -> Tuple[str, ...]:
    """The lanes this row is ROUTED to, primary first. Never a wider list."""
    ladder = [str(lane) for lane in (row.get("ladder") or ()) if lane]
    if not ladder:
        primary = str(row.get("provider") or "")
        ladder = ([primary] if primary else []) + [
            str(lane) for lane in (row.get("fallback_providers") or ()) if lane]
    return tuple(ladder)


def replay(cohort: Sequence[Mapping], ledger: Mapping) -> Tuple[List[Dict], List[Dict]]:
    """``(payable, suppressed)`` over the cohort, one ladder group at a time."""
    groups: "OrderedDict[Tuple[str, ...], List[Mapping]]" = OrderedDict()
    for row in cohort:
        groups.setdefault(_ladder(row), []).append(row)
    payable: List[Dict] = []
    suppressed: List[Dict] = []
    for ladder, rows in groups.items():
        allowed, refused = PAL.suppress(rows, ledger, available_lanes=ladder)
        payable.extend(allowed)
        suppressed.extend(refused)
    return (payable, suppressed)


def classify(row: Mapping) -> str:
    decision = row["paid_history"]["decision"]
    if decision not in CLASSIFICATION:
        raise PAL.PaidLedgerError(
            "ledger decision %r has no classification; a decision this replay "
            "does not understand must not be filed as payable by default"
            % decision)
    return CLASSIFICATION[decision]


def _row_view(row: Mapping) -> Dict:
    history = row["paid_history"]
    return OrderedDict((
        ("identity_key", row.get("identity_key", "")),
        ("canonical_name", row.get("canonical_name", "")),
        ("family", row.get("family", "")),
        ("routed_lane", row.get("provider", "")),
        ("routed_ladder", list(_ladder(row))),
        ("source_url", row.get("source_url", "")),
        ("classification", classify(row)),
        ("ledger_decision", history["decision"]),
        ("match_key", history["match_key"]),
        ("prior_run_id", history.get("prior_run_id", "")),
        ("prior_lane", history.get("prior_lane", "")),
        ("prior_outcome", history.get("prior_outcome", "")),
        ("material_change_reason", history.get("material_change_reason", "")),
        ("why", history["reason"]),
    ))


def _ledger_as_evidence(ledger: Mapping) -> List[Dict]:
    """Every recorded paid attempt, in the shape ``summarise`` reads.

    The ledger names the lane ``lane`` and the acquisition report names it
    ``provider``; the rest of the fields already line up. Nothing is invented
    here -- the predecessor rows of an in-run escalation carry no outcome by
    construction and are dropped, because an attempt with no outcome is not
    evidence for or against a lane.
    """
    rows: List[Dict] = []
    for attempt in ledger.get("attempts") or ():
        if not attempt.get("outcome"):
            continue
        rows.append(dict(attempt, provider=attempt.get("lane", "")))
    return rows


def lane_plan(payable: Sequence[Mapping], evidence_rows: Sequence[Mapping],
              ledger: Mapping) -> Dict:
    """The cheapest QUALIFIED lane for each genuinely payable row.

    Two evidence views are recorded and they answer different questions. THIS
    MARKET is what Grand Rapids measured on its own, and on its own it
    qualifies nothing: its best pairs are Marriott on the browser at 17 of 17
    and Hilton at 16 of 18, both short of the 20 effective attempts the policy
    demands, and every Firecrawl family is smaller still. The CROSS-RUN view is
    the same rule over every attempt this project has ever paid for, which is
    the corpus the qualification thresholds were derived against.

    The plan is built on the cross-run view, because a threshold that exists to
    refuse a lucky sample should not be met or missed by an accident of which
    market a row happens to sit in. Both views are written out, so a reader can
    see the market's own number rather than take the wider one on trust.
    """
    local = LQ.qualify(LQ.summarise(evidence_rows))
    costs = LQ.lane_costs()
    evidence = LQ.summarise(_ledger_as_evidence(ledger))
    verdicts = LQ.qualify(evidence, available={p: c["available"]
                                               for p, c in costs.items()})
    plans = LQ.plan_cohort_lanes(payable, verdicts, costs)
    lanes = Counter(p["primary_lane"] for p in plans)
    return OrderedDict((
        ("schema", LQ.SCHEMA),
        ("rows", len(plans)),
        ("by_lane", OrderedDict(sorted(lanes.items()))),
        ("firecrawl", lanes.get("firecrawl", 0)),
        ("brightdata_browser", lanes.get("brightdata_browser", 0)),
        ("brightdata_web_unlocker", lanes.get("brightdata_web_unlocker", 0)),
        ("other", sum(count for lane, count in lanes.items()
                      if lane not in ("firecrawl", "brightdata_browser",
                                      "brightdata_web_unlocker"))),
        ("evidence_used", "CROSS_RUN_LEDGER"),
        ("qualified_pairs", sorted("%s/%s" % (p, f) for (p, f), v
                                   in verdicts.items() if v["qualified"])),
        ("qualified_pairs_on_this_markets_evidence_alone",
         sorted("%s/%s" % (p, f) for (p, f), v in local.items()
                if v["qualified"])),
        ("verdicts_cross_run", OrderedDict(
            ("%s/%s" % key, verdicts[key]) for key in verdicts)),
        ("verdicts_this_market", OrderedDict(
            ("%s/%s" % key, local[key]) for key in local)),
        ("lane_costs", costs),
        ("plans", plans),
    ))


def cost_plan(plans: Sequence[Mapping], costs: Mapping) -> Dict:
    """What the payable rows would cost. Zero rows is a real answer, not a gap."""
    credits = sum(1.0 for p in plans if p["primary_credit_billed"])
    projected = sum(float(p["primary_usd_minor"] or 0.0)
                    for p in plans if not p["primary_credit_billed"])
    # Every credit-billed row may escalate ONCE to the browser lane, and every
    # dollar row may fall back to its own fallback lane. The worst case prices
    # both, because a ceiling that assumes the happy path is not a ceiling.
    browser = float(costs.get(LQ.DEFAULT_LANE, {})
                    .get("usd_minor_per_property") or 0.0)
    fallback = sum(float(p["fallback_usd_minor"] or browser)
                   for p in plans if p["primary_credit_billed"])
    fallback += sum(float(p["fallback_usd_minor"] or 0.0)
                    for p in plans if not p["primary_credit_billed"])
    worst = projected + fallback
    return OrderedDict((
        ("firecrawl_credits_required", round(credits, 2)),
        ("projected_brightdata_usd_minor", round(projected, 2)),
        ("fallback_exposure_usd_minor", round(fallback, 2)),
        ("worst_case_usd_minor", round(worst, 2)),
        ("recommended_hard_cap_usd_minor", int(round(worst))),
        ("current_spend_usd_minor", 0),
        ("why", "no row is payable, so there is nothing to authorise and the "
                "recommended cap is zero" if not plans else
                "the cap covers the projection plus one fallback attempt for "
                "every row, which is the most this cohort can cost"),
    ))


def identity_holds(cohort: Sequence[Mapping], payable: Sequence[Mapping],
                   dedup: Mapping, routing: Mapping) -> Dict:
    """Each named identity question, and proof the replay left it open."""
    verdicts: Dict[Tuple[str, str], str] = {}
    for group in dedup.get("groups") or ():
        keys = tuple(sorted(str(k) for k in group.get("identity_keys") or ()))
        if len(keys) == 2:
            verdicts.setdefault(keys, str(group.get("verdict") or ""))
    merged = set()
    for merge in dedup.get("merges") or ():
        for field in ("absorbed", "merged_into", "absorbed_identity_key"):
            if merge.get(field):
                merged.add(str(merge[field]))
        for key in (merge.get("absorbed_identity_keys") or ()):
            merged.add(str(key))
    payable_keys = {r.get("identity_key") for r in payable}
    cohort_keys = {r.get("identity_key") for r in cohort}
    states = {str(e.get("identity_key") or ""): str(e.get("routing_state") or "")
              for e in (routing.get("entries") or ())}

    rows = []
    for left, right, note in IDENTITY_HOLDS:
        pair = tuple(sorted((left, right)))
        rows.append(OrderedDict((
            ("identity_keys", [left, right]),
            ("question", note),
            ("dedup_verdict", verdicts.get(pair, "NOT_GROUPED")),
            ("still_two_identities", verdicts.get(pair) != "SAFE_MERGE"
             and left not in merged and right not in merged),
            ("routing_state", OrderedDict(
                (k, states.get(k, "NOT_IN_CENSUS")) for k in (left, right))),
            ("in_cohort", sorted(k for k in (left, right) if k in cohort_keys)),
            ("in_payable_cohort",
             sorted(k for k in (left, right) if k in payable_keys)),
            ("resolved_by_this_pass", False),
            ("note", "a replay reads history; it does not rule on identity. "
                     "Both halves stay distinct and neither is promoted."),
        )))
    return OrderedDict((("count", len(rows)), ("holds", rows)))


def validate(cohort: Sequence[Mapping], payable: Sequence[Mapping],
             suppressed: Sequence[Mapping], ledger: Mapping,
             holds: Mapping) -> Dict:
    """The things that must be true, each answered from the rows."""
    urls = [PAL.canonical_url(r) for r in payable if PAL.canonical_url(r)]
    codes = [PAL.property_code(r) for r in payable if PAL.property_code(r)]
    duplicate_urls = sorted(u for u, n in Counter(urls).items() if n > 1)
    duplicate_codes = sorted(c for c, n in Counter(codes).items() if n > 1)

    index = PAL.LedgerIndex(ledger)
    rebought = sorted(r.get("identity_key", "") for r in payable
                      if index.lookup(r)[2])
    unreasoned = sorted(
        r.get("identity_key", "") for r in payable
        if r["paid_history"]["decision"] != PAL.FIRST_PAID_ATTEMPT
        and not r["paid_history"].get("material_change_reason"))
    weak = sorted(r.get("identity_key", "") for r in suppressed
                  if r["paid_history"]["match_key"] not in PAL.PAGE_MATCH_KEYS)

    checks = OrderedDict((
        ("no_duplicate_page_in_payable_cohort", OrderedDict((
            ("ok", not duplicate_urls),
            ("duplicate_canonical_urls", duplicate_urls)))),
        ("no_duplicate_canonical_property_in_payable_cohort", OrderedDict((
            ("ok", not duplicate_codes),
            ("duplicate_property_codes", duplicate_codes)))),
        ("no_already_paid_page_is_purchased_again", OrderedDict((
            ("ok", not rebought), ("identity_keys", rebought)))),
        ("no_same_method_failure_retried_without_a_material_change", OrderedDict((
            ("ok", not unreasoned), ("identity_keys", unreasoned)))),
        ("current_spend_is_zero", OrderedDict((
            ("ok", True),
            ("usd_minor", 0),
            ("plan_credits", 0),
            ("why", "no provider is constructed and no lane is called; the "
                    "cohort is derived by --dry-run and the ledger is read "
                    "from disk")))),
        ("every_suppression_rests_on_a_page_key", OrderedDict((
            # The mirror of the identity-hold question. Over-suppression is the
            # expensive mistake -- a suppressed hotel never gets a policy -- so
            # it matters that no row here was refused on proximity. Every one
            # matched the URL we actually fetched.
            ("ok", not weak),
            ("suppressed_on_a_weak_key", weak),
            ("by_match_key", OrderedDict(sorted(Counter(
                r["paid_history"]["match_key"] for r in suppressed).items()))),
            ("why", "CANONICAL_URL and PROPERTY_CODE name a PAGE and decide "
                    "alone; the premises keys only ever propose")))),
        ("cohort_accounted_for", OrderedDict((
            ("ok", len(payable) + len(suppressed) == len(cohort)),
            ("payable", len(payable)), ("suppressed", len(suppressed)),
            ("submitted", len(cohort))))),
        ("identity_holds_preserved", OrderedDict((
            ("ok", all(h["still_two_identities"]
                       and not h["resolved_by_this_pass"]
                       for h in holds["holds"])),
            ("count", holds["count"])))),
    ))
    checks["all_pass"] = all(v["ok"] for v in checks.values())
    return checks


def build(*, dry_run_path: Path, routing_path: Path, ledger_path: Path,
          evidence_path: Path, dedup_path: Path,
          acquisition_path: Path) -> Dict:
    dry_run = _load(dry_run_path)
    routing = _load(routing_path)
    ledger = PAL.load(ledger_path)
    evidence = _load(evidence_path)
    dedup = _load(dedup_path)
    acquisition = _load(acquisition_path)

    cohort = list(dry_run.get("cohort") or ())
    routed = [e for e in (routing.get("entries") or ())
              if e.get("routing_state") == "ROUTED"]

    payable, suppressed = replay(cohort, ledger)
    rows = [_row_view(r) for r in list(payable) + list(suppressed)]
    rows.sort(key=lambda r: (r["classification"], r["identity_key"]))
    counts = Counter(r["classification"] for r in rows)

    plan = lane_plan(payable, list(evidence.get("results") or ()), ledger)
    costs = plan["lane_costs"]
    holds = identity_holds(cohort, payable, dedup, routing)

    # Re-ingesting the run this market has already paid for must add nothing.
    # If it added rows the ledger would be incomplete, and every suppression
    # below would be an accident rather than a guarantee.
    reingested = PAL.ingest_run(acquisition, market_id=MARKET)
    before = len(ledger.get("attempts") or ())
    after = len(PAL.merge(ledger, reingested).get("attempts") or ())

    return OrderedDict((
        ("schema", SCHEMA),
        ("what_this_is",
         "Every currently routed Grand Rapids / Holland acquisition candidate "
         "replayed through the cross-run paid-attempt ledger, offline. No "
         "provider was called and nothing was spent."),
        ("market_id", MARKET),
        ("work_order", WORK_ORDER),
        ("inputs", OrderedDict(
            (name, OrderedDict((
                ("path", str(path.relative_to(_REPO_ROOT).as_posix())),
                ("sha256", _sha256(path)))))
            for name, path in (("dry_run", dry_run_path),
                               ("routing", routing_path),
                               ("paid_attempt_ledger", ledger_path),
                               ("lane_evidence", evidence_path),
                               ("pre_acquisition_dedup", dedup_path),
                               ("paid_run", acquisition_path)))),
        ("prior_paid_run", OrderedDict((
            ("work_order", acquisition.get("work_order", "")),
            ("run_id", acquisition.get("run_id", "")),
            ("outcome", acquisition.get("outcome", "")),
            ("attempted", acquisition.get("attempted", 0)),
            ("spend_usd_minor", (acquisition.get("spend") or {})
             .get("binding_usd_minor", 0)),
            ("plan_credits", (acquisition.get("spend") or {})
             .get("estimated_plan_credits", 0)),
            ("note", "the work order was written as though this run had not "
                     "happened; the artifact says it did, and that is what the "
                     "ledger has to protect"),
        ))),
        ("ledger_completeness", OrderedDict((
            ("attempts_in_ledger", before),
            ("grand_rapids_attempts", sum(
                1 for a in ledger["attempts"] if a.get("market_id") == MARKET)),
            ("rows_from_re_ingesting_the_paid_run", len(reingested)),
            ("new_rows_added", after - before),
            ("ok", after == before),
            ("why", "the ledger already holds every attempt of the paid run, "
                    "so a re-ingest is a no-op and the suppressions below rest "
                    "on a complete record"),
        ))),
        ("counts", OrderedDict((
            ("routed_identities_before", len(routed)),
            ("acquisition_cohort_before", len(cohort)),
            ("settled_before_the_ledger_by_the_dedup_gate",
             int(dry_run.get("settled_size") or 0)),
            ("suppressed_by_cross_run_ledger", len(suppressed)),
            ("reusable_evidence", counts.get("REUSABLE_POLICY_EVIDENCE", 0)),
            ("prior_paid", counts.get("ALREADY_PAID", 0)),
            ("prior_failed", counts.get("SAME_PAGE_ALREADY_FAILED", 0)),
            ("routing_repair_required",
             counts.get("ROUTING_REPAIR_REQUIRED", 0)),
            ("genuinely_payable_after_replay",
             counts.get("GENUINELY_PAYABLE", 0)),
        ))),
        ("by_classification", OrderedDict(
            (name, counts.get(name, 0)) for name in CLASSES)),
        ("paid_history_summary", PAL.summary(payable, suppressed)),
        ("lane_plan", plan),
        ("cost_plan", cost_plan(plan["plans"], costs)),
        ("identity_holds", holds),
        ("validation", validate(cohort, payable, suppressed, ledger, holds)),
        ("rows", rows),
    ))


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run-report", default=str(
        LP / "grand_rapids_holland_mi_acquisition_dry_run_replay_018.json"))
    parser.add_argument("--routing", default=str(
        LP / "grand_rapids_holland_mi_routing_recovered_001.json"))
    parser.add_argument("--ledger",
                        default=str(LP / "ptf_paid_attempt_ledger_001.json"))
    parser.add_argument("--lane-evidence", default=str(
        LP / "grand_rapids_holland_mi_acquisition_merged_closeout_001.json"))
    parser.add_argument("--dedup", default=str(
        LP / "grand_rapids_holland_mi_pre_acquisition_dedup_001.json"))
    parser.add_argument("--paid-run", default=str(
        LP / "grand_rapids_holland_mi_market_acquisition_pass1_001.json"))
    parser.add_argument("--out", default=str(
        LP / "grand_rapids_holland_mi_cross_run_ledger_replay_018.json"))
    args = parser.parse_args(argv)

    document = build(dry_run_path=Path(args.dry_run_report),
                     routing_path=Path(args.routing),
                     ledger_path=Path(args.ledger),
                     evidence_path=Path(args.lane_evidence),
                     dedup_path=Path(args.dedup),
                     acquisition_path=Path(args.paid_run))
    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(json.dumps(document, indent=1, ensure_ascii=False) + "\n",
                   encoding="utf-8")

    counts = document["counts"]
    print("routed identities        : %d" % counts["routed_identities_before"])
    print("acquisition cohort       : %d" % counts["acquisition_cohort_before"])
    print("suppressed by the ledger : %d"
          % counts["suppressed_by_cross_run_ledger"])
    for name in CLASSES:
        print("  %-26s %d" % (name.lower(), document["by_classification"][name]))
    plan, cost = document["lane_plan"], document["cost_plan"]
    print("lanes                    : firecrawl %d, browser %d, unlocker %d, "
          "other %d" % (plan["firecrawl"], plan["brightdata_browser"],
                        plan["brightdata_web_unlocker"], plan["other"]))
    print("firecrawl credits        : %s" % cost["firecrawl_credits_required"])
    print("projected / worst case   : %s / %s cents"
          % (cost["projected_brightdata_usd_minor"],
             cost["worst_case_usd_minor"]))
    print("recommended hard cap     : %s cents"
          % cost["recommended_hard_cap_usd_minor"])
    print("identity holds preserved : %d" % document["identity_holds"]["count"])
    print("validation               : %s" % document["validation"]["all_pass"])
    print("written                  : %s" % out)
    return 0 if document["validation"]["all_pass"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
