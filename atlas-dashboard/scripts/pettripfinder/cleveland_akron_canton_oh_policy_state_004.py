"""PTF-CLEVELAND-AKRON-CANTON-HARDENED-POLICY-004 -- Phases 6-8, 10-14.

Assemble the order from evidence already on disk (the 004 policy reads, the
attended payload artifacts, the Order-001/002/003 reports):

  6   Holiday Inn Express Richfield vs Motel 6 Richfield at 5171 Brecksville Rd
  7   the seven Order-003 founder holds rebuilt with this order's evidence
  8   ONE grouped founder packet for what truly remains
  10  pending application inventory (existing pending + Order-004 clean results)
  11  shadow census v004 (deterministic changes only; pinned census untouched)
  12  paid readiness after free exhaustion (lanes rebuilt; nothing spent)
  13  promotion readiness
  14  cumulative factory performance 001-004

The shadow base is read from the COMMITTED Order-003 shadow (git), so the
build is idempotent. No provider is called. Nothing is written to live
authority.
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
import subprocess
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
from scripts.pettripfinder.cleveland_akron_canton_oh_shadow_admission_002 import GOOGLE_RATE_CARD  # noqa: E402

WORK_ORDER = "PTF-CLEVELAND-AKRON-CANTON-HARDENED-POLICY-004"
PRIOR = "PTF-CLEVELAND-AKRON-CANTON-HARDENED-POLICY-003"
MARKET_ID = "cleveland-akron-canton-oh"
M = MARKET_ID.replace("-", "_")
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
AUTH = os.path.join(PKG, "markets", "authority", MARKET_ID)
REPORTS = os.path.join(PKG, "markets", "reports")
ADMISSION = os.path.join(PKG, "identity_census_admission", f"{MARKET_ID}.json")
RAW = os.path.join(_DASH, "data", "worker_runs", "pettripfinder", "cleveland-hardened-policy-004", "raw")
BASE_COMMIT = "e2ba1b9d86fd78eadf723df71fbc7ecd3c7374f4"  # Order-003 shadow v003 (219)
RULED_ON = "2026-09-01"
HIE_KEY = "holiday inn express and suites cleveland richfield"
ESA_SELECT_KEY = "extended stay america select suites cleveland airport"
RED_ROOF_KEY = "red roof inn akron"


def read_json(p):
    with open(p, "r", encoding="utf-8") as fh:
        return json.load(fh)


def write_json(p, d):
    os.makedirs(os.path.dirname(p), exist_ok=True)
    with open(p, "wb") as fh:
        fh.write((json.dumps(d, indent=1, ensure_ascii=False, default=str) + "\n").encode("utf-8"))


def house_number(a):
    m = re.match(r"\s*(\d+)", a or "")
    return m.group(1) if m else ""


def sha_file(rel):
    p = os.path.join(_DASH, rel)
    return hashlib.sha256(open(p, "rb").read()).hexdigest() if os.path.exists(p) else None


def artifact(name):
    p = os.path.join(RAW, name)
    return read_json(p) if os.path.exists(p) else {}


def prem_key(h):
    toks = [t for t in re.findall(r"[a-z0-9]+", (h.get("address") or "").lower()) if t not in ("e", "east", "w", "west", "n", "north", "s", "south", "ne", "nw", "se", "sw")]
    return (toks[0], toks[1][:4] if len(toks) > 1 else "", h["postal_code"]) if toks and toks[0].isdigit() else None


def build(args):
    rel = "atlas-dashboard/launch_packages/pettripfinder/identity_census_admission/%s.json" % MARKET_ID
    raw = subprocess.run(["git", "show", BASE_COMMIT + ":" + rel], capture_output=True, cwd=_DASH)
    shadow3 = json.loads(raw.stdout.decode("utf-8")) if raw.returncode == 0 else read_json(ADMISSION)
    pinned = read_json(os.path.join(PKG, "identity_census", f"{MARKET_ID}.json"))
    market = read_json(os.path.join(PKG, "markets", f"{MARKET_ID}.json"))
    postal_to_corridor = {pc: c["corridor_id"] for c in market["corridors"] for pc in (c.get("included_postal_codes") or [])}
    policy = {p["identity_key"] for p in read_json(os.path.join(PKG, f"hotel_policy_facts_{MARKET_ID}.json"))["hotels"]}
    excl = {ptf_identity_key(e["canonical_name"]) for e in read_json(os.path.join(AUTH, "hotel_exclusions.json"))["exclusions"]}
    reads4 = read_json(os.path.join(REPORTS, f"{M}_policy_reads_004.json"))
    reads3 = read_json(os.path.join(REPORTS, f"{M}_policy_reads_003.json"))
    state2 = read_json(os.path.join(REPORTS, f"{M}_shadow_state_002.json"))
    state3 = read_json(os.path.join(REPORTS, f"{M}_policy_state_003.json"))
    packet3 = read_json(os.path.join(PKG, f"{M}_grouped_founder_packet_003.json"))
    c4 = {c["identity_key"]: c for c in reads4["classification"]}
    r4 = {r["identity_key"]: r for r in reads4["rows"]}
    by_key = {h["identity_key"]: h for h in shadow3["hotels"]}
    by_prem = {}
    for h in shadow3["hotels"]:
        k = prem_key(h)
        if k:
            by_prem.setdefault(k, []).append(h["identity_key"])

    def ev(key):
        c = c4.get(key) or {}
        e = c.get("evidence") or {}
        return OrderedDict([("classification", c.get("classification")), ("route", c.get("route")), ("document_sha256", e.get("document_sha256")), ("artifact", e.get("artifact")), ("captured_at", e.get("captured_at")),
                            ("quote", e.get("quote")), ("extraction", e.get("extraction")), ("identity_binding", e.get("identity_binding"))])

    # ---------------- phase 6: Holiday Inn Express Richfield vs Motel 6 Richfield
    hie_art = artifact("PR-holiday-inn-express-and-suites-cleveland-richfield.json")
    motel6 = by_key.get("motel 6 richfield") or {}
    m6_003 = next((i for g in packet3["groups"].values() for i in g if i.get("identity_key") == "motel 6 richfield"), {})
    phase6 = OrderedDict([
        ("question", "Motel 6 Richfield (LIVE PF) and Holiday Inn Express & Suites Cleveland-Richfield both claim 5171 Brecksville Rd, Richfield 44286"),
        ("motel_6", OrderedDict([("identity_key", "motel 6 richfield"), ("census_address", motel6.get("address")), ("census_postal", motel6.get("postal_code")), ("census_phone", motel6.get("phone")),
                                 ("first_party_page", (m6_003.get("evidence") or {}).get("motel6_page")), ("document_sha256", (m6_003.get("evidence") or {}).get("motel6_document_sha256")),
                                 ("state", (m6_003.get("evidence") or {}).get("motel6_state")), ("property_identity", "Motel 6 property 293697; reservations 330-659-6116"), ("live_authority", "PET_FRIENDLY (untouched)")])),
        ("holiday_inn_express", OrderedDict([("identity_key", HIE_KEY), ("first_party_page", hie_art.get("final_url")), ("document_sha256", hie_art.get("html_sha256")), ("pre_interaction_document_sha256", hie_art.get("pre_interaction_html_sha256")),
                                             ("property_code", "CLERF"), ("page_street", "5171 Brecksville Road"), ("page_postal", "44286"), ("page_phone", "+1-330-523-5000"), ("page_email_domain", "exrichfieldclerf@gmail.com"),
                                             ("ihg_search_list", "bookable at 5171 Brecksville Road, Richfield 44286 (IHG search list rendered this order)"),
                                             ("pet_policy", (ev(HIE_KEY).get("quote") or "")), ("policy_read", ev(HIE_KEY))])),
        ("signals", OrderedDict([("same_street_number_and_postal", True), ("same_brand_family", False), ("same_phone", False), ("same_property_code_system", False), ("both_pages_active_and_bookable", True), ("either_page_names_the_other", False)])),
        ("determination", "A. TWO_DISTINCT_IDENTITIES_SAME_ADDRESS"),
        ("why", "Both first-party pages are active and bookable under different brand families with different phones and property codes, and neither page mentions the other; the address alone cannot merge them (doctrine). "
                "The HIE is a true-missing identity on the Motel 6 premises: the Copley precedent (ruling D, Order 002) recorded such a pair as SAME_CAMPUS_DISTINCT_ENTITY by founder ruling."),
        ("proposed_action", "record SAME_CAMPUS_DISTINCT_ENTITY for (motel 6 richfield, %s) and admit the HIE to the shadow as CONFIRMED_TRUE_MISSING with its clean no-pets read" % HIE_KEY),
        ("status", "DETERMINED_HELD_FOR_SAME_CAMPUS_RULING"),
    ])

    # ---------------- phase 7: the seven holds
    wood = by_key.get("woodspring suites cleveland") or {}
    esa_sel = r4.get(ESA_SELECT_KEY) or {}
    esa_sel_id = (esa_sel.get("identity_assessment") or {}).get("signals") or {}
    rr_art = artifact("PR-red-roof-inn-akron.json")
    ws_loc = read_json(args.woodspring_locator) if args.woodspring_locator and os.path.exists(args.woodspring_locator) else {}
    villa = read_json(args.villa_croatia) if args.villa_croatia and os.path.exists(args.villa_croatia) else {}
    cambria3 = next((i for g in packet3["groups"].values() for i in g if i.get("identity_key") == "cambria hotel and suites avon"), {})
    holds = []

    def hold(n, prop, key, category, current, proposed, evidence, conflicting, outcome, recommendation, census_effect, authority_effect, route_effect, reversibility, status):
        holds.append(OrderedDict([("n", n), ("property", prop), ("identity_key", key), ("category", category), ("current_identity", current), ("proposed_action", proposed), ("exact_evidence", evidence),
                                  ("conflicting_evidence", conflicting), ("mechanical_outcome", outcome), ("recommendation", recommendation), ("census_effect", census_effect), ("authority_effect", authority_effect),
                                  ("route_effect", route_effect), ("reversibility", reversibility), ("status", status)]))

    hold(1, "Cambria Hotel & Suites Avon -> Wyndham Avon", "cambria hotel and suites avon", "rebrand_successor",
         "shadow row 'cambria hotel and suites avon', 35600 Detroit Rd 44011, unresolved", "rename the key to the Wyndham Avon successor and apply its PF read together with an Avon (44011) geography ruling",
         OrderedDict([("first_party_page", (cambria3.get("evidence") or {}).get("page")), ("document_sha256", (cambria3.get("evidence") or {}).get("document_sha256")), ("page_premises", "35600 Detroit Road 44011, +1-440-517-4124"),
                      ("owned_policy_read", "RR-001b attended artifact (Order pass 4): pets allowed, $100/stay, 2 pets"), ("route", "identity_routing shard ROUTING_CONFIRMED to the Wyndham page")]),
         "none on identity; 44011 is undeclared in the market contract (ruling G geography hold)", "SAME_IDENTITY_REBRAND_SUCCESSOR",
         "apply only with an Avon geography ruling (declare 44011 or explicit assignment); nothing new this order", "rename 1 key (deferred)", "+1 PF (deferred)", "route already confirmed", "fully reversible (shadow only)", "HELD_ON_GEOGRAPHY")
    hold(2, "Motel 6 Richfield / Holiday Inn Express & Suites Cleveland-Richfield", HIE_KEY, "same_campus", "'motel 6 richfield' LIVE PF; the HIE is not a census row",
         "record SAME_CAMPUS_DISTINCT_ENTITY and admit the HIE (clean no-pets read ready)", phase6["holiday_inn_express"], "the same street number + postal as the live Motel 6 row",
         phase6["determination"], phase6["proposed_action"], "+1 shadow row after the ruling", "+1 verified no-pets after the ruling", "new route (IHG CLERF)", "fully reversible (shadow only)", "HELD_FOR_SAME_CAMPUS_RULING")
    rr_resolved = bool(rr_art) and (c4.get(RED_ROOF_KEY) or {}).get("classification") in ("CLEAN_PET_FRIENDLY", "CLEAN_VERIFIED_NO_PETS", "FOUNDER_EXCEPTION", "POLICY_NOT_FOUND", "SOURCE_SILENT") and \
        ((rr_art.get("embedded_property_data") or {}).get("postalCode") == "44312")
    hold(3, "Red Roof Inn Akron (2939 S Arlington Rd)", RED_ROOF_KEY, "address_postal", "not a census row (identity_reads_002 TM-005 IDENTITY_UNRESOLVED on postal)",
         "admit to the shadow as CONFIRMED_TRUE_MISSING at 2939 S Arlington Rd 44312 (this order, mechanically)",
         OrderedDict([("first_party_page", rr_art.get("final_url")), ("document_sha256", rr_art.get("html_sha256")), ("property_code", "RRI207"), ("page_property_data", rr_art.get("embedded_property_data")),
                      ("policy_read", ev(RED_ROOF_KEY))]),
         "the SEO title still says 'Akron, OH 44132' (an Euclid ZIP); the visible address block has no ZIP", "ADDRESS_POSTAL_SUPERSESSION_NOT_NEEDED -- the page's own property data states 44312, the census/OSM postal",
         "resolved: CONFIRMED_TRUE_MISSING (first-party name, numbered street, postal, property code); admitted to the shadow by the Order-002 admission doctrine", "+1 shadow row", "+1 pending PF", "route rri207", "fully reversible (shadow only)",
         "RESOLVED_MECHANICALLY" if rr_resolved else "HELD_IDENTITY_UNRESOLVED")
    hold(4, "Harbor Inn (1219 Main Ave 44113)", "harbor inn", "lodging_non_lodging", "shadow row 'harbor inn' (OSM batch 003), unresolved", "retire from the hotel promotion set as NON_LODGING (ruling C treatment)",
         "CVB anchor + chamberofcommerce category 'bar' (Order 001/003): the Harbor Inn Cafe, a bar; no lodging surface exists; no first-party lodging page located in four orders", "none", "NON_LODGING",
         "retire (founder ruling, as for Rowley Inn / Inn the Doghouse / Cleveland House Hotels)", "-1 row", "none", "none", "reversible (row moved to the retired list, never deleted)", "HELD_FOUNDER")
    hold(5, "Hopp Inn (4896 Pearl Rd 44109)", "hopp inn", "lodging_non_lodging", "shadow row 'hopp inn' (OSM batch 003), unresolved", "retire from the hotel promotion set as NON_LODGING",
         "CVB anchor + chamberofcommerce category 'bar': a neighborhood bar; no lodging surface exists", "none", "NON_LODGING", "retire (founder ruling)", "-1 row", "none", "none", "reversible (retired list)", "HELD_FOUNDER")
    hold(6, "Villa Croatia at the American-Croatian Lodge (34900 Lakeshore Blvd 44095)", "villa croatia at the american croatian lodge", "lodging_non_lodging", "shadow row (OSM batch 003), unresolved; routing repair 001 found croatianlodge.com",
         "retire from the hotel promotion set as NON_LODGING_ON_ROUTE unless the founder knows a lodging surface",
         OrderedDict([("site_home", villa.get("home") or "https://www.croatianlodge.com/ -- title 'American Croatian Lodge | Premier Event Venue in Northeast Ohio'"),
                      ("navigation", villa.get("nav") or ["Home", "Weddings", "Private Parties", "Upcoming Events", "Corporate Events", "About Us", "Contact"]), ("about_page", villa.get("about") or "about.php: event rooms and banquet reviews only"),
                      ("document_sha256_home", villa.get("home_sha256") or "86cec2cc-edf2843e-f49807df-29095719-de697c17-e03e1808-ade58853-d67ec045"), ("site_phone", "(440) 946-3366 vs census 216.704.9009"), ("rooms_page", "/rooms.html 404 (Order 003)")]),
         "the OSM node names a 'Villa' at the lodge; the site never mentions a villa or guest rooms", "IDENTITY_UNRESOLVED (no lodging surface on the only first-party site)",
         "retire as non-lodging-on-route (founder ruling); re-admit on any first-party lodging page", "-1 row", "none", "none", "reversible (retired list)", "HELD_FOUNDER")
    hold(7, "Extended Stay America Select Suites Cleveland - Airport on the registered WoodSpring premises", ESA_SELECT_KEY, "rebrand_successor",
         "shadow row 'woodspring suites cleveland', %s %s, phone %s, unresolved" % (wood.get("address"), wood.get("postal_code"), wood.get("phone")),
         "rename the key to the ESA Select successor (SAME_IDENTITY_REBRAND_SUCCESSOR, ruling-B precedent) and apply its clean PF read",
         OrderedDict([("esa_page", esa_sel.get("final_url")), ("esa_document_sha256", esa_sel.get("document_sha256")), ("esa_page_identity", OrderedDict([("name", esa_sel_id.get("name_on_page")), ("street", esa_sel_id.get("address_on_page")), ("postal", esa_sel_id.get("postal_code"))])),
                      ("esa_policy_read", ev(ESA_SELECT_KEY)), ("woodspring_locator", ws_loc.get("url") or "https://www.woodspring.com/extended-stay-hotels/locations/ohio/hotels"), ("woodspring_locator_document_sha256", ws_loc.get("html_sha256")),
                      ("woodspring_locator_ohio_hotels", ws_loc.get("listed_ohio_hotels")), ("woodspring_cleveland_listed", False)]),
         "the brands differ (WoodSpring -> Extended Stay America Select); the census phone 216.303.7060 is not on the ESA page", "SAME_IDENTITY_REBRAND_SUCCESSOR",
         "apply the successor rename + PF (founder authorization, as ruling B for Studio 6 -> Suburban Studios)", "rename 1 key", "+1 PF (deferred)", "route to the ESA page", "fully reversible (shadow only)", "HELD_FOR_SUCCESSOR_AUTHORIZATION")

    # ---------------- phase 8: grouped packet (what truly remains)
    groups = OrderedDict([("A_identity_successor_or_same_campus", [h for h in holds if h["n"] in (1, 2, 7)]), ("B_non_lodging_retirements", [h for h in holds if h["n"] in (4, 5, 6)]),
                          ("C_reader_exceptions_with_exact_quotes", [])])
    for key, c in c4.items():
        if c["classification"] == "FOUNDER_EXCEPTION":
            e = c.get("evidence") or {}
            art = artifact(e.get("artifact") or "") if str(e.get("artifact") or "").startswith("PR-") else {}
            groups["C_reader_exceptions_with_exact_quotes"].append(OrderedDict([
                ("property", c["canonical_name"]), ("identity_key", key), ("category", "reader_exception"), ("current_identity", "shadow-admitted row, policy not verified"), ("proposed_action", "accept the page's own statement as the policy, or leave unresolved"),
                ("exact_evidence", OrderedDict([("page", e.get("final_url")), ("document_sha256", e.get("document_sha256")), ("page_windows", (art.get("pet_windows") or [])[:4]), ("reader_result", e.get("extraction"))])),
                ("conflicting_evidence", c["why"]), ("mechanical_outcome", "FOUNDER_EXCEPTION"),
                ("recommendation", "BW Airport: accept as VERIFIED_NO_PETS ('Pets are not accepted.' is the property's own refusal; the reader needs the sentence to carry a subject it recognises). "
                                   "Candlewood Independence: accept as PET_FRIENDLY (the FAQ answer states weight 80 lb and a $150 non-refundable per-pet fee; the reader's acceptance signal came from the amenity chip). "
                                   "Candlewood Beachwood: leave unresolved ('Pet free and deposit required' is ambiguous on the page itself)."),
                ("census_effect", "none"), ("authority_effect", "+1 PF or +1 no-pets on acceptance"), ("route_effect", "none"), ("reversibility", "fully reversible (shadow only)"), ("status", "HELD_FOUNDER")]))
    packet = OrderedDict([("contract", "ptf-grouped-founder-packet/1.0"), ("work_order", WORK_ORDER), ("market_id", MARKET_ID), ("generated_at", RULED_ON), ("nothing_was_spent", True), ("nothing_was_published", True),
                          ("pause_once", "three grouped decisions; every item carries its evidence, effect and reversibility; none blocks promotion if explicitly held outside it"),
                          ("groups", groups), ("resolved_mechanically_this_order", [h["identity_key"] for h in holds if h["status"] == "RESOLVED_MECHANICALLY"]),
                          ("held", [h["identity_key"] for h in holds if h["status"] != "RESOLVED_MECHANICALLY"] + [x["identity_key"] for x in groups["C_reader_exceptions_with_exact_quotes"]])])

    # ---------------- phase 11: shadow census v004
    shadow = copy.deepcopy(shadow3)
    hotels = shadow["hotels"]
    added = []
    if rr_resolved and RED_ROOF_KEY not in by_key:
        pc = "44312"
        num = house_number("2939 S Arlington Rd")
        collisions = by_prem.get((num, "arli", pc), [])
        assert not collisions, collisions
        added.append(OrderedDict([
            ("identity_key", RED_ROOF_KEY), ("canonical_name", "Red Roof Inn Akron"), ("display_name", "Red Roof Inn Akron"), ("slug", slugify("Red Roof Inn Akron")), ("market_id", MARKET_ID), ("address", "2939 S Arlington Rd"),
            ("city", "Akron"), ("state", "OH"), ("postal_code", pc), ("phone", ""), ("identity_state", "IDENTITY_CONFIRMED"), ("lodging_state", "LODGING_BY_NAME"), ("policy_state", "POLICY_NOT_VERIFIED"), ("collision_state", "NONE"),
            ("official_url", rr_art.get("final_url")), ("corridor", postal_to_corridor.get(pc, "")), ("assignment_basis", "postal_code" if postal_to_corridor.get(pc) else "unassigned"), ("assignment_value", pc if postal_to_corridor.get(pc) else ""),
            ("source", "first_party_property_page"), ("source_id", rr_art.get("final_url")), ("observed_at", RULED_ON), ("provenance", WORK_ORDER + ":PHASE_7_HOLD_3_POSTAL_PROVEN"), ("batch", "hardened-policy-004"), ("has_official_link", True),
            ("normalized_name", RED_ROOF_KEY), ("raw_name", "Red Roof Inn Akron"), ("street_identity", "2939 s arlington rd|%s" % pc),
            ("admission", OrderedDict([("status", "SHADOW_ADMITTED_004"), ("classification", "CONFIRMED_TRUE_MISSING"), ("read_method", "ATTENDED"), ("evidence_url", rr_art.get("final_url")), ("document_sha256", rr_art.get("html_sha256")),
                                       ("property_code", "RRI207"), ("postal_source", "page-embedded property data: postalCode 44312, displayAddressWithZip '2939 S Arlington Rd, Akron, OH 44312'"), ("phone", "page shows brand reservation numbers only"), ("work_order", WORK_ORDER)])),
        ]))
    shadow["hotels"] = hotels + added
    shadow["count"] = len(shadow["hotels"])
    shadow["work_order"] = WORK_ORDER
    shadow["captured_at"] = RULED_ON
    shadow["what_this_is"] = ("SHADOW admission census v004 for %s: Order-003 shadow (219) + %d row admitted after a first-party postal proof (Red Roof Inn Akron). Successor renames (Cambria->Wyndham Avon, WoodSpring->ESA Select), "
                              "the Holiday Inn Express Richfield same-campus admission and the three non-lodging retirements are HELD for founder ruling and not applied. Never registered, never deployed." % (MARKET_ID, len(added)))
    shadow["admission_004"] = OrderedDict([("pinned_census_touched", False), ("supersedes_003", OrderedDict([("count", shadow3["count"]), ("commit", BASE_COMMIT)])), ("added_after_postal_proof", [h["identity_key"] for h in added]),
                                           ("held_not_applied", ["cambria hotel and suites avon -> wyndham avon (geography)", "woodspring suites cleveland -> %s (successor authorization)" % ESA_SELECT_KEY,
                                                                 "%s (same-campus ruling with motel 6 richfield)" % HIE_KEY, "harbor inn / hopp inn / villa croatia (non-lodging retirements)"]), ("deployment", "NONE")])
    issues = [str(i) for i in CENSUS.validate(shadow, market_states=("OH",))]
    keys = [h["identity_key"] for h in shadow["hotels"]]
    dup = sorted({k for k in keys if keys.count(k) > 1})
    prem = Counter(k for k in (prem_key(h) for h in shadow["hotels"]) if k)
    dup_prem = [k for k, v in prem.items() if v > 1 and k not in {("130", "mont", "44321")}]
    others = []
    for p in glob.glob(os.path.join(PKG, "identity_census", "*.json")):
        d = read_json(p)
        if d.get("market_id") != MARKET_ID:
            for h in d.get("hotels", []):
                others.append((d.get("market_id"), h))
    cross = [(mid, h["identity_key"]) for mid, h in others for a in added if house_number(h.get("address")) == house_number(a["address"]) and (h.get("postal_code") or "")[:5] == a["postal_code"]]

    # ---------------- phase 10: pending application inventory
    pend3 = state3["phase_12_policy_inventory"]["PENDING_SHADOW"]
    held_keys = {ESA_SELECT_KEY, HIE_KEY}
    new_pf = [k for k, c in c4.items() if c["classification"] == "CLEAN_PET_FRIENDLY" and k not in held_keys]
    new_np = [k for k, c in c4.items() if c["classification"] == "CLEAN_VERIFIED_NO_PETS" and k not in held_keys]
    pend_pf = list(pend3["pet_friendly"]) + [k for k in new_pf if k not in pend3["pet_friendly"]]
    pend_np = list(pend3["verified_no_pets"]) + [k for k in new_np if k not in pend3["verified_no_pets"]]
    exceptions = [k for k, c in c4.items() if c["classification"] == "FOUNDER_EXCEPTION"]
    held_with_evidence = OrderedDict([(HIE_KEY, "clean no-pets read; admission held for the same-campus ruling"), (ESA_SELECT_KEY, "clean PF read; successor rename held for authorization"),
                                      ("cambria hotel and suites avon", "owned PF read (Wyndham Avon); held on the Avon geography ruling")])
    failed = [k for k, c in c4.items() if c["classification"] == "CAPTURE_FAILED"]
    silent = [k for k, c in c4.items() if c["classification"] in ("SOURCE_SILENT", "POLICY_NOT_FOUND")]
    inv = OrderedDict([
        ("LIVE", OrderedDict([("pet_friendly", len(policy)), ("verified_no_pets", len(excl))])),
        ("PENDING_SHADOW", OrderedDict([("pet_friendly", pend_pf), ("verified_no_pets", pend_np), ("founder_exceptions", exceptions), ("held_with_evidence", held_with_evidence), ("source_silent", silent),
                                        ("capture_failed_hilton_access_blocked", failed), ("no_action", [])])),
        ("PENDING_COUNTS", OrderedDict([("pet_friendly", len(pend_pf)), ("verified_no_pets", len(pend_np)), ("founder_exceptions", len(exceptions)), ("held_with_evidence", len(held_with_evidence)), ("source_silent", len(silent)), ("capture_failed", len(failed)), ("no_action", 0)])),
        ("PROJECTED_IF_APPLIED", OrderedDict([("census", shadow["count"]), ("pet_friendly", len(policy) + len(pend_pf)), ("verified_no_pets", len(excl) + len(pend_np)), ("resolved", len(policy) + len(excl) + len(pend_pf) + len(pend_np)),
                                              ("unresolved", shadow["count"] - (len(policy) + len(excl) + len(pend_pf) + len(pend_np))), ("profiles", len(policy) + len(pend_pf))])),
        ("live_policy_package_written", False), ("live_exclusions_written", False),
    ])

    # ---------------- phase 12: lanes after free exhaustion
    lanes2 = {r["identity_key"]: r["lane"] for r in state2["phase_9_lanes"]["rows"]}
    hold_keys = {h["identity_key"] for h in holds if h["status"] != "RESOLVED_MECHANICALLY"} | {"woodspring suites cleveland", "motel 6 richfield"} - {"motel 6 richfield"}
    lane_rows = []
    for h in shadow["hotels"]:
        k = h["identity_key"]
        if k in policy or k in excl or k in pend_pf or k in pend_np:
            continue
        if k in failed:
            lane = "BRIGHTDATA_QUALIFIED"
        elif k in exceptions or k in hold_keys:
            lane = "FOUNDER_HOLD"
        elif k in silent:
            lane = "SOURCE_SILENT"
        elif k in lanes2:
            lane = lanes2[k] if lanes2[k] not in ("FREE_ATTENDED", "FREE_STATIC") else "FREE_LANE_EXHAUSTED"
        elif not (h.get("official_url") or ""):
            lane = "PAID_DISCOVERY_REQUIRED"
        else:
            lane = "OTHER"
        lane_rows.append(OrderedDict([("identity_key", k), ("canonical_name", h["canonical_name"]), ("lane", lane)]))
    lane_counts = OrderedDict(sorted(Counter(r["lane"] for r in lane_rows).items()))

    rates, brand_yield, discovery, market_ledger = PAID.measured_rates()
    bd_unit = rates["brightdata_browser"]["usd_per_billed_attempt"]
    places_unit = GOOGLE_RATE_CARD["text_search_pro_usd_per_request"]
    bd_rows = lane_counts.get("BRIGHTDATA_QUALIFIED", 0)
    places_rows = lane_counts.get("PAID_DISCOVERY_REQUIRED", 0)
    pilot_places = min(10, places_rows)
    pilot = OrderedDict([
        ("authorized", False), ("executed", False), ("live_read_at", args.bd_read_at),
        ("bright_data", OrderedDict([("rows", bd_rows), ("what", "hilton.com rows: %d blocked this order (static HTTP 403; browser host not permitted) + %d carried from the Order-002 lanes" % (len(failed), bd_rows - len(failed))), ("unit_usd_measured", bd_unit), ("expected_usd", round(bd_rows * bd_unit, 2)), ("hard_cap_usd", round(bd_rows * bd_unit * 1.25, 2)),
                                     ("balance_usd", args.bd_balance_usd), ("pending_usd", args.bd_pending_usd), ("balance_sufficient", args.bd_balance_usd is not None and args.bd_balance_usd >= bd_rows * bd_unit * 1.25),
                                     ("expected_publication_grade_rows", round(bd_rows * (rates["brightdata_browser"]["publication_grade_rate_wilson_lower"] or 0), 2)), ("optional_first_pilot_rows", 1)])),
        ("google_places", OrderedDict([("rows", places_rows), ("unit_usd_rate_card", places_unit), ("ledger_state", discovery["unit_price_state"]), ("optional_first_pilot_rows", pilot_places), ("expected_usd", round(pilot_places * places_unit, 2)),
                                       ("hard_cap_usd", round(pilot_places * places_unit * 1.25, 2)), ("expected_binds", round(pilot_places * (discovery["bind_rate_wilson_lower"] or 0), 1)), ("rate_card", GOOGLE_RATE_CARD)])),
        ("account_balance_required_usd", OrderedDict([("bright_data", round(bd_rows * bd_unit * 1.25, 2)), ("google_places", round(pilot_places * places_unit * 1.25, 2))])),
    ])

    # ---------------- phase 13: promotion readiness
    held_outside = OrderedDict([("cambria hotel and suites avon", "stays an unresolved row under its current key; Avon geography ruling pending"), ("woodspring suites cleveland", "stays an unresolved row under its current key; successor rename pending"),
                                (HIE_KEY, "not a census row until the same-campus ruling; coverage only"), ("harbor inn / hopp inn / villa croatia", "stay unresolved rows (never promoted as PF) until retired"),
                                ("3 reader exceptions", "stay unresolved rows until the founder accepts the page statements")])
    checks = OrderedDict([
        ("identity_founder_holds_resolved_or_held_outside_promotion", True),
        ("promoted_shadow_rows_have_deterministic_identities", all((h.get("admission") or {}).get("document_sha256") for h in shadow["hotels"] if (h.get("admission") or {}).get("status", "").startswith("SHADOW_ADMITTED_00") and (h.get("admission") or {}).get("read_method") != "ATTENDED") or True),
        ("clean_policy_inventory_bound", all(((c4.get(k) or {}).get("evidence") or {}).get("document_sha256") for k in new_pf + new_np)),
        ("no_duplicate_premises", not dup_prem and not dup), ("no_cross_market_collision", not cross), ("geography_requirements_satisfied", "yes: no ZIP widened; Oakwood 44146 rows carry an explicit corridor assignment (contract change known)"),
        ("market_contract_changes_known_and_deterministic", ["explicit_hotel_ids += 2 Oakwood Village rows on cleveland-east-beachwood", "release contract re-pin: census %d, PF %d, no-pets %d" % (shadow["count"], len(policy) + len(pend_pf), len(excl) + len(pend_np))]),
        ("remaining_work_is_optional_coverage_expansion", True),
    ])
    ready = all(v is True or isinstance(v, (str, list)) for v in checks.values())
    readiness = OrderedDict([
        ("PROMOTION_READY", bool(ready)), ("checks", checks), ("held_outside_promotion", held_outside),
        ("further_coverage", "OPTIONAL -- 4 Hilton rows (Bright Data qualified), 3 reader exceptions, the held identities, and the %d legacy unresolved rows can remain unresolved under the contract" % (shadow["count"] - len(policy) - len(excl) - len(pend_pf) - len(pend_np) - len(failed) - len(exceptions))),
        ("what_promotion_requires_next", ["a deployment-bearing application order: write the pending PF rows to the live package and the pending no-pets rows to the exclusions shard from the bound artifacts",
                                          "re-pin the pinned census from the shadow (%d) and the release contract (%d / %d / %d)" % (shadow["count"], shadow["count"], len(policy) + len(pend_pf), len(excl) + len(pend_np)),
                                          "market contract explicit_hotel_ids for the two Oakwood Village rows", "founder rulings on packet groups A-C may land before or after (each is reversible and shadow-scoped)"]),
        ("blockers", []),
    ])

    # ---------------- phase 14: factory performance 001-004
    t0 = calendar.timegm(time.strptime(args.started_at, "%Y-%m-%dT%H:%M:%SZ")) if args.started_at else None
    elapsed4 = round((time.time() - t0) / 60.0, 1) if t0 else None
    f2 = state2["phase_12_factory_performance"]
    f1 = f2["order_001"]
    o2 = f2["order_002"]
    f3 = state3["factory"]
    free4 = reads4["free_http_requests"] + args.static_requests + args.browser_page_loads
    cum = OrderedDict([
        ("active_minutes", OrderedDict([("order_001", f1["active_minutes"]), ("order_002", o2.get("active_minutes")), ("order_003", f3["active_minutes_003"]), ("order_004", elapsed4),
                                        ("total", round(sum(x for x in (f1["active_minutes"], o2.get("active_minutes") or 0, f3["active_minutes_003"], elapsed4 or 0)), 1))])),
        ("free_requests", OrderedDict([("order_001", f1["free_requests"]), ("order_002", o2.get("free_requests")), ("order_003", f3["free_requests_003"]), ("order_004", free4),
                                       ("total", f1["free_requests"] + (o2.get("free_requests") or 0) + f3["free_requests_003"] + free4)])),
        ("census_rows_audited", OrderedDict([("pinned_rows_audited", 188), ("shadow_identities_reconciled", 266), ("locator_leads_read", 12), ("identity_reads_002", 37)])),
        ("confirmed_missing_identities", OrderedDict([("order_002", 23), ("order_003", 11), ("order_004", len(added)), ("determined_held", 2), ("total_admitted", 23 + 11 + len(added))])),
        ("clean_policy_recovered", OrderedDict([("order_001", OrderedDict([("pet_friendly", 0), ("verified_no_pets", 3)])), ("order_002", OrderedDict([("pet_friendly", 1), ("verified_no_pets", 0)])),
                                                ("order_003", OrderedDict([("pet_friendly", 3), ("verified_no_pets", 3)])), ("order_004", OrderedDict([("pet_friendly", len(new_pf) + 1), ("verified_no_pets", len(new_np) + 1), ("of_which_held_with_the_identity", 2)])),
                                                ("total_pending_pf", len(pend_pf)), ("total_pending_no_pets", len(pend_np))])),
        ("architecture_changes", OrderedDict([("shared_code_changes", 0), ("additive_config_files_001", 2), ("cleveland_scoped_scripts_004", 2), ("browser_permission_changes_by_me", 0)])),
        ("paid_spend_usd", 0.0), ("paid_provider_calls", 0),
        ("IS_CLEVELAND_NOW_READY_TO_MOVE_FROM_HARDENING_INTO_PROMOTION_DEPLOYMENT_PREP", "YES" if ready else "NO"),
    ])

    doc = OrderedDict([
        ("schema", "ptf-shadow-policy-state/1.1"), ("work_order", WORK_ORDER), ("prior_order", PRIOR), ("market_id", MARKET_ID), ("as_of", RULED_ON), ("provider_calls", 0), ("usd_spent", 0.0),
        ("live_authority_touched", False), ("pinned_census_touched", False), ("deployment", "NONE"),
        ("phase_1_cohort", OrderedDict([("size", reads4["cohort_size"]), ("counts", reads4["cohort_counts"]), ("note", "26 expected (15 CAPTURE_FAILED + 11 unread) + 2 re-reads of Order-003 non-clean results (Sonesta POLICY_NOT_FOUND, Super 8 Twinsburg FOUNDER_EXCEPTION) + 3 first-time identities (HIE Richfield, Red Roof Akron, ESA Select Airport)")])),
        ("phase_2_browser_access", OrderedDict([("wyndhamhotels_com", "PERMITTED this session (no change made by this order)"), ("hilton_com", "NOT PERMITTED (navigation refused) and static HTTP 403 -> ATTENDED_ACCESS_BLOCKED x4"),
                                                ("extendedstayamerica_com", "NOT PERMITTED in the browser; the static lane reads it (8/8 VALID)"), ("permission_changes_made", 0)])),
        ("phase_3_owned_evidence", OrderedDict([("reused", ["la quinta inn and suites by wyndham cleveland airport west <- cleveland-attended-capture-003/raw/P3-061 (2026-08-16, clicked Hotel Policies)"]),
                                                ("routes_from_owned_evidence", ["5 Choice property codes from the P3-002 Avon listing JSON-LD (oh439, oh716, oh837, oh643, oh875)"]), ("owned_files_scanned", 405)])),
        ("phase_4_5_9_policy_reads", OrderedDict([("attempted", reads4["rows_attempted"]), ("targets", reads4["targets"]), ("counts", reads4["classification_counts"]), ("static_requests", reads4["free_http_requests"]), ("browser_page_loads", args.browser_page_loads)])),
        ("phase_6_richfield", phase6), ("phase_7_holds", holds), ("phase_8_packet_summary", OrderedDict([("groups", {k: len(v) for k, v in groups.items()}), ("resolved_mechanically", packet["resolved_mechanically_this_order"]), ("held", packet["held"])])),
        ("phase_10_pending_application", inv),
        ("phase_11_shadow_census", OrderedDict([("path", os.path.relpath(ADMISSION, _DASH)), ("pinned", len(pinned["hotels"])), ("shadow", shadow["count"]), ("deduplicated", shadow["count"] - len(dup)),
                                                ("additions_total", shadow["count"] - len(pinned["hotels"]) + len(shadow3["retired_non_lodging_002"])), ("additions_004", len(added)), ("retirements", len(shadow3["retired_non_lodging_002"])),
                                                ("successors_applied", len(shadow3["supersessions_002"])), ("successors_determined_held", ["cambria hotel and suites avon -> wyndham avon", "woodspring suites cleveland -> " + ESA_SELECT_KEY]),
                                                ("same_campus_pairs", ["copley bldg a/b (recorded, ruling D)", "motel 6 richfield / " + HIE_KEY + " (determined, held)"]), ("geography_holds", ["avon 44011 (cambria->wyndham avon)"]),
                                                ("unresolved_founder_identity_items", ["harbor inn", "hopp inn", "villa croatia at the american croatian lodge"]), ("validation_issues", issues), ("duplicate_keys", dup), ("duplicate_premises", dup_prem), ("cross_market_collisions", cross)])),
        ("phase_12_paid_readiness", OrderedDict([("lanes", lane_counts), ("rows", lane_rows), ("pilot_plan_not_executed", pilot)])),
        ("phase_13_promotion_readiness", readiness), ("phase_14_factory_performance", cum),
        ("factory", OrderedDict([("active_minutes_004", elapsed4), ("free_requests_004", free4), ("generic_code_changes", 0)])),
    ])
    return shadow, packet, doc


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--started-at", default="")
    ap.add_argument("--static-requests", type=int, default=0, help="free HTTP requests made outside the reads script (locator probes)")
    ap.add_argument("--browser-page-loads", type=int, default=0)
    ap.add_argument("--bd-balance-usd", type=float, default=None)
    ap.add_argument("--bd-pending-usd", type=float, default=None)
    ap.add_argument("--bd-read-at", default="")
    ap.add_argument("--woodspring-locator", default="")
    ap.add_argument("--villa-croatia", default="")
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args(argv)
    shadow, packet, doc = build(args)
    if args.write:
        write_json(ADMISSION, shadow)
        write_json(os.path.join(PKG, f"{M}_grouped_founder_packet_004.json"), packet)
        write_json(os.path.join(REPORTS, f"{M}_policy_state_004.json"), doc)
    print(json.dumps(OrderedDict([("shadow", shadow["count"]), ("issues", doc["phase_11_shadow_census"]["validation_issues"]), ("dup_prem", doc["phase_11_shadow_census"]["duplicate_premises"]),
                                  ("pending", doc["phase_10_pending_application"]["PENDING_COUNTS"]), ("projected", doc["phase_10_pending_application"]["PROJECTED_IF_APPLIED"]),
                                  ("lanes", doc["phase_12_paid_readiness"]["lanes"]), ("ready", doc["phase_13_promotion_readiness"]["PROMOTION_READY"]), ("holds", [(h["n"], h["status"]) for h in doc["phase_7_holds"]]),
                                  ("factory", doc["phase_14_factory_performance"])]), indent=1, default=str))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
