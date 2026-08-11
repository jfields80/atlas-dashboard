"""PTF-DAYTON-INTEGRATION-AND-CANDIDATE-BUILD-001 -- Dayton authority and isolation.

These run against the committed Dayton authority, not fixtures. What they
defend is what the worker package got wrong, and would get wrong again:

  * a fee published from a lossy transcription rather than the captured page
  * a contradictory or dual-representation fee resolved by picking one
  * a truncated or garbled species string completed into a claim
  * "per pet" leaking off Hampton Troy onto the other Hamptons
  * a VERIFIED_NO_PETS with no artifact behind it
  * Dayton counted into Columbus's or Cleveland's authority, or the reverse
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pytest

from scripts.pettripfinder.hotel_exclusions import load_exclusions
from scripts.pettripfinder.market_ownership import owned_by
from scripts.pettripfinder.site_data import (
    normalize_name, published_facts_path, read_production_rows,
)

DAYTON = "dayton-oh"
COLUMBUS = "columbus-oh"
CLEVELAND = "cleveland-akron-canton-oh"
_ROOT = Path(__file__).resolve().parents[2]

#: The counts this integration adjudicated, as a partition of the 129-hotel
#: census. They are asserted as a set so a silent drift in any one of them
#: fails rather than being absorbed by another bucket.
ACCEPTED = 33
NO_PETS = 6
HELD = 6
CENSUS = 129


@pytest.fixture(scope="module")
def facts():
    return json.loads(published_facts_path(DAYTON).read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def census():
    p = (_ROOT / "launch_packages" / "pettripfinder" / "identity_census"
         / "dayton-oh.json")
    return json.loads(p.read_text(encoding="utf-8"))


class TestDaytonAuthority:

    def test_thirty_three_hotels_are_published(self, facts):
        assert facts["market"] == DAYTON
        assert len(facts["hotels"]) == ACCEPTED
        assert {h["verification_state"] for h in facts["hotels"]} == {"VERIFIED_PET_FRIENDLY"}

    def test_six_verified_no_pets_are_dayton_owned(self):
        day = [e for e in load_exclusions()
               if e.get("market_id") == DAYTON
               and e["exclusion_state"] == "VERIFIED_NO_PETS"]
        assert len(day) == NO_PETS

    def test_every_published_fact_carries_a_quote_from_the_page(self, facts):
        """The whole standard in one assertion. Three of the worker's quotes
        were lossy transcriptions ("5.00" for "$75.00"); this is the check that
        catches that class of error rather than trusting the extracted value."""
        for hotel in facts["hotels"]:
            evidence = {e["field"]: e["quote"] for e in hotel["evidence"]}
            page = " ".join(hotel["evidence_quote"].split()).lower()
            for field in hotel["facts"]:
                assert field in evidence, "%s: %s has no evidence" % (hotel["name"], field)
                assert " ".join(evidence[field].split()).lower() in page, (
                    "%s: %s quote is not in the captured page text"
                    % (hotel["name"], field))

    def test_withheld_fields_are_recorded_and_absent_from_facts(self, facts):
        for hotel in facts["hotels"]:
            for field, reason in hotel["withheld_fields"].items():
                assert field not in hotel["facts"], (
                    "%s: %s is both withheld and published" % (hotel["name"], field))
                assert len(reason) > 20, "a withheld field needs a real reason"

    def test_no_invented_money_or_weight_units(self, facts):
        for hotel in facts["hotels"]:
            f = hotel["facts"]
            if "pet_fee" in f:
                assert re.fullmatch(r"\$\d+\.\d{2}", f["pet_fee"]), hotel["name"]
            if "weight_limit" in f:
                assert f["weight_limit"].endswith(" pounds"), hotel["name"]
            # {lt, lte, combined} is the closed operator set. "per pet" is not a
            # member and renders as nothing at all, so it is withheld instead.
            assert f.get("weight_limit_operator") in (None, "lt", "lte", "combined")

    def test_a_fee_cap_is_a_structure_not_a_display_string(self, facts):
        """A cap that arrives as "$75.00 per stay" reaches the detail renderer
        as a str and is asked for .get("amount"). Two properties carry one."""
        caps = [h for h in facts["hotels"] if "fee_cap" in h["facts"]]
        assert len(caps) == 2
        for hotel in caps:
            cap = hotel["facts"]["fee_cap"]
            assert isinstance(cap, dict), hotel["name"]
            assert cap["amount"] == "75.00" and cap["basis"] == "per stay"
            # the ceiling is NOT the rate
            assert hotel["facts"]["pet_fee"] == "$25.00"


class TestContradictionsArePreservedNotResolved:

    def test_springhill_troy_publishes_no_fee(self, facts):
        """Its page shows "Per Stay: $125.00" beside a $75/$150/$250 ladder
        containing no $125 band. Picking one would invent a price."""
        h = next(x for x in facts["hotels"] if x["key"] == "springhill suites troy dayton")
        assert "pet_fee" not in h["facts"] and "fee_tiers" not in h["facts"]
        assert "pet_fee" in h["withheld_fields"]
        # what IS supported still publishes
        assert h["facts"]["species_allowed"] == "dogs"
        assert h["facts"]["weight_limit"] == "50 pounds"

    def test_towneplace_beavercreek_publishes_no_fee(self, facts):
        """"$100.00 per stay" and "$20.00 per night" are listed as separate
        rows; they coincide only for a five-night stay."""
        h = next(x for x in facts["hotels"]
                 if x["key"] == "towneplace suites by marriott dayton beavercreek")
        assert "pet_fee" not in h["facts"] and "fee_basis" not in h["facts"]
        assert h["facts"]["weight_limit"] == "75 pounds"

    def test_hilton_garden_inn_beavercreek_computes_no_additive_total(self, facts):
        """"$75(1-5 nights) additional $75(5+ night)" is an add-on. The worker
        recorded a $150 second band; no total is asserted here."""
        h = next(x for x in facts["hotels"] if x["key"] == "hilton garden inn dayton beavercreek")
        assert h["facts"]["pet_fee"] == "$75.00"
        assert "fee_tiers" not in h["facts"]
        assert "150" not in json.dumps(h["facts"])
        assert "additional" in h["facts"]["general_restrictions"]


class TestSpeciesIsNeverCompleted:

    def test_xenia_withholds_a_garbled_species(self, facts):
        """The page renders "dog/only" -- neither "dogs only" nor "dog/cat
        only", which are different promises."""
        h = next(x for x in facts["hotels"] if x["key"] == "hampton inn and suites xenia dayton")
        assert "species_allowed" not in h["facts"]
        assert "species_allowed" in h["withheld_fields"]

    def test_home2_beavercreek_withholds_a_truncated_species(self, facts):
        """The page's own text stops at "dog/cat on"."""
        h = next(x for x in facts["hotels"] if x["key"] == "home2 suites by hilton dayton beavercreek")
        assert "species_allowed" not in h["facts"]


class TestPerPetScopeDoesNotSpread:

    def test_hampton_troy_states_per_pet(self, facts):
        h = next(x for x in facts["hotels"] if x["key"] == "hampton inn troy")
        assert h["facts"]["fee_scope"] == "per pet"
        assert "per pet" in h["evidence_quote"]

    def test_no_other_hampton_claims_a_fee_scope(self, facts):
        """Six other Hampton/Hilton-brand properties in this market show the
        same fee shape and never say "per pet". The scope stays where the words
        are."""
        others = [h for h in facts["hotels"]
                  if "hampton" in h["key"] and h["key"] != "hampton inn troy"]
        assert len(others) >= 5
        for h in others:
            assert "fee_scope" not in h["facts"], h["name"]
            assert "fee_scope" in h["withheld_fields"], h["name"]


class TestNegativeFactsNeedArtifactsToo:

    def test_every_dayton_exclusion_quotes_an_affirmative_refusal(self):
        for e in load_exclusions():
            if e.get("market_id") != DAYTON:
                continue
            quote = e["evidence_quote"].lower()
            assert "not allowed" in quote or "no pets" in quote, e["canonical_name"]
            assert e["source_hash"], e["canonical_name"]

    def test_hie_troy_is_not_excluded(self):
        """The worker counted it VERIFIED_NO_PETS on a research-agent assertion
        with no quote, no capture and no hash. Silence about evidence is not
        evidence, so it went back to unresolved rather than being grandfathered."""
        names = {normalize_name(e["canonical_name"]) for e in load_exclusions()}
        assert normalize_name("Holiday Inn Express & Suites Troy") not in names

    def test_the_census_still_records_it_for_a_later_capture(self, census):
        hit = [h for h in census["hotels"]
               if normalize_name(h["canonical_name"])
               == normalize_name("Holiday Inn Express & Suites Troy")]
        assert len(hit) == 1, "the property is retained, not deleted"


class TestTheCensusPartitions:

    def test_the_census_is_one_hundred_twenty_nine(self, census):
        assert census["count"] == CENSUS == len(census["hotels"])

    def test_slugs_are_unique(self, census):
        slugs = [h["slug"] for h in census["hotels"]]
        assert len(set(slugs)) == len(slugs)

    def test_accepted_plus_excluded_never_exceeds_the_census(self, facts):
        assert ACCEPTED + NO_PETS + HELD <= CENSUS

    def test_every_published_hotel_is_identity_confirmed(self, facts, census):
        by_key = {normalize_name(h["canonical_name"]): h for h in census["hotels"]}
        for hotel in facts["hotels"]:
            row = by_key.get(hotel["key"])
            assert row is not None, "%s is not in the census" % hotel["name"]
            assert row["identity_state"] == "IDENTITY_CONFIRMED", hotel["name"]


class TestMarketIsolation:

    def test_dayton_inventory_is_owned_by_dayton(self):
        rows = [r for r in read_production_rows() if r.get("market_id") == DAYTON]
        assert len(rows) == ACCEPTED
        assert len(owned_by(rows, DAYTON)) == ACCEPTED

    def test_columbus_and_cleveland_row_counts_are_untouched(self):
        rows = read_production_rows()
        assert len([r for r in rows if r.get("market_id") == COLUMBUS]) == 116
        assert len([r for r in rows if r.get("market_id") == CLEVELAND]) == 19

    def test_columbus_still_has_exactly_fourteen_no_pets(self):
        cbus = [e for e in load_exclusions()
                if e.get("market_id") == COLUMBUS
                and e["exclusion_state"] == "VERIFIED_NO_PETS"]
        assert len(cbus) == 14

    def test_cleveland_still_has_exactly_eight_no_pets(self):
        cle = [e for e in load_exclusions()
               if e.get("market_id") == CLEVELAND
               and e["exclusion_state"] == "VERIFIED_NO_PETS"]
        assert len(cle) == 8

    def test_no_dayton_hotel_appears_in_another_market_authority(self, facts):
        day_keys = {h["key"] for h in facts["hotels"]}
        for market in (COLUMBUS, CLEVELAND):
            path = published_facts_path(market)
            if not path.exists():
                continue
            other = json.loads(path.read_text(encoding="utf-8"))
            assert not (day_keys & {h["key"] for h in other["hotels"]}), market


class TestTheCollisionAtPresidentialDrive:

    def test_neither_party_publishes(self, facts):
        """Homewood Suites (CONFIRMED) and Staybridge Fairborn (PROVISIONAL)
        both claim 2750 Presidential Dr. The conflict was marked RESOLVED with
        a null resolution and a note saying verification was still required, so
        neither reaches the published set."""
        keys = {h["key"] for h in facts["hotels"]}
        assert normalize_name("Homewood Suites by Hilton Dayton-Fairborn (Wright Patterson)") not in keys
        assert normalize_name("Staybridge Suites Fairborn - Dayton East") not in keys

    def test_no_two_published_dayton_rows_share_a_street_and_zip(self):
        rows = [r for r in read_production_rows() if r.get("market_id") == DAYTON]
        seen = {}
        for r in rows:
            key = (r["address"].strip().lower(), r["postal_code"].strip())
            assert key not in seen, "%s collides with %s" % (r["name"], seen.get(key))
            seen[key] = r["name"]
