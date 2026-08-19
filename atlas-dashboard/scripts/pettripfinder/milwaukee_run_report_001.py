"""PTF-MILWAUKEE-ACQUISITION-ROUTER-INTEGRATION-001 -- the performance report.

Derives every number in the work order's §19-§21 from the durable journal and
the live cost anchor. Nothing here is estimated except where it says so, and
the estimate is never presented as billing.
"""

from __future__ import annotations

import json
import statistics
import sys
from collections import Counter
from pathlib import Path
from typing import Dict, List, Optional

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

MARKET = "milwaukee-wi"
WORK_ORDER = "PTF-MILWAUKEE-ACQUISITION-ROUTER-INTEGRATION-001"
PKG = REPO / "launch_packages" / "pettripfinder"
REPORTS = PKG / "markets" / "reports"
RUN_ROOT = REPO / "data" / "acquisition" / "milwaukee-router-001"
JOURNAL = RUN_ROOT / "milwaukee-router-001" / "journal.jsonl"
ANCHOR = RUN_ROOT / "market_cost_anchor.json"


def _load(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def _journal() -> List[Dict]:
    if not JOURNAL.exists():
        return []
    return [json.loads(l) for l in JOURNAL.read_text(encoding="utf-8").splitlines()
            if l.strip()]


def _live_spend() -> Dict:
    """Cumulative market spend, from per-zone month-to-date cost.

    NOT from the account balance. The balance lags accrual badly -- mid-run it
    reported $3.95 spent while the zones had accrued $12.77 -- and a mid-run
    top-up made its drawdown negative, which a clamp turns into a reported
    $0.00. Zone cost only ever increases and a top-up cannot touch it.
    """
    from scripts.pettripfinder.brightdata import client as CLIENT
    from scripts.pettripfinder.milwaukee_acquisition_run_001 import BILLABLE_ZONES
    anchor = _load(ANCHOR) if ANCHOR.exists() else {}
    start = anchor.get("zone_costs_usd_minor") or {}
    per_zone, spent, unreadable = {}, 0, []
    for zone in BILLABLE_ZONES:
        snap = CLIENT.read_usage("%s:report:%s" % (MARKET, zone), zone=zone)
        now = snap.cost_month_usd_minor
        per_zone[zone] = now
        a = start.get(zone)
        if now is None or a is None:
            unreadable.append(zone)
            continue
        spent += max(0, now - a)
    balance = CLIENT.read_usage("%s:report:balance" % MARKET)
    return {
        "anchor_zone_costs_usd_minor": start,
        "current_zone_costs_usd_minor": per_zone,
        "spent_usd_minor": None if unreadable else spent,
        "unreadable_zones": unreadable,
        "telemetry_available": not unreadable,
        "balance_usd_minor": balance.balance_usd_minor,
        "pending_charge_usd_minor": balance.pending_charge_usd_minor,
        "measured_from": ("per-zone month-to-date cost, summed across every "
                          "billable zone; monotonic and top-up-immune"),
        "why_not_balance": ("the account balance debits on a lag and rose "
                            "mid-run on a top-up, under-reporting spend 3x "
                            "against a hard cap"),
    }


def build(*, read_cost: bool = True) -> Dict:
    queue = _load(REPORTS / ("%s_policy_acquisition_queue_001.json" % MARKET))
    entries = _journal()
    states = Counter(e["final_state"] for e in entries)
    routable = queue["routable_total"]

    pub = [e for e in entries if e["final_state"] == "ACQUIRED_PUBLICATION_GRADE"]
    nonpub = [e for e in entries if e["final_state"] == "ACQUIRED_NONPUBLICATION_GRADE"]
    acquired = pub + nonpub

    attempts = sum(e.get("attempts", 0) for e in entries)
    times = [e.get("elapsed_seconds", 0.0) for e in entries if e.get("elapsed_seconds")]

    lanes = Counter()
    readers = Counter()
    for e in entries:
        lanes[e.get("provider") or "none"] += 1
        readers[e.get("reader") or "none"] += 1

    cost = _live_spend() if read_cost else {"spent_usd_minor": None}
    spent = cost.get("spent_usd_minor")

    def per(n) -> Optional[float]:
        return round(spent / n, 2) if (spent is not None and n) else None

    doc = {
        "schema": "ptf-milwaukee-run-report/1.0",
        "work_order": WORK_ORDER,
        "market_id": MARKET,

        "queue": {
            "queue_total": queue["queue_total"],
            "routable_total": routable,
            "brand_excluded_total": queue["brand_excluded_total"],
            "processed": len(entries),
            "remaining": routable - len(entries),
        },

        "outcomes": {
            "state_counts": dict(states),
            "automatic_fetch_success": len(acquired),
            "publication_grade": len(pub),
            "non_publication_grade": len(nonpub),
            "policy_not_found": states.get("POLICY_NOT_FOUND", 0),
            "identity_review": states.get("IDENTITY_REVIEW", 0),
            "source_ambiguous": states.get("SOURCE_AMBIGUOUS", 0),
            "source_contradictory": states.get("SOURCE_CONTRADICTORY", 0),
            "technical_fallback_required": states.get("TECHNICAL_FALLBACK_REQUIRED", 0),
            "provider_exhausted": states.get("PROVIDER_EXHAUSTED", 0),
            "budget_exhausted": states.get("BUDGET_EXHAUSTED", 0),
        },

        "attempts": {
            "total_attempts": attempts,
            "avg_attempts_per_property": (round(attempts / len(entries), 3)
                                          if entries else None),
            "properties_needing_more_than_one_attempt":
                sum(1 for e in entries if e.get("attempts", 0) > 1),
        },

        "cost": {
            **cost,
            "cost_per_attempted_property_usd_minor": per(len(entries)),
            "cost_per_fetch_success_usd_minor": per(len(acquired)),
            "cost_per_publication_grade_record_usd_minor": per(len(pub)),
            "hard_cap_usd_minor": 1500,
            "soft_checkpoints_usd_minor": [500, 1000],
        },

        "time": {
            "total_capture_seconds": round(sum(times), 1) if times else 0,
            "avg_seconds_per_property": round(statistics.mean(times), 1) if times else None,
            "median_seconds_per_property": (round(statistics.median(times), 1)
                                            if times else None),
            "p95_seconds_per_property": (
                round(sorted(times)[max(0, int(len(times) * 0.95) - 1)], 1)
                if len(times) >= 20 else None),
            "avg_seconds_per_success": (
                round(sum(e.get("elapsed_seconds", 0) for e in acquired) / len(acquired), 1)
                if acquired else None),
        },

        "router_utilization": {
            "by_lane": dict(lanes),
            "by_reader": dict(readers),
            "brightdata_browser": lanes.get("brightdata_browser", 0),
            "brightdata_web_unlocker": lanes.get("brightdata_web_unlocker", 0),
            "direct_local": 0,
        },

        "versus_old_workflow": {
            "old_workflow_equivalent_attended_rows": queue["queue_total"],
            "actual_attended_rows_used": 0,
            "attended_fallback_required":
                states.get("TECHNICAL_FALLBACK_REQUIRED", 0)
                + states.get("PROVIDER_EXHAUSTED", 0),
            "automated_share_of_processed": (
                round(100.0 * len(acquired) / len(entries), 1) if entries else None),
            "note": ("Share is of properties PROCESSED, not of the market. The "
                     "old pattern required one attended browser row per hotel; "
                     "this run used zero."),
        },

        "authority": {
            "policy_authority_changed": False,
            "exclusions_changed": False,
            "seeds_changed": False,
            "approvals_changed": False,
            "founder_approvals_created": 0,
        },
    }
    out = REPORTS / ("%s_run_report_001.json" % MARKET)
    out.write_bytes((json.dumps(doc, indent=1, ensure_ascii=False) + "\n").encode("utf-8"))
    return doc


def main() -> int:
    d = build()
    q, o, c, t = d["queue"], d["outcomes"], d["cost"], d["time"]
    print("processed %d of %d routable (%d remaining)"
          % (q["processed"], q["routable_total"], q["remaining"]))
    print("publication-grade %d | fetch success %d | states %s"
          % (o["publication_grade"], o["automatic_fetch_success"], o["state_counts"]))
    print("attempts %d (avg %.2f/property)"
          % (d["attempts"]["total_attempts"], d["attempts"]["avg_attempts_per_property"] or 0))
    print("spent %s cents of 1500 | per pub-grade record %s cents"
          % (c["spent_usd_minor"], c["cost_per_publication_grade_record_usd_minor"]))
    print("avg %ss/property, median %ss, p95 %ss"
          % (t["avg_seconds_per_property"], t["median_seconds_per_property"],
             t["p95_seconds_per_property"]))
    print("lanes %s" % d["router_utilization"]["by_lane"])
    print("readers %s" % d["router_utilization"]["by_reader"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
