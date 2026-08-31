# -*- coding: utf-8 -*-
"""PTF-...-PARSER-REPAIR-AND-RETRY-009, Phases 4 and 5.

Prices the retry cohort and runs it. FIRECRAWL ONLY, under a $7.00 cap.

Three things Pass 008 got wrong are structurally prevented here rather than
merely avoided:

  * ``PAL.build_attempt`` derives the ``attempt_id`` from (market, run,
    identity, lane). Pass 008's runner numbered rows by loop index, so
    re-running a slice at a different offset silently reissued ids that were
    already taken and bought two pages twice. A derived id cannot collide with
    itself.
  * Grading is not re-invented. Pass 008's runner asked the record for an
    identity key it does not carry (``bound``, not ``confirmed``) and demanded
    a resolved ``pets_allowed`` on top, so it wrote ``publication_grade:
    false`` on every row including the ten that had acquired evidence. Here the
    adapter's outcome and the ledger's own ``_grade`` decide.
  * The cap is enforced BEFORE each call and against the LIVE credit balance,
    not against an assumed per-row constant. Pass 008 measured 0.95
    credits/attempt where its plan assumed 0.54; a cap checked only against the
    assumption would not have been a cap at all.

Every attempt names its predecessor and the material change that permits it.
The original attempts are untouched.
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

MARKET = "detroit-ann-arbor-mi"
WORK_ORDER = "PTF-DETROIT-ANN-ARBOR-PROPERTY-CODE-PARSER-REPAIR-AND-RETRY-009"
RUN_ID = "detroit-firecrawl-009-retry"
AS_OF = "2026-08-29"

#: The authorised additional cap. Not the Pass 008 cap, and not cumulative.
CAP_USD = 7.00

#: MEASURED in Pass 008: 62 credits over 65 attempts, at the repo's recorded
#: dollar equivalent of $0.13358/credit. The plan's old 0.54 assumption is not
#: used -- it understated that run by nearly half.
CREDITS_PER_ATTEMPT = 62.0 / 65.0
USD_PER_CREDIT = 0.0721333333333333 / 0.54
USD_PER_ATTEMPT = CREDITS_PER_ATTEMPT * USD_PER_CREDIT

LANE = "firecrawl"
READER_FOR = {"IHG": "ihg", "CHOICE": "choice_static", "WYNDHAM": "wyndham"}

LP = _REPO_ROOT / "launch_packages" / "pettripfinder"
COHORT_PATH = LP / "detroit_ann_arbor_retry_cohort_009.json"
LEDGER_PATH = LP / "ptf_paid_attempt_ledger_001.json"
PLAN_PATH = LP / "detroit_ann_arbor_retry_cost_plan_009.json"
RUN_PATH = LP / "detroit_ann_arbor_retry_run_009.json"
RUN_DIR = (_REPO_ROOT / "data" / "worker_runs" / "pettripfinder"
           / "detroit-ann-arbor-retry-009")


def load(path: Path) -> Dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_lf(path: Path, doc) -> None:
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8", newline="\n")


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


def cost_plan(rows: List[Dict], credits_before: Optional[float]) -> Dict:
    """Priced at the MEASURED rate, and truncated mechanically if it does not
    fit. Never 'run until the cap is exceeded'."""
    affordable = int(CAP_USD // USD_PER_ATTEMPT)
    this_run = min(len(rows), affordable)
    plan = OrderedDict([
        ("schema", "ptf-detroit-ann-arbor-retry-cost-plan/1.0"),
        ("work_order", WORK_ORDER), ("market_id", MARKET), ("as_of", AS_OF),
        ("authorisation", OrderedDict([
            ("lane", LANE), ("hard_cap_usd", CAP_USD),
            ("bright_data", "FORBIDDEN"), ("web_unlocker", "FORBIDDEN"),
            ("google_places", "FORBIDDEN"),
            ("cohort", "the parser-defect retry rows only; no expansion"),
        ])),
        ("unit_cost", OrderedDict([
            ("credits_per_attempt", round(CREDITS_PER_ATTEMPT, 4)),
            ("usd_per_credit", round(USD_PER_CREDIT, 6)),
            ("usd_per_attempt", round(USD_PER_ATTEMPT, 6)),
            ("basis", "MEASURED in Pass 008: 62 credits over 65 attempts. The "
                      "Pass 008 plan's 0.54 credits/attempt came from 203 "
                      "older ledger rows and understated that run by nearly "
                      "half, so it is not reused."),
        ])),
        ("cohort", OrderedDict([
            ("retry_rows", len(rows)),
            ("affordable_under_cap", affordable),
            ("rows_this_run", this_run),
            ("truncated_before_spending", this_run < len(rows)),
        ])),
        ("projected", OrderedDict([
            ("attempts", this_run),
            ("credits_required", round(this_run * CREDITS_PER_ATTEMPT, 2)),
            ("worst_case_usd", round(this_run * USD_PER_ATTEMPT, 2)),
            ("margin_under_cap",
             round(CAP_USD - this_run * USD_PER_ATTEMPT, 2)),
            ("worst_case_is_every_attempt_failing",
             "Yes. Cost is denominated in ATTEMPTS: a refusal bills the same "
             "as a good page, which is precisely how Pass 008 spent $8.28 for "
             "ten answers."),
        ])),
        ("account", OrderedDict([
            ("firecrawl_credits_before", credits_before),
            ("credits_required", round(this_run * CREDITS_PER_ATTEMPT, 2)),
            ("sufficient", (credits_before is None
                            or credits_before >= this_run * CREDITS_PER_ATTEMPT)),
        ])),
    ])
    write_lf(PLAN_PATH, plan)
    return plan


def run() -> None:
    cohort = load(COHORT_PATH)
    rows = cohort["retry_cohort"]
    ledger = load(LEDGER_PATH)
    census = {row["identity_key"]: row for row in
              load(LP / "identity_census" / ("%s.json" % MARKET))["hotels"]}
    RUN_DIR.mkdir(parents=True, exist_ok=True)

    # A page this RUN has already bought is never bought again, whatever
    # slice is asked for. Pass 008 relied on the caller passing a correct
    # offset and bought two pages twice when it did not; the ledger, not
    # the caller's arithmetic, decides what is left to do.
    already = {attempt["identity_key"] for attempt in ledger["attempts"]
               if attempt.get("run_id") == RUN_ID}
    done_before = len(already)
    rows = [row for row in rows if row["identity_key"] not in already]

    credits_before = FC.credits_remaining()
    plan = cost_plan(rows, credits_before)
    limit = plan["cohort"]["rows_this_run"]
    # An optional smaller slice, for proving the repaired gate admits a
    # page before committing the whole cohort to it.
    if len(sys.argv) > 1:
        limit = min(limit, int(sys.argv[1]))
    rows = rows[:limit]

    print("=== Phase 4: cost plan ===")
    print("  already bought    :", done_before, "(skipped)")
    print("  retry rows        :", plan["cohort"]["retry_rows"])
    print("  affordable at cap :", plan["cohort"]["affordable_under_cap"])
    print("  rows this run     :", limit,
          "(truncated)" if plan["cohort"]["truncated_before_spending"] else "")
    print("  worst case        : $%.2f of $%.2f (%.1f credits)"
          % (plan["projected"]["worst_case_usd"], CAP_USD,
             plan["projected"]["credits_required"]))
    print("  credits before    :", credits_before)
    print()
    print("=== Phase 5: running the retry cohort (firecrawl only) ===")

    results: List[Dict] = []
    outcomes: Counter = Counter()

    def flush() -> None:
        ledger["count"] = len(ledger["attempts"])
        write_lf(LEDGER_PATH, ledger)

    for number, row in enumerate(rows, 1):
        key = row["identity_key"]
        brand = row["brand"]
        crow = census.get(key) or {}
        expected_code = row["property_code_expected"]

        # The cap, checked BEFORE the call against the LIVE balance where the
        # vendor will report one. An assumed rate is a projection; the balance
        # is the fact.
        spent_credits = ((credits_before - FC.credits_remaining())
                         if credits_before is not None else
                         len(results) * CREDITS_PER_ATTEMPT)
        spent_usd = spent_credits * USD_PER_CREDIT
        if spent_usd + USD_PER_ATTEMPT > CAP_USD:
            print("  STOP: the next attempt would exceed the $%.2f cap "
                  "($%.2f spent)" % (CAP_USD, spent_usd))
            break

        target = BC.CaptureTarget(
            slug=crow.get("slug") or "", hotel=crow.get("canonical_name") or "",
            requested_url=row["canonical_url"], property_code=expected_code,
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
            envelope = jsonable(extraction) or {}
            reading = envelope.get("reading") or {}
            files = ((envelope.get("artifacts") or {}).get("files") or {})
            rendered = files.get("rendered.html") or {}
            identity = jsonable(getattr(record, "identity", None)) or {}
            outcome = (getattr(record, "outcome", "")
                       or ("ACQUISITION_FAILURE" if error else ""))
            # The adapter reaches VALID only after assess_identity confirms and
            # a non-generic policy block is located and persisted. That is the
            # publication-grade test; it is not re-derived here.
            acquired = outcome == "VALID" and bool(reading.get("found"))

            source = OrderedDict([
                ("identity_key", key),
                ("canonical_name", crow.get("canonical_name") or "",),
                ("brand", brand),
                ("property_code", expected_code),
                # ``official_url`` is one of the four names the ledger's
                # own adapter recognises. A field it does not know leaves
                # canonical_url empty, and an empty canonical_url is a
                # paid page that no future market can see it already
                # bought.
                ("official_url", row["canonical_url"]),
                ("address", crow.get("address") or ""),
                ("postal_code", crow.get("postal_code") or ""),
                ("phone", crow.get("phone") or ""),
                ("provider", LANE),
                ("providers_tried", [LANE]),
                ("reader", READER_FOR.get(brand, "")),
                ("attempted_at", started),
                ("outcome", outcome),
                ("publication_grade", acquired),
                ("artifact_path", str(rendered.get("path") or "")),
                ("content_hash", str(rendered.get("sha256") or "")),
            ])
            attempt = PAL.build_attempt(
                source, market_id=MARKET, work_order=WORK_ORDER,
                run_id=RUN_ID, lane=LANE,
                cost_usd_minor=USD_PER_ATTEMPT * 100,
                firecrawl_credits=CREDITS_PER_ATTEMPT,
                predecessor_attempt_id=row.get("predecessor_attempt_id") or "",
                material_change_reason=row["material_change_reason"])
            ledger["attempts"].append(attempt)
            flush()                                  # durable, as it happens

        outcomes[outcome or "ACQUISITION_FAILURE"] += 1
        results.append(OrderedDict([
            ("attempt_id", attempt["attempt_id"]),
            ("identity_key", key),
            ("canonical_name", crow.get("canonical_name") or ""),
            ("brand", brand),
            ("canonical_url", row["canonical_url"]),
            ("property_code_expected", expected_code),
            ("property_code_parsed_from_final_url",
             PS.property_code(getattr(record, "final_url", "") or "", brand)),
            ("property_code_parsed_from_requested_url",
             PS.property_code(row["canonical_url"], brand)),
            ("firecrawl_outcome", outcome or "ACQUISITION_FAILURE"),
            ("identity_verdict", OrderedDict([
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
            ("artifact_path", str(rendered.get("path") or "")),
            ("artifact_hash", str(rendered.get("sha256") or "")),
            ("publication_grade", acquired),
            ("credits", CREDITS_PER_ATTEMPT),
            ("spend_usd", round(USD_PER_ATTEMPT, 6)),
            ("predecessor_attempt_id", row.get("predecessor_attempt_id") or ""),
            ("material_change_reason", row["material_change_reason"]),
            ("refusal_reason", error or (getattr(record, "detail", "") or "")),
        ]))
        print("  %3d/%d %-42s %-18s %s"
              % (number, len(rows), (crow.get("canonical_name") or "")[:42],
                 outcome or "ACQUISITION_FAILURE", "PUB" if acquired else ""))
        time.sleep(0.4)

    credits_after = FC.credits_remaining()
    credits_spent = ((credits_before - credits_after)
                     if None not in (credits_before, credits_after) else None)
    usd_spent = (credits_spent * USD_PER_CREDIT
                 if credits_spent is not None else None)

    write_lf(RUN_PATH, OrderedDict([
        ("schema", "ptf-detroit-ann-arbor-retry-run/1.0"),
        ("work_order", WORK_ORDER), ("market_id", MARKET), ("as_of", AS_OF),
        ("run_id", RUN_ID), ("lane", LANE),
        ("lanes_forbidden_and_not_used",
         ["brightdata_browser", "brightdata_web_unlocker", "google_places"]),
        ("note",
         "The parser-defect retry cohort, re-run against the repaired identity "
         "gate. Every attempt names its predecessor and the material change "
         "that permits it; the original Pass 008 attempts are unchanged."),
        ("attempts", len(results)),
        ("outcomes", dict(outcomes)),
        ("publication_grade",
         sum(1 for result in results if result["publication_grade"])),
        ("spend", OrderedDict([
            ("authoritative_unit", "firecrawl plan CREDITS"),
            ("credits_before", credits_before),
            ("credits_after", credits_after),
            ("credits_spent", credits_spent),
            ("usd_spent", round(usd_spent, 4) if usd_spent is not None else None),
            ("hard_cap_usd", CAP_USD),
            ("cap_held", usd_spent is None or usd_spent <= CAP_USD),
            ("measured_credits_per_attempt",
             round(credits_spent / len(results), 4)
             if credits_spent is not None and results else None),
        ])),
        ("results", results),
    ]))

    print()
    print("attempts:", len(results), "| outcomes:", dict(outcomes))
    print("publication-grade:",
          sum(1 for result in results if result["publication_grade"]))
    print("credits %s -> %s (spent %s) | $%.4f of $%.2f"
          % (credits_before, credits_after, credits_spent,
             usd_spent or 0.0, CAP_USD))
    print("wrote", RUN_PATH.name)


if __name__ == "__main__":
    run()
