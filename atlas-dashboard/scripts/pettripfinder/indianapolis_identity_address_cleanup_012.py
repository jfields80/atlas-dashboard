# -*- coding: utf-8 -*-
"""PTF-INDIANAPOLIS-IDENTITY-ADDRESS-CLEANUP-012 -- zero-cost identity/address
cleanup of the Indianapolis SHADOW census.

SHADOW ONLY. Touches ``identity_census_admission/indianapolis-in.json`` and the
review register; never the pinned census, the policy package, the release
contract, the final partition or the deployment manifest. No provider is
called: every proof below is either an artifact already on canonical or a free
first-party read made attended on 2026-09-01 and quoted verbatim.

WHAT IS DETERMINISTIC AND APPLIED HERE (the IDR-005-001 precedent: an address
supersession with two independent property signals, or a route bound on an
exact identity, is a shadow action and not a founder question):

  comfort inn east indianapolis      7015 Western Select Dr -> 2295 N. Shadeland
        proof: the row is PHONE-bound to Choice IN099 (owned Places bind on
        (317) 359-9999 == census 3173599999) and IN099's own page prints
        2295 N. Shadeland and the same telephone.
  comfort suites indianapolis airport 2181 W Southern Ave -> 2750 Fortune Cir W
        proof: the row's OWN official_url is property IN293, and IN293's page
        prints 2750 Fortune Circle West / (317) 759-2371; Choice lists exactly
        one Comfort Suites near the airport. The OSM candidate held at 2750
        Fortune Circle West is therefore this same hotel -- an alias, not a
        missing identity.
  wingate by wyndham ... plainfield   6010 Gateway Dr -> 6300 Gateway Dr
        proof: Wingate's own page (6300, +1-317-204-2457), the owned Places bind
        (6300 Gateway Dr) and the OSM candidate (6300) agree; and 6010 Gateway
        Drive is a DIFFERENT hotel already in the census (Baymont Plainfield,
        3172039321).
  echo suites ... indianapolis ameriplex 8805 Ameriplex Dr -> 5831 Alta Lake Dr
        proof: the page named EXACTLY "ECHO Suites Extended Stay by Wyndham
        Indianapolis AmeriPlex" prints 5831 Alta Lake Drive / +1-317-283-9434;
        Wyndham's Indianapolis inventory carries exactly ONE ECHO Suites; the
        owned Places bind returned 5831 Alta Lk Dr.
  quality inn noblesville indianapolis 17070 Dragonfly Drive -> Lane (cosmetic)
        proof: Choice IN338 (Choice's only Noblesville property) prints 17070
        Dragonfly Lane; the owned Places bind returned 17070 Dragonfly Dr.
  wyndham indianapolis west          route corrected to the page now titled
        "Wyndham Indianapolis Airport": same brand, same street 2544 Executive
        Drive, same postal 46241, and the page telephone +1-317-248-2481 IS the
        owned telephone 3172482481. The old slug soft-404s. The row is STILL
        ACTIVE and was never closed; its display name is queued for the founder.

WHAT IS RECORDED AND QUEUED, NOT DECIDED: every retirement, merge and rename
(IDR-007-001, three duplicate pairs, AmericInn Fishers, Ramada Airport, the
Wyndham West name) goes to indianapolis_in_founder_packet_012.json.
"""
from __future__ import annotations

import json
import sys
from collections import Counter, OrderedDict
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

WORK_ORDER = "PTF-INDIANAPOLIS-IDENTITY-ADDRESS-CLEANUP-012"
MARKET = "indianapolis-in"
READ_AT = "2026-09-01"
BOUND_AT = "2026-09-01T02:30:00Z"
PKG = _REPO_ROOT / "launch_packages" / "pettripfinder"
SHADOW = PKG / "identity_census_admission" / "indianapolis-in.json"
REGISTER = PKG / "indianapolis_in_identity_review_register_002.json"
COHORT_007 = PKG / "indianapolis_in_unrouted_cohort_007.json"
ROUTING_007 = PKG / "indianapolis_in_routing_results_007.json"
OUT_RECORD = PKG / "indianapolis_in_identity_address_cleanup_012.json"
OUT_PACKET = PKG / "indianapolis_in_founder_packet_012.json"
OUT_COHORT = PKG / "indianapolis_in_unrouted_cohort_012.json"

FREE = "$0 -- free first-party read, attended, 2026-09-01"


# --------------------------------------------------------------------------- #
# formatting-preserving JSON io
# --------------------------------------------------------------------------- #

def _load(path):
    text = path.read_text(encoding="utf-8-sig")
    doc = json.loads(text, object_pairs_hook=OrderedDict)
    fmt = None
    for indent in (1, 2, 4):
        for ea in (True, False):
            for nl in ("\n", ""):
                if json.dumps(doc, indent=indent, ensure_ascii=ea) + nl == text:
                    fmt = (indent, ea, nl)
    if fmt is None:
        fmt = (1, False, "\n")
    return doc, fmt


def _save(path, doc, fmt):
    path.write_text(json.dumps(doc, indent=fmt[0], ensure_ascii=fmt[1]) + fmt[2],
                    encoding="utf-8", newline="\n")


def _new(path, doc):
    path.write_text(json.dumps(doc, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8", newline="\n")


# --------------------------------------------------------------------------- #
# the deterministic actions
# --------------------------------------------------------------------------- #

SUPERSESSIONS = [
    OrderedDict([
        ("identity_key", "comfort inn east indianapolis"),
        ("address", "2295 N. Shadeland"), ("postal_code", "46219"),
        ("phone", "3173599999"),
        ("official_url", "https://www.choicehotels.com/indiana/indianapolis/comfort-inn-hotels/in099"),
        ("property_code", "IN099"),
        ("verdict", "A. ADDRESS_SUPERSESSION"),
        ("cause", "D. the OpenStreetMap candidate carried a street no first-party source ever confirmed; the identity was already PHONE-bound"),
        ("proof", [
            "owned Places bind (PTF-INDIANAPOLIS-PLACES-BROADER-RECOVERY-010): bind_method PHONE, census 3173599999 == matched (317) 359-9999, postal 46219, names compatible",
            "Choice IN099 own page read attended 2026-09-01 prints '2295 N. Shadeland, Indianapolis, IN, 46219, US' and '(317) 359-9999' -- the SAME telephone",
            "Choice's own Indianapolis-area listing names exactly one 'Comfort Inn Indianapolis East', at 2295 N. Shadeland",
            "the earlier acquisition (PTF-INDIANAPOLIS-ADDRESS-REVIEW-006 queue) had already recorded page street 2295 N. Shadeland verbatim against the census street",
        ]),
        ("bound_on", "telephone agrees exactly (Places bind and the property page)"),
        ("page_telephone", "3173599999"),
    ]),
    OrderedDict([
        ("identity_key", "comfort suites indianapolis airport"),
        ("address", "2750 Fortune Circle West"), ("postal_code", "46241"),
        ("phone", "3177592371"),
        ("official_url", "https://www.choicehotels.com/indiana/indianapolis/comfort-suites-hotels/in293"),
        ("property_code", "IN293"),
        ("verdict", "A. ADDRESS_SUPERSESSION"),
        ("cause", "D. the prior-census row carried a street and telephone no source ever confirmed, while its own official_url already named property IN293"),
        ("proof", [
            "the census row's own official_url is https://www.choicehotels.com/indiana/indianapolis/comfort-suites-hotels/in293 -- property code IN293 is the identity anchor",
            "Choice IN293 own page read attended 2026-09-01: 'Comfort Suites near Indianapolis Airport', '2750 Fortune Circle West, Indianapolis, IN, 46241, US', '(317) 759-2371'",
            "Choice's own Indianapolis-area listing carries exactly ONE Comfort Suites near the airport (IN293); no Choice property is listed at 2181 West Southern Avenue",
            "the OSM candidate dc_38bda8c5e06cb16b held at admission (2750 Fortune Circle West, 46241) names this same building -- ALREADY_REGISTERED_ALIAS, not a missing identity",
        ]),
        ("bound_on", "property code IN293 in the row's own official URL; page telephone read"),
        ("page_telephone", "3177592371"),
        ("resolves_collision_candidate", "dc_38bda8c5e06cb16b"),
    ]),
    OrderedDict([
        ("identity_key", "wingate by wyndham indianapolis airport plainfield"),
        ("address", "6300 Gateway Drive"), ("postal_code", "46168"),
        ("phone", "3172042457"),
        ("official_url", "https://www.wyndhamhotels.com/wingate/plainfield-indiana/wingate-by-wyndham-indianapolis-airport-plainfield/overview"),
        ("property_code", ""),
        ("verdict", "A. ADDRESS_SUPERSESSION"),
        ("cause", "D. the prior-census street 6010 Gateway Drive belongs to a DIFFERENT hotel already in this census (Baymont Inn & Suites Plainfield Indianapolis Airport, 3172039321)"),
        ("proof", [
            "Wingate's own page read attended 2026-09-01: 'Wingate by Wyndham Indianapolis Airport Plainfield', '6300 Gateway Drive', '+1-317-204-2457'",
            "owned Places bind (010): returned_address '6300 Gateway Dr, Plainfield, IN 46168, USA' for this exact name",
            "OSM candidate dc_471a3f27e0f70810 held at admission: 6300 Gateway Drive, 46168 -- ALREADY_REGISTERED_ALIAS of this row",
            "census row 'baymont inn and suites plainfield indianapolis airport' sits at 6010 Gateway Drive with its own telephone, so 6010 cannot also be the Wingate",
        ]),
        ("bound_on", "exact property name on the page + Places and OSM agree on the street + the old street is another hotel's"),
        ("page_telephone", "3172042457"),
        ("resolves_collision_candidate", "dc_471a3f27e0f70810"),
    ]),
    OrderedDict([
        ("identity_key", "echo suites extended stay by wyndham indianapolis ameriplex"),
        ("address", "5831 Alta Lake Drive"), ("postal_code", "46241"),
        ("phone", "3172839434"),
        ("official_url", "https://www.wyndhamhotels.com/echo-suites/indianapolis-indiana/echo-suites-extended-stay-indianapolis-ameriplex/overview"),
        ("property_code", ""),
        ("verdict", "A. ADDRESS_SUPERSESSION"),
        ("cause", "D. the prior-census street 8805 Ameriplex Drive was never confirmed by any source; the property's own page and Places both print Alta Lake Drive"),
        ("proof", [
            "Wyndham's own page read attended 2026-09-01: heading 'ECHO Suites Extended Stay by Wyndham Indianapolis AmeriPlex' (the exact identity), '5831 Alta Lake Drive', '+1-317-283-9434'",
            "Wyndham's own Indianapolis search inventory carries exactly ONE ECHO Suites (brand filter count 1), so the name denotes one building",
            "owned Places bind (010): returned 'ECHO Suites Extended Stay by Wyndham Indianapolis AmeriPlex', '5831 Alta Lk Dr, Indianapolis, IN 46241, USA'",
            "the shadow also holds an OSM stub 'echo suites extended stay by wyndham' at 5831 / 46241 -- the same building; its retirement as a duplicate is queued for the founder (IDR-012-003), not decided here",
        ]),
        ("bound_on", "exact property name on the page + single-property brand inventory + Places agrees on the street"),
        ("page_telephone", "3172839434"),
    ]),
    OrderedDict([
        ("identity_key", "quality inn noblesville indianapolis"),
        ("address", "17070 Dragonfly Lane"), ("postal_code", "46060"),
        ("phone", ""),
        ("official_url", "https://www.choicehotels.com/indiana/noblesville/quality-inn-hotels/in338"),
        ("property_code", "IN338"),
        ("verdict", "ADDRESS_CONFIRMED_CURRENT (cosmetic street-type correction Drive -> Lane)"),
        ("cause", "C. cosmetic: same number and street name, the suffix differed"),
        ("proof", [
            "Choice's own Noblesville listing read attended 2026-09-01: 'Quality Inn Noblesville-Indianapolis', '17070 Dragonfly Lane, Noblesville, IN, 46060, US' -- Choice's ONLY property in Noblesville",
            "owned Places bind (010): 'Quality Inn Noblesville-Indianapolis', '17070 Dragonfly Dr, Noblesville, IN 46060, USA'",
            "the acquisition had already reached IN338 for this row and recorded page street 17070 Dragonfly Lane",
        ]),
        ("bound_on", "street number and name agree; Choice lists exactly one Noblesville property (IN338)"),
        ("page_telephone", ""),
    ]),
]

ROUTE_ONLY = [
    OrderedDict([
        ("identity_key", "wyndham indianapolis west"),
        ("official_url", "https://www.wyndhamhotels.com/wyndham/indianapolis-indiana/wyndham-indianapolis-airport/overview"),
        ("phone", "3172482481"),
        ("classification", "STILL_ACTIVE -- SAME_IDENTITY, page now titled 'Wyndham Indianapolis Airport'"),
        ("proof", [
            "owned record for this identity carries telephone 3172482481 and the old URL .../wyndham-indianapolis-west/overview, which now answers a soft-404 (routing 007)",
            "Wyndham's own Indianapolis search inventory read attended 2026-09-01 lists 'Wyndham Indianapolis Airport' at '2544 Executive Drive, Indianapolis, Indiana 46241' -- the census street and postal",
            "that page read attended 2026-09-01 prints '+1-317-248-2481' -- the SAME telephone",
            "same brand family (WYNDHAM), same street, same postal, same telephone: an exact identity; only the locality word in the display name changed (West -> Airport)",
        ]),
        ("bound_on", "telephone agrees exactly; same brand, street and postal; display name differs and is queued for the founder (IDR-012-006)"),
        ("page_address", "2544 Executive Drive"), ("page_telephone", "3172482481"),
    ]),
]


def apply_shadow(shadow):
    by = {h["identity_key"]: h for h in shadow["hotels"]}
    applied = []
    for s in SUPERSESSIONS:
        h = by[s["identity_key"]]
        was = OrderedDict((k, h.get(k, "")) for k in (
            "identity_key", "canonical_name", "address", "postal_code", "official_url",
            "phone", "provenance", "source", "source_id", "observed_at"))
        h["supersession"] = OrderedDict([
            ("work_order", WORK_ORDER),
            ("ruling", "deterministic shadow action under the IDR-005-001 precedent; no founder ruling required"),
            ("verdict", s["verdict"]), ("cause", s["cause"]), ("was", was),
            ("proof", s["proof"]),
            ("two_independent_property_signals", True),
            ("lineage_preserved", True), ("second_identity_created", False),
            ("policy_published", False),
        ])
        h["address"] = s["address"]
        h["postal_code"] = s["postal_code"]
        if s["phone"]:
            h["phone"] = s["phone"]
        prior_url = h.get("official_url", "")
        h["official_url"] = s["official_url"]
        h.setdefault("routing_history", []).append(OrderedDict([
            ("work_order", WORK_ORDER), ("prior_official_url", prior_url),
            ("bound_url", s["official_url"]), ("bound_on", s["bound_on"]),
            ("method", "owned_artifact_url_confirmed_by_attended_first_party_read"),
            ("page_address", s["address"]), ("page_telephone", s["page_telephone"]),
            ("census_address", was["address"]), ("cost", FREE), ("bound_at", BOUND_AT),
        ]))
        if s.get("property_code"):
            h["property_code"] = s["property_code"]
        applied.append(OrderedDict([("identity_key", s["identity_key"]), ("action", "ADDRESS_SUPERSESSION_AND_ROUTE"),
                                    ("from", was["address"]), ("to", s["address"]), ("bound_url", s["official_url"])]))
        if s.get("resolves_collision_candidate"):
            for c in shadow.get("identity_key_collisions", []):
                if c["identity_key"] == s["identity_key"]:
                    c["resolution_012"] = OrderedDict([
                        ("work_order", WORK_ORDER),
                        ("held_candidate_id", s["resolves_collision_candidate"]),
                        ("classification", "ALREADY_REGISTERED_ALIAS"),
                        ("note", "the held candidate names the same building the kept row now carries after its address supersession; nothing to add"),
                    ])
    for r in ROUTE_ONLY:
        h = by[r["identity_key"]]
        prior_url = h.get("official_url", "")
        h["official_url"] = r["official_url"]
        h["phone"] = r["phone"]
        h.setdefault("routing_history", []).append(OrderedDict([
            ("work_order", WORK_ORDER), ("prior_official_url", prior_url),
            ("bound_url", r["official_url"]), ("bound_on", r["bound_on"]),
            ("method", "attended_first_party_inventory_and_page_read"),
            ("page_address", r["page_address"]), ("page_telephone", r["page_telephone"]),
            ("census_address", h["address"]), ("cost", FREE), ("bound_at", BOUND_AT),
        ]))
        h["closure_review_012"] = OrderedDict([
            ("work_order", WORK_ORDER), ("was_classified", "PROPERTY_CLOSED_OR_CONVERTED (routing 007, brand soft-404)"),
            ("now", r["classification"]), ("proof", r["proof"]),
            ("display_name_change_queued", "IDR-012-006"),
        ])
        applied.append(OrderedDict([("identity_key", r["identity_key"]), ("action", "ROUTE_CORRECTION_EXACT_IDENTITY"),
                                    ("bound_url", r["official_url"])]))
    return applied


# --------------------------------------------------------------------------- #
# the review register and the founder packet
# --------------------------------------------------------------------------- #

QUEUE_RESOLUTIONS = OrderedDict([
    ("comfort inn east indianapolis", "ADDRESS_SUPERSESSION -- applied to the shadow (phone-bound IN099)"),
    ("echo suites extended stay by wyndham indianapolis ameriplex", "ADDRESS_SUPERSESSION -- applied to the shadow (exact-name page + single-property inventory + Places); the OSM stub at 5831 is a duplicate queued as IDR-012-003"),
    ("quality inn and suites noblesville indianapolis", "IDENTITY_UNRESOLVED -- DUPLICATE_OF_EXISTING: Choice lists exactly one Noblesville property (IN338, 17070 Dragonfly Lane), which the OSM row already carries; retirement queued as IDR-012-001"),
    ("quality inn brownsburg indianapolis west", "IDENTITY_UNRESOLVED -- DUPLICATE_OF_EXISTING: Choice's only Brownsburg Quality Inn is IN441 at 31 Maplehurst Drive, which the OSM row 'quality inn and suites brownsburg indianapolis west' already carries; retirement queued as IDR-012-002"),
    ("quality inn noblesville indianapolis", "ADDRESS_CONFIRMED_CURRENT -- cosmetic Drive -> Lane corrected in the shadow; routed to IN338"),
    ("wingate by wyndham indianapolis airport plainfield", "ADDRESS_SUPERSESSION -- applied to the shadow (page + Places + OSM agree on 6300; 6010 is the Baymont)"),
])

PACKET_ITEMS = [
    OrderedDict([
        ("review_id", "IDR-007-001"), ("property", "la quinta inn (census) / Baymont by Wyndham Indianapolis Northwest (page)"),
        ("exact_issue", "OpenStreetMap single-source census row 'la quinta inn' at 3871 West 92nd Street 46268 with no telephone and no website; the only first-party page at that street is Baymont by Wyndham Indianapolis Northwest (3871 W 92nd St, +1-317-426-0215). Brand differs, so the routing gate held it."),
        ("current_identity", "la quinta inn -- bare brand key, no locality, no phone, no URL"),
        ("proposed_action", "SAME_IDENTITY_REBRAND_SUCCESSOR: rename the row to 'Baymont by Wyndham Indianapolis Northwest', bind the Baymont page, keep 'La Quinta Inn' in lineage (the WoodSpring -> ESA Plainfield precedent, FOUNDER RULING 1)"),
        ("evidence", [
            "Baymont by Wyndham Indianapolis Northwest own page read attended 2026-09-01: '3871 W 92nd St, Indianapolis, Indiana 46268-3102', '+1-317-426-0215' -- street and postal agree exactly with the census row",
            "the census row is a SINGLE_SOURCE OpenStreetMap candidate with WEBSITE_MISSING and no telephone; no owned artifact carries a La Quinta telephone for this street",
            "Wyndham's own Indianapolis inventory read attended 2026-09-01 carries 4 La Quinta properties; the three the census already routes are Downtown (401 E Washington), Airport Executive Dr (2650 Executive Dr) and South (5120 Victory Dr); no La Quinta card at 92nd Street was observed among the loaded results",
            "Wyndham's inventory also shows 'Baymont by Wyndham Indianapolis Airport Lynhurst' at 5316 W. Southern Ave -- the census row 'la quinta inn indianapolis airport lynhurst' has evidently been re-flagged the same way (recorded here, out of scope)",
        ]),
        ("conflicting_signals", "a rebrand and a co-located pair produce identical street/postal evidence (the register's own words); the 4th La Quinta in Wyndham's inventory was not positively identified, so 'no La Quinta at 92nd' is not proven"),
        ("recommended_ruling", "A. SAME_IDENTITY_REBRAND_SUCCESSOR (a bare-brand OSM tag at a building Wyndham now sells as Baymont NW)"),
        ("census_impact", "shadow 268 -> 268 (rename, not add); the bare key 'la quinta inn' leaves the census"),
        ("route_impact", "one route bound (Baymont NW page)"), ("publication_impact", "none until a policy is read from the bound page"),
        ("reversibility", "full: lineage keeps the OSM row; the rename is a shadow write"),
    ]),
    OrderedDict([
        ("review_id", "IDR-012-001"), ("property", "quality inn and suites noblesville indianapolis (prior census, 16025 Promise Road)"),
        ("exact_issue", "two census rows for one hotel: this prior-census row and the OSM row 'quality inn noblesville indianapolis' (17070 Dragonfly Lane, now routed to IN338)"),
        ("current_identity", "quality inn and suites noblesville indianapolis, 16025 Promise Road 46060, no phone, no URL"),
        ("proposed_action", "DUPLICATE_OF_EXISTING -> retire this row; keep 'quality inn noblesville indianapolis' (IN338)"),
        ("evidence", ["Choice's own Noblesville listing read attended 2026-09-01: exactly ONE Choice property in Noblesville, 'Quality Inn Noblesville-Indianapolis', 17070 Dragonfly Lane (IN338)",
                      "the earlier acquisition for THIS row also reached IN338 and recorded page street 17070 Dragonfly Lane",
                      "16025 Promise Road was never confirmed by any source; the nearby Baymont Noblesville sits at 16025 Prosperity Drive"]),
        ("conflicting_signals", "none found"), ("recommended_ruling", "DUPLICATE_OF_EXISTING -- retire"),
        ("census_impact", "shadow 268 -> 267"), ("route_impact", "none (the surviving row is routed)"),
        ("publication_impact", "none"), ("reversibility", "full"),
    ]),
    OrderedDict([
        ("review_id", "IDR-012-002"), ("property", "quality inn brownsburg indianapolis west (prior census, 31 Brownsburg Place)"),
        ("exact_issue", "two census rows for one hotel: this prior-census row and the OSM row 'quality inn and suites brownsburg indianapolis west' (31 Maplehurst Drive)"),
        ("current_identity", "quality inn brownsburg indianapolis west, 31 Brownsburg Place 46112, no phone, no URL"),
        ("proposed_action", "DUPLICATE_OF_EXISTING -> retire this row; keep the OSM row and bind it to IN441"),
        ("evidence", ["Choice's own listing read attended 2026-09-01: 'Quality Inn & Suites Brownsburg - Indianapolis West', 31 Maplehurst Drive, Brownsburg 46112 -- Choice's only Quality Inn in Brownsburg (IN441)",
                      "the earlier acquisition for THIS row reached IN441 and recorded page street 31 Maplehurst Drive; same street number 31",
                      "'31 Brownsburg Place' was never confirmed by any source"]),
        ("conflicting_signals", "none found"), ("recommended_ruling", "DUPLICATE_OF_EXISTING -- retire; bind the surviving OSM row to IN441"),
        ("census_impact", "shadow -> -1"), ("route_impact", "+1 route on the surviving row"), ("publication_impact", "none"), ("reversibility", "full"),
    ]),
    OrderedDict([
        ("review_id", "IDR-012-003"), ("property", "echo suites extended stay by wyndham (OSM stub, '5831', 46241)"),
        ("exact_issue", "an OpenStreetMap stub with a truncated street ('5831') duplicates the prior-census row 'echo suites extended stay by wyndham indianapolis ameriplex', now superseded to 5831 Alta Lake Drive"),
        ("current_identity", "echo suites extended stay by wyndham -- bare brand key"),
        ("proposed_action", "DUPLICATE_OF_EXISTING -> retire the stub"),
        ("evidence", ["Wyndham's own Indianapolis inventory carries exactly ONE ECHO Suites (brand filter count 1)",
                      "the named row's page prints 5831 Alta Lake Drive / +1-317-283-9434 -- the stub's street number"]),
        ("conflicting_signals", "none found"), ("recommended_ruling", "DUPLICATE_OF_EXISTING -- retire"),
        ("census_impact", "shadow -> -1"), ("route_impact", "none"), ("publication_impact", "none"), ("reversibility", "full"),
    ]),
    OrderedDict([
        ("review_id", "IDR-012-004"), ("property", "americinn by wyndham fishers indianapolis (OSM, 9780 North by Northeast Boulevard 46037)"),
        ("exact_issue", "routing 007 classified it PROPERTY_CLOSED_OR_CONVERTED on a brand soft-404; this order sought the stronger evidence the doctrine asks for"),
        ("current_identity", "americinn by wyndham fishers indianapolis"),
        ("proposed_action", "PROPERTY_CONVERTED -> retire the row (ROUTING_RETIRED); the successor is ALREADY registered as 'comfort inn fishers indianapolis'"),
        ("evidence", ["owned Places record (PTF-INDIANAPOLIS-PLACES-QUALIFICATION-008): business_status CLOSED_PERMANENTLY, (317) 578-9000, 9780 N by NE Blvd",
                      "Wyndham's own Indianapolis inventory read attended 2026-09-01: the AmericInn brand filter carries NO property (no count), and the property page soft-404s (routing 007)",
                      "Choice's own listing read attended 2026-09-01: 'Comfort Inn & Suites Fishers - Indianapolis', 9780 N. by Northeast Boulevard, Fishers 46037 -- the same street, and that identity is already a census row"]),
        ("conflicting_signals", "the census holds THREE rows at 9780 North by Northeast Boulevard (this one, comfort inn fishers, staybridge suites fishers); whether Staybridge is a second building on the parcel is not examined here"),
        ("recommended_ruling", "PROPERTY_CONVERTED -- retire; successor already registered"),
        ("census_impact", "shadow -> -1"), ("route_impact", "one dead route retired"), ("publication_impact", "none"), ("reversibility", "full"),
    ]),
    OrderedDict([
        ("review_id", "IDR-012-005"), ("property", "ramada indianapolis airport (OSM, 5601 Fortune Circle West 46241)"),
        ("exact_issue", "routing 007 classified it PROPERTY_CLOSED_OR_CONVERTED on a brand soft-404"),
        ("current_identity", "ramada indianapolis airport"),
        ("proposed_action", "PROPERTY_CLOSED_OR_CONVERTED -> retire (ROUTING_RETIRED); successor unknown"),
        ("evidence", ["Wyndham's own Indianapolis inventory read attended 2026-09-01: the Ramada brand filter carries NO property (no count); the property page soft-404s (routing 007)",
                      "owned Places record (010) at capture time still returned 'Ramada by Wyndham Indianapolis Airport', 5601 Fortune Cir W, (317) 643-5699 -- a directory listing that has since lost its first-party page"]),
        ("conflicting_signals", "the Places listing existed at capture; no first-party successor at 5601 Fortune Circle West was found, so closed vs converted is not settled"),
        ("recommended_ruling", "PROPERTY_CLOSED_OR_CONVERTED -- retire the route; keep the row in lineage until a successor appears"),
        ("census_impact", "shadow -> -1 if retired"), ("route_impact", "one dead route retired"), ("publication_impact", "none"), ("reversibility", "full"),
    ]),
    OrderedDict([
        ("review_id", "IDR-012-006"), ("property", "wyndham indianapolis west (2544 Executive Drive 46241)"),
        ("exact_issue", "the hotel is open and routed (this order bound its current page on an exact telephone match); Wyndham now titles it 'Wyndham Indianapolis Airport'"),
        ("current_identity", "wyndham indianapolis west"),
        ("proposed_action", "NAME_CORRECTION: canonical/display name -> 'Wyndham Indianapolis Airport' (identity key unchanged, lineage kept)"),
        ("evidence", ["page +1-317-248-2481 == owned 3172482481; same brand, street, postal"]),
        ("conflicting_signals", "none"), ("recommended_ruling", "approve the display-name correction"),
        ("census_impact", "none"), ("route_impact", "none (already bound)"), ("publication_impact", "the published name, if ever published, would follow the page"), ("reversibility", "full"),
    ]),
]


def update_register(reg, applied):
    q = reg["address_review_queue_006"]
    for row in q["rows"]:
        row["resolution_012"] = QUEUE_RESOLUTIONS[row["identity_key"]]
    q["resolved_by_012"] = OrderedDict([
        ("applied_supersessions", 3), ("cosmetic_corrections", 1), ("duplicates_queued_for_founder", 2), ("unresolved", 0)])
    for r in reg["reviews"]:
        if r["review_id"] == "IDR-007-001":
            r["investigated_by_012"] = OrderedDict([
                ("outcome", "IDENTITY_UNRESOLVED mechanically -- no owned telephone to compare and the brand differs; recommended ruling prepared in indianapolis_in_founder_packet_012.json"),
                ("recommended", "A. SAME_IDENTITY_REBRAND_SUCCESSOR"),
                ("first_party_read", "Baymont by Wyndham Indianapolis Northwest page, 2026-09-01: 3871 W 92nd St 46268-3102, +1-317-426-0215"),
            ])
    for f in reg.get("further_findings_registered_by_004", []):
        pass
    new_reviews = []
    for p in PACKET_ITEMS:
        if p["review_id"] == "IDR-007-001":
            continue
        new_reviews.append(OrderedDict([
            ("review_id", p["review_id"]),
            ("review_state", "DUPLICATE_IDENTITY_REVIEW" if p["review_id"] in ("IDR-012-001", "IDR-012-002", "IDR-012-003")
             else "CLOSURE_REVIEW" if p["review_id"] in ("IDR-012-004", "IDR-012-005") else "NAME_CORRECTION_REVIEW"),
            ("raised_by", WORK_ORDER), ("question", p["exact_issue"]), ("identity_key", p["property"].split(" (")[0]),
            ("proposed_action", p["proposed_action"]), ("evidence", p["evidence"]),
            ("recommended_ruling", p["recommended_ruling"]),
            ("forbidden_until_ruled", ["retiring, merging or renaming the identity", "publishing anything for it"]),
            ("default_if_never_ruled", "the row stays as it is in the shadow census"),
            ("acted_on", False),
        ]))
    reg["reviews"].extend(new_reviews)
    reg["applied_by_012"] = applied
    return reg


# --------------------------------------------------------------------------- #
# the routing backlog, rebuilt
# --------------------------------------------------------------------------- #

def rebuild_cohort(shadow, applied):
    import importlib.util
    spec = importlib.util.spec_from_file_location(
        "cp", str(_REPO_ROOT / "scripts" / "pettripfinder" / "indianapolis_routing_cost_plan_003.py"))
    cp = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(cp)
    c7 = json.loads(COHORT_007.read_text(encoding="utf-8-sig"))
    r7 = json.loads(ROUTING_007.read_text(encoding="utf-8-sig"))["classifications"]
    routed = {a["identity_key"] for a in applied}
    review_first = {"la quinta inn", "quality inn and suites noblesville indianapolis",
                    "quality inn brownsburg indianapolis west", "echo suites extended stay by wyndham"}
    closed = {"americinn by wyndham fishers indianapolis", "ramada indianapolis airport"}
    keys = [k for k in c7["identity_keys"] if k not in routed]
    seg = Counter()
    for k in keys:
        if k in review_first:
            s = "IDENTITY_REVIEW_FIRST"
        elif k in closed:
            s = "CLOSED_OR_CONVERTED"
        elif r7.get(k) == "ROUTE_NOT_FOUND" or cp.brand_of(k) in cp.FREE_ROUTING_PROVEN:
            s = "FREE_LANE_EXHAUSTED_THIS_RUN"
        elif cp.brand_of(k) in cp.FREE_ROUTING_REFUSED:
            s = "ROUTING_REPAIR_FIRST_PAID_DISCOVERY"
        else:
            s = "ROUTING_REPAIR_FIRST_INDEPENDENT"
        seg[s] += 1
    doc = OrderedDict([
        ("schema", c7["schema"]), ("what_this_is", "the Indianapolis unrouted cohort after the zero-cost identity/address cleanup: 007's cohort minus the rows this order routed on exact identity, with the rows now awaiting a founder retire/merge ruling held as IDENTITY_REVIEW_FIRST so no discovery is bought for a row that may leave the census"),
        ("market_id", MARKET), ("supersedes", "indianapolis_in_unrouted_cohort_007.json"),
        ("source_work_order", WORK_ORDER),
        ("scopes", OrderedDict([("audit_measured", len(keys)), ("whole_shadow_census", len(keys)),
                                ("how_whole_shadow_is_counted", c7["scopes"]["how_whole_shadow_is_counted"])])),
        ("routed_by_012", sorted(routed)),
        ("segments", OrderedDict(sorted(seg.items(), key=lambda kv: -kv[1]))),
        ("segment_rule", "IDENTITY_REVIEW_FIRST for rows under a pending founder ruling; CLOSED_OR_CONVERTED for rows proven closed/converted and awaiting retirement; FREE_LANE_EXHAUSTED_THIS_RUN for rows the free lane already tried (ROUTE_NOT_FOUND in 007) or whose brand the free lane covers; then PAID_DISCOVERY vs INDEPENDENT by brand family -- the same rule 007 applied"),
        ("count", len(keys)), ("identity_keys", keys),
        ("whole_shadow_identity_keys", keys),
    ])
    return doc


def main():
    shadow, sfmt = _load(SHADOW)
    reg, rfmt = _load(REGISTER)
    before = Counter(h["identity_key"] for h in shadow["hotels"])
    applied = apply_shadow(shadow)
    assert Counter(h["identity_key"] for h in shadow["hotels"]) == before
    assert shadow["count"] == 268 and len(shadow["hotels"]) == 268
    _save(SHADOW, shadow, sfmt)
    reg = update_register(reg, applied)
    _save(REGISTER, reg, rfmt)
    cohort = rebuild_cohort(shadow, applied)
    _new(OUT_COHORT, cohort)
    packet = OrderedDict([
        ("schema", "ptf-founder-packet/1.0"), ("work_order", WORK_ORDER), ("market_id", MARKET),
        ("generated_at", READ_AT), ("cost", OrderedDict([("paid_provider_calls", 0), ("usd_spent", 0.0), ("attended_page_loads", 11)])),
        ("one_sitting", "seven rulings; every one is a retire, merge or rename that doctrine reserves for the founder. Nothing here blocks the pending policy application; all of it precedes a pinned-census promotion."),
        ("resolved_without_you", applied),
        ("decisions_requested", PACKET_ITEMS),
        ("guarantees", ["pinned census 257 untouched", "live PF 56 untouched", "no provider called, $0", "every action above is a shadow write with lineage preserved"]),
    ])
    _new(OUT_PACKET, packet)
    record = OrderedDict([
        ("schema", "ptf-identity-address-cleanup/1.0"), ("work_order", WORK_ORDER), ("market_id", MARKET),
        ("generated_at", READ_AT), ("shadow_only", True), ("paid_provider_calls", 0), ("usd_spent", 0.0),
        ("attended_first_party_reads", [
            "https://www.choicehotels.com/indiana/indianapolis/comfort-suites-hotels/in293",
            "https://www.choicehotels.com/indiana/indianapolis/comfort-inn-hotels/in099",
            "https://www.choicehotels.com/indiana/noblesville/hotels",
            "https://www.wyndhamhotels.com/hotels/indianapolis-indiana (brand filter counts: La Quinta 4, ECHO Suites 1, Wingate 3, Baymont 8, AmericInn none, Ramada none)",
            "https://www.wyndhamhotels.com/baymont/indianapolis-indiana/baymont-inn-and-suites-indianapolis-northwest/overview",
            "https://www.wyndhamhotels.com/wyndham/indianapolis-indiana/wyndham-indianapolis-airport/overview",
            "https://www.wyndhamhotels.com/echo-suites/indianapolis-indiana/echo-suites-extended-stay-indianapolis-ameriplex/overview",
            "https://www.wyndhamhotels.com/wingate/plainfield-indiana/wingate-by-wyndham-indianapolis-airport-plainfield/overview",
        ]),
        ("open_review_set_rebuilt", OrderedDict([
            ("IDENTITY_SUCCESSOR_REVIEW", ["la quinta inn"]),
            ("ADDRESS_SUPERSESSION_REVIEW", list(QUEUE_RESOLUTIONS)),
            ("ADDRESS_AND_GEOGRAPHY_REVIEW", ["woodspring suites indianapolis airport south -- RULED_AND_APPLIED by 007 (IDR-005-002); contract change pending promotion; not reopened"]),
            ("CLOSED_OR_CONVERTED_REVIEW", ["americinn by wyndham fishers indianapolis", "ramada indianapolis airport", "wyndham indianapolis west"]),
            ("HELD_CANDIDATE", ["comfort suites indianapolis airport (dc_38bda8c5e06cb16b)", "wingate by wyndham indianapolis airport plainfield (dc_471a3f27e0f70810)",
                                "15 further build-time collision holds recorded in identity_key_collisions, untouched by this order"]),
            ("OTHER", []),
        ])),
        ("classifications", OrderedDict([
            ("IDR-007-001", "IDENTITY_UNRESOLVED (recommended A. SAME_IDENTITY_REBRAND_SUCCESSOR; founder packet)"),
            ("comfort suites indianapolis airport", "ALREADY_REGISTERED_ALIAS (held OSM candidate == IN293); ADDRESS_SUPERSESSION applied"),
            ("address_queue", QUEUE_RESOLUTIONS),
            ("closed_or_converted", OrderedDict([
                ("americinn by wyndham fishers indianapolis", "PROPERTY_CONVERTED (Places CLOSED_PERMANENTLY + brand inventory absent + Choice successor at the same street) -- retire queued IDR-012-004"),
                ("ramada indianapolis airport", "PROPERTY_CLOSED_OR_CONVERTED (brand inventory absent + soft-404; successor unknown) -- retire queued IDR-012-005"),
                ("wyndham indianapolis west", "STILL_ACTIVE (renamed Wyndham Indianapolis Airport; exact telephone match) -- routed; name queued IDR-012-006"),
            ])),
        ])),
        ("applied_shadow_actions", applied),
        ("founder_packet", OUT_PACKET.name), ("cohort", OUT_COHORT.name),
        ("cohort_segments", cohort["segments"]),
        ("untouched", ["identity_census/indianapolis-in.json (257)", "hotel_policy_facts_indianapolis-in.json (56)",
                       "deploy/netlify/release_contracts/indianapolis-in.json", "indianapolis_in_final_partition_004.json",
                       "deploy/netlify/global_deployment_manifest.json", "both cross-run ledgers", "launch participation"]),
    ])
    _new(OUT_RECORD, record)
    print("applied:", json.dumps(applied, ensure_ascii=False)[:600])
    print("cohort:", cohort["count"], dict(cohort["segments"]))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
