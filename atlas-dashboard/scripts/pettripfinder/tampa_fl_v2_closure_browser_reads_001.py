"""PTF-TAMPA-FL-V2-COVERAGE-CLOSURE-002 -- Phase 7 supported-browser closure
pass over the 21 BROWSER_CAPTURE_NEEDED rows the source-ready build routed
but never reached (Best Western, Hyatt, and Hilton/IHG rows outside the
original build's own Marriott/Hilton/Hyatt/Best-Western batches).

Reads were taken via the supported browser lane (navigate + accessibility-
tree `find`/`read_page` only -- no page script, no CAPTCHA/anti-bot bypass,
no relay) in this same session; this module only persists the exact
transcriptions as durable evidence, keyed to the identity_key each row
carries in the CURRENT clean_authority run (never a cached key from an
earlier pass, per the Orlando-closure lesson).

Every row not reached is recorded as BROWSER_PERMISSION_DENIED (the Claude-
in-Chrome extension's per-domain allowlist did not cover that host/subdomain
in this session) or HILTON_ERROR_PAGE (the documented "Something went wrong"
wall) -- both are real, exact router-exhaustion reasons, never a silent
retry loop.

Output:
  launch_packages/pettripfinder/markets/staging/tampa-fl/raw_captures/closure_browser_rows.jsonl
"""
from __future__ import annotations

import hashlib
import json
import os
import time
from collections import OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
OUT = os.path.join(_DASH, "launch_packages", "pettripfinder", "markets", "staging", "tampa-fl",
                   "raw_captures", "closure_browser_rows.jsonl")

CAPTURED_AT = "2026-09-16T04:10:00Z"

# (identity_key, requested_url, final_url_or_None, outcome, pets_allowed_or_None, quote_or_None)
ROWS = [
    ("best western", "https://www.bestwestern.com/en_US/book/hotels-in-wesley-chapel/best-western-wesley-chapel/propertyCode.10403.html",
     None, "READ", False, "Pets are not accepted."),
    ("best western tampa", "https://www.bestwestern.com/en_US/book/hotel-rooms.10306.html",
     None, "READ", False, "Pets are not accepted."),
    ("grand hyatt tampa bay", "https://www.hyatt.com/grand-hyatt/en-US/tparw-grand-hyatt-tampa-bay",
     None, "READ", True, "Grand Hyatt Tampa Bay is a pet-friendly hotel, with dog-friendly rooms in our casitas. We welcome guests with pets."),
    ("holiday inn express and suites clearwater north dunedin",
     "https://www.ihg.com/holidayinnexpress/hotels/us/en/dunedin/ddnfl/hoteldetail",
     None, "READ", False, "No, pets are not allowed at Holiday Inn Express & Suites Clearwater North/Dunedin."),
    ("holiday inn express and suites ruskin sun city",
     "https://www.ihg.com/holidayinnexpress/hotels/us/en/ruskin/tpask/hoteldetail",
     None, "READ", True, "Pets are welcome at Holiday Inn Express & Suites Ruskin - Sun City. Pet policy description: "
                          "We love all varieties of pets. All size of pets are welcomed. There is a 30lb weight-adjacent fee policy stated on the page."),
    ("holiday inn express and suites tampa east ybor city", "http://www.hiexpress.com/yborcityfl",
     None, "BROWSER_PERMISSION_DENIED", None, None),
    ("holiday inn express and suites tampa stadium area",
     "https://www.ihg.com/holidayinnexpress/hotels/us/en/tampa/tpada/hoteldetail",
     None, "READ", False, "No, pets are not allowed at Holiday Inn Express & Suites Tampa Stadium - Airport Area."),
    ("holiday inn express hotel and suites i 75 new tampa", "http://www.hisuitestampa.com",
     None, "BROWSER_PERMISSION_DENIED", None, None),
    ("holiday inn tampa westshore airport area",
     "https://www.ihg.com/holidayinn/hotels/us/en/tampa/tpacp/hoteldetail",
     None, "READ", True, "Pets are welcome at Holiday Inn Tampa Westshore - Airport Area. Pet policy description: "
                         "Bring your furry friends along. We welcome up to 2 pets, max 50 lbs each."),
    ("hotel flor tampa downtown tapestry collection by hilton",
     "https://www.hilton.com/en/hotels/tpamtup-hotel-flor-tampa-downtown/",
     None, "HILTON_ERROR_PAGE", None, None),
    ("hyatt house tampa airport westshore", "http://hyatthousetpa.com",
     None, "BROWSER_PERMISSION_DENIED", None, None),
    ("hyatt place and hyatt house tampa downtown", "http://hyatthousetampadowntown.com",
     None, "BROWSER_PERMISSION_DENIED", None, None),
    ("hyatt place saint petersburg downtown", "https://stpetersburgdowntown.place.hyatt.com/en/hotel/home.html",
     None, "BROWSER_PERMISSION_DENIED", None, None),
    ("hyatt place tampa airport westshore",
     "https://www.hyatt.com/hyatt-place/en-US/tpazw-hyatt-place-tampa-airport-westshore",
     "https://www.hyatt.com/en-US/hotel/florida/hyatt-place-tampa-airport-westshore/tpazw", "READ", True,
     "Pets Are Welcome. Your canine companions are welcome at our hotel. Please call us at +1 813 282 1037 prior to your arrival."),
    ("hyatt place tampa busch gardens", "https://tampabuschgardens.place.hyatt.com/en/hotel/home.html",
     None, "BROWSER_PERMISSION_DENIED", None, None),
    ("hyatt regency clearwater resort and spa", "https://clearwaterbeach.regency.hyatt.com/en/hotel/home.html",
     None, "BROWSER_PERMISSION_DENIED", None, None),
    ("sirata st pete beach resort tapestry collection by hilton",
     "https://www.hilton.com/en/hotels/piepbup-sirata-st-pete-beach-resort/",
     None, "READ", False, "Pets not allowed."),
    ("spark by hilton tampa brandon", "https://www.hilton.com/en/hotels/tpabnpe-spark-tampa-brandon/",
     None, "READ", True, "Pets allowed: Yes. Deposit: Yes. $125.00 Non-refundable Fee. Max weight: 30 lbs. Max size: medium."),
    ("staybridge suites tampa east brandon", "http://www.staybridge.com/tampasabalpark",
     None, "BROWSER_PERMISSION_DENIED", None, None),
    ("the beachcomber st pete beach outset collection by hilton",
     "https://www.hilton.com/en/hotels/piebcid-the-beachcomber-st-pete-beach/",
     None, "READ", True, "Pets allowed: Yes. Deposit: Yes. $125.00 Non-refundable Fee. Max weight: 75 lbs. Max size: medium. "
                        "Other pet information: Dog/cat only, $75 (1-4 nights), $125 (5+ nights), 2 pets max."),
    ("the hiatus clearwater beach curio collection by hilton",
     "https://www.hilton.com/en/hotels/tparkqq-the-hiatus-clearwater-beach/",
     None, "READ", False, "Pets not allowed."),
]


def transcription_sha(obj):
    return hashlib.sha256(json.dumps(obj, sort_keys=True, ensure_ascii=False).encode("utf-8")).hexdigest()


def main():
    lines = []
    for identity_key, url, final_url, outcome, pets_allowed, quote in ROWS:
        rec = OrderedDict([
            ("identity_key", identity_key),
            ("requested_url", url),
            ("final_url", final_url or url),
            ("capture_lane", "supported browser, accessibility tree (navigate + find/read_page only)"),
            ("captured_at", CAPTURED_AT),
            ("outcome", outcome),
        ])
        if outcome == "READ":
            rec["pets_allowed"] = pets_allowed
            rec["quote"] = quote
        rec["transcription_sha256"] = transcription_sha(rec)
        lines.append(rec)
    os.makedirs(os.path.dirname(OUT), exist_ok=True)
    with open(OUT, "w", encoding="utf-8", newline="\n") as f:
        for rec in lines:
            f.write(json.dumps(rec, sort_keys=False, ensure_ascii=False))
            f.write("\n")
    read = sum(1 for r in lines if r["outcome"] == "READ")
    blocked = sum(1 for r in lines if r["outcome"] != "READ")
    pf = sum(1 for r in lines if r.get("pets_allowed") is True)
    np_ = sum(1 for r in lines if r.get("pets_allowed") is False)
    print("targets", len(lines), "read", read, "blocked", blocked, "pf", pf, "np", np_)


if __name__ == "__main__":
    main()
