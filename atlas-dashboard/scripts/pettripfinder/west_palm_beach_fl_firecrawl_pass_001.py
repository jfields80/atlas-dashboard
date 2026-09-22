"""PTF-WEST-PALM-BEACH-FL-HARDENED-SOURCE-READY-001 -- Phase 13, the Firecrawl rung (cloned from the Orlando FL V2 harness).

THREE COHORTS, ALL COMPUTED, NONE TYPED
-----------------------------------------
  ROUTED        ``ladder.plan_cohort`` over this order's committed static report: every row whose static attempt
                failed on the CHANNEL and whose family the committed route table sends to Firecrawl.
  DISCOVERED    Choice property routes read from the brand's own city pages through Firecrawl
                (west_palm_beach_fl_firecrawl_discovery_001, when it exists), in-market towns only, that no static read
                answered. A property CODE selects; the page's own address admits -- these are identity-fill reads.
  PROBE         families the route table has NOT measured (independents, Red Roof, Motel 6, Radisson, Best
                Western): the ladder marks them FIRECRAWL_UNMEASURED_FOR_FAMILY / probe-eligible. At most
                PROBE_PER_FAMILY rows each, chosen deterministically (sorted identity key).
  WALL_REPROBE  Marriott and Hilton are a measured capability wall. ONE row each is re-probed as a diagnostic of
                whether the wall still stands; the result is recorded and is never used as policy evidence,
                because the router does not route those families here.

THE CAP IS ON ATTEMPTS; the credit floor is a second stop; the credit delta is the meter (one credit on success,
zero when every engine is refused). Existing plan credits only -- no new purchase, no USD.

Identity is never positional: ``ladder.bind_results`` binds each result to the request naming its identity key
AND URL. Nothing is written to authority, and neither shared ledger is written.

Output:
  launch_packages/pettripfinder/markets/reports/west_palm_beach_fl_firecrawl_pass_001.json
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

WORK_ORDER = "PTF-WEST-PALM-BEACH-FL-HARDENED-SOURCE-READY-001"
MARKET_ID = "west-palm-beach-fl"
SCHEMA = "ptf-firecrawl-pass/1.0"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
CENSUS = os.path.join(PKG, "identity_census_proposed", "west-palm-beach-fl.json")
STATIC_REPORT = os.path.join(REPORTS, "west_palm_beach_fl_free_static_capture_001.json")
DISCOVERY = os.path.join(REPORTS, "west_palm_beach_fl_firecrawl_discovery_001.json")
PROBE_PER_FAMILY = 4
#: PALM BEACH COUNTY: independents are the market's largest unresolved family, so EVERY escalatable independent static failure
#: the ladder marks probe-eligible is attempted (bounded by --cap-attempts and the live credit floor).
PROBE_PER_FAMILY_OVERRIDE = {"INDEPENDENT": 10 ** 6}
PROBE_FAMILIES = ("INDEPENDENT", "RED_ROOF", "MOTEL6", "RADISSON", "BEST_WESTERN")
WALL_REPROBE = ("MARRIOTT", "HILTON")
_IN_MARKET_CHOICE_TOWNS = ("west-palm-beach", "palm-beach", "palm-beach-gardens", "north-palm-beach", "royal-palm-beach",
                           "palm-beach-shores", "riviera-beach", "singer-island", "lake-park", "mangonia-park",
                           "juno-beach", "jupiter", "tequesta", "lake-worth", "lake-worth-beach",
                           "palm-springs", "greenacres", "atlantis", "lake-clarke-shores", "haverhill",
                           "lantana", "manalapan", "hypoluxo", "boynton-beach", "ocean-ridge", "gulf-stream",
                           "delray-beach", "highland-beach", "boca-raton", "wellington", "loxahatchee",
                           "westlake", "belle-glade", "pahokee", "south-bay")
SPACING_SECONDS = 2.0


def read_json(path):
    return json.loads(Path(path).read_text(encoding="utf-8-sig"))


def as_plain(obj):
    if dataclasses.is_dataclass(obj) and not isinstance(obj, type):
        return dataclasses.asdict(obj)
    return obj if isinstance(obj, dict) else json.loads(json.dumps(obj, default=str))


def sha256_file(p: Path) -> str:
    return hashlib.sha256(p.read_bytes()).hexdigest() if p.is_file() else ""


class _D(object):
    """A planned Firecrawl request that did not come from ladder.plan_cohort (discovery fill / probe / wall re-probe)."""

    def __init__(self, key, family, url, reason, cohort, measured_by=""):
        self.identity_key, self.family, self.url, self.reason, self.cohort = key, family, url, reason, cohort
        self.firecrawl = L.Candidacy(True, reason, measured_by=measured_by)
        self.settled = False
        self.next_lane = L.FIRECRAWL


def cohort(static_report):
    rows = [L.RowEvidence(identity_key=r["identity_key"], family=(r.get("brand") or "").upper(),
                          url=r["requested_url"], owned_state="", static_outcome=r["outcome"])
            for r in static_report["rows"]]
    decisions = L.plan_cohort(rows)
    planned = [_D(d.identity_key, d.family, d.url, d.reason, "ROUTED", d.firecrawl.measured_by)
               for d in decisions if d.next_lane == L.FIRECRAWL and not d.settled]
    used = {d.url.rstrip("/").lower() for d in planned}
    static_by_key = {r["identity_key"]: r for r in static_report["rows"]}
    static_valid = {r["requested_url"].rstrip("/").lower() for r in static_report["rows"] if r.get("outcome") == "VALID"}
    extra = []
    disc = read_json(DISCOVERY) if os.path.exists(DISCOVERY) else {"routes": []}
    for r in sorted(disc.get("routes", []), key=lambda x: x["route"]):
        town = r["route"].split("/florida/", 1)[-1].split("/", 1)[0] if "/florida/" in r["route"] else ""
        u = r["route"].rstrip("/").lower()
        if r["family"] != "CHOICE" or town not in _IN_MARKET_CHOICE_TOWNS or u in used or u in static_valid:
            continue
        used.add(u)
        extra.append(_D("choice-route::" + r["property_code"], "CHOICE", r["route"],
                        "CHOICE_DISCOVERED_ROUTE_IDENTITY_FILL", "DISCOVERED",
                        "PTF-FIRECRAWL-CHOICE-VALIDATION-004, PTF-CHOICE-READER-AND-ROUTE-CLOSURE-005"))
    per = {}
    for d in sorted(decisions, key=lambda x: x.identity_key):
        fam = d.family or "INDEPENDENT"
        u = (d.url or "").rstrip("/").lower()
        if not u or u in used:
            continue
        if fam in PROBE_FAMILIES and d.firecrawl.reason == L.NOT_CANDIDATE_UNMEASURED:
            if per.get(fam, 0) >= PROBE_PER_FAMILY_OVERRIDE.get(fam, PROBE_PER_FAMILY):
                continue
            per[fam] = per.get(fam, 0) + 1
            used.add(u)
            extra.append(_D(d.identity_key, fam, d.url, "FIRECRAWL_PROBE_UNMEASURED_FAMILY", "PROBE"))
        elif (fam in WALL_REPROBE and d.firecrawl.reason == L.NOT_CANDIDATE_KNOWN_WALL
              and (static_by_key.get(d.identity_key) or {}).get("outcome") == "ACCESS_DENIED"):
            if per.get(fam, 0) >= 1:
                continue
            per[fam] = 1
            used.add(u)
            extra.append(_D(d.identity_key, fam, d.url, "FIRECRAWL_WALL_REPROBE_DIAGNOSTIC_ONLY", "WALL_REPROBE",
                            L.KNOWN_CAPABILITY_WALLS.get(fam, "")))
    return planned + extra, decisions


def build(args) -> OrderedDict:
    census = {r["identity_key"]: r for r in read_json(CENSUS)["hotels"]}
    static_report = read_json(STATIC_REPORT)
    static_by_key = {r["identity_key"]: r for r in static_report["rows"]}
    planned, all_decisions = cohort(static_report)
    if args.targets_file:
        # A TARGETS COHORT: rows the router leaves Firecrawl-eligible that this pass's own static-report cohort
        # cannot see, because their route was not in the static report (a website the Places route-discovery lane
        # found after the static pass, or a brand route discovered later). Each row still states its family, so the
        # ladder's own exclusions (Hyatt / Best Western) and walls (Marriott / Hilton) are honoured by the caller.
        planned = [_D(t["identity_key"], (t.get("family") or "INDEPENDENT").upper(), t["url"],
                      t.get("why") or "FIRECRAWL_PROBE_ROUTER_ELIGIBLE_NOT_IN_STATIC_COHORT", t.get("cohort", "PROBE"))
                   for t in sorted(read_json(args.targets_file), key=lambda x: x["identity_key"])
                   if t.get("url")]
    elif args.retry_from:
        # RETRY COHORT: rows a prior pass classed in --retry-class whose failure was THIS order's own census
        # defect (the licence's abbreviated grid street refused the page's own ordinal spelling), re-attempted once
        # against the restated census. Not a new family, not a new lane; the same router rung on the same URL.
        prior = read_json(args.retry_from)
        want = set(args.retry_class or ())
        planned = [_D(r["identity_key"], r.get("family") or "INDEPENDENT", r["requested_url"],
                      "FIRECRAWL_RETRY_AFTER_CENSUS_STREET_RESTATEMENT", "RETRY")
                   for r in sorted(prior.get("rows", []), key=lambda x: x["identity_key"])
                   if r.get("firecrawl_class") in want and r["identity_key"] in census]
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
            ("cohort", getattr(d, "cohort", "ROUTED")),
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
        ("phase", "13 -- the Firecrawl rung, after the free static pass"),
        ("run_id", run_id),
        ("lane", "firecrawl (rendered scrape; billed in PLAN CREDITS, no USD)"),
        ("authorization", OrderedDict((
            ("granted_by", "EXISTING AUTHORIZED PROVIDER CAPACITY (FIRECRAWL_API_KEY present as an environment "
                           "variable, existing plan credits, presence-only confirmed); no new purchase, no new "
                           "provider authorization"),
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
    ap.add_argument("--run-id", default="west_palm_beach_fl_firecrawl_001")
    ap.add_argument("--cap-attempts", type=int, default=150)
    ap.add_argument("--floor-credits", type=int, default=400)
    ap.add_argument("--out", default=os.path.join(REPORTS, "west_palm_beach_fl_firecrawl_pass_001.json"))
    ap.add_argument("--targets-file", default="", help="a JSON list of {identity_key, family, url, why, cohort}")
    ap.add_argument("--retry-from", default="", help="a prior pass report whose rows are retried")
    ap.add_argument("--retry-class", action="append", help="firecrawl_class of the prior rows to retry (repeatable)")
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
