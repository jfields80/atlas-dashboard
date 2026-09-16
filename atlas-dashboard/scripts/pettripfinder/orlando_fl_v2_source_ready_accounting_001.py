"""PTF-ORLANDO-FL-HARDENED-V2-SOURCE-READY-001 -- Phases 10, 21-25 and 29: the machine-readable accounting.

Reads only committed reports and staged documents (nothing fetches) and writes one accounting document with:
  headline accounting, holds by class, exclusions by class, corridor coverage, submarket overlay coverage
  (Disney / Universal / Kissimmee ...), brand-by-brand acquisition accounting, provider-attempt accounting,
  competitor (BringFido) reconciliation, negation conflicts caught, remaining unresolved root causes, and the
  V1-vs-V2 diagnostic (V1 figures are the order's historical baseline, quoted, never read from the V1 branch).

Output: launch_packages/pettripfinder/markets/reports/orlando_fl_v2_source_ready_accounting_001.json
"""
from __future__ import annotations

import json
import os
import re
import sys
from collections import Counter, OrderedDict, defaultdict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

from scripts.pettripfinder import orlando_fl_v2_geography_001 as GEO  # noqa: E402
from scripts.pettripfinder.orlando_fl_v2_nonhotel_rulings_001 import exclusion_class  # noqa: E402
from scripts.pettripfinder.site_data import normalize_name  # noqa: E402

WORK_ORDER = "PTF-ORLANDO-FL-HARDENED-V2-SOURCE-READY-001"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
R = os.path.join(PKG, "markets", "reports")
OUT = os.path.join(R, "orlando_fl_v2_source_ready_accounting_001.json")
V1 = OrderedDict([("census", 545), ("pet_friendly", 87), ("no_pets", 2), ("resolved", 89), ("unresolved", 456),
                  ("access_blocked", 149)])


def L(name, default=None):
    p = os.path.join(R, name)
    if not os.path.exists(p):
        return default
    return json.load(open(p, encoding="utf-8-sig"))


def family(name, brand=""):
    n = (name or "").lower()
    b = (brand or "").upper()
    table = [
        ("MARRIOTT", r"marriott|courtyard|residence inn|springhill|fairfield|towneplace|ac hotel|aloft|westin|sheraton|"
                     r"moxy|element|renaissance|delta hotels|autograph|tribute|gaylord|ritz-carlton|four points|city express|w "),
        ("HILTON", r"hilton|hampton|embassy suites|homewood|home2|doubletree|tru by|tapestry|canopy|spark by|signia|waldorf|curio"),
        ("IHG", r"holiday inn|crowne plaza|staybridge|candlewood|even hotel|avid|intercontinental|kimpton|hotel indigo|voco"),
        ("WYNDHAM", r"wyndham|baymont|days inn|super 8|super8|ramada|travelodge|travel lodge|la quinta|microtel|howard johnson|"
                    r"hawthorn|wingate|tryp"),
        ("CHOICE", r"comfort inn|comfort suites|quality inn|quality suites|sleep inn|clarion|cambria|mainstay|suburban|"
                   r"econo lodge|rodeway|ascend|everhome"),
        ("HYATT", r"hyatt"), ("BEST_WESTERN", r"best western|surestay"), ("SONESTA", r"sonesta|americas best value|america's best value"),
        ("RED_ROOF", r"red roof|hometowne|home towne"), ("MOTEL6", r"motel 6|studio 6"), ("EXTENDED_STAY", r"extended stay america"),
        ("WOODSPRING", r"woodspring"),
    ]
    for fam, rx in table:
        if re.search(rx, n):
            return fam
    if b in ("DISNEY", "UNIVERSAL", "LOEWS", "ROSEN", "OMNI", "DRURY", "RADISSON"):
        return "RESORTS_AND_OTHER_COLLECTIONS"
    if re.search(r"disney|universal|loews|rosen|omni|four seasons|caribe royale|margaritaville|grand cypress|bonnet creek", n):
        return "RESORTS_AND_OTHER_COLLECTIONS"
    return "INDEPENDENT"


def main():
    census = json.load(open(os.path.join(PKG, "identity_census", "orlando-fl.json"), encoding="utf-8"))
    part = json.load(open(os.path.join(PKG, "orlando_fl_final_partition_v2_001.json"), encoding="utf-8"))
    clean = L("orlando_fl_v2_clean_authority_001.json")
    fc = L("orlando_fl_v2_firecrawl_pass_001.json", {}) or {}
    disc = L("orlando_fl_v2_firecrawl_discovery_001.json", {}) or {}
    ladder = L("orlando_fl_v2_ladder_plan_001.json", {}) or {}
    static = L("orlando_fl_v2_free_static_capture_001.json", {}) or {}
    reads = L("orlando_fl_v2_policy_reads_001.json", {}) or {}
    comp = L("orlando_fl_v2_competitor_challenge_001.json", {}) or {}
    dbpr = L("orlando_fl_v2_dbpr_lane_001.json", {}) or {}

    items = part["items"]
    hotels = {h["identity_key"]: h for h in census["hotels"]}
    pf = sum(1 for i in items if i["final_state"] == "PUBLISHED_PET_FRIENDLY")
    npets = sum(1 for i in items if i["final_state"] == "VERIFIED_NO_PETS")
    unres = [i for i in items if not i["resolved"]]
    disp = Counter(i["disposition"] for i in unres)

    non = census["non_admitted"]
    excl = Counter()
    for r in non:
        if r["classification"] == "NON_LODGING":
            excl[exclusion_class(r["classification_reason"])] += 1
    ncls = Counter(r["classification"] for r in non)

    holds = OrderedDict([
        ("IDENTITY", disp.get("IDENTITY_HOLD", 0)), ("ROUTING", disp.get("ROUTING_HOLD", 0)),
        ("ACCESS_BLOCKED", disp.get("ACCESS_BLOCKED", 0)), ("EVIDENCE", disp.get("EVIDENCE_HOLD", 0)),
        ("NEGATION", disp.get("NEGATION_HOLD", 0)), ("BROWSER_CAPTURE", disp.get("BROWSER_CAPTURE_NEEDED", 0)),
        ("POLICY_NOT_FOUND", disp.get("POLICY_NOT_FOUND", 0)), ("SOURCE_SILENT", disp.get("SOURCE_SILENT", 0)),
        ("MIXED_RESORT", disp.get("MIXED_RESORT_HOLD", 0)), ("PAID", disp.get("PAID_HOLD", 0)),
        ("GEOGRAPHY", disp.get("GEOGRAPHY_HOLD", 0)), ("FOUNDER", disp.get("FOUNDER_REVIEW", 0)),
        ("OTHER", sum(v for k, v in disp.items() if k not in (
            "IDENTITY_HOLD", "ROUTING_HOLD", "ACCESS_BLOCKED", "EVIDENCE_HOLD", "NEGATION_HOLD", "BROWSER_CAPTURE_NEEDED",
            "POLICY_NOT_FOUND", "SOURCE_SILENT", "MIXED_RESORT_HOLD", "PAID_HOLD", "GEOGRAPHY_HOLD", "FOUNDER_REVIEW"))),
    ])

    # corridors
    cor = OrderedDict()
    for slug, name, _a, klass, _m, _z, _d in GEO.CORRIDORS:
        cid = "orlando-fl__" + slug
        rows = [i for i in items if i["corridor"] == cid]
        p = sum(1 for i in rows if i["final_state"] == "PUBLISHED_PET_FRIENDLY")
        n = sum(1 for i in rows if i["final_state"] == "VERIFIED_NO_PETS")
        cor[slug] = OrderedDict([("class", klass), ("census", len(rows)), ("pet_friendly", p), ("no_pets", n),
                                 ("unresolved", len(rows) - p - n),
                                 ("resolution_rate", round((p + n) / len(rows), 3) if rows else None),
                                 ("page_publishes", p >= 5)])

    # submarket overlays
    over = defaultdict(Counter)
    for i in items:
        h = hotels[i["identity_key"]]
        area = GEO.route_overlay((i["corridor"] or "").split("__")[-1], h.get("street"), h.get("latitude"), h.get("longitude"))
        c = over[area or "unplaced"]
        c["census"] += 1
        c["pet_friendly"] += i["final_state"] == "PUBLISHED_PET_FRIENDLY"
        c["no_pets"] += i["final_state"] == "VERIFIED_NO_PETS"
    overlays = OrderedDict((k, OrderedDict([("census", v["census"]), ("pet_friendly", v["pet_friendly"]), ("no_pets", v["no_pets"]),
                                            ("unresolved", v["census"] - v["pet_friendly"] - v["no_pets"])]))
                           for k, v in sorted(over.items()))

    # brand-by-brand
    fc_rows = fc.get("rows", [])
    fc_by_key = {r["identity_key"]: r for r in fc_rows}
    bb = defaultdict(Counter)
    for i in items:
        h = hotels[i["identity_key"]]
        fam = family(h["canonical_name"], h.get("brand"))
        c = bb[fam]
        c["census"] += 1
        c["pet_friendly"] += i["final_state"] == "PUBLISHED_PET_FRIENDLY"
        c["no_pets"] += i["final_state"] == "VERIFIED_NO_PETS"
        c["unresolved"] += not i["resolved"]
        c["access_blocked"] += i["disposition"] == "ACCESS_BLOCKED"
        rr = i.get("router_record") or {}
        c["firecrawl_attempted"] += bool(rr.get("firecrawl_attempted"))
        c["firecrawl_success"] += rr.get("firecrawl_result") == "FIRECRAWL_PUBLICATION_GRADE"
    for r in fc_rows:
        if r.get("cohort") == "DISCOVERED":
            bb["CHOICE"]["firecrawl_attempted_identity_fill_routes"] += 1
            bb["CHOICE"]["firecrawl_success_identity_fill_routes"] += r.get("outcome") == "VALID"
    brands = OrderedDict((k, OrderedDict(sorted(v.items()))) for k, v in sorted(bb.items()))

    # providers
    classes = Counter(r.get("firecrawl_class") for r in fc_rows)
    eligible = sum(1 for r in ladder.get("rows", []) if r.get("firecrawl_candidate"))
    not_eligible = sum(1 for r in ladder.get("rows", []) if not r.get("firecrawl_candidate"))
    providers = OrderedDict([
        ("static_http_requests", static.get("free_http_requests_this_run")),
        ("firecrawl_eligible_by_router", eligible),
        ("firecrawl_not_eligible_by_router", not_eligible),
        ("firecrawl_not_eligible_by_reason", OrderedDict(sorted(Counter(r.get("firecrawl_reason") for r in ladder.get("rows", [])
                                                                         if not r.get("firecrawl_candidate")).items()))),
        ("firecrawl_attempted_policy_pass", len(fc_rows)),
        ("firecrawl_attempted_by_cohort", OrderedDict(sorted(Counter(r.get("cohort") for r in fc_rows).items()))),
        ("firecrawl_success_publication_grade", classes.get("FIRECRAWL_PUBLICATION_GRADE", 0)),
        ("firecrawl_identity_only_or_silent", classes.get("FIRECRAWL_IDENTITY_ONLY", 0) + classes.get("FIRECRAWL_SOURCE_SILENT", 0)),
        ("firecrawl_failed_blocked_or_mismatch", sum(v for k, v in classes.items() if k in ("FIRECRAWL_BLOCKED", "FIRECRAWL_FAILED", "FIRECRAWL_MISMATCH"))),
        ("firecrawl_classes", OrderedDict(sorted(classes.items()))),
        ("firecrawl_discovery_pages_attempted", len(disc.get("pages", []))),
        ("firecrawl_credits_policy_pass", fc.get("credits")),
        ("firecrawl_credits_discovery", disc.get("credits")),
        ("other_provider_attempted", 0),
        ("brightdata_calls", 0), ("places_calls", 0), ("usd_spent", 0.0),
        ("supported_browser_reads", sum(1 for r in reads.get("rows", []) if r.get("lane") == "ATTENDED_BROWSER")),
        ("supported_browser_required_unresolved", disp.get("BROWSER_CAPTURE_NEEDED", 0)),
        ("access_blocked_after_router_exhaustion", disp.get("ACCESS_BLOCKED", 0)),
        ("new_provider_spend", 0), ("new_provider_authorization_required", False),
    ])

    # competitor reconciliation
    leads = comp.get("leads", [])
    rows_all = census["hotels"] + census["non_admitted"]
    lead_rows = defaultdict(list)
    for r in rows_all:
        for o in r["evidence"]:
            if o.get("lane") == "COMPETITOR_LEAD":
                lead_rows[normalize_name(o["name"])].append(r)
    admitted_keys = {h["identity_key"] for h in census["hotels"]}
    recon = Counter()
    detail = []
    for l in leads:
        rs = lead_rows.get(normalize_name(l["name"]), [])
        r = rs[0] if rs else None
        if r is None:
            cls = "REVIEW"
        elif r["identity_key"] in admitted_keys and len(r.get("lanes", [])) > 1:
            cls = "EXACT_ATLAS_MATCH"
        elif r["classification"] == "NON_LODGING":
            cls = exclusion_class(r["classification_reason"])
        elif r["classification"] == "OUTSIDE_MARKET":
            cls = "OUTSIDE"
        elif r["classification"] == "SAME_IDENTITY_REBRAND_SUCCESSOR":
            cls = "REBRAND"
        elif r["lanes"] == ["COMPETITOR_LEAD"] and r["classification"] == "TRUE_HOTEL_IDENTITY":
            cls = "TRUE_MISSING_IDENTITY"
        else:
            cls = "REVIEW"
        recon[cls] += 1
        part_row = next((i for i in items if r is not None and i["identity_key"] == r["identity_key"]), None)
        detail.append(OrderedDict([("lead", l["name"]), ("class", cls), ("census_row", r["canonical_name"] if r else None),
                                   ("census_classification", r["classification"] if r else None),
                                   ("partition_disposition", part_row["disposition"] if part_row else None)]))
    matched = [d for d in detail if d["class"] == "EXACT_ATLAS_MATCH"]
    competitor = OrderedDict([
        ("bringfido_raw_discovery_count", comp.get("raw_captured")),
        ("bringfido_stated_total", comp.get("competitor_stated_total")),
        ("normalized_unique_identities", comp.get("normalized_unique")),
        ("rental_listings_excluded_as_vacation_rental", len(comp.get("rental_listings", []))),
        ("hotel_leads", len(leads)),
        ("matched_to_census", len(matched)),
        ("matched_but_policy_unresolved", sum(1 for d in matched if d["partition_disposition"] not in ("CLEAN_PET_FRIENDLY", "CLEAN_VERIFIED_NO_PETS"))),
        ("matched_published_pet_friendly", sum(1 for d in matched if d["partition_disposition"] == "CLEAN_PET_FRIENDLY")),
        ("matched_verified_no_pets_on_first_party", sum(1 for d in matched if d["partition_disposition"] == "CLEAN_VERIFIED_NO_PETS")),
        ("true_missing_qualifying", recon.get("TRUE_MISSING_IDENTITY", 0)),
        ("excluded_stale_outside", sum(v for k, v in recon.items() if k in ("OUTSIDE", "VACATION_RENTAL", "TIMESHARE", "RESORT_RESIDENCE", "NON_HOTEL", "REBRAND"))),
        ("review_name_not_bound", recon.get("REVIEW", 0)),
        ("by_class", OrderedDict(sorted(recon.items()))),
        ("leads", detail),
    ])

    neg = [r for r in clean["rejected"] if r["classification"].startswith("NEGATION_HOLD")]
    resolved = pf + npets
    doc = OrderedDict([
        ("schema", "ptf-source-ready-accounting/1.0"), ("work_order", WORK_ORDER), ("market_id", "orlando-fl"),
        ("headline", OrderedDict([
            ("total_discovered", census["total_candidates"]),
            ("dbpr_registry_leads", dbpr.get("lead_count")),
            ("qualifying_proposed_census", census["count"]),
            ("valid_pet_friendly", pf), ("valid_verified_no_pets", npets),
            ("resolved", resolved), ("unresolved", len(unres)),
            ("resolution_rate", round(resolved / census["count"], 4) if census["count"] else None),
        ])),
        ("holds", holds),
        ("unresolved_by_disposition", OrderedDict(sorted(disp.items()))),
        ("exclusions", OrderedDict([
            ("vacation_rental", excl.get("VACATION_RENTAL", 0)), ("timeshare", excl.get("TIMESHARE", 0)),
            ("resort_residence", excl.get("RESORT_RESIDENCE", 0)), ("non_hotel", excl.get("NON_HOTEL", 0)),
            ("outside", ncls.get("OUTSIDE_MARKET", 0)), ("closed", 0),
            ("dbpr_licences_excluded_without_entering_the_graph", dbpr.get("exclusion_totals")),
            ("non_admitted_by_classification", OrderedDict(sorted(ncls.items()))),
        ])),
        ("corridors", cor),
        ("submarket_overlays", overlays),
        ("brand_by_brand", brands),
        ("providers", providers),
        ("competitor_reconciliation", competitor),
        ("negation_conflicts_caught", OrderedDict([("count", len(neg)), ("rows", [OrderedDict([("class", r["classification"]),
                                                    ("name", (r.get("identity_signals") or {}).get("name_on_page")),
                                                    ("quote", (r.get("quote") or "")[:300])]) for r in neg])])),
        ("remaining_unresolved_root_causes", OrderedDict((d, OrderedDict([
            ("count", n), ("examples", [i["canonical_name"] for i in unres if i["disposition"] == d][:8]),
            ("next_action_example", next((i["next_action"] for i in unres if i["disposition"] == d), ""))]))
            for d, n in disp.most_common())),
        ("v1_vs_v2", OrderedDict([
            ("v1_baseline_from_order", V1),
            ("v2", OrderedDict([("census", census["count"]), ("pet_friendly", pf), ("no_pets", npets), ("resolved", resolved),
                                ("unresolved", len(unres)), ("access_blocked_after_router_exhaustion", disp.get("ACCESS_BLOCKED", 0))])),
            ("delta", OrderedDict([("census", census["count"] - V1["census"]), ("pet_friendly", pf - V1["pet_friendly"]),
                                   ("no_pets", npets - V1["no_pets"]), ("resolved", resolved - V1["resolved"]),
                                   ("unresolved", len(unres) - V1["unresolved"])])),
        ])),
    ])
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    print(json.dumps(OrderedDict([("headline", doc["headline"]), ("holds", holds), ("exclusions", doc["exclusions"]["non_admitted_by_classification"]),
                                  ("competitor", {k: v for k, v in competitor.items() if k != "leads"})]), indent=1))


if __name__ == "__main__":
    main()
