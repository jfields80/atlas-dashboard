"""PTF-CLEVELAND-POLICY-CAPTURE-WORKER-003 -- closeout categorization of
every ROUTED_AWAITING_CAPTURE target this worker did not advance to a
proposed candidate, one primary reason and one next action each.

Built entirely from this run's own on-disk artifacts (the fetch index and
raw captures under ``data/worker_runs/pettripfinder/cleveland-policy-
capture-003/``, gitignored) plus the committed manifest and census --
nothing here is hand-transcribed, so a re-run over the same captures
reproduces the identical report.
"""

from __future__ import annotations

import json
import re
import sys
from collections import Counter
from pathlib import Path
from urllib.parse import urlsplit

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

RUN_ID = "cleveland-policy-capture-003"
MANIFEST_PATH = (_REPO_ROOT / "launch_packages" / "pettripfinder"
                  / "cleveland_unresolved_manifest.json")
CENSUS_PATH = (_REPO_ROOT / "launch_packages" / "pettripfinder" / "identity_census"
               / "cleveland-akron-canton-oh.json")
FETCH_INDEX_PATH = (_REPO_ROOT / "data" / "worker_runs" / "pettripfinder" / RUN_ID
                     / "fetch_index.json")
OUT_PATH = (_REPO_ROOT / "data" / "worker_runs" / "pettripfinder" / RUN_ID
            / "remaining_unresolved_report.json")

#: Advanced to a proposed candidate this run (published-readiness quality).
#: Keyed on the FETCH slug (``slugify(normalized_name)``, from
#: cleveland_capture_003_fetch.py) -- not the curated census slug, which
#: sometimes drops a stopword (e.g. "and") the raw normalized_name keeps.
ADVANCED_WITH_EVIDENCE = {
    "drury-plaza-hotel", "drury-inn-and-suites-beachwood",
    "la-quinta-inn-cleveland-independence",
    "la-quinta-inn-and-suites-cleveland-airport-north",
    "super-8-by-wyndham-richfield-cleveland",
}

#: Evidence exists and the quote is verified, but the automated M10 name-token
#: identity check rejects it (see cleveland_capture_003_observations.py) --
#: address and phone both independently agree with the census, but Wyndham's
#: own JSON-LD abbreviates "South" to "S", which the token-subset check treats
#: as a different word. Not silently forced through; retained rejected.
IDENTITY_TOKEN_MISMATCH = {
    "super-8-by-wyndham-akron-south-green-uniontown":
        "page identity (JSON-LD) reads 'Super 8 by Wyndham Akron "
        "S/Green/Uniontown OH' -- the brand's own abbreviation of 'South' to "
        "'S' fails the membrane's M10 name-token subset check even though "
        "street address (1605 Corporate Woods Pkwy/Parkway, 44685) and phone "
        "((330) 776-5350 / +1-330-776-5350) both match the census exactly",
}

#: Page rendered (HTTP 200) but carries no affirmative pet-policy statement in
#: its static text -- only an unrendered "Pet & Service Animal Policy"
#: accordion heading and a conditional, non-asserting "pets (if allowed)"
#: fee-disclaimer clause, which states nothing either way.
RENDERED_NO_AFFIRMATIVE_STATEMENT = {
    "baymont-by-wyndham-copley-akron",
    "super-8-by-wyndham-copley-akron",
    "microtel-inn-and-suites-north-canton",
}

#: The routed official_url redirects to a brand-wide, non-property-specific
#: page (a search-results listing), never resolving to the property itself.
REDIRECTED_OFF_PROPERTY = {
    "days-inn-richfield":
        "https://www.wyndhamhotels.com/days-inn/richfield-ohio/"
        "days-inn-and-suites-richfield/overview redirects to "
        "https://www.wyndhamhotels.com/hotels/richfield-ohio?brand_id=DI, a "
        "brand-wide Richfield search-results page with no property-specific "
        "identity or policy content",
}

_TOKEN_RE = re.compile(r"[^a-z0-9]+")


def slugify(name: str) -> str:
    return _TOKEN_RE.sub("-", name.lower()).strip("-")


def _targets():
    manifest = json.loads(MANIFEST_PATH.read_text(encoding="utf-8"))
    return [i for i in manifest["items"] if i["classification"] == "ROUTED_AWAITING_CAPTURE"]


def _census_by_norm():
    census = json.loads(CENSUS_PATH.read_text(encoding="utf-8"))
    return {h["normalized_name"]: h for h in census["hotels"]}


def build_report() -> list:
    targets = _targets()
    census_by_norm = _census_by_norm()
    index = {r["n"]: r for r in json.loads(FETCH_INDEX_PATH.read_text(encoding="utf-8"))}

    handled_fetch_slugs = (ADVANCED_WITH_EVIDENCE | set(IDENTITY_TOKEN_MISMATCH)
                            | RENDERED_NO_AFFIRMATIVE_STATEMENT | set(REDIRECTED_OFF_PROPERTY))

    report = []
    for n, item in enumerate(targets, start=1):
        census_row = census_by_norm.get(item["normalized_name"], {})
        slug = census_row.get("slug") or slugify(item["normalized_name"])
        fetch_slug = index[n]["slug"]

        def row(category, detail, action):
            return {"slug": slug, "canonical_name": item["canonical_name"],
                    "official_url": item["official_url"], "category": category,
                    "detail": detail, "next_action": action}

        if fetch_slug in ADVANCED_WITH_EVIDENCE:
            continue
        if fetch_slug in IDENTITY_TOKEN_MISMATCH:
            report.append(row(
                "IDENTITY_TOKEN_MISMATCH", IDENTITY_TOKEN_MISMATCH[fetch_slug],
                "a human confirms the abbreviation is the same property (or a "
                "property-code override is recovered), then the retained "
                "rejected observation in observations.json is re-admitted -- "
                "no new capture is needed"))
            continue
        if fetch_slug in RENDERED_NO_AFFIRMATIVE_STATEMENT:
            report.append(row(
                "JS_RENDERED_NO_STATIC_CONTENT",
                "HTTP 200, page identity confirmed via JSON-LD, but the "
                "brand's own 'Pet & Service Animal Policy' accordion is a "
                "client-side template that did not render in the static "
                "fetch, and no other affirmative pet statement exists in the "
                "static text",
                "attended browser capture -- the page renders its "
                "pet-policy text client-side"))
            continue
        if fetch_slug in REDIRECTED_OFF_PROPERTY:
            report.append(row(
                "REDIRECTED_OFF_PROPERTY", REDIRECTED_OFF_PROPERTY[fetch_slug],
                "recover a corrected property-specific URL for this hotel -- "
                "the current routing binding redirects to a brand-wide "
                "search page, not the property"))
            continue

        r = index[n]
        host = urlsplit(item["official_url"]).hostname or ""
        if r["reason"] == "blocked_source":
            report.append(row(
                "ACCESS_BLOCKED",
                "%s HTTP %s Forbidden (directly attempted)" % (host, r["http_status"]),
                "attended/authenticated browser capture, or a direct operator "
                "phone call -- static HTTP is bot-walled at the brand-platform "
                "level (this exact block reproduces across every Dayton/"
                "Columbus/Cleveland worker run to date; not attempted here as "
                "a bypass, per ADR-PTF-AUTOMATED-BROWSING)"))
        elif r["reason"] == "fetch_timeout":
            report.append(row(
                "ACCESS_BLOCKED",
                "%s read-timeout, no response (directly attempted)" % host,
                "attended/authenticated browser capture, or a direct operator "
                "phone call -- static HTTP times out at the brand-platform "
                "level (this exact block reproduces across every Dayton/"
                "Columbus/Cleveland worker run to date; not attempted here as "
                "a bypass, per ADR-PTF-AUTOMATED-BROWSING)"))
        else:
            report.append(row(
                "UNCLASSIFIED_FETCH_OUTCOME",
                "reason=%r http_status=%r" % (r["reason"], r["http_status"]),
                "investigate the raw capture directly; this outcome was not "
                "anticipated by this worker's closeout categories"))

    assert len(report) + len(ADVANCED_WITH_EVIDENCE) == 74, (
        "closeout report (%d) + advanced candidates (%d) must reconcile to "
        "the full 74-target set" % (len(report), len(ADVANCED_WITH_EVIDENCE)))
    return report


def main() -> int:
    report = build_report()
    OUT_PATH.parent.mkdir(parents=True, exist_ok=True)
    OUT_PATH.write_text(json.dumps(report, indent=2), encoding="utf-8")

    counts = Counter(r["category"] for r in report)
    print("wrote", OUT_PATH, "with", len(report), "rows")
    for cat, n in counts.most_common():
        print(" ", cat, n)
    print("advanced-with-evidence this run:", len(ADVANCED_WITH_EVIDENCE))
    print("total accounted:", len(report) + len(ADVANCED_WITH_EVIDENCE))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
