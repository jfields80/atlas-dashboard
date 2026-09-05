"""PTF-CINCINNATI-HARDENED-REVALIDATION-001 -- Phase 11, the Firecrawl rung.

The rung the hardened factory added and Dayton never reached. Cincinnati's free
static pass answered nothing and failed 65 rows on the CHANNEL, which is the
only kind of static failure that escalates. The acquisition ladder reads those
outcomes and names the rows Firecrawl is the next lane for: a family the
committed route table sends there on a measured decision (Choice, IHG), a URL
that is a property page, and a property code that parses. Marriott and Hilton
are a measured capability wall and are never candidates; the ladder says so by
name rather than by omission.

This module fetches nothing it was not told to. Its cohort is computed by
``ladder.plan_cohort`` from the committed static report, never typed in, and
every call is bounded three ways:

  * a HARD CREDIT CAP, checked against a LIVE credit read before each call, so
    the run stops WHEN the cap is reached and not after;
  * one attempt per identity, ever, in this run;
  * identity is never positional -- every request carries the identity key it
    is FOR and the URL it will fetch, and ``ladder.bind_results`` binds a
    result only to the request whose identity key AND requested URL it names.

Nothing is written to authority. The output is one report of classified
observations plus the per-call ledger the adapter keeps.
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

WORK_ORDER = "PTF-CINCINNATI-HARDENED-REVALIDATION-001"
MARKET_ID = "cincinnati-oh"
SCHEMA = "ptf-firecrawl-pass/1.0"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
STATIC_REPORT = os.path.join(REPORTS, "cincinnati_oh_free_static_capture_001.json")
INVENTORY = os.path.join(REPORTS, "cincinnati_application_inventory_016.json")
SPACING_SECONDS = 2.0


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def as_plain(obj):
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return dataclasses.asdict(obj)
    return obj if isinstance(obj, dict) else json.loads(json.dumps(obj, default=str))


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else ""


def cohort(static_report, owned_keys):
    """The rows the LADDER names, from the committed static outcomes."""
    rows = [L.RowEvidence(
        identity_key=r["identity_key"], family=(r.get("brand") or "").upper(),
        url=r["requested_url"],
        owned_state=L.OWNED_EVIDENCE_ANSWERS if r["identity_key"] in owned_keys else "",
        static_outcome=r["outcome"]) for r in static_report["rows"]]
    decisions = L.plan_cohort(rows)
    by_key = {r["identity_key"]: r for r in static_report["rows"]}
    return ([d for d in decisions if d.next_lane == L.FIRECRAWL and not d.settled],
            decisions, by_key)


def build(args) -> OrderedDict:
    census = {r["identity_key"]: r for r in
              read_json(os.path.join(PKG, "identity_census", MARKET_ID + ".json"))["hotels"]}
    static_report = read_json(STATIC_REPORT)
    inv = read_json(INVENTORY)
    owned = {r["identity_key"] for rows in inv["items"].values() for r in rows}

    planned, all_decisions, static_by_key = cohort(static_report, owned)
    pressure = L.attended_pressure(all_decisions)
    print("firecrawl cohort", len(planned), "cap", args.cap_credits, flush=True)

    run_id = args.run_id
    run_dir = Path(_DASH) / "data" / "acquisition" / run_id
    run_dir.mkdir(parents=True, exist_ok=True)

    credits_before = FC.credits_remaining()
    print("credits before", credits_before, flush=True)

    requests_made = []   # the Request objects, for non-positional binding
    results = []         # what came back, each naming its identity and URL
    rows = []
    stopped_by_cap = False

    for d in planned:
        spent = (credits_before - (FC.credits_remaining() or credits_before)) if credits_before else 0
        if spent >= args.cap_credits:
            stopped_by_cap = True
            print("STOP: credit cap reached at", spent, flush=True)
            break
        key = d.identity_key
        crow = census.get(key)
        name = crow["canonical_name"] if crow else key
        slug = (crow or {}).get("slug") or re.sub(r"[^a-z0-9]+", "-", key).strip("-")
        envelope = FC.request_envelope(d.url, profile=FC.ROUTED_PROFILE)
        requests_made.append(L.Request(identity_key=key, requested_url=d.url,
                                       lane=L.FIRECRAWL))
        target = BC.CaptureTarget(
            slug=slug, hotel=name, requested_url=d.url,
            property_code=DEDUP.property_code({"official_url": d.url}),
            market_id=MARKET_ID, normalized_name=key, identity_key=key,
            expected_postal_code=((crow or {}).get("postal_code") or "")[:5],
            expected_street=(crow or {}).get("address", ""),
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
            ("identity_key", key),
            ("canonical_name", name),
            ("family", d.family),
            ("property_code", target.property_code),
            ("requested_url", d.url),
            ("final_url", a.get("final_url")),
            ("outcome", a.get("outcome")),
            ("detail", (a.get("detail") or "")[:300]),
            ("identity_assessment", identity),
            ("identity_confirmed", confirmed),
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

        publication_grade = False
        surface_strategy = ""
        if a.get("outcome") == "VALID" and (attempt_dir / "policy-block.txt").is_file():
            result = {
                "identity_key": key, "canonical_name": name, "brand": d.family,
                "corridor": (crow or {}).get("corridor", ""), "source_url": d.url,
                "outcome": "VALID", "final_url": a.get("final_url") or d.url,
                "artifact_dir": str(attempt_dir),
                "identity_confirmed": confirmed, "locator_strategy": "",
            }
            try:
                obs, grade, refusal = MOS.observation_for(
                    result, run_id=run_id, market_id=MARKET_ID, census_row=crow)
                ext = ((obs or {}).get("observation") or {}).get("extraction") or {}
                publication_grade = bool(grade) and str(
                    (grade or {}).get("verdict") or (grade or {}).get("grade") or ""
                ).endswith("CONFIRMED")
                surface_strategy = str(
                    ((obs or {}).get("reader_provenance") or {}).get("strategy")
                    or result.get("locator_strategy") or "")
                row["observation"] = OrderedDict([
                    ("extraction", ext),
                    ("evidence", ((obs or {}).get("observation") or {}).get("evidence")),
                    ("withheld_fields", (obs or {}).get("withheld_fields")),
                    ("publication_grade", grade),
                    ("refusal_reason", refusal),
                    ("reader_provenance", (obs or {}).get("reader_provenance")),
                ])
                row["pets_allowed"] = ext.get("pets_allowed")
            except Exception as exc:  # noqa: BLE001
                row["observation_error"] = repr(exc)

        row["firecrawl_class"] = L.classify_firecrawl_result(
            outcome=a.get("outcome"), identity_confirmed=confirmed,
            publication_grade=publication_grade,
            surface_strategy=surface_strategy)
        rows.append(row)
        print("  %-28s %-16s %s" % (key[:28], a.get("outcome"), row["firecrawl_class"]), flush=True)

    credits_after = FC.credits_remaining()
    binding = L.bind_results(requests_made, results)

    return OrderedDict((
        ("schema", SCHEMA),
        ("work_order", WORK_ORDER),
        ("market_id", MARKET_ID),
        ("phase", "11 -- the Firecrawl rung, after the free static pass"),
        ("run_id", run_id),
        ("lane", "firecrawl (rendered scrape; billed in PLAN CREDITS, no USD)"),
        ("authorization", OrderedDict((
            ("granted_by", "operator, in session, for this diagnostic cohort"),
            ("cap_credits", args.cap_credits),
            ("usd_spent", 0.0),
            ("brightdata_calls", 0), ("places_calls", 0),
        ))),
        ("cohort_source", "ladder.plan_cohort over the committed static report; "
                          "never a typed list"),
        ("attended_pressure_before", pressure),
        ("planned_rows", len(planned)),
        ("attempted_rows", len(rows)),
        ("stopped_by_cap", stopped_by_cap),
        ("credits", OrderedDict((
            ("before", credits_before), ("after", credits_after),
            ("delta", (credits_before - credits_after)
             if (credits_before is not None and credits_after is not None) else None),
            ("note", "the credit delta is the meter; the adapter asserts no "
                     "per-call price and none may be inferred"),
        ))),
        ("binding", binding),
        ("class_counts", OrderedDict(sorted(Counter(r["firecrawl_class"] for r in rows).items()))),
        ("outcome_counts", OrderedDict(sorted(Counter(r["outcome"] for r in rows).items()))),
        ("authority_mutation", "NONE"),
        ("rows", rows),
    ))


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--run-id", default="cincinnati_oh_firecrawl_001")
    ap.add_argument("--cap-credits", type=int, default=7)
    ap.add_argument("--out", default=os.path.join(REPORTS, "cincinnati_oh_firecrawl_pass_001.json"))
    args = ap.parse_args(argv)
    rep = build(args)
    with open(args.out, "wb") as fh:
        fh.write((json.dumps(rep, indent=1, ensure_ascii=False, default=str) + "\n").encode("utf-8"))
    print("written", os.path.relpath(args.out, _DASH))
    print("classes:", dict(rep["class_counts"]))
    print("credits:", dict(rep["credits"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
