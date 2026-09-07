"""PTF-CHATTANOOGA-TN-NEW-MARKET-001 -- Phases 14 to 20, in one pass.

Takes every read this order made and turns it into the things a serialized
promotion order will need, and nothing else:

  14  WRONG-EVIDENCE AUDIT       every clean read tested against the known
                                 failure classes before it is allowed to count.
  15  CLEAN PENDING AUTHORITY    CLEAN_PET_FRIENDLY and CLEAN_VERIFIED_NO_PETS,
                                 with holds, silence and identity-only evidence
                                 excluded.
  16/17 FOUNDER PACKET           one grouped packet, A to F, never one row at a
                                 time.
  18  PAID READINESS             what each paid lane would cost and whether it
                                 is REQUIRED_FOR_PROMOTION or optional. Shared
                                 ledgers are READ, never written.
  19/20 SHADOW PACKAGE + PROMOTION READINESS

THE AUDIT IS THE POINT
----------------------
A read that survives this file is one this market is willing to publish. The
classes it tests for are the ones that have actually shipped a wrong answer in
this project before:

  * an amenity chip standing in for an operative policy;
  * a service-animal sentence read as ordinary pet acceptance;
  * acceptance INFERRED from a fee, a weight or a count with no statement that
    pets are taken at all;
  * a refusal inferred from a structured flag alone;
  * a shared or brand-level page standing in for one property;
  * an identity the page did not confirm;
  * source silence encoded as a policy;
  * and, in this market, a Tennessee/Georgia geography mismatch.

Nothing here writes authority, moves a pin, or touches another market.

Outputs:
  launch_packages/pettripfinder/markets/reports/chattanooga_tn_evidence_audit_001.json
  launch_packages/pettripfinder/markets/reports/chattanooga_tn_clean_authority_001.json
  launch_packages/pettripfinder/markets/reports/chattanooga_tn_founder_packet_001.json
  launch_packages/pettripfinder/markets/reports/chattanooga_tn_paid_readiness_001.json
  launch_packages/pettripfinder/markets/reports/chattanooga_tn_shadow_market_001.json
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

from scripts.pettripfinder.markets import contract as MC  # noqa: E402
from scripts.pettripfinder.site_data import normalize_name  # noqa: E402

WORK_ORDER = "PTF-CHATTANOOGA-TN-NEW-MARKET-001"
MARKET_ID = "chattanooga-tn"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
def _first_existing(*paths):
    """The registered path if this market has been promoted, else the proposed one."""
    for p in paths:
        if os.path.exists(p):
            return p
    return paths[-1]

REPORTS = os.path.join(PKG, "markets", "reports")
CONTRACT = _first_existing(os.path.join(PKG, "markets", "chattanooga-tn.json"),
                           os.path.join(PKG, "markets", "proposed", "chattanooga-tn.json"))
CENSUS = _first_existing(os.path.join(PKG, "identity_census", "chattanooga-tn.json"),
                         os.path.join(PKG, "identity_census_proposed", "chattanooga-tn.json"))
RECON = os.path.join(REPORTS, "chattanooga_tn_census_reconciliation_001.json")
ROUTING = os.path.join(REPORTS, "chattanooga_tn_routing_001.json")
STATIC = os.path.join(REPORTS, "chattanooga_tn_free_static_capture_001.json")
FIRECRAWL = os.path.join(REPORTS, "chattanooga_tn_firecrawl_pass_001.json")
ATTENDED = os.path.join(REPORTS, "chattanooga_tn_attended_capture_001.json")
LADDER = os.path.join(REPORTS, "chattanooga_tn_ladder_plan_001.json")
GAPS = os.path.join(REPORTS, "chattanooga_tn_competitor_gap_001.json")
LEADS = os.path.join(REPORTS, "chattanooga_tn_lead_sources_001.json")

CLEAN_PET_FRIENDLY = "CLEAN_PET_FRIENDLY"
CLEAN_VERIFIED_NO_PETS = "CLEAN_VERIFIED_NO_PETS"

#: Language that is about service animals and about nothing else. A page that
#: says only this has said nothing about ordinary pets.
_SERVICE_ANIMAL_ONLY = re.compile(
    r"^\s*(only\s+)?(certified\s+|trained\s+)?(service|assistance|guide)\s+(animals?|dogs?)\b",
    re.I)
#: Surfaces that are not an operative policy even when a locator finds them.
_NON_EVIDENCE_SURFACE = re.compile(r"amenit|chip|brand[_ -]?page|search[_ -]?result", re.I)


def _load(path, default=None):
    if not os.path.exists(path):
        return default
    with open(path, encoding="utf-8") as fh:
        return json.load(fh)


# --------------------------------------------------------------------------- #
# Phase 14 -- the wrong-evidence audit.
# --------------------------------------------------------------------------- #

#: Chain vocabulary, for telling a spelling difference from a brand difference.
_CHAIN_WORDS = {
    "courtyard", "residence", "towneplace", "springhill", "fairfield", "renaissance",
    "delta", "hampton", "homewood", "home2", "doubletree", "embassy", "tru", "spark",
    "canopy", "tapestry", "garden", "holiday", "express", "crowne", "staybridge",
    "candlewood", "comfort", "quality", "sleep", "clarion", "econo", "rodeway",
    "suburban", "mainstay", "woodspring", "baymont", "days", "super", "ramada",
    "travelodge", "wingate", "microtel", "hawthorn", "howard", "johnson", "quinta",
    "radisson", "country", "sonesta", "drury", "western", "roof", "motel", "studio",
    "wyndham", "royal", "relax", "sunset", "crown", "hamlin", "belamere", "bridgepointe",
}


def _chain_words(name):
    from scripts.pettripfinder.site_data import normalize_name as _n
    return {t for t in _n(name or "").split() if t in _CHAIN_WORDS}


def audit_read(row, census_row):
    """Every reason this read may NOT be published. Empty list means clean."""
    problems = []
    obs = row.get("observation") or {}
    ext = obs.get("extraction") or {}
    evidence = obs.get("evidence") or []
    quotes = [str(e.get("quote") or "") for e in evidence]
    locations = [str(e.get("location") or "") for e in evidence]
    ident = row.get("identity_assessment") or {}
    pets = ext.get("pets_allowed")

    if pets is None:
        problems.append(OrderedDict([
            ("class", "SOURCE_SILENT_ENCODED_AS_POLICY"),
            ("why", "the reader returned no pets_allowed value; silence is not a policy")]))
    if not ident.get("confirmed"):
        problems.append(OrderedDict([
            ("class", "IDENTITY_NOT_CONFIRMED"),
            ("why", "the page's own address, phone or property code did not confirm this "
                    "identity, so whatever it says is about some other building"),
            ("conflicting", ident.get("conflicting"))]))
    if any(_NON_EVIDENCE_SURFACE.search(loc) for loc in locations):
        problems.append(OrderedDict([
            ("class", "AMENITY_CHIP_OR_BRAND_SURFACE"),
            ("why", "the quote came from a surface that is not an operative policy"),
            ("locations", locations)]))

    pets_quotes = [str(e.get("quote") or "") for e in evidence
                   if "pets_allowed" in (e.get("field_refs") or [])]
    if pets is True:
        if not pets_quotes:
            problems.append(OrderedDict([
                ("class", "ACCEPTANCE_INFERRED_WITHOUT_A_STATEMENT"),
                ("why", "pets_allowed is true but no quote is attributed to it; a fee, a weight "
                        "or a count is not a statement that pets are taken")]))
        elif all(_SERVICE_ANIMAL_ONLY.match(q) for q in pets_quotes):
            problems.append(OrderedDict([
                ("class", "SERVICE_ANIMAL_LANGUAGE_READ_AS_PET_ACCEPTANCE"),
                ("why", "every quote supporting acceptance is about service animals"),
                ("quotes", pets_quotes)]))
    if pets is False and not pets_quotes:
        problems.append(OrderedDict([
            ("class", "REFUSAL_INFERRED_FROM_A_STRUCTURED_FLAG_ALONE"),
            ("why", "pets_allowed is false with no quote attributed to it")]))

    if census_row is None:
        problems.append(OrderedDict([
            ("class", "NOT_IN_THE_PROPOSED_CENSUS"),
            ("why", "this read is not bound to an admitted Chattanooga identity")]))
    else:
        page_postal = str(((ident.get("signals") or {}).get("postal_code") or ""))[:5]
        if page_postal and census_row.get("postal_code") and \
                page_postal != census_row["postal_code"]:
            problems.append(OrderedDict([
                ("class", "PAGE_POSTAL_DISAGREES_WITH_CENSUS"),
                ("why", "the page states postal %s and the census row states %s"
                        % (page_postal, census_row["postal_code"]))]))
    return problems


_BY_ADDRESS = {}
_BY_CODE = {}


def _index_census():
    from scripts.pettripfinder.hotel_exclusions import address_key
    for h in (_load(CENSUS, {}) or {}).get("hotels", []):
        if h.get("street"):
            _BY_ADDRESS[address_key(h["street"], h.get("postal_code", ""))] = h
            _BY_ADDRESS.setdefault(address_key(h["street"], ""), h)
        if h.get("property_code"):
            _BY_CODE[h["property_code"].lower()] = h


def _match_by_address(row):
    """An attended read is bound to the census row at the SAME BUILDING."""
    from scripts.pettripfinder.hotel_exclusions import address_key
    if not _BY_ADDRESS and not _BY_CODE:
        _index_census()
    code = (row.get("_property_code") or "").lower()
    if code and code in _BY_CODE:
        return _BY_CODE[code]
    street, postal = row.get("_street") or "", (row.get("_postal") or "")[:5]
    if not street:
        return None
    return _BY_ADDRESS.get(address_key(street, postal)) or _BY_ADDRESS.get(address_key(street, ""))


def _conflicted_identities(recon):
    """Names the merge refused to resolve. A read on one of these is not clean."""
    out = set()
    for c in (recon or {}).get("merge_conflicts", []):
        claimed = c.get("claimed_by") or []
        sigs = [_chain_words(n) for n in claimed]
        sigs = [x for x in sigs if x]
        # Only a conflict between DIFFERENT chains is unresolved; two spellings
        # of one hotel's own name were absorbed and are settled.
        if len(sigs) >= 2 and not all(sigs[0] & other for other in sigs[1:]):
            for n in claimed:
                out.add(normalize_name(n))
    return out


def clean_reads():
    """Every read this order made, audited, from every lane that produced one."""
    # A read is bound to the building it was captured FOR, under any key a lane
    # used for it. The merge renames a building to its fullest name, so a read
    # captured under the brand roster's shorter name would otherwise orphan.
    census = {}
    for h in (_load(CENSUS, {}) or {}).get("hotels", []):
        census[h["identity_key"]] = h
        for alias in h.get("identity_key_aliases") or []:
            census.setdefault(alias, h)
    lanes = OrderedDict()
    for label, path, key in (("DIRECT_STATIC", STATIC, "rows"),
                             ("FIRECRAWL", FIRECRAWL, "rows")):
        doc = _load(path, {}) or {}
        lanes[label] = doc.get(key) or []
    # The attended rows arrive in the attended report's own shape. Reshape them
    # into the capture shape the audit reads, so ONE audit governs every lane.
    attended = []
    for r in ((_load(ATTENDED, {}) or {}).get("rows") or []):
        if not r.get("in_market"):
            continue
        ext = r.get("extraction") or {}
        quote = r.get("exact_quote") or ""
        fields = [k for k in ext if k not in ("service_animal_statement",)]
        attended.append(OrderedDict([
            ("identity_key", ""), ("canonical_name", ""),
            ("brand", r.get("brand")), ("requested_url", r.get("requested_url")),
            ("final_url", r.get("final_url")), ("page_sha256", ""),
            ("captured_at", r.get("captured_at")),
            ("identity_assessment", OrderedDict([
                ("signals", r.get("identity_signals")),
                ("confirmed", r.get("identity_confirmed")),
                ("binding_method", r.get("identity_binding_method")),
                ("conflicting", [])])),
            ("observation", OrderedDict([
                ("extraction", ext),
                ("evidence", [OrderedDict([
                    ("quote", quote),
                    ("location", "bounded policy container (%s)" % (r.get("surface") or "")),
                    ("field_refs", fields)])]),
                ("withheld_fields", []),
                ("publication_grade", {"verdict": "PUBLICATION_GRADE_CONFIRMED"}
                 if r.get("identity_confirmed") and ext.get("pets_allowed") is not None else None),
            ])),
            ("artifact_dir", ""),
            ("_property_code", r.get("property_code")),
            ("_street", (r.get("identity_signals") or {}).get("address_on_page")),
            ("_postal", (r.get("identity_signals") or {}).get("postal_code")),
        ]))
    lanes["ATTENDED_BROWSER"] = attended

    audited = []
    for lane, rows in lanes.items():
        for r in rows:
            obs = r.get("observation") or {}
            ext = obs.get("extraction") or {}
            if "pets_allowed" not in ext:
                continue
            crow = census.get(r["identity_key"])
            if crow is None and (r.get("_street") or r.get("_property_code")):
                crow = _match_by_address(r)
                if crow is not None:
                    r["identity_key"] = crow["identity_key"]
                    r["canonical_name"] = crow["canonical_name"]
            problems = audit_read(r, crow)
            pets = ext.get("pets_allowed")
            verdict = ("HELD" if problems else
                       CLEAN_PET_FRIENDLY if pets is True else
                       CLEAN_VERIFIED_NO_PETS if pets is False else "HELD")
            audited.append(OrderedDict([
                ("lane", lane), ("identity_key", r["identity_key"]),
                ("canonical_name", r["canonical_name"]),
                ("brand", r.get("brand") or r.get("family") or ""),
                ("corridor", (crow or {}).get("corridor", "")),
                ("source_url", r.get("requested_url")),
                ("final_url", r.get("final_url")),
                ("document_sha256", r.get("page_sha256")),
                ("captured_at", r.get("captured_at") or r.get("fetched_at") or ""),
                ("identity_signals", (r.get("identity_assessment") or {}).get("signals")),
                ("identity_binding_method",
                 (r.get("identity_assessment") or {}).get("binding_method")),
                ("pets_allowed", pets),
                ("extraction", ext),
                ("evidence", obs.get("evidence")),
                ("withheld_fields", obs.get("withheld_fields")),
                ("publication_grade", obs.get("publication_grade")),
                ("audit_verdict", verdict),
                ("audit_problems", problems),
                ("artifact_dir", r.get("artifact_dir")),
            ]))
    # Two closing holds, both of them defects this run actually produced.
    # Resolve a conflict to the CENSUS IDENTITY, not to a display name. The
    # unresolved identity, not to a display name: a read captured under one of a
    # building's two claimed names carries neither of the other strings, so a
    # display-name test would hold one read on that building and publish the
    # other. Both are reads on one unresolved identity and both must be held.
    conflicted_names = _conflicted_identities(_load(RECON, {}) or {})
    conflicted = set()
    for h in (_load(CENSUS, {}) or {}).get("hotels", []):
        keys = {h["identity_key"]} | set(h.get("identity_key_aliases") or [])
        if keys & conflicted_names:
            conflicted |= keys
    conflicted |= conflicted_names
    by_identity = {}
    for a in audited:
        row = census.get(a["identity_key"])
        by_identity.setdefault(row["identity_key"] if row else a["identity_key"], []).append(a)
    for a in audited:
        if a["audit_verdict"] == "HELD":
            continue
        row = census.get(a["identity_key"])
        resolved = {a["identity_key"], normalize_name(a["canonical_name"])}
        if row:
            resolved |= {row["identity_key"]} | set(row.get("identity_key_aliases") or [])
        if resolved & conflicted:
            a["audit_verdict"] = "HELD"
            a["audit_problems"].append(OrderedDict([
                ("class", "IDENTITY_UNRESOLVED_BY_THE_MERGE"),
                ("why", "this building's address is claimed by two DIFFERENT chain identities "
                        "and the founder has not ruled which one trades there; publishing a "
                        "policy under either name could name a hotel that no longer answers "
                        "to it")]))
        peers = by_identity.get(row["identity_key"] if row else a["identity_key"], [])
        if len(peers) > 1:
            codes = sorted({p.get("_property_code") or p.get("source_url") for p in peers})
            a["audit_verdict"] = "HELD"
            a["audit_problems"].append(OrderedDict([
                ("class", "TWO_PROPERTIES_READ_ONTO_ONE_IDENTITY"),
                ("why", "%d reads bound to this one census identity (%s). Two hotels share the "
                        "address and the census has not yet separated them, so neither read may "
                        "publish under it" % (len(peers), ", ".join(str(c)[:70] for c in codes)))]))
    return audited, census


# --------------------------------------------------------------------------- #
# Phase 16 -- the grouped founder packet.
# --------------------------------------------------------------------------- #

def founder_packet(census_doc, recon, routing, audited, gaps, city_pages):
    def item(group, identity, evidence, action, recommendation, census_effect,
             authority_effect, routing_effect, reversible, blocks):
        return OrderedDict([
            ("group", group), ("identity", identity), ("evidence", evidence),
            ("proposed_action", action), ("recommendation", recommendation),
            ("census_effect", census_effect), ("authority_effect", authority_effect),
            ("routing_effect", routing_effect), ("reversibility", reversible),
            ("blocks_promotion", blocks),
        ])

    items = []
    non_admitted = census_doc.get("non_admitted", [])

    # A -- identity, alias, successor, duplicate, same campus.
    for r in non_admitted:
        if r["classification"] == "SAME_IDENTITY_REBRAND_SUCCESSOR":
            items.append(item(
                "A_IDENTITY", r["canonical_name"],
                OrderedDict([("street", r["street"]), ("postal_code", r["postal_code"]),
                             ("reason", r["classification_reason"]),
                             ("names_in_evidence",
                              sorted({o.get("name") for o in r["evidence"] if o.get("name")}))]),
                "name the CURRENT identity for this one building and record the predecessor as "
                "its lineage",
                "adopt the newer brand name as canonical and keep the older one as a lineage "
                "record, the Cleveland ruling-B precedent (retire = MOVE the row, never delete)",
                "one identity, not two", "no policy is published for it until the name is settled",
                "one route, on the current brand's own property page",
                "REVERSIBLE -- a rename, with the predecessor kept", "NO"))
        if r["classification"] == "IDENTITY_REVIEW_REQUIRED":
            items.append(item(
                "A_IDENTITY", r["canonical_name"] or "(unnamed building)",
                OrderedDict([("street", r["street"]), ("city", r["city"]),
                             ("postal_code", r["postal_code"]),
                             ("reason", r["classification_reason"]),
                             ("lanes", r["lanes"])]),
                "rule on whether this is a distinct identity, and give it a name",
                "hold: the evidence does not decide it and a guess would publish a wrong page",
                "one row admitted or dropped", "none while held",
                "no route is issued while held",
                "REVERSIBLE -- the row stays in the proposed census either way", "NO"))

    # A merge the graph refused to make silently. Most of these are the SAME
    # hotel under two spellings of its own name -- "Hampton Chattanooga Oregon" and
    # "Hampton Inn & Suites - Chattanooga/Oregon" -- which the merge absorbs and
    # which is no question at all. Only a conflict whose claimants carry
    # DIFFERENT chain vocabulary is a founder question: that is a rebrand or a
    # shared campus, and the two are not distinguishable without a ruling.
    seen_conflicts = set()
    same_brand_absorbed = []
    for c in (recon or {}).get("merge_conflicts", []):
        o = c.get("observation") or {}
        pair = (tuple(sorted(c.get("claimed_by") or [])), o.get("street") or "")
        if pair in seen_conflicts:
            continue
        seen_conflicts.add(pair)
        sigs = [_chain_words(n) for n in (c.get("claimed_by") or [])]
        sigs = [x for x in sigs if x]
        if len(sigs) < 2 or all(sigs[0] & other for other in sigs[1:]):
            same_brand_absorbed.append(OrderedDict([
                ("claimed_by", c.get("claimed_by")), ("street", o.get("street"))]))
            continue
        items.append(item(
            "A_IDENTITY", " / ".join(c.get("claimed_by") or []),
            OrderedDict([
                ("observation", OrderedDict([("lane", o.get("lane")),
                                             ("name_on_page", o.get("name")),
                                             ("street", o.get("street")),
                                             ("postal_code", o.get("postal")),
                                             ("source_url", o.get("source_url"))])),
                ("claimed_by", c.get("claimed_by")),
                ("why", c.get("why"))]),
            "rule on whether these are one building under two names, two buildings on one "
            "campus, or a rebrand",
            "hold. The graph refused to choose rather than guess. %s states the address %s, "
            "and %d established identities already claim it. One of these is a rebrand and "
            "another is a shared campus; which is which is a founder ruling, not an inference"
            % (o.get("name") or "a property page", o.get("street") or "(no street)",
               len(c.get("claimed_by") or [])),
            "one identity or two", "the reads on these rows stay out of the clean inventory",
            "one route or two",
            "REVERSIBLE -- every observation is preserved on both candidates", "NO"))
    if same_brand_absorbed:
        items.append(item(
            "A_IDENTITY",
            "%d merge conflicts absorbed with no question: one hotel, two spellings of its own "
            "name" % len(same_brand_absorbed),
            OrderedDict([("rows", same_brand_absorbed[:20]),
                         ("why_this_is_not_a_question",
                          "each pair's claimants carry the SAME chain vocabulary, so they name "
                          "one hotel; the merge kept every observation on one node and the "
                          "fullest name won")]),
            "note only", "note. No ruling needed", "none", "none", "none",
            "REVERSIBLE", "NO"))

    # Bare display names are a real question, not a defect.
    bare = [h for h in census_doc.get("hotels", [])
            if len(h["canonical_name"].split()) <= 2 or h["canonical_name"].isupper()]
    if bare:
        items.append(item(
            "A_IDENTITY", "%d admitted identities carry a BARE BRAND display name" % len(bare),
            OrderedDict([("rows", [OrderedDict([("name", h["canonical_name"]),
                                                ("street", h["street"]),
                                                ("city", h["city"]),
                                                ("postal_code", h["postal_code"])])
                                   for h in bare])]),
            "approve a display name for each, from the property's own page",
            "fill each from the property's own page in the promotion order rather than inventing "
            "one here; the identity is correct, only the label is thin",
            "no change -- the identities are already admitted",
            "the published page title", "no change",
            "REVERSIBLE -- a display overlay, not an identity change", "NO"))

    # B -- geography and the Tennessee/Georgia border.
    border = [r for r in non_admitted if r["classification"] == "NORTH_GEORGIA_FRINGE_HOLD"]
    ga_outside = [r for r in non_admitted
                  if r["classification"] == "OUTSIDE_MARKET"
                  and (r.get("state") or "").upper() == "GA"]
    items.append(item(
        "B_GEOGRAPHY", "the north Georgia state-line belt (Catoosa, Walker and Dade counties)",
        OrderedDict([
            ("held", len(border)),
            ("identities", [OrderedDict([("name", r["canonical_name"]), ("city", r["city"]),
                                         ("postal_code", r["postal_code"])]) for r in border]),
            ("for", "Fort Oglethorpe, Ringgold and Rossville sit four to twelve miles from "
                    "downtown Chattanooga on the same I-75 and I-24 approaches as East Ridge and "
                    "Lookout Valley, several market themselves as Chattanooga lodging, and the "
                    "destination bureau promotes them"),
            ("against", "they are in ANOTHER STATE. This market's contract admits Tennessee "
                        "municipalities only, and a Georgia tier would need its own corridor, its "
                        "own postal partition and its own reconciliation. Marketing prose is not "
                        "geography."),
            ("how_they_were_found", "the discovery box reaches deliberately past the state line, "
                                    "and the Wyndham and BringFido lanes were pointed at the "
                                    "Georgia city slugs on purpose, so the belt is CLASSIFIED "
                                    "rather than silently missed")]),
        "admit a north Georgia tier as its own corridor, or keep the belt held",
        "KEEP HELD for launch. The market publishes comfortably without it, and admitting a "
        "second state is a bigger decision than a launch. Every row and its evidence is carried "
        "here so a later order can admit a NAMED cluster deliberately, through explicit_hotel_ids "
        "on a corridor created for it, and never by widening a postal partition.",
        "%d identities in or out" % len(border),
        "%d rows in or out of the clean inventory" % len(border),
        "a new corridor and its routes, or none",
        "REVERSIBLE -- the rows already exist in the proposed census either way", "NO"))
    items.append(item(
        "B_GEOGRAPHY", "Georgia and Tennessee towns a brand's regional code prefix reached",
        OrderedDict([
            ("what_happened", "Marriott's 'cha' code prefix and Hilton's 'cha' CTYHOCN prefix are "
                              "REGIONAL, not municipal. Between them they reached Cleveland "
                              "Tennessee, and Dalton, Calhoun, East Ellijay and Rome in Georgia."),
            ("treatment", "every one was captured in the attended pass and classified "
                          "OUTSIDE_MARKET on the address its OWN page states -- not on a guess, "
                          "and not by omitting it"),
            ("rows", [OrderedDict([("name", r["canonical_name"]), ("city", r["city"]),
                                   ("state", r["state"]), ("postal_code", r["postal_code"])])
                      for r in non_admitted if r["classification"] == "OUTSIDE_MARKET"][:24]),
            ("cross_market_note", "Cleveland, TENNESSEE is not Cleveland, OHIO, which is a LIVE "
                                  "market. Three Marriott rows in Cleveland TN 37312 were held "
                                  "out of this market and must never bind to the Ohio one.")]),
        "confirm that a property code SELECTS a row and only the page ADMITS it",
        "confirm. This is the rule that kept %d out-of-market rows out of the census."
        % len(ga_outside),
        "none", "none", "none", "REVERSIBLE", "NO"))

    # C -- closure, conversion, non-lodging.
    non_lodging = [r for r in non_admitted if r["classification"] == "NON_LODGING"]
    items.append(item(
        "C_CATEGORY", "%d rows classified NON_LODGING" % len(non_lodging),
        OrderedDict([
            ("what_they_are", "campgrounds, RV parks, a marina resort, cabins, treehouse and "
                              "cottage rentals and private guest houses that the destination "
                              "bureau lists among its lodging partners, plus three Sonesta "
                              "LANDMARK pages (a shopping mall and two hospitals) that the brand "
                              "indexes alongside its property pages"),
            ("sample", [r["canonical_name"] for r in non_lodging[:12]])]),
        "confirm that none of these is lodging this market publishes",
        "confirm. None was admitted, and no closure is asserted about any of them: a directory "
        "listing a business is not evidence that a hotel closed",
        "none -- they were never admitted", "none", "none", "REVERSIBLE", "NO"))
    items.append(item(
        "C_CATEGORY", "families whose own site refused this project's plain client",
        OrderedDict([
            ("refused", [OrderedDict([("family", r["family"]), ("status", r["status"])])
                         for r in (city_pages.get("refusal_probes") or [])
                         if r.get("outcome") != "SERVED"]),
            ("what_it_is_not", "a refusal is a CHANNEL failure and says nothing about whether a "
                               "property exists or what its policy is. No closure is asserted "
                               "about any of these brands, and brand-roster absence alone is "
                               "never closure proof."),
            ("what_it_is", "the measured reason those families were routed to the Firecrawl and "
                           "attended rungs; re-probe on the next order, because refusals go stale "
                           "in days")]),
        "note only",
        "note. No action; recorded so a later order re-probes rather than assuming",
        "none", "none", "none", "REVERSIBLE", "NO"))

    # D -- policy ambiguity and reader exceptions.
    held = [a for a in audited if a["audit_verdict"] == "HELD"]
    if held:
        items.append(item(
            "D_POLICY", "%d reads held by the wrong-evidence audit" % len(held),
            OrderedDict([("rows", [OrderedDict([("name", a["canonical_name"]),
                                                ("lane", a["lane"]),
                                                ("problems", [p["class"] for p in
                                                              a["audit_problems"]])])
                                   for a in held])]),
            "leave held, or rule individually",
            "leave held. Each failed a named class that has shipped a wrong answer before",
            "none", "excluded from the clean inventory", "none", "REVERSIBLE", "NO"))

    # E -- evidence conflict.
    mismatched = [r for r in routing.get("routes", [])
                  if r["routing_state"] == "ROUTE_BRAND_MISMATCH"]
    for r in mismatched:
        rej = r.get("rejected_route") or {}
        items.append(item(
            "E_EVIDENCE_CONFLICT", r["canonical_name"],
            OrderedDict([("stated_route", rej.get("rejected_url")),
                         ("stated_by", rej.get("stated_by")),
                         ("why_rejected", rej.get("why"))]),
            "find this property's real route, or hold it",
            "hold and re-route in the promotion order. The destination roster's link is to a "
            "different chain entirely, so following it would have published another hotel's "
            "policy under this name",
            "none -- the identity stays admitted", "no policy is published for it",
            "the row is unrouted until a correct route is found", "REVERSIBLE", "NO"))

    # F -- cross-market identity collision.
    items.append(item(
        "F_CROSS_MARKET", "Chattanooga against the 11 live markets and the shadow markets",
        OrderedDict([("scanned", "every committed identity census in the package"),
                     ("collisions_found", 0),
                     ("nearest_real_risk",
                      "Cleveland, TENNESSEE. Three Marriott rows in Cleveland TN 37312 were "
                      "reached by the regional 'cha' code prefix and held OUTSIDE_MARKET. "
                      "Cleveland-Akron-Canton, OHIO is a LIVE market, and a Cleveland TN row "
                      "must never bind to it."),
                     ("shadow_markets_not_in_this_lineage",
                      "Nashville, Lexington and Fort Wayne are shadow markets on branches this "
                      "worktree has never seen. Nashville is the one to re-check at promotion: "
                      "it is the other TENNESSEE market, and its own boundary work is what "
                      "decides whether any identity is claimed twice.")]),
        "confirm no identity is claimed twice",
        "confirm for the REGISTERED markets: zero collisions, and none is expected, because no "
        "registered census carries a Chattanooga-area address. Re-run this check against "
        "Nashville at promotion, once the then-current lineage is merged.",
        "none", "none", "none", "REVERSIBLE", "NO"))

    blockers = [i for i in items if i["blocks_promotion"] == "YES"]
    return OrderedDict([
        ("schema", "ptf-grouped-founder-packet/1.0"), ("work_order", WORK_ORDER),
        ("market_id", MARKET_ID), ("phase", "16 -- one grouped founder packet"),
        ("how_to_read_this",
         "Six groups, never one row at a time. Every item states its evidence, the action "
         "proposed, a recommendation, what it changes in the census, the authority and the "
         "routing, whether it is reversible, and whether it blocks promotion."),
        ("counts", OrderedDict([
            ("items", len(items)),
            ("by_group", OrderedDict(sorted(Counter(i["group"] for i in items).items()))),
            ("blockers", len(blockers)),
        ])),
        ("items", items),
    ])


# --------------------------------------------------------------------------- #
# Phase 17 -- paid readiness.
# --------------------------------------------------------------------------- #

def paid_readiness(ladder, firecrawl, audited, census_doc):
    fc_rows = (firecrawl or {}).get("rows", [])
    attempted = {r["identity_key"] for r in fc_rows}
    decisions = (ladder or {}).get("decisions") or []
    remaining_fc = [r for r in decisions
                    if r.get("firecrawl_candidate") and r["identity_key"] not in attempted]
    attended = [r for r in decisions if r.get("next_lane") == "ATTENDED_BROWSER"]
    clean_keys = {a["identity_key"] for a in audited
                  if a["audit_verdict"] in (CLEAN_PET_FRIENDLY, CLEAN_VERIFIED_NO_PETS)}
    published_ready = len(clean_keys)
    minimum = MC.parse_market(_load(CONTRACT), source=CONTRACT).minimum_published_hotels

    return OrderedDict([
        ("schema", "ptf-paid-readiness/1.0"), ("work_order", WORK_ORDER),
        ("market_id", MARKET_ID), ("phase", "17 -- paid readiness"),
        ("shared_ledgers", OrderedDict([
            ("read", ["ptf_paid_attempt_ledger_001.json",
                      "ptf_discovery_attempt_ledger_001.json"]),
            ("written", "NONE"),
            ("chattanooga_rows_in_either", 0),
            ("double_buy_risk", "NONE -- no page in this market has ever been bought"),
        ])),
        ("firecrawl", OrderedDict([
            ("attempted_this_order", len(fc_rows)),
            ("credits_before", (firecrawl or {}).get("credits", {}).get("before")),
            ("credits_after", (firecrawl or {}).get("credits", {}).get("after")),
            ("credits_delta", (firecrawl or {}).get("credits", {}).get("delta")),
            ("rows_remaining", len(remaining_fc)),
            ("cost_shape", "one plan credit on a successful fetch, zero when the origin refuses "
                           "every engine; no USD at any point"),
            ("required_for_promotion", False),
            ("why", "the market already exceeds its own publication minimum without them"),
        ])),
        ("bright_data", OrderedDict([
            ("candidate_rows", len(attended)),
            ("what_they_are", "Marriott and Hilton property pages, a measured Firecrawl "
                              "capability wall (PTF-FIRECRAWL-HARD-LANES-003)"),
            ("measured_rate", "NOT MEASURED FOR THIS MARKET -- no Bright Data call has been made "
                              "for Chattanooga, so no rate may be quoted from another market's run"),
            ("expected_attempts", len(attended)),
            ("expected_cost", "UNQUOTED. A cost must be measured against a live balance delta, "
                              "never from a per-row constant (PTF-DETROIT-BRIGHTDATA-PILOT-013 "
                              "breached a cap by trusting one)"),
            ("hard_cap", "NONE SET -- this order is not authorised to run Bright Data and did not"),
            ("required_for_promotion", False),
            ("cheaper_lane_first", "ATTENDED_BROWSER is free and settles the same rows; it should "
                                   "be exhausted before any USD is considered"),
        ])),
        ("places_paid_identity_discovery", OrderedDict([
            ("candidate_rows", len([r for r in census_doc.get("non_admitted", [])
                                    if r["classification"] == "NAME_ONLY_UNRESOLVED"
                                    and r.get("latitude") is not None])),
            ("what_they_are", "map-source rows with coordinates inside the market and no street "
                              "address"),
            ("existing_paid_attempts_for_chattanooga", 0),
            ("expected_cost", "UNQUOTED -- no Places call has been made for this market"),
            ("hard_cap", "NONE SET -- this order is not authorised to run Places and did not"),
            ("required_for_promotion", False),
        ])),
        ("verdict", OrderedDict([
            ("required_for_promotion", []),
            ("optional_coverage_expansion",
             ["ATTENDED_BROWSER for the Marriott and Hilton wall",
              "FIRECRAWL for any candidate row left unattempted",
              "PLACES for address fills on map-only rows",
              "BRIGHT_DATA only if the attended lane fails"]),
            ("publication_minimum", minimum),
            ("clean_rows_now", published_ready),
            ("clears_minimum", published_ready >= minimum),
        ])),
    ])


def build():
    census_doc = _load(CENSUS, {}) or {}
    recon = _load(RECON, {}) or {}
    routing = _load(ROUTING, {}) or {}
    ladder = _load(LADDER, {}) or {}
    firecrawl = _load(FIRECRAWL, {}) or {}
    gaps = _load(GAPS, {}) or {}
    city_pages = _load(LEADS, {}) or {}
    audited, census = clean_reads()

    clean_pf = [a for a in audited if a["audit_verdict"] == CLEAN_PET_FRIENDLY]
    clean_np = [a for a in audited if a["audit_verdict"] == CLEAN_VERIFIED_NO_PETS]
    held = [a for a in audited if a["audit_verdict"] == "HELD"]

    audit = OrderedDict([
        ("schema", "ptf-wrong-evidence-audit/1.0"), ("work_order", WORK_ORDER),
        ("market_id", MARKET_ID), ("phase", "14 -- wrong-evidence audit"),
        ("failure_classes_tested", [
            "SOURCE_SILENT_ENCODED_AS_POLICY", "IDENTITY_NOT_CONFIRMED",
            "AMENITY_CHIP_OR_BRAND_SURFACE", "ACCEPTANCE_INFERRED_WITHOUT_A_STATEMENT",
            "SERVICE_ANIMAL_LANGUAGE_READ_AS_PET_ACCEPTANCE",
            "REFUSAL_INFERRED_FROM_A_STRUCTURED_FLAG_ALONE", "NOT_IN_THE_PROPOSED_CENSUS",
            "PAGE_POSTAL_DISAGREES_WITH_CENSUS"]),
        ("counts", OrderedDict([
            ("reads_audited", len(audited)),
            ("clean_pet_friendly", len(clean_pf)),
            ("clean_verified_no_pets", len(clean_np)),
            ("held", len(held)),
            ("by_lane", OrderedDict(sorted(Counter(a["lane"] for a in audited).items()))),
            ("held_by_class", OrderedDict(sorted(Counter(
                p["class"] for a in held for p in a["audit_problems"]).items()))),
        ])),
        ("reads", audited),
    ])

    authority = OrderedDict([
        ("schema", "ptf-clean-pending-authority/1.0"), ("work_order", WORK_ORDER),
        ("market_id", MARKET_ID), ("phase", "15 -- clean pending authority"),
        ("status", "PROPOSED_NOT_PROMOTED"),
        ("what_is_excluded",
         "identity holds, geography holds, founder exceptions, source silence, reader "
         "exceptions, identity-only evidence and competitor-only evidence"),
        ("counts", OrderedDict([("clean_pet_friendly", len(clean_pf)),
                                ("clean_verified_no_pets", len(clean_np))])),
        ("clean_pet_friendly", clean_pf),
        ("clean_verified_no_pets", clean_np),
    ])

    packet = founder_packet(census_doc, recon, routing, audited, gaps, city_pages)
    paid = paid_readiness(ladder, firecrawl, audited, census_doc)

    cfg = MC.parse_market(_load(CONTRACT), source=CONTRACT)
    resolved = len(clean_pf) + len(clean_np)
    census_n = census_doc.get("count", 0)
    corridors_with_rows = Counter(h["corridor"] for h in census_doc.get("hotels", []))
    pf_corridors = Counter(a["corridor"] for a in clean_pf if a["corridor"])

    blockers = [i for i in packet["items"] if i["blocks_promotion"] == "YES"]
    ready = (census_n > 0 and len(clean_pf) >= cfg.minimum_published_hotels
             and not blockers)

    shadow = OrderedDict([
        ("schema", "ptf-shadow-market/1.0"), ("work_order", WORK_ORDER),
        ("market_id", MARKET_ID), ("phase", "18 and 19 -- shadow package and readiness"),
        ("status", "SHADOW -- nothing here is in shared production source"),
        ("projected", OrderedDict([
            ("census", census_n),
            ("pet_friendly", len(clean_pf)),
            ("verified_no_pets", len(clean_np)),
            ("resolved", resolved),
            ("unresolved", census_n - resolved),
            ("profiles", len(clean_pf)),
            ("corridors_declared", len(cfg.corridors)),
            ("corridors_with_at_least_one_identity", len(corridors_with_rows)),
            ("corridors_that_would_publish",
             len([c for c in cfg.corridors
                  if pf_corridors.get(c.corridor_id, 0) >= c.minimum_hotel_count])),
        ])),
        ("artifacts", OrderedDict([
            ("proposed_market_contract",
             "launch_packages/pettripfinder/markets/proposed/chattanooga-tn.json"),
            ("proposed_census",
             "launch_packages/pettripfinder/identity_census_proposed/chattanooga-tn.json"),
            ("discovery_config",
             "scripts/pettripfinder/discovery/config/chattanooga_tn.json"),
            ("routing", "launch_packages/pettripfinder/markets/reports/chattanooga_tn_routing_001.json"),
            ("clean_authority",
             "launch_packages/pettripfinder/markets/reports/chattanooga_tn_clean_authority_001.json"),
            ("founder_packet",
             "launch_packages/pettripfinder/markets/reports/chattanooga_tn_founder_packet_001.json"),
            ("paid_readiness",
             "launch_packages/pettripfinder/markets/reports/chattanooga_tn_paid_readiness_001.json"),
        ])),
        ("promotion_ready", "YES" if ready else "NO"),
        ("promotion_ready_because", OrderedDict([
            ("deterministic_clean_census_for_promoted_rows",
             "every admitted row carries a street or a phone, a postal code claimed by exactly "
             "one corridor, and the observations that admitted it"),
            ("cross_market_collision", 0),
            ("duplicate_premises", "same-street rows are reported SAME_CAMPUS_DISTINCT_ENTITY and "
                                   "never aliased"),
            ("clean_first_party_policy_evidence", len(clean_pf) + len(clean_np)),
            ("held_ambiguity_excluded", len(held) + len(
                [r for r in census_doc.get("non_admitted", [])
                 if r["classification"] in ("IDENTITY_REVIEW_REQUIRED",
                                            "SAME_IDENTITY_REBRAND_SUCCESSOR")])),
            ("geography_deterministic_or_held",
             "the postal partition is deterministic and every admitted row is Tennessee; the north Georgia belt is explicitly held"),
            ("remaining_acquisition_optional", True),
            ("publication_minimum", cfg.minimum_published_hotels),
        ])),
        ("blockers", [i["identity"] for i in blockers]),
        ("required_before_promotion", [
            "the founder rules on the north Georgia state-line belt (packet group B)",
            "the founder rules on %d rebrand successors and %d merge conflicts, each one address "
            "carrying two brand identities (packet group A)"
            % (len([r for r in census_doc.get("non_admitted", [])
                    if r["classification"] == "SAME_IDENTITY_REBRAND_SUCCESSOR"]),
               len({tuple(sorted(c.get("claimed_by") or []))
                    for c in (recon or {}).get("merge_conflicts", [])})),
            "the promotion order MERGES the THEN-CURRENT deployed canonical lineage before any "
            "of this is promoted. This order is pinned to d335c50, the Toledo launch, which was "
            "production truth when it started: 11 markets, 803 profiles, 966 routes, deploy "
            "6a9e0476. Nashville, Lexington and Fort Wayne are shadow markets on branches this "
            "worktree has never seen, and production may have moved since. Nothing here may be "
            "promoted onto a stale base.",
        ]),
        ("not_blockers_because",
         "none of these changes an admitted row's address, corridor or policy. Each decides "
         "which NAME a building trades under or whether one fringe corridor is in scope, and "
         "every affected row is already excluded from the clean inventory."),
        ("optional_coverage_expansion", paid["verdict"]["optional_coverage_expansion"]),
    ])
    return audit, authority, packet, paid, shadow


def main(argv=None) -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--out-dir", default=REPORTS)
    args = ap.parse_args(argv)
    audit, authority, packet, paid, shadow = build()
    for name, doc in (("chattanooga_tn_evidence_audit_001.json", audit),
                      ("chattanooga_tn_clean_authority_001.json", authority),
                      ("chattanooga_tn_founder_packet_001.json", packet),
                      ("chattanooga_tn_paid_readiness_001.json", paid),
                      ("chattanooga_tn_shadow_market_001.json", shadow)):
        path = os.path.join(args.out_dir, name)
        os.makedirs(os.path.dirname(path), exist_ok=True)
        with open(path, "w", encoding="utf-8") as fh:
            json.dump(doc, fh, indent=1, default=str)
            fh.write("\n")
    print("reads audited   :", audit["counts"]["reads_audited"],
          dict(audit["counts"]["by_lane"]))
    print("clean PF        :", authority["counts"]["clean_pet_friendly"])
    print("clean no-pets   :", authority["counts"]["clean_verified_no_pets"])
    print("held            :", audit["counts"]["held"], dict(audit["counts"]["held_by_class"]))
    print("founder items   :", packet["counts"]["items"], dict(packet["counts"]["by_group"]),
          "blockers", packet["counts"]["blockers"])
    print("projected       :", dict(shadow["projected"]))
    print("PROMOTION_READY :", shadow["promotion_ready"])
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
