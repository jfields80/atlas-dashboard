"""PTF-ORLANDO-FL-PARALLEL-SOURCE-READY-001 -- Orlando-owned identity rules.

Address normalisation, brand vocabulary, lodging-category classification and
Greater Orlando geography used ONLY by the orlando-fl shadow build. Nothing here
is imported by, or changes, any shared factory module.
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
    (r"\bIRLO BRONSON( MEMORIAL| MEM)?( HWY| HIGHWAY)?( 192)?\b", "IRLO192"), (r"\b(US|U S|W|E)?\s*(HWY|HIGHWAY)\s*192\b", "IRLO192"), (r"\bUS 192\b", "IRLO192"),
    (r"\bSTATE (ROAD|RD) (\d+)\b", r"SR\2"), (r"\bSR (\d+)\b", r"SR\1"), (r"\bFL-(\d+)\b", r"SR\1"),
    (r"\b(US|U S) (HWY|HIGHWAY) (\d+)\b", r"US\3"), (r"\bUS (\d+)\b", r"US\1"), (r"\b(HWY|HIGHWAY) (\d+)\b", r"US\2"), (r"\bUS-(\d+)\b", r"US\1"),
    (r"\bINT'?L\b", "INTERNATIONAL"), (r"\bINTL\b", "INTERNATIONAL"), (r"\bI DRIVE\b", "INTERNATIONAL DR"), (r"\bAMERCIAN\b", "AMERICAN"),
    (r"\bJAMACIAN\b", "JAMAICAN"), (r"\bSANDLAKE\b", "SAND LAKE"), (r"\bCENTERIEW\b", "CENTERVIEW"), (r"\bMARBELLA PALMS\b", "MARBELLA PALM"),
    (r"\bEPCOT RESORTS\b", "EPCOT RESORT"), (r"\bSEA HARBOUR\b", "SEA HARBOR"), (r"\bPOLYNESIAN ISLES\b", "POLYNESIAN ISLE"), (r"\bORANGE BLOSSM\b", "ORANGE BLOSSOM"),
    (r"\bT\.? ?G\.? LEE\b", "TG LEE"), (r"\bCOLONIAL TOWNPARK\b", "COLONIAL TOWN PARK"), (r"\bST\.\b", "ST"),
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
    # numeric route equivalence e.g. IRLO192
    return False


GENERIC_NAME = {"HOTEL", "HOTELS", "INN", "SUITES", "SUITE", "AND", "THE", "BY", "AT", "OF", "&", "ORLANDO", "RESORT", "RESORTS", "LLC", "INC", "A", "AN", "FL", "FLORIDA",
                "MARRIOTT", "HILTON", "WYNDHAM", "IHG", "COLLECTION", "NEAR", "AREA", "IN", "ON", "-", "/", "EXTENDED", "STAY"}


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
# brands
# ==========================================================================

# ordered: longer / more specific patterns first. value = (family, sub-brand)
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
    (r"\bcity\s+express\b", ("MARRIOTT", "CITY_EXPRESS")),
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
    (r"\brosen\b", ("ROSEN", "ROSEN")),
    (r"\bloews\b|\bportofino\b|\bporto\s+fino\b|\broyal\s+pacific\b|\bsapphire\s+falls\b|\bhard\s+rock\s+hotel\b", ("UNIVERSAL_LOEWS", "LOEWS")),
    (r"\bomni\b", ("OMNI", "OMNI")),
    (r"\bradisson\b|\bcountry\s+inn\b|\bpark\s+inn\b", ("CHOICE_RADISSON", "RADISSON")),
    (r"\bdrury\b", ("DRURY", "DRURY")),
    (r"\bmelia\b", ("MELIA", "MELIA")),
    (r"\bwestgate\b", ("WESTGATE", "WESTGATE")),
    (r"\bbluegreen\b", ("BLUEGREEN", "BLUEGREEN")),
    (r"\bdiamond\s+resorts\b", ("HILTON_VACATION", "DIAMOND")),
    (r"\bdisney(?:'|`|\u2019)s\b", ("DISNEY", "DISNEY")),
    (r"\buniversal\b.*\bresort\b|\bendless\s+summer\b|\bcabana\s+bay\b|\baventura\s+hotel\b|\bhelios\b|\bstella\s+nova\b|\bterra\s+luna\b", ("UNIVERSAL", "UNIVERSAL")),
    (r"\bmy\s+place\b", ("MYPLACE", "MYPLACE")),
    (r"\boyo\b", ("OYO", "OYO")),
    (r"\bmargaritaville\b", ("MARGARITAVILLE", "MARGARITAVILLE")),
    (r"\bb\s?&\s?b\s+hotels?\b", ("BB_HOTELS", "BB_HOTELS")),
    (r"\bstayable\b", ("STAYABLE", "STAYABLE")),
    (r"\bred\s+carpet\s+inn\b|\bscottish\s+inn\b|\bamericas?'?s?\s+best\s+value\b|\bmasters\s+inn\b", ("REDLION_HOSPITALITY", "ECONOMY_FRANCHISE")),
    (r"\bred\s+lion\b", ("REDLION_HOSPITALITY", "RED_LION")),
    (r"\bsiegel\b", ("SIEGEL", "SIEGEL")),
    (r"\bcaribe\s+royale\b", ("CARIBE", "CARIBE")),
]
_COMPILED = [(re.compile(p, re.I), v) for p, v in BRAND_PATTERNS]


def brands_in(name):
    """All (family, sub) brands named, in order found (a dual-brand name yields two)."""
    found = []
    text = (name or "")
    for rx, v in _COMPILED:
        if rx.search(text) and v not in found:
            # suppress generic parent when a sub-brand of the same family already matched
            if v[1] in ("HILTON", "MARRIOTT", "WYNDHAM", "HYATT") and any(f[0].split("_")[0] == v[0] for f in found):
                continue
            if v[1] == "HOLIDAY_INN" and any(f[1] in ("HIEX", "HICV") for f in found):
                continue
            if v[1] == "BEST_WESTERN" and any(f[1] == "SURESTAY" for f in found):
                continue
            if v[1] == "MVC" and re.search(r"marriott'?s\s+orlando\s+world\s+cent", text, re.I):
                v = ("MARRIOTT", "MARRIOTT")
                if v in found:
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
    # a bare parent brand ("Marriott Village", "Hyatt") does not conflict with its own sub-brands
    if (ba <= parents or bb <= parents) and shared_family:
        return False
    return True


GEO_TOKENS = set("""ORLANDO LAKE BUENA VISTA LBV KISSIMMEE INTERNATIONAL DRIVE DR IDRIVE I CONVENTION CENTER CENTRE UNIVERSAL SEAWORLD SEA WORLD DISNEY SPRINGS
AIRPORT MCO DOWNTOWN NORTH SOUTH EAST WEST MAINGATE MAIN GATE THEME PARKS PARK AREA NEAR CELEBRATION ALTAMONTE MAITLAND UCF MARY SANFORD FLORIDA FL MALL
CROSSINGS FLAMINGO NONA MILLENIA US 192 HWY IRLO BRONSON W E S N CLERMONT DAVENPORT SE SW NE NW APOPKA OCOEE BLVD AMERICAN WAY VINELAND ACROSS FROM
UNIVERSITY CHAMPIONSGATE CHAMPIONS REUNION ST CLOUD HAINES CITY WINTER LEE ROAD RD SOUTHPARK SOUTHEAST SOUTHWEST NEAREST TO UNIV STUDIOS
ENTRANCE WESTERN TOWN OF OFFICIAL WALT AN INTL OIA JOHN YOUNG PKWY GRANDE LAKES BONNET CREEK THE AT BY AND IN ON HOTEL HOTELS INN SUITES SUITE RESORT RESORTS
SPA COLLECTION LLC INC LTD TRS A""".split())


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

TIMESHARE_RX = re.compile(r"\b(westgate|marriott'?s (?!orlando world)|marriott vacation|vistana|hilton grand vacations|hilton vacation club|grand vacations|club wyndham|worldmark|wyndham vacation|holiday inn club|bluegreen|diamond resorts|vacation village|legacy vacation|hapimag|liki tiki|summer bay|exploria|orange lake resort|palisades resort|parc soleil|tuscany village|cypress harbour|grande vista|harbour lake|imperial palms|royal palms|sabal palms|lakeshore reserve|grand beach|star island|cypress palms|wyndham bonnet creek|the berkley|fountains resort|bluegreen fountains|mystic dunes|polynesian isles resort|seaworld resort club|orlando international resort club|sunshine resort|lake eve resort|runaway beach club|silver lake resort|parkway international resort|cane island|florida vacation villas|saratoga resort villas|vacation villas|disney'?s? old key west|saratoga springs|kidani|animal kingdom villas|riviera resort|bay lake tower|boardwalk villas|beach club villas|villas at disney|treehouse villas|copper creek|boulder ridge|polynesian villas|grand floridian.*villas|las palmeras|marriott vacation club|kingstown reef|blue tree resort|leisure resort|town center resort|vacation club|grande villas|cypress pointe resort|aqua sol|fantasy world|world ?quest)\b", re.I)
VACATION_RENTAL_RX = re.compile(r"\b(vista cay|isles at cay commons|coral cay|villas? (at|of) seven dwarfs|holiday home|airbnb|vrbo|resort rentals?|rentals?\b|vacation homes?|townhomes|villa solterra|villa relax|tuscan hills|emerald green|reunion resort|encore resort|windsor (hills|at westside)|solterra|champions ?gate (resort )?homes|storey lake|evermore orlando resort|villatel|regal oaks|sun village|oakwood at|camden|apartments?\b|apartment homes|condo|condominium|traditions at|corporate center|casa da|miss addison|robert lamothe|the palms? of|margaritaville cottages|bella vida|spectrum resort)\b", re.I)
NON_HOTEL_RX = re.compile(r"\b(rv (park|resort)|campground|fish camp|marina|wedding|ballroom|group sales|clubhouse|golf club(?! lodge)|assisted living|alf\b|superior residences|collegiate village|student|apartments|living\b|halston|domain apartments|heron lake|arcadia|westerly|overture|millennium apartments|tucker|place on millenia|valencia trace|palmer\b|liv at|community asset)\b", re.I)
RESTRICTED_RX = re.compile(r"\b(shades of green|jetblue|lake nona club|army|navy|air force)\b", re.I)
CONDO_HOTEL_NAMES = re.compile(r"\b(the point (hotel|orlando)|parc corniche|lake buena vista resort village|floridays|grove resort|blue heron beach|enclave (hotel|suites)|palms hotel (&|and) villas|avanti palms|cypress cove villas|seasons florida resort|magic moment|galleria palms|mago?ic key)\b", re.I)


UNIT_NAME_RX = re.compile(r"^\s*villa\s+\d+\s*$", re.I)


def classify(ident_names, licence_ranks, units, sources=()):
    names = " | ".join(ident_names)
    if not licence_ranks and all(UNIT_NAME_RX.match(n or "") for n in ident_names[1:] or ident_names):
        return "VACATION_RENTAL", "individual numbered villa unit (OSM guest_house); no DBPR hotel/motel licence"
    has_hotel_licence = any(r in ("HOTL", "MOTL") for r in licence_ranks)
    only_tapt = licence_ranks and all(r == "TAPT" for r in licence_ranks)
    only_bnb = licence_ranks and all(r == "BNB" for r in licence_ranks)
    if RESTRICTED_RX.search(names):
        return "RESTRICTED_NON_PUBLIC", "restricted-access lodging (name rule)"
    if only_bnb:
        return "NON_HOTEL_BNB", "DBPR BNB licence class (bed & breakfast; out of current category)"
    if only_tapt:
        if units <= 4:
            return "VACATION_RENTAL", "DBPR TAPT licence with <=4 units (individual transient apartment unit)"
        return "NON_HOTEL", "DBPR TAPT (transient apartment) licence; apartment-community operation, not a hotel"
    if TIMESHARE_RX.search(names):
        return ("MIXED_RESORT_HOLD" if has_hotel_licence else "TIMESHARE"), "vacation-ownership name rule" + (" + public hotel licence" if has_hotel_licence else "; no DBPR hotel/motel licence")
    if not has_hotel_licence and VACATION_RENTAL_RX.search(names):
        return "VACATION_RENTAL", "vacation-rental / condo / apartment name rule; no DBPR hotel/motel licence"
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
# ==========================================================================

CITY_CLASS = {
    # CORE
    "ORLANDO": "CORE", "LAKE BUENA VISTA": "CORE", "BAY LAKE": "CORE", "KISSIMMEE": "CORE", "CELEBRATION": "CORE", "BELLE ISLE": "CORE",
    # CORRIDOR (strong evaluation -> admitted)
    "WINTER PARK": "CORRIDOR", "MAITLAND": "CORRIDOR", "ALTAMONTE SPRINGS": "CORRIDOR", "ALTAMONTE": "CORRIDOR", "ALTAMONTE SPRINGSF": "CORRIDOR",
    "APOPKA": "CORRIDOR", "OCOEE": "CORRIDOR", "WINTER GARDEN": "CORRIDOR", "WINDERMERE": "CORRIDOR", "CLERMONT": "CORRIDOR", "MINNEOLA": "CORRIDOR",
    "DAVENPORT": "CORRIDOR", "CHAMPIONS GATE": "CORRIDOR", "CHAMPIONSGATE": "CORRIDOR", "REUNION": "CORRIDOR", "FOUR CORNERS": "CORRIDOR",
    "LAKE MARY": "CORRIDOR", "SANFORD": "CORRIDOR", "HEATHROW": "CORRIDOR", "LONGWOOD": "CORRIDOR", "CASSELBERRY": "CORRIDOR", "FERN PARK": "CORRIDOR",
    "OVIEDO": "CORRIDOR", "WINTER SPRINGS": "CORRIDOR",
    # FRINGE (careful evaluation -> admitted as fringe)
    "ST CLOUD": "FRINGE", "ST. CLOUD": "FRINGE", "SAINT CLOUD": "FRINGE", "POINCIANA": "FRINGE",
    # OUTSIDE / FUTURE STANDALONE
    "HAINES CITY": "OUTSIDE", "MOUNT DORA": "OUTSIDE", "MT. DORA": "OUTSIDE", "DELAND": "OUTSIDE", "LAKELAND": "OUTSIDE", "WINTER HAVEN": "OUTSIDE",
    "LEESBURG": "OUTSIDE", "LADY LAKE": "OUTSIDE", "EUSTIS": "OUTSIDE", "TAVARES": "OUTSIDE", "UMATILLA": "OUTSIDE", "ASTOR": "OUTSIDE",
    "HOWEY-IN-THE-HILLS": "OUTSIDE", "SORRENTO": "OUTSIDE", "FRUITLAND PARK": "OUTSIDE", "MASCOTTE": "OUTSIDE", "KENANSVILLE": "OUTSIDE",
    "AUBURNDALE": "OUTSIDE", "BARTOW": "OUTSIDE", "LAKE WALES": "OUTSIDE", "DUNDEE": "OUTSIDE", "LAKE ALFRED": "OUTSIDE", "BABSON PARK": "OUTSIDE",
    "STREAMSONG": "OUTSIDE", "FROSTPROOF": "OUTSIDE", "HOMELAND": "OUTSIDE", "INDIAN LAKE ESTATES": "OUTSIDE", "MULBERRY": "OUTSIDE",
    "DEBARY": "OUTSIDE", "ORANGE CITY": "OUTSIDE", "DELTONA": "OUTSIDE", "CASSADAGA": "OUTSIDE", "LAKE HELEN": "OUTSIDE", "OAKLAND": "CORRIDOR",
    "DAYTONA BEACH": "OUTSIDE", "ORMOND BEACH": "OUTSIDE", "OCALA": "OUTSIDE", "WILDWOOD": "OUTSIDE", "PLANT CITY": "OUTSIDE", "BROOKSVILLE": "OUTSIDE",
}

CORRIDORS = [
    # id, label, class, note
    ("downtown-orlando", "Downtown Orlando", "CORE"),
    ("orlando-international-airport", "Orlando International Airport (MCO) & Lake Nona", "CORE"),
    ("international-drive", "International Drive (North I-Drive / Sand Lake)", "CORE"),
    ("orange-county-convention-center", "Orange County Convention Center", "CORE"),
    ("universal-orlando", "Universal Orlando & Epic Universe", "CORE"),
    ("seaworld", "SeaWorld Orlando", "CORE"),
    ("lake-buena-vista", "Lake Buena Vista / SR-535 / Bonnet Creek", "CORE"),
    ("disney-springs", "Disney Springs Resort Area", "CORE"),
    ("walt-disney-world", "Walt Disney World Resort", "CORE"),
    ("flamingo-crossings", "Flamingo Crossings (Walt Disney World West Entrance)", "CORRIDOR"),
    ("kissimmee-us-192-maingate", "Kissimmee US-192 Maingate / Tourist Corridor", "CORE"),
    ("kissimmee-downtown-east-us-192", "Downtown Kissimmee & East US-192", "CORE"),
    ("celebration", "Celebration", "CORE"),
    ("four-corners-davenport-championsgate", "Four Corners / Davenport / ChampionsGate", "CORRIDOR"),
    ("south-orlando-florida-mall-millenia", "South Orlando (Florida Mall / OBT / Millenia)", "CORE"),
    ("east-orlando-ucf", "East Orlando / UCF", "CORE"),
    ("north-orlando-winter-park-maitland", "Winter Park / Maitland / North Orlando", "CORRIDOR"),
    ("west-orlando-ocoee-winter-garden", "West Orlando / Ocoee / Winter Garden", "CORRIDOR"),
    ("altamonte-springs-longwood", "Altamonte Springs / Longwood / Casselberry", "CORRIDOR"),
    ("lake-mary-sanford", "Lake Mary / Sanford (Orlando Sanford Intl Airport)", "CORRIDOR"),
    ("apopka", "Apopka", "CORRIDOR"),
    ("clermont", "Clermont / Minneola", "CORRIDOR"),
    ("st-cloud", "St. Cloud", "FRINGE"),
]
CORRIDOR_LABEL = {c[0]: c[1] for c in CORRIDORS}
CORRIDOR_CLASS = {c[0]: c[2] for c in CORRIDORS}

#: Used ONLY when an identity has no coordinates in any lane. Each ZIP maps to the
#: corridor its hotels overwhelmingly occupy; the rule that fired is recorded on the row.
ZIP_FALLBACK = {
    "34746": "kissimmee-us-192-maingate", "34747": "kissimmee-us-192-maingate", "34744": "kissimmee-downtown-east-us-192", "34741": "kissimmee-downtown-east-us-192",
    "33896": "four-corners-davenport-championsgate", "33897": "four-corners-davenport-championsgate", "33837": "four-corners-davenport-championsgate",
    "34714": "four-corners-davenport-championsgate", "34711": "clermont", "32750": "altamonte-springs-longwood", "32707": "altamonte-springs-longwood",
    "32701": "altamonte-springs-longwood", "32714": "altamonte-springs-longwood", "32771": "lake-mary-sanford", "32773": "lake-mary-sanford", "32746": "lake-mary-sanford",
    "32819": "international-drive", "32821": "seaworld", "32836": "lake-buena-vista", "32830": "walt-disney-world", "32801": "downtown-orlando", "32803": "downtown-orlando",
    "32822": "orlando-international-airport", "32812": "orlando-international-airport", "32827": "orlando-international-airport", "32809": "south-orlando-florida-mall-millenia",
    "32837": "south-orlando-florida-mall-millenia", "32839": "south-orlando-florida-mall-millenia", "32817": "east-orlando-ucf", "32826": "east-orlando-ucf",
    "34769": "st-cloud", "34771": "st-cloud", "34787": "west-orlando-ocoee-winter-garden", "34761": "west-orlando-ocoee-winter-garden",
}

ANCHORS = {
    "universal": (28.4745, -81.4650), "epic": (28.4382, -81.4470), "seaworld": (28.4112, -81.4619), "occc": (28.4248, -81.4690),
    "idrive_north": (28.4530, -81.4710), "downtown": (28.5419, -81.3790), "mco": (28.4312, -81.3081), "lake_nona": (28.3760, -81.2690),
    "celebration": (28.3190, -81.5420),
}


def dist_km(a, b):
    r = 6371.0
    p1, p2 = math.radians(a[0]), math.radians(b[0])
    dp, dl = p2 - p1, math.radians(b[1] - a[1])
    h = math.sin(dp / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(dl / 2) ** 2
    return 2 * r * math.asin(math.sqrt(h))


def city_norm(city):
    c = " ".join((city or "").upper().replace(".", ". ").split()).replace(". ", ".")
    c = c.replace("ST.CLOUD", "ST. CLOUD")
    return c


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
        return (klass or "UNKNOWN"), None, "NO_COORDINATES"
    p = (lat, lng)
    # hard outside envelope
    if not (28.15 <= lat <= 28.86 and -81.80 <= lng <= -81.10):
        return "OUTSIDE", None, "OUTSIDE_ENVELOPE"
    if postal == "34787" and lat < 28.40 and lng < -81.59:
        return "CORRIDOR", "flamingo-crossings", "ZIP34787_FLAMINGO_CROSSINGS_BOX"
    if postal == "32830" or c == "BAY LAKE":
        if 28.366 <= lat <= 28.392 and -81.525 <= lng <= -81.495:
            return "CORE", "disney-springs", "ZIP32830_HOTEL_PLAZA_BOX"
        return "CORE", "walt-disney-world", "ZIP32830_DISNEY_PROPERTY"
    if c in ("ST CLOUD", "ST. CLOUD", "SAINT CLOUD"):
        return "FRINGE", "st-cloud", "CITY_ST_CLOUD"
    if c in ("CELEBRATION",):
        return "CORE", "celebration", "CITY_CELEBRATION"
    if c in ("DAVENPORT", "CHAMPIONS GATE", "CHAMPIONSGATE", "REUNION", "FOUR CORNERS") or (lat < 28.37 and lng <= -81.635):
        return "CORRIDOR", "four-corners-davenport-championsgate", "FOUR_CORNERS_BOX_OR_CITY"
    if c in ("WINTER PARK", "MAITLAND"):
        return "CORRIDOR", "north-orlando-winter-park-maitland", "CITY_WINTER_PARK_MAITLAND"
    if c in ("ALTAMONTE SPRINGS", "ALTAMONTE", "ALTAMONTE SPRINGSF", "LONGWOOD", "CASSELBERRY", "FERN PARK", "OVIEDO", "WINTER SPRINGS"):
        return "CORRIDOR", "altamonte-springs-longwood", "CITY_SEMINOLE_SOUTH"
    if c in ("LAKE MARY", "SANFORD", "HEATHROW"):
        return "CORRIDOR", "lake-mary-sanford", "CITY_SEMINOLE_NORTH"
    if lat >= 28.72 and lng > -81.44:
        return "CORRIDOR", "lake-mary-sanford", "SEMINOLE_NORTH_BOX"
    if 28.655 <= lat < 28.72 and -81.44 < lng <= -81.25:
        return "CORRIDOR", "altamonte-springs-longwood", "SEMINOLE_SOUTH_BOX"
    if c == "APOPKA" or (lat > 28.64 and lng < -81.44):
        return "CORRIDOR", "apopka", "CITY_APOPKA_OR_BOX"
    if c in ("CLERMONT", "MINNEOLA") and lat > 28.45:
        return "CORRIDOR", "clermont", "CITY_CLERMONT"
    if c in ("OCOEE", "WINTER GARDEN", "OAKLAND", "WINDERMERE"):
        return "CORRIDOR", "west-orlando-ocoee-winter-garden", "CITY_WEST_ORANGE"
    # Kissimmee / US-192
    if 28.22 <= lat < 28.352 and -81.635 < lng <= -81.44 and not (lat > 28.345 and lng > -81.53):
        if dist_km(p, ANCHORS["celebration"]) < 1.2:
            return "CORE", "celebration", "CELEBRATION_ANCHOR_1.2KM"
        return "CORE", "kissimmee-us-192-maingate", "US192_WEST_BOX"
    if 28.20 <= lat < 28.345 and -81.44 < lng <= -81.25:
        return "CORE", "kissimmee-downtown-east-us-192", "KISSIMMEE_EAST_BOX"
    if c == "KISSIMMEE" and 28.15 <= lat < 28.37:
        return "CORE", ("kissimmee-downtown-east-us-192" if lng > -81.44 else "kissimmee-us-192-maingate"), "CITY_KISSIMMEE_FALLBACK"
    if 28.345 <= lat <= 28.43 and -81.62 <= lng <= -81.53:
        return "CORE", "walt-disney-world", "DISNEY_PROPERTY_BOX"
    # theme-park / convention cluster
    if dist_km(p, ANCHORS["universal"]) <= 1.9 or dist_km(p, ANCHORS["epic"]) <= 1.2:
        return "CORE", "universal-orlando", "UNIVERSAL_ANCHOR"
    if 28.345 <= lat < 28.405 and -81.53 <= lng <= -81.475:
        return "CORE", "lake-buena-vista", "LBV_535_BONNET_CREEK_BOX"
    if 28.395 <= lat <= 28.475 and -81.49 <= lng <= -81.43:
        cand = [("seaworld", dist_km(p, ANCHORS["seaworld"])), ("orange-county-convention-center", dist_km(p, ANCHORS["occc"])), ("international-drive", dist_km(p, ANCHORS["idrive_north"]))]
        cand.sort(key=lambda t: t[1])
        return "CORE", cand[0][0], "IDRIVE_ENVELOPE_NEAREST_ANCHOR"
    if 28.37 <= lat < 28.405 and -81.475 < lng <= -81.43:
        return "CORE", "seaworld", "SOUTH_IDRIVE_BOX"
    if dist_km(p, ANCHORS["downtown"]) <= 4.2:
        return "CORE", "downtown-orlando", "DOWNTOWN_ANCHOR_4.2KM"
    if (28.33 <= lat <= 28.49 and -81.345 <= lng <= -81.21):
        return "CORE", "orlando-international-airport", "MCO_LAKE_NONA_BOX"
    if 28.39 <= lat < 28.52 and -81.445 <= lng < -81.345:
        return "CORE", "south-orlando-florida-mall-millenia", "SOUTH_ORLANDO_BOX"
    if 28.50 <= lat <= 28.66 and -81.33 < lng <= -81.10:
        return "CORE", "east-orlando-ucf", "EAST_ORLANDO_BOX"
    if 28.585 <= lat <= 28.66 and -81.445 <= lng <= -81.33:
        return "CORRIDOR", "north-orlando-winter-park-maitland", "NORTH_ORLANDO_BOX"
    if 28.50 <= lat <= 28.62 and -81.60 <= lng < -81.40:
        return "CORRIDOR", "west-orlando-ocoee-winter-garden", "WEST_ORLANDO_BOX"
    if 28.40 <= lat <= 28.50 and -81.53 <= lng < -81.43:
        return "CORE", "international-drive", "DR_PHILLIPS_BAY_HILL_BOX"
    return (klass or "UNKNOWN"), None, "NO_CORRIDOR_RULE"
