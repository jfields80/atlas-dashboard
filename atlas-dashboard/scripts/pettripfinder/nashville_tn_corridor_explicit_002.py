"""PTF-NASHVILLE-TN-NEW-MARKET-001 -- Phase 2b, the two by-name corridors.

WHY TWO CORRIDORS CLAIM NO POSTAL CODE
--------------------------------------
Nashville has two traveler districts that a postal partition cannot express,
and this order authored a corridor for each rather than pretending they are not
there:

  OPRYLAND / MUSIC VALLEY   ZIP 37214 carries BOTH the Donelson/BNA airport
                            cluster AND the Gaylord Opryland cluster four miles
                            north. One ZIP, two markets.
  VANDERBILT / WEST END     ZIP 37203 carries the Gulch, Midtown, Music Row AND
                            the West End Avenue spine. Six operators name their
                            own properties "Vanderbilt/West End"; the ZIP cannot.

Membership is untouched: 37214 belongs to ``airport-donelson`` and 37203 to
``the-gulch-midtown-music-row``, both for MEMBERSHIP, and every hotel below is
already an admitted census row. This file only decides DISPLAY, which
``markets.assignment.assign_hotels`` resolves at tier 2 (``explicit_hotel_ids``)
ahead of the tier-3 ZIP match.

WHAT DECIDES A MEMBERSHIP HERE
------------------------------
The STREET the property's own page states, and nothing else. Not a name, not a
guess, not a distance. Four streets are the Opryland cluster and three are the
West End spine; a hotel is in one of these corridors when its own address is on
one of them.

McGavock Pike is DELIBERATELY not on the Opryland list even though one property
on it is named "near Opryland". The road runs from the airport terminal to Opry
Mills and carries the Sheraton Music City and an Aloft that are airport hotels
by any reading. A street that genuinely spans two districts cannot decide
either, so those rows stay in the airport corridor and the corridor note says so.

Output:
  launch_packages/pettripfinder/markets/proposed/nashville-tn.json (in place)
  launch_packages/pettripfinder/markets/reports/nashville_tn_corridor_explicit_002.json
"""
from __future__ import annotations

import json
import os
import re
import sys
from collections import OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

from scripts.pettripfinder.site_data import normalize_name  # noqa: E402

WORK_ORDER = "PTF-NASHVILLE-TN-NEW-MARKET-001"
MARKET_ID = "nashville-tn"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
CONTRACT = os.path.join(PKG, "markets", "proposed", "nashville-tn.json")
CENSUS = os.path.join(PKG, "identity_census_proposed", "nashville-tn.json")
OUT = os.path.join(PKG, "markets", "reports", "nashville_tn_corridor_explicit_002.json")

#: ``corridor slug -> (the ZIP that corridor's hotels sit in, the streets)``.
#: A street here is matched on the property's OWN stated address, normalised,
#: as a whole-word phrase. Nothing is matched on a hotel's name.
BY_STREET = OrderedDict([
    ("opryland-music-valley", ("37214", [
        "music valley drive", "music valley dr",
        "opryland drive", "opryland dr",
        "music city circle",
        "rudy circle",
    ])),
    ("vanderbilt-west-end", ("37203", [
        "west end avenue", "west end ave",
        "hayes street",
        "29th avenue north",
    ])),
])
#: Streets considered and DELIBERATELY excluded, with the reason. Recorded so
#: the next order does not re-derive the judgement.
CONSIDERED_AND_EXCLUDED = OrderedDict([
    ("mcgavock pike", "runs from the BNA terminal to Opry Mills and carries both an "
                      "airport Aloft and the Sheraton Music City as well as a Home2 "
                      "named 'near Opryland'. A street that spans two districts "
                      "cannot decide either; these rows stay in airport-donelson."),
    ("broadway", "the Broadway address range crosses Midtown, Music Row and the "
                 "downtown honky-tonk strip; the ZIP already separates them."),
    ("division street", "the Gulch and Midtown share it."),
])


def _load(p):
    with open(p, encoding="utf-8") as fh:
        return json.load(fh)


def normalise_street(street):
    s = re.sub(r"[^a-z0-9 ]+", " ", (street or "").lower())
    return re.sub(r"\s+", " ", s).strip()


def main():
    contract = _load(CONTRACT)
    census = _load(CENSUS)
    by_slug = {c["slug"]: c for c in contract["corridors"]}

    assigned, report_rows = {}, []
    for slug, (zip5, streets) in BY_STREET.items():
        picked = []
        for h in census["hotels"]:
            if (h.get("postal_code") or "") != zip5:
                continue
            norm = normalise_street(h.get("street"))
            hit = next((s for s in streets if (" %s " % s) in (" %s " % norm)), "")
            if not hit:
                continue
            key = normalize_name(h["canonical_name"])
            if not key or key in assigned:
                continue
            assigned[key] = slug
            picked.append(key)
            report_rows.append(OrderedDict([
                ("corridor", slug), ("identity_key", key),
                ("canonical_name", h["canonical_name"]),
                ("street_the_page_states", h["street"]),
                ("postal_code", h["postal_code"]),
                ("matched_street", hit),
                ("basis", "the STREET the property's own page states; never its name"),
            ]))
        corridor = by_slug[slug]
        corridor["explicit_hotel_ids"] = sorted(picked)
        corridor["_explicit_basis"] = (
            "PTF-NASHVILLE-TN-NEW-MARKET-001 assigned these by the STREET each "
            "property's own page states, from %s. Membership is unaffected: postal "
            "code %s belongs to another corridor and every row here was already "
            "admitted by it. This list decides DISPLAY only, at tier 2 of "
            "markets.assignment.assign_hotels, which outranks the tier-3 ZIP match."
            % (", ".join(streets), zip5))

    with open(CONTRACT, "w", encoding="utf-8") as fh:
        json.dump(contract, fh, indent=1)
        fh.write("\n")

    doc = OrderedDict([
        ("schema", "ptf-corridor-explicit-assignment/1.0"),
        ("work_order", WORK_ORDER), ("market_id", MARKET_ID),
        ("phase", "2b -- the two corridors a postal partition cannot express"),
        ("what_this_is",
         "Two Nashville traveler districts share a postal code with a different "
         "district. Rather than pretend they are not there, or widen a ZIP and "
         "place hotels wrongly, each is a corridor that claims NO postal code and "
         "names its properties explicitly."),
        ("membership_is_unaffected",
         "37214 belongs to airport-donelson and 37203 to the-gulch-midtown-music-row "
         "for MEMBERSHIP. Every hotel named here was already an admitted census row "
         "under those corridors. Only the display area changes."),
        ("what_decides_it",
         "the STREET the property's own page states. Not a name, not a distance, not "
         "a guess."),
        ("streets_considered_and_excluded", CONSIDERED_AND_EXCLUDED),
        ("counts", OrderedDict(
            (slug, len(by_slug[slug]["explicit_hotel_ids"])) for slug in BY_STREET)),
        ("assignments", report_rows),
    ])
    with open(OUT, "w", encoding="utf-8") as fh:
        json.dump(doc, fh, indent=1)
        fh.write("\n")

    for slug in BY_STREET:
        print("%-28s %d hotels" % (slug, len(by_slug[slug]["explicit_hotel_ids"])))
    for r in report_rows:
        print("   %-26s %-46s %s" % (r["corridor"], r["canonical_name"][:46],
                                     r["street_the_page_states"]))
    print("written", os.path.relpath(OUT, _DASH))


if __name__ == "__main__":
    main()
