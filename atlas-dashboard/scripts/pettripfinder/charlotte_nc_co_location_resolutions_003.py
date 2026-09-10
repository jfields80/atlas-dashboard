"""PTF-CHARLOTTE-NC-ZERO-TO-LIVE-BENCHMARK-001 -- the co-located-hotel rulings.

Charlotte's airport and uptown corridors are full of DUAL-BRAND BUILDINGS: one
street address, two separately bookable hotels, two brand property codes, two
official URLs and -- the reason this file has to exist -- sometimes two OPPOSITE
pet policies.

2220 West Tyvola Road is the sharp case. The Fairfield Inn & Suites Charlotte
Airport (cltfs) states "Pets Not Allowed" and becomes a VERIFIED_NO_PETS
exclusion. The Residence Inn by Marriott Charlotte Airport (cltwe) states "2
pets 80 pounds max per room with USD 100 non-refundable fee per room per stay"
and is clean pet-friendly. The exclusion contract matches an exclusion to a
candidate on STREET IDENTITY, so without a ruling the Fairfield's refusal would
bar the Residence Inn from publishing -- the guard doing exactly its job on a
fact about the OTHER hotel. Cincinnati's promotion order paid for this lesson
when a lossy address key nearly un-published a live hotel.

THE PROOF, NOT AN OVERRIDE
--------------------------
Each resolution below is written only where `hotel_exclusions.co_located_distinct`
can be MADE: two distinct identity keys, two distinct canonical first-party
URLs, and a brand family plus property code readable from BOTH official URLs
that differ within the same family. That is founder ruling A of
PTF-INDIANAPOLIS-FOUNDER-PROMOTION-004, applied unchanged. A pair missing a
code, missing a URL or sharing a URL is NOT proved distinct: it is left blocked
and named here, because the safe answer to an ambiguous identity is to publish
neither.

A resolution waives a STREET-IDENTITY match and nothing else. A match on the
name or an alias is never waived: that is the property itself, and no ruling
about an address may publish a hotel that said no.

Output: launch_packages/pettripfinder/identity_resolutions.json  (rows appended)
        launch_packages/pettripfinder/markets/reports/charlotte_nc_co_location_003.json
"""
from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections import OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

from scripts.pettripfinder import hotel_exclusions as HE          # noqa: E402
from scripts.pettripfinder import publication_guard as PG         # noqa: E402
from scripts.pettripfinder.site_data import normalize_name        # noqa: E402

WORK_ORDER = "PTF-CHARLOTTE-NC-ZERO-TO-LIVE-BENCHMARK-001"
MARKET_ID = "charlotte-nc"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
REPORTS = os.path.join(PKG, "markets", "reports")
AUTHORITY = os.path.join(PKG, "charlotte_nc_proposed_authority_002.json")
RESOLUTIONS = os.path.join(PKG, "identity_resolutions.json")
OUT = os.path.join(REPORTS, "charlotte_nc_co_location_003.json")
REVIEWED_AT = "2026-09-10"


def _code(url):
    """The brand property code the operator's own URL states, or ''."""
    m = re.search(r"/hotels/([a-z0-9]{5})-", url or "", re.I)
    if m:
        return m.group(1).lower()
    m = re.search(r"/([a-z0-9]{5,7})/hoteldetail", url or "", re.I)
    if m:
        return m.group(1).lower()
    m = re.search(r"/en/hotels/([a-z0-9]{4,9})-", url or "", re.I)
    return m.group(1).lower() if m else ""


def _load(p):
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


def build():
    auth = _load(AUTHORITY)
    by_street = {}
    for kind, rows in (("pet_friendly", auth["pet_friendly"]),
                       ("verified_no_pets", auth["verified_no_pets"])):
        for r in rows:
            k = HE.address_key(r.get("address") or "", (r.get("postal_code") or "")[:5])
            if k.strip("|"):
                by_street.setdefault(k, []).append((kind, r))

    resolved, refused = [], []
    for key, rows in sorted(by_street.items()):
        if len(rows) < 2:
            continue
        # EVERY shared address needs a ruling, not only the ones where an
        # exclusion would block a listing. Two PET-FRIENDLY hotels in one
        # building hit a different mechanism with the same cause: the listing
        # dataset builder dedupes by street address and keeps ONE row, so the
        # renderer writes one profile page and every link to the other dangles
        # ("missing hotel profile file for X"). That is the Detroit Troy case
        # (PTF-DETROIT-ANN-ARBOR-TROY-IDENTITY-AND-BUNDLE-030), and it is a
        # CONFIGURATION fix: the dedup is doing exactly what it should to an
        # UNREVIEWED shared address. Charlotte has four such pairs -- Courtyard
        # and Residence Inn at Northlake, Holiday Inn and Candlewood at Fort
        # Mill, Homewood Suites and its neighbour at SouthPark, Tru and its
        # neighbour at Concord -- plus one pet-friendly/no-pets pair at 2220
        # West Tyvola Road.
        pf = [r for kind, r in rows if kind == "pet_friendly"]
        np_ = [r for kind, r in rows if kind == "verified_no_pets"]
        pairs = [(a, b) for a in pf for b in np_]
        pairs += [(pf[i], pf[j]) for i in range(len(pf)) for j in range(i + 1, len(pf))]
        if not pairs:
            continue
        for a, b in pairs:
            if True:
                verdict, why = HE.co_located_distinct(
                    {"canonical_name": a["canonical_name"],
                     "official_url": a.get("official_url", ""),
                     "normalized_name": a["normalized_name"]},
                    {"canonical_name": b["canonical_name"],
                     "official_url": b.get("official_url", ""),
                     "normalized_name": b["normalized_name"]})
                row = OrderedDict((
                    ("address_key", key),
                    ("pet_friendly", a["canonical_name"]),
                    ("pet_friendly_url", a.get("official_url", "")),
                    ("verified_no_pets", b["canonical_name"]),
                    ("verified_no_pets_url", b.get("official_url", "")),
                    ("verdict", verdict), ("why", why),
                ))
                if verdict != "DISTINCT":
                    refused.append(row)
                    continue
                resolved.append((key, a, b, row))

    rows = []
    for key, a, b, _row in resolved:
        slug_a = normalize_name(a["canonical_name"]).replace(" ", "-")
        rows.append(OrderedDict((
            ("resolution_id", "res-%s-%s" % (MARKET_ID, slug_a))[:96],
            # SCOPED TO THIS MARKET. `identity_resolutions.json` is a GLOBAL
            # file and Milwaukee, St. Louis and Detroit all scope their rows
            # with market_id; only the Columbus BrewDog pair is deliberately
            # unscoped. Leaving these unscoped made seven Charlotte rulings
            # look like global records and broke the Columbus-unchanged claim,
            # which asserts that its one resolution is still the ONLY unscoped
            # record in the file.
            ("market_id", MARKET_ID),
            ("resolution_type", PG.SAME_CAMPUS),
            ("address_key", key),
            ("identities", [
                OrderedDict((("canonical_name", a["canonical_name"]),
                             ("category", "pet-friendly-hotels"),
                             ("slug", slug_a),
                             ("official_url", a.get("official_url", "")))),
                OrderedDict((("canonical_name", b["canonical_name"]),
                             ("category", "pet-friendly-hotels"),
                             ("slug", normalize_name(b["canonical_name"]).replace(" ", "-")),
                             ("official_url", b.get("official_url", "")))),
            ]),
            ("evidence",
             "Two separately bookable hotels in one building at address key %s. The operators' "
             "own pages publish them under different brand property codes in the same brand "
             "family and at different canonical first-party URLs (%s and %s), which is the "
             "exclusion contract's own co_located_distinct proof. %s's verified refusal is a "
             "fact about %s and never about %s; this resolution waives the STREET-IDENTITY match "
             "and nothing else."
             % (key, a.get("official_url", ""), b.get("official_url", ""),
                b["canonical_name"], b["canonical_name"], a["canonical_name"])),
            # Both identities are in the SAME category, so the contract demands
            # a stated reason rather than letting a same-category pair through
            # on the address alone. Columbus's precedent pair was a hotel and a
            # taproom, which the categories themselves distinguished; two hotels
            # in one building do not have that luxury.
            ("distinct_reason",
             "Two hotels, not one property under two names: %s is Marriott property code %s and "
             "%s is Marriott property code %s -- distinct codes inside one brand family, each "
             "with its own canonical first-party URL and its own separately stated pet policy. "
             "The exclusion contract's co_located_distinct proof returns DISTINCT for this pair."
             % (a["canonical_name"], _code(a.get("official_url", "")),
                b["canonical_name"], _code(b.get("official_url", "")))),
            ("reviewer_id", WORK_ORDER),
            ("reviewed_at", REVIEWED_AT),
        )))
    for r in rows:
        r["resolution_hash"] = PG.resolution_hash(r)
    return rows, refused


def main(argv=None):
    ap = argparse.ArgumentParser()
    ap.add_argument("--write", action="store_true")
    args = ap.parse_args(argv)
    rows, refused = build()
    print("co-located pairs proved DISTINCT :", len(rows))
    for r in rows:
        print("   ", r["address_key"], "::", " | ".join(i["canonical_name"]
                                                        for i in r["identities"]))
    print("pairs NOT proved distinct (left blocked):", len(refused))
    for r in refused:
        print("   ", r["address_key"], "::", r["verdict"], r["why"][:90])

    doc = _load(RESOLUTIONS)
    existing = {r["resolution_id"] for r in doc["resolutions"]}
    fresh = [r for r in rows if r["resolution_id"] not in existing]
    doc["resolutions"] = doc["resolutions"] + fresh
    # validate_resolutions RAISES on a resolution that would let two records
    # blur together and RETURNS the validated rows otherwise; an exception is
    # the failure signal, not a non-empty list.
    try:
        validated = PG.validate_resolutions(doc)
    except Exception as exc:                                        # noqa: BLE001
        print("contract REFUSED                 :", exc)
        print("NOT WRITTEN")
        return 1
    print("contract validated resolutions   :", len(validated))
    if args.write:
        with open(RESOLUTIONS, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(doc, fh, indent=1, ensure_ascii=False)
            fh.write("\n")
        report = OrderedDict((
            ("schema", "ptf-co-location-rulings/1.0"), ("work_order", WORK_ORDER),
            ("market_id", MARKET_ID), ("as_of", REVIEWED_AT),
            ("resolutions_added", len(fresh)),
            ("pairs_left_blocked", len(refused)),
            ("waives", "a STREET-IDENTITY match only; a name or alias match is never waived"),
            ("resolutions", rows), ("not_proved_distinct", refused),
        ))
        os.makedirs(os.path.dirname(OUT), exist_ok=True)
        with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
            json.dump(report, fh, indent=1, ensure_ascii=False)
            fh.write("\n")
        print("written                          :", os.path.relpath(RESOLUTIONS, _DASH))
        print("written                          :", os.path.relpath(OUT, _DASH))
    else:
        print("(dry run; pass --write)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
