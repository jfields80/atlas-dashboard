# -*- coding: utf-8 -*-
"""PTF-DETROIT-ANN-ARBOR-FIRECRAWL-RATE-LIMIT-RECOVERY-010.

Re-runs the 29 Pass 009 rows that failed on provider rate limiting alone.

WHY THEY FAILED, from Pass 009's own ordering: the run produced nine good
answers, then twelve refusals, then ten more good answers, then seventeen
refusals. That is a request-per-minute budget of roughly ten being hit,
released, and hit again -- not a wall.

WHAT MADE IT WORSE was the pacing. A successful capture takes about seven
seconds because ``waitFor`` is 6000ms, but a rate-limited response returns
IMMEDIATELY. Pass 009 slept a flat 0.4s between rows, so the moment the budget
tripped the loop began firing several requests a second against a limiter that
needed quiet to recover, and it stayed tripped. The fix is not a longer sleep
after a success -- it is pacing measured from the START of each request, and a
real pause after a refusal.

So this order paces two ways:

  * a MINIMUM INTERVAL between request starts, so a fast failure cannot
    accelerate the loop the way it did in 009;
  * a BACKOFF after any rate-limited response, because the budget needs a
    window of quiet, and the next row is what pays for it otherwise.

ONE PROVIDER CALL PER ROW. A row refused again is recorded and left; it is not
retried inside this order.
"""
from __future__ import annotations

import json
import sys
import time
from collections import Counter, OrderedDict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List, Optional

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.acquisition import firecrawl_capture as FC  # noqa: E402
from scripts.pettripfinder.acquisition import paid_attempt_ledger as PAL  # noqa: E402
from scripts.pettripfinder.brightdata import browser_capture as BC  # noqa: E402
from scripts.pettripfinder.brightdata import policy_surface as PS  # noqa: E402
# The 009 runner's helpers, reused rather than restated. Only the paced loop
# is new here, and it is the whole reason this order exists.
from scripts.pettripfinder import (                                # noqa: E402
    detroit_ann_arbor_retry_run_009 as R9)

MARKET = "detroit-ann-arbor-mi"
WORK_ORDER = "PTF-DETROIT-ANN-ARBOR-FIRECRAWL-RATE-LIMIT-RECOVERY-010"
RUN_ID = "detroit-firecrawl-010-ratelimit"
PRIOR_RUN = "detroit-firecrawl-009-retry"
AS_OF = "2026-08-29"

MATERIAL_CHANGE = "RATE_LIMIT_RECOVERY_AFTER_PACING_CHANGE"

CAP_USD = 5.00
#: Measured exactly in Pass 009: 19 billed attempts consumed 19 credits.
CREDITS_PER_BILLED_ATTEMPT = 1.0
USD_PER_CREDIT = 0.0721333333333333 / 0.54

#: Seconds between request STARTS. Pass 009's budget released after roughly ten
#: requests a minute, so this sits deliberately outside that: a capture already
#: takes about seven seconds, and the interval only bites when a request
#: returns fast -- which is exactly the case that broke 009.
MIN_INTERVAL_SECONDS = 13.0
#: Quiet the limiter needs after refusing, paid before the NEXT row rather than
#: by retrying this one.
RATE_LIMIT_BACKOFF_SECONDS = 75.0

LANE = "firecrawl"
LP = _REPO_ROOT / "launch_packages" / "pettripfinder"
C009 = LP / "detroit_ann_arbor_retry_classification_009.json"
COHORT_PATH = LP / "detroit_ann_arbor_rate_limit_cohort_010.json"
LEDGER_PATH = LP / "ptf_paid_attempt_ledger_001.json"
RUN_PATH = LP / "detroit_ann_arbor_rate_limit_run_010.json"
RUN_DIR = (_REPO_ROOT / "data" / "worker_runs" / "pettripfinder"
           / "detroit-ann-arbor-ratelimit-010")


def build_cohort() -> Dict:
    """Phase 1, mechanically. Every condition is checked, none assumed."""
    classification = R9.load(C009)
    ledger = R9.load(LEDGER_PATH)
    qualification = R9.load(
        LP / "detroit_ann_arbor_firecrawl_lane_qualification_008.json")
    code_by_key = {row["identity_key"]: (row.get("property_code") or "")
                   for row in qualification["qualified_rows"]}
    # The classification artifact carries the ledger's CANONICAL url -- host
    # and path, no scheme -- which parses but does not fetch. The request URL
    # comes from the 009 cohort, which holds the routed form.
    # ...and the routed form comes from the market's own routing shard, which
    # is the authority for what URL a property is fetched at. The 008 ledger
    # stored the NORMALIZED url (host and path, no scheme) and every artifact
    # downstream inherited it; Firecrawl happens to accept that, but a routed
    # URL is what the market actually decided and is what should be requested.
    request_url = {}
    for route in R9.load(
            LP / "markets" / "authority" / MARKET / "identity_routing.json"
    )["routes"]:
        if route["status"] != "ROUTING_CONFIRMED":
            continue
        request_url[route["hotel_ref"]["identity_key"]] = (
            route.get("official_property_url") or "")

    # Any attempt that has since ANSWERED this identity, from any run.
    resolved = {attempt["identity_key"] for attempt in ledger["attempts"]
                if attempt.get("market_id") == MARKET
                and attempt.get("publication_grade")}

    rows, rejected = [], []
    for result in classification["results"]:
        key = result["identity_key"]
        expected = (code_by_key.get(key) or "").lower()
        url = request_url.get(key) or ""
        parsed = PS.property_code(url, result["brand"]).lower()
        checks = OrderedDict([
            ("previous_outcome_was_rate_limited", bool(result["rate_limited"])),
            ("no_property_document_reached", result["reading"] is None),
            ("routed_url_available", bool(url)),
            ("no_policy_result_produced", result["reading"] is None),
            ("prior_billed_cost_was_zero", not result["billed"]),
            ("not_since_resolved", key not in resolved),
            ("parser_now_resolves_expected_code",
             bool(expected) and parsed == expected),
        ])
        if all(checks.values()):
            rows.append(OrderedDict([
                ("identity_key", key),
                ("canonical_name", result["canonical_name"]),
                ("brand", result["brand"]),
                ("canonical_url", url),
                ("property_code_expected", expected),
                ("property_code_parsed", parsed),
                ("predecessor_attempt_id", result["attempt_id"]),
                ("material_change_reason", MATERIAL_CHANGE),
            ]))
        elif result["rate_limited"]:
            rejected.append(OrderedDict([
                ("identity_key", key),
                ("failed_checks", [name for name, ok in checks.items()
                                   if not ok]),
            ]))

    doc = OrderedDict([
        ("schema", "ptf-detroit-ann-arbor-rate-limit-cohort/1.0"),
        ("work_order", WORK_ORDER), ("market_id", MARKET), ("as_of", AS_OF),
        ("lane", LANE),
        ("material_change_reason", MATERIAL_CHANGE),
        ("membership_test",
         "all six conditions, checked per row: the previous outcome was "
         "RATE_LIMITED, no property document was reached, no policy result was "
         "produced, the failed attempt billed nothing, no later attempt has "
         "resolved the identity, and the repaired parser now returns the "
         "expected property code."),
        ("cohort_size", len(rows)),
        ("rate_limited_rows_rejected", len(rejected)),
        ("rejected_rows", rejected),
        ("by_brand", dict(Counter(row["brand"] for row in rows))),
        ("cohort", rows),
    ])
    R9.write_lf(COHORT_PATH, doc)
    return doc


def run() -> None:
    cohort = build_cohort()
    rows = cohort["cohort"]
    print("=== Phase 1: exact cohort ===")
    print("  rows qualifying   :", len(rows), cohort["by_brand"])
    print("  rejected          :", cohort["rate_limited_rows_rejected"])
    if len(rows) > 29:
        raise SystemExit("cohort exceeds the authorised 29 rows")

    ledger = R9.load(LEDGER_PATH)
    census = {row["identity_key"]: row for row in
              R9.load(LP / "identity_census" / ("%s.json" % MARKET))["hotels"]}
    RUN_DIR.mkdir(parents=True, exist_ok=True)

    # A page this run already bought is never bought again, whatever slice is
    # asked for -- the ledger decides what is left, not the caller's arithmetic.
    already = {attempt["identity_key"] for attempt in ledger["attempts"]
               if attempt.get("run_id") == RUN_ID}
    rows = [row for row in rows if row["identity_key"] not in already]

    credits_before = FC.credits_remaining()
    usd_per_attempt = CREDITS_PER_BILLED_ATTEMPT * USD_PER_CREDIT
    affordable = int(CAP_USD // usd_per_attempt)
    if len(rows) > affordable:                # truncate BEFORE spending
        print("  truncating %d -> %d rows to stay under the $%.2f cap"
              % (len(rows), affordable, CAP_USD))
        rows = rows[:affordable]

    print()
    print("=== Phase 2/3: paced run (interval %.0fs, backoff %.0fs) ==="
          % (MIN_INTERVAL_SECONDS, RATE_LIMIT_BACKOFF_SECONDS))
    print("  already bought    :", len(already), "(skipped)")
    print("  rows this run     :", len(rows))
    print("  worst case        : $%.2f of $%.2f"
          % (len(rows) * usd_per_attempt, CAP_USD))
    print("  credits before    :", credits_before)
    print()

    results: List[Dict] = []
    outcomes: Counter = Counter()
    next_allowed_at = 0.0

    def flush() -> None:
        ledger["count"] = len(ledger["attempts"])
        R9.write_lf(LEDGER_PATH, ledger)

    for number, row in enumerate(rows, 1):
        key = row["identity_key"]
        brand = row["brand"]
        crow = census.get(key) or {}

        spent_credits = ((credits_before - FC.credits_remaining())
                         if credits_before is not None else
                         len(results) * CREDITS_PER_BILLED_ATTEMPT)
        spent_usd = spent_credits * USD_PER_CREDIT
        if spent_usd + usd_per_attempt > CAP_USD:
            print("  STOP: the next attempt would exceed the $%.2f cap "
                  "($%.2f spent)" % (CAP_USD, spent_usd))
            break

        # Pacing measured from the START of the previous request, so a fast
        # refusal cannot accelerate the loop.
        wait = next_allowed_at - time.monotonic()
        if wait > 0:
            time.sleep(wait)
        next_allowed_at = time.monotonic() + MIN_INTERVAL_SECONDS

        target = BC.CaptureTarget(
            slug=crow.get("slug") or "", hotel=crow.get("canonical_name") or "",
            requested_url=row["canonical_url"],
            property_code=row["property_code_expected"],
            market_id=MARKET, normalized_name=key, identity_key=key,
            street_identity=crow.get("street_identity") or "",
            expected_postal_code=crow.get("postal_code") or "",
            expected_street=crow.get("address") or "",
            expected_phone=crow.get("phone") or "",
            expected_locality=crow.get("city") or "",
            identity_brand=brand, census_matched=True, census_note="")

        started = datetime.now(timezone.utc).isoformat()
        record, extraction, error = None, None, ""
        try:
            record, extraction = FC.run_attempt(target, 1, run_dir=RUN_DIR,
                                                brand=brand)
        except Exception as exc:                                 # noqa: BLE001
            error = FC.redact(str(exc))[:250]
        finally:
            envelope = R9.jsonable(extraction) or {}
            reading = envelope.get("reading") or {}
            files = ((envelope.get("artifacts") or {}).get("files") or {})
            rendered = files.get("rendered.html") or {}
            identity = R9.jsonable(getattr(record, "identity", None)) or {}
            outcome = (getattr(record, "outcome", "")
                       or ("ACQUISITION_FAILURE" if error else ""))
            detail = error or (getattr(record, "detail", "") or "")
            rate_limited = "RATE_LIMITED" in detail
            acquired = outcome == "VALID" and bool(reading.get("found"))

            source = OrderedDict([
                ("identity_key", key),
                ("canonical_name", crow.get("canonical_name") or ""),
                ("brand", brand),
                ("property_code", row["property_code_expected"]),
                # one of the four names the ledger's adapter recognises; an
                # unknown name leaves canonical_url empty and hides a paid page
                ("official_url", row["canonical_url"]),
                ("address", crow.get("address") or ""),
                ("postal_code", crow.get("postal_code") or ""),
                ("phone", crow.get("phone") or ""),
                ("provider", LANE), ("providers_tried", [LANE]),
                ("reader", R9.READER_FOR.get(brand, "")),
                ("attempted_at", started),
                ("outcome", outcome),
                ("publication_grade", acquired),
                ("artifact_path", str(rendered.get("path") or "")),
                ("content_hash", str(rendered.get("sha256") or "")),
            ])
            attempt = PAL.build_attempt(
                source, market_id=MARKET, work_order=WORK_ORDER,
                run_id=RUN_ID, lane=LANE,
                # a rate-limited call bills nothing; recording a cost for it
                # would overstate the spend and mislead the next cohort's price
                cost_usd_minor=(0.0 if rate_limited else usd_per_attempt * 100),
                firecrawl_credits=(0.0 if rate_limited
                                   else CREDITS_PER_BILLED_ATTEMPT),
                predecessor_attempt_id=row["predecessor_attempt_id"],
                material_change_reason=MATERIAL_CHANGE)
            if not attempt.get("canonical_url"):
                raise SystemExit("refusing to write a ledger row with an empty "
                                 "canonical_url for %r" % key)
            ledger["attempts"].append(attempt)
            flush()

        outcomes[("RATE_LIMITED" if rate_limited
                  else outcome or "ACQUISITION_FAILURE")] += 1
        results.append(OrderedDict([
            ("attempt_id", attempt["attempt_id"]),
            ("identity_key", key),
            ("canonical_name", crow.get("canonical_name") or ""),
            ("brand", brand),
            ("canonical_url", row["canonical_url"]),
            ("property_code_expected", row["property_code_expected"]),
            ("property_code_parsed",
             PS.property_code(getattr(record, "final_url", "") or "", brand)),
            ("predecessor_attempt_id", row["predecessor_attempt_id"]),
            ("material_change_reason", MATERIAL_CHANGE),
            ("firecrawl_outcome", outcome or "ACQUISITION_FAILURE"),
            ("rate_limited", rate_limited),
            ("billed", not rate_limited),
            ("credits", 0.0 if rate_limited else CREDITS_PER_BILLED_ATTEMPT),
            ("identity_verdict", OrderedDict([
                ("confirmed", bool(identity.get("confirmed"))),
                ("binding_method", identity.get("binding_method") or ""),
            ])),
            ("policy_reading", OrderedDict([
                ("found", bool(reading.get("found"))),
                ("pets_allowed", reading.get("pets_allowed")),
                ("block_text", (reading.get("block_text") or "")[:600]),
                ("brand_generic", bool(reading.get("brand_generic"))),
            ])),
            ("artifact_path", str(rendered.get("path") or "")),
            ("artifact_hash", str(rendered.get("sha256") or "")),
            ("publication_grade", acquired),
            ("refusal_reason", detail[:200]),
        ]))
        print("  %3d/%d %-42s %-16s %s"
              % (number, len(rows), (crow.get("canonical_name") or "")[:42],
                 "RATE_LIMITED" if rate_limited
                 else (outcome or "ACQUISITION_FAILURE"),
                 "PUB" if acquired else ""))

        if rate_limited:
            # Do not retry this row. Pay the quiet before the NEXT one.
            print("        ... backing off %.0fs before the next row"
                  % RATE_LIMIT_BACKOFF_SECONDS)
            next_allowed_at = time.monotonic() + RATE_LIMIT_BACKOFF_SECONDS

    credits_after = FC.credits_remaining()
    credits_spent = ((credits_before - credits_after)
                     if None not in (credits_before, credits_after) else None)
    usd_spent = (credits_spent * USD_PER_CREDIT
                 if credits_spent is not None else None)
    reached = [r for r in results if not r["rate_limited"]]

    R9.write_lf(RUN_PATH, OrderedDict([
        ("schema", "ptf-detroit-ann-arbor-rate-limit-run/1.0"),
        ("work_order", WORK_ORDER), ("market_id", MARKET), ("as_of", AS_OF),
        ("run_id", RUN_ID), ("lane", LANE),
        ("lanes_forbidden_and_not_used",
         ["brightdata_browser", "brightdata_web_unlocker", "google_places",
          "paid_discovery"]),
        ("pacing", OrderedDict([
            ("min_interval_seconds", MIN_INTERVAL_SECONDS),
            ("rate_limit_backoff_seconds", RATE_LIMIT_BACKOFF_SECONDS),
            ("measured_from", "the START of each request, so a fast refusal "
                              "cannot accelerate the loop"),
            ("one_call_per_row", True),
        ])),
        ("attempts", len(results)),
        ("outcomes", dict(outcomes)),
        ("reached_the_identity_gate", len(reached)),
        ("publication_grade",
         sum(1 for r in results if r["publication_grade"])),
        ("spend", OrderedDict([
            ("authoritative_unit", "firecrawl plan CREDITS"),
            ("credits_before", credits_before),
            ("credits_after", credits_after),
            ("credits_spent", credits_spent),
            ("usd_spent", round(usd_spent, 4) if usd_spent is not None else None),
            ("hard_cap_usd", CAP_USD),
            ("cap_held", usd_spent is None or usd_spent <= CAP_USD),
        ])),
        ("results", results),
    ]))

    print()
    print("attempts:", len(results), "| outcomes:", dict(outcomes))
    print("reached the gate:", len(reached), "| publication-grade:",
          sum(1 for r in results if r["publication_grade"]))
    print("credits %s -> %s (spent %s) | $%.4f of $%.2f"
          % (credits_before, credits_after, credits_spent,
             usd_spent or 0.0, CAP_USD))
    print("wrote", RUN_PATH.name)


if __name__ == "__main__":
    run()
