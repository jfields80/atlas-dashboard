"""PTF-LOUISVILLE-IDENTITY-ROUTING-REPAIR-001 -- apply desk-pass findings.

Deterministic. Reads committed Louisville census + partition + derivation,
applies first-party identity/URL repairs, writes authorities and the two
required reports. Does not browse pet policy, does not publish, does not
touch other markets.

    python -m scripts.pettripfinder.apply_louisville_identity_routing_repair
"""
from __future__ import annotations

import json
from collections import Counter, OrderedDict
from pathlib import Path

from scripts.pettripfinder.census_partition_builder import (
    next_action_for, write_json,
)
from scripts.pettripfinder.contracts import census, enums, partition
from scripts.pettripfinder.normalize_census_geography import recompute

REPO = Path(__file__).resolve().parents[2]
PKG = REPO / "launch_packages" / "pettripfinder"
CENSUS_PATH = PKG / "identity_census" / "louisville-ky.json"
PARTITION_PATH = PKG / "louisville_final_partition_001.json"
DERIVATION_PATH = PKG / "markets" / "reports" / "louisville-ky_capture_queue_derivation.json"
REPAIR_PATH = PKG / "markets" / "reports" / "louisville_identity_routing_repair_001.json"
READY_PATH = PKG / "markets" / "reports" / "louisville_capture_ready_queue_002.json"
WORK = "PTF-LOUISVILLE-IDENTITY-ROUTING-REPAIR-001"
AS_OF = "2026-08-16"

DESK_CLASSES = {
    "IDENTITY_REVIEW", "PROPERTY_LEVEL_URL_RECOVERY", "ROUTING_REPLACEMENT",
}

# bind=True means identity is sufficiently bound and the URL may enter the
# capture-ready queue. Conflicts, closures, and unverified matches stay false.
REPAIRS = {
    # --- IDENTITY_REVIEW / Marriott ---
    "ac hotel by marriott louisville downtown": {
        "identity_class": "IDENTITY_CONFIRMED",
        "url_class": "EXACT_PROPERTY_URL_FOUND",
        "url": "https://www.marriott.com/en-us/hotels/sdfac-ac-hotel-louisville-downtown/overview/",
        "code": "sdfac", "source": "marriott.com", "bind": True,
        "phone": "502-568-6880",
        "notes": "Official AC Hotel Louisville Downtown. Page phone 502-568-6880.",
    },
    "aloft louisville downtown": {
        "identity_class": "IDENTITY_CORRECTION_REQUIRED",
        "url_class": "EXACT_PROPERTY_URL_FOUND",
        "url": "https://www.marriott.com/en-us/hotels/sdfld-aloft-louisville-downtown/overview/",
        "code": "sdfld", "source": "marriott.com", "bind": True,
        "phone": "502-583-1888",
        "notes": "Replaced stale sdfal (Aloft Louisville East) with sdfld Downtown at 102 W Main.",
    },
    "courtyard by marriott louisville downtown": {
        "identity_class": "IDENTITY_CONFIRMED",
        "url_class": "EXACT_PROPERTY_URL_FOUND",
        "url": "https://www.marriott.com/en-us/hotels/sdfdt-courtyard-louisville-downtown/overview/",
        "code": "sdfdt", "source": "marriott.com", "bind": True,
    },
    "courtyard by marriott louisville east": {
        "identity_class": "IDENTITY_CONFIRMED",
        "url_class": "EXACT_PROPERTY_URL_FOUND",
        "url": "https://www.marriott.com/en-us/hotels/sdfch-courtyard-louisville-east/overview/",
        "code": "sdfch", "source": "marriott.com", "bind": True,
    },
    "courtyard by marriott louisville northeast": {
        "identity_class": "IDENTITY_CONFIRMED",
        "url_class": "EXACT_PROPERTY_URL_FOUND",
        "url": "https://www.marriott.com/en-us/hotels/sdfne-courtyard-louisville-northeast/overview/",
        "code": "sdfne", "source": "marriott.com", "bind": True,
        "phone": "502-429-9293",
    },
    "fairfield inn and suites by marriott clarksville": {
        "identity_class": "IDENTITY_UNRESOLVED",
        "url_class": "URL_UNRESOLVED",
        "bind": False,
        "notes": "No Fairfield at 1717 Marriott Dr Clarksville IN. BNACV is Clarksville TN.",
    },
    "fairfield inn and suites by marriott louisville downtown": {
        "identity_class": "IDENTITY_CONFIRMED",
        "url_class": "EXACT_PROPERTY_URL_FOUND",
        "url": "https://www.marriott.com/en-us/hotels/sdffd-fairfield-inn-and-suites-louisville-downtown/overview/",
        "code": "sdffd", "source": "marriott.com", "bind": True,
    },
    "fairfield inn and suites by marriott louisville east": {
        "identity_class": "IDENTITY_CORRECTION_REQUIRED",
        "url_class": "EXACT_PROPERTY_URL_FOUND",
        "url": "https://www.marriott.com/en-us/hotels/sdfle-fairfield-inn-and-suites-louisville-east/overview/",
        "code": "sdfle", "source": "marriott.com", "bind": True,
        "address": "1220 Kentucky Mills Drive", "postal_code": "40299",
        "phone": "502-240-6171",
        "notes": "Official address 1220 Kentucky Mills Drive 40299, not 1220 S Hurstbourne Pkwy.",
    },
    "fairfield inn and suites by marriott louisville north": {
        "identity_class": "IDENTITY_CORRECTION_REQUIRED",
        "url_class": "IDENTITY_CONFLICT",
        "url": "https://www.marriott.com/en-us/hotels/sdffl-fairfield-inn-and-suites-louisville-jeffersonville/overview/",
        "code": "sdffl", "source": "marriott.com", "bind": False,
        "notes": "SDFFL is Fairfield Louisville Jeffersonville at 3000 Gottbrath Pkwy, not 300 Embassy Blvd.",
    },
    "residence inn by marriott louisville downtown": {
        "identity_class": "IDENTITY_CONFIRMED",
        "url_class": "EXACT_PROPERTY_URL_FOUND",
        "url": "https://www.marriott.com/en-us/hotels/sdfgj-residence-inn-louisville-downtown/overview/",
        "code": "sdfgj", "source": "marriott.com", "bind": True,
    },
    "residence inn by marriott louisville northeast": {
        "identity_class": "IDENTITY_CONFIRMED",
        "url_class": "EXACT_PROPERTY_URL_FOUND",
        "url": "https://www.marriott.com/en-us/hotels/sdfri-residence-inn-louisville-northeast/overview/",
        "code": "sdfri", "source": "marriott.com", "bind": True,
        "address": "3500 Springhurst Commons Drive",
        "phone": "502-412-1311",
    },
    "residence inn by marriott louisville st matthews": {
        "identity_class": "IDENTITY_CORRECTION_REQUIRED",
        "url_class": "IDENTITY_CONFLICT",
        "url": "https://www.marriott.com/en-us/hotels/sdfhf-residence-inn-louisville-east/overview/",
        "code": "sdfhf", "source": "marriott.com", "bind": False,
        "notes": "No Marriott page titled St Matthews. SDFHF is Residence Inn Louisville East at 120 N Hurstbourne.",
    },
    "springhill suites by marriott louisville downtown": {
        "identity_class": "IDENTITY_CONFIRMED",
        "url_class": "EXACT_PROPERTY_URL_FOUND",
        "url": "https://www.marriott.com/en-us/hotels/sdfsd-springhill-suites-louisville-downtown/overview/",
        "code": "sdfsd", "source": "marriott.com", "bind": True,
        "phone": "502-569-7373",
    },
    "springhill suites by marriott louisville hurstbourne north": {
        "identity_class": "IDENTITY_CONFIRMED",
        "url_class": "EXACT_PROPERTY_URL_FOUND",
        "url": "https://www.marriott.com/en-us/hotels/sdfsh-springhill-suites-louisville-hurstbourne-north/overview/",
        "code": "sdfsh", "source": "marriott.com", "bind": True,
        "address": "10101 Forest Green Boulevard", "postal_code": "40223",
        "phone": "502-326-3895",
    },
    "towneplace suites by marriott louisville northeast": {
        "identity_class": "IDENTITY_CORRECTION_REQUIRED",
        "url_class": "EXACT_PROPERTY_URL_FOUND",
        "url": "https://www.marriott.com/en-us/hotels/sdftn-towneplace-suites-louisville-northeast/overview/",
        "code": "sdftn", "source": "marriott.com", "bind": True,
        "address": "10110 Champions Farm Drive",
        "phone": "502-339-5410",
        "notes": "Official address 10110 Champions Farm Drive, not 3600 Springhurst Blvd.",
    },
    # --- IDENTITY_REVIEW / Hilton ---
    "embassy suites by hilton louisville east": {
        "identity_class": "IDENTITY_CONFIRMED",
        "url_class": "EXACT_PROPERTY_URL_FOUND",
        "url": "https://www.hilton.com/en/hotels/sdfemes-embassy-suites-louisville-east/",
        "code": "sdfemes", "source": "hilton.com", "bind": True,
    },
    "hampton inn and suites louisville east": {
        "identity_class": "IDENTITY_CORRECTION_REQUIRED",
        "url_class": "IDENTITY_CONFLICT",
        "url": "https://www.hilton.com/en/hotels/sdfhshx-hampton-suites-louisville-east/",
        "code": "sdfhshx", "source": "hilton.com", "bind": False,
        "notes": "Hilton Hampton Inn & Suites Louisville East is 1451 Alliant Ave, not 11901 Plantside Dr.",
    },
    "hampton inn clarksville": {
        "identity_class": "IDENTITY_CONFIRMED",
        "url_class": "EXACT_PROPERTY_URL_FOUND",
        "url": "https://www.hilton.com/en/hotels/sdfcvhx-hampton-louisville-north-clarksville/",
        "code": "sdfcvhx", "source": "hilton.com", "bind": True,
        "phone": "812-280-1501",
    },
    "hampton inn jeffersonville louisville north": {
        "identity_class": "IDENTITY_UNRESOLVED",
        "url_class": "URL_UNRESOLVED", "bind": False,
        "notes": "No Hilton page for Hampton at 7002 Highway 62 Jeffersonville.",
    },
    "hampton inn louisville downtown": {
        "identity_class": "IDENTITY_CONFIRMED",
        "url_class": "EXACT_PROPERTY_URL_FOUND",
        "url": "https://www.hilton.com/en/hotels/sdfdthx-hampton-louisville-downtown/",
        "code": "sdfdthx", "source": "hilton.com", "bind": True,
    },
    "hampton inn louisville northeast": {
        "identity_class": "IDENTITY_CONFIRMED",
        "url_class": "EXACT_PROPERTY_URL_FOUND",
        "url": "https://www.hilton.com/en/hotels/sdfkyhx-hampton-louisville-northeast/",
        "code": "sdfkyhx", "source": "hilton.com", "bind": True,
        "address": "4100 Hampton Lake Way",
    },
    "hampton inn sellersburg": {
        "identity_class": "IDENTITY_UNRESOLVED",
        "url_class": "URL_UNRESOLVED", "bind": False,
        "notes": "No Hampton Inn Sellersburg page. Spark Sellersburg is a different identity.",
    },
    "hilton garden inn louisville east": {
        "identity_class": "IDENTITY_CORRECTION_REQUIRED",
        "url_class": "IDENTITY_CONFLICT",
        "url": "https://www.hilton.com/en/hotels/sdflegi-hilton-garden-inn-louisville-east/",
        "code": "sdflegi", "source": "hilton.com", "bind": False,
        "notes": "HGI Louisville East is 1530 Alliant Ave. Census 9780 Ormsby Station / 502-423-0018 maps nearer HGI Northeast.",
    },
    "home2 suites by hilton jeffersonville": {
        "identity_class": "IDENTITY_UNRESOLVED",
        "url_class": "URL_UNRESOLVED", "bind": False,
        "notes": "No Home2 Jeffersonville page. Nearest is Home2 Clarksville at 1624 Leisure Way.",
    },
    "home2 suites by hilton louisville northeast": {
        "identity_class": "IDENTITY_UNRESOLVED",
        "url_class": "URL_UNRESOLVED", "bind": False,
        "notes": "No Home2 Louisville Northeast at 3701 Chamberlain Ln on hilton.com.",
    },
    "homewood suites by hilton louisville east": {
        "identity_class": "IDENTITY_CORRECTION_REQUIRED",
        "url_class": "IDENTITY_CONFLICT",
        "url": "https://www.hilton.com/en/hotels/sdfeahw-homewood-suites-louisville-east/",
        "code": "sdfeahw", "source": "hilton.com", "bind": False,
        "notes": "Homewood East is 9401 Hurstbourne Trace, not 10245 Linn Station Rd.",
    },
    "tru by hilton jeffersonville louisville north": {
        "identity_class": "IDENTITY_UNRESOLVED",
        "url_class": "URL_UNRESOLVED", "bind": False,
    },
    "tru by hilton louisville downtown": {
        "identity_class": "IDENTITY_UNRESOLVED",
        "url_class": "URL_UNRESOLVED", "bind": False,
        "notes": "No Tru Louisville Downtown at 410 S 3rd St on hilton.com.",
    },
    # --- IDENTITY_REVIEW / IHG ---
    "candlewood suites jeffersonville": {
        "identity_class": "IDENTITY_CORRECTION_REQUIRED",
        "url_class": "IDENTITY_CONFLICT",
        "url": "https://www.ihg.com/candlewood/hotels/us/en/clarksville/sdfvp/hoteldetail",
        "code": "sdfvp", "source": "ihg.com", "bind": False,
        "notes": "IHG Candlewood Louisville North is 1419 Bales Lane Clarksville, not 1419 N Luther Rd Jeffersonville.",
    },
    "candlewood suites louisville airport": {
        "identity_class": "IDENTITY_CONFIRMED",
        "url_class": "EXACT_PROPERTY_URL_FOUND",
        "url": "https://www.ihg.com/candlewood/hotels/us/en/louisville/sdfgl/hoteldetail",
        "code": "sdfgl", "source": "ihg.com", "bind": True,
    },
    "candlewood suites louisville east": {
        "identity_class": "IDENTITY_UNRESOLVED",
        "url_class": "URL_UNRESOLVED", "bind": False,
        "notes": "No Candlewood at 11701 Plantside Dr on IHG locator.",
    },
    "holiday inn express and suites louisville northeast": {
        "identity_class": "IDENTITY_CONFIRMED",
        "url_class": "EXACT_PROPERTY_URL_FOUND",
        "url": "https://www.ihg.com/holidayinnexpress/hotels/us/en/louisville/sdfwr/hoteldetail",
        "code": "sdfwr", "source": "ihg.com", "bind": True,
    },
    "holiday inn express clarksville": {
        "identity_class": "IDENTITY_UNRESOLVED",
        "url_class": "URL_UNRESOLVED", "bind": False,
    },
    "holiday inn express louisville southwest": {
        "identity_class": "IDENTITY_UNRESOLVED",
        "url_class": "URL_UNRESOLVED", "bind": False,
    },
    "holiday inn express new albany": {
        "identity_class": "IDENTITY_CORRECTION_REQUIRED",
        "url_class": "IDENTITY_CONFLICT",
        "url": "https://www.ihg.com/holidayinnexpress/hotels/us/en/new-albany/sdfna/hoteldetail",
        "code": "sdfna", "source": "ihg.com", "bind": False,
        "notes": "Official HIE New Albany is 506 W Spring St, not 200 Plaza Dr.",
    },
    "holiday inn express sellersburg": {
        "identity_class": "IDENTITY_UNRESOLVED",
        "url_class": "URL_UNRESOLVED", "bind": False,
    },
    "holiday inn louisville east hurstbourne": {
        "identity_class": "IDENTITY_CONFIRMED",
        "url_class": "EXACT_PROPERTY_URL_FOUND",
        "url": "https://www.ihg.com/holidayinn/hotels/us/en/louisville/sdfea/hoteldetail",
        "code": "sdfea", "source": "ihg.com", "bind": True,
    },
    # --- IDENTITY_REVIEW / Wyndham ---
    "days inn by wyndham clarksville": {
        "identity_class": "IDENTITY_UNRESOLVED",
        "url_class": "URL_UNRESOLVED", "bind": False,
    },
    "days inn by wyndham louisville downtown": {
        "identity_class": "IDENTITY_UNRESOLVED",
        "url_class": "URL_UNRESOLVED", "bind": False,
    },
    "la quinta inn and suites by wyndham louisville airport expo": {
        "identity_class": "PROPERTY_CLOSED",
        "url_class": "PROPERTY_CLOSED_OR_CONVERTED", "bind": False,
        "notes": "No La Quinta at 4125 Preston Hwy in current Wyndham inventory.",
    },
    "microtel inn and suites by wyndham louisville airport": {
        "identity_class": "IDENTITY_UNRESOLVED",
        "url_class": "URL_UNRESOLVED", "bind": False,
        "notes": "Only Louisville Microtel on brand site is East at 1221 Kentucky Mills Dr.",
    },
    "super 8 by wyndham clarksville": {
        "identity_class": "IDENTITY_UNRESOLVED",
        "url_class": "URL_UNRESOLVED", "bind": False,
    },
    "super 8 by wyndham louisville airport": {
        "identity_class": "IDENTITY_CONFIRMED",
        "url_class": "BRAND_PROPERTY_URL_FOUND",
        "url": "https://www.wyndhamhotels.com/super-8/louisville-kentucky/super-8-louisville-airport/overview",
        "source": "wyndhamhotels.com", "bind": True,
        "address": "4800 Preston Highway", "postal_code": "40213",
        "phone": "502-632-9574",
    },
    "super 8 by wyndham louisville southwest": {
        "identity_class": "IDENTITY_UNRESOLVED",
        "url_class": "URL_UNRESOLVED", "bind": False,
    },
    "super 8 by wyndham new albany": {
        "identity_class": "IDENTITY_UNRESOLVED",
        "url_class": "URL_UNRESOLVED", "bind": False,
    },
    "wingate by wyndham louisville east": {
        "identity_class": "IDENTITY_CORRECTION_REQUIRED",
        "url_class": "EXACT_PROPERTY_URL_FOUND",
        "url": "https://www.wyndhamhotels.com/wingate/louisville-kentucky/wingate-by-wyndham-louisville-east/overview",
        "source": "wyndhamhotels.com", "bind": True,
        "address": "12301 Alliant Court",
        "phone": "502-785-0850",
        "notes": "Official street is 12301 Alliant Court, not 12301 Plantside Dr.",
    },
    # --- IDENTITY_REVIEW / Choice ---
    "comfort inn louisville southwest": {
        "identity_class": "IDENTITY_CORRECTION_REQUIRED",
        "url_class": "IDENTITY_CONFLICT",
        "url": "https://www.choicehotels.com/kentucky/louisville/comfort-inn-hotels/ky148",
        "code": "ky148", "source": "choicehotels.com", "bind": False,
        "notes": "Comfort Inn SW ky148 is 4444 Dixie Hwy, not 6703 Dixie Hwy.",
    },
    "comfort inn louisville university": {
        "identity_class": "IDENTITY_UNRESOLVED",
        "url_class": "URL_UNRESOLVED", "bind": False,
    },
    "comfort inn sellersburg": {
        "identity_class": "IDENTITY_UNRESOLVED",
        "url_class": "URL_UNRESOLVED", "bind": False,
    },
    "quality inn and suites university airport": {
        "identity_class": "IDENTITY_CONFIRMED",
        "url_class": "BRAND_PROPERTY_URL_FOUND",
        "url": "https://www.choicehotels.com/kentucky/louisville/quality-inn-hotels/ky109",
        "code": "ky109", "source": "choicehotels.com", "bind": True,
    },
    "quality inn louisville airport": {
        "identity_class": "IDENTITY_UNRESOLVED",
        "url_class": "URL_UNRESOLVED", "bind": False,
    },
    "quality inn louisville east": {
        "identity_class": "IDENTITY_CORRECTION_REQUIRED",
        "url_class": "IDENTITY_CONFLICT",
        "url": "https://www.choicehotels.com/kentucky/louisville/quality-inn-hotels/ky369",
        "code": "ky369", "source": "choicehotels.com", "bind": False,
        "notes": "Quality Inn & Suites East ky369 is 9340 Blairwood Rd, not 1001 Herr Ln.",
    },
    "quality inn louisville southwest": {
        "identity_class": "PROPERTY_RENAMED_OR_CONVERTED",
        "url_class": "PROPERTY_CLOSED_OR_CONVERTED", "bind": False,
        "notes": "No Quality Inn SW. Comfort Inn ky148 now occupies 4444 Dixie Hwy.",
    },
    "quality inn new albany": {
        "identity_class": "IDENTITY_UNRESOLVED",
        "url_class": "URL_UNRESOLVED", "bind": False,
    },
    "quality suites jeffersonville louisville north": {
        "identity_class": "IDENTITY_CONFIRMED",
        "url_class": "EXACT_PROPERTY_URL_FOUND",
        "url": "https://www.choicehotels.com/indiana/jeffersonville/quality-inn-hotels/in198",
        "code": "in198", "source": "choicehotels.com", "bind": True,
    },
    "sleep inn louisville expo": {
        "identity_class": "IDENTITY_CONFIRMED",
        "url_class": "BRAND_PROPERTY_URL_FOUND",
        "url": "https://www.choicehotels.com/kentucky/louisville/sleep-inn-hotels/ky434",
        "code": "ky434", "source": "choicehotels.com", "bind": True,
    },
    # --- IDENTITY_REVIEW / other ---
    "country inn and suites by radisson louisville airport": {
        "identity_class": "IDENTITY_CORRECTION_REQUIRED",
        "url_class": "IDENTITY_CONFLICT",
        "url": "https://www.choicehotels.com/kentucky/louisville/country-inn-suites-hotels/ky417",
        "code": "ky417", "source": "choicehotels.com", "bind": False,
        "notes": "Only Louisville Country Inn is East at 1241 Kentucky Mills Dr, not 1241 Durrett Ln.",
    },
    "drury inn and suites louisville": {
        "identity_class": "IDENTITY_CORRECTION_REQUIRED",
        "url_class": "EXACT_PROPERTY_URL_FOUND",
        "url": "https://www.druryhotels.com/locations/louisville-ky/drury-inn-and-suites-louisville-east",
        "code": "0105", "source": "druryhotels.com", "bind": True,
        "address": "9501 Blairwood Road",
        "notes": "Official Drury Inn & Suites Louisville East at 9501 Blairwood (census 9502). Phone matches.",
    },
    "extended stay america suites louisville hurstbourne": {
        "identity_class": "PROPERTY_CLOSED",
        "url_class": "PROPERTY_CLOSED_OR_CONVERTED", "bind": False,
        "notes": "No Hurstbourne ESA on live brand city page. 10503 Timberwood Cir is not a current ESA hotel.",
    },
    "hyatt place louisville east": {
        "identity_class": "IDENTITY_CONFIRMED",
        "url_class": "EXACT_PROPERTY_URL_FOUND",
        "url": "https://www.hyatt.com/hyatt-place/en-US/sdfze-hyatt-place-louisville-east",
        "code": "SDFZE", "source": "hyatt.com", "bind": True,
    },
    "motel 6 louisville airport fair expo": {
        "identity_class": "IDENTITY_CORRECTION_REQUIRED",
        "url_class": "EXACT_PROPERTY_URL_FOUND",
        "url": "https://www.motel6.com/property/motel-louisville-kentucky-us-294109/",
        "code": "294109", "source": "motel6.com", "bind": True,
        "phone": "502-742-4722",
    },
    "motel 6 louisville ky bardstown road": {
        "identity_class": "PROPERTY_RENAMED_OR_CONVERTED",
        "url_class": "PROPERTY_CLOSED_OR_CONVERTED", "bind": False,
        "notes": "No Motel 6 Bardstown Road on motel6.com. Same address marketed as Budgetel Inn & Suites.",
    },
    "studio 6 louisville airport expo center": {
        "identity_class": "IDENTITY_CONFIRMED",
        "url_class": "EXACT_PROPERTY_URL_FOUND",
        "url": "https://www.studio6.com/property/motel-louisville-kentucky-us-294003/",
        "code": "294003", "source": "studio6.com", "bind": True,
        "address": "571 Phillips Lane", "phone": "502-361-5008",
    },
    "red roof inn louisville expo airport": {
        "identity_class": "IDENTITY_CONFIRMED",
        "url_class": "EXACT_PROPERTY_URL_FOUND",
        "url": "https://www.redroof.com/property/ky/louisville/rri118",
        "code": "RRI118", "source": "redroof.com", "bind": True,
    },
    "red roof inn louisville hurstbourne": {
        "identity_class": "IDENTITY_CONFIRMED",
        "url_class": "EXACT_PROPERTY_URL_FOUND",
        "url": "https://www.redroof.com/property/ky/louisville/rri034",
        "code": "RRI034", "source": "redroof.com", "bind": True,
    },
    # --- URL RECOVERY ---
    "baymont by wyndham louisville airport south": {
        "identity_class": "IDENTITY_CONFIRMED",
        "url_class": "EXACT_PROPERTY_URL_FOUND",
        "url": "https://www.wyndhamhotels.com/baymont/louisville-kentucky/baymont-inn-louisville-airport-south/overview",
        "source": "wyndhamhotels.com", "bind": True,
    },
    "best western greentree inn": {
        "identity_class": "IDENTITY_CONFIRMED",
        "url_class": "EXACT_PROPERTY_URL_FOUND",
        "url": "https://www.bestwestern.com/en_US/book/hotels-in-clarksville/best-western-green-tree-inn/propertyCode.18028.html",
        "code": "18028", "source": "bestwestern.com", "bind": True,
    },
    "best western premier louisville airport expo center hotel": {
        "identity_class": "PROPERTY_RENAMED_OR_CONVERTED",
        "url_class": "PROPERTY_CLOSED_OR_CONVERTED", "bind": False,
        "notes": "1921 Bishop Ln is Holiday Inn Express Airport Expo (IHG sdfbl). No BW Premier at that address on bestwestern.com.",
    },
    "cambria hotel louisville downtown whiskey row": {
        "identity_class": "IDENTITY_CONFIRMED",
        "url_class": "EXACT_PROPERTY_URL_FOUND",
        "url": "https://www.choicehotels.com/kentucky/louisville/cambria-hotels/ky322",
        "code": "ky322", "source": "choicehotels.com", "bind": True,
    },
    "candlewood suites louisville northeast": {
        "identity_class": "IDENTITY_CONFIRMED",
        "url_class": "EXACT_PROPERTY_URL_FOUND",
        "url": "https://www.ihg.com/candlewood/hotels/us/en/louisville/sdfza/hoteldetail",
        "code": "sdfza", "source": "ihg.com", "bind": True,
    },
    "candlewood suites louisville south fair and expo": {
        "identity_class": "IDENTITY_CONFIRMED",
        "url_class": "EXACT_PROPERTY_URL_FOUND",
        "url": "https://www.ihg.com/candlewood/hotels/us/en/louisville/sdfpp/hoteldetail",
        "code": "sdfpp", "source": "ihg.com", "bind": True,
        "notes": "IHG lists OPENING SOON / Fair-Expo Center. Property page exists.",
    },
    "comfort inn and suites clarksville": {
        "identity_class": "IDENTITY_CONFIRMED",
        "url_class": "BRAND_PROPERTY_URL_FOUND",
        "url": "https://www.choicehotels.com/indiana/clarksville/comfort-inn-hotels/in599",
        "code": "in599", "source": "choicehotels.com", "bind": True,
    },
    "comfort suites louisville airport": {
        "identity_class": "IDENTITY_CONFIRMED",
        "url_class": "EXACT_PROPERTY_URL_FOUND",
        "url": "https://www.choicehotels.com/kentucky/louisville/comfort-suites-hotels/ky136",
        "code": "ky136", "source": "choicehotels.com", "bind": True,
    },
    "comfort suites louisville east": {
        "identity_class": "IDENTITY_CONFIRMED",
        "url_class": "EXACT_PROPERTY_URL_FOUND",
        "url": "https://www.choicehotels.com/kentucky/louisville/comfort-suites-hotels/ky418",
        "code": "ky418", "source": "choicehotels.com", "bind": True,
    },
    "courtyard by marriott louisville airport": {
        "identity_class": "IDENTITY_CONFIRMED",
        "url_class": "EXACT_PROPERTY_URL_FOUND",
        "url": "https://www.marriott.com/en-us/hotels/sdfap-courtyard-louisville-airport/overview/",
        "code": "sdfap", "source": "marriott.com", "bind": True,
    },
    "drury inn and suites louisville north": {
        "identity_class": "IDENTITY_CONFIRMED",
        "url_class": "EXACT_PROPERTY_URL_FOUND",
        "url": "https://www.druryhotels.com/locations/louisville-ky/drury-inn-and-suites-louisville-north",
        "code": "0149", "source": "druryhotels.com", "bind": True,
    },
    "fairfield inn and suites by marriott louisville airport": {
        "identity_class": "IDENTITY_CORRECTION_REQUIRED",
        "url_class": "EXACT_PROPERTY_URL_FOUND",
        "url": "https://www.marriott.com/en-us/hotels/sdffa-fairfield-inn-and-suites-louisville-airport/overview/",
        "code": "sdffa", "source": "marriott.com", "bind": True,
        "address": "653 Phillips Lane",
        "notes": "Official address 653 Phillips Lane (census 807). Phone matches.",
    },
    "fairfield inn and suites by marriott new albany": {
        "identity_class": "IDENTITY_CORRECTION_REQUIRED",
        "url_class": "EXACT_PROPERTY_URL_FOUND",
        "url": "https://www.marriott.com/en-us/hotels/sdffy-fairfield-inn-and-suites-louisville-new-albany-in/overview/",
        "code": "sdffy", "source": "marriott.com", "bind": True,
        "address": "108 Daisy Summit", "phone": "812-920-3220",
        "notes": "Official address 108 Daisy Summit, not 500 Marriott Dr.",
    },
    "four points by sheraton louisville airport": {
        "identity_class": "IDENTITY_CONFIRMED",
        "url_class": "EXACT_PROPERTY_URL_FOUND",
        "url": "https://www.marriott.com/en-us/hotels/sdffp-four-points-louisville-airport/overview/",
        "code": "sdffp", "source": "marriott.com", "bind": True,
    },
    "hampton inn by hilton new albany louisville west": {
        "identity_class": "IDENTITY_CONFIRMED",
        "url_class": "EXACT_PROPERTY_URL_FOUND",
        "url": "https://www.hilton.com/en/hotels/sdfkdhx-hampton-new-albany-louisville-west/",
        "code": "sdfkdhx", "source": "hilton.com", "bind": True,
        "phone": "812-945-2771",
    },
    "hampton inn louisville airport": {
        "identity_class": "IDENTITY_CONFIRMED",
        "url_class": "EXACT_PROPERTY_URL_FOUND",
        "url": "https://www.hilton.com/en/hotels/sdfaphx-hampton-louisville-airport/",
        "code": "sdfaphx", "source": "hilton.com", "bind": True,
    },
    "hampton inn louisville east hurstbourne": {
        "identity_class": "IDENTITY_CONFIRMED",
        "url_class": "EXACT_PROPERTY_URL_FOUND",
        "url": "https://www.hilton.com/en/hotels/sdfhuhx-hampton-louisville-east-hurstbourne/",
        "code": "sdfhuhx", "source": "hilton.com", "bind": True,
        "phone": "502-426-1822",
    },
    "hawthorn suites by wyndham louisville east": {
        "identity_class": "IDENTITY_CONFIRMED",
        "url_class": "EXACT_PROPERTY_URL_FOUND",
        "url": "https://www.wyndhamhotels.com/hawthorn-extended-stay/louisville-kentucky/hawthorn-suites-by-wyndham-louisville-east/overview",
        "source": "wyndhamhotels.com", "bind": True,
        "phone": "502-785-0823",
    },
    "hilton garden inn jeffersonville": {
        "identity_class": "IDENTITY_CONFIRMED",
        "url_class": "EXACT_PROPERTY_URL_FOUND",
        "url": "https://www.hilton.com/en/hotels/sdfjfgi-hilton-garden-inn-jeffersonville-louisville-north/",
        "code": "sdfjfgi", "source": "hilton.com", "bind": True,
    },
    "hilton garden inn louisville airport": {
        "identity_class": "IDENTITY_CONFIRMED",
        "url_class": "EXACT_PROPERTY_URL_FOUND",
        "url": "https://www.hilton.com/en/hotels/sdfahgi-hilton-garden-inn-louisville-airport/",
        "code": "sdfahgi", "source": "hilton.com", "bind": True,
    },
    "hilton garden inn louisville downtown": {
        "identity_class": "IDENTITY_CONFIRMED",
        "url_class": "EXACT_PROPERTY_URL_FOUND",
        "url": "https://www.hilton.com/en/hotels/sdfldgi-hilton-garden-inn-louisville-downtown/",
        "code": "sdfldgi", "source": "hilton.com", "bind": True,
    },
    "hilton garden inn louisville mall st matthews": {
        "identity_class": "IDENTITY_CONFIRMED",
        "url_class": "EXACT_PROPERTY_URL_FOUND",
        "url": "https://www.hilton.com/en/hotels/sdfsmgi-hilton-garden-inn-louisville-mall-of-st-matthews/",
        "code": "sdfsmgi", "source": "hilton.com", "bind": True,
    },
    "holiday inn express and suites jeffersonville": {
        "identity_class": "IDENTITY_CONFIRMED",
        "url_class": "EXACT_PROPERTY_URL_FOUND",
        "url": "https://www.ihg.com/holidayinnexpress/hotels/us/en/jeffersonville/indjv/hoteldetail",
        "code": "indjv", "source": "ihg.com", "bind": True,
    },
    "holiday inn louisville airport south": {
        "identity_class": "IDENTITY_CONFIRMED",
        "url_class": "EXACT_PROPERTY_URL_FOUND",
        "url": "https://www.ihg.com/holidayinn/hotels/us/en/louisville/sdfoo/hoteldetail",
        "code": "sdfoo", "source": "ihg.com", "bind": True,
    },
    "home2 suites by hilton louisville airport expo center": {
        "identity_class": "IDENTITY_CONFIRMED",
        "url_class": "EXACT_PROPERTY_URL_FOUND",
        "url": "https://www.hilton.com/en/hotels/sdfecht-home2-suites-louisville-airport-expo-center/",
        "code": "sdfecht", "source": "hilton.com", "bind": True,
    },
    "home2 suites by hilton louisville downtown nulu": {
        "identity_class": "IDENTITY_CONFIRMED",
        "url_class": "EXACT_PROPERTY_URL_FOUND",
        "url": "https://www.hilton.com/en/hotels/sdflmht-home2-suites-louisville-downtown-nulu/",
        "code": "sdflmht", "source": "hilton.com", "bind": True,
    },
    "homewood suites by hilton louisville downtown": {
        "identity_class": "IDENTITY_CONFIRMED",
        "url_class": "EXACT_PROPERTY_URL_FOUND",
        "url": "https://www.hilton.com/en/hotels/loudthw-homewood-suites-louisville-downtown/",
        "code": "loudthw", "source": "hilton.com", "bind": True,
    },
    "howard johnson by wyndham louisville airport": {
        "identity_class": "PROPERTY_CLOSED",
        "url_class": "PROPERTY_CLOSED_OR_CONVERTED", "bind": False,
        "notes": "No Howard Johnson Louisville on current Wyndham locator.",
    },
    "marriott louisville east": {
        "identity_class": "IDENTITY_CONFIRMED",
        "url_class": "EXACT_PROPERTY_URL_FOUND",
        "url": "https://www.marriott.com/en-us/hotels/sdfls-louisville-marriott-east/overview/",
        "code": "sdfls", "source": "marriott.com", "bind": True,
    },
    "radisson hotel louisville north": {
        "identity_class": "IDENTITY_CONFIRMED",
        "url_class": "BRAND_PROPERTY_URL_FOUND",
        "url": "https://www.choicehotels.com/indiana/clarksville/radisson-hotels/in043",
        "code": "in043", "source": "choicehotels.com", "bind": True,
    },
    "residence inn by marriott louisville airport": {
        "identity_class": "IDENTITY_CONFIRMED",
        "url_class": "EXACT_PROPERTY_URL_FOUND",
        "url": "https://www.marriott.com/en-us/hotels/sdfra-residence-inn-louisville-airport/overview/",
        "code": "sdfra", "source": "marriott.com", "bind": True,
    },
    "sheraton louisville riverside hotel": {
        "identity_class": "IDENTITY_CONFIRMED",
        "url_class": "EXACT_PROPERTY_URL_FOUND",
        "url": "https://www.marriott.com/en-us/hotels/sdfsi-sheraton-louisville-riverside-hotel/overview/",
        "code": "sdfsi", "source": "marriott.com", "bind": True,
    },
    "springhill suites by marriott louisville airport": {
        "identity_class": "IDENTITY_CONFIRMED",
        "url_class": "EXACT_PROPERTY_URL_FOUND",
        "url": "https://www.marriott.com/en-us/hotels/sdfla-springhill-suites-louisville-airport/overview/",
        "code": "sdfla", "source": "marriott.com", "bind": True,
    },
    "star motel": {
        "identity_class": "IDENTITY_CORRECTION_REQUIRED",
        "url_class": "URL_UNRESOLVED", "bind": False,
        "notes": "No first-party site. SoIN lists Star Motel at 803 Hwy 31 East, not 1412 Eastern Blvd.",
    },
    "staybridge suites louisville east": {
        "identity_class": "IDENTITY_CONFIRMED",
        "url_class": "EXACT_PROPERTY_URL_FOUND",
        "url": "https://www.ihg.com/staybridge/hotels/us/en/louisville/sdfmt/hoteldetail",
        "code": "sdfmt", "source": "ihg.com", "bind": True,
    },
    "staybridge suites louisville expo center": {
        "identity_class": "IDENTITY_CONFIRMED",
        "url_class": "EXACT_PROPERTY_URL_FOUND",
        "url": "https://www.ihg.com/staybridge/hotels/us/en/louisville/sdfbg/hoteldetail",
        "code": "sdfbg", "source": "ihg.com", "bind": True,
    },
    "suburban studios louisville north": {
        "identity_class": "IDENTITY_CONFIRMED",
        "url_class": "EXACT_PROPERTY_URL_FOUND",
        "url": "https://www.choicehotels.com/indiana/clarksville/suburban-hotels/in269",
        "code": "in269", "source": "choicehotels.com", "bind": True,
    },
    "towneplace suites by marriott louisville airport": {
        "identity_class": "IDENTITY_CORRECTION_REQUIRED",
        "url_class": "EXACT_PROPERTY_URL_FOUND",
        "url": "https://www.marriott.com/en-us/hotels/sdfts-towneplace-suites-louisville-airport/overview/",
        "code": "sdfts", "source": "marriott.com", "bind": True,
        "address": "6601 Paramount Park Drive",
        "notes": "Official address 6601 Paramount Park Drive, not 4600 Olin Rd. Phone matches.",
    },
    "towneplace suites by marriott louisville downtown": {
        "identity_class": "IDENTITY_CONFIRMED",
        "url_class": "EXACT_PROPERTY_URL_FOUND",
        "url": "https://www.marriott.com/en-us/hotels/sdftd-towneplace-suites-louisville-downtown/overview/",
        "code": "sdftd", "source": "marriott.com", "bind": True,
    },
    "towneplace suites by marriott louisville north": {
        "identity_class": "IDENTITY_CONFIRMED",
        "url_class": "EXACT_PROPERTY_URL_FOUND",
        "url": "https://www.marriott.com/en-us/hotels/sdfvn-towneplace-suites-louisville-north/overview/",
        "code": "sdfvn", "source": "marriott.com", "bind": True,
        "phone": "812-914-4100",
    },
    "travelodge by wyndham sellersburg louisville north": {
        "identity_class": "IDENTITY_CONFIRMED",
        "url_class": "EXACT_PROPERTY_URL_FOUND",
        "url": "https://www.wyndhamhotels.com/travelodge/sellersburg-indiana/travelodge-sellersburg-louisville-north/overview",
        "source": "wyndhamhotels.com", "bind": True,
    },
    "tru by hilton louisville airport": {
        "identity_class": "IDENTITY_CONFIRMED",
        "url_class": "EXACT_PROPERTY_URL_FOUND",
        "url": "https://www.hilton.com/en/hotels/sdflaru-tru-louisville-airport/",
        "code": "sdflaru", "source": "hilton.com", "bind": True,
    },
    # --- ROUTING REPLACEMENT ---
    "moxy louisville downtown": {
        "identity_class": "IDENTITY_CONFIRMED",
        "url_class": "EXACT_PROPERTY_URL_FOUND",
        "url": "https://www.marriott.com/en-us/hotels/sdfox-moxy-louisville-downtown/overview/",
        "code": "sdfox", "source": "marriott.com", "bind": True,
        "discovery_url": "https://www.gotolouisville.com/directory/moxy-louisville-downtown/",
        "notes": "Replaced GoToLouisville directory route with Marriott sdfox. Tourism URL kept as discovery provenance.",
    },
    "myriad hotel": {
        "identity_class": "IDENTITY_CONFIRMED",
        "url_class": "EXACT_PROPERTY_URL_FOUND",
        "url": "https://myriadhotel.com/",
        "code": "sdfmyup", "source": "myriadhotel.com", "bind": True,
        "discovery_url": "https://www.gotolouisville.com/directory/myriad-hotel/",
        "notes": "First-party myriadhotel.com. Hilton Tapestry https://www.hilton.com/en/hotels/sdfmyup-the-myriad-hotel-louisville/.",
    },
    "residence inn by marriott louisville east oxmoor": {
        "identity_class": "IDENTITY_CONFIRMED",
        "url_class": "EXACT_PROPERTY_URL_FOUND",
        "url": "https://www.marriott.com/en-us/hotels/sdfre-residence-inn-louisville-east-oxmoor/overview/",
        "code": "sdfre", "source": "marriott.com", "bind": True,
        "phone": "502-409-8071",
        "discovery_url": "https://www.gotolouisville.com/directory/residence-inn-by-marriott-louisville-east-oxmoor/",
        "notes": "Replaced GoToLouisville directory route with Marriott sdfre.",
    },
}


def _load(path: Path):
    return json.loads(path.read_text(encoding="utf-8-sig"))


def _url_grade(url: str) -> str:
    url = (url or "").strip()
    if not url:
        return "missing"
    host = url.split("/")[2].lower() if "://" in url else ""
    if "gotolouisville.com" in host:
        return "tourism_directory"
    if any(h in host for h in (
        "marriott.com", "hilton.com", "ihg.com", "hyatt.com",
        "wyndhamhotels.com", "choicehotels.com", "omnihotels.com",
        "bestwestern.com", "druryhotels.com", "motel6.com", "studio6.com",
        "redroof.com",
    )):
        return "brand_property"
    return "exact_first_party"


def partition_state_for(hotel: dict, repair: dict | None, prior_state: str) -> str:
    if hotel["lodging_state"] == enums.NOT_LODGING:
        return enums.OUT_OF_CURRENT_CATEGORY
    if repair and repair.get("identity_class") in (
        "PROPERTY_CLOSED", "PROPERTY_RENAMED_OR_CONVERTED",
    ):
        return enums.AWAITING_CENSUS_REVIEW
    if hotel["identity_state"] in (
        enums.IDENTITY_UNRESOLVED, enums.IDENTITY_PROVISIONAL,
    ):
        return enums.AWAITING_IDENTITY_RESOLUTION
    if not (hotel.get("official_url") or "").strip():
        return enums.AWAITING_OFFICIAL_URL
    if prior_state == enums.AWAITING_POLICY_OBSERVATION or (
        repair and repair.get("bind")
    ):
        return enums.AWAITING_POLICY_OBSERVATION
    return prior_state


def main() -> None:
    census_doc = _load(CENSUS_PATH)
    part_doc = _load(PARTITION_PATH)
    der = _load(DERIVATION_PATH)
    hotels = {h["identity_key"]: h for h in census_doc["hotels"]}
    items = {i["identity_key"]: i for i in part_doc["items"]}

    desk_rows = [r for r in der["rows"] if r["execution_class"] in DESK_CLASSES]
    desk_keys = [r["identity_key"] for r in desk_rows]
    assert len(desk_rows) == 110, len(desk_rows)
    assert len(set(desk_keys)) == 110
    assert set(desk_keys) <= set(hotels)
    missing_repairs = [k for k in desk_keys if k not in REPAIRS]
    extra_repairs = [k for k in REPAIRS if k not in set(desk_keys)]
    if missing_repairs or extra_repairs:
        raise SystemExit("repair map mismatch missing=%s extra=%s"
                         % (missing_repairs, extra_repairs))

    before_ready = {
        r["identity_key"] for r in der["rows"]
        if r["execution_class"] in (
            "POLICY_OBSERVATION_REQUIRED", "ATTENDED_POLICY_SURFACE",
        )
    }

    repair_rows = []
    for desk in desk_rows:
        key = desk["identity_key"]
        hotel = hotels[key]
        item = items[key]
        repair = REPAIRS[key]
        before_url = hotel.get("official_url") or ""
        if repair.get("bind") and repair.get("url"):
            hotel["official_url"] = repair["url"]
            hotel["has_official_link"] = True
            hotel["identity_state"] = enums.IDENTITY_CONFIRMED
            hotel["lodging_state"] = enums.LODGING_CONFIRMED
        elif repair["identity_class"] in (
            "PROPERTY_CLOSED", "PROPERTY_RENAMED_OR_CONVERTED",
        ):
            hotel["lodging_state"] = enums.LODGING_NEEDS_REVIEW
        if repair.get("address"):
            hotel["address"] = repair["address"]
            hotel["street_identity"] = ("%s|%s" % (
                repair["address"].lower(),
                repair.get("postal_code") or hotel.get("postal_code") or "",
            ))
        if repair.get("postal_code"):
            hotel["postal_code"] = repair["postal_code"]
        if repair.get("phone"):
            hotel["phone"] = repair["phone"]
            hotel["phone_key"] = "".join(ch for ch in repair["phone"] if ch.isdigit())
        note = repair.get("notes") or ""
        if note:
            existing = hotel.get("notes") or ""
            hotel["notes"] = (existing + " " + note).strip() if existing else note

        new_state = partition_state_for(hotel, repair, item["final_state"])
        item["final_state"] = new_state
        item["official_url"] = hotel.get("official_url") or ""
        item["updated_at"] = AS_OF
        terminal = new_state in enums.TERMINAL_STATES
        item["resolved"] = terminal
        item["next_action"] = "" if terminal else next_action_for(new_state)
        item["next_action_source"] = "" if terminal else "markets/reports/louisville_identity_routing_repair_001.json"
        item["determined_by"] = "" if terminal else WORK
        if repair.get("bind"):
            item["state_override_reason"] = (
                "DESK_PASS %s: bound %s from %s."
                % (repair["url_class"], repair.get("code") or "property page",
                   repair.get("source") or "first-party")
            )
        elif repair["identity_class"] in (
            "PROPERTY_CLOSED", "PROPERTY_RENAMED_OR_CONVERTED",
        ):
            item["state_override_reason"] = "DESK_PASS %s. %s" % (
                repair["identity_class"], note)

        repair_rows.append(OrderedDict((
            ("identity_key", key),
            ("hotel", hotel["canonical_name"]),
            ("desk_class", desk["execution_class"]),
            ("address", hotel.get("address") or ""),
            ("city", hotel["city"]),
            ("state", hotel["state"]),
            ("postal_code", hotel.get("postal_code") or ""),
            ("phone", hotel.get("phone") or ""),
            ("brand_source", repair.get("source") or ""),
            ("property_code", repair.get("code") or ""),
            ("prior_url", before_url),
            ("official_url", hotel.get("official_url") or ""),
            ("discovery_provenance", repair.get("discovery_url") or ""),
            ("identity_class", repair["identity_class"]),
            ("url_class", repair["url_class"]),
            ("capture_ready", bool(repair.get("bind"))),
            ("notes", note),
        )))

    write_json(CENSUS_PATH, census_doc)
    census_doc, geo_changes = recompute("louisville-ky")
    hotels = {h["identity_key"]: h for h in census_doc["hotels"]}
    unassigned = [
        h["canonical_name"] for h in census_doc["hotels"]
        if h["lodging_state"] != enums.NOT_LODGING and not h.get("corridor")
    ]
    if unassigned:
        raise SystemExit("unassigned after recompute: %s" % unassigned)

    ident_counts = Counter(h["identity_state"] for h in census_doc["hotels"])
    census_doc["identity_state_counts"] = OrderedDict(sorted(ident_counts.items()))
    write_json(CENSUS_PATH, census_doc)

    counts = OrderedDict()
    for state in enums.PARTITION_STATES:
        n = sum(1 for i in part_doc["items"] if i["final_state"] == state)
        if n:
            counts[state] = n
    from scripts.pettripfinder.contracts.partition import STATE_MEANINGS
    present = {i["final_state"] for i in part_doc["items"]}
    part_doc["final_state_counts"] = counts
    part_doc["final_state_meanings"] = OrderedDict(
        (s, STATE_MEANINGS[s]) for s in enums.PARTITION_STATES if s in present)
    part_doc["as_of"] = AS_OF
    write_json(PARTITION_PATH, part_doc)

    rec = partition.reconcile(
        census.identity_keys(census_doc), part_doc, market_id="louisville-ky")
    if not rec.agrees:
        raise SystemExit("census/partition disagree")
    if census.validate(census_doc, market_states=["KY", "IN"]):
        raise SystemExit(census.validate(census_doc, market_states=["KY", "IN"]))
    if partition.validate(part_doc):
        raise SystemExit(partition.validate(part_doc))

    already = []
    for key in sorted(before_ready):
        hotel = hotels[key]
        item = items[key]
        already.append(OrderedDict((
            ("identity_key", key),
            ("hotel", hotel["canonical_name"]),
            ("state", hotel["state"]),
            ("corridor", hotel.get("corridor") or ""),
            ("official_url", hotel.get("official_url") or ""),
            ("url_grade", _url_grade(hotel.get("official_url") or "")),
            ("final_state", item["final_state"]),
            ("source", "prior_capture_ready"),
        )))
    newly = []
    for row in repair_rows:
        if not row["capture_ready"]:
            continue
        hotel = hotels[row["identity_key"]]
        item = items[row["identity_key"]]
        newly.append(OrderedDict((
            ("identity_key", row["identity_key"]),
            ("hotel", row["hotel"]),
            ("state", hotel["state"]),
            ("corridor", hotel.get("corridor") or ""),
            ("official_url", row["official_url"]),
            ("url_grade", _url_grade(row["official_url"])),
            ("final_state", item["final_state"]),
            ("source", "desk_pass_001"),
        )))
    ready_items = already + newly
    ready_items.sort(key=lambda r: r["identity_key"])

    market = _load(PKG / "markets" / "louisville-ky.json")
    corr_before = {c["corridor_id"]: c for c in der["corridor_readiness"]}
    corr_after = []
    for corridor in market["corridors"]:
        cid = corridor["corridor_id"]
        members = [h for h in census_doc["hotels"] if h.get("corridor") == cid]
        ready_here = [r for r in ready_items if r["corridor"] == cid]
        still = [
            h for h in members
            if items[h["identity_key"]]["final_state"] not in enums.TERMINAL_STATES
            and h["identity_key"] not in {r["identity_key"] for r in ready_here}
        ]
        newly_id = sum(
            1 for row in repair_rows
            if hotels[row["identity_key"]].get("corridor") == cid
            and row["identity_class"] == "IDENTITY_CONFIRMED"
        )
        newly_url = sum(
            1 for row in repair_rows
            if hotels[row["identity_key"]].get("corridor") == cid
            and row["capture_ready"]
        )
        corr_after.append(OrderedDict((
            ("corridor_id", cid),
            ("census", len(members)),
            ("queue_before", corr_before[cid]["queue"]),
            ("capture_ready_before", corr_before[cid]["capture_ready"]),
            ("newly_identity_confirmed", newly_id),
            ("newly_url_ready", newly_url),
            ("capture_ready_after", len(ready_here)),
            ("still_blocked", len(still)),
        )))

    id_counts = Counter(r["identity_class"] for r in repair_rows)
    url_counts = Counter(r["url_class"] for r in repair_rows)
    repair_doc = OrderedDict((
        ("schema", "ptf-louisville-identity-routing-repair/1.0"),
        ("work_order", WORK),
        ("market_id", "louisville-ky"),
        ("as_of", AS_OF),
        ("note",
         "Desk pass over the 110 unresolved identity/URL/routing rows. "
         "OTA pages were not used as identity authority. Closed/converted "
         "identities stay in census as AWAITING_CENSUS_REVIEW. No pet policy "
         "was captured."),
        ("desk_total", 110),
        ("desk_class_counts", dict(Counter(r["desk_class"] for r in repair_rows))),
        ("identity_class_counts", dict(id_counts)),
        ("url_class_counts", dict(url_counts)),
        ("capture_ready_before", len(before_ready)),
        ("capture_ready_after", len(ready_items)),
        ("routing_replacements_completed", 3),
        ("geography_changes", geo_changes),
        ("corridor_readiness", corr_after),
        ("rows", repair_rows),
    ))
    write_json(REPAIR_PATH, repair_doc)

    ready_doc = OrderedDict((
        ("schema", "ptf-louisville-capture-ready-queue/2.0"),
        ("work_order", WORK),
        ("market_id", "louisville-ky"),
        ("as_of", AS_OF),
        ("note",
         "Capture-ready identities only: identity bound, first-party or "
         "property-level brand URL, no unresolved rename/address conflict, "
         "no tourism-only route. Not a policy authority."),
        ("count", len(ready_items)),
        ("prior_ready", len(before_ready)),
        ("newly_ready", len(newly)),
        ("items", ready_items),
    ))
    write_json(READY_PATH, ready_doc)

    print("desk", 110)
    print("identity", dict(id_counts))
    print("url", dict(url_counts))
    print("ready before/after", len(before_ready), len(ready_items))
    print("geo_changes", len(geo_changes))
    print("partition", dict(part_doc["final_state_counts"]))
    print("unresolved", rec.unresolved, "ooc", rec.out_of_category)


if __name__ == "__main__":
    main()
