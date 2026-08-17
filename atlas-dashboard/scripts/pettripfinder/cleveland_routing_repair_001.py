"""PTF-CLEVELAND-ROUTING-REPAIR-001 -- repair the Cleveland routing bottleneck.

Mechanically derives the 43-row routing queue (the 7 committed routing-review
observations from the Pass-3 packet + every AWAITING_ROUTING_REPLACEMENT,
AWAITING_PROPERTY_LEVEL_URL and AWAITING_OFFICIAL_URL identity in the
committed partition at d14cdc4), adjudicates each against authoritative
sources only (exact first-party property pages, official brand property
pages, official CVB/chamber directories as discovery anchors -- never an OTA
as routing authority), and applies exactly what the evidence supports:

* identity_routing.json -- corrected/confirmed/upgraded URLs on the 27
  existing records, three new records for identities whose official URL this
  pass found, one record moved to ROUTING_HELD because the brand endpoint
  refuses to serve its property page. Excluded identities gain no route
  (DoubleTree Canton Downtown's corrected page lives on its exclusion
  record; the standing invariant holds).
* cleveland_unresolved_manifest.json -- official_url kept in lockstep with
  routing (the partition's drift audit is the gate), classification moved to
  ROUTING_REPAIRED_AWAITING_CAPTURE where a working property page now
  exists, and a ``routing_repair`` provenance block recording verdict,
  old URL and evidence on every adjudicated row.
* cleveland_final_partition_002.json -- RE-DERIVED by its own builder; the
  builder's per-slug override tables carry this work order's state moves
  (13 repaired AWAITING_ROUTING_REPLACEMENT rows and Best Western Plus North
  Canton moving the other way), each with its recorded reason.

NO published policy fact moves. NO approval is written. NO exclusion moves.
Two identities (Harbor Inn, Hopp-Inn) are IDENTITY_CONFLICT findings -- the
census address hosts a bar, not lodging -- recorded for the census lane;
their partition states do not move on routing evidence.

Outputs: cleveland_routing_repair_001_results.json (all 43 exactly once)
and cleveland_routing_repair_001_capture_ready_queue.json (every identity
made or confirmed capture-eligible, plus the P3-049 re-drive row; the three
ADR-forbidden Hyatt rows stay operator-manual and are listed separately).

Run:  python -m scripts.pettripfinder.cleveland_routing_repair_001 [--apply]
"""

from __future__ import annotations

import argparse
import json
import sys
from collections import Counter, OrderedDict
from pathlib import Path
from typing import Dict, List, Optional

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder import identity_routing as IR                     # noqa: E402
from scripts.pettripfinder.identity_routing import registrable_domain        # noqa: E402

MARKET = "cleveland-akron-canton-oh"
WORK_ORDER = "PTF-CLEVELAND-ROUTING-REPAIR-001"
AS_OF = "2026-08-16"

LP = _REPO_ROOT / "launch_packages" / "pettripfinder"
PARTITION_PATH = LP / "cleveland_final_partition_002.json"
MANIFEST_PATH = LP / "cleveland_unresolved_manifest.json"
ROUTING_PATH = LP / "identity_routing.json"
CENSUS_PATH = LP / "identity_census" / ("%s.json" % MARKET)
PACKET_PATH = LP / "cleveland_pass3_founder_review_packet.json"
RESULTS_PATH = LP / "cleveland_routing_repair_001_results.json"
QUEUE_OUT_PATH = LP / "cleveland_routing_repair_001_capture_ready_queue.json"

#: The classification this pass writes where a working property page now
#: exists. Distinct from ROUTED_AWAITING_CAPTURE so capture-003's recorded
#: attempt outcomes keep describing exactly the rows that run swept.
REPAIRED = "ROUTING_REPAIRED_AWAITING_CAPTURE"

#: Domains that can never source a rendered-page binding (bot-walled; the
#: standing rule from PTF-CLEVELAND-DAYTON-WORKER-INTEGRATION-001).
WALLED = {"hilton.com", "marriott.com", "ihg.com", "choicehotels.com",
          "bestwestern.com", "radissonhotels.com", "redroof.com",
          "extendedstayamerica.com"}


def B(name=False, street=False, zip_=False, phone=False, code=None):
    return OrderedDict([("name", name), ("street", street), ("zip", zip_),
                        ("phone", phone), ("property_code", code)])


# --------------------------------------------------------------------------- #
# Adjudications. Every entry records what was probed, what bound, and the
# verdict. new_url None means the URL on record stands (or none exists).
# --------------------------------------------------------------------------- #

ADJ: "OrderedDict[str, Dict]" = OrderedDict()

# ---- A. the 7 committed routing-review observations ------------------------ #
ADJ["cambria hotel and suites avon"] = {
    "group": "OBSERVATION", "verdict": "PROPERTY_CLOSED_OR_CONVERTED",
    "old_url": "https://www.choicehotels.com/ohio/avon/cambria-hotels/oh598",
    "new_url": "https://www.wyndhamhotels.com/wyndham/avon-ohio/wyndham-avon/overview",
    "source_relationship": "OFFICIAL_BRAND_PROPERTY_PAGE",
    "binding": B(street=True, zip_=True),
    "brand": "WYNDHAM", "property_code": None, "page_rendered": True,
    "capture_ready": True, "state_move": None,
    "rename_proposal": "Wyndham Avon",
    "evidence": "choicehotels.com/oh598 redirects to the brand's Avon city "
                "listing (Pass-3 artifact P3-002); the Wyndham Avon property "
                "page serves and carries 35600 Detroit Rd and 44011 -- the "
                "census address. The property converted Cambria -> Wyndham "
                "Avon; the census identity is unchanged pending a founder "
                "rename decision.",
}
ADJ["doubletree by hilton canton downtown"] = {
    "group": "OBSERVATION", "verdict": "ROUTING_REPLACED",
    "old_url": "https://www.330barandgrill.com/",
    "new_url": "https://www.hilton.com/en/hotels/cakcodt-doubletree-canton-downtown/",
    "source_relationship": "OFFICIAL_BRAND_PROPERTY_PAGE",
    "binding": B(name=True, street=True, zip_=True, phone=True,
                 code="cakcodt"),
    "brand": "DOUBLETREE", "property_code": "cakcodt", "page_rendered": False,
    "capture_ready": False, "state_move": None, "excluded": True,
    "evidence": "The queued URL is the hotel's own restaurant's site; the "
                "cakcodt property page (hash-bound Pass-3 artifact P3-004b) "
                "binds by JSON-LD: 320 Market Avenue South, 44702, "
                "330-471-8000. The identity is VERIFIED_NO_PETS and its "
                "exclusion record already cites the corrected page as "
                "official_url; excluded identities hold no routes, so the "
                "correction lands as exclusion-URL confirmation only.",
}
ADJ["holiday inn canton"] = {
    "group": "OBSERVATION", "verdict": "ROUTING_REPLACED",
    "old_url": "https://www.twenty20taphouse.com/",
    "new_url": "https://www.ihg.com/holidayinn/hotels/us/en/canton/cakbv/hoteldetail",
    "source_relationship": "OFFICIAL_BRAND_PROPERTY_PAGE",
    "binding": B(name=True, street=True, zip_=True, phone=True, code="cakbv"),
    "brand": "HOLIDAY_INN", "property_code": "cakbv", "page_rendered": False,
    "capture_ready": True, "state_move": None,
    "evidence": "The recorded URL is the hotel's restaurant (Twenty20 "
                "Taphouse). IHG's Holiday Inn Canton (Belden Village) page "
                "cakbv serves and carries 4520 Everhard Rd NW, 44718 and "
                "330-494-2770 -- all three census signals.",
}
ADJ["radisson hotel akron fairlawn"] = {
    "group": "OBSERVATION", "verdict": "ROUTING_REPLACED",
    "old_url": "https://www.radissonhotels.com/en-us/hotels/radisson-akron",
    "new_url": "https://www.choicehotels.com/ohio/akron/radisson-hotels/oh557",
    "source_relationship": "OFFICIAL_BRAND_PROPERTY_PAGE",
    "binding": B(name=True, street=True, zip_=True, phone=True, code="oh557"),
    "brand": "RADISSON", "property_code": "oh557", "page_rendered": False,
    "capture_ready": True, "state_move": None,
    "evidence": "radissonhotels.com/radisson-akron redirects to the brand "
                "page (Pass-3 artifact P3-019). Radisson Americas moved to "
                "Choice Hotels; the choicehotels.com oh557 property page "
                "serves and carries 200 Montrose West Ave, 44321 and "
                "330-666-9300 -- all three census signals.",
}
ADJ["the inn at amish door"] = {
    "group": "OBSERVATION", "verdict": "ROUTING_REPLACED",
    "old_url": "https://www.milanaballroom.com/",
    "new_url": "https://amishdoor.com/the-inn-at-amish-door/",
    "source_relationship": "FIRST_PARTY_PROPERTY_PAGE",
    "binding": B(name=True, street=True, zip_=True, phone=True),
    "brand": "INDEPENDENT", "property_code": None, "page_rendered": True,
    "capture_ready": True, "state_move": None,
    "evidence": "The recorded URL is an event-venue site. The Amish Door "
                "Village's own inn page serves a plain GET and carries 1210 "
                "Winesburg St, Wilmot, 44689 and 330-359-7996 -- all three "
                "census signals plus the property name.",
}
ADJ["best western plus north canton inn and suites"] = {
    "group": "OBSERVATION", "verdict": "ROUTING_UNRESOLVED",
    "old_url": "https://www.bestwestern.com/en_US/book/hotels-in-north-canton/"
               "best-western-plus-north-canton-inn-suites/propertyCode.36148.html",
    "new_url": None,
    "source_relationship": "OFFICIAL_CVB_DIRECTORY_ANCHOR",
    "binding": B(name=True, street=True, zip_=True),
    "brand": "BEST_WESTERN", "property_code": "36148", "page_rendered": False,
    "capture_ready": False, "state_move": "AWAITING_ROUTING_REPLACEMENT",
    "hold": True,
    "evidence": "Both the direct hotel-rooms.36148 URL and the canonical "
                "property-page URL redirect to bestwestern.com's search page "
                "(pre-filled with a different city), so the brand endpoint "
                "refuses to serve this property page to this session. "
                "Closure is NOT inferred: the Canton CVB "
                "(explorecantonohio.com) lists the property as operating at "
                "6889 Sunset Strip Ave NW, North Canton 44720. The route is "
                "HELD with the candidate URL retained; an attended or "
                "operator session must re-probe before capture.",
}
ADJ["la quinta inn and suites cleveland airport north"] = {
    "group": "OBSERVATION", "verdict": "ROUTING_CONFIRMED",
    "old_url": "https://www.wyndhamhotels.com/laquinta/cleveland-ohio/"
               "la-quinta-cleveland-airport-north/overview",
    "new_url": None,
    "source_relationship": "OFFICIAL_BRAND_PROPERTY_PAGE",
    "binding": B(name=True, street=True, zip_=True, phone=True),
    "brand": "LA_QUINTA", "property_code": None, "page_rendered": True,
    "capture_ready": True, "state_move": None,
    "evidence": "During Pass 3 this URL redirected to the DIFFERENT La "
                "Quinta Cleveland Airport West property (North Olmsted); "
                "re-probed this session it serves the Airport North page "
                "carrying 4222 West 150th St, 44135 and 216-251-8500 -- all "
                "three census signals. The redirect was transient; the "
                "recorded URL stands. Any future capture must re-verify the "
                "page's own address before extracting policy.",
}

# ---- B. the 13 AWAITING_ROUTING_REPLACEMENT rows --------------------------- #
ADJ["comfort suites hartville"] = {
    "group": "ROUTING_REPLACEMENT", "verdict": "ROUTING_REPLACED",
    "old_url": "https://www.hartvillekitchen.com",
    "new_url": "https://www.choicehotels.com/ohio/hartville/comfort-suites-hotels/oh596",
    "source_relationship": "OFFICIAL_BRAND_PROPERTY_PAGE",
    "binding": B(name=True, street=True, zip_=True, phone=True, code="oh596"),
    "brand": "COMFORT_SUITES", "property_code": "oh596",
    "page_rendered": False, "capture_ready": True,
    "state_move": "AWAITING_POLICY_OBSERVATION",
    "evidence": "The recorded URL is a restaurant. choicehotels.com oh596 "
                "serves and carries 953 Edison St NW, 44632 and 330-587-4347 "
                "-- all three census signals.",
}
ADJ["cottages at the lodge"] = {
    "group": "ROUTING_REPLACEMENT", "verdict": "ROUTING_CONFIRMED",
    "old_url": "https://www.thelodgeatgeneva.com/stay/lodging/cottage-rooms/",
    "new_url": None,
    "source_relationship": "FIRST_PARTY_PROPERTY_PAGE",
    "binding": B(name=True, street=True, zip_=True, phone=True),
    "brand": "INDEPENDENT", "property_code": None, "page_rendered": True,
    "capture_ready": True, "state_move": "AWAITING_POLICY_OBSERVATION",
    "evidence": "The URL on record was marked dead; it serves a plain GET "
                "this session (title 'Cottages - The Lodge at "
                "Geneva-on-the-Lake') and carries 4888 N Broadway, 44041 and "
                "440-466-7100 -- all three census signals.",
}
ADJ["crowne plaza cleveland airport"] = {
    "group": "ROUTING_REPLACEMENT", "verdict": "ROUTING_REPLACED",
    "old_url": "https://www.crowneplazacle.com",
    "new_url": "https://www.ihg.com/crowneplaza/hotels/us/en/middleburg-heights/clemh/hoteldetail",
    "source_relationship": "OFFICIAL_BRAND_PROPERTY_PAGE",
    "binding": B(name=True, street=True, zip_=True, phone=True, code="clemh"),
    "brand": "CROWNE_PLAZA", "property_code": "clemh",
    "page_rendered": False, "capture_ready": True,
    "state_move": "AWAITING_POLICY_OBSERVATION",
    "evidence": "The vanity domain answers 403/502. IHG's clemh property "
                "page serves and carries 7230 Engle Rd, 44130 and "
                "440-243-4040 -- all three census signals.",
}
ADJ["days inn richfield"] = {
    "group": "ROUTING_REPLACEMENT", "verdict": "PROPERTY_CLOSED_OR_CONVERTED",
    "old_url": "https://www.wyndhamhotels.com/days-inn/richfield-ohio/"
               "days-inn-and-suites-richfield/overview",
    "new_url": "https://www.choicehotels.com/ohio/richfield/quality-inn-hotels/oh330",
    "source_relationship": "OFFICIAL_BRAND_PROPERTY_PAGE",
    "binding": B(street=True, zip_=True, code="oh330"),
    "brand": "QUALITY_INN", "property_code": "oh330",
    "page_rendered": False, "capture_ready": True,
    "state_move": "AWAITING_POLICY_OBSERVATION",
    "rename_proposal": "Quality Inn & Suites Richfield",
    "census_hygiene": "page phone (330) 523-5329 differs from census "
                      "330.659.6151; changed with the flag conversion",
    "evidence": "The Wyndham URL redirects to the brand's Richfield search "
                "page. choicehotels.com oh330 serves 'Quality Inn & Suites "
                "Richfield' at 4742 Brecksville Rd, 44286 -- the census "
                "street and ZIP. The property converted Days Inn -> Quality "
                "Inn; census identity unchanged pending a founder rename.",
}
ADJ["doubletree by hilton cleveland westlake"] = {
    "group": "ROUTING_REPLACEMENT", "verdict": "PROPERTY_CLOSED_OR_CONVERTED",
    "old_url": "https://www.hilton.com/en/hotels/clecrdt-doubletree-cleveland-westlake/",
    "new_url": "https://www.wyndhamhotels.com/wyndham-garden/westlake-ohio/"
               "wyndham-garden-westlake/overview",
    "source_relationship": "OFFICIAL_BRAND_PROPERTY_PAGE",
    "binding": B(street=True, zip_=True, phone=True),
    "brand": "WYNDHAM_GARDEN", "property_code": None, "page_rendered": True,
    "capture_ready": True, "state_move": "AWAITING_POLICY_OBSERVATION",
    "rename_proposal": "Wyndham Garden Westlake",
    "evidence": "hilton.com/clecrdt is a genuine Hilton 404 ('That page has "
                "checked out'). The Wyndham Garden Westlake page serves and "
                "carries 1100 Crocker Rd, 44145 and 440-871-6000 -- all "
                "three census signals. DoubleTree -> Wyndham Garden "
                "conversion; census identity unchanged pending a founder "
                "rename.",
}
ADJ["embassy suites by hilton akron canton airport"] = {
    "group": "ROUTING_REPLACEMENT", "verdict": "ROUTING_REPLACED",
    "old_url": "https://luggageroomspeakeasy.com",
    "new_url": "https://www.hilton.com/en/hotels/caknaes-embassy-suites-akron-canton-airport/",
    "source_relationship": "OFFICIAL_BRAND_PROPERTY_PAGE",
    "binding": B(name=True, street=True, zip_=True, phone=True,
                 code="caknaes"),
    "brand": "EMBASSY_SUITES", "property_code": "caknaes",
    "page_rendered": False, "capture_ready": True,
    "state_move": "AWAITING_POLICY_OBSERVATION",
    "evidence": "The recorded URL is the hotel's on-site bar. Hilton's "
                "caknaes property page serves and carries 7883 Freedom Ave "
                "NW, 44720 and 330-305-0500 -- all three census signals.",
}
ADJ["extended stay america premier suites"] = {
    "group": "ROUTING_REPLACEMENT", "verdict": "ROUTING_REPLACED",
    "old_url": "https://www.hyatt.com/en-US/hotel/ohio/"
               "hyatt-place-cleveland-independence/clezi",
    "new_url": "https://www.extendedstayamerica.com/hotels/oh/cleveland/independence",
    "source_relationship": "OFFICIAL_BRAND_PROPERTY_PAGE",
    "binding": B(name=True, street=True, zip_=True, phone=True),
    "brand": "EXTENDED_STAY_AMERICA", "property_code": None,
    "page_rendered": False, "capture_ready": True,
    "state_move": "AWAITING_POLICY_OBSERVATION",
    "evidence": "The recorded URL points at a DIFFERENT hotel (Hyatt Place "
                "Cleveland Independence). ESA's own property page serves "
                "and carries 6025 Jefferson Dr, 44131 and 216-328-1060 -- "
                "all three census signals.",
}
ADJ["highlander inn"] = {
    "group": "ROUTING_REPLACEMENT", "verdict": "ROUTING_REPLACED",
    "old_url": "https://www.highlanderinncle.com",
    "new_url": "https://highlanderinnhotel.com/",
    "source_relationship": "FIRST_PARTY_PROPERTY_PAGE",
    "binding": B(name=True, street=True, zip_=True, phone=True),
    "brand": "INDEPENDENT", "property_code": None, "page_rendered": True,
    "capture_ready": True, "state_move": "AWAITING_POLICY_OBSERVATION",
    "evidence": "The old domain no longer resolves (DNS). The property's "
                "new domain highlanderinnhotel.com serves a plain GET and "
                "carries 4353 Northfield Rd, 44128 and the census phone "
                "digits 216-475-4070.",
}
ADJ["intercontinental suites hotel cleveland"] = {
    "group": "ROUTING_REPLACEMENT", "verdict": "ROUTING_REPLACED",
    "old_url": "https://www.intercontinentalsuitescleveland.com",
    "new_url": "https://www.icsuitescleveland.com/",
    "source_relationship": "FIRST_PARTY_PROPERTY_PAGE",
    "binding": B(name=True, street=True, zip_=True, phone=True),
    "brand": "INTERCONTINENTAL", "property_code": None,
    "page_rendered": True, "capture_ready": True,
    "state_move": "AWAITING_POLICY_OBSERVATION",
    "evidence": "The recorded vanity 301-redirects to the property's own "
                "icsuitescleveland.com, which renders in the attended "
                "browser and carries 8800 Euclid Ave, 44106 and "
                "216-707-4300 -- all three census signals.",
}
ADJ["sonesta es suites cleveland westlake"] = {
    "group": "ROUTING_REPLACEMENT", "verdict": "ROUTING_REPLACED",
    "old_url": "https://www.sonesta.com/us/ohio/westlake/"
               "sonesta-es-suites-cleveland-westlake",
    "new_url": "https://www.sonesta.com/sonesta-simply-suites/oh/westlake/"
               "sonesta-simply-suites-cleveland-westlake",
    "source_relationship": "OFFICIAL_BRAND_PROPERTY_PAGE",
    "binding": B(street=True, zip_=True, phone=True),
    "brand": "SONESTA", "property_code": None, "page_rendered": True,
    "capture_ready": True, "state_move": "AWAITING_POLICY_OBSERVATION",
    "rename_proposal": "Sonesta Simply Suites Cleveland Westlake",
    "evidence": "The old ES-Suites path is gone; the Simply Suites rebrand "
                "path serves and carries 30100 Clemens Rd, 44145 and "
                "440-892-2254 -- all three census signals. Same ES->Simply "
                "rebrand the founder already ruled census-hygiene-only at "
                "Cleveland Airport (D06).",
}
ADJ["springhill suites solon"] = {
    "group": "ROUTING_REPLACEMENT", "verdict": "ROUTING_REPLACED",
    "old_url": "https://www.springhillsolon.com",
    "new_url": "https://www.marriott.com/en-us/hotels/clesh-springhill-suites-cleveland-solon/overview/",
    "source_relationship": "OFFICIAL_BRAND_PROPERTY_PAGE",
    "binding": B(name=True, street=True, zip_=True, phone=True, code="clesh"),
    "brand": "SPRINGHILL_SUITES", "property_code": "clesh",
    "page_rendered": False, "capture_ready": True,
    "state_move": "AWAITING_POLICY_OBSERVATION",
    "evidence": "The vanity domain answers 403 and is dead as an official "
                "endpoint. Marriott's clesh property page serves and "
                "carries 30100 Aurora Rd, 44139 and 440-248-9600 -- all "
                "three census signals.",
}
ADJ["the bertram inn at glenmoor"] = {
    "group": "ROUTING_REPLACEMENT", "verdict": "ROUTING_REPLACED",
    "old_url": "https://glenmoorcc.com/Spa",
    "new_url": "https://glenmoorcc.com/Hotel",
    "source_relationship": "FIRST_PARTY_PROPERTY_PAGE",
    "binding": B(name=True, street=True, zip_=True, phone=True),
    "brand": "INDEPENDENT", "property_code": None, "page_rendered": True,
    "capture_ready": True, "state_move": "AWAITING_POLICY_OBSERVATION",
    "evidence": "The recorded path is the spa. Glenmoor Country Club's own "
                "/Hotel page serves a plain GET and carries 4191 Glenmoor "
                "Rd NW, 44718, 330-966-3600 and the Bertram name.",
}
ADJ["the lakehouse inn and winery"] = {
    "group": "ROUTING_REPLACEMENT", "verdict": "ROUTING_CONFIRMED",
    "old_url": "https://thelakehouseinn.com/",
    "new_url": None,
    "source_relationship": "FIRST_PARTY_PROPERTY_PAGE",
    "binding": B(name=True, street=True, zip_=True, phone=True),
    "brand": "INDEPENDENT", "property_code": None, "page_rendered": True,
    "capture_ready": True, "state_move": "AWAITING_POLICY_OBSERVATION",
    "evidence": "The URL on record was marked dead; it serves a plain GET "
                "this session (title 'The Lakehouse Inn | A Bed & Breakfast "
                "in Geneva on the Lake') and carries 5653 Lake Rd E, 44041 "
                "and 440-466-8668 -- all three census signals.",
}

# ---- C. the 8 AWAITING_PROPERTY_LEVEL_URL rows ------------------------------ #
ADJ["comfort suites twinsburg"] = {
    "group": "PROPERTY_LEVEL_URL", "verdict": "PROPERTY_LEVEL_URL_UPGRADED",
    "old_url": "https://www.choicehotels.com/ohio/twinsburg/comfort-suites-hotels/oh271",
    "new_url": None,
    "source_relationship": "OFFICIAL_BRAND_PROPERTY_PAGE",
    "binding": B(name=True, zip_=True, phone=True, code="oh271"),
    "brand": "COMFORT_SUITES", "property_code": "oh271",
    "page_rendered": False, "capture_ready": True, "state_move": None,
    "census_hygiene": "page street reads 2716 Creekside Drive; census "
                      "carries 2715 Creekside Dr -- address form to review",
    "evidence": "The URL on record IS the oh271 property page; it serves "
                "and carries the census ZIP 44087 and phone 330-963-5909. "
                "Name and property code bind; the one-digit street "
                "difference is a census address-form observation, not an "
                "identity failure.",
}
_RRI = {
    "red roof inn cleveland east": (
        "https://www.redroof.com/property/Willoughby/OH/44094/"
        "Hotels-close-to-Cleveland-Clinic-I-90-/RRI053/",
        "https://www.redroof.com/property/oh/willoughby/rri053",
        "RRI053", "4166 OH-306 (State Route 306)", "44094"),
    "red roof inn independence": (
        "https://www.redroof.com/property/Independence/OH/44131/"
        "Hotels-close-to-South-Cleveland-Ohio-I-77-I-480/RRI028/",
        "https://www.redroof.com/property/oh/independence/rri028",
        "RRI028", "6020 Quarry Ln", "44131"),
    "red roof inn middleburg heights": (
        "https://www.redroof.com/property/Cleveland/OH/44130/"
        "Hotels-close-to-Cleveland-Hopkins-Airport-I-71/RRI060/",
        "https://www.redroof.com/property/oh/cleveland/rri060",
        "RRI060", "17555 Bagley Rd", "44130"),
    "red roof inn westlake": (
        "https://www.redroof.com/property/Westlake/OH/44145/"
        "Hotels-close-to-I-90-Northwest-Freeway/RRI094/",
        "https://www.redroof.com/property/oh/westlake/rri094",
        "RRI094", "29595 Clemens Rd", "44145"),
}
for _key, (_old, _new, _code, _addr, _zip) in _RRI.items():
    ADJ[_key] = {
        "group": "PROPERTY_LEVEL_URL",
        "verdict": "PROPERTY_LEVEL_URL_UPGRADED",
        "old_url": _old, "new_url": _new,
        "source_relationship": "OFFICIAL_BRAND_PROPERTY_PAGE",
        "binding": B(name=True, street=True, zip_=True, code=_code),
        "brand": "RED_ROOF", "property_code": _code,
        "page_rendered": False, "capture_ready": True, "state_move": None,
        "evidence": "The stored landing-style URL 301-redirects to the "
                    "canonical property page %s, whose page carries %s and "
                    "the ZIP %s in its own title; the %s property code "
                    "binds. The page phone is Red Roof central reservations "
                    "(877), so binding rests on street, ZIP and code."
                    % (_new, _addr, _zip, _code),
    }
ADJ["residence inn by marriott cleveland university circle medical center"] = {
    "group": "PROPERTY_LEVEL_URL", "verdict": "PROPERTY_LEVEL_URL_UPGRADED",
    "old_url": "https://marriott.com/cleuv",
    "new_url": "https://www.marriott.com/en-us/hotels/"
               "cleuv-residence-inn-cleveland-university-circle-medical-center/overview/",
    "source_relationship": "OFFICIAL_BRAND_PROPERTY_PAGE",
    "binding": B(name=True, street=True, zip_=True, phone=True, code="cleuv"),
    "brand": "RESIDENCE_INN", "property_code": "cleuv",
    "page_rendered": False, "capture_ready": True, "state_move": None,
    "evidence": "The short link expands to the full cleuv property page, "
                "which serves and carries 1914 E 101 St, 44106 and "
                "216-249-9090 -- all three census signals.",
}
ADJ["towneplace suites by marriott"] = {
    "group": "PROPERTY_LEVEL_URL", "verdict": "PROPERTY_LEVEL_URL_UPGRADED",
    "old_url": "https://www.marriott.com/brands/towneplace-suites.mi",
    "new_url": "https://www.marriott.com/en-us/hotels/"
               "cleto-towneplace-suites-cleveland-solon/overview/",
    "source_relationship": "OFFICIAL_BRAND_PROPERTY_PAGE",
    "binding": B(name=True, street=True, zip_=True, phone=True, code="cleto"),
    "brand": "TOWNEPLACE_SUITES", "property_code": "cleto",
    "page_rendered": False, "capture_ready": True, "state_move": None,
    "evidence": "The recorded URL was the BRAND homepage. Marriott's cleto "
                "property page serves and carries 6040 Enterprise Pkwy, "
                "44139 and 440-394-1270 -- all three census signals.",
}
ADJ["travelodge cleveland airport"] = {
    "group": "PROPERTY_LEVEL_URL", "verdict": "ROUTING_CONFIRMED",
    "old_url": "https://www.wyndhamhotels.com/travelodge/brook-park-ohio/"
               "travelodge-cleveland-airport/overview",
    "new_url": None,
    "source_relationship": "OFFICIAL_BRAND_PROPERTY_PAGE",
    "binding": B(name=True, street=True, zip_=True, phone=True),
    "brand": "TRAVELODGE", "property_code": None, "page_rendered": True,
    "capture_ready": True, "state_move": None,
    "evidence": "The URL on record IS the property page; it renders in the "
                "attended browser and carries the census street number "
                "14043, ZIP 44142 and phone 216-920-0855.",
}

# ---- D. the 15 AWAITING_OFFICIAL_URL rows ----------------------------------- #
_NO_SITE = {
    "berlin s motel": ("chamberofcommerce.com business directory confirms "
                       "Berlin's Motel at 334 31st St NW, Barberton 44203; "
                       "no first-party website exists in any authoritative "
                       "source."),
    "budget inn": ("chamberofcommerce.com confirms The Budget Inn at 5891 "
                   "Akron-Cleveland Rd, Hudson 44236; the only web "
                   "presences are OTA white-labels; no first-party site."),
    "clarion inn and conference center": (
        "thisiscleveland.com (CVB) confirms the property operating at 6625 "
        "Dean Memorial Parkway, Hudson 44236, 330.653.9191, but Choice "
        "Hotels lists no Clarion in Hudson OH -- the property appears to "
        "have left the flag -- and no first-party site exists."),
    "courtesy inn": ("visitakron-summit.org (CVB) lists Courtesy Inn at 210 "
                     "W Market St, Akron 44303 with no website link; no "
                     "first-party site exists."),
    "don el motel": ("visitakron-summit.org (CVB) lists Don-El Motel at "
                     "5133 Akron-Cleveland Rd, Peninsula 44264 with no "
                     "website link; no first-party site exists."),
    "lakeside motel": ("visitakron-summit.org (CVB) lists Lakeside Motel at "
                       "3529 Manchester Rd, Akron 44319 with no website "
                       "link; no first-party site exists."),
    "ranch motel": ("visitakron-summit.org (CVB) lists Ranch Motel at 3608 "
                    "State Rd, Cuyahoga Falls 44223 with no website link; "
                    "no first-party site exists."),
    "sunset motel": ("chamberofcommerce.com confirms Sunset Motel at 10255 "
                     "Northfield Rd, Northfield 44067; only OTA "
                     "white-labels exist; no first-party site."),
    "twinsburg country inn": ("visitakron-summit.org (CVB) lists Twinsburg "
                              "Country Inn at 11336 Ravenna Rd, Twinsburg "
                              "44087 with no website link; no first-party "
                              "site exists."),
    "twinsburg inn motel": ("visitakron-summit.org (CVB) lists Twinsburg "
                            "Inn Motel at 9440 Ravenna Rd, Twinsburg 44087 "
                            "with no website link; no first-party site "
                            "exists."),
}
for _key, _ev in _NO_SITE.items():
    ADJ[_key] = {
        "group": "OFFICIAL_URL", "verdict": "ROUTING_UNRESOLVED",
        "old_url": None, "new_url": None,
        "source_relationship": "OFFICIAL_CVB_DIRECTORY_ANCHOR",
        "binding": B(), "brand": "INDEPENDENT", "property_code": None,
        "page_rendered": False, "capture_ready": False, "state_move": None,
        "evidence": _ev + " No URL is fabricated; the identity stays in the "
                    "discovery lane.",
    }
ADJ["harbor inn"] = {
    "group": "OFFICIAL_URL", "verdict": "IDENTITY_CONFLICT",
    "old_url": None, "new_url": None,
    "source_relationship": "OFFICIAL_CVB_DIRECTORY_ANCHOR",
    "binding": B(), "brand": "INDEPENDENT", "property_code": None,
    "page_rendered": False, "capture_ready": False, "state_move": None,
    "census_review": True,
    "evidence": "Every authoritative source (thisiscleveland.com CVB, "
                "chamberofcommerce.com -- category 'bar') describes 1219 "
                "Main Ave as the Harbor Inn Cafe, one of Cleveland's oldest "
                "BARS, not lodging. Census-review candidate alongside Inn "
                "the Doghouse and The Rowley Inn; the state stays in the "
                "discovery lane because a category exit is a census "
                "decision, not a routing one.",
}
ADJ["hopp inn"] = {
    "group": "OFFICIAL_URL", "verdict": "IDENTITY_CONFLICT",
    "old_url": None, "new_url": None,
    "source_relationship": "OFFICIAL_CVB_DIRECTORY_ANCHOR",
    "binding": B(), "brand": "INDEPENDENT", "property_code": None,
    "page_rendered": False, "capture_ready": False, "state_move": None,
    "census_review": True,
    "evidence": "Every authoritative source (thisiscleveland.com CVB, "
                "chamberofcommerce.com -- category 'bar') describes 4896 "
                "Pearl Rd as the Hopp-Inn, a neighborhood BAR with Polish "
                "food, not lodging. Census-review candidate; state stays in "
                "the discovery lane for the same reason as Harbor Inn.",
}
ADJ["magnuson extended stay"] = {
    "group": "OFFICIAL_URL", "verdict": "OFFICIAL_URL_FOUND",
    "old_url": None,
    "new_url": "https://www.magnusonhotels.com/magnusonhotelextendedstaycantonohio/",
    "source_relationship": "OFFICIAL_BRAND_PROPERTY_PAGE",
    "binding": B(name=True, street=True, zip_=True, phone=True),
    "brand": "MAGNUSON", "property_code": None, "page_rendered": True,
    "capture_ready": True, "state_move": None,
    "evidence": "magnusonhotels.com's own property page serves a plain GET "
                "and carries 4285 Everhard Rd NW, 44718 and 330-494-2233 -- "
                "all three census signals.",
}
ADJ["quality inn arlington"] = {
    "group": "OFFICIAL_URL", "verdict": "OFFICIAL_URL_FOUND",
    "old_url": None,
    "new_url": "https://www.choicehotels.com/ohio/akron/quality-inn-hotels/oh462",
    "source_relationship": "OFFICIAL_BRAND_PROPERTY_PAGE",
    "binding": B(name=True, street=True, zip_=True, phone=True, code="oh462"),
    "brand": "QUALITY_INN", "property_code": "oh462",
    "page_rendered": False, "capture_ready": True, "state_move": None,
    "evidence": "choicehotels.com oh462 ('Quality Inn Akron South') serves "
                "and carries 2873 S Arlington Rd, 44312 and 234-542-8314 -- "
                "all three census signals. The Akron CVB "
                "(visitakron-summit.org) lists the same property as "
                "'Quality Inn Arlington'.",
}
ADJ["villa croatia at the american croatian lodge"] = {
    "group": "OFFICIAL_URL", "verdict": "OFFICIAL_URL_FOUND",
    "old_url": None,
    "new_url": "https://croatianlodge.com/",
    "source_relationship": "FIRST_PARTY_PROPERTY_PAGE",
    "binding": B(name=True, street=True, zip_=True),
    "brand": "INDEPENDENT", "property_code": None, "page_rendered": True,
    "capture_ready": True, "state_move": None,
    "census_hygiene": "site phone 440-946-3366 differs from census "
                      "216.704.9009",
    "evidence": "The American Croatian Lodge's own croatianlodge.com serves "
                "a plain GET and carries 34900 Lakeshore Blvd, 44095 and "
                "the Lodge name with room content. The site presents "
                "primarily as an event venue; the lodging component must "
                "be verified at capture time.",
}


# --------------------------------------------------------------------------- #
# Mechanics.
# --------------------------------------------------------------------------- #

def load_json(path: Path) -> Dict:
    return json.loads(path.read_text(encoding="utf-8-sig"))


def write_lf(path: Path, document) -> None:
    path.write_bytes((json.dumps(document, indent=2, ensure_ascii=False)
                      + "\n").encode("utf-8"))


def derive_queue() -> "OrderedDict[str, str]":
    """identity_key -> group, mechanically, exactly once each."""
    partition = load_json(PARTITION_PATH)
    packet = load_json(PACKET_PATH)
    queue: "OrderedDict[str, str]" = OrderedDict()
    for obs in packet["routing_review_observations"]:
        queue[obs["identity_key"]] = "OBSERVATION"
    for state, group in (("AWAITING_ROUTING_REPLACEMENT",
                          "ROUTING_REPLACEMENT"),
                         ("AWAITING_PROPERTY_LEVEL_URL",
                          "PROPERTY_LEVEL_URL"),
                         ("AWAITING_OFFICIAL_URL", "OFFICIAL_URL")):
        for item in partition["items"]:
            if item["final_state"] != state:
                continue
            if item["identity_key"] in queue:
                raise SystemExit("STOP: %r in two queue groups"
                                 % item["identity_key"])
            queue[item["identity_key"]] = group
    return queue


def run(apply: bool) -> Dict:
    queue = derive_queue()
    obs_ids = [o["identity_key"] for o in
               load_json(PACKET_PATH)["routing_review_observations"]]
    duplicates = [k for k, n in Counter(obs_ids).items() if n > 1]
    omissions = sorted(set(queue) - set(ADJ))
    extras = sorted(set(ADJ) - set(queue))
    if duplicates or omissions or extras:
        raise SystemExit("STOP: queue drift dup=%s omit=%s extra=%s"
                         % (duplicates, omissions, extras))
    for key, group in queue.items():
        if ADJ[key]["group"] != group:
            raise SystemExit("STOP: %r adjudicated under %r but derived %r"
                             % (key, ADJ[key]["group"], group))
    if len(queue) != 43:
        raise SystemExit("STOP: expected 43 rows, derived %d" % len(queue))

    census = {h["normalized_name"]: h
              for h in load_json(CENSUS_PATH)["hotels"]}
    routing = load_json(ROUTING_PATH)
    by_key = {r["hotel_ref"]["normalized_name"]: r
              for r in routing["routes"]
              if r.get("market_id") == MARKET}

    updated, created, held = [], [], []
    for key, spec in ADJ.items():
        target_url = spec["new_url"] or spec["old_url"]
        route = by_key.get(key)
        if spec["verdict"] in ("ROUTING_UNRESOLVED", "IDENTITY_CONFLICT") \
                and not spec.get("hold"):
            continue                       # nothing routable to write
        if spec.get("excluded"):
            if route is not None:
                raise SystemExit("STOP: excluded %r still holds a route"
                                 % key)
            continue                       # exclusion carries the URL
        if route is None:
            row = census[key]
            route = OrderedDict([
                ("routing_id", "route-%s-%s" % (MARKET, row["slug"])),
                ("schema_version", "1.0.0"),
                ("hotel_ref", OrderedDict([
                    ("identity_key", row["identity_key"]),
                    ("market_id", MARKET),
                    ("canonical_name", row["canonical_name"]),
                    ("normalized_name", key),
                ])),
                ("market_id", MARKET),
                ("official_property_url", target_url),
                ("official_domain", registrable_domain(target_url)),
                ("brand", spec["brand"]),
                ("binding_method", IR.BINDING_PAGE_RENDERED
                 if spec["page_rendered"] else IR.BINDING_BRAND_INDEX),
                ("binding_sources", []),
                ("identity_context", OrderedDict([
                    ("address", row["address"]), ("city", row["city"]),
                    ("state", row["state"]),
                    ("postal_code", row["postal_code"]),
                    ("phone", row["phone"]),
                ])),
                ("observed_at", AS_OF), ("verified_at", AS_OF),
                ("status", IR.ROUTING_CONFIRMED),
                ("notes", ""), ("category", "accommodation"),
            ])
            if spec["property_code"]:
                route["property_code"] = spec["property_code"]
            routing["routes"].append(route)
            created.append(key)
        else:
            updated.append(key)

        route["official_property_url"] = target_url
        route["official_domain"] = registrable_domain(target_url)
        route["brand"] = spec["brand"]
        if spec["property_code"]:
            route["property_code"] = spec["property_code"]
        elif "property_code" in route and spec["new_url"]:
            del route["property_code"]
        domain = registrable_domain(target_url)
        method = (IR.BINDING_PAGE_RENDERED
                  if spec["page_rendered"] and domain not in WALLED
                  else IR.BINDING_BRAND_INDEX)
        route["binding_method"] = method
        signals = [k for k, v in spec["binding"].items()
                   if v is True]
        if spec["binding"]["property_code"]:
            signals.append("property_code=%s"
                           % spec["binding"]["property_code"])
        route["identity_signals_matched"] = signals
        route["binding_sources"] = [
            "%s: %s" % (WORK_ORDER, spec["evidence"]),
        ]
        route["observed_at"] = AS_OF
        route["verified_at"] = AS_OF
        route["status"] = (IR.ROUTING_HELD if spec.get("hold")
                           else IR.ROUTING_CONFIRMED)
        prior_note = route.get("notes") or ""
        route["notes"] = ("%s %s verdict=%s; old URL: %s."
                          % (prior_note + (" //" if prior_note else ""),
                             WORK_ORDER, spec["verdict"],
                             spec["old_url"] or "(none)")).strip()
        IR.validate_record(route)

    routing["count"] = len(routing["routes"])

    # ---- manifest sync ------------------------------------------------------ #
    manifest = load_json(MANIFEST_PATH)
    items = {i["normalized_name"]: i for i in manifest["items"]}
    routed_now = {r["hotel_ref"]["normalized_name"]: r
                  for r in routing["routes"] if r.get("market_id") == MARKET}
    reclassified = 0
    for key, spec in ADJ.items():
        item = items.get(key)
        if item is None:
            if spec.get("excluded"):
                continue
            raise SystemExit("STOP: %r not in the unresolved manifest" % key)
        route = routed_now.get(key)
        if route is not None:
            item["official_url"] = route["official_property_url"]
        if spec["capture_ready"]:
            item["classification"] = REPAIRED
            item["why_unresolved"] = (
                "%s bound a working property page; the pet policy is still "
                "unobserved." % WORK_ORDER)
            item["next_action"] = (
                "Open %s in the attended browser, verify the page's own "
                "address block matches the census identity, and capture "
                "the pet policy surface." % route["official_property_url"])
            reclassified += 1
        item["routing_repair"] = OrderedDict([
            ("work_order", WORK_ORDER), ("as_of", AS_OF),
            ("verdict", spec["verdict"]),
            ("old_url", spec["old_url"] or ""),
            ("evidence", spec["evidence"]),
        ])
        if spec.get("rename_proposal"):
            item["routing_repair"]["rename_proposal"] = \
                spec["rename_proposal"]
        if spec.get("census_hygiene"):
            item["routing_repair"]["census_hygiene"] = spec["census_hygiene"]
    manifest["as_of"] = AS_OF
    manifest["routing_repair_001"] = (
        "%s adjudicated 43 routing rows: every verdict, old URL and the "
        "exact evidence live on each item's routing_repair block and in "
        "cleveland_routing_repair_001_results.json." % WORK_ORDER)

    # ---- results + capture-ready queue -------------------------------------- #
    results = []
    verdicts = Counter()
    for key, spec in ADJ.items():
        verdicts[spec["verdict"]] += 1
        row = census[key]
        route = routed_now.get(key)
        results.append(OrderedDict([
            ("identity_key", key),
            ("canonical_name", row["canonical_name"]),
            ("group", spec["group"]),
            ("verdict", spec["verdict"]),
            ("old_url", spec["old_url"] or ""),
            ("new_candidate_url", spec["new_url"] or ""),
            ("requested_url", spec["new_url"] or spec["old_url"] or ""),
            ("final_url", (route or {}).get("official_property_url", "")
             if not spec.get("excluded")
             else spec["new_url"]),
            ("source_relationship", spec["source_relationship"]),
            ("identity_binding", spec["binding"]),
            ("evidence", spec["evidence"]),
            ("capture_ready", spec["capture_ready"]),
            ("state_move", spec["state_move"] or ""),
            ("rename_proposal", spec.get("rename_proposal", "")),
            ("census_hygiene", spec.get("census_hygiene", "")),
            ("census_review_candidate", bool(spec.get("census_review"))),
        ]))

    ready_rows = []
    for key, spec in ADJ.items():
        if not spec["capture_ready"]:
            continue
        row = census[key]
        route = routed_now[key]
        ready_rows.append(OrderedDict([
            ("queue_id", "CLE-RR-%03d" % (len(ready_rows) + 1)),
            ("identity_key", key),
            ("name", row["canonical_name"]),
            ("slug", row["slug"]),
            ("official_url", route["official_property_url"]),
            ("address", row["address"]), ("city", row["city"]),
            ("postal_code", row["postal_code"]), ("phone", row["phone"]),
            ("brand", spec["brand"]),
            ("routing_verdict", spec["verdict"]),
            ("rename_proposal", spec.get("rename_proposal", "")),
            ("identity_caution", "verify the page's own address before "
                                 "extracting policy"
             if spec["verdict"] == "PROPERTY_CLOSED_OR_CONVERTED"
             or key == "la quinta inn and suites cleveland airport north"
             else ""),
        ]))
    ready_rows.append(OrderedDict([
        ("queue_id", "CLE-RR-%03d" % (len(ready_rows) + 1)),
        ("identity_key", "hilton garden inn akron canton airport"),
        ("name", "Hilton Garden Inn Akron-Canton Airport"),
        ("slug", "hilton-garden-inn-akron-canton-airport"),
        ("official_url", "https://www.hilton.com/en/hotels/"
                         "cakapgi-hilton-garden-inn-akron-canton-airport/"),
        ("address", "5251 Landmark Blvd"), ("city", "North Canton"),
        ("postal_code", "44720"), ("phone", "(330) 966-4907"),
        ("brand", "HILTON_GARDEN_INN"),
        ("routing_verdict", "ROUTING_CONFIRMED"),
        ("rename_proposal", ""),
        ("identity_caution", "P3-049 re-drive: the URL was Akamai-blocked "
                             "for the Pass-3 session only because it was "
                             "reused for cool-down probes; drive it FIRST "
                             "in a fresh session, before any other Hilton "
                             "page."),
    ]))

    queue_doc = OrderedDict([
        ("schema", "ptf-cleveland-routing-repair-queue/1.0"),
        ("work_order", WORK_ORDER), ("as_of", AS_OF),
        ("market_id", MARKET),
        ("rule", "Every identity this repair made or confirmed "
                 "capture-eligible, exactly once, each with an "
                 "identity-bound property URL -- plus the P3-049 re-drive "
                 "row. The three Hyatt rows are ADR-forbidden for "
                 "automation and stay operator-manual; their instructions "
                 "live in the Pass-3 packet and are restated here."),
        ("capture_ready_total", len(ready_rows)),
        ("rows", ready_rows),
        ("operator_manual_only",
         load_json(PACKET_PATH)["hyatt_operator_manual_instructions"]),
    ])

    results_doc = OrderedDict([
        ("schema", "ptf-cleveland-routing-repair-results/1.0"),
        ("work_order", WORK_ORDER), ("as_of", AS_OF),
        ("market_id", MARKET),
        ("derived_from", "cleveland_final_partition_002.json + the Pass-3 "
                         "packet's routing_review_observations at d14cdc4"),
        ("queue_total", len(queue)),
        ("queue_check", OrderedDict([("duplicates", 0), ("omissions", 0),
                                     ("extras", 0)])),
        ("verdict_counts", OrderedDict(sorted(verdicts.items()))),
        ("routes_updated", sorted(updated)),
        ("routes_created", sorted(created)),
        ("rule", "Routing says where a property speaks, never what it "
                 "said. OTA pages are never routing authority; CVB and "
                 "chamber directories anchor discovery only. No URL is "
                 "fabricated, no closure is inferred from a redirect, no "
                 "policy fact moves, and no approval is written."),
        ("results", results),
    ])

    summary = OrderedDict([
        ("queue_total", len(queue)),
        ("verdicts", dict(sorted(verdicts.items()))),
        ("routes_updated", len(updated)),
        ("routes_created", len(created)),
        ("manifest_reclassified", reclassified),
        ("capture_ready_rows", len(ready_rows)),
    ])

    if apply:
        write_lf(ROUTING_PATH, routing)
        # Manifest keeps the builder's byte-stable format (indent=1, LF).
        MANIFEST_PATH.write_bytes(
            (json.dumps(manifest, indent=1, ensure_ascii=False) + "\n")
            .encode("utf-8"))
        write_lf(RESULTS_PATH, results_doc)
        write_lf(QUEUE_OUT_PATH, queue_doc)
        from scripts.pettripfinder.cleveland_final_partition_002 import \
            _write_json as _write_partition, build_partition
        partition = build_partition()
        _write_partition(PARTITION_PATH, partition)
        counts = Counter(i["final_state"] for i in partition["items"])
        summary["final_state_counts"] = OrderedDict(sorted(counts.items()))
    return summary


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--apply", action="store_true")
    args = parser.parse_args()
    summary = run(args.apply)
    for key, value in summary.items():
        print("%s: %s" % (key, json.dumps(value)
                          if not isinstance(value, str) else value))
    if not args.apply:
        print("dry run: nothing written")
    return 0


if __name__ == "__main__":
    sys.exit(main())
