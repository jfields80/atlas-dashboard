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

from pettripfinder.market_state import current
from pettripfinder.market_state import current
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
#:
#: PTF-DAYTON-CANDIDATE-PROMOTION-001 moved 33 -> 44 and 6 -> 7 by promoting the
#: reviewed dayton-recovery-002 candidates: eleven pet-friendly identities and
#: Hotel Versailles's affirmative no-pets refusal. Two of the fourteen proposed
#: candidates were NOT promoted (both Wyndham marketing-blurb records, readiness
#: POLICY_PARTIAL) and remain proposals.
#:
#: PTF-DAYTON-WORK-BROWSER-INTEGRATION-001 moved 44 -> 47 and 7 -> 8. Nothing in
#: that work order publishes from the ChatGPT Work browser transcription, which
#: carries no artifact of any page. What it did was point at four hash-verified
#: captures this repository already held or fetched first-party while verifying
#: a routing proposal: two Best Westerns that dayton_recovery_002_closeout had
#: written off as "bestwestern.com 403" while an attended capture of each sat on
#: disk, a fourth Extended Stay America, and Best Western Celina's refusal.
#: PTF-DAYTON-OH-HARDENED-APPLICATION-002 moved 47 -> 54 and 8 -> 24, applying
#: the 23-row clean inventory PTF-DAYTON-OH-HARDENED-REVALIDATION-001 recovered
#: at $0 through the attended lane. Every applied row is bound to its own
#: property's page on that page's premises and was re-read by the canonical
#: reader at application time. The census did NOT move: it is still 129.
#: PTF-FACTORY-THROUGHPUT-HARDENING-001: these are CURRENT-state counts and
#: are read from the one reviewed pin (tests/pettripfinder/pins/market_state.json)
#: rather than restated here. The history above stays as the record of how
#: they moved; the next order that moves Dayton edits the pin, not this file.
_NOW = current(DAYTON)
ACCEPTED = _NOW.pet_friendly
NO_PETS = _NOW.verified_no_pets
HELD = 6
CENSUS = _NOW.census


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
            # PTF-POLICY-SCHEMA-MIGRATION-001: evidence entries keep the field
            # names they were captured under -- their text is never rewritten --
            # so a canonical fact is checked against the legacy name it came
            # from. The protection is unchanged: every published fact must be
            # traceable to a quote that appears in the captured page.
            aliases = {"species": "species_allowed",
                       "combined_weight_limit": "weight_limit_combined",
                       "dimension_constraints": "general_restrictions"}
            for field in hotel["facts"]:
                source_field = aliases.get(field, field)
                assert source_field in evidence,                     "%s: %s has no evidence" % (hotel["name"], field)
                assert " ".join(evidence[source_field].split()).lower() in page, (
                    "%s: %s quote is not in the captured page text"
                    % (hotel["name"], field))

    def test_withheld_fields_are_recorded_and_absent_from_facts(self, facts):
        for hotel in facts["hotels"]:
            for field, decision in (hotel.get("withheld_fields") or {}).items():
                assert field not in hotel["facts"], (
                    "%s: %s is both withheld and published" % (hotel["name"], field))
                # 1.2 replaced bare prose with a reason CODE plus the sentence.
                assert decision["reason_code"], hotel["name"]
                assert len(decision["reason"]) > 20, "a withheld field needs a real reason"

    def test_no_invented_money_or_weight_units(self, facts):
        for hotel in facts["hotels"]:
            f = hotel["facts"]
            if "pet_fee" in f:
                assert isinstance(f["pet_fee"]["amount_cents"], int), hotel["name"]
                assert f["pet_fee"]["currency"] == "USD", hotel["name"]
            if "weight_limit" in f:
                assert f["weight_limit"]["unit"] in ("lb", "kg"), hotel["name"]
                # 1.2 removed the overload: {lt, lte} only, and the scope that
                # used to be smuggled into this slot is its own field.
                assert f["weight_limit"]["operator"] in ("lt", "lte"), hotel["name"]
                assert f["weight_limit"]["scope"] == "per_pet", hotel["name"]

    def test_a_fee_cap_is_a_structure_not_a_display_string(self, facts):
        """A cap that arrives as "$75.00 per stay" reaches the detail renderer
        as a str and is asked for .get("amount"). Two properties carry one."""
        caps = [h for h in facts["hotels"] if "fee_cap" in h["facts"]]
        assert len(caps) == 2
        for hotel in caps:
            cap = hotel["facts"]["fee_cap"]
            assert isinstance(cap, dict), hotel["name"]
            assert cap["amount_cents"] == 7500 and cap["basis"] == "per_stay"
            # A cap states its OWN qualifiers or says it has none.
            assert cap["qualifier_stated"] is True, hotel["name"]
            # the ceiling is NOT the rate
            assert hotel["facts"]["pet_fee"]["amount_cents"] == 2500


class TestContradictionsArePreservedNotResolved:

    def test_springhill_troy_publishes_no_fee(self, facts):
        """Its page shows "Per Stay: $125.00" beside a $75/$150/$250 ladder
        containing no $125 band. Picking one would invent a price."""
        h = next(x for x in facts["hotels"] if x["key"] == "springhill suites troy dayton")
        assert "pet_fee" not in h["facts"] and "fee_tiers" not in h["facts"]
        assert "pet_fee" in h["withheld_fields"]
        # what IS supported still publishes
        # "Dogs only, no cats" is a refusal, and 1.2 records it as one
        # rather than leaving cats merely unmentioned.
        assert h["facts"]["species"] == {"dogs": "accepted",
                                         "cats": "prohibited"}
        assert h["facts"]["weight_limit"]["value"] == 50

    def test_towneplace_beavercreek_publishes_no_fee(self, facts):
        """"$100.00 per stay" and "$20.00 per night" are listed as separate
        rows; they coincide only for a five-night stay."""
        h = next(x for x in facts["hotels"]
                 if x["key"] == "towneplace suites by marriott dayton beavercreek")
        assert "pet_fee" not in h["facts"]
        assert h["facts"]["weight_limit"]["value"] == 75

    def test_hilton_garden_inn_beavercreek_computes_no_additive_total(self, facts):
        """"$75(1-5 nights) additional $75(5+ night)" is an add-on. The worker
        recorded a $150 second band; no total is asserted here."""
        h = next(x for x in facts["hotels"] if x["key"] == "hilton garden inn dayton beavercreek")
        assert h["facts"]["pet_fee"]["amount_cents"] == 7500
        assert "fee_tiers" not in h["facts"]
        assert "150" not in json.dumps(h["facts"])
        # The unresolved "additional $75" survives where source wording belongs
        # -- in the evidence array. PTF-DAYTON-RECERTIFICATION-001 Pass B took
        # it OUT of general_restrictions: a fee_tiers withholding cannot mean
        # anything while the same unresolved amounts are published as prose on
        # the very same profile. What the record must never do is assert a
        # total, and it still does not.
        assert "general_restrictions" in h["facts"]
        assert "$" not in h["facts"]["general_restrictions"]
        assert any("additional" in e["quote"] for e in h["evidence"])


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
        assert h["facts"]["pet_fee"]["scope"] == "per_pet"
        assert "per pet" in h["evidence_quote"]

    def test_no_other_hampton_claims_a_fee_scope(self, facts):
        """Six other Hampton/Hilton-brand properties in this market show the
        same fee shape and never say "per pet". The scope stays where the words
        are."""
        others = [h for h in facts["hotels"]
                  if "hampton" in h["key"] and h["key"] != "hampton inn troy"]
        assert len(others) >= 5
        for h in others:
            # Absent, not withheld: these pages say nothing about scope, and
            # Phase F removed the 110 entries that merely restated a silence.
            assert not (h["facts"].get("pet_fee") or {}).get("scope"), h["name"]
            assert "fee_scope" not in (h.get("withheld_fields") or {}), h["name"]


class TestNegativeFactsNeedArtifactsToo:

    def test_every_dayton_exclusion_quotes_an_affirmative_refusal(self):
        """A refusal must be the property's own words, in one of the two shapes
        a property actually states one.

        PTF-DAYTON-CANDIDATE-PROMOTION-001: this used to accept only the PROSE
        shape ("no pets" / "not allowed"). Hotel Versailles refuses in the
        STRUCTURED shape instead -- ``"petsAllowed": false`` on the ``@type:
        Hotel`` node of its own JSON-LD, with no visible pet text anywhere on
        the page. That shape was already accepted authority in this repository
        (two Columbus Best Western exclusions applied by
        PTF-NEGATIVE-EVIDENCE-P0-001 carry exactly it), so the narrower Dayton
        check was wrong about the standard, not about Versailles. Broadening it
        is the honest fix; paraphrasing a prose refusal onto a page that states
        none would have been inventing evidence to satisfy a lexical test.

        PTF-DAYTON-WORK-BROWSER-INTEGRATION-001 widens the PROSE arm once more,
        for the same reason and not a new one. Best Western Celina's page says
        "Pets are not accepted." in the same PET POLICY slot where its four
        sibling captures state a nightly pet rate. That is as affirmative a
        refusal as a page can make; the old pattern simply did not list the verb
        the property used. Note that this record deliberately does NOT cite the
        structured arm even though its JSON-LD also reads false: that flag reads
        false on every Best Western page captured here, including four that
        charge for dogs, so it is brand boilerplate. See
        ``scripts.pettripfinder.integrate_dayton_work_browser_001.
        best_western_pets_allowed_survey``.
        """
        for e in load_exclusions():
            if e.get("market_id") != DAYTON:
                continue
            quote = " ".join(e["evidence_quote"].split()).lower()
            prose = re.search(r"no pets|not (allowed|permitted|accepted)", quote) is not None
            structured = re.search(r'"?petsallowed"?\s*:\s*false', quote) is not None
            assert prose or structured, e["canonical_name"]
            assert e["source_hash"], e["canonical_name"]

    def test_no_dayton_exclusion_rests_on_silence(self):
        """The distinction the exclusion authority exists to hold: an unanswered
        capture is not a refusal. Every Dayton no-pets record must name a source
        and carry a hash of the artifact the quote came from."""
        for e in load_exclusions():
            if e.get("market_id") != DAYTON:
                continue
            assert e["source_url"], e["canonical_name"]
            assert len(e["source_hash"]) >= 64, e["canonical_name"]
            assert e["exclusion_state"] == "VERIFIED_NO_PETS", e["canonical_name"]

    def test_hie_troy_is_excluded_only_now_that_evidence_exists(self):
        """The invariant is unchanged; the evidence caught up with it.

        The worker had counted Troy VERIFIED_NO_PETS on a research-agent
        assertion with no quote, no capture and no hash, so it went back to
        unresolved rather than being grandfathered -- and this test asserted its
        ABSENCE from the registry for as long as that was the whole story.
        PTF-DAYTON-OH-HARDENED-APPLICATION-002 admitted it on evidence the
        earlier pass did not have: the property's own page states "No, pets are
        not allowed at Holiday Inn Express & Suites Troy", bound to the census
        row on street number, postal code and telephone, with the document
        sha256 recorded. So the assertion flips, and what it now guards is the
        thing that always mattered -- the record exists BECAUSE it carries an
        artifact, not despite carrying none.
        """
        hits = [e for e in load_exclusions()
                if normalize_name(e["canonical_name"])
                == normalize_name("Holiday Inn Express & Suites Troy")]
        assert len(hits) == 1
        record = hits[0]
        assert record["exclusion_state"] == "VERIFIED_NO_PETS"
        assert len(record["source_hash"]) >= 64, "a refusal needs the artifact's hash"
        assert record["source_url"]
        assert re.search(r"not allowed", record["evidence_quote"], re.I),             "the quote must be the property's own refusal"

    def test_the_census_still_records_it_for_a_later_capture(self, census):
        hit = [h for h in census["hotels"]
               if normalize_name(h["canonical_name"])
               == normalize_name("Holiday Inn Express & Suites Troy")]
        assert len(hit) == 1, "the property is retained, not deleted"


class TestThePromotedRecoveryCandidates:
    """PTF-DAYTON-CANDIDATE-PROMOTION-001. What review changed about the
    fourteen proposed candidates, pinned to the records so it cannot drift."""

    def test_marketing_language_still_never_publishes(self, facts):
        """POLICY_PARTIAL never publishes -- but a better source can replace it.

        Both Wyndhams were POLICY_PARTIAL on the evidence PTF-DAYTON-CANDIDATE-
        PROMOTION-001 had: marketing language ("you can bring your pet for an
        extra nightly fee") without a stated policy. That rule is unchanged and
        is still asserted below.

        The Baymont now publishes because the marketing blurb is no longer its
        best source. PTF-DAYTON-OH-HARDENED-REVALIDATION-001 opened the
        property's own Hotel Policies dialog and read its operative PET &
        SERVICE ANIMAL POLICY section: "A maximum of 2 pets allowed up to 50 lbs
        for a non-refundable charge of 25.00 USD per pet per night." That is a
        stated policy, and it publishes on its own terms with a fee, a weight
        limit, a count and a quote.

        The Wingate has no such read and MUST still be absent.
        """
        from scripts.pettripfinder.policy import readiness as RD

        keys = {h["key"] for h in facts["hotels"]}
        assert normalize_name("Wingate by Wyndham Dayton North") not in keys
        assert "POLICY_PARTIAL" not in RD.PUBLISHABLE_STATES

        baymont = [h for h in facts["hotels"]
                   if h["key"] == normalize_name("Baymont by Wyndham Dayton North")]
        assert len(baymont) == 1, "published from the Hotel Policies dialog, not the blurb"
        quotes = " ".join(e["quote"] for e in baymont[0]["evidence"])
        assert "25.00 USD" in quotes and "50 lbs" in quotes,             "it publishes on the stated policy, not on marketing language"

    def test_extended_stay_publishes_no_fee_and_no_weight(self, facts):
        """The fee is a tiered CLEANING fee ($25/day for six nights, then
        $15/day); the size limit is dimensional (36 inches), not weight."""
        esa = [h for h in facts["hotels"] if h["key"].startswith("extended stay america")]
        # 3 -> 4: PTF-DAYTON-WORK-BROWSER-INTEGRATION-001 added Select Suites
        # Dayton - Miamisburg, whose page serves the identical Pet Policy block.
        # It is held to the identical standard, which is the point of asserting
        # over the whole family rather than over a list of three names.
        assert len(esa) == 4
        for h in esa:
            assert "pet_fee" not in h["facts"], h["name"]
            assert "weight_limit" not in h["facts"], h["name"]
            assert h["facts"]["pet_count_limit"] == 2
            assert h["facts"]["pet_count_scope"] == "room"

    def test_extended_stay_general_restrictions_is_one_contiguous_sentence(self, facts):
        """It used to be fee_sentence + " " + size_sentence -- two verbatim spans
        ~9,000 characters apart in the capture, joined into a value that is a
        span of no page. The published value must be inside the policy block,
        which is what the page actually said, contiguously."""
        for h in facts["hotels"]:
            if not h["key"].startswith("extended stay america"):
                continue
            gr = " ".join(h["facts"]["general_restrictions"].split())
            assert "36 inches" in gr and "cleaning fee" not in gr, h["name"]
            assert gr in " ".join(h["evidence_quote"].split()), h["name"]

    def test_celina_withholds_a_fee_its_own_page_contradicts(self, facts):
        """The description says to call the hotel for fees; the Policies section
        states a flat $10 per pet per night. Picking one resolves a contradiction
        the property has not resolved."""
        h = next(x for x in facts["hotels"]
                 if x["key"] == normalize_name("Americas Best Value Inn Celina"))
        assert "pet_fee" not in h["facts"] and "pet_fee" in h["withheld_fields"]
        assert "10" not in json.dumps(h["facts"])

    def test_only_the_cobblestone_properties_claim_a_species(self, facts):
        """"Dog Friendly" in as many words is a species. "pets" never is."""
        promoted = {"cobblestone hotel and suites bellefontaine",
                    "cobblestone hotel and suites eaton",
                    "cobblestone hotel and suites urbana",
                    "cobblestone hotel and suites indian lake russells point"}
        for h in facts["hotels"]:
            if h["key"] in promoted:
                assert h["facts"]["species"] == {"dogs": "accepted"}, h["name"]

    def test_urbana_does_not_inherit_its_siblings_fee(self, facts):
        """Three Cobblestone pages state "$25/dog per night" in the policies
        block; Urbana's leaves that slot empty. Silence is not a price."""
        h = next(x for x in facts["hotels"]
                 if x["key"] == "cobblestone hotel and suites urbana")
        assert "pet_fee" not in h["facts"]
        assert "25" not in json.dumps(h["facts"])
        priced = [x for x in facts["hotels"]
                  if x["key"].startswith("cobblestone") and "pet_fee" in x["facts"]]
        assert len(priced) == 3
        for x in priced:
            assert x["facts"]["pet_fee"]["amount_cents"] == 2500

    def test_hotel_versailles_is_excluded_not_published(self, facts):
        """The one negative finding in the batch. It must be in the exclusion
        registry and absent from the published package -- the two states this
        authority exists to keep apart."""
        key = normalize_name("Hotel Versailles")
        assert key not in {h["key"] for h in facts["hotels"]}
        rec = next(e for e in load_exclusions()
                   if normalize_name(e["canonical_name"]) == key)
        assert rec["market_id"] == DAYTON
        assert rec["exclusion_state"] == "VERIFIED_NO_PETS"
        assert rec["evidence_quote"] == '"petsAllowed": false'


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
        # Cleveland moved 19 -> 21 under its OWN integration
        # (PTF-CLEVELAND-POLICY-CAPTURE-INTEGRATION-003); Dayton did not
        # move it, which is what this test defends.
        assert len([r for r in rows if r.get("market_id") == CLEVELAND]) == \
            current(CLEVELAND).profiles

    def test_columbus_still_has_exactly_fourteen_no_pets(self):
        cbus = [e for e in load_exclusions()
                if e.get("market_id") == COLUMBUS
                and e["exclusion_state"] == "VERIFIED_NO_PETS"]
        assert len(cbus) == current(COLUMBUS).verified_no_pets

    def test_cleveland_still_has_exactly_eight_no_pets(self):
        cle = [e for e in load_exclusions()
               if e.get("market_id") == CLEVELAND
               and e["exclusion_state"] == "VERIFIED_NO_PETS"]
        assert len(cle) == current(CLEVELAND).verified_no_pets

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
