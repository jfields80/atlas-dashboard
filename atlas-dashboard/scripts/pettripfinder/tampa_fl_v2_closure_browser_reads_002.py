"""PTF-TAMPA-FL-V2-TERMINAL-HOLD-CLOSURE-003 -- Phase 5/6: 15 supported-browser
reads (navigate + accessibility-tree find/read_page only -- no scripts,
relays, or CAPTCHA/anti-bot bypass) over the 7 IHG rows the ZIP-fixed static
lane correctly declined to fetch (tampa_fl_v2_closure_static_002 excludes
marriott/hilton/ihg.com as browser-only) plus the 9 known
BROWSER_CAPTURE_NEEDED rows carried over from pass 2. 2 of the 9 known rows
(Holiday Inn Express Tampa East/Ybor City, Staybridge Suites Tampa
East-Brandon) were routed through their working ihg.com property page
instead of the legacy hiexpress.com/staybridge.com custom domain that pass 2
found BROWSER_PERMISSION_DENIED -- the router's route table pointed at the
wrong of two live first-party URLs for the same identity. The other 5 known
Hyatt subdomain rows (*.place.hyatt.com / *.regency.hyatt.com) reached the
same fact through hyatt.com's own (non-subdomain) hotel-info/policies pages
instead. Hotel Flor Tampa Downtown (Hilton) reproduces the exact
"Something went wrong" error page pass 2 documented and stays
ACCESS_BLOCKED; not retried further (no new lane exists to try).

One of the 7 -- "Holiday Inn Tampa Airport Westshore" (tpacp, 700 N
Westshore Blvd, 33609) -- is a duplicate identity of the already-resolved
"Holiday Inn Tampa Westshore - Airport Area" (700 North West Shore
Boulevard, 33609, CLEAN_PET_FRIENDLY since pass 2): same building, two
identity_keys from a street-spelling variance census_reconciliation's
dedup never folded. Its read is recorded here for completeness but is
EXCLUDED from clean_authority's evidence feed (duplicate_of set) -- the
identity itself is retired by tampa_fl_v2_closure_dedup_002.py, not
double-counted as a new resolution.

Output:
  launch_packages/pettripfinder/markets/staging/tampa-fl/raw_captures/closure_browser_rows.jsonl (appended)
"""
from __future__ import annotations

import hashlib
import json
import os
from collections import OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
OUT = os.path.join(_DASH, "launch_packages", "pettripfinder", "markets", "staging", "tampa-fl",
                    "raw_captures", "closure_browser_rows.jsonl")
CAPTURED_AT = "2026-09-16T09:00:00Z"
LANE = "supported browser, accessibility tree (navigate + find/read_page only), terminal-hold closure pass"

# identity_key -> duplicate_of identity_key (retired by tampa_fl_v2_closure_dedup_002.py,
# never fed to clean_authority as a second, double-counted resolution).
DUPLICATE_OF = {
    "holiday inn tampa airport westshore": "holiday inn tampa westshore airport area",
}

READS = [
    ("holiday inn", "https://www.ihg.com/holidayinn/hotels/us/en/st-petersburg/tpapb/hoteldetail", True,
     "Pets are welcome at Holiday Inn St. Petersburg West."),
    ("holiday inn express and suites hotel busch gardens and usf",
     "https://www.ihg.com/holidayinnexpress/hotels/us/en/tampa/tpabb/hoteldetail", True,
     "Pets are welcome at Holiday Inn Express & Suites Tampa -USF-Busch Gardens."),
    ("holiday inn express oldsmar",
     "https://www.ihg.com/holidayinnexpress/hotels/us/en/oldsmar/oldfl/hoteldetail", True,
     "Pets are welcome at Holiday Inn Express & Suites Tampa Northwest-Oldsmar."),
    ("holiday inn harbourside", "https://www.ihg.com/holidayinn/hotels/us/en/clearwater/clwrb/hoteldetail", False,
     "No, pets are not allowed at Holiday Inn & Suites Clearwater Beach S-Harbourside."),
    ("holiday inn hotel and suites clearwater beach",
     "https://www.ihg.com/holidayinn/hotels/us/en/clearwater-beach/clwgv/hoteldetail", False,
     "No, pets are not allowed at Holiday Inn & Suites Clearwater Beach."),
    ("holiday inn tampa airport westshore",
     "https://www.ihg.com/holidayinn/hotels/us/en/tampa/tpacp/hoteldetail", True,
     "Pet-friendly (150 USD / stay). Pet damage deposit: 150 USD."),
    ("staybridge suites", "https://www.ihg.com/staybridge/hotels/us/en/st-petersburg/piesb/hoteldetail", True,
     "Pets are welcome at Staybridge Suites St. Petersburg Downtown."),
    ("holiday inn express and suites tampa east ybor city",
     "https://www.ihg.com/holidayinnexpress/hotels/us/en/tampa/tpans/hoteldetail", False,
     "No, pets are not allowed at Holiday Inn Express & Suites Tampa East - Ybor City."),
    ("holiday inn express hotel and suites i 75 new tampa",
     "https://www.ihg.com/holidayinnexpress/hotels/us/en/tampa/tpabd/hoteldetail", True,
     "Pets are welcome at Holiday Inn Express & Suites Tampa-I-75 @ Bruce B. Downs. Pet policy description: "
     "2 well behaved dogs under 35lbs. Pets not allowed on Elevators or in Suites."),
    ("staybridge suites tampa east brandon",
     "https://www.ihg.com/staybridge/hotels/us/en/tampa/tpasb/hoteldetail", True,
     "Pets are welcome at Staybridge Suites Tampa East- Brandon. There is a pet deposit per stay of 75 USD."),
    ("hyatt house tampa airport westshore",
     "https://www.hyatt.com/hyatt-house/en-US/tpaxw-hyatt-house-tampa-airport-westshore/hotel-info", True,
     "Hyatt House Tampa Airport / Westshore is a pet-friendly hotel that welcomes up to two dogs per room."),
    ("hyatt place and hyatt house tampa downtown",
     "https://www.hyatt.com/hyatt-place/en-US/tpazd-hyatt-place-tampa-downtown/hotel-info", True,
     "Your pets are welcome at Hyatt Place Tampa Downtown. Bring up to two dogs along when you stay with us."),
    ("hyatt place saint petersburg downtown",
     "https://www.hyatt.com/hyatt-place/en-US/piezd-hyatt-place-st-petersburg-downtown/hotel-info", True,
     "Your dogs are welcome when you stay at our pet-friendly hotel in downtown St. Pete. We welcome up to "
     "2 pets, maximum number of pets is 2."),
    ("hyatt place tampa busch gardens",
     "https://www.hyatt.com/hyatt-place/en-US/tpazb-hyatt-place-tampa-busch-gardens/hotel-info", True,
     "We welcome your furry friends at Hyatt Place Tampa/Busch Gardens."),
    ("hyatt regency clearwater resort and spa",
     "https://www.hyatt.com/hyatt-regency/en-US/pierc-hyatt-regency-clearwater-beach-resort-and-suites/policies",
     False, "This hotel does not allow pets with the exception of service animals."),
]

BLOCKED = [
    ("hotel flor tampa downtown tapestry collection by hilton",
     "https://www.hilton.com/en/hotels/tpamtup-hotel-flor-tampa-downtown/",
     '"Something went wrong" error page, reproduced identically to pass 2 -- no new lane exists to retry.'),
]


def sha(u, q):
    return hashlib.sha256((u + "|" + q).encode("utf-8")).hexdigest()


def main():
    lines = []
    for key, url, pets_allowed, quote in READS:
        row = OrderedDict([
            ("identity_key", key), ("requested_url", url), ("final_url", url),
            ("capture_lane", LANE), ("captured_at", CAPTURED_AT), ("outcome", "READ"),
            ("pets_allowed", pets_allowed), ("quote", quote), ("transcription_sha256", sha(url, quote)),
        ])
        if key in DUPLICATE_OF:
            row["duplicate_of"] = DUPLICATE_OF[key]
        lines.append(row)
    for key, url, note in BLOCKED:
        lines.append(OrderedDict([
            ("identity_key", key), ("requested_url", url), ("final_url", url),
            ("capture_lane", LANE), ("captured_at", CAPTURED_AT), ("outcome", "BLOCKED"),
            ("note", note),
        ]))

    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "a", encoding="utf-8", newline="\n") as f:
        for row in lines:
            f.write(json.dumps(row, ensure_ascii=False) + "\n")
    print("appended", len(lines), "rows (", sum(1 for r in lines if r.get('outcome') == 'READ'), "READ,",
          sum(1 for r in lines if r.get('outcome') == 'BLOCKED'), "BLOCKED)")


if __name__ == "__main__":
    main()
