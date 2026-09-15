"""PTF-ORLANDO-FL-HARDENED-V2-SOURCE-READY-001 -- Phases 20-21: every census identity in exactly one disposition.

Two vocabularies on every row, both mechanical:

  final_state   the partition contract's own state (contracts.partition), which the sealed package reconciles.
  disposition   the order's Phase 20 vocabulary (CLEAN_PET_FRIENDLY, CLEAN_VERIFIED_NO_PETS, IDENTITY_HOLD, ROUTING_HOLD,
                ACCESS_BLOCKED, EVIDENCE_HOLD, NEGATION_HOLD, POLICY_NOT_FOUND, SOURCE_SILENT, BROWSER_CAPTURE_NEEDED,
                PAID_HOLD, MIXED_RESORT_HOLD, GEOGRAPHY_HOLD, FOUNDER_REVIEW).

Every unresolved row also carries its ROUTER RECORD (Phase 13): the static attempt, whether the ladder found Firecrawl
eligible, whether Firecrawl was attempted and what it returned, whether the attended browser read it, and the final
block reason. ACCESS_BLOCKED is written ONLY after that record shows the router exhausted: a static channel failure,
Firecrawl either attempted and refused/failed or not eligible by the committed route table, and no attended read.

Nothing here fetches or publishes.

Output: launch_packages/pettripfinder/markets/staging/orlando-fl/launch_package/orlando_fl_final_partition_v2_001.json
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import Counter, OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

from scripts.pettripfinder.contracts import partition as PARTITION  # noqa: E402
from scripts.pettripfinder.hotel_exclusions import address_key  # noqa: E402

WORK_ORDER = "PTF-ORLANDO-FL-HARDENED-V2-SOURCE-READY-001"
MARKET_ID = "orlando-fl"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
OUT = os.path.join(PKG, "markets", "staging", "orlando-fl", "launch_package", "orlando_fl_final_partition_v2_001.json")
CENSUS = os.path.join(PKG, "identity_census_proposed", "orlando-fl.json")
CLEAN = os.path.join(REPORTS, "orlando_fl_v2_clean_authority_001.json")
ROUTING = os.path.join(REPORTS, "orlando_fl_v2_routing_001.json")
STATIC = os.path.join(REPORTS, "orlando_fl_v2_free_static_capture_001.json")
LADDER = os.path.join(REPORTS, "orlando_fl_v2_ladder_plan_001.json")
FIRECRAWL = os.path.join(REPORTS, "orlando_fl_v2_firecrawl_pass_001.json")
READS = os.path.join(REPORTS, "orlando_fl_v2_policy_reads_001.json")
AS_OF = "2026-09-15"

#: held read class -> (final_state, disposition)
HELD = {
    "NEGATION_HOLD": ("AWAITING_CONTRADICTION_RESOLUTION", "NEGATION_HOLD"),
    "NEGATION_HOLD_UNREADABLE_REFUSAL": ("AWAITING_POLICY_OBSERVATION", "NEGATION_HOLD"),
    "FIRST_PARTY_CONFLICT": ("AWAITING_CONTRADICTION_RESOLUTION", "EVIDENCE_HOLD"),
    "SERVICE_ANIMAL_ONLY": ("AWAITING_POLICY_OBSERVATION", "EVIDENCE_HOLD"),
    "QUOTE_NOT_OPERATIVE": ("AWAITING_POLICY_OBSERVATION", "EVIDENCE_HOLD"),
    "FEE_ONLY": ("AWAITING_POLICY_OBSERVATION", "EVIDENCE_HOLD"),
    "AMENITY_CHIP_ONLY": ("AWAITING_POLICY_OBSERVATION", "EVIDENCE_HOLD"),
    "QUOTE_CONTRADICTS_CLAIM": ("AWAITING_CONTRADICTION_RESOLUTION", "EVIDENCE_HOLD"),
    "POLICY_NOT_FOUND": ("AWAITING_POLICY_OBSERVATION", "POLICY_NOT_FOUND"),
    "CO_LOCATION_RULING_REQUIRED": ("AWAITING_IDENTITY_RESOLUTION", "IDENTITY_HOLD"),
    "ADDRESS_KEY_DIRECTIONAL_COLLISION": ("AWAITING_IDENTITY_RESOLUTION", "IDENTITY_HOLD"),
    "DUPLICATE_READ_FOR_ONE_IDENTITY": ("AWAITING_POLICY_OBSERVATION", "EVIDENCE_HOLD"),
    "STRUCTURED_NO_PETS_INSUFFICIENT": ("AWAITING_POLICY_OBSERVATION", "EVIDENCE_HOLD"),
}
#: families the committed route table excludes from paid acquisition (premium domains) -- attended only
EXCLUDED_FAMILIES = ("HYATT", "BEST_WESTERN")
_TIMESHARE_WORDS = re.compile(r"\b(vacation club|grand vacations|vistana|marriott'?s (?!orlando world)|westgate|club wyndham|"
                              r"worldmark|holiday inn club|bluegreen|villas? resort|residence club)\b", re.I)


def _load(p, default=None):
    if not os.path.exists(p):
        return default
    with open(p, encoding="utf-8-sig") as fh:
        return json.load(fh)


def _keys(h):
    # ORDERED (the identity key, then its aliases sorted): callers take the FIRST key a lane row exists for, and a set's
    # order moves with Python's per-process string hash -- the reproduction run picked another alias's static row
    return [h["identity_key"]] + sorted(set(h.get("identity_key_aliases") or []) - {h["identity_key"]})


def build():
    census = _load(CENSUS)
    clean = _load(CLEAN)
    routing = {r["identity_key"]: r for r in (_load(ROUTING, {}) or {}).get("routes", [])}
    static = {r["identity_key"]: r for r in (_load(STATIC, {}) or {}).get("rows", [])}
    ladder = {r["identity_key"]: r for r in (_load(LADDER, {}) or {}).get("rows", [])}
    fc = {r["identity_key"]: r for r in (_load(FIRECRAWL, {}) or {}).get("rows", [])}
    reads = (_load(READS, {}) or {}).get("rows", [])
    read_streets = {}
    for r in reads:
        sig = r.get("identity_signals") or {}
        k = address_key(sig.get("address_on_page") or "", (sig.get("postal_code") or "")[:5])
        if k:
            read_streets.setdefault(k, []).append(r)

    # browser reads the supported lane attempted and the site refused (Akamai "Access Denied"), by brand property code
    browser_blocked = {}
    raw = os.path.join(PKG, "markets", "staging", "orlando-fl", "raw_captures")
    browser_ok = set()
    for fname in ("marriott_browser_rows.jsonl", "marriott_browser_rows_agent.jsonl", "marriott_browser_rows_retry.jsonl",
                  "marriott_browser_rows_closure.jsonl", "hilton_browser_rows.jsonl", "hilton_browser_rows_retry.jsonl",
                  "hilton_browser_rows_closure.jsonl", "hyatt_browser_rows.jsonl", "hyatt_browser_rows_closure.jsonl",
                  "bestwestern_browser_rows.jsonl"):
        p = os.path.join(raw, fname)
        if not os.path.exists(p):
            continue
        for line in open(p, encoding="utf-8-sig"):
            line = line.strip()
            if not line:
                continue
            r = json.loads(line)
            code = (r.get("c") or (re.search(r"/hotels/([a-z0-9]+)-", r.get("u") or "") or [None, ""])[1]).lower()
            if r.get("status") in ("BLOCKED", "RETIRED", "COMING_SOON") and code:
                browser_blocked[code] = r.get("status")
            elif r.get("status") == "OK" and code:
                browser_ok.add(code)
    # a code the browser later read (closure-002 retry after the wall lifted) is no longer browser-blocked
    for code in browser_ok:
        if browser_blocked.get(code) == "BLOCKED":
            del browser_blocked[code]
    pf ={r["identity_key"] for r in clean["clean_pet_friendly"]}
    np_ = {r["identity_key"] for r in clean["clean_verified_no_pets"]}
    by_street = {}
    for h in census["hotels"]:
        by_street.setdefault(address_key(h.get("street") or "", (h.get("postal_code") or "")[:5]), []).append(h["identity_key"])
    held = {}
    for r in clean["rejected"]:
        if r["classification"] not in HELD:
            continue
        sig = r.get("identity_signals") or {}
        k = r.get("identity_key")
        if not k:
            cands = by_street.get(address_key(sig.get("address_on_page") or "", (sig.get("postal_code") or "")[:5]), [])
            k = cands[0] if len(cands) == 1 else None
        if k and k not in held:
            held[k] = r

    items = []
    for h in census["hotels"]:
        key = h["identity_key"]
        keys = _keys(h)
        row = OrderedDict((("identity_key", key), ("canonical_name", h["canonical_name"])))
        if key in pf:
            row.update(final_state="PUBLISHED_PET_FRIENDLY", resolved=True, disposition="CLEAN_PET_FRIENDLY")
        elif key in np_:
            row.update(final_state="VERIFIED_NO_PETS", resolved=True, disposition="CLEAN_VERIFIED_NO_PETS")
        else:
            route = routing.get(key) or next((routing[k] for k in keys if k in routing), {}) or {}
            srow = next((static[k] for k in keys if k in static), {})
            lrow = next((ladder[k] for k in keys if k in ladder), {})
            frow = next((fc[k] for k in keys if k in fc), {})
            street_reads = read_streets.get(address_key(h.get("street") or "", (h.get("postal_code") or "")[:5]), [])
            browser = [r for r in street_reads if r.get("lane") == "ATTENDED_BROWSER"]
            family = (route.get("brand_family") or lrow.get("brand") or h.get("brand") or "").upper() or "INDEPENDENT"
            record = OrderedDict([
                ("brand_family", family),
                ("route", route.get("url") or h.get("official_url") or ""),
                ("static_attempt", srow.get("outcome") or ("NOT_ATTEMPTED_NO_ROUTE" if not (route.get("url")) else
                                                           "NOT_ATTEMPTED_READ_BY_A_BRAND_SERVICE_LANE")),
                ("official_route_attempt", "YES" if route.get("url") else "NO_ROUTE"),
                ("firecrawl_eligible", bool(lrow.get("firecrawl_candidate"))),
                ("firecrawl_eligibility_reason", lrow.get("firecrawl_reason") or ""),
                ("firecrawl_attempted", bool(frow)),
                ("firecrawl_result", frow.get("firecrawl_class") or ""),
                ("other_router_fallback", "NONE_AUTHORIZED (Bright Data USD lanes need a founder cost plan)"),
                ("supported_browser_result", ("READ" if browser else "NOT_READ")),
            ])
            code = (h.get("property_code") or "").lower() or (
                re.search(r"/hotels/([a-z0-9]{5,8})-|propertyCode\.(\d+)", record["route"] or "") or [None, ""])[1] or ""
            if code in browser_blocked:
                record["supported_browser_result"] = browser_blocked[code]
            state = disp = action = None
            reason = h.get("classification_reason") or ""
            if h.get("identity_state") != "IDENTITY_CONFIRMED":
                state, disp = "AWAITING_IDENTITY_RESOLUTION", "IDENTITY_HOLD"
                action = "resolve the identity before any policy work binds to it: " + reason[:200]
            elif key in held:
                state, disp = HELD[held[key]["classification"]]
                action = ("the property's own page was read and its statement was held as %s: %s"
                          % (held[key]["classification"], (held[key].get("why") or "")[:240]))
            elif street_reads and all((r.get("extraction") or {}).get("pets_allowed") is None for r in street_reads):
                state, disp = "AWAITING_POLICY_OBSERVATION", "SOURCE_SILENT"
                action = "the property's own page served and stated no pet policy the readers located; observe a policy page"
            elif not record["route"]:
                if _TIMESHARE_WORDS.search(h["canonical_name"]):
                    state, disp = "AWAITING_OFFICIAL_URL", "MIXED_RESORT_HOLD"
                    action = "a resort / vacation-ownership campus with no first-party hotel route: prove public hotel operation first"
                else:
                    state, disp = "AWAITING_OFFICIAL_URL", "ROUTING_HOLD"
                    action = ("find a first-party route: no brand inventory, bureau listing or map source in this order stated "
                              "the property's own page")
            elif srow.get("outcome") in ("POLICY_NOT_FOUND",) or srow.get("classification") in (
                    "IDENTITY_TEXT_BOUND_POLICY_SILENT", "SOURCE_SILENT_STATIC", "BLOCK_FOUND_BUT_SILENT") \
                    or frow.get("firecrawl_class") == "FIRECRAWL_SOURCE_SILENT":
                state, disp = "AWAITING_POLICY_OBSERVATION", "SOURCE_SILENT"
                action = "the property's own page served and stated no operative pet policy; read a dedicated policy / FAQ page"
            elif srow.get("outcome") == "IDENTITY_MISMATCH" or frow.get("firecrawl_class") == "FIRECRAWL_MISMATCH":
                state, disp = "AWAITING_ROUTING_REPLACEMENT", "ROUTING_HOLD"
                action = "the routed page states a different property; find the property's own route"
            elif record["supported_browser_result"] == "BLOCKED":
                state, disp = "ACCESS_BLOCKED", "ACCESS_BLOCKED"
                action = ("router exhausted: static %s; Firecrawl %s (%s); the supported attended browser was served the "
                          "site's 'Access Denied' bot wall on 2026-09-15. Re-probe the attended read when the wall lifts; the "
                          "only further lane is a founder-costed paid fetch"
                          % (srow.get("outcome") or "not attempted", "not eligible" if not record["firecrawl_eligible"] else
                             "attempted", record["firecrawl_eligibility_reason"] or record["firecrawl_result"]))
            elif record["supported_browser_result"] in ("RETIRED", "COMING_SOON"):
                state, disp = "AWAITING_ROUTING_REPLACEMENT", "ROUTING_HOLD" if record["supported_browser_result"] == "RETIRED" else "IDENTITY_HOLD"
                action = ("the brand's own route is %s (the property page redirects to the brand's search or is listed as "
                          "coming soon); find the building's current flag and route" % record["supported_browser_result"])
            elif family in ("MARRIOTT", "HILTON") or family in EXCLUDED_FAMILIES:
                state, disp = "AWAITING_ATTENDED_CAPTURE", "BROWSER_CAPTURE_NEEDED"
                action = ("the router's next rung is the attended browser (%s is %s); read the property page there"
                          % (family, "a measured Firecrawl capability wall" if family in ("MARRIOTT", "HILTON")
                             else "excluded from paid acquisition on premium-domain cost"))
            elif frow and frow.get("firecrawl_class") in ("FIRECRAWL_BLOCKED", "FIRECRAWL_FAILED"):
                state, disp = "ACCESS_BLOCKED", "ACCESS_BLOCKED"
                action = ("router exhausted on the free and authorised lanes: static %s, Firecrawl %s; the next rung is an "
                          "attended read or a founder-costed paid fetch" % (srow.get("outcome"), frow.get("firecrawl_class")))
            elif srow.get("outcome") in ("ACCESS_DENIED", "NAVIGATION_FAILED", "CAPTURE_FAILED", "UNHYDRATED", "BLANK_PAGE",
                                         "UNEXPECTED_PAGE") and not lrow.get("firecrawl_candidate") and not frow:
                state, disp = "AWAITING_ATTENDED_CAPTURE", "BROWSER_CAPTURE_NEEDED"
                action = ("static %s; Firecrawl is not the next rung (%s); an attended read is"
                          % (srow.get("outcome"), lrow.get("firecrawl_reason") or "unmeasured family"))
            elif lrow.get("firecrawl_reason") == "PROPERTY_CODE_UNPARSEABLE_ROUTING_REPAIR_REQUIRED":
                state, disp = "AWAITING_PROPERTY_LEVEL_URL", "ROUTING_HOLD"
                action = "the route carries no parseable brand property code; repair the route to the brand's canonical page"
            else:
                state, disp = "AWAITING_POLICY_OBSERVATION", "BROWSER_CAPTURE_NEEDED"
                action = "no lane in this order produced a bindable policy read for this routed identity; read it attended"
            record["final_block_reason"] = action
            row.update(final_state=state, resolved=False, disposition=disp, next_action=action,
                       next_action_source="PTF-ORLANDO-FL-HARDENED-V2 acquisition router record", determined_by=WORK_ORDER,
                       router_record=record)
        row["corridor"] = h.get("corridor")
        row["brand"] = h.get("brand") or ""
        items.append(row)

    counts = Counter(i["final_state"] for i in items)
    return OrderedDict((
        ("schema", PARTITION.SCHEMA), ("work_order", WORK_ORDER), ("market_id", MARKET_ID), ("as_of", AS_OF),
        ("what_this_is", "Every admitted Orlando V2 census identity in exactly one disposition state, with the order's "
                         "Phase 20 disposition and, for every unresolved row, the acquisition router record."),
        ("count", len(items)),
        ("counts_by_state", OrderedDict(sorted(counts.items()))),
        ("counts_by_disposition", OrderedDict(sorted(Counter(i["disposition"] for i in items).items()))),
        ("resolved", sum(1 for i in items if i["resolved"])),
        ("unresolved", sum(1 for i in items if not i["resolved"])),
        ("items", items),
    ))


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=OUT)
    args = ap.parse_args(argv)
    doc = build()
    issues = PARTITION.validate(doc)
    print("identities :", doc["count"], "resolved", doc["resolved"], "unresolved", doc["unresolved"])
    print("by state   :", dict(doc["counts_by_state"]))
    print("by disp    :", dict(doc["counts_by_disposition"]))
    print("contract   :", len(issues), "issues")
    for i in issues[:8]:
        print("   !", str(i)[:160])
    if issues:
        return 1
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
