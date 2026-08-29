# -*- coding: utf-8 -*-
"""PTF-DETROIT-ANN-ARBOR-BRIGHTDATA-PILOT-013, Phase 3.

Runs the admitted pilot. ONE SANCTIONED PAID ATTEMPT PER ROW.

``cross_brand_capture.run_attempt`` is called, not ``capture_property``: the
latter retries up to three times per provider, and this order forbids automatic
second attempts. A row that fails is recorded as it failed.

NO ESCALATION. The registry lists ``brightdata_web_unlocker`` as a fallback for
both families; it is not the sanctioned path for these rows and is not called.
Nor is Firecrawl, which has already answered a different part of this market and
whose rates must not be allowed to leak into this measurement.

EVERY ATTEMPT IS WRITTEN TO THE LEDGER IN A ``finally``, before anything can
raise. Pass 008 learned that the hard way: a grading error after a fetch left a
paid attempt with no ledger row, and an unrecorded spend is one a future cohort
will pay again.

COST IS MEASURED, NOT ASSUMED. The zone meter is read before and after. Bright
Data reports zone cost MONTH-TO-DATE and settles UPWARD after a run, so the
delta is a floor at the moment it is taken, and it is labelled that way.
"""
from __future__ import annotations

import asyncio
import json
import sys
from collections import Counter, OrderedDict
from datetime import datetime, timezone
from pathlib import Path
from typing import Dict, List

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.acquisition import paid_attempt_ledger as PAL  # noqa: E402
from scripts.pettripfinder.brightdata import browser_capture as BC        # noqa: E402
from scripts.pettripfinder.brightdata import client                       # noqa: E402
from scripts.pettripfinder.brightdata import cross_brand_capture as CBC   # noqa: E402
from scripts.pettripfinder import (                                       # noqa: E402
    detroit_ann_arbor_brightdata_pilot_013 as P13)

MARKET = P13.MARKET
WORK_ORDER = P13.WORK_ORDER
RUN_ID = P13.RUN_ID
LANE = P13.LANE
CAP_USD = P13.CAP_USD
CEILING = P13.USD_CEILING_PER_ATTEMPT

LP = P13.LP
LEDGER_PATH = P13.LEDGER_PATH
RUN_PATH = LP / "detroit_ann_arbor_brightdata_run_013.json"
RUN_DIR = (_REPO_ROOT / "data" / "worker_runs" / "pettripfinder"
           / "detroit-ann-arbor-brightdata-013")

#: Bright Data sessions are slow and this is a paid lane; a short pause between
#: sessions keeps the run from stacking managed browsers on top of each other.
PAUSE_SECONDS = 3.0


def jsonable(obj):
    if obj is None or isinstance(obj, (str, int, float, bool)):
        return obj
    if isinstance(obj, dict):
        return {str(k): jsonable(v) for k, v in obj.items()}
    if isinstance(obj, (list, tuple)):
        return [jsonable(v) for v in obj]
    for attr in ("to_dict", "_asdict"):
        if hasattr(obj, attr):
            return jsonable(getattr(obj, attr)())
    if hasattr(obj, "__dict__"):
        return {k: jsonable(v) for k, v in vars(obj).items()
                if not k.startswith("_")}
    return str(obj)


#: A SECOND CONCURRENT INVOCATION IS A DUPLICATE BUY. The "already bought"
#: guard reads the ledger at startup, so it cannot see rows a run still has in
#: flight -- which is exactly how this pilot spent $2.64 against a $2.28 cap:
#: the run was launched in the background, judged stalled, and launched again
#: while the first was still working. The lock makes the mistake impossible
#: rather than merely discouraged.
LOCK_PATH = RUN_DIR / ".run-in-progress.lock"


def acquire_lock() -> None:
    RUN_DIR.mkdir(parents=True, exist_ok=True)
    try:
        handle = open(LOCK_PATH, "x", encoding="utf-8")
    except FileExistsError:
        raise SystemExit(
            "REFUSING TO START: %s exists, so another invocation of this paid "
            "run is already in progress. A second concurrent run re-buys the "
            "pages the first has in flight, because the already-bought guard "
            "reads the ledger at startup. If you are certain no run is active, "
            "delete the lock file." % LOCK_PATH)
    handle.write(datetime.now(timezone.utc).isoformat())
    handle.close()


def release_lock() -> None:
    try:
        LOCK_PATH.unlink()
    except FileNotFoundError:
        pass


async def main() -> None:
    acquire_lock()
    admitted = P13.load(P13.ADMITTED_PATH)
    plan = P13.load(P13.PLAN_PATH)
    rows = admitted["admitted_rows"][:plan["cohort"]["rows_this_run"]]
    ledger = P13.load(LEDGER_PATH)
    census = {row["identity_key"]: row for row in
              P13.load(LP / "identity_census" / ("%s.json" % MARKET))["hotels"]}
    RUN_DIR.mkdir(parents=True, exist_ok=True)

    # A page this run already bought is never bought again, whatever slice is
    # asked for. The ledger decides what is left, not the caller's arithmetic.
    already = {attempt["identity_key"] for attempt in ledger["attempts"]
               if attempt.get("run_id") == RUN_ID}
    rows = [row for row in rows if row["identity_key"] not in already]
    # An optional smaller slice, for proving a lane this market has never used
    # actually reaches a page before committing the whole cohort to it.
    if len(sys.argv) > 1:
        rows = rows[:int(sys.argv[1])]

    before = client.read_usage("pre-%s" % RUN_ID)
    print("zone %s | month-to-date $%.2f | balance $%.2f"
          % (before.zone, (before.cost_month_usd_minor or 0) / 100.0,
             (before.balance_usd_minor or 0) / 100.0))
    print("rows this run: %d (already bought: %d)" % (len(rows), len(already)))
    print()

    results: List[Dict] = []
    outcomes: Counter = Counter()

    def flush() -> None:
        ledger["count"] = len(ledger["attempts"])
        P13.write_lf(LEDGER_PATH, ledger)

    for number, row in enumerate(rows, 1):
        key = row["identity_key"]
        crow = census.get(key) or {}

        # The cap, enforced BEFORE the call and against the CEILING -- the
        # conservative figure, because the meter lags and cannot be trusted
        # mid-run to say what has already been spent.
        if (len(results) + 1) * CEILING > CAP_USD + 1e-9:
            print("STOP: the next attempt would exceed the $%.2f cap" % CAP_USD)
            break

        target = BC.CaptureTarget(
            slug=crow.get("slug") or "", hotel=crow.get("canonical_name") or "",
            requested_url=row["canonical_url"],
            property_code=row.get("property_code") or "",
            market_id=MARKET, normalized_name=key, identity_key=key,
            street_identity=crow.get("street_identity") or "",
            expected_postal_code=crow.get("postal_code") or "",
            expected_street=crow.get("address") or "",
            expected_phone=crow.get("phone") or "",
            expected_locality=crow.get("city") or "",
            identity_brand=row["brand"], census_matched=True, census_note="")

        started = datetime.now(timezone.utc).isoformat()
        record, extraction, error = None, None, ""
        try:
            record, extraction = await CBC.run_attempt(
                target, 1, run_dir=RUN_DIR, brand=row["brand"])
        except Exception as exc:                                 # noqa: BLE001
            error = client.redact(str(exc))[:250]
        finally:
            envelope = jsonable(extraction) or {}
            reading = envelope.get("reading") or {}
            files = ((envelope.get("artifacts") or {}).get("files") or {})
            rendered = (files.get("rendered.html") or files.get("page.html")
                        or {})
            identity = jsonable(getattr(record, "identity", None)) or {}
            outcome = (getattr(record, "outcome", "")
                       or ("ACQUISITION_FAILURE" if error else ""))
            detail = error or (getattr(record, "detail", "") or "")
            acquired = outcome == "VALID" and bool(reading.get("found"))

            source = OrderedDict([
                ("identity_key", key),
                ("canonical_name", crow.get("canonical_name") or ""),
                ("brand", row["brand"]),
                ("property_code", row.get("property_code") or ""),
                ("official_url", row["canonical_url"]),
                ("address", crow.get("address") or ""),
                ("postal_code", crow.get("postal_code") or ""),
                ("phone", crow.get("phone") or ""),
                ("provider", LANE), ("providers_tried", [LANE]),
                ("reader", row.get("reader") or ""),
                ("attempted_at", started),
                ("outcome", outcome),
                ("publication_grade", acquired),
                ("artifact_path", str(rendered.get("path")
                                      or getattr(record, "artifact_dir", "")
                                      or "")),
                ("content_hash", str(rendered.get("sha256") or "")),
            ])
            attempt = PAL.build_attempt(
                source, market_id=MARKET, work_order=WORK_ORDER,
                run_id=RUN_ID, lane=LANE,
                cost_usd_minor=CEILING * 100,
                material_change_reason="")
            if not attempt.get("canonical_url"):
                raise SystemExit("refusing a ledger row with an empty "
                                 "canonical_url for %r" % key)
            ledger["attempts"].append(attempt)
            flush()

        outcomes[outcome or "ACQUISITION_FAILURE"] += 1
        results.append(OrderedDict([
            ("attempt_id", attempt["attempt_id"]),
            ("identity_key", key),
            ("canonical_name", crow.get("canonical_name") or ""),
            ("brand", row["brand"]),
            ("sub_brand", row["sub_brand"]),
            ("city", row["city"]),
            ("canonical_url", row["canonical_url"]),
            ("lane", LANE),
            ("reader", row.get("reader") or ""),
            ("access_result", outcome or "ACQUISITION_FAILURE"),
            ("identity_result", OrderedDict([
                ("confirmed", bool(identity.get("confirmed"))),
                ("binding_method", identity.get("binding_method") or ""),
                ("matched", identity.get("matched") or []),
                ("conflicting", identity.get("conflicting") or []),
            ])),
            ("policy_reading", OrderedDict([
                ("found", bool(reading.get("found"))),
                ("pets_allowed", reading.get("pets_allowed")),
                ("block_text", (reading.get("block_text") or "")[:600]),
                ("brand_generic", bool(reading.get("brand_generic"))),
                ("charges", reading.get("charges") or []),
            ])),
            ("publication_grade", acquired),
            ("artifact_path", str(rendered.get("path")
                                  or getattr(record, "artifact_dir", "") or "")),
            ("artifact_hash", str(rendered.get("sha256") or "")),
            ("cost_ceiling_usd", CEILING),
            ("refusal_reason", detail[:200]),
        ]))
        print("  %2d/%d %-8s %-40s %-18s %s"
              % (number, len(rows), row["brand"],
                 (crow.get("canonical_name") or "")[:40],
                 outcome or "ACQUISITION_FAILURE", "PUB" if acquired else ""))
        await asyncio.sleep(PAUSE_SECONDS)

    after = client.read_usage("post-%s" % RUN_ID)
    spent_minor = ((after.cost_month_usd_minor or 0)
                   - (before.cost_month_usd_minor or 0))

    P13.write_lf(RUN_PATH, OrderedDict([
        ("schema", "ptf-detroit-ann-arbor-brightdata-run/1.0"),
        ("work_order", WORK_ORDER), ("market_id", MARKET),
        ("as_of", P13.AS_OF), ("run_id", RUN_ID), ("lane", LANE),
        ("lanes_forbidden_and_not_used",
         ["firecrawl", "google_places", "brightdata_web_unlocker"]),
        ("attempts_per_row", 1),
        ("automatic_retries", 0),
        ("attempts", len(results)),
        ("outcomes", dict(outcomes)),
        ("publication_grade",
         sum(1 for row in results if row["publication_grade"])),
        ("spend", OrderedDict([
            ("authoritative_unit", "Bright Data zone cost, month-to-date"),
            ("zone", after.zone),
            ("month_to_date_before_usd",
             (before.cost_month_usd_minor or 0) / 100.0),
            ("month_to_date_after_usd",
             (after.cost_month_usd_minor or 0) / 100.0),
            ("measured_delta_usd", spent_minor / 100.0),
            ("bandwidth_before", before.bandwidth_display),
            ("bandwidth_after", after.bandwidth_display),
            ("ceiling_usd", round(len(results) * CEILING, 2)),
            ("hard_cap_usd", CAP_USD),
            ("cap_held", round(len(results) * CEILING, 2) <= CAP_USD),
            ("caveat",
             "Bright Data reports zone cost MONTH-TO-DATE and settles UPWARD "
             "after a run, so this delta is a FLOOR at the moment it was "
             "taken, not a final invoice. The authorised ceiling is what the "
             "cap was enforced against."),
        ])),
        ("results", results),
    ]))

    print()
    print("attempts:", len(results), "| outcomes:", dict(outcomes))
    print("publication-grade:",
          sum(1 for row in results if row["publication_grade"]))
    print("zone cost $%.2f -> $%.2f (delta $%.2f, a floor) | ceiling $%.2f of $%.2f"
          % ((before.cost_month_usd_minor or 0) / 100.0,
             (after.cost_month_usd_minor or 0) / 100.0, spent_minor / 100.0,
             len(results) * CEILING, CAP_USD))
    print("wrote", RUN_PATH.name)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    finally:
        release_lock()
