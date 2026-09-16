"""PTF-ORLANDO-FL-V2-TARGETED-COVERAGE-CLOSURE-002 -- free static first-party reads for the targeted cohort.

The closure order works only three cohorts: the BringFido-matched unresolved hotels, the 23 hotels V1 published
pet-friendly that V2 did not, and the hotels that could change a corridor's publishing decision. For the targets whose
OWN page (or the brand's own property page) answers a plain client, this lane is the router's DIRECT_STATIC_FETCH rung --
no provider, no credit.

For each target it:
  1. fetches the page (documents persisted by sha256 under data/acquisition/orlando_fl_v2_closure_static_001/);
  2. binds the page to the census identity: the census house number AND postal code in the page text, the census
     phone, or the page's own structured streetAddress/postalCode -- a name never binds;
  3. requires every quoted sentence to be present, character for character, in the page's visible text (fail closed:
     one missing sentence drops the row, recorded in `dropped`);
  4. writes the explicit facts those sentences state -- nothing inferred.

Output: launch_packages/pettripfinder/markets/staging/orlando-fl/raw_captures/closure_static_rows.json
"""
from __future__ import annotations

import html
import json
import os
import re
import sys
import time
from collections import OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

from scripts.pettripfinder import orlando_fl_v2_brand_inventory_001 as B  # noqa: E402

B.DOCS = os.path.join(_DASH, "data", "acquisition", "orlando_fl_v2_closure_static_001")
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
CENSUS = os.path.join(PKG, "identity_census", "orlando-fl.json")
OUT = os.path.join(PKG, "markets", "staging", "orlando-fl", "raw_captures", "closure_static_rows.json")

# identity_key -> (brand, url, [verbatim sentences], extraction, cohorts)
READS = OrderedDict([
    ("drury inn and suites near universal orlando resort", (
        "DRURY", "https://www.druryhotels.com/locations/orlando-fl/drury-inn-and-suites-near-universal-orlando-resort",
        ["Pet Policy Dogs and cats accepted", "Limit of two pets per room with a combined weight of 80 pounds"],
        {"pets_allowed": True, "species_allowed": ["dog", "cat"], "pet_count_limit": 2, "weight_limit": 80,
         "weight_limit_unit": "lb", "weight_basis": "combined"}, ["BRINGFIDO"])),
    ("drury plaza hotel orlando disney springs area", (
        "DRURY", "https://www.druryhotels.com/locations/orlando-fl/drury-plaza-hotel-orlando",
        ["Pet Policy Dogs and cats accepted", "Limit of two pets per room with a combined weight of 80 pounds"],
        {"pets_allowed": True, "species_allowed": ["dog", "cat"], "pet_count_limit": 2, "weight_limit": 80,
         "weight_limit_unit": "lb", "weight_basis": "combined"}, ["CORRIDOR_CRITICAL:walt-disney-world"])),
    ("sonesta es suites orlando lake buena vista", (
        "SONESTA", "https://www.sonesta.com/sonesta-es-suites/fl/orlando/sonesta-es-suites-orlando-lake-buena-vista",
        ["Sonesta ES Suites Orlando – Lake Buena Vista is pet-friendly and welcomes well-mannered pets, with no breed or "
         "weight restrictions", "Up to two pets are permitted per suite"],
        {"pets_allowed": True, "pet_count_limit": 2}, ["BRINGFIDO", "V1_REGRESSION"])),
    ("lake nona wave hotel", (
        "INDEPENDENT", "https://www.lakenonawavehotel.com/faq",
        ["Is The Hotel Pet Friendly", "We welcome pets under 40 lbs"],
        {"pets_allowed": True, "weight_limit": 40, "weight_limit_unit": "lb"}, ["BRINGFIDO", "V1_REGRESSION"])),
    ("westgate blue tree at lake buena vista", (
        "INDEPENDENT", "https://www.westgateresorts.com/hotels/florida/orlando/westgate-blue-tree-resort/",
        ["At Westgate Blue Tree Resort we are a pet-friendly hotel",
         "Up to 2 dogs are allowed per unit and the combined weight of both pets must not exceed 60 pounds"],
        {"pets_allowed": True, "species_allowed": ["dog"], "pet_count_limit": 2, "weight_limit": 60,
         "weight_limit_unit": "lb", "weight_basis": "combined"}, ["BRINGFIDO"])),
    ("the delaney hotel", (
        "INDEPENDENT", "https://staydh.com/rooms",
        ["Pets Welcome: One pet 40 pounds or less is allowed with $50/night non-refundable fee"],
        {"pets_allowed": True, "pet_count_limit": 1, "weight_limit": 40, "weight_limit_unit": "lb"}, ["BRINGFIDO"])),
    ("omni championsgate resort hotel lp", (
        "OMNI", "https://www.omnihotels.com/hotels/orlando-championsgate/property-details/policies",
        ["Pet Policy Pets under 50 lbs. are allowed on the second floor of the main resort building, deluxe rooms only",
         "Pets are not permitted in the villas"],
        {"pets_allowed": True, "weight_limit": 50, "weight_limit_unit": "lb"},
        ["CORRIDOR_CRITICAL:four-corners-davenport"])),
    ("park plaza", (
        "INDEPENDENT", "https://parkplazahotel.com/service/policies/",
        ["Dogs up to 25 pounds allowed with a non-refundable pet fee"],
        {"pets_allowed": True, "species_allowed": ["dog"], "weight_limit": 25, "weight_limit_unit": "lb"},
        ["CORRIDOR_CRITICAL:winter-park-maitland"])),
])

# The name the property's OWN page states, where the census still carries a registry licensee name.
PAGE_NAMES = {
    "omni championsgate resort hotel lp": "Omni Orlando Resort at ChampionsGate",
    "park plaza": "Park Plaza Hotel",
}


def _visible(body):
    t = body.decode("utf-8", "replace")
    t = re.sub(r"(?s)<script.*?</script>|<style.*?</style>|<noscript.*?</noscript>", " ", t)
    return " ".join(html.unescape(re.sub(r"<[^>]+>", " ", t)).split())


def _digits(s):
    return re.sub(r"\D", "", s or "")[-10:]


def main():
    hotels = json.load(open(CENSUS, encoding="utf-8"))["hotels"]
    census = {h["identity_key"]: h for h in hotels}
    # a read renames its building to the name the page states; the baseline key survives as an alias
    for h in hotels:
        for alias in h.get("identity_key_aliases") or []:
            census.setdefault(alias, h)
    st = B.Stats()
    rows, dropped = [], []
    for key, (brand, url, sentences, ext, cohorts) in READS.items():
        h = census.get(key)
        if h is None:
            dropped.append(OrderedDict([("identity_key", key), ("why", "NOT_IN_THE_CENSUS")]))
            continue
        time.sleep(0.8)
        row, body = B.fetch(url, st, timeout=30)
        if row["status"] != 200 or not body:
            # one polite retry: omnihotels.com answered 200 and 403 to the same URL minutes apart
            time.sleep(8)
            row, body = B.fetch(url, st, timeout=30)
        if row["status"] != 200 or not body:
            dropped.append(OrderedDict([("identity_key", key), ("why", "STATIC_STATUS_%s" % row["status"])]))
            continue
        vis = _visible(body)
        raw = body.decode("utf-8", "replace")
        num = (h.get("street") or "").split()[0] if h.get("street") else ""
        z = (h.get("postal_code") or "")[:5]
        ld_streets = re.findall(r'"streetAddress"\s*:\s*"([^"]+)"', raw)
        ld_zips = [x[:5] for x in re.findall(r'"postalCode"\s*:\s*"([^"]+)"', raw)]
        bound_by = ("HOUSE_NUMBER_AND_POSTAL_CODE_ON_THE_PAGE" if num and z and re.search(r"\b%s\b" % re.escape(num), vis) and z in vis
                    else "PHONE_ON_THE_PAGE" if _digits(h.get("phone")) and _digits(h.get("phone")) in re.sub(r"\D", "", vis)
                    else "PAGE_STRUCTURED_ADDRESS" if num and z in ld_zips and any(s.split()[:1] == [num] for s in ld_streets)
                    else "")
        if not bound_by:
            dropped.append(OrderedDict([("identity_key", key), ("why", "PAGE_NOT_BOUND_TO_THE_CENSUS_IDENTITY")]))
            continue
        missing = [s for s in sentences if s not in vis]
        if missing:
            dropped.append(OrderedDict([("identity_key", key), ("why", "QUOTED_SENTENCE_NOT_ON_THE_PAGE"), ("missing", missing)]))
            continue
        rows.append(OrderedDict([
            ("identity_key", key), ("brand", brand), ("n", PAGE_NAMES.get(key, h["canonical_name"])), ("u", url), ("final_url", row["final_url"]),
            ("st", h["street"]), ("z", z), ("ph", h.get("phone")), ("h", row["sha256"]), ("b", row["bytes"]),
            ("q", ". ".join(sentences) + "."), ("extraction", ext), ("binding", bound_by), ("cohorts", cohorts),
        ]))
        print("READ", key, bound_by)
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(OrderedDict([("free_http_requests", st.requests), ("rows", rows), ("dropped", dropped)]), fh,
                  indent=1, ensure_ascii=False)
        fh.write("\n")
    print("reads", len(rows), "dropped", dropped)


if __name__ == "__main__":
    main()
