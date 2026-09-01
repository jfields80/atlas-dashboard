# -*- coding: utf-8 -*-
"""The CURRENT promoted Indianapolis state, in one place.

Before this module the number 24 was written out by hand in roughly twenty
assertions across nine test files. That was fine while it never moved. When
PTF-INDIANAPOLIS-56-PROFILE-AUTHORITY-PROMOTION-017 promoted the market from
24 profiles to 55, every one of those assertions failed at once, and the
failure looked like twenty separate regressions instead of one intended change.

A count that lives in twenty places is not twenty guards. It is one fact and
nineteen chances to update it inconsistently.

WHAT THESE NUMBERS MEAN, AND WHAT THEY DO NOT
----------------------------------------------
They describe SOURCE-PROMOTED state: the committed package and shard. The
package carries ``published: true`` and ``deployed: false`` -- build-ready in
source, nothing deployed. A test asserting "this work order promoted nothing"
should NOT assert these numbers; it should assert that its own artifacts
propose rather than promote, because the live counts move whenever a LATER
work order legitimately promotes.
"""
from __future__ import annotations

#: launch_packages/pettripfinder/hotel_policy_facts_indianapolis-in.json
PROMOTED_PET_FRIENDLY = 67

#: markets/authority/indianapolis-in/hotel_exclusions.json
PROMOTED_VERIFIED_NO_PETS = 37

#: markets/authority/indianapolis-in/seed_businesses.csv (one row per profile)
PROMOTED_SEED_ROWS = 67

#: identity_census/indianapolis-in.json -- 257 from 004 until
#: PTF-INDIANAPOLIS-PROMOTION-AND-ASSEMBLY-014 promoted the reviewed shadow (263:
#: five retirements, one rebrand-successor rename, twelve admissions since 002).
CENSUS = 263

#: What the market was before 017, kept so a test can state the delta rather
#: than silently forget there was one.
PROMOTED_BEFORE_017 = 24
VERIFIED_NO_PETS_BEFORE_017 = 24

#: The work order that moved it, for error messages worth reading.
#: 56 by 017/018; 67 since PTF-INDIANAPOLIS-PROMOTION-AND-ASSEMBLY-014 applied the
#: 11 pending records (6 ESA + 5 Wyndham) and 3 verified-no-pets exclusions.
PROMOTED_BY = "PTF-INDIANAPOLIS-PROMOTION-AND-ASSEMBLY-014"
PROMOTED_BY_017 = "PTF-INDIANAPOLIS-56-PROFILE-AUTHORITY-PROMOTION-017"

#: Every verified-no-pets identity in the committed shard, sorted.
#: Six test files each froze this list inline at 24 names. One promotion
#: broke all six at once, which is six chances to update it inconsistently
#: and no extra safety. A test that means "this work order did not touch
#: the exclusion authority" should compare against the authority, not
#: against a copy of it made on a different day.
EXCLUSION_NAMES = [
    'baymont by wyndham indianapolis northeast',
    'comfort inn avon indianapolis west',
    'comfort inn fishers indianapolis',
    'comfort inn indianapolis airport plainfield',
    'comfort suites west indianapolis brownsburg',
    'courtyard by marriott indianapolis airport',
    'courtyard by marriott indianapolis at the capitol',
    'courtyard by marriott indianapolis downtown',
    'courtyard by marriott indianapolis fishers',
    'courtyard indianapolis noblesville',
    'courtyard indianapolis plainfield',
    'courtyard indianapolis west speedway',
    'crowne plaza indianapolis airport',
    'crowne plaza indianapolis downtown union station',
    'days inn and suites by wyndham northwest indianapolis',
    'days inn by wyndham indianapolis castleton',
    'fairfield inn and suites indianapolis avon',
    'fairfield inn and suites indianapolis carmel',
    'fairfield inn and suites indianapolis downtown',
    'fairfield inn and suites indianapolis east',
    'holiday inn express and suites greenwood',
    'holiday inn express and suites indianapolis east',
    'holiday inn express and suites indianapolis north carmel',
    'holiday inn express and suites indianapolis w airport area',
    'holiday inn express indianapolis downtown',
    'holiday inn express indianapolis fishers an ihg hotel',
    'holiday inn indianapolis downtown',
    'indianapolis marriott downtown',
    'jw marriott indianapolis',
    'marriott indianapolis north',
    'microtel inn and suites by wyndham indianapolis airport',
    'quality inn and suites airport',
    'sheraton indianapolis hotel at keystone crossing',
    'springhill suites by marriott indianapolis carmel',
    'springhill suites by marriott indianapolis westfield',
    'springhill suites indianapolis airport plainfield',
    'springhill suites indianapolis downtown',
]

#: The same authority, keyed by exclusion_id.
EXCLUSION_IDS = [
    'ii-baymont-by-wyndham-indianapolis-northeast',
    'ii-comfort-inn-avon-indianapolis-west',
    'ii-comfort-inn-fishers-indianapolis',
    'ii-comfort-inn-indianapolis-airport-plainfield',
    'ii-comfort-suites-west-indianapolis-brownsburg',
    'ii-courtyard-by-marriott-indianapolis-airport',
    'ii-courtyard-by-marriott-indianapolis-at-the-capitol',
    'ii-courtyard-by-marriott-indianapolis-downtown',
    'ii-courtyard-by-marriott-indianapolis-fishers',
    'ii-courtyard-indianapolis-noblesville',
    'ii-courtyard-indianapolis-plainfield',
    'ii-courtyard-indianapolis-west-speedway',
    'ii-crowne-plaza-indianapolis-airport',
    'ii-crowne-plaza-indianapolis-downtown-union-station',
    'ii-days-inn-and-suites-by-wyndham-northwest-indianapolis',
    'ii-days-inn-by-wyndham-indianapolis-castleton',
    'ii-fairfield-inn-and-suites-indianapolis-avon',
    'ii-fairfield-inn-and-suites-indianapolis-carmel',
    'ii-fairfield-inn-and-suites-indianapolis-downtown',
    'ii-fairfield-inn-and-suites-indianapolis-east',
    'ii-holiday-inn-express-and-suites-greenwood',
    'ii-holiday-inn-express-and-suites-indianapolis-east',
    'ii-holiday-inn-express-and-suites-indianapolis-north-carmel',
    'ii-holiday-inn-express-and-suites-indianapolis-w-airport-area',
    'ii-holiday-inn-express-indianapolis-downtown',
    'ii-holiday-inn-express-indianapolis-fishers-an-ihg-hotel',
    'ii-holiday-inn-indianapolis-downtown',
    'ii-indianapolis-marriott-downtown',
    'ii-jw-marriott-indianapolis',
    'ii-marriott-indianapolis-north',
    'ii-microtel-inn-and-suites-by-wyndham-indianapolis-airport',
    'ii-quality-inn-and-suites-airport',
    'ii-sheraton-indianapolis-hotel-at-keystone-crossing',
    'ii-springhill-suites-by-marriott-indianapolis-carmel',
    'ii-springhill-suites-by-marriott-indianapolis-westfield',
    'ii-springhill-suites-indianapolis-airport-plainfield',
    'ii-springhill-suites-indianapolis-downtown',
]
