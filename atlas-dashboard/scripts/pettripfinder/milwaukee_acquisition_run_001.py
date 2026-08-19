"""PTF-MILWAUKEE-ACQUISITION-ROUTER-INTEGRATION-001 -- the Milwaukee run.

Drives the committed Milwaukee policy-acquisition queue through the proven
PTF acquisition router. The router decides provider and reader; this module
decides only *whether it is safe to spend at all*, and *when to stop*.

Cost safety (founder override, 2026-08-18)
------------------------------------------
    SOFT_CHECKPOINT_1  = $5     persist + report, continue if cost is normal
    SOFT_CHECKPOINT_2  = $10    persist + report, continue if cost is normal
    HARD_MARKET_CAP    = $15    stop immediately and safely

Spend is measured from the vendor's per-zone MONTH-TO-DATE COST, summed across
every zone this market can bill to, never from the router's per-attempt
estimate and never from the account balance.

The balance was the original measure and it was wrong in the dangerous
direction. Bright Data debits the balance on a lag: mid-run the balance said
$3.95 had been spent while the zones had already accrued $12.77 -- a 3x
under-report against a hard cap. Worse, a mid-run top-up RAISED the balance,
so drawdown went negative and the clamp reported $0.00 spent while the run was
minutes from the cap. Zone cost has neither failure: it only ever increases,
and a top-up cannot touch it.

The balance is still read, and still gates whether a run may start, because a
zone figure cannot tell you whether there is money left to spend. It is
corroboration, not the meter.

Three gates run BEFORE the first paid call, and any one of them stops the run
with nothing spent:

1. cost telemetry must be live. The override is explicit -- "if provider cost
   telemetry is stale or unavailable: STOP rather than risk exceeding the
   budget" -- so an unreadable balance is a stop, not a warning.
2. the account balance must exceed the remaining cap, because a run that
   cannot finish should not start.
3. at least one provider must pass its own health check.

Every completed property is journalled before the next one begins, so a kill
at any moment loses at most the property in flight. ``--resume`` is the
default and completed keys are read from the journal, never from memory.
"""

from __future__ import annotations

import argparse
import asyncio
import json
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts.pettripfinder.acquisition import journal as JOURNAL      # noqa: E402
from scripts.pettripfinder.acquisition import providers as PROVIDERS  # noqa: E402
from scripts.pettripfinder.acquisition import registry as REGISTRY    # noqa: E402
from scripts.pettripfinder.brightdata import client as CLIENT         # noqa: E402
from scripts.pettripfinder.brightdata import corpus as CORPUS         # noqa: E402
from scripts.pettripfinder.brightdata import cross_brand_pilot_002 as P2  # noqa: E402

MARKET = "milwaukee-wi"
WORK_ORDER = "PTF-MILWAUKEE-ACQUISITION-ROUTER-INTEGRATION-001"
PKG = REPO / "launch_packages" / "pettripfinder"
REPORTS = PKG / "markets" / "reports"
QUEUE_PATH = REPORTS / ("%s_policy_acquisition_queue_001.json" % MARKET)

#: Founder cost override. Cents, so the comparisons are integer-exact.
SOFT_CHECKPOINT_1_USD_MINOR = 500
SOFT_CHECKPOINT_2_USD_MINOR = 1000
HARD_CAP_USD_MINOR = 1500

RUN_ROOT = REPO / "data" / "acquisition" / "milwaukee-router-001"


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


# --------------------------------------------------------------------------- #
# Spend, measured from the vendor rather than estimated.
# --------------------------------------------------------------------------- #

#: Every zone this market can bill to. The Browser API lane bills to the first
#: and the Web Unlocker alternates across the other two, so summing all three
#: is what makes the meter cover every lane the router can choose.
BILLABLE_ZONES = ("scraping_browser1", "mcp_unlocker", "cli_unlocker")


class SpendMeter:
    """Month-to-date cost summed across every billable zone.

    Monotonic and top-up-immune, which the account balance is not. See the
    module docstring for the incident that forced the change.
    """

    def __init__(self) -> None:
        self.baseline: Optional[CLIENT.UsageSnapshot] = None
        self.latest: Optional[CLIENT.UsageSnapshot] = None
        self.samples: List[Dict] = []

    #: Where the MARKET-level baseline lives. The founder cap is "$15 total
    #: provider spend for this Milwaukee work order", not $15 per invocation,
    #: so the baseline has to outlive the process. Without this, ten runs of
    #: ten properties could each spend $15 and every one would report itself
    #: inside the cap.
    ANCHOR = RUN_ROOT / "market_cost_anchor.json"

    def read(self, label: str) -> CLIENT.UsageSnapshot:
        snap = CLIENT.read_usage(label)
        self.latest = snap
        if self.baseline is None:
            self.baseline = self._anchor(snap)
        self.samples.append(snap.to_dict())
        return snap

    def _anchor(self, fresh: CLIENT.UsageSnapshot) -> CLIENT.UsageSnapshot:
        """The first balance ever seen for this market, persisted."""
        if self.ANCHOR.exists():
            try:
                stored = json.loads(self.ANCHOR.read_text(encoding="utf-8"))
                return CLIENT.UsageSnapshot(
                    label=stored.get("label", "anchor"),
                    captured_at=stored.get("captured_at", ""),
                    zone=stored.get("zone", CLIENT.ZONE),
                    available=bool(stored.get("available")),
                    cost_month_usd_minor=stored.get("cost_month_usd_minor"),
                    bandwidth_bytes=stored.get("bandwidth_bytes"),
                    bandwidth_display=stored.get("bandwidth_display", ""),
                    cost_display=stored.get("cost_display", ""),
                    balance_usd_minor=stored.get("balance_usd_minor"),
                    pending_charge_usd_minor=stored.get("pending_charge_usd_minor"),
                    notes=tuple(stored.get("notes") or ()))
            except (ValueError, TypeError, OSError):
                pass
        if fresh.available and fresh.balance_usd_minor is not None:
            self.ANCHOR.parent.mkdir(parents=True, exist_ok=True)
            self.ANCHOR.write_text(json.dumps(fresh.to_dict(), indent=1),
                                   encoding="utf-8")
        return fresh

    @property
    def telemetry_live(self) -> bool:
        snap = self.latest
        return bool(snap and snap.available and snap.balance_usd_minor is not None)

    def zone_costs(self) -> Dict[str, Optional[int]]:
        """Month-to-date cost per billable zone, read live."""
        out: Dict[str, Optional[int]] = {}
        for zone in BILLABLE_ZONES:
            snap = CLIENT.read_usage("%s:zone:%s" % (MARKET, zone), zone=zone)
            out[zone] = snap.cost_month_usd_minor
        return out

    def spent_usd_minor(self) -> Optional[int]:
        """Cumulative market spend: summed per-zone cost growth since the
        anchor. ``None`` when any zone cannot be read -- which callers must
        treat as a stop, never as zero. Under a hard cap, an unknown spend and
        a zero spend must never look the same."""
        anchor = self.anchor_zone_costs()
        if anchor is None:
            return None
        now = self.zone_costs()
        total = 0
        for zone in BILLABLE_ZONES:
            a, b = anchor.get(zone), now.get(zone)
            if a is None or b is None:
                return None
            total += max(0, b - a)
        return total

    def anchor_zone_costs(self) -> Optional[Dict[str, int]]:
        if not self.ANCHOR.exists():
            return None
        try:
            data = json.loads(self.ANCHOR.read_text(encoding="utf-8"))
        except (ValueError, OSError):
            return None
        zones = data.get("zone_costs_usd_minor")
        if not isinstance(zones, dict):
            return None
        return {k: v for k, v in zones.items()}

    def balance_usd_minor(self) -> Optional[int]:
        """Corroboration only: whether money remains, not how much was spent."""
        return self.latest.balance_usd_minor if self.latest else None

    def zone_delta_usd_minor(self) -> Optional[int]:
        """Browser-lane growth only, reported beside the total so the split
        between the two lanes stays visible."""
        anchor = self.anchor_zone_costs()
        if anchor is None or not self.latest:
            return None
        a, b = anchor.get(BILLABLE_ZONES[0]), self.latest.cost_month_usd_minor
        if a is None or b is None:
            return None
        return max(0, b - a)


# --------------------------------------------------------------------------- #
# Preflight
# --------------------------------------------------------------------------- #

def preflight(meter: SpendMeter, *, cap_usd_minor: int) -> Dict:
    """Everything that must be true before a single cent is spent."""
    checks: List[Dict] = []

    snap = meter.read("%s:baseline" % MARKET)
    checks.append({
        "check": "cost_telemetry_live",
        "ok": meter.telemetry_live,
        "detail": ("balance %s cents, zone month-to-date %s"
                   % (snap.balance_usd_minor, snap.cost_display or "?")
                   if meter.telemetry_live else
                   "the vendor's balance could not be read: %s"
                   % "; ".join(snap.notes or ("no reason given",))),
    })

    balance = snap.balance_usd_minor
    checks.append({
        "check": "balance_covers_the_cap",
        "ok": balance is not None and balance >= cap_usd_minor,
        "detail": ("balance %d cents against a %d cent cap"
                   % (balance, cap_usd_minor)) if balance is not None
                  else "balance unreadable",
    })

    healthy = []
    provider_detail = {}
    for pid in PROVIDERS.all_ids():
        health = PROVIDERS.get(pid).health_check()
        provider_detail[pid] = {"available": bool(health.available),
                                "detail": health.detail}
        if health.available:
            healthy.append(pid)
    checks.append({
        "check": "at_least_one_provider_available",
        "ok": bool(healthy),
        "detail": ("available: %s" % ", ".join(healthy)) if healthy else
                  "; ".join("%s: %s" % (p, d["detail"])
                            for p, d in sorted(provider_detail.items())),
    })

    return {"ok": all(c["ok"] for c in checks), "checks": checks,
            "providers": provider_detail, "healthy_providers": healthy,
            "baseline": snap.to_dict()}


# --------------------------------------------------------------------------- #
# The run
# --------------------------------------------------------------------------- #

def _record_for(row) -> "CORPUS.BenchmarkRecord":
    """A capture record for a property with NO committed benchmark.

    Milwaukee has no policy authority, so there is nothing to compare a capture
    against -- ``facts``, ``quotes`` and ``withheld_fields`` are empty on
    purpose. That is the safe direction: the router reads only brand, identity
    key and name, and an empty benchmark cannot leak an expected answer into a
    capture the way a populated one could.
    """
    return CORPUS.BenchmarkRecord(
        identity_key=row["identity_key"],
        name=row["canonical_name"],
        market_id=row["market_id"],
        brand=row["brand"],
        bucket=CORPUS.bucket_of(row["brand"]),
        source_url=row["official_url"],
        pets_allowed=None,
        facts={},
        quotes=(),
        withheld_fields={},
        service_animal_statement="",
        categories=frozenset(),
        origin="census")


def _spent_so_far(meter: "SpendMeter") -> Optional[int]:
    """Cumulative market spend before this invocation, from the zone anchor."""
    if not SpendMeter.ANCHOR.exists():
        return 0
    return meter.spent_usd_minor()


def load_queue() -> List[Dict]:
    doc = json.loads(QUEUE_PATH.read_text(encoding="utf-8-sig"))
    return [r for r in doc["items"] if not r["brand_excluded"]]


def checkpoint_report(*, meter: SpendMeter, journal: JOURNAL.Journal,
                      queue: List[Dict], label: str) -> Dict:
    entries = journal.read()
    resolved = [e for e in entries.values()
                if e.get("final_state", "").startswith("ACQUIRED")]
    pub = [e for e in entries.values()
           if e.get("final_state") == "ACQUIRED_PUBLICATION_GRADE"]
    spent = meter.spent_usd_minor()
    return {
        "checkpoint": label,
        "at": _now(),
        "properties_attempted": len(entries),
        "properties_resolved": len(resolved),
        "publication_grade_records": len(pub),
        "cost_usd_minor": spent,
        "cost_per_resolved_record_usd_minor": (
            round(spent / len(resolved), 2) if spent is not None and resolved else None),
        "remaining_queue": len(queue) - len(entries),
        "zone_delta_usd_minor": meter.zone_delta_usd_minor(),
    }


async def run(*, max_properties: Optional[int], resume: bool,
              run_id: str, dry_run: bool) -> Dict:
    started = time.monotonic()
    run_dir = RUN_ROOT / run_id
    run_dir.mkdir(parents=True, exist_ok=True)
    journal = JOURNAL.Journal(path=run_dir / "journal.jsonl")

    queue = load_queue()
    done = journal.completed_keys() if resume else set()
    pending = [r for r in queue if r["identity_key"] not in done]
    if max_properties is not None:
        pending = pending[:max_properties]

    meter = SpendMeter()
    # The balance gate must test the REMAINING allowance, not the whole cap.
    # After the market has spent $2.33 of its $15, a $13.75 balance is ample --
    # but comparing it against the full $15 would refuse to resume a run that
    # is comfortably fundable, which is a false stop and the opposite of safe.
    already = _spent_so_far(meter)
    remaining_cap = max(0, HARD_CAP_USD_MINOR - (already or 0))
    pre = preflight(meter, cap_usd_minor=remaining_cap)
    pre["already_spent_usd_minor"] = already
    pre["remaining_cap_usd_minor"] = remaining_cap

    report = {
        "schema": "ptf-milwaukee-acquisition-run/1.0",
        "work_order": WORK_ORDER,
        "market_id": MARKET,
        "run_id": run_id,
        "run_start": _now(),
        "dry_run": dry_run,
        "cost_policy": {
            "soft_checkpoint_1_usd_minor": SOFT_CHECKPOINT_1_USD_MINOR,
            "soft_checkpoint_2_usd_minor": SOFT_CHECKPOINT_2_USD_MINOR,
            "hard_cap_usd_minor": HARD_CAP_USD_MINOR,
            "measured_from": "vendor account balance drawdown, read live",
        },
        "preflight": pre,
        "queue_total": len(queue),
        "already_completed": len(done),
        "planned_this_batch": len(pending),
        "checkpoints": [],
        "properties": [],
    }

    if not pre["ok"]:
        report["outcome"] = "STOPPED_BEFORE_SPENDING"
        report["stop_reason"] = "; ".join(
            "%s: %s" % (c["check"], c["detail"]) for c in pre["checks"] if not c["ok"])
        report["run_end"] = _now()
        report["total_elapsed_seconds"] = round(time.monotonic() - started, 3)
        report["total_cost_usd_minor"] = 0
        report["attended_fallback_required"] = len(pending)
        return report

    if dry_run:
        report["outcome"] = "DRY_RUN_ONLY"
        report["run_end"] = _now()
        report["total_elapsed_seconds"] = round(time.monotonic() - started, 3)
        report["total_cost_usd_minor"] = 0
        return report

    # ------------------------------------------------------------------ #
    # Paid section. Reached only when all three gates passed.
    # ------------------------------------------------------------------ #
    from scripts.pettripfinder.acquisition import router as ROUTER

    hit_1 = hit_2 = False
    for row in pending:
        spent = meter.spent_usd_minor()
        if spent is None:
            report["outcome"] = "STOPPED_TELEMETRY_LOST"
            report["stop_reason"] = ("the vendor balance became unreadable "
                                     "mid-run; stopped rather than spend blind")
            break
        if spent >= HARD_CAP_USD_MINOR:
            report["outcome"] = "STOPPED_HARD_CAP"
            report["stop_reason"] = ("hard cap reached: %d of %d cents"
                                     % (spent, HARD_CAP_USD_MINOR))
            break
        if not hit_1 and spent >= SOFT_CHECKPOINT_1_USD_MINOR:
            hit_1 = True
            report["checkpoints"].append(
                checkpoint_report(meter=meter, journal=journal, queue=queue,
                                  label="soft_$5"))
        if not hit_2 and spent >= SOFT_CHECKPOINT_2_USD_MINOR:
            hit_2 = True
            report["checkpoints"].append(
                checkpoint_report(meter=meter, journal=journal, queue=queue,
                                  label="soft_$10"))

        began = time.monotonic()
        record = _record_for(row)
        target = P2.target_for(record)
        try:
            result = await ROUTER.route_property(
                record, target, run_dir=run_dir, run_id=run_id)
            doc = result.document
            grade = dict(doc.publication_grade) if doc is not None else {}
            entry = {
                "identity_key": row["identity_key"],
                "canonical_name": row["canonical_name"],
                "brand": row["brand"],
                "official_url": row["official_url"],
                "final_state": result.state,
                "attempts": len(result.attempts),
                "providers_tried": list(result.providers_tried),
                "provider": result.attempts[-1].provider if result.attempts else "",
                "reader": (result.route or {}).get("reader", ""),
                "failure": result.failure,
                "failure_class": result.failure_class,
                "escalation_stopped_because": result.escalation_stopped_because,
                # The state already IS the verdict; do not re-derive it
                # from the grade dict and risk a second opinion.
                "publication_grade": result.state == "ACQUIRED_PUBLICATION_GRADE",
                "publication_grade_detail": grade,
                "policy_locator": doc.policy_locator if doc is not None else "",
                "content_hash": doc.content_hash if doc is not None else "",
                "estimated_bytes": result.cost.estimated_bytes,
                "reported_usd_minor": result.cost.reported_usd_minor,
                "elapsed_seconds": round(time.monotonic() - began, 3),
                "completed_at": _now(),
                "result": result.to_dict(),
            }
        except Exception as exc:                                  # noqa: BLE001
            # A crash must still be journalled. An unrecorded paid attempt is
            # money spent that a resume would spend again.
            entry = {
                "identity_key": row["identity_key"],
                "canonical_name": row["canonical_name"],
                "brand": row["brand"],
                "official_url": row["official_url"],
                "final_state": "TECHNICAL_FALLBACK_REQUIRED",
                "attempts": 0,
                "providers_tried": [],
                "provider": "", "reader": "",
                "failure": CLIENT.redact("%s: %s" % (type(exc).__name__, exc)),
                "failure_class": "RUNNER_EXCEPTION",
                "publication_grade": False,
                "bytes": 0,
                "elapsed_seconds": round(time.monotonic() - began, 3),
                "completed_at": _now(),
            }
        journal.append(entry)          # durable BEFORE the next property
        report["properties"].append(entry)
        meter.read("%s:after:%s" % (MARKET, row["identity_key"]))
    else:
        report["outcome"] = "BATCH_COMPLETE"

    report.setdefault("outcome", "BATCH_COMPLETE")
    meter.read("%s:final" % MARKET)
    report["run_end"] = _now()
    report["total_elapsed_seconds"] = round(time.monotonic() - started, 3)
    report["total_cost_usd_minor"] = meter.spent_usd_minor()
    report["zone_delta_usd_minor"] = meter.zone_delta_usd_minor()
    report["cost_samples"] = meter.samples
    report["journal_total"] = journal.count()
    return report


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", default="milwaukee-router-001")
    parser.add_argument("--max-properties", type=int, default=10,
                        help="bounded batch; a kill can never lose more than this")
    parser.add_argument("--no-resume", action="store_true")
    parser.add_argument("--dry-run", action="store_true",
                        help="run the gates and the plan, spend nothing")
    parser.add_argument("--report", default=None)
    args = parser.parse_args(argv)

    report = asyncio.run(run(max_properties=args.max_properties,
                             resume=not args.no_resume,
                             run_id=args.run_id, dry_run=args.dry_run))

    # Per-invocation record. Deliberately NOT a committed artifact: a run can
    # be stopped mid-batch, and a stale per-invocation file sitting beside the
    # journal-derived report is two answers to one question. The committed
    # record is milwaukee-wi_run_report_001.json, which is derived from the
    # durable journal and is therefore always current.
    out = Path(args.report) if args.report else (
        RUN_ROOT / ("%s_last_invocation.json" % MARKET))
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes((json.dumps(report, indent=1, ensure_ascii=False) + "\n")
                    .encode("utf-8"))

    print("outcome            : %s" % report["outcome"])
    if report.get("stop_reason"):
        print("stop reason        : %s" % report["stop_reason"])
    print("queue total        : %d" % report["queue_total"])
    print("planned this batch : %d" % report["planned_this_batch"])
    print("cost (cents)       : %s" % report.get("total_cost_usd_minor"))
    try:
        shown = out.relative_to(REPO)
    except ValueError:
        shown = out
    print("report             : %s" % shown)
    for check in report["preflight"]["checks"]:
        print("  [%s] %-34s %s" % ("ok" if check["ok"] else "BLOCKED",
                                   check["check"], check["detail"]))
    return 0 if report["outcome"] in ("BATCH_COMPLETE", "DRY_RUN_ONLY") else 2


if __name__ == "__main__":
    raise SystemExit(main())
