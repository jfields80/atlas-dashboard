"""PILOT-PTF-1 real-launch-package proof.

Uses the actual ``launch_packages/pettripfinder/`` sample files (not the
dedicated 12-listing acceptance fixture) to prove the converter and
readiness check behave honestly against real, currently-insufficient
inventory. Does NOT assert launch readiness -- the opposite: it asserts the
real sample package is honestly reported as NOT launch-ready.
"""

from __future__ import annotations

import json
import pathlib

from scripts.generate_pettripfinder_pilot import (
    compute_inventory_readiness,
    load_launch_package,
)
from scripts.pettripfinder.listing_dataset_builder import build_listing_dataset

_LAUNCH_PACKAGE_DIR = (
    pathlib.Path(__file__).resolve().parents[3] / "launch_packages" / "pettripfinder"
)


def _load(name: str):
    with (_LAUNCH_PACKAGE_DIR / name).open("r", encoding="utf-8") as f:
        return json.load(f)


class TestRealSeedFilesParse:
    def test_seed_businesses_parses(self):
        seed = _load("seed_businesses.json")
        assert len(seed) == 4

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
        seed = _load("seed_businesses.json")
        cats = _load("categories.json")
        locs = _load("locations.json")
        return build_listing_dataset(seed_businesses=seed, categories=cats, locations=locs)

    def test_duplicate_is_deduplicated_and_reported(self):
        result = self._build()
        assert result.ok
        assert len(result.rejected_duplicates) == 1
        # Deterministic winner (alphabetically-first name at the tied
        # address wins, see listing_dataset_builder._dedup_key) -- either
        # "Sunset Bay..." name is a real record; the point being proven is
        # that exactly one of the two survives and the other is reported.
        assert "Columbus, OH" in result.rejected_duplicates[0]

    def test_three_unique_valid_listings_remain(self):
        result = self._build()
        assert result.ok
        assert len(result.dataset.listings) == 3

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
        result = self._build()
        assert result.ok
        names = {l.business_name for l in result.dataset.listings}
        # One of the two Sunset Bay records wins deterministically (see
        # test_duplicate_is_deduplicated_and_reported); both are real
        # source names, never a fabricated placeholder.
        assert names == {"Duplicate Sunset Bay Inn", "Barkside Cafe", "Riverbend Off-Leash Dog Park"}


class TestRealPackageReadiness:
    def test_readiness_is_false(self):
        seed = _load("seed_businesses.json")
        cats = _load("categories.json")
        locs = _load("locations.json")
        config = _load("pilot_config.json")
        result = build_listing_dataset(seed_businesses=seed, categories=cats, locations=locs)
        readiness = compute_inventory_readiness(result.dataset, config["inventory_thresholds"])
        assert readiness["launch_inventory_ready"] is False

    def test_counts_show_insufficient_inventory(self):
        seed = _load("seed_businesses.json")
        cats = _load("categories.json")
        locs = _load("locations.json")
        config = _load("pilot_config.json")
        result = build_listing_dataset(seed_businesses=seed, categories=cats, locations=locs)
        readiness = compute_inventory_readiness(result.dataset, config["inventory_thresholds"])
        assert readiness["total_unique_listings"] == 3
        assert readiness["total_unique_listings"] < config["inventory_thresholds"]["minimum_total_listings"]
        assert set(readiness["categories_below_target"]) == {
            "pet-friendly-hotels", "pet-friendly-parks", "pet-friendly-restaurants",
        }

    def test_load_launch_package_helper_matches_direct_reads(self):
        package = load_launch_package()
        assert package["blueprint"]["project_profile"]["project_name"] == "PetTripFinder"
        assert len(package["seed_businesses"]) == 4
