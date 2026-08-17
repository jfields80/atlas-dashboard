"""PTF-CLEVELAND-MARKET-FACTORY-001 -- a property code is unique within its brand.

Cleveland is the first market dense enough to prove the old rule wrong. IHG's
Hotel Indigo Cleveland Beachwood is ``clebd`` on ihg.com; Marriott's Residence
Inn Cleveland Beachwood is ``clebd`` on marriott.com. Both extractions are
correct, the hotels are a mile apart, and comparing codes globally called the
whole routing authority corrupt and refused to load it.

Scoping the check by registrable domain makes it true rather than merely strict.
The case the rule exists for -- one brand's code aimed at two of that brand's
properties, which is how a capture ends up proving the wrong hotel -- still
fails, and that is what most of this module tests.

The URL check stays global on purpose: one URL cannot be two properties whoever
serves it, which is how both Drury Cleveland hotels pointing at
druryhotels.com's front door gets caught.
"""

from __future__ import annotations

import pytest

from scripts.pettripfinder.identity_routing import (
    IdentityRoutingError, ROUTING_CONFIRMED, validate_authority,
)

MARKET = "cleveland-akron-canton-oh"


def route(name, url, code="", market=MARKET, status=ROUTING_CONFIRMED):
    key = name.lower().replace(" ", "-")
    return {
        "routing_id": "route-%s-%s" % (market, key),
        "schema_version": "1.0.0",
        "hotel_ref": {"market_id": market, "canonical_name": name,
                      "normalized_name": name.lower()},
        "market_id": market,
        "official_property_url": url,
        "official_domain": url.split("/")[2].split(".", 1)[-1] if "//" in url else "",
        "property_code": code,
        "brand": "",
        "binding_method": "BRAND_INDEX_BINDING",
        "binding_sources": ["cvb listing"],
        "identity_signals_matched": ["cvb_listing_for_this_property"],
        "observed_at": "2026-08-09", "verified_at": "2026-08-09",
        "status": status,
        "notes": "test fixture",
    }


def authority(*routes):
    return {"schema": "ptf-identity-routing/1.0", "contract_version": "1.0.0",
            "routes": list(routes)}


#: The two real Cleveland records that exposed this.
INDIGO = route("Hotel Indigo Cleveland Beachwood",
               "https://www.ihg.com/hotelindigo/hotels/us/en/beachwood/clebd/hoteldetail",
               "clebd")
RESIDENCE = route("Residence Inn Cleveland Beachwood",
                  "https://www.marriott.com/en-us/hotels/clebd-residence-inn-cleveland-beachwood/overview/",
                  "clebd")


class TestTheRealCollisionIsAccepted:

    def test_the_same_code_on_two_different_brands_is_valid(self):
        assert len(validate_authority(authority(INDIGO, RESIDENCE))) == 2

    def test_it_is_the_domain_that_separates_them(self):
        """Not the brand string, not the name -- the registrable domain of the
        URL each code was extracted from."""
        out = validate_authority(authority(INDIGO, RESIDENCE))
        assert {r["official_property_url"].split("/")[2] for r in out} == {
            "www.ihg.com", "www.marriott.com"}


class TestTheDangerousCollisionStillFails:
    """One brand, one code, two properties. This is the case that lets a
    capture prove the wrong hotel, and it must never load."""

    def test_two_marriott_properties_sharing_a_code_is_refused(self):
        a = route("Residence Inn Cleveland Beachwood",
                  "https://www.marriott.com/en-us/hotels/clebd-residence-inn/overview/", "clebd")
        b = route("Courtyard Cleveland Beachwood",
                  "https://www.marriott.com/en-us/hotels/clebd-courtyard/overview/", "clebd")
        with pytest.raises(IdentityRoutingError) as e:
            validate_authority(authority(a, b))
        assert "binds two different identities" in str(e.value)
        assert "marriott.com" in str(e.value)

    def test_two_ihg_properties_sharing_a_code_is_refused(self):
        a = route("Hotel Indigo Beachwood",
                  "https://www.ihg.com/hotelindigo/hotels/us/en/beachwood/clebd/hoteldetail", "clebd")
        b = route("Holiday Inn Beachwood",
                  "https://www.ihg.com/holidayinn/hotels/us/en/beachwood/clebd/hoteldetail", "clebd")
        with pytest.raises(IdentityRoutingError):
            validate_authority(authority(a, b))

    def test_a_subdomain_of_the_same_brand_is_still_the_same_brand(self):
        """embassysuites3.hilton.com and www.hilton.com are one namespace."""
        a = route("Embassy Suites Beachwood",
                  "https://embassysuites3.hilton.com/en/hotels/clebhes-x/", "clebhes")
        b = route("Hilton Cleveland East",
                  "https://www.hilton.com/en/hotels/clebhes-y/", "clebhes")
        with pytest.raises(IdentityRoutingError):
            validate_authority(authority(a, b))


class TestTheUrlRuleStaysGlobal:

    def test_one_url_for_two_hotels_is_refused_whoever_serves_it(self):
        """Both Cleveland Drury properties were linked to the brand's front
        door by the CVB. A brand homepage is property-specific for nobody."""
        a = route("Drury Inn And Suites Beachwood", "https://www.druryhotels.com")
        b = route("Drury Plaza Hotel", "https://www.druryhotels.com")
        with pytest.raises(IdentityRoutingError) as e:
            validate_authority(authority(a, b))
        assert "URL" in str(e.value) and "binds two different identities" in str(e.value)

    def test_two_property_pages_on_one_brand_are_fine(self):
        a = route("Courtyard Cleveland Beachwood",
                  "https://www.marriott.com/en-us/hotels/clebw-courtyard/overview/", "clebw")
        b = route("Residence Inn Cleveland Beachwood",
                  "https://www.marriott.com/en-us/hotels/clebd-residence-inn/overview/", "clebd")
        assert len(validate_authority(authority(a, b))) == 2


class TestNothingElseMoved:

    def test_a_record_with_no_code_is_never_compared(self):
        a = route("Aloft Beachwood", "https://www.aloftbeachwood.com")
        b = route("Hampton Inn Beachwood", "https://www.hamptoninnbeachwood.com")
        assert len(validate_authority(authority(a, b))) == 2

    def test_code_comparison_is_case_insensitive_within_a_brand(self):
        a = route("A", "https://www.marriott.com/en-us/hotels/CLEBD-a/overview/", "CLEBD")
        b = route("B", "https://www.marriott.com/en-us/hotels/clebd-b/overview/", "clebd")
        with pytest.raises(IdentityRoutingError):
            validate_authority(authority(a, b))

    def test_the_live_routing_authority_still_validates(self):
        """The real file, after Cleveland's 87 records were added to Columbus's
        20. If the scoping change had broken anything, it would show here."""
        from scripts.pettripfinder.identity_routing import load_routes
        routes = load_routes()
        # 107 -> 80: PTF-CLEVELAND-OVERNIGHT-AUTHORITY-001 retired the 27
        # routes whose hotels became Cleveland inventory or exclusions. Routing
        # is only ever for a CONFIRMED hotel that is NOT inventory.
        # 80 -> 167: PTF-CLEVELAND-URL-RECOVERY-WORKER-002 identity-verified
        # and routed 87 more Cleveland hotels that were previously
        # NO_OFFICIAL_URL; Columbus is unchanged at 20.
        # 167 -> 165: PTF-CLEVELAND-POLICY-CAPTURE-INTEGRATION-003 retired
        # the two Drury routes whose hotels became Cleveland inventory.
        # 165 -> 174: PTF-DAYTON-WORK-BROWSER-INTEGRATION-001 opened Dayton
        # routing with nine first-time bindings, one CONFIRMED and eight HELD.
        # Dayton is the first market to add a Choice/IHG/Red Roof route since
        # the codes were scoped by registrable domain, which is exactly the
        # case this file exists for.
        assert len(routes) == 157  # plus Grand Rapids--Holland's 67 routed identities
        markets = {r["market_id"] for r in routes}
        assert {"columbus-oh", "cleveland-akron-canton-oh", "dayton-oh"} <= markets
