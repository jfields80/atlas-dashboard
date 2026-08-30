"""PTF-CINCINNATI-FOUNDER-REVIEW-AND-APPLICATION-004 -- ruling #1 and Phase 4.

    python -m scripts.pettripfinder.cincinnati_identity_and_routing_004
    python -m scripts.pettripfinder.cincinnati_identity_and_routing_004 --write

RULING #1 -- THE REBRAND
------------------------
The founder approved that the building at 9651 Seward Rd, Fairfield OH 45014,
committed to this census as "Extended Stay America-Cincinnati-Fairfield", now
trades as "Studio 6 Extended Stay Fairfield, OH - Cincinnati", and directed
that no policy be published against the old name.

A rename moves the identity key, because the key is derived from the canonical
name. So this SUPERSEDES rather than overwrites: the new row carries
``prior_identity_key``, the old key is preserved and reachable, and nothing
that referenced it is silently orphaned. It was checked against prior-census
twins, which is the check PTF-INDIANAPOLIS-FOUNDER-REVIEW-002 exists for --
"studio 6 cincinnati springdale" is a DIFFERENT identity at 11645 Chesterdale
Rd in Springdale, and the founder explicitly forbade merging them.

The property's policy is NOT published here. Its page states pet terms, and
they are capturable the moment a pass observes them against the new name.

PHASE 4 -- ROUTING REPAIRS, ALL AT ZERO COST
--------------------------------------------
D2  Two committed routes no longer resolve to their hotel. theglendalia.com
    serves an Indonesian gambling page and iresteasy.com a Japanese article
    about beef bowls; neither names the hotel, the city, or any Ohio postal
    code. Both are REMOVED from the shard and preserved verbatim in the
    retirement ledger. A dead route is worse than no route: it is a URL a
    future pass will spend a paid fetch on and then read somebody else's page.

D3  SureStay Florence's propertyCode URL redirects to a Best Western hotel
    SEARCH page. A brand index is not a property page. There is no free
    first-party evidence of where this property now lives, so the route is
    removed and the identity returns to URL recovery -- explicitly unresolved,
    which the work order permits and which is the honest state.

D4  hollywoodindiana.com now redirects to pennentertainment.com. Penn
    Entertainment is Hollywood Casino's own operator, the destination page is
    titled "Hotel | Hollywood Casino Lawrenceburg" and states Lawrenceburg IN
    47025, which binds to the census row. That is a first-party successor, not
    a reseller, so the route's URL is UPDATED rather than retired.
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import OrderedDict
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder import market_authority as MA              # noqa: E402
from scripts.pettripfinder.contracts.identity_key import ptf_identity_key  # noqa: E402

WORK_ORDER = "PTF-CINCINNATI-FOUNDER-REVIEW-AND-APPLICATION-004"
MARKET_ID = "cincinnati-oh"
OPERATOR = "jfields80"
AS_OF = "2026-08-29"

PKG = _REPO_ROOT / "launch_packages" / "pettripfinder"
CENSUS = PKG / "identity_census" / "cincinnati-oh.json"
REPORTS = PKG / "markets" / "reports"
LEDGER = REPORTS / "cincinnati_route_retirement_004_ledger.json"

OLD_KEY = "extended stay america cincinnati fairfield"
NEW_NAME = "Studio 6 Extended Stay Fairfield, OH - Cincinnati"
FORBIDDEN_MERGE = "studio 6 cincinnati springdale"

RETIRE = {
    "the glendalia": (
        "DOMAIN LAPSED AND RESOLD. theglendalia.com now serves 'BASKET168 - "
        "Situs Slot Pragmatic Gacor', an Indonesian gambling/e-commerce page "
        "with zero occurrences of Glendalia, Glendale, Ohio or any Cincinnati "
        "postal code. Observed by attended browser 2026-08-29 under "
        "PTF-CINCINNATI-ZERO-COST-CAPTURE-003."),
    "rest": (
        "DOMAIN LAPSED AND RESOLD. iresteasy.com now serves a Japanese "
        "article about beef-bowl ingredients (lang=ja) with no mention of a "
        "hotel, Cincinnati, Ohio or any 45xxx postal code. Observed by "
        "attended browser 2026-08-29 under PTF-CINCINNATI-ZERO-COST-"
        "CAPTURE-003."),
    "surestay hotel by best western florence": (
        "PROPERTY PAGE GONE. propertyCode.55078 redirects to a Best Western "
        "hotel-search page titled 'Search Best Western Hotels & Resorts'. A "
        "brand index is not a property page and its content is not this "
        "property's claim. No free first-party evidence of a successor URL "
        "exists, so this identity returns to PROPERTY_LEVEL_URL_RECOVERY "
        "rather than being bound to a guess."),
}

REPOINT = {
    "hollywood casino lawrenceburg": (
        "https://www.pennentertainment.com/hollywood-lawrenceburg/hotel",
        "pennentertainment.com",
        "hollywoodindiana.com redirects here. Penn Entertainment is this "
        "casino's own operator, and the destination page is titled 'Hotel | "
        "Hollywood Casino Lawrenceburg' and states Lawrenceburg, IN 47025, "
        "which binds to the census row. A first-party successor domain, not a "
        "reseller, so the route is repointed rather than retired."),
}


class RepairError(RuntimeError):
    pass


def _load(path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def rename(census, write):
    rows = census["hotels"]
    row = next((h for h in rows if h["identity_key"] == OLD_KEY), None)
    if row is None:
        raise RepairError("%s is not in the census" % OLD_KEY)
    new_key = ptf_identity_key(NEW_NAME)
    if any(h["identity_key"] == new_key for h in rows):
        raise RepairError("%r already exists; a rename must never collide"
                          % new_key)
    twin = next((h for h in rows if h["identity_key"] == FORBIDDEN_MERGE), None)
    if twin is None:
        raise RepairError("the twin the founder forbade merging is missing")
    if twin["address"] == row["address"]:
        raise RepairError("the twin shares this address; that is a merge "
                          "question, not a rename")

    row["prior_identity_key"] = OLD_KEY
    row["identity_key"] = new_key
    row["canonical_name"] = NEW_NAME
    row["display_name"] = NEW_NAME
    row["slug"] = new_key.replace(" ", "-")
    row["provenance"] = WORK_ORDER
    row["observed_at"] = AS_OF
    row["rename"] = OrderedDict((
        ("from_canonical_name", "Extended Stay America-Cincinnati-Fairfield"),
        ("from_identity_key", OLD_KEY),
        ("ruled_by", OPERATOR), ("ruled_on", AS_OF),
        ("work_order", WORK_ORDER),
        ("evidence",
         "The property's own page at motel6.com states h1 'Studio 6 Extended "
         "stay Fairfield, OH - Cincinnati'. Extended Stay America's own site "
         "no longer lists 9651 Seward Rd among its eleven Cincinnati-area "
         "addresses. Observed attended 2026-08-29."),
        ("not_merged_with", FORBIDDEN_MERGE),
        ("not_merged_because",
         "A different identity at 11645 Chesterdale Rd, Springdale OH 45246 -- "
         "a different building in a different city. The founder forbade the "
         "merge explicitly."),
        ("policy_deferred",
         "No policy is published against this identity. The founder ruled the "
         "Studio 6 terms must not be attached to the ESA name; they are "
         "capturable against the new name in the next pass."),
    ))
    return new_key, row


def repair_routes(write):
    doc = MA.load_market_routing_document(MARKET_ID)
    keep, removed = [], []
    for route in doc["routes"]:
        key = route["hotel_ref"]["identity_key"]
        if key in RETIRE:
            route = OrderedDict(route)
            route["retired_at"] = AS_OF
            route["retired_by"] = WORK_ORDER
            route["retired_reason"] = RETIRE[key]
            removed.append(route)
            continue
        if key in REPOINT:
            url, domain, why = REPOINT[key]
            route = OrderedDict(route)
            route["official_property_url"] = url
            route["official_domain"] = domain
            route["verified_at"] = AS_OF
            route["notes"] = why
        keep.append(route)

    missing = set(RETIRE) - {r["hotel_ref"]["identity_key"] for r in removed}
    if missing:
        raise RepairError("routes to retire not found: %s" % sorted(missing))
    if not any(r["hotel_ref"]["identity_key"] in REPOINT for r in keep):
        raise RepairError("the route to repoint was not found")
    return doc, keep, removed


def main(argv=None) -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--write", action="store_true")
    args = parser.parse_args(argv)
    try:
        census = _load(CENSUS)
        new_key, row = rename(census, args.write)
        doc, keep, removed = repair_routes(args.write)
    except RepairError as exc:
        print("REFUSED: %s" % exc)
        return 2

    print("rename          : %r -> %r" % (OLD_KEY, new_key))
    print("                  not merged with %r" % FORBIDDEN_MERGE)
    print("routes before   : %d" % len(doc["routes"]))
    print("routes retired  : %d (%s)"
          % (len(removed), ", ".join(sorted(RETIRE))))
    print("routes repointed: %d (%s)"
          % (len(REPOINT), ", ".join(sorted(REPOINT))))
    print("routes after    : %d" % len(keep))

    if args.write:
        CENSUS.write_text(json.dumps(census, indent=1, ensure_ascii=False)
                          + "\n", encoding="utf-8", newline="\n")
        print("WROTE %s" % CENSUS.name)

        LEDGER.write_text(json.dumps(OrderedDict((
            ("schema", "ptf-market-route-retirement-ledger/1.0"),
            ("work_order", WORK_ORDER), ("market_id", MARKET_ID),
            ("as_of", AS_OF),
            ("why", "Phase 4 of the founder review. Two domains had lapsed and "
                    "been resold and one property page had become a brand "
                    "search page. A route that resolves to somebody else's "
                    "website is worse than no route: it is a URL the next pass "
                    "spends a fetch on and then reads the wrong page from."),
            ("count", len(removed)), ("removed_routes", removed),
        )), indent=1, ensure_ascii=False) + "\n",
            encoding="utf-8", newline="\n")
        print("WROTE %s (%d preserved)" % (LEDGER.name, len(removed)))

        path = MA.routing_shard_path(MARKET_ID)
        shard = MA.build_routing_shard(MARKET_ID, keep,
                                       doc.get("source_batches") or ())
        path.write_text(MA.render_json(shard), encoding="utf-8", newline="")
        print("WROTE %s (%d routes)" % (path.name, shard["count"]))
    else:
        print("(check only -- pass --write)")
    return 0


if __name__ == "__main__":                                # pragma: no cover
    raise SystemExit(main())
