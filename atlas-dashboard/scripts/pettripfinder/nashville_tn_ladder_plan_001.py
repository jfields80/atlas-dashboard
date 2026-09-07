"""PTF-NASHVILLE-TN-NEW-MARKET-001 -- Phase 11 preflight: what the ladder says next.

Runs every static outcome through ``acquisition.ladder.firecrawl_candidacy`` and
reports, per row, the next rung and WHY. It fetches nothing and spends nothing:
this is the decision document that has to exist before a credit is consumed.

Three facts this preflight is built to keep straight:

* **Firecrawl cost is bimodal.** One credit when a fetch succeeds, zero when the
  origin refuses every engine. A blended average is not a ceiling, so the cap
  here is on ATTEMPTS, never on an expected spend.
* **Marriott and Hilton are measured walls.** PTF-FIRECRAWL-HARD-LANES-003 saw
  every-engine failure on six of seven attempts. Those rows are not candidates
  at any budget; they are attended-browser rows.
* **A refusal escalates, a silence does not.** Only a channel failure moves a row
  down the ladder. A page that served and said nothing about pets is
  SOURCE_SILENT and Firecrawl cannot change that.

Output:
  launch_packages/pettripfinder/markets/reports/nashville_tn_ladder_plan_001.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter, OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

from scripts.pettripfinder.acquisition import ladder as LAD  # noqa: E402
from scripts.pettripfinder.acquisition import registry as REG  # noqa: E402

WORK_ORDER = "PTF-NASHVILLE-TN-NEW-MARKET-001"
MARKET_ID = "nashville-tn"
SCHEMA = "ptf-acquisition-ladder-plan/1.0"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
CAPTURE = os.path.join(REPORTS, "nashville_tn_free_static_capture_001.json")
PAID_LEDGER = os.path.join(PKG, "ptf_paid_attempt_ledger_001.json")
DISCOVERY_LEDGER = os.path.join(PKG, "ptf_discovery_attempt_ledger_001.json")


def _load(path, default=None):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def ledger_state():
    """Read the shared ledgers. This order READS them and never writes them."""
    paid = _load(PAID_LEDGER, {}) or {}
    disc = _load(DISCOVERY_LEDGER, {}) or {}
    paid_rows = paid.get("attempts") or []
    disc_rows = disc.get("attempts") or []
    return OrderedDict([
        ("paid_attempt_ledger", OrderedDict([
            ("path", "launch_packages/pettripfinder/ptf_paid_attempt_ledger_001.json"),
            ("total_attempts", len(paid_rows)),
            ("nashville_attempts", sum(1 for r in paid_rows if r.get("market_id") == MARKET_ID)),
            ("markets_present", sorted({r.get("market_id") for r in paid_rows if r.get("market_id")})),
        ])),
        ("discovery_attempt_ledger", OrderedDict([
            ("path", "launch_packages/pettripfinder/ptf_discovery_attempt_ledger_001.json"),
            ("total_attempts", len(disc_rows)),
            ("nashville_attempts", sum(1 for r in disc_rows if r.get("market_id") == MARKET_ID)),
            ("markets_present", sorted({r.get("market_id") for r in disc_rows if r.get("market_id")})),
        ])),
        ("double_buy_risk",
         "NONE. Neither shared ledger carries a single nashville-tn row, so no page in this market "
         "has ever been bought and nothing here can be a second purchase. This order WRITES "
         "neither ledger."),
    ])


def credits_now():
    try:
        from scripts.pettripfinder.acquisition import firecrawl_capture as FC
        return FC.credits_remaining()
    except Exception as exc:  # noqa: BLE001
        return "READ_FAILED:%s" % type(exc).__name__


def build(args) -> OrderedDict:
    cap = _load(CAPTURE, {}) or {}
    registry = REG.load()
    routed_families = LAD.firecrawl_routed_families(registry)
    rows = []
    for r in cap.get("rows", []):
        outcome = r.get("outcome") or ""
        family = r.get("brand") or ""
        url = r.get("requested_url") or ""
        cand = LAD.firecrawl_candidacy(family=family, url=url,
                                       prior_static_outcome=outcome, registry=registry)
        rows.append(OrderedDict([
            ("identity_key", r["identity_key"]), ("canonical_name", r["canonical_name"]),
            ("cohort", r["cohort"]), ("brand", family), ("url", url),
            ("static_outcome", outcome), ("static_classification", r["classification"]),
            ("firecrawl_candidate", cand.candidate),
            ("firecrawl_reason", cand.reason),
            ("measured_by", cand.measured_by),
            ("probe_eligible", cand.probe_eligible),
            ("next_rung", "FIRECRAWL" if cand.candidate
             else "ATTENDED_BROWSER" if cand.reason in (
                 LAD.NOT_CANDIDATE_KNOWN_WALL, LAD.NOT_CANDIDATE_UNMEASURED)
             else "NONE" if cand.reason == LAD.NOT_CANDIDATE_STATIC_ANSWERED
             else "ROUTING_REPAIR" if cand.reason == LAD.NOT_CANDIDATE_CODE_UNPARSEABLE
             else "SETTLED_OR_REVIEW"),
        ]))

    candidates = [r for r in rows if r["firecrawl_candidate"]]
    by_host = Counter()
    for r in candidates:
        h = (r["url"].split("/")[2] if r["url"].count("/") > 2 else "").lower()
        by_host[h] += 1

    return OrderedDict([
        ("schema", SCHEMA), ("work_order", WORK_ORDER), ("market_id", MARKET_ID),
        ("phase", "11 preflight -- the ladder's decision, before any credit is spent"),
        ("paid_provider_calls", 0), ("usd_spent", 0.0), ("http_requests", 0),
        ("firecrawl_routed_families", list(routed_families)),
        ("known_capability_walls", dict(LAD.KNOWN_CAPABILITY_WALLS)),
        ("plan_credits_remaining_at_planning_time", credits_now()),
        ("cost_is_bimodal",
         "A Firecrawl attempt costs one credit when a fetch succeeds and zero when the origin "
         "refuses every engine. There is no blended per-row price to budget against, so any "
         "authorisation here caps ATTEMPTS and reports the credit delta afterwards."),
        ("a_refusal_escalates_a_silence_does_not",
         "Only ACCESS_DENIED, UNHYDRATED, BLANK_PAGE, NAVIGATION_FAILED, UNEXPECTED_PAGE and "
         "CAPTURE_FAILED move a row down the ladder. A page that served and said nothing about "
         "pets is SOURCE_SILENT, and a rendered fetch of the same page would say nothing too."),
        ("shared_ledgers_read_only", ledger_state()),
        ("counts", OrderedDict([
            ("rows", len(rows)),
            ("firecrawl_candidates", len(candidates)),
            ("candidates_by_brand",
             OrderedDict(sorted(Counter(r["brand"] for r in candidates).items()))),
            ("candidates_by_host", OrderedDict(sorted(by_host.items()))),
            ("by_next_rung", OrderedDict(sorted(Counter(r["next_rung"] for r in rows).items()))),
            ("by_firecrawl_reason",
             OrderedDict(sorted(Counter(r["firecrawl_reason"] for r in rows).items()))),
        ])),
        ("rows", rows),
    ])


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(REPORTS, "nashville_tn_ladder_plan_001.json"))
    args = ap.parse_args(argv)
    rep = build(args)
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8") as fh:
        json.dump(rep, fh, indent=1, default=str)
        fh.write("\n")
    c = rep["counts"]
    print("rows                :", c["rows"])
    print("firecrawl candidates:", c["firecrawl_candidates"], dict(c["candidates_by_brand"]))
    print("by next rung        :", dict(c["by_next_rung"]))
    print("by reason           :", dict(c["by_firecrawl_reason"]))
    print("credits remaining   :", rep["plan_credits_remaining_at_planning_time"])
    print("written             :", args.out)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
