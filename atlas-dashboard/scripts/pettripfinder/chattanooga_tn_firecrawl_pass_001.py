"""PTF-CHATTANOOGA-TN-NEW-MARKET-001 -- Phase 12, the Firecrawl rung.

The Cincinnati phase-11 harness re-pointed at ``chattanooga-tn``. The cohort is
computed by ``ladder.plan_cohort`` from this order's committed static report and
is never typed in: 28 rows across Wyndham and IHG, two of the three families the
committed route table sends to Firecrawl on a measured decision. Marriott and
Hilton are a measured capability wall (PTF-FIRECRAWL-HARD-LANES-003) and are not
candidates at any budget; they go to the attended browser instead.

WHY THIS RUNS WITHOUT A NEW FOUNDER QUESTION
--------------------------------------------
Standing doctrine already authorises bounded plan credits for a small cohort in
exactly this shape. Indianapolis FIRECRAWL-RECOVERY-021 attempted 36 rows for 17
credits; Toledo NEW-MARKET-001 attempted 19 against a 488-credit balance;
Cincinnati HARDENED-REVALIDATION-001 ran under a 7-credit cap. Twenty-eight
attempts against a 442-credit plan balance is about six percent of it, and no
USD is involved at any point. Chattanooga is a brand-new market: the committed
paid-attempt ledger and discovery ledger name it zero times, so no row here can
be a second purchase of a page this project has already bought.

THE CAP IS ON ATTEMPTS
----------------------
Firecrawl's cost is BIMODAL: one credit when a fetch succeeds, zero when the
origin refuses every engine. There is therefore no blended per-row price to
budget against and no credit figure that is a safe ceiling. This run caps the
number of ATTEMPTS, checks the live credit balance before each one as a second
stop, and reports the credit delta afterwards as the only honest meter.

IDENTITY IS NEVER POSITIONAL
----------------------------
Every request carries the identity key it is FOR and the URL it will fetch, and
``ladder.bind_results`` binds a result only to the request whose identity key
AND requested URL it names. An unbound result is reported UNBOUND, never guessed.

Nothing is written to authority, and neither shared ledger is written.

Output:
  launch_packages/pettripfinder/markets/reports/chattanooga_tn_firecrawl_pass_001.json
"""
from __future__ import annotations

import argparse
import dataclasses
import hashlib
import json
import os
import re
import sys
import time
from collections import Counter, OrderedDict
from pathlib import Path

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

from scripts.pettripfinder.acquisition import firecrawl_capture as FC  # noqa: E402
from scripts.pettripfinder.acquisition import ladder as L  # noqa: E402
from scripts.pettripfinder.acquisition import market_observation_store as MOS  # noqa: E402
from scripts.pettripfinder.brightdata import browser_capture as BC  # noqa: E402
from scripts.pettripfinder.discovery import identity_dedup as DEDUP  # noqa: E402

WORK_ORDER = "PTF-CHATTANOOGA-TN-NEW-MARKET-001"
MARKET_ID = "chattanooga-tn"
SCHEMA = "ptf-firecrawl-pass/1.0"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
CENSUS = os.path.join(PKG, "identity_census_proposed", "chattanooga-tn.json")
STATIC_REPORT = os.path.join(REPORTS, "chattanooga_tn_free_static_capture_001.json")
SPACING_SECONDS = 2.0


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def as_plain(obj):
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return dataclasses.asdict(obj)
    return obj if isinstance(obj, dict) else json.loads(json.dumps(obj, default=str))


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else ""


def cohort(static_report):
    rows = [L.RowEvidence(identity_key=r["identity_key"],
                          family=(r.get("brand") or "").upper(),
                          url=r["requested_url"], owned_state="",
                          static_outcome=r["outcome"])
            for r in static_report["rows"]]
    decisions = L.plan_cohort(rows)
    return ([d for d in decisions if d.next_lane == L.FIRECRAWL and not d.settled],
            decisions)


def build(args) -> OrderedDict:
    census = {r["identity_key"]: r for r in read_json(CENSUS)["hotels"]}
    static_report = read_json(STATIC_REPORT)
    static_by_key = {r["identity_key"]: r for r in static_report["rows"]}
    planned, all_decisions = cohort(static_report)
    pressure = L.attended_pressure(all_decisions)
    print("firecrawl cohort", len(planned), "attempt cap", args.cap_attempts, flush=True)

    run_id = args.run_id
    run_dir = Path(_DASH) / "data" / "acquisition" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    credits_before = FC.credits_remaining()
    print("credits before", credits_before, flush=True)

    requests_made, results, rows = [], [], []
    stopped_by = ""

    for d in planned:
        if len(rows) >= args.cap_attempts:
            stopped_by = "ATTEMPT_CAP"
            print("STOP: attempt cap reached at", len(rows), flush=True)
            break
        live = FC.credits_remaining()
        if live is not None and live <= args.floor_credits:
            stopped_by = "CREDIT_FLOOR"
            print("STOP: credit floor reached at", live, flush=True)
            break
        key = d.identity_key
        crow = census.get(key)
        srow = static_by_key.get(key) or {}
        name = (crow or {}).get("canonical_name") or srow.get("canonical_name") or key
        slug = re.sub(r"[^a-z0-9]+", "-", key).strip("-")[:80]
        envelope = FC.request_envelope(d.url, profile=FC.ROUTED_PROFILE)
        requests_made.append(L.Request(identity_key=key, requested_url=d.url, lane=L.FIRECRAWL))
        target = BC.CaptureTarget(
            slug=slug, hotel=name, requested_url=d.url,
            property_code=DEDUP.property_code({"official_url": d.url}),
            market_id=MARKET_ID, normalized_name=key, identity_key=key,
            expected_postal_code=((crow or {}).get("postal_code") or "")[:5],
            expected_street=(crow or {}).get("street", ""),
            expected_phone=(crow or {}).get("phone", ""),
            expected_locality=(crow or {}).get("city", ""),
            identity_brand=d.family, census_matched=crow is not None)

        time.sleep(SPACING_SECONDS)
        attempt, payload = FC.run_attempt(target, 1, run_dir=run_dir,
                                          brand=d.family, profile=FC.ROUTED_PROFILE)
        a = as_plain(attempt)
        attempt_dir = run_dir / slug / "attempt-01"
        identity = a.get("identity") or {}
        confirmed = bool(identity.get("confirmed"))

        row = OrderedDict([
            ("identity_key", key), ("canonical_name", name), ("family", d.family),
            ("cohort", srow.get("cohort", "")),
            ("property_code", target.property_code),
            ("requested_url", d.url), ("final_url", a.get("final_url")),
            ("outcome", a.get("outcome")), ("detail", (a.get("detail") or "")[:300]),
            ("identity_assessment", identity), ("identity_confirmed", confirmed),
            ("expected_postal_code", target.expected_postal_code),
            ("expected_street", target.expected_street),
            ("captured_at", a.get("started_at")),
            ("request_envelope", envelope),
            ("page_sha256", sha256_file(attempt_dir / "rendered.html")),
            ("artifact_dir", str(attempt_dir.relative_to(_DASH)) if attempt_dir.is_dir() else ""),
            ("ladder_reason", d.reason),
            ("firecrawl_measured_by", d.firecrawl.measured_by),
        ])
        results.append({"identity_key": key, "requested_url": d.url,
                        "identity_confirmed": confirmed, "outcome": a.get("outcome")})

        publication_grade, surface_strategy = False, ""
        if a.get("outcome") == "VALID" and (attempt_dir / "policy-block.txt").is_file():
            result = {
                "identity_key": key, "canonical_name": name, "brand": d.family,
                "corridor": (crow or {}).get("corridor", ""), "source_url": d.url,
                "outcome": "VALID", "final_url": a.get("final_url") or d.url,
                "artifact_dir": str(attempt_dir), "identity_confirmed": confirmed,
                "locator_strategy": "",
            }
            try:
                obs, grade, refusal = MOS.observation_for(
                    result, run_id=run_id, market_id=MARKET_ID,
                    census_row=OrderedDict([
                        ("identity_key", key), ("canonical_name", name),
                        ("address", (crow or {}).get("street", "")),
                        ("postal_code", (crow or {}).get("postal_code", "")),
                        ("phone", (crow or {}).get("phone", "")),
                        ("city", (crow or {}).get("city", "")),
                        ("corridor", (crow or {}).get("corridor", "")),
                    ]) if crow else None)
                ext = ((obs or {}).get("observation") or {}).get("extraction") or {}
                publication_grade = bool(grade) and str(
                    (grade or {}).get("verdict") or (grade or {}).get("grade") or ""
                ).endswith("CONFIRMED")
                surface_strategy = str(
                    ((obs or {}).get("reader_provenance") or {}).get("strategy") or "")
                row["observation"] = OrderedDict([
                    ("extraction", ext),
                    ("evidence", ((obs or {}).get("observation") or {}).get("evidence")),
                    ("withheld_fields", (obs or {}).get("withheld_fields")),
                    ("publication_grade", grade), ("refusal_reason", refusal),
                    ("reader_provenance", (obs or {}).get("reader_provenance")),
                ])
                row["pets_allowed"] = ext.get("pets_allowed")
            except Exception as exc:  # noqa: BLE001
                row["observation_error"] = repr(exc)

        row["firecrawl_class"] = L.classify_firecrawl_result(
            outcome=a.get("outcome"), identity_confirmed=confirmed,
            publication_grade=publication_grade, surface_strategy=surface_strategy)
        rows.append(row)
        print("  %-34s %-18s %s" % (key[:34], a.get("outcome"), row["firecrawl_class"]),
              flush=True)

    credits_after = FC.credits_remaining()
    binding = L.bind_results(requests_made, results)

    return OrderedDict((
        ("schema", SCHEMA), ("work_order", WORK_ORDER), ("market_id", MARKET_ID),
        ("phase", "11 -- the Firecrawl rung, after the free static pass"),
        ("run_id", run_id),
        ("lane", "firecrawl (rendered scrape; billed in PLAN CREDITS, no USD)"),
        ("authorization", OrderedDict((
            ("granted_by", "STANDING DOCTRINE for a small cohort in this shape "
                           "(PTF-INDIANAPOLIS-FIRECRAWL-RECOVERY-021, 36 rows / 17 credits; "
                           "PTF-CINCINNATI-HARDENED-REVALIDATION-001, 7-credit cap)"),
            ("cap_attempts", args.cap_attempts),
            ("credit_floor", args.floor_credits),
            ("usd_spent", 0.0), ("brightdata_calls", 0), ("places_calls", 0),
        ))),
        ("why_the_cap_is_on_attempts",
         "Firecrawl costs one credit on a successful fetch and zero when the origin refuses "
         "every engine, so no per-row price exists to budget against and no credit figure is a "
         "ceiling. Attempts are the thing this run controls; the credit delta is what it reports."),
        ("cohort_source", "ladder.plan_cohort over this order's committed static report; "
                          "never a typed list"),
        ("attended_pressure_before", pressure),
        ("planned_rows", len(planned)), ("attempted_rows", len(rows)),
        ("stopped_by", stopped_by),
        ("credits", OrderedDict((
            ("before", credits_before), ("after", credits_after),
            ("delta", (credits_before - credits_after)
             if (credits_before is not None and credits_after is not None) else None),
            ("note", "the credit delta is the meter; the adapter asserts no per-call price and "
                     "none may be inferred"),
        ))),
        ("binding", binding),
        ("class_counts", OrderedDict(sorted(Counter(r["firecrawl_class"] for r in rows).items()))),
        ("outcome_counts", OrderedDict(sorted(Counter(str(r["outcome"]) for r in rows).items()))),
        ("authority_mutation", "NONE"),
        ("shared_ledgers_written", "NONE"),
        ("rows", rows),
    ))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", default="chattanooga_tn_firecrawl_001")
    ap.add_argument("--cap-attempts", type=int, default=28)
    ap.add_argument("--floor-credits", type=int, default=380)
    ap.add_argument("--out", default=os.path.join(REPORTS, "chattanooga_tn_firecrawl_pass_001.json"))
    args = ap.parse_args(argv)
    rep = build(args)
    with open(args.out, "wb") as fh:
        fh.write((json.dumps(rep, indent=1, ensure_ascii=False, default=str) + "\n")
                 .encode("utf-8"))
    print("written", os.path.relpath(args.out, _DASH))
    print("classes:", dict(rep["class_counts"]))
    print("credits:", dict(rep["credits"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
