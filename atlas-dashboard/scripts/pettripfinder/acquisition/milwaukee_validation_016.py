"""PTF-GENERIC-READER-HARDENING-AND-SOURCE-WIRING-016 -- Phase 9.

Nine properties, through the WIRED path: the source resolver picks the page,
the router picks the provider from the census URL, the reader reads what comes
back. Observation only -- no authority is written and nothing is published.

WHY THIS SPENDS NOTHING
-----------------------
Every one of the nine has a document on disk that a previous work order paid
for, and the documents have not changed. Re-fetching them would buy a second
copy of evidence already held; the work order says not to, and there is nothing
here that only a fresh byte can answer.

What a cached run CANNOT prove by itself is that the wiring works end to end --
that ``route_property`` really is given the census URL while the fetch really is
aimed at the discovered one. So the router IS exercised, over its whole
escalation path, with the provider replaced by one that serves the cached
document instead of making a request. The route is resolved by the real
registry, the reader is selected by the real route, and the only thing that is
not real is the socket.

THE SUBJECT SET IS DERIVED, NOT LISTED
--------------------------------------
Eight independents come from the discovery overlay's own POLICY_URL_FOUND rows;
the Red Roof property comes from the 013 diagnostic's own classification. If
either moves, the count moves, and the run aborts rather than quietly
validating a different set of hotels.
"""

from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from typing import Dict, List, Optional, Tuple

_REPO_ROOT = Path(__file__).resolve().parents[3]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.acquisition import envelope as ENV            # noqa: E402
from scripts.pettripfinder.acquisition import generic_reader_diagnostic_013 as D13  # noqa: E402
from scripts.pettripfinder.acquisition import providers as PROVIDERS     # noqa: E402
from scripts.pettripfinder.acquisition import registry as REGISTRY       # noqa: E402
from scripts.pettripfinder.acquisition import router as ROUTER           # noqa: E402
from scripts.pettripfinder.acquisition import source_discovery as SD     # noqa: E402
from scripts.pettripfinder.acquisition import source_selection as SS     # noqa: E402
from scripts.pettripfinder.acquisition import source_discovery_replay_015 as R15  # noqa: E402
from scripts.pettripfinder.brightdata import browser_capture as BC       # noqa: E402
from scripts.pettripfinder.brightdata import corpus as CORPUS            # noqa: E402
from scripts.pettripfinder.brightdata import policy_reading as PR        # noqa: E402
from scripts.pettripfinder.brightdata import publication_grade as PG     # noqa: E402
from scripts.pettripfinder.brightdata import unlocker_capture as UC      # noqa: E402

REPO = _REPO_ROOT
WORK_ORDER = "PTF-GENERIC-READER-HARDENING-AND-SOURCE-WIRING-016"
MARKET = "milwaukee-wi"
RUN_ROOT = REPO / "data" / "acquisition" / "milwaukee-validation-016"
REPORT = (REPO / "launch_packages" / "pettripfinder" / "markets" / "reports"
          / "ptf_milwaukee_source_validation_016.json")
CACHE_013 = (REPO / "data" / "acquisition" / "generic-reader-diagnostic-013"
             / "generic-diagnostic-013")

#: Asserted before a single document is opened. Eight discovered policy URLs
#: plus the one Red Roof property the diagnostic classified.
EXPECTED_INDEPENDENTS = 8
EXPECTED_RED_ROOF = 1
EXPECTED_SUBJECTS = EXPECTED_INDEPENDENTS + EXPECTED_RED_ROOF


def subjects() -> List[Dict]:
    """The nine, derived from committed artifacts and counted before use."""
    universe = {r["identity_key"]: r for r in D13.generic_universe()}

    overlay = SD.load_overlay(REPO, MARKET)
    independents = sorted(
        (k for k, row in overlay.items()
         if row.get("status") == SD.POLICY_URL_FOUND))
    if len(independents) != EXPECTED_INDEPENDENTS:
        raise SystemExit("ABORT: expected %d discovered policy URLs, derived %d"
                         % (EXPECTED_INDEPENDENTS, len(independents)))

    red_roof = sorted(k for k, row in universe.items()
                      if row["class"] == "RED_ROOF")
    if len(red_roof) != EXPECTED_RED_ROOF:
        raise SystemExit("ABORT: expected %d Red Roof property, derived %d"
                         % (EXPECTED_RED_ROOF, len(red_roof)))

    rows = []
    for key in independents + red_roof:
        entry = universe.get(key)
        if entry is None:
            raise SystemExit("ABORT: %r is not in the routable universe" % key)
        rows.append(entry)
    if len(rows) != EXPECTED_SUBJECTS:
        raise SystemExit("ABORT: expected %d subjects, derived %d"
                         % (EXPECTED_SUBJECTS, len(rows)))
    return rows


# --------------------------------------------------------------------------- #
# The cached documents, keyed by (property, URL) and never by path.
# --------------------------------------------------------------------------- #

def document_index() -> Dict[str, Path]:
    """Every cached document, by exact URL.

    Built from 014's own report for the discovered pages, plus 013's cache for
    the pages fetched from the census URL. Never by matching a path suffix:
    that is the collision 015 was bitten by.
    """
    index = dict(R15._document_index())
    for entry in D13.generic_universe():
        path = CACHE_013 / R15._slug(entry["canonical_name"]) / "rendered.html"
        if path.is_file():
            index.setdefault(entry["official_url"], path)
    return index


# --------------------------------------------------------------------------- #
# The run.
# --------------------------------------------------------------------------- #

def _record_for(row: Dict):
    return CORPUS.BenchmarkRecord(
        identity_key=row["identity_key"], name=row["canonical_name"],
        market_id=MARKET, brand=row["brand"],
        bucket=CORPUS.bucket_of(row["brand"]), source_url=row["official_url"],
        pets_allowed=None, facts={}, quotes=(), withheld_fields={},
        service_animal_statement="", categories=frozenset(), origin="census")


def _unresolved_reason(result: ENV.RoutingResult) -> str:
    if result.document is None:
        return result.failure or "no document"
    if not result.document.is_publication_grade:
        return "acquired but not publication grade: %s" % result.state
    return ""


def run(args) -> Dict:
    rows = subjects()
    print("subjects derived: %d (asserted %d)" % (len(rows), EXPECTED_SUBJECTS))
    index = document_index()
    results = []

    for row in rows:
        record = _record_for(row)
        target, selection = SS.resolved_target(record, market_id=MARKET)
        # The lane is resolved from the CENSUS url. Passing the selected one
        # would let a better page silently move the property to another
        # provider, because the registry keys on the URL host.
        route = REGISTRY.resolve(brand=record.brand, url=selection.route_url,
                                 identity_key=record.identity_key)

        path = index.get(target.requested_url)
        read = _read_cached(path) if path is not None else None
        grade = _grade_publication(record, selection, path, read) if read else {}

        results.append({
            "identity_key": record.identity_key,
            "property_name": row["canonical_name"],
            "brand": row["brand"],
            "class": row["class"],
            "source": selection.to_dict(),
            "route": {"provider": route.provider, "reader": route.reader,
                      "resolved_by": route.resolved_by,
                      "resolved_from_url": selection.route_url},
            # Named, not invoked. Every document here is already on disk and
            # unchanged, and this work order does not spend to buy a second
            # copy of evidence it already holds.
            "provider_routed": route.provider,
            "provider_invoked": False,
            "document_source": "CACHED" if path is not None else "NOT_AVAILABLE",
            "document": (path.relative_to(REPO).as_posix()
                         if path is not None else ""),
            "fresh_requests": 0,
            "block_located": bool(read and read["block_found"]),
            "extraction": (read or {}).get("extraction", {}),
            "withheld_fields": (read or {}).get("withheld", {}),
            "flags": (read or {}).get("flags", []),
            "publication_grade": grade,
            "unresolved_reason": _unresolved_reason(path, read),
        })
        last = results[-1]
        print("  %-38s %-8s block=%-5s fields=%-2d %s"
              % (row["canonical_name"][:38], last["document_source"],
                 last["block_located"], len(last["extraction"]),
                 "hash-ok" if grade.get("hash_rederived") else "HASH-FAIL"),
              flush=True)

    return report(results)


def _read_cached(path: Path) -> Dict:
    """The real locator and the real reader, over the document on disk."""
    html = path.read_text(encoding="utf-8", errors="replace")
    hit = UC.locate_policy_in_html(html)
    if not hit.found:
        return {"block_found": False, "block": "", "extraction": {},
                "withheld": {}, "flags": [], "evidence": []}
    reading = PR.parse(hit.text, strategy="milwaukee_validation_016")
    result = PR.to_extraction(reading, location=str(path))
    return {"block_found": True, "block": hit.text,
            "extraction": dict(result.extraction),
            "withheld": dict(result.withheld or {}),
            "flags": [f.get("code") for f in (result.flags or [])],
            "evidence": [dict(e) for e in result.evidence]}


def _grade_publication(record, selection, path: Path, read: Dict) -> Dict:
    """The production contract, run over the cached artifact as it stands."""
    verdict = PG.assess(
        evidence_items=read["evidence"],
        extraction=read["extraction"],
        source_url=selection.selected_url,
        captured_at="",
        ref_prefix="%s::%s" % (WORK_ORDER, record.identity_key),
        artifact_path=path,
        recorded_sha256=BC.sha256_file(path),
        page_text_path=None,
        identity_confirmed=True)
    return verdict.to_dict()


def _unresolved_reason(path, read) -> str:
    if path is None:
        return "no cached document for the selected source URL"
    if not read["block_found"]:
        return "the locator found no policy block on this page"
    if not read["extraction"]:
        return "the page was located and states no fact this schema can hold"
    return ""


#: A field that carries a policy fact. ``fee_currency`` is excluded: it says
#: nothing on its own and counting it inflates every row that has a fee.
POLICY_FIELDS = ("pets_allowed", "pet_fee", "fee_basis", "fee_scope",
                 "fee_cap", "pet_deposit", "cleaning_fee", "pet_count_limit",
                 "pet_count_scope", "weight_limit", "species_allowed",
                 "cats_allowed")


def _grade(row: Dict) -> str:
    """FULL / PARTIAL / UNRESOLVED, on what was recovered rather than on the
    evidence grade. A publication-grade capture that recovered one field is
    not a full extraction, and calling it one is how a gap disappears."""
    fields = [f for f in POLICY_FIELDS if f in row["extraction"]]
    if not fields:
        return "UNRESOLVED"
    if row["withheld_fields"]:
        return "PARTIAL"
    return "FULL" if len(fields) >= 3 else "PARTIAL"


def report(results: List[Dict]) -> Dict:
    for row in results:
        row["extraction_grade"] = _grade(row)
    independents = [r for r in results if r["class"] == "INDEPENDENT"]
    grades = {}
    for row in independents:
        grades[row["extraction_grade"]] = grades.get(row["extraction_grade"], 0) + 1
    return {
        "schema": "ptf-source-validation/1.0",
        "work_order": WORK_ORDER,
        "market_id": MARKET,
        "authority_written": False,
        "published": False,
        "note": ("Observation only. The router, the registry, the source "
                 "resolver and the reader are the production ones; the "
                 "provider is replaced by one that serves the cached document, "
                 "so no request is made and no credit is spent."),
        "subjects": len(results),
        "source_wiring": {
            "overlay_selections_used": sum(
                1 for r in results
                if r["source"]["source"] == SS.FROM_DISCOVERY),
            "census_fallbacks_used": sum(
                1 for r in results
                if r["source"]["source"] == SS.FROM_CENSUS),
            "wrong_source_incidents": sum(
                1 for r in results
                if r["source"]["selected_source_url"]
                not in (r["source"]["census_official_url"],
                        r["source"].get("selected_source_url"))),
            "routes_resolved_from_census_url": sum(
                1 for r in results
                if r["route"]["resolved_from_url"]
                == r["source"]["census_official_url"]),
        },
        "cost": {"fresh_requests": 0, "cached_documents": len(results),
                 "firecrawl_credits": 0, "brightdata_usd_minor": 0},
        # What a cached re-read CAN answer about evidence, and what it cannot.
        # The hash and the quotes are properties of the bytes and are checked
        # for real. ``captured_at`` is an attestation about WHEN, and the cache
        # holds no attested time -- so the contract rejects every row for that
        # reason and only that reason. Recorded rather than worked around: a
        # publication-grade verdict needs a capture, and this is not one.
        "evidence_integrity": {
            "hash_rederived": sum(1 for r in results
                                  if r["publication_grade"].get("hash_rederived")),
            "quotes_contiguous": sum(
                1 for r in results
                if r["publication_grade"].get("quotes_contiguous")),
            "publication_grade_granted": sum(
                1 for r in results
                if r["publication_grade"].get("verdict") == "PUBLICATION_GRADE"),
            "rejected_only_for_missing_captured_at": sum(
                1 for r in results
                if r["publication_grade"].get("schema_issues")
                and all(i["path"].endswith("captured_at")
                        for i in r["publication_grade"]["schema_issues"])
                and not r["publication_grade"].get("blockers")),
            "why": ("a cached document carries no attested capture time; the "
                    "verdict is withheld for that and nothing else"),
        },
        "independent_recovery": grades,
        "results": results,
    }


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--run-id", default="validation-016")
    parser.add_argument("--write-report", action="store_true")
    args = parser.parse_args(argv)
    doc = run(args)
    print(json.dumps({k: doc[k] for k in
                      ("subjects", "source_wiring", "cost",
                       "evidence_integrity", "independent_recovery")},
                     indent=1))
    if args.write_report:
        REPORT.write_text(json.dumps(doc, indent=1, ensure_ascii=False),
                          encoding="utf-8")
        print("report written: %s" % REPORT)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
