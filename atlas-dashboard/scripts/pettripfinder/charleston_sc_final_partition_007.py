"""PTF-CHARLESTON-SC-PARALLEL-SOURCE-READY-001 -- the final partition.

Every census Charleston identity, in EXACTLY ONE state, with exactly one next
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

Output: launch_packages/pettripfinder/markets/staging/charleston-sc/launch_package/charleston_sc_final_partition_007.json
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

WORK_ORDER = "PTF-CHARLESTON-SC-PARALLEL-SOURCE-READY-001"
MARKET_ID = "charleston-sc"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
OUT = os.path.join(PKG, "markets", "staging", "charleston-sc", "launch_package",
                   "charleston_sc_final_partition_007.json")

#: A family this order MEASURED as refusing on this run, with what it returned. None among the families that name a
#: census identity: Marriott, Hilton, IHG, Hyatt, Choice, Best Western, Red Roof and Extended Stay America served the
#: attended session; Motel 6 refused the attended browser ("Permission denied for JavaScript execution on this
#: domain") but no Motel 6 row reached the census (the map rows are name-only); the plain-client sitemap refusals are
#: recorded in the brand-inventory report.
REFUSALS = {}
#: Independent properties whose OWN site refused this client on this run.
SITE_REFUSALS = {
    "starlight motor inn": "a plain-client 403 on starlightchs.com",
    "the cottages on charleston harbor": "a plain-client 403 on thecottagesoncharlestonharbor.com",
}
#: Buildings no first-party route was found for.
ROUTE_NOT_FOUND = {
    "country victorian": "the map's only website tag is a Tripadvisor review page, not the inn's own site",
    "stay express inn north charleston": "no website on any lane (map row only)",
    "the palmetto house inn": "no website on any lane (map row only)",
}
_NOZIP = ("ADDRESS_NOT_ON_DOCUMENT -- the statement sits on a FAQ / policy document that states neither the property's "
          "house number nor its postal code, so the read cannot bind to the building by the page's own street identity; ")
_SILENT = "POLICY_NOT_FOUND -- "
_NOTOP = "QUOTE_NOT_OPERATIVE -- "
_CHIP = "AMENITY_CHIP_ONLY -- "
#: Buildings whose own page SERVED but states no operative, bindable policy, by census name.
POLICY_SILENT = {
    "20 south battery": _NOTOP + "the inn's own FAQ says 'While we love our furry friends, we do not accept pets' -- a "
                        "refusal the shared reader does not read; held, never reworded",
    "360 king boutique suites": _CHIP + "its own home page carries 'PET FRIENDLY' and a 'Happy Pets Package' offer only",
    "86 cannon historic inn": _NOZIP + "its policies page says 'No pets allowed (including emotional support animals)'",
    "andrew pinckney inn": _NOZIP + "its FAQ says 'We do not allow pets at this time'",
    "bijou boutique inn": _SILENT + "its own site served no pet or policy wording on this run (home page and /faq)",
    "charleston harbor resort & marina": _NOTOP + "the resort's own policies page says 'The Charleston Harbor Resort & "
                                         "Marina does allow dogs' -- an acceptance the shared reader does not read; held",
    "elliott house inn": _NOZIP + "its FAQ says 'No, we do not accommodate pets'",
    "emeline": _NOZIP + "its FAQ says 'Yes, we’d love to welcome your pet' and its pet page states only a $200 "
               "cleaning fee (FEE_ONLY)",
    "fire tower": _SILENT + "its own site served no pet or policy wording on this run (home page and /faq)",
    "francis marion hotel": _NOZIP + "its dog-friendly page lists 'Only dogs are allowed' / '1 dog per room'",
    "french quarter inn": _SILENT + "its own site (fqicharleston.com, home page and /faq/) served no readable pet wording",
    "fulton lane inn": _NOTOP + "the inn's own FAQ says 'As much as we love pets, we cannot accommodate them' -- held, "
                       "never reworded",
    "harbourview inn": _SILENT + "its own home, privacy and FAQ pages served no pet wording on this run",
    "hotel bennett": _NOTOP + "the hotel's own FAQ says 'We welcome a maximum of two (2) dogs per guestroom, per stay and "
                     "should not exceed 25 pounds each' -- an acceptance the shared reader does not read; held",
    "hotel richemont": _SILENT + "its own home page and /faq/ served no pet wording on this run",
    "indigo inn": _SILENT + "its own home page and /faq/ served no pet wording on this run",
    "luxury bed & breakfast inn on folly beach": _NOZIP + "its FAQ says 'Unfortunately, we do not allow pets at our "
                                                 "property'",
    "market pavilion hotel": _NOZIP + "its policies page says it 'does not permit pets within our ... hotel guest rooms'",
    "meeting street inn": _SILENT + "its own home page and /faq/ served no pet wording on this run",
    "parson inn": _NOZIP + "its terms page says 'No pets allowed'",
    "planters inn": _NOTOP + "the inn's own FAQ says 'We are unfortunately not a pet friendly hotel' -- held, never reworded",
    "seaside inn": _CHIP + "its own home page says 'Seaside Inn is the only pet-friendly hotel in the heart of Isle of "
                   "Palms' (marketing copy, not a policy)",
    "shem creek inn": _NOTOP + "the inn's own FAQ says 'No, we do not allow pets on our property' -- held, never reworded",
    "the ansonborough": _CHIP + "its own home page offers a 'Paws & Relax' pet package only",
    "the ashley": _NOZIP + "its FAQ says 'We are not a pet-friendly hotel'",
    "the charlee on cannon": _NOZIP + "its home page carries a 'Pets allowed' label only",
    "the charleston place": _CHIP + "the hotel's own policies page says 'We welcome pets of all sizes at The Charleston "
                            "Place' -- read by the shared reader as an amenity label; held, never reworded",
    "the cooper": _SILENT + "its own home page and /faq/ served no pet wording on this run",
    "the jasmine house": _NOZIP + "its FAQ says 'No, pets are strictly prohibited on our property'",
    "the loutrel": _NOZIP + "its FAQ says 'No, pets are strictly prohibited on our property'",
    "the nickel hotel": _NOZIP + "its FAQ says 'We are not pet-friendly'",
    "the palmetto hotel charleston": _SILENT + "its own home page and /faq/ served no pet wording on this run",
    "the palms oceanfront hotel": _SILENT + "its own home page and FAQ served no pet wording on this run",
    "the pinch": _NOZIP + "its FAQ says 'we are a pet-free hotel'",
    "the ryder hotel": _NOZIP + "its home page says 'A limited number of pet-friendly rooms may be available; advance "
                       "notice and a nightly fee may apply' (also not an operative acceptance)",
    "the spectator hotel": _NOZIP + "its FAQ says 'The Spectator Hotel does not allow pets'",
    "tides folly beach": _NOZIP + "its home page says 'Tides Folly Beach welcomes dogs in designated pet-friendly "
                         "accommodations' but states its postal code only inside a script block, not in the page text",
    "victoria house inn": _SILENT + "victoriahouseinn.com redirects to the Charming Inns group site, which states no "
                          "policy for this inn",
    "zero george": _NOZIP + "its FAQ says 'we are predominantly a pet-free hotel' while its residences 'do allow dogs for "
                   "stays of more than 10 days' -- two regimes, neither operative",
    "woodspring suites north charleston airport i-526": _NOTOP + "the brand's own Pet Policy block states fees and limits "
                                                        "('A max of 80 pounds total and a max of 2 pets (dogs, no cats).') "
                                                        "and no acceptance the shared reader reads",
}
for _esa in ("airport", "ashley phosphate rd.", "mt. pleasant", "north charleston - i-526", "northwoods blvd."):
    POLICY_SILENT["extended stay america - charleston - " + _esa] = (
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
    census = _load(os.path.join(PKG, "identity_census_proposed", "%s.json" % MARKET_ID))
    clean = _load(os.path.join(REPORTS, "charleston_sc_clean_authority_001.json"))
    routing = _load(os.path.join(REPORTS, "charleston_sc_routing_001.json"), {})

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
            row["next_action_source"] = ("PTF-CHARLESTON-SC-PARALLEL-SOURCE-READY-001 "
                                         "acquisition passes: owned evidence, brand city pages, "
                                         "brand sitemaps, OSM extract, the Charleston Area CVB and Visit Folly, the independents' own "
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
         "Every census Charleston identity in exactly one disposition state. A terminal state "
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
