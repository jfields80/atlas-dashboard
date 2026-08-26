"""PTF-MILWAUKEE-MARKET-FACTORY-001 -- generate the committed Milwaukee artifacts.

Pure and deterministic: no network, no clock, no randomness. Every value in
``CANONICAL`` and ``NON_CANONICAL`` was READ from the source named on its row
during the work order; this module only reshapes those observations into the
committed contracts, so re-running it on any machine reproduces the committed
files byte for byte.

This is the FIRST stage of a two-stage pipeline. It writes the market as the
factory measured it; ``milwaukee_router_integration_001`` then applies the
sixteen official URLs recovered by PTF-MILWAUKEE-ACQUISITION-ROUTER-
INTEGRATION-001. Running this module alone therefore reproduces the factory
baseline, not the current committed census -- run both, in that order, to
reproduce what is committed.

Run from the repository root::

    python -m scripts.pettripfinder.build_milwaukee_market_001
    python -m scripts.pettripfinder.milwaukee_router_integration_001

It writes:

  launch_packages/pettripfinder/identity_census/milwaukee-wi.json
  launch_packages/pettripfinder/milwaukee_final_partition_001.json
  launch_packages/pettripfinder/milwaukee_candidate_ledger_001.json
  launch_packages/pettripfinder/markets/milwaukee-wi.json
  launch_packages/pettripfinder/markets/coverage/milwaukee-wi.json
  launch_packages/pettripfinder/markets/reports/milwaukee-wi_*.json

It does NOT write any authority. The market's routing, exclusion and seed
shards under markets/authority/milwaukee-wi/ were created empty by this work
order and stay empty until a work order with policy evidence fills them; this
module never opens them. It never touches the generated global compatibility
artifacts either -- those come from
scripts/pettripfinder/build_global_authority.py and from nowhere else.
"""

from __future__ import annotations

import hashlib
import json
import re
import sys
from pathlib import Path

REPO = Path(__file__).resolve().parents[2]
if str(REPO) not in sys.path:
    sys.path.insert(0, str(REPO))

from scripts.pettripfinder.contracts.identity_key import ptf_identity_key  # noqa: E402
from scripts.pettripfinder.markets.contract import slugify                # noqa: E402


MARKET = "milwaukee-wi"
WORK_ORDER = "PTF-MILWAUKEE-MARKET-FACTORY-001"
AS_OF = "2026-08-17"
BASE_COMMIT = "c236f52da26ac7b1fe531b2497cef5dfba67d9d2"
PKG = REPO / "launch_packages" / "pettripfinder"
REPORTS = PKG / "markets" / "reports"

CENSUS_SCHEMA = "ptf-market-identity-census/1.1"
PARTITION_SCHEMA = "ptf-market-final-partition/1.1"

# ------------------------------------------------------------------------- #
# The observed candidate universe. Every row was read from the source named
# in ``sources``; nothing here comes from an OTA or a map platform, and
# ``url`` is populated only where the URL itself was observed on a
# first-party brand index or on the property's own site.
# ------------------------------------------------------------------------- #

H = lambda s: "https://www.hilton.com/en/hotels/%s/" % s
M = lambda s: "https://www.marriott.com/en-us/hotels/%s/overview/" % s
I = lambda b, c, k: "https://www.ihg.com/%s/hotels/us/en/%s/%s/hoteldetail" % (b, c, k)
C = lambda p: "https://www.choicehotels.com%s" % p
W = lambda b, c, s: "https://www.wyndhamhotels.com/%s/%s/%s/overview" % (b, c, s)
B = lambda p: "https://www.bestwestern.com%s" % p

VM = "visit_milwaukee"
VW = "visit_waukesha_pewaukee"
VB = "visit_brookfield"
TW = "travel_wisconsin"
WH = "wi_lodging_association"
CH = "chain_locator"

# name, street, city, zip, phone, sources, url, extras
_C = "CANONICAL_CENSUS"

CANONICAL = [
    # ---------------- Downtown Milwaukee (53202) ----------------
    dict(name="Hilton Garden Inn Milwaukee Downtown", street="611 North Broadway", city="Milwaukee", zip="53202", phone="4142716611", sources=[CH, VM, WH], url=H("mkemdgi-hilton-garden-inn-milwaukee-downtown"), code="MKEMDGI"),
    dict(name="Home2 Suites by Hilton Milwaukee Downtown", street="515 N Jefferson St", city="Milwaukee", zip="53202", phone="4142408331", sources=[CH], url=H("mkesuht-home2-suites-milwaukee-downtown"), code="MKESUHT"),
    dict(name="Tru by Hilton Milwaukee Downtown", street="515 N Jefferson St", city="Milwaukee", zip="53202", phone="4142408331", sources=[CH, VM], url=H("mkesoru-tru-milwaukee-downtown"), code="MKESORU", former="Tru by Hilton Milwaukee"),
    dict(name="Homewood Suites by Hilton Milwaukee Downtown", street="500 N. Water Street", city="Milwaukee", zip="53202", phone="4145631090", sources=[CH, VM, WH], url=H("mkedohw-homewood-suites-milwaukee-downtown"), code="MKEDOHW"),
    dict(name="Drury Plaza Hotel Milwaukee Downtown", street="700 N. Water Street", city="Milwaukee", zip="53202", phone="4142247864", sources=[CH, VM, WH], url="", code=""),
    dict(name="Kimpton Journeyman Hotel", street="310 E. Chicago Street", city="Milwaukee", zip="53202", phone="4142913970", sources=[CH, VM, WH, TW], url=I("kimptonhotels", "journeyman-hotel-milwaukee-wi", "mketj"), code="MKETJ", former="The Kimpton Journeyman Hotel"),
    dict(name="The Pfister Hotel", street="424 E. Wisconsin Avenue", city="Milwaukee", zip="53202", phone="4142738222", sources=[VM, WH, TW], url=""),
    dict(name="The Westin Milwaukee", street="550 North Van Buren Street", city="Milwaukee", zip="53202", phone="4142245224", sources=[CH, VM, WH, TW], url=M("mkeiw-the-westin-milwaukee"), code="MKEIW"),
    dict(name="Milwaukee Marriott Downtown", street="625 N Milwaukee Street", city="Milwaukee", zip="53202", phone="4142785999", sources=[CH, VM, WH, TW], url=M("mkedn-milwaukee-marriott-downtown"), code="MKEDN"),
    dict(name="Knickerbocker on the Lake", street="1028 E. Juneau Avenue", city="Milwaukee", zip="53202", phone="4142768500", sources=[VM, WH, TW], url=""),
    dict(name="The Plaza Hotel Milwaukee", street="1007 N. Cass Street", city="Milwaukee", zip="53202", phone="4142762101", sources=[VM, WH, TW], url="", former="The Plaza Hotel"),
    dict(name="Dubbel Dutch Hotel", street="817 N Marshall St", city="Milwaukee", zip="53202", phone="4143763439", sources=[VM, TW], url="", former="Dubbel Dutch"),
    dict(name="Saint Kate - The Arts Hotel", street="139 E. Kilbourn Avenue", city="Milwaukee", zip="53202", phone="4142768686", sources=[VM, WH, TW], url=""),
    dict(name="Hotel Metro, Autograph Collection", street="411 East Mason Street", city="Milwaukee", zip="53202", phone="4142721937", sources=[CH, VM, WH, TW], url=M("mkeak-hotel-metro-autograph-collection"), code="MKEAK"),
    dict(name="Holiday Inn Express Milwaukee Downtown", street="525 N Jefferson Street", city="Milwaukee", zip="53202", phone="4142402896", sources=[CH, VM], url=I("holidayinnexpress", "milwaukee", "mkeem"), code="MKEEM"),
    dict(name="County Clare Irish Inn & Pub", street="1234 N Astor St", city="Milwaukee", zip="53202", phone="4142725273", sources=[TW], url=""),

    # ---------------- Downtown Milwaukee (53203) ----------------
    dict(name="Hilton Milwaukee", street="509 W. Wisconsin Avenue", city="Milwaukee", zip="53203", phone="4142717250", sources=[CH, VM, WH, TW], url=H("mkemhhf-hilton-milwaukee"), code="MKEMHHF", former="Hilton Milwaukee City Center"),
    dict(name="The Marc Hotel", street="640 N 6th Street", city="Milwaukee", zip="53203", phone="4143901800", sources=[WH], url=""),
    dict(name="DoubleTree by Hilton Hotel Milwaukee Downtown", street="611 W. Wisconsin Avenue", city="Milwaukee", zip="53203", phone="4142732950", sources=[CH, VM, TW], url=H("mkeccdt-doubletree-milwaukee-downtown"), code="MKECCDT"),
    dict(name="Cambria Hotel Milwaukee Downtown", street="503 N. Plankinton Ave", city="Milwaukee", zip="53203", phone="4142234484", sources=[CH, VM, TW], url=C("/wisconsin/milwaukee/cambria-hotels/wi297"), code="WI297"),
    dict(name="Courtyard by Marriott Milwaukee Downtown", street="300 W. Michigan Street", city="Milwaukee", zip="53203", phone="4142914122", sources=[CH, VM, WH, TW], url=M("mkedt-courtyard-milwaukee-downtown"), code="MKEDT"),
    dict(name="Residence Inn by Marriott Milwaukee Downtown", street="648 North Plankinton Avenue", city="Milwaukee", zip="53203", phone="4142247890", sources=[CH, VM, WH, TW], url=M("mkeri-residence-inn-milwaukee-downtown"), code="MKERI"),
    dict(name="SpringHill Suites by Marriott Milwaukee Downtown", street="744 Vel R Phillips Avenue", city="Milwaukee", zip="53203", phone="4142739811", sources=[CH, VM, WH], url=M("mkesh-springhill-suites-milwaukee-downtown"), code="MKESH"),
    dict(name="Fairfield by Marriott Inn & Suites Milwaukee Downtown", street="710 North Dr. Martin Luther King Jr. Drive", city="Milwaukee", zip="53203", phone="4146267100", sources=[CH, VM, WH, TW], url=M("mkefd-fairfield-inn-and-suites-milwaukee-downtown"), code="MKEFD", former="Fairfield Inn and Suites Milwaukee Downtown"),
    dict(name="Hampton Inn & Suites Milwaukee Downtown", street="176 W. Wisconsin Avenue", city="Milwaukee", zip="53203", phone="4142714656", sources=[CH, VM, TW], url=H("mkedwhx-hampton-suites-milwaukee-downtown"), code="MKEDWHX"),
    dict(name="Hyatt Regency Milwaukee", street="333 West Kilbourn Avenue", city="Milwaukee", zip="53203", phone="4142761234", sources=[CH, VM, WH, TW], url="https://www.hyatt.com/hyatt-regency/en-US/mkerm-hyatt-regency-milwaukee", code="MKERM"),
    dict(name="The Trade, Autograph Collection", street="420 West Juneau Avenue", city="Milwaukee", zip="53203", phone="4146440080", sources=[CH, VM, WH, TW], url=M("mkedd-the-trade-autograph-collection"), code="MKEDD"),

    # ---------------- Downtown Milwaukee (53204 / 53205 / 53212 / 53233) ----------------
    dict(name="The Iron Horse Hotel", street="500 W. Florida Street", city="Milwaukee", zip="53204", phone="4143744766", sources=[VM, TW], url=""),
    dict(name="Brewhouse Inn & Suites", street="1215 N. 10th Street", city="Milwaukee", zip="53205", phone="4148103350", sources=[VM, WH, TW], url=""),
    dict(name="Aloft by Marriott Milwaukee Downtown", street="1230 N. Dr. Martin Luther King Jr. Dr.", city="Milwaukee", zip="53212", phone="4142260122", sources=[CH, VM, WH, TW], url=M("mkeal-aloft-milwaukee-downtown"), code="MKEAL", former="Aloft Milwaukee Downtown"),
    dict(name="Days Inn & Suites by Wyndham Milwaukee", street="1840 North 6th Street", city="Milwaukee", zip="53212", phone="4149210304", sources=[CH, WH, TW], url=W("days-inn", "milwaukee-wisconsin", "days-inn-and-suites-milwaukee"), former="Hotel of the Arts"),
    dict(name="Ambassador Hotel Milwaukee, Trademark Collection by Wyndham", street="2308 W Wisconsin Avenue", city="Milwaukee", zip="53233", phone="4143455000", sources=[CH, VM, WH, TW], url=W("trademark", "milwaukee-wisconsin", "ambassador-hotel-trademark-collection")),
    dict(name="Ramada by Wyndham Milwaukee", street="2301 W Wisconsin Avenue", city="Milwaukee", zip="53233", phone="4143420000", sources=[CH, VM, WH], url=W("ramada", "milwaukee-wisconsin", "ramada-milwaukee"), former="Ambassador Inn at Marquette"),
    dict(name="Hyatt Place Milwaukee Downtown", street="800 W. Juneau Avenue", city="Milwaukee", zip="53233", phone="4148083880", sources=[CH, VM, WH], url=""),
    dict(name="Potawatomi Casino Hotel", street="1721 W. Canal Street", city="Milwaukee", zip="53233", phone="8007298866", sources=[VM, WH], url=""),
    dict(name="Biller Hotel", street="725 N. 22nd Street", city="Milwaukee", zip="53233", phone="4149336000", sources=[WH, TW], url="",
         lodging="NEEDS_REVIEW", hold="AWAITING_CENSUS_REVIEW",
         note="Long-running downtown property offering both nightly and extended-stay rooms. Listed as lodging by the Wisconsin Hotel & Lodging Association and by the state tourism registry, but its own description mixes transient rooms with temporary housing, so the current-category question is held open rather than assumed."),

    # ---------------- Milwaukee Airport & South (53207) ----------------
    dict(name="Best Western Plus Milwaukee Airport Hotel & Conference Center", street="5105 S Howell Avenue", city="Milwaukee", zip="53207", phone="4147692100", sources=[CH, VM, WH, TW], url=B("/en_US/book/hotels-in-milwaukee/best-western-plus-milwaukee-airport-hotel-conference-center/propertyCode.50056.html"), code="50056"),
    dict(name="Hilton Garden Inn Milwaukee Airport", street="5890 S. Howell Avenue", city="Milwaukee", zip="53207", phone="4148372424", sources=[CH, VM, WH, TW], url=H("mkegigi-hilton-garden-inn-milwaukee-airport"), code="MKEGIGI"),
    dict(name="Home2 Suites by Hilton Milwaukee Airport", street="5880 South Howell Avenue", city="Milwaukee", zip="53207", phone="4144812900", sources=[CH, VM, WH], url=H("mkeaiht-home2-suites-milwaukee-airport"), code="MKEAIHT"),
    dict(name="Clarion Pointe Milwaukee Airport", street="5037 S Howell Ave", city="Milwaukee", zip="53207", phone="", sources=[CH], url=C("/wisconsin/milwaukee/clarion-hotels/wi519"), code="WI519"),
    dict(name="Royle Hotel Milwaukee Airport", street="5311 S. Howell Ave.", city="Milwaukee", zip="53207", phone="4144812400", sources=[CH, VM], url=C("/wisconsin/milwaukee/choice-hotels/wi008"), code="WI008", former="Royle Hotel (Soon to be a Radisson) Milwaukee Airport a Choice Hotel"),
    dict(name="Super 8 by Wyndham Milwaukee Airport", street="5253 South Howell Avenue", city="Milwaukee", zip="53207", phone="4143955165", sources=[CH, TW], url=W("super-8", "milwaukee-wisconsin", "super-8-milwaukee-airport")),
    dict(name="Holiday Inn & Suites Milwaukee Airport", street="545 W. Layton Avenue", city="Milwaukee", zip="53207", phone="4144824444", sources=[CH, VM, TW], url=I("holidayinn", "milwaukee", "mkela"), code="MKELA"),
    dict(name="Courtyard by Marriott Milwaukee Airport", street="4620 South 5th Street", city="Milwaukee", zip="53207", phone="4147474405", sources=[CH, VM, WH], url=M("mkecy-courtyard-milwaukee-airport"), code="MKECY"),
    dict(name="Hyatt Place Milwaukee Airport", street="200 West Grange Avenue", city="Milwaukee", zip="53207", phone="4147443600", sources=[CH, VM, TW], url=""),

    # ---------------- Milwaukee Airport & South (53221) ----------------
    dict(name="Spark by Hilton Milwaukee Airport", street="4488 S 27th St", city="Milwaukee", zip="53221", phone="", sources=[CH], url=H("mkearpe-spark-milwaukee-airport"), code="MKEARPE", former="Quality Suites Milwaukee Airport"),
    dict(name="Rodeway Inn & Suites Milwaukee Airport", street="4400 S. 27th Street", city="Milwaukee", zip="53221", phone="", sources=[CH, TW], url=C("/wisconsin/milwaukee/rodeway-inn-hotels/wi121"), code="WI121"),
    dict(name="Suburban Studios Milwaukee Airport", street="4400 S. 27th Street, Building B", city="Milwaukee", zip="53221", phone="", sources=[CH], url=C("/wisconsin/milwaukee/suburban-hotels/wi451"), code="WI451"),
    dict(name="Country Inn & Suites by Radisson, Milwaukee Airport, WI", street="6200 South 13th Street", city="Milwaukee", zip="53221", phone="", sources=[CH, TW], url=C("/wisconsin/milwaukee/country-inn-suites-hotels/wi486"), code="WI486"),
    dict(name="Econo Lodge Milwaukee Airport", street="6541 S. 13th St.", city="Milwaukee", zip="53221", phone="", sources=[CH, TW], url=C("/wisconsin/milwaukee/econo-lodge-hotels/wi423"), code="WI423"),
    dict(name="Sleep Inn & Suites Milwaukee Airport", street="4600 South 6th Street", city="Milwaukee", zip="53221", phone="4143264599", sources=[CH, VM, TW], url=C("/wisconsin/milwaukee/sleep-inn-hotels/wi186"), code="WI186"),
    dict(name="Crowne Plaza Milwaukee Airport", street="6401 South 13th Street", city="Milwaukee", zip="53221", phone="4147645300", sources=[CH, VM, WH, TW], url=I("crowneplaza", "milwaukee", "mketh"), code="MKETH", former="Crowne Plaza Milwaukee South"),
    dict(name="Holiday Inn Express & Suites Milwaukee Airport", street="1400 W. Zellman Court", city="Milwaukee", zip="53221", phone="4143133687", sources=[CH, VM, WH, TW], url=I("holidayinnexpress", "milwaukee", "mkeoc"), code="MKEOC"),
    dict(name="Hampton Inn Milwaukee-Airport", street="1200 West College Avenue", city="Milwaukee", zip="53221", phone="4147624240", sources=[CH, VM, TW], url=H("mkeaphx-hampton-milwaukee-airport"), code="MKEAPHX"),
    dict(name="Travelodge by Wyndham Milwaukee", street="1716 W Layton Ave", city="Milwaukee", zip="53221", phone="4149145124", sources=[CH, WH], url=W("travelodge", "milwaukee-wisconsin", "travelodge-milwaukee"), former="Howard Johnson Inn Milwaukee Airport"),
    dict(name="Hideaway Inn", street="5105 S. 27th Street", city="Greenfield", zip="53221", phone="4142828500", sources=[WH], url=""),

    # ---------------- Northwest Milwaukee (53224 / 53225) ----------------
    dict(name="Hilton Garden Inn Milwaukee Northwest Conference Center", street="11600 West Park Place", city="Milwaukee", zip="53224", phone="4143599823", sources=[CH, VM, WH, TW], url=H("mkeppgi-hilton-garden-inn-milwaukee-northwest-conference-center"), code="MKEPPGI"),
    dict(name="Holiday Inn Express & Suites Milwaukee NW - Park Place", street="10831 W Park Place", city="Milwaukee", zip="53224", phone="4149790250", sources=[CH, VM, TW], url=I("holidayinnexpress", "milwaukee", "mkepp"), code="MKEPP", former="Comfort Suites Milwaukee Park Place"),
    dict(name="WoodSpring Suites Milwaukee - Menomonee Falls", street="12355 West Park Place", city="Milwaukee", zip="53224", phone="4142852102", sources=[CH], url="https://www.woodspring.com/extended-stay-hotels/locations/wisconsin/Menomonee-Falls/woodspring-suites-Milwuakee-Menomonee-Falls", code="WI366"),
    dict(name="Comfort Suites Milwaukee West", street="11777 W Silver Spring Drive", city="Milwaukee", zip="53225", phone="", sources=[CH], url=C("/wisconsin/milwaukee/comfort-suites-hotels/wi147"), code="WI147", former="Hyatt Place Milwaukee West"),
    dict(name="Hampton Inn Milwaukee-Northwest", street="5601 N. Lover's Lane Rd.", city="Milwaukee", zip="53225", phone="4144668881", sources=[CH, VM, TW], url=H("mkellhx-hampton-milwaukee-northwest"), code="MKELLHX", former="Hampton Inn by Hilton Milwaukee - Northwest"),

    # ---------------- North Shore / Glendale / Brown Deer / Mequon ----------------
    dict(name="Four Points by Sheraton Milwaukee North Shore", street="8900 North Kildeer Court", city="Milwaukee", zip="53209", phone="4143558585", sources=[CH, WH, TW], url=M("mkefp-four-points-milwaukee-north-shore"), code="MKEFP"),
    dict(name="Holiday Inn Milwaukee Riverfront", street="4700 N. Port Washington Road", city="Milwaukee", zip="53212", phone="4149626040", sources=[CH, VM, WH, TW], url=I("holidayinn", "milwaukee", "mkehi"), code="MKEHI"),
    dict(name="AmericInn by Wyndham Glendale/Milwaukee", street="5110 N Port Washington Rd", city="Glendale", zip="53217", phone="4149648484", sources=[CH, VM, TW], url=W("americinn", "glendale-wisconsin", "americinn-glendale-milwaukee"), former="La Quinta Inn Hampton Avenue"),
    dict(name="La Quinta Inn & Suites by Wyndham Milwaukee Bayshore Area", street="5423 N Port Washington Road", city="Glendale", zip="53217", phone="4149626767", sources=[CH, TW], url=W("laquinta", "glendale-wisconsin", "la-quinta-milwaukee-bayshore-area")),
    dict(name="Motel 6 Milwaukee, WI - Glendale", street="5485 North Port Washington Road", city="Glendale", zip="53217", phone="", sources=[CH, TW], url="https://www.motel6.com/property/motel-glendale-wisconsin-us-294362/"),
    dict(name="Hampton Inn Glendale Milwaukee", street="7065 North Port Washington Rd", city="Glendale", zip="53217", phone="4149283878", sources=[CH, VM, TW], url=H("mkepwhx-hampton-glendale-milwaukee"), code="MKEPWHX", former="Hampton Inn Milwaukee North/Glendale"),
    dict(name="Fairfield by Marriott Inn & Suites Milwaukee North", street="7035 North Port Washington Road", city="Glendale", zip="53217", phone="4144465900", sources=[CH, VM, TW], url=M("mkefi-fairfield-inn-and-suites-milwaukee-north"), code="MKEFI", former="Fairfield Inn & Suites Milwaukee North/Glendale"),
    dict(name="Residence Inn by Marriott Milwaukee North/Glendale", street="7003 North Port Washington Road", city="Glendale", zip="53217", phone="4144464295", sources=[CH, VM, TW], url=M("mkeng-residence-inn-milwaukee-north-glendale"), code="MKENG"),
    dict(name="Holiday Inn Express Milwaukee N-Brown Deer/Mequon", street="4443 W Schroeder Dr", city="Brown Deer", zip="53223", phone="", sources=[CH], url=I("holidayinnexpress", "brown-deer", "mkebd"), code="MKEBD"),
    dict(name="Candlewood Suites Milwaukee Brown Deer", street="4483 W Schroeder Dr", city="Brown Deer", zip="53223", phone="", sources=[CH, TW], url=I("candlewood", "brown-deer", "mkesd"), code="MKESD"),
    dict(name="Country Inn & Suites by Radisson, Brown Deer - Milwaukee North", street="5200 W Brown Deer Rd", city="Brown Deer", zip="53223", phone="", sources=[CH], url=C("/wisconsin/brown-deer/country-inn-suites-hotels/wi561"), code="WI561", former="Courtyard Milwaukee North"),
    dict(name="Baymont by Wyndham Mequon Milwaukee Area", street="10330 Port Washington Road", city="Mequon", zip="53092", phone="2622413677", sources=[CH, TW], url=W("baymont", "mequon-wisconsin", "baymont-inn-and-suites-mequon-milwaukee-area")),
    dict(name="Chalet Motel of Mequon", street="10401 N. Port Washington Road", city="Mequon", zip="53092", phone="8003434510", sources=[TW], url=""),
    dict(name="Mequon Country Inn - Sybaris", street="10240 N Cedarburg Rd", city="Mequon", zip="53092", phone="2622428000", sources=[TW], url="",
         identity="IDENTITY_PROVISIONAL", hold="AWAITING_IDENTITY_RESOLUTION",
         note="The state tourism registry carries one hotels-and-motels listing under a compound name that appears to describe two co-located businesses (a country inn and a Sybaris themed-suites property). No first-party page was found that settles whether this is one lodging identity or two, so the identity is provisional."),

    # ---------------- Oak Creek / Franklin / south suburbs ----------------
    dict(name="avid hotels Oak Creek", street="9293 South 13th Street", city="Oak Creek", zip="53154", phone="4146263099", sources=[CH, VM, TW], url=I("avidhotels", "oak-creek", "mkeco"), code="MKECO", former="Avid Hotel Oak Creek"),
    dict(name="Comfort Suites Milwaukee Airport", street="6362 S. 13th Street", city="Oak Creek", zip="53154", phone="4145701111", sources=[CH, VM, WH, TW], url=C("/wisconsin/oak-creek/comfort-suites-hotels/wi065"), code="WI065"),
    dict(name="Candlewood Suites Milwaukee Airport-Oak Creek", street="6440 S. 13th Street", city="Oak Creek", zip="53154", phone="", sources=[CH, WH, TW], url=I("candlewood", "oak-creek", "mkegw"), code="MKEGW"),
    dict(name="Fairfield by Marriott Inn & Suites Milwaukee Airport", street="6460 South 13th Street", city="Oak Creek", zip="53154", phone="4145708888", sources=[CH, VM, WH, TW], url=M("mkeap-fairfield-inn-and-suites-milwaukee-airport"), code="MKEAP", former="Fairfield Inn & Suites Milwaukee Airport"),
    dict(name="TownePlace Suites by Marriott Milwaukee Oak Creek", street="7980 South Market Street", city="Oak Creek", zip="53154", phone="4147647980", sources=[CH, VM, WH, TW], url=M("mkeok-towneplace-suites-milwaukee-oak-creek"), code="MKEOK"),
    dict(name="Homewood Suites by Hilton Oak Creek Milwaukee", street="1900 W. Creekside Crossing Circle", city="Oak Creek", zip="53154", phone="", sources=[CH, WH, TW], url=H("mkehohw-homewood-suites-oak-creek-milwaukee"), code="MKEHOHW"),
    dict(name="La Quinta Inn by Wyndham Milwaukee Airport / Oak Creek", street="7141 S 13th St.", city="Oak Creek", zip="53154", phone="4143692135", sources=[CH, TW], url=W("laquinta", "oak-creek-wisconsin", "la-quinta-inn-milwaukee-airport-oak-creek")),
    dict(name="Hawthorn Extended Stay by Wyndham Milwaukee Airport", street="1001 W College Avenue", city="Oak Creek", zip="53154", phone="4145718800", sources=[CH, TW], url=W("hawthorn-extended-stay", "oak-creek-wisconsin", "hawthorn-extended-stay-milwaukee-airport")),
    dict(name="Red Roof Inn Milwaukee - Airport/ Oak Creek", street="6360 South 13th Street", city="Oak Creek", zip="53154", phone="", sources=[CH, TW], url="https://www.redroof.com/property/wi/oak-creek/rri031", code="RRI031"),
    dict(name="Motel 6 Oak Creek, WI", street="1201 West College Avenue", city="Oak Creek", zip="53154", phone="", sources=[CH, TW], url="https://www.motel6.com/property/motel-oak-creek-wisconsin-us-293841/"),
    dict(name="Victoria Motel", street="10131 S. Chicago Road", city="Oak Creek", zip="53154", phone="4147626062", sources=[WH], url=""),
    dict(name="Hampton Inn & Suites Milwaukee/Franklin", street="6901 S. 76th Street", city="Franklin", zip="53132", phone="4144274800", sources=[CH, VM, WH, TW], url=H("mkefkhx-hampton-suites-milwaukee-franklin"), code="MKEFKHX"),
    dict(name="Sleep Inn & MainStay Suites Milwaukee/Franklin", street="6868 S. Ballpark Drive", city="Franklin", zip="53132", phone="4143007070", sources=[VM, CH], url="",
         identity="IDENTITY_PROVISIONAL", hold="AWAITING_IDENTITY_RESOLUTION",
         note="VISIT Milwaukee carries one combined listing while the Choice brand index carries two property codes at this address (wi391 Sleep Inn, wi392 MainStay Suites). The brand's own property pages refused automated access during this work order, so whether this is one dual-brand identity or two is unresolved rather than guessed. The postal code shown by the destination listing (53152) is not a Franklin ZIP and is recorded here as 53132, the ZIP every other source gives for this address."),
    dict(name="Staybridge Suites Milwaukee Airport South", street="9575 South 27th Street", city="Franklin", zip="53132", phone="", sources=[CH, TW], url=I("staybridge", "franklin", "mkefr"), code="MKEFR"),
    dict(name="Embassy Motel", street="8253 S 27th St", city="Franklin", zip="53132", phone="4147611234", sources=[TW], url=""),
    dict(name="American Motel", street="9335 S 27th St", city="Franklin", zip="53132", phone="4147612324", sources=[TW], url=""),
    dict(name="Golden Key Motel", street="3600 S 108th St", city="Greenfield", zip="53228", phone="4145435300", sources=[WH], url=""),

    # ---------------- Wauwatosa / West Allis / West Milwaukee ----------------
    dict(name="Renaissance Milwaukee West Hotel", street="2300 North Mayfair Road", city="Wauwatosa", zip="53226", phone="4147712300", sources=[CH, VM, TW], url=M("mkemr-renaissance-milwaukee-west-hotel"), code="MKEMR"),
    dict(name="Sonesta Milwaukee West Wauwatosa", street="10499 W. Innovation Dr.", city="Wauwatosa", zip="53226", phone="4144759500", sources=[TW], url=""),
    dict(name="Homewood Suites by Hilton Wauwatosa Milwaukee", street="11320 West Burleigh Street", city="Wauwatosa", zip="53222", phone="4144442844", sources=[CH, VM, WH, TW], url=H("mkewuhw-homewood-suites-wauwatosa-milwaukee"), code="MKEWUHW"),
    dict(name="SpringHill Suites by Marriott Milwaukee West/Wauwatosa", street="10411 West Watertown Plank Road", city="Wauwatosa", zip="53226", phone="4142573424", sources=[CH, VM, TW], url=M("mkesm-springhill-suites-milwaukee-west-wauwatosa"), code="MKESM"),
    dict(name="Residence Inn by Marriott Milwaukee West", street="1300 Discovery Parkway", city="Wauwatosa", zip="53226", phone="4142582575", sources=[CH, VM, WH, TW], url=M("mkewe-residence-inn-milwaukee-west"), code="MKEWE"),
    dict(name="Holiday Inn Express Milwaukee-West Medical Center", street="11111 West North Avenue", city="Wauwatosa", zip="53226", phone="4147780333", sources=[CH, VM, WH, TW], url=I("holidayinnexpress", "wauwatosa", "mkeex"), code="MKEEX"),
    dict(name="Extended Stay America - Milwaukee - Wauwatosa", street="11121 W. North Ave.", city="Wauwatosa", zip="53226", phone="4144431909", sources=[CH, TW], url="https://www.extendedstayamerica.com/hotels/wi/milwaukee/wauwatosa"),
    dict(name="Forty Winks Inn", street="11017 W. Bluemound Road", city="Wauwatosa", zip="53226", phone="4147742800", sources=[WH, TW], url=""),
    dict(name="Home2 Suites by Hilton Milwaukee West", street="1212 S. 70th Street", city="West Allis", zip="53214", phone="", sources=[CH, TW], url=H("mkemwht-home2-suites-milwaukee-west"), code="MKEMWHT"),
    dict(name="Hampton Inn & Suites Milwaukee West", street="8201 W. Greenfield Avenue", city="West Allis", zip="53214", phone="", sources=[CH, TW], url=H("mkewahx-hampton-suites-milwaukee-west"), code="MKEWAHX"),
    dict(name="Days Inn by Wyndham West Allis/Milwaukee", street="1673 South 108th Street", city="West Allis", zip="53214", phone="4145626816", sources=[CH, TW], url=W("days-inn", "west-allis-wisconsin", "days-inn-west-allis-milwaukee")),
    dict(name="Holiday Inn Express & Suites Milwaukee - West Allis", street="10111 West Lincoln Avenue", city="West Allis", zip="53227", phone="4143272200", sources=[CH, VM, WH, TW], url=I("holidayinnexpress", "west-allis", "mkell"), code="MKELL", former="Holiday Inn Express & Suites West Allis"),
    dict(name="Fairfield by Marriott Inn & Suites Milwaukee West", street="4229 West National Avenue", city="West Milwaukee", zip="53215", phone="4146452800", sources=[CH, VM, TW], url=M("mkefw-fairfield-inn-and-suites-milwaukee-west"), code="MKEFW", former="Fairfield Inn & Suites Milwaukee West"),

    # ---------------- Brookfield ----------------
    dict(name="DoubleTree by Hilton Hotel Milwaukee - Brookfield", street="18155 Bluemound Road", city="Brookfield", zip="53045", phone="2627921212", sources=[CH, VB, TW], url=H("mkebkdt-doubletree-milwaukee-brookfield"), code="MKEBKDT"),
    dict(name="Hilton Garden Inn Milwaukee Brookfield Conference Center", street="265 S. Moorland Road", city="Brookfield", zip="53005", phone="2623300800", sources=[CH, VB, WH], url=H("mkebcgi-hilton-garden-inn-milwaukee-brookfield-conference-center"), code="MKEBCGI"),
    dict(name="Hampton Inn Milwaukee/Brookfield", street="575 North Barker Road", city="Brookfield", zip="53045", phone="2627961500", sources=[CH, VM, WH, TW], url=H("mkebfhx-hampton-milwaukee-brookfield"), code="MKEBFHX"),
    dict(name="Embassy Suites by Hilton Milwaukee Brookfield", street="1200 South Moorland Road", city="Brookfield", zip="53005", phone="2627822900", sources=[CH, VM, VB, WH, TW], url=H("mkembes-embassy-suites-milwaukee-brookfield"), code="MKEMBES"),
    dict(name="Sheraton Milwaukee Brookfield Hotel", street="375 South Moorland Road", city="Brookfield", zip="53005", phone="2623641100", sources=[CH, VM, VB, WH, TW], url=M("mkesi-sheraton-milwaukee-brookfield-hotel"), code="MKESI"),
    dict(name="Courtyard by Marriott Milwaukee Brookfield at Poplar Creek", street="20300 West Bluemound Road", city="Brookfield", zip="53045", phone="2622054900", sources=[CH, VM, TW], url=M("mkeby-courtyard-milwaukee-brookfield-at-poplar-creek"), code="MKEBY", former="Courtyard Milwaukee Brookfield at Poplar Creek"),
    dict(name="Residence Inn by Marriott Milwaukee Brookfield at Poplar Creek", street="20300 West Bluemound Road", city="Brookfield", zip="53045", phone="2622054912", sources=[CH, VM, TW], url=M("mkebi-residence-inn-milwaukee-brookfield-at-poplar-creek"), code="MKEBI"),
    dict(name="Residence Inn by Marriott Milwaukee Brookfield", street="765 Pinehurst Court", city="Brookfield", zip="53005", phone="2627820765", sources=[CH, VM, VB, WH], url=M("mkerb-residence-inn-milwaukee-brookfield"), code="MKERB"),
    dict(name="Fairfield by Marriott Inn & Suites Milwaukee Brookfield", street="135 Discovery Drive", city="Brookfield", zip="53045", phone="2622054450", sources=[CH, VB], url=M("mkefb-fairfield-inn-and-suites-milwaukee-brookfield"), code="MKEFB"),
    dict(name="TownePlace Suites by Marriott Milwaukee Brookfield", street="600 North Calhoun Road", city="Brookfield", zip="53005", phone="2627848450", sources=[CH, VB, TW], url=M("mkets-towneplace-suites-milwaukee-brookfield"), code="MKETS"),
    dict(name="Holiday Inn Brookfield - Milwaukee", street="1005 South Moorland Road", city="Brookfield", zip="53005", phone="2627869540", sources=[CH, VM, VB, TW], url=I("holidayinn", "brookfield", "mkebr"), code="MKEBR", former="Midway Hotel & Suites Brookfield"),
    dict(name="Holiday Inn Express & Suites Milwaukee - Brookfield", street="115 Discovery Drive", city="Brookfield", zip="53045", phone="2622145600", sources=[CH, VB], url=I("holidayinnexpress", "brookfield", "mkebf"), code="MKEBF"),
    dict(name="Country Inn & Suites by Radisson, Milwaukee West (Brookfield), WI", street="1250 S Moorland Road", city="Brookfield", zip="53005", phone="2627821400", sources=[CH, VB, TW], url=C("/wisconsin/brookfield/country-inn-suites-hotels/wi489"), code="WI489"),
    dict(name="AmericInn by Wyndham Brookfield", street="16865 W Bluemound Rd", city="Brookfield", zip="53005", phone="2622995640", sources=[CH, VB, TW], url=W("americinn", "brookfield-wisconsin", "americinn-brookfield"), former="Sonesta Select Milwaukee Brookfield"),
    dict(name="Motel 6 Suites Milwaukee Brookfield, WI", street="325 North Brookfield Road", city="Brookfield", zip="53045", phone="", sources=[CH], url="https://www.motel6.com/property/motel-brookfield-wisconsin-us-368045/"),
    dict(name="Studio 6 Extended Stay Milwaukee Brookfield WI", street="325 North Brookfield Road", city="Brookfield", zip="53045", phone="", sources=[CH, TW], url="https://www.motel6.com/property/motel-milwaukee-wi-wisconsin-us-357314/", former="Extended Stay America Suites Milwaukee Brookfield"),

    # ---------------- Waukesha / Pewaukee / New Berlin ----------------
    dict(name="Tru by Hilton Milwaukee Brookfield", street="20925 Watertown Road", city="Waukesha", zip="53186", phone="2623368800", sources=[CH, VM, TW], url=H("mkeboru-tru-milwaukee-brookfield"), code="MKEBORU"),
    dict(name="Home2 Suites by Hilton Milwaukee Brookfield", street="650 Larry Court", city="Waukesha", zip="53186", phone="2623421500", sources=[CH, VM, TW], url=H("mkebrht-home2-suites-milwaukee-brookfield"), code="MKEBRHT"),
    dict(name="Milwaukee Marriott West", street="W231N1600 Corporate Ct", city="Waukesha", zip="53186", phone="2625740888", sources=[CH, VW, TW], url=M("mkemw-milwaukee-marriott-west"), code="MKEMW"),
    dict(name="Comfort Inn Waukesha - Milwaukee West", street="2510 Plaza Court", city="Waukesha", zip="53186", phone="2627866015", sources=[CH, VW, TW], url=C("/wisconsin/waukesha/comfort-inn-hotels/wi007"), code="WI007", former="Super 8 by Wyndham Waukesha"),
    dict(name="Extended Stay America - Milwaukee - Waukesha", street="2520 Plaza Ct.", city="Waukesha", zip="53186", phone="2627980217", sources=[CH, VW, TW], url="https://www.extendedstayamerica.com/hotels/wi/milwaukee/waukesha"),
    dict(name="Baymont by Wyndham Waukesha", street="2111 East Moreland Blvd", city="Waukesha", zip="53186", phone="2622327980", sources=[CH, VW, TW], url=W("baymont", "waukesha-wisconsin", "baymont-inn-and-suites-waukesha")),
    dict(name="The Clarke Hotel", street="314 W. Main St.", city="Waukesha", zip="53186", phone="2625493800", sources=[VW, WH], url=""),
    dict(name="Cobblestone Hotel & Suites - Waukesha/West Milwaukee", street="704 N. Grand Avenue", city="Waukesha", zip="53186", phone="2622905667", sources=[VW, CH], url="https://staycobblestone.com/wi/waukesha/"),
    dict(name="Price Pointe Inn", street="532 Bluemound Road", city="Waukesha", zip="53188", phone="4142136861", sources=[VW, WH], url=""),
    dict(name="Best Western Waukesha Grand", street="2840 N Grandview Boulevard", city="Pewaukee", zip="53072", phone="2625249300", sources=[CH, VW, WH, TW], url=B("/en_US/book/hotels-in-pewaukee/best-western-waukesha-grand/propertyCode.50116.html"), code="50116"),
    dict(name="Holiday Inn Pewaukee-Milwaukee West", street="N14 W24140 Tower Place", city="Pewaukee", zip="53072", phone="2625066300", sources=[CH, VW, TW], url=I("holidayinn", "pewaukee", "pkehi"), code="PKEHI"),
    dict(name="avid hotels Milwaukee West - Waukesha", street="2101 Meadow Lane", city="Pewaukee", zip="53072", phone="", sources=[CH, VW], url=I("avidhotels", "waukesha", "mkeav"), code="MKEAV"),
    dict(name="Wildwood Lodge", street="N14 W24121 Tower Place", city="Pewaukee", zip="53072", phone="2625062000", sources=[VW, TW], url="https://thewildwoodlodge.com/pewaukee/"),
    dict(name="The Ingleside Hotel", street="2810 Golf Road", city="Pewaukee", zip="53072", phone="2625470201", sources=[VM, VW, WH, TW], url=""),
    dict(name="La Quinta Inn & Suites by Wyndham Milwaukee SW New Berlin", street="15300 W Rock Ridge Rd.", city="New Berlin", zip="53151", phone="2627170900", sources=[CH, TW], url=W("laquinta", "new-berlin-wisconsin", "la-quinta-milwaukee-sw-new-berlin")),
    dict(name="Holiday Inn Express & Suites Milwaukee-New Berlin", street="15451 W. Beloit Road", city="New Berlin", zip="53151", phone="", sources=[CH, TW], url=I("holidayinnexpress", "new-berlin", "mkenb"), code="MKENB"),

    # ---------------- Menomonee Falls / Germantown ----------------
    dict(name="Delta Hotels Milwaukee Northwest", street="N88 W14750 Main Street", city="Menomonee Falls", zip="53051", phone="2622515153", sources=[CH, WH, TW], url=M("mkedm-delta-hotels-milwaukee-northwest"), code="MKEDM", former="Delta Hotels by Marriott Milwaukee Northwest"),
    dict(name="SpringHill Suites by Marriott Menomonee Falls", street="N 91 W 15901 Falls Parkway", city="Menomonee Falls", zip="53051", phone="2625099100", sources=[CH], url=M("mkems-springhill-suites-menomonee-falls"), code="MKEMS"),
    dict(name="Home2 Suites by Hilton Menomonee Falls Milwaukee", street="N91 W15851 Falls Parkway", city="Menomonee Falls", zip="53051", phone="", sources=[CH], url=H("mkemfht-home2-suites-menomonee-falls-milwaukee"), code="MKEMFHT"),
    dict(name="Best Western Germantown Inn", street="W190N10862 Commerce Circle", city="Germantown", zip="53022", phone="2625029750", sources=[CH, TW], url=B("/en_US/book/hotels-in-germantown/best-western-germantown-inn/propertyCode.50140.html"), code="50140"),
    dict(name="Comfort Inn & Suites NW Milwaukee", street="W177 N9675 Riversbend Lane", city="Germantown", zip="53022", phone="", sources=[CH, TW], url=C("/wisconsin/germantown/comfort-inn-hotels/wi426"), code="WI426"),
    dict(name="Country Inn & Suites by Radisson, Germantown, WI", street="W188 N11020 Maple Road", city="Germantown", zip="53022", phone="", sources=[CH, TW], url=C("/wisconsin/germantown/country-inn-suites-hotels/wi483"), code="WI483"),
    dict(name="Super 8 by Wyndham Germantown/Milwaukee", street="N 96 W 17490 County Line Rd", city="Germantown", zip="53022", phone="2625090896", sources=[CH, WH, TW], url=W("super-8", "germantown-wisconsin", "super-8-germantown-milwaukee")),

    # ---------------- Held for category review ----------------
    dict(name="Kinn Guesthouse Downtown Milwaukee", street="600 N. Broadway", city="Milwaukee", zip="53202", phone="8555466653", sources=[VM, WH], url="",
         lodging="NEEDS_REVIEW", hold="AWAITING_CENSUS_REVIEW",
         note="VISIT Milwaukee groups it with bed-and-breakfasts and guest houses, while the state tourism registry files the Kinn properties under hotels and motels. The two official taxonomies disagree, so the current-category question is held rather than decided."),
    dict(name="Kinn Guesthouse Bay View", street="2535 S. Kinnickinnic Avenue", city="Milwaukee", zip="53207", phone="", sources=[VM, WH, TW], url="",
         lodging="NEEDS_REVIEW", hold="AWAITING_CENSUS_REVIEW",
         note="Same conflicting official taxonomies as the downtown Kinn property; held for the same reason."),
    dict(name="Best Western Plus Milwaukee West", street="5501 W National Ave", city="Milwaukee", zip="53214", phone="4146716400", sources=[TW], url="",
         identity="IDENTITY_UNRESOLVED", hold="AWAITING_IDENTITY_RESOLUTION",
         note="Carried by the state tourism registry but absent from Best Western's own current property sitemap, which lists exactly one Milwaukee property (the airport hotel). A missing brand route is not closure evidence, so the identity is unresolved: either the property left the brand under a new name or the registry entry is stale."),
]

# --------------------------------------------------------------------------- #
# Candidates that are NOT canonical census identities.
# --------------------------------------------------------------------------- #

NON_CANONICAL = [
    # --- confirmed duplicates / superseded identities (same building) ---
    dict(name="Hotel of the Arts", street="1840 N. 6th Street", city="Milwaukee", zip="53212", sources=[WH, TW], disposition="CONFIRMED_DUPLICATE", dup="Days Inn & Suites by Wyndham Milwaukee", reason="The property's own site markets it as 'Hotel of the Arts Days Inn & Suites'; Wyndham's live property page carries the same street address under the brand name. One building, one identity."),
    dict(name="Quality Suites Milwaukee Airport", street="4488 S. 27th Street", city="Milwaukee", zip="53221", sources=[CH, TW], disposition="CONFIRMED_DUPLICATE", dup="Spark by Hilton Milwaukee Airport", reason="Converted from Choice to Spark by Hilton at the same address; Hilton's live locator carries 4488 S 27th St as Spark by Hilton Milwaukee Airport. The Choice brand index entry is stale."),
    dict(name="Sonesta Select Milwaukee Brookfield", street="16865 W Bluemound Rd", city="Brookfield", zip="53005", sources=[TW, VB], disposition="CONFIRMED_DUPLICATE", dup="AmericInn by Wyndham Brookfield", reason="Sonesta's own property page no longer resolves and redirects to its state index, while Wyndham's live property page carries this address as AmericInn by Wyndham Brookfield and Visit Brookfield has renamed its listing to AmericInn."),
    dict(name="Howard Johnson Inn Milwaukee Airport", street="1716 W Layton Ave", city="Milwaukee", zip="53221", sources=[CH], disposition="CONFIRMED_DUPLICATE", dup="Travelodge by Wyndham Milwaukee", reason="Wyndham's sitemap still carries the Howard Johnson slug but its property page no longer resolves; the live Travelodge property page carries the same street address."),
    dict(name="Super 8 by Wyndham Waukesha", street="2510 Plaza Court", city="Waukesha", zip="53186", sources=[CH], disposition="CONFIRMED_DUPLICATE", dup="Comfort Inn Waukesha - Milwaukee West", reason="Wyndham's property page no longer resolves; Choice's live brand index carries the same street address as Comfort Inn Waukesha - Milwaukee West."),
    dict(name="Ambassador Inn at Marquette", street="2301 W. Wisconsin Avenue", city="Milwaukee", zip="53233", sources=[TW], disposition="CONFIRMED_DUPLICATE", dup="Ramada by Wyndham Milwaukee", reason="Same street address as the live Ramada property page; a former identity of the same building."),
    dict(name="Midway Hotel & Suites Brookfield", street="1005 S Moorland Rd", city="Brookfield", zip="53005", sources=[TW], disposition="CONFIRMED_DUPLICATE", dup="Holiday Inn Brookfield - Milwaukee", reason="Same street address as IHG's live Holiday Inn Brookfield property page."),
    dict(name="Hyatt Place Milwaukee West", street="11777 W Silver Spring Drive", city="Milwaukee", zip="53225", sources=[TW], disposition="CONFIRMED_DUPLICATE", dup="Comfort Suites Milwaukee West", reason="Hyatt's own worldwide property dataset carries exactly three Milwaukee-area properties and none at this address; Choice's live brand index carries it as Comfort Suites Milwaukee West."),
    dict(name="Courtyard Milwaukee North", street="5200 W. Brown Deer Road", city="Brown Deer", zip="53223", sources=[TW], disposition="CONFIRMED_DUPLICATE", dup="Country Inn & Suites by Radisson, Brown Deer - Milwaukee North", reason="Absent from Marriott's current Wisconsin property sitemap; Choice's live brand index carries the same address."),
    dict(name="Comfort Suites Milwaukee Park Place", street="10831 W Park Place", city="Milwaukee", zip="53224", sources=[TW], disposition="CONFIRMED_DUPLICATE", dup="Holiday Inn Express & Suites Milwaukee NW - Park Place", reason="Same street address as IHG's live property page; absent from Choice's current brand index."),
    dict(name="La Quinta Inn Hampton Avenue", street="5110 N Port Washington Rd", city="Glendale", zip="53217", sources=[TW], disposition="CONFIRMED_DUPLICATE", dup="AmericInn by Wyndham Glendale/Milwaukee", reason="Same street address as the live AmericInn property page on Wyndham's own site."),
    dict(name="Extended Stay America Suites Milwaukee Brookfield", street="325 N Brookfield Rd", city="Brookfield", zip="53045", sources=[TW], disposition="CONFIRMED_DUPLICATE", dup="Studio 6 Extended Stay Milwaukee Brookfield WI", reason="Extended Stay America's own Wisconsin locations index lists only Appleton, Madison and Milwaukee (Wauwatosa and Waukesha). Motel 6's live property record carries this address as Studio 6."),
    dict(name="Hilton Milwaukee City Center", street="509 W. Wisconsin Avenue", city="Milwaukee", zip="53203", sources=[TW], disposition="CONFIRMED_DUPLICATE", dup="Hilton Milwaukee", reason="Former name of the same property; Hilton's own locator now calls it Hilton Milwaukee."),
    dict(name="Sleep Inn Milwaukee/Franklin", street="6868 S. Ballpark Drive", city="Franklin", zip="53132", sources=[CH], disposition="SOURCE_LISTING_ALREADY_ACCOUNTED_FOR", dup="Sleep Inn & MainStay Suites Milwaukee/Franklin", reason="Choice property code wi391 at the Ballpark Commons address; carried by the held combined identity pending resolution."),
    dict(name="MainStay Suites Milwaukee/Franklin", street="6868 S. Ballpark Drive", city="Franklin", zip="53132", sources=[CH], disposition="SOURCE_LISTING_ALREADY_ACCOUNTED_FOR", dup="Sleep Inn & MainStay Suites Milwaukee/Franklin", reason="Choice property code wi392 at the Ballpark Commons address; carried by the held combined identity pending resolution."),

    # --- category exclusions ---
    dict(name="The Muse Gallery Guesthouse", street="602 E. Lincoln Avenue", city="Milwaukee", zip="53207", sources=[VM], disposition="CATEGORY_EXCLUDED", reason="VISIT Milwaukee lists it under bed-and-breakfasts and guest houses; a guesthouse is outside the current PetTripFinder lodging category."),
    dict(name="Marquette University Residence Halls", street="1442 W. Wisconsin Avenue", city="Milwaukee", zip="53233", sources=[VM], disposition="CATEGORY_EXCLUDED", reason="University student housing offered as summer accommodation; not transient hotel lodging."),
    dict(name="StayMKE", street="", city="Milwaukee", zip="53213", sources=[VM], disposition="CATEGORY_EXCLUDED", reason="A short-term-rental management brand rather than a single lodging property; no street address is published."),
    dict(name="RV Park at Wisconsin State Fair Park", street="601 S. 76th Street", city="Milwaukee", zip="53214", sources=[VM], disposition="CATEGORY_EXCLUDED", reason="RV park; outside the current lodging category."),
    dict(name="The Inn on the Olde Homestead", street="N4 W22496 Bluemound Rd", city="Waukesha", zip="53186", sources=[VW], disposition="CATEGORY_EXCLUDED", reason="Bed-and-breakfast inn; outside the current lodging category."),
    dict(name="Brumder Mansion Bed and Breakfast", street="3046 W Wisconsin Ave", city="Milwaukee", zip="53208", sources=["secondary_discovery"], disposition="CATEGORY_EXCLUDED", reason="Bed-and-breakfast; outside the current lodging category. Surfaced only by secondary discovery, not by any official inventory used here."),
    dict(name="Schuster Mansion Bed & Breakfast", street="3209 W Wells St", city="Milwaukee", zip="53208", sources=["secondary_discovery"], disposition="CATEGORY_EXCLUDED", reason="Bed-and-breakfast; outside the current lodging category. Surfaced only by secondary discovery."),

    # --- boundary exclusions ---
    dict(name="Delafield Hotel", street="415 Genesee Street", city="Delafield", zip="53018", sources=[VM, WH], disposition="BOUNDARY_EXCLUDED", reason="Western Waukesha County Lake Country; outside the Greater Milwaukee traveler boundary set by this work order."),
    dict(name="La Quinta Inn & Suites by Wyndham Milwaukee Delafield", street="2801 Hillside Drive", city="Delafield", zip="53018", sources=[CH, TW], disposition="BOUNDARY_EXCLUDED", reason="Delafield / Lake Country; outside the boundary despite the Milwaukee brand name."),
    dict(name="AmericInn by Wyndham Delafield", street="2412 Milwaukee Street", city="Delafield", zip="53018", sources=[CH], disposition="BOUNDARY_EXCLUDED", reason="Delafield / Lake Country; outside the boundary."),
    dict(name="Holiday Inn Express & Suites Delafield", street="3030 Golf Road", city="Delafield", zip="53018", sources=[CH], disposition="BOUNDARY_EXCLUDED", reason="Delafield / Lake Country; outside the boundary."),
    dict(name="Hilton Garden Inn Oconomowoc", street="1443 Pabst Farms Circle", city="Oconomowoc", zip="53066", sources=[CH], disposition="BOUNDARY_EXCLUDED", reason="Oconomowoc / Lake Country, roughly thirty miles west of downtown Milwaukee; outside the boundary."),
    dict(name="TownePlace Suites by Marriott Oconomowoc", street="1242 Corporate Center Drive", city="Oconomowoc", zip="53066", sources=[CH], disposition="BOUNDARY_EXCLUDED", reason="Oconomowoc / Lake Country; outside the boundary."),
    dict(name="Staybridge Suites Milwaukee West-Oconomowoc", street="1141 Blue Ribbon Drive", city="Oconomowoc", zip="53066", sources=[CH, TW], disposition="BOUNDARY_EXCLUDED", reason="Oconomowoc / Lake Country; outside the boundary despite the Milwaukee brand name."),
    dict(name="Mon Bijou", street="E Lisbon Rd", city="Oconomowoc", zip="53066", sources=[WH], disposition="BOUNDARY_EXCLUDED", reason="Oconomowoc / Lake Country; outside the boundary."),
    dict(name="Hampton Inn & Suites Grafton", street="1385 Gateway Drive", city="Grafton", zip="53024", sources=[CH], disposition="BOUNDARY_EXCLUDED", reason="Ozaukee County outer ring, oriented to Grafton-Cedarburg rather than to a named Milwaukee traveler cluster."),
    dict(name="TownePlace Suites by Marriott Milwaukee Grafton", street="1601 Gateway Drive", city="Grafton", zip="53024", sources=[CH], disposition="BOUNDARY_EXCLUDED", reason="Ozaukee County outer ring; outside the boundary despite the Milwaukee brand name."),
    dict(name="Comfort Inn & Suites Grafton-Cedarburg", street="1415 Port Washington Road", city="Grafton", zip="53024", sources=[CH], disposition="BOUNDARY_EXCLUDED", reason="Ozaukee County outer ring; the brand's own name orients it to Grafton-Cedarburg."),
    dict(name="Baymont by Wyndham Grafton Milwaukee", street="", city="Grafton", zip="", sources=[CH], disposition="BOUNDARY_EXCLUDED", reason="Ozaukee County outer ring; outside the boundary. Surfaced only as a Wyndham sitemap slug whose property page no longer resolves."),
    dict(name="Hampton Inn & Suites West Bend", street="1975 South 18th Avenue", city="West Bend", zip="53095", sources=[CH], disposition="BOUNDARY_EXCLUDED", reason="Washington County outer ring, roughly thirty-five miles from downtown Milwaukee; outside the boundary."),
    dict(name="TownePlace Suites by Marriott Milwaukee West Bend", street="175 East Water Street", city="West Bend", zip="53095", sources=[CH], disposition="BOUNDARY_EXCLUDED", reason="Washington County outer ring; outside the boundary despite the Milwaukee brand name."),
    dict(name="AmericInn by Wyndham West Bend", street="2424 West Washington Street", city="West Bend", zip="53095", sources=[CH], disposition="BOUNDARY_EXCLUDED", reason="Washington County outer ring; outside the boundary."),
    dict(name="Country Inn & Suites by Radisson, West Bend, WI", street="2000 Gateway Court", city="West Bend", zip="53095", sources=[CH, WH], disposition="BOUNDARY_EXCLUDED", reason="Washington County outer ring; outside the boundary."),
    dict(name="Quality Inn & Suites West Bend", street="W. Washington Street", city="West Bend", zip="53095", sources=[CH, WH], disposition="BOUNDARY_EXCLUDED", reason="Washington County outer ring; outside the boundary."),
    dict(name="Motel 6 Saukville, WI", street="180 South Foster Dr", city="Saukville", zip="53080", sources=[CH], disposition="BOUNDARY_EXCLUDED", reason="Ozaukee County outer ring; outside the boundary."),
    dict(name="Comfort Inn & Suites Jackson - West Bend", street="W227 N16890 Tillie Lake Crt", city="Jackson", zip="53037", sources=[CH], disposition="BOUNDARY_EXCLUDED", reason="Washington County outer ring; outside the boundary."),
    dict(name="The Harborview on Lake Michigan, an Ascend Collection Hotel", street="135 East Grand Avenue", city="Port Washington", zip="53074", sources=[CH], disposition="BOUNDARY_EXCLUDED", reason="Port Washington, Ozaukee County lakeshore; a separate leisure destination outside the boundary."),
    dict(name="Holiday Inn Express & Suites Port Washington", street="350 E Seven Hills Road", city="Port Washington", zip="53074", sources=[CH], disposition="BOUNDARY_EXCLUDED", reason="Port Washington, Ozaukee County lakeshore; outside the boundary."),
    dict(name="Washington House Inn", street="W62 N573 Washington Avenue", city="Cedarburg", zip="53012", sources=[VM], disposition="BOUNDARY_EXCLUDED", reason="Cedarburg, Ozaukee County; outside the boundary."),
    dict(name="Erin Hills Golf Course", street="7169 County Road O", city="Hartford", zip="53027", sources=[WH], disposition="BOUNDARY_EXCLUDED", reason="Washington County golf resort roughly forty miles from downtown Milwaukee; outside the boundary."),
    dict(name="DoubleTree by Hilton Hotel Racine Harbourwalk", street="223 Gaslight Circle", city="Racine", zip="53403", sources=[CH], disposition="BOUNDARY_EXCLUDED", reason="Racine is its own traveler market, not part of Greater Milwaukee."),
    dict(name="Home2 Suites by Hilton Racine", street="1301 West Road", city="Sturtevant", zip="53177", sources=[CH], disposition="BOUNDARY_EXCLUDED", reason="Racine County; outside the boundary."),
    dict(name="Delta Hotels Mount Pleasant", street="7111 Washington Avenue Hwy 20", city="Mount Pleasant", zip="53406", sources=[CH], disposition="BOUNDARY_EXCLUDED", reason="Racine County; outside the boundary."),
    dict(name="Fairfield by Marriott Inn & Suites Mount Pleasant, WI", street="7111 Washington Avenue", city="Mount Pleasant", zip="53406", sources=[CH], disposition="BOUNDARY_EXCLUDED", reason="Racine County; outside the boundary."),
    dict(name="Holiday Inn Express & Suites Racine", street="13317 Hospitality Court", city="Mount Pleasant", zip="53177", sources=[CH], disposition="BOUNDARY_EXCLUDED", reason="Racine County; outside the boundary."),
    dict(name="Staybridge Suites Racine - Mount Pleasant", street="7430 Washington Ave", city="Mount Pleasant", zip="53406", sources=[CH], disposition="BOUNDARY_EXCLUDED", reason="Racine County; outside the boundary."),
    dict(name="Clarion Pointe Racine - Mount Pleasant", street="1154 Prairie Dr.", city="Racine", zip="53406", sources=[CH], disposition="BOUNDARY_EXCLUDED", reason="Racine County; outside the boundary."),
    dict(name="Comfort Inn Mount Pleasant - Racine", street="1150 Oakes Rd", city="Racine", zip="53406", sources=[CH], disposition="BOUNDARY_EXCLUDED", reason="Racine County; outside the boundary."),
    dict(name="Country Inn & Suites by Radisson, Mt. Pleasant-Racine West, WI", street="13339 Hospitality Court", city="Mount Pleasant", zip="53177", sources=[CH], disposition="BOUNDARY_EXCLUDED", reason="Racine County; outside the boundary."),
    dict(name="SureStay by Best Western Mount Pleasant Racine", street="", city="Mount Pleasant", zip="", sources=[CH], disposition="BOUNDARY_EXCLUDED", reason="Racine County; outside the boundary."),
    dict(name="Americas Best Value Inn & Suites Racine", street="", city="Racine", zip="", sources=[CH], disposition="BOUNDARY_EXCLUDED", reason="Racine County; the only Sonesta-family property the brand's own Wisconsin index carries."),
    dict(name="Jellystone Park Camp-Resort in Caledonia", street="8425 Highway 38", city="Caledonia", zip="53108", sources=[VM], disposition="BOUNDARY_EXCLUDED", reason="Racine County, and a camp-resort rather than hotel lodging; excluded on boundary first."),
    dict(name="Grand Geneva Resort & Spa", street="7036 Grand Geneva Way", city="Lake Geneva", zip="53147", sources=[VM, CH], disposition="BOUNDARY_EXCLUDED", reason="Lake Geneva resort market; outside the boundary."),
    dict(name="Destination Geneva National", street="1221 Geneva National Avenue South", city="Lake Geneva", zip="53147", sources=[VM], disposition="BOUNDARY_EXCLUDED", reason="Lake Geneva resort market; outside the boundary."),
    dict(name="Fairfield by Marriott Inn & Suites Lake Geneva", street="1111 North Edwards Boulevard", city="Lake Geneva", zip="53147", sources=[CH], disposition="BOUNDARY_EXCLUDED", reason="Lake Geneva resort market; outside the boundary."),
    dict(name="Inn on Woodlake", street="705 Woodlake Road", city="Kohler", zip="53044", sources=[VM], disposition="BOUNDARY_EXCLUDED", reason="Kohler / Sheboygan County resort destination; outside the boundary."),
    dict(name="The American Club - Destination Kohler", street="419 Highland Drive", city="Kohler", zip="53044", sources=[VM], disposition="BOUNDARY_EXCLUDED", reason="Kohler / Sheboygan County resort destination; outside the boundary."),
    dict(name="Lazy Days Campgrounds", street="1475 Lakeview Road", city="West Bend", zip="53090", sources=[VM], disposition="BOUNDARY_EXCLUDED", reason="Washington County campground; outside the boundary and outside the lodging category."),

    # --- brand-delisted slugs with no recoverable current identity ---
    dict(name="Baymont Inn & Suites Glendale Milwaukee N Area", street="", city="Glendale", zip="", sources=[CH], disposition="IDENTITY_UNRESOLVED", reason="Surfaced only as a Wyndham sitemap slug; the brand's own property page no longer resolves and no other source family carries the identity. A missing brand route is not closure evidence, so neither a live identity nor a closure is established."),
    dict(name="Days Inn Milwaukee Airport", street="", city="Milwaukee", zip="", sources=[CH], disposition="IDENTITY_UNRESOLVED", reason="Surfaced only as a Wyndham sitemap slug whose property page no longer resolves; no address is published by any source used here."),
    dict(name="Days Inn Wauwatosa Milwaukee", street="", city="Wauwatosa", zip="", sources=[CH], disposition="IDENTITY_UNRESOLVED", reason="Surfaced only as a Wyndham sitemap slug whose property page no longer resolves."),
    dict(name="Days Inn Oak Creek Milwaukee Airport", street="", city="Oak Creek", zip="", sources=[CH], disposition="IDENTITY_UNRESOLVED", reason="Surfaced only as a Wyndham sitemap slug whose property page no longer resolves."),
    dict(name="Super 8 Wauwatosa Med Ctr Milwaukee West", street="", city="Wauwatosa", zip="", sources=[CH], disposition="IDENTITY_UNRESOLVED", reason="Surfaced only as a Wyndham sitemap slug whose property page no longer resolves; the street address is not published by any source used here."),
    dict(name="Super 8 West Bend", street="", city="West Bend", zip="", sources=[CH], disposition="BOUNDARY_EXCLUDED", reason="Washington County outer ring; outside the boundary. Also a Wyndham slug whose property page no longer resolves."),
]



# --------------------------------------------------------------------------- #
# Corridors
# --------------------------------------------------------------------------- #

CORRIDORS = [
    dict(slug="downtown-milwaukee", name="Downtown Milwaukee, Third Ward & Near West Side",
         area="Downtown Milwaukee",
         desc="The walkable downtown core: East Town and the lakefront, Westown and the "
              "Baird Center, the Historic Third Ward, Walker's Point, the Brewery District "
              "and the Marquette/Near West Side.",
         zips=["53202", "53203", "53204", "53205", "53212", "53233"], cities=[], explicit=[]),
    dict(slug="milwaukee-airport-south", name="Milwaukee Airport & South Side",
         area="Milwaukee Airport",
         desc="The Mitchell International Airport hotel strip along South Howell Avenue and "
              "South 13th/27th Street, plus Bay View and the south-side approach to the city.",
         zips=["53207", "53221"], cities=[], explicit=[]),
    dict(slug="milwaukee-northwest", name="Northwest Milwaukee / Park Place",
         area="Northwest Milwaukee",
         desc="The Park Place and Silver Spring business corridor in far northwest Milwaukee, "
              "off US-45 and Good Hope Road.",
         zips=["53224", "53225"], cities=[], explicit=[]),
    dict(slug="milwaukee-north-shore", name="North Shore, Glendale & Brown Deer",
         area="Glendale & the North Shore",
         desc="The Port Washington Road corridor through Glendale and Bayshore, the Brown Deer "
              "and Schroeder Drive cluster, and the Mequon edge of the North Shore.",
         zips=["53209"],
         cities=["Glendale", "Brown Deer", "Mequon", "Bayside", "Whitefish Bay", "Shorewood",
                 "Fox Point", "River Hills"],
         explicit=["holiday inn milwaukee riverfront"]),
    dict(slug="oak-creek-franklin", name="Oak Creek, Franklin & the South Suburbs",
         area="Oak Creek & Franklin",
         desc="The I-94 south corridor through Oak Creek and Franklin, including Drexel Town "
              "Square and Ballpark Commons, plus the Greenfield and Greendale suburbs.",
         zips=[],
         cities=["Oak Creek", "Franklin", "Greenfield", "Greendale", "Hales Corners",
                 "Cudahy", "South Milwaukee", "Saint Francis"],
         explicit=[]),
    dict(slug="wauwatosa-west-allis", name="Wauwatosa & West Allis",
         area="Wauwatosa & West Allis",
         desc="The Milwaukee Regional Medical Center and Innovation Drive campus, Mayfair, "
              "and the State Fair Park side of West Allis and West Milwaukee.",
         zips=["53214"], cities=["Wauwatosa", "West Allis", "West Milwaukee"], explicit=[]),
    dict(slug="brookfield", name="Brookfield",
         area="Brookfield",
         desc="The Bluemound Road and Moorland Road hotel corridor in eastern Waukesha County, "
              "around Brookfield Square and the Brookfield Conference Center.",
         zips=[], cities=["Brookfield", "Elm Grove"], explicit=[]),
    dict(slug="waukesha-pewaukee", name="Waukesha, Pewaukee & New Berlin",
         area="Waukesha & Pewaukee",
         desc="The I-94 west corridor through Pewaukee and Waukesha, downtown Waukesha, and "
              "the New Berlin business parks.",
         zips=[], cities=["Waukesha", "Pewaukee", "New Berlin", "Muskego"], explicit=[]),
    dict(slug="menomonee-falls-germantown", name="Menomonee Falls & Germantown",
         area="Menomonee Falls & Germantown",
         desc="The US-41/45 northwest corridor through Menomonee Falls and Germantown, the "
              "outer edge of the Milwaukee visitor market on that side.",
         zips=[], cities=["Menomonee Falls", "Germantown", "Butler", "Sussex"], explicit=[]),
]

BOUNDARY_NOTE = (
    "PTF-MILWAUKEE-MARKET-FACTORY-001 Greater Milwaukee traveler market, not a "
    "county line and not the full Milwaukee-Racine-Waukesha CSA. INCLUDED: all of "
    "Milwaukee County (Milwaukee, Wauwatosa, West Allis, West Milwaukee, Oak Creek, "
    "Franklin, Greenfield, Greendale, Glendale, Brown Deer and the North Shore "
    "villages); the eastern Waukesha County I-94 corridor (Brookfield, Elm Grove, "
    "Waukesha, Pewaukee, New Berlin, Menomonee Falls); and two contiguous outer-ring "
    "municipalities whose lodging is named for and oriented to Milwaukee -- Germantown "
    "(Washington County, contiguous with Menomonee Falls; every hotel there brands "
    "itself 'Milwaukee' or 'NW Milwaukee') and Mequon (Ozaukee County, contiguous with "
    "the Brown Deer cluster). EXCLUDED as deliberate boundary decisions, each recorded "
    "in the candidate ledger with its reason: western Waukesha County / Lake Country "
    "(Delafield, Oconomowoc); the Washington County outer ring (West Bend, Jackson, "
    "Hartford); the Ozaukee outer ring (Grafton, Cedarburg, Saukville, Port "
    "Washington); Racine and Kenosha counties, which are their own traveler markets; "
    "and the Lake Geneva and Kohler resort destinations. Milwaukee-city identities are "
    "assigned by postal code because one city name spans four distinct traveler areas; "
    "every suburb is assigned by city and state. Exactly one identity carries an "
    "explicit assignment: Holiday Inn Milwaukee Riverfront has a Milwaukee 53212 "
    "mailing address but sits on the Glendale riverfront, so a ZIP match would place "
    "it downtown. This market publishes nothing in this work order."
)

# --------------------------------------------------------------------------- #
# Derivation
# --------------------------------------------------------------------------- #


def corridor_id(slug):
    return "%s__%s" % (MARKET, slug)


def assign(row):
    """Reproduce the assignment tiers: explicit, then ZIP, then city+state."""
    key = ptf_identity_key(row["name"])
    for c in CORRIDORS:
        if key in c["explicit"]:
            return corridor_id(c["slug"]), "explicit", key
    for c in CORRIDORS:
        if row["zip"] and row["zip"] in c["zips"]:
            return corridor_id(c["slug"]), "postal_code", row["zip"]
    for c in CORRIDORS:
        if row["city"] and row["city"].lower() in [x.lower() for x in c["cities"]]:
            return corridor_id(c["slug"]), "city_state", "%s, %s" % (row["city"].lower(), "WI")
    raise SystemExit("UNASSIGNED: %s (%s %s)" % (row["name"], row["city"], row["zip"]))


def build_census():
    hotels = []
    for row in CANONICAL:
        key = ptf_identity_key(row["name"])
        cid, basis, value = assign(row)
        hotels.append({
            "identity_key": key,
            "canonical_name": row["name"],
            "display_name": row["name"],
            "slug": slugify(row["name"]),
            "market_id": MARKET,
            "address": row["street"],
            "city": row["city"],
            "state": "WI",
            "postal_code": row["zip"],
            "phone": row.get("phone", ""),
            "identity_state": row.get("identity", "IDENTITY_CONFIRMED"),
            "lodging_state": row.get("lodging", "LODGING_CONFIRMED"),
            "policy_state": "POLICY_NOT_VERIFIED",
            "collision_state": "NONE",
            "official_url": row.get("url", ""),
            "property_code": row.get("code", ""),
            "corridor": cid,
            "assignment_basis": basis,
            "assignment_value": value,
            "source": row["sources"][0],
            "corroborating_sources": row["sources"][1:],
            "observed_at": AS_OF,
            "provenance": "%s:%s" % (WORK_ORDER, row["sources"][0]),
            "normalized_name": key,
            "former_name": row.get("former", ""),
            "url_shape": "property" if row.get("url") else "",
            "disposition": "canonical",
            "street_identity": "%s|%s" % (row["street"].lower(), row["zip"]),
            "census_note": row.get("note", ""),
        })
    hotels.sort(key=lambda h: h["identity_key"])
    # A shared street address or switchboard is a FACT about the site, not a
    # duplicate identity: each of these pairs is a dual-brand or twin property
    # carrying two distinct property codes on the brand's own index. Recorded
    # so the state is visible rather than implied by a note.
    by_addr, by_phone = {}, {}
    for h in hotels:
        if h["address"]:
            by_addr.setdefault(h["street_identity"], []).append(h)
        if h["phone"]:
            by_phone.setdefault(h["phone"], []).append(h)
    for group in by_addr.values():
        if len(group) > 1:
            for h in group:
                h["collision_state"] = "SHARED_ADDRESS"
    for group in by_phone.values():
        if len(group) > 1:
            for h in group:
                if h["collision_state"] == "NONE":
                    h["collision_state"] = "SHARED_PHONE"
    return hotels


def collision_audit(hotels):
    by_addr, by_phone, by_name = {}, {}, {}
    for h in hotels:
        if h["address"]:
            by_addr.setdefault(h["street_identity"], []).append(h["canonical_name"])
        if h["phone"]:
            by_phone.setdefault(h["phone"], []).append(h["canonical_name"])
        by_name.setdefault(h["identity_key"], []).append(h["canonical_name"])
    addr = {k: v for k, v in by_addr.items() if len(v) > 1}
    phone = {k: v for k, v in by_phone.items() if len(v) > 1}
    dup = {k: v for k, v in by_name.items() if len(v) > 1}
    return addr, phone, dup


PARTITION_MEANINGS = {
    "AWAITING_POLICY_OBSERVATION":
        "The route is sound and the page served its content, but no pet policy has "
        "ever been observed on it. UNKNOWN, never a refusal.",
    "AWAITING_OFFICIAL_URL":
        "No official URL has ever been found for this identity. The census confirms "
        "the property exists; nothing says where its page is.",
    "AWAITING_CENSUS_REVIEW":
        "The identity's presence or category in the census is itself in question.",
    "AWAITING_IDENTITY_RESOLUTION":
        "Identity is provisional or unresolved, so policy work cannot safely bind to "
        "this record.",
}

NEXT_ACTIONS = {
    "AWAITING_POLICY_OBSERVATION":
        "Capture the property's pet-policy surface on its own official page.",
    "AWAITING_OFFICIAL_URL":
        "Recover the property's own official URL from a first-party surface before any "
        "policy work begins.",
    "AWAITING_CENSUS_REVIEW":
        "Decide the current-category question for this identity before it enters any "
        "capture queue.",
    "AWAITING_IDENTITY_RESOLUTION":
        "Resolve the identity from a first-party surface before binding a route to it.",
}


def build_partition(hotels):
    items = []
    for h in hotels:
        row = next(r for r in CANONICAL if ptf_identity_key(r["name"]) == h["identity_key"])
        state = row.get("hold")
        if state is None:
            state = "AWAITING_POLICY_OBSERVATION" if h["official_url"] else "AWAITING_OFFICIAL_URL"
        items.append({
            "identity_key": h["identity_key"],
            "canonical_name": h["canonical_name"],
            "slug": h["slug"],
            "city": h["city"],
            "state": "WI",
            "postal_code": h["postal_code"],
            "final_state": state,
            "resolved": False,
            "next_action": NEXT_ACTIONS[state],
            "next_action_source": "identity_census/%s.json" % MARKET,
            "determined_by": WORK_ORDER,
            "updated_at": AS_OF,
            "official_url": h["official_url"],
            "state_override_reason": row.get("note", ""),
        })
    return items


CAPTURE_READINESS = {
    # Brands whose surfaces this repository has already established need an
    # attended browser or a fresh session; recorded as planning only.
    "hilton.com": "FRESH_SESSION_REQUIRED",
    "marriott.com": "FRESH_SESSION_REQUIRED",
    "ihg.com": "ATTENDED_REQUIRED",
    "choicehotels.com": "SPECIAL_SURFACE_REQUIRED",
    "wyndhamhotels.com": "EVIDENCE_READY",
    "bestwestern.com": "EVIDENCE_READY",
    "extendedstayamerica.com": "EVIDENCE_READY",
    "redroof.com": "ATTENDED_REQUIRED",
    "motel6.com": "EVIDENCE_READY",
    "hyatt.com": "ATTENDED_REQUIRED",
    "woodspring.com": "EVIDENCE_READY",
    "staycobblestone.com": "EVIDENCE_READY",
    "thewildwoodlodge.com": "EVIDENCE_READY",
}


def readiness_for(url):
    if not url:
        return "POLICY_SURFACE_UNKNOWN"
    host = re.sub(r"^https?://(www\.)?", "", url).split("/")[0]
    return CAPTURE_READINESS.get(host, "POLICY_SURFACE_UNKNOWN")


def routing_status(row):
    if row.get("identity") in ("IDENTITY_PROVISIONAL", "IDENTITY_UNRESOLVED"):
        return "IDENTITY_REVIEW_NEEDED"
    if row.get("lodging") == "NEEDS_REVIEW":
        return "IDENTITY_REVIEW_NEEDED"
    if not row.get("url"):
        return "ROUTING_RECOVERY_NEEDED"
    host = re.sub(r"^https?://(www\.)?", "", row["url"]).split("/")[0]
    if host == "choicehotels.com":
        return "SPECIAL_ACCESS"
    return "PROPERTY_LEVEL_ROUTE_CONFIRMED"


def write(path, doc):
    """Write LF-exact bytes.

    ``Path.write_text`` translates newlines on Windows and would produce a file
    whose shape depends on who ran the build. .gitattributes already forces LF
    for committed authority artifacts; writing bytes removes the ambiguity a
    layer earlier, exactly as ``market_authority._write_if_changed`` does.
    """
    path.parent.mkdir(parents=True, exist_ok=True)
    text = json.dumps(doc, indent=1, ensure_ascii=False) + "\n"
    path.write_bytes(text.encode("utf-8"))
    return path


def main():
    hotels = build_census()
    keys = [h["identity_key"] for h in hotels]
    assert len(keys) == len(set(keys)), "duplicate identity keys"
    addr, phone, dup = collision_audit(hotels)

    census = {
        "schema": CENSUS_SCHEMA,
        "market_id": MARKET,
        "identity_key_contract": "ptf_identity_key/1.0",
        "identity_contract": "ptf-identity-evidence/1.0",
        "work_order": WORK_ORDER,
        "captured_at": AS_OF,
        "note": (
            "Greater Milwaukee traveler-market census built from five independent source "
            "families: VISIT Milwaukee's complete listing inventory (every one of its 1,552 "
            "committed listings was read and the 86 in its Sleep category extracted, plus one "
            "hotel it files under Attractions), the Waukesha-Pewaukee and Brookfield "
            "destination bureaus, ten hotel-brand locators read from each brand's own "
            "property index, the Wisconsin Department of Tourism's statewide lodging registry "
            "(all 1,115 hotel-and-motel listings read), and the Wisconsin Hotel & Lodging "
            "Association's member directory. No OTA and no map platform was used as census "
            "authority. No policy authority exists for this market: every policy_state is "
            "POLICY_NOT_VERIFIED by construction and no pet-policy wording was inspected."
        ),
        "source_authorities": [
            "https://www.visitmilwaukee.org/places-to-stay/",
            "https://visitwaukesha.org/where-to-stay/",
            "https://www.visitbrookfield.com/business-directory/categories/hotels-and-accommodations/",
            "https://www.travelwisconsin.com/stay/hotels-motels",
            "https://web.wisconsinlodging.org/Lodging",
            "brand property indexes: hilton.com, marriott.com, ihg.com, hyatt.com, "
            "choicehotels.com, wyndhamhotels.com, bestwestern.com, extendedstayamerica.com, "
            "redroof.com, motel6.com, druryhotels.com, woodspring.com, sonesta.com, "
            "staycobblestone.com, thewildwoodlodge.com",
        ],
        "count": len(hotels),
        "base_commit": BASE_COMMIT,
        "collision_audit": {
            "duplicate_names_found": len(dup),
            "duplicate_names": sorted(dup),
            "phone_collisions": sorted(phone),
            "address_collisions": sorted(addr),
            "address_collision_detail": {k: sorted(v) for k, v in sorted(addr.items())},
            "out_of_boundary": 0,
            "cross_market_collisions": [],
            "notes": (
                "Every shared street address in this market is a genuine dual-brand or "
                "twin-property site confirmed by two property codes on the brand's own "
                "index, not a duplicate identity."
            ),
            "status": "RESOLVED",
            "open_conflict_count": 0,
        },
        "identity_state_counts": {
            s: sum(1 for h in hotels if h["identity_state"] == s)
            for s in ("IDENTITY_CONFIRMED", "IDENTITY_PROVISIONAL", "IDENTITY_UNRESOLVED")
        },
        "source_methodology": (
            "Every canonical row's name, address and postal code was read from a first-party "
            "brand property index, an official destination-marketing inventory, the state "
            "tourism registry or the state lodging association's member directory. Where a "
            "brand index and a destination listing disagreed on a property's name, the "
            "brand's own current name was taken as canonical and the other recorded as "
            "former_name. No closure was recorded from the absence of a brand route alone."
        ),
        "worker_branch": "grok/ptf-milwaukee-market-001",
        "worker_run": WORK_ORDER,
        "hotels": hotels,
    }
    write(PKG / "identity_census" / ("%s.json" % MARKET), census)

    items = build_partition(hotels)
    counts = {}
    for i in items:
        counts[i["final_state"]] = counts.get(i["final_state"], 0) + 1
    partition = {
        "schema": PARTITION_SCHEMA,
        "work_order": WORK_ORDER,
        "market_id": MARKET,
        "as_of": AS_OF,
        "note": (
            "No committed policy authority exists for this market: published=0 and "
            "verified_no_pets=0 by construction. Every identity carries exactly one blocker "
            "and one next action; none is terminal."
        ),
        "source_authorities": ["identity_census/%s.json" % MARKET],
        "count": len(items),
        "final_state_counts": counts,
        "final_state_meanings": {k: PARTITION_MEANINGS[k] for k in sorted(counts)},
        "items": items,
    }
    write(PKG / "milwaukee_final_partition_001.json", partition)

    # ------------------------------------------------------------------ ledger
    rows = []
    n = 0
    for row in CANONICAL:
        n += 1
        rows.append({
            "ledger_id": "MKE-CAND-%03d" % n,
            "candidate_name": row["name"],
            "identity_key": ptf_identity_key(row["name"]),
            "address": row["street"],
            "city": row["city"],
            "state": "WI",
            "postal_code": row["zip"],
            "phone": row.get("phone", ""),
            "sources": row["sources"],
            "official_url": row.get("url", ""),
            "observed_at": AS_OF,
            "disposition": "CANONICAL_CENSUS",
            "disposition_reason": row.get("note") or (
                "Transient lodging inside the Greater Milwaukee traveler boundary, confirmed "
                "by %d source famil%s." % (len(row["sources"]),
                                           "y" if len(row["sources"]) == 1 else "ies")),
            "duplicate_of": "",
            "former_name": row.get("former", ""),
        })
    for row in NON_CANONICAL:
        n += 1
        rows.append({
            "ledger_id": "MKE-CAND-%03d" % n,
            "candidate_name": row["name"],
            "identity_key": ptf_identity_key(row["name"]),
            "address": row.get("street", ""),
            "city": row.get("city", ""),
            "state": "WI",
            "postal_code": row.get("zip", ""),
            "phone": "",
            "sources": row["sources"],
            "official_url": "",
            "observed_at": AS_OF,
            "disposition": row["disposition"],
            "disposition_reason": row["reason"],
            "duplicate_of": row.get("dup", ""),
            "former_name": "",
        })
    dcounts = {}
    for r in rows:
        dcounts[r["disposition"]] = dcounts.get(r["disposition"], 0) + 1
    ledger = {
        "schema": "ptf-market-candidate-ledger/1.0",
        "work_order": WORK_ORDER,
        "market_id": MARKET,
        "as_of": AS_OF,
        "note": (
            "One row per lodging-looking candidate surfaced during Milwaukee discovery. "
            "Every candidate carries exactly one disposition and the reason for it; nothing "
            "was discarded silently, including candidates that turned out to be former "
            "identities of properties already in the census."
        ),
        "count": len(rows),
        "disposition_counts": {k: dcounts[k] for k in sorted(dcounts)},
        "rows": rows,
    }
    write(PKG / "milwaukee_candidate_ledger_001.json", ledger)

    # ------------------------------------------------------------- duplicates
    dl = [r for r in rows if r["disposition"] in
          ("CONFIRMED_DUPLICATE", "BOUNDARY_EXCLUDED", "CATEGORY_EXCLUDED",
           "IDENTITY_UNRESOLVED", "SOURCE_LISTING_ALREADY_ACCOUNTED_FOR")]
    write(REPORTS / ("%s_duplicate_ledger.json" % MARKET), {
        "schema": "ptf-milwaukee-duplicate-ledger/1.0",
        "work_order": WORK_ORDER,
        "market_id": MARKET,
        "as_of": AS_OF,
        "counts": {
            "canonical": len(CANONICAL),
            "duplicate": dcounts.get("CONFIRMED_DUPLICATE", 0),
            "source_listing_already_accounted_for": dcounts.get("SOURCE_LISTING_ALREADY_ACCOUNTED_FOR", 0),
            "boundary_excluded": dcounts.get("BOUNDARY_EXCLUDED", 0),
            "category_excluded": dcounts.get("CATEGORY_EXCLUDED", 0),
            "identity_unresolved_ledger_only": dcounts.get("IDENTITY_UNRESOLVED", 0),
            "closed": 0,
        },
        "items": [{
            "identity_key": r["identity_key"],
            "canonical_name": r["candidate_name"],
            "disposition": r["disposition"].lower(),
            "duplicate_of": r["duplicate_of"],
            "notes": r["disposition_reason"],
            "source": r["sources"][0],
        } for r in dl],
    })

    # ------------------------------------------------------- source registry
    write(REPORTS / ("%s_source_registry.json" % MARKET), {
        "schema": "ptf-milwaukee-source-registry/1.0",
        "work_order": WORK_ORDER,
        "market_id": MARKET,
        "as_of": AS_OF,
        "count": len(SOURCES),
        "sources": SOURCES,
    })

    # --------------------------------------------------- routing assessments
    ritems = []
    for row in CANONICAL:
        key = ptf_identity_key(row["name"])
        ritems.append({
            "identity_key": key,
            "canonical_name": row["name"],
            "official_url": row.get("url", ""),
            "property_code": row.get("code", ""),
            "url_shape": "property" if row.get("url") else "",
            "binding_method": "BRAND_INDEX_BINDING" if row.get("url") else "",
            "routing_readiness": routing_status(row),
            "capture_readiness": readiness_for(row.get("url", "")),
            "assessment_status": "ASSESSMENT_ONLY",
            "not_routing_authority": True,
            "source": row["sources"][0],
            "verified_at": AS_OF,
        })
    ritems.sort(key=lambda r: r["identity_key"])
    rr = {}
    cr = {}
    for r in ritems:
        rr[r["routing_readiness"]] = rr.get(r["routing_readiness"], 0) + 1
        cr[r["capture_readiness"]] = cr.get(r["capture_readiness"], 0) + 1
    write(REPORTS / ("%s_routing_assessments.json" % MARKET), {
        "schema": "ptf-milwaukee-routing-assessments/1.0",
        "work_order": WORK_ORDER,
        "market_id": MARKET,
        "as_of": AS_OF,
        "note": (
            "Assessments only. Nothing here is written to any routing authority: the market's "
            "routing shard is empty and no record carries ROUTING_CONFIRMED. A URL recorded "
            "here was observed on the brand's own property index, which is a routing binding "
            "and never publication-grade evidence."
        ),
        "count": len(ritems),
        "routing_readiness_counts": {k: rr[k] for k in sorted(rr)},
        "capture_readiness_counts": {k: cr[k] for k in sorted(cr)},
        "items": ritems,
    })

    # -------------------------------------------------- founder review queue
    qitems = []
    for idx, i in enumerate(items, start=1):
        payload = json.dumps({k: i[k] for k in sorted(i)}, ensure_ascii=False,
                             sort_keys=True).encode("utf-8")
        qitems.append({
            "row_number": idx,
            "identity_key": i["identity_key"],
            "hotel_id": i["identity_key"],
            "canonical_name": i["canonical_name"],
            "address": next(h["address"] for h in hotels if h["identity_key"] == i["identity_key"]),
            "phone": next(h["phone"] for h in hotels if h["identity_key"] == i["identity_key"]),
            "official_candidate_url": i["official_url"],
            "corridor": next(h["corridor"] for h in hotels if h["identity_key"] == i["identity_key"]),
            "current_classification": i["final_state"],
            "blocking_reason": i["final_state"],
            "requested_evidence": "citable pet-policy artifact from the property's own page"
            if i["final_state"] == "AWAITING_POLICY_OBSERVATION"
            else "first-party evidence that resolves the blocker named above",
            "next_action": i["next_action"],
            "batch": "batch-%03d" % (((idx - 1) // 10) + 1),
            "review_status": "NOT_STARTED",
            "row_sha256": hashlib.sha256(payload).hexdigest(),
        })
    write(REPORTS / ("%s_founder_review_queue.json" % MARKET), {
        "schema": "ptf-milwaukee-founder-review-queue/1.0",
        "work_order": WORK_ORDER,
        "market_id": MARKET,
        "as_of": AS_OF,
        "count": len(qitems),
        "batch_size": 10,
        "items": qitems,
    })

    # ------------------------------------------------ census completeness
    write(REPORTS / ("%s_census_completeness.json" % MARKET), completeness(hotels, dcounts, rr, cr))

    # ----------------------------------------------------------- market config
    write(PKG / "markets" / ("%s.json" % MARKET), market_config())

    # --------------------------------------------------------- coverage config
    write(PKG / "markets" / "coverage" / ("%s.json" % MARKET), {
        "schema": "ptf-coverage-config/1.0",
        "market_id": MARKET,
        "_note": (
            "Advisory coverage-audit configuration for the Milwaukee factory census. "
            "Uncalibrated priors. Nothing gates on this file. The source-family overrides "
            "are the mechanism a post-sharding market uses to declare its own sources "
            "instead of appending to the shared CONCRETE_SOURCE_FAMILY table."
        ),
        "census_kind": "identity_census",
        "population": 1560000,
        "thresholds": {},
        "non_independent_family_pairs": [],
        "source_family_overrides": {
            "visit_milwaukee": "CVB",
            "visit_waukesha_pewaukee": "CVB",
            "visit_brookfield": "CVB",
            "travel_wisconsin": "REGISTRY",
            "wi_lodging_association": "DIRECTORY",
            "secondary_discovery": "DIRECTORY",
        },
        "zones_min_expected": {},
        "accepted_gaps": [],
    })

    print("census      %d" % len(hotels))
    print("partition   %s" % counts)
    print("ledger      %d %s" % (len(rows), dcounts))
    print("routing     %s" % rr)
    print("capture     %s" % cr)
    print("addr collisions %d  phone collisions %d" % (len(addr), len(phone)))
    for k, v in sorted(addr.items()):
        print("   shared address:", k, "->", sorted(v))


SOURCES = [
    dict(source_id="visit_milwaukee", name="VISIT Milwaukee listing inventory",
         organization="VISIT Milwaukee (Greater Milwaukee Convention & Visitors Bureau)",
         source_type="CVB", family="CVB",
         url="https://www.visitmilwaukee.org/places-to-stay/",
         geographic_coverage="Milwaukee County and the surrounding visitor market, plus "
                             "outlying Wisconsin destinations the bureau promotes",
         data_categories=["lodging"], access_date=AS_OF,
         status="authority_for_identity",
         limitations=(
             "Partner-based: it carries no Days Inn, Super 8, La Quinta, Motel 6, Red Roof, "
             "Extended Stay America or WoodSpring property, and it files Potawatomi Casino "
             "Hotel under Attractions rather than Sleep. Its listings also carry a small "
             "number of postal-code defects (Franklin 53152 for a 53132 address). Every one "
             "of its 1,552 listings was read and classified rather than trusting its Sleep "
             "landing page."),
         automated_access="static_html"),
    dict(source_id="visit_waukesha_pewaukee", name="Visit Waukesha Pewaukee Where to Stay",
         organization="Waukesha Pewaukee Convention and Visitors Bureau",
         source_type="CVB", family="CVB",
         url="https://visitwaukesha.org/where-to-stay/",
         geographic_coverage="Waukesha and Pewaukee",
         data_categories=["lodging"], access_date=AS_OF,
         status="authority_for_identity",
         limitations=("Names and phone numbers only; the listing pages do not publish street "
                      "addresses, which were taken from each property's own site."),
         automated_access="static_html"),
    dict(source_id="visit_brookfield", name="Visit Brookfield hotels and accommodations directory",
         organization="Visit Brookfield",
         source_type="CVB", family="CVB",
         url="https://www.visitbrookfield.com/business-directory/categories/hotels-and-accommodations/",
         geographic_coverage="Brookfield",
         data_categories=["lodging", "official_url"], access_date=AS_OF,
         status="authority_for_identity",
         limitations=("Eleven listings. One listing's name and its linked website disagree "
                      "(AmericInn Brookfield linking a Sonesta URL), which is what surfaced "
                      "that property's rebrand."),
         automated_access="rendered_dom"),
    dict(source_id="travel_wisconsin", name="Travel Wisconsin statewide lodging registry",
         organization="Wisconsin Department of Tourism",
         source_type="STATE_TOURISM_REGISTRY", family="REGISTRY",
         url="https://www.travelwisconsin.com/stay/hotels-motels",
         geographic_coverage="All of Wisconsin",
         data_categories=["lodging", "address"], access_date=AS_OF,
         status="authority_for_identity",
         limitations=(
             "Carries stale entries alongside live ones -- ten of its Milwaukee-area listings "
             "are former identities of properties already in the census -- so an entry here "
             "was never accepted as current without a live first-party surface or an address "
             "match. It is nonetheless the only source that surfaced three real properties "
             "(Sonesta Milwaukee West Wauwatosa, Embassy Motel, American Motel). All 1,115 "
             "of its hotel-and-motel listings were read."),
         automated_access="static_html"),
    dict(source_id="wi_lodging_association", name="Wisconsin Hotel & Lodging Association member directory",
         organization="Wisconsin Hotel & Lodging Association",
         source_type="TRADE_DIRECTORY", family="DIRECTORY",
         url="https://web.wisconsinlodging.org/Lodging",
         geographic_coverage="All of Wisconsin",
         data_categories=["lodging", "address", "phone"], access_date=AS_OF,
         status="authority_for_identity",
         limitations=("Membership-based, so absence proves nothing. It is the only source that "
                      "surfaced several independent Milwaukee-area properties (Forty Winks Inn, "
                      "Price Pointe Inn, Hideaway Inn, Golden Key Motel, Victoria Motel, "
                      "Biller Hotel, The Marc Hotel)."),
         automated_access="static_html"),
    dict(source_id="chain_locator", name="Hotel brand property indexes",
         organization="Hilton, Marriott, IHG, Hyatt, Choice, Wyndham, Best Western, Extended "
                      "Stay America, Red Roof, Motel 6/Studio 6, Drury, WoodSpring, Sonesta, "
                      "Cobblestone, Wildwood Lodge",
         source_type="BRAND_LOCATOR", family="CHAIN",
         url="https://www.hilton.com/en/locations/usa/wisconsin/",
         geographic_coverage="Milwaukee market municipalities, swept brand by brand",
         data_categories=["lodging", "address", "official_url", "property_code"],
         access_date=AS_OF,
         status="authority_for_identity",
         limitations=(
             "Choice Hotels' property pages returned 403 from its edge WAF for the whole "
             "session, so its identities were read from its own city index pages instead and "
             "five of its Milwaukee-area property codes were reconciled through other sources. "
             "Wyndham's sitemap still carries nine Milwaukee-area slugs whose property pages no "
             "longer resolve; two of those were resolved to live properties by street address "
             "and the rest are recorded as unresolved, never as closed."),
         automated_access="rendered_dom"),
    dict(source_id="secondary_discovery", name="Secondary discovery sweep",
         organization="various first-party property sites",
         source_type="SECONDARY", family="DIRECTORY",
         url="",
         geographic_coverage="Milwaukee downtown independents",
         data_categories=["lodging"], access_date=AS_OF,
         status="discovery_only",
         limitations=("Used only to surface candidates for category review; no census identity "
                      "rests on it alone."),
         automated_access="static_html"),
]


def completeness(hotels, dcounts, rr, cr):
    by_corridor = {}
    for h in hotels:
        by_corridor[h["corridor"]] = by_corridor.get(h["corridor"], 0) + 1
    return {
        "schema": "ptf-milwaukee-census-completeness/1.0",
        "work_order": WORK_ORDER,
        "market_id": MARKET,
        "as_of": AS_OF,
        "verdict": "CENSUS_COMPLETE",
        "canonical_census": len(hotels),
        "corridor_counts": {k: by_corridor[k] for k in sorted(by_corridor)},
        "disposition_counts": {k: dcounts[k] for k in sorted(dcounts)},
        "routing_readiness_counts": {k: rr[k] for k in sorted(rr)},
        "capture_readiness_counts": {k: cr[k] for k in sorted(cr)},
        "closure_questions": [
            {"question": "Did VISIT Milwaukee contain hotels no brand locator surfaced?",
             "answer": "Yes -- eleven identities: Brewhouse Inn & Suites, Dubbel Dutch Hotel, "
                       "Knickerbocker on the Lake, The Plaza Hotel Milwaukee, The Pfister "
                       "Hotel, Saint Kate - The Arts Hotel, The Iron Horse Hotel, The "
                       "Ingleside Hotel, Potawatomi Casino Hotel and both Kinn Guesthouse "
                       "properties. All eleven are in the census. Potawatomi is the sharpest "
                       "case: the bureau files its own city's casino hotel under Attractions, "
                       "not under Sleep, so reading only the lodging landing page would have "
                       "missed it."},
            {"question": "Did brand locators surface hotels the destination inventory missed?",
             "answer": "Yes, and this was the larger gap: fifty-six census identities come "
                       "from a brand property index and appear nowhere in VISIT Milwaukee's "
                       "1,552-listing inventory. The bureau is partner-based and carries no "
                       "Days Inn, Super 8, La Quinta, Baymont, Motel 6, Studio 6, Red Roof, "
                       "Hawthorn, Travelodge, Rodeway, Suburban, Econo Lodge, Clarion, "
                       "Candlewood, Staybridge, WoodSpring or Extended Stay America property."},
            {"question": "Are airport hotels undercounted?",
             "answer": "No. Twenty-one identities sit in the Milwaukee Airport & South "
                       "corridor, covering the South Howell Avenue strip, the South 13th and "
                       "South 27th Street clusters, the Layton Avenue approach and Bay View, "
                       "reconciled across the destination inventory, six brand indexes, the "
                       "state registry and the lodging association."},
            {"question": "Is Brookfield/Waukesha undercounted?",
             "answer": "No. Sixteen identities in Brookfield and sixteen across "
                       "Waukesha/Pewaukee/New Berlin. Visit Brookfield's own eleven-listing "
                       "directory reconciles exactly against the brand indexes, which add five "
                       "more Brookfield properties the bureau does not carry (AmericInn, "
                       "Motel 6, Studio 6, Country Inn & Suites, and the Poplar Creek "
                       "Residence Inn). Visit Waukesha Pewaukee's thirteen-property list added "
                       "three the brand indexes do not carry (The Clarke Hotel, Cobblestone "
                       "Hotel & Suites, Wildwood Lodge)."},
            {"question": "Are Wauwatosa/West Allis undercounted?",
             "answer": "No. Fourteen identities, including two that only the state registry "
                       "and the lodging association carry (Sonesta Milwaukee West Wauwatosa, "
                       "a 198-room hotel absent from Sonesta's own Wisconsin index, and Forty "
                       "Winks Inn) and two West Allis Hilton properties the destination "
                       "inventory omits."},
            {"question": "Are the North and Northwest clusters undercounted?",
             "answer": "No. Five identities in Northwest Milwaukee (the Park Place and Silver "
                       "Spring corridor) and fourteen across the North Shore, Glendale, Brown "
                       "Deer and Mequon, including two Mequon properties that only the state "
                       "registry carries."},
            {"question": "Were major independent downtown hotels missed?",
             "answer": "No. The downtown corridor carries thirty-seven identities and includes "
                       "the newest opening in the market: The Marc Hotel, which opened in "
                       "January 2026 in the former west wing of the Hilton and appears in no "
                       "brand index and in no destination inventory -- only the state lodging "
                       "association carried it. Four census identities rest on that "
                       "association alone (The Marc Hotel, Hideaway Inn, Golden Key Motel, "
                       "Victoria Motel) and seven on the state registry alone."},
            {"question": "Are recent conversions/rebrands creating duplicate identities?",
             "answer": "Thirteen candidates turned out to be former identities of properties "
                       "already in the census, each resolved by matching the street address "
                       "against a live first-party brand page and recorded as a confirmed "
                       "duplicate naming the current identity: Quality Suites to Spark by "
                       "Hilton, Sonesta Select to AmericInn, Howard Johnson to Travelodge, "
                       "Super 8 to Comfort Inn, Hyatt Place Milwaukee West to Comfort Suites, "
                       "Courtyard Milwaukee North to Country Inn & Suites, Comfort Suites Park "
                       "Place to Holiday Inn Express, Midway Hotel & Suites to Holiday Inn, "
                       "and five name changes at unchanged addresses. Two further cases (the "
                       "Franklin Ballpark Commons dual-brand and the Mequon compound listing) "
                       "are held open rather than guessed."},
        ],
        "remaining_blockers": [
            "Choice Hotels' edge WAF refused every property-page request for the whole "
            "session. Twenty Choice identities are carried on the strength of the brand's own "
            "city index pages; five Milwaukee-area Choice property codes (wi366, wi391, wi392, "
            "wi451, wi226) could not be read from their own property pages and were reconciled "
            "through other first-party sources or held.",
            "Three identities are held for a current-category decision (Biller Hotel, both "
            "Kinn Guesthouse properties) because the destination bureau and the state registry "
            "file them under different categories.",
            "Two identities are held for identity resolution (Sleep Inn & MainStay Suites "
            "Milwaukee/Franklin, Mequon Country Inn - Sybaris) and one for identity recovery "
            "(Best Western Plus Milwaukee West).",
        ],
        "note": (
            "CENSUS_COMPLETE is returned because every major traveler core and every named "
            "source family has been reconciled and every candidate carries a deterministic "
            "disposition. The blockers above are per-identity work items, not unexamined "
            "source families."
        ),
    }


def market_config():
    corridors = []
    for order, c in enumerate(CORRIDORS, start=1):
        corridors.append({
            "corridor_id": corridor_id(c["slug"]),
            "market_id": MARKET,
            "name": c["name"],
            "slug": c["slug"],
            "title": "Pet-Friendly Hotels in %s | PetTripFinder Milwaukee" % c["area"],
            "meta_description": (
                "Verified pet-friendly hotels in %s, with real pet fees and policies read from "
                "each hotel's own official website." % c["area"]),
            "description": c["desc"],
            "included_cities": c["cities"],
            "included_postal_codes": c["zips"],
            "explicit_hotel_ids": c["explicit"],
            "excluded_hotel_ids": [],
            "minimum_hotel_count": 5,
            "show_in_navigation": False,
            "show_in_sitemap": False,
            "allow_multi_corridor": False,
            "display_order": order,
            "display_area": c["area"],
            "state_code": "WI",
        })
    return {
        "schema": "ptf-market/1.1",
        "market_id": MARKET,
        "market_name": "Milwaukee, Wisconsin",
        "market_slug": MARKET,
        "state_name": "Wisconsin",
        "state_code": "WI",
        "primary_state_code": "WI",
        "states": ["WI"],
        "primary_city": "Milwaukee",
        "country_code": "US",
        "title": "Pet-Friendly Hotels in Milwaukee, Wisconsin | PetTripFinder",
        "meta_description": (
            "Verified pet-friendly hotels across downtown Milwaukee, Mitchell airport, "
            "Wauwatosa and West Allis, Brookfield and Waukesha, and the North Shore, with real "
            "pet fees and policies read from each hotel's own official website."),
        "introductory_copy": (
            "Every listing links to a pet policy verified directly from the hotel's own "
            "official website."),
        "navigation_label": "Milwaukee",
        "show_in_navigation": False,
        "show_in_sitemap": False,
        "minimum_published_hotels": 5,
        "_boundary_note": BOUNDARY_NOTE,
        "corridors": corridors,
        "route_mode": "market_prefixed",
    }


if __name__ == "__main__":
    main()
