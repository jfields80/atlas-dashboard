"""Unit tests for the PILOT-PTF-1 ListingDataset converter
(``engines/website_generation/ingestion/listing_dataset_builder.py``).

Pure-function tests only -- no engine chain, no file I/O (fixture data is
inline). See ``tests/website_generation/integration/
test_pettripfinder_launch_package.py`` for the real launch-package proof.
"""

from __future__ import annotations

from engines.website_generation.contracts.enums import ArtifactKind
from engines.website_generation.contracts.versions import SCHEMA_VERSIONS
from scripts.pettripfinder.listing_dataset_builder import (
    build_categories,
    build_listing_dataset,
    build_locations,
)

_CATEGORIES = [{"name": "Hotels", "slug": "hotels"}, {"name": "Parks", "slug": "parks"}]
_LOCATIONS = [{"name": "Columbus", "slug": "columbus-oh", "state": "OH"}]


def _biz(**overrides):
    base = {
        "name": "Acme Inn",
        "category": "Hotels",
        "city": "Columbus",
        "state": "OH",
        "address": "1 Main St",
    }
    base.update(overrides)
    return base


class TestPurity:
    def test_deterministic_same_input_same_output(self):
        seed = [_biz()]
        a = build_listing_dataset(seed_businesses=seed, categories=_CATEGORIES, locations=_LOCATIONS)
        b = build_listing_dataset(seed_businesses=seed, categories=_CATEGORIES, locations=_LOCATIONS)
        assert a.dataset == b.dataset

    def test_input_order_does_not_affect_output(self):
        seed_a = [_biz(name="A", address="1 A St"), _biz(name="B", address="2 B St")]
        seed_b = list(reversed(seed_a))
        a = build_listing_dataset(seed_businesses=seed_a, categories=_CATEGORIES, locations=_LOCATIONS)
        b = build_listing_dataset(seed_businesses=seed_b, categories=_CATEGORIES, locations=_LOCATIONS)
        assert a.dataset.listings == b.dataset.listings


class TestCategoriesAndLocations:
    def test_build_categories_sorted_by_slug(self):
        cats = build_categories([{"name": "Parks", "slug": "parks"}, {"name": "Hotels", "slug": "hotels"}])
        assert [c.slug for c in cats] == ["hotels", "parks"]

    def test_build_locations_sorted_by_slug(self):
        locs = build_locations([{"name": "Dublin", "slug": "dublin-oh", "state": "OH"},
                                 {"name": "Columbus", "slug": "columbus-oh", "state": "OH"}])
        assert [l.slug for l in locs] == ["columbus-oh", "dublin-oh"]


class TestValidDataset:
    def test_single_valid_listing(self):
        result = build_listing_dataset(seed_businesses=[_biz()], categories=_CATEGORIES, locations=_LOCATIONS)
        assert result.ok
        assert len(result.dataset.listings) == 1
        listing = result.dataset.listings[0]
        assert listing.business_name == "Acme Inn"
        assert listing.category_id == "cat-hotels"
        assert listing.location_id == "loc-columbus-oh"

    def test_schema_version_matches_registry(self):
        result = build_listing_dataset(seed_businesses=[_biz()], categories=_CATEGORIES, locations=_LOCATIONS)
        assert result.dataset.schema_version == SCHEMA_VERSIONS[ArtifactKind.LISTING_DATASET]

    def test_listings_ordered_by_category_then_slug(self):
        seed = [
            _biz(name="Z Inn", category="Hotels", address="9 Z St"),
            _biz(name="A Park", category="Parks", address="8 A St"),
            _biz(name="A Inn", category="Hotels", address="7 A St"),
        ]
        result = build_listing_dataset(seed_businesses=seed, categories=_CATEGORIES, locations=_LOCATIONS)
        assert [l.slug for l in result.dataset.listings] == ["a-inn", "z-inn", "a-park"]

    def test_unresolvable_location_leaves_location_id_empty_not_an_error(self):
        result = build_listing_dataset(
            seed_businesses=[_biz(city="Nowhere", state="ZZ")], categories=_CATEGORIES, locations=_LOCATIONS,
        )
        assert result.ok
        assert result.dataset.listings[0].location_id == ""


class TestDedup:
    def test_exact_duplicate_by_address_is_deduplicated(self):
        seed = [
            _biz(name="Sunset Bay Inn", address="123 Sunset Bay Rd"),
            _biz(name="Duplicate Sunset Bay Inn", address="123 Sunset Bay Road"),
        ]
        result = build_listing_dataset(seed_businesses=seed, categories=_CATEGORIES, locations=_LOCATIONS)
        assert result.ok
        assert len(result.dataset.listings) == 1
        assert result.rejected_duplicates

    def test_case_different_duplicate_is_deduplicated(self):
        seed = [_biz(name="Acme Inn"), _biz(name="ACME INN")]
        result = build_listing_dataset(seed_businesses=seed, categories=_CATEGORIES, locations=_LOCATIONS)
        assert result.ok
        assert len(result.dataset.listings) == 1

    def test_winner_is_deterministic_regardless_of_input_order(self):
        seed_a = [_biz(name="Acme Inn"), _biz(name="ACME INN")]
        seed_b = list(reversed(seed_a))
        a = build_listing_dataset(seed_businesses=seed_a, categories=_CATEGORIES, locations=_LOCATIONS)
        b = build_listing_dataset(seed_businesses=seed_b, categories=_CATEGORIES, locations=_LOCATIONS)
        assert a.dataset.listings[0].business_name == b.dataset.listings[0].business_name

    def test_distinct_businesses_are_not_merged(self):
        seed = [_biz(name="Acme Inn", address="1 Main St"), _biz(name="Beta Inn", address="2 Oak Ave")]
        result = build_listing_dataset(seed_businesses=seed, categories=_CATEGORIES, locations=_LOCATIONS)
        assert result.ok
        assert len(result.dataset.listings) == 2
        assert not result.rejected_duplicates


class TestRejections:
    def test_unknown_category_is_rejected(self):
        result = build_listing_dataset(
            seed_businesses=[_biz(category="Spas")], categories=_CATEGORIES, locations=_LOCATIONS,
        )
        assert not result.ok
        assert any("unresolved_category" in e for e in result.errors)

    def test_malformed_rating_is_rejected(self):
        result = build_listing_dataset(
            seed_businesses=[_biz(rating="not-a-number")], categories=_CATEGORIES, locations=_LOCATIONS,
        )
        assert not result.ok
        assert any("malformed_rating" in e for e in result.errors)

    def test_slug_collision_is_rejected(self):
        seed = [_biz(name="A B", address="1 St"), _biz(name="A---B", address="2 St")]
        result = build_listing_dataset(seed_businesses=seed, categories=_CATEGORIES, locations=_LOCATIONS)
        assert not result.ok
        assert any("slug_collision" in e for e in result.errors)

    def test_unsafe_cta_url_is_rejected(self):
        result = build_listing_dataset(
            seed_businesses=[_biz()], categories=_CATEGORIES, locations=_LOCATIONS,
            enrichment_by_key={("acme inn", "columbus", "oh"): {"cta_url": "javascript:alert(1)"}},
        )
        assert not result.ok
        assert any("unsafe_cta_url" in e for e in result.errors)

    def test_unsafe_website_url_is_rejected(self):
        result = build_listing_dataset(
            seed_businesses=[_biz()], categories=_CATEGORIES, locations=_LOCATIONS,
            enrichment_by_key={("acme inn", "columbus", "oh"): {"website_url": "javascript:alert(1)"}},
        )
        assert not result.ok
        assert any("unsafe_website_url" in e for e in result.errors)

    def test_no_partial_output_on_error(self):
        seed = [_biz(name="Good", address="1 St"), _biz(name="Bad", category="Nope", address="2 St")]
        result = build_listing_dataset(seed_businesses=seed, categories=_CATEGORIES, locations=_LOCATIONS)
        assert result.dataset is None

    def test_errors_are_batch_reported_not_first_failure_only(self):
        seed = [_biz(name="Bad1", category="Nope1", address="1 St"),
                _biz(name="Bad2", category="Nope2", address="2 St")]
        result = build_listing_dataset(seed_businesses=seed, categories=_CATEGORIES, locations=_LOCATIONS)
        assert len(result.errors) == 2


class TestRatingConversion:
    def test_decimal_rating_conversion_is_exact(self):
        result = build_listing_dataset(
            seed_businesses=[_biz(rating=4.5)], categories=_CATEGORIES, locations=_LOCATIONS,
        )
        assert result.dataset.listings[0].rating.rating_hundredths == 450

    def test_string_rating_conversion_is_exact(self):
        result = build_listing_dataset(
            seed_businesses=[_biz(rating="4.5")], categories=_CATEGORIES, locations=_LOCATIONS,
        )
        assert result.dataset.listings[0].rating.rating_hundredths == 450

    def test_missing_rating_is_none(self):
        result = build_listing_dataset(seed_businesses=[_biz()], categories=_CATEGORIES, locations=_LOCATIONS)
        assert result.dataset.listings[0].rating is None


class TestReviewCountHonesty:
    def test_unknown_review_count_is_negative_sentinel(self):
        result = build_listing_dataset(
            seed_businesses=[_biz(rating=4.0)], categories=_CATEGORIES, locations=_LOCATIONS,
        )
        assert result.dataset.listings[0].rating.review_count == -1

    def test_explicit_zero_review_count_is_preserved(self):
        result = build_listing_dataset(
            seed_businesses=[_biz(rating=4.0)], categories=_CATEGORIES, locations=_LOCATIONS,
            enrichment_by_key={("acme inn", "columbus", "oh"): {"review_count": 0}},
        )
        assert result.dataset.listings[0].rating.review_count == 0

    def test_real_review_count_is_preserved(self):
        result = build_listing_dataset(
            seed_businesses=[_biz(rating=4.0)], categories=_CATEGORIES, locations=_LOCATIONS,
            enrichment_by_key={("acme inn", "columbus", "oh"): {"review_count": 42}},
        )
        assert result.dataset.listings[0].rating.review_count == 42


class TestProvenanceNotCTA:
    def test_source_url_never_becomes_cta(self):
        result = build_listing_dataset(
            seed_businesses=[_biz(source_url="https://example.com/acme")],
            categories=_CATEGORIES, locations=_LOCATIONS,
        )
        assert result.dataset.listings[0].cta is None

    def test_cta_created_only_from_enrichment_real_destination(self):
        result = build_listing_dataset(
            seed_businesses=[_biz()], categories=_CATEGORIES, locations=_LOCATIONS,
            enrichment_by_key={("acme inn", "columbus", "oh"): {"cta_url": "https://acme-inn.example/book"}},
        )
        cta = result.dataset.listings[0].cta
        assert cta is not None
        assert cta.label == "Visit website"
        assert cta.target_route == "https://acme-inn.example/book"


class TestDescriptionHonesty:
    def test_description_from_pet_policy_and_amenities(self):
        result = build_listing_dataset(
            seed_businesses=[_biz(pet_policy="Dogs welcome", amenities=["dog_park_nearby", "pet_beds"])],
            categories=_CATEGORIES, locations=_LOCATIONS,
        )
        description = result.dataset.listings[0].description
        assert "Dogs welcome" in description
        assert "dog_park_nearby" in description

    def test_no_description_when_no_source_data(self):
        result = build_listing_dataset(seed_businesses=[_biz()], categories=_CATEGORIES, locations=_LOCATIONS)
        assert result.dataset.listings[0].description == ""


class TestContact:
    def test_contact_created_only_from_enrichment(self):
        result = build_listing_dataset(
            seed_businesses=[_biz()], categories=_CATEGORIES, locations=_LOCATIONS,
            enrichment_by_key={("acme inn", "columbus", "oh"): {"phone": "555-0100"}},
        )
        assert result.dataset.listings[0].contact.phone == "555-0100"

    def test_no_contact_when_no_enrichment(self):
        result = build_listing_dataset(seed_businesses=[_biz()], categories=_CATEGORIES, locations=_LOCATIONS)
        assert result.dataset.listings[0].contact is None


class TestAddressDuplicationFix:
    """AES-WEB-002K.2: a seed record's ``address`` field sometimes carries
    the full postal string, redundantly repeating the record's own
    ``city``/``state`` (e.g. "123 Sunset Bay Road, Columbus, OH" alongside
    separate city="Columbus"/state="OH" fields), which downstream rendering
    then joins into a visibly duplicated locality."""

    def test_trailing_locality_stripped(self):
        result = build_listing_dataset(
            seed_businesses=[_biz(address="123 Sunset Bay Road, Columbus, OH", city="Columbus", state="OH")],
            categories=_CATEGORIES, locations=_LOCATIONS,
        )
        assert result.dataset.listings[0].address.street == "123 Sunset Bay Road"

    def test_case_insensitive_trailing_locality_stripped(self):
        result = build_listing_dataset(
            seed_businesses=[_biz(address="123 Sunset Bay Road, columbus, oh", city="Columbus", state="OH")],
            categories=_CATEGORIES, locations=_LOCATIONS,
        )
        assert result.dataset.listings[0].address.street == "123 Sunset Bay Road"

    def test_normal_street_only_value_unchanged(self):
        result = build_listing_dataset(
            seed_businesses=[_biz(address="456 Barkside Ave", city="Dublin", state="OH")],
            categories=_CATEGORIES, locations=_LOCATIONS,
        )
        assert result.dataset.listings[0].address.street == "456 Barkside Ave"

    def test_city_state_fields_still_populated_after_strip(self):
        result = build_listing_dataset(
            seed_businesses=[_biz(address="123 Sunset Bay Road, Columbus, OH", city="Columbus", state="OH")],
            categories=_CATEGORIES, locations=_LOCATIONS,
        )
        address = result.dataset.listings[0].address
        assert address.city == "Columbus"
        assert address.state == "OH"
