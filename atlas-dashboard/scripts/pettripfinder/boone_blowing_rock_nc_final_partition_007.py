"""PTF-BOONE-BLOWING-ROCK-NC-PARALLEL-SOURCE-READY-001 -- the final partition.

Every census Boone - Blowing Rock identity, in EXACTLY ONE state, with exactly one next
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

Output: launch_packages/pettripfinder/markets/staging/boone-blowing-rock-nc/launch_package/boone_blowing_rock_nc_final_partition_007.json
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

WORK_ORDER = "PTF-BOONE-BLOWING-ROCK-NC-PARALLEL-SOURCE-READY-001"
MARKET_ID = "boone-blowing-rock-nc"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
OUT = os.path.join(PKG, "markets", "staging", "boone-blowing-rock-nc", "launch_package",
                   "boone_blowing_rock_nc_final_partition_007.json")

#: A family this order MEASURED as refusing a plain client on this run, with the
#: status it returned. Used only to explain an ACCESS_BLOCKED row.
REFUSALS = {
    "CHOICE": "a plain-client sitemap timeout, and in the attended session choicehotels.com's Boone property pages "
              "(nc790 Quality Inn, nc052 Comfort Suites) returned an empty behavioural bot-challenge shell (the brand's "
              "bot defence; never bypassed)",
    "RADISSON": "a plain-client 403 on the brand sitemap and a connection failure on the bureau's legacy countryinns.com "
                "route; no Radisson property page for Boone was reached on this run",
}
#: Independent properties whose OWN site refused this client on this run.
SITE_REFUSALS = {
    "ridgeway inn": "a plain-client 403 on ridgewayinn-nc.com",
    "yonahlossee resort accommodations": "no answer from yonahlossee.com (connection failure) and no other first-party "
                                         "route found",
}
#: Buildings whose own page SERVED but states no operative, bindable policy, by census name.
POLICY_SILENT = {
    "alpine village inn": "the inn's own home page says only 'Please, note that we require a $10/night pet fee if you "
                          "bring a pet' -- a fee sentence the shared reader classifies FEE_ONLY; a fee alone never "
                          "establishes acceptance",
    "cliff dwellers inn": "the inn's own rates-and-policies page states 'a nominal $25 charge per pet per night' -- read "
                          "FEE_ONLY by the shared reader, and that page states no street and postal code",
    "rhode's motor lodge": "the lodge's own policies page ('welcomes you and your dog! For $75/stay (flat fee) you may "
                           "bring up to TWO dogs weighing 50 pounds or less') is read FEE_ONLY by the shared reader; held, "
                           "never reworded",
    "the inn at crestwood": "the inn's own pet page ('Pet charges are $50.00 per pet, per night and only allowed in "
                            "designated rooms') is read FEE_ONLY by the shared reader; held, never reworded",
    "the 1850 hotel": "the hotel's own FAQ says it 'is not pet-friendly', a refusal the shared reader does not read "
                      "(QUOTE_NOT_OPERATIVE); held, never reworded",
    "the windmoor hotel": "the hotel's own FAQ says it 'is not pet-friendly' (QUOTE_NOT_OPERATIVE to the shared reader), "
                          "and its JSON-LD carries the sister 1850 Hotel's Boone address; held",
    "the blowing rock manor": "the hotel's own FAQ says The Manor 'is not pet-friendly' (QUOTE_NOT_OPERATIVE to the shared "
                              "reader); held",
    "hemlock inn and suites": "the inn's own amenities page says 'All of our rooms are non-smoking and pet-free.' "
                              "(QUOTE_NOT_OPERATIVE to the shared reader); held",
    "village inn of blowing rock": "the operator's own pet page ('The Village Inns of Blowing Rock allows dogs at "
                                   "Hillwinds Inn, Boxwood Lodge and Village Inn ...') is a sentence the shared reader "
                                   "does not read (QUOTE_NOT_OPERATIVE); held, never reworded",
    "hillwinds inn": "the operator's Hillwinds page says only 'The Hillwinds Inn is pet friendly' (AMENITY_CHIP_ONLY to "
                     "the shared reader) and states the Village Inn's street, not 315 Sunset Drive",
    "boxwood lodge": "boxwoodlodge.com did not answer; the operator's pet sentence naming the lodge is QUOTE_NOT_OPERATIVE "
                     "to the shared reader",
    "the horton hotel": "the hotel's own FAQ says 'Yes, we have five pet-friendly rooms' but that document states no "
                        "street and postal code (the address is only on its cookie / privacy pages), so the read cannot "
                        "bind by the policy page's own street identity",
    "westglow luxury resort and spa": "the resort's own policies page says 'Lodges 2 and 3 welcome pets' (the Manor House, "
                                      "Daingerfield House and Lodge 1 are no-pet) but states no street and postal code",
    "highland hills motel and cabins": "the motel's own rate-policies page says small dogs are permitted in designated "
                                       "units, but states '2748 Hwy 105 South, Boone, NC' with no postal code",
    "lazy bear lodge": "the B&B's own policies page says 'No Pets' but the page states no street and postal code",
    "lovill house inn": "the inn's own lodging-policies page says only that 'Certain circumstances allow for pets in the "
                        "cabin or our climate controlled pet house' -- conditional, not an operative policy for the inn's "
                        "rooms",
    "blue ridge tourist court": "the court's own home page served with no pet wording",
    "gideon ridge inn": "the inn's own home page served with no pet wording",
    "hellbender bed & beverage": "the inn's own home page served with no pet wording",
    "the embers hotel": "the hotel's own home page served with no pet wording and links to no policy page",
    "the inn at ragged gardens": "the inn's own home and amenities pages served with no pet wording",
}
#: Held reads, by identity key, with the class the clean-authority helper gave.
HELD_CLASSES = ("SERVICE_ANIMAL_ONLY", "FIRST_PARTY_CONFLICT", "QUOTE_NOT_OPERATIVE", "POLICY_NOT_FOUND", "FEE_ONLY", "CO_LOCATION_RULING_REQUIRED")
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
    clean = _load(os.path.join(REPORTS, "boone_blowing_rock_nc_clean_authority_001.json"))
    routing = _load(os.path.join(REPORTS, "boone_blowing_rock_nc_routing_001.json"), {})

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
        k = census_by_street.get(address_key(sig.get("address_on_page") or "",
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
            row["next_action_source"] = ("PTF-BOONE-BLOWING-ROCK-NC-PARALLEL-SOURCE-READY-001 "
                                         "acquisition passes: owned evidence, brand city pages, "
                                         "brand sitemaps, OSM extract, Explore Boone and High Country Host, the independents' own "
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
        ("as_of", "2026-09-13"),
        ("what_this_is",
         "Every census Boone - Blowing Rock identity in exactly one disposition state. A terminal state "
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
