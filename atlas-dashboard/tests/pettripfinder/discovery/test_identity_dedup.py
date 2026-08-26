"""PTF-GENERIC-PRE-ACQUISITION-DEDUP-HARDENING-001 -- do not pay twice for one
property.

The factory's duplicate scan ran in phase 13, five phases AFTER the cost plan.
By then the duplicates had been routed twice, bought twice and read twice.
Grand Rapids-Holland's re-census produced 47 duplicate groups over 68 of 163
identities -- a bare OpenStreetMap name and a qualified prior-census name for
one building, each routed to the same page.

What these tests pin is the shape of the verdict, because the conservative
direction is not the same in both directions:

* merging two real hotels is a published defect that costs a re-census;
* refusing to merge two sightings of one hotel costs one duplicate purchase.

So a merge needs a shared signal AND names that agree by token containment, and
everything short of that keeps both rows. The spend protection does NOT depend
on getting identity right: it keys on the PAGE, so two identities that would
fetch one URL cannot both be bought whatever we decide they are.
"""

from __future__ import annotations

from scripts.pettripfinder.acquisition import market_paid_acquisition as MPA
from scripts.pettripfinder.acquisition import market_routing as MR
from scripts.pettripfinder.discovery import identity_dedup as D


def row(key, name, *, url="", address="", zipc="", phone=""):
    return {
        "identity_key": key, "canonical_name": name, "official_url": url,
        "address": address, "postal_code": zipc, "phone": phone,
    }


def verdicts(rows):
    return {(g["signal"], g["verdict"]) for g in D.analyse(rows)["groups"]}


# --------------------------------------------------------------------------- #
# 1-2. One page, two identity keys.
# --------------------------------------------------------------------------- #

class TestOnePageTwoIdentities:

    def test_same_url_two_identity_keys_is_caught(self):
        rows = [row("ac hotel", "AC Hotel", url="https://x.com/ac"),
                row("ac hotel grand rapids downtown",
                    "AC Hotel Grand Rapids Downtown", url="https://x.com/ac")]
        analysis = D.analyse(rows)
        assert ("CANONICAL_URL", D.MERGE) in verdicts(rows)
        assert analysis["merged_identities"] == 1
        # The qualified name is the survivor: it carries more evidence.
        assert analysis["merges"][0]["into"] == "ac hotel grand rapids downtown"

    def test_same_url_incompatible_names_is_held_not_merged(self):
        """At most one of them owns that page -- but we do not know which."""
        rows = [row("sleep inn and suites", "Sleep Inn and Suites",
                    url="https://x.com/p"),
                row("spark by hilton grand rapids", "Spark by Hilton Grand Rapids",
                    url="https://x.com/p")]
        analysis = D.analyse(rows)
        assert ("CANONICAL_URL", D.REVIEW) in verdicts(rows)
        assert analysis["merged_identities"] == 0
        assert analysis["withheld_from_acquisition"] == 1
        assert analysis["identities_out"] == 2, "neither row may be discarded"

    def test_url_comparison_ignores_scheme_www_and_trailing_slash(self):
        rows = [row("a hotel", "A Hotel", url="http://Example.com/p/"),
                row("a hotel downtown", "A Hotel Downtown",
                    url="https://www.example.com/p")]
        assert D.analyse(rows)["merged_identities"] == 1

    def test_same_property_code_two_identities_merges_on_compatible_names(self):
        rows = [row("canopy by hilton", "Canopy by Hilton",
                    url="https://hilton.com/en/hotels/GRRDTDT-canopy/"),
                row("canopy by hilton grand rapids downtown",
                    "Canopy by Hilton Grand Rapids Downtown",
                    url="https://hilton.com/en/hotels/GRRDTDT-canopy/rooms/")]
        analysis = D.analyse(rows)
        assert any(g["signal"] == "PROPERTY_CODE" for g in analysis["groups"])
        assert analysis["merged_identities"] == 1

    def test_same_property_code_across_different_url_paths_is_still_one_page(self):
        """/rooms/ and the overview are one property on the brand's own key, so
        the URL text differing must not let both be bought."""
        rows = [row("canopy", "Canopy",
                    url="https://hilton.com/en/hotels/GRRDTDT-canopy/"),
                row("canopy by hilton grand rapids downtown",
                    "Canopy by Hilton Grand Rapids Downtown",
                    url="https://hilton.com/en/hotels/GRRDTDT-canopy/rooms/")]
        analysis = D.analyse(rows)
        assert any(g["signal"] == "PROPERTY_CODE" for g in analysis["groups"])
        # A one-token name cannot satisfy the containment rule, so this is not
        # auto-merged -- but it is a PAGE signal, so exactly one may be bought.
        assert analysis["merged_identities"] == 0
        assert len(D.payable_keys(rows, analysis)) == 1


# --------------------------------------------------------------------------- #
# 3-4. Premises signals with compatible names.
# --------------------------------------------------------------------------- #

class TestPremisesSignalsWithCompatibleNames:

    def test_same_phone_and_compatible_name_merges(self):
        rows = [row("residence inn holland", "Residence Inn Holland",
                    phone="616-393-6900"),
                row("residence inn by marriott holland",
                    "Residence Inn by Marriott Holland", phone="(616) 393 6900")]
        assert D.analyse(rows)["merged_identities"] == 1

    def test_same_address_and_compatible_name_merges(self):
        rows = [row("embassy suites grand rapids downtown",
                    "Embassy Suites Grand Rapids Downtown",
                    address="710 Monroe Ave NW", zipc="49503"),
                row("embassy suites by hilton grand rapids downtown",
                    "Embassy Suites by Hilton Grand Rapids Downtown",
                    address="710 Monroe Ave NW", zipc="49503")]
        assert D.analyse(rows)["merged_identities"] == 1

    def test_a_spelling_variant_is_not_auto_merged(self):
        """"BlueJay" and "Blue Jay" are one hotel to a reader and two token
        sets to a tokeniser. Deliberately NOT merged: a spelling bridge is
        similarity, and similarity is the one thing that may never merge. The
        closure scan still reports the pair for a human."""
        rows = [row("the bluejay hotel", "The BlueJay Hotel",
                    address="644 Bridge St NW", zipc="49504"),
                row("the blue jay hotel and events",
                    "The Blue Jay Hotel and Events",
                    address="644 Bridge St NW", zipc="49504")]
        analysis = D.analyse(rows)
        assert analysis["merged_identities"] == 0
        assert analysis["identities_out"] == 2


# --------------------------------------------------------------------------- #
# 5-6. Genuinely distinct properties survive.
# --------------------------------------------------------------------------- #

class TestDistinctPropertiesSurvive:

    def test_incompatible_same_address_hotels_remain_distinct(self):
        """A dual-brand building. Two hotels, one address, no defect -- and
        two purchases, because they fetch two different pages."""
        rows = [row("hampton inn louisville east", "Hampton Inn Louisville East",
                    address="1150 Forest Bridge Rd", zipc="40223"),
                row("home2 suites louisville east", "Home2 Suites Louisville East",
                    address="1150 Forest Bridge Rd", zipc="40223")]
        analysis = D.analyse(rows)
        assert ("STREET_AND_POSTAL_CODE", D.DISTINCT) in verdicts(rows)
        assert analysis["merged_identities"] == 0
        assert analysis["withheld_from_acquisition"] == 0
        assert analysis["identities_out"] == 2

    def test_a_shared_building_stays_distinct_when_property_codes_differ(self):
        """The brand is the authority on its own inventory. Differing codes
        outrank a shared address AND compatible names."""
        rows = [row("hampton inn", "Hampton Inn",
                    url="https://hilton.com/en/hotels/AAABBHX-hampton/",
                    address="1150 Forest Bridge Rd", zipc="40223"),
                row("hampton inn louisville east", "Hampton Inn Louisville East",
                    url="https://hilton.com/en/hotels/CCCDDHX-hampton/",
                    address="1150 Forest Bridge Rd", zipc="40223")]
        analysis = D.analyse(rows)
        assert analysis["merged_identities"] == 0, analysis["groups"]
        assert analysis["identities_out"] == 2

    def test_a_shared_brand_alone_never_merges(self):
        """No shared signal at all: two Comfort Inns in one market are two
        hotels until something says otherwise."""
        rows = [row("comfort inn", "Comfort Inn", address="1 A St", zipc="49503"),
                row("comfort inn grandville", "Comfort Inn Grandville",
                    address="2 B St", zipc="49418")]
        assert D.analyse(rows)["groups_found"] == 0

    def test_incompatible_brands_on_one_switchboard_remain_distinct(self):
        """Comfort Inn and Comfort Suites are two brands; the shared line is a
        fact about a phone, not about a building."""
        rows = [row("comfort inn", "Comfort Inn", phone="6166670733"),
                row("comfort suites grandville grand rapids sw",
                    "Comfort Suites Grandville Grand Rapids SW",
                    phone="6166670733")]
        analysis = D.analyse(rows)
        assert ("TELEPHONE", D.DISTINCT) in verdicts(rows)
        assert analysis["merged_identities"] == 0


# --------------------------------------------------------------------------- #
# 7. The prior-census / OSM shape that motivated all of this.
# --------------------------------------------------------------------------- #

class TestPriorAndFreshBareName:

    def test_a_bare_osm_name_merges_into_its_qualified_prior_identity(self):
        rows = [row("ac hotel", "AC Hotel", phone="6167763200"),
                row("ac hotel grand rapids downtown",
                    "AC Hotel Grand Rapids Downtown", phone="6167763200",
                    address="50 Monroe Ave NW", zipc="49503",
                    url="https://marriott.com/en-us/hotels/grrad-ac/")]
        analysis = D.analyse(rows)
        assert analysis["merged_identities"] == 1
        merge, = analysis["merges"]
        assert merge["absorbed"] == "ac hotel"
        assert merge["into"] == "ac hotel grand rapids downtown"

    def test_a_one_token_name_can_never_absorb_anything(self):
        """"Motel" is a subset of half the market."""
        rows = [row("motel", "Motel", phone="6160000000"),
                row("motel 6 grand rapids", "Motel 6 Grand Rapids",
                    phone="6160000000")]
        assert D.analyse(rows)["merged_identities"] == 0


# --------------------------------------------------------------------------- #
# 8-9. The gate actually protects the money.
# --------------------------------------------------------------------------- #

class TestNothingIsPaidForTwice:

    def _entry(self, key, name, url):
        return {
            "identity_key": key, "canonical_name": name, "brand": "B",
            "corridor": "c", "source_url": url, "provider": "brightdata_browser",
            "reader": "r", "routing_state": MR.ROUTED, "ladder": [],
            "fallback_providers": [],
        }

    def test_an_unresolved_duplicate_is_withheld_before_cost_planning(self):
        """8. Held, not discarded: the census keeps both rows and exactly one
        of them is payable."""
        rows = [row("sleep inn and suites", "Sleep Inn and Suites",
                    url="https://x.com/p"),
                row("spark by hilton grand rapids", "Spark by Hilton Grand Rapids",
                    url="https://x.com/p")]
        payable = D.payable_keys(rows)
        assert len(payable) == 1
        assert len(rows) == 2

    def test_two_identity_keys_on_one_url_yield_one_purchase(self):
        """9. The backstop, independent of what the census decided they are."""
        cohort, settled = MPA.derive_cohort(
            [self._entry("ac hotel", "AC Hotel", "https://x.com/ac"),
             self._entry("ac hotel grand rapids downtown",
                         "AC Hotel Grand Rapids Downtown", "https://x.com/ac")],
            {"results": []})
        assert len(cohort) == 1, "one page must not be bought twice"
        assert len(settled) == 1
        assert "pay twice for one answer" in settled[0]["settled_because"]

    def test_two_identity_keys_on_one_property_code_yield_one_purchase(self):
        cohort, settled = MPA.derive_cohort(
            [self._entry("a", "A Hotel",
                         "https://hilton.com/en/hotels/GRRDTDT-a/"),
             self._entry("b", "B Hotel Downtown",
                         "https://hilton.com/en/hotels/GRRDTDT-b/rooms/")],
            {"results": []})
        assert len(cohort) == 1
        assert len(settled) == 1

    def test_distinct_pages_are_both_bought(self):
        """The gate must not suppress real work."""
        cohort, settled = MPA.derive_cohort(
            [self._entry("a", "A", "https://x.com/a"),
             self._entry("b", "B", "https://x.com/b")],
            {"results": []})
        assert len(cohort) == 2
        assert settled == []

    def test_cohort_plus_settled_still_accounts_for_every_routed_identity(self):
        """The invariant the module docstring promises."""
        entries = [self._entry("a", "A", "https://x.com/p"),
                   self._entry("b", "B Downtown", "https://x.com/p"),
                   self._entry("c", "C", "https://x.com/c")]
        cohort, settled = MPA.derive_cohort(entries, {"results": []})
        assert len(cohort) + len(settled) == len(entries)

    def test_a_row_with_no_url_is_never_suppressed_as_a_twin(self):
        """Absence of a URL is not a shared URL."""
        cohort, settled = MPA.derive_cohort(
            [self._entry("a", "A", ""), self._entry("b", "B", "")],
            {"results": []})
        assert len(cohort) == 2
