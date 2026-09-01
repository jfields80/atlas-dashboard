"""PTF-CLEVELAND-AKRON-CANTON-HARDENED-APPLICATION-002 -- Phases 5, 7, 8, 9, 10, 11, 12, 13.

Build the Cleveland SHADOW state from the grouped rulings and the phase-4
identity reads:

  5   admit every CONFIRMED_TRUE_MISSING premises (first-party name, numbered
      street, postal; unique premises; no cross-market collision; in-market;
      lodging) to identity_census_admission/<market>.json -- a COPY of the
      pinned census with the Studio 6 supersession applied, the three
      non-lodging rows moved out of the hotel set, and the admitted rows
      appended; the pinned census is never touched
  7   PINNED vs SHADOW counts
  8   policy application inventory (LIVE and PROJECTED kept apart)
  9   routing / unresolved lanes after the reads
  10  live pricing: Bright Data balance (read-only snapshot passed in) and the
      measured ledger rate; Google Places from the public rate card, with the
      ledger state left UNPRICED_BY_LEDGER
  11  pilot plan (NOT executed)
  12  cumulative factory performance 001 + 002
  13  ONE small residual founder packet

No provider is called. Nothing is written to live authority.
"""
from __future__ import annotations

import argparse
import calendar
import copy
import glob
import hashlib
import json
import os
import re
import sys
import time
from collections import Counter, OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

from scripts.pettripfinder.contracts import census as CENSUS  # noqa: E402
from scripts.pettripfinder.contracts.identity_key import ptf_identity_key  # noqa: E402
from scripts.pettripfinder.markets.contract import slugify  # noqa: E402
from scripts.pettripfinder import cleveland_akron_canton_oh_paid_readiness_014 as PAID  # noqa: E402

WORK_ORDER = "PTF-CLEVELAND-AKRON-CANTON-HARDENED-APPLICATION-002"
PRIOR = "PTF-CLEVELAND-AKRON-CANTON-HARDENED-REVALIDATION-001"
MARKET_ID = "cleveland-akron-canton-oh"
M = MARKET_ID.replace("-", "_")
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
AUTH = os.path.join(PKG, "markets", "authority", MARKET_ID)
REPORTS = os.path.join(PKG, "markets", "reports")
ADMISSION = os.path.join(PKG, "identity_census_admission", f"{MARKET_ID}.json")
RULED_ON = "2026-09-01"
GOOGLE_RATE_CARD = OrderedDict([
    ("source", "https://developers.google.com/maps/billing-and-pricing/pricing (public rate card, read 2026-09-01; no API call made)"),
    ("text_search_pro_usd_per_1000", 32.00), ("text_search_pro_usd_per_request", 0.032),
    ("place_details_pro_usd_per_1000", 17.00), ("place_details_pro_usd_per_request", 0.017),
    ("note", "a websiteUri lookup is a Text Search Pro SKU; monthly free-tier credit may apply and is not assumed"),
])
ATTENDED_HOSTS = ("hilton.com", "marriott.com", "ihg.com", "choicehotels.com", "bestwestern.com", "radissonhotels", "redroof.com", "extendedstayamerica.com", "hyatt.com", "sonesta.com", "ritzcarlton.com")


def read_json(p):
    with open(p, "r", encoding="utf-8") as fh:
        return json.load(fh)


def write_json(p, d):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "wb") as fh:
        fh.write((json.dumps(d, indent=1, ensure_ascii=False, default=str) + "\n").encode("utf-8"))


def sha_file(p):
    return hashlib.sha256(open(p, "rb").read()).hexdigest() if os.path.exists(p) else None


def host_of(url):
    m = re.match(r"https?://([^/]+)", url or "")
    return m.group(1).lower().replace("www.", "") if m else ""


def house_number(addr):
    m = re.match(r"\s*(\d+)", addr or "")
    return m.group(1) if m else ""


def build(args):
    census_doc = read_json(os.path.join(PKG, "identity_census", f"{MARKET_ID}.json"))
    pinned = census_doc["hotels"]
    market = read_json(os.path.join(PKG, "markets", f"{MARKET_ID}.json"))
    postal_to_corridor = {pc: c["corridor_id"] for c in market["corridors"] for pc in (c.get("included_postal_codes") or [])}
    reads = read_json(os.path.join(REPORTS, f"{M}_identity_reads_002.json"))
    app = read_json(os.path.join(PKG, f"{M}_shadow_application_002.json"))
    rulings = read_json(os.path.join(REPORTS, f"{M}_application_rulings_002.json"))
    rebuild = read_json(os.path.join(REPORTS, f"{M}_unresolved_rebuild_007.json"))
    paid_prior = read_json(os.path.join(REPORTS, f"{M}_paid_readiness_014.json"))
    proj_prior = read_json(os.path.join(REPORTS, f"{M}_hardened_projection_013.json"))
    policy = {p["identity_key"]: p for p in read_json(os.path.join(PKG, f"hotel_policy_facts_{MARKET_ID}.json"))["hotels"]}
    excl = {ptf_identity_key(e["canonical_name"]): e for e in read_json(os.path.join(AUTH, "hotel_exclusions.json"))["exclusions"]}
    others = []
    for p in glob.glob(os.path.join(PKG, "identity_census", "*.json")):
        d = read_json(p)
        if isinstance(d, dict) and d.get("market_id") and d.get("market_id") != MARKET_ID:
            others += [(d["market_id"], h) for h in d.get("hotels", [])]

    # ---------------- phase 5: shadow census
    retired_keys = {r["identity_key"] for r in app["C_non_lodging_retirements"]}
    succ = app["B_successor_pet_friendly"]
    hotels = []
    supersessions = []
    for h in pinned:
        if h["identity_key"] in retired_keys:
            continue
        if h["identity_key"] == succ["predecessor"]["identity_key"] and succ["application_state"] == "SHADOW_PENDING_APPLICATION":
            row = copy.deepcopy(h)
            s = succ["successor"]
            row.update([("identity_key", s["identity_key"]), ("canonical_name", s["canonical_name"]), ("display_name", s["canonical_name"]), ("slug", s["slug"]),
                        ("address", s["address"]), ("city", s["city"]), ("postal_code", s["postal_code"]), ("phone", s["phone"]), ("official_url", s["official_url"]),
                        ("identity_state", "IDENTITY_CONFIRMED"), ("lodging_state", "LODGING_CONFIRMED"), ("has_official_link", True),
                        ("normalized_name", s["identity_key"]), ("raw_name", s["canonical_name"])])
            row["superseded_from"] = OrderedDict([("identity_key", h["identity_key"]), ("canonical_name", h["canonical_name"]), ("phone", h.get("phone")), ("official_url", h.get("official_url")),
                                                   ("provenance", h.get("provenance")), ("source", h.get("source")), ("ruling", "B"), ("work_order", WORK_ORDER),
                                                   ("resolution", "SAME_IDENTITY_REBRAND_SUCCESSOR"), ("binding", succ["binding"])])
            hotels.append(row)
            supersessions.append(OrderedDict([("from", h["identity_key"]), ("to", s["identity_key"]), ("property_code", s["property_code"])]))
            continue
        hotels.append(h)

    by_num = {}
    for h in hotels:
        n = house_number(h.get("address"))
        if n and h.get("postal_code"):
            by_num.setdefault((n, h["postal_code"][:5]), []).append(h["identity_key"])
    admitted, withheld = [], []
    for r in reads["classification"]:
        if r["classification"] != "CONFIRMED_TRUE_MISSING":
            continue
        pi = r["page_identity"]
        name = (pi.get("name") or r["name"]).strip()
        name = re.sub(r"\s*\|.*$", "", name)
        key = ptf_identity_key(name)
        num, pc = house_number(pi.get("street")), (pi.get("postal_code") or "")[:5]
        problems = []
        if r["admission"] != "ELIGIBLE_FOR_SHADOW_ADMISSION":
            problems.append(r["admission"])
        if any(k == key for k in (h["identity_key"] for h in hotels)) or any(a["identity_key"] == key for a in admitted):
            problems.append("DUPLICATE_IDENTITY_KEY")
        if (num, pc) in by_num or any(house_number(a["address"]) == num and a["postal_code"] == pc for a in admitted):
            problems.append("DUPLICATE_PREMISES")
        if any(house_number(h.get("address")) == num and (h.get("postal_code") or "")[:5] == pc for _, h in others):
            problems.append("CROSS_MARKET_COLLISION")
        if not (pc in postal_to_corridor or pc in {(h.get("postal_code") or "")[:5] for h in pinned}):
            problems.append("GEOGRAPHY_NOT_DECLARED")
        if problems:
            withheld.append(OrderedDict([("cohort_id", r["cohort_id"]), ("name", name), ("problems", problems)]))
            continue
        url = r["read"]["url"] or ""
        page_is_property = not any(t in url for t in ("/hotels/oh/cleveland", "find-hotels", "-hotels?brand", "-hotels"))
        row = OrderedDict([
            ("identity_key", key), ("canonical_name", name), ("display_name", name), ("slug", slugify(name)), ("market_id", MARKET_ID),
            ("address", pi.get("street") or ""), ("city", pi.get("locality") or r["premises_proposed"].get("city") or ""), ("state", "OH"), ("postal_code", pc),
            ("phone", pi.get("phone") or ""), ("identity_state", "IDENTITY_CONFIRMED"), ("lodging_state", "LODGING_BY_NAME"), ("policy_state", "POLICY_NOT_VERIFIED"),
            ("collision_state", "NONE"), ("official_url", url if page_is_property else ""), ("corridor", postal_to_corridor.get(pc, "")),
            ("assignment_basis", "postal_code" if postal_to_corridor.get(pc) else "unassigned"), ("assignment_value", pc if postal_to_corridor.get(pc) else ""),
            ("source", "first_party_page" if page_is_property else "first_party_brand_locator"), ("source_id", url), ("observed_at", (r["read"].get("read_at") or RULED_ON)[:10] if False else RULED_ON),
            ("provenance", WORK_ORDER + ":IDENTITY_READ:" + r["cohort_id"]), ("batch", "hardened-application-002"), ("has_official_link", bool(url if page_is_property else "")),
            ("normalized_name", key), ("raw_name", name), ("street_identity", "%s|%s" % ((pi.get("street") or "").lower(), pc)),
            ("admission", OrderedDict([("status", "SHADOW_ADMITTED_002"), ("ruling", "E"), ("classification", r["classification"]), ("read_method", r["read"]["method"]),
                                       ("evidence_url", url), ("document_sha256", r["read"].get("document_sha256")), ("artifact_file", r["read"].get("artifact_file")),
                                       ("property_code", pi.get("property_code")), ("premises_proposed_by", "openstreetmap" if r["cohort_id"] <= "TM-036" else "marriott_directory"),
                                       ("ruled_by", "PTF-FOUNDER-001"), ("ruled_on", RULED_ON), ("work_order", WORK_ORDER)])),
        ])
        if not row["city"]:
            row["city"] = next((h.get("city") for h in pinned if (h.get("postal_code") or "")[:5] == pc and h.get("city")), "")
        admitted.append(row)
        by_num.setdefault((num, pc), []).append(key)

    shadow = copy.deepcopy(census_doc)
    shadow["schema"] = census_doc["schema"]
    shadow["what_this_is"] = ("SHADOW admission census for %s (%s): the pinned %d rows with the Studio 6 -> Suburban Studios supersession applied (ruling B), the %d non-lodging rows moved to retired_non_lodging_002 (ruling C), and %d first-party-confirmed TRUE_MISSING premises admitted (ruling E). Never registered, never deployed; the pinned census, release contract and deployment manifest are untouched."
                              % (MARKET_ID, WORK_ORDER, len(pinned), len(retired_keys), len(admitted)))
    shadow["work_order"] = WORK_ORDER
    shadow["captured_at"] = RULED_ON
    shadow["hotels"] = hotels + admitted
    shadow["count"] = len(shadow["hotels"])
    shadow["retired_non_lodging_002"] = app["C_non_lodging_retirements"]
    shadow["supersessions_002"] = supersessions
    shadow["admission"] = OrderedDict([("pinned_census_touched", False), ("supersedes", OrderedDict([("work_order", census_doc.get("work_order")), ("count", len(pinned)), ("sha256", sha_file(os.path.join(PKG, "identity_census", f"{MARKET_ID}.json")))])),
                                       ("added", len(admitted)), ("retired", len(retired_keys)), ("superseded", len(supersessions)), ("withheld", withheld), ("policy_published_by_this_admission", 0), ("deployment", "NONE")])
    issues = [str(i) for i in CENSUS.validate(shadow, market_states=("OH",))]
    keys = [h["identity_key"] for h in shadow["hotels"]]
    dup_keys = sorted({k for k in keys if keys.count(k) > 1})

    # ---------------- phase 7: counts
    rc = reads["classification_counts"]
    state = OrderedDict([
        ("PINNED", OrderedDict([("census", len(pinned)), ("pet_friendly", len(policy)), ("verified_no_pets", len(excl)), ("resolved", len(policy) + len(excl)), ("unresolved", len(pinned) - len(policy) - len(excl))])),
        ("SHADOW", OrderedDict([("total_identities", shadow["count"]), ("deduplicated_identities", shadow["count"] - len(dup_keys)), ("confirmed_additions", len(admitted)), ("withheld_additions", len(withheld)),
                                ("retirements_non_lodging", len(retired_keys)), ("successors_applied", len(supersessions)), ("same_campus_pairs_recorded", app["counts"]["same_campus_resolutions"]),
                                ("geography_holds", sum(1 for r in reads["classification"] if r.get("admission") == "GEOGRAPHY_FOUNDER_HOLD")),
                                ("identity_reads", OrderedDict([("attempted", reads["reads_attempted"]), ("cohort", reads["cohort_size"]), ("classification", rc)])),
                                ("unresolved_identity_after_reads", rc.get("IDENTITY_UNRESOLVED", 0))])),
    ])

    # ---------------- phase 8: policy inventory
    pf_pending = [succ["successor"]["identity_key"]] if succ["application_state"] == "SHADOW_PENDING_APPLICATION" else []
    np_pending = [x["identity_key"] for x in app["A_clean_verified_no_pets"] if x["application_state"] == "SHADOW_PENDING_APPLICATION"]
    holds = [c["census_identity"] for c in app["phase_6_conversions"] if c["disposition"] == "FOUNDER_IDENTITY_HOLD"]
    holds = sorted(set(holds))
    silent = [r["identity_key"] for r in paid_prior["rows"] if r["lane"] == "SOURCE_SILENT"]
    policy_inv = OrderedDict([
        ("LIVE", OrderedDict([("pet_friendly", len(policy)), ("verified_no_pets", len(excl))])),
        ("PENDING_SHADOW", OrderedDict([("pet_friendly", pf_pending), ("verified_no_pets", np_pending), ("founder_holds", holds), ("source_silent", silent),
                                        ("newly_admitted_rows_without_policy", [a["identity_key"] for a in admitted])])),
        ("PROJECTED_IF_APPLIED", OrderedDict([("census", shadow["count"]), ("pet_friendly", len(policy) + len(pf_pending)), ("verified_no_pets", len(excl) + len(np_pending)),
                                              ("resolved", len(policy) + len(excl) + len(pf_pending) + len(np_pending)),
                                              ("unresolved", shadow["count"] - (len(policy) + len(excl) + len(pf_pending) + len(np_pending)))])),
        ("live_policy_package_written", False), ("live_exclusions_written", False),
    ])

    # ---------------- phase 9: lanes after the reads
    lanes = []
    prior_lane = {r["identity_key"]: r for r in paid_prior["rows"]}
    for r in rebuild["rows"]:
        k = r["identity_key"]
        pl = prior_lane.get(k, {})
        lane = pl.get("lane", r["lane"])
        if k in retired_keys:
            lane = "CLOSED_OR_CONVERTED"
        elif k in np_pending or k == succ["predecessor"]["identity_key"]:
            lane = "FREE_LANE_EXHAUSTED"
        elif k in holds:
            lane = "IDENTITY_REVIEW_FIRST"
        elif lane == "FREE_ATTENDED_QUALIFIED":
            lane = "FREE_ATTENDED"
        lanes.append(OrderedDict([("identity_key", k), ("canonical_name", r["canonical_name"]), ("brand_family", r["brand_family"]), ("lane", lane), ("prior_lane_014", pl.get("lane"))]))
    for a in admitted:
        h = host_of(a.get("official_url") or a["source_id"])
        lane = "FREE_ATTENDED" if any(x in h for x in ATTENDED_HOSTS) else ("FREE_STATIC" if a.get("official_url") else "FREE_ATTENDED")
        lanes.append(OrderedDict([("identity_key", a["identity_key"]), ("canonical_name", a["canonical_name"]), ("brand_family", "NEW"), ("lane", lane), ("prior_lane_014", None), ("note", "newly admitted; no policy read yet")]))
    lane_counts = OrderedDict(sorted(Counter(l["lane"] for l in lanes).items()))

    # ---------------- phase 10/11: pricing and the (unexecuted) pilot
    rates, brand_yield, discovery, market_ledger = PAID.measured_rates()
    bd_unit = rates["brightdata_browser"]["usd_per_billed_attempt"]
    bd_rows = [l for l in lanes if l["lane"] == "BRIGHTDATA_QUALIFIED"]
    disc_rows = [l for l in lanes if l["lane"] == "PAID_DISCOVERY_REQUIRED"]
    places_unit = GOOGLE_RATE_CARD["text_search_pro_usd_per_request"]
    pilot = OrderedDict([
        ("authorized", False), ("executed", False),
        ("bright_data", OrderedDict([("attempts", min(1, len(bd_rows))), ("unit_usd_measured_from_ledger", bd_unit), ("expected_usd", round(min(1, len(bd_rows)) * bd_unit, 2)),
                                     ("hard_cap_usd", round(min(1, len(bd_rows)) * bd_unit * 1.25, 2)), ("live_balance_usd", args.bd_balance_usd), ("live_pending_usd", args.bd_pending_usd),
                                     ("balance_sufficient", args.bd_balance_usd is not None and args.bd_balance_usd >= min(1, len(bd_rows)) * bd_unit * 1.25),
                                     ("rule", "cap against the live balance read BEFORE the run; the balance settles late and is not a cost meter; stop WHEN the cap is exceeded")])),
        ("google_places", OrderedDict([("lookups", min(10, len(disc_rows))), ("ledger_unit_price_state", discovery["unit_price_state"]),
                                       ("unit_usd_from_public_rate_card", places_unit), ("expected_usd_at_rate_card", round(min(10, len(disc_rows)) * places_unit, 2)),
                                       ("hard_cap_usd_at_rate_card", round(min(10, len(disc_rows)) * places_unit * 1.25, 2)), ("rate_card", GOOGLE_RATE_CARD),
                                       ("account", "Google Cloud billing account, separate from the Bright Data prepaid balance; no balance read is possible without a call"),
                                       ("expected_binds_at_measured_rate", round(min(10, len(disc_rows)) * (discovery["bind_rate_wilson_lower"] or 0), 1))])),
        ("account_balance_required_usd", OrderedDict([("bright_data", round(min(1, len(bd_rows)) * bd_unit * 1.25, 2)), ("google_places", round(min(10, len(disc_rows)) * places_unit * 1.25, 2))])),
    ])

    # ---------------- phase 12: cumulative factory performance
    t0 = calendar.timegm(time.strptime(args.started_at, "%Y-%m-%dT%H:%M:%SZ")) if args.started_at else None
    elapsed_002 = round((time.time() - t0) / 60.0, 1) if t0 else None
    a1 = proj_prior["phase_15_factory_assessment"]
    perf = OrderedDict([
        ("order_001", OrderedDict([("active_minutes", a1["active_elapsed_minutes"]), ("free_requests", a1["free_requests"]), ("evidence_reused", a1["evidence_artifacts_reused"]), ("routes_recovered", a1["routes_recovered"]),
                                   ("clean_outcomes", a1["clean_policy_outcomes"]), ("founder_decisions", a1["founder_decisions_required"]), ("generic_code_changes", a1["generic_code_changes_required"])])),
        ("order_002", OrderedDict([("active_minutes", elapsed_002), ("free_requests", reads["free_http_requests"] + args.browser_page_loads + 3), ("first_party_identity_reads", reads["reads_attempted"]),
                                   ("confirmed_true_missing", rc.get("CONFIRMED_TRUE_MISSING", 0)), ("shadow_admitted", len(admitted)), ("clean_outcomes_applied_to_shadow", OrderedDict([("pet_friendly", len(pf_pending)), ("verified_no_pets", len(np_pending))])),
                                   ("routes_recovered", 0), ("generic_code_changes", 0)])),
        ("cumulative", OrderedDict([("active_minutes", round((a1["active_elapsed_minutes"] or 0) + (elapsed_002 or 0), 1)), ("free_requests", a1["free_requests"] + reads["free_http_requests"] + args.browser_page_loads + 3),
                                    ("owned_evidence_reused", a1["evidence_artifacts_reused"]), ("first_party_identity_reads", reads["reads_attempted"]), ("routes_recovered", 0),
                                    ("confirmed_census_additions", len(admitted)), ("clean_policy_outcomes", OrderedDict([("pet_friendly", len(pf_pending)), ("verified_no_pets", len(np_pending))])),
                                    ("paid_provider_calls", 0), ("usd_spent", 0.0), ("generic_code_changes", 0)])),
    ])

    # ---------------- phase 13: residual packet
    residual = []

    def item(prop, key, issue, evidence, rec, cimp, aimp):
        residual.append(OrderedDict([("property", prop), ("identity_key", key), ("issue", issue), ("evidence", evidence), ("recommendation", rec), ("census_impact", cimp), ("authority_impact", aimp)]))

    for c in app["phase_6_conversions"]:
        if c["disposition"] == "FOUNDER_IDENTITY_HOLD" and c["census_identity"] == "cambria hotel and suites avon" and not any(x["identity_key"] == c["census_identity"] for x in residual):
            item("Cambria Hotel & Suites Avon -> Wyndham Avon", c["census_identity"], "owned page at the census premises (35600 Detroit Rd 44011) now brands the property Wyndham Avon and states pets allowed $100/stay, 2 pets; premises sit in the Avon geography hold",
                 OrderedDict([("artifact", c["artifact"]), ("sha256", c["artifact_sha256"]), ("page", c["page"])]), "RULE_SUCCESSOR (rename + apply PF) or HOLD with the Avon geography question", "rename 1 key", "+1 PF")
    for r in rulings["rows"]:
        if r["disposition"] == "REQUIRES_INDIVIDUAL_FOUNDER_RULING" and r["identity_key"] != "cambria hotel and suites avon":
            item(r["property"], r["identity_key"], r["why"], "census_audit_005 / routing_repair_001 traces", "rule the recorded proposal", "rename or none", "none now")
    same_campus = [x for x in residual if x["identity_key"] in ("motel 6 richfield", "residence inn cleveland beachwood")]
    item("Motel 6 Richfield vs Holiday Inn Express & Suites Cleveland-Richfield (5171 Brecksville Rd 44286)", "motel 6 richfield",
         "IHG's own search lists Holiday Inn Express & Suites Cleveland-Richfield ACTIVE at 5171 Brecksville Road, the census address of the LIVE PF Motel 6 Richfield row; the motel6.com page timed out on static re-read",
         "identity_reads_002 TM-033 IHG search list; live_audit_010", "READ the motel6.com page attended: same building (successor/predecessor) or two hotels on one lot; do not withdraw the live row without evidence", "possible +1 row or address supersession", "none until read")
    item("Red Roof Inn Akron (2939 S Arlington Rd)", ptf_identity_key("Red Roof Inn Akron"), "redroof.com page RRI207 states the street but its title says ZIP 44132 while OSM states 44312; JSON-LD carries no postal",
         "identity_reads_002 TM-005", "accept 44312 (44132 does not exist in Summit County) and admit, or hold", "+1 row if accepted", "none")
    item("Oakwood Village 44146: Hampton Inn & Suites Oakwood Village-Cleveland (23300 Oakwood Commons Dr) and Quality Inn & Suites Oakwood Village (23303 Oakwood Commons Dr)", "(geography)",
         "two first-party-confirmed hotels sit in postal 44146, which no corridor declares and no pinned row holds; classified OUTSIDE_MARKET by rule, not by intent (the east-side doctrine reaches Warrensville Heights / Solon)",
         "identity_reads_002 TM-019, TM-021", "declare 44146 in cleveland-east-beachwood or macedonia-twinsburg-northfield, or decline", "+2 rows if declared", "none")
    item("Brand-locator leads not in the cohort (no read spent)", "(leads)",
         "ESA Brooklyn 10300 Cascade Crossing 44144; ESA Select Mentor 5650 Emerald Ct 44060; ESA Select Airport 20829 Emerald Pkwy 44135; ESA Great Northern Mall 25801 Country Club Blvd 44070; ESA Middleburg Heights 17552 Rosbough Dr 44130; Comfort Inn Cleveland Airport 17550 Rosbough Dr 44130; Quality Inn Middleburg Heights 7233 Engle Rd 44130; MainStay Suites Middleburg Heights 7325 Engle Rd 44130; Candlewood Suites Cleveland South-Independence 6125 Rockside Pl 44131; Candlewood Suites Beachwood 3625 Orange Pl 44122; Staybridge Suites Mayfield Hts 6103 Landerhaven Dr 44124; Staybridge Suites Akron-Stow 4351 Steels Pointe Dr 44224",
         "identity_reads_002 TM-010, TM-027, TM-033 locator pages", "authorize one read each in a later order (12 leads) -- this order capped reads at the 36 + 6", "up to +12 rows", "none")
    packet = OrderedDict([("contract", "ptf-founder-review-packet/1.0"), ("work_order", WORK_ORDER), ("market_id", MARKET_ID), ("generated_at", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())),
                          ("nothing_was_spent", True), ("nothing_was_published", True), ("decisions_requested", len(residual)), ("items", residual)])

    ready_blockers = [
        "the shadow application (1 PF, 3 no-pets, 1 supersession, 3 retirements, 1 same-campus resolution) is not applied to live authority -- that is a deployment-bearing order",
        "the release contract pins census 188 / PF 99 / no-pets 40 and the deployment manifest pins the contract; promoting %d shadow rows needs a re-pin and a deployment" % shadow["count"],
        "%d admitted premises have no policy read yet (free static/attended lanes)" % len(admitted),
        "%d unresolved policy rows remain on pinned identities (%s)" % (policy_inv["PROJECTED_IF_APPLIED"]["unresolved"] - len(admitted), ", ".join("%s %d" % kv for kv in lane_counts.items() if kv[0] not in ("FREE_LANE_EXHAUSTED", "CLOSED_OR_CONVERTED"))),
        "%d residual founder decisions" % len(residual),
    ]
    state_doc = OrderedDict([
        ("schema", "ptf-shadow-state/1.0"), ("work_order", WORK_ORDER), ("prior_order", PRIOR), ("market_id", MARKET_ID), ("as_of", RULED_ON),
        ("provider_calls", 0), ("usd_spent", 0.0), ("live_authority_touched", False), ("pinned_census_touched", False), ("deployment", "NONE"),
        ("phase_5_shadow_admission", OrderedDict([("path", os.path.relpath(ADMISSION, _DASH)), ("count", shadow["count"]), ("admitted", len(admitted)), ("withheld", withheld), ("validation_issues", issues), ("duplicate_identity_keys", dup_keys),
                                                  ("admitted_rows", [OrderedDict([("identity_key", a["identity_key"]), ("address", a["address"]), ("postal_code", a["postal_code"]), ("corridor", a["corridor"]), ("source", a["source"])]) for a in admitted])])),
        ("phase_7_state", state), ("phase_8_policy_inventory", policy_inv),
        ("phase_9_lanes", OrderedDict([("counts", lane_counts), ("rows", lanes)])),
        ("phase_10_live_pricing", OrderedDict([("bright_data", OrderedDict([("balance_usd", args.bd_balance_usd), ("pending_usd", args.bd_pending_usd), ("month_to_date_usd_all_markets", args.bd_month_usd), ("read_at", args.bd_read_at),
                                                                              ("measured_usd_per_billed_attempt", bd_unit), ("publication_grade_rate", rates["brightdata_browser"]["publication_grade_rate"]), ("ledger_attempts", rates["brightdata_browser"]["attempts"])])),
                                               ("google_places", OrderedDict([("ledger_state", discovery["unit_price_state"]), ("rate_card", GOOGLE_RATE_CARD), ("ledger_bind_rate_wilson_lower", discovery["bind_rate_wilson_lower"])])),
                                               ("firecrawl", "not a lane for this cohort")])),
        ("phase_11_pilot_plan_not_executed", pilot), ("phase_12_factory_performance", perf),
        ("promotion_readiness", OrderedDict([("READY", False), ("blockers", ready_blockers),
                                             ("further_discovery_is_optional_coverage_expansion", "YES -- 48/48 cells, 9 brand families and every reachable first-party locator have been read; the remaining census signal is 12 brand-locator leads and 3 URL-less motels. The blocking work is policy acquisition and application, not discovery.")])),
        ("phase_13_residual_packet", OrderedDict([("path", os.path.relpath(os.path.join(PKG, f"{M}_residual_founder_packet_002.json"), _DASH)), ("decisions", len(residual))])),
    ])
    return shadow, state_doc, packet


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--started-at", default=None)
    ap.add_argument("--browser-page-loads", type=int, default=0)
    ap.add_argument("--bd-balance-usd", type=float, default=None)
    ap.add_argument("--bd-pending-usd", type=float, default=None)
    ap.add_argument("--bd-month-usd", type=float, default=None)
    ap.add_argument("--bd-read-at", default=None)
    args = ap.parse_args(argv)
    shadow, state, packet = build(args)
    write_json(ADMISSION, shadow)
    p2 = os.path.join(REPORTS, f"{M}_shadow_state_002.json")
    p3 = os.path.join(PKG, f"{M}_residual_founder_packet_002.json")
    write_json(p2, state)
    write_json(p3, packet)
    for p in (ADMISSION, p2, p3):
        print("written", os.path.relpath(p, _DASH))
    a = state["phase_5_shadow_admission"]
    print("shadow census", a["count"], "admitted", a["admitted"], "withheld", a["withheld"], "issues", a["validation_issues"], "dup keys", a["duplicate_identity_keys"])
    print("state", json.dumps(state["phase_7_state"]["SHADOW"], default=str)[:400])
    print("policy", json.dumps(state["phase_8_policy_inventory"]["PROJECTED_IF_APPLIED"]))
    print("lanes", dict(state["phase_9_lanes"]["counts"]))
    print("pilot", json.dumps(state["phase_11_pilot_plan_not_executed"]["account_balance_required_usd"]), "balance ok:", state["phase_11_pilot_plan_not_executed"]["bright_data"]["balance_sufficient"])
    print("residual decisions", packet["decisions_requested"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
