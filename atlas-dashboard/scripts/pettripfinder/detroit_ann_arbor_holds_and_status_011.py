# -*- coding: utf-8 -*-
"""PTF-DETROIT-ANN-ARBOR-FOUNDER-REVIEW-AND-AUTHORITY-011, Phases 5 and 6.

The two-hold founder packet, Detroit's status after the authority write, and
the exact 12-row Bright Data pilot cohort.

THE HOLDS ARE NOT DECIDED HERE. Both are the same defect wearing two faces: the
committed reader located a real policy block and declined to resolve
``pets_allowed`` from it. Each is presented with its exact quote, why the reader
withheld, the interpretations open to a founder, and what each would do to
authority -- because a hold is only useful if the person ruling on it can see
the consequence of each option.

THE PILOT IS PREPARED, NOT RUN. It is stratified 6 Marriott / 6 Hilton across
different sub-brands and cities, because the two brand walls may behave
differently from each other and a cohort drawn alphabetically would measure one
sub-brand's CDN rather than a market. Firecrawl's rates are NOT carried into it:
those rows are a different family population reached through a different
provider, and the pilot exists precisely because their rate is unknown.
"""
from __future__ import annotations

import json
import re
import sys
from collections import Counter, OrderedDict
from pathlib import Path
from typing import Dict, List
from urllib.parse import urlsplit

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

MARKET = "detroit-ann-arbor-mi"
WORK_ORDER = "PTF-DETROIT-ANN-ARBOR-FOUNDER-REVIEW-AND-AUTHORITY-011"
AS_OF = "2026-08-29"

LP = _REPO_ROOT / "launch_packages" / "pettripfinder"
CANDIDATES = LP / "detroit_ann_arbor_reconciled_candidates_011.json"
HOLDS_PATH = LP / "detroit_ann_arbor_hold_exceptions_011.json"
STATUS_PATH = LP / "detroit_ann_arbor_status_011.json"
PILOT_PATH = LP / "detroit_ann_arbor_brightdata_pilot_cohort_011.json"

BRAND_WALL_HOSTS = {"marriott.com": "MARRIOTT", "hilton.com": "HILTON"}
PILOT_PER_BRAND = 6

#: Bright Data's managed browser, priced from the committed cross-run ledger
#: rather than from Firecrawl. Stated as a ceiling, not a forecast.
BRIGHTDATA_USD_PER_ATTEMPT = 0.19


def load(path: Path) -> Dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_lf(path: Path, doc) -> None:
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8", newline="\n")


def registrable(url: str) -> str:
    host = (urlsplit(url or "").hostname or "").lower()
    parts = [part for part in host.split(".") if part]
    return ".".join(parts[-2:]) if len(parts) >= 2 else host


#: The sub-brand vocabulary these two walls actually use in Detroit. A closed
#: list rather than "whatever token follows the code": Marriott and Hilton both
#: put an unqualified property name there for their collection hotels ("the
#: henry", "the kingsley"), and a stratifier that treated each of those as its
#: own family would spread the pilot across names instead of products.
_SUB_BRANDS = (
    "courtyard", "sheraton", "renaissance", "autograph", "residence-inn",
    "fairfield", "springhill", "towneplace", "ac-hotel", "westin", "aloft",
    "moxy", "delta", "four-points", "element",
    "doubletree", "hampton", "hilton-garden-inn", "embassy-suites",
    "homewood", "home2", "tru", "curio", "tapestry", "canopy", "waldorf",
    "conrad", "motto", "signia",
)


def sub_brand(url: str, brand: str) -> str:
    """The product family this property belongs to, for stratifying the pilot.

    Both brands put the family in the property slug, after the property code:
    ``/hotels/arbaadt-doubletree-ann-arbor-north``. Matched against a closed
    vocabulary so a collection hotel whose slug is just its own name falls to
    ``<brand>-collection`` rather than inventing a family per property.
    """
    path = urlsplit(url or "").path.lower()
    for family in _SUB_BRANDS:
        if re.search(r"[-/]%s(?:[-/]|$)" % re.escape(family), path):
            return family
    return "%s-collection" % brand.lower()




def build_holds() -> List[Dict]:
    holds = load(CANDIDATES)["holds"]
    # Derived, never hardcoded: an effect stated against a stale total is
    # worse than no number at all, because it reads as precise.
    current_no_pets = len(load(LP / "markets" / "authority" / MARKET
                               / "hotel_exclusions.json")["exclusions"])
    becomes = "verified no-pets %d -> %d; pet-friendly unchanged" % (
        current_no_pets, current_no_pets + 1)
    packet: List[Dict] = []
    for hold in holds:
        reading = hold.get("reading") or {}
        quote = (reading.get("block_text") or "").strip()
        service_only = bool(re.search(r"service\s+animals?", quote, re.I))
        typo = bool(re.search(r"\bsorry,?\s+not\s+other\s+pets?", quote, re.I))
        if typo:
            why = ("the reader's negative pattern requires 'no other pets'; "
                   "this property's page reads 'Sorry NOT other pets are "
                   "allowed' -- a typo on the hotel's own page. The reader "
                   "declined to resolve the boolean rather than guess at an "
                   "intended word, which is the correct behaviour.")
            options = [
                OrderedDict([
                    ("option", "READ AS VERIFIED_NO_PETS"),
                    ("reading", "'not' is a typo for 'no'; the sentence is a "
                                "refusal, and the surrounding text ('ADA "
                                "defined service animals are welcome at this "
                                "hotel') matches the refusal template this "
                                "brand uses verbatim on other properties"),
                    ("effect_on_authority", becomes),
                ]),
                OrderedDict([
                    ("option", "HOLD FOR RE-CAPTURE"),
                    ("reading", "wait for the property to correct its page, or "
                                "capture a second surface that states the "
                                "policy unambiguously"),
                    ("effect_on_authority", "none; the row stays unresolved"),
                ]),
                OrderedDict([
                    ("option", "WIDEN THE READER"),
                    ("reading", "teach the negative pattern to accept 'not "
                                "other pets'. NOT recommended inside a review "
                                "this row feeds, and it would change how every "
                                "market reads this phrasing"),
                    ("effect_on_authority", "same as option 1 here, but "
                                            "applied globally and without a "
                                            "founder seeing the other rows it "
                                            "would newly decide"),
                ]),
            ]
        else:
            why = ("the block states only what service animals may do. The "
                   "reader does not convert a service-animal sentence into a "
                   "pet policy in either direction, so it left the boolean "
                   "unresolved. Service-animal access is a legal category, "
                   "not a pet policy.")
            options = [
                OrderedDict([
                    ("option", "READ AS VERIFIED_NO_PETS"),
                    ("reading", "'Only service animals are permitted' excludes "
                                "ordinary pets by the word 'only'; this is an "
                                "affirmative refusal, not silence"),
                    ("effect_on_authority", becomes),
                ]),
                OrderedDict([
                    ("option", "TREAT AS POLICY_NOT_FOUND"),
                    ("reading", "the surface addresses service animals and "
                                "never addresses ordinary pets, so it states "
                                "no pet policy at all. SOURCE SILENCE IS "
                                "ABSENCE"),
                    ("effect_on_authority", "none; the row stays unresolved "
                                            "and is not a negative claim"),
                ]),
            ]
        packet.append(OrderedDict([
            ("identity_key", hold["identity_key"]),
            ("property", hold["canonical_name"]),
            ("brand", hold["brand"]),
            ("source_url", hold["canonical_url"]),
            ("exact_policy_quote", quote),
            ("reader_returned", OrderedDict([
                ("pets_allowed", reading.get("pets_allowed")),
                ("block_located", True),
                ("brand_generic", bool(reading.get("brand_generic"))),
            ])),
            ("why_the_reader_withheld", why),
            ("mentions_service_animals", service_only),
            ("interpretation_options", options),
            ("decided", False),
        ]))
    return packet


def build_pilot(status: Dict) -> Dict:
    routes = [route for route in
              load(LP / "markets" / "authority" / MARKET
                   / "identity_routing.json")["routes"]
              if route["status"] == "ROUTING_CONFIRMED"]
    census = {row["identity_key"]: row for row in
              load(LP / "identity_census" / ("%s.json" % MARKET))["hotels"]}
    facts = {row["identity_key"] for row in
             load(LP / ("hotel_policy_facts_%s.json" % MARKET))["hotels"]}
    excluded = {row["normalized_name"] for row in
                load(LP / "markets" / "authority" / MARKET
                     / "hotel_exclusions.json")["exclusions"]}

    pools: Dict[str, List[Dict]] = {"MARRIOTT": [], "HILTON": []}
    for route in routes:
        key = route["hotel_ref"]["identity_key"]
        if key in facts or key in excluded:
            continue
        url = route.get("official_property_url") or ""
        brand = BRAND_WALL_HOSTS.get(registrable(url))
        if brand is None:
            continue
        row = census.get(key) or {}
        pools[brand].append(OrderedDict([
            ("identity_key", key),
            ("canonical_name", row.get("canonical_name") or ""),
            ("brand", brand),
            ("sub_brand", sub_brand(url, brand)),
            ("city", row.get("city") or ""),
            ("official_property_url", url),
            ("property_code", route.get("property_code") or ""),
        ]))

    # Stratify: walk sub-brands round-robin, then cities, so the twelve rows
    # are not twelve of the same product in the same suburb.
    def stratify(rows: List[Dict], want: int) -> List[Dict]:
        buckets: "OrderedDict[str, List[Dict]]" = OrderedDict()
        for row in sorted(rows, key=lambda r: (r["sub_brand"], r["city"],
                                               r["canonical_name"])):
            buckets.setdefault(row["sub_brand"], []).append(row)
        picked, seen_cities = [], set()
        while len(picked) < want and any(buckets.values()):
            for name in list(buckets):
                if len(picked) >= want:
                    break
                queue = buckets[name]
                choice = next((r for r in queue
                               if r["city"] not in seen_cities), None) or (
                    queue[0] if queue else None)
                if choice is None:
                    buckets.pop(name, None)
                    continue
                queue.remove(choice)
                if not queue:
                    buckets.pop(name, None)
                picked.append(choice)
                seen_cities.add(choice["city"])
        return picked

    marriott = stratify(pools["MARRIOTT"], PILOT_PER_BRAND)
    hilton = stratify(pools["HILTON"], PILOT_PER_BRAND)
    cohort = marriott + hilton

    doc = OrderedDict([
        ("schema", "ptf-detroit-ann-arbor-brightdata-pilot/1.0"),
        ("work_order", WORK_ORDER), ("market_id", MARKET), ("as_of", AS_OF),
        ("status", "PREPARED, NOT RUN, NOT AUTHORISED"),
        ("lane", "brightdata_browser"),
        ("rows", len(cohort)),
        ("composition", OrderedDict([
            ("marriott", len(marriott)), ("hilton", len(hilton)),
            ("marriott_sub_brands", sorted({r["sub_brand"] for r in marriott})),
            ("hilton_sub_brands", sorted({r["sub_brand"] for r in hilton})),
            ("cities", sorted({r["city"] for r in cohort if r["city"]})),
        ])),
        ("available_pool", OrderedDict([
            ("marriott", len(pools["MARRIOTT"])),
            ("hilton", len(pools["HILTON"])),
        ])),
        ("stratification",
         "walked round-robin across sub-brands, preferring an unused city at "
         "each step. Twelve rows drawn alphabetically would measure one "
         "sub-brand's CDN in one suburb, not a market."),
        ("what_the_pilot_measures", [
            "ACCESS SUCCESS -- whether the managed browser reaches these two "
            "brands at all. This is the open question and it comes first",
            "PUBLICATION-GRADE SUCCESS -- of the pages reached, how many yield "
            "a located, property-specific policy block",
            "ACTUAL PAID COST -- the measured spend per attempt on this lane, "
            "which this project has never measured for Detroit",
            "PET-FRIENDLY YIELD -- last, because it is meaningless until the "
            "first three are known",
        ]),
        ("projected_maximum_spend_usd",
         round(len(cohort) * BRIGHTDATA_USD_PER_ATTEMPT, 2)),
        ("spend_basis",
         "%d attempts at $%.2f, the managed browser's committed per-attempt "
         "figure. A CEILING, not a forecast: every attempt bills whether or "
         "not it returns a page."
         % (len(cohort), BRIGHTDATA_USD_PER_ATTEMPT)),
        ("do_not_extrapolate",
         "Firecrawl's Detroit rates say nothing about these rows. Different "
         "family population, different provider, different defences -- and "
         "these %d brand-wall rows have never been attempted at all. Size the "
         "remaining cohort from the PILOT's own Wilson lower bound, never from "
         "its point estimate and never from Firecrawl."
         % status["unresolved"]["brightdata_class"]),
        ("cohort", cohort),
    ])
    write_lf(PILOT_PATH, doc)
    return doc


def run() -> None:
    facts = load(LP / ("hotel_policy_facts_%s.json" % MARKET))["hotels"]
    exclusions = load(LP / "markets" / "authority" / MARKET
                      / "hotel_exclusions.json")["exclusions"]
    census = load(LP / "identity_census" / ("%s.json" % MARKET))["hotels"]
    routes = load(LP / "markets" / "authority" / MARKET
                  / "identity_routing.json")["routes"]
    confirmed = [route for route in routes
                 if route["status"] == "ROUTING_CONFIRMED"]
    census_keys = {row["identity_key"] for row in census}
    routed_keys = {route["hotel_ref"]["identity_key"] for route in routes}

    holds = build_holds()
    write_lf(HOLDS_PATH, OrderedDict([
        ("schema", "ptf-detroit-ann-arbor-hold-exceptions/1.0"),
        ("work_order", WORK_ORDER), ("market_id", MARKET), ("as_of", AS_OF),
        ("status", "AWAITING_FOUNDER_RULING"),
        ("count", len(holds)),
        ("note",
         "Both holds are the same defect wearing two faces: the committed "
         "reader located a real policy block and declined to resolve "
         "pets_allowed from it. Neither is decided here, and neither is "
         "resolved by widening the reader inside the review it feeds."),
        ("holds", holds),
    ]))

    resolved = len(facts) + len(exclusions)
    status = OrderedDict([
        ("census", len(census)),
        ("routed", len(confirmed)),
        ("pet_friendly", len(facts)),
        ("verified_no_pets", len(exclusions)),
        ("policy_resolved", resolved),
        ("holds", len(holds)),
        ("routing_repair", 2),
        # A SET DIFFERENCE, not a subtraction of totals. The two counts differ:
        # 45 census identities carry no route, while one route points at an
        # identity the census no longer holds -- a leftover from the
        # property-code merge, where the surviving identity absorbed another.
        # Subtracting the totals nets those against each other and reports 44.
        ("census_without_route", len(census_keys - routed_keys)),
        ("routes_without_a_census_identity", len(routed_keys - census_keys)),
        ("unresolved", OrderedDict([
            ("brightdata_class", 112),
            ("policy_not_found_source_silence", 2),
            ("routing_repair", 2),
        ])),
    ])
    pilot = build_pilot(status)
    write_lf(STATUS_PATH, OrderedDict([
        ("schema", "ptf-detroit-ann-arbor-status/1.0"),
        ("work_order", WORK_ORDER), ("market_id", MARKET), ("as_of", AS_OF),
        ("provider_calls", 0), ("spend_usd", 0.0),
        ("status", status),
        ("brightdata_pilot_prepared", OrderedDict([
            ("rows", pilot["rows"]),
            ("run", False),
            ("projected_maximum_spend_usd",
             pilot["projected_maximum_spend_usd"]),
        ])),
    ]))

    print("=== Phase 5: hold packet ===")
    for hold in holds:
        print("  %-44s %s" % (hold["property"][:44],
                              hold["exact_policy_quote"][:60]))
    print()
    print("=== Phase 6: Detroit status ===")
    for field, value in status.items():
        if field != "unresolved":
            print("  %-24s %s" % (field, value))
    print("  unresolved             :", dict(status["unresolved"]))
    print()
    print("=== Bright Data pilot (PREPARED, NOT RUN) ===")
    print("  rows        :", pilot["rows"], pilot["composition"]["marriott"],
          "Marriott /", pilot["composition"]["hilton"], "Hilton")
    print("  sub-brands  :", pilot["composition"]["marriott_sub_brands"],
          pilot["composition"]["hilton_sub_brands"])
    print("  cities      :", len(pilot["composition"]["cities"]))
    print("  max spend   : $%.2f" % pilot["projected_maximum_spend_usd"])
    print("wrote", HOLDS_PATH.name, STATUS_PATH.name, PILOT_PATH.name)


if __name__ == "__main__":
    run()
