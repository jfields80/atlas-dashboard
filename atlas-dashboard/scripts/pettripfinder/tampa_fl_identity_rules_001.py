"""PTF-TAMPA-FL-PARALLEL-SOURCE-READY-001 -- Tampa-owned identity rules.

Address normalisation, brand vocabulary, lodging-category classification and
Tampa Bay geography used ONLY by the tampa-fl shadow build. Nothing here is
imported by, or changes, any shared factory module. Address/brand helpers and
BRAND_PATTERNS / DUAL_BRAND_PAIRS are the same national vocabulary Orlando's
identity rules used (scripts/pettripfinder/orlando_fl_identity_rules_001.py on
worker/ptf-orlando-fl-market-001) -- reused unmodified because brand names are
not market-specific. Geography, TIMESHARE_RX/VACATION_RENTAL_RX/NON_HOTEL_RX/
RESTRICTED_RX/CONDO_HOTEL_NAMES are Tampa Bay-specific and written fresh.
"""

from __future__ import annotations

import math
import re


# ==========================================================================
# addr
# ==========================================================================

SUFFIX = {"BOULEVARD": "BLVD", "BLV": "BLVD", "DRIVE": "DR", "DV": "DR", "ROAD": "RD", "PARKWAY": "PKWY", "PWKY": "PKWY", "PKY": "PKWY", "HIGHWAY": "HWY",
          "STREET": "ST", "AVENUE": "AVE", "AV": "AVE", "COURT": "CT", "CIRCLE": "CIR", "LANE": "LN", "TRAIL": "TRL", "TR": "TRL", "PLACE": "PL",
          "TERRACE": "TER", "LOOP": "LOOP", "WAY": "WAY", "PLAZA": "PLZ", "SQUARE": "SQ", "CROSSING": "XING", "COVE": "CV", "POINT": "PT", "PIKE": "PIKE", "CT.": "CT"}
DIRS = {"NORTH": "N", "SOUTH": "S", "EAST": "E", "WEST": "W", "NORTHEAST": "NE", "NORTHWEST": "NW", "SOUTHEAST": "SE", "SOUTHWEST": "SW"}
GENERIC_STREET = set(SUFFIX.values()) | set(DIRS.values()) | {"US", "SR", "STATE", "ROUTE", "HWY", "MEMORIAL", "MEM", "BLDG", "UNIT", "STE", "SUITE", "FL"}
FIX = [
    (r"\bSTATE (ROAD|RD) (\d+)\b", r"SR\2"), (r"\bSR (\d+)\b", r"SR\1"), (r"\bFL-(\d+)\b", r"SR\1"),
    (r"\b(US|U S) (HWY|HIGHWAY) (\d+)\b", r"US\3"), (r"\bUS (\d+)\b", r"US\1"), (r"\b(HWY|HIGHWAY) (\d+)\b", r"US\2"), (r"\bUS-(\d+)\b", r"US\1"),
    (r"\bINT'?L\b", "INTERNATIONAL"), (r"\bINTL\b", "INTERNATIONAL"), (r"\bDALE MABRY HWY\b", "DALE MABRY HWY"),
    (r"\bVETERANS EXPWY\b", "VETERANS EXPRESSWAY"), (r"\bVETERANS EXPY\b", "VETERANS EXPRESSWAY"),
    (r"\bMEMORIAL HWY\b", "MEMORIAL HWY"), (r"\bBAYSHORE BLV\b", "BAYSHORE BLVD"), (r"\bST\.\b", "ST"),
    (r"\bGANDY BLV\b", "GANDY BLVD"), (r"\bKENNEDY BLV\b", "KENNEDY BLVD"), (r"\bFOWLER AV\b", "FOWLER AVE"),
]


def norm_street(s):
    s = (s or "").upper()
    s = re.sub(r"[#,]", " ", s)
    s = re.sub(r"(?<=[A-Z])-(?=[A-Z])", " ", s)
    s = re.sub(r"(?<=\w)\.(?=\s|$)", "", s)
    s = re.sub(r"\s+", " ", s).strip()
    for a, b in FIX:
        s = re.sub(a, b, s)
    toks = []
    for t in s.split():
        t = t.strip(".")
        t = SUFFIX.get(t, t)
        t = DIRS.get(t, t)
        toks.append(t)
    return " ".join(toks)


def split_number(s):
    s = norm_street(s)
    m = re.match(r"^(\d+)(?:-?[A-Z](?=\s))?\s*(.*)$", s)
    if not m:
        return None, s
    return m.group(1), m.group(2)


def street_core(rest):
    toks = [t for t in rest.split() if t not in DIRS.values()]
    toks = [t for t in toks if t not in ("BLDG", "UNIT", "STE", "SUITE")]
    core = [t for t in toks if t not in GENERIC_STREET]
    if not core and toks:
        core = toks[:1]
    return core


def addr_key(street):
    num, rest = split_number(street)
    core = street_core(rest)
    return num, core


def directionals(street):
    num, rest = split_number(street)
    toks = rest.split()
    return {t for t in toks[:1] if t in DIRS.values()}


def same_address(a, b):
    na, ca = addr_key(a)
    nb, cb = addr_key(b)
    da, db = directionals(a), directionals(b)
    if da and db and da != db:
        return False
    if not na or not nb or na != nb:
        return False
    if not ca or not cb:
        return False
    sa, sb = set(ca), set(cb)
    if sa & sb:
        return True
    return False


GENERIC_NAME = {"HOTEL", "HOTELS", "INN", "SUITES", "SUITE", "AND", "THE", "BY", "AT", "OF", "&", "TAMPA", "RESORT", "RESORTS", "LLC", "INC", "A", "AN", "FL", "FLORIDA",
                "MARRIOTT", "HILTON", "WYNDHAM", "IHG", "COLLECTION", "NEAR", "AREA", "IN", "ON", "-", "/", "EXTENDED", "STAY", "CLEARWATER", "PETERSBURG", "ST", "SAINT"}


def name_tokens(n):
    n = (n or "").upper().replace("&", " AND ")
    n = re.sub(r"[^A-Z0-9 ]", " ", n)
    return [t for t in n.split() if t not in GENERIC_NAME]


def name_sim(a, b):
    ta, tb = set(name_tokens(a)), set(name_tokens(b))
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def haversine_m(lat1, lng1, lat2, lng2):
    r = 6371000.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = p2 - p1, math.radians(lng2 - lng1)
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


# ==========================================================================
# brands (national vocabulary, same as orlando_fl_identity_rules_001.BRAND_PATTERNS)
# ==========================================================================

BRAND_PATTERNS = [
    (r"\bhampton\s+inn\b|\bhampton\b(?!\s+roads)|\bhamption\b", ("HILTON", "HAMPTON")),
    (r"\bhilton\s+garden\s+inn\b|\bhgi\b", ("HILTON", "HILTON_GARDEN_INN")),
    (r"\bhome\s?2\b", ("HILTON", "HOME2")),
    (r"\bhomewood\b", ("HILTON", "HOMEWOOD")),
    (r"\bembassy\s+suites\b", ("HILTON", "EMBASSY")),
    (r"\bdouble\s?tree\b", ("HILTON", "DOUBLETREE")),
    (r"\btru\s+by\s+hilton\b", ("HILTON", "TRU")),
    (r"\bspark\b", ("HILTON", "SPARK")),
    (r"\bsignia\b", ("HILTON", "SIGNIA")),
    (r"\bwaldorf\b", ("HILTON", "WALDORF")),
    (r"\bconrad\b", ("HILTON", "CONRAD")),
    (r"\bcanopy\b", ("HILTON", "CANOPY")),
    (r"\btapestry\b", ("HILTON", "TAPESTRY")),
    (r"\bhilton\s+(grand\s+)?vacation", ("HILTON_VACATION", "HGV")),
    (r"\bhilton\b", ("HILTON", "HILTON")),
    (r"\bcourtyard\b", ("MARRIOTT", "COURTYARD")),
    (r"\bresidence\s+inn\b", ("MARRIOTT", "RESIDENCE_INN")),
    (r"\bspring\s?hill\b", ("MARRIOTT", "SPRINGHILL")),
    (r"\btowne?\s?place\b", ("MARRIOTT", "TOWNEPLACE")),
    (r"\bfairfield\b", ("MARRIOTT", "FAIRFIELD")),
    (r"\bfour\s+points\b", ("MARRIOTT", "FOUR_POINTS")),
    (r"\bsheraton\s+vistana\b|\bvistana\b", ("MARRIOTT_VACATION", "VISTANA")),
    (r"\bsheraton\b", ("MARRIOTT", "SHERATON")),
    (r"\bwestin\b", ("MARRIOTT", "WESTIN")),
    (r"\brenaissance\b", ("MARRIOTT", "RENAISSANCE")),
    (r"\baloft\b", ("MARRIOTT", "ALOFT")),
    (r"\belement\b", ("MARRIOTT", "ELEMENT")),
    (r"\bac\s+hotel\b", ("MARRIOTT", "AC")),
    (r"\bmoxy\b", ("MARRIOTT", "MOXY")),
    (r"\bdelta\b", ("MARRIOTT", "DELTA")),
    (r"\bgaylord\b", ("MARRIOTT", "GAYLORD")),
    (r"\bjw\s+marriott\b", ("MARRIOTT", "JW")),
    (r"\britz\b", ("MARRIOTT", "RITZ")),
    (r"\btribute\s+portfolio\b", ("MARRIOTT", "TRIBUTE")),
    (r"\bautograph\s+collection\b", ("MARRIOTT", "AUTOGRAPH")),
    (r"\ble\s+meridien\b", ("MARRIOTT", "LE_MERIDIEN")),
    (r"\bedition\b", ("MARRIOTT", "EDITION")),
    (r"\bmarriott'?s\b|\bmarriott\s+vacation\b", ("MARRIOTT_VACATION", "MVC")),
    (r"\bmarriott\b", ("MARRIOTT", "MARRIOTT")),
    (r"\bholiday\s+inn\s+club\b", ("IHG_VACATION", "HICV")),
    (r"\bholiday\s+inn\s+express\b", ("IHG", "HIEX")),
    (r"\bholiday\s+inn\b", ("IHG", "HOLIDAY_INN")),
    (r"\bcrowne\s+plaza\b", ("IHG", "CROWNE")),
    (r"\bstaybridge\b", ("IHG", "STAYBRIDGE")),
    (r"\bcandlewood\b", ("IHG", "CANDLEWOOD")),
    (r"\bavid\b", ("IHG", "AVID")),
    (r"\beven\s+hotel|\beven\b\s*(&|and)", ("IHG", "EVEN")),
    (r"\bindigo\b", ("IHG", "INDIGO")),
    (r"\bvoco\b", ("IHG", "VOCO")),
    (r"\bkimpton\b", ("IHG", "KIMPTON")),
    (r"\bhyatt\s+place\b", ("HYATT", "HYATT_PLACE")),
    (r"\bhyatt\s+house\b", ("HYATT", "HYATT_HOUSE")),
    (r"\bhyatt\s+regency\b", ("HYATT", "HYATT_REGENCY")),
    (r"\bhyatt\b", ("HYATT", "HYATT")),
    (r"\bcomfort\s+(inn|suites)\b", ("CHOICE", "COMFORT")),
    (r"\bquality\s+(inn|suites)\b", ("CHOICE", "QUALITY")),
    (r"\bsleep\s+inn\b", ("CHOICE", "SLEEP")),
    (r"\bclarion\b", ("CHOICE", "CLARION")),
    (r"\bcambria\b", ("CHOICE", "CAMBRIA")),
    (r"\becono\s+lodge\b", ("CHOICE", "ECONO")),
    (r"\brodeway\b", ("CHOICE", "RODEWAY")),
    (r"\bmainstay\b", ("CHOICE", "MAINSTAY")),
    (r"\bsuburban\b", ("CHOICE", "SUBURBAN")),
    (r"\bwoodspring\b|\bwoodsprings\b", ("CHOICE", "WOODSPRING")),
    (r"\bdays\s+inn\b", ("WYNDHAM", "DAYS_INN")),
    (r"\bsuper\s?8\b", ("WYNDHAM", "SUPER8")),
    (r"\bramada\b", ("WYNDHAM", "RAMADA")),
    (r"\bhoward\s+johnson\b|\bhojo\b", ("WYNDHAM", "HOJO")),
    (r"\btravel\s?lodge\b", ("WYNDHAM", "TRAVELODGE")),
    (r"\bbaymont\b", ("WYNDHAM", "BAYMONT")),
    (r"\bla\s+quinta\b", ("WYNDHAM", "LA_QUINTA")),
    (r"\bwingate\b", ("WYNDHAM", "WINGATE")),
    (r"\bmicrotel\b", ("WYNDHAM", "MICROTEL")),
    (r"\btryp\b", ("WYNDHAM", "TRYP")),
    (r"\bhawthorn\b", ("WYNDHAM", "HAWTHORN")),
    (r"\bknights\s+inn\b", ("WYNDHAM", "KNIGHTS")),
    (r"\bclub\s+wyndham\b|\bworldmark\b|\bwyndham\s+vacation", ("WYNDHAM_VACATION", "CLUB_WYNDHAM")),
    (r"\bwyndham\s+grand\b", ("WYNDHAM", "WYNDHAM_GRAND")),
    (r"\bwyndham\b", ("WYNDHAM", "WYNDHAM")),
    (r"\bsurestay\b", ("BEST_WESTERN", "SURESTAY")),
    (r"\bbest\s+western\b", ("BEST_WESTERN", "BEST_WESTERN")),
    (r"\bmotel\s?6\b", ("G6", "MOTEL6")),
    (r"\bstudio\s?6\b", ("G6", "STUDIO6")),
    (r"\bred\s+roof\b", ("RED_ROOF", "RED_ROOF")),
    (r"\bhome\s?towne\b", ("RED_ROOF", "HOMETOWNE")),
    (r"\bextended\s+stay\s*america\b|\bextended\s+stayamerica\b", ("ESA", "ESA")),
    (r"\bintown\b", ("INTOWN", "INTOWN")),
    (r"\bsonesta\b", ("SONESTA", "SONESTA")),
    (r"\bloews\b", ("LOEWS", "LOEWS")),
    (r"\bomni\b", ("OMNI", "OMNI")),
    (r"\bradisson\b|\bcountry\s+inn\b|\bpark\s+inn\b", ("CHOICE_RADISSON", "RADISSON")),
    (r"\bdrury\b", ("DRURY", "DRURY")),
    (r"\bmelia\b", ("MELIA", "MELIA")),
    (r"\bwestgate\b", ("WESTGATE", "WESTGATE")),
    (r"\bbluegreen\b", ("BLUEGREEN", "BLUEGREEN")),
    (r"\bdiamond\s+resorts\b", ("HILTON_VACATION", "DIAMOND")),
    (r"\bmy\s+place\b", ("MYPLACE", "MYPLACE")),
    (r"\boyo\b", ("OYO", "OYO")),
    (r"\bmargaritaville\b", ("MARGARITAVILLE", "MARGARITAVILLE")),
    (r"\bb\s?&\s?b\s+hotels?\b", ("BB_HOTELS", "BB_HOTELS")),
    (r"\bstayable\b", ("STAYABLE", "STAYABLE")),
    (r"\bred\s+carpet\s+inn\b|\bscottish\s+inn\b|\bamericas?'?s?\s+best\s+value\b|\bmasters\s+inn\b", ("REDLION_HOSPITALITY", "ECONOMY_FRANCHISE")),
    (r"\bred\s+lion\b", ("REDLION_HOSPITALITY", "RED_LION")),
    (r"\bsiegel\b", ("SIEGEL", "SIEGEL")),
]
_COMPILED = [(re.compile(p, re.I), v) for p, v in BRAND_PATTERNS]


def brands_in(name):
    """All (family, sub) brands named, in order found (a dual-brand name yields two)."""
    found = []
    text = (name or "")
    for rx, v in _COMPILED:
        if rx.search(text) and v not in found:
            if v[1] in ("HILTON", "MARRIOTT", "WYNDHAM", "HYATT") and any(f[0].split("_")[0] == v[0] for f in found):
                continue
            if v[1] == "HOLIDAY_INN" and any(f[1] in ("HIEX", "HICV") for f in found):
                continue
            if v[1] == "BEST_WESTERN" and any(f[1] == "SURESTAY" for f in found):
                continue
            found.append(v)
    return found


def primary_brand(name):
    b = brands_in(name)
    return b[0] if b else None


def brand_conflict(a, b):
    """True when both names carry a brand and the sub-brand sets are disjoint."""
    la, lb = brands_in(a), brands_in(b)
    ba, bb = {x[1] for x in la}, {x[1] for x in lb}
    if not ba or not bb:
        return False
    if ba & bb:
        return False
    parents = {"HILTON", "MARRIOTT", "WYNDHAM", "HYATT"}
    shared_family = {x[0] for x in la} & {x[0] for x in lb}
    if (ba <= parents or bb <= parents) and shared_family:
        return False
    return True


GEO_TOKENS = set("""TAMPA CLEARWATER PETERSBURG ST SAINT BEACH BEACHES DOWNTOWN NORTH SOUTH EAST WEST AIRPORT WESTSHORE YBOR BRANDON OLDSMAR LARGO DUNEDIN
PALM HARBOR SAFETY TARPON SPRINGS WESLEY CHAPEL RIVERVIEW APOLLO RUSKIN PLANT CITY TEMPLE TERRACE NEW SUNCOAST PARKWAY FL FLORIDA MALL BAY WATER STREET
CHANNELSIDE MIDTOWN CASINO FAIRGROUNDS USF UNIVERSITY MEDICAL CENTER SUITES SUITE INN HOTEL HOTELS RESORT RESORTS SPA COLLECTION LLC INC LTD TRS A AND THE AT
BY OF ON IN NEAR AREA SEMINOLE PINELLAS PARK GULFPORT ISLAND TIERRA VERDE REDINGTON MADEIRA INDIAN ROCKS SHORES TREASURE VETERANS EXPRESSWAY FLETCHER SABAL PARK""".split())


def core_tokens(name):
    n = (name or "").upper().replace("&", " ")
    n = re.sub(r"[^A-Z0-9 ]", " ", n)
    return [t for t in n.split() if t not in GEO_TOKENS]


def core_sim(a, b):
    ta, tb = set(core_tokens(a)), set(core_tokens(b))
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


#: Dual-brand concepts that are genuinely two hotels sharing one building / licence.
DUAL_BRAND_PAIRS = {frozenset(p) for p in [
    ("HOLIDAY_INN", "CANDLEWOOD"), ("EVEN", "STAYBRIDGE"), ("HILTON_GARDEN_INN", "HOME2"), ("HAMPTON", "HOME2"),
    ("RESIDENCE_INN", "SPRINGHILL"), ("SPRINGHILL", "TOWNEPLACE"), ("COURTYARD", "RESIDENCE_INN"), ("ALOFT", "ELEMENT"),
    ("HIEX", "STAYBRIDGE"), ("HIEX", "CANDLEWOOD"), ("FAIRFIELD", "TOWNEPLACE"), ("HAMPTON", "HOMEWOOD"), ("HILTON_GARDEN_INN", "HOMEWOOD"),
    ("TRU", "HOME2"), ("MOTEL6", "STUDIO6"), ("RED_ROOF", "HOMETOWNE"), ("HYATT_PLACE", "HYATT_HOUSE"),
]}


# ==========================================================================
# classify
# ==========================================================================

#: Tampa Bay is not a theme-park-vacation-ownership destination the way Orlando is;
#: named timeshare/fractional operators are matched generically by brand vocabulary
#: rather than by a long list of specific resort names (kept narrow deliberately --
#: an over-broad name list risks excluding a genuine hotel that merely shares a word).
TIMESHARE_RX = re.compile(r"\b(bluegreen|westgate|marriott vacation club|marriott'?s (?!water)|vistana|hilton grand vacations|hilton vacation club|club wyndham|worldmark|wyndham vacation|holiday inn club vacations|diamond resorts|vacation village|fractional ownership|vacation ownership)\b", re.I)
VACATION_RENTAL_RX = re.compile(r"\b(airbnb|vrbo|vacation rentals?|holiday home|beach house rentals?|condo rentals?|resort rentals?|vacation homes?|villa rentals?|property management)\b", re.I)
NON_HOTEL_RX = re.compile(r"\b(rv (park|resort)|campground|fish camp|marina\b(?!.*hotel)|wedding venue|ballroom rental|group sales office|assisted living|alf\b|independent living|senior living|apartments?\s+(homes?|community)|student housing|self storage|storage facility)\b", re.I)
#: MacDill Air Force Base and other government/military lodging is not open public accommodation.
RESTRICTED_RX = re.compile(r"\bmacdill\b|\bair force\b|\bnaval\b(?!\s+air museum)|\bnavy\b|\barmy\b|\bcoast guard\b|\bveterans affairs\b|\bva medical\b", re.I)
#: Named condo-hotel / resort-residence operations where public hotel status needs proof, not assumption.
CONDO_HOTEL_NAMES = re.compile(r"\b(sailport waterfront suites|sunset vistas|regatta beach club|shephe?rd'?s beach resort)\b", re.I)


UNIT_NAME_RX = re.compile(r"^\s*(unit|villa|condo)\s+\d+\s*$", re.I)


def classify(ident_names, licence_ranks, units, sources=()):
    names = " | ".join(ident_names)
    if not licence_ranks and all(UNIT_NAME_RX.match(n or "") for n in ident_names[1:] or ident_names):
        return "VACATION_RENTAL", "individual numbered unit (OSM apartment/guest_house); no DBPR hotel/motel licence"
    has_hotel_licence = any(r in ("HOTL", "MOTL") for r in licence_ranks)
    only_tapt = licence_ranks and all(r == "TAPT" for r in licence_ranks)
    only_bnb = licence_ranks and all(r == "BNB" for r in licence_ranks)
    if RESTRICTED_RX.search(names):
        return "RESTRICTED_NON_PUBLIC", "restricted-access / military lodging (name rule)"
    if only_bnb:
        return "NON_HOTEL_BNB", "DBPR BNB licence class (bed & breakfast; out of current category)"
    if only_tapt:
        if units <= 4:
            return "VACATION_RENTAL", "DBPR TAPT licence with <=4 units (individual transient apartment unit)"
        return "NON_HOTEL", "DBPR TAPT (transient apartment) licence; apartment-community operation, not a hotel"
    if TIMESHARE_RX.search(names):
        return ("MIXED_RESORT_HOLD" if has_hotel_licence else "TIMESHARE"), "vacation-ownership name rule" + (" + public hotel licence" if has_hotel_licence else "; no DBPR hotel/motel licence")
    if not has_hotel_licence and VACATION_RENTAL_RX.search(names):
        return "VACATION_RENTAL", "vacation-rental / condo-rental name rule; no DBPR hotel/motel licence"
    if NON_HOTEL_RX.search(names) and not has_hotel_licence:
        return "NON_HOTEL", "non-hotel name rule; no DBPR hotel/motel licence"
    if has_hotel_licence:
        return "HOTEL", "DBPR HOTL/MOTL public lodging licence"
    if CONDO_HOTEL_NAMES.search(names):
        return "MIXED_RESORT_HOLD", "condo-hotel / resort-residence operation without a DBPR hotel/motel licence; public hotel operation unproven"
    srcs = set(sources)
    if srcs <= {"OSM"}:
        return "REVIEW_NO_LICENSE", "OSM-only lodging lead with no active DBPR hotel/motel licence located (possible closure, rename or unlicensed)"
    return "REVIEW_NO_LICENSE", "no DBPR hotel/motel licence located for this lead"


# ==========================================================================
# geography
#
# Decision (PHASE 3, documented again in the FINAL report): Tampa, St.
# Petersburg and Clearwater/Clearwater Beach are built as ONE Tampa Bay market
# with strong, separately-identified corridors (not merged into a generic
# blob, not split into standalone markets yet). Basis: Florida's own DBPR
# district grouping treats Hillsborough and Pinellas as one lodging-licence
# district (District 3); the two CVBs (Visit Tampa Bay, Visit St Pete-
# Clearwater) both market to the same out-of-state traveler as "Tampa Bay";
# and real corridor-level hotel density on both sides of the bay (Tampa 188,
# St Petersburg ~80, Clearwater/Clearwater Beach ~120 DBPR HOTL/MOTL licences)
# supports named, separately-navigable corridors rather than a merged label.
# Standalone-market optionality is preserved: every corridor below is a
# distinct, separately identified unit that a future order could repartition
# into its own market without re-doing identity work.
# ==========================================================================

CITY_CLASS = {
    # CORE -- Tampa (sub-corridor requires coordinates; city-only leads with no
    # coordinate match are admitted CORE with corridor=None -> geography hold,
    # never guessed).
    "TAMPA": "CORE",
    # CORE -- Clearwater / Clearwater Beach
    "CLEARWATER": "CORE", "CLEARWATER BEACH": "CORE", "CLEARWATER BCH": "CORE",
    # CORE -- St. Petersburg (mainland downtown + city generally; sub-assigned by box)
    "ST PETERSBURG": "CORE", "ST. PETERSBURG": "CORE", "SAINT PETERSBURG": "CORE", "ST PETE": "CORE", "ST. PETERSBERG": "CORE",
    # CORE -- St Pete Beach / Gulf Beaches barrier-island strip
    "ST PETE BEACH": "CORE", "ST. PETE BEACH": "CORE", "ST.PETE BEACH": "CORE", "ST PETE BCH": "CORE",
    "SAINT PETERSBURG BEACH": "CORE", "ST PETERSBURG BEACH": "CORE", "SAINT PETERSBURG BCH": "CORE",
    "TREASURE ISLAND": "CORE", "MADEIRA BEACH": "CORE", "INDIAN ROCKS BEACH": "CORE", "INDIAN ROCKS BCH": "CORE",
    "INDIAN SHORES": "CORE", "REDINGTON SHORES": "CORE", "REDINGTON BEACH": "CORE",
    "NORTH REDINGTON BEACH": "CORE", "NORTH REDINGTON BEAC": "CORE", "N REDINGTON BCH": "CORE",
    "BELLEAIR BEACH": "CORE", "BELLEAIR": "CORE", "TIERRA VERDE": "CORE", "GULFPORT": "CORE",
    # CORRIDOR -- strong evaluation, admitted
    "BRANDON": "CORRIDOR", "SEFFNER": "CORRIDOR", "TEMPLE TERRACE": "CORRIDOR",
    "LARGO": "CORRIDOR", "SEMINOLE": "CORRIDOR", "PINELLAS PARK": "CORRIDOR",
    "DUNEDIN": "CORRIDOR", "PALM HARBOR": "CORRIDOR", "SAFETY HARBOR": "CORRIDOR", "OLDSMAR": "CORRIDOR",
    "TARPON SPGS": "CORRIDOR", "TARPON SPRINGS": "CORRIDOR",
    "LUTZ": "CORRIDOR",
    # FRINGE -- careful evaluation, admitted as fringe
    "WESLEY CHAPEL": "FRINGE",
    "RIVERVIEW": "FRINGE", "APOLLO BEACH": "FRINGE", "RUSKIN": "FRINGE", "GIBSONTON": "FRINGE", "SUN CITY CENTER": "FRINGE", "DOVER": "FRINGE",
    "PLANT CITY": "FRINGE",
    # OUTSIDE / not automatically absorbed
    "ZEPHYRHILLS": "OUTSIDE", "PORT RICHEY": "OUTSIDE", "NEW PORT RICHEY": "OUTSIDE", "HUDSON": "OUTSIDE",
    "DADE CITY": "OUTSIDE", "LAND O' LAKES": "OUTSIDE", "LAND O LAKES": "OUTSIDE", "HOLIDAY": "OUTSIDE",
    "TRINITY": "OUTSIDE", "ODESSA": "OUTSIDE", "SPRING HILL": "OUTSIDE", "BROOKSVILLE": "OUTSIDE",
    "LAKELAND": "OUTSIDE", "WINTER HAVEN": "OUTSIDE", "BARTOW": "OUTSIDE", "SARASOTA": "OUTSIDE", "BRADENTON": "OUTSIDE",
    "ANNA MARIA": "OUTSIDE", "ELLENTON": "OUTSIDE",
}

CORRIDORS = [
    # id, label, class
    ("downtown-tampa-riverwalk", "Downtown Tampa & the Riverwalk", "CORE"),
    ("ybor-city", "Ybor City", "CORE"),
    ("westshore-airport-rocky-point", "Westshore, Tampa International Airport (TPA) & Rocky Point", "CORE"),
    ("busch-gardens-usf", "Busch Gardens & USF", "CORE"),
    ("brandon", "Brandon", "CORRIDOR"),
    ("new-tampa-tampa-palms-lutz", "New Tampa, Tampa Palms & Lutz", "CORRIDOR"),
    ("wesley-chapel", "Wesley Chapel", "FRINGE"),
    ("south-hillsborough-riverview-apollo-beach", "South Hillsborough (Riverview, Apollo Beach, Ruskin, Sun City Center)", "FRINGE"),
    ("plant-city", "Plant City", "FRINGE"),
    ("clearwater-beach", "Clearwater Beach", "CORE"),
    ("downtown-clearwater", "Downtown Clearwater", "CORE"),
    ("downtown-st-petersburg", "Downtown St. Petersburg", "CORE"),
    ("st-pete-beach-gulf-beaches", "St. Pete Beach & the Gulf Beaches (Treasure Island, Madeira Beach, Indian Rocks Beach)", "CORE"),
    ("mid-pinellas", "Mid-Pinellas (Largo, Seminole, Pinellas Park, Gulfport)", "CORRIDOR"),
    ("north-pinellas", "North Pinellas (Dunedin, Palm Harbor, Safety Harbor, Oldsmar)", "CORRIDOR"),
    ("tarpon-springs", "Tarpon Springs", "CORRIDOR"),
]
CORRIDOR_LABEL = {c[0]: c[1] for c in CORRIDORS}
CORRIDOR_CLASS = {c[0]: c[2] for c in CORRIDORS}

#: Used ONLY when an identity has no coordinates in any lane. Each ZIP maps to
#: the corridor its hotels overwhelmingly occupy; the rule that fired is
#: recorded on the row.
ZIP_FALLBACK = {
    "33602": "downtown-tampa-riverwalk", "33603": "downtown-tampa-riverwalk", "33606": "downtown-tampa-riverwalk",
    "33605": "ybor-city",
    "33607": "westshore-airport-rocky-point", "33609": "westshore-airport-rocky-point", "33614": "westshore-airport-rocky-point",
    "33611": "westshore-airport-rocky-point", "33616": "westshore-airport-rocky-point",
    "33612": "busch-gardens-usf", "33613": "busch-gardens-usf", "33617": "busch-gardens-usf", "33620": "busch-gardens-usf",
    "33637": "new-tampa-tampa-palms-lutz", "33647": "new-tampa-tampa-palms-lutz", "33548": "new-tampa-tampa-palms-lutz", "33558": "new-tampa-tampa-palms-lutz",
    "33510": "brandon", "33511": "brandon",
    "33543": "wesley-chapel", "33544": "wesley-chapel", "33545": "wesley-chapel",
    "33569": "south-hillsborough-riverview-apollo-beach", "33578": "south-hillsborough-riverview-apollo-beach",
    "33579": "south-hillsborough-riverview-apollo-beach", "33570": "south-hillsborough-riverview-apollo-beach", "33573": "south-hillsborough-riverview-apollo-beach",
    "33563": "plant-city", "33565": "plant-city", "33566": "plant-city", "33567": "plant-city",
    "33767": "clearwater-beach",
    "33755": "downtown-clearwater", "33756": "downtown-clearwater", "33759": "downtown-clearwater", "33760": "downtown-clearwater",
    "33761": "downtown-clearwater", "33762": "downtown-clearwater", "33763": "downtown-clearwater", "33764": "downtown-clearwater", "33765": "downtown-clearwater",
    "33701": "downtown-st-petersburg", "33705": "downtown-st-petersburg", "33701": "downtown-st-petersburg",
    "33702": "downtown-st-petersburg", "33703": "downtown-st-petersburg", "33704": "downtown-st-petersburg",
    "33712": "downtown-st-petersburg", "33713": "downtown-st-petersburg", "33716": "downtown-st-petersburg",
    "33706": "st-pete-beach-gulf-beaches", "33708": "st-pete-beach-gulf-beaches", "33715": "st-pete-beach-gulf-beaches",
    "33770": "mid-pinellas", "33771": "mid-pinellas", "33773": "mid-pinellas", "33774": "mid-pinellas", "33776": "mid-pinellas", "33777": "mid-pinellas", "33778": "mid-pinellas", "33707": "mid-pinellas",
    "34677": "north-pinellas", "34683": "north-pinellas", "34684": "north-pinellas", "34685": "north-pinellas", "34695": "north-pinellas", "34698": "north-pinellas",
    "34689": "tarpon-springs", "34688": "tarpon-springs",
}

ANCHORS = {
    "downtown_tampa": (27.9478, -82.4584), "ybor": (27.9659, -82.4370), "westshore": (27.9556, -82.5183),
    "airport": (27.9755, -82.5332), "rocky_point": (27.9720, -82.5490), "busch_gardens": (28.0378, -82.4199),
    "usf": (28.0587, -82.4139), "temple_terrace": (28.0353, -82.3899), "brandon": (27.9378, -82.2860),
    "new_tampa": (28.1280, -82.4020), "clearwater_beach": (27.9775, -82.8288), "downtown_clearwater": (27.9659, -82.7999),
    "downtown_stpete": (27.7730, -82.6389), "st_pete_beach": (27.7241, -82.7420), "treasure_island": (27.7667, -82.7671),
    "largo": (27.9095, -82.7873), "dunedin": (28.0186, -82.7748), "tarpon_springs": (28.1461, -82.7568),
    "wesley_chapel": (28.2364, -82.3178), "riverview": (27.8663, -82.3226), "plant_city": (28.0189, -82.1129),
}


def dist_km(a, b):
    r = 6371.0
    p1, p2 = math.radians(a[0]), math.radians(b[0])
    dp, dl = p2 - p1, math.radians(b[1] - a[1])
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


def city_norm(city):
    c = " ".join((city or "").upper().replace(".", ". ").split()).replace(". ", ".")
    c = re.sub(r"\.$", "", c)
    fixes = {
        "ST.PETE BEACH": "ST PETE BEACH", "ST.PETERSBURG": "ST PETERSBURG",
        "SAINT PETERSBURG": "ST PETERSBURG", "ST.PETERSBERG": "ST PETERSBURG", "TARPON SPGS": "TARPON SPRINGS",
    }
    return fixes.get(c, c)


def assign(city, postal, lat, lng):
    """(geography_class, corridor_id or None, rule)."""
    c = city_norm(city)
    klass = CITY_CLASS.get(c)
    if klass == "OUTSIDE":
        return "OUTSIDE", None, "CITY_OUTSIDE:%s" % c
    if lat is None:
        z = ZIP_FALLBACK.get(postal)
        if z:
            return CORRIDOR_CLASS[z], z, "ZIP_FALLBACK_NO_COORDINATES:%s" % postal
        # single-corridor cities need no coordinates at all
        SINGLE = {
            "BRANDON": "brandon", "SEFFNER": "brandon", "WESLEY CHAPEL": "wesley-chapel", "PLANT CITY": "plant-city",
            "RIVERVIEW": "south-hillsborough-riverview-apollo-beach", "APOLLO BEACH": "south-hillsborough-riverview-apollo-beach",
            "RUSKIN": "south-hillsborough-riverview-apollo-beach", "GIBSONTON": "south-hillsborough-riverview-apollo-beach",
            "SUN CITY CENTER": "south-hillsborough-riverview-apollo-beach", "DOVER": "south-hillsborough-riverview-apollo-beach",
            "CLEARWATER BEACH": "clearwater-beach", "CLEARWATER BCH": "clearwater-beach", "CLEARWATER": "downtown-clearwater",
            "TARPON SPRINGS": "tarpon-springs", "TARPON SPGS": "tarpon-springs", "DUNEDIN": "north-pinellas",
            "PALM HARBOR": "north-pinellas", "SAFETY HARBOR": "north-pinellas", "OLDSMAR": "north-pinellas",
            "LARGO": "mid-pinellas", "SEMINOLE": "mid-pinellas", "PINELLAS PARK": "mid-pinellas", "GULFPORT": "mid-pinellas", "BELLEAIR": "mid-pinellas",
            "TEMPLE TERRACE": "busch-gardens-usf", "LUTZ": "new-tampa-tampa-palms-lutz",
            "TREASURE ISLAND": "st-pete-beach-gulf-beaches", "MADEIRA BEACH": "st-pete-beach-gulf-beaches",
            "INDIAN ROCKS BEACH": "st-pete-beach-gulf-beaches", "INDIAN ROCKS BCH": "st-pete-beach-gulf-beaches",
            "INDIAN SHORES": "st-pete-beach-gulf-beaches", "REDINGTON SHORES": "st-pete-beach-gulf-beaches",
            "REDINGTON BEACH": "st-pete-beach-gulf-beaches", "NORTH REDINGTON BEACH": "st-pete-beach-gulf-beaches",
            "NORTH REDINGTON BEAC": "st-pete-beach-gulf-beaches", "N REDINGTON BCH": "st-pete-beach-gulf-beaches",
            "BELLEAIR BEACH": "st-pete-beach-gulf-beaches", "TIERRA VERDE": "st-pete-beach-gulf-beaches",
            "ST PETE BEACH": "st-pete-beach-gulf-beaches", "ST PETE BCH": "st-pete-beach-gulf-beaches",
            "SAINT PETERSBURG BEACH": "st-pete-beach-gulf-beaches", "ST PETERSBURG BEACH": "st-pete-beach-gulf-beaches",
            "SAINT PETERSBURG BCH": "st-pete-beach-gulf-beaches",
        }
        cid = SINGLE.get(c)
        if cid:
            return CORRIDOR_CLASS[cid], cid, "CITY_SINGLE_CORRIDOR_NO_COORDINATES:%s" % c
        return (klass or "UNKNOWN"), None, "NO_COORDINATES"
    p = (lat, lng)
    # hard outside envelope (Tampa Bay basin)
    if not (27.55 <= lat <= 28.35 and -82.85 <= lng <= -82.15):
        return "OUTSIDE", None, "OUTSIDE_ENVELOPE"
    # Gulf beach barrier islands (west of the Intracoastal, Pinellas)
    if lng <= -82.72 and 27.70 <= lat <= 27.90:
        return "CORE", "st-pete-beach-gulf-beaches", "GULF_BEACHES_BOX"
    if lng <= -82.76 and 27.90 <= lat <= 27.99:
        return "CORE", "clearwater-beach", "CLEARWATER_BEACH_BOX"
    # St. Petersburg downtown / mainland
    if 27.73 <= lat <= 27.83 and -82.68 <= lng <= -82.60:
        return "CORE", "downtown-st-petersburg", "STPETE_DOWNTOWN_BOX"
    if 27.70 <= lat <= 27.87 and -82.72 < lng <= -82.60:
        return "CORE", "downtown-st-petersburg", "STPETE_METRO_BOX"
    # Mid / North Pinellas
    if 27.86 <= lat <= 27.93 and -82.82 <= lng <= -82.70:
        return "CORRIDOR", "mid-pinellas", "MID_PINELLAS_BOX"
    if 28.12 <= lat <= 28.17 and -82.79 <= lng <= -82.72:
        return "CORRIDOR", "tarpon-springs", "TARPON_SPRINGS_BOX"
    if 27.96 <= lat < 28.12 and -82.80 <= lng <= -82.65:
        return "CORRIDOR", "north-pinellas", "NORTH_PINELLAS_BOX"
    if dist_km(p, ANCHORS["downtown_clearwater"]) < 4.5:
        return "CORE", "downtown-clearwater", "DOWNTOWN_CLEARWATER_ANCHOR"
    # Hillsborough east / south
    if lat < 27.90 and lng > -82.40:
        if lng > -82.20:
            return "FRINGE", "plant-city", "PLANT_CITY_BOX"
        return "FRINGE", "south-hillsborough-riverview-apollo-beach", "SOUTH_HILLSBOROUGH_BOX"
    if 27.90 <= lat <= 27.97 and -82.35 <= lng <= -82.20:
        return "CORRIDOR", "brandon", "BRANDON_BOX"
    if lat > 28.15:
        return "FRINGE", "wesley-chapel", "WESLEY_CHAPEL_BOX"
    if lat > 28.08 and lng > -82.45:
        return "CORRIDOR", "new-tampa-tampa-palms-lutz", "NEW_TAMPA_BOX"
    # Tampa city anchors
    if dist_km(p, ANCHORS["ybor"]) < 2.2:
        return "CORE", "ybor-city", "YBOR_ANCHOR"
    if dist_km(p, ANCHORS["downtown_tampa"]) < 3.0:
        return "CORE", "downtown-tampa-riverwalk", "DOWNTOWN_TAMPA_ANCHOR"
    if dist_km(p, ANCHORS["airport"]) < 3.5 or dist_km(p, ANCHORS["westshore"]) < 3.0 or dist_km(p, ANCHORS["rocky_point"]) < 2.5:
        return "CORE", "westshore-airport-rocky-point", "WESTSHORE_AIRPORT_ANCHOR"
    if dist_km(p, ANCHORS["busch_gardens"]) < 3.5 or dist_km(p, ANCHORS["usf"]) < 3.0 or dist_km(p, ANCHORS["temple_terrace"]) < 2.5:
        return "CORE", "busch-gardens-usf", "BUSCH_GARDENS_USF_ANCHOR"
    # remaining Tampa city fallback: admitted CORE, corridor left for the
    # nearest anchor rather than an unassigned hold, since every lead here has
    # coordinates and lies within Tampa city proper.
    cands = [("downtown-tampa-riverwalk", dist_km(p, ANCHORS["downtown_tampa"])), ("westshore-airport-rocky-point", dist_km(p, ANCHORS["westshore"])),
             ("busch-gardens-usf", dist_km(p, ANCHORS["usf"])), ("ybor-city", dist_km(p, ANCHORS["ybor"])),
             ("new-tampa-tampa-palms-lutz", dist_km(p, ANCHORS["new_tampa"])), ("brandon", dist_km(p, ANCHORS["brandon"]))]
    cands.sort(key=lambda t: t[1])
    return "CORE", cands[0][0], "TAMPA_NEAREST_ANCHOR_%.1fKM" % cands[0][1]
