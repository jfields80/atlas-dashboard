"""PTF-COLUMBIA-SC-PARALLEL-SOURCE-READY-001 -- the final partition.

Every census Columbia identity, in EXACTLY ONE state, with exactly one next
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

Output: launch_packages/pettripfinder/markets/staging/columbia-sc/launch_package/columbia_sc_final_partition_007.json
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

WORK_ORDER = "PTF-COLUMBIA-SC-PARALLEL-SOURCE-READY-001"
MARKET_ID = "columbia-sc"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
OUT = os.path.join(PKG, "markets", "staging", "columbia-sc", "launch_package",
                   "columbia_sc_final_partition_007.json")

#: A family this order MEASURED as refusing on this run, with what it returned. None among the families that name a
#: census identity: Marriott, Hilton, IHG, Hyatt, Choice, Best Western, Red Roof and Extended Stay America served the
#: attended session; Motel 6 refused the attended browser ("Permission denied for JavaScript execution on this
#: domain") but no Motel 6 row reached the census (the map rows are name-only); the plain-client sitemap refusals are
#: recorded in the brand-inventory report.
REFUSALS = {
}
#: Independent properties whose OWN site refused this client on this run.
SITE_REFUSALS = {
}
#: Buildings no first-party route was found for.
ROUTE_NOT_FOUND = {
    "knights inn columbia airport/cayce": ("only the map names this building (1987 Airport Boulevard); no brand inventory, "
                                           "bureau listing or map website tag states a first-party route, and Wyndham's own "
                                           "sitemap no longer lists a Knights Inn in the market"),
    "travelers inn": ("only the map names this building (2200 Airport Boulevard); no brand inventory, bureau listing or map "
                      "website tag states a first-party route"),
}
_NOZIP = ("ADDRESS_NOT_ON_DOCUMENT -- the statement sits on a policy / FAQ document that states neither the property's "
          "house number nor its postal code, so the read cannot bind to the building by the page's own street identity; ")
_SILENT = "POLICY_NOT_FOUND -- "
_NOTOP = "QUOTE_NOT_OPERATIVE -- "
_CHIP = "AMENITY_CHIP_ONLY -- "
_CONFLICT = "FIRST_PARTY_CONFLICT -- "
#: Buildings whose own page SERVED but states no operative, bindable policy, by census name.
POLICY_SILENT = {
    "hotel trundle": _NOTOP + ("its own FAQ (hoteltrundle.com/faq, sha256 adbfba4b...) answers 'Can I bring my pet?' with 'While "
                               "we love pets, we kindly ask that you leave your furry friends at home.' -- a refusal to a person "
                               "that the shared reader does not read as operative; held, never reworded"),
    "intown suites extended stay columbia sc - two notch": (
        _NOZIP + "the brand's own property page says 'No pets allowed at InTown Suites Columbia SC – Two Notch' "
        "(intownsuites.com/extended-stay-hotels/south-carolina/columbia/east-9/, sha256 14939514...) and states no postal code"),
    "intown suites columbia west": (
        _NOZIP + "the brand's own property page says 'No pets allowed at InTown Suites Columbia SC – Broad River' "
        "(.../columbia/broad-river/, sha256 22dc0c39...) and states neither the house number nor the postal code"),
    "intown suites columbia northwest": (
        _NOZIP + "the brand's own property page says 'No pets allowed at InTown Suites Columbia SC – Columbiana' beside "
        "'330 Columbiana Drive' (.../columbia/columbiana/, sha256 72030f3e...) and states no postal code"),
    "motel 6 columbia east sc": (
        _CHIP + "Motel 6's own property page (attended browser, motel6.com/property/motel-columbia-sc-south-carolina-us-294017/) "
        "carries 'Pet-Friendly Accommodation', 'Pets welcome throughout your stay' and 'Pets Allowed / Pets Stay Free' labels, "
        "which the shared reader classes as an amenity label, and states '7541 Nates Road, Columbia SC' with no postal code"),
    "staybridge suites columbia": _SILENT + ("IHG's own page for caers (attended browser, sha256 26e958f8...) carries the FAQ "
                                             "question 'Can I bring my pet to Staybridge Suites Columbia?' with no answer text"),
    "studiores by marriott columbia harbison": _SILENT + ("Marriott's own page for caenr (attended browser, sha256 52d3c14a...) "
                                                          "carries no Pet Policy row"),
    "baymont by wyndham columbia northwest": (
        "FEE_ONLY -- the brand's own property service says 'Maximum 2 pets per room permitted for a non-refundable charge 30 "
        "USD/pet/night under 40lbs and 55 USD/pet/night over 40lbs. Pet sanitation fee is 100.00 USD if applicable. ADA defined "
        "service animals are also welcome at this hotel.' -- a count and tiered charges with no acceptance the shared reader "
        "reads; held, never reworded"),
}
_ESA_CHIP = (_CHIP + "the brand's own page carries a 'Pet-friendly room' amenity chip and a terms-of-use fee schedule only "
             "(AMENITY_CHIP_ONLY / FEE_ONLY); no acceptance is stated")
for _esa in ("extended stay america - columbia - ft. jackson", "extended stay america - columbia - greystone",
             "extended stay america - columbia - northwest/harbison",
             "extended stay america - columbia - west - interstate-126"):
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
    clean = _load(os.path.join(REPORTS, "columbia_sc_clean_authority_001.json"))
    routing = _load(os.path.join(REPORTS, "columbia_sc_routing_001.json"), {})

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
            row["next_action_source"] = ("PTF-COLUMBIA-SC-PARALLEL-SOURCE-READY-001 "
                                         "acquisition passes: owned evidence, brand city pages, "
                                         "brand sitemaps, OSM extract, the Columbia CVB roster, the independents' own "
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
        ("as_of", "2026-09-15"),
        ("what_this_is",
         "Every census Columbia identity in exactly one disposition state. A terminal state "
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
