"""PTF-SAVANNAH-GA-PARALLEL-SOURCE-READY-001 -- the final partition.

Every census Savannah identity, in EXACTLY ONE state, with exactly one next
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

Output: launch_packages/pettripfinder/markets/staging/savannah-ga/launch_package/savannah_ga_final_partition_007.json
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

WORK_ORDER = "PTF-SAVANNAH-GA-PARALLEL-SOURCE-READY-001"
MARKET_ID = "savannah-ga"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
OUT = os.path.join(PKG, "markets", "staging", "savannah-ga", "launch_package",
                   "savannah_ga_final_partition_007.json")

#: A family this order MEASURED as refusing on this run, with what it returned. None in Savannah: Choice
#: (after a slow challenge page), Best Western, Red Roof, Motel 6, Extended Stay America and Hyatt all served
#: the attended session; the plain-client sitemap refusals are recorded in the brand-inventory report.
REFUSALS = {}
#: Independent properties whose OWN site refused this client on this run.
SITE_REFUSALS = {
    "catherine ward house inn": "a plain-client 403 on catherinewardhouseinn.com",
    "hamilton-turner inn": "a plain-client 403 on hamilton-turnerinn.com",
    "the desoto savannah": "a plain-client 403 on thedesotosavannah.com (both the www and bare hosts)",
    "the inn on west liberty": "a plain-client 403 on innonwestliberty.com",
}
#: Buildings no first-party route was found for (the bureau links a social page, a brand home page or a dead URL).
ROUTE_NOT_FOUND = {
    "presidents' quarters inn": "the bureau's listed website presidentsquarters.com answered 404 on this run",
    "recess hotel & club": "the bureau links only the hotel's Instagram account; no first-party site was read",
    "sonesta essentials hotel savannah": "the bureau links only sonesta.com's home page, and Sonesta's sitemap walk named no "
                                         "Savannah property route on this run",
    "america's best value inn": "the bureau's listed website (americasbestvaluesavannah.com) is a third-party promotional "
                                "page written about the motel, not the operator's own site",
}
#: Buildings whose own page SERVED but states no operative, bindable policy, by census name.
POLICY_SILENT = {
    "17 hundred 90 inn": "the inn's own policies page says 'We do NOT offer pet friendly hotel rooms.' -- a refusal the shared "
                         "reader does not read (QUOTE_NOT_OPERATIVE); held, never reworded",
    "eliza thompson house": "the inn's own amenities page says 'PET POLICY: While we do not allow pets, ...' and its FAQ says only "
                            "'Only service animals as specified by the ADA are allowed' -- neither read by the shared reader; held",
    "forsyth park inn": "the inn's own FAQ says 'We are not pet or Emotional Support Animal friendly.' (QUOTE_NOT_OPERATIVE to the "
                        "shared reader); held, never reworded",
    "gastonian": "the inn's own amenities page says 'PET POLICY: We do not allow pets of any kind.' (QUOTE_NOT_OPERATIVE to the "
                 "shared reader); held, never reworded",
    "kehoe house": "the inn's own amenities page says 'While we do not allow pets, ...' (QUOTE_NOT_OPERATIVE to the shared "
                   "reader); held, never reworded",
    "marshall house": "the hotel's own FAQ says 'We cannot accomodate pets at this time' (QUOTE_NOT_OPERATIVE to the shared "
                      "reader), and that FAQ document states the street but not its postal code; held",
    "olde harbour inn": "the inn's own home page says 'Pets are always welcome.' (QUOTE_NOT_OPERATIVE to the shared reader) and "
                        "its pet page's sentences are an award line (AMENITY_CHIP_ONLY) and 'a $75 pet-amenity fee' (FEE_ONLY); "
                        "held, never reworded",
    "planters inn on reynolds square": "the inn's own FAQ says 'No, pets are strictly prohibited on our property.' "
                                       "(QUOTE_NOT_OPERATIVE to the shared reader); held, never reworded",
    "azalea inn and villas": "the inn's own FAQ says 'Sorry, none of our rooms are pet or ESA friendly' (QUOTE_NOT_OPERATIVE "
                             "to the shared reader); held, never reworded",
    "river street inn": "the inn's own home page served with no pet wording and links no policy page",
    "thunderbird inn": "the motel's own home page served with no pet wording and links no policy page",
    "breezeway studio manor": "its own home page served with no pet wording; whether it is a hotel or a set of rental studios "
                              "is also unconfirmed",
    "extended stay america - savannah - midtown": "the brand's own page carries a 'Pet-friendly room' amenity chip and a terms "
                                                  "fee schedule only (AMENITY_CHIP_ONLY / FEE_ONLY); no acceptance is stated",
    "extended stay america - savannah - pooler": "the brand's own page carries a 'Pet-friendly' amenity chip and a terms fee "
                                                 "schedule only (AMENITY_CHIP_ONLY / FEE_ONLY); no acceptance is stated",
    "motel 6 savannah, ga - midtown": "the brand's own page carries the chain's 'Pets Allowed' / 'Pets stay free' labels only "
                                      "(AMENITY_CHIP_ONLY); no property statement",
    "motel 6 pooler, ga - savannah airport": "the brand's own page calls it 'pet-friendly' in marketing copy only "
                                             "(AMENITY_CHIP_ONLY)",
    "studio 6 extended stay - savannah, ga": "the brand's own page carries a 'Pets Allowed' label only (AMENITY_CHIP_ONLY)",
    "woodspring suites savannah garden city": "the brand's own Pet Policy block ('Limit 2 dogs under 80 lbs. per room. No cats. "
                                              "Non-refundable deposit of $75 UDS and then $10 per day per pet.') is read FEE_ONLY "
                                              "by the shared reader; held, never reworded",
    "woodspring suites savannah pooler": "the brand's own Pet Policy block opens 'Service Animals are welcome at no additional "
                                         "charge ...' and is read SERVICE_ANIMAL_ONLY by the shared reader; held, never reworded",
}
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
    clean = _load(os.path.join(REPORTS, "savannah_ga_clean_authority_001.json"))
    routing = _load(os.path.join(REPORTS, "savannah_ga_routing_001.json"), {})

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
            row["next_action_source"] = ("PTF-SAVANNAH-GA-PARALLEL-SOURCE-READY-001 "
                                         "acquisition passes: owned evidence, brand city pages, "
                                         "brand sitemaps, OSM extract, Visit Savannah and Visit Pooler, the independents' own "
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
         "Every census Savannah identity in exactly one disposition state. A terminal state "
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
