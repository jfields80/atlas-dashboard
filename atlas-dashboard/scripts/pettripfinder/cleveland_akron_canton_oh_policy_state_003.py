"""PTF-CLEVELAND-AKRON-CANTON-HARDENED-POLICY-003 -- Phases 1-9, 12-15.

Assemble the order from evidence already on disk (static reads, attended
payloads, the Order-001/002 artifacts):

  1   the 14 residual items rebuilt and grouped A-F
  2   Cambria -> Wyndham Avon: current first-party page vs census premises
  3   Motel 6 Richfield: current first-party page (active) vs IHG inventory
  4   Red Roof Akron: postal reconciliation
  5   Oakwood Village 44146: market intent, explicit assignment
  6   Westin / TownePlace Solon: full-name overlays, identity keys preserved
  7   the five routing-repair-001 traces
  8   Kent State: lodging, in market
  9   the 12 brand-locator leads, read from the locator pages already captured
  12  shadow policy application inventory (LIVE vs PROJECTED)
  13  shadow census v003 (identity_census_admission, rebuilt deterministically)
  14  paid pilot plan (not executed)
  15  promotion readiness

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
from scripts.pettripfinder.cleveland_akron_canton_oh_shadow_admission_002 import GOOGLE_RATE_CARD  # noqa: E402

WORK_ORDER = "PTF-CLEVELAND-AKRON-CANTON-HARDENED-POLICY-003"
MARKET_ID = "cleveland-akron-canton-oh"
M = MARKET_ID.replace("-", "_")
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
AUTH = os.path.join(PKG, "markets", "authority", MARKET_ID)
REPORTS = os.path.join(PKG, "markets", "reports")
ADMISSION = os.path.join(PKG, "identity_census_admission", f"{MARKET_ID}.json")
RULED_ON = "2026-09-01"
EAST = "cleveland-akron-canton-oh__cleveland-east-beachwood"

# Static identity reads made by this order (scratch file copied into the report; sha256 of the served document).
STATIC_003 = json.load(open(os.path.join(os.environ.get("PTF_SCRATCH", ""), "static_003.json"), encoding="utf-8")) if os.environ.get("PTF_SCRATCH") and os.path.exists(os.path.join(os.environ.get("PTF_SCRATCH", ""), "static_003.json")) else {}

# 12 brand-locator leads (Order 002 locator pages; first-party name + street + postal); the locator document sha256 is the evidence.
LEADS = [
    ("Extended Stay America Suites Cleveland - Brooklyn", "10300 Cascade Crossing", "Brooklyn", "44144", "ESA", "https://www.extendedstayamerica.com/hotels/oh/cleveland", "b5fa977a85db053b4a63459be2a50541149eac6978dc14bcb5aab3c42c97796e"),
    ("Extended Stay America Select Suites Cleveland - Mentor", "5650 Emerald Ct", "Mentor", "44060", "ESA", "https://www.extendedstayamerica.com/hotels/oh/cleveland", "b5fa977a85db053b4a63459be2a50541149eac6978dc14bcb5aab3c42c97796e"),
    ("Extended Stay America Select Suites Cleveland - Airport", "20829 Emerald Pkwy", "Cleveland", "44135", "ESA", "https://www.extendedstayamerica.com/hotels/oh/cleveland", "b5fa977a85db053b4a63459be2a50541149eac6978dc14bcb5aab3c42c97796e"),
    ("Extended Stay America Suites Cleveland - Great Northern Mall", "25801 Country Club Blvd.", "North Olmsted", "44070", "ESA", "https://www.extendedstayamerica.com/hotels/oh/cleveland", "b5fa977a85db053b4a63459be2a50541149eac6978dc14bcb5aab3c42c97796e"),
    ("Extended Stay America Suites Cleveland - Middleburg Heights", "17552 Rosbough Dr.", "Middleburg Heights", "44130", "ESA", "https://www.extendedstayamerica.com/hotels/oh/cleveland", "b5fa977a85db053b4a63459be2a50541149eac6978dc14bcb5aab3c42c97796e"),
    ("Comfort Inn Cleveland Airport", "17550 Rosbough Dr.", "Middleburg Heights", "44130", "CHOICE", "https://www.choicehotels.com/ohio/north-olmsted/radisson-hotels?brand=RD", "bcecc6d6ba6c8a1c6c206af4c32396842ddf182928f0ff2ff6298d4b461c55f6"),
    ("Quality Inn Middleburg Heights near Cleveland Airport", "7233 Engle Road", "Middleburg Heights", "44130", "CHOICE", "https://www.choicehotels.com/ohio/north-olmsted/radisson-hotels?brand=RD", "bcecc6d6ba6c8a1c6c206af4c32396842ddf182928f0ff2ff6298d4b461c55f6"),
    ("MainStay Suites Middleburg Heights Cleveland Airport", "7325 Engle Rd", "Middleburg Heights", "44130", "CHOICE", "https://www.choicehotels.com/ohio/north-olmsted/radisson-hotels?brand=RD", "bcecc6d6ba6c8a1c6c206af4c32396842ddf182928f0ff2ff6298d4b461c55f6"),
    ("Candlewood Suites Cleveland South - Independence", "6125 Rockside Place", "Independence", "44131", "IHG", "https://www.ihg.com/hotels/us/en/find-hotels/hotel-search?qDest=Independence,%20OH", None),
    ("Candlewood Suites Beachwood - Cleveland", "3625 Orange Place", "Beachwood", "44122", "IHG", "https://www.ihg.com/hotels/us/en/find-hotels/hotel-search?qDest=Independence,%20OH", None),
    ("Staybridge Suites Cleveland Mayfield Hts Beachwd", "6103 Landerhaven Drive", "Mayfield Heights", "44124", "IHG", "https://www.ihg.com/hotels/us/en/find-hotels/hotel-search?qDest=Independence,%20OH", None),
    ("Staybridge Suites Akron-Stow-Cuyahoga Falls", "4351 Steels Pointe Drive", "Stow", "44224", "IHG", "https://www.ihg.com/hotels/us/en/find-hotels/hotel-search?qDest=Independence,%20OH", None),
]
OAKWOOD = [
    ("Hampton Inn & Suites Oakwood Village-Cleveland", "23300 Oakwood Commons Drive", "Oakwood Village", "44146", "+1 440-945-6291", "https://www.hilton.com/en/hotels/cleovhx-hampton-suites-oakwood-village-cleveland/", "CLEOVHX", "ef3a7757c35a4c4365ee339fac6a7cbca9088598826f92f8991bfb60114bec04"),
    ("Quality Inn & Suites Oakwood Village - Cleveland South", "23303 Oakwood Commons Drive", "Oakwood Village", "44146", "", "", "", "83b02bb08ade196c33aa3cfcecd864e69edfb482db525e88acc01d40c390583b"),
]


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


def build(args):
    # Rebuild from the COMMITTED Order-002 shadow every time (idempotent); the file on disk may already carry this order's additions.
    import subprocess
    rel = "atlas-dashboard/launch_packages/pettripfinder/identity_census_admission/%s.json" % MARKET_ID
    raw = subprocess.run(["git", "show", "e5dfab33f8f856adf10b10ce6eded670e6348800:" + rel], capture_output=True, cwd=_DASH)
    shadow2 = json.loads(raw.stdout.decode("utf-8")) if raw.returncode == 0 else read_json(ADMISSION)
    pinned = read_json(os.path.join(PKG, "identity_census", f"{MARKET_ID}.json"))
    market = read_json(os.path.join(PKG, "markets", f"{MARKET_ID}.json"))
    postal_to_corridor = {pc: c["corridor_id"] for c in market["corridors"] for pc in (c.get("included_postal_codes") or [])}
    policy = {p["identity_key"] for p in read_json(os.path.join(PKG, f"hotel_policy_facts_{MARKET_ID}.json"))["hotels"]}
    excl = {ptf_identity_key(e["canonical_name"]) for e in read_json(os.path.join(AUTH, "hotel_exclusions.json"))["exclusions"]}
    app2 = read_json(os.path.join(PKG, f"{M}_shadow_application_002.json"))
    reads = read_json(os.path.join(REPORTS, f"{M}_policy_reads_003.json"))
    state2 = read_json(os.path.join(REPORTS, f"{M}_shadow_state_002.json"))
    residual2 = read_json(os.path.join(PKG, f"{M}_residual_founder_packet_002.json"))
    static = read_json(args.static_reads) if args.static_reads and os.path.exists(args.static_reads) else {}
    motel6 = read_json(args.motel6) if args.motel6 and os.path.exists(args.motel6) else {}
    others = []
    for p in glob.glob(os.path.join(PKG, "identity_census", "*.json")):
        d = read_json(p)
        if isinstance(d, dict) and d.get("market_id") and d.get("market_id") != MARKET_ID:
            others += [(d["market_id"], h) for h in d.get("hotels", [])]

    hotels = copy.deepcopy(shadow2["hotels"])
    by_key = {h["identity_key"]: h for h in hotels}
    by_num = {}
    for h in hotels:
        n = house_number(h.get("address"))
        if n and h.get("postal_code"):
            by_num.setdefault((n, h["postal_code"][:5]), []).append(h["identity_key"])

    packet = OrderedDict((g, []) for g in ("A_rebrand_successor", "B_address_postal", "C_geography", "D_routing_trace", "E_lodging_non_lodging", "F_brand_locator_lead"))
    settled, held = [], []

    def item(group, prop, key, issue, evidence, rec, status, cimp="none", aimp="none"):
        packet[group].append(OrderedDict([("property", prop), ("identity_key", key), ("issue", issue), ("evidence", evidence), ("recommendation", rec), ("status", status), ("census_impact", cimp), ("authority_impact", aimp)]))
        (settled if status.startswith("SETTLED") else held).append(key)

    # ---------------- phase 2: Cambria -> Wyndham Avon
    wa = static.get("wyndham_avon", {})
    cam = by_key.get("cambria hotel and suites avon", {})
    binds = wa.get("status") == 200 and house_number(wa.get("street")) == house_number(cam.get("address")) and wa.get("postal") == cam.get("postal_code")
    item("A_rebrand_successor", "Cambria Hotel & Suites Avon -> Wyndham Avon", "cambria hotel and suites avon",
         "the current first-party page at the census premises brands the property Wyndham Avon",
         OrderedDict([("page", wa.get("url")), ("document_sha256", wa.get("sha")), ("page_name", wa.get("name")), ("page_street", wa.get("street")), ("page_postal", wa.get("postal")), ("page_phone", wa.get("phone")),
                      ("census", OrderedDict([("address", cam.get("address")), ("postal_code", cam.get("postal_code")), ("phone", cam.get("phone"))])), ("route", "identity_routing shard ROUTING_CONFIRMED to the Wyndham page"),
                      ("historical", "PTF-CLEVELAND-ROUTING-REPAIR-001 verdict PROPERTY_CLOSED_OR_CONVERTED with rename proposal 'Wyndham Avon'; RR-001 attended artifact reads pets allowed $100/stay, 2 pets")]),
         "SAME_IDENTITY_REBRAND_SUCCESSOR (street number + postal + route bind; the census phone is empty so phone cannot conflict). NOT applied: Avon (44011) is a geography hold (ruling G). Apply the rename + PF only together with an Avon geography ruling.",
         "DETERMINED_HELD_ON_GEOGRAPHY" if binds else "HELD_IDENTITY_UNRESOLVED", "rename 1 key (deferred)", "+1 PF (deferred)")

    # ---------------- phase 3: Motel 6 Richfield / HIE
    m6_active = bool(motel6) and "5171 Brecksville" in json.dumps(motel6)
    item("A_rebrand_successor", "Motel 6 Richfield (LIVE PF) and Holiday Inn Express & Suites Cleveland-Richfield at 5171 Brecksville Rd", "motel 6 richfield",
         "two brands claim the same street address", OrderedDict([("motel6_page", motel6.get("url")), ("motel6_document_sha256", motel6.get("html_sha256")), ("motel6_state", "ACTIVE and bookable; JSON-LD names Motel 6 Richfield, OH at 5171 Brecksville Road; reservations 330-659-6116"),
                                                              ("ihg_search", "Holiday Inn Express & Suites Cleveland-Richfield listed bookable at 5171 Brecksville Road, Richfield 44286 (identity_reads_002 TM-033 search list)")]),
         "BOTH_ACTIVE_DISTINCT_SAME_ADDRESS_IDENTITIES: Motel 6 is still active (own page) and the HIE is active (IHG inventory); neither is a successor of the other. Record SAME_CAMPUS_DISTINCT_ENTITY and admit the HIE as a true-missing identity on a first-party property-page read (not done this order: the IHG property page was not opened). Live Motel 6 PF row untouched.",
         "DETERMINED_AWAITING_HIE_PAGE_READ" if m6_active else "HELD", "+1 row after the HIE page read", "none")

    # ---------------- phase 4: Red Roof Akron
    item("B_address_postal", "Red Roof Inn Akron (2939 S Arlington Rd)", ptf_identity_key("Red Roof Inn Akron"),
         "census/OSM postal 44312 vs the page's SEO title '44132'", OrderedDict([("page", "https://www.redroof.com/property/oh/akron/rri207"), ("page_address_block", "2939 S Arlington Rd, Akron OH (no postal in the address block or JSON-LD)"), ("title", "Cheap Hotel in Akron, OH 44132 | Red Roof"), ("property_code", "RRI207"), ("brand_locator", "redroof.com/locations/oh/akron rendered empty")]),
         "IDENTITY_UNRESOLVED on postal: the street, city and property code bind, the page states no postal in its own address block, and 44132 (an Euclid ZIP) cannot be the Akron premises; a second first-party source (Red Roof locator or booking page) is needed before admission. Not silently corrected.",
         "HELD_IDENTITY_UNRESOLVED", "+1 row after postal proof", "none")

    # ---------------- phase 5: Oakwood Village 44146
    oak_rows = []
    for name, street, city, pc, phone, url, code, sha in OAKWOOD:
        key = ptf_identity_key(name)
        oak_rows.append(OrderedDict([
            ("identity_key", key), ("canonical_name", name), ("display_name", name), ("slug", slugify(name)), ("market_id", MARKET_ID), ("address", street), ("city", city), ("state", "OH"), ("postal_code", pc),
            ("phone", phone), ("identity_state", "IDENTITY_CONFIRMED"), ("lodging_state", "LODGING_BY_NAME"), ("policy_state", "POLICY_NOT_VERIFIED"), ("collision_state", "NONE"), ("official_url", url),
            ("corridor", EAST), ("assignment_basis", "explicit"), ("assignment_value", ""), ("source", "first_party_page" if url else "first_party_brand_locator"), ("source_id", url or "choicehotels.com locator"),
            ("observed_at", RULED_ON), ("provenance", WORK_ORDER + ":PHASE_5_OAKWOOD_VILLAGE"), ("batch", "hardened-policy-003"), ("has_official_link", bool(url)), ("normalized_name", key), ("raw_name", name),
            ("street_identity", "%s|%s" % (street.lower(), pc)),
            ("admission", OrderedDict([("status", "SHADOW_ADMITTED_003_EXPLICIT_ASSIGNMENT_PENDING_CONTRACT"), ("classification", "CONFIRMED_TRUE_MISSING"), ("geography", "CLEARLY_WITHIN_EXISTING_MARKET_INTENT"),
                                       ("why", "Oakwood Village is a Cuyahoga County suburb on I-271 between declared postals 44128 (Warrensville Heights) and 44139 (Solon) in the east-side doctrine; assigned EXPLICITLY to %s rather than by declaring ZIP 44146" % EAST),
                                       ("contract_change_required", "explicit_hotel_ids on %s (market contract) -- a protected file; proposed, not applied" % EAST), ("evidence_document_sha256", sha), ("property_code", code), ("work_order", WORK_ORDER)])),
        ]))
    item("C_geography", "Oakwood Village 44146 (2 first-party-confirmed hotels)", "(geography)", "undeclared postal inside the east-side doctrine",
         OrderedDict([("hotels", [r["canonical_name"] for r in oak_rows]), ("declared_neighbours", ["44128 Warrensville Heights", "44139 Solon", "44146 sits between them on I-271"])]),
         "CLEARLY_WITHIN_EXISTING_MARKET_INTENT: admitted to the SHADOW with an explicit corridor assignment (%s); no ZIP widened; the contract's explicit_hotel_ids change is proposed for the deployment-bearing order" % EAST, "SETTLED_MECHANICALLY_SHADOW_ONLY", "+2 shadow rows", "none")

    # ---------------- phase 6: full-name overlays (keys preserved)
    overlays = [("the westin", "The Westin Cleveland Downtown", "https://www.marriott.com/en-us/hotels/clewi-the-westin-cleveland-downtown/overview/", "03e2306560df8efb540a522729bf6e20130321f528436b96ef129b14b5f9983c"),
                ("towneplace suites by marriott", "TownePlace Suites by Marriott Cleveland Solon", "https://www.marriott.com/en-us/hotels/cleto-towneplace-suites-cleveland-solon/overview/", "f909711936fc93105fbb52e64199a72be2dc72b0db5eb213dca241327a36ba9c"),
                ("sonesta es suites cleveland westlake", "Sonesta Simply Suites Cleveland Westlake", "https://www.sonesta.com/sonesta-simply-suites/oh/westlake/sonesta-simply-suites-cleveland-westlake", static.get("sonesta_westlake", {}).get("sha"))]
    applied_overlays = []
    for key, full, url, sha in overlays:
        h = by_key.get(key)
        if not h:
            continue
        h["display_name"] = full
        h["display_name_overlay_003"] = OrderedDict([("full_name", full), ("evidence_url", url), ("document_sha256", sha), ("identity_key_preserved", True), ("live_row", key in policy or key in excl)])
        if url and not h.get("official_url"):
            h["official_url"] = url
            h["has_official_link"] = True
        applied_overlays.append(key)
    item("D_routing_trace", "The Westin / TownePlace Suites by Marriott / Sonesta ES Suites Cleveland Westlake full names", "(3 keys)", "shortened or superseded chain names on LIVE rows",
         OrderedDict([("westin", "The Westin Cleveland Downtown, 777 Saint Clair Ave NE 44114, CLEWI"), ("towneplace", "TownePlace Suites by Marriott Cleveland Solon, 6040 Enterprise Pkwy 44139, CLETO"), ("sonesta", "Sonesta Simply Suites Cleveland Westlake, 30100 Clemens Rd 44145, phone matches census")]),
         "display-name overlays applied in the SHADOW with identity keys preserved (doctrine: a successor key needs approval; none is required here)", "SETTLED_MECHANICALLY_SHADOW_ONLY", "none (display only)", "none")

    # ---------------- phase 7: routing-repair traces
    # Comfort Suites Twinsburg: Choice's own locator states 2716 Creekside Drive
    cs = by_key.get("comfort suites twinsburg")
    if cs and cs.get("address", "").startswith("2715"):
        cs["address_supersession_003"] = OrderedDict([("from", cs["address"]), ("to", "2716 Creekside Drive"), ("evidence", "choicehotels.com locator (identity_reads_002 TM-034 page): 'Comfort Suites Twinsburg | 2716 Creekside Drive, Twinsburg, OH, 44087'"), ("document_sha256", "cde73e2d298495829f1b6f694aace6f94fcde701b3dcb7da35e2ab56531da828")])
        cs["address"] = "2716 Creekside Drive"
    item("D_routing_trace", "Comfort Suites Twinsburg", "comfort suites twinsburg", "census 2715 Creekside Dr vs page 2716 Creekside Drive (routing repair 001)", "Choice locator states 2716 Creekside Drive, Twinsburg, OH 44087",
         "SAFE_ADDRESS_SUPERSESSION applied in the shadow (live PF row's policy untouched)", "SETTLED_MECHANICALLY_SHADOW_ONLY", "address form on 1 row", "none")
    item("D_routing_trace", "Sonesta ES Suites Cleveland Westlake -> Sonesta Simply Suites", "sonesta es suites cleveland westlake", "routing repair 001 ROUTING_REPLACED with a rename proposal", "static read: page name Sonesta Simply Suites Cleveland Westlake, 30100 Clemens Road 44145, (440) 892-2254 = census phone",
         "SAFE_ROUTE_REPAIR: route to the Simply Suites page and display-name overlay (key preserved)", "SETTLED_MECHANICALLY_SHADOW_ONLY", "display only", "none")
    item("E_lodging_non_lodging", "Harbor Inn (1219 Main Ave 44113)", "harbor inn", "routing repair 001 IDENTITY_CONFLICT", "CVB anchor + chamberofcommerce category 'bar': the Harbor Inn Cafe, one of Cleveland's oldest bars; no lodging surface exists",
         "NON_LODGING -> RETIRE_FROM_HOTEL_PROMOTION_SET (same treatment as ruling C); awaiting founder", "HELD_FOUNDER", "-1 row", "none")
    item("E_lodging_non_lodging", "Hopp Inn (4896 Pearl Rd 44109)", "hopp inn", "routing repair 001 IDENTITY_CONFLICT", "CVB anchor + chamberofcommerce category 'bar': neighborhood bar with Polish food; no lodging surface exists",
         "NON_LODGING -> RETIRE_FROM_HOTEL_PROMOTION_SET; awaiting founder", "HELD_FOUNDER", "-1 row", "none")
    item("D_routing_trace", "Villa Croatia at the American-Croatian Lodge", "villa croatia at the american croatian lodge", "routing repair 001 OFFICIAL_URL_FOUND with a phone mismatch", "croatianlodge.com is an event-venue site (34900 Lakeshore Blvd #301, 44095); /rooms.html is 404; site phone 440-946-3366 vs census 216.704.9009",
         "HOLD: the route names the venue, not the lodging; no first-party lodging page located", "HELD_FOUNDER", "none", "none")

    # ---------------- phase 8: Kent State
    ks = by_key.get("kent state university hotel and conference center")
    kst = static.get("kent_state_hotel", {})
    if ks and kst.get("status") == 200 and house_number(kst.get("street")) == house_number(ks.get("address")) and kst.get("postal") == ks.get("postal_code"):
        ks["lodging_state"] = "LODGING_CONFIRMED"
        ks["official_url"] = kst.get("final") or kst.get("url")
        ks["has_official_link"] = True
        ks["lodging_confirmation_003"] = OrderedDict([("page", kst.get("final")), ("document_sha256", kst.get("sha")), ("page_name", kst.get("name")), ("page_street", kst.get("street")), ("page_postal", kst.get("postal")), ("page_phone", kst.get("phone"))])
        item("E_lodging_non_lodging", "Kent State University Hotel & Conference Center", ks["identity_key"], "lodging_state NEEDS_REVIEW", "first-party site names the hotel at 215 S. Depeyster Street, Kent 44240, +1-330-346-0100 (census street/postal/phone)",
             "LODGING, in market (44240, streetsboro-hudson-aurora corridor); lodging_state -> LODGING_CONFIRMED in the shadow; pet policy not stated on the site (work-browser pass: PAGE_RENDERED_NO_PET_POLICY_STATED)", "SETTLED_MECHANICALLY_SHADOW_ONLY", "none", "none")

    # ---------------- phase 9: 12 brand-locator leads
    lead_results, lead_rows = [], []
    for name, street, city, pc, fam, url, sha in LEADS:
        key = ptf_identity_key(name)
        num = house_number(street)
        hits = by_num.get((num, pc), []) + [r["identity_key"] for r in lead_rows if house_number(r["address"]) == num and r["postal_code"] == pc]
        cross = [(mid, h["identity_key"]) for mid, h in others if house_number(h.get("address")) == num and (h.get("postal_code") or "")[:5] == pc]
        in_market = pc in postal_to_corridor or pc in {(h.get("postal_code") or "")[:5] for h in pinned["hotels"]}
        fam_of = lambda n: ("ESA" if "extended stay" in n.lower() else "IHG" if re.search(r"staybridge|candlewood|holiday inn|crowne", n.lower()) else "CHOICE" if re.search(r"comfort|quality|mainstay", n.lower()) else "OTHER")
        if key in by_key:
            cls, why = "ALREADY_REGISTERED_ALIAS", "identity key registered"
        elif hits and fam_of(by_key[hits[0]]["canonical_name"]) == fam:
            cls, why = "ALREADY_REGISTERED_ALIAS", "premises registered as %s (same brand family; name variant)" % hits[0]
        elif hits:
            cls, why = "REBRAND_SUCCESSOR", "premises registered as %s under another brand family; the registered row's page must be read before either identity moves (founder group A)" % hits[0]
        elif cross:
            cls, why = "OUTSIDE", "premises registered in %s" % cross[0][0]
        elif not in_market:
            cls, why = "OUTSIDE", "postal %s undeclared" % pc
        else:
            cls, why = "CONFIRMED_TRUE_MISSING", "brand's own locator states name, numbered street and postal; no registered row in any market shares the premises"
        lead_results.append(OrderedDict([("lead", name), ("identity_key", key), ("address", street), ("postal_code", pc), ("brand_family", fam), ("locator", url), ("locator_document_sha256", sha), ("classification", cls), ("why", why)]))
        if cls == "CONFIRMED_TRUE_MISSING":
            lead_rows.append(OrderedDict([
                ("identity_key", key), ("canonical_name", name), ("display_name", name), ("slug", slugify(name)), ("market_id", MARKET_ID), ("address", street), ("city", city), ("state", "OH"), ("postal_code", pc),
                ("phone", ""), ("identity_state", "IDENTITY_CONFIRMED"), ("lodging_state", "LODGING_BY_NAME"), ("policy_state", "POLICY_NOT_VERIFIED"), ("collision_state", "NONE"), ("official_url", ""),
                ("corridor", postal_to_corridor.get(pc, "")), ("assignment_basis", "postal_code" if postal_to_corridor.get(pc) else "unassigned"), ("assignment_value", pc if postal_to_corridor.get(pc) else ""),
                ("source", "first_party_brand_locator"), ("source_id", url), ("observed_at", RULED_ON), ("provenance", WORK_ORDER + ":PHASE_9_LOCATOR_LEAD"), ("batch", "hardened-policy-003"), ("has_official_link", False),
                ("normalized_name", key), ("raw_name", name), ("street_identity", "%s|%s" % (street.lower(), pc)),
                ("admission", OrderedDict([("status", "SHADOW_ADMITTED_003"), ("classification", cls), ("read_method", "BRAND_LOCATOR"), ("evidence_url", url), ("document_sha256", sha), ("phone", "not stated by the locator"), ("work_order", WORK_ORDER)])),
            ]))
    for lr in lead_results:
        grp = "A_rebrand_successor" if lr["classification"] == "REBRAND_SUCCESSOR" else "F_brand_locator_lead"
        item(grp, lr["lead"], lr["identity_key"], "brand-locator lead (Order 002)", OrderedDict([("locator", lr["locator"]), ("document_sha256", lr["locator_document_sha256"]), ("address", lr["address"] + " " + lr["postal_code"])]),
             lr["classification"] + " -- " + lr["why"], "SETTLED_MECHANICALLY_SHADOW_ONLY" if lr["classification"] == "CONFIRMED_TRUE_MISSING" else ("HELD_FOUNDER" if lr["classification"] == "REBRAND_SUCCESSOR" else "SETTLED_NO_ACTION"), "+1 shadow row" if lr["classification"] == "CONFIRMED_TRUE_MISSING" else "none", "none")

    # ---------------- phase 13: shadow census v003
    shadow = copy.deepcopy(shadow2)
    shadow["hotels"] = hotels + oak_rows + lead_rows
    shadow["count"] = len(shadow["hotels"])
    shadow["work_order"] = WORK_ORDER
    shadow["captured_at"] = RULED_ON
    shadow["what_this_is"] = ("SHADOW admission census v003 for %s: Order-002 shadow (208) + 2 Oakwood Village rows (explicit east-side assignment, contract change proposed) + %d brand-locator true-missing rows; "
                              "display-name overlays on 3 live rows (keys preserved); Comfort Suites Twinsburg address supersession; Kent State lodging confirmed. Never registered, never deployed." % (MARKET_ID, len(lead_rows)))
    shadow["admission_003"] = OrderedDict([("pinned_census_touched", False), ("supersedes_002", OrderedDict([("count", shadow2["count"]), ("sha256", sha_file(os.path.relpath(ADMISSION, _DASH)))])),
                                           ("added_oakwood_explicit", len(oak_rows)), ("added_locator_leads", len(lead_rows)), ("display_overlays", applied_overlays), ("address_supersessions", ["comfort suites twinsburg"] if cs else []),
                                           ("lodging_confirmed", ["kent state university hotel and conference center"] if ks and ks.get("lodging_confirmation_003") else []), ("deployment", "NONE")])
    issues = [str(i) for i in CENSUS.validate(shadow, market_states=("OH",))]
    keys = [h["identity_key"] for h in shadow["hotels"]]
    dup = sorted({k for k in keys if keys.count(k) > 1})
    def prem_key(h):
        toks = [t for t in re.findall(r"[a-z0-9]+", (h.get("address") or "").lower()) if t not in ("e", "east", "w", "west", "n", "north", "s", "south", "ne", "nw", "se", "sw")]
        return (toks[0], toks[1][:4] if len(toks) > 1 else "", h["postal_code"]) if toks and toks[0].isdigit() else None
    prem = Counter(k for k in (prem_key(h) for h in shadow["hotels"]) if k)
    same_campus_recorded = {("130", "mont", "44321")}
    dup_prem = [k for k, v in prem.items() if v > 1 and k not in same_campus_recorded]

    # ---------------- phase 12: policy inventory
    pc_ = reads["classification"]
    new_pf = [x["identity_key"] for x in pc_ if x["classification"] == "CLEAN_PET_FRIENDLY"]
    new_np = [x["identity_key"] for x in pc_ if x["classification"] == "CLEAN_VERIFIED_NO_PETS"]
    pend_pf = [app2["B_successor_pet_friendly"]["successor"]["identity_key"]] + new_pf
    pend_np = [x["identity_key"] for x in app2["A_clean_verified_no_pets"]] + new_np
    inv = OrderedDict([
        ("LIVE", OrderedDict([("pet_friendly", len(policy)), ("verified_no_pets", len(excl))])),
        ("PENDING_SHADOW", OrderedDict([("pet_friendly", pend_pf), ("verified_no_pets", pend_np), ("founder_holds", [x["identity_key"] for x in pc_ if x["classification"] == "FOUNDER_EXCEPTION"] + ["cambria hotel and suites avon"]),
                                        ("source_silent_or_not_found", [x["identity_key"] for x in pc_ if x["classification"] in ("SOURCE_SILENT", "POLICY_NOT_FOUND")]),
                                        ("capture_failed_attended_lane", [x["identity_key"] for x in pc_ if x["classification"] == "CAPTURE_FAILED"]),
                                        ("no_action", [])])),
        ("PROJECTED_IF_APPLIED", OrderedDict([("census", shadow["count"]), ("pet_friendly", len(policy) + len(pend_pf)), ("verified_no_pets", len(excl) + len(pend_np)), ("resolved", len(policy) + len(excl) + len(pend_pf) + len(pend_np)),
                                              ("unresolved", shadow["count"] - (len(policy) + len(excl) + len(pend_pf) + len(pend_np))), ("profiles", len(policy) + len(pend_pf))])),
        ("live_policy_package_written", False), ("live_exclusions_written", False),
    ])

    # ---------------- phase 14: pilot plan (not executed)
    rates, brand_yield, discovery, market_ledger = PAID.measured_rates()
    bd_unit = rates["brightdata_browser"]["usd_per_billed_attempt"]
    places_unit = GOOGLE_RATE_CARD["text_search_pro_usd_per_request"]
    lanes2 = state2["phase_9_lanes"]["counts"]
    pilot = OrderedDict([
        ("authorized", False), ("executed", False), ("live_read_at", args.bd_read_at),
        ("bright_data", OrderedDict([("rows", 1), ("unit_usd_measured", bd_unit), ("expected_usd", round(bd_unit, 2)), ("hard_cap_usd", round(bd_unit * 1.25, 2)), ("balance_usd", args.bd_balance_usd), ("pending_usd", args.bd_pending_usd),
                                     ("balance_sufficient", args.bd_balance_usd is not None and args.bd_balance_usd >= bd_unit * 1.25), ("expected_publication_grade_rows", round(1 * (rates["brightdata_browser"]["publication_grade_rate_wilson_lower"] or 0), 2))])),
        ("google_places", OrderedDict([("rows", 10), ("unit_usd_rate_card", places_unit), ("ledger_state", discovery["unit_price_state"]), ("expected_usd", round(10 * places_unit, 2)), ("hard_cap_usd", round(10 * places_unit * 1.25, 2)),
                                       ("expected_binds", round(10 * (discovery["bind_rate_wilson_lower"] or 0), 1)), ("rate_card", GOOGLE_RATE_CARD)])),
        ("account_balance_required_usd", OrderedDict([("bright_data", round(bd_unit * 1.25, 2)), ("google_places", round(10 * places_unit * 1.25, 2))])),
    ])

    # ---------------- phase 15: readiness
    failed = [x["identity_key"] for x in pc_ if x["classification"] == "CAPTURE_FAILED"]
    blockers = [
        "clean policy inventory is NOT fully bound: %d of 23 admitted rows are CAPTURE_FAILED (attended lane dropped / wyndhamhotels.com not permitted in the extension) and %d newly admitted rows (Oakwood 2 + leads %d) have no policy read" % (len(failed), 2 + len(lead_rows), len(lead_rows)),
        "founder identity decisions still open: %d held items (Cambria/Avon geography, Motel 6-HIE same campus, Red Roof postal, Harbor Inn, Hopp Inn, Villa Croatia)" % len(held),
        "the shadow application (PF %d, no-pets %d, 1 supersession, 3 retirements, overlays) is not applied to live authority -- deployment-bearing order" % (len(pend_pf), len(pend_np)),
        "the release contract pins 188/99/40 and the market contract lacks the Oakwood explicit assignment; a deterministic rebuild needs both re-pinned in the deployment-bearing order",
    ]
    t0 = calendar.timegm(time.strptime(args.started_at, "%Y-%m-%dT%H:%M:%SZ")) if args.started_at else None
    elapsed = round((time.time() - t0) / 60.0, 1) if t0 else None
    doc = OrderedDict([
        ("schema", "ptf-shadow-policy-state/1.0"), ("work_order", WORK_ORDER), ("market_id", MARKET_ID), ("as_of", RULED_ON), ("provider_calls", 0), ("usd_spent", 0.0),
        ("live_authority_touched", False), ("pinned_census_touched", False), ("deployment", "NONE"),
        ("phase_1_grouped_packet", OrderedDict([("groups", packet), ("settled", sorted(set(settled))), ("held", sorted(set(held)))])),
        ("phase_9_locator_leads", OrderedDict([("attempted", len(LEADS)), ("counts", OrderedDict(sorted(Counter(l["classification"] for l in lead_results).items()))), ("results", lead_results)])),
        ("phase_10_11_policy_reads", OrderedDict([("attempted", reads["rows_attempted"]), ("targets", reads["targets"]), ("counts", reads["classification_counts"]), ("free_http_requests", reads["free_http_requests"])])),
        ("phase_12_policy_inventory", inv),
        ("phase_13_shadow_census", OrderedDict([("path", os.path.relpath(ADMISSION, _DASH)), ("pinned", len(pinned["hotels"])), ("shadow", shadow["count"]), ("deduplicated", shadow["count"] - len(dup)),
                                                ("additions_total", shadow["count"] - len(pinned["hotels"]) + len(shadow2["retired_non_lodging_002"])), ("additions_003", len(oak_rows) + len(lead_rows)),
                                                ("retirements", len(shadow2["retired_non_lodging_002"])), ("successors", len(shadow2["supersessions_002"])), ("geography_holds", ["avon (cambria->wyndham avon)"]),
                                                ("unresolved_identity", ["red roof inn akron", "villa croatia", "harbor inn", "hopp inn"]), ("validation_issues", issues), ("duplicate_keys", dup), ("duplicate_premises", dup_prem)])),
        ("phase_14_pilot_plan_not_executed", pilot),
        ("phase_15_promotion_readiness", OrderedDict([("PROMOTION_READY", False), ("blockers", blockers), ("optional_coverage_expansion_blocks_promotion", False)])),
        ("factory", OrderedDict([("active_minutes_003", elapsed), ("free_requests_003", reads["free_http_requests"] + args.static_requests + args.browser_page_loads), ("generic_code_changes", 0)])),
    ])
    return shadow, doc


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--static-reads", default="")
    ap.add_argument("--motel6", default="")
    ap.add_argument("--started-at", default=None)
    ap.add_argument("--static-requests", type=int, default=0)
    ap.add_argument("--browser-page-loads", type=int, default=0)
    ap.add_argument("--bd-balance-usd", type=float, default=None)
    ap.add_argument("--bd-pending-usd", type=float, default=None)
    ap.add_argument("--bd-read-at", default=None)
    args = ap.parse_args(argv)
    shadow, doc = build(args)
    write_json(ADMISSION, shadow)
    p2 = os.path.join(REPORTS, f"{M}_policy_state_003.json")
    write_json(p2, doc)
    packet = OrderedDict([("contract", "ptf-founder-review-packet/1.0"), ("work_order", WORK_ORDER), ("market_id", MARKET_ID), ("generated_at", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())),
                          ("nothing_was_spent", True), ("nothing_was_published", True), ("groups", doc["phase_1_grouped_packet"]["groups"]),
                          ("held_decisions", doc["phase_1_grouped_packet"]["held"]), ("settled_mechanically", doc["phase_1_grouped_packet"]["settled"])])
    p3 = os.path.join(PKG, f"{M}_grouped_founder_packet_003.json")
    write_json(p3, packet)
    for p in (ADMISSION, p2, p3):
        print("written", os.path.relpath(p, _DASH))
    sc = doc["phase_13_shadow_census"]
    print("shadow", sc["shadow"], "dedup", sc["deduplicated"], "issues", sc["validation_issues"], "dup keys", sc["duplicate_keys"], "dup premises", sc["duplicate_premises"])
    print("leads", dict(doc["phase_9_locator_leads"]["counts"]))
    print("policy", dict(doc["phase_10_11_policy_reads"]["counts"]))
    print("projected", json.dumps(doc["phase_12_policy_inventory"]["PROJECTED_IF_APPLIED"]))
    print("packet held", doc["phase_1_grouped_packet"]["held"], "settled", len(doc["phase_1_grouped_packet"]["settled"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
