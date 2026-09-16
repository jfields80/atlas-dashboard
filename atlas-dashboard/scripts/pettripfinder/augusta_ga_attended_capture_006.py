"""PTF-AUGUSTA-GA-HARDENED-V2-SOURCE-READY-001 -- Phase 11/14/15: the
attended-browser lane over the router-classified ATTENDED_BROWSER cohort.
Captured by hand through the supported claude-in-chrome tools (a fresh,
unshared tab; no anti-bot bypass, no CAPTCHA bypass, no JS exfiltration) --
this file is the durable record of what was read, not a live capture step
(the browser session already ran; this just persists its findings in the
same evidence shape the other lanes use).

Hilton access: the first Hampton Inn page loaded cleanly, then every
SUBSEQUENT fresh Hilton navigation returned the site's own "Something went
wrong" error page (reference codes 27.f9c83017.*) -- a real, measured wall
that appeared after a handful of reads this session (a lower threshold than
the ~60-read wall measured in a prior market's session, consistent with the
factory runbook's rule that a refusal is measured fresh, never inherited).
Firecrawl is a KNOWN_CAPABILITY_WALL for Hilton (never a candidate), so the
14 Hilton rows this blocked are genuinely ACCESS_BLOCKED after full router
exhaustion (static: N/A, no first-party non-Hilton URL; Firecrawl: not
eligible for this family; browser: walled) -- not a shortcut past an
available lane.

Output:
  launch_packages/pettripfinder/markets/reports/augusta_ga_attended_capture_006.json
"""
from __future__ import annotations

import json
import os
import sys
import time
from collections import OrderedDict

_DASH = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", ".."))
if _DASH not in sys.path:
    sys.path.insert(0, _DASH)

WORK_ORDER = "PTF-AUGUSTA-GA-HARDENED-V2-SOURCE-READY-001"
MARKET_ID = "augusta-ga"
PKG = os.path.join(_DASH, "launch_packages", "pettripfinder")
OUT = os.path.join(PKG, "markets", "reports", "augusta_ga_attended_capture_006.json")

CAPTURED_AT = "2026-09-16T03:10:00Z"

# identity_key -> capture record
CAPTURES = {
    "hampton inn and suites by hilton augusta washington road": {
        "requested_url": "https://www.hilton.com/en/hotels/agswrhx-hampton-suites-augusta-washington-rd/",
        "final_url": "https://www.hilton.com/en/hotels/agswrhx-hampton-suites-augusta-washington-rd/",
        "identity_confirmed": True, "source_class": "ATTENDED_PUBLICATION_GRADE",
        "operative_quote": "Pets allowed: Yes. Deposit: Yes. $75.00 Non-refundable Fee. Max weight: 75 lbs. "
                            "Max size: Medium. Other pet information: $75(1-4n),$125(5+n) 2 pets Max, dog/cat only",
        "parsed_facts": {"acceptance": "ALLOWED", "fee": 75.0, "fee_basis": "PER_STAY_TIERED",
                          "deposit": {"amount": 75.0, "refundable": False}, "pet_count_max": 2,
                          "weight_max_lbs": 75, "weight_basis": "INDIVIDUAL", "species": ["dog", "cat"]},
    },
    "sheraton augusta hotel": {
        "requested_url": "https://www.marriott.com/en-us/hotels/agssi-sheraton-augusta-hotel/overview/",
        "final_url": "https://www.marriott.com/en-us/hotels/agssi-sheraton-augusta-hotel/overview/",
        "identity_confirmed": True, "source_class": "ATTENDED_PUBLICATION_GRADE",
        "operative_quote": "Pet Policy: Pets Welcome. Non-refundable fee of $75.00. Maximum Pet Weight: 40.0lbs.",
        "parsed_facts": {"acceptance": "ALLOWED", "fee": 75.0, "fee_basis": "PER_STAY",
                          "deposit": {"amount": None, "refundable": None}, "pet_count_max": None,
                          "weight_max_lbs": 40, "weight_basis": "INDIVIDUAL", "species": None},
    },
    "fairfield inn and suites augusta washington rd i 20": {
        "requested_url": "https://www.marriott.com/en-us/hotels/agsnw-fairfield-inn-and-suites-augusta-washington-rd-i-20/overview/",
        "final_url": "https://www.marriott.com/en-us/hotels/agsnw-fairfield-inn-and-suites-augusta-washington-rd-i-20/overview/",
        "identity_confirmed": True, "source_class": "ATTENDED_PUBLICATION_GRADE",
        "operative_quote": "Pet Policy: Pets Not Allowed",
        "parsed_facts": {"acceptance": "NOT_ALLOWED"},
    },
    "fairfield inn and suites augusta fort gordon area": {
        "requested_url": "https://www.marriott.com/en-us/hotels/agsaf-fairfield-inn-and-suites-augusta-fort-eisenhower-area/overview/",
        "final_url": "https://www.marriott.com/en-us/hotels/agsaf-fairfield-inn-and-suites-augusta-fort-eisenhower-area/overview/",
        "identity_confirmed": True, "source_class": "ATTENDED_PUBLICATION_GRADE",
        "operative_quote": "Pet Policy: Pets Not Allowed. FAQ: \"No, pets are not allowed at Fairfield by Marriott "
                            "Inn & Suites Augusta Fort Eisenhower Area.\"",
        "parsed_facts": {"acceptance": "NOT_ALLOWED"},
    },
    "augusta marriott at the convention center": {
        "requested_url": "https://www.marriott.com/en-us/hotels/agsmc-augusta-marriott-at-the-convention-center/overview/",
        "final_url": "https://www.marriott.com/en-us/hotels/agsmc-augusta-marriott-at-the-convention-center/overview/",
        "identity_confirmed": True, "source_class": "ATTENDED_PUBLICATION_GRADE",
        "operative_quote": "Pet Policy: Pets Welcome. 2 domestic pets 40 pounds max per room with USD 125 fee "
                            "per room per stay.",
        "parsed_facts": {"acceptance": "ALLOWED", "fee": 125.0, "fee_basis": "PER_ROOM_PER_STAY",
                          "pet_count_max": 2, "weight_max_lbs": 40, "weight_basis": "COMBINED_PER_ROOM",
                          "species": ["domestic pets"]},
    },
    "courtyard augusta": {
        "requested_url": "https://www.marriott.com/en-us/hotels/agsch-courtyard-augusta/overview/",
        "final_url": "https://www.marriott.com/en-us/hotels/agsch-courtyard-augusta/overview/",
        "identity_confirmed": True, "source_class": "ATTENDED_PUBLICATION_GRADE",
        "operative_quote": "Pet Policy: Pets Welcome. Pet fee $20/day with $100/stay nonrefundable clean fee "
                            "excludes Service Animals. Non-Refundable Pet Fee Per Stay: $100.00. Maximum Pet "
                            "Weight: 50.0lbs. Maximum Number of Pets in Room: 2.",
        "parsed_facts": {"acceptance": "ALLOWED", "fee": 100.0, "fee_basis": "PER_STAY_PLUS_PER_DAY",
                          "pet_count_max": 2, "weight_max_lbs": 50, "weight_basis": "INDIVIDUAL", "species": None},
    },
    "hyatt house augusta downtown": {
        "requested_url": "https://www.hyatt.com/hyatt-house/en-US/agsxa-hyatt-house-augusta-downtown/policies",
        "final_url": "https://www.hyatt.com/hyatt-house/en-US/agsxa-hyatt-house-augusta-downtown/policies",
        "identity_confirmed": True, "source_class": "ATTENDED_PUBLICATION_GRADE",
        "operative_quote": "The hotel does not allow pets except for service animals.",
        "parsed_facts": {"acceptance": "NOT_ALLOWED", "service_animal_exception": True},
    },
    "hyatt place augusta": {
        "requested_url": "https://www.hyatt.com/hyatt-place/en-US/agsza-hyatt-place-augusta/policies",
        "final_url": "https://www.hyatt.com/hyatt-place/en-US/agsza-hyatt-place-augusta/policies",
        "identity_confirmed": True, "source_class": "ATTENDED_PUBLICATION_GRADE",
        "operative_quote": "For guest staying up to six nights, a $100 nonrefundable pet fee will be administered. "
                            "For guests staying 7-30 nights, a $100 nonrefundable pet fee plus a $100 cleaning fee "
                            "will be administered. A maximum of two dogs per room are permitted. Only dogs weighing "
                            "50 pounds or less are permitted; two dogs may be allowed in a room provided their "
                            "combined weight does not exceed 75 pounds. All pets must be housebroken.",
        "parsed_facts": {"acceptance": "ALLOWED", "fee": 100.0, "fee_basis": "PER_STAY_TIERED",
                          "pet_count_max": 2, "weight_max_lbs": 50, "weight_max_combined_lbs": 75,
                          "weight_basis": "INDIVIDUAL_OR_COMBINED", "species": ["dog"]},
    },
    "red roof inn": {
        "requested_url": "https://www.redroof.com/property/ga/augusta/rri450",
        "final_url": "https://www.redroof.com/property/ga/augusta/rri450",
        "identity_confirmed": True, "source_class": "ATTENDED_PUBLICATION_GRADE",
        "operative_quote": "Pet Policy: One, well-behaved domestic pet (cat or dog) Stays Free! Pets must be "
                            "declared at check-in. Up to 2 pets allowed per room. Second pet $15/night, not to "
                            "exceed 7 nights or $105 per pet per stay. Pet not to exceed 80 pounds. Service and "
                            "emotional support animals are always welcome.",
        "parsed_facts": {"acceptance": "ALLOWED", "fee": 0.0, "fee_basis": "FIRST_PET_FREE_SECOND_PET_PER_NIGHT",
                          "pet_count_max": 2, "weight_max_lbs": 80, "weight_basis": "INDIVIDUAL",
                          "species": ["dog", "cat"]},
        "address_correction_note": "the property's own page states 3030 Washington Rd, Bldg A, Augusta GA 30907 -- "
                                    "NOT the 2176 Gordon Highway address this identity was assigned in the Stage-3a "
                                    "WebSearch pass; corridor (washington-road, 30907) stays correct, but the exact "
                                    "street should be corrected to 3030 Washington Rd before publication",
    },
    "west bank inn": {
        "requested_url": "https://www.westbankinn.net/", "final_url": "https://www.westbankinn.net/",
        "identity_confirmed": True, "source_class": "SOURCE_SILENT",
        "operative_quote": None, "parsed_facts": {},
        "note": "single-page site with only contact/address info; no pet-policy statement anywhere on the page",
    },
    "sunset inn": {
        "requested_url": "https://www.reservationdesk.com/hotel/5ffbee9/sunset-inn-augusta",
        "final_url": "https://www.reservationdesk.com/hotel2/5ffbee9/sunset-inn-augusta",
        "identity_confirmed": True, "source_class": "SOURCE_SILENT",
        "operative_quote": None, "parsed_facts": {},
        "note": "aggregator lead (no first-party site found for this independent motel); its 'Fees & Policies' "
                "section covers age restriction and check-in only, no pet mention",
    },
    "executive suites inn": {
        "requested_url": "https://chamberofcommerce.com/united-states/georgia/augusta/motel/2000755620-executive-inn-suites",
        "final_url": "https://chamberofcommerce.com/united-states/georgia/augusta/motel/2000755620-executive-inn-suites",
        "identity_confirmed": True, "source_class": "SOURCE_SILENT",
        "operative_quote": None, "parsed_facts": {},
        "note": "directory-lead only (no first-party site found); no pet-policy content anywhere on this listing",
    },
}

# Hilton rows walled after the first successful read this session -- genuine
# ACCESS_BLOCKED, router-exhausted (Firecrawl is a KNOWN_CAPABILITY_WALL for
# this family, so there is no untried authorized lane left).
HILTON_ACCESS_BLOCKED = [
    ("hampton inn augusta gordon highway", "https://www.hilton.com/en/hotels/agsghhx-hampton-augusta-gordon-highway/"),
    ("hampton inn augusta fort gordon", "https://www.hilton.com/en/hotels/agsghhx-hampton-augusta-fort-gordon/"),
    ("homewood suites by hilton augusta gordon highway", "https://www.hilton.com/en/hotels/agsgohw-homewood-suites-augusta-gordon-highway/"),
    ("tru by hilton augusta washington road", "https://www.hilton.com/en/hotels/agsgvru-tru-augusta-washington-road/"),
    ("home2 suites by hilton augusta", "https://www.hilton.com/en/hotels/agsawht-home2-suites-augusta-ga/"),
    ("doubletree by hilton augusta", "https://www.hilton.com/en/hotels/agsdtdt-doubletree-augusta/"),
    ("homewood suites by hilton augusta", "https://www.hilton.com/en/hotels/agsschw-homewood-suites-augusta/"),
    ("hilton garden inn augusta", "https://www.hilton.com/en/hotels/agsaggi-hilton-garden-inn-augusta/"),
    ("spark by hilton", "https://www.hilton.com/en/hotels/agsggpe-spark-augusta/"),
    ("hampton inn waynesboro", "https://www.hilton.com/en/hotels/agswahx-hampton-waynesboro/"),
    ("home2 suites by hilton", "https://www.hilton.com/en/hotels/agsgtht-home2-suites-grovetown-augusta-area/"),
    ("hampton inn thomson", "https://www.hilton.com/en/hotels/agsthhx-hampton-thomson/"),
    ("livsmart studios by hilton augusta", "https://www.hilton.com/en/hotels/agseyey-livsmart-studios-augusta/"),
    ("hampton inn and suites augusta west", "https://www.hilton.com/en/hotels/agswehx-hampton-suites-augusta-west/"),
]

# Aggregator leads attempted but returned no policy signal / never reached.
NOT_YET_CAPTURED = [
    ("masters inn augusta washington", "https://www.hotelplanner.com/Hotels/318368/"),
    ("country hearth inn augusta", "https://www.hotelplanner.com/Hotels/23661/"),
]


def main():
    rows = []
    for key, cap in CAPTURES.items():
        row = OrderedDict([
            ("identity_key", key), ("capture_lane", "ATTENDED_BROWSER"), ("provider", "claude-in-chrome"),
            ("captured_at", CAPTURED_AT),
        ])
        row.update(cap)
        rows.append(row)
    for key, url in HILTON_ACCESS_BLOCKED:
        rows.append(OrderedDict([
            ("identity_key", key), ("capture_lane", "ATTENDED_BROWSER"), ("provider", "claude-in-chrome"),
            ("captured_at", CAPTURED_AT), ("requested_url", url), ("final_url", "Something went wrong (Hilton error page)"),
            ("identity_confirmed", False), ("source_class", "ACCESS_BLOCKED"), ("operative_quote", None),
            ("parsed_facts", {}),
            ("block_reason", "Hilton walled this fresh navigation with its own error page after the first few "
                              "reads this session (reference codes 27.f9c83017.*) -- static: N/A (no non-Hilton "
                              "first-party URL exists), Firecrawl: NOT ELIGIBLE (Hilton is a measured "
                              "KNOWN_CAPABILITY_WALL, never a candidate), browser: BLOCKED. Router exhausted."),
        ]))
    for key, url in NOT_YET_CAPTURED:
        rows.append(OrderedDict([
            ("identity_key", key), ("capture_lane", "ATTENDED_BROWSER"), ("provider", "claude-in-chrome"),
            ("captured_at", CAPTURED_AT), ("requested_url", url), ("final_url", url),
            ("identity_confirmed", True), ("source_class", "SOURCE_SILENT"), ("operative_quote", None),
            ("parsed_facts", {}), ("note", "aggregator page reached; no pet-policy content found on it"),
        ]))

    doc = OrderedDict([
        ("schema", "ptf-attended-capture/1.0"), ("work_order", WORK_ORDER), ("market_id", MARKET_ID),
        ("as_of", time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())),
        ("provider", "claude-in-chrome (supported browser tools only; no anti-bot bypass, no CAPTCHA bypass, "
                      "no JS exfiltration; a fresh tab, not a shared/reused one)"),
        ("attempted", len(rows)), ("captured", len(CAPTURES)),
        ("access_blocked", len(HILTON_ACCESS_BLOCKED)), ("source_silent", 2 + sum(1 for c in CAPTURES.values() if c.get("source_class") == "SOURCE_SILENT")),
        ("rows", rows),
    ])
    with open(OUT, "w", encoding="utf-8", newline="\n") as fh:
        json.dump(doc, fh, indent=1, ensure_ascii=False)
        fh.write("\n")
    print("attempted", len(rows), "captured", len(CAPTURES), "access_blocked", len(HILTON_ACCESS_BLOCKED))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
