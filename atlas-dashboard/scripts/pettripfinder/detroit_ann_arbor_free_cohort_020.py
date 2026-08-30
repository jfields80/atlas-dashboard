# -*- coding: utf-8 -*-
"""PTF-DETROIT-ANN-ARBOR-FREE-ATTENDED-PASS-020, Phase 1.

Rebuilds the zero-cost attended-Chrome cohort from CURRENT authority, routing
and ledger state. NOTHING IS CAPTURED HERE and no provider is called.

THE 33 IS RE-DERIVED, NOT INHERITED. Order 019 classified the remainder while
it was applying authority; this order checks every condition again against what
the market holds now.

EMBASSY SUITES IS ADMITTED SEPARATELY AND STAYS OUT OF THE INDEPENDENT
DENOMINATOR. It is a Hilton property on a brand domain, admitted only because a
founder ruled HOLD_FOR_RE_CAPTURE on it and left it routed for exactly this.
Counting one brand page inside a measurement of independent domains would
answer a different question from the one this pass is asking.
"""
from __future__ import annotations

import json
import sys
from collections import Counter, OrderedDict
from pathlib import Path
from typing import Dict, List
from urllib.parse import urlsplit

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.acquisition import paid_attempt_ledger as PAL  # noqa: E402

MARKET = "detroit-ann-arbor-mi"
WORK_ORDER = "PTF-DETROIT-ANN-ARBOR-FREE-ATTENDED-PASS-020"
RUN_ID = "detroit-attended-020"
AS_OF = "2026-08-30"

EMBASSY = "embassy suites by hilton detroit livonia novi"

#: Domains this market has already worked through a PAID lane. A row on one of
#: these is out of scope here: it has been measured, and re-working it free
#: would answer a question already answered.
PAID_LANE_HOSTS = {
    "marriott.com", "hilton.com", "ihg.com", "choicehotels.com",
    "wyndhamhotels.com",
}

#: Chain domains that have NEVER been worked in this market. They are still the
#: property's own first-party site, still unresolved and still unpaid, so they
#: are free-eligible -- but they are a different population from a one-off
#: hotel's own domain, and the lane question this pass asks is about the latter.
#: Admitted, and reported as their own stratum rather than blended in.
SMALL_CHAIN_HOSTS = {
    "redroof.com", "woodspring.com", "druryhotels.com",
    "extendedstayamerica.com", "hyatt.com", "bestwestern.com",
    "radissonhotels.com", "sonesta.com", "motel6.com",
}

LP = _REPO_ROOT / "launch_packages" / "pettripfinder"
OUT_PATH = LP / "detroit_ann_arbor_free_cohort_020.json"


def load(path: Path) -> Dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_lf(path: Path, doc) -> None:
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8", newline="\n")


def registrable(url: str) -> str:
    host = (urlsplit(url or "").hostname or "").lower()
    parts = [part for part in host.split(".") if part]
    return ".".join(parts[-2:]) if len(parts) >= 2 else host


def run() -> None:
    census = {row["identity_key"]: row for row in
              load(LP / "identity_census" / ("%s.json" % MARKET))["hotels"]}
    routes = {route["hotel_ref"]["identity_key"]: route for route in
              load(LP / "markets" / "authority" / MARKET
                   / "identity_routing.json")["routes"]
              if route["status"] == "ROUTING_CONFIRMED"}
    published = {row["identity_key"] for row in
                 load(LP / ("hotel_policy_facts_%s.json" % MARKET))["hotels"]}
    excluded = {row["normalized_name"] for row in
                load(LP / "markets" / "authority" / MARKET
                     / "hotel_exclusions.json")["exclusions"]}
    ledger = load(LP / "ptf_paid_attempt_ledger_001.json")
    answered = {attempt["identity_key"] for attempt in ledger["attempts"]
                if attempt.get("market_id") == MARKET
                and attempt.get("publication_grade")}
    attempted = {attempt["identity_key"] for attempt in ledger["attempts"]
                 if attempt.get("market_id") == MARKET}

    unresolved = set(census) - published - excluded
    admitted, suppressed = [], []
    seen_url, seen_identity = {}, {}

    for key in sorted(unresolved):
        if key == EMBASSY:
            continue                       # admitted separately, below
        row = census[key]
        route = routes.get(key)
        url = (route or {}).get("official_property_url") or ""
        host = registrable(url)
        checks = OrderedDict([
            ("detroit_market_member", key in census),
            ("unresolved", True),
            ("currently_routed", route is not None),
            ("first_party_property_domain", bool(host)),
            ("not_already_worked_on_a_paid_lane",
             host not in PAID_LANE_HOSTS),
            ("absolute_canonical_url", url.lower().startswith("https://")),
            ("not_already_answered_by_persisted_evidence",
             key not in answered),
            ("not_previously_attempted_on_a_paid_lane", key not in attempted),
        ])
        entry = OrderedDict([
            ("identity_key", key),
            ("canonical_name", row.get("canonical_name") or ""),
            ("host", host),
            ("canonical_url", url),
            ("city", row.get("city") or ""),
            ("address", row.get("address") or ""),
            ("postal_code", row.get("postal_code") or ""),
            ("phone", row.get("phone") or ""),
            ("slug", row.get("slug") or ""),
            ("stratum", "SMALL_CHAIN_DOMAIN" if host in SMALL_CHAIN_HOSTS
             else "INDEPENDENT_DOMAIN"),
            ("checks", checks),
        ])
        if not all(checks.values()):
            entry["suppressed_because"] = [name for name, ok in checks.items()
                                           if not ok]
            suppressed.append(entry)
            continue
        canonical = PAL.canonical_url({"official_url": url})
        identity = PAL.property_identity({"official_url": url})
        if canonical in seen_url or (identity and identity in seen_identity):
            entry["suppressed_because"] = ["duplicate page or building in the "
                                           "cohort"]
            suppressed.append(entry)
            continue
        seen_url[canonical] = key
        if identity:
            seen_identity[identity] = key
        admitted.append(entry)

    embassy_row = census.get(EMBASSY)
    embassy_route = routes.get(EMBASSY)
    embassy = OrderedDict([
        ("identity_key", EMBASSY),
        ("canonical_name", (embassy_row or {}).get("canonical_name") or ""),
        ("admission", "FOUNDER_AUTHORIZED_ZERO_COST_RECAPTURE"),
        ("authorisation",
         "founder ruling under PTF-DETROIT-ANN-ARBOR-BRIGHTDATA-AUTHORITY-"
         "APPLICATION-019: HOLD_FOR_RE_CAPTURE, kept unresolved and routed so "
         "it could be worked again at zero cost."),
        ("canonical_url", (embassy_route or {}).get("official_property_url")
         or ""),
        ("city", (embassy_row or {}).get("city") or ""),
        ("address", (embassy_row or {}).get("address") or ""),
        ("postal_code", (embassy_row or {}).get("postal_code") or ""),
        ("phone", (embassy_row or {}).get("phone") or ""),
        ("slug", (embassy_row or {}).get("slug") or ""),
        ("prior_evidence",
         "Are pets allowed at Embassy Suites by Hilton Detroit Livonia Novi?"),
        ("why_that_is_not_evidence", "it is a question, not an answer"),
        ("counted_in_the_independent_lane", False),
        ("attempts_permitted", 1),
    ])

    by_host = Counter(row["host"] for row in admitted)
    by_stratum = Counter(row["stratum"] for row in admitted)
    write_lf(OUT_PATH, OrderedDict([
        ("schema", "ptf-detroit-ann-arbor-free-cohort/1.0"),
        ("work_order", WORK_ORDER), ("market_id", MARKET), ("as_of", AS_OF),
        ("run_id", RUN_ID),
        ("lane", "attended_chrome"),
        ("provider_calls", 0), ("spend_usd", 0.0),
        ("lanes_forbidden", ["brightdata_browser", "brightdata_web_unlocker",
                             "firecrawl", "google_places"]),
        ("rebuilt_from_current_state",
         "order 019 reported ~33; every condition is re-checked here against "
         "the authority, routing and ledger as they stand now."),
        ("unresolved_total", len(unresolved)),
        ("independent_cohort", OrderedDict([
            ("starting_candidates", len(admitted) + len(suppressed)),
            ("suppressed", len(suppressed)),
            ("suppression_reasons",
             dict(Counter(reason for row in suppressed
                          for reason in row["suppressed_because"]))),
            ("admitted", len(admitted)),
            ("by_stratum", dict(by_stratum)),
            ("stratum_note",
             "INDEPENDENT_DOMAIN is a one-off hotel's own site -- the "
             "population this pass's lane question is about. "
             "SMALL_CHAIN_DOMAIN is a chain never worked in this market; "
             "free-eligible and worth capturing, but measured separately so "
             "it cannot flatter or depress the independent rate."),
            ("distinct_hosts", len(by_host)),
            ("hosts", OrderedDict(sorted(by_host.items()))),
        ])),
        ("founder_authorized_recapture", embassy),
        ("admitted_rows", admitted),
        ("suppressed_rows", suppressed),
    ]))

    print("=== Phase 1: free cohort rebuilt ===")
    print("  unresolved total          :", len(unresolved))
    print("  starting free candidates  :", len(admitted) + len(suppressed))
    print("  suppressed                :", len(suppressed))
    for reason, n in Counter(reason for row in suppressed
                             for reason in row["suppressed_because"]).items():
        print("     %-50s %d" % (reason, n))
    print("  ADMITTED free candidates  :", len(admitted), dict(by_stratum))
    print("     across %d distinct hosts" % len(by_host))
    print("  founder re-capture        : 1 (Embassy Suites, separate lane)")
    print("wrote", OUT_PATH.name)


if __name__ == "__main__":
    run()
