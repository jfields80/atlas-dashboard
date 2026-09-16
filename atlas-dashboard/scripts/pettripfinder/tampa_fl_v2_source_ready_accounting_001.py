"""PTF-TAMPA-FL-HARDENED-V2-SOURCE-READY-001 -- Phases 10, 20-25 and 29: the machine-readable accounting.

Reads only committed reports and staged documents (nothing fetches) and writes one accounting document with:
headline accounting, holds by class, exclusions by class, corridor coverage, brand-by-brand acquisition
accounting, provider-attempt accounting, competitor (BringFido) reconciliation, negation conflicts caught,
remaining unresolved root causes, and the V1-vs-V2 diagnostic (V1 figures are the order's historical
baseline, quoted, never read from a V1 branch).

Output: launch_packages/pettripfinder/markets/reports/tampa_fl_v2_source_ready_accounting_001.json
"""
from __future__ import annotations

import json
import os
import re
import sys
from collections import Counter, OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

from scripts.pettripfinder import tampa_fl_v2_geography_001 as GEO  # noqa: E402
from scripts.pettripfinder.tampa_fl_v2_nonhotel_rulings_001 import exclusion_class  # noqa: E402

WORK_ORDER = "PTF-TAMPA-FL-HARDENED-V2-SOURCE-READY-001"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
R = os.path.join(PKG, "markets", "reports")
OUT = os.path.join(R, "tampa_fl_v2_source_ready_accounting_001.json")
#: The mission's own historical Tampa V1 baseline, quoted verbatim; never read from a V1 branch.
V1 = OrderedDict([("census", 580), ("pet_friendly", 30), ("no_pets", 4), ("resolved", 34), ("unresolved", 546),
                  ("resolution_rate", 0.059), ("firecrawl_used", 0)])


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
                     r"moxy|element|renaissance|delta hotels|autograph|tribute|four points|le meridien"),
        ("HILTON", r"hilton|hampton|embassy suites|homewood|home2|doubletree|tru by|tapestry|canopy|spark by|signia|waldorf|curio|outset"),
        ("IHG", r"holiday inn|crowne plaza|staybridge|candlewood|even hotel|avid|intercontinental|kimpton|hotel indigo|voco"),
        ("WYNDHAM", r"wyndham|baymont|days inn|super 8|super8|ramada|travelodge|travel lodge|la quinta|microtel|howard johnson|"
                    r"hawthorn|wingate|tryp"),
        ("CHOICE", r"comfort inn|comfort suites|quality inn|quality suites|sleep inn|clarion|cambria|mainstay|suburban|"
                   r"econo lodge|rodeway|ascend|everhome"),
        ("HYATT", r"hyatt"), ("BEST_WESTERN", r"best western|surestay"), ("SONESTA", r"sonesta|americas best value|america's best value"),
        ("RED_ROOF", r"red roof|hometowne|home towne"), ("MOTEL6", r"motel 6|studio 6"), ("EXTENDED_STAY", r"extended stay america"),
        ("WOODSPRING", r"woodspring"), ("DRURY", r"drury"), ("OMNI", r"\bomni\b"), ("RADISSON", r"radisson"),
    ]
    for fam, rx in table:
        if re.search(rx, n):
            return fam
    return "INDEPENDENT"


def main():
    census = json.load(open(os.path.join(PKG, "identity_census_proposed", "tampa-fl.json"), encoding="utf-8"))
    part = json.load(open(os.path.join(PKG, "markets", "staging", "tampa-fl", "launch_package",
                                       "tampa_fl_final_partition_v2_001.json"), encoding="utf-8"))
    clean = L("tampa_fl_v2_clean_authority_001.json", {}) or {}
    fc = L("tampa_fl_v2_firecrawl_pass_001.json", {}) or {}
    static = L("tampa_fl_v2_free_static_capture_001.json", {}) or {}
    comp = L("tampa_fl_v2_competitor_challenge_001.json", {}) or {}
    dbpr = L("tampa_fl_v2_dbpr_lane_001.json", {}) or {}
    routing = L("tampa_fl_v2_routing_001.json", {}) or {}
    wyndham = L("tampa_fl_v2_wyndham_lane_001.json", {}) or {}

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
        ("ROUTING", disp.get("ROUTING_HOLD", 0)), ("BROWSER_CAPTURE", disp.get("BROWSER_CAPTURE_NEEDED", 0)),
        ("ACCESS_BLOCKED", disp.get("ACCESS_BLOCKED", 0)), ("SOURCE_SILENT", disp.get("SOURCE_SILENT", 0)),
        ("EVIDENCE", disp.get("EVIDENCE_HOLD", 0)), ("NEGATION", disp.get("NEGATION_HOLD", 0)),
        ("IDENTITY_MISMATCH", disp.get("IDENTITY_MISMATCH_HOLD", 0)),
        ("OTHER", sum(v for k, v in disp.items() if k not in (
            "ROUTING_HOLD", "BROWSER_CAPTURE_NEEDED", "ACCESS_BLOCKED", "SOURCE_SILENT", "EVIDENCE_HOLD",
            "NEGATION_HOLD", "IDENTITY_MISMATCH_HOLD"))),
    ])

    # corridors
    cor = OrderedDict()
    for slug, name, _a, klass, _m, _z, _d in GEO.CORRIDORS:
        cid = "tampa-fl__" + slug
        rows = [i for i in items if i["corridor"] == cid]
        p = sum(1 for i in rows if i["final_state"] == "PUBLISHED_PET_FRIENDLY")
        n = sum(1 for i in rows if i["final_state"] == "VERIFIED_NO_PETS")
        cor[slug] = OrderedDict([("name", name), ("class", klass), ("census", len(rows)), ("pet_friendly", p),
                                 ("no_pets", n), ("unresolved", len(rows) - p - n),
                                 ("resolution_rate", round((p + n) / len(rows), 3) if rows else None),
                                 ("page_publishes", p >= 5)])
    uncorridored = sum(1 for i in items if not i.get("corridor"))

    # brand-by-brand
    fam_counter = Counter()
    fam_pf = Counter()
    fam_np = Counter()
    fam_unres = Counter()
    fam_fc_attempt = Counter()
    fam_fc_success = Counter()
    fam_blocked = Counter()
    for i in items:
        h = hotels.get(i["identity_key"], {})
        fam = family(i["canonical_name"], h.get("brand"))
        fam_counter[fam] += 1
        if i["final_state"] == "PUBLISHED_PET_FRIENDLY":
            fam_pf[fam] += 1
        elif i["final_state"] == "VERIFIED_NO_PETS":
            fam_np[fam] += 1
        else:
            fam_unres[fam] += 1
        if i["disposition"] == "ACCESS_BLOCKED":
            fam_blocked[fam] += 1
    for r in fc.get("rows", []):
        fam = (r.get("family") or "").upper() or "INDEPENDENT"
        fam_fc_attempt[fam] += 1
        if r.get("firecrawl_class") == "FIRECRAWL_PUBLICATION_GRADE":
            fam_fc_success[fam] += 1
    brand_tbl = OrderedDict()
    for fam in sorted(fam_counter):
        brand_tbl[fam] = OrderedDict([
            ("census", fam_counter[fam]), ("pet_friendly", fam_pf[fam]), ("no_pets", fam_np[fam]),
            ("unresolved", fam_unres[fam]), ("firecrawl_attempted", fam_fc_attempt.get(fam, 0)),
            ("firecrawl_success", fam_fc_success.get(fam, 0)), ("access_blocked", fam_blocked.get(fam, 0)),
        ])

    # competitor (BringFido) reconciliation
    comp_leads = comp.get("leads", [])
    census_names = {re.sub(r"[^a-z0-9]+", " ", h["canonical_name"].lower()).strip() for h in census["hotels"]}

    def _norm(n):
        return re.sub(r"[^a-z0-9]+", " ", (n or "").lower()).strip()

    comp_matched = sum(1 for r in comp_leads if _norm(r["name"]) in census_names)
    comp_true_missing = len(comp_leads) - comp_matched

    static_outcomes = Counter(str(r.get("outcome")) for r in static.get("rows", []))
    fc_class = Counter(r.get("firecrawl_class") for r in fc.get("rows", []))

    router_root_causes = OrderedDict([
        ("ROUTING_HOLD", "no first-party route was ever assembled: mostly independent DBPR-licensed motels/inns "
                         "with no brand inventory, bureau or map route, and brand routes 42 rows deep whose "
                         "static-only families (IHG, Choice, Best Western, Hyatt, Red Roof, Radisson, Motel 6) "
                         "this order's Firecrawl probe cohort did not reach individually"),
        ("BROWSER_CAPTURE_NEEDED", "Marriott/Hilton/Hyatt routes this order's supported-browser lane had not yet "
                                   "reached when Hilton's 5-in-a-row wall stopped that lane, or Hyatt routes on "
                                   "subdomains this browser session has no read permission for"),
        ("ACCESS_BLOCKED", "every free/authorized lane this order attempted (static plain client, Firecrawl where "
                           "eligible) was refused or failed"),
        ("SOURCE_SILENT", "the page served and stated no operative pet policy the shared readers located"),
        ("EVIDENCE_HOLD", "a fee/weight/count sentence with no explicit acceptance wording in the same quote; "
                          "held rather than published on an amenity fragment alone"),
        ("IDENTITY_MISMATCH_HOLD", "the fetched page's own identity did not confirm this census row"),
    ])

    doc = OrderedDict([
        ("schema", "ptf-source-ready-accounting/1.0"), ("work_order", WORK_ORDER), ("market_id", "tampa-fl"),
        ("headline", OrderedDict([
            ("total_discovered_dbpr_leads", dbpr.get("lead_count", None)),
            ("proposed_census", census["count"]), ("valid_pet_friendly", pf), ("valid_verified_no_pets", npets),
            ("resolved", pf + npets), ("unresolved", census["count"] - pf - npets),
            ("resolution_rate", round((pf + npets) / census["count"], 4) if census["count"] else None),
        ])),
        ("holds_by_class", holds),
        ("exclusions", OrderedDict([
            ("non_lodging_total", sum(1 for r in non if r["classification"] == "NON_LODGING")),
            ("by_exclusion_class", OrderedDict(sorted(excl.items()))),
            ("outside_market", ncls.get("OUTSIDE_MARKET", 0)),
            ("name_only_unresolved", ncls.get("NAME_ONLY_UNRESOLVED", 0)),
            ("identity_review_required", ncls.get("IDENTITY_REVIEW_REQUIRED", 0)),
            ("same_campus_distinct_entity", ncls.get("SAME_CAMPUS_DISTINCT_ENTITY", 0)),
            ("same_identity_rebrand_successor", ncls.get("SAME_IDENTITY_REBRAND_SUCCESSOR", 0)),
            ("dbpr_cndo_excluded", dbpr.get("exclusion_totals", {}).get("CNDO", 0)),
            ("dbpr_dwel_excluded", dbpr.get("exclusion_totals", {}).get("DWEL", 0)),
            ("dbpr_napt_excluded", dbpr.get("exclusion_totals", {}).get("NAPT", 0)),
        ])),
        ("corridor_coverage", cor),
        ("uncorridored_rows", uncorridored),
        ("corridor_count", len(cor)),
        ("corridors_publishing", sum(1 for c in cor.values() if c["page_publishes"])),
        ("brand_by_brand", brand_tbl),
        ("providers", OrderedDict([
            ("static_capture_outcomes", OrderedDict(sorted(static_outcomes.items()))),
            ("static_free_http_requests", static.get("free_http_requests_this_run", 0)),
            ("firecrawl_class_counts", OrderedDict(sorted((k, v) for k, v in fc_class.items() if k))),
            ("firecrawl_planned_rows", fc.get("planned_rows", 0)), ("firecrawl_attempted_rows", fc.get("attempted_rows", 0)),
            ("firecrawl_credits", fc.get("credits", {})),
            ("wyndham_read", wyndham.get("read", 0)), ("wyndham_retired_routes", wyndham.get("retired", 0)),
            ("wyndham_by_pet_indicator", wyndham.get("by_pet_indicator", {})),
            ("routed_admitted", routing.get("census_admitted", 0)),
            ("routing_by_state", (routing.get("counts") or {}).get("by_routing_state", {})),
            ("usd_spent", 0.0), ("new_provider_authorization", "NONE"),
        ])),
        ("competitor_reconciliation", OrderedDict([
            ("competitor", "BringFido"),
            ("cities_challenged", comp.get("cities_challenged", 0)),
            ("stated_totals_by_city", comp.get("stated_totals_by_city", {})),
            ("raw_captured", comp.get("raw_captured", 0)), ("normalized_unique", comp.get("normalized_unique", 0)),
            ("matched_to_census_by_exact_name", comp_matched),
            ("true_missing_candidates_by_name", comp_true_missing),
            ("note", "Name-normalised matching only, a first pass; a true-missing figure here is a candidate "
                     "count pending first-party verification, not an admitted identity."),
        ])),
        ("negation_conflicts_caught", clean.get("negation_conflicts_caught", [])),
        ("remaining_unresolved_root_causes", router_root_causes),
        ("v1_vs_v2", OrderedDict([
            ("v1", V1),
            ("v2", OrderedDict([("census", census["count"]), ("pet_friendly", pf), ("no_pets", npets),
                                ("resolved", pf + npets), ("unresolved", census["count"] - pf - npets),
                                ("resolution_rate", round((pf + npets) / census["count"], 4) if census["count"] else None),
                                ("firecrawl_used", fc.get("attempted_rows", 0))])),
            ("delta", OrderedDict([("census", census["count"] - V1["census"]), ("pet_friendly", pf - V1["pet_friendly"]),
                                   ("no_pets", npets - V1["no_pets"]), ("resolved", (pf + npets) - V1["resolved"]),
                                   ("unresolved", (census["count"] - pf - npets) - V1["unresolved"])])),
        ])),
    ])
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    print("headline:", doc["headline"])
    print("holds:", dict(doc["holds_by_class"]))
    print("corridors publishing:", doc["corridors_publishing"], "/", doc["corridor_count"])
    print("competitor:", doc["competitor_reconciliation"]["matched_to_census_by_exact_name"], "matched,",
          doc["competitor_reconciliation"]["true_missing_candidates_by_name"], "true-missing candidates")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
