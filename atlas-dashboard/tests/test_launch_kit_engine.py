"""Tests for the Launch Kit Engine (pure, in-memory)."""

from __future__ import annotations

import csv
import io
import json

import pytest

from engines.launch_kit import (
    LAUNCH_KIT_FILENAMES,
    LaunchKitInput,
    LaunchKitInputError,
    build_launch_kit,
    slugify,
)


def _parse_csv(content: str):
    return list(csv.DictReader(io.StringIO(content)))


# ---------------------------------------------------------------------------
# Structure and completeness
# ---------------------------------------------------------------------------


class TestKitStructure:
    def test_all_twelve_files_present_in_order(self, full_blueprint, full_seed_package):
        kit = build_launch_kit(
            LaunchKitInput("pet-trip-finder", full_blueprint, full_seed_package)
        )
        assert tuple(f.filename for f in kit.files) == LAUNCH_KIT_FILENAMES
        assert len(kit.files) == 12

    def test_project_name_defaults_from_slug(self, sparse_blueprint, sparse_seed_package):
        kit = build_launch_kit(
            LaunchKitInput("pet-trip-finder", sparse_blueprint, sparse_seed_package)
        )
        assert kit.project_name == "Pet Trip Finder"

    def test_explicit_project_name_used(self, sparse_blueprint, sparse_seed_package):
        kit = build_launch_kit(
            LaunchKitInput(
                "pet-trip-finder",
                sparse_blueprint,
                sparse_seed_package,
                project_name="PetTripFinder.com",
            )
        )
        assert kit.project_name == "PetTripFinder.com"

    def test_slug_is_sanitized(self, sparse_blueprint, sparse_seed_package):
        kit = build_launch_kit(
            LaunchKitInput("Pet Trip Finder!", sparse_blueprint, sparse_seed_package)
        )
        assert kit.project_slug == "pet-trip-finder"

    def test_get_file_and_missing_file(self, full_blueprint, full_seed_package):
        kit = build_launch_kit(
            LaunchKitInput("p", full_blueprint, full_seed_package)
        )
        assert kit.get_file("blueprint.json").filename == "blueprint.json"
        with pytest.raises(KeyError):
            kit.get_file("nope.txt")


# ---------------------------------------------------------------------------
# Input validation
# ---------------------------------------------------------------------------


class TestValidation:
    def test_empty_slug_rejected(self):
        with pytest.raises(LaunchKitInputError):
            build_launch_kit(LaunchKitInput("", {}, {}))

    def test_symbol_only_slug_rejected(self):
        with pytest.raises(LaunchKitInputError):
            build_launch_kit(LaunchKitInput("!!!", {}, {}))

    def test_non_mapping_blueprint_rejected(self):
        with pytest.raises(LaunchKitInputError):
            build_launch_kit(LaunchKitInput("p", ["not-a-dict"], {}))  # type: ignore[arg-type]

    def test_non_mapping_seed_package_rejected(self):
        with pytest.raises(LaunchKitInputError):
            build_launch_kit(LaunchKitInput("p", {}, "not-a-dict"))  # type: ignore[arg-type]


# ---------------------------------------------------------------------------
# Determinism
# ---------------------------------------------------------------------------


class TestDeterminism:
    def test_identical_input_byte_identical_output(
        self, full_blueprint, full_seed_package
    ):
        kit_a = build_launch_kit(
            LaunchKitInput("p", full_blueprint, full_seed_package)
        )
        kit_b = build_launch_kit(
            LaunchKitInput("p", full_blueprint, full_seed_package)
        )
        for file_a, file_b in zip(kit_a.files, kit_b.files):
            assert file_a.filename == file_b.filename
            assert file_a.content == file_b.content

    def test_no_timestamp_without_generated_at(
        self, full_blueprint, full_seed_package
    ):
        kit = build_launch_kit(
            LaunchKitInput("p", full_blueprint, full_seed_package)
        )
        for launch_file in kit.files:
            assert "Generated:" not in launch_file.content

    def test_generated_at_appears_when_provided(
        self, full_blueprint, full_seed_package
    ):
        stamp = "2026-07-06T00:00:00Z"
        kit = build_launch_kit(
            LaunchKitInput(
                "p", full_blueprint, full_seed_package, generated_at=stamp
            )
        )
        assert stamp in kit.get_file("launch_checklist.md").content
        assert stamp in kit.get_file("operator_notes.md").content

    def test_all_files_use_lf_line_endings(self, full_blueprint, full_seed_package):
        kit = build_launch_kit(
            LaunchKitInput("p", full_blueprint, full_seed_package)
        )
        for launch_file in kit.files:
            assert "\r" not in launch_file.content


# ---------------------------------------------------------------------------
# Extraction from a full-featured input
# ---------------------------------------------------------------------------


class TestFullExtraction:
    @pytest.fixture
    def kit(self, full_blueprint, full_seed_package):
        return build_launch_kit(
            LaunchKitInput("pet-trip-finder", full_blueprint, full_seed_package)
        )

    def test_blueprint_json_round_trips(self, kit, full_blueprint):
        assert json.loads(kit.get_file("blueprint.json").content) == full_blueprint

    def test_seed_csv_rows_match_listings(self, kit):
        rows = _parse_csv(kit.get_file("seed_businesses.csv").content)
        assert len(rows) == 3
        assert rows[0]["name"] == "The Barkley Hotel"
        # Preferred columns come first.
        header = kit.get_file("seed_businesses.csv").content.splitlines()[0]
        assert header.startswith("id,name,category")

    def test_seed_csv_serializes_nested_values_as_json(self, kit):
        rows = _parse_csv(kit.get_file("seed_businesses.csv").content)
        assert json.loads(rows[0]["amenities"]) == ["dog park", "pet spa"]

    def test_seed_json_matches_listings(self, kit):
        data = json.loads(kit.get_file("seed_businesses.json").content)
        assert [entry["id"] for entry in data] == ["L001", "L002", "L003"]

    def test_categories_normalized_sorted_with_slugs(self, kit):
        cats = json.loads(kit.get_file("categories.json").content)
        assert [c["slug"] for c in cats] == ["campgrounds", "hotels"]
        assert cats[1]["listing_count"] == 2

    def test_locations_normalized_sorted_with_slugs(self, kit):
        locs = json.loads(kit.get_file("locations.json").content)
        assert [l["slug"] for l in locs] == ["columbus-oh", "dublin-oh"]

    def test_url_map_uses_blueprint_when_present(self, kit):
        rows = _parse_csv(kit.get_file("url_map.csv").content)
        assert all(row["source"] == "blueprint" for row in rows)
        assert {row["url"] for row in rows} == {
            "/",
            "/hotels/",
            "/columbus-oh/hotels/",
        }

    def test_seo_pages_flatten_keyword_lists(self, kit):
        rows = _parse_csv(kit.get_file("seo_pages.csv").content)
        assert len(rows) == 2
        hotels = next(r for r in rows if r["url"] == "/hotels/")
        assert hotels["secondary_keywords"] == "dog friendly hotels; pet hotels"

    def test_content_plan_rows(self, kit):
        rows = _parse_csv(kit.get_file("content_plan.csv").content)
        assert len(rows) == 2
        assert rows[0]["content_type"] == "listicle"

    def test_monetization_plan_round_trips(self, kit, full_blueprint):
        data = json.loads(kit.get_file("monetization_plan.json").content)
        assert data == full_blueprint["monetization_plan"]

    def test_ai_task_queue_assigns_ids_and_status(self, kit):
        rows = _parse_csv(kit.get_file("ai_task_queue.csv").content)
        assert rows[0]["task_id"] == "T001"
        assert rows[1]["task_id"] == "CUSTOM-2"  # explicit id preserved
        assert all(row["status"] == "pending" for row in rows)
        assert rows[1]["depends_on"] == "T001"

    def test_checklist_uses_roadmap_phases(self, kit):
        content = kit.get_file("launch_checklist.md").content
        assert "## Foundation" in content
        assert "- [ ] Set up hosting" in content
        assert "- [ ] Import seed listings" in content  # dict-style task
        assert "- [ ] (no tasks defined for this phase)" in content
        assert "- [ ] Import 3 seed businesses" in content

    def test_operator_notes_include_stats_risks_quality(self, kit):
        content = kit.get_file("operator_notes.md").content
        assert "- Seed businesses: 3" in content
        assert "Thin content penalty" in content
        assert "Mitigation: Minimum 300 words per category page" in content
        assert "verified_count: 1" in content
        assert "Primary model: featured_listings" in content

    def test_stats_counts(self, kit):
        stats = kit.stats
        assert stats.listing_count == 3
        assert stats.category_count == 2
        assert stats.location_count == 2
        assert stats.seo_page_count == 2
        assert stats.content_item_count == 2
        assert stats.ai_task_count == 2
        assert "blueprint.roadmap" in stats.sections_present
        assert stats.sections_missing == ()


# ---------------------------------------------------------------------------
# Sparse input: everything missing still yields a valid package
# ---------------------------------------------------------------------------


class TestSparseInput:
    @pytest.fixture
    def kit(self, sparse_blueprint, sparse_seed_package):
        return build_launch_kit(
            LaunchKitInput("sparse-project", sparse_blueprint, sparse_seed_package)
        )

    def test_all_files_still_present(self, kit):
        assert tuple(f.filename for f in kit.files) == LAUNCH_KIT_FILENAMES

    def test_json_files_are_valid_and_empty(self, kit):
        assert json.loads(kit.get_file("seed_businesses.json").content) == []
        assert json.loads(kit.get_file("categories.json").content) == []
        assert json.loads(kit.get_file("locations.json").content) == []
        assert json.loads(kit.get_file("monetization_plan.json").content) == {}

    def test_csv_files_have_headers_only(self, kit):
        for name in ("seed_businesses.csv", "seo_pages.csv", "content_plan.csv",
                     "ai_task_queue.csv"):
            content = kit.get_file(name).content
            lines = content.strip().splitlines()
            assert len(lines) == 1, f"{name} should be header-only"
            assert lines[0], f"{name} header must not be empty"

    def test_url_map_falls_back_to_home_page(self, kit):
        rows = _parse_csv(kit.get_file("url_map.csv").content)
        assert rows == [
            {"url": "/", "page_type": "home", "source": "generated", "notes": ""}
        ]

    def test_checklist_falls_back_to_default_sections(self, kit):
        content = kit.get_file("launch_checklist.md").content
        assert "standard directory launch checklist" in content
        assert "## Pre-Launch" in content
        assert "## Monetization" in content

    def test_operator_notes_flag_missing_sections(self, kit):
        content = kit.get_file("operator_notes.md").content
        assert "blueprint.monetization_plan" in content
        assert "seed_package.listings" in content
        assert "UNVERIFIED" in content

    def test_stats_reflect_emptiness(self, kit):
        assert kit.stats.listing_count == 0
        assert kit.stats.category_count == 0
        assert "blueprint.roadmap" in kit.stats.sections_missing


# ---------------------------------------------------------------------------
# Tolerant key aliases and derivation fallbacks
# ---------------------------------------------------------------------------


class TestTolerantExtraction:
    def test_listings_under_businesses_key(self):
        seed = {"businesses": [{"name": "A", "category": "Cafes", "city": "Columbus"}]}
        kit = build_launch_kit(LaunchKitInput("p", {}, seed))
        assert kit.stats.listing_count == 1

    def test_listings_under_nested_data_wrapper(self):
        seed = {"data": {"records": [{"name": "A"}]}}
        kit = build_launch_kit(LaunchKitInput("p", {}, seed))
        assert kit.stats.listing_count == 1

    def test_categories_derived_from_listings(self):
        seed = {
            "listings": [
                {"name": "A", "category": "Hotels"},
                {"name": "B", "category": "Hotels"},
                {"name": "C", "category": "Vets"},
            ]
        }
        kit = build_launch_kit(LaunchKitInput("p", {}, seed))
        cats = json.loads(kit.get_file("categories.json").content)
        assert [c["slug"] for c in cats] == ["hotels", "vets"]
        assert all(c["derived_from"] == "listings" for c in cats)

    def test_categories_as_plain_strings(self):
        seed = {"categories": ["Hotels", "Vets"]}
        kit = build_launch_kit(LaunchKitInput("p", {}, seed))
        cats = json.loads(kit.get_file("categories.json").content)
        assert [c["name"] for c in cats] == ["Hotels", "Vets"]

    def test_locations_derived_from_listing_cities(self):
        seed = {
            "listings": [
                {"name": "A", "city": "Columbus", "state": "OH"},
                {"name": "B", "city": "Columbus", "state": "OH"},
                {"name": "C", "city": "Dublin", "state": "OH"},
            ]
        }
        kit = build_launch_kit(LaunchKitInput("p", {}, seed))
        locs = json.loads(kit.get_file("locations.json").content)
        assert [l["slug"] for l in locs] == ["columbus-oh", "dublin-oh"]

    def test_generated_url_map_from_categories_and_locations(self):
        seed = {
            "categories": ["Hotels"],
            "locations": [{"name": "Columbus", "state": "OH"}],
        }
        kit = build_launch_kit(LaunchKitInput("p", {}, seed))
        rows = _parse_csv(kit.get_file("url_map.csv").content)
        urls = {row["url"] for row in rows}
        assert urls == {"/", "/hotels/", "/columbus-oh/", "/columbus-oh/hotels/"}
        assert all(row["source"] == "generated" for row in rows)

    def test_monetization_under_alias_key(self):
        blueprint = {"monetization": {"primary_model": "leads"}}
        kit = build_launch_kit(LaunchKitInput("p", blueprint, {}))
        data = json.loads(kit.get_file("monetization_plan.json").content)
        assert data["primary_model"] == "leads"

    def test_roadmap_as_plain_list(self):
        blueprint = {"roadmap": [{"name": "Only Phase", "tasks": ["Do it"]}]}
        kit = build_launch_kit(LaunchKitInput("p", blueprint, {}))
        assert "## Only Phase" in kit.get_file("launch_checklist.md").content

    def test_risks_as_plain_list(self):
        blueprint = {"risks": [{"name": "Something", "severity": "low"}]}
        kit = build_launch_kit(LaunchKitInput("p", blueprint, {}))
        assert "Something" in kit.get_file("operator_notes.md").content

    def test_malformed_listing_entries_dropped(self):
        seed = {"listings": [{"name": "Good"}, 42, None, ["bad"]]}
        kit = build_launch_kit(LaunchKitInput("p", {}, seed))
        assert kit.stats.listing_count == 1


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


class TestSlugify:
    @pytest.mark.parametrize(
        "raw, expected",
        [
            ("Pet Trip Finder", "pet-trip-finder"),
            ("  Columbus, OH  ", "columbus-oh"),
            ("Already-Slugged", "already-slugged"),
            ("Multiple   Spaces & Symbols!!", "multiple-spaces-symbols"),
        ],
    )
    def test_slugify(self, raw, expected):
        assert slugify(raw) == expected
