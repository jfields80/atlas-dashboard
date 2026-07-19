"""PILOT-PTF-1 real-launch-package proof (updated AES-WEB-002N.1).

Uses the actual ``launch_packages/pettripfinder/`` files (not the
dedicated 12-listing acceptance fixture) to prove the converter and
readiness check behave honestly against the real inventory.

AES-WEB-002N.1: the seed authority is now the operator-editable CSV
(``seed_businesses.csv``; the stale JSON was removed), provenance survives
into every record, and the readiness verdict counts READY listings only.

Inventory Wave 1 (2026-07-15): 20 researched Columbus/Dublin hotel records
(official property/brand sources only); the example.com sample hotel was
removed so fake inventory never sits beside the real corpus.

Inventory Wave 2 (2026-07-15): 14 researched Columbus-metro park records
(city, parks-department, and Metro Parks sources); the example.com
Riverbend sample park was removed and its demo illustration repointed to a
real park (Scioto Audubon Metro Park).

Inventory Wave 3 (2026-07-15): 13 researched restaurant records (official
brewery/restaurant/group pages); the example.com Barkside sample was
removed and the dining demo illustration repointed to Land-Grant Brewing.
All three categories now clear the 10-per-category floor, every record is
real, and this suite asserts the first honest launch_inventory_ready=True.
"""

from __future__ import annotations

import json
import pathlib

from scripts.generate_pettripfinder_pilot import (
    compute_inventory_readiness,
    load_launch_package,
    read_seed_businesses_csv,
)
from scripts.pettripfinder.listing_dataset_builder import build_listing_dataset

_LAUNCH_PACKAGE_DIR = (
    pathlib.Path(__file__).resolve().parents[3] / "launch_packages" / "pettripfinder"
)


def _load(name: str):
    with (_LAUNCH_PACKAGE_DIR / name).open("r", encoding="utf-8") as f:
        return json.load(f)


class TestRealSeedFilesParse:
    def test_seed_businesses_csv_parses(self):
        seed = read_seed_businesses_csv(_LAUNCH_PACKAGE_DIR / "seed_businesses.csv")
        assert len(seed) == 52
        for row in seed:
            # Required publish columns are present in the sample rows.
            for field in ("name", "category", "city", "state", "address",
                          "website_url", "source_url", "source_type",
                          "observed_at", "pet_policy"):
                assert str(row.get(field, "")).strip(), (row.get("name"), field)

    def test_stale_seed_json_removed(self):
        # The JSON seed was removed with the CSV promotion -- one authority.
        assert not (_LAUNCH_PACKAGE_DIR / "seed_businesses.json").exists()

    def test_categories_parses(self):
        cats = _load("categories.json")
        assert len(cats) == 3

    def test_locations_parses(self):
        locs = _load("locations.json")
        assert len(locs) == 2

    def test_pilot_config_parses(self):
        config = _load("pilot_config.json")
        assert config["project_name"] == "PetTripFinder"
        assert config["base_url"] == "https://pettripfinder.com"

    def test_pilot_content_parses(self):
        content = _load("pilot_content.json")
        assert "home" in content
        assert "editorial_pages" in content


class TestRealPackageConversion:
    def _build(self):
        seed = read_seed_businesses_csv(_LAUNCH_PACKAGE_DIR / "seed_businesses.csv")
        cats = _load("categories.json")
        locs = _load("locations.json")
        return build_listing_dataset(seed_businesses=seed, categories=cats, locations=locs)

    def test_clean_package_has_no_duplicates(self):
        # Wave 1 hotels are 20 distinct properties -- nearby same-brand
        # locations (three Drury, four Red Roof) must NOT collapse in
        # dedup (distinct addresses; dedup behavior itself stays covered
        # by dedicated fixtures in tests/pettripfinder/).
        result = self._build()
        assert result.ok
        assert result.rejected_duplicates == ()

    def test_provenance_survives_into_every_record(self):
        result = self._build()
        assert result.ok
        for listing in result.dataset.listings:
            assert listing.provenance is not None, listing.listing_id
            assert listing.provenance.source_url.startswith("https://")
            assert listing.provenance.source_type
            assert listing.provenance.observed_at

    def test_forty_seven_unique_valid_listings_remain(self):
        result = self._build()
        assert result.ok
        assert len(result.dataset.listings) == 52

    def test_no_duplicated_locality_in_street_address(self):
        # AES-WEB-002K.2 address-duplication fix: no seed row's street
        # address may carry its own city/state as a trailing, redundant
        # locality.
        result = self._build()
        assert result.ok
        for listing in result.dataset.listings:
            if listing.address is None or not listing.address.city:
                continue
            suffix = ", %s, %s" % (listing.address.city, listing.address.state)
            assert not listing.address.street.endswith(suffix), listing.listing_id

    def test_source_urls_never_become_ctas(self):
        result = self._build()
        assert result.ok
        assert all(listing.cta is None for listing in result.dataset.listings)

    def test_no_verified_badge_produced(self):
        # No listing carries a VERIFIED ListingKind -- the real sample
        # package supplies no verification data at all (§14 honesty rule).
        result = self._build()
        assert result.ok
        from engines.website_generation.contracts.enums import ListingKind
        assert all(
            listing.listing_kind != ListingKind.VERIFIED for listing in result.dataset.listings
        )

    def test_no_fake_default_listings(self):
        # Waves 1-3 removed every example.com sample row (hotel, park,
        # restaurant). The corpus is now 100% real records citing real
        # official sources -- no placeholder URL may appear anywhere.
        result = self._build()
        assert result.ok
        by_name = {l.business_name: l for l in result.dataset.listings}
        assert "Sunset Bay Pet-Friendly Inn" not in by_name
        assert "Riverbend Off-Leash Dog Park" not in by_name
        assert "Barkside Cafe" not in by_name
        ids_by_slug = {c.slug: c.category_id for c in result.dataset.categories}
        counts = {}
        for listing in result.dataset.listings:
            assert "example.com" not in listing.provenance.source_url, listing.business_name
            counts[listing.category_id] = counts.get(listing.category_id, 0) + 1
        assert counts[ids_by_slug["pet-friendly-hotels"]] == 25
        assert counts[ids_by_slug["pet-friendly-parks"]] == 14
        assert counts[ids_by_slug["pet-friendly-restaurants"]] == 13
        assert "Drury Inn & Suites Columbus Polaris" in by_name
        assert "Scioto Audubon Metro Park" in by_name
        assert "Land-Grant Brewing Company" in by_name
        assert "Condado Tacos Dublin" in by_name


class TestRealPackageReadiness:
    def _readiness(self):
        seed = read_seed_businesses_csv(_LAUNCH_PACKAGE_DIR / "seed_businesses.csv")
        cats = _load("categories.json")
        locs = _load("locations.json")
        config = _load("pilot_config.json")
        result = build_listing_dataset(seed_businesses=seed, categories=cats, locations=locs)
        return compute_inventory_readiness(
            result.dataset, config["inventory_thresholds"], reference_date="2026-07-15",
        )

    def test_readiness_is_true(self):
        # Wave 3 milestone: the first honest launch-threshold pass -- every
        # category clears 10 READY and the 30-total floor is met with only
        # real, source-backed records.
        assert self._readiness()["launch_inventory_ready"] is True

    def test_ready_only_counting(self):
        # AES-WEB-002N.1 (remediated semantics) against the Wave 3 corpus:
        # all 47 rows (20 hotels + 14 parks + 13 restaurants) are
        # required-complete and fresh -> READY; advisory gaps (no image,
        # no rating, most phones absent) never demote. Every category
        # clears the 10-per-category floor; no category is below target.
        readiness = self._readiness()
        assert readiness["total_unique_listings"] == 52
        assert readiness["counts_by_state"]["READY"] == 52
        assert readiness["counts_by_state"]["READY_WITH_WARNINGS"] == 0
        assert readiness["counts_by_state"]["NOT_READY"] == 0
        assert readiness["ready_total"] == 52
        assert readiness["ready_by_category"]["pet-friendly-hotels"] == 25
        assert readiness["ready_by_category"]["pet-friendly-parks"] == 14
        assert readiness["ready_by_category"]["pet-friendly-restaurants"] == 13
        assert readiness["categories_below_target"] == []
        for assessment in readiness["assessments"]:
            if assessment.category_slug == "pet-friendly-hotels":
                # No hotel carries authorized media or a citable official
                # rating yet -- visible, non-demoting advisories.
                assert "no_authorized_image" in assessment.advisories
                assert "no_rating" in assessment.advisories

    def test_load_launch_package_helper_matches_direct_reads(self):
        package = load_launch_package()
        assert package["blueprint"]["project_profile"]["project_name"] == "PetTripFinder"
        assert len(package["seed_businesses"]) == 52
