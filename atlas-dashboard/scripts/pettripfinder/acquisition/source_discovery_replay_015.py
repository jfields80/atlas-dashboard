"""PTF-INDEPENDENT-POLICY-URL-DISCOVERY-LAYER-015 -- replay, then route sources.

Runs the reusable ``source_discovery`` layer against the same eleven Milwaukee
independents work order 014 measured, from the documents 014 already paid for,
and requires the answers to match exactly. A reusable implementation that
quietly disagrees with the measurement that justified it is not the same
algorithm, whatever its tests say in isolation.

Then, and only if the replay is clean, it writes the source-routing overlay.

WHY AN OVERLAY AND NOT AN EDIT
-------------------------------
``official_url`` is authoritative in the identity census -- 147 Milwaukee
hotels -- and mirrored in the final partition. Both have been frozen by every
work order in this sequence, and editing them would rewrite the record of where
each property was originally found.

So the discovered URL lives in a separate, non-authoritative overlay that
acquisition consults through ``resolve_source_url``. The census stays canonical,
the original URL is preserved beside the discovered one, provenance and the
commit are recorded, and a bad discovery can be withdrawn by deleting one row
rather than by reconstructing history.
"""

from __future__ import annotations

import argparse
import json
import re
import subprocess
import sys
from collections import Counter
from pathlib import Path
from typing import Dict, List

REPO = Path(__file__).resolve().parents[3]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts.pettripfinder.acquisition import firecrawl_capture as FC             # noqa: E402
from scripts.pettripfinder.acquisition import generic_reader_diagnostic_013 as D13  # noqa: E402
from scripts.pettripfinder.acquisition import independent_url_discovery_014 as D14  # noqa: E402
from scripts.pettripfinder.acquisition import source_discovery as SD              # noqa: E402
from scripts.pettripfinder.brightdata import unlocker_capture as UC               # noqa: E402

WORK_ORDER = "PTF-INDEPENDENT-POLICY-URL-DISCOVERY-LAYER-015"
MARKET = "milwaukee-wi"
REPORTS = REPO / "launch_packages" / "pettripfinder" / "markets" / "reports"
DISCOVERY_014 = REPORTS / "ptf_independent_url_discovery_014.json"
CACHE_014 = REPO / "data" / "acquisition" / "independent-url-discovery-014" / "url-discovery-014"
CACHE_013 = REPO / "data" / "acquisition" / "generic-reader-diagnostic-013" / "generic-diagnostic-013"
RUN_ROOT = REPO / "data" / "acquisition" / "source-discovery-replay-015"

EXPECTED_COHORT = 11
#: What 014 measured. The replay must reproduce these exactly.
EXPECTED_014 = {"POLICY_URL_FOUND": 8, "NO_POLICY_URL_FOUND": 3}


def _slug(text: str) -> str:
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def head() -> str:
    return subprocess.run(["git", "rev-parse", "HEAD"], cwd=str(REPO),
                          capture_output=True, text=True, check=True).stdout.strip()


class CachedFetcher:
    """Serves documents 013 and 014 already paid for; requests only what is new.

    Every lookup reports whether it cost a request, so the ledger can keep
    requests and cache hits as separate numbers.
    """

    def __init__(self, run_dir: Path, ledger: SD.UsageLedger,
                 allow_network: bool) -> None:
        self.run_dir = run_dir
        self.ledger = ledger
        self.allow_network = allow_network
        self.misses: List[str] = []

    def _cached(self, url: str) -> Path | None:
        # An explicit URL -> document index, built from 014's own report. An
        # earlier version matched directories by the slug of the URL PATH,
        # which is not unique across properties: "/faq" matched
        # the-iron-horse-hotel--faq as readily as saint-kate-the-arts-hotel--faq
        # and served one hotel's document for another. Three replay
        # "deviations" were that bug, not a disagreement about the algorithm.
        if _INDEX.get(url):
            return _INDEX[url]
        for root in (self.run_dir,):
            if not root.is_dir():
                continue
            for path in root.rglob("rendered.html"):
                meta = path.with_name("source-url.txt")
                if meta.is_file() and meta.read_text(encoding="utf-8").strip() == url:
                    return path
        return None

    def __call__(self, url: str) -> Dict:
        hit = self._cached(url)
        if hit is not None:
            self.ledger.record(requested=False)
            return {"html": hit.read_text(encoding="utf-8", errors="replace"),
                    "final_url": url, "requested": False}
        if not self.allow_network:
            self.misses.append(url)
            self.ledger.record(requested=False)
            return {"html": "", "final_url": "", "requested": False}
        try:
            result = FC.fetch(url, profile=FC.ROUTED_PROFILE)
        except Exception:                                        # noqa: BLE001
            self.ledger.record(requested=True)
            return {"html": "", "final_url": "", "requested": True}
        self.ledger.record(requested=True)
        html = result.get("html") or ""
        if html:
            out = self.run_dir / _slug(url)[:120]
            out.mkdir(parents=True, exist_ok=True)
            (out / "rendered.html").write_bytes(html.encode("utf-8"))
            (out / "source-url.txt").write_text(url, encoding="utf-8")
        return {"html": html, "final_url": result.get("final_url") or url,
                "requested": True}


def _document_index() -> Dict[str, Path]:
    """Exact URL -> cached document, reconstructed from 014's own report.

    014 named each capture directory ``<property-slug>--<path-slug>``. That
    naming is deterministic but NOT unique across properties, so the mapping is
    rebuilt per property from the candidate URLs the report records, never by
    scanning for a matching suffix.
    """
    index: Dict[str, Path] = {}
    if not DISCOVERY_014.is_file():
        return index
    prior = json.loads(DISCOVERY_014.read_text(encoding="utf-8-sig"))
    from urllib.parse import urlparse
    for row in prior["properties"]:
        prop = _slug(row["property_name"])
        # the homepage 014 fetched for itself, when 013 had not already
        home = CACHE_014 / ("%s--home" % prop)
        if (home / "rendered.html").is_file():
            index[row["starting_url"]] = home / "rendered.html"
        for candidate in row.get("candidates_tried", []):
            path_slug = _slug(urlparse(candidate["url"]).path) or "root"
            directory = CACHE_014 / ("%s--%s" % (prop, path_slug))[:120]
            doc = directory / "rendered.html"
            if doc.is_file():
                index[candidate["url"]] = doc
    return index


_INDEX: Dict[str, Path] = {}


def subjects() -> List[Dict]:
    rows = D14.cohort()
    if len(rows) != EXPECTED_COHORT:
        raise SystemExit("ABORT: expected %d independents, derived %d"
                         % (EXPECTED_COHORT, len(rows)))
    return rows


def home_document(entry: Dict) -> str:
    path = CACHE_013 / _slug(entry["canonical_name"]) / "rendered.html"
    if path.is_file():
        return path.read_text(encoding="utf-8", errors="replace")
    for directory in sorted(CACHE_014.glob("*--home")):
        if directory.name.startswith(_slug(entry["canonical_name"])):
            doc = directory / "rendered.html"
            if doc.is_file():
                return doc.read_text(encoding="utf-8", errors="replace")
    return ""


def replay(allow_network: bool) -> Dict:
    global _INDEX
    _INDEX = _document_index()
    rows = subjects()
    run_dir = RUN_ROOT / "replay"
    run_dir.mkdir(parents=True, exist_ok=True)
    ledger = SD.UsageLedger(path=run_dir / "usage.json").load()
    fetcher = CachedFetcher(run_dir, ledger, allow_network)

    results = []
    for entry in rows:
        result = SD.discover(
            identity_key=entry["identity_key"],
            property_name=entry["canonical_name"],
            starting_url=entry["official_url"],
            home_html=home_document(entry),
            fetch=fetcher, to_text=UC.html_to_text,
            classify_presence=lambda text, ok: D13.classify_presence(
                text, identity_ok=ok))
        results.append(result)
    ledger.save()
    return {"results": results, "ledger": ledger, "misses": fetcher.misses}


def compare_to_014(results: List[SD.DiscoveryResult]) -> Dict:
    prior = json.loads(DISCOVERY_014.read_text(encoding="utf-8-sig"))
    by_key = {r["identity_key"]: r for r in prior["properties"]}
    rows, deviations = [], []
    for result in results:
        was = by_key.get(result.identity_key, {})
        same_status = result.status == was.get("outcome")
        same_url = (result.discovered_url or None) == (was.get("discovered_url") or None)
        same_presence = (result.policy_presence or None) == (was.get("policy_presence") or None)
        row = {"identity_key": result.identity_key,
               "status_014": was.get("outcome"), "status_015": result.status,
               "url_014": was.get("discovered_url"),
               "url_015": result.discovered_url,
               "presence_014": was.get("policy_presence"),
               "presence_015": result.policy_presence,
               "equivalent": same_status and same_url and same_presence}
        rows.append(row)
        if not row["equivalent"]:
            deviations.append(row)
    counts = Counter(r.status for r in results)
    return {"rows": rows, "deviations": deviations,
            "status_counts": dict(counts),
            "matches_expected_014": {k: counts.get(k, 0) == v
                                     for k, v in EXPECTED_014.items()},
            "equivalent": not deviations and all(
                counts.get(k, 0) == v for k, v in EXPECTED_014.items())}


def write_overlay(results: List[SD.DiscoveryResult], commit: str) -> Path:
    """The source-routing preference. Never an edit to the census."""
    records = []
    for result in sorted(results, key=lambda r: r.identity_key):
        records.append({
            "identity_key": result.identity_key,
            "property_name": result.property_name,
            "status": result.status,
            "original_source_url": result.starting_url,
            "discovered_url": result.discovered_url,
            "use_for_acquisition": (result.discovered_url
                                    if result.status == SD.POLICY_URL_FOUND
                                    else result.starting_url),
            "policy_presence": result.policy_presence or None,
            "source_quality": result.source_quality or None,
            "identity_reason": result.identity_reason or None,
            "discovery_reason": result.discovery_reason or None,
            "provenance": {
                "measured_by": "PTF-INDEPENDENT-POLICY-URL-DISCOVERY-014",
                "implemented_by": WORK_ORDER,
                "commit": commit,
                "contract": SD.CONTRACT,
            },
        })
    doc = {
        "schema": SD.OVERLAY_CONTRACT,
        "market_id": MARKET,
        "work_order": WORK_ORDER,
        "note": ("A source-routing PREFERENCE, not authority. official_url "
                 "remains canonical in the identity census and is not edited "
                 "here; acquisition reads this overlay through "
                 "source_discovery.resolve_source_url and falls back to the "
                 "census URL whenever a row is absent or unresolved. A "
                 "discovery can be withdrawn by deleting one row."),
        "is_policy_authority": False,
        "publishes_policy": False,
        "counts": dict(Counter(r["status"] for r in records)),
        "records": records,
    }
    path = SD.overlay_path(REPO, MARKET)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes((json.dumps(doc, indent=1, ensure_ascii=False) + "\n")
                     .encode("utf-8"))
    return path


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--allow-network", action="store_true",
                        help="permit Firecrawl requests for documents no "
                             "cached run already holds")
    parser.add_argument("--write-overlay", action="store_true")
    args = parser.parse_args(argv)

    out = replay(allow_network=args.allow_network)
    results, ledger = out["results"], out["ledger"]
    equivalence = compare_to_014(results)

    print("replayed %d subjects | provider requests %d | cache hits %d"
          % (len(results), ledger.provider_requests, ledger.cache_hits))
    if out["misses"]:
        print("  documents not cached (no network permitted): %d" % len(out["misses"]))
    print()
    for row in equivalence["rows"]:
        print("  %-46s %-20s %s" % (row["identity_key"][:46], row["status_015"],
                                    "OK" if row["equivalent"] else "DEVIATION"))
    print()
    print("status counts:", equivalence["status_counts"])
    print("matches 014  :", equivalence["matches_expected_014"])
    print("EQUIVALENT   :", equivalence["equivalent"])

    doc = {
        "schema": "ptf-source-discovery-replay/1.0",
        "work_order": WORK_ORDER, "market_id": MARKET,
        "note": ("Replay of the 014 measurement through the reusable "
                 "source_discovery layer, from documents 014 already paid "
                 "for. Equivalence is required before the overlay is written."),
        "commit": head(),
        "cohort_size": len(results),
        "equivalence": equivalence,
        "usage": {"provider_requests": ledger.provider_requests,
                  "cache_hits": ledger.cache_hits,
                  "documents_not_cached": len(out["misses"]),
                  "note": ("provider_requests counts REQUESTS and never "
                           "decreases; a cache-only rebuild adds nothing and "
                           "erases nothing")},
        "overlay_written": False,
        "routes_changed": False, "reader_changed": False,
        "census_edited": False, "authority_written": False,
        "policies_published": False,
        "results": [r.to_dict() for r in results],
    }

    if args.write_overlay:
        if not equivalence["equivalent"]:
            print("\nREFUSING to write the overlay: replay is not equivalent")
            return 1
        path = write_overlay(results, doc["commit"])
        doc["overlay_written"] = True
        doc["overlay_path"] = str(path.relative_to(REPO))
        print("\noverlay written: %s" % path.relative_to(REPO))

    (REPORTS / "ptf_source_discovery_replay_015.json").write_bytes(
        (json.dumps(doc, indent=1, ensure_ascii=False) + "\n").encode("utf-8"))
    return 0 if equivalence["equivalent"] else 1


if __name__ == "__main__":
    raise SystemExit(main())
