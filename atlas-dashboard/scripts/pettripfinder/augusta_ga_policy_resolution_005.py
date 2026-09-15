"""PTF-AUGUSTA-GA-POLICY-EVIDENCE-CLOSURE-002 -- the resolved outcome of every
one of the 82 census rows, transcribed directly from the six real evidence
captures under launch_packages/pettripfinder/markets/staging/augusta-ga/raw_captures/
(policy_wyndham_lane.json, policy_hilton_bw_g6_redroof_lane.json,
policy_choice_woodspring_esa_myplace_hyatt_lane.json, policy_marriott_ihg_lane.json,
policy_independent_lane.json, policy_routing_and_identity_investigation.json).

Every entry here is either:
  - a verbatim classification the evidence captured (VERIFIED_PET_FRIENDLY /
    VERIFIED_NO_PETS / POLICY_UNRESOLVED / SOURCE_SILENT / ACCESS_BLOCKED /
    BRAND_INDEX_ONLY / NO_OFFICIAL_ROUTE_FOUND / DEAD_URL), or
  - an identity-collision resolution (all three PTF-AUGUSTA-GA-PARALLEL-
    SOURCE-READY-001 holds came back LIKELY_DISTINCT_PROPERTIES with
    corroborating evidence -- different phone numbers, independent rebrand
    histories, or a mislabeled property code needing correction rather than
    a merge).

Nothing here is inferred beyond what the evidence says. Properties with no
entry below (Marriott's 9, most of IHG's 5) are 100% ACCESS_BLOCKED per
policy_marriott_ihg_lane.json and are handled by the default case in the
consumer script.
"""

from __future__ import annotations

PF = "VERIFIED_PET_FRIENDLY"
NP = "VERIFIED_NO_PETS"
UNRESOLVED = "POLICY_UNRESOLVED"
SILENT = "SOURCE_SILENT"
BLOCKED = "ACCESS_BLOCKED"
BRAND_INDEX = "BRAND_INDEX_ONLY"
NO_ROUTE = "NO_OFFICIAL_ROUTE_FOUND"
DEAD = "DEAD_URL"
CONTRADICTION = "CONTRADICTION"


def r(classification, quote="", facts=None, source_class="", capture_lane="",
      new_url=None, identity_note=""):
    return {
        "classification": classification,
        "operative_quote": quote,
        "parsed_facts": facts or {},
        "source_class": source_class,
        "capture_lane": capture_lane,
        "new_official_url": new_url,
        "identity_note": identity_note,
    }


# canonical_name -> resolution. Keyed by the EXACT name in augusta_ga_market_build_001.CANDIDATES.
RESOLUTIONS = {
    # --- Downtown ---
    "Augusta Marriott at the Convention Center": r(BLOCKED, source_class="PT2_BRAND"),
    "Hyatt House Augusta/Downtown": r(
        SILENT, source_class="PT3_THIRD_PARTY", capture_lane="cvb_listing",
        identity_note="hyatt.com's own property page (PT2_BRAND, higher authority) returned HTTP 403 "
                       "on both /policies and /hotel-info; remains ACCESS_BLOCKED at that tier. The Visit "
                       "Augusta CVB listing (the official_url on file) was successfully read and is silent."),
    "Holiday Inn Express Augusta Downtown": r(
        BLOCKED, source_class="PT2_BRAND",
        identity_note="OPEN FLAG (not acted on): an unverified WebSearch snippet from a parallel batch "
                       "suggested this property's code (agsag) may actually belong to a Stevens Creek Rd "
                       "address, not 444 Broad St Downtown, and that the true Downtown code may be 'agsdt'. "
                       "This was explicitly NOT used as evidence by the agent that found it (secondhand, not "
                       "a direct quote) and is not acted on here either -- flagged for a future direct-fetch "
                       "verification once ihg.com's block lifts, not resolved by this pass."),
    "Ramada by Wyndham Augusta Downtown Hotel & Conference Center": r(BRAND_INDEX, source_class="PT2_BRAND"),
    "Econo Lodge Downtown Augusta": r(
        NP, "Pets Allowed: No General: Only service animals are permitted, free of charge.",
        source_class="PT2_BRAND", capture_lane="official_brand_property_page",
        new_url="https://www.choicehotels.com/georgia/augusta/econo-lodge-hotels/ga584"),
    "The Partridge Inn Augusta, Curio Collection by Hilton": r(
        PF, "Pets\nPets allowed: Yes\nNon-refundable fee: $75.00\nMax weight: 80 lbs\nMax size: Large\n"
            "Pet policy: $75.00 for up to 3 days per pet per day then $25.00 per pet per day thereafter. "
            "Up to 2 dogs per room.",
        facts={"fee": "$75.00 for up to 3 days per pet, then $25.00 per pet per day thereafter",
               "fee_basis": "non-refundable, per pet per day after an initial period",
               "pet_count_limit": 2, "weight_limit": "80 lbs, Max size: Large",
               "species": "dogs (up to 2 dogs per room)"},
        source_class="PT2_BRAND", capture_lane="official_brand_property_page",
        new_url="https://www.hilton.com/en/hotels/agscuqq-the-partridge-inn-augusta/",
        identity_note="Requested URL's property code (agswepi) 404'd; corrected to agscuqq."),
    "Queen Anne Inn": r(SILENT, source_class="PT1_FIRST_PARTY", capture_lane="direct_independent_site"),
    "Olde Town Inn (Fox's Lair)": r(SILENT, source_class="PT1_FIRST_PARTY", capture_lane="direct_independent_site"),

    # --- Washington Road ---
    "Wingate by Wyndham Augusta Washington Road": r(UNRESOLVED, "Pet & Service Animal Policy",
        source_class="PT2_BRAND", capture_lane="official_brand_property_page"),
    "Tru by Hilton Augusta Washington Road": r(
        PF, "Pets\nPets allowed: Yes\nNon-refundable fee: $125.00\nMax weight: 75 lbs\nMax size: Large",
        facts={"fee": "$125.00 non-refundable", "weight_limit": "75 lbs, Max size: Large"},
        source_class="PT2_BRAND", capture_lane="official_brand_property_page"),
    "Spark by Hilton Augusta": r(
        PF, "Pets\nPets allowed: Yes\nNon-refundable fee: $75.00\nMax weight: 50 lbs\nMax size: Medium",
        facts={"fee": "$75.00 non-refundable", "weight_limit": "50 lbs, Max size: Medium"},
        source_class="PT2_BRAND", capture_lane="official_brand_property_page"),
    "Best Western Plus Augusta North Inn & Suites": r(
        PF, "PET POLICY: We are Pet Friendly and allow up to two dogs in a limited number of rooms. The "
            "size limit for any one dog shall be 80 pounds. Other pet types (e.g., cats) may be allowed "
            "upon the hotel's approval prior to arrival. The Pet Friendly rate is 40.00 USD per day. A "
            "refundable cleaning and damage deposit of 150.00 USD is required upon check-in.",
        facts={"fee": "40.00 USD per day", "deposit": "150.00 USD refundable cleaning/damage deposit",
               "pet_count_limit": 2, "weight_limit": "80 lbs per dog",
               "species": "dogs (up to 2); cats upon approval", "room_restrictions": "limited pet-friendly rooms"},
        source_class="PT2_BRAND", capture_lane="official_brand_property_page"),
    "Candlewood Suites Augusta": r(BLOCKED, source_class="PT2_BRAND"),
    "Hilton Garden Inn Augusta": r(
        PF, "Pets\nPets allowed: Yes\nNon-refundable fee: $75.00\nMax weight: 75 lbs\nMax size: Large\n"
            "Pet policy: $75(1-4n),$125(5+n) 2petsMax,dog/cat onl",
        facts={"fee": "$75.00 non-refundable; $75 (1-4 nights), $125 (5+ nights)", "pet_count_limit": 2,
               "weight_limit": "75 lbs, Max size: Large", "species": "dog/cat"},
        source_class="PT2_BRAND", capture_lane="official_brand_property_page",
        new_url="https://www.hilton.com/en/hotels/agsaggi-hilton-garden-inn-augusta/",
        identity_note="Requested code (agsgigi) 404'd; corrected to agsaggi."),
    "Homewood Suites by Hilton Augusta": r(
        PF, "Pets\nPets allowed: Yes\nNon-refundable fee: $75.00\nPet policy: $75(1-4n),$125(5+n) "
            "2petMax,dog/cat only",
        facts={"fee": "$75.00 non-refundable; $75 (1-4 nights), $125 (5+ nights)", "pet_count_limit": 2,
               "species": "dog/cat"},
        source_class="PT2_BRAND", capture_lane="official_brand_property_page",
        new_url="https://www.hilton.com/en/hotels/agsschw-homewood-suites-augusta/",
        identity_note="CRITICAL FIX: the requested code (augwehw) resolves to Homewood Suites by Hilton "
                       "AUGUSTA, MAINE (377 Western Avenue, Augusta ME 04330), not this Georgia property. "
                       "Corrected to the real Georgia property's code, agsschw (1049 Stevens Creek Road)."),
    "Holiday Inn Express Augusta (Stevens Creek Rd)": r(BLOCKED, source_class="PT2_BRAND"),
    "Sheraton Augusta Hotel": r(BLOCKED, source_class="PT2_BRAND"),
    "Courtyard by Marriott Augusta": r(BLOCKED, source_class="PT2_BRAND"),
    "Comfort Suites Augusta Riverwatch": r(
        NP, "Pets Allowed: No General: Only service animals are permitted, free of charge.",
        source_class="PT2_BRAND", capture_lane="official_brand_property_page",
        new_url="https://www.choicehotels.com/georgia/augusta/comfort-suites-hotels/ga579"),
    "Baymont Inn & Suites Augusta (Riverwest)": r(
        NP, "PET & SERVICE ANIMAL POLICY: ADA defined service animals are welcome at this hotel. "
            "Sorry no other pets are allowed.",
        source_class="PT2_BRAND", capture_lane="official_brand_property_page",
        new_url="https://www.wyndhamhotels.com/baymont/augusta-georgia/baymont-inn-and-suites-augusta-riverwatch/overview",
        identity_note="Renamed 'Baymont by Wyndham Augusta Riverwatch'; same address, same identity."),
    "Microtel Inn & Suites by Wyndham Augusta": r(UNRESOLVED, "Pet & Service Animal Policy",
        source_class="PT2_BRAND", capture_lane="official_brand_property_page",
        new_url="https://www.wyndhamhotels.com/microtel/augusta-georgia/microtel-inn-and-suites-augusta-riverwatch/overview"),
    "WoodSpring Suites Augusta Riverwatch": r(
        PF, "Pets allowed. A Non refundable pet registration fee of 50.00 USD and 10.00 USD per night "
            "per pet. Max 75 lbs, 2 dogs per room. No cats.",
        facts={"fee": "50.00 USD non-refundable registration + 10.00 USD/night per pet",
               "pet_count_limit": 2, "weight_limit": "75 lbs", "species": "dogs only; no cats",
               "room_restrictions": "2 dogs per room"},
        source_class="PT2_BRAND", capture_lane="official_brand_property_page"),
    "Quality Inn & Suites Augusta I-20": r(
        NP, "Pets Allowed: No General: Only service animals are permitted, free of charge.",
        source_class="PT2_BRAND", capture_lane="official_brand_property_page"),
    "Rodeway Inn Augusta (Washington Rd)": r(
        UNRESOLVED, source_class="PT2_BRAND",
        identity_note="RESOLVED as a DISTINCT property from Masters Inn Augusta (different phone: "
                       "706-496-2202 vs 706-863-5566; Rodeway is Choice-branded 'Unit B', Masters Inn is "
                       "independent with no unit letter). No policy page fetch was attempted this pass "
                       "(it was originally an identity hold, not sent to the Choice fetch batch); remains "
                       "POLICY_NOT_VERIFIED pending a future property-page read."),
    "Red Roof Inn Washington Road Augusta": r(
        PF, "Pet Policy: One, well-behaved domestic pet (cat or dog) Stays Free! Pets must be declared "
            "at check-in. Up to 2 pets allowed per room. Second pet $15/ night, not to exceed 7 nights or "
            "$105 per pet per stay. Pet not to exceed 80 pounds.",
        facts={"fee": "first pet free; second pet $15/night, max $105/pet/stay", "pet_count_limit": 2,
               "weight_limit": "80 lbs", "species": "cat or dog"},
        source_class="PT2_BRAND", capture_lane="official_brand_property_page",
        new_url="https://www.redroof.com/property/ga/augusta/rri450",
        identity_note="Requested slug retired/redirected to homepage; corrected to path rri450."),
    "HomeTowne Studios Augusta (Washington Rd)": r(
        PF, "Pet Policy: Service animals and Emotional Support Animals are welcome at all HomeTowne "
            "Studios By Red Roof Properties and must be declared at check-in. Pets are permitted with a "
            "$5.00 fee per night, up to $30 a week, and up to $70.00 a month (per pet).",
        facts={"fee": "$5.00/night, up to $30/week, up to $70.00/month per pet"},
        source_class="PT2_BRAND", capture_lane="official_brand_general_page",
        new_url="https://www.redroof.com/extendedstay/hometownestudios/property/ga/augusta/hts1239"),
    "Fairfield Inn & Suites Augusta Washington Rd. / I-20": r(BLOCKED, source_class="PT2_BRAND"),
    "Super 8 Motel Augusta (Washington Rd)": r(
        PF, "Rooms with microwaves and refrigerators, as well as non-smoking rooms, are available at "
            "our pet-friendly hotel.",
        source_class="PT2_BRAND", capture_lane="official_brand_property_page"),
    "Days Inn Washington Road Augusta": r(BRAND_INDEX, source_class="PT2_BRAND"),
    "Hampton Inn & Suites Augusta-Washington Rd": r(
        PF, "PETS\nPets allowed: Yes\nNon-refundable fee: $75.00\nMax weight: 75 lbs\nMax size: Medium\n"
            "Pet policy: $75(1-4n),$125(5+n) 2 pets Max, dog/cat only",
        facts={"fee": "$75.00 non-refundable; $75 (1-4 nights), $125 (5+ nights)", "pet_count_limit": 2,
               "weight_limit": "75 lbs, Max size: Medium", "species": "dog/cat"},
        source_class="PT2_BRAND", capture_lane="official_brand_property_page"),
    "Sonesta Essential Augusta": r(
        UNRESOLVED, source_class="PT2_BRAND",
        identity_note="RESOLVED as DISTINCT from Heritage Inn Augusta (documented rebrand lineage: Rodeway "
                       "Inn & Suites -> SureStay Plus by Best Western -> Sonesta Essential, phone "
                       "706-650-1311; Heritage Inn never appears in that lineage and has its own phone "
                       "706-868-6930 with active reviews through Dec 2025). No policy page fetch attempted "
                       "this pass; remains POLICY_NOT_VERIFIED."),
    "Masters Inn Augusta (aka Masters Economy Inn)": r(
        NO_ROUTE, source_class="",
        identity_note="RESOLVED as DISTINCT from Rodeway Inn Augusta (Washington Rd) -- see that entry. "
                       "mastersinn.com is a dead/parked domain (HugeDomains for-sale page); no live "
                       "official site exists.",
        new_url=""),
    "Heritage Inn Augusta": r(
        NO_ROUTE, source_class="",
        identity_note="RESOLVED as DISTINCT from Sonesta Essential Augusta -- see that entry. No official "
                       "or independent website found; only aggregator listings (Yelp, Tripadvisor, "
                       "Expedia).", new_url=""),
    "Sunset Inn Augusta": r(
        SILENT, source_class="PT1_FIRST_PARTY", capture_lane="direct_independent_site",
        new_url="https://sunsetinnaugusta.com/",
        identity_note="Own domain resolved and reachable, but the page is a thin/unfinished template with "
                       "no pet-policy content."),
    "Rodeway Inn Augusta West - Fort Eisenhower": r(
        NP, "Pets Allowed: No General: Only service animals are permitted, free of charge.",
        source_class="PT2_BRAND", capture_lane="official_brand_property_page"),
    "Baymont Inn & Suites West Augusta (NW Frontage Rd)": r(BRAND_INDEX, source_class="PT2_BRAND"),
    "Knights Inn at Boy Scout Road Augusta": r(
        BRAND_INDEX, source_class="PT2_BRAND",
        identity_note="Every URL variant redirected all the way to the Wyndham corporate homepage -- a "
                       "stronger 'gone' signal, consistent with having exited the Wyndham franchise "
                       "network. Still operates independently per third-party listings."),
    "West Bank Inn": r(
        NP, "Service animals complying with ADA Title lll regulations are allowed. Sorry, pets are not "
            "allowed.",
        source_class="PT3_THIRD_PARTY", capture_lane="reservation_platform_listing",
        new_url="https://www.hotelplanner.com/Hotels/224829/Reservations-West-Bank-Inn-Augusta-2904-Washington-Rd-30909",
        identity_note="First-party site (westbankinn.net) was silent; a property-specific hotelplanner.com "
                       "page gave an unambiguous refusal, used per the rule that a third-party reservation "
                       "page may support a restrictive claim."),

    # --- West Augusta ---
    "Econo Lodge West Augusta": r(
        NP, "Pets Allowed: No General: Only service animals are permitted, free of charge.",
        source_class="PT2_BRAND", capture_lane="official_brand_property_page"),
    "La Quinta Inn & Suites by Wyndham Augusta/Fort Eisenhower": r(
        PF, "Recharge at our pet-friendly hotel with comfortable accommodations, convenient amenities, "
            "and our signature Here for You service.",
        source_class="PT2_BRAND", capture_lane="official_brand_property_page",
        new_url="https://www.wyndhamhotels.com/laquinta/augusta-georgia/la-quinta-inn-and%20suites-augusta-fort-eisenhower/overview"),
    "Comfort Inn & Suites West Augusta": r(
        NP, "Pets Allowed: No General: Only service animals are permitted, free of charge.",
        source_class="PT2_BRAND", capture_lane="official_brand_property_page",
        new_url="https://www.choicehotels.com/georgia/augusta/comfort-inn-hotels/ga842"),
    "Quality Inn & Suites Augusta Fort Gordon Area": r(
        BLOCKED, source_class="PT2_BRAND",
        new_url="https://www.choicehotels.com/georgia/augusta/quality-inn-hotels/ga395",
        identity_note="Property page found (code ga395, phone 706-855-2088) but choicehotels.com blocked "
                       "every fetch attempt."),
    "Hampton Inn & Suites West Augusta": r(
        PF, "PETS\nPets allowed: Yes\nNon-refundable fee: $50.00\nPet policy: 1-4 night stay $50; "
            "5+ night stay $75; 2 pets max; dog or cat only",
        facts={"fee": "$50.00 non-refundable; $50 (1-4 nights), $75 (5+ nights)", "pet_count_limit": 2,
               "species": "dog or cat"},
        source_class="PT2_BRAND", capture_lane="official_brand_property_page",
        new_url="https://www.hilton.com/en/hotels/agswehx-hampton-suites-augusta-west/",
        identity_note="Requested code (agswshx) 404'd; corrected to agswehx."),
    "Holiday Inn Express & Suites West Augusta": r(
        UNRESOLVED, source_class="PT2_BRAND",
        identity_note="Identity hold RESOLVED: this is a real, distinct property (IHG code agsjd "
                       "consistently and exclusively resolves to it across many indexed ihg.com subpages). "
                       "Not fetched for policy this pass (ihg.com blocked); remains POLICY_NOT_VERIFIED."),
    "Holiday Inn West Augusta": r(
        UNRESOLVED, source_class="PT2_BRAND",
        new_url="https://www.ihg.com/holidayinn/hotels/us/en/augusta/agsbr/hoteldetail",
        identity_note="Identity hold RESOLVED as a DISTINCT property from Holiday Inn Express & Suites "
                       "West Augusta. The original code (agsjd) was a DATA ERROR -- it belongs solely to "
                       "the Express property. This hotel's real IHG code, confirmed via ihg.com's own "
                       "indexed subpages, is agsbr (different ZIP, 30813; different phone, 706-396-4600). "
                       "Corrected here rather than merged or dropped."),
    "Hyatt Place Augusta": r(
        PF, "Pets Are Welcome. Our hotel gladly welcomes your four-legged friends. Pet Fees: 1-6 nights: "
            "$100 / STAY. 7-30 nights (Includes cleaning fee): $200 / STAY. Weight Limits: Individual pet "
            "weight limit: 50 Pounds. Combined pets weight limit: 75 Pounds. Maximum number of pets is 2.",
        facts={"fee": "$100/stay (1-6 nights); $200/stay (7-30 nights)", "pet_count_limit": 2,
               "weight_limit": "individual 50 lbs; combined 75 lbs"},
        source_class="PT2_BRAND", capture_lane="official_brand_property_page"),
    "Extended Stay America Premier Suites - Augusta": r(BLOCKED, source_class="PT2_BRAND",
        identity_note="Hard bot-detection interstitial (slide-to-verify) on both headless fetch and a real "
                       "interactive browser session; not bypassed."),
    "DoubleTree by Hilton Hotel Augusta": r(
        PF, "Pets\nPets allowed: Yes\nMax weight: 30 lbs\nMax size: Medium\nPet policy: $75(1-4n), "
            "$125(5+n) 2 pet max dogs & cats only",
        facts={"fee": "$75 (1-4 nights), $125 (5+ nights)", "pet_count_limit": 2, "weight_limit": "30 lbs",
               "species": "dogs & cats"},
        source_class="PT2_BRAND", capture_lane="official_brand_property_page",
        new_url="https://www.hilton.com/en/hotels/agsdtdt-doubletree-augusta/hotel-info/",
        identity_note="Requested code (agsddt) 404'd; corrected to agsdtdt."),
    "Affordable Suites of America Augusta": r(
        PF, "Both small pets and service animals are always welcome in our pet-friendly rooms. Two-animal "
            "maximum per room. There is a $25 non-refundable charge per pet, per day, with a maximum of "
            "$150 per pet. There is no charge for service animals.",
        facts={"fee": "$25 non-refundable per pet per day, max $150 per pet", "pet_count_limit": 2},
        source_class="PT1_FIRST_PARTY", capture_lane="direct_independent_site",
        new_url="https://www.affordablesuites.com/hotels/affordable-suites-augusta-ga/",
        identity_note="ROUTING CLOSED: no official URL was on file before this pass; the corporate "
                       "franchise site resolved directly."),
    "Home2 Suites by Hilton Augusta, GA": r(
        PF, "Pets\nPets allowed: Yes\nNon-refundable fee: $75.00\nPet policy: 1-4 night stay $75; "
            "5+ night stay $125; 2 pets max; dog or cat only",
        facts={"fee": "$75.00 non-refundable; $75 (1-4 nights), $125 (5+ nights)", "pet_count_limit": 2,
               "species": "dog or cat"},
        source_class="PT2_BRAND", capture_lane="official_brand_property_page"),
    "Residence Inn by Marriott Augusta": r(BLOCKED, source_class="PT2_BRAND"),
    "SpringHill Suites by Marriott Augusta": r(BLOCKED, source_class="PT2_BRAND"),
    "My Place Hotel-Augusta, GA": r(
        PF, "Yes! My Place Hotel-Augusta, GA is dog-friendly only. At My Place Hotel-Augusta, GA, "
            "there's a pet fee of $20 per night, $100 per week, or $250 per month per room.",
        facts={"fee": "$20/night, $100/week, or $250/month per room", "species": "dog-friendly only"},
        source_class="PT2_BRAND", capture_lane="official_brand_property_page"),
    "Days Inn Wheeler Road Augusta": r(
        UNRESOLVED, "Additional charges may apply for local amenities such as rollaway beds, parking, "
                    "safe warranties, telephone charges, and pets (if allowed).",
        source_class="PT2_BRAND", capture_lane="official_brand_property_page",
        identity_note="A conditional fee-disclaimer sentence only, not an accept/refuse statement -- "
                       "correctly not inferred as pet-friendly."),
    "Perrin Guest House Inn (aka Perrin Plantation and Inn)": r(
        DEAD, source_class="",
        identity_note="perringuesthouse.com now resolves to an unrelated squatted/spam domain; no live "
                       "official site found.", new_url=""),

    # --- Gordon Highway / Fort Eisenhower ---
    "Studio 6 Fort Gordon Augusta": r(
        PF, "Pet-Friendly Accommodation\nPets welcome throughout your stay\n...\nPets Allowed",
        source_class="PT2_BRAND", capture_lane="official_brand_property_page"),
    "Motel 6 Augusta, GA - Ft Gordon": r(
        PF, "Pet-Friendly Accommodation\nPets welcome throughout your stay\n...\nPets Allowed",
        source_class="PT2_BRAND", capture_lane="official_brand_property_page",
        new_url="https://www.motel6.com/property/motel-augusta-ga-georgia-us-293201/",
        identity_note="Requested numeric code redirected to the sibling Studio 6 property; corrected to "
                       "Motel 6's own id 293201."),
    "Quality Inn & Suites South Augusta (near Fort Gordon)": r(
        NP, "Pets Allowed: No General: Only service animals are permitted, free of charge.",
        source_class="PT2_BRAND", capture_lane="official_brand_property_page"),
    "Hampton Inn Gordon Highway Augusta": r(
        PF, "PETS\nPets allowed: Yes\nNon-refundable fee: $75.00\nPet policy: $75(1-4n), $125(5+n) "
            "2petsMax,dog/cat only",
        facts={"fee": "$75.00 non-refundable; $75 (1-4 nights), $125 (5+ nights)", "pet_count_limit": 2,
               "species": "dog/cat"},
        source_class="PT2_BRAND", capture_lane="official_brand_property_page"),
    "Homewood Suites by Hilton Augusta Gordon Highway": r(
        PF, "Pets\nPets allowed: Yes\nNon-refundable fee: $75.00\nPet policy: $75(1-4n), $125(5+n) "
            "2 pet max dogs & cats only",
        facts={"fee": "$75.00 non-refundable; $75 (1-4 nights), $125 (5+ nights)", "pet_count_limit": 2,
               "species": "dogs & cats"},
        source_class="PT2_BRAND", capture_lane="official_brand_property_page"),
    "Days Inn Fort Gordon Augusta": r(UNRESOLVED, "Pet & Service Animal Policy",
        source_class="PT2_BRAND", capture_lane="official_brand_property_page"),
    "Fairfield Inn & Suites by Marriott Augusta (Gordon Hwy / Fort Eisenhower Area)": r(
        BLOCKED, source_class="PT2_BRAND"),
    "Ramada Hotel Fort Gordon Augusta": r(BRAND_INDEX, source_class="PT2_BRAND"),
    "WoodSpring Suites Fort Gordon Augusta": r(
        PF, "Pets allowed. A Non refundable pet registration fee of 50.00 USD and 10.00 USD per night "
            "per pet. Max 75 lbs, 2 dogs per room. No cats.",
        facts={"fee": "50.00 USD non-refundable registration + 10.00 USD/night per pet",
               "pet_count_limit": 2, "weight_limit": "75 lbs", "species": "dogs only; no cats"},
        source_class="PT2_BRAND", capture_lane="official_brand_property_page",
        new_url="https://www.woodspring.com/extended-stay-hotels/locations/georgia/augusta/woodspring-suites-augusta-fort-gordon",
        identity_note="Requested URL was truncated/malformed; corrected to the live property page."),
    "Wingate by Wyndham Fort Gordon Augusta": r(UNRESOLVED, "Pet & Service Animal Policy",
        source_class="PT2_BRAND", capture_lane="official_brand_property_page",
        new_url="https://www.wyndhamhotels.com/wingate/augusta-georgia/wingate-by-wyndham-augusta-fort-eisenhower/overview"),
    "Super 8 Hotel Fort Gordon Augusta": r(UNRESOLVED, "Pet & Service Animal Policy",
        source_class="PT2_BRAND", capture_lane="official_brand_property_page",
        new_url="https://www.wyndhamhotels.com/super-8/augusta-georgia/super-8-augusta-ft-eisenhower-area/overview"),
    "Scottish Inn Augusta (aka Deluxe Inn Augusta)": r(
        NO_ROUTE, source_class="",
        identity_note="Hospitality International's own locator lists two other Augusta properties but "
                       "neither is this address (1636 Gordon Highway); likely exited that franchise "
                       "network. No brand-hosted page found.", new_url=""),
    "Comfort Inn & Suites Augusta Fort Eisenhower Area": r(
        BLOCKED, source_class="PT2_BRAND",
        new_url="https://www.choicehotels.com/georgia/augusta/comfort-inn-hotels/ga800",
        identity_note="Property page found (code ga800, phone 706-736-6100) but choicehotels.com blocked "
                       "every fetch attempt."),
    "Red Carpet Inn - Augusta": r(SILENT, source_class="PT3_THIRD_PARTY",
        capture_lane="reservation_platform_listing"),
    "Budget Inn Express": r(
        NP, "Pets are not allowed.", source_class="PT1_FIRST_PARTY",
        capture_lane="direct_independent_site",
        new_url="https://www.budgetinnexpressaugusta.us/policies.html",
        identity_note="Homepage marketing copy references 'Pet Friendly Hotels Augusta Ga' as an SEO "
                       "phrase; overridden by the explicit refusal on the site's own policies page."),

    # --- South Augusta ---
    "Americas Best Value Inn Augusta": r(
        SILENT, source_class="PT2_BRAND", capture_lane="official_brand_property_page",
        new_url="https://www.sonesta.com/americas-best-value-inn/ga/augusta/americas-best-value-inn-augusta-s",
        identity_note="ROUTING CLOSED: the ABVI franchisor (Red Lion) was absorbed into Sonesta; this "
                       "brand-affiliated page (address matches exactly) is now the official property page. "
                       "Only a generic 'PAWS at Sonesta' program link, no property-specific terms."),
    "Rodeway Inn Augusta South": r(
        NP, "Pets Allowed: No General: Only service animals are permitted, free of charge.",
        source_class="PT2_BRAND", capture_lane="official_brand_property_page"),
    "Rodeway Inn & Suites Hephzibah Augusta": r(
        CONTRADICTION,
        "Yes! Pets are allowed. [same section, immediately adjacent:] no pets. [elsewhere on page:] "
        "pets are accepted with an additional per night fee.",
        facts={"fee": "unspecified additional per-night fee (contradictory source)"},
        source_class="PT3_THIRD_PARTY", capture_lane="reservation_platform_listing",
        new_url="https://www.choicehotels.com/georgia/hephzibah/rodeway-inn-hotels/ga895",
        identity_note="The hotelplanner.com listing (previously the official_url on file) contains directly "
                       "contradictory boilerplate -- an affirmative 'Yes! Pets are allowed' beside a "
                       "standalone 'no pets' with no qualifier distinguishing them, reading as a templating "
                       "defect rather than a genuine property statement. Updated official_url to the true "
                       "Choice Hotels brand page (ga895, higher authority) for future re-verification; that "
                       "page itself timed out on 3 fetch attempts this pass (ACCESS_BLOCKED at that tier) "
                       "and does NOT resolve the contradiction."),

    # --- Grovetown ---
    "Baymont Inn & Suites Grovetown": r(UNRESOLVED, "Pet & Service Animal Policy",
        source_class="PT2_BRAND", capture_lane="official_brand_property_page",
        new_url="https://www.wyndhamhotels.com/baymont/grovetown-georgia/baymont-by-wyndham-grovetown-augusta/overview"),
    "Days Inn & Suites Grovetown": r(UNRESOLVED, "Pet & Service Animal Policy",
        source_class="PT2_BRAND", capture_lane="official_brand_property_page",
        new_url="https://www.wyndhamhotels.com/days-inn/grovetown-georgia/days-inn-and-suites-augusta-near-fort-eisenhower/overview"),
    "Best Western Augusta West (Grovetown)": r(
        NP, "Pet Policy: Pets are not accepted.", source_class="PT2_BRAND",
        capture_lane="official_brand_property_page"),
    "Sleep Inn & Suites Grovetown - Augusta West": r(
        NP, "Pets Allowed: No General: Only service animals are permitted, free of charge.",
        source_class="PT2_BRAND", capture_lane="official_brand_property_page",
        new_url="https://www.choicehotels.com/georgia/grovetown/sleep-inn-hotels/gac60"),
    "Home2 Suites by Hilton Grovetown Augusta Area": r(
        PF, "Pets\nPets allowed: Yes\nNon-refundable fee: $75.00\nMax weight: 75 lbs\nMax size: Large\n"
            "Pet policy: 1-4 night stay $75 5+ night stay $125 2 pets max dog or cat only",
        facts={"fee": "$75.00 non-refundable; $75 (1-4 nights), $125 (5+ nights)", "pet_count_limit": 2,
               "weight_limit": "75 lbs, Max size: Large", "species": "dog or cat"},
        source_class="PT2_BRAND", capture_lane="official_brand_property_page"),
    "avid hotel Augusta W - Grovetown": r(BLOCKED, source_class="PT2_BRAND"),
    "TownePlace Suites by Marriott Grovetown": r(BLOCKED, source_class="PT2_BRAND"),
    "Fairfield Inn & Suites Grovetown": r(BLOCKED, source_class="PT2_BRAND"),
    "Holiday Inn Express & Suites Augusta W - Grovetown": r(BLOCKED, source_class="PT2_BRAND"),
}
