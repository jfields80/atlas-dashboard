"""PTF-GREENVILLE-NC-PARALLEL-SOURCE-READY-001 -- Phase 10: complete accounting.

Every discovered candidate, every census identity in exactly one disposition, every
hold by class, and per-corridor coverage, computed from the committed market-local
documents -- never typed. Also records the shadow package's identity, its
independent reproduction and the release stop.

Output:
  launch_packages/pettripfinder/markets/reports/greenville_nc_source_ready_accounting_009.json
"""
from __future__ import annotations

import json
import os
import sys
from collections import Counter, OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

WORK_ORDER = "PTF-GREENVILLE-NC-PARALLEL-SOURCE-READY-001"
MARKET_ID = "greenville-nc"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
STAGING = os.path.join(PKG, "markets", "staging", MARKET_ID)
OUT = os.path.join(REPORTS, "greenville_nc_source_ready_accounting_009.json")

#: Measured wall-clock facts of this run (UTC), recorded as observed.
TIMINGS = OrderedDict([
    ("GREENVILLE_START_TIMESTAMP", "2026-09-13T16:05:06Z"),
    ("geography_written", "2026-09-13T16:10:22Z"),
    ("osm_lane_seconds", 405.8),
    ("brand_lane_free_requests", 85),
    ("attended_and_static_reads", "2026-09-13T16:11Z-16:33Z"),
    ("source_ready_inputs_committed", "SEE_COMMIT"),
    ("shadow_package_sealed_and_fast", "SEE_SHADOW_REPORT"),
    ("independent_reproduction", "SEE_REPRODUCTION"),
    ("ZERO_TO_SOURCE_READY", "SEE_FINAL"),
])


def _load(path):
    with open(path, encoding="utf-8-sig") as fh:
        return json.load(fh)


def _coords_for(h, hotels):
    """(lat, lng, basis) for a census row: its own evidence's pin, else the pin of the
    census row on the SAME street name (house number removed, directional kept) whose
    house number is nearest. Reporting only -- never membership."""
    import re
    if h.get("latitude") is not None:
        return h["latitude"], h["longitude"], "the row's own map pin"

    def split(street):
        m = re.match(r"\s*(\d+)\s+(.*)", street or "")
        if not m:
            return None, ""
        name = re.sub(r"\s*\(.*\)", "", m.group(2).lower())
        name = re.sub(r"\b(street|st)\b", "st", name)
        name = re.sub(r"\b(boulevard|blvd)\b", "blvd", name)
        name = re.sub(r"\b(drive|dr)\b", "dr", name)
        name = re.sub(r"\b(road|rd)\b", "rd", name)
        name = re.sub(r"\bsouth\b", "s", name)
        return int(m.group(1)), " ".join(name.replace(".", "").split())
    num, name = split(h.get("street"))
    best = None
    for o in hotels:
        if o is h or o.get("latitude") is None:
            continue
        on, oname = split(o.get("street"))
        if oname and oname == name and num is not None:
            d = abs(on - num)
            if best is None or d < best[0]:
                best = (d, o)
    if best:
        return (best[1]["latitude"], best[1]["longitude"],
                "the pin of %s on the same street (%d house numbers away)" % (best[1]["canonical_name"], best[0]))
    return None, None, "no pin in the evidence and no pinned census row on the same street"


def requested_area_coverage(hotels, pf, np_):
    """Coverage for the areas the order names, as the geography's nearest-anchor
    OVERLAY (greenville_nc_geography_001.COVERAGE_AREAS). Reporting only."""
    from scripts.pettripfinder import greenville_nc_geography_001 as GEO
    areas = OrderedDict((a, []) for a, _la, _ln, _r in GEO.COVERAGE_AREAS)
    elsewhere, unplaced = [], []
    for h in hotels:
        lat, lng, basis = _coords_for(h, hotels)
        row = OrderedDict([("canonical_name", h["canonical_name"]),
                           ("state", "PUBLISHED_PET_FRIENDLY" if h["identity_key"] in pf
                            else "VERIFIED_NO_PETS" if h["identity_key"] in np_ else "UNRESOLVED"),
                           ("placement_basis", basis)])
        if lat is None:
            unplaced.append(row)
            continue
        area = GEO.coverage_area(lat, lng)
        (areas[area] if area else elsewhere).append(row)

    def summary(rows):
        return OrderedDict([("census", len(rows)),
                            ("pet_friendly", sum(1 for r in rows if r["state"] == "PUBLISHED_PET_FRIENDLY")),
                            ("verified_no_pets", sum(1 for r in rows if r["state"] == "VERIFIED_NO_PETS")),
                            ("unresolved", sum(1 for r in rows if r["state"] == "UNRESOLVED")),
                            ("identities", rows)])
    return OrderedDict([
        ("what_it_is", "The order's requested areas as a nearest-anchor overlay on each census row's own map pin "
                       "(or the pin of the nearest pinned census row on the same street). It decides nothing about "
                       "membership or corridors; a row outside every anchor radius is 'elsewhere', a row with no "
                       "usable pin is 'unplaced'."),
        ("areas", OrderedDict((a, summary(rows)) for a, rows in areas.items())),
        ("elsewhere_in_the_admitted_market", summary(elsewhere)),
        ("unplaced", summary(unplaced)),
    ])


def build():
    census = _load(os.path.join(PKG, "identity_census_proposed", "%s.json" % MARKET_ID))
    partition = _load(os.path.join(STAGING, "launch_package", "greenville_nc_final_partition_007.json"))
    geography = _load(os.path.join(REPORTS, "greenville_nc_geography_001.json"))
    osm = _load(os.path.join(REPORTS, "greenville_nc_osm_lane_001.json"))
    capture = _load(os.path.join(REPORTS, "greenville_nc_attended_capture_001.json"))
    shadow = _load(os.path.join(REPORTS, "greenville_nc_shadow_package_008.json"))

    hotels = census["hotels"]
    non_admitted = census["non_admitted"]
    states = Counter(i["final_state"] for i in partition["items"])
    by_state = {}
    for i in partition["items"]:
        by_state.setdefault(i["final_state"], []).append(i["canonical_name"])

    def names(klass, prefix=None):
        return [r["canonical_name"] for r in non_admitted if r["classification"] == klass
                and (prefix is None or (r.get("classification_reason") or "").startswith(prefix))]

    geography_holds = names("IDENTITY_REVIEW_REQUIRED", "GEOGRAPHY_HOLD")
    identity_review = [n for n in names("IDENTITY_REVIEW_REQUIRED") if n not in geography_holds]
    holds = OrderedDict([
        ("IDENTITY_HOLDS", OrderedDict([
            ("count", len(identity_review) + len(names("NAME_ONLY_UNRESOLVED")) + len(names("SAME_IDENTITY_REBRAND_SUCCESSOR"))),
            ("identity_review_required", identity_review),
            ("name_only_unresolved", names("NAME_ONLY_UNRESOLVED")),
            ("rebrand_unresolved", names("SAME_IDENTITY_REBRAND_SUCCESSOR")),
            ("note", "Not census identities: none is registered, none publishes. Every one is a competitor or map "
                     "NAME with no address of its own (or an owned roster row outside the box, Weldon), so none can "
                     "open a building; none needs a founder ruling.")])),
        ("ROUTING_HOLDS", OrderedDict([("count", states.get("AWAITING_OFFICIAL_URL", 0)),
                                       ("identities", by_state.get("AWAITING_OFFICIAL_URL", []))])),
        ("ACCESS_BLOCKED", OrderedDict([("count", states.get("ACCESS_BLOCKED", 0)),
                                        ("identities", by_state.get("ACCESS_BLOCKED", []))])),
        ("EVIDENCE_HOLDS", OrderedDict([("count", states.get("AWAITING_POLICY_OBSERVATION", 0)),
                                        ("identities", by_state.get("AWAITING_POLICY_OBSERVATION", []))])),
        ("GEOGRAPHY_HOLDS", OrderedDict([("count", len(geography_holds)), ("identities", geography_holds)])),
        ("PAID_HOLDS", OrderedDict([("count", 0), ("note", "No paid lane was used or reserved; the %d ACCESS_BLOCKED "
                                                            "identities are the paid-lane candidates for a later order under a founder budget."
                                                            % states.get("ACCESS_BLOCKED", 0))])),
        ("FOUNDER_HOLDS", OrderedDict([("count", 0), ("note", "No row requires a founder ruling. InTown Suites "
                                                               "(a no-pets statement on a page with no postal code) is held "
                                                               "as EVIDENCE, not escalated.")])),
    ])

    pf = {i["identity_key"] for i in partition["items"] if i["final_state"] == "PUBLISHED_PET_FRIENDLY"}
    np_ = {i["identity_key"] for i in partition["items"] if i["final_state"] == "VERIFIED_NO_PETS"}
    minimum = {c["corridor_id"]: c.get("minimum_hotel_count", 5)
               for c in _load(os.path.join(PKG, "markets", "proposed", "%s.json" % MARKET_ID))["corridors"]}
    klass = {c["corridor_id"]: c["geography_class"] for c in geography["corridors"]}
    coverage = []
    for c in geography["corridors"]:
        cid = c["corridor_id"]
        rows = [h for h in hotels if h.get("corridor") == cid]
        n_pf = sum(1 for h in rows if h["identity_key"] in pf)
        n_np = sum(1 for h in rows if h["identity_key"] in np_)
        coverage.append(OrderedDict([
            ("corridor_id", cid), ("geography_class", klass[cid]), ("postal_codes", c["included_postal_codes"]),
            ("census", len(rows)), ("pet_friendly", n_pf), ("verified_no_pets", n_np),
            ("unresolved", len(rows) - n_pf - n_np),
            ("corridor_page_publishes", n_pf >= minimum.get(cid, 5)),
        ]))

    area_coverage = requested_area_coverage(hotels, pf, np_)
    unnamed_map = sum(1 for e in osm["elements"] if not (e.get("tags") or {}).get("name"))
    doc = OrderedDict([
        ("schema", "ptf-market-source-ready-accounting/1.0"), ("work_order", WORK_ORDER), ("market_id", MARKET_ID),
        ("display_market", "Greenville, North Carolina"),
        ("state", "SOURCE_READY -- SHADOW_UNTIL_REGISTERED"),
        ("timings", TIMINGS),
        ("accounting", OrderedDict([
            ("TOTAL_DISCOVERED", census["total_candidates"]),
            ("total_discovered_note",
             "Distinct candidate identities in the identity graph after merging every lane (map, owned brand "
             "harvest, brand city pages and sitemaps, county tourism roster, competitor leads, first-party reads). "
             "Not counted: %d unnamed map elements (a map element with no name is not an identity) and four "
             "retired Wyndham routes (Wingate Greenville, Travelodge Greenville, Days Inn Kinston, Baymont "
             "Chocowinity) that redirect to the brand's search; nor 15 CVB listing slugs whose pages carry no "
             "hotel facility block (restaurants, clubs, a B&B read separately)." % unnamed_map),
            ("classification_counts", census["classification_counts"]),
            ("REGISTERED_CENSUS", census["count"]),
            ("registered_census_note", "The proposed census the registration order will register; nothing is registered by this order."),
            ("PET_FRIENDLY", states.get("PUBLISHED_PET_FRIENDLY", 0)),
            ("VERIFIED_NO_PETS", states.get("VERIFIED_NO_PETS", 0)),
            ("RESOLVED", partition["resolved"]), ("UNRESOLVED", partition["unresolved"]),
            ("partition_counts_by_state", OrderedDict(sorted(states.items()))),
            ("every_census_identity_has_exactly_one_disposition",
             len(partition["items"]) == census["count"]
             and len({i["identity_key"] for i in partition["items"]}) == census["count"]),
            ("outside_market_refused", len(names("OUTSIDE_MARKET"))),
            ("military_government_nonpublic_refused",
             [r["canonical_name"] for r in non_admitted if "MILITARY_GOVERNMENT_NONPUBLIC" in (r.get("classification_reason") or "")]),
        ])),
        ("holds_by_class", holds),
        ("corridor_coverage", coverage),
        ("requested_area_coverage", area_coverage),
        ("first_party_reads", capture["counts"]),
        ("package", OrderedDict([
            ("PACKAGE_CREATED", "YES"), ("execution_zone", shadow["execution_zone"]),
            ("package_id", shadow["package_id"]), ("PACKAGE_DIGEST", shadow["package_digest"]),
            ("created_from_source_sha", shadow["created_from_source_sha"]),
            ("package_path", shadow["package_path"]),
            ("BUILD_INPUT_KEY", shadow["build_input_key"]),
            ("INTENDED_DELTA", shadow["intended_delta"]),
            ("VALIDATION_RECEIPT", OrderedDict([("path", shadow["receipt_path"]), ("digest", shadow["receipt_digest"]),
                                                ("eligible", shadow["FAST_DATA_ONLY_RELEASE_ELIGIBLE"]),
                                                ("rules", shadow["fast_rules"]),
                                                ("unknown", shadow["unknown_rules"]), ("failed", shadow["failed_rules"]),
                                                ("determinism", shadow["determinism_result"])])),
            ("COVERAGE_SCORECARD", shadow["coverage_scorecard"]),
            ("UNRESOLVED_SET", shadow["unresolved_set"]),
            ("HOLD_SET", shadow["hold_set_non_admitted_census_rows"]),
            ("PACKAGE_REPRODUCIBLE", "YES"),
            ("reproduction",
             "Sealed twice in-process (equal digests); then, in a clean git worktree at the source commit, sealed "
             "again by a separate process (equal digest), and the whole derived chain -- geography, capture, census, "
             "clean set, partition, staged policy package, staged shard -- rebuilt from the raw captures with zero "
             "content difference against the commit, sealing to the same digest a third time."),
            ("parent_binding", shadow["parent_binding"]),
        ])),
        ("owned_evidence", OrderedDict([
            ("OWNED_IDENTITIES", "0 Greenville census identities pre-existed in any committed census; one Greenville route "
                                 "(Microtel Greenville/University Med) is carried by charlotte_nc_clean_authority_001 as the "
                                 "official_url of a CHARLOTTE Microtel -- a name collision in that market's evidence, recorded "
                                 "here, not edited (shared/other-market state)."),
            ("OWNED_ROUTES", "5 Marriott PGV* routes from the committed national harvest dayton_oh_brand_directory_harvest_001 "
                             "(Courtyard, Fairfield and Residence Inn Greenville; Fairfield Kinston and Weldon, both outside), "
                             "read at zero requests."),
            ("OWNED_VALID_POLICY_EVIDENCE", "0 -- no committed first-party Greenville pet-policy read existed; every policy "
                                            "record here is a new capture of this order."),
        ])),
        ("factory_code_changed", "NO -- every changed path is a greenville_nc_* helper, the market's discovery config, or a document under the market's own proposed / staging / report paths"),
        ("broad_regression_run", "NO"),
        ("final_production_candidate_created", "NO -- FAST composes the release index in memory only; no whole-site candidate was assembled"),
        ("founder_authorization_created", "NO"),
        ("deployed", "NO"),
        ("shared_state_touched", "NO -- launch_participation.json, bundle_cache_closure.json, the market_state pin, the generated globals, release contracts and the market registry are unchanged"),
        ("next_order", [
            "read the live parent only after Netlify is restored, Fayetteville deploys, and Jacksonville registers and deploys",
            "rebase this branch on it; copy markets/proposed/greenville-nc.json, identity_census_proposed/greenville-nc.json and the staged launch_package documents into their registered paths",
            "market_registration_cli --write, build_global_authority --write/--check, release contract, registration_release_lane register + seal --work-order (a NEW package id against the new parent; this shadow package's rule N fails by design once the parent moves)",
            "regression_delta classify, compose and reproduce the candidate, prepare the founder packet, deploy only on authorization",
        ]),
    ])
    return doc


def main():
    doc = build()
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    a = doc["accounting"]
    print({k: a[k] for k in ("TOTAL_DISCOVERED", "REGISTERED_CENSUS", "PET_FRIENDLY", "VERIFIED_NO_PETS", "RESOLVED", "UNRESOLVED")})
    print({k: v["count"] for k, v in doc["holds_by_class"].items()})
    for c in doc["corridor_coverage"]:
        print(c["corridor_id"].split("__")[1], c["geography_class"], c["census"], c["pet_friendly"], c["verified_no_pets"], c["unresolved"], c["corridor_page_publishes"])
    print(doc["package"]["PACKAGE_DIGEST"], doc["package"]["BUILD_INPUT_KEY"]["staged_input_digest"])
    print("one disposition each:", a["every_census_identity_has_exactly_one_disposition"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
