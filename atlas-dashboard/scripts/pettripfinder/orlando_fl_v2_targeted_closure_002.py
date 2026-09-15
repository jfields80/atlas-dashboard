"""PTF-ORLANDO-FL-V2-TARGETED-COVERAGE-CLOSURE-002 -- machine-readable closure accounting.

Reads the source-ready baseline from its COMMIT (git show of ad2423b5; nothing in the working tree is trusted as "before")
and the current staged documents as "after", and writes one document with:

  bringfido_closure            every BringFido-matched census hotel that was unresolved at the baseline
  v1_regression_reconciliation the 23 hotels V1 published pet-friendly that the baseline did not
  hilton_marriott_targeted     every targeted Hilton / Marriott page read, with its browser status
  corridor_critical            per non-publishing corridor: the minimum cohort that could change the decision, what was
                               worked, and the result
  per_target_router_tracks     OWNED ROUTE / STATIC / OFFICIAL ROUTE / FIRECRAWL / OTHER PROVIDER / BROWSER / FINAL
  revised_unresolved_root_causes, negation_conflicts, firecrawl_this_pass, headline before/after

A baseline identity is followed to the current census by its key, then by its brand property code, then by its street
identity (a page read may rename a building to the name its own page states; the building is the same).

Output: launch_packages/pettripfinder/markets/reports/orlando_fl_v2_targeted_closure_002.json
"""
from __future__ import annotations

import json
import os
import subprocess
from collections import Counter, OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
REPO = os.path.dirname(_DASH)
BASE = "ad2423b5"
PKG = "launch_packages/pettripfinder"
#: the baseline (ad2423b5) paths, read by git show; REGISTERED by PTF-ORLANDO-FL-V2-REGISTRATION-AND-FOUNDER-PACKET-003 to the paths below
BASE_CENSUS = PKG + "/identity_census_proposed/orlando-fl.json"
BASE_PARTITION = PKG + "/markets/staging/orlando-fl/launch_package/orlando_fl_final_partition_v2_001.json"
CENSUS = PKG + "/identity_census/orlando-fl.json"
PARTITION = PKG + "/orlando_fl_final_partition_v2_001.json"
ACCOUNTING = PKG + "/markets/reports/orlando_fl_v2_source_ready_accounting_001.json"
V1DIAG = PKG + "/markets/reports/orlando_fl_v2_v1_diagnostic_001.json"
CLEAN = PKG + "/markets/reports/orlando_fl_v2_clean_authority_001.json"
RAW = PKG + "/markets/staging/orlando-fl/raw_captures/"
OUT = os.path.join(_DASH, PKG, "markets", "reports", "orlando_fl_v2_targeted_closure_002.json")
CORRIDOR_THRESHOLD = 5

CORRIDOR_WORK = OrderedDict([
    ("walt-disney-world", OrderedDict([
        ("minimum_cohort", ["drury plaza hotel orlando disney springs area", "hilton orlando buena vista palace",
                            "hilton orlando lake buena vista"]),
        ("why", "PF 4, needs 1; the Disney resorts without a dog section on their own page cannot state a policy, the "
                "three brand hotels with a first-party route can"),
    ])),
    ("four-corners-davenport", OrderedDict([
        ("minimum_cohort", ["omni championsgate resort hotel lp", "hampton inn orlando maingate south",
                            "comfort inn and suites maingate south davenport", "rodeway inn davenport"]),
        ("why", "PF 2, needs 3; four hotels have (or were given) a first-party route; Home Suites, Stayable, the Reunion "
                "group-sales row and a vacation home have none"),
    ])),
    ("winter-park-maitland", OrderedDict([
        ("minimum_cohort", ["hilton garden inn winter park", "springhill suites winter park", "park plaza",
                            "thurston house", "winter park sweet lodge"]),
        ("why", "PF 2, needs 3 of 5 unresolved"),
    ])),
    ("kissimmee-east", OrderedDict([
        ("minimum_cohort", ["crown motel", "heritage park inn", "park royal orlando", "staymore extended studios",
                            "secrets hideaway", "tropicana motel"]),
        ("why", "PF 2, needs 3; 18 of 24 unresolved rows are DBPR/OSM-only motels with no route; only these 6 carry any "
                "route, and 3 of those routes are dead or point at another business"),
    ])),
    ("apopka", OrderedDict([
        ("minimum_cohort", ["hilton garden inn at apopka city center", "budget inn of apopka", "home inn and suites",
                            "inn at overland"]),
        ("why", "PF 1, needs 4 of 4 unresolved: every remaining row would have to allow pets"),
    ])),
    ("st-cloud", OrderedDict([
        ("minimum_cohort", []),
        ("why", "PF 0, needs 5 of 7 unresolved; all 7 are DBPR-only motels/inns with no first-party route -- no legitimate "
                "cohort can change the decision in this pass, not worked"),
    ])),
])

WORKED_NOTES = {
    "thurston house": "discovery search found no first-party site (listed for sale); ROUTING_HOLD kept",
    "winter park sweet lodge": "discovery search found no first-party site (a third-party directory marks it closed; "
                               "not authoritative); ROUTING_HOLD kept",
    "crown motel": "route crownmotelorlando.com does not resolve (static NAVIGATION_FAILED again)",
    "park royal orlando": "route satisfactionorlandoresort.com does not resolve",
    "heritage park inn": "own site served, states no pet policy",
    "staymore extended studios": "route staymore.com serves a 114-byte shell; not a property page",
    "secrets hideaway": "route is a retired Ramada page; no current first-party route",
    "tropicana motel": "route points at another business (theinnatoakplantation.com); no current first-party route",
    "comfort inn and suites maingate south davenport": "route fla64 found by discovery search; Firecrawl UNEXPECTED_PAGE "
                                                       "(1 credit); supported browser served an Akamai bot check -- "
                                                       "choicehotels.com not retried",
    "rodeway inn davenport": "Firecrawl ACCESS_DENIED in pass 001 (no escalation); browser not attempted after the Akamai "
                             "bot check on choicehotels.com in this pass",
    "hilton orlando buena vista palace": "hotel-info redirects to /amenities/; the Pets policy panel is not exposed to the "
                                         "supported reader even when expanded",
    "hilton orlando lake buena vista": "hotel-info redirects to /amenities/; the Pets policy panel is not exposed to the "
                                       "supported reader even when expanded",
    "budget inn of apopka": "no first-party route; not worked (the corridor needs all four)",
    "home inn and suites": "no first-party route; not worked (the corridor needs all four)",
    "inn at overland": "no first-party route; not worked (the corridor needs all four)",
}


def _git(path):
    return json.loads(subprocess.run(["git", "show", "%s:atlas-dashboard/%s" % (BASE, path)], cwd=REPO,
                                     capture_output=True, check=True).stdout.decode("utf-8-sig"))


def _now(path):
    return json.load(open(os.path.join(_DASH, path), encoding="utf-8-sig"))


def _jsonl(name):
    p = os.path.join(_DASH, RAW + name)
    return [json.loads(l) for l in open(p, encoding="utf-8") if l.strip()] if os.path.exists(p) else []


def main():
    c0, c1 = _git(BASE_CENSUS), _now(CENSUS)
    p0 = {i["identity_key"]: i for i in _git(BASE_PARTITION)["items"]}
    p1 = {i["identity_key"]: i for i in _now(PARTITION)["items"]}
    h0 = {h["identity_key"]: h for h in c0["hotels"]}
    h1 = {h["identity_key"]: h for h in c1["hotels"]}
    by_code = {(h.get("brand"), (h.get("property_code") or "").lower()): k for k, h in h1.items() if h.get("property_code")}
    by_street = {}
    for k, h in h1.items():
        by_street.setdefault(h.get("street_identity") or "", []).append(k)

    def follow(k):
        if k in h1:
            return k
        h = h0.get(k) or {}
        code = (h.get("property_code") or "").lower()
        if code and (h.get("brand"), code) in by_code:
            return by_code[(h.get("brand"), code)]
        hits = by_street.get(h.get("street_identity") or "", [])
        return hits[0] if len(hits) == 1 else None

    def state(p, k):
        i = p.get(k) or {}
        return OrderedDict([("final_state", i.get("final_state")), ("disposition", i.get("disposition")),
                            ("resolved", bool(i.get("resolved")))])

    clean = _now(CLEAN)
    pf_rows = {r["identity_key"]: r for r in clean["clean_pet_friendly"]}
    np_rows = {r["identity_key"]: r for r in clean["clean_verified_no_pets"]}

    def evidence(k):
        r = pf_rows.get(k) or np_rows.get(k)
        if not r:
            return None
        return OrderedDict([("lane", r.get("lane")), ("brand", r.get("brand")), ("source_url", r.get("source_url")),
                            ("document_sha256", r.get("document_sha256")), ("quote", (r.get("quote") or "")[:400])])

    def track(k_now, k_before):
        i = p1.get(k_now) or {}
        rr = i.get("router_record") or {}
        h = h1.get(k_now) or {}
        ev = evidence(k_now)
        return OrderedDict([
            ("OWNED_ROUTE", "YES (owned Marriott harvest)" if any(e.get("lane") == "BRAND_INVENTORY_OWNED" for e in h.get("evidence", [])) else "NO"),
            ("STATIC_ATTEMPT", rr.get("static_attempt") or ("VALID (closure static lane)" if ev and ev["lane"] == "DIRECT_STATIC_FETCH" else "")),
            ("OFFICIAL_ROUTE", h.get("official_url") or rr.get("route") or ""),
            ("FIRECRAWL_ELIGIBLE", rr.get("firecrawl_eligible")), ("FIRECRAWL_ELIGIBILITY_REASON", rr.get("firecrawl_eligibility_reason")),
            ("FIRECRAWL_ATTEMPTED", rr.get("firecrawl_attempted")), ("FIRECRAWL_RESULT", rr.get("firecrawl_result")),
            ("OTHER_PROVIDER", rr.get("other_router_fallback") or "NONE (no new provider authorized; Bright Data / Places not used)"),
            ("BROWSER_RESULT", rr.get("supported_browser_result") or ("READ" if ev and ev["lane"] == "ATTENDED_BROWSER" else "")),
            ("FINAL_DISPOSITION", i.get("disposition")), ("EVIDENCE", ev),
            ("NOTE", WORKED_NOTES.get(k_before) or WORKED_NOTES.get(k_now) or ""),
        ])

    # ---- BringFido
    acc0 = _git(ACCOUNTING)
    names0 = {h["canonical_name"]: k for k, h in h0.items()}
    leads = [l for l in acc0["competitor_reconciliation"]["leads"] if l["class"] == "EXACT_ATLAS_MATCH"]
    bf_keys = []
    lead_names = {}
    for l in leads:
        k = names0.get(l["census_row"])
        if k and not p0.get(k, {}).get("resolved"):
            lead_names.setdefault(k, []).append(l["lead"])
            if k not in bf_keys:
                bf_keys.append(k)
    bf = []
    for k in sorted(bf_keys):
        kn = follow(k)
        bf.append(OrderedDict([("baseline_identity_key", k), ("current_identity_key", kn), ("bringfido_leads", lead_names[k]),
                               ("before", state(p0, k)), ("after", state(p1, kn) if kn else None),
                               ("router_track", track(kn, k) if kn else None)]))
    bf_after = Counter(("PF" if (x["after"] or {}).get("final_state") == "PUBLISHED_PET_FRIENDLY" else
                        "NP" if (x["after"] or {}).get("final_state") == "VERIFIED_NO_PETS" else "UNRESOLVED") for x in bf)

    # ---- V1 regression
    v1 = _git(V1DIAG)["v1_published_not_identically_published_in_v2"]
    v1r = []
    for x in v1:
        k = x["identity_key"]
        kn = follow(k)
        a = state(p1, kn) if kn else {}
        fs, disp = a.get("final_state"), a.get("disposition")
        verdict = ("VERIFIED PET-FRIENDLY" if fs == "PUBLISHED_PET_FRIENDLY" else "VERIFIED NO-PETS" if fs == "VERIFIED_NO_PETS"
                   else "ACCESS BLOCKED" if disp == "ACCESS_BLOCKED" else "IDENTITY CHANGE" if disp == "IDENTITY_HOLD"
                   else "INSUFFICIENT CURRENT EVIDENCE" if disp in ("EVIDENCE_HOLD", "SOURCE_SILENT", "POLICY_NOT_FOUND",
                                                                    "BROWSER_CAPTURE_NEEDED") else "OTHER HOLD")
        v1r.append(OrderedDict([("v1_identity_key", k), ("current_identity_key", kn), ("v1_state", x["v1"]),
                                ("baseline_v2_state", x["v2"]), ("closure_verdict", verdict), ("after", a),
                                ("v1_used_as_evidence", False), ("router_track", track(kn, k) if kn else None)]))

    # ---- Hilton / Marriott / Hyatt targeted browser reads
    hm = []
    for name, brand in (("hilton_browser_rows_closure.jsonl", "HILTON"), ("marriott_browser_rows_closure.jsonl", "MARRIOTT"),
                        ("hyatt_browser_rows_closure.jsonl", "HYATT")):
        for r in _jsonl(name):
            code = (r.get("c") or r["u"].split("/hotels/")[-1].split("-")[0]).lower()
            kn = by_code.get((brand, code))
            hm.append(OrderedDict([("brand", brand), ("property_code", code), ("url", r["u"]), ("browser_status", r["status"]),
                                   ("pet_nodes", r.get("pets") or r.get("pet")), ("current_identity_key", kn),
                                   ("after", state(p1, kn) if kn else None)]))
    hm_counts = OrderedDict()
    for brand in ("HILTON", "MARRIOTT", "HYATT"):
        rows = [x for x in hm if x["brand"] == brand]
        hm_counts[brand] = OrderedDict([
            ("targeted", len(rows)), ("browser_ok", sum(1 for x in rows if x["browser_status"] == "OK")),
            ("browser_blocked", sum(1 for x in rows if x["browser_status"] == "BLOCKED")),
            ("resolved_pet_friendly", sum(1 for x in rows if (x["after"] or {}).get("final_state") == "PUBLISHED_PET_FRIENDLY")),
            ("resolved_no_pets", sum(1 for x in rows if (x["after"] or {}).get("final_state") == "VERIFIED_NO_PETS")),
            ("still_unresolved", sum(1 for x in rows if not (x["after"] or {}).get("resolved")))])

    # ---- corridors
    def corridor_counts(census, part):
        out = {}
        for k, h in ((h["identity_key"], h) for h in census["hotels"]):
            c = (h.get("corridor") or "").split("__")[-1]
            s = (part.get(k) or {}).get("final_state")
            d = out.setdefault(c, Counter())
            d["census"] += 1
            d["pf"] += s == "PUBLISHED_PET_FRIENDLY"
            d["np"] += s == "VERIFIED_NO_PETS"
        return out
    cc0, cc1 = corridor_counts(c0, p0), corridor_counts(c1, p1)
    corr = OrderedDict()
    for c in sorted(cc1):
        corr[c] = OrderedDict([("pf_before", cc0.get(c, {}).get("pf", 0)), ("pf_after", cc1[c]["pf"]),
                               ("np_after", cc1[c]["np"]), ("census_after", cc1[c]["census"]),
                               ("publishes_before", cc0.get(c, {}).get("pf", 0) >= CORRIDOR_THRESHOLD),
                               ("publishes_after", cc1[c]["pf"] >= CORRIDOR_THRESHOLD)])
    corridor_critical = OrderedDict()
    for c, work in CORRIDOR_WORK.items():
        rows = []
        for k in work["minimum_cohort"]:
            kn = follow(k)
            rows.append(OrderedDict([("baseline_identity_key", k), ("current_identity_key", kn),
                                     ("before", state(p0, k)), ("after", state(p1, kn) if kn else None),
                                     ("router_track", track(kn, k) if kn else None)]))
        corridor_critical[c] = OrderedDict([("why", work["why"]), ("pf_before", corr[c]["pf_before"]),
                                            ("pf_after", corr[c]["pf_after"]), ("publishes_after", corr[c]["publishes_after"]),
                                            ("cohort", rows)])

    # ---- firecrawl this pass
    fc3 = _now(PKG + "/markets/reports/orlando_fl_v2_firecrawl_pass_003.json")

    def headline(census, part):
        st = Counter(i["final_state"] for i in part.values())
        res = sum(1 for i in part.values() if i.get("resolved"))
        n = census["count"]
        return OrderedDict([("census", n), ("pet_friendly", st["PUBLISHED_PET_FRIENDLY"]), ("no_pets", st["VERIFIED_NO_PETS"]),
                            ("resolved", res), ("unresolved", n - res), ("resolution_rate", round(res / n, 4))])

    disp1 = Counter(i["disposition"] for i in p1.values() if not i.get("resolved"))
    doc = OrderedDict([
        ("schema", "ptf-targeted-coverage-closure/1.0"), ("work_order", "PTF-ORLANDO-FL-V2-TARGETED-COVERAGE-CLOSURE-002"),
        ("market_id", "orlando-fl"), ("baseline_commit", BASE),
        ("headline", OrderedDict([("before", headline(c0, p0)), ("after", headline(c1, p1))])),
        ("census_change_explained", "583 = 582 + TownePlace Suites Orlando Airport (5530 Butler National Dr): its Marriott route "
                                    "mcota had been bound by name to TownePlace Suites Orlando Downtown (51 Columbia St); the "
                                    "Airport page's own address admitted the DBPR-licensed Airport building and the Downtown "
                                    "building now carries its own route (mcoto). Other key changes are renames to the name the "
                                    "property's own page states (same street identity)."),
        ("bringfido_closure", OrderedDict([
            ("identities_unresolved_at_baseline", len(bf)),
            ("leads_behind_them", sum(len(x["bringfido_leads"]) for x in bf)),
            ("resolved_this_pass", bf_after["PF"] + bf_after["NP"]), ("pet_friendly_found", bf_after["PF"]),
            ("verified_no_pets_found", bf_after["NP"]), ("still_unresolved", bf_after["UNRESOLVED"]),
            ("rows", bf)])),
        ("v1_regression_reconciliation", OrderedDict([
            ("rows_total", len(v1r)), ("by_verdict", OrderedDict(sorted(Counter(x["closure_verdict"] for x in v1r).items()))),
            ("rows", v1r)])),
        ("hilton_marriott_targeted", OrderedDict([("counts", hm_counts), ("rows", hm)])),
        ("corridors", corr),
        ("corridors_publishing", OrderedDict([("before", sum(1 for v in corr.values() if v["publishes_before"])),
                                              ("after", sum(1 for v in corr.values() if v["publishes_after"]))])),
        ("corridor_critical", corridor_critical),
        ("firecrawl_this_pass", OrderedDict([("attempts", len(fc3["rows"])),
                                             ("classes", OrderedDict(Counter(r.get("firecrawl_class") for r in fc3["rows"]))),
                                             ("credits", fc3.get("credits"))])),
        ("negation_conflicts", [OrderedDict([("name", (r.get("identity_signals") or {}).get("name_on_page")),
                                             ("classification", r["classification"]), ("quote", (r.get("quote") or "")[:300])])
                                for r in clean["rejected"] if r["classification"].startswith("NEGATION")
                                or r["classification"] == "QUOTE_CONTRADICTS_CLAIM"]),
        ("revised_unresolved_root_causes", OrderedDict(sorted(disp1.items()))),
    ])
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    print(json.dumps(doc["headline"]))
    print("bringfido", {k: v for k, v in doc["bringfido_closure"].items() if k != "rows"})
    print("v1", doc["v1_regression_reconciliation"]["by_verdict"])
    print("hm", json.dumps(hm_counts))
    print("corridors publishing", doc["corridors_publishing"], {c: (v["pf_before"], v["pf_after"]) for c, v in corridor_critical.items()})
    print("firecrawl", doc["firecrawl_this_pass"])
    print("negation", len(doc["negation_conflicts"]), "root causes", doc["revised_unresolved_root_causes"])


if __name__ == "__main__":
    main()
