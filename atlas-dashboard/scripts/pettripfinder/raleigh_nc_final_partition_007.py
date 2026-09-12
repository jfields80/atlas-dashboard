"""PTF-RALEIGH-NC-FINAL-FRESH-CITY-PROOF-001 -- the final partition.

Every registered Raleigh identity, in EXACTLY ONE state, with exactly one next
action for every state that is not terminal. This is the disposition authority
the sealed package reconciles the census against: a census identity with no
partition row, or two, is a refusal to seal.

THE STATES THIS MARKET USES, AND WHY
------------------------------------
  PUBLISHED_PET_FRIENDLY      an operative acceptance on the property's own
                              page, bound to its own street identity, hashed.
  VERIFIED_NO_PETS            an operative refusal, same standard.
  AWAITING_ATTENDED_CAPTURE   the policy exists on the property's own surface
                              but behind client-side rendering a static fetch
                              cannot reach. Every Wyndham route in this market
                              is here: the operative text lands in
                              `.pet-policy-desc` only after the page's own
                              scripts run, and a plain client is served the
                              amenity chip instead.
  ACCESS_BLOCKED              the surface refused to serve us. Best Western,
                              Extended Stay America, Red Roof, Motel 6, Hyatt
                              and Sonesta each refused this client on this run.
                              This records the FETCH OUTCOME only: a refusal
                              proves nothing about the property.
  AWAITING_POLICY_OBSERVATION the route is sound, the page served, and no pet
                              policy has ever been observed on it. UNKNOWN, and
                              never a refusal -- WoodSpring's property pages
                              carry an SEO keyword list and a chain-level line
                              about "MOST of our locations", which states
                              nothing about the building.
  AWAITING_OFFICIAL_URL       no first-party source in this order stated a route
                              for this identity at all.
  AWAITING_IDENTITY_RESOLUTION the identity itself is provisional: a dual-brand
                              address this order could not prove distinct, or a
                              rebrand whose current flag is not settled.

Nothing here publishes and nothing here is a founder decision.

Output: launch_packages/pettripfinder/raleigh_nc_final_partition_007.json
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

WORK_ORDER = "PTF-RALEIGH-NC-FINAL-FRESH-CITY-PROOF-001"
MARKET_ID = "raleigh-nc"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
OUT = os.path.join(PKG, "raleigh_nc_final_partition_007.json")

#: A family this order MEASURED as refusing a plain client on this run, with the
#: status it returned. Used only to explain an ACCESS_BLOCKED row.
REFUSALS = {
    "BEST_WESTERN": "HTTP 403", "ESA": "HTTP 403", "RED_ROOF": "HTTP 403",
    "MOTEL6": "read timeout", "HYATT": "HTTP 429", "SONESTA": "HTTP 404",
    "CHOICE": "read timeout", "RADISSON": "sitemap refused to this client",
}
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
    for w in WYNDHAM_BRANDS:
        if w in name:
            return "WYNDHAM"
    for w in REFUSALS:
        if w.replace("_", " ") in name or w in name:
            return w
    return ""


def build():
    census = _load(os.path.join(PKG, "identity_census", "%s.json" % MARKET_ID))
    clean = _load(os.path.join(REPORTS, "raleigh_nc_clean_authority_001.json"))
    routing = _load(os.path.join(REPORTS, "raleigh_nc_routing_001.json"), {})

    pf = {r["identity_key"] for r in clean["clean_pet_friendly"]}
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
            elif not url:
                state = "AWAITING_OFFICIAL_URL"
                action = ("find a first-party route: no owned harvest, brand roster, brand "
                          "sitemap, destination organisation or map source in this order stated "
                          "an official URL for this identity")
            elif brand == "WYNDHAM":
                state = "AWAITING_ATTENDED_CAPTURE"
                action = ("read the property's own page in an attended browser: Wyndham renders "
                          "its operative policy client-side into .pet-policy-desc and serves a "
                          "plain client only the amenity chip and a nine-language dictionary")
            elif brand == "WOODSPRING":
                state = "AWAITING_POLICY_OBSERVATION"
                action = ("observe a property-specific policy: the page served and states only an "
                          "SEO keyword list and a chain-level line about MOST of our locations, "
                          "neither of which is about this building")
            elif brand in REFUSALS:
                state = "ACCESS_BLOCKED"
                action = ("re-probe the surface and, if it refuses again, read it in an attended "
                          "browser: this family returned %s to a plain client on this run"
                          % REFUSALS[brand])
            else:
                state = "AWAITING_POLICY_OBSERVATION"
                action = ("read this property's own page: it is routed and no pet policy has been "
                          "observed on it by this order")
            row["final_state"] = state
            row["resolved"] = False
            row["next_action"] = action
            row["next_action_source"] = ("PTF-RALEIGH-NC-FINAL-FRESH-CITY-PROOF-001 "
                                         "acquisition passes: owned evidence, brand city pages, "
                                         "brand sitemaps, lead sources, OSM extracts, free static "
                                         "lane and the attended browser pass")
            row["determined_by"] = WORK_ORDER
        row["corridor"] = h.get("corridor")
        row["brand"] = h.get("brand") or ""
        items.append(row)

    counts = Counter(i["final_state"] for i in items)
    doc = OrderedDict((
        ("schema", PARTITION.SCHEMA),
        ("work_order", WORK_ORDER),
        ("market_id", MARKET_ID),
        ("as_of", "2026-09-10"),
        ("what_this_is",
         "Every registered Raleigh identity in exactly one disposition state. A terminal state "
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
