"""PTF-LOUISVILLE-ATTENDED-CAPTURE-PASS4-001 -- compile the 11-row queue.

Attended Claude-in-Chrome capture of the existing 11-row manual capture
queue (Red Roof x2, Studio 6 x1, Wyndham x5, IHG x3). Does not write policy
authority or founder approvals.

    python -m scripts.pettripfinder.compile_louisville_pass4_capture
"""
from __future__ import annotations

import hashlib
import json
from collections import OrderedDict
from pathlib import Path

from scripts.pettripfinder.census_partition_builder import write_json
from scripts.pettripfinder.contracts import census, enums, partition

REPO = Path(__file__).resolve().parents[2]
PKG = REPO / "launch_packages" / "pettripfinder"
ART = REPO / "data" / "operator_evidence" / "louisville-pass4-capture-001"
RAW = ART / "raw"
QUEUE = PKG / "markets" / "reports" / "louisville_manual_capture_queue_001.json"
RESULTS = PKG / "markets" / "reports" / "louisville_attended_capture_pass4_001.json"
PACKET = (PKG / "markets" / "reports"
          / "louisville_attended_capture_pass4_founder_review_packet.json")
CENSUS = PKG / "identity_census" / "louisville-ky.json"
PARTITION = PKG / "louisville_final_partition_001.json"
WORK = "PTF-LOUISVILLE-ATTENDED-CAPTURE-PASS4-001"
AS_OF = "2026-08-17"

BATCH = [
    "red roof inn louisville expo airport",
    "red roof inn louisville hurstbourne",
    "studio 6 louisville airport expo center",
    "baymont by wyndham louisville airport south",
    "hawthorn suites by wyndham louisville east",
    "travelodge by wyndham sellersburg louisville north",
    "super 8 by wyndham louisville airport",
    "la quinta inn and suites by wyndham louisville northeast old henry",
    "holiday inn express and suites jeffersonville",
    "staybridge suites louisville east",
    "candlewood suites louisville airport",
]

VALID_OUTCOMES = frozenset({
    "PUBLICATION_CANDIDATE", "VERIFIED_NO_PETS_CANDIDATE", "POLICY_NOT_FOUND",
    "IDENTITY_UNCERTAIN", "ACCESS_BLOCKED", "CAPTURE_FAILED",
    "SOURCE_AMBIGUOUS",
})


def _sha(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="replace")


def _assert_in(blob: str, needle: str, label: str) -> None:
    if needle not in blob:
        raise SystemExit("%s missing %r" % (label, needle))


def _artifact(relname: str) -> OrderedDict:
    path = RAW / relname
    return OrderedDict((
        ("relpath", "raw/%s" % relname),
        ("sha256", _sha(path)),
        ("bytes", path.stat().st_size),
    ))


def _row(decision_id, hotel, key, brand, queued_url, final_url,
         identity_signals, outcome, artifacts, quotes, proposed_facts,
         withheld_fields, notes, recommended):
    if outcome not in VALID_OUTCOMES:
        raise SystemExit("bad outcome %s for %s" % (outcome, hotel))
    return OrderedDict((
        ("decision_id", decision_id),
        ("hotel", hotel),
        ("identity_key", key),
        ("brand", brand),
        ("queued_url", queued_url),
        ("final_url", final_url),
        ("identity_binding", "BOUND"),
        ("identity_signals", identity_signals),
        ("outcome", outcome),
        ("source_grade", enums.GRADE_PT1_FIRST_PARTY),
        ("artifacts", artifacts),
        ("quotes", quotes),
        ("proposed_facts", proposed_facts),
        ("withheld_fields", withheld_fields),
        ("notes", notes),
        ("recommended_founder_decision", recommended),
    ))


def main() -> None:
    queue_doc = json.loads(QUEUE.read_text(encoding="utf-8-sig"))
    if queue_doc["count"] != 11 or len(queue_doc["items"]) != 11:
        raise SystemExit("queue is not exactly 11 rows")
    queue_keys = [r["identity_key"] for r in queue_doc["items"]]
    if queue_keys != BATCH:
        raise SystemExit("batch does not match queue order")
    if len(set(queue_keys)) != 11:
        raise SystemExit("duplicate identity_key in queue")

    census_doc = json.loads(CENSUS.read_text(encoding="utf-8-sig"))
    hotels = {h["identity_key"]: h for h in census_doc["hotels"]}
    for key in BATCH:
        if key not in hotels:
            raise SystemExit("missing census row %s" % key)

    # -- Red Roof -----------------------------------------------------
    rr118_pol = _artifact("red-roof-inn-louisville-expo-airport__policy.txt")
    rr118_pol_img = _artifact("red-roof-inn-louisville-expo-airport__policy.png")
    rr118_id_img = _artifact("red-roof-inn-louisville-expo-airport__identity.png")
    rr118_txt = _text(RAW / "red-roof-inn-louisville-expo-airport__policy.txt")
    rr118_quote = (
        "One, well-behaved domestic pet (cat or dog) Stays Free! Pets must "
        "be declared at check-in. Up to 2 pets allowed per room. Second pet "
        "$15/ night, not to exceed 7 nights or $105 per pet per stay. Pet "
        "not to exceed 80 pounds. Service and emotional support animals are "
        "always welcome."
    )
    _assert_in(rr118_txt, rr118_quote, "rri118")

    rr034_pol = _artifact("red-roof-inn-louisville-hurstbourne__policy.txt")
    rr034_pol_img = _artifact("red-roof-inn-louisville-hurstbourne__policy.png")
    rr034_id_img = _artifact("red-roof-inn-louisville-hurstbourne__identity.png")
    rr034_txt = _text(RAW / "red-roof-inn-louisville-hurstbourne__policy.txt")
    _assert_in(rr034_txt, rr118_quote, "rri034")

    # -- Studio 6 -------------------------------------------------------
    s6_pol = _artifact("studio-6-louisville-airport-expo-center__amenities.txt")
    s6_img = _artifact("studio-6-louisville-airport-expo-center__amenities.png")
    s6_txt = _text(RAW / "studio-6-louisville-airport-expo-center__amenities.txt")
    _assert_in(s6_txt, "Pets Allowed", "studio6")
    _assert_in(s6_txt, "Pet Friendly", "studio6")

    # -- Wyndham ----------------------------------------------------------
    bay_pol = _artifact("baymont-by-wyndham-louisville-airport-south__policy.txt")
    bay_txt = _text(RAW / "baymont-by-wyndham-louisville-airport-south__policy.txt")
    bay_quote = (
        "Dogs only please.Two dogs up to 25 lbs are allowed for a "
        "non-refundable charge of $20 plus tax per pet per night with a "
        "$100 refundable deposit. ADA defined service animals are also "
        "welcome at this hotel."
    )
    _assert_in(bay_txt, bay_quote, "baymont")

    haw_pol = _artifact("hawthorn-suites-by-wyndham-louisville-east__policy.txt")
    haw_txt = _text(RAW / "hawthorn-suites-by-wyndham-louisville-east__policy.txt")
    haw_quote = (
        "Service Animals - ADA-defined service animals welcome. / Pets "
        "Allowed - 2 pets max. Dogs and cats only. 75lbs or less per pet. "
        "/ Fees – 75USD per stay for 1–4 nights. 125USD per stay "
        "5+ nights. 25USD per additional pet. / Other information - "
        "Contact hotel for additional details and availability."
    )
    _assert_in(haw_txt, haw_quote, "hawthorn")

    trav_pol = _artifact(
        "travelodge-by-wyndham-sellersburg-louisville-north__policy.txt")
    trav_txt = _text(
        RAW / "travelodge-by-wyndham-sellersburg-louisville-north__policy.txt")
    trav_quote = (
        "Dogs and birds are allowed for a non-refundable charge of 20.00 "
        "USD per night. 1 pet maximum. Sorry no cats allowed. Pet "
        "Sanitation Fee is 150 USD if applicable. ADA defined service "
        "animals are welcome at this hotel."
    )
    _assert_in(trav_txt, trav_quote, "travelodge")

    s8_pol = _artifact("super-8-by-wyndham-louisville-airport__policy.txt")
    s8_txt = _text(RAW / "super-8-by-wyndham-louisville-airport__policy.txt")
    s8_quote = (
        "Maximum of 2 pets with a max weight of 50 lbs per room at a "
        "nonrefundable charge of 25USD per pet per night. Pet Sanitation "
        "fee of 150.00 USD applies if applicable. ADA defined service "
        "animals are welcome at this hotel."
    )
    _assert_in(s8_txt, s8_quote, "super8")

    lq_pol = _artifact(
        "la-quinta-inn-and-suites-by-wyndham-louisville-northeast-old-henry"
        "__policy.txt")
    lq_txt = _text(
        RAW / ("la-quinta-inn-and-suites-by-wyndham-louisville-northeast-"
               "old-henry__policy.txt"))
    lq_quote = (
        "Service Animals - ADA-defined service animals are welcome free of "
        "charge. / Pets Allowed - 2 pets max. Cats and dogs only. 75lbs or "
        "less per pet. / Fees - Non-refundable 25 USD nightly for up to 2 "
        "pets. Max 75 USD per stay. / Other Information - Contact hotel "
        "for additional details and availability."
    )
    _assert_in(lq_txt, lq_quote, "laquinta")

    # -- IHG ----------------------------------------------------------
    hie_faq = _artifact("holiday-inn-express-and-suites-jeffersonville__faq.txt")
    hie_img = _artifact("holiday-inn-express-and-suites-jeffersonville__faq.jpg")
    hie_txt = _text(
        RAW / "holiday-inn-express-and-suites-jeffersonville__faq.txt")
    hie_quote = (
        "No, pets are not allowed at Holiday Inn Express & Suites "
        "Louisville N - Jeffersonville."
    )
    _assert_in(hie_txt, hie_quote, "hie")

    sb_faq = _artifact("staybridge-suites-louisville-east__faq.txt")
    sb_img = _artifact("staybridge-suites-louisville-east__faq.jpg")
    sb_txt = _text(RAW / "staybridge-suites-louisville-east__faq.txt")
    sb_quote = (
        "Pets are welcome at Staybridge Suites Louisville-East. There is a "
        "pet deposit per stay of 75 USD . Our Pet Policy: Pets allowed "
        "with a non refundable fee of 75 plus tax for 1 to 6 nights and "
        "for 7 plus nights it is 150 plus tax. Pets must be registered "
        "upon check in."
    )
    _assert_in(sb_txt, sb_quote, "staybridge")

    cw_faq = _artifact("candlewood-suites-louisville-airport__faq.txt")
    cw_img = _artifact("candlewood-suites-louisville-airport__faq.jpg")
    cw_txt = _text(RAW / "candlewood-suites-louisville-airport__faq.txt")
    cw_quote = (
        "Pets are welcome with a nonrefundable fee The charge is 30 USD "
        "per pet per night For stays of 7 nights or more a flat fee of "
        "150 USD per pet applies A pet agreement is required at check in"
    )
    _assert_in(cw_txt, cw_quote, "candlewood")

    rows = [
        _row(
            "LVL-P4-001", "Red Roof Inn Louisville Expo Airport",
            "red roof inn louisville expo airport", "RED_ROOF",
            "https://www.redroof.com/property/ky/louisville/rri118",
            "https://www.redroof.com/property/ky/louisville/rri118",
            ["Red Roof Inn Louisville Expo Airport", "4704 Preston Hwy",
             "Louisville KY 40213", "property code rri118 in URL"],
            "PUBLICATION_CANDIDATE",
            [rr118_pol, rr118_pol_img, rr118_id_img],
            [rr118_quote],
            OrderedDict((
                ("pets_allowed", True),
                ("species", ["cat", "dog"]),
                ("max_pets_per_room", 2),
                ("first_pet_fee_cents", 0),
                ("second_pet_fee_cents_per_night", 1500),
                ("second_pet_fee_cap_nights", 7),
                ("second_pet_fee_cap_cents_per_stay", 10500),
                ("weight_limit_lbs", 80),
                ("weight_limit_scope", "individual"),
                ("deposit_cents", 5000),
                ("deposit_refundable", True),
                ("service_animals_note",
                 "Service and emotional support animals are always "
                 "welcome (source conflates ADA service animals and "
                 "ESAs; preserved verbatim, not adjudicated)"),
            )),
            OrderedDict(),
            "Attended capture succeeded (Pass 3 was ACCESS_BLOCKED). "
            "Full Hotel Policies block rendered on first navigation.",
            "APPROVE_AFFIRMATIVE_STRUCTURED",
        ),
        _row(
            "LVL-P4-002", "Red Roof Inn Louisville Hurstbourne",
            "red roof inn louisville hurstbourne", "RED_ROOF",
            "https://www.redroof.com/property/ky/louisville/rri034",
            "https://www.redroof.com/property/ky/louisville/rri034",
            ["Red Roof Inn Louisville East - Hurstbourne",
             "9330 Blairwood Rd", "Hurstbourne KY 40222",
             "property code rri034 in URL"],
            "PUBLICATION_CANDIDATE",
            [rr034_pol, rr034_pol_img, rr034_id_img],
            [rr118_quote],
            OrderedDict((
                ("pets_allowed", True),
                ("species", ["cat", "dog"]),
                ("max_pets_per_room", 2),
                ("first_pet_fee_cents", 0),
                ("second_pet_fee_cents_per_night", 1500),
                ("second_pet_fee_cap_nights", 7),
                ("second_pet_fee_cap_cents_per_stay", 10500),
                ("weight_limit_lbs", 80),
                ("weight_limit_scope", "individual"),
                ("deposit_cents", 5000),
                ("deposit_refundable", True),
                ("service_animals_note",
                 "Service and emotional support animals are always "
                 "welcome (source conflates ADA service animals and "
                 "ESAs; preserved verbatim, not adjudicated)"),
            )),
            OrderedDict(),
            "Attended capture succeeded (Pass 3 was ACCESS_BLOCKED). "
            "Identical fee schedule to rri118 (same chain-level Red Roof "
            "pet policy, independently confirmed on this property page, "
            "not inherited).  Display name on-page is 'Louisville East - "
            "Hurstbourne'; identity is bound by URL property code rri034.",
            "APPROVE_AFFIRMATIVE_STRUCTURED",
        ),
        _row(
            "LVL-P4-003", "Studio 6 Louisville Airport Expo Center",
            "studio 6 louisville airport expo center", "STUDIO6",
            "https://www.studio6.com/property/motel-louisville-kentucky-us-294003/",
            "https://www.studio6.com/property/motel-louisville-kentucky-us-294003/",
            ["Studio 6 Suites Louisville, KY - Airport Expo Center",
             "571 Phillips Lane", "phone 5023615008"],
            "PUBLICATION_CANDIDATE",
            [s6_pol, s6_img],
            [],
            OrderedDict((
                ("pets_allowed", True),
            )),
            OrderedDict((
                ("species", "SOURCE_SILENT -- amenities list shows only "
                 "'Pets Allowed'/'Pet Friendly' icons, no species text"),
                ("fee", "SOURCE_SILENT on this property page"),
                ("weight_limit", "SOURCE_SILENT on this property page"),
                ("max_pets", "SOURCE_SILENT on this property page"),
            )),
            "Pass 3 timeout (0 bytes) did not reproduce; page loaded "
            "normally this session. Property-bound identity confirmed "
            "(address + phone match census). Amenities list is property-"
            "bound but carries no fee/weight/species specificity. A "
            "brand-level 'Pets Stay Free Details' footer link exists but "
            "is NOT property-bound and was withheld per contract.",
            "HOLD_PARTIAL_AFFIRMATIVE",
        ),
        _row(
            "LVL-P4-004", "Baymont by Wyndham Louisville Airport South",
            "baymont by wyndham louisville airport south", "WYNDHAM",
            "https://www.wyndhamhotels.com/baymont/louisville-kentucky/"
            "baymont-inn-louisville-airport-south/overview",
            "https://www.wyndhamhotels.com/baymont/louisville-kentucky/"
            "baymont-inn-louisville-airport-south/overview",
            ["Baymont by Wyndham Louisville Airport South",
             "6515 Signature Drive", "Louisville, Kentucky 40213",
             "+1-502-968-4100"],
            "PUBLICATION_CANDIDATE",
            [bay_pol],
            [bay_quote],
            OrderedDict((
                ("pets_allowed", True),
                ("species", ["dog"]),
                ("max_pets_per_room", 2),
                ("weight_limit_lbs", 25),
                ("weight_limit_scope", "individual"),
                ("fee_cents_per_pet_per_night", 2000),
                ("fee_refundable", False),
                ("fee_scope", "plus tax"),
                ("deposit_cents", 10000),
                ("deposit_refundable", True),
            )),
            OrderedDict(),
            "Static HTML slot was empty in Pass 3 (JS-hydrated). This "
            "session, the hydrated Pet & Service Animal Policy node was "
            "read directly from the live DOM after opening 'Hotel "
            "Policies'.",
            "APPROVE_AFFIRMATIVE_STRUCTURED",
        ),
        _row(
            "LVL-P4-005", "Hawthorn Suites by Wyndham Louisville East",
            "hawthorn suites by wyndham louisville east", "WYNDHAM",
            "https://www.wyndhamhotels.com/hawthorn-extended-stay/"
            "louisville-kentucky/hawthorn-suites-by-wyndham-louisville-east/"
            "overview",
            "https://www.wyndhamhotels.com/hawthorn-extended-stay/"
            "louisville-kentucky/hawthorn-suites-by-wyndham-louisville-east/"
            "overview",
            ["Hawthorn Suites by Wyndham Louisville East",
             "751 Cypress Station Drive", "Louisville, Kentucky 40207",
             "+1-502-785-0823"],
            "PUBLICATION_CANDIDATE",
            [haw_pol],
            [haw_quote],
            OrderedDict((
                ("pets_allowed", True),
                ("species", ["dog", "cat"]),
                ("max_pets_per_room", 2),
                ("weight_limit_lbs", 75),
                ("weight_limit_scope", "individual"),
                ("fee_cents_per_stay_1_to_4_nights", 7500),
                ("fee_cents_per_stay_5_plus_nights", 12500),
                ("additional_pet_fee_cents", 2500),
            )),
            OrderedDict((
                ("fee_refundable", "SOURCE_SILENT -- refundability not "
                 "stated for this stay-based fee schedule"),
            )),
            "Static HTML slot was empty in Pass 3 (JS-hydrated). Read "
            "directly from the live hydrated DOM this session.",
            "APPROVE_AFFIRMATIVE_STRUCTURED",
        ),
        _row(
            "LVL-P4-006",
            "Travelodge by Wyndham Sellersburg Louisville North",
            "travelodge by wyndham sellersburg louisville north", "WYNDHAM",
            "https://www.wyndhamhotels.com/travelodge/sellersburg-indiana/"
            "travelodge-sellersburg-louisville-north/overview",
            "https://www.wyndhamhotels.com/travelodge/sellersburg-indiana/"
            "travelodge-sellersburg-louisville-north/overview",
            ["Travelodge by Wyndham Sellersburg / Louisville North",
             "7618 Old State Road 60", "Sellersburg, Indiana 47172",
             "+1-812-246-4451"],
            "PUBLICATION_CANDIDATE",
            [trav_pol],
            [trav_quote],
            OrderedDict((
                ("pets_allowed", True),
                ("species", ["dog", "bird"]),
                ("species_excluded", ["cat"]),
                ("max_pets_per_room", 1),
                ("fee_cents_per_pet_per_night", 2000),
                ("fee_refundable", False),
                ("conditional_sanitation_fee_cents", 15000),
                ("conditional_sanitation_fee_condition", "if applicable"),
            )),
            OrderedDict((
                ("weight_limit", "SOURCE_SILENT"),
            )),
            "Unusual species scope: dogs and birds explicitly allowed, "
            "cats explicitly excluded ('Sorry no cats allowed'). Preserved "
            "verbatim rather than normalized to a generic dog/cat pattern.",
            "APPROVE_AFFIRMATIVE_STRUCTURED",
        ),
        _row(
            "LVL-P4-007", "Super 8 by Wyndham Louisville Airport",
            "super 8 by wyndham louisville airport", "WYNDHAM",
            "https://www.wyndhamhotels.com/super-8/louisville-kentucky/"
            "super-8-louisville-airport/overview",
            "https://www.wyndhamhotels.com/super-8/louisville-kentucky/"
            "super-8-louisville-airport/overview",
            ["Super 8 by Wyndham Louisville Airport",
             "4800 Preston Highway", "Louisville, Kentucky 40213-2226"],
            "PUBLICATION_CANDIDATE",
            [s8_pol],
            [s8_quote],
            OrderedDict((
                ("pets_allowed", True),
                ("max_pets_per_room", 2),
                ("weight_limit_lbs", 50),
                ("fee_cents_per_pet_per_night", 2500),
                ("fee_refundable", False),
                ("conditional_sanitation_fee_cents", 15000),
                ("conditional_sanitation_fee_condition", "if applicable"),
            )),
            OrderedDict((
                ("species", "GENERIC 'pets' only -- source does not name "
                 "dogs/cats explicitly, per contract generic pets is not "
                 "treated as dog+cat"),
                ("weight_limit_scope", "AMBIGUOUS -- source reads 'max "
                 "weight of 50 lbs per room' which could mean combined "
                 "across up to 2 pets or per individual pet; preserved "
                 "verbatim, not resolved"),
            )),
            "Static HTML slot was empty in Pass 3 (JS-hydrated). Read "
            "directly from the live hydrated DOM this session.",
            "HOLD_PARTIAL_AFFIRMATIVE",
        ),
        _row(
            "LVL-P4-008",
            "La Quinta Inn and Suites by Wyndham Louisville Northeast "
            "Old Henry",
            "la quinta inn and suites by wyndham louisville northeast old "
            "henry", "WYNDHAM",
            "https://www.wyndhamhotels.com/laquinta/louisville-kentucky/"
            "la-quinta-inn-and-suites-louisville-ne-old-henry-rd/overview",
            "https://www.wyndhamhotels.com/laquinta/louisville-kentucky/"
            "la-quinta-inn-and-suites-louisville-ne-old-henry-rd/overview",
            ["La Quinta Inn & Suites by Wyndham Louisville NE/Old Henry Rd",
             "13825 Terra View Trl", "Louisville, Kentucky 40245",
             "+1-502-208-5205"],
            "PUBLICATION_CANDIDATE",
            [lq_pol],
            [lq_quote],
            OrderedDict((
                ("pets_allowed", True),
                ("species", ["cat", "dog"]),
                ("max_pets_per_room", 2),
                ("weight_limit_lbs", 75),
                ("weight_limit_scope", "individual"),
                ("fee_cents_per_pet_per_night", 2500),
                ("fee_refundable", False),
                ("fee_cap_cents_per_stay", 7500),
            )),
            OrderedDict(),
            "Uses the corrected Old Henry Rd property URL from "
            "PTF-LOUISVILLE-BRAND-SURFACE-REPAIR-001 (not the prepared "
            "la-quinta-louisville-east URL, a different property). Census "
            "phone 502-919-7910 vs on-page +1-502-208-5205 remains a "
            "known, pre-existing discrepancy (documented in Pass 3); "
            "address/name/property binding is otherwise exact.",
            "APPROVE_AFFIRMATIVE_STRUCTURED",
        ),
        _row(
            "LVL-P4-009",
            "Holiday Inn Express and Suites Jeffersonville",
            "holiday inn express and suites jeffersonville", "IHG",
            "https://www.ihg.com/holidayinnexpress/hotels/us/en/"
            "jeffersonville/indjv/hoteldetail",
            "https://www.ihg.com/holidayinnexpress/hotels/us/en/"
            "jeffersonville/indjv/hoteldetail",
            ["Holiday Inn Express & Suites Louisville N - Jeffersonville",
             "1635 Veterans Parkway", "Jeffersonville, IN 47130",
             "email indjv@ighospitality.com (property code INDJV)",
             "+1-812-920-3918"],
            "VERIFIED_NO_PETS_CANDIDATE",
            [hie_faq, hie_img],
            [hie_quote],
            OrderedDict((
                ("pets_allowed", False),
            )),
            OrderedDict(),
            "Pass 3 was ACCESS_BLOCKED (403 on static fetch). This "
            "session's attended FAQ accordion gave an explicit first-party "
            "negative statement, not silence: 'No, pets are not allowed "
            "at Holiday Inn Express & Suites Louisville N - "
            "Jeffersonville.'",
            "APPROVE_VERIFIED_NO_PETS",
        ),
        _row(
            "LVL-P4-010", "Staybridge Suites Louisville East",
            "staybridge suites louisville east", "IHG",
            "https://www.ihg.com/staybridge/hotels/us/en/louisville/sdfmt/"
            "hoteldetail",
            "https://www.ihg.com/staybridge/hotels/us/en/louisville/sdfmt/"
            "hoteldetail",
            ["Staybridge Suites Louisville-East", "11711 Gateworth Way",
             "Louisville, KY 40299", "property code sdfmt in URL"],
            "PUBLICATION_CANDIDATE",
            [sb_faq, sb_img],
            [sb_quote],
            OrderedDict((
                ("pets_allowed", True),
                ("fee_cents_per_stay_1_to_6_nights", 7500),
                ("fee_cents_per_stay_7_plus_nights", 15000),
                ("fee_scope", "plus tax"),
            )),
            OrderedDict((
                ("fee_refundable", "CONTRADICTORY -- source calls the "
                 "$75 charge both a 'pet deposit' (implies refundable) "
                 "and a 'non refundable fee' in the same FAQ answer. "
                 "Withheld rather than resolved either direction."),
                ("species", "SOURCE_SILENT"),
                ("weight_limit", "SOURCE_SILENT"),
                ("max_pets", "SOURCE_SILENT"),
            )),
            "Pass 3 was ACCESS_BLOCKED (403 on static fetch). Pet FAQ was "
            "not in the default 3-question list; required clicking 'Read "
            "more FAQs' then the pet question to expand.",
            "HOLD_CONTRADICTORY_REFUND_TERMS",
        ),
        _row(
            "LVL-P4-011", "Candlewood Suites Louisville Airport",
            "candlewood suites louisville airport", "IHG",
            "https://www.ihg.com/candlewood/hotels/us/en/louisville/sdfgl/"
            "hoteldetail",
            "https://www.ihg.com/candlewood/hotels/us/en/louisville/sdfgl/"
            "hoteldetail",
            ["Candlewood Suites Louisville Airport", "1367 Gardiner Lane",
             "Louisville, KY 40213",
             "email GM.SDFGL@LotusHotelsTN.com (property code sdfgl)"],
            "PUBLICATION_CANDIDATE",
            [cw_faq, cw_img],
            [cw_quote],
            OrderedDict((
                ("pets_allowed", True),
                ("species", "ALL_PETS_EXPLICIT"),
                ("max_pets_per_room", 2),
                ("weight_limit_lbs", 80),
                ("fee_cents_per_pet_per_night", 3000),
                ("fee_refundable", False),
                ("flat_fee_cents_7_plus_nights_per_pet", 15000),
            )),
            OrderedDict((
                ("deposit_vs_fee_relationship", "AMBIGUOUS -- source "
                 "lists both 'Pet fee per night: 30 USD' and 'Pet damage "
                 "deposit: 30 USD' as separate line items with identical "
                 "amounts; unclear whether the damage deposit is a "
                 "distinct refundable charge or a duplicate restatement "
                 "of the nightly fee. Preserved as two separate observed "
                 "fields, not merged or resolved."),
            )),
            "Pet FAQ was already expanded/visible without needing "
            "'Read more FAQs'. Species stated as 'All pets allowed' "
            "(broader than the usual dog/cat pattern) -- explicit, not "
            "generic silence.",
            "HOLD_AMBIGUOUS_DEPOSIT_VS_FEE",
        ),
    ]

    if [r["identity_key"] for r in rows] != BATCH:
        raise SystemExit("row order mismatch")
    if len(rows) != 11 or len({r["identity_key"] for r in rows}) != 11:
        raise SystemExit("row count/duplicate mismatch")

    rec = partition.reconcile(
        census.identity_keys(census_doc),
        json.loads(PARTITION.read_text(encoding="utf-8-sig")),
        market_id="louisville-ky",
    )
    if rec.published != 0 or rec.verified_no_pets != 0:
        raise SystemExit("authority freeze broken")

    outcomes = [r["outcome"] for r in rows]
    outcome_counts = OrderedDict(
        (name, outcomes.count(name)) for name in sorted(VALID_OUTCOMES))

    brand_counts = OrderedDict((
        ("RED_ROOF", sum(1 for r in rows if r["brand"] == "RED_ROOF")),
        ("STUDIO6", sum(1 for r in rows if r["brand"] == "STUDIO6")),
        ("WYNDHAM", sum(1 for r in rows if r["brand"] == "WYNDHAM")),
        ("IHG", sum(1 for r in rows if r["brand"] == "IHG")),
    ))

    write_json(RESULTS, OrderedDict((
        ("schema", "ptf-louisville-pass4-capture-results/1.0"),
        ("work_order", WORK),
        ("market_id", "louisville-ky"),
        ("as_of", AS_OF),
        ("note",
         "Eleven-row attended Claude-in-Chrome capture of the existing "
         "manual capture queue (louisville_manual_capture_queue_001.json). "
         "No queue rebuild, no brand-surface rerun. Raw evidence is "
         "gitignored under data/operator_evidence/louisville-pass4-"
         "capture-001/raw. No policy authority and no founder approvals "
         "were written."),
        ("batch_total", 11),
        ("outcome_counts", outcome_counts),
        ("brand_counts", brand_counts),
        ("publication_grade_artifacts",
         sum(1 for r in rows if r["artifacts"])),
        ("identity_bound_count",
         sum(1 for r in rows if r["identity_binding"] == "BOUND")),
        ("founder_decisions_required", len(rows)),
        ("authority_changed", False),
        ("rows", rows),
    )))

    packet_rows = []
    for row in rows:
        packet_rows.append(OrderedDict((
            ("decision_id", row["decision_id"]),
            ("hotel", row["hotel"]),
            ("identity_key", row["identity_key"]),
            ("brand", row["brand"]),
            ("url", row["queued_url"]),
            ("final_url", row["final_url"]),
            ("identity_binding", row["identity_binding"]),
            ("identity_signals", row["identity_signals"]),
            ("exact_quotes", row["quotes"]),
            ("artifacts", row["artifacts"]),
            ("source_grade", row["source_grade"]),
            ("proposed_schema_1_2_facts", row["proposed_facts"]),
            ("withheld_fields", row["withheld_fields"]),
            ("notes", row["notes"]),
            ("recommended_founder_decision", row["recommended_founder_decision"]),
            ("outcome", row["outcome"]),
        )))

    write_json(PACKET, OrderedDict((
        ("schema", "ptf-louisville-pass4-founder-review-packet/1.0"),
        ("work_order", WORK),
        ("market_id", "louisville-ky"),
        ("as_of", AS_OF),
        ("note",
         "Pass 4 founder review packet. Every row has publication-grade "
         "evidence (screenshot and/or DOM-extracted first-party text "
         "bound to identity). No founder approvals written. "
         "published=0, verified_no_pets=0."),
        ("founder_approvals_written", False),
        ("decision_count", len(packet_rows)),
        ("rows", packet_rows),
    )))

    print("batch", 11,
          "publication_grade", sum(1 for r in rows if r["artifacts"]),
          "outcome_counts", dict(outcome_counts))


if __name__ == "__main__":
    main()
