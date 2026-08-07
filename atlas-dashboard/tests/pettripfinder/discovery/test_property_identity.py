"""PTF-DISCOVERY -- the four identity defects, each pinned by a test.

An ad-hoc regional census pipeline lost 26 real hotels and mispaired an
unknown number of addresses. The production ``deduplicate()`` pipeline was
never wrong; the ad-hoc one simply skipped its rules. These tests pin the
rules in a form any pipeline can reuse, using the real shapes that failed:
the Destination Cleveland breadcrumb, six Courtyards, four Red Roofs, and
the Fairfield/"field" substring bug that predates all of them.
"""

from __future__ import annotations

import pytest

from scripts.pettripfinder.discovery.property_identity import (
    DISTINCT_PROPERTIES,
    LODGING_BY_NAME,
    LODGING_CONFIRMED,
    NEEDS_ADJUDICATION,
    SAME_PROPERTY_ADDRESS_DISCREPANCY,
    NEEDS_REVIEW,
    NON_LODGING,
    SAME_PROPERTY,
    PropertyIdentityError,
    ambiguous_names,
    assert_distinct_street_identities,
    canonical_property_names,
    classify_lodging,
    compare_identities,
    is_brand_only,
    is_navigation_breadcrumb,
    normalize_phone,
    parse_property_container,
    street_identity,
    validate_pairing,
)

# The real capture shape: chrome, then a breadcrumb naming the PREVIOUS
# property, then this property, then its own Location block.
CONTAINER = """MENU
SEARCH
AREA MAP
CALENDAR
« Back to Courtyard by Marriott (Airport North)
COURTYARD BY MARRIOTT (BEACHWOOD)
VIEW WEBSITE
+ADD TO MY TRIP
Location
3695 Orange Pl.
Beachwood, OH, 44122
216.765.1900
Social
INFORMATION
Hotel
Guest Rooms
"""


# --------------------------------------------------------------------------- #
# 1. Same-node extraction. No positional pairing, ever.
# --------------------------------------------------------------------------- #

class TestPropertyContainer:

    def test_name_and_address_come_from_the_same_container(self):
        r = parse_property_container(CONTAINER, "courtyard-by-marriott-beachwood")
        assert r.display_name == "COURTYARD BY MARRIOTT (BEACHWOOD)"
        assert r.address == "3695 Orange Pl."
        assert r.city == "Beachwood"
        assert r.postal_code == "44122"
        assert r.complete

    def test_the_breadcrumb_is_never_read_as_the_property_name(self):
        """The whole one-row offset in one assertion: the container names the
        PREVIOUS property before it names its own."""
        r = parse_property_container(CONTAINER, "x")
        assert r.previous_in_source == "Courtyard by Marriott (Airport North)"
        assert "Back to" not in r.display_name

    def test_a_container_missing_its_address_is_incomplete_not_paired_onward(self):
        text = CONTAINER.split("Location")[0]
        r = parse_property_container(text, "x")
        assert not r.complete
        assert r.address == "" and r.postal_code == ""
        assert any("Location" in reason for reason in r.incomplete_reasons)

    def test_a_street_line_requires_a_house_number(self):
        """A bare street name is a fragment; accepting one previously gave 57
        Akron hotels the same footer address."""
        text = CONTAINER.replace("3695 Orange Pl.", "Orange Pl.")
        r = parse_property_container(text, "x")
        assert not r.complete
        assert any("house number" in reason for reason in r.incomplete_reasons)

    def test_two_containers_parsed_independently_keep_their_own_addresses(self):
        other = CONTAINER.replace("COURTYARD BY MARRIOTT (BEACHWOOD)",
                                  "COURTYARD BY MARRIOTT (WESTLAKE)") \
                         .replace("3695 Orange Pl.", "25050 Sperry Dr") \
                         .replace("Beachwood, OH, 44122", "Westlake, OH, 44145")
        a = parse_property_container(CONTAINER, "a")
        b = parse_property_container(other, "b")
        assert (a.address, a.postal_code) == ("3695 Orange Pl.", "44122")
        assert (b.address, b.postal_code) == ("25050 Sperry Dr", "44145")

    def test_the_source_id_is_the_containers_own_identifier_not_its_position(self):
        assert parse_property_container(CONTAINER, "slug-from-page-url").source_id \
            == "slug-from-page-url"

    @pytest.mark.parametrize("name", [
        "« Back to Aloft", "� Back to Crowne Plaza", "<< Back to Hampton Inn",
        "Back to Locations"])
    def test_breadcrumbs_are_recognised_whatever_their_encoding(self, name):
        """Batch-001 admitted ten of these as hotels because the leading
        guillemet arrived mangled."""
        assert is_navigation_breadcrumb(name)

    def test_a_real_hotel_name_is_not_mistaken_for_a_breadcrumb(self):
        assert not is_navigation_breadcrumb("Courtyard by Marriott (Beachwood)")
        assert not is_navigation_breadcrumb("Bourbon Street Barrel Room")

    def test_an_area_label_disagreeing_with_the_city_is_reported_not_resolved(self):
        text = CONTAINER.replace("Beachwood, OH, 44122", "Middleburg Heights, OH, 44130")
        warnings = validate_pairing(parse_property_container(text, "x"))
        assert any("area label" in w for w in warnings)


# --------------------------------------------------------------------------- #
# 2. Canonical naming. A disambiguator is only dropped when it disambiguates
#    nothing.
# --------------------------------------------------------------------------- #

class TestCanonicalNaming:

    COURTYARDS = ["Courtyard by Marriott (Airport North)",
                  "Courtyard by Marriott (Beachwood)",
                  "Courtyard by Marriott (Cleveland Airport South)",
                  "Courtyard by Marriott (Cleveland University Circle)",
                  "Courtyard by Marriott (Independence)",
                  "Courtyard by Marriott (Westlake)",
                  "Courtyard by Marriott (Willoughby)"]

    def test_a_shared_base_name_keeps_every_disambiguator(self):
        names = canonical_property_names(self.COURTYARDS)
        assert len(set(names)) == len(self.COURTYARDS)
        assert "Courtyard by Marriott Beachwood" in names
        assert "Courtyard by Marriott" not in names

    def test_a_unique_non_brand_base_name_drops_its_area_label(self):
        """The label really is directory chrome when what remains identifies
        the property on its own."""
        assert canonical_property_names(["Stonehill Hotel (Eastlake)"]) == ["Stonehill Hotel"]
        assert canonical_property_names(["Aurora Inn (Aurora)"]) == ["Aurora Inn"]

    @pytest.mark.parametrize("display,expected", [
        ("Residence Inn (Cleveland Airport/Middleburg Heights)",
         "Residence Inn Cleveland Airport Middleburg Heights"),
        ("Hilton (Cleveland Downtown)", "Hilton Cleveland Downtown"),
        ("AC Hotel (Cleveland Beachwood)", "AC Hotel Cleveland Beachwood"),
        ("Aloft (Beachwood)", "Aloft Beachwood"),
        ("Comfort Suites (Twinsburg)", "Comfort Suites Twinsburg"),
    ])
    def test_a_bare_brand_keeps_its_qualifier_even_when_unique(self, display, expected):
        """"Residence Inn" names a chain, not a hotel. Being the only one in a
        batch is an accident of collection, not evidence -- and seven such
        names survived into a proposed census because uniqueness was the only
        test applied."""
        assert canonical_property_names([display]) == [expected]

    @pytest.mark.parametrize("name,brand_only", [
        ("Residence Inn", True), ("AC Hotel", True), ("Hilton", True),
        ("Comfort Suites", True), ("Great Wolf Lodge", True),
        ("Aloft Beachwood", False), ("Stonehill Hotel", False),
        ("Aurora Inn", False), ("Hotel Cleveland", False),
    ])
    def test_is_brand_only(self, name, brand_only):
        assert is_brand_only(name) is brand_only

    def test_no_arbitrary_brand_only_survivor(self):
        """The exact failure: six Courtyards collapsed into one, and five real
        hotels were then deleted as duplicates."""
        assert ambiguous_names(canonical_property_names(self.COURTYARDS)) == []

    def test_a_shared_base_name_with_no_label_is_disambiguated_from_its_own_city(self):
        names = canonical_property_names(
            ["Staybridge Suites", "Staybridge Suites"], ["Canton", "Mayfield Heights"])
        assert names == ["Staybridge Suites Canton", "Staybridge Suites Mayfield Heights"]

    def test_a_city_hint_already_in_the_name_is_not_repeated(self):
        names = canonical_property_names(
            ["Hampton Inn Canton", "Hampton Inn Massillon"], ["Canton", "Massillon"])
        assert names == ["Hampton Inn Canton", "Hampton Inn Massillon"]

    def test_records_sharing_a_display_name_are_not_collapsed_by_the_return_shape(self):
        """A dict keyed by display name silently loses one of two records --
        which is how the Staybridge collision hid."""
        assert len(canonical_property_names(["Hotel X", "Hotel X"])) == 2

    def test_a_disambiguator_is_never_borrowed_from_a_neighbour(self):
        names = canonical_property_names(
            ["Comfort Inn (Akron South)", "Comfort Inn"], ["Akron", ""])
        assert names[1] == "Comfort Inn"          # no label invented for it
        assert names[0] == "Comfort Inn Akron South"


# --------------------------------------------------------------------------- #
# 3. Dedupe. Street identity is the hard guard.
# --------------------------------------------------------------------------- #

class TestStreetIdentityGuard:

    @pytest.mark.parametrize("brand,streets", [
        ("Courtyard by Marriott", [("3695 Orange Pl.", "44122"), ("7345 Engle Rd.", "44130"),
                                   ("25050 Sperry Dr", "44145"), ("2021 Cornell Rd.", "44106"),
                                   ("5051 West Creek Rd.", "44131"),
                                   ("35103 Maplegrove Rd.", "44094")]),
        ("Red Roof Inn", [("4166 State Route 306", "44094"), ("6020 Quarry Lane", "44131"),
                          ("17555 Bagley Rd.", "44130"), ("29595 Clemens Rd.", "44145")]),
        ("Hampton Inn & Suites", [("7074 Engle Rd.", "44130"), ("6020 Jefferson Dr.", "44131"),
                                  ("800 Mondial Parkway", "44241")]),
        ("Residence Inn by Marriott", [("5280 Broadmoor Cir NW", "44709"),
                                       ("1914 E. 101 St.", "44106"),
                                       ("19149 East Bagley Rd.", "44130")]),
        ("Holiday Inn", [("6001 Rockside Rd.", "44131"), ("16330 Snow Rd.", "44142"),
                         ("3589 Park E Dr.", "44122")]),
    ])
    def test_one_brand_at_many_streets_stays_many_hotels(self, brand, streets):
        """Every group the broken pipeline collapsed. Same name, different
        street: distinct properties, not duplicates."""
        keys = [street_identity(a, z) for a, z in streets]
        assert len(set(keys)) == len(streets)
        for other in keys[1:]:
            verdict, _ = compare_identities(brand, keys[0], brand, other)
            assert verdict == DISTINCT_PROPERTIES

    def test_same_name_at_the_same_street_is_one_property(self):
        key = street_identity("35600 Detroit Rd", "44011")
        verdict, _ = compare_identities("Cambria Hotel & Suites", key,
                                        "Cambria Hotel & Suites", key)
        assert verdict == SAME_PROPERTY

    def test_two_names_at_one_address_are_reviewed_never_auto_merged(self):
        """Gervasi Casa and Villas, and BrewDog DogHouse and DogTap."""
        key = street_identity("1700 55th Street NE", "44721")
        verdict, reason = compare_identities("The Casa at Gervasi Vineyard", key,
                                             "The Villas at Gervasi Vineyard", key)
        assert verdict == NEEDS_ADJUDICATION
        assert "never an automatic merge" in reason

    def test_rebrand_evidence_turns_a_name_match_into_an_adjudication(self):
        verdict, _ = compare_identities(
            "Days Inn", street_identity("4742 Brecksville Rd", "44286"),
            "Days Inn", street_identity("100 Other St", "44286"), rebrand_evidence=True)
        assert verdict == NEEDS_ADJUDICATION

    def test_street_identity_normalises_spelling_but_not_the_house_number(self):
        assert street_identity("3695 Orange Place", "44122") == \
            street_identity("3695 Orange Pl.", "44122")
        assert street_identity("3695 Orange Pl.", "44122") != \
            street_identity("3697 Orange Pl.", "44122")
        assert street_identity("3695 Orange Pl.", "44122") != \
            street_identity("3695 Orange Pl.", "44130")

    def test_the_guard_refuses_a_name_spanning_two_streets(self):
        records = [{"canonical_name": "Staybridge Suites",
                    "street_identity": street_identity("3879 Everhard Rd NW", "44709")},
                   {"canonical_name": "Staybridge Suites",
                    "street_identity": street_identity("6103 Landerhaven Dr", "44124")}]
        with pytest.raises(PropertyIdentityError, match="distinct properties"):
            assert_distinct_street_identities(records)

    def test_the_guard_allows_genuinely_distinct_identities(self):
        assert_distinct_street_identities([
            {"canonical_name": "Staybridge Suites Canton",
             "street_identity": street_identity("3879 Everhard Rd NW", "44709")},
            {"canonical_name": "Staybridge Suites Mayfield Heights",
             "street_identity": street_identity("6103 Landerhaven Dr", "44124")}])


# --------------------------------------------------------------------------- #
# 4. Venue exclusion, without substring overreach.
# --------------------------------------------------------------------------- #

class TestLodgingClassification:

    @pytest.mark.parametrize("name", [
        "Fairfield Inn & Suites Cleveland Airport", "Fairfield Inn Akron South",
        "Fairfield Inn & Suites by Marriott Canton"])
    def test_fairfield_is_never_discarded_by_a_substring_rule(self, name):
        """A venue filter once keyed on the fragment 'field' and deleted every
        Fairfield Inn in the market."""
        state, _ = classify_lodging(name)
        assert state == LODGING_BY_NAME

    @pytest.mark.parametrize("name", [
        "Hampton Inn (North Olmsted/Cleveland Airport)", "Travelodge (Cleveland Airport)",
        "Courtyard by Marriott (Beachwood)", "Aloft (Beachwood)",
        "Four Points by Sheraton Cleveland - Eastlake", "Red Roof Inn (Independence)"])
    def test_real_hotels_classify_as_lodging(self, name):
        assert classify_lodging(name)[0] == LODGING_BY_NAME

    @pytest.mark.parametrize("name,expected", [
        ("Courtyard Cafe", NON_LODGING),
        ("Skinny's Bar & Grill", NON_LODGING),
        ("Talespinner Children's Theatre", NON_LODGING),
        ("Baldwin Wallace University: George Finnie Stadium", NON_LODGING),
        ("Eliot's Bar (Hilton Cleveland Downtown)", NON_LODGING),
        ("The Greatroom Restaurant at Marriott Key Tower", NON_LODGING),
    ])
    def test_venues_are_excluded(self, name, expected):
        assert classify_lodging(name)[0] == expected

    def test_a_venue_inside_a_hotel_is_not_a_hotel(self):
        """'Bar (Hilton ...)' names where the bar is, not what it is."""
        state, reason = classify_lodging("Eliot's Bar (Hilton Cleveland Downtown)")
        assert state == NON_LODGING and "bar" in reason

    def test_hampton_hills_mountain_bike_area_is_not_a_hotel(self):
        """It reached the invalid census as hotel identity."""
        assert classify_lodging("Hampton Hills Mountain Bike Area")[0] != LODGING_BY_NAME

    def test_a_structured_lodging_section_is_authoritative(self):
        state, reason = classify_lodging("Cambria Hotel & Suites", ["Guest Rooms"])
        assert state == LODGING_CONFIRMED and "Guest Rooms" in reason

    @pytest.mark.parametrize("name", [
        "Kent State University Hotel & Conference Center",
        "1833 Restaurant at the Hotel at Oberlin"])
    def test_an_ambiguous_name_is_reviewed_not_silently_excluded(self, name):
        """Excluding a real hotel is as costly as admitting a restaurant, so
        ambiguity resolves to review in both directions."""
        assert classify_lodging(name)[0] == NEEDS_REVIEW

    def test_an_unrecognised_name_is_held_for_review(self):
        assert classify_lodging("Saffron Patch West")[0] == NEEDS_REVIEW

    @pytest.mark.parametrize("name", [
        "Bourbon Street Barrel Room Hotel",     # 'bar' inside 'Barrel'
        "Parkinson Suites",                     # 'park' inside 'Parkinson'
        "Innovation Inn",                       # 'inn' inside 'Innovation'
        "Springfield Inn",                      # the 'field' bug's sibling
        "Centerville Lodge",                    # 'center' inside 'Centerville'
    ])
    def test_a_vocabulary_word_inside_a_longer_word_never_fires(self, name):
        """The vocabularies are matched at word boundaries. A rule that read
        fragments is precisely what deleted every Fairfield Inn, so these
        names must classify on their real head noun, not on a substring."""
        assert classify_lodging(name)[0] == LODGING_BY_NAME

    def test_every_vocabulary_entry_is_a_whole_word_or_phrase(self):
        from scripts.pettripfinder.discovery import property_identity as pi
        for noun in pi.LODGING_HEAD_NOUNS + pi.NON_LODGING_HEAD_NOUNS + pi.LODGING_BRANDS:
            assert noun == noun.strip() and len(noun) >= 2


# --------------------------------------------------------------------------- #
# 5. Telephone as same-property evidence.
# --------------------------------------------------------------------------- #

class TestPhoneIdentity:

    @pytest.mark.parametrize("raw", [
        "330.405.4488", "(330) 405-4488", "330-405-4488", "1-330-405-4488",
        " 3304054488 "])
    def test_one_number_written_many_ways_is_one_key(self, raw):
        assert normalize_phone(raw) == "3304054488"

    @pytest.mark.parametrize("raw", ["", "n/a", "12345", "call us"])
    def test_a_non_number_yields_no_key(self, raw):
        assert normalize_phone(raw) == ""

    def test_a_shared_number_with_a_differing_house_number_is_one_property(self):
        """One Comfort Suites reached a proposed census twice, as 2715 and
        2716 Creekside Dr, because the two sources transcribed the house
        number differently. Two hotels do not share a telephone line."""
        verdict, reason = compare_identities(
            "Comfort Suites Twinsburg", street_identity("2715 Creekside Dr", "44087"),
            "Comfort Suites Twinsburg", street_identity("2716 Creekside Dr", "44087"),
            phone_a="330.963.5909", phone_b="(330) 963-5909")
        assert verdict == SAME_PROPERTY_ADDRESS_DISCREPANCY
        assert "address" in reason

    def test_a_shared_number_with_different_names_is_adjudicated_not_merged(self):
        verdict, _ = compare_identities(
            "Clarion Inn and Conference Center", street_identity("6625 Dean Memorial Pkwy", "44236"),
            "The Norwood Inn", street_identity("6625 Dean Memorial Parkway", "44236"),
            phone_a="330.653.9191", phone_b="330-653-9191")
        assert verdict in (NEEDS_ADJUDICATION, SAME_PROPERTY)

    def test_no_phone_leaves_the_street_rule_untouched(self):
        """Absent phones must not weaken the street guard."""
        verdict, _ = compare_identities(
            "Courtyard by Marriott", street_identity("3695 Orange Pl.", "44122"),
            "Courtyard by Marriott", street_identity("7345 Engle Rd.", "44130"))
        assert verdict == DISTINCT_PROPERTIES

    def test_different_numbers_at_one_address_stay_a_review(self):
        key = street_identity("1700 55th Street NE", "44721")
        verdict, _ = compare_identities("The Casa at Gervasi Vineyard", key,
                                        "The Villas at Gervasi Vineyard", key,
                                        phone_a="330.497.1000", phone_b="330.497.2000")
        assert verdict == NEEDS_ADJUDICATION


# --------------------------------------------------------------------------- #
# 6. Businesses that contain a lodging noun but are not lodging.
# --------------------------------------------------------------------------- #

class TestDecisiveNonLodging:

    @pytest.mark.parametrize("name", [
        "The Barkley Pet Hotel & Day Camp", "Pet Resort of Cleveland",
        "Akron Boarding Kennel", "Fido's Dog Hotel"])
    def test_animal_boarding_is_not_a_hotel(self, name):
        """"The Barkley Pet Hotel & Day Camp" reached a proposed hotel census
        because "Hotel" was the only word any rule looked at."""
        state, reason = classify_lodging(name)
        assert state == NON_LODGING
        assert "not transient lodging for people" in reason

    def test_a_decisive_phrase_outranks_even_structured_evidence(self):
        assert classify_lodging("The Barkley Pet Hotel", ["Guest Rooms"])[0] == NON_LODGING

    @pytest.mark.parametrize("name", [
        "Roost Cleveland - Apartment Hotel", "Hotel Cleveland",
        "The Lakehouse Inn & Winery", "Aurora Inn"])
    def test_real_lodging_is_untouched_by_the_decisive_list(self, name):
        assert classify_lodging(name)[0] in (LODGING_BY_NAME, LODGING_CONFIRMED)

    def test_the_decisive_list_stays_short_and_phrasal(self):
        from scripts.pettripfinder.discovery import property_identity as pi
        for phrase in pi.DECISIVE_NON_LODGING:
            assert phrase == phrase.strip().lower() and len(phrase) >= 6
