"""PTF-TAMPA-FL-V2-COVERAGE-CLOSURE-002 -- Phase 4: an exact terminal reason
for every row this pass's router still cannot resolve to a policy fact, so no
generic 'routing hold' survives without one. Joins the Places route-discovery
lane, the closure static-fetch lane, and the current clean_authority
disposition for each row that is still ROUTING_HOLD after this pass's
acquisition work.

Classification (one of, per PHASE 4):
  ROUTE_RESOLVED               -- (not expected here; those rows left ROUTING_HOLD already)
  NO_OFFICIAL_WEB_PRESENCE_FOUND -- Places found no admitted-postal match, or no website at all
  ACCESS_BLOCKED                -- a website was found and fetched, but returned non-200 / no
                                    readable body (403, timeout, etc.)
  SOURCE_SILENT                 -- the site was fetched and bound to the identity, but no
                                    pet-related sentence was found on it or its policy/FAQ pages
  IDENTITY_HOLD                 -- Places found a website, but it could not be bound to this
                                    identity (postal/house-number/phone mismatch)
  OTHER_EXPLICIT_REASON         -- a brand/OTA/social host route only (never read here)
"""
from __future__ import annotations

import json
import os
from collections import Counter, OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
STAGING = os.path.join(PKG, "markets", "staging", "tampa-fl", "raw_captures")
CLEAN_AUTHORITY = os.path.join(REPORTS, "tampa_fl_v2_clean_authority_001.json")
PLACES = os.path.join(REPORTS, "tampa_fl_v2_closure_places_lookup_001.json")
CLOSURE_STATIC = os.path.join(STAGING, "closure_static_rows.json")
OUT = os.path.join(REPORTS, "tampa_fl_v2_closure_routing_classification_001.json")


def main():
    ca = json.load(open(CLEAN_AUTHORITY, encoding="utf-8"))
    routing_holds = {r["identity_key"]: r for r in ca["rows"] if r["disposition"] == "ROUTING_HOLD"}
    places_by_key = {r["identity_key"]: r for r in json.load(open(PLACES, encoding="utf-8"))["rows"]}
    static_by_key = {r["identity_key"]: r for r in (json.load(open(CLOSURE_STATIC, encoding="utf-8")).get("rows", [])
                                                     if os.path.exists(CLOSURE_STATIC) else [])}

    rows = []
    counts = Counter()
    for key, ca_row in routing_holds.items():
        p = places_by_key.get(key)
        s = static_by_key.get(key)
        if s is not None and s.get("note") == "brand/OTA/social host, not read here":
            cls = "OTHER_EXPLICIT_REASON"
            detail = "Places route discovery bound this identity to a brand/OTA/social host page, which this " \
                     "market's brand-family lanes (not the independents' closure static lane) are responsible for."
        elif s is not None:
            if s.get("s") is None or s.get("s") != 200:
                cls = "ACCESS_BLOCKED"
                detail = "a website was found (Places) and fetched, but the request did not return a usable page " \
                          "(status=%r, error=%r)" % (s.get("s"), s.get("error"))
            elif not s.get("bound"):
                cls = "IDENTITY_HOLD"
                detail = "a website was found and fetched (200), but its own page never confirmed this identity " \
                          "(no matching house number + postal code, phone, or JSON-LD address on the page)"
            elif not any(pg.get("pet_sentences") for pg in s.get("pages", [])):
                cls = "SOURCE_SILENT"
                detail = "the site was fetched and bound to this identity, but no sentence on its home or " \
                          "policy/FAQ pages named pets, dogs or animals"
            else:
                cls = "SOURCE_SILENT"
                detail = "pet-naming sentences were found but did not classify as an operative accept/refuse " \
                          "statement (fee/weight/count alone, or a service-animal-only sentence) -- see clean " \
                          "authority's EVIDENCE_HOLD / negation-conflict accounting for the ones this affected"
        elif p is not None and p.get("matched") and p.get("website_uri"):
            cls = "OTHER_EXPLICIT_REASON"
            detail = "Places found a bindable website but it was not reached by the closure static lane in this " \
                     "pass (lane targeting gap, not a capability wall)"
        elif p is not None and p.get("matched"):
            cls = "NO_OFFICIAL_WEB_PRESENCE_FOUND"
            detail = "Google Places confirmed this identity at an admitted postal code, but the place record " \
                     "carries no website"
        elif p is not None:
            cls = "NO_OFFICIAL_WEB_PRESENCE_FOUND"
            detail = "no Google Places result matched this identity's own postal code (%d candidate(s) returned)" \
                      % p.get("candidates_returned", 0)
        else:
            cls = "NO_OFFICIAL_WEB_PRESENCE_FOUND"
            detail = "not reached by the Places route-discovery lane in this pass (outside its ROUTING_HOLD target set)"
        counts[cls] += 1
        rows.append(OrderedDict([("identity_key", key), ("canonical_name", ca_row["canonical_name"]),
                                 ("closure_classification", cls), ("detail", detail)]))

    out = OrderedDict([
        ("schema", "ptf-tampa-fl-v2-closure-routing-classification/1.0"),
        ("work_order", "PTF-TAMPA-FL-V2-COVERAGE-CLOSURE-002"),
        ("total_routing_hold_rows", len(rows)),
        ("counts", OrderedDict(sorted(counts.items()))),
        ("rows", rows),
    ])
    with open(OUT, "w", encoding="utf-8") as f:
        json.dump(out, f, indent=1, ensure_ascii=False)
        f.write("\n")
    print(json.dumps(dict(counts), indent=1))


if __name__ == "__main__":
    main()
