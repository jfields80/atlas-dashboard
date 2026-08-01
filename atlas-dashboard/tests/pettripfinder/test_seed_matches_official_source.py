"""PTF-DATA -- the seed's address must agree with the source it cites.

The Staybridge Suites Columbus-Dublin row claimed postal code 43017 with
``source_type: OFFICIAL_PROPERTY`` and a ``source_url`` pointing at the IHG
property page. That page has never said 43017 -- the string appears nowhere in
its rendered text or its HTML. The value did not come from the source the row
cites, and it propagated into the reconciliation baseline, five pilot
assignment sets and every generated capture queue before anyone compared the
two.

These tests exist so a seed row cannot again assert an address its own cited
source contradicts. The expected values are READ FROM the captured official
page, never written down here: hardcoding 43016 would simply move the
unverified literal from the CSV into a test, and the next drift would be
invisible in exactly the same way.

Offline: reads the committed fixture and the committed seed. No network.
"""

from __future__ import annotations

import csv
import io
import json
import pathlib

import pytest

REPO_ROOT = pathlib.Path(__file__).resolve().parents[2]
SEED = REPO_ROOT / "launch_packages" / "pettripfinder" / "seed_businesses.csv"
FIXTURE = (REPO_ROOT / "tests" / "research_workers" / "capture_automation"
           / "fixtures" / "ihg-cmhtc.json")

SEED_NAME = "Staybridge Suites Columbus Dublin"
PROPERTY_CODE = "cmhtc"


@pytest.fixture(scope="module")
def official():
    """The official page's own statement of its identity, from the capture."""
    payload = json.loads(FIXTURE.read_text("utf-8"))
    hotel = next(b for b in payload["jsonld"]
                 if isinstance(b, dict)
                 and str(b.get("@type", "")).lower() == "hotel")
    address = hotel.get("address")
    assert isinstance(address, dict), "fixture carries no PostalAddress"
    return {"payload": payload, "hotel": hotel, "address": address}


@pytest.fixture(scope="module")
def seed_row():
    with SEED.open(encoding="utf-8-sig", newline="") as fh:
        for row in csv.DictReader(fh):
            if row.get("name") == SEED_NAME:
                return row
    raise AssertionError("seed row %r not found" % SEED_NAME)


class TestSeedAgreesWithTheSourceItCites:
    def test_the_fixture_is_the_property_the_seed_points_at(self, official, seed_row):
        """Guards the comparison itself: if the fixture ever became a
        different hotel, every assertion below would silently pass."""
        assert PROPERTY_CODE in official["payload"]["final_url"]
        assert PROPERTY_CODE in seed_row["website_url"]
        assert PROPERTY_CODE in seed_row["source_url"]

    def test_the_seed_cites_the_official_property_as_its_source(self, seed_row):
        assert seed_row["source_type"] == "OFFICIAL_PROPERTY"
        assert seed_row["source_url"].startswith("https://www.ihg.com/")

    def test_postal_code_matches_the_official_json_ld(self, official, seed_row):
        """The assertion this file exists for. The expected value is read from
        the captured page, not written here."""
        assert seed_row["postal_code"] == official["address"]["postalCode"]

    def test_street_address_matches_the_official_json_ld(self, official, seed_row):
        assert seed_row["address"] == official["address"]["streetAddress"]

    def test_city_and_state_match(self, official, seed_row):
        assert seed_row["city"] == official["address"]["addressLocality"]
        assert seed_row["state"] == official["address"]["addressRegion"]

    def test_phone_digits_match(self, official, seed_row):
        def digits(value):
            return "".join(c for c in str(value or "") if c.isdigit())

        seed_digits = digits(seed_row["phone"])
        page_digits = digits(official["hotel"].get("telephone"))
        # The page writes a leading country code the seed omits.
        assert page_digits.endswith(seed_digits), (seed_digits, page_digits)

    def test_the_postal_code_actually_appears_on_the_page(self, official, seed_row):
        """Not merely equal to a JSON-LD field -- present in what a reader
        sees. This is the check that would have caught 43017 immediately."""
        text = official["payload"]["text"]
        assert seed_row["postal_code"] in text

    def test_the_superseded_value_appears_nowhere_on_the_page(self, official):
        """43017 is Dublin OH's other ZIP. It is not this property's, and the
        cited page has never carried it."""
        payload = official["payload"]
        assert "43017" not in payload["text"]
        assert "43017" not in payload["html"]


class TestTheSeedStaysInternallyConsistent:
    def test_no_hotel_row_is_missing_a_postal_code(self):
        with SEED.open(encoding="utf-8-sig", newline="") as fh:
            rows = [r for r in csv.DictReader(fh)
                    if r.get("category") == "pet-friendly-hotels"]
        missing = [r["name"] for r in rows if not (r.get("postal_code") or "").strip()]
        assert not missing, missing

    def test_every_hotel_postal_code_is_five_digits(self):
        with SEED.open(encoding="utf-8-sig", newline="") as fh:
            rows = [r for r in csv.DictReader(fh)
                    if r.get("category") == "pet-friendly-hotels"]
        bad = [(r["name"], r["postal_code"]) for r in rows
               if not (r["postal_code"].isdigit() and len(r["postal_code"]) == 5)]
        assert not bad, bad

    def test_the_seed_still_uses_lf_line_endings(self):
        """launch_packages/**/*.csv is pinned to eol=lf in .gitattributes; a
        CRLF rewrite here would change the committed package hash."""
        assert b"\r\n" not in SEED.read_bytes()
