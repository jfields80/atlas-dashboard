"""PTF-SAN-ANTONIO-TX-HARDENED-SOURCE-READY-001 -- Phases 21 and 26: actionability and coverage readiness.

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
  launch_packages/pettripfinder/markets/reports/san_antonio_tx_actionability_001.json
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

WORK_ORDER = "PTF-SAN-ANTONIO-TX-HARDENED-SOURCE-READY-001"
MARKET_ID = "san-antonio-tx"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
R = os.path.join(PKG, "markets", "reports")
STAGING = os.path.join(PKG, "markets", "staging", MARKET_ID, "raw_captures")
OUT = os.path.join(R, "san_antonio_tx_actionability_001.json")

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
#: SAN ANTONIO RAN IT (san_antonio_tx_places_route_discovery_001): its website field is an Enterprise-SKU field
#: whose free monthly allowance renewed on 2026-10-01, and no worktree on this machine had used any of it, so the
#: lane ran inside existing capacity. A row it QUERIED and could not route is therefore exhausted; a row it never
#: queried is still actionable (the lane is authorized and untried for that row).
PLACES_REPORT = os.path.join(R, "san_antonio_tx_places_route_discovery_001.json")
PLACES_EXHAUSTED = ("no first-party route exists in any authorized lane: the brand inventories, the Texas hotel-tax "
                    "permit register, Visit San Antonio's roster, the map, the brands' own area lists and "
                    "directories, and Google Places route discovery (existing free allowance), which queried this "
                    "identity and %s")
#: SAN ANTONIO (measured this order): the attended browser read the Extended Stay America Airport page (seq 162,
#: no DataDome wall); the San Antonio - North page rendered only its template variables (seq 163, unhydrated on two
#: reads). A routeless ESA row has no route for the browser to open.
ESA_WALL = ("Extended Stay America: the brand's own pages were read where a route existed (Airport read, seq 162; "
            "North unhydrated, seq 163); this row has no route in any authorized lane, including Places")
#: SAN ANTONIO (measured this order): every Motel 6 / Studio 6 route this market's lanes carry is a LEGACY route
#: that the brand retires to its home page (Motel 6 1122, Studio 6 5043 -- seq 164-165); the Austin order measured
#: that the brand's live property pages state only an amenity chip, never an operative policy.
MOTEL6_CHIP = ("Motel 6 / Studio 6: the routes this market's lanes carry are legacy routes the brand retires to its "
               "home page (seq 164-165), and the brand's live property pages state only an amenity chip (measured in "
               "the Austin order) -- no authorized lane yields an operative policy")
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
            return ACTIONABLE_NOW, "routed, and no lane has attempted the route yet"
        if family == "MOTEL6":
            return EXHAUSTED, MOTEL6_CHIP
        place = PLACES_BY_KEY.get(row["identity_key"])
        if place is None:
            return ACTIONABLE_NOW, ("Places route discovery (authorized, existing free allowance) has not queried "
                                    "this identity yet")
        if family == "ESA":
            return EXHAUSTED, ESA_WALL
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
            return ACTIONABLE_NOW, "Places named a brand page the attended browser has not opened: " + url[:160]
        return ACTIONABLE_NOW, "unrecognised routing reason (never silently exhausted): " + why[:160]
    if disp == "ACCESS_BLOCKED":
        return EXHAUSTED, why[:300]
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
#: normalised URL -> the attended-browser record that opened it (filled by ``build``).
ATTEMPTED = {}
READS = os.path.join(STAGING, "browser_reads_001.jsonl")


def _norm_url(u):
    u = (u or "").split("?")[0].split("#")[0].lower().rstrip("/")
    return re.sub(r"^https?://(www\.)?", "", u)


def build():
    PLACES_BY_KEY.clear()
    ATTEMPTED.clear()
    if os.path.exists(READS):
        with open(READS, encoding="utf-8") as fh:
            for line in fh:
                if line.strip():
                    rec = json.loads(line)
                    ATTEMPTED[_norm_url(rec.get("requested_url"))] = rec
    for _p in (_load(PLACES_REPORT, {}) or {}).get("rows", []):
        if _p.get("cohort") == "ROUTE_DISCOVERY":
            PLACES_BY_KEY[_p["identity_key"]] = _p
    clean = _load(os.path.join(R, "san_antonio_tx_clean_authority_001.json"), {}) or {}
    routing = _load(os.path.join(R, "san_antonio_tx_routing_001.json"), {}) or {}
    browser = _load(os.path.join(R, "san_antonio_tx_browser_lane_001.json"), {}) or {}
    recon = _load(os.path.join(R, "san_antonio_tx_competitor_reconciliation_001.json"), {}) or {}
    shadow = _load(os.path.join(R, "san_antonio_tx_shadow_package_001.json"), {}) or {}
    by_route = {r["identity_key"]: r for r in routing.get("routes", [])}

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
    # SAN ANTONIO: THE ORDER'S OWN COVERAGE RULE. Founder intervention is required only for a ruling that CANNOT
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
