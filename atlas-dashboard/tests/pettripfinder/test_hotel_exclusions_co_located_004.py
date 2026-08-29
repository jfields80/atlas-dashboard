"""PTF-INDIANAPOLIS-FOUNDER-PROMOTION-004, founder ruling A -- co-located hotels in the exclusion contract.

The street-identity guard stands. A shared address may coexist ONLY when strong,
brand-scoped signals mechanically prove two properties; every weaker case still
fires the guard. Property codes are family-scoped and never compared across
brand families.
"""
from __future__ import annotations

import pytest

from scripts.pettripfinder.hotel_exclusions import (
    CO_LOCATED_DISTINCT,
    CO_LOCATED_DUPLICATE,
    CO_LOCATED_INSUFFICIENT,
    SCHEMA,
    VERIFIED_NO_PETS,
    ExclusionContractError,
    approval_hash,
    brand_scoped_property_identity,
    canonical_url,
    co_located_distinct,
    record_hash,
    validate,
)
from scripts.pettripfinder.site_data import normalize_name


def _record(name, official_url, address="601 West Washington Street", postal="46204"):
    key = normalize_name(name)
    rec = {
        "exclusion_id": "ii-" + key.replace(" ", "-"),
        "canonical_name": name, "normalized_name": key,
        "address": address, "city": "Indianapolis", "state": "IN", "postal_code": postal,
        "phone": "", "official_url": official_url,
        "exclusion_state": VERIFIED_NO_PETS, "evidence_quote": "Pets Not Allowed",
        "source_url": official_url, "observed_at": "2026-08-25",
        "source_hash": "sha256:" + "0" * 64, "reviewer_id": "PTF-FOUNDER-001",
        "reviewed_at": "2026-08-25", "notes": "test", "market_id": "indianapolis-in",
    }
    rec["record_hash"] = record_hash(rec)
    rec["approval_hash"] = approval_hash(rec)
    return rec


def _doc(*records):
    return {"schema": SCHEMA, "contract": "test", "market_id": "indianapolis-in",
            "count": len(records), "exclusions": list(records)}


COURTYARD = _record("Courtyard by Marriott Indianapolis Downtown",
                    "https://www.marriott.com/en-us/hotels/indct-courtyard-indianapolis-downtown/overview/")
SPRINGHILL = _record("SpringHill Suites Indianapolis Downtown",
                     "https://www.marriott.com/en-us/hotels/indsd-springhill-suites-indianapolis-downtown/overview/")


# A -- the Indianapolis case ---------------------------------------------------------------
def test_a_courtyard_indct_and_springhill_indsd_at_601_w_washington_pass():
    verdict, why = co_located_distinct(COURTYARD, SPRINGHILL)
    assert verdict == CO_LOCATED_DISTINCT, why
    assert [r["normalized_name"] for r in validate(_doc(COURTYARD, SPRINGHILL))] == [
        COURTYARD["normalized_name"], SPRINGHILL["normalized_name"]]


# B -- same street + same brand-scoped code ---------------------------------------------------
def test_b_same_street_and_same_marriott_code_fail():
    alias = _record("Courtyard Indianapolis Downtown Marriott Place",
                    "https://www.marriott.com/indct")
    verdict, why = co_located_distinct(COURTYARD, alias)
    assert verdict == CO_LOCATED_DUPLICATE and "indct" in why
    with pytest.raises(ExclusionContractError, match="share one street identity"):
        validate(_doc(COURTYARD, alias))


# C -- different brands, distinct canonical URLs: PASS only when proven distinct --------------
def test_c_different_brands_pass_only_with_codes_on_both_sides():
    hilton = _record("Hampton Inn Indianapolis Downtown Circle Centre",
                     "https://www.hilton.com/en/hotels/inddthx-hampton-indianapolis-downtown/",
                     address="105 South Meridian Street", postal="46225")
    ihg = _record("Holiday Inn Express Indianapolis Circle Centre",
                  "https://www.ihg.com/holidayinnexpress/hotels/us/en/indianapolis/indms/hoteldetail",
                  address="105 South Meridian Street", postal="46225")
    assert co_located_distinct(hilton, ihg)[0] == CO_LOCATED_DISTINCT
    validate(_doc(hilton, ihg))
    # a brand whose URL carries no readable code is NOT proven distinct
    unreadable = _record("Independent Inn Circle Centre", "https://www.circlecentreinn.com/",
                         address="105 South Meridian Street", postal="46225")
    verdict, why = co_located_distinct(hilton, unreadable)
    assert verdict == CO_LOCATED_INSUFFICIENT
    with pytest.raises(ExclusionContractError, match="INSUFFICIENT"):
        validate(_doc(hilton, unreadable))


# D -- same street without strong identity signals -----------------------------------------
def test_d_same_street_without_strong_signals_fails():
    # two directory pages, no brand family, no property code: nothing proves two buildings
    a = _record("Baymont Inn and Suites Plainfield Airport", "https://www.visitindy.com/directory/baymont-plainfield/",
                address="6010 Gateway Drive", postal="46168")
    b = _record("Wingate by Wyndham Indianapolis Airport Plainfield", "https://www.visitindy.com/directory/wingate-plainfield/",
                address="6010 Gateway Drive", postal="46168")
    assert co_located_distinct(a, b)[0] == CO_LOCATED_INSUFFICIENT
    with pytest.raises(ExclusionContractError, match="share one street identity"):
        validate(_doc(a, b))


# E -- identical canonical URL under two records ---------------------------------------------
def test_e_identical_canonical_url_under_two_records_fails():
    a = _record("Hyatt Place Indianapolis Downtown", "https://www.hyatt.com/en-us/hotel/indiana/hyatt-place-indianapolis-downtown/indzi",
                address="130 South Pennsylvania Street")
    b = _record("Hyatt House Indianapolis / Downtown", "https://hyatt.com/en-us/hotel/indiana/hyatt-place-indianapolis-downtown/indzi/",
                address="130 South Pennsylvania Street")
    assert canonical_url(a["official_url"]) == canonical_url(b["official_url"])
    verdict, why = co_located_distinct(a, b)
    assert verdict == CO_LOCATED_DUPLICATE and "canonical" in why
    with pytest.raises(ExclusionContractError, match="DUPLICATE"):
        validate(_doc(a, b))


# F -- raw codes reused across brand families are not matches --------------------------------
def test_f_raw_codes_across_families_do_not_collide():
    assert brand_scoped_property_identity("https://www.marriott.com/indsw") == ("MARRIOTT", "indsw")
    assert brand_scoped_property_identity(
        "https://www.ihg.com/holidayinnexpress/hotels/us/en/plainfield/indsw/hoteldetail") == ("IHG", "indsw")
    marriott = _record("SpringHill Suites by Marriott Indianapolis Westfield", "https://www.marriott.com/indsw",
                       address="19317 Westmore Lane", postal="46074")
    ihg = _record("Holiday Inn Express Plainfield",
                  "https://www.ihg.com/holidayinnexpress/hotels/us/en/plainfield/indsw/hoteldetail",
                  address="19317 Westmore Lane", postal="46074")
    verdict, why = co_located_distinct(marriott, ihg)
    assert verdict == CO_LOCATED_DISTINCT and "MARRIOTT:indsw" in why and "IHG:indsw" in why


# the guard is never weakened for the cases it already caught ------------------------------
def test_duplicate_identity_keys_are_still_refused_first():
    with pytest.raises(ExclusionContractError, match="duplicate excluded identity"):
        validate(_doc(COURTYARD, dict(COURTYARD, exclusion_id="ii-other")))


def test_the_extractor_never_returns_a_code_without_its_family():
    assert brand_scoped_property_identity("https://www.hotelindy.com") == ("", "")
    assert brand_scoped_property_identity("https://www.marriott.com/") == ("MARRIOTT", "")
    assert brand_scoped_property_identity("") == ("", "")
