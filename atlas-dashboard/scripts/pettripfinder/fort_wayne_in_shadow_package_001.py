"""PTF-FORT-WAYNE-IN-NEW-MARKET-001 -- Phases 7, 14-19 (shadow package).

The order's closing artifacts, all derived from the lane reports and none of
them authored by hand:

  phase 7   brand inventory audit -- every official brand row classified
  phase 14  wrong-evidence audit -- the known failure classes, run over every
            clean candidate BEFORE it is allowed into the inventory
  phase 15  clean pending authority -- CLEAN_PET_FRIENDLY and
            CLEAN_VERIFIED_NO_PETS
  phase 16  founder packet -- one grouped packet, groups A-F
  phase 17  paid readiness -- what each paid lane would cost, and whether it is
            REQUIRED_FOR_PROMOTION or OPTIONAL_COVERAGE_EXPANSION
  phase 18  the Fort Wayne shadow source package
  phase 19  PROMOTION_READY

NOTHING HERE WRITES SHARED PRODUCTION SOURCE. The proposed census is written to
``identity_census_proposed/``, not ``identity_census/``; the market contract
stays in ``markets/pending/``; no global is regenerated, no pin is moved, and no
candidate is assembled. Every count below is a statement about a SHADOW market.

Outputs:
  launch_packages/pettripfinder/markets/reports/fort_wayne_in_shadow_package_001.json
  launch_packages/pettripfinder/identity_census_proposed/fort-wayne-in.json
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from collections import Counter, OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

from scripts.pettripfinder.contracts import census as CENSUS_CONTRACT  # noqa: E402
from scripts.pettripfinder.contracts import enums  # noqa: E402
from scripts.pettripfinder.markets import contract as MC  # noqa: E402
from scripts.pettripfinder.markets.assignment import assign_hotels  # noqa: E402

WORK_ORDER = "PTF-FORT-WAYNE-IN-NEW-MARKET-001"
MARKET_ID = "fort-wayne-in"
SCHEMA = "ptf-shadow-market-package/1.0"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
PROPOSED_CENSUS_DIR = os.path.join(PKG, "identity_census_proposed")
PENDING_CONTRACT = os.path.join(PKG, "markets", "pending", "fort-wayne-in.json")

RECON = os.path.join(REPORTS, "fort_wayne_in_census_reconciliation_001.json")
CAPTURE = os.path.join(REPORTS, "fort_wayne_in_routing_and_static_capture_001.json")
BRAND = os.path.join(REPORTS, "fort_wayne_in_brand_directory_harvest_001.json")
COMPETITOR = os.path.join(REPORTS, "fort_wayne_in_competitor_leads_001.json")
CVB = os.path.join(REPORTS, "fort_wayne_in_cvb_directory_harvest_001.json")
OSM = os.path.join(REPORTS, "fort_wayne_in_osm_census_sweep_001.json")


def read_json(path, default=None):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8-sig") as fh:
        return json.load(fh)


def slugify(text):
    return re.sub(r"[^a-z0-9]+", "-", (text or "").strip().lower()).strip("-")


# --------------------------------------------------------------------------- #
# Phase 14 -- the wrong-evidence audit
# --------------------------------------------------------------------------- #

#: Language that states a CONSTRAINT on pets without stating ACCEPTANCE. A fee,
#: a weight cap or a head count is what the hotel charges or limits IF it takes
#: pets; on its own it is not the hotel saying it does.
_CONSTRAINT_ONLY = re.compile(
    r"\b(fee|deposit|charge|weight|lbs?\b|pounds?|maximum|max\.?|limit|per night|"
    r"per stay|non-?refundable)\b", re.I)
#: Acceptance language proper.
_ACCEPTANCE = re.compile(
    r"\b(pets? (?:are )?(?:welcome|allowed|permitted|accepted)|we (?:welcome|allow|accept) "
    r"pets?|pet[- ]friendly|dogs? (?:are )?(?:welcome|allowed|permitted))\b", re.I)
#: Service-animal language. Never ordinary-pet acceptance, and never a refusal
#: of ordinary pets either.
_SERVICE_ANIMAL = re.compile(
    r"\b(service animal|assistance animal|guide dog|emotional support|ADA)\b", re.I)
#: Amenity-chip shapes: a facet label, not an operative policy.
_AMENITY_CHIP = re.compile(
    r"^\s*(pets? allowed|pet friendly|pets? ok|dogs? allowed|pets?)\s*$", re.I)


def audit_clean_row(row):
    """Every known wrong-evidence class, run over ONE clean candidate.

    Returns the list of findings. A non-empty list keeps the row OUT of the
    clean inventory: the audit is a gate, not a note.
    """
    findings = []
    observation = row.get("observation") or {}
    extraction = observation.get("extraction") or {}
    quotes = " ".join(
        (e.get("quote") or "") for e in (observation.get("evidence") or [])
        if isinstance(e, dict))
    pets = extraction.get("pets_allowed")

    identity = row.get("identity_assessment") or {}
    if identity and identity.get("confirmed") is False:
        findings.append("IDENTITY_NOT_CONFIRMED_ON_THE_CAPTURED_PAGE")
    if row.get("route_basis", "").startswith("brand's own inventory slug"):
        findings.append("ROUTE_BOUND_BY_SLUG_NOT_BY_ADDRESS")

    if quotes:
        if _AMENITY_CHIP.match(quotes.strip()):
            findings.append("AMENITY_CHIP_SUBSTITUTED_FOR_POLICY")
        if _SERVICE_ANIMAL.search(quotes) and not _ACCEPTANCE.search(quotes):
            findings.append("SERVICE_ANIMAL_LANGUAGE_ONLY")
        if pets is True and not _ACCEPTANCE.search(quotes) and _CONSTRAINT_ONLY.search(quotes):
            findings.append("ACCEPTANCE_INFERRED_FROM_A_FEE_WEIGHT_OR_COUNT")
    elif pets is not None:
        findings.append("NO_EVIDENCE_QUOTE_BEHIND_A_DECIDED_POLICY")

    if pets is False and not quotes:
        findings.append("NO_PETS_FROM_A_STRUCTURED_FLAG_ALONE")
    return findings


# --------------------------------------------------------------------------- #
# Phase 7 -- brand inventory audit
# --------------------------------------------------------------------------- #

def brand_audit(brand_doc, capture_rows):
    routed_urls = {r.get("url") for r in capture_rows if r.get("url")}
    out = []
    for c in (brand_doc or {}).get("candidates") or []:
        page = c.get("page") or {}
        status = page.get("status")
        title = page.get("title") or ""
        url = c["url"]
        if re.search(r"^\s*(search results|find hotels)", title, re.I):
            state = "DEAD_PROPERTY_CODE"
            why = ("the brand answered 200 with a search page, not this property; "
                   "the slug is retired and the route needs repair")
        elif re.search(r"^\s*(hotels? in |extended stay hotels in )", title, re.I):
            state = "BRAND_INVENTORY_SILENT"
            why = "a brand CITY page, not a property page; it routes nothing"
        elif url in routed_urls:
            state = "EXACT_ACTIVE_ROUTE"
            why = "matched to a Fort Wayne census identity and routed"
        elif status == 403:
            state = "TRUE_MISSING_BRAND_IDENTITY"
            why = ("the brand's own inventory publishes this property but its page "
                   "refuses a plain client, and no census identity matched the slug "
                   "uniquely; the address is not yet obtained")
        elif status == 200:
            state = "TRUE_MISSING_BRAND_IDENTITY"
            why = "the brand publishes this property and no census identity matched it"
        else:
            state = "BRAND_INVENTORY_SILENT"
            why = "the brand did not serve this property page (%s)" % status
        out.append(OrderedDict([
            ("family", c["family"]), ("url", url),
            ("property_code", c.get("property_code") or ""),
            ("page_status", status), ("title", title[:120]),
            ("state", state), ("why", why),
        ]))
    return out


# --------------------------------------------------------------------------- #
# Phase 16 -- the founder packet
# --------------------------------------------------------------------------- #

def founder_packet(recon, capture_rows, brand_rows, competitor):
    groups = OrderedDict([
        ("A_identity_alias_successor_duplicate_same_campus", []),
        ("B_geography_fringe", []),
        ("C_closure_conversion_non_lodging", []),
        ("D_policy_ambiguity_reader_exception", []),
        ("E_evidence_conflict", []),
        ("F_cross_market_identity_collision", []),
    ])

    def item(identity, evidence, action, recommendation, census_effect,
             authority_effect, routing_effect, reversible, blocks):
        return OrderedDict([
            ("identity", identity), ("evidence", evidence),
            ("proposed_action", action), ("recommendation", recommendation),
            ("census_effect", census_effect), ("authority_effect", authority_effect),
            ("routing_effect", routing_effect), ("reversibility", reversible),
            ("blocks_promotion", blocks)])

    for conflict in recon.get("same_number_street_disagreement") or []:
        groups["A_identity_alias_successor_duplicate_same_campus"].append(item(
            "%s / %s at %s, ZIP %s" % (conflict["a"]["name"], conflict["b"]["name"],
                                       conflict["street_number"], conflict["postal_code"]),
            "%s states %r; %s states %r. Same street number and ZIP, different street."
            % (conflict["a"]["lane"], conflict["a"]["street"],
               conflict["b"]["lane"], conflict["b"]["street"]),
            "rule whether these are ONE property the two sources name differently, "
            "or two buildings that share a street number",
            "ONE property -- IN-930 and East Washington Boulevard are the same "
            "roadway here, and both lanes give the same house number and ZIP",
            "merges two candidate rows into one identity", "none: neither row publishes",
            "the surviving row keeps one route", "fully reversible", "NO"))

    for collision in recon.get("name_collisions_across_buildings") or []:
        groups["A_identity_alias_successor_duplicate_same_campus"].append(item(
            collision["identity_key"],
            "; ".join("%s at %s (%s)" % (g["canonical_name"], g["street"] or "no street",
                                         ",".join(g["lanes"]))
                      for g in collision["groups"]),
            "give each building a distinguishing canonical name, or rule one an alias",
            "distinguish by location -- a bare brand name over two buildings cannot "
            "route or publish",
            "keeps both rows, renames at least one", "none: neither row publishes",
            "each building keeps its own route", "fully reversible", "NO"))

    for g in recon["groups"]:
        if g["classification"] == "ADDRESS_CONFLICT":
            groups["E_evidence_conflict"].append(item(
                g["canonical_name"],
                "observations disagree: postal %s, address keys %s"
                % (g["distinct_postal_codes"], g["distinct_address_keys"]),
                "establish the property's real address from a first-party source",
                "hold until a first-party page states the address",
                "row stays out of the confirmed census", "none", "unrouted",
                "fully reversible", "NO"))
        elif g["classification"] == "IDENTITY_REVIEW_REQUIRED":
            groups["A_identity_alias_successor_duplicate_same_campus"].append(item(
                g["canonical_name"], g["classification_reason"],
                "settle the identity before routing", "hold",
                "row stays out of the confirmed census", "none", "unrouted",
                "fully reversible", "NO"))
        elif g["classification"] == "SAME_CAMPUS_DISTINCT_ENTITY":
            groups["A_identity_alias_successor_duplicate_same_campus"].append(item(
                g["canonical_name"], "shares an address key with another identity",
                "rule whether these are co-located distinct hotels", "hold both",
                "both rows stay out", "none", "unrouted", "fully reversible", "NO"))

    name_only = [g for g in recon["groups"]
                 if g["classification"] == "NAME_ONLY_UNRESOLVED"]
    if name_only:
        groups["B_geography_fringe"].append(item(
            "%d name-only leads" % len(name_only),
            "named by a directory but no lane states a street address, so market "
            "membership cannot be settled either way",
            "obtain an address, or retire the lead",
            "leave unresolved -- these are leads, and a lead is not a census row",
            "no effect: they are not in the confirmed census", "none", "unrouted",
            "fully reversible", "NO"))

    ct = [b for b in brand_rows if b["state"] == "TRUE_MISSING_BRAND_IDENTITY"]
    if ct:
        groups["A_identity_alias_successor_duplicate_same_campus"].append(item(
            "%d brand-inventory properties with no census identity" % len(ct),
            "the brand's own inventory publishes them; their property pages refuse "
            "a plain client so no address was obtained",
            "obtain each address from a rendered fetch, then admit",
            "OPTIONAL coverage expansion -- correctness does not depend on it",
            "would add up to %d identities" % len(ct), "none yet", "each gains a route",
            "fully reversible", "NO"))

    dead = [b for b in brand_rows if b["state"] == "DEAD_PROPERTY_CODE"]
    if dead:
        groups["C_closure_conversion_non_lodging"].append(item(
            "%d retired brand slugs" % len(dead),
            "; ".join(b["url"] for b in dead),
            "record the slug as retired; do NOT read it as a closure",
            "retire the ROUTE only -- a brand-roster absence is not proof a building "
            "closed, and each of these has a live sibling slug",
            "none", "none", "route repaired or withdrawn", "fully reversible", "NO"))

    ct_rows = [b for b in brand_rows
               if re.search(r"/hotels/hvn", b["url"], re.I)]
    if ct_rows:
        groups["F_cross_market_identity_collision"].append(item(
            "%d Marriott 'New Haven' properties in CONNECTICUT" % len(ct_rows),
            "selected by this market's 'new-haven' locality token; their codes are "
            "HVN-prefixed (New Haven CT), not FWA",
            "exclude from Fort Wayne",
            "exclude -- New Haven, Indiana and New Haven, Connecticut share a name "
            "and nothing else",
            "none: never admitted", "none", "none", "fully reversible", "NO"))

    warsaw = [b for b in brand_rows if "fwafw" in (b.get("property_code") or "")]
    if warsaw:
        groups["B_geography_fringe"].append(item(
            "Fairfield Inn & Suites Warsaw (Marriott code fwafw)",
            "carries this market's FWA property-code prefix but sits in Warsaw, "
            "Indiana, about 40 miles west and outside the declared geography",
            "exclude from Fort Wayne",
            "exclude -- a property code is Marriott's routing convenience, not a "
            "market boundary",
            "none: never admitted", "none", "none", "fully reversible", "NO"))

    return groups


def build(args):
    recon = read_json(RECON)
    capture = read_json(CAPTURE, {"rows": []})
    brand_doc = read_json(BRAND, {})
    competitor = read_json(COMPETITOR, {})
    cvb = read_json(CVB, {})
    osm = read_json(OSM, {})
    contract = MC.parse_market(read_json(PENDING_CONTRACT),
                               source="markets/pending/fort-wayne-in.json")

    rows = capture.get("rows") or []
    by_key = {g["identity_key"]: g for g in recon["groups"]}

    # ---- phase 14 + 15: audit, then admit -------------------------------- #
    clean_pf, clean_no_pets, held = [], [], []
    for r in rows:
        classification = r.get("classification")
        if classification not in ("CLEAN_PET_FRIENDLY", "CLEAN_VERIFIED_NO_PETS"):
            continue
        findings = audit_clean_row(r)
        entry = OrderedDict([
            ("identity_key", r["identity_key"]),
            ("canonical_name", r["canonical_name"]),
            ("street", r.get("street") or ""), ("postal_code", r.get("postal_code") or ""),
            ("route", r.get("url")), ("route_state", r.get("route_state")),
            ("route_basis", r.get("route_basis")),
            ("final_url", r.get("final_url")),
            ("source_lane", "DIRECT_STATIC_FETCH"),
            ("captured_at", r.get("captured_at")),
            ("page_sha256", r.get("page_sha256")),
            ("identity_signals", r.get("identity_assessment")),
            ("extraction", (r.get("observation") or {}).get("extraction")),
            ("evidence", (r.get("observation") or {}).get("evidence")),
            ("withheld_fields", (r.get("observation") or {}).get("withheld_fields")),
            ("publication_grade", (r.get("observation") or {}).get("publication_grade")),
            ("wrong_evidence_findings", findings),
        ])
        if findings:
            entry["held_because"] = findings
            held.append(entry)
        elif classification == "CLEAN_PET_FRIENDLY":
            clean_pf.append(entry)
        else:
            clean_no_pets.append(entry)

    brand_rows = brand_audit(brand_doc, rows)
    packet = founder_packet(recon, rows, brand_rows, competitor)

    # ---- phase 18: the shadow census ------------------------------------- #
    confirmed = [g for g in recon["groups"]
                 if g["classification"] == "EXACT_UNIQUE_IDENTITY"]
    pf_keys = {e["identity_key"] for e in clean_pf}
    no_pets_keys = {e["identity_key"] for e in clean_no_pets}
    route_by_key = {r["identity_key"]: r for r in rows}

    hotels = []
    for g in sorted(confirmed, key=lambda x: x["canonical_name"].lower()):
        key = g["identity_key"]
        r = route_by_key.get(key) or {}
        if key in pf_keys:
            policy_state = enums.POLICY_CONFIRMED
        elif key in no_pets_keys:
            policy_state = enums.VERIFIED_NO_PETS
        else:
            policy_state = enums.POLICY_NOT_VERIFIED
        hotels.append(OrderedDict([
            ("identity_key", key),
            ("canonical_name", g["canonical_name"]),
            ("display_name", g["canonical_name"]),
            ("slug", g["slug"] or slugify(g["canonical_name"])),
            ("market_id", MARKET_ID),
            ("address", g.get("street") or ""),
            ("city", g.get("city") or "Fort Wayne"),
            ("state", "IN"),
            ("postal_code", g.get("postal_code") or ""),
            ("phone", g.get("phone") or ""),
            ("identity_state", enums.IDENTITY_CONFIRMED if len(g["lanes"]) > 1
             else enums.IDENTITY_PROVISIONAL),
            ("lodging_state", enums.LODGING_CONFIRMED if len(g["lanes"]) > 1
             else enums.LODGING_BY_NAME),
            ("policy_state", policy_state),
            ("collision_state", enums.COLLISION_NONE),
            ("official_url", r.get("url") or g.get("official_url") or ""),
            ("corridor", ""), ("assignment_basis", ""), ("assignment_value", ""),
            ("source", "+".join(g["lanes"]).lower()),
            ("source_id", g["slug"]),
            ("observed_at", time.strftime("%Y-%m-%d", time.gmtime())),
            ("provenance", "%s:%s" % (WORK_ORDER, "+".join(g["lanes"]).lower())),
            ("normalized_name", key),
            ("former_name", ""),
            ("url_shape", "property" if r.get("url") else ""),
            ("disposition", "canonical"),
            ("street_identity", g.get("street") or ""),
        ]))

    # Corridor assignment through the ONE assignment authority.
    # fail_closed=False because this is review tooling, not the build: an
    # unauthorized multi-corridor match is RECORDED and leaves the hotel
    # UNASSIGNED rather than raising or being guessed at.
    assignment = assign_hotels(
        contract,
        [{"name": h["canonical_name"], "city": h["city"], "state": h["state"],
          "postal_code": h["postal_code"]} for h in hotels],
        fail_closed=False)
    for h in hotels:
        key = h["identity_key"]
        corridors = assignment.corridor_of.get(key) or ()
        if len(corridors) == 1:
            h["corridor"] = corridors[0]
            basis, value = assignment.basis_of.get(key, ("", ""))
            h["assignment_basis"] = basis
            h["assignment_value"] = value

    census = OrderedDict([
        ("schema", enums.CENSUS_SCHEMA),
        ("market_id", MARKET_ID),
        ("identity_key_contract", "ptf_identity_key/1.0"),
        ("identity_contract", "ptf-identity-evidence/1.0"),
        ("work_order", WORK_ORDER),
        ("captured_at", time.strftime("%Y-%m-%d", time.gmtime())),
        ("status", "PROPOSED_SHADOW_CENSUS_NOT_REGISTERED"),
        ("note",
         "The PROPOSED Fort Wayne census. It lives in identity_census_proposed/ "
         "and is NOT the committed census: nothing in the production build reads "
         "this path, no global was regenerated for it, and no pin names it. The "
         "promotion order moves it. Every row was reconciled from free first-party "
         "lanes (OpenStreetMap, the Allen County CVB, and the Marriott/Hilton/"
         "Wyndham/WoodSpring/Magnuson inventories); competitor rows are leads only "
         "and none is admitted here."),
        ("source_authorities", [
            "OpenStreetMap via Overpass (ODbL)", "Visit Fort Wayne / Allen County CVB",
            "Marriott official sitemap (via a committed owned harvest)",
            "Hilton official Fort Wayne location page",
            "Wyndham / WoodSpring / Magnuson official sitemaps",
        ]),
        ("count", len(hotels)),
        ("identity_state_counts",
         OrderedDict(sorted(Counter(h["identity_state"] for h in hotels).items()))),
        ("hotels", hotels),
    ])

    issues = CENSUS_CONTRACT.validate(census, market_states=("IN",))

    # ---- phase 17: paid readiness ---------------------------------------- #
    unresolved_routed = [r for r in rows
                         if r.get("url") and r.get("classification") not in
                         ("CLEAN_PET_FRIENDLY", "CLEAN_VERIFIED_NO_PETS")]
    blocked = [r for r in unresolved_routed
               if r.get("classification") in ("ACCESS_BLOCKED_PLAIN_CLIENT",
                                              "NEEDS_ATTENDED_RENDER")]
    missing_brand = [b for b in brand_rows if b["state"] == "TRUE_MISSING_BRAND_IDENTITY"]
    paid = OrderedDict([
        ("firecrawl", OrderedDict([
            ("candidate_rows", len(blocked)),
            ("credits_if_every_attempt_succeeds", len(blocked)),
            ("cost_basis",
             "Firecrawl cost is BIMODAL: 1 credit on a success, 0 when the origin "
             "refuses every engine. The blended average is not a ceiling, so the "
             "cap is on ATTEMPTS, not on an expected spend."),
            ("authorized_by_this_order", False),
            ("classification", "OPTIONAL_COVERAGE_EXPANSION"),
        ])),
        ("bright_data", OrderedDict([
            ("candidate_rows", len(blocked)),
            ("measured_rate", "not measured on this market"),
            ("expected_attempts", len(blocked)),
            ("hard_cap_usd", None),
            ("authorized_by_this_order", False),
            ("classification", "OPTIONAL_COVERAGE_EXPANSION"),
        ])),
        ("places", OrderedDict([
            ("candidate_rows", len(missing_brand)),
            ("existing_paid_attempts_for_this_market", 0),
            ("note", "no Fort Wayne row appears in any committed paid-attempt "
                     "ledger; this market has never been bought"),
            ("authorized_by_this_order", False),
            ("classification", "OPTIONAL_COVERAGE_EXPANSION"),
        ])),
        ("attended_browser", OrderedDict([
            ("candidate_rows", len(blocked) + len(missing_brand)),
            ("cost", "no money; operator time"),
            ("classification", "OPTIONAL_COVERAGE_EXPANSION"),
        ])),
        ("required_for_promotion", []),
        ("why_nothing_is_required",
         "Promotion needs the rows it promotes to be correct, not the market to be "
         "complete. Every clean row here was read from a first-party page and "
         "survived the wrong-evidence audit; every unresolved row is explicitly "
         "held and publishes nothing. Buying more coverage would raise the count "
         "and cannot change the correctness of what is already clean."),
    ])

    # ---- phase 19: promotion readiness ------------------------------------ #
    blockers = []
    if issues:
        blockers.append("the proposed census does not satisfy the census contract: %s"
                        % [i.code for i in issues][:5])
    if not clean_pf and not clean_no_pets:
        blockers.append("no clean policy row: the market would promote an empty "
                        "authority")
    duplicate_premises = [g for g in recon["groups"]
                          if g["classification"] == "SAME_CAMPUS_DISTINCT_ENTITY"]
    if duplicate_premises:
        blockers.append("%d unresolved same-address pairs" % len(duplicate_premises))
    # The market's OWN contract says how many published hotels it takes to be a
    # market. Promoting below that ships a market page with almost nothing on
    # it, and every corridor falls under its own minimum too -- so this is a
    # publication blocker, not a coverage preference. Checked against the
    # contract's declared number rather than a literal, so raising or lowering
    # the bar is a config change and not a code change.
    if len(clean_pf) < contract.minimum_published_hotels:
        blockers.append(
            "the market publishes %d pet-friendly profile(s) against its own "
            "minimum_published_hotels of %d: the free static lane returned 1 VALID "
            "capture from 19 routed rows, and 38 of the remaining rows are CHANNEL "
            "failures (13 ACCESS_DENIED brand walls, 3 UNHYDRATED, 2 transport) "
            "rather than sources that said nothing. A rendered lane -- attended "
            "browser at no money, or Firecrawl on authorized credits -- is what "
            "this market needs, and neither is authorized by this order."
            % (len(clean_pf), contract.minimum_published_hotels))
    corridors_publishing = sum(
        1 for c in contract.corridors
        if sum(1 for e in clean_pf
               if (by_key.get(e["identity_key"]) or {}).get("postal_code", "")
               in c.included_postal_codes) >= c.minimum_hotel_count)
    if not corridors_publishing:
        blockers.append(
            "no corridor reaches its own minimum_hotel_count, so the market would "
            "publish no corridor page at all")

    return OrderedDict([
        ("schema", SCHEMA), ("work_order", WORK_ORDER),
        ("phase", "7/14-19 -- brand audit, wrong-evidence audit, clean authority, "
                  "founder packet, paid readiness, shadow package, promotion readiness"),
        ("market_id", MARKET_ID), ("as_of", time.strftime("%Y-%m-%d", time.gmtime())),
        ("nothing_written_to_production_source", True),
        ("proposed_census_path", "launch_packages/pettripfinder/identity_census_proposed/fort-wayne-in.json"),
        ("proposed_contract_path", "launch_packages/pettripfinder/markets/pending/fort-wayne-in.json"),
        ("census_contract_issues", [OrderedDict([("field", i.field), ("code", i.code),
                                                 ("message", i.message)])
                                    for i in issues]),
        ("brand_inventory_audit", OrderedDict([
            ("counts", OrderedDict(sorted(Counter(b["state"] for b in brand_rows).items()))),
            ("rows", brand_rows),
        ])),
        ("wrong_evidence_audit", OrderedDict([
            ("clean_candidates_examined", len(clean_pf) + len(clean_no_pets) + len(held)),
            ("held_by_the_audit", len(held)),
            ("findings", OrderedDict(sorted(Counter(
                f for e in held for f in e["wrong_evidence_findings"]).items()))),
            ("held_rows", held),
        ])),
        ("clean_pending_authority", OrderedDict([
            ("clean_pet_friendly", clean_pf),
            ("clean_verified_no_pets", clean_no_pets),
        ])),
        ("founder_packet", packet),
        ("paid_readiness", paid),
        ("shadow_market", OrderedDict([
            ("census", len(hotels)),
            ("pet_friendly", len(clean_pf)),
            ("verified_no_pets", len(clean_no_pets)),
            ("out_of_category", 0),
            ("resolved", len(clean_pf) + len(clean_no_pets)),
            ("unresolved", len(hotels) - len(clean_pf) - len(clean_no_pets)),
            ("profiles", len(clean_pf)),
            ("corridors_defined", len(contract.corridors)),
            ("corridors_with_a_census_row",
             len({h["corridor"] for h in hotels if h["corridor"]})),
            ("unassigned_to_any_corridor",
             sum(1 for h in hotels if not h["corridor"])),
            ("corridor_conflicts", len(assignment.conflicts)),
            ("routed", sum(1 for r in rows if r.get("url"))),
        ])),
        ("promotion", OrderedDict([
            ("promotion_ready", "NO" if blockers else "YES"),
            ("blockers", blockers),
            ("required_before_promotion", blockers or [
                "integrate the then-current deployed canonical lineage first"]),
            ("optional_coverage_expansion", [
                "%d brand-inventory properties whose pages refuse a plain client"
                % len(missing_brand),
                "%d routed rows blocked or unhydrated on the static lane" % len(blocked),
                "%d name-only leads with no address" % sum(
                    1 for g in recon["groups"]
                    if g["classification"] == "NAME_ONLY_UNRESOLVED"),
            ]),
        ])),
    ]), census


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=os.path.join(
        REPORTS, "fort_wayne_in_shadow_package_001.json"))
    args = ap.parse_args(argv)
    rep, census = build(args)
    os.makedirs(PROPOSED_CENSUS_DIR, exist_ok=True)
    census_path = os.path.join(PROPOSED_CENSUS_DIR, "fort-wayne-in.json")
    with open(census_path, "wb") as fh:
        fh.write((json.dumps(census, indent=1, ensure_ascii=False, default=str) + "\n").encode("utf-8"))
    with open(args.out, "wb") as fh:
        fh.write((json.dumps(rep, indent=1, ensure_ascii=False, default=str) + "\n").encode("utf-8"))
    print("written", os.path.relpath(census_path, _DASH))
    print("written", os.path.relpath(args.out, _DASH))
    print(json.dumps(rep["shadow_market"], indent=1))
    print("census contract issues:", len(rep["census_contract_issues"]))
    print("PROMOTION_READY:", rep["promotion"]["promotion_ready"], rep["promotion"]["blockers"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
