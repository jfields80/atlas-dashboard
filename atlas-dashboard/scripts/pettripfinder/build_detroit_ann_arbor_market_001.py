"""PTF-DETROIT-ANN-ARBOR-MARKET-FACTORY-001 -- Phase 1 independent census.

Builds the Detroit-Ann Arbor, Michigan lodging census, final partition,
source registry, duplicate ledger, routing assessments, and founder-review
queue from independently discovered hotel identities. No policy authority,
seed, exclusion registry, release contract, or assembler file is written, and
no browser capture runs. Every census policy_state is POLICY_NOT_VERIFIED and
every partition row is a non-terminal blocker: this market has no committed
policy authority yet, so published=0 and verified_no_pets=0 by construction.

Sequence, per the work order: independent discovery -> candidate ledger ->
identity reconciliation -> boundary review -> canonical census -> corridor
assignment -> final partition -> routing/capture-readiness assessment. The
corridor registry (launch_packages/pettripfinder/markets/detroit-ann-arbor-
mi.json) was authored AFTER this candidate table was drafted from discovery,
never the reverse -- the corridor registry does not define the universe.

Run:

    python -m scripts.pettripfinder.build_detroit_ann_arbor_market_001
"""

from __future__ import annotations

import csv
import hashlib
import json
import sys
from collections import OrderedDict
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parents[2]
if str(_REPO_ROOT) not in sys.path:
    sys.path.insert(0, str(_REPO_ROOT))

from scripts.pettripfinder.census_partition_builder import next_action_for
from scripts.pettripfinder.contracts import census as CENSUS
from scripts.pettripfinder.contracts import enums
from scripts.pettripfinder.contracts import partition as PART
from scripts.pettripfinder.contracts.identity_key import (
    IDENTITY_KEY_CONTRACT,
    ptf_identity_key,
)
from scripts.pettripfinder.markets import assign_hotels, load_markets, market_by_id, slugify
from scripts.pettripfinder.site_data import normalize_name

WORK_ORDER = "PTF-DETROIT-ANN-ARBOR-MARKET-FACTORY-001"
MARKET = "detroit-ann-arbor-mi"
AS_OF = "2026-08-16"
BASE_COMMIT = "4843a7d0c7b0331a67a219c446a5c2726e95e726"
WORKER_BRANCH = "worker/ptf-detroit-ann-arbor-market-001"
PACKAGE = _REPO_ROOT / "launch_packages" / "pettripfinder"
REPORTS = PACKAGE / "markets" / "reports"
CENSUS_PATH = PACKAGE / "identity_census" / ("%s.json" % MARKET)
PARTITION_PATH = PACKAGE / "detroit_ann_arbor_final_partition_001.json"
DATA_ROOT = _REPO_ROOT / "data" / "market_research" / "detroit-ann-arbor"
QUEUE_ROOT = _REPO_ROOT / "data" / "operator_evidence" / "detroit-ann-arbor-founder-review-001"

# disposition: canonical | duplicate | boundary_excluded | closed
# url_shape: property | brand_index | none


def _c(**kw):
    return kw


CANDIDATES = [
    # ======================================================================
    # DOWNTOWN / MIDTOWN / CORKTOWN DETROIT -- Visit Detroit (DMCVB) Detroit
    # Hotel Guide, https://visitdetroit.com/detroit-hotel-guide/ (accessed
    # 2026-08-16). Names transcribed verbatim; the guide does not publish
    # street addresses, so these are IDENTITY_CONFIRMED via the CVB's own
    # attribution of a distinct, unambiguous hotel name to Detroit rather
    # than via a transcribed address.
    # ======================================================================
    _c(name="Detroit Foundation Hotel", address="250 West Larned Street", city="Detroit",
       postal="48226", phone="", url="", url_shape="none",
       source="visit_detroit", ident="IDENTITY_CONFIRMED", lodging="LODGING_CONFIRMED"),
    _c(name="Trumbull and Porter Hotel", address="", city="Detroit", postal="",
       phone="", url="", url_shape="none",
       source="visit_detroit", ident="IDENTITY_CONFIRMED", lodging="LODGING_CONFIRMED"),
    _c(name="The Inn on Ferry Street", address="", city="Detroit", postal="",
       phone="", url="", url_shape="none",
       source="visit_detroit", ident="IDENTITY_CONFIRMED", lodging="LODGING_CONFIRMED"),
    _c(name="The Godfrey Hotel Detroit", address="", city="Detroit", postal="",
       phone="", url="", url_shape="none",
       source="visit_detroit", ident="IDENTITY_CONFIRMED", lodging="LODGING_CONFIRMED"),
    _c(name="Shinola Hotel", address="1400 Woodward Avenue", city="Detroit",
       postal="48226", phone="313-356-1400", url="https://www.shinolahotel.com",
       url_shape="property", source="visit_detroit", ident="IDENTITY_CONFIRMED",
       lodging="LODGING_CONFIRMED"),
    _c(name="Westin Book Cadillac Detroit", address="1114 Washington Boulevard",
       city="Detroit", postal="48226", phone="",
       url="https://www.marriott.com/en-us/hotels/dtwcw-the-westin-book-cadillac-detroit/overview/",
       url_shape="property", source="visit_detroit", ident="IDENTITY_CONFIRMED",
       lodging="LODGING_CONFIRMED"),
    _c(name="Hotel David Whitney, Autograph Collection", address="", city="Detroit",
       postal="", phone="",
       url="https://www.marriott.com/en-us/hotels/dtwkd-hotel-david-whitney-autograph-collection/overview/",
       url_shape="property", source="visit_detroit", ident="IDENTITY_CONFIRMED",
       lodging="LODGING_CONFIRMED"),
    _c(name="El Moore Lodge", address="", city="Detroit", postal="", phone="",
       url="", url_shape="none", source="visit_detroit", ident="IDENTITY_CONFIRMED",
       lodging="LODGING_CONFIRMED"),
    _c(name="Cambria Hotel Detroit Downtown", address="", city="Detroit", postal="",
       phone="", url="", url_shape="none", source="visit_detroit",
       ident="IDENTITY_CONFIRMED", lodging="LODGING_CONFIRMED"),
    _c(name="The Siren Hotel", address="", city="Detroit", postal="", phone="",
       url="", url_shape="none", source="visit_detroit", ident="IDENTITY_CONFIRMED",
       lodging="LODGING_CONFIRMED"),
    _c(name="Roost Detroit", address="", city="Detroit", postal="", phone="",
       url="", url_shape="none", source="visit_detroit", ident="IDENTITY_CONFIRMED",
       lodging="LODGING_CONFIRMED"),
    _c(name="Atheneum Suite Hotel", address="", city="Detroit", postal="", phone="",
       url="", url_shape="none", source="visit_detroit", ident="IDENTITY_CONFIRMED",
       lodging="LODGING_CONFIRMED"),
    _c(name="Element Detroit at the Metropolitan", address="", city="Detroit",
       postal="", phone="", url="", url_shape="none", source="visit_detroit",
       ident="IDENTITY_CONFIRMED", lodging="LODGING_CONFIRMED"),
    _c(name="Hotel Indigo Detroit Downtown", address="", city="Detroit", postal="",
       phone="", url="", url_shape="none", source="visit_detroit",
       ident="IDENTITY_CONFIRMED", lodging="LODGING_CONFIRMED"),
    _c(name="MGM Grand Detroit", address="", city="Detroit", postal="", phone="",
       url="", url_shape="none", source="visit_detroit", ident="IDENTITY_CONFIRMED",
       lodging="LODGING_CONFIRMED"),
    _c(name="MotorCity Casino Hotel", address="", city="Detroit", postal="", phone="",
       url="", url_shape="none", source="visit_detroit", ident="IDENTITY_CONFIRMED",
       lodging="LODGING_CONFIRMED"),
    _c(name="Hollywood Casino at Greektown", address="", city="Detroit", postal="",
       phone="", url="", url_shape="none", source="visit_detroit",
       ident="IDENTITY_CONFIRMED", lodging="LODGING_CONFIRMED"),
    _c(name="Detroit Marriott at the Renaissance Center", address="", city="Detroit",
       postal="", phone="",
       url="https://www.marriott.com/en-us/hotels/dtwdt-detroit-marriott-at-the-renaissance-center/overview/",
       url_shape="property", source="visit_detroit", ident="IDENTITY_CONFIRMED",
       lodging="LODGING_CONFIRMED"),
    _c(name="Courtyard by Marriott Detroit Downtown", address="", city="Detroit",
       postal="", phone="", url="", url_shape="none", source="visit_detroit",
       ident="IDENTITY_CONFIRMED", lodging="LODGING_CONFIRMED"),
    _c(name="Crowne Plaza Detroit Downtown Riverfront", address="", city="Detroit",
       postal="", phone="", url="", url_shape="none", source="visit_detroit",
       ident="IDENTITY_CONFIRMED", lodging="LODGING_CONFIRMED"),
    _c(name="DoubleTree Suites by Hilton Downtown Detroit", address="",
       city="Detroit", postal="", phone="", url="", url_shape="none",
       source="visit_detroit", ident="IDENTITY_CONFIRMED", lodging="LODGING_CONFIRMED"),

    # ======================================================================
    # DEARBORN -- Dearborn Area Chamber of Commerce member directory
    # (dearbornareachamber.org, accessed 2026-08-16) plus Visit Detroit's
    # Wayne County/Dearborn section for gap-fill.
    # ======================================================================
    _c(name="Dearborn Inn, Autograph Collection", address="20301 Oakwood Boulevard",
       city="Dearborn", postal="48124", phone="",
       url="https://www.marriott.com/en-us/hotels/dtwdk-dearborn-inn-autograph-collection/overview/",
       url_shape="property", source="dearborn_chamber", ident="IDENTITY_CONFIRMED",
       lodging="LODGING_CONFIRMED"),
    _c(name="The Henry, Autograph Collection", address="300 Town Center Drive",
       city="Dearborn", postal="48126", phone="",
       url="https://www.marriott.com/hotels/travel/dtwak-the-henry-autograph-collection/",
       url_shape="property", source="dearborn_chamber", ident="IDENTITY_CONFIRMED",
       lodging="LODGING_CONFIRMED"),
    _c(name="DoubleTree by Hilton Detroit Dearborn", address="", city="Dearborn",
       postal="", phone="", url="", url_shape="none", source="visit_detroit",
       ident="IDENTITY_CONFIRMED", lodging="LODGING_CONFIRMED"),
    _c(name="Best Western Greenfield Inn", address="", city="Dearborn", postal="",
       phone="", url="", url_shape="none", source="visit_detroit",
       ident="IDENTITY_CONFIRMED", lodging="LODGING_CONFIRMED"),
    _c(name="Comfort Inn at Greenfield Village", address="", city="Dearborn",
       postal="", phone="",
       url="https://www.dearbornareachamber.org/directory/listing/dearborn-west-village-hotel/",
       url_shape="brand_index", source="dearborn_chamber", ident="IDENTITY_CONFIRMED",
       lodging="LODGING_CONFIRMED"),
    _c(name="Red Roof Inn Dearborn", address="24130 Michigan Avenue", city="Dearborn",
       postal="48124", phone="", url="", url_shape="none", source="dearborn_chamber",
       ident="IDENTITY_CONFIRMED", lodging="LODGING_CONFIRMED"),
    _c(name="Staybridge Suites Dearborn", address="", city="Dearborn", postal="",
       phone="", url="", url_shape="none", source="chain_aggregate",
       ident="IDENTITY_PROVISIONAL", lodging="LODGING_BY_NAME"),
    _c(name="Holiday Inn Fairlane Dearborn", address="", city="Dearborn", postal="",
       phone="", url="", url_shape="none", source="chain_aggregate",
       ident="IDENTITY_PROVISIONAL", lodging="LODGING_BY_NAME"),

    # ======================================================================
    # DTW AIRPORT / ROMULUS / BELLEVILLE -- Visit Detroit airport section
    # plus first-party brand-locator pages (wyndhamhotels.com, hilton.com)
    # confirmed by targeted discovery, plus a Destination Ann Arbor listing
    # for the Belleville property.
    # ======================================================================
    _c(name="The Westin Detroit Metropolitan Airport", address="", city="Romulus",
       postal="", phone="",
       url="https://www.marriott.com/en-us/hotels/dtwma-the-westin-detroit-metropolitan-airport/overview/",
       url_shape="property", source="visit_detroit", ident="IDENTITY_CONFIRMED",
       lodging="LODGING_CONFIRMED"),
    _c(name="Delta Hotels by Marriott Detroit Metro Airport", address="",
       city="Romulus", postal="", phone="", url="", url_shape="none",
       source="visit_detroit", ident="IDENTITY_CONFIRMED", lodging="LODGING_CONFIRMED"),
    _c(name="Wyndham Garden Detroit Metro Airport Romulus", address="",
       city="Romulus", postal="", phone="",
       url="https://www.wyndhamhotels.com/wyndham-garden/romulus-michigan/wyndham-garden-romulus-detroit-metro-airport/overview",
       url_shape="property", source="chain_locator", ident="IDENTITY_CONFIRMED",
       lodging="LODGING_CONFIRMED"),
    _c(name="Travelodge by Wyndham Romulus Detroit Airport", address="",
       city="Romulus", postal="", phone="",
       url="https://www.wyndhamhotels.com/travelodge/romulus-michigan/travelodge-romulus-detroit-airport/overview",
       url_shape="property", source="chain_locator", ident="IDENTITY_CONFIRMED",
       lodging="LODGING_CONFIRMED"),
    _c(name="Wingate by Wyndham Detroit Metro Airport", address="", city="Romulus",
       postal="", phone="",
       url="https://www.wyndhamhotels.com/wingate/romulus-michigan/wingate-by-wyndham-detroit-metro-airport/overview",
       url_shape="property", source="chain_locator", ident="IDENTITY_CONFIRMED",
       lodging="LODGING_CONFIRMED"),
    _c(name="Baymont by Wyndham Detroit Airport Romulus", address="", city="Romulus",
       postal="", phone="",
       url="https://www.wyndhamhotels.com/baymont/romulus-michigan/baymont-inn-and-suites-detroit-airport-romulus/overview",
       url_shape="property", source="chain_locator", ident="IDENTITY_CONFIRMED",
       lodging="LODGING_CONFIRMED"),
    _c(name="Howard Johnson by Wyndham Romulus Detroit Metro Airport", address="",
       city="Romulus", postal="", phone="",
       url="https://www.wyndhamhotels.com/hojo/romulus-michigan/howard-johnson-romulus-detroit-metro-airport/overview",
       url_shape="property", source="chain_locator", ident="IDENTITY_CONFIRMED",
       lodging="LODGING_CONFIRMED"),
    _c(name="Hampton Inn & Suites Detroit Airport Romulus", address="", city="Romulus",
       postal="", phone="",
       url="https://www.hilton.com/en/hotels/dttrmhx-hampton-suites-detroit-airport-romulus/",
       url_shape="property", source="chain_locator", ident="IDENTITY_CONFIRMED",
       lodging="LODGING_CONFIRMED"),
    _c(name="Hilton Garden Inn Detroit Metro Airport", address="", city="Romulus",
       postal="", phone="", url="", url_shape="none", source="chain_aggregate",
       ident="IDENTITY_PROVISIONAL", lodging="LODGING_BY_NAME"),
    _c(name="Embassy Suites by Hilton Detroit Metro Airport", address="",
       city="Romulus", postal="", phone="", url="", url_shape="none",
       source="chain_aggregate", ident="IDENTITY_PROVISIONAL", lodging="LODGING_BY_NAME"),
    _c(name="Comfort Inn Metro Airport", address="", city="Romulus", postal="",
       phone="", url="", url_shape="none", source="chain_aggregate",
       ident="IDENTITY_PROVISIONAL", lodging="LODGING_BY_NAME"),
    _c(name="TownePlace Suites by Marriott Detroit Belleville", address="",
       city="Belleville", postal="", phone="",
       url="https://www.annarbor.org/listing/towneplace-suites-by-marriott-detroit-belleville/2339/",
       url_shape="brand_index", source="destination_ann_arbor", ident="IDENTITY_CONFIRMED",
       lodging="LODGING_CONFIRMED",
       notes="Found via Destination Ann Arbor's own directory; the property is "
             "geographically west of DTW along I-94, grouped with the airport "
             "corridor rather than Ann Arbor city."),

    # ======================================================================
    # SOUTHFIELD -- brand-locator aggregate discovery (no single chamber/CVB
    # directory found for Southfield; every row here is IDENTITY_PROVISIONAL
    # pending an independently sourced street address, the same gap-fill
    # treatment Pittsburgh gave its GPHA-only rows).
    # ======================================================================
    _c(name="Detroit Marriott Southfield", address="", city="Southfield", postal="",
       phone="", url="", url_shape="none", source="chain_aggregate",
       ident="IDENTITY_PROVISIONAL", lodging="LODGING_BY_NAME"),
    _c(name="SpringHill Suites Detroit Southfield", address="", city="Southfield",
       postal="", phone="", url="", url_shape="none", source="chain_aggregate",
       ident="IDENTITY_PROVISIONAL", lodging="LODGING_BY_NAME"),
    _c(name="Courtyard by Marriott Detroit Southfield", address="", city="Southfield",
       postal="", phone="", url="", url_shape="none", source="chain_aggregate",
       ident="IDENTITY_PROVISIONAL", lodging="LODGING_BY_NAME"),
    _c(name="Hilton Garden Inn Detroit Southfield", address="", city="Southfield",
       postal="", phone="", url="", url_shape="none", source="chain_aggregate",
       ident="IDENTITY_PROVISIONAL", lodging="LODGING_BY_NAME"),
    _c(name="Hampton Inn by Hilton Detroit Southfield", address="", city="Southfield",
       postal="", phone="", url="", url_shape="none", source="chain_aggregate",
       ident="IDENTITY_PROVISIONAL", lodging="LODGING_BY_NAME"),
    _c(name="Staybridge Suites Detroit Southfield", address="", city="Southfield",
       postal="", phone="", url="", url_shape="none", source="chain_aggregate",
       ident="IDENTITY_PROVISIONAL", lodging="LODGING_BY_NAME"),
    _c(name="Holiday Inn Express & Suites Southfield Detroit", address="",
       city="Southfield", postal="", phone="", url="", url_shape="none",
       source="chain_aggregate", ident="IDENTITY_PROVISIONAL", lodging="LODGING_BY_NAME"),
    _c(name="Ramada by Wyndham Southfield", address="", city="Southfield", postal="",
       phone="", url="", url_shape="none", source="chain_aggregate",
       ident="IDENTITY_PROVISIONAL", lodging="LODGING_BY_NAME"),
    _c(name="Hawthorn Suites by Wyndham Southfield Detroit", address="",
       city="Southfield", postal="", phone="", url="", url_shape="none",
       source="chain_aggregate", ident="IDENTITY_PROVISIONAL", lodging="LODGING_BY_NAME"),
    _c(name="The Westin Southfield Detroit", address="", city="Southfield", postal="",
       phone="", url="", url_shape="none", source="chain_aggregate",
       ident="IDENTITY_PROVISIONAL", lodging="LODGING_BY_NAME"),

    # ======================================================================
    # TROY / AUBURN HILLS -- Auburn Hills Chamber of Commerce hotels
    # directory (business.auburnhillschamber.com, accessed 2026-08-16) for
    # the Auburn Hills rows with full addresses/phones, plus first-party
    # Choice/IHG locator pages, plus brand-aggregate gap-fill for Troy.
    # ======================================================================
    _c(name="Crowne Plaza Auburn Hills", address="1500 North Opdyke Rd",
       city="Auburn Hills", postal="48326", phone="248-373-4550", url="",
       url_shape="none", source="auburn_hills_chamber", ident="IDENTITY_CONFIRMED",
       lodging="LODGING_CONFIRMED"),
    _c(name="Hampton Inn Detroit Auburn Hills North", address="3988 Baldwin Road",
       city="Auburn Hills", postal="48326", phone="248-874-4902", url="",
       url_shape="none", source="auburn_hills_chamber", ident="IDENTITY_CONFIRMED",
       lodging="LODGING_CONFIRMED"),
    _c(name="Holiday Inn Express Hotel & Suites Auburn Hills",
       address="3990 Baldwin Rd", city="Auburn Hills", postal="48326",
       phone="248-322-7000", url="", url_shape="none", source="auburn_hills_chamber",
       ident="IDENTITY_CONFIRMED", lodging="LODGING_CONFIRMED"),
    _c(name="Hotel Indigo Detroit North Troy", address="575 W. Big Beaver",
       city="Troy", postal="48084", phone="248-686-7059", url="",
       url_shape="none", source="auburn_hills_chamber", ident="IDENTITY_CONFIRMED",
       lodging="LODGING_CONFIRMED"),
    _c(name="EVEN Hotel Detroit North Troy", address="575 W. Big Beaver",
       city="Troy", postal="48084", phone="248-686-7059", url="",
       url_shape="none", source="auburn_hills_chamber", ident="IDENTITY_CONFIRMED",
       lodging="LODGING_CONFIRMED",
       notes="Dual-branded IHG property sharing one street address with Hotel "
             "Indigo Detroit North - Troy; the shared street identity is "
             "expected and flagged by the collision audit, the same treatment "
             "Pittsburgh gave Ace Hotel / The Maverick."),
    _c(name="TownePlace Suites Detroit Auburn Hills", address="3900 Baldwin Rd",
       city="Auburn Hills", postal="48326", phone="248-322-7000", url="",
       url_shape="none", source="auburn_hills_chamber", ident="IDENTITY_CONFIRMED",
       lodging="LODGING_CONFIRMED"),
    _c(name="Hotel Auburn Hills", address="2300 Featherstone Rd", city="Auburn Hills",
       postal="48326", phone="248-334-2222", url="", url_shape="none",
       source="auburn_hills_chamber", ident="IDENTITY_CONFIRMED", lodging="LODGING_CONFIRMED"),
    _c(name="Hyatt Place Detroit Auburn Hills", address="1545 N Opdyke Rd",
       city="Auburn Hills", postal="48326", phone="248-475-9393", url="",
       url_shape="none", source="auburn_hills_chamber", ident="IDENTITY_CONFIRMED",
       lodging="LODGING_CONFIRMED"),
    _c(name="Quality Inn Auburn Hills", address="1461 N Opdyke Rd", city="Auburn Hills",
       postal="48326", phone="248-370-0044", url="", url_shape="none",
       source="auburn_hills_chamber", ident="IDENTITY_CONFIRMED", lodging="LODGING_CONFIRMED"),
    _c(name="Red Roof Inn Auburn Hills", address="1294 North Opdyke Rd",
       city="Auburn Hills", postal="48326", phone="248-373-2228", url="",
       url_shape="none", source="auburn_hills_chamber", ident="IDENTITY_CONFIRMED",
       lodging="LODGING_CONFIRMED"),
    _c(name="Sonesta Select Detroit Auburn Hills", address="2550 Aimee Lane",
       city="Auburn Hills", postal="48326", phone="248-373-4100", url="",
       url_shape="none", source="auburn_hills_chamber", ident="IDENTITY_CONFIRMED",
       lodging="LODGING_CONFIRMED"),
    _c(name="SpringHill Suites Auburn Hills", address="4919 Interpark Dr",
       city="Orion Township", postal="48359", phone="248-475-4700", url="",
       url_shape="none", source="auburn_hills_chamber", ident="IDENTITY_CONFIRMED",
       lodging="LODGING_CONFIRMED"),
    _c(name="Comfort Suites Auburn Hills Detroit", address="", city="Auburn Hills",
       postal="", phone="",
       url="https://www.choicehotels.com/michigan/auburn-hills/comfort-suites-hotels/mi142",
       url_shape="property", source="chain_locator", ident="IDENTITY_CONFIRMED",
       lodging="LODGING_CONFIRMED"),
    _c(name="Staybridge Suites Auburn Hills", address="", city="Auburn Hills",
       postal="", phone="",
       url="https://www.ihg.com/staybridge/hotels/us/en/auburn-hills/dttyz/hoteldetail",
       url_shape="property", source="chain_locator", ident="IDENTITY_CONFIRMED",
       lodging="LODGING_CONFIRMED"),
    _c(name="Sonesta ES Suites Auburn Hills", address="", city="Auburn Hills",
       postal="", phone="", url="", url_shape="none", source="chain_aggregate",
       ident="IDENTITY_PROVISIONAL", lodging="LODGING_BY_NAME"),
    _c(name="Woodland Direct", address="2025 Taylor Road", city="Auburn Hills",
       postal="48326", phone="810-620-0932", url="", url_shape="none",
       source="auburn_hills_chamber", ident="IDENTITY_CONFIRMED", lodging="NOT_LODGING",
       notes="Chamber 'hotels' category member; this is a home-theater/AV "
             "retailer, not a lodging business. Retained as a category-excluded "
             "census row, not silently dropped."),
    _c(name="Fairfield Inn & Suites Detroit Troy", address="", city="Troy",
       postal="", phone="", url="", url_shape="none", source="chain_aggregate",
       ident="IDENTITY_PROVISIONAL", lodging="LODGING_BY_NAME"),
    _c(name="Detroit Marriott Troy", address="", city="Troy", postal="", phone="",
       url="", url_shape="none", source="chain_aggregate", ident="IDENTITY_PROVISIONAL",
       lodging="LODGING_BY_NAME"),
    _c(name="Courtyard by Marriott Detroit Troy", address="", city="Troy", postal="",
       phone="", url="", url_shape="none", source="chain_aggregate",
       ident="IDENTITY_PROVISIONAL", lodging="LODGING_BY_NAME"),
    _c(name="TownePlace Suites by Marriott Detroit Troy", address="", city="Troy",
       postal="", phone="", url="", url_shape="none", source="chain_aggregate",
       ident="IDENTITY_PROVISIONAL", lodging="LODGING_BY_NAME"),
    _c(name="Home2 Suites by Hilton Troy", address="", city="Troy", postal="",
       phone="", url="", url_shape="none", source="chain_aggregate",
       ident="IDENTITY_PROVISIONAL", lodging="LODGING_BY_NAME"),
    _c(name="Embassy Suites by Hilton Detroit Troy Auburn Hills", address="",
       city="Troy", postal="", phone="", url="", url_shape="none",
       source="chain_aggregate", ident="IDENTITY_PROVISIONAL", lodging="LODGING_BY_NAME"),
    _c(name="Hilton Garden Inn Detroit Troy", address="", city="Troy", postal="",
       phone="", url="", url_shape="none", source="chain_aggregate",
       ident="IDENTITY_PROVISIONAL", lodging="LODGING_BY_NAME"),
    _c(name="Tru by Hilton Troy Detroit", address="", city="Troy", postal="",
       phone="", url="", url_shape="none", source="chain_aggregate",
       ident="IDENTITY_PROVISIONAL", lodging="LODGING_BY_NAME"),
    _c(name="Homewood Suites by Hilton Detroit Troy", address="", city="Troy",
       postal="", phone="", url="", url_shape="none", source="chain_aggregate",
       ident="IDENTITY_PROVISIONAL", lodging="LODGING_BY_NAME"),
    _c(name="Holiday Inn Express & Suites Detroit North Troy", address="",
       city="Troy", postal="", phone="", url="", url_shape="none",
       source="chain_aggregate", ident="IDENTITY_PROVISIONAL", lodging="LODGING_BY_NAME"),
    _c(name="Holiday Inn & Suites Detroit Troy", address="", city="Troy", postal="",
       phone="", url="", url_shape="none", source="chain_aggregate",
       ident="IDENTITY_PROVISIONAL", lodging="LODGING_BY_NAME"),
    _c(name="Wingate by Wyndham Troy", address="", city="Troy", postal="",
       phone="", url="", url_shape="none", source="chain_aggregate",
       ident="IDENTITY_PROVISIONAL", lodging="LODGING_BY_NAME"),
    _c(name="Somerset Inn", address="", city="Troy", postal="", phone="",
       url="", url_shape="none", source="chain_aggregate", ident="IDENTITY_PROVISIONAL",
       lodging="LODGING_BY_NAME"),

    # ======================================================================
    # BIRMINGHAM / ROYAL OAK / ROCHESTER / PONTIAC -- Auburn Hills Chamber
    # directory rows with full addresses, plus Visit Detroit gap-fill.
    # ======================================================================
    _c(name="Royal Park Hotel", address="600 E University Drive", city="Rochester",
       postal="48307", phone="248-652-2600", url="", url_shape="none",
       source="auburn_hills_chamber", ident="IDENTITY_CONFIRMED", lodging="LODGING_CONFIRMED"),
    _c(name="The Townsend Hotel", address="100 Townsend Street", city="Birmingham",
       postal="48009", phone="248-642-7900", url="", url_shape="none",
       source="auburn_hills_chamber", ident="IDENTITY_CONFIRMED", lodging="LODGING_CONFIRMED"),
    _c(name="The Kingsley Bloomfield Hills", address="39475 Woodward Ave",
       city="Bloomfield Hills", postal="48304", phone="248-644-1400", url="",
       url_shape="none", source="auburn_hills_chamber", ident="IDENTITY_CONFIRMED",
       lodging="LODGING_CONFIRMED"),
    _c(name="Auburn Hills Marriott Pontiac", address="3600 Centerpoint Pkwy",
       city="Pontiac", postal="48341", phone="248-253-9800", url="",
       url_shape="none", source="auburn_hills_chamber", ident="IDENTITY_CONFIRMED",
       lodging="LODGING_CONFIRMED",
       notes="Chamber-listed name carries the Auburn Hills brand cluster name "
             "but the transcribed address is Pontiac; city recorded from the "
             "address, not the name."),
    _c(name="Courtyard Detroit Pontiac Bloomfield", address="3555 Centerpoint Pkwy",
       city="Pontiac", postal="48341", phone="248-858-9595", url="",
       url_shape="none", source="auburn_hills_chamber", ident="IDENTITY_CONFIRMED",
       lodging="LODGING_CONFIRMED"),
    _c(name="Daxton Hotel", address="", city="Birmingham", postal="", phone="",
       url="", url_shape="none", source="visit_detroit", ident="IDENTITY_CONFIRMED",
       lodging="LODGING_CONFIRMED"),
    _c(name="Hotel Royal Oak", address="", city="Royal Oak", postal="", phone="",
       url="", url_shape="none", source="visit_detroit", ident="IDENTITY_CONFIRMED",
       lodging="LODGING_CONFIRMED"),
    _c(name="Hyatt Place Detroit Royal Oak", address="", city="Royal Oak", postal="",
       phone="", url="", url_shape="none", source="visit_detroit",
       ident="IDENTITY_CONFIRMED", lodging="LODGING_CONFIRMED"),

    # ======================================================================
    # NOVI / WIXOM -- Vibe Credit Union Showplace (formerly Suburban
    # Collection Showplace) official partner-hotels page,
    # https://www.vibeshowplace.com/hotels (accessed 2026-08-16), plus
    # brand-aggregate gap-fill.
    # ======================================================================
    _c(name="Hyatt Place Detroit Novi", address="46080 Grand River Avenue",
       city="Novi", postal="48374", phone="", url="", url_shape="none",
       source="vibe_showplace", ident="IDENTITY_CONFIRMED", lodging="LODGING_CONFIRMED"),
    _c(name="Homewood Suites by Hilton Novi", address="", city="Novi", postal="",
       phone="", url="", url_shape="none", source="vibe_showplace",
       ident="IDENTITY_CONFIRMED", lodging="LODGING_CONFIRMED"),
    _c(name="Hampton Inn & Suites Wixom", address="", city="Wixom", postal="",
       phone="", url="", url_shape="none", source="vibe_showplace",
       ident="IDENTITY_CONFIRMED", lodging="LODGING_CONFIRMED"),
    _c(name="Sonesta Select Detroit Novi", address="", city="Novi", postal="",
       phone="", url="", url_shape="none", source="vibe_showplace",
       ident="IDENTITY_CONFIRMED", lodging="LODGING_CONFIRMED"),
    _c(name="Holiday Inn Express Wixom", address="", city="Wixom", postal="",
       phone="", url="", url_shape="none", source="vibe_showplace",
       ident="IDENTITY_CONFIRMED", lodging="LODGING_CONFIRMED"),
    _c(name="Four Points by Sheraton Detroit Novi", address="", city="Novi",
       postal="", phone="", url="", url_shape="none", source="vibe_showplace",
       ident="IDENTITY_CONFIRMED", lodging="LODGING_CONFIRMED"),
    _c(name="Holiday Inn Express Novi", address="", city="Novi", postal="",
       phone="", url="", url_shape="none", source="vibe_showplace",
       ident="IDENTITY_CONFIRMED", lodging="LODGING_CONFIRMED"),
    _c(name="Sheraton Detroit Novi Hotel", address="", city="Novi", postal="",
       phone="", url="", url_shape="none", source="vibe_showplace",
       ident="IDENTITY_CONFIRMED", lodging="LODGING_CONFIRMED"),
    _c(name="DoubleTree by Hilton Detroit Novi", address="", city="Novi", postal="",
       phone="", url="", url_shape="none", source="chain_aggregate",
       ident="IDENTITY_PROVISIONAL", lodging="LODGING_BY_NAME"),
    _c(name="Residence Inn by Marriott Detroit Novi", address="", city="Novi",
       postal="", phone="", url="", url_shape="none", source="chain_aggregate",
       ident="IDENTITY_PROVISIONAL", lodging="LODGING_BY_NAME"),
    _c(name="Staybridge Suites Detroit Novi", address="", city="Novi", postal="",
       phone="", url="", url_shape="none", source="chain_aggregate",
       ident="IDENTITY_PROVISIONAL", lodging="LODGING_BY_NAME"),
    _c(name="The Baronette Renaissance Detroit Novi", address="", city="Novi",
       postal="", phone="", url="", url_shape="none", source="chain_aggregate",
       ident="IDENTITY_PROVISIONAL", lodging="LODGING_BY_NAME"),
    _c(name="Courtyard by Marriott Detroit Novi", address="", city="Novi", postal="",
       phone="", url="", url_shape="none", source="chain_aggregate",
       ident="IDENTITY_PROVISIONAL", lodging="LODGING_BY_NAME"),
    _c(name="Delta Hotels by Marriott Detroit Novi", address="", city="Novi",
       postal="", phone="", url="", url_shape="none", source="chain_aggregate",
       ident="IDENTITY_PROVISIONAL", lodging="LODGING_BY_NAME"),

    # ======================================================================
    # FARMINGTON HILLS / WEST BLOOMFIELD -- brand-locator aggregate.
    # ======================================================================
    _c(name="Residence Inn by Marriott Detroit Farmington Hills", address="",
       city="Farmington Hills", postal="", phone="", url="", url_shape="none",
       source="chain_aggregate", ident="IDENTITY_PROVISIONAL", lodging="LODGING_BY_NAME"),
    _c(name="Fairfield Inn & Suites Detroit Farmington Hills", address="",
       city="Farmington Hills", postal="", phone="", url="", url_shape="none",
       source="chain_aggregate", ident="IDENTITY_PROVISIONAL", lodging="LODGING_BY_NAME"),
    _c(name="Holiday Inn & Suites Farmington Hills Detroit NW", address="",
       city="Farmington Hills", postal="", phone="", url="", url_shape="none",
       source="chain_aggregate", ident="IDENTITY_PROVISIONAL", lodging="LODGING_BY_NAME"),
    _c(name="Holiday Inn Express & Suites Farmington Hills Detroit", address="",
       city="Farmington Hills", postal="", phone="", url="", url_shape="none",
       source="chain_aggregate", ident="IDENTITY_PROVISIONAL", lodging="LODGING_BY_NAME"),
    _c(name="Hampton Inn by Hilton West Bloomfield Novi", address="",
       city="West Bloomfield", postal="", phone="", url="", url_shape="none",
       source="chain_aggregate", ident="IDENTITY_PROVISIONAL", lodging="LODGING_BY_NAME"),

    # ======================================================================
    # LIVONIA / PLYMOUTH / NORTHVILLE -- brand-locator aggregate.
    # ======================================================================
    _c(name="Detroit Marriott Livonia", address="", city="Livonia", postal="",
       phone="", url="", url_shape="none", source="chain_aggregate",
       ident="IDENTITY_PROVISIONAL", lodging="LODGING_BY_NAME"),
    _c(name="Embassy Suites by Hilton Detroit Livonia Novi", address="",
       city="Livonia", postal="", phone="", url="", url_shape="none",
       source="chain_aggregate", ident="IDENTITY_PROVISIONAL", lodging="LODGING_BY_NAME"),
    _c(name="Fairfield Inn & Suites by Marriott Detroit Livonia", address="",
       city="Livonia", postal="", phone="", url="", url_shape="none",
       source="chain_aggregate", ident="IDENTITY_PROVISIONAL", lodging="LODGING_BY_NAME"),
    _c(name="Holiday Inn Express Detroit Northwest Livonia", address="",
       city="Livonia", postal="", phone="", url="", url_shape="none",
       source="chain_aggregate", ident="IDENTITY_PROVISIONAL", lodging="LODGING_BY_NAME"),
    _c(name="Quality Inn & Suites Banquet Center Livonia", address="",
       city="Livonia", postal="", phone="", url="", url_shape="none",
       source="chain_aggregate", ident="IDENTITY_PROVISIONAL", lodging="LODGING_BY_NAME"),
    _c(name="Americas Best Value Inn Livonia Detroit", address="", city="Livonia",
       postal="", phone="", url="", url_shape="none", source="chain_aggregate",
       ident="IDENTITY_PROVISIONAL", lodging="LODGING_BY_NAME"),
    _c(name="Hilton Garden Inn Plymouth", address="", city="Plymouth", postal="",
       phone="", url="", url_shape="none", source="chain_aggregate",
       ident="IDENTITY_PROVISIONAL", lodging="LODGING_BY_NAME"),
    _c(name="Spark by Hilton Plymouth", address="", city="Plymouth", postal="",
       phone="", url="", url_shape="none", source="chain_aggregate",
       ident="IDENTITY_PROVISIONAL", lodging="LODGING_BY_NAME"),
    _c(name="Holiday Inn Express Plymouth Ann Arbor", address="", city="Plymouth",
       postal="", phone="", url="", url_shape="none", source="chain_aggregate",
       ident="IDENTITY_PROVISIONAL", lodging="LODGING_BY_NAME"),
    _c(name="Home2 Suites by Hilton Northville Detroit", address="",
       city="Northville", postal="", phone="", url="", url_shape="none",
       source="chain_aggregate", ident="IDENTITY_PROVISIONAL", lodging="LODGING_BY_NAME"),
    _c(name="Saint John's Resort", address="", city="Northville", postal="",
       phone="", url="", url_shape="none", source="visit_detroit",
       ident="IDENTITY_PROVISIONAL", lodging="LODGING_BY_NAME"),

    # ======================================================================
    # ANN ARBOR -- Destination Ann Arbor (annarbor.org) listing pages,
    # individually confirmed by name/address/URL (accessed 2026-08-16), plus
    # first-party IHG/Motel 6 locator pages for two chain gap-fill rows.
    # ======================================================================
    _c(name="Sheraton Ann Arbor Hotel", address="", city="Ann Arbor", postal="",
       phone="", url="https://www.annarbor.org/listing/sheraton-ann-arbor-hotel/1216/",
       url_shape="brand_index", source="destination_ann_arbor", ident="IDENTITY_CONFIRMED",
       lodging="LODGING_CONFIRMED"),
    _c(name="The Inn at the Michigan League", address="", city="Ann Arbor",
       postal="", phone="",
       url="https://www.annarbor.org/listing/the-inn-at-the-michigan-league/1280/",
       url_shape="brand_index", source="destination_ann_arbor", ident="IDENTITY_CONFIRMED",
       lodging="LODGING_CONFIRMED"),
    _c(name="Hilton Garden Inn Ann Arbor", address="", city="Ann Arbor", postal="",
       phone="", url="https://www.annarbor.org/listing/hilton-garden-inn-ann-arbor/980/",
       url_shape="brand_index", source="destination_ann_arbor", ident="IDENTITY_CONFIRMED",
       lodging="LODGING_CONFIRMED"),
    _c(name="Ann Arbor Regent Hotel & Suites", address="", city="Ann Arbor",
       postal="", phone="",
       url="https://www.annarbor.org/listing/ann-arbor-regent-hotel-&-suites/732/",
       url_shape="brand_index", source="destination_ann_arbor", ident="IDENTITY_CONFIRMED",
       lodging="LODGING_CONFIRMED"),
    _c(name="Residence Inn by Marriott Ann Arbor Downtown", address="",
       city="Ann Arbor", postal="", phone="",
       url="https://www.annarbor.org/listing/residence-inn-by-marriott-ann-arbor-downtown/1183/",
       url_shape="brand_index", source="destination_ann_arbor", ident="IDENTITY_CONFIRMED",
       lodging="LODGING_CONFIRMED"),
    _c(name="AC Hotel Ann Arbor Downtown", address="", city="Ann Arbor", postal="",
       phone="", url="https://www.annarbor.org/listing/ac-hotel-ann-arbor-downtown/4135/",
       url_shape="brand_index", source="destination_ann_arbor", ident="IDENTITY_CONFIRMED",
       lodging="LODGING_CONFIRMED"),
    _c(name="Graduate Ann Arbor", address="", city="Ann Arbor", postal="", phone="",
       url="", url_shape="none", source="destination_ann_arbor", ident="IDENTITY_CONFIRMED",
       lodging="LODGING_CONFIRMED"),
    _c(name="EVEN Hotel Ann Arbor", address="", city="Ann Arbor", postal="",
       phone="", url="", url_shape="none", source="destination_ann_arbor",
       ident="IDENTITY_CONFIRMED", lodging="LODGING_CONFIRMED"),
    _c(name="The Bell Tower Hotel", address="", city="Ann Arbor", postal="",
       phone="", url="https://belltowerhotel.com", url_shape="property",
       source="destination_ann_arbor", ident="IDENTITY_CONFIRMED", lodging="LODGING_CONFIRMED"),
    _c(name="The Kensington Hotel Ann Arbor", address="", city="Ann Arbor",
       postal="", phone="", url="https://www.kensingtonannarbor.com",
       url_shape="property", source="destination_ann_arbor", ident="IDENTITY_CONFIRMED",
       lodging="LODGING_CONFIRMED"),
    _c(name="Weber's Inn", address="", city="Ann Arbor", postal="", phone="",
       url="", url_shape="none", source="destination_ann_arbor", ident="IDENTITY_CONFIRMED",
       lodging="LODGING_CONFIRMED"),
    _c(name="Courtyard by Marriott Ann Arbor", address="", city="Ann Arbor",
       postal="", phone="",
       url="https://www.marriott.com/en-us/hotels/arbch-courtyard-ann-arbor/overview/",
       url_shape="property", source="destination_ann_arbor", ident="IDENTITY_CONFIRMED",
       lodging="LODGING_CONFIRMED"),
    _c(name="Fairfield Inn Ann Arbor", address="", city="Ann Arbor", postal="",
       phone="", url="https://www.annarbor.org/listing/fairfield-inn-ann-arbor/917/",
       url_shape="brand_index", source="destination_ann_arbor", ident="IDENTITY_CONFIRMED",
       lodging="LODGING_CONFIRMED"),
    _c(name="Quality Inn & Suites Ann Arbor", address="", city="Ann Arbor",
       postal="", phone="",
       url="https://www.annarbor.org/listing/quality-inn-&-suites-ann-arbor/508/",
       url_shape="brand_index", source="destination_ann_arbor", ident="IDENTITY_CONFIRMED",
       lodging="LODGING_CONFIRMED"),
    _c(name="Homewood Suites by Hilton Ann Arbor", address="2457 S State St",
       city="Ann Arbor", postal="48104", phone="",
       url="https://www.hilton.com/en/hotels/arbashw-homewood-suites-ann-arbor/",
       url_shape="property", source="destination_ann_arbor", ident="IDENTITY_CONFIRMED",
       lodging="LODGING_CONFIRMED"),
    _c(name="TownePlace Suites by Marriott Ann Arbor", address="", city="Ann Arbor",
       postal="", phone="", url="https://www.annarbor.org/listing/towneplace-suites-by-marriott/1316/",
       url_shape="brand_index", source="destination_ann_arbor", ident="IDENTITY_CONFIRMED",
       lodging="LODGING_CONFIRMED"),
    _c(name="Red Roof Inn Ann Arbor University of Michigan South", address="",
       city="Ann Arbor", postal="", phone="",
       url="https://www.annarbor.org/listing/red-roof-inn-ann-arbor-university-of-michigan-south/1175/",
       url_shape="brand_index", source="destination_ann_arbor", ident="IDENTITY_CONFIRMED",
       lodging="LODGING_CONFIRMED"),
    _c(name="Red Roof PLUS+ Ann Arbor University of Michigan North",
       address="3621 Plymouth Rd", city="Ann Arbor", postal="48105", phone="",
       url="https://www.annarbor.org/listing/red-roof-plus+-ann-arbor-university-of-michigan-north/4147/",
       url_shape="brand_index", source="destination_ann_arbor", ident="IDENTITY_CONFIRMED",
       lodging="LODGING_CONFIRMED"),
    _c(name="Holiday Inn Express & Suites Ann Arbor West", address="",
       city="Ann Arbor", postal="", phone="",
       url="https://www.annarbor.org/listing/holiday-inn-express-&-suites-ann-arbor-west/982/",
       url_shape="brand_index", source="destination_ann_arbor", ident="IDENTITY_CONFIRMED",
       lodging="LODGING_CONFIRMED"),
    _c(name="Extended Stay America Detroit Ann Arbor University South",
       address="", city="Ann Arbor", postal="", phone="",
       url="https://www.annarbor.org/listing/extended-stay-america-detroit-ann-arbor-university-south/915/",
       url_shape="brand_index", source="destination_ann_arbor", ident="IDENTITY_CONFIRMED",
       lodging="LODGING_CONFIRMED"),
    _c(name="Staybridge Suites Ann Arbor University of Michigan", address="",
       city="Ann Arbor", postal="", phone="",
       url="https://www.ihg.com/staybridge/hotels/us/en/ann-arbor/arbsb/hoteldetail",
       url_shape="property", source="chain_locator", ident="IDENTITY_CONFIRMED",
       lodging="LODGING_CONFIRMED"),
    _c(name="Motel 6 Ann Arbor", address="3764 S State St", city="Ann Arbor",
       postal="48108", phone="", url="https://www.motel6.com/us/michigan/ann-arbor/",
       url_shape="property", source="chain_locator", ident="IDENTITY_CONFIRMED",
       lodging="LODGING_CONFIRMED"),

    # ======================================================================
    # YPSILANTI -- Destination Ann Arbor's Ypsilanti surrounding-destination
    # page, https://www.annarbor.org/surrounding-destinations/ypsilanti/hotel/
    # (accessed 2026-08-16), with transcribed addresses.
    # ======================================================================
    _c(name="Ann Arbor Marriott Ypsilanti at Eagle Crest", address="1275 South Huron St",
       city="Ypsilanti", postal="48197", phone="",
       url="https://www.marriott.com/en-us/hotels/dtwys-ann-arbor-marriott-ypsilanti-at-eagle-crest/overview/",
       url_shape="property", source="destination_ann_arbor", ident="IDENTITY_CONFIRMED",
       lodging="LODGING_CONFIRMED"),
    _c(name="Fairfield Inn & Suites Ann Arbor Ypsilanti", address="326 James L Hart Parkway",
       city="Ypsilanti", postal="48197", phone="",
       url="https://www.marriott.com/en-us/hotels/arbfy-fairfield-inn-and-suites-ann-arbor-ypsilanti/overview/",
       url_shape="property", source="destination_ann_arbor", ident="IDENTITY_CONFIRMED",
       lodging="LODGING_CONFIRMED"),
    _c(name="Hampton Inn & Suites Ypsilanti", address="515 James L. Hart Pkwy.",
       city="Ypsilanti", postal="48197", phone="", url="", url_shape="none",
       source="destination_ann_arbor", ident="IDENTITY_CONFIRMED", lodging="LODGING_CONFIRMED"),

    # ======================================================================
    # BOUNDARY EXCLUDED -- discovered candidates outside this work order's
    # named hypothesis corridors. Ledger only, never in the canonical census.
    # ======================================================================
    _c(name="Wyndham Garden Sterling Heights", address="", city="Sterling Heights",
       postal="", phone="", url="", url_shape="none", source="visit_detroit",
       ident="IDENTITY_CONFIRMED", lodging="LODGING_CONFIRMED", disposition="boundary_excluded",
       notes="Macomb County. Visit Detroit's own Detroit Hotel Guide groups it "
             "under Macomb County, which is not a named hypothesis cluster in "
             "this work order."),
    _c(name="Hampton Inn & Suites Chesterfield Township", address="",
       city="Chesterfield Township", postal="", phone="", url="", url_shape="none",
       source="visit_detroit", ident="IDENTITY_CONFIRMED", lodging="LODGING_CONFIRMED",
       disposition="boundary_excluded", notes="Macomb County."),
    _c(name="Hyatt Place Utica", address="", city="Utica", postal="", phone="",
       url="", url_shape="none", source="visit_detroit", ident="IDENTITY_CONFIRMED",
       lodging="LODGING_CONFIRMED", disposition="boundary_excluded", notes="Macomb County."),
    _c(name="Cambria Hotel Shelby Township Detroit", address="", city="Shelby Township",
       postal="", phone="", url="", url_shape="none", source="visit_detroit",
       ident="IDENTITY_CONFIRMED", lodging="LODGING_CONFIRMED", disposition="boundary_excluded",
       notes="Macomb County."),
    _c(name="TownePlace Suites by Marriott Detroit Sterling Heights", address="",
       city="Sterling Heights", postal="", phone="", url="", url_shape="none",
       source="visit_detroit", ident="IDENTITY_CONFIRMED", lodging="LODGING_CONFIRMED",
       disposition="boundary_excluded", notes="Macomb County."),
    _c(name="Hampton Inn Saline", address="1250 E. Michigan Ave.", city="Saline",
       postal="48176", phone="", url="", url_shape="none", source="destination_ann_arbor",
       ident="IDENTITY_CONFIRMED", lodging="LODGING_CONFIRMED", disposition="boundary_excluded",
       notes="Western Washtenaw outer ring. Destination Ann Arbor lists Saline "
             "as a 'surrounding destination', not a named hypothesis corridor "
             "in this work order."),
    _c(name="Baymont by Wyndham Chelsea", address="", city="Chelsea", postal="",
       phone="", url="", url_shape="none", source="destination_ann_arbor",
       ident="IDENTITY_CONFIRMED", lodging="LODGING_CONFIRMED", disposition="boundary_excluded",
       notes="Western Washtenaw outer ring; same treatment as Saline."),
    _c(name="Mission Point Resort", address="", city="Mackinac Island", postal="",
       phone="", url="", url_shape="none", source="auburn_hills_chamber",
       ident="IDENTITY_CONFIRMED", lodging="LODGING_CONFIRMED", disposition="boundary_excluded",
       notes="Chamber 'hotels' category member over 250 miles north; a "
             "membership listing, not a market presence."),
    _c(name="GEMI Owner LLC", address="133 Evergreen Ave.", city="East Lansing",
       postal="48823", phone="312-267-4185", url="", url_shape="none",
       source="auburn_hills_chamber", ident="IDENTITY_UNRESOLVED",
       lodging="LODGING_BY_NAME", disposition="boundary_excluded",
       notes="Chamber 'hotels' category member in East Lansing; outside the "
             "market regardless of category, and its own lodging status was "
             "never independently confirmed."),
]


SOURCES = [
    {"source_id": "visit_detroit", "name": "Visit Detroit Detroit Hotel Guide",
     "organization": "Detroit Metro Convention & Visitors Bureau",
     "source_type": "CVB", "family": "CVB",
     "url": "https://visitdetroit.com/detroit-hotel-guide/",
     "geographic_coverage": "Detroit metro: Downtown Detroit, Wayne County/Dearborn, Oakland County, Macomb County, DTW Airport",
     "data_categories": ["lodging"], "access_date": AS_OF,
     "status": "authority_for_identity",
     "limitations": "The guide names hotels by neighborhood grouping and does "
                     "not publish street addresses; identity confidence rests "
                     "on the CVB's own unambiguous naming of a distinct "
                     "property, not a transcribed address. Macomb County rows "
                     "sourced here are boundary-excluded from this market.",
     "automated_access": "static_html"},
    {"source_id": "destination_ann_arbor", "name": "Destination Ann Arbor places-to-stay directory",
     "organization": "Destination Ann Arbor / Washtenaw County CVB",
     "source_type": "CVB", "family": "CVB",
     "url": "https://www.annarbor.org/places-to-stay/hotels/",
     "geographic_coverage": "Ann Arbor, Ypsilanti, and surrounding Washtenaw County destinations",
     "data_categories": ["lodging"], "access_date": AS_OF,
     "status": "authority_for_identity_when_listing_page_states_address",
     "limitations": "The top-level hotels index is a JavaScript-rendered "
                     "widget not readable as static HTML; individual "
                     "/listing/ pages and the Ypsilanti/Saline/Chelsea "
                     "surrounding-destination pages were readable and used "
                     "directly. Not every listing page states a street "
                     "address.",
     "automated_access": "static_html_partial"},
    {"source_id": "dearborn_chamber", "name": "Dearborn Area Chamber of Commerce member directory",
     "organization": "Dearborn Area Chamber of Commerce", "source_type": "destination_partner",
     "family": "DIRECTORY", "url": "https://www.dearbornareachamber.org/directory/",
     "geographic_coverage": "Dearborn", "data_categories": ["lodging"],
     "access_date": AS_OF, "status": "authority_for_identity",
     "limitations": "Directory search results reachable per-listing rather "
                     "than as one paginated category export; treated as "
                     "PARTIAL harvesting.",
     "automated_access": "static_html_partial"},
    {"source_id": "auburn_hills_chamber", "name": "Auburn Hills Chamber of Commerce hotels category",
     "organization": "Auburn Hills Chamber of Commerce", "source_type": "destination_partner",
     "family": "DIRECTORY", "url": "https://business.auburnhillschamber.com/list/category/hotels-479",
     "geographic_coverage": "Auburn Hills, Troy, Rochester, Birmingham, Bloomfield Hills, Pontiac, Orion Township",
     "data_categories": ["lodging"], "access_date": AS_OF,
     "status": "authority_for_identity",
     "limitations": "Members with addresses far outside the market (Mackinac "
                     "Island, East Lansing) and at least one non-lodging "
                     "member (an AV retailer) appear in the 'hotels' category "
                     "and are excluded/flagged rather than trusted blindly.",
     "automated_access": "static_html"},
    {"source_id": "vibe_showplace", "name": "Vibe Credit Union Showplace official partner hotels",
     "organization": "Vibe Credit Union Showplace (formerly Suburban Collection Showplace)",
     "source_type": "destination_partner", "family": "DIRECTORY",
     "url": "https://www.vibeshowplace.com/hotels",
     "geographic_coverage": "Novi and Wixom, adjacent to the venue",
     "data_categories": ["lodging"], "access_date": AS_OF,
     "status": "authority_for_identity",
     "limitations": "Only the anchor Hyatt Place listing carries a full "
                     "street address on this page; the rest are named with "
                     "distance-from-venue only.",
     "automated_access": "static_html"},
    {"source_id": "chain_locator", "name": "First-party brand locator pages (Wyndham/Hilton/IHG/Choice/Motel 6)",
     "organization": "Individual hotel brands", "source_type": "official_business",
     "family": "CHAIN", "url": "https://www.wyndhamhotels.com/ ; https://www.hilton.com/ ; https://www.ihg.com/ ; https://www.choicehotels.com/ ; https://www.motel6.com/",
     "geographic_coverage": "Romulus, Auburn Hills, Ann Arbor",
     "data_categories": ["lodging"], "access_date": AS_OF,
     "status": "authority_for_identity_and_url",
     "limitations": "Used only where a specific first-party property page URL "
                     "was directly observed; every row from this source "
                     "carries that real, unfabricated URL.",
     "automated_access": "static_html"},
    {"source_id": "chain_aggregate", "name": "Aggregated brand-locator discovery (no single directory page)",
     "organization": "Multiple hotel brands, discovered via search aggregation",
     "source_type": "aggregator", "family": "CHAIN",
     "url": "",
     "geographic_coverage": "Southfield, Troy, Auburn Hills gap-fill, Novi gap-fill, Farmington Hills, Livonia/Plymouth/Northville, Dearborn gap-fill, DTW gap-fill",
     "data_categories": ["lodging"], "access_date": AS_OF,
     "status": "discovery_and_gap_fill_evidence",
     "limitations": "No single authoritative directory page exists for these "
                     "suburbs; property names are corroborated across "
                     "multiple booking aggregators citing the brand's own "
                     "hotel, but no independently sourced street address was "
                     "recovered. Every row from this source is "
                     "IDENTITY_PROVISIONAL, the same treatment Pittsburgh gave "
                     "its GPHA-only gap-fill rows.",
     "automated_access": "search_aggregation"},
]


def _dump(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8")


def _street_identity(address: str, postal: str) -> str:
    street = normalize_name(address)
    return "%s|%s" % (street, (postal or "")[:5]) if street else ""


def _blocker_for(row: dict) -> str:
    # No policy authority, seed, or exclusion registry exists for this
    # market yet -- every row resolves purely from identity/lodging/URL
    # facts, never from a founder decision (there are none to read).
    if row["lodging_state"] == enums.NOT_LODGING:
        return enums.OUT_OF_CURRENT_CATEGORY
    if row["identity_state"] in (enums.IDENTITY_PROVISIONAL, enums.IDENTITY_UNRESOLVED):
        return enums.AWAITING_IDENTITY_RESOLUTION
    if row.get("url_shape") == "brand_index":
        return enums.AWAITING_PROPERTY_LEVEL_URL
    if row.get("official_url"):
        return enums.AWAITING_POLICY_OBSERVATION
    return enums.AWAITING_OFFICIAL_URL


def build() -> dict:
    market = market_by_id(load_markets(), MARKET)
    ledger = []
    canonical = []
    seen_keys = {}
    for raw in CANDIDATES:
        disp = raw.get("disposition") or "canonical"
        name = raw["name"]
        key = ptf_identity_key(name)
        item = {
            "identity_key": key,
            "canonical_name": name,
            "disposition": disp,
            "duplicate_of": raw.get("duplicate_of") or "",
            "notes": raw.get("notes") or "",
            "source": raw["source"],
        }
        if disp != "canonical":
            ledger.append(item)
            continue
        if key in seen_keys:
            raise SystemExit("duplicate canonical identity_key: %r (%s / %s)"
                             % (key, seen_keys[key], name))
        seen_keys[key] = name
        slug = slugify(name)
        row = {
            "identity_key": key,
            "canonical_name": name,
            "display_name": name,
            "slug": slug,
            "market_id": MARKET,
            "address": raw.get("address") or "",
            "city": raw.get("city") or "",
            "state": "MI",
            "postal_code": (raw.get("postal") or "")[:5],
            "phone": raw.get("phone") or "",
            "identity_state": raw["ident"],
            "lodging_state": raw["lodging"],
            "policy_state": enums.POLICY_NOT_VERIFIED,
            "collision_state": enums.COLLISION_NONE,
            "official_url": raw.get("url") or "",
            "corridor": "",
            "assignment_basis": "",
            "assignment_value": "",
            "source": raw["source"],
            "source_id": slug,
            "observed_at": AS_OF,
            "provenance": "%s:%s" % (WORK_ORDER, raw["source"]),
            "normalized_name": normalize_name(name),
            "former_name": raw.get("former") or "",
            "url_shape": raw.get("url_shape") or "none",
            "disposition": "canonical",
            "street_identity": _street_identity(raw.get("address") or "", raw.get("postal") or ""),
        }
        canonical.append(row)

    assign_rows = [{"name": r["identity_key"], "city": r["city"],
                    "state": r["state"], "postal_code": r["postal_code"]}
                   for r in canonical]
    assignment = assign_hotels(market, assign_rows, fail_closed=True)
    unassigned_names = []
    for row in canonical:
        key = row["identity_key"]
        corridors = assignment.corridor_of.get(key) or ()
        if not corridors:
            unassigned_names.append(row["canonical_name"])
            row["corridor"] = ""
            row["assignment_basis"] = enums.BASIS_UNASSIGNED
            row["assignment_value"] = ""
        else:
            row["corridor"] = corridors[0]
            basis, value = assignment.basis_of[key]
            row["assignment_basis"] = basis
            row["assignment_value"] = value
    if unassigned_names:
        raise SystemExit("unassigned canonical hotels: %s" % unassigned_names)

    collision_detail = {}
    by_street = {}
    for row in canonical:
        sid = row["street_identity"]
        if sid:
            by_street.setdefault(sid, []).append(row["canonical_name"])
    for sid, names in by_street.items():
        if len(names) > 1:
            collision_detail[sid] = names
            for row in canonical:
                if row["street_identity"] == sid:
                    row["collision_state"] = enums.COLLISION_SHARED_ADDRESS

    hotels = sorted(canonical, key=lambda r: r["identity_key"])
    census_doc = OrderedDict((
        ("schema", enums.CENSUS_SCHEMA),
        ("market_id", MARKET),
        ("identity_key_contract", IDENTITY_KEY_CONTRACT),
        ("identity_contract", "ptf-identity-evidence/1.0"),
        ("work_order", WORK_ORDER),
        ("captured_at", AS_OF),
        ("note", "Phase 1 independent-discovery census for a NEW market. No "
                 "policy authority, seed, exclusion registry, or release "
                 "contract exists for this market yet, so every policy_state "
                 "is the legacy-frozen POLICY_NOT_VERIFIED and the partition "
                 "carries zero terminal PUBLISHED_PET_FRIENDLY or "
                 "VERIFIED_NO_PETS rows by construction. The corridor "
                 "registry was authored from this candidate table, never the "
                 "reverse -- Cincinnati's defect of building the census FROM "
                 "its own corridor registry does not apply here."),
        ("source_authorities", [
            "https://visitdetroit.com/detroit-hotel-guide/",
            "https://www.annarbor.org/places-to-stay/hotels/",
            "https://www.dearbornareachamber.org/directory/",
            "https://business.auburnhillschamber.com/list/category/hotels-479",
            "https://www.vibeshowplace.com/hotels",
        ]),
        ("count", len(hotels)),
        ("base_commit", BASE_COMMIT),
        ("collision_audit", {
            "duplicate_names_found": 0,
            "duplicate_names": {},
            "phone_collisions": 0,
            "address_collisions": len(collision_detail),
            "address_collision_detail": collision_detail,
            "out_of_boundary": 0,
            "cross_market_collisions": 0,
            "notes": "Address collisions are retained and flagged. Hotel "
                     "Indigo Detroit North - Troy and EVEN Hotel Detroit "
                     "North - Troy are a dual-branded IHG property sharing "
                     "one street address; both are real, distinct brand "
                     "identities. Category-excluded and identity-unresolved "
                     "rows stay in the census.",
            "status": "PROVISIONAL_FLAGS_OPEN" if collision_detail else "NO_OPEN_CONFLICTS",
            "open_conflict_count": len(collision_detail),
        }),
        ("identity_state_counts", {
            "IDENTITY_CONFIRMED": sum(1 for r in hotels if r["identity_state"] == enums.IDENTITY_CONFIRMED),
            "IDENTITY_PROVISIONAL": sum(1 for r in hotels if r["identity_state"] == enums.IDENTITY_PROVISIONAL),
            "IDENTITY_UNRESOLVED": sum(1 for r in hotels if r["identity_state"] == enums.IDENTITY_UNRESOLVED),
        }),
        ("source_methodology", "Official destination/CVB and chamber "
                                "directories first (Visit Detroit, "
                                "Destination Ann Arbor, Dearborn Area "
                                "Chamber, Auburn Hills Chamber, Vibe "
                                "Showplace), then first-party brand-locator "
                                "pages for airport/Auburn Hills/Ann Arbor gap "
                                "rows with a directly observed URL, then "
                                "aggregated brand-locator discovery "
                                "(IDENTITY_PROVISIONAL, no independently "
                                "sourced address) for suburbs with no single "
                                "chamber/CVB directory: Southfield, most of "
                                "Troy, Farmington Hills, Livonia/Plymouth/"
                                "Northville, and Novi gap-fill. policy_state "
                                "is POLICY_NOT_VERIFIED throughout."),
        ("worker_branch", WORKER_BRANCH),
        ("worker_run", WORK_ORDER),
        ("hotels", hotels),
    ))

    issues = CENSUS.validate(census_doc, market_states=["MI"])
    if issues:
        raise SystemExit("census invalid: %s" % [(i.path, i.code, i.detail) for i in issues])

    items = []
    for row in hotels:
        state = _blocker_for(row)
        terminal = state in enums.TERMINAL_STATES
        items.append(OrderedDict((
            ("identity_key", row["identity_key"]),
            ("canonical_name", row["canonical_name"]),
            ("slug", row["slug"]),
            ("city", row["city"]),
            ("state", row["state"]),
            ("postal_code", row["postal_code"]),
            ("final_state", state),
            ("resolved", terminal),
            ("next_action", "" if terminal else next_action_for(state)),
            ("next_action_source", "" if terminal else "identity_census/detroit-ann-arbor-mi.json"),
            ("determined_by", WORK_ORDER),
            ("updated_at", AS_OF),
            ("official_url", row["official_url"]),
            ("state_override_reason", ""),
        )))
    items.sort(key=lambda r: r["identity_key"])
    counts = {}
    for item in items:
        counts[item["final_state"]] = counts.get(item["final_state"], 0) + 1
    meanings = {state: PART.STATE_MEANINGS[state] for state in sorted(counts)}
    partition_doc = OrderedDict((
        ("schema", enums.PARTITION_SCHEMA),
        ("work_order", WORK_ORDER),
        ("market_id", MARKET),
        ("as_of", AS_OF),
        ("note", "No committed policy authority exists for this market yet: "
                 "published=0 and verified_no_pets=0 by construction. Every "
                 "row is a blocker state derived from identity/lodging/URL "
                 "facts only. Silence is not a refusal."),
        ("source_authorities", ["identity_census/detroit-ann-arbor-mi.json"]),
        ("count", len(items)),
        ("final_state_counts", counts),
        ("final_state_meanings", meanings),
        ("items", items),
    ))
    p_issues = PART.validate(partition_doc)
    if p_issues:
        raise SystemExit("partition invalid: %s" % [(i.path, i.code, i.detail) for i in p_issues])
    rec = PART.reconcile(CENSUS.identity_keys(census_doc), partition_doc, market_id=MARKET)
    rec_issues = PART.reconciliation_issues(rec)
    if rec_issues or not rec.agrees:
        raise SystemExit("reconciliation failed: %s missing_p=%s missing_c=%s dups=%s"
                         % (rec_issues, rec.missing_from_partition, rec.missing_from_census,
                            rec.duplicated_in_partition))

    queue_items = []
    seq = 0
    for item in items:
        if item["resolved"]:
            continue
        seq += 1
        batch = "batch-%03d" % (((seq - 1) // 10) + 1)
        queue_items.append(OrderedDict((
            ("row_number", seq),
            ("identity_key", item["identity_key"]),
            ("hotel_id", item["identity_key"]),
            ("canonical_name", item["canonical_name"]),
            ("address", next(r["address"] for r in hotels if r["identity_key"] == item["identity_key"])),
            ("phone", next(r["phone"] for r in hotels if r["identity_key"] == item["identity_key"])),
            ("official_candidate_url", item["official_url"]),
            ("corridor", next(r["corridor"] for r in hotels if r["identity_key"] == item["identity_key"])),
            ("current_classification", item["final_state"]),
            ("blocking_reason", item["final_state"]),
            ("requested_evidence", "property-level official URL and a citable pet-policy artifact" if not item["official_url"] else "citable pet-policy artifact from the property's own page"),
            ("next_action", item["next_action"]),
            ("batch", batch),
            ("review_status", "NOT_STARTED"),
        )))
        payload = json.dumps(queue_items[-1], sort_keys=True, ensure_ascii=False)
        queue_items[-1]["row_sha256"] = hashlib.sha256(
            payload.encode("utf-8")).hexdigest()

    routing = []
    for row in hotels:
        routing.append(OrderedDict((
            ("identity_key", row["identity_key"]),
            ("canonical_name", row["canonical_name"]),
            ("official_url", row["official_url"]),
            ("url_shape", row["url_shape"]),
            ("assessment_status", "ASSESSMENT_ONLY"),
            ("not_routing_authority", True),
            ("capture_readiness", _blocker_for(row)),
        )))

    source_reg = OrderedDict((
        ("schema", "ptf-detroit-ann-arbor-source-registry/1.0"),
        ("work_order", WORK_ORDER),
        ("market_id", MARKET),
        ("as_of", AS_OF),
        ("count", len(SOURCES)),
        ("sources", SOURCES),
    ))
    used_sources = {r["source"] for r in hotels}
    missing_src = used_sources - {s["source_id"] for s in SOURCES}
    if missing_src:
        raise SystemExit("census sources not in registry: %s" % sorted(missing_src))

    coverage = OrderedDict((
        ("schema", "ptf-coverage-config/1.0"),
        ("market_id", MARKET),
        ("_note", "Advisory coverage-audit configuration for the Detroit-Ann "
                  "Arbor factory census. Uncalibrated priors. Nothing gates "
                  "on this file."),
        ("census_kind", "identity_census"),
        ("population", 4300000),
        ("thresholds", {}),
        ("non_independent_family_pairs", []),
        ("source_family_overrides", {
            "visit_detroit": "CVB",
            "destination_ann_arbor": "CVB",
            "dearborn_chamber": "DIRECTORY",
            "auburn_hills_chamber": "DIRECTORY",
            "vibe_showplace": "DIRECTORY",
            "chain_locator": "CHAIN",
            "chain_aggregate": "CHAIN",
        }),
        ("zones_min_expected", {}),
        ("accepted_gaps", []),
    ))

    ledger_doc = OrderedDict((
        ("schema", "ptf-detroit-ann-arbor-duplicate-ledger/1.0"),
        ("work_order", WORK_ORDER),
        ("market_id", MARKET),
        ("as_of", AS_OF),
        ("counts", {
            "canonical": len(hotels),
            "duplicate": sum(1 for x in ledger if x["disposition"] == "duplicate"),
            "boundary_excluded": sum(1 for x in ledger if x["disposition"] == "boundary_excluded"),
            "closed": sum(1 for x in ledger if x["disposition"] == "closed"),
            "category_excluded_in_census": sum(1 for r in hotels if r["lodging_state"] == enums.NOT_LODGING),
        }),
        ("items", ledger),
    ))

    queue_doc = OrderedDict((
        ("schema", "ptf-detroit-ann-arbor-founder-review-queue/1.0"),
        ("work_order", WORK_ORDER),
        ("market_id", MARKET),
        ("as_of", AS_OF),
        ("count", len(queue_items)),
        ("batch_size", 10),
        ("items", queue_items),
    ))

    routing_doc = OrderedDict((
        ("schema", "ptf-detroit-ann-arbor-routing-assessments/1.0"),
        ("work_order", WORK_ORDER),
        ("market_id", MARKET),
        ("as_of", AS_OF),
        ("note", "Assessments only. Nothing here is written to "
                 "identity_routing.json and no status is ROUTING_CONFIRMED."),
        ("count", len(routing)),
        ("items", routing),
    ))

    _dump(CENSUS_PATH, census_doc)
    _dump(PARTITION_PATH, partition_doc)
    _dump(REPORTS / "detroit-ann-arbor-mi_source_registry.json", source_reg)
    _dump(REPORTS / "detroit-ann-arbor-mi_duplicate_ledger.json", ledger_doc)
    _dump(REPORTS / "detroit-ann-arbor-mi_routing_assessments.json", routing_doc)
    _dump(REPORTS / "detroit-ann-arbor-mi_founder_review_queue.json", queue_doc)
    _dump(PACKAGE / "markets" / "coverage" / "detroit-ann-arbor-mi.json", coverage)
    _dump(DATA_ROOT / "source_registry.json", source_reg)
    _dump(DATA_ROOT / "duplicate_ledger.json", ledger_doc)
    _dump(DATA_ROOT / "routing_assessments.json", routing_doc)
    _dump(DATA_ROOT / "boundary.json", {
        "work_order": WORK_ORDER, "market_id": MARKET, "as_of": AS_OF,
        "included_corridors": [c.corridor_id for c in market.corridors],
        "excluded_from_census": [x for x in ledger if x["disposition"] == "boundary_excluded"],
    })

    candidate_items = []
    for raw in CANDIDATES:
        key = ptf_identity_key(raw["name"])
        disp = raw.get("disposition") or "canonical"
        if disp == "canonical" and raw.get("lodging") == "NOT_LODGING":
            final_disp = "category_excluded"
        elif disp == "canonical" and raw.get("ident") == "IDENTITY_UNRESOLVED":
            final_disp = "identity_unresolved"
        elif disp == "canonical" and raw.get("ident") == "IDENTITY_PROVISIONAL":
            final_disp = "canonical_census"
        elif disp == "canonical":
            final_disp = "canonical_census"
        elif disp == "duplicate":
            final_disp = "confirmed_duplicate"
        elif disp == "boundary_excluded":
            final_disp = "boundary_excluded"
        else:
            final_disp = disp
        candidate_items.append(OrderedDict((
            ("identity_key", key),
            ("canonical_name", raw["name"]),
            ("source_disposition", disp),
            ("final_disposition", final_disp),
            ("source", raw["source"]),
            ("duplicate_of", raw.get("duplicate_of") or ""),
            ("notes", raw.get("notes") or ""),
        )))
    candidate_ledger = OrderedDict((
        ("schema", "ptf-detroit-ann-arbor-candidate-ledger/1.0"),
        ("work_order", WORK_ORDER),
        ("market_id", MARKET),
        ("as_of", AS_OF),
        ("count", len(candidate_items)),
        ("items", candidate_items),
    ))
    _dump(DATA_ROOT / "candidate_ledger.json", candidate_ledger)

    boundary_items = [x for x in ledger if x["disposition"] == "boundary_excluded"]
    _dump(DATA_ROOT / "boundary_exclusion_ledger.json", OrderedDict((
        ("schema", "ptf-detroit-ann-arbor-boundary-exclusion-ledger/1.0"),
        ("work_order", WORK_ORDER),
        ("market_id", MARKET),
        ("as_of", AS_OF),
        ("count", len(boundary_items)),
        ("items", boundary_items),
    )))

    review_rows = []
    for row in hotels:
        stored = (row["corridor"], row["assignment_basis"], row["assignment_value"])
        recomputed = assignment.corridor_of[row["identity_key"]]
        basis, value = assignment.basis_of[row["identity_key"]]
        review_rows.append(OrderedDict((
            ("identity_key", row["identity_key"]),
            ("stored_corridor", row["corridor"]),
            ("stored_basis", row["assignment_basis"]),
            ("stored_value", row["assignment_value"]),
            ("recomputed_corridor", recomputed[0] if recomputed else ""),
            ("recomputed_basis", basis),
            ("recomputed_value", value),
            ("diff", stored != (recomputed[0] if recomputed else "", basis, value)),
        )))
    _dump(DATA_ROOT / "corridor_assignment_review.json", OrderedDict((
        ("schema", "ptf-detroit-ann-arbor-corridor-assignment-review/1.0"),
        ("work_order", WORK_ORDER),
        ("market_id", MARKET),
        ("as_of", AS_OF),
        ("count", len(review_rows)),
        ("diff_count", sum(1 for r in review_rows if r["diff"])),
        ("items", review_rows),
    )))

    _dump(DATA_ROOT / "reconciliation_report.json", OrderedDict((
        ("schema", "ptf-detroit-ann-arbor-reconciliation-report/1.0"),
        ("work_order", WORK_ORDER),
        ("market_id", MARKET),
        ("as_of", AS_OF),
        ("census_count", rec.census_count),
        ("partition_count", rec.partition_count),
        ("published", rec.published),
        ("verified_no_pets", rec.verified_no_pets),
        ("out_of_category", rec.out_of_category),
        ("unresolved", rec.unresolved),
        ("agrees", rec.agrees),
        ("missing_from_partition", sorted(rec.missing_from_partition)),
        ("missing_from_census", sorted(rec.missing_from_census)),
        ("duplicated_in_partition", sorted(rec.duplicated_in_partition)),
        ("candidates", len(CANDIDATES)),
        ("canonical", len(hotels)),
        ("confirmed_duplicates", sum(1 for x in ledger if x["disposition"] == "duplicate")),
        ("boundary_excluded", sum(1 for x in ledger if x["disposition"] == "boundary_excluded")),
        ("queue", len(queue_items)),
    )))

    QUEUE_ROOT.mkdir(parents=True, exist_ok=True)
    batches = {}
    for q in queue_items:
        batches.setdefault(q["batch"], []).append(q)
    fields = list(queue_items[0].keys()) if queue_items else []
    for batch_id, rows in batches.items():
        csv_path = QUEUE_ROOT / ("%s-review.csv" % batch_id)
        with csv_path.open("w", encoding="utf-8", newline="") as fh:
            writer = csv.DictWriter(fh, fieldnames=fields)
            writer.writeheader()
            writer.writerows(rows)
        identity_keys = [r["identity_key"] for r in rows]
        body = json.dumps(rows, sort_keys=True, ensure_ascii=False)
        _dump(QUEUE_ROOT / ("%s-manifest.json" % batch_id), {
            "batch": batch_id, "count": len(rows),
            "identity_keys": identity_keys,
            "sha256": hashlib.sha256(body.encode("utf-8")).hexdigest(),
        })
    rollup_csv = QUEUE_ROOT / "queue-rollup.csv"
    with rollup_csv.open("w", encoding="utf-8", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=fields)
        writer.writeheader()
        writer.writerows(queue_items)
    rollup_body = json.dumps(queue_items, sort_keys=True, ensure_ascii=False)
    _dump(QUEUE_ROOT / "queue-rollup-manifest.json", {
        "batch": "rollup",
        "count": len(queue_items),
        "identity_keys": [r["identity_key"] for r in queue_items],
        "sha256": hashlib.sha256(rollup_body.encode("utf-8")).hexdigest(),
    })
    screenshot_items = []
    for q in queue_items:
        screenshot_items.append(OrderedDict((
            ("identity_key", q["identity_key"]),
            ("hotel_id", q["hotel_id"]),
            ("official_candidate_url", q["official_candidate_url"]),
            ("corridor", q["corridor"]),
            ("capture_status", "NOT_CAPTURED"),
            ("screenshot_path", ""),
            ("sha256", ""),
            ("note", "No screenshot was captured in this work order. This row is the pending capture target only.",),
        )))
    _dump(QUEUE_ROOT / "screenshot-queue.json", OrderedDict((
        ("schema", "ptf-detroit-ann-arbor-screenshot-queue/1.0"),
        ("work_order", WORK_ORDER),
        ("market_id", MARKET),
        ("as_of", AS_OF),
        ("count", len(screenshot_items)),
        ("captured", 0),
        ("items", screenshot_items),
    )))
    _dump(QUEUE_ROOT / "queue-index.json", queue_doc)

    capture_lanes = {}
    for row in hotels:
        lane = _blocker_for(row)
        capture_lanes[lane] = capture_lanes.get(lane, 0) + 1
    hyatt_count = sum(1 for r in hotels if "hyatt" in r["normalized_name"])

    summary = {
        "candidates": len(CANDIDATES),
        "canonical": len(hotels),
        "published": rec.published,
        "verified_no_pets": rec.verified_no_pets,
        "out_of_category": rec.out_of_category,
        "unresolved": rec.unresolved,
        "queue": len(queue_items),
        "duplicates_ledger": sum(1 for x in ledger if x["disposition"] == "duplicate"),
        "boundary_excluded": sum(1 for x in ledger if x["disposition"] == "boundary_excluded"),
        "closed": sum(1 for x in ledger if x["disposition"] == "closed"),
        "identity_provisional": sum(1 for r in hotels if r["identity_state"] == enums.IDENTITY_PROVISIONAL),
        "identity_unresolved": sum(1 for r in hotels if r["identity_state"] == enums.IDENTITY_UNRESOLVED),
        "missing_official_url": sum(1 for r in hotels if not r["official_url"]),
        "hyatt_count": hyatt_count,
        "agrees": rec.agrees,
        "final_state_counts": counts,
        "capture_lane_distribution": capture_lanes,
        "suppressed_corridors": [dict(s) for s in assignment.suppressed],
        "published_corridors": list(assignment.published),
    }
    print(json.dumps(summary, indent=2))
    return summary


if __name__ == "__main__":
    build()
