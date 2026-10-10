"""PTF-DALLAS-FORT-WORTH-TX-HARDENED-SOURCE-READY-001 -- Phases 21 and 26: actionability and coverage readiness.

UNRESOLVED IS NOT ACTIONABLE. A large, bounded, fully-explained unresolved cohort is allowed; what is NOT
allowed is a row this order could still have resolved with an authorized lane and did not. So EVERY unresolved
ROW (not every disposition) is assigned exactly one class, from its own hold reason, its own route and its own
brand family:

  ACTIONABLE_NOW              an authorized lane remains untried for this row
  AUTHORIZED_ROUTER_EXHAUSTED every rung the committed route table and the supported browser open for this row
                              was exercised, and the row's own evidence is what it is
  REQUIRES_NEW_PROVIDER       only a provider this order has no authorization for could reach it
  REQUIRES_NEW_SPEND          only new paid capacity could reach it
  REQUIRES_FOUNDER            only a founder decision (a shared document, a business rule) can move it

WHY THIS IS PER-ROW. The port this module replaced bucketed whole dispositions, so a row the router had just
routed and no lane had yet attempted ("routed but no acquisition lane in this order attempted the page yet")
was counted AUTHORIZED_ROUTER_EXHAUSTED with every other ROUTING_HOLD. That is exactly the row the order forbids
hiding. Here the reason text decides, and an unrecognised reason falls to ACTIONABLE_NOW -- never the other way.

COVERAGE READY is then decided mechanically: YES only when nothing is actionable and nothing needs a founder or
new spend to reach; FOUNDER DECISION when nothing is actionable but a material cohort is reachable only through
new spend or a founder ruling; NO while anything is actionable.

Reads only committed reports. Nothing fetches, spends, registers, authorizes or deploys.

Output:
  launch_packages/pettripfinder/markets/reports/dallas_fort_worth_tx_actionability_001.json
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

WORK_ORDER = "PTF-DALLAS-FORT-WORTH-TX-HARDENED-SOURCE-READY-001"
MARKET_ID = "dallas-fort-worth-tx"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
R = os.path.join(PKG, "markets", "reports")
STAGING = os.path.join(PKG, "markets", "staging", MARKET_ID, "raw_captures")
OUT = os.path.join(R, "dallas_fort_worth_tx_actionability_001.json")

ACTIONABLE_NOW = "ACTIONABLE_NOW"
EXHAUSTED = "AUTHORIZED_ROUTER_EXHAUSTED"
NEW_PROVIDER = "REQUIRES_NEW_PROVIDER"
NEW_SPEND = "REQUIRES_NEW_SPEND"
FOUNDER = "REQUIRES_FOUNDER"
#: A hotel whose own first-party page or name states it has not opened (the Denver pre-authorization correction
#: 003 ruling, carried into this order's own Phase rule: PREOPENING PUBLISHED = 0, never verified-no-pets). No lane,
#: spend or ruling reaches it today -- only its opening does, after which its policy is revalidated.
PREOPENING = "HELD_UNTIL_OPENING"
CLASSES = (ACTIONABLE_NOW, EXHAUSTED, NEW_PROVIDER, NEW_SPEND, FOUNDER, PREOPENING)

#: Places route discovery is the ONLY lane that finds a website for a row no brand roster, bureau or map links.
#: DALLAS-FORT WORTH RAN IT (dallas_fort_worth_tx_places_route_discovery_001, inside the renewed free monthly allowance;
#: existing capacity, no new spend). A row it QUERIED and could not route is therefore exhausted; a row it never
#: queried is still actionable (the lane is authorized and untried for that row).
PLACES_REPORT = os.path.join(R, "dallas_fort_worth_tx_places_route_discovery_001.json")
PLACES_EXHAUSTED = ("no first-party route exists in any authorized lane: the brand inventories, the Metroplex bureaus' "
                    "lodging rosters, the Texas hotel-tax permit register (which names a taxpayer and premises, never "
                    "a website), the map, the brands' own city directories read in the attended "
                    "browser, and Google Places route discovery (existing free allowance), which queried this "
                    "identity and %s")
#: The attended browser's own outcomes that end a row's acquisition -- the property's or brand's own
#: page was reached (or the brand's own directory was read) and what it states is final for this order.
BROWSER_TERMINAL = {
    "NO_PET_STATEMENT_ON_OWN_SITE": "the property's own site was read in the attended browser and states no pet policy "
                                    "anywhere reachable (silence is never a refusal)",
    "NOT_LISTED_BY_BRAND_OWN_DIRECTORY": "the brand's own city directory, read in the attended browser, does not list "
                                         "this building -- the brand has left it and its current operator is unproven",
    "NOT_LISTED_BY_OPERATOR_OWN_DIRECTORY": "the operator's own lodging directory does not list a premises by this name",
    "ROUTE_RETIRED_REDIRECTS_TO_BRAND_SEARCH": "the brand's own property route is retired (it redirects to the brand's "
                                               "search, which does not list the building)",
    "SERVER_ERROR_PAGE": "the operator's own page answered a server error on two attended attempts; not retried "
                         "further (no hammering, no bypass)",
    "NAVIGATION_FAILED": "the property's own route answers an error page or a 404 in the attended browser",
    "NO_CONTENT_SITE_IN_PROGRESS": "the property's own domain shows only 'Website In Progress'",
    "NO_CONTENT_BLANK_PAGE": "the property's own site renders an empty page in the attended browser",
    "NO_OPERATIVE_STATEMENT": "the brand's own page states only a conditional ('Pets may be accepted. Please contact "
                              "the hotel'), never an acceptance or a refusal",
    "READ": "the attended browser read the property's own page",
    # the labels this order's recorder writes (browser_protocol vocabulary).
    "IDENTITY_BOUND_POLICY_SOURCE_SILENT": "the property's own site was read in the attended browser, bound these "
                                           "premises on its own address, and states no pet policy anywhere reachable "
                                           "(silence is never a refusal)",
    "ROUTE_BOUND_POLICY_SOURCE_SILENT": "the property's own site (the census route) was read in the attended browser and "
                                        "states no pet policy anywhere reachable; it prints no street address",
    "AMENITY_CHIP_ONLY_NOT_OPERATIVE": "the property's own page carries only an amenity label ('Pet friendly'), which "
                                       "states no policy and is never acceptance",
    "UNIT_LISTING_HOUSE_RULE_ONLY": "the site lists individual rental units and the only pet wording is one unit "
                                    "listing's house rule -- never a property-wide policy",
    "OPERATOR_STATUS_PAGE_NO_PREMISES": "the operator's own page was read for operating status; it binds no premises",
    "PAGE_PRINTS_NO_PREMISES_ADDRESS": "the brand's own page prints no house number or ZIP, so it can never bind these "
                                       "premises",
    "ROUTE_RETIRED_REDIRECTS_TO_BRAND_HOME": "the brand's own property route redirects to the brand home page: the "
                                             "brand no longer lists the property",
    "CLOSURE_STATED_BY_OPERATOR": "the operator's own page states the property is closed",
    "NO_PROPERTY_PAGE_ROUTE_LANDS_ON_BRAND_SEARCH": "the brand's own property route lands on its search / home page: "
                                                    "the brand publishes no property page for these premises",
    "NAVIGATION_FAILED_ERROR_PAGE": "the property's own route answers an error page or a 404 in the attended browser",
    "CHALLENGE_DENIED_AKAMAI_ACCESS_DENIED": "the brand answered the attended browser with an anti-bot denial across "
                                             "paced windows; never bypassed",
    "CHALLENGE_DENIED_DATADOME_CAPTCHA": "the brand served a CAPTCHA to the attended browser; never solved or bypassed",
    "REJECTED_OUT_OF_MARKET_PAGE_ADDRESS": "the page's own address is outside the admitted geography",
    "IDENTITY_READ_ROW_EXCLUDED_AS_TIMESHARE": "the brand's own page names these premises a vacation-ownership resort",
    "IDENTITY_NOT_CONFIRMED": "the only website any authorized lane names for this row is not the property's own (a "
                              "third-party booking template, a lapsed domain now serving another business, or a "
                              "font/CDN host); it never states this property's policy",
}
#: AUSTIN: a REFUSAL the property's own page states and this order read as a refusal, which the SHARED reader
#: (first_party_binding.classify_quote, FAST rule C) cannot interpret -- "No pets allowed in this property", "we
#: are unfortunately unable to accommodate pets", "pets (including ESAs) are not permitted" behind an FAQ question.
#: Only a change to that shared module publishes these; this order may not make it. REQUIRES_FOUNDER.
SHARED_READER_REFUSAL = ("the property's own page states a refusal this order read as one, but the SHARED reader "
                         "FAST rule C re-runs cannot interpret it (a shared-factory change this order may not make); "
                         "held, never published -- ")


#: The shared reader's "the quote accepts pets" verdict when the only acceptance words sit in an FAQ QUESTION
#: ("'Are pets allowed? | ... are not permitted'") -- the Kalahari shape.
_QUESTION_ONLY_ACCEPT = re.compile(r"the quote accepts pets: '(?:Are|Is|Can|Do|Does)\b[^?']{0,120}\?", re.I)
#: ...and the quote refuses pets at the PROPERTY, not in one of its areas: Hotel ZaZa's "pets are not permitted in
#: our restaurants or pool" is an area rule beside an acceptance, never a refusal of the stay.
_WHOLE_PROPERTY_REFUSAL = re.compile(r"\bnot\s+(?:allowed|accepted|permitted)\b(?!\s+(?:in|inside|on|at)\s+(?:our|the|any)\b)",
                                     re.I)


def _load(path, default=None):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


def _attempted_route(row, route):
    """DALLAS-FORT WORTH: the attended browser's own record for the row's OWN route (the routing route, or the website
    Places bound at the row's own house number and ZIP), when that read reached a terminal outcome but bound no
    premises (an independent's site printing no address, a third-party template, a retired brand route). The row is
    exhausted on that record -- the authorized browser opened its only route -- never left looking untried."""
    urls = [(route or {}).get("url") or ""]
    place = PLACES_BY_KEY.get(row["identity_key"]) or {}
    if place.get("bound"):
        urls.append((place.get("place") or {}).get("website_uri") or "")
    for u in urls:
        rd = ATTEMPTED.get(_norm_url(u)) if u else None
        if not rd:
            continue
        oc = rd.get("read_outcome") or ""
        if oc == "READ":
            return ("the attended browser read the row's own route (seq %s, %s), but the page's own address line (%r) "
                    "does not bind these premises (no house number / ZIP, or a different building), so its quote is "
                    "never attributed to this row -- %s" % (rd.get("seq"), u.split("?")[0][:120],
                                                          rd.get("page_address_line"), (rd.get("note") or "")[:160]))
        if oc in BROWSER_TERMINAL:
            return "%s (attended browser seq %s, %s): %s" % (BROWSER_TERMINAL[oc], rd.get("seq"), u.split("?")[0][:120],
                                                            (rd.get("note") or "")[:200])
    return ""


#: Brand hosts whose own property pages the attended browser reads (the routing table's url or alternate routes).
_BRAND_HOST = re.compile(r"^(?:marriott|hilton|ihg|hyatt|choicehotels|wyndhamhotels|bestwestern|motel6|redroof|sonesta|"
                         r"extendedstayamerica|druryhotels|omnihotels|loewshotels|radissonhotels|woodspring)\.com/")


def _untried_brand_route(route):
    """DALLAS-FORT WORTH: a brand's own property route (the routing url or an alternate route, e.g. the Marriott
    inventory's marriott.com/<code>) the attended browser has never opened. Such a row is ACTIONABLE -- never
    'new spend' because a Places lookup is spent while an authorized route sits untried."""
    for u in [(route or {}).get("url")] + list((route or {}).get("alternate_routes") or []):
        n = _norm_url(u)
        if n and _BRAND_HOST.match(n) and n not in ATTEMPTED:
            return u
    return ""


def classify(row, route):
    """(class, why) for one unresolved clean-authority row."""
    disp = row["disposition"]
    why = row.get("hold_reason") or ""
    family = (route or {}).get("brand_family") or ""
    state = (route or {}).get("routing_state") or ""
    if disp == "BROWSER_CAPTURE_NEEDED":
        return ACTIONABLE_NOW, "a brand page the attended browser has not yet read"
    if disp == "ROUTING_HOLD":
        if why.startswith("routed but no acquisition lane"):
            tried = _attempted_route(row, route)
            if tried:
                return EXHAUSTED, tried
            if _norm_url((route or {}).get("url")).startswith("marriott.com/") and MARRIOTT_WINDOW_CLOSED:
                return EXHAUSTED, MARRIOTT_WINDOW_CLOSED + " (" + route["url"].split("?")[0][:160] + ")"
            return ACTIONABLE_NOW, "routed, and no lane has attempted the route yet"
        untried = _untried_brand_route(route)
        if untried and _norm_url(untried).startswith("marriott.com/") and MARRIOTT_WINDOW_CLOSED:
            return EXHAUSTED, MARRIOTT_WINDOW_CLOSED + " (" + untried.split("?")[0][:160] + ")"
        if untried:
            return ACTIONABLE_NOW, ("the brand's own property route has not been opened by the attended browser: "
                                    + untried.split("?")[0][:160])
        place = PLACES_BY_KEY.get(row["identity_key"])
        if place is None and PLACES_ALLOWANCE_SPENT:
            # the free Enterprise allowance this order may use is spent (the places module's own cap: 990 of the
            # ~1,000 free requests this month); one more website lookup is NEW paid spend, which needs the founder.
            return NEW_SPEND, ("no authorized free lane routes this row, and Places route discovery's free monthly "
                               "Enterprise allowance is spent (%s of the %s requests this order may make, with the "
                               "earlier orders' 775 this month); a website lookup for it is new paid spend"
                               % (PLACES_DOC.get("enterprise_requests_made"), PLACES_DOC.get("route_discovery_cap")))
        if place is None:
            return ACTIONABLE_NOW, ("Places route discovery (authorized, existing free allowance) has not queried "
                                    "this identity yet")
        if place.get("error"):
            found = "answered %s" % place["error"]
        elif not place.get("bound"):
            found = ("returned no place at this row's own house number and ZIP (%d candidates)"
                     % int(place.get("candidates_returned") or 0))
        elif not (place.get("place") or {}).get("website_uri"):
            found = "bound a place at this row's own address that lists no website"
        else:
            found = ("bound a place whose website (%s) is a brand or directory host or never stated this row's own "
                     "address" % place["place"]["website_uri"][:90])
        if why.startswith(("RETIRED_BRAND_ROUTE", "the route the census carries served an error page",
                           "the brand's own property-code route lands", "the census routes this identity to a brand HOME")):
            return EXHAUSTED, why.split(" (")[0] + "; " + PLACES_EXHAUSTED % found
        if why.startswith("routing state") or "NO_OFFICIAL_WEB_PRESENCE" in why:
            return EXHAUSTED, PLACES_EXHAUSTED % found
        if why.startswith("NOT_FIRST_PARTY_SITE"):
            return EXHAUSTED, why.split(" -- ")[0] + "; " + PLACES_EXHAUSTED % found
        if why.startswith("OTHER_EXPLICIT_REASON"):
            # Places named a BRAND, booking or social page for this row. The brand page is read in the attended
            # browser like any brand route; a social or third-party booking page is never a first-party policy.
            m = re.search(r"\((https?://[^)\s]+)", why)
            url = m.group(1) if m else ""
            read = ATTEMPTED.get(_norm_url(url))
            if read:
                return EXHAUSTED, ("Places named %s; the attended browser opened it (seq %s): %s -- %s"
                                   % (url.split("?")[0], read["seq"], read["read_outcome"], (read.get("note") or "")[:200]))
            if re.search(r"(facebook|instagram|oyorooms|booking|expedia|tripadvisor|airbnb|vrbo)\.com", url, re.I):
                return EXHAUSTED, ("Places named only a social or third-party booking page (%s), never a first-party "
                                   "policy source; no other authorized lane routes this row" % url.split("?")[0])
            if _norm_url(url).startswith("marriott.com/") and MARRIOTT_WINDOW_CLOSED:
                return EXHAUSTED, MARRIOTT_WINDOW_CLOSED + " (Places named " + url.split("?")[0][:160] + ")"
            return ACTIONABLE_NOW, "Places named a brand page the attended browser has not opened: " + url[:160]
        return ACTIONABLE_NOW, "unrecognised routing reason (never silently exhausted): " + why[:160]
    if disp in ("ACCESS_BLOCKED", "IDENTITY_MISMATCH_HOLD", "SOURCE_SILENT") and BOUND_READS.get(row["identity_key"]):
        # the attended browser's OWN outcome for this identity decides -- never the static lane's.
        rd = BOUND_READS[row["identity_key"]][-1]
        oc = rd.get("outcome") or ""
        if oc in BROWSER_TERMINAL and oc != "READ":
            return EXHAUSTED, "%s (attended browser seq %s, %s): %s" % (
                BROWSER_TERMINAL[oc], rd.get("seq"), (rd.get("requested_url") or "")[:120], (rd.get("note") or "")[:200])
        if oc == "READ" and disp == "ACCESS_BLOCKED":
            return EXHAUSTED, ("the attended browser read the brand's own page (seq %s) and bound it to this row, but the "
                               "adjudication holds it: %s" % (rd.get("seq"), why[:200]))
    if disp == "ACCESS_BLOCKED":
        if UNBOUND_BY_KEY.get(row["identity_key"]):
            rd = UNBOUND_BY_KEY[row["identity_key"]]
            oc = rd.get("outcome") or ""
            if oc in BROWSER_TERMINAL and oc != "READ":
                return EXHAUSTED, "%s (attended browser seq %s, %s): %s" % (
                    BROWSER_TERMINAL[oc], rd.get("seq"), (rd.get("requested_url") or "")[:120],
                    (rd.get("note") or "")[:200])
            return EXHAUSTED, ("the attended browser read the property's own page (seq %s), but the page's own address "
                               "line (%r) contradicts this row's census address, so the read is never bound and the row "
                               "is held on the conflict -- %s" % (rd.get("seq"), rd.get("page_address_line"),
                                                                    (rd.get("note") or "")[:160]))
        tried = _attempted_route(row, route)
        if tried:
            return EXHAUSTED, tried
        if "MARRIOTT_AUTHORIZED_WINDOW_CLOSED" in why:
            # the clean authority's own measured blocker: the order's one authorized Marriott window is spent.
            return EXHAUSTED, why[:400]
        return ACTIONABLE_NOW, ("the static lane was refused and the attended browser (authorized) has not opened this "
                                "row's own page: " + why[:200])
    if disp == "SOURCE_SILENT":
        return EXHAUSTED, ("the property's own page served, bound, and states no operative pet policy; silence "
                           "is never a refusal, and only the operator publishing a policy changes it")
    if disp in ("EVIDENCE_HOLD", "NEGATION_HOLD"):
        if why.startswith("PREOPENING_NOT_YET_OPEN"):
            return PREOPENING, ("nonpublishing until the hotel opens and its first-party policy is revalidated "
                                "(PREOPENING PUBLISHED = 0) -- " + why[:200])
        if "ROUTE_DOMAIN_CONFLICT" in why:
            return FOUNDER, ("two first-party routes for one premises; which one the package cites is a routing "
                             "ruling -- " + why[:200])
        if ("no refusal the reader will interpret" in why
                or ("QUOTE_CONTRADICTS_CLAIM (the quote accepts pets:" in why and _QUESTION_ONLY_ACCEPT.search(why)
                    and _WHOLE_PROPERTY_REFUSAL.search(why))):
            return FOUNDER, SHARED_READER_REFUSAL + why[:200]
        return EXHAUSTED, ("the first-party evidence was read and is not publishable as stated (conditional, "
                           "fee/weight-only, chip-only, or the shared reader disagrees); no further acquisition "
                           "changes the page's own wording -- " + why[:200])
    if disp == "IDENTITY_MISMATCH_HOLD":
        if why.startswith("SAME PREMISES, TWO IDENTITIES"):
            return FOUNDER, ("a dual-brand building is TWO hotels, each proved by its own brand code and page; "
                             "publishing them needs a same_campus_distinct_entity row in the SHARED "
                             "identity_resolutions.json, which this order may not write")
        if why.startswith("SITE TITLE COLLISION"):
            return FOUNDER, ("two first-party names share the site's 60-character title; which display name each "
                             "carries is a founder naming decision -- " + why[:200])
        return EXHAUSTED, why[:300]
    return ACTIONABLE_NOW, "unrecognised disposition (never silently exhausted): " + disp


#: identity_key -> the Places route-discovery row that queried it (filled by ``build``).
PLACES_BY_KEY = {}
#: the Places report itself, and whether this order's Enterprise cap (its share of the free allowance) is reached.
PLACES_DOC = {}
PLACES_ALLOWANCE_SPENT = False
#: identity_key -> the attended-browser lane rows BOUND to it, in sequence (filled by ``build``).
BOUND_READS = {}
#: identity_key -> an attended read of the row's own page that could NOT be bound because the page's own address
#: contradicts the row's (filled by ``build`` from UNBOUND_READS_BY_ROW below).
UNBOUND_BY_KEY = {}
#: The attended reads this order opened FOR a census row that the browser lane's own binder left unbound, keyed by
#: the recorded property code -> census identity key. Filled only from THIS order's own log (never inherited).
UNBOUND_READS_BY_ROW = {
}
#: normalised URL -> the attended-browser record that opened it (filled by ``build``).
ATTEMPTED = {}
#: The clean authority's measured Marriott blocker (its ``marriott_window_closed``), "" while the lane is open.
MARRIOTT_WINDOW_CLOSED = ""
READS = os.path.join(STAGING, "browser_reads_001.jsonl")


def _norm_url(u):
    u = (u or "").split("?")[0].split("#")[0].lower().rstrip("/")
    return re.sub(r"^https?://(www\.)?", "", u)


def build():
    PLACES_BY_KEY.clear()
    ATTEMPTED.clear()
    BOUND_READS.clear()
    UNBOUND_BY_KEY.clear()
    if os.path.exists(READS):
        with open(READS, encoding="utf-8") as fh:
            for line in fh:
                if line.strip():
                    rec = json.loads(line)
                    ATTEMPTED[_norm_url(rec.get("requested_url"))] = rec
    global PLACES_ALLOWANCE_SPENT, MARRIOTT_WINDOW_CLOSED
    from scripts.pettripfinder.dallas_fort_worth_tx_clean_authority_001 import marriott_window_closed
    MARRIOTT_WINDOW_CLOSED = marriott_window_closed()
    PLACES_DOC.clear()
    PLACES_DOC.update(_load(PLACES_REPORT, {}) or {})
    PLACES_ALLOWANCE_SPENT = (int(PLACES_DOC.get("enterprise_requests_made") or 0)
                              >= int(PLACES_DOC.get("route_discovery_cap") or 10 ** 9))
    for _p in PLACES_DOC.get("rows", []):
        if _p.get("cohort") == "ROUTE_DISCOVERY":
            PLACES_BY_KEY[_p["identity_key"]] = _p
    clean = _load(os.path.join(R, "dallas_fort_worth_tx_clean_authority_001.json"), {}) or {}
    routing = _load(os.path.join(R, "dallas_fort_worth_tx_routing_001.json"), {}) or {}
    browser = _load(os.path.join(R, "dallas_fort_worth_tx_browser_lane_001.json"), {}) or {}
    recon = _load(os.path.join(R, "dallas_fort_worth_tx_competitor_reconciliation_001.json"), {}) or {}
    shadow = _load(os.path.join(R, "dallas_fort_worth_tx_shadow_package_001.json"), {}) or {}
    by_route = {r["identity_key"]: r for r in routing.get("routes", [])}
    for b in browser.get("rows", []):
        if b.get("identity_key"):
            BOUND_READS.setdefault(b["identity_key"], []).append(b)
        elif b.get("property_code") in UNBOUND_READS_BY_ROW:
            UNBOUND_BY_KEY[UNBOUND_READS_BY_ROW[b["property_code"]]] = b

    rows = clean.get("rows", [])
    unresolved = [r for r in rows if r["disposition"] not in ("CLEAN_PET_FRIENDLY", "CLEAN_VERIFIED_NO_PETS")]
    per_row = []
    for r in unresolved:
        cls, why = classify(r, by_route.get(r["identity_key"]))
        rt = by_route.get(r["identity_key"]) or {}
        per_row.append(OrderedDict([
            ("identity_key", r["identity_key"]), ("canonical_name", r["canonical_name"]),
            ("corridor", r.get("corridor", "")), ("brand_family", rt.get("brand_family") or ""),
            ("disposition", r["disposition"]), ("actionability", cls), ("why", why),
        ]))
    per_row.sort(key=lambda x: (x["actionability"], x["disposition"], x["identity_key"]))

    table = OrderedDict()
    for disp in sorted({x["disposition"] for x in per_row}):
        c = Counter(x["actionability"] for x in per_row if x["disposition"] == disp)
        table[disp] = OrderedDict([("total", sum(c.values()))] + [(k.lower(), c.get(k, 0)) for k in CLASSES])
    totals = Counter(x["actionability"] for x in per_row)
    actionable_total = totals.get(ACTIONABLE_NOW, 0)

    marriott_open = sum(1 for x in per_row if x["brand_family"] == "MARRIOTT" and x["actionability"] == ACTIONABLE_NOW)
    browser_open = sum(1 for x in per_row if x["disposition"] == "BROWSER_CAPTURE_NEEDED")
    fast = shadow.get("fast_rules") or {}
    conditions = OrderedDict([
        ("actionable_unresolved_is_zero", actionable_total == 0),
        ("no_material_identity_gap", not recon.get("material_unexplained_gap", False)),
        ("no_material_unexplained_policy_gap", all(x["why"] for x in per_row)),
        ("authorized_acquisition_lanes_exhausted", actionable_total == 0),
        ("marriott_queue_terminally_resolved_or_exhausted", marriott_open == 0),
        ("browser_required_brands_processed_or_bounded", browser_open == 0),
        ("publication_set_safe", int((clean.get("counts") or {}).get("CLEAN_PET_FRIENDLY", 0)) > 0),
        ("package_deterministic_and_fast_clean",
         bool(shadow.get("PACKAGE_REPRODUCIBLE_IN_PROCESS")) and bool(fast)
         and all(v == "PASS" for v in fast.values())),
    ])
    # THE ORDER'S OWN COVERAGE RULE (carried from San Antonio, restated by this order). Founder intervention is required only for a ruling that CANNOT
    # safely remain held, and the order lists "dual-brand / shared-campus rows safely held if unresolved" and
    # "preopening rows safely excluded" among the COVERAGE READY = YES conditions, and tells a novel refusal the
    # shared reader cannot interpret to be "held safely". A founder row of one of those kinds is therefore a SAFE
    # HOLD (reported, never published) and does not gate coverage; only new spend, a new provider, or a founder
    # ruling that cannot safely wait would.
    safe_founder = sum(1 for x in per_row if x["actionability"] == FOUNDER and (
        x["why"].startswith("a dual-brand building is TWO hotels") or x["why"].startswith(SHARED_READER_REFUSAL)))
    gated = (totals.get(NEW_SPEND, 0) + totals.get(NEW_PROVIDER, 0) + totals.get(FOUNDER, 0) - safe_founder)
    if actionable_total:
        coverage = "NO"
    elif gated:
        coverage = "FOUNDER DECISION"
    else:
        coverage = "YES" if all(conditions.values()) else "NO"

    return OrderedDict([
        ("schema", "ptf-market-actionability/2.0"),
        ("work_order", WORK_ORDER),
        ("market_id", MARKET_ID),
        ("phase", "21 + 26 -- actionability of every unresolved ROW, and the coverage decision"),
        ("unresolved_is_not_actionable",
         "A large, bounded, fully-explained unresolved cohort is allowed. What is not allowed is a row an "
         "authorized lane could still reach. ACTIONABLE UNRESOLVED must be 0 before COVERAGE READY = YES."),
        ("census_total", len(rows)),
        ("resolved", len(rows) - len(unresolved)),
        ("unresolved_total", len(unresolved)),
        ("totals_by_class", OrderedDict((k, totals.get(k, 0)) for k in CLASSES)),
        ("by_disposition", table),
        ("actionable_unresolved_remaining", actionable_total),
        ("rows_gated_on_new_spend_provider_or_founder", gated),
        ("founder_rows_safely_held", safe_founder),
        ("preopening_rows_safely_excluded", totals.get(PREOPENING, 0)),
        ("places_note", "Google Places route discovery ran inside the renewed free monthly allowance (existing "
                        "capacity, no new spend); a row it queried and could not route is exhausted, a row it "
                        "never queried is actionable"),
        ("attended_browser", OrderedDict([
            ("attempts", browser.get("attempts")), ("reads", browser.get("reads")),
            ("challenge_denied", browser.get("challenge_denied")), ("unbound", browser.get("unbound")),
            ("paid_provider_calls", browser.get("paid_provider_calls")),
            ("akamai_bypassed", browser.get("akamai_bypassed")),
            ("browser_js_exfiltration_used", browser.get("browser_js_exfiltration_used")),
            ("local_relay_used", browser.get("local_relay_used")),
        ])),
        ("coverage_conditions", conditions),
        ("COVERAGE_READY", coverage),
        ("TECHNICAL_SOURCE_READY", "YES" if conditions["package_deterministic_and_fast_clean"] else "NO"),
        ("rows", per_row),
    ])


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=OUT)
    args = ap.parse_args(argv)
    doc = build()
    os.makedirs(os.path.dirname(args.out), exist_ok=True)
    with open(args.out, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    print("unresolved", doc["unresolved_total"], "actionable", doc["actionable_unresolved_remaining"])
    print("by class:", json.dumps(doc["totals_by_class"]))
    for k, v in doc["by_disposition"].items():
        print("  %-24s %s" % (k, json.dumps(v)))
    for x in doc["rows"]:
        if x["actionability"] == ACTIONABLE_NOW:
            print("  ACTIONABLE:", x["canonical_name"], "|", x["why"][:120])
    print("conditions:", json.dumps(doc["coverage_conditions"]))
    print("TECHNICAL SOURCE READY =", doc["TECHNICAL_SOURCE_READY"], "| COVERAGE READY =", doc["COVERAGE_READY"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
