"""PTF-RICHMOND-VA-PARALLEL-SOURCE-READY-001 -- the final partition.

Every census Richmond identity, in EXACTLY ONE state, with exactly one next
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

Output: launch_packages/pettripfinder/markets/staging/richmond-va/launch_package/richmond_va_final_partition_007.json
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

WORK_ORDER = "PTF-RICHMOND-VA-PARALLEL-SOURCE-READY-001"
MARKET_ID = "richmond-va"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
#: REGISTERED by PTF-RICHMOND-VA-REGISTER-RESEAL-AND-AUTHORIZATION-PREP-002: the package root.
OUT = os.path.join(PKG, "richmond_va_final_partition_007.json")

#: A family this order MEASURED as refusing on this run, with what it returned. None among the families that name a
#: census identity: Marriott, Hilton, IHG, Hyatt, Choice, Best Western, Red Roof and Extended Stay America served the
#: attended session; Motel 6 refused the attended browser ("Permission denied for JavaScript execution on this
#: domain") but no Motel 6 row reached the census (the map rows are name-only); the plain-client sitemap refusals are
#: recorded in the brand-inventory report.
REFUSALS = {
    "MOTEL6": "a plain-client timeout on every motel6.com / studio6.com / staystudio6.com property route (static lane)",
    "CHOICE": ("a 403 shell (557 bytes) on the property page in the attended browser after 22 property pages had served "
               "(Quality Inn Richmond Airport, va033); per the Atlanta lesson the pass stopped rather than retry"),
}
#: Independent properties whose OWN site refused this client on this run.
SITE_REFUSALS = {
    "v.i.p. inn": "a plain-client 403 on vipmotorinn.com",
    "inn at patrick henry's": "a DNS failure (getaddrinfo) on innatph.com, the site the bureau lists",
}
#: Buildings no first-party route was found for.
ROUTE_NOT_FOUND = {
    "airport inn motel": "the only website any lane names (airport-inn-motel-richmond.magnusonhotels.com) no longer resolves",
    "america's best value inn": "the only website any lane names is the defunct brand home page bestvalueinn.com",
    "americas best value inn richmond": "the only website any lane names is a zenhotels.com booking page, not the property's own",
    "capitol inn by belvilla richmond airport va": "the only website any lane names is an hrs.com booking page",
    "city motel": "the only website any lane names is an hrs.com booking page",
    "royal inn": "the only website any lane names is a booking.com page",
    "dominion inn & suites": ("the bureau's website link is a former Rodeway Inn choicehotels.com route (va489) that Choice's own "
                              "Sandston roster no longer lists"),
    "sandston inn & suites": ("a map-only row at 5209 Williamsburg Road, the building whose own pages today state Red Roof Inn "
                              "(Building A) and HomeTowne Studios (Building B); no route of its own"),
    "knights inn and suites near university of richmond": ("a map-only row at 7201 West Broad Street, the building whose own "
                                                          "pages today state Red Roof Inn (Building A) and HomeTowne Studios "
                                                          "(Building B); no route of its own"),
}
_NOZIP = ("ADDRESS_NOT_ON_DOCUMENT -- the statement sits on a FAQ / policy document that states neither the property's "
          "house number nor its postal code, so the read cannot bind to the building by the page's own street identity; ")
_SILENT = "POLICY_NOT_FOUND -- "
_NOTOP = "QUOTE_NOT_OPERATIVE -- "
_CHIP = "AMENITY_CHIP_ONLY -- "
#: Buildings whose own page SERVED but states no operative, bindable policy, by census name.
POLICY_SILENT = {
    "the jefferson hotel": _NOTOP + ("its own FAQ says 'Pet policies and fees apply; we recommend contacting the hotel in "
                                     "advance to make arrangements' and its amenities list 'Dog Friendly (fees apply)' -- no "
                                     "operative acceptance; held, never reworded"),
    "museum district b&b": _NOTOP + ("its own policies page says 'We do not accept animals, but there are boarding facilities "
                                     "and pet friendly hotels nearby' -- a refusal the shared reader reads as contradicting "
                                     "itself (QUOTE_CONTRADICTS_CLAIM); held, never reworded"),
    "intown suites midlothian": _NOZIP + ("the brand's own property page (attended browser, sha256 34d2b631...) says 'No pets "
                                          "allowed at InTown Suites Richmond VA – Green Springs' and states the street but no "
                                          "postal code"),
    "intown suites perdue springs": _NOZIP + ("the brand's own property page (attended browser, sha256 70103690...) says 'No "
                                              "pets allowed at InTown Suites Richmond VA – Chester' and states the street but "
                                              "no postal code"),
    "woodspring suites richmond west i-64": ("FEE_ONLY -- the brand's own page states 'Limit 2 dogs, under 75lbs. per room. No "
                                             "cats. Non-refundable pet cleaning fee of 100USD per pet ...' -- limits and fees "
                                             "but no acceptance the shared reader reads; held, never reworded"),
    "express airport inn": _CHIP + "its own home page carries a 'Pet Friendly' label only",
    "brentwood inn and suites glen allen": _NOTOP + ("its own FAQ says 'Non Smoking, Pet-friendly rooms can be requested by "
                                                     "contacting the manager' (and its JSON-LD states a Georgia postal code)"),
    "colony house motor lodge": _SILENT + "its own site (colony-lodge.edan.io) served no pet or policy wording on this run",
    "historic mankin mansion bed and breakfast": _SILENT + "its own site served no pet or policy wording on this run",
    "virginia cliffe inn": _SILENT + "its own site (vacliffeinn.com) served no pet or policy wording on this run",
    "knights inn ashland, va": _SILENT + "its own brand page served no pet or policy wording on this run",
    "extended stay america suites north chesterfield - arboretum": (
        _CHIP + "the brand's own page carries a 'Pet-friendly room' amenity chip and a terms-of-use fee schedule, and its "
        "page states no address in its Hotel JSON-LD"),
}
for _esa in ("glen allen - short pump", "innsbrook", "w. broad street - glenside - north", "w. broad street - glenside - south",
             "west end - i-64"):
    POLICY_SILENT["extended stay america - richmond - " + _esa] = (
        _CHIP + "the brand's own page carries a 'Pet-friendly room' amenity chip and a terms-of-use fee schedule only "
        "(AMENITY_CHIP_ONLY / FEE_ONLY); no acceptance is stated")
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
    census = _load(os.path.join(PKG, "identity_census", "%s.json" % MARKET_ID))
    clean = _load(os.path.join(REPORTS, "richmond_va_clean_authority_001.json"))
    routing = _load(os.path.join(REPORTS, "richmond_va_routing_001.json"), {})

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
            row["next_action_source"] = ("PTF-RICHMOND-VA-PARALLEL-SOURCE-READY-001 "
                                         "acquisition passes: owned evidence, brand city pages, "
                                         "brand sitemaps, OSM extract, Visit Richmond VA, the independents' own "
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
         "Every census Richmond identity in exactly one disposition state. A terminal state "
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
