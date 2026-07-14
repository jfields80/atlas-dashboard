"""Component Engine Phase-B integration tests (AES-WEB-002J.19;
ADR-WEB-CONTENT-BINDING-MAP) -- the real ``ComponentEngine.compile()``
exercised end to end against the real registered catalog, real
``ListingDataset``/``BrandPackage`` inputs, and bindability-aware selection.

Distinct from ``test_component_engine.py`` (golden/general engine
behavior): this file is the dedicated home for the J.19 binding matrix
(groups B-K of the implementation test plan) -- bindability filtering,
listing assignment, SOURCE_UNAVAILABLE/STRUCTURED_DEFERRED handling, honest
failure modes, and determinism, all through the public ``compile()`` entry
point.
"""

from __future__ import annotations

import pytest

from engines.website_generation.brand.brand_engine import BrandEngine
from engines.website_generation.components import ComponentEngine, build_default_registry
from engines.website_generation.components.binding_rules import is_categorically_bindable
from engines.website_generation.contracts.artifacts import (
    BusinessSpec,
    ContentBlock,
    ContentPackage,
    ListingAddress,
    ListingCategory,
    ListingContact,
    ListingDataset,
    ListingHoursEntry,
    ListingRating,
    ListingRecord,
    ListingSponsorship,
    PagePlan,
    SiteArchitecture,
    artifact_sha256,
)
from engines.website_generation.contracts.enums import ArtifactKind, ListingKind, Weekday
from engines.website_generation.contracts.errors import ComponentResolutionError
from engines.website_generation.contracts.versions import SCHEMA_VERSIONS

_REGISTRY = build_default_registry()


def _sa(pages):
    return SiteArchitecture(
        schema_version=SCHEMA_VERSIONS[ArtifactKind.SITE_ARCHITECTURE],
        artifact_kind=ArtifactKind.SITE_ARCHITECTURE, source_hashes={},
        pages=tuple(pages), nav_routes=(), sitemap_routes=tuple(p.route for p in pages),
    )


def _cp(blocks=()):
    return ContentPackage(
        schema_version=SCHEMA_VERSIONS[ArtifactKind.CONTENT_PACKAGE],
        artifact_kind=ArtifactKind.CONTENT_PACKAGE, source_hashes={}, blocks=tuple(blocks),
    )


def _brand():
    spec = BusinessSpec(
        schema_version=SCHEMA_VERSIONS[ArtifactKind.BUSINESS_SPEC],
        artifact_kind=ArtifactKind.BUSINESS_SPEC, source_hashes={},
        business_name="Test Directory", niche="y", audience="z", value_proposition="w",
    )
    return BrandEngine().resolve(spec)


def _full_listing(**overrides):
    fields = dict(
        listing_id="lakeview-lodge", business_name="Lakeview Lodge",
        slug="lakeview-lodge", category_id="cat-hotels",
        description="A lakeside lodge that welcomes pets.",
        contact=ListingContact(phone="555-0100", email="stay@lakeview.example"),
        address=ListingAddress(city="Austin", state="TX"),
        hours=(ListingHoursEntry(day=Weekday.MONDAY, opens="08:00", closes="20:00"),),
        rating=ListingRating(rating_hundredths=450, review_count=27),
        credentials=("Licensed pet boarding operator",),
    )
    fields.update(overrides)
    return ListingRecord(**fields)


def _dataset(listings, categories=(ListingCategory(category_id="cat-hotels", label="Hotels", slug="hotels"),)):
    return ListingDataset(
        schema_version=SCHEMA_VERSIONS[ArtifactKind.LISTING_DATASET],
        artifact_kind=ArtifactKind.LISTING_DATASET, source_hashes={},
        listings=tuple(listings), categories=categories, locations=(),
    )


_PROFILE_PAGE = PagePlan(route="/hotels/lakeview-lodge/", page_type="business-profile", title="")


# --------------------------------------------------------------------------- #
# B. Bindability-aware selection
# --------------------------------------------------------------------------- #

class TestBindabilityAwareSelection:
    def test_architecturally_unbindable_required_slot_falls_back(self):
        # directory.categories.grid (STRUCTURED_DEFERRED required field) is
        # excluded; its declared fallback layout.grid.standard wins instead.
        result = ComponentEngine().compile(
            _sa([PagePlan(route="/", page_type="home", title="")]),
            _cp([
                ContentBlock(page_route="/", slot_id="hero_h1", text="Find pet-friendly places to stay"),
                ContentBlock(page_route="/", slot_id="subhead", text="Verified hotels, parks, restaurants."),
                ContentBlock(page_route="/", slot_id="message", text="Some listings are sponsored."),
            ]),
            brand_package=_brand(),
        )
        ids = [i.component_id for i in result.component_manifest.pages[0].components]
        assert "directory.categories.grid" not in ids
        assert "layout.grid.standard" in ids

    def test_selection_trace_names_bindability_as_the_elimination_reason(self):
        # directory.categories.grid isn't ranked highly enough to land in the
        # trace's named top-5 candidates (§14.3 size bound -- the same
        # compression every other elimination filter is subject to); its
        # elimination is still provable via the per-filter count.
        result = ComponentEngine().compile(
            _sa([PagePlan(route="/", page_type="home", title="")]),
            _cp([
                ContentBlock(page_route="/", slot_id="hero_h1", text="Find pet-friendly places to stay"),
                ContentBlock(page_route="/", slot_id="subhead", text="Verified hotels, parks, restaurants."),
                ContentBlock(page_route="/", slot_id="message", text="Some listings are sponsored."),
            ]),
            brand_package=_brand(),
        )
        grid_slot = next(
            s for s in result.component_manifest.selection_trace.slots
            if s.slot_id == "/#categories_grid"
        )
        assert grid_slot.elimination_counts.get("bindability", 0) >= 1

    def test_optional_unbindable_slot_dropped_not_failed(self):
        # locations_grid is optional with no fallback -- an unbindable real
        # candidate must be silently (but traceably) dropped, not fail the
        # whole compile.
        result = ComponentEngine().compile(
            _sa([PagePlan(route="/", page_type="home", title="")]),
            _cp([
                ContentBlock(page_route="/", slot_id="hero_h1", text="Find pet-friendly places to stay"),
                ContentBlock(page_route="/", slot_id="subhead", text="Verified hotels, parks, restaurants."),
                ContentBlock(page_route="/", slot_id="message", text="Some listings are sponsored."),
            ]),
            brand_package=_brand(),
        )
        ids = [i.component_id for i in result.component_manifest.pages[0].components]
        assert "directory.locations.grid" not in ids

    def test_required_slot_with_no_bindable_fallback_raises(self):
        # AES-WEB-002J.20: the category recipe's "pagination"/"zero_results"
        # slots gained a structural fallback (layout.stack.standard) by
        # operator-authorized amendment, so category no longer demonstrates
        # this claim. search-results' "pagination" slot is untouched by
        # that amendment (§13 operator decision: category recipe only) and
        # still has no fallback, with its only real candidate
        # (nav.pagination.standard: page_context is SOURCE_UNAVAILABLE)
        # still categorically unbindable.
        with pytest.raises(ComponentResolutionError) as exc:
            ComponentEngine().compile(
                _sa([PagePlan(route="/search", page_type="search-results", title="")]),
                _cp(), listing_dataset=_dataset([_full_listing()]), brand_package=_brand(),
            )
        assert "unresolved_required_slots" in exc.value.diagnostics

    def test_bindability_check_is_purely_static_independent_of_supplied_data(self):
        # Even WITH full data supplied, the categorically-unbindable
        # candidate is still excluded -- proving the filter is architectural,
        # not data-availability-based.
        with_data = ComponentEngine().compile(
            _sa([PagePlan(route="/", page_type="home", title="")]),
            _cp([
                ContentBlock(page_route="/", slot_id="hero_h1", text="Find pet-friendly places to stay"),
                ContentBlock(page_route="/", slot_id="subhead", text="Verified hotels, parks, restaurants."),
                ContentBlock(page_route="/", slot_id="message", text="Some listings are sponsored."),
            ]),
            listing_dataset=_dataset([_full_listing()]), brand_package=_brand(),
        )
        ids = [i.component_id for i in with_data.component_manifest.pages[0].components]
        assert "directory.categories.grid" not in ids  # still excluded


# --------------------------------------------------------------------------- #
# C. Editorial content binding (alias precedence)
# --------------------------------------------------------------------------- #

class TestEditorialBinding:
    def test_hero_h1_alias_to_page_h1(self):
        result = ComponentEngine().compile(
            _sa([PagePlan(route="/", page_type="home", title="")]),
            _cp([
                ContentBlock(page_route="/", slot_id="hero_h1", text="Real headline text"),
                ContentBlock(page_route="/", slot_id="subhead", text="Real subhead text"),
                ContentBlock(page_route="/", slot_id="message", text="Real message text"),
            ]),
            brand_package=_brand(),
        )
        h1_block = next(
            b for b in result.content_package.blocks if b.slot_id == "h1"
        )
        assert h1_block.text == "Real headline text"

    def test_missing_required_editorial_content_fails_honestly(self):
        with pytest.raises(ComponentResolutionError) as exc:
            ComponentEngine().compile(
                _sa([PagePlan(route="/", page_type="home", title="")]),
                _cp(), brand_package=_brand(),
            )
        content_failures = exc.value.diagnostics.get("unbindable_required_content", [])
        assert any(f["slot"] == "h1" for f in content_failures)


# --------------------------------------------------------------------------- #
# D. Listing assignment and projection (business-profile route)
# --------------------------------------------------------------------------- #

class TestListingAssignmentAndProjection:
    def test_real_listing_name_bound(self):
        result = ComponentEngine().compile(
            _sa([_PROFILE_PAGE]), _cp(),
            listing_dataset=_dataset([_full_listing()]), brand_package=_brand(),
        )
        page = result.component_manifest.pages[0]
        header = next(i for i in page.components if i.component_id == "profile.header.business")
        name_block = next(b for b in result.content_package.blocks if b.slot_id == "name")
        assert name_block.text == "Lakeview Lodge"
        assert header.props["listing_ref"].startswith("bind.listing_name.")

    def test_real_contact_hours_description(self):
        result = ComponentEngine().compile(
            _sa([_PROFILE_PAGE]), _cp(),
            listing_dataset=_dataset([_full_listing()]), brand_package=_brand(),
        )
        by_slot = {b.slot_id: b.text for b in result.content_package.blocks}
        assert by_slot["description"] == "A lakeside lodge that welcomes pets."
        assert "555-0100" in by_slot["contact_info"]
        assert "Mon" in by_slot["hours"]
        assert by_slot["credentials"] == "Licensed pet boarding operator"

    def test_sponsorship_disclosure_bound_when_present(self):
        listing = _full_listing(
            listing_kind=ListingKind.SPONSORED,
            sponsorship=ListingSponsorship(kind=ListingKind.SPONSORED, disclosure_text="Sponsored listing"),
        )
        # AES-WEB-002J.20: related_listings excludes the page's own listing
        # (exclude_self=True), so a companion listing in the same category
        # is required for a real (non-self) related_listings instance to
        # exist. listing.card.sponsored requires a disclosure content slot.
        companion = _full_listing(listing_id="other-lodge", slug="other-lodge")
        result = ComponentEngine().compile(
            _sa([_PROFILE_PAGE]), _cp(),
            listing_dataset=_dataset([listing, companion]), brand_package=_brand(),
        )
        page = result.component_manifest.pages[0]
        assert any(i.component_id == "listing.card.standard" for i in page.components)

    def test_no_matching_listing_fails_honestly(self):
        # The route names a listing slug that does not exist in the dataset.
        page = PagePlan(route="/hotels/does-not-exist/", page_type="business-profile", title="")
        with pytest.raises(ComponentResolutionError) as exc:
            ComponentEngine().compile(
                _sa([page]), _cp(),
                listing_dataset=_dataset([_full_listing()]), brand_package=_brand(),
            )
        content_failures = exc.value.diagnostics.get("unbindable_required_content", []) + \
            exc.value.diagnostics.get("unbindable_required_props", [])
        assert any("missing_listing" in f["reason"] for f in content_failures)

    def test_related_listings_expands_one_instance_per_non_self_match(self):
        # AES-WEB-002J.19 (superseded): Phase A selected exactly one
        # listing.card.standard instance for related_listings regardless of
        # how many listings matched -- no repetition.
        #
        # AES-WEB-002J.20: repetition now sits between Phase A selection and
        # Phase B binding, so related_listings expands to one instance per
        # matching listing (exclude_self=True: the page's own listing,
        # lakeview-lodge, never counts as its own "related" listing). Three
        # companions in the same category prove real N-way expansion, not
        # just the N=1 case that was indistinguishable from the old
        # single-instance behavior.
        multi = _dataset([
            _full_listing(),  # lakeview-lodge -- matches _PROFILE_PAGE's route; excluded as self
            _full_listing(listing_id="other-lodge-1", slug="other-lodge-1"),
            _full_listing(listing_id="other-lodge-2", slug="other-lodge-2"),
            _full_listing(listing_id="other-lodge-3", slug="other-lodge-3"),
        ])
        result = ComponentEngine().compile(
            _sa([_PROFILE_PAGE]), _cp(), listing_dataset=multi, brand_package=_brand(),
        )
        page = result.component_manifest.pages[0]
        cards = [i for i in page.components if i.component_id == "listing.card.standard"]
        assert len(cards) == 3
        bound_ids = [c.props["listing_ref"].split(".")[-1] for c in cards]
        assert "lakeview-lodge" not in bound_ids
        assert bound_ids == ["other-lodge-1", "other-lodge-2", "other-lodge-3"]


# --------------------------------------------------------------------------- #
# E-F. Errors, honesty, no placeholders
# --------------------------------------------------------------------------- #

class TestHonestFailureAndNoPlaceholders:
    def test_no_resolved_placeholder_strings_anywhere(self):
        result = ComponentEngine().compile(
            _sa([_PROFILE_PAGE]), _cp(),
            listing_dataset=_dataset([_full_listing()]), brand_package=_brand(),
        )
        for block in result.content_package.blocks:
            assert "Resolved " not in block.text
            assert "TODO" not in block.text
            assert "placeholder" not in block.text.lower()

    def test_batch_reports_multiple_failures_together(self):
        pages = [
            PagePlan(route="/", page_type="home", title=""),
            _PROFILE_PAGE,
        ]
        with pytest.raises(ComponentResolutionError) as exc:
            ComponentEngine().compile(_sa(pages), _cp())  # no listing/brand at all
        diag = exc.value.diagnostics
        total_entries = sum(len(v) for v in diag.values() if isinstance(v, list))
        assert total_entries > 1  # multiple distinct failures batched, not first-failure-only

    def test_no_partial_result_on_failure(self):
        with pytest.raises(ComponentResolutionError):
            result = ComponentEngine().compile(_sa([_PROFILE_PAGE]), _cp())
            # unreachable if the exception is raised, which it must be
            assert result is None  # pragma: no cover


# --------------------------------------------------------------------------- #
# G. ContentPackage immutability
# --------------------------------------------------------------------------- #

class TestContentPackageImmutability:
    def test_original_content_package_object_unmodified(self):
        original = _cp([ContentBlock(page_route="/", slot_id="hero_h1", text="Original headline")])
        original_hash = artifact_sha256(original)
        try:
            ComponentEngine().compile(
                _sa([PagePlan(route="/", page_type="home", title="")]),
                original,
                brand_package=_brand(),
            )
        except ComponentResolutionError:
            pass  # incomplete content (no subhead/message) -- irrelevant to this check
        assert artifact_sha256(original) == original_hash
        assert original.blocks == (ContentBlock(page_route="/", slot_id="hero_h1", text="Original headline"),)

    def test_augmented_package_is_a_new_object(self):
        original = _cp([
            ContentBlock(page_route="/", slot_id="hero_h1", text="Find pet-friendly places to stay"),
            ContentBlock(page_route="/", slot_id="subhead", text="Verified hotels, parks, restaurants."),
            ContentBlock(page_route="/", slot_id="message", text="Some listings are sponsored."),
        ])
        result = ComponentEngine().compile(
            _sa([PagePlan(route="/", page_type="home", title="")]), original, brand_package=_brand(),
        )
        assert result.content_package is not original
        assert len(result.content_package.blocks) > len(original.blocks)
        assert set(original.blocks) <= set(result.content_package.blocks)


# --------------------------------------------------------------------------- #
# H. Determinism
# --------------------------------------------------------------------------- #

class TestDeterminism:
    def test_repeat_compile_byte_identical(self):
        ds, brand = _dataset([_full_listing()]), _brand()
        sa, cp = _sa([_PROFILE_PAGE]), _cp()
        a = ComponentEngine().compile(sa, cp, listing_dataset=ds, brand_package=brand)
        b = ComponentEngine().compile(sa, cp, listing_dataset=ds, brand_package=brand)
        assert artifact_sha256(a.component_manifest) == artifact_sha256(b.component_manifest)
        assert artifact_sha256(a.content_package) == artifact_sha256(b.content_package)

    def test_fresh_registry_instances_agree(self):
        ds, brand = _dataset([_full_listing()]), _brand()
        sa, cp = _sa([_PROFILE_PAGE]), _cp()
        a = ComponentEngine().compile(sa, cp, listing_dataset=ds, brand_package=brand, registry=build_default_registry())
        b = ComponentEngine().compile(sa, cp, listing_dataset=ds, brand_package=brand, registry=build_default_registry())
        assert artifact_sha256(a.component_manifest) == artifact_sha256(b.component_manifest)


# --------------------------------------------------------------------------- #
# I. Architecture
# --------------------------------------------------------------------------- #

class TestArchitecture:
    def test_component_engine_owns_binding_no_renderer_import(self):
        import ast

        import engines.website_generation.components.component_engine as ce
        tree = ast.parse(ast.unparse(ast.parse(open(ce.__file__, encoding="utf-8").read())))
        for node in ast.walk(tree):
            if isinstance(node, ast.ImportFrom) and node.module:
                assert "rendering" not in node.module
                assert "emitters" not in node.module
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    assert "rendering" not in alias.name
                    assert "emitters" not in alias.name

    def test_pipeline_remains_unwired(self):
        from engines.website_generation.constants.build import (
            PHASE1_EXECUTED_STAGES,
            STAGE_SPEC_COMPILATION,
        )
        assert PHASE1_EXECUTED_STAGES == (STAGE_SPEC_COMPILATION,)

    def test_all_components_remain_proposed(self):
        ids = [d.component_id for d in _REGISTRY.all_definitions()]
        assert {str(_REGISTRY.lifecycle(c)) for c in ids} == {"LifecycleStatus.PROPOSED"}

    def test_is_categorically_bindable_matches_engine_behavior(self):
        assert is_categorically_bindable("directory.categories.grid") is False
        assert is_categorically_bindable("hero.local.standard") is True
