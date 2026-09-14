"""PTF-HAMPTON-ROADS-VA-PARALLEL-SOURCE-READY-001 -- the final partition.

Every census Hampton Roads identity, in EXACTLY ONE state, with exactly one next
action for every state that is not terminal. This is the disposition authority
the sealed package reconciles the census against: a census identity with no
partition row, or two, is a refusal to seal.

THE STATES THIS MARKET USES, AND WHY
------------------------------------
  PUBLISHED_PET_FRIENDLY      an operative acceptance on the property's own
                              page, bound to its own street identity, hashed.
  VERIFIED_NO_PETS            an operative refusal, same standard.
  ACCESS_BLOCKED              the surface refused to serve us. Choice (a
                              sitemap timeout, not a permitted navigation), G6
                              (Motel 6: timeout, not navigable), Best Western
                              (property route redirected to search) and Radisson
                              (an empty shell) refused this client on this run.
                              This records the FETCH OUTCOME only: a refusal
                              proves nothing about the property.
  AWAITING_POLICY_OBSERVATION the route is sound, the page served, and no pet
                              policy has ever been observed on it. UNKNOWN, and
                              never a refusal. A service-animal-only statement
                              and a property whose own pages CONFLICT are here
                              too: neither is a refusal and neither publishes.
  AWAITING_OFFICIAL_URL       no first-party source in this order stated a route
                              for this identity at all.
  AWAITING_IDENTITY_RESOLUTION the identity itself is provisional: a dual-brand
                              address this order could not prove distinct, or a
                              rebrand whose current flag is not settled.

Nothing here publishes and nothing here is a founder decision.

Output: launch_packages/pettripfinder/markets/staging/hampton-roads-va/launch_package/hampton_roads_va_final_partition_007.json
(SHADOW UNTIL REGISTERED: the partition is staged inside the market zone, never at the package root.)
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from collections import Counter, OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

from scripts.pettripfinder.contracts import partition as PARTITION  # noqa: E402

WORK_ORDER = "PTF-HAMPTON-ROADS-VA-PARALLEL-SOURCE-READY-001"
MARKET_ID = "hampton-roads-va"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
OUT = os.path.join(PKG, "markets", "staging", "hampton-roads-va", "launch_package",
                   "hampton_roads_va_final_partition_007.json")

#: A family this order MEASURED as refusing on this run, with what it returned. None among the families that name a
#: census identity: Marriott, Hilton, IHG, Hyatt, Choice, Best Western, Red Roof and Extended Stay America served the
#: attended session; Motel 6 refused the attended browser ("Permission denied for JavaScript execution on this
#: domain") but no Motel 6 row reached the census (the map rows are name-only); the plain-client sitemap refusals are
#: recorded in the brand-inventory report.
REFUSALS = {
    "MOTEL6": ("a plain-client timeout on every motel6.com / studio6.com property route (static lane); no attended "
               "read was made of the family on this run"),
    "CHOICE": ("a 403 shell (557 bytes) on the property page in the attended browser after 30 property pages had served, "
               "and again after one more page on a second pass (va904); per the Atlanta lesson the pass stopped rather than "
               "retry"),
}
#: Independent properties whose OWN site refused this client on this run.
SITE_REFUSALS = {
    "sea view hotel": ("a plain-client 403 on seaviewhotelvb.com, and the attended browser was not permitted to navigate "
                       "to the domain"),
    "ocean cove motel": ("a plain-client connection timeout on oceancovemotel.com, and the attended browser was not "
                         "permitted to navigate to the domain"),
    "the belvedere beach resort": ("a TLS certificate failure on belvederebeachresort.com for the plain client, and a "
                                   "browser privacy (certificate) interstitial the attended pass did not click through"),
    "american inn": "a TLS certificate failure on americaninnchesapeake.com for the plain client",
    "bowers hill inn": "a TLS certificate failure on bowershillinn.com for the plain client",
    "stayapt suites": "a plain-client 403 on stayapt.com",
}
#: Buildings no first-party route was found for.
ROUTE_NOT_FOUND = {
    "alamar resort motel": "the only website any lane names (alamarresortinn.biz) now serves a parked-domain page (ww17.)",
    "oceans 2700": "the only website any lane names (oceans2700.com) redirects to a domain-sale page (hugedomains.com)",
    "belmont inn & suites": "the only website any lane names is a bureau booking-engine link, not the property's own site",
    "atlantic inn": ("the only websites any lane names are a third-party booking engine (stayflexi.com) and a Wyndham "
                     "Travelodge route that the brand's own sitemap walk found RETIRED"),
    "hazel inn & suites": "the only website any lane names is a third-party booking page (gohotelo.com)",
    "studios & suites 4 less chesapeake": ("the only website any lane names is a generic Choice Hotels city page for another "
                                           "property, not this building's own route"),
}
_NOZIP = ("ADDRESS_NOT_ON_DOCUMENT -- the statement sits on a policy / FAQ document that states neither the property's "
          "house number nor its postal code, so the read cannot bind to the building by the page's own street identity; ")
_SILENT = "POLICY_NOT_FOUND -- "
_NOTOP = "QUOTE_NOT_OPERATIVE -- "
_CHIP = "AMENITY_CHIP_ONLY -- "
_CONFLICT = "FIRST_PARTY_CONFLICT -- "
#: Buildings whose own page SERVED but states no operative, bindable policy, by census name.
POLICY_SILENT = {
    "beach carousel motel": _NOZIP + "its own rates-info page says '• NO PETS' (beachcarousel.com/rates-info/, sha256 d01fee68...)",
    "cerca del mar motel": _NOZIP + "its own policies page says 'No pets' (cercadelmar.net/policies, sha256 bbdb5401...)",
    "the capes hotel": _NOZIP + "its own amenities-policies page says '• Sorry, No Pets' (capeshotel.com, sha256 4fe1ef5a...)",
    "intown suites chesapeake/greenbrier extended stay": (
        _NOZIP + "the brand's own FAQ says 'We do not accept pets; however service animals are always welcome' "
        "(intownsuites.com/faq/, sha256 5b71d54b...), a brand-wide page that names no property"),
    "brentwood inn & suites": (
        _CONFLICT + "its own home page says 'No pets allowed' (sha256 c0032ed1...) and its own FAQ page says 'Is Brentwood Inn "
        "& Suites Suffolk VA Pet Friendly? Yes! Pets are allowed, $20.00 PER NIGHT PER PET charged' (sha256 566957dc...); two "
        "first-party statements that disagree publish neither; held, never reworded"),
    "the sitio": _NOTOP + ("its own FAQ says 'We love pets; however, we are not a pet friendly hotel.' -- a refusal to a person "
                           "that the shared reader does not read as operative; held, never reworded"),
    "magnuson hotel virginia beach": _NOTOP + ("the brand's own property page carries only 'No Pet' / 'Pet Allowed' search-filter "
                                               "labels and states no address on the document"),
    "the inn at old beach": _CHIP + ("its only site is a vacation-rental manager's listing (transcendentstays.com) with a "
                                     "'Pets allowed' amenity chip"),
    "economy inn and suites": _CHIP + "its own page says only 'This is family-friendly, pet-friendly'",
    "yourspace hotels chesapeake": _CHIP + "its own policies page is titled 'Chesapeake Virginia Pet Friendly Hotel' and states no policy",
    "woodspring suites virginia beach": ("FEE_ONLY -- the brand's own page answers 'Are pets allowed at WoodSpring Suites Virginia "
                                         "Beach?' with 'Limit 2 dogs, under 75lbs. per room. No cats. Non-refundable pet cleaning fee "
                                         "of 100USD per pet and daily charge of 25USD for first 6 nights and 10USD per pet per night "
                                         "charge for the duration of the stay.' -- limits and fees but no acceptance the shared reader "
                                         "reads; held, never reworded"),
    "woodspring suites chesapeake-norfolk greenbrier": ("FEE_ONLY -- the brand's own page states 'Limit 2 dogs, under 75lbs' and the "
                                                        "same cleaning-fee schedule; no acceptance the shared reader reads"),
    "woodspring suites chesapeake-norfolk south": ("FEE_ONLY -- the brand's own page states 'Limit 2 dogs, under 75lbs' and the "
                                                   "same cleaning-fee schedule; no acceptance the shared reader reads"),
    "blue marlin motel": _SILENT + "its own site (attended browser, 4 pages) served no pet or animal wording on this run",
    "seashire inn and suites": _SILENT + "its own site (attended browser, 3 pages) served no pet or animal wording on this run",
    "cutty sark motel and historic cottages": _SILENT + "its own site (cuttysarkvb.com) served no pet or policy wording on this run",
    "macthrift motor inn": _SILENT + "its own site (macthriftvb.com) served no pet or policy wording on this run",
    "schooner inn": _SILENT + "its own site (schoonerinnvb.com) served no pet or policy wording on this run",
    "sun and sand resort": _SILENT + "its own site (sunandsandresortvb.com, 2 pages) served no pet or policy wording on this run",
    "the breakers resort inn": _SILENT + "its own site (breakersresort.com, 3 pages) served no pet or policy wording on this run",
    "the historic boxwood inn": _SILENT + "its own site (historicboxwoodinn.com) served no pet or policy wording on this run",
    "the lodge at kiln creek": _SILENT + "its own site (thelodgeatkilncreek.com) served no pet or policy wording on this run",
    "country villa b&b and wedding venue": _SILENT + "its own site (countryvillainn.com) served no pet or policy wording on this run",
}
_ESA_CHIP = (_CHIP + "the brand's own page carries a 'Pet-friendly room' amenity chip and a terms-of-use fee schedule only "
             "(AMENITY_CHIP_ONLY / FEE_ONLY); no acceptance is stated")
for _esa in ("extended stay america", "extended stay america - chesapeake - churchland blvd.",
             "extended stay america - chesapeake - crossways blvd.", "extended stay america - greenbrier circle",
             "extended stay america - newport news - oyster point", "extended stay america - newport news - yorktown",
             "extended stay america - norfolk - virginia beach", "extended stay america - virginia beach - independence blvd."):
    POLICY_SILENT[_esa] = _ESA_CHIP
#: Held reads, by identity key, with the class the clean-authority helper gave.
HELD_CLASSES = ("SERVICE_ANIMAL_ONLY", "FIRST_PARTY_CONFLICT", "QUOTE_NOT_OPERATIVE", "POLICY_NOT_FOUND", "FEE_ONLY",
                "CO_LOCATION_RULING_REQUIRED", "ADDRESS_KEY_DIRECTIONAL_COLLISION", "AMENITY_CHIP_ONLY")
#: Chain words in a census name that identify a refused family when the census
#: row carries no brand (a map-only row).
NAME_FAMILY = (
    ("BEST_WESTERN", ("best western",)),
    ("ESA", ("extended stay america", "extended stay")),
    ("FOUR_SEASONS", ("four seasons",)),
    ("RED_ROOF", ("red roof",)),
    ("MOTEL6", ("motel 6", "studio 6")),
    ("HYATT", ("hyatt",)),
    ("CHOICE", ("comfort inn", "comfort suites", "quality inn", "sleep inn", "clarion",
                "econo lodge", "rodeway", "mainstay", "suburban", "cambria", "ascend hotel")),
    ("RADISSON", ("country inn",)),
)
WYNDHAM_BRANDS = ("WYNDHAM", "BAYMONT", "DAYS", "HOJO", "LAQUINTA", "MICROTEL",
                  "RAMADA", "SUPER", "WINGATE", "HAWTHORN", "TRAVELODGE", "WATERWALK")


def _load(p, default=None):
    if not os.path.exists(p):
        return default
    with open(p, encoding="utf-8-sig") as fh:
        return json.load(fh)


def _brand_of(row):
    b = (row.get("brand") or "").upper()
    if b:
        return b
    name = (row.get("canonical_name") or "").upper()
    for fam, words in NAME_FAMILY:
        if any(w.upper() in name for w in words):
            return fam
    for w in WYNDHAM_BRANDS:
        if w in name:
            return "WYNDHAM"
    for w in REFUSALS:
        if w.replace("_", " ") in name or w in name:
            return w
    return ""


def build():
    census = _load(os.path.join(PKG, "identity_census_proposed", "%s.json" % MARKET_ID))
    clean = _load(os.path.join(REPORTS, "hampton_roads_va_clean_authority_001.json"))
    routing = _load(os.path.join(REPORTS, "hampton_roads_va_routing_001.json"), {})

    pf = {r["identity_key"] for r in clean["clean_pet_friendly"]}
    census_by_street = {}
    from scripts.pettripfinder.hotel_exclusions import address_key
    for h in census["hotels"]:
        census_by_street.setdefault(address_key(h.get("street") or "", (h.get("postal_code") or "")[:5]),
                                    h["identity_key"])
    held = {}
    for r in clean["rejected"]:
        if r["classification"] not in HELD_CLASSES:
            continue
        sig = r.get("identity_signals") or {}
        # A held co-location / directional-collision row names its own identity key; two buildings the shared
        # street key conflates are never joined by the street alone.
        k = r.get("identity_key") or census_by_street.get(address_key(sig.get("address_on_page") or "",
                                                                      (sig.get("postal_code") or "")[:5]))
        if k:
            held[k] = r
    np_ = {r["identity_key"] for r in clean["clean_verified_no_pets"]}
    routed = {r["identity_key"]: r for r in routing.get("routes", []) if r.get("url")}

    items = []
    for h in census["hotels"]:
        key = h["identity_key"]
        row = OrderedDict((("identity_key", key), ("canonical_name", h["canonical_name"])))
        if key in pf:
            row["final_state"] = "PUBLISHED_PET_FRIENDLY"
            row["resolved"] = True
        elif key in np_:
            row["final_state"] = "VERIFIED_NO_PETS"
            row["resolved"] = True
        else:
            brand = _brand_of(h)
            url = (routed.get(key) or {}).get("url") or h.get("official_url") or ""
            if h.get("identity_state") != "IDENTITY_CONFIRMED":
                state = "AWAITING_IDENTITY_RESOLUTION"
                action = ("resolve the identity before any policy work binds to it: this row is "
                          "provisional in the census and a policy read cannot be attached to a "
                          "building the identity graph has not settled")
            elif key in held:
                state = "AWAITING_POLICY_OBSERVATION"
                action = (("the property's own page was read and its statement was held as %s: %s. "
                           "Observe an operative statement of acceptance or refusal before this "
                           "row publishes")
                          % (held[key]["classification"], (held[key].get("why") or "")[:220]))
            elif (h.get("canonical_name") or "").lower() in POLICY_SILENT:
                state = ("ACCESS_BLOCKED" if "refused" in POLICY_SILENT[(h.get("canonical_name") or "").lower()]
                         else "AWAITING_POLICY_OBSERVATION")
                action = ("observe an operative first-party statement: %s"
                          % POLICY_SILENT[(h.get("canonical_name") or "").lower()])
            elif (h.get("canonical_name") or "").lower() in ROUTE_NOT_FOUND:
                state = "AWAITING_OFFICIAL_URL"
                action = ("find a first-party route: %s" % ROUTE_NOT_FOUND[(h.get("canonical_name") or "").lower()])
            elif (h.get("canonical_name") or "").lower() in SITE_REFUSALS:
                state = "ACCESS_BLOCKED"
                action = ("re-probe the property's own site: it gave %s on this run"
                          % SITE_REFUSALS[(h.get("canonical_name") or "").lower()])
            elif brand in REFUSALS:
                state = "ACCESS_BLOCKED"
                action = ("re-probe the family's surface and, if it refuses again, route this "
                          "identity to the paid lane under a founder budget: this family gave %s "
                          "on this run" % REFUSALS[brand])
            elif not url:
                state = "AWAITING_OFFICIAL_URL"
                action = ("find a first-party route: no owned harvest, brand roster, brand "
                          "sitemap, destination organisation or map source in this order stated "
                          "an official URL for this identity")
            elif brand == "WYNDHAM":
                state = "AWAITING_OFFICIAL_URL"
                action = ("find the property's current first-party route: its Wyndham sitemap "
                          "route redirected to the brand's city search page in the attended pass "
                          "(a retired or rebranded route), so no property page states a policy")
            elif brand in REFUSALS:
                state = "ACCESS_BLOCKED"
                action = ("re-probe the surface and, if it refuses again, route it to the paid "
                          "lane under a founder budget: this family gave %s on this run"
                          % REFUSALS[brand])
            else:
                state = "AWAITING_POLICY_OBSERVATION"
                action = ("read this property's own page: it is routed and no pet policy has been "
                          "observed on it by this order")
            row["final_state"] = state
            row["resolved"] = False
            row["next_action"] = action
            row["next_action_source"] = ("PTF-HAMPTON-ROADS-VA-PARALLEL-SOURCE-READY-001 "
                                         "acquisition passes: owned evidence, brand city pages, "
                                         "brand sitemaps, OSM extract, the city bureaus, the independents' own "
                                         "sites and the attended browser pass")
            row["determined_by"] = WORK_ORDER
        row["corridor"] = h.get("corridor")
        row["brand"] = h.get("brand") or ""
        items.append(row)

    counts = Counter(i["final_state"] for i in items)
    doc = OrderedDict((
        ("schema", PARTITION.SCHEMA),
        ("work_order", WORK_ORDER),
        ("market_id", MARKET_ID),
        ("as_of", "2026-09-14"),
        ("what_this_is",
         "Every census Hampton Roads identity in exactly one disposition state. A terminal state "
         "carries no next action and is marked resolved; every other state carries exactly one "
         "next action, the pass that determined it and the work order that set it. An identity "
         "missing here, or present twice, makes the sealed package refuse to serialize."),
        ("count", len(items)),
        ("counts_by_state", OrderedDict(sorted(counts.items()))),
        ("resolved", sum(1 for i in items if i["resolved"])),
        ("unresolved", sum(1 for i in items if not i["resolved"])),
        ("items", items),
    ))
    return doc


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default=OUT)
    args = ap.parse_args(argv)
    doc = build()
    issues = PARTITION.validate(doc)
    print("identities  :", doc["count"])
    print("by state    :", dict(doc["counts_by_state"]))
    print("resolved    :", doc["resolved"], "| unresolved:", doc["unresolved"])
    print("contract    :", len(issues), "issues")
    for i in issues[:8]:
        print("   !", str(i)[:150])
    if issues:
        print("NOT WRITTEN")
        return 1
    with open(args.out, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    print("written     :", os.path.relpath(args.out, _DASH))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
