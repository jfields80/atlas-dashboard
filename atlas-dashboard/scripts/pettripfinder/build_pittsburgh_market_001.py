"""PTF-PITTSBURGH-MARKET-REVALIDATION-001 -- revalidate the Pittsburgh factory.

Ports the PTF-PITTSBURGH-MARKET-BUILD-001 candidate table onto canonical
fea73de. Builds the tracked census, partition, source registry, duplicate
ledger, routing assessments, founder-review queue, coverage config, and
utility inventory. No policy authority, seed, exclusion registry, release
contract, or assembler file is written.

Every census policy_state is POLICY_NOT_VERIFIED. Run:

    python -m scripts.pettripfinder.build_pittsburgh_market_001
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

WORK_ORDER = "PTF-PITTSBURGH-MARKET-REVALIDATION-001"
SOURCE_WORK_ORDER = "PTF-PITTSBURGH-MARKET-BUILD-001"
MARKET = "pittsburgh-pa"
AS_OF = "2026-08-15"
BASE_COMMIT = "fea73de1ec699289cf04b88fd7069cf23fa4d735"
WORKER_BRANCH = "grok/ptf-pittsburgh-revalidation-001"
PACKAGE = _REPO_ROOT / "launch_packages" / "pettripfinder"
REPORTS = PACKAGE / "markets" / "reports"
CENSUS_PATH = PACKAGE / "identity_census" / ("%s.json" % MARKET)
PARTITION_PATH = PACKAGE / "pittsburgh_final_partition_001.json"
DATA_ROOT = _REPO_ROOT / "data" / "market_research" / "pittsburgh"
QUEUE_ROOT = _REPO_ROOT / "data" / "operator_evidence" / "pittsburgh-founder-review-001"

# disposition: canonical | duplicate | boundary_excluded | closed | category_excluded
# url_shape: property | brand_index | none


def _c(**kw):
    return kw


CANDIDATES = [
    # --- Cultural Trust (destination partner), addresses transcribed ---
    _c(name="Omni William Penn Hotel", address="530 William Penn Place", city="Pittsburgh",
       postal="15219", phone="412-281-7100",
       url="https://www.omnihotels.com/hotels/pittsburgh-william-penn",
       url_shape="property", source="cultural_trust", ident="IDENTITY_CONFIRMED",
       lodging="LODGING_CONFIRMED"),
    _c(name="Cambria Hotel Pittsburgh Downtown", address="1320 Centre Avenue",
       city="Pittsburgh", postal="15219", phone="412-381-6687",
       url="https://www.cambriapgh.com", url_shape="property",
       source="cultural_trust", ident="IDENTITY_CONFIRMED", lodging="LODGING_CONFIRMED"),
    _c(name="Courtyard by Marriott Pittsburgh Downtown", address="945 Penn Avenue",
       city="Pittsburgh", postal="15222", phone="412-434-5551",
       url="https://www.marriott.com/en-us/hotels/pitcy-courtyard-pittsburgh-downtown/overview/",
       url_shape="property", source="cultural_trust", ident="IDENTITY_CONFIRMED",
       lodging="LODGING_CONFIRMED"),
    _c(name="Joinery Hotel Pittsburgh", address="453 Boulevard of the Allies",
       city="Pittsburgh", postal="15219", phone="412-339-1870",
       url="https://www.joineryhotel.com", url_shape="property",
       source="cultural_trust", ident="IDENTITY_CONFIRMED", lodging="LODGING_CONFIRMED",
       former="Distrikt Hotel Pittsburgh",
       notes="PGH-P1-D003 founder-approved rename/conversion "
             "(PTF-PITTSBURGH-PASS1-DECISION-APPLICATION-001): the queued "
             "distrikthotelpittsburgh.com URL 301s to joineryhotel.com, whose "
             "first-party pages render the identical street address (453 "
             "Boulevard of the Allies) and phone (412-339-1870). Brand "
             "affiliation: Curio Collection by Hilton. The Joinery pet policy "
             "observed during Pass 1 under the old identity is provenance "
             "only; it must be recaptured under this identity before any "
             "publication."),
    _c(name="DoubleTree by Hilton Hotel & Suites Pittsburgh Downtown",
       address="One Bigelow Square", city="Pittsburgh", postal="15219",
       phone="412-281-5800",
       url="https://www.hilton.com/en/hotels/pitdtdt-doubletree-hotel-and-suites-pittsburgh-downtown/",
       url_shape="property", source="cultural_trust", ident="IDENTITY_CONFIRMED",
       lodging="LODGING_CONFIRMED"),
    _c(name="Drury Plaza Hotel Pittsburgh Downtown", address="745 Grant Street",
       city="Pittsburgh", postal="15219", phone="412-281-2900",
       url="https://www.druryhotels.com/locations/pittsburgh-pa/drury-plaza-hotel-pittsburgh-downtown",
       url_shape="property", source="cultural_trust", ident="IDENTITY_CONFIRMED",
       lodging="LODGING_CONFIRMED"),
    _c(name="Etage Executive Living Downtown", address="424 Stanwix Street",
       city="Pittsburgh", postal="15222", phone="412-646-8696",
       url="https://www.stayetage.com", url_shape="property",
       source="cultural_trust", ident="IDENTITY_CONFIRMED", lodging="LODGING_CONFIRMED"),
    _c(name="EVEN Hotel Pittsburgh Downtown", address="425 Forbes Ave",
       city="Pittsburgh", postal="15219", phone="412-301-2277",
       url="https://www.ihg.com/evenhotels/hotels/us/en/pittsburgh/pitev/hoteldetail",
       url_shape="property", source="cultural_trust", ident="IDENTITY_CONFIRMED",
       lodging="LODGING_CONFIRMED"),
    _c(name="Fairmont Pittsburgh", address="510 Market Street", city="Pittsburgh",
       postal="15222", phone="412-773-8800",
       url="https://www.fairmont.com/pittsburgh", url_shape="property",
       source="cultural_trust", ident="IDENTITY_CONFIRMED", lodging="LODGING_CONFIRMED"),
    _c(name="Hampton Inn & Suites Pittsburgh Downtown", address="1247 Smallman Street",
       city="Pittsburgh", postal="15222", phone="412-288-4350",
       url="https://www.hilton.com/en/hotels/pitdnhx-hampton-suites-pittsburgh-downtown/",
       url_shape="property", source="cultural_trust", ident="IDENTITY_CONFIRMED",
       lodging="LODGING_CONFIRMED"),
    _c(name="Hilton Garden Inn Pittsburgh Downtown", address="250 Forbes Avenue",
       city="Pittsburgh", postal="15222", phone="412-281-5557",
       url="https://www.hilton.com/en/hotels/pitfagi-hilton-garden-inn-pittsburgh-downtown/",
       url_shape="property", source="cultural_trust", ident="IDENTITY_CONFIRMED",
       lodging="LODGING_CONFIRMED"),
    _c(name="Homewood Suites Pittsburgh Downtown", address="1410 Smallman Street",
       city="Pittsburgh", postal="15222", phone="412-232-0200",
       url="https://www.hilton.com/en/hotels/pitdohw-homewood-suites-pittsburgh-downtown/",
       url_shape="property", source="cultural_trust", ident="IDENTITY_CONFIRMED",
       lodging="LODGING_CONFIRMED"),
    _c(name="Hyatt Place Pittsburgh North Shore", address="260 North Shore Drive",
       city="Pittsburgh", postal="15212", phone="412-321-3000",
       url="https://www.hyatt.com/en-US/hotel/pennsylvania/hyatt-place-pittsburgh-north-shore/pitzn",
       url_shape="property", source="cultural_trust", ident="IDENTITY_CONFIRMED",
       lodging="LODGING_CONFIRMED"),
    _c(name="Pittsburgh Marriott City Center", address="112 Washington Place",
       city="Pittsburgh", postal="15219", phone="412-471-4000",
       url="https://www.marriott.com/en-us/hotels/pitdt-pittsburgh-marriott-city-center/overview/",
       url_shape="property", source="cultural_trust", ident="IDENTITY_CONFIRMED",
       lodging="LODGING_CONFIRMED"),
    _c(name="The Atterbury Hotel Autograph Collection", address="107 Sixth Street",
       city="Pittsburgh", postal="15222", phone="412-562-1200",
       url="https://www.marriott.com/en-us/hotels/pitkd-the-atterbury-hotel-autograph-collection/overview/",
       url_shape="property", source="visit_pittsburgh", ident="IDENTITY_CONFIRMED",
       lodging="LODGING_CONFIRMED", former="Renaissance Pittsburgh Hotel"),
    _c(name="Residence Inn Pittsburgh North Shore", address="574 West General Robinson Street",
       city="Pittsburgh", postal="15212", phone="412-321-2099",
       url="https://www.marriott.com/en-us/hotels/pitrn-residence-inn-pittsburgh-north-shore/overview/",
       url_shape="property", source="cultural_trust", ident="IDENTITY_CONFIRMED",
       lodging="LODGING_CONFIRMED"),
    _c(name="Sheraton Pittsburgh Hotel at Station Square",
       address="300 West Station Square Drive", city="Pittsburgh", postal="15219",
       phone="412-261-2000",
       url="https://www.marriott.com/en-us/hotels/pitps-sheraton-pittsburgh-hotel-at-station-square/overview/",
       url_shape="property", source="cultural_trust", ident="IDENTITY_CONFIRMED",
       lodging="LODGING_CONFIRMED"),
    _c(name="SpringHill Suites Pittsburgh North Shore", address="223 Federal Street",
       city="Pittsburgh", postal="15212", phone="412-323-9005",
       url="https://www.marriott.com/en-us/hotels/pitns-springhill-suites-pittsburgh-north-shore/overview/",
       url_shape="property", source="cultural_trust", ident="IDENTITY_CONFIRMED",
       lodging="LODGING_CONFIRMED"),
    _c(name="The Westin Pittsburgh", address="1000 Penn Avenue", city="Pittsburgh",
       postal="15222", phone="412-281-3700",
       url="https://www.marriott.com/en-us/hotels/pitwi-the-westin-pittsburgh/overview/",
       url_shape="property", source="cultural_trust", ident="IDENTITY_CONFIRMED",
       lodging="LODGING_CONFIRMED"),
    _c(name="Wyndham Grand Pittsburgh Downtown", address="600 Commonwealth Place",
       city="Pittsburgh", postal="15222", phone="412-391-4600",
       url="https://www.wyndhamhotels.com/wyndham-grand/pittsburgh-pennsylvania/wyndham-grand-pittsburgh-downtown/overview",
       url_shape="property", source="cultural_trust", ident="IDENTITY_CONFIRMED",
       lodging="LODGING_CONFIRMED"),
    _c(name="Kimpton Hotel Monaco Pittsburgh", address="620 William Penn Place",
       city="Pittsburgh", postal="15219", phone="412-471-1170",
       url="https://www.monaco-pittsburgh.com", url_shape="property",
       source="visit_pittsburgh", ident="IDENTITY_CONFIRMED", lodging="LODGING_CONFIRMED"),
    _c(name="The Industrialist Hotel Pittsburgh Autograph Collection",
       address="405 Wood Street", city="Pittsburgh", postal="15222", phone="412-430-4444",
       url="https://www.marriott.com/en-us/hotels/pitad-the-industrialist-hotel-pittsburgh-autograph-collection/overview/",
       url_shape="property", source="visit_pittsburgh", ident="IDENTITY_CONFIRMED",
       lodging="LODGING_CONFIRMED"),
    # --- PAACC airport chamber (in-boundary only) ---
    _c(name="Hilton Garden Inn Pittsburgh Airport South Robinson Mall",
       address="303 Park Manor Drive", city="Pittsburgh", postal="15205",
       phone="412-788-9500",
       url="https://www.hilton.com/en/hotels/pitrogi-hilton-garden-inn-pittsburgh-airport-south-robinson-mall/",
       url_shape="property", source="paacc", ident="IDENTITY_CONFIRMED",
       lodging="LODGING_CONFIRMED"),
    _c(name="Hilton Garden Inn Pittsburgh Airport", address="9600 University Boulevard",
       city="Moon Township", postal="15108", phone="412-205-5400",
       url="https://www.hilton.com/en/hotels/pitmtgi-hilton-garden-inn-pittsburgh-airport/",
       url_shape="property", source="paacc", ident="IDENTITY_CONFIRMED",
       lodging="LODGING_CONFIRMED"),
    _c(name="DoubleTree by Hilton Pittsburgh Airport", address="8402 University Boulevard",
       city="Moon Township", postal="15108", phone="412-329-1400",
       url="https://www.hilton.com/en/hotels/pitardt-doubletree-pittsburgh-airport/",
       url_shape="property", source="paacc", ident="IDENTITY_CONFIRMED",
       lodging="LODGING_CONFIRMED"),
    _c(name="SpringHill Suites Pittsburgh Airport", address="2500 Market Place Boulevard",
       city="Coraopolis", postal="15108", phone="412-729-2554",
       url="", url_shape="none", source="paacc", ident="IDENTITY_CONFIRMED",
       lodging="LODGING_CONFIRMED"),
    _c(name="Sonesta Simply Suites Pittsburgh Airport", address="100 Chauvet Drive",
       city="Pittsburgh", postal="15275", phone="412-787-7770",
       url="", url_shape="none", source="paacc", ident="IDENTITY_CONFIRMED",
       lodging="LODGING_CONFIRMED"),
    _c(name="Hyatt Place Pittsburgh Airport", address="6011 Campbells Run Road",
       city="Pittsburgh", postal="15205", phone="412-494-0202",
       url="https://www.hyatt.com/en-US/hotel/pennsylvania/hyatt-place-pittsburgh-airport/pitza",
       url_shape="property", source="paacc", ident="IDENTITY_CONFIRMED",
       lodging="LODGING_CONFIRMED"),
    _c(name="TownePlace Suites Pittsburgh Airport Robinson Township",
       address="1006 Sutherland Drive", city="Pittsburgh", postal="15205",
       phone="412-494-4000", url="", url_shape="none", source="paacc",
       ident="IDENTITY_CONFIRMED", lodging="LODGING_CONFIRMED"),
    _c(name="Fairfield Inn & Suites by Marriott Pittsburgh Robinson Township",
       address="1004 Sutherland Drive", city="Pittsburgh", postal="15205",
       phone="412-859-9070",
       url="https://www.marriott.com/hotels/travel/pitwf-fairfield-inn-and-suites-pittsburgh-airport-robinson-township/",
       url_shape="property", source="paacc", ident="IDENTITY_CONFIRMED",
       lodging="LODGING_CONFIRMED"),
    _c(name="Trellis North Fayette", address="1500 Park Lane", city="Pittsburgh",
       postal="15275", phone="412-787-3300", url="", url_shape="none",
       source="paacc", ident="IDENTITY_CONFIRMED", lodging="LODGING_CONFIRMED"),
    _c(name="Americas Best Value Inn Moon Township", address="8858 University Boulevard",
       city="Moon Township", postal="15108", phone="412-604-2378", url="",
       url_shape="none", source="paacc", ident="IDENTITY_CONFIRMED",
       lodging="LODGING_CONFIRMED"),
    _c(name="Hampton Inn Pittsburgh Green Tree", address="555 Trumbull Drive",
       city="Pittsburgh", postal="15205", phone="412-922-0100",
       url="https://www.hilton.com/en/hotels/pitgnhx-hampton-pittsburgh-greentree/",
       url_shape="property", source="paacc", ident="IDENTITY_CONFIRMED",
       lodging="LODGING_CONFIRMED"),
    _c(name="Pittsburgh Airport Marriott", address="777 Aten Road", city="Coraopolis",
       postal="15108", phone="412-788-8800",
       url="https://www.marriott.com/hotels/travel/pitmc-pittsburgh-airport-marriott/",
       url_shape="property", source="paacc", ident="IDENTITY_CONFIRMED",
       lodging="LODGING_CONFIRMED"),
    _c(name="Motel 6 Pittsburgh", address="211 Beecham Drive", city="Pittsburgh",
       postal="15205", phone="412-922-9400", url="", url_shape="none",
       source="paacc", ident="IDENTITY_CONFIRMED", lodging="LODGING_CONFIRMED"),
    _c(name="Courtyard by Marriott Pittsburgh Airport Settlers Ridge",
       address="5100 Campbells Run Road", city="Pittsburgh", postal="15205",
       phone="412-788-4404", url="", url_shape="none", source="paacc",
       ident="IDENTITY_CONFIRMED", lodging="LODGING_CONFIRMED"),
    _c(name="Sheraton Pittsburgh Airport Hotel", address="1160 Thorn Run Road",
       city="Moon Township", postal="15108", phone="412-262-2400",
       url="https://www.marriott.com/hotels/travel/pitsa-sheraton-pittsburgh-airport-hotel/",
       url_shape="property", source="paacc", ident="IDENTITY_CONFIRMED",
       lodging="LODGING_CONFIRMED"),
    _c(name="Courtyard by Marriott Pittsburgh Airport", address="450 Cherrington Parkway",
       city="Coraopolis", postal="15108", phone="412-264-5000", url="",
       url_shape="none", source="paacc", ident="IDENTITY_CONFIRMED",
       lodging="LODGING_CONFIRMED"),
    _c(name="DoubleTree by Hilton Green Tree", address="500 Mansfield Avenue",
       city="Pittsburgh", postal="15205", phone="412-922-8400",
       url="https://www.hilton.com/en/hotels/pitgtdt-doubletree-pittsburgh-green-tree/",
       url_shape="property", source="paacc", ident="IDENTITY_CONFIRMED",
       lodging="LODGING_CONFIRMED"),
    _c(name="Fairfield Inn & Suites Pittsburgh Neville Island",
       address="5850 Grand Avenue", city="Pittsburgh", postal="15225",
       phone="412-264-4722",
       url="https://www.marriott.com/hotels/travel/pitnv-fairfield-inn-and-suites-pittsburgh-neville-island/",
       url_shape="property", source="paacc", ident="IDENTITY_CONFIRMED",
       lodging="LODGING_CONFIRMED"),
    _c(name="Hampton Inn & Suites Pittsburgh Airport South Settlers Ridge",
       address="5000 Campbells Run Road", city="Pittsburgh", postal="15205",
       phone="412-788-4440",
       url="https://www.hilton.com/en/hotels/pitsrhx-hampton-suites-pittsburgh-airport-south-settlers-ridge/",
       url_shape="property", source="paacc", ident="IDENTITY_CONFIRMED",
       lodging="LODGING_CONFIRMED"),
    _c(name="Comfort Suites Pittsburgh Airport", address="750 Aten Road",
       city="Coraopolis", postal="15108", phone="412-494-5750", url="",
       url_shape="none", source="paacc", ident="IDENTITY_CONFIRMED",
       lodging="LODGING_CONFIRMED"),
    _c(name="Hyatt Regency Pittsburgh International Airport",
       address="1111 Airport Boulevard", city="Pittsburgh", postal="15231",
       phone="724-899-1234",
       url="https://www.hyatt.com/en-US/hotel/pennsylvania/hyatt-regency-pittsburgh-international-airport/pitap",
       url_shape="property", source="paacc", ident="IDENTITY_CONFIRMED",
       lodging="LODGING_CONFIRMED"),
    # --- East Liberty Chamber ---
    _c(name="Hotel Indigo Pittsburgh East Liberty", address="123 North Highland Avenue",
       city="Pittsburgh", postal="15206", phone="412-665-0555",
       url="https://www.ihg.com/hotelindigo/hotels/us/en/pittsburgh/pithb/hoteldetail",
       url_shape="property", source="east_liberty_chamber", ident="IDENTITY_CONFIRMED",
       lodging="LODGING_CONFIRMED"),
    _c(name="Hyatt House Pittsburgh Bloomfield Shadyside", address="5335 Baum Blvd",
       city="Pittsburgh", postal="15224", phone="412-621-9900",
       url="https://www.hyatt.com/en-US/hotel/pennsylvania/hyatt-house-pittsburgh-bloomfield-shadyside/pitxp",
       url_shape="property", source="east_liberty_chamber", ident="IDENTITY_CONFIRMED",
       lodging="LODGING_CONFIRMED"),
    _c(name="SpringHill Suites Pittsburgh Bakery Square",
       address="134 Bakery Square Boulevard", city="Pittsburgh", postal="15206",
       phone="412-362-8600",
       url="https://www.marriott.com/hotels/travel/pitel-springhill-suites-pittsburgh-bakery-square/",
       url_shape="property", source="east_liberty_chamber", ident="IDENTITY_CONFIRMED",
       lodging="LODGING_CONFIRMED"),
    _c(name="Courtyard by Marriott Pittsburgh Shadyside", address="5308 Liberty Avenue",
       city="Pittsburgh", postal="15224", phone="412-683-3113",
       url="https://www.marriott.com/hotels/travel/pitok-courtyard-pittsburgh-shadyside/",
       url_shape="property", source="east_liberty_chamber", ident="IDENTITY_CONFIRMED",
       lodging="LODGING_CONFIRMED"),
    _c(name="Hilton Garden Inn Pittsburgh University Place", address="3454 Forbes Avenue",
       city="Pittsburgh", postal="15213", phone="412-683-2040",
       url="https://www.hilton.com/en/hotels/pitucgi-hilton-garden-inn-pittsburgh-university-place/",
       url_shape="property", source="east_liberty_chamber", ident="IDENTITY_CONFIRMED",
       lodging="LODGING_CONFIRMED"),
    _c(name="Mansions on Fifth", address="5105 Fifth Avenue", city="Pittsburgh",
       postal="15232", phone="412-381-5105", url="https://mansionsonfifth.com",
       url_shape="property", source="east_liberty_chamber", ident="IDENTITY_CONFIRMED",
       lodging="LODGING_CONFIRMED"),
    _c(name="Shadyside Inn Suites", address="5405 Fifth Avenue", city="Pittsburgh",
       postal="15232", phone="412-441-4444", url="https://shadysideinn.com",
       url_shape="property", source="east_liberty_chamber", ident="IDENTITY_CONFIRMED",
       lodging="LODGING_CONFIRMED"),
    _c(name="Sunnyledge Boutique Hotel", address="5124 Fifth Avenue", city="Pittsburgh",
       postal="15232", phone="412-683-5014", url="https://sunnyledge.com",
       url_shape="property", source="east_liberty_chamber", ident="IDENTITY_CONFIRMED",
       lodging="LODGING_CONFIRMED"),
    _c(name="The Oaklander Hotel Autograph Collection", address="5130 Bigelow Blvd",
       city="Pittsburgh", postal="15213", phone="412-578-8500",
       url="https://theoaklanderhotel.com", url_shape="property",
       source="visit_pittsburgh", ident="IDENTITY_CONFIRMED", lodging="LODGING_CONFIRMED"),
    _c(name="Residence Inn Pittsburgh Oakland University Place",
       address="3341 Forbes Avenue", city="Pittsburgh", postal="15213", phone="",
       url="https://www.marriott.com/en-us/hotels/pitrd-residence-inn-pittsburgh-oakland-university-place/overview/",
       url_shape="property", source="visit_pittsburgh", ident="IDENTITY_CONFIRMED",
       lodging="LODGING_CONFIRMED"),
    _c(name="Hotel Indigo Pittsburgh University Oakland",
       address="329 Technology Drive", city="Pittsburgh", postal="15219",
       phone="",
       url="https://www.ihg.com/hotelindigo/hotels/us/en/pittsburgh/pitgh/hoteldetail",
       url_shape="property", source="gpha", ident="IDENTITY_PROVISIONAL",
       lodging="LODGING_CONFIRMED"),
    # --- GPHA members with recoverable geography (in-boundary) ---
    _c(name="AC Hotel by Marriott Pittsburgh Downtown", address="", city="Pittsburgh",
       postal="", phone="",
       url="https://www.marriott.com/hotels/travel/pitar-ac-hotel-pittsburgh-downtown/",
       url_shape="property", source="gpha", ident="IDENTITY_PROVISIONAL",
       lodging="LODGING_BY_NAME"),
    _c(name="Embassy Suites by Hilton Pittsburgh Downtown", address="",
       city="Pittsburgh", postal="15222", phone="",
       url="https://www.hilton.com/en/hotels/pitsmes-embassy-suites-pittsburgh-downtown/",
       url_shape="property", source="gpha", ident="IDENTITY_PROVISIONAL",
       lodging="LODGING_BY_NAME"),
    _c(name="Fairfield Inn & Suites Pittsburgh Downtown", address="",
       city="Pittsburgh", postal="15222", phone="", url="", url_shape="none",
       source="visit_pittsburgh", ident="IDENTITY_PROVISIONAL",
       lodging="LODGING_BY_NAME"),
    _c(name="Holiday Inn Express Pittsburgh North Shore", address="228 Federal Street",
       city="Pittsburgh", postal="15212", phone="412-323-0300",
       url="https://www.visitpittsburgh.com/directory/holiday-inn-express-suites-pittsburgh-north-shore/",
       url_shape="brand_index", source="visit_pittsburgh", ident="IDENTITY_CONFIRMED",
       lodging="LODGING_CONFIRMED"),
    _c(name="The Landing Hotel at Rivers Casino", address="", city="Pittsburgh",
       postal="15212", phone="", url="https://thelandinghotelpgh.com",
       url_shape="property", source="gpha", ident="IDENTITY_PROVISIONAL",
       lodging="LODGING_BY_NAME"),
    _c(name="The Priory Hotel", address="", city="Pittsburgh", postal="15212",
       phone="", url="https://thepriory.com", url_shape="property",
       source="gpha", ident="IDENTITY_PROVISIONAL", lodging="LODGING_BY_NAME"),
    _c(name="TRYP Hotel Pittsburgh", address="", city="Pittsburgh", postal="15222",
       phone="", url="https://www.tryppittsburgh.com", url_shape="property",
       source="gpha", ident="IDENTITY_PROVISIONAL", lodging="LODGING_BY_NAME"),
    _c(name="Holiday Inn Express South Side", address="", city="Pittsburgh",
       postal="15203", phone="",
       url="https://www.ihg.com/holidayinnexpress/hotels/us/en/pittsburgh/pitxs/hoteldetail",
       url_shape="property", source="gpha", ident="IDENTITY_PROVISIONAL",
       lodging="LODGING_BY_NAME"),
    _c(name="Hyatt House Pittsburgh South Side Works", address="", city="Pittsburgh",
       postal="15203", phone="",
       url="https://www.hyatt.com/en-US/hotel/pennsylvania/hyatt-house-pittsburgh-south-side/pitxs",
       url_shape="property", source="gpha", ident="IDENTITY_PROVISIONAL",
       lodging="LODGING_BY_NAME"),
    _c(name="SpringHill Suites Pittsburgh Southside Works", address="",
       city="Pittsburgh", postal="15203", phone="",
       url="https://www.marriott.com/hotels/travel/pitss-springhill-suites-pittsburgh-southside-works/",
       url_shape="property", source="gpha", ident="IDENTITY_PROVISIONAL",
       lodging="LODGING_BY_NAME"),
    _c(name="Crowne Plaza Pittsburgh South", address="", city="Pittsburgh",
       postal="", phone="",
       url="https://www.ihg.com/crowneplaza/hotels/us/en/pittsburgh/pitso/hoteldetail",
       url_shape="property", source="gpha", ident="IDENTITY_PROVISIONAL",
       lodging="LODGING_BY_NAME"),
    _c(name="Hampton Inn University Center", address="", city="Pittsburgh",
       postal="15213", phone="",
       url="https://www.hilton.com/en/hotels/pitokhx-hampton-pittsburgh-university-medical-center/",
       url_shape="property", source="gpha", ident="IDENTITY_PROVISIONAL",
       lodging="LODGING_BY_NAME"),
    _c(name="Residence Inn Pittsburgh University Center", address="",
       city="Pittsburgh", postal="15213", phone="",
       url="https://www.marriott.com/hotels/travel/pitro-residence-inn-pittsburgh-university-medical-center/",
       url_shape="property", source="gpha", ident="IDENTITY_PROVISIONAL",
       lodging="LODGING_BY_NAME"),
    _c(name="Courtyard by Marriott Pittsburgh University Center", address="",
       city="Pittsburgh", postal="15213", phone="",
       url="https://www.marriott.com/en-us/hotels/pityu-courtyard-pittsburgh-university-center/overview/",
       url_shape="property", source="gpha", ident="IDENTITY_PROVISIONAL",
       lodging="LODGING_BY_NAME"),
    _c(name="Holiday Inn Express & Suites Pittsburgh Airport", address="",
       city="Coraopolis", postal="15108", phone="",
       url="https://www.ihg.com/holidayinnexpress/hotels/us/en/pittsburgh/pitex/hoteldetail",
       url_shape="property", source="gpha", ident="IDENTITY_PROVISIONAL",
       lodging="LODGING_BY_NAME"),
    _c(name="Hampton Inn Pittsburgh Airport Moon", address="", city="Moon Township",
       postal="15108", phone="",
       url="https://www.hilton.com/en/hotels/pitaphx-hampton-pittsburgh-airport/",
       url_shape="property", source="gpha", ident="IDENTITY_PROVISIONAL",
       lodging="LODGING_BY_NAME"),
    _c(name="La Quinta Inn & Suites Pittsburgh Airport", address="",
       city="Moon Township", postal="15108", phone="",
       url="https://www.wyndhamhotels.com/laquinta/moon-township-pennsylvania/la-quinta-inn-pittsburgh-airport/overview",
       url_shape="property", source="gpha", ident="IDENTITY_PROVISIONAL",
       lodging="LODGING_BY_NAME"),
    _c(name="Residence Inn Pittsburgh Airport Coraopolis", address="",
       city="Coraopolis", postal="15108", phone="",
       url="https://www.marriott.com/hotels/travel/pitra-residence-inn-pittsburgh-airport/",
       url_shape="property", source="gpha", ident="IDENTITY_PROVISIONAL",
       lodging="LODGING_BY_NAME"),
    _c(name="Homewood Suites Robinson Area", address="", city="Pittsburgh",
       postal="15205", phone="",
       url="https://www.hilton.com/en/hotels/pitrthw-homewood-suites-pittsburgh-airport-robinson-mall-area-pa/",
       url_shape="property", source="gpha", ident="IDENTITY_PROVISIONAL",
       lodging="LODGING_BY_NAME"),
    _c(name="Hampton Inn Pittsburgh Monroeville", address="", city="Monroeville",
       postal="15146", phone="",
       url="https://www.hilton.com/en/hotels/pitmvhx-hampton-pittsburgh-monroeville/",
       url_shape="property", source="gpha", ident="IDENTITY_PROVISIONAL",
       lodging="LODGING_BY_NAME"),
    _c(name="DoubleTree by Hilton Pittsburgh Monroeville", address="",
       city="Monroeville", postal="15146", phone="",
       url="https://www.hilton.com/en/hotels/pitmrdt-doubletree-pittsburgh-monroeville-convention-center/",
       url_shape="property", source="gpha", ident="IDENTITY_PROVISIONAL",
       lodging="LODGING_BY_NAME"),
    _c(name="Courtyard by Marriott Pittsburgh Monroeville", address="",
       city="Monroeville", postal="15146", phone="", url="", url_shape="none",
       source="gpha", ident="IDENTITY_PROVISIONAL", lodging="LODGING_BY_NAME"),
    _c(name="Residence Inn Pittsburgh Monroeville", address="", city="Wilkins Township",
       postal="15146", phone="",
       url="https://www.marriott.com/hotels/travel/pitpm-residence-inn-pittsburgh-monroeville-wilkins-township/",
       url_shape="property", source="gpha", ident="IDENTITY_PROVISIONAL",
       lodging="LODGING_BY_NAME"),
    _c(name="SpringHill Suites Pittsburgh Monroeville", address="",
       city="Monroeville", postal="15146", phone="",
       url="https://www.marriott.com/hotels/travel/pitmv-springhill-suites-pittsburgh-monroeville/",
       url_shape="property", source="gpha", ident="IDENTITY_PROVISIONAL",
       lodging="LODGING_BY_NAME"),
    _c(name="Hampton Inn & Suites Pittsburgh Waterfront", address="",
       city="West Homestead", postal="15120", phone="",
       url="https://www.hilton.com/en/hotels/pitwhhx-hampton-suites-pittsburgh-waterfront-west-homestead/",
       url_shape="property", source="gpha", ident="IDENTITY_PROVISIONAL",
       lodging="LODGING_BY_NAME"),
    _c(name="Courtyard by Marriott Pittsburgh Waterfront", address="",
       city="West Homestead", postal="15120", phone="", url="", url_shape="none",
       source="gpha", ident="IDENTITY_PROVISIONAL", lodging="LODGING_BY_NAME"),
    _c(name="Hampton Inn Pittsburgh Wexford Sewickley", address="", city="Wexford",
       postal="15090", phone="",
       url="https://www.hilton.com/en/hotels/pitwshx-hampton-pittsburgh-wexford-sewickley/",
       url_shape="property", source="gpha", ident="IDENTITY_PROVISIONAL",
       lodging="LODGING_BY_NAME"),
    _c(name="Courtyard by Marriott Cranberry Woods", address="",
       city="Cranberry Township", postal="16066", phone="", url="",
       url_shape="none", source="gpha", ident="IDENTITY_PROVISIONAL",
       lodging="LODGING_BY_NAME"),
    _c(name="DoubleTree by Hilton Pittsburgh Cranberry", address="",
       city="Cranberry Township", postal="16066", phone="",
       url="https://www.hilton.com/en/hotels/pitmadt-doubletree-pittsburgh-cranberry/",
       url_shape="property", source="gpha", ident="IDENTITY_PROVISIONAL",
       lodging="LODGING_BY_NAME"),
    _c(name="Holiday Inn Express Pittsburgh Cranberry Township", address="",
       city="Cranberry Township", postal="16066", phone="",
       url="https://www.ihg.com/holidayinnexpress/hotels/us/en/cranberry/fklpa/hoteldetail",
       url_shape="property", source="gpha", ident="IDENTITY_PROVISIONAL",
       lodging="LODGING_BY_NAME"),
    _c(name="Home2 Suites Pittsburgh Cranberry Township", address="",
       city="Cranberry Township", postal="16066", phone="",
       url="https://www.hilton.com/en/hotels/pitltht-home2-suites-pittsburgh-cranberry-pa/",
       url_shape="property", source="gpha", ident="IDENTITY_PROVISIONAL",
       lodging="LODGING_BY_NAME"),
    _c(name="Hyatt Place Pittsburgh Cranberry", address="",
       city="Cranberry Township", postal="16066", phone="",
       url="https://www.hyatt.com/en-US/hotel/pennsylvania/hyatt-place-pittsburgh-cranberry/pitzc",
       url_shape="property", source="gpha", ident="IDENTITY_PROVISIONAL",
       lodging="LODGING_BY_NAME"),
    _c(name="Marriott Pittsburgh North Cranberry Woods", address="",
       city="Cranberry Township", postal="16066", phone="",
       url="https://www.marriott.com/hotels/travel/pitno-pittsburgh-marriott-north/",
       url_shape="property", source="gpha", ident="IDENTITY_PROVISIONAL",
       lodging="LODGING_BY_NAME"),
    _c(name="Residence Inn Pittsburgh Cranberry Township", address="",
       city="Cranberry Township", postal="16066", phone="",
       url="https://www.marriott.com/hotels/travel/pitcr-residence-inn-pittsburgh-cranberry-township/",
       url_shape="property", source="gpha", ident="IDENTITY_PROVISIONAL",
       lodging="LODGING_BY_NAME"),
    _c(name="Hampton Inn Pittsburgh Bridgeville", address="", city="Bridgeville",
       postal="15017", phone="",
       url="https://www.hilton.com/en/hotels/pitbvhx-hampton-pittsburgh-bridgeville/",
       url_shape="property", source="gpha", ident="IDENTITY_PROVISIONAL",
       lodging="LODGING_BY_NAME"),
    _c(name="SpringHill Suites Pittsburgh Mt Lebanon", address="",
       city="Mount Lebanon", postal="15228", phone="",
       url="https://www.marriott.com/hotels/travel/pitle-springhill-suites-pittsburgh-mt-lebanon/",
       url_shape="property", source="gpha", ident="IDENTITY_PROVISIONAL",
       lodging="LODGING_BY_NAME"),
    _c(name="Hampton Inn Pittsburgh Harmarville", address="", city="Cheswick",
       postal="15024", phone="",
       url="https://www.hilton.com/en/hotels/pithahx-hampton-suites-pittsburgh-harmarville/",
       url_shape="property", source="gpha", ident="IDENTITY_PROVISIONAL",
       lodging="LODGING_BY_NAME"),
    _c(name="SpringHill Suites Pittsburgh Mills", address="", city="Tarentum",
       postal="15084", phone="",
       url="https://www.marriott.com/hotels/travel/pitml-springhill-suites-pittsburgh-mills/",
       url_shape="property", source="gpha", ident="IDENTITY_PROVISIONAL",
       lodging="LODGING_BY_NAME"),
    # --- Category excluded (stay in census as NOT_LODGING) ---
    _c(name="Inn on Negley", address="703 South Negley Avenue", city="Pittsburgh",
       postal="15232", phone="412-661-0631", url="https://www.innonnegley.com",
       url_shape="property", source="east_liberty_chamber", ident="IDENTITY_CONFIRMED",
       lodging="NOT_LODGING", disposition="canonical"),
    _c(name="Choderwood", address="7665 Lock Way West", city="Pittsburgh",
       postal="15206", phone="412-441-4975", url="", url_shape="none",
       source="east_liberty_chamber", ident="IDENTITY_CONFIRMED",
       lodging="NOT_LODGING"),
    _c(name="The Maverick by Kasa", address="120 South Whitfield Street",
       city="Pittsburgh", postal="15206", phone="650-451-3444",
       url="https://kasa.com/properties/kasa-the-maverick-pittsburgh",
       url_shape="property", source="east_liberty_chamber", ident="IDENTITY_CONFIRMED",
       lodging="NOT_LODGING"),
    # --- Closed / converted (census review, not exclusion registry) ---
    _c(name="Ace Hotel Pittsburgh", address="120 South Whitfield Street",
       city="Pittsburgh", postal="15206", phone="412-361-3300",
       url="https://www.acehotel.com/pittsburgh/", url_shape="property",
       source="gpha", ident="IDENTITY_CONFIRMED", lodging="NEEDS_REVIEW",
       notes="East Liberty Chamber now lists The Maverick by Kasa at this address; Ace is reported closed."),
    # --- Duplicate of Atterbury ---
    _c(name="Renaissance Pittsburgh Hotel", address="107 Sixth Street",
       city="Pittsburgh", postal="15222", phone="412-562-1200",
       url="https://renaissance-hotels.marriott.com/renaissance-pittsburgh-hotel",
       url_shape="property", source="gpha", ident="IDENTITY_CONFIRMED",
       lodging="LODGING_CONFIRMED", disposition="duplicate",
       duplicate_of="The Atterbury Hotel Autograph Collection"),
    # --- Boundary excluded (ledger only, not in census) ---
    _c(name="My Place Hotel Beaver Valley", address="138 Stone Quarry Road",
       city="Monaca", postal="15061", phone="724-773-0500", url="",
       url_shape="none", source="paacc", ident="IDENTITY_CONFIRMED",
       lodging="LODGING_CONFIRMED", disposition="boundary_excluded",
       notes="Beaver County / Monaca. Outside approved visitor product."),
    _c(name="Hilton Garden Inn Pittsburgh Area Beaver Valley",
       address="2000 Wagner Road Ext. South", city="Monaca", postal="15061",
       phone="724-888-5952", url="", url_shape="none", source="paacc",
       ident="IDENTITY_CONFIRMED", lodging="LODGING_CONFIRMED",
       disposition="boundary_excluded", notes="Beaver County / Monaca."),
    _c(name="Hampton Inn Beaver Valley", address="202 Fairview Drive",
       city="Monaca", postal="15061", phone="724-774-5580", url="",
       url_shape="none", source="paacc", ident="IDENTITY_CONFIRMED",
       lodging="LODGING_CONFIRMED", disposition="boundary_excluded",
       notes="Beaver County / Monaca."),
    _c(name="Home2 Suites by Hilton Pittsburgh Area Beaver Valley",
       address="1000 Wagner Road Extension South", city="Monaca", postal="15061",
       phone="724-770-1101", url="", url_shape="none", source="paacc",
       ident="IDENTITY_CONFIRMED", lodging="LODGING_CONFIRMED",
       disposition="boundary_excluded", notes="Beaver County / Monaca."),
    _c(name="Hyatt Place Hollywood Casino Racetrack Pittsburgh South",
       address="212 Racetrack Road", city="Washington", postal="15301",
       phone="724-222-7777", url="", url_shape="none", source="paacc",
       ident="IDENTITY_CONFIRMED", lodging="LODGING_CONFIRMED",
       disposition="boundary_excluded", notes="Washington PA city / Meadows."),
    _c(name="Cobblestone Inn & Suites Ambridge", address="", city="Ambridge",
       postal="", phone="", url="https://www.staycobblestone.com/pa/ambridge/",
       url_shape="property", source="gpha", ident="IDENTITY_PROVISIONAL",
       lodging="LODGING_BY_NAME", disposition="boundary_excluded",
       notes="Beaver County / Ambridge."),
    _c(name="Courtyard by Marriott Greensburg", address="", city="Greensburg",
       postal="", phone="", url="", url_shape="none", source="gpha",
       ident="IDENTITY_PROVISIONAL", lodging="LODGING_BY_NAME",
       disposition="boundary_excluded", notes="Westmoreland county seat."),
    _c(name="Courtyard by Marriott Washington Meadowlands", address="",
       city="Washington", postal="15301", phone="", url="", url_shape="none",
       source="gpha", ident="IDENTITY_PROVISIONAL", lodging="LODGING_BY_NAME",
       disposition="boundary_excluded", notes="Washington PA / Meadow Lands."),
    _c(name="DoubleTree Pittsburgh Meadow Lands", address="", city="Washington",
       postal="15301", phone="",
       url="https://www.hilton.com/en/hotels/pitmpdt-doubletree-pittsburgh-meadow-lands/",
       url_shape="property", source="gpha", ident="IDENTITY_PROVISIONAL",
       lodging="LODGING_BY_NAME", disposition="boundary_excluded",
       notes="Washington PA / Meadow Lands."),
    _c(name="Hilton Garden Inn Pittsburgh Southpointe", address="",
       city="Canonsburg", postal="", phone="",
       url="https://www.hilton.com/en/hotels/pitspgi-hilton-garden-inn-pittsburgh-southpointe/",
       url_shape="property", source="gpha", ident="IDENTITY_PROVISIONAL",
       lodging="LODGING_BY_NAME", disposition="boundary_excluded",
       notes="Washington County / Southpointe."),
    _c(name="Homewood Suites Pittsburgh Southpointe", address="",
       city="Canonsburg", postal="", phone="",
       url="https://www.hilton.com/en/hotels/pitsbhw-homewood-suites-pittsburgh-southpointe/",
       url_shape="property", source="gpha", ident="IDENTITY_PROVISIONAL",
       lodging="LODGING_BY_NAME", disposition="boundary_excluded",
       notes="Washington County / Southpointe."),
    _c(name="Nemacolin Woodlands", address="", city="Farmington", postal="",
       phone="", url="https://www.nemacolin.com", url_shape="property",
       source="gpha", ident="IDENTITY_PROVISIONAL", lodging="LODGING_BY_NAME",
       disposition="boundary_excluded", notes="Laurel Highlands resort, not Pittsburgh visitor overnight core."),
    _c(name="Seven Springs Mountain Resort", address="", city="Champion",
       postal="", phone="", url="https://www.7springs.com", url_shape="property",
       source="gpha", ident="IDENTITY_PROVISIONAL", lodging="LODGING_BY_NAME",
       disposition="boundary_excluded", notes="Somerset County resort."),
    _c(name="SpringHill Suites Pittsburgh Latrobe", address="", city="Latrobe",
       postal="", phone="",
       url="https://www.marriott.com/hotels/travel/pitlt-springhill-suites-pittsburgh-latrobe/",
       url_shape="property", source="gpha", ident="IDENTITY_PROVISIONAL",
       lodging="LODGING_BY_NAME", disposition="boundary_excluded",
       notes="Westmoreland / Latrobe."),
    _c(name="SpringHill Suites Pittsburgh Washington", address="",
       city="Washington", postal="15301", phone="",
       url="https://www.marriott.com/hotels/travel/pitws-springhill-suites-pittsburgh-washington/",
       url_shape="property", source="gpha", ident="IDENTITY_PROVISIONAL",
       lodging="LODGING_BY_NAME", disposition="boundary_excluded",
       notes="Washington PA."),
    _c(name="Drury Inn & Suites Pittsburgh", address="", city="Pittsburgh",
       postal="", phone="",
       url="https://www.druryhotels.com/locations/pittsburgh-pa/drury-plaza-hotel-pittsburgh-downtown",
       url_shape="brand_index", source="gpha", ident="IDENTITY_UNRESOLVED",
       lodging="NEEDS_REVIEW", disposition="duplicate",
       duplicate_of="Drury Plaza Hotel Pittsburgh Downtown",
       notes="GPHA lists a second Drury name that resolves to the same downtown Plaza URL. Held as a duplicate of Drury Plaza until a distinct street address is found."),
]


SOURCES = [
    {"source_id": "visit_pittsburgh", "name": "VisitPITTSBURGH",
     "organization": "VisitPITTSBURGH / Pittsburgh Convention & Visitors Bureau",
     "source_type": "CVB", "family": "CVB",
     "url": "https://www.visitpittsburgh.com/hotels-resorts/",
     "geographic_coverage": "Pittsburgh visitor market",
     "data_categories": ["lodging", "dining", "parks"],
     "access_date": AS_OF, "status": "authority_for_identity_when_directory_page_states_address",
     "limitations": "Main hotel index is JavaScript-rendered and not readable as static HTML. Individual directory pages and the dog-friendly hotels blog were readable.",
     "automated_access": "static_html_partial"},
    {"source_id": "cultural_trust", "name": "Pittsburgh Cultural Trust hotel list",
     "organization": "Pittsburgh Cultural Trust", "source_type": "destination_partner",
     "family": "CVB", "url": "https://trustarts.org/pct_home/visit/hotels",
     "geographic_coverage": "Downtown, North Shore, Station Square, Strip",
     "data_categories": ["lodging"], "access_date": AS_OF,
     "status": "authority_for_identity",
     "limitations": "Renaissance name is stale; VisitPITTSBURGH now lists 107 Sixth Street as The Atterbury Hotel.",
     "automated_access": "static_html"},
    {"source_id": "paacc", "name": "Pittsburgh Airport Area Chamber hotels/motels",
     "organization": "Pittsburgh Airport Area Chamber of Commerce",
     "source_type": "destination_partner", "family": "DIRECTORY",
     "url": "https://www.paacc.com/list/category/hotels-motels-38",
     "geographic_coverage": "Airport, Robinson, Green Tree, plus Beaver Valley and Washington spillover",
     "data_categories": ["lodging"], "access_date": AS_OF,
     "status": "authority_for_identity_inside_boundary",
     "limitations": "Includes Monaca and Washington PA hotels that this market excludes.",
     "automated_access": "static_html"},
    {"source_id": "east_liberty_chamber", "name": "East Liberty Chamber Stay directory",
     "organization": "East Liberty Chamber of Commerce",
     "source_type": "destination_partner", "family": "DIRECTORY",
     "url": "https://www.eastlibertychamber.org/Stay",
     "geographic_coverage": "East Liberty, Shadyside, Oakland edge",
     "data_categories": ["lodging", "bnb", "short_term"], "access_date": AS_OF,
     "status": "authority_for_identity",
     "limitations": "Lists B&B and STR inventory that is not current hotel category.",
     "automated_access": "static_html"},
    {"source_id": "gpha", "name": "Greater Pittsburgh Hotel Association current members",
     "organization": "Greater Pittsburgh Hotel Association",
     "source_type": "industry_association", "family": "DIRECTORY",
     "url": "https://www.pittsburgh-hotels.org/current-members",
     "geographic_coverage": "Greater Pittsburgh lodging association, including outer-ring and out-of-market resorts",
     "data_categories": ["lodging"], "access_date": AS_OF,
     "status": "discovery_and_membership_evidence",
     "limitations": "Many member links are wrong (several Courtyards point at the downtown Courtyard URL). Names without independently sourced street addresses stay IDENTITY_PROVISIONAL. Includes vendors that are not hotels.",
     "automated_access": "static_html"},
    {"source_id": "city_parks", "name": "City of Pittsburgh Our Parks",
     "organization": "City of Pittsburgh", "source_type": "municipal",
     "family": "REGISTRY", "url": "https://www.pittsburghpa.gov/Recreation-Events/Parks-Greenways/Our-Parks",
     "geographic_coverage": "City of Pittsburgh parks",
     "data_categories": ["dog_parks", "parks"], "access_date": AS_OF,
     "status": "authority_for_utilities",
     "limitations": "Page lists park names and neighborhoods; leash rules are not fully specified on every row.",
     "automated_access": "static_html"},
    {"source_id": "parks_conservancy", "name": "Pittsburgh Parks Conservancy Riverview Park",
     "organization": "Pittsburgh Parks Conservancy", "source_type": "destination_partner",
     "family": "DIRECTORY",
     "url": "https://pittsburghparks.org/explore-your-parks/regional-parks/riverview-park/",
     "geographic_coverage": "City regional parks",
     "data_categories": ["dog_parks", "trails"], "access_date": AS_OF,
     "status": "authority_for_utilities",
     "limitations": "Park pages confirm off-leash dog park presence; hours are office hours, not park hours.",
     "automated_access": "static_html"},
    {"source_id": "avets", "name": "Avets Specialty & Emergency Trauma Center",
     "organization": "Avets", "source_type": "official_business",
     "family": "CHAIN", "url": "https://www.avets.com/contact-us/",
     "geographic_coverage": "Monroeville",
     "data_categories": ["emergency_veterinary"], "access_date": AS_OF,
     "status": "authority_for_24_7",
     "limitations": "24/7 claim is taken only from Avets' own contact page.",
     "automated_access": "static_html"},
    {"source_id": "veg_pittsburgh", "name": "VEG ER for Pets Pittsburgh",
     "organization": "VEG ER for Pets", "source_type": "official_business",
     "family": "CHAIN",
     "url": "https://www.veg.com/locations/pennsylvania/pittsburgh",
     "geographic_coverage": "East Liberty / Penn Avenue",
     "data_categories": ["emergency_veterinary"], "access_date": AS_OF,
     "status": "authority_for_24_7",
     "limitations": "24/7 claim is taken only from VEG's own location page.",
     "automated_access": "static_html"},
]


UTILITIES = [
    {"utility_id": "west-park-dog-park", "name": "West Park Dog Park",
     "category": "off_leash_dog_park", "address": "Allegheny Commons West",
     "municipality": "Pittsburgh", "corridor": "pittsburgh-pa__north-shore",
     "official_url": "https://www.pittsburghpa.gov/Recreation-Events/Parks-Greenways/Our-Parks",
     "pet_access": "off-leash area listed by the City of Pittsburgh",
     "leash": "off-leash in designated area", "fenced": "",
     "evidence_url": "https://www.pittsburghpa.gov/Recreation-Events/Parks-Greenways/Our-Parks",
     "evidence_quote": "West Park Dog Park",
     "verified_at": AS_OF, "verification_status": "IDENTITY_CONFIRMED",
     "needs_reverification": False, "as_of": AS_OF, "next_action": ""},
    {"utility_id": "downtown-dog-park-9th-street", "name": "Downtown Dog Park at 9th Street Bridge",
     "category": "off_leash_dog_park", "address": "10th Street Bypass & Fort Duquesne Boulevard",
     "municipality": "Pittsburgh", "corridor": "pittsburgh-pa__downtown",
     "official_url": "https://www.pittsburghpa.gov/Recreation-Events/Parks-Greenways/Our-Parks",
     "pet_access": "city-listed downtown dog park",
     "leash": "", "fenced": "",
     "evidence_url": "https://www.pittsburghpa.gov/Recreation-Events/Parks-Greenways/Our-Parks",
     "evidence_quote": "Downtown Dog Park at 9th Street Bridge",
     "verified_at": AS_OF, "verification_status": "IDENTITY_CONFIRMED",
     "needs_reverification": False, "as_of": AS_OF, "next_action": ""},
    {"utility_id": "olympia-dog-park", "name": "Olympia Dog Park",
     "category": "off_leash_dog_park", "address": "Virginia & Olympia Streets",
     "municipality": "Pittsburgh", "corridor": "pittsburgh-pa__south-side",
     "official_url": "https://www.pittsburghpa.gov/Recreation-Events/Parks-Greenways/Our-Parks",
     "pet_access": "city-listed dog park at Olympia Park / Emerald View",
     "leash": "", "fenced": "",
     "evidence_url": "https://www.pittsburghpa.gov/Recreation-Events/Parks-Greenways/Our-Parks",
     "evidence_quote": "Olympia Dog Park",
     "verified_at": AS_OF, "verification_status": "IDENTITY_CONFIRMED",
     "needs_reverification": False, "as_of": AS_OF, "next_action": ""},
    {"utility_id": "south-side-dog-park", "name": "South Side Dog Park",
     "category": "off_leash_dog_park",
     "address": "South Side Riverfront Park, Monongahela River at South 18th Street",
     "municipality": "Pittsburgh", "corridor": "pittsburgh-pa__south-side",
     "official_url": "https://www.pittsburghpa.gov/Recreation-Events/Parks-Greenways/Our-Parks",
     "pet_access": "city-listed riverfront dog park",
     "leash": "", "fenced": "",
     "evidence_url": "https://www.pittsburghpa.gov/Recreation-Events/Parks-Greenways/Our-Parks",
     "evidence_quote": "South Side Dog Park",
     "verified_at": AS_OF, "verification_status": "IDENTITY_CONFIRMED",
     "needs_reverification": False, "as_of": AS_OF, "next_action": ""},
    {"utility_id": "riverview-park-dog-park", "name": "Riverview Park Off-Leash Dog Park",
     "category": "off_leash_dog_park", "address": "1 Riverview Avenue",
     "municipality": "Pittsburgh", "corridor": "pittsburgh-pa__north-shore",
     "official_url": "https://pittsburghparks.org/explore-your-parks/regional-parks/riverview-park/",
     "pet_access": "off-leash dog park listed by Pittsburgh Parks Conservancy",
     "leash": "off-leash in designated area", "fenced": "true",
     "evidence_url": "https://pittsburghparks.org/explore-your-parks/regional-parks/riverview-park/",
     "evidence_quote": "Off Leash Dog Park",
     "verified_at": AS_OF, "verification_status": "IDENTITY_CONFIRMED",
     "needs_reverification": False, "as_of": AS_OF, "next_action": ""},
    {"utility_id": "bernard-dog-run", "name": "Bernard Dog Run",
     "category": "off_leash_dog_park",
     "address": "Three Rivers Heritage Trail at 40th Street, Lawrenceville",
     "municipality": "Pittsburgh", "corridor": "pittsburgh-pa__strip-lawrenceville",
     "official_url": "https://pittsburghpa.my.site.com/pittsburg311Knowledge/s/article/Does-the-City-have-any-dog-parks",
     "pet_access": "city 311 knowledge article lists Bernard Dog Run, Lawrenceville among year-round off-leash areas",
     "leash": "off-leash", "fenced": "",
     "evidence_url": "https://pittsburghpa.my.site.com/pittsburg311Knowledge/s/article/Does-the-City-have-any-dog-parks",
     "evidence_quote": "Bernard Dog Run, Lawrenceville",
     "verified_at": AS_OF, "verification_status": "IDENTITY_CONFIRMED",
     "needs_reverification": False, "as_of": AS_OF, "next_action": ""},
    {"utility_id": "three-rivers-heritage-trail", "name": "Three Rivers Heritage Trail",
     "category": "greenway_riverfront", "address": "Pittsburgh riverfronts",
     "municipality": "Pittsburgh", "corridor": "pittsburgh-pa__downtown",
     "official_url": "https://www.pittsburghpa.gov/Recreation-Events/Parks-Greenways/Our-Parks",
     "pet_access": "riverfront walking route referenced by the City parks inventory",
     "leash": "", "fenced": "false",
     "evidence_url": "https://www.pittsburghpa.gov/Recreation-Events/Parks-Greenways/Our-Parks",
     "evidence_quote": "South Side Riverfront Park",
     "verified_at": AS_OF, "verification_status": "IDENTITY_CONFIRMED",
     "needs_reverification": False, "as_of": AS_OF,
     "next_action": "Record an official leash rule from a trail-managing agency page."},
    {"utility_id": "avets-monroeville", "name": "Avets Specialty & Emergency Trauma Center",
     "category": "emergency_veterinary_24_7", "address": "2674 Monroeville Blvd",
     "municipality": "Monroeville", "corridor": "pittsburgh-pa__monroeville",
     "official_url": "https://www.avets.com/contact-us/",
     "phone": "412-373-4200",
     "pet_access": "24/7 emergency veterinary",
     "hours": "24/7/365",
     "is_24_7": True,
     "evidence_url": "https://www.avets.com/contact-us/",
     "evidence_quote": "We're here when you need us – 24 hours a day, 7 days a week. 2674 Monroeville Blvd Monroeville, PA 15146 · 412.373.4200. 24/7/365.",
     "verified_at": AS_OF, "verification_status": "IDENTITY_CONFIRMED",
     "needs_reverification": False, "as_of": AS_OF, "next_action": ""},
    {"utility_id": "big-dog-coffee", "name": "Big Dog Coffee",
     "category": "dog_friendly_dining", "address": "South Side",
     "municipality": "Pittsburgh", "corridor": "pittsburgh-pa__south-side",
     "official_url": "http://www.bigdogcoffeeshop.com",
     "pet_access": "VisitPITTSBURGH blog states outdoor patio seating is pet-friendly",
     "patio_only": True,
     "evidence_url": "https://www.visitpittsburgh.com/blog/dog-friendly-restaurants-and-bars-in-pittsburgh/",
     "evidence_quote": "It's super pet-friendly and you are welcome to enjoy your coffee on their outside patio with your dog by your side.",
     "verified_at": AS_OF, "verification_status": "TOURISM_BLOG_ONLY",
     "needs_reverification": False, "as_of": AS_OF,
     "next_action": "Confirm patio pet access on the cafe's own official page before treating this as first-party."},
    {"utility_id": "federal-galley", "name": "Federal Galley",
     "category": "dog_friendly_dining", "address": "North Side",
     "municipality": "Pittsburgh", "corridor": "pittsburgh-pa__north-shore",
     "official_url": "http://www.federalgalley.org",
     "pet_access": "VisitPITTSBURGH blog states the outdoor beer garden offers dog-friendly seating",
     "patio_only": True,
     "evidence_url": "https://www.visitpittsburgh.com/blog/dog-friendly-restaurants-and-bars-in-pittsburgh/",
     "evidence_quote": "A new outdoor beer garden offers dog-friendly seating outside.",
     "verified_at": AS_OF, "verification_status": "TOURISM_BLOG_ONLY",
     "needs_reverification": False, "as_of": AS_OF,
     "next_action": "Confirm patio pet access on Federal Galley's own official page."},
    {"utility_id": "grist-house-craft-brewery", "name": "Grist House Craft Brewery",
     "category": "dog_friendly_brewery", "address": "",
     "municipality": "Pittsburgh", "corridor": "pittsburgh-pa__strip-lawrenceville",
     "official_url": "http://gristhouse.com/",
     "pet_access": "VisitPITTSBURGH blog states the brewery is completely dog friendly",
     "patio_only": False,
     "evidence_url": "https://www.visitpittsburgh.com/blog/dog-friendly-restaurants-and-bars-in-pittsburgh/",
     "evidence_quote": "It's a family owned and operated brewery with an all-seasons deck and spacious outdoor beer garden. The best part? It's completely dog friendly!",
     "verified_at": AS_OF, "verification_status": "TOURISM_BLOG_ONLY",
     "needs_reverification": False, "as_of": AS_OF,
     "next_action": "Confirm dog access on Grist House's own official page."},
    {"utility_id": "veg-pittsburgh", "name": "VEG ER for Pets Pittsburgh",
     "category": "emergency_veterinary_24_7", "address": "6244 Penn Avenue",
     "municipality": "Pittsburgh", "corridor": "pittsburgh-pa__east-end",
     "official_url": "https://www.veg.com/locations/pennsylvania/pittsburgh",
     "phone": "412-690-0511",
     "pet_access": "24/7 emergency veterinary",
     "hours": "OPEN 24/7",
     "is_24_7": True,
     "evidence_url": "https://www.veg.com/locations/pennsylvania/pittsburgh",
     "evidence_quote": "VEG Pittsburgh offers 24 hour Emergency Vet and urgent pet care. OPEN 24/7. 6244 Penn Avenue Pittsburgh, PA 15206",
     "verified_at": AS_OF, "verification_status": "IDENTITY_CONFIRMED",
     "needs_reverification": False, "as_of": AS_OF, "next_action": ""},
]


def _dump(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, ensure_ascii=False) + "\n",
                    encoding="utf-8")


def _street_identity(address: str, postal: str) -> str:
    street = normalize_name(address)
    return "%s|%s" % (street, (postal or "")[:5]) if street else ""


#: Founder-decision application date (PTF-PITTSBURGH-PASS1-DECISION-APPLICATION-001).
DECISION_DATE = "2026-08-16"
APPLICATION_WORK_ORDER = "PTF-PITTSBURGH-PASS1-DECISION-APPLICATION-001"
FACTS_PATH = PACKAGE / ("hotel_policy_facts_%s.json" % MARKET)
EXCLUSIONS_PATH = PACKAGE / "hotel_exclusions.json"

_AUTHORITY_CACHE = None


def _decided_states():
    """identity_key -> terminal state, read from committed policy authority.

    The facts package holds published records; the exclusion REGISTRY (never a
    census annotation) is the no-pets authority. Both are optional: before the
    Pass 1 application landed, neither said anything about Pittsburgh and every
    row stayed with its blocker state.
    """
    global _AUTHORITY_CACHE
    if _AUTHORITY_CACHE is not None:
        return _AUTHORITY_CACHE
    decided = {}
    if FACTS_PATH.is_file():
        doc = json.loads(FACTS_PATH.read_text(encoding="utf-8-sig"))
        for hotel in doc.get("hotels", []):
            if hotel.get("market_id") == MARKET and hotel.get("approval"):
                decided[hotel["identity_key"]] = enums.PUBLISHED_PET_FRIENDLY
    if EXCLUSIONS_PATH.is_file():
        doc = json.loads(EXCLUSIONS_PATH.read_text(encoding="utf-8-sig"))
        for entry in doc.get("exclusions", []):
            if entry.get("market_id") == MARKET \
                    and entry.get("exclusion_state") == "VERIFIED_NO_PETS":
                decided[entry["normalized_name"]] = enums.VERIFIED_NO_PETS
    _AUTHORITY_CACHE = decided
    return decided


def _blocker_for(row: dict) -> str:
    decided = _decided_states()
    state = decided.get(row["identity_key"]) \
        or decided.get(row.get("normalized_name") or "")
    if state:
        return state
    if row["lodging_state"] == enums.NOT_LODGING:
        return enums.OUT_OF_CURRENT_CATEGORY
    if row.get("disposition") == "closed" or row["lodging_state"] == enums.LODGING_NEEDS_REVIEW:
        return enums.AWAITING_CENSUS_REVIEW
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
            "state": "PA",
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
            row["assignment_basis"] = enums.TIER_UNASSIGNED if hasattr(enums, "TIER_UNASSIGNED") else "unassigned"
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
        ("note", "fea73de revalidation of the 2d885d1 PTF-PITTSBURGH-MARKET-BUILD-001 factory. Source work order %s. policy_state is the legacy-frozen POLICY_NOT_VERIFIED on every row; the final partition and the policy/exclusion authorities are the publication truth (Pass 1 founder decisions applied by %s). Closed and out-of-category identities remain in the census; the exclusion REGISTRY additionally carries their OUT_OF_CURRENT_CATEGORY rulings and the founder's VERIFIED_NO_PETS decisions (the Columbus mechanic: a category exit settles an identity as finally as a refusal)." % (SOURCE_WORK_ORDER, APPLICATION_WORK_ORDER)),
        ("source_authorities", [
            "https://trustarts.org/pct_home/visit/hotels",
            "https://www.paacc.com/list/category/hotels-motels-38",
            "https://www.eastlibertychamber.org/Stay",
            "https://www.pittsburgh-hotels.org/current-members",
            "https://www.visitpittsburgh.com/",
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
            "notes": "Address collisions are retained and flagged. Ace Hotel and The Maverick share 120 South Whitfield Street; Ace is closed/converted and Maverick is not current hotel category. Inn-category and STR rows stay in the census as NOT_LODGING.",
            "status": "PROVISIONAL_FLAGS_OPEN" if collision_detail else "NO_OPEN_CONFLICTS",
            "open_conflict_count": len(collision_detail),
        }),
        ("identity_state_counts", {
            "IDENTITY_CONFIRMED": sum(1 for r in hotels if r["identity_state"] == enums.IDENTITY_CONFIRMED),
            "IDENTITY_PROVISIONAL": sum(1 for r in hotels if r["identity_state"] == enums.IDENTITY_PROVISIONAL),
            "IDENTITY_UNRESOLVED": sum(1 for r in hotels if r["identity_state"] == enums.IDENTITY_UNRESOLVED),
        }),
        ("source_methodology", "Official destination-partner and chamber directories first (Cultural Trust, PAACC, East Liberty Chamber), then GPHA membership for gap-fill. Addresses from Cultural Trust, PAACC, and East Liberty Chamber were transcribed from those pages. GPHA names without an independently sourced street address are IDENTITY_PROVISIONAL. Cranberry, South Hills, and Allegheny Valley are in-scope because GPHA lists them as Pittsburgh-market members. Beaver/Washington/Greensburg/resort properties are ledger-only exclusions. policy_state is POLICY_NOT_VERIFIED throughout."),
        ("worker_branch", WORKER_BRANCH),
        ("worker_run", WORK_ORDER),
        ("source_work_order", SOURCE_WORK_ORDER),
        ("source_commit", "2d885d139950f93dba4f02edd04fa849781a8a0a"),
        ("hotels", hotels),
    ))

    issues = CENSUS.validate(census_doc, market_states=["PA"])
    if issues:
        raise SystemExit("census invalid: %s" % [(i.path, i.code, i.detail) for i in issues])

    decided = _decided_states()
    items = []
    for row in hotels:
        state = _blocker_for(row)
        terminal = state in enums.TERMINAL_STATES
        founder_decided = row["identity_key"] in decided \
            or row["normalized_name"] in decided
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
            ("next_action_source", "" if terminal else "identity_census/pittsburgh-pa.json"),
            ("determined_by", APPLICATION_WORK_ORDER if founder_decided else WORK_ORDER),
            ("updated_at", DECISION_DATE if founder_decided else AS_OF),
            ("official_url", row["official_url"]),
            ("state_override_reason",
             ("%s: founder decision applied from the Pass 1 packet; evidence "
              "is the hash-bound attended capture." % APPLICATION_WORK_ORDER)
             if founder_decided else ""),
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
        ("note", "Final states derive from committed authority: PUBLISHED_PET_FRIENDLY from approved records in hotel_policy_facts_pittsburgh-pa.json, VERIFIED_NO_PETS from the hotel_exclusions.json registry (Pass 1 founder decisions, %s). Every other identity is unresolved or out of current category. Silence is not a refusal." % APPLICATION_WORK_ORDER),
        ("source_authorities", ["identity_census/pittsburgh-pa.json"]),
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
        ("schema", "ptf-pittsburgh-source-registry/1.0"),
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
        ("_note", "Advisory coverage-audit configuration for the Pittsburgh factory census. Uncalibrated priors. Nothing gates on this file."),
        ("census_kind", "identity_census"),
        ("population", 2371000),
        ("thresholds", {}),
        ("non_independent_family_pairs", []),
        ("source_family_overrides", {
            "visit_pittsburgh": "CVB",
            "cultural_trust": "CVB",
            "paacc": "DIRECTORY",
            "east_liberty_chamber": "DIRECTORY",
            "gpha": "DIRECTORY",
            "parks_conservancy": "DIRECTORY",
            "city_parks": "REGISTRY",
            "avets": "CHAIN",
            "veg_pittsburgh": "CHAIN",
        }),
        ("zones_min_expected", {}),
        ("accepted_gaps", []),
    ))

    utility_items = []
    for raw_util in UTILITIES:
        item = OrderedDict(raw_util)
        item["revalidation_due"] = "2027-02-11"
        utility_items.append(item)
    utility_doc = OrderedDict((
        ("schema", "ptf-pittsburgh-utility-inventory/1.0"),
        ("work_order", WORK_ORDER),
        ("market_id", MARKET),
        ("as_of", AS_OF),
        ("revalidation_due", "2027-02-11"),
        ("note", "Advisory utility inventory. Not seed inventory and not publication. 180-day staleness is computed against the explicit as_of 2026-08-15 (due 2027-02-11), never by reading a clock. 24/7 veterinary labels require the facility's own page."),
        ("count", len(utility_items)),
        ("items", utility_items),
    ))

    ledger_doc = OrderedDict((
        ("schema", "ptf-pittsburgh-duplicate-ledger/1.0"),
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
        ("schema", "ptf-pittsburgh-founder-review-queue/1.0"),
        ("work_order", WORK_ORDER),
        ("market_id", MARKET),
        ("as_of", AS_OF),
        ("count", len(queue_items)),
        ("batch_size", 10),
        ("items", queue_items),
    ))

    routing_doc = OrderedDict((
        ("schema", "ptf-pittsburgh-routing-assessments/1.0"),
        ("work_order", WORK_ORDER),
        ("market_id", MARKET),
        ("as_of", AS_OF),
        ("note", "Assessments only. Nothing here is written to identity_routing.json and no status is ROUTING_CONFIRMED."),
        ("count", len(routing)),
        ("items", routing),
    ))

    _dump(CENSUS_PATH, census_doc)
    _dump(PARTITION_PATH, partition_doc)
    _dump(REPORTS / "pittsburgh-pa_source_registry.json", source_reg)
    _dump(REPORTS / "pittsburgh-pa_duplicate_ledger.json", ledger_doc)
    _dump(REPORTS / "pittsburgh-pa_routing_assessments.json", routing_doc)
    _dump(REPORTS / "pittsburgh-pa_founder_review_queue.json", queue_doc)
    _dump(REPORTS / "pittsburgh-pa_utility_inventory.json", utility_doc)
    _dump(PACKAGE / "markets" / "coverage" / "pittsburgh-pa.json", coverage)
    _dump(DATA_ROOT / "source_registry.json", source_reg)
    _dump(DATA_ROOT / "duplicate_ledger.json", ledger_doc)
    _dump(DATA_ROOT / "routing_assessments.json", routing_doc)
    _dump(DATA_ROOT / "utility_inventory.json", utility_doc)
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
        elif disp == "canonical" and (
                raw.get("disposition") == "closed"
                or raw.get("lodging") == "NEEDS_REVIEW"):
            final_disp = "closed_or_converted"
        elif disp == "canonical" and raw.get("ident") in (
                "IDENTITY_PROVISIONAL", "IDENTITY_UNRESOLVED"):
            final_disp = "identity_unresolved"
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
        ("schema", "ptf-pittsburgh-candidate-ledger/1.0"),
        ("work_order", WORK_ORDER),
        ("market_id", MARKET),
        ("as_of", AS_OF),
        ("count", len(candidate_items)),
        ("items", candidate_items),
    ))
    _dump(DATA_ROOT / "candidate_ledger.json", candidate_ledger)

    boundary_items = [x for x in ledger if x["disposition"] == "boundary_excluded"]
    _dump(DATA_ROOT / "boundary_exclusion_ledger.json", OrderedDict((
        ("schema", "ptf-pittsburgh-boundary-exclusion-ledger/1.0"),
        ("work_order", WORK_ORDER),
        ("market_id", MARKET),
        ("as_of", AS_OF),
        ("count", len(boundary_items)),
        ("items", boundary_items),
    )))

    rename_items = []
    for row in hotels:
        if row.get("former_name"):
            rename_items.append(OrderedDict((
                ("identity_key", row["identity_key"]),
                ("canonical_name", row["canonical_name"]),
                ("former_name", row["former_name"]),
                ("kind", "rename"),
            )))
    if any(r["canonical_name"] == "Ace Hotel Pittsburgh" for r in hotels):
        rename_items.append(OrderedDict((
            ("identity_key", "ace hotel pittsburgh"),
            ("canonical_name", "Ace Hotel Pittsburgh"),
            ("successor_name", "The Maverick by Kasa"),
            ("kind", "closed_or_converted"),
            ("notes", "East Liberty Chamber lists The Maverick by Kasa at 120 South Whitfield Street.",),
        )))
    _dump(DATA_ROOT / "rename_conversion_history.json", OrderedDict((
        ("schema", "ptf-pittsburgh-rename-conversion-history/1.0"),
        ("work_order", WORK_ORDER),
        ("market_id", MARKET),
        ("as_of", AS_OF),
        ("count", len(rename_items)),
        ("items", rename_items),
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
        ("schema", "ptf-pittsburgh-corridor-assignment-review/1.0"),
        ("work_order", WORK_ORDER),
        ("market_id", MARKET),
        ("as_of", AS_OF),
        ("count", len(review_rows)),
        ("diff_count", sum(1 for r in review_rows if r["diff"])),
        ("items", review_rows),
    )))

    _dump(DATA_ROOT / "reconciliation_report.json", OrderedDict((
        ("schema", "ptf-pittsburgh-reconciliation-report/1.0"),
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

    str_rows = [r for r in hotels if r["lodging_state"] == enums.NOT_LODGING]
    _dump(DATA_ROOT / "str_market_signal.json", OrderedDict((
        ("schema", "ptf-pittsburgh-str-market-signal/1.0"),
        ("work_order", WORK_ORDER),
        ("market_id", MARKET),
        ("as_of", AS_OF),
        ("note", "Market-level STR/flex-housing signal from category-excluded census rows only. Not lodging inventory and not publication.",),
        ("count", len(str_rows)),
        ("items", [OrderedDict((
            ("identity_key", r["identity_key"]),
            ("canonical_name", r["canonical_name"]),
            ("lodging_state", r["lodging_state"]),
            ("corridor", r["corridor"]),
        )) for r in str_rows]),
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
        ("schema", "ptf-pittsburgh-screenshot-queue/1.0"),
        ("work_order", WORK_ORDER),
        ("market_id", MARKET),
        ("as_of", AS_OF),
        ("count", len(screenshot_items)),
        ("captured", 0),
        ("items", screenshot_items),
    )))
    _dump(QUEUE_ROOT / "queue-index.json", queue_doc)

    summary = {
        "canonical": len(hotels),
        "published": rec.published,
        "verified_no_pets": rec.verified_no_pets,
        "out_of_category": rec.out_of_category,
        "unresolved": rec.unresolved,
        "queue": len(queue_items),
        "duplicates_ledger": sum(1 for x in ledger if x["disposition"] == "duplicate"),
        "boundary_excluded": sum(1 for x in ledger if x["disposition"] == "boundary_excluded"),
        "closed": sum(1 for x in ledger if x["disposition"] == "closed"),
        "utilities": len(UTILITIES),
        "confirmed_24_7": sum(1 for u in UTILITIES if u.get("is_24_7")),
        "agrees": rec.agrees,
        "final_state_counts": counts,
    }
    print(json.dumps(summary, indent=2))
    return summary


if __name__ == "__main__":
    build()
