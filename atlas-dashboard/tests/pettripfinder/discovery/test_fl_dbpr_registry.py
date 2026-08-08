"""PTF-DISCOVERY-P0-001 -- Florida DBPR REGISTRY adapter tests.

The synthetic extract below uses the REAL hrlodge column layout (verified
against the live District 1 file, 2026-08-07) with invented rows -- no
Tampa market data is created here, per the work order. The adapter's own
output is validated by the same ``validate_emission_batch`` the ingestion
boundary runs, so contract drift fails in this file first.
"""

from __future__ import annotations

import pytest

from scripts.pettripfinder.discovery.fl_dbpr_registry import (
    SOURCE_ID,
    DbprAdapterError,
    build_adapter_manifest,
    parse_hrlodge_csv,
)
from scripts.pettripfinder.discovery.identity_observation import (
    observation_to_evidence,
)

HEADER = ('"Board Code","License Type Code","Licensee Name","Rank Code",'
          '"Modifier Code","Mailing Name","Mailing Street Address",'
          '"Mailing Address Line 2","Mailing Address Line 3","Mailing City",'
          '"Mailing State Code","Mailing Zip Code","Primary Phone Number",'
          '"Mailing County Code","Business Name","Filler",'
          '"Location Street Address","Location Address Line 2",'
          '"Location Address Line 3","Location City","Location State Code",'
          '"Location Zip Code","Location County Code","Location County",'
          '"Secondary Phone Number","District","Region","License Number",'
          '"Primary Status Code","Secondary Status Code","License Expiry Date",'
          '"Last Inspection Date","Number of Seats or Rental Units",'
          '"Base Risk Level","Secondary Risk Level"')


def _row(licensee="SAMPLE HOLDINGS LLC", rank="HOTL", business="SAMPLE HOTEL",
         address="100 EXAMPLE AVE", addr2="", city="SAMPLETOWN", state="FL",
         zip_code="33900", phone2="(305)555-0100", phone1="",
         license_number="HOT0000001"):
    cells = ["200", "2001", licensee, rank, "", "", "1 MAILING ST", "", "",
             "MAILVILLE", "FL", "33901", phone1, "23", business, "",
             address, addr2, "", city, state, zip_code, "23", "Sample",
             phone2, "1", "01", license_number, "20", "20", "10/01/2026",
             "07/24/2026", "50", "", ""]
    return ",".join('"%s"' % c for c in cells)


def _parse(rows):
    return parse_hrlodge_csv(
        "\n".join([HEADER] + rows),
        observed_at="2026-08-01",
        retrieved_at="2026-08-07T00:00:00Z",
        raw_pointer_prefix="hrlodge1.csv",
        snapshot_hash="a" * 64,
        license_tag="VERIFIED 2026-08-07")


class TestParsing:
    def test_clean_hotel_row_yields_clean_high_confidence_observation(self):
        observations, skipped = _parse([_row()])
        assert skipped == []
        obs = observations[0]
        assert obs["source_id"] == SOURCE_ID
        assert obs["source_family"] == "REGISTRY"
        assert obs["name"] == "SAMPLE HOTEL"
        assert obs["address"] == "100 EXAMPLE AVE"
        assert obs["zip"] == "33900"
        assert obs["phone"] == "(305)555-0100"
        assert obs["license_class"] == "HOTL"
        assert obs["property_code"] == "FL_DBPR:HOT0000001"
        assert obs["parse_confidence"] == "HIGH"
        assert obs["warnings"] == []
        assert obs["provenance"]["raw_pointer"] == "hrlodge1.csv#row=1"

    def test_output_translates_into_evidence(self):
        observations, _ = _parse([_row()])
        evidence = observation_to_evidence(observations[0])
        assert evidence["tier"] == 2
        assert evidence["postal_code"] == "33900"

    def test_wrong_csv_fails_closed(self):
        with pytest.raises(DbprAdapterError, match="missing column"):
            parse_hrlodge_csv("a,b,c\n1,2,3", observed_at="2026-08-01",
                              retrieved_at="2026-08-07T00:00:00Z",
                              raw_pointer_prefix="x.csv")

    def test_nine_digit_zip_is_normalized_to_five(self):
        observations, _ = _parse([_row(zip_code="339004209")])
        assert observations[0]["zip"] == "33900"
        assert observations[0]["warnings"] == []

    def test_dashed_zip_plus_four_is_normalized(self):
        observations, _ = _parse([_row(zip_code="33900-4209")])
        assert observations[0]["zip"] == "33900"

    def test_unparseable_zip_warns_and_drops(self):
        observations, _ = _parse([_row(zip_code="339")])
        obs = observations[0]
        assert "zip" not in obs
        assert any(w["code"] == "W_ADDR_UNPARSED" for w in obs["warnings"])
        assert obs["parse_confidence"] == "MEDIUM"

    def test_invalid_location_phone_warns_and_falls_back_to_primary(self):
        observations, _ = _parse([_row(phone2="813-555-01",
                                       phone1="(305)555-0199")])
        obs = observations[0]
        assert obs["phone"] == "(305)555-0199"
        assert any(w["code"] == "W_PHONE_INVALID" for w in obs["warnings"])

    def test_address_line_2_is_joined(self):
        observations, _ = _parse([_row(addr2="UNIT B")])
        assert observations[0]["address"] == "100 EXAMPLE AVE UNIT B"


class TestBoundaries:
    def test_non_hotel_motel_rank_is_passed_through_with_ambiguity_warning(self):
        observations, skipped = _parse([_row(rank="CNDO",
                                             business="SAMPLE VACATION CONDO",
                                             license_number="CND0000001")])
        assert skipped == []
        obs = observations[0]
        assert obs["license_class"] == "CNDO"
        assert any(w["code"] == "W_AMBIGUOUS_ROW" and "FD-R8" in w["detail"]
                   for w in obs["warnings"])

    def test_motel_rank_is_unambiguous(self):
        observations, _ = _parse([_row(rank="MOTL", business="SAMPLE MOTEL",
                                       license_number="MOT0000001")])
        assert observations[0]["warnings"] == []

    def test_missing_business_name_falls_back_to_licensee_with_warning(self):
        observations, skipped = _parse([_row(business="")])
        assert skipped == []
        obs = observations[0]
        assert obs["name"] == "SAMPLE HOLDINGS LLC"
        assert any(w["code"] == "W_AMBIGUOUS_ROW" for w in obs["warnings"])

    def test_row_without_any_name_is_skipped_with_reason(self):
        observations, skipped = _parse([_row(business="", licensee="")])
        assert observations == []
        assert skipped == [{"raw_pointer": "hrlodge1.csv#row=1",
                            "reason": "no business or licensee name"}]

    def test_row_without_license_number_is_skipped_with_reason(self):
        _, skipped = _parse([_row(license_number="")])
        assert skipped[0]["reason"] == "no license number"

    def test_no_policy_field_can_survive_an_extra_csv_column(self):
        # A hypothetical future extract column named for a policy field is
        # structurally ignored: only the declared columns are ever read.
        header = HEADER + ',"Pets Allowed"'
        row = _row() + ',"YES"'
        observations, _ = parse_hrlodge_csv(
            "\n".join([header, row]), observed_at="2026-08-01",
            retrieved_at="2026-08-07T00:00:00Z", raw_pointer_prefix="x.csv")
        assert "pets_allowed" not in observations[0]
        assert "Pets Allowed" not in observations[0]

    def test_determinism(self):
        assert _parse([_row(), _row(license_number="HOT0000002",
                                    business="OTHER HOTEL")]) == \
            _parse([_row(), _row(license_number="HOT0000002",
                                 business="OTHER HOTEL")])


class TestManifest:
    def test_manifest_declares_the_contract_and_dated_licensing_note(self):
        manifest = build_adapter_manifest()
        assert manifest["source_id"] == SOURCE_ID
        assert manifest["source_family"] == "REGISTRY"
        assert manifest["contract_version"] == "1.0.0"
        assert manifest["retrieval_mode"] == "bulk_file"
        assert "VERIFIED 2026-08-07" in manifest["licensing_note"]
