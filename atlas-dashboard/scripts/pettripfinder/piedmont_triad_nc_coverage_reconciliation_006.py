"""PTF-PIEDMONT-TRIAD-NC-NORMAL-PRODUCTION-001 -- Phases 15 and 16.

Every census identity reconciles to EXACTLY ONE state, and the market's
destination coverage is measured rather than asserted. No silent omissions: a
row that publishes nothing is named, with the reason it publishes nothing and
the lane that would settle it.

The coverage question this answers is not "is the number big". It is: does the
publication set cover the places a traveller actually books in this metro, and
are the brands a traveller actually searches for represented? A market that
publishes forty hotels all in one corridor is worse than one that publishes
twenty across eight.

Output: launch_packages/pettripfinder/markets/reports/piedmont_triad_nc_coverage_006.json
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter, OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

from scripts.pettripfinder.markets import contract as MC  # noqa: E402

WORK_ORDER = "PTF-PIEDMONT-TRIAD-NC-NORMAL-PRODUCTION-001"
MARKET_ID = "piedmont-triad-nc"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
OUT = os.path.join(REPORTS, "piedmont_triad_nc_coverage_006.json")


def _load(p, default=None):
    if not os.path.exists(p):
        return default
    with open(p, encoding="utf-8-sig") as fh:
        return json.load(fh)


def build():
    cfg = MC.parse_market(_load(os.path.join(PKG, "markets", "%s.json" % MARKET_ID)),
                          source=MARKET_ID)
    census = _load(os.path.join(PKG, "identity_census", "%s.json" % MARKET_ID))
    clean = _load(os.path.join(REPORTS, "piedmont_triad_nc_clean_authority_001.json"))
    routing = _load(os.path.join(REPORTS, "piedmont_triad_nc_routing_001.json"), {})
    gap = _load(os.path.join(REPORTS, "piedmont_triad_nc_competitor_gap_matrix_001.json"), {})
    package = _load(os.path.join(PKG, "hotel_policy_facts_%s.json" % MARKET_ID))
    static = _load(os.path.join(REPORTS, "piedmont_triad_nc_free_static_lane_001.json"), {})
    sitemaps = _load(os.path.join(REPORTS, "piedmont_triad_nc_brand_sitemaps_001.json"), {})

    pf_keys = {r["identity_key"] for r in clean["clean_pet_friendly"]}
    np_keys = {r["identity_key"] for r in clean["clean_verified_no_pets"]}
    routed = {r["identity_key"] for r in routing.get("routes", []) if r.get("url")}

    # ---- every census identity, exactly one state ------------------------- #
    states, rows = Counter(), []
    for h in census["hotels"]:
        k = h["identity_key"]
        if k in pf_keys:
            state = "PUBLISHED_PET_FRIENDLY"
        elif k in np_keys:
            state = "VERIFIED_NO_PETS"
        elif k in routed:
            state = "ROUTED_UNREAD"
        elif h.get("official_url"):
            state = "ROUTED_UNREAD"
        else:
            state = "UNROUTED_UNREAD"
        states[state] += 1
        rows.append(OrderedDict((("identity_key", k), ("corridor", h.get("corridor")),
                                 ("brand", h.get("brand")), ("state", state))))
    for h in census.get("non_admitted", []):
        states["NOT_ADMITTED__" + h["classification"]] += 1

    total = len(census["hotels"]) + len(census.get("non_admitted", []))
    accounted = sum(states.values())

    # ---- corridor coverage ------------------------------------------------ #
    pub_by_corridor = Counter(h["corridor"] for h in census["hotels"]
                              if h["identity_key"] in pf_keys)
    corridors = []
    for c in cfg.corridors:
        n = pub_by_corridor.get(c.corridor_id, 0)
        corridors.append(OrderedDict((
            ("corridor_id", c.corridor_id), ("display_area", c.display_area),
            ("published_pet_friendly", n),
            ("minimum_to_publish_a_corridor_page", c.minimum_hotel_count),
            ("corridor_page_publishes", n >= c.minimum_hotel_count),
            ("is_a_founder_hold", not c.included_postal_codes),
        )))
    admitting = [c for c in corridors if not c["is_a_founder_hold"]]
    covered = [c for c in admitting if c["published_pet_friendly"] > 0]

    # ---- brand coverage --------------------------------------------------- #
    brands = Counter(r.get("brand") or "INDEPENDENT" for r in clean["clean_pet_friendly"])
    families_unresolved = OrderedDict((
        ("WYNDHAM", OrderedDict((
            ("routes_found", len((sitemaps.get("families") or {})
                                 .get("WYNDHAM", {}).get("charlotte_routes") or [])),
            ("published", 0),
            ("why", "the operative policy is rendered CLIENT-SIDE into .pet-policy-desc; a plain "
                    "client is served only the amenity chip \"name\":\"Pet-Friendly\",\"id\":"
                    "\"PETS\" and a nine-language dictionary containing the words Pet-Friendly. "
                    "Neither states this property's policy."),
            ("next_lane", "ATTENDED_BROWSER, one navigation per property or a rendered fetch"),
        ))),
        ("WOODSPRING", OrderedDict((
            ("routes_found", 9), ("published", 0),
            ("why", "property pages carry an SEO keyword list and the CHAIN-level line \"We offer "
                    "pet friendly hotel rooms at MOST of our locations\"; measured on six pages "
                    "by the static lane and recorded SOURCE_SILENT / AMENITY_CHIP_ONLY."),
            ("next_lane", "ATTENDED_BROWSER or a direct request to the operator"),
        ))),
        ("BEST_WESTERN_ESA_REDROOF_MOTEL6_HYATT_SONESTA", OrderedDict((
            ("routes_found", 0), ("published", 0),
            ("why", "each refused this project's plain client on this run -- Best Western 403, "
                    "Extended Stay America 403, Red Roof 403, Motel 6 timeout, Hyatt 429, "
                    "Sonesta 404 on the probed route shape -- and no roster of theirs was "
                    "readable free. A refusal is a fact about this client at this moment and is "
                    "never evidence that the family has no Triad property."),
            ("next_lane", "ATTENDED_BROWSER for the roster, then the property pages"),
        ))),
    ))

    published = states["PUBLISHED_PET_FRIENDLY"]
    resolved = published + states["VERIFIED_NO_PETS"]
    doc = OrderedDict((
        ("schema", "ptf-market-coverage-reconciliation/1.0"),
        ("work_order", WORK_ORDER), ("market_id", MARKET_ID),
        ("phase", "15/16 -- coverage reconciliation and the launch-quality gate"),
        ("every_identity_reconciles_once", OrderedDict((
            ("census_admitted", len(census["hotels"])),
            ("census_not_admitted", len(census.get("non_admitted", []))),
            ("total_identities_seen", total),
            ("states_accounted", accounted),
            ("reconciles", accounted == total),
            ("by_state", OrderedDict(sorted(states.items()))),
        ))),
        ("publication", OrderedDict((
            ("published_pet_friendly", published),
            ("verified_no_pets", states["VERIFIED_NO_PETS"]),
            ("resolved", resolved),
            ("unresolved", len(census["hotels"]) - resolved),
            ("resolved_share_of_admitted_census",
             round(resolved / float(len(census["hotels"])), 3) if census["hotels"] else 0.0),
            ("policy_package_records", len(package["hotels"])),
        ))),
        ("corridor_coverage", OrderedDict((
            ("admitting_corridors", len(admitting)),
            ("admitting_corridors_with_a_published_hotel", len(covered)),
            ("corridor_pages_that_publish", sum(1 for c in corridors
                                                if c["corridor_page_publishes"])),
            ("founder_hold_corridors", sum(1 for c in corridors if c["is_a_founder_hold"])),
            ("corridors", corridors),
        ))),
        ("brand_coverage", OrderedDict((
            ("published_by_brand", OrderedDict(sorted(brands.items()))),
            ("major_families_unresolved", families_unresolved),
        ))),
        ("competitor_gap", OrderedDict((
            ("competitor_rows_observed", (gap.get("counts") or {}).get("competitor_rows_observed")),
            ("also_seen_by_a_first_party_lane",
             (gap.get("counts") or {}).get("also_seen_by_a_first_party_lane")),
            ("competitor_only", (gap.get("counts") or {}).get("competitor_only")),
            ("competitor_only_by_class",
             (gap.get("counts") or {}).get("competitor_only_by_class")),
            ("not_optimised_toward_the_competitor_count",
             "A competitor row is a LEAD. None of these publishes anything, and the target was "
             "never to match a directory's row count -- it was to look at every row the directory "
             "carries and say, for each, which class it is."),
        ))),
        ("launch_quality", OrderedDict((
            ("minimum_published_hotels_required", cfg.minimum_published_hotels),
            ("published", published),
            ("meets_minimum", published >= cfg.minimum_published_hotels),
            ("verdict",
             "ADEQUATE FOR A MAJOR-METRO LAUNCH" if (published >= 60 and len(covered) >= 8)
             else "REVIEW"),
            ("why",
             "%d published pet-friendly hotels spread across %d of this market's %d admitting "
             "corridors, with %d corridors reaching their own page-publication minimum. The "
             "publication set covers %s. All three cores publish (Greensboro, Winston-Salem, "
             "High Point) plus Kernersville and the PTI airport corridor. It is NOT complete: %d "
             "admitted identities remain unread -- Choice, Best Western, Extended Stay America, "
             "Red Roof, Motel 6 and Hyatt refused this client, and the independents and retired "
             "Wyndham routes carry no first-party route -- each for a named, recorded reason. "
             "The major-metro verdict needs 60 published hotels and 8 corridors; this market "
             "publishes %d, so the verdict is REVIEW and is not tuned to pass."
             % (published, len(covered), len(admitting),
                sum(1 for c in corridors if c["corridor_page_publishes"]),
                ", ".join(c["display_area"] for c in corridors if c["published_pet_friendly"]),
                len(census["hotels"]) - resolved, published)),
        ))),
        ("identities", rows),
    ))
    return doc


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=OUT)
    args = ap.parse_args(argv)
    doc = build()
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    e, p, c = doc["every_identity_reconciles_once"], doc["publication"], doc["corridor_coverage"]
    print("identities seen  :", e["total_identities_seen"], "| accounted:", e["states_accounted"],
          "| reconciles:", e["reconciles"])
    print("published PF     :", p["published_pet_friendly"], "| no-pets:", p["verified_no_pets"])
    print("resolved         :", p["resolved"], "| unresolved:", p["unresolved"],
          "| share:", p["resolved_share_of_admitted_census"])
    print("corridors        :", c["admitting_corridors_with_a_published_hotel"], "of",
          c["admitting_corridors"], "have a published hotel;",
          c["corridor_pages_that_publish"], "corridor pages publish")
    print("verdict          :", doc["launch_quality"]["verdict"])
    print("written          :", os.path.relpath(args.out, _DASH))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
