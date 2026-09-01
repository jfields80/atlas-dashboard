"""PTF-CLEVELAND-AKRON-CANTON-HARDENED-REVALIDATION-001 -- Phase 7.

Mechanically rebuild the 49 currently-unresolved Cleveland-Akron-Canton rows
from CURRENT state -- the pinned census, the routing shard, the owned-evidence
replay (phase 6), the routing-repair and pass results -- and reclassify each
under the current factory's lanes:

    IDENTITY_REVIEW_FIRST      the identity itself is in question (rename,
                               successor brand, page names another property,
                               non-lodging suspicion)
    ROUTING_REPAIR_FIRST       no first-party property URL, or the route is
                               held / retired / poisoned
    FREE_STATIC_QUALIFIED      routed to a host that serves the policy to a
                               plain client
    FREE_ATTENDED_QUALIFIED    routed to a host that renders client-side but
                               is reachable in an attended browser
    SOURCE_SILENT              the property's own page has been read and says
                               nothing about pets
    OWNED_EVIDENCE_REUSABLE    owned, identity-bound evidence already answers
                               the row and only needs application
    PAID_DISCOVERY_REQUIRED    (assigned by phase 8/14, never here)
    BRIGHTDATA_QUALIFIED       walled brand host where the attended lane
                               already failed
    FOUNDER_HOLD               an ADR forbids the only remaining lane
    OTHER

Historical bucket labels are inputs, never conclusions. Offline; writes one
report; touches no authority.
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

from scripts.pettripfinder.contracts.identity_key import ptf_identity_key  # noqa: E402

WORK_ORDER = "PTF-CLEVELAND-AKRON-CANTON-HARDENED-REVALIDATION-001"
MARKET_ID = "cleveland-akron-canton-oh"
SCHEMA = "ptf-unresolved-rebuild/1.0"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
AUTH = os.path.join(PKG, "markets", "authority", MARKET_ID)
REPORTS = os.path.join(PKG, "markets", "reports")

# Hosts that do NOT serve a usable property page to a plain client (routing
# repair 001 measured these for Cleveland); the policy needs an attended browser.
ATTENDED_HOSTS = ("hilton.com", "marriott.com", "ihg.com", "choicehotels.com", "bestwestern.com",
                  "radissonhotels", "redroof.com", "extendedstayamerica.com", "sonesta.com")
# Walled brand hosts where the paid browser lane is the measured fallback.
BRIGHTDATA_HOSTS = ("marriott.com", "hilton.com")
# Hosts an ADR forbids automating (Kasada interstitial).
ADR_HOLD_HOSTS = ("hyatt.com",)

BRANDS = [
    ("MARRIOTT", r"marriott|courtyard|residence inn|springhill|fairfield|towneplace|ac hotel|aloft|westin|sheraton|le meridien|moxy|element"),
    ("HILTON", r"hilton|hampton|embassy suites|homewood|home2|doubletree|tru by|tapestry|canopy|signia"),
    ("IHG", r"holiday inn|crowne plaza|staybridge|candlewood|even hotel|avid|intercontinental|kimpton|hotel indigo"),
    ("CHOICE", r"comfort inn|comfort suites|quality inn|sleep inn|clarion|cambria|mainstay|suburban|econo lodge|rodeway|woodspring|everhome"),
    ("WYNDHAM", r"wyndham|baymont|days inn|super 8|ramada|travelodge|la quinta|microtel|howard johnson|hawthorn|americinn|trademark"),
    ("ESA", r"extended stay america"), ("BEST_WESTERN", r"best western|surestay"), ("MOTEL6", r"motel 6|studio 6"),
    ("RED_ROOF", r"red roof|hometowne"), ("SONESTA", r"sonesta|simply suites"), ("RADISSON", r"radisson|country inn|park inn"),
    ("INTOWN", r"intown suites"), ("DRURY", r"drury"), ("MY_PLACE", r"my place"), ("HYATT", r"hyatt"), ("MAGNUSON", r"magnuson"),
]


def brand_of(name: str) -> str:
    n = name.lower()
    for fam, rx in BRANDS:
        if re.search(rx, n):
            return fam
    return "INDEPENDENT"


def host_of(url: str) -> str:
    m = re.match(r"https?://([^/]+)", url or "")
    return m.group(1).lower().replace("www.", "") if m else ""


def read_json(path):
    with open(path, "r", encoding="utf-8") as fh:
        return json.load(fh)


def build() -> OrderedDict:
    census = {r["identity_key"]: r for r in read_json(os.path.join(PKG, "identity_census", f"{MARKET_ID}.json"))["hotels"]}
    routing = {r["hotel_ref"]["identity_key"]: r for r in read_json(os.path.join(AUTH, "identity_routing.json"))["routes"]}
    unresolved = read_json(os.path.join(PKG, "cleveland_unresolved_manifest.json"))
    replay = read_json(os.path.join(REPORTS, f"{MARKET_ID.replace('-', '_')}_evidence_replay_006.json"))
    audit = read_json(os.path.join(REPORTS, f"{MARKET_ID.replace('-', '_')}_census_audit_005.json"))
    rr = {r["identity_key"]: r for r in read_json(os.path.join(PKG, "cleveland_routing_repair_001_results.json"))["results"]}
    replay_by_key = {}
    for rec in replay["records"]:
        replay_by_key.setdefault(rec["identity_key"], []).append(rec)
    audit_by_key = {}
    for f in audit["findings"]:
        for k in f["identity_keys"]:
            audit_by_key.setdefault(k, []).append(f)

    rows = []
    for item in unresolved["items"]:
        key = ptf_identity_key(item["canonical_name"])
        crow = census.get(key)
        route = routing.get(key)
        url = (route or {}).get("official_property_url") or item.get("official_url") or (crow or {}).get("official_url") or ""
        route_status = (route or {}).get("status") if route else ("MANIFEST_URL_ONLY" if item.get("official_url") else "NO_ROUTE")
        host = host_of(url)
        fam = brand_of(item["canonical_name"])
        evidence = replay_by_key.get(key, [])
        ev_best = None
        for e in evidence:
            if e["replay"] in ("PET_FRIENDLY_STATED", "NO_PETS_STATED"):
                ev_best = e
                break
        ev_states = sorted({e["replay"] for e in evidence})
        ev_identity_ok = any(e.get("identity", {}).get("confirmed") or (e.get("identity", {}).get("physical_binding") or {}).get("bound") for e in evidence)
        page_named_other = any("IDENTITY_NOT_CONFIRMED_BY_PAGE" in e.get("classification", []) and
                               any("page names" in str(x) for x in ((e.get("identity", {}).get("assessment") or {}).get("reason") or (e.get("identity", {}).get("assessment") or {}).get("reasons") or []))
                               for e in evidence)
        audit_kinds = sorted({f["kind"] for f in audit_by_key.get(key, [])})
        conversion = any(k in ("CONVERSION_OR_RENAME_PENDING", "PRIOR_RENAME_OR_REVIEW_TRACE") for k in audit_kinds) or bool((rr.get(key) or {}).get("rename_proposal"))

        reasons = []
        if conversion or (rr.get(key) or {}).get("census_review_candidate") or "POSSIBLE_NON_LODGING" in audit_kinds or "LODGING_NEEDS_REVIEW" in audit_kinds:
            lane = "IDENTITY_REVIEW_FIRST"
            reasons.append("identity question recorded: " + ", ".join(audit_kinds or ["routing repair rename/review trace"]))
        elif ev_best is not None and ev_identity_ok and not page_named_other:
            lane = "OWNED_EVIDENCE_REUSABLE"
            reasons.append("owned artifact %s reads %s with identity bound" % (ev_best["artifact_file"], ev_best["replay"]))
        elif page_named_other and not url:
            lane = "IDENTITY_REVIEW_FIRST"
            reasons.append("the only owned page names a different property and no route remains")
        elif not url or route_status in ("ROUTING_RETIRED", "ROUTING_HELD"):
            lane = "ROUTING_REPAIR_FIRST"
            reasons.append("no confirmed first-party property URL (route status %s)" % route_status)
        elif any(h in host for h in ADR_HOLD_HOSTS):
            lane = "FOUNDER_HOLD"
            reasons.append("hyatt.com Kasada interstitial; ADR-PTF-AUTOMATED-BROWSING forbids satisfying it -- founder-attended capture only")
        elif evidence and all(e["replay"] in ("SILENT_NO_POLICY_BLOCK", "BLOCK_FOUND_BUT_SILENT", "SERVICE_ANIMAL_LANGUAGE_ONLY") for e in evidence) and ev_identity_ok and fam == "INDEPENDENT":
            lane = "SOURCE_SILENT"
            reasons.append("the property's own page(s) were captured (%d artifact(s)) and say nothing about pets" % len(evidence))
        elif any(h in host for h in BRIGHTDATA_HOSTS) and evidence:
            lane = "BRIGHTDATA_QUALIFIED"
            reasons.append("walled brand host; attended capture already attempted (%s)" % ", ".join(ev_states))
        elif any(h in host for h in ATTENDED_HOSTS):
            lane = "FREE_ATTENDED_QUALIFIED"
            reasons.append("brand host renders client-side or refuses a plain client; attended browser at $0")
        else:
            lane = "FREE_STATIC_QUALIFIED"
            reasons.append("first-party URL on a host that answers a plain client")

        rows.append(OrderedDict([
            ("identity_key", key), ("canonical_name", item["canonical_name"]), ("city", item.get("city")), ("postal_code", item.get("postal_code")),
            ("brand_family", fam), ("in_census", crow is not None),
            ("prior_classification", item["classification"]), ("prior_why", item.get("why_unresolved")),
            ("route_status", route_status), ("url", url), ("host", host),
            ("owned_artifacts", [e["artifact_file"] for e in evidence]), ("owned_replay_states", ev_states),
            ("owned_identity_bound", ev_identity_ok), ("owned_page_names_other_property", page_named_other),
            ("census_audit_findings", audit_kinds),
            ("lane", lane), ("why", reasons),
        ]))

    counts = OrderedDict(sorted(Counter(r["lane"] for r in rows).items()))
    by_prior = OrderedDict()
    for r in rows:
        by_prior.setdefault(r["prior_classification"], Counter())[r["lane"]] += 1
    return OrderedDict([
        ("schema", SCHEMA), ("work_order", WORK_ORDER), ("phase", "7 -- rebuild the 49 current unresolved"),
        ("market_id", MARKET_ID), ("as_of", "2026-09-01"),
        ("what_this_is", "The 49 unresolved rows rebuilt from current state and reclassified under the current factory's lanes. Historical labels are shown beside the new lane but never decide it. PAID_DISCOVERY_REQUIRED is assigned only by phase 8/14 after the free routing lanes are exhausted."),
        ("rows_rebuilt", len(rows)), ("lane_counts", counts),
        ("prior_classification_to_lane", OrderedDict((k, OrderedDict(sorted(v.items()))) for k, v in by_prior.items())),
        ("rows", rows),
    ])


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(REPORTS, f"{MARKET_ID.replace('-', '_')}_unresolved_rebuild_007.json"))
    args = ap.parse_args(argv)
    rep = build()
    with open(args.out, "wb") as fh:
        fh.write((json.dumps(rep, indent=1, ensure_ascii=False, default=str) + "\n").encode("utf-8"))
    print("written", os.path.relpath(args.out, _DASH))
    print("rows", rep["rows_rebuilt"], "lanes:", dict(rep["lane_counts"]))
    for k, v in rep["prior_classification_to_lane"].items():
        print("  ", k, "->", dict(v))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
